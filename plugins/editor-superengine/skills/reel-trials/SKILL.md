---
name: editor-superengine:reel-trials
description: Makes trial reels from one approved cut, changing exactly one opening, hook, camera field or colour look per version. Use for trial reels, a trial version, "test a few hooks on this video", "try different openings", or several truthful openings from the same cut. Not for writing new hook lines (that's shortform-superengine).
---

## Output contract

1. Confirm the current reel has an OK'd latest preview of its base cut.
2. Offer three trial versions, each changing exactly one declared thing. Get the client's choices before writing the spec.
3. Plan and render full-length 720p trial reels; every version keeps the same cut and voice, with no speed change.
4. Open the Trial reels hub tab with the unchanged base and the trial versions together.
5. After Send, read the client's keep/skip choices and notes and report them in plain words.

## Re-invoke guard

- After compaction, invoke this skill again before continuing.
- Read the current reel's Beat Map Send and latest preview OK. A stale or missing OK goes back to `editor-superengine:reel-canvas-build` for approval.
- An existing plan is reusable only while its base hashes still match. Changed cut, Send, words, sound or saved choices need a fresh plan.
- These are trial versions to post and compare by the client's own results. Never call an internal comparison an audience experiment; never invent a predicted score or promise results.
- Never invent hook numbers or proof: every hook number and every number in an opening's text slots must be said in this reel's own words. The planner imports caption-writer's number check.
- Opening kits, hook types, loops and slots are options, never defaults. Do not add them without the client's choice.
- Keep all trial media in this reel's `trials/` folder. Never overwrite its cut, Beat Map Send, captions, camera track, OK files or main renders.

## Flow

Claude runs every command from the client's workspace; the client never types a command. Translate any failure into one plain line. Never send raw tool output to the client.

- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first. `<reel folder>` is the reel's folder inside the videos folder that `paths.videos` names in `editor/editor.config.json`.

Offer the opening kit: three materially different openings from the same true words. Compare topic clarity, curiosity and follow-through as observations, with no invented retention numbers. For each opening, watch muted and check whether the subject and promise are understandable with the sound off. Offer the four hook types: bold claim, question, contrast, or a real number said in the reel. The client chooses; a number is never the default.

From the approved cut, suggest three trial versions, each with ONE change: the opening scene on beat zero, the plain frame-zero hook title, one editing-style field, or a colour look. A hidden plain title cannot be trialled while an opening scene covers it: offer an opening trial instead. Do not alter timings, layout, captions, sound, speed, frame rate or cuts as extra changes.

Write a JSON spec beside the reel's work files with one `versions` list (two to four entries). Each entry has a unique lowercase `id` such as `t1`, one `change`, its fields below, and an optional text `note`:

- `opening`: `scene` is an installed scene id or `null` for the plain title. For a scene, give every text `slots` value and optional `params`. The scene must fit the existing first beat. Choose different scenes or fills from the client's truthful words.
- `hook`: `hook_text` is a different truthful title, at most 70 characters. The base opening must have no scene.
- `reframe`: `field` names exactly one `edit_style.*` entry in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py` FIELDS; `value` is its chosen value. For example `edit_style.punch_scale` or a complete `edit_style.moves.reframe` object. A move that does not affect the picture across the reel may fail the strict picture proof; explain that limitation instead of adding other changes.
- `grade`: `look` is a saved-style look id different from the reel's current look; optional `strength` is above zero and at most one. This burns one look over the composed base preview in one additional generation, keeping its sound packets. It does not replace colour already baked into the approved cut. Explain this before offering that choice.

Run, as Claude:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-trials/scripts/trials.py" plan --reel-dir "<reel folder>" --spec "<reel folder>/work/trials-spec.json"`

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-trials/scripts/trials.py" render --reel-dir "<reel folder>"`

Run `render` with `run_in_background` and wait for it, telling the client it's working, or run one `--only tN` per call; a full render can pass the 10-minute Bash limit. Retry one version with `render --reel-dir "<reel folder>" --only t1`. The planner writes `trials/trials.json`; rendering writes the base, each version and `trials/trials-report.json`. Every version is checked for frame count, frame rate and identical audio packets. Opening/title trials must differ within their opening window and match afterwards within codec tolerance. Camera/colour trials must differ across the reel. A failed version's file is deleted; fix it before presenting it.

Offer the optional **Open loops** panel in the Beat Map: viewer question, on-screen object, setup, updates, closure, the actual spoken closure words and an optional call to action. Setup must precede every update, updates precede closure, and closure precedes the call to action. Send the ledger before planning; the pre check proves the closure words inside that window. Old Sends need no ledger.

Offer the optional **slots** scene for a list reel: two to six labels of one or two words, shown as empty slots in the hook, re-shown and filled in order at the client's section starts, ending on the completed list. Set `count` and `section_starts` (comma-separated local seconds, one per active slot), fill `label1` through `label6`, and leave unused labels empty. Every numbered label must be said in the reel. Place it only when chosen and when its duration fits; never retime the approved cut to make it fit.

Refresh and open the hub using `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/hub.md`, then select **Trial reels**. Play the base and versions side by side; use **Muted** and **Watch the opening** to play the first five seconds together. Ask the client to mark keep or skip for each version, add any note, then Send. Read `trials-selection.json` and report the exact choices in plain words. A keep is a choice to try posting, never permission to publish; posting and result collection remain with the client.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.0 --skill reel-trials --step 'making trial reels' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
