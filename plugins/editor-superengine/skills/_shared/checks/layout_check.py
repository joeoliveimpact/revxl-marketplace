#!/usr/bin/env python3
"""Pre-render layout map: off-screen words, text collisions and face coverage.

Usage: python layout_check.py <reel_dir>     exit 1 on any block, else 0

H-B6: PHASE = "pre"; run(ctx) returns [{check, level, msg, where, at}], writes
nothing, and accepts {reel_dir, fps, cuts, beats, render}. Saved captions, cuts
and Beat Map inputs are authoritative. No captions.json means no rows.
Blocks: text-off-screen (hook or protruding words >=8 px outside), text-collision
(>30% of the smaller on-screen chunk/hook box), word-covered (>=65% in the protected head),
caption-on-face (any chunk/head overlap without a covered word). Warn:
layout-face-unchecked (placement inputs unavailable, including absent anchors).
Chunk off-screen findings belong to caption_check and are never repeated here.
Contained words are exempt from text-off-screen. A short or malformed chunk
can let a word's line-height box extend outside its chunk; check those words
separately. Collision compares chunk and hook boxes only, never word boxes.

Approximation: captions.layer() uses white-space: nowrap, so there is no line
wrap to reproduce. Use its padding, font-size formula, centred text advances
from captions.text_width_em(), and one line-height rectangle per word at the
settled position. These are advance/line boxes, not glyph outlines; browser
kerning, shadows, strokes and animated pop/punch transforms are not measured.
Canonical chunk corners are 1080x1920 master pixels. Optional document `width`
declares stored coordinates at another proportional scale; normalize corners
before fitting text. Font sizes remain master sizes, as in captions.layer().
The saved rendered hooks use placer's shared still envelopes and lifetimes,
including CLI text and plain scene replacements. While a hook is active, the
protected caption region is the eyes-to-mouth band; otherwise it is the head.
Collision comparisons exclude a caption's own chunk/words and produce only
one row per pair of text elements, even if several word boxes also collide.
"""
import json
import sys
from fractions import Fraction
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve()
SKILLS = HERE.parents[2]
sys.path.insert(0, str(SKILLS / "_shared"))
sys.path.insert(0, str(SKILLS / "reel-captions/scripts"))
sys.path.insert(0, str(SKILLS / "reel-canvas-build/scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
import captions  # noqa: E402
import placer  # noqa: E402
import compose  # noqa: E402

PHASE = "pre"
WIDTH, HEIGHT = 1080, 1920
INPUT_ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError,
                AttributeError, ZeroDivisionError, OverflowError)


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _row(check, msg, where, frame, rate, level="block"):
    return dict(check=check, level=level, msg=msg, where=where,
                at=round(float(Fraction(frame) / rate), 2))


def _area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def _intersection(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]),
            min(a[2], b[2]), min(a[3], b[3]))


def _word_boxes(chunk, box, spec):
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        raise ValueError("A caption needs a positive-size box; place it again.")
    pad = min(16, (x1 - x0) / 8)
    size = min(spec["size"], (x1 - x0 - 2 * pad)
               / (captions.text_width_em(chunk["text"]) * spec["punch"]["scale"]))
    x = (x0 + x1) / 2 - captions.text_width_em(chunk["text"]) * size / 2
    top, height = y0 + pad, size * spec["line_h"]
    result = []
    for word in chunk["words"]:
        width = captions.text_width_em(word["text"]) * size
        result.append((word["text"], (x, top, x + width, top + height)))
        x += width + captions.text_width_em(" ") * size
    return result


def _hook(reel, rate):
    saved = compose.saved_hooks(reel)
    if saved is not None:
        return next((h for h in saved if h["start_f"] == 0), None)
    path = reel / "beat-map-selection.json"
    if not path.is_file():
        return None
    beats = _read(path).get("beats", [])
    first = next((b for b in beats if b["start_f"] == 0), None)
    if first is None or any(b["start_f"] == 0 and b.get("scene") is not None for b in beats):
        return None
    if not " ".join(first["speech_anchor"]["text"].split()):
        return None
    word_path = reel / "work/edit_map.cut.json"
    words = _read(word_path)["words"] if word_path.is_file() else []
    return compose.plain_hook(first["speech_anchor"]["text"], first, rate, words, first["end_f"])


