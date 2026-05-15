---
name: offer-architect:price-matrix
description: Build three pricing structures (1mo / 3mo / 6mo / 12mo / VIP) with pros/cons for each, applying the Hormozi commitment-ladder rule (shorter commitment = higher per-month). Includes add-on policy and trigger events to raise prices. Use after build-value-stack. Trigger phrases include "build pricing matrix", "price the offer", "tier pricing", "commitment pricing ladder".
---

# offer-architect:price-matrix

Three pricing ladders for the coach to pick a launch posture from.

## Step 0 — Read inputs

- Coach Profile
- Market Research §3 (pricing benchmarks) and §6 (premium anchors)
- Value Stack (especially total perceived value)
- Reference: Hormozi commitment-pricing data (annual 2% churn vs monthly 10.7%, LTV 5×)

## Step 1 — Anchor the math

From market research, identify:
- Market low / mid / high for 1mo, 3mo, 6mo, 12mo containers in this niche
- Premium ceiling anchor (concierge tier, e.g., Fountain Life APEX-level)
- Coach's current pricing (if any)

## Step 2 — Build three structures

Each structure is a complete ladder. Use the Hormozi commitment rule: 1mo per-month price is 30-50% higher than 12mo per-month.

### Structure A — Market-Mid Launch (Conservative)
- 6mo hero sits at market mid
- 1mo, 3mo, 12mo derived from hero with appropriate commitment discounts
- VIP tier at high-end of "VIP/DFY monthly" market band
- Posture: fastest cohort fill, lowest pricing power

### Structure B — Stretch Defensible (Recommended)
- 6mo hero sits at upper-mid-to-premium of market
- Aligns with specialized / niched pricing (e.g., specialized hormonal/metabolic $600-800/mo benchmark)
- VIP tier higher than Structure A
- Posture: best balance of close rate and margin; recommended after 4-5 founding clients

### Structure C — Premium Ceiling (Aspirational)
- 6mo hero in premium tier (anchored to concierge longevity / executive performance comparables)
- 12mo hero competitive with mid-tier concierge medical
- VIP tier full concierge price point
- Posture: requires 8+ case studies; max margin per client; lowest close rate

## Step 3 — Pros / cons per structure

For each structure, list 4-6 explicit pros and 3-5 explicit cons. Tie to specific market signals.

## Step 4 — Add-on policy table

For each significant add-on (tests, scans, in-person visits, supplements), specify per-structure inclusion:
- ✅ Included all tiers
- Optimization+ included
- Optimization+ subsidized
- Add-on, client pays direct (Hormozi: never include something logistically painful that clients can self-source easily)
- Optionally included at top tier only

Common policy: bloodwork included if the coach has a low-cost partner; DEXA always client-pays (decentralized in 2026, $40-$200 retail); VO2 max scales by structure.

## Step 5 — Maintenance tier

Pricing for the post-program continuation (from Value Stack §7). Typically 20-35% of hero monthly equivalent. Same across structures unless there's a reason to differ.

## Step 6 — Trigger events for price moves

Document explicit conditions for moving up the structure ladder:
- Close rate target hit (e.g., 35% across 10+ application calls)
- Case study count (e.g., 3 documented biomarker deltas)
- Active client count (e.g., 15 actives at current tier)

Grandfather existing clients at old rates when raising.

## Step 7 — Save

Use `templates/pricing-matrix-template.md`. Save to `Clients/[Coach Name]/[Brand] Pricing Matrix - [MM.DD.YY].md`.

## Step 8 — Confirm + recommendation

Walk the coach through the matrix. Recommend launch posture (typically A → trigger to B → C). Confirm before exiting.

## Step 9 — Exit check

Before exiting, run the `price-matrix` checklist in `references/skill-exit-checks.md`. For each item:

- **PASS** → continue
- **GAP** → surface to coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"* If "defer", append to `tasks/findings.md` and footnote the artifact: `> ⚠️ Deferred from exit check: [item] — [reason]`
- **FAIL (hard)** → do not exit. Block until resolved.

**Critical FAIL item for this skill:** One pricing structure MUST be marked LOCKED before exit. Producing three structures and exiting with no lock leaks bookkeeping into the capstone — the PSS will dock points for an unlocked decision. If the coach genuinely needs more time, mark the decision as a flagged direct-ask gap rather than silently exiting.

The exit check is the preventive layer. The capstone PSS is the audit layer.

## Operating rules

- **Honest urgency only.** Founding-cohort pricing with a real trigger to raise is the only acceptable urgency mechanism at premium price points. No fake countdowns.
- **Numbers tie to math.** Every price has a derivation — market anchor + commitment discount + tier delta.
- **1-month is a filter, not revenue.** Build the 1-month tier as a funnel mechanism (credit toward upgrade), not a destination.
- **Match the structure to the moment.** A coach with zero case studies should not launch Structure C — flag it.
