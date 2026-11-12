---
name: editor-superengine:reel-teardown
description: Tears down a reel that is already posted and shows the same footage rebuilt, as one page to read or send the creator. Use on "tear down this reel", "review this reel", "what would we fix", "why did this flop", "make a page I can send them", or a posted reel's video or link. NOT for an unrecorded reel (shortform-superengine's reel-scripter), raw footage (reel-first-cuts) or copying a style (style-decoder).
---

# Reel teardown

Posted reel, then transcript and frames, then the diagnosis, then a rebuilt script, then one
page the client can read or send. **One page per reel. The client picks the hook.**

## Output contract

Every run returns, in this order:

1. One plain line on what was used: the video (their file or a pulled link), how the words were
   timed ("measured" or "estimated" from a pasted transcript), and whether the rebuild runs.
2. Full run only: the hook options, then a stop for the client's pick.
3. The page, checked at phone width and shown as a screenshot, then a stop. Deploying it is a
   separate ask.
4. Saved in the client's workspace under `teardowns/<creator> <MM.DD.YY>/` (that name from the
   start, never renamed): `transcript.md`, `teardown.md` and `site/index.html` with
   `site/img/`. `teardown.md` is the internal record: the same sections as the page, in third
   person, plus the open questions. Tell the client "it's saved in your teardowns folder",
   never the file names.
5. On a failure you can't fix in two tries: what went wrong in plain words, then the failure
   report offer below.

What the client hears follows
`${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-user-hears.md`: no file
names, paths, JSON or script names, ever.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke this skill again before
  going on. Re-running is safe: finished files in the teardown folder are reused, not redone.
- Never re-run a SocialCrawl pull that already succeeded; it costs a credit each time.

## Before you start

- `<editor python>` is the editor's own Python. Windows:
  `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS:
  `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the
  quotes. If it doesn't exist, invoke `editor-superengine:editor-doctor` first.
- **Full run or diagnosis only.** A full run needs shortform-superengine: the skills
  `shortform-superengine:hook`, `shortform-superengine:viral` and
  `shortform-superengine:rehooks` must be in your available skills. If they aren't, this is a
  diagnosis-only teardown (stages 0 to 2, then the page). Say so in the first line. **Never
  fake the rebuild.**
- Claude runs every command with the Bash tool. The client never types one.

## Inputs (ask once, in one message, for whatever is missing)

- The reel: a video file first. A reel link only through SocialCrawl (stage 0).
- The creator: handle, name, what they do, who the reel is for. Pronouns as the client states
  them; otherwise they/them.
- The metric the creator is chasing, in their words. Default when unstated: shares, then saves,
  then comments, then profile visits, with watch time gating all of it, so the default CTA is
  send-to-someone. A stated metric moves to the front and picks the one CTA (saves:
  save-for-later; shares: send-to-someone; comments: a question to answer).
- Whether the script is frozen. Default: not frozen (a rebuild is the point).
- Anything the creator supplied: insights, a retention graph, client results with their
  qualifier. **If none, none.**
- The client's own name and business, for the page's signature.

## Stages (do not reorder)

### 0. Pull and transcribe (no judgment yet)

- **A video file:** copy it to the teardown folder's `work/reel.mp4`. Never touch the original.
- **A reel link:** only when a key already exists at `~/.config/socialcrawl/api_key` or in
  `SOCIALCRAWL_API_KEY` (check it exists; never print it). Before the call, tell the client what
  will run and what it costs: "I'll fetch this reel's details and a copy of the video from
  SocialCrawl. That's 1 credit for the details plus the video download. Go ahead?" **Wait for a
  yes. This is a money step: no yes, no call.** No key: ask the client to download the reel from
  the app and drop the video file in. Never ask them to type a command.
- **Transcribe:** from the client's workspace folder (not the teardown folder), run
  `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py" "teardowns/<folder>/work/reel.mp4" -o "teardowns/<folder>/work/tx.json"`
  (`<folder>` is `<creator> <MM.DD.YY>`). The word list, with start and end times, is `work/tx.json`.
  Exit 3: the transcriber isn't set up, or is set up for another language: invoke `editor-superengine:editor-doctor`, then run it again. Exit 1: the video isn't there, or its sound can't be read.
- **Last resort:** if the transcriber isn't set up or fails twice, ask the client to paste the
  transcript. Pace is then the word count over the reel's length, and **every timing on the page
  and in `teardown.md` is labelled "estimated"**.
- List sentence onsets (a sentence starts at the first word after `.?!`). The measured pace
  formula is in `teardown-details.md`.
- Write `transcript.md`: a header (creator, posted date and stats if pulled, length, how it was
  timed) and the transcript with sentence onsets.

Commands for the pull, the length and the frames: `${CLAUDE_PLUGIN_ROOT}/skills/reel-teardown/references/teardown-details.md`.

### 1. Frames

Grab frames with the editor's ffmpeg at fixed times, build two strips (the opening and the
body) and keep frame 0 large. **Look at both strips before you assert what they show. The read
is the evidence.** Record: the text on screen at 0.0 s, whether it ever changes, cuts or
B-roll, and framing changes.

