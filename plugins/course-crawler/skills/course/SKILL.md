---
name: course
description: 'Scrape an entire online course into a clean, structured local archive. Use this skill whenever the user wants to capture, archive, ingest, mirror, scrape, save, "rip", or "pull down" any multi-lesson course, training program, cohort, or learning portal. Works generically across LMS platforms ... Kajabi, Teachable, Thinkific, Skool (community classrooms), Podia, LearnDash, Mighty Networks, Udemy, custom WordPress course sites. Output per course is clean: page text as Markdown, transcripts as Markdown, extracted reference links, downloaded attachments, slide frames, and video. Use even when the user says it informally ... "grab this whole course", "save the training", "I want everything in this program", "archive this membership", "pull all the lessons". Especially use whenever you see a URL pattern that looks like a course platform (contains "products/", "lessons/", "categories/", "modules/", "courses/", "training/", "academy/", "classroom/").'
---

# Scrape an entire course

This is the headline skill of the plugin. It captures a whole course end-to-end into a clean per-course tree.

## Mental model

Five phases:

1. **Pick a browser backend** ... detect what's available, let the user choose, fall back gracefully
2. **Login** ... user authenticates (via `/login`, or inline here)
3. **Discovery** ... drive the chosen backend to map the course: every module, every lesson URL
4. **Bulk pull** ... `httpx` fetches every lesson with cookies; `trafilatura` extracts clean Markdown; reference links + downloadable attachments are saved
5. **Video processing** ... `yt-dlp` downloads videos, `ffmpeg` extracts slide frames, Whisper transcribes

Phases 1-3 are LLM-driven and use tokens. Phases 4-5 are zero-token script execution.

## Phase 1: Pick a browser backend

Discovery needs an agentic browser. Do NOT assume `browser-use`. Run the detector:

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/browser_backend.py
```

Then decide using BOTH the report and your own in-session tool list:

- If `mcp__plugin_superpowers-chrome_chrome__use_browser` is in your available tools → **superpowers-chrome** (preferred, zero setup).
- Else if `mcp__browser-use__*` tools are available → **browser-use**.
- Else if a Playwright MCP is available → **playwright**.
- If more than one is available, ask the user which they prefer (mention superpowers-chrome is the lowest-friction default).
- If the chosen one errors mid-run, tell the user and try the next in preference order.
- If none are available: offer to run `/setup` (installs browser-use), OR proceed with the manual cookie-paste path documented in `/login` and skip backend-driven discovery (httpx-only ... works for server-rendered courses, not SPAs).

Throughout the rest of this skill, "the browser" means **the chosen backend's** navigate / get-state / screenshot tools. The tool names differ per backend; use whichever the chosen backend exposes.

## Phase 2: Login & confirm scope

- Cookies for the course domain must exist at `~/.iss/sessions/<domain>.txt`. If missing, run `/login <url>` first (it handles assisted login and the manual cookie-paste fallback).
- Navigate the browser to the course URL, screenshot it (full page), and confirm with the user: "I see a course called '<title>' with ~N modules. All of it, or specific modules?"
- Wait for confirmation.

## Phase 3: Discovery

Goal: `metadata/lesson_urls.json` ... a flat, ordered list of every lesson, each `{module_order, module_title, category_id, post_id, title, url}`.

General flow: find the table of contents, walk each module, collect lesson links from the browser's get-state output (look for hrefs with `/posts/`, `/lessons/`, `/items/`, `/lecture`, classroom IDs). Verify the count against any visible "X of Y lessons" indicator ... mismatch means you missed some.

Save both `metadata/course_manifest.json` (structured) and `metadata/lesson_urls.json` (flat). Show the user a module → lesson-count table and confirm.

### Platform tips

- **Kajabi**: `/products/<slug>/categories/<id>/posts/<id>`. Category index at `/products/<slug>/categories`. Video host is usually Wistia.
- **Teachable**: `/courses/<slug>/lectures/<id>`. TOC on the course main page.
- **Thinkific**: `/courses/take/<slug>/lessons/<id>`. TOC is the player sidebar.
- **Skool (community classroom)**: first-class supported. See the Skool section below.
- **Custom WordPress**: varies. Screenshot and inspect visually. Don't assume.

### Skool classroom courses

Skool is a React single-page app, so a plain httpx GET of the classroom URL returns an empty shell ... discovery MUST go through the browser backend.

- Classroom URL shape: `https://www.skool.com/<community>/classroom/<courseId>` and lessons load client-side, often reflected as `?md=<moduleId>` query changes rather than full new URLs.
- Use the helper to keep discovery consistent:
  ```bash
  ~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/discover_skool.py --help
  ```
  It documents the exact selectors and the get-state harvesting pattern. Drive the browser per its guidance: open the classroom, expand every module in the left rail, click into each lesson, and for each lesson capture: the lesson title, the in-page lesson body (Skool renders the write-up inline), any attachment links, and any reference links (GitHub, Google Docs/Drive, Loom, etc.).
