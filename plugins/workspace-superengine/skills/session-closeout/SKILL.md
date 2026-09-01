---
name: session-closeout
description: Use at the end of a working session to capture state — writes a session summary file, updates Checkpoint.md with a log entry, and rewrites handoff.md with next-session priorities. Trigger phrases include "let's wrap up", "closing out for the day", "session closeout", "save state", "I'm done for now", "/session-closeout", and any signal the user is ending work (e.g. "logging off"). If the user also wants the NEXT session queued up as a one-click chip — "see you tomorrow", "continue this tomorrow", "close out and get the next one ready" — use /session-continue instead, which runs this skill in full and then builds that prompt. Pairs with /session-start.
---

# Session Closeout Procedure

Run at end of every session. No skipping the file updates — those are non-negotiable.

## Compaction guard ... re-invoke this skill if the session compacted

This file is long. After a context compaction the skill body is re-injected **truncated to roughly the first 5,000 tokens, keeping only the start**, so the later phases silently vanish.

**If the session has compacted since you invoked this skill, invoke it again before relying on any phase below.** A phase that appears to be missing is the symptom, not a phase that does not exist.

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

> "Sounds like you're wrapping up — three options: `/session-closeout` to save state, `/session-continue` to save state **and** queue tomorrow's session as a one-click chip, or just stop here without logging. Which?"

Only run the full process below after the user confirms. If the user explicitly invokes `/session-closeout`, skip the suggestion and proceed.

---

## Phase 0: Confirm Override-Constraint Compliance (30s)

Before writing the session log, do a quick self-check against the four override constraints (`.claude/rules/overrides.md`; legacy root `RULES.md` on unmigrated workspaces):
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

1. **`sot_policy: decay` is not optional.** It marks the file episodic ... recency-weighted, never deleted, superseded by newer sessions rather than by a status flag. **Episodic and durable never blend.** A durable decision does NOT belong here: a decision meant to bind every future session goes in `.claude/rules/overrides.md`, `MEMORY.md` or `GOALS.md`, and must never be marked `decay`.
2. **Every content header is `## [YYYY-MM-DD] <topic>`.** The date is duplicated from the filename on purpose: retrieval chunks at the H2 boundary and reads the header text, not the filename. A summary with undated headers is a summary the graph cannot date.
3. **Headers are topical, never procedural.** `## [2026-08-14] Linear source-of-truth rule` retrieves. `## [2026-08-14] Notes` does not, and neither does `Progress` or `Misc`. If a section covers three unrelated things, it is three sections.
4. **`## Connections` is required, and it is honest about being inert.** On the `/graphify` skill path those lines parse into nothing ... they become an ordinary heading. Their real job is putting the locked verbs (`depends_on consumes exposes integrates_with runs_on references`) in front of the extractor, which otherwise collapses every relationship into `references`. Write it anyway. It costs four lines.

### Step 3 ... wikilinks, with the cost stated correctly

Write `[[wikilinks]]` to related summaries and files. **Structure is free, semantics are paid** ... on builds that ship the link parser, a structural pass turns links into real `references` edges at zero token cost, but that pass does not run on the `/graphify` skill path, and links inside fenced code blocks are skipped entirely.

Keep targets resolvable to a same-folder sibling where you can. **Do not tell the user "edges are free", and do not tell them there are no free edges.** Which builds parse what, and how to check: `docs/session-summary-format.md`.

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

The raw transcript is the one artifact that is not a summary of anything, and **nothing else on disk records which transcript belongs to which session** ... so unless this line is written, `/session-continue` cannot find it later.

Identify the file, **confirm it exists before writing the path**, and if you cannot identify it write what happened instead of a guess. How to find it and the exact fallback wording: `${CLAUDE_PLUGIN_ROOT}/references/session-log-stamping.md`.

### The retrieval header ... two lines, deliberately not one

`**Summary:**` is a **handle** ... a filename. It resolves and pulls one file whole, or it is missing and you find out immediately. It cannot half-work, and it needs no graph at all.

`**Terms:**` are **topic terms** ... fuzzy, fanned out through hub search, and they can legitimately return nothing. **They carry `(unverified)` until a term-resolution index exists**, because writing them as if they were checked teaches the reader to trust something nobody checked.

**Never merge the two onto one line.** Merged, a term that returns nothing reads as a broken pointer. Split, it reads as a miss, which is all it is. Full rationale: `docs/session-summary-format.md`.

### The 30-day window ... demote old entries in the same file

**Run this every closeout, right after inserting the new entry.** Entries older than 30 days compress to one-liners in a `## Earlier sessions` tail at the bottom of the same file, the newest 5 always stay full, and **entries with no `**Summary:**` handle are never compressed** ... their body exists in exactly one place and compressing it destroys the only copy.

**Say out loud how many entries you retained for having no handle. Every closeout, including ... especially ... when the answer is "all of them."** A demotion that compressed nothing and reported nothing looks exactly like bloat control working when it is actually waiting on the backfill, and that line is the only thing that tells those apart.

