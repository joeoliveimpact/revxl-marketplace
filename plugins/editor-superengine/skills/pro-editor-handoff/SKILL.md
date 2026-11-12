---
name: editor-superengine:pro-editor-handoff
description: "Exports the finished reel as an editable timeline for DaVinci Resolve Studio or another editor. Use when the client asks to open the reel in Resolve, send it to their editor, or get files for Premiere or Final Cut. Offered only when the doctor found Resolve Studio (nle resolve) or the client chose another editor (nle mcp: files only). Never the default export."
---

## Output contract

1. Confirm the client wants an editable copy of the finished reel and which editor they use.
2. Confirm the latest preview has the client's Master OK, then package the reel.
3. For Resolve, use only Studio 21.1's native MCP, import into a new project and verify the saved results.
4. Say what landed in plain words. Offer the failure report after a failure you cannot fix in two tries.

## Re-invoke guard

- After compaction, invoke this skill again before continuing.
- Read `editor/editor.config.json` first. Offer this only for `nle: resolve` or `nle: mcp`, never automatically. If `nle` is `none` or `auto` and the client asks, ask which editor they use, record it through `editor-superengine:editor-doctor` (`--set-nle`), then continue.
- Use the current reel and its latest preview OK. A stale or missing OK means return to `editor-superengine:reel-canvas-build`.
- Only a new Resolve project may be created. Never open or alter an existing project. Launch Resolve only with the client's OK.
- Resolve runs only through its own native MCP tools; the plugin never connects to Resolve itself. Never use an SDK, external scripting connection or another connector.
- Never append an SRT to a timeline, pass SRT source frame ranges, or embed SRT assets or caption elements in FCPXML.
- The client's camera recordings are read only. Keep exported files in the reel's `handoff/` folder.

## Flow

Claude runs every command in the client's workspace; the client never types a command. Keep technical output out of the conversation and translate failures into plain words.

- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first.

`package` refuses without the client's OK of the latest preview; on that refusal, go back to `editor-superengine:reel-canvas-build`. Once the client has opted in:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/pro-editor-handoff/scripts/build_edit.py" package --reel-dir "videos/<reel>"`

The default packages all three picture layers: a-roll, overlay and captions. Re-running replaces exported files. `--which aroll`, `overlay`, `captions` or `none` is for retrying or reusing verified layers. All three must be present; old packages need all layers rendered again. Never substitute the unmoved cut master for the baked a-roll.

Picture-in-picture, blurred-card and moving-transition (whip, zoom, glitch) parts come in as the finished Master picture for those spans, with one plain note naming their times; those pictures are baked, while their voice and original sound remain editable. `package` needs the final video made after the client's latest OK. If it says the approval is from before hook text was saved, invoke `editor-superengine:reel-canvas-build` to make the final video (with the preview's `--hook-text`, if any), then package again.

For `nle: resolve` and the DaVinci Resolve choice, prepare the native steps:

The voice comes in as one continuous track, with picture clips at each cut.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/pro-editor-handoff/scripts/build_edit.py" resolve-steps --reel-dir "videos/<reel>"`

Discover the native tools named like `mcp__DaVinci_Resolve_Studio__get_resolve_status`, `mcp__DaVinci_Resolve_Studio__launch_resolve` and `mcp__DaVinci_Resolve_Studio__run_script`. If they are unavailable, say one plain line: "The Resolve hand-off needs DaVinci Resolve Studio 21.1's own connector turned on; I can offer the files for another editor instead." Stop the Resolve path; never try another route.

Call `mcp__DaVinci_Resolve_Studio__get_resolve_status`. If Resolve isn't running, ask the client to open it, or call `mcp__DaVinci_Resolve_Studio__launch_resolve` with their OK. Read `handoff/resolve-steps.json` and execute its steps in order. Before each, say its `say` line, then call the native `mcp__DaVinci_Resolve_Studio__run_script` with exactly its `script` and `timeout` (never above 60 seconds). The script sets `result`; collect that JSON object under the step's `id`. Stop on the first tool error or result with `ok` other than true. Never continue importing after an error. Save the collected results with the Write tool to `handoff/resolve-result.json`, shaped as `{"ready": {...}, "project": {...}, "import": {...}, "captions": {...}, "report": {...}}`; on failure save only the steps actually run.

Then check the saved results, including a partial failure:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/pro-editor-handoff/scripts/build_edit.py" resolve-check --reel-dir "videos/<reel>" --result "videos/<reel>/handoff/resolve-result.json"`

Read `handoff/resolve-report.json`. Only claim success if the checker passes. It checks linked files, tracks, the bed's applied level and available frames; relay any note about a skipped frame comparison. Say which picture checks were skipped because B-roll or other pictures cover their frames. Relay any MP3 timing note: Resolve may play original MP3 effects about 50 ms late.

For `nle: mcp`, or the Another editor (files) choice, hand over the folder: FCPXML opens in Final Cut or Resolve; FCP7 XML opens in Premiere and other compatible editors; SRT supplies editable subtitles. Keep the referenced original music, effects and finished Master available alongside the reel; the XML points to those files.

Say: "Your spoken picture has a clip at every cut. The graphics and cutaways are a transparent overlay. Captions come in as their own layer; the editable captions file is in the Media Pool and one drag onto a subtitle track gives editable captions. The original music has its speech dip as editable volume points, and the original sound effects have editable levels. Camera moves are baked into the spoken picture; they are not editable camera keyframes." For the files-only path, say the editable captions file is in the hand-off folder instead of the Media Pool.

FCP7 carries simple sound levels; use FCPXML for the music's volume points and fades. Hide the captions picture layer when using editable subtitles to avoid showing both. Finished-picture spans contain the Master captions too.

FCP7 preserves stereo with paired audio tracks: voice first, then every music channel, then effects channels. Its track numbers can differ from the FCPXML lanes.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.2 --skill pro-editor-handoff --step 'handing off the reel' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
