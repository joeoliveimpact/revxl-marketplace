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
place() prefers a text-safe candidate clear of the head. During the hook window,
active stills are hard obstacles; otherwise they remain advisory via ghosts().
If none clears both, it keeps stills clear first, then minimizes head overlap.
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
import fps as fpsmod  # noqa: E402
import styles  # noqa: E402  (reuse anchor validation and the default origin)
import broll_bands  # noqa: E402  (read cached measurements only)

WIDTH, HEIGHT = compose.TIERS["master"]
HEAD_WIDTH = 0.22       # taste: fixed head/neck width when only a centre was measured
HEAD_HEIGHT = 0.20      # taste: fixed head/neck height when only a centre was measured
HEAD_PAD = 24          # taste: margin around the measured head, before the zoom
CAPTION_PAD = 8        # taste: additional screen-pixel clearance around a caption
UNDER_HEAD_GAP = 40    # taste: space below the protected head for the second candidate
FACE_BAND_BOTTOM = .75  # eyes through mouth; captions may share the hair above 15%
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


def hook_still(text, start_f, end_f, box=None):
    if box is not None:
        return start_f, end_f, tuple(box), "hook title"
    x, y, w, size = compose.hook_box(WIDTH, HEIGHT)
    lines = compose.title_lines(text, w, size)
    return (start_f, end_f, (x - w / 2, y, x + w / 2, y + size * 1.15 * lines), "hook title")


def set_hook_stills(ctx, hooks):
    """Install the exact rendered hook times/text, including a scene replacement."""
    ctx["hooks"] = hooks
    ctx["stills"] = [s for s in ctx["stills"] if s[3] not in ("hook title", "highlighted sentence")] + [
        (h["start_f"], h["end_f"], tuple(h["box"]), h["label"]) if h.get("label") == "highlighted sentence"
        else hook_still(h["text"], h["start_f"], h["end_f"], h.get("box")) for h in hooks]


def active_hook(ctx, start_f):
    return next((s for s in ctx["stills"] if s[3] == "hook title" and s[0] <= start_f < s[1]), None)


def face_band(head, top=.15):
    if head is None:
        return None
    height = head[3] - head[1]
    return head[0], head[1] + top * height, head[2], head[1] + FACE_BAND_BOTTOM * height


def caption_protection(ctx, start_f, head):
    """QA and placement share the hair allowance during the rendered hook."""
    return face_band(head) if active_hook(ctx, start_f) else head


def caption_cause(ctx, start_f, end_f):
    """An absent optional scene manifest leaves its overlay setting unknown."""
    hook = active_hook(ctx, start_f)
    saved = next((h for h in ctx.get("hooks", [])
                  if hook is not None and h["start_f"] == hook[0] and h["end_f"] == hook[1]), {})
    unknown = False
    for beat in ctx.get("beats", []):
        scene = beat.get("scene")
        if scene and beat["start_f"] <= end_f and start_f < beat["end_f"]:
            if (scene["id"] == "hf-hook-title" and saved.get("kind") == "plain"
                    and beat["start_f"] == hook[0]):
                continue  # The saved render replaced this scene with a plain hook.
            path = compose.scene_check.SCENES / scene["id"] / "scene.json"
            try:
                spec = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                unknown = True
                continue
            if spec.get("kind") == "overlay":
                return "overlay"
    if hook is not None:
        if saved.get("kind") == "scene":
            return "overlay"
        if not unknown:
            return "plain-hook"
    return "unknown"


