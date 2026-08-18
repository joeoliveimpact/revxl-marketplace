# Changelog — course-crawler

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.7.0 — 2026-08-17

### Fixed

- **`youtube_pull.py` transcribed on CPU even when a GPU was present.** `transcribe_local()` hardcoded `device="cpu", compute_type="int8"`, ignoring the `_whisper_device()` detection that `process_videos.py` had been using all along. YouTube course pulls on a GPU machine were far slower than they needed to be.

### Changed

- **Whisper model default now matches the hardware.** GPU → `large-v3-turbo`, CPU → `small` (was: `small` everywhere). Turbo is dramatically better on proper nouns — the errors that make a transcript unusable — and on a GPU costs about a second of extra load. On CPU the encoder still runs full size, so `small` stays the default there rather than making a laptop crawl. `--whisper-model` overrides either.
- **`large-v3-turbo` added to `--whisper-model` choices** in both scripts. It was previously unselectable, so the only way to get better accuracy was full `large-v3` — roughly double the size and, on constrained hardware, prone to running out of memory.
- Disk, measured: `small` 464 MB · `large-v3-turbo` 1547 MB · `medium` 1460 MB. `medium` is kept for compatibility but is strictly dominated — turbo is 6% larger, more accurate, and faster.

## 0.6.0 — 2026-08-17

### Added

- **Transcription vocabulary prompt, derived from video metadata.** Groq was called with no vocabulary hint, so any name Whisper had not seen was silently replaced with the nearest common-English phrase — "Kling 01" came back as "uh cling a one". `course_vocab()` now builds a prompt from the channel and title yt-dlp already fetched ("This is a lesson from the channel X, titled Y."), which carries the instructor and tool names. On by default; `COURSE_CRAWLER_VOCAB` overrides the derived text and `COURSE_CRAWLER_VOCAB=off` disables it.
  - Deliberately a prose sentence, not a term list: Whisper imitates its prompt's style, so an unpunctuated list makes it emit a transcript with no capitals or punctuation at all.
  - **Lossy trade, documented at the function:** on a real clip this recovered "Kling 01" and "Higgsfield Soul" *and* collapsed a sentence the speaker said twice (net −97 chars). Correct tool names beat a duplicated sentence in reference material; use `=off` when you need verbatim.
- `transcribe_groq()` takes an optional `vocab` and forwards it as Groq's `prompt`.

## 0.5.0 — 2026-06-02

### Added

- **Skool-native (signed Mux) video support.** Some Skool classrooms host video on Mux with *signed playback* (`stream.video.skool.com`) instead of an external `videoLink`. Those lessons carry `metadata.videoId` + a per-lesson `playbackToken` (JWT, aud="v"). `discover_skool.py` now:
  - detects them (`--from-page` reports `skool_native_post_ids`) and resolves the open lesson's signed source automatically;
  - exposes `--mux-page <course_dir> <lesson_page.html> <post_id>` to extract and upsert a signed `video_sources.json` entry from any captured lesson page (the token is per-lesson, so each must be visited — the `course` skill drives this).
  - New helpers: `skool_mux_source()`, `append_video_source()`.

### Fixed

- **Signed-playback downloads 403'd (no Referer).** `process_videos.py` (`download_video`, `try_native_subtitles`) now sends `--referer` when required. New `referer_for()` honors a per-entry `referer` field and defaults Mux/Skool-hosted videos to `https://www.skool.com`, which the Mux `playback_restriction_id` requires.

## 0.4.0 — 2026-05-20

### Added

- **OCR-gated slide extraction.** Replaced raw ffmpeg `select=gt(scene,0.3)` (junk/blurry/dupe-prone) with: sample 1fps → dHash dedupe consecutive → sharpest frame per run → Laplacian blur floor → Tesseract OCR text-density gate (drops talking-head frames) → global dedupe → `slide-NNN.jpg` + `slides.json` (timestamp + OCR text). Falls back to scene-detect when Tesseract is absent. Six tunable flags: `--slide-fps`, `--slide-phash-dist`, `--slide-blur-min`, `--slide-min-words`, `--slide-min-chars`, `--slide-tesseract-cmd`.

### Fixed

