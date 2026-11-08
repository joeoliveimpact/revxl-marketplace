"""The editing-style planner (S6c): turn the client's editing style into a frame-exact plan for the a-roll.

  styles.py plan --reel-dir videos/<reel>   writes videos/<reel>/work/scale_track.json
  styles.py --selftest                      the rules below, on small made-up reels (no video, no tools)
Exit 0 done, 1 stopped by a check (the plain lines say why), 2 bad or missing input. The last stdout line of a
plan is one JSON summary {style, keys, tweens, warnings} (counts).

What it reads: the Beat Map Send (beat-map-selection.json: beats, word marks, edit_style), the cut's word list
(work/edit_map.cut.json, word start times in seconds of the cut), the cut list (work/cuts.json: the segments in
output frames) and, when the face step has run, work/anchors.json (head-band centres per segment,
as fractions of the frame). The frame rate is the cut master's own (work/renders/master-<tag>.mp4, read the way
compose.py reads it, and it must match the cut list's within 0.001); compose.py passes the rate it already read.
The style comes from the Send's edit_style, else the saved style's edit_style
(<state>/styles/default.json), else it stops and asks the client which style they want.
What it writes: work/scale_track.json: keys (the whole a-roll state on each frame where something is set hard),
tweens (eased moves) and their effect-gate spans. compose.py and the caption step read it.

The rules, in plain words:
- Every key and every move starts AND ends on a whole output frame. A word punch starts 0.05 s before its word.
- Punch-in style: the a-roll alternates full size and the punch level from cut to cut (segment 0 is full size);
  each change is a hard set on the cut frame, never a move.
- Word punches (an option): at most one per sentence (later picks in the sentence are dropped with a note).
  The punch multiplies the segment's size; it is never capped. A punch stays inside its segment: it starts no
  earlier than the segment's first frame and is back by its last frame (the hold shrinks first, then the way
  back; if even the way in doesn't fit, the punch is dropped with a note).
- Opening settle (an option): the reel opens slightly pushed in and settles to its size over 0.6 s.
- Follow-cam (an option): the zoom centre follows the head inside each segment and starts over at each cut.
- Ratchets (an option): two to four hard up-steps and a hard return; one sentence's punch event.
- Push and Ken Burns (options): scale across one shot; the drift also moves the zoom centre.
- Reframe (an option): pin an edge while zooming. Drift and reframe own the centre, so follow-cam gives way.
- The zoom centre of each segment is its first head sample, else a default near the eyes; set on the cut frame.
- Layout-switch style: each beat's layout; a change on a cut frame is a hard set, a change between cuts is a
  0.6 s move that stays inside its segment. The moves above belong to the punch-in style only.
- Two moves on the same property that touch or overlap become one smooth gesture.
- A size above the measured softness ceiling (references/tuning.json) gets a note, never a cap.
- Every move goes through the effect gate (VES-1); a problem stops the plan and nothing is written.
"""
import argparse
import bisect
import json
import os
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import saved_style  # noqa: E402
import standing_notes  # noqa: E402
import beat_schema  # noqa: E402
import effect_gate  # noqa: E402
import fps as fpsmod  # noqa: E402

SEND = "beat-map-selection.json"
TRACK = "work/scale_track.json"
ANCHORS = "work/anchors.json"
TUNING = SKILL / "references" / "tuning.json"  # S6c.4 writes it; absent = no ceiling check yet
ASK = "ask: which editing style? punch-ins on jump cuts, or layout switches"
STYLES = ("punch-in", "layout-switch")
STYLE_KEYS = ("style", "punch_scale", "moves")
CAMERA_MOVES = ("push", "ken_burns", "reframe")
MOVE_NAMES = {"push": "slow push", "ken_burns": "Ken Burns", "reframe": "reframe", "ratchet": "ratchet"}
MOVES = ("opening_settle", "follow_cam", "word_punches", "ratchet", *CAMERA_MOVES)
PUNCH_KEYS = ("preset", "shape", "picks")
SHAPES = ("eased", "hard-cut")
PUNCH_SCALE = 1.12             # taste: the suggested jump-cut punch level
ORIGIN = (0.5, 0.38)           # the zoom centre when a segment has no head sample
ONSET_LEAD = Fraction(1, 20)   # A2: a word punch starts 0.05 s before its word
SETTLE, SETTLE_S = 1.06, 0.6   # taste: the opening settle
MOVE_S = 0.6                   # taste: a layout move between cuts
RATCHET_STEP = 0.08            # taste: each step adds this fraction of the segment's scale
RATCHET_STEP_S = 0.2           # taste: time between hard up-steps
RATCHET_HOLD_S = 0.3           # taste: time at the top step before the hard return
PUSH_TO = 1.06                # taste: the slow linear push's scale multiplier
KB_TO = 1.08                  # taste: the slow drift's scale multiplier
KB_PAN = 0.04                 # taste: horizontal travel to each side of the zoom centre
END = (".", "?", "!")          # a word ending in one of these ends a sentence
# Start values; S6c.4 tunes them inside the allowed ranges (dramatic peak 1.18-1.30, hold 0.2-0.5 s).
# hard-cut holds for hold_s, or for the whole gesture (in_s + out_s) when the preset has no hold.
PRESETS = {"dramatic": {"peak": 1.22, "in_s": 0.12, "hold_s": 0.3, "out_s": 0.25,
                        "ease_in": "power2.out", "ease_out": "power2.inOut"},
           "subtle": {"peak": 1.06, "in_s": 1.2, "hold_s": 0, "out_s": 1.2,
                      "ease_in": "sine.inOut", "ease_out": "sine.inOut"}}


class Stop(Exception):
    """A plain stop: exit code + the lines that say why and what to do."""

    def __init__(self, code, *lines):
        super().__init__(lines[0] if lines else "")
        self.code, self.lines = code, lines


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def r4(x):
    return round(float(x), 4)


