# Changelog — claude-workspace-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.12.0 ... 2026-08-29

### Added
- **`.claude/rules/overrides.md` is the new home of the override constraints.** An unscoped rules file the harness loads into every session, replacing the root `RULES.md` that only existed in context after `/session-start` read it. Verified on the CLI surface with a canary test before shipping. New workspaces scaffold it directly; existing workspaces migrate lazily ... `/session-start` finds a legacy `RULES.md`, copies its body verbatim into the rules file, and quarantines the original to the workspace recycle bin with a manifest row. The copy is deliberately content-blind because a fleet audit found dated standing policy in these files with no other copy anywhere.
- **Recycle bin doctrine** (`docs/recycle-bin.md`): quarantine, never delete. Nothing enters without a manifest row, everything stays recoverable until emptied, emptying is an explicit act. Age reads from the manifest's quarantined column, never NTFS timestamps. This is the engine-free slice of the graph-brain work; it makes a future Checkpoint backfill legal without running it.

### Changed
- `session-start` Phase 0 now resolves the constraints in order: rules file present (harness-loaded, Code) or Read (Cowork); legacy `RULES.md` present (migrate once); neither (unscaffolded flag). A workspace holding BOTH files is told the root copy is stale and it gets quarantined ... two live copies with one authoritative is a silent-drift trap.
- The SessionStart hook's scaffold check accepts either rules location, so migrated and freshly scaffolded workspaces stop being warned "isn't scaffolded".
- 31-edit reference sweep across 12 files: super-setup, session-closeout, session-curator, workspace-add-hook/-module, README, kickoff prompt template, session-summary-format, beginner-voice, client-work module all point at the new location. Durable-decision routing now writes rules to the rules file.

### Removed
- `super-setup/templates/RULES.md`. Its replacement `templates/rules/overrides.md` carries the four constraints, the subagent-binding clause, the Linear source-of-truth hard rule, and the user's in-conversation escape hatch.

## 0.11.1 — 2026-08-29

### Fixed
- **`session-continue` no longer stops between its own steps.** The skill declared that it "does two things in order" and never said *in one turn*, so a question asked inside Step 1 ... the same-day check that decides whether closeout already ran ... ended the run. The model answered it, finished the closeout, and reported "ready for Step 2 whenever you are." Nothing had gone wrong except that the user typed one command and got handed the wheel back before the chip existed. A search of the shipped 4,434-word file found zero instances of any continuity rule: no "one turn", no "do not stop", no statement that the chip click is the only gate. Three additions close it ... the top contract now states that Steps 1 to 3 complete in a single turn and that a mid-step question picks a path rather than ending the run; Step 1's same-day ask says explicitly to continue through Step 3 either way it is answered; and Step 3 promotes the chip click from "correct" to **the only** human gate in the skill.
- The ask itself was right and is unchanged. Two real sessions on one day and an accidental double-run are indistinguishable from disk, and only the user can tell them apart. What was missing was the instruction to keep going afterward.
- **Why the eval missed it:** 0.11.0 shipped on six fixture runs graded 20 PASS / 0 FAIL. Those fixtures exercised the *stale-handoff* path the skill was designed around. None of them ran two sessions on the same date, which is the only path that reaches the ask. The failure the author anticipates is the one the author tests.

## 0.11.0 — 2026-08-27

