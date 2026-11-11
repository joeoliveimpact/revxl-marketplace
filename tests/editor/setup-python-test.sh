#!/bin/bash
# Offline regression for Python setup: a failed uv link step can still leave a working interpreter.
# usage: bash tests/editor/setup-python-test.sh <scratch-dir> <state with a real install>
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) UV_EXE=uv.exe; PY_REL=python.exe; VPY_REL=Scripts/python.exe ;;
  Darwin) UV_EXE=uv; PY_REL=bin/python3; VPY_REL=bin/python ;;
  *) echo "SKIP not Windows or macOS"; exit 0 ;;
esac
R="$(cd "$(dirname "$0")/../.." && pwd)"
INS="$R/plugins/editor-superengine/skills/editor-doctor/scripts/install.sh"
S="${1:?usage: setup-python-test.sh <scratch-dir> <state with a real install>}"
REAL="${2:?usage: setup-python-test.sh <scratch-dir> <state with a real install>}"
mkdir -p "$S" || exit 1
S="$(cd "$S" && pwd)"; REAL="$(cd "$REAL" && pwd)" || exit 1
if [ "$UV_EXE" = uv.exe ]; then
  S="$(cygpath -m "$S")"; REAL="$(cygpath -m "$REAL")"
  # Setup refuses an install folder over 115 characters on Windows, and every case here installs into a
  # sub-folder of the scratch folder. Given a long scratch folder, work in a short one on the same drive
  # instead (made here, removed at the end), so the cases test setup and not the length guard.
  if [ "${#S}" -gt 60 ]; then
    SHORT="${S%%:*}:/es-setup-$$"
    mkdir "$SHORT" || { echo "FAIL could not make a short scratch folder at $SHORT"; exit 1; }
    echo "note: the scratch folder is long, so the cases run in $SHORT"
    S="$SHORT"; trap 'rm -rf "$SHORT"' EXIT
  fi
fi
REAL_UV="$REAL/uv/0.13.6/$UV_EXE"
[ -x "$REAL_UV" ] || { echo "FAIL real uv is missing"; exit 1; }
REAL_PY=
for p in "$REAL"/python/cpython-3.12.16-*; do
  if [ -x "$p/$PY_REL" ]; then REAL_PY=$p; break; fi
done
[ -n "$REAL_PY" ] || { echo "FAIL real Python is missing"; exit 1; }
fail=0; ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got [$2] want [$3]"; fail=1; fi; }
has() { printf '%s\n' "$out" | grep -F -c "$1"; }
ins() {
  PATH=/usr/bin:/bin HOME="$S/home" APPDATA="$S/appdata" LOCALAPPDATA="$S/localappdata" TEMP="$S/temp" \
    UV_OFFLINE=1 EDITOR_SE_HOME="$1" SETUP_TEST_CASE="$2" SETUP_TEST_UV="$REAL_UV" \
    SETUP_TEST_PY="$REAL_PY" SETUP_TEST_PY_REL="$PY_REL" sh "$INS" --help 2>&1
}
mkdir -p "$S/home" "$S/appdata" "$S/localappdata" "$S/temp" || exit 1
for c in link missing download success wrong-version will-not-start venv-failure install-cause traceback period; do
  d="$S/$c"
  # Never remove or overwrite a supplied folder's existing state.
  [ ! -e "$d" ] || { echo "FAIL scratch case already exists: $d (use a fresh scratch directory)"; exit 1; }
  mkdir -p "$d/uv/0.13.6" || exit 1
  cat > "$d/uv/0.13.6/$UV_EXE" <<'FAKE'
