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

### `notebooklm-setup` *(shipping in v0.1.0)*
**Triggers:** "set up notebooklm", "install notebooklm", "notebooklm isn't working", "sign in to notebooklm", "my notebooklm login expired", "update notebooklm", "uninstall notebooklm"

The front door. Cross-platform install + Google sign-in + verify, with every known Windows/Mac failure mode pre-empted. Sub-modes: `reauth` (refresh an expired sign-in), `update` (upgrade the tool), `uninstall` (clean removal). Every other skill below depends on this one.

### Roadmap *(separate releases, each its own spec)*
- `notebooklm-doctor` — diagnose a broken install, name the exact fix
- `notebooklm-build` — create notebooks, add sources (URLs, files, folders)
- `notebooklm-ask` — query notebooks; in-session "you have a notebook for this" hints (hook)
- `notebooklm-transcripts` — build notebooks from Fathom/Fireflies call transcripts
- `notebooklm-youtube` — yt-dlp + NotebookLM deep research in parallel
- `notebooklm-studio` — mind maps, videos, slide decks, reports
- `notebooklm-suggest` — recommend which notebooks to build from your material

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
