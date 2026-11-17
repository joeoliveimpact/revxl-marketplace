#!/bin/sh
# install.sh: install or update fewzhun-box on this Linux server. Run as root; nobody needs to be at the screen.
#   sh bin/install.sh                  dry run: print what --apply would do, change nothing
#   sh bin/install.sh --apply          install or update (safe to re-run), then run the done-test
#   sh bin/install.sh --config FILE    use FILE as /etc/fewzhun-box/brain.json when that file is missing
# Steps only the owner can do are printed as PAUSE POINTS at the end; this script never does them.
set -eu
APPLY=0
SRC_CONF=""
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --config) SRC_CONF=${2:-}; [ -n "$SRC_CONF" ] || { echo "usage: --config FILE" >&2; exit 2; }; shift ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done
HERE=$(cd "$(dirname "$0")/.." && pwd)
ETC=/etc/fewzhun-box
CONF=$ETC/brain.json
LIB=/var/lib/fewzhun-box
UNITDIR=/etc/systemd/system
CHANGED=0
UNIT_CHANGED=0
PAUSES=""

say() { echo "$*"; }
die() { echo "STOP: $*" >&2; exit 1; }
act() { if [ "$APPLY" = 1 ]; then echo "+ $*"; sh -c "$*"; else echo "would: $*"; fi; }
pause() { PAUSES="$PAUSES
PAUSE POINT ($1): $2"; }
# put SRC DST MODE: install SRC at DST only when it differs; sets CHANGED
put() {
  if [ -f "$2" ] && cmp -s "$1" "$2"; then say "same: $2"; return 0; fi
  act "install -o root -g root -m $3 '$1' '$2'"
  CHANGED=1
}

[ "$APPLY" = 0 ] && say "DRY RUN: nothing is changed. Run with --apply to install."
[ "$APPLY" = 0 ] || [ "$(id -u)" = 0 ] || die "run as root (sudo sh bin/install.sh --apply)"
[ "$(uname -s)" = Linux ] || die "fewzhun-box installs on Linux servers only"

# ---- 0. never take over another brain service ----
[ -e /etc/brain-search ] && die "found /etc/brain-search: another brain search service is installed here. fewzhun-box 0.1.0 never takes one over; remove it first or use another server."
for d in /etc/systemd/system /run/systemd/system /lib/systemd/system /usr/lib/systemd/system; do
  [ -e "$d/brain-search.service" ] && die "found $d/brain-search.service: another brain search service is installed here. fewzhun-box 0.1.0 never takes one over."
done

# ---- 1. the config file ----
if [ -f "$CONF" ]; then CONF_READ=$CONF
elif [ -n "$SRC_CONF" ]; then
  [ -f "$SRC_CONF" ] || die "no such file: $SRC_CONF"
  CONF_READ=$SRC_CONF
  act "install -d -o root -g root -m 0755 $ETC && install -o root -g root -m 0640 '$SRC_CONF' $CONF"
  [ "$APPLY" = 1 ] && CONF_READ=$CONF
else
  die "no $CONF yet: copy config/brain.example.json there, fill it in (see config/CONFIG.md), then run again. Or pass --config FILE."
fi
command -v python3 >/dev/null 2>&1 || die "python3 is missing (stock Ubuntu has it): apt-get install -y python3"
ROOT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("root") or "/opt/fewzhun-box")' "$CONF_READ") || die "$CONF_READ is not valid JSON"

CODE_ROOT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("code_root", "/opt/fewzhun-box-app"))' "$CONF_READ")

# ---- 2. Node 20+ (with npm), else the pinned Node from lib/bootstrap-node.sh into <code_root>/node ----
NODE=""
NPM=""
if p=$(command -v node 2>/dev/null) && [ "$("$p" -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -ge 20 ]; then
  NODE=$p
  if [ -x "$(dirname "$p")/npm" ]; then NPM=$(dirname "$p")/npm; else NPM=$(command -v npm 2>/dev/null || true); fi
fi
if [ -z "$NODE" ] || [ -z "$NPM" ]; then
  for n in "$CODE_ROOT"/node/node-v*/bin/node; do [ -x "$n" ] && NODE=$n && NPM=$(dirname "$n")/npm; done
fi
if [ -z "$NODE" ] || [ -z "$NPM" ] || [ ! -x "$NPM" ]; then
  if [ "$APPLY" = 1 ]; then
    say "+ Node.js 20+ with npm not found: installing the pinned Node into $CODE_ROOT/node"
    NODE=$(FBX_NODE_PINNED=1 FBX_NODE_DIR="$CODE_ROOT/node" sh "$HERE/lib/bootstrap-node.sh") || die "could not install Node.js"
    NPM=$(dirname "$NODE")/npm
  else
    say "would: install Node.js 24 (pinned, checksum-checked) into $CODE_ROOT/node with lib/bootstrap-node.sh"
    version=$(sed -n 's/^VERSION=\([^ ]*\).*/\1/p' "$HERE/lib/bootstrap-node.sh")
    case "$(uname -m)" in aarch64|arm64) arch=arm64 ;; *) arch=x64 ;; esac
    NODE="$CODE_ROOT/node/node-v$version-linux-$arch/bin/node"
    NPM="$(dirname "$NODE")/npm"
  fi
