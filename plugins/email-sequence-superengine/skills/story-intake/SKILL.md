---
name: email-sequence-superengine:story-intake
description: Quick Q&A that captures the coach's REAL stories into the story-bank, the well every story-driven email pulls from (never invents). Trigger phrases include "add my stories", "story intake", "capture my stories", "my emails need more stories".
---

# Task: story-intake (the antenna Q&A)

Flip the script: instead of inventing stories, INTERVIEW the coach for real ones, then the generators write
the proven framework around real raw material. Authenticity inside the framework. Source for all story-driven
emails (warm, launch, post-call, precall-video, precall E2).

## When this runs
- Standalone: coach says "add stories / story intake / feed me questions."
- Auto: a story-driven generator finds the story-bank empty/thin/stale → runs a quick intake first.
- Top-up: a 2-3 question mini-pass when the bank just needs fresh material.

## How to run it (conversational, ONE question at a time)
Ask like a curious friend, not a form. Capture answers RAW — don't polish, don't make it sound marketingy.
Messy/real is the point. After each answer, optionally probe once ("what did they actually say?", "what
happened right before that?"). Keep it quick: full pass ~7 Qs, mini pass ~3.

### Tone: ask like a friend, not a marketer
The best email stories are PERSONAL and mundane (the Benihana chef, the bar fight, the divorce) — not "5 client wins." Lead with everyday-life questions; business stuff comes second. Keep it loose and human.

### Memory-jog tricks (offer these — they unlock real material)
- "Check your texts to friends from this week — what'd you actually talk about / complain about / laugh at?" (texts to friends ARE the target voice + a story goldmine)
- "Scroll your camera roll — any photo with a story behind it?"
- "What did you tell someone about over dinner?"

### The questions (each maps to a story engine / storyline)
**Everyday life (lead here):**
1. **This weekend** — what'd you actually do? Anything fun, weird, or annoying? *(→ Seinfeld/Analogy)*
2. **Tell-your-friends** — anything crazy happen out in the real world you'd text a friend about? (check your texts) *(→ Story Selling/Seinfeld)*
3. **Small moment** — something tiny that stuck with you? (gym, coffee, your kid, traffic, a stranger) *(→ Analogy/Seinfeld)*
**Then the business angles (lighter):**
4. **The Wall (origin)** — take me to the exact moment your old approach failed. WHERE were you, what were you looking at, how did it feel? (in media res, not a timeline) *(→ Loss & Redemption)*
5. **The epiphany** — the moment you realized the traditional way was a lie and stumbled on your fix? *(→ Amazing Discovery)*
6. **Recent flaw/fail** — an embarrassing mistake or failure lately (even funny)? Polished = "nobody home"; the flaw builds trust. *(→ Vulnerability / Attractive Character)*
7. **"Tried everything" client** — a client who thought they were too far gone... what was their turning point, and what did they SAY? (not a flat testimonial) *(→ Third-Person Proof)*
8. **Hidden benefit** — a secondary win clients get that has nothing to do with the curriculum (present at dinner, not checking email)? *(→ desire/identity)*
9. **What pisses you off / hot take** — something lazy or dishonest in your space, or a belief you repeat that others fight you on? *(→ Us-vs-Them / POV)*

Don't force all 9. A couple of good real everyday stories beat nine thin business ones.

## What makes a story USABLE (probe for these)
- **Heaven & hell / extreme** — the more painful, humiliating, triumphant, the more readable. Don't sand it down.
- **Specific sensory detail** — the £11.42 in the bank, the 11:42 PM, the room. Vague = forgettable.
- **Before & after the moment** — what happened right BEFORE the low point and right AFTER. That's the arc.
- **Scar-as-credential** — the failure/loss is now proof, not shame.
- If an answer is thin, probe ONCE: "what happened right before that?" / "what did they actually say?" / "where were you sitting?"

## Write to the story-bank
For each answer, append an entry to the story-bank (see ${CLAUDE_PLUGIN_ROOT}/references/story-bank.md):
- the RAW story (verbatim-ish, the coach's words/details)
- date captured
- engine/storyline tag(s) it fits
- status: `fresh` (unused)
Confirm what you captured in plain English. Tell the coach they can add more anytime ("got another story? just tell me").

## Guardrails
- NEVER fabricate or embellish into the bank. Only what the coach actually said. If they give nothing, the bank stays empty and generators must flag thin-input (not invent).
- Real names/numbers in the bank are fine for the coach's OWN use, but generators keep OUTPUT broadcast-safe (merge tokens, archetype any client unless the coach approves naming).
- Persist the bank via `${CLAUDE_PLUGIN_DATA}` (survives plugin updates).
- Later: the voice-matching + VoC skill can auto-seed this bank by mining the coach's own calls/content. For now it's Q&A-fed.
