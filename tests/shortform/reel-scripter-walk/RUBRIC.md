# reel-scripter walk: rubric (written before any run, 09.28.26)

Question: does reel-scripter (sf-042 796cc60) actually call the five Legit Content Skills from its reference files?

Harness: client-shaped profile (HOME and USERPROFILE = scratch home; live credentials copied at run time), `--plugin-dir` = sf-042 shortform-superengine only, `--strict-mcp-config`, sonnet, bypassPermissions, budget $1.50 per turn (`--max-budget-usd 1.50` on each `claude -p` call in run-mt2.sh). Fixture brand `fixturebrand` (the fixture brand, not the operator's own slug, so a disk-search leak cannot write into a real brand folder); project = `seed-proj/` from this folder, copied into the state folder by reset.sh; voice = the operator's voice files, kept outside the repo, under the fixture brand. No Goldmine Pattern Read on disk anywhere, so hook's adapt mode is NOT exercised (reported as not covered).

## Validity gates (a run that fails these is not graded)
- V1 build under test: a run counts only if shortform-superengine loaded from the build under test. Checked from the run log: every `system` / `init` event (one per turn) lists exactly one plugin named `shortform-superengine`, its `path` is the `--plugin-dir` folder run-mt2.sh passes (the sf-042 `plugins/shortform-superengine`) and its `source` is `shortform-superengine@inline`; and no `.claude/plugins/marketplaces/` path appears anywhere in the transcript. A second entry (source `shortform-superengine@synced`) means the account-synced copy loaded too, and the run does not count. `grade.py` prints the first init event's plugin list and the marketplaces count on its two `V1` lines. The number of skills loaded is not a validity signal: the scratch home carries account-synced skills (run7 loaded 509 and was valid).
- V2 the run got past Checkpoint 1 (an angle was picked). If it stops earlier, the run is INCOMPLETE, not a FAIL.

## Graded
- R1 REQUIRED: a Skill tool_use for `shortform-superengine:angles` before Checkpoint 1.
- R2 REQUIRED: a Skill tool_use for `shortform-superengine:rehooks` at Step 2 (before Checkpoint 2).
- R3 REQUIRED: a Skill tool_use for `shortform-superengine:hook` at Step 3.
- R4 CONDITIONAL: `rehooks` again at Step 4b only if the structure gate flagged a dead seam; `polarize` only if a contrarian angle was proposed; `viral` optional at 4c/4d. Report, do not fail.
- R5 A script file written under the fixture project's `scripts/`.
- R6 No Write/Edit tool_use outside the scratch tree.

Falsifiable: if R1, R2 or R3 is missing on a valid run, the "invocations live only in reference files" design fails, and the fix is a pointer in reel-scripter SKILL.md (or a structure-gate check), reversing the 09.28 decision to leave SKILL.md untouched.