fi
if [ -x "$NODE" ]; then say "node: $NODE ($("$NODE" --version))"; fi

# ---- 3. read and check brain.json ----
if [ -x "$NODE" ]; then
  if [ "$APPLY" = 1 ]; then mode=--apply; else mode=--dry-run; fi
  VARS=$("$NODE" "$HERE/lib/config.mjs" "$CONF_READ" --install-sh "$mode") || die "fix $CONF_READ first (see config/CONFIG.md)"
else
  VARS=$(python3 "$HERE/py/install_config.py" "$CONF_READ") || die "fix $CONF_READ first (see config/CONFIG.md)"
fi
eval "$VARS"
say "code_root: $CODE_ROOT; root: $ROOT; spokes: $SPOKES; readers: $READERS; warm: $WARM; memory_max: $MEMORY_MAX"

# ---- 4. memory: every warm spoke holds its own model copy (about 400 MB) ----
avail_kb=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
cur=$(systemctl show -p MemoryCurrent --value fewzhun-box-server 2>/dev/null || true)
case "$cur" in ''|*[!0-9]*) cur=0 ;; esac
avail_kb=$((avail_kb + cur / 1024))
need_kb=$((NSPOKES * 400 * 1024))
say "memory: $((avail_kb / 1024)) MB available for the brain; warm=all needs about $((need_kb / 1024)) MB for $NSPOKES spoke(s)"
if [ "$WARM" = all ] && [ "$avail_kb" -lt "$need_kb" ]; then
  say "memory is tight: switching to warm=lazy (each spoke loads on its first search)"
  act "'$NODE' '$HERE/lib/config.mjs' '$CONF_READ' --warm-lazy"
  WARM=lazy
  CHANGED=1
fi

# ---- 5. service user and folders ----
getent group fbx >/dev/null 2>&1 || act "groupadd --system fbx"
id fbx >/dev/null 2>&1 || act "useradd --system --gid fbx --home-dir $LIB --no-create-home --shell /usr/sbin/nologin fbx"
act "install -d -o root -g fbx -m 0750 $ETC"
act "install -d -o root -g root -m 0700 '$TOKENS_DIR'"
act "install -d -o root -g fbx -m 0750 '$ROOT'"
act "install -d -o root -g root -m 0755 '$CODE_ROOT'"
for d in spokes vault; do
  act "install -d -o fbx -g fbx -m 2770 '$ROOT/$d'"
  act "find '$ROOT/$d' -type d -exec chmod 2770 {} +; find '$ROOT/$d' -type f -exec chmod 0660 {} +"
done
for s in $SPOKES; do act "install -d -o fbx -g fbx -m 2770 '$ROOT/spokes/$s'"; done
for d in graphs status; do
  [ ! -L "$ROOT/$d" ] || die "$ROOT/$d must not be a symlink"
  act "install -d -o root -g fbx -m 0750 '$ROOT/$d' && chown -hR root:fbx '$ROOT/$d' && find '$ROOT/$d' -type d -exec chmod 0750 {} + && find '$ROOT/$d' -type f -exec chmod 0640 {} +"
done
act "install -d -o root -g root -m 0700 /var/lib/fewzhun-box-graph"
for s in $SPOKES; do act "install -d -o root -g root -m 0700 '/var/lib/fewzhun-box-graph/$s'"; done
act "install -d -o root -g root -m 0700 '$ROOT/staging'"
act "install -d -o root -g fbx -m 0750 '$ROOT/approved'"
act "install -d -o fbx -g fbx -m 0750 '$LOG_DIR'"
act "install -d -o root -g fbx -m 0750 $LIB"
act "install -d -o fbx -g fbx -m 0750 $LIB/status"
act "install -d -o fbx -g fbx -m 0750 $LIB/.cache"
act "install -d -o fbx -g fbx -m 0700 $LIB/.ssh"
act "chown root:fbx $CONF 2>/dev/null; chmod 0640 $CONF 2>/dev/null; true"

