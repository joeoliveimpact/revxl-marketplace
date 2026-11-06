# editor-doctor installer (F1)

Claude runs `sh install.sh` once; the client never types a command. It needs only curl, tar, unzip and
sha256sum (shasum on macOS). It never uses a system Python, Node or ffmpeg.

| File | Role |
|---|---|
| `install.sh` | POSIX sh. Downloads the pinned uv, which installs a private Python 3.12 and the venv, then runs `install.py` |
| `install.py` | Everything else, from the union of the skills' `deps.json` manifests |
| `pins.json` | Every download: URL + sha256 per OS (win-x64, mac-arm64, mac-x64) |
| `python/*.in` | Per-engine Python requirements (`align.in` is shared) |
| `python/*.lock.txt` | The same, hash-locked with `uv pip compile --generate-hashes` (`--universal`; `parakeet-gpu` for Windows only); installed with `--require-hashes` |

State folder (outside the plugin): Windows `%LOCALAPPDATA%/revxl/editor-superengine`, macOS
`~/Library/Application Support/revxl/editor-superengine`, Linux `${XDG_DATA_HOME:-~/.local/share}/revxl/editor-superengine`.
`EDITOR_SE_HOME` overrides it; a Windows default over 115 characters gets `home-pointer.txt` naming the folder used (runtime.py). `state.json` there records each component's version, URL and sha256,
the transcription engine and the `align_words` status. `skills/_shared/runtime.py` reads it.
Beside the engine, `pick_facts` caches what the pick used (OS, arch, macOS major, NVIDIA GPU + name, the config
`language`). `--engine auto` keeps the recorded engine until a successful read shows one of those changed; a failed
GPU check never changes it. `--repick` (on `install.sh` or the doctor `check_deps.py`) picks again, and retries a
Parakeet that once fell back to faster-whisper. The doctor's `--set-nle mcp|resolve|none|auto` records the client's
hand-off choice in `editor/editor.config.json` (`nle_source` = `manual`; `auto` returns to detection).

Engines (one per machine, one venv): `parakeet-gpu` (Windows + NVIDIA), `parakeet-cpu` (Windows without NVIDIA,
Apple Silicon on macOS 14+), `faster-whisper` (the backup: Intel Macs, older macOS, or when Parakeet fails to
install under `--engine auto`). Intel Macs get no torch, so `align_words` is skipped there.

Not fetched, on purpose: whisper.cpp and its ggml models. The editor never calls `hyperframes transcribe`
(it needs a `whisper-cli` that no pin ships); transcription is Parakeet or faster-whisper in the venv.

## Building boards on the board server (build lanes only)

For whoever builds or ports a board. Starting, restarting and recovering the boards is in `../references/board-server.md`.

### Endpoints

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
- Only the boards listed in `boards.json` are served or saved, and `__save` writes only names in a board's
  `writes` list. Dotfiles, `..` and symlinks that lead out of
  a board or reel folder are refused. JSON, HTML and JS are never cached.
- Send outputs (what a board hands to Claude, e.g. `cut-selection.json`) use `__save`, never `__state`. A board that
  needs a new output file adds its name to its `writes` list in `boards.json`; never change the server.
- Boards load `./board-client.js`, which does the loading, saving, heartbeat, the banner and `mergeCues`:
  `const bc = BoardClient.create({board: "cut-board"}); const saved = await bc.load(); bc.save(state);`
  `BoardClient.mergeCues(saved.cues, freshCues)` refills cues by beat and keeps a saved cue whose beat is gone,
  flagged `unmatched`.

### Adding a board

Put the board's files in `skills/<owning-skill>/boards/<board>/` (its page is `index.html`). The folder name must
be one of the nine boards in `skills/editor-doctor/scripts/boards.json`, which also names each board's owning
skill and template folder. Never change the server: the next start or `board_sync.py` copies the new template.

### Porting an old Content board (S4b, S5, G1)

The old boards lived in each reel's folder and used relative URLs. In the shared copy:

- The folder is the whitelisted name (`cut-board`, `tweak-board`, `sound-board`, `grade-board`), and the page is `index.html`.
- State goes through `BoardClient`, never relative URLs: `bc.load()` replaces `fetch('cut.state.json')`, and
  `bc.save(S)` replaces `fetch('__state?name=cut', ...)`. The file becomes `<board>.state.json`
  (`/videos/<reel>/__state?name=<board>`), and its backup is `<board>.state.json.prev` (it was `.state.prev.json`).
- A bare `fetch('__save', ...)` becomes `fetch('/videos/' + encodeURIComponent(reel) + '/__save?board=cut-board&name=cut-selection.json', ...)`
  with the same JSON Content-Type.
- Other reel files (config, audio, video, waveforms) load from `/videos/<reel>/<file>`; the reel comes from `?reel=`.
