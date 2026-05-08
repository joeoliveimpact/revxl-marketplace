---
name: ghl-workspace-setup
description: Use this skill ONCE per coach client to scaffold their persistent GHL coaching workspace. Triggers on "set up my GHL workspace", "onboard me to REVXL", "build my coaching workspace", "initialize GHL workspace", "first-time setup". Interactive intake that pulls structure from the coach's GHL account via the GHL MCP (pipelines, automations, custom fields), asks them to confirm/edit, then writes 13 scaffold files to a local folder via the Filesystem MCP. After this runs, ghl-session-pickup and ghl-session-closeout maintain the workspace every session.
---

# GHL Workspace Setup

This skill bootstraps a persistent **per-coach workspace** at a local folder on the coach's machine. After this runs once, every future session reads and updates this workspace. Without this, the other ghl-coach-superengine skills work but lose context between sessions.

**Run this ONCE** per coach client. If a workspace already exists at the target path, this skill should detect that and offer to refresh specific files rather than overwriting everything.

## Prerequisites

Before running:
1. **GHL MCP installed and connected** — verify with a test query first. If not connected, hand off to `ghl-mcp-installer`.
2. **Filesystem MCP installed** — required to write the workspace files. If absent, instruct the coach to install it from Claude Desktop's Customize → Connectors panel before continuing.

## Tone

This is the most onboarding-heavy interaction the coach will have. Pace it.

- Plain English. No "scaffold," "directory tree," "JSON" — say "folder," "files."
- Frame each file's purpose in coach terms BEFORE writing it: _"Next we'll write a file called offers.md — it's just a list of your programs and prices, so I always know what to refer to."_
- Confirm before writing each batch (groups of 2–4 related files).
- Celebrate completion: _"You just built the foundation. From now on, I'll remember everything about your business between sessions."_

---

## Workspace location

**Default path:** `~/REVXL-GHL-Workspaces/{coach-business-slug}/`

Where `{coach-business-slug}` is a kebab-case version of the coach's business name (asked during intake).

Example: `~/REVXL-GHL-Workspaces/sarah-strong-nutrition/`

Confirm the path with the coach before writing. Allow override.

---

## Intake — Five questions, one at a time

Ask each, capture the answer, move on. Don't batch.

1. **Business name** — used to slug the workspace folder
2. **Niche / target audience** — for `coach-profile.md`'s ICA section ("women in perimenopause looking to lose 20+ lbs")
3. **Voice / tone** — how the coach wants Claude to sound when drafting messages on their behalf ("warm, direct, no fluff")
4. **Top 1–3 offers** — name + price + length + what's included. Pull anything you can from GHL Memberships if available; ask coach to confirm/correct.
5. **Anything specific Claude should NEVER do** — guardrails (e.g., "never send messages without my approval")

---

## Phase 1 — Pull what we can from GHL via MCP

While intake is happening, run these MCP calls in parallel:

```
get_pipelines(locationId)              # populates pipelines.md
get_workflows(locationId)              # populates automation-inventory.md (existing automations)
list_contact_custom_fields(locationId) # informs coach-profile.md
search_opportunities(stage="any", limit=50) # samples for client-roster.md + follow-up.md
```

Hold results in memory. Use them to pre-fill the scaffold files so the coach confirms rather than authors from scratch.

---

## Phase 2 — Write the 13 scaffold files

Confirm the workspace path one more time, then write all 13 files using the Filesystem MCP. Each template below shows the structure; fill from intake + MCP-pulled data.

### Setup files (rarely change)

#### `RULES.md`
```markdown
# Rules — Override Constraints

Apply these to EVERY action in this workspace. They override anything else.

## 1. Intent Clarification
Never assume intent on ambiguous tasks. If a request has multiple valid interpretations, stop and ask. One question per ambiguity.

## 2. Least Complexity
Default to the simplest solution. If a task takes 3 steps, don't propose 10.

## 3. Surgical Execution
Only change what's requested. Never reformat or rename unrelated parts. Flag in-scope-adjacent issues; don't touch them.

## 4. Declarative Focus
Always identify the Definition of Done. Flag a shorter path if you see one.

## GHL-specific guardrails
- Never bulk-act on 5+ contacts without explicit confirmation
- Always narrate before MCP write actions: "I'm about to {action}. Ready?"
- Always confirm after MCP write actions: "Done ✓ {what changed}"
- Never invent feature behavior — if unsure, hand off to `ghl-docs` skill
- {coach's custom guardrails from intake question 5}
```

