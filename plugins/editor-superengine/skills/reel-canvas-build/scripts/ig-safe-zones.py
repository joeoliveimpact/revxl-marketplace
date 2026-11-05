#!/usr/bin/env python
"""
ig-safe-zones.py - flag anything that lands where Instagram's UI covers it.

Reserve, of a 1080x1920 reel (strictest of the published figures, not an average -
sources range top 108-220, bottom 320-450, right 90-120):

    top 220   account name + follow button
    bottom 450  caption, audio strip, like/share row
    right 120   action rail (like / comment / share / remix)
    left 60     gutter

Leaves a 900x1250 box that always survives. Corroborated independently: the
pixel-panel-explainer spec measures the reference reel's own margins at 72px
left/right and ~140px top on 720x1280 -> 108/210 at 1080x1920.

Text-bearing elements only. Structural cards are exempt on purpose: a creator
card bleeding off the bottom is a design choice (spec rule o1); covered TEXT is
a defect. Pass --all to check every box regardless.

Usage
  python ig-safe-zones.py --svg <file.html|file.svg>      # scrape SVG frames
  python ig-safe-zones.py --json <boxes.json>             # [{label,x,y,w,h}, ...]
  python ig-safe-zones.py --box LABEL X Y W H             # one-off, canvas px

Options
  --canvas W H   canvas size for --json/--box (default 1080 1920)
  --all          include structural boxes, not just text-bearing ones
  --quiet        only print violations

Exit code 1 when anything violates, so it works as a build gate.
"""
import argparse, json, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESERVE = {"top": 220 / 1920, "bottom": 450 / 1920, "left": 60 / 1080, "right": 120 / 1080}

# fills/strokes that mark a box as carrying text in our sketches
TEXTISH = ("#333", "D97757", "F0C43C")

# Sketch convention: annotation text (labels ABOUT the frame, which never ship)
# is drawn in the mute grey or the teal. Reel content is ink / white / coral / gold.
# Without this split the checker flags its own margin notes and the signal drowns.
ANNOTATION_FILLS = ("#8a857d", "#007299")


def violations(label, x, y, w, h, W, H):
    out = []
    if y < RESERVE["top"] * H:
        out.append("top reserve (account name / follow)")
    if y + h > (1 - RESERVE["bottom"]) * H:
        out.append("bottom reserve (caption / audio / like row)")
    if x < RESERVE["left"] * W:
        out.append("left gutter")
    if x + w > (1 - RESERVE["right"]) * W:
        out.append("right action rail")
    return out


def from_svg(path, include_all):
    """Scrape <rect> and <text> out of every <svg viewBox=...> in the file."""
    src = open(path, encoding="utf-8").read()
    boxes = []
    for si, svg in enumerate(re.finditer(r'<svg[^>]*viewBox="([\d.\s-]+)"(.*?)</svg>', src, re.S), 1):
        vb = [float(v) for v in svg.group(1).split()]
        if len(vb) != 4:
            continue
        W, H = vb[2], vb[3]
        body = svg.group(2)
        for m in re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"([^>]*)>', body):
            x, y, w, h = (float(m.group(i)) for i in range(1, 5))
            rest = m.group(5)
            if w >= W * 0.95 and h >= H * 0.95:
                continue  # the frame border itself
            textish = any(t in rest for t in TEXTISH)
            if not textish and not include_all:
                continue
            boxes.append((f"frame {si} rect", x, y, w, h, W, H))
        for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)"([^>]*)>(.*?)</text>', body, re.S):
            x, y = float(m.group(1)), float(m.group(2))
            attrs, txt = m.group(3), re.sub(r"\s+", " ", m.group(4)).strip()
            if not include_all and any(f in attrs for f in ANNOTATION_FILLS):
                continue  # a note about the frame, not something that ships in it
            size = float(re.search(r'font-size="([\d.]+)"', attrs).group(1)) if 'font-size="' in attrs else 8.0
            # approximate ink box from the anchor point
            width = len(txt) * size * 0.55
            x0 = x - width / 2 if 'text-anchor="middle"' in attrs else x
            boxes.append((f'frame {si} text "{txt[:28]}"', x0, y - size, width, size * 1.2, W, H))
    return boxes


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--svg")
    p.add_argument("--json")
    p.add_argument("--box", nargs=5, metavar=("LABEL", "X", "Y", "W", "H"))
    p.add_argument("--canvas", nargs=2, type=float, default=[1080, 1920], metavar=("W", "H"))
    p.add_argument("--all", action="store_true")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args()

    if a.svg:
        boxes = from_svg(a.svg, a.all)
    elif a.json:
        W, H = a.canvas
        boxes = [(b["label"], b["x"], b["y"], b["w"], b["h"], W, H) for b in json.load(open(a.json))]
    elif a.box:
        W, H = a.canvas
        L, x, y, w, h = a.box[0], *(float(v) for v in a.box[1:])
        boxes = [(L, x, y, w, h, W, H)]
    else:
        p.print_help()
        return 0

    bad = []
    for label, x, y, w, h, W, H in boxes:
        v = violations(label, x, y, w, h, W, H)
        if v:
            bad.append((label, x, y, w, h, W, H, v))

    if not a.quiet:
        print("reserve: top %.1f%% | bottom %.1f%% | left %.1f%% | right %.1f%%"
              % (RESERVE["top"] * 100, RESERVE["bottom"] * 100,
                 RESERVE["left"] * 100, RESERVE["right"] * 100))
        print("checked %d element(s)%s" % (len(boxes), "" if a.all else " (text-bearing only)"))

    for label, x, y, w, h, W, H, v in bad:
        print("  VIOLATION  %s" % label)
        print("             x %.4g..%.4g (%.1f%%..%.1f%%)  y %.4g..%.4g (%.1f%%..%.1f%%)"
              % (x, x + w, x / W * 100, (x + w) / W * 100, y, y + h, y / H * 100, (y + h) / H * 100))
        for r in v:
            print("             -> %s" % r)

    print("\n%d violation(s)" % len(bad) if bad else "\nclean - nothing in a reserved zone")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
