---
name: notebooklm-doctor
description: Use to diagnose a broken or flaky NotebookLM install — "notebooklm stopped working", "notebooklm command not found", "is notebooklm still signed in", "check my notebooklm", "notebooklm error", "diagnose notebooklm", "/notebooklm-doctor". Read-only: it inspects and reports the exact fix, it never changes anything. Cross-platform.

---

# notebooklm-doctor — Read-Only Diagnostics (v0.1)

Inspects the NotebookLM install and prints a pass/fail table with the exact remedy for each failure. **Never mutates anything** — no installs, no re-auth, no cache writes. It tells you what's wrong and which skill fixes it.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit before work; else skip:

> I'm going to run a quick health check on NotebookLM — about 20 seconds. I only look and report; I won't change anything. At the end I'll tell you exactly what (if anything) needs fixing.

## Layer 2: Suggest before invoking

If borderline (an error mentions notebooklm but the user didn't ask to diagnose):

> "Want me to run `/notebooklm-doctor` — a quick read-only health check that pinpoints the exact fix? It changes nothing."

If explicitly invoked, skip the suggestion.

## Runtime environment

Read `.claude/workspace.yml#environment`. **`cowork`** → Bash unavailable; say "Diagnostics need Claude Code (the terminal app). Open this workspace there and run `/notebooklm-doctor`." Then stop.

## Set paths (same as setup)

- `MARKER`: `~/.notebooklm/.superengine`
- `PYBIN`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\python.exe` / Mac `~/.notebooklm-venv/bin/python`
- `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`
- `WRAP`: Win `%USERPROFILE%\bin\notebooklm.cmd` / Mac `~/bin/notebooklm`

## Checks (run all, then one table — do not stop on first failure)

| # | Check | How | Remedy on fail |
|---|---|---|---|
| 1 | Install marker | `MARKER` exists | Not set up → run `/notebooklm-setup` |
| 2 | venv + Python | `PYBIN` exists; `PYBIN --version` ≥ 3.10 | Broken env → `/notebooklm-setup` |
| 3 | CLI present | `NB` exists | Broken install → `/notebooklm-setup` |
| 4 | PATH wrapper | `WRAP` exists | Missing wrapper → `/notebooklm-setup` (PATH phase). Note: open a new terminal for it to take effect |
| 5 | Auth valid (live) | `NB auth check --test` contains `Authentication is valid.` | Expired/invalid → `/notebooklm-setup reauth` |
| 6 | Notebooks reachable | `NB list` returns without auth error | If 5 passed but this fails → transient/rate-limit, retry in a few min; else `/notebooklm-setup reauth` |
| 7 | Profiles path sane | `~/.notebooklm/profiles/default/storage_state.json` exists | Migration incomplete → `/notebooklm-setup reauth` |

Run checks 5 and 6 with a 60s timeout each. Treat a timeout as fail with remedy "retry once; if it times out again, `/notebooklm-setup reauth`".

## Report

Print a compact table: check, ✓/✗, and for any ✗ the one-line remedy. Then a single bottom-line:

- All pass → "NotebookLM is healthy ✓ — nothing to fix."
- Any fail → lead with the **single most actionable** remedy (precedence: 1 → 2 → 3 → 5 → 7 → 4 → 6). Don't list ten things; give the one next step, beginner tone, reassure ("this is normal and quick to fix").

Cross-reference `docs/known-issues-windows-mac.md` for the failure's detail if the user wants the why.

## Ground rules (inherited from RULES.md)

- **Surgical Execution:** strictly read-only. If you're tempted to "just fix it while I'm here" — don't. Report and route to `notebooklm-setup`.
- **Least Complexity:** one table, one headline remedy. No multi-page output.
- **Declarative Focus:** DoD = an accurate pass/fail table + the single correct next step. Fixing is a different skill.
