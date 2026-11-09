#!/usr/bin/env python3
"""Pre-render caption truth check (HF-4).

Usage: python caption_check.py <reel_dir>     exit 1 on any block, 0 otherwise

H-B6: PHASE = "pre"; run(ctx) returns [{check, level: "block"|"warn", msg,
where}], with optional at (seconds). ctx = {reel_dir, fps, cuts, beats, render}.
Only reel_dir is used: captions, cut words, fps and duration come from the saved
work/captions.json, work/edit_map.cut.json and work/cuts.json. Nothing is written.
Missing captions or an empty caption plan declaring every word dropped passes.
Boxes are placer's (left, top, right, bottom) corners in 1080x1920 master pixels.

Blocks: caption-file (unreadable inputs), caption-word (changed speech),
caption-word-lost (undeclared omission), caption-time (over 80 ms plus half a
frame from its anchor), caption-grid (fractional frames), caption-past-end
(chunk past the cut or an empty/reversed span), caption-off-frame (8 px outside).
Warns: caption-word-twice (a word both displayed and declared dropped).
Allowed swaps are bidirectional; a compact token covers its whole transcript run.
"""
import json
import math
import sys
import unicodedata
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "pre"
# Explicit vocabulary only: no general rewriting or numeric guessing.
ALLOWED_SWAPS = (
    ("zero", "0"), ("one", "1"), ("two", "2"), ("three", "3"),
    ("four", "4"), ("five", "5"), ("six", "6"), ("seven", "7"),
    ("eight", "8"), ("nine", "9"), ("ten", "10"), ("eleven", "11"),
    ("twelve", "12"), ("thirteen", "13"), ("fourteen", "14"),
    ("fifteen", "15"), ("sixteen", "16"), ("seventeen", "17"),
    ("eighteen", "18"), ("nineteen", "19"), ("twenty", "20"),
    ("thirty", "30"), ("forty", "40"), ("fifty", "50"),
    ("sixty", "60"), ("seventy", "70"), ("eighty", "80"), ("ninety", "90"),
    ("hundred", "100"), ("thousand", "1000"), ("million", "1000000"),
    ("fifteen percent", "15%"), ("percent", "%"), ("and", "&"),
    ("dollars", "$"), ("okay", "OK"),
)
WIDTH, HEIGHT = 1080, 1920
DRIFT_S = 0.080


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _frame(value):
    return _number(value) and int(value) == value


def _normal(text):
    text = text.strip().casefold()
    # Percent, dollar and ampersand spellings carry meaning, even at an edge.
    def punctuation(char):
        return char not in "%&$" and unicodedata.category(char).startswith("P")
    while text and punctuation(text[0]):
        text = text[1:]
    while text and punctuation(text[-1]):
        text = text[:-1]
    return text.strip()


def _coverage(text, position, words):
    """Return the matched run length at this exact word-list position, else 0."""
    caption = _normal(text)
    if caption == _normal(words[position]["word"]):
        return 1
    for left, right in ALLOWED_SWAPS:
        for source, target in ((left, right), (right, left)):
            if caption != _normal(target):
                continue
            parts = source.split()
            run = words[position:position + len(parts)]
            if len(run) == len(parts) and all(_normal(w["word"]) == _normal(p)
                                             for w, p in zip(run, parts)):
                return len(parts)
    return 0


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _row(check, msg, where, at=None, level="block"):
    # Keep a malformed or multi-line caption token from breaking plain-line output.
    row = dict(check=check, level=level, msg=" ".join(msg.split()), where=where)
    if _number(at):
        row["at"] = round(float(at), 2)
    return row


def _file(msg, where="caption 0"):
    return [_row("caption-file", msg, where)]


