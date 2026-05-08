# Install Troubleshooting

Common issues installing revxl-marketplace plugins.

## "Customize panel doesn't have a Skills section" (Claude Desktop)

You're on an older version of Claude Desktop. Update via the menu bar (Mac) or settings (Windows). The Skills panel was added in late 2025/early 2026.

## "GitHub path won't add" (Claude Desktop)

Confirm:
1. Format is `username/repo` only — no `https://github.com/` prefix
2. The repo is **public** (private repos require additional auth setup)
3. The repo has `.claude-plugin/marketplace.json` at its root (revxl-marketplace does)

## "Skills don't appear after Sync" (Claude Desktop)

1. Restart Claude Desktop fully (quit, not just close).
2. Customize → Skills — check that the marketplace appears under "Personal plugins"
3. Click into the marketplace — you should see install cards for each plugin
4. Click Install on each one you want

## "/plugin command not found" (Claude Code Desktop on Windows)

Known bug — [Issue #42142](https://github.com/anthropics/claude-code/issues/42142). Workarounds:

### Option A: use Claude Code CLI in terminal

```bash
claude
```

Then run `/plugin install ...` in the CLI prompt. Both share `~/.claude/` config.

### Option B: edit settings.json manually

Open `~/.claude/settings.json` and add:

```json
{
  "enabledPlugins": {
    "claude-workspace-superengine@revxl-marketplace": true,
    "ghl-coach-superengine@revxl-marketplace": true
  },
  "extraKnownMarketplaces": {
    "revxl-marketplace": {
      "source": {
        "source": "github",
        "repo": "joeoliveimpact/revxl-marketplace"
      }
    }
  }
}
```

Restart Claude Code Desktop.

## "Skills load but don't trigger on my phrases"

Try the exact phrases listed in each plugin's README (or its SKILL.md description). The trigger matcher uses semantic similarity — phrases that are close to the description's trigger list will fire, but very abstract requests may not match.

## "GHL skills don't actually do anything"

The `ghl-coach-superengine` plugin **guides** GHL operations and provides skill descriptions, but it doesn't include the GoHighLevel MCP itself. You also need:

1. The [GoHighLevel-MCP](https://github.com/mastanley13/GoHighLevel-MCP) installed and configured in `claude_desktop_config.json`
2. A valid Private Integrations API key from GHL

After installing the plugin, run the `ghl-mcp-installer` skill: just say _"install the GoHighLevel MCP"_ — Claude will walk you through it step-by-step.

## "Auto-update isn't working"

Auto-update fires when the `metadata.version` in marketplace.json or a plugin's `version` field changes. If you've added a plugin via GitHub path and don't see updates:

1. Force-refresh by removing and re-adding the marketplace in Customize → Skills
2. Check the marketplace's GitHub commit log — confirm new commits exist
3. Restart Claude Desktop fully

## "Validation errors when running claude plugin validate"

```bash
claude plugin validate .
claude plugin validate plugins/{plugin-name}
```

Common errors:
- **marketplace.json: missing source** — every plugin entry needs `"source"` set
- **plugin.json: missing required field** — `name` and `description` are required
- **SKILL.md: invalid frontmatter** — YAML must be valid; `name` and `description` are required
- **agent.md: invalid frontmatter** — same as SKILL.md plus model, color, tools fields

## "I want to uninstall a plugin"

### Claude Desktop
Customize → Skills → click the trash icon next to the plugin

### Claude Code
```
/plugin uninstall {plugin-name}@revxl-marketplace
```

Or remove the entry from `~/.claude/settings.json` `enabledPlugins`.

## Still stuck?

[Open an issue](https://github.com/joeoliveimpact/revxl-marketplace/issues) with:
- Which Claude product (Desktop / Code / CLI)
- OS (Mac / Windows / Linux)
- Exact error message or behavior
- Steps you've already tried
