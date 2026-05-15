# Deep Research Prompts

Pre-built copy-paste prompts the `build-offer-blueprint` skill (and `offer-market-auditor` agent) emit when a research category is thin or missing.

These are run **externally** by the coach — in ChatGPT Deep Research, Claude Deep Research, or Perplexity Pro. Cowork/Code WebSearch isn't deep enough for primary market research.

## How to use (from inside a skill)

When a category in `references/research-checklist.md` is missing or shallow:

1. Load the matching prompt file
2. Substitute `{{niche}}`, `{{ICA}}`, `{{competitor_names}}`, `{{geo}}`, `{{year}}` from the client folder
3. Hand the rendered prompt to the coach with: "Paste this into ChatGPT Deep Research (or Claude Deep Research). When you get the result, paste it back here."
4. Ingest the returned doc, append to `output/research/[Niche] - Deep Research Supplement - MM.DD.YY.md`, continue

## Available prompts

| File | Covers checklist section |
|------|--------------------------|
| `01-niche-market-size.md` | §2 Market size & trajectory |
| `02-competitor-pricing.md` | §3 Pricing benchmarks + §4 Named competitors |
| `03-regulatory-landscape.md` | §5 Regulatory landscape |
| `04-premium-anchors.md` | §6 Premium / concierge anchors |
| `05-ica-validation.md` | §8 ICA validation evidence |

Add more as new gap categories appear.
