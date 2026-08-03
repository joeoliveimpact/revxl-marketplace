---
name: goal-builder
description: Use when the user wants to set a session goal or use the /goal command and needs help shaping it — "help me set a goal", "what should my goal be", "build my goal", "goal for this session", "/goal-builder" — or when they describe a work session's purpose in messy terms and want it pinned down.
---

# Goal Builder — the ideal /goal prompt, promptception-style

Claude Code's `/goal` command sets the session's goal: the one outcome everything in the session steers by. Most people type an activity ("work on my emails") when a goal is an **outcome with a done-test** ("3 launch emails drafted and approved, ready to load into GHL"). This skill runs the promptception method on that gap.

**Voice:** plain English, zero jargon, no sycophancy. Their mess is the fuel. Beginner teach mode is the default — every question carries its *why* (see the promptception skill's Teach Mode; same rules apply here).

## Step 0 — Explain the thing first (teach check)

Before anything, decide whether to explain what `/goal` even is:

- **Explain when** teach mode is BEGINNER (the default), **or** the workspace is set to beginner — check `.claude/workspace.yml` at the workspace root: `verbosity: beginner` means always explain, even mid-session.
- **Skip when** they've toggled "standard mode" this session AND the workspace isn't pinned to beginner.

The explanation is 2–3 sentences, plain English, ending with what it means for them:

*"`/goal` tells Claude what this whole session is FOR — one line that everything I do here steers by. Think of it as the difference between 'let's hang out' and 'we're leaving at 3 to get your kid.' What this means for you: sessions stop wandering, and when you come back tomorrow, the goal tells both of us exactly where we left off."*

## Step 1 — Take the dump

Accept whatever they give — rambling, half-sentences, dictation. Never ask them to tidy it. Nothing attached? Say: *"Just talk. What do you want to walk away with by the end of this session — tell me like you'd tell a friend."*

## Step 2 — Build THE GOAL

Silently extract, then write the goal they'd have written if they were an expert:

- **Outcome, not activity** — what EXISTS when the session ends that doesn't exist now
- **Done-test** — how they'll verifiably know it's done (a thing they can look at, click, send)
- **Scope edges** — what's explicitly IN and what's OUT (the out list is what keeps a session from wandering)
- **Constraints** — deadlines, quality bars, approvals needed, "don't touch X"

Mark missing pieces as blanks: `[WHICH 3 EMAILS]`. Blanks are gap markers, not shipping material — every blank gets resolved before delivery. Never assume.

## Step 3 — Show it, then close gaps

1. **"Here's the goal hiding inside what you said:"** → the full `/goal` text in a copy-able block
2. **Goal Rubric** — score your understanding; ask about any fuzzy dimension (3–5 questions per round, up to 3 rounds, batched, never re-ask):
   - **Outcome** — the thing that exists at the end
   - **Done-test** — how we'll both know it's done
   - **Scope edges** — in vs out
   - **Constraints** — bars, gates, no-touch zones
   - **End game** — what this session's result feeds (the launch, the client, the week)
   - Re-show the updated goal between rounds — the visible sharpening IS the lesson.
   - Escape hatch: only on explicit impatience, name what the remaining guesses cost, then obey "run anyway".

## Step 4 — Deliver

Claude cannot type `/goal` for them — it's a command they run. Hand them the finished line, paste-ready:

```
/goal [the crafted goal text]
```

If `/goal` doesn't exist in their app or the pasted line errors (availability and syntax vary by surface and version — have them try it, or check with `/help`), fall back honestly: *"Your app doesn't have /goal — pin this at the top of our chat instead and I'll steer by it all session."* Then treat it as the session goal yourself.

## Step 5 — Orchestrator check

Before closing, test the goal against the intricacy bar. If **2+** apply — spans multiple systems, spans multiple sessions, touches live infrastructure, touches a money/send path — say so:

*"This goal is big enough that I'd run it in orchestrator mode — I lead a crew of specialist agents instead of doing all the reading myself, and nothing gets built on an unverified claim. Say 'go orchestrator' when you're ready to start."*

Below the bar? Skip the pitch entirely — orchestration overhead must earn itself.

## Step 6 — The lesson (one line)

One sentence max, pointing at what made the goal work: *"Notice the goal names what EXISTS at the end, not what you'll be doing — that's the difference between a session that finishes and one that just runs out of time."*
