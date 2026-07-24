---
name: meta-ads-superengine:meta-ads-daily-brief
description: The 60-second daily glance at a running campaign — pacing, cost per lead versus target, and fatigue flags. At Stage 1 it is read-only by design — it shows the numbers and then talks the coach OUT of touching anything, enforcing the 72-hour and learning-phase rules. Trigger phrases include "daily brief", "how are my ads doing", "check my ads", "today's numbers".
---

# meta-ads-daily-brief — the 60-second glance

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #23.
The job is as much psychological as analytical: the most expensive beginner
habit is "fixing" a young campaign. This skill shows the numbers, then
protects the coach from themselves.

## Load
- shared refs + `metrics.md`
- Active brand state → `launched_at`, `stage`, `targets`, `bad_day_counter`,
  `creatives` (clocks), `last_review` (for the review-day check)
- Brand check (rule 6): a brand named in the coach's message that isn't `active_brand` → stop, offer "switch brand" first ... never another brand's numbers silently.
- Numbers: MCP read if connected, else paste today's row OR a CSV export from
  Ads Manager (both first-class)

## Prereq (E0)
`launched_at` (native or imported). Missing → "a brief needs a live campaign";
render the **no launch on record yet** block below (keeps the full road open,
not just launch-runbook).

## Steps

**1. The glance (60 seconds, primary metrics lead):** spend pacing vs daily
budget · results + cost/result vs `targets` (stamped version) · days since
launch (`launched_at`) and since the newest creative went live (the most
recent `creatives[].live_at`) — the clocks (the plugin never edits live
objects in place, so a refreshed creative = a new `live_at`, which IS the
"last edit" clock).

**Live source (when connected):** if the marker shows `connections.meta_mcp`
connected, these numbers come from `ads_get_ad_entities` (campaign level,
`date_preset: "today"`, plus a `yesterday` pull so pacing has a comparison),
read with catalog field names (`amount_spent`, `results`, `cost_per_result` /
`cost_per_lead`). Not connected → the coach pastes today's row or drops a CSV
export — both first-class, the brief runs identically. `delivery_sub_status`
(ad-set level) surfaced as one line when it reads learning-limited —
teach-glossed at `new`/`learning` (what "learning limited" means, not an
alarm). `ads_account_get_activity_logs` is GATED on rollout (verified 07.22.26): when available,
the edit log cross-checks the do-not-touch clock (did anything actually get
edited?) — detect-first only, never a prereq.

**2. Storytelling row (WHY only, never a decision):** CPM trend, frequency,
hook rate — flagged as fatigue EVIDENCE feeding the weekly review, never as
a reason to touch anything today.

**3. Stage-1 lockout enforcement (the teach moment):** inside 72h of
`launched_at` (or of the newest `creatives[].live_at` — a fresh creative
restarts its own clock), or at stage 1 generally — the brief is
READ-ONLY. Show the numbers, then the speech: *"Nothing here needs action.
Touching it restarts the learning clock — today's best move is a closed
laptop."* Optimization actions unlock at stage ≥2, and even then route
through the weekly review, not the daily glance.

**4. Bad-day protocol:** a day clearly over target → `bad_day_counter`+1
(reset on a normal day). Most dips self-correct — do NOTHING for 3 days.
Counter hits 3 → F7: performance-review is MANDATORY before any cut; cuts
≤20%, never below `targets.hard_deck`. When connected,
`ads_insights_anomaly_signal` is a TRUSTED-DETECTION input (metrics.md): it
may objectively confirm the day is a statistical outlier and increment the
counter as EVIDENCE — it NEVER prescribes an action, never overrides the
3-day wait or the F7 review-before-cut.

**5. Log it:** invoke the kpi-tracker procedure to append the day's
`window_days: 1` row ... a daily pull is a sanctioned entry (metrics.md), not a
rule violation. When
the recent log is trending on-target, append one exit-criteria progress line
read from the kpi-log — e.g. "day 5 of 7 on-target — 2 more days to scale
evidence." Reads the log only; kpi-tracker stays the data owner.

## Terminal paths — inline blocks (routing.md grammar)

**Normal day (E15):**

**Next moves**
1. Nothing to do — that's the win. See you tomorrow. Say: "daily brief"
2. *If review day (7+ days since last review):* the weekly diagnosis. Say: "review my ads"
3. Where am I on the road? Say: "what's next"

**Next moves — 3 bad days (F7)**
The counter hit 3 — this is now a diagnosis job, not a budget knob:
1. Run the weekly review NOW — it finds the why and routes the fix. Say: "review my ads"  ← start here
2. *Only after the review:* if a cut is prescribed, it's ≤20% and never below your hard deck — I'll walk it.

**Next moves — rejection/restriction noticed (F8)**
1. Triage before touching anything. Say: "my ad got rejected"

**Next moves — no launch on record yet (E0: `launched_at` missing)**
A brief needs a live campaign — but here's the whole road, not a dead end:
1. See where you are and what's next on the journey. Say: "what's next"  ← start here
2. *If `last_review.verdict` is `"imported-no-live"`:* that import already came back empty ... the road is a relaunch, not another import. *If `targets` exist,* plan the relaunch. Say: "plan my campaign" *... otherwise run the numbers first.* Say: "run my numbers"
   *Else, if past/current campaign data exists (ran ads before, or exports to import):* diagnose it in import mode. Say: "review my ads"
3. *If the LAUNCH gate is met (`compliance` pass @ current `offer_version` AND `funnel.qualified_event` AND `campaign_plan`):* go live now. Say: "launch my campaign"
   *If a gate piece is missing, build it first:* *no compliance pass?* Say: "compliance check" *· no qualified event?* Say: "qualify my leads" *· no plan?* Say: "plan my campaign"

## Teach mode
In `new`: the 72h lockout and learning phase get full deep-tier treatment
(barista analogy, "every edit restarts the clock"); pacing/CPL glossed with
the coach's own target as the worked example; the do-nothing prescription
explained as strategy, not neglect. In `learning`: brief whys. In `pro`:
the numbers table + verdict line. **The lockout speech renders at FULL
strength at every level.**

## Guardrails
- NEVER prescribes an optimization at stage 1. Ever.
- Storytelling metrics never trigger actions (metrics.md hierarchy).
- Cuts only via F7 → performance-review; hard deck is inviolable.
- One pull per day — live data must not enable nervous-refresh.
- A glance is not a trading terminal; live numbers change nothing about the
  wait windows (no day-trading).
