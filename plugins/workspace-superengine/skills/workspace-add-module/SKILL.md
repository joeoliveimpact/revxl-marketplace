---
name: workspace-add-module
description: Layer an opt-in module into an existing workspace-superengine workspace. Use when the user says "this workspace needs X support", "add a code module", "add the client-work module", "extend this workspace", "let's add content support", "I'm starting to do client work in here", "set up specs tracking", "make this a coding workspace", "add support for clients", "extend the scaffold", "add a module". Reads the requested module's module.json, writes the declared files, and records the install in .claude/workspace.yml. Refuses to overwrite existing files without confirmation per the Surgical Execution rule.
---

# workspace-add-module

Adds one opt-in module from the plugin's `modules/` library to the current workspace.

## When to use

Trigger phrases (auto-activation):

- "add the code module" / "add code support" / "this needs specs tracking"
- "add the client-work module" / "I'm starting client work in here"
- "add the content module" / "set up content folders"
- "extend this workspace" / "what modules are available"
- Anything that names a module by id (`code`, `client-work`, `content`)

Do NOT use for:

- Initial workspace scaffolding (that's `/super-setup`)
- Custom hooks or agents (those are `/workspace-add-hook`, `/workspace-add-agent`)
- Domain rules unrelated to the three shipped modules

## Step 0 — Preconditions

1. Confirm the workspace is scaffolded. Look for `RULES.md` and `CLAUDE.md` at workspace root. If either is missing, stop and recommend `/super-setup`.
2. Read `.claude/workspace.yml`. If absent, stop with the same recommendation.

## Step 1 — Discover available modules

List the contents of the plugin's `modules/` directory (resolve relative to this SKILL.md's location: `../super-setup/modules/`). For each subdirectory, read its `module.json` and capture `name`, `version`, `description`.

Also read `.claude/workspace.yml#modules` so you can mark already-installed modules.

## Step 2 — Pick the module

If the user named a module in the prompt, validate it exists. If not, present a numbered list:

```
Available modules:
  1. code (1.0.0) — Adds spec tracking folders and a code-quality rule.
  2. client-work (1.0.0) — Adds clients/ template and confidentiality rule. [already installed]
  3. content (1.0.0) — Adds content drafts/published folders and content rule.

Which one? (number or name, or 'cancel')
```

If the user picks one already installed, ask: "It's already installed at version X. Reinstall? (y/N)". Default no.

## Step 3 — Check requirements

Read the chosen module's `module.json`. If `requires.scaffold` is set, compare against `.claude-plugin/plugin.json#version`. If the scaffold is too old, stop and explain.

## Step 4 — Plan the writes

For each entry in `creates[]`, decide what will happen:

- **directory:** if it exists, skip silently. If not, create. Drop a `.gitkeep` only when `gitkeep: true`.
- **file:** read the source from `modules/<name>/<source>`. Check destination:
  - If destination does not exist → write.
  - If destination exists and `overwrite == "skip"` → skip with a note.
  - If destination exists and `overwrite == "replace"` → write, but still surface the overwrite in the summary.
  - If destination exists and `overwrite == "ask"` (default) → prompt the user per-file: "overwrite / skip / diff".

Present the plan to the user before executing:

```
Will install module 'code':
  + create dir .claude/specs/in-progress/ (with .gitkeep)
  + create dir .claude/specs/completed/ (with .gitkeep)
  + write file .claude/rules/code-quality.md (new)

Proceed? (Y/n)
```

## Step 5 — Execute

Run the writes in order. For each one, report:

```
  ✓ created .claude/specs/in-progress/
  ✓ created .claude/specs/completed/
  ✓ wrote .claude/rules/code-quality.md
```

If any write fails, stop and surface the error. Do not roll back partial writes — leave them and ask the user how to proceed.

## Step 6 — Register

Append the install to `.claude/workspace.yml`:

```yaml
modules:
  - name: code
    version: 1.0.0
    installedAt: <ISO-8601 now>
```

If the `modules:` block does not exist, create it. If the module was already in the list (reinstall), update its `version` and `installedAt`.

## Step 7 — Report

Print the `postInstallMessage` from `module.json`, followed by a one-line summary of what to do next:

```
Code module installed. Drop draft specs in .claude/specs/in-progress/ ...

Next: run /workspace-cleanup occasionally to archive stale specs.
```

## Ground rules

- **Intent Clarification:** if the user said "add a module" without naming one, ask. Don't guess.
- **Least Complexity:** one module at a time. If the user asks for multiple, do them sequentially with one confirmation each.
- **Surgical Execution:** never overwrite without explicit per-file confirmation. The default for `overwrite: ask` is to ask, every time.
- **Declarative Focus:** Definition of Done is "the files in `creates[]` exist on disk and `.claude/workspace.yml` records the install". If the user asks for "and also configure X", spin that out to `/workspace-add-hook` or `/workspace-add-agent`.

## Environment notes

This skill uses Read, Write, and Glob tools exclusively. It does not call Bash. Works in both Code and Cowork environments without branching.
