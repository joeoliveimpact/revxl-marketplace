---
name: super-setup
description: One-shot workspace scaffolding. Creates RULES.md (referencing /agent-optimizer), CLAUDE.md (referencing RULES.md as non-negotiable), ARCHITECTURE.md, GOALS.md, PLANNING.md, MEMORY.md, Checkpoint.md, handoff.md. Wires session-pickup and session-closeout into the lifecycle. Use when starting a new workspace from scratch or when a workspace is missing core scaffold files.
---

# Super-Setup — Unified Workspace Scaffolding

One skill, one pass. Replaces ad-hoc scaffolding with a guaranteed file scheme that `/session-pickup` and `/session-closeout` know how to read.

---

## Step 0 — Detect

Run from the target workspace root. List existing root files. If ANY of the eight scaffold files exist, ask the user before overwriting:

```
RULES.md, CLAUDE.md, ARCHITECTURE.md, GOALS.md, PLANNING.md, MEMORY.md, Checkpoint.md, handoff.md
```

If all eight exist → skill is a no-op; offer to run `/session-pickup` instead.

---

## Step 1 — Gather workspace context

Ask the user three short questions (use AskUserQuestion in one batch):

1. **Workspace name** — used in document headers (e.g. "MCP Connection Builders")
2. **Primary purpose** — one sentence; populates GOALS.md and CLAUDE.md
3. **Optional plugins/connectors** — does the user want to layer cowork plugin setup on top? If yes, also invoke `anthropic-skills:setup-cowork` after file creation.

Skip if all three are obvious from existing context (e.g. memory, prior conversation, directory name).

---

## Step 2 — Write the eight files

All eight files use the templates in `templates/`. Variables: `{{WORKSPACE_NAME}}`, `{{PURPOSE}}`, `{{DATE}}`.

| File | Template | Notes |
|------|----------|-------|
| RULES.md | `templates/RULES.md` | References /agent-optimizer + inlines 4 constraints |
| CLAUDE.md | `templates/CLAUDE.md` | Banner: RULES.md non-negotiable on every prompt |
| ARCHITECTURE.md | `templates/ARCHITECTURE.md` | Lists all root files + session lifecycle |
| GOALS.md | `templates/GOALS.md` | Seeded with `{{PURPOSE}}` |
| PLANNING.md | `templates/PLANNING.md` | Empty initiatives, scaffolding listed in Recently Completed |
| MEMORY.md | `templates/MEMORY.md` | Empty index pointing to `.claude/memory/` |
| Checkpoint.md | `templates/Checkpoint.md` | Format header + first entry (today's scaffolding) |
| handoff.md | `templates/handoff.md` | P0 = "test this scaffolding", "inventory existing assets" |

**Surgical rule:** never overwrite an existing file without explicit confirmation. If the user confirmed in Step 0, write fresh.

---

## Step 3 — Wire session lifecycle

Confirm these skills exist at `~/.claude/skills/`:
- `agent-optimizer/SKILL.md`
- `session-pickup/SKILL.md`
- `session-closeout/SKILL.md`

If any are missing, flag to the user. The scaffold files reference these by `/name` — they must be installed for the workflow to work.

---

## Step 4 — Optional: layer cowork setup

If the user opted in during Step 1, invoke `anthropic-skills:setup-cowork` now. That skill handles plugins/connectors via Cowork UI widgets — orthogonal to the file scaffolding done above.

---

## Step 5 — Wrap

Report to user:

```
Workspace scaffolded:
  ✓ RULES.md — /agent-optimizer constraints (non-negotiable)
  ✓ CLAUDE.md — references RULES.md on every prompt
  ✓ ARCHITECTURE.md, GOALS.md, PLANNING.md, MEMORY.md
  ✓ Checkpoint.md (session log), handoff.md (next-session priorities)

Session lifecycle:
  /session-pickup  — start of every session
  /session-closeout — end of every session

Next: run /session-pickup or start working. handoff.md has the P0 list.
```

---

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** if workspace name or purpose is ambiguous, ask once.
- **Least Complexity:** eight files is the floor. Do not add more "just in case."
- **Surgical Execution:** never overwrite without confirmation.
- **Declarative Focus:** DoD is "the eight files exist with sensible content; session skills work against them." If the user asks for a feature beyond that, push it to a separate task.

---

## Promotion path

This skill currently lives at `.claude/skills/super-setup/` (workspace-local). Once tested and stable, copy the entire directory to `~/.claude/skills/super-setup/` to make it user-global.
