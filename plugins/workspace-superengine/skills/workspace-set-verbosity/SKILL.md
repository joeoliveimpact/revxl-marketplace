---
name: workspace-set-verbosity
description: Flip workspace verbosity between beginner and standard mode. Use when the user says "switch to beginner mode", "turn on verbose mode", "stop explaining everything", "I'm new to this", "I'm experienced, less hand-holding", or any request to change how chatty plugin skills are. Reads/writes .claude/workspace.yml#verbosity. Single-question skill — confirms the new value with the user and writes.
---

# workspace-set-verbosity

One job: flip the `verbosity` field in `.claude/workspace.yml` between `beginner` and `standard`. Confirm the change with the user. Done.

## When this fires

Triggers like:
- "switch to beginner mode"
- "stop explaining everything"
- "turn verbose on"
- "I'm new to Claude — make this friendlier"
- "I know what I'm doing — less preamble please"

## Procedure

### Step 1 — Read current value

Use the Read tool on `.claude/workspace.yml`. Parse for the `verbosity:` line.

If the file doesn't exist → "This workspace hasn't been scaffolded yet. Run `/super-setup` first."

If the field is missing from the file → treat as `standard` (the implicit default).

### Step 2 — Confirm the flip

Tell the user the current value and propose the flip:

```
Current verbosity: standard
Flip to: beginner

Beginner mode adds a 2-3 sentence preamble before each workspace skill runs, written at a 7th-grade reading level.

Proceed? [Y/n]
```

If the user picks `n`, stop. Don't write.

### Step 3 — Write the change

Use the Edit tool with `old_string` = the current `verbosity:` line and `new_string` = the new value.

If the line was absent, use the Edit tool with `old_string` = the file's top YAML block opener and `new_string` = opener + `verbosity: <value>` on a new line.

### Step 4 — Confirm to user

One line:

```
Verbosity set to **beginner**. New setting applies starting on the next skill invocation.
```

Done. End your turn.

## Out of scope

- Changing any other workspace.yml field (environment, etc.)
- Adding new verbosity levels beyond beginner/standard
- Editing skill files themselves

## Beginner-mode preamble for this skill

(See `docs/beginner-voice.md`. If current verbosity is beginner, emit before Step 1:)

> I'm about to change how chatty the workspace is. Beginner mode adds a short heads-up before each skill so you know what's coming; standard mode is quiet and just does the work. I'll read the current setting, ask you to confirm the swap, then save it.
