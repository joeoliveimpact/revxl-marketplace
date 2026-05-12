# Changelog — claude-workspace-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
