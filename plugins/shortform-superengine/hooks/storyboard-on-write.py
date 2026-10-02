#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) hook: check the storyboard table of reel-scripter's final
script every time it is written, and hand any failure back to the model so it fixes the file.

Why: in walks the Step 5 storyboard came out as a plain aligned list, or with rows over 5 s and
several cues per row, and nothing checked it (SKLLPLG-361). The rules live in
skills/reel-scripter/structure_gate.py storyboard_problems(), the one definition.

Acts only when tool_input.file_path (backslashes allowed) ends in .md but not .skeleton.md, sits
in a folder named `scripts`, and that folder's parent holds analysis-data.json or a reel-build/
folder. Reads the file from disk. Problems -> stderr, exit 2 (Claude Code shows stderr of a
PostToolUse exit 2 to the model). Pass -> exit 0, silent.

Fail-open: any error exits 0 silently. Never prints to stdout. Stdlib only.
Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import json, sys
from pathlib import Path

sys.dont_write_bytecode = True
SHAPE = ("Required shape: a `## Text overlays` table `| Beat | Seconds | Overlay | Visual cue |`, one row "
         "per 3 to 5 s (no row over 5 s), exactly one visual cue per row, every script section covered, "
         "times back to back from 0:00.")


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    fp = Path(str(data["tool_input"]["file_path"]).replace("\\", "/"))
    name = fp.name.lower()
    if not name.endswith(".md") or name.endswith(".skeleton.md") or fp.parent.name.lower() != "scripts":
        return 0
    proj = fp.parent.parent
    if not ((proj / "analysis-data.json").is_file() or (proj / "reel-build").is_dir()):
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "reel-scripter"))
    import structure_gate as gate
    probs = gate.storyboard_problems(fp.read_text(encoding="utf-8-sig"))
    if not probs:
        return 0
    msg = f"Storyboard check failed for {fp.name}:\n" + "".join(f"- {p}\n" for p in probs) + SHAPE + "\n"
    sys.stderr.buffer.write(msg.encode("utf-8"))
    sys.stderr.flush()
    return 2


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:
        code = 0
    sys.exit(code)
