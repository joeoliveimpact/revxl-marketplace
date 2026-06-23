# Precall Framework — 4-Touch Strategy-Call Show-Up Sequence

Distilled from `output/research/Email Nurture Architecture - Research - 06.17.26.md` (Gemini Type 1)
+ `output/research/Email Nurture - Vault + Notebook Synthesis - 06.17.26.md` (Orchestrating Trust upgrades).
This is the STRUCTURE the `email-show-up-sequence` generator fills in the coach's voice. Not swipe copy.

**Goal:** strategy-call show-up >80%, establish authority, pre-handle objections.
**Trigger:** prospect books a strategy / triage / discovery call.
**Output:** 4-email sequence package.

## The 4 emails

| # | Send | Purpose | Lever | Subject angle | CTA |
|---|------|---------|-------|---------------|-----|
| 1 | immediately | confirm + micro-commitment | Commitment/Consistency | "Confirmed: [call] details" | sync cal + reply CONFIRMED |
| 2 | 24h before | method differentiator | Authority/Contrast | name the common mistake | read the breakdown |
| 3 | 4h before | boundary + qualification | Scarcity/Boundary | "Please read before today's call" | complete pre-call workbook |
| 4 | 1h before | tech + access | Hyper-accessibility | "[Call] starting in 60 min" | join waiting room |

**Pitch + CTA per email** (see ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md): E1 `none` — reply-trigger + cal-sync (1+2) · E2 `none` — open-loop read (3) · E3 `none` — resource/pre-work (4) · E4 `none` — access/join link. Precall stays no-pitch under BOTH pitch floors (they already booked; selling hurts show-up).

**Story dose: LIGHT** (see ${CLAUDE_PLUGIN_ROOT}/references/story-engines.md). E2 (method differentiator) carries a micro-story — the common mistake told as a quick scene, blunt seam to the lesson. E1/E3/E4 stay functional (confirm, boundary, access). Don't story the reminders.

## Upgrades (beat the generic version — from Orchestrating Trust notebook)

1. **Diagnostic Bridge** — replace the static workbook in E3 with a 10-15 question interactive scorecard pre-work. Why: 97.2% show vs 36.2% (Hawthorne effect — the prospect invests, so they show).
2. **Transfer-of-Trust video** — in E2 (or E1), reference a short founder/coach video intro that edifies the closer before the call. Why: borrows the coach's authority onto the call-taker; warms the relationship.
3. **Pre-emptive objection strike** — in E2 or E3, name and dissolve the biggest objection before the call ("Why 'Not Now' is the most expensive decision"). Why: removes the objection from the live call where it costs the close.
4. **Blameless missed-visit rebook** — if E4's call is missed, the follow-up rebooks within 24h with zero shame framing. Why: reclaims >30% of no-shows. (Lives in `email-no-show-sequence` later; flag the hook in E4.)

## Guardrails (baked into the generator)

- **No excessive homework** — one pre-call action max (the scorecard/workbook), kept light.
- **Enforce an active confirmation reply** in E1 (reply CONFIRMED) — micro-commitment + engagement signal + deliverability.
- **Format mode per email:** E1/E3/E4 = text-only (HARD default — lands in primary tab, reads personal). E2 = light-HTML allowed (the method breakdown can carry a little structure), still plain-first.

## Companion touchpoints (NOT built as channels in v1)

Email is the spine. SMS, LinkedIn voice note, and the scorecard tool are optional companions the coach wires into GHL manually (7-11-4 rule, speed-to-lead <5 min). Flag them in the sequence package as "optional — wire in GHL", do not generate them as channels.
