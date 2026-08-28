# Degraded branches — every one of them says something readable

Read this the moment anything in `/session-continue` goes wrong. Every row names what to say out loud. **Never dump this file at the user** ... say the one line that fits.

---


| What happened | What to do |
|---|---|
| **`spawn_task` is unavailable** in this environment | Do not fail, and do not quietly drop the work. Step 3 already wrote the prompt to `sessions/kickoff-MM-DD-YY.md`, so point at that file and print it in a fenced block as well: *"I can't spawn a task chip from here, so tomorrow's opening message is saved at `sessions/kickoff-MM-DD-YY.md` ... open a fresh session and paste it in."* The prompt is the deliverable; the chip is just delivery. |
| **The prompt could not be written to disk** (permissions, read-only path) | Say so plainly, then spawn the chip anyway ... a chip with no file beats no chip. Do not silently skip the write and imply it happened. |
| **Closeout did not complete** | Say which phase stopped and what that costs, then offer the choice. *"Closeout stopped before it rewrote handoff.md, so anything I put on a chip would be yesterday's plan. Want me to finish the closeout first, or spawn a chip that says the handoff is stale?"* Never build silently on a stale handoff. |
| **Closeout had already completed** before this skill was invoked | Step 1's check found `handoff.md` already carrying today's date under `## Last session`. Do not run closeout again ... it is not idempotent, and a second run appends a second Checkpoint entry, writes a second summary file and repoints `handoff.md` at half the record. Ask whether to skip to Step 2 or whether work since then needs its own closeout, and default to skipping. |
| **No `handoff.md` at all** | The workspace is not scaffolded. Say so, point at `/super-setup`, and do not create a handoff from here just to have something to read. |
| **`handoff.md` exists but has no P0 items** | Spawn anyway, with the thin flag and `MISSION NOT SET`. *"There's no P0 in the handoff, so the chip has no mission ... it'll open with the summary and ask you what you want to do. Want to name a first task now instead?"* **Do not invent a mission**, not even an obvious-looking one like "continue yesterday's work". |
| **Session summary missing** (Phase 0.7 could not write it) | Read order falls back to `Checkpoint.md`'s top entry, thin flag set, and the prompt says which file is missing rather than pointing at a path that does not exist. |
| **Two sessions today** ... several `session-summary-MM-DD-YY*` files | Use the one `handoff.md` points at. It is the newest by definition, because closeout just wrote both. |
