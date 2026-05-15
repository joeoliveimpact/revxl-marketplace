# Changelog — offer-architect

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
