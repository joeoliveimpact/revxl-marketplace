# Changelog — notebooklm-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