def one_line_hook_clears(ctx, spans):
    """Re-place every inclusive (start, end, height) span with a one-line plain hook.

    Only canonical multi-line plain hooks can be shortened this way. The trial
    owns its notes/fallbacks and retains every other still and placement input.
    """
    if not spans or ctx["median_box"] is None:
        return False
    _, _, width, size = compose.hook_box(WIDTH, HEIGHT)
    one_line = hook_still("", 0, 1)[2]
    trial = dict(ctx, stills=list(ctx["stills"]), notes=[], fallbacks=[])
    for start, end, height in spans:
        hook = active_hook(ctx, start)
        if hook is None or caption_cause(ctx, start, end) != "plain-hook":
            return False
        saved = next((h for h in ctx.get("hooks", [])
                      if h["start_f"] == hook[0] and h["end_f"] == hook[1]), None)
        if saved is None or compose.title_lines(saved["text"], width, size) <= 1:
            return False
        canonical = hook_still(saved["text"], hook[0], hook[1])[2]
        if (not all(math.isclose(a, b) for a, b in zip(hook[2], canonical))
                or hook[2][3] <= one_line[3]):
            return False
        trial["stills"][ctx["stills"].index(hook)] = (hook[0], hook[1], one_line, hook[3])
    for start, end, height in spans:
        box = place(trial, start, end, height)
        head = caption_protection(trial, start, head_box_at(trial, start, end))
        if head is not None and hits(box, head):
            return False
        if any(start < e and end >= a and hits(box, still)
               for a, e, still, _ in trial["stills"]):
            return False
    return True


def load_ctx(reel_dir, hook=None):
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
    rate = fpsmod.as_fraction(track["fps"])
    if rate <= 0 or any(abs(float(rate) - float(fpsmod.as_fraction(doc["fps"]))) > 0.001 for doc in (cuts, send)):
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
    stills, hooks = [], []
    beats = send["beats"]
    first = next((b for b in beats if b["start_f"] == 0), None)
    if (first is not None or hook is not None) and not any(
            b["start_f"] == 0 and b.get("scene") is not None for b in beats):
        text, hook_f = hook if hook is not None else (
            first["speech_anchor"]["text"], min(first["end_f"], round(compose.HOOK_MAX_S * rate)))
        text = " ".join(text.split())
        if text:
            stills.append(hook_still(text, 0, hook_f))
            hooks.append(dict(text=text, start_f=0, end_f=hook_f))
    if track["style"].get("style") == "layout-switch":
        stills.extend((b["start_f"], b["end_f"], _plate(layouts[b["layout"]]["plate"]),
                       f"{b['layout']} card plate") for b in beats if b["layout"] != "full")
    return {"track": track, "segments": segments, "beats": beats, "fps": rate,
            "master_size": (WIDTH, HEIGHT), "boxes": boxes, "median_box": median,
            "layouts": {name: tuple(lay["box"]) for name, lay in layouts.items()},
            "stills": stills, "hooks": hooks, "notes": [], "broll_bands": broll_bands.read_cache(reel)}


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


def speaker_spans(ctx, start_f, end_f):
    """Inclusive spans with visible a-roll, using the compositor's coverage.

    B-roll (cover or blur-fill), takeovers and opaque underlays hide a-roll
    below them. Foreground PIP stays visible, including moves to/from PIP.
    Split and other layouts retain head_box_at's mapping when not covered.
    Unknown coverage leaves the face rule active for the whole span.
    """
    _check_span(ctx, start_f, end_f)
    try:
        covers = compose.picture_covers(ctx.get("beats") or [], ctx.get("fps") or ctx.get("rate"), opaque_only=True)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return [(start_f, end_f)]
    track = ctx["track"]
    edges = {start_f, end_f + 1}
    edges.update(f for start, end, _ in covers for f in (start, end) if start_f < f <= end_f)
    edges.update(k["f"] for k in track["keys"] if start_f < k["f"] <= end_f)
    edges.update(t[k] for t in track["tweens"] if t["prop"] == "layout"
                 for k in ("start_f", "end_f") if start_f < t[k] <= end_f)
    pip = ctx["layouts"].get("pip")
    spans = []
    ordered = sorted(edges)
    for start, end in zip(ordered, ordered[1:]):
        covered = any(a <= start < e for a, e, _ in covers)
        if not covered or (pip is not None and pip in _options(ctx, "layout", start)):
            spans.append((start, end - 1))
    return spans


