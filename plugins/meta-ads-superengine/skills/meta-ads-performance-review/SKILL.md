---
name: meta-ads-superengine:meta-ads-performance-review
description: The weekly diagnosis — pulls the numbers (paste, CSV, or live connection), judges them against the stage framework and the CRM's reality, and ROUTES to the fix rather than just reporting. Has week-one, monthly backend-audit, and import modes. Trigger phrases include "review my ads", "weekly review", "why are my ads not working", "ad performance review".
---

# meta-ads-performance-review — diagnose, then route

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #25.
The rule that makes this skill useful: **one primary diagnosis + one routed
fix** — never a metrics dump.

## Load
- shared refs + `metrics.md` + `naming.md` (the CSV parse grammar)
- Active brand state → `launched_at`, `stage`, `targets`, `kpi_log`,
  `creatives`, `funnel`, `last_review`
- Brand check (rule 6): a brand named in the coach's message that isn't `active_brand` → stop, offer "switch brand" first ... never another brand's numbers silently.
- Numbers: MCP read if connected; **manual-paste / CSV export first-class**
- CRM reality: booked calls + closes this period where a call funnel + CRM
  exist (ask ... Meta can't see it); no CRM or no calls → the coach's own tally
  of conversions this window (sales / signups / closes) is first-class,
  recorded as `conversions_manual` on the kpi row (metrics.md)

## Prereq (E0)
`launched_at` OR import mode (F5 onramp — diagnosing a running account from
exports). Neither present and nothing importable → E0: "a review needs live
or imported numbers" → Say: "what's next" (the compass points at the real
next step — usually launch or setup).

## Modes
- **Week-1** (auto when <14d since `launched_at`): gentler bars — learning
  is normal, "learning limited" is a state you profit in; verdicts mostly
  "hold + keep logging."
- **Standard weekly:** the full diagnosis below.
- **Monthly backend audit:** blended MER + nCAC + **new-vs-returning client
  mix** — the cannibalization catch (great platform ROAS while new-client
  count quietly drops). CRM numbers, not Meta's.
- **Import** (F5): parse exports per `naming.md`; unparseable rows reported
  as unattributable, never guessed; backfills only its OWN keys
  (`last_review`, `launched_at`) WITHOUT touching live — `stage` is written by
  stage-check (the F5 route runs through it), kpi rows by kpi-tracker
  (ownership respected, never bypassed).
  **Backfills `launched_at`** (+`launched_at_source: "import"`) from the
  OLDEST currently-running campaign's start date found in the evidence —
  sources ranked: live MCP read (`ads_get_ad_entities`, campaign level,
  attributes incl. `start_time` and `effective_status` — when connected) > CSV
  export > manual paste with dates. **Only currently-delivering campaigns
  qualify (state-schema rule 5):** a live read must confirm `effective_status
  == "ACTIVE"` before a campaign's `start_time` counts; a CSV or paste source
  must establish delivering status from its status column, else that row cannot
  seed `launched_at`. Discard invalid sentinel dates (Unix-epoch 1969/1970, or any
  pre-2004 value) — they are API nulls, not launches. No per-campaign start
  date derivable → do NOT backfill: say so
  and continue import-only (weekly reviews still work). At `new`/`learning`:
  "this stamps when your ads actually started, so the daily brief has a clock."

## Steps (standard mode)

**1. Pull + parse.** Names parsed by the grammar → per-concept rows joined
to `creatives[]`. Log via kpi-tracker. **Live pull (when connected):** if the
marker shows `connections.meta_mcp` connected, pull per-ad entities via
`ads_get_ad_entities` (`date_preset: last_7d` / `last_14d`) using catalog field
names — alongside, never instead of, manual paste / CSV / import (all
first-class).

**2. Judge vs the stage framework** (wait windows enforced — no verdict
inside a judgment window; say when the verdict date is).

**3. Diagnose — ONE primary finding**, storytelling metrics as the why:
| Finding | Evidence pattern | Routed fix |
|---|---|---|
| Creative fatigue | CPL up + frequency >2.5 / CPM climbing days | creative-strategy (E16) |
| Weak signal | results low + event volume thin / dedup suspect | signal-setup (E16) |
| **Junk leads** | Meta looks fine, CRM says leads don't book/qualify | funnel-qualify (F2) |
| Actuals ≠ assumptions | close/show rates diverge from setup's | breakeven-math re-run (F3, targets cascade) |
| Exit criteria met | kpi-log streak at-or-under target (window-aware, metrics.md) | scale-decision (E16) |
| Nothing wrong | on-target | hold — the honest verdict |

