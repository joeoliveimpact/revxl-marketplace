# Changelog — revxl-os-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-08

### Added
- Initial scaffold (skeleton — not yet functional).
- Plugin manifest, README, directory structure for agents/skills/commands.

### Architecture locked for 0.1.0
- **Three agents:** `task-agent` (orchestrates the whole task pipeline), `dm-triage-agent`, `orchestrator-agent`
- **Telegram supergroup topology:** `#general`, `#tasks`, `#dms`, `#briefing`, `#alerts` — specialized agents dispatch directly per topic; orchestrator handles `#general` fallback
- **Shared workspace folders** at `~/.claude/revxl-os/` — single source of truth read by `task-agent` AND the future `content-superengine`. Folders: `transcripts/`, `dms/`, `emails/`, `saved-content/`, `portals/`. Same JSON shape per item across platforms.
- **Ingestion layer (NEW):** five skills feed the workspace folders before `task-collect` runs. Each uses the adapter pattern (one skill, multiple platform adapters):
  - `ingest-transcripts` (v0.1 adapter: Fathom; v0.2: Otter/Fireflies/Granola/Zoom)
  - `ingest-portals` (v0.1 adapter: GHL community via GHL MCP; v0.2: Skool/Circle/Mighty/Kajabi/Slack/Discord)
  - `ingest-emails` (v0.1 adapter: Gmail via GWS MCP)
  - `ingest-dms` (v0.1 adapter: Instagram via Botright; v0.2: FB/LinkedIn)
  - `ingest-saved-content` (v0.1 adapter: Instagram saved collection via Botright)
- **Task pipeline reads from the workspace folders.** `task-collect` scans each folder for new items, calls `task-extract` for promise extraction, writes via `task-add` to `tasks.json`.
- **Sync-out (v0.1):** internal canonical store (`tasks.json`) + ccboard fork as task dashboard + GHL sync via `ghl-coach-superengine` handoff
- **DM browser:** Botright via new `revxl-stealth-browser` plugin (Python MCP wrapper, antibot detection)
- **MCP delivery:** `.mcp.json` config (NOT Claude Desktop connectors — agents run in terminal Claude Code)
- **Onboarding:** `os-setup` skill asks for sources, portals, and target system at install time. Multi-select per category. Writes MCP config, registers schedules, pairs Telegram bot.

### Planned skills for 0.1.0 release

**Ingestion layer (workspace folder writers):**
- `ingest-transcripts` (Fathom adapter)
- `ingest-portals` (GHL community adapter)
- `ingest-emails` (Gmail adapter)
- `ingest-dms` (Instagram via Botright — after stealth-browser plugin)
- `ingest-saved-content` (Instagram via Botright — after stealth-browser plugin)

**Task pipeline (reads from workspace folders):**
- `task-add` — write path (FIRST vertical slice — DONE 2026-05-08)
- `task-collect` — nightly pull from workspace folders
- `task-extract` — promise extraction from transcripts/email/portal text
- `task-morning-brief` — 7am prioritized brief
- `task-sync-out` — push to dashboard + GHL

**Operations:**
- `os-setup` — onboarding walkthrough (writes MCP config, registers schedules, pairs Telegram)
- `os-status` — agent + queue status
- `os-schedule-manage` — schedule config

### Skills already shipped
- `task-add` — 2026-05-08 (commit 931326c)

### Compatibility
- Claude Code: 2.1.80+ (requires Channels feature)
- Claude Desktop: not supported (Channels is a Claude Code feature)