def visible_head_box_at(ctx, start_f, end_f):
    """The existing mapped head envelope, restricted to visible a-roll frames."""
    return _union(head_box_at(ctx, a, e) for a, e in speaker_spans(ctx, start_f, end_f))


def speaker_hidden(ctx, start_f, end_f):
    """True when full-frame B-roll covers most of the inclusive span, so the speaker's face is not on screen."""
    covered = 0
    for beat in ctx.get("beats", []):
        clip = beat.get("broll")
        if clip and beat.get("layout") == "full" and clip.get("fit") == "cover":
            covered += max(0, min(end_f + 1, beat["end_f"]) - max(start_f, beat["start_f"]))
    return covered * 2 > end_f - start_f + 1


def _broll_profiles(ctx, start_f, end_f):
    profiles = []
    duration = 0
    cache = ctx.get("broll_bands", {})
    for beat in ctx.get("beats", []):
        clip = beat.get("broll")
        overlap = min(end_f + 1, beat["end_f"]) - max(start_f, beat["start_f"])
        if overlap <= 0 or not clip or beat["layout"] != "full" or clip["fit"] != "cover":
            continue
        entry = cache.get(broll_bands.beat_key(beat))
        if entry is None:
            continue
        duration += overlap
        profiles.append(entry["rows"])
    return profiles if duration * 2 > end_f - start_f + 1 else []


def _detail_score(rows, y, band_h):
    lo = max(0, math.floor((y - CAPTION_PAD) / broll_bands.ROW_PX))
    hi = min(len(rows), math.ceil((y + band_h + CAPTION_PAD) / broll_bands.ROW_PX))
    return sum(rows[lo:hi]) / (hi - lo)


def _broll_place(ctx, start_f, end_f, band_h, stills):
    profiles = _broll_profiles(ctx, start_f, end_f)
    if not profiles:
        return None
    x0, top, x1, bottom = SAFE
    last_y = bottom - band_h
    preferred = min(LOW_Y, last_y)
    # Include every whole-pixel spot the old placer could choose, so a coarse
    # grid cannot miss a plainer band than the old placement.
    candidates = set(range(top, math.floor(last_y) + 1)) | {last_y, preferred}
    clear = []
    for y in candidates:
        box = x0, y, x1, y + band_h
        if all(not hits(box, still, CAPTION_PAD) for still in stills):
            score = max(_detail_score(rows, y, band_h) for rows in profiles)
            clear.append((score, abs(y - preferred), -y, box))
    return min(clear)[-1] if clear else None


