---
name: carousel-superengine:carousel-create
description: Core generator. Turn a topic, avatar pain, story, reel script, transcript, or teardown into a complete carousel package with slide-by-slide copy, design directions, caption, and hashtags in the coach's voice. Trigger phrases include "build a carousel", "carousel about", "make this a carousel", "turn this into a carousel", "carousel from this teardown".
---

# Task: create

Input in → complete carousel package out. Never a thin draft.

## Load
${CLAUDE_PLUGIN_ROOT}/references/business-config.md (stop → route to `carousel-setup` if placeholders)
${CLAUDE_PLUGIN_ROOT}/references/exemplar-carousel.md — **study FIRST, match its density**
${CLAUDE_PLUGIN_ROOT}/references/slide-architecture.md · hook-patterns.md · swipe-retention.md · cta-slide-patterns.md · design-rules.md · caption-strategy.md
${CLAUDE_PLUGIN_ROOT}/references/platform-nuance.md (when platform is linkedin/both)
${CLAUDE_PLUGIN_ROOT}/templates/carousel-package.md (output shape)
${CLAUDE_PLUGIN_ROOT}/references/carousel-quality.md (gate, before delivery)

**Voice (in order):** shared brain `~/.claude/revxl/<brand>/voc/` (voice-guide + voc-profile +
signature-bits where present... honor `provisional` stamps and freshness per the brain's own rules) →
config interim anchors → if neither, offer the bundled `brand-brain` skill before writing in a
generic voice. Write at `{{VOICE_EDGE}}`.

## Flow

**1. Resolve the input.** One of: topic/pain ("carousel about X") · idea request (generate 3-5
options from the 6 topic frameworks × `{{CONTENT_PILLARS}}` × `{{AVATAR_PAINS}}`, coach picks) ·
repurpose (reel script / transcript / post — extract the core idea + strongest lines, credit the
source medium's beats) · teardown output (borrow STRUCTURE only; every atom of content becomes the
coach's).

**2. Lock the frame (confirm with the coach in one message):** platform · objective (save / share /
DM / follow — sets the CTA pattern) · blueprint (A educational / B story-led / C case-study — see
slide-architecture) · the ONE avatar pain this hits. Blueprint C requires a REAL client story from
config/VoC... if the bank is thin, elicit now (3 quick questions) or pivot to A/B. Never invent.

**3. Map before copy.** Build the slide map (n / role / job-in-≤12-words) per the blueprint +
5-pillar arc. Triple Hook on slides 1-3. Show the map with **one Brain status line** —
`Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`; the
pull must leave a visible trace either way. Beginner levels get one plain-English line
on why this order. Adjust on feedback, then write.
   **Brain pull #1 (Trigger 1 of 2):** resolve the Brain key per
   `${CLAUDE_PLUGIN_ROOT}/references/vault-api.md` (ladder: env → `~/.config/revxl/vault_api_key`
   → ask once). **Check `brain-pulls/` in the working folder first** — a cached pull for this
   topic means no call. Key + no cache: ONE `/v1/search` — `query` = the carousel's topic/pain,
   `variants` shaped by the blueprint locked in step 2 (**query recipes** — the row always
   exists because step 2 forces the pick):
   | Blueprint | variants |
   |---|---|
   | A educational | `["educational carousel structure", "<topic> framework"]` |
   | B story-led | `["story-led carousel", "story arc retention"]` |
   | C case-study | `["case study carousel", "proof content structure"]` |
   Always append the raw topic/pain as its own variant. Input leaning across two blueprints →
   take one variant from each row. Recipes shape `variants` only — `query` stays the topic/pain,
   and hybrid search mode forgives imperfect fits; **never skip the pull because the content
   doesn't fit a mold.** Save the cited hits to `brain-pulls/<topic-slug>.md` and weave them
   into the slide map as extra evidence, cited `[brain] <path>`. No key / 4xx / 5xx / timeout →
   follow the reference's degrade table and move on — the Brain never blocks a carousel.

**4. Write the package** per the template: 3 hook alternates (different archetypes) with a
recommended pick + reason — **Brain pull #2 (Trigger 2 of 2, optional):** if the key resolves
and the hook bank feels stale or thin, ONE `/v1/search` — `query` = `hook <archetype> <topic>`
using the archetype you're drafting (one variant per archetype when drafting across several;
no clean archetype → plain `hook <topic>`) + up to 3 `/v1/note` reads on the top hits; current
hook patterns beat frozen ones. Cache to
`brain-pulls/`, cite `[brain] <path>`, same degrade rules; **total Brain budget for the whole
carousel: ≤2 searches + ≤3 note reads, never inside loops** · per-slide copy (20% rule, 25-50 words, bold skim path) · per-slide
design direction (executable by a non-designer) + retention device · soft CTA on the summary slide,
hard CTA per the chosen pattern wired to `{{CTA_DESTINATION}}` · caption (4-part, 150-300 words,
keyword front-loaded) · 3-5 narrow hashtags · per-slide alt text · platform delta block when `both`.
Entertainment-first doctrine: the carousel earns attention before it teaches; dose the personality
per voice edge. Numbers/results only from `{{PROOF_ASSETS}}`.

**5. Gate + deliver.** Run carousel-quality.md end to end; fix fails silently. Deliver per
`{{OUTPUT_DESTINATION}}` as a DRAFT for approval. With `{{TEACH_MODE}}` on, close with 2-3 plain
"why this works" lines (the craft, not a lecture). Offer the natural next: the platform variant, a
second topic from the idea engine, or schedule notes.

## Rules
- Drafts only; the coach posts. No scheduling promises.
- No em dashes in any client-facing copy ("..." for pauses). House rule, absolute.
- Suggest-then-approve on hooks and any offer-specific claim.
- A package below exemplar density does not ship.
