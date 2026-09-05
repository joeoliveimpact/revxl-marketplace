---
name: meta-ads-superengine:meta-ads-static-ads
description: Turns ad concepts into still-image ad designs a non-designer can execute — layout patterns, safe zones, long-copy statics for cold traffic, and carousel structures. Produces Canva-executable design directions per concept. Trigger phrases include "make static ads", "image ads", "design my ads", "static ad ideas".
---

# meta-ads-static-ads — still-image production

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #16.

## Load
- shared refs + `${CLAUDE_PLUGIN_ROOT}/skills/meta-ads-static-ads/references/static-patterns.md`
- Active brand state → `creatives` (static-format concept rows + their copy)
- Active brand state → `compliance[]` (entry matching current `offer_version`) → constraints
- Voice/brand look: voc/ if it carries visual notes; else ask once

## Prereq (E0)
Concept rows exist. Missing → creative-strategy.

## Steps

**1. Per static concept:** pick 1–2 layout patterns matching its awareness
level + driver (emotional → authentic/handwritten/before-after; logical →
framework-overlay/long-copy). **Constraint gate (before/after):** before
offering before/after, read `compliance[]` for the current `offer_version`.
A current-version constraint that bans it → do NOT offer it; name the
constraint as the reason and offer the nearest compliant alternative from
static-patterns.md (framework-overlay or color-block testimonial). No
current-version entry (constraints unknown) → offer it with the flag behavior
below and note the compliance check hasn't run for this offer version. A
current-version entry with no such constraint → proceed. **Voice check (F10 if cold):** on-image words
are voice-sensitive — voc/ absent → reuse `voice_sketch` if present (no
re-interview), else capture and write it; label voice-confidence low, never
silent-generic. Write the design direction:
- exact on-image text (hook-grade, 40-char front-load, from the concept's
  copy blocks — or generated hook-grade inline when ad-copy hasn't run yet)
- layout pattern + composition notes a non-designer executes in Canva
- **4:5 spec; 9:16 variant with safe zones 14/35/6 respected** — call out
  the middle band placement explicitly
- designed AND plain variants for long-copy statics (run both).

**2. Boundary:** multi-slide carousel production → carousel-superengine
when installed (one pointer line); this skill designs single statics +
carousel STRUCTURE only.

**3. Brain (1 search + up to 2 reads, via `revxl-vault-search`).** Invoke
`workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=meta-ads-superengine spoke=meta-ads-strategy question: static
ad cold traffic coaching ... angles: long copy; pattern interrupt`. Self-evidencing
line; degrade F9.

**4. Write** the design-directions artifact; note its path on each concept row's own `artifacts.static` key (never touch another kind's key).

**Renderer note (appendix, not wired):** an optional FAL image renderer
exists in the developer repo's research corpus
— a P5 decision, not offered to coaches in v1. Canva is the path.

## Terminal paths — inline blocks (routing.md grammar)

**Directions delivered (E11):** preamble: the outside-Claude step ("Build
these in Canva; export 4:5 + 9:16; keep them on your drive — launch uploads
them PAUSED"), then:

**Next moves**
1. *If video concepts await:* script them next. Say: "write my video script"  ← start here *(when video is next in the mix)*
2. *If all S1 concepts now have assets:* build the campaign structure. Say: "plan my campaign"
3. Directions for the next static batch. Say: "make static ads"

**Next moves — voice cold (F10)**
1. Build your brand brain — on-image text in a borrowed voice reads as an ad, not you. Say: "build my brand brain" *(if installed)*
2. Proceed labeled low-confidence — upgrade later without redesigning.

## Teach mode
In `new`: plain-English-first — "static ad" deep-glossed (a still image
with words — and why plain text-heavy images often beat video for cold
coaching audiences); "safe zones" deep-glossed with the consequence line
("text at the edges literally can't be read"); every pattern named after
its plain description. In `learning`: gloss safe zones/4:5 first use. In
`pro`: pattern + direction per concept, terse.

## Guardrails
- Safe zones 14/35/6 ONLY (the 10/10 rule is wrong — canon).
- No unattributed stats on-image; real numbers, real deadlines.
- Before/after imagery, three-state per current `offer_version` constraint:
  banned → blocked; unknown (no current-version entry) → flag for the
  compliance gate per-offer; clear → proceed.
