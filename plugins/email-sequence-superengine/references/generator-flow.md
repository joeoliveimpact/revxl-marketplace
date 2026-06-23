# Shared Generator Flow (all campaign types)

Every generator skill follows this. The only thing that changes per skill is which campaign framework
it loads. Keeps the 8 generators consistent and DRY.

## Always load
${CLAUDE_PLUGIN_ROOT}/references/business-config.md · ${CLAUDE_PLUGIN_ROOT}/references/copy-format-rules.md · ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md ·
${CLAUDE_PLUGIN_ROOT}/references/psych-reuse.md · ${CLAUDE_PLUGIN_ROOT}/references/voice-anchor.md · ${CLAUDE_PLUGIN_ROOT}/templates/sequence-package.md · ${CLAUDE_PLUGIN_ROOT}/references/sequence-quality.md
PLUS the campaign framework named by the calling skill (e.g. ${CLAUDE_PLUGIN_ROOT}/references/launch-framework.md).

## The non-generic rule (every campaign)
These are BROADCAST sequences: built once at setup, fired to everyone who hits the trigger. There is
NO per-prospect input at send time. "Feels personal" comes from THREE things, never individual facts:
1. **Coach voice** — from the voice anchor (cadence, vocabulary, signature phrases).
2. **Avatar shared pains + objections** — from config; name them sharply in the coach's words.
3. **Merge tokens** — `{{contact.first_name}}`, `{{appointment.meeting_url}}`, etc. for the light touch.
Never write a fact that only fits one prospect.

## Flow
1. **Read business-config** — voice anchor, program, OFFER, AVATAR (pains + objections), output destination, GHL push flag, explanation level. If voice/avatar are placeholders → route to `setup` first.
2. **Load the campaign framework + voice anchor** — the email table, cadence, levers, mistakes-to-avoid, benchmarks for THIS campaign; plus the coach's voice.
3. **Generate the emails** into ${CLAUDE_PLUGIN_ROOT}/templates/sequence-package.md — per email: subject (hook-type) + preview + body (PAS/HSO/two-line) + send timing + GHL trigger spec + benchmark-to-watch + **CTA (pattern # from cta-patterns.md) at the email's framework pitch level**. Speak to the avatar's shared situation in the coach's voice. Merge tokens, not individual facts. Apply each email's lever + format-mode + copy rules. Honor `{{PITCH_FLOOR}}` (soft-floor → no pure-`none` marketing emails; precall/onboarding excepted). Primary CTA at the body close, not the P.S. Avoid the campaign's listed mistakes.
4. **Run ${CLAUDE_PLUGIN_ROOT}/references/sequence-quality.md.** Any FLAG → fix and re-check.
5. **Review/approve** — show the coach; honor edits.
6. **Deliver** to `{{OUTPUT_DESTINATION}}` as a draft.
7. **Optional GHL push** — only if `{{GHL_PUSH}}` = on AND the coach approves → ${CLAUDE_PLUGIN_ROOT}/references/ghl-push.md. Stage templates only; never assign a workflow, never send live.

## Format mode (per campaign framework)
text-only HARD default for cold + nurture/launch-to-cold; richer HTML only for in-program sends
(onboarding, engaged segments). Each framework states its own mix.

## Teach mode (when `{{TEACH_MODE}}` = on)
As you build, add a short plain "why this works" note per email/section (the story engine used, the pitch level,
the CTA pattern, the P.S. role, why the avatar pain is named) — 8th-grade language, teach to fish. See
${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md. When off, just build.

## Subjects + offer specifics = SUGGEST, don't assume (Intent Clarification)
**Subject lines are SUGGESTIONS.** For each email, offer 2-3 subject options (different hook angles) for the coach to pick/tweak — never assert one as final. Same for ANY offer specific: scarcity, deadlines, seat/spot counts, prices, discounts, promo names, bonus stacks. Do NOT bake an unapproved promo or number into the copy — propose it, mark it `[SUGGESTED — confirm]`, and let the coach approve or supply the real value. Inventing an offer the coach didn't sign off on (esp. fake scarcity) is the failure mode to avoid.

## Guardrails (all campaigns)
Draft only. No individual-prospect facts. **No invented scarcity/urgency/promos/numbers — coach-confirmed REAL only (see copy-format-rules honesty floor / FTC line).** Subjects + offer specifics are suggested for approval, never assumed. Explanation level per `{{EXPLANATION_LEVEL}}`. Teach mode per `{{TEACH_MODE}}`. No em dashes ("..." for pauses).