def place(ctx, start_f, end_f, band_h=134):
    """Keep base placement outside hooks; inside, clear active stills first."""
    head = head_box_at(ctx, start_f, end_f)
    hook = active_hook(ctx, start_f)
    stills = [box for a, e, box, label in ctx["stills"]
              if (hook is not None or label == "highlighted sentence") and start_f < e and end_f >= a]
    if not isinstance(band_h, (int, float)) or not math.isfinite(band_h) or band_h <= 0:
        raise ValueError("Caption band height must be a positive number of pixels.")
    x0, top, x1, bottom = SAFE
    last_y = bottom - band_h
    if last_y >= top:
        broll_box = _broll_place(ctx, start_f, end_f, band_h, stills)
        if broll_box is not None:
            return broll_box
        if ctx["median_box"] is None:
            note = (f"No head samples for {_seconds(ctx, start_f, end_f)}; placing captions at the lowest safe spot where possible. "
                    "Check it against the speaker before rendering.")
            if note not in ctx["notes"]:
                ctx["notes"].append(note)
            low = x0, last_y, x1, bottom
            if all(not hits(low, still, CAPTION_PAD) for still in stills):
                return low
        if hook is not None:
            y = math.ceil(hook[2][3] + UNDER_HEAD_GAP)
            box = x0, y, x1, y + band_h
            protected = caption_protection(ctx, start_f, head)
            if (top <= y <= last_y and (protected is None or not hits(box, protected, CAPTION_PAD))
                    and all(not hits(box, still, CAPTION_PAD) for still in stills)):
                return box
        spots = [last_y if ctx["median_box"] is None else min(LOW_Y, last_y)]
        if head is not None:
            spots.append(math.ceil(head[3] + UNDER_HEAD_GAP))
        spots.extend(math.ceil(box[3] + UNDER_HEAD_GAP) for box in stills)
        spots.append(top)
        covered, clear_stills = [], []
        for y in spots:
            box = x0, y, x1, y + band_h
            if not top <= y <= last_y:
                continue
            still_clear = all(not hits(box, still, CAPTION_PAD) for still in stills)
            if still_clear and (head is None or not hits(box, head, CAPTION_PAD)):
                return box
            overlap = (0 if head is None else
                       max(0, min(box[2], head[2]) - max(box[0], head[0]))
                       * max(0, min(box[3], head[3]) - max(box[1], head[1])))
            covered.append((overlap, -y, box))
            if still_clear:
                clear_stills.append((overlap, -y, box))
        overlap, _, box = min(clear_stills or covered)
        if not clear_stills:
            note = (f"Captions from {_seconds(ctx, start_f, end_f)} overlap the hook title; "
                    + compose.caption_advice(caption_cause(ctx, start_f, end_f)))
            if note not in ctx["notes"]:
                ctx["notes"].append(note)
        if head is not None and hits(box, head, CAPTION_PAD):
            note = (f"Captions from {_seconds(ctx, start_f, end_f)} overlap part of the speaker's head "
                    "because the shot is tight; the caption step may shorten or drop them.")
            if note not in ctx["notes"]:
                ctx["notes"].append(note)
            if hook is not None and hits(box, face_band(head), CAPTION_PAD):
                reason = "can't fit between your hook title and your face on this shot. "
                cause = caption_cause(ctx, start_f, end_f)
                spans = [(start_f, end_f, band_h)]
                for previous in ctx.get("fallbacks", []):
                    a, e = previous["start_f"], previous["end_f"]
                    protected = caption_protection(ctx, a, head_box_at(ctx, a, e))
                    if (caption_cause(ctx, a, e) == "plain-hook" and protected is not None
                            and hits(previous["box"], protected)):
                        spans.append((a, e, previous["box"][3] - previous["box"][1]))
                clears = one_line_hook_clears(ctx, spans) if cause == "plain-hook" else False
                advice = compose.caption_advice(cause, one_line_clears=clears)
                prior = next((i for i, n in enumerate(ctx["notes"]) if reason in n), None)
                if prior is None:
                    ctx["notes"].append(f"Captions from {_seconds(ctx, start_f, end_f)} {reason}" + advice)
                else:
                    ctx["notes"][prior] = ctx["notes"][prior].split(reason)[0] + reason + advice
        fallback = dict(start_f=start_f, end_f=end_f, box=box, overlap_px=overlap)
        if fallback not in ctx.setdefault("fallbacks", []):
            ctx["fallbacks"].append(fallback)
        return box
    raise NoRoom(f"Captions from {_seconds(ctx, start_f, end_f)} are too tall for the safe text area.")


