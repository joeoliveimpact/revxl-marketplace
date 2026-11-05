"""Set up the grade for one reel: measure the footage, bake the looks, write grade.json at the identity.

    <editor python> -X utf8 -I make_grade.py --reel <name> --video <raw or cut .mp4> --reel-dir <videos/<reel>> \
        [--look <id> --strength <0-1>]

Writes into <reel-dir>/grade/: grade-config.json, three reference frames (grade-f25/50/75.jpg) and looks/<id>.cube
(each look baked at full strength and run through the skin guard). Then <reel-dir>/grade.json: one take (the whole
video), correction at the identity, the chosen look (default none) and the cube for the cut with its sha256.

The grade opens at the identity: nothing changes until you pick something. What it measures goes in "suggested",
the one-click fix the Grade Board offers:
  - the black point (0.5th percentile luma) and white point (99.5th) across the three frames;
  - the skin hue, from the dominant saturated hue in the upper-centre of each frame (median of three);
  - which frame carries the most face (skin-mask area), the frame the looks are judged on.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import grade_math as gm  # noqa: E402
import bake_grade as bg  # noqa: E402
import skin_guard as sg  # noqa: E402
from apply_grade import duration, read_frame, run  # noqa: E402

MEASURE_W = 640          # frames are measured at this width at most: enough for percentiles, light on memory


def snap(v, name):
    """Snapped to the slider's own step, so the number on the board is the number that gets sent."""
    step = gm.RANGES[name][2]
    return round(round(v / step) * step, 6)


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Measure a reel and write its grade at the identity")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--reel-dir", required=True, help="videos/<reel>")
    ap.add_argument("--look", default="none")
    ap.add_argument("--strength", type=float, default=1.0)
    a = ap.parse_args()

    video, reel_dir = Path(a.video).resolve(), Path(a.reel_dir).resolve()
    if not video.is_file():
        print(f"There's no video at {video}.")
        return 1
    out = reel_dir / "grade"
    out.mkdir(parents=True, exist_ok=True)
    dur = duration(video)

    frames = []
    for pct in (25, 50, 75):
        t = dur * pct / 100.0
        name = f"grade-f{pct}.jpg"
        run([rt.tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
             "-q:v", "2", "-update", "1", str(out / name)])
        px = read_frame(video, t, MEASURE_W)
        dh = sg.dominant_hue(px)
        frames.append(dict(pct=pct, t=round(t, 3), file=name, _px=px,
                           _hue=None if dh is None else dh[0], _sat=None if dh is None else dh[1]))
    hues = [f["_hue"] for f in frames if f["_hue"] is not None]
    if not hues:
        print("No face found in the upper-centre of any frame, so the skin can't be measured. "
              "Is this a graphics-only video? Ask Claude to set the skin hue by hand.")
        return 1
    off = [(x - hues[0] + 180.0) % 360.0 - 180.0 for x in hues]
    skin_hue = (hues[0] + float(np.median(off))) % 360.0
    skin_sat = float(np.median([f["_sat"] for f in frames if f["_sat"] is not None]))
    luma = np.concatenate([(f["_px"] * gm.LUMA).sum(-1).reshape(-1) for f in frames])
    black, white = float(np.percentile(luma, 0.5)), float(np.percentile(luma, 99.5))
    for f in frames:
        f["skin_area"] = round(float(sg.skin_mask(f["_px"], skin_hue).mean()), 5)
    face = max(frames, key=lambda f: f["skin_area"])
    skin = sg.skin_rgb([face["_px"]])
    for f in frames:
        for k in ("_px", "_hue", "_sat"):
            f.pop(k)

    # every look baked at full strength and checked against this reel's skin
    looks = []
    for lid, lk in bg.load_looks().items():
        rel = f"grade/looks/{lid}.cube"
        lat, _, _ = bg.bake({"look": {"id": lid, "strength": 1.0}})
        bg.write_cube(reel_dir / rel, lat, 33, f"look {lk['name']}")
        ok, nums, msg = sg.check(skin, reel_dir / rel, bool(lk.get("neutral")))
        looks.append(dict(id=lid, name=lk["name"], neutral=bool(lk.get("neutral")), cube=rel, stack=lk["stack"],
                          guard=dict(ok=ok, **nums)))
        print(f"  {'✓' if ok else '✗'} look {lk['name']}: {msg} {nums}")

    measured = dict(black_pct=0.5, black=round(black, 4), white_pct=99.5, white=round(white, 4),
                    skin_hue=round(skin_hue, 1), skin_sat=round(skin_sat, 3), per_frame_hue=[round(x, 1) for x in hues],
                    skin_rgb=[round(float(x), 4) for x in skin])
    suggested = dict(black=snap(black, "black"), white=snap(white, "white"), skin_hue=snap(skin_hue, "skin_hue"))
    # the Grade Board plays the video only when it sits in the reel folder (the board server serves only that)
    video_rel = video.relative_to(reel_dir).as_posix() if video.is_relative_to(reel_dir) else None
    cfg = dict(reel=a.reel, video=video.name, video_rel=video_rel, duration=round(dur, 3), math_version=gm.SPEC["version"],
               measured=measured, correction=gm.defaults(gm.PRE), suggested=suggested,
               frames=frames, face_frame=face["file"], looks=looks)
    (out / "grade-config.json").write_bytes((json.dumps(cfg, indent=1) + "\n").encode("utf-8"))

    print(f"\n{a.reel}: {dur:.2f}s · black {black:.4f} · white {white:.4f} · skin hue {skin_hue:.1f} deg"
          f" · face frame {face['file']}")
    print(f"  -> {out / 'grade-config.json'}")
    look = {"id": a.look, "strength": a.strength}
    _, neutral = bg.look_stack(look)   # refuses an unknown look or a strength outside 0-1
    take = dict(range=[0.0, round(dur, 3)], measured=measured, correction=gm.defaults(gm.PRE))

    def guard(i, cube):
        ok, _, msg = sg.check(skin, cube, neutral)
        return None if ok else msg
    doc, problems = bg.write_grade(reel_dir, [take], look, guard=guard)
    if problems:
        print(f"{problems[0]} (grade.json was not written)")
        return 1
    print(f"  -> {reel_dir / 'grade.json'} (look {doc['look']['id']}, cube {doc['cube']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
