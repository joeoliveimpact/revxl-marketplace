---
name: session-start
description: Use at the start of a working session to load context ... verifies the override constraints (migrating a legacy RULES.md into .claude/rules/overrides.md when found), reads handoff.md, ARCHITECTURE.md, PLANNING.md, recent Checkpoint.md entries, and surfaces priorities for this session. Trigger phrases include "let's start the session", "pick up where we left off", "what was I working on", "session start", "/session-start", and any opening message that suggests the user is resuming work without saying so explicitly (e.g. "morning", "back at it"). Replaces the legacy /session-pickup command.
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

## Phase 0: Override constraints ... Non-Negotiable (30s)

**Always first.** The four override constraints (Intent Clarification, Least Complexity,
Surgical Execution, Declarative Focus) govern every action this session. Where they live
depends on the workspace's generation; check in this order:

1. **`.claude/rules/overrides.md` exists** → in the Code environment the harness already
   loaded it into this session; do not re-read it, state one line (constraints active via
   rules file) and move on. In the Cowork environment, Read the file ... harness rules
   loading is unverified there, so the Read IS the load. **If a root `RULES.md` ALSO
   exists**, it is stale ... it stopped being authoritative at migration. Say so in one
   line and (Code only) quarantine it and repoint its references, per the quarantine,
   manifest, repointing, and receipt bullets of the migration step below. In the
   Cowork environment nothing can be moved, so say the root copy is stale and leave
   it; the next Code session retires it. **Do not run that
   step's first bullet here**: `overrides.md` already exists, and rewriting it from a
   legacy body would overwrite the live rules with the stale copy. Never leave both
   copies live, and never silently ignore it.
