---
name: email-sequence-superengine:winback
description: Build a 3-touch win-back / sunset sequence that reactivates cold or churned contacts, or cleanly sunsets them. Trigger phrases include "winback sequence", "reactivate cold leads", "win back churned clients", "sunset emails".
---

# Task: winback

Build the 3-touch win-back / sunset sequence (broadcast: built once, fires to dormant contacts).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/winback-framework.md

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the winback framework above. Output 3 emails
(D1 / D7 / D14), all text-only. D3 must drive the stay/go decision — the deliverability win (suppress
non-responders after the window) is the point. Never guilt-trip.
