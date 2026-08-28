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

## Phase 0.7: Write the session summary (5 min)

**Runs before Phase 1 on purpose.** Phase 1's Checkpoint entry points at this file by name, and Phase 2's handoff wiki-links it. Write the thing before you write the two pointers to it, or both pointers are guesses.

One file per session. It is the expansion of the terse Checkpoint burst, and it is the file `/session-continue` reads back when it builds the next session's kickoff prompt. Full format reference: `docs/session-summary-format.md` in this plugin.

### Step 1 ... pick the path

`sessions/session-summary-MM-DD-YY.md` at the workspace root.

- **Create `sessions/` if it does not exist.** Most workspaces were scaffolded before this existed, so a missing folder is normal, not an error.
- **Collisions get a numeric suffix**, in order: `session-summary-08-14-26.md`, then `-1`, then `-2`. Check with Glob before writing. Never overwrite an existing summary ... a second session on the same day is a second file.
- **Every pointer written later carries the suffix you actually used.** Phase 1's `**Summary:**` handle and Phase 2's `## Session summary` block both show `session-summary-MM-DD-YY` as a placeholder, not a literal. On a second same-day session the file is `-1` and so is every pointer at it. A pointer at the un-suffixed name is the handle-pointing-at-nothing failure this phase exists to avoid, self-inflicted.

### Step 2 ... write the file

Write it yourself, here, in this context. Everything the summary needs ... what was built, why, what it cost, what broke, what is unfinished ... is already in this conversation, and reconstructing it from file timestamps somewhere else would get it wrong in ways nobody catches.

The file to be written, exactly this shape:

```markdown
---
id: session-summary-MM-DD-YY
tags: [session, episodic, <workspace-slug>]
date_created: YYYY-MM-DD
date_updated: YYYY-MM-DD
source: workspace-canonical
sot_policy: decay
source_count: 1
confidence: 0.8
---

# Session summary ... YYYY-MM-DD

## [YYYY-MM-DD] <topic ... what this section is actually about>

<The expansion. What was built or decided, why, what it cost, what broke. This is the
body that used to bloat the Checkpoint entry.>

## [YYYY-MM-DD] <second topic>

<...>

## [YYYY-MM-DD] Open threads for next session

<What is unfinished, and what the next session needs to know to pick it up.>

## Connections

- `depends_on` ... [[<thing this session's work needs>]]
- `consumes` ... <file or artifact this work reads>
- `integrates_with` ... <system it touches>
```

**Four rules, and each one is load-bearing:**

1. **`sot_policy: decay` is not optional.** It marks the file episodic ... recency-weighted, never deleted, superseded by newer sessions rather than by a status flag. **Episodic and durable never blend.** A durable decision does NOT belong here: a decision meant to bind every future session goes in `RULES.md`, `MEMORY.md` or `GOALS.md`, and must never be marked `decay`.
2. **Every content header is `## [YYYY-MM-DD] <topic>`.** The date is duplicated from the filename on purpose: retrieval chunks at the H2 boundary and reads the header text, not the filename. A summary with undated headers is a summary the graph cannot date.
3. **Headers are topical, never procedural.** `## [2026-08-14] Linear source-of-truth rule` retrieves. `## [2026-08-14] Notes` does not, and neither does `Progress` or `Misc`. If a section covers three unrelated things, it is three sections.
4. **`## Connections` is required, and it is honest about being inert.** On the `/graphify` skill path those lines parse into nothing ... they become an ordinary heading. Their real job is putting the locked verbs (`depends_on consumes exposes integrates_with runs_on references`) in front of the extractor, which otherwise collapses every relationship into `references`. Write it anyway. It costs four lines.

### Step 3 ... wikilinks, with the cost stated correctly

Write `[[wikilinks]]` to related summaries and files. **Structure is free, semantics are paid.**

- On graphify versions that ship the link parser, a free structural pass turns `[[link]]`, `[[link.md]]`, `[text](file.md)` and `[text](./file.md)` into real `references` edges at zero token cost. That pass does **not** run on the `/graphify` skill path, which only hands the extractor the `code` bucket. **Older builds have no link parser at all, so never state the cost for a specific machine without checking it** ... `which graphify` and `graphify --version` first. Full detail: `docs/session-summary-format.md`.
- Keep targets resolvable to a **same-folder sibling, path-relative** where you can ... a link from one summary to another inside `sessions/` qualifies.
- **Links inside fenced code blocks are skipped.** A link that appears only inside a fence produces nothing.

