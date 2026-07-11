#!/usr/bin/env python3
"""Export carousel slide HTML files to PNGs (and optionally a single PDF).

Usage:
    python render_slides.py <html_dir> [--out <png_dir>] [--pdf <file.pdf>]
                            [--selector "#slide"] [--width 1080] [--height 1350]

Screenshots the slide ELEMENT (element.screenshot(), never a viewport clip) so the
export is exactly the slide's pixels. HTML files are processed in sorted filename
order (slide_01.html, slide_02.html, ...). Requires: pip install playwright &&
playwright install chromium.
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html_dir", help="directory containing slide_*.html files")
    ap.add_argument("--out", default=None, help="PNG output dir (default: <html_dir>/png)")
    ap.add_argument("--pdf", default=None, help="also assemble PNGs into this single PDF (LinkedIn)")
    ap.add_argument("--selector", default="#slide", help="slide element selector (default: #slide)")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1350)
    args = ap.parse_args()

    html_dir = Path(args.html_dir)
    pages = sorted(html_dir.glob("*.html"))
    if not pages:
        print(json.dumps({"ok": False, "error": f"no .html files in {html_dir}"}))
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"ok": False, "error": "playwright not installed",
                          "fix": "pip install playwright && playwright install chromium"}))
        return 1

    out_dir = Path(args.out) if args.out else html_dir / "png"
    out_dir.mkdir(parents=True, exist_ok=True)
    pngs = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": args.width + 100, "height": args.height + 100})
        for html_file in pages:
            page.goto(html_file.resolve().as_uri())
            page.wait_for_timeout(250)  # fonts/paint settle
            el = page.query_selector(args.selector)
            if el is None:
                print(json.dumps({"ok": False, "error": f"{args.selector} not found in {html_file.name}"}))
                browser.close()
                return 1
            png_path = out_dir / (html_file.stem + ".png")
            el.screenshot(path=str(png_path))
            pngs.append(png_path)
        browser.close()

    result = {"ok": True, "slides": len(pngs), "png_dir": str(out_dir)}

    if args.pdf:
        try:
            # JpegImagePlugin import is load-bearing: Pillow's PDF writer needs the JPEG
            # encoder registered, and a bare `from PIL import Image` may not register it.
            from PIL import Image, JpegImagePlugin  # noqa: F401
        except ImportError:
            result["pdf"] = None
            result["pdf_error"] = "Pillow not installed (pip install pillow); PNGs exported fine"
            print(json.dumps(result))
            return 0
        try:
            images = [Image.open(f).convert("RGB") for f in pngs]
            pdf_path = Path(args.pdf)
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            images[0].save(pdf_path, save_all=True, append_images=images[1:])
        except Exception as e:
            result["pdf"] = None
            result["pdf_error"] = f"PDF assembly failed ({e}); PNGs exported fine"
            print(json.dumps(result))
            return 0
        size_mb = pdf_path.stat().st_size / 1_048_576
        result["pdf"] = str(pdf_path)
        result["pdf_pages"] = len(images)
        result["pdf_mb"] = round(size_mb, 1)
        if size_mb > 10:
            result["pdf_warning"] = "over LinkedIn's 10MB comfort zone — reduce image detail or slide count"

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
