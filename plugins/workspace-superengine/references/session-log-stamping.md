# Stamping the session log path

Read this at Phase 1 when filling the Checkpoint entry's `**Session log:**` line. Needed at exactly one moment. **Never dump this file at the user.**

---


The raw session transcript holds every turn of this session at full fidelity, and it is the one artifact that is *not* a summary of anything. `/session-continue` reads it to recover the reasoning behind a decision, which is precisely what a handoff compresses out. But nothing else on disk records which transcript belongs to which session, so unless this line is written, that link is gone the moment the session ends.

Transcripts live at `~/.claude/projects/<workspace-path-slug>/<session-id>.jsonl`, where the slug is the absolute workspace path with separators replaced by `-`.

**Two ways to identify the file, in order:**

1. **From a session id the environment already exposes.** In Claude Code the scratchpad directory path contains the session id, and the transcript is that id plus `.jsonl`. Verified on Claude Code desktop 08.27.26.
2. **Newest `.jsonl` by modification time** in the project directory, and only when its mtime is within the last few minutes ... a live session's transcript is being appended to right now.

**Then confirm the file exists before writing the path** (Code: `test -f`; Cowork: Glob). Never write a transcript path you did not confirm ... a citation to a file that is not there is worse than no citation, because it reads as though somebody checked.

**If neither method resolves, write what happened instead of a guess:**

```
**Session log:** could not determine (two sessions ran concurrently; newest-by-mtime is unreliable)
```

**Method 2 is unreliable when sessions overlap.** If two are running, the newest transcript may not be this one. Say so on the line rather than stamping a path that might point at somebody else's session.

**Expect these entries to get much shorter than they used to be.** A pre-summary top entry runs about 60 lines. Now the body lives in the Phase 0.7 summary and the entry is a burst plus two pointer lines. **That is the bloat fix working, not information loss** ... the full write-up is one wiki-link away.
