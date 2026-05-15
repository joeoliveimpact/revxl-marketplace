---
name: offer-architect:export-roadmap-video
description: Generate a NotebookLM-importable bundle (and optionally an MP4 via Higgs Field / Gemini video connector) for a 3-minute client-facing offer roadmap video. Use after finalize-offer to produce the deliverable Jared specifically requested in the 05.13.26 call. Trigger phrases include "generate roadmap video", "NotebookLM bundle", "3 minute video for the offer", "export the offer video".
---

# offer-architect:export-roadmap-video

The deliverable Jared asked for: a 3-minute video that walks a prospect through their personalized roadmap. NotebookLM-ready bundle in v1; optional auto-generation in v0.2.

## Step 0 — Read inputs

- `Clients/[Coach Name]/[Brand] Final Offer - *.md` (required — stop if missing)
- Optionally: prospect intake info if the video is for a specific lead
- The existing NotebookLM bundle written by `finalize-offer`

## Step 1 — Decide: generic or per-prospect?

Ask the coach:
- **Generic** — One reusable bundle for prospects in general (default for first run)
- **Per-prospect** — Customized bundle for a specific lead who's been intaked (more powerful; sales tool)

If per-prospect, ask for the lead's intake info (name, age, primary pain, top biomarker concern, lifestyle context). Personalize the speaker notes.

## Step 2 — Refresh the NotebookLM bundle

If `finalize-offer` already wrote the bundle, read it. Otherwise create it now using the same structure (00 Speaker Notes through Sources.md).

For per-prospect: customize `00 - Speaker Notes` with the prospect's name and their specific pain points. Re-write the intro and the "what your first 30 days look like" section.

## Step 3 — Choose output format

Three paths:

### Path 1 — NotebookLM bundle only (v1 default)
- Ensure the bundle is complete
- Write `NotebookLM Import Instructions.md` with explicit click-by-click steps:
  1. Go to notebooklm.google.com
  2. Create new notebook
  3. Upload all bundle .md files as sources
  4. Generate "Audio Overview" → "Customize" → set to 3 minutes max
  5. Optional: use the prompt template (provided in instructions) to direct the generation toward a sales-roadmap framing rather than a generic summary
  6. Download the result
- Done — coach handles generation in NotebookLM UI

### Path 2 — Higgs Field connector (v0.2, if available)
- Check if Higgs Field or Gemini video MCP/connector is configured
- If yes: invoke the connector with the speaker notes + a visual style prompt (default: clean, branded, with biomarker dashboard visuals)
- Save the generated MP4 to `output/html/` or `output/markdown/` depending on format
- If the connector fails or isn't available, fall back to Path 1

### Path 3 — Gemini video presentation (v0.2, if Joe's connector is wired)
- Joe mentioned this in transcript line 87
- Same fallback rule: if unavailable, default to Path 1

For v1, default to Path 1 unless the coach explicitly requests video auto-generation AND a connector is configured.

## Step 4 — Validate

The bundle should be self-contained — a coach with zero context could drop it into NotebookLM and get a coherent 3-minute audio overview. Check:
- ✅ Speaker notes flow (intro → dream → protocol → first 30 days → close)
- ✅ Sources file points to the offer doc + book reference + workspace research
- ✅ Coach's voice fingerprint is present in the speaker notes (not generic AI tone)
- ✅ Length budget: ~450 words for a 3-min audio = the speaker notes should sit at 400-500 words

If validation fails on any check, fix before exiting.

## Step 5 — Hand-off

Update `HANDOFF.md` for the coach with:
- Path to bundle
- Next action (import to NotebookLM)
- Estimated time to generate (5-10 min)
- What to do with the output (review, optionally re-record in their own voice, embed on sales page or send via DM)

Update `tasks/STATUS.md` to mark the video export as complete.

## Operating rules

- **Self-contained bundle.** Anyone (coach, VA, partner) should be able to import + generate without re-reading the entire pipeline.
- **Voice over polish.** A 3-min video that sounds like the coach beats a polished 5-min generic one.
- **Don't auto-publish.** The output is for the coach to review and approve before they ship it to prospects.
- **Per-prospect mode is high-leverage.** A customized 3-min video sent to a specific lead converts at multiples of a generic one. Push coaches toward this once they've used the generic mode once.
