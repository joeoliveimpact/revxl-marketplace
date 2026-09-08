---
description: Switch the assistant's end-user voice between new (plain-English-first, explains terms), learning (some fluency assumed) and pro (standard voice, no scaffolding). Persists across sessions and across every installed RevXL superengine.
---

# /teach-mode

Set the shared teach level for every installed RevXL superengine. Authority file:
`~/.claude/revxl/teach-level`. Legacy sibling file, dual-written:
`~/.claude/revxl/teach-mode`. Convention:
`../skills/_shared/references/teach-mode.md`.

## Argument

`$ARGUMENTS` is the requested level: `new`, `learning` or `pro`.
- `new` ... plain-English first; explains a thing in plain words, then names the
  technical term with a one-line gloss; adds "what this means for you" lines.
- `learning` ... plain English plus the real term inline; less hand-holding; a
  brief why on the major decisions only.
- `pro` ... ordinary professional voice, no teaching scaffolding.

The two legacy words are still accepted and mapped: `beginner` -> `new`,
`off` -> `pro`.

## What to do

1. Read `$ARGUMENTS`.
   - If empty -> read the current level per the read snippet in
     `teach-mode.md` (`teach-level` first, then legacy `teach-mode` mapped,
     else `new`), report it plus how to change it. Stop.
   - If it is not one of `new` / `learning` / `pro` / `beginner` / `off` -> ask
     which one they meant. Stop.
   - Map `beginner` -> `new` and `off` -> `pro` before writing.
2. Ensure `~/.claude/revxl/` exists.
3. Write the single word (`new`, `learning` or `pro`) to
   `~/.claude/revxl/teach-level`.
4. Dual-write the legacy word to `~/.claude/revxl/teach-mode`:
   `new` -> `beginner`, `learning` -> `beginner`, `pro` -> `off`.
   Both files are written on every change, never one of the two.
5. Confirm in one plain line, e.g. *"Teach level is now **pro** ... I'll use the
   standard voice. Run `/teach-mode new` to turn explanations back on."*

This takes effect immediately and persists across sessions.
