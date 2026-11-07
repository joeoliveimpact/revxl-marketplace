"""Remembered-pick contract: <scratch-dir> [--case NAME]; own scratch state only."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SKILLS = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills"
sys.path.insert(0, str(SKILLS / "_shared"))
import saved_style as ss
SOURCE_HOME = ss.runtime.state_dir()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cli(script, *args, code=0):
    result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SKILLS / "_shared" / script),
                             *map(str, args)], capture_output=True, encoding="utf-8")
    assert result.returncode == code, (result.returncode, result.stdout, result.stderr)
    return result.stdout + result.stderr


def pick(key="caption_style.style", value="bold-pop", note="Keep my words bright", style="default"):
    cli("standing_notes.py", "pick", key, "--value", json.dumps(value), "--note", note, "--style", style)


def put(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, ensure_ascii=False) + "\n").encode("utf-8"))


def readers():
    return (module(SKILLS / "reel-captions/scripts/captions.py", "captions"),
            module(SKILLS / "reel-canvas-build/scripts/styles.py", "styles"))


def reel(root):
    folder = root / "videos/next"
    put(root / "editor/editor.config.json", {})
    put(folder / "beat-map-selection.json", {"beats": [], "word_marks": []})
    put(folder / "work/edit_map.cut.json", {"words": [
        {"word": "Our", "start": 0, "end": 0.2}, {"word": "words.", "start": 0.3, "end": 0.6}]})
    put(folder / "work/cuts.json", {"fps": 30, "segments": [{"out_in_f": 0, "out_out_f": 60}]})
    return folder


def case_verbatim(root):
    note = '  My "caf\u00e9" \u2014 \u9ec4\u8272 \U0001f49b\nKeep these words.  '
    pick(note=note)
    data = ss.load()
    record = data["picks"]["caption_style.style"]
    assert record["note"].encode("utf-8") == note.encode("utf-8")
    assert record["value"] == "bold-pop" and record["at"]
    assert "caption_style" not in data and "standing_notes" not in data
    output = cli("standing_notes.py", "picks")
    assert 'Last time you picked Bold pop for captions - your words: "' + note + '"' in output
    assert note in "\n".join(ss.readback(data))
    pick(value="boxed", style="client-b")
    assert ss.load()["picks"]["caption_style.style"]["value"] == "bold-pop"
    assert ss.load("client-b")["picks"]["caption_style.style"]["value"] == "boxed"
    before = ss.path().read_bytes()
    for key, value in (("caption_style.style", "invented"), ("caption_style", {"style": "invented"}),
                       ("font", 123), ("language", "en")):
        output = cli("standing_notes.py", "pick", key, "--value", json.dumps(value), "--note", "bad", code=2)
        assert "Traceback" not in output and len(output.splitlines()) == 1
        assert ss.path().read_bytes() == before


def case_recommended(root):
    folder = reel(root)
    pick()
    pick("edit_style.style", "layout-switch", "Let the layout do it")
    assert ss.resolve("caption_style.style", saved=ss.load()) == ("bold-pop", "recommended")
    assert ss.resolve("edit_style.style", saved=ss.load()) == ("layout-switch", "recommended")
    cap, styles = readers()
    for reader, callback, label, note in (
            (cap, lambda: cap.pick_style(folder), "Bold pop", "Keep my words bright"),
            (styles, lambda: styles.pick_style({}), "Layout switch", "Let the layout do it")):
        try:
            callback()
        except reader.Stop as error:
            assert error.code == 1 and error.lines[0].startswith("ask:"), error.lines
            assert ". Last time you picked " + label in error.lines[0] and '"' + note + '"' in error.lines[0]
        else:
            raise AssertionError("A remembered pick must still ask")
    assert cap.main(["plan", "--reel-dir", str(folder)]) == 1
    assert not (folder / "work/captions.json").exists()
    # Parent choices also recommend their child value, without setting it.
    ss.save({})
    pick("caption_style", {"style": "boxed"}, "Keep it framed")
    assert ss.resolve("caption_style.style", saved=ss.load()) == ("boxed", "recommended")


def case_saved_wins(root):
    folder = reel(root)
    pick()
    pick("edit_style.style", "layout-switch", "Let the layout do it")
    data = ss.load()
    data.update(caption_style={"style": "clean"}, edit_style={"style": "punch-in"})
    ss.save(data)
    cap, styles = readers()
    assert ss.resolve("caption_style.style", saved=ss.load()) == ("clean", "saved")
    assert cap.pick_style(folder) == ({"style": "clean"}, "saved")
    assert styles.pick_style({}) == ({"style": "punch-in"}, "saved")
    cli("standing_notes.py", "add", "Always boxed", "--key", "caption_style.style", "--value", '"boxed"')
    assert cap.pick_style(folder) == ({"style": "boxed"}, "saved")
    assert ss.resolve("caption_style.style", reel={"caption_style": {"style": "none"}},
                      saved=ss.load()) == ("none", "reel")


def case_archive(root):
    folder = reel(root)
    ss.save({"caption_style": {"style": "clean"}, "font": "Inter"})
    original = ss.path().read_bytes()
    put(folder / "beat-map-selection.json", {"caption_style": {"style": "boxed"}})
    cli("saved_style.py", "save-from-reel", folder)
    second = ss.path().read_bytes()
    put(folder / "beat-map-selection.json", {"caption_style": {"style": "bold-pop"}})
    cli("saved_style.py", "save-from-reel", folder)
    current = ss.path().read_bytes()
    assert ss.path("default@v1").read_bytes() == original
    assert ss.path("default@v2").read_bytes() == second
    listed = cli("saved_style.py", "list")
    assert len(listed.splitlines()) == 1 and "2 archived versions" in listed
    assert "@v" not in listed
    assert "Caption look: Clean" in cli("saved_style.py", "show", "default@v1")
    cli("saved_style.py", "save-from-reel", folder)
    assert not ss.path("default@v3").exists(), "Unchanged re-save created an archive"
    cli("saved_style.py", "restore", "default@v1")
    assert ss.load()["caption_style"]["style"] == "clean"
    assert ss.path("default@v3").read_bytes() == current
    assert ss.path("default@v1").read_bytes() == original
    # Restore always keeps the current file, even when restoring the same contents again.
    restored = ss.path().read_bytes()
    cli("saved_style.py", "restore", "default@v1")
    assert ss.path("default@v4").read_bytes() == restored
    before = ss.path().read_bytes()
    for name in ("default", "default@v99", "../default@v1"):
        cli("saved_style.py", "restore", name, code=2)
        assert ss.path().read_bytes() == before


def case_board(root):
    folder = reel(root)
    pick()
    cap, _ = readers()
    doc = cap.picker_doc(folder)
    assert doc["recommended"]["value"] == "bold-pop"
    assert doc["recommended"]["note"] == "Keep my words bright"
    assert doc["current"] is None
    assert not (folder / "look-picker-selection.json").exists()
    board = (SKILLS / "reel-captions/boards/look-picker/index.html").read_text(encoding="utf-8")
    assert "Your last pick" in board and "C.recommended" in board
    pick("edit_style.style", "layout-switch", "Let the layout do it")
    builder = module(SKILLS / "reel-canvas-build/scripts/make_beat_map.py", "make_beat_map")
    items = json.loads((folder / "work/edit_map.cut.json").read_text())["words"]
    words = [w["word"] for w in items]
    beat_doc = builder.build_doc(folder, {"beats": [{"w0": 0, "w1": 1, "layout": "full"}]},
                                 words, items, "work/edit_map.cut.json", folder / "work/edit_map.cut.json", 30, 60)
    builder.beat_schema.validate_beat_map(beat_doc, words)
    assert "edit_style" not in beat_doc
    plan = root / "plan.json"
    put(plan, {"beats": [{"w0": 0, "w1": 1, "layout": "full"}]})
    assert builder.run(folder, plan, "work/edit_map.cut.json", "work/cuts.json", False) == 0
    config = json.loads((folder / "beat-map.config.json").read_text(encoding="utf-8"))
    assert config["recommended"]["value"] == "layout-switch"
    assert config["recommended"]["note"] == "Let the layout do it"
    builder.beat_schema.validate_beat_map(json.loads((folder / "beat-map.state.json").read_text()), words)
    assert "edit_style" not in json.loads((folder / "beat-map-selection.json").read_text())
    board = (SKILLS / "reel-canvas-build/boards/beat-map/index.html").read_text(encoding="utf-8")
    assert "Your last pick" in board and "boardConfig.recommended" in board


def case_auto_record(root):
    folder = reel(root)
    cap, styles = readers()
    put(folder / "beat-map-selection.json", {
        "caption_style": {"style": "clean"}, "sent_at": "2026-11-06T10:00:00Z"})
    put(folder / "look-picker-selection.json", {
        "caption_style": {"style": "bold-pop"}, "sent_at": "2026-11-06T11:00:00Z"})
    assert cap.pick_style(folder) == ({"style": "bold-pop"}, "picker")
    record = ss.load()["picks"]["caption_style.style"]
    assert record["value"] == "bold-pop" and record["note"] == "" and record["at"]
    pick(note="  My exact words.  ")
    cap.pick_style(folder)
    assert ss.load()["picks"]["caption_style.style"]["note"] == "  My exact words.  "
    # The newer Beat Map wins, clears the old words, and does not set a saved default.
    put(folder / "beat-map-selection.json", {
        "caption_style": {"style": "boxed"}, "sent_at": "2026-11-06T12:00:00Z"})
    assert cap.pick_style(folder) == ({"style": "boxed"}, "reel")
    data = ss.load()
    assert data["picks"]["caption_style.style"]["value"] == "boxed"
    assert data["picks"]["caption_style.style"]["note"] == ""
    assert "caption_style" not in data
    # With no new Send, the remembered value still asks on the next reel.
    put(folder / "beat-map-selection.json", {})
    (folder / "look-picker-selection.json").unlink()
    try:
        cap.pick_style(folder)
    except cap.Stop as error:
        assert error.code == 1 and ". Last time you picked Boxed" in error.lines[0]
    else:
        raise AssertionError("An automatically remembered caption look must still ask")
    assert styles.pick_style({"edit_style": {"style": "layout-switch"}}) == (
        {"style": "layout-switch"}, "reel")
    record = ss.load()["picks"]["edit_style.style"]
    assert record["value"] == "layout-switch" and record["note"] == "" and record["at"]
    pick("edit_style.style", "layout-switch", "Keep my layout")
    styles.pick_style({"edit_style": {"style": "layout-switch"}})
    assert ss.load()["picks"]["edit_style.style"]["note"] == "Keep my layout"
    styles.pick_style({"edit_style": {"style": "punch-in"}})
    data = ss.load()
    assert data["picks"]["edit_style.style"]["value"] == "punch-in"
    assert data["picks"]["edit_style.style"]["note"] == ""
    assert "edit_style" not in data
    try:
        styles.pick_style({})
    except styles.Stop as error:
        assert error.code == 1 and ". Last time you picked Punch in" in error.lines[0]
    else:
        raise AssertionError("An automatically remembered editing style must still ask")


def case_shared_home_untouched(root):
    shared = root / "shared-state"
    state = json.loads((SOURCE_HOME / "state.json").read_text(encoding="utf-8"))
    for component in state.get("components", {}).values():
        for name, path in component.get("bins", {}).items():
            component["bins"][name] = str((SOURCE_HOME / path).resolve())
    put(shared / "state.json", state)
    # Recognizable bytes in a copy: a missing file cannot hide an accidental write.
    put(shared / "styles/default.json", {"schema": 1, "font": "Inter", "picks": {
        "caption_style.style": {"value": "boxed", "note": "Shared words", "at": "2026-11-06T12:00:00Z"}}})
    before = (shared / "styles/default.json").read_bytes()
    for name in ("captions_test.py", "styles_test.py"):
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B",
                                 str(Path(__file__).parent / name)],
                                env=dict(os.environ, EDITOR_SE_HOME=str(shared)),
                                capture_output=True, encoding="utf-8", timeout=180)
        assert (shared / "styles/default.json").read_bytes() == before, f"{name} changed the shared style"
        assert result.returncode == 0, (name, result.returncode, result.stdout, result.stderr)


def case_unreadable(root):
    folder = reel(root)
    cap, styles = readers()
    put(folder / "beat-map-selection.json", {"caption_style": {"style": "boxed"}})
    ss.path().parent.mkdir(parents=True, exist_ok=True)
    message = "Your saved style file can't be read, so I didn't change it. Ask Claude to repair it."
    for raw in (b'{"font": "My font", "accent": #123ABC}\n', b"[]", b"null", b"\xff"):
        ss.path().write_bytes(raw)
        for callback, expected in (
                (lambda: cap.pick_style(folder), ({"style": "boxed"}, "reel")),
                (lambda: styles.pick_style({"edit_style": {"style": "layout-switch"}}),
                 ({"style": "layout-switch"}, "reel"))):
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                assert callback() == expected
            assert output.getvalue().splitlines() == [ss.NOTE]
            assert ss.path().read_bytes() == raw, "Reading a Send overwrote the unreadable style"
        put(folder / "look-picker-selection.json", {"caption_style": {"style": "bold-pop"}})
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            assert cap.pick_style(folder) == ({"style": "bold-pop"}, "picker")
        assert output.getvalue().splitlines() == [ss.NOTE]
        assert ss.path().read_bytes() == raw
        (folder / "look-picker-selection.json").unlink()
        output = cli("standing_notes.py", "pick", "caption_style.style", "--value", '"clean"',
                     "--note", "Keep my words", code=2)
        assert output.splitlines() == [message], output
        assert ss.path().read_bytes() == raw, "Explicit pick overwrote the unreadable style"
        assert list(ss.path().parent.iterdir()) == [ss.path()], "Refused write left files behind"


def case_no_preselect(root):
    board = (SKILLS / "reel-canvas-build/boards/beat-map/index.html").read_text(encoding="utf-8")
    init = board.split("function loadEditStyle() {", 1)[1].split("function readEditStyle()", 1)[0]
    assignment = re.search(r'\$\("#edit-style"\)\.value\s*=\s*([^;]+);', init)
    assert assignment and assignment.group(1).strip() == 'es.style || ""', (
        "The Style menu must start from the reel choice or Ask, never the recommendation")


CASES = {"verbatim": case_verbatim, "recommended": case_recommended, "saved-wins": case_saved_wins,
         "archive": case_archive, "board": case_board, "auto-record": case_auto_record,
         "no-preselect": case_no_preselect, "shared-home-untouched": case_shared_home_untouched,
         "unreadable": case_unreadable}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="picks-", dir=scratch) as tmp:
        for name in [args.case] if args.case else CASES:
            root = Path(tmp) / name
            root.mkdir()
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
