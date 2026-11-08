# Adapted from shorts-studio/engine/short/gen.py, auto_chunks (MIT).
# Changes by REVXL: output-frame layout boundaries and inclusive word positions.
#
# MIT License
#
# Copyright (c) 2026 Claude Video Studio contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Adapted from video-use/helpers/render.py, chunk_words (MIT).
# Changes by REVXL: cut-word dictionaries, frame lifetimes, layout boundaries,
# optional punctuation/pause breaks and truthful marked runs kept together.
#
# MIT License
#
# Copyright (c) 2026 Browser Use
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Plan burned-in captions and return markup for compose's root timeline.

No tools or rendering in plan(); reading a Send remembers its caption look.
Only write() saves work/captions.json.
Word positions always refer to the original cut word list, including empty rows.
pick_marks() returns inclusive truthful runs; the planner retains later accents
and separately records the one punch event allowed per sentence.
"""
import argparse
import contextlib
import html
import io
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS, PLUGIN = HERE.parents[1], HERE.parents[2]
for directory in (SKILLS / "_shared", SKILLS / "reel-canvas-build/scripts",
                  SKILLS / "caption-writer/scripts", PLUGIN / "scripts"):
    sys.path.insert(0, str(directory))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import saved_style  # noqa: E402
import standing_notes  # noqa: E402
import beat_schema  # noqa: E402
import scene_check  # noqa: E402
from emphasis import truthful_span, tokenize, _is_num  # noqa: E402, F401 (shared TRI-6 rule)

SEND = "beat-map-selection.json"
PICKER_SEND = "look-picker-selection.json"
CHAR_WIDTHS = HERE.parent / "references/char-widths.json"
DEFAULT_WORDS = beat_schema.DEFAULT_WORDS
ASK = "ask: which caption look? Clean, Bold pop, Boxed, Karaoke or Outline caps (or no captions)"
DEFAULTS = {"accent": "#FFD84D", "under_small_overlays": True, "line_breaks": True,
            "echo_suppression": False, "min_read_s": 0.35,
            "mark_look": "accent", "loud_emphasis": False}  # taste: reading-time suggestion


def _look(label, size, case="none", stroke=None, plate=None, start=None, frames=4, karaoke=False):
    return {"label": label, "size": size, "case": case, "color": "#FFFFFF", "accent": "#FFD84D",
            "stroke": stroke, "plate": plate, "line_h": 1.2,
            "pop": {"from": start or {"autoAlpha": 0, "y": 12},
                    "to": {"autoAlpha": 1, "y": 0, "scale": 1}, "frames": frames, "ease": "power2.out"},
            "punch": {"scale": 1.08, "frames": 4}, "karaoke": karaoke}


# taste: sizes, outlines, plate, line height, pop and punch values are client choices.
STYLES = {
    "clean": _look("Clean", 64),
    "bold-pop": _look("Bold pop", 84, "upper", stroke="#000000",
                      start={"autoAlpha": 0, "scale": 0.7}, frames=5),
    "boxed": _look("Boxed", 60, plate="rgba(0,0,0,0.72)", start={"autoAlpha": 0, "scale": 0.9}),
    "karaoke": _look("Karaoke", 68, start={"autoAlpha": 0}, frames=3, karaoke=True),
    "outline-caps": _look("Outline caps", 76, "upper", stroke="accent", start={"autoAlpha": 0, "y": 20}),
}


class Stop(Exception):
    """Exit code and plain lines suitable for the client."""

    def __init__(self, code, *lines):
        super().__init__(lines[0] if lines else "")
        self.code, self.lines = code, lines


def _num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Stop(2, f"Cannot read {Path(path).name}: {e}. Make it again before planning captions.") from None


def pick_style(reel_dir_or_bm, bm=None, *, remember=True, style_reel=None):
    """Newest caption Send, then saved choice, then ask; accept legacy Beat Map dictionaries."""
    picker = {}
    reel = None
    if isinstance(reel_dir_or_bm, dict):
        bm = reel_dir_or_bm
    else:
        reel = Path(reel_dir_or_bm)
        bm = read_json(reel / SEND) if bm is None else bm
        if (reel / PICKER_SEND).is_file():
            picker = read_json(reel / PICKER_SEND)
        if not isinstance(picker, dict):
            raise Stop(2, "The Look Picker choice must be an object. Send it again.")
    if not isinstance(bm, dict):
        raise Stop(2, "The Beat Map Send must be an object. Send it again.")
    def sent_at(doc):
        value = doc.get("sent_at")
        if not value:  # Older Sends had no timestamp.
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError
            return stamp
        except (AttributeError, TypeError, ValueError):
            raise Stop(2, "A caption choice has no valid send time. Send it again.") from None
    if "caption_style" in picker and ("caption_style" not in bm or sent_at(picker) >= sent_at(bm)):
        cs = picker["caption_style"]
        if remember and isinstance(cs, dict) and cs.get("style") in (*STYLES, "none"):
            standing_notes.record_pick("caption_style.style", cs["style"])
        return picker["caption_style"], "picker"
    if "caption_style" in bm:
        cs = bm["caption_style"]
        if remember and isinstance(cs, dict) and cs.get("style") in (*STYLES, "none"):
            standing_notes.record_pick("caption_style.style", cs["style"])
        return bm["caption_style"], "reel"
    try:
        saved = saved_style.load(reel if style_reel is None else style_reel)
    except FileNotFoundError:
        saved = {}
    except (OSError, ValueError):
        raise Stop(2, "Cannot read the active saved style; save it again and try again.") from None
    _, source = saved_style.resolve("caption_style.style", saved=saved)
    if source == "recommended":
        raise Stop(1, ASK + saved_style.recommendation_line("caption_style.style", saved))
    if isinstance(saved, dict) and saved.get("caption_style") is not None:
        return saved["caption_style"], "saved"
    raise Stop(1, ASK)


def check_style(cs, source="reel", *, reel=None):
    """Fill taste options, or name the choice and the place that needs fixing."""
    where = {"reel": "the Beat Map Send's caption_style", "picker": "the Look Picker choice's caption_style",
             "saved": "the saved style's caption_style"}[source]
    fix = ("Fix caption_style in the Beat Map Send and try again." if source == "reel"
           else "Send the caption choice from the Look Picker again." if source == "picker"
           else "Fix caption_style in the active saved style and try again.")
    if not isinstance(cs, dict):
        raise Stop(2, f"{where} must be an object.", fix)
    bad = []
    unknown = set(cs) - {"style", *DEFAULTS}
    if unknown:
        bad.append(f"{where} has unknown options: {', '.join(sorted(unknown))}.")
    sid = cs.get("style")
    if not isinstance(sid, str) or sid not in (*STYLES, "none"):
        bad.append(f"{where}.style must be clean, bold-pop, boxed, karaoke, outline-caps or none.")
    filled = {**DEFAULTS, **cs}
    if "accent" not in cs:
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                saved = saved_style.load(reel)
        except (OSError, ValueError):
            saved = {}
        accent = saved.get("accent") if isinstance(saved, dict) else None
        if isinstance(accent, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
            filled["accent"] = accent
    if not isinstance(filled["accent"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", filled["accent"]):
        bad.append(f"{where}.accent must be a colour such as #FFD84D.")
    for key in ("under_small_overlays", "line_breaks", "echo_suppression", "loud_emphasis"):
        if not isinstance(filled[key], bool):
            bad.append(f"{where}.{key} must be true or false.")
    if filled["mark_look"] not in ("accent", "marker"):
        bad.append(f"{where}.mark_look must be accent or marker.")
    if not _num(filled["min_read_s"]) or filled["min_read_s"] < 0:
        bad.append(f"{where}.min_read_s must be a finite number of seconds, zero or more.")
    if bad:
        raise Stop(2, *bad, fix)
    return {"style": "none"} if sid == "none" else filled


def _rate(fps):
    try:
        if isinstance(fps, bool):
            raise ValueError
        rate = Fraction(str(fps))
        if rate <= 0:
            raise ValueError
        return rate
    except (ValueError, TypeError, ZeroDivisionError):
        raise Stop(2, "The frame rate must be a positive number. Fix work/cuts.json.") from None


def _word_input(words):
    if not isinstance(words, list):
        raise Stop(2, "The cut word list needs a words list. Make the cut word list again.")
    previous = -1
    for i, word in enumerate(words):
        if not (isinstance(word, dict) and isinstance(word.get("word"), str)
                and _num(word.get("start")) and _num(word.get("end"))
                and 0 <= word["start"] <= word["end"] and word["start"] >= previous):
            raise Stop(2, f"Cut word {i} needs text and ordered, nonnegative start/end seconds. Make the word list again.")
        previous = word["start"]


def _groups(words, rate, switches, line_breaks, protected=()):
    """Adapted chunk_words + auto_chunks; protected truthful runs are atomic."""
    positions = [i for i, w in enumerate(words) if w["word"].strip()]
    starts = {r["w0"]: r["w1"] for r in protected}
    inside = {i for r in protected for i in range(r["w0"], r["w1"])}
    out, current = [], []
    for j, i in enumerate(positions):
        w = words[i]
        boundary = current and any(round(words[current[0]]["start"] * rate) < f <= round(w["start"] * rate)
                                   for f in switches)
        size = sum(i <= p <= starts[i] for p in positions) if i in starts else 1
        if current and (boundary or len(current) + size > 3):
            out.append(current)
            current = []
        current.append(i)
        nxt = words[positions[j + 1]] if j + 1 < len(positions) else None
        dur = w["end"] - words[current[0]]["start"]
        close = (nxt is None or len(current) >= 3 or (len(current) >= 2 and dur >= 0.35)
                 or (line_breaks and (w["word"].rstrip()[-1] in ".,!?;:"
                                      or (nxt is not None and nxt["start"] - w["end"] >= 0.3))))
        if close and i not in inside:
            out.append(current)
            current = []
    return out


def _timed(words, groups, rate, switches, total_f):
    out, previous = [], 0
    for j, group in enumerate(groups):
        start = max(previous, round(words[group[0]]["start"] * rate))
        nxt = round(words[groups[j + 1][0]]["start"] * rate) if j + 1 < len(groups) else total_f
        switch = next((f for f in switches if f > start), total_f)
        end = min(nxt, round((words[group[-1]]["end"] + 0.3) * rate), switch, total_f)
        if end <= start or any(round(words[i]["start"] * rate) >= end for i in group):
            raise Stop(2, f"Caption at word {group[0]} has no whole frame available. Fix the word times or cut length.")
        out.append({"w0": group[0], "w1": group[-1], "start_f": start, "end_f": end})
        previous = end
    return out


def chunk(words, fps, switch_f, total_f, line_breaks=True):
    """Inclusive word-list ranges; exclusive end frames, never across a switch."""
    _word_input(words)
    rate = _rate(fps)
    if not _int(total_f) or total_f <= 0 or not isinstance(line_breaks, bool):
        raise Stop(2, "The cut needs a positive whole-frame length and line_breaks must be true or false.")
    if not all(_int(f) and 0 <= f <= total_f for f in switch_f):
        raise Stop(2, "Layout switches must be whole frames inside the cut.")
    switches = sorted(set(switch_f))
    return _timed(words, _groups(words, rate, switches, line_breaks), rate, switches, total_f)


def _mark_runs(words, candidates):
    """Expand through the shared rule; merge adjacent equal candidates before expansion."""
    tokens = [w["word"] if isinstance(w, dict) else w for w in words]
    if not all(isinstance(w, str) for w in tokens) or not isinstance(candidates, list):
        raise Stop(2, "Word marks need a word list and a list of {w, mark} choices in the Beat Map Send.")
    seen, initial = set(), []
    for c in candidates:
        if not (isinstance(c, dict) and set(c) == {"w", "mark"} and _int(c["w"])
                and 0 <= c["w"] < len(tokens) and c["mark"] in beat_schema.MARKS and c["w"] not in seen
                and tokens[c["w"]].strip()):
            raise Stop(2, "Fix word_marks in the Beat Map Send: use unique word positions and num, key, emph or cta.")
        seen.add(c["w"])
    sentence, n = [], 0
    for word in tokens:
        sentence.append(n)
        n += word.rstrip().endswith((".", "!", "?"))
    for c in sorted(candidates, key=lambda c: c["w"]):
        if (initial and initial[-1]["w1"] + 1 == c["w"] and initial[-1]["mark"] == c["mark"]
                and sentence[initial[-1]["w1"]] == sentence[c["w"]]):
            initial[-1]["w1"] = c["w"]
        else:
            initial.append({"w0": c["w"], "w1": c["w"], "mark": c["mark"]})
    # tokenize can split one transcript word (e.g. an em dash). Map back without renumbering.
    flat, owners, bounds = [], [], []
    for i, word in enumerate(tokens):
        start = len(flat)
        parts = tokenize(word)
        flat.extend(parts)
        owners.extend([i] * len(parts))
        bounds.append((start, len(flat)))
    expanded = []
    for run in initial:
        if bounds[run["w0"]][0] == bounds[run["w1"]][1]:
            raise Stop(2, "A word mark has no spoken word. Choose words in the Beat Map Send, not a dash alone.")
        a, e = truthful_span(flat, bounds[run["w0"]][0], bounds[run["w1"]][1])
        expanded.append({"w0": owners[a], "w1": owners[e - 1], "mark": run["mark"]})
    runs = []
    for run in sorted(expanded, key=lambda r: (r["w0"], r["w1"])):
        if runs and run["w0"] <= runs[-1]["w1"]:
            if run["mark"] != runs[-1]["mark"]:
                raise Stop(2, "Truthful word marks overlap with different accents. Pick one mark for that phrase in the Beat Map Send.")
            runs[-1]["w1"] = max(run["w1"], runs[-1]["w1"])
        else:
            runs.append(dict(run))
    punches, notes, used = set(), [], set()
    for i, run in enumerate(runs):
        if run["mark"] in ("key", "emph"):
            sent = sentence[run["w0"]]
            if sent in used:
                notes.append(f"Words {run['w0']}-{run['w1']} keep their accent; only one punch is used per sentence.")
            else:
                used.add(sent)
                punches.add(i)
    return runs, punches, notes


def pick_marks(words, candidates):
    """Inclusive truthful runs. Later stress runs retain accents; plan() limits punches."""
    return _mark_runs(words, candidates)[0]


def suggest_loud(reel_dir, words, notes=None):
    """Suggest candidates from source peaks; the caller still applies the shared truthful-span rule."""
    note = "No loudness suggestions are available; make the cut and measure its sound first."
    try:
        reel = Path(reel_dir)
        env = read_json(reel / "work/envelope.json")
        cuts = read_json(reel / "work/cuts.json")
        rate, speed = float(_rate(cuts["fps"])), cuts["speed"]
        win, db, segments = env["win_s"], env["db"], cuts["segments"]
        if not (_num(speed) and speed > 0 and _num(win) and win > 0
                and isinstance(db, list) and db and all(_num(v) for v in db)
                and isinstance(segments, list) and segments):
            raise ValueError
        previous = 0
        for seg in segments:
            if not (all(_int(seg[k]) for k in ("out_in_f", "out_out_f", "src_in_f", "src_out_f"))
                    and seg["out_in_f"] == previous < seg["out_out_f"]
                    and 0 <= seg["src_in_f"] < seg["src_out_f"]):
                raise ValueError
            previous = seg["out_out_f"]
        peaks = []
        for i, word in enumerate(words):
            if not word["word"].strip():
                continue
            samples, covered = [], 0
            for seg in segments:
                a = max(word["start"], seg["out_in_f"] / rate)
                b = min(word["end"], seg["out_out_f"] / rate)
                if b <= a:
                    continue
                covered += b - a
                src_a = seg["src_in_f"] / rate + (a - seg["out_in_f"] / rate) * speed
                src_b = min(seg["src_out_f"] / rate,
                            seg["src_in_f"] / rate + (b - seg["out_in_f"] / rate) * speed)
                lo, hi = math.floor(src_a / win + 1e-9), math.ceil(src_b / win - 1e-9)
                if src_b <= src_a or lo < 0 or hi > len(db):
                    raise ValueError
                samples.extend(db[lo:hi])
            if not samples or covered + 1e-6 < word["end"] - word["start"]:
                raise ValueError
            peaks.append((i, max(samples)))
        if not peaks:
            return []
        median = statistics.median(peak for _, peak in peaks)
        return [{"w": i, "mark": "emph"} for i, peak in peaks if peak >= median + 6]  # taste: 6 dB
    except (Stop, KeyError, TypeError, ValueError, OverflowError):
        if notes is None:
            print(note, file=sys.stderr)
        else:
            notes.append(note)
        return []


def _beats(bm, total):
    beats = bm.get("beats", [])
    if not isinstance(beats, list):
        raise Stop(2, "The Beat Map Send needs a beats list. Send it again.")
    for beat in beats:
        if not (isinstance(beat, dict) and _int(beat.get("start_f")) and _int(beat.get("end_f"))
                and 0 <= beat["start_f"] < beat["end_f"] <= total and beat.get("layout") in beat_schema.LAYOUTS):
            raise Stop(2, "A beat needs a layout and whole start/end frames inside the cut. Fix the Beat Map Send.")
        scene = beat.get("scene")
        if scene is not None:
            if not (isinstance(scene, dict) and isinstance(scene.get("id"), str)
                    and re.fullmatch(r"[a-z0-9][a-z0-9-]*", scene["id"])
                    and isinstance(scene.get("slots", {}), dict)):
                raise Stop(2, "A scene needs its scene name and slot text. Fix the Beat Map Send.")
    return sorted(beats, key=lambda b: b["start_f"])


def _slot_tokens(value):
    if isinstance(value, dict):
        return [token for v in value.values() for token in _slot_tokens(v)]
    if isinstance(value, list):
        return [token for v in value for token in _slot_tokens(v)]
    return re.findall(r"[\w']+", str(value).casefold())


def _brand_font(notes, reel):
    """Use scenes' declared faces and shipped, licensed runtime/fonts files."""
    fallback = {"family": "Inter", "src": "./fonts/Inter-Regular.woff2"}
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            saved = saved_style.load(reel)
    except (OSError, ValueError):
        return fallback
    font = saved.get("font") if isinstance(saved, dict) else None
    if not font:
        return fallback
    if isinstance(font, str) and font.strip():
        for scene in sorted(scene_check.SCENES.glob("*/scene.html")):
            try:
                urls = scene_check.font_faces(scene.read_text(encoding="utf-8")).get(font, [])
                files = [(scene_check.FONTS / u[len("./fonts/"):]).resolve() for u in urls]
                if urls and all(u.startswith("./fonts/")
                                and f.is_relative_to(scene_check.FONTS.resolve()) and f.is_file()
                                and f.suffix.lower() in scene_check.FONT_EXT for u, f in zip(urls, files)):
                    return {"family": font, "src": urls[0]}
            except (OSError, ValueError):
                continue
    notes.append(f"Your brand font {font} isn't available for captions yet, so they use Inter.")
    return fallback


