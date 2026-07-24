---
name: meta-ads-superengine:meta-ads-launch-runbook
description: The guided Ads Manager click-path that turns a campaign plan into an actually-launched campaign. Builds everything paused, verifies the settings, publishes deliberately, then writes the go-live facts and gives the 72-hour do-not-touch briefing. This is the skill that stops the coach ending with a plan instead of a live campaign. Trigger phrases include "launch my campaign", "launch it", "go live", "publish my ads".
---

# meta-ads-launch-runbook — the launch executor

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #21.
The DoD keystone: **zero → launched, never a dead end.** Native writer of
`launched_at` — daily-brief's 72h lockout, creative-test's dual clock, and
performance-review's week-1 mode all compute from it.

## Load
- shared refs + `naming.md`
- Active brand state → `campaign_plan`, `creatives`, `compliance`, `funnel`,
  `stage`, `targets`

## THE GATE (prereq, hard — E0 with the exact missing item)
All three must hold, else refuse and route:
1. `campaign_plan` artifact exists → else campaign-plan.
2. `compliance[]` has a **pass matching the current `offer_version`** → else
   compliance-check (a stale pass for an older offer does NOT count).
3. `funnel.qualified_event` is set → else funnel-qualify.
State the block plainly and route to the missing door — never launch around a
missing gate.

## Pre-flight (before the build walk — the gate passed; now make the launch honest)

**Tracking liveness** (informed consent, NOT a hard block). Read `signal.pixel`
and `signal.capi`. If either is null or `pending`, say it plainly: "Meta will
optimize on raw form-fills, not qualified leads — your cost per QUALIFIED lead
will look worse than it is." Then require an explicit, acknowledged choice
(Instant-Forms coaches legitimately launch pixel-light — never launch blind,
never refuse):
- (a) wire tracking first. Say: "set up tracking"
- (b) proceed on the fallback objective, acknowledged — record an open_loop
  ("tracking pending — revisit after launch") so the compass surfaces it later.

**Visual-asset check.** Every `produced` concept in the plan must have a
visual artifact ... a populated `artifacts.static` or `artifacts.script` key
(image/video file); copy alone can't be placed. A concept with only text kinds
(`artifacts.hooks` / `artifacts.copy`) and no visual routes to production
first: Say: "make static ads" or Say: "write my video script" (then produce
the visual), before the build walk continues. A concept carrying only a legacy
single `artifact` string is unverifiable-kind ... ask the coach whether a
visual exists rather than assume it does.

