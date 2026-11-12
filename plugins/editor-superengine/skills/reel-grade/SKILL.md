---
name: editor-superengine:reel-grade
description: Sets the colour of a talking-head reel. Use on "grade this reel", "match the colour between my recordings", "colour grade", "fix the colour", "make it warmer", "the skin looks off", or "open the Grade Board". The editor measures the footage, shows every colour option on one contact sheet and the Grade Board, the client picks, and the grade is burnt in only after the client says yes. Every grade is checked so skin stays natural. NOT for cuts, captions or sound.
---

# reel-grade: the reel's colour

Match the colour of takes from different recordings and use the client's saved look when no look is picked for this reel.

## Output contract (every run, in this order)

1. The contact sheet and the Grade Board open in the Browser pane, with one plain line: "Pick a colour, or none, then press Send." Then stop for the Send.
2. The client's pick in plain words (the colour, its strength, the suggested fix on or off) and the question "Burn this grade into the video? Say yes to go ahead."
3. After the yes: the graded video.
4. A last line: what the client does next, or what still stops the grade.
5. On a failure you can't fix in two tries: what went wrong in plain words, then the failure report below.

Speak the way `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-user-hears.md` says: no file names, paths, script names or raw check output.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke it again before going on.
- Re-running is safe: the measurement and board steps write into `videos/<reel>/grade/` and `videos/<reel>/grade.json`; step 4 re-renders the cut from the raw only after a new yes.
- If the video changed after step 1 (a new cut), run step 1 again and ask for a new Send: the old frames and measurements are stale.
- Follow sections 5 and 6 (Auto edit and controls in chat) of ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md.

## Ground rules

- **The client never types a command.** Claude runs each one with the Bash tool from the client's workspace folder. `<reel>` is the reel's folder name under `videos/`.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. If it doesn't exist, run `editor-superengine:editor-doctor` first. Every command runs as `<editor python> -X utf8 -I "<script>" ...`.
- `<scripts>` is `${CLAUDE_PLUGIN_ROOT}/skills/reel-grade/scripts`. The board server serves the Grade Board from `boards/grade-board/index.html`. `deps.json` lists what editor-doctor installs for this skill; if a package or ffmpeg is missing, run editor-doctor, never `pip install` (it would break the editor's pinned Python).
- `<the video to grade>` is the signed-off cut master, `videos/<reel>/work/renders/master-<tag>.mp4` (tag = the cut's speed with the dot dropped, e.g. `115x`). If it is missing, the cut isn't done: hand back to `editor-superengine:reel-first-cuts`.
- Grade after the cut is signed off and before the visuals and the sound pass. If the sound pass already ran, run its mix again after grading.
- A *look* is one of the five colour presets (natural, warm, punchy, soft-matte, mono); None is no look.

## Hard rules (always on)

1. **The colour is the client's.** The grade opens at the identity (no change); the measured fix is a button, never a default. Taste is an option, never a rule: say what a colour does, never that one is right.
2. **Nothing is burnt in without the client's yes.** Claude runs step 4 only after the client said yes to this grade, in this conversation (a re-run needs a new yes), because the encode changes the delivered video.
3. **Skin stays natural.** Every look and every Send runs the skin guard. A refused grade is never forced: say so in plain words and offer a lower strength or another colour.
4. **ffmpeg writes the pixels; the page is where the client judges.** Never ship a browser screenshot or canvas readback as the grade: browser colour management shifts it.

## The flow

### 1. Measure

`<editor python> -X utf8 -I "<scripts>/make_grade.py" --reel <reel> --video "<the video to grade>" --reel-dir videos/<reel>`

It measures black, white and skin hue on three frames, bakes each look and checks it against this reel's skin (a ✗ line is a look the guard refused: don't offer it), and writes `grade.json` at the identity. "No face found": ask whether this is a graphics-only video.

**1b. Several recordings** (the cut's `work/cuts.json` has `takes`): match them before step 2: `<editor python> -X utf8 -I "<scripts>/grade_match.py" --from-cuts videos/<reel>`.

### 2. Contact sheet and Grade Board

`<editor python> -X utf8 -I "<scripts>/looks_sheet.py" --reel-dir videos/<reel>`

It writes `videos/<reel>/grade/looks-sheet.jpg`: the face frame through None and each look, labelled. Show it. Then start the board server and open the Grade Board inside the hub (`board=grade-board`, Full view), as `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md` step 3 says. The client picks a colour and its strength, tries the suggested fix, compares with the wipe and A/B, then presses Send (it writes `grade-selection.json`).

No board, or the client picks from the sheet in chat: run step 1's `make_grade.py` again with `--look <id> --strength <0-1>`, then go to step 4.

### 3. The Send becomes the grade

`<editor python> -X utf8 -I "<scripts>/grade_from_selection.py" --reel-dir videos/<reel>`

It bakes the Send into one cube, runs the skin guard and writes `grade.json`. Nothing is applied. Exit 1 names the problem in one line (no Send yet, no setup, a grade the guard refused, a Send from another grade maths version): fix that, or ask for a new Send.

### 4. Burn it in, only on the client's yes

Tell the client the pick and ask (output contract, item 2). On a yes:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/render.py" videos/<reel>/work/ "<raw video>" --master --scrub --grade videos/<reel>/grade.json`

Use the reel's raw video; when the cut lists takes, render.py chooses the raw from the cut.

This replaces the cut's master with the graded one, so the visuals and the sound pass use it with no extra encode. It checks the cube's sha before rendering. "Missing or changed": run step 3 again. A change after the client sees it goes back to the board (step 2).

The maths, the 8-bit page vs the float bake, the Windows filter path and the sha check: `${CLAUDE_PLUGIN_ROOT}/skills/reel-grade/references/grade-details.md`.

## What this skill will not decide

- Which colour, how strong, whether to use the suggested fix: the client decides.
- Whether the grade is done: the guard qualifies it; only the client's own look approves it.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.2 --skill reel-grade --step '<measure, match, sheet, board, bake or apply>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