The rules, the ordering, and the exact wording of both spoken reports: `${CLAUDE_PLUGIN_ROOT}/references/checkpoint-demotion.md`.

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
| A durable constraint ... a rule that should bind every future session | `.claude/rules/overrides.md` |
| A fact about the user or the project ... true regardless of what you work on next | `MEMORY.md`, as a dated bullet under the right bucket. A long write-up gets its own file under `memory/` plus an index line in `MEMORY.md`, per MEMORY.md's own "long write-ups go in their own files; link them from here" instruction. |
| An outcome or objective ... something you could check later and say yes or no to | `GOALS.md` |

Show them in one block, numbered, destination visible, so accepting costs one word:

```
Now that you've actually worked in here, I can take a real swing at your goals.
Here's what today suggests. Yes or no to each ... "no" costs nothing.

  1. GOAL  → GOALS.md
     "Every client call has a written summary in output/ within 24 hours."
     (why: you did three of these today and asked me to standardize the format)

  2. RULE  → .claude/rules/overrides.md
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
- `.claude/rules/overrides.md` is normally never edited (Phase 3's table says exactly that). An explicitly accepted rule from this pass is the one exception, because the user just said it out loud. Append it under a `## Workspace-specific rules` heading at the bottom. **Never touch the four override constraints.**
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

- **Destination is a bullet or a checkbox** (`GOALS.md`, `.claude/rules/overrides.md`, a `MEMORY.md` line) ... carry the same three inline at the end of the line:

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
| .claude/rules/overrides.md | NEVER edit unless user explicitly asks — these are the override constraints |
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

## Phase 4.2: Close background processes this session started

Sessions leak background processes. A dev server, a watcher, a script left running behind a `&`. They sit there eating memory for days, and on a coach's laptop nobody ever notices or knows what to do about it.

**The reason this needs a ledger, and cannot be done by looking at what is running:** the process table cannot tell you what is an orphan.

- **Parent lies.** MCP servers start through `npx`, so their parent is `cmd.exe`, not Claude. Filtering on "no live Claude parent" flagged roughly thirty MCP servers that were actively in use.
- **Name lies, and this one is dangerous.** Claude Code IS node. Stopping processes named `node` kills the session running the command, plus every other Claude window that is open.
- **Age lies.** A three-day-old server can be in daily use. A ten-minute-old one can belong to another window that is open right now.

So the plugin records a process at the moment a Bash command starts it, and closes from that record. **The process table is only ever used to VERIFY a record, never to pick a target. Anything not in the ledger is reported, never stopped.**

### `environment: cowork`

**Say this plainly and move on. Do not improvise around it:**

> Cowork has no Bash, so I cannot see or stop background processes from here. That part of closeout only runs in Claude Code. If you have had Claude Code sessions in this workspace, run `/session-closeout` there when you get a chance.

Do not report this phase as clean, done, or skipped-because-nothing-found. It is skipped because the capability is absent. Those are different things and the user needs the real one.

### `environment: code`

**Step 1 ... find the ledger tool.** In order:

1. `"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" process-ledger list`
2. If that produces **no output at all**, read `~/.claude/workspace-superengine/process-ledger/cli-path.txt` and run `bash "<the path in that file>" list`.
3. If neither works, say so out loud:

   > I could not reach the background process tool, so I do not know whether this session left anything running. That is not the same as "nothing is running."

   **Empty output is never evidence of a clean machine.** The wrapper exits quietly when it cannot find bash, which looks exactly like "no processes found" if you are not careful. The real "nothing here" answer is a report that says so in words, which the tool prints when the ledger is genuinely empty.

**Step 1b ... read the first three lines before you read anything else.**

- If the output starts with `PROCESS LEDGER UNAVAILABLE`, that is the whole answer. Tell the user the check could not run and why, in the tool's own words. **Do not report the phase as clean.** "I could not check" and "nothing is running" are different facts.
- Check the `Workspace:` line actually names this workspace. If it names a parent, a subfolder, or something unexpected, say so ... the answer below it is about a different workspace.
- The `Resolved by:` line underneath says how it worked that out (`CLAUDE_PROJECT_DIR`, or which marker file it found walking up). When the `Workspace:` line looks wrong, that line is what tells you why, so quote it rather than guessing.

You may also see a line reporting processes **refused as machinery** at recording time. That is a count of things the tool declined to write down at all, such as Claude's own shells. It is informational and needs no action.

**Step 2 ... show the user what it printed.** Show the list itself, not a summary of it. Each entry carries the command, when it was recorded, how much memory it is using right now, and one of five states:

| State | What it means | What you may do |
|---|---|---|
| `STOPPABLE` | identity verified, and either this Claude instance started it or the session that did has ended | may be offered to the user |
| `OTHER-WINDOW` | identity verified, but another Claude window that is still open owns it | report only, never offer |
| `MISMATCH` | that pid is running something different from what was recorded | report only, never offer, and never "force" it |
| `MACHINERY` | identity verified, and it is Claude's own plumbing (the shell commands run in, a console host, this plugin's own hooks) | report only, never offer, never stop |
| `GONE` | it already exited; the entry is closed automatically | nothing to do |

