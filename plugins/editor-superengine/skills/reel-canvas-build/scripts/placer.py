# Adapted from shorts-studio/scripts/edit_build.py (MIT), hits() and caption spots only.
# Copyright (c) 2026 Claude Video Studio contributors
# Changes by REVXL: corner rectangles, master-pixel head mapping, sampled moves,
# Instagram-safe candidates, timed fallback notes and still-graphic overlap notes.
# Graphics zoning from the source is not used.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Face-safe caption geometry on the 1080x1920 master; renders and writes nothing.

load_ctx(reel_dir) reads the existing style track, cut list, Beat Map Send and
optional anchors. Anchor boxes are normalized (left, top, right, bottom), in the
same master frame as the anchor centres. All returned boxes use master-pixel
corners. head_box_at() and place() include both requested frames; cut segments,
hook and plate lifetimes retain their stored exclusive end frames.

ghosts(ctx, bands) accepts records {start_f, end_f, box: (x0, y0, x1, y1)}.
Missing-anchor and tight-shot notes accumulate in ctx["notes"] (deduplicated).
place() prefers a clear text-safe candidate. If none is clear, it minimizes
overlap area with the span's zoomed head envelope; ties use the lower spot.
The span, band and overlap area are recorded in ctx["fallbacks"]. NoRoom is
reserved for an impossible band height, not a tight shot.
An active move uses its whole 0..1 progress grid, conservatively even when a
caption covers only part of it. Overlapping properties use a Cartesian product;
the non-overshooting eases need no linear-time approximation or value_at call.

