# GoKollab Community Superengine

Natural-language automation for your **clientclub / GoHighLevel** community. Run it from Claude Code — no terminal, no scripts.

## What it does
- **Onboard members by tier** — `/onboard [name]`: approves them from the request queue, adds them to the right channels, builds their private 1:1 channel, pins their call-recording post, and posts welcomes (private + community).
- **Group-call recap posts** — turns a Fathom group-call recording into a featured "Full Call Notes" post.
- **1:1 call-history upkeep** — keeps each client's private call-history post updated from their Fathom 1:1s.

## First-time setup (~10–15 min, one login, no terminal)
1. Make sure your **GoHighLevel MCP** is connected (that's how it reads member tiers).
2. Run **`/gokollab-setup`** and follow along. It will:
   - walk you through turning on bypass-permissions mode,
   - install what's missing (handled for you),
   - open a browser once so you can **log in** to your community,
   - read your channels and ask you to confirm them,
   - ask a few questions about your **tiers** and **welcome messages**,
   - run a safe self-test.

## Everyday use
- `/onboard Jane Doe` — onboard a new member end-to-end.
- "post the group call from Wednesday" — group-call recap.
- 1:1 call histories update automatically once wired to your schedule.

## Requirements
- **Claude Code desktop** (the setup turns on bypass-permissions for you)
- **GoHighLevel MCP** connected (member tier lookup)
- A **clientclub community you administer**
- A **browser MCP** (the setup installs/connects it for the login step)

## What's inside
- `skills/` — `gokollab-setup`, `onboard-member`, plus the Fathom→community posting suite
- `cli/bin/` — the `clientclub` CLI for Windows, macOS, Linux
- `cli/token-helpers/`, `cli/config.toml.example` — auth helpers + header template
- `docs/` — operator guide

## Support
Built by Joe Olive · joe@bizzfixx.com · v0.1.0
