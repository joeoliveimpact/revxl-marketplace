# Changelog — revxl-webhook-channel

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-08

### Added
- Initial scaffold (skeleton — not yet functional).
- Plugin manifest and README.

### Planned for 0.1.0 release
- `webhook.ts` — Bun MCP server: stdio transport + HTTP listener on configurable port
- `claude/channel` capability declaration with two-way reply tool
- `claude/channel/permission` capability for remote approval relay
- Sender gating via signature headers (GHL, Cal.com, Stripe, custom HMAC)
- Pre-wired routes: `/ghl`, `/calcom`, `/stripe`, `/dm`, `/event`
- `package.json` for Bun dependency management

### Compatibility
- Claude Code: 2.1.81+ (Channels + permission relay)
- Runtime: Bun (Node and Deno also work; Bun is the documented default)
