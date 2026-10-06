#!/usr/bin/env python3
"""Two checks on reel-scripter's final script <project>/scripts/<slug>.md, branching on
hook_event_name. A final script is a .md (not .skeleton.md, not .draft.md) in a folder named
`scripts` whose parent holds analysis-data.json or a reel-build/ folder.

PreToolUse(Write), not final yet (SKLLPLG-370): a Write that would CREATE scripts/<slug>.md while
scripts/<slug>.skeleton.md exists and reel-build/provenance.md holds no `passed:` line for that
skeleton's text is blocked (exit 2, stderr to the model): the gate has not passed this reel. Why:
in walk 369b-gut the model, rightly refusing to invent health claims, saved an INCOMPLETE script
at the final path before Step 4a and the gate; the next reel then resumed it. The block routes it
to <slug>.draft.md and tells the model to say in plain words what the client still has to give.
An existing final script (already written once) and a script with no skeleton are never blocked,
so older reels stay editable after a newer reel's pass rewrites provenance.md. Ceiling: a final
script deleted and written again needs its skeleton's passed: line again.

PostToolUse(Write|Edit|MultiEdit), storyboard (SKLLPLG-361): check the storyboard table every time
the final script is written and hand failures back so the model fixes the file. Acts only on a
final script that has a sibling <slug>.skeleton.md or a `## Text overlays` heading, so client
notes kept in scripts/ are left alone. The rules live in skills/reel-scripter/structure_gate.py
storyboard_problems(), the one definition. Problems -> stderr, exit 2 (Claude Code shows stderr
of a PostToolUse exit 2 to the model). Pass -> exit 0, silent.

Fail-open: any error exits 0 silently. Never prints to stdout. Stdlib only.
Test: python skills/reel-scripter/structure_gate.py --selftest-hook
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
SHAPE = ("Required shape: a `## Text overlays` table `| Beat | Seconds | Overlay | Visual cue |`, one row "
         "per 3 to 5 s (no row over 5 s), exactly one visual cue per row, every script section covered, "
         "times back to back from 0:00.")
OVERLAYS = re.compile(r"^[ \t]*#{2,3}[ \t]+Text[ -]overlays?\b", re.I | re.M)
NOT_FINAL = ("Not saved: {name} is the final script, and the gate has not passed this reel's skeleton ({skel} "
             "has no matching passed: line in reel-build/provenance.md). Finish Step 4a (viral) and the Step 4b "
             "gate first, then write it. If you are stopping with parts missing, save it as {draft} instead and "
             "tell the client in plain words what you still need from them (for example: their facts for the "
             "proof beat).")


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    fp = Path(str(data["tool_input"]["file_path"]).replace("\\", "/"))
    name = fp.name.lower()
    if (not name.endswith(".md") or name.endswith(".skeleton.md") or name.endswith(".draft.md")
            or fp.parent.name.lower() != "scripts"):
        return 0
    proj = fp.parent.parent
    if not ((proj / "analysis-data.json").is_file() or (proj / "reel-build").is_dir()):
        return 0
    skel = fp.with_name(fp.name[:-3] + ".skeleton.md")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "reel-scripter"))
    import structure_gate as gate
    if data.get("hook_event_name") == "PreToolUse":
        if data.get("tool_name") != "Write" or fp.exists() or not skel.is_file():
            return 0
        with open(skel, encoding="utf-8-sig") as f:
            want = gate.fingerprint(f.read())
        prov = proj / "reel-build" / "provenance.md"
        text = prov.read_text(encoding="utf-8-sig") if prov.is_file() else ""
        if want in [m.group(1).lower() for m in map(gate.PASSED.match, text.splitlines()) if m]:
            return 0
        msg = NOT_FINAL.format(name=f"scripts/{fp.name}", skel=skel.name, draft=f"scripts/{fp.name[:-3]}.draft.md")
        sys.stderr.buffer.write((msg + "\n").encode("utf-8"))
        sys.stderr.flush()
        return 2
    text = fp.read_text(encoding="utf-8-sig")
    if not (skel.is_file() or OVERLAYS.search(text)):
        return 0
    probs = gate.storyboard_problems(text)
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