### Added
- **`session-continue` ... close out and queue tomorrow in one pass.** It runs the full `session-closeout`, then reads back the files closeout just wrote (`Checkpoint.md`, `handoff.md`, the new session summary) and assembles the next session's kickoff prompt from them, spawning it as a task chip. The click stays on purpose: starting a session is a human gate, and it is where local, worktree or cloud gets chosen, which is not a choice a skill should make silently.
- **`session-closeout` writes a per-session summary file (new Phase 0.7).** `sessions/session-summary-MM-DD-YY.md`, written *before* Phase 1 so that the Checkpoint entry's `**Summary:**` handle and the handoff's wiki-link both point at a file that already exists. The Checkpoint entry itself shrinks to a burst plus two pointer lines, and the full write-up lives one link away. That is the bloat fix, not information loss.
- **The session transcript is now a source for the kickoff prompt.** `session-closeout` stamps a `**Session log:**` path onto the Checkpoint entry ... nothing else on disk records which transcript belongs to which session, so without it that link dies with the session. `session-continue` reads the log's conversation layer (filtered to `user`/`assistant` text blocks: on one measured session that was **29.6 KB out of a 0.90 MB file, 3.2%** ... the rest is tool plumbing) alongside `handoff.md`. The handoff still decides what carries forward; the transcript supplies the reasoning it compressed out, and where the two disagree that goes to the user as a finding instead of being resolved silently.
- **This plugin's first `references/` directory.** Six on-demand reference files carrying the material that is only needed at one moment — the transcript filter, the kickoff-prompt template, the degraded-branch table, the never-transcribe-a-hash evidence, the Checkpoint demotion rules, and session-log stamping. `session-continue` came down from ~5,330 words to ~4,150 and `session-closeout` from ~4,305 to ~3,420. Both remain over the 2,200 ceiling on purpose: what is left runs on every invocation, so moving it would add a mandatory second read rather than defer anything. Recorded in `docs/skill-size-exceptions.md`.
- **`session-curator` is scoped to mid-session work.** It shared bare trigger words ("wrap up", "close out", "handoff") with `session-closeout` while writing a pre-0.11.0 handoff — including a dated `## Last session`, which is exactly the line `session-continue` reads to decide whether a closeout already ran. Its description now routes end-of-session phrasing to the skills that own that format, and Mode 2 says plainly that its templates are older than the current contract.
- **The kickoff prompt is written to `sessions/kickoff-MM-DD-YY.md`** before the chip is spawned. A chip is not a durable artifact: unclicked or lost, the assembled prompt was gone and nothing recorded that the skill had run.
- **`docs/session-summary-format.md`** ... the full format reference for the new summary artifact: frontmatter, dated topical headers, the `Connections` block, and why `sot_policy: decay` is not optional.

## 0.10.0 — 2026-08-09

