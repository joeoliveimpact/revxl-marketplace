#!/usr/bin/env python3
"""Pre-render check: the word map still matches the cut, and every kept word's place in the cut is right to 6 ms.

    <editor python> -X utf8 -I map_check.py <reel_dir>      exit 1 on any block, 0 when clean

Module contract (H-B6): PHASE = "pre"; run(ctx) returns [{check, level: "block"|"warn", msg, where}],
ctx = {reel_dir, fps, cuts, beats, render}. Only ctx["reel_dir"] is read: the check reads work/cuts.json,
work/edit_map.json and work/word_map.json from disk, because staleness is a test on the files themselves.

Blocks:
  word-map-missing   no work/word_map.json (or cuts.json / edit_map.json missing, or any of them unreadable)
  word-map-stale     cuts.json or edit_map.json changed after the map was written (sha256 in the map)
  word-missing       a kept word (recomputed by word_map.build from the current files) is not in the map
  word-twice         a word sits in two segments, or the map lists it twice
  word-not-kept      the map lists a word the cut drops
  word-wrong-piece   the map puts a word in a different segment than the cut does
  word-time          a word's output start or end is off by more than 6 ms from
                     out_in_f/fps + (src_t - src_in_f/fps) / speed
"""
import json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2] / "reel-first-cuts" / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
import word_map  # noqa: E402

PHASE = "pre"
TOL = 0.006
RERUN = " Rerun word_map.py on this reel before rendering."


def _hit(check, msg, where):
    return dict(check=check, level="block", msg=msg, where=where)


def run(ctx):
    work = Path(ctx["reel_dir"]) / "work"
    cuts_p, em_p, map_p = work / "cuts.json", work / "edit_map.json", work / "word_map.json"
    for p in (cuts_p, em_p, map_p):
        if not p.exists():
            what = "No word map yet" if p is map_p else "Can't check the words: %s is missing" % p.name
            return [_hit("word-map-missing", what + "." + RERUN, str(p))]
    try:
        cuts, em, m = (json.loads(p.read_text(encoding="utf-8")) for p in (cuts_p, em_p, map_p))
        got = m["words"]
    except (ValueError, KeyError, TypeError) as e:
        return [_hit("word-map-missing", "The word map or its inputs can't be read (%s)." % e + RERUN, str(map_p))]
    if m.get("cuts_sha256") != word_map.sha(cuts_p) or m.get("edit_map_sha256") != word_map.sha(em_p):
        return [_hit("word-map-stale", "The word map is out of date: the cut list (cuts.json) or the transcript "
                     "(edit_map.json) changed after it was written." + RERUN, str(map_p))]

    want = word_map.build(cuts, em)["words"]
    out, where = [], lambda w: "work/word_map.json: %s" % w["id"]
    cw, cg = Counter(w["id"] for w in want), Counter(w["id"] for w in got)
    twice = {i for i in cw | cg if cw[i] > 1 or cg[i] > 1}
    for i in sorted(twice):
        w = next(x for x in want + got if x["id"] == i)
        pieces = sorted({x["seg"] + 1 for x in want + got if x["id"] == i})
        out.append(_hit("word-twice", "'%s' shows up twice in the cut (pieces %s); a word belongs in one piece only."
                        % (w["word"], ", ".join(map(str, pieces))), where(w)))
    W, G = {w["id"]: w for w in want}, {w["id"]: w for w in got}
    for i, w in W.items():
        if i not in G:
            out.append(_hit("word-missing", "'%s' is kept in the cut but missing from the word map." % w["word"]
                            + RERUN, where(w)))
    for i, g in G.items():
        w = W.get(i)
        if w is None:
            out.append(_hit("word-not-kept", "'%s' is in the word map but the cut drops it." % g["word"] + RERUN,
                            where(g)))
        elif i not in twice and g.get("seg") != w["seg"]:
            out.append(_hit("word-wrong-piece", "'%s' is mapped to piece %s but sits in piece %d of the cut."
                            % (w["word"], g.get("seg", -1) + 1, w["seg"] + 1) + RERUN, where(w)))
        elif i not in twice:
            for k in ("out_start", "out_end"):
                off = abs(float(g.get(k, 1e9)) - w[k])
                if off > TOL + 1e-9:
                    out.append(_hit("word-time", "'%s' %s at %.3f s in the word map but belongs at %.3f s in the cut "
                                    "(%.0f ms off; the limit is 6 ms)." % (w["word"], k[4:] + "s", float(g.get(k, -1)),
                                                                          w[k], off * 1000) + RERUN, where(w)))
                    break
    return out


def main():
    ensure_utf8_output()
    if len(sys.argv) != 2:
        raise SystemExit("usage: map_check.py <reel_dir>")
    hits = run(dict(reel_dir=sys.argv[1], fps=None, cuts=None, beats=None, render=None))
    for h in hits:
        print("%s  %s  %s  (%s)" % (h["level"].upper(), h["check"], h["msg"], h["where"]))
    blocks = sum(h["level"] == "block" for h in hits)
    print("map check: %s" % ("%d block(s): fix these before rendering" % blocks if blocks
                             else "clean, every kept word is in the word map at the right time"))
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