def plan(reel_dir, fps=None, *, _style=None, style_reel=None):
    """Read the Send, words, cuts and saved style; return a plan without writing."""
    reel = Path(reel_dir)
    style_reel = reel if style_reel is None else style_reel
    bm = read_json(reel / SEND)
    cs, source = pick_style(reel, bm, style_reel=style_reel) if _style is None else (_style, "picker")
    cs = check_style(cs, source, reel=style_reel)
    word_doc = read_json(reel / DEFAULT_WORDS)
    words = word_doc.get("words") if isinstance(word_doc, dict) else None
    _word_input(words)
    cuts = read_json(reel / "work/cuts.json")
    segs = cuts.get("segments") if isinstance(cuts, dict) else None
    if not (isinstance(segs, list) and segs and all(
            isinstance(g, dict) and _int(g.get("out_in_f")) and _int(g.get("out_out_f"))
            and 0 <= g["out_in_f"] < g["out_out_f"] for g in segs)
            and all(a["out_out_f"] == b["out_in_f"] for a, b in zip(segs, segs[1:]))):
        raise Stop(2, "The cut list needs ordered output-frame segments. Make work/cuts.json again.")
    rate = _rate(cuts.get("fps") if fps is None else fps)
    total = segs[-1]["out_out_f"]
    doc = {"schema": 1, "style": cs, "chunks": [], "declared_drops": [], "notes": []}
    if cs["style"] == "none":
        doc["declared_drops"] = [{"w": i, "why": "captions off"} for i in range(len(words))]
        return doc
    doc["font"] = _brand_font(doc["notes"], style_reel)
    beats = _beats(bm, total)
    switches = sorted({b["start_f"] for a, b in zip(beats, beats[1:]) if a["layout"] != b["layout"]})
    candidates = bm.get("word_marks", [])
    if not isinstance(candidates, list):
        raise Stop(2, "Word marks need a list of choices in the Beat Map Send. Send it again.")
    if cs["loud_emphasis"] and not candidates:
        candidates = suggest_loud(reel, words, doc["notes"])
        if candidates:
            doc["notes"].append("Loudness suggestions supply the word marks; review the stressed phrases before rendering.")
    runs, punches, notes = _mark_runs(words, candidates)
    doc["notes"].extend(notes)
    def fits(run):  # lane fix: a truthful run must fit one caption; else its stress is left off (a note, no stop)
        positions = [i for i in range(run["w0"], run["w1"] + 1) if words[i]["word"].strip()]
        return len(positions) <= 3 and not any(round(words[positions[0]]["start"] * rate) < f <=
                                               round(words[positions[-1]]["start"] * rate) for f in switches)
    kept = [i for i, run in enumerate(runs) if fits(run)]
    for i, run in enumerate(runs):
        if i not in kept:
            said = " ".join(words[w]["word"].strip() for w in range(run["w0"], run["w1"] + 1))
            doc["notes"].append(f"The stress on \"{said}\" was left off: the whole true phrase doesn't fit one "
                                f"caption. Mark a shorter true phrase on the Beat Map if you want it stressed.")
    punches = {i for i in punches if i in kept}
    runs = {i: runs[i] for i in kept}
    # First validate public chunk inputs, then regroup only where a truthful mark needs it.
    chunks = chunk(words, rate, switches, total, cs["line_breaks"])
    if runs:
        chunks = _timed(words, _groups(words, rate, switches, cs["line_breaks"], list(runs.values())), rate,
                        switches, total)
    marks = {w: (run["mark"], i in punches) for i, run in runs.items()
             for w in range(run["w0"], run["w1"] + 1)}
    run_ids = {w: i for i, run in runs.items() for w in range(run["w0"], run["w1"] + 1)}
    doc["declared_drops"] = [{"w": i, "why": "empty"} for i, w in enumerate(words) if not w["word"].strip()]
    kinds = {}
    for c in chunks:
        positions = [i for i in range(c["w0"], c["w1"] + 1) if words[i]["word"].strip()]
        why = None
        for beat in beats:
            scene = beat.get("scene")
            if not scene or not (beat["start_f"] < c["end_f"] and c["start_f"] < beat["end_f"]):
                continue
            if not cs["under_small_overlays"]:
                sid = scene["id"]
                if sid not in kinds:
                    scene_doc = read_json(scene_check.SCENES / sid / "scene.json")
                    if not isinstance(scene_doc, dict) or scene_doc.get("kind") not in ("overlay", "takeover"):
                        raise Stop(2, f"The {sid} scene has no valid kind. Fix its scene.json.")
                    kinds[sid] = scene_doc["kind"]
                if kinds[sid] == "overlay":
                    why = "overlay"
                    break
            if (cs["echo_suppression"] and beat["start_f"] <= c["start_f"] and c["end_f"] <= beat["end_f"]
                    and set(_slot_tokens(" ".join(words[i]["word"] for i in positions)))
                    <= set(_slot_tokens(scene.get("slots", {})))):
                why = "echo"
        if why:
            doc["declared_drops"].extend({"w": i, "why": why} for i in positions)
            continue
        entries = []
        for i in positions:
            mark, punch = marks.get(i, (None, False))
            text = words[i]["word"].strip()
            if STYLES[cs["style"]]["case"] == "upper":
                text = text.upper()
            entries.append({"w": i, "text": text, "start_f": max(c["start_f"], round(words[i]["start"] * rate)),
                            "mark": mark, "punch": punch, "run": run_ids.get(i)})
        item = {"i": len(doc["chunks"]), **c, "text": " ".join(w["text"] for w in entries), "words": entries}
        doc["chunks"].append(item)
        if Fraction(c["end_f"] - c["start_f"], 1) / rate < cs["min_read_s"]:
            doc["notes"].append(f"Caption {item['i']} is short to read; consider a longer hold if you prefer.")
    doc["declared_drops"].sort(key=lambda d: d["w"])
    return doc


