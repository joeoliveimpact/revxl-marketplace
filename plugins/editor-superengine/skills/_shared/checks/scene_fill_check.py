#!/usr/bin/env python3
"""Pre-render check: scene text fits and a counter ends on its beat's number.

    python -X utf8 -I scene_fill_check.py <reel_dir>   exit 1 on any block, else 0

Module contract (H-B6): PHASE = "pre"; run(ctx) returns
[{check, level: "block", msg, where}]. ctx = {reel_dir, fps, cuts, beats, render}.
Calls scene_check.fill_problems with the whole beat and the cut's word strings,
as compose.py does. Overflow is slot-overflow; a counter/beat mismatch is
final-number. Other fill problems retain a scene-fill block. No beats means
nothing to check. Writes nothing.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2] / "reel-canvas-build" / "scripts"))
sys.path.insert(0, str(HERE.parents[3] / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
import beat_schema  # noqa: E402
import scene_check  # noqa: E402

PHASE = "pre"


def _number(value):
    value = value if isinstance(value, (int, float)) else float(value)
    return format(int(value), ",") if int(value) == value else format(value, ",")


def _plain_problem(problem, beat):
    scene = beat["scene"]
    slot = re.match(r"slot (.+?) is \d+ characters", problem)
    if slot:
        return f"The {slot[1]} text is too long for this scene. Shorten it on the Beat Map board."
    counter = re.match(r"the counter would show (.+?) \((?:value|from)\)", problem)
    if counter:
        return (f"The counter's number {counter[1]} is too long for its space. "
                "Shorten the number or the text beside it on the Beat Map board.")
    if "mid-count fits the display" in problem:
        return "The counter starts outside its counting range. Set its starting number between zero and its final number."
    mismatch = re.match(r"the counter ends on (.+?) but the beat's value is (.+?);", problem)
    if mismatch:
        return (f"The counter ends on {_number(mismatch[1])}, but this moment calls for {_number(mismatch[2])}. "
                "Make those numbers match on the Beat Map board.")
    unheard = re.match(r"(.+?) is not said in the transcript;", problem)
    if unheard:
        # scene_check's :g can round a large claim to scientific notation. Match
        # the original fill to recover its full number rather than rounding again.
        claims = [scene.get("params", {}).get("value")]
        claims += [n for text in scene.get("slots", {}).values() if isinstance(text, str)
                   for n, _ in scene_check.numbers(text)]
        value = next((n for n in claims if isinstance(n, (int, float)) and f"{n:g}" == unheard[1]), unheard[1])
        return f"The number {_number(value)} is not spoken in the cut. Replace it with a spoken number on the Beat Map board."
    msg = " ".join(problem.replace(" (F-11)", "").replace(" (VES-3 f)", "").split())
    return msg[:1].upper() + msg[1:] + ". Fix this scene on the Beat Map board."


def run(ctx):
    beats = ctx.get("beats") or []
    scened = [beat for beat in beats if beat.get("scene") is not None]
    if not scened:
        return []
    words_path = Path(ctx["reel_dir"]) / "work/edit_map.cut.json"
    words = beat_schema.load_words(words_path) if words_path.is_file() else None
    rows = []
    for beat in scened:
        for problem in scene_check.fill_problems(beat["scene"].get("id"), beat, words=words):
            if problem.startswith("the counter ends on "):
                check = "final-number"
            elif "it fits " in problem or "mid-count fits the display" in problem:
                check = "slot-overflow"
            else:
                check = "scene-fill"
            rows.append(dict(check=check, level="block", where="beat %s" % beat.get("id", "unknown"),
                             msg=" ".join(_plain_problem(problem, beat).split())))
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
        print("The scene check could not finish. Restore the Beat Map and cut word list, then run QA again.",
              file=sys.stderr)
        sys.exit(1)
