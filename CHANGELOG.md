# Changelog — revxl-marketplace

Marketplace-level changelog. For plugin-specific changes, see each plugin's own CHANGELOG.md.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.9] — 2026-06-02

### Changed
- Plugin: [course-crawler](plugins/course-crawler/CHANGELOG.md) v0.5.0 — Skool-native (signed Mux) video support: `discover_skool.py` detects `videoId`/signed-token lessons and adds a `--mux-page` extractor; `process_videos.py` now sends the required `Referer` for signed Mux playback (previously 403'd). Surfaced archiving a Skool classroom whose videos are Mux-hosted rather than YouTube/Loom.

## [0.1.8] — 2026-05-20

### Changed
- Plugin: [course-crawler](plugins/course-crawler/CHANGELOG.md) v0.4.0 — OCR-gated slide extraction (new feature); promo-video filter, GPU-Whisper crash containment, and Windows long-path (`\\?\`) support (fixes). All developed in-cache during plugin testing across the two prior sessions; now upstreamed.

## [0.1.7] — 2026-05-19

### Removed
- **revxl-os-superengine delisted from the catalog** — not release-ready. Plugin code is retained in `plugins/revxl-os-superengine/` and is unaffected; only the marketplace entry was removed. Mirrors the built-but-unpublished pattern used for `revxl-webhook-channel` (commit `d833b46`). The catalog now ships 5 plugins.

## [0.1.6] — 2026-05-17

### Changed
- **CI/local validator drift fixed.** Extracted CI's three inline check groups into one committed `scripts/validate.py`; the workflow now calls that script (`python scripts/validate.py --section ...`) instead of inline heredocs. Contributors run the identical command locally before pushing, so a green local run == green CI. Closes the gap where the SKILL.md YAML-frontmatter check only ran in CI (the bug that slipped `course-crawler` 0.3.0 → CI red). `CONTRIBUTING.md` updated to point at the script.

## [0.1.5] — 2026-05-17

### Fixed
- Plugin: [course-crawler](plugins/course-crawler/CHANGELOG.md) v0.3.2 — fixed unquoted-colon YAML frontmatter in `skills/course/SKILL.md` that was failing marketplace CI (pre-existing since 0.3.0). All 5 course-crawler skill frontmatters now parse.

## [0.1.4] — 2026-05-17

### Changed
- Plugin: [course-crawler](plugins/course-crawler/CHANGELOG.md) v0.3.1 — lesson-centric output tree (`<course>/NN-module/NN-lesson/` with `<lesson>.md` text+links, `transcript.md`, `slides/`, `downloads/`); replaces the scattered type-first layout. Shared `lesson_order` so scrape + transcribe write the same folders; `process_videos` no longer deletes the lesson folder.

## [0.1.3] — 2026-05-17

### Added
- Plugin: [course-crawler](plugins/course-crawler/CHANGELOG.md) v0.3.0 — capture any online content (single pages, full courses incl. Skool classrooms, YouTube playlists) into a clean knowledge-base archive. Browser-backend abstraction, assisted/manual login, Next.js `__NEXT_DATA__` Skool parser, clean per-course output tree (Markdown + reference links + assets + slides + transcripts), and local GPU Whisper by default with Groq/OpenAI fallback.

## [0.1.2] — 2026-05-15

### Added
- Plugin: [offer-architect](plugins/offer-architect/CHANGELOG.md) v0.2.2 — Hormozi-structured offer building for coaches, with a 3–5 page Offer Blueprint + plain-English Projected Success Score report as the capstone outputs. Two-layer scoring (preventive exit-checks + capstone audit), 4-framework naming system (MAGIC / SMILE & SCRATCH / Igor / Neumeier), and a hard no-inventing-deliverables rule enforced via provenance tags.

## [0.1.0] — 2026-05-07

### Added
- Initial marketplace release
- Plugin: [claude-workspace-superengine](plugins/claude-workspace-superengine/CHANGELOG.md) v0.1.0
- Plugin: [ghl-coach-superengine](plugins/ghl-coach-superengine/CHANGELOG.md) v0.1.0
- CI: GitHub Actions workflow for plugin schema validation on every push
- Docs: architecture, plugin-conventions, creating-plugins