def run(ctx):
    reel = Path(ctx["reel_dir"])
    path = reel / "work/captions.json"
    if not path.is_file():
        return []
    doc = _read(path)
    cuts = ctx.get("cuts") or _read(reel / "work/cuts.json")
    rate = Fraction(str(cuts["fps"]))
    if rate <= 0:
        raise ValueError("The cut needs a positive frame rate; make the cut again.")
    scale = WIDTH / float(doc.get("width", WIDTH))
    if scale <= 0:
        raise ValueError("The caption coordinate width must be positive; place the captions again.")
    elements, rows = [], []
    if doc["style"]["style"] != "none":
        spec = captions.STYLES[doc["style"]["style"]]
        for i, chunk in enumerate(doc["chunks"]):
            if "box" not in chunk:
                continue  # A plan has no geometry until compose places it.
            box = tuple(v * scale for v in chunk["box"])
            elements.append(dict(where=f"caption {i}", start=chunk["start_f"], end=chunk["end_f"],
                                 box=box, words=_word_boxes(chunk, box, spec)))
    hooks = compose.saved_hooks(reel, doc.get("hooks"))
    if hooks is None:  # older caption documents did not record the rendered hook
        fallback = _hook(reel, rate)
        hooks = [fallback] if fallback else []
    hook = None
    for i, saved in enumerate(hooks):
        a, e, box, _ = placer.hook_still(saved["text"], saved["start_f"], saved["end_f"], saved.get("box"))
        hook = dict(where="hook" if i == 0 else f"hook {i}", start=a, end=e, box=box, words=[], hook=True)
        elements.append(hook)

    try:
        face_ctx = placer.load_ctx(reel)
        placer.set_hook_stills(face_ctx, hooks)
        if face_ctx["median_box"] is None:
            face_ctx = None
    except INPUT_ERRORS:
        face_ctx = None
    face_unchecked = face_ctx is None
    for element in elements:
        where, start = element["where"], element["start"]
        is_hook = element.get("hook", False)
        boxes = [("hook title", element["box"])] if is_hook else element["words"]
        for text, box in boxes:
            if not is_hook:
                chunk_box = element["box"]
                if (box[0] >= chunk_box[0] - 1e-9 and box[1] >= chunk_box[1] - 1e-9
                        and box[2] <= chunk_box[2] + 1e-9 and box[3] <= chunk_box[3] + 1e-9):
                    continue  # caption_check already owns off-frame chunks.
            outside = max(0, -box[0], -box[1], box[2] - WIDTH, box[3] - HEIGHT)
            if outside >= 8 - 1e-9:
                rows.append(_row("text-off-screen",
                                 f"The text '{text}' sits {outside:g} px off the video; move it inside the frame.",
                                 where, start, rate))
        if is_hook or face_ctx is None:
            continue
        try:
            head = placer.head_box_at(face_ctx, start, element["end"] - 1)
            head = placer.caption_protection(face_ctx, start, head)
        except INPUT_ERRORS:
            face_ctx, face_unchecked = None, True
            continue
        if head is None:
            continue  # The measured head is outside the picture during this span.
        hook_face = ("sits on the speaker's face because the hook title leaves no room; "
                     "shorten the hook to one line, or use your opening words as the hook."
                     if placer.active_hook(face_ctx, start) else None)
        covered = False
        for text, box in element["words"]:
            if _area(box) > 0 and _area(_intersection(box, head)) >= 0.65 * _area(box) - 1e-9:
                covered = True
                when = f"{float(Fraction(start) / rate):.2f} s"
                rows.append(_row("word-covered",
                                 f"The word '{text}' at {when} " + (hook_face or
                                 "sits on the speaker's face; move the caption or ask Claude to re-place it."),
                                 where, start, rate))
        if not covered and _area(_intersection(element["box"], head)) > 0:
            rows.append(_row("caption-on-face",
                             "The caption " + hook_face if hook_face else
                             "The caption touches the speaker's face; move it or ask Claude to re-place it.",
                             where, start, rate))

    screen = (0, 0, WIDTH, HEIGHT)
    for a, b in combinations(elements, 2):
        start = max(a["start"], b["start"])
        if start >= min(a["end"], b["end"]):
            continue
        box_a, box_b = _intersection(a["box"], screen), _intersection(b["box"], screen)
        smaller = min(_area(box_a), _area(box_b))
        if smaller > 0 and _area(_intersection(box_a, box_b)) > 0.3 * smaller + 1e-9:
            rows.append(_row("text-collision",
                             f"The text in {a['where']} and {b['where']} overlaps too much; move one so both are clear.",
                             a["where"], start, rate))
    if face_unchecked:
        first = next((e for e in elements if not e.get("hook")), hook)
        rows.append(_row("layout-face-unchecked",
                         "The speaker's face could not be checked; run the face and placement steps again before reviewing captions.",
                         first["where"] if first else "hook", first["start"] if first else 0, rate, "warn"))
    return rows


def main():
    ensure_utf8_output()
    if len(sys.argv) != 2:
        raise SystemExit("usage: layout_check.py <reel_dir>")
    rows = run({"reel_dir": sys.argv[1]})
    for row in rows:
        print(f"{row['level'].upper()}  {row['check']}  {row['msg']}  ({row['where']}, {row['at']:.2f} s)")
    blocks = sum(row["level"] == "block" for row in rows)
    print(f"layout check: {blocks} block(s)")
    return 1 if blocks else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("The layout check could not finish: " + str(exc).splitlines()[0], file=sys.stderr)
        sys.exit(1)
