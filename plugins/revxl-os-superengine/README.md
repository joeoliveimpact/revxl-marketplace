# revxl-os-superengine

> Autonomous coaching ops, running in your Claude Code session. Daily briefings, task surfacing, and DM triage — delivered to your phone via Telegram.

---

## What this plugin does

If you've looked at OpenClaw, Manus, or any of the other autonomous-agent platforms and thought _"that's a lot of infrastructure for what I actually need,"_ this is the answer.

`revxl-os-superengine` ships three opinionated agents that run on their own schedules, push results to your phone over Telegram, and let you reply or approve actions remotely. No separate runtime. No daemon. Just Claude Code with channels enabled.

Built on Anthropic's [Channels](https://code.claude.com/docs/en/channels) feature (research preview, requires Claude Code 2.1.80+).

---

## Agents

### `os-morning-agent`
**Trigger:** Scheduled (default 7:00 AM local)

Pulls calendar agenda, top inbox items, and due tasks. Posts a single brief to your Telegram. You read it from bed.

### `os-tasks-agent`
**Trigger:** Scheduled (every 4 hours) + on-demand via Telegram message

Tracks open tasks, flags overdue, drafts updates. When something needs your decision, it pings you with options.

### `os-dm-triage-agent`
**Trigger:** Event (incoming message via Telegram or future webhook channel)

Categorizes, drafts a reply, queues for your approval. Cold outreach, client DMs, and urgency signals all routed.

---

## Skills

- `os-setup` — One-shot configuration: installs Bun, walks you through Telegram bot creation, pairs your account, registers webhook listeners
- `os-status` — Quick "where am I" check: active agents, recent triggers, queued items
- `os-schedule-manage` — Configure when each agent runs (or disable)

---

## Commands

- `/os-start` — Spawn Claude Code with channels enabled and the right plugins wired

---

## Install

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install revxl-os-superengine
/plugin install telegram@claude-plugins-official
/plugin install revxl-webhook-channel@revxl-marketplace
```

Then run the setup skill:
```
/os-setup
```

The skill walks you through Bun installation, Telegram bot creation via BotFather, pairing your account, and configuring agent schedules.

---

## Requirements

- Claude Code v2.1.80 or later
- [Bun](https://bun.sh) (for the channel runtime)
- A Telegram account (free)
- macOS or Linux. Windows users: install via WSL Ubuntu.

---

## Pairs with

- **`claude-workspace-superengine`** — workspace lifecycle (scaffold + pickup + closeout). Recommended.
- **`revxl-webhook-channel`** — custom MCP webhook channel for GHL, Cal.com, Stripe, and any service that POSTs. Recommended.
- **`ghl-coach-superengine`** — GoHighLevel toolkit. If you use GHL.

---

## Status

v0.1.0 — research preview. The Channels feature is itself in preview; expect occasional breakage as the API stabilizes. Report issues at [revxl-marketplace/issues](https://github.com/joeoliveimpact/revxl-marketplace/issues).

---

## License

MIT — see `LICENSE`.
