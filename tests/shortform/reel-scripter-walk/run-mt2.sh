#!/bin/bash
# Multi-turn walk: opening ask, then client-style answers at each checkpoint via --resume. usage: bash run-mt2.sh <name> [--run2]. run-mt.sh + fixes after run5: MSYS path conversion left ON (production shape), CLAUDE_PLUGIN_ROOT set (Desktop expands it; headless does not), synced shortform copy moved aside before each turn
# State lives outside the repo: home/ (scratch Claude profile; the login file is copied in below), proj/, logs/, synced-aside/.
# --run2 (or RS_WALK_RUN2=1): a second reel in the same project with no reset; the loop stops on a finished script whose name or content was not there at start (a reused or overwritten slug counts).
S="$(cygpath -m "${RS_WALK_STATE:-$HOME/rs-walk-state}")"; H="$S/home"; L="$S/logs"; N="$1"
RUN2="${RS_WALK_RUN2:-}"; [ "$2" = "--run2" ] && RUN2=1
# The plugin under test is the one in this repo, found from this script's own location.
R="$(cygpath -m "$(cd "$(dirname "$0")/../../.." && pwd)")/plugins/shortform-superengine"
[ -d "$R" ] || { echo "refuse: no plugin at $R"; exit 2; }
[ -d "$H/.claude" ] && [ -d "$S/proj" ] || { echo "refuse: no home/.claude or proj under $S (set RS_WALK_STATE, run reset.sh)"; exit 2; }
mkdir -p "$L"
ls "$L/$N"-t*.jsonl >/dev/null 2>&1 && { echo "refuse: $N exists"; exit 2; }
# One line per finished script: "<name> <sha256 of its content>", so a changed file is a new line.
finished() { for f in "$S/proj/scripts/"*.md; do [ -f "$f" ] || continue; case "${f##*/}" in *skeleton*) continue;; esac; echo "${f##*/} $(sha256sum < "$f" | cut -d' ' -f1)"; done | sort; }
START=""; [ -n "$RUN2" ] && START="$(finished)"
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL
cp "$HOME/.claude/.credentials.json" "$H/.claude/.credentials.json"
export HOME="$H" USERPROFILE="$(cygpath -w "$H")"
for v in $(env | grep -o -E "^(CLAUDE[A-Z_]*|ANTHROPIC[A-Z_]*)"); do unset "$v"; done
export CLAUDE_PLUGIN_ROOT="$R"
mkdir -p "$S/synced-aside"
cd "$S/proj" || exit 1
FLAGS=(--plugin-dir "$R" --model sonnet --max-budget-usd 1.50 --output-format stream-json --verbose --strict-mcp-config --permission-mode bypassPermissions)
ANS=("Write a reel script for me from my competitor analysis."
     "Yes, that voice is right. Go ahead."
     "Option 1."
     "Approved, lock it."
     "Go with your top-scored option."
     "Go with your top-scored option."
     "Go with your top-scored option."
     "Go with your top-scored option."
     "Looks good, finish it."
     "Looks good, finish it.")
SID=""
for i in "${!ANS[@]}"; do
  OUT="$L/$N-t$i.jsonl"
  for p in "$H"/.claude/plugins/synced/*/shortform-superengine; do [ -d "$p" ] && { rm -rf "$S/synced-aside/sf-$i"; mv "$p" "$S/synced-aside/sf-$i"; echo "turn $i: moved synced shortform aside"; }; done
  if [ -z "$SID" ]; then claude -p "${ANS[$i]}" "${FLAGS[@]}" > "$OUT" 2> "$OUT.err"
  else claude -p "${ANS[$i]}" --resume "$SID" "${FLAGS[@]}" > "$OUT" 2> "$OUT.err"; fi
  [ -z "$SID" ] && SID=$(grep -o '"session_id":"[^"]*"' "$OUT" | head -1 | cut -d'"' -f4)
  echo "turn $i sid=$SID lines=$(wc -l < "$OUT")"
  NEW="$(comm -13 <(echo "$START") <(finished))"
  [ -n "$NEW" ] && { echo "script written at turn $i: $NEW"; break; }
done
cat "$L/$N"-t*.jsonl > "$L/$N.jsonl"