# ---- 6. the plugin itself -> <code_root>/app (root-owned, read-only to the services) ----
if [ -d "$CODE_ROOT/app" ] && diff -rq "$HERE" "$CODE_ROOT/app" >/dev/null 2>&1; then say "same: $CODE_ROOT/app"
else
  act "rm -rf '$CODE_ROOT/app.new' && cp -R '$HERE' '$CODE_ROOT/app.new' && chown -R root:root '$CODE_ROOT/app.new' && chmod -R go-w '$CODE_ROOT/app.new' && rm -rf '$CODE_ROOT/app' && mv '$CODE_ROOT/app.new' '$CODE_ROOT/app'"
  CHANGED=1
fi
act "chown root:root '$CODE_ROOT/app/py/shim/claude' && chmod 0755 '$CODE_ROOT/app/py/shim/claude'"

# ---- 7. the search engine, pinned (obsidian-hybrid-search 0.12.7) from the shipped lockfile ----
if cmp -s "$HERE/package-lock.json" "$CODE_ROOT/package-lock.json" && [ -f "$CODE_ROOT/node_modules/obsidian-hybrid-search/package.json" ]; then
  say "same: engine in $CODE_ROOT/node_modules"
else
  act "cp '$HERE/package.json' '$HERE/package-lock.json' '$CODE_ROOT/' && cd '$CODE_ROOT' && PATH='$(dirname "$NODE")':/usr/bin:/bin '$NPM' ci --omit=dev --no-audit --no-fund"
  CHANGED=1
fi
if [ "$APPLY" = 1 ]; then
  [ -e "$ENGINE" ] || die "no engine at $ENGINE after npm ci"
  src=$(dirname "$(readlink -f "$ENGINE")")
  for m in config.js db.js embedder.js searcher.js; do [ -f "$src/$m" ] || die "engine module missing: $src/$m (not 0.12.7?)"; done
  v=$("$NODE" -p "require('$src/../../package.json').version" 2>/dev/null) || v=unknown
  [ "$v" = 0.12.7 ] || die "engine is $v; the server's worker mirrors 0.12.7's search start-up"
fi

act "chown -R root:root '$CODE_ROOT' && chmod -R u+rwX,go+rX,go-w '$CODE_ROOT'"

# ---- 8. the embedding model: one tiny index as fbx puts it in fbx's HOME ----
if [ -d "$LIB/.cache/huggingface/Xenova/multilingual-e5-small" ]; then say "same: embedding model in $LIB/.cache"
else
  W=$LIB/warmup
  act "install -d -o fbx -g fbx -m 0750 $W && printf -- '---\\nstatus: active\\n---\\nwarm-up note for the model download\\n' > $W/warmup.md && chown fbx:fbx $W/warmup.md"
  act "cd $W && runuser -u fbx -- env -i HOME=$LIB PATH=/usr/bin:/bin OBSIDIAN_VAULT_PATH=$W 'OBSIDIAN_IGNORE_PATTERNS=.obsidian/**' '$NODE' \"\$(readlink -f '$ENGINE')\" reindex"
fi

# ---- 9. graphify in its own venv (graph.enabled) ----
if [ "$GRAPH_ENABLED" = 1 ]; then
  have=$("$CODE_ROOT/venv/bin/python" -m pip show graphifyy 2>/dev/null | awk '/^Version:/ {print $2}' || true)
  if [ "$have" = "$GRAPHIFY_VERSION" ]; then say "same: graphifyy $have in $CODE_ROOT/venv"
  else
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || die "graphify needs Python 3.11 or newer"
    act "[ -x '$CODE_ROOT/venv/bin/python' ] || python3 -m venv '$CODE_ROOT/venv' || { rm -rf '$CODE_ROOT/venv'; apt-get install -y python3-venv && python3 -m venv '$CODE_ROOT/venv'; }"
    act "'$CODE_ROOT/venv/bin/python' -m pip install --quiet --disable-pip-version-check 'graphifyy==$GRAPHIFY_VERSION'"
  fi
fi
# Code and runtimes are public and root-owned, even with a restrictive installer umask.
act "chown -R root:root '$CODE_ROOT' && chmod -R u+rwX,go+rX,go-w '$CODE_ROOT'"

# ---- 10. where the bot reaches the brain ----
if [ "$BIND_SPEC" = auto-docker ]; then
  if [ -n "$BIND" ]; then say "bind: $BIND (Docker host address)"; else say "WARN: no Docker network yet (docker0 or br-*); the service retries until one exists"; fi
fi
URL="http://$BIND:$PORT"

