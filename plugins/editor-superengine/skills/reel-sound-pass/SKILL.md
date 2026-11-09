---
name: editor-superengine:reel-sound-pass
description: Finishes the sound of a picture-locked reel. Use on "sound pass", "add music", "pick a track", "background music under my voice", "add sound effects", "mix the sound", "master the audio", "clean up my voice", or "run Auphonic". The client picks every sound on the Sound Board, then the editor bakes the stems, cleans the voice (free by default, Auphonic only after the client says yes to its cost), keeps the board's levels, masters to -14 LUFS, puts the sound back on the untouched picture last, and checks every cue made it. NOT for picture edits, captions or the first cut, which come before this.
---

# reel-sound-pass: the reel's finished sound

## Output contract (every run, in this order)

1. What will happen, in one or two plain lines: the free voice clean-up, or the Auphonic plan (what runs, what it costs) and the question "Say yes to go ahead."
2. When there is a sound library: the Sound Board, open in the Browser pane, with the cues Claude proposes. The client decides.
3. The delivered file, `videos/<reel>/sound/final.mp4`, in plain words: how loud it is, that the picture is untouched, and that every sound effect came through (or which one didn't). When the reel has visuals (`videos/<reel>/beat-map.state.json` exists) and every check passed, also say the finished video with the visuals will use this sound as long as the cut and its colour stay the same. With no visuals planned, this file is the finished reel.
4. A short listening list (the loudest hits, the music stops, the closer).
5. "The mix is yours. Listen, then say ship or name the moment to change." On ship: with visuals, the next step is the final video (reel-canvas-build); without, the reel is done.

Speak to the client the way `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-coach-hears.md` says: no file names, paths, script names or raw check output.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke it again before going on.
- Re-running is safe. The mix reads the picture and the board's Send and writes only into `videos/<reel>/sound/`. A paid Auphonic result for the same voice track is saved and reused at no charge; a paid job is never started twice.
- If the picture changed after the board was made, the board and its cue times are stale: run step 2's `new_board.py` again with `--video "<the new locked picture>"`, then reopen the board. Reopening alone keeps the old picture.
- Follow sections 5 and 6 (Auto edit and controls in chat) of ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md.

## Ground rules

- **The client never types a command.** Claude runs every command with the Bash tool, from the client's workspace folder.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. If it doesn't exist, run `editor-superengine:editor-doctor` first.
- `<reel>` is the reel's folder name under the workspace's videos folder.

## Hard rules (always on)

1. **Nothing that costs money runs without the client's yes.** Auphonic goes: the plan (step 3), the client's yes, then the mix with `mix.py --voice auphonic --yes` (step 4). Never run `auphonic.py run` yourself. Claude passes `--yes` only after the client said yes to the plan lines, in this conversation, for this voice track: a new plan and a new yes whenever the voice track was made again (a new cut, a new bake, a different `--video`).
2. **The mix is the client's; the machinery only preserves it.** Their board picks are the ruling. A pick that looks wrong gets a question, with the measurement, never a fix.
3. **The picture is copied, never re-encoded.** The sound goes onto it last, and every check runs on the delivered file.
4. **The Auphonic key never shows.** Not in a command, the chat, a file Claude writes or a report. Claude never reads the key file.

## The flow

### 1. Sound library

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/sfx_ingest.py" fetch`

"No sound library yet": the mix ships voice only (skip the board, go to step 4). A failed download unpacks nothing; run it once more. `verify` re-checks the library; `add "<file>"` adds one of the client's own sounds (dead air trimmed, measured).

### 2. Sound Board

Read the cut and propose cues: each a moment with 2-3 candidate sounds, more than should ship, so the client cuts rather than accepts. Write them as JSON (`[{id, beat, short, why, time, candidates:[files]}]`) with the Write tool, then:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/new_board.py" --reel <reel> --cues <cues.json> [--stops <stops.json>] [--bed <bed file>]`

When the client sent the Beat Map (`videos/<reel>/beat-map-selection.json` exists), pre-fill the cues instead of writing them by hand: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/prefill_cues.py" --reel <reel> --out <cues.json>` proposes a transition at each look change and a hit on each marked word, never in the closer. Review them (keep more than should ship), then pass them to `new_board.py --cues`; they arrive undecided.

Start the board server and open `/editor/sound-board/?reel=<reel>` in the Browser pane, as `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md` says. The client auditions each cue against the picture, keeps or rejects, slides the music, sets stops and fades, then presses Send (it writes `sound-selection.json`; undecided cues are kept, never mixed).

Taste tips to offer, never rules: keep it subtle; long swooshes and echo tails rarely help; let the closer land in silence; one sound per moment, not two doubled. The board shows these too, and never blocks a choice.

### 2b. Music

The board's music row lists every track (Starter pack, Free library, Your track) with its level (-18 dB suggested) and the dip under the voice (6 dB suggested); both are options, never rules. Beat-sync on the music row is an option too (off by default): it starts the music on a beat and offers to snap cues to it; speech cuts never move. After the Send:

- `music_request` is `"free"` or `"own"`: walk the client through adding the track as `${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/references/music-library.md` says (`music_pick.py`, run like the `pick` line below: `add-free` records exactly the licence the download page shows; `add-own` for their own track), then run step 2's `new_board.py` command again with `--video "videos/<reel>/<picture_url>"` (`picture_url` is in `videos/<reel>/config.json`, a path inside the reel folder) and reopen the board.
- `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/music_pick.py" pick <reel>` writes the reel's licence row (`music.json`), plus `credits.txt` when the licence asks for a credit: give the client that line for the post caption.
- The mix refuses the final while the picked track has no complete licence row, or the client's own track lacks the "I have the rights" tick. Its line names what's missing; fix that, then mix again.

### 3. Voice clean-up choice

Free is the default (`voice_cleanup` in `editor/editor.config.json`). If the client wants Auphonic:

- No key yet: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/auphonic.py" --setup-key` opens an empty key file in their text editor. They paste the key, save, close and say done. Never ask for the key in the chat.
- `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/auphonic.py" plan "videos/<reel>/sound/voice.wav" --reel-dir "videos/<reel>"` prints the plan. Show its lines as they are and wait for the yes. If `sound/voice.wav` doesn't exist yet, make the stems first: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/bake.py" --reel <reel>`.

### 4. Mix

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/scripts/mix.py" --reel <reel> [--voice free|auphonic] [--yes]`

It stops on a nearly silent recording, bakes the stems from the board's Send, cleans the voice, keeps the board's levels, masters to -14 LUFS and a -1 dBTP peak, puts the sound on the picture, and checks the delivered file. If reel-first-cuts rendered again after the board was made (the cut master is newer than `videos/<reel>/config.json`), the board's cue times are stale: tell the client, propose the cues again on the new cut, rebuild the board (Re-invoke guard) and wait for a new Send before mixing. `--video` is only for exit 2.

- Exit 0: delivered. Tell the client in plain words.
- Exit 1: a check stopped it; the line says which. Nearly silent: ask whether the right microphone was recording. A sound effect that didn't come through: ask about that cue (often its level on the board).
- Exit 2: no picture found. Pass `--video`.
- Exit 3: Auphonic without the client's yes. Show the plan first.
- No Auphonic key: it says so and uses the free clean-up. Tell the client.

### 5. Listen

Give the client the listening list and the file in the Browser pane. Their ear beats every check; a passing check is not approval. A change goes back to the board (step 2) and the mix again.

Stage detail, the checks and why the split chain is the house path: `${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/references/sound-pass-details.md`. The board's own notes: `${CLAUDE_PLUGIN_ROOT}/skills/reel-sound-pass/references/sound-board.md`.

## What this skill will not decide

- Which sounds, where, how loud, which music, where it slides: the client decides on the board.
- Whether a suspicious pick is wrong: ask, with the measurement, and take the answer.
- Whether the mix is done: the checks qualify it; only the client's listen approves it.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.0 --skill reel-sound-pass --step '<library, prefill, board, music, mix, auphonic or master>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
