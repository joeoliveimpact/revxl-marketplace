---
name: email-sequence-superengine:email-winback-sequence
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

**Brain pull via `revxl-vault-search` ... structure check before the first email.** Fires
between step 2 and step 3 of the generator flow: config, campaign framework and voice
anchor are locked, nothing is drafted yet. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull for this campaign means no call, and the evidence line reads
`skipped (cached)`. No cache: ONE invocation of `workspace-superengine:revxl-vault-search`
with the Skill tool, args `depth=med plugin=email-sequence-superengine
spoke=email-reference-library question: win-back and sunset email sequence for a dormant list ... angles: reactivation open; stay-or-go decision email; sunset close`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Weave the hits in as STRUCTURE (touch order, how the reactivation open earns a reply, what the sunset close does), cited `[brain] <path>`, and
save the pull to `<project>/brain-pulls/<campaign-slug>.md`. At the review checkpoint (flow step 5) print exactly one
line: `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
Optional second pull, only when the first came back with nothing usable on subject lines
or the CTA: `depth=low plugin=email-sequence-superengine spoke=content-strategy question:
subject-line hooks and CTA moves for a win-back and sunset sequence ... angles: reactivation open; stay-or-go ask`. `med` is
1 search + up to 2 note reads, `low` is 1 search + 0 reads, so both together spend
2 searches + 2 reads against this step's cap of at most 2 searches + 3 note reads.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep building. The Brain never blocks a sequence.