#### `CLAUDE.md`
```markdown
# {Coach business name} — GHL Coaching Workspace

> ⚠️ **Read RULES.md every session.** They override everything else.

## Session start
1. Read RULES.md
2. Run `ghl-session-pickup` skill — it reads the workspace and presents a brief
3. Confirm goal-of-session before doing work

## Tone
- Plain English. No CRM jargon without explainer.
- One step at a time.
- Narrate before MCP writes; confirm after.
- Reassure liberally. Celebrate small wins.
- Voice when drafting messages: {coach's voice from intake}

## MCP usage
- The GHL MCP is connected. I can read and update contacts, pipelines, opportunities, calendars, conversations, etc.
- I always confirm bulk operations (5+ records).
- Never invent feature behavior — if unsure, run `ghl-docs` skill.

## Files in this workspace
- See `coach-profile.md` for who this coach is
- See `offers.md` for programs and pricing
- See `pipelines.md` for actual pipeline structure
- See `follow-up.md`, `client-roster.md`, `attention-needed.md` for current state
- See `automation-inventory.md` for what's already built
- See `kpis.md` for current metrics
- See `wins.md` for recent celebrations
- See `Checkpoint.md` for session log; `handoff.md` for next-session priorities
```

#### `coach-profile.md`
```markdown
# Coach Profile — {Business name}

## Identity
- **Name:** {coach name}
- **Business:** {business name}
- **Website:** {if provided}

## Niche / Ideal Client Avatar
{from intake question 2 — paragraph form}

## Voice & tone
{from intake question 3}

## GHL setup
- **Location ID:** {pulled from MCP}
- **MCP install date:** {today}
- **Time zone:** {pulled from MCP}

## Business model
{1–2 sentences: 1:1 only / group / hybrid / DIY course / etc.}

## Hard guardrails (Claude never does these)
{from intake question 5}
```

#### `offers.md`
```markdown
# Offers

For each offer, document:
- Name
- Price + structure (one-time, monthly, payment plan)
- Length / duration
- What's included
- Ideal client for this offer
- Status (active / paused / sunsetting)

## {Offer 1 name}
- **Price:** {price}
- **Length:** {duration}
- **Includes:** {list}
- **Ideal for:** {audience}
- **Status:** active

## {Offer 2 name}
...

(Continue for each offer from intake)
```

#### `pipelines.md`
```markdown
# Pipelines (actual structure pulled from GHL)

> Source: GHL MCP `get_pipelines()` on {date}

## {Pipeline 1 name}
**Purpose:** {what it tracks — e.g., "leads from DMs"}

| Stage | Meaning |
|-------|---------|
| {stage 1} | {what it means in this coach's flow} |
| {stage 2} | ... |

## {Pipeline 2 name}
...

(Continue for each pipeline returned by MCP. Ask coach to fill in "Meaning" for each stage.)
```

### State trackers (updated every session)

#### `follow-up.md`
```markdown
# Follow-Up Queue — Hot Leads

> Auto-refreshed at session start by `ghl-session-pickup`. Sorted by urgency (most urgent at top).

## Urgent (act today)
*(empty — fills as MCP queries identify hot leads needing follow-up)*

## High priority (act this week)
*(empty)*

## Watch (no action yet)
*(empty)*

---

### How urgency is calculated
- **Urgent:** `status-hot` + last touch >24h ago, OR opportunity in `Decision Pending` >5 days
- **High priority:** `status-qualified` + last touch >48h, OR `action-dm-sent` >48h with no response
- **Watch:** `status-nurture` contacts; new leads from yesterday
```

#### `client-roster.md`
```markdown
# Active Client Roster

> Snapshot of paying clients, refreshed at session start.

| Client | Program | Stage | Last Touch | Days Since | Flags |
|--------|---------|-------|------------|------------|-------|
| {filled by ghl-session-pickup from MCP} |

## Onboarding (first 2 weeks)
*(list those tagged `client-onboarding`)*

## Active
*(list those tagged `client-active`)*

## Check-In Due (overdue >14 days)
*(list those flagged for missed check-in)*

## Renewal / Upsell window
*(clients in their final 30 days)*

## Paused
*(those tagged `client-paused`)*
```

#### `attention-needed.md`
```markdown
# Attention Needed

> Surfaced by `ghl-notifier`. The coach should review these before starting other work.

## Stuck leads
*(opportunities sitting in a stage >7 days with no movement)*

## Broken automations
*(workflows that have errored or that the coach has flagged for review)*

## Tag drift
*(contacts with conflicting tags — e.g., both `status-hot` and `client-active`)*

## Missing data
*(contacts missing key custom fields)*

## Coach's manual flags
*(items the coach has manually added — "remember to check Sarah on Friday")*
```

### Inventory

