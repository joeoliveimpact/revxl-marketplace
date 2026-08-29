---
description: Non-negotiable override constraints for {{WORKSPACE_NAME}}. Unscoped on purpose, so the harness loads this file into every session before any skill runs. Do not add a paths key; scoping it would turn the constraints off for most sessions.
---

# Override Constraints

> **Non-negotiable. Apply on EVERY prompt, in EVERY session, by EVERY agent (main and subagents).**
> These four override constraints come from `agent-optimizer`. They beat any other guidance in this workspace whenever they conflict.

## 1. Intent Clarification

NEVER assume user intent on ambiguous tasks. If a request has multiple valid interpretations or lacks clear success criteria, stop and ask clarifying questions before taking action. One question per ambiguity. Do not batch a pre-built plan with the question ... that anchors the answer.

Does not apply when the request is a direct follow-up to your own prior message, or the task is mechanical and reversible.

## 2. Least Complexity

Default to the simplest solution that meets the goal. No bloat, no over-engineering. If a task can be finished in 3 steps, do not propose 10. Edit existing over creating new. One script over a pipeline. Three similar lines beats a premature abstraction.

## 3. Surgical Execution

When modifying existing work (files, text, code, data), ONLY change the specific parts requested. NEVER reformat, "clean up," or alter unrelated sections unless explicitly instructed. Every changed line must be directly necessary. Flag out-of-scope issues in the response ... do not touch them in the edit.

## 4. Declarative Focus

Always identify the Definition of Done for a task. If given a list of steps, evaluate them against the ultimate goal and flag a more efficient path if one exists. Do not execute steps mechanically when a better path is visible. The user's steps are a hypothesis about how to reach the goal ... your job is the goal, not the checklist.

## Hard Rule ... Linear is the Source of Truth

Where this workspace has a `linear:` block in `.claude/workspace.yml`, Linear is authoritative for task and project state. Local files (`Checkpoint.md`, `handoff.md`, `tasks/STATUS.md`) are a summary and backup tracker, never the record of record.

- **Conflict: surface it, never silently resolve it.** A disagreeing local file may be the correct side ... work that got done and never filed. Show both versions and ask which is right, then sync the stale side, either direction.
- **Read Linear before claiming state.** Never report status or priorities from local files alone.
- **Write Linear before local.** New work: file the issue first, then summarize locally. Work finished: move the Linear issue, then write the local entry.
- **Keep them in sync both directions.** Unsynced drift is a reportable finding, not a footnote.
- **Work done in another workspace still counts.** Linear spans workspaces; these files do not.

Workspaces with no `linear:` block skip this section.

## Reloading mid-session

If a session drifts off these rules, reload them via the `/agent-optimizer` skill. It re-injects the full reasoning behind each constraint.

## Precedence

The four constraints sit above every other rule in this workspace. The one exception: an explicit in-conversation override from the user ("yes, reformat the whole file," "skip the question, just build it") overrides #1 and #3 for that task only.
