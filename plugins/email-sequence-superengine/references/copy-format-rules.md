# Copy + Format Rules (all generators)

Apply to every email this plugin generates. Source: REVUP Email Nurture notebook + Ben Settle vault
(`output/research/Email Nurture - Vault + Notebook Synthesis - 06.17.26.md`).

## Copy rules
- **Write like you speak** — no marketing-speak. Polished reads "nobody's home" in the AI era; small imperfections read human.
- **Thumb-scroll format** — new sentence on its own line; paragraphs ≤2-3 sentences. For how LONG an email runs, see **Email length** below (measured from 2,220 real Ben Settle emails — not a guessed ceiling).
- **One-Action rule** — one next step per email; repeat the CTA up to 3x but always the same destination. The **primary CTA lives at the body close** — NOT the P.S. (in email the P.S. is largely skimmed as a pitch slot; Settle, vault).
- **No "no" questions** — never phrase so the reader can mentally disagree with the VALUE/pitch (builds defenses). EXCEPTION: deliberate permission-to-exit questions in no-show E3 ("is the timing off?") and winback sunset ("should I take you off?") — those graceful-out framings are the intended mechanic, not a leak.
- **80/20 value-to-pitch** — give before you ask. See Pitch floor below for how often you actually pitch.
- **P.S. (strategic, high-attention)** — one of the most-read lines in the email (REVUP notebook). Use it OFTEN (most emails, not forced on every), as a deliberate device — never as the primary CTA/ask (Settle: a pitch buried in the P.S. gets skimmed). P.S. playbook: recurring **subplot** / personal thread · **social proof** (a quick win or count) · **curiosity / open-loop** that pulls to the next email · **personality / hot take** · a **soft nudge** toward the body's CTA (re-state the door, don't make the P.S. carry the ask).
- **No em dashes** — use "..." for pauses (workspace standard).
- **No invented claims · NO false scarcity (honesty floor + FTC line).** NEVER fabricate scarcity, urgency, deadlines, "X spots/seats left," low-stock counts, countdowns, or ANY promo / offer / number / discount the coach hasn't explicitly approved as TRUE. Fake scarcity is a 2026 anti-pattern AND an FTC dark pattern (the FTC's *Bringing Dark Patterns to Light* names "false urgency claims" + "fake low-stock messages" as deceptive; NNG draws the line at whether the deadline/count reflects reality). It erodes trust ("Only 3 left!" with 3,000 in stock = a lie readers catch; LTV of a manipulated customer ≈ zero). Use scarcity/urgency ONLY when the coach confirms it's genuinely real; otherwise drive with the REAL cost of inaction, not manufactured pressure. If a campaign could use a deadline/limit, **SUGGEST it and ask the coach for the real number — never invent one.**
- **Objection reframe pattern: Acknowledge → Align → Reframe → Ask.**