### Fixed
- **Cache cleanup silently deleted nothing on Windows and reported success.** A live pass printed `FREED: 0.03 GB`, no errors, having failed on the three largest directories. Cause: `MAX_PATH` (260 characters). Any plugin bundling `node_modules` exceeds it — `hyperframes` carries 268-character paths under `node_modules/.bun/` — so `shutil.rmtree` raises `WinError 3` partway through and abandons the rest; read-only attributes add `WinError 5` on top. Step 7 now requires all three countermeasures: the `\\?\` extended-length prefix on every delete path, an `onerror` handler that clears the read-only bit and retries, and a **freed-vs-planned comparison** so a pass that reclaims far less than it planned says so loudly instead of printing a success line. Verification is now arithmetic (`os.path.exists()` re-checked per directory, failures counted and printed), not the absence of an exception. The same run went from 0.03 GB to **4.48 GB** after the fix. macOS/Linux skip the prefix — it is Windows-only.
- **The scaffold created `outputs/` while every real workspace uses `output/`.** Checked across live workspaces: 7 of 7 use the singular form, none use the plural. Every new workspace therefore started out inconsistent with every older one, and any skill following the template wrote to a folder the user's other workspaces did not have. `super-setup` (and the `workspace-plan` / `workspace-verify` / `workspace-cleanup` references, plus the ARCHITECTURE and CLAUDE templates) now use `output/`.
- **`session-start` treated a missing `PLANNING.md` as a broken scaffold.** It now reads `PLANNING.md` only if present. Absence of that one file is no longer grounds for telling the user to re-run `/super-setup`; the other four scaffold files still are.

### Changed
- **The configured issue tracker is now read BEFORE the local files (Phase 3.5 → Phase 0.5).** Where a tracker is configured it is the record of record for what is open, done, and in progress; the workspace files are a summary written by whoever closed out last, and they go stale the moment work happens in another workspace. Reading them first anchored the whole brief to the weaker source — observed live, where a status brief reported the last session as five days old while the tracker showed work that had moved the same morning elsewhere.
- **Tracker/local disagreements are surfaced, never silently resolved.** A local file that contradicts the tracker may be the correct side — work that got done and never filed, or a step the process dropped. The skill now shows both versions and asks which is right, then updates whichever is stale, in either direction. It never overwrites correct information to make two sources agree. The status brief gains a `Drift:` line, omitted entirely when there is nothing to report.
- **Look up projects and teams by ID where the config provides one** — a name lookup can silently return empty and read as "nothing open."

## 0.9.1 — 2026-08-04

### Added
- **Cache health step**, with the trap that makes it look worse than it is. `.in_use` PID lock files accumulate for months, so a naive read reports a plugin "loading three versions at once" and sends someone chasing a bug that does not exist. The step now requires cross-referencing against actually-running processes — **only a marker matching a live PID is evidence of what is loaded**. Caught during post-restart verification: one plugin showed 10 markers on its old version, every one dead (newest 13 days old), while the single live marker sat correctly on the new version.
- **Superseded-version reporting + guarded cleanup offer.** Old version directories survive an update and feed the loader-picks-lowest bug ([#77546](https://github.com/anthropics/claude-code/issues/77546)); there is no `claude plugin cache prune` ([#81217](https://github.com/anthropics/claude-code/issues/81217)). Measured on one real machine: **12.4 GB total cache, 8.2 GB superseded (66%), 1,627 dead lock files**, with a single plugin holding five dead versions at ~1.5 GB each. Cleanup is offered, never automatic, and a directory must clear all three gates before it is even proposed: not the registry's current version, no live PID holding a lock in it, and explicit user consent for that specific list.

## 0.9.0 — 2026-08-03

### Added
- **`/update-everything`** — the missing "update all" command. Claude Code spreads updates across five tools, `claude plugin update` has no bulk mode (it takes a required plugin argument, so 50 plugins means 50 commands), and marketplaces must refresh *before* plugins or updates falsely report "already current". This runs the whole sequence in the right order and reports a per-plugin before/after diff instead of a wall of output.
  - Covers: marketplaces → plugins (looped, batch never aborts on one failure) → `npx skills` at **both** global and project scope → workspace-local `.claude/skills/` health → optional `claude plugin prune` and `claude update` (both ask first, never auto-run).
  - **Three-store awareness.** Beyond the CLI registry there is a **Cowork/agent-mode store** (`local-agent-mode-sessions/<id>/rpm/plugin_<id>/`) served as ZIPs from Anthropic's cloud, whose copy **shadows** the CLI copy. Nothing local reaches it — Anthropic's backend snapshots the marketplace at registration and never re-pulls ([#69683](https://github.com/anthropics/claude-code/issues/69683)), and remove-and-re-add is deduplicated server-side. The skill detects these from loaded skill prefixes, reports them as their own group, never claims to have updated them, and gives the one remedy that works: remove from Customize so Cowork falls back to the CLI copy ([#74609](https://github.com/anthropics/claude-code/issues/74609)).
  - **Loose-skill health check** at both project (`.claude/skills/`) and global (`~/.claude/skills/`) scope, not just versions: flags `SKILL.md` frontmatter that fails to parse (an unquoted colon inside `description` makes the whole frontmatter fail, and the skill then loads with empty metadata so its triggers silently never fire) and superseded copies that shadow an installed plugin.
  - Handles `Version: unknown` and git-SHA versions without reporting either as "current"; skips disabled plugins and says so; surfaces the same plugin installed from multiple marketplaces as a question instead of updating every copy blindly.
  - **Repair ladder with read-back verification.** `claude plugin update` printing "updated from X to Y" is only the out leg; the registry actually changing is the back leg, and nothing checked it before. Every update now re-reads `installed_plugins.json` and reports what *actually* moved, naming **which rung fixed each plugin** — rung 1 (update), 2 (uninstall/reinstall), or 3 (guarded registry edit with backup and auto-rollback). Field-validated on 7 pinned plugins: rung 1 fixed 7/7.
  - **Rung 0.5 — transport failures are not pins, and climbing the ladder for them is harmful.** A catalog entry of the form `{"source":"github","repo":"owner/name"}` resolves to SSH; with no GitHub SSH key the clone fails and the plugin silently never updates. Rung 2 would re-clone into the same failure and rung 3 would point the registry at a version that was never downloaded. Detected by `Permission denied (publickey)` / `Failed to clone`, fixed with `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`. Found live: a plugin sat 24 versions behind (4.6.1 vs 4.30.1) for months because of this alone.
  - **One-read pin detection** before any command runs: compare each registry `installPath` against the directories present in `cache/<marketplace>/<plugin>/`. A newer unused directory — especially carrying `.orphaned_at`, meaning it will be garbage-collected in ~7–14 days — is the diagnosis.
  - States the **restart requirement every run**, including when nothing changed.
  - Ends by offering to schedule itself as a weekly `/schedule` routine at a deliberately off-peak, non-round time, reporting only on weeks when something actually changed.

## 0.8.2 — 2026-08-01

### Added

- **session-closeout Phase 4.5 — commit the workspace repo.** Closeout is now the commit point: if the workspace root is a git repo, the session's work is committed automatically after the scaffold writes, with a message built from the Checkpoint.md entry just written. Skips silently when the workspace is not a repo or the tree is clean, flags non-session files (stray downloads, caches that a `.gitignore` should catch) rather than sweeping them in, and **never pushes** — a push is outward-facing and stays gated on explicit user approval, with unpushed commits reported in Phase 5. Phase 5's verification list gains a matching row.

## 0.8.1 — 2026-06-21

### Added

- **Team-scoped Linear tracking** (`linear.scope: team`) for hub workspaces that span multiple projects under one team (e.g. a Client Work workspace with one project per client). session-start reviews open issues across the whole team grouped by project; session-closeout picks the specific project worked on (creating it under the team if absent). Single-project workspaces are unaffected — `scope` is optional and defaults to project-scoped.

## 0.8.0 — 2026-06-21

### Added

- **Linear tracking is now automatic in the session skills.** `session-start` gains **Phase 3.5 (Linear Review)** and `session-closeout` gains **Phase 2.5 (Sync to Linear)**. Both run only when `.claude/workspace.yml` has a `linear:` block with `status: configured`, and skip silently otherwise. Session-start pulls open issues for the configured project into the status brief; session-closeout syncs started/completed work to that project.
- **`linear-kickoff` tracking mode now seeds an `ARCHITECTURE.md` Linear line** (super-setup Step 14 documents this) so the team/project binding is discoverable from the workspace map.

### Changed

- **Trigger corrected to the per-workspace `configured` flag, not bare MCP connection.** The Linear MCP is shared across every workspace, so "is Linear connected?" is true everywhere and cannot scope anything — the `linear:` binding is what selects the project. A connection check is now a **health-check** (warn if configured-but-disconnected), never the trigger, and never fails a session boundary.

### Fixed

- **The 0.7.0 directive-only design didn't fire.** It relied on the agent noticing the `## Linear Tracking` directive in each workspace's `CLAUDE.md` *and* the workspace being configured — so backfilled-but-unconfigured workspaces stayed dormant and tracking silently never happened. The behavior now lives in the skills themselves, gated on the explicit `configured` flag.

