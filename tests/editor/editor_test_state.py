"""Scratch editor choices for tests; installed tool binaries are read only."""
import contextlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/_shared"))
import runtime


def copy_tool_state(source, target, *, packages=False):
    """Copy installation facts, leaving saved choices out of the test home."""
    source, target = Path(source).resolve(), Path(target).resolve()
    state_file = source / "state.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}
    for component in state.get("components", {}).values():
        for name, path in component.get("bins", {}).items():
            component["bins"][name] = str((source / path).resolve())
    for model in state.get("models", {}).values():
        if "dir" in model:
            model["dir"] = str((source / model["dir"]).resolve())
    target.mkdir(parents=True, exist_ok=True)
    (target / "state.json").write_bytes((json.dumps(state, ensure_ascii=False) + "\n").encode("utf-8"))
    if packages:
        # The renderer locates these relative to state_dir, including in subprocesses.
        for name in ("hyperframes", "hyperframes-home"):
            if (source / name).is_dir():
                shutil.copytree(source / name, target / name)
    return target


@contextlib.contextmanager
def isolated_home(*, packages=False):
    """Cover in-process readers and child scripts; restore the caller's environment."""
    source = runtime.state_dir()
    with tempfile.TemporaryDirectory(prefix="editor-test-state-") as folder:
        home = copy_tool_state(source, Path(folder) / "state", packages=packages)
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(home)}):
            yield home
