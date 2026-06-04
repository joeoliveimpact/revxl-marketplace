# Changelog — gokollab-community-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-06-04

### Added
- Initial release.

#### Skills (6)
- `gokollab-setup` — first-run installer + setup interview: turns on bypass permissions, detects OS (Windows/Mac), checks + installs dependencies, drives a one-time guided login to capture the operator's own clientclub token (no terminal), discovers + confirms the community channel map, runs the "ask the coach" interview to build `onboarding-config.json`, then self-tests.
- `onboard-member` — onboard a community member by tier: approves them from the request queue, reads their tier from GoHighLevel (via the GHL MCP), then runs that tier's recipe — adds them to the right channels, creates their private 1:1 channel (if the tier gets one), pins their call-recording post, and posts welcomes.
- `create-fathom-deep-post` — turn one Fathom group-call recording into a featured "Full Call Notes" recap post.
- `add-1on1-call-to-history` — append one 1:1 call as an enriched entry to a client's pinned call-history post (prepend-only, with a mandatory backup guardrail).
- `update-client-1on1-history` — scan Fathom calls over a window and route each to the right post (group deep-post vs 1:1 history).
- `fathom-revxl-setup` — recurring health/auth verify (the daily smoke test).

#### Bundled
- `clientclub` CLI binaries for Windows, macOS (Intel + Apple Silicon), and Linux.
- Token-mint helpers (PowerShell / Python / shell) + `config.toml` header template.

### Requires (external)
- **GoHighLevel MCP** — member tier lookup (tag / custom field).
- **A browser-automation MCP** — the one-time login capture; `gokollab-setup` installs/connects it.
- A **clientclub community you administer**.

### Compatibility
- **Claude Code:** skills + slash commands + bundled CLI.
- **Claude Desktop:** skills (slash commands not available).
