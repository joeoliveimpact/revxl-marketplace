---
name: meta-ads-superengine:meta-ads-compliance-check
description: The live policy gate before launch. Checks the offer against current Meta ad policy — Special Ad Categories (including Financial Products & Services), AI-content labeling, and claim rules — using a LIVE lookup every time, never cached knowledge. Also handles ad-rejection and account-restriction triage. Trigger phrases include "compliance check", "is my ad allowed", "my ad got rejected", "account restricted".
---

# meta-ads-compliance-check — the live policy gate

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #11.
**HARD LAUNCH GATE.** Every entry in this domain was a corpus failure — the
knowledge base missed an Oct-2024 policy change. **Compliance answers NEVER
come from cache, canon, the vault, or the Brain. Live check, every time.**

## Load
- shared refs (canon for FRAMING only, never as the answer)
- Active brand state → `setup.offer`, `offer_version`

## Prereq (E0)
`setup.offer`. Missing → setup.

## Steps

**1. Live policy lookup (mandatory).** Detect-first: when the Meta MCP is
connected, use `ads_get_help_article` (live Meta help/policy articles with
canonical URLs — cite them). Otherwise fall back to WebFetch/WebSearch on the
current Meta policy pages (Special Ad Categories, AI-content/labeling,
prohibited-content). Do NOT answer from memory or any bundled doc. If live
lookup is impossible right now, say so and return "unverified — cannot pass
the gate" (never a cached pass).

**2. Screen the offer** (per `offer_version`):
- **Special Ad Categories** incl. **Financial Products & Services** (5th
  category, Oct 2024 / enforced Jan 2025). Financial coaching that
  promotes/links financial products CAN trigger it; life/health/business
  coaching generally doesn't — **check per offer**, never assume "coaching
  never triggers."
- **AI-content labeling** — C2PA auto-labeling (from Jun 1 2026); no global
  mandatory instant-rejection regime (that's SEO fiction). If AI-avatar/
  synthetic creative is planned, note the auto-label + trust cost.
- **Claims** — health/income/outcome claims that need substantiation or a
  disclaimer.

While screening, capture every creative-level restriction the live sources
state for this offer's niche as plain-language constraint strings (e.g. "no
before/after transformations", "no scale/tape-measure/body-shame imagery"),
each with its source citation shown next to it in the conversation, not stored
in state.

**3. Verdict** → append `compliance[]`
`{offer_version, result: "pass"|"flagged"|"unverified", categories[], constraints[], checked_at}`.
State the LAUNCH consequence plainly: a flagged/failed offer keeps launch
blocked (F1); an unverified check is not a pass and keeps launch blocked (F11).
A pass that carries constraints is still a pass ... say so plainly ("you're
cleared to run, with these rules: ...").

## Rejection-triage sub-mode (entered via F8)
Ad rejected or account restricted: live-lookup the specific policy cited →
diagnose the likely cause → the appeal path → **don't-make-it-worse
warnings** (don't spam re-submits, don't edit-and-relaunch blindly). Route
back to the fix (offer framing / creative change) then re-run.

## Terminal paths — inline blocks (routing.md grammar)

**PASS (E9):** preamble: "Compliance pass recorded for your current offer —
launch gate is green on this item." Then pick #1 by state:

**Next moves**
1. *If no creatives yet:* build the creative plan — what your 3–5 genuinely different ads will be. Say: "creative strategy"  ← start here
   *If creatives exist, no plan, and `stage` is set:* build the campaign structure. Say: "plan my campaign" *(no `stage` yet → "what stage am I in" first)*
   *If a plan exists and the launch gate is green (`funnel.qualified_event` set):* launch it. Say: "launch my campaign" *(event missing → "qualify my leads" first)*
2. Check where you are on the whole road. Say: "what's next"

**Next moves — flagged/failed (F1)**
The specific fix comes first (offer reframe / creative change / category
setting), stated plainly. Launch stays BLOCKED until a pass matches the
current offer.
1. Apply the fix, then re-run the gate. Say: "compliance check"
2. *If the fix means changing the offer itself:* update it first (this resets the math + compliance for the new version). Say: "resume setup"

**Next moves — unverified (live check unavailable, F11)**
The gate could not run — no live policy source reachable. Nothing is recorded
as a pass; LAUNCH stays blocked until a real check passes.
1. Re-run once you're back online. Say: "compliance check"
2. Keep building in parallel — the gate blocks launch, not the rest of the work. Say: "creative strategy"
3. Check where you are on the whole road. Say: "what's next"

**Rejection-triage exit (F8):** after diagnosis + appeal path, re-render the
F1 block (fix → re-run).

## Teach mode
In `new`: plain-English-first — "Special Ad Categories" explained as "Meta's
restricted classes; some coaching offers count as financial products" BEFORE
the term, with the per-offer consequence line; the launch-gate consequence
always stated. When constraints are recorded, add the consequence line: "what
this means for you: these are the creative rules your ads must follow, and I'll
enforce them when we build." In `learning`: gloss SAC/C2PA first use. In `pro`: verdict +
categories + gate consequence, terse. **Gates and warnings render at FULL
strength at every level** (teach-mode.md exception).

## Guardrails
- **Brain: NONE.** This skill is hard-excluded from vault/Brain retrieval —
  the vault contains graded compliance notes and surfacing one as the answer
  is exactly the failure mode (canon rule 2). Emit `Brain: skipped
  (compliance = live check only)`.
- A pass is stamped to `offer_version` — a later offer/price change
  invalidates it (the compass flags the stale gate).
