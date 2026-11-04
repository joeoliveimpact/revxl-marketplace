#!/bin/bash
# S1a check: every editor-superengine Python lock resolves, binary-only and hash-checked, for each platform it
# ships to, using the pinned uv and managed Python that install.sh put in a state folder (no system Python).
#   parakeet-gpu   win_amd64 (Windows + NVIDIA only by design; it has no macOS cell)
#   parakeet-cpu   win_amd64, macOS arm64 (14.0)
#   faster-whisper win_amd64, macOS arm64 (14.0), macOS x86_64 (13.0)
# "info" rows show the macOS floors and do not gate.
# usage: bash tests/editor/pip-matrix.sh <state-dir made by install.sh>     (exit 0 = every gating cell resolves)
R="$(cd "$(dirname "$0")/../.." && pwd)"; L="$R/plugins/editor-superengine/skills/editor-doctor/scripts/python"
ST="${1:?usage: pip-matrix.sh <state-dir>}"
UV="$(ls "$ST"/uv/*/uv.exe "$ST"/uv/*/uv 2>/dev/null | head -1)"
PY="$ST/venv/Scripts/python.exe"; [ -x "$PY" ] || PY="$ST/venv/bin/python"
[ -x "$UV" ] && [ -x "$PY" ] || { echo "FAIL: no uv/python in $ST (run run-py-test.sh first)"; exit 1; }
export UV_NO_CONFIG=1 UV_CACHE_DIR="$ST/cache/uv"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail=0
printf '%-15s %-26s %-6s %-5s %s\n' variant platform macos gate result
cell() { # variant uv-platform macos-target gate
  out="$(MACOSX_DEPLOYMENT_TARGET="$3" "$UV" pip install --dry-run --python "$PY" --python-platform "$2" \
    --python-version 3.12 --only-binary :all: --require-hashes -r "$L/$1.lock.txt" --target "$T/x" 2>&1)"; rc=$?
  if [ $rc -eq 0 ]; then res="resolves ($(printf '%s\n' "$out" | grep -c '^ + ') packages)"
  else why="$(printf '%s\n' "$out" | grep -m1 -i 'because' || printf '%s\n' "$out" | grep -m1 -i 'error')"
    res="FAILS: $(printf '%s' "$why" | sed 's/^ *//' | cut -c1-150)"; [ "$4" = yes ] && fail=1; fi
  printf '%-15s %-26s %-6s %-5s %s\n' "$1" "$2" "${3:--}" "$4" "$res"
}
cell parakeet-gpu   x86_64-pc-windows-msvc "" yes
cell parakeet-cpu   x86_64-pc-windows-msvc "" yes
cell parakeet-cpu   aarch64-apple-darwin  14.0 yes
cell faster-whisper x86_64-pc-windows-msvc "" yes
cell faster-whisper aarch64-apple-darwin  14.0 yes
cell faster-whisper x86_64-apple-darwin   13.0 yes
cell faster-whisper aarch64-apple-darwin  13.0 info
cell faster-whisper x86_64-apple-darwin   12.0 info
exit $fail
