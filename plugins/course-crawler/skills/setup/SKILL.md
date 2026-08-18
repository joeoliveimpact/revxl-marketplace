---
name: setup
description: One-time setup of course-crawler on this machine. ALWAYS use this skill the first time someone wants to scrape a page, course, or YouTube playlist with this plugin. Detects whether the user is on macOS or Windows and installs everything needed (Python 3.13, ffmpeg, yt-dlp, uv, browser-use with Chromium, faster-whisper, trafilatura, httpx), builds a per-user virtual environment, wires the browser-use MCP into Claude Code at user scope, and optionally captures a Groq API key for fast Whisper transcription. If yt-dlp or ffmpeg is already on PATH, skips reinstalling them. Use this skill when the user says any of "set up the scraper", "install the plugin", "I'm new", "first time", "nothing works yet", or when one of the other skills (page, course, login, youtube) reports that setup hasn't been done yet.
---

# Setup course-crawler

This is the first thing a new user runs. After it succeeds the other skills (`login`, `page`, `course`, `youtube`) just work.

## Communicate clearly with the user

The audience for this plugin is **anyone** — including people who have never opened a terminal. Walk through each step in plain English. Tell them what you're about to do, then do it, then confirm what just happened. If something needs the user's input (password prompt, API key), pause and wait.

Use "..." for pauses in your prose, never em-dashes.

## Step 1: Detect the operating system

Run a quick check with the Bash tool: `uname -s` returns `Darwin` on Mac, `Linux` on Linux/WSL, or fails on native Windows.

Branch accordingly:

- **macOS** → follow `references/setup-mac.md`
- **Windows** → follow `references/setup-windows.md`
- **Linux/WSL** → follow `references/setup-mac.md` (same approach with `apt` instead of `brew`; the reference covers it)

Read the relevant reference file in full, then execute it step by step.

## Step 2: Confirm what got installed

After the install steps run, sanity-check that the four CLI tools and the venv all exist:

```bash
# Mac/Linux
which brew && which python3.13 && which ffmpeg && which yt-dlp && which uv
ls ~/.iss/venv/bin/browser-use
```

```powershell
# Windows
where python; where ffmpeg; where yt-dlp; where uv
ls $env:USERPROFILE\.iss\venv\Scripts\browser-use.exe
```

Show the user a checklist of what's present and what's missing. If anything is missing, halt and re-run the relevant install step.

## Step 3: Wire the browser-use MCP into Claude Code

The browser-use MCP is what makes login flows and discovery work. It needs to be registered in Claude Code's **user-scope** config (`~/.claude.json` on Mac/Linux, `%USERPROFILE%\.claude.json` on Windows) so it loads in every workspace.

Open the file (create it if missing) and merge in:

```json
{
  "mcpServers": {
    "browser-use": {
      "command": "<path-to-venv>/bin/browser-use",
      "args": ["--mcp", "--headed"]
    }
  }
}
```

`<path-to-venv>` is `~/.iss/venv` on Mac/Linux or `%USERPROFILE%\.iss\venv` on Windows. On Windows the binary is `Scripts\browser-use.exe`.

Important: if the file already contains `mcpServers` with other entries, *add* the `browser-use` key — don't overwrite the whole block. Read the file first, parse the JSON, add the entry, write it back.

After saving, tell the user to **restart Claude Code** (close the window, reopen the workspace). The MCP loads on startup.

## Step 4: Transcription backend — local Whisper is the default

Many lessons already have native captions (YouTube auto-subs etc.) which the plugin uses for free, no key. A Whisper backend is only needed for lessons with **no** captions. **Local faster-whisper is the default** — private, $0, no API keys, and fast on a GPU. Only fall back to an API if the user has no usable GPU and wants speed without local install.

