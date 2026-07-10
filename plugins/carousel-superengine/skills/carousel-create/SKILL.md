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
${CLAUDE_PLUGIN_ROOT}/references/transcript-intake.md (when the input is a call/meeting — paste-first)
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
source medium's beats) · **call build** ("carousel from my last call / my call with <name>" — resolve
the transcript per transcript-intake.md: pasted text wins, else fetch from `{{TRANSCRIPT_SOURCE}}`,
else build from the coach's memory with the gap flagged) · teardown output (borrow STRUCTURE only;
every atom of content becomes the coach's) · **template preset** (arriving via `carousel-templates`
use-template — the look is already decided; skip design questions, copy + strategy only).

**2. Lock the frame (confirm with the coach in one message):** platform · objective (save / share /
DM / follow — sets the CTA pattern) · blueprint (A educational / B story-led / C case-study — see
slide-architecture) · the ONE avatar pain this hits. Blueprint C requires a REAL client story from
config/VoC... if the bank is thin, elicit now (3 quick questions) or pivot to A/B. Never invent.

**3. Map before copy.** Build the slide map (n / role / job-in-≤12-words) per the blueprint +
5-pillar arc. Triple Hook on slides 1-3. Show the map... beginner levels get one plain-English line
on why this order. Adjust on feedback, then write.

**4. Write the package** per the template: 3 hook alternates (different archetypes) with a
recommended pick + reason · per-slide copy (20% rule, 25-50 words, bold skim path) · per-slide
design direction (executable by a non-designer) + retention device · soft CTA on the summary slide,
hard CTA per the chosen pattern wired to `{{CTA_DESTINATION}}` · caption (4-part, 150-300 words,
keyword front-loaded) · 3-5 narrow hashtags · per-slide alt text · platform delta block when `both` ·
**render handoff:** one line per slide tagging it template-text (clean layout system) or
custom-visual (designer-tier craft) — this is what `carousel-render` routes on.
Entertainment-first doctrine: the carousel earns attention before it teaches; dose the personality
per voice edge. Numbers/results only from `{{PROOF_ASSETS}}`.

**5. Gate + deliver.** Run carousel-quality.md end to end; fix fails silently. Deliver per
`{{OUTPUT_DESTINATION}}` as a DRAFT for approval. With `{{TEACH_MODE}}` on, close with 2-3 plain
"why this works" lines (the craft, not a lecture).

## Ends with (offer, never block)
- **"Want the images now?"** → `carousel-render` — "make the images" (the package is render-ready;
  images are where it becomes a post)
- Platform variant when config isn't `both` → "make the LinkedIn version"
- Second topic from the idea engine → "another one about ___"
- (When `{{SCHEDULE_STATUS}}` is unset, once per session) "Want a fresh draft like this on a
  schedule? Weekly or daily, from your topics or your latest calls — you approve every one." →
  scheduled-builds flow (${CLAUDE_PLUGIN_ROOT}/references/scheduled-builds.md)

## Rules
- Drafts only; the coach posts. Scheduling drafts BUILDS on request — posting is never scheduled.
- No em dashes in any client-facing copy ("..." for pauses). House rule, absolute.
- Suggest-then-approve on hooks and any offer-specific claim.
- A package below exemplar density does not ship.
