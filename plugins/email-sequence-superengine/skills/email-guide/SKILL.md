---
name: email-sequence-superengine:email-guide
description: Plain-English first-run tour of the email sequence engine. Orients new users, runs setup, and builds the first sequence with hand-holding. Use for first-timers or anyone who says help / I'm new / walk me through. Trigger phrases include "guide me through email sequences", "first time", "walk me through the email engine".
---

# Task: guide

Plain-English first-run tour. Beginner mode by default — hand-hold through setup + the first sequence.

## Load
${CLAUDE_PLUGIN_ROOT}/references/business-config.md
the `email-setup` skill
the `email-show-up-sequence` skill

## Flow
1. **Orient** — in plain English: "I build the emails that get a booked prospect to actually show up to your call, written in your voice. We'll set things up once, then build your first sequence." Name any technical term with a one-line gloss; add a "what this means for you" line where the consequence isn't obvious.
2. **Run setup** — walk through the `email-setup` skill one question at a time, explaining why each matters (especially reply routing and format-mode — the two that affect deliverability).
3. **Build the first sequence** — start with the `email-show-up-sequence` skill (simplest, highest-impact). Remind them this is ONE set of emails that fires to everyone who books, built from their voice + avatar pains (not per-prospect). Mention the other 7 generators exist for when they're ready (`email-launch-promo-sequence`, `email-warm-nurture-sequence`, `email-no-show-sequence`, `email-follow-up-sequence`, `email-winback-sequence`, `email-onboarding-sequence`, `email-presell-video`). Explain each email's job as you go.
4. **Show the quality gate** — explain what the checklist caught and why it matters (especially broadcast-safe: no individual facts).
5. **Hand off** — tell them how to rebuild/tweak it later (`email-show-up-sequence`) and how to change explanation level ("set level to intermediate/advanced").
