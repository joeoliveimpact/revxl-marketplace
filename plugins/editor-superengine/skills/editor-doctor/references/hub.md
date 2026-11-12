# Open my editor hub

Claude runs these commands in the client's workspace with the editor Python from the Ground rules in SKILL.md.
The client never types a command. Refresh before opening, and again after an edit or a Send is acted on:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/board_sync.py"`

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/hub_rows.py"`

Start or reuse the [board server](board-server.md), then open its printed URL plus `editor/hub/` in the Browser
pane with `preview_start`. The page reads `hub-data.json` every 15 seconds; Reload re-reads it without discarding
the open board or moving the player when its URL is unchanged. Only Claude runs the refresh script. It reads
the configured editor/videos folders, the board manifest, artifacts, Health STATUS entries and Goldmine exports;
media inspection and frame extraction use the installed video tools. The script never spends credits or probes the setup.

Guided view shows the current step and reel strip. Full workspace uses a reel list, centre boards and a right
inspector with quick adjustments, notes, skill requests and Save this style. Both views use the same data and
Sends. Layout is in the hub's own `hub.state.json`, saved through `__state?name=hub` in an existing reel, and used
across reel selection and browser reload. With no reels the toggle is disabled: the server requires an existing
reel for every state write. Deleting the state-owning reel also deletes that preference.

The Full view button fills the hub with the client's open board under a slim step bar. Back to hub, Escape, or the pane's Back
leaves Full view in the same hub document with your board tab, draft and place kept, including when opened at a Full view address.
Messages and the copy-line fallback show just under the bar in Full view. The step buttons open built boards inside the same hub.
Use `editor/hub/?reel=<reel>&board=<board id>&view=full` to open a built board (or `board=review` for Master
review) in Full view. Omit `view=full` to keep the hub visible. The address follows your board and view;
unknown or unbuilt boards open the hub with a short status line. A refresh follows the next step when you
are still on the previous step's board and keyboard focus is outside the board frame.

## What Claude reads after a Send

All Sends use `/videos/<reel>/__save?board=hub&name=<file>`. A successful Send records a request; it does not
start tools. Read the whole file before acting and keep earlier entries when acknowledging a request.

| File | Meaning and next action |
|---|---|
| `review.json` | `{ "approve": true, "preview": "<latest finished preview filename>", "note": "<text>", "sent_at": "<ISO>" }`. The page plays the newest finished `renders/* Preview 720p - *.mp4`, excluding `.partial.mp4`, and approval works before a master exists. Send notes uses `approve: false`. Read the note and make requested fixes. On an approve, invoke `editor-superengine:reel-canvas-build`: it records the OK with `--from-review` (build.md section 3) and makes the final video. A notes-only Send is a change request for canvas-build. When present, the page also shows the master and QA result. Approval does not publish anything. |
| `reel-notes.json` | Append-only list of note text, kind and player time. Read these before working on the reel and apply the client's instructions. |
| `hub-requests.json` | Append-only request objects (`at`, `reel`, `skill`, `ask`, `choices`), or controls entries (`kind: "controls"`, `value`, `at`). Use the table below, keyed on `skill`. Quick adjustments are requests with the chosen values, not fabricated board selections. |

| `skill` | What Claude does |
|---|---|
| `health` | This skill's doctor (step 2). |
| `adjust-cut` | Invoke `editor-superengine:reel-first-cuts` (the gaps). |
| `adjust-grade` | Invoke `editor-superengine:reel-grade`. |
| `adjust-sound` | Invoke `editor-superengine:reel-sound-pass`. |
| `style` | Ask "Save these choices as a new style?"; on yes, run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" save-from-reel <reel folder>`, read back the result, say the new name and offer a rename in the same line. This saves the choices and the workspace skill. Refresh with both scripts above. |
| `styles` | Run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py"`: `choices.action` = `rename` runs `rename <choices.id> <choices.label>`; `default` runs `set-default <choices.id>`. `auto` runs `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/style_learn.py" auto <choices.id> on\|off --workspace <workspace folder>` using `choices.on`. Read back in one plain line and refresh with both scripts above. |
| `captions` | Ask once, "The words on the video, or the text under the post?" The text under the post is `editor-superengine:caption-writer`; words on the video are `editor-superengine:reel-captions`. |
| `broll` | Invoke `editor-superengine:reel-broll`; use the client's clips on the Beat Map tab. |
| `qa` | Invoke `editor-superengine:reel-canvas-build`; follow its `references/qa-check.md` for that reel (pre check, then the full check on the latest Master when one exists). |
| `handoff` | Invoke `editor-superengine:pro-editor-handoff` with the client's `choices.editor`: DaVinci Resolve or another editor's files. |
| `trial` | Invoke `editor-superengine:reel-trials` from the approved cut; read `trials-selection.json` after Send and report keep/skip in plain words. |
| `cover` | Invoke `editor-superengine:reel-cover`; prepare candidates, open the Cover Picker, then apply the client's Send. |
| `goldmine` | The router's not-built line plus its one follow-up (`${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/SKILL.md`, "Not built yet"). |

At the start of every editing turn (including a direct skill run), inspect each configured reel's `hub-requests.json` for controls entries not yet marked `handled_at`. Across reels, the last controls entry wins by ISO `at` (within a file, later entries break ties). For `kind: "controls"` and `value: "simple"|"advanced"`, run the doctor with `--set-controls <value>`, then mark the pending controls entries `handled_at` with the current ISO time, preserving every entry and all other requests. Run both refresh commands above. Process these before a new chat controls request so the client's current ask wins. The config is the single source of truth; the browser cache is overwritten from it on every board load. A hub flip applies immediately to the open hub and its loaded iframes, posts the timestamped request, and follows the saved config on the next load. The client never types a command.

The page serializes list updates and re-reads disk before appending, including repeated clicks. A failed POST
keeps the draft and exposes a copy-to-paste line with the payload. It never claims a failed Send succeeded.
The existing server offers whole-file writes, so simultaneous writes from separate browsers are not a transaction.
Use one active hub when sending requests.

## Goldmine

Goldmine uses the workspace's `reel-build/goldmine-run.json`, or the active shortform brand state's `project_path`.
The current pointer is authoritative: missing compute exports show the credits empty state, never stale/sample
numbers. `n` is the export's `corpus.reels_total`, alongside the manifest's breakout count.
