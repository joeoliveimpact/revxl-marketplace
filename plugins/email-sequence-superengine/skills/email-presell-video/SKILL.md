---
name: email-sequence-superengine:email-presell-video
description: Write a 5-7 minute pre-sell VSL script (spoken) that warms a prospect before a booked call. Trigger phrases include "precall video script", "VSL script", "pre-sell video", "video before the call".
---

# Task: precall-video-script

Build the 5-7 min pre-sell VSL script (broadcast: ONE script, recorded once, shown to every booked prospect).
Output is a SPOKEN SCRIPT, not an email sequence.

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/precall-video-framework.md
${CLAUDE_PLUGIN_ROOT}/references/story-engines.md (story dose: HEAVY — §2-3 are spoken story beats)

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md for steps 1-2 (read config, load framework + voice anchor) and the
non-generic rule. Then DEVIATE for output:
- Generate a spoken script in 4 sections with timestamps (see framework table), written for the EAR in the
  coach's voice. Name the avatar's failed past attempts + #1 objection; no individual facts.
- Skip the email-specific template/checklist items (subject/preview/format-mode). Still run the voice-match,
  non-generic, broadcast-safe, and no-em-dash gates from ${CLAUDE_PLUGIN_ROOT}/references/sequence-quality.md.
- Deliver to `{{OUTPUT_DESTINATION}}` as a draft script. Note it pairs with precall E2 (the email links to it).
