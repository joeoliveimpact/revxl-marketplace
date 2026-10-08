---
name: stories-superengine:stories-schedule
description: "Schedule or post approved story frames: hosts them at a public link, then one Metricool story post on Instagram + Facebook (through Claude's Metricool connector or composio), or Instagram directly when there's no Metricool. Also reads back what's scheduled and whether it published. Only after the coach says go. Trigger phrases include \"schedule it\", \"post it\", \"send it tomorrow at 10\", \"did my story go out\", \"what's scheduled tomorrow\"."
---

> **Compaction guard:** if this conversation was compacted since this skill loaded, invoke it again.
> `publish-result.json` in the set folder means it's already scheduled: read back, never schedule twice.

**Output contract** — in the set folder: `hosted.json` (frame links), `metricool-payload.json`,
`publish-result.json`; then a read-back line per network. Nothing goes out without the coach's go
**in this conversation, for this set and this time**.

## Load
- `${CLAUDE_PLUGIN_DATA}/business-config.md` (`{{PUBLISH_ROUTE}}`, brand id, time zone, media host)
- `${CLAUDE_PLUGIN_ROOT}/references/publish-paths.md` (routes, payload, every measured gotcha)

Scripts run with the recorded Python (see `stories-setup`, "Run a script").

## Steps

**1. Confirm the go.** Say exactly what will happen: "N frames, one story post, Instagram + Facebook,
Fri Oct 9 at 10:00 AM (New York time), posts itself." Wait for a clear yes. A changed time or
frame = ask again.

**2. Same-day check.** Read back the day first (step 6 command). A set already there at that time →
tell the coach and ask before adding another.

**3. Host the frames** (skip for `drafts-only`):
`publish.py host "<set>/frame-1.png" ... "<set>/frame-N.png" --via <composio|gws from {{MEDIA_HOST}}> --out "<set>/hosted.json"`
It stops if any link doesn't serve an image or video. Fix the share, never schedule around it.

**4. Schedule**, by `{{PUBLISH_ROUTE}}`:
- **metricool-composio:**
  `publish.py schedule --hosted "<set>/hosted.json" --when "YYYY-MM-DD HH:MM" --tz "<{{TIMEZONE}}>" --brand-id <id> --toolkit <{{METRICOOL_TOOLKIT}}> [--ai] --out "<set>"`
  Add `--ai` per `{{AI_LABEL}}`: `auto` = when any frame uses a generated image; `on` = always; `off` = never. Add `--manual` only when the coach wants to add
  Instagram music by hand (Metricool pings their phone at post time).
- **metricool-connector:** same command with `--payload-only`, then call the connector's
  create-scheduled-post tool with the three fields in `metricool-payload.json` (`blogId`, `date`,
  `info` as the string it is). Save its answer to `publish-result.json`.
- **instagram-direct:** say "This goes live on Instagram right now, no Facebook." Get a yes for *now*,
  then `publish.py instagram "<set>/frame-1.png" ... --confirm-live`. Frames post in order.
- **drafts-only:** tell the coach where the frames are and the order to post them.

**5. Report.** The post id, the time, and each network's status (PENDING = queued). Remind them of the
DM tool's story-reply trigger for the keyword, if the set ends on one.

**6. Read back** (after the post time, or when asked "did it go out?"):
`publish.py readback --brand-id <id> --date YYYY-MM-DD --tz "<{{TIMEZONE}}>" --toolkit <...>`
(connector route: its get-scheduled-posts tool with `brandId`, `fromDate`/`toDate` WITH the offset,
`timezone`). PUBLISHED on both = done. FAILED or still PENDING well after the time → show the error,
fix in Metricool's app with the coach (there's no delete through the API).

## Never
- Schedule without a go for this exact set and time, or schedule the same set twice.
- Trust an old post id after an edit: Metricool re-numbers a post on every change. Read back by date.
- Use a hardcoded UTC offset: the script computes it for the post's date (daylight saving).
