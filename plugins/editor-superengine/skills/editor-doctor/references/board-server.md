# Editor boards: starting, recovering and extending the board server

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
3. Open the board in the Browser pane with `preview_start`, using the printed URL plus the board and reel:
   `{url}editor/<board>/?reel=<reel>`, e.g. `http://127.0.0.1:8747/editor/cut-board/?reel=<reel>`.
   `<reel>` is the reel's folder name under the workspace's videos folder.

It copies the boards into the workspace first (the same work as `board_sync.py`, below), takes the port from
`ports.board` in `editor/editor.config.json` (8747) and picks any free port when that one is busy. It stops by
itself about 5 minutes after the last board closes, or 15 minutes after starting when no board ever opens, so it
never runs forever. Starting it again is always safe.

To copy or refresh the boards without starting the server:
`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/board_sync.py"`.
It prints one plain line per board ("copied", "refreshed", "up to date", or "not built yet, nothing to copy").
A refresh overwrites only the board's own template files; saved work and the client's files are never touched.

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

## Endpoints (for the boards that later steps port)

The URLs stay the same whatever folders `paths.editor` and `paths.videos` name on disk.

| Request | What it does |
|---|---|
| `GET /editor/<board>/<file>` | The board's shared copy, from `<paths.editor>/<board>/` |
| `GET /videos/<reel>/<file>` | The reel's files, from `<paths.videos>/<reel>/`. HTTP Range answers 206, so video seeking works |
| `GET /videos/<reel>/<board>.state.json` | The board's saved state (404 until the first save) |
| `POST /videos/<reel>/__state?name=<board>` | Saves the JSON body as `<board>.state.json` in the reel folder; the previous file becomes `<board>.state.json.prev` (one kept). The reel folder must already exist |
| `POST /videos/<reel>/__save?board=<board>&name=<file>` | A Send output: saves the JSON body as `<file>` in the reel folder (no `.prev`). `<file>` must be in that board's `writes` list in `boards.json`. The reel folder must already exist |
| `POST /heartbeat` | Keeps the server running; body `{}` |

- Every request needs Host `127.0.0.1:<port>` or `localhost:<port>`. Every POST needs the page's own Origin,
  `Content-Type: application/json` and a JSON body of at most 2 MB. Anything else is refused (403, 400 or 413).
- Only the boards listed in `scripts/boards.json` are served or saved, and `__save` writes only names in a board's
  `writes` list. Dotfiles, `..` and symlinks that lead out of
  a board or reel folder are refused. JSON, HTML and JS are never cached.
- Send outputs (what a board hands to Claude, e.g. `selection.json`) use `__save`, never `__state`. A board that
  needs a new output file adds its name to its `writes` list in `boards.json`; never change the server.
- Boards load `./board-client.js`, which does the loading, saving, heartbeat, the banner and `mergeCues`:
  `const bc = BoardClient.create({board: "cut-board"}); const saved = await bc.load(); bc.save(state);`
  `BoardClient.mergeCues(saved.cues, freshCues)` refills cues by beat and keeps a saved cue whose beat is gone,
  flagged `unmatched`.

## Adding a board (later steps)

Put the board's files in `skills/<owning-skill>/boards/<board>/` (its page is `index.html`). The folder name must
be one of the nine boards in `skills/editor-doctor/scripts/boards.json`, which also names each board's owning
skill and template folder. Never change the server: the next start or `board_sync.py` copies the new template.

## Porting an old Content board (S4b, S5, G1)

The old boards lived in each reel's folder and used relative URLs. In the shared copy:

- The folder is the whitelisted name (`cut-board`, `tweak-board`, `sound-board`, `grade-board`), and the page is `index.html`.
- State goes through `BoardClient`, never relative URLs: `bc.load()` replaces `fetch('cut.state.json')`, and
  `bc.save(S)` replaces `fetch('__state?name=cut', ...)`. The file becomes `<board>.state.json`
  (`/videos/<reel>/__state?name=<board>`), and its backup is `<board>.state.json.prev` (it was `.state.prev.json`).
- A bare `fetch('__save', ...)` becomes `fetch('/videos/' + encodeURIComponent(reel) + '/__save?board=<board>&name=selection.json', ...)`
  with the same JSON Content-Type.
- Other reel files (config, audio, video, waveforms) load from `/videos/<reel>/<file>`; the reel comes from `?reel=`.

## When it fails

- `✗ Editor boards: ...` means it couldn't start; the line says why. Run the same command once more.
- A second failure, or a board that still won't load: the failure report in SKILL.md, with step `boards` and the
  `✗` line (or what the board shows) as the error line.
