---
name: meta-ads-superengine:meta-ads-teach
description: View or change the teach level (new / learning / pro) that controls how much the Meta ads engine glosses and explains — both Claude terms and Meta jargon. Trigger phrases include "teach level", "less hand-holding", "explain more", "talk to me like a pro".
---

# meta-ads-teach — the explanation dial

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #4.
Full mechanism: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/teach-mode.md`.

## Steps

**1. Read current.** `~/.claude/revxl/teach-level`, with the legacy
`teach-mode` fallback chain from teach-mode.md. Show it + the three-level
table in one compact form:

- **new** — I gloss everything (Claude terms AND Meta jargon), explain the
  why behind each move
- **learning** — Meta terms glossed on first use, brief whys on big decisions
- **pro** — terse operator voice, no glossing

If the marker's `tooling_level` is set (the axes are split per teach-mode.md),
show BOTH: "Meta-ads terms: <teach-level> · Claude/tooling terms:
<tooling_level>" so the coach sees each axis's setting.

**2. Resolve the ask.**
- Named level → set it.
- Directional ("less hand-holding" → up one; "explain more" / "plain" →
  down one) → confirm the target level, set it.
- Axis-specific ("gloss the Claude stuff, skip the ads glossary" / "I know
  ads, explain the tool") → set the two axes independently per teach-mode.md's
  split-axis rule (`teach-level` for the ads axis, `tooling_level` for the
  Claude/tooling axis).
- Just viewing → show + offer to change, done.

**3. Write BOTH files** (the dual-write is not optional —
`~/.claude/revxl/teach-level` + legacy `~/.claude/revxl/teach-mode` mapping
per teach-mode.md). Mirror to `state.teach_level`.

**4. Confirm in the NEW level's voice** (self-demonstrating):
- to `pro`: "Done. Terse from here."
- to `new`: "Done — I'll explain terms as they come up and tell you why
  each move matters. Change it anytime by saying 'teach level'."

**5. Inline block (edge E21):**

**Next moves**
1. Back to what you were doing — I'll pick up right where we stopped. Say: "<the interrupted skill's trigger>" (or just continue)
2. Not sure where you were? The compass knows. Say: "what's next"

## Rules
- One exception to level-obedience, stated in teach-mode.md and honored
  everywhere: gates, refusals, and compliance warnings render at FULL
  strength at every level. Say so if a `pro` coach asks why.
- A mid-session "plain" during another skill does NOT need this skill —
  that skill re-explains and offers to persist (this skill is the
  deliberate dial).
