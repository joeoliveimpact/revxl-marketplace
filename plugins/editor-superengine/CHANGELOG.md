# Changelog — editor-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0] — 2026-11-08

### Added
- **`editor-doctor`**: installs the editor's tools itself (Python, Node, ffmpeg, Chrome headless
  shell, HyperFrames, the transcription and cutout models), all pinned by sha256 (HyperFrames by
  its npm lock hashes), checks them,
  and starts the editor hub and boards.
- **`recording-preflight`**: checks the camera and sound from a 10-second test clip before the
  client records.
- **Boards**: the Cut Board and Tweak Board (first cut), Beat Map and Sketches (on-screen plan
  and direction), the caption Look Picker, Grade Board, Sound Board, Cover Picker, the Trials
  board, and the editor hub that links them.
- **`reel-captions`**: burned-in captions with truthful word marks and a picked caption look.
- **`reel-broll`**: own or AI-generated B-roll as cutaways over Beat Map beats.
- **`reel-grade`**: measured colour options on one contact sheet; the client picks on the Grade
  Board; recordings matched to each other.
- **`reel-sound-pass`**: music, sound effects, voice clean-up (free, or Auphonic with a yes
  gate), mix and master. A starter sound pack is downloaded on first use from a pinned,
  sha256-checked file; its credits ship in `LICENSES/SOUND-PACK-CREDITS.md`.
- **`reel-cover`**: a cover frame with an optional short title, usable as frame zero.
- **`reel-trials`**: trial reels that each change exactly one opening, hook, camera field or look.
- **`pro-editor-handoff`**: an editable timeline for DaVinci Resolve Studio or another editor.
- **`style-decoder`**: decodes a reel's editing style into a saved style later edits follow.
- **`caption-writer`**: writes or audits the post caption under a finished reel.
- **`reel-teardown`**: tears down a posted reel and shows the same footage rebuilt.
- **Saved styles**: a client's look (edit, captions, colour, transitions) carried from reel to
  reel, with a default style and named styles.
- **Scenes**: 19 on-screen scenes (titles, lower thirds, lists, quotes, stat cards, end cards, a
  3D glass card), seven adapted from HyperFrames.
- **Several recordings**: cuts from two recordings, a separate mic synced to the camera, and
  Shorts cut from one long recording.
- **`LICENSES/NOTICE`** lists every copied or adapted file and every download the installer
  makes; GSAP's terms are in `runtime/gsap/GSAP-NOTICE`.

### Changed
- **`editor-start-here`** routes to all 15 skills.
- **`reel-first-cuts`** is driven from the Cut Board and Tweak Board.
- **`reel-canvas-build`** replaces `reel-motion-comps`: plan on the Beat Map, pick a direction
  on Sketches, design, then render.

## [0.1.0] — 2026-09-04

First release. The editing half of the short-form pipeline, split out so it can be
installed without the strategy and scripting engines.

### Added
- **`editor-start-here`** — the router. Pipeline order (first cuts, then picture lock,
  then motion comps), which skill answers which ask, when each shared reference
  applies, and the dependency check with the exact commands that verify ffmpeg,
  ffprobe, Python and faster-whisper.
- **`reel-first-cuts`** — raw recording to finished spoken cut in one build pass.
  Ten stages, three of which stop for a human ruling, plus the ear-driven correction
  loop. The governing rule is calibrate from the file, never ship a magic number.
- **`reel-motion-comps`** — the design-iteration loop for reel visuals: divergent
  directions over the real plates, one parameter factory per element, ladders instead
  of single attempts, and a measurement kit that has each caught a real defect.
- **Four shared references** under `skills/_shared/references/`:
  `house-rules.md` (duplicate before the first cut, fewest generations, never judge
  picture on a proxy, half-ass setup makes half-ass output), `frame-zero-hook.md`
  (the complete visual hook readable at 0.000s), `preview-before-render.md` (cheap
  previews approved before any render), and `design-prompt.md` (the art-director
  prompt for a design canvas).
- **Bundled scripts**, all invoked through `${CLAUDE_PLUGIN_ROOT}`:
  `reel-first-cuts/scripts/probe.py` (true frame rate, RMS envelope, per-file
  thresholds, duplicate-frame table), `gaps.py` (gap tightening in source
  coordinates, orphan guard), `render.py` (one filter graph from the raw, master and
  scrub), `silence_budget.py` (the aggregate silence gate),
  `transcribe_words.py` (word-timestamped transcript, VAD on, hard-fails on an empty
  word list), and `reel-motion-comps/scripts/ig-safe-zones.py` (Instagram UI reserve
  pre-check).

### Deliberately not shipped
- **Regression fixtures.** The fixture table and its runner keyed on one client's
  verbatim voice-over lines and their timecodes, so they cannot ship in a public
  plugin. The defect classes they guard are documented in
  `skills/reel-first-cuts/references/correction-loop.md` instead.
- **`reel-sound-pass`** — music, SFX spotting and mastering levels. Deferred to 0.2.
- **`design-canvas-review`** — the single review surface. Deferred to 0.2;
  `reel-motion-comps` names the requirement without depending on the skill.
- **The Design / Higgsfield / HyperFrames router** and **zoom suggestions** on the
  spoken cut. Both deferred to 0.2 rather than shipped half-built.
