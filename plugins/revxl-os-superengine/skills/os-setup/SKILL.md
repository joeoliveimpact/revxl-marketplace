---
name: os-setup
description: Use this skill when the user wants to set up, install, configure, or onboard REVXL OS. Triggers include "set up revxl os", "/os-setup", "configure revxl", "install revxl", "onboarding", "set up my agents", "wire up the os", or first-time use after `/plugin install revxl-os-superengine`. Walks the user through a sequential, branching configuration: source providers (transcripts/portals/emails/DMs), task sync target, Telegram bot pairing, agent schedules. Writes the workspace folder structure, the `.mcp.json` config, the Telegram allowlist, and a `~/.claude/revxl-os/config.json` for the agents to read. Designed for non-technical users — narrate every step, confirm before writes, never assume.
---

# os-setup

The install lynchpin for REVXL OS. Without this, no agent has a workspace, no MCP is wired, and Telegram isn't paired.

This is the difference between OpenClaw's "clone repo, edit five config files, hope" install and our "answer 6 questions, done" install.

---

## Pre-flight checks (do these FIRST, before any questions)

Confirm before asking anything:

1. **Claude Code version >= 2.1.80** (Channels feature requires it).
   Check: `claude --version`. If older, tell the user: "REVXL OS needs Claude Code 2.1.80 or newer for the Channels feature. Update with: `npm i -g @anthropic-ai/claude-code` (or your install method) and re-run setup."

2. **Bun installed**.
   Check: `bun --version`. If missing, walk through install: "Bun is needed to run the Telegram channel and webhook server. Install: `curl -fsSL https://bun.sh/install | bash` (Mac/Linux/WSL) or download from https://bun.sh. Re-run setup after."

3. **`~/.claude/` exists and is writable**. If not, fail loud — the user has a broken Claude Code install.

4. **`claude-workspace-superengine` installed.** If not, recommend installing it ("REVXL OS pairs with `claude-workspace-superengine` for session lifecycle. Install with `/plugin install claude-workspace-superengine@revxl-marketplace`. Optional but recommended.")

If any pre-flight fails, stop. Don't proceed to questions until the user fixes it.

---

## Workspace folder scaffold

Once pre-flight passes, **create the workspace folders SILENTLY** (no question — these are universal):

```
~/.claude/revxl-os/
├── config.json                # written incrementally as questions are answered
├── tasks.json                 # initialized as {"version": 1, "tasks": [], "last_modified": "..."}
├── transcripts/
│   ├── client-calls/
│   ├── sales-calls/
│   └── _meta.json             # {"adapter": null, "last_sync": null}
├── dms/
│   └── _meta.json
├── emails/
│   └── archive/
│   └── _meta.json
├── saved-content/
│   └── _meta.json
└── portals/
    └── _meta.json
```

Mention briefly: "Created your REVXL OS workspace at `~/.claude/revxl-os/`. Now let's wire up your sources."

---

## Question flow (sequential, narrated, one at a time)

Ask ONE question at a time. After each answer, write to `config.json` immediately and confirm. Never batch.

The `config.json` shape (built up across the flow):

```json
{
  "version": 1,
  "user": {
    "name": "...",
    "timezone": "..."
  },
  "sources": {
    "transcripts": { "adapter": "fathom" | "otter" | "fireflies" | "granola" | "zoom" | null, "credentials_ref": "..." },
    "calendar": { "adapter": "google" | "apple" | "outlook" | null },
    "email": { "adapter": "gmail" | "outlook" | null, "filter_label": "..." },
    "portals": [ { "adapter": "ghl" | "skool" | "circle" | ..., "community_id": "..." } ],
    "dms": [ { "platform": "instagram" | "facebook" | "linkedin", "handle": "..." } ]
  },
  "task_target": {
    "system": "internal" | "ghl" | "clickup" | "airtable" | "notion" | "todoist",
    "credentials_ref": "..."
  },
  "telegram": {
    "bot_username": "...",
    "supergroup_id": "...",
    "topics": { "general": "...", "tasks": "...", "dms": "...", "briefing": "...", "alerts": "..." },
    "allowlist": [ "..." ]
  },
  "schedules": {
    "ingest_nightly": "0 1 * * *",
    "morning_brief": "0 7 * * *",
    "task_sync_out": "0 2 * * *"
  },
  "channels_enabled": ["telegram", "revxl-webhook-channel"]
}
```

