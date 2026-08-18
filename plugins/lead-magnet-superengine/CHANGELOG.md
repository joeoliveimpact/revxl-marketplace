# Changelog

## 0.1.1 — 2026-08-17
- Transcription now documents passing a **vocabulary prompt** built from the brand's canonical names (brand-brain `voc/business-config.md` + the `## Vocabulary` block in `voc/voice-guide.md`). Without one, Whisper silently substitutes the nearest common-English phrase for product names it has never seen.
- Guidance added at every point the research chain reaches for transcription: `lm-setup`, `lm-research`, `core/source-chains.md`.
- Two caveats documented alongside the recommendation, because both fail silently: a bare comma list strips capitalization and punctuation from the whole transcript, and a prompt can drop a speaker's retakes — compare output length on multi-take source.
- Prefer Groq `whisper-large-v3-turbo` over full `large-v3`: no worse on proper nouns, ~3x cheaper, and it kept speech that full v3 dropped.


## 0.1.0 — initial release
- Three entry doors: `lm-create` (from scratch), `lm-revamp` (improve your existing magnet), `lm-inspired-by` (reverse-engineer a competitor's without copying) + `lm-start-here` router.
- Shared 5-stage build pipeline (intake → structure → draft → QC rubric → deliver) with a 15-criteria quality rubric and PDF rendering + QC.
- Bundled knowledge layer: 6 reference docs (frameworks, format-by-niche matrix, conversion benchmarks, common mistakes, nurture handoff, hooks & titles) wired into the build stages.
- brand-brain bundled: voice-matched drafts via the shared `~/.claude/revxl/<brand>/voc/` brain (built once, reused across all REVXL engines).
- Honest capability detection: optional upgrades (search, transcription, social) report unavailable unless actually probed live — no silent fake enrichment; graceful degradation to WebSearch.
- Config + client profiles persist via `${CLAUDE_PLUGIN_DATA}` (survive plugin updates).
