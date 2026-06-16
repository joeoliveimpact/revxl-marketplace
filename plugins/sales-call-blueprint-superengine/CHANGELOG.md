# Changelog — sales-call-blueprint-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-06-15

### Added
- Initial release.
- **5 skills:** `start` (orchestrator/router), `setup` (first-run config wizard — auto-discovers brand/program/closer data, sets transcript source + output destination, scoped dependency check), `guide` (plain-English first-time tour for non-technical users), `triage-blueprint` (15-min qualification call blueprint), `strategy-blueprint` (full RFPDP closing-call blueprint).
- **1 agent:** `sales-blueprint-builder` — builds blueprints for one prospect or a batch in its own context (autonomous or dispatcher-bookended), draft-first.
- **Two output modes:** deep Pre-Call Prep doc + scannable Call-Time Blueprint card (one or both).
- **Source-agnostic transcript pull** (`transcript-pull`): Fathom / Fireflies / Granola / GHL / Otter / manual paste / local-audio — manual paste is the universal fallback, never blocks.
- **Pluggable delivery** (`deliver-blueprint`): Google Drive (dated folders) / local / GHL note / chat / custom.
- **Frameworks as references:** RFPDP method, psychological-profile extraction, high-impact questions, objection handling.
- **Quality gate:** `blueprint-quality.md` checklist run before every delivery.
- **Config-driven:** one `references/business-config.md` holds all `{{VARIABLE}}` values; ships with placeholders so each installer runs `setup` fresh.
- **Pricing is never stored** — supplied live at the price drop; the skill structures how to drop the number, not the number itself.
- **Explainer mode** (on by default): plain-English narration + "what this means for you" lines, toggleable with "explainer off".
