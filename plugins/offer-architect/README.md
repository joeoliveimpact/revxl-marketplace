# offer-architect

Build market-validated, Hormozi-structured coaching offers — start to finish — using a guided pipeline of slash commands.

## What it does

Takes a coach from "I have an idea / current offer" to a final consolidated offer document with:
- Coach profile + brand voice
- Niche + market deep research (cited)
- Gap analysis with open questions
- Feasibility scorecard across competing positions
- Hormozi $100M Offers value stack (Value Equation + Trim & Stack + Bonuses + Guarantees + Naming)
- Three-structure pricing matrix (1mo / 3mo / 6mo / 12mo / VIP)
- Consolidated final offer doc + NotebookLM-ready bundle for a 3-minute roadmap video

## Install

Copy or symlink this folder into your plugins directory (or its parent), then in Claude Code:

```
/plugin install offer-architect
```

(or invoke skills directly by their slash command if the plugin is in the auto-discover path)

## Usage

```bash
/offer-architect:start            # orchestrator — run this first
```

The orchestrator routes you through:

1. `/offer-architect:intake-coach` — captures background, current offer, ICA, partners, voice, constraints
2. `/offer-architect:research-market` — web deep-research on niche + competitors + regulatory + pricing
3. `/offer-architect:find-gaps` — open questions + assumptions to validate
4. `/offer-architect:assess-feasibility` — weighted scorecard across alternative positionings
5. `/offer-architect:build-value-stack` — Hormozi framework applied
6. `/offer-architect:price-matrix` — 3 pricing structures with pros/cons
7. `/offer-architect:finalize-offer` ⭐ — consolidated final doc + NotebookLM bundle
8. `/offer-architect:build-offer-blueprint` ⭐⭐ — synthesis capstone: 3–5 page Offer Blueprint + Projected Success Score report (launch gate)
9. `/offer-architect:export-roadmap-video` — 3-min video output (NotebookLM)

### Capstone outputs (from `build-offer-blueprint`)

Two files per client per run:
- **`[Brand] Offer Blueprint - MM.DD.YY.md`** — 3–5 page foundational reference doc. Source of truth for marketing copy, website, landing page, funnel, content, program delivery. Hand to any downstream tool.
- **`[Brand] Projected Success Score - MM.DD.YY.md`** — plain-English launch-readiness score (0–100) with section breakdown, top 5 priority fixes, and launch verdict. Written at 7th-grade reading level for coaching-business newcomers.

The capstone enforces a **hard no-inventing-deliverables rule** — every item carries a provenance tag (`[confirmed]` / `[coach-to-build]` / `[suggested-optional]`) and the PSS counts each by tag (100% / 50% / 0%). This stops hallucinated stacks from inflating launch-readiness scores.

The capstone also runs the **`offer-market-auditor` agent** as a 4-check launch gate (Price Defensibility / Audience Pain / Claim Substantiation / Competitive Position). Audit findings deduct directly from PSS dimension scores — one unified score, no separate audit doc.

Each step can be re-run independently. State lives in `.claude/specs/in-progress/offer-build.md`.

## Output convention

The plugin writes to a `Clients/[Coach Name]/` folder in your workspace. Research goes to `output/research/`. NotebookLM bundles go to `Clients/[Coach Name]/[Brand] NotebookLM Bundle/`.

## Dependencies (optional but recommended)

- `brand-voice` plugin — for voice capture and enforcement
- `gws-docs` skill — for pulling existing Google Docs the coach has
- Web search capability (built into Claude Code)

## Origin

Built off the manual offer-building process Joe Olive ran for Coach Jared Tavasolian (Heal-Strong) in May 2026. The Jared run is preserved in `Clients/Jared Tavasolian/` as the canonical reference example.

## Reference materials in this plugin

Inside `references/` there are three layers of Hormozi framework material:

| Folder / file | What it is | When to use |
|---------------|-----------|-------------|
| `hormozi-100m-offers-summary.md` | One-page cheat sheet of the whole framework | Quick orientation; embed snippets in SKILL.md decisions |
| `kb/00-master-protocol.md` + `kb/01-06-*.md` | Executable knowledge base — 6 structured modules (Value Equation, Market Selection, Trim & Stack, Scarcity/Urgency/Bonuses, Guarantees, Naming) | Primary source the `build-value-stack` and `price-matrix` skills read from |
| `chapters/00-17-*.md` | Chapter-by-chapter summaries of the framework | Reference deep-dive when a specific chapter concept is needed |
| `extractions/*-instructions.md` + `*-rules.md` | Paired instruction + rules extracts per chapter | Programmatic reasoning over specific framework rules |
| `create_hormozi_offer-pattern.md` | Fabric-pattern format of the offer-build flow | Use if running via Fabric instead of Claude Code |
| `research-checklist.md` | Checklist `research-market` skill enforces | Source-of-truth for what every market-research pass must cover |
| `pss-rubric.md` | Projected Success Score scoring rubric — section→dimension weights, audit deductions, naming two-axis rubric | Source-of-truth for `build-offer-blueprint` scoring (audit layer) |
| `skill-exit-checks.md` | Per-skill exit checks — preventive scoring run by each upstream skill before completing | Source-of-truth for catching gaps at their source (preventive layer) |

The `kb/` folder is the **canonical executable reference** — skills should prefer it over the summary. The summary exists for quick context in SKILL.md preamble; the kb/ is for actual reasoning.

> **A note on source material.** The reference materials in this plugin are *summaries, structured extractions, and protocol-style reformulations* of Alex Hormozi's framework from *$100M Offers*. The plugin does **not** include the book's verbatim text. If you want the original quotes or full passages while running this plugin, you should own the book (paperback, ebook, audiobook, or Acquisition.com access) and refer to it directly. Buy the book — Hormozi gives away a tremendous amount of value at a low price point, and supporting the source material is the right call.

## Versioning

`0.1.0` — initial release. 9 skills + 7 templates + multi-layer reference KB. NotebookLM bundle export only (auto-video generation deferred to v0.2).

`0.2.0` — adds synthesis capstone: `build-offer-blueprint` skill + `offer-market-auditor` agent + 2 new templates (Offer Blueprint, PSS report) + `pss-rubric.md` + `templates/deep-research-prompts/` library. Hard rule on no-inventing-deliverables enforced via provenance tags and provenance-weighted PSS scoring.

`0.2.1` — adds preventive scoring layer: `skill-exit-checks.md` + exit-check step in all 7 upstream skills (intake-coach, research-market, find-gaps, assess-feasibility, build-value-stack, price-matrix, finalize-offer). Each skill runs its slice of the PSS rubric before completing — catching gaps at source instead of letting them leak to the capstone. The capstone PSS now reflects offer quality, not pipeline hygiene.

`0.2.2` — clarity + consistency polish. Exit-check steps in all 7 upstream skills now have explicit step numbers (was placeholder "Step N"). `start` skill updated to (a) include `build-offer-blueprint` in the pipeline routing — was missing — (b) set coach expectation that the pipeline may pause for quality gates or external deep-research prompts, and (c) flag the Offer Blueprint + PSS as the true DoD with NotebookLM bundle/video as optional follow-ons. Math bugs fixed in Jared's dry-run artifacts (bonus stack arithmetic, speed-to-launch projection). Band wording aligned across rubric, template, capstone skill, and gauge mockups — only 90+ now signals "launch now."
