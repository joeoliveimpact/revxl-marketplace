---
name: meta-ads-superengine:meta-ads-ad-copy
description: Writes the primary text and headlines for each ad concept using proven copy frameworks (PAS, BAB, Claim-Reason-Outcome and more), inside Meta's character limits, in the coach's voice, with up to 5 in-ad copy variants. Trigger phrases include "write my ad copy", "primary text", "ad headlines", "write the ad".
---

# meta-ads-ad-copy — primary text + headlines

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #15.

## Load
- shared refs + `${CLAUDE_PLUGIN_ROOT}/skills/meta-ads-ad-copy/references/copy-frameworks.md`
- Active brand state → `creatives` (concept rows + hooks when written)
- Active brand state → `compliance[]` (entry matching current `offer_version`) → constraints
- Voice: `~/.claude/revxl/<brand>/voc/`

## Prereq (E0)
Concept rows exist. Missing → creative-strategy.

## Steps

**1. Voice check (F10 if cold)** — voc/ absent → reuse `voice_sketch` if
present (no re-interview), else capture and write it; low-confidence label,
never silent.

**2. Per concept:** pick the framework by awareness level (pairing table in
copy-frameworks.md), write primary text + headline sets:
- 125 visible chars carry the payload (write for the visible zone).
- Headline ≤40, front-loaded.
- **5-slot variants inside ONE ad** — up to 5 primary texts + headlines per
  ad, never 5 separate ads.
- Avatar's real language from voc-profile; AI-tells avoided; real numbers
  only; default CTA button + strong in-copy CTA.
- Active constraints (from `compliance[]` for the current `offer_version`)
  stated up front and respected: copy that would violate one is not offered,
  with the constraint named.

**3. Brain (1 search + up to 2 reads, via `revxl-vault-search`).** Invoke
`workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=meta-ads-superengine spoke=meta-ads-strategy question: ad copy
for coaching offers ... angles: <awareness stage> message frame; long copy vs
short copy`. Self-evidencing line; degrade F9.

**4. Write** the copy blocks artifact (paste-ready per concept, slots
labeled); note its path on each concept row's own `artifacts.copy` key (never touch another kind's key).

## Terminal paths — inline blocks (routing.md grammar)

**Copy delivered (E11):** preamble names the artifact, then:

**Next moves**
1. *If static concepts await:* design directions for the images this copy sits on. Say: "make static ads"  ← start here *(when statics are next in the mix)*
   *If video concepts await:* script them. Say: "write my video script"
2. Copy for the next concept batch. Say: "write my ad copy"
3. *If all S1 concepts now have assets:* build the campaign structure. Say: "plan my campaign"

**Next moves — voice cold (F10)**
1. Build your brand brain — copy is where a borrowed voice shows most. Say: "build my brand brain" *(if installed)*
2. Proceed labeled low-confidence.

## Teach mode
In `new`: plain-English-first — "primary text" and "headline" located on an
actual ad ("the words above the picture / the bold line under it"); the
5-slot rule explained with the bundling why ("what this means for you: five
versions in one ad teach Meta faster than five competing ads"); frameworks
named AFTER a worked example. In `learning`: gloss PAS/framework names first
use. In `pro`: the copy blocks, terse.

## Guardrails
- **Zero unattributed stats** in any output — the framework's old "+22%"
  style numbers are laundered and stripped (canon).
- Char limits enforced at write time, not after.
- No fake scarcity; only promises the coach will keep.
