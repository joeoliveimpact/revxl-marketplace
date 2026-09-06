---
name: email-sequence-superengine:email-add-stories
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

**Brain pull via `revxl-vault-search` ... structure check before you write the bank.** Fires
once the coach's answers are captured and before a single entry is written. Wiring per
${CLAUDE_PLUGIN_ROOT}/references/vault-api.md. **Check `<project>/brain-pulls/` first**
... a cached pull means no call, and the evidence line reads `skipped (cached)`. No cache:
ONE invocation of `workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=email-sequence-superengine spoke=email-reference-library
question: story-driven email structure ... angles: which everyday story types carry an
email; where the open loop sits; the turn from story to lesson`.
You are looking at successful marketing emails. Look for structure, framework, sequence
shape, subject-line pattern, open and close moves, and ideas. Never reproduce a line of
a source email. The client's voice comes from brand-brain, the structure from the Brain.
Use what comes back as STRUCTURE only ... it tags each entry with the engine and shape it
fits and tells you which thin answer is worth one more probe; it never supplies story
content, and nothing from the Brain is ever written into the bank as if the coach said
it. Cite `[brain] <path>` and save the pull to `<project>/brain-pulls/story-intake.md` (a story intake has no campaign, so the slug is fixed and the pull is reused across intakes).
When you confirm what you captured, print exactly one line: `Brain: [brain] <path>
woven` or `Brain: skipped (no key / cached / degraded / budget)`.
`med` is 1 search + up to 2 note reads, and this step fires no second pull, so it spends
1 search + up to 2 reads against the cap of at most 2 searches + 3 note reads per named
step.
No key / workspace-superengine missing / any failure ... degrade per the wiring doc,
print `Brain: skipped (degraded)`, and keep going. The Brain never blocks a story intake.

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
