---
name: carousel-superengine:carousel-inspire
description: Niche-wide carousel intelligence. Studies what's winning across many accounts and hashtags in the coach's niche — winning hook archetypes, structures, topics, visual systems — and returns an evidence-cited pattern report plus ranked build candidates adapted to the coach's voice. Trigger phrases include "what's working in my niche", "competitor analysis", "who should I study", "carousel inspiration", "what should I make next", "find winning carousels".
---

# Task: inspire

Niche in → evidence-cited pattern report + ranked build candidates out. Synthesis of MANY posts —
for one specific post, that's `carousel-teardown`. Analysis-driven, never vibes: every claim carries
`@handle · metric · post URL`.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md if present (the persisted filled config — read FIRST) → else ${CLAUDE_PLUGIN_ROOT}/references/business-config.md (shipped template only; placeholders → stop, route to `carousel-setup`)
${CLAUDE_PLUGIN_ROOT}/references/teardown-method.md (SocialCrawl calls, slide-order rule, honesty rules)
${CLAUDE_PLUGIN_ROOT}/references/beat-schema.md (the per-slide record contract for step 3.5)

Requires the coach's own SocialCrawl key (`{{SOCIALCRAWL_KEY_STATUS}}: saved`) — missing → offer the
2-minute setup (references/socialcrawl-key-setup.md) or the manual route (coach pastes links they
admire → batch of single teardowns instead).

## Credit discipline (non-negotiable)

Costs stated in plain language BEFORE spending, at every rung: ~1cr single pull → free-flow after a
one-line note · ~5cr batch → say the cost first · 10cr+ → explicit yes required · large sweeps →
live balance check (`GET /v1/credits/balance`, free) + named total + after-balance + explicit yes,
never batched silently. A coach who says "just go" still gets the total named once.

## Flow (checkpointed — each ✋ is a hard pause)

**1. Frame the hunt.** From config: niche, positioning, avatar. Ask only what's missing. Two
discovery lanes, run both when budget allows:
- **Accounts lane:** competitor/adjacent accounts — coach's seed handles (seeds expand the pool,
  never cap it) + niche search. Target ~15-25 accounts tiered by size (relative to the coach);
  fewer is fine with the coach's explicit ok.
- **Hashtag lane (carousel-native):** 3-5 niche hashtags → `/search/hashtag?type=top` → keep posts
  where `media_urls` length > 1 (that's a carousel) → rank by engagement.
✋ **Checkpoint 1:** confirm niche framing + seed accounts/hashtags before any paid pull.

**2. Source the pool.** Run the lanes → candidate carousels ranked by real engagement (views /
likes / comments — ONLY metrics the API returns; never fabricate saves/shares, they aren't public).
✋ **Checkpoint 2:** show the ranked candidate set (handle · followers · post engagement · one-line
why) + the exact credit cost to go deep on the top N. Coach trims or approves.

**3. Deep-read the approved set.** Full pulls per teardown-method.md (`download_media=true`,
slide-order label rule). Read every slide of every approved carousel.

**3.5. Extract the beat dataset (the granularity you just paid for — never skip).** One structured
record PER SLIDE per beat-schema.md: role, copy verbatim + abstracted formula, framework role,
visual, engagement device, loop tier, seam question. Read both tiers — winners AND the bottom of
the ranked pool — the win/loss contrast is where the signal lives. Parallelize readers on large
sets. Persist as `${CLAUDE_PLUGIN_DATA}/analysis/beats-<niche-slug>-<MM.DD.YY>.json`.

**4. Synthesize FROM the beat dataset (not from raw slides):**
- **hook library** — every slide-1 verbatim + formula + device, win/loss-tagged (the shapes feed
  archetype selection; verbatims stay in the coach's data)
- **framework skeletons** — winning role-sequences as reusable blueprints `carousel-create` can
  instantiate ("hook → context → value×4 → proof → payoff → cta")
- **positional beat-map** — what each slide position does in winners vs losers
- **kill-list** — losing beat-patterns to gate against (buried reader stake, unresolved close,
  context overload)
- plus the prose report: structure patterns, topic clusters + gaps, visual systems (feeds Path A
  steal-style), cadence signal where visible
Every line evidence-stamped `@handle · metric · URL`. Inferences from partial data tagged as such;
positional claims from `order_verified: false` decks down-weighted and said so.
Save the full report to `${CLAUDE_PLUGIN_DATA}/analysis/inspire-<niche-slug>-<MM.DD.YY>.md` (create
the folder if missing) — `carousel-create` consults report + beat data at its winning check on
every future build.
✋ **Checkpoint 3:** deliver the report; confirm which direction to build before generating anything.

**5. Rank the build candidates.** 3-5 concrete carousel concepts adapted to the COACH — their
avatar pains, their pillars, their voice (never a clone of anyone's post): "Pattern: <what wins> ·
Evidence: <@handle · metric> · Your version: <one-line concept in their positioning>."

## Ends with (offer, never block)
- **Deep-dive the standout** → `carousel-teardown` — "tear down #1" (full single-post autopsy +
  downloaded slides become the render style reference)
- **Build from a pattern** → `carousel-create` — "build from pattern 2" (the concept carries the
  evidence; the content is 100% the coach's)
- Re-run for another niche/angle → `carousel-inspire`
- (When `{{SCHEDULE_STATUS}}` is unset, once per session) "Want a monthly refresh of this report on
  autopilot? Drafted and waiting, you approve everything." → scheduled-builds flow

## Rules
- Public accounts/posts only; research + inspiration use — pulled media/copy is analysis input, never content to repost.
- Structure and style get borrowed; wording, examples, and images never.
- Real metrics only. No reach predictions, no virality promises — craft, not prophecy.
- Batch pulls are throttled and always pre-approved; a failed pull degrades to the manual route, never dead-ends.
