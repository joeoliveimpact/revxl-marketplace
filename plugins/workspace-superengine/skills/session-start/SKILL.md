---
name: session-start
description: Use at the start of a working session to load context — reads RULES.md, handoff.md, ARCHITECTURE.md, PLANNING.md, recent Checkpoint.md entries, and surfaces priorities for this session. Trigger phrases include "let's start the session", "pick up where we left off", "what was I working on", "session start", "/session-start", and any opening message that suggests the user is resuming work without saying so explicitly (e.g. "morning", "back at it"). Replaces the legacy /session-pickup command.
---

# Session Start Procedure

Run at the start of every session. Don't start building until Phase 0 + Phase 4 complete.

## Runtime environment

This skill reads `.claude/workspace.yml#environment` on entry. Two paths:

- **`environment: code`** — use Bash freely for `cat`, `ls`, `test`, `git`, service probes.
- **`environment: cowork`** — Bash is unavailable or sandboxed. Use the Read / Glob / Grep / Write tools for all file ops. Live service / git / MCP probes become **advisory** — surface the commands to the user; do not attempt them.

If `.claude/workspace.yml` is missing or unreadable, default to **cowork-safe behavior** (no Bash) and flag it: "Workspace config not found — running in safe mode. Run `/super-setup` to scaffold or `/workspace-set-verbosity` to repair config."

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> Welcome back. I'll spend the first minute reading the four most important files (your rules, your handoff notes, your project plan, and the latest session log) so I know exactly where we left off. Then I'll tell you what's ready to work on.

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

## Phase 0.5: Linear Review — the source of truth (conditional)

**Runs BEFORE the local files are read.** Where a tracker is configured, it — not the workspace files — is the record of record for what is open, done, and in progress. Local files are a summary/backup written by whoever closed out last; they go stale the moment work happens somewhere else. Reading them first anchors the brief to the weaker source.

Runs **only if** `.claude/workspace.yml` has a `linear:` block with `status: configured`. If `status` is `unset`/`declined`, or there is no `linear:` block → **skip silently** and go straight to Phase 1.

The trigger is the **configured flag**, NOT a bare MCP connection. The Linear MCP is shared across every workspace, so "is Linear connected?" is true everywhere and can't scope anything — the per-workspace `linear:` binding (team + project) is what decides which project to read.

1. Read the `linear:` block — note `team`, `project` (and their ids), and `scope` if present.
2. **Connection health-check:** probe the Linear MCP (e.g. `list_issues`). If the workspace is configured but the MCP is **not** connected → surface a one-line warning (`Linear configured but MCP not connected — issues not pulled`), note that the brief is therefore built from local files alone, and continue. **Never fail session-start over Linear.**
3. Pull open issues (non-completed states), scoped by the `linear:` block:
   - **Default (project-scoped):** `list_issues` filtered to the configured `project`.
   - **`scope: team`** (workspace spans multiple projects — e.g. a Client Work hub with one project per client): `list_issues` filtered to the `team`, grouped by project. Use this when the block has a `team` but no `project`.
   Summarize: total count + the top few by priority/status (and by project, if team-scoped).
4. Carry the summary into Phase 1 (as the baseline the local files are checked against) and into the Phase 4 brief.

**Look up projects and teams by ID, not by name** where the config provides one — a name lookup can silently return empty and read as "nothing open."

