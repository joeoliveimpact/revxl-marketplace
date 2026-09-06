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

**Brain pull via `revxl-vault-search` ... structure check before the first spoken line.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: pre-sell video script that warms a prospect before a booked call ... angles: spoken open; story beat order; close that hands off to the call`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (section order, the shape of the open, where the story beats sit, how the close hands off to the call), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the draft hand-off print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a pre-sell video before a booked call ... angles: spoken open; hand-off close`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a script.
