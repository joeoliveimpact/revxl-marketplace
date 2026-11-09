# Master clock

Pads the audio gaps in a master joined from several clips, then proves the sound now runs on the
same clock the cut is rendered on.

## When

- A master joined from more than one clip (a Tella pull, takes stitched into one file, a
  `raw/_concat.txt`), before the Stage 0 probe.
- On an existing cut: words chopped only after the first clip, the audio a fraction of a second
  shorter than the video, a last word "clamped to the WAV end". Stop and run this.
- Not for single-clip raws: they already run on one clock.

## Run it

`<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes.

```bash
<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/clock_fix.py" --concat raw/_concat.txt -o "raw/<Reel> Master Raw (audio gap-padded) - MM.DD.YY.mov"
```

For a concat that already exists, pass the mp4 instead of `--concat`. The video is stream-copied
untouched and only the audio gaps are padded; then the script checks about 12 speaking windows
and fails on any lag over 2 ms.

The script leaves the gap-padded .mov under its final name only after a passing proof. If it exists, use it; never rebuild it.

## Exit codes

| Exit | Means | What Claude does |
|---|---|---|
| 0 | The clocks agree | The `.mov` is now the RAW for every later stage (probe, transcribe, render). Extract WAVs from it plainly. |
| 1 | The proof failed | Stop; nothing is left under the final name. Never hand that master to a later stage. |
| 2 | One plain error line | A missing or unreadable file: check the path and run again. "The editor's setup isn't finished": run `editor-superengine:editor-doctor`. |
| 3 | "Not enough clear speech to check the sound against the picture" | Nothing was saved. Check the master's sound plays and isn't muted, then run again with `--points 24`. Still 3: stop and tell the client the sound couldn't be checked; never cut the unfixed master. |

After two failed tries, offer the reel-first-cuts failure report with step `clock fix`.

## What the client hears

Plain words, per `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-user-hears.md`:
"Your clips were joined with tiny gaps in the sound, so I lined the sound back up with the
picture and checked it at several spots." Never the file path, never "CLOCKS AGREE", and no
millisecond tables unless they ask.

## Why

A stream-copied multi-clip master has two clocks. Each clip's audio runs a few tens of ms short of
its video, so every join leaves an audio gap. The render cuts on the pts clock (`atrim`); a plain
WAV drops the gaps, so everything measured on it drifts behind the render by the gaps so far.
Fix the master once, never the consumers.

## Common mistakes

| Mistake | Reality |
|---|---|
| `aresample=async=1` alone | Its default `min_hard_comp` is 0.1 s, so gaps under 100 ms stay (measured: still 52 to 99 ms adrift). The script uses 0.005. |
| Join the audio gaplessly instead | Each later clip's audio then leads its video by the gaps so far: lip sync off by up to half a second. The pts clock is the true one. |
| Skip the proof because the durations match | Matching durations prove nothing. The script correlates, and skips room-tone windows that would read a false lag. |
| Find render splices by summing segment durations | The concat filter pads audio to frame-quantised video, up to a frame per join. Correlate each segment into the render. |

## Real-world impact

One test reel (09.17.26): 11 Tella clips drifting 52 ms after clip 1 to 479 ms by clip 11. Scrub v3
had 48 of 68 splices on speech; after this fix and a rebuild, 3, all seams of the editor's own strikes.

## Self-check

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/clock_fix.py" --selftest`
builds a synthetic multi-clip master with planted gaps and proves the fix.
