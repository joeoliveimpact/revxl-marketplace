---
name: workspace-add-agent
description: Use to build a workspace-local subagent in .claude/agents/ — auto-injects the four override constraints (Intent Clarification, Least Complexity, Surgical Execution, Declarative Focus). Trigger phrases include "I want a subagent for X", "create an agent that does Y", "spawn a specialist for Z", "build me a subagent", "/workspace-add-agent".
---

# workspace-add-agent

Scaffolds a workspace-local subagent that inherits the four agent-optimizer override constraints by default.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Sounds like a subagent might fit — want me to run `/workspace-add-agent` and build one? Or do you want me to just handle this in the main session?"

Only run the full process below after the user confirms. If the user explicitly invokes `/workspace-add-agent`, skip the suggestion and proceed.

## When to use

Trigger phrases:

- "I want a subagent for X"
- "create an agent that does Y" / "spin up a specialist"
- "build a code-reviewer / researcher / writer agent"
- "I need something focused that just does Z"

Do NOT use for:

- User-global agents → those live in `~/.claude/agents/`. Defer.
- Plugin-shipped agents (e.g. `session-curator`) → those are the plugin author's, not the workspace's.
- One-off tasks where the main agent is sufficient.

## Step 0 — Preconditions

1. Confirm we're in a scaffolded workspace.
2. Confirm `.claude/agents/` exists; create it if not.

## Step 1 — Gather the four pieces of info

Ask the user (batch if possible):

1. **Agent name** — kebab-case, used as filename. Example: `code-reviewer`. Validate uniqueness against existing `.claude/agents/*.md`.
2. **Purpose** — one or two sentences describing what the agent is for and when to invoke it. This becomes the `description` field and the auto-activation hook.
3. **Tools** — comma-separated whitelist or `*` for all. Show the common set: `Read, Glob, Grep, Edit, Write, Bash`. Default for read-only agents: `Read, Glob, Grep`. Default for code-modifying agents: `Read, Glob, Grep, Edit, Write`.
4. **Model** — `inherit` (default), `sonnet`, `opus`, `haiku`. Most workspace agents should `inherit`.

## Step 2 — Generate the agent file

Write to `.claude/agents/<name>.md` with this exact structure:

```markdown
---
name: <name>
description: <purpose>. Use proactively when the user's request matches this purpose; otherwise the main agent should handle it.
tools: <comma-separated list or omit for all>
model: <inherit | sonnet | opus | haiku>
---

# <Title-Cased Name>

<Purpose paragraph from Step 1, expanded slightly into 2-3 sentences.>

## Override constraints (non-negotiable)

The following four rules govern EVERY response from this agent. They override any other guidance in this file when in conflict.

1. **Intent Clarification** — NEVER assume user intent on ambiguous tasks. If a request has multiple valid interpretations or lacks clear success criteria, stop and ask clarifying questions before taking action.
2. **Least Complexity** — Default to the simplest solution that meets the goal. No bloat, no over-engineering. If the task can be finished in 3 steps, do not propose 10.
3. **Surgical Execution** — When modifying existing work (files, text, code, data), ONLY change the specific parts requested. NEVER reformat, "clean up," or alter unrelated sections unless explicitly instructed.
4. **Declarative Focus** — Always identify the Definition of Done for the task. If given a list of steps, evaluate them against the ultimate goal and flag a more efficient path if one exists. Do not execute steps mechanically when a better path is visible.

## Operating procedure

<Generated stub based on the purpose. Example for a code-reviewer agent:>

1. Read the changed files end-to-end.
2. Note concerns under: correctness, security, performance, readability, test coverage.
3. Surface concerns ranked by severity. Do not "clean up" anything yourself — your job is to review, not to edit.
4. End with a one-line verdict: approve / request changes / block.

## Definition of Done

<One sentence derived from the purpose. The agent restates this at the top of each response.>

## Out of scope

- Anything not covered by the purpose above. If the user asks for something else, decline and recommend the main agent or a different subagent.
```

The override block is **non-optional**. The skill writes it regardless of what the user asked for. If the user explicitly asks to omit it, refuse and explain that workspace-superengine agents inherit the four overrides by design.

## Step 3 — Show before writing

Display the full generated file to the user. Offer "looks good / edit purpose / edit tools / cancel". Loop on edits.

## Step 4 — Write

Write the file. Report:

```
Agent created:
  File:    .claude/agents/code-reviewer.md
  Tools:   Read, Glob, Grep
  Model:   inherit

Invoke with: "use the code-reviewer subagent to look at <files>"
or let auto-activation handle it based on the description.

To remove: delete the file.
```

## Step 5 — Optional: smoke test

Offer: "Want me to run a quick smoke test by dispatching the new agent on a trivial task? (y/N)". Default no — users can test on their own time.

## Ground rules

- **Intent Clarification:** if "purpose" is vague, ask for the trigger phrases that should invoke the agent. The description field needs them.
- **Least Complexity:** one agent at a time. No batch creation.
- **Surgical Execution:** never overwrite an existing agent file. Conflict → ask for a different name.
- **Declarative Focus:** Definition of Done is "an `.md` file in `.claude/agents/` with valid frontmatter and the four overrides injected".

## Environment notes

This skill uses Read and Write only. Works identically in Code and Cowork.