### 2. Diagnose (on the original)

- If shortform-superengine is installed, read reel-scripter's shared references first (hook
  diagnostics, story locks, CTA scaffolds). Otherwise diagnose from the transcript and frames
  with the same structure below.
- The four hook killers (delay, confusion, irrelevance, disinterest) on the spoken opening and
  the frame-0 text. Name which fire.
- Craft scores Hook / Body / CTA / Overall, 0 to 100, on the Story Locks rubric. When
  reel-scripter's references aren't available, use the fallback rubric in
  `${CLAUDE_PLUGIN_ROOT}/skills/reel-teardown/references/teardown-details.md`.
- The six levers, each as "what they did / why it leaks / the fix, in their own words": scroll
  stop, re-hooks, share, save, profile visit, comments and likes.

### 3. Rebuild (full run only), in this order, cold

The run order and the 90 s gate are the point; don't reorder.

Each skill runs as a **fresh subagent** (the Agent tool) that sees exactly two things: the
skill, which it invokes with the Skill tool and follows (its method file's `## What you return`
is the shape of its answer, `## Ask the creator for` is what the brief must carry), and a brief
written from `${CLAUDE_PLUGIN_ROOT}/skills/reel-teardown/references/cold-run-brief.md`. **It
never sees this skill, the diagnosis, or another skill's output** except the one input the
table hands it. If one did, throw its result away and run it again: a warm run isn't a test of
the skill. Save each result in `work/` as `01 hook.md`, `02 viral.md`, `03 rehooks.md`.

| Order | Skill | It gets | Gate before the next |
|---|---|---|---|
| a | `shortform-superengine:hook` | the original transcript, onsets, frame facts | **The client picks one opening** with AskUserQuestion: the options, primary first, plus "none of these". Never pick for them. |
| b | `shortform-superengine:viral` | the original transcript plus the picked opening, marked "keep this opening" | The result runs **under 90 s at the creator's measured pace**. If not, cut whole sentences from the creator's own lines until it does, and say which. |
| c | `shortform-superengine:rehooks` | viral's result with estimated onsets | Its 90 s gate passes. If it still refuses, viral's step was wrong: go back, never pad. |

Hook comes before viral because viral needs an opening to build around. Viral comes before
rehooks because rehooks refuses anything over 90 s. `angles` and `polarize` aren't in this run;
offer them after, if the creator wants a series or a sharper stance.

### 4. Re-score and reconcile (full run only)

Story Locks on the rebuilt script: the four craft scores again, beside stage 2's. Merge the
three results into one beat map (time, beat, spoken, on screen, job): hook's picked opening,
viral's body and CTA, rehooks' typed re-hooks at rehooks' timings. Where they disagree, viral's
line wins inside a beat and rehooks' placement wins between beats. Write the full read-through
script.

### 5. Page

- Start from `${CLAUDE_PLUGIN_ROOT}/skills/reel-teardown/references/page-shell.html` and keep
  its section order. Frames go in `site/img/` as JPEG. Address the creator in second person.
  Keep the `noindex` line. Dates are MM.DD.YY. A local file with no link or stats: leave the
  stats line out. The signature is the client's name and business.
- **Diagnosis only:** the rebuild sections (hook options, beat map, script, re-hook map, scores
  after) become one plain note: the rebuilt script comes from shortform-superengine, which isn't
  installed. The CTA pull quote describes the current CTA and its fix in one line; it doesn't
  write a rebuilt CTA. In the chat, offer to help install shortform-superengine.
- **Check before showing:** add an entry named `teardown-<folder>` to the client workspace's
  `.claude/launch.json` (create it if missing, keep existing entries) that serves `site/` with
  `<editor python>` on a free local port, `--directory` set to the site folder's absolute path; the entry's shape is in `teardown-details.md`. Then
  `preview_start` by that name. At 375 px wide, with JavaScript:
  `document.documentElement.scrollWidth == 375`, every visible row inside `.tscroll` (header rows
  are hidden on mobile) computes `display: block` (tables stacked into cards), and no console
  errors, and no unfilled placeholders: `document.documentElement.outerHTML` contains no `{{`
  (the title and meta lines included) and `document.body.innerText` contains no "goes here". A
  failed check means fix the page, never deploy it. Re-check until all four hold.

## Guardrails

- The creator's words are the material. Reorder, cut whole sentences, add seams and one CTA.
  **Never add a claim, number, study or result they didn't say**; leave a marked fill-in.
- Don't sanitize their wording. Blunt stays blunt.
- One CTA on the rebuilt reel, chosen by the metric. Say why.
- Second person on the page, but keep the creator's "we" where viral kept it on purpose, and say so.
- Scores are craft. Never a view prediction.
- Option (house style, the client turns it on): no em dashes or en dashes on the page.

Common mistakes and the fix for each: `${CLAUDE_PLUGIN_ROOT}/skills/reel-teardown/references/teardown-details.md`.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.2 --skill reel-teardown --step '<pull, transcribe, frames, rebuild or page>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
