#!/bin/sh
# done-test.sh: run ON THE BOX as root after install. Read-only apart from the search queries it sends.
# Usage: sh done-test.sh     (settings: brain.json "done_test"; FEWZHUN_BOX_CONFIG moves brain.json;
#                             FBX_NODE names the node to use)
# Prints one PASS / FAIL / SKIP line per check and exits non-zero if any check failed.
CONF=${FEWZHUN_BOX_CONFIG:-/etc/fewzhun-box/brain.json}
HERE=$(cd "$(dirname "$0")/.." && pwd)
NODE=${FBX_NODE:-$(command -v node 2>/dev/null || true)}
if [ -z "$NODE" ]; then for n in "$HERE"/../node/node-v*/bin/node; do [ -x "$n" ] && NODE=$n; done; fi
[ -x "$NODE" ] || { echo "FAIL no node found (set FBX_NODE)"; exit 1; }
VARS=$("$NODE" "$HERE/lib/config.mjs" "$CONF" --sh) || { echo "FAIL $CONF does not load"; exit 1; }
eval "$VARS"
Q=${DT_QUERY:-$DT_SEM_Q}
export Q DT_SEM_Q DT_SEM_EXPECT DT_SUP_Q DT_SUP_PATH DT_DECAY_Q DT_DECAYS DT_KEEPS
URL="http://$BIND:$PORT"
TOK="$TOKENS_DIR/$DT_READER"
LOG="$LOG_DIR/queries.jsonl"
fails=0
skips=0
ok() { echo "PASS $*"; }
bad() { echo "FAIL $*"; fails=$((fails + 1)); }
skip() { echo "SKIP $*"; skips=$((skips + 1)); }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@"; }
# authed TOKENFILE curl-args...: the token reaches curl on stdin, never on a command line
authed() { f=$1; shift; printf 'header = "Authorization: Bearer %s"\n' "$(cat "$f")" | curl -s --max-time 60 -K - "$@"; }
# js EXPR: run EXPR with r = the JSON on stdin; it prints "PASS ..." or "FAIL ..."
js() { "$NODE" -e "let r; try { r = JSON.parse(require('fs').readFileSync(0, 'utf8')); } catch { console.log('FAIL response is not JSON'); process.exit(); } const E = process.env; $1"; }
verdict() { case "$1" in PASS*) ok "${1#PASS }" ;; SKIP*) skip "${1#SKIP }" ;; *) bad "${1#FAIL }" ;; esac; }

[ -n "$BIND" ] || { echo "FAIL bind $BIND_SPEC resolves to no address (is Docker up?)"; exit 1; }
echo "bind: $BIND_SPEC resolves to $BIND"
[ -r "$TOK" ] || { echo "FAIL no readable token for reader $DT_READER at $TOK (run as root)"; exit 1; }
echo "done-test: $URL as reader $DT_READER (spokes $DT_SPOKES)"

# 1. health, no token, no data
h=$(curl -fsS --max-time 5 "$URL/health")
[ "$h" = '{"ok":true}' ] && ok "health: $h" || bad "health: '$h'"

# 2. not signed in -> 401; a wrong token -> 401 too (403 is only for spokes)
for p in "/search?q=test" "/read?spoke=x&path=x.md" "/me"; do
  c=$(code "$URL$p"); [ "$c" = 401 ] && ok "no token $p -> $c" || bad "no token $p -> $c (want 401)"
done
wrong=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
c=$(printf 'header = "Authorization: Bearer %s"\n' "$wrong" | curl -s -o /dev/null -w '%{http_code}' --max-time 30 -K - "$URL/search?q=test")
[ "$c" = 401 ] && ok "wrong token -> $c" || bad "wrong token -> $c (want 401)"

# 3. a spoke this reader may not read and a spoke that does not exist get the same 403
nb=$(authed "$TOK" -w ' %{http_code}' --get --data-urlencode "q=test" --data-urlencode "spokes=no-such-spoke-zz" "$URL/search" | sed 's/token: no-such-spoke-zz"/token: SPOKE"/')
case "$nb" in *' 403') ok "spoke that does not exist -> 403" ;; *) bad "spoke that does not exist -> ${nb##* } (want 403)" ;; esac
if [ -n "$DT_OTHER_SPOKE" ]; then
  ob=$(authed "$TOK" -w ' %{http_code}' --get --data-urlencode "q=test" --data-urlencode "spokes=$DT_OTHER_SPOKE" "$URL/search" | sed "s/token: $DT_OTHER_SPOKE\"/token: SPOKE\"/")
  [ "$ob" = "$nb" ] && ok "spoke $DT_OTHER_SPOKE (not allowed) -> same 403 as a missing spoke" || bad "not-allowed spoke answer differs from missing spoke: '$ob' vs '$nb'"
  c=$(authed "$TOK" -o /dev/null -w '%{http_code}' "$URL/read?spoke=$DT_OTHER_SPOKE&path=x.md")
  [ "$c" = 403 ] && ok "read from $DT_OTHER_SPOKE -> $c" || bad "read from $DT_OTHER_SPOKE -> $c (want 403)"
