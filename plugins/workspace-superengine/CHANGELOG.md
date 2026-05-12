# Changelog — claude-workspace-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
