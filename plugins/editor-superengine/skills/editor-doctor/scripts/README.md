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
`EDITOR_SE_HOME` overrides it (tests). `state.json` there records each component's version, URL and sha256,
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
