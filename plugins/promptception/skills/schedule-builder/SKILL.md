---
name: schedule-builder
description: Use when the user wants something to happen automatically at a set time or on a recurring rhythm — "every morning", "weekly report", "remind me", "run this every Friday", "do this while I'm asleep", "help me schedule", "/schedule-builder" — or when they ask about the /schedule command or scheduled routines.
---

# Schedule Builder — the ideal scheduled routine, promptception-style

Claude Code's `/schedule` creates routines: prompts that run on a clock (once or recurring) with **no chat and no human present**. That changes everything about how the prompt must be written — it can't ask a follow-up question, can't say "like we discussed", and nobody is there when it hits a snag. This skill runs the promptception method on that reality.

**Voice:** plain English, zero jargon, no sycophancy. Beginner teach mode is the default — every question carries its *why* (see the promptception skill's Teach Mode; same rules apply here).

## Step 0 — Explain the thing first (teach check)

Before anything, decide whether to explain what `/schedule` even is:

- **Explain when** teach mode is BEGINNER (the default), **or** the workspace is set to beginner — check `.claude/workspace.yml` at the workspace root: `verbosity: beginner` means always explain, even mid-session.
- **Skip when** they've toggled "standard mode" this session AND the workspace isn't pinned to beginner.

The explanation is 2–3 sentences, plain English, ending with what it means for them:

*"`/schedule` sets up work that runs on a clock — every morning, every Friday, once next Tuesday — whether you're at the computer or not. Like a coffee maker with a timer, but for reports, check-ins, and prep work. What this means for you: the recurring stuff happens without you remembering it, and you review results instead of doing the work."*

## Step 1 — Take the dump

Accept the mess as-is. Nothing attached? Say: *"Just talk. What do you want to happen on its own — and when?"*

## Step 2 — Build THE ROUTINE

Silently extract, then write the routine prompt an expert would have written. The unattended test governs everything:

- **Self-contained** — the prompt carries EVERYTHING the job needs (names, links, formats, examples). It fires in a fresh context with zero memory of this conversation — "the usual report" means nothing at 6am
- **Timing** — when, how often, one-time or recurring, and the timezone
- **Deliverable + destination** — what gets produced and WHERE it lands so they actually see it (a file, an email draft, a message)
- **Snag behavior** — what it does when an input is missing or a step fails with nobody watching: skip and report, or stop. Never guess-and-send
- **Outward-action rule** — anything that leaves the machine (send, post, publish) defaults to DRAFT for their review, not auto-fire, unless they explicitly choose otherwise now

Blanks for anything missing: `[WHICH INBOX]`. Every blank resolved before creating. Never assume.

## Step 3 — Show it, then close gaps

1. **"Here's the routine hiding inside what you said:"** → the full routine prompt + its schedule, in a copy-able block
2. **Routine Rubric** — ask about any fuzzy dimension (3–5 questions per round, up to 3 rounds, batched, never re-ask):
   - **Self-contained** — could a stranger run this from the text alone
   - **Timing** — exact clock, rhythm, timezone
   - **Deliverable + destination** — what shows up, where
   - **Snag behavior** — the no-human-watching branch
   - **End game** — what this rhythm feeds
   - Re-show the updated routine between rounds. Escape hatch only on explicit impatience, costs named first.

## Step 4 — Create it (this one Claude CAN do)

Unlike `/goal` and `/loop`, Claude can create the schedule directly. A standing automation is a real commitment, so the gate is explicit:

*"Ready to create: [one-line summary] running [schedule]. Say go and it's live."*

On the explicit yes, create the routine (via the schedule capability in the session). Then read back what was created — name, schedule, next run — so they see it exists. If the session has no scheduling capability, say so plainly and hand them the paste-ready `/schedule` request instead.

**Teach the controls** (one line): they can list, pause, or delete routines anytime by asking — a schedule isn't a tattoo.

## Step 5 — Orchestrator check

If the routine's job clears the intricacy bar (**2+** of: multi-system, multi-session, live infrastructure, money/send path), recommend the split: *"I'd have the routine do the gathering, and run the heavy judgment in orchestrator mode when you're present — automated collection, verified decisions. Say 'go orchestrator' to set up that half."*

Below the bar? Don't pitch it.

## Step 6 — The lesson (one line)

One sentence max: *"Notice the routine carries everything it needs inside itself — at 6am there's no conversation to remember, so the prompt IS the memory."*
