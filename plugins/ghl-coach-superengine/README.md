# ghl-coach-superengine

> A done-with-you GoHighLevel toolkit for health, wellness, and fitness coaches. Built for non-technical users.

![demo placeholder](../../docs/demos/ghl-coach-superengine.gif)

---

## What this plugin does

Most coaches dump money into GoHighLevel, then can't make it work — they don't know how to organize contacts, when to move pipeline stages, or which automations matter. This plugin closes that gap. Five skills + one operator agent that work together to keep your GHL clean while you focus on coaching.

The skills **guide** clients through actions they can do themselves AND **execute** actions directly via the GoHighLevel MCP — depending on what they want. Always plain English. Always one step at a time. Always reassuring.

---

## Skills

### `ghl-mcp-installer`
**Triggers:** "install GoHighLevel MCP", "connect my GHL to Claude", "set up GHL"

Walks non-technical coaches through installing the [GoHighLevel-MCP (mastanley13)](https://github.com/mastanley13/GoHighLevel-MCP) into Claude Desktop step-by-step. Covers Node install, getting Private Integrations API key + Location ID from GHL, building the MCP server, wiring `claude_desktop_config.json`, and verifying the connection. Designed for users with zero terminal experience.

### `ghl-tagging`
**Triggers:** "tag this contact", "what tags should I use", "organize my contacts", "find contacts tagged X"

The canonical tag taxonomy: Source / Status / Interest / Goal / Client / Action — explained in plain English, with rules for when each set applies and execution patterns via the GHL MCP. Built-in bulk operation safeguards (5+ contacts requires explicit confirmation).

### `ghl-pipelines`
**Triggers:** "move Sarah to Call Booked", "where are my hot leads", "create an opportunity"

Manages the two canonical pipelines (Sales DM + Client). Handles stage moves WITH coordinated tag updates so contacts never end up in inconsistent state. Adapts to non-canonical pipeline names by reading the actual structure from GHL on session start.

### `ghl-automations`
**Triggers:** "build me an automation", "automate my onboarding", "set up follow-up"

Trigger → action framework taught in plain English. Maps the conversation in pseudo-code BEFORE opening GHL's workflow builder. Test-with-one-contact discipline. Priority order for which automations to build first (welcome sequence, call reminders, no-response follow-ups, alumni re-engagement). Native GHL only — no Zapier, no N8N.

### `ghl-session-startup`
**Triggers:** "let's get started", "I'm back", "open up my GHL"

Pre-flight at the start of every coaching session: pulls memory (offers, pipelines, automations), verifies MCP connection silently, recaps last session, asks the goal-of-session question, routes to the right downstream skill.

---

## Agents

### `ghl-coach-assistant` (Claude Code only)
**Triggers:** "process this lead end-to-end", "handle Sarah from DM to enrolled", "process all my new leads", "audit my Decision Pending bucket"

Multi-step GHL operator. Takes complex requests that span tagging + pipeline moves + opportunity creation + notification, executes them in its own context window, returns a concise summary. Token-efficient batch worker.

Hybrid mode: sometimes guide, sometimes operator — always explicit which. Built-in bulk operation safeguards. Defers strategy questions and automation-builder requests back to the parent chat.

---

## Quick install

### Claude Desktop (recommended for most coaches)
1. Customize → Skills → **+** next to "Personal plugins"
2. Paste: `{YOUR-GITHUB-USERNAME}/revxl-marketplace`
3. Click Sync → click **Install** on `ghl-coach-superengine`
4. Then say: _"install the GoHighLevel MCP"_ → the `ghl-mcp-installer` skill walks you through it.

### Claude Code
```
/plugin marketplace add {YOUR-GITHUB-USERNAME}/revxl-marketplace
/plugin install ghl-coach-superengine@revxl-marketplace
```

Full step-by-step in the [marketplace INSTALL guide](../../README.md#install).

---

## Required: the GoHighLevel MCP

This plugin **guides** GHL operations and provides skill descriptions, but it doesn't execute MCP calls itself — it triggers the [GoHighLevel-MCP](https://github.com/mastanley13/GoHighLevel-MCP) which you install separately. The `ghl-mcp-installer` skill makes this painless. Do this AFTER installing the plugin.

You'll need:
- A GoHighLevel account with Settings → Integrations → Private Integrations access
- A Private Integrations API key (the installer skill walks you through getting one)
- Your Location ID (from Settings → Company → Locations)
- Node.js 18+ on your machine
- Comfort opening a terminal (or willingness to follow click-by-click instructions)

---

## Tone & non-tech-savvy users

This plugin is opinionated about audience. Every skill enforces:
- Plain English (no CRM jargon without explainer)
- One action at a time
- Narrate before executing destructive actions
- Confirm bulk operations (5+ contacts)
- Reassure constantly — "this is fixable", "nothing is permanent", "this is normal to feel confused"
- Celebrate small wins

If you're building for a different audience (technical operators), copy this plugin and adjust the tone rules.

---

## Adapting to specific clients

Out of the box, the skills assume health/wellness/fitness coaching with the canonical Sales DM + Client pipelines. To adapt for a specific client:
- [ ] Verify pipeline names + stage names match (or update memory at session start)
- [ ] Save offer names + prices to Claude memory
- [ ] Adjust goal tags to their niche (e.g., remove `goal-hormones` for pure strength coach)
- [ ] Document existing automations so you don't duplicate
- [ ] Note any custom fields they're using

The tagging taxonomy and automation priority order work for almost all health/wellness coaching businesses without modification.

---

## Compatibility

| Platform | Skills | Agent |
|----------|--------|-------|
| Claude Desktop | ✅ | n/a |
| Claude Code | ✅ | ✅ |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
