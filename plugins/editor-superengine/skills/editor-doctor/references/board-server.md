# Editor boards: starting and recovering the board server

The boards (Cut, Tweak, Sound, Beat Map, Sketches, Grade, Hub, Look Picker, Cover Picker) are web pages the
client clicks through in the Browser pane. One small local server per workspace serves them and saves each
board's work to disk. The client never types a command; Claude runs everything below in the Bash tool from the
client's workspace folder. `<editor python>` is the editor's own Python (see the Ground rules in SKILL.md), never a
bare `py`, `python` or `python3`.

## Start or restart the boards

1. Run this with `run_in_background` (it keeps running while boards are open):

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/board_server.py"`

2. Wait for its one line, `Editor boards: http://127.0.0.1:<port>/`. If a server for this workspace is already
   running, the line names that one and the command ends at once; that is normal.
3. Open the board inside the hub in the Browser pane with `preview_start`:
   `{url}editor/hub/?reel=<reel>&board=<board id>&view=full`, e.g. `http://127.0.0.1:8747/editor/hub/?reel=<reel>&board=cut-board&view=full`.
   `<reel>` is the reel's folder name under the workspace's videos folder.
   When the hub is already open in the Browser pane, the same address switches it to that board.
   The hub is the client's one window: never open a second tab or a bare board or video address for them.
   A board's own page (`{url}editor/<board>/?reel=<reel>`) still loads; it is for tests and direct links only.

It copies the boards into the workspace first (the same work as `board_sync.py`, below), takes the port from
`ports.board` in `editor/editor.config.json` (8747) and picks any free port when that one is busy. It stops by
itself about 5 minutes after the last board closes, or 15 minutes after starting when no board ever opens, so it
never runs forever. Starting it again is always safe.

To copy or refresh the boards without starting the server:
`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/board_sync.py"`.
It prints one plain line per board ("copied", "refreshed", "up to date", or "not built yet, nothing to copy").
A refresh overwrites only the board's own template files; saved work and the client's files are never touched.

## Open my board for a reel

H-HUB-1 deliberately opens boards inside the hub so the client keeps reel context and the other boards together.

For "Open my <board> for <reel>", use the asked board's id: Cut Board `cut-board`, Tweak Board `tweak-board`,
Beat Map `beat-map`, Sketches `sketches`, Sound Board `sound-board`, Grade Board `grade-board`.
Refresh the hub data using `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/hub.md`, then start or reuse
the server with steps 1 and 2 above. Open `{url}editor/hub/?reel=<reel>&board=<board id>&view=full` in the Browser pane with
`preview_start`, URL-encoding the reel name. Tell the client: "Your <board> is open. Back to hub, at the top left, shows everything else."

## A pasted "Restart my editor boards" line

When the server stops while a board is open, the board shows a red banner with a line and a Copy button. The line
reads `Restart my editor boards and save this <board> state for reel <reel>: <JSON>`. When the client pastes it:

1. Start the boards (steps 1 and 2 above).
2. With the Write tool, put the JSON after the colon, exactly as pasted, in `editor/restore.tmp`.
3. Save it through the server, so the previous save is kept as `.prev` (`<url>` is the printed URL without its
   trailing slash):
   `curl -s -X POST -H "Origin: <url>" -H "Content-Type: application/json" --data-binary "@editor/restore.tmp" "<url>/videos/<reel>/__state?name=<board>"`
   It answers `{"ok": true, ...}`.
4. Reopen the board (step 3 above) and tell the client their work is back.

A line without JSON (`Restart my editor boards (the <board> for reel <reel> lost its connection).`) means
nothing was unsaved: start the boards and reopen that board.

## When it fails

- `✗ Editor boards: ...` means it couldn't start; the line says why. Run the same command once more.
- A second failure, or a board that still won't load: the failure report in SKILL.md, with step `boards` and the
  `✗` line (or what the board shows) as the error line.
