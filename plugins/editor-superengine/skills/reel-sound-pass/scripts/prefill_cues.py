"""Pre-fill the Sound Board's cue proposals from the client's Beat Map Send.

  prefill_cues.py --reel <reel> --out <cues.json> [--sfx <dir>]

Reads <reel>/beat-map-selection.json (fps, beats, word_marks), the cut's words <reel>/work/edit_map.cut.json (a
mark's w is the word's list position; start is cut time) and the sound library (--sfx, default <paths.editor>/sound/,
the folder new_board.py copies from). Writes only --out: [{id, beat, short, why, time, candidates}], the shape
new_board.py --cues takes. There is no state field, so every cue arrives on the board undecided.

  - a transition at each beat start whose layout differs from the beat before it (none before 0.2 s);
  - a hit at the start of each word marked num, key or emph;
  - nothing at or after the closer's start (the last beat that isn't an overlay): the closer lands in silence;
  - cues within 0.05 s of each other become one (a marked word wins over a transition);
  - 2-3 candidates per cue, picked by the sound's name: transitions from whoosh/swoosh/swish/sweep/air sounds of
    0.6 s or less (measured), hits from hit/tick/tap/pop/click/thump/knock/bump/thud/impact sounds; a kind with
    fewer than 2 is topped up from the rest of the library (transitions still 0.6 s or less).
Exit 0 written; 2 no Beat Map Send, or an empty library (one plain line, nothing written).
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import workspace, write_json  # noqa: E402
import measure_sfx  # noqa: E402

HIT_MARKS = ("num", "key", "emph")
TRANSITION_WORDS = ("whoosh", "swoosh", "swish", "sweep", "air")
HIT_WORDS = ("hit", "tick", "tap", "pop", "click", "thump", "knock", "bump", "thud", "impact")
MIN_T, MERGE_S, MAX_TRANSITION_S = 0.2, 0.05, 0.6
CLOSER_SILENT = True        # no cue in the closer (the test turns it off to prove the rule bites)


def read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def library(folder):
    """[(file name, measured seconds or None)] of the sounds in folder."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return [(f.name, measure_sfx.duration(f)) for f in sorted(folder.iterdir())
            if f.is_file() and f.suffix.lower() in measure_sfx.SOUND_EXT]


def _kind(name, words):
    return any(t.startswith(w) for t in re.split(r"[^a-z]+", Path(name).stem.lower()) if t for w in words)


def _pick(pool, extra, i):
    """Up to 3 from pool, rotated by i so neighbouring cues offer different sounds first; at least 2 if extra allows."""
    got = (pool[i % len(pool):] + pool[:i % len(pool)])[:3] if pool else []
    return got + [x for x in extra if x not in got][:max(0, 2 - len(got))]


def propose(sel, words, lib):
    """The cue proposals from a Beat Map Send, the cut's word list and the library [(name, seconds)]."""
    fps = float(sel.get("fps") or 30)
    beats = sorted((b for b in sel.get("beats") or [] if isinstance(b, dict)), key=lambda b: b.get("start_f", 0))
    solid = [b for b in beats if b.get("layout") != "overlay"] or beats
    closer = solid[-1]["start_f"] / fps if solid else float("inf")
    raw = []                                                   # (time, is a mark, beat, short, why, kind)
    for prev, b in zip(beats, beats[1:]):
        t = b["start_f"] / fps
        if b.get("layout") != prev.get("layout") and t >= MIN_T:
            label = (b.get("speech_anchor") or {}).get("text") or b.get("id", "")
            raw.append((t, False, label, "whoosh into the %s look" % b.get("layout"),
                        "The look changes here (%s to %s)." % (prev.get("layout"), b.get("layout")), "transition"))
    for m in sel.get("word_marks") or []:
        w = m.get("w")
        if m.get("mark") in HIT_MARKS and isinstance(w, int) and 0 <= w < len(words) \
                and isinstance(words[w].get("start"), (int, float)):
            word = words[w].get("word", "")
            raw.append((float(words[w]["start"]), True, '"%s"' % word, "hit on %s" % word,
                        "You marked this word (%s)." % m["mark"], "hit"))
    if CLOSER_SILENT:
        raw = [r for r in raw if r[0] < closer]
    kept = []
    for r in sorted(raw, key=lambda r: (r[0], not r[1])):
        if kept and r[0] - kept[-1][0] <= MERGE_S + 1e-9:
            if r[1] and not kept[-1][1]:
                kept[-1] = r
            continue
        kept.append(r)
    trans = [n for n, d in lib if _kind(n, TRANSITION_WORDS) and d is not None and d <= MAX_TRANSITION_S]
    short = [n for n, d in lib if n not in trans and d is not None and d <= MAX_TRANSITION_S]
    hits = [n for n, _ in lib if _kind(n, HIT_WORDS)]
    rest = [n for n, _ in lib if n not in hits]
    out, seen = [], {"transition": 0, "hit": 0}
    for i, (t, _, label, short_, why, kind) in enumerate(kept):
        cands = _pick(trans, short, seen[kind]) if kind == "transition" else _pick(hits, rest, seen[kind])
        seen[kind] += 1
        out.append({"id": "c%d" % (i + 1), "beat": label, "short": short_, "why": why, "time": round(t, 3),
                    "candidates": cands})
    return out


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Pre-fill the Sound Board's cues from the Beat Map Send.")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--out", required=True, help="the cue proposals JSON to write (for new_board.py --cues)")
    ap.add_argument("--sfx", help="folder of sound effects (default: the workspace library)")
    a = ap.parse_args(argv)
    editor_dir, videos_dir = workspace()
    reel = videos_dir / a.reel
    sel = read_json(reel / "beat-map-selection.json")
    if not isinstance(sel, dict) or not isinstance(sel.get("beats"), list):
        print("There is no Beat Map Send for this reel yet, so the cues can't be pre-filled. Propose them by hand.")
        return 2
    lib = library(a.sfx or editor_dir / "sound")
    if not lib:
        print("There are no sound effects in the library yet, so the cues can't be pre-filled.")
        return 2
    words = (read_json(reel / "work" / "edit_map.cut.json") or {}).get("words")
    if not isinstance(words, list):
        print("The cut's word list isn't there, so only the look changes get cues (no marked words).")
        words = []
    cues = propose(sel, [w if isinstance(w, dict) else {} for w in words], lib)
    write_json(a.out, cues)
    print("Pre-filled %d cue%s from the Beat Map (nothing in the closer)." % (len(cues), "" if len(cues) == 1 else "s"))
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
