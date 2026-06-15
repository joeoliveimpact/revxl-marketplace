---
name: update-client-1on1-history
description: Use when Fathom calls must be found/scanned and sorted to the right REVXL (clientclub.net) destinations — i.e. you do NOT yet know which calls or where they go — e.g. "run today's 1:1 sync", "update {Client}'s 1:1 history" (finds + adds their new calls), "update all clients' call history", "process the last 24h of Fathom calls", the daily cron audit, or one unclassified webhook recording. Classifies each call (1:1 / group / ambiguous) and dispatches to the atomic primitives; ambiguous → review queue. To add ONE call you've already identified, use add-1on1-call-to-history (1:1) or create-fathom-deep-post (group) directly.
---

# update-client-1on1-history (router / reconciler)

Scan a set of Fathom calls, **classify** each, and **dispatch** to the right atomic skill. This skill is the brain (routing rules) — it does NOT render or post itself.

- 1:1 call → `add-1on1-call-to-history` (client + recording_id)
- Group/office-hours call → `create-fathom-deep-post` (recording_id) + append an entry to the current week's Group Calls index post
- Ambiguous → review queue (don't guess)

The mechanics (auth, fetch, post, traps) live in `../_fathom-revxl-shared/pipeline.md`. The formats live with each primitive.

## Modes
- **`manual`** — one named client OR a small batch. Scan that client's (or all clients') Fathom calls, diff against existing history, dispatch each new call. Per-client confirm gate at classify in manual mode.
- **`daily`** (the cron audit pass) — scan last 24h–7d, reconcile: any call missing its post/entry → dispatch the right primitive. Auth-checked first via `fathom-revxl-setup verify`. No human gate; ambiguous → queue.
- **`webhook`** — single `recording_id` (± client) in → classify → dispatch one primitive.

## Routing rules (LOCKED 05.26.26)

Title patterns vary: `{Client}`, `{Client} and {Operator}`, case variants, suffixes. Use **case-insensitive client-name substring** + participant signal, not exact regex.

| # | Title shape | Participant check | → Route |
|---|---|---|---|
| 1 | Client name; no "REVXL"/"REVUP" group markers | the operator + ONLY that client (+ optional coach) | `add-1on1-call-to-history` |
| 2 | "Office Hour" AND starts `REVXL`/`{Operator}` | exactly 1 client | Group Calls: `create-fathom-deep-post` + weekly-index entry |
| 2b | "Office Hour" AND starts `REVXL`/`{Operator}` | 0 or 2+ clients | Group Calls (same as #2) |
| 3 | Starts `REVUP ` | (any) | Group Calls (same as #2) |
| 4 | `Impromptu Zoom Meeting` | exactly 1 client + the operator | `add-1on1-call-to-history` |
| 4b | `Impromptu Zoom Meeting` | else | Review queue |
| 5 | None of the above | (any) | Review queue (unknown pattern) |

> Change from the pre-05.28 skill: rules #2/#2b/#3 previously went to the review queue ("group post handling not wired"). They now **dispatch to the Group Calls flow** (deep post + index entry).

### Classification refinements (keep)
- **Pre-onboarding sales calls:** if a call PRE-DATES the client's existing "Onboarding" entry → likely sales/discovery. Surface in classify gate; default exclude.
- **Duration <5 min** (proxy: max timestamp in summary < 300s) → reschedule/quick-touch, SKIP.
- **Name aliases:** `Dana Scanlon Whitfield` → `Dana Whitfield` (channel "Dana Whitfield", no ` - 1:1` suffix). Extend as new variants appear.
- **Known non-clients (skip silently):** `Victor Almeida` (@execexecution.com).

## Workflow

1. **Setup.** Detect OS, load `config.json`, mint token, `doctor` (or `fathom-revxl-setup verify`). `pipeline.md` §0–1.
2. **Pull calls** for the scope: a window (`list_meetings created_after=…`) for daily/all, or all-time for one named client (paginate `next_cursor`).
3. **Per call, apply routing rules** → `{recording_id, decision, target, client?, reason}`.
4. **Diff** against what already exists (read the client's history post / the week's index / channel posts) so re-runs are idempotent — skip calls already posted.
5. **Dispatch** each routed call to its primitive (`add-1on1-call-to-history` or `create-fathom-deep-post`). In manual mode, confirm the classify list with the operator first.
6. **Queue** ambiguous calls to `tasks/1on1-review-queue.md`.
7. **Report / notify.** Daily: write the review queue + (Phase 2) Telegram/Obsidian brief. Manual: summarize to the operator.

## Review queue format
Append to `tasks/1on1-review-queue.md`:
```md
## {YYYY-MM-DD HH:MM} — {mode} run
### Routed
- ✅ {Client/Group}: {recording_id} → {primitive} → {postId}
### Queued for review
- ⚠️ {title} ({date}) — {reason}: {fathom_url}
  - Suggested: {route to X / skip / extend alias map}
```

## Enriching / backfilling existing histories

To upgrade a client's older **bare** entries (date-only links) to the enriched format — or rebuild a whole history — note that each existing entry already carries its Fathom **share token**. Resolve token → recording_id (`../_fathom-revxl-shared/pipeline.md` §4c: `/share/{token}` 302 → `/calls/{slug}` → `get_recording_by_call_id` → recording_id), fetch the summary, and re-render. **Match the client's existing format variant** (`1on1-format.md`) unless explicitly told to normalize all clients to enriched. Preserve each entry's original share token, date text, and any "- Part 2" / "- Onboarding" label. Back up the post before overwriting (read via `--deliver file:` — pipeline.md §7 trap 6); graceful-missing Drive → omit the 📜 link. Bulk overwrite → round-trip ONE first (pipeline.md §8).

## Common mistakes
- **Doing the append/post inline.** This skill only classifies + dispatches. Rendering + posting belong to the primitives (single source of format truth).
- **Non-idempotent re-runs.** Always diff against existing posts/entries first; the daily audit must create nothing when already up to date.
- **Auto-creating a missing 1:1 history post.** If a client has no Call-History post, queue + ask — don't fabricate one.

## References
- `add-1on1-call-to-history` — the 1:1 primitive
- `create-fathom-deep-post` — the group primitive
- `fathom-revxl-setup` — auth/dep verify (daily pre-run)
- `../_fathom-revxl-shared/pipeline.md` — auth, fetch, post, channel resolution, traps
- `../_fathom-revxl-shared/config.json` — paths + IDs
