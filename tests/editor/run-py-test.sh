#!/bin/bash
# S1a check for plugins/editor-superengine/skills/editor-doctor/scripts/install.sh, patterned on
# tests/shortform/run-py-test.sh (its fake-Store-Python technique). With PATH stripped (a fake WindowsApps folder whose python/python3/py stubs
# exit 9009 comes first; then only the system dirs bash needs; no real python/py/node/ffmpeg/uv) and HOME,
# APPDATA, LOCALAPPDATA and TEMP pointed into scratch, install.sh runs unattended into <scratch>/state and:
# exit 0; managed Python + venv; node at the pin; local HyperFrames 0.8.184; ffmpeg with zscale; Chrome at the pin;
# every model file's sha256; the engine's imports; a ✓ + non-ASCII file name under captured stdout (TRI-1);
# a real Parakeet run on a short clip with its provider (Parakeet engines; CUDA required on parakeet-gpu);
# a second install.sh run is a no-op that still exits 0.
# usage: bash tests/editor/run-py-test.sh <scratch-dir> [auto|parakeet-gpu|parakeet-cpu|faster-whisper] [speech-clip]
#        (exit 0 = all pass; the clip is only needed for the Parakeet run, and is never shipped)
R="$(cd "$(dirname "$0")/../.." && pwd)"; P="$R/plugins/editor-superengine"
S="${1:?usage: run-py-test.sh <scratch-dir> [engine] [speech-clip]}"; ENGINE="${2:-auto}"; CLIP="${3:-}"
mkdir -p "$S" && S="$(cd "$S" && pwd)"
command -v cygpath >/dev/null && { S="$(cygpath -m "$S")"; R="$(cygpath -m "$R")"; P="$R/plugins/editor-superengine"; }
T="$S/t"; ST="$S/state"; rm -rf "$T"; mkdir -p "$T/WindowsApps" "$T/home" "$T/appdata" "$T/localappdata" "$T/tmp" "$T/utf8"
for n in python python3 py; do printf '#!/bin/bash\necho STUB; exit 9009\n' > "$T/WindowsApps/$n"; done
chmod +x "$T/WindowsApps/"*
if command -v cygpath >/dev/null; then SYS="/usr/bin:/bin:$(cygpath -u "${SYSTEMROOT:-C:\\Windows}")/System32"
else SYS="/usr/bin:/bin:/usr/sbin:/sbin"; fi
SP="$(command -v cygpath >/dev/null && cygpath -u "$T" || echo "$T")/WindowsApps:$SYS"  # PATH needs POSIX form (C: has a colon)
w() { command -v cygpath >/dev/null && cygpath -w "$1" || echo "$1"; }
iso() { env -u PYTHONPATH -u PYTHONHOME -u PYTHONUTF8 -u PYTHONIOENCODING -u VIRTUAL_ENV -u NODE_OPTIONS -u UV_CACHE_DIR -u UV_PYTHON_INSTALL_DIR \
  PATH="$SP" HOME="$T/home" USERPROFILE="$(w "$T/home")" APPDATA="$(w "$T/appdata")" LOCALAPPDATA="$(w "$T/localappdata")" \
  TEMP="$(w "$T/tmp")" TMP="$(w "$T/tmp")" EDITOR_SE_HOME="$ST" "$@"; }
fail=0; ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got [$2] want [$3]"; fail=1; fi; }

# The stubs exit 9009 like the real Store stub; bash keeps the low 8 bits, so the caller sees 49.
ck "stripped PATH: python is the Store stub" "$(iso python -c 1 2>/dev/null) $(iso python -c 1 >/dev/null 2>&1; echo $?)" "STUB 49"
ck "stripped PATH: py is the Store stub" "$(iso py -3 -c 1 2>/dev/null) $(iso py -3 -c 1 >/dev/null 2>&1; echo $?)" "STUB 49"
ck "stripped PATH: no node, ffmpeg or uv" "$(iso sh -c 'command -v node ffmpeg uv' | wc -l | tr -d ' ')" 0
REG0="$(command -v reg >/dev/null && reg query 'HKCU\Software\Python' 2>/dev/null | tr -d '\r' | sort)"

INS="$P/skills/editor-doctor/scripts/install.sh"
iso sh "$INS" --engine "$ENGINE" > "$S/run1.log" 2>&1; rc=$?
cat "$S/run1.log"
ck "install.sh run 1 exits 0" "$rc" 0
VPY="$ST/venv/Scripts/python.exe"; [ -x "$VPY" ] || VPY="$ST/venv/bin/python"
# Every probe below runs the managed venv python in the stripped environment with the plugin's env builders.
vp() { iso "$VPY" -X utf8 -I -c "import sys; sys.path.insert(0, r'$P/skills/_shared'); import runtime as rt, subprocess, json, hashlib, os
$1"; }
ck "managed Python 3.12.16 runs the venv, outside any system Python" \
  "$(vp "import platform; print(platform.python_version(), sys.base_prefix.replace(chr(92),'/').startswith(r'$ST/python'), sys.prefix.replace(chr(92),'/') == r'$ST/venv')" | tr -d '\r')" "3.12.16 True True"
ck "node --version is the pin" "$(vp "print(subprocess.run([rt.tool('node'), '--version'], capture_output=True, text=True).stdout.strip())" | tr -d '\r')" v22.23.4
ck "local HyperFrames CLI reports 0.8.184" \
  "$(vp "print(subprocess.run(rt.hyperframes_cmd('--version'), capture_output=True, text=True, env=rt.hyperframes_env()).stdout.strip().splitlines()[-1])" | tr -d '\r')" 0.8.184
ck "ffmpeg has zscale and tonemap" "$(vp "o = subprocess.run([rt.tool('ffmpeg'), '-hide_banner', '-filters'], capture_output=True, text=True).stdout; print(' zscale ' in o, ' tonemap ' in o)" | tr -d '\r')" "True True"
ck "chrome-headless-shell present at the pin" \
  "$(vp "s = rt.load_state(); print(os.path.isfile(rt.tool('chrome')), s['components']['chrome']['version'], '152.0.7977.30' in s['components']['chrome']['files'][0]['url'])" | tr -d '\r')" "True 152.0.7977.30 True"
ck "every model file's sha256 matches the pin" "$(vp "
s = rt.load_state(); bad = []; n = 0
def h(p):
    x = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): x.update(b)
    return x.hexdigest()
