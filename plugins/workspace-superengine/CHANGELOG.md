# Changelog — claude-workspace-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
