#!/usr/bin/env python3
"""Ask about word-free stretches of at least 3 seconds in the kept output."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output


def silences(cuts, words):
    fps, speed = float(Fraction(str(cuts["fps"]))), float(cuts.get("speed", 1))
    spans = []
    end = 0.0
    for seg in cuts.get("segments", []):
        start, stop = seg["src_in_f"] / fps, seg["src_out_f"] / fps
        offset = seg["out_in_f"] / fps
        end = max(end, seg["out_out_f"] / fps)
        for word in words:
            if "take" in seg and str(word.get("take", 1)) != str(seg["take"]):
                continue
            a, b = max(start, float(word["start"])), min(stop, float(word["end"]))
            if b > a:
                spans.append((offset + (a - start) / speed, min(end, offset + (b - start) / speed)))
    cursor, gaps = 0.0, []
    for a, b in sorted(spans) + [(end, end)]:
        if a - cursor >= 3 - 1e-9:
            gaps.append(dict(start=round(cursor, 3), end=round(a, 3), duration=round(a - cursor, 3)))
        cursor = max(cursor, b)
    return gaps


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("work", type=Path, nargs="?", default=Path("work"))
    ap.add_argument("--json", action="store_true", help="save work/long-silences.json")
    a = ap.parse_args(argv)
    try:
        cuts = json.loads((a.work / "cuts.json").read_text(encoding="utf-8"))
        if cuts.get("takes"):
            words = []
            for take, info in cuts["takes"].items():
                doc = json.loads((a.work.parent / info["work"] / "edit_map.json").read_text(encoding="utf-8"))
                words.extend(dict(w, take=take) for w in doc["words"])
        else:
            words = json.loads((a.work / "edit_map.json").read_text(encoding="utf-8"))["words"]
        gaps = silences(cuts, words)
        choices = {"linger": "keep the last caption on screen", "title": "show a title card", "cut": "cut this quiet part"}
        try:
            selection = json.loads((a.work.parent / "tweak-selection.json").read_text(encoding="utf-8"))
            saved = selection.get("silences", []) if isinstance(selection, dict) else []
            if not isinstance(saved, list):
                saved = []
        except (OSError, ValueError):
            saved = []
        for gap in gaps:
            for entry in saved:
                if not (isinstance(entry, dict) and isinstance(entry.get("start"), (int, float))
                        and not isinstance(entry["start"], bool) and isinstance(entry.get("choice"), str)
                        and entry["choice"] in choices):
                    continue
                try:
                    matched = abs(entry["start"] - gap["start"]) <= .05
                except OverflowError:
                    continue
                if matched:
                    gap["choice"] = entry["choice"]
                    break
            if "choice" in gap:
                print(f"At output {gap['start']:.2f} s ({gap['duration']:.2f} s without words): "
                      f"the client chose {choices[gap['choice']]} on the Tweak board.")
                continue
            print(f"At output {gap['start']:.2f} s ({gap['duration']:.2f} s without words): "
                  "linger on the last caption / title card / cut it?")
        if a.json:
            (a.work / "long-silences.json").write_bytes((json.dumps(dict(silences=gaps), indent=2) + "\n").encode("utf-8"))
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
        print("Long silences could not be checked. Restore cuts.json and edit_map.json, then ask again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