def ghosts(ctx, bands):
    """Plain advisory lines for temporally overlapping hook/plate rectangles.

    Fitted hook scenes use their supplied text boxes, never inferred geometry.
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
    from unittest.mock import patch
    assert hits((10, 10, 20, 20), (15, 15, 30, 30))
    assert not hits((0, 0, 10, 10), (10, 0, 20, 10))
    assert hits((0, 0, 10, 10), (10, 0, 20, 10), 1)
    assert all(math.isclose(a, b) for a, b in zip(
        _map((400, 800, 600, 1000), (0, 960, 1080, 960), 1, styles.ORIGIN), (400, 1280, 600, 1480)))
    assert _map((0, 0, 1080, 1920), (738, 28, 312, 555), 1.43, styles.ORIGIN) == (738, 28, 1050, 583)
    assert _map((0, 0, 100, 100), (0, 0, 1080, 1920), 3, (1, 1)) is None
    assert compose.title_lines("Watch this before you post", 840, 72) == 2
    assert math.isclose(hook_still("Watch this before you post", 0, 125)[2][3], 445.6)
    # Ignoring an active still would pick the top spot, over the hook.
    head = (200, 850, 880, 1500)
    ctx = {"track": {"total_f": 100, "keys": [{"f": 0}], "tweens": []},
           "segments": [(0, 100)], "boxes": {0: head}, "median_box": head,
           "layouts": {"full": (0, 0, 1080, 1920)}, "fps": Fraction(25),
           "stills": [(0, 50, (90, 280, 930, 570), "hook title")], "notes": []}
    covered_beat = dict(id="cover", start_f=0, end_f=100, layout="full", broll={"fit": "cover"})
    visible_ctx = dict(ctx, beats=[covered_beat], layouts=dict(ctx["layouts"],
                       pip=(738, 28, 312, 555), split=(0, 960, 1080, 960)))
    for fit in ("cover", "blur-fill"):
        covered_beat["broll"]["fit"] = fit
        assert speaker_spans(visible_ctx, 0, 99) == []
        assert visible_head_box_at(visible_ctx, 0, 99) is None
    visible_ctx["track"] = dict(ctx["track"], keys=[dict(f=0, layout="full"),
                                dict(f=40, layout="pip"), dict(f=60, layout="full")])
    assert speaker_spans(visible_ctx, 0, 99) == [(40, 59)]
    pip_head = visible_head_box_at(visible_ctx, 0, 99)
    assert 738 <= pip_head[0] < pip_head[2] <= 1050 and 28 <= pip_head[1] < pip_head[3] <= 583
    visible_ctx["track"] = dict(ctx["track"], tweens=[dict(prop="layout", start_f=20, end_f=40,
                                **{"from": "full", "to": "pip"})])
    assert speaker_spans(visible_ctx, 0, 99) == [(20, 39), (40, 99)]
    visible_ctx["track"] = dict(ctx["track"], keys=[dict(f=0, layout="split")])
    assert visible_head_box_at(visible_ctx, 0, 99) is None  # B-roll is above a split box too.
    visible_ctx["beats"] = []
    assert visible_head_box_at(visible_ctx, 0, 99) == (200, 1330, 880, 1920)
    visible_ctx["beats"] = [dict(id="takeover", start_f=0, end_f=100, layout="full",
                                 scene={"id": "cta-end-card"})]
    assert visible_head_box_at(visible_ctx, 0, 99) is None
    for rate in (Fraction(25), Fraction(30), Fraction(30000, 1001)):
        assert visible_head_box_at(dict(visible_ctx, fps=rate), 0, 99) is None
    for rate_key in ("fps", "rate"):
        trial = dict(visible_ctx)
        trial.pop("fps")
        trial[rate_key] = Fraction(30)
        assert visible_head_box_at(trial, 0, 99) is None
    for missing_rate in ({"fps": None}, {}):
        trial = dict(visible_ctx)
        trial.pop("fps")
        trial.update(missing_rate)
        assert speaker_spans(trial, 0, 99) == [(0, 99)]
        assert visible_head_box_at(trial, 0, 99) == head_box_at(trial, 0, 99)
    trial = dict(visible_ctx, beats=[dict(visible_ctx["beats"][0], scene={"id": "unavailable-card"})])
    assert visible_head_box_at(trial, 0, 99) == head_box_at(trial, 0, 99)
    box = place(ctx, 0, 49)
    assert box == (60, 610, 960, 744), box
    assert not hits(box, head, CAPTION_PAD) and not hits(box, ctx["stills"][0][2])
    assert not any("can't fit between your hook title" in n for n in ctx["notes"])
    assert place(ctx, 50, 60) == (60, 220, 960, 354)
    assert place(ctx, 49, 50) == box  # an inclusive span crossing the hook end
    # A tight head may force overlap, but a clear still remains a hard obstacle.
    ctx["boxes"][0] = ctx["median_box"] = (0, 400, 1080, 1920)
    ctx["stills"][0] = (0, 50, (60, 220, 960, 600), "hook title")
    box = place(ctx, 0, 49)
    assert not hits(box, ctx["stills"][0][2]) and ctx["fallbacks"]
    no_room = ("Captions from 0.00 to 1.96 seconds can't fit between your hook title and your face on this shot. "
               + compose.caption_advice("unknown"))
    assert no_room in ctx["notes"], ctx["notes"]
    place(ctx, 10, 20)
    assert sum("can't fit between your hook title" in n for n in ctx["notes"]) == 1
    outside = dict(ctx, boxes={0: (0, 0, 1080, 1920)}, median_box=(0, 0, 1080, 1920), notes=[])
    place(outside, 50, 60)
    assert any("because the shot is tight" in n for n in outside["notes"])
    assert not any("can't fit between your hook title" in n for n in outside["notes"])
    ctx["stills"][0] = (0, 50, (0, 0, 1080, 1920), "hook title")
    place(ctx, 0, 49)
    assert ("Captions from 0.00 to 1.96 seconds overlap the hook title; "
            + compose.caption_advice("unknown")) in ctx["notes"]
    ctx["median_box"] = None
    ctx["stills"][0] = (0, 50, (90, 280, 930, 570), "hook title")
    assert place(ctx, 0, 49) == (60, 1336, 960, 1470)
    ctx["stills"].append((0, 50, (60, 1300, 960, 1470), "card plate"))
    assert place(ctx, 0, 49) == (60, 610, 960, 744)
    # With no hook, plates remain advisory and cannot change base geometry.
    ctx["stills"] = [(0, 50, (60, 1300, 960, 1470), "card plate")]
    plated = place(ctx, 0, 49)
    ctx["stills"] = []
    assert plated == place(ctx, 0, 49) == (60, 1336, 960, 1470)
    assert ghosts(dict(ctx, stills=[(0, 50, plated, "card plate")]), [
        dict(start_f=0, end_f=49, box=plated)])
    ctx.update(boxes={0: head}, median_box=head)
    base = place(ctx, 0, 49)
    ctx["stills"] = [(0, 50, base, "card plate")]
    assert place(ctx, 0, 49) == base
    # Full-frame B-roll hides the head; choose detail bands, still clearing the hook.
    clip_beat = dict(start_f=0, end_f=100, layout="full",
                     broll=dict(src="clip.mp4", **{"in": 0, "out": 100}, fit="cover"))
    profile = {"rows": [10] * 65 + [0] * 55}
    bctx = dict(ctx, beats=[clip_beat], stills=[], notes=[],
                broll_bands={broll_bands.beat_key(clip_beat): profile})
    assert place(bctx, 0, 49) == (60, 1336, 960, 1470)
    profile["rows"] = [10] * 40 + [0] * 25 + [10] * 55
    middle = place(bctx, 0, 49)
    assert 648 <= middle[1] and middle[3] <= 1032
    profile["rows"] = [10] * 120
    profile["rows"][15:36] = [0] * 21
    profile["rows"][55:75] = [1] * 20
    bctx["stills"] = [(0, 50, (60, 220, 960, 600), "hook title")]
    blocked = place(bctx, 0, 49)
    assert 888 <= blocked[1] and blocked[3] <= 1192
    clip_beat["end_f"] = 25
    assert place(bctx, 25, 49) == place(dict(bctx, broll_bands={}), 25, 49)
    first = {"start_f": 0, "end_f": 300, "layout": "full", "speech_anchor": {"text": "First beat"}}
    docs = {Path(styles.TRACK).name: {"fps": "25/1", "total_f": 300, "style": {},
                                    "keys": [{"f": 0, "layout": "full"}], "tweens": []},
            "cuts.json": {"fps": "25/1", "segments": [{"out_in_f": 0, "out_out_f": 300}]},
            Path(styles.SEND).name: {"fps": "25/1", "beats": [first]}}
    with patch(__name__ + "._read", side_effect=lambda path: docs[path.name]), \
            patch.object(styles, "load_anchors", return_value=None):
        short = load_ctx("unused", hook=("Hi", 25))["stills"][0]
        long = load_ctx("unused", hook=("W" * 70, 75))["stills"][0]
        fallback = load_ctx("unused")["stills"][0]
        assert short[:2] == (0, 25) and math.isclose(short[2][3], 362.8)
        assert long[:2] == (0, 75) and long[2][3] > short[2][3]
        assert fallback[:2] == (0, 125)
    head = (200, 600, 880, 1900)
    ctx.update(boxes={0: head}, median_box=head, notes=[], stills=[(0, 50, (90, 280, 930, 570), "hook title")])
    hair = place(ctx, 0, 49)
    assert hair == (60, 610, 960, 744) and hits(hair, head)
    assert not hits(hair, face_band(head), CAPTION_PAD)
    assert not any("can't fit between your hook title" in n for n in ctx["notes"])
    assert place(ctx, 49, 60) == hair  # the ruling classifies a chunk by its start
    # At the exclusive hook end the full head is protected again.
    assert place(ctx, 50, 60) == (60, 220, 960, 354)
    ctx["boxes"][0] = ctx["median_box"] = (200, 400, 880, 1500)
    blocked = place(ctx, 0, 49)
    assert blocked != hair and ctx["fallbacks"]  # the under-hook spot crosses the face
    assert not hits(blocked, face_band(ctx["median_box"]), CAPTION_PAD)
    assert not any("can't fit between your hook title" in n for n in ctx["notes"])
    # Exercise QA messages through real caption geometry, including the hook end.
    import tempfile
    sys.path.insert(0, str(HERE.parents[1] / "_shared/checks"))
    import layout_check
    with tempfile.TemporaryDirectory() as home:
        reel = Path(home)
        (reel / "work").mkdir()
        (reel / "work/cuts.json").write_text(json.dumps({"fps": "25/1"}), encoding="utf-8")
        head = (200, 600, 880, 1900)
        ctx.update(boxes={0: head}, median_box=head)
        hook = dict(text="Hi", start_f=0, end_f=50, spoken=False, word_count=1, shown_words=[])
        for start, y, check in ((0, 850, "word-covered"), (49, 850, "word-covered"),
                                 (0, 670, "caption-on-face"), (50, 610, "word-covered"),
                                 (50, 470, "caption-on-face")):
            chunk = dict(start_f=start, end_f=start + 10, text="Hi", box=[60, y, 960, y + 134],
                         words=[dict(text="Hi")])
            doc = {"style": {"style": "clean"}, "chunks": [chunk], "hooks": [hook]}
            (reel / "work/captions.json").write_text(json.dumps(doc), encoding="utf-8")
            with patch.object(layout_check.placer, "load_ctx", return_value=ctx):
                rows = layout_check.run({"reel_dir": reel})
            row = next(r for r in rows if r["check"] == check)
            assert row["level"] == "block", rows
            assert row["advice"] == compose.caption_advice("unknown"), rows
            if check == "word-covered":
                assert row["msg"] == (f"The word 'Hi' at {start / 25:.2f} s sits on your face. "
                                      + compose.caption_advice("unknown")), rows
            else:
                assert row["msg"] == "The caption touches your face. " + compose.caption_advice("unknown"), rows
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
