# Changelog

## 0.2.0 - 2026-09-05

### Added
- **The RevXL Brain, at one named step in each build door.** `lm-create` (Phase 1.5), `lm-inspired-by` (Step 5.5) and `lm-revamp` (Step 2.5) each check the vault once, after the brief is locked and before the first draft line: `depth=med` on the `frameworks-reference-library` spoke for lead-magnet structure and step sequence, then `depth=low` on `content-strategy` for current hooks, titles and CTA language. That is 2 searches and 2 note reads per step, inside the plugin's cap of 2 searches + 3 note reads.
- **New wiring reference `references/vault-api.md`:** the two spokes, six query recipes (one per generator per spoke), the `brain-pulls/` cache rule, the budget arithmetic, the evidence line and the degrade rule. It carries the frameworks library's copyright rule verbatim ... structure, frameworks and ideas only, never its words, cited as the source of the idea rather than the words.
- **Evidence line on every build:** `Brain: [brain] <path> woven` or `Brain: skipped (no key / cached / degraded / budget)`, so a coach can always tell whether a pull happened.
- `lm-setup` documents the Brain as an optional connection rather than a profile upgrade, and runs the connection test by invoking `workspace-superengine:revxl-vault-search` with args `test plugin=lead-magnet-superengine`.
- README: the optional-Brain requirements line and a short Brain section.

### Changed
- Requires workspace-superengine 0.15.0 or later for live Brain pulls. Without it, or without a key, the three doors run on the bundled reference docs and say so once. No key ladder, no curl and no endpoint anywhere in this plugin ... the connection lives in one place for every RevXL plugin.

## 0.1.1 — 2026-08-17
- Transcription now documents passing a **vocabulary prompt** built from the brand's canonical names (brand-brain `voc/business-config.md` + the `## Vocabulary` block in `voc/voice-guide.md`). Without one, Whisper silently substitutes the nearest common-English phrase for product names it has never seen.
- Guidance added at every point the research chain reaches for transcription: `lm-setup`, `lm-research`, `core/source-chains.md`.
- Two caveats documented alongside the recommendation, because both fail silently: a bare comma list strips capitalization and punctuation from the whole transcript, and a prompt can drop a speaker's retakes — compare output length on multi-take source.
- Prefer Groq `whisper-large-v3-turbo` over full `large-v3`: no worse on proper nouns, ~3x cheaper, and it kept speech that full v3 dropped.
- (09.04.26) `plugin.json` bumped to 0.1.1 to match this entry and the catalogue; it had stayed at 0.1.0, so this release never reached installed clients until now.


## 0.1.0 — initial release
- Three entry doors: `lm-create` (from scratch), `lm-revamp` (improve your existing magnet), `lm-inspired-by` (reverse-engineer a competitor's without copying) + `lm-start-here` router.
- Shared 5-stage build pipeline (intake → structure → draft → QC rubric → deliver) with a 15-criteria quality rubric and PDF rendering + QC.
- Bundled knowledge layer: 6 reference docs (frameworks, format-by-niche matrix, conversion benchmarks, common mistakes, nurture handoff, hooks & titles) wired into the build stages.
- brand-brain bundled: voice-matched drafts via the shared `~/.claude/revxl/<brand>/voc/` brain (built once, reused across all REVXL engines).
- Honest capability detection: optional upgrades (search, transcription, social) report unavailable unless actually probed live — no silent fake enrichment; graceful degradation to WebSearch.
- Config + client profiles persist via `${CLAUDE_PLUGIN_DATA}` (survive plugin updates).
