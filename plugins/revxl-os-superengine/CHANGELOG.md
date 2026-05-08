# Changelog — revxl-os-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-08

### Added
- Initial scaffold (skeleton — not yet functional).
- Plugin manifest, README, directory structure for agents/skills/commands.

### Architecture locked for 0.1.0
- **Three agents:** `task-agent` (orchestrates the whole task pipeline), `dm-triage-agent`, `orchestrator-agent`
- **Telegram supergroup topology:** `#general`, `#tasks`, `#dms`, `#briefing`, `#alerts` — specialized agents dispatch directly per topic; orchestrator handles `#general` fallback
- **Task pipeline source connectors (v0.1):** Gmail (GWS MCP), Google Calendar (GWS MCP), Telegram task channel (manual add), Fathom (dogfooding — Joe's transcript tool)
- **Task pipeline sync-out (v0.1):** internal SQLite canonical store + ccboard fork as task dashboard + GHL sync via `ghl-coach-superengine` handoff
- **DM browser:** Botright via new `revxl-stealth-browser` plugin (Python MCP wrapper, antibot detection)
- **MCP delivery:** `.mcp.json` config (NOT Claude Desktop connectors — agents run in terminal Claude Code)
- **Onboarding:** `os-setup` skill asks for sources at install time (transcript provider, task system, DM platforms)

### Planned skills for 0.1.0 release
- `task-collect` — nightly pull from all sources
- `task-extract` — promise extraction from transcripts/email
- `task-morning-brief` — 7am prioritized brief
- `task-add` — Telegram listener (FIRST vertical slice)
- `task-sync-out` — push to dashboard + GHL
- `os-setup` — onboarding walkthrough
- `os-status` — agent + queue status
- `os-schedule-manage` — schedule config

### Compatibility
- Claude Code: 2.1.80+ (requires Channels feature)
- Claude Desktop: not supported (Channels is a Claude Code feature)
