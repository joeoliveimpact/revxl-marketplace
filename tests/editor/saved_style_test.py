"""Saved-style contract: <scratch-dir> [--case NAME]; no shared state writes."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SKILLS = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills"
sys.path.insert(0, str(SKILLS / "_shared"))


def module(skill, name):
    spec = importlib.util.spec_from_file_location(name, SKILLS / skill / "scripts" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def put(doc, key, value):
    parts = key.split(".")
    for part in parts[:-1]:
        doc = doc.setdefault(part, {})
    doc[parts[-1]] = value


def get(doc, key):
    for part in key.split("."):
        doc = doc[part]
    return doc


def leaves(doc, prefix=""):
    out = {}
    for key, value in doc.items():
        name = prefix + key
        if isinstance(value, dict) and value:
            out.update(leaves(value, name + "."))
        else:
            out[name] = value
    return out


def key_paths(doc, prefix=""):
    for key, value in doc.items():
        name = prefix + key
        yield name
        if isinstance(value, dict):
            yield from key_paths(value, name + ".")


def sample(row):
    key = row["key"]
    special = {"style_id": "bold-pop", "accent": "#123ABC", "font": "Montserrat",
               "look.id": "warm", "cut.default_attempt": "first", "edit_style.style": "punch-in",
               "caption_style.style": "bold-pop", "caption_style.accent": "#123ABC"}
    if key in special:
        return special[key]
    if "allowed" in row:
        return next(value for value in row["allowed"] if value != row["default"])
    kind = row["type"]
    return {"text": "chosen", "number": 0.6, "bool": not row["default"],
            "object": {"future": "kept"}, "list": ["chosen"], "integers": [1],
            "integer": 3, "segments": [1]}[kind]


def case_table(ss):
    rows = {row["key"]: row for row in ss.FIELDS}
    assert len(rows) == len(ss.FIELDS), "Duplicate option rows"
    for row in ss.FIELDS:
        assert {"key", "default", "where", "ladder", "plain"} <= row.keys()
        if row["where"] != "saved style":
            continue
        data, value = {}, sample(row)
        assert value != row["default"], row["key"]
        put(data, row["key"], value)
        ss.save(data)
        assert get(ss.load(), row["key"]) == value, row["key"]
        assert ss.resolve(row["key"], saved=ss.load()) == (value, "saved"), row["key"]
        assert ss.resolve(row["key"], saved={}) == (None, "ask"), row["key"]
    st = module("reel-canvas-build", "styles")
    defaults = st.check_style({"style": "punch-in"}, "reel", 10)
    for key, value in leaves(defaults, "edit_style.").items():
        assert key in rows, key
        if key != "edit_style.style":  # style itself is asked, not defaulted
            assert rows[key]["default"] == value, key
    assert all("edit_style." + key in rows for key in st.STYLE_KEYS)
    assert all("edit_style.moves." + key in rows for key in st.MOVES)
    assert all("edit_style.moves.word_punches." + key in rows for key in st.PUNCH_KEYS)
    camera = st.check_style({"style": "punch-in", "moves": {
        "push": {"segments": "all"}, "ken_burns": {"segments": [0]}}}, "reel", 10)
    for key in ("push", "ken_burns"):
        assert rows[f"edit_style.moves.{key}.to"]["default"] == camera["moves"][key]["to"]
    camera = st.check_style({"style": "punch-in", "moves": {
        "word_punches": {"preset": "dramatic", "shape": "eased", "picks": []},
        "ratchet": {"picks": [], "levels": 2}, "push": {"segments": "all"},
        "ken_burns": {"segments": "all"}, "reframe": {"segments": "all", "edge": "left"}}}, "reel", 10)
    for key in key_paths(camera, "edit_style."):
        assert key in rows, key
    cap = module("reel-captions", "captions")
    for key, value in cap.DEFAULTS.items():
        assert rows["caption_style." + key]["default"] == value, key
    doctor = module("editor-doctor", "check_deps")
    for key in key_paths(json.loads(doctor.STYLE_SKELETON)):
        assert key in rows, key
    assert {"look.id", "look.strength"} <= rows.keys()
    for key, value in leaves(doctor.DEFAULTS).items():
        assert rows[key]["where"] == "editor.config.json", key
        assert rows[key]["default"] == value, key
        assert rows[key]["ladder"] == [], key
    # Unknown keys survive, output is deterministic UTF-8/LF, schema is always 1.
    data = {"schema": 99, "future": {"note": "caf\u00e9"}, "caption_style": None}
    ss.save(data)
    raw = ss.path().read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n") and "caf\u00e9" in raw.decode("utf-8")
    assert ss.load() == {**data, "schema": 1}
    assert data["schema"] == 99
    assert raw == (json.dumps(ss.load(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    before = raw
    for bad in ({"font": 1}, {"edit_style": []}, {"look": {"strength": True}},
                {"caption_style": {"line_breaks": 1}}, {"look": {"strength": float("nan")}},
                {"transitions": {"allowed": "fade"}}, {"cut": {"default_attempt": 1}}):
        try:
            ss.save(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Wrong type accepted: {bad}")
        assert ss.path().read_bytes() == before
    with patch.object(ss.os, "replace", side_effect=OSError("test write failure")):
        try:
            ss.save({"font": "Inter"})
        except OSError:
            pass
        else:
            raise AssertionError("Failed replacement was swallowed")
    assert ss.path().read_bytes() == before
    assert list(ss.path().parent.iterdir()) == [ss.path()], "Temporary write was left behind"
    assert doctor.ensure_style(ss.path().parents[1]) is False
    assert ss.path().read_bytes() == before
    fresh = ss.path().parents[1] / "doctor"
    assert doctor.ensure_style(fresh) is True
    skeleton = json.loads((fresh / "styles/default.json").read_text(encoding="utf-8"))
    assert skeleton["edit_style"] is None and skeleton["caption_style"] is None
    assert skeleton["cut"] == {"default_attempt": None}


def case_ladder(ss):
    choices = {"beat": {"accent": "#111111"}, "reel": {"accent": "#222222"},
               "saved": {"accent": "#333333"}}
    for source, value in (("beat", "#111111"), ("reel", "#222222"), ("saved", "#333333")):
        assert ss.resolve("accent", **choices) == (value, source)
        del choices[source]
    assert ss.resolve("accent", **choices) == (None, "ask")
    assert ss.resolve("caption_style.line_breaks", saved={"caption_style": {"line_breaks": False}}) == (False, "saved")
    assert ss.resolve("look.strength", beat={"look": {"strength": 0}}, saved={"look": {"strength": 1}}) == (0, "beat")


def case_readback(ss):
    full = {"style_id": "coach", "accent": "#FFD84D", "font": "Montserrat",
            "look": {"id": "warm", "strength": 0.6}, "transitions": {"allowed": ["fade"], "sfx_pair": "soft"},
            "edit_style": {"style": "punch-in", "punch_scale": 1.12},
            "caption_style": {"style": "bold-pop"}, "cut": {"default_attempt": "first"}}
    lines = ss.readback(full)
    assert len(lines) == 8 and len({line.split(":")[0] for line in lines}) == 8
    decoded_line = "Decoded style: Coach (from your style decoder)"
    assert decoded_line in lines
    decoded_only = ss.readback({"style_id": "coach"})
    assert decoded_line in decoded_only
    assert not any(line.startswith("Caption look") for line in decoded_only)
    assert next(row for row in ss.FIELDS if row["key"] == "style_id")["plain"] == "Decoded style"
    assert "Caption look: Bold pop, accent yellow #FFD84D" in lines
    assert "Brand font: Montserrat" in lines and "Grade look: Warm at 60 %" in lines
    assert "Editing style: punch-ins at 1.12x" in lines
    assert not any("not saved yet" in line for line in lines)
    assert not any(raw in "\n".join(lines) for raw in ("style_id", "edit_style", "caption_style", "default_attempt", "sfx_pair"))
    assert not any(row["key"] in line for row in ss.FIELDS if "." in row["key"] for line in lines)
    assert all("not saved yet, I'll ask" in line for line in ss.readback({}))
    assert "not saved yet" in "\n".join(ss.readback({"look": {"strength": "bad"}, "edit_style": []}))
    ss.save(full, "client-2")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert ss.main(["show", "client-2"]) == 0
    assert output.getvalue().splitlines() == lines
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert ss.main(["fields"]) == 0
    assert len(output.getvalue().splitlines()) == len(ss.FIELDS)
    assert "key | default | where | ladder" not in output.getvalue()  # one row per field


def case_bad(ss):
    note = "Your saved style couldn't be read, so this reel uses its own choices."
    for raw in (b"{", b"[]", b"null", b"\xff"):
        ss.path().parent.mkdir(parents=True, exist_ok=True)
        ss.path().write_bytes(raw)
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            assert ss.load() == {}
        assert output.getvalue().strip() == note
    with patch.object(Path, "read_text", side_effect=PermissionError("test unreadable file")):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            assert ss.load() == {}
        assert output.getvalue().strip() == note
    ss.path().unlink()
    output = io.StringIO()
    with contextlib.redirect_stderr(output):
        assert ss.load() == {}
    assert output.getvalue() == ""
    for name in ("", "../default", "Default", "a_b", "a/b", "a\\b", "a.json", "a\n", None):
        for fn in (ss.path, ss.load, lambda n: ss.save({}, n)):
            try:
                fn(name)
            except ValueError as e:
                assert "lowercase" in str(e)
            else:
                raise AssertionError(f"Bad name accepted: {name!r}")


def case_readers(ss):
    data = {"edit_style": {"style": "punch-in", "punch_scale": 1.2},
            "caption_style": {"style": "boxed"}, "accent": "#123ABC", "font": "Montserrat",
            "cut": {"default_attempt": "first"}}
    ss.save(data)
    st = module("reel-canvas-build", "styles")
    cap = module("reel-captions", "captions")
    compose = module("reel-canvas-build", "compose")
    board = module("reel-first-cuts", "make_board")
    with patch.object(ss, "load", wraps=ss.load) as reader:
        assert st.pick_style({}) == (data["edit_style"], "saved")
        assert cap.pick_style({}) == (data["caption_style"], "saved")
        assert cap.check_style({"style": "clean"})["accent"] == "#123ABC"
        assert compose.saved_brand() == {"accent": "#123ABC", "font": "Montserrat"}
        assert board.default_attempt() == "first"
        assert reader.call_count == 5, "A reader bypassed the shared loader"
    assert st.pick_style({"edit_style": {"style": "layout-switch"}})[1] == "reel"
    assert cap.pick_style({"caption_style": {"style": "clean"}})[1] == "reel"
    assert cap.check_style({"style": "clean", "accent": "#ABCDEF"})["accent"] == "#ABCDEF"
    ss.save({})
    assert board.default_attempt() == "last"


def case_nonobject(ss):
    cap = module("reel-captions", "captions")
    for raw in (b"[]", b"null"):
        ss.path().parent.mkdir(parents=True, exist_ok=True)
        ss.path().write_bytes(raw)
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            assert ss.load() == {}
        assert output.getvalue().strip() == ss.NOTE
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                cap.pick_style({})
            except cap.Stop as error:
                assert error.code == 1 and error.lines == (cap.ASK,), (error.code, error.lines)
            else:
                raise AssertionError("No caption choice must ask the client")


def case_isolated(ss):
    for script, args in (("saved_style.py", ["show"]), ("saved_style.py", ["fields"]),
                         ("saved_style.py", ["list"]), ("standing_notes.py", ["list"])):
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SKILLS / "_shared" / script), *args],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0, (script, args, result.stderr)


def case_unreadable_writes(ss):
    root = ss.path().parents[1]
    reel = root / "workspace/videos/reel"
    reel.mkdir(parents=True)
    (reel / "beat-map-selection.json").write_bytes(b'{"caption_style": {"style": "boxed"}}\n')
    message = "Your saved style file can't be read, so I didn't change it. Ask Claude to repair it."
    ss.path().parent.mkdir(parents=True, exist_ok=True)
    ss.path("default@v1").write_bytes(b'{"font": "Archived"}\n')
    for raw in (b'{"font": "My font", "accent": #123ABC}\n', b"[]", b"null", b"\xff"):
        ss.path().write_bytes(raw)
        before = {p.name: p.read_bytes() for p in ss.path().parent.iterdir()}
        for archive in (False, True):
            try:
                ss.save({"font": "Inter"}, archive=archive)
            except ValueError as error:
                assert str(error) == message
            else:
                raise AssertionError("A write replaced an unreadable style")
            assert ss.path().read_bytes() == raw
        for script, args in (
                ("standing_notes.py", ["pick", "caption_style.style", "--value", '"boxed"',
                                       "--note", "Keep my words"]),
                ("standing_notes.py", ["add", "Keep captions boxed", "--key", "caption_style.style",
                                       "--value", '"boxed"']),
                ("standing_notes.py", ["add", "Keep my words", "--unmatched"]),
                ("standing_notes.py", ["match", "a-note-id", "--key", "caption_style.style", "--value", '"boxed"']),
                ("standing_notes.py", ["remove", "a-note-id"]),
                ("saved_style.py", ["save-from-reel", str(reel), "--workspace", str(root / "workspace")]),
                ("saved_style.py", ["restore", "default@v1"])):
            result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SKILLS / "_shared" / script), *args],
                                    capture_output=True, encoding="utf-8", timeout=30)
            assert result.returncode == 2, (script, result.returncode, result.stdout, result.stderr)
            assert result.stdout == "" and result.stderr.splitlines() == [message], (script, result.stdout, result.stderr)
            assert ss.path().read_bytes() == raw, f"{script} overwrote the unreadable style"
            assert not (root / "workspace/.claude").exists(), "Refused save wrote a workspace skill"
            assert {p.name: p.read_bytes() for p in ss.path().parent.iterdir()} == before, "Refused write changed files"
    ss.path().write_bytes(b'{"font": "Original"}\n')
    with patch.object(Path, "read_text", side_effect=PermissionError("test unreadable file")):
        try:
            ss.save({"font": "Inter"})
        except ValueError as error:
            assert str(error) == message
        else:
            raise AssertionError("A write replaced a style that could not be opened")
    assert ss.path().read_bytes() == b'{"font": "Original"}\n'


CASES = {"table": case_table, "ladder": case_ladder, "readback": case_readback, "bad": case_bad,
         "readers": case_readers, "nonobject": case_nonobject, "isolated": case_isolated,
         "unreadable-writes": case_unreadable_writes}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    failures = 0
    # Unique scratch home even if the caller passes a shared scratch parent.
    with tempfile.TemporaryDirectory(prefix="saved-style-", dir=scratch) as root:
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(Path(root) / "state")}):
            import saved_style as ss
            for name in [args.case] if args.case else CASES:
                with patch.dict(os.environ, {"EDITOR_SE_HOME": str(Path(root) / name)}):
                    try:
                        CASES[name](ss)
                        print(f"PASS {name}")
                    except Exception as e:
                        failures += 1
                        print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"{failures} failed" if failures else "all passed")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
