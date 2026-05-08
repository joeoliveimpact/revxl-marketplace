---
name: ghl-session-closeout
description: Use this skill at the end of every coaching session — when the coach says "wrap up", "close out", "checkpoint", "handoff for next time", "I'm done for today", "save where we are", or when context approaches 50%. Refreshes the workspace state files (follow-up.md, client-roster.md, attention-needed.md, automation-inventory.md) from GHL via MCP, appends a session entry to Checkpoint.md, rewrites handoff.md, logs any wins, and runs a final RULES.md compliance check. Designed for non-tech coaches — confirms before writing each file, narrates progress, celebrates the close.
---

# GHL Session Closeout

Run at the **end of every session**. No skipping the file updates — that's where continuity comes from.

## Prerequisites
- Workspace must exist. If absent → flag: "I don't see a workspace to update. Did we miss running `ghl-workspace-setup`?"
- GHL MCP and Filesystem MCP both connected.

---

## Phase 0 — RULES.md compliance self-check (30s)

Before writing the session log, briefly scan the session for RULES.md violations:
- **Surgical Execution:** any out-of-scope MCP edits this session?
- **Least Complexity:** any over-engineering in automations or skill chains?
- **Intent Clarification:** any assumptions made on ambiguous requests?
- **Bulk operation discipline:** any 5+-record action without explicit confirmation?

If any flagged → note them in the Checkpoint entry under a "RULES violations" section. If clean, no section.

---

## Phase 1 — Refresh state files from GHL (2 min)

Same MCP queries as `ghl-session-pickup` Phase 3, but at session END so trackers reflect what was just done:

```
search_opportunities(stage="any", sort="lastActivity")
search_contacts(tag="client-active", tag="client-onboarding")
search_opportunities(daysInStage>7)
get_workflows(locationId)
```

Update via Filesystem MCP:

### `follow-up.md`
Recompute hot-lead buckets. Items the coach acted on this session should drop out (or move to a different bucket). New leads added during the session should appear.

### `client-roster.md`
Update `Days Since Touch` and re-bucket based on new tags/stages from the session's MCP actions.

### `attention-needed.md`
- Remove items the coach addressed
- Add new ones detected this refresh
- Preserve any manual flags the coach added during the session

### `automation-inventory.md`
If a new workflow was built or modified during the session, add/update its entry:
- Trigger
- Action chain summary
- Build date
- Status (test mode / live)
- Coach's notes ("for new client onboarding")

---

## Phase 2 — Detect wins (1 min)

Scan the session for celebration-worthy events. Common signals:
- A new `client-` tag added (someone enrolled)
- An opportunity moved to `Enrolled` or `Won`
- An automation went live for the first time
- A milestone count hit (5th client, 50th lead, etc.)
- A coach milestone in conversation ("I just hit $X MRR")

For each, append a one-paragraph entry to `wins.md` (newest at top):

```markdown
## {date}
{1–3 sentences capturing what happened, in the coach's voice}
```

Don't fabricate wins. If no real wins this session, skip this phase silently.

---

## Phase 3 — Append Checkpoint.md entry (2 min)

Add a NEW entry at the top, below the format header.

Strict template:
```markdown
## YYYY-MM-DD — {short title}
**Duration:** ~Xh
**TL;DR:** {1–2 sentences}

### Completed
- {what got done — one bullet per concrete accomplishment}

### Decisions
- {decision} — why: {rationale}

### MCP actions taken
- {tagged X contacts} — {tag list}
- {moved Y opportunities} — {from → to}
- {built Z automations} — {names}
- {sent N messages} — {channel + recipient counts}

### Wins
- {also appended to wins.md}

### Files touched
- {workspace file} — {what changed}

### Not done (rolled to handoff.md)
- {item with context for next session}

### RULES violations (only if any)
- {violation + what to do differently}

---
```

Every section gets content or `(none)`. No silent omissions.

---

## Phase 4 — Rewrite handoff.md (2 min)

handoff.md is **rewritten**, not appended. It's the next-session brief.

