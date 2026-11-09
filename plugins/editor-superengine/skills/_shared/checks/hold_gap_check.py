"""Warn when a long interval between visual events has no written hold reason."""
from fractions import Fraction
import json
from pathlib import Path

PHASE = "pre"


def run(ctx):
    cuts, beats = ctx.get("cuts"), ctx.get("beats")
    if not cuts or not cuts.get("segments"):
        return []
    fps = float(Fraction(str(cuts["fps"])))
    end = cuts["segments"][-1]["out_out_f"]
    events = {0, end}
    events.update(s["out_in_f"] for s in cuts["segments"])
    events.update(b[k] for b in (beats or []) for k in ("start_f", "end_f"))
    reasons = []
    for name in ("beat-map-selection.json", "work/holds.json"):
        path = Path(ctx["reel_dir"]) / name
        try:
            holds = json.loads(path.read_text(encoding="utf-8")).get("holds", []) if path.is_file() else []
            reasons.extend([h["at_f"] for h in holds if isinstance(h.get("reason"), str) and h["reason"].strip()
                            and type(h.get("at_f")) is int])
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    points = sorted(e for e in events if 0 <= e <= end)
    return [dict(check="hold-gap", level="warn", where="work/holds.json", at=a / fps,
                 msg=f"There are {(b - a) / fps:.2f} seconds between visual events. Add a hold reason or consider a change.")
            for a, b in zip(points, points[1:]) if (b - a) / fps > 2.2 and not any(a <= f < b for f in reasons)]
