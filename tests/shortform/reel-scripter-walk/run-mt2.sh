#!/bin/bash
# Multi-turn walk: opening ask, then client-style answers at each stop via --resume. usage: bash run-mt2.sh <name> [gut|contra] [--run2]. run-mt.sh + fixes after run5: MSYS path conversion left ON (production shape), CLAUDE_PLUGIN_ROOT set (Desktop expands it; headless does not), synced shortform copy moved aside before each turn
# State lives outside the repo: home/ (scratch Claude profile; never holds a login file), proj/ (gut) or proj-contra/ (contra), fixtures/, logs/, synced-aside/.
# Auth (SKLLPLG-369): a walk-only `claude setup-token` token read from RS_WALK_TOKEN (default $HOME/.config/rs-walk/walk-token) and passed as CLAUDE_CODE_OAUTH_TOKEN. The live ~/.claude/.credentials.json is never read or copied.
# --run2 (or RS_WALK_RUN2=1): a second reel in the same project with no reset; the loop stops on a finished script whose name or content was not there at start (a reused or overwritten slug counts).
# Answers: respond.py picks each one from the fixture's answer file (gut: answers-gut.txt here; contra: <state>/fixtures/contra-answers.txt) off the last assistant text of the turn before. At most 18 turns.
# Budget: --max-budget-usd 3.00 per turn; the walk stops once the session's total_cost_usd passes RS_WALK_CAP (default 8.00).
S="$(cygpath -m "${RS_WALK_STATE:-$HOME/rs-walk-state}")"; H="$S/home"; L="$S/logs"; N="$1"
RUN2="${RS_WALK_RUN2:-}"; FX=gut
for a in "${@:2}"; do case "$a" in --run2) RUN2=1;; gut|contra) FX="$a";; *) echo "refuse: unknown arg $a"; exit 2;; esac; done
CAP="${RS_WALK_CAP:-8.00}"
# The plugin under test is the one in this repo, found from this script's own location.
D="$(cygpath -m "$(cd "$(dirname "$0")" && pwd)")"
R="$(cygpath -m "$(cd "$(dirname "$0")/../../.." && pwd)")/plugins/shortform-superengine"
case "$FX" in
  gut) P="$S/proj"; B=fixturebrand; ANSF="$D/answers-gut.txt";;
  contra) P="$S/proj-contra"; B=contrabrand; ANSF="$S/fixtures/contra-answers.txt";;
