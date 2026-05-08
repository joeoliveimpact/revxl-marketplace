# Changelog — revxl-os-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-08

### Added
- Initial scaffold (skeleton — not yet functional).
- Plugin manifest, README, directory structure for agents/skills/commands.

### Planned for 0.1.0 release
- Agent: `os-morning-agent` — scheduled daily briefing → Telegram
- Agent: `os-tasks-agent` — scheduled + on-demand task surfacing
- Agent: `os-dm-triage-agent` — event-triggered DM triage and draft replies
- Skill: `os-setup` — one-shot configuration walkthrough
- Skill: `os-status` — agent and queue status check
- Skill: `os-schedule-manage` — configure agent schedules
- Command: `/os-start` — spawn Claude Code with channels enabled

### Compatibility
- Claude Code: 2.1.80+ (requires Channels feature)
- Claude Desktop: not supported (Channels is a Claude Code feature)
