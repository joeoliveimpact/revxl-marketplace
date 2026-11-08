"""Named styles and one pick per reel: <scratch> [--case NAME]."""
import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from save_style_test import SKILLS, fixture, run, ss, write
from editor_test_state import copy_tool_state

SKELETON = ('{"schema":1,"style_id":null,"accent":null,"font":null,"look":null,'
            '"transitions":{"allowed":[],"sfx_pair":null},"edit_style":null,'
            '"caption_style":null,"cut":{"default_attempt":null}}')
OPTIONS = ["Which style for this reel?", "- Copy a reel I like", "- Start fresh"]


def snapshot():
    return {p.name: p.read_bytes() for p in ss.path("default").parent.iterdir()}


def ok(*args):
    result = run(*args)
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    return result.stdout.splitlines()


def refused(*args):
    before = snapshot()
    result = run(*args)
    assert result.returncode == 2 and not result.stdout, (result.stdout, result.stderr)
    assert len(result.stderr.splitlines()) == 1 and "Traceback" not in result.stderr
    assert snapshot() == before
    return result.stderr.strip()


def saves(root, count=2):
    workspace, reel, _ = fixture(root)
    for number in range(1, count + 1):
        write(reel / "grade.json", {"look": {"id": "warm", "strength": number / 10}})
        lines = ok("save-from-reel", reel)
        assert lines[-1] == f"Saved as Style {number}. Want a different name for it?"
    return workspace, reel


def case_two_saves(root):
    # A new style must not inherit unrelated preferences or remembered picks.
    write(ss.path("default"), {"schema": 1, "picks": {"font": {"value": "Inter", "note": "", "at": "now"}}})
    _, reel = saves(root)
    assert ss.styles() == [dict(id="style-1", label="Style 1", default=True),
                           dict(id="style-2", label="Style 2", default=False)]
    assert ss.load(name="style-1")["look"]["strength"] == 0.1
    assert ss.load(name="style-2")["look"]["strength"] == 0.2
    for name in ("style-1", "style-2"):
        data = ss.load(name=name)
        assert "label" not in data and "picks" not in data and "font" not in data
    assert ok("show") == ss.readback(ss.load(name=ss.active_name()))
    assert ok("picker", reel)[-2:] == OPTIONS[-2:]


def case_rename(root):
    _, reel = saves(root)
    before = ss.path("style-2").read_bytes()
    assert ok("rename", "style-2", " Talking head ") == ["Renamed to Talking head."]
    assert "- Talking head" in ok("picker", reel)
    assert "- Style 2" not in ok("picker", reel)
    assert ss.path("style-2").read_bytes() == before
    assert ok("set-default", "talking head") == ["Talking head is now your default."]
    assert next(row for row in ss.styles() if row["id"] == "style-2")["default"]
    assert ok("show", "TALKING HEAD") == ss.readback(ss.load(name="style-2"))
    assert ok("pick", reel, "talking head") == ["This reel uses Talking head."]
    assert ss.pick_for(reel)["style"] == "style-2"
    assert ok("save-from-reel", reel, "--name", "talking head")[-1] == "Updated Talking head."
    assert ss.path("style-2").read_bytes() == before
    assert ok("rename", "TALKING HEAD", "Talking head") == ["Renamed to Talking head."]
    for label in ("sTyLe 1", "", "  ", "x" * 41, "one\ntwo"):
        refused("rename", "style-2", label)
    refused("rename", "missing", "New name")
    refused("rename", "_index", "New name")
    refused("show", "No such style")
    refused("save-from-reel", reel, "--name", "No such style")
    assert ok("delete", "talking head") == ["Talking head is archived; you can restore it any time.",
                                            "Style 1 is now your default."]


def case_default_marked(root):
    _, reel = saves(root)
    lines = ok("picker", reel)
    assert lines[1] == "- Style 1 (your default, recommended)"
    assert sum("(your default, recommended)" in line for line in lines) == 1
    assert ok("set-default", "style-2") == ["Style 2 is now your default."]
    lines = ok("picker", reel)
    assert lines[1] == "- Style 2 (your default, recommended)" and "- Style 1" in lines
    assert sum("(your default, recommended)" in line for line in lines) == 1
    assert [s["id"] for s in ss.styles()] == ["style-1", "style-2"], "Changing the default changed creation order"
    refused("set-default", "missing")


