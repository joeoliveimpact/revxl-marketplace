#!/usr/bin/env python3
"""Checks on reel-scripter's final script <project>/scripts/<slug>.md, branching on
hook_event_name and tool_name. A final script is a .md (not .skeleton.md, not .draft.md) in a folder named
`scripts` whose parent holds analysis-data.json or a reel-build/ folder.

PreToolUse(Write), not final yet (SKLLPLG-370): a Write that would CREATE scripts/<slug>.md while
scripts/<slug>.skeleton.md exists and reel-build/provenance.md holds no `passed:` line for that
skeleton's text is blocked (exit 2, stderr to the model): the gate has not passed this reel. Why:
in walk 369b-gut the model, rightly refusing to invent health claims, saved an INCOMPLETE script
at the final path before Step 4a and the gate; the next reel then resumed it. The block routes it
to <slug>.draft.md and tells the model to say in plain words what the client still has to give.
An existing final script (already written once) and a script with no skeleton are never blocked,
so older reels stay editable after a newer reel's pass rewrites provenance.md. An Edit or MultiEdit
that creates the final script (its first old_string is empty, which Claude Code refuses on a file
with content) gets the same rule in PostToolUse, after it lands. Ceiling: a final script deleted and
written again needs its skeleton's passed: line again.

PostToolUse(Write|Edit|MultiEdit), storyboard (SKLLPLG-361): check the storyboard table every time
the final script is written and hand failures back so the model fixes the file. Acts only on a
final script that has a sibling <slug>.skeleton.md or a `## Text overlays` heading, so client
notes kept in scripts/ are left alone. The rules live in skills/reel-scripter/structure_gate.py
storyboard_problems(), the one definition. Problems -> stderr, exit 2 (Claude Code shows stderr
of a PostToolUse exit 2 to the model). Pass -> exit 0, silent.

Placeholders (SKLLPLG-370): walks 050-reel2 and 050-contra saved a final script still holding
[NEEDS YOUR INPUT], [KEYWORD] and an OPEN: note. A final script in which structure_gate.py
placeholder_problems() (the one definition) finds anything is a draft: PreToolUse(Write) blocks it
before it lands and PostToolUse(Edit|MultiEdit) flags it after (exit 2 both), routing it to
<slug>.draft.md and telling the model to say in plain words what the client still has to give.
Checked on the same final scripts as the storyboard (a sibling skeleton or a `## Text overlays`
heading), and before it: a script with placeholders gets that message only.

Terminal route (SKLLPLG-370): walk 050-gut wrote the final script with a Bash python heredoc, so no
Write or Edit hook saw it. The command is never parsed; the file is checked. PreToolUse(Bash|
PowerShell) records size and mtime of every final script in the project's scripts/ (the project as
hooks/stamp-on-skill.py finds it; none = silent, nothing recorded) in
~/.claude/shortform-superengine/script-snap/<tool_use_id>.json. PostToolUse(Bash|PowerShell), and
PostToolUseFailure(Bash|PowerShell) for a command that exits non-zero (CLI 2.1.287 fires that one
instead), start through hooks/script-post.sh, which skips Python when the call left no snapshot; this
reads and deletes that file and checks each final script the call created or changed: a new one gets the
not-final rule above, then each gets the placeholder rule and the storyboard check, with the same exit
2 and a message saying what to move or fix. Ceilings: only the active project's scripts/ is watched; a
snapshot older than a day is pruned, so a call running longer goes unchecked; no snapshot (its Pre did
not run) = silent.

Fail-open: any error exits 0 silently. Never prints to stdout. Stdlib only.
Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import importlib.util, json, re, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SNAPS = Path.home() / ".claude" / "shortform-superengine" / "script-snap"
SHAPE = ("Required shape: a `## Text overlays` table `| Beat | Seconds | Overlay | Visual cue |`, one row "
         "per 3 to 5 s (no row over 5 s), exactly one visual cue per row, every script section covered, "
         "times back to back from 0:00.")
OVERLAYS = re.compile(r"^[ \t]*#{2,3}[ \t]+Text[ -]overlays?\b", re.I | re.M)
NOT_FINAL = ("Not saved: {name} is the final script, and the gate has not passed this reel's skeleton ({skel} "
             "has no matching passed: line in reel-build/provenance.md). Finish Step 4a (viral) and the Step 4b "
             "gate first, then write it. If you are stopping with parts missing, save it as {draft} instead and "
             "tell the client in plain words what you still need from them (for example: their facts for the "
             "proof beat).")
NOT_FINAL_AFTER = ("{name} is the final script, and the gate has not passed this reel's skeleton yet ({skel} has no "
                   "matching passed: line in reel-build/provenance.md), so it cannot stay at that path. Move it to "
                   "{draft} now. Then finish Step 4a (viral) and the Step 4b gate and write the final script; if you "
                   "are stopping with parts missing, tell the client in plain words what you still need from them "
                   "(for example: their facts for the proof beat).")
PLACEHOLDER = ("{lead}{name} is the final script, and it still holds parts the client has to give: {found}. A final "
               "script holds none. {fix}, and tell the client in plain words what you still need from them (for "
               "example: the keyword for the CTA, or their own facts for a beat). Write {name} once every part is "
               "filled.")


def final(fp):
    """(project, skeleton path) when fp is a final script path, else None."""
    name = fp.name.lower()
    if (not name.endswith(".md") or name.endswith(".skeleton.md") or name.endswith(".draft.md")
            or fp.parent.name.lower() != "scripts"):
        return None
    proj = fp.parent.parent
    if not ((proj / "analysis-data.json").is_file() or (proj / "reel-build").is_dir()):
        return None
    return proj, fp.with_name(fp.name[:-3] + ".skeleton.md")


def check(fp, text, new, pre):
    """The message for this write of the final script fp (its text; new = it did not exist before;
    pre = it has not landed yet), or None when it may stand."""
    proj, skel = final(fp)
    sys.path.insert(0, str(HERE.parent / "skills" / "reel-scripter"))
    import structure_gate as gate
    name, draft = f"scripts/{fp.name}", f"scripts/{fp.name[:-3]}.draft.md"
    if new and skel.is_file():
        with open(skel, encoding="utf-8-sig") as f:
            want = gate.fingerprint(f.read())
        prov = proj / "reel-build" / "provenance.md"
        ptext = prov.read_text(encoding="utf-8-sig") if prov.is_file() else ""
        if want not in [m.group(1).lower() for m in map(gate.PASSED.match, ptext.splitlines()) if m]:
            return (NOT_FINAL if pre else NOT_FINAL_AFTER).format(name=name, skel=skel.name, draft=draft)
    if not (skel.is_file() or OVERLAYS.search(text)):
        return None
    found = gate.placeholder_problems(text)
    if found:
        return PLACEHOLDER.format(lead="Not saved: " if pre else "", name=name, found=", ".join(found),
                                  fix=f"Save it as {draft} instead" if pre else
                                  f"Move it to {draft} now (rename it, so nothing stays at {name})")
    probs = [] if pre else gate.storyboard_problems(text)
    return f"Storyboard check failed for {fp.name}:\n" + "".join(f"- {p}\n" for p in probs) + SHAPE if probs else None


def scripts(proj):
    """{name: [size, mtime_ns]} of the final scripts in proj/scripts."""
    d = proj / "scripts"
    return {f.name: [f.stat().st_size, f.stat().st_mtime_ns] for f in d.glob("*.md") if final(f)} if d.is_dir() else {}


def terminal(data):
    """Bash|PowerShell. Pre: snapshot the active project's final scripts. Post: check the ones this call
    created or changed. Returns the message or None."""
    snap = SNAPS / (re.sub(r"[^\w-]", "_", str(data.get("tool_use_id") or data.get("session_id") or "")) + ".json")
    if data.get("hook_event_name") == "PreToolUse":
        spec = importlib.util.spec_from_file_location("stamp_on_skill", HERE / "stamp-on-skill.py")
        sos = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sos)
        proj = sos.project(data.get("cwd"))
        if proj is None:
            return None
        SNAPS.mkdir(parents=True, exist_ok=True)
        for old in SNAPS.glob("*.json"):  # a call another hook blocked never reaches its Post
            if time.time() - old.stat().st_mtime > 86400:
                old.unlink()
        snap.write_text(json.dumps({"project": str(proj), "scripts": scripts(proj)}), encoding="utf-8")
        return None
    if not snap.is_file():
        return None
    before = json.loads(snap.read_text(encoding="utf-8"))
    snap.unlink()
    proj, old = Path(before["project"]), before["scripts"]
    msgs = [check(proj / "scripts" / n, (proj / "scripts" / n).read_text(encoding="utf-8-sig"), n not in old, False)
            for n, st in scripts(proj).items() if old.get(n) != st]
    return "\n\n".join(m for m in msgs if m) or None


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    if data.get("tool_name") in ("Bash", "PowerShell"):
        msg = terminal(data)
    else:
        fp = Path(str(data["tool_input"]["file_path"]).replace("\\", "/"))
        if not final(fp):
            return 0
        if data.get("hook_event_name") == "PreToolUse":
            if data.get("tool_name") != "Write":
                return 0
            msg = check(fp, str(data["tool_input"].get("content") or ""), not fp.exists(), True)
        else:
            inp = data["tool_input"]
            first = (inp.get("edits") or [{}])[0] if data.get("tool_name") == "MultiEdit" else inp
            new = data.get("tool_name") in ("Edit", "MultiEdit") and first.get("old_string") == ""
            msg = check(fp, fp.read_text(encoding="utf-8-sig"), new, False)
    if not msg:
        return 0
    sys.stderr.buffer.write((msg + "\n").encode("utf-8"))
    sys.stderr.flush()
    return 2


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:
        code = 0
    sys.exit(code)