**Delivery-blocker scan** (detect-first). IF the marker shows
`connections.meta_mcp` connected: run `ads_get_errors` (read-only) and surface
any account-level blockers on THIS campaign — incomplete creative, deprecated
formats — BEFORE the coach clicks publish. Not connected → one line ("no MCP —
skipping the automated error scan; watch for red banners in Ads Manager") and
move on. Paste-first coaches unaffected.

## Steps (build PAUSED, then publish)

**1. Build paused** — walk Ads Manager screen by screen, names verbatim from
the plan (`naming.md`): campaign (objective, CBO, budget) → ad set (broad:
location/age-floor/language; automated bidding) → **ads, placed by the plan's
asset-source lane** for each `creatives[].id`, 5-slot copy variants in place
where produced:
- **(a) upload** (`source: produced` or `upload`) — upload the file, map it to
  its `creatives[].id`. Phone-shot video? Get the file onto this machine first
  (AirDrop / Drive / email it to yourself) before you start.
- **(b) existing post** (`source: post-id`) — use Ads Manager's "Use existing
  post" flow and enter the `post_id` from the plan; keeps the likes/comments
  social proof (best-content synergy).
- **(c) an asset with no `creatives[]` row** (coach brings something new at
  launch) — do NOT improvise a row here; register it first so the registry and
  naming line up. Say: "creative strategy"

Everything stays **paused**.

**2. Verify before publish** (checklist):
- objective = Leads/Sales · CBO on · budget matches targets · broad settings
  correct · enhancement rules per canon (creative-modifying OFF,
  multi-advertiser OFF for high-ticket) · qualified event selected as the
  optimization event · Post-ID used where a proven organic post is being run
  as an ad (best-content synergy).

**3. Publish** — the coach flips paused → active deliberately. **Confirm by
read-back, not honor system:** ask the coach to read the Delivery column out
loud.
- "In review" = published (review can take hours; if it flips to Rejected,
  that's the rejection route — Say: "my ad got rejected").
- "Draft" or "Paused" = NOT published — do not write `launched_at`; walk back
  to the unfinished screen.
Only on a published read-back (In review / Active) do you write the go-live
facts.

**4. The 72h briefing** (teach moment at every level): every edit re-enters
learning; do NOT touch it for 72h; daily-brief will show numbers and talk you
out of tweaking. Set the expectation of a launch-day wobble.

**5. Write** `launched_at` (native writer — the F5 import backfill in
performance-review is the one sanctioned exception, see state-schema rule 5),
each launched `creatives[].live_at` + status "launched".

## Re-activation (turning a paused campaign back on)
Trigger: the coach says they re-enabled, or plan to re-enable, a
previously-launched campaign in Ads Manager. Say: "I turned my ads back on".
THE GATE above does NOT block a re-activation ... the campaign already exists
and the coach flipped it on outside the plugin; refusing here would just leave
the clocks wrong. Instead, any gate piece missing for the CURRENT offer
(compliance pass, qualified event, plan artifact) is flagged plainly as a
post-launch loose end → `open_loops`, with the fix route named.
This is the one other motion that stamps `launched_at`, and it stays the native
writer ... no new writer, no exception to ownership. Re-entering delivery
restarts the learning clock, so the go-live facts get re-stamped.

**Confirm by read-back, the same discipline as first publish** (never honor
system): ask the coach to read the Delivery column out loud.
- "Active" or "In review" = back on ... proceed to re-stamp.
- "Paused" or "Draft" = NOT re-enabled ... do not write `launched_at`; nothing
  to re-stamp yet.

On a confirmed read-back:
- Write a fresh `launched_at` + `launched_at_source: "reactivation"` (same
  native writer, per state-schema rule 5 and the ownership table).
- Re-run **the 72h briefing** (step 4) ... re-entering learning is the teach
  moment: do NOT touch it for 72h; the daily brief will show numbers and hold
  the clock.
- Update `creatives[].live_at` ONLY for the creatives actually re-entering
  delivery. Unclear which ones got re-enabled? Ask the coach ... never guess.

From here the post-publish next-moves apply exactly as after a first launch
(E14): the daily brief tomorrow.

## Rejection at publish (F8)
Ad rejected / account restricted at go-live → compliance-check
**rejection-triage** sub-mode (live policy lookup, appeal path,
don't-make-it-worse). Do not blindly resubmit.

## Terminal paths — inline blocks (routing.md grammar)

**Published (E14):** the v0.1 success terminus — the coach has a LAUNCHED
campaign. Preamble: what went live + the 72h speech, then:

**Next moves**
1. Tomorrow: your 60-second glance — I'll show the numbers AND hold you to the 72-hour do-not-touch rule. Say: "daily brief"  ← start here
2. Set the measuring stick now — baseline the KPI log against your targets. Say: "show my trends"
3. Nothing else today. Touching the campaign now restarts its learning — the best move is a closed laptop.

**Next moves — gate refused (E0)**
Launch is blocked; the missing item is named plainly:
1. *If no campaign plan:* build the structure first. Say: "plan my campaign"
2. *If compliance missing/stale for this offer:* run the live gate. Say: "compliance check"
3. *If no qualified event:* build the qualified-lead layer. Say: "qualify my leads"

**Next moves — stopped mid-build**
A precise stop-point (which screen, which blocker), never "come back later":
1. Resume the click-path at the exact screen we stopped. Say: "launch my campaign"
2. *If stopped by a rejection/restriction:* triage it before touching anything. Say: "my ad got rejected"

**Rejection at publish (F8):** route to the triage trigger above; do not
blindly resubmit.

## Teach mode
In `new`: every Ads Manager screen glossed ("this toggle is X, leave it
because Y"); the paused-first why and the 72h lockout get full deep-tier
treatment (learning-phase barista analogy, "what this means for you: every
edit restarts the clock"). In `learning`: screen names assumed, settings
whys brief. In `pro`: the click-path checklist, terse. **The 72h speech and
gate refusals render at FULL strength at every level.**

## Guardrails
- Never write `launched_at` if the campaign isn't actually published; the same
  read-back gates a re-activation re-stamp (a "Paused" or "Draft" Delivery
  column means no write).
- No write-scope automation in v1 — the coach clicks publish; the skill
  guides. (ops-setup keeps write scopes off — premortem #12.)
