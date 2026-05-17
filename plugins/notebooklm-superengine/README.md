# notebooklm-superengine

> Google NotebookLM, set up and driven by Claude — install, sign in, and use it just by talking. Mac + Windows. Local-only.

![demo placeholder](../../docs/demos/notebooklm-superengine.gif)

---

## What this plugin does

NotebookLM is incredibly useful, but the part that stops people is **getting it installed and signed in** — especially on Windows, where the usual approach fails at almost every step. This plugin removes that wall.

One guided skill (`notebooklm-setup`) detects your operating system, installs the missing pieces into an isolated environment (nothing touches your system Python or your normal browser), opens a browser once so you sign in to Google, and verifies it actually works. After that, you build research notebooks, ask them questions, and turn them into podcasts and study guides — all by talking to Claude.

**Local-only by design.** No servers, no tunnels, no extra accounts. It runs on your machine in Claude Code.

---

## Skills

### `notebooklm-setup` *(v0.1.0)*
**Triggers:** "set up notebooklm", "install notebooklm", "notebooklm isn't working", "sign in to notebooklm", "my notebooklm login expired", "update notebooklm", "uninstall notebooklm"

The front door. Cross-platform install + Google sign-in + verify, with every known Windows/Mac failure mode pre-empted. Sub-modes: `reauth`, `update`, `uninstall`. Every other skill depends on this one.

### `notebooklm-doctor` *(v0.2.0)*
**Triggers:** "notebooklm stopped working", "check my notebooklm", "diagnose notebooklm", "is notebooklm still signed in"

Read-only health check — 7 checks, one pass/fail table, the single exact next step. Changes nothing.

### `notebooklm-build` *(v0.2.0)*
**Triggers:** "build a notebook about X", "make a notebook from these links", "add these files to my X notebook"

Creates a notebook (or adds to one), loads URL/YouTube/file/folder/pasted sources with bulk-safety, waits until they're ready.

### `notebooklm-ask` *(v0.2.0)*
**Triggers:** "ask my X notebook…", "what does my research say about…", "what notebooks do I have"

Asks the right notebook (confirms which when ambiguous), optional citations, honest attribution. Never writes notes without asking.

### In-session hint *(hook, v0.2.0)*
A background nudge: if your prompt matches a notebook you already have, Claude offers to consult it; if you show research intent and have none yet, it offers to build one. Cheap, no extra cost, offers — never auto-runs.

### `notebooklm-transcripts` *(v0.3.0)*
**Triggers:** "make a notebook from this call", "build a notebook from my Fathom transcript", "turn my client calls into a notebook"

Builds/extends a notebook from call transcripts — explicit files, pasted text, or a Downloads scan (Fathom/Fireflies/Otter). Bulk-safe.

### `notebooklm-youtube` *(v0.3.0)*
**Triggers:** "make a notebook from this YouTube video", "research this topic and pull in this video"

Adds a YouTube video natively **and** runs parallel NotebookLM deep web research, so the notebook covers both. Optional verbatim-transcript enrichment.

### `notebooklm-studio` *(v0.3.0)*
**Triggers:** "make a podcast from my X notebook", "turn this into a study guide", "generate a mind map / slide deck / video"

Generates podcasts, videos, mind maps, slide decks, reports, quizzes, flashcards — runs the long ones in the background and downloads when ready.

### Roadmap *(separate release, its own spec)*
- `notebooklm-suggest` — audit your material and recommend notebooks worth building

---

## Quick install

### Claude Code
```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install notebooklm-superengine@revxl-marketplace
```
Then run `/notebooklm-setup`.

### Claude Desktop
Skills install via Customize → Skills. **Note:** setup itself must run in **Claude Code** (it installs software) — Desktop/Cowork can't install. The SessionStart hook will tell you this if you try.

Full step-by-step in the [marketplace INSTALL guide](../../README.md#install).

---

## How to use it

Just talk to Claude:

| Say this | What happens |
|----------|--------------|
| "set up notebooklm" | `notebooklm-setup` installs + signs you in |
| "my notebooklm login expired" | `notebooklm-setup reauth` refreshes the sign-in |
| "list my notebooks" | (after setup) Claude runs the CLI for you |

You don't need command names. Triggers match how people actually talk.

---

## Dependencies

- **Claude Code** (the terminal app). Setup installs software, so it cannot run in Claude Desktop / Cowork.
- **Python** — setup installs 3.12 via winget (Windows) / Homebrew (Mac) if you don't have ≥3.10.
- **A Google account** with NotebookLM access.
- Windows: Microsoft Edge (ships with Windows 10/11). Mac: nothing extra — Playwright Chromium is installed into the isolated environment.
- Soft pairing: if `workspace-superengine` is installed, its session lifecycle complements this; no hard dependency.

---

## Compatibility

| Platform | Skills | Setup can run? |
|----------|--------|----------------|
| Claude Code (CLI / desktop / IDE) | ✅ | ✅ |
| Claude Desktop / Cowork | ✅ (loaded) | ❌ (installs software — use Claude Code) |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
