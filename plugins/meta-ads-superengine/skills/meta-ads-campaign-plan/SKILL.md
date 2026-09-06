---
name: meta-ads-superengine:meta-ads-campaign-plan
description: Produces the stage-appropriate campaign structure — consolidated CBO, broad targeting, automated bidding, the naming convention, and budget from the coach's real targets. Stage 1 is one campaign, one ad set, 3-5 distinct concepts. Includes the high-ticket omnipresent branch for $10k+ offers. Trigger phrases include "plan my campaign", "campaign structure", "how should I set up my campaign".
---

# meta-ads-campaign-plan — the structure artifact

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #12.
The launch-runbook executes this artifact click-by-click, so it must be
concrete: named objects, budgets, settings.

## Load
- shared refs + `naming.md` + `vault-api.md`
- Active brand state → `targets`, `stage`, `creatives`, `setup.offer/price`

## Prereq (E0)
`targets` + `stage`. Missing → breakeven-math / stage-check.

## Steps

**1. Build the stage-appropriate structure** (framework Part 3, canon veto):
- **Consolidated CBO** — one campaign. Stage 1 = ONE campaign, ONE ad set,
  3–5 distinct concepts. No separate testing/retargeting campaigns below
  ~$300/day.
- **Broad targeting** — location + age floor + language only. No interest
  stacks, no LAL ladders, no audience-size bands (all obsolete — canon: Targeting + structure).
- **Automated bidding** (highest volume). Objective = Leads/Sales only.
- **Enhancements rule** (framework 2.3): reject anything that modifies the
  creative itself; accept things around it. Multi-advertiser ads OFF for
  high-ticket.
- **Budget** from `targets` (daily, within the stage band). **Volume-floor
  sanity:** sanity-check the daily budget against the optimization event's
  expected weekly volume (metrics.md learning-phase floor) ... under-floor at
  S1 means optimize on the upstream raw-lead event first (see signal-setup).
- **Names** from `naming.md` (campaign/ad set/ad grammar — the parseable
  convention performance-review reads later).

**2. High-ticket branch ($10k+ offers).** Add the omnipresent warm-audience
exception (multiple ad sets / saturation) — **alongside, never instead of**,
the conversion campaign (framework 5.3). Only for $10k+.

**3. Brain (1 search + up to 2 reads, via `revxl-vault-search`).** Campaign structure rides on
the stage posture. Invoke `workspace-superengine:revxl-vault-search` with the
Skill tool, args `depth=med plugin=meta-ads-superengine spoke=meta-ads-strategy
question: campaign structure stage <N> consolidated CBO ... angles: the stage
posture; the offer tier`.
Self-evidencing line; degrade F9.

**4. Write** the plan artifact (naming convention) → `campaign_plan` (path).
Include the **paused-first** instruction (everything builds paused; launch is
a separate deliberate step). **Per concept row, record the asset source** so
the launch-runbook knows how to place each ad: `produced` (artifact path) /
`upload` (coach-supplied file) / `post-id` (existing post — `Post ID: <id>`,
preserves social proof).

## Terminal paths — inline blocks (routing.md grammar)

**Plan written, gate MET (E13):** preamble names the artifact + "everything
in it builds paused", then:

**Next moves**
1. Launch it — I'll walk you through Ads Manager click by click, everything paused until YOU publish. Say: "launch my campaign"  ← start here
2. *If concept slots in the plan are unfilled:* produce the missing creatives first. Say: "creative strategy"
3. Review the plan against the road. Say: "what's next"

**Next moves — plan written, launch gate BLOCKED**
Launch is blocked until every gate item is green — stated plainly, the
missing item named:
1. *If compliance is missing/stale for this offer:* run the live policy gate. Say: "compliance check"
2. *If no qualified event is set:* build the qualified-lead layer. Say: "qualify my leads"

## Teach mode
In `new`: plain-English-first — CBO via the water-tank analogy and broad via
the sign analogy (glossary deep tier) BEFORE the terms; every setting
in the plan carries a one-line "why this is on/off"; the paused-first rule
gets its "what this means for you". In `learning`: gloss CBO/broad/objective
first use. In `pro`: the structure artifact, terse.

## Guardrails
- Banned-content grep must stay clean: no LAL tiers, interest stacks, 70/30,
  size bands (canon).
- The plan names concepts by their state `creatives[].id` (naming join key)
  so the registry and the live ads line up.
