# Changelog — course-crawler

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
