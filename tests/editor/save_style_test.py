"""Save this reel's choices and workspace skill: <scratch> [--case NAME]."""
import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "plugins/editor-superengine/skills"
sys.path.insert(0, str(SKILLS / "_shared"))
import saved_style as ss
sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import copy_tool_state


def write(target, data):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((json.dumps(data) + "\n").encode("utf-8"))


def run(*args):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(SKILLS / "_shared/saved_style.py"),
                           *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=30)


def fixture(root):
    workspace = root / "client workspace"
    reel = workspace / "clips/reel-1"
    reel.mkdir(parents=True)
    write(workspace / "editor/editor.config.json", {"paths": {"videos": "clips"}})
    bm = {"sent_at": "2026-11-05T10:00:00-05:00", "edit_style": {
        "style": "punch-in", "punch_scale": 1.2, "moves": {
            "opening_settle": True, "follow_cam": False,
            "word_punches": {"preset": "dramatic", "shape": "eased", "picks": [2, 7]},
            "ratchet": {"picks": [1, 3], "levels": 3},
            "push": {"segments": "all", "to": 1.09},
            "ken_burns": {"segments": [0], "to": 1.1},
            "reframe": {"segments": [1], "edge": "left"}}},
        "caption_style": {"style": "clean"}}
    write(reel / "beat-map-selection.json", bm)
    write(reel / "look-picker-selection.json", {
        "sent_at": "2026-11-05T15:01:00Z", "caption_style": {"style": "boxed"}})
    write(reel / "grade.json", {"look": {"id": "warm", "strength": 0.6}, "cube": "ignored.cube"})
    return workspace, reel, bm


def case_fromreel(root):
    workspace, reel, bm = fixture(root)
    original = copy.deepcopy(bm)
    result = run("save-from-reel", reel)
    assert result.returncode == 0, result.stderr
    saved = ss.load()
    assert saved["caption_style"] == {"style": "boxed"}
    assert saved["look"] == {"id": "warm", "strength": 0.6}
    wanted = copy.deepcopy(bm["edit_style"])
    wanted["moves"]["word_punches"]["picks"] = []
    wanted["moves"]["ratchet"]["picks"] = []
    for move in ("ken_burns", "reframe"):
        wanted["moves"].pop(move)
    assert saved["edit_style"] == wanted
    assert json.loads((reel / "beat-map-selection.json").read_text()) == original
    assert result.stdout.splitlines() == ss.readback(saved)
    assert "accent" not in saved and "font" not in saved
    # Equal timestamps favour the picker, and offsets compare as actual times.
    for stamp, expected in (("2026-11-05T15:00:00Z", "boxed"),
                            ("2026-11-05T14:59:59Z", "clean")):
        write(reel / "look-picker-selection.json", {
            "sent_at": stamp, "caption_style": {"style": "boxed"}})
        assert run("save-from-reel", reel).returncode == 0
        assert ss.load()["caption_style"]["style"] == expected
    bm.update(accent="#123ABC", font="Montserrat")
    write(reel / "beat-map-selection.json", bm)
    assert run("save-from-reel", reel).returncode == 0
    assert (ss.load()["accent"], ss.load()["font"]) == ("#123ABC", "Montserrat")
    (reel / "grade.json").unlink()
    write(reel / "grade-selection.json", {"look": {"id": "mono", "strength": 0.4}})
    assert run("save-from-reel", reel).returncode == 0
    assert ss.load()["look"] == {"id": "mono", "strength": 0.4}


def case_keep(root):
    _, reel, _ = fixture(root)
    kept = {"accent": "#ABCDEF", "font": "Inter", "style_id": "client-style",
            "transitions": {"allowed": ["fade"], "sfx_pair": "soft"},
            "cut": {"default_attempt": "first"}, "future": {"kept": True},
            "standing_notes": [{"id": "n1", "note": "Keep it warm", "status": "matched",
                                "key": "look.id", "value": "warm"}]}
    ss.save(kept)
    assert run("save-from-reel", reel).returncode == 0
    assert all(ss.load()[key] == value for key, value in kept.items())
    before = ss.load()
    for name in ("beat-map-selection.json", "look-picker-selection.json", "grade.json"):
        (reel / name).unlink()
    assert run("save-from-reel", reel).returncode == 0
    assert ss.load() == before, "Missing reel choices replaced saved choices"


def case_named(root):
    _, reel, _ = fixture(root)
    ss.save({"font": "Inter"})
    before = ss.path().read_bytes()
    result = run("save-from-reel", reel, "--name", "client-b")
    assert result.returncode == 0, result.stderr
    assert ss.path("client-b").is_file() and ss.path().read_bytes() == before
    result = run("list")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [f"{name}: {ss.readback(ss.load(name))[0]}"
                                          for name in ("client-b", "default")]


