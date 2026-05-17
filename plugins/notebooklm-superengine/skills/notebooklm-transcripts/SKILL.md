---
name: notebooklm-transcripts
description: Use to build a NotebookLM notebook from call/meeting transcripts — "make a notebook from this call", "build a notebook from my Fathom transcript", "summarize these meeting notes", "I have Fireflies transcripts to analyze", "turn my client calls into a notebook", "/notebooklm-transcripts". Cross-platform; requires notebooklm-setup done first. v1 = local files / pasted text / Downloads scan (no Fathom/Fireflies API).

---

# notebooklm-transcripts — Notebooks From Call Transcripts (v0.1)

Takes call/meeting transcripts (Fathom, Fireflies, Otter, plain exports) and builds or extends a NotebookLM notebook from them. **v1 source scope:** explicit file paths, pasted text, and a `~/Downloads` scan with filename heuristics. Vendor API integration (Fathom/Fireflies keys) is a deliberate later enhancement — do not attempt API calls.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit; else skip:

> I'll turn your call transcripts into a NotebookLM notebook you can question. Tell me where the transcripts are (a file, pasted text, or your Downloads folder) and I'll do the rest.

## Layer 2: Suggest before invoking

If borderline ("I just got off a client call", "here are my meeting notes"):

> "Want me to build a NotebookLM notebook from that transcript with `/notebooklm-transcripts`? Then you can ask it questions later."

If explicitly invoked, skip the suggestion.

## Preconditions

1. `.claude/workspace.yml#environment` `cowork` → "This needs Claude Code (the terminal app) to run the tool. Open this workspace there." Stop.
2. `~/.notebooklm/.superengine` missing **and** `<NB> auth check --test` not valid → "NotebookLM isn't set up — run `/notebooklm-setup` first." Stop. (If marker missing but auth is valid, proceed — it's a working unregistered install; mention they can run `/notebooklm-setup` once to register.)
3. Set `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`.

## Phase 1 — Locate transcripts (Intent Clarification)

Ask which source (one question, not a batch):
- **Explicit path(s)** — the user gives file path(s).
- **Pasted text** — the user pastes the transcript into chat.
- **Scan Downloads** — glob `~/Downloads` for likely transcripts: extensions `.txt .md .vtt .srt .docx .pdf`; filename contains any of `fathom fireflies otter transcript meeting call notes recording` (case-insensitive); sort newest first; cap the list at 15. Present candidates as a numbered list with dates; the user picks. **Never auto-ingest the whole folder.**

## Phase 2 — Target notebook

- **New notebook:** propose a title from the meeting/topic (e.g. "Client Call — Acme — 2026-05-16"); confirm. `<NB> create "<title>"` → capture id → `<NB> use <id>`.
- **Add to existing:** `<NB> list`, show titles, user picks → `<NB> use <id>`.

## Phase 3 — Add transcripts as sources

- File path: `<NB> source add "<path>"` (timeout 180s each).
- Pasted text: write to a temp `.md` (a readable title as the first `#` heading helps NotebookLM), `<NB> source add "<temp>"`, then delete the temp file.
- **Bulk safety (≥5 transcripts or a Downloads multi-pick):** list every item, get one explicit confirmation, add one at a time narrating "Adding 2 of 6: …", final count + any failures.

## Phase 4 — Wait for READY

Poll `<NB> source list` (or `source wait`) until all added transcripts are processed; report any that failed (don't claim done while processing).

## Phase 5 — Refresh titles cache

Run `<NB> list --json`, parse `notebooks[].id` / `notebooks[].title`, rewrite `~/.notebooklm/notebooks.cache` — one line `id<TAB>title`, UTF-8, LF newlines (never CRLF), skip empty rows, overwrite. Best-effort; continue on failure. Keeps the `notebook-suggest` hook accurate.

## Phase 6 — Report + next move

Beginner tone, ≤3 items: notebook title + id, transcripts added (and failures), one next move: "Ask it: 'what were the action items?' (`/notebooklm-ask`)" or "Make a summary doc or podcast (`/notebooklm-studio`)".

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** confirm the source and new-vs-existing notebook — never silently scan or guess.
- **Surgical Execution:** add transcripts only; never delete/restructure an existing notebook. Delete temp paste files you create.
- **Least Complexity:** v1 is local/paste/Downloads. No Fathom/Fireflies API, no auto-watchers — those are separate later work.
- **Declarative Focus:** DoD = target notebook has the chosen transcripts READY + titles cache refreshed.