## 0.7.0 — 2026-06-17

### Added

- **Optional Linear tracking** for workspaces. `super-setup` gains **Step 14** — a conditional, no-op-by-default step that offers to wire up Linear tracking only when (a) the Linear MCP is connected and (b) the personal `linear-kickoff` skill is available. Clients without either are unaffected.
- **`## Linear Tracking` section** added to the `CLAUDE.md` template (pre-setup wording) and a `linear:` state block (`status`/`team`/`project`) added to the `workspace.yml` template. The unmodified `session-start`/`session-closeout` skills read `CLAUDE.md`, so the directive is honored at both session boundaries without further skill edits.

### Notes

- The actual Linear assignment is driven by `linear-kickoff` (tracking-only mode), which lives in the user's personal skills, not in this plugin. This plugin only contains the conditional offer, keeping all client installs a guaranteed no-op when Linear isn't present.

## 0.6.1 — 2026-05-12

### Changed

- Rewrote the plugin description (`plugin.json` and marketplace entry) in plain language. Old copy was jargon-heavy ("superengine", "shipped templates", "no model invention", "override constraints") and failed the plugin's own beginner-voice standard. New copy leads with the problem ("Stops Claude from forgetting what you were working on"), states concrete outcomes, signals plain-language explanations, and lists modules + runtime coverage.

