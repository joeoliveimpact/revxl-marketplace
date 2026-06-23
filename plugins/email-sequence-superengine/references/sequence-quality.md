# Sequence Quality Gate

Run before delivering any sequence. Mark each PASS / FLAG. Any FLAG → fix and re-check before delivery.

## Voice + specificity (the two that killed the last build)
- [ ] **Voice match** — reads like THIS coach (cadence, vocabulary, signature phrases from the anchor), not generic.
- [ ] **Non-generic via avatar pain, NOT individual data** — every email names a specific shared pain/objection from the avatar config, in the coach's words, so it feels written-for-me to anyone in the niche. If it reads like a bland template → FLAG.
- [ ] **Broadcast-safe** — NO individual-prospect facts (no specific names, numbers, or events only one prospect would have). Personalization is merge tokens only (`{{contact.first_name}}`). If an email only fits one person → FLAG (this is a set sequence sent to everyone).

## Precall guardrails
- [ ] **One pre-call action max** — no excessive homework (scorecard OR workbook, kept light).
- [ ] **Active confirmation reply present in E1** (reply CONFIRMED — micro-commitment + engagement signal).
- [ ] **Format mode correct** — E1/E3/E4 text-only; E2 light-HTML allowed.
- [ ] **Pre-emptive objection strike present** (E2 or E3) — biggest objection named + dissolved before the call.

## Storytelling (warm-nurture + any story-driven email: launch case/origin, precall E2)
- [ ] **Stories are REAL** — sourced from the story-bank (${CLAUDE_PLUGIN_ROOT}/references/story-bank.md) / story-intake, not invented. If you see fabricated "a coach I worked with..." filler → FLAG, replace with a banked story or run intake.
- [ ] **Earn-the-open test** — strip the CTA: is the email still worth reading? If no → FLAG (it's an ad in banter).
- [ ] **90/10 + offer concentration** — most sends entertain with light/zero offer-ask; the offer concentrates on the ~1-in-4 invite. Not every email pitches the program.
- [ ] **Runs a story engine** (Story Selling / Analogy-Seinfeld / HSO·HIPS·PAS) — NOT a generic tips/bullet newsletter. If it reads like tips → FLAG, rewrite as story.
- [ ] **Rotation** — engine + storyline vary across the sequence/weeks; no two sends the same shape.
- [ ] **Open loop chained** where multi-send (end teasing a named next; resolve + reopen).
- [ ] **P.S. subplot thread** present (separate personal narrative in the P.S., not the CTA).
- [ ] **Blunt seam** — story hard-pivots to one CTA, no subtle fade.

## CTA + pitch
- [ ] **CTA matches a pattern** in ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md and fits the email's framework row (pattern # + pitch level).
- [ ] **HARD NO-PITCH CONTEXTS respected (overrides `{{PITCH_FLOOR}}`)** — these carry NO `soft` or `hard` ask (no free signup, resource, throwaway link, buy/apply/book). Breadcrumb + anticipation pointers ("more on YouTube," "community's coming") ARE allowed and encouraged. If a SOFT-OFFER or HARD CTA appears on one → FLAG and strip it (downgrade to a pointer or remove):
  - **First email back to a cold / dormant / reactivation list** (the re-intro / "help me build" send) — reply-ask + breadcrumb/anticipation only. Pitching an offer on send #1 to people who forgot they opted in = unsubscribes + spam complaints = burns deliverability.
  - **Precall** (already booked) and **onboarding** (already bought) — selling hurts show-up / buyer's remorse.
  - **Permission-to-exit** sends (no-show E3, winback sunset) — the graceful-out IS the mechanic.
- [ ] **Soft-Pitch Gradient applied** — each email's CTA tier (none / breadcrumb / anticipation / soft / hard, per ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md) fits its role; pointers/teasers used instead of a soft offer where the email shouldn't sell but should still point somewhere.
- [ ] **`{{PITCH_FLOOR}}` understood correctly** — soft-floor means the SEQUENCE always has a sell motion (~1 invite per 4), NOT a CTA bolted onto every email. A pure-value/entertainment send inside the 90/10 MAY end with just a reply-nudge or nothing. A throwaway link is OPTIONAL, never mandatory. **When unsure on a value/story email → default to reply-nudge or nothing, NOT a soft offer.** value-first = pure-`none` value emails freely allowed.
- [ ] **Pitch matches the framework row** for emails that DO carry an ask.
- [ ] **Primary CTA at the body close**, not buried in the P.S.
- [ ] **80/20 held across the sequence** — value outweighs pitch; not every email is a hard ask, and most carry NO ask at all.
- [ ] **No fabricated scarcity / urgency / promos / numbers** — zero "X spots left," countdowns, fake deadlines, or any offer/discount/count the coach hasn't confirmed as REAL (FTC dark pattern + 2026 anti-pattern). Any scarcity present is coach-confirmed true, or it's CUT. → FLAG + strip if invented.
- [ ] **Subjects + offer specifics presented as SUGGESTIONS** — 2-3 subject options per email; scarcity/deadline/price/promo marked `[SUGGESTED — confirm]`, never asserted as final.

## Copy rules
- [ ] **Length fits the goal-indexed profile** (see ${CLAUDE_PLUGIN_ROOT}/references/copy-format-rules.md → Email length) — warm: the mix matches the RUN'S GOAL (Reactivate 5/4/1 · Nurture 3/6/1 · Prime 2/4/4 · Convert punchy closes); other campaigns within their per-type range. Long-form (700-1000) only where the story earns it. **Stagger + spacing held** — no same-length emails back-to-back; long + punchy spread across the run. (Anchor: measured from 2,220 Settle emails — median body ~390 — NOT a guessed <150 ceiling.)
- [ ] Thumb-scroll format — one sentence per line, short paras.
- [ ] One-Action CTA — single destination, repeated ≤3x.
- [ ] No "no" questions.
- [ ] P.S. used strategically on most emails (subplot / proof / curiosity / personality / soft nudge) — never carrying the primary CTA/ask.
- [ ] **No em dashes** — "..." used for pauses.

## Routing + safety
- [ ] Reply-routing note correct (GHL Conversations default; no external reply-to).
- [ ] **Draft only** — nothing sent to live contacts; GHL push (if used) stages templates only, never assigns a workflow.
