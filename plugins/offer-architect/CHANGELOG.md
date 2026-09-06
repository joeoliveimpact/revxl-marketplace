# Changelog — offer-architect

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-09-05

### Added
- `references/vault-api.md` ... the RevXL Brain wiring reference for this plugin: the
  `frameworks-reference-library` spoke, the copyright rule (structure and ideas only,
  never quoted, cited as the source of the idea and not the words), the invocation, the
  per-skill query recipes, the cache and budget rules, the evidence line and the
  degrade rules.
- Brain trigger at one named step in `build-value-stack`, `price-matrix`,
  `finalize-offer` and `build-offer-blueprint` (`Step 0b`, after the inputs are read
  and before the first draft). Each fires ONE `depth=med` invocation of
  `workspace-superengine:revxl-vault-search` with `plugin=offer-architect` and
  `spoke=frameworks-reference-library`, checks `brain-pulls/` first, and prints a
  `Brain: ...` evidence line at the skill's next checkpoint. `export-roadmap-video`
  gets no trigger: it repackages decisions already locked upstream.
- `intake-coach` Step 1b runs the Brain connection test (`test plugin=offer-architect`)
  and degrades in plain English when workspace-superengine is missing.
- README: optional-Brain-key line under dependencies and a Brain section.

### Changed
- `plugin.json` now carries the `$schema`, `homepage` and `license` (MIT, matching the
  shipped LICENSE) fields every other catalog plugin has, and the author email matches
  the rest of the catalog.
- Requires workspace-superengine 0.15.0 or later for live Brain pulls; without it the
  pipeline degrades to its bundled references and says so once. No curl, no key
  handling and no endpoint lives in this plugin.

## [0.2.2] — 2026-05-15

### Changed
- Exit-check steps in all 7 upstream skills now have explicit step numbers (was placeholder "Step N")
- `start` skill orchestrator updated: pipeline routing now includes `build-offer-blueprint` capstone (was missing), DoD corrected to Blueprint + PSS (not finalize/video), coach-facing expectation set that the pipeline may pause for quality checks or external deep-research prompts

### Fixed
- Bonus stack arithmetic bug in dry-run artifacts (provenance-weighted math)
- Speed-to-launch projection math in PSS report
- Old band-meaning copy lingering in gauge mockup
- Band wording aligned across rubric, template, capstone skill, and gauge mockups — only 90+ now signals "launch now"

## [0.2.1] — 2026-05-15

### Added
- `references/skill-exit-checks.md` — per-skill preventive scoring checklists
- Exit-check step in all 7 upstream skills (`intake-coach`, `research-market`, `find-gaps`, `assess-feasibility`, `build-value-stack`, `price-matrix`, `finalize-offer`). Each skill runs its slice of the PSS rubric before completing — catching gaps at source instead of letting them leak to the capstone.
- Two-layer scoring model documented in `pss-rubric.md`: preventive layer (exit-checks) + audit layer (capstone PSS).

### Changed
- Capstone PSS now reflects offer quality, not pipeline hygiene. Top-priority fixes surface as strategic work, not bookkeeping.

## [0.2.0] — 2026-05-15

### Added
- **Synthesis capstone:** `build-offer-blueprint` skill — takes every prior artifact, runs an intake gap-check + scored auto-fill, dispatches a market audit, and produces TWO outputs (Offer Blueprint + Projected Success Score report)
- **Market audit agent:** `offer-market-auditor` — 4-check launch gate (Price Defensibility, Audience Pain Validation, Claim Substantiation, Competitive Position) with PASS/FLAG/FAIL verdicts feeding PSS deductions
- **Templates:** `offer-blueprint-template.md` (3–5 page reference doc), `projected-success-score-template.md` (plain-English launch report), `intake-required-fields.md` (3-mode field schema: inferable / direct-ask / deep-research-prompt)
- **References:** `pss-rubric.md` (section→dimension weights, audit-to-PSS deduction map, naming two-axis rubric, 5-band scoring 0-20/20-50/50-70/70-90/90+)
- **Deep-research prompt library:** 5 pre-built copy-paste prompts (niche size, competitor pricing, regulatory, premium anchors, ICA validation) for external deep-research tools when WebSearch isn't deep enough
- **Naming system:** 4 frameworks supported (Hormozi MAGIC, Watkins SMILE & SCRATCH, Igor, Marty Neumeier Zag) with two-axis scoring (cold-traffic conversion potential vs brand-trust longevity)
- **Hard rule on no inventing deliverables:** provenance tagging (`[confirmed]` / `[coach-to-build]` / `[suggested-optional]`) enforced everywhere; PSS counts items weighted by tag (100% / 50% / 0%) so hallucinated stacks can't inflate launch-readiness scores

## [0.1.0] — 2026-05-14

### Added
- Initial release
- 9 skills: `start`, `intake-coach`, `research-market`, `find-gaps`, `assess-feasibility`, `build-value-stack`, `price-matrix`, `finalize-offer`, `export-roadmap-video`
- 7 templates: coach profile, market research, gaps, feasibility scorecard, value stack, pricing matrix, final offer + NotebookLM bundle scaffold
- Multi-layer Hormozi $100M Offers reference KB: master protocol + 6 modules (Value Equation, Market Selection, Trim & Stack, Scarcity/Urgency/Bonuses, Guarantees, Naming) + 17 chapter summaries + raw chunks + extractions
- NotebookLM bundle export for 3-minute roadmap video deliverable
