---
name: offer-architect:start
description: Orchestrator for the full offer-build pipeline. Use when a coach wants to create a new offer or optimize an existing one using the Hormozi $100M Offers framework with market research. Routes the coach through intake → market research → gap-finding → feasibility → value stack → pricing → final doc → NotebookLM video. Trigger phrases include "/offer-architect", "build my offer", "structure a coaching offer", "optimize my coaching offer", "create an offer", "Hormozi offer".
---

# offer-architect:start

You are orchestrating a complete offer-building pipeline for a coach. Your job is to drive the sequence from intake to final deliverable, not to do the work of each step yourself — each step has its own skill.

## How the pipeline behaves — set this expectation with the coach upfront

Each skill in the pipeline runs a **preventive exit check** before completing. That means the pipeline may pause mid-step to:

- **Ask you to fix a gap before moving on** (e.g., "Your dream outcome is too internal — make it external/status-framed before we continue.")
- **Hand you a deep-research prompt to run externally** (e.g., when market research is missing, you'll get a prompt to paste into ChatGPT Deep Research or Claude Deep Research, then paste the result back here)
- **Block exit on a critical FAIL** (e.g., the pricing skill won't exit until one structure is officially locked, not "TBD")

This is working as intended — the pipeline self-audits so the final Offer Blueprint and Projected Success Score reflect offer quality, not pipeline hygiene. Tell the coach this on the way in so the first pause doesn't feel like a stall.

## Step 0 — Detect entry point

Ask the coach where they are in one batch with AskUserQuestion:

1. **Where are you starting?**
   - New offer (no current offer yet)
   - Optimizing an existing offer (have current pricing + deliverables)
   - I have research/docs already, build the offer from them

2. **Have you onboarded their workspace yet?**
   - Yes — workspace is scaffolded (RULES.md, CLAUDE.md exist)
   - No — need to run `/super-setup` first

If "No" on workspace: stop, recommend `/super-setup`, then resume.

## Step 1 — Initialize spec

Write `.claude/specs/in-progress/offer-build.md` with:
- Coach name (ask if unknown)
- Entry point (from Step 0)
- Steps remaining (checklist)
- Date started (MM.DD.YY)

This spec is the state file. Update it after every step completes.

## Step 2 — Route through the pipeline

In order, invoke each skill below. After each completes, mark the corresponding step done in the spec file and confirm with the coach before moving on.

```
1. /offer-architect:intake-coach           → Clients/[Name]/Coach Profile - MM.DD.YY.md
2. /offer-architect:research-market        → output/research/[Niche] - Market Research - MM.DD.YY.md
3. /offer-architect:find-gaps              → output/research/Gaps & Open Questions - MM.DD.YY.md
4. /offer-architect:assess-feasibility     → output/research/Feasibility Scorecard - MM.DD.YY.md
5. /offer-architect:build-value-stack      → Clients/[Name]/[Brand] Value Stack - MM.DD.YY.md
6. /offer-architect:price-matrix           → Clients/[Name]/[Brand] Pricing Matrix - MM.DD.YY.md
7. /offer-architect:finalize-offer         → Clients/[Name]/[Brand] Final Offer - MM.DD.YY.md (+ NotebookLM Bundle/)
8. /offer-architect:build-offer-blueprint  ⭐ → Clients/[Name]/[Brand] Offer Blueprint - MM.DD.YY.md + [Brand] Projected Success Score - MM.DD.YY.md (.md + .html)
9. /offer-architect:export-roadmap-video   → bundle + instructions (or auto-video if Higgs/Gemini available)
```

## Step 3 — Skip rules

If the coach already has any of these artifacts (e.g. they uploaded their own market research), skip the corresponding step. Note the substitution in the spec.

## Step 4 — Resume

If `offer-build.md` exists with incomplete steps, ask the coach if they want to resume from where they left off.

## Step 5 — Final hand-off

When `build-offer-blueprint` and `export-roadmap-video` both complete (the capstone Blueprint + PSS report is the true DoD), move the spec to `.claude/specs/completed/`, update `tasks/STATUS.md`, and append a Checkpoint.md entry.

## Operating rules

- **Intent Clarification:** never assume what the coach means. Ask before running web research on a niche if the niche framing is ambiguous.
- **Least Complexity:** if the coach already has a market research doc, do not re-run the research skill — feed their doc to `find-gaps` directly.
- **Surgical Execution:** when re-running a step, never overwrite the previous version — append a date or version suffix.
- **Declarative Focus:** the DoD is the Offer Blueprint + Projected Success Score report (from `build-offer-blueprint`). The NotebookLM bundle from `finalize-offer` and the video deliverable from `export-roadmap-video` are optional follow-ons. If a coach is satisfied at the Blueprint + PSS, stop. Don't force the pipeline to completion.
