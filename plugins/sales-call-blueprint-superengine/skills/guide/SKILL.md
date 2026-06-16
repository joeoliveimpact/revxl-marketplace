---
name: sales-call-blueprint-superengine:guide
description: First-time plain-English tour of the sales-call blueprint superengine, for new or non-technical users. Walks through what it does in plain language, runs setup, and builds the first blueprint with extra hand-holding. Trigger phrases include "/sales-call-blueprint-superengine guide", "first time", "how do I use this", "walk me through the blueprint skill", "I'm new", "help me get started with blueprints".
---

<purpose>
First-time guided tour. Walks a new user through what the skill does in plain English, runs setup, and offers to build their first blueprint with extra hand-holding. Keeps it friendly and jargon-light — translate every technical term inline.
</purpose>

<user-story>
As someone using this skill for the first time, I want a quick plain-English walkthrough of what it does and how to use it, so that I'm not staring at commands I don't understand — and I end the tour with a working setup and my first blueprint.
</user-story>

<when-to-use>
- First run — auto-offer this when ${CLAUDE_PLUGIN_ROOT}/references/business-config.md still has placeholder/example values, OR the user says "first time", "how do I use this", "walk me through", "help", "I'm new".
- Entry point routes here via /sales-call-blueprint-superengine guide.
- Skip for returning users who know what they want (go straight to triage/strategy).
</when-to-use>

<steps>

<step name="welcome" priority="first">
Give a short, plain-English orientation (no wall of text). Cover, in your own friendly words:
- **What this does:** "You paste me the conversation (or call recording) that led to a booked sales call, and I hand you a battle-plan for that call — who they are, what they actually want, the order to ask things, the objections coming, and how to close."
- **Two call types:** *triage* = the quick 15-min 'are they a fit' call; *strategy* = the full closing call.
- **Two outputs:** *Pre-Call Prep* = the deep doc you read beforehand; *Call-Time Blueprint* = the one-screen cheat-sheet you keep open during the call. You can get one or both.
- **It uses your own playbook** (the RFPDP method, your objection handling) — not generic sales advice.
Then: "Want the 60-second tour, or should I just set you up and build one?" **Wait.**
</step>

<step name="how_to_use">
ALWAYS show this compact "Here's how you use it" card before setup — even if the user skips the tour. Don't move past it silently.
- **Build a blueprint:** run `strategy` (full closing call) — or `triage` (15-min qualifier) if your business runs those — or just paste the conversation. I'll ask: which call type (only if you do triage) · who's taking it · which output.
- **What to give me (easiest):** just paste everything — the DM/chat thread, any notes, even the call transcript. Pasting is usually fastest. Only lean on auto-pull (Fathom/GHL/Drive) if you ALREADY have it connected; otherwise don't bother hunting, just paste. Thin/no thread is fine — I flag gaps, never invent.
- **Two outputs:** Pre-Call Prep (deep, read beforehand) · Call-Time Blueprint (one-screen, during the call) · or both.
- **Where it lands:** auto-saved to your configured destination (e.g. Google Drive dated folder); I confirm the link.
- **Batch:** "blueprint these 8" → the agent builds them all at once.
- **Housekeeping:** `setup` to reconfigure · `guide` for this tour · "explainer off" (= quick mode) to stop the step-by-step narration.
</step>

<step name="how_it_works">
If they want the tour, explain each piece in 1-2 plain lines each, naming the term then glossing it:
- **Setup** — "I fill in your brand/program details by reading where they already live (your CLAUDE.md, website, Drive) so you don't type a form."
- **Transcript pull** — "If there was an earlier call, I can grab its transcript from your recorder (Fathom, Fireflies, etc.) and fold it in. No recorder? Paste it or skip it."
- **The blueprint** — "I read the conversation, build a profile of the person, rank what to ask, and pre-load the objections."
- **Delivery** — "I send the finished blueprint wherever you want — Google Drive in dated folders, a file here, a note on their CRM contact, or just on screen."
- **Pricing** — "I never store your prices. You say the number live; I just structure how to drop it."
Keep it conversational. Invite questions before moving on.
</step>

<step name="run_setup">
Hand off to setup: "Let's get you configured — takes a minute." Run the `setup` skill (auto-discover brand data, set transcript source + output destination, dependency check). Come back here when done.
</step>

<step name="first_blueprint">
Offer to build their first one together, with extra hand-holding: "Paste the DM thread or point me at a call recording for a real upcoming call, and I'll build your first blueprint — I'll explain each step as I go." Route to triage or strategy based on their answer. While {{EXPLAINER_MODE}} is on, narrate what each step is doing and why.
</step>

<step name="set_mode">
At the end, ask: "Want me to keep explaining each step as we go (good while you're learning), or switch to quick mode now that you've seen it?" Set {{EXPLAINER_MODE}} in ${CLAUDE_PLUGIN_ROOT}/references/business-config.md accordingly. Remind them they can say "explainer on/off" anytime.
</step>

</steps>

<output>
An oriented first-time user with a populated config, a dependency report, their first blueprint delivered, and {{EXPLAINER_MODE}} set to their preference.
</output>

<acceptance-criteria>
- [ ] Plain-English orientation given (what it does, call types, two outputs) — jargon glossed inline
- [ ] "Here's how you use it" card shown (always, even if the tour was skipped)
- [ ] Setup run (config populated, dependencies checked)
- [ ] Offered to build a first blueprint with step-by-step narration
- [ ] {{EXPLAINER_MODE}} set to the user's preference at the end
</acceptance-criteria>
