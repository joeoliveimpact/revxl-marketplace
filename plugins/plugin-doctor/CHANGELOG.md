# Changelog — plugin-doctor

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.1] — 2026-07-03

### Changed
- **Stall A now fixes itself.** The doctor downloads the staged, fully reversible updater
  script from [Claude-marketplace-updater](https://github.com/joeoliveimpact/Claude-marketplace-updater)
  and launches it detached (`--stage1`, then `--stage2` if needed) — Claude Desktop quits,
  the cache clears, Desktop reopens, plugins re-sync. Works from a Claude Desktop chat or
  Claude Code; the user's session survives the restart. The previous CLI/UI walkthroughs
  remain as manual fallbacks when the script can't be fetched.

## [0.1.0] — 2026-06-30

### Added
- Initial release. One skill (`/plugin-doctor`) that diagnoses and fixes the two plugin-update stalls: **Stall A** — plugin stuck on an old version (marketplace refresh + force-reinstall, with CLI commands for Claude Code and step-by-step UI walkthrough for Claude Desktop, including the quit-and-reopen step the Desktop sync bug requires); **Stall B** — in-app directory install failing with `404 Not Found: plugin_<id>` (git-path install bypass + report path). Config-safety first: `${CLAUDE_PLUGIN_DATA}` and `~/.claude/revxl/` survive reinstalls, with an optional temp backup for belt-and-suspenders.
