---
name: ghl-tagging
description: Use this skill when a coaching client asks about GoHighLevel tags — "tag this contact", "what tags should I use", "organize my contacts", "add tag", "remove tag", "find contacts tagged X", or anything about contact organization in GHL. Provides the canonical tagging taxonomy for health/wellness/fitness coaches (source / status / interest / goal / client / action), explains tags in plain English, and executes tag operations via the GHL MCP. Designed for non-technical users — narrate every action, confirm bulk operations, reassure freely.
---

# GHL Tagging System

Tags are the spine of a clean GoHighLevel account. This skill teaches the client the tagging system AND executes tag operations via the GHL MCP.

**Mental model to give the client:**
> "Tags are sticky notes on a contact. They tell you who someone is, where they came from, what they want, and what needs to happen next. Clean tags = easy filtering, easy automation, easy reporting."

---

## Tone Rules (CRITICAL)

- One step at a time. Never give more than 3 action items at once.
- Plain English. No CRM jargon without an explainer.
- Narrate before acting via MCP: "I'm about to add `src-instagram` to Sarah's contact. Ready?"
- Confirm after every action: "Done ✓ Sarah now has the tag."
- For bulk operations (5+ contacts), always pause and get explicit confirmation.

---

## Tag Naming Convention

All tags use **lowercase with hyphens**, grouped by prefix so they sort cleanly in GHL's tag list.

---

## 🟦 SOURCE TAGS — Where did this person come from?

| Tag | Meaning |
|-----|---------|
| `src-instagram` | Came through Instagram (DM, post, bio link) |
| `src-facebook` | Came through Facebook (group, page, ad) |
| `src-referral` | Referred by an existing client or partner |
| `src-website` | Found via website, blog, or opt-in form |
| `src-paid-ad` | Came through a paid ad campaign |
| `src-manychat` | Originally a ManyChat subscriber |
| `src-other` | Source unknown or doesn't fit above |

**Rule:** Every contact should have **exactly ONE** `src-` tag.

---

## 🟨 STATUS TAGS — Where are they in the journey?

| Tag | Meaning |
|-----|---------|
| `status-new` | Just entered the system, not yet contacted |
| `status-nurture` | Not ready to buy yet, keep warming up |
| `status-hot` | Actively interested, ready to move fast |
| `status-qualified` | Had a conversation, confirmed they're a fit |
| `status-not-a-fit` | Not the right client at this time |
| `status-ghosted` | Was engaged, went silent |

**Rule:** A contact should have **ONE active** `status-` tag at a time. Update as they move forward — remove the old one, add the new.

---

## 🟩 INTEREST TAGS — What are they interested in?

| Tag | Meaning |
|-----|---------|
| `interest-1on1` | Interested in 1:1 private coaching |
| `interest-group` | Interested in the group program |
| `interest-hybrid` | Interested in the 1:1 + group hybrid |
| `interest-course` | Interested in a self-paced course or digital product |
| `interest-unknown` | Haven't expressed clear preference yet |

**Rule:** A contact **can have multiple** `interest-` tags.

---

## 🟥 GOAL TAGS — What does this person want to achieve?

| Tag | Meaning |
|-----|---------|
| `goal-weight-loss` | Primary goal is losing weight or body fat |
| `goal-strength` | Wants to build strength or muscle |
| `goal-energy` | Struggling with low energy, fatigue |
| `goal-hormones` | Hormonal health, thyroid, cycle regulation |
| `goal-mindset` | Emotional eating, relationship with food/body |
| `goal-nutrition` | Focused on food, meal planning, habits |
| `goal-overall` | General health and wellness, no specific focus |

**Rule:** A contact **can have multiple** `goal-` tags. They help personalize messaging.

---

## 🟪 CLIENT TAGS — Are they currently a paying client?

