#!/usr/bin/env python3
"""Sample every second for persistent text-like bands; save the intake sheet.

caption_scan.py recording.mp4 --work work
Exit 3 means likely burned-in words, 0 means no persistent band found.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output
import runtime as rt


def bands(image):
    """Text edges alternate bright/dark many times along a short row group.

    Require several busy rows, a wide horizontal spread, and a shallow band.
    This deliberately simple contrast heuristic is not OCR: textures can
    resemble letters. Persistence below means at least two 1 fps samples.
    """
    gray = image.convert("L")
    w, h = gray.size
    pixels = gray.load()
    rows = []
    for y in range(h):
        edges = [x for x in range(1, w) if abs(pixels[x, y] - pixels[x - 1, y]) >= 65]
        if len(edges) >= 10 and edges[-1] - edges[0] >= w * .28:
            rows.append(y)
    groups = []
    for y in rows:
        if groups and y - groups[-1][-1] <= 3:
            groups[-1].append(y)
        else:
            groups.append([y])
    return [(g[0] + g[-1]) / 2 / h for g in groups if len(g) >= 5 and g[-1] - g[0] <= h * .12]


def scan(video, work):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    hits = []
    with tempfile.TemporaryDirectory(prefix="intake-", dir=work) as tmp:
        subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-i", str(video),
                        "-vf", "fps=1,scale=320:-2", str(Path(tmp) / "%08d.png")],
                       check=True, capture_output=True)
        paths = sorted(Path(tmp).glob("*.png"))
        if not paths:
            raise ValueError("the recording has no 1 fps samples")
        with Image.open(paths[0]) as first:
            th = round(first.height * 160 / first.width)
        sheet = Image.new("RGB", (160 * min(10, len(paths)), (th + 20) * math.ceil(len(paths) / 10)), "#181818")
        draw = ImageDraw.Draw(sheet)
        for i, path in enumerate(paths):
            with Image.open(path) as frame:
                hits.append(bands(frame))
                thumb = frame.convert("RGB").resize((160, th))
            x, y = i % 10 * 160, i // 10 * (th + 20)
            sheet.paste(thumb, (x, y))
            draw.text((x + 4, y + th + 2), "%d s" % i, fill="white")
        sheet.save(work / "intake-sheet.png")
    flagged = set()
    for candidates in hits:
        for center in candidates:
            matches = [i for i, row in enumerate(hits) if any(abs(y - center) <= .025 for y in row)]
            if len(matches) >= 2:
                flagged.update(matches)
    # ponytail: tuned on synthetic clips only. Before refusing real footage,
    # Claude must inspect intake-sheet.png and confirm these are burned words.
    doc = dict(burned_in=bool(flagged), score=round(len(flagged) / len(hits), 3), flagged_s=sorted(flagged))
    (work / "intake.json").write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    return doc


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", type=Path)
    ap.add_argument("--work", type=Path, default=Path("work"))
    a = ap.parse_args(argv)
    try:
        doc = scan(a.video, a.work)
        if doc["burned_in"]:
            print("The footage already has words burned in; the editor won't cover them.")
            return 3
        print("No persistent burned-in text band found; review the intake sheet.")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("The caption intake scan could not finish. Check the recording and editor video tools.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