#!/bin/sh
case "$*" in
  --version) echo 'uv 0.13.6 (setup test)'; exit 0 ;;
  'python install --no-bin 3.12.16')
    case "$SETUP_TEST_CASE" in
      link|success|venv-failure)
        mkdir -p "$UV_PYTHON_INSTALL_DIR" && cp -R "$SETUP_TEST_PY" "$UV_PYTHON_INSTALL_DIR/" || exit 3
        if [ "$SETUP_TEST_CASE" != link ]; then exit 0; fi
        echo "error: Missing expected target directory for Python minor version link at $UV_PYTHON_INSTALL_DIR/${SETUP_TEST_PY##*/}" >&2 ;;
      wrong-version|will-not-start)
        p="$UV_PYTHON_INSTALL_DIR/cpython-3.12.16-test/$SETUP_TEST_PY_REL"
        mkdir -p "$(dirname "$p")" || exit 3
        if [ "$SETUP_TEST_CASE" = wrong-version ]; then
          printf '#!/bin/sh\necho 3.12.15\n' > "$p"
        else printf '#!/bin/sh\nexit 1\n' > "$p"; fi
        chmod +x "$p"
        echo 'error: Missing expected target directory for Python minor version link' >&2 ;;
      missing) echo 'error: something else broke' >&2 ;;
      install-cause) echo 'error: Failed to install Python.' >&2
        echo 'Caused by: could not unpack archive' >&2
        echo 'Caused by: No space left on device (os error 28)' >&2 ;;
      traceback) printf '%s\n' 'Traceback (most recent call last):' \
        '  File "urllib3/connection.py", line 12' '  File "aiohttp/http_parser.py", line 512' \
        'RuntimeError: disk is full' >&2 ;;
      period) echo 'error: access denied.' >&2 ;;
      download) echo 'error: Failed to download https://example.invalid/python' >&2
        echo 'Caused by: error sending request' >&2 ;;
    esac
    exit 2 ;;
  venv\ *)
    printf '%s\n' "$@" > "$EDITOR_SE_HOME/venv-args.txt"
    if [ "$SETUP_TEST_CASE" = venv-failure ]; then
      echo 'error: Failed to create virtualenv' >&2
      echo 'Caused by: No space left on device (os error 28)' >&2
      exit 2
    fi
    exec "$SETUP_TEST_UV" "$@" ;;
  *) echo "error: unexpected fake uv arguments: $*" >&2; exit 3 ;;
esac
FAKE
  chmod +x "$d/uv/0.13.6/$UV_EXE"
  # A stale network error must never classify this run's non-network failure.
  mkdir -p "$d/logs"; printf '%s\n' 'error: Failed to download in an earlier step' > "$d/logs/install.log"
  out="$(ins "$d" "$c")"; rc=$?
  printf '%s\n' "$out" > "$d/output.txt"
  case "$c" in
    link|success)
      ck "$c: exit 0" "$rc" 0
      ck "$c: Python ready" "$(has '✓ Python 3.12.16')" 1
      ck "$c: stage 2 help reached" "$(has 'usage: install.py')" 1
      version=$([ -x "$d/venv/$VPY_REL" ] && "$d/venv/$VPY_REL" -I -c 'import platform; print(platform.python_version())' 2>/dev/null | tr -d '\r')
      ck "$c: real venv Python version" "$version" 3.12.16
      venv_python=$(sed -n '4p' "$d/venv-args.txt")
      if [ "$c" = success ]; then
        ck 'success: venv uses requested version' "$venv_python" 3.12.16
      else
        ck 'link: venv uses verified interpreter path' "$venv_python" "$d/python/${REAL_PY##*/}/$PY_REL"
      fi
      if [ "$c" = link ]; then
        ck 'link: recovery note in log' "$(grep -c 'install step reported an error.*Python it installed works.*setup continues' "$d/logs/install.log")" 1
        ck 'link: no alarming screen message' "$(has 'error:')" 0
        out="$(ins "$d" "$c")"; rc=$?
        ck 'repeat: exit 0' "$rc" 0
        ck 'repeat: Python already in place' "$(has '✓ Python 3.12.16 already in place')" 1
        ck 'repeat: no Python install' "$(has 'Installing Python')" 0
      fi ;;
    missing)
      ck 'missing: exit 1' "$rc" 1
      ck 'missing: names install failure' "$(has 'installing Python failed')" 1
      ck 'missing: quotes current error' "$(has 'something else broke')" 1
      ck 'missing: no internet advice' "$(has 'internet')" 0 ;;
    download)
      ck 'download: exit 1' "$rc" 1
      ck 'download: names download failure' "$(has 'downloading Python failed')" 1
      ck 'download: internet advice' "$(has 'Check the internet connection')" 1 ;;
    wrong-version|will-not-start)
      ck "$c: exit 1" "$rc" 1
      if [ "$c" = wrong-version ]; then
        ck "$c: names version mismatch" "$(has 'installing Python failed: the installed Python reports 3.12.15 instead of 3.12.16. Send the setup report.')" 1
      else
        ck "$c: names startup failure" "$(has 'installing Python failed: the installed Python did not start. Send the setup report.')" 1
      fi
      ck "$c: no internet advice" "$(has 'internet')" 0 ;;
    venv-failure|install-cause)
      ck "$c: exit 1" "$rc" 1
      if [ "$c" = venv-failure ]; then
        ck "$c: names venv failure" "$(has "creating the editor's Python environment failed: error: Failed to create virtualenv (No space left on device (os error 28)). Send the setup report.")" 1
      else
        ck "$c: includes last cause" "$(has 'error: Failed to install Python. (No space left on device (os error 28)). Send the setup report.')" 1
      fi
      ck "$c: no internet advice" "$(has 'internet')" 0 ;;
    traceback|period)
      ck "$c: exit 1" "$rc" 1
      ck "$c: no internet advice" "$(has 'internet')" 0
      if [ "$c" = period ]; then
        ck 'period: exactly one final period' "$(has 'error: access denied. Send the setup report.')" 1
      fi ;;
  esac
