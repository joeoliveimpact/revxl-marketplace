---
name: offer-architect:intake-coach
description: Capture a coach's background, current offer state, ICA hypothesis, partners, brand voice, and constraints into a single Coach Profile doc. Use when onboarding a new coach to the offer-architect pipeline, or when starting a fresh build for an existing coach whose profile hasn't been formalized yet. Trigger phrases include "intake new coach", "capture coach background", "onboard a coach", "build coach profile".
---

# offer-architect:intake-coach

Produce a single Coach Profile document that captures everything downstream skills need.

## Step 0 — Locate or create the client folder

If no folder exists: `Clients/[Coach Full Name]/`. Create it. If one exists, use it.

## Step 1 — Pull what already exists

Before asking the coach anything, check whether brand/voice/business materials already exist on connected platforms:

- If `brand-voice:discover-brand` is available, invoke it to find existing brand docs, sales pages, content samples, past offer docs
- If `gws-docs` is available, ask the coach to drop URLs of any relevant existing Google Docs (intake forms, previous research, current sales page)
- Read any docs already in `Clients/[Coach Full Name]/`

Summarize what was found before asking new questions — never ask for info you already have.

## Step 2 — Structured intake (one AskUserQuestion batch per category, max 4 questions per batch)

Cover these categories. Each is a question or a small batch:

### Practice & credentials
- Years in practice, certifications, modalities, location, in-person vs. remote ratio

### Current offers (if any)
- Each existing offer: name, price, format, length, primary deliverable, close rate (est OK), churn (est OK), where leads come from

### Ideal Client Avatar (ICA) hypothesis
- Demographic (age range, gender, income, family stage, profession)
- Psychographic (what they want, what they fear, what's failed for them before)
- Where they hang out (online, in-person, communities)
- Two-frame question: who they CURRENTLY sell to vs. who they WANT to sell to

### Partners & warm channels
- Gym / studio partnerships, doctor/medical partnerships, telemedicine, supplement/peptide providers, affiliate programs, referral sources, existing audiences

### Voice & brand
- Brand name (if any), tagline, three adjectives that describe the voice
- Sample content (IG caption, call clip, etc.) — pull via `brand-voice` skill if available

### Constraints
- Time available per week for delivery
- Solo practitioner ceiling (clients/quarter max)
- Regulatory / liability exposure (e.g., peptides, TRT, supplements, dietary advice in regulated states)
- Tech stack already in use (TrueCoach, Voxer, GHL, Skool, Kajabi, etc.)
- Budget for tools, ads, partnerships

### Goals
- 90-day revenue goal
- 12-month revenue goal
- "What does success look like in 1 year?"

## Step 3 — Write the Coach Profile

Use `templates/coach-profile-template.md` from the plugin. Substitute variables, fill all sections from the answers + pulled artifacts. Save as:

`Clients/[Coach Full Name]/Coach Profile - [MM.DD.YY].md`

## Step 4 — Confirm and proceed

Show the coach the profile, ask if anything is missing or wrong. Update before exiting. Update the offer-build spec to mark `intake-coach` complete.

## Step 5 — Exit check

Before exiting, run the `intake-coach` checklist in `references/skill-exit-checks.md`. For each item:

- **PASS** → continue
- **GAP** → surface to coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"* If "defer", append to `tasks/findings.md` and footnote the artifact: `> ⚠️ Deferred from exit check: [item] — [reason]`
- **FAIL (hard)** → do not exit. Block until resolved.

The exit check is the preventive layer. The capstone PSS is the audit layer. Catching gaps here means the capstone's Top-5 priority fixes are real strategic improvements, not bookkeeping.

## Operating rules

- **Intent Clarification:** if the coach gives vague answers ("I don't know my close rate"), give them a way to estimate ("rough range: 1 in 10? 1 in 5? 1 in 20?") rather than skipping.
- **Least Complexity:** don't ask for info that doesn't matter to downstream skills. If a coach has no existing offer, skip the close-rate/churn questions entirely.
- **Surgical Execution:** the profile is a living doc — when re-running this skill later, append a new dated section, don't overwrite.
- **Declarative Focus:** the DoD is "downstream skills have everything they need without going back to the coach." If after writing the profile you find a downstream gap, return here and add the missing field.
