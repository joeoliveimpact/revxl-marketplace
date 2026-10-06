#!/bin/bash
# PostToolUse and PostToolUseFailure on Bash|PowerShell (SKLLPLG-370): start Python (run-py.sh + the script in $1,
# storyboard-on-write.py) only when this call's PreToolUse left a snapshot, ~/.claude/shortform-superengine/
# script-snap/<tool_use_id>.json. The Pre writes one only inside a reel project, so a terminal call anywhere else
# costs one bash start here instead of a Python start. Looks under $HOME and %USERPROFILE%, either of which Python's
# home can be. No tool_use_id in stdin: hand over to Python, which decides. Never prints; exit code passes through.
# usage (hooks.json): bash "${CLAUDE_PLUGIN_ROOT}/hooks/script-post.sh" "${CLAUDE_PLUGIN_ROOT}/hooks/storyboard-on-write.py"
in="$(cat)"
re='"tool_use_id"[[:space:]]*:[[:space:]]*"([^"]*)"'
if [[ $in =~ $re ]]; then
  f=".claude/shortform-superengine/script-snap/${BASH_REMATCH[1]//[!A-Za-z0-9_-]/_}.json"
  u="${USERPROFILE//\\//}"
  [ -f "$HOME/$f" ] || { [ -n "$u" ] && [ -f "$u/$f" ]; } || exit 0
fi
exec bash "${0%/*}/run-py.sh" "$1" <<<"$in"
