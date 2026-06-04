---
name: add-1on1-call-to-history
description: Use when ONE already-identified 1:1 client call needs adding to that client's pinned "Call History" post in their private REVXL (clientclub.net) channel — you already know the call AND the client — e.g. "add Sarah's latest call to her history", "put yesterday's Marcus call in his history", "log this 1:1 in {client}'s call history", or a webhook carrying a specific 1:1 recording. For group-call deep posts use create-fathom-deep-post; to find/scan which calls go where (you don't yet know), use update-client-1on1-history.
---

# add-1on1-call-to-history

Append ONE 1:1 call as an enriched entry to a client's pinned "Call History" post. **Prepend, never replace** — every existing entry, the Calendly header, the pin, and comments must survive.

## When to use
- A known 1:1 call belongs in a known client's history.
- Webhook with `{client, recording_id}` on a new 1:1 recording.
- **Not** for group calls → `create-fathom-deep-post`. **Not** for "figure out where this call goes" → `update-client-1on1-history` (it calls this skill).

## Inputs
- `client` (name) + `recording_id` (or Fathom URL). Optional `post_id` to skip resolution.

## Procedure
1. **Platform + token.** Detect OS, load `config.json`, mint token, `doctor`. `../_fathom-revxl-shared/pipeline.md` §0–1.
2. **Resolve channel + Call-History post.** channel-map → client's ` - 1:1` channel (apply aliases; Dana Whitfield has no suffix) → `list-pinned-posts` → the "Call History" post. None found → STOP, queue, ask the operator (no auto-create). §6.
3. **Read existing post content** (`groups posts get … --json` — NOT `--agent`). Keep it in-memory. §2.
4. **BACK UP** the current post content to disk before going further (`…-backup-pre-{date}.json`). Non-negotiable — this is the guardrail from a prior destructive-overwrite incident. `1on1-format.md` §Safety.
5. **Dedup.** If this call's date or shareUrl already appears in the post → STOP (already logged).
6. **Fetch** summary (`get_meeting_summary`), share URL (curl+regex), Drive transcript (graceful-missing → drop 📜). §4–5.
7. **Render ONE entry** per `../_fathom-revxl-shared/1on1-format.md` + exemplar `../_fathom-revxl-shared/exemplars/1on1-history.example.html`. Match the client's existing entry format variant if they have one (Surgical Execution).
8. **Prepend** the new entry: insert below the Calendly header as the newest entry, with `<hr>` separators, preserving ALL existing entries + header verbatim.
9. **UPDATE_POST** (`{action:UPDATE_POST, post:{id, content}}`) via UTF-8 no-BOM stdin. §2–3. Don't change title/pin/visibility.
10. **Verify** — readback; confirm new entry present, header + prior entries intact, `lastEditedAt` fresh, pin unchanged.

## Quick reference
```
<clientclubBinary> groups channels update-post <loc> <grp> <chn> <postId> --stdin --agent < <payload.json>
# payload: {"action":"UPDATE_POST","post":{"id":"<postId>","content":"<full new HTML>"}}
```

## Common mistakes
- **Replacing instead of prepending** — the exact mistake from a prior destructive-overwrite incident. The post is a *running history*; add one entry, keep the rest. If you're rebuilding the whole body, re-read existing entries first and carry them forward.
- **Skipping the backup** before UPDATE. Always back up first.
- **Dropping the Calendly header** or changing the title/pin. Preserve them.
- **Normalizing other entries' formatting** — only touch the new entry; match the client's existing variant.
- **`Get-Content -Raw` round-trip** corrupting emojis → use `[IO.File]::ReadAllText` UTF-8. pipeline.md §7.

## References
- `../_fathom-revxl-shared/pipeline.md` — auth, fetch, post, channel resolution, traps
- `../_fathom-revxl-shared/1on1-format.md` — locked entry format + safety rule
- `../_fathom-revxl-shared/exemplars/1on1-history.example.html` — canonical body
- `../_fathom-revxl-shared/config.json` — paths + IDs