Run: python -X utf8 -I placer.py --selftest
"""
import argparse
import json
import math
import re
import statistics
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compose  # noqa: E402  (reuse the renderer's layout, hook and reserve rules)
import styles  # noqa: E402  (reuse anchor validation and the default origin)

WIDTH, HEIGHT = compose.TIERS["master"]
HEAD_WIDTH = 0.22       # taste: fixed head/neck width when only a centre was measured
HEAD_HEIGHT = 0.20      # taste: fixed head/neck height when only a centre was measured
HEAD_PAD = 24          # taste: margin around the measured head, before the zoom
CAPTION_PAD = 8        # taste: additional screen-pixel clearance around a caption
UNDER_HEAD_GAP = 40    # taste: space below the protected head for the second candidate
LOW_Y = HEIGHT * 0.72  # taste: the port's preferred low caption position
PROGRESS = tuple(i / 10 for i in range(11))
SAFE = (round(compose.RESERVE["left"] * WIDTH), round(compose.RESERVE["top"] * HEIGHT),
        round((1 - compose.RESERVE["right"]) * WIDTH), round((1 - compose.RESERVE["bottom"]) * HEIGHT))


class NoRoom(Exception):
    """Plain lines the caller can show without a traceback."""

    def __init__(self, lines):
        self.lines = (lines,) if isinstance(lines, str) else tuple(lines)
        super().__init__("\n".join(self.lines))


def hits(a, b, pad=0):
    """Adapted: both rectangles now use corners, not the port's mixed formats.

    Touching edges are clear; pad expands the protected rectangle on every side.
    """
    return not (a[2] + pad <= b[0] or a[0] >= b[2] + pad
                or a[3] + pad <= b[1] or a[1] >= b[3] + pad)


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(f"Cannot read {path.name}; make it again before placing captions.") from None


def _union(boxes):
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _sample_box(point):
    box = point.get("box")
    if box is None:
        x, y = point["x"], point["y"]
        box = (x - HEAD_WIDTH / 2, y - HEAD_HEIGHT / 2,
               x + HEAD_WIDTH / 2, y + HEAD_HEIGHT / 2)
    elif not (isinstance(box, (list, tuple)) and len(box) == 4
              and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                      and math.isfinite(v) and 0 <= v <= 1 for v in box)
              and box[0] < box[2] and box[1] < box[3]):
        raise ValueError("A head sample box needs four ordered corners between 0 and 1; run the face step again.")
    return (box[0] * WIDTH - HEAD_PAD, box[1] * HEIGHT - HEAD_PAD,
            box[2] * WIDTH + HEAD_PAD, box[3] * HEIGHT + HEAD_PAD)


def _plate(markup):
    """The actual filled plate, rather than the transparent full-frame card root."""
    match = re.search(r'class="layout-plate"[^>]*\bstyle="([^"]+)"', markup)
    if match is None:
        raise ValueError("A layout card has no plate box; check its layout before checking captions.")
    fields = dict(re.findall(r'(left|top|width|height):\s*([\d.]+)px', match[1]))
    if len(fields) != 4:
        raise ValueError("A layout plate needs a position and size before checking captions.")
    x, y, w, h = (float(fields[k]) for k in ("left", "top", "width", "height"))
    return x, y, x + w, y + h


def load_ctx(reel_dir):
    """Load existing JSON and layout partials only; no probe, render or new work file."""
    reel = Path(reel_dir)
    track = _read(reel / styles.TRACK)
    cuts = _read(reel / "work/cuts.json")
    send = _read(reel / styles.SEND)
    segments = [(s["out_in_f"], s["out_out_f"]) for s in cuts["segments"]]
    if not segments or segments[0][0] != 0 or any(
            not isinstance(a, int) or not isinstance(e, int) or a >= e for a, e in segments
    ) or any(a != previous[1] for previous, (a, _) in zip(segments, segments[1:])):
        raise ValueError("The cut list has missing or overlapping frames; make the cut again.")
    rate = Fraction(str(track["fps"]))
    if rate <= 0 or any(abs(float(rate) - float(doc["fps"])) > 0.001 for doc in (cuts, send)):
        raise ValueError("The style, cut list and Beat Map need the same frame rate; make them again.")
    if track["total_f"] != segments[-1][1] or not track["keys"] or track["keys"][0]["f"] != 0:
        raise ValueError("The style track does not cover this cut; plan its editing style again.")
    # Keep styles.py's sample validation, but retain boxes that its centre-only reader discards.
    try:
        measured = styles.load_anchors(reel, segments)
    except styles.Stop as exc:
        raise ValueError("\n".join(exc.lines)) from None
    anchors = _read(reel / styles.ANCHORS) if measured is not None else {"segments": []}
    boxes, all_boxes = {}, []
    for segment in anchors["segments"]:
        samples = [_sample_box(point) for point in segment["samples"]]
        boxes[segment["seg"]] = _union(samples)
        all_boxes.extend(samples)
    median = tuple(statistics.median(box[i] for box in all_boxes) for i in range(4)) if all_boxes else None
    names = {"full"} | {k["layout"] for k in track["keys"]} | {b["layout"] for b in send["beats"]}
    for move in track["tweens"]:
        if move["prop"] == "layout":
            names.update((move["from"], move["to"]))
    layouts = {name: compose.layout(name, 1) for name in sorted(names)}
    stills = []
    beats = send["beats"]
    first = next((b for b in beats if b["start_f"] == 0), None)
    if first is not None and not any(b["start_f"] == 0 and b.get("scene") is not None for b in beats):
        text = " ".join(first["speech_anchor"]["text"].split())
        if text:
            x, y, w, size = compose.hook_box(WIDTH, HEIGHT)
            # The same conservative three-line envelope as compose.py's hook safe-zone check.
            stills.append((0, min(first["end_f"], round(compose.HOOK_MAX_S * rate)),
                           (x - w / 2, y, x + w / 2, y + size * 1.15 * 3), "hook title"))
    if track["style"].get("style") == "layout-switch":
        stills.extend((b["start_f"], b["end_f"], _plate(layouts[b["layout"]]["plate"]),
                       f"{b['layout']} card plate") for b in beats if b["layout"] != "full")
    return {"track": track, "segments": segments, "beats": beats, "fps": rate,
            "master_size": (WIDTH, HEIGHT), "boxes": boxes, "median_box": median,
            "layouts": {name: tuple(lay["box"]) for name, lay in layouts.items()},
            "stills": stills, "notes": []}


def _lerp(a, b, progress):
    if isinstance(a, (list, tuple)):
        return tuple(x + (y - x) * progress for x, y in zip(a, b))
    return a + (b - a) * progress


def _options(ctx, prop, frame):
    """A hard/settled state, or every progress sample of the active property.

    A whole-state key inside another property's move must not hide that move.
    At the same frame as a key the renderer's fromTo starts after its set.
    """
    track = ctx["track"]
    key = max((k for k in track["keys"] if k["f"] <= frame), key=lambda k: k["f"])
    default = {"scale": 1.0, "origin": styles.ORIGIN, "layout": "full"}[prop]
    value = ((key.get("ox", styles.ORIGIN[0]), key.get("oy", styles.ORIGIN[1]))
             if prop == "origin" else key.get(prop, default))
    move = max((t for t in track["tweens"] if t["prop"] == prop and t["start_f"] <= frame),
               key=lambda t: t["start_f"], default=None)
    values = [value]
    if move is not None and frame < move["end_f"]:
        a, b = move["from"], move["to"]
        if prop == "layout":
            a, b = ctx["layouts"][a], ctx["layouts"][b]
        # Include the hard state as well: whole-state keys can occur during another move.
        values = [_lerp(a, b, p) for p in PROGRESS]
        values.append(ctx["layouts"][value] if prop == "layout" else value)
    else:
        if move is not None and move["end_f"] > key["f"]:
            value = move["to"]
        values = [ctx["layouts"][value] if prop == "layout" else value]
    return values


def _map(box, layout, scale, origin):
    bx, by, bw, bh = layout
    cover = max(bw / WIDTH, bh / HEIGHT)
    dx, dy = (bw - WIDTH * cover) / 2, (bh - HEIGHT * cover) / 2
    ox, oy = origin[0] * bw, origin[1] * bh
    # Cover-fit, then wrapper scale about its origin, then outer-box position and clip.
    x0 = bx + ox + scale * (box[0] * cover + dx - ox)
    y0 = by + oy + scale * (box[1] * cover + dy - oy)
    x1 = bx + ox + scale * (box[2] * cover + dx - ox)
    y1 = by + oy + scale * (box[3] * cover + dy - oy)
    clipped = max(bx, x0), max(by, y0), min(bx + bw, x1), min(by + bh, y1)
    return clipped if clipped[0] < clipped[2] and clipped[1] < clipped[3] else None


def _check_span(ctx, f0, f1):
    if not (isinstance(f0, int) and isinstance(f1, int) and 0 <= f0 <= f1 < ctx["track"]["total_f"]):
        raise ValueError("Caption frames must be ordered whole frames inside this cut.")


def head_box_at(ctx, f0, f1):
    """Union of the protected on-screen head over the inclusive frame span.

    Each segment uses all its samples, or the reel's coordinate-wise median
    sample box. Events split the span into states; every active move contributes
    all eleven progress samples, including layout geometry. Scale/origin/layout
    combinations are independent, deliberately conservative during overlap.
    """
    _check_span(ctx, f0, f1)
    if ctx["median_box"] is None:
        return None
    track = ctx["track"]
    events = {k["f"] for k in track["keys"]}
    events.update(t[k] for t in track["tweens"] for k in ("start_f", "end_f"))
    mapped = []
    for i, (a, e) in enumerate(ctx["segments"]):
        lo, hi = max(f0, a), min(f1, e - 1)
        if lo > hi:
            continue
        box = ctx["boxes"].get(i) or ctx["median_box"]
        for frame in sorted({lo, hi} | {f for f in events if lo <= f <= hi}):
            for scale, origin, layout in product(*(_options(ctx, p, frame) for p in ("scale", "origin", "layout"))):
                mapped.append(_map(box, layout, scale, origin))
    return _union(mapped)


def _seconds(ctx, f0, f1):
    return f"{float(Fraction(f0) / ctx['fps']):.2f} to {float(Fraction(f1) / ctx['fps']):.2f} seconds"


def place(ctx, start_f, end_f, band_h=134):
    """Try low, below-head, top; otherwise use least overlap, then lowest spot."""
    head = head_box_at(ctx, start_f, end_f)
    if not isinstance(band_h, (int, float)) or not math.isfinite(band_h) or band_h <= 0:
        raise ValueError("Caption band height must be a positive number of pixels.")
    x0, top, x1, bottom = SAFE
    last_y = bottom - band_h
    if last_y >= top:
        if ctx["median_box"] is None:
            note = (f"No head samples for {_seconds(ctx, start_f, end_f)}; using the lowest safe caption spot. "
                    "Check it against the speaker before rendering.")
            if note not in ctx["notes"]:
                ctx["notes"].append(note)
            return x0, last_y, x1, bottom
        spots = [min(LOW_Y, last_y)]
        if head is not None:
            spots.append(math.ceil(head[3] + UNDER_HEAD_GAP))
        spots.append(top)
        covered = []
        for y in spots:
            box = x0, y, x1, y + band_h
            if not top <= y <= last_y:
                continue
            if head is None or not hits(box, head, CAPTION_PAD):
                return box
            overlap = (max(0, min(box[2], head[2]) - max(box[0], head[0]))
                       * max(0, min(box[3], head[3]) - max(box[1], head[1])))
            covered.append((overlap, -y, box))
        overlap, _, box = min(covered)
        note = (f"Captions from {_seconds(ctx, start_f, end_f)} overlap part of the speaker's head "
                "because the shot is tight; the caption step may shorten or drop them.")
        if note not in ctx["notes"]:
            ctx["notes"].append(note)
        fallback = dict(start_f=start_f, end_f=end_f, box=box, overlap_px=overlap)
        if fallback not in ctx.setdefault("fallbacks", []):
            ctx["fallbacks"].append(fallback)
        return box
    raise NoRoom(f"Captions from {_seconds(ctx, start_f, end_f)} are too tall for the safe text area.")


def ghosts(ctx, bands):
    """Plain advisory lines for temporally overlapping hook/plate rectangles.

    Scene boxes do not exist yet and are intentionally not inferred.
    """
    notes = []
    for band in bands:
        start, end = band["start_f"], band["end_f"]
        for a, e, box, label in ctx["stills"]:
            if start < e and end >= a and hits(band["box"], box):
                line = f"Captions from {_seconds(ctx, start, end)} overlap the still {label}; check that both remain readable."
                if line not in notes:
                    notes.append(line)
    return notes


def selftest():
    assert hits((10, 10, 20, 20), (15, 15, 30, 30))
    assert not hits((0, 0, 10, 10), (10, 0, 20, 10))
    assert hits((0, 0, 10, 10), (10, 0, 20, 10), 1)
    assert all(math.isclose(a, b) for a, b in zip(
        _map((400, 800, 600, 1000), (0, 960, 1080, 960), 1, styles.ORIGIN), (400, 1280, 600, 1480)))
    assert _map((0, 0, 1080, 1920), (738, 28, 312, 555), 1.43, styles.ORIGIN) == (738, 28, 1050, 583)
    assert _map((0, 0, 100, 100), (0, 0, 1080, 1920), 3, (1, 1)) is None
    print("selftest ok")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Check face-safe caption geometry without rendering.")
    parser.add_argument("--selftest", action="store_true", help="run a few fast geometry checks")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
