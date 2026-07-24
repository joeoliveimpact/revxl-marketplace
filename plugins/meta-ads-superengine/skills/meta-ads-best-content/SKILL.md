---
name: meta-ads-superengine:meta-ads-best-content
description: Mines the coach's OWN winners — past ad records and organic content — into a ranked replicate-into-paid list, reusing the shortform engine's analysis data before any paid crawl. Your best organic reel plus a 5-second CTA is a free ad. Trigger phrases include "mine my winners", "my best content", "what already works", "turn my reels into ads".
---

# meta-ads-best-content — your own winners

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #20.
The highest-signal creative input is what ALREADY worked for this coach —
free, voice-perfect, and proven on their actual audience.

## Load
- shared refs
- Active brand state → `setup` (profiles, history), `state/<brand>/history/`
- **Reuse-first:** shortform-superengine's `analysis-data.json` when that
  plugin's marker exists (its competitor/own-reel analysis already ranked
  the coach's content — never re-crawl what a sibling already pulled)
- SocialCrawl key (optional, ✋-gated) for what's missing

## Prereq (E0)
`setup` done (needs profiles or history imports). Missing → setup.

## Steps

**1. Inventory the sources:** imported Ads-Manager records
(`history/` — past winners ranked by cost/result), or paste your past-ad
numbers right here (name, spend, results, cost per result ... I'll file them
into `history/` for you), shortform analysis data
(detect-first), organic profiles (✋ crawl only for gaps, cost named,
approval first).

**2. Rank into the replicate-list:** what won, WHY it likely won (hook,
angle, format — storytelling metrics as evidence), and the paid-translation
for each: founder-face reel → +5–10s CTA → run via **Post ID** (organic
proof compounds); past winning ad → iterate dimensionally, never re-run
stale creative as-is.

**3. Map to the PDA matrix** (when it exists): each winner validates a cell
— flag matrix cells with NO proven winner as the real test candidates.

**4. Write** the replicate-list artifact; open_loop "feed winners to
creative-strategy".

## Terminal paths — inline blocks (routing.md grammar)

**Replicate-list delivered (E19):** preamble = the ranked list, then:

**Next moves**
1. *If `targets` are set:* fold the winners into your creative plan — proven angles get priority slots. Say: "creative strategy"  ← start here
2. *If `targets` aren't set yet:* run your numbers first — the creative plan reads them. Say: "run my numbers"
3. *If a winner is launch-ready (an organic reel needing only a CTA):* note it for the campaign plan — it runs via its Post ID. Say: "plan my campaign" *(when the mix is complete)*
4. See how your winners compare to the field. Say: "competitor ads" *(if your creative strategy exists)*

**Next moves — nothing to mine (no history, no organic presence)**
Not a dead end — it just means concepts start from the matrix:
1. Build concepts from the avatar matrix directly. Say: "creative strategy"
2. Start the organic flywheel so future rounds have winners to mine *(if the shortform engine is installed:* Say: "write a reel script from my analysis"*)*

## Teach mode
In `new`: plain-English-first — Post-ID deep-glossed ("running the SAME
post as an ad keeps its likes and comments — social proof compounds instead
of resetting"); "what this means for you: your phone-shot reel that got 40
comments is a better ad than anything a studio makes you." In `learning`:
gloss Post-ID first use. In `pro`: ranked list + translations, terse.

## Guardrails
- Reuse-first is a hard rule: shortform data before ANY crawl; ✋ + named
  cost before any credit spend; declined → Ad-free path continues.
- Winners are ranked on primary metrics where records allow; organic
  engagement is a proxy, labeled as such.
