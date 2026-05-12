# RULES.md — {{WORKSPACE_NAME}}

> **Non-negotiable. Apply on EVERY prompt, in EVERY session, by EVERY agent (main and subagents).**
> These four override constraints come from `agent-optimizer`. They beat any other guidance in this workspace whenever they conflict.

---

## The four override constraints

1. **Intent Clarification** — NEVER assume user intent on ambiguous tasks. If a request has multiple valid interpretations or lacks clear success criteria, stop and ask clarifying questions before taking action.

2. **Least Complexity** — Default to the simplest solution that meets the goal. No bloat, no over-engineering. If a task can be finished in 3 steps, do not propose 10.

3. **Surgical Execution** — When modifying existing work (files, text, code, data), ONLY change the specific parts requested. NEVER reformat, "clean up," or alter unrelated sections unless explicitly instructed.

4. **Declarative Focus** — Always identify the Definition of Done for a task. If given a list of steps, evaluate them against the ultimate goal and flag a more efficient path if one exists. Do not execute steps mechanically when a better path is visible.

---

## Reloading the constraints mid-session

If a session drifts off these rules, the user (or Claude) can reload them via the `/agent-optimizer` skill. The skill re-injects the full reasoning behind each constraint.

---

## Why this file is at the workspace root

`CLAUDE.md` opens with a directive to read this file on every prompt. Putting RULES.md at the root (not buried in `.claude/`) makes it visible to humans reviewing the workspace and to any tool that lists root files.

_Last touched: {{DATE}}_
