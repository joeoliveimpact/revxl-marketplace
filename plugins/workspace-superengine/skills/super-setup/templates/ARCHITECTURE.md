# ARCHITECTURE.md — {{WORKSPACE_NAME}}

Map of every root file and folder. Update when you add or remove anything.

## Root files

| File | Purpose |
|------|---------|
| `RULES.md` | Four override constraints (non-negotiable, every prompt) |
| `CLAUDE.md` | Workspace constitution and session checklist |
| `ARCHITECTURE.md` | This file — workspace map |
| `GOALS.md` | Primary purpose + success criteria |
| `PLANNING.md` | Active projects + Now / Next / Later roadmap |
| `MEMORY.md` | Index into the 6 named memory buckets |
| `Checkpoint.md` | Append-only session log |
| `handoff.md` | What the next session should pick up first |

## Folders

| Folder | Purpose |
|--------|---------|
| `tasks/` | Operational task tracking (`STATUS.md`, `findings.md`) |
| `troubleshooting/` | Known issues, runbooks |
| `outputs/drafts/` | Work-in-progress artifacts (drafts, scratch) |
| `outputs/final/` | Ship-ready artifacts |
| `.claude/` | Workspace-local Claude config: `workspace.yml`, `rules/`, future hooks/agents |

## Session lifecycle

```
session-start  →  read RULES → handoff → ARCHITECTURE → PLANNING → Checkpoint
work happens
session-closeout  →  update Checkpoint.md, rewrite handoff.md
```

_Last touched: {{DATE}}_