else skip "reader $DT_READER may read every spoke, so there is no forbidden spoke to try"; fi

# 4. a real query through the real engine: JSON, >= 1 result, no spoke failed, all active, no AGENTS/README
if [ -n "$Q" ]; then
  json=$(authed "$TOK" --get --data-urlencode "q=$Q" --data-urlencode limit=20 "$URL/search")
  verdict "$(printf '%s' "$json" | js '
    if (!Array.isArray(r.results)) console.log(`FAIL no results list: ${JSON.stringify(r).slice(0, 200)}`);
    else if (r.failed) console.log(`FAIL spoke(s) failed: ${JSON.stringify(r.failed)}`);
    else if (!r.results.length) console.log(`FAIL 0 results for "${E.Q}" across ${r.spokes.join(",")}`);
    else {
      const b = r.results.filter((h) => /(^|\/)(AGENTS|README)\.md$/i.test(h.path) || String(h.status || "").trim().toLowerCase() !== "active");
      console.log(b.length ? `FAIL hidden notes returned: ${b.map((h) => h.spoke + "/" + h.path).join(", ")}` : `PASS "${E.Q}": ${r.results.length} result(s) across ${r.spokes.join(",")}, all active, ${r.ms} ms`);
    }')"
  t=$(authed "$TOK" -o /dev/null -w '%{time_total}' --get --data-urlencode "q=$Q" "$URL/search")
  awk "BEGIN { exit !($t < 5) }" && ok "warm query took ${t}s (< 5)" || bad "warm query took ${t}s (want < 5)"
else skip "done_test.query is not set in brain.json"; fi

# 5. meaning search: a question sharing no words with the note must still find it
if [ -n "$DT_SEM_Q" ] && [ -n "$DT_SEM_EXPECT" ]; then
  sp=${DT_SEM_EXPECT%%/*}; rel=${DT_SEM_EXPECT#*/}
  note=$(authed "$TOK" --get --data-urlencode "spoke=$sp" --data-urlencode "path=$rel" "$URL/read")
  json=$(authed "$TOK" --get --data-urlencode "q=$DT_SEM_Q" --data-urlencode limit=10 "$URL/search")
  verdict "$(printf '%s' "$json" | NOTE="$note" js '
    let n = {}; try { n = JSON.parse(E.NOTE); } catch {}
    const words = (s) => new Set(String(s || "").toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((w) => w.length > 3));
    const nw = words(n.text); const shared = [...words(E.DT_SEM_Q)].filter((w) => nw.has(w));
    const i = (r.results || []).findIndex((h) => `${h.spoke}/${h.path}` === E.DT_SEM_EXPECT);
    if (!n.text) console.log(`FAIL expected note ${E.DT_SEM_EXPECT} is not readable (missing, not active, or not a spoke this reader may read)`);
    else if (shared.length) console.log(`FAIL the meaning query shares words with the note (${shared.join(", ")}), so it proves nothing; reword it`);
    else if (i < 0) console.log(`FAIL meaning search: "${E.DT_SEM_Q}" did not find ${E.DT_SEM_EXPECT} in the top 10 (${(r.results || []).map((h) => h.path).join(", ")})`);
    else console.log(`PASS meaning search: "${E.DT_SEM_Q}" found ${E.DT_SEM_EXPECT} at rank ${i + 1} with no shared words`);')"
else skip "done_test.semantic {q, expect_path} is not set in brain.json"; fi

