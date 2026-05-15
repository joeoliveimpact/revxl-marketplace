# Skill Exit Checks — Preventive Scoring Through the Pipeline

Each upstream skill in the offer-architect pipeline runs an exit check before completing. The check is the slice of the PSS rubric that skill owns. If any item fails, the skill surfaces the gap to the coach and offers to fix it *before* exiting — so the PSS at the capstone reflects **offer quality**, not pipeline hygiene.

Cross-references `references/pss-rubric.md` (the scoring system) and `references/research-checklist.md` (the market-research evidence map).

---

## How an exit check works (operational template)

At the end of every upstream skill, add this step:

> ### Step N — Exit check
>
> Before exiting, run the checklist in `references/skill-exit-checks.md` for `[skill-name]`. For each item:
> - **PASS** — continue
> - **GAP** — surface to the coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"*
>     - If "fix now" → loop back to the relevant step
>     - If "defer" → append to `tasks/findings.md` AND mark in the artifact: `> ⚠️ Deferred from exit check: [item] — [coach's reason]`
> - **FAIL** (hard) — do not exit. Block until resolved.
>
> Exit checks are **3–5 items per skill** by design. They catch what would otherwise leak downstream to the capstone PSS.

---

## intake-coach

**Owns:** Avatar/Pain + Dream Outcome (partial)

| # | Check | Severity |
|---|-------|----------|
| 1 | Avatar has BOTH demographics (age, income, profession, geography) AND psychographics (fears, dreams, status motive, where they hang out) | GAP |
| 2 | Dream outcome is one sentence, pictureable, and frames the outcome externally (how others perceive the client) — not just internally ("I feel better") | GAP |
| 3 | Top 3 pains identified using verbatim ICA language where possible — not paraphrased coach-speak | GAP |
| 4 | Brand voice captured (3 adjectives + example sentence) OR explicitly deferred to finalize-offer | GAP |
| 5 | Coach's available deliverables enumerated — what they have today vs what they'd need to build. Drives provenance tagging downstream. | **FAIL** (hard) — without this, every downstream skill risks inventing |

---

## research-market

**Owns:** Market-Fit evidence, Pricing comparables

| # | Check | Severity |
|---|-------|----------|
| 1 | All 10 sections of `references/research-checklist.md` filled OR explicitly marked "data unavailable, recommend follow-up" | GAP |
| 2 | ≥3 named competitors with pricing (public or sourced estimate) | GAP |
| 3 | ≥2 premium/concierge anchors cited with annual price + inclusion list | GAP |
| 4 | ICA validation evidence dated ≤12 months from current year | GAP |
| 5 | Every dollar figure in the report has a URL or explicit "data unavailable" tag — no unsourced numbers | **FAIL** (hard) — downstream pricing decisions can't survive without sourced comparables |

---

## find-gaps

**Owns:** Differentiation evidence

| # | Check | Severity |
|---|-------|----------|
| 1 | Each gap maps to a specific section of the research report (not free-floating) | GAP |
| 2 | Each gap has an actionable next step OR an explicit defer-with-reason (`deferred — too costly to resolve before launch`) | GAP |
| 3 | No gap left as "TBD" without an owner (Jared / external research / partner) | GAP |
| 4 | Differentiation gaps explicitly identified — i.e., what makes this offer NOT like the 3 nearest competitors | GAP |

---

## assess-feasibility

**Owns:** Positioning

| # | Check | Severity |
|---|-------|----------|
| 1 | ≥2 alternative positionings scored (not just one) | GAP |
| 2 | Each positioning scored on the same weighted axes — apples to apples | GAP |
| 3 | Winner stated explicitly with 1-line rationale | GAP |
| 4 | Fallback positioning identified — what to switch to if the winner doesn't convert in the first 8–12 application calls | GAP |

---

## build-value-stack

**Owns:** Value Equation + Claim Substantiation (partial)

