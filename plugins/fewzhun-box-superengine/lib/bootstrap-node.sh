#!/bin/sh
# bootstrap-node.sh: make sure fewzhun-box has a Node.js 20 or newer (Linux and Mac, POSIX sh).
# Copied from Fewzhun v1.1 scripts/bootstrap-node.sh; only the install folder and messages changed.
# stdout: one line, the absolute path of the node to use. Messages go to stderr.
# Exit 0 = path printed, 1 = could not provide Node (nothing half-installed is used).
# If no Node 20+ is on PATH (or FBX_NODE_PINNED=1), it installs the pinned official Node into
# FBX_NODE_DIR (install.sh passes <code_root>/node). It never touches another plugin's folders.
# FBX_NODE_DIST (test seam): a base URL or a local folder holding the dist files.
set -eu
VERSION=24.21.0 # same pin as Fewzhun v1.1
say() { printf '%s\n' "$*" >&2; }
major() { "$1" --version 2>/dev/null | sed -n 's/^v\([0-9][0-9]*\)\..*/\1/p'; }

if [ "${FBX_NODE_PINNED:-0}" != 1 ] && p=$(command -v node 2>/dev/null) && [ -n "$p" ]; then
  m=$(major "$p" || true)
  if [ -n "$m" ] && [ "$m" -ge 20 ]; then
    case "$p" in /*) ;; *) p="$(cd "$(dirname "$p")" && pwd)/$(basename "$p")" ;; esac
    printf '%s\n' "$p"; exit 0
  fi
fi

case "$(uname -s)" in Linux) os=linux ;; Darwin) os=darwin ;; *) say "fewzhun-box runs on Linux or Mac; this system is not supported."; exit 1 ;; esac
case "$(uname -m)" in x86_64|amd64) arch=x64 ;; aarch64|arm64) arch=arm64 ;; *) say "This computer's processor type is not supported by Node.js $VERSION."; exit 1 ;; esac
name="node-v$VERSION-$os-$arch"
file="$name.tar.gz"
state="${FBX_NODE_DIR:-/opt/fewzhun-box-app/node}"
bin="$state/$name/bin/node"
m=$(major "$bin" || true)
if [ -n "$m" ] && [ "$m" -ge 20 ]; then printf '%s\n' "$bin"; exit 0; fi

dist="${FBX_NODE_DIST:-https://nodejs.org/dist/v$VERSION}"
dl="$state/dl"
mkdir -p "$dl" "$state"
fetch() {
  if [ -d "$dist" ]; then cp "$dist/$1" "$2"
  elif command -v curl >/dev/null 2>&1; then curl -fsSL --max-time 600 -o "$2" "$dist/$1"
  elif command -v wget >/dev/null 2>&1; then wget -q -T 600 -O "$2" "$dist/$1"
  else say "Neither curl nor wget is available to download Node.js."; exit 1
  fi
}

say "Getting Node.js $VERSION for fewzhun-box (about a 55 MB download, about 200 MB installed)..."
sums="$dl/SHASUMS256-v$VERSION.txt"
fetch SHASUMS256.txt "$sums"
want=$(awk -v f="$file" '$2 == f { print $1; exit }' "$sums")
if [ -z "$want" ]; then say "The Node.js checksum list has no entry for $file; nothing was installed."; exit 1; fi
fetch "$file" "$dl/$file"
if command -v sha256sum >/dev/null 2>&1; then got=$(sha256sum "$dl/$file" | cut -d' ' -f1)
else got=$(shasum -a 256 "$dl/$file" | cut -d' ' -f1)
fi
if [ "$got" != "$want" ]; then
  rm -f "$dl/$file"
  say "The Node.js download failed its checksum; nothing was installed."; exit 1
fi
tar -xzf "$dl/$file" -C "$state"
rm -f "$dl/$file"
m=$(major "$bin" || true)
if [ -z "$m" ] || [ "$m" -lt 20 ]; then say "Node.js could not be unpacked."; exit 1; fi
printf '%s\n' "$bin"
