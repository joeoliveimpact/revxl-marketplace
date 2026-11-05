#!/bin/bash
# S1b check (spec :120 done-test) for plugins/editor-superengine/skills/editor-doctor/scripts/check_deps.py.
# Works on COPIES of two installed state folders (the originals are never touched):
#   <gpu-state> = an S1a state with parakeet-gpu installed, <fw-state> = one with faster-whisper installed.
# Checks: --selftest passes; Linux gets the plain line and a clean exit (fake uname); every missing dep prints
# its STATUS line and its plain fix (a state folder holding only state.json); Resolve masked -> nle none;
# unmasked -> engine parakeet-gpu and nle = what detection finds; GPU masked -> parakeet-cpu; Parakeet masked
# -> faster-whisper plus the retake warning. Each workspace is a scratch folder used as the cwd.
# S1b-fix: a fake nvidia-smi first on PATH that times out, exits non-zero or prints garbage keeps parakeet-gpu, the
# venv's package set and prints the STATUS gpu warn; GPU masked (a successful no-GPU read) re-picks; --repick forces a
# re-pick; --set-nle mcp survives a re-run, --set-nle auto returns to detection, a config without nle_source is auto.
# Round 2: on the fw copy's recorded fallback (written by the Parakeet-masked case), a re-run keeps faster-whisper;
# --repick retries Parakeet (masked again), falls back again with the retake warning and exits 0.
# usage: bash tests/editor/doctor-test.sh <scratch-dir> <gpu-state> <fw-state>      (exit 0 = all pass)
R="$(cd "$(dirname "$0")/../.." && pwd)"
S="${1:?usage: doctor-test.sh <scratch-dir> <gpu-state> <fw-state>}"; GSRC="${2:?gpu-state}"; FSRC="${3:?fw-state}"
mkdir -p "$S" && S="$(cd "$S" && pwd)"
command -v cygpath >/dev/null && { S="$(cygpath -m "$S")"; R="$(cygpath -m "$R")"; }
P="$R/plugins/editor-superengine"; D="$P/skills/editor-doctor/scripts/check_deps.py"; INS="$P/skills/editor-doctor/scripts/install.sh"
fail=0; ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got [$2] want [$3]"; fail=1; fi; }
vpy() { if [ -x "$1/venv/Scripts/python.exe" ]; then echo "$1/venv/Scripts/python.exe"; else echo "$1/venv/bin/python"; fi; }
# copy SRC DEST: a full copy whose venv points at its own copied base Python (pyvenv.cfg home).
copy() {
  rm -rf "$2"; cp -r "$1" "$2" || return 1
  local base; base="$(ls -d "$2"/python/cpython-3.12.16-* | head -1)"
  "$base/python.exe" -I -c "import sys, re; p = sys.argv[1]; s = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8', newline='\n').write(re.sub(r'(?m)^home = .*$', lambda m: 'home = ' + sys.argv[2], s))" \
    "$2/venv/pyvenv.cfg" "$(command -v cygpath >/dev/null && cygpath -w "$base" || echo "$base")" 2>/dev/null \
  || "$base/bin/python3" -I -c "import sys, re; p = sys.argv[1]; s = open(p).read(); open(p, 'w').write(re.sub(r'(?m)^home = .*$', 'home = ' + sys.argv[2] + '/bin', s))" "$2/venv/pyvenv.cfg" "$base"
}
# doc STATE WS [VAR=value ...] -- [doctor args]: runs the doctor with WS as cwd and STATE as the state folder.
doc() {
  local st="$1" ws="$2"; shift 2; local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  [ -n "${KEEP:-}" ] || { rm -rf "$ws"; mkdir -p "$ws"; }  # KEEP=1 doc ...: re-run in the same workspace
  (cd "$ws" && env EDITOR_SE_HOME="$st" LOCALAPPDATA="$LADW" "${envs[@]}" "$(vpy "$A")" -B -X utf8 -I "$D" "$@")
}
cfg() { "$(vpy "$A")" -B -I -c "import json, sys; print(json.load(open(sys.argv[1], encoding='utf-8'))[sys.argv[2]])" "$1/editor/editor.config.json" "$2" | tr -d '\r'; }
# st STATE: the recorded engine and the cached GPU fact from state.json (S1b-fix)
st() { "$(vpy "$A")" -B -I -c "import json, sys; d = json.load(open(sys.argv[1], encoding='utf-8')); print(d['engine'], d.get('pick_facts', {}).get('gpu'))" "$1/state.json" | tr -d '\r'; }
# pkgs STATE: the venv's installed package set (name==version), sorted
pkgs() { "$(vpy "$1")" -B -I -c 'import importlib.metadata as m; print(chr(10).join(sorted(d.metadata["Name"] + "==" + d.version for d in m.distributions())))' | tr -d '\r'; }
# fake_smi DIR timeout|nonzero|garbage: a fake nvidia-smi (.cmd on Windows) for the flaky-read cases
fake_smi() {
  rm -rf "$1"; mkdir -p "$1"
  if command -v cygpath >/dev/null; then
    case "$2" in timeout) printf '@ping -n 26 127.0.0.1 >nul\n' ;; nonzero) printf '@echo NVIDIA-SMI has failed because it could not communicate with the NVIDIA driver.\n@exit /b 9\n' ;;
      garbage) printf '@echo zz9 qq garbled 0x00\n' ;; esac > "$1/nvidia-smi.cmd"
  else
    case "$2" in timeout) printf '#!/bin/sh\nsleep 25\n' ;; nonzero) printf '#!/bin/sh\necho NVIDIA-SMI has failed; exit 9\n' ;;
      garbage) printf '#!/bin/sh\necho zz9 qq garbled 0x00\n' ;; esac > "$1/nvidia-smi"; chmod +x "$1/nvidia-smi"
  fi
}

