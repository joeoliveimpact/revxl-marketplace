---
name: editor-superengine:editor-start-here
description: The router for editor-superengine. Use when someone says "edit my reel", "cut this talking head", "first cut", "tighten the gaps", "design the hook", "motion comps", "where do I start with editing", or "editor superengine". Also use any time it is not yet clear whether the ask is about the spoken cut or the visuals. Names the pipeline order, sends the work to the right skill, and runs the dependency check before anything touches a file.
---

# Editor superengine: start here

Two build skills, one order, four shared references. This skill decides which one you are
in and checks the machine can run it.

## Pipeline order

```
raw recording
   -> reel-first-cuts      spoken edit: probe, transcribe, rulings, waveform gate,
                           gaps, render, silence budget, ear pass
   -> PICTURE LOCK         the cut is signed off and the timeline stops moving
   -> reel-motion-comps    visuals: directions, ladders, rulings from frames
```

**Nothing about the visuals starts before picture lock.** Every comp is timed against the
cut, so a cut that moves invalidates every timing derived from it.

**Sound design, music and captions come after motion comps and are not in 0.1.0.** If the
ask is a sound pass, mastering levels or burned-in captions, say so plainly rather than
improvising it here.

## Which skill

| The ask | Go to |
|---|---|
| "cut this", "build the A-roll", "make a first pass" | `reel-first-cuts` |
| "tighten the gaps", "the pause after X drags", "there's an orphan word" | `reel-first-cuts`, Stage 9 |
| "why does this sound clipped", "did the cut damage a word" | `reel-first-cuts`, Stage 3 |
| "how long is it", "speed it up", "1.15x" | `reel-first-cuts`, Stage 5 |
| "design the hook", "comp the intro", "direction options" | `reel-motion-comps` |
| "ladder the blur", "iterate this element" | `reel-motion-comps`, step 3 |
| "will this get covered by the Instagram UI" | `reel-motion-comps`, safe-zone pre-check |
| a sound pass, music, captions, compositing | not in 0.1.0, say so |

Invoke each with the Skill tool by its full name: `editor-superengine:reel-first-cuts`, `editor-superengine:reel-motion-comps`.

## The four shared references

| Reference | Applies when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md` | Always, before the first file. Duplicate the source, fewest generations, never judge picture on a proxy, load the governing docs first. |
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/preview-before-render.md` | Before any render, export or master. Cheap previews go to the reviewer first. |
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/frame-zero-hook.md` | Any time the hook frame is being designed or checked. |
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/design-prompt.md` | Handing a design canvas the art-director brief. |

## Dependency check, run it first

```bash
ffmpeg -version
ffprobe -version
python --version
python -c "import faster_whisper; print(faster_whisper.__version__)"
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py --selftest
```

- **ffmpeg and ffprobe** must both resolve. Every measurement, gate and render is ffmpeg.
  Note the version: `-fps_mode` needs 5.1 or newer, older builds want `-vsync`.
- **Python 3.10 or newer.** Detect `python3` or `python`; do not assume either name.
- **faster-whisper** is only needed for the bundled transcriber. If the import fails, you
  can still run the pipeline with a bring-your-own transcript that satisfies
  `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/transcription-contract.md`.
  Install it with `pip install faster-whisper`.
- The `--selftest` line proves the transcriber's own device and precision derivations
  without downloading a model.

Report what is missing before starting, not halfway through Stage 4.

## The one rule that outranks the router

**The human rules from frames and from the ear, never from prose.**

Do not ask for approval of a description, a plan or a table when the thing being judged is
a picture or a sound. Render the frame. Serve the cut. Every gate in this plugin measures
*fit*; none of them measures whether it lands. Three stages of `reel-first-cuts` stop for a
ruling, and every pick in `reel-motion-comps` comes off a rendered comp. That is the design,
not a formality.