Template:
```markdown
# Handoff — Next-Session Priorities

## Last session
{date} — {title} (see Checkpoint.md for full entry)

## Status
{1-line system state — pipeline depth, client load, anything notable}

## Blockers
{numbered, or "(none)"}

## P0 — Next Actions
1. {first thing next session should do}
2. {second}

## P1 — Deferred
{items captured but not urgent}

## Verify before doing
- {anything to check before resuming — credentials, MCP, recent automation tests}

## Reminders for the coach
- {anything they need to do outside Claude — book that call, update offer copy, etc.}
```

Rewrite based on what's still open + what we just learned this session.

---

## Phase 5 — Update setup files if needed (variable)

Check whether anything this session changed durable facts:

| File | Update if… |
|------|------------|
| `coach-profile.md` | Niche pivoted, new offer launched, voice updated |
| `offers.md` | Added/removed/repriced an offer this session |
| `pipelines.md` | Coach restructured pipelines or added a stage |
| `kpis.md` | Quarterly review session OR coach reported new metrics |
| `RULES.md` | NEVER edit unless coach explicitly asked |
| `CLAUDE.md` | Workspace-level instruction change requested |

Walk each one quickly. UPDATE or NO CHANGE — never silently skip.

---

## Phase 6 — Memory updates (30s)

If durable facts changed (new offer, niche shift, new MCP install, voice update, business name change), update Claude memory entries so future session-pickups have fresh values without re-reading files.

Memory candidates worth updating:
- Coach name / business name
- Voice notes (1-line)
- Top 3 offer names + prices
- Niche / ICA description
- MCP install status

Use the auto-memory protocol from `~/.claude/CLAUDE.md`.

---

## Phase 7 — Final verification table

Report this verbatim to the coach. Every applicable file gets a row.

```
| File                    | Action     | Reason if NO CHANGE |
|-------------------------|------------|---------------------|
| follow-up.md            | UPDATED    | — |
| client-roster.md        | UPDATED    | — |
| attention-needed.md     | UPDATED    | — |
| automation-inventory.md | ?          | ? |
| wins.md                 | UPDATED/NO CHANGE | {reason} |
| Checkpoint.md           | UPDATED    | — |
| handoff.md              | UPDATED    | — |
| coach-profile.md        | UPDATED/NO CHANGE | {reason} |
| offers.md               | UPDATED/NO CHANGE | {reason} |
| pipelines.md            | UPDATED/NO CHANGE | {reason} |
| kpis.md                 | UPDATED/NO CHANGE | {reason} |
```

If any row is `?` — fix it before reporting complete.

---

## Phase 8 — Celebrate the close

Don't just report and exit. Acknowledge the work.

Examples:
> "Solid session. You moved {N} contacts forward, cleared {M} stuck items, and built that welcome automation. Workspace is saved. Next session, I'll pick up exactly where we left off — see you then."

Or for shorter sessions:
> "Quick one — saved your progress. Top of mind for next time: {handoff.md P0 #1}. See you then."

---

## Quick mode (for short sessions)

If the session was under 15 minutes and touched <3 contacts/files:
- Skip Phase 0, Phase 5, Phase 6
- Write a 3-line Checkpoint entry
- Update handoff.md only if anything blocks the next session
- Skip the verification table; just confirm completion

Don't quick-mode a session that:
- Made automation changes
- Added/removed clients
- Hit a RULES violation
- Resulted in big decisions

Those need the full procedure.

---

## Edge cases

- **MCP errors during refresh** — write what you can; flag in Checkpoint that some files may be stale; tell coach to expect a longer pickup next session
- **Coach abruptly leaves** mid-closeout — write whatever's been completed, note in handoff.md "session ended early; verify state next session"
- **Conflicting state** (e.g., handoff says X is open but Checkpoint shows X was closed this session) — flag explicitly, ask coach to clarify before overwriting
- **Workspace has drifted** (files manually edited outside Claude since last session) — preserve manual edits where possible; flag in Checkpoint

---

## Hard rules

- **Never skip Phase 1 (refresh).** Stale trackers are worse than no trackers.
- **Never invent wins.** Real ones only.
- **Never edit RULES.md** without explicit coach request.
- **Never silently skip a file** in the verification table.
- **Always celebrate** before logging off.
