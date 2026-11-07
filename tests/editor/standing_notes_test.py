"""Standing-note contract: <scratch-dir> [--case NAME]; own scratch state only."""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SKILLS = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills"
SHARED = SKILLS / "_shared"
CLI = SHARED / "standing_notes.py"
sys.path.insert(0, str(SHARED))
import saved_style as ss


def cli(*args, code=0, cwd=None):
    result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(CLI), *args],
                            cwd=cwd, capture_output=True, encoding="utf-8")
    assert result.returncode == code, (result.returncode, result.stdout, result.stderr)
    return result.stdout + result.stderr


def add(note, key="caption_style.style", value="bold-pop", style="default"):
    cli("add", note, "--key", key, "--value", json.dumps(value), "--style", style)
    return ss.load(style)["standing_notes"][-1]["id"]


def readback(style="default"):
    return "\n".join(ss.readback(ss.load(style)))


def captions():
    spec = importlib.util.spec_from_file_location(
        "captions", SKILLS / "reel-captions/scripts/captions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case_sticks(root):
    add("Always use bold pop captions")
    cap = captions()
    for name in ("first-reel", "second-reel"):
        reel = root / name
        reel.mkdir()
        (reel / "beat-map-selection.json").write_bytes(b'{"beats": [], "word_marks": []}\n')
        assert ss.resolve("caption_style.style", saved=ss.load()) == ("bold-pop", "saved")
        assert cap.pick_style(reel) == ({"style": "bold-pop"}, "saved")
    assert "Always: Caption look = bold-pop" in cli("list")
    assert "Always: Caption look = bold-pop" in readback()
    # A named style must not change the default or another client's notes.
    add("My captions are boxed", value="boxed", style="client-b")
    assert ss.load("client-b")["caption_style"]["style"] == "boxed"
    assert ss.load()["caption_style"]["style"] == "bold-pop"
    assert "My captions are boxed" in cli("list", "--style", "client-b")


def case_verbatim(root):
    note = '  Always say "caf\u00e9" \u2014 \u9ec4\u8272 \U0001f49b\nKeep my "words".  '
    add(note)
    record = ss.load()["standing_notes"][0]
    assert record["note"].encode("utf-8") == note.encode("utf-8")
    assert record["status"] == "matched" and record["added"]
    assert record["key"] == "caption_style.style" and record["value"] == "bold-pop"
    assert f'(your words: "{note}")' in cli("list")
    assert note in readback()
    assert b"\r" not in ss.path().read_bytes()


def case_unmatched(root):
    note = "Give every reel that feeling from my childhood"
    cli("add", note, "--unmatched")
    record = ss.load()["standing_notes"][0]
    assert record["status"] == "unmatched" and record["note"] == note
    assert record["key"] is None and record["value"] is None
    assert ss.resolve("caption_style.style", saved=ss.load()) == (None, "ask")
    assert set(ss.load()) == {"schema", "standing_notes"}
    for output in (cli("list"), readback()):
        assert "Standing notes:" not in output
        section = output.split("Could not be matched:", 1)[1]
        assert note in section
        assert "I couldn't tie this to a setting; tell me which part of the edit it's about." in section


def case_replace(root):
    first = add("Always use bold pop")
    second = add("Always use boxed captions", value="boxed")
    assert first != second
    assert ss.resolve("caption_style.style", saved=ss.load()) == ("boxed", "saved")
    for output in (cli("list"), readback()):
        assert "Always use bold pop" in output and "Always use boxed captions" in output
        assert "replaced by a newer note" in output
        assert first not in output and second not in output
        assert "Always: Caption look = boxed" in output
        assert "Always: Caption look = bold-pop" not in output
    cli("remove", str(first))
    assert ss.resolve("caption_style.style", saved=ss.load()) == ("boxed", "saved")
    assert second in cli("list", "--ids")


def case_match(root):
    cli("add", "Use my yellow", "--unmatched")
    note_id = ss.load()["standing_notes"][0]["id"]
    cli("match", str(note_id), "--key", "accent", "--value", '"#FFD84D"')
    record = ss.load()["standing_notes"][0]
    assert record["id"] == note_id and record["note"] == "Use my yellow"
    assert record["status"] == "matched"
    assert ss.resolve("accent", saved=ss.load()) == ("#FFD84D", "saved")
    assert "Use my yellow" not in cli("list").split("Could not be matched:", 1)[1]
    # Matching a formerly unmatched note also replaces an existing rule.
    previous = add("My font is Inter", key="font", value="Inter")
    cli("add", "Use the other font", "--unmatched")
    current = ss.load()["standing_notes"][-1]["id"]
    cli("match", str(current), "--key", "font", "--value", '"Montserrat"')
    assert ss.resolve("font", saved=ss.load()) == ("Montserrat", "saved")
    assert "replaced by a newer note" in cli("list")
    assert current in cli("list", "--ids") and current not in readback()
    assert previous != current


def case_remove(root):
    add("Old caption choice")
    current = add("Use boxed now", value="boxed")
    accent = add("Use my yellow", key="accent", value="#FFD84D")
    cli("remove", str(current))
    assert ss.resolve("caption_style.style", saved=ss.load()) == ("bold-pop", "saved")
    assert ss.resolve("accent", saved=ss.load()) == ("#FFD84D", "saved")
    assert "Use boxed now" not in cli("list")
    assert "Always: Caption look = bold-pop" in cli("list")
    assert "replaced" not in cli("list")
    assert all("replaced_by" not in n for n in ss.load()["standing_notes"])
    cli("remove", str(accent))
    assert ss.resolve("accent", saved=ss.load()) == (None, "ask")
    cli("add", "Still unsure", "--unmatched")
    note_id = ss.load()["standing_notes"][-1]["id"]
    cli("remove", str(note_id))
    assert "Still unsure" not in readback()


def case_badkey(root):
    for key in ("unknown.option", "language", "ports.board"):
        output = cli("add", "Do not lose this", "--key", key, "--value", '"chosen"', code=2)
        assert "saved style" in output.lower()
        assert not ss.path().exists(), "Invalid key wrote a style"
    add("Keep this rule")
    before = ss.path().read_bytes()
    for args in (("add", "Bad JSON", "--key", "accent", "--value", "not-json"),
                 ("add", "Wrong type", "--key", "accent", "--value", "123"),
                 ("add", "Unset is not a rule", "--key", "accent", "--value", "null"),
                 ("add", "Missing value", "--key", "accent"),
                 ("add", "Conflicting choices", "--unmatched", "--value", "true"),
                 ("match", "missing", "--key", "accent", "--value", '"#FFD84D"'),
                 ("remove", "missing"),
                 ("add", "Bad name", "--unmatched", "--style", "../outside")):
        cli(*args, code=2)
        assert ss.path().read_bytes() == before, args


def case_allowed(root):
    add("Keep this rule")
    before = ss.path().read_bytes()
    for key, value in (("caption_style.style", "invented"), ("look.id", "invented"),
                       ("edit_style.style", "invented"), ("caption_style", {"style": "invented"})):
        output = cli("add", "Invalid choice", "--key", key, "--value", json.dumps(value), code=2)
        assert "Traceback" not in output and len(output.splitlines()) == 1
        assert ss.path().read_bytes() == before
    cli("add", "Match me later", "--unmatched")
    note_id = ss.load()["standing_notes"][-1]["id"]
    before = ss.path().read_bytes()
    cli("match", note_id, "--key", "caption_style.style", "--value", '"invented"', code=2)
    assert ss.path().read_bytes() == before


def case_parent(root):
    child = add("Bold captions")
    parent = add("Whole caption choice", key="caption_style", value={"style": "boxed", "line_breaks": False})
    assert ss.load()["standing_notes"][0]["replaced_by"] == parent
    assert ss.load()["caption_style"] == {"style": "boxed", "line_breaks": False}
    # Parent wins even when a child note is added later.
    later = add("Clean captions", value="clean")
    assert ss.load()["standing_notes"][-1]["replaced_by"] == parent
    assert ss.load()["caption_style"]["style"] == "boxed"
    cli("remove", parent)
    assert ss.load()["caption_style"] == {"style": "clean"}
    assert all(n.get("replaced_by") != parent for n in ss.load()["standing_notes"])
    cli("remove", later)
    assert ss.load()["caption_style"]["style"] == "bold-pop"
    cli("remove", child)
    assert "caption_style" not in ss.load()
    cli("add", "Unclear words", "--unmatched")
    unmatched = ss.load()["standing_notes"][-1]["id"]
    assert unmatched not in cli("list") and unmatched not in readback()
    assert unmatched in cli("list", "--ids")


CASES = {"sticks": case_sticks, "verbatim": case_verbatim, "unmatched": case_unmatched,
         "replace": case_replace, "match": case_match, "remove": case_remove, "badkey": case_badkey,
         "allowed": case_allowed, "parent": case_parent}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="standing-notes-", dir=scratch) as temporary:
        for name in [args.case] if args.case else CASES:
            root = Path(temporary) / name
            root.mkdir()
            with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / "state")}):
                try:
                    CASES[name](root)
                    print(f"PASS {name}")
                except Exception as exc:
                    failures += 1
                    print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"{failures} failed" if failures else "all passed")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