A="$S/state-gpu"; B="$S/state-fw"
# doc()'s LOCALAPPDATA: a setup run by the doctor leaves home-pointer.txt here, never in the real app data
mkdir -p "$S/lad"; LADW="$(command -v cygpath >/dev/null && cygpath -w "$S/lad" || echo "$S/lad")"
echo "copying $GSRC -> $A and $FSRC -> $B ..."
copy "$GSRC" "$A" && copy "$FSRC" "$B" || { echo "FAIL could not copy the state folders"; exit 1; }

"$(vpy "$A")" -B -X utf8 -I "$D" --selftest > "$S/selftest.log" 2>&1; rc=$?; cat "$S/selftest.log"
ck "--selftest exits 0" "$rc" 0

mkdir -p "$S/fake-linux"; printf '#!/bin/sh\ncase "$1" in -m) echo x86_64 ;; *) echo Linux ;; esac\n' > "$S/fake-linux/uname"; chmod +x "$S/fake-linux/uname"
rm -rf "$S/linux-state"
FL="$(command -v cygpath >/dev/null && cygpath -u "$S/fake-linux" || echo "$S/fake-linux")"  # PATH needs POSIX form (C: has a colon)
if [ "$(env PATH="$FL:$PATH" uname -s)" != Linux ]; then echo "FAIL the fake uname is not first on PATH (Linux case not run)"; fail=1
else
  out="$(env PATH="$FL:$PATH" EDITOR_SE_HOME="$S/linux-state" sh "$INS" 2>&1)"; rc=$?; echo "$out"
  ck "Linux: plain line, clean exit, no state folder (nothing downloaded)" "$out|$rc|$([ -e "$S/linux-state" ] && echo made || echo none)" \
    "Linux isn't supported yet (Windows and macOS are).|0|none"
fi