- **Promo-video transcript pollution on Skilljar (and any course with shared page chrome).** `scrape_course.py::drop_page_chrome_videos()` filters any video source appearing on ≥ceil(0.6·N) lessons — generic across courses, no hardcoded IDs. Stops `process_videos` from picking a promo-carousel YouTube embed as the lesson video.
- **GPU Whisper batch-killer crash on Windows.** `process_videos.py::transcribe_local` runs faster-whisper in a disposable subprocess (`_whisper_worker`) that writes the transcript then `os._exit(0)`, so ctranslate2's CUDA destructor abort (0xC0000409) at Python finalization can't kill the batch. GPU speed retained; a crash is contained to one lesson.
- **Windows MAX_PATH (260-char) write failures on long lesson titles.** Both `scrape_course.py` and `process_videos.py` now wrap `course_dir` with the `\\?\` extended-length prefix on `sys.platform=="win32"` so derived child paths inherit it. Resolves `FileNotFoundError` writing `<lesson>.md`/`transcript.md`/`slide-NNN.jpg` for paths over 260 chars.

## 0.3.2 — 2026-05-17

### Fixed

- **Marketplace CI red:** `skills/course/SKILL.md` frontmatter `description:` contained an unquoted `clean: page text` — the colon-space made the YAML parser read it as a mapping ("mapping values are not allowed here") and fail validation. Single-quoted the description scalar. Verified all 5 course-crawler skill frontmatters now parse. (Pre-existing since 0.3.0; surfaced by CI, missed by the local validator.)

## 0.3.1 — 2026-05-17

### Changed

- **Lesson-centric output tree.** Replaced the type-first layout (`written/`, `transcripts/`, `links/`, `assets/`, `visual/` each split by module/lesson — everything for one lesson scattered across five top-level folders) with: `<course>/NN-module/NN-lesson/` holding that lesson's `<lesson>.md` (clean text **with a `## Reference links` section appended** — one file, not two), `transcript.md` + `transcript.srt` (only if it has a video), `slides/`, `downloads/`. Machine files stay in `metadata/`.
- `discover_skool.py` writes `lesson_order` into the manifest so `scrape_course.py` and `process_videos.py` compute the **identical** per-lesson folder (single source of truth).
- `process_videos.py` now writes into the shared lesson folder and **never deletes it** (it holds the text + downloads); video/caption work happens in a temp `.work/` that is cleaned up. `--slides`/`--transcripts-only` discard only the mp4, not the lesson.
- Dropped trafilatura YAML frontmatter and the synthetic `<h1>` so the lesson `.md` has a single clean title.
- Added `--limit` to `scrape_course.py` (parity with `process_videos.py`, for partial/test runs).

## 0.3.0 — 2026-05-17

First marketplace release. Reworked from the original `info-scraping-superengine` pass into a tested, plain-language plugin.

### Added

- **Browser-backend abstraction** (`scripts/browser_backend.py`): detects the agentic browser available this session (superpowers-chrome preferred, then browser-use, then Playwright), lets the user choose, falls back, or offers a manual path. No longer hardcoded to browser-use.
- **Assisted + manual login** (`skills/login`): opens the chosen browser at the login page, watches for completion, captures cookies via CDP; always-available manual cookie-paste fallback for environments with no usable browser.
- **First-class Skool support** (`scripts/discover_skool.py`): parses the Next.js `__NEXT_DATA__` blob — one classroom page yields the entire course tree (every module/lesson, title, video, resources, writeup). No lesson-by-lesson navigation, no DOM pollution.
- **Clean output contract**: per-course tree of `written/` (clean Markdown), `transcripts/` (reflowed prose), `links/` (categorized reference links — GitHub/Google/Notion/Loom), `assets/` (downloaded attachments), `visual/` (slide frames), `metadata/`. Raw HTML only with `--keep-html`.
- **Transcription**: `--transcripts-only` (fast native captions, no download), default `--slides` capable, and `--whisper auto|groq|openai|local`. **Local GPU Whisper is the default** — auto-detects NVIDIA GPU (`device=cuda`, `float16`), CPU fallback, Groq/OpenAI API fallback.
- **`--slides` mode**: download → scene-detect slide frames + transcript → delete the video (keeps visuals, no multi-GB bloat).
- Expanded video-host detection: Wistia, Vimeo, YouTube, Vidalytics, VdoCipher (DRM-flagged), JW Player, Bunny Stream, Mux, Kaltura, Loom, HLS, DASH, direct mp4/webm/mov.
- GPU-aware, confirmation-gated transcription setup in `skills/setup` with a plain-English explanation and alternatives.

### Fixed

- Cross-platform `dump_cookies.py` (Windows PowerShell CIM + macOS/Linux `ps`).
- Skill→script path resolution now uses `${CLAUDE_SKILL_DIR}` (previously an unresolvable `<plugin-root>` placeholder — scripts could never run).
- UTF-8 stdout/stderr guard on all scripts (no more Windows cp1252 crashes on emoji/arrows).
- Neutral User-Agent (was an identifiable `GOATA-Scraper/1.0`).
- Exit code reflects real failures only ("nothing new to do" is success).
