# Changelog

## 0.1.0 — initial release
- Three entry doors: `lm-create` (from scratch), `lm-revamp` (improve your existing magnet), `lm-inspired-by` (reverse-engineer a competitor's without copying) + `lm-start-here` router.
- Shared 5-stage build pipeline (intake → structure → draft → QC rubric → deliver) with a 15-criteria quality rubric and PDF rendering + QC.
- Bundled knowledge layer: 6 reference docs (frameworks, format-by-niche matrix, conversion benchmarks, common mistakes, nurture handoff, hooks & titles) wired into the build stages.
- brand-brain bundled: voice-matched drafts via the shared `~/.claude/revxl/<brand>/voc/` brain (built once, reused across all REVXL engines).
- Honest capability detection: optional upgrades (search, transcription, social) report unavailable unless actually probed live — no silent fake enrichment; graceful degradation to WebSearch.
- Config + client profiles persist via `${CLAUDE_PLUGIN_DATA}` (survive plugin updates).
