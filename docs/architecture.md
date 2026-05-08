# Architecture — revxl-marketplace

How this marketplace is organized and why.

## The three-tier model

Anthropic's plugin system has three tiers. Understanding them prevents most architectural mistakes:

```
[Marketplace Catalog]   ←  this repo's .claude-plugin/marketplace.json
        ↓ indexes
[Plugin Sources]        ←  each plugin's folder under plugins/
        ↓ contains
[Components]            ←  skills/, agents/, commands/, hooks/, .mcp.json
```

**The marketplace doesn't host plugins — it indexes them.** Each plugin is independent and self-contained. The marketplace.json points to where each one lives.

For revxl-marketplace, all plugins currently live in this same repo under `./plugins/{name}/`. But we could just as easily reference plugins from external repos via `"source": {"source": "github", "repo": "owner/external-plugin"}` if a plugin grows enough to warrant its own home.

## Repository layout

```
revxl-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # catalog — lists every plugin
├── .github/
│   └── workflows/
│       └── validate-plugins.yml  # CI: schema validation on every push
├── plugins/
│   └── {plugin-name}/            # one self-contained plugin per folder
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── {skill-name}/
│       │       └── SKILL.md
│       ├── agents/
│       │   └── {agent-name}.md
│       ├── README.md
│       ├── CHANGELOG.md
│       └── LICENSE
├── docs/                         # marketplace-level documentation
├── README.md                     # marketplace landing page
├── CHANGELOG.md                  # marketplace-level releases
├── CONTRIBUTING.md
├── CODEOWNERS
└── LICENSE
```

### Why each plugin has its own README/CHANGELOG/LICENSE

Three reasons:

1. **Per-plugin install.** When clients sync the marketplace in Claude Desktop, they see each plugin as a separate install card. Each card needs its own description and pitch — that comes from the plugin's README.

2. **Versioning autonomy.** A plugin may release v0.4.0 while another stays at v0.1.0. Each CHANGELOG documents its own history.

3. **Future extraction.** If a plugin outgrows the marketplace and needs its own repo, its self-contained folder can be moved out wholesale without rewriting docs.

## How marketplace.json resolves plugins

The `metadata.pluginRoot: "./plugins"` shortcut means each plugin's `source` field can be just the folder name:

```json
{
  "name": "claude-workspace-superengine",
  "source": "claude-workspace-superengine"   // resolves to ./plugins/claude-workspace-superengine
}
```

For external plugins (from another repo), use the full source object:

```json
{
  "name": "external-plugin",
  "source": {
    "source": "github",
    "repo": "owner/external-plugin",
    "ref": "v1.0.0"
  }
}
```

## Install paths

| Client | Install method | What gets installed |
|--------|---------------|---------------------|
| Claude Desktop | Customize → Skills → paste GitHub path → Sync | User picks each plugin individually |
| Claude Code | `/plugin install {name}@revxl-marketplace` | Just that plugin |
| Manual JSON | Add to `~/.claude/settings.json` `enabledPlugins` | Plugin enables on next launch |

## Auto-update model

Once a marketplace is registered with a client's Claude:
- Claude periodically refreshes the marketplace.json from GitHub
- New plugin entries appear in the install picker
- Existing plugins update when their version field changes
- Removed plugins persist locally until manually uninstalled

To force-update: bump the `metadata.version` in marketplace.json.

## Validation

CI runs `claude plugin validate` on every push (see [.github/workflows/validate-plugins.yml](../.github/workflows/validate-plugins.yml)). This catches:
- marketplace.json schema errors
- Per-plugin plugin.json schema errors
- SKILL.md frontmatter errors
- agent.md frontmatter errors
- Missing required fields
- Broken cross-references

Run locally before pushing:
```bash
claude plugin validate .
claude plugin validate plugins/claude-workspace-superengine
claude plugin validate plugins/ghl-coach-superengine
```

## Reference docs

- [Claude Code Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Anthropic's official marketplace.json](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json) — canonical reference
- [Claude Code JSON schema](https://github.com/hesreallyhim/claude-code-json-schema) — community-maintained schemas
