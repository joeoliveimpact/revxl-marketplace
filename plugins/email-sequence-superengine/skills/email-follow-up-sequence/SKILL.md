---
name: email-sequence-superengine:email-follow-up-sequence
description: Build a 4-touch no-close follow-up sequence that keeps a prospect who didn't buy on the call moving toward yes. Trigger phrases include "post-call follow-up", "follow up after the call", "they didn't close", "after-call emails".
---

# Task: post-call-followup

Build the 4-touch post-call (no-close) follow-up sequence (broadcast: built once, fires when a call logs no-close).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/post-call-followup-framework.md
${CLAUDE_PLUGIN_ROOT}/references/story-engines.md (story dose: HEAVY on E2 — Third-Person Proof case story)

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the post-call framework above. Output 4 emails
(+2h / D3 / D10 / D17), all text-only. E1 recap anchors the avatar's shared pains in their words (not one
prospect's call). D2 case study features the avatar's #1 objection. D17 is a respectful breakup.

**Brain pull via `revxl-vault-search` ... structure check before the first email.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: follow-up email sequence after a sales call that did not close ... angles: recap open; third-person proof story; respectful breakup`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (touch order, the shape of the recap open, where the proof story sits), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the review checkpoint (flow step 5) print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a post-call follow-up sequence ... angles: recap open; proof-story close`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a sequence.
