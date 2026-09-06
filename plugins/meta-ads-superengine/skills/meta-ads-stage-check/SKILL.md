---
name: meta-ads-superengine:meta-ads-stage-check
description: Diagnose which of the four spend stages the coach is in (Test $10-49 / Validate $50-99 / Ramp $100-299 / Scale $300+), show the posture for that stage, and audit exit criteria when they think they're ready to move up. Trigger phrases include "what stage am I in", "stage check", "am I ready to scale up", "meta ads stage".
---

# meta-ads-stage-check — the spend-stage diagnosis

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #6.
The 4-stage spine (framework Part 3) as an interactive diagnosis. Stages move
on **exit criteria, never impatience**.

## Load
- shared refs (as breakeven-math) + `metrics.md`
- Active brand state → `setup.spend_level`, `stage`, `kpi_log`, `targets`

## Prereq (E0)
`setup.spend_level`. Missing → setup.

## Steps

**1. Place the stage** by current/planned daily spend + history:
| Stage | Band/day | Goal |
|---|---|---|
| 1 TEST | $10–49 | find 1–2 resonant concepts; buy data not customers |
| 2 VALIDATE | $50–99 | prove the winner holds at real spend; harden the signal loop |
| 3 RAMP | $100–299 | grow spend without breaking what works; find the ceiling |
| 4 SCALE | $300+ | systematic growth, backend (MER/nCAC) as north star |

**Boundary tiebreak:** at a band boundary the GOAL decides ... still hunting a
winner = the lower stage; a proven winner being hardened or grown = the upper.

**2. Show the posture card** for that stage (framework Part 3):
structure · creative count (S1 3–5 distinct · S2 8–12 · S3 15–20 · S4 20+) ·
testing mode · automation posture · the stage's named failure modes. Render
per teach level.

**3. Exit-criteria audit** (only if the coach asks "am I ready to move up"):
- S1→S2: one+ concept holds CPL ≤ target across 7+ consecutive days (metrics.md 7-day minimum).
- S2→S3: CPL/CPQL at-or-under target 7–14 consecutive days AND CRM-confirmed
  qualified-lead→call→close rates (not Meta-reported).
- S3→S4: stable at target on a 14-day rolling average with a creative
  pipeline ready.
Consecutive-days are counted window-aware (metrics.md); cite the covering rows.
Demand **kpi-log evidence, not vibes** (read `kpi_log`); no evidence → the
move is "keep gathering data", route to daily-brief/performance-review.

**4. Brain (1 search + up to 2 reads, via `revxl-vault-search`).** Invoke
`workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=meta-ads-superengine spoke=meta-ads-strategy question: <the
diagnosed stage> posture ... angles: the diagnosed stage; stage 1 test broad
CBO kill discipline`.
Self-evidencing line; degrade F9.

**5. Write** `stage`.

## Terminal paths — inline blocks (routing.md grammar)

**Stage diagnosed (E12):** preamble names the stage + one-line posture, then:

**Next moves**
1. *If `targets` are set:* build the structure that fits this stage. Say: "plan my campaign"  ← start here
2. *If `targets` aren't set yet:* run your numbers first — the plan needs them. Say: "run my numbers"
3. *If S3/S4 and asking about moving up:* run the evidence-based scale audit. Say: "should I scale"
4. *If the exit audit failed:* the diagnosed fix — fresh creative (Say: "creative strategy") or signal hardening (Say: "set up tracking")

**Next moves — advance requested, evidence missing**
Stages move on evidence, never impatience — `stage` stays put.
1. *If `targets` are set:* start logging the numbers that prove it. Say: "show my trends"
2. *If `targets` aren't set yet:* run your numbers first — trends need a target to track against. Say: "run my numbers"
3. The daily glance builds the record automatically. Say: "daily brief"

## Teach mode
In `new`: plain-English-first — each stage's posture explained as behavior
("at your budget, the whole job is finding 1–2 ads that work — buying data,
not customers") before band jargon; "exit criteria" glossed (one-liner tier)
and worked against the coach's own targets. In `learning`: gloss exit
criteria / posture terms first use. In `pro`: stage + posture card + audit
verdict, terse.

## Guardrails
- No banned structures in any posture card (no LAL tiers, interest stacks,
  70/30, AEM — canon).
- DIRECTIONAL numbers (creative counts, raise %) phrased as direction, not law.