def case_migrate(root):
    data = {"schema": 1, "font": "Inter", "look": {"id": "warm", "strength": 0.6}}
    write(ss.path("default"), data)
    ss.path("default@v1").write_bytes(b'{"font":"Old font"}\n')
    before = snapshot()
    assert ok("list") == [f"Style 1 (default): {ss.readback(data)[0]} (1 archived versions)"]
    assert ok("show") == ss.readback(data) and ss.load(name="default") == data
    assert ss.load(root / "unpicked") == {}
    assert ss.styles() == [dict(id="default", label="Style 1", default=True)]
    assert snapshot() == before, "Migration wrote files during a read"
    ss.path("default").write_bytes((SKELETON + "\n").encode("utf-8"))
    before = snapshot()
    assert ss.styles() == [] and ok("list") == [] and snapshot() == before
    picks = {"caption_style.style": {"value": "boxed", "note": "Keep it framed", "at": "now"}}
    write(ss.path("default"), {"schema": 1, "picks": picks})
    before = snapshot()
    assert ss.styles() == [] and ss.load(name="default")["picks"] == picks and snapshot() == before
    # Blank nested objects stay blank; 0 and False are real choices.
    assert not ss._has_choices({"transitions": {"allowed": [], "nested": {"empty": None}}})
    assert ss._has_choices({"caption_style": {"line_breaks": False}})
    assert ss._has_choices({"look": {"strength": 0}})
    write(ss.path("client-b"), {"font": "B"})
    write(ss.path("client-a"), {"font": "A"})
    os.utime(ss.path("client-b"), (100, 100))
    os.utime(ss.path("client-a"), (200, 200))
    assert ss.styles() == [dict(id="client-b", label="Client b", default=True),
                           dict(id="client-a", label="Client a", default=False)]
    assert not ss.path("default").with_name("_index.json").exists()
    ss.rename("client-b", "Oldest")
    assert ss.path("default").with_name("_index.json").is_file()


def case_delete_default(root):
    _, reel = saves(root, 3)
    before = ss.path("style-1").read_bytes()
    ok("pick", reel, "style-1")
    assert ok("delete", "style-1") == ["Style 1 is archived; you can restore it any time.",
                                        "Style 3 is now your default."]
    assert not ss.path("style-1").exists() and ss.path("style-1@v1").read_bytes() == before
    assert ss.pick_for(reel) is None
    assert not any(line.startswith("- Style 1") for line in ok("picker", reel))
    assert ss.styles()[-1] == dict(id="style-3", label="Style 3", default=True)
    refused("delete", "style-1")
    ok("restore", "style-1@v1")
    assert ss.styles()[0] == dict(id="style-1", label="Style 1", default=False)
    assert ss.path("style-1").read_bytes() == before and ss.path("style-1@v1").read_bytes() == before
    # Both a renamed label and an existing archive reserve the next free number.
    ok("rename", "style-2", "Talking head")
    ok("delete", "style-2")
    assert ok("save-from-reel", reel)[-1] == "Saved as Style 4. Want a different name for it?"
    ok("restore", "style-2@v1")
    assert ss.styles()[1]["label"] == "Talking head"


def case_picker_options(root):
    reel = root / "reel"
    assert ok("picker", reel) == OPTIONS
    write(ss.path("default"), json.loads(SKELETON))
    assert ok("picker", reel) == OPTIONS
    _, reel = saves(root)
    assert ok("picker", reel)[-2:] == OPTIONS[-2:]


