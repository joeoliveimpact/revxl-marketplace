---
name: session-closeout
description: Use at the end of a working session to capture state — updates Checkpoint.md with a session log entry and rewrites handoff.md with next-session priorities. Trigger phrases include "let's wrap up", "closing out for the day", "session closeout", "save state", "I'm done for now", "/session-closeout", and any signal the user is ending work (e.g. "logging off", "see you tomorrow"). Pairs with /session-start.
---

# Session Closeout Procedure

Run at end of every session. No skipping the file updates — those are non-negotiable.

## Runtime environment

This skill reads `.claude/workspace.yml#environment` on entry.

- **`environment: code`** — Bash available for snapshots (`systemctl`, `docker ps`, `git log`, etc.).
- **`environment: cowork`** — all file edits use Read/Edit/Write tools. Phase 4 live-infrastructure snapshots become **advisory** — record what's known from workspace files, skip live probes.

Default to cowork-safe behavior if config missing.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> Time to wrap up. I'll write a short log of what we did today and rewrite the handoff notes so next session's Claude knows what's next. Takes about two minutes.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Sounds like you're wrapping up — want me to run `/session-closeout` to update Checkpoint.md and handoff.md? Or just stop here without logging?"

Only run the full process below after the user confirms. If the user explicitly invokes `/session-closeout`, skip the suggestion and proceed.

---

## Phase 0: Confirm RULES.md Compliance (30s)

Before writing the session log, do a quick self-check against RULES.md:
- Did this session honor Surgical Execution? (no out-of-scope edits)
- Did this session honor Least Complexity? (no over-engineering)
- Any feedback patterns from the user worth saving to memory?

If yes to the last → save a memory file (per `~/.claude/CLAUDE.md` auto memory rules) before proceeding.

---

## Phase 1: Append to Checkpoint.md (5 min)

**Both environments:**
1. Read `Checkpoint.md` with the Read tool to load current contents.
2. Construct the new entry (template below).
3. Locate the position after the file's format header (first `---` separator).
4. Use the Edit tool to insert the new entry there — replace the first `---\n` with `---\n\n<new entry>\n\n---\n`.

Do NOT use Bash redirects (`>>`) — they create encoding issues in Cowork and overwrite risk in Code.

Open `Checkpoint.md`. Add a NEW entry at the top (newest first), below the format header.

Template:
```markdown
## YYYY-MM-DD — {short title}
**Duration:** ~Xh
**TL;DR:** {1–2 sentences capturing what was accomplished}

### Completed
- {item}

### Decisions
- {decision} — why: {rationale}

### Discoveries
- {non-obvious fact learned that wasn't known before}

### Failed attempts
- {what was tried and didn't work — include root cause if known}

### Files touched
- {path} — {what changed}

### Not done (rolled to handoff.md)
- {item}

---
```

**Hard rule:** every section has content or is explicitly marked "(none)". No silent omissions.

---

## Phase 2: Rewrite handoff.md (3 min)

**Both environments:** use the Write tool to replace handoff.md entirely. If file doesn't exist, Write creates it.

handoff.md is **rewritten**, not appended. It represents the live state for the NEXT session.

Template:
```markdown
# Handoff — Next-Session Priorities

## Last session
{date} — {title} (see Checkpoint.md for full entry)

## Status
{1-line system state — what's working, what's not}

## Blockers
{numbered list, or "(none)"}

## P0 — Next Actions
1. {first thing next session should do, with verify command if applicable}
2. {second}

## P1 — Deferred
{items captured but not urgent}

## Verify before building
- {anything to check before resuming work — credentials, services, branches}

## Credentials needed
| Credential | Status | Action if missing |

## Key files from last session
- {path} — {brief note}
```

If handoff.md doesn't exist, create it. If it exists, fully replace its contents.

---

## Phase 2.5: Sync to Linear (conditional)

Runs **only if** `.claude/workspace.yml` has a `linear:` block with `status: configured`. Otherwise **skip silently**.

Trigger is the **configured flag**, not bare MCP connection (the MCP is shared across all workspaces; the per-workspace `linear:` binding scopes which project to write).

