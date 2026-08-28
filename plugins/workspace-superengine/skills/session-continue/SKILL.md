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

**First, check whether closeout already ran today.** `/session-closeout` is not idempotent ... a second run writes a second summary file, appends a second Checkpoint entry, re-runs the 30-day demotion over a file it just rewrote, and replaces `handoff.md` so it points at only the second half of the record. Running it twice splits one session's record in two. So check disk before invoking it.

**Read `handoff.md` and look at `## Last session`.** That line carries the date closeout stamped on it when it rewrote the file. Two outcomes:

| What you found | What to do |
|---|---|
| `## Last session` carries **today's** date | Closeout's handoff rewrite already ran today. Ask the user (below); the default is skipping to Step 2. |
| It carries an **older** date, or there is no such line | Treat closeout as not-run and go to the invocation below. |

**Check the handoff ... not `Checkpoint.md`, and never the presence of files.** Closeout writes the Checkpoint entry in Phase 1 and rewrites the handoff in Phase 2. A run that dies between those two leaves a Checkpoint entry dated today while `handoff.md` is still yesterday's, and yesterday's handoff is exactly what would send Step 2 off to build tomorrow's prompt from a stale plan. A Checkpoint-date check passes that case silently. A handoff-date check catches it, because the handoff is both the last thing closeout writes that this skill depends on and the file Step 2 reads. And a session summary sitting on disk proves Phase 0.7 ran and proves nothing else at all.

**If the handoff already carries today's date, ask. Do not assume.** A real second working session on the same day and a double-run look nearly identical from disk, and only the user knows which one this is:

> "Closeout already ran today and wrote `sessions/session-summary-MM-DD-YY.md`. Do you want me to skip straight to building the kickoff prompt from those files, or has there been more work since that needs its own closeout?"

**The safe default is skipping to Step 2** and building the prompt from the files already on disk. A second real closeout is the exception, and the user names it explicitly.

**Call the Skill tool.** Pass it the skill `workspace-superengine:session-closeout` and let it run its whole procedure.

**Make the call. Do not describe the call.** Writing "invoking closeout now" and then continuing is not an invocation, and in a transcript the two are indistinguishable ... which is exactly how it goes unnoticed. The only evidence that closeout ran is the files it wrote, so make the tool call, then check the files.

**Use the namespaced form exactly: `workspace-superengine:session-closeout`.** A bare `/session-closeout` is a skill name in slash costume ... this plugin ships no `commands/` directory, so there is no command by that name, and what a bare slash string resolves to here is unverified. The namespaced argument is the form that names one specific thing.

**Do not reimplement any of it here, do not skip phases to save time, and do not quick-mode it on this skill's behalf.** Closeout owns the session summary (Phase 0.7), the Checkpoint entry (Phase 1) and the handoff rewrite (Phase 2). This skill's entire input is what those three phases put on disk.

**Then assert it actually ran.** When the call returns, re-read `handoff.md` and check `## Last session` again ... the same check as before the call, used the second time as a receipt.

- **It carries today's date** ... Phase 2 finished, the handoff on disk is this session's, go to Step 2.
- **It does not** ... say it loudly, in these words or close to them: *"Closeout reported back, but `handoff.md` still carries an older date under `## Last session`, so its handoff rewrite did not finish. Anything I build now would be built on a stale plan."* Then go to Step 4's degraded branch. **Do not proceed on the assumption that it worked.**

**If closeout does not complete** ... the user aborts it, a write fails, they say "skip the closeout, just make the chip" ... do not silently continue as if it ran. Go to Step 4's degraded branch. A kickoff prompt built on a stale handoff is the failure this skill exists to prevent, wearing the costume of the thing working.

---

## Step 2: Build the kickoff prompt FROM THE FILES ON DISK

### 2a ... re-read, do not remember

**Re-read the files with the Read tool, even though you just wrote them this session.** Do not build any part of the prompt from what you remember of the conversation.

Read, in this order:

