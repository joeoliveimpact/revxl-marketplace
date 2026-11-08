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
    result = run("save-from-reel", reel, "--name", "default")
    assert result.returncode == 0, result.stderr
    saved = ss.load(name="default")
    assert saved["caption_style"] == {"style": "boxed"}
    assert saved["look"] == {"id": "warm", "strength": 0.6}
    wanted = copy.deepcopy(bm["edit_style"])
    wanted["moves"]["word_punches"]["picks"] = []
    wanted["moves"]["ratchet"]["picks"] = []
    for move in ("ken_burns", "reframe"):
        wanted["moves"].pop(move)
    assert saved["edit_style"] == wanted
    assert json.loads((reel / "beat-map-selection.json").read_text()) == original
    assert result.stdout.splitlines() == ss.readback(saved) + ["Updated Style 1."]
    assert "accent" not in saved and "font" not in saved
    # Equal timestamps favour the picker, and offsets compare as actual times.
    for stamp, expected in (("2026-11-05T15:00:00Z", "boxed"),
                            ("2026-11-05T14:59:59Z", "clean")):
        write(reel / "look-picker-selection.json", {
            "sent_at": stamp, "caption_style": {"style": "boxed"}})
        assert run("save-from-reel", reel, "--name", "default").returncode == 0
        assert ss.load(name="default")["caption_style"]["style"] == expected
    bm.update(accent="#123ABC", font="Montserrat")
    write(reel / "beat-map-selection.json", bm)
    assert run("save-from-reel", reel, "--name", "default").returncode == 0
    assert (ss.load(name="default")["accent"], ss.load(name="default")["font"]) == ("#123ABC", "Montserrat")
    (reel / "grade.json").unlink()
    write(reel / "grade-selection.json", {"look": {"id": "mono", "strength": 0.4}})
    assert run("save-from-reel", reel, "--name", "default").returncode == 0
    assert ss.load(name="default")["look"] == {"id": "mono", "strength": 0.4}


def case_keep(root):
    _, reel, _ = fixture(root)
    kept = {"accent": "#ABCDEF", "font": "Inter", "style_id": "client-style",
            "transitions": {"allowed": ["fade"], "sfx_pair": True},
            "cut": {"default_attempt": "first"}, "future": {"kept": True},
            "standing_notes": [{"id": "n1", "note": "Keep it warm", "status": "matched",
                                "key": "look.id", "value": "warm"}]}
    ss.save(kept)
    assert run("save-from-reel", reel, "--name", "default").returncode == 0
    assert all(ss.load(name="default")[key] == value for key, value in kept.items())
    before = ss.load(name="default")
    for name in ("beat-map-selection.json", "look-picker-selection.json", "grade.json"):
        (reel / name).unlink()
    assert run("save-from-reel", reel, "--name", "default").returncode == 0
    assert ss.load(name="default") == before, "Missing reel choices replaced saved choices"


def case_named(root):
    _, reel, _ = fixture(root)
    ss.save({"font": "Inter"})
    before = ss.path().read_bytes()
    result = run("save-from-reel", reel, "--name", "client-b")
    assert result.returncode == 0, result.stderr
    assert ss.path("client-b").is_file() and ss.path().read_bytes() == before
    result = run("list")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [f'{row["label"]}' + (" (default)" if row["default"] else "") +
                                          f': {ss.readback(ss.load(name=row["id"]))[0]}' for row in ss.styles()]


