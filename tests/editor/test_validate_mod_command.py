"""validate.py check 4, option B: a slash-command a plugin's own mod registers.

Run: python tests/editor/test_validate_mod_command.py (exit 0 on pass).
Imports scripts/validate.py and points it at a throwaway repo with one or two
fake plugins, then reads check_plugin_integrity()'s errors.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validate", REPO / "scripts" / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)

README = "# p\n\nType `/editor` to open the Editor Cockpit.\n"
MOD = "export const register = on => {\n  on('session.start', async ($, e, next) => {\n    await $.command.register({ name: 'editor', description: 'Open it' })\n    return next(e)\n  })\n}\n"


def plugin(root: Path, name: str, readme: str = "", mod: str | None = None, command_md: bool = False) -> None:
    d = root / "plugins" / name
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": name, "description": "x"}), encoding="utf-8")
    if readme:
        (d / "README.md").write_text(readme, encoding="utf-8")
    if mod is not None:
        (d / "hooks" / "mod").mkdir(parents=True)
        (d / "hooks" / "hooks.json").write_text(json.dumps({"modules": ["./mod/register.ts"]}), encoding="utf-8")
        (d / "hooks" / "mod" / "register.ts").write_text(mod, encoding="utf-8")
    if command_md:
        (d / "commands").mkdir()
        (d / "commands" / "editor.md").write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")


def errors(build) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        names = build(root)
        validate.REPO = root
        validate._published = lambda: set(names)
        return [e for e in validate.check_plugin_integrity() if "/editor" in e]


# (a) README advertises /editor and the plugin's mod registers it: no error.
assert errors(lambda r: (plugin(r, "p", README, MOD), ["p"])[1]) == []

# (b) same README, no mod: the advertised command resolves nowhere.
e = errors(lambda r: (plugin(r, "p", README), ["p"])[1])
assert len(e) == 1 and "advertised command /editor has no commands/editor.md" in e[0], e

# (c) another plugin's mod registers editor: still an error for this plugin.
e = errors(lambda r: (plugin(r, "p", README), plugin(r, "q", "", MOD), ["p", "q"])[2])
assert len(e) == 1 and "plugins/p/README.md" in e[0] and "advertised command /editor" in e[0], e

# (d) the mod registers editor and commands/editor.md exists: the file would shadow it.
e = errors(lambda r: (plugin(r, "p", README, MOD, command_md=True), ["p"])[1])
assert len(e) == 1 and "commands/editor.md would shadow the mod's /editor" in e[0], e

# Double quotes, and a name after other keys, are read too.
dq = MOD.replace("{ name: 'editor', description: 'Open it' }", '{ description: "Open it", name: "editor" }')
assert errors(lambda r: (plugin(r, "p", README, dq), ["p"])[1]) == []

print("test_validate_mod_command: all passed")
sys.exit(0)
