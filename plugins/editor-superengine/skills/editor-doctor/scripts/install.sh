#!/bin/sh
# editor-superengine setup (F1). Runs unattended once Claude starts it: Git Bash on Windows, sh/zsh on macOS.
# Needs only curl, tar, unzip and sha256sum (shasum on macOS); never a system Python, Node or ffmpeg.
#   1. downloads a pinned, hash-checked uv into the state folder
#   2. uv installs a private Python 3.12 there and makes the isolated venv
#   3. hands off to install.py (inside that venv) for Node, ffmpeg, HyperFrames, Chrome, Python packages, models
# State folder: Windows %LOCALAPPDATA%/revxl/editor-superengine, macOS ~/Library/Application Support/revxl/
# editor-superengine, Linux ${XDG_DATA_HOME:-~/.local/share}/revxl/editor-superengine; EDITOR_SE_HOME overrides.
# Usage: sh install.sh [--engine auto|parakeet-gpu|parakeet-cpu|faster-whisper] [--repick]    Re-running skips what
# is in place. auto keeps the recorded engine unless the machine facts changed; --repick picks again (install.py).
set -u
UV_VERSION=0.13.6
PY_VERSION=3.12.16

say() { printf '%s\n' "$*"; }
fail() { printf '%s\n' "✗ Editor setup: $*"; exit 1; }

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || fail "could not find its own folder. Reinstall the editor plugin."
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) OS=win ;;
  Darwin) OS=mac ;;
  Linux) OS=linux ;;
  *) OS=other ;;
esac
ARCH=$(uname -m)
# A Rosetta shell on Apple Silicon reports x86_64; install the native build.
if [ "$OS" = mac ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null)" = 1 ]; then ARCH=arm64; fi

if [ -n "${EDITOR_SE_HOME:-}" ]; then STATE=$EDITOR_SE_HOME
elif [ "$OS" = win ]; then
  [ -n "${LOCALAPPDATA:-}" ] || fail "Windows did not say where app data lives (LOCALAPPDATA is empty). Restart Claude and run the setup again."
  STATE="$LOCALAPPDATA/revxl/editor-superengine"
elif [ "$OS" = mac ]; then STATE="$HOME/Library/Application Support/revxl/editor-superengine"
else STATE="${XDG_DATA_HOME:-$HOME/.local/share}/revxl/editor-superengine"
fi
# H-S1a-path-3 (hub 11.04.26): with no EDITOR_SE_HOME, follow the home-pointer.txt an earlier setup left in the default
# folder when it names a folder holding an install (runtime.state_dir() does the same), so a re-run isn't refused.
if [ -z "${EDITOR_SE_HOME:-}" ] && [ -f "$STATE/home-pointer.txt" ]; then
  P=$(tr -d '\r\n' < "$STATE/home-pointer.txt")
  if [ -n "$P" ] && [ -f "$P/state.json" ]; then STATE=$P; fi
fi
if [ "$OS" = win ] && command -v cygpath >/dev/null 2>&1; then
  STATE=$(cygpath -m "$STATE"); HERE=$(cygpath -m "$HERE")
fi
# H-S1a-3 (hub 11.04.26): Linux keeps its state-folder rule above but gets no downloads; a plain line, a clean exit.
if [ "$OS" = linux ]; then say "Linux isn't supported yet (Windows and macOS are)."; exit 0; fi
# H-S1a-path (hub 11.04.26): Windows stops at 259 characters without long-path support, and the deepest file the
# setup unpacks (Node.js 22.23.4's npm) sits 143 below the state folder, so a folder over 115 breaks the install.
# Refuse it before anything is created. Re-measure when the Node pin changes.
if [ "$OS" = win ] && [ "${#STATE}" -gt 115 ]; then
  fail "this install folder is ${#STATE} characters long, and Windows only allows 115 here. Re-run the setup with EDITOR_SE_HOME set to a shorter folder, such as C:\\revxl-es."
fi

case "$OS-$ARCH" in
  win-x86_64) UV_ASSET=uv-x86_64-pc-windows-msvc.zip
    UV_SHA=a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f; UV_EXE=uv.exe ;;
  mac-arm64) UV_ASSET=uv-aarch64-apple-darwin.tar.gz
    UV_SHA=60fbd5c8a1ed681845eea28d9d622fcde03c51e91a43465b64a1e17db1ed3472; UV_EXE=uv ;;
  mac-x86_64) UV_ASSET=uv-x86_64-apple-darwin.tar.gz
    UV_SHA=63ba17fdda55ad1a230d4b37fc6017ffa10c23688c83818bd3bfdf914c652a02; UV_EXE=uv ;;
  *) fail "this computer ($OS $ARCH) isn't supported yet. The editor setup supports 64-bit Windows and macOS." ;;
