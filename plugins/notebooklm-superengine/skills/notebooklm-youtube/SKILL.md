---
name: notebooklm-youtube
description: Use to build/enrich a NotebookLM notebook from YouTube plus parallel deep web research — "make a notebook from this YouTube video", "research this topic and pull in this video", "analyze this YouTube playlist", "deep-dive this video and the web on X", "/notebooklm-youtube". Cross-platform; requires notebooklm-setup done first. Pulls yt-dlp/ffmpeg on demand only if transcript-enrichment is used.

---

# notebooklm-youtube — YouTube + Parallel Deep Research (v0.1)

Adds YouTube content to a notebook **and**, in parallel, kicks off NotebookLM deep web research on the topic — so the notebook has both the video and a researched web base when you start asking.

NotebookLM ingests YouTube URLs natively, so the default path needs no extra tools. `yt-dlp` (+ `ffmpeg`) are only pulled if you opt into **transcript enrichment** (grabbing the exact transcript as a text source for higher fidelity).

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit; else skip:

> I'll add this YouTube video to a NotebookLM notebook and, at the same time, have NotebookLM research the topic on the web. When both finish you'll have one notebook covering the video and the wider research.

## Layer 2: Suggest before invoking

If borderline ("here's a great YouTube talk on X", "I want to learn X from this video"):

> "Want me to build a NotebookLM notebook from that video and run parallel deep research with `/notebooklm-youtube`?"

If explicitly invoked, skip the suggestion.

## Preconditions

1. `.claude/workspace.yml#environment` `cowork` → "Needs Claude Code (the terminal app)." Stop.
2. `~/.notebooklm/.superengine` missing **and** `<NB> auth check --test` invalid → "Run `/notebooklm-setup` first." Stop. (Marker missing but auth valid → proceed; mention `/notebooklm-setup` registers it.)
3. Set `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`. Set `PYBIN` (the venv python) for optional yt-dlp install.

## Phase 1 — Inputs (Intent Clarification)

- The YouTube URL(s).
- The **research angle** for parallel deep research (a focused query — propose one from the video title/topic; confirm).
- Target notebook: new (propose title) or existing (`<NB> list` → pick).
- **Transcript enrichment?** Default **off** (NotebookLM ingests the video natively). Offer it only if the user wants the verbatim transcript as text or the URL fails native ingest. Enrichment triggers Phase 1b.

### Phase 1b — On-demand deps (only if transcript enrichment chosen)

Check `<PYBIN> -m yt_dlp --version` and `ffmpeg -version`. If missing, narrate and install with confirmation:
- yt-dlp: `<PYBIN> -m pip install -U yt-dlp`
- ffmpeg: Win `winget install -e --id Gyan.FFmpeg` / Mac `brew install ffmpeg`
If the user declines the install, fall back to native URL ingest (skip enrichment) — don't block.

## Phase 2 — Two tracks in parallel

- **Notebook target:** create/`use` the notebook.
- **Track A — video:** `<NB> source add "<youtube-url>"` (native ingest, timeout 180s). If transcript enrichment: also `<PYBIN> -m yt_dlp --skip-download --write-auto-sub --sub-format vtt -o "<temp>" "<url>"`, convert/clean the `.vtt` to text, `source add` that text file, delete temps.
- **Track B — deep research (parallel):** `<NB> source add-research "<research angle>" --mode deep --no-wait` — kicks off without blocking Track A.

## Phase 3 — Reconcile

`<NB> research wait --import-all` (or poll `<NB> research status`) to import deep-research results. Confirm the YouTube source reached READY via `<NB> source list`. Deep research can take several minutes — narrate, don't appear hung.

## Phase 4 — Refresh cache + report

Refresh `~/.notebooklm/notebooks.cache` (`<NB> list --json` → `id<TAB>title`, UTF-8, LF, skip empty, overwrite; best-effort). Report: notebook title+id, video added (+enrichment?), research sources imported, one next move (`/notebooklm-ask` or `/notebooklm-studio`).

## Ground rules (inherited from RULES.md)

- **Least Complexity:** default path = native URL ingest + parallel deep research. yt-dlp/ffmpeg only when enrichment is explicitly chosen — don't install them otherwise.
- **Intent Clarification:** confirm the research angle and notebook target; don't invent a deep-research query silently.
- **Surgical Execution:** delete any temp transcript/subtitle files created. Add sources only.
- **Declarative Focus:** DoD = notebook has the video source READY + deep-research imported + cache refreshed.