Do not tell the user "edges are free". Do not tell them there are no free edges. The sentence above is the accurate one.

### Step 4 ... the failure branches

- **`sessions/` cannot be created** (permissions, read-only path): say so plainly, write the summary body into the Checkpoint entry instead of a pointer, and do NOT write a handle line pointing at a file that does not exist.

  > I could not create the `sessions/` folder, so today's write-up went into Checkpoint.md in full instead of its own summary file. Nothing was lost ... the entry is just longer than usual.
- **Session was genuinely thin** (ten minutes, one small fix): still write the file. A short summary is fine; a missing one breaks the handle in the Checkpoint entry. One dated H2 and a Connections block is a complete summary.

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
**Summary:** [[session-summary-MM-DD-YY]]
**Terms:** {3 to 5 topic terms, comma separated} (unverified ... no hub yet)
**Session log:** {path to this session's transcript, or how it could not be determined}

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

### `**Session log:**` ... stamp the transcript path, or say you could not

The raw session transcript holds every turn of this session at full fidelity, and it is the one artifact that is *not* a summary of anything. `/session-continue` reads it to recover the reasoning behind a decision, which is precisely what a handoff compresses out. But nothing else on disk records which transcript belongs to which session, so unless this line is written, that link is gone the moment the session ends.

Transcripts live at `~/.claude/projects/<workspace-path-slug>/<session-id>.jsonl`, where the slug is the absolute workspace path with separators replaced by `-`.

**Two ways to identify the file, in order:**

1. **From a session id the environment already exposes.** In Claude Code the scratchpad directory path contains the session id, and the transcript is that id plus `.jsonl`. Verified on Claude Code desktop 08.27.26.
2. **Newest `.jsonl` by modification time** in the project directory, and only when its mtime is within the last few minutes ... a live session's transcript is being appended to right now.

**Then confirm the file exists before writing the path** (Code: `test -f`; Cowork: Glob). Never write a transcript path you did not confirm ... a citation to a file that is not there is worse than no citation, because it reads as though somebody checked.

**If neither method resolves, write what happened instead of a guess:**

```
**Session log:** could not determine (two sessions ran concurrently; newest-by-mtime is unreliable)
```

**Method 2 is unreliable when sessions overlap.** If two are running, the newest transcript may not be this one. Say so on the line rather than stamping a path that might point at somebody else's session.

**Expect these entries to get much shorter than they used to be.** A pre-summary top entry runs about 60 lines. Now the body lives in the Phase 0.7 summary and the entry is a burst plus two pointer lines. **That is the bloat fix working, not information loss** ... the full write-up is one wiki-link away.

### The retrieval header ... two lines, deliberately not one

`**Summary:**` and `**Terms:**` do different jobs and fail differently. That is why they never get merged into a single line.

| Line | What it is | How it behaves |
|---|---|---|
| `**Summary:**` | the **handle** ... the summary file's frontmatter `id`, which is also its filename | Deterministic. It resolves and pulls that one file whole, or the file is missing and you find out immediately. It cannot half-work. |
| `**Terms:**` | **topic terms** ... fuzzy concepts that fan out through hub search and pull the whole neighborhood, including notes written later in other sessions or other workspaces | Can legitimately return nothing. |

Merged onto one line, a term that returns nothing looks like a broken pointer. Split, it reads as a miss, which is all it is.

**Terms carry `(unverified ... no hub yet)` until the hub exists.** Verifying that a term actually resolves needs the hub's term-resolution index, which is not built yet. Writing terms as if they were checked teaches the reader to trust something nobody checked, and the first dead term after that costs the whole header its credibility. **The handle needs no graph at all** ... it is a filename, and it works in a workspace with no hub, no graphify, and no second brain. Once the hub lands, drop the marker on terms you actually resolved.

### The 30-day window ... demote old entries in the same file

Do this every closeout, right after inserting the new entry. **Closeout owns this, not a scheduled job** ... Checkpoint has to work before any graph exists, and the scheduled night job that would otherwise own it does not exist yet.

1. **Full zone (top of the file):** every entry from the last 30 days, newest first, complete with burst, handle and terms.
2. **Floor of 5.** The full zone always keeps at least the 5 newest entries, even when all of them are older than 30 days. A quiet month cannot empty the top of the file.
3. **Tail (below the full zone, same file):** everything else, one line each, newest first:

   ```
   - 2026-07-02 · Linear source-of-truth rule → [[session-summary-07-02-26]] · terms: linear, source of truth
   ```

4. **No second archive artifact.** The tail lives in `Checkpoint.md` under a `## Earlier sessions` heading at the bottom of the file. Do not create an archive file, do not move anything to another folder.
5. **Ordering:** the full zone stays newest-first, then `## Earlier sessions` last, also newest-first. An old entry that cannot be compressed (see below) stays in the full zone, in date order, which means the full zone can run past 30 days. That is intended, not a bug to tidy up.

**Compress ONLY entries that have a resolvable `**Summary:**` handle.** An entry written before session summaries existed has its body in exactly one place, and compressing it to one line destroys the only copy. Those stay full, however old they are, and they do not count against the floor. Converting them is the backfill's job, and **the backfill is blocked until deletions are recoverable** ... do not attempt it here, do not attempt it partially, and do not "just do the top few".

**Say out loud how many entries you retained for having no handle. Every closeout, including ... especially ... when the answer is "all of them."**

A file with no handles anywhere compresses nothing, and a demotion step that compresses nothing and reports nothing looks exactly like bloat control working. It is not working; it is waiting on the backfill. The user has to be able to tell those apart, and the only thing that distinguishes them is this line.

- **Some compressed, some retained:**
  > Compressed 12 older entries to one-liners. Another 9 predate session summaries and have no handle, so I left those in full ... they stay that way until the backfill is unblocked.
- **Nothing compressed, everything retained** ... the case for any workspace that has been running since before this format existed:
  > Nothing could be compressed this time: all 47 entries in `Checkpoint.md` predate session summaries, so none of them has a handle to compress down to. The file will keep growing until the backfill converts them, and the backfill is blocked until deletions are recoverable. From today forward, new entries carry a handle and will compress normally.

**Silence here is a defect, not a clean result.** Report the count even when it is zero in the other direction (nothing retained, everything compressed) ... that is one short line and it is the only evidence the step ran at all.

If demotion would compress an entry whose handle points at a file that is not on disk, leave it full and say so:

> One older Checkpoint entry points at a session summary I could not find, so I left it in full rather than compressing it down to a link that goes nowhere.

---

## Phase 2: Rewrite handoff.md (3 min)

**Both environments:** use the Write tool to replace handoff.md entirely. If file doesn't exist, Write creates it.

handoff.md is **rewritten**, not appended. It represents the live state for the NEXT session.

Template:
```markdown
# Handoff — Next-Session Priorities

## Last session
{date} — {title} (see Checkpoint.md for full entry)

## Session summary
[[session-summary-MM-DD-YY]] · `sessions/session-summary-MM-DD-YY.md`

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

**`## Session summary` carries both forms on purpose.** The wiki-link is what a human clicks and what Obsidian resolves; the path is what survives a tool that does not understand wiki-links. Belt and suspenders, one extra line.

**Five of these headings are load-bearing and must not be renamed, reordered out of existence, or reworded:** `## Last session`, `## Session summary`, `## P0 — Next Actions`, `## Verify before building`, `## Key files from last session`. `/session-continue` reads them by name to build the next session's kickoff prompt. Rename one and that prompt silently loses a field ... it will still generate, it will just be missing the part nobody notices is gone. If a section has nothing in it, write `(none)` under it. Never delete the heading.

---

## Phase 2.5: Sync to Linear (conditional)

Runs **only if** `.claude/workspace.yml` has a `linear:` block with `status: configured`. Otherwise **skip silently**.

Trigger is the **configured flag**, not bare MCP connection (the MCP is shared across all workspaces; the per-workspace `linear:` binding scopes which project to write).

**Name the tools and call them.** This phase describes an outcome; these are the calls that produce it. The Linear MCP may register under an **opaque id** rather than a readable name, so load its tools by exact name (`select:mcp__<server-id>__list_issues,...`) using the `mcp_server_id` pinned in the `linear:` block, or enumerate the deferred-tool list for `list_issues` / `save_issue` / `save_comment` and read the id off those names. A failed keyword search for "linear" is **not** evidence the connector is down.

1. Read the `linear:` block — `team`, `project` (+ ids), and `mcp_server_id` if present.
2. **Connection health-check:** probe with `list_issues`. If configured but the Linear MCP isn't connected → warn one line, skip the sync, and record `Linear sync skipped — MCP not connected` in the Checkpoint entry. **Never fail closeout over Linear.**
3. Sync this session's work, sourced from the Checkpoint entry you just wrote. Scope by the `linear:` block:
   - **Default (project-scoped):** sync to the configured `project`.
   - **`scope: team`** (no single `project` — workspace spans multiple): pick the right project under the `team` based on what was worked on (e.g. a Client Work hub → the specific `Clients/<name>` project). If no matching project exists yet, create it under the team, then sync.
   - **Search first** with `list_issues` — never duplicate an issue that already exists.
   - Work **started** this session → `save_issue` to create, or to move an existing issue to **In Progress**.
   - Work **completed** → `save_issue` to move matching issues to **Done** (create + close if none existed).
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

## Phase 4.5: Commit the Workspace Repo (conditional)

Runs **only if** the workspace root is a git repo. Skip silently otherwise.

Closeout is the commit point. The user should never have to ask for a commit — every scaffold
write from Phases 1–3 is already on disk by now, so one commit here captures the whole session.

**Code environment:**
1. `git -C <workspace> status --short` — if clean, report "nothing to commit" and move on.
2. Review the list before staging. Anything that is **not** session work — stray downloads, large
   caches, files a `.gitignore` should be catching — gets flagged to the user, not committed.
3. `git add -A`, then commit with a message built from the Checkpoint.md entry just written:
   subject = `Session MM.DD.YY: {short title}`, body = the entry's Completed bullets, condensed.
   Write the message to a file and use `git commit -F <file>` — heredocs die on apostrophes on
   Windows, and PowerShell here-string syntax (`@'…'@`) leaks a literal `@` when run under Bash.
4. **Do not push.** A push is outward-facing and needs explicit approval. If the repo has a remote
   and unpushed commits, say so in the Phase 5 report and let the user decide.

**Cowork environment:** advisory — report the `git add -A && git commit` command for the user to run.

---

## Phase 5: Final Verification — Explicit Handoff Table

Report this table to the user. Every applicable file gets a row with action + reason if NO CHANGE.

```
| File              | Action     | Reason (if NO CHANGE) |
|-------------------|------------|-----------------------|
| sessions/session-summary-MM-DD-YY.md | CREATED | — |
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
5. Workspace repo committed (or explicitly clean / not a repo)? Unpushed commits reported?

6. Session summary written, and does the Checkpoint entry's `**Summary:**` handle point at a file that is actually on disk? Check it with Glob or `test -f`, do not assume it. A handle pointing at nothing is worse than no handle, because it looks like it works.
7. Demotion ran, **and said something**? Entries older than 30 days (beyond the newest 5) are one-liners in the tail, EXCEPT pre-summary entries with no handle, which stay full on purpose. The retained count was spoken out loud. A demotion that compressed nothing and reported nothing is a defect, not a pass ... it is indistinguishable from bloat control working when it is actually waiting on the backfill.

If any row shows `?` — fix it before reporting complete.

---

## Quick mode (for short sessions)

If the session was under 30 minutes and touched <3 files, you can:
- Skip Phase 0, Phase 3, Phase 4
- Write a 3-line Checkpoint.md entry
- Keep handoff.md's `## Last session` current ... Phase 2 still runs, see below

**Phase 0.7 is never skipped either, and neither is the demotion step.** The summary can be four lines on a quick session, but it has to exist, because Phase 1 writes a `**Summary:**` handle pointing at it and a handle pointing at nothing is a lie the next session believes. Demotion is a couple of edits and skipping it is how a Checkpoint file quietly grows back to 300 KB.

**Phase 2 is never skipped, even when nothing blocks the next session.** `handoff.md` is rewritten every closeout without exception, because `/session-continue` decides whether a closeout ran **by reading the date under `## Last session`**. A quick mode that leaves that date stale makes a completed closeout look like one that never happened, and continue then runs a second full closeout over the top of it ... two Checkpoint entries, two summary files, one session. If genuinely nothing changed for the next session, rewrite the file anyway and say so in `## Status`. The date is the receipt.

Don't quick-mode a session that touched architecture, made decisions, or hit failures.
Those need the full procedure.