def run(ctx):
    work = Path(ctx["reel_dir"]) / "work"
    try:
        doc = _read(work / "captions.json")
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        return _file("The caption file cannot be read. Make the captions again before rendering.")
    if not (isinstance(doc, dict) and isinstance(doc.get("chunks"), list)
            and isinstance(doc.get("declared_drops"), list)):
        return _file("The caption file needs captions and declared drops. Make the captions again.")
    chunks, drops = doc["chunks"], doc["declared_drops"]
    if not all(isinstance(d, dict) and isinstance(d.get("w"), int)
               and not isinstance(d["w"], bool) for d in drops):
        return _file("A declared caption drop has no word position. Make the captions again.")
    dropped = {d["w"] for d in drops}
    try:
        words = _read(work / "edit_map.cut.json")["words"]
        if not (isinstance(words, list) and all(
                isinstance(w, dict) and isinstance(w.get("word"), str)
                and _number(w.get("start")) for w in words)):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        return _file("The cut's spoken words cannot be read. Make the cut word list again before checking captions.")
    if not chunks and all(i in dropped for i in range(len(words))):
        return []
    try:
        cuts = _read(work / "cuts.json")
        fps = float(Fraction(str(cuts["fps"])))
        total = cuts["segments"][-1]["out_out_f"]
        if not math.isfinite(fps) or fps <= 0 or not _frame(total) or total <= 0:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError, IndexError, ZeroDivisionError, OverflowError):
        return _file("The cut's frame rate or length cannot be read. Make the cut again before checking captions.")

    allowance = DRIFT_S + 0.5 / fps
    rows, shown = [], {}
    for index, chunk in enumerate(chunks):
        where = f"caption {index}"
        if not (isinstance(chunk, dict) and isinstance(chunk.get("words"), list)
                and all(isinstance(w, dict) and isinstance(w.get("text"), str) for w in chunk["words"])):
            rows.extend(_file("This caption has no readable word list. Make the captions again.", where))
            continue
        start, end = chunk.get("start_f"), chunk.get("end_f")
        at = start / fps if _number(start) else None

        def hit(check, msg, time=at, level="block"):
            rows.append(_row(check, msg, where, time, level))

        entries = chunk["words"]
        for entry in [chunk, *entries]:
            keys = ("start_f", "end_f") if entry is chunk else (
                ("start_f", "end_f") if "end_f" in entry else ("start_f",))
            if any(not _frame(entry.get(key)) for key in keys):
                hit("caption-grid", "A caption time is between video frames. Snap its times to whole frames before rendering.")
        if _number(start) and _number(end) and (end > total or start >= end):
            hit("caption-past-end", "A caption ends after the video or has no time to appear. Fit its start and end inside the cut.")

        first_start = entries[0].get("start_f") if entries else None
        anchors = [first_start / fps] if _number(first_start) else []
        first_position = entries[0].get("w") if entries else None
        if (isinstance(first_position, int) and not isinstance(first_position, bool)
                and 0 <= first_position < len(words)):
            anchors.append(words[first_position]["start"])
        if _number(start) and any(abs(start / fps - anchor) > allowance + 1e-9 for anchor in anchors):
            hit("caption-time", "A caption starts too far from its first spoken word. Restore its time from the transcript.")
        for entry in entries:
            position, frame = entry.get("w"), entry.get("start_f")
            time = frame / fps if _number(frame) else at
            if _number(frame) and not 0 <= frame < total:
                hit("caption-past-end", "A caption word starts outside the video. Move its start inside the cut.", time)
            if not (isinstance(position, int) and not isinstance(position, bool) and 0 <= position < len(words)):
                hit("caption-word", "A caption word has no matching position in the transcript. Make the captions again.", time)
                continue
            original = words[position]
            length = _coverage(entry["text"], position, words)
            # A changed word is still displayed at this position; report its text,
            # rather than adding a second finding claiming that position is lost.
            for covered in range(position, position + (length or 1)):
                shown.setdefault(covered, (where, time))
            if not length:
                hit("caption-word", f"The caption says '{entry['text']}' but the speaker said '{original['word'].strip()}' "
                    f"at {original['start']:.3f} s. Restore the spoken word.", original["start"])
            if _number(frame) and abs(frame / fps - original["start"]) > allowance + 1e-9:
                hit("caption-time", f"The caption word '{entry['text']}' starts too far from the speech "
                    f"at {original['start']:.3f} s. Restore its time from the transcript.", original["start"])

        if "box" in chunk:
            box = chunk["box"]
            if not (isinstance(box, (list, tuple)) and len(box) == 4 and all(_number(v) for v in box)):
                rows.extend(_file("This caption has no readable position on the video. Place the captions again.", where))
            else:
                # placer.place() already returns master-pixel corners, not x/y/width/height.
                outside = max(0, -box[0], -box[1], box[2] - WIDTH, box[3] - HEIGHT)
                if outside >= 8:
                    when = f"{at:.3f} s" if at is not None else "an unknown time"
                    hit("caption-off-frame", f"A caption at {when} sits {outside:g} px off the edge of the video. Move it inside the frame.")

    for position, word in enumerate(words):
        if position in shown and position in dropped:
            where, at = shown[position]
            rows.append(_row("caption-word-twice", f"The word '{word['word'].strip()}' is both shown and marked dropped. "
                             "Remove the drop or the displayed word.", where, word["start"], "warn"))
        elif position not in shown and position not in dropped:
            # Prefer the original containing chunk; if the whole chunk was removed,
            # seek the nearest remaining caption (or the first missing caption).
            nearest = min(range(len(chunks)), key=lambda i: abs(
                (chunks[i].get("start_f", 0) / fps if isinstance(chunks[i], dict)
                 and _number(chunks[i].get("start_f")) else 0) - word["start"]), default=0)
            owner = next((i for i, c in enumerate(chunks) if isinstance(c, dict)
                          and _number(c.get("w0")) and _number(c.get("w1"))
                          and c["w0"] <= position <= c["w1"]), nearest)
            rows.append(_row("caption-word-lost", f"The spoken word '{word['word'].strip()}' at {word['start']:.3f} s "
                             "is missing from the captions. Restore it or declare why it is dropped.",
                             f"caption {owner}", word["start"]))
    return rows


def main(argv=None):
    ensure_utf8_output()
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: caption_check.py <reel_dir>")
        return 2
    rows = run({"reel_dir": argv[0], "fps": None, "cuts": None, "beats": None, "render": None})
    for row in rows:
        print(f"{row['level']} {row['check']}: {row['msg']} ({row['where']})")
    if not rows:
        print("Caption check: nothing to fix.")
    return 1 if any(row["level"] == "block" for row in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
