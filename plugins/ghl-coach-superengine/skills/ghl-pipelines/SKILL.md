---
name: ghl-pipelines
description: Use this skill when a coaching client asks about GoHighLevel pipelines or opportunities — "move this contact to the next stage", "add to my pipeline", "what stage is X in", "create an opportunity", "move them through the pipeline", "where are my hot leads". Manages the two canonical pipelines (Sales DM Pipeline + Client Pipeline) and executes pipeline moves via the GHL MCP. Coordinates tag updates with stage moves so contacts stay clean as they progress.
---

# GHL Pipeline Management

Pipelines are the **journey map** for every contact in GoHighLevel. This skill manages both pipelines and the tag updates that need to ride alongside every stage move.

**Mental model to give the client:**
> "A pipeline is a row of buckets. Each bucket is a stage. Contacts (as opportunities) move from left to right as they progress. The visual layout makes it obvious who needs attention right now."

---

## Tone Rules (CRITICAL)

- One step at a time.
- Always narrate before executing: "I'm about to move Sarah from `Qualified` to `Call Booked` and update her tags. Ready?"
- Confirm after: "Done ✓ Sarah is now in `Call Booked` with `action-call-booked` flagged."
- Pipeline moves often need TAG updates — handle both in one operation when possible.

---

## The Two Canonical Pipelines

### 1. Sales DM Pipeline
For leads coming through Instagram DMs, ManyChat, social media, referrals.

```
New DM → Qualified → Call Booked → Proposal Sent → Decision Pending → Enrolled → Lost / Not a Fit
```

| Stage | What it means |
|-------|---------------|
| New DM | Lead just entered, first message exchanged or not |
| Qualified | Had conversation, confirmed they're a fit for your offer |
| Call Booked | Discovery call is on the calendar |
| Proposal Sent | Offer has been shared in writing or on the call |
| Decision Pending | They asked for time to think |
| Enrolled | They paid / signed up — moves to Client Pipeline next |
| Lost / Not a Fit | Closed — won't move forward |

### 2. Client Pipeline
For paying clients in active programs.

```
Onboarding → Active → Check-In Due → Renewal / Upsell → Alumni → Paused
```

| Stage | What it means |
|-------|---------------|
| Onboarding | First 2 weeks — getting set up |
| Active | In the program, engaged |
| Check-In Due | Hasn't checked in this week — needs attention |
| Renewal / Upsell | Program ending — opportunity to extend or upgrade |
| Alumni | Completed program successfully |
| Paused | Program paused (life circumstances) |

> **Adapt for new clients:** Ask "What are the names of your pipelines and what does each stage mean to you?" Update memory with their actual setup. Don't assume the canonical names match.

---

## Stage Move Decision Table — Sales DM Pipeline

| What happened | Move to stage | Tag changes |
|---------------|---------------|-------------|
| First DM exchanged | `New DM` | Add `src-{channel}`, `status-new`, `interest-unknown`, `action-dm-sent` |
| They responded positively | `Qualified` | Remove `status-new`, add `status-hot` |
| Call is booked | `Call Booked` | Remove `action-dm-sent`, add `action-call-booked` |
| Proposal shared | `Proposal Sent` | Remove `action-call-booked`, add `action-proposal-sent` |
| They said "let me think" | `Decision Pending` | Add `action-waiting-decision` |
| They enrolled 🎉 | `Enrolled` | **Remove ALL `status-` and `action-` tags**, add `client-onboarding` |
| They said no | `Lost / Not a Fit` | Remove all `action-` tags, add `status-not-a-fit` |

---

## Stage Move Decision Table — Client Pipeline

| What happened | Move to stage | Tag changes |
|---------------|---------------|-------------|
| Just enrolled | `Onboarding` | Add `client-onboarding`, remove sales tags |
| Past week 2, engaged | `Active` | Swap `client-onboarding` → `client-active` |
| No check-in this week | `Check-In Due` | Add `action-follow-up` |
| Program ending | `Renewal / Upsell` | Add `action-follow-up` |
| Finished program | `Alumni` | Swap `client-active` → `client-alumni` |
| Asked to pause | `Paused` | Swap to `client-paused` |

---

## MCP Operations

### Move opportunity to new stage
```
update_opportunity_status(opportunityId, newStage)
```

### Create opportunity (when adding lead to pipeline)
```
create_opportunity(
  pipelineId,
  stage="New DM",
  contactId,
  name="{contact name} - {program interest}",
  monetaryValue={offer price}
)
```

### Search by stage
```
search_opportunities(pipelineId, stage="Hot")
```

### Get pipeline structure (always at session start to verify stage names)
```
get_pipelines(locationId)
```

---

## Common Operations (Templates)

### "Add this new lead to the Sales DM Pipeline"
1. Find or create the contact (use `ghl-tagging` skill for tag setup).
2. Create the opportunity:
   ```
   create_opportunity(
     pipelineId={Sales DM Pipeline ID},
     stage="New DM",
     contactId={contact},
     name="{Name} - {Interest}",
     monetaryValue={offer price}
   )
   ```
3. Confirm: "Done ✓ {name} is in `New DM` with a {price} opportunity attached. Want to send the first message now?"

### "Move {name} to Call Booked"
1. Find their current opportunity.
2. Update stage → `Call Booked`.
3. Tag updates: remove `action-dm-sent`, add `action-call-booked`.
4. Confirm and ask if they want a calendar reminder.

### "{name} enrolled!" (transition between pipelines)
1. Move opportunity in Sales DM Pipeline to `Enrolled`.
2. Create new opportunity in Client Pipeline at `Onboarding` stage.
3. Tag changes: remove all `status-` and `action-` tags, add `client-onboarding`.
4. Celebrate: "🎉 {name} just enrolled. Sales pipeline closed, Client Pipeline started, tags cleaned up. That's a complete handoff."

### "Show me my hot leads"
1. `search_opportunities(stage="Qualified")` OR `search_contacts(tag="status-hot")`.
2. List them with: name + last touch + days in current stage.
3. Recommend action for the top 3.

---

## Pre-flight Check (run once per session)

If the client's pipeline names don't match the canonical ones above:
1. Run `get_pipelines(locationId)` to fetch their actual structure.
2. Save the real pipeline names + stage names to Claude memory.
3. Use their real names in all narration ("moving to your `Hot Leads` stage" not "moving to `Qualified`").

---

## Bulk Operation Warning

For any move affecting 5+ opportunities (e.g., "move everyone in `Decision Pending` for over 14 days to `Lost`"):
1. List the affected contacts first.
2. Pause: "I'm about to move {N} contacts. Confirm before I proceed?"
3. Execute one at a time, narrating each.

---

## Reassurance Scripts

**When client confused about stages:**
> "Pipelines feel like a lot at first. The trick is just thinking about each stage as 'where are they in their decision?' That's it."

**When they want to skip a stage:**
> "Totally fine to skip stages — pipelines are about reflecting reality, not following a rigid script. If they went straight from DM to Enrolled, we just move them all the way over."

**Celebrate progress:**
> "Just looked at your pipeline view — you have {N} opportunities in `Qualified` right now. That's {N} real conversations. That's the work paying off."
