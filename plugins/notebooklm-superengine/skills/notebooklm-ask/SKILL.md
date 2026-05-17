---
name: notebooklm-ask
description: Use to ask questions of a NotebookLM notebook — "ask my X notebook …", "what does my research say about …", "query the X notebook", "according to my notebook …", "switch to my X notebook", "what notebooks do I have", "/notebooklm-ask". Cross-platform; requires notebooklm-setup done first.
---

# notebooklm-ask — Query Notebooks (v0.1)

Asks a question against a notebook (current or named), optionally with citations, and manages which notebook is active. Read-leaning: never writes a note without explicit confirmation.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit; else skip:

> I'll ask your NotebookLM notebook and bring back the answer. If you have several notebooks, I'll make sure I'm asking the right one first.

## Layer 2: Suggest before invoking

If a question looks answerable by a known notebook (the `notebook-suggest` hook may have hinted this):

> "You have a NotebookLM notebook on that — want me to ask it with `/notebooklm-ask` instead of answering from memory?"

If explicitly invoked, skip the suggestion.

## Preconditions

1. `.claude/workspace.yml#environment` `cowork` → "Asking a notebook needs Claude Code (the terminal app). Open this workspace there." Stop.
2. `~/.notebooklm/.superengine` missing → "NotebookLM isn't set up — run `/notebooklm-setup` first." Stop.
3. Set `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`.

## Phase 1 — Resolve the target notebook (Intent Clarification)

- If the user named a notebook → match it against `NB list`. Exactly one match → `NB use <id>`. Multiple/none → show titles, ask which.
- If the user didn't name one → `NB status`. If a sensible active notebook is set, confirm it ("Asking your '<title>' notebook — right?") on the first question of a session; reuse silently after. If none set and multiple exist → list, ask.
- "what notebooks do I have" → just `NB list`, present titles, refresh the cache (Phase 4), stop.

## Phase 2 — Ask

`NB ask "<question>"` (timeout 120s). If the user wants sources/citations, add `--json` and surface the cited passages. For follow-ups in the same notebook, keep asking without re-confirming context.

**Never** pass `--save-as-note` unless the user explicitly says to save the answer as a note in the notebook — that writes to their notebook. Confirm first if ambiguous.

## Phase 3 — Answer

Return the notebook's answer plainly. Attribute it ("From your '<title>' notebook:"). If citations were requested, list them. If the notebook returned nothing useful, say so — don't backfill from your own knowledge and present it as the notebook's answer.

## Phase 4 — Refresh titles cache

Whenever you list in this skill, use `NB list --json`, parse `notebooks[].id` / `notebooks[].title`, and rewrite `~/.notebooklm/notebooks.cache` — one line per notebook `id<TAB>title`, **UTF-8, LF newlines (never CRLF)**, skip empty id/title, overwrite. Best-effort; continue on write failure. Keeps the `notebook-suggest` hook accurate.

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** never guess which notebook when it's ambiguous — one quick confirm beats answering from the wrong source.
- **Surgical Execution:** asking is read-only. No `--save-as-note`, no source/notebook edits, unless explicitly requested.
- **Least Complexity:** answer the question from the notebook. Don't auto-generate artifacts or add sources here.
- **Declarative Focus:** DoD = the user's question answered from the correct notebook, attributed honestly.
