---
name: offer-architect:assess-feasibility
description: Score 2-4 alternative offer positionings on a weighted matrix (TAM, defensibility, pricing power, voice fit, time-to-revenue, liability, content fit, scalability) and recommend one with confidence rating. Use after find-gaps. Trigger phrases include "score the offer", "feasibility analysis", "compare positioning", "weighted scorecard for the offer".
---

# offer-architect:assess-feasibility

Quantify the offer-positioning decision so the coach doesn't pick on vibes.

## Step 0 — Read inputs

- Coach Profile
- Market Research (especially §9 alternative positionings)
- Gaps doc

## Step 1 — Define alternatives (2-4)

If market-research §9 already proposed positionings, use those. Otherwise, ask the coach for 2-4 distinct positioning bets to compare. Examples (longevity coaching):
- A: Integrated longevity (broad)
- B: Peptide-first specialty
- C: Performance/longevity for affluent men 40-55
- D: Coach-the-coaches (B2B)

Each alternative gets a short paragraph describing the bet.

## Step 2 — Score on the weighted matrix

| Dimension | Weight | Why this matters |
|-----------|------:|------------------|
| TAM size | 3 | Market headroom |
| Defensibility / moat | 4 | Can competitors copy you? |
| Pricing power | 5 | What can you charge? |
| Voice / personality fit | 4 | Will the coach actually execute it? |
| Time-to-revenue | 5 | How fast can the first dollar land? |
| Liability exposure (inverted) | 5 | Higher = better (less risk) |
| Content production fit | 3 | Can the coach reliably produce content? |
| Scalability ceiling | 4 | Solo vs team economics |

Each dimension scored 1-10 per alternative. Multiply by weight. Sum to a weighted total. Rank.

Weights can be adjusted if the coach has specific constraints (e.g., capital-light = increase weight on time-to-revenue and lower weight on TAM).

## Step 3 — Recommendation

Output:
- Ranked alternatives with weighted totals
- Recommended primary
- Recommended fallback (run if primary fails to convert in 90 days)
- Kill list (alternatives to abandon and why)
- Confidence rating per call (Low / Medium / High) with reasoning
- Risk matrix: top 3 risks of the recommended path with mitigation

## Step 4 — Save

Use `templates/feasibility-scorecard-template.md`. Save to `output/research/Feasibility Scorecard - [MM.DD.YY].md`.

## Step 5 — Confirm

Walk the coach through the matrix. The recommendation is a hypothesis, not a dictate. Ask: "Do you accept this primary bet, or do you want to adjust weights / add an alternative I missed?"

## Step 6 — Exit check

Before exiting, run the `assess-feasibility` checklist in `references/skill-exit-checks.md`. For each item:

- **PASS** → continue
- **GAP** → surface to coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"* If "defer", append to `tasks/findings.md` and footnote the artifact: `> ⚠️ Deferred from exit check: [item] — [reason]`
- **FAIL (hard)** → do not exit. Block until resolved.

The exit check is the preventive layer. The capstone PSS is the audit layer.

## Operating rules

- **Weighting is the lever.** Don't hide the weights — explain why each dimension is weighted the way it is.
- **Score with reasons.** Each score gets a 1-sentence rationale. "8/10 because [specific reason]."
- **Default-bias toward simplicity.** When two alternatives score within 5% of each other, pick the simpler one to execute.
- **Liability is inverted.** Higher score = lower risk. Make sure the math reflects this.
