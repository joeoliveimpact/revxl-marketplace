#!/usr/bin/env python3
"""PostToolUse(Skill) hook: write a skill's stamp when the Skill tool really calls it.

Why: in walks the model copied `from:` stamp lines out of skill files instead of calling the
skills. Now no skill file holds a stamp: this hook appends `from: <name> <stamp>` to
<project>/reel-build/provenance.md after a real Skill call, and structure_gate.py checks it.
stamp() is imported from skills/reel-scripter/structure_gate.py, the one definition.

Acts only on tool_input.skill = shortform-superengine:<angles|rehooks|hook|polarize|viral>.
rehooks is written as rehookslines when its args carry a step token of 3 or 3-lines
(`step: X`, `step=X`, `step X`, any case), or when its args carry no step token and
provenance.md already holds a valid `from: rehooks` line for this project. Any other step
token (2, 4b, ...) writes rehooks.

Project: the marker's active_brand (legacy brand) -> state/<brand>.json project_path, as
reel-scripter reads it (_shared/references/state-schema.md); else the cwd when it holds
analysis-data.json; else nothing is written.

Fail-silent by contract: always exit 0, never print to stdout. An error after the project is
known goes to <project>/reel-build/stamp-hook.log; any other error is swallowed.
Stdlib only. Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import json, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
NAMES = ("angles", "rehooks", "hook", "polarize", "viral")
STEP = re.compile(r"\bstep(?:[ \t]*[:=][ \t]*|[ \t]+)([0-9A-Za-z][\w.-]*)", re.I)


def project(cwd):
    home = Path.home() / ".claude" / "shortform-superengine"
    try:
        m = json.loads((home / ".superengine").read_text(encoding="utf-8-sig"))
        brand = m.get("active_brand") or m.get("brand")
        p = json.loads((home / "state" / f"{brand}.json").read_text(encoding="utf-8-sig")).get("project_path")
        if p and Path(p).is_dir():
            return Path(p)
    except Exception:
        pass
    if cwd and (Path(cwd) / "analysis-data.json").is_file():
        return Path(cwd)
    return None


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except Exception:
        return
    if not isinstance(data, dict) or data.get("tool_name") != "Skill":
        return
    inp = data.get("tool_input")
    if not isinstance(inp, dict):
        return
    plugin, _, name = str(inp.get("skill") or "").partition(":")
    if plugin != "shortform-superengine" or name not in NAMES:
        return
    proj = project(data.get("cwd") or os.getcwd())
    if proj is None:
        return
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "reel-scripter"))
        import structure_gate as gate
        prov = proj / "reel-build" / "provenance.md"
        old = prov.read_text(encoding="utf-8-sig") if prov.exists() else ""
        if name == "rehooks":
            args = inp.get("args")
            args = args if isinstance(args, str) else json.dumps(args)
            mine = gate.stamp("rehooks", proj)
            had = any(m and m.group(1).lower() == "rehooks" and m.group(2).lower() == mine
                      for m in map(gate.FROM.match, old.splitlines()))
            tok = STEP.search(args)
            tok = tok.group(1).lower().rstrip(".") if tok else None
            if tok in ("3", "3-lines") or (tok is None and had):
                name = "rehookslines"
        prov.parent.mkdir(parents=True, exist_ok=True)
        with open(prov, "a", encoding="utf-8", newline="\n") as f:
            f.write(("\n" if old and not old.endswith("\n") else "") + f"from: {name} {gate.stamp(name, proj)}\n")
    except Exception as e:
        try:
            with open(proj / "reel-build" / "stamp-hook.log", "a", encoding="utf-8") as f:
                f.write(f"{type(e).__name__}: {e}\n")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
