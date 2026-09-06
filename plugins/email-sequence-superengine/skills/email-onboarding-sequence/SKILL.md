---
name: email-sequence-superengine:email-onboarding-sequence
description: Build a 5-email 30-day new-client onboarding sequence that drives momentum and saves the day 10-14 dropoff. Trigger phrases include "onboarding emails", "new client sequence", "welcome sequence", "onboard new clients".
---

# Task: onboarding

Build the 5-email 30-day new-client onboarding sequence (broadcast: built once, fires on payment+signature).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/onboarding-framework.md

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the onboarding framework above. Output 5 emails
(immediately / D2 / D7 / D14 / D30). HTML allowed (in-program audience) but keep it personal. D1 must not
overload; D3 sets comms boundaries (reply "AGREED"). Belongs on the transactional subdomain.

**Brain pull via `revxl-vault-search` ... structure check before the first email.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: new-client onboarding email sequence over the first 30 days ... angles: welcome email structure; momentum email; saving the mid-program dropoff`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (send order across the 30 days, what each open and close does, where the momentum save sits), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the review checkpoint (flow step 5) print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a 30-day new-client onboarding sequence ... angles: welcome open; momentum save`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a sequence.
