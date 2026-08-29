# {{WORKSPACE_NAME}} — Workspace Constitution

> ## Non-Negotiable — Apply on EVERY Prompt
> The four override constraints (Intent Clarification, Least Complexity, Surgical Execution, Declarative Focus) live in [`.claude/rules/overrides.md`](.claude/rules/overrides.md), which the harness loads into every session automatically. They apply to every task in this workspace and override any other guidance below whenever they conflict.

---

## Purpose

{{PURPOSE}}

## Session Start Checklist

When a new Claude session opens in this workspace, read these in order:

1. **handoff.md** — what the previous session left for this one (priorities, blockers)
2. **ARCHITECTURE.md** — workspace map
3. **PLANNING.md** — active initiatives
4. **Checkpoint.md** — recent session log entries (skim last 1–2 entries)

Run `/session-start` to automate the read. Run `/session-closeout` at session end to update Checkpoint.md and handoff.md.

## Core Files

| File | Read when |
|------|-----------|
| `.claude/rules/overrides.md` | Loaded automatically every session |
| `handoff.md` | Session start — next-session priorities |
| `Checkpoint.md` | Session start (skim recent) — accumulating session log |
| `ARCHITECTURE.md` | Session start or when navigating the workspace |
| `GOALS.md` | Scoping work or evaluating trade-offs |
| `PLANNING.md` | Session start or picking up in-progress work |
| `MEMORY.md` | When prior-session context is relevant |
| `tasks/STATUS.md` | Picking up unfinished tasks |
| `tasks/findings.md` | Recording discoveries during research |
| `troubleshooting/known-issues.md` | Hitting a familiar error |

## Outputs

- `output/drafts/` — work-in-progress artifacts
- `output/final/` — ship-ready artifacts

## Settings

- `.claude/workspace.yml` — verbosity + environment (`beginner|standard`, `code|cowork`)
- `.claude/rules/` — workspace-local rule files added by modules

## Linear Tracking

Status: not configured.
At session-start and session-closeout: if Linear is connected, offer to assign a team + project to track this workspace (run `linear-kickoff` tracking mode). If not connected, say so and skip. Once configured, replace this section with the post-setup version and record it in `.claude/workspace.yml` under `linear:`.

---

_Scaffolded {{DATE}} by `workspace-superengine` v0.2._