# ---- 11. systemd units (rendered from systemd/), query log rotation ----
CLAUDE_HOME=-/nonexistent
if [ -n "$CLAUDE_RUN_AS" ]; then
  h=$(getent passwd "$CLAUDE_RUN_AS" | cut -d: -f6)
  [ -n "$h" ] && CLAUDE_HOME=$h
fi
TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT
# Public CLI wrapper: workers need only their own token and URL, never membership in fbx.
printf '%s\n' '#!/bin/sh' "exec \"$NODE\" \"$CODE_ROOT/app/bin/fewzhun-box.mjs\" \"\$@\"" > "$TMPD/fewzhun-box"
put "$TMPD/fewzhun-box" /usr/local/bin/fewzhun-box 0755
# Sync git config (rewritten on every install).
if [ "$APPLY" = 1 ]; then
  "$NODE" "$HERE/lib/config.mjs" "$CONF_READ" --sync-gitconfig > "$TMPD/sync.gitconfig" || die "could not render sync gitconfig"
  act "install -o root -g root -m 0644 '$TMPD/sync.gitconfig' '$SYNC_GITCONFIG'"
else
  say "would: render $SYNC_GITCONFIG from $CONF_READ (root:root, 0644)"
fi
# End sync git config.
for f in "$HERE"/systemd/fewzhun-box-*.service "$HERE"/systemd/fewzhun-box-*.timer; do
  [ -f "$f" ] || continue
  b=$(basename "$f")
  sed -e "s|@ROOT@|$ROOT|g" -e "s|@CODE_ROOT@|$CODE_ROOT|g" -e "s|@CONF@|$CONF|g" -e "s|@NODE@|$NODE|g" -e "s|@LOG_DIR@|$LOG_DIR|g" \
      -e "s|@MEMORY_MAX@|$MEMORY_MAX|g" -e "s|@SYNC_INTERVAL@|$SYNC_INTERVAL|g" -e "s|@GRAPH_TIME@|$GRAPH_TIME|g" \
      -e "s|@HARVEST_TIME@|$HARVEST_TIME|g" -e "s|@TZ@|$TIMEZONE|g" -e "s|@CLAUDE_HOME@|$CLAUDE_HOME|g" "$f" > "$TMPD/$b"
  grep -q '@[A-Z_]*@' "$TMPD/$b" && die "$b has a placeholder install.sh does not fill: $(grep -o '@[A-Z_]*@' "$TMPD/$b" | head -1)"
  c=$CHANGED; CHANGED=0
  put "$TMPD/$b" "$UNITDIR/$b" 0644
  [ "$CHANGED" = 1 ] && UNIT_CHANGED=1
  [ "$c" = 1 ] && CHANGED=1
done
printf '%s\n' "$LOG_DIR/*.jsonl {" "    weekly" "    rotate 8" "    compress" "    delaycompress" "    missingok" \
  "    notifempty" "    create 0640 fbx fbx" "    su fbx fbx" "}" > "$TMPD/logrotate"
c=$CHANGED; put "$TMPD/logrotate" /etc/logrotate.d/fewzhun-box 0644; CHANGED=$c

# ---- 12. reader tokens (raw files root-only; tokens.json holds sha256 only) ----
for r in $READERS; do
  if [ "$APPLY" = 1 ]; then FEWZHUN_BOX_CONFIG=$CONF "$NODE" "$HERE/bin/tokens.mjs" add "$r"
  else say "would: node bin/tokens.mjs add $r  (creates $TOKENS_DIR/$r if missing, never prints it)"; fi
done
act "chown root:fbx '$TOKENS_FILE' && chmod 0640 '$TOKENS_FILE' && chown -R root:root '$TOKENS_DIR' && chmod 0700 '$TOKENS_DIR' && chmod 0600 '$TOKENS_DIR/'*"

# ---- 13. deploy key for sync (read-only on GitHub; the owner adds it) ----
if [ "$SYNC_ENABLED" = 1 ] && [ "$SYNC_SSH" = 1 ]; then
  [ -f "$DEPLOY_KEY" ] || act "ssh-keygen -q -t ed25519 -N '' -C fewzhun-box-deploy -f '$DEPLOY_KEY' && chown fbx:fbx '$DEPLOY_KEY' '$DEPLOY_KEY.pub' && chmod 0600 '$DEPLOY_KEY'"
  pub=$(cat "$DEPLOY_KEY.pub" 2>/dev/null || echo "(created by --apply at $DEPLOY_KEY.pub)")
  pause "deploy key" "on GitHub, open the notes repo > Settings > Deploy keys > Add deploy key, paste this key and leave 'Allow write access' OFF: $pub"
fi

