---
name: email-sequence-superengine:email-launch-promo-sequence
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

**Brain pull via `revxl-vault-search` ... structure check before the first email.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: seven-day open-cart launch email sequence ... angles: cart-open announcement; objection-strike email; deadline-day close`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (day-by-day order, what each open and close does, subject-line patterns worth testing), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the review checkpoint (flow step 5) print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a seven-day open-cart launch ... angles: cart-open hook; deadline-day close`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a sequence.
