# revxl-os-superengine

> Autonomous coaching ops, running in your Claude Code session. A task agent that collects commitments from everywhere you make them, a DM triage agent, and an orchestrator — all delivered through Telegram.

---

## What this plugin does

If you've looked at OpenClaw, Manus, or any of the autonomous-agent platforms and thought _"that's a lot of infrastructure for what I actually need,"_ this is the answer.

`revxl-os-superengine` ships three opinionated agents that run on schedules, listen to event triggers, push results to your phone over Telegram, and let you reply or approve actions remotely. No separate runtime. No daemon. Just Claude Code with channels enabled.

When OpenClaw breaks (and it does — it's fragile and rarely updated), you're stuck. When this breaks, you tell Claude in-session "fix that skill" and it fixes itself. That's the difference.

Built on Anthropic's [Channels](https://code.claude.com/docs/en/channels) feature (research preview, requires Claude Code 2.1.80+).

---

## Agents

### `task-agent` (the main one)
**Triggers:** scheduled (nightly collect, 7am brief), event (Telegram add), on-demand

The orchestrator for your entire task pipeline. Owns:
- Nightly collection from every configured source (email, calendar, call transcripts, DMs, client portals)
- Promise extraction — coaches commit to things constantly in transcripts and emails; this agent finds them
- A canonical task store (per-user SQLite) — single source of truth
- Sync-out to whatever task system you already use (GHL, ClickUp, Airtable, Notion, custom dashboard)
- Morning brief: prioritized + scheduled against today's calendar, posted to Telegram
- On-demand adds via the Telegram task channel

### `dm-triage-agent`
**Trigger:** event (incoming DM via Telegram channel or stealth-browser-detected notification)

Categorizes inbound DMs (IG/FB/LinkedIn/SMS/email), drafts replies, queues for your approval. Cold replies go through ManyChat or your Meta app; engaged replies route through `revxl-stealth-browser` (Botright-based, anti-detection).

### `orchestrator-agent`
**Trigger:** any message in #general topic that isn't routed elsewhere

Free-form Q&A, fallback for queries that don't match a specialized agent. Delegates to task-agent or dm-triage-agent when appropriate.

---

## Telegram channel topology

The plugin uses **Telegram supergroup topics** so each agent has its own channel:

```
REVXL OS (Telegram supergroup)
├─ #general       ← orchestrator-agent (free-form, fallback)
├─ #tasks         ← task-agent (text "remind me to call Maya")
├─ #dms           ← dm-triage-agent (incoming DMs + drafts)
├─ #briefing      ← read-only: morning brief lands here
└─ #alerts        ← system events, low-priority pings
```

Routing rule: specialized topics dispatch directly (no orchestration overhead). #general routes through the orchestrator.

---

## Skills

### Task pipeline (`task-agent` skills)
- `task-collect` — nightly run, pulls from all configured sources
- `task-extract` — parses transcripts/emails for commitments ("I'll send that by Friday")
- `task-morning-brief` — 7am, prioritizes against today's calendar, posts to #briefing
- `task-add` — listens on #tasks for manual adds via Telegram
- `task-sync-out` — pushes canonical store to GHL/ClickUp/Airtable/dashboard

### Onboarding (`os-setup` skill)
A walkthrough that asks the new user:
1. Calendar source (Google / Apple / Outlook)
2. Email source (Gmail / Outlook / IMAP)
3. Call transcript provider (Otter / Fireflies / Granola / Fathom / Zoom AI / none)
4. DM platforms to monitor (IG / FB / LinkedIn / SMS / none)
5. Existing task system (GHL / ClickUp / Airtable / Notion / Todoist / none → use built-in dashboard)
6. Daily brief time (default 7am)

Then it writes the right MCP entries, registers the right channels, configures schedules.

### Operations
- `os-status` — quick "where am I" check (active agents, recent triggers, queued items)
- `os-schedule-manage` — configure or disable agent schedules

---

## Commands

- `/os-start` — spawn Claude Code with channels enabled and the right plugins wired

---

## Install

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install revxl-os-superengine
/plugin install telegram@claude-plugins-official
/plugin install revxl-webhook-channel@revxl-marketplace
/plugin install revxl-stealth-browser@revxl-marketplace
```

Then run the setup skill:
```
/os-setup
```

---

## Requirements

- Claude Code v2.1.80 or later
- [Bun](https://bun.sh) (for channel runtimes)
- Python 3.10+ (for stealth browser if using DM triage)
- A Telegram account (free)
- macOS or Linux. Windows users: install via WSL Ubuntu.

---

## Pairs with

- **`claude-workspace-superengine`** — workspace lifecycle (scaffold + pickup + closeout). Recommended.
- **`revxl-webhook-channel`** — custom MCP webhook channel for GHL, Cal.com, Stripe, custom POSTs. Recommended for incoming events.
- **`revxl-stealth-browser`** — Botright-based browser automation for DM triage on platforms without sanctioned APIs (IG, FB, LinkedIn). Recommended if using DM triage.
- **`ghl-coach-superengine`** — GoHighLevel toolkit. If you use GHL, task-agent syncs there.

---

## Why this beats OpenClaw

| | OpenClaw | revxl-os-superengine |
|---|---|---|
| Install | Multi-step setup, separate runtime | 4x `/plugin install`, run `/os-setup` |
| Self-healing when broken | "Fork the repo and fix" | "Tell Claude to fix the skill" |
| Update cadence | Sporadic, breaks on bumps | Versioned in marketplace, updates cleanly |
| Specialized to coaching | No | Yes |
| Multi-channel UX | Single chat | Topics per agent in one supergroup |
| Permission model | All-or-nothing | Native Claude Code permission relay |

---

## Status

v0.1.0 — research preview / scaffold. Channels feature is itself in preview; expect occasional breakage as the API stabilizes. Report issues at [revxl-marketplace/issues](https://github.com/joeoliveimpact/revxl-marketplace/issues).

---

## License

MIT — see `LICENSE`.