## Email length — measured anchor, goal-indexed (NOT a flat ceiling)
**Empirical anchor (2,220 real Ben Settle emails, engaged daily list = warm's analog, body ≈ wc − ~20):** min ~60 · p25 ~300 · **median ~390** · p75 ~490 · p90 ~700 · p95 ~850 · max 10k+. Settle STAGGERS by purpose: a flat "<150" ceiling guts the workhorse email. Length is measured, varied, and goal-driven.

Three bands (body words): **punchy 150-200** (teaser, pitch-close, no-show, quick value) · **mid/workhorse 350-500** (daily value/story) · **long/earned 700-1000** (deep story — a minority; only when it needs the room + passes strip-the-CTA at length).

### Warm-nurture: goal-indexed mix (per 10 emails) — ask/infer the RUN'S GOAL first
| Goal | Mix (punchy / mid / long) | Lean |
|------|---------------------------|------|
| **Reactivate** (dormant re-warm) | 5 / 4 / 1 | short — rebuild the open habit + protect the inbox; the long is earned LATER, not on a cold list |
| **Nurture** (steady, evergreen) | 3 / 6 / 1 | balanced workhorse (the DEFAULT) |
| **Prime** (pre-launch belief / authority) | 2 / 4 / 4 | long — story persuades a warmed list |
| **Convert** (push to offer/booking) | escalate; closes punchy 120-200 | short at the ask |

Principle (constant across goals): **long is earned + a minority; mid carries the load; punchy keeps the rhythm.** **Stagger + space** — never run same-length emails back-to-back; spread the long + the punchy across the run. With `{{TEACH_MODE}}` on, teach the attention-span why (every extra paragraph sheds readers; long-form is a privilege you earn).

### Per-generator ranges (other campaigns — goal baked into the type)
| Generator | Body-word range |
|-----------|-----------------|
| launch | story/value 350-550; closes (D6/D7) **120-220** |
| precall (booked) | **150-300** per touch (E1 confirm may dip <150 — "you're booked, reply CONFIRMED") |
| precall-video | spoken **2-5 min** default (7 max if insisted; teach attention-span) ≈ 300-750 spoken words |
| post-call | E1 recap 150-250 · E2 case-study 350-550 · breakup short |
| onboarding | 200-400 (in-program; may run longer, HTML ok) |
| winback | D1 150-250 · sunset 80-150 |
| no-show | 60-120 (empathy = brief) |

**Sourced vs reasoned (honesty):** warm bands + the 350-500 workhorse = **measured** (Settle n=2,220). no-show "<4 sentences" = architecture research (sourced). Other rows = **reasoned** (trust + permission scale with length — you haven't earned 400 words from a cold/just-booked reader) — refine with live data.

## Pitch levels — the Soft-Pitch Gradient (canonical: ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md)
Five tiers by commitment asked: **none** (read/reply) · **breadcrumb** (point only: "more on YouTube," "I'm on IG" — no conversion) · **anticipation** (teaser: "keep an eye out, it's coming" — asks nothing now) · **soft** (real low-stakes ask: free signup, resource, throwaway/takeaway link) · **hard** (buy/apply/book; the close). The middle two ask for NO conversion — that's the tier to reach for when an email shouldn't sell but should still point somewhere. Settle: direct > loopy for the actual ask.

## Pitch floor (`{{PITCH_FLOOR}}` — set in setup)
The vault (Settle) says sell in EVERY marketing email; "good-will / no-sell emails destroy your box office." Honor the coach's chosen floor:
- **soft-floor (default)** — the SEQUENCE always carries a sell motion (~1 invite per 4). This does NOT mean a CTA on every email. A throwaway/soft link MAY ride under the entertainment on a value send, but it is OPTIONAL, never mandatory. Hard pitches only where the framework escalates (launch close, winback sunset).
- **value-first** — pure-value `none` emails freely allowed in nurture; sell less often. Softer brand, leaves money on the table per Settle.

**soft-floor ≠ "soft CTA on every email."** The 90/10 entertainment-to-offer rule governs (see ${CLAUDE_PLUGIN_ROOT}/references/story-engines.md): most sends entertain/teach with NO offer-ask. When unsure whether a value/story email needs a CTA → default to a reply-nudge or nothing, NOT a soft offer. Misreading soft-floor as "pitch every email" is the #1 drift in this plugin — do not.

### HARD NO-PITCH CONTEXTS (override BOTH floors — NO `soft` or `hard` ask; breadcrumb/anticipation pointers ARE allowed)
These bar a conversion ask (tiers soft + hard), NOT a no-ask pointer. A breadcrumb ("more on YouTube") or anticipation teaser ("the community's opening soon, watch your inbox") is fine and encouraged on these — it points without selling.
1. **First email back to a cold / dormant / reactivation list** — the re-intro / "help me build" send. Reply-ask + breadcrumb/anticipation only; NO soft offer (not even a free signup or throwaway link). Pitching send #1 to people who forgot they opted in = unsubscribes + spam complaints = burns the warm-up + deliverability. Earn the open before any conversion ask.
2. **Precall** (already booked) — selling hurts show-up.
3. **Onboarding** (already bought) — selling triggers buyer's remorse.
4. **Permission-to-exit** sends (no-show E3, winback sunset) — the graceful-out is the mechanic, not a leak.

## Format mode (per-sequence, explained in the output)
- **text-only = HARD default** for cold + all nurture/launch-to-cold. Lands in the primary tab, trips fewer spam filters, reads personal. Explain this to the coach in the package.
- **richer HTML allowed only once the contact is in-program** (engaged opener/replier; reputation cushion exists) — onboarding + engaged-segment sends.
- Precall: E1/E3/E4 text-only; E2 light-HTML allowed.

## Deliverability (one-liner)
Tech layer (dedicated IP + SPF/DKIM/DMARC + warm-up) and content layer (engagement, reply-worthy email) are ADDITIVE. Spam complaints fall toward zero when readers want the email. Replies + curiosity ARE a deliverability mechanism.

## Reply routing (GHL)
- **Default = keep replies in GHL Conversations** → enables tag/workflow automation. Recommended.
- **Do NOT set an external reply-to** — it routes replies away from Conversations.
- **Do NOT reply from an outside inbox** — breaks the reply route (won't sync back). Forwarding/BCC only work with Mailgun + LC Email.
- Setup asks: GHL Conversations (default) vs external inbox (warn: breaks GHL automation).
