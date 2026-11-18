---
name: carousel-superengine:carousel-review
description: Put rendered slides in front of the coach in a live browser so they can mark them up directly, then turn their notes into fixes and re-render. Use after any render (Path B/workspace especially), or any time the coach wants to look at a finished deck before posting. Trigger phrases include "show me the carousel", "let me see the slides", "preview the deck", "I want to mark it up", "review the render", "put it in a browser", "let me look at it before I post".
---

# Task: review

Rendered PNGs → coach marks them up in a browser → their notes become edits → re-render → verify.

This exists because **spot-checking a couple of exports does not catch what a coach catches.**
On a live run the quality gate scored a deck 12/12 and a 2-3 PNG check passed it, while a browser
markup pass surfaced a headline bleeding off the right edge, a ghost word colliding with the type,
and a "proof" image that was a 1325x100 sliver floating in dead space. Looking at all of them, at
size, with the coach, is the check.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md if present
${CLAUDE_PLUGIN_ROOT}/references/design-rules.md (the hard guardrails you are checking against)
${CLAUDE_PLUGIN_ROOT}/references/render/review-loop.md (the loop — read before serving anything)

## Flow

**0. Find the render.** Use the render directory from this conversation, or the newest one the
coach points at. Needs an exported PNG set. No PNGs → route to `carousel-render` first.

**1. Build the contact sheet.** Per `review-loop.md`. Numbered slides, filename on each, grid and
one-at-a-time modes.

> **Write it OUTSIDE the render directory.** `render_slides.py` globs every `.html` in the folder
> and dies on the first file with no `#slide` element. A sheet written next to the slides breaks
> the next re-render with `"#slide not found in index.html"`.

**2. Serve it and open it.** Static server on loopback, then the in-app browser pane. Give the
coach the URL in plain text too — they may want their own browser to annotate in.

**3. Wait. Do not narrate the slides.** The coach is looking. Offer the two or three things you
already know are unresolved (open flags from the build, anything you deviated on) and stop.

**4. Take the markup.** Annotated screenshots come back with numbered notes. Map every note to a
slide number and echo the mapping as a table before changing anything — a misread note costs a
full rebuild cycle.

**5. Answer questions before executing them.** Coaches mark up in questions ("should this be
bigger?", "shouldn't this say X?"). Some are instructions, some are genuine asks. Where a note
would break something the deck depends on — an open loop, a CTA keyword, a payoff match — say so
and recommend, then do what they decide. See `review-loop.md` for the specific traps.

**6. Fix at the source.** Edit the generator, never the exported HTML. Re-run build + export.

**7. Verify the CHANGED slides at full size.** Read each changed PNG. The contact sheet is for the
coach's eye, not yours — thumbnails hide edge bleed, overlap, and illegible small type.

**8. Loop.** Steps 2-7 until the coach says it's done. Then hand back file paths. Drafts; the
coach posts.

## Cleanup
Leave the server running until the coach is finished. Contact sheet is disposable — say whether
it should be kept, gitignored, or deleted.

## Not this skill
Grading copy against beat data → `carousel-quality.md` via `carousel-create`.
Producing the images at all → `carousel-render`.
Saving the finished look for reuse → `carousel-templates`.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `carousel-superengine/reports/report-body.md` under the workspace folder: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text, slide copy).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin carousel-superengine --plugin-version 0.6.0 --skill carousel-review --step '<opening the review or re-rendering>' --error-line '<the error line>' --summary '<headline>' --body-file carousel-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

The client never types any of these; you run them.
