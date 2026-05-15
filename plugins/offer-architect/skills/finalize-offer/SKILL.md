---
name: offer-architect:finalize-offer
description: The finisher. Reads every artifact built so far, asks the coach a sequenced set of decision questions, resolves all open gaps, and produces ONE consolidated final offer document plus a NotebookLM-ready bundle for the 3-minute roadmap video deliverable. Use as the last step in the offer-architect pipeline. Trigger phrases include "finalize my offer", "build the final offer doc", "wrap up the offer", "ship the offer".
---

# offer-architect:finalize-offer

⭐ The skill Joe committed to in the 05.13.26 Jared call. Takes every upstream artifact and produces a single canonical final offer doc + NotebookLM bundle.

## Step 0 — Read every artifact

Locate and read all of:
- `Clients/[Coach Name]/Coach Profile - *.md`
- `output/research/[Niche] - Market Research - *.md`
- `output/research/Gaps & Open Questions - *.md`
- `output/research/Feasibility Scorecard - *.md`
- `Clients/[Coach Name]/[Brand] Value Stack - *.md`
- `Clients/[Coach Name]/[Brand] Pricing Matrix - *.md`
- Any uploaded notes / decisions from the coach in `Clients/[Coach Name]/`

If any are missing, stop and route back through the pipeline.

## Step 1 — Decision question pass (sequenced AskUserQuestion batches)

Walk the coach through the unresolved decisions, in order. Max 4 questions per batch:

### A. Positioning lock
- Confirm the primary positioning from the feasibility scorecard
- Confirm the fallback positioning

### B. Pricing structure lock
- Which structure (A / B / C) to launch with
- Founding-cohort pricing? Yes / no
- Maintenance tier price confirmed

### C. Name lock
- Pick the external offer name from MAGIC candidates
- Tagline (≤ 12 words)
- Internal tier name (for ops clarity)

### D. Inclusions lock
- For each ambiguous add-on (VO2 mobile, DEXA, supplements, etc.), confirm: included / subsidized / client-pays
- Bonus set confirmed (subtract any the coach won't deliver)
- Guarantee set confirmed (no surprises)

### E. Open question resolution
- For every blocking gap from `find-gaps`, present the gap + ask for the coach's answer or "deferred"

### F. Voice & brand
- If `brand-voice:enforce-voice` is installed, ask whether to apply voice on the final doc
- If no brand voice exists, ask the coach for 3 adjectives + 1 example sentence in the voice they want — fold into the writing

### G. Distribution & delivery channel decisions
- Sales mechanism: application + discovery call / direct buy / both
- Onboarding flow (intake form, kickoff call, kit shipping if applicable)
- Communication channels (Voxer / WhatsApp / Email / Loom / Zoom)

## Step 2 — Produce the consolidated final offer document

Use `templates/final-offer-template.md`. Sections:

1. **The offer in one sentence** — pure positioning
2. **The complete value stack** — locked components from `build-value-stack`
3. **The complete pricing ladder** — the selected structure with all tiers
4. **Bonuses (locked)** — final list with anchored values
5. **Guarantees (locked)** — final 3 stacked guarantees
6. **Scarcity & urgency** — locked
7. **Naming & tagline** — final
8. **Maintenance tier** — final
9. **"Coach Reviews" thoroughness layer** — 10-15 categories with cadence
10. **Sales mechanism + onboarding flow** — application URL, discovery call format, kickoff sequence
11. **Operational delivery spec** — week-by-week client experience, tools used, time commitment for coach
12. **Brand voice fingerprint** — three adjectives + example sentence + lean-in / lean-out rules
13. **Hand-off package** — sections that copy directly into: (a) sales page, (b) onboarding email, (c) discovery call script template
14. **Open items deferred** — any non-blocking gap the coach chose to defer
15. **Validation plan** — what to track in first 90 days

Save to: `Clients/[Coach Name]/[Brand] Final Offer - [MM.DD.YY].md`

## Step 3 — Produce the NotebookLM bundle

Create the folder: `Clients/[Coach Name]/[Brand] NotebookLM Bundle/`

Drop in:
1. `00 - Speaker Notes for 3-Min Roadmap Video.md` — outlined script (intro, dream outcome, the 5 protocol pillars, what the next 30 days look like, the close)
2. `01 - Final Offer Summary.md` — copy of §1, §2, §3 of the final doc (slim for NotebookLM source ingestion)
3. `02 - Value Stack Highlights.md` — top 10 components from the value stack with retail anchors
4. `03 - The Coach Reviews List.md` — the 14-category review layer (trust signal in the video)
5. `04 - Client Journey - Week-by-Week.md` — the first-30-days experience
6. `05 - Three Guarantees.md` — the risk reversal portion
7. `Sources.md` — pointer back to the research doc + book reference + workspace `Hormozi - 100M - Offers - Book.md`
8. `NotebookLM Import Instructions.md` — explicit step-by-step for the coach to import + generate the 3-min audio overview / video

If a Higgs Field or Gemini video connector is configured (per Joe's transcript line 87), invoke that path automatically and save the generated MP4 to `output/html/`.

## Step 4 — Brand voice pass

If `brand-voice:enforce-voice` is installed:
- Run it on the final offer doc
- Run it on the speaker notes (most critical — the video viewer experiences the voice directly)

If not installed, do a manual voice pass: re-read with the coach's three adjectives in mind, adjust sentence cadence and word choice. Flag passages the coach should review.

## Step 5 — Hand-off summary

Write a 1-page handoff summary to `Clients/[Coach Name]/HANDOFF.md` listing:
- Final offer doc location
- NotebookLM bundle location
- Next 3 actions for the coach (typically: import bundle to NotebookLM → generate audio overview → review and approve)
- Tracking checklist for first 90 days

Update `tasks/STATUS.md`, append `Checkpoint.md`, rewrite `handoff.md`. Move `offer-build.md` spec to `.claude/specs/completed/`.

## Step 6 — Next step pointer

After finalize, recommend the capstone:

> "Your final offer doc is locked. To produce the **Offer Blueprint** (3–5 page reference doc) + **Projected Success Score** (launch-readiness report) for downstream marketing/content tools, run `/offer-architect:build-offer-blueprint` next."

## Step 7 — Exit check

Before exiting, run the `finalize-offer` checklist in `references/skill-exit-checks.md`. For each item:

- **PASS** → continue
- **GAP** → surface to coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"* If "defer", append to `tasks/findings.md` and footnote the artifact: `> ⚠️ Deferred from exit check: [item] — [reason]`
- **FAIL (hard)** → do not exit. Block until resolved.

Critical FAIL items for this skill:
- Guarantee text not verbatim / copy-pastable
- Offer name still "candidate" — must be LOCKED
- Pricing structure not inherited as LOCKED from price-matrix (last chance to enforce)

This is the last preventive layer before the capstone `build-offer-blueprint` runs the full PSS audit. Everything that leaks past finalize-offer becomes a top-5 priority fix on the PSS report — which is bad UX for the coach. Catch it here.

## Operating rules

- **One canonical doc.** The final offer doc is the source of truth. Earlier docs are inputs, not deliverables.
- **Decisions are explicit.** Every locked decision in §1 is traceable to a coach answer in the Q&A pass. Don't infer.
- **Voice is not optional.** If the coach didn't capture voice in intake, capture it here. The final doc has to *sound like the coach*.
- **NotebookLM bundle is the finisher's finisher.** Do not skip it. This is the deliverable Jared specifically asked for.
- **Re-runnable.** If the coach later wants to revise, this skill can be re-run — append `-v2` to the filename and to the spec.
