---
name: editor-superengine:reel-broll
description: Adds own or downloaded AI B-roll as cutaways over Beat Map beats. Use for add B-roll, generate B-roll, AI cutaway, or use my clip over a line. Hands generation to higgsfield-superengine, prepares silent clips, logs their bytes, and opens the Beat Map tab before reel-canvas-build renders.
---

# reel-broll: cutaway clips on the reel

## Output contract

1. Say where the clips stand in one plain line.
2. Open the Beat Map tab in the editor hub and say what to pick there.
3. After Send, summarize the picks and hand the render to `editor-superengine:reel-canvas-build`.
4. After a failure you cannot fix in two tries, offer the report below.

## Re-invoke guard

- After compaction, invoke this skill again before continuing.
- The spoken cut must be signed off first. If it changes, rebuild the Beat Map and preview.
- Reopening the board is safe. Never replace the client's edited board without asking.

## Flow

The client drops their own video clips in `videos/<reel>/broll/`. Claude runs every command; the client never types one. Translate file names and technical output into plain words for the client.

- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first.

Run from the client's workspace:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-broll/scripts/broll_ingest.py" "<reel folder>"`

If setup is missing, invoke `editor-superengine:editor-doctor`. If there is no cut, invoke `editor-superengine:reel-first-cuts`. An unreadable clip is skipped with its name; ask for a readable copy.

Open the hub using `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md`, then its Beat Map tab. If the reel needs its first Beat Map, follow `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/beat-map.md`; preserve an existing one. Per beat, pick B-roll (or None), Fit (Cover or Blurred fill), and Starts at in seconds. The board saves whole frames and refuses clips shorter than the beat. Loading keeps saved picks unchanged. Have the client press Send once. Read `beat-map-selection.json`, then invoke `editor-superengine:reel-canvas-build` for the preview and the final after the client's OK.

## Generate a clip

This needs the internet and spends the client's own Higgsfield credits: their plan, their key. The editor never pays or runs generation. If higgsfield-superengine is not installed or set up, say so and offer to invoke `higgsfield-superengine:higgsfield-setup`; the client never types a command.

1. Invoke `higgsfield-superengine:hf-generate` for a short silent 9:16 video for the beat. It picks the model, shows the full prompt for approval and writes `higgsfield/requests/<name>.json`. Pause that skill after the request is written, before it prices or submits.
2. Run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-broll/scripts/broll_ingest.py" "<reel folder>" --reuse "<request json>"`. This reads local files only. A match means use that prepared clip: tell the client it is reused, with no new job and no charge, then go to the Beat Map tab. A changed prompt or setting is a different request. If the request cannot be read, stop and fix it before continuing.
3. With no match, continue `higgsfield-superengine:hf-generate`: it shows the estimate as "about $X". That is the spending ask: ask whether to proceed and wait. "No" means stop before submission; nothing runs and nothing is charged. Only "Yes" lets that skill submit through its spend guard, wait, download into `higgsfield/<YYYY-MM-DD>/`, and keep the job id (`request_id`). On a retry, follow its existing-job guard; never submit the same job twice.
4. Run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-broll/scripts/broll_ingest.py" "<reel folder>" --ai "<downloaded file>" --job-id "<request_id>" --request "<request json>"`. This prepares one silent copy in `broll/ingested/`, without changing the download, and logs its job id and the exact request's hash. Only that Higgsfield skill handles generation, prices, credits and downloads.
5. Return to the Beat Map tab to place it, then follow the existing Send and preview flow above.

## Hard rules

- Audio is removed on ingest and every B-roll layer stays muted; the voice sound is copied unchanged.
- The footage ledger must match the file's hash and identity. Source ranges cannot overlap themselves.
- Start and end on whole cut frames; each clip plays for the whole beat. Two B-roll spans cannot overlap; one may cross cuts. The render checks the spans first.
- An AI clip cannot sit on a beat with a value or a counter or stat-card scene: it would look like proof. Own clips pass; every AI ledger row carries its job id.
- Used footage needs a licence row before the 1080p final; an AI row also needs its job id. Previews warn; finals refuse missing rows.

Placement is taste: suggest keeping the speaker visible in the first and last 3 seconds, or putting one longer cutaway over dense jump cuts. These are options, never blocks. Stock footage is outside this skill.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.1.0 --skill reel-broll --step 'adding the clients clips' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
