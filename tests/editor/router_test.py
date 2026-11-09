"""Static router coverage. Run: python -I tests/editor/router_test.py"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "plugins" / "editor-superengine" / "skills"
PREFIX = "editor-superengine:"
ROUTER = "editor-start-here"

# C:/Workspaces/Content Studio/output/orchestrator-mode/11.03.26/skill-map.md
# (11.03.26). Five folds: motion comps, QA and styles -> canvas-build;
# editor-hub -> editor-doctor; master-clock-fix -> reel-first-cuts.
SKILL_MAP = {
    "editor-start-here": "editor-start-here",
    "editor-doctor": "editor-doctor",
    "recording-preflight": "recording-preflight",
    "reel-first-cuts": "reel-first-cuts",
    "reel-grade": "reel-grade",
    "reel-broll": "reel-broll",
    "reel-canvas-build": "reel-canvas-build",
    "reel-sound-pass": "reel-sound-pass",
    "pro-editor-handoff": "pro-editor-handoff",
    "reel-trials": "reel-trials",
    "reel-captions": "reel-captions",
    "caption-writer": "caption-writer",
    "reel-cover": "reel-cover",
    "reel-teardown": "reel-teardown",
    "style-decoder": "style-decoder",
    "reel-motion-comps": "reel-canvas-build",
    "reel-qa": "reel-canvas-build",
    "reel-styles": "reel-canvas-build",
    "editor-hub": "editor-doctor",
    "master-clock-fix": "reel-first-cuts",
}
fail = 0


def ck(name, errors):
    global fail
    print(f"FAIL {name}: {'; '.join(errors)}" if errors else f"PASS {name}")
    fail |= bool(errors)


def section(text, heading):
    level = len(heading.split()[0])
    match = re.search(rf"^{re.escape(heading)}\s*\n(.*?)(?=^#{{1,{level}}} |\Z)",
                      text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"missing section {heading}")
    return match[1]


def main():
    folders = {p.name for p in SKILLS.iterdir() if p.is_dir() and p.name != "_shared"}
    targets = set(SKILL_MAP.values())
    ck("map vs folders", [f"missing SKILL.md: {s}" for s in sorted(targets)
                           if not (SKILLS / s / "SKILL.md").is_file()]
       + [f"unmapped folder: {s}" for s in sorted(folders - targets)])

    text = (SKILLS / ROUTER / "SKILL.md").read_text(encoding="utf-8")
    table = [line.strip().strip("|").split("|")
             for line in section(text, "## Which skill").splitlines()
             if line.strip().startswith("|")]
    if len(table) < 3 or [c.strip() for c in table[0]] != ["The ask", "Invoke"]:
        raise ValueError("missing Which skill table")
    if len(table[1]) != 2 or any(not re.fullmatch(r":?-+:?", c.strip()) for c in table[1]):
        raise ValueError("invalid table separator")
    rows = []
    for cells in table[2:]:
        if len(cells) != 2:
            raise ValueError(f"expected two table cells: {cells}")
        match = re.fullmatch(r"`?(editor-superengine:[a-z0-9-]+)`?(?:\s+\(.*\))?", cells[1].strip())
        if not match:
            raise ValueError(f"invalid Invoke: {cells[1]}")
        rows.append((cells[0].strip(), match[1]))
    invoked = {invoke.removeprefix(PREFIX) for _, invoke in rows}
    ck("router vs folders", [f"unknown Invoke: {s}" for s in sorted(invoked - folders)]
       + [f"missing router target: {s}" for s in sorted(targets - {ROUTER} - invoked)])

    asks = json.loads((ROOT / "tests" / "editor" / "router-asks.json").read_text(encoding="utf-8"))
    if not isinstance(asks, list):
        raise ValueError("asks must be an array")
    for i, ask in enumerate(asks, 1):
        if not isinstance(ask, dict) or any(not isinstance(ask.get(k), str)
                                           for k in ("ask", "expect", "row", "hint")):
            raise ValueError(f"ask {i} needs string ask, expect, row and hint fields")
    errors, hints = [], []
    not_built = section(text, "### Not built yet").casefold()
    whats_next = section(text, "## What's next").casefold()
    for ask in asks:
        label, row, expect, hint = (ask[k] for k in ("ask", "row", "expect", "hint"))
        if row == "not-built":
            want = "not-built"
        elif row in SKILL_MAP:
            want = PREFIX + SKILL_MAP[row]
        else:
            want = None
        if want is None or expect != want:
            errors.append(f"{label!r}: row {row!r} expects {want!r}, got {expect!r}")
        if expect != "not-built" and (not expect.startswith(PREFIX)
                                      or expect.removeprefix(PREFIX) not in folders):
            errors.append(f"{label!r}: unknown expect {expect!r}")
        sources = [not_built] if expect == "not-built" else [
            phrase.casefold() for phrase, invoke in rows if invoke == expect]
        if expect == PREFIX + ROUTER:
            sources = [whats_next]
        if not hint.strip() or not any(hint.casefold() in source for source in sources):
            hints.append(f"{label!r}: hint {hint!r} missing from {expect} router text")
    covered = {ask["row"] for ask in asks}
    errors += [f"missing ask for map row: {s}" for s in sorted(set(SKILL_MAP) - {ROUTER} - covered)]
    if "not-built" not in covered:
        errors.append("missing not-built ask")
    ck("asks vs map", errors)
    ck("asks vs router text", hints)
    labels = [ask["ask"].strip().casefold() for ask in asks]
    ck("unique non-empty asks", ["empty or duplicate ask"]
       if not all(labels) or len(labels) != len(set(labels)) else [])

    logic = (ROOT / "plugins" / "editor-superengine" / "hooks" / "mod" / "logic.ts").read_text(encoding="utf-8")
    match = re.search(r"^export const LABELS\b.*?^\}", logic, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError("missing Cockpit LABELS")
    phrases = re.findall(r'''^\s*(\w+):\s*\{[^}]*?\bphrase:\s*('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")''',
                         match[0], re.MULTILINE)
    if not phrases:
        raise ValueError("missing Cockpit phrases")
    errors = []
    for action, literal in phrases:
        phrase = ast.literal_eval(literal).replace("<reel>", "Reel 3").replace("<board>", "Sound Board")
        if not any(ask["ask"] == phrase for ask in asks):
            errors.append(f"{action}: missing ask {phrase!r}")
    ck("Cockpit phrases vs asks", errors)
    return fail


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"FAIL router inputs: {exc}")
        sys.exit(1)