## 0.6.0 — 2026-05-12

### Added

- **Cowork compatibility** across `session-start` and `session-closeout` skills. Both skills now branch on `.claude/workspace.yml#environment` and avoid Bash entirely in Cowork sessions. Live-infrastructure probes become advisory in Cowork (commands surfaced to user, not executed).
- **Environment detection** in `super-setup` (Step 0.3): attempts a no-op Bash call, falls back to Cowork on failure, confirms with the user, persists to `.claude/workspace.yml#environment`.
- **Identity detection** in `super-setup` (Step 0.5): scans `~/.claude/CLAUDE.md`, `~/.claude/projects/*/memory/*.md` files with `type: user` frontmatter, and `~/.gitconfig` as fallback. Detected values surface as defaults in setup questions with "press Enter to accept" UX. Strict privacy boundary — no client/feedback/workspace memories pulled.
- **`workspace-set-verbosity`** skill — single-question flip between `beginner` and `standard` modes. Writes `.claude/workspace.yml#verbosity`.
- **`docs/beginner-voice.md`** — 7th-grade voice style guide with reading-level target, five rules, and five example preambles.
- **Beginner-mode preambles** on all 11 plugin skills (`super-setup`, `session-start`, `session-closeout`, `workspace-add-module`, `workspace-add-hook`, `workspace-add-agent`, `workspace-cleanup`, `workspace-set-verbosity`, `workspace-brainstorm`, `workspace-verify`, `workspace-plan`). Each skill checks `verbosity` on entry and emits a 2-3 sentence preamble when set to `beginner`.

### Changed

- `session-start` and `session-closeout` SKILL.md files now contain explicit Runtime environment blocks documenting Code vs Cowork behavior.
- `super-setup` flow gains two new steps (0.3 environment detection, 0.5 identity detection) before the user-question phase.
- Renamed the `session-pickup` skill folder to `session-start` to match the `/session-start` command. Internal references updated.

### Notes

- Existing v0.5 Code workspaces upgrade non-breakingly — environment auto-detects as `code` and behavior is unchanged.
- Cowork users get a working scaffold and session lifecycle for the first time in this release.

## 0.5.0 — 2026-05-12

### Added
- New skill `workspace-brainstorm` — turns fuzzy ideas into written designs at `docs/specs/`. Universal (content, coaching, ops, code).
- New skill `workspace-verify` — pre-completion checklist enforcing evidence-before-done. Universal across content drafts, client deliverables, and code.
- New skill `workspace-plan` — turns approved designs into stepwise plans with explicit Definition of Done.
- New doc `docs/skill-activation.md` — client-facing explanation of how each skill auto-activates with example trigger prompts.

### Changed
- Activation polish across all plugin skills (`super-setup`, `session-start`, `session-closeout`, `workspace-add-module`, `workspace-add-hook`, `workspace-add-agent`, `workspace-cleanup`, `workspace-set-verbosity`, `agent-optimizer`). Each skill's `description` frontmatter rewritten with richer trigger phrases. Each skill body now includes a "Layer 2: Suggest before invoking" section so Claude can offer the skill instead of firing aggressively on borderline matches.

## 0.4.0 — 2026-05-12

### Added — Module system (P3)

