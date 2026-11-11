---
name: editor-superengine:reel-cover
description: Picks a cover frame from the reel, adds an optional short title using its own words, and can use the cover as frame zero. Use for "pick a cover", "thumbnail", "cover photo", "pick the frame people see first", cover titles, or the Cover Picker. Not for generated thumbnail images.
---

## Output contract

1. Show up to six real frames from this reel, with the recommended opening first.
2. Open the Cover Picker tab and let the client choose a frame, an optional title and whether to embed it as frame zero.
3. After Send, apply the choice to `"<reel folder>/cover.jpg"` and `cover.json`.
4. Report the chosen frame, exact title (or no title) and first-frame cover on/off in plain words. If on, say the next render puts the cover at frame zero; the reel's length and sound stay the same.

## Re-invoke guard

- After compaction, invoke this skill again before continuing.
- Read the reel's current cut and cover Send before acting. A changed cut or final needs fresh candidates.
- Needs a cut master or a final video. If neither exists, invoke `editor-superengine:reel-first-cuts` first.
- This is the editor's own offline cover picker. Use real reel frames; no generated image, paid service or carousel picker.
- The user chooses. Titles contain at most six words and 28 letters, all said in the reel; numbers must also pass caption-writer's number check. Never invent a claim. Your title sits above your head when there is room, otherwise below the top 75% of the measured head box to clear your eyes and mouth. Try one size smaller in the same order before refusing; offer a shorter title or another cover frame from the picker. A box filling the whole frame refuses a title.
- An existing `cover.jpg` is an applied choice, not permission to pick again or publish.

## Flow

Claude runs every command from the client's workspace; the client never types a command. Translate any failure into one plain line. Never send raw tool output to the client.

- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first. `<reel folder>` is the reel's folder inside the videos folder that `paths.videos` names in `editor/editor.config.json`.

Frame 0 is recommended because the hook text lives there (on the cut master, the hook text is added with the final); any frame is fine. If frame 0 is blurry, the sharpest frame within the first half-second is recommended instead. Without face anchors, explain that the suggestions use sharpness alone and the head is not measured.

If `<reel folder>/work/anchors.json` is missing or older than the newest `<reel folder>/work/renders/master-*.mp4`, run as Claude with `run_in_background` and wait for it to finish:
`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/face_crop.py" anchors --reel-dir "<reel folder>"`
If it stops or finds no face, go on and say plainly: "The cover suggestions use sharpness only, and the title sits low."

Run, as Claude:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-cover/scripts/cover_pick.py" candidates --reel-dir "<reel folder>"`

The newest final is used, or the cut master if there is no final. Use `--video "<chosen video>"` only when the client chose a different existing reel video. Frames, scores, head boxes and the reel's word list are in `cover/candidates.json`.

Refresh and open the hub using `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/hub.md`, then select **Cover Picker**. Let the client pick a frame, optionally enter their short title, optionally check **Use this cover as the first frame of the reel** (off by default), then Send. The live preview marks the protected head and face band and title area. If the title cannot fit beside the face even one size smaller, say: "The title doesn't fit beside your face on this frame, even one size smaller. Use a shorter title, or pick another cover frame from the picker."

After Send, read `cover-picker-selection.json`, then run:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-cover/scripts/cover_pick.py" apply --reel-dir "<reel folder>"`

Report the frame, exact title and embed on/off. Show `cover.jpg`. If embed is on, say: "Your next render puts this cover at frame zero." The cover is visible for one frame only; the following frame, reel length and audio timing are unchanged. A new render goes through `editor-superengine:reel-canvas-build` and its normal preview approval. This choice never publishes anything.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.1 --skill reel-cover --step 'picking the cover' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