# 6. a superseded note is gone: not in results, not readable, no copy in its spoke
if [ -n "$DT_SUP_Q" ] && [ -n "$DT_SUP_PATH" ]; then
  sp=${DT_SUP_PATH%%/*}; rel=${DT_SUP_PATH#*/}
  json=$(authed "$TOK" --get --data-urlencode "q=$DT_SUP_Q" --data-urlencode limit=20 "$URL/search")
  verdict "$(printf '%s' "$json" | js '
    const hit = (r.results || []).some((h) => `${h.spoke}/${h.path}` === E.DT_SUP_PATH);
    console.log(hit ? `FAIL superseded ${E.DT_SUP_PATH} came back for "${E.DT_SUP_Q}"` : Array.isArray(r.results) ? `PASS superseded ${E.DT_SUP_PATH} absent from "${E.DT_SUP_Q}" (${r.results.length} other result(s))` : `FAIL no results list`);')"
  c=$(authed "$TOK" -o /dev/null -w '%{http_code}' --get --data-urlencode "spoke=$sp" --data-urlencode "path=$rel" "$URL/read")
  [ "$c" = 404 ] && ok "read superseded $DT_SUP_PATH -> $c" || bad "read superseded $DT_SUP_PATH -> $c (want 404)"
  [ -e "$ROOT/spokes/$sp/$rel" ] && bad "superseded copy still on disk: $ROOT/spokes/$sp/$rel" || ok "no superseded copy in $ROOT/spokes/$sp"
else skip "done_test.superseded {q, path} is not set in brain.json"; fi

# 7. ageing: a note in a decay spoke loses weight with age; a note in a "never" spoke keeps its score
if [ -n "$DT_DECAY_Q" ] && [ -n "$DT_DECAYS" ] && [ -n "$DT_KEEPS" ]; then
  json=$(authed "$TOK" --get --data-urlencode "q=$DT_DECAY_Q" --data-urlencode limit=20 "$URL/search")
  verdict "$(printf '%s' "$json" | js '
    const f = (p) => (r.results || []).find((h) => `${h.spoke}/${h.path}` === p);
    const d = f(E.DT_DECAYS); const k = f(E.DT_KEEPS);
    if (!d || !k) console.log(`FAIL "${E.DT_DECAY_Q}" must return both ${E.DT_DECAYS} and ${E.DT_KEEPS}; got ${(r.results || []).map((h) => h.spoke + "/" + h.path).join(", ")}`);
    else if (!(d.weight < 1)) console.log(`FAIL ${E.DT_DECAYS} (decay spoke, dated ${d.date}) kept weight ${d.weight}`);
    else if (k.weight !== 1) console.log(`FAIL ${E.DT_KEEPS} (decay never, dated ${k.date}) lost rank: weight ${k.weight}`);
    else console.log(`PASS ageing: ${E.DT_DECAYS} weight ${d.weight.toFixed(3)} (dated ${d.date}); ${E.DT_KEEPS} keeps weight 1 (dated ${k.date})`);')"
else skip "done_test.decay {q, decays, keeps} is not set in brain.json"; fi
echo "info: $(systemctl show -p MemoryCurrent -p MemoryMax fewzhun-box-server 2>/dev/null | tr '\n' ' ')(workers: $(pgrep -fc engine-worker.mjs || echo 0))"

# 8. read: instruction files and paths outside the spoke -> 404; a folder that is not a spoke -> 403
first=${DT_SPOKES%%,*}
for p in AGENTS.md README.md ../../../etc/passwd /etc/passwd ../vault/README.md "%2e%2e/%2e%2e/etc/passwd" AGENTS.md.bak; do
  c=$(authed "$TOK" -o /dev/null -w '%{http_code}' "$URL/read?spoke=$first&path=$p")
  [ "$c" = 404 ] && ok "read $first/$p -> $c" || bad "read $first/$p -> $c (want 404)"
done
c=$(authed "$TOK" -o /dev/null -w '%{http_code}' "$URL/read?spoke=vault&path=README.md")
[ "$c" = 403 ] && ok "read from vault (not a spoke) -> $c" || bad "read from vault -> $c (want 403)"

# 9. viewer: strict security header on the page
hdr=$(curl -s -D - -o /dev/null --max-time 10 "$URL/view" | tr -d '\r' | grep -i '^content-security-policy:')
case "$hdr" in *"default-src 'self'; script-src 'self'"*"frame-ancestors 'none'"*) ok "viewer CSP: ${hdr#*: }" ;; *) bad "viewer CSP missing or loose: '$hdr'" ;; esac

