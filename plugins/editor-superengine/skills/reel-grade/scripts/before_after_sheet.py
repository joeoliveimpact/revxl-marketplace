#!/usr/bin/env python3
"""Three before | after pairs at early, middle and late source times.

before_after_sheet.py before.mp4 after.mp4 --out grade/before-after.png
Or omit after.mp4 and pass --lut <the baked grade LUT> to preview it.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]
from win_encoding import ensure_utf8_output
import runtime as rt
from apply_grade import filter_arg


def duration(path):
    p = subprocess.run([rt.tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                       check=True, capture_output=True)
    return float(json.loads(p.stdout)["format"]["duration"])


def frame(path, t, tile, cube=None):
    vf = f"scale={tile}:-2" + ("," + filter_arg(cube) if cube else "")
    p = subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-ss", f"{t:.6f}", "-i", str(path),
                        "-vf", vf, "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"],
                       check=True, capture_output=True)
    with Image.open(io.BytesIO(p.stdout)) as im:
        return im.convert("RGB")


def sheet(before, after, out, *, tile=320, cube=None):
    if not Path(before).is_file() or (after is not None and not Path(after).is_file()) or (cube is not None and not Path(cube).is_file()):
        raise ValueError("Both comparison sources (or the grade cube) must exist.")
    length = min(duration(before), duration(after)) if after is not None else duration(before)
    if length <= 0 or not 32 <= tile <= 640:
        raise ValueError("Choose a positive duration and tile width from 32 to 640.")
    pairs = []
    for fraction in (.1, .5, .9):
        t = length * fraction
        left, right = frame(before, t, tile), frame(after or before, t, tile, cube)
        if right.size != left.size:
            right = right.resize(left.size)
        pairs.append((t, left, right))
    w, h = pairs[0][1].size
    im = Image.new("RGB", (2 * w, 3 * h))
    draw = ImageDraw.Draw(im)
    for i, (t, left, right) in enumerate(pairs):
        im.paste(left, (0, i * h)); im.paste(right, (w, i * h))
        for x, label in ((0, "Before"), (w, "After")):
            draw.rectangle((x, i * h, x + w, i * h + 24), fill="#181818")
            draw.text((x + 6, i * h + 5), f"{label} | {t:.2f} s", fill="white")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, format="PNG")


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path, nargs="?")
    ap.add_argument("--lut", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tile", type=int, default=320)
    a = ap.parse_args(argv)
    if (a.after is None) == (a.lut is None):
        ap.error("give either an after video or --lut")
    try:
        sheet(a.before, a.after, a.out, tile=a.tile, cube=a.lut)
        print(f"Before/after sheet -> {a.out}")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("The before/after sheet could not be made. Check both sources and the grade cube.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
