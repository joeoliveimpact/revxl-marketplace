#!/bin/sh
# find-python.sh - find a Python >= 3.9 for higgsfield-superengine on Mac/Linux; install one per-user if there is none.
# The Mac twin of find-python.ps1, with the same contract. Looks in the same fixed places as hooks/hf-guard.sh, so the
# guard and the skills use the same kind of Python:
#   the uv-managed Python (~/.local/share/uv/python), python.org, Homebrew, /usr/local, and /usr/bin/python3 only
#   when Apple's developer tools are installed (otherwise that file opens an install pop-up).
# None found -> unattended per-user install, no admin password: uv (astral.sh) into ~/.local/bin, then
#   uv python install 3.12   (into ~/.local/share/uv/python)
# Run it from the client's workspace folder. On success it writes the interpreter's full path (one line, UTF-8, no
# newline) to higgsfield/.python and prints one JSON line, exit 0:
#   {"status": "ok", "via": "uv", "version": "3.12.11", "python": "/Users/.../bin/python3", "tried": [...]}
# Use it as:  Bash  "$(cat higgsfield/.python)" script.py
# Otherwise one JSON line, exit 1: status not_found (the install did not give a usable Python), no_curl, or dry_run.
# Launch:  sh find-python.sh [--dry-run]     --dry-run never installs; reports what it would run.
tried=""
add() { tried="$tried$1
"; }
probe() {  # $1 label, $2 path -> sets found_py and returns 0 if it is a usable Python >= 3.9
  if [ ! -x "$2" ]; then return 1; fi
  if "$2" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    found_py=$2; found_via=$1; add "$1: ok"; return 0
  fi
  add "$1: older than 3.9 or did not run"; return 1
}
find_py() {
  for p in "$HOME"/.local/share/uv/python/cpython-3.*/bin/python3; do probe uv "$p" && return 0; done
  for p in /Library/Frameworks/Python.framework/Versions/3.*/bin/python3; do probe python.org "$p" && return 0; done
  probe homebrew /opt/homebrew/bin/python3 && return 0
  probe usr-local /usr/local/bin/python3 && return 0
  if [ "$(uname -s)" = Linux ] || xcode-select -p >/dev/null 2>&1; then
    probe system /usr/bin/python3 && return 0
  else
    add "system: skipped (Apple developer tools not installed; it would open an install pop-up)"
  fi
  return 1
}
result() {  # $1 status, $2 exit code; JSON is written by Python when there is one
  if [ -n "$found_py" ]; then
    TRIED="$tried" "$found_py" -c 'import json, os, sys
st, via, py = sys.argv[1:4]
v = "%d.%d.%d" % sys.version_info[:3]
if st == "ok":
    os.makedirs("higgsfield", exist_ok=True)
    with open(os.path.join("higgsfield", ".python"), "w", encoding="utf-8", newline="") as f:
        f.write(py)
print(json.dumps({"status": st, "via": via, "version": v, "python": py,
                  "tried": [t for t in os.environ["TRIED"].split("\n") if t]}))' "$1" "$found_via" "$found_py"
  else
    printf '{"status": "%s", "tried": "%s"}\n' "$1" "$(printf '%s' "$tried" | tr '\n"' '; ')"
  fi
  exit "$2"
}
found_py=""
if find_py; then result ok 0; fi
uv="$HOME/.local/bin/uv"
if [ "$1" = "--dry-run" ]; then
  add "would run: curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh, then $uv python install 3.12"
  result dry_run 1
fi
if [ ! -x "$uv" ]; then
  if ! command -v curl >/dev/null 2>&1; then add "curl: not found"; result no_curl 1; fi
  curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh >/dev/null 2>&1 || add "uv install: failed"
fi
if [ -x "$uv" ]; then
  "$uv" python install 3.12 >/dev/null 2>&1 || add "uv python install 3.12: failed"
else
  add "uv: not installed"
fi
if find_py; then result ok 0; fi
result not_found 1