# 10. graphs: only to a reader with that spoke AND view: true
gs=""
for s in $(echo "$DT_SPOKES" | tr ',' ' '); do [ -f "$ROOT/graphs/$s/graph.json" ] && gs="$gs $s"; done
if [ -z "$gs" ]; then skip "no graph.json yet for $DT_SPOKES (the nightly graph job builds them)"; else
  for s in $gs; do
    c=$(authed "$TOK" -o /dev/null -w '%{http_code}' "$URL/graph/$s/graph.json")
    if [ "$DT_VIEW" = 1 ]; then [ "$c" = 200 ] && ok "graph $s for viewer $DT_READER -> $c" || bad "graph $s -> $c (want 200)"
    else [ "$c" = 403 ] && ok "graph $s for $DT_READER (view: false) -> $c" || bad "graph $s -> $c (want 403: view is false)"; fi
  done
fi
if [ -n "$DT_OTHER_SPOKE" ]; then
  c=$(authed "$TOK" -o /dev/null -w '%{http_code}' "$URL/graph/$DT_OTHER_SPOKE/graph.html")
  [ "$c" = 403 ] && ok "another spoke's graph ($DT_OTHER_SPOKE) -> $c" || bad "another spoke's graph ($DT_OTHER_SPOKE) -> $c (want 403)"
fi

# 11. listeners: only the bind address (and the tailnet one); never a wildcard
b=$(ss -ltnH "sport = :$PORT" 2>/dev/null | awk '{print $4}')
badl=$(printf '%s\n' "$b" | grep -v -e "^$BIND:$PORT\$" ${TAILNET:+-e "^$TAILNET:$PORT\$"} | grep . || true)
[ -n "$b" ] && [ -z "$badl" ] && ok "listening only on: $(echo $b)" || bad "listeners on port $PORT: '$(echo $b)' (want only $BIND${TAILNET:+ and $TAILNET})"

# 12. the server's outside address refuses the connection
pub=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')
if [ -z "$pub" ]; then skip "could not find this server's outside address"
elif [ "$pub" = "$BIND" ]; then bad "the brain is bound to the outside address $pub"
else
  c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://$pub:$PORT/health")
  [ "$c" = 000 ] && ok "outside address $pub:$PORT refuses the connection" || bad "outside address $pub:$PORT answered $c (want refused)"
fi

# 13. from inside the bot's container: /health, then one search (read-only GETs)
if [ -z "$DT_CONTAINER" ]; then skip "done_test.container not set: no in-container check"
elif ! docker inspect "$DT_CONTAINER" >/dev/null 2>&1; then bad "container $DT_CONTAINER not found"
else
  QE=$(printf %s "${Q:-test}" | sed 's/ /+/g')
  tool=$(docker exec "$DT_CONTAINER" sh -c 'for t in curl python3; do command -v $t >/dev/null 2>&1 && { echo $t; exit; }; done')
  case "$tool" in
    curl)
      hh=$(docker exec "$DT_CONTAINER" curl -s --max-time 10 "$URL/health")
      sc=$(printf 'header = "Authorization: Bearer %s"\n' "$(cat "$TOK")" | docker exec -i "$DT_CONTAINER" curl -s -o /dev/null -w '%{http_code}' --max-time 60 -K - "$URL/search?q=$QE") ;;
    python3)
      hh=$(docker exec "$DT_CONTAINER" python3 -c "import urllib.request; print(urllib.request.urlopen('$URL/health', timeout=10).read().decode())")
      sc=$(docker exec -i "$DT_CONTAINER" python3 -c "
import sys, urllib.request, urllib.error
req = urllib.request.Request('$URL/search?q=$QE', headers={'Authorization': 'Bearer ' + sys.stdin.read().strip()})
try: print(urllib.request.urlopen(req, timeout=60).status)
except urllib.error.HTTPError as e: print(e.code)" < "$TOK") ;;
    *) skip "container has neither curl nor python3: no in-container check" ;;
  esac
  if [ -n "$tool" ]; then
  [ "$hh" = '{"ok":true}' ] && ok "container ($tool) reaches /health" || bad "container ($tool) /health: '$hh'"
  [ "$sc" = 200 ] && ok "container ($tool) token search -> $sc" || bad "container ($tool) token search -> $sc (want 200)"
  fi
fi

# 14. queries are logged, and no token ever is
sleep 1
leak=0
for t in "$TOKENS_DIR"/*; do [ -f "$t" ] && grep -qFf "$t" "$LOG" 2>/dev/null && leak=1; done
if [ -s "$LOG" ] && [ "$leak" = 0 ]; then ok "query log has $(wc -l < "$LOG") lines, no token"; else bad "query log missing or holds a token"; fi

echo "failures: $fails"
echo "skips: $skips"
[ "$fails" = 0 ]
