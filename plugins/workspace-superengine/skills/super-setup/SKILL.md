---
name: super-setup
description: Use to scaffold a brand-new workspace from scratch — creates RULES.md, CLAUDE.md, ARCHITECTURE.md, GOALS.md, PLANNING.md, MEMORY.md, Checkpoint.md, handoff.md, tasks/, troubleshooting/, outputs/, and .claude/workspace.yml. Trigger phrases include "set up this workspace", "scaffold a new workspace", "I just opened an empty folder", "initialize a project here", "make this folder into a workspace", "/super-setup". Detects Cowork vs Code environment, pre-fills owner identity from global config, and offers a beginner-verbosity mode for first-time clients.
---

# super-setup — Workspace Scaffolding (v0.2)

One skill, one pass. Reads the templates that ship inside this plugin and writes a complete scaffold to the target workspace. No model invention.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Looks like this might be a fresh workspace — want me to run `/super-setup` and scaffold the core files? Or are you set up already and just want to talk?"

Only run the full process below after the user confirms. If the user explicitly invokes `/super-setup`, skip the suggestion and proceed.

The templates live at: `${PLUGIN_DIR}/skills/super-setup/templates/`

The substitutions performed on every copy:
- `{{WORKSPACE_NAME}}` → user-supplied workspace name
- `{{PURPOSE}}` → user-supplied primary purpose sentence
- `{{DATE}}` → today's date in `YYYY-MM-DD` format

---

## Step 0 — Detect existing scaffold

List the target workspace root. If ANY of these files exist, stop and ask the user before overwriting:

```
RULES.md  CLAUDE.md  ARCHITECTURE.md  GOALS.md  PLANNING.md  MEMORY.md  Checkpoint.md  handoff.md
```

If all 8 root files exist AND `tasks/`, `troubleshooting/`, `outputs/`, `.claude/` are present → the workspace is already scaffolded. Offer `/session-start` instead and exit.

If some files exist and some don't, ask: "Existing scaffold partially present. Overwrite-and-replace, fill-gaps-only, or abort?"

## Step 1 — Gather context

Ask the user (single AskUserQuestion batch):
1. **Workspace name** — short, used in document headers.
2. **Primary purpose** — one sentence; populates `GOALS.md` and `CLAUDE.md`.

Skip questions whose answers are obvious from prior context (directory name, prior messages).

## Step 2 — Compute substitutions

Set:
- `WORKSPACE_NAME` = user answer to Q1
- `PURPOSE` = user answer to Q2
- `DATE` = today (`YYYY-MM-DD`)

## Steps 3–10 — Copy and substitute the 12 template files

For each template under `templates/`, read it from the plugin directory, perform string substitution on all three placeholders, and Write the result to the target path:

| Source (in plugin) | Destination (in workspace) |
|---|---|
| `templates/RULES.md` | `RULES.md` |
| `templates/CLAUDE.md` | `CLAUDE.md` |
| `templates/ARCHITECTURE.md` | `ARCHITECTURE.md` |
| `templates/GOALS.md` | `GOALS.md` |
| `templates/PLANNING.md` | `PLANNING.md` |
| `templates/MEMORY.md` | `MEMORY.md` |
| `templates/Checkpoint.md` | `Checkpoint.md` |
| `templates/handoff.md` | `handoff.md` |
| `templates/tasks/STATUS.md` | `tasks/STATUS.md` |
| `templates/tasks/findings.md` | `tasks/findings.md` |
| `templates/troubleshooting/known-issues.md` | `troubleshooting/known-issues.md` |
| `templates/workspace.yml` | `.claude/workspace.yml` |

Create the destination directories (`tasks/`, `troubleshooting/`, `.claude/`) as needed before writing.

## Step 11 — Create the 3 placeholder folders

Create these as empty (zero-byte) `.gitkeep` files:
- `outputs/drafts/.gitkeep`
- `outputs/final/.gitkeep`
- `.claude/rules/.gitkeep`

## Step 12 — Report

Tell the user which files were created. Don't dump contents — list paths only.

## Step 13 — Verify (REQUIRED before claiming done)

Perform all three checks below. Surface any failure to the user and DO NOT report success.

### 13a — File existence

Confirm all 15 artifacts exist at the expected paths in the target workspace:

```
RULES.md
CLAUDE.md
ARCHITECTURE.md
GOALS.md
PLANNING.md
MEMORY.md
Checkpoint.md
handoff.md
tasks/STATUS.md
tasks/findings.md
troubleshooting/known-issues.md
.claude/workspace.yml
outputs/drafts/.gitkeep
outputs/final/.gitkeep
.claude/rules/.gitkeep
```

Missing files → STOP, report which are missing, do not proceed.

### 13b — CLAUDE.md line count

Read `CLAUDE.md`. Count lines. Must be **≤ 150**. If over, STOP and report the line count — a template regression has occurred.

### 13c — Placeholder substitution

For each of the 12 non-`.gitkeep` files, search for the literal strings `{{WORKSPACE_NAME}}`, `{{PURPOSE}}`, `{{DATE}}`, and any pattern matching `{{` `}}`. If ANY remains, STOP, report which file and which placeholder, do not claim success.

### 13d — Success report

Only if 13a, 13b, 13c all pass, report:

```
Workspace scaffolded: {{WORKSPACE_NAME}}
  ✓ 15 artifacts created
  ✓ CLAUDE.md within 150-line budget
  ✓ no template placeholders remaining

Next: open handoff.md for P0, or run /session-start.
```

---

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** if workspace name or purpose is ambiguous, ask once.
- **Least Complexity:** 15 artifacts is the floor. Modules add more — they are separate skills.
- **Surgical Execution:** never overwrite without confirmation in Step 0.
- **Declarative Focus:** DoD is "15 artifacts exist; CLAUDE.md ≤ 150 lines; no `{{...}}` left." Anything beyond that is a separate task.
