# Intake Required Fields — Schema for `build-offer-blueprint`

The skill checks every field below before drafting. Three resolution modes per field.

---

## Resolution modes

| Mode | When to use | How |
|------|-------------|-----|
| **Inferable** | Field can be derived from existing artifacts (research report, value stack, pricing matrix, transcripts) | Generate 2–3 scored options + 1-line why for each. Coach picks or writes own. Defend with evidence if coach picks materially weaker (except naming — taste call). |
| **Direct-ask** | Field is a coach decision/preference the artifacts can't reveal | Ask one question, one field at a time. No batched 20-question forms. |
| **Deep-research-prompt** | Field needs evidence the workspace doesn't have and can't WebSearch deeply enough | Emit a tailored copy-paste prompt for ChatGPT Deep Research / Claude Deep Research with niche/ICA pre-filled. Coach runs externally, pastes result back. |

---

## Required fields

| # | Field | Mode | Source if inferable |
|---|-------|------|---------------------|
| 1 | Avatar — demographics | Direct-ask (unless captured in Coach Profile) | Coach Profile |
| 2 | Avatar — psychographics | Inferable | Coach Profile + Research Report §1 |
| 3 | Dream outcome (1 sentence) | Inferable | Value Stack + Research Report §8 (ICA validation) |
| 4 | Top 3 pains the offer solves | Inferable | Research Report §1, §8 + Coach Profile |
| 5 | Offer name (or "needs naming") | Inferable (multi-framework — see below) | Final Offer doc OR generate from scratch |
| 6 | Hero promise (1 sentence) | Inferable | Value Stack §1 + Final Offer §1 |
| 7 | Primary mechanism | Inferable | Value Stack + Coach Profile |
| 8 | Chosen pricing structure (A/B/C) | Direct-ask | Pricing Matrix shows all 3; coach picks |
| 9 | Price points (locked) | Direct-ask (after structure pick) | Pricing Matrix |
| 10 | Guarantee type chosen | Direct-ask | Final Offer §5 if exists |
| 11 | Primary delivery format | Inferable | Value Stack + Coach Profile |
| 12 | Positioning angle | Inferable | Feasibility Scorecard alternatives |
| 13 | Top 3 named competitors | Inferable | Research Report §4 |

---

## Optional fields (only included if coach opts in)

| Field | Default | Note |
|-------|---------|------|
| Bonus stack details | OMIT unless coach says "yes I have these" | Hard rule: no inventing bonuses |
| Scarcity/urgency strategy | OMIT unless coach has one ready to enforce | Don't invent fake scarcity |
| Content pillar preferences | Suggest based on pains, mark `[suggested-optional]` | Coach must accept to count in PSS |
| Founding cohort pricing | Ask | If artifacts indicate yes/no, use that |
| Brand voice fingerprint | Inferable if `brand-voice` artifacts exist; else direct-ask | |

---

## Naming fields — special multi-framework handling

When field #5 (offer name) needs generation, produce **one candidate per framework**, minimum 4:

1. **Hormozi MAGIC** — Magnet, Avatar, Goal, Interval, Container word
2. **Watkins SMILE & SCRATCH** (Eat My Words) — Suggestive, Memorable, Imagery, Legs, Emotional; avoid SCRATCH pitfalls
3. **Igor Naming Guide** — Sound symbolism + positioning
4. **Marty Neumeier 7 criteria** (Zag) — Distinctive, Brief, Appropriate, Easy, Likable, Extendable, Protectable

Optional 5th:
5. **Donald Miller StoryBrand** — Name signals customer transformation

Each candidate displays:
- The name
- Framework attribution `[MAGIC]` / `[Watkins]` / `[Igor]` / `[Neumeier]` / `[StoryBrand]`
- Two-axis score: Cold-traffic /10 · Brand-trust /10
- One-line why

Default recommendation by audience sophistication (auto-detected from avatar):
- Premium / professional → Neumeier or Watkins default
- Mass-market / cold-funnel → MAGIC default

---

## Provenance tagging on all output

Every value-stack item, bonus, deliverable, content angle, and program component carries a tag:

| Tag | Meaning |
|-----|---------|
| `[confirmed]` | Coach has this today, can deliver |
| `[coach-to-build]` | Coach has agreed to build before launch, with rough effort estimate |
| `[suggested-optional]` | Skill suggested, coach has NOT yet committed |

**Default for any item without explicit coach confirmation: OMIT, don't invent.**

PSS scoring weights items by tag:
- `[confirmed]` → 100% weight
- `[coach-to-build]` → 50% weight (until built)
- `[suggested-optional]` → 0% weight (doesn't count unless accepted)

---

## Mid-intake gating questions

Before any section that requires specific deliverables (bonuses, guarantees, program components), the skill asks first:

> "Do you have [X] already? If yes, describe it. If no — do you want to build one before launch (rough effort estimate?), or skip it for this version?"

If coach says skip, the item is OMITTED — not added as `[suggested-optional]` unless coach asks for suggestions.

---

## Speed-to-launch bias

If a section is weak but adding to it would delay launch by weeks, the skill flags this in the PSS as:

> "You can launch now with a score of X, or invest [2 weeks] to lift score by [Y] points. Your call."

The coach decides. The skill never forces perfection over launch.
