---
name: meta-ads-superengine:meta-ads-hook-writer
description: Writes scroll-stopping hooks for each ad concept from a 29-formula library, on the coach's real avatar and offer, in their voice. Hooks are the first 3 seconds or first line — most of an ad's fate. Trigger phrases include "write hooks", "hook ideas", "first three seconds", "ad hooks".
---

# meta-ads-hook-writer — the first three seconds

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #14.

## Load
- shared refs + `${CLAUDE_PLUGIN_ROOT}/skills/meta-ads-hook-writer/references/hook-library.md`
- Active brand state → `creatives` (concept rows), `setup.offer`
- Voice: `~/.claude/revxl/<brand>/voc/` (voc-profile pains = hook raw material)

## Prereq (E0)
Concept rows exist. Missing → creative-strategy ("hooks serve a concept —
we design the concepts first").

## Steps

**1. Voice check (F10 if cold)** — as creative-strategy; voc/ absent → reuse
`voice_sketch` if present (no re-interview), else capture and write it;
low-confidence label, never silent-generic.

**2. Per concept:** pick 2–3 hook TYPES matching its awareness level (the
pairing table in hook-library.md), then write 3–5 hooks per concept using
the avatar's OWN words from voc-profile (specific beats clever: "tried
everything and my body just doesn't respond anymore" beats "weight loss
struggles"). Label h1/h2/… per naming grammar — CT-Tool variant IDs.

**3. 40-character check** on every hook (the mobile cutoff); flag any that
bury the payload.

**4. Brain (1 search).** Recipe = awareness row: query "hook <awareness
stage> coaching", variants keyed to the concept's pain. Self-evidencing
line; degrade F9.

**5. Write** the hook sheet artifact; note its path on each concept row's own `artifacts.hooks` key (never touch another kind's key).

## Terminal paths — inline blocks (routing.md grammar)

**Hooks delivered (E11):** preamble names the artifact + count per concept,
then:

**Next moves**
1. Write the body copy these hooks open — primary text + headlines per concept. Say: "write my ad copy"  ← start here
2. *If a video concept is next:* script it — the hook is the first beat. Say: "write my video script"
3. Hooks for the next concept batch. Say: "write hooks"
4. *If all S1 concepts now have assets:* build the campaign structure. Say: "plan my campaign"

**Next moves — voice cold (F10)**
1. Build your brand brain first — hooks in a borrowed voice waste the spend. Say: "build my brand brain" *(if installed)*
2. Proceed labeled low-confidence — upgrade later without rewriting concepts.

## Teach mode
In `new`: plain-English-first — the shop-window analogy for "hook"
(glossary deep tier) and why ~80% of an ad's job is done in 3 seconds
("what this means for you: we write many hooks per concept because this is
the highest-leverage sentence you'll ever write"). In `learning`: gloss
hook-rate/CT-Tool first use. In `pro`: the hook sheet, terse.

## Guardrails
- Hook numbers must be REAL (client counts, savings, timeframes the coach
  can defend) — canon rule 1, no laundered stats, no fake scarcity.
- Distinct hooks ≠ distinct concepts: hook variants stay INSIDE their
  concept (CT-Tool lane), never spawn near-duplicate ads.