for name, m in s['models'].items():
    files = m['files'] if 'files' in m else {os.path.basename(m['url']): m['sha256']}
    for f, sha in files.items():
        n += 1
        if h(os.path.join(rt.state_dir(), m['dir'], f)) != sha: bad.append(f)
print(n > 0 and not bad, sorted(s['models']), bad)" | tr -d '\r' | cut -d' ' -f1)" True
ck "with no override the state folder follows the OS rule" \
  "$(iso env -u EDITOR_SE_HOME "$VPY" -X utf8 -I -c "import sys; sys.path.insert(0, r'$P/skills/_shared'); import runtime; print(runtime.state_dir())" | tr -d '\r')" \
  "$(vp "print(os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~/Library/Application Support'), 'revxl', 'editor-superengine'))" | tr -d '\r')"
vp "s = rt.load_state(); print('models:', {k: sorted(v.get('files', {'u2net_human_seg.onnx': 1})) for k, v in s['models'].items()})"
EN="$(vp "print(rt.load_state()['engine'])" | tr -d '\r')"
echo "engine: $EN ($(vp "print(rt.load_state()['engine_reason'])" | tr -d '\r')); align_words: $(vp "print(rt.load_state().get('align_words'))" | tr -d '\r')"
[ "$ENGINE" = auto ] || ck "engine is the one asked for" "$EN" "$ENGINE"
case "$EN" in faster-whisper) IMP="import faster_whisper, ctranslate2, onnxruntime, torch, transformers" ;;
  *) IMP="import onnx_asr, onnxruntime, torch, transformers" ;; esac
ck "venv imports: $IMP" "$(iso "$VPY" -c "$IMP; print('ok')" 2>&1 | tr -d '\r' | tail -1)" ok
iso "$VPY" "$R/tests/editor/smoke_utf8.py" "$T/utf8" > "$S/utf8-captured.txt" 2>&1; rc=$?
ck "TRI-1 smoke under captured stdout (no PYTHONUTF8): exit 0, one ✓, the non-ASCII name" \
  "$rc $(grep -c '✓' "$S/utf8-captured.txt") $(grep -c 'café ✓ 日本.txt' "$S/utf8-captured.txt")" "0 1 1"
ck "TRI-1: the file name on disk is café ✓ 日本.txt" "$(ls "$T/utf8")" "café ✓ 日本.txt"

if [ "${EN#parakeet}" != "$EN" ]; then
  if [ -z "$CLIP" ]; then echo "FAIL Parakeet run: no speech clip given"; fail=1
  else
    rm -f "$S/clip.wav"
    vp "subprocess.run([rt.tool('ffmpeg'), '-v', 'error', '-y', '-ss', '0', '-t', '4', '-i', r'$CLIP', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', r'$S/clip.wav'], check=True)"
    vp "r = subprocess.run([rt.tool('python'), r'$R/tests/editor/parakeet_smoke.py', r'$S/clip.wav'], capture_output=True, text=True, encoding='utf-8', env=rt.python_env()); print(r.stdout.strip()); print(r.stderr[-600:], file=sys.stderr); sys.exit(r.returncode)" > "$S/parakeet.json" 2> "$S/parakeet.err"; rc=$?
    cat "$S/parakeet.json"
    ck "Parakeet run returns words" "$rc $(vp "print(json.load(open(r'$S/parakeet.json', encoding='utf-8'))['words'] > 0)" | tr -d '\r')" "0 True"
    PROV="$(vp "print(','.join(json.load(open(r'$S/parakeet.json', encoding='utf-8'))['providers']))" | tr -d '\r')"
    echo "Parakeet provider: $PROV"
    [ "$EN" = parakeet-gpu ] && ck "parakeet-gpu ran on CUDA" "$PROV" CUDAExecutionProvider
  fi
fi

iso sh "$INS" --engine "$ENGINE" > "$S/run2.log" 2>&1; rc=$?
cat "$S/run2.log"
ck "install.sh run 2 exits 0" "$rc" 0
ck "run 2 is a no-op (no download or install lines)" "$(grep -cE '^(Downloading|Installing)' "$S/run2.log")" 0
ck "nothing linked into HOME/.local/bin" "$(ls -A "$T/home/.local/bin" 2>/dev/null | wc -l | tr -d ' ')" 0
command -v reg >/dev/null && ck "Windows registry Python keys unchanged (no uv registration)" \
  "$(reg query 'HKCU\Software\Python' 2>/dev/null | tr -d '\r' | sort)" "$REG0"
exit $fail
