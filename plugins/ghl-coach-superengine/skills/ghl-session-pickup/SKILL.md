---
name: ghl-session-pickup
description: Use this skill at the start of every coaching session — when the coach says "let's get started", "I'm back", "open up my GHL", "what's the status?", "pick up where we left off", or whenever a working session begins. Reads the persistent workspace files, refreshes hot-lead and client-roster state from GHL via MCP, runs the notifier to surface anything urgent, and presents a one-screen brief. Replaces the older `ghl-session-startup` skill with a richer, file-backed flow.
---

# GHL Session Pickup

Run at the **start of every coaching session**. Reads the workspace, refreshes state, surfaces what needs attention, agrees on a session goal. Don't do other work until this completes.

## Prerequisites
- Workspace must exist (created by `ghl-workspace-setup`). If absent → tell the coach to run `ghl-workspace-setup` first.
- GHL MCP must be connected. If it errors → hand off to `ghl-mcp-installer`.
- Filesystem MCP must be available to read/write workspace files.

---

## Phase 0 — RULES.md compliance check (15s)

Read `RULES.md` from the workspace. The four override constraints + GHL guardrails apply to everything in this session. Acknowledge silently — don't broadcast unless violated.

---

## Phase 1 — Read the workspace (1 min)

Read these files in order. Don't skip.

1. `handoff.md` — what last session left for this one
2. `coach-profile.md` — refresh on niche, voice, ICA
3. `offers.md` — current programs/prices (referenced often during the session)
4. `attention-needed.md` — blockers, stuck items
5. `follow-up.md` — current hot-leads queue
6. `client-roster.md` — current paying-client snapshot
7. **Skim** the most recent 1–2 entries in `Checkpoint.md`

Memory pulls (parallel): coach name, business name, voice, top offers — these may already be in Claude memory from setup.

---

## Phase 2 — Verify MCP connection (silent, 30s)

Run a fast read-only check:
```
search_contacts(limit=1)
```

If it returns data: ✅ green light, move on. Don't broadcast — keep this invisible when it works.
If it errors: surface immediately, hand off to `ghl-mcp-installer` for reconnection.

---

## Phase 3 — Refresh state from GHL (live MCP, 1–2 min)

Pull live data and write the trackers. Run these MCP queries in parallel:

```
search_opportunities(stage="any", sort="lastActivity")           # for follow-up.md
search_contacts(tag="client-active", tag="client-onboarding")    # for client-roster.md
search_opportunities(daysInStage>7)                              # for attention-needed.md
get_workflows(locationId)                                        # detect new automations not in inventory
```

Then update the workspace files via Filesystem MCP:

### Refresh `follow-up.md`
Recompute the urgent / high-priority / watch buckets based on the urgency rules (see file body). Sort each bucket by most-urgent first. Each entry: `name | last touch | stage | suggested action`.

### Refresh `client-roster.md`
Update `Days Since Touch` for every active client. Move clients between sub-sections (Onboarding / Active / Check-In Due / Renewal / Paused) based on tags + days.

### Refresh `attention-needed.md`
Append new items detected this refresh:
- Stuck leads (>7 days no movement)
- Tag drift (conflicting tags on same contact)
- Missing data (key custom fields empty)
- New workflow errors (if MCP exposes execution logs)

Don't remove existing manual flags — only the coach removes those.

### Sync `automation-inventory.md`
If `get_workflows()` returns workflows not in the inventory file, append them with status "newly detected — confirm purpose with coach."

---

## Phase 4 — Run the notifier (30s)

Invoke `ghl-notifier` (agent if Claude Code, inline logic if Claude Desktop). It scans the just-refreshed files and produces:
- Top 3 items needing attention right now (in-conversation)
- Optionally creates GHL internal tasks for urgent items (>24h since flag, urgent-bucket)

Hold the notifier's output for the brief.

---

## Phase 5 — Present the brief (1 min)

Format:

```
SESSION PICKUP — {date}

Last session: {1-line summary from Checkpoint.md top entry}
Status: {clean / X blockers}

🔥 HEADS UP (from notifier):
  1. {top urgent item — what + suggested action}
  2. {second}
  3. {third}

📋 PIPELINE QUICK LOOK:
  Hot leads: {N urgent / M high-priority / K watch}
  Active clients: {N onboarding / M active / K check-in-due}
  Stuck items: {count}

🎯 PLANNED FROM HANDOFF:
  {handoff.md P0 #1}
  {handoff.md P0 #2}

What's the ONE most important thing we accomplish today?
```

End your turn. Wait for the coach's answer before doing work.

---

## Phase 6 — After goal confirmed: route + start

Based on what the coach picks, hand off to the right downstream skill:

| Coach goal | Skill |
|------------|-------|
| Tag/organize/clean up contacts | `ghl-tagging` |
| Move someone, pipeline work | `ghl-pipelines` |
| Build/edit automation | `ghl-automations` |
| "How does GHL do X" question | `ghl-docs` |
| Multi-step batch work (process N leads end-to-end) | `ghl-coach-assistant` agent (Claude Code) or stay in this skill (Desktop) |

For multi-skill goals, plan the sequence in plain English first:
> "OK so we'll: 1) tag the new contact, 2) add them to the pipeline, 3) trigger the welcome workflow. I'll do them one at a time. Ready?"

---

## Tone reminders (carry through entire session)

- One step at a time
- Plain English; no jargon without explainer
- Narrate before MCP writes; confirm after
- Reassure: "totally fixable", "this is normal", "we can pause anytime"
- Celebrate small wins; append to `wins.md` at session end if anything worth celebrating happened
- Bulk operations (5+) require explicit confirmation

---

## When the coach says "I don't know what to focus on"

Don't pick for them — show options:

> "Looking at your workspace, here's what's loudest:
>   - **{N urgent} hot leads** sitting cold — could clear those in 20 min
>   - **{stuck count} stuck opportunities** that need a decision
>   - **{automation count} automations** showing as new — want me to confirm what they do?
>
> Which lights up for you?"

---

## When the coach says "I'm overwhelmed"

> "Totally fair. Let's pause and pick the smallest possible thing.
>
> What's ONE contact or ONE situation that's bugging you right now? We'll just clean that up. Once that feels good, we stop for today."

Then handle that one thing with maximum care. Don't extend.

---

## Hard rules

- **Never skip Phase 1 (workspace read).** That's where context lives.
- **Never skip Phase 5 (the goal question).** It anchors everything.
- **Never start work** before the coach confirms in their own words what they want.
- **Never bulk-execute** during pickup. Save those for after the goal is set.

---

## Edge cases

- **Workspace exists but is stale** (last session was >30 days ago) → flag in brief: "It's been {N} days since we last met. A lot may have changed in your GHL — Phase 3's refresh may take longer."
- **MCP returns no data** for a refresh query (empty pipeline, no clients) → write that to the file as "(empty as of {date})" rather than leaving stale data.
- **handoff.md has unresolved blockers** → surface FIRST in the brief, before the heads-up section.
