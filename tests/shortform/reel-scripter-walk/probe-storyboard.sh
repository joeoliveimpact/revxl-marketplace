#!/bin/bash
# SKLLPLG-367 live probe: does hooks/storyboard-on-write.py fire on a real headless Write and make the model fix the file?
# One claude -p run ($1.00 cap) is told to Write a final script whose storyboard has exactly one defect (row 2 runs 8 s).
# Hook feedback is not recorded in stream-json on this build (measured 10.02.26), so the proof is behavioural. PASS needs:
# (a) the first Write landed the defect, (b) a later Write/Edit/MultiEdit of the same file (the prompt allows a change only
# when a tool or hook reports a problem, and nothing else names the defect), (c) zero storyboard_problems on disk. Exit 0 PASS, 1 FAIL, 2 refused.
# State lives outside the repo: <state> = RS_PROBE_STATE, default $HOME/rs-walk-state/probe367 (home/, proj/, probe.jsonl).
# Invocation shape mirrors run-mt2.sh: scratch HOME/USERPROFILE with no login file, CLAUDE*/ANTHROPIC* unset, then the walk-only
# token (RS_WALK_TOKEN, default $HOME/.config/rs-walk/walk-token) passed as CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_PLUGIN_ROOT set,
# MSYS path conversion left on, synced shortform copies moved aside. Never reads ~/.claude/.credentials.json (SKLLPLG-369). usage: bash probe-storyboard.sh
S="$(cygpath -m "${RS_PROBE_STATE:-$HOME/rs-walk-state/probe367}")"; H="$S/home"; P="$S/proj"; LOG="$S/probe.jsonl"
R="$(cygpath -m "$(cd "$(dirname "$0")/../../.." && pwd)")/plugins/shortform-superengine"
F="$P/scripts/probe-water.md"
[ -d "$R" ] || { echo "refuse: no plugin at $R"; exit 2; }
TF="${RS_WALK_TOKEN:-$HOME/.config/rs-walk/walk-token}"
WT="$({ tr -d ' \r\n' < "$TF"; } 2>/dev/null)"
case "$WT" in sk-ant-oat*) ;; *) echo "refuse: no walk token in $TF (run claude setup-token, save it there)"; exit 2;; esac
rm -rf "$P" && mkdir -p "$P/scripts" "$P/reel-build" "$H/.claude" "$S/synced-aside" || exit 2
echo '{}' > "$P/analysis-data.json"
FIX="$(cat <<'EOF'
# Water before meals

## Script
Hook: You are not hungry. You are thirsty.
Body: Drink a full glass of water ten minutes before each meal for one week and watch what your portions do.
CTA: Follow for one small habit a day.

## Text overlays
| Beat | Seconds | Overlay | Visual cue |
|---|---|---|---|
| Hook | 0:00-0:04 | Not hungry. Thirsty. | Close-up to camera |
| Body | 0:04-0:12 | One glass, ten minutes before | Pour a glass of water |
| CTA | 0:12-0:16 | Follow for one habit a day | Point at the follow button |
EOF
)"
MSG="Use the Write tool to save the markdown between the BEGIN and END lines below to $F, as given (leave out the BEGIN and END lines). If a tool or hook then reports a problem with the file, fix the file and save it again. Then reply done.
BEGIN
$FIX
END"
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL
rm -f "$H/.claude/.credentials.json"
export HOME="$H" USERPROFILE="$(cygpath -w "$H")"
for v in $(env | grep -o -E "^(CLAUDE[A-Z_]*|ANTHROPIC[A-Z_]*)"); do unset "$v"; done
export CLAUDE_PLUGIN_ROOT="$R" CLAUDE_CODE_OAUTH_TOKEN="$WT"
for p in "$H"/.claude/plugins/synced/*/shortform-superengine; do [ -d "$p" ] && { rm -rf "$S/synced-aside/sf"; mv "$p" "$S/synced-aside/sf"; echo "moved synced shortform aside"; }; done
cd "$P" || exit 2
claude -p "$MSG" --plugin-dir "$R" --model sonnet --max-budget-usd 1.00 --output-format stream-json --verbose --strict-mcp-config --permission-mode bypassPermissions > "$LOG" 2> "$LOG.err"
echo "claude exit $? lines=$(wc -l < "$LOG") log=$LOG"
PYTHONIOENCODING=utf-8 py -3.12 - "$LOG" "$F" "$R" <<'EOF'
import json, sys
log, f, r = sys.argv[1:]
sys.dont_write_bytecode = True
sys.path.insert(0, r + "/skills/reel-scripter")
import structure_gate as g
lines = open(log, encoding="utf-8").read().splitlines()
writes = []
for l in lines:
    try:
        m = json.loads(l)
    except ValueError:
        continue
    if m.get("type") != "assistant":
        continue
    for c in m.get("message", {}).get("content", []):
        if (c.get("type") == "tool_use" and c.get("name") in ("Write", "Edit", "MultiEdit")
                and str(c.get("input", {}).get("file_path", "")).replace("\\", "/").lower().endswith("scripts/probe-water.md")):
            writes.append(c.get("input", {}))
first = writes[0].get("content", "") if writes else ""
again = len(writes) - 1
try:
    probs = g.storyboard_problems(open(f, encoding="utf-8-sig").read())
except OSError as e:
    probs = [f"unreadable: {e}"]
res = [("a", bool(writes) and bool(g.storyboard_problems(first)), f"first Write carried the planted defect: {g.storyboard_problems(first) if writes else 'no Write'}"),
       ("b", again > 0, f"Write/Edit/MultiEdit of the script after the first Write: {max(again, 0)}"),
       ("c", not probs, f"storyboard_problems on final file: {probs or 'none'}")]
for k, ok, what in res:
    print(f"{'PASS' if ok else 'FAIL'} ({k}) {what}")
ok = all(x[1] for x in res)
print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
EOF
