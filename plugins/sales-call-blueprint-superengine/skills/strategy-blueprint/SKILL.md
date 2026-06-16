---
name: sales-call-blueprint-superengine:strategy-blueprint
description: Build a full RFPDP strategy / closing call blueprint from a prospect's DM thread (and any prior triage notes) — deep psychological profile, ranked discovery, objection playbook, and pitch structure. Use when prepping a booked strategy, discovery, sales, or closing call. Trigger phrases include "/sales-call-blueprint-superengine strategy", "strategy blueprint", "closing call prep", "prep my sales call", "build a strategy call plan", "blueprint this discovery call".
---

<purpose>
Generate a full RFPDP strategy / closing-call blueprint from a prospect's DM thread (and any triage notes), in the requested output mode(s). This is the heavy workflow — deep psychological analysis plus a ranked, customized call plan that hands the closer an unfair advantage.
</purpose>

<user-story>
As {{CLOSER_NAME}} (or any closer at {{BRAND_NAME}}), I want a customized strategy-call blueprint built from the prospect's own words, so that I walk in knowing their psychology, the right discovery order, and every likely objection before they raise it.
</user-story>

<when-to-use>
- Prepping for a booked strategy / closing call (a.k.a. discovery, sales, or {{STRATEGY_CALL_NAME}})
- Triage notes exist and need folding into a deeper strategy plan
- Entry point routes here via /sales-call-blueprint-superengine strategy
</when-to-use>

<steps>

<step name="gather_input" priority="first">
Confirm the three gate answers and collect the material. Do NOT proceed until all are answered:
1. **Call type** — confirm this is a strategy call (if triage, route to the `triage-blueprint` skill instead).
2. **Who is taking the call?**
3. **Output mode** — Pre-Call Prep (deep), Call-Time Blueprint (live), or both?

Then collect:
- The complete DM conversation that led to the booking (paste-in).
- Any prior triage notes (treat as confirmed discovery data, not assumptions).
- Confirm ${CLAUDE_PLUGIN_ROOT}/references/business-config.md values are current (especially {{PROGRAM_LENGTH}}). Pricing is supplied live, not stored.

If the DM thread is thin or missing, say so and proceed under the thin-DM rule (${CLAUDE_PLUGIN_ROOT}/references/psych-profile.md) — flag gaps, don't fabricate.

**Wait for response before proceeding.**
</step>

<step name="pull_prior_transcript">
If a prior call exists (usually the triage call) and no triage notes were pasted, pull its transcript using ${CLAUDE_PLUGIN_ROOT}/references/transcript-pull.md and the {{TRANSCRIPT_SOURCE}} set in ${CLAUDE_PLUGIN_ROOT}/references/business-config.md. Discover the source's exact tools via ToolSearch, fetch by prospect name / date / pasted URL, and extract confirmed intel (revenue, bottleneck, goal, urgency, partner, coachability, phrases to mirror). If retrieval fails or {{TRANSCRIPT_SOURCE}} = manual, ask for a paste; if none exists, proceed from the DMs alone and flag the gap. Treat anything retrieved as confirmed intel to deepen — not re-ask — in discovery.
</step>

<step name="extract_profile">
Apply ${CLAUDE_PLUGIN_ROOT}/references/psych-profile.md to the DM thread. Document the five dimensions (pain & urgency, commitment signals, objection previews, language/style, relationship context), the decision-making pattern, and a trust calibration. Mark every gap `[CONFIRM LIVE]` / `[NOT IN DMs]`. If triage notes exist, fold confirmed data in here.
</step>

<step name="build_call_plan">
Construct the RFPDP call plan using ${CLAUDE_PLUGIN_ROOT}/references/rfpdp-method.md and ${CLAUDE_PLUGIN_ROOT}/references/high-impact-questions.md:
- Customize Rapport, Frame, and the opening Pain question to this prospect's exact words and energy.
- **Rank the 10 discovery topics** for THIS prospect (Pain first, Trust last by default, but order by their situation). For each: customized questions, what to listen for, the landmine. Note triage-confirmed topics to deepen rather than re-ask.
- Build the Pitch: temperature check → 2–4 custom pillars (pain → solution → why-not-alone) → brief delivery → price drop (you handle all pricing — state your investment and stop talking; the skill prescribes no prices, discounts, or terms).
- Build the Objection Playbook with ${CLAUDE_PLUGIN_ROOT}/references/objection-handling.md: pre-identified objections from the DMs + anticipated ones, each with isolate→reframe.
- Write Closing Strategy + Critical Success Factors ("remember only 3 things").
</step>

<step name="render_output">
Render the requested mode(s):
- **Pre-Call Prep** → ${CLAUDE_PLUGIN_ROOT}/templates/precall-prep.md (lead with the narrative risk-brief to the caller).
- **Call-Time Blueprint** → ${CLAUDE_PLUGIN_ROOT}/templates/calltime-blueprint.md (compress FROM the deep doc so they stay consistent).
- **Both** → generate the deep doc first, then derive the live card from it.
Resolve all {{config}} variables. Name the output `[Prospect Name] - STRATEGY - [MM.DD.YY].md`.
</step>

<step name="review">
Run ${CLAUDE_PLUGIN_ROOT}/references/blueprint-quality.md against the output. Fix any fails.

Present the blueprint(s) to the user.
Ask: "Does this look right? Any adjustments — discovery order, objections, the pitch pillars?"

**Wait for approval or revision requests.** Per workspace rules, this is a draft until approved — do NOT deliver before sign-off.
</step>

<step name="deliver">
ONLY AFTER approval: deliver the blueprint(s) to {{OUTPUT_DESTINATION}} using ${CLAUDE_PLUGIN_ROOT}/references/deliver-blueprint.md (google-drive / local / ghl-note / chat / custom — may be a list). If unset, ask where it should go. Confirm the exact location/link back. On a destination failure, fall back to local and say so.
</step>

</steps>

<output>
A strategy-call blueprint in the requested mode(s): a deep Pre-Call Prep doc, a live Call-Time Blueprint, or both — fully customized to the prospect, config-resolved, quality-checked, and named after the prospect.
</output>

<acceptance-criteria>
- [ ] Three gate questions answered (call type, caller, output mode)
- [ ] Prior-call transcript pulled from {{TRANSCRIPT_SOURCE}} (or paste / none-with-gap-flagged)
- [ ] Psychological profile extracted with gaps flagged, not fabricated
- [ ] Discovery topics ranked for this specific prospect
- [ ] Objection playbook built from DM-evidenced + anticipated objections
- [ ] Output mode(s) rendered with config variables resolved
- [ ] Passed blueprint-quality.md
- [ ] User approved final output
</acceptance-criteria>
