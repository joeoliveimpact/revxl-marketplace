---
name: meta-ads-superengine:meta-ads-lead-questions
description: Writes the actual form or quiz question set that does the qualifying — the money-gate phrased to filter without scaring, commitment and timeline questions, and pre-call intel that arms the close, all in the coach's voice. Trigger phrases include "write my lead questions", "qualify questions", "instant form questions", "my quiz questions".
---

# meta-ads-lead-questions — the qualifying questions

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #9.
The production half of the funnel layer — the questions are their own copy
craft. They gate on the real money number and sound like the coach.

## Load
- shared refs + `vault-api.md`
- Active brand state → `funnel.qualification_gate`, `targets`, `setup.offer`, `setup.price`/`setup.backend_price`
- Voice: `~/.claude/revxl/<brand>/voc/` (voice-guide, voc-profile)

## Prereq (E0)
`funnel.qualification_gate` set. Missing → funnel-qualify.

## Steps

**1. Voice check (F10 if cold).** voc/ present → match register. voc/ absent
but `voice_sketch` present → reuse it (voice confidence: low, no re-interview).
Neither → offer capture (brand-brain if installed, else a 3-question inline
voice sketch; **write `voice_sketch` on capture**) and proceed **labeled
"voice confidence: low"** — never silently generic.

**2. Build the set:**
- **Money-gate (fork on the front-end price):**
  - **Paid front end** (`setup.price` > 0): phrased to filter-not-scare,
    anchored on what a client actually PAYS (`setup.price`, or
    `setup.backend_price` for a low-ticket front end); `targets` only tunes
    friction-vs-volume. Framed as fit, not interrogation.
  - **Free / $0 front end** (`setup.price == 0`): NO dollar figure at the free
    door ... a money question at a free opt-in kills the funnel it protects.
    Ask a soft readiness gate there instead (commitment, timing, fit ... "how
    ready are you to start?", "what's your timeline?"), in the coach's voice.
    Put the real money question DOWNSTREAM, where intent is already high: the
    application right before call booking (call funnels), or the checkout /
    sales page itself (no-call funnels ... the price there IS the money
    question). Anchor on `setup.backend_price`. Name that touchpoint in the
    artifact so the coach
    knows where it lands.
- **Commitment / timeline** — readiness to start.
- **Pre-call intel** — 1–2 questions whose answers arm the close (the
  specific struggle, what they've tried).
- Tune count to friction-vs-quality (fewer = more volume/lower quality).
- Mechanics: Instant Form (native, low friction) vs external quiz — recommend
  per the coach's stack and volume goal.

**3. Brain (1 search, optional).** Recipe = funnel-event / awareness: query
"lead qualification questions coaching", variants keyed to the gate.
Self-evidencing line; degrade F9.

**4. Write** the artifact (workspace naming convention); note path in
`funnel.spec_artifact` addendum.

## Terminal paths — inline blocks (routing.md grammar)

**Question set delivered (E7):** preamble names the artifact path, then:

**Next moves**
1. Wire the tracking — so these answers become the signal Meta optimizes on. Say: "set up tracking"  ← start here
2. Run the live policy gate early. Say: "compliance check"
3. *If voice was cold this run (F10):* build your brand brain so every future asset sounds like YOU. Say: "build my brand brain" *(if brand-brain installed; else the inline voice interview)*

## Teach mode
In `new`: plain-English-first — explain why a money question FILTERS rather
than scares when phrased as fit ("what this means for you: fewer leads, but
the ones who book can actually afford you"), gloss Instant Form (deep tier
not needed — one-liner) and the friction-vs-quality trade with small
numbers. In `learning`: gloss Instant Form first use. In `pro`: the set +
mechanics choice, terse.

## Guardrails
- Never invent the coach's proof or numbers into a question.
- The money-gate filters, it doesn't shame — a wrong tone here kills volume
  AND quality.
