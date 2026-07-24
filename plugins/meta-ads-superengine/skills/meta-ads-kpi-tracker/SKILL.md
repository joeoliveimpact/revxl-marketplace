---
name: meta-ads-superengine:meta-ads-kpi-tracker
description: The data layer — appends each review pull to the per-brand KPI log and renders trends against targets and stage exit criteria. Mostly invoked by the daily brief and weekly review; callable directly to see trends. Trigger phrases include "show my trends", "kpi log", "how am I trending".
---

# meta-ads-kpi-tracker — the memory

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #24.
Deliberately thin: a log writer + trend renderer. daily-brief and
performance-review invoke it; the coach's own door is "show my trends".

## Load
- shared refs + `metrics.md` (the kpi-log.json schema lives there)
- Active brand state → `targets`, `stage`, `kpi_log` pointer
- Brand check (rule 6): a brand named in the coach's message that isn't `active_brand` → stop, offer "switch brand" first ... never another brand's numbers silently.
- `state/<brand>/kpi-log.json` (create from schema on first entry)

## Prereq (E0)
`targets`. Missing → breakeven-math ("trends need a target to trend
against").

## Steps

**1. Append (when invoked with a pull):** one entry per pull (a daily-brief
pull = a `window_days: 1` row; a review pull = one row for its whole window) —
window, spend, results, cost/result, CPL/CPQL, the storytelling row,
source (manual-paste / csv-import / mcp / cli), `targets_version` stamp, verdict
(on-target / over / under / insufficient-data). Append-only, never edit
history.

**Live pull (when connected):** if the marker shows `connections.meta_mcp`
connected, pull the row from `ads_get_ad_entities` with `date_preset` matching
the entry's `window_days` (`last_7d` / `last_14d` / `last_30d`), using catalog
field names (`amount_spent`, `results`, `cost_per_result` / `cost_per_lead`,
and the storytelling fields `cpm`, `ctr` / `website_ctr`, `frequency`); stamp
`source: "mcp"`. Manual paste and CSV import are equally first-class — the log
doesn't care which door the row came through. Before a live pull, any metric
name a caller introduced that isn't in the catalog gets checked against
`ads_get_field_context` (the metric-name firewall) — on a mismatch, report the
resolved/unresolved name and stop; never guess a field. Hook and hold rates
are derived, not stored: hook = `3_second_video_plays` ÷ `impressions`; hold =
`video_thruplay_watched_actions` ÷ `3_second_video_plays` (catalog-verified —
no `hook_rate` / `hold_rate` field exists; `3_second_video_plays` is
campaign/adset level only).

**2. Render trends (always):** verdict-over-time vs targets and the
stage's exit criteria — within a `targets_version` only; across versions,
flag the boundary ("targets changed here — comparing across it lies").
State plainly: how many consecutive on-target days (window-aware counting,
metrics.md), what the exit criterion needs, the gap. `ads_insights_performance_trend`, when connected, is
trend-render corroboration only — the append-only log stays the verdict
source, and `targets_version` stamping lives in the log, never in Meta's trend
view.

**3. Write** `kpi_log` pointer on first entry.

## Terminal paths — inline blocks (routing.md grammar)

**Trends rendered (E23):**

**Next moves**
1. *If invoked by brief/review:* back to the caller — the verdict feeds it.
2. *If exit criteria are trending met:* the evidence exists now — run the scale audit. Say: "should I scale"
3. *If launched and data is thin (insufficient-data verdicts):* keep the cadence — the log builds itself. Say: "daily brief"
4. Not sure where this leaves you? The compass always knows your next move. Say: "what's next"

## Teach mode
In `new`: "exit criteria" deep-glossed with the coach's actual numbers
("your target is $X — the bar for stage 2 is holding at-or-under it for
7–14 straight days; you're at N"); the version-boundary rule explained
("what this means for you: after a re-math, old rows are graded against
old rules — I never mix them"); primary-vs-storytelling in one line
("primary metrics decide, storytelling metrics only explain the why"). In
`learning`: brief. In `pro`: the trend table.

## Guardrails
- Append-only; `targets_version` stamps make history honest (F3 cascade).
- Storytelling columns recorded, never decisive.
- Manual-paste and CSV are first-class sources.
