---
name: meta-ads-superengine:meta-ads-breakeven-math
description: The numbers gate before $1 is spent. Works backward from the coach's offer to the CPL / cost-per-qualified-lead / cost-per-call they can actually afford, the breakeven ROAS, and a budget floor. Sanity-checks the inputs (a claimed 80% close rate gets challenged). Trigger phrases include "run my numbers", "breakeven math", "what can I pay per lead", "meta ads math".
---

# meta-ads-breakeven-math — the math gate

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #7.
This is the floor every downstream target reads. **Never skip on impatience** —
the #1 beginner failure is filming/boosting before the math exists.

## Load
- `state-schema.md`, `journey-map.md`, `routing.md`, `teach-mode.md`, `glossary.md`, `canon.md`, `metrics.md`, `vault-api.md` — under `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/`
- Active brand state → `setup.offer/price/close_rate/show_rate/lead_to_call_rate`

## Prereq (E0)
`setup.offer` + `setup.price` != null (0 is VALID — free front end; requires
`setup.backend_price`). Missing → route to setup with the plain why.

## Steps

**1. Gather + sanity-check inputs.** Pull from setup; ask for the rest.
FIRST, the funnel shape (it decides which rates even matter): *"Does a sales
call sit between a lead and a purchase, or do people buy directly?"* →
`setup.funnel_type` (`"call"` | `"checkout"`). Then gather by type.

**Call funnel.** Sanity-check each rate with a concrete question, not a
number demand:
- close rate (booked call → client): *"Out of your last 10 sales calls, how
  many became clients?"* A claimed 80% gets the gentle challenge — most
  high-ticket close rates are 20–40%; an inflated rate makes every target
  below too generous.
- show rate (booked → showed): typical 50–70%.
- lead → booked-call rate: typical 5–20% of qualified leads.
- qualification rate (raw lead → passes your questions): *"Out of 10 leads
  who hit your questions, how many pass?"* → `setup.lead_to_qualified_rate`,
  typical 30–70%. Flag if outside the band, same as the others.

**Checkout funnel.** No call step, so ask `setup.lead_to_purchase_rate`
(lead → buyer) if the coach knows it; skip freely (targets.cpl stays null
until real data, and that's honest).

**Subscription probe** (either type): if the price is monthly/recurring, ask
*"how many months does an average client stay?"* → `setup.avg_retention_months`.

**Gross margin** (light touch): *"any real per-client delivery costs ...
software seats, physical product, paid staff per client?"* If none, leave
`setup.gross_margin` null (service assumption, ~1.0); only set it when real
costs exist.

Flag any input that sits outside a plausible band; use the coach's number but
note the risk.

**2. Compute (show the formula line by line at `new`).**
`client_value` = what a closed client PAYS: `setup.price`, OR
`setup.backend_price` when price ≤ 0 (free/low-ticket front end). Two-price
offers anchor on the backend — ask if both are null. **Subscription offers:**
`client_value = monthly price (or backend monthly) × avg_retention_months`
(lifetime value, not one month). `client_value` is persisted to
`targets.client_value` so a re-run reproduces the same anchor.
```
CALL FUNNEL:
value per booked call    = client_value × close_rate × show_rate
value per qualified lead = value per booked call × lead_to_call_rate
value per lead           = value per qualified lead × lead_to_qualified_rate
target CPL               = value per lead × margin_factor        (0.3–0.5 to start)
target CPQL              = value per qualified lead × margin_factor

CHECKOUT FUNNEL:
target CPA = client_value × margin_factor
target CPL = client_value × lead_to_purchase_rate × margin_factor   (only if the rate is known; else targets.cpl stays null until real data, say so honestly)

BOTH:
breakeven ROAS = 1 / gross_margin       (service offers, no real delivery costs: gross_margin ≈ 1.0 → breakeven at ROAS 1)
hard deck = a budget floor the coach won't cut below in a bad-day protocol
```
Anchor the reframe (canon/framework): *high-ticket coaches can tolerate
"expensive" leads — most quit at CPLs that were actually profitable. The
advanced advertiser doesn't have the best ROAS, they have the biggest
tolerable CAC.*

**3. Brain (named trigger — 1 search max).** Recipe row = funnel-event /
topic: query "breakeven CPL high-ticket coaching", variants keyed to the
offer type. Weave a corroborating pattern if returned; cite `[brain] <path>`.
Emit the self-evidencing line. Degrade per `vault-api.md` (F9).

**4. Write targets.** `targets.{cpl, cpql, cost_per_call, breakeven_roas,
hard_deck, client_value, offer_version_used}` (`offer_version_used` = the
current `offer_version` these targets ran against), bump
`targets.targets_version`, stamp `computed_at`. Show the coach the numbers AND the math (an artifact, not just
answers). Also **persist any inputs gathered here** that setup didn't already
hold — `setup.close_rate` / `setup.show_rate` / `setup.lead_to_call_rate` /
`setup.lead_to_qualified_rate` / `setup.lead_to_purchase_rate` /
`setup.funnel_type` / `setup.avg_retention_months` / `setup.gross_margin` (the
sanctioned writer, state-schema ownership) — so an F3 re-run has a baseline
to compare actuals against.

## Terminal paths — inline blocks (routing.md grammar)

**Targets computed (E5):** preamble names the numbers + "saved to your
journey file", then:

**Next moves**
1. Decide what Meta learns to find — buyers, not tire-kickers. The qualified-lead layer is THE coach edge. Say: "qualify my leads"  ← start here
2. Diagnose your spend stage — what your daily budget makes possible right now. Say: "what stage am I in"
3. *Parallel-safe, can run early:* the live policy check that gates launch. Say: "compliance check"

**Next moves — no-go (F6)**
The math doesn't work at any realistic CPL. Deliver the specific number that
has to change (price up, close rate up, or a cheaper-entry offer) — never a
shrug. *Free front end:* the lever is backend price or front-to-backend
conversion — not the front price. Append an `open_loops` entry (skill
`meta-ads-breakeven-math`, note = the blocking number) so the compass
resurfaces it. Then:
1. Revisit the offer or price — the one number that unlocks paid traffic. Say: "resume setup"
2. Park ads for now — your economics don't support paid traffic yet; here's the threshold to hit first. (No trigger — an honest stop, compass stays available: "what's next")

**Re-run (F3, from a downstream diverge):** recompute, bump
`targets_version`, warn that consumers (campaign-plan, scale-decision) must
re-check — then re-render the E5 block.

## Teach mode
In `new`: plain-English-first — walk the formula line by line in plain words
BEFORE naming CPL/CPQL/breakeven-ROAS (deep-tier glossary entries, worked
with the coach's own price + rates the moment they're captured), and give
the "expensive leads can be profitable" reframe its own "what this means for
you" line. Worked examples use `client_value`, never a $0 front price (no
"your $0 offer" glosses). In `learning`: gloss the money terms on first use.
In `pro`: inputs → table of targets → done.

## Guardrails
- No unattributed stats in any output (canon rule 1). The example figures in
  the framework ($2k client → $25/lead) are illustrative — label them as
  examples, never as the coach's result.
- Margin factor is a starting range, not a law — say so.