def band_h(spec):
    """One text line plus plate/shadow and the full pop/punch envelope, in master pixels."""
    # taste: 16 px padding on each edge, 4 px outline, full punch clearance.
    return math.ceil(spec["size"] * spec["line_h"] * spec["punch"]["scale"] + 32 + 8
                     + abs(spec["pop"]["from"].get("y", 0)))


def _js(values):
    return "{" + ", ".join(f"{key}: {json.dumps(value)}" for key, value in values.items()) + "}"


def text_width_em(text):
    """Inter-based advances, approximate for brand fonts; the placer's 8 px margin absorbs it.

    Retain the old 0.6 em estimate for missing glyphs and the same fit rule for every font.
    """
    try:
        table = json.loads(CHAR_WIDTHS.read_text(encoding="utf-8"))
        units, widths = table["units_per_em"], table["widths"]
        if not _num(units) or units <= 0 or not isinstance(widths, dict):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        units, widths = 1000, {}
    return sum(widths[ch] / units if ch in widths and _num(widths[ch]) and widths[ch] >= 0 else 0.6
               for ch in text) or 0.6


def layer(doc, boxes, s, t):
    """Return (CSS string, layer lines, root-timeline lines); append fitting notes to doc.

    boxes are frozen placer corner tuples (x0,y0,x1,y1); caller forwards the
    placer's notes into doc['notes']. No placement fallback ever removes a chunk.
    t maps a whole frame to compose's seconds string, including for durations.
    """
    if doc["style"]["style"] == "none":
        return "", [], []
    spec = STYLES[doc["style"]["style"]]
    accent = doc["style"]["accent"]
    marker = doc["style"].get("mark_look", "accent") == "marker"
    # taste: soft shadow, 3 px outline and 16 px rounded plate corners.
    stroke = accent if spec["stroke"] == "accent" else spec["stroke"]
    font = doc.get("font", {"family": "Inter", "src": "./fonts/Inter-Regular.woff2"})
    family = json.dumps(font["family"], ensure_ascii=False)
    stack = family + ', "Inter"' if font["family"] != "Inter" else family
    # compose copies the same runtime/fonts tree, including this face, next to Inter.
    brand_face = (f'@font-face {{font-family: {family}; src: url({json.dumps(font["src"], ensure_ascii=False)}); font-weight: 400;}}\n'
                  if font["family"] != "Inter" else '')
    css = ('@font-face {font-family: "Inter"; src: url("fonts/Inter-Regular.woff2") format("woff2"); font-weight: 400;}\n'
           + brand_face
           + '#captions .caption {position: absolute; '
           + f'font-family: {stack}; font-weight: 400; font-synthesis: none; '
           f'color: {spec["color"]}; line-height: {spec["line_h"]}; white-space: nowrap; text-align: center; '
           f'text-shadow: 0 {2*s:g}px {6*s:g}px rgba(0,0,0,0.65); '
           + (f'-webkit-text-stroke: {3*s:g}px {stroke}; paint-order: stroke fill; ' if stroke else '')
           + (f'background: {spec["plate"]}; border-radius: {16*s:g}px; ' if spec["plate"] else '')
           + f'padding: {16*s:g}px; box-sizing: border-box;}}\n'
           '#captions .cap-word, #captions .cap-punch, #captions .cap-marker {display: inline-block;}\n'
           '#captions .cap-marker {position: relative; isolation: isolate;}\n'
           '#captions .cap-marker .cap-word {position: relative; z-index: 1;}\n'
           f'#captions .cap-marker-swipe {{position: absolute; left: 0; right: 0; top: 16%; height: 72%; '
           f'background: {accent}; opacity: 0.38; transform: scaleX(0); transform-origin: left center; z-index: 0;}}\n'
           + ('' if marker else f'#captions .marked {{color: {accent};}}\n')
           + ('#captions .cap-word {opacity: 0.55;}\n' if spec["karaoke"] else ''))
    layers, tl = ['<div class="band" id="captions" style="z-index: 600">'], []
    for c in doc["chunks"]:
        box = boxes[c["i"]]
        x0, y0, x1, y1 = box
        if not (s > 0 and x1 > x0 and y1 > y0):
            raise Stop(2, "A caption needs a positive-size box and output scale. Place it again.")
        # Reserve plate and punch space around measured character advances.
        pad = min(16, (x1 - x0) / 8)  # taste: reduce plate padding for very narrow boxes
        size = min(spec["size"], (x1 - x0 - 2 * pad) / (text_width_em(c["text"]) * spec["punch"]["scale"]))
        if size < spec["size"]:
            note = f"Caption {c['i']} uses a smaller font to fit its safe spot."
            if note not in doc["notes"]:
                doc["notes"].append(note)
        spans, punched, swipes = [], [], []
        group, marked_run = False, False
        for j, w in enumerate(c["words"]):
            prev = c["words"][j - 1] if j else None
            same_run = (prev is not None and w["mark"] and prev["mark"] == w["mark"]
                        and prev.get("run") == w.get("run") and prev["punch"] == w["punch"])
            if marked_run and not same_run:
                spans.append('</span>')
                marked_run = False
            if group and (not w["punch"] or not same_run):
                spans.append('</span>')
                group = False
            if w["punch"] and not group:
                pid = f"cap-{c['i']}-punch-{j}"
                spans.append(f'<span class="cap-punch" id="{pid}">')
                punched.append((pid, w["start_f"]))
                group = True
            if marker and w["mark"] and not marked_run:
                mid = f"cap-{c['i']}-marker-{j}"
                spans.append(f'<span class="cap-marker"><span class="cap-marker-swipe" id="{mid}"></span>')
                swipes.append((mid, w["start_f"]))
                marked_run = True
            wid = f"cap-{c['i']}-w-{w['w']}"
            classes = "cap-word marked" if w["mark"] else "cap-word"
            spans.append(f'<span class="{classes}" id="{wid}">{html.escape(w["text"])}</span>')
            nxt = c["words"][j + 1] if j + 1 < len(c["words"]) else None
            if marked_run and (nxt is None or not nxt["mark"] or nxt["mark"] != w["mark"]
                               or nxt.get("run") != w.get("run") or nxt["punch"] != w["punch"]):
                spans.append('</span>')
                marked_run = False
            if group and (nxt is None or not nxt["punch"] or nxt.get("run") != w.get("run")):
                spans.append('</span>')
                group = False
            if nxt is not None:
                spans.append(" ")
        if group:
            spans.append('</span>')
        layers.append(f'<div class="caption" id="cap-{c["i"]}" style="left: {(x0+x1)/2*s:g}px; '
                      f'top: {y0*s:g}px; font-size: {size*s:g}px; padding: {pad*s:g}px; visibility: hidden">{"".join(spans)}</div>')
        el = f'"#cap-{c["i"]}"'
        tl.append(f'tl.set({el}, {{xPercent: -50, autoAlpha: 0, immediateRender: true}}, 0);')  # lane fix: lint's set-at-0 rule
        target = dict(spec["pop"]["to"])
        if c["start_f"] == 0:
            tl.append(f'tl.set({el}, {_js(target)[:-1]}, immediateRender: true}}, {t(0)});')
        else:
            frames = min(spec["pop"]["frames"], c["end_f"] - c["start_f"])
            start = {key: value * s if key == "y" else value for key, value in spec["pop"]["from"].items()}
            props = _js(target)[:-1] + f', duration: {t(frames)}, ease: "{spec["pop"]["ease"]}", immediateRender: false}}'
            tl.append(f'tl.fromTo({el}, {_js(start)}, {props}, {t(c["start_f"])});')
        for pid, start_f in punched:
            frames = min(spec["punch"]["frames"], c["end_f"] - start_f)
            if frames > 0:
                tl.append(f'tl.fromTo("#{pid}", {{scale: {spec["punch"]["scale"]}}}, '
                          f'{{scale: 1, duration: {t(frames)}, ease: "power2.out", immediateRender: false}}, {t(start_f)});')
        for mid, start_f in swipes:
            if start_f == 0:
                tl.append(f'tl.set("#{mid}", {{scaleX: 1, transformOrigin: "left center", immediateRender: true}}, {t(0)});')
            else:
                frames = min(spec["pop"]["frames"], c["end_f"] - start_f)
                tl.append(f'tl.fromTo("#{mid}", {{scaleX: 0, transformOrigin: "left center"}}, '
                          f'{{scaleX: 1, duration: {t(frames)}, ease: "power2.out", immediateRender: false}}, {t(start_f)});')
        if spec["karaoke"]:
            for j, w in enumerate(c["words"]):
                if j:
                    prev = c["words"][j - 1]
                    color = accent if prev["mark"] else spec["color"]
                    tl.append(f'tl.set("#cap-{c["i"]}-w-{prev["w"]}", {{opacity: 0.55, color: "{color}"}}, {t(w["start_f"])});')
                tl.append(f'tl.set("#cap-{c["i"]}-w-{w["w"]}", {{opacity: 1, color: "{accent}"}}, {t(w["start_f"])});')
        tl.append(f'tl.set({el}, {{autoAlpha: 0}}, {t(c["end_f"])});')
    layers.append('</div>')
    return css, layers, tl


