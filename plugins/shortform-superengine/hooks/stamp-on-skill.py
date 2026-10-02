#!/usr/bin/env python3
"""PostToolUse(Skill|Read) hook: write a skill's stamp only when the Skill tool calls it AND
the model then Reads that skill's method file, in the same session.

Why: in walks the model copied `from:` stamp lines out of skill files instead of calling the
skills, and later called a skill without loading its method (SKLLPLG-361). Now no skill file
holds a stamp: this hook appends `from: <name> <stamp>` to <project>/reel-build/provenance.md
after a real Skill call followed by a Read of the method file, and structure_gate.py checks it.
stamp() is imported from skills/reel-scripter/structure_gate.py, the one definition.

Skill call: acts only on tool_input.skill = shortform-superengine:<angles|rehooks|hook|polarize|
viral>. It writes no stamp; it opens a slot for the name in <project>/reel-build/stamp-pending.json,
{"session": "<session_id>", "open": [...]}. A file for another session_id is dropped first.
rehooks opens rehookslines when its args carry a step token of 3 or 3-lines (`step: X`,
`step=X`, `step X`, any case), or when its args carry no step token and provenance.md already
holds a valid `from: rehooks` line for this project. Any other step token (2, 4b, ...) opens
rehooks.

Read: when tool_input.file_path is one of this plugin's own method files (inside the plugin
root this script sits in; backslashes and case do not matter) and its slot is open for this
session_id, append the stamp and close the slot. Method files: skills/<name>/references/
legit-<name>.md for angles, rehooks, hook, polarize and viral; skills/rehooks/references/
step3-lines.md for rehookslines. A Read with no open slot, before the call, in another session
or of a copy outside the plugin root writes nothing. A missing session_id counts as "".

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
ROOTS = {Path(__file__).absolute().parent.parent, Path(__file__).resolve().parent.parent}
METHOD = {f"skills/{n}/references/legit-{n}.md": n for n in NAMES}
METHOD["skills/rehooks/references/step3-lines.md"] = "rehookslines"


def norm(p):
    return str(p).replace("\\", "/").lower()


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


def load_pending(path, sid):
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(d, dict) and d.get("session") == sid and isinstance(d.get("open"), list):
            return d
    except Exception:
        pass
    return {"session": sid, "open": []}


def save_pending(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(d) + "\n")


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except Exception:
        return
    if not isinstance(data, dict) or data.get("tool_name") not in ("Skill", "Read"):
        return
    inp = data.get("tool_input")
    if not isinstance(inp, dict):
        return
    sid = str(data.get("session_id") or "")
    if data["tool_name"] == "Read":
        fp = norm(inp.get("file_path") or "")
        slot = next((METHOD.get(fp[len(r):]) for r in (norm(x) + "/" for x in ROOTS) if fp.startswith(r)), None)
        if slot is None:
            return
    else:
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
        pend = proj / "reel-build" / "stamp-pending.json"
        if data["tool_name"] == "Read":
            if not pend.exists():
                return
            state = load_pending(pend, sid)
            if slot not in state["open"]:
                return
            old = prov.read_text(encoding="utf-8-sig") if prov.exists() else ""
            with open(prov, "a", encoding="utf-8", newline="\n") as f:
                f.write(("\n" if old and not old.endswith("\n") else "") + f"from: {slot} {gate.stamp(slot, proj)}\n")
            state["open"] = [n for n in state["open"] if n != slot]
            save_pending(pend, state)
            return
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
        state = load_pending(pend, sid)
        if name not in state["open"]:
            state["open"].append(name)
            save_pending(pend, state)
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
