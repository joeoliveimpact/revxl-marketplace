#!/bin/bash
# H-S1a-path check for install.sh's long-folder guard (Windows only; prints SKIP elsewhere).
# A 241-character EDITOR_SE_HOME, and 116 (the first length over the limit), must print the one refuse line,
# exit 1 and create nothing. A 115-character one must get past the guard: that path is itself a plain file, so
# the next step (mkdir) fails at once. PATH holds no curl, so an install.sh without the guard fails fast and offline.
# usage: bash tests/editor/deep-root-test.sh <scratch-dir>    (exit 0 = all pass)
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) ;; *) echo "SKIP not Windows"; exit 0 ;; esac
R="$(cd "$(dirname "$0")/../.." && pwd)"; INS="$(cygpath -m "$R")/plugins/editor-superengine/skills/editor-doctor/scripts/install.sh"
S="${1:?usage: deep-root-test.sh <scratch-dir>}"; mkdir -p "$S" && S="$(cygpath -m "$(cd "$S" && pwd)")"
rm -rf "$S/r" "$S/q" "$S/file"
fail=0; ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got [$2] want [$3]"; fail=1; fi; }
# root N BASE: a path exactly N characters long under BASE
root() { p="$2/"; while [ ${#p} -lt "$1" ]; do p="${p}x"; done; printf '%s' "$p"; }
ins() { PATH=/usr/bin:/bin EDITOR_SE_HOME="$1" sh "$INS" 2>&1; }

for n in 241 116; do
  rm -rf "$S/r"; d="$(root "$n" "$S/r")"; out="$(ins "$d")"; rc=$?
  ck "$n-character folder: exit 1" "$rc" 1
  ck "$n-character folder: the one refuse line" "$out" \
    "✗ Editor setup: this install folder is $n characters long, and Windows only allows 115 here. Re-run the setup with EDITOR_SE_HOME set to a shorter folder, such as C:\\revxl-es."
  ck "$n-character folder: nothing created" "$([ -e "$S/r" ] && echo yes || echo no)" no
done
mkdir -p "$S/q"; d="$(root 115 "$S/q")"; : > "$d"  # the 115-character path is a plain file: cygpath keeps it, mkdir under it fails
out="$(ins "$d")"; rc=$?
ck "115-character folder gets past the guard (stops at the next step, mkdir)" \
  "$rc $(printf '%s\n' "$out" | grep -c 'characters long') $(printf '%s\n' "$out" | grep -c 'could not create its folder')" "1 0 1"
exit $fail
