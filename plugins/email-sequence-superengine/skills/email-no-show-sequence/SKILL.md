---
name: email-sequence-superengine:email-no-show-sequence
description: Build a 4-touch reschedule sequence that blamelessly rebooks prospects who no-showed a call. Trigger phrases include "no-show emails", "rebook no-shows", "reschedule sequence", "they didn't show".
---

# Task: no-show-recovery

Build the 4-touch no-show reschedule sequence (broadcast: built once, fires when a session is marked no-show).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/no-show-recovery-framework.md

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the no-show framework above. Output 4 emails
(+15min / +24h / D5 / D10), all text-only. Empathy-first, never guilt-trip. E1 under 4 sentences with 2
alt slots. D10 is a clean blameless breakup with a self-service booking link.

**Brain pull via `revxl-vault-search` ... structure check before the first email.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: reschedule email sequence after a missed call ... angles: blameless rebook ask; very short first email; clean breakup close`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (touch order, how the blameless ask is framed, what the breakup close does), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the review checkpoint (flow step 5) print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a no-show reschedule sequence ... angles: blameless rebook ask; breakup close`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a sequence.
