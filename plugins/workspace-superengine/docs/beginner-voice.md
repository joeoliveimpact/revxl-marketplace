# Beginner-mode voice guide

This document is the style standard for every plugin skill's beginner-mode preamble. If a skill ships in `workspace-superengine`, its preamble follows these rules.

## Why this exists

The plugin has two audiences:

1. Joe — experienced Claude Code user across coding, content, ops, client work.
2. REVXL coaching clients — many new to Claude, often non-technical, running Claude Desktop / Cowork.

Standard mode (terse, silent, action-first) suits audience 1. Beginner mode suits audience 2. Both audiences install the same plugin; verbosity flips per-workspace via `.claude/workspace.yml#verbosity`.

This guide is for **beginner mode only**. In standard mode, do not emit preambles.

## Reading-level target

- **Flesch-Kincaid ~70+** (7th-grade reading level). Aim for short sentences, plain verbs, common words.
- No CI check enforces this in v0.2 — author honor system.
- Quick test: read the preamble out loud. If a smart 7th-grader would stumble, simplify.

## Five rules

### 1. Define jargon inline on first use

Bad: "I'll set up a hook to fire on SessionStart."
Good: "I'll set up a hook (a small script that runs automatically when something happens) to fire whenever you start a new Claude session."

If the term appears again in the same preamble, the inline definition can be dropped.

### 2. Analogies over acronyms

Bad: "Loading the RULES.md overrides via the agent-optimizer SKILL."
Good: "Think of agent-optimizer as a coach standing behind Claude — it reminds Claude of four ground rules before every task."

Avoid acronyms entirely where possible. Where unavoidable, expand on first use.

### 3. Short, active, plain

- Cap sentences at ~18 words.
- Use active voice: "I'll save the file" not "the file will be saved".
- Plain verbs: "make", "show", "save", "read" — not "instantiate", "demonstrate", "persist", "consume".

### 4. Three-sentence cap

A preamble is **2-3 sentences**, never more. Beginner mode is helpful, not exhausting. If you need four sentences, you're explaining too much — cut the least-load-bearing one.

### 5. Lead with the verb, not the meta

Bad: "This skill is going to perform a workspace setup operation."
Good: "I'm about to set up your workspace files."

Start sentences with what you'll DO, not what kind of thing this is.

## Concrete examples (use these as templates)

### Example 1 — super-setup

> I'm about to set up your workspace files. This creates about 15 starter files — things like a rules file (so Claude follows the same ground rules every session), a memory file, and a checkpoint log. Once done, you'll have everything you need to start working.

### Example 2 — session-start

> Welcome back. I'll spend the first minute reading the four most important files (your rules, your handoff notes, your project plan, and the latest session log) so I know exactly where we left off. Then I'll tell you what's ready to work on.

### Example 3 — session-closeout

> Time to wrap up. I'll write a short log of what we did today and rewrite the handoff notes so next session's Claude knows what's next. Takes about two minutes.

### Example 4 — workspace-brainstorm

> Let's turn this idea into something concrete. I'll ask a handful of questions to sharpen it, then write up a short design doc you can keep or throw away. No commitment — we're just thinking out loud on paper.

### Example 5 — workspace-set-verbosity

> I'm about to change how chatty the workspace is. Beginner mode adds a short heads-up before each skill so you know what's coming; standard mode is quiet and just does the work. I'll read the current setting, ask you to confirm the swap, then save it.

## When to skip the preamble even in beginner mode

- **Continuing immediately from another skill** (no new user turn between them) — would be repetitive.
- **The skill's whole job is one question** (e.g. set-verbosity) — the preamble IS the prompt; don't double up unless it adds clarity.
- **The user explicitly said "skip the preamble"** in the same turn.

Use judgment, but lean toward emitting when in doubt.

## Layer 2 — "Suggest before invoking" wording

When a skill MIGHT fit but isn't certain (per the design spec Layer 2), surface it as a question, not a silent fire:

> This looks like a brainstorm situation — want me to run `/workspace-brainstorm`? Or should I just answer directly?

This phrasing works in both verbosity modes. In beginner mode, the suggestion is itself the discoverability mechanism — clients learn the skill catalog by being asked.

## Maintenance

If a new skill is added in v0.3+, its author writes the beginner preamble at the same time as the SKILL.md body. PR reviewers check it against this guide.
