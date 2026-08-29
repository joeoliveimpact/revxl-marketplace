# How workspace-superengine skills activate

Most of the time you don't have to remember slash commands. The skills in this plugin watch what you're saying and offer themselves when they fit. Here's how the magic works, and exactly which phrases tend to fire each skill.

## Three layers of activation

### Layer 1 — Auto-invoke (silent)

Every skill ships with a rich `description` field. When your prompt matches the description, Claude auto-invokes the skill without asking. This is the default in Claude Code and Claude Desktop. You can always disable a particular skill if it's firing when you don't want it.

### Layer 2 — Suggest before firing

When your prompt only partly matches a skill, Claude asks first instead of running the whole thing:

> "This looks like a brainstorm — want me to run `/workspace-brainstorm`? Or should I just answer directly?"

This protects you from skills firing aggressively and doubles as discoverability — you find out a skill exists in the moment you might have used it.

### Layer 3 — Catalog awareness

The plugin's SessionStart hook (when installed) puts a one-line catalog of available skills into Claude's context at the start of every session. You don't see it, but Claude does. It nudges Claude to consider a skill when one would help.

## Example prompts that fire each skill

### `/workspace-brainstorm` — fuzzy idea → written design

Fires on:
- "I have an idea for a new coaching offer"
- "Let's brainstorm a content series"
- "What should I do about my onboarding sequence"
- "Thinking about launching something new"
- "Help me figure out the offer structure"
- "I want to build a thing but I'm not sure what"

### `/workspace-plan` — design → stepwise plan

Fires on:
- "Let's plan the launch"
- "How should I approach this rebuild"
- "What's the path to ship X"
- "I need a plan for the content production schedule"
- "Turn this design into steps"

### `/workspace-verify` — pre-completion checklist

Fires on:
- "I'm done with the draft"
- "Task complete"
- "Ready to ship"
- "Before I close this out"
- "Is this finished"
- "Looks good to go"

### `/workspace-add-module` — extend the workspace

Fires on:
- "This workspace needs code support"
- "Let's add a content module"
- "I want to start doing client work here"
- "Add a module"

### `/workspace-cleanup` — heavy housekeeping

Fires on:
- "This workspace is messy"
- "Let's tidy up"
- "Too many files"
- "Archive the old stuff"

### `/workspace-add-hook` and `/workspace-add-agent`

Fires on:
- "I want a hook for X"
- "Automate Z at session start"
- "I want a subagent that does Y"
- "Build me an agent"

### `/workspace-set-verbosity`

Fires on:
- "Switch to beginner mode"
- "Stop explaining everything"
- "Turn verbose off"

### `/super-setup`

Fires on:
- "Set up this workspace"
- "Scaffold a new workspace"
- "I just opened an empty folder"
- "Initialize a project here"

### `/session-start`, `/session-closeout` and `/session-continue`

Fires on:
- `/session-start` — "Let's start the session" / "Pick up where we left off" / "Morning" / "What was I working on"
- `/session-closeout` — "Let's wrap up" / "Closing out for the day" / "I'm done for now"
- `/session-continue` — "Close out and queue the next session" / "Wrap up and set up tomorrow" / "See you tomorrow" / "I'm done, get the next one ready"

`/session-continue` runs `/session-closeout` in full first, then builds the next session's opening prompt from what closeout wrote and puts it on a one-click chip. Use closeout alone when no follow-on session is wanted.

### `/agent-optimizer`

Fires on:
- "Reload the four rules"
- "Reset the overrides"
- Any moment Claude is drifting on Intent Clarification, Least Complexity, Surgical Execution, or Declarative Focus

## How to turn it off

If a skill keeps firing when you don't want it:

1. Tell Claude directly: "don't auto-run /workspace-brainstorm in this session"
2. Or invoke `/workspace-set-verbosity` and switch to `standard` (quieter behavior overall)
3. Or disable the skill in your plugin settings

## How to nudge a skill to fire

If you want a skill but Claude isn't picking up on it, just use the slash command — `/workspace-plan`, `/workspace-verify`, etc. Slash commands always work and skip the suggestion gate.
