---
name: update-everything
description: Use to update every Claude extension layer at once — marketplaces, plugins, npx skills (global and project), and the Claude Code CLI itself — and to find things sitting stale or silently broken. Trigger phrases include "update everything", "update my plugins", "are my plugins current", "am I behind", "check for updates", "update my skills", "everything up to date?", "/update-everything". Also use when a plugin behaves like an older version, or before a client call where stale skills would embarrass you.
---

# update-everything

There is no single "update all" command in Claude Code. The real surface is five separate tools, one of which (`claude plugin update`) has **no bulk mode** and must be looped one plugin at a time, and the order between them is invisible and easy to get backwards. This skill is that missing command.

**Voice:** plain English, no jargon dumps. The user should never have to know which tool owns which layer.

## Step 0 — Explain, if they're new to this (teach check)

Explain when teach mode is BEGINNER (default) **or** `.claude/workspace.yml` has `verbosity: beginner`. Skip when they've said "standard mode" and the workspace isn't pinned beginner.

> *"Your Claude add-ons come from a few different places — plugins, marketplaces, skills, and Claude Code itself — and each one updates separately. This runs all of them in the right order, tells you what actually changed, and points out anything sitting stale or broken. Takes a couple of minutes. What this means for you: no more finding out on a client call that you've been four versions behind."*

## Step 1 — Preflight

Check `claude` and `npx` resolve. **A missing tool degrades, never blocks** — if `npx` is absent, say so once and still do the plugin work. Report what you'll be able to cover before starting.

## Step 2 — Marketplaces FIRST (order is load-bearing)

```
claude plugin marketplace update
```
No name = all marketplaces. **This must run before any plugin update.** Skip it and plugins resolve against a stale index and report "already current" when they are not — the single most common cause of a phantom-successful update.

## Step 3 — Snapshot before

```
claude plugin list
```
Parse each entry: `name@marketplace`, `Version:`, `Status:`. Keep this as the BEFORE state — the final report is a diff against it, not a wall of command output.

Three states to handle correctly, none of which mean "fine":
- **`Version: unknown`** — the plugin ships no version string. It is neither current nor broken. Update it, then label it `unknown → unknown (no version published)`. Never count it as up to date.
- **Git-SHA versions** (12-hex, e.g. `0427b5b1281b`) — normal for source-tracked plugins. A changed SHA IS an update; report it as "updated (new build)".
- **`Status: disabled`** — skip it, and name it in the report as skipped-because-disabled. Updating a disabled plugin is wasted work and confusing output.

## Step 4 — Update plugins (the loop)

`claude plugin update` takes a required `<plugin>` argument and has no `--all`. Loop over the enabled plugins from Step 3:

```
claude plugin update <name>@<marketplace>
```

**Never abort the batch on one failure.** Capture each result; a single plugin erroring must not cost the other fifty.

**Duplicates:** the same plugin installed from more than one marketplace (e.g. `superpowers` from three) is a finding, not a loop iteration. **Stop and surface it** — show the marketplaces and versions and ask which to keep. Blindly updating all copies leaves the user with several versions of the same thing and no idea which one is loading.

**Stalls:** if a plugin reports success but the version does not move, say so plainly and give the fix inline — refresh that one marketplace (`claude plugin marketplace update <name>`), retry the update, and if it still will not move, the version registry (`~/.claude/plugins/installed_plugins.json`) is pinning it and a reinstall of that plugin is the fix. Report it; do not attempt registry surgery.

## Step 5 — Plugins the CLI cannot see (do not skip this)

**Some plugins are installed through Claude Desktop's Customize panel and do not appear in `claude plugin list` at all.** The CLI cannot read or update them. If you only loop Step 4, those go stale forever while the report says everything is current — the exact failure this skill exists to prevent.

Detect them: compare the skills actually loaded in this session (their `plugin-name:skill-name` prefixes) against the Step 3 list. Any plugin prefix that is loaded but absent from `claude plugin list` lives on the Desktop surface.

Name every one of them, then hand off:

> *"These N plugins are installed through Claude Desktop, so this command can't reach them: [names]. To update them: open Claude Desktop → Customize → Skills → find each one → Update. Same restart rule applies."*

## Step 6 — npx skills, both scopes

```
npx skills check
npx skills update -g     # global (user-level) skills
npx skills update -p     # project skills, when in a project
```
Run `check` first; only update what it reports stale. Cover **both** scopes — a workspace can hold project-level skills that global updates never touch.

## Step 7 — Workspace-local health (what version checks miss)

Local skills in `.claude/skills/` have no version and no update path — they go stale invisibly and can be **silently broken**. Check both:

1. **Frontmatter parses.** Every `.claude/skills/*/SKILL.md` must have YAML frontmatter that parses, with `name` and `description`. The classic killer is an **unquoted colon inside `description`** ("Trigger phrases: ..."), which makes the whole frontmatter fail to parse — the skill then loads with EMPTY metadata and its triggers silently never fire. It looks perfectly fine when read by a human. Report any file that fails, with the fix: quote the description or remove the bare `: `.
2. **Superseded copies.** A local skill whose name matches an installed plugin is very likely an old copy that the published plugin has replaced. Name it and ask — never delete it yourself.

## Step 8 — The report (this is the deliverable)

Diff Step 3's snapshot against a fresh `claude plugin list`. Lead with what changed. Structure:

- **Updated** — `name: old → new`, one line each
- **Already current** — a count, not a list
- **Needs your attention** — duplicates, stalls, `unknown` versions, disabled skips, broken local frontmatter, Desktop-only plugins
- **Nothing changed?** Say exactly that in one line. Silence is a valid, good result.

Never paste raw command output as the report.

## Step 9 — Restart (say this every single time, even when nothing changed)

> *"Plugin updates don't take effect until Claude restarts. Fully quit — system tray → Quit, not just closing the window — and reopen. Until you do, you're still running the old versions."*

This is load-bearing. A user who skips the restart sees "updated", gets old behavior, and reports a bug that does not exist.

## Step 10 — Offer the extras (ask, never auto-run)

Two things this skill will not do without an explicit yes, because both change more than a version number:

- **`claude plugin prune`** — removes auto-installed dependencies no longer needed. Offer `claude plugin prune --dry-run` first so they see what would go.
- **`claude update`** — updates the Claude Code CLI itself. Always a separate, explicit ask.

## Step 11 — Offer to make it recurring

The whole point is that nobody remembers to run this. After a successful run, offer the routine — **never create it silently**:

> *"Want me to run this for you every week so you never fall behind again? I'll only message you when something actually changed."*

Ask two things, then build it:
1. **Cadence** — weekly is the default. Daily is noise; monthly means running months-stale plugins.
2. **What to hear back** — a short summary of what changed, and silence when nothing did.

Build it with the **`/schedule`** capability (cloud routines survive a closed laptop). `/loop` is the wrong tool — it is session-scoped and dies with the window.

Pick an **off-peak, non-round** time. Everyone who asks for "weekly" gets Monday 9am, which is exactly when marketplaces are busiest — `17 6 * * 2` (Tuesday 06:17) is a better default. Say why in one line so it does not look arbitrary.

The routine's prompt must be **self-contained** — it fires with no conversation to remember. Have it: run this skill's sequence, report only changes, and stay silent on a no-change week.
