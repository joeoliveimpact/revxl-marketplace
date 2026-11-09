#!/usr/bin/env python3
# Changed from shorts-studio scripts/follow_cut.py (MIT): cuts.json frames and speed, editor tools, frame assertion.
"""Give a synced screen recording the same frame cuts and speed as the reel.

<editor python> -X utf8 -I follow_cut.py screen.mp4 --cuts work/cuts.json --out work/screen-cut.mp4
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output
import runtime as rt
from render import count_frames, joined_tail, video_cut


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--cuts", required=True, help="work/cuts.json, from gaps.py")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cuts = json.loads(Path(a.cuts).read_text(encoding="utf-8"))
    segs, fps, speed = cuts["segments"], cuts["fps"], cuts.get("speed", 1.)
    if len(cuts.get("takes") or {}) > 1 or len({s.get("take", 1) for s in segs}) > 1:
        print("a screen recording can follow one recording's cut; this reel mixes recordings")
        return 2
    if not segs:
        raise ValueError("the cut has no pieces")
    parts = ["[0:v]split=%d%s;" % (len(segs), "".join("[s%d]" % i for i in range(len(segs))))]
    for i, s in enumerate(segs):
        parts.append("[s%d]%s[v%d];" % (i, video_cut(s, fps), i))
    parts.extend(joined_tail(len(segs), fps, speed, audio=False))
    graph = Path(a.out).with_suffix(".graph.txt")
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_bytes("\n".join(parts).encode("utf-8"))
    subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", a.video, "-/filter_complex", str(graph),
                    "-map", "[v]", "-an", "-r", str(fps), "-c:v", "libx264", "-preset", "fast",
                    "-crf", "18", "-pix_fmt", "yuv420p", a.out], check=True, capture_output=True)
    frames = count_frames(a.out)
    if frames != segs[-1]["out_out_f"]:
        raise ValueError("the screen cut has %d frames but cuts.json says %d" % (frames, segs[-1]["out_out_f"]))
    print("screen follows the cut: %d pieces, %d frames -> %s" % (len(segs), frames, a.out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("the screen recording could not follow the cut: " + str(e).strip().splitlines()[0], file=sys.stderr)
        sys.exit(2)
