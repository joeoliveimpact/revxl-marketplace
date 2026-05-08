# Creating a New Superengine

How to add a new plugin to revxl-marketplace.

## Before you start

1. **Check the roadmap** in [README.md](../README.md) — make sure your idea isn't already planned.
2. **Open an issue** describing what you want to build. We'll align on scope before you write code.
3. **Read [docs/plugin-conventions.md](plugin-conventions.md)** — naming, frontmatter, tone rules.
4. **Look at [claude-workspace-superengine](../plugins/claude-workspace-superengine/) and [ghl-coach-superengine](../plugins/ghl-coach-superengine/)** as canonical examples.

## Steps

### 1. Scaffold the folder

```bash
cd plugins/
mkdir -p my-plugin-superengine/.claude-plugin
mkdir -p my-plugin-superengine/skills/my-first-skill
mkdir -p my-plugin-superengine/agents
cd my-plugin-superengine
```

### 2. Write `.claude-plugin/plugin.json`

```json
{
  "$schema": "https://anthropic.com/claude-code/plugin.schema.json",
  "name": "my-plugin-superengine",
  "description": "What it does, who it's for, what it requires.",
  "version": "0.1.0",
  "author": {
    "name": "Your Name",
    "email": "you@example.com"
  },
  "homepage": "https://github.com/{owner}/revxl-marketplace/tree/main/plugins/my-plugin-superengine",
  "license": "MIT",
  "keywords": ["..."]
}
```

### 3. Write your first skill

`skills/my-first-skill/SKILL.md`:

```markdown
---
name: my-first-skill
description: Use this skill when {trigger phrases}, {related triggers}. Brief description of what the skill does and who it's for. Be specific — the description is the trigger surface.
---

# My First Skill

(skill body — instructions for Claude when this skill activates)

## Tone rules

(if your audience is non-technical, copy the tone rules from plugin-conventions.md)

## Procedure

(step-by-step what Claude should do)
```

**Trigger surface guidance:** include 5-10 phrases the user might actually say. Verb forms, noun forms, alternate phrasings. Be greedy — false positives are cheap, false negatives are expensive.

### 4. Optional: write an agent

`agents/my-agent.md`:

```markdown
---
name: my-agent
description: |
  Use this agent when {situation}. Examples:

  <example>
  Context: {situation}
  user: "{user message}"
  assistant: "I'll use the my-agent agent to {what it does}."
  <commentary>
  {why the agent triggers}
  </commentary>
  </example>

  (add 2-3 more examples)
model: sonnet
color: cyan
tools: ["Read", "Write", "Edit"]
---

You are an expert {role}. (system prompt)
```

Reference: see [claude-workspace-superengine/agents/session-curator.md](../plugins/claude-workspace-superengine/agents/session-curator.md) for a full example.

### 5. Write per-plugin README, CHANGELOG, LICENSE

Copy from an existing plugin and adapt. Required sections in README per [plugin-conventions.md](plugin-conventions.md):
- Tagline
- What it does
- Per-skill section
- Per-agent section
- Install
- Dependencies
- Compatibility table
- Changelog reference
- License
- Marketplace backlink

### 6. Add to marketplace.json

Edit `.claude-plugin/marketplace.json` and add your plugin to the `plugins` array:

```json
{
  "name": "my-plugin-superengine",
  "description": "Marketplace-card description (the install pitch).",
  "source": "my-plugin-superengine",
  "category": "productivity",
  "version": "0.1.0",
  "author": {"name": "Your Name", "email": "you@example.com"},
  "homepage": "https://github.com/{owner}/revxl-marketplace/tree/main/plugins/my-plugin-superengine",
  "keywords": ["..."]
}
```

### 7. Validate

```bash
claude plugin validate plugins/my-plugin-superengine
claude plugin validate .
```

Fix any errors. CI runs the same checks on push.

### 8. Test locally

```bash
# Add your fork as a marketplace
claude plugin marketplace add {your-fork}/revxl-marketplace

# Install your new plugin
claude plugin install my-plugin-superengine@revxl-marketplace
```

Restart Claude Code. Trigger your skills with the phrases from your description. Verify they load and behave correctly.

### 9. Update CHANGELOGs

- Plugin's own CHANGELOG.md: add v0.1.0 entry
- Marketplace's CHANGELOG.md: note the new plugin

### 10. Open a PR

Follow the [CONTRIBUTING.md](../CONTRIBUTING.md) checklist.

## Common mistakes to avoid

1. **Vague skill descriptions** — won't trigger reliably. Be greedy with trigger phrases.
2. **Forgetting to bump versions** — auto-update breaks for clients.
3. **Mixing two domains in one plugin** — split into two superengines instead.
4. **Hardcoding paths** — use relative paths or `${CLAUDE_PLUGIN_ROOT}` (Claude Code).
5. **Skipping the README sections** — clients use READMEs to decide whether to install. Bad README = no installs.
6. **Missing CHANGELOG entry** — auto-update may not fire.
7. **Out-of-tone for the audience** — if it's for non-tech coaches, no jargon. Period.

## Reference plugins to copy from

- **Workspace lifecycle pattern:** [claude-workspace-superengine](../plugins/claude-workspace-superengine/)
- **Multi-skill domain plugin:** [ghl-coach-superengine](../plugins/ghl-coach-superengine/)
- **Anthropic canonical:** [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — see plugin-dev, skill-creator, mcp-server-dev
