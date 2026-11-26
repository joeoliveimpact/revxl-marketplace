#!/usr/bin/env python3
"""Pre-render check: beats that use the face card ("Face card + head pop") can draw it.

    python -X utf8 -I face_card_check.py <reel_dir>      exit 1 on any block, else 0

Module contract (H-B6): PHASE = "pre"; run(ctx) returns [{check, level, msg, where}].
ctx = {reel_dir, fps, cuts, beats, render}. A reel with no facecard beat gets no rows. Writes nothing.
- face-card-hidden (warn): the saved editing style track doesn't draw the card (only Layout switches does),
  so those beats show full screen.
- face-card-cutout (block): the head cut-out (work/matte/cutout.mov) is missing, older than the cut, or not
  frame for frame with it; compose refuses the same way before rendering.
- face-card-window (warn): the window compose measured from the cut-out (work/facecard.json) had to be held
  inside the picture, so the head pops less than the layout's data-head-rise or sits off-centre.
Without a style track (no preview yet) only the cut-out is checked; without a measured window, no window row.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2] / "reel-canvas-build" / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
import compose  # noqa: E402
from face_text_check import aroll_path  # noqa: E402  (the cut master compose renders from)

PHASE = "pre"
NAME = "facecard"


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run(ctx):
    reel = Path(ctx["reel_dir"])
    beats = ctx.get("beats")
    if beats is None:
        beats = (_read(reel / "beat-map-selection.json") or {}).get("beats") or []
    numbers = [str(i) for i, b in enumerate(beats, 1) if b.get("layout") == NAME]
    if not numbers:
        return []
    where = "beat " + ", ".join(numbers)
    track = _read(reel / compose.styles.TRACK)
    if track is not None and not compose.card_layouts(track):
        return [dict(check="face-card-hidden", level="warn", where=where,
                     msg="The face card only shows with the Layout switches editing style, so these beats show you "
                         "full screen. Pick Layout switches under Editing style on the Beat Map, then Send.")]
    rows = []
    cuts = ctx.get("cuts") or _read(reel / "work/cuts.json") or {}
    master = aroll_path(reel, cuts)
    segments = cuts.get("segments") or []
    if master is not None and segments:
        problem = compose.head_matte_problem(reel, master, segments[-1]["out_out_f"])
        if problem:
            rows.append(dict(check="face-card-cutout", level="block", where=where, msg=problem))
    window = _read(reel / compose.CARD_WINDOW) if compose.card_src(reel) else None
    if window is not None and window.get("clamped"):
        rows.append(dict(check="face-card-window", level="warn", where=where,
                         msg="Your head sits too near the edge of the picture in this recording for the face card's "
                             "usual framing, so it pops less than usual or sits off-centre in the card. Check those "
                             "beats in the preview."))
    return rows


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    args = ap.parse_args()
    rows = run(dict(reel_dir=args.reel_dir, fps=None, cuts=None, beats=None, render=None))
    for row in rows:
        print("%s  %s  %s  (%s)" % (row["level"].upper(), row["check"], row["msg"], row["where"]))
    return 1 if any(row["level"] == "block" for row in rows) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("The face card check could not finish. Make the cut and the Beat Map Send again, then run QA again.",
              file=sys.stderr)
        sys.exit(1)