M="$S/state-missing"; rm -rf "$M"; mkdir -p "$M"; cp "$A/state.json" "$M/"
doc "$M" "$S/ws-missing" -- --no-install > "$S/missing.log" 2>&1; rc=$?; cat "$S/missing.log"
ck "every dep missing -> exit 1" "$rc" 1
bad="$(awk '/^STATUS [^ ]+ missing /{c=$2; getline n; if (n !~ ("^FIX " c " Claude re-runs the setup: sh \".*install.sh\" --engine ")) print c} ' "$S/missing.log" | tr '\n' ' ')"
ck "each missing dep's STATUS line is followed by its plain fix (the exact setup command)" "$bad" ""
ck "missing lines cover every installed component" \
  "$(grep -oE '^STATUS (python|ffmpeg|node|hyperframes|chrome|cutout-model|transcriber|model-[a-z-]+|align|engine) missing' "$S/missing.log" | wc -l | tr -d ' ')" 10

doc "$A" "$S/ws-resolve-masked" EDITOR_SE_MASK=resolve -- --no-install > "$S/resolve-masked.log" 2>&1; rc=$?; cat "$S/resolve-masked.log"
ck "Resolve masked -> nle none (exit $rc)" "$(cfg "$S/ws-resolve-masked" nle)" none

doc "$A" "$S/ws-unmasked" -- > "$S/unmasked.log" 2>&1; rc=$?; cat "$S/unmasked.log"
ck "unmasked doctor exits 0" "$rc" 0
ck "unmasked: engine parakeet-gpu" "$(cfg "$S/ws-unmasked" engine)" parakeet-gpu
NLE="$(cfg "$S/ws-unmasked" nle)"; WANT=none
[ "$(grep -cE '^STATUS resolve-(installed|edition|version|scripting) ok ' "$S/unmasked.log")" = 4 ] && WANT=resolve
ck "unmasked: nle is what detection finds ($NLE)" "$NLE" "$WANT"
ck ".platform.json written with the stamp" "$("$(vpy "$A")" -B -I -c "import json, sys; d = json.load(open(sys.argv[1], encoding='utf-8')); print(d['stamp']['steps'], d['engine']['installed'], len(d['status']) > 0)" "$S/ws-unmasked/editor/.platform.json" | tr -d '\r')" "S1a+S1b parakeet-gpu True"
ck "saved-style skeleton created" "$(cat "$A/styles/default.json")" '{"schema":1,"style_id":null,"accent":null,"font":null,"look":null,"transitions":{"allowed":[],"sfx_pair":null}}'

# S1b-fix: a flaky GPU read keeps the engine (the unmasked run above cached the facts beside parakeet-gpu)
FS="$(command -v cygpath >/dev/null && cygpath -u "$S/fake-smi" || echo "$S/fake-smi")"  # PATH needs POSIX form
ck "cache seeded by the unmasked run" "$(st "$A")" "parakeet-gpu True"
pkgs "$A" > "$S/pkgs-before.txt"; echo "venv packages before: $(wc -l < "$S/pkgs-before.txt")"
for kind in timeout nonzero garbage; do
  fake_smi "$S/fake-smi" "$kind"
  which="$(env PATH="$FS:$PATH" "$(vpy "$A")" -B -I -c "import shutil; print(shutil.which('nvidia-smi'))" | tr -d '\r')"
  case "$which" in *fake-smi*) ;; *) echo "FAIL the fake nvidia-smi is not first on PATH ($which)"; fail=1; continue ;; esac
  doc "$A" "$S/ws-flaky-$kind" PATH="$FS:$PATH" -- > "$S/flaky-$kind.log" 2>&1; rc=$?; cat "$S/flaky-$kind.log"
  pkgs "$A" > "$S/pkgs-$kind.txt"
  ck "flaky GPU read ($kind): exit 0, engine stays parakeet-gpu (config, state.json)" "$rc $(cfg "$S/ws-flaky-$kind" engine) $(st "$A")" "0 parakeet-gpu parakeet-gpu True"
  ck "flaky GPU read ($kind): the venv's package set is unchanged" "$(cmp -s "$S/pkgs-before.txt" "$S/pkgs-$kind.txt" && echo same)" same
  ck "flaky GPU read ($kind): STATUS gpu warn (engine kept) + its FIX; no package install" \
    "$(grep -cx "STATUS gpu warn The NVIDIA graphics card check didn't answer this time, so the editor kept its current transcriber (parakeet-gpu)." "$S/flaky-$kind.log") $(grep -c '^FIX gpu ' "$S/flaky-$kind.log") $(grep -c '^Installing the Python packages' "$S/flaky-$kind.log")" "1 1 0"
