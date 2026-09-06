---
name: meta-ads-superengine:meta-ads-scale-decision
description: The evidence-based scale audit — checks the stage exit criteria against the KPI log (never vibes), prescribes raise-in-place increments with the wobble warning, enforces the testing-budget guardrail and the hard deck, and knows when the answer is "not yet". Trigger phrases include "should I scale", "raise my budget", "ready to spend more", "scale my ads".
---

# meta-ads-scale-decision — go / hold, with receipts

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #26.
Scaling on a 3-day hot streak is how winners die. This skill demands the
log.

## Load
- shared refs + `metrics.md`
- Active brand state → `kpi_log` (+ the log file), `stage`, `targets`,
  `creatives` (pipeline check), `last_review`
- Brand check (rule 6): a brand named in the coach's message that isn't `active_brand` → stop, offer "switch brand" first ... never another brand's numbers silently.

## Prereq — THE EVIDENCE GATE (E0)
`kpi_log` has entries. Missing → refuse + route: *"A raise is a bet — the
log is the receipts. Start logging first."* → Say: "show my trends".

## Steps

**1. Exit-criteria audit** against the log (within current
`targets_version`): the stage's bar (S1→2: CPL ≤ target 7+ consecutive days
(metrics.md 7-day minimum) · S2→3: 7–14 days + CRM-confirmed rates · S3→4:
14-day rolling stability). Cite the specific rows. Consecutive-days evidence is
counted by the window-aware rule (metrics.md): a mix of daily and window rows is
valid ... cite the covering rows. Actuals diverging from
setup assumptions → **F3 first: re-run the math before any raise.**
**Live cross-check (when connected):** the cited kpi-log rows may be
sanity-checked against a live `ads_get_ad_entities` pull (`date_preset:
last_14d` / `last_30d`, catalog field names) — a discrepancy is FLAGGED for the
coach, but the append-only log stays authoritative and the no-vibes evidence
gate is unchanged — whether the log was fed by manual paste, CSV, or MCP, live
data corroborates it, never replaces it.

**2. Brain (1 search + up to 2 reads, via `revxl-vault-search`).** Invoke
`workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=meta-ads-superengine spoke=meta-ads-strategy question:
stage-exit and raise posture ... angles: the diagnosed stage; stage 3 ramp
ceiling raise-in-place`. Self-evidencing line; degrade F9.

**3. Verdict:**
- **GO:** raise-in-place — **≤20%, same campaign, then hands off 48–72h.**
  Never duplicate-to-scale. Expect the 1–2 day wobble; judge the 7-day
  average after, never raise-day numbers. Hands-off alternative: automated
  rules at ±3%/day with a buffer zone. A 200%+ jump = full learning reset.
  When connected, `ads_insights_performance_trend` renders the S3 14-day
  rolling stability and the post-raise 7-day average (corroboration; the log
  remains the receipts).
- **HOLD:** the missing evidence named ("you need N more on-target days"),
  next check date set.
- **CEILING FOUND** (S3): stepped raises decaying CPL toward breakeven →
  the ceiling is real; the unlock is better creative, not budget mechanics.
  `ads_insights_auction_ranking_benchmarks` (when connected) colors the ceiling
  diagnosis — storytelling context on whether the auction is being lost on
  quality / engagement rank; the "unlock is creative, not budget" verdict is
  unchanged.

**4. Guardrail checks (every GO):** testing minimums ≤20% of daily budget ·
creative pipeline ready (winners fatigue in ~2–3 weeks at higher spend — a
raise without a queue is a fatigue appointment) · never below
`targets.hard_deck` on any subsequent cut · S4: cost caps as circuit
breaker + the backend (MER/nCAC) becomes the north star.

**5. Write** `stage` (on a stage advance), open_loop with the post-raise
check date. A HOLD writes its open_loop too (next-check date) — the compass
must resurface the re-check, not just GO outcomes.

## Terminal paths — inline blocks (routing.md grammar)

**GO (E17):** preamble = the raise instruction (exact number, exact date to
judge), then:

**Next moves**
1. Make the raise in Ads Manager — same campaign, +N%, then hands off. I'll judge it on <date>. Say: "daily brief" (tomorrow — glance only)
2. *If the creative queue is thin:* stock it before fatigue arrives. Say: "creative strategy"
3. Log the raise as a marker in the trend line. Say: "show my trends"

**Next moves — HOLD (evidence missing)**
1. Keep the cadence — the log builds the case. Say: "daily brief"
2. The weekly diagnosis moves the needle more than budget does right now. Say: "review my ads"

**Next moves — ceiling found**
1. The unlock is creative, not budget: new distinct concepts raise the ceiling. Say: "creative strategy"  ← start here
2. Hold spend at the ceiling; re-test after the next creative batch. Say: "should I scale" (after 7+ days)

## Teach mode
In `new`: raise-in-place deep-glossed (oven analogy) + the wobble warning
("what this means for you: day 1–2 after a raise looks worse — that's
normal, we judge day 7"); the evidence gate explained without shame ("not
'no' — 'not yet, and here's exactly what yes looks like'"). In `learning`:
gloss wobble/ceiling first use. In `pro`: verdict + instruction + check
date. **The never-duplicate and hard-deck rules render at FULL strength at
every level.**

## Guardrails
- No raise without log evidence; no raise >20%; never duplicate-to-scale;
  never below the hard deck (canon + framework).
- DIRECTIONAL numbers stay directional in output.
- A GO always ships with its judgment date — a raise without a review date
  is a loose end.
