# Changelog — notebooklm-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.4.0 — 2026-05-16

### Added

- **Milestone 4 (final skill): `notebooklm-suggest`** — the deep, privacy-bounded build-audit. Niche auto-discovery from Claude context (super-setup 0.5 privacy boundary) + scan inference, one-line confirm, interview only as last resort. Two-pass read: metadata (free/private) → snippet (consent-gated). Recommend-only — never builds or uploads. Dedup vs the titles cache ("add to existing" vs "build new"). Ranked top 5–7. Per-pick soft handoff to `/notebooklm-build` / `-transcripts` / `-youtube`. Has pre-setup value (dedup skipped + warned when NotebookLM not installed).

### Notes

- Completes the planned skill set: setup, doctor, build, ask, transcripts, youtube, studio, suggest (8 skills) + the dual-duty `notebook-suggest` hook.

## 0.3.0 — 2026-05-16

### Added

- **Milestone 3: source breadth + outputs.**
- Skill: `notebooklm-transcripts` — build/extend a notebook from call transcripts. v1 sources: explicit paths, pasted text, `~/Downloads` scan with filename heuristics (Fathom/Fireflies/Otter/etc.). Bulk-safety confirmation; temp-file cleanup; cache refresh. Vendor APIs explicitly deferred.
- Skill: `notebooklm-youtube` — native YouTube URL ingest **+** parallel `source add-research --mode deep --no-wait` so the notebook covers the video and researched web base. Optional transcript enrichment pulls yt-dlp/ffmpeg **on demand only** (winget/brew + venv pip), with graceful fallback to native ingest if declined.
- Skill: `notebooklm-studio` — generate podcast/video/mind-map/slide-deck/report/quiz/flashcards and download. Async by design: ask-before-generate, kick off → track (`artifact wait`/`list`) → notify → ask-before-download to the workspace `output/`. Mind-map special-cased as sync. Honors the rate-limit/long-run reality.

### Notes

- All three reuse the verified mechanics from M1/M2: setup/auth gating (working-but-unmarked tolerated), the `id<TAB>title` UTF-8/LF titles cache (refreshed after any list), and `docs/command-surface.md` autonomy rules (`generate`/`download` are ask-before).

## 0.2.1 — 2026-05-16

### Fixed

- **Test-pass findings against a live install (non-destructive validation on Windows).**
- **Marker false-negative:** a working install done before the plugin (or by hand) had no state marker, so `notebooklm-setup`, `notebooklm-doctor`, and the SessionStart hook all falsely reported "not set up". `notebooklm-setup` Phase 1 now detects a working-but-unmarked install (CLI present + live auth valid) and *just stamps the marker + seeds the cache* — no reinstall, no re-auth. `notebooklm-doctor` reframes check 1: marker absence is informational, not a broken-install verdict; if the real checks pass it reports "works, unregistered — run setup once to stamp (instant)".
- **CRLF cache bug:** caches written in Windows text mode are CRLF; the `notebook-suggest` hook leaked a trailing `\r` into the emitted notebook title. Hook now strips CR defensively. Cache-write instructions in `notebooklm-setup` / `-build` / `-ask` tightened to be deterministic: `list --json`, keys `id`/`title`, UTF-8, LF newlines, skip empty rows.

### Verified

- `notebooklm-doctor` checks 2–7 correct against the live install; `list --json` schema (`notebooks[].{id,title,index,created_at,is_owner}`) matches the cache convention; cache→hook pipeline works end-to-end with 70 real notebooks; hook query/build/silent branches correct including the CRLF case.

## 0.2.0 — 2026-05-16

### Added

- **Milestone 2: core loop + diagnostics + dual-duty hook.**
- Skill: `notebooklm-doctor` — read-only health check. 7 checks (marker, venv/Python, CLI, PATH wrapper, live auth, notebooks reachable, profiles path), one pass/fail table, single headline remedy by precedence. Never mutates.
- Skill: `notebooklm-build` — create a notebook / add to existing; add URL/YouTube/file/folder/pasted sources with bulk-safety confirmation; wait for READY; refresh the titles cache.
- Skill: `notebooklm-ask` — resolve target notebook (named/active/disambiguate), ask with optional `--json` citations, honest attribution, never `--save-as-note` without explicit confirm; refresh the titles cache.
- Hook: `notebook-suggest` (`UserPromptSubmit`) — **dual duty, cheap, no API/model calls.** (1) Query nudge: prompt matches a cached notebook title → offer `/notebooklm-ask`. (2) Light build nudge: no notebooks cached + research-intent prompt → offer `/notebooklm-build` (or `/notebooklm-suggest` when present). Reads only `~/.notebooklm/notebooks.cache`.
- Titles cache convention (`~/.notebooklm/notebooks.cache`, `id<TAB>title`) seeded by `notebooklm-setup` Phase 7 and refreshed by `-build` / `-ask`.

### Changed

- `notebooklm-setup` Phase 7 now seeds the titles cache so the suggestion hook works from first use.

## 0.1.0 — 2026-05-16

### Added

- Initial release. **Milestone 1: plugin scaffold + `notebooklm-setup`.**
- Skill: `notebooklm-setup` — cross-platform (Mac + Windows) install, Google sign-in, and verify for the `notebooklm-py` CLI. Sub-modes: `reauth`, `update`, `uninstall`. Every known Windows/Mac failure mode from the cross-platform bring-up baked in as guardrails (Edge channel instead of bundled Chromium on Windows; no `AutomationControlled` launch arg; synchronous self-detecting login; full `*PSIDTS` cookie wait; profiles-migration reconciliation).
- SessionStart hook (`hooks/session-start` + polyglot `hooks/run-hook.cmd`) on `startup|clear|compact`: silent when set up; nudges `/notebooklm-setup` when the install state marker is absent. Pure marker-file check — no network, no CLI calls.
- `docs/command-surface.md` — the local-only NotebookLM CLI reference + autonomy rules (run-without-asking vs. ask-first).
- `docs/known-issues-windows-mac.md` — durable remedy map for setup verification failures.

### Notes

- **Local-only by design.** No MCP server, tunnel, or extra accounts. Cowork is explicitly out of scope (the broker/443 path is unsolved and a poor fit for non-technical clients).
- Setup must run in Claude Code — it installs software; Claude Desktop / Cowork cannot.
- Roadmap skills (`notebooklm-doctor`, `-build`, `-ask`, `-transcripts`, `-youtube`, `-studio`, `-suggest`) ship in subsequent versions, each as its own spec → plan → implement cycle.