def case_decoded(root):
    workspace, reel, bm = fixture(root)
    del bm["caption_style"]
    write(reel / "beat-map-selection.json", bm)
    (reel / "look-picker-selection.json").unlink()
    write(workspace / "editor/style-decoder/styles/coach/style-spec.json", {"style": {"id": "coach"}})
    result = run("save-from-reel", reel, "--name", "default", "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert ss.load(name="default")["style_id"] == "coach"
    decoded_line = "Decoded style: Coach (from your style decoder)"
    skill = workspace / ".claude/skills/my-editing-style/SKILL.md"
    for lines in (ss.readback(ss.load(name="default")), result.stdout.splitlines()):
        assert decoded_line in lines
        assert not any(line.startswith("Caption look") for line in lines)
    assert "## Your default style: none saved" in skill.read_text(encoding="utf-8")
    write(reel / "look-picker-selection.json", {"caption_style": {"style": "boxed"}})
    result = run("save-from-reel", reel, "--name", "default", "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    for lines in (ss.readback(ss.load(name="default")), result.stdout.splitlines()):
        assert decoded_line in lines
        assert any(line.startswith("Caption look: Boxed") for line in lines)
    write(workspace / "editor/style-decoder/styles/Coach_B/style-spec.json", {})
    result = run("save-from-reel", reel, "--name", "default", "--from-decoded", "Coach_B")
    assert result.returncode == 0, result.stderr
    assert ss.load(name="default")["style_id"] == "Coach_B"
    before = ss.path().read_bytes()
    for slug in ("missing", "../coach", "/coach"):
        result = run("save-from-reel", reel, "--name", "default", "--from-decoded", slug)
        assert result.returncode == 2 and "Traceback" not in result.stderr
        assert len(result.stderr.splitlines()) == 1
        assert ss.path().read_bytes() == before


def decoded_fixture(root, spec=None):
    workspace, reel, _ = fixture(root)
    for filename in ("beat-map-selection.json", "look-picker-selection.json", "grade.json"):
        (reel / filename).unlink()
    if spec is None:
        spec = {"spec_version": "1.0", "style": {"slug": "coach", "status": "approved"},
                "adapters": {"editor": {"edit_style": "layout-switch", "caption_style": "karaoke", "look": "mono"}},
                "typography": {"roles": [{"caption_default": True, "closest_available": "Inter"}],
                               "caption_mechanics": {"min_group_duration_ms": 450}},
                "color": {"tokens": [{"role": "Brand ACCENT", "hex": "#123ABC"}]},
                "transitions": [{"type": "zoom"}, {"type": "cut"}, {"type": "spin"}, {"type": "zoom"}],
                "canvas": {"layout_modes": [{"id": "a"}, {"id": "b"}]},
                "motion": {"rules": [{"id": "move-a"}, {"id": "move-b"}]},
                "pacing": {"median_shot_s": 1.4}}
    target = workspace / "editor/style-decoder/styles/coach/style-spec.json"
    write(target, spec)
    return workspace, reel, target, spec


def case_decoded_apply(root):
    _, reel, _, spec = decoded_fixture(root)
    original = copy.deepcopy(spec)
    mapped, unmapped = ss.decoded_choices(spec)
    expected = {"edit_style": {"style": "layout-switch"},
                "caption_style": {"style": "karaoke", "accent": "#123ABC", "min_read_s": 0.45},
                "look": {"id": "mono", "strength": 1.0}, "font": "Inter", "accent": "#123ABC",
                "transitions": {"allowed": ["zoom"]}}
    assert mapped == expected and spec == original, (mapped, spec)
    ss.validate(mapped)
    ss.pick(reel, "copy")
    result = run("save-from-reel", reel, "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert ss.styles() == [{"id": "style-1", "label": "Style 1", "default": False}]
    assert ss._index()["default"] is None
    assert ss.load(reel) == {**expected, "style_id": "coach", "schema": 1}
    assert ss.resolve("caption_style.style", saved=ss.load(reel)) == ("karaoke", "saved")
    assert ss.pick_for(reel)["how"] == "saved" and ss.pick_for(reel)["style"] == "style-1"
    assert ss._index()["active_reel"] == str(reel.resolve())
    assert "Saved as Style 1. Want a different name for it?" in result.stdout
    assert "This decoded style is still a draft." not in result.stdout
    lines = [line for line in result.stdout.splitlines() if line.startswith("Not copied")]
    assert any("layout" in line.lower() and "2" in line for line in lines), lines
    assert any("motion" in line.lower() and "2" in line for line in lines), lines
    assert any("spin" in line.lower() for line in lines), lines
    assert any("rhythm" in line.lower() and "1.4" in line for line in lines), lines
    assert not any("cut" in line.lower() for line in unmapped)
    sys.path.insert(0, str(SKILLS / "reel-captions/scripts"))
    import captions
    assert captions.pick_style(reel, {}, remember=False) == (expected["caption_style"], "saved")
    # Subsequent copies create new styles and keep existing defaults and picks.
    ss.set_default("style-1")
    result = run("save-from-reel", reel, "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert ss._index()["default"] == "style-1" and ss.pick_for(reel)["style"] == "style-1"
    assert ss.styles()[1]["label"] == "Style 2"
    ss.save({**ss.load(name="style-2"), "cut": {"pause_ms": 320},
             "caption_style": {"line_breaks": False}}, "style-2")
    result = run("save-from-reel", reel, "--name", "style-2", "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert ss.load(name="style-2")["caption_style"] == {"line_breaks": False, "style": "karaoke",
                                                       "accent": "#123ABC", "min_read_s": 0.45}
    write(reel / "look-picker-selection.json", {"caption_style": {"style": "boxed"}})
    write(reel / "beat-map-selection.json", {"font": "Montserrat", "accent": "#FFFFFF"})
    result = run("save-from-reel", reel, "--name", "style-2", "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    saved = ss.load(name="style-2")
    assert saved["caption_style"] == {"style": "boxed"}
    assert saved["font"] == "Montserrat" and saved["accent"] == "#FFFFFF"
    assert saved["cut"] == {"pause_ms": 320} and ss.pick_for(reel)["style"] == "style-1"


def case_decoded_siblings(root):
    _, reel, target, spec = decoded_fixture(root)
    assert run("save-from-reel", reel, "--from-decoded", "coach").returncode == 0
    sibling = ss.path("style-1").with_name("style-1.decoded.json")
    raw = sibling.read_bytes()
    note = json.loads(raw)
    assert note["schema"] == 1 and note["slug"] == "coach"
    assert note["spec_version"] == "1.0" and note["spec_status"] == "approved"
    assert note["mapped"] == ["accent", "caption_style", "edit_style", "font", "look", "transitions"]
    assert any("spin" in line.lower() for line in note["unmapped"])
    assert note["saved_at"] and b"\r" not in raw
    ss.rename("style-1", "Coach")
    assert sibling.read_bytes() == raw
    learn = sibling.with_name("style-1.learn.json")
    write(learn, {"schema": 1, "keep": True})
    spec["adapters"]["editor"]["look"] = "warm"
    spec["style"]["status"] = "draft"
    write(target, spec)
    result = run("save-from-reel", reel, "--name", "Coach", "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert "This decoded style is still a draft." in result.stdout
    assert sibling.with_name("style-1@v1.decoded.json").read_bytes() == raw
    assert not learn.with_name("style-1@v1.learn.json").exists()
    assert learn.exists(), "Re-save must leave learning state to style_learn"
    newer = sibling.read_bytes()
    ss.restore("style-1@v1")
    assert sibling.read_bytes() == raw and ss.load(name="style-1")["look"]["id"] == "mono"
    assert sibling.with_name("style-1@v2.decoded.json").read_bytes() == newer
    ss.delete("Coach")
    assert not sibling.exists()
    assert sibling.with_name("style-1@v3.decoded.json").read_bytes() == raw
    ss.restore("style-1@v3")
    assert sibling.read_bytes() == raw
    assert learn.with_name("style-1@v2.learn.json").exists()


def case_decoded_empty(root):
    _, reel, _, _ = decoded_fixture(root, {"style": {"status": "draft"}, "pacing": {"median_shot_s": 1.4}})
    ss.pick(reel, "copy")
    result = run("save-from-reel", reel, "--from-decoded", "coach")
    assert result.returncode == 2 and not result.stdout
    assert result.stderr.splitlines() == ["Nothing in that decoded style matches an editor setting yet, so I didn't save it. This reel starts fresh: I'll ask about each choice."]
    assert ss.pick_for(reel)["how"] == "fresh" and ss.styles() == []
    assert not list(ss.path("default").parent.glob("*.decoded.json"))
    # A failed copy must not replace an existing saved pick either.
    ss.save({"font": "Inter"}, "kept")
    ss.pick(reel, "kept")
    result = run("save-from-reel", reel, "--from-decoded", "coach")
    assert result.returncode == 2 and ss.pick_for(reel)["style"] == "kept"
    assert len(ss.styles()) == 1


def case_decoded_old(root):
    _, reel, _, _ = decoded_fixture(root)
    ss.save({"style_id": "coach"}, "coach")
    write(ss.path("coach"), {"schema": 1, "style_id": "coach"})
    ss.pick(reel, "coach")
    before = {p: p.read_bytes() for p in ss.path("coach").parent.glob("*.json")}
    assert ss.load(reel) == {"schema": 1, "style_id": "coach"}
    assert ss.picker_lines(reel) == ["This reel uses Style 1."]
    assert run("show", "coach").returncode == 0
    assert "Decoded style: Coach (from your style decoder)" in ss.readback(ss.load(reel))
    ss.validate(ss.load(reel))
    assert {p: p.read_bytes() for p in before} == before
    result = run("save-from-reel", reel, "--name", "coach", "--from-decoded", "coach")
    assert result.returncode == 0, result.stderr
    assert ss.load(reel)["caption_style"]["style"] == "karaoke"
    assert ss.path("coach").with_name("coach.decoded.json").exists()


def case_decoded_types(root):
    spec = {"adapters": {"editor": {"edit_style": [], "caption_style": "UNKNOWN (unclear)", "look": "neon"}},
            "typography": {"roles": [{"caption_default": True, "closest_available": "HUMAN-INPUT"}],
                           "caption_mechanics": {"min_group_duration_ms": True}},
            "color": {"tokens": [{"role": "accent", "hex": "#bad"}]},
            "transitions": [{"type": "hard cut"}, {"type": "none"}, {"type": []}],
            "audio": {"music": {"present": False}}, "structure": {"beats": [{"id": "secret-id"}]},
            "assets": {"panel_treatments": [{"id": "secret-id"}]}, "color_extra": {"id": "secret-id"}}
    original = copy.deepcopy(spec)
    data, lines = ss.decoded_choices(spec)
    assert data == {} and spec == original
    assert all(isinstance(line, str) and "\n" not in line and "secret-id" not in line for line in lines)
    for word in ("editing", "caption", "grade", "typography", "colour", "transition", "audio", "beat", "panel"):
        assert any(word in line.lower() for line in lines), (word, lines)
    for invalid in (None, "UNKNOWN", "HUMAN-INPUT", "450", True, 0, -1, float("inf"), float("nan")):
        data, _ = ss.decoded_choices({"typography": {"caption_mechanics": {"min_group_duration_ms": invalid}}})
        assert not data, (invalid, data)
    data, _ = ss.decoded_choices({"typography": {"roles": [
        {"caption_default": True, "closest_available": "Inter"},
        {"caption_default": True, "closest_available": "Montserrat"}]}})
    assert "font" not in data, "Ambiguous caption defaults must not pick an arbitrary font"
    data, _ = ss.decoded_choices({"color": {"tokens": [
        {"role": "accent", "hex": "bad"}, {"role": "accent", "hex": "#123ABC"},
        {"role": "accent", "hex": "#FFFFFF"}]}, "transitions": [
            {"type": "zoom"}, {"type": "fade"}, {"type": "zoom"}]})
    assert data == {"accent": "#123ABC", "caption_style": {"accent": "#123ABC"},
                    "transitions": {"allowed": ["fade", "zoom"]}}


def case_decoded_contract(root):
    sys.path.insert(0, str(SKILLS / "style-decoder/scripts"))
    import stylespec
    workspace, _, target, _ = decoded_fixture(root)
    spec = copy.deepcopy(stylespec.SPEC_TEMPLATE)
    spec["style"].update(slug="coach", status="approved")
    spec["sources"] = [{"id": "src-01", "duration_s": 1}]
    (target.parent / "evidence.txt").write_bytes(b"fixture evidence\n")
    for number, (dotted, _) in enumerate(stylespec.RULE_GROUPS):
        group, _, key = dotted.rpartition(".")
        parent = spec[group] if group else spec
        parent[key] = [{"id": f"rule-{number}", "evidence": ["evidence.txt"],
                        "observed_in": ["src-01"], "confidence": "provisional", "layer": "edit"}]
    spec["typography"]["roles"][0].update(closest_available="Inter", size_metric="em_pct_of_width",
                                         mode_scope=["full"], caption_default=True)
    spec["structure"]["beats"][0]["anchor"] = {"type": "absolute", "s": 0}
    spec["canvas"]["layout_timeline"] = [{"t_start": 0, "t_end": 1, "mode_id": "full"}]
    spec["typography"]["caption_mechanics"] = {"grouping_algorithm": "word groups"}
    spec["typography"]["caption_content_rules"] = {
        "role_precedence": ["caption"], "lexicon": {"brand_nouns": ["Coach"]},
        "transcript_normalization": {"mode": "spoken"}}
    spec["ingredients"] = [{"desc": "A-roll"}]
    spec["adapters"]["hyperframes"].update(constants={"width": 1080}, tween_recipes=[{"duration_s": 0.2}])
    spec["adapters"]["editor"] = {"edit_style": "punch-in", "caption_style": "clean", "look": "natural"}
    write(target, spec)
    write(target.parent / "sources/src-01/layout_timeline.json", {"segments": spec["canvas"]["layout_timeline"]})
    config = root / "decoder-config.json"
    write(config, {"data_dir": str(workspace / "editor/style-decoder")})
    with patch.dict(os.environ, {"EDITOR_SUPERENGINE_CONFIG": str(config)}):
        for command, success in (("validate", "VALIDATE PASS"), ("coverage", "COVERAGE PASS")):
            result = subprocess.run([sys.executable, "-X", "utf8", "-I",
                                     str(SKILLS / "style-decoder/scripts/stylespec.py"), command, "coach"],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            assert result.returncode == 0 and success in result.stdout, result.stdout + result.stderr
    # Unknown editor choices remain legal for the decoder's gates too.
    spec["adapters"]["editor"] = {"edit_style": "UNKNOWN", "caption_style": "UNKNOWN", "look": "UNKNOWN"}
    write(target, spec)
    with patch.dict(os.environ, {"EDITOR_SUPERENGINE_CONFIG": str(config)}):
        for command in ("validate", "coverage"):
            result = subprocess.run([sys.executable, "-X", "utf8", "-I",
                                     str(SKILLS / "style-decoder/scripts/stylespec.py"), command, "coach"],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr


def case_skill(root):
    workspace, reel, _ = fixture(root)
    ss.save({"standing_notes": [{"id": "n1", "note": "Keep the laughs", "status": "unmatched"}]})
    # Exercise the public function as well as the CLI.
    ss.save_from_reel(reel, "default")
    skill = workspace / ".claude/skills/my-editing-style/SKILL.md"
    raw = skill.read_bytes()
    text = raw.decode("utf-8")
    assert text.startswith("---\nname: my-editing-style\n")
    assert ('description: Holds the client\'s saved editing choices and standing notes for editor-superengine. '
            'Use when the client says "use my style" or "edit this my way"; '
            'for anything else start at editor-superengine:editor-start-here.') in text
    assert all(line in text for line in ss.readback(ss.load(name="default")))
    assert ("Invoke editor-superengine:editor-start-here first; it runs the style picker. "
            "Then run the edit in its pipeline order, invoking each skill it names; "
            "finish with the before-posting check: the references/qa-check.md of editor-superengine:reel-canvas-build.") in text
    assert "on this computer" not in text
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    assert 'Claude asks one question, "Which style for this reel?"' in text
    assert '"Copy a reel I like" and "Start fresh"' in text
    assert "A saved style applies only to the reel it was picked for; a new reel gets the style picker." in text
    assert "including its Auto edit line" in text
    assert "## Your default style: Style 1" in text
    assert not re.search(r"^\s*\d+[.)]\s", text, re.M), "The pipeline must not be duplicated"
    assert not re.search(r"captions.*grade", text, re.I | re.S), "Captions must not precede grade"
    assert "Standing notes:" not in text and "Could not be matched:" in text
    assert len(text.split()) < 600 and b"\r" not in raw
    write(reel / "grade.json", {"look": {"id": "mono", "strength": 1.0}})
    assert run("save-from-reel", reel, "--name", "default").returncode == 0
    assert skill.read_bytes() != raw and "Grade look: Mono at 100 %" in skill.read_text()
    handmade = b"My hand-made skill\n"
    skill.write_bytes(handmade)
    result = run("save-from-reel", reel, "--name", "default")
    assert result.returncode == 0, result.stderr
    assert skill.read_bytes() == handmade
    candidate = skill.with_name("SKILL.new.md")
    assert candidate.is_file() and "separate" in result.stdout.lower()
    assert run("save-from-reel", reel, "--name", "default").returncode == 0
    candidate.write_bytes(handmade)
    before = ss.path().read_bytes()
    assert run("save-from-reel", reel, "--name", "default").returncode == 2
    assert candidate.read_bytes() == handmade and ss.path().read_bytes() == before
    other = root / "explicit workspace"
    assert run("save-from-reel", reel, "--name", "default", "--workspace", other).returncode == 0
    assert (other / ".claude/skills/my-editing-style/SKILL.md").is_file()


def case_longnotes(root):
    workspace, reel, _ = fixture(root)
    ss.save({"standing_notes": [{"id": "n1", "note": "Keep it warm " * 220, "status": "unmatched"}]})
    before = ss.path().read_bytes()
    result = run("save-from-reel", reel, "--name", "default")
    assert result.returncode == 2 and "too long" in result.stderr
    assert ss.path().read_bytes() == before
    assert not (workspace / ".claude/skills/my-editing-style/SKILL.md").exists()


def case_hub(root):
    rows = (SKILLS / "editor-doctor/references/hub.md").read_text(encoding="utf-8").splitlines()
    row = next(line for line in rows if line.startswith("| `style` |"))
    assert "save-from-reel" in row
    assert "Save these choices as a new style?" in row
    assert "--name" not in row and "same line" in row
    row = next(line for line in rows if line.startswith("| `styles` |"))
    assert "rename <choices.id> <choices.label>" in row and "set-default <choices.id>" in row
    assert "one plain line" in row and "refresh with both scripts above" in row


def case_doctor(root):
    doctor = (SKILLS / "editor-doctor/SKILL.md").read_text(encoding="utf-8")
    line = next(line for line in doctor.splitlines() if "--set-nle resolve" in line)
    assert "`--set-nle resolve` (Resolve Studio, imported through its own connector)" in line
    assert "`--set-nle mcp` (another editor: files only)" in line
    details = (SKILLS / "editor-doctor/references/doctor-details.md").read_text(encoding="utf-8")
    assert "(`mcp` = files for another editor)" in details


def case_set(root):
    _, reel, _ = fixture(root)
    result = run("set", "caption_style", "null", "--style", "default")
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.splitlines()) == 1 and "none saved" in result.stdout
    ss.save({"font": "Inter", "caption_style": {"style": "clean"}})
    before = ss.load(name="default")
    result = run("set", "caption_style", '{"style":"boxed"}', "--style", "Style 1")
    assert result.returncode == 0, result.stderr
    assert ss.load(name="default") == {**before, "caption_style": {"style": "boxed"}}
    assert ss.path("default@v1").is_file()
    assert len(result.stdout.splitlines()) == 1 and "Style 1" in result.stdout
    raw = ss.path().read_bytes()
    result = run("set", "caption_style", '{"style":"clean"}', "--style", "bold")  # an unknown name never makes a new style
    assert result.returncode == 2 and "not found" in result.stderr and ss.path().read_bytes() == raw
    for key, value in (("nope", "1"), ("caption_style.style", "5"), ("caption_style", "{")):
        raw = ss.path().read_bytes()
        result = run("set", key, value, "--style", "default")
        assert result.returncode == 2 and "Traceback" not in result.stderr
        assert len(result.stderr.splitlines()) == 1
        assert ss.path().read_bytes() == raw
    assert run("save-from-reel", reel).returncode == 0
    assert run("pick", reel, "style-2").returncode == 0
    raw = ss.path("default").read_bytes()
    result = run("set", "caption_style", '{"style":"bold-pop"}', "--reel", reel)
    assert result.returncode == 0, result.stderr
    assert ss.load(name="style-2")["caption_style"] == {"style": "bold-pop"}
    assert ss.path("default").read_bytes() == raw
    assert run("set", "edit_style.moves.push.to", "1.08", "--reel", reel).returncode == 0
    assert ss.load(name="style-2")["edit_style"]["moves"]["push"]["to"] == 1.08

    # Returning to an earlier reel must not edit the last-picked reel's style.
    other = reel.with_name("reel-3")
    other.mkdir()
    assert run("pick", reel, "Style 1").returncode == 0
    assert run("pick", other, "Style 2").returncode == 0
    raw = ss.path("style-2").read_bytes()
    result = run("set", "caption_style", '{"style":"karaoke"}', "--reel", reel)
    assert result.returncode == 0, result.stderr
    assert ss.load(name="default")["caption_style"] == {"style": "karaoke"}
    assert ss.path("style-2").read_bytes() == raw
    assert result.stdout.splitlines() == ["Updated Style 1."]
    # Normal mode retains this reel's saved style; it does not borrow the cursor.
    assert run("pick", reel, "normal").returncode == 0
    assert run("pick", other, "Style 2").returncode == 0
    assert run("set", "caption_style.line_breaks", "false", "--reel", reel).returncode == 0
    assert ss.load(name="default")["caption_style"]["line_breaks"] is False
    assert ss.path("style-2").read_bytes() == raw

    # Even with Style 2 as default, a reel without a saved pick cannot write.
    assert run("set-default", "Style 2").returncode == 0
    for choice in ("unpicked", "fresh", "copy", "normal"):
        target = reel.with_name("reel-" + choice)
        target.mkdir()
        if choice != "unpicked":
            result = run("pick", target, choice)
            assert result.returncode == (2 if choice == "normal" else 0), result.stderr
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = run("set", "caption_style", '{"style":"clean"}', "--reel", target)
        assert result.returncode == 2 and result.stdout == "", result
        assert result.stderr.splitlines() == [
            "This reel has no saved style picked; pick one first, then try again."]
        assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    # Explicit management stays available while the cursor points to a fresh reel.
    assert run("pick", reel, "fresh").returncode == 0
    assert run("set", "caption_style.style", '"outline-caps"', "--style", "Style 2").returncode == 0
    assert ss.load(name="style-2")["caption_style"]["style"] == "outline-caps"
    for target_args in ((), ("--reel", reel, "--style", "Style 2")):
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = run("set", "caption_style", '{"style":"clean"}', *target_args)
        assert result.returncode == 2 and not result.stdout and len(result.stderr.splitlines()) == 1
        assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def case_refresh(root):
    workspace, reel, _ = fixture(root)
    skill = workspace / ".claude/skills/my-editing-style/SKILL.md"
    for _ in range(2):
        result = run("save-from-reel", reel)
        assert result.returncode == 0, result.stderr
    assert "## Your default style: Style 1" in skill.read_text(encoding="utf-8")
    for args, label in ((("rename", "Style 1", "Bold"), "Bold"),
                        (("set-default", "Style 2"), "Style 2"),
                        (("delete", "Style 2"), "Bold")):
        result = run(*args, "--workspace", workspace)
        assert result.returncode == 0, result.stderr
        assert f"## Your default style: {label}" in skill.read_text(encoding="utf-8")
    handmade = b"My hand-made skill\n"
    skill.write_bytes(handmade)
    result = run("rename", "Bold", "Warm", "--workspace", workspace)
    assert result.returncode == 0, result.stderr
    assert skill.read_bytes() == handmade
    candidate = skill.with_name("SKILL.new.md")
    assert "## Your default style: Warm" in candidate.read_text(encoding="utf-8")
    candidate.write_bytes(handmade)
    result = run("rename", "Warm", "Soft", "--workspace", workspace)
    assert result.returncode == 0 and not result.stderr
    assert len(result.stdout.splitlines()) == 2 and "refresh" in result.stdout.lower()
    assert ss.styles()[0]["label"] == "Soft"
    assert skill.read_bytes() == candidate.read_bytes() == handmade
    other = root / "no skill"
    assert run("set-default", "Soft", "--workspace", other).returncode == 0
    assert not (other / ".claude").exists()
    candidate.unlink()
    skill.write_bytes((ss.SKILL_MARKER + "\n").encode("utf-8"))
    assert run("delete", "Soft", "--workspace", workspace).returncode == 0
    assert "## Your default style: none saved" in skill.read_text(encoding="utf-8")


CASES = {"fromreel": case_fromreel, "keep": case_keep, "named": case_named,
         "decoded": case_decoded, "decoded_apply": case_decoded_apply,
         "decoded_siblings": case_decoded_siblings, "decoded_empty": case_decoded_empty,
         "decoded_old": case_decoded_old, "decoded_types": case_decoded_types,
         "decoded_contract": case_decoded_contract, "skill": case_skill, "longnotes": case_longnotes, "hub": case_hub,
         "doctor": case_doctor, "set": case_set, "refresh": case_refresh}


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
