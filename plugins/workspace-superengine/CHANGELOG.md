# Changelog — claude-workspace-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.9.0 — 2026-08-03

### Added
- **`/update-everything`** — the missing "update all" command. Claude Code spreads updates across five tools, `claude plugin update` has no bulk mode (it takes a required plugin argument, so 50 plugins means 50 commands), and marketplaces must refresh *before* plugins or updates falsely report "already current". This runs the whole sequence in the right order and reports a per-plugin before/after diff instead of a wall of output.
  - Covers: marketplaces → plugins (looped, batch never aborts on one failure) → `npx skills` at **both** global and project scope → workspace-local `.claude/skills/` health → optional `claude plugin prune` and `claude update` (both ask first, never auto-run).
  - **Accounts for Desktop-installed plugins.** They are invisible to `claude plugin list`, so the update loop skips them — but they load from the shared marketplace clones at `~/.claude/plugins/marketplaces/`, which the step-1 marketplace refresh already pulls. The skill detects them from loaded skill prefixes, reports them as their own group, and explicitly steers users away from the Customize tab's Update button (unreliable) toward the terminal path that works.
  - **Loose-skill health check** at both project (`.claude/skills/`) and global (`~/.claude/skills/`) scope, not just versions: flags `SKILL.md` frontmatter that fails to parse (an unquoted colon inside `description` makes the whole frontmatter fail, and the skill then loads with empty metadata so its triggers silently never fire) and superseded copies that shadow an installed plugin.
  - Handles `Version: unknown` and git-SHA versions without reporting either as "current"; skips disabled plugins and says so; surfaces the same plugin installed from multiple marketplaces as a question instead of updating every copy blindly.
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
