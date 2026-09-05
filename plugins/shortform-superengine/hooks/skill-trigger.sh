#!/bin/bash
# UserPromptSubmit hook: if the prompt contains one of the shortform-superengine
# skills' trigger phrases, inject one line naming the skill to invoke before
# doing the work by hand. Ported from promptception/hooks/orchestrator-trigger.sh.
# Greps raw stdin rather than parsing a specific JSON field so it survives
# input-schema drift across Claude Code versions. Exit 0 always; stdout (if any)
# is added to context. Empty or malformed stdin -> no output (fail-open).
set -euo pipefail

input=$(cat)

# Deliberately narrower than the skills' description trigger lists: generic
# words ("harvest", "cross-reference", "onboard") false-positive on everyday
# prompts. The descriptions still carry them; the hook only fires on the
# unmistakable invocations. First match wins; exactly one line is printed.
ONBOARDING='set up shortform|onboard shortform|shortform setup|(install|configure) the reel plugin|get the shortform superengine ready|finish setting up the content engine'
REEL_SCRIPTER='write a reel script|script a reel|reel script|reel-scripter|script the next reel|weekly topic pool|idea bank'
CROSS_REFERENCE='competitor cross-reference|cross-reference my client|content gap analysis|build my visual dashboards|regenerate my visuals'
PULSE='run the weekly pulse|competitor pulse|what changed this week|refresh my competitor analysis|manage my roster|comment pulse|mine the comments on'
BRAND_BRAIN='capture my voice|build my brand brain|brand brain|mine my calls|set up my voice|refresh my voice guide|update my topics'
HARVEST='harvest .{0,40}(library|content|videos)|get everything .{0,40} teaches|pull all of .{0,40} content|build a corpus from|refresh our notebook on'
SOCIALCRAWL='socialcrawl|social crawl|social media api'

nudge() {
  echo "[shortform-superengine] This looks like a job for the $1 skill ... invoke it (Skill tool) before doing the work by hand."
}

if echo "$input" | grep -qiE "$ONBOARDING"; then
  nudge onboarding
elif echo "$input" | grep -qiE "$REEL_SCRIPTER"; then
  nudge reel-scripter
elif echo "$input" | grep -qiE "$CROSS_REFERENCE"; then
  nudge competitor-cross-reference
elif echo "$input" | grep -qiE "$PULSE"; then
  nudge competitor-pulse
elif echo "$input" | grep -qiE "$BRAND_BRAIN"; then
  nudge brand-brain
elif echo "$input" | grep -qiE "$HARVEST"; then
  nudge creator-strategy-harvest
elif echo "$input" | grep -qiE "$SOCIALCRAWL"; then
  nudge socialcrawl
fi

exit 0