def case_siblings(root):
    _, reel = saves(root, 1)
    folder = ss.path("style-1").parent
    payloads = {"intake": b'{"answers":["Keep the laugh"]}\n', "learn": b'{"approved":3}\n'}
    for kind, raw in payloads.items():
        (folder / f"style-1.{kind}.json").write_bytes(raw)
    blocker = folder / "style-1@v1.intake.json"
    blocker.write_bytes(b'{"older":"keep this too"}\n')
    # A later refusal must roll back the archive, sibling moves and style removal too.
    before = snapshot()
    with patch.object(ss, "_write_index", side_effect=ValueError("Could not save the style names.")):
        try:
            ss.delete("style-1")
        except ValueError as error:
            assert str(error) == "Could not save the style names."
        else:
            raise AssertionError("The planted refusal was ignored")
    assert snapshot() == before
    ok("delete", "style-1")
    assert not ss.path("style-1").exists() and not list(folder.glob("style-1.*.json"))
    for kind, raw in payloads.items():
        assert (folder / f"style-1@v2.{kind}.json").read_bytes() == raw
    assert blocker.read_bytes() == b'{"older":"keep this too"}\n'
    assert ok("list") == ["Archived: Style 1 (restore with style-1@v2)"] and ok("picker", reel) == OPTIONS
    ok("restore", "style-1@v2")
    for kind, raw in payloads.items():
        assert (folder / f"style-1.{kind}.json").read_bytes() == raw
        assert (folder / f"style-1@v2.{kind}.json").read_bytes() == raw
    assert len(ok("list")) == 1 and len(ss.styles()) == 1
    assert ok("picker", reel).count("- Style 1 (your default, recommended)") == 1
    # Restoring over a current style archives its siblings at the same new version.
    changed = {kind: b'{"newer":"' + kind.encode() + b'"}\n' for kind in payloads}
    for kind, raw in changed.items():
        (folder / f"style-1.{kind}.json").write_bytes(raw)
    current = ss.path("style-1").read_bytes()
    ok("restore", "style-1@v2")
    assert ss.path("style-1@v3").read_bytes() == current
    for kind, raw in payloads.items():
        assert (folder / f"style-1.{kind}.json").read_bytes() == raw
        assert (folder / f"style-1@v3.{kind}.json").read_bytes() == changed[kind]
    assert blocker.read_bytes() == b'{"older":"keep this too"}\n'
    # Unarchived siblings do not reserve a number; archived siblings do.
    (folder / "_index.json").unlink()
    (folder / "style-2.intake.json").write_bytes(b'{"font":"Not a style"}\n')
    assert ss.styles() == [dict(id="style-1", label="Style 1", default=True)]
    assert ss._next_style(ss._index()) == ("style-2", "Style 2")
    (folder / "style-2@v1.learn.json").write_bytes(b'{"font":"Not an archive"}\n')
    assert ss._next_style(ss._index()) == ("style-3", "Style 3")
    assert len(ok("list")) == 1
    for name in ("style-1.intake", "style-1@v1.learn"):
        try:
            ss.path(name)
        except ValueError:
            pass
        else:
            raise AssertionError("A sibling was accepted as a style path")


def case_pick(root):
    _, reel = saves(root)
    picks = {"caption_style.style": {"value": "boxed", "note": "Frame it", "at": "now"}}
    write(ss.path("default"), {"schema": 1, "picks": picks})
    assert ok("pick", reel, "style-2") == ["This reel uses Style 2."]
    data = ss.load(name="style-2")
    assert ss.load(reel) == {**data, "picks": picks} and ss.path() == ss.path("style-2")
    assert "picks" not in ss.load(reel, for_write=True) and "picks" not in ss.load(name="style-2")
    assert ok("picker", reel / "../reel-1") == ["This reel uses Style 2."]
    assert ok("pick", reel, "fresh") == ["This reel starts fresh: I'll ask about each choice."]
    assert ss.load(reel) == {"picks": picks} and ss.path() == ss.path("default")
    assert ss.active_name() == "default"
    assert ok("picker", reel) == ["This reel starts fresh."]
    assert ok("picker", root / "other")[0] == OPTIONS[0]
    refused("pick", reel, "missing")
    assert ok("pick", reel, "copy") == ["Send me the reel you like. I'll measure its style, save it as a new style and use it on this reel."]
    assert ok("picker", reel) == ["This reel copies a reel you like."]
    ss.path("default").unlink()
    assert ss.load(name="default") == {} and ss.path() == ss.path("default")
    # Standing notes follow the active saved style; automatic picks still go to default.
    import standing_notes
    ok("pick", reel, "style-2")
    assert standing_notes.main(["add", "Keep this for Style 2", "--unmatched"]) == 0
    assert "standing_notes" in ss.load(name="style-2") and not ss.path("default").exists()
    standing_notes.record_pick("caption_style.style", "boxed")
    assert ss.load(name="default")["picks"]["caption_style.style"]["value"] == "boxed"
    assert "picks" not in ss.load(name="style-2")


