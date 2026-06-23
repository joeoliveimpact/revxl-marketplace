# Onboarding Framework — 5-Email 30-Day New-Client Sequence

Source: Email Nurture Architecture Research (Type 9). Broadcast: built once, fires on payment+signature.
In-program audience → richer HTML allowed. Specificity from coach voice + avatar pains, never individual facts.

**Objective:** kill buyer's remorse, capture intake, set boundaries, build kickoff momentum.
**Trigger:** client signs agreement + completes initial payment (tag `client-onboarding`).
**Cadence:** 5 emails over the first 30 days. Format: HTML allowed (in-program; reputation cushion exists); keep personal.

| # | Send | Purpose | Lever | Subject angle | CTA |
|---|------|---------|-------|---------------|-----|
| 1 | immediately | welcome + portal access | Instant Gratification | "welcome to the team" + receipt/login | log in + book kickoff |
| 2 | D2 | deep intake form | Skin in the Game | "action required: your intake" (timeline) | complete intake |
| 3 | D7 | rules of engagement | Boundary Setting | "how we work together" (channels, response times, cancel policy) | reply "AGREED" |
| 4 | D14 | week-2 check-in | Momentum | "your 14-day momentum check" + a guide | access the guide |
| 5 | D30 | month-1 retention audit | Feedback Loops | "quick question about your first 30 days" | reply |

**Pitch + CTA per email** (see ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md): E1 `none` — portal login + book kickoff (5+7) · E2 `none` — apply/intake (9) · E3 `none` — reply AGREED (1) · E4 `none` — resource (4) · E5 `none` — reply (1). **No-pitch under BOTH floors — they already bought; this is retention, not selling.**

**Story dose: LIGHT** (see ${CLAUDE_PLUGIN_ROOT}/references/story-engines.md). E4 (week-2 momentum) carries a short relatable story — "week 2 is where people drift" — to normalize the dip; E1 welcome can open with a brief human beat. E2/E3 stay operational (intake, ROE). Don't story the admin emails.

**Levers:** Skin in the Game (D2 intake deepens commitment); Boundary Setting (prevents scope creep/burnout).
**Mistakes to avoid:** info overload on day 1; no comms rules (late-night messages → coach burnout).
**Benchmarks:** open 90-100%; intake completion 90%+; feedback response 45-55%.
**Deliverability note:** onboarding belongs on the TRANSACTIONAL subdomain (client-critical), separate from marketing sends.
