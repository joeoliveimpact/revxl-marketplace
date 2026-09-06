---
name: offer-architect:build-offer-blueprint
description: Synthesis capstone for the offer-architect pipeline. Reads every prior artifact for a client (Coach Profile, Market Research, Value Stack, Pricing Matrix, Final Offer, transcripts), runs a gap-check + scored-option intake, dispatches the offer-market-auditor agent for a 4-check launch gate, and produces TWO outputs — a 3–5 page Offer Blueprint reference doc + a plain-English Projected Success Score report. Use as the final step after finalize-offer. Trigger phrases include "build offer blueprint", "generate the blueprint", "launch readiness score", "PSS", "score my offer".
---

# offer-architect:build-offer-blueprint

The synthesis capstone. Takes everything built across the pipeline and produces the foundational reference doc + launch-readiness score the coach uses to drive all downstream marketing, content, and delivery work.

## Hard rule — read this first

**Never invent bonuses, program components, guarantees, or offer pieces the coach hasn't confirmed.** Past systems hallucinated cool-sounding bonuses that the coach couldn't deliver, inflated the offer on paper, and delayed launch. The goal here is **launch fast with real deliverables**, not aspirational ones.

Every value-stack item, bonus, deliverable, and program component carries a provenance tag:
- `[confirmed]` — coach has it today, can deliver
- `[coach-to-build]` — coach agreed to build before launch, with effort estimate
- `[suggested-optional]` — skill suggested, coach has NOT committed

Default for any item without explicit coach confirmation: **OMIT, don't invent.**

## Step 0 — Read every artifact

Locate and read all of:
- `Clients/[Coach Name]/Coach Profile - *.md`
- `output/research/[Niche] - Market Research - *.md`
- `output/research/Gaps & Open Questions - *.md` (if exists)
- `output/research/Feasibility Scorecard - *.md` (if exists)
- `Clients/[Coach Name]/[Brand] Value Stack - *.md`
- `Clients/[Coach Name]/[Brand] Pricing Matrix - *.md`
- `Clients/[Coach Name]/[Brand] Final Offer - *.md` (if exists)
- Any transcripts in `Clients/[Coach Name]/`
- `references/pss-rubric.md` (your scoring rubric)
- `references/research-checklist.md` (audit evidence map)
- `templates/intake-required-fields.md` (your field schema)
- `templates/offer-blueprint-template.md` (output 1 shape)
- `templates/projected-success-score-template.md` (output 2 shape)

If Coach Profile or Market Research is missing, stop. Route the coach back through `intake-coach` and `research-market` first.

## Step 0b ... Brain pull: blueprint structure and launch-gate framing (via `revxl-vault-search`)

Wiring per [`../../references/vault-api.md`](../../references/vault-api.md). **Check `brain-pulls/` first**
... a cached pull for this offer means no invocation. No cache: ONE invocation of
`workspace-superengine:revxl-vault-search` with the Skill tool, args
`depth=med plugin=offer-architect spoke=frameworks-reference-library question: offer blueprint and launch readiness for <niche> <offer name> ... angles: offer document structure; naming frameworks; risk reversal; launch gate criteria`.
Read the echoed `spoke` back; anything other than `frameworks-reference-library` is
degraded.

