---
name: session-pickup
description: Use at the start of a working session to load context — reads RULES.md, handoff.md, ARCHITECTURE.md, PLANNING.md, recent Checkpoint.md entries, and surfaces priorities for this session. Trigger phrases include "let's start the session", "pick up where we left off", "what was I working on", "session start", "/session-start", and any opening message that suggests the user is resuming work without saying so explicitly (e.g. "morning", "back at it"). Replaces the legacy /session-pickup command.
---

# Session Pickup Procedure

Run at the start of every session. Don't start building until Phase 0 + Phase 4 complete.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Looks like you're starting fresh — want me to run `/session-start` to pull priorities from handoff.md and recent Checkpoint entries? Or do you already know what you're working on?"

Only run the full process below after the user confirms. If the user explicitly invokes `/session-start`, skip the suggestion and proceed.

---

## Phase 0: RULES.md — Non-Negotiable (30s)

**Always first.** Read `RULES.md` at workspace root. The four override constraints
(Intent Clarification, Least Complexity, Surgical Execution, Declarative Focus) govern
every action this session.

If RULES.md is missing → flag immediately. Suggest running `/super-setup` to scaffold
the workspace, or run `/agent-optimizer` to load the constraints into context directly.

---

## Phase 1: Read Handoff Docs (2 min)

Read in order. Don't skip.

1. **handoff.md** — what the previous session left for this one (P0, blockers, status)
2. **ARCHITECTURE.md** — workspace map (skim if you've read it recently)
3. **PLANNING.md** — active initiatives
4. **Checkpoint.md** — most recent 1–2 entries only (skim for context, don't read the whole log)
5. **MEMORY.md** — only if today's work touches a topic indexed there

**If any file is missing** → workspace isn't fully scaffolded. Suggest `/super-setup`.

After reading, state to user:
- What the last session accomplished (1 sentence from Checkpoint.md top entry)
- What blockers handoff.md flagged
- What today's planned work is (from handoff.md P0)

---

## Phase 2: Verify Anything handoff.md Flagged (3 min)

handoff.md may list:
- Background tasks needing verification (run their verify commands)
- Service health checks (only if workspace has live services)
- Credential checks (confirm SET, don't print values)
- "Verify before building" items

For each item, run the check, record actual result. **Stop if any critical item failed.**
Don't paper over a broken state — fix it or flag it before proceeding.

If handoff.md has no verification items → skip Phase 2.

---

## Phase 3: Workspace-Specific Health (variable)

If the workspace has live infrastructure (servers, MCP servers, APIs), run any health
checks documented in ARCHITECTURE.md or `.claude/health-checks.md`. This phase is
**conditional** — pure-document workspaces skip it.

Common patterns:
- Service status (systemctl, docker ps)
- MCP server connectivity
- API key validity
- File/folder integrity (no `/skills/` or `/memory/` in agent workspaces — token pollution risk)

---

## Phase 4: Present Status Brief (1 min)

Format:

```
SESSION PICKUP — {date}

Last session: {1-line summary from Checkpoint.md}
Handoff status: {clean / X blockers}
Verification: {all passed / X failed}

Blockers:
  1. {blocker — action needed}

Ready to work on:
  1. {handoff.md P0 #1}
  2. {handoff.md P0 #2}

Where do you want to start?
```

End your turn. Wait for direction before starting work.

---

## When to skip phases

- **Pure document workspace** (no servers, no MCP) → skip Phase 3 entirely
- **Continuing a session in the same window** (no break) → skip pickup, just continue
- **Brand-new empty workspace** → run `/super-setup` instead of pickup

---

## Common failure patterns to check

If today's work touches any of these, verify before building:

- **Stale references:** RULES.md, handoff.md, or Checkpoint.md pointing to files that no longer exist
- **Drift between Checkpoint.md and reality:** "Service X running" claims that don't match actual state
- **Context bloat:** large directories advertised in system prompts (skills/, memory/ inside agent workspaces)
- **Credential expiry:** API keys, tokens that may have rotated
