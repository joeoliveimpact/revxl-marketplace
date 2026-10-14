#!/bin/bash
# Script launcher: run one of this plugin's Python scripts with this machine's Python 3, passing stdin, args and the exit code through.
# Copied from shortform-superengine's hooks/run-py.sh (same probe), so this plugin needs no other plugin.
# Tries py -3 (Windows launcher), then every python3 and python on PATH in order, and uses the first that really runs
# (a quick probe that it runs and is Python 3): the Microsoft Store stub, a py with no Python 3 behind it and a
# Python 2 (macOS 11-12.2 /usr/bin/python) fail the probe and are skipped,
# while a working Store Python passes. On a Mac, /usr/bin/python3 is skipped unless the command line tools are
# installed, so the probe never raises the install dialog.
# No working Python: print a line starting NO-PYTHON and exit 3. That line is the ONLY signal for session-closeout's
# by-hand fallback; the scripts never print it, so a script's own refusal or error can never read as "no Python".
# ponytail: the probe costs one extra interpreter start per call; cache the chosen path if that ever shows up.
# usage (skills): bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/<script>.py" [args...]
s="$1"; shift
[ -f "$s" ] || { echo "run-py.sh: script not found: $s (reinstall workspace-superengine)" >&2; exit 1; }
try() { "$@" -c 'import sys; sys.exit(sys.version_info[0] != 3)' </dev/null >/dev/null 2>&1 && exec "$@" "$s" "${args[@]}"; }
args=("$@")
p="$(command -v py 2>/dev/null)" && try "$p" -3
for c in python3 python; do
  while IFS= read -r -u 3 p; do
    [ "$p" = /usr/bin/python3 ] && [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1 && continue
    try "$p"
  done 3< <(type -ap "$c" 2>/dev/null)
done
echo "NO-PYTHON: no working Python 3 on this machine (tried py -3, python3, python)."
exit 3
