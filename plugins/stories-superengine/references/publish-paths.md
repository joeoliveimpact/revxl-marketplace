# Publish paths — getting frames onto Instagram + Facebook Stories

Use what the coach already has. Check in this order and take the first that works.

| Route | What it does | How Claude reaches it |
|---|---|---|
| **metricool-connector** | Schedules ONE Story post holding every frame, on Instagram AND Facebook | Metricool's own Claude connector (Customize → Connectors). Find its tools with ToolSearch: `metricool scheduled post` / `brand settings`. |
| **metricool-composio** | Same as above | composio toolkit whose name contains `metricool` (`publish.py detect`). |
| **instagram-direct** | Posts to Instagram Stories **right now**, one frame at a time. No schedule, no Facebook. | composio `instagram` toolkit. |
| **drafts-only** | Frames saved to the folder; the coach posts by hand | always available |

Facebook Stories only go out through Metricool. Instagram's API alone can't schedule a story and has
no sticker or link fields.

## Hosting (Metricool and Instagram both need a public link)

Neither service takes a file upload; each fetches the frame from a URL.
- **composio Google Drive** (`googledrive` toolkit): upload, then share "anyone with the link" as a
  reader. Proven. 5 MB per file limit on this upload, fine for frames, small for long video.
- **gws CLI**, when the coach has it: same result.
- Link form: `https://drive.google.com/uc?export=download&id=<id>`.
- `host` writes `hosted.json`: a list of `{file, drive_id, url, content_type}` in frame order.
  `schedule` reads only `url`, in that order.
- **Before anything schedules, the link must answer `image/*` or `video/*`.** A `text/html` answer
  means the share failed. Metricool then fails with "Failed to normalize media". `publish.py host`
  stops on it.

## Metricool payload (built by `publish.py schedule`)

- Top level: `blogId` (the brand id as a string), `date` (ISO with the UTC offset **for that date**,
  so daylight saving is right), `info` (a JSON *string*).
- `info.media`: the frame links in order. Several frames in one post publish as one story sequence,
  order kept. PNG and MP4 can mix.
- `info.providers`: `instagram` and/or `facebook`. `instagramData.type` and `facebookData.type` = `STORY`.
- `autoPublish: true` posts by itself. `false` (`--manual`) makes Metricool ping the coach's phone at
  post time instead: the only way to add Instagram music to a story, since the API can't.
- `instagramData.isAiGenerated`: true when any frame uses a generated image.

### Through the Claude connector

Call the connector's create-scheduled-post tool with exactly the three fields from
`metricool-payload.json` (`blogId`, `date`, `info`). Read the brand id from its brand-settings tool.

## Gotchas measured on a live account

- Metricool gives a post a **new id on every edit**. Read back by date, not by an old id.
- There is no delete through the API. A replaced post can only be set to draft. Fix it in Metricool's app.
- The read-back tool takes `brandId`, `fromDate`, `toDate` (with offset) and `timezone`, and rejects
  dates with no offset.
- composio sometimes writes a big answer to a file instead of printing it. `publish.py` reads it back.
- A composio `--dry-run` can pass with no live connection. Only a real read (like `brands`) proves it.
- Pass `gws` and `composio` their arguments as a list. A shell string on Windows mangles the JSON and
  the share silently fails.
- Story numbers sync late: often over an hour after posting. Instagram insights need 1,000+ followers.
- Metricool's free plan allows one custom connector at a time.

## Instagram direct (`publish.py instagram ... --confirm-live`)

- Instagram takes JPEG only; the script converts PNG frames first.
- Each frame is two calls: create the story container, then publish it. It goes live immediately.
- Only after the coach says go, and only when Metricool isn't available.