- Because Skool content is SPA-rendered, the bulk-pull step (Phase 4) will use the browser-rendered HTML the discovery captured, not a fresh httpx GET, for lessons whose body isn't server-rendered. `discover_skool.py` writes per-lesson rendered HTML into `metadata/rendered/` so `scrape_course.py` can parse it offline.

## Phase 4: Bulk pull (clean output)

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/scrape_course.py ./scraped/<course-slug>
```

This script (zero tokens):
- Refreshes cookies from the live browser session (auto-detects the CDP port from any backend), or uses the manually-pasted cookie file.
- For each lesson: clean Markdown via trafilatura → `written/`, extracted reference links (GitHub, Google Docs/Drive, Notion, Loom, generic off-domain) → `links/`, downloadable attachments (pdf, zip, docx, xlsx, pptx, csv, key) → `assets/`.
- Detects video sources across many hosts (Wistia, Vimeo, YouTube, Vidalytics, VdoCipher [DRM-flagged], JW Player, Bunny Stream, Mux, Kaltura, Loom, HLS, DASH, direct mp4/webm/mov) → `metadata/video_sources.json`.
- **Raw HTML is NOT saved by default** (it was the "mess"). Pass `--keep-html` only if the user explicitly wants it for re-parsing.

Show the user `metadata/scrape_report.json`: lessons captured / failed, links found, attachments downloaded.

## Phase 5: Video processing

Ask the user what they want. For knowledge-base use, **transcripts-only is the
fast default** (native captions via yt-dlp, no multi-GB downloads, no Whisper):

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/process_videos.py ./scraped/<course-slug> --transcripts-only
```

For the full video + slide-frame layers:

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/process_videos.py ./scraped/<course-slug>
```

Downloads each video, extracts unique slide frames (ffmpeg scene-detection, threshold 0.3), writes the transcript as Markdown to `transcripts/` and `.srt` (timestamps) under `video/`. Transcription: Groq Whisper-large-v3-turbo if a Groq key is configured, else local faster-whisper. DRM-locked videos (VdoCipher) are skipped with a clear `drm_locked` status, not a broken download. Use `--skip-existing` to resume.

## Clean output structure

```
./scraped/<course-slug>/
├── written/<NN>-<module-slug>/<lesson-slug>.md          clean Markdown
├── transcripts/<NN>-<module-slug>/<lesson-slug>.md       transcript as Markdown
├── links/<NN>-<module-slug>/<lesson-slug>.md             categorized reference links
├── assets/<NN>-<module-slug>/<lesson-slug>/              downloaded attachments
├── visual/<NN>-<module-slug>/<lesson-slug>/              screenshots + slide frames
├── video/<NN>-<module-slug>/<lesson-slug>/               video.mp4 + transcript.srt
└── metadata/                                             manifests, reports, cookies, rendered/
```

After a successful scrape, offer the knowledge-base transform (Phase 2 of the plugin roadmap): "Want me to turn these transcripts into step-by-step guides or structured summaries?" ... if the `kb-transform` skill is installed.

## Edge cases

- **SPA course (Skool, some custom)**: discovery via the backend already renders JS; bulk-pull uses the captured rendered HTML for SPA-only bodies.
- **Video host needs auth**: scripts pass `metadata/cookies.txt` to yt-dlp automatically.
- **DRM video (VdoCipher)**: detected and reported, not silently failed. Tell the user it's manual-capture only.
- **Whisper rate limit**: `process_videos.py` retries with backoff; if exhausted, wait or use `--no-groq` for local.
- **No working browser backend**: manual cookie paste + httpx-only pull. Works for server-rendered courses; warn that SPA courses need a backend.

## Why this skill orchestrates other things

Course scraping is the most multi-step workflow in the plugin. One skill so the user says "scrape this course" once and walks away with a clean archive.
