"""Burn a baked .cube into a video (one generation, ffmpeg, CRF 14) or into a still image.

    <editor python> -X utf8 -I apply_grade.py <video> <grade>.cube -o <graded.mp4>
    <editor python> -X utf8 -I apply_grade.py <video> <grade>.cube -o <probe.mp4> --ss 12.5 -t 2   # a short probe
    <editor python> -X utf8 -I apply_grade.py <frame.png> <grade>.cube -o <graded.png>             # a still

The picture is always ffmpeg's, never the browser's: browser colour management shifts what a canvas readback
contains, so the Grade Board is the judging surface and this is the writing surface.

The PSNR it prints is a SANITY number, not a quality gate. A grade is supposed to change the picture, so a high
number means the cube barely did anything and a low one means it did a lot. It catches the two silent failures: a
lut3d that never loaded (PSNR = inf, output identical to the source) and a chain that mangled the frame (under 12 dB).

Also the home of the frame reader (read_frame) the other grade scripts share.
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

IMAGES = {".png", ".jpg", ".jpeg"}


def run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)


def duration(path):
    """Seconds of the video stream (a still reads 0)."""
    if Path(path).suffix.lower() in IMAGES:
        return 0.0
    p = run([rt.tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], 120)
    return float(json.loads(p.stdout)["format"]["duration"])


def read_frame(path, t=0.0, max_w=None):
    """One frame as float64 RGB in [0,1], shape (h, w, 3). ffmpeg decodes (and rotates), Pillow reads the PNG."""
    cmd = [rt.tool("ffmpeg"), "-v", "error"]
    if Path(path).suffix.lower() not in IMAGES:
        cmd += ["-ss", f"{t:.3f}"]
    cmd += ["-i", str(path), "-frames:v", "1"]
    if max_w:
        cmd += ["-vf", f"scale='min(iw,{int(max_w)})':-2"]
    p = run(cmd + ["-f", "image2pipe", "-c:v", "png", "-"], 300)
    if not p.stdout:
        raise RuntimeError(f"no frame at {t:.2f}s in {Path(path).name}")
    return np.asarray(Image.open(io.BytesIO(p.stdout)).convert("RGB"), dtype=np.float64) / 255.0


def filter_arg(cube: Path) -> str:
    """A Windows path inside an ffmpeg filtergraph.

    Three things all have to be true or the graph fails to parse: forward slashes, the drive colon escaped, and the
    whole thing single-quoted. Escaped but unquoted is NOT enough: the parser has already split on the colon.
    """
    p = str(Path(cube).resolve())
    if "'" in p:
        raise SystemExit(f"The cube's folder path has an apostrophe, which ffmpeg can't read: {p}. Move it.")
    return "lut3d=file='" + p.replace("\\", "/").replace(":", "\\:") + "'"


def apply(src, cube, out, ss=None, seconds=None):
    """Run the ffmpeg pass; returns the encode time in seconds."""
    src, out = Path(src), Path(out)
    cmd = [rt.tool("ffmpeg"), "-y", "-v", "error"]
    if ss:
        cmd += ["-ss", f"{ss:.3f}"]
    cmd += ["-i", str(src)]
    if seconds:
        cmd += ["-t", f"{seconds:.3f}"]
    cmd += ["-vf", filter_arg(cube)]
    if out.suffix.lower() in IMAGES:
        cmd += ["-frames:v", "1", "-update", "1"]
    else:
        cmd += ["-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy"]
    t0 = time.time()
    run(cmd + [str(out)], 7200)
    return time.time() - t0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Apply a baked .cube with ffmpeg")
    ap.add_argument("source", help="a video, or a .png/.jpg still")
    ap.add_argument("cube_path", metavar="cube")
    ap.add_argument("-o", "--out", required=True, help=".mp4 for a video, .png/.jpg for a still")
    ap.add_argument("--ss", type=float, default=None, help="start offset (probe renders only)")
    ap.add_argument("-t", "--seconds", type=float, default=None, help="duration (probe renders only)")
    a = ap.parse_args()
    src, cube, out = Path(a.source), Path(a.cube_path), Path(a.out)
    for p, what in ((src, "source"), (cube, "cube")):
        if not p.is_file():
            print(f"There's no {what} file at {p}.")
            return 1
    try:
        enc = apply(src, cube, out, a.ss, a.seconds)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg could not apply the grade: {(e.stderr or b'').decode('utf-8', 'replace').strip()[-300:]}")
        return 1
    mid = duration(out) / 2.0
    before, after = read_frame(src, (a.ss or 0.0) + mid), read_frame(out, mid)
    if before.shape != after.shape:
        print(f"The picture size changed {before.shape[1]}x{before.shape[0]} -> {after.shape[1]}x{after.shape[0]}; "
              "a grade must never resize.")
        return 1
    mse = float((((before - after) * 255.0) ** 2).mean())
    psnr = float("inf") if mse == 0 else 10.0 * np.log10(255.0 ** 2 / mse)
    print(f"{out.name}: {after.shape[1]}x{after.shape[0]} · applied in {enc:.1f}s · {out.stat().st_size / 1e6:.2f} MB")
    print(f"  cube: {cube.name}")
    print(f"  mid-frame PSNR vs source: {psnr:.2f} dB (sanity only - a grade SHOULD move this)")
    if psnr == float("inf"):
        print("  WARNING: identical to the source. The lut3d did nothing - check the cube loaded.")
    elif psnr < 12:
        print("  WARNING: under 12 dB. That is not a grade, that is damage. Check the cube.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
