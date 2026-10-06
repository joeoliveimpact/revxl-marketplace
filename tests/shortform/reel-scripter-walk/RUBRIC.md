# reel-scripter walk: rubric (0.5.0 conductor flow)

Question: does reel-scripter run as a conductor, calling the five Legit Content Skills at their steps, loading each skill's method file before it shows that skill's options, and passing its own gate?

Harness: `run-mt2.sh <name> [gut|contra] [--run2]`. Client-shaped profile (HOME and USERPROFILE = the scratch home under the state folder; the login file is copied in at run time), `--plugin-dir` = this repo's `plugins/shortform-superengine` only, `--strict-mcp-config`, sonnet, bypassPermissions. At most 18 turns; `--max-budget-usd 3.00` per turn; the walk stops once the session's `total_cost_usd` passes `RS_WALK_CAP` (default 8.00). Each answer is picked by `respond.py` from the fixture's answer file, off the last assistant text of the turn before; the responder refuses any answer that carries a phrase the plugin's trigger hook routes to another skill. `reset.sh <fixture>` before each walk, except run 2 of the second-reel walk.

Fixtures:
- **gut**: `seed-proj/` from this folder (synthetic, a myth-bust field), brand `fixturebrand`, answers `answers-gut.txt`. No Goldmine data.
- **contra**: a named subset of a real analysis, kept in the state folder only (`fixtures/contra-seed`), brand `contrabrand`, answers `fixtures/contra-answers.txt` there. Its `reel-build/goldmine-run.json` shows `reads.passed` true. The opening ask steers to the fixture's topic with no trigger phrase.

Grading: `py -3.12 grade.py <log> [--fixture gut|contra] [--run2]`. It prints one PASS or FAIL line per criterion and ends with `VERDICT: PASS` or `VERDICT: FAIL` plus the failed criteria (exit 0 or 1). A criterion whose input is absent (no skeleton, no script, no storyboard, no init event) FAILS with the reason; nothing passes silently. The final skeleton and script are the files under the project's `scripts/` that this transcript wrote (Write, Edit, or a shell redirect naming them); the newest wins.

## Criteria (all required; one FAIL fails the walk)

- **V1 build under test.** Every `system` / `init` event lists exactly one `shortform-superengine`, and its `path` is the `--plugin-dir` folder (this repo's plugin); no `.claude/plugins/marketplaces/` path appears in the transcript.
- **R5 script written.** A finished script under the project's `scripts/`. A script the plugin's placeholder rule flags (`structure_gate.py` `placeholder_problems()`, the rule the hooks use: a bracket that starts with a placeholder word such as `[KEYWORD]`, `[NEEDS YOUR INPUT]` or `[TBD]`, a short `[YOUR ...]` slot, a reel-scripter scaffold slot such as `[outcome]`, a `STATUS: DRAFT` line, an `INCOMPLETE` marker) is a draft and FAILS, naming what it still holds.
- **C calls placed.** A Skill tool_use for `shortform-superengine:<name>`, placed by its step token. Models paraphrase the template's `step:` line, so the token is parsed tolerantly: `step: X`, `step=X` or `step X`, any case, first match in the args; no match = no token. Accepted:
  - `angles`: a call (any step token) before the first `rehooks`, `polarize`, `hook` or `viral` call
  - `rehooks` Step 2: the first rehooks call, with step `2`, `slots` or none
  - `polarize`: any call; required when the skeleton's `angle_kind:` is `myth-bust/negation` or `contrarian/curiosity` (no readable skeleton = FAIL, the need cannot be judged)
  - `rehooks` `3-lines`: a later rehooks call (step token optional) followed by a Read of `rehooks/references/step3-lines.md` before the next assistant text of 300+ characters
  - `hook`: a call with step `3`, `3-hook` or none, after the rehooks Step-2 call
  - `viral`: a call whose step starts with `4a`, or none (required on every reel)
- **N no stamp copied from a file.** A stamp counts only from its Skill call. FAIL, naming the tool call, on any Read of a wrapper `skills/<name>/SKILL.md` (angles, polarize, hook, rehooks, viral), or any Bash, PowerShell or Grep call that targets one of those files or `rehooks/references/step3-lines.md` and searches for `from:`. A plain Read of `step3-lines.md` is the method-file load and is fine. Stamps are now written by the plugin hook `hooks/stamp-on-skill.py` only when the Skill tool calls the skill and the model then Reads that skill's method file in the same session (one stamp per skill per project folder); no skill file holds one, and the model never writes a `from:` line.
- **O order.** For each required call: the Skill call, then a Read of that skill's `references/legit-<name>.md` (`rehooks/references/step3-lines.md` for `3-lines`), before the first assistant text of 300+ characters after the call (the options shown). A Read just before the call counts too: one after the last 300+ character assistant text before the call. One qualifying occurrence per call is enough.
- **K checkpoints hold.** No step rises inside one user turn; each `result` event ends a turn. Steps as `hooks/stamp-on-skill.py` maps them: reel-scripter 0, angles 1, polarize 2, hook 3, viral 5; rehooks 4 with step `3` or `3-lines` (or no token after an earlier rehooks call), 5 with a step starting `4`, else 2. FAIL, naming the call, on a call above the highest step reached in the same turn as the last call at that step (it crossed a checkpoint without the user). Lower calls pass; reel-scripter and angles reset the highest step. A Skill call a hook blocked (its tool_result is an error) counts as no call, here and in C and O.
- **G gate.** The last `structure_gate.py` run on the final skeleton in the transcript (a Bash or PowerShell call naming it, not `--angles`) ends in a `PASS` line, and nothing writes the skeleton after that run (a Write, Edit or MultiEdit on it, or a shell command naming it with `>`, `tee`, `Set-Content` or `Out-File`). Graded from the transcript alone: the grader does not re-run the gate (stamps are per project, so a copy cannot pass) and does not read `reel-build/provenance.md` (a later reel's pass rewrites it, so the grade would depend on when grading ran).
- **S Other side.** For `myth-bust/negation` and `contrarian/curiosity`, the skeleton has a beat labelled `Other side`.
- **V visual cues.** In the final script's storyboard table (the first table with a seconds column and a cue column), the number of cues is at least the summed seconds / 5. A seconds cell is a number or a range (`0-3`, `0:03-0:06`); any cell that cannot be read as one FAILS the criterion. Cues in one cell are counted by separators: `;`, ` + `, ` / `, `->`, `then`, `<br>`; an empty cell or `none` is 0.
- **D deleted files.** No Read of `hook-formulas.md`, `hook-mastery.md`, `opener-patterns.md`, `retention-psychology.md` or `reel-scripter/references/say-this-not-that.md`.
- **Q Goldmine question.** contra: the exact question text from `step3-options.md`, the hook pass, appears in assistant text. gut: it never appears.
- **P no part-2 CTA.** The final script has no "follow for part 2" ask.
- **R2 second reel** (`--run2` only). Run 2's own log holds its own `angles`, `rehooks` and `hook` Skill calls.

## Controls

- A known-bad log (a pre-conductor run with no `step:` args) must print `VERDICT: FAIL`.
- A walk counts only if V1 passes. Login check (outside the grader): scratch login file after the walk vs the live one before.

## Not graded here

- Whether a skill's advice was used, only that its file was loaded before its options were shown.
- Whether the Other side beat was softened in the written script.
- The answer picks themselves: the responder's rules are regexes over the model's words, so a walk that stalls on a mismatched answer shows up as missing calls, not as a separate criterion.