**Step 4a — detect a GPU (do this automatically, don't ask):**

```bash
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader   # non-empty => NVIDIA GPU present
```

**Step 4b — explain it simply, then ask before installing.**

Never install the GPU setup silently. First give the user a plain-English, no-jargon explanation and get an explicit yes. Keep it to ~3 short sentences. Template (adapt to what was detected):

> "Good news ... your computer has a graphics card (an NVIDIA <name>). I can use it to turn course videos into text *on your machine* ... private, free, and fast (about 15-20x faster than not using it). It's a one-time ~300 MB install. Alternatives: a cloud service (fast, no install, but costs a little and sends audio out), or skip it entirely (you'll still get text for videos that already have captions). Want me to set up the GPU option?"

Then use `AskUserQuestion` with:
1. **Yes, set up local GPU transcription (recommended)** — install into the venv:
   ```bash
   <venv-python> -m pip install faster-whisper nvidia-cublas-cu12 nvidia-cudnn-cu12
   ```
   Verify: `<venv-python> -c "import ctranslate2;print(ctranslate2.get_cuda_device_count())"` → `>=1`.
2. **Use a cloud API instead** — skip the local install, go to Step 4c.
3. **Skip transcription** — captions-only; lessons without captions get no transcript.

**If no GPU was detected:** don't pitch the GPU path. Briefly offer local CPU Whisper (`<venv-python> -m pip install faster-whisper` ... "works offline and free, but slow") vs. a cloud API vs. captions-only, and let them pick. Only install on confirmation.

`process_videos.py` and `youtube_pull.py` both auto-detect the GPU at runtime (`_whisper_device()`) — no config needed. `--whisper auto` (default) order is **local → groq → openai**, so once faster-whisper is in the venv it is used automatically.

**Model is chosen to match the hardware, automatically:**

| Hardware | Default model | Why |
|---|---|---|
| GPU | `large-v3-turbo` | Costs ~1s more load than `small` and is dramatically better on proper nouns — the errors that make a transcript unusable |
| CPU | `small` | Turbo's encoder runs full size regardless of decoder shortcuts, so it is meaningfully slower on CPU; a laptop pulling a long course would crawl |

Override with `--whisper-model` either way. First run on a GPU downloads ~1.5 GB (vs 464 MB for `small`) — one time, cached thereafter. Worth mentioning to the user before the first pull so the wait is expected.

`medium` remains selectable for compatibility but is strictly dominated: turbo is only 6% larger, more accurate, *and* faster.

**Step 4c — optional API fallback (only if the user wants it):** ask via `AskUserQuestion` whether they also want an API fallback for machines with no GPU:
- **Groq** — `gsk_...` key, https://console.groq.com/keys (fast, cheap, free tier).
- **OpenAI** — `sk-...` key, https://platform.openai.com/api-keys (reuses a /watch key if present).

If they give a key, persist it (mode 600 on Mac/Linux), `~/.iss/.env` (Windows `%USERPROFILE%\.iss\.env`):

```
# optional fallback only; local Whisper is used first when available
GROQ_API_KEY=<key>
OPENAI_API_KEY=<key>
```

Warn about transcript exposure for any pasted key. Mirror a Groq key into `~/.config/watch/.env` if that dir exists (shared with /watch). Per-run override: `--whisper local|groq|openai`.

## Step 5: Finish

Print a clear "all set" summary that includes:

- What got installed and where (paths)
- Where output will go by default (`./scraped/<topic>/` in the current working dir)
- What to do next: "Run `/page <url>` to save a single page, `/course <url>` for a whole course, or `/youtube <url>` for a video or playlist. Run `/login <url>` first if the site requires authentication."

## Self-check before declaring done

Don't claim setup is complete unless ALL of these are true:

- [ ] Python 3.13 venv exists and `python --version` from it returns 3.13.x
- [ ] `browser-use doctor` from the venv passes its core checks
- [ ] `ffmpeg -version` and `yt-dlp --version` both print something
- [ ] The MCP entry exists in the user-scope `.claude.json`
- [ ] Local Whisper is the default: `faster-whisper` imports from the venv; if an NVIDIA GPU is present, `ctranslate2.get_cuda_device_count() >= 1` (GPU acceleration confirmed). API key in `~/.iss/.env` is optional fallback only

If a check fails, fix it before moving on. The other skills will fail in confusing ways if setup is half-done.

## Why this exists

Without this skill, the other four skills would each have to re-implement OS detection, dep installation, venv creation, and MCP wiring. Centralizing it here keeps the rest of the plugin simple and lets us put the friction in one place where a user is mentally prepared for it.
