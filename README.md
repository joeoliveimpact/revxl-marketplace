# revxl-marketplace

> A curated catalog of Claude superengines from [REVXL](https://engineforimpact.com). Opinionated, multi-skill plugins built for real coaching businesses.

![marketplace banner placeholder](docs/demos/marketplace-banner.png)

[![Validate Plugins](https://github.com/{YOUR-GITHUB-USERNAME}/revxl-marketplace/actions/workflows/validate-plugins.yml/badge.svg)](https://github.com/{YOUR-GITHUB-USERNAME}/revxl-marketplace/actions/workflows/validate-plugins.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What's a "superengine"?

A **superengine** is a multi-skill plugin built around a single domain. One install gives you all the skills, agents, and patterns you need to operate that domain end-to-end. No piecing together loose skills, no figuring out the right combinations.

Each superengine is opinionated about audience, tone, and workflow — so it works out of the box without configuration.

---

## Plugins in this marketplace

### 🛠️ [claude-workspace-superengine](plugins/claude-workspace-superengine/)
Workspace lifecycle for Claude. Scaffolds new workspaces with the canonical 8-file scheme, picks up cleanly at session start, closes out cleanly at session end. Built on the four `agent-optimizer` override constraints.

**Skills:** `super-setup`, `session-pickup`, `session-closeout`
**Agents:** `session-curator`
**Works in:** Claude Desktop, Claude Code

→ [Read the docs](plugins/claude-workspace-superengine/README.md)

---

### 📊 [ghl-coach-superengine](plugins/ghl-coach-superengine/)
A done-with-you GoHighLevel toolkit for health, wellness, and fitness coaches. Walks non-technical clients through MCP install, manages tags + pipelines + automations, ships a multi-step coach-assistant agent.

**Skills:** `ghl-mcp-installer`, `ghl-tagging`, `ghl-pipelines`, `ghl-automations`, `ghl-session-startup`
**Agents:** `ghl-coach-assistant`
**Requires:** [GoHighLevel-MCP](https://github.com/mastanley13/GoHighLevel-MCP)
**Works in:** Claude Desktop, Claude Code

→ [Read the docs](plugins/ghl-coach-superengine/README.md)

---

## Install

Per-plugin install — pick what you want. Skips what you don't.

### Claude Desktop (the chat app)

1. Open Claude Desktop
2. Click **Customize** in the left sidebar
3. Click **Skills** → **+** next to *"Personal plugins"*
4. Paste this GitHub path:
   ```
   {YOUR-GITHUB-USERNAME}/revxl-marketplace
   ```
5. Click **Sync** → you'll see each plugin as a separate install card
6. Click **Install** on the ones you want

✅ Done. Auto-updates whenever this marketplace pushes new versions.

### Claude Code (developer tool)

```
/plugin marketplace add {YOUR-GITHUB-USERNAME}/revxl-marketplace
/plugin install claude-workspace-superengine@revxl-marketplace
/plugin install ghl-coach-superengine@revxl-marketplace
```

Or edit `~/.claude/settings.json` directly — see [docs/install-troubleshooting.md](docs/install-troubleshooting.md).

---

## Repository structure

```
revxl-marketplace/
├── .claude-plugin/
│   └── marketplace.json              ← marketplace catalog (this file lists all plugins)
├── .github/
│   └── workflows/
│       └── validate-plugins.yml      ← CI: validates schema on every push
├── plugins/
│   ├── claude-workspace-superengine/ ← self-contained plugin
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/
│   │   ├── agents/
│   │   ├── README.md, CHANGELOG.md, LICENSE
│   └── ghl-coach-superengine/        ← self-contained plugin
│       ├── .claude-plugin/plugin.json
│       ├── skills/
│       ├── agents/
│       ├── README.md, CHANGELOG.md, LICENSE
├── docs/
│   ├── architecture.md               ← how this marketplace is organized
│   ├── plugin-conventions.md         ← naming, frontmatter, tone rules
│   └── creating-plugins.md           ← contributor guide
├── README.md                         ← this file
├── CHANGELOG.md                      ← marketplace-level releases
├── CONTRIBUTING.md
├── CODEOWNERS
└── LICENSE
```

Each plugin folder is **fully self-contained** — its own manifest, README, CHANGELOG, LICENSE. The marketplace.json INDEXES them; it doesn't host them.

---

## Roadmap

| Plugin | Status | Notes |
|--------|--------|-------|
| `claude-workspace-superengine` | ✅ v0.1.0 | Initial release |
| `ghl-coach-superengine` | ✅ v0.1.0 | Initial release |
| `meta-mcp-superengine` | 🔜 planned | Meta Graph API installer + skills for Instagram/Facebook DMs |
| `umnico-superengine` | 🔜 planned | Umnico MCP installer + DM management for coaches |
| `manychat-superengine` | 🔜 planned | ManyChat installer + flow patterns |
| `plugin-builder-superengine` | 🔜 planned | Meta-plugin: scaffold new superengines |

---

## Auto-updates

When you install via Claude Desktop's GitHub path, your plugins auto-refresh from this repo on each app launch. No action needed on your end.

When new plugins ship, they appear in the Customize panel automatically — pick the ones you want, skip the rest.

---

## For developers

- [docs/architecture.md](docs/architecture.md) — how the marketplace is structured and why
- [docs/plugin-conventions.md](docs/plugin-conventions.md) — naming, frontmatter, tone rules every superengine follows
- [docs/creating-plugins.md](docs/creating-plugins.md) — contributor guide for adding a new superengine
- [CONTRIBUTING.md](CONTRIBUTING.md) — PR process, coding standards, testing
- [.github/workflows/validate-plugins.yml](.github/workflows/validate-plugins.yml) — CI validation runs on every push

---

## License

MIT — see [LICENSE](LICENSE). Each plugin in this marketplace is also MIT-licensed individually.

## Author

[Joe Olive](mailto:joe@engineforimpact.com) — [REVXL](https://engineforimpact.com)

## Issues / Requests

[Open a GitHub issue](https://github.com/{YOUR-GITHUB-USERNAME}/revxl-marketplace/issues) — bug reports, feature requests, "this should also do X" all welcome.
