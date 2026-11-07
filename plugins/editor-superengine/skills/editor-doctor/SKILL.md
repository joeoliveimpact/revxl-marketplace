---
name: editor-superengine:editor-doctor
description: Sets up and checks the editor's tools, and starts or restarts the editor boards. Use for first-time setup, "is the editor ready", "check the editor's setup or tools", a missing or broken tool, after a plugin update, when another editor-superengine skill says the setup is missing, "open my editor hub", or "start my editor boards" / "restart my editor boards" (or a pasted "Restart my editor boards ..." line). NOT for checking the camera, light or sound before filming (that's recording-preflight).
---

# editor-doctor: set up and check the editor's tools

## Output contract (every run, in this order)

1. One plain line per STATUS line the doctor prints: ✓ for ok, ⚠ for warn, ✗ for missing. Use plain words. Never paste STATUS or FIX text, file names, paths or JSON to the client.
2. Under every ⚠ or ✗: what Claude is doing about it, or the one thing the client does (from its FIX line).
3. The transcription engine and why, from the `engine` line. On the backup (faster-whisper), show the retake warning from its FIX line word for word.
4. DaVinci Resolve: only when the `nle` line says `resolve`, say the Resolve hand-off can be offered later. Don't build or start it. With `nle none`, say nothing about Resolve or a hand-off unless the client asks; then explain the `resolve-*` lines. When the `nle` line says `chosen by you`, it is the client's own choice: confirm it in one line, and don't argue with it.
5. A last line: "The editor is ready", or what still stops it.
6. On any failure you can't fix in two tries: what went wrong in plain words, then the failure report offer below.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on.
- Re-running is safe. The setup and the doctor skip what is already in place, and a stopped download resumes. Never delete the state folder or `editor/` files to start fresh.
- Never start DaVinci Resolve, and never use a DaVinci Resolve tool or MCP here. The check only reads files.
- `EDITOR_SE_MASK` is for tests only. Never set it for a client.

## Ground rules

- **The client never types a command.** Claude runs each command below in the Bash tool, from the client's workspace folder, as one command. Windows and macOS run the same commands.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes.
- The first setup downloads up to about 5 GB. That can take 10 to 40 minutes on a slow connection. Run it with `run_in_background` and wait for it to finish. Tell the client it is working and roughly how long it takes.
- Plain English for a busy coach. Gloss a term once, e.g. "transcriber (turns speech into timed words)".
- Details (the STATUS format, every component, the config keys, where files live, how Resolve is checked): `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/doctor-details.md`.

## 1. Setup (only when `<editor python>` doesn't exist yet)

`sh "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/install.sh"`

- It ends `✓ Editor setup is ready`: go to step 2.
- It prints `Linux isn't supported yet (Windows and macOS are).`: tell the client that, and stop.
- A line starting `✗ Editor setup:`: it says what failed and what to do. A download or connection problem: run the same command once more. Anything else, or a second failure: the failure report, with step `setup` and that line as the error line.
- A `⚠ Transcription needs macOS ...` line is not a failure. The setup carries on without transcription, and the doctor reports which parts are off.

## 2. Doctor (the machine test, the engine, the checks)

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/check_deps.py"`

It runs the machine test, picks the engine, and has the setup install that engine. If Parakeet won't install, it switches to the faster-whisper backup and prints the retake warning. It then checks every part, checks Resolve, and writes `editor/editor.config.json` and `editor/.platform.json` in the workspace. It can also run setup downloads, so give it the same long wait as step 1. Only the `STATUS` and `FIX` lines at the end count; installer lines above them are progress.

- Exit 0: nothing required is missing (⚠ lines may still need a word to the client).
- Exit 1: something required is missing. `FIX` lines that start `Claude re-runs the setup:` all name the same command. Run the command after the colon once, then run step 2 again. Missing again: the failure report, with step `doctor` and the `STATUS` line (without the word STATUS) as the error line.
- Other FIX lines are things only the client can do, like updating macOS or a Resolve setting. Tell them in plain words, and offer to run step 2 again once they're done.
- A quick check with no installs, e.g. when another skill asks whether the editor is ready: add `--no-install` to the same command.
- The doctor keeps the transcription engine already chosen. It picks again only when the computer really changed (another graphics card, a macOS update, a new `language`). A graphics card check that doesn't answer never changes it; the `gpu` ⚠ line says so. When the client asks to choose the engine again, add `--repick` to the same command.
- When the client says which editor hand-off they want (DaVinci Resolve Studio, files for another editor such as Premiere or Final Cut, or none), record it with the same command plus `--set-nle resolve` (Resolve Studio, imported through its own connector), `--set-nle mcp` (another editor: files only) or `--set-nle none`. Later doctor runs keep it. `--set-nle auto` hands the choice back to the doctor's Resolve check. It only writes the config, so it is quick.
- Offline self-test, after every setup: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/offline_selftest.py"` (renders and transcribes with the network blocked; add `--static` for a quick no-render check any time). Each ✗ line says what failed.

## 3. Tell the client

Follow the output contract. Example: "✓ Video tools (ffmpeg, Chrome, the motion renderer) are in place. ✓ Transcription runs on your NVIDIA graphics card (Parakeet). The editor is ready."

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.1.0 --skill editor-doctor --step '<setup, doctor or boards>' --error-line '<the error line from step 1 or 2>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

**If setup failed before the editor's Python existed** (`<editor python>` is missing), use `python3` in its place, or `python` if `python3` doesn't run. First check it with `-c "import sys"`. A Windows Store stub that prints an install message doesn't count. The report script needs only plain Python. If neither runs, skip the draft. The details are already saved in `editor-superengine/reports/report-body.md`, so tell the client where that file is so they can email it to the plugin's support.

**Start or restart my editor boards** (also a pasted "Restart my editor boards and save this ... state" line from a board): follow `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md`.

## Open my editor hub

For "Open my editor hub", refresh its data, start or reuse the board server and open `editor/hub/` in the Browser
pane. Follow `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/hub.md` for the commands and Send handling.
Claude runs the commands; the client never types them.
