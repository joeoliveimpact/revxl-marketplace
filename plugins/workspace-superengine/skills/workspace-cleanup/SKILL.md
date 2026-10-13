---
name: workspace-cleanup
description: Use to aggressively tidy a workspace — archive completed specs, list drafts (each moves only if picked one by one), reorganize folder clutter, prune outdated entries from PLANNING.md / handoff.md. Trigger phrases include "this workspace is messy", "let's tidy up", "too many files", "clean this up", "archive the old stuff", "/workspace-cleanup". Heavier than session-closeout's lightweight per-session audit.
---

# workspace-cleanup

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> Time to tidy up. I'll look through your workspace for completed work, stale files, and clutter ... then ask before moving anything. Nothing gets deleted: junk goes to a recycle bin folder (`_recycle-bin/`) with a note of where it came from, and nothing moves without your say-so.

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

Walk the workspace and build a categorized findings list. Audit is Glob + Read. Moves and quarantines need Bash `mv` (Code only); in Cowork, present the plan and stop.

Categories:

### A. Stale specs (if `code` module installed)

- `.claude/specs/in-progress/*` whose contents include a "shipped" / "completed" / "done" marker → candidates for archive to `.claude/specs/completed/`.

### B. Stale drafts (if `content` module installed)

- `content/drafts/*` → every draft is listed in the plan, and `all` or a category pick never moves one. A draft moves only when the user picks that draft per item. A draft whose contents carry a "published" / "shipped" marker is labelled `offer`: if picked, it moves to `content/published/` when the user confirms it shipped, otherwise to `content/drafts/_stale/`. A draft with no marker is labelled `keep`: it stays put unless the user picks it per item, which archives it to `content/drafts/_stale/`.

### C. Loose outputs

- Files in workspace root that match output-y patterns (`*.draft.md`, `output*.md`, `notes-*.md`, `tmp-*`, `scratch*`) → candidates for move to `output/drafts/`.

### D. Junk patterns

- `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.swp`, `*.bak`, `~$*`, `*.orig`, empty `.gitkeep` in directories that no longer need one → candidates for quarantine to `_recycle-bin/` (never deleted; contract: `${CLAUDE_PLUGIN_ROOT}/docs/recycle-bin.md`).

### E. Empty / vestigial directories

- Top-level dirs containing only `.gitkeep` and nothing else, that aren't required by the scaffold. Surface, don't delete by default.

### F. Stray docs in root

- `*.md` files in workspace root that aren't in the scaffold whitelist (RULES, CLAUDE, ARCHITECTURE, GOALS, PLANNING, MEMORY, Checkpoint, handoff, README, CHANGELOG, LICENSE). Candidates for move to `output/drafts/` or `tasks/`.

### G. Duplicate / near-duplicate files

- Same basename in multiple locations (e.g. `roadmap.md` in root AND in `tasks/`). Surface for user resolution.

Skip entirely:

- Anything inside `clients/`, `_recycle-bin/`, `.git/`, `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`.
- Anything matching `.gitignore` patterns if a `.gitignore` exists at root.

## Step 2 — Present the plan

Group findings by category. For each, propose an action. Display like:

```
Workspace cleanup plan (dry run):

A. Stale specs (3)
   archive  .claude/specs/in-progress/2026-01-04-old-feature.md  -> .claude/specs/completed/
   archive  .claude/specs/in-progress/2026-02-15-shelved.md      -> .claude/specs/completed/
   keep     .claude/specs/in-progress/2026-04-30-recent.md       (no shipped marker)

B. Drafts (2, listed only; "all" and "category" skip them)
   keep     content/drafts/2025-12-old-essay.md  (no published marker; only if picked per item) -> content/drafts/_stale/
   offer    content/drafts/launch-post.md        (published marker; per item only) -> content/published/ if it shipped, else content/drafts/_stale/

C. Loose outputs (2)
   move     scratch-notes.md  -> output/drafts/
   move     output-v3.md      -> output/drafts/

D. Junk (4)
   quarantine .DS_Store
   quarantine Thumbs.db
   quarantine tmp-debug.bak
   quarantine ARCHITECTURE.md.orig

E. Empty directories (1)
   keep     legacy/  (surfaced, no action — delete manually if intentional)

F. Stray docs (2)
   move     meeting-notes-2026-03.md  -> tasks/
   move     idea-draft.md             -> output/drafts/

G. Duplicates (1)
   surface  roadmap.md in / AND tasks/  (resolve manually)

Total: 11 actions proposed (2 archive, 4 move, 4 quarantine, 1 surface); drafts are per item only.

Proceed? Options:
  all       - apply everything above except drafts (B is per-item only)
  category  - pick categories to apply
  per-item  - confirm each action
  cancel
```

