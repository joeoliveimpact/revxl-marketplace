---
name: email-sequence-superengine:launch
description: Build a 7-day open-cart launch email sequence (broadcast) for a program promotion or enrollment window. Trigger phrases include "launch sequence", "open cart emails", "promo sequence", "enrollment launch emails".
---

# Task: launch

Build the 7-day open-cart launch sequence (broadcast: built once, fires to the segment when cart opens).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/launch-framework.md
${CLAUDE_PLUGIN_ROOT}/references/story-engines.md (story dose: CORE — serialized arc, rotated engines, day-to-day open loops)

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the launch framework above. Output 7 emails (D1-D7),
intensifying the final 48h. Apply launch-specific notes: mail on deadline day (>50% of revenue); D5 strikes
the avatar's top 3 objections; D7 is short plain-text 4h before close.
