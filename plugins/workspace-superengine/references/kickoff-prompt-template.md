# Kickoff prompt template — the exact shape 2e assembles

Read this at 2e, once the six fields from 2b are in hand. It is the literal output shape. **Never dump this file at the user.**

---


```markdown
# START LOCALLY → <5 to 8 word mission title>

<thin-flag block, only if 2d fired>

**Workspace:** `<absolute path to the workspace root>`
**Route:** <the single line from 2c>

Run `/session-start` first ... it verifies the override constraints, then reads `handoff.md`, `ARCHITECTURE.md`,
`PLANNING.md` when present, and the newest one or two `Checkpoint.md` entries, then
works through whatever `handoff.md` listed under `Verify before building` and reports
what failed. **It does not read session summaries** ... that one is yours to open, and
it is item 1 below. Then work the mission below.

## Mission

<P0 item 1, verbatim>

Last session: <date> ... <title from the Checkpoint entry>.
Full write-up: `sessions/session-summary-MM-DD-YY.md`

## Deliverable

<the artifact or outcome, or the not-stated line from 2b>

## Read first, in this order

1. `sessions/session-summary-MM-DD-YY.md` ... what happened last session and why (use the exact path from handoff's `## Session summary`, suffix included ... a second same-day session carries `-1`)
2. `<transcript path>` ... the full session log, if one was stamped. Filter to `user`/`assistant` text blocks ... on the one session this was measured against, the rest of the file was tool output. Open it when you need the reasoning behind a decision, not just the decision.
3. `<key file path>` ... <its note from handoff.md>
4. `<key file path>` ... <its note>

## Step 0 ... close these before building

- <decision item, verbatim>
- <decision item, verbatim>

## Hard rails ... verbatim from handoff.md "Verify before building"

- <rail, verbatim>
- <rail, verbatim>

## Skills

1. `/session-start`
2. `<the mode the P0 names>` ... <one clause on why>
```

**Title, when there is no mission to name it after:** `START LOCALLY → <workspace name>, no mission set`. Do not title it after something else in the handoff to make the button look normal ... the button is the first place the user finds out the chip is thin.

**The absolute workspace path is not optional.** A prompt that says "read handoff.md" with no root is unusable in a fresh session that does not know where it is. Same reason the title carries the route instruction: this text gets read cold, by someone with no other context, and every assumption it makes about what the reader already knows is a hole.
