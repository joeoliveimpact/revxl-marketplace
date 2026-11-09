"""Doctor --set-controls and hub config proof. Temp folders only, no installs or browser.
Run: python -I tests/editor/set_controls_test.py
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
SK = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills"
sys.path[:0] = [str(SK / "_shared"), str(SK / "editor-doctor/scripts")]
import runtime as rt
import check_deps as doctor
import hub_rows


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    # All optional saved-style/brand reads must stay in this owned home too.
    with patch.dict(os.environ, EDITOR_SE_HOME=str(root / "state"), HOME=td, USERPROFILE=td):
        old_cwd = Path.cwd()
        os.chdir(root)
        try:
            config = rt.config_path(root)
            config.parent.mkdir(parents=True)
            original = {"nle": "mcp", "custom": {"keep": [1, 2]}, "paths": {"editor": "desk", "videos": "clips"}}
            config.write_bytes((json.dumps(original) + "\n").encode("utf-8"))
            with patch.object(doctor, "doctor", side_effect=AssertionError("full doctor must not run")):
                for mode in ("advanced", "simple"):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        assert doctor.main(["--set-controls", mode]) == 0
                    cfg = rt.read_config(root)
                    assert cfg["controls"] == mode
                    assert all(cfg[k] == v for k, v in original.items())
                    assert f"STATUS controls ok {mode}" in output.getvalue()
                    assert hub_rows.build(root)["config"]["controls"] == mode
                    assert b"\r" not in config.read_bytes()
                    print(f"PASS --set-controls {mode}, preserves keys, hub config, LF")
            for value in (None, "invalid", [], 42):
                cfg = dict(original)
                if value is not None:
                    cfg["controls"] = value
                config.write_bytes(json.dumps(cfg).encode("utf-8"))
                assert hub_rows.build(root)["config"]["controls"] == "simple"
            config.unlink()
            assert hub_rows.build(root)["config"]["controls"] == "simple"
            print("PASS missing/invalid controls default to simple")
            for bad in (b"{broken", b"[]"):
                config.write_bytes(bad)
                with contextlib.redirect_stdout(io.StringIO()):
                    assert doctor.main(["--set-controls", "advanced"]) == 1
                assert config.read_bytes() == bad
            print("PASS invalid config refused without overwrite")
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    doctor.main(["--set-controls", "invalid"])
                    raise AssertionError("invalid choice accepted")
                except SystemExit as error:
                    assert error.code == 2
            print("PASS invalid command choice rejected")
        finally:
            os.chdir(old_cwd)