def case_skill_text(root):
    workspace, _ = saves(root, 1)
    raw = (workspace / ".claude/skills/my-editing-style/SKILL.md").read_bytes()
    text = raw.decode("utf-8")
    assert 'one question, "Which style for this reel?"' in text
    assert '"Copy a reel I like" and "Start fresh"' in text
    assert "default as the recommended pick" in text
    assert "A saved style applies only to the reel it was picked for; a new reel gets the style picker." in text
    assert "In normal mode" in text and "including its Auto edit line" in text
    assert "## Your default style: Style 1" in text and ss.SKILL_MARKER in text.splitlines()
    assert "${CLAUDE_PLUGIN_ROOT}" not in text and b"\r" not in raw and len(text.split()) < 600
    assert "Holds the client's saved editing choices and standing notes for editor-superengine." in text
    assert "Invoke editor-superengine:editor-start-here first; it runs the style picker." in text
    assert "Then run the edit in its pipeline order, invoking each skill it names;" in text
    assert "the references/qa-check.md of editor-superengine:reel-canvas-build." in text
    assert "on this computer" not in text


def case_unreadable_index(root):
    _, reel = saves(root)
    index = ss.path("default").with_name("_index.json")
    for raw in (b"{", b"[]", b"null", b"\xff", b'{"schema":1,"styles":[],"archived":{}}'):
        index.write_bytes(raw)
        ss._index_noted.clear()
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            assert ss.styles() == [] and ss.styles() == []
        assert output.getvalue().splitlines() == [ss.INDEX_NOTE]
        for args in (("rename", "style-1", "New"), ("set-default", "style-1"), ("delete", "style-1"),
                     ("pick", reel, "fresh"), ("save-from-reel", reel), ("restore", "style-1@v1")):
            assert refused(*args) == ss.INDEX_WRITE_NOTE
        before = snapshot()
        try:
            ss.save({"font": "New"})
        except ss.UnreadableStyleError as error:
            assert str(error) == ss.INDEX_WRITE_NOTE
        else:
            raise AssertionError("Overwrote an unreadable index")
        assert snapshot() == before


def case_blank_save(root):
    workspace = root / "workspace"
    reel = workspace / "videos/blank"
    reel.mkdir(parents=True)
    write(workspace / "editor/editor.config.json", {})
    ss.path("default").parent.mkdir(parents=True, exist_ok=True)
    before = snapshot()
    assert refused("save-from-reel", reel) == "This reel has no choices to save yet. Send a board first."
    assert snapshot() == before and not (workspace / ".claude").exists()
    write(reel / "sound-selection.json", {"bed": {"gain_db": -16}})
    assert ok("save-from-reel", reel)[-1] == "Saved as Style 1. Want a different name for it?"
    assert ss.load(name="style-1")["music"]["bed_gain_db"] == -16
    assert "Music level: -16 dB" in ok("show", "Style 1")


def case_missing_delete(root):
    _, reel = saves(root, 1)
    ss.path("style-1").unlink()
    sibling = ss.path("style-1").with_suffix(".learn.json")
    sibling.write_bytes(b'{"auto":{"on":true}}\n')
    assert ok("delete", "style-1") == ["Style 1 was already gone; I removed it from your list."]
    assert not sibling.exists()
    assert ss.path("style-1@v1").with_suffix(".learn.json").read_bytes() == b'{"auto":{"on":true}}\n'
    assert not ss.path("style-1@v1").exists()
    assert ss.styles() == [] and ok("list") == [] and ok("picker", reel) == OPTIONS


