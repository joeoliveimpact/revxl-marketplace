# editor-doctor details

The reference for `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/SKILL.md`. The code is the source of truth:
`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/check_deps.py` (the doctor),
`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/install.sh` and `install.py` (the setup),
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/runtime.py` (paths, the engine pick, the test-only masks).

## Contents
- STATUS lines
- The engine
- Where the files live
- editor.config.json
- DaVinci Resolve check
- Tests

## STATUS lines (stable; S13 Health and the Cockpit parse them)

```
STATUS <component> ok|warn|missing <plain detail>
FIX <component> <plain fix for this OS>        <- right after every warn or missing line
```

- `missing` on a required part makes the doctor exit 1. `warn` never does.
- Installer progress lines can come before the STATUS block. Parsers read only lines that start `STATUS ` or `FIX `.
- The same lines are saved as data in `editor/.platform.json` under `status`.
- A FIX for a missing installed part is always `Claude re-runs the setup: sh "<plugin>/skills/editor-doctor/scripts/install.sh" --engine <engine>`. The engine is the one that is installed (or the one the machine test picked). Claude runs it; the client never does.

| Component | What is checked |
|---|---|
| `machine` | OS, arch, macOS version, NVIDIA GPU, RAM total and free (always ok; missing only on Linux) |
| `gpu` | only when the NVIDIA check didn't answer: a warn saying the current engine was kept (see "The engine") |
| `state-folder` | only when the setup's pointer is in use: the folder the editor is installed in instead of the usual one (see "Where the files live") |
| `python` | the editor's own Python 3.12 and its venv, built from the state folder's managed Python |
| `ffmpeg` | ffmpeg + ffprobe present; zscale, tonemap, psnr and the needed encoders |
| `node` | Node.js at the pinned version |
| `hyperframes` | HyperFrames 0.8.184 installed from this plugin's lockfile |
| `chrome` | chrome-headless-shell at the pinned version |
| `cutout-model` | u2net_human_seg by sha256 |
| `transcriber` | the engine's hash-locked Python packages match the lock and load |
| `model-parakeet` / `model-faster-whisper` | the engine's model files by sha256 |
| `align` | align_words: torch + transformers load and wav2vec2 matches by sha256 (warn on Intel Macs: skipped) |
| `engine` | which engine and why; on the backup, the retake warning as its FIX |
| `engine-switch` | only when this workspace's `language` needs the other engine than the one installed: a warn saying it is switching and reinstalling (see "The engine") |
| `resolve-installed`, `resolve-edition`, `resolve-version`, `resolve-scripting` | the Resolve requirements, all optional (warn, never missing) |
| `nle` | `resolve` or `none` from detection, or the client's own choice ("chosen by you"), as written to the config |
| `config` | editor.config.json written (missing if it holds broken JSON, which the doctor leaves alone) |

## The engine (TX-1, PB-11, hub rulings 11.04.26)

| Computer | Engine |
|---|---|
| Windows with an NVIDIA GPU | parakeet-gpu |
| Windows without one | parakeet-cpu |
| Apple Silicon, macOS 14 or newer | parakeet-cpu |
| Intel Mac, macOS 13 or newer | faster-whisper (the backup; the retake warning shows) |
| Apple Silicon below macOS 14, Intel Mac on macOS 12 or older | none: "Transcription needs macOS 14 (Intel: 13) or newer on this Mac. Update macOS to turn it on." The setup skips the engine and doesn't fail. Parts that don't need transcription keep working, and the `engine` line names the parts that are off. |
| Linux | not supported: the setup prints "Linux isn't supported yet (Windows and macOS are)." and exits 0 with nothing downloaded |

Parakeet v2 understands English only. When `language` in editor.config.json is set to anything other than English, the pick is faster-whisper, which handles many languages. Unset counts as English. When Parakeet won't install, the setup falls back to faster-whisper and keeps it on later runs. After a fallback, `--repick` retries Parakeet; if it still won't install, the setup falls back again and the retake warning shows.

**The pick is kept (S1b-fix).** `state.json` in the state folder records `pick_facts` beside `engine`: `{"os", "arch", "macos_major", "gpu", "gpu_name", "language"}` (`gpu_name` from `nvidia-smi -L`). Doctor and setup runs keep the recorded engine. They pick again only when:

- a successful read shows one of those facts changed (another graphics card, a macOS update, a new `language`), or
- the client asks: Claude adds `--repick` to the doctor command (`install.sh --repick` does the same for the setup).

A GPU read that fails is never a change: `nvidia-smi` times out, exits non-zero, prints no GPU line, or is missing where a GPU was recorded. The engine stays, no packages are installed or swapped, the setup prints the same warning, and STATUS shows `gpu warn` with its fix. With nothing cached (the first run, or a state folder from before this change) the pick runs as before. The `gpu` test mask counts as a successful "no GPU" read.

**One pick per language (A2).** `language` lives in each workspace, but the state folder is shared by the whole computer. So `state.json` keeps one cached pick per language under `picks` (`en` for English or unset, else the language's main code, e.g. `es`), and the top-level `engine` is what is installed now. Each language's pick stays stable, and a failed GPU read keeps that language's engine. A re-run in the same workspace installs nothing.

**Known limit: one shared venv.** All languages share one set of transcriber packages. Moving to a workspace whose language needs the other engine (English uses Parakeet, other languages faster-whisper) reinstalls the packages, and moving back reinstalls them again. The doctor says so before the setup starts, and STATUS shows it:

`STATUS engine-switch warn This workspace uses Spanish (es), so the transcription engine is switching to faster-whisper; this reinstalls about 1-3 GB once.`

## Where the files live

- **In the workspace (the cwd):** `editor/editor.config.json` and `editor/.platform.json`.
- **In the state folder:** the machine-level toolchain and models, plus the saved style `styles/default.json`. The state folder is `%LOCALAPPDATA%\revxl\editor-superengine` on Windows and `~/Library/Application Support/revxl/editor-superengine` on macOS. When that Windows path is over 115 characters, the setup installs into a shorter folder (`EDITOR_SE_HOME`) and leaves `home-pointer.txt` in the usual one, naming it; the scripts follow it.

## editor.config.json (setup and machine settings only; taste lives in the saved style)

| Key | Default | Written by | Read by |
|---|---|---|---|
| `schema` | 1 | the doctor | everything that reads the config |
| `engine` | null until the machine test | the doctor: the engine that actually installed (`none` on old macOS) | transcription (S3), STATUS |
| `language` | null (unset = English) | not written by the doctor | the engine pick (doctor and setup) |
| `nle` | `auto` until detection | the doctor: `resolve` or `none` from detection while `nle_source` is `auto`; `--set-nle` writes the client's choice (`mcp`, `resolve` or `none`) (`mcp` = files for another editor) | the Resolve hand-off offer (S12) |
| `nle_source` | `auto` (missing counts as `auto`, for older configs) | the doctor: `auto`, or `manual` after `--set-nle mcp`, `resolve` or `none` (`--set-nle auto` returns to `auto`). Only `auto` is re-detected; a `manual` nle is kept and reported as "chosen by you" | the Resolve hand-off offer (S12) |
| `ports.board` | 8747 | default | the boards' free-port fallback (S4a) |
| `voice_cleanup` | `free` (or `auphonic`) | default | voice clean-up (S5) |
| `paths.editor`, `paths.videos` | `editor`, `videos` (relative to the workspace) | default | boards and the Cockpit |
| `cuts.beat_ms` | 300 | default | the Cut Board's "Pause after commas" starting value (make_board.py) and gaps.py's beat (S4b) |
| `grade`, `scenes`, `broll`, `music`, `transitions`, `cover`, `trial`, `three` | `{}` | added by later steps | their own steps |

On every run the doctor adds missing keys and keeps every existing value. It sets only `engine`, `nle` and `nle_source`, and keeps a `manual` nle.
The saved style skeleton is written once, only if missing, and never overwritten:
`{"schema":1,"style_id":null,"accent":null,"font":null,"look":null,"transitions":{"allowed":[],"sfx_pair":null}}`.
For taste, the saved style overrides the config.

## DaVinci Resolve check (PB-40; read-only, never opens Resolve)

The hand-off needs all four of: installed, Studio, version 21.1 or newer, and external scripting set to Local or Network. Anything less gives `nle: none`.

| | Windows | macOS |
|---|---|---|
| Installed | `%ProgramFiles%\Blackmagic Design\DaVinci Resolve\Resolve.exe` | `/Applications/DaVinci Resolve/DaVinci Resolve.app` (or `DaVinci Resolve Studio.app`) |
| Version | registry `HKLM\SOFTWARE\Blackmagic Design\DaVinci Resolve` value `Version` | the app's `Contents/Info.plist` `CFBundleShortVersionString` |
| Studio | a `*studio*.lic` file in `%ProgramData%\Blackmagic Design\DaVinci Resolve\Support\.license` (names only, never read) | the same licence folder under `/Library/Application Support/Blackmagic Design/DaVinci Resolve/`, or "Studio" in the bundle name |
| External scripting | `System.Scripting.Mode` in `%APPDATA%\Blackmagic Design\DaVinci Resolve\Preferences\config.dat` (0 None, 1 Local, 2 Network) | the same key in `~/Library/Preferences/Blackmagic Design/DaVinci Resolve/config.dat` |

- The scripting value is the one Resolve last saved. Whether a live connection works can only be confirmed while Resolve is open, and the STATUS line says so.
- If the key has never been saved, the line is a warn that says the doctor can't tell. Its fix: in Resolve Studio open DaVinci Resolve > Preferences > System > General, set External scripting using to Local, click Save, then Claude re-runs the doctor.
- A Studio licence on a USB key leaves no licence file, so it shows as not Studio.

## Tests

- `<editor python> -X utf8 -I ".../check_deps.py" --selftest` runs offline in temp folders.
- `tests/editor/doctor-test.sh` in the marketplace repo runs the spec done-test on copies of installed state folders.
- Test-only masks (`EDITOR_SE_MASK=gpu,parakeet,resolve`) are documented in one place, the runtime.py docstring. They are never set for a client.
