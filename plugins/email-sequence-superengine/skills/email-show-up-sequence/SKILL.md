---
name: email-sequence-superengine:email-show-up-sequence
description: Build a 4-email strategy-call show-up sequence (broadcast, fires to every prospect who books) that maximizes call show rate and pre-handles the #1 objection. Trigger phrases include "precall sequence", "show-up emails", "get prospects to show for the call", "pre-call nurture".
---

# Task: precall-nurture

Build the 4-email strategy-call show-up sequence (broadcast: built once, fires to EVERY prospect who books).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/precall-framework.md

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the precall framework above. Output 4 emails
(immediately / 24h / 4h / 1h before), text-only except E2 (light-HTML allowed). Precall-specific:
- E1 enforces an active confirmation reply (reply CONFIRMED) — micro-commitment + engagement signal.
- E2/E3 strike the avatar's #1 objection pre-emptively.
- One pre-call action max (the leak-list / scorecard) — no excessive homework.
- Fold in the Orchestrating-Trust upgrades from the framework (Diagnostic Bridge, transfer-of-trust video, blameless rebook hook in E4).

**Brain pull via `revxl-vault-search` ... structure check before the first email.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: pre-call show-up email sequence for a booked strategy call ... angles: reminder email structure; pre-handling the top objection; asking for a confirmation reply`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (email order, what each open and close does, subject-line patterns worth testing), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the review checkpoint (flow step 5) print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a pre-call show-up sequence ... angles: confirmation reply; objection pre-handle`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a sequence.

Canonical broadcast example: ${CLAUDE_PLUGIN_ROOT}/references/exemplar-precall-sequence.md