| # | Check | Severity |
|---|-------|----------|
| 1 | Value Equation scored on all 4 drivers (Dream Outcome ↑, Likelihood ↑, Time Delay ↓, Effort & Sacrifice ↓) with composite score | GAP |
| 2 | Every stack component has a provenance tag: `[confirmed]` / `[coach-to-build]` / `[suggested-optional]`. No untagged items. | **FAIL** (hard) — untagged items leak into downstream as if confirmed |
| 3 | Every outcome promise either substantiated by evidence (methodology, case data, anchor citation) OR hedged with conditional language ("if you complete checkpoints", "measurable improvement on 3 of...") | **FAIL** (hard) — unhedged absolute claims are FTC-risky and would flag at capstone audit |
| 4 | No FTC-risky absolute language without backing — scan for words like "guaranteed [number]%", "everyone gets", "100% of clients" | GAP |
| 5 | Stacked value-to-price ratio ≥4× (Hormozi bar). If <4×, flag for the coach: either trim price or add value before exit. | GAP |
| 6 | Marketing-headline candidates (if generated here) explicitly paired with hedge OR moved to claim-substantiation-friendly framing | GAP — this is the slot that caught Jared's "decade reversal" drift |

---

## price-matrix

**Owns:** Pricing Defensibility

| # | Check | Severity |
|---|-------|----------|
| 1 | Each structure has all 5 tiers (1mo / 3mo / 6mo / 12mo / VIP) | GAP |
| 2 | Each tier has at least one cited market comparable (URL or research-report reference) | GAP |
| 3 | Commitment-discount math is explicit — % off vs 1mo equivalent shown for each tier | GAP |
| 4 | **One structure is marked LOCKED before exit** — not "TBD" / "Jared decides later" / "recommended for Month 3+". The skill forces the lock decision or moves it to a flagged direct-ask. | **FAIL** (hard) — this is the gap that cost Jared 3 points at capstone |
| 5 | Add-on test costs (DEXA, VO2, bloodwork) included where relevant with COGS-vs-retail breakout | GAP |

---

## finalize-offer

**Owns:** Guarantee Strength, Naming, all final-lock items

| # | Check | Severity |
|---|-------|----------|
| 1 | Guarantee text is verbatim / copy-pastable — not "we'll figure out the language later" | **FAIL** (hard) |
| 2 | Guarantee language is conditional or appropriately hedged — no unconditional refunds at high-ticket without explicit reasoning for the exception | GAP |
| 3 | Offer name is LOCKED (final), not "candidate" / "TBD" / "leading option" | **FAIL** (hard) |
| 4 | Marketing-copy sections of the final offer doc (sales page, onboarding email, discovery call script) scanned for FTC-risky absolute language | GAP — clears Claim Substantiation FLAG before capstone |
| 5 | All 15 sections of `final-offer-template.md` filled OR explicitly marked deferred with reason | GAP |
| 6 | Pricing structure inherited from `price-matrix` is LOCKED here (not still "to be picked") | **FAIL** (hard) — last chance to enforce |
| 7 | Sales mechanism + onboarding flow stated (application vs direct buy, channels) | GAP |

---

## Operating rules for all exit checks

- **Don't over-check.** 3–5 items per skill. If a check is rarely failed in practice, drop it from a future version.
- **Severity matters.** GAP items can be deferred with a note. FAIL items block exit.
- **Capture the gap as evidence.** Every deferred GAP → entry in `tasks/findings.md` + warning footnote in the artifact. This way the capstone PSS knows what was deferred and can deduct appropriately.
- **The capstone runs the full PSS rubric anyway.** Exit checks are the preventive layer; PSS is the audit layer. Both layers exist on purpose.
- **Coach can always override.** Exit checks raise issues; coach decides what to fix vs defer. The skill is not the gatekeeper of the coach's business.

---

## Updating the exit checks

This file evolves with the pipeline. When a recurring gap shows up at the capstone PSS, add it to the relevant skill's exit check here. When a check fails almost never, drop it.

Maintain the rule: **3–5 items per skill** unless there's a strong reason otherwise. More items = more friction = less use.