def case_decoded(root):
    workspace, reel, bm = fixture(root)
    del bm["caption_style"]
    write(reel / "beat-map-selection.json", bm)
    (reel / "look-picker-selection.json").unlink()
    write(workspace / "editor/style-decoder/styles/coach/style-spec.json", {"style": {"id": "coach"}})
    result = run("save-from-reel", reel, "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert ss.load()["style_id"] == "coach"
    decoded_line = "Decoded style: Coach (from your style decoder)"
    skill = workspace / ".claude/skills/my-editing-style/SKILL.md"
    for lines in (ss.readback(ss.load()), result.stdout.splitlines(), skill.read_text(encoding="utf-8").splitlines()):
        assert decoded_line in lines
        assert not any(line.startswith("Caption look") for line in lines)
    write(reel / "look-picker-selection.json", {"caption_style": {"style": "boxed"}})
    result = run("save-from-reel", reel, "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    for lines in (ss.readback(ss.load()), result.stdout.splitlines(), skill.read_text(encoding="utf-8").splitlines()):
        assert decoded_line in lines
        assert any(line.startswith("Caption look: Boxed") for line in lines)
    write(workspace / "editor/style-decoder/styles/Coach_B/style-spec.json", {})
    result = run("save-from-reel", reel, "--from-decoded", "Coach_B")
    assert result.returncode == 0, result.stderr
    assert ss.load()["style_id"] == "Coach_B"
    before = ss.path().read_bytes()
    for slug in ("missing", "../coach", "/coach"):
        result = run("save-from-reel", reel, "--from-decoded", slug)
        assert result.returncode == 2 and "Traceback" not in result.stderr
        assert len(result.stderr.splitlines()) == 1
        assert ss.path().read_bytes() == before


def case_skill(root):
    workspace, reel, _ = fixture(root)
    ss.save({"standing_notes": [{"id": "n1", "note": "Keep the laughs", "status": "unmatched"}]})
    # Exercise the public function as well as the CLI.
    ss.save_from_reel(reel)
    skill = workspace / ".claude/skills/my-editing-style/SKILL.md"
    raw = skill.read_bytes()
    text = raw.decode("utf-8")
    assert text.startswith("---\nname: my-editing-style\n")
    assert ('description: Use when the client says "use my style" or "edit this my way"; '
            'for anything else start at editor-superengine:editor-start-here.') in text
    assert all(line in text for line in ss.readback(ss.load()))
    assert ("Run the edit in the pipeline order of editor-superengine:editor-start-here, invoking each skill it names; "
            "finish with the before-posting check in "
            "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/qa-check.md.") in text
    assert "Claude asks which saved style to use at the start of each reel; the default is the recommended pick." in text
    assert not re.search(r"^\s*\d+[.)]\s", text, re.M), "The pipeline must not be duplicated"
    assert not re.search(r"captions.*grade", text, re.I | re.S), "Captions must not precede grade"
    assert "Standing notes:" not in text and "Could not be matched:" in text
    assert len(text.split()) < 600 and b"\r" not in raw
    write(reel / "grade.json", {"look": {"id": "mono", "strength": 1.0}})
    assert run("save-from-reel", reel).returncode == 0
    assert skill.read_bytes() != raw and "Grade look: Mono at 100 %" in skill.read_text()
    handmade = b"My hand-made skill\n"
    skill.write_bytes(handmade)
    result = run("save-from-reel", reel)
    assert result.returncode == 0, result.stderr
    assert skill.read_bytes() == handmade
    candidate = skill.with_name("SKILL.new.md")
    assert candidate.is_file() and "separate" in result.stdout.lower()
    assert run("save-from-reel", reel).returncode == 0
    candidate.write_bytes(handmade)
    before = ss.path().read_bytes()
    assert run("save-from-reel", reel).returncode == 2
    assert candidate.read_bytes() == handmade and ss.path().read_bytes() == before
    other = root / "explicit workspace"
    assert run("save-from-reel", reel, "--workspace", other).returncode == 0
    assert (other / ".claude/skills/my-editing-style/SKILL.md").is_file()


def case_longnotes(root):
    workspace, reel, _ = fixture(root)
    ss.save({"standing_notes": [{"id": "n1", "note": "Keep it warm " * 220, "status": "unmatched"}]})
    before = ss.path().read_bytes()
    result = run("save-from-reel", reel)
    assert result.returncode == 2 and "too long" in result.stderr
    assert ss.path().read_bytes() == before
    assert not (workspace / ".claude/skills/my-editing-style/SKILL.md").exists()


def case_hub(root):
    rows = (SKILLS / "editor-doctor/references/hub.md").read_text(encoding="utf-8").splitlines()
    row = next(line for line in rows if line.startswith("| `style` |"))
    assert "save-from-reel" in row
    assert "Use these choices as the default for your next reels?" in row


def case_doctor(root):
    doctor = (SKILLS / "editor-doctor/SKILL.md").read_text(encoding="utf-8")
    line = next(line for line in doctor.splitlines() if "--set-nle resolve" in line)
    assert "`--set-nle resolve` (Resolve Studio, imported through its own connector)" in line
    assert "`--set-nle mcp` (another editor: files only)" in line
    details = (SKILLS / "editor-doctor/references/doctor-details.md").read_text(encoding="utf-8")
    assert "(`mcp` = files for another editor)" in details


CASES = {"fromreel": case_fromreel, "keep": case_keep, "named": case_named,
         "decoded": case_decoded, "skill": case_skill, "longnotes": case_longnotes, "hub": case_hub,
         "doctor": case_doctor}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="save-style-", dir=scratch) as tmp:
        for name in [args.case] if args.case else CASES:
            root = Path(tmp) / name
            root.mkdir()
            copy_tool_state(ss.runtime.state_dir(), root / "state")
            with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / "state")}):
                try:
                    CASES[name](root)
                    print(f"PASS {name}")
                except Exception as error:
                    failures += 1
                    print(f"FAIL {name}: {type(error).__name__}: {error}")
    print(f"{failures} failed" if failures else "all passed")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