### Q1: Name + timezone
"What should I call you, and what timezone are you in? (e.g., 'Joe, America/New_York'). I'll use this for the morning brief and any time-sensitive output."

Write to `config.user`.

### Q2: Calendar source
"What calendar do you use? (Google / Apple / Outlook / none)"
- Google → check that `gws-mcp` is configured. If not, walk them through `revxl-google-ws-mcp` skill OR offer to write the MCP config entry directly if they've already authed elsewhere.
- Apple → flag as v0.2 (no Apple Calendar MCP yet); proceed without
- Outlook → flag as v0.2; proceed without
- none → proceed

### Q3: Email source
"Want REVXL OS to scan your email for commitments and tasks? (yes-Gmail / yes-Outlook / no)"
- yes-Gmail → confirms GWS MCP. Then ask: "Should it scan ALL email, or only emails matching a label like `revxl-tasks`? (Recommended: label-only — easier to control what gets pulled.)"
- yes-Outlook → flag as v0.2
- no → skip

### Q4: Call transcript provider
"Do you record calls and use a transcript service? (Fathom / Otter / Fireflies / Granola / Zoom AI Companion / none)"

For each, walk through what's needed:
- **Fathom** → asks for API key (https://fathom.video/api), writes credential ref to OS keychain or `.env`, sets adapter
- **Otter** → API key flow (different path)
- **Fireflies** → API key
- **Granola** → no public API as of v0.1; flag as v0.2 / browser-scraping path needed
- **Zoom** → uses Zoom MCP if user has Zoom plugin installed; otherwise points to setup
- none → proceed

### Q5: Client community / portal
"Where do your paying clients chat with you? (GoHighLevel / Skool / Circle / Mighty / Kajabi / Slack / Discord / none / multiple)"

Multi-select (user can pick 1+). For each:
- **GoHighLevel** → reuses GHL MCP from `ghl-coach-superengine`. Asks for the community ID. If GHL MCP not yet installed, recommend `/plugin install ghl-coach-superengine@revxl-marketplace`.
- **Skool / Circle / Mighty / Kajabi** → flag adapter as v0.2 (not yet built)
- **Slack** → use Slack MCP if available
- **Discord** → use Discord channel plugin (sanctioned, in claude-plugins-official)
- none → proceed

### Q6: DMs (engaged-reply only)
"Want REVXL OS to monitor and draft DM replies? Note: cold outbound is NOT supported in v0.1 to protect your accounts. Only engaged conversations. (Instagram / Facebook / LinkedIn / SMS / none / multiple)"

For each:
- **Instagram / Facebook / LinkedIn** → requires `revxl-stealth-browser` plugin. If not installed, recommend `/plugin install revxl-stealth-browser@revxl-marketplace` and walk through Botright Chromium setup.
- **SMS** → uses iMessage channel (Mac only) if available
- none → proceed

### Q7: Saved content collection (content brainstorm seed)
"Do you save IG/FB posts to a dedicated collection for content inspiration? If yes, I'll have an agent pull from it daily so the future content superengine has source material. (yes-Instagram / yes-Facebook / both / no / not yet)"

If yes: ask for the collection name. Save to config. Same `revxl-stealth-browser` dependency.

### Q8: Task sync target
"Where do you want your tasks to land? (Just Telegram / GoHighLevel / ClickUp / Airtable / Notion / Todoist / Custom dashboard / Multiple)"

- **Just Telegram** → only the canonical `tasks.json` + Telegram brief; no external sync
- **GHL** → uses `ghl-coach-superengine` GHL MCP. Tasks become GHL contact notes or opportunities (user picks).
- **ClickUp / Airtable / Notion / Todoist** → flag as v0.2 (adapters not yet built); offer to fall back to Telegram-only
- **Custom dashboard** → install `revxl-os-dashboard` plugin (forked ccboard) — recommend if available
- **Multiple** → multi-select, user picks

### Q9: Schedule preferences
"When should REVXL OS run? Defaults: nightly ingestion at 1am, morning brief at 7am, sync to external systems at 2am. Want to change any of these?" (Keep defaults / Customize)

If customize: ask each in turn.

### Q10: Telegram bot pairing
This is the longest step. Walk through:

1. "Create a Telegram bot: open @BotFather, send `/newbot`, give it a name (e.g., `REVXL OS — Joe`). Copy the token BotFather returns."
2. Wait for user to paste the token. Then write it to `~/.claude/channels/telegram/.env` (or run `/telegram:configure <token>`).
3. "Now create a supergroup in Telegram (any name), add your bot as admin, then enable Topics in group settings."
4. "Create five topics in this order: `general`, `tasks`, `dms`, `briefing`, `alerts`. The order matters — REVXL OS uses the topic IDs to route."
5. "Restart Claude Code with `--channels`: `claude --channels plugin:telegram@claude-plugins-official`. Then DM your bot any message — you'll get a pairing code. Run `/telegram:access pair <code>` to add yourself to the allowlist."
6. After pairing: write supergroup ID and topic IDs to `config.telegram`.
7. Lock down access: `/telegram:access policy allowlist`.

---

## Final write step

After all questions answered, do these in order:

1. **Write `~/.claude/revxl-os/config.json`** (atomic write).
2. **Write `.mcp.json` entries** for each configured MCP source. If a project-level `.mcp.json` exists, ask before modifying. Otherwise write to user-level `~/.claude.json` MCP config.
3. **Register schedules** via `os-schedule-manage` skill internals (cron file or system scheduler — implementation detail).
4. **Initialize `tasks.json`** with empty array.
5. **Print summary** of what was configured.
6. **Test fire**: optionally invoke `task-add` with a placeholder task ("Test task from os-setup — ✓ delete me") to confirm the write path works. Then immediately remove it.

---

## Output to user at end

Format:
```
✓ REVXL OS is configured.

Sources wired up:
  • Calendar: Google
  • Email: Gmail (label: revxl-tasks)
  • Transcripts: Fathom
  • Portal: GHL community "Engine For Impact"
  • DMs: not configured (skipped)
  • Saved content: not configured (skipped)

Tasks land in: GHL contact notes + Telegram

Schedules:
  • 1:00 AM — nightly ingestion
  • 7:00 AM — morning brief → #briefing
  • 2:00 AM — sync to GHL

Telegram bot paired: @YourBotName
Supergroup: REVXL OS Joe (ID: -100xxxx)

To start the OS, run:
  claude --channels plugin:telegram@claude-plugins-official

Then DM your bot. Or text in #tasks: "remind me to test the system"
```

---

## Tone rules

- Plain English. No jargon without explanation.
- Narrate before acting on anything that writes a file: "I'm about to write your config to `~/.claude/revxl-os/config.json`. Ready?"
- Confirm after every write: "Done ✓"
- For multi-select questions, accept either comma-separated or "all of the above"
- If the user picks something that's v0.2 (e.g., Apple Calendar), don't pretend — say "That adapter isn't ready in v0.1. Want to skip and add it later, or pick a different source?"
- Never silently fail. If an MCP write fails because the user's `.claude.json` is corrupted, surface it.

---

## Resumability

If the user runs `/os-setup` mid-flow (e.g., they got interrupted), detect existing `config.json` and ask: "I see you've already configured X, Y, Z. Continue where we left off (Z came next), reconfigure from scratch, or update one specific section?"

Don't make them redo the whole flow.

---

## What this skill does NOT do

- **Doesn't run agents.** That happens after setup, when the user starts Claude Code with `--channels`.
- **Doesn't fetch data.** That's the ingest-* skills' job.
- **Doesn't generate the morning brief.** That's `task-morning-brief`.
- **Doesn't validate that data sources actually work.** It writes config; the agents validate on first run. (Future enhancement: add a `os-status` test-fire that confirms every source returns data.)

Setup. Configure. Done. The agents do the work after.
