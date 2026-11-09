"""Optional transition suggestions, following Beat Map order, never blocking."""
import json
from pathlib import Path

PHASE = "pre"


def run(ctx):
    path = Path(ctx["reel_dir"]) / "storyboard.json"
    try:
        selection = json.loads((Path(ctx["reel_dir"]) / "sketches-selection.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        selection = {}
    has_key = isinstance(selection, dict) and "storyboard" in selection
    if not has_key and not path.is_file():
        return []
    try:
        items = (selection["storyboard"] if has_key else json.loads(path.read_text(encoding="utf-8")))["beats"]
        beats = ctx.get("beats") or []
        rows = []
        for first, second in zip(beats, beats[1:]):
            a, b = items.get(first["id"]), items.get(second["id"])
            if a is not None and b is not None and a.get("out") != b.get("in"):
                rows.append(dict(check="storyboard", level="warn", where=f"beats {first['id']} / {second['id']}",
                                 msg="Suggestion: match the first beat's exit transform to the next beat's entry transform."))
        return rows
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return [dict(check="storyboard", level="warn", where="storyboard.json",
                     msg="Suggestion: save the storyboard transforms again; this file could not be read.")]
