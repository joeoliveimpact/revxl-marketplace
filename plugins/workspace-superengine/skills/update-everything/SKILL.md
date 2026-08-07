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

**Also check for pins here, before updating anything.** For each entry, compare its `installPath` against the directories actually present in `cache/<marketplace>/<plugin>/`. A newer directory sitting there unused means the registry is pinned to an old version while the new one is already downloaded — that IS the diagnosis, in one read, and no command was needed to find it.

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

### Verify every update — the leg nobody checks

`claude plugin update` printing `updated from X to Y` is the OUT leg. **The registry actually changing is the BACK leg, and nothing checks it by default.** That is why a repair can "work" without anyone knowing which part worked.

After each update, **read `~/.claude/plugins/installed_plugins.json` back** and compare `version` + `installPath` against the snapshot. Report per plugin what actually moved, not what the command claimed.

### The repair ladder — climb one rung at a time, and name the rung that worked

Field-validated 08.04.26 on 7 pinned plugins: **rung 1 fixed 7 of 7.** Rungs 2 and 3 were never needed. Do not skip ahead.

| Rung | Action | Escalate when |
|---|---|---|
| 0 | `claude plugin marketplace update` (Step 2 — already done) | never sufficient alone |
| **0.5** | **Transport check — see below. Branch out of the ladder entirely if it fires.** | — |
| 1 | `claude plugin update <name>@<mkt>` → **read the registry back** | version unchanged in the registry |
| 2 | `claude plugin uninstall` then `install` (rewrites the registry; also repairs a missing or orphaned cache dir) | still unchanged |
| 3 | back up `installed_plugins.json` → minimal targeted edit → read back → **auto-rollback on any mismatch** | mismatch after rollback → stop, escalate with the captured state |

**Always report which rung fixed each plugin.** "Fixed" without naming the rung is the exact failure this replaces.

### Rung 0.5 — transport failure is NOT a pin. Never climb the ladder for it.

If an update fails with `Permission denied (publickey)`, `Could not read from remote repository`, or `Failed to clone repository`, the plugin is **not** pinned — the fetch never happened.

Cause: a catalog entry of the form `{"source": "github", "repo": "owner/name"}` resolves to **SSH** (`git@github.com:`). Without an SSH key for GitHub, the clone fails. This is independent of the marketplace clone's own remote, which may well be HTTPS.

Fix — retry the same command with HTTPS preferred:
```
CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin update <name>@<marketplace>
```

**Climbing the ladder here is harmful:** rung 2 re-clones and hits the identical failure, and rung 3 would point the registry at a version that was never downloaded. (Found live: `cli-printing-press` sat at 4.6.1 for months against a published 4.30.1 — 24 versions — purely because of this.)

### Orphaned-but-newer cache dirs

A newer version directory sitting in `cache/<mkt>/<plugin>/` carrying an `.orphaned_at` marker means the new version was downloaded, never adopted by the registry, then marked for garbage collection. It is deleted after ~7–14 days. **Fix the pin before then**, or the case degrades into a missing-cache-dir that only rung 2 can repair. Six of the seven plugins in the live test were in exactly this state.

## Step 5 — Cowork-installed plugins: a third store nothing local can reach

There are **three** plugin stores, they hold different versions, and either of the first two can be the stale one:

| Store | Path | Who loads it | Reachable from here? |
|---|---|---|---|
| CLI registry | `~/.claude/plugins/installed_plugins.json` + `cache/` | Claude Code CLI, Desktop **Code tab** | ✅ Steps 2–4 |
| **Cowork / agent-mode** | `…/local-agent-mode-sessions/<id>/rpm/plugin_<id>/` | Desktop **Cowork tab** | ❌ **No** |
| Display cache | IndexedDB in the Claude app-data folder | the plugins panel only | n/a |

