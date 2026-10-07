# Changelog — shortform-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.0] ... 2026-10-06

### Added
- **content-goldmine skill** (SKLLPLG-332). Say "run the goldmine" after a finished
  cross-reference and it builds the Content Goldmine dashboard. New `SKILL.md` with
  `references/publish.md` and `references/gotchas.md`. The page is always saved under
  `<project>/visuals/` first, then published as a private Artifact (db `bank`); its link,
  the saved path and the dashboard tag go under `goldmine.*` in state. A first run (no
  `reel-build/goldmine-run.json`) re-runs analyze with a 30-day `--window-from` window and
  checks `window_source`. A later day resumes into the run's existing reads files.
  Journey-map roster, edges E31 and F11, the shortform-next route, the state-schema
  `goldmine` block and the skill count (16) follow.
- **Dashboard fetch** in `goldmine_build.py`: curl plus `tarfile` download of the pinned
  `content-goldmine-dashboard` tag (v0.2.1, engagement asks off the lead magnet board)
  into `~/.cache/shortform-superengine/goldmine-dashboard/<tag>`, with a commit-stamp
  check, safe-member and single-root checks, and a plain ERROR line and exit code for
  every failure.
- **Runner sync**: weak-CTA, `named_word`, `weak_cta_reels`, `--top-per-creator` and the
  stale-PAPS-row check. `reads` pre-fills the mechanical fields. `check-reads` requires
  `lm_none` on a row with no offer (an engagement ask) and never sets it itself, needs
  `lm_types` only when CTA rows exist, requires the newest PAPS to match, and writes the
  Proven Hooks file.

### Changed
- **Goldmine data is used by default.** When a Goldmine run's reads have passed, every
  reel uses its Pattern Read and proven hooks (hook, rehooks, viral, angles, polarize),
  adapted to the client's voice and never copied. The 0.5.0 mid-reel Goldmine question,
  gate check 9 and `hooks/goldmine-answer.py` are gone. The client's own hook enters as a
  `candidates:` line beside the proven ones. The only off switch is the client plainly
  saying to use their own hook or ignore the data; then no skill gets the data for that
  reel. The proven hooks come from the file named by `reads.proven_hooks`, else the top 3
  by multiplier from `reads.packet`.