esac
[ -n "$N" ] || { echo "usage: bash run-mt2.sh <name> [gut|contra] [--run2]"; exit 2; }
[ -d "$R" ] || { echo "refuse: no plugin at $R"; exit 2; }
[ -d "$H/.claude" ] && [ -d "$P" ] || { echo "refuse: no home/.claude or $P (set RS_WALK_STATE, run reset.sh $FX)"; exit 2; }
[ -f "$ANSF" ] || { echo "refuse: no answer file $ANSF"; exit 2; }
grep -q "\"active_brand\": *\"$B\"" "$H/.claude/shortform-superengine/.superengine" || { echo "refuse: active_brand is not $B (run reset.sh $FX)"; exit 2; }
MSG="$(PYTHONIOENCODING=utf-8 py -3.12 "$D/respond.py" "$ANSF" --open)" || { echo "refuse: responder check failed"; exit 2; }
mkdir -p "$L"
ls "$L/$N"-t*.jsonl >/dev/null 2>&1 && { echo "refuse: $N exists"; exit 2; }
# One line per finished script: "<name> <sha256 of its content>", so a changed file is a new line.
# Not finished: a file the plugin's placeholder rule flags (structure_gate.placeholder_problems, the rule the hooks use).
unfinished() { PYTHONIOENCODING=utf-8 py -3.12 -B -c 'import sys; sys.path.insert(0, sys.argv[1]); import structure_gate as g; sys.exit(not g.placeholder_problems(open(sys.argv[2], encoding="utf-8-sig").read()))' "$R/skills/reel-scripter" "$1"; }
finished() { for f in "$P/scripts/"*.md; do [ -f "$f" ] || continue; case "${f##*/}" in *skeleton*|*.draft.md) continue;; esac; unfinished "$f" && continue; echo "${f##*/} $(sha256sum < "$f" | cut -d' ' -f1)"; done | sort; }
START=""; [ -n "$RUN2" ] && START="$(finished)"
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL
TF="${RS_WALK_TOKEN:-$HOME/.config/rs-walk/walk-token}"
WT="$({ tr -d ' \r\n' < "$TF"; } 2>/dev/null)"
case "$WT" in sk-ant-oat*) ;; *) echo "refuse: no walk token in $TF (run claude setup-token, save it there)"; exit 2;; esac
rm -f "$H/.claude/.credentials.json"
export HOME="$H" USERPROFILE="$(cygpath -w "$H")"
for v in $(env | grep -o -E "^(CLAUDE[A-Z_]*|ANTHROPIC[A-Z_]*)"); do unset "$v"; done
export CLAUDE_PLUGIN_ROOT="$R" CLAUDE_CODE_OAUTH_TOKEN="$WT"
mkdir -p "$S/synced-aside"
cd "$P" || exit 1
FLAGS=(--plugin-dir "$R" --model sonnet --max-budget-usd 3.00 --output-format stream-json --verbose --strict-mcp-config --permission-mode bypassPermissions)
SID=""
for i in $(seq 0 17); do
  OUT="$L/$N-t$i.jsonl"
  echo "turn $i says: $MSG"
  for p in "$H"/.claude/plugins/synced/*/shortform-superengine; do [ -d "$p" ] && { rm -rf "$S/synced-aside/sf-$i"; mv "$p" "$S/synced-aside/sf-$i"; echo "turn $i: moved synced shortform aside"; }; done
  if [ -z "$SID" ]; then claude -p "$MSG" "${FLAGS[@]}" > "$OUT" 2> "$OUT.err"
  else claude -p "$MSG" --resume "$SID" "${FLAGS[@]}" > "$OUT" 2> "$OUT.err"; fi
  [ -z "$SID" ] && SID=$(grep -o '"session_id":"[^"]*"' "$OUT" | head -1 | cut -d'"' -f4)
  echo "turn $i sid=$SID lines=$(wc -l < "$OUT")"
  NEW="$(comm -13 <(echo "$START") <(finished))"
  [ -n "$NEW" ] && { echo "script written at turn $i: $NEW"; break; }
  COST=$(grep -o '"total_cost_usd":[0-9.eE+-]*' "$OUT" | tail -1 | cut -d: -f2)
  echo "turn $i session cost so far: \$${COST:-unknown}"
  # Fail fast: a turn whose final result is an error and that spent nothing (bad login, crash) stops the walk.
  if grep '"type":"result"' "$OUT" | grep -q '"is_error":true' && awk -v c="${COST:-0}" 'BEGIN { exit !(c + 0 == 0) }'; then
    echo "turn $i failed with no spend: $(grep -o '"result":"[^"]\{0,160\}' "$OUT" | tail -1 | cut -d'"' -f4); stopping"; break
  fi
  if [ -n "$COST" ] && awk -v c="$COST" -v m="$CAP" 'BEGIN { exit !(c + 0 > m + 0) }'; then
    echo "walk cap tripped at turn $i: session total_cost_usd \$$COST passed RS_WALK_CAP \$$CAP; stopping"; break
  fi
  MSG="$(PYTHONIOENCODING=utf-8 py -3.12 "$D/respond.py" "$ANSF" "$OUT")" || { echo "responder failed after turn $i; stopping"; break; }
done
# Numeric turn order (a glob would put t10 before t2).
for j in $(seq 0 "$i"); do [ -f "$L/$N-t$j.jsonl" ] && cat "$L/$N-t$j.jsonl"; done > "$L/$N.jsonl"