Default to `per-item` if the user is silent. The Surgical Execution rule means we never act in bulk by default.

## Step 3 — Execute approved actions

Run the chosen actions in this order: archives and moves first, quarantines last.

Quarantine each junk file as `${CLAUDE_PLUGIN_ROOT}/docs/recycle-bin.md` specifies, following the quarantine steps in `${CLAUDE_PLUGIN_ROOT}/skills/session-start/SKILL.md` (the legacy `RULES.md` migration): create the bin if it is missing, move the file into today's `_recycle-bin/<YYYY-MM-DD>/` folder (collision suffix before the first dot), and append its six-column manifest row in the same pass. Never delete a file.

For each action, log:

```
  ✓ archived  .claude/specs/in-progress/2026-01-04-old-feature.md -> .claude/specs/completed/
  ✗ skipped   scratch-notes.md (user declined)
  ! failed    Thumbs.db (permission denied)
```

If a destination directory does not exist (e.g. `output/drafts/` in a workspace where the user never created it), create it on the fly with a `.gitkeep` if it'd otherwise be empty.

## Step 4 — Append to Checkpoint.md

Record what was done as a new entry, written with the Edit tool (as `/session-closeout` does) and inserted directly before the first line that starts with `## ` (the current newest entry), the same anchor `/session-closeout` uses. If that exact heading line occurs more than once in the file, extend `old_string` (and the end of `new_string`) with the lines that follow it until it is unique; the Edit tool needs a unique match. If the file has no `## ` line yet, append the entry at the end. Never rewrite the file through a shell command (a heredoc or a script): that changes its line endings.

```markdown
## YYYY-MM-DD — Workspace cleanup

- Archived 2 stale specs to .claude/specs/completed/
- Moved 1 stale draft to content/drafts/_stale/
- Moved 2 loose outputs to output/drafts/
- Quarantined 3 junk files to _recycle-bin/<YYYY-MM-DD>/ (manifest rows added)
- Surfaced 1 duplicate for manual resolution

No client material touched. No scaffolding files modified.

---
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
- **Surgical Execution:** never delete any file; removal is a quarantine with a manifest row. Never move out of `clients/`. Never touch the eight scaffold files (RULES, CLAUDE, ARCHITECTURE, GOALS, PLANNING, MEMORY, Checkpoint, handoff). If the user says "delete CLAUDE.md", refuse and recommend `/super-setup` for a clean re-scaffold.
- **Declarative Focus:** Definition of Done is "workspace passes the same audit cleanly on a second pass". If the user asks for things outside the audit categories (rewrite ARCHITECTURE.md, generate a sitemap), spin them out.

## Environment notes

Audit is Glob + Read, identical in Code and Cowork. Moves and quarantines need Bash `mv` (Code only); in Cowork, present the plan and stop. Junk-file detection is pattern-based, so Cowork's lack of `find` doesn't matter: Glob handles it.

## Relationship to /session-closeout

- `/session-closeout` runs at end of session, audits the workspace, ADVISES the user. Non-destructive.
- `/workspace-cleanup` is the same audit logic but ACTIONS on findings: moves and quarantines, with confirmation. Nothing is deleted; removal is a quarantine with a manifest row.

The two skills share the audit categorization but diverge on what they do with findings. P3 implementation extracts the audit into a shared helper that both skills call — but that refactor is a P4 concern. For P3, duplicate the audit logic inside `workspace-cleanup` SKILL.md text and reconcile later.
