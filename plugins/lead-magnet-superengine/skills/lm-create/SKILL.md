---
name: lm-create
description: >
  Guided Q&A intake for building a lead magnet from scratch.
  Triggers on: "create a lead magnet", "make me an opt-in", "/lm-create",
  "build a lead magnet", "I need a lead magnet", "create an opt-in".
---

# /lm-create — Guided Lead Magnet Creation

**Origin:** Pure guided Q&A (nothing pre-exists — no URL, no old PDF).  
**Output:** Seeds `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` with your answers, then runs the shared
Blueprint → Draft → Design → Score → Output pipeline.

---

## How to Use

Type `/lm-create` (or say "create a lead magnet") and Claude will ask you five
questions, one at a time. Answer in plain English — no marketing jargon needed.
When all five answers are in, Claude builds the magnet automatically.

Data upgrades (SearXNG, Firecrawl, etc.) enrich each answer
automatically when they're connected. If none are connected, the skill works
entirely from your answers — no upgrade is required. Framework guidance is
always available from the bundled references (no upgrade needed).

---

## Workflow

### Phase 0 — Capability Check (silent, runs before Q&A)

Before asking questions, run:

```python
from lib.profile import load_profile, resolve
from lib.capability_detect import detect

import os
DATA = os.environ["CLAUDE_PLUGIN_DATA"]
# Active client profile persists outside the package. If missing, /lm-setup
# seeds it from ${CLAUDE_PLUGIN_ROOT}/profiles/client.blank.json (template).
profile = load_profile(os.path.join(DATA, "profiles", "client.json"))
caps = detect(profile, probes={
    "search":    lambda: searxng_health_check(),
    "ranked":    lambda: tavily_health_check(),
    "scrape":    lambda: firecrawl_health_check(),
    "social":    lambda: metricool_health_check(),
})
# caps is a dict[str, bool] — e.g. {"search": True, "ranked": False, ...}
```

Store `caps` in working context. Each Q&A step below checks `caps` to decide
whether to offer data enrichment or just ask.

---

### Phase 1 — Guided Q&A (five questions)

Ask questions one at a time. Wait for the user's answer before continuing.
After each answer, check the relevant source chain and offer enrichment if the
capability is live. Plain-English tone throughout — no jargon, no pressure.

---

#### Q1 — Niche

**Ask:**
> "What niche or industry is this magnet for? A sentence is fine —
> for example: 'online fitness coaches', 'real estate investors', 'bookkeepers
> serving small businesses'."

**Source-chain check (after user answers):**

Maps to **Competitor discovery** row in `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md`.

- If `caps["search"]` is `True`:  
  Offer: "I can search for competitors in that niche automatically to sharpen
  your positioning. Want me to run that now?"  
  If yes → call `lib.sources.search(query=<niche> + " lead magnet opt-in", chain=["searxng", "tavily", "websearch"])`.  
  Seed result into blueprint as `competitor_context`.

- If `caps["search"]` is `False`:  
  Ask: "Name 2–3 competitors and what you've seen them offer." (verbatim from
  source-chains.md fallback).

Store answer as `seed.niche`.

---

#### Q2 — Core Offer

**Ask:**
> "What's the paid thing you're ultimately selling? This could be a coaching
> programme, a course, a done-for-you service — whatever someone would pay you
> for. Don't worry about the magnet yet; just describe what you sell."

**Framework check (after user answers):**

Load `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md` (bundled —
always available, no upgrade required) and match the user's offer to the
relevant magnet type (consumable / tool / lead-qualifying bridge). Use
`${CLAUDE_PLUGIN_ROOT}/references/format-by-niche-matrix.md` to shortlist
formats that fit the niche from Q1.

Store answer as `seed.core_offer`.

---

#### Q3 — Audience Pain

**Ask:**
> "What's the #1 frustration or fear your audience has RIGHT NOW — before they
> find you? What keeps them up at night, or what have they already tried and
> failed at?"

**Source-chain check (after user answers):**

Maps to **Competitor social — what's working** row in `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md`.

- If `caps["social"]` is `True`:  
  Offer: "I can pull competitor social posts to surface the language your
  audience actually uses when describing this pain. Want me to check?"  
  If yes → call SocialCrawl skill (or Metricool MCP if `ranked` is also live)
  with `<niche> + pain language / complaints` query.  
  Surface top 3–5 verbatim phrases and inject into `seed.pain_language` for
  use in Draft stage (B4 — Avoid AI Dust Bunnies).