1. Read the `linear:` block — `team`, `project` (+ ids).
2. **Connection health-check:** if configured but the Linear MCP isn't connected → warn one line, skip the sync, and record `Linear sync skipped — MCP not connected` in the Checkpoint entry. **Never fail closeout over Linear.**
3. Sync this session's work to the configured project, sourced from the Checkpoint entry you just wrote:
   - Work **started** this session → create issues (or move existing) to **In Progress** under the project.
   - Work **completed** → move matching issues to **Done** (create + close if none existed).
   - **Search the project first** — never duplicate an issue that already exists.
4. Keep it coarse: one issue per meaningful unit of work, NOT per file touched.
5. Record the issue IDs touched in the Checkpoint entry (so the sync is auditable).

**Cowork:** same rule — sync if the MCP is connected; otherwise advisory (note the intended sync, don't probe-fail).

---

## Phase 3: Update Other Scaffold Files (variable)

For each file in the table that needs an update:

- **Targeted change** (a section or table row): use the Edit tool with a sufficiently unique `old_string`.
- **Full rewrite** (rare; only if a file is being repurposed): use the Write tool.

Never use `sed -i` — fails silently on Windows line endings and is unavailable in Cowork.

Walk through each of the other root files. For each, decide UPDATE or NO CHANGE — never silently skip.

| File | Update if… |
|------|------------|
| ARCHITECTURE.md | New folder, new root file, major structural change, or a new integration wired up (e.g. Linear tracking) |
| GOALS.md | Goals shifted, new success metric, or new active integration |
| PLANNING.md | Initiative completed, new initiative started, or pending item resolved |
| MEMORY.md | New memory file added — append to index |
| RULES.md | NEVER edit unless user explicitly asks — these are the override constraints |
| CLAUDE.md | Workspace purpose changed or new core file added |

---

## Phase 4: Workspace-Specific Snapshots (conditional)

If the workspace has live infrastructure, snapshot it. Otherwise skip.

**Skip if:** pure document workspace, no servers, no MCP servers running, no APIs.

**Run if:** workspace has services, agent runtimes, hosted MCP servers, etc. Reference any
`.claude/health-checks.md` or workspace-specific runbook for the exact commands to run.

**Code environment:**
- Run service status: `systemctl status <svc>` or `docker ps`
- Snapshot config: read versions, env values, agent registry
- Background tasks: list running / completed / failed with verify command for each
- Credential checklist (status only, no values)
- Record results in the matching Checkpoint.md entry section.

**Cowork environment — advisory snapshot:**
- Read `.claude/workspace.yml`, `.claude/health-checks.md`, and any service-config files via Read tool.
- Record CONFIGURED state (what the workspace is set up to run), not LIVE state.
- Add a banner to the Checkpoint.md "Phase 4 snapshot" section: `> Cowork environment — live probes skipped. Configured state only.`
- For background tasks, list the verify commands the next session should run rather than results.

---

## Phase 5: Final Verification — Explicit Handoff Table

Report this table to the user. Every applicable file gets a row with action + reason if NO CHANGE.

```
| File              | Action     | Reason (if NO CHANGE) |
|-------------------|------------|-----------------------|
| Checkpoint.md     | UPDATED    | — |
| handoff.md        | UPDATED    | — |
| ARCHITECTURE.md   | ?          | ? |
| GOALS.md          | ?          | ? |
| PLANNING.md       | ?          | ? |
| MEMORY.md         | ?          | ? |
```

Also confirm:
1. Checkpoint.md entry is self-contained for someone who wasn't in this session?
2. handoff.md P0 list is actionable (not vague)?
3. Any background tasks have verify commands documented?
4. Any durable user/feedback/project learnings saved to memory?

If any row shows `?` — fix it before reporting complete.

---

## Quick mode (for short sessions)

If the session was under 30 minutes and touched <3 files, you can:
- Skip Phase 0, Phase 3, Phase 4
- Write a 3-line Checkpoint.md entry
- Update handoff.md if anything blocks the next session

Don't quick-mode a session that touched architecture, made decisions, or hit failures.
Those need the full procedure.