**`MACHINERY` is the tool working, not a problem.** It means the ledger checked the entry, found it accurate, and refused it anyway because stopping it would kill the shell every command runs in, or Claude itself. It never enters the consent list and it is never counted in `STOPPABLE`. Do not escalate it, do not offer it, and do not go looking for another way to stop it. If the user asks what it is, that one sentence is the whole answer.

**Step 3 ... ask, with the cost visible.** Name the specific processes and what stopping them costs. Never ask a blanket "shall I clean up background processes?"

> These two are still running from this session: a dev server on port 3000 (180 MB) and a file watcher (40 MB). Stop them?

**Step 4 ... stop only what they said yes to.**

```
"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" process-ledger stop --token <token from the list> --pids <only the pids they approved>
```

The token ties the approval to that exact list. If anything changed between the list and the stop, the tool refuses the whole batch and tells you to ask again. That refusal is correct behavior, not an error to work around.

The tool re-verifies every process immediately before stopping it and skips any that no longer match. **A skip is a success, not a failure.** Report skips to the user in the tool's own words. Do not retry them, do not look up the pid another way, and never reach for `Stop-Process`, `taskkill`, `kill`, or `pkill` yourself to finish the job. That is the exact move that kills the harness.

**Step 5 ... report the outcome, including the boring one.** "Nothing was left running this session" is a real result and gets said out loud. Silence here reads as "the check was skipped."

**If the user asks you to stop something that is not in the ledger:** decline and explain. The plugin can only prove ownership of what it recorded. Offer the command so they can run it themselves with their own eyes on it.

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
| .claude/rules/overrides.md | ?  | NO CHANGE almost always; UPDATED only via 2.7b's accepted-rule exception |
```

Also confirm:
1. Checkpoint.md entry is self-contained for someone who wasn't in this session?
2. handoff.md P0 list is actionable (not vague)?
3. Any background tasks have verify commands documented?
4. Any durable user/feedback/project learnings saved to memory?
5. Workspace repo committed (or explicitly clean / not a repo)? Unpushed commits reported?
6. Phase 4.2 ran and produced a spoken result? In Claude Code that is either a list the user answered, or "nothing was left running." In Cowork it is the plain "I cannot do this from here." A closeout that says nothing at all about background processes is a defect.
7. Phase 2.7 ran? If a deferred marker was present, it was either **honored** (heavy pass ran, items proposed) or **explicitly declined by the user**. A closeout that leaves a deferred marker sitting there without saying a word is a defect. If the workspace was clean, 2.7 correctly produced no output and there is nothing to report here.

8. Session summary written, and does the Checkpoint entry's `**Summary:**` handle point at a file that is actually on disk? Check it with Glob or `test -f`, do not assume it. A handle pointing at nothing is worse than no handle, because it looks like it works.
9. Demotion ran, **and said something**? Entries older than 30 days (beyond the newest 5) are one-liners in the tail, EXCEPT pre-summary entries with no handle, which stay full on purpose. The retained count was spoken out loud. A demotion that compressed nothing and reported nothing is a defect, not a pass ... it is indistinguishable from bloat control working when it is actually waiting on the backfill.

If any row shows `?` — fix it before reporting complete.

---

## Quick mode (for short sessions)

If the session was under 30 minutes and touched <3 files, you can:
- Skip Phase 0, Phase 3, Phase 4 (the live-infrastructure snapshot) ... **Phase 4.2 is not part of that skip**
- Write a 3-line Checkpoint.md entry
- Keep handoff.md's `## Last session` current ... Phase 2 still runs, see below

**Phase 0.7 is never skipped either, and neither is the demotion step.** The summary can be four lines on a quick session, but it has to exist, because Phase 1 writes a `**Summary:**` handle pointing at it and a handle pointing at nothing is a lie the next session believes. Demotion is a couple of edits and skipping it is how a Checkpoint file quietly grows back to 300 KB.

**Phase 2 is never skipped, even when nothing blocks the next session.** `handoff.md` is rewritten every closeout without exception, because `/session-continue` decides whether a closeout ran **by reading the date under `## Last session`**. A quick mode that leaves that date stale makes a completed closeout look like one that never happened, and continue then runs a second full closeout over the top of it ... two Checkpoint entries, two summary files, one session. If genuinely nothing changed for the next session, rewrite the file anyway and say so in `## Status`. The date is the receipt.

**Phase 2.7 is never skipped, not even in quick mode.** The light check costs two file reads and produces nothing when the workspace is clean. And the first closeout after a fresh setup is exactly the one most likely to be short ... skipping it there is how parked goals never get asked about at all. If the session really was too thin to build candidates from, 2.7b's thin-session branch already handles that: it says one line and keeps the marker.

**Phase 4.2 is never skipped either.** It is one command, and it says nothing at all when the ledger is empty. The short casual session is exactly the one where somebody fires up a dev server, gets distracted, and closes the window ... so skipping it there skips it in the case it was built for.

Don't quick-mode a session that touched architecture, made decisions, or hit failures.
Those need the full procedure.