- If `caps["social"]` is `False`:  
  Ask: "Which of your competitors are most active on social, and what kinds of
  posts seem to perform best for them?" (verbatim source-chain fallback).  
  Or skip if user can't answer — pain description from Q3 is sufficient.

Store answer as `seed.audience_pain`.

---

#### Q4 — The ONE Narrow Problem

**Ask:**
> "If you had to pick ONE specific problem your magnet solves — not a list,
> not a theme — what is it? It should be something a person could describe in
> one sentence and feel immediately."
>
> *Tip: this is different from Q3. Q3 is the big fear; Q4 is the specific,
> narrow problem the magnet will actually fix.*

**No automatic enrichment for this question.** The narrow problem must come
from the human — it's a creative/strategic decision, not a data lookup.

After the user answers, reflect it back in one sentence and confirm:
> "So the magnet solves: [restate]. Is that right, or would you adjust it?"

Store confirmed answer as `seed.narrow_problem`.

---

#### Q5 — The Next-Problem → Offer Link (Hormozi Step 1)

**Ask:**
> "After someone gets the result from your magnet, what's the NEW problem that
> shows up — the one your paid offer solves? In other words: what does the
> magnet deliver, and what gap does that leave that makes working with you the
> obvious next step?"
>
> *Example: "The magnet teaches them to write better emails. The new problem is
> they now know what to say but don't have the time or system to send at
> scale — that's where my done-for-you service comes in."*

**Framework check (after user answers):**

Silently validate the next-problem → offer logic against the Hormozi Step 1
framing in `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md`
(bundled — always available). If the link is weak, surface a one-line
coaching note:
> "One thought: [specific Hormozi Step 1 framing that tightens the bridge]."

Let the user decide whether to adjust.

Store answer as `seed.next_problem_bridge`.

---

### Phase 1.5 ... Brain pull (brief locked, before the blueprint) via `revxl-vault-search`

Wiring per `${CLAUDE_PLUGIN_ROOT}/references/vault-api.md` (the `revxl-vault-search`
skill in workspace-superengine finds the key; this skill never runs a key ladder). All
five answers are confirmed and nothing has been drafted yet, so this is the named step.

**Check `brain-pulls/` in the working folder first** ... a cached pull for this niche and
narrow problem on the same spoke means no invocation for that spoke; reuse it and print
`Brain: skipped (cached)`.

No cache: two invocations, in this order.

1. Invoke `workspace-superengine:revxl-vault-search` with the Skill tool, args
   `depth=med plugin=lead-magnet-superengine spoke=frameworks-reference-library question: lead magnet structure for <niche> coaches ... angles: magnet types consumable tool and lead-qualifying; the step sequence of a great lead magnet; narrow problem to next problem bridge`.
2. Invoke `workspace-superengine:revxl-vault-search` with the Skill tool, args
   `depth=low plugin=lead-magnet-superengine spoke=content-strategy question: lead magnet hooks and titles for <niche> ... angles: opt-in headline patterns; CTA language; what is converting now`.

That is 2 searches and 2 note reads for the whole step: `depth=med` is 1 search plus up
to 2 reads, `depth=low` is 1 search plus 0 reads. The cap is 2 searches + 3 note reads
per named step, so this fits with a read to spare. Do not raise the second invocation to
`med` ... that would spend 4 reads and breach the cap. Read the echoed `spoke` back on
each invocation; anything other than the one asked for is degraded.

Weave what comes back into the seed as extra evidence, every borrowed idea cited
`[brain] <path>`: structure and step sequence from `frameworks-reference-library`, hook,
title and CTA language from `content-strategy`. The frameworks library is a third-party
reference library ... take its structure and ideas, never its words (the rule is in the
wiring reference). Save both pulls to `brain-pulls/<slug>.md`, slug carrying the spoke.

At the Phase 2 confirmation checkpoint print exactly one line:
`Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`.
No key, the skill missing, or any failure: degrade per the wiring reference and move on
... the Brain never blocks a build.

---

### Phase 2 — Seed and Hand Off to Build Core

Once all five answers are confirmed, assemble the seed object:

```python
seed = {
    "origin": "lm-create",
    "niche": seed.niche,
    "core_offer": seed.core_offer,
    "audience_pain": seed.audience_pain,
    "narrow_problem": seed.narrow_problem,
    "next_problem_bridge": seed.next_problem_bridge,
    "competitor_context": competitor_context,   # may be empty dict
    "pain_language": pain_language,             # may be empty list
    "caps": caps,
}
```

Show the user a one-paragraph summary of what was captured and ask:
> "Here's what I have. Ready to build? I'll go through blueprint, draft,
> design, and scoring — and show you the final magnet."

On confirmation, hand off to `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` — run all five stages:
**Stage 1 Blueprint → Stage 2 Draft → Stage 3 Design → Stage 4 Score → Stage 5 Output.**

---

### Phase 3 — Rubric Self-Check (Stage 4 of Build Core)

Before any output is shown, run `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` self-check in full:

- Score all 15 criteria: A1–A4, B1–B6, C1–C5.
- Section C IS included (self-check mode — see rubric Mode note).
- Any FAIL → return to Stage 2 (copy) or Stage 3 (design) to fix before output.
- Any FLAG → note in the JSON sidecar; surface to user in the "what/why" doc.
- Gate: 0 FAIL and 0–2 FLAG = READY. Otherwise revise and re-score.

Do not skip or abbreviate the rubric. No output ships without a passing gate.

---

### Phase 4 — Output (Stage 5 of Build Core)

Deliver three artifacts as specified in `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` Stage 5:

| Artifact | Description |
|---|---|
| **PDF** | Rendered via `lib.render_pdf.html_to_pdf()` using `${CLAUDE_PLUGIN_ROOT}/templates/field-guide.html.j2` and the `sections` schema. |
| **"What/Why" doc** | Plain-English explanation of magnet type, hook, win, and strategy decisions. Includes any rubric FLAGs and their fix notes. |
| **JSON sidecar** | `magnet-meta.json` with keys: `type`, `hook`, `win`, `sources_used`, `rubric_score`, `rubric_flags`. |

---

## Source-Chain Reference Map

| Q&A Field | Source-chain row (${CLAUDE_PLUGIN_ROOT}/core/source-chains.md) | Profile key |
|---|---|---|
| Q1 Niche | Competitor discovery | `search` (SearXNG → Tavily → WebSearch) |
| Q2 Core Offer | Bundled framework references (no chain) | — (`${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md` + `format-by-niche-matrix.md`) |
| Q3 Audience Pain | Competitor social — what's working | `social` (Metricool → SocialCrawl → WebSearch) |
| Q4 Narrow Problem | No chain — human decision only | — |
| Q5 Next-Problem Bridge | Bundled framework references (no chain) | — (`${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md` Step 1 validation) |

---

## Data-Optional Design

This skill works at zero-upgrade baseline. If every `caps` value is `False`:
- Q1: user names competitors manually.
- Q2: bundled framework references still apply (they ship with the plugin).
- Q3: user describes audience pain verbatim; social language is skipped.
- Q4: no chain regardless.
- Q5: bundled Hormozi Step 1 validation still applies.

Full data upgrades improve depth and specificity; they do not change the
workflow structure or output format.

---

## Quick Reference — Key Paths

| Path | Role |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` | Five-stage shared pipeline (Blueprint → Output) |
| `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` | 15-criterion self-check rubric |
| `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md` | Source chain rows + fallback questions |
| `${CLAUDE_PLUGIN_ROOT}/lib/profile.py` | `load_profile()` / `resolve()` |
| `${CLAUDE_PLUGIN_ROOT}/lib/capability_detect.py` | `detect(profile, probes)` — live capability check |
| `${CLAUDE_PLUGIN_ROOT}/lib/sources.py` | `search(query, chain)` — chain-walking sourcer |
| `${CLAUDE_PLUGIN_ROOT}/lib/render_pdf.py` | `html_to_pdf(html, out_path)` |
| `${CLAUDE_PLUGIN_ROOT}/lib/qc_pdf.py` | `check(pdf_path)` — post-render validation |
| `${CLAUDE_PLUGIN_ROOT}/templates/field-guide.html.j2` | Jinja2 PDF template |
| `${CLAUDE_PLUGIN_ROOT}/profiles/client.blank.json` | Shipped template; active profile lives at `${CLAUDE_PLUGIN_DATA}/profiles/<name>.json` |
