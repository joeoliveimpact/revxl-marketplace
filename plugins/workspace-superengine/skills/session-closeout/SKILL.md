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
3. Sync this session's work, sourced from the Checkpoint entry you just wrote. Scope by the `linear:` block:
   - **Default (project-scoped):** sync to the configured `project`.
   - **`scope: team`** (no single `project` — workspace spans multiple): pick the right project under the `team` based on what was worked on (e.g. a Client Work hub → the specific `Clients/<name>` project). If no matching project exists yet, create it under the team, then sync.
   - Work **started** this session → create issues (or move existing) to **In Progress**.
   - Work **completed** → move matching issues to **Done** (create + close if none existed).
   - **Search first** — never duplicate an issue that already exists.
4. Keep it coarse: one issue per meaningful unit of work, NOT per file touched.
5. Record the issue IDs touched in the Checkpoint entry (so the sync is auditable).

**Cowork:** same rule — sync if the MCP is connected; otherwise advisory (note the intended sync, don't probe-fail).

---

## Phase 2.7: Goals ... light check every time, deferred elicitation when it's owed

Two things live here. The **light check (2.7a)** runs every closeout and is silent unless something is genuinely wrong. The **heavy pass (2.7b)** runs only when goals are owed, and it is obligated ... it is the promise `/super-setup` made on the user's behalf when it parked the question.

Runs after Phase 1 on purpose: the Checkpoint entry you just wrote is the evidence this phase reasons from.

Read `.claude/workspace.yml` (the `goals:` block, if it has one) and `GOALS.md`.

### 2.7a ... Light check (silent when clean)

**Default outcome is silence.** Do not say "goals look fine", do not add a reassurance line, do not add a row anywhere in the Phase 5 table. Speak only if one of these is true:

1. **A deferred marker is present** ... first, if `goals.status: declined`, this item is **FALSE** and you skip it regardless of what else you see. Otherwise: `goals.status: deferred`, OR a `GOALS DEFERRED` banner in `GOALS.md`. Either one on its own counts; they are deliberately redundant so a lost config or a hand-edit can't erase the debt. → run the heavy pass (2.7b). Do not merely mention it. Closeout is where this gets paid.
2. **Goals are blank or placeholder** ... first, if `goals.status: declined`, this item is **FALSE** and you skip it no matter what the file looks like. Otherwise: `## Primary purpose` empty or still `{{PURPOSE}}`, or `## Success criteria` holding nothing but the shipped placeholder rows (the ones ending in the literal `…` ellipsis). → run the heavy pass too. Same debt, it just never got marked.
3. **Today's work contradicts the stated goals** ... first, if `goals.status: declined`, this item is **FALSE** and you skip it. Otherwise: the session's real work sits plainly outside `## Primary purpose`, or lands squarely on something listed under `## Non-goals`. Use the Checkpoint entry you just wrote as the evidence, not a hunch. Emit one line, phrased as a question, and change nothing on your own:

   > Today was mostly `<what you actually did>`, and `GOALS.md` says this workspace is for `<purpose>` / lists `<non-goal>` as a non-goal. Has the goal moved, or was today a one-off?

   A one-off answer means no edit at all. If they say the goal moved, update `GOALS.md` in Phase 3 and stamp the change per 2.7c.

**Legacy workspaces with no `goals:` block:** the missing block is not itself a problem. Judge on `GOALS.md` content alone. Real content and no contradiction → silent, and don't add the block. **That "don't add" is narrow: don't write config just to record that a workspace is fine.** It never blocks creating the block when there is a real state to persist ... 2.7b Step 5 creates it on a decline, and 2.7d clears it on a reopen. Both of those are states that have to survive the session.

**`goals.status: declined` beats everything else in 2.7a.** It means the user explicitly asked to be left alone about this. Treat the workspace as clean, stay silent, permanently, and **never run the heavy pass on a declined workspace.** That is why the short-circuit is written into all three items above instead of sitting down here as a note ... an item you have to remember to correct afterwards is an item somebody evaluates wrong, and here a wrong read means firing a full elicitation block at a user who just asked you to stop. That is the exact failure this feature exists to prevent, walking back in through the decline door.

**Precedence, for the one case where the two markers disagree:** `goals.status: declined` AND a `GOALS DEFERRED` banner both present → **`declined` wins.** The banner is leftover from before the user declined; their "stop asking" is the newer signal and a direct instruction. Stay silent, and while you are here, delete the stale banner from `GOALS.md`. It contradicts an explicit instruction, and leaving it there invites the next session to misread it as a live debt.

**Never raise that deletion conversationally** ... don't mention it in prose, don't ask about it, don't use it as a doorway back into the goals topic. Account for it in exactly one place, the Phase 5 handoff table, as:

```
| GOALS.md | UPDATED | stale deferred banner removed |
```

That keeps the file accounting honest ... Phase 5 requires a row with an action and a reason, and printing `NO CHANGE` there would simply be false ... without reopening the conversation the user closed. It is the only edit a declined workspace ever gets from this phase.

None of the three true → **emit nothing** and go to Phase 3.

### 2.7b ... The heavy pass (deferred elicitation)

Runs on the **first closeout after a deferred setup**, and on every closeout after that until the debt clears or the user declines. By now the user has actually worked in this workspace, which is the entire point: they can answer now, and they genuinely could not at setup.

**Step 1 ... build candidates from evidence, not imagination.**

Read what actually happened today, in this order:
- the Checkpoint entry you wrote in Phase 1 (Completed, Decisions, Discoveries, Failed attempts, Files touched)
- the `P0` items you're about to write into `handoff.md`
- corrections or pushback the user gave you this session
- which skills and tools got used

**Step 2 ... propose NAMED items. Never ask an open question.**

This is the rule the whole feature turns on. "What are your goals?" is the original bug: it's the question the user couldn't answer at setup and still can't answer cold. Propose **3 to 6 specific, named candidates** drawn from Step 1 and let them pick. Someone who can't invent a goal from a blank page can absolutely say "yes, that one" or "no, not that."

Route each candidate to a destination **before** you show it, using the house rules that already exist:

| What the item is | Where it goes |
|---|---|
| A durable constraint ... a rule that should bind every future session | `RULES.md` |
| A fact about the user or the project ... true regardless of what you work on next | `MEMORY.md`, as a dated bullet under the right bucket. A long write-up gets its own file under `memory/` plus an index line in `MEMORY.md`, per MEMORY.md's own "long write-ups go in their own files; link them from here" instruction. |
| An outcome or objective ... something you could check later and say yes or no to | `GOALS.md` |

Show them in one block, numbered, destination visible, so accepting costs one word:

```
Now that you've actually worked in here, I can take a real swing at your goals.
Here's what today suggests. Yes or no to each ... "no" costs nothing.

  1. GOAL  → GOALS.md
     "Every client call has a written summary in output/ within 24 hours."
     (why: you did three of these today and asked me to standardize the format)

  2. RULE  → RULES.md
     "Nothing goes out to a client without you seeing it first."
     (why: you stopped me twice today right before a send)

  3. FACT  → MEMORY.md, tools-and-access bucket
     "Client records live in GoHighLevel. The CRM is the source of truth, not the spreadsheet."
     (why: came up when we went looking for the contact list)

Yes to all, or just pick numbers ... "1 and 3" is a perfectly good answer.
```

**Step 3 ... per-item accept, then write only what was accepted.**

- **Never auto-write.** Nothing on that list lands anywhere until the user says yes to that specific item.
- **Per item, not all-or-nothing.** "1 and 3" means item 2 is dropped and not re-proposed this session.
- `RULES.md` is normally never edited (Phase 3's table says exactly that). An explicitly accepted rule from this pass is the one exception, because the user just said it out loud. Append it under a `## Workspace-specific rules` heading at the bottom. **Never touch the four override constraints.**
- Stamp every accepted item per 2.7c before writing it.

**Step 4 ... clear the marker, in this order.**

Only once at least one accepted **goal** has actually landed in `GOALS.md`:

1. Write the accepted goal(s) into `GOALS.md`, replacing the placeholder criterion rows.
2. Delete the `GOALS DEFERRED` banner from `GOALS.md`.
3. Set `goals.status: set` and `deferred_on: ""` in `.claude/workspace.yml`.

Accepted rules or facts alone do **not** clear the marker. The marker is about goals; only a goal landing in `GOALS.md` pays that debt.

**Step 5 ... the failure branches. Each one has something readable to say.**

- **User rejects every candidate:** nothing is written and the marker stays exactly as it is.
  > No problem, nothing written. I'll take another swing next closeout with fresh evidence.
- **User says stop asking:** honor it immediately, and leave `GOALS.md` looking like a deliberate end point rather than an unfinished template. All four steps, in order, none optional:

  1. Set `goals.status: declined` in `.claude/workspace.yml`. **If the workspace has no `goals:` block at all** ... anything scaffolded before this check existed, which is most workspaces ... **create the block now** with `status: declined` and `deferred_on: ""`. The "don't add the block" notes elsewhere in this phase are about clean workspaces that have nothing worth recording. A decline is a real state, and if it does not get written down the next closeout has no idea it happened and asks all over again.
  2. Remove the `GOALS DEFERRED` banner from `GOALS.md`, if one is there.
  3. **Delete the placeholder criterion rows** under `## Success criteria` (the shipped rows ending in the literal `…` ellipsis) and write this in their place, with today's date:

     ```markdown
     _Success criteria intentionally left unset. The workspace owner asked not to be prompted for these on YYYY-MM-DD. Say "let's set goals" to reopen._
     ```

     **Step 3 is the one that gets skipped, and skipping it breaks the whole decline.** Leave those placeholder rows sitting there and the workspace still looks blank-and-unfinished to every future light check ... which is precisely the trigger the user just asked you to stop pulling. Deleting them is what makes "they decided not to" readable as different from "nobody has got to this yet."
  4. Say one line:
     > Got it, I'll leave goals alone. Say "let's set goals" whenever you want to pick it back up.

  `declined` reads as clean to the light check in both skills, so nothing brings this up again on its own.
- **Session too thin to derive anything honestly** (ten minutes, nothing really done): do not manufacture filler candidates. One line, marker stays:
  > Not enough happened today for me to guess at your goals honestly. I'll leave the marker and try again after a real working session.
- **`GOALS.md` is missing entirely:** the workspace isn't fully scaffolded. Say so, point at `/super-setup`, keep the marker, and do not create the file from here.

### 2.7c ... Provenance stamp on everything this pass writes

Anything written by 2.7b carries where it came from and how much evidence sits behind it. **Three facts, every time: which session it came from, `source_count`, and `provisional`.** The last two are the `brand-brain` skill's own fields, reused with its threshold: `source_count` counts **independent observations**, and `provisional: true` whenever `source_count` is under 3.

The two shapes below carry the same three facts. Only the syntax differs, because one destination has frontmatter to put them in and the other does not.

One session of evidence is `source_count: 1`, so a first-pass item is always provisional. That's honest, not weak ... it tells the next session this was inferred from a single day, not established.

- **Destination is a file with frontmatter** (a `memory/<slug>.md` write-up) ... put all three in the frontmatter, brand-brain's shape:

  ```yaml
  ---
  inferred_from_session: 2026-08-13
  source_count: 1
  provisional: true
  ---
  ```

- **Destination is a bullet or a checkbox** (`GOALS.md`, `RULES.md`, a `MEMORY.md` line) ... carry the same three inline at the end of the line:

  ```markdown
  - [ ] Every client call has a written summary in output/ within 24 hours. _(inferred from session 2026-08-13 · source_count: 1 · provisional: true)_
  ```

**Promotion, one rule, no machinery:** when a later session observes the same thing again, bump `source_count` on that line and re-date the stamp. At `source_count: 3`, drop `provisional` ... that's brand-brain's threshold, reused as-is. Do not build a refresh job for this; it happens on touch or it doesn't happen.

### 2.7d ... Reopening after a decline

`declined` is a state the user can leave. This section is the exit, and it is the thing the end-state line in their `GOALS.md` promises them ("Say 'let's set goals' to reopen").

**Trigger:** the workspace has `goals.status: declined`, and the user asks to set goals. That is the literal phrase from the end-state line, or any plain equivalent ... "let's do goals", "I want to set success criteria", "can we revisit the goals". **The user has to ask. Nothing here fires on its own**, which is the whole point of having honored the decline in the first place.

**Do this, in order:**

1. In `.claude/workspace.yml`, set `goals.status: unset` and `deferred_on: ""`.
2. In `GOALS.md`, delete the `_Success criteria intentionally left unset..._` end-state line.
3. Run the heavy pass (2.7b) right now, using this session's evidence. It behaves exactly as it does after a deferred setup ... named candidates, per-item accept, provenance stamps.
4. If this session has no real work to build candidates from, don't manufacture filler. Use 2.7b Step 5's thin-session wording and set `goals.status: deferred` with today's date so the next closeout picks it up with better evidence.

**Why clearing the status matters beyond the goals themselves:** `declined` short-circuits all three items in 2.7a, including item 3, the drift check. So a declined workspace is not being checked for goal drift at all. Clearing it back to `unset` turns that back on, which means a user who reopens and then writes real goals starts getting drift-checked against them again. One mechanism closes both halves.

**If you are reading the promise in a user's `GOALS.md` and this section does not exist in your copy of the skill**, say that plainly to the user rather than improvising a reopen. A wrong guess at their config is worse than an honest "your plugin version is older than that note."

**Both environments:** all of Phase 2.7 is conversation plus Read / Edit / Write. There is no Bash anywhere in it, so Claude Code and Cowork behave identically here.

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
6. Phase 2.7 ran? If a deferred marker was present, it was either **honored** (heavy pass ran, items proposed) or **explicitly declined by the user**. A closeout that leaves a deferred marker sitting there without saying a word is a defect. If the workspace was clean, 2.7 correctly produced no output and there is nothing to report here.

If any row shows `?` — fix it before reporting complete.

---

## Quick mode (for short sessions)

If the session was under 30 minutes and touched <3 files, you can:
- Skip Phase 0, Phase 3, Phase 4
- Write a 3-line Checkpoint.md entry
- Update handoff.md if anything blocks the next session

**Phase 2.7 is never skipped, not even in quick mode.** The light check costs two file reads and produces nothing when the workspace is clean. And the first closeout after a fresh setup is exactly the one most likely to be short ... skipping it there is how parked goals never get asked about at all. If the session really was too thin to build candidates from, 2.7b's thin-session branch already handles that: it says one line and keeps the marker.

Don't quick-mode a session that touched architecture, made decisions, or hit failures.
Those need the full procedure.
