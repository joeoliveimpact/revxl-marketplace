# Changelog — ghl-coach-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-07

### Added
- Initial release.

#### Skills (8)
- `ghl-mcp-installer` — non-technical step-by-step GoHighLevel MCP install
- `ghl-workspace-setup` — once-per-coach intake; scaffolds the 13-file persistent workspace via Filesystem MCP, pulls live structure from GHL via MCP, captures coach identity/voice/offers
- `ghl-docs` — GHL feature reference desk; in-prompt knowledge for coaching-core features + WebFetch fallback to help.gohighlevel.com for everything else; always cites sources
- `ghl-session-pickup` — start-of-session lifecycle: reads workspace, refreshes state from GHL via MCP, runs notifier, presents one-screen brief, agrees on session goal
- `ghl-session-closeout` — end-of-session lifecycle: refreshes trackers, appends Checkpoint, rewrites handoff, logs wins, RULES.md compliance check, verification table
- `ghl-tagging` — canonical contact tag taxonomy + MCP execution patterns
- `ghl-pipelines` — Sales DM + Client pipeline management with coordinated tag updates
- `ghl-automations` — GHL-native workflow design with priority order and trigger→action framework

#### Agents (2)
- `ghl-coach-assistant` (Claude Code only) — multi-step GHL operator for end-to-end lead processing
- `ghl-notifier` — scores items in workspace state files by urgency; returns top-3 in-conversation brief; creates GHL internal tasks via MCP for items urgent >24h

#### Workspace
- 13-file persistent per-coach workspace at `~/REVXL-GHL-Workspaces/{slug}/`:
  - Setup: RULES, CLAUDE, coach-profile, offers, pipelines
  - State trackers: follow-up, client-roster, attention-needed
  - Inventory: automation-inventory, wins
  - Strategy: kpis
  - Lifecycle: Checkpoint, handoff

### Requires (external)
- [GoHighLevel-MCP (mastanley13)](https://github.com/mastanley13/GoHighLevel-MCP) — `ghl-mcp-installer` walks coaches through this
- Filesystem MCP — required for workspace file persistence

### Compatibility
- Claude Desktop: skills + workspace files (agents not available in Desktop subagent mode)
- Claude Code: skills + agents + workspace files

### Removed
- (Pre-release) `ghl-session-startup` — folded into the richer file-backed `ghl-session-pickup`
