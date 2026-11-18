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

**2.5. Offer the niche seed (default offer, explicit yes to spend).**
When setup saved a SocialCrawl key, offer the inspire pull BEFORE build #1: "Want me to study your
niche first? One pull (~cost named up front) shows what's already winning for coaches like you and
feeds every build after this for about a month. Skip it and we build from your pain map alone —
totally fine, you can run it later." Yes → route through `carousel-inspire` (its own credit gates
apply). No/no key → proceed; the first build runs on the pain map + bundled patterns, said plainly.
This is the ENGINE's step one, not every build's — one pull serves ~30 days.

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

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `carousel-superengine/reports/report-body.md` under the workspace folder: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text, slide copy).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin carousel-superengine --plugin-version 0.6.0 --skill carousel-guide --step '<setup or the first build>' --error-line '<the error line>' --summary '<headline>' --body-file carousel-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

The client never types any of these; you run them.
