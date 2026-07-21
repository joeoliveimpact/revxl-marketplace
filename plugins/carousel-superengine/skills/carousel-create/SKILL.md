---
name: carousel-superengine:carousel-create
description: Core generator. Turn a topic, avatar pain, story, reel script, transcript, or teardown into a complete carousel package with slide-by-slide copy, design directions, caption, and hashtags in the coach's voice. Trigger phrases include "build a carousel", "carousel about", "make this a carousel", "turn this into a carousel", "carousel from this teardown".
---

# Task: create

Input in → complete carousel package out. Never a thin draft.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md if present (the persisted filled config — read FIRST) → else ${CLAUDE_PLUGIN_ROOT}/references/business-config.md (shipped template only; placeholders → stop, route to `carousel-setup`)
${CLAUDE_PLUGIN_ROOT}/references/exemplar-carousel.md — **study FIRST, match its density**
${CLAUDE_PLUGIN_ROOT}/references/slide-architecture.md · hook-patterns.md · swipe-retention.md · retention-loops.md · cta-slide-patterns.md · design-rules.md · caption-strategy.md
${CLAUDE_PLUGIN_ROOT}/references/platform-nuance.md (when platform is linkedin/both)
${CLAUDE_PLUGIN_ROOT}/references/transcript-intake.md (when the input is a call/meeting — paste-first)
${CLAUDE_PLUGIN_DATA}/analysis/ when present (persisted inspire/teardown reports — read-only, consulted at step 1.5)
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
source medium's beats) · **provided final copy** ("here's my carousel, polish and package it" /
a staged draft — package it AS-IS: the step-1.5 scorecard grades it, and any change to their
words lands only with the coach's approval) · **call build** ("carousel from my last call / my call with <name>" — resolve
the transcript per transcript-intake.md: pasted text wins, else fetch from `{{TRANSCRIPT_SOURCE}}`,
else build from the coach's memory with the gap flagged) · teardown output (borrow STRUCTURE only;
every atom of content becomes the coach's) · **template preset** (arriving via `carousel-templates`
use-template — the look is already decided; skip design questions, copy + strategy only).

**1.5. Consult the data + winning check.** Locate the freshest inspire synthesis, beat dataset
(`beats-*.json`), and any relevant teardown for this niche/topic — `${CLAUDE_PLUGIN_DATA}/analysis/`
plus anything produced this session. Always say the report's age; >30 days is stale niche intel —
offer ONE `carousel-inspire` refresh (credit-gated as inspire always is) and proceed either way.
**Empty `analysis/` + any data-dependent config value** (`{{CTA_DESTINATION}}: per-build`, or a
skeleton choice that wants niche data): name the value that can't be honored without data and make
the inspire offer EXPLICIT — "your config says CTA per-build (decided from competitor data), but
no niche data exists yet; one inspire pull seeds it for ~30 days of builds — exact credits are
quoted at inspire's own checkpoint before anything spends" — then proceed on the coach's call.
Nothing there → judge from the avatar pain map + the bundled pattern refs alone — and when there's
also no SocialCrawl key, name inspire's MANUAL route once ("paste 3-5 carousels you admire and
I'll run them as teardowns — no key, no credits — that becomes your niche data"). **Re-offer
damping:** the explicit inspire offer fires ONCE per session; after a decline, later builds this
session get one quiet line at most ("niche data still unseeded"), never the full pitch again.
Then judge the
resolved concept against what's winning: hook archetypes, structures, topic clusters, the pains
that pull. When the beat data holds framework skeletons, offer instantiating a proven
role-sequence, not just a vibe. Every input mode gets this — for repurpose/call builds the
enrichment is step 1's job; the check judges the RESULT.
**Copy scorecard (whenever FINAL copy exists — provided, repurposed, or staged draft):** grade the
copy itself line-by-line against the beat data, not just the concept — proof-beat count vs the
niche benchmark, kill-list hits, words/slide, numbered-tease held, hook archetype match. Surface
a scorecard with specific gaps + real-fix options ("0 proof beats vs winner benchmark ≥2; here
are 3 real receipts from your proof assets"). Graded flag, never a silent rewrite.
**Strong** → one line on why, straight to the frame lock. **Needs repackaging** → propose 1-3
pivots/lane shifts that stay close to the original concept, each naming its evidence ("hook
archetype X + pain #2 outperforming, per the inspire run of MM.DD"). Suggest-then-approve: the
coach picks, and the original always stays an option. A weak verdict shapes the pitch — it never
blocks the build.

**2. Lock the frame (confirm with the coach in one message):** platform · objective (save / share /
DM / follow — sets the CTA pattern) · blueprint (A educational / B story-led / C case-study — see
slide-architecture) · the ONE avatar pain this hits. Config `{{CTA_DESTINATION}}: per-build` and
no niche data (or the coach declined the pull) → resolve it HERE: ask which destination THIS
build uses — never carry `per-build` unresolved into step 4 (the gate rejects placeholder CTAs). Blueprint C requires a REAL client story from
config/VoC... if the bank is thin, elicit now (3 quick questions) or pivot to A/B. Never invent.

**3. Map before copy.** Build the slide map (n / role / job-in-≤12-words) per the blueprint +
5-pillar arc. Triple Hook on slides 1-3. **The map shows the loop chain** (per retention-loops.md):
which question each slide opens and closes, primary loop held to the payoff slide, seam question
named at every transition — a seam with nothing open gets fixed at the map stage, not after copy.
Show the map with **one Brain status line** —
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
design direction (executable by a non-designer) + retention device · **ONE CTA, on the final slide
only**, per the chosen pattern wired to `{{CTA_DESTINATION}}` — never a mid-deck soft-save or any
second ask; one action per carousel (a mid-deck ask that differs from the final one splits intent
and the reader does neither — mid-deck slides tease the swipe, never request an action) —
**keyword-CTA asset check (hard rule):** when the CTA is keyword→asset ("Comment X → get Y"), verify
Y actually exists (ask the coach or check the named path) BEFORE writing the CTA; missing → offer
(a) build the asset first or (b) fall back to a single content-appropriate CTA (evergreen
reference — frameworks, checklists, how-tos → the ONE ask becomes save, not an added save) ·
caption (4-part, keyword front-loaded; length default 150-300 words but CONTESTED —
per-account test variable, see caption-strategy.md's 2026 note) · 3-5 narrow hashtags · per-slide alt text · platform delta block when `both` ·
**render handoff:** one line per slide tagging it template-text (clean layout system) or
custom-visual (designer-tier craft) — this is what `carousel-render` routes on.
Entertainment-first doctrine: the carousel earns attention before it teaches; dose the personality
per voice edge. Numbers/results only from `{{PROOF_ASSETS}}`.

**5. Gate + deliver.** Run carousel-quality.md end to end. On GENERATED copy: fix fails silently.
On coach-PROVIDED copy: the scorecard's rule wins — surface each fail as a graded flag with the
fix proposed, rewrite their words only on approval. **Tiebreaker:** the coach explicitly declining
a flagged fix ends the argument — ship their version with the flag NOTED in the delivery line
("shipping with 61-word slide 6, your call") so the decision is on record, never re-litigated. Deliver per
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
