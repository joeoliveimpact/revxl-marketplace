---
name: offer-architect:research-market
description: Run deep web research on a coach's niche and market — TAM/SAM sizing, competitor pricing and positioning, regulatory landscape, premium anchors, add-on test costs. Produces a cited research doc that all downstream offer-architect skills reference. Use after intake-coach. Trigger phrases include "research the market", "research my niche", "competitor research", "pricing research".
---

# offer-architect:research-market

Run a standardized market-research pass and write a cited report. Every claim must have a linked source.

## Step 0 — Read inputs

- `Clients/[Coach Name]/Coach Profile - *.md` — for niche, ICA, current pricing
- Any uploaded prior research the coach has

## Step 1 — Run the research checklist

Use the checklist in `references/research-checklist.md`. At minimum, do these passes via WebSearch (4-6 parallel queries):

1. **Niche market size + trajectory (2026 data)** — TAM/SAM, growth rate, key demand signals
2. **Competitor pricing benchmarks** — 3-5 named competitors at low / mid / high tier; ladder lengths (1mo / 3mo / 6mo / 12mo / VIP); features and positioning
3. **Regulatory + liability landscape** — anything specific to the niche (peptides, hormones, dietary advice, mental health claims, scope-of-practice issues)
4. **Premium / concierge anchors** — high-end reference points (e.g., Fountain Life APEX, LifeSpan Medicine for longevity; Equinox+ for fitness; Bulletproof Labs; etc.) to anchor the upper pricing ceiling
5. **Add-on test costs** — any in-person tests, blood work, scans relevant to the niche (DEXA, VO2 max, gut testing, hormone panels) with 2026 retail pricing
6. **ICA validation signals** — recent articles, Reddit threads, podcasts, trend data showing the ICA is actively buying

Use the **current year (2026)** in every query.

## Step 2 — Synthesize

Use `templates/market-research-template.md`. Structure:

- §1 Niche definition + ICA
- §2 Market size & trajectory (cited)
- §3 Pricing benchmarks table (Low / Mid / High across all container lengths)
- §4 Named competitors (3-5) with positioning, pricing, what they do, what they don't
- §5 Regulatory / liability landscape with specific statutes/agencies
- §6 Premium anchors (concierge tier comparables)
- §7 Add-on tests + pricing
- §8 ICA validation evidence
- §9 Recommended positioning (1-3 alternative bets — these feed `assess-feasibility`)
- §10 Sources (full URL list)

## Step 3 — Save and link

Save to `output/research/[Niche] - Market Research - [MM.DD.YY].md`.

Also append a one-line summary entry to `tasks/findings.md`.

## Step 4 — Confirm with coach

Show the coach a 1-paragraph executive summary of what was found. Ask: "Anything you want me to dig deeper on?" — re-run targeted searches if so. Otherwise mark complete in offer-build spec.

## Step 5 — Exit check

Before exiting, run the `research-market` checklist in `references/skill-exit-checks.md`. For each item:

- **PASS** → continue
- **GAP** → surface to coach: *"[Item] is missing/weak. Want to fix it now, or defer with a note?"* If "defer", append to `tasks/findings.md` and footnote the artifact: `> ⚠️ Deferred from exit check: [item] — [reason]`
- **FAIL (hard)** → do not exit. Block until resolved.

The exit check is the preventive layer. The capstone PSS is the audit layer. Catching unsourced numbers here means the capstone audit doesn't trip a Price Defensibility FAIL.

## Operating rules

- **Cite everything.** Every dollar figure, every market size, every regulatory claim → URL.
- **Use 2026.** Hard-code current year in queries.
- **Don't guess.** If a search doesn't return clean data on a specific number, say so explicitly and recommend a follow-up.
- **Compare engines.** Where two sources conflict, surface the conflict — don't pick one silently.
- **Parallel-by-default.** Launch 4-6 web searches in a single message.
