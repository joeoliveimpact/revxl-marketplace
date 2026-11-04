#!/usr/bin/env python3
"""style-decoder — palette extraction.

    python stylepalette.py <style-slug> <src-id> [--zones <file.json>] [--k 5]

Dominant colors per zone across sampled base frames -> palette.json + a swatch
strip PNG (evidence for the contact sheet / runbook).

Zones default to horizontal thirds (top/mid/bottom). Once layout modes are
known, the decode phase can re-run with --zones pointing at a JSON list of
{"id","rect_pct":[x,y,w,h]} matching the discovered panel geometry.

Pure Pillow (adaptive palette quantize = median-cut); no other dependencies.
Colors come from platform-compressed 512px frames — treat hex values as tokens,
not colorimetric truth. Contract: stylepalette-contract.md.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stylespec  # noqa: E402  (also puts skills/_shared on sys.path)
from win_encoding import ensure_utf8_output  # noqa: E402

DEFAULT_ZONES = [
    {"id": "top", "rect_pct": [0, 0, 100, 33]},
    {"id": "mid", "rect_pct": [0, 33, 100, 34]},
    {"id": "bottom", "rect_pct": [0, 67, 100, 33]},
]
SAMPLE_FRAMES = 12


def dominant_colors(img, k: int) -> list[tuple[str, float]]:
    """[(hex, share)] via Pillow adaptive palette (median-cut)."""
    from PIL import Image
    small = img.convert("RGB").resize((96, 96))
    q = small.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    # histogram() of a "P" image = pixel count per palette index. getdata() is
    # deprecated (removed in Pillow 14); histogram() works on every version.
    counts = Counter({i: n for i, n in enumerate(q.histogram()) if n})
    total = sum(counts.values())
    out = []
    for idx, n in counts.most_common(k):
        r, g, b = pal[idx * 3: idx * 3 + 3]
        out.append((f"#{r:02X}{g:02X}{b:02X}", round(n / total, 3)))
    return out


def main() -> None:
    ensure_utf8_output()
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow (the image library) isn't installed in this Python — the palette step needs it")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("src")
    ap.add_argument("--zones", default="", help="JSON file: [{id, rect_pct:[x,y,w,h]}]")
    ap.add_argument("--k", type=int, default=5, help="colors per zone")
    args = ap.parse_args()

    d = os.path.join(stylespec.style_dir(args.slug), "sources", args.src)
    frames = sorted(glob.glob(os.path.join(d, "frames", "base_*.jpg")))
    if not frames:
        sys.exit(f"no base frames in {d}/frames — run styleframes.py first")
    step = max(1, len(frames) // SAMPLE_FRAMES)
    sample = frames[::step][:SAMPLE_FRAMES]

    zones = DEFAULT_ZONES
    if args.zones:
        with open(args.zones, encoding="utf-8") as f:
            zones = json.load(f)

    result = {"sampled_frames": [os.path.basename(p) for p in sample],
              "zones": []}
    swatch_rows = []
    for z in zones:
        x, y, w, h = z["rect_pct"]
        agg = Counter()
        for p in sample:
            im = Image.open(p)
            W, H = im.size
            crop = im.crop((int(W * x / 100), int(H * y / 100),
                            int(W * (x + w) / 100), int(H * (y + h) / 100)))
            for hex_, share in dominant_colors(crop, args.k):
                agg[hex_] += share
        total = sum(agg.values()) or 1
        colors = [{"hex": hex_, "share": round(v / total, 3)}
                  for hex_, v in agg.most_common(args.k)]
        result["zones"].append({"id": z["id"], "rect_pct": z["rect_pct"], "colors": colors})
        swatch_rows.append((z["id"], colors))

    with open(os.path.join(d, "palette.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # swatch strip: one row per zone, k blocks wide
    sw, sh = 120, 60
    from PIL import Image as PImage
    sheet = PImage.new("RGB", (sw * args.k, sh * len(swatch_rows)), (24, 24, 24))
    for r, (_zid, colors) in enumerate(swatch_rows):
        for c, col in enumerate(colors):
            block = PImage.new("RGB", (sw, sh),
                               tuple(int(col["hex"][i:i + 2], 16) for i in (1, 3, 5)))
            sheet.paste(block, (c * sw, r * sh))
    strip = os.path.join(d, "palette-swatch.png")
    sheet.save(strip)
    print(f"[palette] {len(zones)} zones x top-{args.k} -> palette.json, {os.path.basename(strip)}")
    for z in result["zones"]:
        tops = ", ".join(f"{c['hex']}({c['share']})" for c in z["colors"][:3])
        print(f"  {z['id']:>8}: {tops}")


if __name__ == "__main__":
    main()
