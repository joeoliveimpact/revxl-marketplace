---
name: stories-superengine:stories-guide-set
description: "Build a multi-frame Instagram/Facebook story set: one that sells a lead magnet and ends on 'reply KEYWORD', or one that turns the coach's own words into frames. Copy from the guide or the coach, photos placed so text never covers a face, frames rendered and checked, contact sheet approved, then handed to scheduling. Trigger phrases include \"story set for my guide\", \"stories for my freebie\", \"make stories for tomorrow\", \"turn this into a story\", \"story that says reply\"."
---

> **Compaction guard:** if this conversation was compacted since this skill loaded, invoke it again.
> Resume from the story folder: `story.json` present = copy is locked; `frame-*.png` present = rendered.

**Output contract** — one folder per set in the workspace: `stories/<SET NAME> <MM.DD.YY>/` (the POST date)
- `copy.md`: the source, the options shown, the coach's final words
- photo files used, copied in
- `story.json` (schema: `${CLAUDE_PLUGIN_ROOT}/references/frame-spec.md`)
- `frame-1.png` … `frame-N.png` (1080×1920) and `_contact-sheet.png`
Nothing posts from this skill. Approved frames go to `stories-schedule`.

## Load
- `${CLAUDE_PLUGIN_DATA}/business-config.md` (no file, or placeholders → `stories-setup` first)
- `${CLAUDE_PLUGIN_ROOT}/references/story-craft.md` (the method; follow it)
- `${CLAUDE_PLUGIN_ROOT}/references/frame-spec.md` (story.json fields, colors, checks)
- Voice: `~/.claude/revxl/<brand>/voc/voice-guide.md` when it exists

Scripts run with the recorded Python (see `stories-setup`, "Run a script").

## Steps

**1. Pin the job (one question at a time, only what's missing).**
- Which set: a lead magnet from `{{LEAD_MAGNETS}}`, or the coach's own words?
- When it goes out: a date + time, default tomorrow at `{{DEFAULT_POST_TIME}}` in `{{TIMEZONE}}`.
  Before planning, read what's already scheduled that day (`stories-schedule`, readback). Something
  already at that time → tell the coach what's there and ask: different time, or go anyway.
- State the Definition of Done back: "N frames, your words, you see them before anything schedules."

**2. Read the source.** For a guide, get the file (the path in `{{LEAD_MAGNETS}}`, a Drive link or a
paste) and read all of it. Pull: the promise, who it's for, what's inside, the best lines in the
coach's own words, and the reply keyword. If the coach already runs posts for this guide, read them
and keep the story's keyword the same as theirs.

**3. Copy.** Two paths:
- **The coach writes it** (often the best result): take their words exactly.
- **Options from the guide:** 3–4 directions, each a different angle (reframe, pain, test, identity),
  every line lifted from the guide. Ask with the AskUserQuestion tool; put each option's full wording in the option's `description`
  (` / ` between lines, ` · ` between frames), never only in a preview pane.

Then give **numbered suggestions** on the final words, each one they can accept or skip: a missing
"reply KEYWORD" frame, a bridge line that makes the keyword make sense, spelling, the frame split,
photo pairing, anything the render check will trip on (emoji, very long lines). Suggestions are
about whether the story works, never about their voice. Write the final words to `copy.md`.

**4. Split into frames.** One beat per frame, about 25 words max, the ask frame last. Show the split
as a table (frame · words · background) before rendering.

**5. Photos.** Coach's own photos first (ask, or use ones they've shared before). For each photo
frame, look at the image and place the text in open space: sky, wall, car hood, never a face. Set
`position` (`top` / `bottom`) and `focus` to keep faces clear. Generated images are fine for organic
stories; note them so the AI label is set when scheduling. Copy each photo into the set folder.

**6. Write `story.json`.** One `style` for the whole set (`{{STORY_STYLE}}`). Photo frames: white
then black solid bubbles. Plain-black frames: rotate `{{STORY_COLORS}}`. `cm-1`…`cm-7` wash frames: white then black, like photos. Line breaks at phrase ends,
lines under ~26 characters.

**7. Render.** `render_frames.py "<set folder>"`.
- A **FIT** failure names the line: break it shorter (same words) and render again.
- A **FONT** failure: check the internet connection, render again.
- Side-margin notes are fine to post; mention them only if a frame looks cramped.

**8. Look before showing.** Open `_contact-sheet.png` yourself: any face covered, awkward crop, typo,
emoji shown as a box? Fix and re-render first.

**9. Show the coach.** Send the contact sheet (SendUserFile when they're on their phone). Say the post
time, the networks, and the one thing only they can do: confirm their DM tool has a **story reply**
trigger for the keyword. Ask for go.

**10. Hand off.** On "go" → `stories-schedule` with the set folder, time, and whether any frame is a
generated image. Changes → back to the step they touch, re-render, show again.

## Never
- Never post or schedule from here.
- Never fill a name, handle or photo of another person from a web search.
- Never mix text styles inside a set, put text on a face, or invent a number the source doesn't have.