- `module.json` manifest schema (v1). Each module declares files-to-create, directories-to-create, overwrite behavior, and an optional post-install message.
- Three opt-in modules shipped under `skills/super-setup/modules/`:
  - **`code`** — adds `.claude/specs/in-progress/` + `.claude/specs/completed/` + a `code-quality.md` rule that auto-loads on common source-file extensions.
  - **`client-work`** — adds `clients/_template/` (README + intake + sessions + deliverables) and a `client-work.md` rule covering confidentiality and engagement boundaries.
  - **`content`** — adds `content/drafts/` + `content/published/` + a `content-creation.md` rule covering voice, sourcing, and publish discipline.

### Added — Extension skills

- **`workspace-add-module`** — reads the module library, installs the chosen module's files, respects per-file overwrite confirmation, registers the install in `.claude/workspace.yml`.
- **`workspace-add-hook`** — interactive hook builder. Generates a script in `.claude/hooks/` and a matching entry in `.claude/settings.json`. Workspace-scoped only; never touches user-global settings.
- **`workspace-add-agent`** — interactive subagent builder. Auto-injects the four agent-optimizer override constraints into every generated agent. Non-optional.
- **`workspace-cleanup`** — aggressive housekeeping. Archives stale specs, sweeps junk, reorganizes loose outputs, surfaces duplicates. Per-item confirmation by default. Never touches `clients/`, never modifies the eight scaffold files.

### Changed

- Bumped plugin version to 0.4.0.

### Not yet

- Super-setup module integration (still P1 territory).
- Discipline skills (brainstorm / verify / plan — P4).
- Identity, voice, and cowork-mode handling (P5).

## [0.3.0] — 2026-05-12

### Added
- SessionStart hook (`hooks/session-start` + polyglot `hooks/run-hook.cmd`) that runs on `startup|clear|compact` and:
  - Loads the bundled `agent-optimizer` skill content into session context.
  - Emits a scaffold-status prompt to run `/super-setup` when `RULES.md` or `CLAUDE.md` are missing from the workspace root.
  - Broadcasts `verbosity` and `environment` from `.claude/workspace.yml` as a workspace-config reminder.
- Bundled `skills/agent-optimizer/SKILL.md` — the plugin no longer depends on a global agent-optimizer install. The four override constraints (Intent Clarification, Least Complexity, Surgical Execution, Declarative Focus) ship inside the plugin.

### Compatibility
- Windows: requires Git for Windows (provides `bash.exe`) — same requirement as the upstream `superpowers` plugin.
- macOS/Linux: standard bash. No additional dependencies.

## [0.2.0] — 2026-05-12

### Changed
- **BREAKING:** Plugin renamed from `claude-workspace-superengine` to `workspace-superengine` (dropped reserved `claude-` namespace). Marketplace entry, plugin folder, plugin.json, and homepage URL all updated. Existing installs must re-add.
- `super-setup` SKILL.md rewritten. The skill now ships its templates on disk under `skills/super-setup/templates/` (12 files + 3 `.gitkeep`) instead of asking the model to invent file contents at runtime.

### Added
- 12 shipped template files: `RULES.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GOALS.md`, `PLANNING.md`, `MEMORY.md`, `Checkpoint.md`, `handoff.md`, `tasks/STATUS.md`, `tasks/findings.md`, `troubleshooting/known-issues.md`, `workspace.yml`.
- 3 `.gitkeep` placeholders for `outputs/drafts/`, `outputs/final/`, `.claude/rules/`.
- Templates use `{{WORKSPACE_NAME}}`, `{{PURPOSE}}`, `{{DATE}}` placeholders, substituted at scaffold time.
- New **Step 13 — Verify** in `super-setup`: confirms all 15 artifacts exist, CLAUDE.md ≤ 150 lines, no `{{...}}` placeholders remain in output.

## [0.1.0] — 2026-05-07

### Added
- Initial release.
- Skill: `super-setup` — scaffolds the eight canonical workspace files
- Skill: `session-pickup` — disciplined start-of-session procedure
- Skill: `session-closeout` — disciplined end-of-session procedure with explicit UPDATE/NO-CHANGE walk
- Agent: `session-curator` — token-efficient closeout in subagent context (Claude Code only)

### Compatibility
- Claude Desktop: skills only (Customize → Skills install path)
- Claude Code: skills + agent (marketplace or settings.json install)