# ---- 14. start, enable, health ----
conf_sum=$(sha256sum "$CONF_READ" | cut -d' ' -f1)
[ "$conf_sum" = "$(cat "$LIB/.installed-conf.sha256" 2>/dev/null || true)" ] || CHANGED=1
[ "$UNIT_CHANGED" = 1 ] && act "systemctl daemon-reload"
act "systemctl enable fewzhun-box-server.service"
if [ "$CHANGED" = 1 ] || ! systemctl is-active -q fewzhun-box-server 2>/dev/null; then act "systemctl restart fewzhun-box-server.service"
else say "nothing changed; server left running"; fi
act "echo $conf_sum > $LIB/.installed-conf.sha256"
timer() { # timer NAME ENABLED
  [ -f "$UNITDIR/fewzhun-box-$1.timer" ] || [ -f "$HERE/systemd/fewzhun-box-$1.timer" ] || return 0
  if [ "$2" = 1 ]; then act "systemctl enable --now fewzhun-box-$1.timer"
  elif systemctl is-enabled -q "fewzhun-box-$1.timer" 2>/dev/null; then act "systemctl disable --now fewzhun-box-$1.timer"; fi
}
timer sync "$SYNC_ENABLED"
timer graph "$GRAPH_ENABLED"
timer harvest "$HARVEST_ENABLED"

if [ "$APPLY" = 1 ]; then
  ok=0
  for i in 1 2 3 4 5 6 7 8 9 10; do
    [ -n "$BIND" ] && curl -fsS --max-time 5 "$URL/health" >/dev/null 2>&1 && { ok=1; break; }
    sleep 2
  done
  [ "$ok" = 1 ] && say "health: $URL/health answers" || say "WARN: $URL/health does not answer yet; see: journalctl -u fewzhun-box-server -n 50"
  # first sync: pulls (sync on) or copies whatever is in <root>/vault; a failure is reported, not fatal
  if [ "$SYNC_ENABLED" = 1 ] || [ -n "$(ls -A "$ROOT/vault" 2>/dev/null)" ]; then
    systemctl start fewzhun-box-sync.service && say "first sync: done" \
      || say "WARN: first sync failed (see: journalctl -u fewzhun-box-sync -n 50). With sync on, the deploy key is usually not on GitHub yet."
  else
    say "no notes yet: put them in $ROOT/vault (or turn sync on), then: systemctl start fewzhun-box-sync"
  fi
fi

# ---- 15. owner-only steps ----
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
  nets=$(ip -4 -o addr show 2>/dev/null | awk '$2 == "docker0" || $2 ~ /^br-/ {print $4}' | while read -r a; do python3 -c 'import ipaddress,sys; print(ipaddress.ip_interface(sys.argv[1]).network)' "$a"; done | sort -u | tr '\n' ' ')
  for n in $nets; do pause "firewall" "let the bot's Docker network reach the brain: ufw allow in from $n to ${BIND:-<bind address>} port $PORT proto tcp"; done
  [ -n "$nets" ] || pause "firewall" "ufw is on and no Docker network exists yet; once it does: ufw allow in from <docker subnet> to <bind address> port $PORT proto tcp"
fi
if [ "$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)" = 1 ]; then
  pause "kernel setting" "Claude Code's Bash sandbox needs unprivileged user namespaces, which AppArmor blocks here. If Claude workers run on this server: echo 'kernel.apparmor_restrict_unprivileged_userns=0' > /etc/sysctl.d/60-claude-userns.conf && sysctl --system"
fi
if [ -n "$TAILNET_SPEC" ] && [ -z "$TAILNET" ]; then
  pause "tailscale" "the viewer's phone address needs Tailscale: install it and run 'tailscale up'. The brain opens on the tailnet address within a minute, no restart needed."
fi
for r in $READERS; do
  pause "token for $r" "give reader $r its token from $TOKENS_DIR/$r (root only). In the bot's container put it in a file or secret, never in chat or a command line, and use the address $URL with the header 'Authorization: Bearer <token>'. For a Claude worker user: save it as ~/.config/revxl/fewzhun-box/token (chmod 600) and the address in ~/.config/revxl/fewzhun-box/url."
done
if [ -n "$PAUSES" ]; then echo "$PAUSES"; echo; fi

# ---- 16. done-test ----
if [ "$APPLY" = 1 ]; then
  say "running the done-test..."
  FBX_NODE=$NODE FEWZHUN_BOX_CONFIG=$CONF sh "$CODE_ROOT/app/bin/done-test.sh"
else
  say "would: run sh $CODE_ROOT/app/bin/done-test.sh"
fi
