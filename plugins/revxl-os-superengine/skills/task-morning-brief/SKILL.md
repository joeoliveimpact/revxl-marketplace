---
name: task-morning-brief
description: Use this skill to produce the morning task brief — a prioritized, calendar-aware view of what the user actually needs to do today. Triggers include "morning brief", "what's on my plate today", "give me my brief", "today's priorities", or the scheduled 7am cron firing inside the task-agent. Reads the canonical task store at `~/.claude/revxl-os/tasks.json` (read-only — never writes), pulls today's calendar via GWS MCP if available, prioritizes against known commitments and time blocks, and posts the result to the Telegram `#briefing` topic via the telegram channel's `reply` tool. Designed to be the single piece of output the user reads from their phone before their first call.
---

# task-morning-brief

The output the user reads before their first coffee. One Telegram message in `#briefing`. Tight, prioritized, calendar-aware.

This skill is **read-only against the task store**. All writes go through `task-add`. This skill never edits, deletes, or marks tasks complete.

---

## When this fires

1. **Scheduled** (default 7am local time, configurable via `os-schedule-manage`)
2. **On-demand** — user says "give me my morning brief", "what's on today", "today's plan"
3. **Programmatic** — task-agent calls it after a major collection run if the user asked for "post-collect brief"

---

## Inputs (what this skill reads)

1. **`~/.claude/revxl-os/tasks.json`** — the canonical task store (every open task)
2. **`~/.claude/revxl-os/config.json`** — for user's timezone + Telegram topic IDs
3. **Google Calendar** via `gws-calendar-agenda` skill (if calendar source configured) — today's events
4. **Optional:** `~/.claude/revxl-os/transcripts/`, `dms/`, `portals/` `_meta.json` for "anything new since last brief?" deltas

If any source is unavailable, **degrade gracefully** — never fail the whole brief because one source is offline.

---

## Output: one Telegram message, ~15 lines max

Format:

```
☀️ {greeting} {name}. {date}.

📅 Today
{event 1, time}
{event 2, time}
{event 3, time}
(or: "No meetings today.")

🎯 Top 3 (priority order)
1. {task} — {why this is #1, one phrase}
2. {task} — {why}
3. {task} — {why}

⏱ Time-sensitive
{any task with due_at <= today + 1 day, briefly}

📥 New since last brief
{count} commitments found in transcripts/email/DMs overnight.

Reply with task numbers (e.g. "1 done") or "tasks" for the full list.
```

If empty in any section, omit the section header. Never pad with "Nothing here!" filler.

---

## Prioritization rules

The hard part. In order:

1. **Hard deadlines today** (any task with `due_at` ≤ end of today) → top, tagged ⏰
2. **Calendar prep work** (any task whose text mentions a person/topic in today's calendar events) → next
3. **Promised but no due date** (`source: agent-extract`, `due_at: null`) → ranked by age (oldest first)
4. **User-added** (`source: telegram-tasks` or `direct`, no due_at) → ranked by recency (newest first — user just added them, probably top of mind)

Pick the top 3. Anything beyond #3 goes to "Time-sensitive" if due-soon, otherwise omitted from the brief (but stays in the store).

**Never include:** completed tasks, tasks marked snooze, tasks with `due_at` more than 7 days out (unless user requests "this week's plan").

---

## Calendar awareness

For each top-3 task, check:
- Is there a calendar event today involving the same person? → mark with 👤
- Is there a calendar block of free time long enough for the task? → optionally suggest "do this between 10-11am, you're free"

Don't over-engineer. If the agenda is dense (5+ meetings), just list events and skip suggested time blocks. The user already knows their day is full.

---

## "New since last brief" delta

Read `~/.claude/revxl-os/{transcripts,dms,emails,portals}/_meta.json` for `last_brief_seen_at`. Count items captured since that timestamp.

Output one line: `📥 New since last brief: N commitments captured (M from transcripts, K from email, ...)`.

After producing the brief, write the current timestamp to each `_meta.json` as `last_brief_seen_at`. This is the ONE write this skill does — and it's metadata, not the task store.

---

## Delivery: Telegram via the channel reply tool

When invoked from the schedule trigger:
1. Read `config.telegram.topics.briefing` for the topic ID
2. Build the message string per the format above
3. Call the telegram channel's `reply` tool with `chat_id` set to the briefing topic
4. Confirm in the parent context: "Posted morning brief to #briefing — {N} tasks surfaced."

When invoked on-demand from a Claude Code session (not Telegram):
- Print the same brief in the terminal as plain text
- Also post to `#briefing` if Telegram is configured (so the user sees it on their phone too)

---

## Tone rules

- **Short.** 15 lines max. The user is reading from bed.
- **Specific.** "Call Maya about her funnel review" — not "follow up with client".
- **No moralizing.** Don't say "You have a lot on your plate." Just list it.
- **No emojis except the section markers** (☀️ 📅 🎯 ⏱ 📥 ⏰ 👤). Don't sprinkle.
- **Greeting rotates by day** — not "Good morning" every day. Light variety: "Morning Joe.", "☕ Joe —", "Tuesday up." But pull from a small fixed pool (5-6 options) — never invent something cute.

---

## Failure modes to handle

| Failure | Behavior |
|---|---|
| `tasks.json` empty | Brief still fires: `🎯 Top 3: nothing in your task store. Add some via #tasks.` |
| GWS MCP not configured | Skip the 📅 section entirely; don't mention "calendar unavailable" |
| Telegram channel not active | Print to terminal only; don't error out the schedule |
| Store corrupted | Surface to `#alerts` topic plainly: "Brief skipped: tasks.json corrupted at {timestamp}. Restore from backup." Do not produce a brief from corrupted data. |
| Network down (can't reach Telegram API) | Cache the brief at `~/.claude/revxl-os/.briefs/pending-{date}.txt`, retry next time the agent runs. |

---

## What this skill does NOT do

- **Does not write to `tasks.json`.** Read-only.
- **Does not mark tasks complete.** That's a future `task-complete` skill.
- **Does not send reminders for individual tasks during the day.** That's `task-agent`'s scheduled checks (every 4hr).
- **Does not run task-collect.** Brief should run AFTER nightly collect (1am) — by 7am, the store is fresh. If collect failed overnight, brief surfaces what's in the store as of the last successful run.

Single output. Single channel. Single moment in the user's day. The whole point is *not* to be a notification firehose.

---

## Example output

```
☀️ Morning Joe. Friday May 9.

📅 Today
9:30  Sales call: Maya Reynolds (45m)
11:00 EFI cohort Q&A (1h)
3:00  Sarah onboarding kickoff (30m)

🎯 Top 3
1. Send Maya the funnel diagram before 9:30 — 👤 today's call
2. Review Sarah's intake form — 👤 3pm kickoff
3. Reply to Adams family re: December retreat — promised Tuesday, still open

⏱ Time-sensitive
Cohort Q&A doc due before 11am.

📥 New since last brief: 4 commitments captured (3 transcripts, 1 email).

Reply "1 done" or "tasks" for the full list.
```

That's the whole product. One message. Read in 15 seconds. Decisions made.