done

# S1b-fix: a manual nle survives re-runs; auto returns to detection; a config without nle_source counts as auto
doc "$A" "$S/ws-nle" -- --set-nle mcp > "$S/set-nle-mcp.log" 2>&1; rc=$?; cat "$S/set-nle-mcp.log"
KEEP=1 doc "$A" "$S/ws-nle" -- --no-install > "$S/nle-manual.log" 2>&1; rc2=$?; cat "$S/nle-manual.log"
ck "--set-nle mcp, then a re-run (Resolve detection: $(grep -cE '^STATUS resolve-(installed|edition|version|scripting) ok ' "$S/nle-manual.log")/4 ok) -> mcp / manual, chosen by you" \
  "$rc $rc2 $(cfg "$S/ws-nle" nle) $(cfg "$S/ws-nle" nle_source) $(grep -c '^STATUS nle ok mcp (chosen by you' "$S/nle-manual.log")" "0 0 mcp manual 1"
KEEP=1 doc "$A" "$S/ws-nle" -- --set-nle auto > "$S/set-nle-auto.log" 2>&1; rc=$?; cat "$S/set-nle-auto.log"
KEEP=1 doc "$A" "$S/ws-nle" EDITOR_SE_MASK=resolve -- --no-install > "$S/nle-auto.log" 2>&1; rc2=$?; cat "$S/nle-auto.log"
ck "--set-nle auto, then a re-run with Resolve masked -> none / auto" "$rc $rc2 $(cfg "$S/ws-nle" nle) $(cfg "$S/ws-nle" nle_source)" "0 0 none auto"
rm -rf "$S/ws-nle-old"; mkdir -p "$S/ws-nle-old/editor"; printf '{"schema": 1, "nle": "mcp"}\n' > "$S/ws-nle-old/editor/editor.config.json"
KEEP=1 doc "$A" "$S/ws-nle-old" EDITOR_SE_MASK=resolve -- --no-install > "$S/nle-old.log" 2>&1; rc=$?; cat "$S/nle-old.log"
ck "a config without nle_source counts as auto -> none / auto" "$rc $(cfg "$S/ws-nle-old" nle) $(cfg "$S/ws-nle-old" nle_source)" "0 none auto"

doc "$A" "$S/ws-gpu-masked" EDITOR_SE_MASK=gpu -- > "$S/gpu-masked.log" 2>&1; rc=$?; cat "$S/gpu-masked.log"
ck "GPU masked -> exit 0, engine parakeet-cpu" "$rc $(cfg "$S/ws-gpu-masked" engine)" "0 parakeet-cpu"
ck "real change (a successful no-GPU read) re-picked: state.json engine + cached GPU fact" "$(st "$A")" "parakeet-cpu False"

