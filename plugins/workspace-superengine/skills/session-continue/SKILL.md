---
name: session-continue
description: Use at the very end of a working session when the user wants the NEXT session teed up, not just logged ... runs the full /session-closeout, then auto-builds a kickoff prompt from the files closeout just wrote and spawns it as a task chip the user clicks once to start fresh with inherited context. Trigger phrases include "/session-continue", "wrap up and set up tomorrow", "close out and queue the next session", "I'm done, get the next one ready", "hand this off to a fresh session", "continue this tomorrow", "start a new session with this context", and any wrap-up request that also asks for the next session to be prepared. If the user only wants state saved with no follow-on session, use /session-closeout instead.
---

# Session Continue ... close out, then tee up the next session

One command at the end of a session. It does two things in order:

1. Runs `/session-closeout` in full, unchanged.
2. Builds the next session's kickoff prompt **from the files closeout just wrote** and spawns it as a task chip. The user clicks once and a fresh session starts with the context already loaded.

**The point is zero hand-authoring.** Nobody writes a kickoff prompt by hand, and nobody re-explains yesterday to a fresh Claude.

## Runtime environment

Read `.claude/workspace.yml#environment` on entry.

- **`environment: code`** ... Bash available for the git check in Step 2c.
- **`environment: cowork`** ... no Bash. Use Glob for the `.git` check, and treat the credential checks as advisory. Everything else is identical.

Default to cowork-safe behavior if the config is missing.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit this before doing any work. If `standard` or missing, skip it and proceed silently.

> I'll do the normal wrap-up first ... session summary, checkpoint, handoff. Then I'll write the opening message for your next session and put it on a button. Tomorrow you click it once and the new Claude already knows where we left off. About three minutes.

## Layer 2: Suggest before invoking

If the user's wrap-up request is borderline ... could be a plain closeout, could be a closeout plus a queued next session ... ask before firing:

> "Want the plain wrap-up (`/session-closeout`), or wrap up **and** queue tomorrow's session as a one-click chip (`/session-continue`)?"

If the user explicitly invokes `/session-continue`, skip the suggestion and proceed.

---

## Step 1: Run `/session-closeout`, in full, unchanged

Invoke `/session-closeout` and let it run its whole procedure. **Do not reimplement any of it here, do not skip phases to save time, and do not quick-mode it on this skill's behalf.** Closeout owns the session summary (Phase 0.7), the Checkpoint entry (Phase 1) and the handoff rewrite (Phase 2). This skill's entire input is what those three phases put on disk.

**If closeout does not complete** ... the user aborts it, a write fails, they say "skip the closeout, just make the chip" ... do not silently continue as if it ran. Go to Step 4's degraded branch. A kickoff prompt built on a stale handoff is the failure this skill exists to prevent, wearing the costume of the thing working.

---

## Step 2: Build the kickoff prompt FROM THE FILES ON DISK

### 2a ... re-read, do not remember

**Re-read the files with the Read tool, even though you just wrote them this session.** Do not build any part of the prompt from what you remember of the conversation.

Read, in this order:

1. `handoff.md` (the version closeout just wrote)
2. `sessions/session-summary-MM-DD-YY.md` (the path from handoff's `## Session summary`)
3. `Checkpoint.md`, top entry only
4. `.claude/workspace.yml` (environment, verbosity, and any `linear:` block)

**Then check every file the read order is about to cite.** For each path in `## Key files from last session`, and for the session summary itself, get its size (Code: `wc -c`; Cowork: Read it and look). Three outcomes:

- **Missing** ... no file at that path.
- **Stub** ... it exists but holds **under 200 bytes, or fewer than 3 non-empty lines**. That threshold is written down rather than judged so the check cannot drift: a file a next session is told to *read for context* is a paragraph at minimum, and one sentence is a placeholder somebody meant to come back to.
- **Real** ... anything else. Cite it normally.

**Never repeat the handoff's description of a file as though it were true when the file does not back it up.** `handoff.md` describes intent, not disk. A handoff line saying "the field map, rows 1 to 11 done" against a 35-byte file is exactly the failure this whole skill is built to prevent: correctly cited, verbatim faithful, and useless. Keep the description, and mark it against what is actually there ... see the Read order row in 2b for the wording.

**This is not bureaucracy, it is the whole design.** A prompt built from chat memory is a summary of a summary ... it inherits everything this session got wrong, drifted on, or half-decided, and it inherits it invisibly. A prompt built from disk is exactly as good as the handoff, which is a thing the user can read and correct. If a field is not in the files, it does not go in the prompt. **Ever.** If you find yourself supplying a detail from memory because "the handoff didn't quite capture it", stop ... the correct fix is to say so and offer to add it to `handoff.md` first, then rebuild.

### 2b ... the field map

Six fields. Each row says where it comes from and what happens when the source is missing. **A missing source never produces an invented value ... it produces a named gap that appears in the prompt itself.**

| Field | Source | If the source is missing or empty |
|---|---|---|
| **Mission** | `handoff.md` → `## P0 — Next Actions`, **item 1**, verbatim. Plus the `## Last session` line for one sentence of context. | **Do not fabricate a mission.** Write `MISSION NOT SET ... handoff.md has no P0 items.` and set the thin flag. The chip still spawns; it just says out loud that nobody decided what to do next. |
| **Deliverable** | The outcome named inside P0 item 1 ... the file, artifact, decision or state it produces. If P0 item 1 names a path or an artifact, quote it. | If P0 item 1 names no outcome, write `Deliverable not stated in handoff. Agree what "done" looks like before building.` and set the thin flag. Do not guess the artifact. |
| **Read order** | The session-summary path first, then `handoff.md` → `## Key files from last session` in the order listed, each with its note. Every entry carries the 2a disk check. | Missing section → read order is the session summary alone, plus the line `handoff.md listed no key files.` Missing summary too → say `No session summary on disk` and set the thin flag. **Per entry, from the 2a check:** a **missing** file gets `**MISSING from disk.**` appended to its line; a **stub** gets `**UNVERIFIED ... the file on disk is <N> bytes, a stub, not what this describes. Check before building on it.**` Keep the handoff's description in both cases and put the mark right after it, in the read-order entry itself. Never in a footnote, never only in the thin block ... a reader skimming a numbered list has to hit it without looking anywhere else. |
| **Step-0 batch** | Any item under `## P0 — Next Actions` or `## P1 — Deferred` that is phrased as a **decision** or carries the words **confirm** or **resolve**. Also anything in `## Blockers` that needs an answer rather than an action. | None found → `No open decisions. Go straight to the mission.` That is a real, good answer and it does NOT set the thin flag. **Unless the Mission is also not set** ... then write `No open decisions were recorded either.` Pointing a reader at a mission that does not exist is the kind of small wrongness that makes a whole prompt read as auto-generated slop. |
| **Hard rails** | `handoff.md` → `## Verify before building`, **verbatim**. Copy the lines exactly, including any commands. Do not paraphrase, do not reorder, do not "clean up". | Section missing or `(none)` → `No pre-build checks were recorded.` and set the thin flag. Rails are the highest-cost field to lose, because their absence looks identical to "nothing to check". |
| **Skills** | `/session-start` always first. Then whichever mode the P0 names ... if P0 item 1 says "build", "plan", "verify", "clean up", map it to the matching workspace skill (`/workspace-plan`, `/workspace-verify`, `/workspace-cleanup`, and so on). | P0 names no mode → list `/session-start` alone. Do not invent a second skill to make the list look fuller. |

**Verbatim means verbatim.** For Hard rails especially: retype nothing, summarize nothing. If a rail says `check the Tailscale link is up before hitting the rig`, that exact sentence goes in the prompt.

### 2c ... route detection, stated and never guessed

The chip's click is where the user picks **local**, **worktree**, or **cloud**, and the UI default is **Start with worktree**, which is wrong for most workspaces. A skill cannot change that default, so the prompt has to carry the instruction to where the user will actually read it.

Run both checks and write a `Route:` line stating what you found. **Run both even when the first one already rules something out** ... they are independent reasons, and if both fire, both go in the line. Dropping the second because the first already forced "local" loses the reason a reader needs when they later move this workspace into a repo.

1. **Is the workspace root a git repo?**
   - Code: `git -C "<workspace root>" rev-parse --git-dir`
   - Cowork: Glob for `.git` at the workspace root.
   - **Not a repo** → `Route: this workspace is not a git repo, so "Start with worktree" will not work. Choose **Start locally**.`
2. **Does the mission need something only this machine has?** Scan the Mission, Deliverable and Hard rails text for: absolute local paths (`C:\...`, `/home/...`, `~/...`), SSH or SSH keys, a Tailscale hostname or tailnet IP, `localhost`, a locally-installed CLI, a local `.env` or credential file, or a local MCP server.
   - **Found** → `Route: cloud will not work for this one ... <the specific thing>. Choose **Start locally**.` Name the thing. "Needs local access" is not a reason, `sessions/` is on this machine and the rig is only reachable over the tailnet is a reason.
3. **Both clean** (real git repo, nothing machine-bound) → `Route: local or worktree both work. Worktree keeps this branch isolated.`

**If a check could not run** ... no Bash and Glob was inconclusive ... say that, in place, rather than defaulting to a guess:

> `Route: I could not confirm whether this folder is a git repo, so I can't tell you whether worktree will work. Start locally if you're unsure.`

### 2d ... the thin flag, and why it is loud

**The failure mode this skill has to defend against is a prompt that generates *something* rather than the *right* thing.** A chip full of plausible-looking filler passes every naive check ... it has all the headings, it reads fine, and it sends the next session off in a direction nobody chose. Silence is what makes that dangerous, so thinness gets announced twice: once to the user right now, and once inside the prompt where the next session will read it cold.

**A read order pointing at stubs is thin, even when every handoff section was present.** If **half or more** of the cited files came back missing or stub from the 2a check, the thin flag is set and the block names it: `read order (N of M cited files are stubs or missing)`. A prompt whose headings are all filled but whose pointers lead to one-sentence placeholders is the exact shape of plausible-and-useless, and the sections being present is what makes it hard to spot.

If **any** field above hit its missing-source branch, or the read-order condition just above fired, put this block at the very top of the prompt, directly under the title. **Name every field whose source was missing, with one exception: the cases the table calls real answers.** An empty Step-0 batch is a real answer ("there is nothing to decide"), so it is never named as a gap. An empty Read order IS named, because a handoff with no key files listed is a handoff that skipped a section, not one reporting that no files matter.

```
> **HEADS UP ... THIS PROMPT IS THIN.**
> Missing from the handoff: <named fields, comma separated>.
> Not backed by disk: <cited files that came back stub or missing, comma separated>.
> These were never written down, not considered and dropped. Do not infer them and
> do not start building on a guess ... ask first.
```

**Both lines are conditional. Print a line only when it has content**, and drop the other. A handoff can be complete and still point at empty files, or be full of gaps while every file it names is real. Printing an empty `Not backed by disk:` teaches the reader to skim the block, which is the one thing it cannot afford.

And say one line to the user before spawning:

> Chip is ready, but it's thin ... `handoff.md` had no `Verify before building` section, so tomorrow's session starts with no pre-build checks. Want to add those now, or start thin?

### 2e ... assemble

```markdown
# START LOCALLY → <5 to 8 word mission title>

<thin-flag block, only if 2d fired>

**Workspace:** `<absolute path to the workspace root>`
**Route:** <the single line from 2c>

Run `/session-start` first ... it loads RULES.md, the handoff, and the last session
summary, and it flags anything in them that no longer matches reality. Then work the
mission below.

## Mission

<P0 item 1, verbatim>

Last session: <date> ... <title from the Checkpoint entry>.
Full write-up: `sessions/session-summary-MM-DD-YY.md`

## Deliverable

<the artifact or outcome, or the not-stated line from 2b>

## Read first, in this order

1. `sessions/session-summary-MM-DD-YY.md` ... what happened last session and why
2. `<key file path>` ... <its note from handoff.md>
3. `<key file path>` ... <its note>

## Step 0 ... close these before building

- <decision item, verbatim>
- <decision item, verbatim>

## Hard rails ... verbatim from handoff.md "Verify before building"

- <rail, verbatim>
- <rail, verbatim>

## Skills

1. `/session-start`
2. `<the mode the P0 names>` ... <one clause on why>
```

**Title, when there is no mission to name it after:** `START LOCALLY → <workspace name>, no mission set`. Do not title it after something else in the handoff to make the button look normal ... the button is the first place the user finds out the chip is thin.

**The absolute workspace path is not optional.** A prompt that says "read handoff.md" with no root is unusable in a fresh session that does not know where it is. Same reason the title carries the route instruction: this text gets read cold, by someone with no other context, and every assumption it makes about what the reader already knows is a hole.

---

## Step 3: Spawn the chip

Spawn the prompt as a task via `spawn_task`, with the title prefixed **`START LOCALLY → `**.

```
title:  START LOCALLY → Finish the process-ledger consent token
prompt: <the assembled text from 2e>
```

**Why the prefix, given the route line already says it:** the user reads the title on the button. They may never read the body before clicking, and the button next to it says "Start with worktree". The prefix is the instruction placed where the decision actually gets made. Keep it on the title even when 2c found that worktree would work fine ... local is the right default for a workspace whose scaffold files live on this machine, and one consistent title is worth more than a title that changes shape.

**The click stays, and that is correct.** Starting an interactive session is a human gate. It is also where local / worktree / cloud gets chosen, which is a choice no skill should make silently on the user's behalf.

Then tell the user, in one or two lines, what is on the chip:

> Tomorrow's session is queued: "Finish the process-ledger consent token". Click it when you're ready ... pick **Start locally**, this workspace isn't a git repo so worktree won't work.

---

## Step 4: The degraded branches. Every one of them says something readable.

| What happened | What to do |
|---|---|
| **`spawn_task` is unavailable** in this environment | Do not fail, and do not quietly drop the work. Print the assembled prompt in a fenced block and say: *"I can't spawn a task chip from here, so here's tomorrow's opening message ... copy it into a fresh session and it'll pick up from where we stopped."* The prompt is the deliverable; the chip is just delivery. |
| **Closeout did not complete** | Say which phase stopped and what that costs, then offer the choice. *"Closeout stopped before it rewrote handoff.md, so anything I put on a chip would be yesterday's plan. Want me to finish the closeout first, or spawn a chip that says the handoff is stale?"* Never build silently on a stale handoff. |
| **No `handoff.md` at all** | The workspace is not scaffolded. Say so, point at `/super-setup`, and do not create a handoff from here just to have something to read. |
| **`handoff.md` exists but has no P0 items** | Spawn anyway, with the thin flag and `MISSION NOT SET`. *"There's no P0 in the handoff, so the chip has no mission ... it'll open with the summary and ask you what you want to do. Want to name a first task now instead?"* **Do not invent a mission**, not even an obvious-looking one like "continue yesterday's work". |
| **Session summary missing** (Phase 0.7 could not write it) | Read order falls back to `Checkpoint.md`'s top entry, thin flag set, and the prompt says which file is missing rather than pointing at a path that does not exist. |
| **Two sessions today** ... several `session-summary-MM-DD-YY*` files | Use the one `handoff.md` points at. It is the newest by definition, because closeout just wrote both. |

---

## Verification before you report done

1. Did the prompt get built from files re-read off disk, not from this conversation?
2. Does it carry the **absolute** workspace path?
3. Are the hard rails **verbatim** ... same words, same commands, same order?
4. Does every field that was missing appear as a named gap rather than as nothing at all?
5. If any gap exists, is the thin-flag block at the top of the prompt AND was it said out loud to the user?
6. Does the `Route:` line state a finding from a check that actually ran, rather than an assumption?
7. Read the prompt once as if you had never seen this workspace. **Could you act on it?** If any step of it only makes sense because you were here today, that step is built on memory and has to be cut or sourced from a file.

---

## Non-goal, recorded so it does not get re-proposed

A headless `claude -p "<prompt>"` through Bash is the only way to remove the click. **It is the wrong trade.** It runs the next session non-interactively, which means the user cannot steer it, cannot answer its questions, and cannot pick local vs worktree vs cloud. The click is not friction to be optimized away ... it is the human gate on starting a session, and it is where a real decision gets made.
