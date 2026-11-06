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

## What Claude reads after a Send

All Sends use `/videos/<reel>/__save?board=hub&name=<file>`. A successful Send records a request; it does not
start tools. Read the whole file before acting and keep earlier entries when acknowledging a request.

| File | Meaning and next action |
|---|---|
| `review.json` | `{ "approve": true, "preview": "<latest finished preview filename>", "note": "<text>", "sent_at": "<ISO>" }`. The page plays the newest finished `renders/* Preview 720p - *.mp4`, excluding `.partial.mp4`, and approval works before a master exists. Send notes uses `approve: false`. Read the note and make requested fixes. On an approve, invoke `editor-superengine:reel-canvas-build`: it records the OK with `--from-review` (build.md section 3) and makes the final video. A notes-only Send is a change request for canvas-build. When present, the page also shows the master and QA result. Approval does not publish anything. |
| `reel-notes.json` | Append-only list of note text, kind and player time. Read these before working on the reel and apply the client's instructions. |
| `hub-requests.json` | Append-only request objects (`at`, `reel`, `skill`, `ask`, `choices`). Use the table below, keyed on `skill`. Quick adjustments are requests with the chosen values, not fabricated board selections. |

| `skill` | What Claude does |
|---|---|
| `health` | This skill's doctor (step 2). |
| `adjust-cut` | Invoke `editor-superengine:reel-first-cuts` (the gaps). |
| `adjust-grade` | Invoke `editor-superengine:reel-grade`. |
| `adjust-sound` | Invoke `editor-superengine:reel-sound-pass`. |
| `style` | Ask "Use these choices as the default for your next reels?"; on yes, follow "make it my default" in `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/style.md`. Nothing else. |
| `captions` | Ask once, "The words on the video, or the text under the post?" The text under the post is `editor-superengine:caption-writer`; words on the video get the router's not-built line. |
| `cover`, `qa`, `broll`, `trial`, `goldmine` | The router's not-built line plus its one follow-up (`${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/SKILL.md`, "Not built yet"). |

The page serializes list updates and re-reads disk before appending, including repeated clicks. A failed POST
keeps the draft and exposes a copy-to-paste line with the payload. It never claims a failed Send succeeded.
The existing server offers whole-file writes, so simultaneous writes from separate browsers are not a transaction.
Use one active hub when sending requests.

## Cockpit agreement

Stage and open-Send rules are read from `hooks/mod/logic.ts`, including optional Grade, sent/locked state and
downstream timestamps. The Cockpit keeps its baseline and acknowledgements in private stores, which a disk-only
script cannot access. When those are available to Claude, export the current workspace's baseline and its ack map
as `<paths.editor>/hub/cockpit-state.json`: `{"baseline": 1234, "acked": {"reel-01/cut-selection.json": 1235}}`
(timestamps are milliseconds), then refresh. Without a baseline the hub follows the Cockpit rule: no open Sends.
Hub requests still appear in the request queue. Automatic Cockpit routing of these files belongs to its Send router.

Goldmine uses the workspace's `reel-build/goldmine-run.json`, or the active shortform brand state's `project_path`.
The current pointer is authoritative: missing compute exports show the credits empty state, never stale/sample
numbers. `n` is the export's `corpus.reels_total`, alongside the manifest's breakout count.

## Porting a board

See [Building boards on the board server](../scripts/README.md#building-boards-on-the-board-server-build-lanes-only).
Keep templates under the manifest's owning skill; the hub template is `skills/editor-doctor/boards/hub`.
Board tabs and their stages/order come from `boards.json`. A missing client template says "not built yet".
Master review is `editor/hub/review.html?reel=<reel>`, never a render folder listing.

Use `BoardClient.create({board: "cut-board"})` for board state. Send the real whitelisted filename, for example
`/videos/<reel>/__save?board=cut-board&name=cut-selection.json` or
`/videos/<reel>/__save?board=grade-board&name=grade-selection.json`. State is `<board>.state.json` with one `.prev`;
Sends are distinct files. Templates must not include generated `hub-data.json`, filmstrip frames or client state:
board_sync overwrites only template-owned files and preserves these generated artifacts.
