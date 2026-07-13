---
name: carousel-superengine:carousel-guide
description: Plain-English first-run tour of the carousel engine. Orients a brand-new user, runs setup, then builds their first carousel with hand-holding. Trigger phrases include "walk me through it", "carousel guide", "how does the carousel engine work", "I'm new to this".
---

# Task: guide

Hand-held first run. Assume zero context and `{{EXPLANATION_LEVEL}}: beginner` until told otherwise.

## Flow

**1. Orient (60 seconds, no jargon).**
Say what this does in plain words: "You tell me a topic or paste a carousel link you liked. I build the whole post: what each slide says, how each slide should look, the caption, the hashtags... and then I can make the actual slide images too. Nothing posts automatically... you always see drafts first."

Name the two ways in:
- **Create** — "give me a topic, I build the carousel."
- **Teardown** — "paste a link to a carousel that's working, I break down why, then rebuild it as YOURS... your voice, your clients' pains, your CTA. Structure is borrowed; content never is."

**2. Run setup.**
Route through the `carousel-setup` skill, essentials pass only (level, teach mode, brand, voice, pains, platform, CTA destination, output). Tell them the deeper questions come later and why they matter.

**3. Build the first carousel together.**
Ask for one thing their ideal client complains about constantly, in the client's words. Then run the `carousel-create` skill on it with TEACH MODE ON regardless of config... narrate why the hook was chosen, why the slides sit in this order, why the CTA slide asks for exactly one action.

**4. Close the loop.**
Show where the config lives (`${CLAUDE_PLUGIN_DATA}/business-config.md` — the persisted copy every
build reads; the file in the plugin's references folder is only the blank template), how to change
voice edge / teach mode / platform anytime, and the
fastest next actions. Then offer the natural nexts (never block):
- **"Want the actual images for this one?"** → the `carousel-render` skill — "make the images"
  (plain: "I turn the draft into finished slides you can post")
- Next topic → the `carousel-create` skill — "carousel about ___"
- **"See a carousel you loved lately?"** → the `carousel-teardown` skill — paste the link

## Rules
- Never dump the full command table on a beginner; introduce commands as they're needed.
- One question at a time during setup.
- The first carousel should ship in the same sitting... momentum beats completeness (the deep avatar fields can wait).