| Tag | Meaning |
|-----|---------|
| `client-onboarding` | Just enrolled, in the first 2 weeks |
| `client-active` | Currently in a program and engaged |
| `client-paused` | Program paused (life circumstances) |
| `client-alumni` | Completed a program successfully |
| `client-vip` | High-touch, long-term, or multi-program client |

**Rule:** Client tags **replace** `status-` tags once someone becomes a paying client. Remove all `status-` tags when adding a `client-` tag.

---

## 🔶 ACTION TAGS — What needs to happen next? (Temporary)

| Tag | Meaning |
|-----|---------|
| `action-follow-up` | Needs a follow-up message or call |
| `action-dm-sent` | DM was sent, waiting for response |
| `action-call-booked` | Discovery call is on the calendar |
| `action-proposal-sent` | Offer or proposal has been shared |
| `action-waiting-decision` | They said "let me think about it" |

**Rule:** **Temporary tags** — remove them once the action is complete. Think of them as task flags.

---

## Niche Adaptation

Adjust the tag set based on the client's actual coaching focus:
- Pure strength coach → drop `goal-hormones`, add `goal-mobility` or `goal-performance`
- Pure nutrition coach → drop `goal-strength`, expand goal-nutrition into `goal-fat-loss`, `goal-muscle-gain`, `goal-metabolic-health`
- Sources → only keep the channels they actually use; drop the rest

Always confirm the adapted set with the client before applying.

---

## MCP Operations

When executing via the GHL MCP, use these tool patterns:

### Add tags
```
add_contact_tags(contactId, ["src-instagram", "status-new", "interest-unknown"])
```

### Remove tags
```
remove_contact_tags(contactId, ["action-dm-sent"])
```

### Find contacts by tag
```
search_contacts(tag="status-hot")
```

### Bulk apply (use carefully)
For "add `client-active` to everyone in the Active stage of the Client Pipeline":
1. `search_opportunities(pipelineId, stage="Active")`
2. For each opportunity → get contact → `add_contact_tags(...)`
3. **Pause before execution** — read out the count and ask for confirmation.

---

## Common Operations (Templates)

### "I just got a new lead from Instagram"
1. Find or create the contact (`search_contacts` or `create_contact`).
2. Add: `src-instagram`, `status-new`, `interest-unknown`.
3. Tell client: "Done ✓ {name} is in your system, tagged as a new Instagram lead. Want me to add them to the Sales DM Pipeline next?"

### "Tag this person as hot"
1. Find contact.
2. Remove old `status-` tag (e.g. `status-new`).
3. Add `status-hot`.
4. Confirm: "Done ✓ {name} is now flagged as hot. Want to move them in the pipeline too?"

### "They enrolled!"
1. Remove ALL `status-` and `action-` tags.
2. Add `client-onboarding`.
3. Move them to the `Onboarding` stage of the Client Pipeline.
4. Celebrate: "🎉 That's huge — {name} is officially a client. They're tagged for onboarding and moved to the right place."

### "They said no / not a fit"
1. Add `status-not-a-fit`.
2. Remove all `action-` tags.
3. Move them to the `Lost / Not a Fit` stage of the Sales DM Pipeline.

---

## Bulk Operation Safety Rule

Before executing any tag change affecting **5+ contacts**:

> "I'm about to {action} for {N} contacts. That's a lot — let me list them first so you can verify nothing's off. Ready to see the list?"

After listing:

> "Look good? Want me to proceed with all {N}, or skip any?"

Never bulk-tag without explicit confirmation. Tags are reversible but cleaning up 50 wrongly-tagged contacts is a chore.

---

## Reassurance Scripts

**When client is overwhelmed:**
> "We don't have to set up every tag today. Want to start with just `src-` tags so you know where every lead came from? That alone is a game-changer."

**When client made a tagging mistake:**
> "No worries — totally fixable. I'll remove the wrong tag and add the right one. Done in two seconds."

**When client celebrates a milestone:**
> "{contact name} just moved from `status-hot` to `client-onboarding`. That's the whole reason this tag system exists — you can SEE the wins in real-time."