1. `handoff.md` (the version closeout just wrote)
2. `sessions/session-summary-MM-DD-YY.md` (the path from handoff's `## Session summary`)
3. `Checkpoint.md`, top entry only ... including its `**Session log:**` line
4. `.claude/workspace.yml` (environment and verbosity ... this skill uses nothing else from it)
5. **the session transcript**, at the path on that `**Session log:**` line ... conversation layer only, see below

**Filter the transcript to `user`/`assistant` text blocks. Never read the raw `.jsonl`** ... on the one session this was measured against, the conversation was a small fraction of the file and the rest was tool output. The filter command, the Cowork branch, and what to do when no log was stamped: `${CLAUDE_PLUGIN_ROOT}/references/transcript-filtering.md`.

#### What the transcript is for, and what it is not

**It is the evidence. `handoff.md` is the decision.** The transcript holds every reversed call, abandoned approach and corrected mistake, all weighted exactly the same as the conclusions that survived. A prompt built from raw transcript can resurrect something this session deliberately killed, and it will sound just as confident as the parts that were kept.

So: **the handoff decides what carries forward. The transcript explains why.** Take Mission, Deliverable, Step-0 and Hard rails from the handoff exactly as the field map says. Use the transcript to add the reasoning behind them, and nothing else.

**Where the two disagree, say so ... do not pick a winner.** If the handoff records an outcome the transcript shows was later reversed, or the transcript settles something the handoff never captured, that is a finding and it goes to the user now, while it can still be fixed:

> The handoff says the phase manifest ships as designed, but the log shows we cut it later in the session. Which one should tomorrow's prompt carry?

That check exists nowhere else. It is the reason for reading both rather than either.

**Then check every file the read order is about to cite.** For each path in `## Key files from last session`, and for the session summary itself, get its size (Code: `wc -c`; Cowork: Read it and look). Three outcomes:

- **Missing** ... no file at that path.
- **Stub** ... it exists but holds **under 200 bytes, or fewer than 3 non-empty lines**. That threshold is written down rather than judged so the check cannot drift: a file a next session is told to *read for context* is a paragraph at minimum, and one sentence is a placeholder somebody meant to come back to.
- **Real** ... anything else. Cite it normally.

**Never repeat the handoff's description of a file as though it were true when the file does not back it up.** `handoff.md` describes intent, not disk. A handoff line saying "the field map, rows 1 to 11 done" against a 35-byte file is exactly the failure this whole skill is built to prevent: correctly cited, verbatim faithful, and useless. Keep the description, and mark it against what is actually there ... see the Read order row in 2b for the wording.

**Why disk and not this conversation, when the conversation obviously holds more.** It does hold more. That is not the axis. The axis is that **disk is auditable and a context window is not** ... the user can read `handoff.md`, disagree with it, and correct it; they cannot do any of that to what a model remembers. The transcript satisfies both at once, which is why it is item 5 rather than an argument for working from memory.

If a field is not in the files, it does not go in the prompt. **Ever.** If you find yourself supplying a detail from memory because "the handoff didn't quite capture it", stop ... the correct fix is to say so and offer to add it to `handoff.md` first, then rebuild.

### 2b ... the field map

Six fields. Each row says where it comes from and what happens when the source is missing. **A missing source never produces an invented value ... it produces a named gap that appears in the prompt itself.**

| Field | Source | If the source is missing or empty |
|---|---|---|
| **Mission** | `handoff.md` → `## P0 — Next Actions`, **item 1**, verbatim. Plus the `## Last session` line for one sentence of context. | **Do not fabricate a mission.** Write `MISSION NOT SET ... handoff.md has no P0 items.` and set the thin flag. The chip still spawns; it just says out loud that nobody decided what to do next. |
| **Deliverable** | The outcome named inside P0 item 1 ... the file, artifact, decision or state it produces. If P0 item 1 names a path or an artifact, quote it. | If P0 item 1 names no outcome, write `Deliverable not stated in handoff. Agree what "done" looks like before building.` and set the thin flag. Do not guess the artifact. |
| **Read order** | The session-summary path first, then `handoff.md` → `## Key files from last session` in the order listed, each with its note. Every entry carries the 2a disk check. | Missing section → read order is the session summary alone, plus the line `handoff.md listed no key files.` Missing summary too → say `No session summary on disk` and set the thin flag. **Per entry, from the 2a check:** a **missing** file gets `**MISSING from disk.**` appended to its line; a **stub** gets `**UNVERIFIED ... the file on disk is <N> bytes, a stub, not what this describes. Check before building on it.**` Keep the handoff's description in both cases and put the mark right after it, in the read-order entry itself. Never in a footnote, never only in the thin block ... a reader skimming a numbered list has to hit it without looking anywhere else. |
| **Step-0 batch** | Any item under `## P0 — Next Actions` or `## P1 — Deferred` that is phrased as a **decision** or carries the words **confirm** or **resolve**. Also anything in `## Blockers` that needs an answer rather than an action. | None found → `No open decisions. Go straight to the mission.` That is a real, good answer and it does NOT set the thin flag. **Unless the Mission is also not set** ... then write `No open decisions were recorded either.` Pointing a reader at a mission that does not exist is the kind of small wrongness that makes a whole prompt read as auto-generated slop. |
| **Hard rails** | `handoff.md` → `## Verify before building`, **verbatim**. Copy the lines exactly, including any commands. Do not paraphrase, do not reorder, do not "clean up". **One narrow exception, spelled out below the table: a commit hash or pinned version is never transcribed as fact.** | Section missing or `(none)` → `No pre-build checks were recorded.` and set the thin flag. Rails are the highest-cost field to lose, because their absence looks identical to "nothing to check". |
| **Skills** | `/session-start` always first. Then whichever mode the P0 names ... if P0 item 1 says "build", "plan", "verify", "clean up", map it to the matching workspace skill (`/workspace-plan`, `/workspace-verify`, `/workspace-cleanup`, and so on). | P0 names no mode → list `/session-start` alone, and this does **NOT** set the thin flag ... it is a normal outcome, not a gap. Do not invent a second skill to make the list look fuller. |

**Verbatim means verbatim.** For Hard rails especially: retype nothing, summarize nothing. If a rail says `check the Tailscale link is up before hitting the rig`, that exact sentence goes in the prompt. Rewording a safety rule is its own hazard, and it is the reason this field is copied rather than written.

#### The one exception: rules are verbatim, state is re-derived

**A rule stays true next month. A fact about one moment does not.** So copy the rails verbatim, with one carve-out: **a commit hash, a pinned version, or a claim that some binary or service EXISTS is never transcribed into the prompt as fact.** Emit the command that re-derives it instead, or hand the check forward:

- `build from b38ef37` becomes `build from the current tip ... re-derive it: git -C <repo> log --oneline -1`
- `pinned at graphify 0.9.42` becomes `confirm the installed version before relying on it: graphify --version`
- an unprobed binary becomes `the handoff refers to ghl-cli. Confirm it is installed ... it was not probed when this prompt was written.`

**If you probed it, say so and say how.** `ghl-cli is on PATH (checked at generation time).`

The measured incidents behind this rule, and why it is worth an exception to a verbatim instruction: `${CLAUDE_PLUGIN_ROOT}/references/state-not-fact.md`.

### 2c ... route detection, stated and never guessed

The chip's click is where the user picks **local**, **worktree**, or **cloud**, and the UI default is **Start with worktree**, which is wrong for most workspaces. A skill cannot change that default, so the prompt has to carry the instruction to where the user will actually read it.

Run both checks and write a `Route:` line stating what you found. **Run both even when the first one already rules something out** ... they are independent reasons, and if both fire, both go in the line. Dropping the second because the first already forced "local" loses the reason a reader needs when they later move this workspace into a repo.

1. **Is the workspace root a git repo?**
   - Code: `git -C "<workspace root>" rev-parse --git-dir`
   - Cowork: Glob for `.git` at the workspace root.
   - **Not a repo** → `Route: this workspace is not a git repo, so "Start with worktree" will not work. Choose **Start locally**.`
2. **Does the mission need something only this machine has?** Scan the Mission, Deliverable and Hard rails text for: absolute local paths (`C:\...`, `~/...`, or a unix path rooted at `/`), SSH or SSH keys, a Tailscale hostname or tailnet IP, `localhost`, a locally-installed CLI, a local `.env` or credential file, or a local MCP server.
   - **Found** → `Route: cloud will not work for this one ... <the specific thing>. Choose **Start locally**.` Name the thing. "Needs local access" is not a reason, `sessions/` is on this machine and the rig is only reachable over the tailnet is a reason.
   - **What this scan actually found is a string in handoff prose, not a thing on this machine.** Naming it is required; asserting it exists is not allowed unless you probed it. Probe what you can cheaply probe (Code: `which <cli>`, `test -f <path>`; Cowork: Glob the path) and write the finding. If you did not probe it, phrase it as a pointer and not a fact: `Route: the handoff names ghl-cli, which would make this local-only. Not probed ... confirm it before building.` A route line is still a good route line when it says what it checked.
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

The template, the title rule, and why the absolute workspace path is mandatory: `${CLAUDE_PLUGIN_ROOT}/references/kickoff-prompt-template.md`. Assemble the six fields from 2b into that shape exactly ... it is the output contract, not a suggestion.

---

## Step 3: Write the prompt to disk, then spawn the chip

**Write it to disk first, before spawning anything.** `sessions/kickoff-MM-DD-YY.md`, beside the session summary, same numeric-suffix rule on a collision.

A task chip is not a durable artifact. If it is never clicked, dismissed by accident, or lost with the session, the assembled prompt is gone and nothing anywhere records that this skill ran at all. **That contradicts the rule this whole skill is built on** ... disk is auditable and a context window is not, and a chip is neither. Writing the file costs one Write call and makes the prompt reviewable, correctable and re-runnable tomorrow.

Then spawn the prompt as a task via `spawn_task`, with the title prefixed **`START LOCALLY → `**.

```
title:  START LOCALLY → Finish the process-ledger consent token
prompt: <the assembled text from 2e>
```

**Why the prefix, given the route line already says it:** the user reads the title on the button. They may never read the body before clicking, and the button next to it says "Start with worktree". The prefix is the instruction placed where the decision actually gets made. Keep it on the title even when 2c found that worktree would work fine ... local is the right default for a workspace whose scaffold files live on this machine, and one consistent title is worth more than a title that changes shape.

**The click stays, and that is correct.** Starting an interactive session is a human gate. It is also where local / worktree / cloud gets chosen, which is a choice no skill should make silently on the user's behalf.

Then tell the user, in one or two lines, what is on the chip:

> Tomorrow's session is queued: "Finish the process-ledger consent token". Click it when you're ready ... pick **Start locally**, which lives behind the small dropdown arrow on the chip, not on the main button. This workspace isn't a git repo, so worktree won't work. The prompt is also saved at `sessions/kickoff-MM-DD-YY.md` if you want to read or edit it first.

---

## Step 4: The degraded branches

Something will be missing sooner or later ... closeout aborted, no `handoff.md`, no P0, `spawn_task` unavailable, the prompt could not be written. **Every one of those has a written branch, and every branch says something readable to the user rather than failing silently or proceeding as if nothing happened.** The full table: `${CLAUDE_PLUGIN_ROOT}/references/degraded-branches.md`.

**Never invent a degraded path that is not in that file.** Silence is the failure mode this skill exists to prevent.

---

## Verification before you report done

1. Was the assembled prompt written to `sessions/kickoff-MM-DD-YY.md`, and does that file exist? Check it, do not assume it.
2. Did the prompt get built from files re-read off disk, not from this conversation?
3. Does it carry the **absolute** workspace path?
4. Are the hard rails **verbatim** ... same words, same commands, same order?
5. Does every field that was missing appear as a named gap rather than as nothing at all?
6. If any gap exists, is the thin-flag block at the top of the prompt AND was it said out loud to the user?
7. Does the `Route:` line state a finding from a check that actually ran, rather than an assumption?
8. Read the prompt once as if you had never seen this workspace. **Could you act on it?** If any step of it only makes sense because you were here today, that step is built on memory and has to be cut or sourced from a file.

---

## Non-goals and recorded rationale

Settled questions that should not be re-opened ... chiefly why the chip's click is kept rather than optimised away with a headless `claude -p`: `docs/kickoff-prompt-rationale.md`.