---
name: workspace-cleanup
description: Use to aggressively tidy a workspace — archive completed specs, sweep stale drafts, reorganize folder clutter, prune outdated entries from PLANNING.md / handoff.md. Trigger phrases include "this workspace is messy", "let's tidy up", "too many files", "clean this up", "archive the old stuff", "/workspace-cleanup". Heavier than session-closeout's lightweight per-session audit.
---

# workspace-cleanup

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> Time to tidy up. I'll look through your workspace for completed work, stale files, and clutter — then ask before moving or deleting anything. Nothing disappears without your say-so.

Action-taking housekeeping. Reuses the audit logic from `session-closeout` Phase 0.5 but acts on findings instead of merely listing them.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Looks like the workspace could use a tidy — want me to run `/workspace-cleanup` and walk through archiving / reorganizing? Or just deal with one file you have in mind?"

Only run the full process below after the user confirms. If the user explicitly invokes `/workspace-cleanup`, skip the suggestion and proceed.

## When to use

Trigger phrases:

- "clean up the workspace" / "this is getting messy"
- "archive old specs" / "too many drafts in root"
- "trim the workspace down"
- "what should I delete?" / "garbage collect"

Do NOT use for:

- Per-session wrap-up (`/session-closeout` handles that with an audit + advise pattern)
- Deleting client material (this skill never touches `clients/`)
- Touching anything in `.git/` or other VCS metadata

## Step 0 — Preconditions

1. Confirm scaffolded workspace.
2. Read `.claude/workspace.yml`. Note `environment` and which modules are installed — affects which cleanup rules apply.

## Step 1 — Audit (the inventory pass)

Walk the workspace and build a categorized findings list. Use Glob + Read only (no Bash, for Cowork compat).

Categories:

### A. Stale specs (if `code` module installed)

- `.claude/specs/in-progress/*` whose mtime is over 60 days old OR whose contents include a "shipped" / "completed" / "done" marker → candidates for archive to `.claude/specs/completed/`.

### B. Stale drafts (if `content` module installed)

- `content/drafts/*` over 90 days old with no recent edits → candidates for either move-to-published (if user confirms it shipped) or archive to `content/drafts/_stale/`.

### C. Loose outputs

- Files in workspace root that match output-y patterns (`*.draft.md`, `output*.md`, `notes-*.md`, `tmp-*`, `scratch*`) → candidates for move to `output/drafts/`.

### D. Junk patterns

- `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.swp`, `*.bak`, `~$*`, `*.orig`, empty `.gitkeep` in directories that no longer need one → candidates for deletion.

### E. Empty / vestigial directories

- Top-level dirs containing only `.gitkeep` and nothing else, that aren't required by the scaffold. Surface, don't delete by default.

### F. Stray docs in root

- `*.md` files in workspace root that aren't in the scaffold whitelist (RULES, CLAUDE, ARCHITECTURE, GOALS, PLANNING, MEMORY, Checkpoint, handoff, README, CHANGELOG, LICENSE). Candidates for move to `output/drafts/` or `tasks/`.

### G. Duplicate / near-duplicate files

- Same basename in multiple locations (e.g. `roadmap.md` in root AND in `tasks/`). Surface for user resolution.

Skip entirely:

- Anything inside `clients/`, `.git/`, `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`.
- Anything matching `.gitignore` patterns if a `.gitignore` exists at root.

## Step 2 — Present the plan

Group findings by category. For each, propose an action. Display like:

```
Workspace cleanup plan (dry run):

A. Stale specs (3)
   archive  .claude/specs/in-progress/2026-01-04-old-feature.md  -> .claude/specs/completed/
   archive  .claude/specs/in-progress/2026-02-15-shelved.md      -> .claude/specs/completed/
   keep     .claude/specs/in-progress/2026-04-30-recent.md       (under 60 days)

B. Stale drafts (1)
   move     content/drafts/2025-12-old-essay.md  -> content/drafts/_stale/

C. Loose outputs (2)
   move     scratch-notes.md  -> output/drafts/
   move     output-v3.md      -> output/drafts/

D. Junk (4)
   delete   .DS_Store
   delete   Thumbs.db
   delete   tmp-debug.bak
   delete   ARCHITECTURE.md.orig

E. Empty directories (1)
   keep     legacy/  (surfaced, no action — delete manually if intentional)

F. Stray docs (2)
   move     meeting-notes-2026-03.md  -> tasks/
   move     idea-draft.md             -> output/drafts/

G. Duplicates (1)
   surface  roadmap.md in / AND tasks/  (resolve manually)

Total: 9 actions proposed (3 archive, 3 move, 3 delete, 1 surface).

Proceed? Options:
  all       - apply everything above
  category  - pick categories to apply
  per-item  - confirm each action
  cancel
```

Default to `per-item` if the user is silent. The Surgical Execution rule means we never act in bulk by default.

## Step 3 — Execute approved actions

Run the chosen actions in this order: deletes last (so a botched move doesn't lose data), archives and moves first.

For each action, log:

```
  ✓ archived  .claude/specs/in-progress/2026-01-04-old-feature.md -> .claude/specs/completed/
  ✗ skipped   scratch-notes.md (user declined)
  ! failed    Thumbs.db (permission denied)
```

If a destination directory does not exist (e.g. `output/drafts/` in a workspace where the user never created it), create it on the fly with a `.gitkeep` if it'd otherwise be empty.

## Step 4 — Append to Checkpoint.md

Record what was done at the bottom of the Checkpoint.md log as a new entry:

```markdown
## YYYY-MM-DD — Workspace cleanup

- Archived 2 stale specs to .claude/specs/completed/
- Moved 1 stale draft to content/drafts/_stale/
- Moved 2 loose outputs to output/drafts/
- Deleted 3 junk files
- Surfaced 1 duplicate for manual resolution

No client material touched. No scaffolding files modified.
```

If `Checkpoint.md` does not exist, skip this step — flag as a workspace scaffolding gap.

## Step 5 — Report

Print the actions summary + a one-line follow-up suggestion:

```
Cleanup complete. 9 actions taken, 0 failures.

Suggestions:
  - Resolve the duplicate roadmap.md manually (root vs tasks/).
  - Consider deleting legacy/ if you no longer need it.
  - Run /workspace-cleanup monthly to keep this tidy.
```

## Ground rules

- **Intent Clarification:** if the audit surfaces something ambiguous (file with no clear category, file that could be content OR a spec), ask once. Do not guess.
- **Least Complexity:** seven categories is the ceiling. Do not invent new heuristics on the fly.
- **Surgical Execution:** never delete a non-junk file. Never move out of `clients/`. Never touch the eight scaffold files (RULES, CLAUDE, ARCHITECTURE, GOALS, PLANNING, MEMORY, Checkpoint, handoff). If the user says "delete CLAUDE.md", refuse and recommend `/super-setup` for a clean re-scaffold.
- **Declarative Focus:** Definition of Done is "workspace passes the same audit cleanly on a second pass". If the user asks for things outside the audit categories (rewrite ARCHITECTURE.md, generate a sitemap), spin them out.

## Environment notes

Pure Read/Glob/Write. No Bash. Identical behavior in Code and Cowork. Junk-file detection is pattern-based — Cowork's lack of `find` doesn't matter because Glob handles it.

## Relationship to /session-closeout

- `/session-closeout` runs at end of session, audits the workspace, ADVISES the user. Non-destructive.
- `/workspace-cleanup` is the same audit logic but ACTIONS on findings. Destructive (with confirmation).

The two skills share the audit categorization but diverge on what they do with findings. P3 implementation extracts the audit into a shared helper that both skills call — but that refactor is a P4 concern. For P3, duplicate the audit logic inside `workspace-cleanup` SKILL.md text and reconcile later.
