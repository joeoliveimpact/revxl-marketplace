---
name: meta-ads-superengine:meta-ads-creative-test
description: Runs the creative testing discipline on live ads — dual-clock verdicts (fast-kill vs winner calls), dimensional swings as separate ads, micro-variants only through Meta's native Creative-Testing Tool, the Stage-3 pack protocol, and the mandatory pre-kill check that protects feeder ads. Trigger phrases include "test my creatives", "which ad is winning", "kill or keep", "creative test".
---

# meta-ads-creative-test — the testing discipline

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #18.

## Load
- shared refs + `metrics.md` (dual clock, storytelling-vs-primary)
- Active brand state → `creatives` (live rows + `live_at` clocks),
  `kpi_log`, `stage`, `targets`

## Prereq (E0)
`creatives[].live_at` — something is actually running. Missing →
launch-runbook ("verdicts need live ads; launch first").

## Steps

**1. Clock every live creative** from its `live_at`:
- **48–72h fast-kill window:** ~1× target CPL spent with zero spend or no
  cheap leading indicators (hook rate, outbound CTR — storytelling metrics
  used HERE as leading indicators, still never as final judges) → candidate
  kill.
- **7–14d winner window:** stable at-or-under target CPL/CPQL → winner
  call. In between → "too early, judge on <date>".

**2. MANDATORY pre-kill check (the last-click exception).** Before ANY kill
recommendation on a high-spend low-ROAS ad: is the overall campaign KPI
holding? Delivery sequences ads — the ugly top-funnel educator may be
feeding the pretty closer. Kill it and the closer collapses. Check assist
behavior; when in doubt, hold.

**3. Design the next test:**
- **Dimensional swings only** as separate ads (length / format / actor /
  concept — a 15s UGC vs a 90s VSL vs a plain static). Never five
  near-identical variants.
- **Micro-variants (hooks, copy) exclusively via Meta's native
  Creative-Testing Tool** (ad-level "Set Up Test", ≤5 variants, comparison
  metric = cost per lead NEVER engagement; Highest-Volume bidding only;
  tests new duplicates only).
- Priority ladder: **replicate → iterate → net-new.**
- **Stage 3 pack protocol** when new ads starve under CBO: new dated ad set
  (`pack-YYYYMMDD`), min-spend = 1× target CPL, exactly 7 days, then remove
  the floor. **20% guardrail:** all testing minimums combined ≤20% of daily
  budget.

**4. Never edit a running winner** — iterate via dimensional variations
(new B-roll, format repackage, actor swap); every significant edit resets
learning.

**5. Brain (1 search + up to 2 reads, via `revxl-vault-search`).** Invoke
`workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=meta-ads-superengine spoke=meta-ads-strategy question: <the
creative-test diagnosis> ... angles: creative fatigue frequency CPM; dimensional
swing vs native CT-Tool test`.
Self-evidencing line; degrade F9.

**6. Write** `creatives[].status` (killed/winner + dates).

## Terminal paths — inline blocks (routing.md grammar)

**Verdicts delivered (E18):** preamble = the verdict table (keep / kill /
too-early-until-date, pre-kill check evidenced), then:

**Next moves**
1. Iterate the winner — dimensional variations, a new lottery ticket from a proven idea. Say: "creative strategy"  ← start here
2. Replace the kills — produce the next concepts in the queue. Say: "<the format's trigger per the queue>"
3. *If micro-variants are the right move:* set up the native test — I'll walk the CT-Tool clicks. (Part of this skill — say "test my creatives" with the variant list.)

**Next moves — total failure (F4: everything died at the kill window)**
First batch dead is DATA, not defeat:
1. New concept batch from untouched matrix cells. Say: "creative strategy"
2. *If this is the SECOND total failure:* the problem is upstream — re-check the math and the funnel, not the ads. Say: "run my numbers" then "qualify my leads"

## Teach mode
In `new`: plain-English-first — the dual clock explained as behavior
("obvious deaths get 3 days; winner calls take a week — day-to-day numbers
are noise"); "dimensional swing" deep-glossed via the lottery-ticket
analogy; the pre-kill check gets its own "what this means for you" ("some
ads don't close — they hand customers to the one that does; killing them
quietly breaks the winner"). In `learning`: gloss CT-Tool/dual-clock first
use. In `pro`: verdict table + next test, terse.

## Guardrails
- Coach-scale statistics (canon): ~90% confidence, 7–10 days or ~100
  conversions — never demand 95%-confidence sample sizes.
- Verdicts cite kpi-log rows (evidence, not vibes).
- The 20% testing-budget guardrail is checked on every pack.
