# Changelog — revxl-marketplace

Marketplace-level changelog. For plugin-specific changes, see each plugin's own CHANGELOG.md.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
