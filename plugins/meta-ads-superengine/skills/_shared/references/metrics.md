# Metrics — decision hierarchy + the KPI log contract

## The hierarchy (hard rule, every ops skill)

**Primary metrics make decisions. Storytelling metrics explain them.**
No skill ever prescribes an action off a storytelling metric alone.

| Tier | Metrics | Role |
|---|---|---|
| **Primary** | spend · results · cost/result (CPL, CPQL, cost/call) · blended ROAS | The ONLY decision inputs |
| **Trusted-detection** | `ads_insights_anomaly_signal` (Meta's own statistical outlier math) | May objectively increment a counter (e.g. bad-day) or flag a bleeder as EVIDENCE — NEVER prescribes an action, never overrides a wait window or the pre-kill check |
| **Backend** (Stage 3–4 north star) | blended MER · nCAC · new-vs-returning client mix | Overrule Meta's dashboard — computed from the CRM, monthly |
| **Storytelling** | CTR · CPM · frequency · hook rate (~30% healthy) · hold rate (~7–8%) · industry/auction benchmarks (`ads_insights_industry_benchmark`, `ads_insights_auction_ranking_benchmarks`) · `ads_insights_advertiser_context` · Opportunity Score | Diagnose WHY a primary moved; never trigger actions |

Fatigue example done right: CPL rising (primary → act) + frequency 2.7 and
CPM climbing (storytelling → the why is fatigue → route to
creative-strategy, not to budget fiddling).

## Fatigue-evidence spec (D-3)

Fatigue is a PRIMARY move (CPL rising) corroborated by storytelling evidence —
never called on storytelling alone. Flag fatigue when **CPL is rising AND any
of**:
- `cpm` climbing ~3–5% daily over a 4–7 day run,
- `frequency` > 2.5,
- one ad taking > 60% of its ad set's `amount_spent` (dominance).

The primary (CPL) is what earns the verdict; these three are the why. Routed
fix is always creative-strategy, never a budget knob (canon-derived,
staged-framework corpus).

## Opportunity Score — stage gate (canon)

`ads_get_opportunity_score` is Meta's own recommendation number.
- **S1–S2:** do NOT fetch or surface it.
- **S3–S4:** MAY fetch, always labeled *"Meta's opinion — it recommends
  Meta's own features"* (storytelling tier, context only).
- **Never a decision input at any stage.** Primary metrics + the CRM decide.

## Judgment windows (stage-linked)

- **7-day minimum** on any verdict; day-to-day Meta is noise.
- Low volume → stretch the window (a month at ~6 conversions/week).
- **Volume floor (learning phase, directional):** Meta's learning phase wants
  roughly 50 optimization events per ad set per week to exit reliably. At S1
  budgets, do the math on the chosen event ... an expected weekly count far
  under that floor means optimize on the higher-volume upstream event (raw
  lead) first, qualify downstream, and revisit as spend grows.
- Dual clock (canon): obvious deaths at 48–72h (~1× target CPL spent, zero
  leading indicators) · winner calls at 7d+.
- Post-raise wobble: judge the 7-day average AFTER a raise, never raise-day.
- ~90% confidence / 7–10 days / ~100 conversions is coach-scale
  significance. When in doubt, a significance calculator — not vibes.

## Targets come from breakeven-math only

Every judgment compares against `targets.*` in state (stamped
`targets_version`). A skill noticing actuals diverging from the assumptions
behind those targets (close rate, show rate) routes to breakeven-math re-run
(edge F3) — it never quietly adjusts a target itself.

## The KPI log — `state/<brand>/kpi-log.json`

Owned by `meta-ads-kpi-tracker` (the data layer — daily-brief and
performance-review invoke it; coaches touch it via "show my trends").
Append-only.

```jsonc
{
  "schema_version": "1.0",
  "entries": [
    {
      "date": "YYYY-MM-DD",
      "window_days": 7,             // the window this row summarizes
      "spend": 0,
      "results": 0,                 // count of the optimized event
      "cost_per_result": 0,
      "conversions_manual": null,   // OPTIONAL number|null ... coach's own tally of conversions for the window (sales, signups, closes); first-class for no-CRM / no-call funnels; perf-review's CRM-reality read accepts it
      "cpl": null, "cpql": null,    // when distinguishable
      "cpm": null, "ctr": null, "frequency": null,   // storytelling row — recorded, never decisive
      "source": "manual-paste" | "csv-import" | "mcp" | "cli",   // "mcp" = hosted connector (Path A); "cli" = official Meta Ads CLI (Path B)
      "targets_version": 1,         // which targets this row was judged against
      "verdict": "on-target" | "over" | "under" | "insufficient-data",
      "note": null
    }
  ]
}
```

Rules:
- One entry per pull ... a daily-brief pull appends a `window_days: 1` row; a
  review pull appends one row for its whole window; never two rows for the same
  date + window. `window_days` says what each row covers.
- `targets_version` stamps make old rows honest after a re-math (F3): trends
  compare within a version, flag across versions.
- Trend rendering: verdict-over-time vs exit criteria (`stage-check` reads
  this for stage-advance evidence; `scale-decision` refuses to act without
  it — "kpi-log evidence, not vibes").
- **Streak counting (window-aware):** a calendar day counts as on-target when
  an on-target row covers it ... either its own `window_days: 1` row, or a
  larger on-target window row (an on-target `window_days: 7` row = 7 covered
  on-target days ending at its date).
  - An over/under row breaks the streak across every day it covers.
  - Uncovered days (no row) break a consecutive-days requirement; they don't
    count either way for rolling averages.
  - Consumers of "7+ consecutive days" / "streak" language count by THIS rule
    and cite the covering rows.
- Manual-paste and CSV import are **first-class** sources — MCP is an
  enhancement, never a prerequisite (family law).
