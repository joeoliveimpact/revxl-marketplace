---
name: matter-status
description: Snapshot one matter or all matters — status, deadlines, amount at stake, and the next actions. Use for "where's the X matter", "what's open", "matter status", "what's due", or a portfolio view across every case. Reads the matter files; changes nothing.
---

# matter-status

Read-only overview of where matters stand. No edits.

## When to use
"What's the status of X", "what matters are open", "what's due soon", "give me the rundown". Good at session start.

## Steps

1. **Scope.** One matter (`matters/<slug>/`) or all of `matters/`.

2. **Per matter, read `matter.md`** (and skim `chronology.md` for the latest event). Pull: name, type, our role, status, amount at stake, **next deadline**, open actions, anything flagged for a licensed attorney.

3. **Sort by urgency** — nearest deadline / most exposure first. Call out anything past due or within 14 days.

4. **Report** a compact table: Matter | Type | Status | Amount | Next deadline | Top action. Then a one-line "needs attention" callout for the most urgent.

## Ground rules
- **Read-only.** Never edit matter files from this skill.
- Surface deadlines and approval-gate items prominently — missing a deadline is the failure mode this skill exists to prevent.

## Definition of Done
A scannable status of the requested scope, urgency-sorted, with the single most pressing item named.
