#!/usr/bin/env python3
"""Goldmine answer hook: `goldmine: asked-yes|asked-no` can be written only after the user has
replied to the Goldmine question asked word for word (SKLLPLG-365).

Why: in a walk the model reworded the question, put it in bold, and in the same turn appended
`goldmine: asked-yes` to <project>/reel-build/provenance.md before the user had answered.

UserPromptSubmit: when the assistant text of the turn this prompt answers holds a line that is
exactly structure_gate.GOLD_Q (stripped; curly apostrophes and runs of spaces allowed, nothing
else: no bold, quotes or rewording), append `goldmine-asked: <stamp("goldmine", project)>` to
provenance.md and add one line of context telling the model to record the answer now. That turn
is read from transcript_path: the assistant text after the last real user prompt (sidechain,
isMeta and tool_result entries do not count); when this prompt is already logged, the turn before.
PostToolUse(AskUserQuestion): the same, when one of its questions is exactly GOLD_Q.
PreToolUse(Write|Edit|MultiEdit|Bash|PowerShell): new text (content, new_string, command) that
names provenance and holds `goldmine: asked-` is blocked (exit 2, reason on stderr) while
provenance.md has no valid goldmine-asked: line; new text holding `goldmine-asked:` is always
blocked, since only this hook writes that line. structure_gate.py check 9 checks the order on disk.

Project: found as hooks/stamp-on-skill.py finds it (its project() is reused). Fail-open: any
error exits 0 with nothing written. Stdlib only.
Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import importlib.util, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ANSWER = re.compile(r"goldmine:[ \t]*asked-", re.I)
MARK = re.compile(r"goldmine-asked:", re.I)


def load():
    sys.path.insert(0, str(HERE.parent / "skills" / "reel-scripter"))
    import structure_gate as gate
    spec = importlib.util.spec_from_file_location("stamp_on_skill", HERE / "stamp-on-skill.py")
    sos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sos)
    return gate, sos.project


def flat(t):
    return " ".join(str(t).replace("\u2019", "'").split())


def turn_text(path):
    """Assistant text blocks of the turn the current prompt answers."""
    prev, turn = [], []
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read()
    if "Content Goldmine dashboard" not in raw:  # runs on every prompt: skip the parse when it cannot match
        return []
    for ln in raw.split(chr(10)):  # not splitlines(): a raw U+2028 inside a JSON line must not split it
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(e, dict) or e.get("isSidechain") or e.get("isMeta"):
            continue
        c = (e.get("message") or {}).get("content")
        blocks = [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []
        if e.get("type") == "assistant":
            turn += [b.get("text", "") for b in blocks if b.get("type") == "text"]
        elif e.get("type") == "user" and (isinstance(c, str) or any(b.get("type") == "text" for b in blocks)):
            prev, turn = turn, []
    return turn or prev


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    event = data.get("hook_event_name")
    inp = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    gate, project = load()
    q = flat(gate.GOLD_Q)
    if event == "PreToolUse":
        new = " ".join(str(x) for x in [inp.get("content"), inp.get("new_string"), inp.get("command")]
                       + [e.get("new_string") for e in inp.get("edits") or [] if isinstance(e, dict)] if x)
        where = f"{inp.get('file_path') or ''} {inp.get('command') or ''}".lower()
        if MARK.search(new):
            why = ("only the plugin hook writes goldmine-asked: lines, when the user replies to the Goldmine "
                   "question. Write only the goldmine: line; to remove one line, Edit just that line.")
        elif ANSWER.search(new) and "provenance" in where:
            proj = project(data.get("cwd"))
            prov = proj / "reel-build" / "provenance.md" if proj else None
            if prov is None or (prov.exists() and gate.gold_mark(prov.read_text(encoding="utf-8-sig").splitlines(), proj)
                                is not None):
                return 0
            why = ("a goldmine: asked-yes or asked-no line is written only after the user has replied to the "
                   "Goldmine question, and provenance.md has no goldmine-asked: line yet (the plugin writes it "
                   "when the user replies to a message holding the question in its exact words). If you just "
                   "asked it, end your turn and wait for the reply. If you asked it in other words, or in bold "
                   "or quotes, ask it again on its own line, exactly:\n" + gate.GOLD_Q)
        else:
            return 0
        sys.stderr.buffer.write(f"[shortform-superengine] Blocked: {why}\n".encode("utf-8"))
        return 2
    if event == "UserPromptSubmit":
        asked = any(flat(ln) == q for t in turn_text(data["transcript_path"]) for ln in t.splitlines())
    elif event == "PostToolUse" and data.get("tool_name") == "AskUserQuestion":
        asked = any(isinstance(x, dict) and flat(x.get("question", "")) == q for x in inp.get("questions") or [])
    else:
        return 0
    proj = project(data.get("cwd")) if asked else None
    if proj is None:
        return 0
    prov = proj / "reel-build" / "provenance.md"
    old = prov.read_text(encoding="utf-8-sig") if prov.exists() else ""
    with open(prov, "a", encoding="utf-8", newline="\n") as f:
        f.write(("\n" if old and not old.endswith("\n") else "") + f"goldmine-asked: {gate.stamp('goldmine', proj)}\n")
    msg = ("[shortform-superengine] The user has now answered the Goldmine question. Record it now: append one "
           f"line to {prov.as_posix()}, `goldmine: asked-yes` if they said yes or `goldmine: asked-no` if they "
           "said no. If the answer is unclear, ask them yes or no before writing either.")
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:
        code = 0
    sys.exit(code)
