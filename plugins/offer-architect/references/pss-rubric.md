# Projected Success Score (PSS) Rubric

The PSS scores an offer's launch-readiness on a 0–100 scale using a **hybrid two-view model**: 11 raw section scores (transparency) roll up into 10 weighted strategic dimensions (decision-making).

> **Two-layer scoring system:**
> - **Preventive layer** — `references/skill-exit-checks.md` defines per-skill exit checks each upstream skill runs before completing. Catches gaps at their source.
> - **Audit layer** — this rubric, run by `build-offer-blueprint` at the capstone. Scores what made it through.
>
> The two layers stay in sync: when a recurring gap shows up here at the capstone, it gets added to the relevant upstream skill's exit check.

---

## Section view — 11 raw sections (0–100 each, unweighted display)

Mapped 1:1 to the Offer Blueprint structure. Each section gets a raw score for transparency. The coach sees exactly which section is weak.

| # | Section | What "good" looks like |
|---|---------|------------------------|
| 1 | Client Snapshot | Avatar specific (demographics + psychographics), dream outcome in 1 sentence |
| 2 | Core Offer Summary | Promise + mechanism + format all stated, no fuzz |
| 3 | Value Stack Distilled | ≥6 `[confirmed]` items, total stacked value ≥4× price |
| 4 | Pricing Decision | One structure locked, payment terms clear, price defended vs comparables |
| 5 | Guarantees & Risk Reversal | Verbatim guarantee text, asymmetric in coach's favor only when claim-substantiated |
| 6 | Naming & Positioning | Named, two-axis-scored, 1-line positioning crisp |
| 7 | Marketing Seeds | ≥3 headlines, ≥3 pain hooks, ≥3 transformation hooks, all backed by research |
| 8 | Funnel/Page Notes | Funnel shape stated, must-include sections listed |
| 9 | Content Angles | ≥5 topics each mapped to a researched pain or dream point |
| 10 | Program & Deliverables | Phase or week-by-week structure, all items `[confirmed]` |
| 11 | Source Citations | Every claim links back to an artifact or research source |

---

## Dimension view — 10 weighted strategic dimensions (drives final PSS)

Section scores roll up to dimensions. Dimensions are weighted by **impact on whether the offer works at all**, not equally.

| Dimension | Weight | Rolls up from sections |
|-----------|--------|------------------------|
| Value Equation | **15** | §3 Value Stack |
| Market-Fit | **15** | §1 Snapshot, §7 Marketing Seeds, §9 Content Angles |
| Pricing Defensibility | **15** | §4 Pricing Decision |
| Guarantee Strength | **15** | §5 Guarantees |
| Avatar/Pain | **7** | §1 Snapshot |
| Dream Outcome | **7** | §2 Core Offer Summary |
| Positioning | **7** | §6 Naming & Positioning |
| Differentiation | **7** | §6 Naming & Positioning, §7 Marketing Seeds |
| Naming | **6** | §6 Naming & Positioning |
| Launch-Readiness | **6** | §10 Program & Deliverables, §11 Citations |
| **Total** | **100** | |

Weights are **hidden by default** in the PSS report. A collapsible "How this is scored" section reveals them.

---

## Audit-to-PSS deduction map

The `offer-market-auditor` agent runs 4 checks. Findings deduct from dimension scores. This integration means the audit doesn't produce a separate doc — its findings reshape the PSS.

| Audit Check | FAIL = | FLAG = |
|-------------|--------|--------|
| Price Defensibility | Pricing Defensibility capped at **40** | −15 pts on Pricing Defensibility |
| Audience Pain Validation | Avatar/Pain + Market-Fit each capped at **40** | −15 pts on each |
| Claim Substantiation | Guarantee Strength + Value Equation each capped at **50** | −15 pts on each |
| Competitive Position | Differentiation + Positioning each capped at **40** | −15 pts on each |

PASS = no adjustment.

---

## Provenance tagging affects scoring

| Tag | Counts at... |
|-----|-------------|
| `[confirmed]` | **100%** weight |
| `[coach-to-build]` | **50%** weight (until built and confirmed) |
| `[suggested-optional]` | **0%** weight (does not count unless coach accepts) |

This is the **hard guardrail against inflated scores from invented deliverables**. A value stack of 10 items where 8 are `[suggested-optional]` scores like a stack of 2.

---

## Score bands

| Band | Range | Label | What it means (coach-facing) |
|------|-------|-------|-------------------------------|
| 🔴 | 0–20 | Bad | The offer won't sell. Major rework before anything else. |
| 🟠 | 20–50 | Weak | Foundation is shaky. Fix the red sections before testing in market. |
| 🟡 | 50–70 | Workable | You could launch, but you'll leave money on the table. Worth tightening first. |
| 🟢 | 70–90 | Strong | Close to launch-ready. Fix the top items, then go. |
| 🟢🟢 | 90+ | **Launch-Ready** | Your offer is ready. Launch now. |

**Hard line:** Only the 90+ band signals "launch now." The Strong band (70–90) is the on-deck zone — solid foundation but with top-priority fixes still pending. This distinction matters: telling a coach at 75 to "launch and iterate" sets them up to launch a flawed offer when 2 weeks of work would put them in the green-green band.

---

## General scoring rubric (for inferred-option fields)

Used when the skill generates scored options for hero promise, positioning, headlines, content hooks (NOT naming — naming uses the two-axis rubric below).

Score 0–2 on each of 5 axes, total /10:

| Axis | 0 | 1 | 2 |
|------|---|---|---|
| **Specificity** | Vague | Names target OR mechanism OR outcome | Names target AND mechanism AND measurable outcome |
| **Strategic fit** | Misaligned with avatar/dream | Partial alignment | Directly hits researched avatar pain + dream outcome |
| **Differentiation** | Indistinguishable from 3 competitors | Mild differentiation | Clearly distinct from named competitors |
| **Believability** | Hype, unsupported | Plausible | Substantiated by research or methodology |
| **Memorability** | Forgettable | Sticky on second read | Sticks after one read |

---

## Naming rubric — two-axis (each /10)

Names are scored on BOTH axes simultaneously. Different frameworks tilt different ways.

**Axis 1 — Cold-traffic conversion potential** (0–2 each):
- Clear promise stated
- Specific timeframe or number
- Avatar called out
- Mechanism hinted
- Curiosity / pattern interrupt

**Axis 2 — Brand-trust longevity** (0–2 each):
- Confident without hype
- Won't sound dated in 5 years
- Pronounceable + spellable (Watkins SCRATCH test)
- Distinctive, not generic (Neumeier criterion)
- Extensible (sub-products fit under the name)

Each name candidate displays both scores + framework attribution, e.g.:

> **"Heal-Strong"** [Neumeier] — Cold-traffic: 4/10 · Brand-trust: 9/10
> **"The 12-Week Heal-Strong Reset"** [MAGIC] — Cold-traffic: 9/10 · Brand-trust: 5/10

Default recommendation by audience:
- **Premium / professional / high-sophistication** → Neumeier / Watkins defaults
- **Mass-market / cold-funnel / low-sophistication** → MAGIC default

Naming is a **taste call**. The skill shows scores and does not defend any single option against the coach's preference.
