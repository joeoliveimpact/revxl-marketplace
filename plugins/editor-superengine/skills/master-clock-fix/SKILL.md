---
name: master-clock-fix
description: Use when a reel's source is several clips joined into one master (Tella pulls, concat demuxer, stream copy) BEFORE any probe, transcription, edit map or cut is built on it; or when a cut rendered from such a master chops the ends and beginnings of words everywhere after the first clip while every boundary gate reads green; or when a master's audio stream is shorter than its video, or the last word had to be "clamped to the WAV end".
---

# Master Clock Fix

## Output contract

Every run ends with, in this order:

1. The join receipt (each clip's audio/video gap), told to the client in plain words.
2. The fixed `.mov` path. It is now the RAW for every later stage.
3. The proof verdict: the worst lag and CLOCKS AGREE.

On FAIL (exit 1), stop. Never hand that master to any later stage.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on.
- Never rebuild a master whose gap-padded `.mov` already exists with a passing proof. Use it.

## Overview

A stream-copied multi-clip master has **two clocks**. Each clip's audio is a few tens of ms shorter
than its video, so the concat leaves an audio pts gap at every join. The render cuts on the pts clock
(`atrim`); a WAV extracted the normal way drops those gaps, so everything measured on it (envelope,
words, islands, segments) drifts behind the render by the accumulated gaps. **Fix the master once, at
build time. Never fix the consumers.**

## When to use

- Any master built from more than one clip, before Stage 0 of `reel-first-cuts`.
- Symptoms on an existing cut: chops on word edges only after the first clip; "audio ~0.5 s shorter
  than video on the concat"; a last word clamped to the WAV end; boundary gates green, ear says no.
- Not for single-clip raws (one clock already) and not for fixing A/V sync inside a clip.

## Do this

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/master-clock-fix/scripts/clock_fix.py" --concat raw/_concat.txt -o "raw/<Reel> Master Raw (audio gap-padded) - MM.DD.YY.mov"
```

For a concat that already exists, pass the mp4 instead of `--concat`. The script stream-copies the
video (generation 0 untouched), pads the audio gaps to PCM, then **proves** the output's plain WAV
clock equals the input's `atrim` clock at ~12 speaking windows. It exits 1 on any lag over 2 ms.
**The `.mov` is now the RAW for every downstream stage** (probe, transcribe, render, Resolve).
Extract WAVs from it plainly; they land on the right clock.

Self-check: `python "${CLAUDE_PLUGIN_ROOT}/skills/master-clock-fix/scripts/clock_fix.py" --selftest` builds a synthetic
multi-clip master with planted gaps and proves the fix (needs ffmpeg + numpy).

## Common mistakes

| Mistake | Reality |
|---|---|
| `aresample=async=1` alone | ffmpeg's `min_hard_comp` default is 0.1 s; gaps under 100 ms stay. Measured: still 52 to 99 ms adrift. Use `min_hard_comp=0.005`. |
| Concatenate the audio gaplessly instead | Clip N+1's audio then leads its video by the accumulated gap: lip sync off by up to half a second. The pts clock is the truthful one. |
| Skip the proof because durations now match | Durations matching is not evidence. Correlate. A reading on room tone can show a false lag; the script skips silent windows. |
| Locate render splices by summing segment durations | The concat filter pads audio to frame-quantised video (up to a frame per join). Correlate each segment into the render first. |
| "Clamp the last word to the WAV end" | That is the symptom. Stop and run this. |

## Real-world impact

One test reel (09.17.26): 11 Tella clips, gaps 35 to 90 ms each, drift 52 ms after clip 1 to 479 ms by
clip 11. Scrub v3 had 48 of 68 splices on speech; after the fix and a rebuild, 3 of 68, all of them
seams of the editor's own strikes. No gap rule or threshold could have fixed it.