2. **Legacy: root `RULES.md` exists and `.claude/rules/overrides.md` does not** (Code
   environment only) → **migrate it now, once:**
   - Read `RULES.md` in full. Write `.claude/rules/overrides.md`: a frontmatter block
     whose `description:` says these are the workspace's override constraints, loaded
     every session, migrated from the legacy root RULES.md ... and **no `paths:` key**
     (unscoped is the load mechanism) ... followed by the RULES.md body **verbatim.
     Do not summarize, reorder, or drop anything: fleet audit 08.29.26 found
     workspace-specific standing policy in these files.**
   - Quarantine the original. **If `_recycle-bin/` does not exist yet, create it
     first**, in the shape the next bullet specifies, then create today's
     `<YYYY-MM-DD>/` batch folder. Only then move `RULES.md` to
     `_recycle-bin/<YYYY-MM-DD>/RULES.md`, and append its manifest row in the same
     pass: a file sitting in the bin with no row is the one state the contract
     forbids. If that exact path is already taken, suffix before the FIRST dot
     (`RULES-1.md`, then `RULES-2.md`) and give the new file its own row. Never
     overwrite a file already in the bin.
   - The row goes in `_recycle-bin/MANIFEST.md`. Build the bin as
     `docs/recycle-bin.md` specifies rather than improvising a shape: `_recycle-bin/`
     holding a `README.md`, a `MANIFEST.md`, and the dated batch folder. The manifest
     header row is exactly
     `| File | Original path | Quarantined | Eligible | Reason | Notes |` over a
     matching separator row, and **all six columns are required**: `File` is the
     basename as stored in the bin (so it carries any collision suffix),
     `Original path` is workspace-relative with forward slashes, `Quarantined` is
     today as `YYYY-MM-DD`, `Eligible` is that date plus 7 days, `Reason` is a short
     phrase such as `migrated to .claude/rules/overrides.md`, and `Notes` starts empty
     because a later restore annotates it there. The `README.md` restates, IN FULL,
     the three numbered contract points (nothing enters without a manifest row;
     everything stays recoverable until emptied; emptying is an explicit act, never a
     timer) and the scope-discipline section that keeps the bin out of scope for every
     skill except a missing-file lookup or a direct question about it. A human
     browsing the workspace without this plugin installed has to get the whole
     contract from that file alone. A short manifest is the measured failure mode, not
     a hypothetical: the first real migration improvised four columns and left a
     restore nowhere to record itself. Never delete the file, and never leave both
     copies live ... two live copies with one authoritative is a silent-drift trap.
   - Repoint the live references before they dangle. Grep the workspace for
     `RULES.md`, then **discard three classes of hit before changing anything.**
     Everything under `_recycle-bin/`: the manifest row names the file on purpose and
     `Original path` IS the restore address, so rewriting it destroys the only way
     back, and the quarantined copy has to stay byte-identical. Everything inside
     `.claude/rules/overrides.md`: its body is verbatim by the rule two bullets above,
     and its frontmatter names the file it came from on purpose. And every hit in
     `Checkpoint.md`, `handoff.md` history, session logs, `tasks/findings.md`,
     `troubleshooting/known-issues.md`, or any dated entry: those record what
     happened and rewriting them falsifies the record. Then rewrite ONLY prose and
     table references in markdown config: `CLAUDE.md`'s opening rules line and its
     read-at-session-start table, `ARCHITECTURE.md`'s file map, other
     `.claude/rules/*.md`, and module docs. **Leave code and config alone.** A string
     literal in a script is not a pointer, and a path in `.gitignore` rewritten this
     way silently untracks the rules file; a workspace-root marker list needs the new
     path ADDED, never substituted, because other workspaces still have the old file.
     Use the Grep tool or `rg`, never `grep -r`, which walks `.git`. Write the target
     as `.claude/rules/overrides.md`, noting that it now loads automatically. In a
     table row, copy the shape `super-setup` scaffolds (this example tracks
     `super-setup/templates/CLAUDE.md`; the two move together):

     ```
     | `.claude/rules/overrides.md` | Loaded automatically every session |
     ```

     Change only the reference lines and leave the rest of those files untouched.
     Name the files you edited. Skipping this aims every pointer at the recycle bin.
   - Tell the user in one line: rules moved to `.claude/rules/overrides.md` (loads
     every session now) ... or, on the both-files-present path where nothing moved,
     that the stale root copy was retired to the recycle bin and `overrides.md` was
     left untouched ... plus, only if you actually rewrote any, which files had their
     pointers updated.
   - The migrated file takes effect from the NEXT session; for THIS session, apply the
     constraints from the RULES.md you just read.
   In the Cowork environment, skip the migration (no reliable file moves there): read
   whichever of the two files exists and apply the constraints from it.
3. **Neither file exists** → flag immediately. Suggest running `/super-setup` to
   scaffold the workspace, or run `/agent-optimizer` to load the constraints into
   context directly.

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

If `handoff.md`, `ARCHITECTURE.md`, or `Checkpoint.md` is missing ... or the rules slot is empty (neither `.claude/rules/overrides.md` nor a legacy root `RULES.md` exists) ... the workspace isn't fully scaffolded. Suggest `/super-setup`. A missing `PLANNING.md` alone is not a scaffolding failure ... note it and move on.

### Check the local files against what the tracker said (only when Phase 0.5 ran)

Compare the two. Where they disagree — a Linear issue marked Done that handoff still lists as a blocker, work that moved this week with no Checkpoint entry, a P0 with no matching issue — **surface it, do not silently resolve it in either direction.**

Show both versions and ask which is right. The tracker is the default authority for *reporting* state, but a disagreeing local file may be the correct side: work that got done and never filed, or a step the process dropped. Then update whichever side is stale. Never overwrite correct information to make two sources match.

Work done in another workspace still counts — a tracker spans workspaces, these files do not. An unexplained gap between the two usually means exactly that, not that nothing happened.

After reading, state to user:
- What the last session accomplished (1 sentence from Checkpoint.md top entry)
- What blockers handoff.md flagged
- What today's planned work is (from handoff.md P0)

---

