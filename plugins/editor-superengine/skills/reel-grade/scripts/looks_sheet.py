"""The looks contact sheet: the reel's face frame through None and every look, as one labelled image.

    <editor python> -X utf8 -I looks_sheet.py --reel-dir <videos/<reel>> [--tile 480]

Reads <reel-dir>/grade/grade-config.json (make_grade.py writes it, with the face frame and each look's baked cube)
and writes <reel-dir>/grade/looks-sheet.jpg: ffmpeg applies each cube with lut3d and lays the tiles out with
xstack, 3 per row, None first and then the looks in looks.json order; Pillow writes each tile's name on it.
Works without the Grade Board, so a look can be picked from this one picture.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
from apply_grade import filter_arg, run  # noqa: E402

COLS = 3


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="One image of the face frame through every look")
    ap.add_argument("--reel-dir", required=True, help="videos/<reel>")
    ap.add_argument("--tile", type=int, default=480, help="tile width in pixels")
    a = ap.parse_args()
    reel_dir = Path(a.reel_dir).resolve()
    cfg_path = reel_dir / "grade" / "grade-config.json"
    if not cfg_path.is_file():
        print(f"There's no grade set up for this reel yet ({cfg_path} is missing). Run make_grade.py first.")
        return 1
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    tiles = [("None", None)] + [(lk["name"], reel_dir / lk["cube"]) for lk in cfg["looks"]]
    for name, cube in tiles:
        if cube is not None and not cube.is_file():
            print(f"The {name} look's cube is missing ({cube}). Run make_grade.py again.")
            return 1
    n = len(tiles)
    rows = -(-n // COLS)
    chains = [f"[0:v]scale={a.tile}:-2,split={n}" + "".join(f"[s{i}]" for i in range(n))]
    for i, (_, cube) in enumerate(tiles):
        chains.append(f"[s{i}]" + (filter_arg(cube) if cube else "null") + f"[t{i}]")
    # every tile is the same size, so the layout is plain multiples of the first tile's w0/h0
    layout = "|".join("+".join(["w0"] * (i % COLS) or ["0"]) + "_" + "+".join(["h0"] * (i // COLS) or ["0"])
                      for i in range(n))
    chains.append("".join(f"[t{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black[out]")
    sheet = reel_dir / "grade" / "looks-sheet.jpg"
    run([rt.tool("ffmpeg"), "-y", "-v", "error", "-i", str(reel_dir / "grade" / cfg["face_frame"]),
         "-filter_complex", ";".join(chains), "-map", "[out]", "-frames:v", "1", "-q:v", "2", "-update", "1",
         str(sheet)])
    im = Image.open(sheet).convert("RGB")
    tw, th = im.width // COLS, im.height // rows
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=max(14, tw // 16))
    for i, (name, _) in enumerate(tiles):
        x, y = (i % COLS) * tw + 8, (i // COLS) * th + 8
        box = draw.textbbox((x, y), name, font=font)
        draw.rectangle((box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4), fill=(20, 20, 20))
        draw.text((x, y), name, fill=(240, 240, 240), font=font)
    im.save(sheet, quality=92)
    print(f"-> {sheet} ({im.width}x{im.height}, {n} tiles: {', '.join(t[0] for t in tiles)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
