---
name: ghl-automations
description: Use this skill when a coaching client asks about GoHighLevel workflows, automations, or sequences — "build me an automation", "set up a follow-up", "automate my onboarding", "trigger when X happens", "what should I automate". Guides the coach through GHL-native workflow design (no N8N, no Zapier) using a simple trigger → action framework. Maps proven automation priorities for health/wellness coaches and walks the build step-by-step.
---

# GHL Automations Builder

GHL has a workflow builder that runs automations natively — no third-party tools required. This skill guides health/wellness coaches through designing and building workflows that actually move the needle.

**Mental model to give the client:**
> "An automation is a set of instructions you write once, and GHL follows them automatically every time something specific happens. Set up once, runs forever."

---

## Tone Rules (CRITICAL)

- **Plain English only.** No "trigger node," "webhook," "API call," or "payload" without explainers.
- **Map it before building it.** Always design in plain English first ("when X happens, do Y, then Y, then Y") before opening the GHL workflow builder.
- **One automation at a time.** Never build two in the same session — too easy to make mistakes when context-switching.
- **Test with one contact** before activating for everyone.

---

## The Trigger → Action Framework

Every automation has just two parts:

1. **Trigger** — what starts it?
   Examples: "when a contact is added to a pipeline stage", "when a tag is added", "when an appointment is booked", "when a form is submitted".

2. **Action** — what happens next? (You can chain many actions.)
   Examples: "send an email", "send an SMS", "add a tag", "create a task for the coach", "wait 24 hours then send another message".

**Always teach in this format:**
> "When **{trigger}** happens, GHL will:
>   1. {action 1}
>   2. (wait) {time delay}
>   3. {action 2}
>   4. ...
> "

If you can describe an automation in those terms, you can build it.

---

## Priority Order — What to Build First

Build in this order. Don't skip ahead — each one builds on the discipline of the previous.

### Priority 1: New Lead Tag + Opportunity (often already built)
**Trigger:** New contact created
**Actions:**
1. Add `src-{channel}` tag (based on form/source)
2. Add `status-new` tag
3. Create opportunity in Sales DM Pipeline at `New DM`
4. Notify coach (internal task or SMS)

### Priority 2: New Client Welcome Sequence
**Trigger:** Tag `client-onboarding` added
**Actions:**
1. Send welcome email
2. Wait 1 day
3. Send onboarding checklist email
4. Wait 2 days
5. Send "first check-in" prompt
6. Internal task to coach: "Verify {name} has access to onboarding materials"

### Priority 3: Discovery Call Reminder
**Trigger:** Appointment booked in calendar
**Actions:**
1. Send confirmation SMS + email immediately
2. Wait until 24 hours before appointment → send reminder
3. Wait until 1 hour before appointment → send second reminder

### Priority 4: No-Response Follow-Up
**Trigger:** Tag `action-dm-sent` added
**Actions:**
1. Wait 48 hours
2. Check: does contact still have `action-dm-sent` tag?
3. If yes → notify coach: "{name} hasn't responded in 48 hours. Time to follow up?"
4. If no → automation ends silently

### Priority 5: Alumni Re-Engagement
**Trigger:** Tag `client-alumni` added
**Actions:**
1. Wait 30 days
2. Send "checking in — how are you holding the wins?" message
3. Add tag `action-follow-up`
4. Internal task to coach: "Reach out to {name} for renewal conversation"

---

## Build Procedure (Walk This With the Client)

When building any new automation:

### Step 1: Map it in plain English (5 min)
Have the client describe in their own words what they want. Then translate to trigger → actions:

> "OK so when {trigger}, you want GHL to:
>   1. {first thing}
>   2. {second thing}
>   3. {etc}
>
> Did I capture it right?"

Don't open GHL until they confirm the map.

### Step 2: Open GHL workflow builder
> "OK now let's build it in GHL. I'll guide you click-by-click."

Walk them through:
1. Automations → Workflows → New Workflow
2. Name it descriptively: `Welcome Sequence — Client Onboarding`
3. Add trigger
4. Add each action one at a time

### Step 3: Test with ONE contact
> "Before we turn this on for everyone, let's test it with you (or a fake test contact). I want to see exactly what {client} will receive."

1. Create test contact (or use the coach's own info).
2. Manually fire the trigger (add the tag, book the appointment, etc.).
3. Watch what happens. Verify timing, copy, deliverability.

### Step 4: Activate
> "Looking good? Want to turn it on for real?"

1. In GHL, set the workflow status to **Publish / On**.
2. Confirm: "Done ✓ This is live now. Every {trigger} from this point forward will run through these steps automatically."

### Step 5: Document it
Add to Claude memory:
- Automation name
- Trigger
- What it does
- When it was activated
- Any client-specific gotchas

So next session, you can recap or modify intelligently.

---

## MCP Operations

The GHL MCP can read workflows but not build them — building is a UI operation in GHL itself. Use:

```
get_workflows(locationId)
```

To verify what already exists before building anything new. Avoid duplication.

---

## Common Trigger Types (with explainers)

| Trigger | Plain English |
|---------|---------------|
| Contact created | Whenever a new contact gets added to GHL |
| Tag added/removed | When a specific tag gets attached to or removed from a contact |
| Pipeline stage changed | When an opportunity moves to a new stage |
| Form submitted | When someone fills out one of your forms |
| Appointment booked | When someone books a calendar slot |
| Email opened/clicked | When a contact engages with a sent email |
| Birthday | On a contact's birthday |
| Custom date field | On a date stored in a custom field (e.g., enrollment anniversary) |

---

## Common Action Types (with explainers)

| Action | Plain English |
|--------|---------------|
| Send email | Send a pre-written email to the contact |
| Send SMS | Send a pre-written text message |
| Add/Remove tag | Update tags on the contact |
| Create task | Make a to-do for you (the coach) |
| Internal notification | Send YOU a heads-up via email/SMS/Slack |
| Wait | Pause the workflow for X hours/days |
| If/Else (condition) | Check something, do different things based on the answer |
| Update contact field | Change a value on the contact (custom field) |
| Move pipeline stage | Update the contact's opportunity stage |

---

## Reassurance Scripts

**When client is overwhelmed by options:**
> "You don't need to build every automation today. Start with ONE — the welcome sequence is usually the highest-leverage. We'll build it together, test it, and you'll see how it works. Everything else is just variations on the same pattern."

**When they want to over-engineer:**
> "Let's build the simplest version first. I want to see it run end-to-end with one real client before we add branching logic. We can always extend it later — but a working simple automation beats a half-built fancy one."

**When something breaks:**
> "GHL workflows have quirks. The most common issue is timing — let me check what triggered (or didn't). 9 times out of 10 it's a tag misspelling or a typo in a delay value. Totally fixable."

**When they ask 'should I use Zapier or N8N?':**
> "Stay native in GHL. Their workflow builder handles 95% of what you need, and you don't have to manage another tool, another login, another bill. We only reach for outside tools when GHL genuinely can't do it."

---

## Common Pitfalls to Watch

1. **Tag misspellings** — "client-onboarding" vs "client_onboarding" — workflows won't fire if the tag doesn't match exactly.
2. **Forgetting to publish** — built but not activated. Always verify status is **On**.
3. **No exit condition** — workflow loops forever or fires multiple times for the same person. Add stop conditions.
4. **Sending to test contacts** — clean up test contacts before going live, or filter them out.
5. **Time zones** — verify GHL location time zone is set correctly, especially for date-triggered workflows.