## Phase 1.5: Goal alignment check (silent unless something is actually wrong)

A three-second look at whether this workspace still knows what it is for.

**The default outcome of this phase is total silence.** Say nothing about goals unless one of the two named conditions below is true. No "goals look fine", no green checkmark, no reassurance line, no row in the brief. A check that speaks every single session turns into nagging, nagging gets tuned out, and then nobody reads it on the one session where it mattered. Silence on a clean workspace is the requirement, not a nicety.

Read `.claude/workspace.yml` (the `goals:` block, if it has one) and `GOALS.md`. Both are plain Read-tool reads, so this works the same in Claude Code and in Cowork.

**Check the two conditions in order, and first true wins. Never emit more than one line total.** A workspace that deferred at setup will usually satisfy both at once ... it has the banner AND it still has the untouched placeholder rows underneath ... because they are two symptoms of one debt. Two lines about the same debt is the nagging this phase exists to prevent. Condition 1 fires, you say your one line, you stop checking.

**Condition 1 ... goals were parked at setup.** First: if `goals.status: declined`, this condition is **FALSE** and you skip it, no matter what else you see. Otherwise it is true if `goals.status: deferred`, OR `GOALS.md` carries a `GOALS DEFERRED` banner. Either marker on its own is enough; they are deliberately redundant. Emit exactly one line, and put it in the Phase 4 brief's `Blockers` section:

> Goals are still parked from setup. I'll walk you through them at your next `/session-closeout`, using what you actually work on today.

**Informational only. Do NOT ask the goal question here.** Setup asking too early is the exact bug this whole feature exists to fix, and asking again at session-start ... before any work has happened today ... re-imports it. One line, no question mark, move on.

**Condition 2 ... goals are blank or still placeholder.** First: if `goals.status: declined`, this condition is **FALSE** and you skip it, no matter what the file looks like. Otherwise it is true if `GOALS.md`'s `## Primary purpose` is empty or still reads `{{PURPOSE}}`, or `## Success criteria` holds nothing but the shipped placeholder rows (the ones ending in the literal `…` ellipsis). Emit one line in `Blockers`:

> `GOALS.md` never got filled in. Worth five minutes at closeout ... I'll propose some based on what you work on.

**Legacy workspaces with no `goals:` block.** Any workspace scaffolded before this check existed has no `goals:` block, and that absence is not a problem by itself. Judge those on `GOALS.md` alone: real content → clean, stay silent, and do NOT add the block. **That "do NOT add" is narrow, and it is worth reading twice: it means don't write config just to record that a workspace is fine.** It never means the block can't be created when there is a real state to save ... `/session-closeout` Phase 2.7b Step 5 creates it on a decline for exactly that reason. Placeholder or blank content → Condition 2 applies. A missing block is never on its own a reason to speak.

**`goals.status: declined` beats everything else in this phase.** It means the user explicitly asked to be left alone about goals. Treat the workspace as clean and stay silent. That is why the short-circuit is written into both conditions above rather than left as a note down here ... a condition you have to remember to correct afterwards is a condition somebody evaluates wrong.

**`declined` is not a life sentence, though.** If the user themselves asks to set goals ... "let's set goals", "can we revisit the goals" ... that is a reopen, and the procedure is `/session-closeout` Phase 2.7d: clear the status back to `unset`, remove the end-state line from `GOALS.md`, then run the goal pass. Session-start does not edit `GOALS.md`, so run that procedure rather than half-doing it here. **You still never bring this up first.** The user asks, or nothing happens.

**Precedence, for the one case where the two markers disagree:** if `goals.status: declined` AND a `GOALS DEFERRED` banner are somehow both present, **`declined` wins.** The banner is leftover from before the user declined; their "stop asking" is the newer signal and it is a direct instruction. Stay silent. Do not delete the banner from here ... session-start does not edit `GOALS.md`. The next `/session-closeout` clears it.

