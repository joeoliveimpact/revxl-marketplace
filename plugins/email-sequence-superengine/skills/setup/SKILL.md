---
name: email-sequence-superengine:setup
description: First-run wizard for the email sequence engine. Captures brand voice, program, avatar pains and objections, offer, sender domains, reply routing, ESP, pitch floor, and voice edge into the business config every generator reads. Trigger phrases include "set up email sequences", "configure the email engine", "email setup", "reconfigure my email config".
---

# Task: setup

First-run wizard. Capture config, write to business-config (persisted via `${CLAUDE_PLUGIN_DATA}`).

## Load
${CLAUDE_PLUGIN_ROOT}/references/business-config.md

## Ask + write each key
Ask conversationally, per `{{EXPLANATION_LEVEL}}`. Push for CONCRETE phrasing in the coach's words, not categories
("their reach died and sales dried up post-2022," not "marketing struggles"). These inputs are the conversion
engine — proven required ingredients (Hormozi + Settle), not nice-to-haves.

**A. Tone + brand**
1. **Explanation level** — beginner / intermediate / advanced (default beginner). How much jargon I translate.
1b. **Teach mode** — on (default) / off. Plain: "Teach mode means as I build, I'll explain WHY each move works in simple terms, so you learn to do this yourself, not just get the emails. Teaching you to fish. Want it on?" Toggle anytime. (See ${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md.)
2. **Program + positioning + audience** — who they serve, one-line positioning.
3. **Coach POV / hot takes** — strongest contrarian opinions vs mainstream advice in their niche (feeds POV emails + story-bank).
4. **Brand voice / anchor** — path to a voice guide if one exists, else note interim anchor sources. Detect-if-exists first.

**B. Avatar deep (the conversion engine)**
5. **Dream outcome in STATUS terms** — not just "what they want," but how they want peers/spouse/industry to SEE them (status > money).
6. **Real pain vs polite pain** — the visceral/shameful truth, not the public version. Probe the 3 levels: External (surface problem) / Internal (how it feels) / Philosophical (why it's just plain WRONG they deal with it).
7. **Top shared pains** — 3-5, in their words (broadcast specificity engine).
8. **The enemy** — named villain the avatar already resents (a method, a guru type, an industry norm). Powers Us-vs-Them.
9. **What they've tried + why they think it failed for THEM** — the "won't work for me" belief (the deepest objection).
10. **Objections mapped to the 4 fears** — Self (do I have the capacity) / You (can you really help / are you legit) / Unknown (fear of change) / History (burned before). Also capture the DIY objection ("why not just YouTube/AI it") + the Spouse/partner objection.
11. **List awareness** — problem-aware / solution-aware / product-aware (shapes hooks).
12. **(optional) Nightmare avatar** — who they do NOT want (repulsion criteria for disqualification).

**C. Offer deep**
13. **Offer framing** — how it's described (NO price — coach supplies live).
14. **Mechanism + discovery** — the specific vehicle/"how," and how the coach found/built it (sell the vacation, not the plane).
15. **Contrarian frame** — "everything you've been taught about X is wrong because ___" (point of difference).
16. **Proof assets** — specific client results WITH numbers.
17. **Micro-wins** — quick wins to give in E1/E2 (2-min reset, cheat sheet) for instant competence.
18. **Cost of inaction** — what staying stuck 6-12 months costs them ($/exhaustion/missed opportunity).
19. **Drop-off point** — where clients historically hit the valley of despair (e.g. day 10-14) → onboarding momentum-save.
20. **(optional) Segments** — 2-3 self-select pathways at the gate (for routing).

**D. Delivery / system**
21. **Sender domains** — sending domain(s); subdomain split for cold vs in-program if relevant.
22. **ESP** — ghl (default) / activecampaign / klaviyo / kit / mailchimp / none-export. Detect connection; route auto-push vs export.
23. **Reply routing** — GHL Conversations (default) vs external. **Warn:** external breaks GHL automation + the reply route.
24. **Pitch floor** — soft-floor (default) vs value-first. Plain: soft-floor = every marketing email leaves a soft "door's open" CTA (revenue-backed Settle default, NOT salesy — hard pitches only at launch close / sunset); value-first = some pure-value emails, no ask. Precall + onboarding stay no-pitch either way.
25. **GHL push** — on/off. Off by default (opt-in, approval-gated).
26. **Output destination** — workspace file / GHL / export.

> This is long. For beginners, OFFER to do it in 2 passes (essentials now: 1-2,5,7,10,13,21-26; the deeper avatar/offer fields next session). Don't force all 26 in one sitting — but flag that the deep fields are what make the copy convert.

## Finish
- Write all values into business-config.
- Confirm back to the coach in plain English (per explanation level).
- Offer to build the first sequence (route to precall-nurture) or the guided tour (guide).
