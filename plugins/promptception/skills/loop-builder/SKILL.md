---
name: loop-builder
description: Use when the user wants something checked or done repeatedly and needs the /loop command shaped for it — "keep checking", "monitor this", "every 5 minutes", "run this until", "watch for", "help me set up a loop", "/loop-builder" — or when they try to phrase a recurring task and it comes out vague.
---

# Loop Builder — the ideal /loop prompt, promptception-style

Claude Code's `/loop` command re-runs a prompt on a schedule: `/loop 5m <prompt>` (fixed interval) or `/loop <prompt>` (Claude paces itself). A loop prompt is a different animal from a normal prompt: it fires over and over **with nobody watching**, so a vague one doesn't just underperform — it repeats its mistake every tick and burns usage doing it. This skill runs the promptception method on that problem.

**Voice:** plain English, zero jargon, no sycophancy. Beginner teach mode is the default — every question carries its *why* (see the promptception skill's Teach Mode; same rules apply here).

## Step 0 — Explain the thing first (teach check)

Before anything, decide whether to explain what `/loop` even is:

- **Explain when** teach mode is BEGINNER (the default), **or** the workspace is set to beginner — check `.claude/workspace.yml` at the workspace root: `verbosity: beginner` means always explain, even mid-session.
- **Skip when** they've toggled "standard mode" this session AND the workspace isn't pinned to beginner.

The explanation is 2–3 sentences, plain English, ending with what it means for them:

*"`/loop` makes Claude re-run one instruction over and over on a timer — check something, act if needed, wait, repeat. Like asking an assistant to 'check the inbox every 20 minutes and flag me if the client replies.' What this means for you: you stop babysitting things that change on their own — the loop watches so you don't have to."*

## Step 1 — Take the dump

Accept the mess as-is. Nothing attached? Say: *"Just talk. What do you want checked or done over and over — and what should happen when it's found?"*

## Step 2 — Build THE LOOP PROMPT

Silently extract, then write the loop prompt an expert would have written. A good one nails all five:

- **Watch target** — the ONE thing each tick checks (a status, an inbox, a metric, a file)
- **Per-tick action** — if found/changed, do X; otherwise do nothing and wait. One check, one action — a loop doing three jobs badly should be three loops or a plan
- **Stop condition** — when the loop ENDS (found it, N times, a date, "until I say stop"). A loop with no exit runs until it's killed
- **Safe to repeat** — the action can't double-fire damage (send the same email twice, re-post, re-charge). If it could, the prompt must check "already done?" first
- **Interval** — matched to how fast the watched thing actually changes. Checking a daily report every 5 minutes is 287 wasted runs

Blanks for anything missing: `[WHAT COUNTS AS A REPLY]`. Every blank resolved before delivery. Never assume.

## Step 3 — Show it, then close gaps

1. **"Here's the loop hiding inside what you said:"** → the full command in a copy-able block
2. **Loop Rubric** — ask about any fuzzy dimension (3–5 questions per round, up to 3 rounds, batched, never re-ask):
   - **Watch target** — what exactly gets checked each tick
   - **Per-tick action** — and what happens on the quiet ticks
   - **Stop condition** — how this ends
   - **Repeat safety** — what breaks if it fires twice
   - **Interval** — how fast does the watched thing really change
   - Re-show the updated command between rounds. Escape hatch only on explicit impatience, costs named first.

## Step 4 — Deliver

Claude cannot start a loop for them — the client runs the command. Hand it over paste-ready:

```
/loop 20m [the crafted loop prompt]
```

Plus the two operating facts every loop owner needs (one line each): loops keep consuming usage while they run, and telling Claude to **"stop the loop"** ends it.

If `/loop` doesn't exist in their app, offer the nearest real route: *"Your app doesn't have /loop — a scheduled routine does the same job on a fixed clock. Want me to build it? Say '/schedule-builder'."*

## Step 5 — Orchestrator check

If the per-tick action clears the intricacy bar (**2+** of: multi-system, multi-session, live infrastructure, money/send path), flag it before they run:

*"Each tick of this loop is doing heavyweight work — I'd run the action in orchestrator mode so every tick's claims get verified instead of assumed. Say 'go orchestrator' and we'll set it up that way."*

Below the bar? Don't pitch it.

## Step 6 — The lesson (one line)

One sentence max: *"Notice the loop says when to STOP — that's the line most people forget, and it's the difference between an assistant and a runaway."*
