#!/bin/bash
# SKLLPLG-370 check for plugins/shortform-superengine/hooks/run-py.sh: the hook exit code passes through on
# forward-slash, backslash and mixed Windows paths; a broken interpreter (the Store stub, a py with no Python 3)
# or a Python 2 is skipped for a working one later on PATH; a working Python inside a WindowsApps folder is
# used; and no
# working Python at all exits 0 silently.  usage: bash tests/shortform/run-py-test.sh   (exit 0 = all pass)
H="$(cd "$(dirname "$0")/../../plugins/shortform-superengine/hooks" && pwd)"; T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
REAL="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
case "$REAL" in *WindowsApps*|"") REAL="$(py -3 -c 'import sys; print(sys.executable)' 2>/dev/null | tr -d '\r')";; esac
command -v cygpath >/dev/null && REAL="$(cygpath -u "$REAL")"
[ -x "$REAL" ] || { echo "SKIP: no real Python 3 found to test with"; exit 0; }
mkdir -p "$T/proj/scripts" "$T/WindowsApps" "$T/badpy" "$T/goodstore/WindowsApps" "$T/empty" "$T/py2"
echo '{}' > "$T/proj/analysis-data.json"
printf '# x\n\n## Text overlays\n| Beat | Seconds | Overlay | Visual cue |\n|---|---|---|---|\n| Hook | 0:00-0:09 | a | b |\n' > "$T/proj/scripts/x.md"
IN="{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$(cygpath -m "$T/proj/scripts/x.md" 2>/dev/null || echo "$T/proj/scripts/x.md")\"}}"
printf '#!/bin/bash\necho STUB; exit 9009\n' > "$T/WindowsApps/python3"; cp "$T/WindowsApps/python3" "$T/WindowsApps/python"
printf '#!/bin/bash\necho "No suitable Python runtime found" >&2; exit 103\n' > "$T/badpy/py"
printf '#!/bin/bash\nexec "%s" "$@"\n' "$REAL" > "$T/goodstore/WindowsApps/python3"
# A Python 2 stand-in: an empty -c runs, anything Python-3-only fails, as /usr/bin/python 2.7 does.
printf '#!/bin/bash\n[ "$1" = -c ] && [ -z "$2" ] && exit 0\necho "SyntaxError: invalid syntax" >&2; exit 1\n' > "$T/py2/python3"
chmod +x "$T/WindowsApps/"* "$T/badpy/py" "$T/goodstore/WindowsApps/python3" "$T/py2/python3"
RD="$(dirname "$REAL")"; B="$(command -v bash)"
fail=0; ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got [$2] want [$3]"; fail=1; fi; }
S=storyboard-on-write.py
ck "forward-slash paths, bad storyboard -> 2" "$(echo "$IN" | bash "$H/run-py.sh" "$H/$S" 2>/dev/null; echo $?)" 2
if command -v cygpath >/dev/null; then
  W="$(cygpath -w "$H")"; M="$(cygpath -w "$H/..")/hooks"
  ck "backslash paths -> 2" "$(echo "$IN" | bash "$W\\run-py.sh" "$W\\$S" 2>/dev/null; echo $?)" 2
  ck "mixed paths, as \${CLAUDE_PLUGIN_ROOT}/hooks on Windows -> 2" "$(echo "$IN" | bash "$M/run-py.sh" "$M/$S" 2>/dev/null; echo $?)" 2
fi
ck "no Python on PATH -> 0, silent" "$(echo "$IN" | PATH="$T/empty" "$B" "$H/run-py.sh" "$H/$S" 2>&1; echo $?)" 0
ck "only the Store stub -> 0, silent" "$(echo "$IN" | PATH="$T/WindowsApps" "$B" "$H/run-py.sh" "$H/$S" 2>&1; echo $?)" 0
ck "Store stub first, real Python later on PATH -> 2" "$(echo "$IN" | PATH="$T/WindowsApps:$RD" "$B" "$H/run-py.sh" "$H/$S" 2>/dev/null; echo $?)" 2
ck "py with no Python 3, real Python later -> 2" "$(echo "$IN" | PATH="$T/badpy:$RD" "$B" "$H/run-py.sh" "$H/$S" 2>/dev/null; echo $?)" 2
ck "Python 2 first, real Python later -> 2" "$(echo "$IN" | PATH="$T/py2:$RD" "$B" "$H/run-py.sh" "$H/$S" 2>/dev/null; echo $?)" 2
ck "a working Python inside a WindowsApps folder is used -> 2" "$(echo "$IN" | PATH="$T/goodstore/WindowsApps" "$B" "$H/run-py.sh" "$H/$S" 2>/dev/null; echo $?)" 2
exit $fail
