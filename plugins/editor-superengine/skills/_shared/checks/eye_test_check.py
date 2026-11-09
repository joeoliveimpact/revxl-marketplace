"""Optional five-question visual review. Every finding is advisory."""
import json
from pathlib import Path

PHASE = "post"
IDS = ("poster", "confident", "hierarchy", "handshake", "rests")


def run(ctx):
    path = Path(ctx["reel_dir"]) / "work/eye-test.json"
    if not path.is_file():
        return []
    rows = []

    def warn(msg):
        rows.append(dict(check="eye-test", level="warn", msg=msg, where="work/eye-test.json"))

    try:
        answers = json.loads(path.read_text(encoding="utf-8"))["answers"]
        for ident in IDS:
            found = [a for a in answers if a.get("id") == ident]
            if len(found) != 1:
                warn(f"Answer {ident} exactly once; found {len(found)} answers.")
            elif found[0].get("answer") != "yes":
                warn(f"Review {ident}: choose a fix, then answer yes or no again.")
        for extra in sorted({str(a.get("id")) for a in answers} - set(IDS)):
            warn(f"Unknown eye-test question {extra}; use the five documented ids.")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        warn("The eye-test answers could not be read. Save the five answers again.")
    return rows