done
# Import errors must not inherit internet advice (ENOTFOUND is part of ModuleNotFoundError).
if [ -x "$S/success/venv/$VPY_REL" ]; then
  "$S/success/venv/$VPY_REL" -X utf8 -I -B - "$R/plugins/editor-superengine/skills/editor-doctor/scripts/install.py" "$S" <<'PY'
import importlib.util
import io
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("installer", sys.argv[1])
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
setup = installer.Setup.__new__(installer.Setup)
setup.log = io.StringIO()
cases = [
    ("import", False, "ModuleNotFoundError: no module named example", "ModuleNotFoundError: no module named example"),
    ("access", False, "error: access denied", "error: access denied"),
    ("npm-code", True, "npm error code ENOTFOUND", ""),
    ("http", True, "error: HTTP status client error (403 Forbidden)", ""),
    ("npm-network", True, """npm error code ENOTFOUND
npm error syscall getaddrinfo
npm error errno ENOTFOUND
npm error network request to https://registry.npmjs.org/... failed, reason: getaddrinfo ENOTFOUND registry.npmjs.org
npm error network This is a problem related to network connectivity.
npm error A complete log of this run can be found in: C:\\...\\_logs\\2026-11-11T00_00_00_000Z-debug-0.log""", ""),
    ("npm-integrity", False, """npm error code EINTEGRITY
npm error sha512-... integrity checksum failed when using sha512: wanted sha512-... but got sha512-...
npm error A complete log of this run can be found in: C:\\...\\_logs\\...-debug-0.log""",
     "EINTEGRITY: sha512-... integrity checksum failed when using sha512: wanted sha512-... but got sha512-"),
    ("npm-usage", False, r"""npm error code EUSAGE
npm error
npm error The `npm ci` command can only install with an existing package-lock.json or
npm error npm-shrinkwrap.json with lockfileVersion >= 1. Run an install with npm@5 or
npm error later to generate a package-lock.json file, then try again.
npm error
npm error Clean install a project
npm error
npm error Usage:
npm error npm ci
npm error A complete log of this run can be found in: C:\npm-cache\_logs\2026-11-11T00_00_00_000Z-debug-0.log""",
     ("EUSAGE", "can only install with an existing package-lock.json")),
    ("npm-script", False, r"""npm error code 1
npm error path C:\x\node_modules\post
npm error command failed
npm error command C:\WINDOWS\system32\cmd.exe /d /s /c node fail.js
npm error boom: the real cause
npm error A complete log of this run can be found in: C:\npm-cache\_logs\2026-11-11T00_00_00_000Z-debug-0.log""",
     ("exit code 1", "command failed", "boom: the real cause")),
    ("npm-permission", False, r"""npm error code EPERM
npm error syscall open
npm error path C:/x/node_modules/.staging/pkg
npm error errno -4048
npm error Error: EPERM: operation not permitted, open 'C:/x/node_modules/.staging/pkg'
npm error  [Error: EPERM: operation not permitted, open 'C:/x/node_modules/.staging/pkg'] {
npm error   errno: -4048,
npm error   code: 'EPERM',
npm error A complete log of this run can be found in: C:\npm-cache\_logs\2026-11-11T00_00_00_000Z-debug-0.log""",
     ("EPERM", "operation not permitted")),
    ("npm-cap", False, "npm error code ETEST\nnpm error " + "x" * 350, "ETEST: " + "x" * 293),
    ("traceback", False, 'Traceback (most recent call last):\n  File "urllib3/connection.py", line 12\n  File "aiohttp/http_parser.py", line 512\nRuntimeError: disk is full', "RuntimeError: disk is full"),
    ("uv-cause", False, "error: Failed to install: torch-2.5.1 (torch==2.5.1).\nCaused by: could not unpack\nCaused by: No space left on device (os error 28)",
     "error: Failed to install: torch-2.5.1 (torch==2.5.1). (No space left on device (os error 28))"),
    ("hints", False, "error: access denied.\nhint: see error: documentation\nnote: try again", "error: access denied"),
    ("period", False, "error: access denied.  ", "error: access denied"),
    ("cap", False, "error: " + "x" * 250 + ".", "error: " + "x" * 193),
]
cases += [(name + "-legacy", network, error.replace("npm error", "npm ERR!"), detail)
          for name, network, error, detail in cases if name.startswith("npm-")]
