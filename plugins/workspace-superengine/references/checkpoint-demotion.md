# Checkpoint demotion — the 30-day window

Read this at Phase 1, immediately after inserting the new Checkpoint entry. It runs every closeout. **Never dump this file at the user** ... but the retained count in it is spoken out loud, every time.

---


Do this every closeout, right after inserting the new entry. **Closeout owns this, not a scheduled job** ... Checkpoint has to work before any graph exists, and the scheduled night job that would otherwise own it does not exist yet.

1. **Full zone (top of the file):** every entry from the last 30 days, newest first, complete with burst, handle and terms.
2. **Floor of 5.** The full zone always keeps at least the 5 newest entries, even when all of them are older than 30 days. A quiet month cannot empty the top of the file.
3. **Tail (below the full zone, same file):** everything else, one line each, newest first:

   ```
   - 2026-07-02 · Linear source-of-truth rule → [[session-summary-07-02-26]] · terms: linear, source of truth
   ```

4. **No second archive artifact.** The tail lives in `Checkpoint.md` under a `## Earlier sessions` heading at the bottom of the file. Do not create an archive file, do not move anything to another folder.
5. **Ordering:** the full zone stays newest-first, then `## Earlier sessions` last, also newest-first. An old entry that cannot be compressed (see below) stays in the full zone, in date order, which means the full zone can run past 30 days. That is intended, not a bug to tidy up.

**Compress ONLY entries that have a resolvable `**Summary:**` handle.** An entry written before session summaries existed has its body in exactly one place, and compressing it to one line destroys the only copy. Those stay full, however old they are, and they do not count against the floor. Converting them is the backfill's job, and **the backfill is blocked until deletions are recoverable** ... do not attempt it here, do not attempt it partially, and do not "just do the top few".

**Say out loud how many entries you retained for having no handle. Every closeout, including ... especially ... when the answer is "all of them."**

A file with no handles anywhere compresses nothing, and a demotion step that compresses nothing and reports nothing looks exactly like bloat control working. It is not working; it is waiting on the backfill. The user has to be able to tell those apart, and the only thing that distinguishes them is this line.

- **Some compressed, some retained:**
  > Compressed 12 older entries to one-liners. Another 9 predate session summaries and have no handle, so I left those in full ... they stay that way until the backfill is unblocked.
- **Nothing compressed, everything retained** ... the case for any workspace that has been running since before this format existed:
  > Nothing could be compressed this time: all 47 entries in `Checkpoint.md` predate session summaries, so none of them has a handle to compress down to. The file will keep growing until the backfill converts them, and the backfill is blocked until deletions are recoverable. From today forward, new entries carry a handle and will compress normally.

**Silence here is a defect, not a clean result.** Report the count even when it is zero in the other direction (nothing retained, everything compressed) ... that is one short line and it is the only evidence the step ran at all.

If demotion would compress an entry whose handle points at a file that is not on disk, leave it full and say so:

> One older Checkpoint entry points at a session summary I could not find, so I left it in full rather than compressing it down to a link that goes nowhere.
