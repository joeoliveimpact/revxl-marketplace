---
name: meta-ads-superengine:meta-ads-video-script
description: Writes shootable ad video scripts — quick 15-30 second direct versions and longer 90-120 second VSL teaching versions — in talking-head, UGC, or VSL architecture, teleprompter-formatted, in the coach's voice. Paid-native only; organic reels belong to the shortform engine. Trigger phrases include "write my video script", "ad video script", "VSL script", "script my ad".
---

# meta-ads-video-script — shootable scripts

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #17.

## Load
- shared refs + `${CLAUDE_PLUGIN_ROOT}/skills/meta-ads-video-script/references/script-structures.md`
- Active brand state → `creatives` (video-format concept rows + hooks/copy)
- Active brand state → `compliance[]` (entry matching current `offer_version`) → constraints
- Voice: `~/.claude/revxl/<brand>/voc/`

## Prereq (E0)
Concept rows exist. Missing → creative-strategy.

## Steps

**1. Voice check (F10 if cold)** — scripts are SPOKEN; a borrowed voice is
loudest here. voc/ absent → reuse `voice_sketch` if present (no re-interview),
else capture and write it. Low-confidence label, never silent.

**2. Per video concept:** pick the architecture (VSL / talking-head / UGC
per the concept's awareness + driver), then write BOTH lengths where the
concept supports it (bipolar rule): the 15–30s direct cut AND the 90–120s
VSL — each with word-for-word lines + direction cues (Silent Stare, B-roll
moments, caption emphasis), teleprompter-formatted. Active constraints (from
`compliance[]` for the current `offer_version`) are stated up front and
respected: a script that would violate one is not offered, with the constraint
named.

**3. Pacing pass:** hook in frame zero, no hard pitch before ~1:15 on the
VSL, captions noted as mandatory, 4:5 + 9:16 export note with safe zones.

**4. Post-ID note:** if the coach posts Reels, recommend the organic-first
path (publish → run the winner via its Post ID) — coordinates with
best-content.

**5. Brain (1 search).** Recipe = format(video/vsl) row keyed to the
architecture. Self-evidencing line; degrade F9.

**6. Write** the script artifact; note its path on each concept row's own `artifacts.script` key (never touch another kind's key).

## Boundary (family — no dupes)
Paid-native scripts only (offer-CTA, VSL). Organic reels = the
shortform-superengine's reel-scripter; Post-ID bridges the two. AI-avatar
route: surface the C2PA label + trust cost caveat, real footage
recommended; Higgsfield directors = operator appendix, not a coach path.

## Terminal paths — inline blocks (routing.md grammar)

**Scripts delivered (E11):** preamble: the outside-Claude step ("Film these
— phone + natural light beats a studio; keep exports on your drive, launch
uploads them PAUSED"), then:

**Next moves**
1. *If all S1 concepts now have assets:* build the campaign structure. Say: "plan my campaign"  ← start here *(when the mix is complete)*
2. Scripts for the next video concept. Say: "write my video script"
3. *If the coach posts Reels organically:* mine your winners — your best organic Reel + a 5-second CTA is a free ad. Say: "mine my winners"

**Next moves — voice cold (F10)**
1. Build your brand brain — a script that doesn't sound like you reads as an ad, not a person. Say: "build my brand brain" *(if installed)*
2. Proceed labeled low-confidence.

## Teach mode
In `new`: plain-English-first — VSL/UGC/talking-head deep-glossed (glossary
Section 3) BEFORE the acronyms; the late-CTA rule gets its "what this means
for you" ("fewer people finish the video, but the ones who do arrive
pre-sold"); direction cues explained ("Silent Stare = 2 seconds of eye
contact before you speak — it stops the scroll"). In `learning`: gloss
VSL/Post-ID first use. In `pro`: the scripts, terse.

## Guardrails
- Bipolar lengths (canon) — never a single one-size 30s script.
- No unattributed stats spoken in any script; real client results only,
  with consent.
- Safe zones + 4:5/9:16 always in the export note.