def read_json(path, missing):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Stop(2, missing) from None
    except (OSError, ValueError) as e:
        raise Stop(2, f"✗ {path.name} can't be read ({e}); make it again.") from None


def write_json(path, obj):
    data = (json.dumps(obj, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    assert b"\r" not in data
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# ---- inputs --------------------------------------------------------------------------------------------------
def master_fps(reel, cuts):
    """The cut master's own rate as "n/d", read the way compose.py reads it (fps.resolve_fps on the video)."""
    if not _num(cuts.get("speed")):
        raise Stop(2, "✗ The cut list work/cuts.json is incomplete; make the cut again.")
    master = reel / "work" / "renders" / f"master-{('%.2fx' % cuts['speed']).replace('.', '')}.mp4"
    if not master.is_file():
        raise Stop(2, f"✗ The cut master work/renders/{master.name} is missing; make the cut first.")
    return fpsmod.resolve_fps(master)


def load(reel, fps=None):
    """The plan's inputs. fps: the rate compose.py already read from the cut master, else it is read here."""
    if not reel.is_dir():
        raise Stop(2, f"✗ There's no reel folder at {reel}; point --reel-dir at videos/<reel>.")
    bm = read_json(reel / SEND, "✗ Send the Beat Map first: press Send on the Beat Map board, then run this again.")
    try:
        words = beat_schema.load_words(reel / beat_schema.DEFAULT_WORDS)
        beat_schema.validate_beat_map(bm, words)
    except beat_schema.SchemaError as e:
        raise Stop(2, *[f"✗ {p}" for p in e.problems], "Fix it on the board and Send again.") from None
    items = json.loads((reel / beat_schema.DEFAULT_WORDS).read_text(encoding="utf-8"))["words"]
    cuts = read_json(reel / "work" / "cuts.json", "✗ There's no cut list (work/cuts.json) yet; make the cut first.")
    segs = cuts.get("segments") if isinstance(cuts, dict) else None
    if not (isinstance(cuts, dict) and _num(cuts.get("fps")) and isinstance(segs, list) and segs
            and all(isinstance(s, dict) and _int(s.get("out_in_f")) and _int(s.get("out_out_f"))
                    and s["out_in_f"] < s["out_out_f"] for s in segs)):
        raise Stop(2, "✗ The cut list work/cuts.json is incomplete; make the cut again.")
    try:
        fps = fpsmod.parse_fps(fps) if fps is not None else master_fps(reel, cuts)
    except ValueError as e:
        raise Stop(2, f"✗ {e}") from None
    if abs(float(Fraction(fps)) - cuts["fps"]) > 1e-3:  # compose.py's rule
        raise Stop(1, f"✗ The cut master runs at {float(Fraction(fps)):.3f} fps but the cut list says {cuts['fps']} "
                      f"fps; make the cut again.")
    spans = [(s["out_in_f"], s["out_out_f"]) for s in segs]
    inp = {"bm": bm, "words": words, "starts": [it.get("start") for it in items], "fps": fps,
           "rate": Fraction(fps), "segs": spans, "starts_f": [a for a, _ in spans],
           "cut_frames": [a for a, _ in spans[1:]], "total": spans[-1][1]}
    inp["anchors"] = load_anchors(reel, spans)
    return inp


def load_anchors(reel, segs):
    """{segment index: [(f, x, y), ...] sorted by f}, or None when the face step hasn't run."""
    path = reel / ANCHORS
    if not path.exists():
        return None
    doc = read_json(path, "")
    fix = "run the face step again."
    if not (isinstance(doc, dict) and isinstance(doc.get("segments"), list)):
        raise Stop(2, f"✗ {ANCHORS} has no segments list; {fix}")
    out = {}
    for i, s in enumerate(doc["segments"]):
        seg = s.get("seg") if isinstance(s, dict) else None
        if not (_int(seg) and 0 <= seg < len(segs) and isinstance(s.get("samples"), list)):
            raise Stop(2, f"✗ {ANCHORS} segments[{i}] is not {{seg, samples}} for one of the "
                          f"{len(segs)} segments; {fix}")
        a, e = segs[seg]
        pts = []
        for p in s["samples"]:
            ok = isinstance(p, dict) and _int(p.get("f")) and a <= p["f"] < e and all(
                _num(p.get(k)) and 0 <= p[k] <= 1 for k in ("x", "y"))
            if not ok:
                raise Stop(2, f"✗ {ANCHORS} segment {seg} has a sample {str(p)[:60]} that is not {{f, x, y}} "
                              f"inside frames {a}-{e - 1} with x, y between 0 and 1; {fix}")
            pts.append((p["f"], float(p["x"]), float(p["y"])))
        out[seg] = sorted(pts)
    return out


def pick_style(bm, *, reel=None, remember=True):
    """(edit_style, "reel" | "saved"): the Send's, else the saved style's; neither = ask the client (H-R36)."""
    if "edit_style" in bm:
        es = bm["edit_style"]
        if remember and isinstance(es, dict) and es.get("style") in STYLES:
            standing_notes.record_pick("edit_style.style", es["style"])
        return bm["edit_style"], "reel"
    saved = saved_style.load(reel)
    _, source = saved_style.resolve("edit_style.style", saved=saved)
    if source == "recommended":
        raise Stop(1, ASK + saved_style.recommendation_line("edit_style.style", saved))
    es = saved.get("edit_style") if isinstance(saved, dict) else None
    if isinstance(es, dict):
        return es, "saved"
    raise Stop(1, ASK)


def check_style(es, source, n_words):
    """The edit_style with every option filled in (moves off), or Stop(2) with plain lines."""
    where = "the Beat Map's edit_style" if source == "reel" else "the saved style's edit_style"
    fix = ("Pick the editing style again on the Beat Map board and Send again." if source == "reel"
           else "Fix edit_style in the saved style (styles/default.json).")
    show = beat_schema._show
    if not isinstance(es, dict):
        raise Stop(2, f"✗ {where} {show(es)} is not an object.", fix)
    bad = []
    unknown = [k for k in es if k not in STYLE_KEYS]
    if unknown:
        bad.append(f"✗ {where} has unknown keys {', '.join(map(str, unknown))} (allowed: {', '.join(STYLE_KEYS)})")
    if es.get("style") not in STYLES:
        bad.append(f"✗ {where}.style {show(es.get('style'))} is not a style; use punch-in or layout-switch")
    ps = es.get("punch_scale", PUNCH_SCALE)
    if not (_num(ps) and 1 <= ps <= 4):
        bad.append(f"✗ {where}.punch_scale {show(ps)} is not a punch level; use a number from 1 to 4, e.g. 1.12")
    mv = {} if es.get("moves") is None else es["moves"]
    wp = None
    if not isinstance(mv, dict):
        bad.append(f"✗ {where}.moves {show(mv)} is not an object; use {{{', '.join(MOVES)}}}")
        mv = {}
    unknown = [k for k in mv if k not in MOVES]
    if unknown:
        bad.append(f"✗ {where}.moves has unknown keys {', '.join(map(str, unknown))} (allowed: {', '.join(MOVES)})")
    for k in ("opening_settle", "follow_cam"):
        if not isinstance(mv.get(k, False), bool):
            bad.append(f"✗ {where}.moves.{k} {show(mv[k])} is not true or false")
    if mv.get("word_punches") is not None:
        wp = mv["word_punches"]
        if not (isinstance(wp, dict) and sorted(wp) == sorted(PUNCH_KEYS)):
            bad.append(f"✗ {where}.moves.word_punches {show(wp)} is not {{{', '.join(PUNCH_KEYS)}}}")
        else:
            if wp["preset"] not in PRESETS:
                bad.append(f"✗ {where} word punch preset {show(wp['preset'])} is not one of {', '.join(PRESETS)}")
            if wp["shape"] not in SHAPES:
                bad.append(f"✗ {where} word punch shape {show(wp['shape'])} is not one of {', '.join(SHAPES)}")
            if not (isinstance(wp["picks"], list) and all(_int(w) and 0 <= w < n_words for w in wp["picks"])):
                bad.append(f"✗ {where} word punch picks {show(wp['picks'])} are not word numbers "
                           f"(0 to {n_words - 1})")
    camera = {}
    for k in ("ratchet", *CAMERA_MOVES):
        v = mv.get(k)
        camera[k] = v
        if v is None:
            continue
        allowed = ("picks", "levels") if k == "ratchet" else ("segments", "edge" if k == "reframe" else "to")
        required = ("segments",) if k in ("push", "ken_burns") else allowed
        if not (isinstance(v, dict) and all(n in allowed for n in v) and all(n in v for n in required)):
            bad.append(f"✗ {where}.moves.{k} {show(v)} needs {', '.join(required)}; allowed keys: {', '.join(allowed)}")
            continue
        if k == "ratchet":
            if not (_int(v["levels"]) and 2 <= v["levels"] <= 4):
                bad.append(f"✗ {where} ratchet levels {show(v['levels'])} must be a whole number from 2 to 4")
            if not (isinstance(v["picks"], list) and all(_int(w) and 0 <= w < n_words for w in v["picks"])):
                bad.append(f"✗ {where} ratchet picks {show(v['picks'])} are not word numbers (0 to {n_words - 1})")
        else:
            seg = v["segments"]
            if not (seg == "all" or isinstance(seg, list) and all(_int(i) and i >= 0 for i in seg)):
                bad.append(f"✗ {where} {MOVE_NAMES[k]} segments {show(seg)} must be all or a list of segment numbers from 0")
            if k == "reframe":
                if v["edge"] not in ("top", "bottom", "left", "right"):
                    bad.append(f"✗ {where} reframe edge {show(v['edge'])} must be top, bottom, left or right")
            else:
                to = v.get("to", PUSH_TO if k == "push" else KB_TO)
                if not (_num(to) and 1 <= to <= 2):
                    bad.append(f"✗ {where} {MOVE_NAMES[k]} zoom {show(to)} must be a number from 1 to 2")
                camera[k] = dict(v, to=to)
    if bad:
        raise Stop(2, *bad, fix)
    on = [k for k in MOVES if mv.get(k) not in (None, False)]
    if on and es["style"] != "punch-in":
        raise Stop(2, f"✗ {where} turns on {', '.join(on)}, but those moves belong to the punch-in style; "
                      f"turn them off or pick punch-in.", fix)
    return {"style": es["style"], "punch_scale": ps,
            "moves": {"opening_settle": mv.get("opening_settle", False), "follow_cam": mv.get("follow_cam", False),
                      "word_punches": wp, **camera}}


# ---- the plan ------------------------------------------------------------------------------------------------
def sentence_of(words):
    out, n = [], 0
    for w in words:
        out.append(n)
        n += w.rstrip().endswith(END)
    return out


def merge(tweens):
    """F-14: moves on the same property from different gestures that touch or overlap become ONE power2.inOut
    move from the first start to the last end. Parts of one gesture (a punch's way in and out, a follow-cam
    path) never merge with each other. A merged move that ends where it began is dropped."""
    out = []
    for t in sorted(tweens, key=lambda t: (t["prop"], t["start_f"], t["end_f"])):
        m = out[-1] if out and out[-1]["prop"] == t["prop"] else None
        if m and t["start_f"] <= m["end_f"] and not m["g"] & t["g"]:
            if t["end_f"] >= m["end_f"]:
                m.update(end_f=t["end_f"], to=t["to"])
            m.update(ease="power2.inOut", id=f"{m['id']} + {t['id']}", g=m["g"] | t["g"])
            continue
        out.append(dict(t))
    return [t for t in out if t["from"] != t["to"]]


def value_at(sets, tweens, prop, f):
    """The a-roll's `prop` on frame f: the latest hard set, or the move that started after it."""
    sf = max(k for k in sets if k <= f and prop in sets[k])
    tw = max((t for t in tweens if t["prop"] == prop and sf < t["start_f"] <= f),
             key=lambda t: t["start_f"], default=None)
    if tw is None:
        return sets[sf][prop]
    if f >= tw["end_f"]:
        return tw["to"]
    k = (f - tw["start_f"]) / (tw["end_f"] - tw["start_f"])  # only a linear follow-cam move is ever caught mid-way
    if isinstance(tw["from"], list):
        return [a + (b - a) * k for a, b in zip(tw["from"], tw["to"])]
    return tw["from"]


def build(inp, es, presets=None):
    """(keys, tweens, warnings) for the style; pure."""
    presets = presets or PRESETS
    rate, segs, words, bm = inp["rate"], inp["segs"], inp["words"], inp["bm"]
    warn = []
    punch = es["style"] == "punch-in"
    mv = es["moves"]
    selected = {}
    for name in CAMERA_MOVES:
        move = mv[name]
        picks = move["segments"] if move else []
        selected[name] = set(range(len(segs))) if picks == "all" else set(picks)
        if any(i >= len(segs) for i in selected[name]):
            raise Stop(2, f"✗ The {MOVE_NAMES[name]} move names a segment outside this cut; use segment numbers 0 to {len(segs) - 1}.")
    for left, right, why in (("push", "ken_burns", "pick one per shot"),
                             ("ken_burns", "reframe", "both place the zoom centre; pick one per shot")):
        shared = selected[left] & selected[right]
        if shared:
            raise Stop(2, f"✗ {MOVE_NAMES[left]} and {MOVE_NAMES[right]} both use segment {min(shared)}; {why}.")
    zooming = selected["push"] | selected["ken_burns"]
    placed = selected["ken_burns"] | selected["reframe"]

    def frames(sec):
        return round(Fraction(str(sec)) * rate)

    def seg_of(f):
        return max(0, bisect.bisect_right(inp["starts_f"], f) - 1)

    solid = sorted((b for b in bm["beats"] if b["layout"] != "overlay"), key=lambda b: b["start_f"])

    def layout_at(f):
        if punch:
            return "full"  # the punch-in style covers jump cuts by scale; the a-roll stays full screen
        prev = [b for b in solid if b["start_f"] <= f]
        return prev[-1]["layout"] if prev else "full"

    scale = [es["punch_scale"] if punch and i % 2 else 1.0 for i in range(len(segs))]
    anchors = inp["anchors"] or {}
    origin = [list(anchors[i][0][1:]) if anchors.get(i) else list(ORIGIN) for i in range(len(segs))]
    sets, tweens = {}, []

    def put(f, **kv):
        sets.setdefault(f, {}).update(kv)

    def tween(s, e, prop, a, b, ease, tid, g):
        tweens.append({"start_f": s, "end_f": e, "prop": prop, "from": a, "to": b, "ease": ease, "id": tid,
                       "g": frozenset([g])})

    for i, (a, _) in enumerate(segs):  # A4 + the punch-in rule: the segment's state, set hard on its first frame
        put(a, scale=scale[i], origin=origin[i], layout=layout_at(a))

    if not punch:
        move_f, prev = frames(MOVE_S), "full"
        for b in solid:
            f = b["start_f"]
            if b["layout"] != prev and f not in sets and f < inp["total"]:
                last = segs[seg_of(f)][1] - 1
                end = min(f + move_f, last)
                if end <= f:
                    warn.append(f"beat {b['id']}'s layout change sits on the last frame before a cut, so it "
                                f"lands on the cut instead")
                else:
                    if end < f + move_f:
                        warn.append(f"the layout move into beat {b['id']} is shortened to {end - f} frames so it "
                                    f"ends before the cut")
                    tween(f, end, "layout", prev, b["layout"], "power2.inOut", f"layout {b['id']}", b["id"])
            prev = b["layout"]

    kept = []  # punch events: (word, start, end, segment, hard sets, tweens) in time order
    wp = mv["word_punches"] if punch else None
    ratchet = mv["ratchet"] if punch else None
    if wp or ratchet:
        events = [(w, "word punch") for w in set(wp["picks"])] if wp else []
        events += [(w, "ratchet") for w in set(ratchet["picks"])] if ratchet else []
        for w, _ in events:
            if not _num(inp["starts"][w]):
                raise Stop(2, f"✗ word {w} in {beat_schema.DEFAULT_WORDS} has no start time; make the cut's word "
                              f"list again.")
        events.sort(key=lambda event: (inp["starts"][event[0]], event[0], event[1]))
        sent, owner = sentence_of(words), {}
        for w, kind in events:
            name = f'"{words[w].strip()}" (word {w})'
            st = Fraction(str(inp["starts"][w]))
            i = seg_of(round(st * rate))
            a, e = segs[i]
            on = max(round((st - ONSET_LEAD) * rate), a)
            room = e - 1 - on
            if i in zooming:
                warn.append(f"{kind} on {name} dropped: segment {i} already has a camera move")
                continue
            if sent[w] in owner:
                warn.append(f'{kind} on {name} dropped: one punch per sentence, and "{words[owner[sent[w]]]}" '
                            f'already has it')
                continue
            if kept and kept[-1][3] == i and on < kept[-1][2]:
                warn.append(f"{kind} on {name} dropped: it would start before the punch on "
                            f'"{words[kept[-1][0]].strip()}" ends')
                continue
            if kind == "ratchet":
                step, hold = max(1, frames(RATCHET_STEP_S)), max(1, frames(RATCHET_HOLD_S))
                levels = min(ratchet["levels"], (room - hold) // step + 1)
                if levels < 2:
                    warn.append(f"ratchet on {name} dropped: fewer than 2 levels fit before the cut at frame {e}")
                    continue
                if levels < ratchet["levels"]:
                    warn.append(f"ratchet on {name} shortened to {levels} levels so it is back before the cut")
                end = on + (levels - 1) * step + hold
                hard_sets = [(on + n * step, r4(scale[i] * (1 + (n + 1) * RATCHET_STEP))) for n in range(levels)]
                hard_sets.append((end, scale[i]))
                kept.append((w, on, end, i, hard_sets, []))
                owner[sent[w]] = w
                continue
            p = presets[wp["preset"]]
            hard = wp["shape"] == "hard-cut"
            peak = r4(scale[i] * p["peak"])  # A5: segment x peak, never max() and never capped
            if hard:
                want = frames(p["hold_s"] or p["in_s"] + p["out_s"])
                hold = min(want, room)
                if hold < 1:
                    warn.append(f"word punch on {name} dropped: no room before the cut at frame {e}")
                    continue
                if hold < want:
                    warn.append(f"word punch on {name} shortened to {hold} frames so it is back before the cut")
                kept.append((w, on, on + hold, i, [(on, peak), (on + hold, scale[i])], []))
                owner[sent[w]] = w
                continue
            fi, fh, fo = frames(p["in_s"]), frames(p["hold_s"]), frames(p["out_s"])
            if fi + 1 > room:
                warn.append(f"word punch on {name} dropped: no room before the cut at frame {e}")
                continue
            h = max(0, min(fh, room - fi - fo))
            o = min(fo, room - fi - h)
            if (h, o) != (fh, fo):
                warn.append(f"word punch on {name} shortened (hold {h}, way back {o} frames) so it is back "
                            f"before the cut")
            tw = [(on, on + fi, scale[i], peak, p["ease_in"], f"punch {w} in"),
                  (on + fi + h, on + fi + h + o, peak, scale[i], p["ease_out"], f"punch {w} out")]
            kept.append((w, on, on + fi + h + o, i, [], tw))
            owner[sent[w]] = w

    if punch and mv["opening_settle"] and 0 in zooming:
        warn.append("opening settle skipped: segment 0 already has a camera move")
    if punch and mv["opening_settle"] and 0 not in zooming:
        a, e = segs[0]
        end = min(a + frames(SETTLE_S), e - 1)
        first = next((k[1] for k in kept if k[3] == 0), None)
        if first is not None:
            end = min(end, first)  # the settle gives way to an early punch (and merges with an eased one)
        if end > a:
            put(a, scale=r4(scale[0] * SETTLE))
            tween(a, end, "scale", r4(scale[0] * SETTLE), scale[0], "power2.out", "opening settle", "settle")
        else:
            warn.append("opening settle skipped: a word punch starts on the first frame")

    for w, _, _, _, hard_sets, tw in kept:
        for f, v in hard_sets:
            put(f, scale=v)
        for s, e, a, b, ease, tid in tw:
            tween(s, e, "scale", a, b, ease, tid, f"punch {w}")

    for i, (a, e) in enumerate(segs):
        if i in selected["reframe"]:
            edge = mv["reframe"]["edge"]
            ox, oy = origin[i]
            put(a, origin=[0 if edge == "left" else 1 if edge == "right" else ox,
                           0 if edge == "top" else 1 if edge == "bottom" else oy])
            has_zoom = (scale[i] != 1 or any(k[3] == i for k in kept)
                        or i == 0 and mv["opening_settle"] and 0 not in zooming
                        or any(i in selected[n] and mv[n]["to"] > 1 for n in ("push", "ken_burns")))
            if not has_zoom:
                warn.append(f"the reframe has nothing to hold: segment {i} isn't zoomed")
        for name, ease in (("push", "none"), ("ken_burns", "sine.inOut")):
            if i not in selected[name]:
                continue
            tid = f"push {i}" if name == "push" else f"ken-burns {i} scale"
            tween(a, e - 1, "scale", scale[i], r4(scale[i] * mv[name]["to"]), ease, tid, f"{name} {i}")
            if name == "ken_burns":
                ox, oy = origin[i]
                start, end = [max(0, ox - KB_PAN), oy], [min(1, ox + KB_PAN), oy]
                put(a, origin=start)
                tween(a, e - 1, "origin", start, end, ease, f"ken-burns {i} origin", f"{name} {i}")

    if punch and mv["follow_cam"]:
        if inp["anchors"] is None:
            warn.append("follow-cam: there are no head samples yet (work/anchors.json), so the camera stays put")
        for i in sorted(placed):
            warn.append(f"follow-cam skipped on segment {i}: its camera move places the zoom centre")
        for i, pts in sorted(anchors.items()):  # VES-6: inside each segment only; the cut key restarts it
            if i in placed:
                continue
            for (f0, x0, y0), (f1, x1, y1) in zip(pts, pts[1:]):
                if f1 > f0:
                    tween(f0, f1, "origin", [x0, y0], [x1, y1], "none", f"follow-cam {i}: {f0}-{f1}", f"follow {i}")

    tweens = merge(tweens)
    keys = []
    for f in sorted(sets):
        ox, oy = value_at(sets, tweens, "origin", f)
        keys.append({"f": f, "scale": r4(value_at(sets, tweens, "scale", f)), "ox": r4(ox), "oy": r4(oy),
                     "layout": value_at(sets, tweens, "layout", f)})
    out = []
    for t in tweens:
        t.pop("g")
        if t["prop"] == "origin":
            t["from"], t["to"] = [r4(v) for v in t["from"]], [r4(v) for v in t["to"]]
        out.append(t)
    return keys, out, warn


def ceiling_notes(keys, tweens, beats, tuning):
    """A5 / AZ-2 b: a note for each beat whose total size passes the measured ceiling; values never change."""
    try:
        ceil = json.loads(Path(tuning).read_text(encoding="utf-8")).get("softness_ceiling")
    except FileNotFoundError:
        return []
    except (OSError, ValueError, AttributeError) as e:
        return [f"the softness ceiling can't be read from {Path(tuning).name} ({e}), so it wasn't checked"]
    if not _num(ceil):
        return []
    solid = sorted((b for b in beats if b["layout"] != "overlay"), key=lambda b: b["start_f"])
    seen, out = set(), []
    hits = [(k["f"], k["scale"]) for k in keys] + [(t["end_f"], t["to"]) for t in tweens if t["prop"] == "scale"]
    for f, v in sorted(hits):
        if v > ceil:
            bid = next((b["id"] for b in reversed(solid) if b["start_f"] <= f), solid[0]["id"] if solid else "-")
            line = f"softness: beat {bid} reaches {v:g}"
            if line not in seen:
                seen.add(line)
                out.append(line)
    return out


def plan(reel, extra_spans=None, presets=None, tuning=None, fps=None, *, remember_choices=True, style_reel=None):
    """The scale track for the reel, effect-gated; writes nothing (cmd_plan writes it). Raises Stop.
    extra_spans: internal, so a test can plant a move the gate must refuse. fps: compose.py's rate ("n/d") from the
    cut master; None = read it from the cut master here."""
    inp = load(Path(reel), fps)
    raw, source = pick_style(inp["bm"], reel=reel if style_reel is None else style_reel, remember=remember_choices)
    es = check_style(raw, source, len(inp["words"]))
    keys, tweens, warn = build(inp, es, presets)
    warn += ceiling_notes(keys, tweens, inp["bm"]["beats"], tuning or TUNING)
    spans = [{"layer": "aroll_transform", "start_f": t["start_f"], "end_f": t["end_f"], "id": t["id"]}
             for t in tweens]
    problems = effect_gate.check(spans + list(extra_spans or []), inp["cut_frames"], inp["fps"], inp["total"])
    if problems:
        raise Stop(1, *[f"BLOCK {p}" for p in problems], "Nothing was written; change the style's moves and plan again.")
    return {"schema": 1, "fps": inp["fps"], "total_f": inp["total"], "style": es, "source": source,
            "keys": keys, "tweens": tweens, "spans": spans, "warnings": warn}


def cmd_plan(reel, extra_spans=None, presets=None, tuning=None):
    try:
        track = plan(reel, extra_spans, presets, tuning)
    except Stop as s:
        for line in s.lines:
            print(line)
        return s.code
    write_json(Path(reel) / TRACK, track)
    print(f"✓ Style planned: {track['style']['style']}, {len(track['tweens'])} moves")
    for w in track["warnings"]:
        print(f"note: {w}")
    print(json.dumps({"style": track["style"]["style"], "keys": len(track["keys"]), "tweens": len(track["tweens"]),
                      "warnings": len(track["warnings"])}))
    return 0


# ---- selftest ------------------------------------------------------------------------------------------------
WORDS = [("Three", 0.10), ("edits", 0.46), ("that", 0.82), ("save.", 1.18), ("Meet", 1.50), ("Alex", 1.62),
         ("today.", 1.80), ("This", 2.10), ("works", 2.40), ("every", 2.80), ("time.", 3.93), ("Go", 4.30),
         ("now!", 4.60)]
SEGS = [(0, 50), (50, 100), (100, 150)]


def beat(bid, s, e, w0, w1, layout="full", words=WORDS):
    return {"id": bid, "start_f": s, "end_f": e,
            "speech_anchor": {"text": " ".join(w for w, _ in words[w0:w1 + 1]), "w0": w0, "w1": w1},
            "layout": layout, "value": None, "scene": None, "broll": None, "transition": None}


BEATS = [beat("b_001", 0, 50, 0, 6), beat("b_002", 50, 100, 7, 10), beat("b_003", 100, 150, 11, 12)]


def make_reel(root, edit_style=None, beats=None, anchors=None, fps=25, segs=SEGS, words=WORDS):
    """A small reel folder for styles.py (no video): Send, cut word list, cut list, optional anchors.json."""
    reel = Path(tempfile.mkdtemp(prefix="styles-", dir=root))
    (reel / "work").mkdir()

    def wj(rel, obj):
        (reel / rel).write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))

    wj(beat_schema.DEFAULT_WORDS, {"words": [{"id": f"w_{i:04d}", "word": w, "start": s, "end": round(s + 0.2, 2)}
                                             for i, (w, s) in enumerate(words)]})
    wj("work/cuts.json", {"fps": fps, "speed": 1.0, "segments": [
        {"src_in_f": a + 10 * i, "src_out_f": e + 10 * i, "out_in_f": a, "out_out_f": e} for i, (a, e) in enumerate(segs)]})
    send = {"schema": 1, "reel": "demo", "fps": fps, "words": beat_schema.DEFAULT_WORDS,
            "beats": beats or BEATS, "word_marks": [], "proposed": {}, "notes": {}, "needs": "", "sent_at": None}
    if edit_style is not None:
        send["edit_style"] = edit_style
    wj(SEND, send)
    if anchors is not None:
        wj(ANCHORS, {"segments": [{"seg": i, "samples": [{"f": f, "x": x, "y": y} for f, x, y in pts]}
                                  for i, pts in anchors.items()]})
    return reel


def selftest():
    fails = []

    def expect(name, ok, detail=""):
        if not ok:
            fails.append(f"{name}{(': ' + str(detail)[:300]) if detail else ''}")

    def run(root, es, **kw):
        try:
            return plan(make_reel(root, es, **{k: v for k, v in kw.items() if k in ("beats", "anchors")}),
                        presets=kw.get("presets"), tuning=kw.get("tuning", Path(root) / "no-tuning.json"),
                        extra_spans=kw.get("extra"), fps=kw.get("fps", "25"))
        except Stop as s:
            return s

    def pin(**moves):
        return {"style": "punch-in", "punch_scale": 1.12, "moves": moves}

    def at(track, f):
        return next((k for k in track["keys"] if k["f"] == f), None)

    old_home = os.environ.get("EDITOR_SE_HOME")
    with tempfile.TemporaryDirectory() as root:
        os.environ["EDITOR_SE_HOME"] = str(Path(root) / "state")
        try:
            s = run(root, None)
            expect("ask line when no style anywhere", isinstance(s, Stop) and s.code == 1 and s.lines == (ASK,), s)
            (Path(root) / "state" / "styles").mkdir(parents=True)
            (Path(root) / "state" / "styles" / "default.json").write_text(
                json.dumps({"edit_style": {"style": "layout-switch"}}), encoding="utf-8")
            t = run(root, None)
            expect("saved style used when the Send has none", not isinstance(t, Stop) and t["source"] == "saved", t)
        finally:
            if old_home is None:
                os.environ.pop("EDITOR_SE_HOME", None)
            else:
                os.environ["EDITOR_SE_HOME"] = old_home

        t = run(root, pin())
        expect("punch-in: hard sets 1.0 / 1.12 / 1.0 on frames 0, 50, 100, no moves",
               [(k["f"], k["scale"]) for k in t["keys"]] == [(0, 1.0), (50, 1.12), (100, 1.0)] and not t["tweens"], t)
        expect("default zoom centre on each cut frame", all((k["ox"], k["oy"]) == ORIGIN for k in t["keys"]), t)
        expect("camera options all off by default", all(t["style"]["moves"][n] is None
               for n in ("ratchet", *CAMERA_MOVES)), t)
        for levels in (2, 3, 4):
            t = run(root, pin(ratchet={"picks": [0], "levels": levels}))
            on = round((Fraction("0.10") - ONSET_LEAD) * 25)
            expected = [(on + n * 5, r4(1 + (n + 1) * RATCHET_STEP)) for n in range(levels)]
            expected.append((on + (levels - 1) * 5 + 8, 1.0))
            expect(f"ratchet: {levels} hard steps then back to 1.0, no tween",
                   [(k["f"], k["scale"]) for k in t["keys"] if on <= k["f"] <= expected[-1][0]] == expected
                   and not t["tweens"], t)
        t = run(root, pin(push={"segments": "all"}, opening_settle=True))
        expect("push: linear, first to last frame, settle skipped",
               [(x["start_f"], x["end_f"], x["ease"]) for x in t["tweens"]]
               == [(0, 49, "none"), (50, 99, "none"), (100, 149, "none")]
               and any("opening settle skipped" in w for w in t["warnings"]), t)
        t = run(root, pin(ken_burns={"segments": [1]}))
        expect("Ken Burns: two moves inside one shot", len(t["tweens"]) == 2 and
               all(x["start_f"] == 50 and x["end_f"] == 99 and x["ease"] == "sine.inOut" for x in t["tweens"]), t)
        s = run(root, pin(ken_burns={"segments": [1]}),
                extra=[{"layer": "aroll_transform", "start_f": 40, "end_f": 60, "id": "planted Ken Burns"}])
        expect("Ken Burns: planted cut crossing blocked", isinstance(s, Stop) and s.code == 1
               and s.lines[0].startswith("BLOCK"), s)
        s = run(root, pin(push={"segments": [1]}, ken_burns={"segments": [1]}))
        expect("camera conflicts are plain Stop(2)", isinstance(s, Stop) and s.code == 2
               and "pick one per shot" in s.lines[0], s)

        p13 = {"dramatic": dict(PRESETS["dramatic"], peak=1.30), "subtle": PRESETS["subtle"]}
        es = dict(pin(word_punches={"preset": "dramatic", "shape": "hard-cut", "picks": [7]}), punch_scale=1.10)
        t = run(root, es, presets=p13)
        on = round((Fraction("2.10") - ONSET_LEAD) * 25)
        expect("1.43: 1.10 x 1.30 set hard on the onset, back after the hold",
               at(t, on) and at(t, on)["scale"] == 1.43 and at(t, on + 8)["scale"] == 1.1 and not t["tweens"], t)

        tun = Path(root) / "tuning.json"
        tun.write_text(json.dumps({"softness_ceiling": 1.25}), encoding="utf-8")
        t = run(root, es, presets=p13, tuning=tun)
        expect("ceiling: a note, the value unchanged",
               "softness: beat b_002 reaches 1.43" in t["warnings"] and at(t, on)["scale"] == 1.43, t)

        t = run(root, pin(word_punches={"preset": "dramatic", "shape": "eased", "picks": [0, 2, 7]}))
        ids = [x["id"] for x in t["tweens"]]
        expect("one punch per sentence: word 2 dropped with a note naming it",
               any('"that" (word 2) dropped' in w for w in t["warnings"]) and not any("punch 2" in i for i in ids), t)
        p7 = [x for x in t["tweens"] if x["id"].startswith("punch 7")]
        expect("eased punch: power2.out in, power2.inOut out, peak 1.12 x 1.22 frame-exact",
               [(x["ease"], x["to"]) for x in p7] == [("power2.out", 1.3664), ("power2.inOut", 1.12)]
               and p7[0]["start_f"] == on and p7[0]["end_f"] == on + 3, p7)

        t = run(root, pin(word_punches={"preset": "dramatic", "shape": "eased", "picks": [6, 10]}))
        p6 = [x for x in t["tweens"] if x["id"].startswith("punch 6")]
        expect("clip: a punch near the cut is back by the segment's last frame (hold, then way back, shortened)",
               p6 and p6[-1]["end_f"] == 49 and p6[0]["start_f"] == 44, p6)
        expect("clip: a punch whose way in doesn't fit is dropped with a note",
               any('"time." (word 10) dropped' in w for w in t["warnings"]), t["warnings"])
        expect("clip: no span crosses a cut", not effect_gate.check(t["spans"], [50, 100], "25/1", 150), t["spans"])

        t = run(root, pin(opening_settle=True))
        expect("opening settle: 1.06 on frame 0, settles over 0.6 s (15 frames) power2.out",
               at(t, 0)["scale"] == 1.06 and t["tweens"] == [{"start_f": 0, "end_f": 15, "prop": "scale", "from": 1.06,
                                                              "to": 1.0, "ease": "power2.out", "id": "opening settle"}],
               t)
        t = run(root, pin(opening_settle=True, word_punches={"preset": "dramatic", "shape": "eased", "picks": [0]}))
        first = t["tweens"][0]
        expect("merge: the settle and an early punch touch -> one power2.inOut move 1.06 -> 1.22",
               (first["start_f"], first["end_f"], first["from"], first["to"], first["ease"]) == (0, 4, 1.06, 1.22,
                                                                                                "power2.inOut"), t)

        anchors = {0: [(0, 0.5, 0.30), (20, 0.55, 0.32), (40, 0.6, 0.34)], 1: [(55, 0.4, 0.4), (95, 0.45, 0.42)]}
        t = run(root, pin(follow_cam=True), anchors=anchors)
        og = [(x["start_f"], x["end_f"]) for x in t["tweens"] if x["prop"] == "origin"]
        expect("follow-cam: moves stay inside their segment, linear", og == [(0, 20), (20, 40), (55, 95)]
               and all(x["ease"] == "none" for x in t["tweens"]), t["tweens"])
        expect("follow-cam: restarts on the cut frame at the new segment's first sample; default where no samples",
               (at(t, 50)["ox"], at(t, 50)["oy"]) == (0.4, 0.4) and (at(t, 100)["ox"], at(t, 100)["oy"]) == ORIGIN, t)
        t = run(root, pin(follow_cam=True))
        expect("follow-cam with no anchors: does nothing, with a note",
               not t["tweens"] and any("follow-cam" in w for w in t["warnings"]), t)
        t = run(root, pin(), anchors=anchors)
        expect("anchor: the first head sample on each cut frame, without follow-cam",
               not t["tweens"] and (at(t, 0)["ox"], at(t, 0)["oy"]) == (0.5, 0.3), t)

        lb = [beat("b_001", 0, 50, 0, 6), beat("b_002", 50, 70, 7, 8, "split"), beat("b_003", 70, 150, 9, 12, "stack")]
        t = run(root, {"style": "layout-switch"}, beats=lb)
        expect("layout-switch: a change on the cut frame is a hard set, mid-segment a 15-frame power2.inOut move",
               at(t, 50)["layout"] == "split" and at(t, 100)["layout"] == "stack"
               and t["tweens"] == [{"start_f": 70, "end_f": 85, "prop": "layout", "from": "split", "to": "stack",
                                    "ease": "power2.inOut", "id": "layout b_003"}], t)
        mb = [beat("b_001", 0, 60, 0, 7), beat("b_002", 60, 65, 8, 8, "split"), beat("b_003", 65, 150, 9, 12, "pip")]
        t = run(root, {"style": "layout-switch"}, beats=mb)
        expect("merge: two overlapping layout moves -> one power2.inOut move full -> pip",
               [(x["start_f"], x["end_f"], x["from"], x["to"], x["ease"]) for x in t["tweens"]]
               == [(60, 80, "full", "pip", "power2.inOut")], t["tweens"])
        s = run(root, {"style": "layout-switch", "moves": {"opening_settle": True}})
        expect("moves refused in layout-switch (exit 2)", isinstance(s, Stop) and s.code == 2
               and "belong to the punch-in style" in s.lines[0], s)
        s = run(root, pin(), extra=[{"layer": "aroll_transform", "start_f": 40, "end_f": 60, "id": "planted"}])
        expect("VES-1: a planted move across a cut stops the plan (exit 1)",
               isinstance(s, Stop) and s.code == 1 and s.lines[0].startswith("BLOCK aroll_transform 'planted'"), s)
        s = run(root, pin(), fps="30")
        expect("fps: a rate 0.001 or more off the cut list's stops the plan (exit 1)",
               isinstance(s, Stop) and s.code == 1 and "make the cut again" in s.lines[0], s)
        t = plan(make_reel(root, pin(), fps=29.97), fps="30000/1001", tuning=Path(root) / "no-tuning.json")
        expect("fps: the track carries the master's exact rate (30000/1001 over the cut list's 29.97)",
               t["fps"] == "30000/1001", t["fps"])
        t = run(root, pin(opening_settle=True, follow_cam=True,
                          word_punches={"preset": "subtle", "shape": "eased", "picks": [4, 7, 11]}), anchors=anchors)
        ints = all(_int(k["f"]) for k in t["keys"]) and all(_int(x["start_f"]) and _int(x["end_f"]) for x in t["tweens"])
        expect("frames: every key, move start and move end is a whole frame", ints, t)
        expect("subtle: sine.inOut both halves", all(x["ease"] == "sine.inOut" for x in t["tweens"]
                                                     if x["id"].startswith("punch")), t["tweens"])
    for f in fails:
        print(f"selftest FAILED: {f}")
    if not fails:
        print("selftest ok")
    return 1 if fails else 0


# ---- CLI -----------------------------------------------------------------------------------------------------
def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Plan the reel's editing style: punch-ins, moves and layout sets.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks (no tools) and exit")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan", help="write work/scale_track.json from the Beat Map Send and the cut")
    p.add_argument("--reel-dir", required=True, help="the reel folder, videos/<reel>")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd != "plan":
        ap.print_help()
        return 2
    return cmd_plan(Path(a.reel_dir).resolve())


def guarded(fn):
    """The last line of defence: an unexpected failure is one plain line and exit 1, never a traceback."""
    try:
        return fn()
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001  (known failures print their own lines)
        msg = str(e).strip().splitlines()[0][:200] if str(e).strip() else ""
        print(f"✗ The style planner stopped unexpectedly ({type(e).__name__}{': ' + msg if msg else ''}). Run it "
              f"again; if it fails twice, offer the failure report.")
        return 1


if __name__ == "__main__":
    sys.exit(guarded(main))
