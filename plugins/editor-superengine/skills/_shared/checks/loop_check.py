"""N5 pre-render ledger check. No ledger means no finding and no writes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reel-canvas-build/scripts"))
import beat_schema

PHASE = "pre"


def run(ctx):
    reel = Path(ctx["reel_dir"])
    path = reel / "beat-map-selection.json"
    if not path.is_file():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError
        if "loops" not in doc or doc["loops"] == []:
            return []
        word_path = reel / beat_schema.DEFAULT_WORDS
        timed = json.loads(word_path.read_text(encoding="utf-8")).get("words")
        if not isinstance(timed, list) or not timed:
            raise ValueError
        problems = beat_schema.loops_problems(doc, timed_words=timed)
    except (OSError, ValueError, TypeError, AttributeError):
        problems = ["The open-loop ledger needs the Beat Map and this cut's timed words; restore them and Send again."]
    return [{"check": "open-loop", "level": "block", "msg": problem, "where": "Open loops"} for problem in problems]
