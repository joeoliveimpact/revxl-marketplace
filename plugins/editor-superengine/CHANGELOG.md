# Changelog — editor-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.4] — 2026-11-24

### Changed
- **Board layout**: the Sound Board, Tweak Board and Grade Board have a divider between the
  picture and the list. Drag it to give either side more room; double-click it to go back to
  the default. The picture loads at a size that fits the window, and a bar under it (on these
  boards and the Sketches rough cut) drags it bigger or smaller. Each board remembers its sizes
  in this browser.
- **Sound Board**: "keep all", "reject all" and "reset" sit at the top of the cue list, next to
  "Match effect levels". Each cue is one card with a single "Advanced controls" strip under it
  (time, nudges, length, peak and level), so opening it no longer squeezes the beat text into a
  narrow column. A narrow list stacks each card in two columns.

## [0.2.3] — 2026-11-17

### Added
- **Build motion**: motion scenes are built and checked in their own step, after the caption
  look and before the sound. A Motion review board shows every scene. Motion counts as done only
  when each scene is left as it is, or when you say the reel gets no graphics. A beat can use a
  scene written for its own reel, and one command places the scenes on the Beat Map.
- **Hide private details**: on the Beat Map, draw blur or solid black boxes over a B-roll clip,
  for the whole clip or for a time range. The boxes are applied on every render (preview,
  master, trial reels and the hand-off). If a box cannot be applied, the render stops rather
  than show the detail. Before the Beat Map Send, Claude asks whether any B-roll shows private
  details and never answers for you.
- **Stills as B-roll**: screenshots and images (PNG, JPG, WebP) can be placed as B-roll.
- **Sound-effect levels**: the sound pass evens out sound-effect loudness on its own ("Match
  effect levels" on the Sound Board, on by default). Levels you set by hand are kept, and an
  effect that could not be raised enough is marked. The mix check says why a cue was not heard.

### Changed
- **Frame rates**: scenes keep exact frames at every common frame rate (checked at 23.976, 24,
  25, 29.97, 30, 50 and 59.94), and the Motion review renders at the reel's own rate.
- **World scenes**: on a stack or split layout the face stays in its slot unless you pick
  "Graphics take the whole screen". The caption band is checked on every frame, and a crossing
  names its beat, time and words.
- **Sound Board**: it plays the newest preview made after the motion was approved, and says
  which file it plays.
- **Guides**: the skill guides and references match what the code does, with one owner for each
  rule. Placing scenes or picking the style no longer reopens the Beat Map Send.

### Fixed
- **Cut Board ad-libs**: the Cut Board lines up the locked script with what was actually said,
  ad-libs included, and a script fix replaces every match.
- **Hub on a new reel**: opening the hub on a new reel builds its rows itself. It never switches
  to another reel on its own or shows a raw 404.
- **Sound in the master**: the sound mix always lines up with the cut, so it reaches the master.
  Approving "Latest mix" approves the real preview, and a re-mix after your OK makes the master
  ask for a new preview.
- **Motion choice**: building motion clears an earlier "no motion graphics" choice, so new
  scenes always reach the Motion review.
- **Beat Map**: it shows Loading until it knows its state, and a reel scene on its own beat no
  longer stops the Send.

## [0.2.2] — 2026-11-11

### Added
- **Caption fonts**: the full Inter and Montserrat font families ship with the plugin (19 new
  font files). Caption looks use real heavy weights, and the doctor checks the bundled font
  files.
- **Full view**: a board opens in Full view inside the editor hub, with Back to hub and a step
  band, in place of a separate tab.

### Changed
- **Beat Map**: rebuilt as one beat at a time, with a small sketch of each layout, a timeline of
  the whole reel, and a flag on a beat Claude wants looked at.
- **Rebuilding a Beat Map** keeps the picks already made on beats whose words did not change,
  and names any it could not keep.

### Fixed
- **Word marks**: a mark stays on the word or words you marked. One marked word no longer grows
  into a whole sentence, and two marks in one sentence no longer stop the captions step.
- **Picture-match check**: it no longer blocks a correct cut from a recording that is not 30
  frames a second. It reports what it measured, says the cut video is older only when the file
  times show it, and reports any piece it could not compare.

## [0.2.1] — 2026-11-11

### Fixed
- **First cut, frame count**: the first-cut render now carries exactly the frames the cut list
  states. Footage recorded under 30 frames a second (23.976, 24 or 25) lost a frame at any speed,
  and a cut at 1.2x could lose one at any frame rate, so the render stopped on its own
  frame-count check. The scrubbing copy and a screen recording that follows the cut are fixed the
  same way.
- **First-time setup on Windows**: setup no longer stops at "Installing Python" when the install
  worked. It checks that the installed Python runs and carries on. Setup's failure messages now
  say what failed, in the tool's own words; "check the internet connection" appears only when a
  download failed.
- **Editor Cockpit and hub, Motion step**: a reel with no sketches file no longer shows Motion
  (and the Sketches board) as done. Motion is done when the sketches are locked, or when the sent
  Beat Map asks for no scene on any beat.

### Known limits
- A recording whose picture starts after its sound holds the first picture for that gap in the
  first cut; the sound stays in step.
- When an install script inside the HyperFrames install fails, setup's message gives the exit
  code and may leave out the script's own error line.

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
