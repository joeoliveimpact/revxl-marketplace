# teach-mode — shared end-user voice convention

> Canonical cross-superengine convention. CNTNTSE-133. Every RevXL superengine
> reads this at skill entry so the **end user (the client)** gets a consistent
> voice. Copy the read snippet below verbatim into each skill — do not re-design it.

## The setting

- **File:** `~/.claude/revxl/teach-mode` — one line, value `beginner` or `off`.
  Top-level (NOT brand-scoped) — one switch flips every installed superengine.
- **Default:** `beginner`. **Absent or unreadable file = `beginner`.**
- Written by each plugin's **onboarding** skill on first install.

## Levels

| Value | Voice |
|-------|-------|
| `beginner` (default) | Plain-English-first. Name a technical term only after explaining it in plain words, then gloss it inline on first use. Add a "what this means for you" line wherever the consequence isn't obvious. Never strip the real vocabulary — translate alongside it. |
| `off` | Normal/standard voice. No teaching scaffolding, no glosses, no "what this means for you" lines. Assume the user knows the terms. |

`off` means *teaching off*, not *terse* — it is the ordinary professional voice, not caveman/expert-jargon.

## Read snippet (copy verbatim at skill entry)

```
teach_mode = read("~/.claude/revxl/teach-mode").trim() if it exists, else "beginner"
if teach_mode == "beginner":
    apply the beginner voice (plain-first, gloss terms, "what this means for you")
else:  # "off" or any other value
    apply the standard voice
```

In a SKILL.md this is one short paragraph at the top of the body (see the
"Teach mode" section the bundled skills carry).

## Adjusting it

Two ways, both persist (they rewrite the file):

1. **Command:** `/teach-mode off` (or `/teach-mode beginner`).
2. **Plain request:** "talk to me like an expert" / "stop explaining the basics"
   → set `off`. "explain things more simply" / "I'm new to this" → set `beginner`.

When a skill detects either, it writes the new value to `~/.claude/revxl/teach-mode`
(creating `~/.claude/revxl/` if needed) and confirms the switch.

## Adoption (other superengines)

Each superengine copies the read snippet into its skills' entry and adds the
`/teach-mode` command. Tracked as the sweep in CNTNTSE-133 — one pass per plugin.
