---
description: Switch the assistant's end-user voice between beginner (plain-English-first, explains terms) and off (standard voice). Persists across sessions.
---

# /teach-mode

Set the shared teach-mode for every installed RevXL superengine. One file,
one switch: `~/.claude/revxl/teach-mode`. Convention:
`../skills/_shared/references/teach-mode.md`.

## Argument

`$ARGUMENTS` is the requested level: `beginner` or `off`.
- `beginner` — plain-English-first; explains a thing in plain words, then names the
  technical term with a one-line gloss; adds "what this means for you" lines.
- `off` — standard professional voice, no teaching scaffolding.

## What to do

1. Read `$ARGUMENTS`.
   - If empty → read the current value from `~/.claude/revxl/teach-mode` (absent =
     `beginner`) and report it, plus how to change it. Stop.
   - If it's not `beginner` or `off` → ask which one they meant. Stop.
2. Ensure `~/.claude/revxl/` exists.
3. Write the single word (`beginner` or `off`) to `~/.claude/revxl/teach-mode`.
4. Confirm in one plain line, e.g. *"Teach mode is now **off** — I'll use the
   standard voice. Run `/teach-mode beginner` to turn explanations back on."*

This takes effect immediately and persists across sessions.