Weave what comes back as **structure and ideas only**: it may reshape how a Blueprint section is framed, which naming angles are worth generating at Step 2, or how risk reversal is presented. It never supplies a
sentence. Never quote, closely paraphrase or reproduce the source text ... cite
`[brain] <path>` as the source of the idea, not of the words. Save the cited hits to
`brain-pulls/<offer-slug>.md`. At Step 9 (Hand-off to the coach) print exactly one evidence line:
`Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
No key, skill missing, mismatched spoke or any other failure ... degrade per the
reference, print the skipped line and keep going; the Brain never blocks this step.
This is **not** the market audit. `offer-market-auditor` runs later, at Step 5,
against a drafted Blueprint and with open-web evidence; this pull runs first and
only shapes the draft. Never feed Brain hits to the auditor as market data.
This is the only Brain invocation in this skill: 1 search and at most 2 note reads,
inside the cap of 2 searches + 3 note reads per named step.

## Step 1 — Intake gap-check (three modes)

Walk every required field in `templates/intake-required-fields.md`. For each:

### Mode A — Inferable from artifacts
Generate 2–3 scored options + 1-line "why" each. Present to coach. Coach picks or writes own.

**Scoring rubric** (general, /10): use the 5-axis rubric in `references/pss-rubric.md` — Specificity, Strategic fit, Differentiation, Believability, Memorability. 0–2 each.

**Defend-with-evidence rule (non-naming fields):** If the coach picks the materially weaker option, ask their reasoning. If the data clearly supports a different pick, push back once with the evidence (citing the research report). If the coach holds, accept their call and note it.

**Naming exception:** Naming is a taste call. Show options + scores, do not defend.

### Mode B — Direct-ask
For fields the artifacts can't reveal (e.g., chosen pricing structure A/B/C, guarantee type), ask one question at a time. No batched 20-question forms.

### Mode C — Deep-research-prompt
If a field requires evidence the workspace doesn't have AND a single WebSearch can't fill it (e.g., niche TAM, competitor pricing the coach has never gathered):

1. Render the matching prompt from `templates/deep-research-prompts/` — substitute `{{niche}}`, `{{ICA}}`, `{{competitor_names}}`, `{{geo}}`, `{{year}}` from artifacts
2. Hand it to the coach: "Paste this into ChatGPT Deep Research or Claude Deep Research. When you get the result, paste it back here."
3. Ingest the returned doc to `output/research/[Niche] - Deep Research Supplement - [MM.DD.YY].md`
4. Continue intake

## Step 2 — Naming pass (multi-framework, two-axis)

When the offer name is `inferable` (not already locked):

Generate **one candidate per framework**, minimum 4:

1. **Hormozi MAGIC** — Magnet, Avatar, Goal, Interval, Container word
2. **Watkins SMILE & SCRATCH** (Eat My Words) — Suggestive, Memorable, Imagery, Legs, Emotional; avoid SCRATCH pitfalls
3. **Igor Naming Guide** — Sound symbolism + positioning weight
4. **Marty Neumeier 7 criteria** (Zag) — Distinctive, Brief, Appropriate, Easy, Likable, Extendable, Protectable

Optional 5th: **Donald Miller StoryBrand** — name signals customer transformation.

Score each candidate on the **two-axis naming rubric** in `references/pss-rubric.md`:
- Cold-traffic conversion potential /10
- Brand-trust longevity /10

Display format:
> **"[Name]"** [Framework] — Cold-traffic: X/10 · Brand-trust: Y/10 — *[1-line why]*

**Default recommendation** based on auto-detected avatar sophistication:
- Premium / professional / high-sophistication → Neumeier or Watkins default
- Mass-market / cold-funnel / low-sophistication → MAGIC default

Coach picks. **Do not defend** any single option against coach preference — naming is taste.

## Step 3 — Mid-intake deliverable gates

Before drafting sections that require specific deliverables (bonuses, guarantees, program components, content angles):

Ask: **"Do you have [X] already? If yes, describe it. If no — do you want to build one before launch (rough effort estimate?), or skip it for this version?"**

Tag accordingly:
- "Yes, here it is" → `[confirmed]`
- "I'll build it before launch by [date]" → `[coach-to-build]`
- "Skip it" → OMIT entirely from the Blueprint

If the coach asks "What bonus could I add?" — only then suggest, and tag the suggestion `[suggested-optional]` until the coach explicitly accepts.

## Step 4 — Draft the Offer Blueprint

Use `templates/offer-blueprint-template.md`. Fill all 11 sections from the artifacts + intake answers.

Save to: `Clients/[Coach Name]/[Brand] Offer Blueprint - [MM.DD.YY].md`

Length target: **3–5 pages rendered**. Every section dense, no filler. Examples are 1-line samples, not full marketing copy.

Cite every claim back to its source artifact in §11.

## Step 5 — Dispatch the audit agent

Launch the `offer-market-auditor` agent with:
- Path to the drafted Offer Blueprint (Step 4 output)
- Paths to Market Research, Coach Profile, Value Stack, Pricing Matrix, Final Offer
- Path to `references/research-checklist.md`

Wait for the structured PASS/FLAG/FAIL verdict on all 4 checks.

### If audit returns INCOMPLETE (research gap)
1. Identify which deep-research prompts the auditor flagged
2. Hand the prompts to the coach for external execution
3. Ingest returned research
4. Re-dispatch the auditor with supplemented evidence

### If audit returns critical FAIL
Surface to the coach as a blocker before continuing to PSS:

> "The audit found a critical issue: [check name] FAILED. [1-line summary]. You can revise the offer, accept with caveat (which will cap your PSS in this area), or override. Which do you want?"

Coach decides. Record the decision in the Blueprint §11 if "accept with caveat" or "override".

## Step 6 — Calculate the PSS

Using the rubric in `references/pss-rubric.md`:

1. **Section scores (0–100 each, raw)** — score all 11 sections of the Offer Blueprint
2. **Apply provenance weighting** — items tagged `[coach-to-build]` count at 50%, `[suggested-optional]` at 0%
3. **Roll up to 10 dimensions** with the weights in the rubric
4. **Apply audit deductions** per the audit-to-PSS map
5. **Compute final PSS** = sum of weighted dimension scores
6. **Determine band**: 🔴 / 🟠 / 🟡 / 🟢 / 🟢🟢

## Step 7 — Generate the PSS report

Use `templates/projected-success-score-template.md`. Fill all sections.

**Writing voice — hard constraint:** every explanation written for a coach who barely knows business jargon. 7th-grade reading level. Examples:

- ❌ "Value Equation coefficient: 0.6, dream-outcome inflation suboptimal"
- ✅ "Your offer promises a real result, but it's not specific enough. 'Get healthier' is too vague — try 'lose 15 lbs in 90 days' so people can picture exactly what they'll get."

Top 5 priority fixes — rank by (score gap × dimension weight). For each, give:
- What to fix (plain English)
- Why it matters (1–2 sentences, no jargon)
- Effort (Quick win / 1 week / 2+ weeks)
- Estimated PSS lift

Launch verdict — pick one based on band. **Only 90+ signals "launch now":**
- 🔴 0–20 / 🟠 20–50 → "Not yet — fix the red items"
- 🟡 50–70 → "Tighten before launch — workable but soft"
- 🟢 70–90 → "Close to launch-ready — fix top items, then go"
- 🟢🟢 90+ → "Launch-ready — go now"

Speed-to-launch note (when applicable): "You can launch now at [current score], or invest [X weeks] to lift to [projected score]. Your call."

Save to: `Clients/[Coach Name]/[Brand] Projected Success Score - [MM.DD.YY].md`

## Step 8 — Update workspace state

- Append a session entry summary to `Checkpoint.md`
- Update `tasks/STATUS.md` (move related items to Done)
- If a spec file exists in `.claude/specs/in-progress/`, move it to `completed/`
- Update `tasks/findings.md` with any non-obvious discoveries during the run

## Step 9 — Hand-off to the coach

Print a final summary to the coach:

```
✅ Offer Blueprint generated: [path]
✅ Projected Success Score: [XX]/100 — [band label]

Top 3 things to do next:
1. Read the Blueprint (3–5 pages)
2. Review the PSS — especially Top 5 priority fixes
3. [If launch-ready] Hand the Blueprint to your marketing tool / writer / next plugin
   [If not] Address the top priority fix, then re-run this skill
```

## Operating rules

- **Two outputs, every run.** Offer Blueprint + PSS report. Never one without the other.
- **Provenance tags everywhere.** Default to OMIT, not INVENT.
- **Audit is non-optional.** No PSS without the audit running. Audit gaps trigger deep-research prompts, not assumed PASSes.
- **PSS voice is 7th grade.** If a sentence needs a glossary, rewrite it.
- **Speed-to-launch over perfection.** Flag the tradeoff; let the coach decide.
- **Re-runnable.** If the coach revises and wants a fresh score, re-run — filename gets `-v2` suffix.