def picker_times(reel_dir):
    """Sample each layout's first beat, or a quarter of the cut when it isn't used."""
    reel = Path(reel_dir)
    cuts, bm = read_json(reel / "work/cuts.json"), read_json(reel / SEND)
    rate = _rate(cuts["fps"])
    total = cuts["segments"][-1]["out_out_f"]
    beats = _beats(bm, total)
    return {name: float(Fraction(next(((b["start_f"] + b["end_f"]) / 2 for b in beats
                                      if b["layout"] == name), total / 4)) / rate)
            for name in beat_schema.LAYOUTS}


def picker_doc(reel_dir):
    """Build the shared picker document without grabbing frames or writing anything."""
    import compose  # lazy: the picker reuses the compositor's layout contract
    import placer
    reel = Path(reel_dir)
    saved = saved_style.load(reel)
    _, source = saved_style.resolve("caption_style.style", saved=saved)
    recommended = saved_style.recommendation("caption_style.style", saved) if source == "recommended" else None
    try:
        current, source = pick_style(reel)
        checked = check_style(current, source, reel=reel)
    except Stop as exc:
        if exc.code != 1:
            raise
        current, checked = None, {}
    # A neutral card look is only a preview; an unset choice stays unset, including 'none'.
    preview_style = {**checked, "style": "clean", "under_small_overlays": True, "echo_suppression": False}
    planned = plan(reel, _style=preview_style)
    if not planned["chunks"]:
        raise Stop(2, "The cut needs spoken words before you can preview caption looks.")
    sample = next((c for c in planned["chunks"] if any(w["mark"] for w in c["words"])), planned["chunks"][0])
    rate = _rate(read_json(reel / "work/cuts.json")["fps"])
    notes, looks = list(planned["notes"]), {}
    ctx = None
    if (reel / "work/scale_track.json").is_file():
        try:
            ctx = placer.load_ctx(reel)
        except ValueError as exc:
            raise Stop(2, str(exc)) from None
    else:
        notes.append("No placement track is ready; using the lowest safe caption spot. Check it against the speaker.")
    for sid, spec in STYLES.items():
        c = {**sample, "i": 0, "words": [dict(w, text=w["text"].upper() if spec["case"] == "upper" else w["text"])
                                       for w in sample["words"]]}
        c["text"] = " ".join(w["text"] for w in c["words"])
        height = band_h(spec)
        try:
            if ctx is None:
                x0, _, x1, bottom = placer.SAFE
                box = (x0, bottom - height, x1, bottom)
            else:
                box = placer.place(ctx, c["start_f"], c["end_f"] - 1, height)
        except (ValueError, placer.NoRoom) as exc:
            raise Stop(2, str(exc)) from None
        variants, sheets = {}, []
        for mode in ("accent", "marker"):
            doc = {"style": check_style({**preview_style, "style": sid, "mark_look": mode}, reel=reel),
                   "chunks": [c], "notes": notes}
            css, markup, _ = layer(doc, [box], 1, lambda f: str(float(Fraction(f) / rate)))
            # The board owns the animation; supply a visible, centred caption and settled marker.
            variants[mode] = "".join(markup[1:-1]).replace("visibility: hidden", "visibility: visible; transform: translateX(-50%)")
            sheets.append(css)
        # Scope both mark variants within their caption so one card's CSS cannot recolour another.
        css = sheets[0].replace('#captions .marked', '#captions .caption:not(.marker-mode) .marked')
        variants["marker"] = variants["marker"].replace('class="caption"', 'class="caption marker-mode"')
        variants["marker"] = variants["marker"].replace('class="cap-marker-swipe"', 'class="cap-marker-swipe" style="transform: scaleX(1)"')
        looks[sid] = {"label": spec["label"], "css": css, "html": variants,
                      "pop": {"from": dict(spec["pop"]["from"]), "to": dict(spec["pop"]["to"]),
                              "seconds": float(spec["pop"]["frames"] / rate), "ease": spec["pop"]["ease"]},
                      "punch": {"scale": spec["punch"]["scale"], "seconds": float(spec["punch"]["frames"] / rate)}}
    if ctx is not None:
        notes.extend(n for n in ctx["notes"] if n not in notes)
    tips = [line.removeprefix("- Suggestion: ").strip()
            for line in (HERE.parent / "references/looks.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("- Suggestion: ")]
    return {"schema": 1, "reel": reel.name, "fps": float(rate),
            "frames": {name: f"work/look-picker/frame-{name}.jpg" for name in beat_schema.LAYOUTS},
            "layouts": {name: compose.layout(name, 1) for name in beat_schema.LAYOUTS},
            "sample": {"text": sample["text"], "words": sample["words"]}, "looks": looks,
            "options": {**DEFAULTS, "mark_look": ["accent", "marker"]}, "current": current,
            "recommended": recommended,
            "tips": tips, "notes": notes}


def picker(reel_dir):
    """Write the client's cut stills and the board's document; never save a style choice."""
    reel = Path(reel_dir)
    if not (reel / "work/cuts.json").is_file():
        raise Stop(2, "make the cut first")
    cuts = read_json(reel / "work/cuts.json")
    speed = cuts.get("speed") if isinstance(cuts, dict) else None
    if not _num(speed) or speed <= 0:
        raise Stop(2, "make the cut first")
    master = reel / "work/renders" / ("master-" + ("%.2fx" % speed).replace(".", "") + ".mp4")
    if not master.is_file():
        raise Stop(2, "make the cut first")
    doc = picker_doc(reel)
    times = picker_times(reel)
    (reel / "work/look-picker").mkdir(parents=True, exist_ok=True)
    for name, seconds in times.items():
        try:
            result = subprocess.run([rt.tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{seconds:.6f}",
                                     "-i", str(master), "-frames:v", "1", "-q:v", "2", "-update", "1",
                                     str(reel / doc["frames"][name])], capture_output=True, text=True)
        except (OSError, RuntimeError, KeyError):
            raise Stop(2, "The preview pictures could not be made. Check the video tools and try again.") from None
        if result.returncode:
            raise Stop(2, "The preview pictures could not be made. Make the cut again and retry.")
    # lane fix: the board loads the licensed Inter from here (FontFace), never an embedded copy
    shutil.copy2(HERE.parents[2] / "runtime/fonts/Inter-Regular.woff2", reel / "work/look-picker/Inter-Regular.woff2")
    (reel / "work/look-picker.json").write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return doc


def write(reel_dir, doc):
    path = Path(reel_dir) / "work/captions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return path


def selftest():
    import tempfile
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as home, patch.object(rt, "state_dir", return_value=Path(home)):
        assert check_style({"style": "clean"})["accent"] == "#FFD84D"
    assert pick_marks(["this", "doesn't", "work."], [{"w": 2, "mark": "emph"}]) == [
        {"w0": 1, "w1": 2, "mark": "emph"}]
    words = [{"word": text, "start": i / 10, "end": i / 10 + 0.08}
             for i, text in enumerate(("a", "new", "look"))]
    chunks = chunk(words, 30, [3], 30)
    assert [(c["w0"], c["w1"]) for c in chunks] == [(0, 0), (1, 2)]
    assert all(not c["start_f"] < 3 < c["end_f"] for c in chunks)
    try:
        check_style({"style": "guess", "accent": "#FFD84D"})
    except Stop as e:
        assert e.code == 2
    else:
        raise AssertionError("Unknown style must stop")
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Plan the reel's burned-in captions or propose truthful word marks.")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan", help="save the caption plan")
    p.add_argument("--reel-dir", required=True)
    m = sub.add_parser("marks", help="print truthful marks for the Beat Map Send")
    m.add_argument("--reel-dir", required=True)
    m.add_argument("--candidates", default="[]", help="JSON list of {w, mark}")
    m.add_argument("--loud", action="store_true", help="also suggest marks from louder words")
    p = sub.add_parser("picker", help="prepare the Look Picker pictures and caption cards")
    p.add_argument("--reel-dir", required=True)
    a = ap.parse_args(argv)
    try:
        if a.selftest:
            return selftest()
        if a.cmd == "picker":
            picker(a.reel_dir)
            print("The caption looks are ready to compare in the Look Picker.")
            return 0
        if a.cmd == "plan":
            doc = plan(a.reel_dir)
            write(a.reel_dir, doc)
            label = "No captions" if doc["style"]["style"] == "none" else STYLES[doc["style"]["style"]]["label"]
            print(f"{label}: {len(doc['chunks'])} captions planned; {len(doc['declared_drops'])} words left off.")
            for note in doc["notes"]:
                print(note)
            return 0
        if a.cmd == "marks":
            try:
                candidates = json.loads(a.candidates)
            except ValueError:
                raise Stop(2, "The candidate marks must be a JSON list of {w, mark} choices.") from None
            words = read_json(Path(a.reel_dir) / DEFAULT_WORDS)
            items = words.get("words") if isinstance(words, dict) else None
            _word_input(items)
            if a.loud:
                _mark_runs(items, candidates)  # Validate explicit choices before combining suggestions.
                loud = suggest_loud(a.reel_dir, items)
                chosen = {c["w"] for c in candidates}
                candidates += [c for c in loud if c["w"] not in chosen]
            runs, _, notes = _mark_runs(items, candidates)
            for note in notes:
                print(note, file=sys.stderr)
            print(json.dumps([{"w": w, "mark": r["mark"]} for r in runs
                              for w in range(r["w0"], r["w1"] + 1) if items[w]["word"].strip()], ensure_ascii=False))
            return 0
        ap.print_help()
        return 2
    except Stop as e:
        print("\n".join(e.lines))
        return e.code


if __name__ == "__main__":
    sys.exit(main())
