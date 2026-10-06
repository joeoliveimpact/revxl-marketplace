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
viral>. It writes no stamp; it opens a slot for the name in this session's entry of
<project>/reel-build/stamp-pending.json, {"sessions": {"<session_id>": {"open": [...], ...}}}. Every
path reads and writes only its own session's entry, so no chat ever replaces another chat's state;
10 entries are kept: entries without `rs` go first, oldest first, and the current chat's never
(SKLLPLG-370).
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
to `turn` in this session's entry only when it has one; otherwise it writes nothing and creates
no file. Only a shortform Skill call creates an entry. PreToolUse on a Skill call of
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
- Both rules apply only in a session that has called reel-scripter (`rs` in its entry, set by its
  PreToolUse). In any other session a call of angles, rehooks, hook, polarize or viral (each
  wrapper's "Prereq: None") is never blocked and still stamps, so a fix call in a new chat (a reel
  continued without a reel-scripter call) lands its stamp, and a one-off in a second chat cannot
  switch off a reel in progress in another (SKLLPLG-370). Ceiling: provenance.md is per project,
  not per chat, so a one-off's stamp lands in the open reel's provenance.md too.
- Ask the client (Joe, 10.03): in an `rs` session past a pass boundary that came after its last
  reel-scripter call (a reel was finished since then), a Step 2 call with no fresh angles stamp (a
  polarize hot take, rehooks) may be a new reel or a one-off, and only the client knows. It is
  blocked with ASK and `asked` keeps the turn and the pass. A later call whose args carry
  `standalone: yes` (or `standalone=true`, quoted or not), in a LATER user turn than that block and
  on the same pass (the client answered), passes and sets `rs` false,
  so the session's order rules end until reel-scripter is called again. A reel-scripter or angles
  call clears `asked`. A reel-scripter call after the pass starts a new reel, so its Step 2 call
  gets Rule 1. Ceiling: a second reel started in that session without a reel-scripter call runs
  unchecked.
A blocked call changes nothing, except that an ASK block keeps `asked` (and the pass it saw). Exit 2 puts the stderr text
in front of the model and stops the call.

Fail-open by contract: exit 0 except a block (exit 2, the reason on stderr); never print to
stdout. An error after the project is known goes to <project>/reel-build/stamp-hook.log and
exits 0; any other error is swallowed.
Stdlib only. Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import json, os, re, sys, time
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
         "turn; make this call after the user replies. Pick an option only when the user asked you to "
         "choose; then say which one and why, and that they can change it.")
ASK = ("Blocked: Step 1 has not run for a new reel, and a reel was finished since reel-scripter last ran in "
       "this chat, so this call may be a one-off. Ask the client in plain words whether they want a new reel or "
       "just this on its own, and end your turn. New reel: Call Skill shortform-superengine:angles with step: 1 "
       "(Step 1). On its own: after they reply, call this skill again with the line `standalone: yes` in its args.")
STANDALONE = re.compile(r"""(?<![\w-])standalone["']?[ \t]*[:=][ \t]*["']?(?:yes|true)\b""", re.I)
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


def load_pending(path):
    """stamp-pending.json's {session_id: state} map; {} when the file is missing or unreadable."""
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig")).get("sessions")
        return {k: v for k, v in d.items() if isinstance(v, dict)} if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_pending(path, sessions, sid, state):
    """Write this session's entry as the newest and keep 10: entries without `rs` go first, oldest
    first, never the current one. A temp file swapped in with os.replace, so another chat's hook does
    not read a half-written file and drop every entry (except on the plain-write fallback below)."""
    # ponytail: read-modify-write with no lock, so two chats' hooks in the same instant can lose one
    # write. Add a lock file if that ever bites.
    sessions.pop(sid, None)
    sessions[sid] = state
    others = [k for k in sessions if k != sid]
    others = [k for k in others if not sessions[k].get("rs")] + [k for k in others if sessions[k].get("rs")]
    for k in others[:max(0, len(sessions) - 10)]:
        del sessions[k]
    body = json.dumps({"sessions": sessions}) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        for _ in range(5):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.02)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
    # Windows refuses the swap while another program (OneDrive sync, antivirus) holds the file open,
    # but allows a plain write; a lost write would lose a turn and block the client's next step.
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)


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
        sessions = load_pending(pend)
        state = sessions.get(sid)
        if user:
            if state is not None:
                state["turn"] = state.get("turn", 0) + 1
                save_pending(pend, sessions, sid, state)
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "reel-scripter"))
        import structure_gate as gate
        if data["tool_name"] == "Read":
            opened = state.get("open") if state else None
            if not isinstance(opened, list) or slot not in opened:
                return 0
            old = prov.read_text(encoding="utf-8-sig") if prov.exists() else ""
            with open(prov, "a", encoding="utf-8", newline="\n") as f:
                f.write(("\n" if old and not old.endswith("\n") else "") + f"from: {slot} {gate.stamp(slot, proj)}\n")
            state["open"] = [n for n in opened if n != slot]
            save_pending(pend, sessions, sid, state)
            return 0
        old = prov.read_text(encoding="utf-8-sig") if prov.exists() else ""
        step = step_of(name, inp, old, proj, gate)
        state = state if state is not None else {}
        if not isinstance(state.get("open"), list):
            state["open"] = []
        if pre:
            angled = has(old, "angles", proj, gate)
            passed = [m.group(1).lower() for m in map(gate.PASSED.match, old.splitlines()) if m]
            # ponytail: "this session called reel-scripter" is the pipeline test, so a reel resumed in a
            # new session without a reel-scripter call runs unchecked. Key it on the open reel if that bites.
            if name == "reel-scripter":
                state["rs"], state["rsp"] = True, (passed[-1] if passed else None)
            elif not state.get("rs"):
                return 0
            if passed and not angled and state.get("pass") != passed[-1]:
                state["top"], state["pass"] = 5, passed[-1]
            turn, top = state.get("turn", 0), state.get("top", 0)
            if passed and step == 2 and not angled and state.get("rsp") != passed[-1]:
                args, asked = inp.get("args"), state.get("asked") or [0, None]
                if (STANDALONE.search(args if isinstance(args, str) else json.dumps(args))
                        and asked[1] == passed[-1] and turn > asked[0]):
                    state["rs"] = False
                    save_pending(pend, sessions, sid, state)
                    return 0
                state["asked"] = [turn, passed[-1]]
                save_pending(pend, sessions, sid, state)
                sys.stderr.write(ASK + "\n")
                return 2
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
                if step <= 1:
                    state.pop("asked", None)
                state["top"], state["at"] = step, turn
                save_pending(pend, sessions, sid, state)
            return 0
        if step == 4:
            name = "rehookslines"
        if name not in state["open"]:
            state["open"].append(name)
            save_pending(pend, sessions, sid, state)
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
