---
name: meta-ads-superengine:meta-ads-start
description: Entry point for the Meta ads engine. Greets, detects first-run vs returning, shows the grouped skill map, surfaces the compass and any canon-staleness banner, and routes to the right door. Trigger phrases include "meta ads", "start meta ads", "meta ads engine", "run ads for my coaching business".
---

# meta-ads-start — the front door

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #1.

## Load (in order)
1. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/journey-map.md` — roster + edges (all routing below comes from it)
2. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/teach-mode.md` → read `~/.claude/revxl/teach-level` (fallback chain per that file; absent → `new`)
3. `~/.claude/meta-ads-superengine/.superengine` (marker) + `state/<active_brand>.json` — either absent → FIRST RUN
4. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/canon.md` — compute staleness

## Steps

**1. Staleness banner (before anything else).** If canon's verified-as-of
date is >90 days old, show the banner verbatim from canon.md. Otherwise
silent.

**2. Branch on run state.**

**FIRST RUN (no marker):** Warm two-sentence greeting: what this engine does
(zero → launched → scaling Meta ads, built for coaches) and that it teaches
as it goes. Then edge E1 — do NOT dump the full skill list on a first-run
coach. Render this block (adapt the "why" clauses to teach level):

**Next moves**
1. Take the tour — the whole road in 2 minutes, and why the order matters. Say: "ads tour"  ← start here *(default, unless your opener already signals live ads)*
2. Jump straight in — I learn your business once, ~10 minutes, only 3 answers required. Say: "set up my ads"  *(← start here when the opener signals existing ads: "I already run ads", your campaigns, spend talk ... I'll import what's running, nothing gets paused)*
3. Just exploring — ask me anything about Meta ads, plain-English answers.
4. You can never get lost — this always shows the road. Say: "what's next"

**RETURNING (marker + state):** One-line position ("<brand>: stage N,
last touched <date>"). Surface `open_loops` if any. Then edge E2 — render
the compass inline (delegate to the meta-ads-next procedure, which produces
the state-ranked **Next moves** block) rather than a static menu.

**3. Skill map on request.** If the coach asks "what can you do", show the
roster from journey-map grouped (Core / Strategy / Creative / Launch / Ops),
one line per GROUP at `new` teach level (one line per skill at
`learning`/`pro`). Always close with the compass pointer: *"Lost at any
point? Say **what's next**."*

## Teach mode
In `new`: plain-English-first — explain in plain words, then name the term
with a one-line gloss on first use (deep-tier entries from glossary.md
Section 3 for any term listed there, with worked numbers), and add a "what this
means for you" line where the consequence isn't obvious. In `learning`:
gloss Meta terms on first use (one-liner tier). In `pro`: terse operator
voice, no glosses.

## Rules
- This skill writes NO state (read-only door).
- All trigger phrases quoted to the coach come from the journey-map roster —
  never invent or paraphrase them.
- Refusal-free zone: whatever the coach asks for, route them (edge E0 lives
  in the target skill, not here).
