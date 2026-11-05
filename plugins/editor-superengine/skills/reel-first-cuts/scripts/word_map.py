#!/usr/bin/env python3
"""Stage 4 -> render: write work/word_map.json, where every kept word lands in the cut, before anything renders.

    <editor python> -X utf8 -I word_map.py <reel_dir>

Reads : <reel>/work/cuts.json (gaps.py snap_cuts: fps, speed, frame segments) and
        <reel>/work/edit_map.json (build_edit_map.py: the source word times)
Writes: <reel>/work/word_map.json
        {version, cuts_sha256, edit_map_sha256, fps, speed,
         words: [{id, word, seg, src_start, src_end, out_start, out_end}]}

A word is kept when its source `start` falls inside a segment's source span: src_in_f/fps <= start < src_out_f/fps.
`start` (the edit map's aligned start) is the anchor gaps.py places cuts from: overlaps() (gaps.py:146-147) and
keep_edge_words() (gaps.py:160-183) test the edit map's start/end, never parakeet_start, and words with status
"unresolved" (not in the audio) are dropped before any of that (gaps.py:433), so they are dropped here too.
Output time of a source time t in its segment: out_in_f/fps + (t - src_in_f/fps) / speed, speed from cuts.json
(1.0 when absent). A word whose start sits in two segments (overlapping segments) is listed once per segment, so
map_check.py can block it. The two sha256 fields are of the input files' bytes: the map is stale once either changes.
"""
import hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(cuts, edit_map):
    """The word map's body from parsed cuts.json + edit_map.json (no file reads, no hashes)."""
    fps, speed = cuts["fps"], cuts.get("speed", 1.0)
    words = [w for w in edit_map["words"] if w.get("status") != "unresolved"]
    out = []
    for w in words:
        for k, s in enumerate(cuts["segments"]):
            s0, s1, c0 = s["src_in_f"] / fps, s["src_out_f"] / fps, s["out_in_f"] / fps
            if s0 <= w["start"] < s1:
                out.append(dict(id=w["id"], word=w["word"].strip(), seg=k, src_start=w["start"], src_end=w["end"],
                                out_start=round(c0 + (w["start"] - s0) / speed, 6),
                                out_end=round(c0 + (w["end"] - s0) / speed, 6)))
    return dict(version=1, fps=fps, speed=speed, words=out)


def write(reel_dir):
    work = Path(reel_dir) / "work"
    cuts_p, em_p = work / "cuts.json", work / "edit_map.json"
    m = build(json.loads(cuts_p.read_text(encoding="utf-8")), json.loads(em_p.read_text(encoding="utf-8")))
    m = dict(version=m.pop("version"), cuts_sha256=sha(cuts_p), edit_map_sha256=sha(em_p), **m)
    (work / "word_map.json").write_bytes(json.dumps(m, ensure_ascii=False, indent=1).encode("utf-8"))
    return m


def main():
    ensure_utf8_output()
    if len(sys.argv) != 2:
        raise SystemExit("usage: word_map.py <reel_dir>")
    work = Path(sys.argv[1]) / "work"
    for need in ("cuts.json", "edit_map.json"):
        if not (work / need).exists():
            raise SystemExit("ERROR: %s is missing: run gaps.py (cuts.json) and build_edit_map.py first" % (work / need))
    m = write(sys.argv[1])
    print("word_map.json: %d kept words in %d segments, speed %s" % (
        len(m["words"]), len({w["seg"] for w in m["words"]}), m["speed"]))


if __name__ == "__main__":
    main()
