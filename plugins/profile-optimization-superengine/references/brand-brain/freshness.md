# Freshness ... the 7-day heartbeat

A stale brain drifts from how prospects actually talk right now = copy converts worse. Keep it fresh in small increments, never one big stale-then-catchup.

## Stamps
- Every artifact write records `updated_at` (ISO date + time) in that file's header block.
- `voc/index.md` (workspace-level) records per bucket: last-pull timestamp, source, #items mined, decline count, last-offered timestamp.

## Age-on-access
Every consumer (and this skill's router) computes `days_since_update` on read and surfaces it.

## The gate
- **≤7 days:** reuse silently.
- **>7 days:** offer once per session: *"Your voice + topics are N days old ... want a quick update? (~1-3 min, only pulls what's new)"* Decline → proceed with the existing brain, increment the decline count. Never nag on back-to-back builds.
- **Repeated declines / big backlog:** escalate the WORDING only (explain the why: stale VoC = copy drifts from current prospect language = lower conversion; give an honest time estimate from the new-item count; offer "top-patterns quick pass" vs "full re-rank"). Still declinable. Never forced.

## Delta mining
Refresh pulls only what's NEW since the last stamp (calls, posts, threads). Append to buckets, re-rank incrementally ... never re-mine the whole corpus. Weekly-content-bank rebuilds from the delta: entries older than 7 days expire out.

## Auto-refresh offer (at setup)
- **Cowork client** → scheduled task (Fri night / Mon morning / their pick) via scheduled-tasks.
- **Code client** → routine/cron (`/schedule`, or a Windows scheduled task).
- SLA either way: never more than ~7 days stale.

## Teach-and-do
Every freshness prompt carries a one-line WHY (matched to the user's explanation level) while doing the work. The coach learns the VoC principle by using it.