**Everything else is clean → emit nothing at all.** Goals present and filled in is the normal case, and it produces zero output from this phase.

Whether today's work contradicts the stated goals is checked at **closeout**, not here. At session-start no work has happened yet, so there is nothing to compare against, and guessing produces exactly the chatter this phase is designed to avoid.

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

## Phase 3.5: Sweep background processes left by earlier sessions (Code only)

Closeout catches what the session it is closing started. It never runs at all when a session crashes, gets killed, or is closed by shutting the window ... which is exactly how a process ends up still running three days later. This phase is the other half: it picks up what those sessions never got to close.

**`environment: cowork`** ... Cowork has no Bash, so this cannot run. If the user asks, tell them plainly that background process checks only work in Claude Code. Do not report it as clean.

**`environment: code`:**

1. Run `"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" process-ledger list`. If it produces **no output at all**, fall back to the path stored in `~/.claude/workspace-superengine/process-ledger/cli-path.txt`. If neither works, say that the check could not run. **Do not treat silence as "nothing found."**
2. If the output starts with `PROCESS LEDGER UNAVAILABLE`, put that in `Blockers` as one line in the tool's own words. Never translate it into "nothing found". Also check the `Workspace:` line names this workspace before trusting anything under it; the `Resolved by:` line underneath says how that was worked out, and is what you quote when the workspace looks wrong.
3. If it reports nothing recorded, emit nothing here and move on. That is the normal case and it should be quiet.
4. If it lists entries, put **one line** in the Phase 4 brief's `Blockers` section:

   > 2 background processes from earlier sessions are still running (about 220 MB). Say the word and I will show you the list.

   Then stop. Do not stop anything at session-start on your own initiative. If the user asks, follow **`/session-closeout` Phase 4.2 Steps 2 to 5** exactly ... same list, same explicit consent, same consent token, same rule that a skipped process stays alive.

The sweep returns the same five states closeout uses (`STOPPABLE`, `OTHER-WINDOW`, `MISMATCH`, `MACHINERY`, `GONE`), and the table in **`/session-closeout` Phase 4.2 Step 2** is the single description of them. Only `STOPPABLE` is ever countable as something the user could act on. Two of them come up here often enough to name:

- **`MISMATCH`** is reported and never acted on. That pid is running something other than what was recorded, which on Windows usually just means the number got reused. Stopping it would kill a program this workspace never started.
- **`MACHINERY`** is Claude's own plumbing, refused even though the entry is accurate. It is the tool working correctly, not a finding. Do not put it in `Blockers` and do not raise it on its own.

You may also see a count of processes **refused as machinery** at recording time. Informational, no action.

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

(Omit the Linear line entirely if the workspace has no `linear:` block — don't print "not configured" noise in workspaces that never opted in. Show it only when a `linear:` block exists. Omit the Drift line when there is nothing to report — silence is the correct output for a workspace whose files match its tracker.

Goals get no line of their own in this brief, ever. When Phase 1.5 stayed silent ... the normal case ... **nothing about goals appears anywhere in this output.** When Phase 1.5 fired, its single line rides inside `Blockers` and nowhere else.)

End your turn. Wait for direction before starting work.

---

## When to skip phases

- **Pure document workspace** (no servers, no MCP) → skip Phase 3 entirely
- **Continuing a session in the same window** (no break) → skip session-start, just continue
- **Brand-new empty workspace** → run `/super-setup` instead of session-start

---

## Common failure patterns to check

If today's work touches any of these, verify before building:

- **Stale references:** Use the Grep tool to search `.claude/rules/overrides.md`, handoff.md, Checkpoint.md top entry for path strings; verify each path exists via Glob (Cowork) or `test -f` (Code).
- **Drift between Checkpoint.md and reality:** "Service X running" claims that don't match actual state
- **Context bloat:** large directories advertised in system prompts (skills/, memory/ inside agent workspaces)
- **Credential expiry:** API keys, tokens that may have rotated
