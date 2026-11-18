"""Measure a carousel slide instead of eyeballing it.

  python slide_check.py palette <image> [<image> ...] [--top 6]
      Dominant colours of each image as hex + share. For reference carousels and decks with no build code.
      Values are measured from pixels: record them as "estimated".

  python slide_check.py contrast <slide.html> [<slide.html> ...] [--scale 0.33] [--size 1080x1350] [--all] [--json]
      Renders each HTML file (one slide per file, any markup) and for every text element compares its colour
      with the real pixels around it (median of a ring 3 to 6 px outside its box), so text over photos is
      checked too. Opacity, the element's own and its parents', is blended in. --scale is viewed size divided
      by authored size (0.33 for a 1080 px slide seen at 360 px); it decides which text counts as large.
      Prints failing blocks only unless --all. Exit code 1 if any text is under its WCAG threshold.
      Not meaningful over placeholder frames: run it on slides with their real art.

  python slide_check.py --selftest

Needs Pillow; contrast also needs Playwright with Chromium. Methods ported from the MIT-licensed
claude-code-video-toolkit (ring-median contrast) and Apache-2.0 hyperframes-skills (bucket palette).
"""
import argparse, io, json, pathlib, re, sys
from collections import Counter


def lum(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg, bg, a):
    return tuple(a * f + (1 - a) * b for f, b in zip(fg, bg))


def hexof(rgb):
    return "#%02X%02X%02X" % tuple(int(round(c)) for c in rgb)


def palette(img, top=6):
    """Bucket pixels at 4 bits per channel; return [(hex, share)] of the biggest buckets, averaged."""
    img = img.convert("RGB")
    img.thumbnail((240, 240))
    sums, counts = {}, Counter()
    raw = img.tobytes()
    for r, g, b in zip(raw[0::3], raw[1::3], raw[2::3]):
        k = (r >> 4, g >> 4, b >> 4)
        counts[k] += 1
        s = sums.setdefault(k, [0, 0, 0])
        s[0] += r; s[1] += g; s[2] += b
    total = sum(counts.values())
    return [(hexof([c / n for c in sums[k]]), n / total) for k, n in counts.most_common(top)]


def ring_median(img, box):
    """Per-channel median of the pixels 3 to 6 px outside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    W, H = img.size
    px = []
    for bx in ((x0 - 6, y0 - 6, x1 + 6, y0 - 3), (x0 - 6, y1 + 3, x1 + 6, y1 + 6),
               (x0 - 6, y0, x0 - 3, y1), (x1 + 3, y0, x1 + 6, y1)):
        a, b, c, d = max(0, bx[0]), max(0, bx[1]), min(W, bx[2]), min(H, bx[3])
        if c > a and d > b:
            raw = img.crop((a, b, c, d)).tobytes()
            px.extend(zip(raw[0::3], raw[1::3], raw[2::3]))
    if not px:
        return None
    return tuple(sorted(p[k] for p in px)[len(px) // 2] for k in range(3))


# Text elements = elements with a direct, non-empty text node. Colour is the computed colour.
COLLECT = """() => [...document.querySelectorAll('body *')].filter(e =>
  [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && e.getClientRects().length).map(e => {
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  let op = 1;  // opacity multiplies down the tree: a footer at opacity .6 dims the text inside it
  for (let n = e; n && n.nodeType === 1; n = n.parentElement) op *= parseFloat(getComputedStyle(n).opacity);
  return {text: e.textContent.trim().slice(0, 40), color: s.color, size: parseFloat(s.fontSize),
          weight: parseInt(s.fontWeight) || 400, opacity: op, box: [r.left, r.top, r.right, r.bottom]};
})"""


def check_slide(page, path, scale):
    from PIL import Image
    page.goto(pathlib.Path(path).resolve().as_uri())
    page.evaluate("document.fonts.ready")
    items = page.evaluate(COLLECT)
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    out = []
    for t in items:
        m = re.match(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?", t["color"])
        bg = ring_median(img, t["box"])
        if not m or bg is None:
            continue
        alpha = t["opacity"] * (float(m.group(4)) if m.group(4) else 1.0)
        fg = blend(tuple(float(m.group(i)) for i in (1, 2, 3)), bg, alpha)  # see-through text as it lands on its ground
        seen = t["size"] * scale  # size as the viewer sees it; --scale 0.33 for a 1080 slide shown at 360
        large = seen >= 24 or (seen >= 18.66 and t["weight"] >= 700)
        need = 3.0 if large else 4.5
        r = ratio(fg, bg)
        out.append(dict(t, ratio=round(r, 2), need=need, ok=r >= need, bg=hexof(bg), fg=hexof(fg), alpha=round(alpha, 2)))
    return out


def selftest():
    from PIL import Image
    assert round(ratio((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert round(ratio((196, 86, 42), (244, 240, 232)), 1) == 3.9, ratio((196, 86, 42), (244, 240, 232))
    img = Image.new("RGB", (100, 100), (244, 240, 232))
    img.paste((196, 86, 42), (0, 0, 30, 100))
    p = palette(img, 2)
    assert p[0][0] == "#F4F0E8" and p[1][0] == "#C4562A" and abs(p[1][1] - 0.3) < 0.02, p
    assert ring_median(img, (50, 40, 80, 60)) == (244, 240, 232)
    assert round(ratio(blend((255, 255, 255), (0, 0, 0), 0.6), (0, 0, 0)), 1) == 7.4, ratio(blend((255, 255, 255), (0, 0, 0), 0.6), (0, 0, 0))
    print("selftest OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # slide copy holds symbols cp1252 cannot print
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["palette", "contrast"])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--scale", type=float, default=1.0, help="viewed size / authored size (0.33 for a 1080px slide in a phone feed)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="print every text block, not only the failing ones")
    ap.add_argument("--size", default="1080x1350", help="slide size in px, WxH")
    a = ap.parse_args()
    if a.mode == "palette":
        from PIL import Image
        res = {f: palette(Image.open(f), a.top) for f in a.files}
        if a.json:
            print(json.dumps(res))
        else:
            for f, cols in res.items():
                print(pathlib.Path(f).name + "  " + "  ".join(f"{h} {s:.0%}" for h, s in cols))
        sys.exit(0)
    from playwright.sync_api import sync_playwright
    fails, res = 0, {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        w, h = (int(v) for v in a.size.lower().split("x"))
        pg = b.new_page(viewport={"width": w, "height": h})
        for f in a.files:
            res[f] = check_slide(pg, f, a.scale)
        b.close()
    if a.json:
        print(json.dumps(res))
    for f, rows in res.items():
        bad = [r for r in rows if r.get("ok") is False]
        fails += len(bad)
        if not a.json:
            print(f"{pathlib.Path(f).name}: {len(rows)} text blocks, {len(bad)} under threshold")
            for r in (rows if a.all else bad):
                print(f"  {r['ratio']}:1 (needs {r['need']}) {r['color']} on {r['bg']} at {r['size']:.0f}px  \"{r['text']}\"")
    sys.exit(1 if fails else 0)