Fatigue evidence follows the metrics.md **fatigue-evidence spec (D-3)** — CPL
rising is the primary that earns the call; `ads_insights_performance_trend`
(when connected) computes the CPM micro-trend that corroborates it
(storytelling, never the verdict on its own). When connected,
`ads_insights_anomaly_signal` runs as a pre-diagnosis pass (TRUSTED-DETECTION,
metrics.md) — its outlier / bleeder flags feed the table above as EVIDENCE
only; it never triggers a kill directly, and the mandatory pre-kill check
(step 5) still runs.

**Market context (when connected, storytelling only):**
`ads_insights_industry_benchmark` + `ads_insights_auction_ranking_benchmarks` +
`ads_insights_advertiser_context` answer "is it me or the market?" — a context
line in the monthly backend audit and beside a fatigue / weak-signal call.
Never in the verdict line; the diagnosis stays primary-metric + CRM.

**4. Brain (1 search).** Recipe = ops-verdict row: query the diagnosis + stage
posture, variants keyed to the primary finding ("creative fatigue CPL rising
frequency"). Self-evidencing line; degrade F9.

**5. Pre-kill check (mandatory)** before any kill recommendation — the
last-click exception (a high-spend "low-ROAS" ad may be feeding the
closer; check campaign KPI + assists first).

**6. Write** `last_review` {date, verdict, targets_version_used}. Write
`targets_version_used` ONLY when `targets` exist; with no `targets`, write
`last_review` without it and say plainly the review ran against no targets
(breakeven-math is the fix ... Say: "run my numbers").

## Terminal paths — inline blocks (routing.md grammar)

**Diagnosis delivered (E16):** preamble = the one-line verdict + evidence,
then (render ONLY the diagnosed row's route as #1; **F5 import-mode guard:**
if the routed fix's own prereq isn't in state yet — common after an import
with no `targets`/`funnel` — its E0 sends the coach to that foundation first,
so name that foundation as #1 instead):

**Next moves**
1. *Fatigue:* fresh distinct concepts — the fix is creative, not budget. Say: "creative strategy"
   *Weak signal:* verify the event + dedup. Say: "set up tracking"
   *Junk leads:* tighten the qualification gate. Say: "qualify my leads"
   *Actuals diverged:* re-run the math — every target downstream shifts. Say: "run my numbers"
   *Exit criteria met:* the evidence-based scale audit. Say: "should I scale"
2. Log + trends behind this verdict. Say: "show my trends"
3. *Hold verdict:* nothing to fix — next review in 7 days. Say: "review my ads"

**Next moves — monthly backend audit findings**
1. *Cannibalization found:* re-add purchaser/client exclusions + re-audit next month — I'll walk the setting.
2. *Backend healthy:* carry on. Say: "daily brief"

**Next moves — import complete, nothing live (`imported-no-live`)**
The import parsed, but zero campaigns are currently delivering (all paused, or
every row unattributable). Plainly: your history is filed (in
`state/<brand>/history/`), but no `launched_at` was stamped ... there is no
live campaign to clock. `last_review` records verdict `"imported-no-live"`, so
the daily brief knows the import already ran and will not re-offer it. The road
now is a relaunch:
1. *If no `targets` yet:* run the numbers first ... the foundation a relaunch stands on. Say: "run my numbers"
   *If `targets` exist:* plan the relaunch from what the import just taught you. Say: "plan my campaign"
2. Not sure where you stand? Say: "what's next"

## Teach mode
In `new`: "your CRM is the truth, Meta is the claim" leads; MER/nCAC
deep-glossed at monthly mode with the coach's real revenue; each diagnosis
explained as a story before its term ("people see the ad a lot now and
click less — it's wearing out; that's called fatigue"). In `learning`:
gloss MER/nCAC first use. In `pro`: verdict + route, terse. Across levels, one
honest caveat: Claude's math is trusted for anomaly and bleeder DETECTION, not
for holistic strategy — verdicts stay numbers-based plus the coach's CRM
reality, never Meta's opinion.

## Guardrails
- One primary diagnosis; secondary findings get one line each, max.
- No verdict inside a wait window; no kill without the pre-kill check.
- Junk-leads are diagnosed against CRM reality ... the coach's own conversion
  tally (`conversions_manual`) counts as that reality (an honest self-count
  beats blind). Only when there's NO tally and no CRM is the diagnosis blind
  there ... say so, don't guess.
