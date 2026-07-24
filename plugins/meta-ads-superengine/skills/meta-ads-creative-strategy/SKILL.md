---
name: meta-ads-superengine:meta-ads-creative-strategy
description: The creative hub. Builds the PDA matrix (Persona × Desire × Awareness) and turns it into 3-5 genuinely distinct ad concepts at Stage 1 (more at scale), sets the format mix, and routes each concept to its production skill. Reads the coach's brand voice and consumes competitor and own-content intel. Trigger phrases include "creative strategy", "plan my creatives", "what ads should I make", "ad concepts".
---

# meta-ads-creative-strategy — THE HUB

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #13.
The journey orbits this skill: foundations feed it, production executes its
plan, RUN loops back to it. **Creative IS the targeting** — the ad itself
decides who sees it, so concept design is the highest-leverage step in the
whole engine.

## Load
- shared refs (`state-schema.md`, `journey-map.md`, `routing.md`,
  `teach-mode.md`, `glossary.md`, `canon.md`, `naming.md`, `vault-api.md`)
- Active brand state → `targets`, `stage`, `creatives`, `setup.offer`
- Active brand state → `compliance[]` (entry matching current `offer_version`) → constraints
- **Voice (required read):** `~/.claude/revxl/<brand>/voc/` (voc-profile =
  avatar pains in the avatar's words; voice-guide = register)
- Intel when present: competitor-intel / best-content artifacts (open_loops
  point at them)

## Prereq (E0)
`targets` set. Missing → breakeven-math ("we don't design ads before we know
what a lead is allowed to cost").

## Steps

**1. Voice + avatar check (F10 if cold).** voc/ present → the avatar's OWN
words seed the matrix. voc/ absent but `voice_sketch` present → reuse it
(voice confidence: low, no re-interview). Neither → offer capture (brand-brain
if installed, else inline mini-interview; **write `voice_sketch` on capture**),
proceed labeled "voice confidence: low".

**2. Build the PDA matrix.** Persona × Desire × Awareness:
- **Personas:** 2–3 real client archetypes (circumstance-based beats
  demographic: "the executive who tried six diets and still hits 3 PM
  brain-fog" — precise WITHOUT shrinking the audience).
- **Desires:** outcome + status framing (how they want to be SEEN).
- **Awareness:** unaware / problem-aware / solution-aware / product-aware /
  most-aware — decides what each ad must say first (the awareness ladder).

**3. Cut concepts from the matrix.** Stage-appropriate count (S1 3–5, S2
8–12, S3 12–20, S4 15–25+). **Stage unset (`stage: null`):** say so plainly,
offer stage-check as move #1, and proceed at the S1 count labeled "stage unset
... assumed test stage." Each concept distinct on at least one axis —
different pain, avatar, format, or awareness level. **Never hook-swaps of
one idea** — near-duplicates get bundled and compete as ONE ad (the lottery
tickets rule). Give each concept:
- id `cN` (naming grammar — the registry join key)
- one-line brief: persona + pain + awareness + message frame
- **format assignment** (the dimensional mix): static / video (talking-head
  or UGC) / VSL — per stage mix and the emotional-vs-logical driver read
  (raw storytelling for life/mindset; mechanism/clinical for skeptical
  exec/health buyers).

Active constraints (from `compliance[]` for the current `offer_version`) are
stated up front and respected: a concept whose format or driver would violate
one (e.g. a before/after static under a "no before/after" constraint) is not
offered, with the constraint named.

**4. Weave intel (when present).** Competitor angles feed the matrix as
ANGLE candidates (never structure clones); own-winners get "replicate into
paid" priority slots (founder-face default — it outperforms polish).

**5. Brain (heaviest consumer — 2 searches).** Recipe rows: awareness +
format ("problem aware hook coaching", "static long copy cold traffic"
keyed to the concepts just cut). Weave returned patterns; cite
`[brain] <path>`; self-evidencing line; degrade F9.

**6. Write** concept rows into `creatives[]` (status draft) + route each to
its production skill.

## Terminal paths — inline blocks (routing.md grammar)

**Concepts locked (E10):** preamble lists the concepts (id + one-liner +
format), then:

**Next moves**
1. Produce the first concept — <its format> for c1. Say: "<write hooks / write my ad copy / make static ads / write my video script — per c1's format>"  ← start here
2. Work through the rest — I'll route each concept to its format's skill in order.
3. *If no intel has fed the matrix yet:* mine your own winners first — free, and it's the highest-signal input. Say: "mine my winners"
4. *If own PDA now exists and the coach wants the field view:* see what's working in your niche. Say: "competitor ads"

**Next moves — voice cold (F10)**
1. Build your brand brain — every asset after this sounds like YOU. Say: "build my brand brain" *(if installed; else the inline interview)*
2. Proceed on low-confidence voice — honest label, upgrade later.

## Teach mode
In `new`: plain-English-first — the lottery-ticket analogy for distinct
concepts and the shop-window analogy for creative-is-targeting (glossary
deep tier) BEFORE PDA/awareness jargon; each matrix axis explained with the
coach's own avatar as the example; "what this means for you: five genuinely
different ideas beat fifty tweaks." In `learning`: gloss PDA/awareness first
use. In `pro`: matrix → concept table → routing, terse.

## Guardrails
- Canon: concept counts are DIRECTIONAL — direction firm, numbers soft.
- Never state "Entity ID" as a Meta mechanism — say "near-duplicates get
  bundled and compete as one ad."
- No unattributed stats in concept briefs.
