#!/bin/bash
# Hook launcher: run a hook's Python script with this machine's Python 3, passing stdin, args and the exit code through.
# Tries py -3 (Windows launcher), then every python3 and python on PATH in order, and uses the first that really runs
# (a quick probe that it runs and is Python 3): the Microsoft Store stub, a py with no Python 3 behind it and a
# Python 2 (macOS 11-12.2 /usr/bin/python) fail the probe and are skipped,
# while a working Store Python passes. On a Mac, /usr/bin/python3 is skipped unless the command line tools are
# installed, so the hook never raises the install dialog. No working Python: exit 0 silently, so every hook fails
# open (SKLLPLG-370; live 0.4.1 hooks needed only bash and node).
# ponytail: the probe costs one extra interpreter start per hook; cache the chosen path if that ever shows up.
# usage (hooks.json): bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"
s="$1"; shift
try() { "$@" -c 'import sys; sys.exit(sys.version_info[0] != 3)' </dev/null >/dev/null 2>&1 && exec "$@" "$s" "${args[@]}"; }
args=("$@")
p="$(command -v py 2>/dev/null)" && try "$p" -3
for c in python3 python; do
  while IFS= read -r -u 3 p; do
    [ "$p" = /usr/bin/python3 ] && [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1 && continue
    try "$p"
  done 3< <(type -ap "$c" 2>/dev/null)
done
exit 0
