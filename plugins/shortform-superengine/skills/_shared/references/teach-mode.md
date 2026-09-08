# teach-mode ... one dial, three levels, family-shared

> Canonical cross-superengine convention. Every RevXL superengine reads this at
> skill entry so the **end user (the client)** gets one consistent voice across
> every installed engine. Copy the read snippet below verbatim into each skill.
> Do not re-design it.

## The dial

| Level | Voice |
|---|---|
| `new` (default) | Plain-English first. Explain the thing in plain words, THEN name the technical term with a one-line gloss on first use, and add a "what this means for you" line wherever the consequence is not obvious. Never lead with the term; never strip the real vocabulary either, translate alongside it |
| `learning` | Plain English plus the real term inline. Less hand-holding, some fluency assumed. Brief why on the major decisions only |
| `pro` | Ordinary professional voice. No teaching scaffolding, no glosses, no "what this means for you" lines |

`pro` means *teaching off*, not *terse*, and never *less safe*: gates, refusals
and cost warnings render at full strength at every level.

## Storage and back-compat

- **Authority:** `~/.claude/revxl/teach-level` ... one word, `new` / `learning` /
  `pro`. Top level, NOT brand-scoped: one switch flips every installed
  superengine.
- **Legacy dual-write:** on every write, also write `~/.claude/revxl/teach-mode`
  for older siblings: `new` -> `beginner`, `learning` -> `beginner`,
  `pro` -> `off`.
- **Legacy read fallback:** if `teach-level` is absent but `teach-mode` exists,
  map `beginner` -> `new`, `off` -> `pro`, then write both files (migrates in
  place).
- **Conflict guard:** if BOTH files exist and the legacy `teach-mode` is newer
  by mtime than `teach-level` AND maps to a different level (a sibling engine
  wrote it afterwards), ask once before overwriting. Never silently clobber a
  level the client may have just set elsewhere.
- **Neither file exists -> `new`**, and onboarding's calibration question is the
  natural fix.

## Read snippet (copy verbatim at skill entry)

```
level = read("~/.claude/revxl/teach-level").trim()          if it exists
   else map(read("~/.claude/revxl/teach-mode").trim())      if THAT exists
        where "beginner" -> "new", "off" -> "pro"
   else "new"

if level == "new":       plain-first, gloss every term on first use, add
                         "what this means for you" lines
elif level == "learning": plain English plus the term inline, why on the big
                         decisions only
else:                    ordinary professional voice, no scaffolding
```

In a SKILL.md this is one short paragraph at the top of the body (see the
"Teach mode" section each bundled skill carries).

**Re-read at every skill start** (drift guard). Never trust a value cached
earlier in the session. Mirror it to `state.teach_level` for the record; the
file is the authority (`state-schema.md`).

## Changing it

Two ways, both persist (they rewrite both files):

1. **Command:** `/teach-mode new|learning|pro`. The legacy words `beginner` and
   `off` are still accepted and mapped (`beginner` -> `new`, `off` -> `pro`).
2. **Plain request:** "talk to me like an expert" / "stop explaining the basics"
   -> `pro`. "less hand-holding" -> one level down. "explain things more simply"
   / "I'm new to this" -> `new`.

When a skill detects either, it writes the new level to
`~/.claude/revxl/teach-level` AND the mapped legacy word to
`~/.claude/revxl/teach-mode` (creating `~/.claude/revxl/` if needed), then
confirms the switch in one line.

## Where it renders

- Next-moves blocks render per level (`routing.md` rule 4): a one-line "why" per
  option at `new`, bare lines at `pro`.
- First use per session is what gets glossed, not every occurrence.
- Numbers stay honest at every level. Directional facts are phrased as
  direction ("push slightly past your real 90-day cadence"), never fake
  precision.

## One command, never a skill

`commands/teach-mode.md` is the only teach-mode surface this plugin ships.
**Never add `skills/teach-mode/`**: a `commands/<name>.md` shadows a
same-named skill directory on Desktop and the skill launches empty.