for i, wording in enumerate(["Failed to download", "error sending request", "dns error", "connection refused",
                             "connection reset", "connection timed out", "connection closed", "timed out",
                             "tls handshake", "certificate verify failed", "HTTP status 503",
                             "EAI_AGAIN", "ECONNRESET", "ECONNREFUSED", "ETIMEDOUT", "CERT_HAS_EXPIRED",
                             "UNABLE_TO_VERIFY_LEAF_SIGNATURE"]):
    cases.append((f"network-{i}", True, f"error: {wording}", ""))
failed = False
for name, network, error, detail in cases:
    folder = Path(sys.argv[2]) / f"command-{name}"
    folder.mkdir()
    setup.run([sys.executable, "-I", "-c", f"import sys; print({error!r}, file=sys.stderr); sys.exit(1)"])
    message = setup.command_failure("installing Python packages")
    (folder / "output.txt").write_text(message, encoding="utf-8")
    try:
        assert ("Check the internet connection" in message) == network, message
        assert "A complete log of this run" not in message, message
        assert "hint:" not in message and "note:" not in message, message
        if isinstance(detail, tuple):
            assert all(part in message for part in detail), message
            assert all(part not in message for part in ("syscall", "errno", "cmd.exe", "path ",
                                                        "Usage:", "Clean install a project", "[", "{")), message
            assert message.endswith(". Send the setup report."), message
            assert not message.endswith(".. Send the setup report."), message
        elif not network:
            assert message == f"installing Python packages failed: {detail}. Send the setup report.", message
        print(f"PASS command-{name}")
    except AssertionError as exc:
        print(f"FAIL command-{name}: {exc}")
        failed = True
sys.exit(1 if failed else 0)
PY
  ck 'captured command errors: network advice only for network failures' "$?" 0
else
  ck 'captured command error checks have a working Python' missing ready
fi
exit $fail
