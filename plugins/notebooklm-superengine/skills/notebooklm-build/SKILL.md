---
name: notebooklm-build
description: Use to create a NotebookLM notebook and add sources to it — "build a notebook about X", "make a notebook from these links", "create a notebook", "add these files/URLs to a notebook", "start a research notebook on X", "add this to my X notebook", "/notebooklm-build". Cross-platform; requires notebooklm-setup done first.

---

# notebooklm-build — Create Notebooks & Add Sources (v0.1)

Creates a notebook and loads sources into it (URLs, YouTube links, local files, pasted text, a folder of files), waits for processing, and reports the notebook id. Keeps the titles cache fresh so the suggestion hook works.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit; else skip:

> I'll create a NotebookLM notebook and add your sources to it. NotebookLM needs a minute to read each source — I'll wait and tell you when it's ready.

## Layer 2: Suggest before invoking

If borderline ("I have a bunch of articles on X" / "I want to study Y"):

> "Want me to build a NotebookLM notebook for that with `/notebooklm-build`? I'll create it and load the sources."

If explicitly invoked, skip the suggestion.

## Preconditions

1. Read `.claude/workspace.yml#environment`. **`cowork`** → "Building needs Claude Code (the terminal app) so I can run the tool. Open this workspace there." Stop.
2. Check `~/.notebooklm/.superengine`. Missing → "NotebookLM isn't set up yet — run `/notebooklm-setup` first." Stop.
3. Set `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`.

## Phase 1 — Clarify intent (Intent Clarification)

Ask only what's ambiguous (one question if needed, not a batch):
- **New notebook or add to existing?** If "add to existing" and the notebook is unclear, run `NB list`, show titles, let them pick.
- **Title** (new notebook only) — propose one from the topic; confirm if unsure.
- **Sources** — collect the URLs / file paths / folder / pasted text. If a folder, confirm scope before bulk-adding (see Bulk safety).

## Phase 2 — Create (new notebook path)

`NB create "<title>"` → capture the notebook id from output. Then `NB use <id>` to set context.
(Add-to-existing path: `NB use <id>` for the chosen notebook; skip create.)

## Phase 3 — Add sources

For each source: `NB source add "<url-or-path>"` (timeout 180s each). Narrate per source ("Adding 1 of 4: …").

**Bulk safety (≥5 sources or a folder):** list every item first, get one explicit confirmation, then add one at a time narrating progress, and give a final count with any failures. Never silently bulk-add.

For pasted text: write it to a temp `.md` file, `source add` that path, then delete the temp file.

## Phase 4 — Wait for READY

Poll `NB source list` (or `NB source wait <id>` where available) until all sources report ready/processed, or report which failed. Don't claim done while sources are still processing.

## Phase 5 — Refresh titles cache (enables the suggestion hook)

After any successful create/add, run `NB list` and rewrite `~/.notebooklm/notebooks.cache` — one line per notebook as `id<TAB>title` (UTF-8, overwrite whole file). This is the cheap data the `notebook-suggest` hook reads; keep it current. If the write fails, continue (cache is best-effort, not critical-path).

## Phase 6 — Report

Beginner tone, ≤3 items: notebook title + id, count of sources added (and any that failed), and one next move: "Ask it something — 'ask my <title> notebook …'".

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** never guess between new-vs-existing notebook or invent a title silently — confirm once.
- **Least Complexity:** one notebook, the requested sources, done. No auto-generation of podcasts/reports here — that's `notebooklm-studio`.
- **Surgical Execution:** adding sources only; never delete or restructure an existing notebook unless explicitly asked.
- **Declarative Focus:** DoD = notebook exists, requested sources are READY, titles cache refreshed. Generation/asking are other skills.