- **The paid comments step always asks first, at three depth levels.** With no
  `--top-per-creator`, `plan` prices Light (each competitor's best breakout), Standard
  (top 3 per competitor) and Deep (every breakout in the window) in one ask, with the
  balance and the pull's window dates; the client picks a level, and a bare yes gets
  "which level?". `fetch` honours the saved cap, limits calls to the approved credits
  divided by the per-reel price, counts a missing `credits_used` as the estimate (marked
  `credits_estimated`), and refuses an approval below the Deep price that names no level.
  `--top-per-creator` must be a whole number of 1 or more.
- **A one-off counts only when the client asks for it.** The 0.5.0 new-reel-or-one-off
  hold lifts only after the client's own chat reply says "on its own", "one-off", "by
  itself" or "standalone", never with "new reel" or a negation in the same reply, and
  never from Claude's own `standalone: yes` alone. Popup answers and task notifications
  never count. The question is asked in plain chat.
- `publish.md` locks roster requests and reply drafts to the owner and Editors, like the
  Bank, and says plainly who can see them.
- **State schema 1.1.** The `goldmine` block is a 1.1 key, so content-goldmine Step 9
  sets `schema_version` to "1.1" when it records a run (`state-schema.md`, rule 7).
- The marketplace listing and the catalog README name the Content Goldmine. The skill
  count stays 16.
- The credit guard's Goldmine comment is reworded; the guard behaves the same.

### Fixed
- Zero breakouts give a plain message and exit 0 at every step, except `fetch` run
  without `--approved` or without a SocialCrawl API key, which stops on that first. A
  first run that finds nothing no longer uses up the 30-day window, and a zero result
  after a Goldmine keeps its passed reads.
- Long paths on Windows: the dashboard cache and the project folder work past the
  260-character limit through the long-path form, with no machine setting changed and
  nothing asked of the client. Messages and saved state show the normal path. A long
  project on a network drive stops up front with one plain message (exit 10).
- `analyze.py` works in long project folders on Windows too: the runner's 150-character
  gate, file paths joined from parts, and the same exit 10 for a long network folder.
  Checked by `tests/shortform/test_analyze_long_path.py`.
- `transcribe` says plainly when there is nothing to transcribe.
- The CTA pattern treats an em dash as a separator.
- `run-py.sh` exits 0 when a hook script is missing, so an update that removes a hook
  never blocks a session that is already open.

### Known limits
- The SocialCrawl calls still run from shortform in this release. Moving them to
  SocialCrawl Superengine is planned for the next release.

## [0.5.0] ... 2026-10-06

### Added
- **Five Legit Content Skills: hook, rehooks, viral, angles and polarize.** Each
  ships as a small wrapper SKILL.md (plugin triggers, routing, what reel-scripter
  hands over) around a byte-identical copy of the public master at
  `skills/<name>/references/legit-<name>.md`. `scripts/check_legit_sync.py`
  proves the copies match the master and pins their hashes in
  `scripts/legit-sync-manifest.json`. reel-scripter calls them from its reference
  files: angles at Step 1, polarize at Step 2 (myth-bust and contrarian reels),
  rehooks at Steps 2, 3 and 4b, hook in the Step 3 hook pass (with the top proven
  hooks from the pull's Pattern Read), and viral on every reel at Step 4a.
  Journey-map roster, registry rows E26
  to E30, the trigger hook and the skill counts (15) follow.
- **The structure gate enforces the calls.** Headless walks showed reel-scripter
  skipping written call lines (hook 0 of 4, angles and rehooks 1 of 4). The
  run now carries a `from:` stamp line from angles, rehooks and hook (kept in
  `reel-build/provenance.md`, see "Stamps are per run" below), each handed back
  only by that skill's wrapper, and `structure_gate.py` fails
  Step 4b on a missing or wrong stamp with the Skill call that fixes it.
  `angle_from:` waives the angles stamp when Step 1's proposal was skipped.
  A second gate run before Checkpoint 1 (`structure_gate.py --angles` on the
  saved proposals) makes angles run before the user picks, not after.
- **Stamps are per run** (SKLLPLG-336). The `from:` lines now go in
  `<project>/reel-build/provenance.md`, never in the skeleton or the angles file (a stamp in
  either one fails the gate). The gate clears that file when a reel passes, leaving one
  `passed:` line for that skeleton, so a second reel cannot pass on the first reel's stamps.
  Step 1's dedupe skips `*.skeleton.md`.

### Changed
- **reel-scripter is a conductor** (SKLLPLG-359). It runs the steps; the five skills own
  the method, and reel-scripter keeps no second copy of it. `hook-formulas.md`,
  `hook-mastery.md`, `opener-patterns.md` and `retention-psychology.md` are deleted;
  `say-this-not-that.md` moved to `skills/_shared/references/` with the losing-openers
  table. New calls, each with its own stamp in `reel-build/provenance.md`: rehooks again
  at Step 3 (`step: 3-lines`, the secondary hook first, the re-hooks after the body and
  proof picks), polarize at Step 2 for the Other side beat that myth-bust and contrarian
  skeletons now carry (it replaces the Step 1 polarize call), and viral on every reel at
  Step 4a (it replaces the optional punch-up; the user picks which suggestions apply).
  The skeleton needs an `angle_kind:` line. The hook pass shows 3 to 5 openings, all from
  hook, and asks the Goldmine question only when `reel-build/goldmine-run.json` shows
  data (a `goldmine:` line records it). Goldmine files are found through that JSON, never
  by the newest file name. Story Locks drops Locks 1 and 3 and Swaps 1 and 7 (6 swaps
  now) and may flag, never rewrite, another skill's line. The "follow for Part 2" CTA is
  gone; "follow for more" stays. The storyboard gets per-beat seconds and a visual cue
  every 3 to 5 s. pipeline-detail.md gains a method precedence rule (the skills and
  rulings, the Vault, Goldmine data: 2 of 3 decide).
- **Stamps are written by a hook, not by the model.** In 2 of 6 walks the model read a
  wrapper SKILL.md or `rehooks/references/step3-lines.md` for its `from:` line and copied
  the stamp instead of calling the skill; in 1 of 2 contrarian walks it wrote
  `goldmine: asked-yes` without asking. No skill file holds a stamp now. A new PostToolUse
  hook on the Skill tool, `hooks/stamp-on-skill.py`, appends `from: <name> <stamp>` to
  `<project>/reel-build/provenance.md` when angles, rehooks, hook, polarize or viral is
  really called (rehooks is written as `rehookslines` on a `step: 3-lines` call, or on a
  call after its Step 2 stamp). A stamp is the first 12 hex of a sha256 over a salt, the
  skill name and the project folder, so a stamp from another project or a typed token
  fails the gate. The hook never blocks: it exits 0 and prints nothing. The Goldmine
  question moves into the hook skill's reel-scripter Step 3 mode, which asks it, waits for
  the answer and writes the `goldmine:` line. `structure_gate.py --selftest` uses a
  throwaway salt; `--selftest-hook` feeds the hook sample input.
- **A stamp now needs the Skill call followed by a Read of the method file** (SKLLPLG-361).
  The stamp hook also runs on Read: a Skill call only opens a slot for that session, and the
  stamp is written when the model then Reads that skill's `references/legit-<name>.md`
  (`rehooks/references/step3-lines.md` for rehookslines) inside this plugin. A call with no
  Read, a Read before the call, or a Read in another session writes no stamp.
- **The final script's storyboard is checked on every write** (SKLLPLG-361). A new hook,
  `hooks/storyboard-on-write.py`, runs on Write, Edit and MultiEdit of
  `<project>/scripts/<slug>.md` (never the skeleton) and calls
  `structure_gate.storyboard_problems()`: a pipe table with a seconds and a cue column, each
  row over 0 and at most 5 s with exactly one visual cue, every `## Script` section named in
  a Beat cell, and range times back to back from 0:00. A problem exits 2 with the list on
  stderr, so the model fixes the file in the same turn. `structure_gate.py --storyboard
  <script>` runs the same check by hand.
- **The Goldmine answer is recorded only after the user replies** (SKLLPLG-365). A walk
  showed the hook skill rewording and bolding the Goldmine question, then writing
  `goldmine: asked-yes` in the turn it asked. The question now sits in `hook/SKILL.md` and
  `step3-options.md` as one fenced line to send exactly, defined once in code
  (`structure_gate.GOLD_Q`) and checked by selftest. A new hook, `hooks/goldmine-answer.py`,
  writes a `goldmine-asked:` stamp to `reel-build/provenance.md` only when the user replies to
  a turn holding the question word for word (or answers it through AskUserQuestion), and
  blocks any `goldmine: asked-` write before that stamp exists and any hand-written stamp.
  `structure_gate.py` check 9 fails an `asked-yes` or `asked-no` line with no valid stamp
  above it.
- **Walk rig** (tests/shortform/reel-scripter-walk): `probe-storyboard.sh` is a one-command
  live proof that the storyboard hook fires and the model fixes the file (SKLLPLG-367).
- **Checkpoints hold and Step 1 always runs** (SKLLPLG-362, SKLLPLG-366). Walks skipped Step 1
  and, on a second reel, ran every sub-skill call in one turn and picked the options themselves,
  because the gate checked that each call happened, never when. `hooks/stamp-on-skill.py` now
  also runs on UserPromptSubmit and on PostToolUse AskUserQuestion (it counts the user's turns,
  only for the session that owns the reel) and on PreToolUse Skill. It blocks (exit 2, the
  reason shown to the model) a Step 2 or later sub-skill call when `reel-build/provenance.md`
  holds no valid angles stamp, and a call that moves to a later step in the same user turn as
  the last call at the furthest step reached (a checkpoint crossed without the user). Going
  back a step is allowed. After the gate passes, Step 3 or later calls are fix calls allowed in
  any session, and a Step 2 call starts a new reel that needs a fresh angles call. Step 1 is
  never skipped: what the client brings (their own idea, leftover unpicked angles, a
  content-plan idea, an open loop) goes into the angles call as `candidates` and comes back as
  option 1 beside fresh options. The `--angles` instruction moved from SKILL.md to
  pipeline-detail.md "Step 1 propose". Walk grader: angles must come before the first rehooks,
  polarize, hook or viral call; new criterion K "checkpoints hold"; calls a hook blocked count
  as no call; a step token's trailing period is ignored. The walk's simulated client approves
  the skeleton only when asked a question.

### Fixed
- **Hooks start Python through a launcher** (SKLLPLG-370). The new hooks called bare
  `python`, which fails on a Mac with only `python3` and hits the Store stub on a Windows
  machine without Python. `hooks/run-py.sh` tries `py -3`, then every `python3` and `python` on PATH, and uses
  the first one that really runs Python 3, so the Store stub, a `py` with no Python 3 and a
  Python 2 are skipped
  and a working Store Python is used. On a Mac it skips `/usr/bin/python3` unless the
  command line tools are installed (no install dialog). No working Python: it exits 0
  silently, so every hook fails open. `tests/shortform/run-py-test.sh` checks it.
- **The five skills work on their own again** (SKLLPLG-370). The order rules now apply only
  in a session that called reel-scripter, so "write me a hook" or a hot take in any other
  chat is never pulled into the reel pipeline, and cannot switch off a reel in progress in
  another chat: each chat keeps its own order state, so a fix call in a new chat still
  stamps. After a finished reel, a Step 2 call (a hot take, rehooks) is held until
  Claude asks the client whether it is a new reel or a one-off (Joe, 10.03); a one-off then
  runs on its own and ends the order rules for that chat.
- **The five Legit skills end with their Next-moves block when run on their own.** Run
  outside reel-scripter, hook, rehooks, viral, angles and polarize ended on the method
  copy's Close line and never showed the block. Each wrapper now puts its block after
  the copy's Close; called by reel-scripter, it still hands back with no block.
- **An unfinished script is saved as a draft, not as the final script** (SKLLPLG-370). A
  Write that would create `scripts/<slug>.md` while that reel's skeleton has no `passed:`
  line is blocked and routed to `<slug>.draft.md`, with a plain-words note of what the client
  still has to give. An Edit or MultiEdit that creates that file before the pass is flagged after it
  lands and routed the same way. Existing final scripts stay editable. The storyboard check skips client
  notes in `scripts/` (no skeleton and no `## Text overlays` heading).
- **A final script that still has gaps is saved as a draft** (SKLLPLG-370). In walks, scripts
  reached `scripts/<slug>.md` after the gate passed with `[NEEDS YOUR INPUT]` beats, `[YOUR LIST]`
  overlays and a `STATUS: DRAFT` line, or with `[KEYWORD]` in the CTA and an `OPEN:` note. A Write of
  such a script is now blocked before it lands, and an Edit or MultiEdit that leaves one is flagged
  after; both route it to `<slug>.draft.md`, and Claude tells the client in plain words what is still
  missing. The rule lives once in `structure_gate.py` (`placeholder_problems`), and the walk rig uses
  the same one. It is built for precision, since blocking a finished script costs more than missing a
  gap: a bracket counts only when it starts with a placeholder word (`[KEYWORD]`, `[keyword]`,
  `[insert stat]`, `[TBD]`, `[TODO]`, `{{keyword}}`), is a short `[YOUR ...]` slot, or is a scaffold slot
  reel-scripter's references teach (`[outcome]`, `[resource]`); a `STATUS: DRAFT` line and an
  `INCOMPLETE` marker count too. Stage directions such as `[CTA]`, `[HOOK]`, `[ON SCREEN: ...]` and
  `[FRAME 0: ...]` do not count, but one that starts with a placeholder word does
  (`[ADD ZOOM]`, `[STAT: 73%]`: a known limit). Measured before shipping it: no hit on 22 such stage directions, Joe's 13
  real scripts and his teleprompter scripts, any finished walk script or the seed project, and every
  unfinished walk script with a bracketed placeholder word is still caught. Ceiling: a gap written as free text (`[THE MISSING PIECE]`,
  `[FOOD]`) is not caught, and an `OPEN:` note is not counted.
- **A script written from the terminal gets the same checks** (SKLLPLG-370). A walk wrote the final
  script with a Bash python heredoc, so no Write or Edit check ran. Now a Bash or PowerShell call made
  while a reel project resolves (the active brand's project, else a working directory that holds
  `analysis-data.json`; with neither, nothing is recorded) records that project's final scripts
  before it runs and checks each one it created or changed after, also when the command exits non-zero
  (Claude Code fires `PostToolUseFailure` then, not `PostToolUse`): the not-yet-passed rule, the gaps
  rule and the storyboard check, with a message saying what to move or fix. The command itself is never read. The
  after-check starts Python only when that call left a record, so a terminal call outside a reel
  project no longer starts it.
- **Checkpoint wording** (Joe's rulings, 10.02). "Just pick for me" covers the current
  checkpoint only: Claude picks, says which and why, and the client can change it. A
  copy-only edit at Checkpoint 4 keeps the gate's pass; only a skeleton change (a beat
  added, cut, moved, relabelled or re-tagged) re-runs the skills. Four "as the angle" leftovers now say the idea is Step 1's option 1.
  The paths in four reel-scripter commands (SKILL.md and pipeline-detail.md) are quoted for
  folders with spaces. The hook nudge fires
  on "opening line" only when a reel or video is named.
- **Version notes.** subject-matter and own-content-analysis (SKLLPLG-301) ship in a later
  release, not 0.5.0; the lines that promised them for 0.5.0 now say so.

## [0.4.2] ... 2026-09-11 (never released on its own; ships in 0.5.0)

### Added
- **A structure gate at reel-scripter Step 4b.** Checkpoint 2 now writes the
  locked skeleton to `<project>/scripts/<slug>.skeleton.md`: one numbered line per
  beat, loops tagged `[open ID]`, `[close ID]` and `[hold ID]` (a beat that deepens
  a loop already open), plus an optional `visual_loop:` line. `structure_gate.py`
  fails an early close of the main loop, a flat run of two untagged beats, a dead
  seam with no loop open, and a main loop that never pays off (the unpaid-loop
  check, which a declared visual loop does not excuse). Step 4c never starts before
  exit 0, and Checkpoint 4 shows the gate's `Seams:` line.
- **The editor-superengine handoff.** The script-written block (E6) offers the next
  step after recording: "Let me know when you record and where I can access the raw
  video(s)", `Say: "cut this reel"` (if installed), with a line on installing
  editor-superengine from the RevXL marketplace first. It replaces the "regenerate
  my visuals" move.
- **"retry the failed handles"**, the pulse's failed-handles-only retry: it re-lists
  only the handles whose newest probe line is still `probe-failed`, on the window
  they failed, priced at Checkpoint P1, and never moves `pulse.last_run`.
- **Open loops in the compass.** `shortform-next` (E20 and F3) renders an open loop
  by its skill: "resume my cross-reference", "script idea N from my content plan"
  or "script that reel". reel-scripter writes its `open_loops` entry at Checkpoint
  0, so an abandoned reel reaches the compass, and removes it at Step 5.
- **Two `check_routing.py` checks.** An id cited anywhere in a block body with no
  journey-map row is an error, and shortform-next's (E20) and (F3) blocks must
  carry byte-identical move lines.

### Changed
- **txt transcripts now count and are diagnosed.** `analyze.py` reads the
  `transcripts/<creator>/*.txt` files as spoken transcripts: they count toward
  `transcript_coverage` AND feed the spoken hook and theme diagnosis, so a counted
  reel is never ranked on its caption. On a project with txt transcripts the hook
  and theme tables shift; a JSON-only project reads the same as before. A NO
  VOICEOVER header or an empty body does not count, and a reel with both kinds
  counts once, its JSON text diagnosed. `field_vet.py` reads the same competitor txt files (never the client's `reels-full`).
- **Schema 1.5, additive only.** `meta.window_reels`, `window_reels_transcribed`,
  `transcribed_newest_published_at`, `transcribed_median_published_at` and
  `transcript_sources` (json, txt, both), plus `period_breakouts.window_source`.
  Nothing is renamed or removed; `render_visuals.py` accepts 1.5.
- **The pulse window starts at `pulse.last_run`.** `window_from` is the older of
  the last run and today minus 7 days (14 on request), so a missed week is covered
  in full and the window is never under 7 days; `analyze.py --window-from` takes
  it. Listings page on with `max_id` until the window is covered (pinned reels never
  decide the stop). Each page is keyed `pulse-<brand>-<handle>-<window_from>-p<n>`,
  so a resumed run replays at 0cr within 24h, and every retry (a 502/503, the
  failed-handles pass, retry mode) adds a fresh `-r<local HHMMSS>`. A handle
  that fails logs `probe-failed` in `refresh-log.md`, a
  later pull logs `probe-ok`, and roster health counts only the failures after a
  handle's last `probe-ok`.
- **The weekly brief** takes breakouts from `period_breakouts`, never the all-time
  leaderboard (the render now labels those rows as the leaderboard), and states
  this window's transcript coverage, the transcribed sample's recency, the tier
  balance and the handles that still failed. `whats-new.json` hook moves carry
  `field_n` and `client_n`.

### Fixed
- `field_vet.py`: the client's own reels no longer count as the field; with no
  spoken rows it prints a DEGRADED banner and a `[cap]` caption verdict instead of
  calling a keyword new; the strongest angle word is the first WINNER; a keyword
  match ends on a word boundary.
- `scripting_brief.py`: unranked rows count as neither winners nor flops; the
  opener-order line is gone from the brief; a DEGRADED analysis carries a warning
  line; a schema major-version mismatch stops before anything is written.
- `analyze.py` snapshots the `analysis-data.json` it is about to overwrite into
  `history/` (local date, never a duplicate). `render_visuals.py` resolves a
  relative `--prev` against the project and exits 1 on an unreadable one before
  writing anything.

## [0.4.1] ... 2026-09-08

### Added
- **The bundled `socialcrawl` skill is back.** 0.4.0 removed it and kept only
  `_shared/references/socialcrawl-endpoints.md`, which is the short list of calls
  the pipeline itself makes, leaving the engine with no API method and no
  per-platform reference of its own. The lean core returns exactly as it shipped in
  0.3.4 (`SKILL.md` plus 12 platform references), retrofitted to the 0.4.0 routing
  contract: `## Prereq (E0)` names the one door (the API key ladder; no key means
  refuse, spend nothing, and route to onboarding) and `## Terminal paths` writes
  four endings ... call made (E25), no key (E0), credits short (F4) and call failed
  (F10).
- **Registry rows E25 and F10** in `journey-map.md`, the `socialcrawl` roster row
  and its phrases ("check my SocialCrawl balance", "resolve this social URL",
  "batch-check engagement", "what does <endpoint> cost", "socialcrawl"), and the
  hook branch that nudges the skill on them. The branch is last, so no existing
  trigger loses precedence.

### Changed
- **The ruling this release encodes:** the research method, the templates and the
  guidelines live in shortform-superengine; socialcrawl-superengine, when
  installed, executes the searches. The skill description, the plugin README and
  the endpoints table say so.
- **`check_routing.py` section 4** skips `skills/socialcrawl/`: the bundled lean
  core IS the endpoint canon, and the endpoints table governs the pipeline's own
  calls. Every other file still has to name only endpoints the table lists.

## [0.4.0] ... 2026-09-08

### Added
- **A front door and a compass.** `shortform-start` ("start shortform") opens the
  journey, migrates a 0.3.x marker-only machine into the new state file without
  re-asking anything, and hands off. `shortform-next` ("what's next in shortform")
  reads that state and ranks two to four moves, and it writes nothing, so you can
  ask it as often as you like.
- **`content-plan`**, the weekly plan exit: 7 to 15 source-tagged ideas from four
  sources (the field's outliers, your own material and VoC, fresh signals via
  `google_news`, `google_trends` and `reddit`, and audience questions), balanced
  across your pillars and deduped against everything already scripted.
- **`## Terminal paths` in the top third of every skill.** Every ending, including
  every failure, decline and degrade, now has a written block that offers the next
  move. Placement is the point: after a context compaction the tail of a long
  SKILL.md is gone, and the skill that produces the deliverable was exactly the one
  losing its routing.
- **The routing gate.** `scripts/check_routing.py`, wired as `validate.py --section
  routing` and a sixth CI job, fails the build on a block past the compaction cut,
  a block outside Terminal paths, a block citing no journey-map id, a registry
  edge no block cites, an endpoint no table row names, a stale catalog version
  prefix, or a wrong README skill count.
- **`skills/_shared/references/`**: `journey-map.md` (the roster and the edge
  registry, E0 to E24 and F1 to F9), `routing.md` (the block grammar),
  `state-schema.md` (one state file per brand, one writer per key) and
  `socialcrawl-endpoints.md` (every endpoint this plugin calls, with its price).

### Changed
- **The Vault runs on the 0.15.0 contract**, so live pulls need
  workspace-superengine 0.15.1 or later. Without it the skills say so in one line
  and continue on the bundled references. The Vault never blocks a script.
- **Topic Pool moved out of `reel-scripter` into `content-plan`**, which is where
  a weekly pool belongs and which fixes the pools-are-too-small problem: one source
  became four. `reel-scripter` gains "script idea N from my content plan".
- **Six retained skills retrofitted** to the same pattern: the description carries
  every phrase a block offers, `## Prereq (E0)` names the door, state is read at
  the start and the owned keys written at the end.
- **`reel-scripter` and `competitor-cross-reference` steps now summarise inline**,
  with the full prose in `references/`. Every guardrail and checkpoint survives;
  the step text you read in the file is shorter than it was.

### Removed
- **The bundled `socialcrawl` skill.** Its endpoints are now
  `_shared/references/socialcrawl-endpoints.md` and nothing calls it by name.
  Anything deeper than that table (field search beyond the roster, creator vetting,
  share of voice, lead finding) belongs to socialcrawl-superengine, and the compass
  renders a written install refusal that routes rather than stalling.
- **The "hand off to the vault" option** on a finished harvest (SKLLPLG-78).
  Engines read the Vault; they never write to it.

### Known limits
- The pulse's `instagram/search/reels` leg is priced at 5cr where the docs say 1cr,
  and `prism/universal` is undocumented. Both carry a "verify against
  `credits_used`" note in the endpoints table; no credits were spent to settle it.
- `own-content-analysis` and `subject-matter` ship in 0.5.0. Until then "read my
  results" routes to the weekly pulse, and every block offering them is marked
  "(if installed)".
- The SKLLPLG-236 reel-scripter repairs and the SKLLPLG-234 competitor-pulse
  repairs ship in 0.4.2. No Python script in this plugin changed in 0.4.0.

## [0.3.4] — 2026-09-05

### Fixed
- **Rankings follow lift, not account size** (SKLLPLG-260, 201). `hook_taxonomy`,
  `theme_performance` and `gaps` carry `field_lift`, `field_accounts` and `read`
  (schema 1.4, additive): each account's reels in a bucket are scored against that
  account's OWN median views, then the median across accounts; 1.0 is neutral. The
  brief's every ranking comparator now uses lift; the pooled view count stays on
  screen but never ranks. A winner needs 1.2x lift and a loser sits under 0.8x; between
  the bars is near baseline. Fewer than 3 accounts or 8 reels reads `thin` and is never
  a winner or a loser. `field_vet.py` bands the same way. A pooled median had let one
  large account be the field (a keyword read 10.80x pooled, 1.27x per account).
  `--baseline-days N` optionally windows the denominators; default all-time.
- **Pinned and junk rows are dropped before any median** (SKLLPLG-261). `post.flags.pinned`
  rows, reels with no views reported, clips measured under 3 s, and rows with nothing
  said and nothing written never enter a ranking. Counts land in
  `meta.dropped_pinned` / `meta.dropped_junk`, in `analysis-data.md` and on the
  console. A missing duration never drops a row on its own.
- **Three candidates, not one** (SKLLPLG-201). The gap-to-close names the top hook and
  the next two, the top theme and the next two, so the same corpus stops yielding one
  concept re-skinned. The scripter also reads `<project>/scripts/*.md` and excludes
  pairings it already wrote unless nothing else remains.
- **Loud degrade, one payload reader** (SKLLPLG-263). Transcript coverage below
  `transcript_coverage_min` (default 0.6, `analysis-config.json`) prints a DEGRADED
  line in the md and on the console and sets `meta.degraded`. One `_items_of()` reader
  handles `{reels}` / `{items}` / `{data.items}` on both tracks in `analyze.py` and
  `field_vet.py`.

### Added
- **A UserPromptSubmit nudge** (`hooks/skill-trigger.sh`): when a prompt reads like a
  job one of the seven skills owns, one line names the skill to invoke. Fires in Claude
  Code (terminal and Desktop); never in Cowork, which does not load plugin hooks.
- **The SocialCrawl credit guard** (`hooks/credit-guard.mjs` + `costs.json`), the same file
  socialcrawl-superengine ships; the two copies must move together.
- **Named delegation**: when socialcrawl-superengine is installed (marker or cache dir),
  the four pull sites invoke `socialcrawl-superengine:research-plays` by name. Never blocks.

### Changed
- **The vault is the RevXL Vault** (Joe's ruling 09.04.26): every mention of the live
  strategy API at brain.engineforimpact.com now says Vault, so it can never be confused
  with brand-brain. Step 0d says "check the vault" and routes to
  `workspace-superengine:revxl-vault-search` when workspace-superengine 0.14.1+ is
  installed. The `brain-pulls/` folder, the host and `VAULT_API_KEY` keep their names.
- **The Vault status line is mandatory** (SKLLPLG-268): every brief states searches, reads
  and ok / degraded / skipped, even at zero calls; where Vault doctrine and local stats
  disagree, the brief says so and ranks the doctrine first. The Vault still never blocks
  a script.
- `render_visuals.py` accepts schema 1.4. An old brief reads a 1.4 file; the new brief on
  a 1.3 file keeps the old order.

## [0.3.3] — 2026-09-04

### Fixed
- **The 08.28 breakout-engine fix is now actually in the repo.** It was applied to
  the marketplace working tree and hand-patched into client caches on 08.28.26 and
  never committed, so every fresh install and every update kept the old ranker.
  Four files land byte-for-byte:
  - `analyze.py` — the client's own reels are excluded from the field outliers
    (Joe's ruling 08.28.26), so the brief can no longer recommend a pairing whose
    only evidence is a reel the client already posted; `outliers_full` is emitted
    alongside the capped list.
  - `scripting_brief.py` — reads `outliers_full`. The 30-row cap hid 483 of 513
    qualifying field reels from the theme × hook table.
  - `analysis-data.schema.json` — schema 1.3 (`outliers_full`, `period_breakouts`,
    `meta.generated_at`).
  - `render_visuals.py` — accepts schema 1.3, and **GURU joins `TIER_ORDER`**
    (SKLLPLG-262). `analyze.py` computed the tier; the renderer silently dropped it.
- **VAD enabled on the local faster-whisper path** (`transcribe_reels.py`,
  SKLLPLG-259). `vad_filter` defaults to False and was never set, so trailing
  silence decoded into invented sentences, sometimes in another language. Measured
  at roughly 8% of reels before the fix. `vad_filter=True` only: no batching, no
  VAD tuning, no `condition_on_previous_text` change (unmeasured; tracked
  separately). `onnxruntime` already ships with faster-whisper, so nothing new to
  install.

## [0.3.2] — 2026-08-17

### Added
- **brand-brain reference `transcription-vocabulary.md`.** How to turn the names
  already mined into `voc/business-config.md` and the `## Vocabulary` block of
  `voc/voice-guide.md` into a Whisper/Groq vocabulary prompt — and the two ways
  that prompt backfires (a bare comma list strips punctuation from the entire
  transcript; a prompt can drop a speaker's retakes, so compare output length).
- Guidance at both points that reach for Groq (`onboarding`,
  `competitor-cross-reference`), including preferring `whisper-large-v3-turbo`
  over full `large-v3` — no worse on proper nouns, ~3x cheaper, and it did not
  lose speech with a prompt where full v3 dropped 219 characters.

### Why
Measured across 48 minutes of real audio transcribed without a vocabulary: the
correct brand name appeared 3 times against 18 mangled ones. In one case a
reviewer read a mangled product name as the speaker stumbling and marked 9.4s
for deletion.


## [0.3.1] — 2026-07-21

### Added
- **C19 — secondary-hook dosage is a mandatory computation (Step 3).** The
  secondary-hook section now computes the placement COUNT from the length
  target via retention-psychology §4's dosage table (30s→1 · 45s→1–2 ·
  60s→2–3 · 90s→3–4) BEFORE generating, with 3 scored options per slot —
  never a single placement on a 60s+ reel. Dogfood catch (07.16.26, JOI-001):
  a 63s listicle shipped one secondary; the user hand-added the missing two
  exactly where the table places them. Sixth instance of the
  documented-but-optional-craft pattern (C15–C18).

## [0.3.0] — 2026-07-16

### Added — 2026-07-15 pm dogfood batch (C15–C18: implied craft → enforced screens)
- **C15 — mandatory skeleton-optimization pass (Step 2).** The beat skeleton is
  screened BEFORE Checkpoint 2 against four checks (one idea not a list · length
  budget · one loop paid late · single lever), presented pre-tightened with a
  one-line why per trim. Users approve an optimized skeleton, never a raw dump.
- **C16 — custom-idea field vet (`field_vet.py`, Step 1).** A user-supplied topic
  is vetted against the field before beats are committed: per-keyword spoken-track
  median vs field median (captions reported separately, never merged — the C7
  weighting), WINNER/NEUTRAL/LOSER/UNTESTED verdicts. Topic-level twin of the §8
  hook-type firewall. The idea is never vetoed — only the framing adapts.
- **C16b — LOSER vs UNTESTED branching.** LOSER (has data, underperforms) →
  pivot with 2–3 data-backed adjustments, user picks. UNTESTED / THIN (n<5) →
  NOT a loser: possible first-mover edge; de-risk by riding the novel topic on a
  proven hook type + nearest proven frame word. No data ≠ bad idea.
- **C17 — mandatory loop-integrity check (Step 4b).** Walks every beat seam and
  fails on dead-seam / early-close / flat-run before Checkpoint 4. Rule: from
  hook to CTA there is never a moment with zero open loops; the spanning loop
  resolves in the final beat.
- **C18 — Swap #8: second-person default (story-locks).** Every teaching /
  benefit / stakes line asks "can this be `you`, not `I`?" — first person kept
  ONLY for the creator's own proof/testimony. Vault-backed (viewer-as-protagonist).

### Added — 2026-07-15 batch (C-gate fixes + cheap enhancements)
- **C7 — dual-track analysis (schema 1.2, additive).** analyze.py now keys hook/
  theme/hook-line diagnosis on the SPOKEN transcript when one exists (per-reel
  caption fallback, marked `src`); the caption-keyed read ships as a separate
  "Caption patterns" md section + JSON `captions` bucket (packaging/SEO surface —
  never merged into the spoken diagnosis). `meta.transcript_coverage` reports
  degraded runs. Caption-only datasets stay byte-identical (regression gate).
- **C10 — scripting_brief.py reads live pipeline shapes.** `{reels}` top key
  native (legacy `{items}` fallback), JSON transcript ingest
  (client-transcripts.json + competitors/transcripts/*.json) when no txt
  transcripts exist — kills the caption-only "0 reels" failure.
- **C13 — text-overlay storyboard.** Step 3 gains a scored storyboard section
  (2 options, beat→overlay table 1:1 on the frozen skeleton, frame-1 = hook
  verbatim, ≤6 words/line, silent-scroll test); Step 5 template gains
  `## Text overlays`.
- **C12 substance layer explicit.** Client-topic reels REQUIRE a per-beat
  interview before generation; unanswered beats flagged, never invented.
- **C2** three-tier outlier cross-tab in `_pattern_stats.md`; **C4** 4-Killers
  validation note (120-reel corpus: 9/12 losers, 0/12 winners); **C5** blueprint
  synthesis-format template in pattern-matrix.md.
- **Wording:** Brain rebranded "Joe's Content Strategy Cloud Brain API"
  (constantly updated — the plugin double-checks current strategies);
  coach→client/brand-owner genericization (users may not be coaches).

### Added
- **Pattern Matrix — two-layer beat/pattern measurement (Step 4c).** Three new
  scripts in competitor-cross-reference, all config-driven (niche knowledge stays
  in the run's `analysis-config.json`, never in the plugin): `transcribe_reels.py`
  (batch transcription **straight off the pulled CDN URLs — no downloading, no
  yt-dlp**; parallel ffmpeg prefetch → faster-whisper; resume-safe; saves
  per-segment timestamps), `extract_patterns.py` (Layer 1: ~30 deterministic
  dims/reel — timing, rhetoric, CTA mechanics, caption↔spoken relationship,
  engagement joins — with auto winner-vs-loser lift tables, tool league, CTA
  payoff cross-tabs), `select_beatmap_set.py` (Layer 2: stratified N winners +
  N losers per cluster for Claude's semantic hand-map → Reel Beat Blueprint).
  New references: `pattern-matrix.md` (method + dims), `theme-derivation.md`
  (how to build a lane's `themes` override — method, not preset). Field-proven
  on a 1,000-reel corpus 07.12.26.
- **GURU competitor tier (4th, optional).** ≥500k-follower / household-authority
  accounts split out of LARGE so mega-accounts stop skewing the size-comparable
  benchmark (essential for small clients). analyze.py reads an optional `GURU`
  key in tiers.json/analysis-config.json — absent key = byte-identical legacy
  3-tier path. Documented in Step 2c + 4a.
- **Visual deliverables layer.** New deterministic renderer
  `competitor-cross-reference/render_visuals.py`: `analysis-data.json` →
  self-contained offline HTML at `<project>/visuals/` — **overview.html**
  (stat cards, reach-efficiency ladder, tier scoreboard, hooks + themes
  field-vs-client, followers×views map, cadence, opportunity map, gap cards,
  outlier wall, this-week panel), **competitors.html** (profile picker;
  `--split` writes standalone per-competitor pages for client delivery),
  **client.html** (profile + hook mix + the written roadmap inlined).
  Chart.js 4.4.7 vendored + inlined (zero network in output); dataviz-validated
  CVD-safe palette; table-view twin per chart; every JSON string HTML-escaped;
  brand tokens via optional `<project>/visual-theme.json`; `--prev` computes
  `whats-new.json` deltas; client trend charts once `history/` has ≥2 snapshots.
- **`competitor-pulse` skill (new, 5th user-facing).** The weekly heartbeat:
  snapshot → priced listing pass (✋ before any spend) → winners-only deep legs
  (✋, capped) → additive merge → re-analyze → refreshed visuals → cited
  "what changed this week" brief. Plus: **roster ops** (add/remove/swap with
  tier-balance check; removal moves data to `retired/` so no analysis ghosts),
  **field search** (free local-corpus keyword search first; live legs offered
  cost-labeled), **comment-pulse** (single post / creator last-N / field
  winners → deterministic word-frequency tables + quote-receipted opinion,
  objection, and question mining at ~5cr/post on IG — live-verified native
  delegation, not the 1cr doc price), and an optional-research-legs price
  table. Weekly schedule is SUGGESTED only (Step 4c pattern) — a
  scheduled run still stops at the credit checkpoint.
- **"Next moves" mesh — no dead ends.** Every pipeline skill now ends every
  terminal path (including declines and empty weeks) with 2–4 exact-trigger
  next-step offers; schedulable items are asked, never auto-set. Convention +
  E1–E16 edge registry: `skills/_shared/references/next-moves.md`. Closed dead
  ends: reel-scripter post-script + topic-pool no-pick, brand-brain
  refresh-decline + interview floor, harvest post-manifest, cross-reference
  checkpoint stops.
- **Schema 1.1 (additive).** `analysis-data.json` gains per-creator + client
  `hook_mix` ({hook_type: count}); versioning rules documented in the contract
  (minor = additive-only, consumers ignore unknown keys; major = hard stop).
  md + stdout verified byte-identical (regression gate).
- **RevXL Brain wiring (living knowledge API).** reel-scripter now pulls current
  content-strategy intelligence from Joe's Content Strategy Cloud Brain API
  (`brain.engineforimpact.com` — constantly updated, so scripts are always
  double-checked against current strategies)
  at exactly two named triggers — brief build (0d) and hook step — with a hard
  per-reel budget (≤2 searches + ≤3 note reads), a project-local cache
  (`<project>/brain-pulls/`), and full degrade to the bundled reference files when
  the key is missing/inactive or the API is unreachable. Key resolution mirrors
  SocialCrawl: env `VAULT_API_KEY` → `~/.config/revxl/vault_api_key` → ask-once+save.
  New shared reference: `skills/_shared/references/vault-api.md`. Onboarding Step 3
  gains an optional "RevXL Brain" wiring block (key issued by Joe; never blocks).
- **Brain API v1.1 — full hub-search surface** (live-verified over HTTPS 07.10.26):
  search gains `mode` (hybrid/semantic/fulltext/title), `path` similarity ("more like
  this note"), `tags`/`scope`/`frontmatter` filters with `-` exclusions, `threshold`,
  `rerank`, `snippet_length`; new `/v1/related` (graph traversal, depth ≤2); `/v1/note`
  reads up to 3 notes per call (+`raw`, `related:false`), returns links + backlinks.
  Budgets unchanged (each read path = 1 unit).

### Changed
- **Transcription is now ON by default and automatic** (was: off, opt-in). Spoken
  transcripts are the primary analysis text; an IG post caption is metadata, NOT what
  the creator says on camera — caption-only analysis is a flagged degrade, never a
  silent substitute. (Root cause of the 07.09 client run that analyzed captions.)
- **Parallel transcription:** Groq + local Whisper launch together, first healthy
  transcript wins (was: sequential fallback with captions preferred). `yt-dlp` is the
  fetch floor; platform subtitle track → post caption only when both engines fail,
  with a `caption-only` flag on every output that cites that reel.
- Automatic scope: all client reels + every outlier + each competitor's top performers;
  full-fleet expansion offered (free chain — runtime warning, not credits).
- competitor-cross-reference intake: `Transcript opt-in (off)` → `Transcription (on —
  automatic, explicit opt-out only)`.
- onboarding Step 2 reframed: transcription is the heart of the system, not garnish;
  gate rule now names yt-dlp the *fetch* floor (not "captions floor").
- creator-strategy-harvest + YouTube ref wording: YouTube subtitle tracks are real
  spoken-word transcripts (distinct from the IG post-caption shortcut); behavior unchanged.

## [0.2.2] — 2026-07-04

### Changed
- **Bundled `socialcrawl` skill is now a generated lean core** derived from the
  `socialcrawl-superengine` plugin's canonical skill: 12 reference files covering exactly
  the platforms this engine uses (Instagram, TikTok, YouTube, Facebook, Reddit, Google
  search/ads/trends/news, LinkedIn, Prism, universal search) with **exact per-call
  credits on every endpoint row** — including the Prism cheat codes (free URL resolver,
  1-credit batch post stats for 100 URLs, 1-credit full comments). 19 unused platform
  refs removed. The ⛔ transcript ban carries over verbatim (now covering all 9 banned
  endpoints, price-accurate).
- **SocialCrawl Superengine detection:** competitor-cross-reference (sourcing step),
  reel-scripter (Topic Pool), and onboarding (activation) now detect
  `~/.claude/socialcrawl-superengine/.superengine` and offer the deep research plays
  (ad-library recon, share-of-voice, audience-questions seeding) when the plugin is
  installed — one-line mention when it isn't, never a blocker.
- Onboarding: both-transcribers recommendation hardened (Groq + local Whisper both, so
  no reel falls through); updating guide rewritten dual-OS (Mac + Windows sync fixes).
- reel-scripter: Topic Pool mode ("20 ideas from the best performers" → evidence-cited
  weekly `topic-pool.md`); never-pay-for-transcripts guardrail.

## [0.2.1] — 2026-07-04

Premortem-driven hardening of the bundled `brand-brain` producer + reel-scripter's voice wiring (same premortem as email-sequence-superengine 0.2.1).

### Fixed
- **analyze.py read 0 reels from real pulled data (silent all-zero analysis).**
  `reels_of()` only accepted the mock `{items:[…]}` wrapper; the live puller writes
  `{handle,count,reels:[…]}`. Now accepts `reels` → `items` → `data.items`.
  Found on the first real-corpus run 07.12.26 — the engine had only ever been
  validated against synthetic harness data.
- **Cadence was always 0.0/wk on real data.** `cadence()` required epoch timestamps;
  the live API returns ISO-8601 `published_at`. New `_epoch()` helper accepts both.
- **Transcription step no longer instructs downloading.** The old text said to
  resolve videos via `yt-dlp`/instaloader — wrong and risky. The pulled reel JSON
  already carries the direct IG CDN `.mp4` (`post.content.media_urls`); ffmpeg
  streams it directly. Rewrote the step with the CDN-expiry rule (transcribe
  same-day or re-pull, ~3cr) and the segment-timestamps requirement.
- **reel-scripter now checks the shared brand brain FIRST** — `~/.claude/revxl/<brand>/voc/` was missing from its voice-resolution ladder, so a brain built from another engine (e.g. email) was invisible to reel scripting. The cross-engine promise now actually resolves.
- Brand-brain tie-in doc no longer claims reel-scripter reads `weekly-content-bank.md` (it doesn't; topical seeds are handed inline after a mine/refresh).

### Changed
- **Signature-bit canonization is PARKED** (bundled brand-brain): candidates still mined + filed (schema unchanged), no canonization review until a consumer engine reads canon bits. Candidacy gained mechanical deployability gates (portability, self-contained setup); canon requires recurrence across ≥2 independent sources.
- **Machine-readable overfit flag:** brain stamp blocks gain additive `source_count` + `provisional` keys; reel-scripter treats `provisional: true` brains as hypotheses, surfaces brain age on read, offers a refresh once, never gates scripting.
- **Mirror-language guard:** reel-scripter never quotes `voc-profile.md` "Mirror Language (hypothesis)" entries as audience VoC.
- Bit reaction evidence carries strength (`explicit`|`riff-along`); ranking tiebreak formalized; brand slug normalized with a similar-folder check.

## [0.2.0] — 2026-06-30

### Added
- **`brand-brain` skill (bundled shared producer)** — same producer bundled in email-sequence-superengine v0.2.0. Mines a client's real sources (Fathom/Fireflies recordings, own social, Meta DM export, guided-interview floor) into the shared brand brain at `~/.claude/revxl/<brand>/voc/` (voice-guide, voc-profile + evergreen seeds, shared business-config, signature-bits, weekly-content-bank). Idempotent detect-and-reuse: if the brain exists (built from ANY engine), it reuses/refreshes, never re-mines. reel-scripter's detect-and-prefer path now has its producer in-box.

### Changed
- **onboarding step 4b:** when no brand brain exists, offers to build it now with the bundled `brand-brain` skill (was: "fast-follow, not installed yet" message).

## [0.1.1] — 2026-06-26

### Added
- **`socialcrawl` skill bundled** — the full SocialCrawl API reference (27 platforms, 28 endpoint files) now ships inside the plugin, so onboarding no longer depends on a separately-installed global skill. Documents the Instagram `&max_id` pagination contract + a transient-failure retry note.
- **`onboarding`**: Node.js prerequisite check; new `references/troubleshooting.md` (antivirus install-block workaround, restart-via-Task-Manager, MCP-won't-attach recovery); SocialCrawl referral sign-up link.

### Changed
- **`competitor-cross-reference`**: pre-flight now shows live credit balance + estimated cost + confirm before any spend; expands a 2–3 handle seed to the ~25-competitor floor instead of accepting a thin set.

### Fixed
- Onboarding no longer dead-ends when a client lacks the global `socialcrawl` skill — the root cause of an Instagram scrape failure observed during a live client onboarding.

## [0.1.0] — 2026-06-24

### Added
- Initial release. Format engine #1 of the RevXL content family (shared analysis core bundled for now; splits out at format #2).
- **`onboarding`** — guided one-time setup: runtime + transcription-tier detection (yt-dlp captions floor + Groq / local faster-whisper), gate rule (captions + at least one real transcriber), bring-your-own-key SocialCrawl wiring with a client click-path, default beginner teach mode, state marker, and end-to-end verify.
- **`competitor-cross-reference`** — Instagram client-vs-competitor reel cross-reference → 10-section, client-facing strategy roadmap. Deterministic, regression-locked metrics engine; captions-first optional transcription (portable chain, no private infra).
- **`creator-strategy-harvest`** — harvest a trusted creator's full library (YouTube channel + playlists + newsletter) into a dated, recency-ruled, framework-extracted corpus for a knowledge vault (captions-first).
- **`reel-scripter`** — analysis-driven IG reel scripting: ranks proven niche moves from a cross-reference run and guides an in-voice Hook → Secondary → Body → Proof → CTA script with caption, flow-check, and craft scoring.
- **`/teach-mode`** command + shared teach-mode convention (`~/.claude/revxl/teach-mode`, `beginner` / `off`) — plain-English-first end-user voice by default, switchable.
- Skills chain forward: onboarding → competitor-cross-reference → reel-scripter.
