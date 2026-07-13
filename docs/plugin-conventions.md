# Plugin Conventions

Every superengine in revxl-marketplace follows these conventions. They keep tone consistent, install reliable, and cross-plugin coordination clean.

## Naming

### Plugin name
- Lowercase, kebab-case, ends in `-superengine`
- Domain prefix first: `claude-workspace-superengine`, `ghl-coach-superengine`, `meta-mcp-superengine`
- The `-superengine` suffix signals it's a multi-skill plugin (vs. a standalone skill)

### Skill names inside a plugin
- Lowercase, kebab-case, descriptive
- Domain-prefixed when ambiguous: `ghl-tagging` not `tagging`
- Avoid generic names like `helper`, `tool`, `assistant`

### Agent names
- Lowercase, kebab-case
- 2-4 words: `session-curator`, `ghl-coach-assistant`, `plugin-validator`

## Frontmatter standards

### SKILL.md frontmatter
```yaml
---
name: skill-name
description: Use this skill when {trigger phrases}, {related triggers}, or {natural language phrases the user would say}. Brief description of what the skill does and who it's for.
---
```

**The description is the trigger surface.** If a user says one of these phrases or anything semantically close, the skill loads. Be specific. Include 5-10 trigger phrases. Specify the audience.

Bad: "Manages tags."
Good: "Use this skill when a coaching client asks about GoHighLevel tags — 'tag this contact', 'what tags should I use', 'organize my contacts', 'add tag', 'remove tag', 'find contacts tagged X'..."

### agent.md frontmatter
```yaml
---
name: agent-name
description: |
  Use this agent when {situation}. Triggers on: {phrases}. Examples:

  <example>
  Context: {situation}
  user: "{user message}"
  assistant: "I'll use the {agent-name} agent to {what it does}."
  <commentary>
  {why the agent triggers}
  </commentary>
  </example>

  (2-4 examples)
model: sonnet  # or inherit
color: cyan    # blue/cyan for analysis, green for generation, yellow for validation, red for security, magenta for transformation
tools: ["Read", "Write", "Edit", "Bash"]  # optional, defaults to all
---
```

### plugin.json schema
```json
{
  "$schema": "https://anthropic.com/claude-code/plugin.schema.json",
  "name": "plugin-name",
  "description": "What it does, who it's for, what it requires.",
  "version": "0.1.0",
  "author": {"name": "...", "email": "..."},
  "homepage": "...",
  "license": "MIT",
  "keywords": ["..."]
}
```

### marketplace.json plugin entry
```json
{
  "name": "plugin-name",
  "description": "Marketplace-card description (different from plugin.json — this is the install pitch).",
  "source": "plugin-name",
  "category": "productivity|crm|development|...",
  "version": "0.1.0",
  "author": {"name": "...", "email": "..."},
  "homepage": "...",
  "keywords": ["..."]
}
```

## Tone rules

The default tone for revxl-marketplace plugins is **non-technical, plain English, one-step-at-a-time, reassuring**. This matches the audience for most REVXL coaching clients.

If your plugin is for a different audience (technical operators, developers), explicitly state the tone shift in the plugin's README.

### Always:
- Plain English. No jargon without explainer.
- One action at a time. Never give >3 action items in a single response.
- Narrate before destructive actions: "I'm about to {action}. Ready?"
- Confirm after every action: "Done ✓ {what changed}."
- Reassure: "Totally fixable", "this is normal", "we can pause anytime."
- Celebrate small wins.

### Never:
- Dump a wall of instructions
- Use jargon like "webhook", "API call", "payload", "trigger node" without translating
- Execute bulk operations (5+ items) without explicit confirmation
- Assume context from a previous session — always recap

## Bulk operation safety

Any skill or agent that can affect 5+ records (contacts, files, etc.) MUST:
1. List affected items first
2. Pause for explicit confirmation
3. Execute one at a time, narrating progress
4. Final report with counts and exceptions

## Plugin self-containment

Each plugin folder must contain:
- `.claude-plugin/plugin.json` — manifest
- `skills/{name}/SKILL.md` — at least one skill (or one agent)
- `README.md` — describes the plugin, its skills, install, dependencies, audience
- `CHANGELOG.md` — versioned change history
- `LICENSE` — MIT (or document why otherwise)

Optional but recommended:
- `agents/{name}.md` — agents (Claude Code only)
- `commands/{name}.md` — slash commands (Claude Code only)
- `hooks/hooks.json` — lifecycle hooks
- `.mcp.json` — MCP server config

## Cross-plugin coordination

Plugins can reference each other's skills via natural language. If `ghl-coach-superengine`'s `ghl-session-startup` should invoke `claude-workspace-superengine`'s `session-pickup`, just say so in the body:

> "If the workspace has a `handoff.md`, run the `session-pickup` skill from `claude-workspace-superengine` first to recap workspace context before starting the GHL session."

Don't try to make plugins technically depend on each other — keep dependencies soft and natural-language-driven.

## Versioning

[Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** (1.0.0): breaking changes to skill triggers, manifest schema, or removed components
- **MINOR** (0.1.0): new skills, new agents, new triggers (additive)
- **PATCH** (0.0.1): bug fixes, doc updates, frontmatter tightening

Bump version in BOTH:
- `plugins/{name}/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json` (the entry for that plugin)

Otherwise auto-update on clients won't trigger.

On every version bump, also update the `vX.Y.Z · ` prefix in the plugin's `marketplace.json` description to match its `version` field (the picker doesn't display the version field, so the semver is embedded in the description text — it lives in 2 places and must stay in sync).

## Documentation requirements

Every plugin's README must include:
- Plugin name + 1-line tagline
- Demo placeholder (or real demo)
- "What this plugin does" — 1-2 paragraphs
- Per-skill section: trigger phrases + description
- Per-agent section: trigger phrases + when to use
- Install instructions (Claude Desktop AND Claude Code)
- Dependencies (other plugins, MCP servers, external accounts)
- Compatibility table (Claude Desktop / Claude Code, Skills / Agents)
- Changelog reference
- License
- Backlink to marketplace