**Cowork plugins are served as ZIPs from Anthropic's cloud, not from the local marketplace clones**, and **the Cowork copy shadows the CLI copy** when both exist. Anthropic's backend snapshots the marketplace repo at registration and never re-pulls ([#69683](https://github.com/anthropics/claude-code/issues/69683), open); remove-and-re-add is deduplicated server-side, so it does not reset the snapshot either.

**Never claim the terminal run updated these.** It did not, and it cannot.

Detect them: compare the plugin prefixes of skills loaded in this session (`plugin-name:skill-name`) against the Step 3 list. Any prefix loaded but absent from `claude plugin list` is Cowork-installed. Cross-check against `rpm/manifest.json` — an entry missing `updatedAtVerified` while its siblings have it marks an orphaned snapshot, and a `marketplaceName` pointing at a catalog that no longer lists that plugin proves the snapshot is stale.

Report them as their own group, honestly:

> *"N plugins are installed through Claude Desktop's Customize panel: [names]. Those are served from Anthropic's side and nothing on this machine can update them — including what I just ran. The Update button in Customize is also unreliable for the same reason. The one thing that works: remove the plugin in Customize → Skills, which makes Cowork fall back to your CLI copy (which IS current now). Leave it removed — re-adding it re-enables the stale copy."*

## Step 6 — npx skills, both scopes

```
npx skills check
npx skills update -g     # global (user-level) skills
npx skills update -p     # project skills, when in a project
```
Run `check` first; only update what it reports stale. Cover **both** scopes — a workspace can hold project-level skills that global updates never touch.

## Step 7 — Loose-skill health, local AND global (what version checks miss)

Skills sitting in a skills folder have no version and no update path — they go stale invisibly and can be **silently broken**. Check **both** locations:

- `.claude/skills/` in the current workspace (project scope)
- `~/.claude/skills/` (global/user scope)

Check both of these in each:

1. **Frontmatter parses.** Every `.claude/skills/*/SKILL.md` must have YAML frontmatter that parses, with `name` and `description`. The classic killer is an **unquoted colon inside `description`** ("Trigger phrases: ..."), which makes the whole frontmatter fail to parse — the skill then loads with EMPTY metadata and its triggers silently never fire. It looks perfectly fine when read by a human. Report any file that fails, with the fix: quote the description or remove the bare `: `.
2. **Superseded copies.** A loose skill whose name matches an installed plugin is very likely an old copy the published plugin has replaced — and the loose copy can shadow or contradict the current one. Name it, say which plugin supersedes it, and ask. Never delete it yourself.

## Step 7.5 — Cache health (and the trap that makes it look worse than it is)

### `.in_use` markers lie unless you cross-check live PIDs

Each cache version directory can hold a `.in_use/` folder of PID lock files. It is tempting to read these as "this is the version currently loaded." **They are not.** They accumulate for months — dead PIDs from long-gone sessions sit alongside the live one, so a naive read reports a plugin "loading three versions at once" and sends someone chasing a bug that does not exist.

Always cross-reference against actually-running processes:
- Windows: `Get-Process claude | Select-Object -ExpandProperty Id`
- macOS/Linux: `pgrep -x claude`

A marker whose PID is not running is a corpse. **Only a marker matching a live PID is evidence of what is loaded.** (Field example: one plugin showed 10 markers on its old version — every one dead, the newest 13 days old — while the single live marker sat on the new version. The plugin was perfectly healthy.)

### Superseded version directories

Every plugin keeps its old version directories after an update. They are scheduled for garbage collection (docs say 14 days, [#77546](https://github.com/anthropics/claude-code/issues/77546) reports ~7 — assume the shorter), but until then they pile up, and they feed a real bug: the loader can pick the **lowest** cached version even when the registry correctly points at the newest.

Report, per plugin: total cache size, how much is superseded, and the count of dead lock files. Measured on one real machine: **12.4 GB total, 8.2 GB superseded (66%), 1,627 stale lock files** — a single plugin holding five dead versions at ~1.5 GB each. ([#81217](https://github.com/anthropics/claude-code/issues/81217) tracks the absence of any prune command; there is no `claude plugin cache prune`.)

**Offer cleanup; never run it unprompted.** Deleting a cache directory is destructive and the grace period exists for a reason — a concurrent session may legitimately still be reading an old version. Before proposing any directory for deletion, require **all three**:
1. it is not the version in `installed_plugins.json`,
2. no live PID holds a lock in it,
3. the user said yes to that specific list.

Show the list with sizes and let them choose. If a directory carries `.orphaned_at`, say that it will be removed automatically anyway and deleting it early only reclaims the space sooner.

## Step 8 — The report (this is the deliverable)

Diff Step 3's snapshot against a fresh `claude plugin list`. Lead with what changed. Structure:

- **Updated** — `name: old → new (fixed by rung N)`, one line each. Always name the rung.
- **Already current** — a count, not a list
- **Needs your attention** — transport failures, duplicates, stalls, `unknown` versions, disabled skips, broken local frontmatter
- **Cowork plugins** — their own group, with the honest "nothing local reaches these" line from Step 5
- **Cache** — one line: total size, superseded size, dead lock count. Offer cleanup only if superseded space is worth reclaiming.
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