# S1b-fix: --repick forces a re-pick. An explicit setup records parakeet-gpu with the same facts (GPU masked); a plain
# doctor run keeps it, the same run with --repick picks again (parakeet-cpu).
rm -rf "$S/ws-repick"; mkdir -p "$S/ws-repick"
(mkdir -p "$S/lad" "$S/home" && cd "$S/ws-repick" && env EDITOR_SE_HOME="$A" LOCALAPPDATA="$(command -v cygpath >/dev/null && cygpath -w "$S/lad" || echo "$S/lad")" HOME="$S/home" EDITOR_SE_MASK=gpu sh "$INS" --engine parakeet-gpu) > "$S/repick-setup.log" 2>&1; rc=$?; cat "$S/repick-setup.log"
ck "explicit setup --engine parakeet-gpu (GPU masked) exits 0" "$rc $(st "$A")" "0 parakeet-gpu False"
KEEP=1 doc "$A" "$S/ws-repick" EDITOR_SE_MASK=gpu -- > "$S/norepick.log" 2>&1; rc=$?; cat "$S/norepick.log"
ck "same facts, no --repick: the engine is kept (parakeet-gpu)" "$rc $(cfg "$S/ws-repick" engine) $(grep -c '^Installing the Python packages' "$S/norepick.log")" "0 parakeet-gpu 0"
KEEP=1 doc "$A" "$S/ws-repick" EDITOR_SE_MASK=gpu -- --repick > "$S/repick.log" 2>&1; rc=$?; cat "$S/repick.log"
ck "--repick: picked again -> parakeet-cpu" "$rc $(cfg "$S/ws-repick" engine) $(st "$A")" "0 parakeet-cpu parakeet-cpu False"

doc "$B" "$S/ws-parakeet-masked" EDITOR_SE_MASK=parakeet -- > "$S/parakeet-masked.log" 2>&1; rc=$?; cat "$S/parakeet-masked.log"
ck "Parakeet masked -> exit 0, engine faster-whisper" "$rc $(cfg "$S/ws-parakeet-masked" engine)" "0 faster-whisper"
ck "Parakeet masked -> the retake warning shows" \
  "$(grep -q '^FIX engine On this computer the editor uses its backup transcriber. It can drop a retake' "$S/parakeet-masked.log" && echo shown)" shown

# S1b-fix round 2: the case above recorded the fallback in B's state.json (the code's own write, no hand edit)
ck "recorded fallback in state.json" "$("$(vpy "$A")" -B -I -c "import json, sys; d = json.load(open(sys.argv[1], encoding='utf-8')); print(d['engine'], '|', d['engine_reason'], '|', d['pick_facts']['gpu'])" "$B/state.json" | tr -d '\r')" \
  "faster-whisper | backup: parakeet-gpu failed to install | True"
KEEP=1 doc "$B" "$S/ws-parakeet-masked" EDITOR_SE_MASK=parakeet -- > "$S/fallback-keep.log" 2>&1; rc=$?; cat "$S/fallback-keep.log"
ck "recorded fallback, no --repick: Parakeet not retried, faster-whisper kept" \
  "$rc $(grep -c 'test mask: Parakeet is made uninstallable' "$S/fallback-keep.log") $(cfg "$S/ws-parakeet-masked" engine)" "0 0 faster-whisper"
KEEP=1 doc "$B" "$S/ws-parakeet-masked" EDITOR_SE_MASK=parakeet -- --repick > "$S/fallback-repick.log" 2>&1; rc=$?; cat "$S/fallback-repick.log"
ck "recorded fallback + --repick: Parakeet retried (pick line, mask refusal, switch line), exit 0, ends on faster-whisper" \
  "$rc $(grep -c '^Transcription engine: parakeet-gpu ' "$S/fallback-repick.log") $(grep -c '^(test mask: Parakeet is made uninstallable)' "$S/fallback-repick.log") $(grep -c '^Parakeet would not install on this computer' "$S/fallback-repick.log") $(cfg "$S/ws-parakeet-masked" engine)" \
  "0 1 1 1 faster-whisper"
ck "recorded fallback + --repick: the retake warning prints (setup ⚠ line and FIX engine)" \
  "$(grep -c '^⚠ On this computer the editor uses its backup transcriber' "$S/fallback-repick.log") $(grep -c '^FIX engine On this computer the editor uses its backup transcriber' "$S/fallback-repick.log")" "1 1"
exit $fail
