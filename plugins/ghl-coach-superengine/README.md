# ghl-coach-superengine

> A done-with-you GoHighLevel toolkit for health, wellness, and fitness coaches. Builds and maintains a persistent per-coach workspace on the local machine. Built for non-technical users.

![demo placeholder](../../docs/demos/ghl-coach-superengine.gif)

---

## What this plugin does

Most coaches dump money into GoHighLevel, then can't make it work — they don't know how to organize contacts, when to move pipeline stages, which automations matter, or what's piling up that needs attention. This plugin closes that gap.

**Eight skills + two agents** that together build a persistent coaching workspace on the coach's machine, refresh it from GHL on every session, surface what needs attention, and execute multi-step work via the GoHighLevel MCP — all in plain English, one step at a time, with constant reassurance.

The skills **guide** the coach through actions they can do themselves AND **execute** actions directly via the MCP. Always plain English. Always one step at a time. Always reassuring.

---

## Skills

### Setup & Reference

#### `ghl-mcp-installer`
**Triggers:** "install GoHighLevel MCP", "connect my GHL to Claude", "set up GHL"

Walks non-technical coaches through installing the [GoHighLevel-MCP](https://github.com/mastanley13/GoHighLevel-MCP) into Claude Desktop step-by-step. Covers Node install, Private Integrations API key, Location ID, building the MCP server, wiring `claude_desktop_config.json`, and verifying.

#### `ghl-workspace-setup`
**Triggers:** "set up my GHL workspace", "onboard me to REVXL", "build my coaching workspace" — runs **once per coach**

Interactive intake that creates **13 persistent workspace files** on the coach's machine via Filesystem MCP. Pulls structure from GHL (pipelines, automations, custom fields), asks for the coach to confirm/edit, then writes everything. From here on, the workspace persists between sessions.

#### `ghl-docs`
**Triggers:** "how do I do X in GHL", "where is the X setting", "can GHL do Y"

GHL feature reference desk. Two-tier knowledge: in-prompt mental model for coaching-core features (contacts, pipelines, calendars, workflows, conversations, forms, memberships), WebFetch fallback to `help.gohighlevel.com` for everything else. Always cites sources.

### Lifecycle

#### `ghl-session-pickup`
**Triggers:** "let's get started", "I'm back", "what's the status?", session start

Reads the workspace, refreshes hot-leads/clients/blockers from GHL via MCP, runs the `ghl-notifier` agent, presents a one-screen brief. Asks the goal-of-session question and routes to the right downstream skill.

#### `ghl-session-closeout`
**Triggers:** "wrap up", "close out", "checkpoint", "handoff for next time"

Refreshes state files post-session, appends a Checkpoint entry, rewrites handoff, logs wins, runs RULES.md compliance check, surfaces the verification table. Optionally updates setup files (offers, pipelines) if they changed during the session.

### Operations

#### `ghl-tagging`
**Triggers:** "tag this contact", "what tags should I use", "find contacts tagged X"

Canonical tag taxonomy: Source / Status / Interest / Goal / Client / Action — explained in plain English with rules and MCP execution patterns. Built-in bulk operation safeguards.

#### `ghl-pipelines`
**Triggers:** "move Sarah to Call Booked", "where are my hot leads"

Manages Sales DM + Client pipelines. Coordinates stage moves with tag updates so contacts never end up in inconsistent state. Adapts to non-canonical pipeline names.

#### `ghl-automations`
**Triggers:** "build me an automation", "automate my onboarding"

Trigger → action framework taught in plain English. Maps automations BEFORE opening GHL's workflow builder. Test-with-one-contact discipline. Priority order for which automations to build first.

---

## Agents

### `ghl-coach-assistant` (Claude Code only)
**Triggers:** "process this lead end-to-end", "handle Sarah from DM to enrolled", "process all my new leads"

Multi-step GHL operator. Takes complex requests spanning tagging + pipeline moves + opportunity creation + notification, executes them in its own context window, returns a concise summary. Built-in bulk operation safeguards. Defers strategy and automation-builder requests back to the parent.

### `ghl-notifier`
**Triggers:** during `ghl-session-pickup` (always), or manually: "what should I focus on?", "anything urgent?"

Scans the workspace state files, scores items by urgency, returns a top-3 brief to the parent session, AND optionally creates GHL internal tasks via MCP for items urgent for >24h. Coach sees urgent items both in-conversation AND in their normal GHL task inbox.

---

## The 13-file workspace

`ghl-workspace-setup` creates this structure at `~/REVXL-GHL-Workspaces/{coach-business-slug}/`:

### Setup (rarely change)
| File | Purpose |
|------|---------|
| `RULES.md` | Override constraints (agent-optimizer + GHL guardrails) |
| `CLAUDE.md` | Session instructions, tone rules, file map |
| `coach-profile.md` | Identity, niche, ICA, voice, GHL location ID, hard guardrails |
| `offers.md` | Programs, prices, ideal client per offer |
| `pipelines.md` | Actual pipeline structure (pulled from GHL) |

### State trackers (updated every session)
| File | Purpose |
|------|---------|
| `follow-up.md` | Hot leads queue (Urgent / High priority / Watch buckets) |
| `client-roster.md` | Active paying clients by stage with days-since-touch |
| `attention-needed.md` | Stuck leads, broken automations, tag drift, manual flags |

### Inventory & strategy
| File | Purpose |
|------|---------|
| `automation-inventory.md` | Every workflow built, trigger, actions, status |
| `wins.md` | Celebration log (motivation + content source) |
| `kpis.md` | Manual quarterly snapshot of metrics |

### Lifecycle
| File | Purpose |
|------|---------|
| `Checkpoint.md` | Append-only session log |
| `handoff.md` | Next-session priorities (rewritten each session) |

---

## Quick install

### Claude Desktop (recommended for coaches)

1. Customize → Skills → **+** next to "Personal plugins"
2. Paste: `joeoliveimpact/revxl-marketplace`
3. Click Sync → click **Install** on `ghl-coach-superengine`

Then in your first conversation:
1. Say _"install the GoHighLevel MCP"_ → `ghl-mcp-installer` walks you through it
2. Say _"set up my GHL workspace"_ → `ghl-workspace-setup` builds the 13 files
3. From every future session forward: just say _"let's get started"_ — the workspace remembers everything

### Claude Code

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install ghl-coach-superengine@revxl-marketplace
```

Full step-by-step in the [marketplace INSTALL guide](../../README.md#install).

---

## Required external installs

This plugin **guides + executes** GHL work but depends on two MCP servers:

1. **GoHighLevel MCP** — [mastanley13/GoHighLevel-MCP](https://github.com/mastanley13/GoHighLevel-MCP). The `ghl-mcp-installer` skill walks you through this.
2. **Filesystem MCP** — required to write workspace files. Install from Claude Desktop's Customize → Connectors. Without it, the workspace files can't be written.

After installing both, run `ghl-workspace-setup`.

---

## Tone & non-tech-savvy users

This plugin is opinionated about audience. Every skill enforces:
- Plain English (no CRM jargon without explainer)
- One action at a time
- Narrate before executing destructive actions
- Confirm bulk operations (5+ contacts)
- Reassure constantly
- Celebrate small wins

If you're building for a different audience, copy this plugin and adjust the tone rules.

---

## Adapting per-coach

Out of the box, the skills assume health/wellness/fitness coaching. For each new coach client, `ghl-workspace-setup` captures niche, voice, offers, pipelines automatically. Most adaptation happens at workspace creation, not in skill code.

---

## Compatibility

| Platform | Skills | Agents | Workspace files |
|----------|--------|--------|-----------------|
| Claude Desktop | ✅ all 8 | only inline (not subagent) | ✅ via Filesystem MCP |
| Claude Code | ✅ all 8 | ✅ both as subagents | ✅ |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