#### `automation-inventory.md`
```markdown
# Automation Inventory

> Auto-populated from GHL MCP `get_workflows()` on {date}. Updated when new automations are built.

## Active workflows

### {Workflow name 1}
- **Trigger:** {what fires it}
- **Actions:** {chain summary}
- **Status:** Active
- **Last fired:** {if available}
- **Notes:** {coach notes}

### {Workflow name 2}
...

## Paused workflows
*(those marked inactive in GHL)*

## Planned (not built yet)
*(things the coach wants to build — added during sessions)*

## Known issues
*(workflows that have misfired or have edge cases)*
```

#### `wins.md`
```markdown
# Wins & Celebrations

> Standalone log so the coach can scroll for motivation. Source for testimonials and content.

## {Date}
{enrollment, milestone, testimonial, breakthrough — 1-paragraph each}

---

(Most recent on top. Append new entries via `ghl-session-closeout` when wins happen.)
```

### Strategic

#### `kpis.md`
```markdown
# KPIs — Current Snapshot

> Manually updated quarterly (or when reviewing performance). Don't rely on auto-refresh.

## Last updated: {date}

## Lead generation
- **Leads added per month:** {number}
- **Top source:** {channel}

## Conversion
- **Call book rate (qualified → call booked):** {%}
- **Show rate (call booked → showed):** {%}
- **Close rate (showed → enrolled):** {%}

## Revenue
- **MRR:** {$}
- **Average client value (LTV):** {$}
- **Avg sales cycle (first DM → enrolled):** {days}

## Retention
- **Active clients:** {count}
- **Alumni:** {count}
- **Churn rate (last 30 days):** {%}

## Notes
{anything contextual about the period}
```

### Lifecycle

#### `Checkpoint.md`
```markdown
# Checkpoint — Session Log

> Append-only. Newest entry at top. Updated by `ghl-session-closeout`.

Format per entry:
```
## YYYY-MM-DD — {short title}
**Duration:** ~Xh
**TL;DR:** {1–2 sentences}

### Completed
- {item}

### Decisions
- {decision} — why: {rationale}

### MCP actions taken
- {tagged X contacts, moved Y opportunities, etc.}

### Wins
- {anything worth celebrating — also append to wins.md}

### Files touched
- {paths}

### Not done (rolled to handoff.md)
- {item}

---
```

(No entries yet — `ghl-session-closeout` will start adding them.)
```

#### `handoff.md`
```markdown
# Handoff — Next-Session Priorities

> Rewritten by `ghl-session-closeout`. The first thing read at session start.

## Last session
{date} — workspace setup (this session)

## Status
Workspace just scaffolded. Ready for first working session.

## P0 — Next Actions
1. Run `ghl-session-pickup` to take a first look at hot leads + active clients
2. Review the auto-pulled pipelines.md and confirm stage meanings
3. Pick the ONE thing to accomplish in the first real session

## Blockers
*(none)*

## Reminders
- The MCP is connected; talk to me naturally — I can do most things directly
- Files in this workspace persist between sessions; I'll read them every time
```

---

## Phase 3 — Confirm and celebrate

Once all 13 files are written, summarize for the coach:

> "Done ✓ Your GHL coaching workspace is at `{path}`. 13 files. From now on, every time we start a session, I'll read these and pick up exactly where we left off — no re-explaining. Want to do a quick look around, or jump into the first real session?"

Save key facts to **Claude memory** (durable across sessions, redundant with files for quick access):
- Coach name
- Business name
- Workspace path
- MCP install status: confirmed
- Niche
- Voice notes (1 line)
- Top 3 offer names + prices

These memory entries make session-pickup faster (no need to re-read setup files for basic identity facts).

---

## Edge cases

- **Workspace already exists** at the target path → don't overwrite. Offer: "I see a workspace already. Want to refresh specific files (`offers.md`, `pipelines.md`), or start fresh somewhere else?"
- **Filesystem MCP not installed** → instruct coach to install via Customize → Connectors before continuing. Don't proceed without it.
- **GHL MCP not installed** → hand off to `ghl-mcp-installer` first.
- **Coach skips a question** (e.g., "I don't have offers nailed down yet") → leave that file with a `# TODO` placeholder; note in handoff.md to revisit.
- **GHL location is empty** (brand new account) → still write all files; many will start empty. Note in `attention-needed.md`.

---

## Success criteria

You succeed when:
1. All 13 files exist at the workspace path
2. Each file has real coach-specific content (not template placeholders) — except where MCP returned empty
3. Memory has the coach's identity facts saved
4. handoff.md has clear P0 for the first real session
5. Coach feels oriented, not overwhelmed
