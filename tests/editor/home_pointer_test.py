"""H-S1a-path-2 check: the setup's home-pointer.txt and runtime.state_dir(). Offline, temp folders only, about 10 s on Windows.
install.py's real main() runs with a short EDITOR_SE_HOME, its Setup stubbed (no downloads); then state_dir() with no
EDITOR_SE_HOME must return that folder, and fall back to the default when the folder is gone or holds no install.
usage: python -I tests/editor/home_pointer_test.py    (exit 0 = all pass)
"""
import importlib.util, os, shutil, subprocess, sys, tempfile, types
from pathlib import Path

SK = Path(__file__).resolve().parents[2] / "plugins" / "editor-superengine" / "skills"
sys.path.insert(0, str(SK / "_shared"))
import runtime as rt  # noqa: E402

spec = importlib.util.spec_from_file_location("install", SK / "editor-doctor" / "scripts" / "install.py")
ins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ins)
ins.Setup = lambda st, engine, repick=False: types.SimpleNamespace(go=lambda: None)  # the install itself, stubbed
spec2 = importlib.util.spec_from_file_location("check_deps", SK / "editor-doctor" / "scripts" / "check_deps.py")
cd = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(cd)
fail = 0


def ck(name, got, want):
    global fail
    print(("PASS " if got == want else "FAIL ") + name + ("" if got == want else f": got [{got}] want [{want}]"))
    fail |= got != want


def install(st):
    os.environ["EDITOR_SE_HOME"] = str(st)
    sys.argv = ["install.py"]
    try:
        return ins.main()
    finally:
        del os.environ["EDITOR_SE_HOME"]


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    os.environ.pop("EDITOR_SE_HOME", None)
    lad = td / "appdata"
    lad = lad / ("x" * max(1, 175 - len(str(lad))))  # LOCALAPPDATA 175 characters, so the default folder is 200: too long
    os.environ.update(LOCALAPPDATA=str(lad), HOME=str(td / "home"), XDG_DATA_HOME=str(td / "xdg"))
    default, short = rt.default_state_dir(), td / "short"
    short.mkdir()
    (short / "state.json").write_text("{}", encoding="utf-8")
    ck("setup with a short EDITOR_SE_HOME exits 0", install(short), 0)
    ck("home-pointer.txt names that folder (one LF line)", (default / rt.HOME_POINTER).read_bytes(),
       (Path(os.path.abspath(short)).as_posix() + "\n").encode("utf-8"))
    ck("state_dir() with no EDITOR_SE_HOME is that folder", rt.state_dir(), short)
    os.environ["EDITOR_SE_HOME"] = str(td / "other")
    ck("EDITOR_SE_HOME still wins over the pointer", rt.state_dir(), td / "other")
    del os.environ["EDITOR_SE_HOME"]
    seen = {}
    real_run, cd.subprocess.run = cd.subprocess.run, lambda cmd, **kw: seen.update(kw) or types.SimpleNamespace(returncode=0)
    try:
        cd.run_installer("auto")
    finally:
        cd.subprocess.run = real_run
    ck("the doctor runs the setup in the pointed-to folder", Path(seen.get("env", {}).get("EDITOR_SE_HOME", "")), short)
    if sys.platform == "win32" and shutil.which("sh"):
        # The loop case: the default folder is too long, and an earlier setup with a short EDITOR_SE_HOME left the pointer.
        # install.sh re-run with no EDITOR_SE_HOME must follow it, not refuse. No curl on PATH: it stops offline at the uv download.
        env = {k: v for k, v in os.environ.items() if k != "EDITOR_SE_HOME"}
        r = subprocess.run([shutil.which("sh"), "-c", 'PATH=/usr/bin:/bin exec sh "$0"',
                            str(SK / "editor-doctor" / "scripts" / "install.sh")], env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        out = r.stdout + r.stderr
        ck("install.sh re-run with no EDITOR_SE_HOME: not refused", "characters long" in out, False)
        ck("install.sh re-run works in the pointed-to folder", ((short / "logs" / "install.log").is_file(),
           (default / "logs").exists()), (True, False))
        shutil.rmtree(short / "downloads", ignore_errors=True)
        shutil.rmtree(short / "logs", ignore_errors=True)
    else:
        print("SKIP install.sh loop case (Windows only)")
    (short / "state.json").unlink()
    ck("a pointer to a folder with no install falls back to the default", rt.state_dir(), default)
    shutil.rmtree(short)
    ck("a pointer to a missing folder falls back to the default", rt.state_dir(), default)
    short.mkdir()
    (short / "state.json").write_text("{}", encoding="utf-8")
    install(short)
    ck("setup at the default folder exits 0", install(default), 0)
    ck("a setup at the default folder drops the pointer", (default / rt.HOME_POINTER).exists(), False)
    ck("state_dir() is the default again", rt.state_dir(), default)
sys.exit(fail)