esac
UV_URL="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_ASSET"

mkdir -p "$STATE/downloads" "$STATE/logs" || fail "could not create its folder at $STATE. Check the disk has free space."
LOG="$STATE/logs/install.log"
printf '\n== install.sh %s\n' "$(date)" >>"$LOG"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# fetch URL DEST SHA256: resumes a stuck or broken download (curl -C -), up to 3 rounds of 5 retries.
fetch() {
  part="$2.part"; n=0
  while :; do
    if [ -f "$part" ] && [ "$(sha256_of "$part")" = "$3" ]; then break; fi
    n=$((n + 1)); [ "$n" -le 3 ] || return 1
    curl -fL -sS --retry 5 --retry-delay 3 --retry-all-errors --connect-timeout 30 \
      --speed-limit 20000 --speed-time 60 -C - -o "$part" "$1" 2>>"$LOG"
    rc=$?
    if [ "$rc" -ne 0 ]; then [ "$rc" -eq 33 ] && rm -f "$part"; sleep 3; continue; fi
    [ "$(sha256_of "$part")" = "$3" ] && break
    rm -f "$part"
  done
  mv -f "$part" "$2"
}

UVDIR="$STATE/uv/$UV_VERSION"; UV="$UVDIR/$UV_EXE"
if [ -x "$UV" ] && "$UV" --version 2>/dev/null | grep -q "^uv $UV_VERSION"; then
  say "✓ uv $UV_VERSION already in place"
else
  say "Downloading uv $UV_VERSION (installs the editor's private Python) ..."
  A="$STATE/downloads/$UV_ASSET"
  fetch "$UV_URL" "$A" "$UV_SHA" || fail "downloading uv failed. Check the internet connection, then run the setup again."
  rm -rf "$UVDIR"; mkdir -p "$UVDIR"
  case "$UV_ASSET" in
    *.zip) unzip -oq "$A" -d "$UVDIR" ;;
    *) tar -xzf "$A" -C "$UVDIR" --strip-components 1 ;;
  esac || fail "unpacking uv failed. Check the disk has free space, then run the setup again."
  rm -f "$A"
  "$UV" --version 2>/dev/null | grep -q "^uv $UV_VERSION" || fail "uv was downloaded but won't start. Send the setup report."
  say "✓ uv $UV_VERSION"
fi

# uv keeps everything inside the state folder: no ~/.local/bin links, no Windows registry entry, no user config.
export UV_PYTHON_INSTALL_DIR="$STATE/python" UV_CACHE_DIR="$STATE/cache/uv" UV_NO_CONFIG=1 \
  UV_MANAGED_PYTHON=1 UV_PYTHON_INSTALL_BIN=0 UV_PYTHON_INSTALL_REGISTRY=0
VENV="$STATE/venv"
if [ "$OS" = win ]; then VPY="$VENV/Scripts/python.exe"; else VPY="$VENV/bin/python"; fi
have=$([ -x "$VPY" ] && "$VPY" -I -c 'import platform; print(platform.python_version())' 2>/dev/null | tr -d '\r')
if [ "$have" = "$PY_VERSION" ]; then
  say "✓ Python $PY_VERSION already in place"
else
  say "Installing Python $PY_VERSION (a private copy, separate from any other Python) ..."
  "$UV" python install --no-bin "$PY_VERSION" >>"$LOG" 2>&1 \
    || fail "installing Python failed. Check the internet connection, then run the setup again."
  "$UV" venv --clear --python "$PY_VERSION" "$VENV" >>"$LOG" 2>&1 \
    || fail "creating the editor's Python environment failed. Check the disk has free space, then run the setup again."
  say "✓ Python $PY_VERSION"
fi

export EDITOR_SE_HOME="$STATE" EDITOR_SE_UV="$UV" EDITOR_SE_UV_VERSION="$UV_VERSION" EDITOR_SE_UV_URL="$UV_URL" \
  EDITOR_SE_UV_SHA256="$UV_SHA" PYTHONUTF8=1 PYTHONIOENCODING=utf-8
exec "$VPY" -X utf8 -I "$HERE/install.py" "$@"
