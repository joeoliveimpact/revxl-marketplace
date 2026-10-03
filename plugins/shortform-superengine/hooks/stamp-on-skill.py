#!/usr/bin/env python3
"""PostToolUse(Skill|Read) hook: write a skill's stamp only when the Skill tool calls it AND
the model then Reads that skill's method file, in the same session. Also PreToolUse(Skill),
UserPromptSubmit and PostToolUse(AskUserQuestion): the order check below. It branches on
hook_event_name.

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

Order (SKLLPLG-362, SKLLPLG-366): walks skipped Step 1, then ran every sub-skill call in one
turn and picked the options themselves, because the gate checks THAT a call happened, never
WHEN. A user turn, UserPromptSubmit or PostToolUse AskUserQuestion (the user answered), adds 1
to `turn` in stamp-pending.json only when that file holds this session_id; otherwise it writes
nothing and creates no file, so a prompt in another session never resets this reel's state.
Only a shortform Skill call creates or resets the file. PreToolUse on a Skill call of
shortform-superengine:<reel-scripter|angles|rehooks|hook|polarize|viral> maps it to a step:
reel-scripter 0, angles 1, rehooks (Step 2) and polarize 2, hook 3, rehooks in Step-3 mode 4,
viral and rehooks with a step token starting 4 (4b) 5. rehooks' mode is read as for the stamp.
`top` is the highest step reached, `at` the turn of the last call at it.
- Pass boundary: provenance.md holds a `passed:` line and no valid angles stamp (the gate's
  skeleton pass rewrote it to that line). The first call in a session that sees a boundary sets
  `top` to 5 and keeps the line's fingerprint as `pass`: fix calls after a pass (rehooks 4b,
  hook, viral) are then backward calls, even in the turn of the pass, and a new reel starts
  at angles, which sets top 1.
- Rule 1: a call at step 2 or later with no valid angles stamp in provenance.md exits 2 (Step 1
  has not run for this reel). Past a pass boundary a call at step 3 or later is a fix call
  (hook, rehooks 3-lines, viral, rehooks 4b at Checkpoint 4) and passes, in any session; a step-2
  call is a new reel and needs a fresh angles stamp, which the angles method Read appends below
  the `passed:` line. Ceiling: a new reel that skips Step 2 and goes straight to hook after a
  pass is treated as a fix call.
- Rule 2: a call above `top` in the same turn as `at` exits 2 (it crosses Checkpoint
  min(top, 3) without the user). Calls at or below `top` pass. Fix calls get Rule 2 as well.
  reel-scripter sets top 0 and angles sets top 1 (a new reel, a new angle).
A blocked call changes nothing. Exit 2 puts the stderr text in front of the model and stops
the call.

Fail-open by contract: exit 0 except a block (exit 2, the reason on stderr); never print to
stdout. An error after the project is known goes to <project>/reel-build/stamp-hook.log and
exits 0; any other error is swallowed.
Stdlib only. Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import json, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
NAMES = ("angles", "rehooks", "hook", "polarize", "viral")
STEPS = {"reel-scripter": 0, "angles": 1, "rehooks": 2, "polarize": 2, "hook": 3, "viral": 5}
RULE1 = ("Blocked: Step 1 has not run for this reel (no valid angles stamp in reel-build/provenance.md). "
         "Call Skill shortform-superengine:angles now with step: 1, passing what the client brought (their "
         "own idea, a leftover angle, a content-plan idea, an open loop) as candidates beside fresh angles, "
         "then Read skills/angles/references/legit-angles.md, propose the options, show Checkpoint 1 and "
         "end your turn. Make this call only after the user picks.")
RULE2 = ("Blocked: you are crossing Checkpoint {n} without the user. Show Checkpoint {n} and end your "
         "turn; make this call after the user replies. Never pick an option for the user.")
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


def load_pending(path, sid, new=True):
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(d, dict) and d.get("session") == sid and isinstance(d.get("open"), list):
            return d
    except Exception:
        pass
    return {"session": sid, "open": []} if new else None


def save_pending(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(d) + "\n")


def has(old, name, proj, gate):
    """provenance.md text `old` holds a valid `from: <name>` line for this project."""
    mine = gate.stamp(name, proj)
    return any(m and m.group(1).lower() == name and m.group(2).lower() == mine
               for m in map(gate.FROM.match, old.splitlines()))


def step_of(name, inp, old, proj, gate):
    """The step of a call (STEPS). rehooks: 4 (Step-3 mode) on a step token of 3 or 3-lines, or on
    no step token after a valid rehooks line; 5 on a token starting 4 (4b); else 2."""
    if name != "rehooks":
        return STEPS[name]
    args = inp.get("args")
    args = args if isinstance(args, str) else json.dumps(args)
    tok = STEP.search(args)
    tok = tok.group(1).lower().rstrip(".") if tok else None
    if tok in ("3", "3-lines") or (tok is None and has(old, "rehooks", proj, gate)):
        return 4
    return 5 if tok and tok.startswith("4") else 2


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    event = data.get("hook_event_name")
    pre = event == "PreToolUse"
    user = event == "UserPromptSubmit" or (event == "PostToolUse" and data.get("tool_name") == "AskUserQuestion")
    if not user and data.get("tool_name") not in (("Skill",) if pre else ("Skill", "Read")):
        return 0
    sid = str(data.get("session_id") or "")
    if not user:
        inp = data.get("tool_input")
        if not isinstance(inp, dict):
            return 0
        if data["tool_name"] == "Read":
            fp = norm(inp.get("file_path") or "")
            slot = next((METHOD.get(fp[len(r):]) for r in (norm(x) + "/" for x in ROOTS) if fp.startswith(r)), None)
            if slot is None:
                return 0
        else:
            plugin, _, name = str(inp.get("skill") or "").partition(":")
            if plugin != "shortform-superengine" or name not in (STEPS if pre else NAMES):
                return 0
    proj = project(data.get("cwd") or os.getcwd())
    if proj is None:
        return 0
    try:
        prov = proj / "reel-build" / "provenance.md"
        pend = proj / "reel-build" / "stamp-pending.json"
        if user:
            state = load_pending(pend, sid, new=False)
            if state is not None:
                state["turn"] = state.get("turn", 0) + 1
                save_pending(pend, state)
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "reel-scripter"))
        import structure_gate as gate
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
            return 0
        old = prov.read_text(encoding="utf-8-sig") if prov.exists() else ""
        step = step_of(name, inp, old, proj, gate)
        state = load_pending(pend, sid)
        if pre:
            angled = has(old, "angles", proj, gate)
            passed = [m.group(1).lower() for m in map(gate.PASSED.match, old.splitlines()) if m]
            if passed and not angled and state.get("pass") != passed[-1]:
                state["top"], state["pass"] = 5, passed[-1]
            turn, top = state.get("turn", 0), state.get("top", 0)
            # ponytail: past a pass boundary every step-3+ call counts as a fix call, so a new reel that
            # skips Step 2 and goes straight to hook after a pass passes Rule 1 (and Rule 2 reads it as a
            # backward call). Tell a fix call from a new reel by the skeleton it edits if that bites.
            if step >= 2 and not angled and not (passed and step >= 3):
                sys.stderr.write(RULE1 + "\n")
                return 2
            if step > top and state.get("at") == turn:
                sys.stderr.write(RULE2.format(n=min(top, 3)) + "\n")
                return 2
            if step <= 1 or step >= top:
                state["top"], state["at"] = step, turn
                save_pending(pend, state)
            return 0
        if step == 4:
            name = "rehookslines"
        if name not in state["open"]:
            state["open"].append(name)
            save_pending(pend, state)
    except Exception as e:
        try:
            with open(proj / "reel-build" / "stamp-hook.log", "a", encoding="utf-8") as f:
                f.write(f"{type(e).__name__}: {e}\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    code = 0
    try:
        code = main()
    except BaseException:
        code = 0
    sys.exit(2 if code == 2 else 0)
