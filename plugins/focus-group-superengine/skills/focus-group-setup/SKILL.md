---
name: focus-group-setup
description: Build a reusable synthetic focus-group PERSONA PACK for a brand/audience. Ingests the brand's real assets (site, socials, docs), derives the audience criteria — adaptive per niche, not hardcoded — asks the user to fill any gaps, and writes a portable JSON pack the run skill consumes. Trigger when the user wants to "set up a focus group", "build a persona pack / audience", "create an audience for testing", or runs /focus-group-setup. Works for ANY niche and any client, not just the operator's own brand.
---

# Focus Group — Setup (build the persona pack)

Builds the audience once; the `focus-group-run` skill reuses it. The pack is the portable IP — one per brand/client.

## Principle: belt & suspenders
Auto-gather what you can from real assets, then **query the user for every gap**. Tag every field with provenance: `found` (cite source), `asked` (user-provided), or `inferred` (low-confidence guess). Never leave a silent hole — and never silently guess a field you could ask about.

## Inputs (ask for what's missing — explicit only, never blind-scrape the machine)
- Brand/operator name + niche (one line).
- Website URL(s), social handles (for real language + audience signal).
- Optional: workspace research docs, prior audience data, a competitor or two.
- Who the audience is, in the user's words (seed; you'll refine).

## Step 1 — Ingest
Pull real signal from the provided assets only:
- Website copy → positioning, voice, offer, proof.
- Socials (via socialcrawl if available) → follower language, comment phrasing, who actually engages.
- Workspace docs / prior research → existing audience insight.
Capture **real phrasing** from comments/DMs — it makes personas talk like the market, not like stereotypes.

## Step 2 — Derive criteria (UNIVERSAL + ADAPTIVE)

**Business model — DERIVE FIRST; it cascades into every dim below.** Detect B2B / B2C / **hybrid-prosumer** from the offer, price point, and audience — do NOT force a binary:
- **B2C** → buyer = 1 person, fast/impulse; triggers = emotion/identity; objections = price/trust; casual language.
- **B2B** → buyer = a UNIT (champion / economic-buyer / blocker / end-user), slow cycle; triggers = ROI/risk/consensus/budget-cycle; objections = integration/security/team buy-in/procurement; formal. Personas carry a `buying_role` field.
- **hybrid-prosumer** → individual deciding on B2C emotion/speed but spending business money with a B2B ROI lens. Weight both. (Most coach/creator/SMB markets land here.)
If ambiguous after ingest, ASK. The chosen model reshapes decision-unit, triggers, objections, timeline, and language across all personas.

**Universal dims (always fill):** niche, sub-segments, demographics (age/gender/region/language), role/stage + revenue band, core pains, desired outcomes, general skepticism, platform behavior, real language/voice, buying triggers + price-sensitivity, trusted influences, **segment weights** (how common each segment is — pack mirrors the real mix, not 50/50).

**Adaptive dims (GENERATE 1–3 per niche — do NOT hardcode):** the domain-specific axis that actually predicts reactions in THIS market. Examples:
- AI-for-coaches → "AI sophistication: skeptic ↔ power-user"
- fitness coaching → "training experience: newbie ↔ advanced"
- B2B SaaS → "technical maturity"
- finance → "risk tolerance"
Infer the right axis from the niche; if unsure, ASK the user which distinction most divides their buyers.

## Step 3 — Gap-query (the suspenders)
For each criterion: mark `found` / `inferred` / `missing`. Then ask the user — **batched, specific, only the missing + low-confidence** ones. Not an interrogation; 3–6 targeted questions max per round.

Also ask the **Teach Mode** opt-in (default ON): "Want Teach Mode on? When it's on, I explain the *why* behind each move in plain English as we go — so you learn to read your own audience, not just get the verdict. Adds a line or two here and there; turn it off anytime by saying 'teach mode off.'" Record the answer as `meta.teach_mode` in Step 4.

## Step 4 — Synthesize the pack
Generate N persona objects (default 50; the run skill samples up for deep/hyperreal). Each persona:
`{ id, name, age, segment, stage, <adaptive_dim(s)>, skepticism, pain, desired_outcome, platform, voice, role }`
- **role** distribution mirrors a real audience: fence-sitter/indifferent MAJORITY, fewer enthusiasts, a few skeptics, a couple haters. Roles are lenses, not scripts.
- Spread personas across the universal + adaptive dims to match the segment weights.
- Keep each persona compact (~one line of attributes) — the run swarm needs signal, not backstory.

Write to `${CLAUDE_PLUGIN_DATA}/persona-pack-<brand-slug>-v<n>.json` with a `meta` block: audience summary, built_from sources, provenance per dim, segment_weights, role_distribution, `teach_mode` (`true` unless the user opted out at setup — the run skill reads this; the user can still toggle it per session), and a `provenance` caveat (v0 = inferred until calibrated against a real signal).

## Step 5 — Confirm
Show the user a short synthesized summary (audience in 5 lines + the adaptive axis chosen). Let them edit/approve. Lock on approval.

## Notes
- **Temperature is NOT baked into the pack** — the same personas are run cold or warm via a context injection in the run skill. The pack just describes WHO they are.
- **Reusable per client:** swap the brand inputs → new pack. This skill is brand-agnostic.
- Calibrate: the run skill's verdicts are directional until checked against one real audience signal (a poll, real comments). Note this in the pack meta.
