#!/usr/bin/env python3
"""Pre-render check: each beat's saved speech quote still resolves in the cut.

    python -X utf8 -I anchor_check.py <reel_dir>      exit 1 on any block, else 0

Module contract (H-B6): PHASE = "pre"; run(ctx) returns
[{check, level: "block", msg, where}]. ctx = {reel_dir, fps, cuts, beats, render}.
Uses beat_schema's speech_anchor rules with work/edit_map.cut.json's words.
No Beat Map or no cut word list means nothing to check. Writes nothing.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2] / "reel-canvas-build" / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
import beat_schema  # noqa: E402

PHASE = "pre"


def run(ctx):
    reel = Path(ctx["reel_dir"])
    beats = ctx.get("beats")
    words_path = reel / "work/edit_map.cut.json"
    if not beats or not words_path.is_file():
        return []
    words = beat_schema.load_words(words_path)
    rows = []
    for beat in beats:
        where = "beat %s" % beat.get("id", "unknown")
        problems = beat_schema.beat_problems(beat, words, where=where)
        for problem in problems:
            if "speech_anchor" not in problem:
                continue
            if "does not match words" in problem:
                msg = "The saved speech quote for %s no longer matches the cut's words." % where
            elif "past the word list" in problem:
                msg = "The saved speech quote for %s points past the cut's last word." % where
            else:
                msg = "The saved speech quote or word range for %s is invalid." % where
            rows.append(dict(check="anchor-lost", level="block", where=where,
                             msg=msg + " Update its quote and word range on the Beat Map board."))
    return rows


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    args = ap.parse_args()
    path = args.reel_dir / "beat-map-selection.json"
    beats = json.loads(path.read_text(encoding="utf-8")).get("beats") if path.is_file() else None
    rows = run(dict(reel_dir=args.reel_dir, fps=None, cuts=None, beats=beats, render=None))
    for row in rows:
        print("%s  %s  %s  (%s)" % (row["level"].upper(), row["check"], row["msg"], row["where"]))
    return 1 if any(row["level"] == "block" for row in rows) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("The speech quote check could not finish. Restore the Beat Map and cut word list, then run QA again.",
              file=sys.stderr)
        sys.exit(1)
