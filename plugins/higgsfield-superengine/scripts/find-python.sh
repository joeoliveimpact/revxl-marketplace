#!/bin/sh
# find-python.sh - find a Python >= 3.9 for higgsfield-superengine on Mac/Linux. The Mac twin of find-python.ps1.
# Same approach as the other REVXL plugins (notebooklm-superengine, course-crawler): a version check, and if Python is
# missing or too old, Homebrew installs it (brew install python@3.12). No Homebrew: status no_python, and the setup
# skill points the client to python.org. On a Mac without Apple's developer tools, the python3 check can open Apple's
# "install developer tools" box: installing from it gives a usable Python 3.9, then run this again.
# Checks python3 on PATH, then Homebrew, python.org and /usr/local (an app opened from the Dock has a short PATH).
# Run it from the client's workspace folder. On success it writes the interpreter's full path (no newline) to
# higgsfield/.python and prints one JSON line, exit 0:
#   {"status": "ok", "version": "3.12.11", "python": "/opt/homebrew/bin/python3"}
# Otherwise one JSON line, exit 1: {"status": "no_python", "brew": true|false}
# Use it as:  Bash  "$(cat higgsfield/.python)" script.py
find_py() {
  for py in "$(command -v python3 2>/dev/null)" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
            /Library/Frameworks/Python.framework/Versions/3.*/bin/python3; do
    [ -n "$py" ] && [ -x "$py" ] || continue
    if "$py" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
      "$py" -c 'import json, os, sys
os.makedirs("higgsfield", exist_ok=True)
with open(os.path.join("higgsfield", ".python"), "w", encoding="utf-8", newline="") as f:
    f.write(sys.executable)
print(json.dumps({"status": "ok", "version": "%d.%d.%d" % sys.version_info[:3], "python": sys.executable}))'
      exit 0
    fi
  done
}
find_py
for brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  if [ -x "$brew" ]; then
    "$brew" install python@3.12 >/dev/null 2>&1
    find_py
    echo '{"status": "no_python", "brew": true}'; exit 1
  fi
done
echo '{"status": "no_python", "brew": false}'; exit 1
