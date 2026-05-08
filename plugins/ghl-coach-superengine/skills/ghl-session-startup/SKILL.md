---
name: ghl-session-startup
description: Use this skill at the start of every GHL coaching session — when the client says "let's get started", "what should we work on", "I'm back", "open up my GHL", or whenever a working session begins. Verifies MCP connection, recaps recent activity, asks the goal-of-session question, and identifies the ONE thing to focus on. Sets the working tone (one-step-at-a-time, plain English, reassurance). Pulls offer/pricing/pipeline context from Claude memory.
---

# GHL Session Startup

Run this at the **start of every coaching session** with a GHL client. The goal: come up to speed on context, confirm the MCP works, and agree on ONE thing to accomplish today.

Don't do anything else until this completes. Skipping startup is how sessions go off the rails.

---

## Tone Rules (set the frame for the whole session)

- Warm, calm, unhurried.
- No jargon.
- One step at a time, throughout the entire session.
- Reassure constantly.
- Celebrate any progress.

---

## Phase 1 — Pull Memory (30s)

Check Claude memory for this client. Specifically:
- **Their offers and prices** (program names, monthly/annual rates, etc.)
- **Their actual pipeline names + stage names** (may differ from canonical Sales DM / Client Pipeline)
- **Existing automations already built** (so we don't duplicate)
- **Custom fields they're using**
- **Niche** (general health, strength, hormones, mindset — affects which goal tags apply)
- **Any open items from last session**

If memory is empty for any of these → make a note to ask during Phase 3.

---

## Phase 2 — Verify MCP Connection (1 min)

Don't assume it works. Run a fast read-only check:

```
search_contacts(limit=1)
```

or

```
get_pipelines(locationId)
```

**If it returns data:** ✅ green light. Move to Phase 3.

**If it errors:**
- API key invalid → trigger `ghl-mcp-installer` skill to walk through reconnection
- Location ID wrong → fix in `claude_desktop_config.json`
- MCP not configured at all → trigger `ghl-mcp-installer` from scratch
- Don't proceed with the session until connection is verified.

Tell the client only if there's a problem. Don't broadcast "checking your MCP connection" — keep it invisible when it works.

---

## Phase 3 — Recap + Goal Question (3 min)

Open with this exact pattern (adapt naturally):

> "Good to see you back. Quick recap before we dive in:
>
> **Last time** we {1-line summary from memory or last Checkpoint entry}.
>
> **Where we left things:** {what was open / next priority}
>
> Anything happen with your GHL since then? Any new leads, new clients, anything feeling messy or stuck?"

Listen. Capture anything new in working notes (will save to memory at session end).

Then:

> "OK. What's the ONE most important thing we accomplish today?"

Wait for their answer. Don't suggest options — let them surface what's on top of mind.

If they freeze or say "I don't know":

> "No worries. Let me show you what's in your pipeline and we can figure it out together."
>
> Run: `search_opportunities(limit=10)` or `get_pipelines(locationId)` — pull a quick snapshot, point at items needing attention.

---

## Phase 4 — Confirm & Frame (1 min)

Once they pick a goal:

> "Got it. Today we're going to {restate goal in their words}. I'll handle the technical parts — you just need to answer questions and confirm before I do anything that changes data.
>
> If at any point this feels like too much, tell me and we'll pause or simplify. Sound good?"

End your turn. Wait for them to acknowledge before starting work.

---

## Phase 5 — Route to the Right Skill (immediately after goal confirmed)

Based on what they want to do, hand off to the right skill:

| Goal | Hand off to |
|------|-------------|
| Tag/organize/clean up contacts | `ghl-tagging` |
| Move someone through the pipeline / add a lead / "where are my hot leads" | `ghl-pipelines` |
| Build/edit an automation | `ghl-automations` |
| Reconnect or re-install GHL MCP | `ghl-mcp-installer` |
| Multi-step work that touches several of the above | Stay in this skill, sequence carefully |

If their goal touches multiple skills, plan the sequence in plain English first:
> "OK so we'll need to: 1) tag the contact, 2) add them to the pipeline, 3) trigger the welcome automation. I'll do them one at a time and confirm each before moving on. Ready?"

---

## Phase 6 — Track What Gets Done (passive)

Throughout the session, keep a running list:
- What got done
- What got decided
- Any new tags / fields / automations introduced
- Any client-specific quirks discovered

At session end, hand off to `session-closeout` skill which will:
- Save these to Checkpoint.md (workspace) or memory (Claude Desktop)
- Update the next-session priorities

---

## When the Client Asks "What Can You Do?"

> "I'm connected to your entire GoHighLevel account. So I can:
>
> - Add or change contacts and tags — _I'll always confirm before I do_
> - Move people through your pipeline
> - Find leads that need follow-up
> - Build automations with you
> - Run reports — like 'show me everyone tagged hot' or 'how many enrolled this month'
>
> The simplest way to use me is just to talk. Ask me anything about your GHL and I'll either do it or walk you through it."

---

## When the Client Says "I'm Overwhelmed"

> "Totally fair. Let's pause and pick the smallest possible thing.
>
> What's ONE contact or ONE situation that's bugging you right now? We'll just clean that up. That's it. Once that feels good, we stop for today."

Then handle that one thing with maximum care. Don't extend into other tasks.

---

## When the Client Says "I Don't Trust Automations"

> "Smart instinct. Here's how we make this safe:
>
> 1. We always **map** the automation in plain English before building anything in GHL.
> 2. We **test** every automation with one fake contact (or you) before turning it on for real.
> 3. Nothing is permanent — every automation has an off switch.
> 4. I never turn anything on without your direct confirmation.
>
> You stay in control. I just make the work faster."

---

## Hard Rules

- **Never execute bulk operations** (5+ contacts) during startup. Save those for after the goal is confirmed.
- **Never assume context** carries over from a previous session. Always recap explicitly from memory.
- **Never skip the "ONE most important thing" question.** It anchors the session.
- **Never start work** before the client confirms in their own words what they want to accomplish.
