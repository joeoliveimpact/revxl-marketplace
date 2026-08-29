# Skill size — the two documented exceptions

Reference for maintainers. `scripts/validate.py` sets `SKILL_WORD_CEILING = 2200` and
`REFERENCE_WORD_CEILING = 1800`. Both are **warnings**, not errors, so neither fails CI.
This file records which skills exceed the ceiling deliberately, and why, so the warning
is not mistaken for an unnoticed regression.

## The two over the line

| Skill | Words | Status |
|---|---|---|
| `session-continue` | ~4,150 | Documented exception |
| `session-closeout` | ~3,420 | Documented exception |
| `update-everything` | ~2,805 | Pre-existing, not yet audited |

## What was already extracted

0.11.0 introduced this plugin's first `references/` directory. Six files, every one
under the 1,800 reference ceiling, every one cited exactly once:

- `transcript-filtering.md` — the filter command and its degrade branches
- `kickoff-prompt-template.md` — the literal output shape 2e assembles
- `degraded-branches.md` — the seven-row table read only when something has gone wrong
- `state-not-fact.md` — the measured incidents behind the never-transcribe-a-hash rule
- `checkpoint-demotion.md` — the 30-day window, run every closeout
- `session-log-stamping.md` — how to identify the transcript, needed at one moment

Plus `docs/kickoff-prompt-rationale.md` for settled questions that are never loaded at
runtime, and two sections of `session-closeout` compressed to pointers at
`docs/session-summary-format.md`, which already held the same material.

## Why the rest stays inline

**What is left in both files runs on every invocation.** `session-continue`'s 2b field
map, 2c route detection and 2d thin flag execute every single time the skill is called;
`session-closeout`'s phases likewise. Moving always-needed logic into `references/` does
not achieve progressive disclosure — it adds a mandatory second read to every run and
buys nothing but a smaller number in a warning.

The remaining route to the ceiling is splitting `session-continue` into two skills
(build-the-prompt, spawn-and-degrade). That was considered and rejected for 0.11.0: this
plugin already has a crowded end-of-session trigger surface, and adding another skill to
it trades a cosmetic warning for a real activation problem.

**Revisit this if either file grows again.** Growth past here should go into
`references/` or be cut, not appended.
