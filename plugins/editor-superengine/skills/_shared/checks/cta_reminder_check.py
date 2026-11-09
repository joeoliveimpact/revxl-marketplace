"""Check the optional corner reminder against end CTAs and sound limits."""
from fractions import Fraction
import json
import math
from pathlib import Path

PHASE = "pre"
SCENES = Path(__file__).resolve().parents[3] / "scenes"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(ctx):
    reel = Path(ctx["reel_dir"])
    path = reel / "cta-reminder.json"
    rows = []
    where = "cta-reminder.json"

    def row(check, level, msg, at=0):
        rows.append(dict(check=check, level=level, msg=msg, where=where, at=at))

    try:
        map_path = reel / "beat-map-selection.json"
        beat_map = read(map_path) if map_path.is_file() else {}
        if "cta_reminder" in beat_map:
            where = "beat-map-selection.json"
            doc = beat_map["cta_reminder"]
        elif path.is_file():
            doc = read(path)
        else:
            return []
        cuts = ctx.get("cuts") or read(reel / "work/cuts.json")
        fps = float(Fraction(str(cuts["fps"])))
        total = cuts["segments"][-1]["out_out_f"] / fps
        start, hold, gain = (doc[k] for k in ("at_s", "hold_s", "gain"))
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, hold, gain)):
            raise ValueError("non-numeric placement")
        if total <= 0 or start < 0 or hold <= 0 or start + hold > total or gain < 0:
            raise ValueError("placement outside reel")
        if gain > .10:
            row("cta-gain", "block", "The reminder sound is above 10%. Lower its gain to 0.10 or less.", start)
        if not .6 * total <= start <= .8 * total:
            row("cta-timing", "warn", "Place the reminder about 60-80% through the reel.", start)
        if not map_path.is_file():
            beat_map = read(map_path)
        beats = ctx.get("beats") if ctx.get("beats") is not None else beat_map.get("beats", [])
        spans = []
        for beat in beats:
            scene = beat.get("scene") or {}
            spec_path = SCENES / str(scene.get("id", "")) / "scene.json"
            category = read(spec_path).get("category") if spec_path.is_file() else None
            if category == "cta-end-card":
                spans.append((beat["start_f"] / fps, beat["end_f"] / fps))
        marks = [m for m in beat_map.get("word_marks", []) if m.get("mark") == "cta"]
        if marks:
            words = read(reel / "work/edit_map.cut.json")["words"]
            spans.extend((float(words[m["w"]]["start"]), float(words[m["w"]]["end"])) for m in marks)
        if any(start < b and a < start + hold for a, b in spans):
            row("cta-overlap", "block", "The reminder overlaps the end CTA or its marked words. Move it earlier.", start)
        return rows
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, ZeroDivisionError):
        row("cta-input", "block", "The reminder placement could not be checked. Save its time, hold and gain again.")
        return rows
