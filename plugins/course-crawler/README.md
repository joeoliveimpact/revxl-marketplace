# course-crawler

A Claude Code plugin that turns any piece of online content into a clean local archive ... written + visual + video + transcripts.

## What's inside

Five focused skills:

| Skill | When to use it |
|-------|----------------|
| `setup` | First time on this machine, before anything else |
| `login` | Before scraping any site that requires login (course platforms, paywalled blogs) |
| `page` | One URL → clean Markdown |
| `course` | Entire online course (Kajabi, Teachable, Thinkific, Skool, Udemy, custom LMS) |
| `youtube` | Single YouTube video, playlist, or channel |

## How it works under the hood

- **Setup** detects your OS (macOS or Windows) and installs the right tools:
  Python 3.13, ffmpeg, yt-dlp, browser-use (with Chromium), faster-whisper. A
  per-user virtual environment lives at `~/.iss/venv` (Mac) or
  `%USERPROFILE%\.iss\venv` (Windows). Optionally registers your Groq API
  key for fast cloud-based transcription. If `yt-dlp` or `ffmpeg` is already
  on PATH, setup uses what's already there instead of reinstalling.
- **Login** detects an available agentic-browser backend (superpowers-chrome,
  browser-use, or Playwright), opens the login page, watches for you to finish
  signing in, then captures cookies into `~/.iss/sessions/<domain>.txt`. If no
  backend works, a manual cookie copy/paste path always works.
- **Page** uses those cookies (if present) to fetch a URL and extract clean
  Markdown via `trafilatura`, plus reference links and downloadable assets. No
  LLM tokens spent on the fetch itself.
- **Course** drives the chosen browser backend to discover the course's module
  list (including **Skool community classrooms**, a React SPA), then bulk-fetches
  every lesson with `httpx`, detects videos from a wide set of hosts (Wistia,
  Vimeo, YouTube, Vidalytics, JW Player, Bunny Stream, Mux, Kaltura, Loom, HLS,
  DASH, direct mp4/webm/mov), downloads them via `yt-dlp`, extracts unique slide
  frames with ffmpeg scene-detection, and transcribes with Groq's
  Whisper-large-v3-turbo (or local faster-whisper). DRM-locked hosts (VdoCipher)
  are detected and reported cleanly rather than failed silently.
- **YouTube** asks you what you want (transcripts only? + slides? + video
  files? + descriptions?) and runs the matching pipeline.

## Output convention

All skills save into a folder you choose (or `./scraped/<slug>/` by default).
Clean structure ... no raw HTML dumps unless you ask for `--keep-html`:

```
scraped/<topic>/
├── written/      ... clean Markdown per lesson
├── transcripts/  ... transcript as Markdown per lesson
├── links/        ... categorized reference links (GitHub, Google Docs, etc.)
├── assets/       ... downloaded attachments (pdf, zip, docx, ...)
├── visual/       ... slide frames, screenshots
├── video/        ... video.mp4 + transcript.srt
└── metadata/     ... cookies.txt, manifests, reports, rendered/ (SPA)
```

## Install

```
/plugin marketplace add <repo-or-path>
/plugin install course-crawler@course-crawler
```

Then run `/setup` once. After that, point any of the other skills at a URL.
