---
name: offer-architect:find-gaps
description: Read the coach profile + market research and produce a checkboxed list of open questions, untested assumptions, and recommended follow-up research. Use after research-market to ensure nothing critical is missing before feasibility scoring. Trigger phrases include "find gaps", "what's missing", "open questions for the offer".
---

# offer-architect:find-gaps

Diagnostic pass. Identify what's missing before downstream offer construction.

## Step 0 — Read inputs

- `Clients/[Coach Name]/Coach Profile - *.md`
- `output/research/[Niche] - Market Research - *.md`
- Any other docs in `Clients/[Coach Name]/`

## Step 1 — Run gap categories

For each category, list specific items the coach must answer or research before the offer can be finalized:

### A. Coach data gaps
- Numbers not provided (close rate, churn, current LTV, time-to-deliver per client)
- Voice samples missing
- ICA fields ambiguous or under-specified
- Partnerships referenced but not yet confirmed

### B. Market data gaps
- Pricing tiers where research returned conflicting or thin data
- Competitor data where positioning was inferred not confirmed
- Regulatory claims that need attorney review
- Add-on costs (tests, scans) where pricing range was wide

### C. Assumption gaps (things the research assumed)
- Each major assumption explicit, with the basis (research § / source) and an indicator of confidence

### D. Decision gaps (things the coach must decide)
- Positioning bet (which of the alternatives from market-research §9)
- Inclusion-vs-add-on decisions for specific deliverables
- Brand voice direction
- Partnership terms (fee splits, referral structures)

### E. Validation gaps (things to test before scaling)
- Close rate target
- Price-elasticity thresholds
- Format-preference unknowns (e.g., live calls vs async)

## Step 2 — Write checkboxed deliverable

Use `templates/gaps-template.md`. Each gap should be a checkbox with:
- The question / missing item
- Who answers it (coach, attorney, partner, research)
- Whether it's blocking or non-blocking for finalization
- Suggested next action

## Step 3 — Save and review

Save to `output/research/Gaps & Open Questions - [MM.DD.YY].md`.

Show the coach a count: "X total gaps. Y are blocking. Z are non-blocking — can finalize without."

Ask the coach to mark the blocking ones with answers or with a "decide later" note.

## Step 4 — Exit check

Before exiting, run the `find-gaps` checklist in `references/skill-exit-checks.md`. For each item:

- **PASS** → continue
- **GAP** → surface to coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"* If "defer", append to `tasks/findings.md` and footnote the artifact: `> ⚠️ Deferred from exit check: [item] — [reason]`
- **FAIL (hard)** → do not exit. Block until resolved.

The exit check is the preventive layer. The capstone PSS is the audit layer.

## Operating rules

- **Severity matters.** Always distinguish blocking from non-blocking. Don't make a coach feel they have to resolve everything to move forward.
- **Suggest specific actions.** "Talk to attorney" is weak; "30-min consult with healthcare attorney specializing in fitness/wellness scope-of-practice in CA" is actionable.
- **Don't invent gaps.** If the research is solid and the profile is complete, the doc can legitimately say "no critical gaps; proceed to feasibility."
