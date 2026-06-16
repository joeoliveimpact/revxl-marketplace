---
name: sales-call-blueprint-superengine:triage-blueprint
description: Build a 15-minute triage / qualification call blueprint from a prospect's DM thread, for the gatekeeper or setter — qualify and book the strategy call, never pitch or quote pricing. Use when prepping a booked triage or qualification call. Trigger phrases include "/sales-call-blueprint-superengine triage", "triage blueprint", "qualification call prep", "prep my triage call", "build a qualifier", "screen this lead before the sales call".
---

<purpose>
Generate a 15-minute triage (qualification) call blueprint from a prospect's DM thread. The caller is the gatekeeper, not the closer — the job is to qualify and book the strategy call with {{CLOSER_NAME}}, never to pitch or discuss specific pricing.
</purpose>

<user-story>
As a setter/gatekeeper at {{BRAND_NAME}}, I want a tight qualification blueprint built from the prospect's DMs, so that in 15 minutes I can confirm fit, surface dealbreakers, and book the strategy call — or redirect with respect.
</user-story>

<when-to-use>
- Prepping for a booked 15-minute triage / qualification call
- Entry point routes here via /sales-call-blueprint-superengine triage
</when-to-use>

<steps>

<step name="gather_input" priority="first">
Confirm the three gate answers; do NOT proceed until answered:
1. **Call type** — confirm triage (if strategy, route to the `strategy-blueprint` skill).
2. **Who is taking the call?** (the gatekeeper)
3. **Output mode** — Pre-Call Prep (deep), Call-Time Blueprint (live), or both?

Then collect the complete DM conversation and any intake-form data. Confirm ${CLAUDE_PLUGIN_ROOT}/references/business-config.md is current (the in/out criteria reference {{CORE_PROBLEM_SOLVED}} and {{DISQUALIFIER_FLOOR}}).

If DMs are thin, proceed under the thin-DM rule (${CLAUDE_PLUGIN_ROOT}/references/psych-profile.md) — flag gaps, don't fabricate. (Triage is usually first contact, so there's rarely a prior call — but if any prior recorded touchpoint exists, pull it via ${CLAUDE_PLUGIN_ROOT}/references/transcript-pull.md the same way.)

**Wait for response before proceeding.**
</step>

<step name="extract_profile">
Apply ${CLAUDE_PLUGIN_ROOT}/references/psych-profile.md. Focus the profile on qualification signals: real urgency vs. general dissatisfaction, investment capacity tells, decision authority (partner?), coachability, and any logistical flags (currency, timezone). Mark gaps `[CONFIRM LIVE]`.
</step>

<step name="build_qualification_plan">
**Specificity standard:** triage is tighter than a strategy call, but each section must still be hyper-customized to THIS prospect — see `${CLAUDE_PLUGIN_ROOT}/references/exemplar-strategy-blueprint.md` for the level of per-section detail (customized questions, what-to-listen-for + the red flag, landmines). Match that *style* of specificity, scaled to the 15-minute flow — never generic bullets.

Build the 15-minute structure:
1. **Set the Frame (60s)** — qualification, not a pitch. "If it's a fit we'll set up a strategy session with {{CLOSER_NAME}}; if not I'll point you somewhere better." Willingness to say no builds credibility.
2. **Diagnostic Why (2–3 min)** — the timing question + the authority question (why {{BRAND_NAME}} specifically).
3. **Operational Snapshot (3–4 min)** — hard numbers: revenue, lead-gen reality, delivery model.
4. **Gap Analysis (3–4 min)** — current state → 90-day target → the single biggest bottleneck.
5. **Logistics Check (1–2 min)** — only flagged dealbreakers.
Include the **pricing deflection script** (never quote specific pricing on triage) and the **in/out decision criteria**: qualifies if their bottleneck is {{CORE_PROBLEM_SOLVED}} with real urgency and a working delivery model; disqualify/redirect if below {{DISQUALIFIER_FLOOR}}, unproven delivery, or unresolvable dealbreaker. Provide both the "book the strategy call" script and the "redirect with respect" script (point to {{FREE_RESOURCE}}).
</step>

<step name="render_output">
Render the requested mode(s) using ${CLAUDE_PLUGIN_ROOT}/templates/precall-prep.md (deep, with the Call Structure swapped to the 15-min qualification flow) and/or ${CLAUDE_PLUGIN_ROOT}/templates/calltime-blueprint.md (live). Always include ${CLAUDE_PLUGIN_ROOT}/templates/post-call-notes.md as the post-call capture sheet so confirmed intel feeds a future strategy blueprint. Resolve {{config}} variables. Name output `[Prospect Name] - TRIAGE - [MM.DD.YY].md`.
</step>

<step name="review">
Run ${CLAUDE_PLUGIN_ROOT}/references/blueprint-quality.md (including the triage-specific items: no pricing, clear in/out, qualify-not-pitch). Fix any fails.

Present to the user. Ask: "Does this look right? Any adjustments?"

**Wait for approval or revision requests.** Draft until approved — do NOT deliver before the user signs off.
</step>

<step name="deliver">
ONLY AFTER approval: deliver the blueprint(s) to {{OUTPUT_DESTINATION}} using ${CLAUDE_PLUGIN_ROOT}/references/deliver-blueprint.md (may be a list). The post-call-notes sheet goes to the SAME destination so a later strategy run can find it. If destination unset, ask. Confirm the location back; fall back to local on failure.
</step>

</steps>

<output>
A triage qualification blueprint in the requested mode(s), plus a post-call notes sheet — customized to the prospect, config-resolved, quality-checked, named after the prospect.
</output>

<acceptance-criteria>
- [ ] Three gate questions answered
- [ ] Profile focused on qualification signals, gaps flagged not fabricated
- [ ] 15-minute structure with pricing deflection + in/out criteria
- [ ] Book-the-call AND redirect-with-respect scripts both present
- [ ] No specific pricing anywhere in the output
- [ ] Post-call notes sheet included
- [ ] Passed blueprint-quality.md
- [ ] User approved final output
</acceptance-criteria>