**Cowork:** the Linear MCP works in Claude Desktop too when connected; if not connected, treat as advisory (note it, don't probe-fail).

---

## Phase 1: Read Handoff Docs (2 min)

1. Use the Read tool on each file (works in both environments):
   - `handoff.md`
   - `ARCHITECTURE.md`
   - `PLANNING.md` *(optional — read it if present; not every workspace has one)*
   - `Checkpoint.md` (read only the most recent 1–2 entries — use offset/limit params)
   - `MEMORY.md` (only if today's work touches an indexed topic)

2. Existence check before each read:
   - Code: optionally `test -f <path>` via Bash if you prefer
   - Cowork: use Glob with the exact filename pattern, OR attempt Read and treat ENOENT as "missing"

If `RULES.md`, `handoff.md`, `ARCHITECTURE.md`, or `Checkpoint.md` is missing → the workspace isn't fully scaffolded. Suggest `/super-setup`. A missing `PLANNING.md` alone is not a scaffolding failure — note it and move on.

### Check the local files against what the tracker said (only when Phase 0.5 ran)

Compare the two. Where they disagree — a Linear issue marked Done that handoff still lists as a blocker, work that moved this week with no Checkpoint entry, a P0 with no matching issue — **surface it, do not silently resolve it in either direction.**

Show both versions and ask which is right. The tracker is the default authority for *reporting* state, but a disagreeing local file may be the correct side: work that got done and never filed, or a step the process dropped. Then update whichever side is stale. Never overwrite correct information to make two sources match.

Work done in another workspace still counts — a tracker spans workspaces, these files do not. An unexplained gap between the two usually means exactly that, not that nothing happened.

After reading, state to user:
- What the last session accomplished (1 sentence from Checkpoint.md top entry)
- What blockers handoff.md flagged
- What today's planned work is (from handoff.md P0)

---

## Phase 2: Verify Anything handoff.md Flagged (3 min)

For each verification item in handoff.md:

- **Code environment:** run the verify command via Bash. Record actual result.
- **Cowork environment:** display the verify command to the user as a quoted block. Ask them to run it and paste the result back. Mark the check as "user-verified" or "unverified" — do not silently skip.

**Stop if any critical item failed** in either environment. In Cowork, "failed" includes "user declined to verify".

If handoff.md has no verification items → skip Phase 2.

---

## Phase 3: Workspace-Specific Health (variable)

**Code environment** — run any checks documented in ARCHITECTURE.md or `.claude/health-checks.md`. Examples: `systemctl status`, `docker ps`, curl probes against MCP server URLs, API key smoke tests.

**Cowork environment** — Phase 3 is **advisory-only**:
- Read `.claude/health-checks.md` if it exists (use Read tool).
- Surface the documented checks to the user as a checklist. Do not attempt to run them.
- For MCP server connectivity, list the servers configured in the workspace and note: "Cowork cannot probe these directly — confirm in Claude Desktop's MCP panel."

Pure-document workspaces skip Phase 3 entirely regardless of environment.

---

## Phase 4: Present Status Brief (1 min)

Format:

```
SESSION START — {date}

Linear: {N open — top: ID title (priority, status); or "MCP not connected — brief built from local files only"}

Last session: {1-line summary from Checkpoint.md}
Handoff status: {clean / X blockers}
Verification: {all passed / X failed}

Blockers:
  1. {blocker — action needed}

Drift: {none / "Linear shows X, handoff says Y — which is right?"}

Ready to work on:
  1. {P0 #1}
  2. {P0 #2}

Where do you want to start?
```

(Omit the Linear line entirely if the workspace has no `linear:` block — don't print "not configured" noise in workspaces that never opted in. Show it only when a `linear:` block exists. Omit the Drift line when there is nothing to report — silence is the correct output for a workspace whose files match its tracker.)

End your turn. Wait for direction before starting work.

---

## When to skip phases

- **Pure document workspace** (no servers, no MCP) → skip Phase 3 entirely
- **Continuing a session in the same window** (no break) → skip session-start, just continue
- **Brand-new empty workspace** → run `/super-setup` instead of session-start

---

## Common failure patterns to check

If today's work touches any of these, verify before building:

- **Stale references:** Use the Grep tool to search RULES.md, handoff.md, Checkpoint.md top entry for path strings; verify each path exists via Glob (Cowork) or `test -f` (Code).
- **Drift between Checkpoint.md and reality:** "Service X running" claims that don't match actual state
- **Context bloat:** large directories advertised in system prompts (skills/, memory/ inside agent workspaces)
- **Credential expiry:** API keys, tokens that may have rotated