def case_missing_delete_reuse(root):
    import style_learn
    for action in ("delete", "restore"):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / action / "state")}):
            saves(root / action, 1)
            original = ss.path("style-1").read_bytes()
            created = ss._index()["styles"]["style-1"]["created"]
            ss.path("style-1").unlink()
            learning = ss.path("style-1").with_suffix(".learn.json")
            learning.write_bytes(b'{"old":"keep this"}\n')
            ok("delete", "style-1")
            old_learning = ss.path("style-1@v1").with_suffix(".learn.json")
            assert not ss.path("style-1@v1").exists()
            ss.save({"font": "New font"}, "style-1")
            assert ss._index()["styles"]["style-1"]["created"] == created
            style_learn.decline("style-1")
            current, fresh = ss.path("style-1").read_bytes(), learning.read_bytes()
            if action == "restore":
                ss.path("style-1@v3").write_bytes(original)
                ok("restore", "style-1@v3")
                assert ss.path("style-1").read_bytes() == original
                assert ss.path("style-1@v3").read_bytes() == original
            else:
                ok("delete", "style-1")
                assert not ss.path("style-1").exists() and not learning.exists()
            assert old_learning.read_bytes() == b'{"old":"keep this"}\n'
            assert ss.path("style-1@v2").read_bytes() == current
            assert ss.path("style-1@v2").with_suffix(".learn.json").read_bytes() == fresh


def case_delete_picks(root):
    picks = {"caption_style.style": {"value": "boxed", "note": "Frame it", "at": "now"}}
    data = {"schema": 1, "font": "Inter", "picks": picks}
    write(ss.path("default"), data)
    original = ss.path("default").read_bytes()
    assert ok("delete", "Style 1") == ["Style 1 is archived; you can restore it any time."]
    assert ss.path("default@v1").read_bytes() == original
    assert ss.load(name="default") == {"schema": 1, "picks": picks}
    assert ss.styles() == [] and ss.load(name="default")["picks"] == picks
    assert ok("list") == ["Archived: Style 1 (restore with default@v1)"]


def case_archived_list(root):
    saves(root, 1)
    for i in range(11):
        ss.save({"font": f"Font {i}"}, "style-1", archive=True)
    ok("delete", "style-1")
    assert ok("list") == ["Archived: Style 1 (restore with style-1@v12)"]
    ok("restore", "style-1@v12")
    assert len(ok("list")) == 1 and not ok("list")[0].startswith("Archived:")


def case_per_reel(root):
    _, reel1 = saves(root)
    reel2 = reel1.with_name("reel-2")
    reel2.mkdir()
    assert ss.load(reel2) == {}, "An unpicked reel inherited the default"
    ok("pick", reel1, "style-2")
    assert ss.load() == {}, "An unscoped reader used the management cursor"
    assert ss.load(reel1)["look"]["strength"] == 0.2
    assert ss.load(str(reel2)) == {}, "Another reel's pick leaked"
    assert ok("picker", reel2)[0] == OPTIONS[0]
    assert not any("This reel uses" in line for line in ok("picker", reel2))
    ok("pick", reel2, "fresh")
    assert ss.load(reel2) == {}, "A no-style pick inherited the default"
    assert ok("picker", reel1) == ["This reel uses Style 2."]
    assert ss.load(reel1)["look"]["strength"] == 0.2
    ok("pick", reel2, "style-1")
    assert ss.load(reel2)["look"]["strength"] == 0.1
    assert ss.load(reel1)["look"]["strength"] == 0.2
    ok("delete", "style-2")
    assert ss.load(reel1) == {} and ss.load(reel2)["look"]["strength"] == 0.1


def case_legacy_current(root):
    _, reel1 = saves(root, 1)
    reel2 = reel1.with_name("reel-2")
    index = ss._index()
    index.pop("picks", None)
    index.pop("active_reel", None)
    index["current"] = {"reel": str(reel1.resolve()), "style": "style-1", "how": "saved", "at": "now"}
    target = ss.path("default").with_name("_index.json")
    write(target, index)
    before = target.read_bytes()
    assert ss.load(reel1)["look"]["strength"] == 0.1
    assert ss.load(reel2) == {} and ok("picker", reel2)[0] == OPTIONS[0]
    assert target.read_bytes() == before, "Reading legacy state wrote it"
    index["current"] = {"reel": str(reel1.resolve()), "style": "style-1"}
    write(target, index)
    before = target.read_bytes()
    assert ss.load(reel1)["look"]["strength"] == 0.1 and ss.load(reel2) == {}
    assert target.read_bytes() == before, "Reading a minimal legacy pick wrote it"
    assert ok("picker", reel1) == ["This reel uses Style 1."]
    ok("pick", reel2, "fresh")
    assert ss.load(reel1)["look"]["strength"] == 0.1 and ss.load(reel2) == {}
    assert "current" not in json.loads(target.read_text(encoding="utf-8"))
    index.pop("picks", None)
    index.pop("active_reel", None)
    index["current"] = {"reel": str(reel1.resolve()), "style": None, "how": "fresh", "at": "now"}
    write(target, index)
    assert ss.load(reel1) == {} and ss.load(reel2) == {}
    assert ok("picker", reel1) == ["This reel starts fresh."]
    assert ok("picker", reel2)[0] == OPTIONS[0]


