"""Conservative Natural corrections, in the Grade Board's own slider units."""
import json
from pathlib import Path

BOUNDS = json.loads((Path(__file__).resolve().parents[1] / "looks/natural-bounds.json").read_text(encoding="utf-8"))


def clamp(correction):
    out, notes = dict(correction), []
    for key, (lo, hi) in BOUNDS.items():
        if key not in out:
            continue
        value = out[key]
        held = max(lo, min(hi, value))
        if held != value:
            out[key] = held
            notes.append(f"Natural {key} held at {held:g} (requested {value:g}).")
    return out, notes
