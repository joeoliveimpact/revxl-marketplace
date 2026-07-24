---
name: meta-ads-superengine:meta-ads-next
description: The compass. Reads the per-brand journey state and the journey map, shows "you are here" (done / current / next), and returns 2-4 ranked next moves with exact trigger phrases — callable anytime, from anywhere. Trigger phrases include "what's next", "where am I", "what should I do now", "meta ads next".
---

# meta-ads-next — the compass

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #5.
This skill IS the routing engine rendered on demand — other skills may hand
complex mid-journey states to it instead of duplicating logic.

## Load
1. `journey-map.md` (roster, edges, gates) + `routing.md` (block shape/rules) + `state-schema.md` — under `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/`
2. `~/.claude/meta-ads-superengine/.superengine` → active brand → `state/<brand>.json`
3. `~/.claude/revxl/teach-level`

## Compute (in order)

**1. No state at all** → the journey starts at setup. Render this and stop:

**Next moves**
1. Set up your engine — I learn your business once, only 3 answers required. Say: "set up my ads"  ← start here
2. See the whole road first — 2 minutes. Say: "ads tour"

**2. Position.** Walk the journey graph (journey-map "The journey") against
state: which phase is DONE (its state keys written), which is CURRENT
(started, incomplete), what's NEXT. Render per teach level:
- `new`: plain-English road ("Math ✓ → Funnel ✓ → **Creative ← you are
  here** → Plan → Launch"), one "what this means for you" line.
- `pro`: the phase line, bare.

**3. Staleness + loops sweep (before ranking):**
- `compliance[]` entry missing for current `offer_version` while a plan or
  creatives exist → flag: launch is gated.
- `targets.targets_version` older than a re-run trigger (F3 flagged in
  `last_review`) → flag.
- `targets.offer_version_used` differs from current `offer_version` → flag: the
  math ran against an old offer; re-run breakeven-math before trusting targets
  (F3 route). Null `offer_version_used` (legacy state) = unknown, not stale:
  flag it gently on the next math re-run, never as an alarm.
- `open_loops` → each becomes a candidate move.
- `bad_day_counter` ≥ 3 → performance-review outranks everything (F7).

**4. Rank moves.** Candidates = the out-edges of the current position +
loop/staleness fixes. Rules from `routing.md`: #1 must have all prereqs met
in state (never rank a gated move #1 — rank its unblock instead);
state-gate the offers (no PDA → no competitor-intel; declined → skip);
2–4 total.

**5. Render** in the routing.md grammar — `**Next moves**`, numbered, each
line `<verb phrase> — <what you get>. Say: "<trigger>"`, triggers verbatim
from the roster, most-likely-next first, `← start here` on the primary when
the coach is at a phase boundary. *Italic conditionals* for state-gated
options. Why-clauses per teach level.

## Teach mode
In `new`: the position line is plain-English ("you've done the math and the
funnel plan; creative is next — here's why that order") and each move
carries a one-line why; gloss terms per glossary.md deep tier. In
`learning`: position + bare whys. In `pro`: phase line + bare moves.

## Rules
- Reads everything, writes nothing.
- Never generic: every move must cite what in STATE makes it the move
  ("your 3 concepts have copy but no statics").
- Gates surface honestly: "Launch is blocked — compliance hasn't been run
  for your current offer" beats hiding the option.