def case_reader_reels(root):
    from saved_style_test import module
    first, second = root / "first", root / "second"
    first.mkdir()
    second.mkdir()
    choices = {"edit_style": {"style": "punch-in"}, "caption_style": {"style": "boxed"},
               "accent": "#123ABC", "font": "Missing Brand", "look": {"id": "warm", "strength": 0.4},
               "cut": {"default_attempt": "first", "pause_ms": 80},
               "transitions": {"allowed": [], "sfx_pair": True}}
    ss.save(choices, "chosen")
    ss.pick(first, "chosen")
    editing = module("reel-canvas-build", "styles")
    compose = module("reel-canvas-build", "compose")
    captions = module("reel-captions", "captions")
    board = module("reel-first-cuts", "make_board")
    grade = module("reel-grade", "bake_grade")
    transitions = module("reel-canvas-build", "transitions")
    trials = module("reel-trials", "trials")
    assert editing.pick_style({}, reel=first, remember=False) == (choices["edit_style"], "saved")
    assert captions.pick_style(first, {}, remember=False) == (choices["caption_style"], "saved")
    assert compose.saved_brand(first) == {"accent": "#123ABC", "font": "Missing Brand"}
    assert captions.check_style({"style": "clean"}, reel=first)["accent"] == "#123ABC"
    assert board.default_attempt(first) == "first" and board.pause_default(first) == 80
    assert grade.resolve_look(first) == choices["look"] and trials.current_look(first) == "warm"
    for reader, call in [(editing, lambda: editing.pick_style({}, reel=second, remember=False)),
                         (captions, lambda: captions.pick_style(second, {}, remember=False))]:
        try:
            call()
        except reader.Stop as error:
            assert error.code == 1 and error.lines[0].startswith("ask:")
        else:
            raise AssertionError("An unpicked reel inherited a style")
    assert compose.saved_brand(second) == {}
    assert captions.check_style({"style": "clean"}, reel=second)["accent"] == "#FFD84D"
    assert board.default_attempt(second) == "last" and board.pause_default(second) == 150
    assert grade.resolve_look(second) == {"id": "none"} and trials.current_look(second) == "none"
    for reel, expected in [(first, True), (second, False)]:
        transitions.plan({"reel_dir": reel, "beats": [], "cut_frames": [], "rate": 30, "bm": {}})
        assert (reel / "work/transition_cues.json").exists() == expected
    ss.pick(second, "fresh")
    assert ss.load(first)["accent"] == "#123ABC" and compose.saved_brand(second) == {}


CASES = {"two-saves": case_two_saves, "rename": case_rename, "default-marked": case_default_marked,
         "migrate": case_migrate, "delete-default": case_delete_default, "picker-options": case_picker_options,
         "pick": case_pick, "skill-text": case_skill_text, "unreadable-index": case_unreadable_index,
         "siblings": case_siblings, "blank-save": case_blank_save, "missing-delete": case_missing_delete,
         "missing-delete-reuse": case_missing_delete_reuse,
         "delete-picks": case_delete_picks, "archived-list": case_archived_list,
         "per-reel": case_per_reel, "legacy-current": case_legacy_current, "reader-reels": case_reader_reels}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    source = ss.runtime.state_dir()
    failures = 0
    with tempfile.TemporaryDirectory(prefix="style-picker-", dir=scratch) as tmp:
        for name in [args.case] if args.case else CASES:
            root = Path(tmp) / name
            root.mkdir()
            copy_tool_state(source, root / "state")
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
