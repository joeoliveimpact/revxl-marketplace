---
name: create-fathom-deep-post
description: Use when a single Fathom group/office-hours call needs its own "Full Call Notes" deep post created in a REVXL (clientclub.net) channel — e.g. "deep-post this call", "make Full Call Notes for the Wednesday group call", backfilling a missing group-call post, or a webhook firing on a new group recording. For per-client 1:1 history entries use add-1on1-call-to-history instead.
---

# create-fathom-deep-post

Turn ONE Fathom call into a "Full Call Notes" deep post in a REVXL channel. The rendering is **editorial** — you (Claude) transform the Fathom AI summary into the locked HTML format in-context, using the exemplar as the reference. There is no converter script.

## When to use
- A group call (REVXL/REVUP/Office Hours) needs its own deep post in the Group Calls channel.
- Backfilling or re-creating a single Full Call Notes post.
- Webhook fires with a new group-call `recording_id`.
- **Not** for client 1:1 history → use `add-1on1-call-to-history`. **Not** for routing a batch of calls → use `update-client-1on1-history` (it calls this skill).

## Inputs
- `recording_id` (or Fathom call URL — extract the recording_id via `list_meetings`).
- Optional `channel_id` (default = `config.groupCallsChannelId`).

## Procedure
1. **Platform + token.** Detect OS, load `config.json`, mint token, `doctor`. See `../_fathom-revxl-shared/pipeline.md` §0–1.
2. **Fetch summary** via `get_meeting_summary(recording_id)`. §4a.
3. **Fetch share URL** (curl + regex). §4b. On cookie expiry → stop + report (don't post a deep post with no Watch link).
4. **Resolve Drive transcript** for the call. §5. Missing → omit the 📜 Transcript line (graceful).
5. **Render the body** per `../_fathom-revxl-shared/deep-post-format.md` and the exemplar `../_fathom-revxl-shared/exemplars/deep-post.example.html`. Editorial: flatten sub-bullets with paraphrase, tighten, leading `<hr>` + section/topic `<hr>`s, ▶️ bullets, bold lead phrases. Build the title (`📝 Full Call Notes — …`).
6. **Write body to a UTF-8 no-BOM file**, build `{title, content}` payload, **create-post** via stdin. §2–3.
7. **Capture** the new `_id` (regex the response). Log it (append to a deep-post-ids tracking file if one is in use).
8. **Verify** — readback via `groups posts get … --json`; confirm title + emojis rendered; if first of a batch, eyeball the live render before continuing. §8.

## Quick reference
```
<clientclubBinary> groups channels create-post <loc> <grp> <chn> --stdin --agent < <payload.json>
# payload: {"title":"📝 Full Call Notes — …","content":"<html>"}
```

## Common mistakes
- **Posting without the share URL** when the Fathom cookie expired — you'd ship a deep post with a dead Watch link. Stop and re-auth instead.
- **Mechanical (non-editorial) rendering** — dumping the raw Fathom summary verbatim. The format flattens + tightens; match the exemplar, not the source markdown.
- **Forgetting the leading `<hr>`** or the per-topic `<hr>`s — see the locked `<hr>` rule in deep-post-format.md.
- **PowerShell BOM / emoji / JSON traps** — see pipeline.md §7 before writing any PS.
- **Bulk-posting an unproven format** — round-trip ONE first (pipeline.md §8).

## References
- `../_fathom-revxl-shared/pipeline.md` — auth, fetch, post mechanics, traps (per-platform)
- `../_fathom-revxl-shared/deep-post-format.md` — locked format spec
- `../_fathom-revxl-shared/exemplars/deep-post.example.html` — canonical body
- `../_fathom-revxl-shared/config.json` — paths + IDs
