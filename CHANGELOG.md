# Changelog — revxl-marketplace

Marketplace-level changelog. For plugin-specific changes, see each plugin's own CHANGELOG.md.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.41] — 2026-08-04

### Changed
- **workspace-superengine v0.9.1** — `/update-everything` gains cache health: live-PID cross-checking so stale `.in_use` lock files stop reading as "loading two versions at once", plus superseded-version reporting and a triple-gated cleanup offer (never the current version, never one a live process holds, never without explicit consent).

## [0.1.40] — 2026-08-03

### Changed
- **workspace-superengine v0.9.0** — adds `/update-everything`, one command that runs every update path (marketplaces → plugins → npx skills global+project → CLI), reports a before/after diff, names the Desktop-installed plugins the CLI cannot reach, health-checks workspace-local skills for unparseable frontmatter, and offers to schedule itself weekly.

## [0.1.32–0.1.39] — 2026-07-12 → 2026-08-02 (catch-up entry)

The per-release log went dark for this window; reconstructed from the catalog's git history. Rule going forward (CI-enforced): every release PR updates this file and the README catalog table.

### Added
- **meta-ads-superengine v0.3.0** (07.23, catalog 0.1.38) — 27-skill Meta-ads coaching journey. First proprietary-licensed plugin in the catalog.
- **lead-magnet-superengine v0.1.0** (07.12, 0.1.33) — three-door lead-magnet engine.
- **focus-group-superengine v0.1.0 → 0.1.1** (07.12, 0.1.31/0.1.34) — synthetic persona-swarm marketing tester; 0.1.1 adds honest depth tiers.
- **profile-optimization-superengine v0.1.0** (07.13, 0.1.36) — social-profile optimization engine.

### Changed
- **promptception v0.2.0** (08.02, 0.1.39) — Orchestrator Mode (2 skills + 5 tiered agents + trigger hook) and `/goal-builder`, `/loop-builder`, `/schedule-builder`. Repo also gains `.gitattributes` forcing LF on shell scripts.
- **workspace-superengine v0.8.2** (08.01) — commits the workspace repo at closeout.
- **carousel-superengine v0.2.1 → v0.2.2** (07.12–13, 0.1.32/0.1.35) — config read-path fix; winning-check + read-side analysis wiring.
- **carousel-superengine catalog drift fixed** (07.24, 0.1.38) — entry said 0.3.0 while plugin.json shipped 0.4.1; both stale spots corrected.

## [0.1.31] — 2026-07-21

### Changed
- Plugin: [shortform-superengine](plugins/shortform-superengine/CHANGELOG.md) **v0.3.1** — ships C19, the sixth enforced craft screen. Secondary-hook placement is no longer a single judgement call: Step 3 computes the placement COUNT from the length target via the retention-psychology dosage table (30s→1 · 45s→1–2 · 60s→2–3 · 90s→3–4) before generating, then offers three scored options per slot. Dogfood catch — a 63s listicle shipped with one secondary hook and the user hand-added the two the table calls for. The fix landed after v0.3.0 was tagged, so this bump is what puts it in clients' hands.

## [0.1.30] — 2026-07-16

### Changed
- Plugin: [shortform-superengine](plugins/shortform-superengine/CHANGELOG.md) **v0.3.0** — the C-gate + dogfood release. Dual-track analysis (spoken transcripts primary, captions a separate packaging read — schema 1.2 additive), live pipeline-shape ingest in the scripting brief, Pattern Matrix beat/pattern measurement layer (field-proven on a 1,000-reel corpus), GURU competitor tier, visual deliverables renderer, Brain API triggers, and five enforced craft screens surfaced by own-brand dogfooding: mandatory skeleton optimization, custom-idea field vetting (LOSER→pivot / UNTESTED→first-mover de-risk), loop-integrity seam check, second-person-default line pass, text-overlay storyboard. Verified end-to-end on two live reels before ship.

## [0.1.29] — 2026-07-07

### Removed
- Plugin: **plugin-doctor** moved out to its own standalone repo — [joeoliveimpact/plugin-doctor](https://github.com/joeoliveimpact/plugin-doctor). A repair tool for stalled/404'd plugin installs shouldn't ship inside the marketplace it repairs (chicken-and-egg), and it's a general-purpose utility. Existing installs are unaffected; re-add it from the new home with `claude plugin marketplace add joeoliveimpact/plugin-doctor` then `claude plugin install plugin-doctor@plugin-doctor`. Catalog now ships 12 plugins.

## [0.1.28] — 2026-07-06

### Fixed
- Plugin: [gokollab-community-superengine](plugins/gokollab-community-superengine/CHANGELOG.md) v0.1.2 — bundled `clientclub` CLI binaries rebuilt with the `add-users-to` array-body fix: `groups channels add-users-to --stdin` now accepts the JSON **array** body the API requires (previously failed locally with `cannot unmarshal array into map`, breaking the `onboard-member` add-to-channel step). All four platform binaries updated.

## [0.1.26] — 2026-07-05

### Added
- Plugin: [socialcrawl-superengine](plugins/socialcrawl-superengine/CHANGELOG.md) v0.1.1 — **enforced credit-guard hook**. A `PreToolUse` (Bash) hook cost-gates every paid SocialCrawl call before it spends and hard-blocks the 9 banned `*/transcript` endpoints; fail-open (any error → allow) and scoped to socialcrawl.dev commands only, so it never interferes with other work. Ships a 333-endpoint `costs.json` cost table + `credit-guard.mjs`. Adds `_shared/references/{credit-guard,untrusted-data}.md` — the credit-gate ritual and an injection-defense guide for treating scraped social content as untrusted data.

### Changed
- Plugin: [shortform-superengine](plugins/shortform-superengine/CHANGELOG.md) v0.2.3 — bundled `socialcrawl` lean core picks up the same `_shared/references/{credit-guard,untrusted-data}.md` safety guidance and a regenerated lean SKILL, keeping it in sync with the socialcrawl-superengine canon.

## [0.1.25] — 2026-07-04

### Added
- **New plugin: [socialcrawl-superengine](plugins/socialcrawl-superengine/CHANGELOG.md) v0.1.0** — deep social research superengine on the SocialCrawl API. Full 43-platform / 333-endpoint canon with exact per-call credits (generated from SocialCrawl's own docs + pricing registry), guided research plays (VoC mining, ad-library recon, AI-visibility audits, link-in-bio offer mapping, audience demographics, dev radar), and hard-gated big-gun one-shots (creator vetting, lead discovery, share-of-voice — 15–50cr, never batched). BYO key. Pairs with RevXL format engines via a detection marker, or runs standalone. 3 skills, zero MCPs. Catalog now ships 11 plugins.

### Changed
- Plugin: [shortform-superengine](plugins/shortform-superengine/CHANGELOG.md) v0.2.2 — bundled `socialcrawl` skill is now a generated lean core derived from the socialcrawl-superengine canon (12 refs, exact credits, 19 unused platform refs removed); competitor-cross-reference / reel-scripter / onboarding detect the superengine and offer its deep plays when installed (never a blocker); both-transcribers onboarding + dual-OS updating guide; reel-scripter Topic Pool mode.

## [0.1.14] — 2026-06-15

### Changed
- Plugin: [sales-call-blueprint-superengine](plugins/sales-call-blueprint-superengine/CHANGELOG.md) v0.1.2 — adds a gold-standard exemplar (`references/exemplar-strategy-blueprint.md`) and makes `strategy-blueprint` study + match it, enforcing full depth (all 10 discovery topics expanded, 3 scripted pillars, ~7-objection playbook, "do not compress" + ~25–35K target). Fixes thin output that didn't match the example blueprints.

## [0.1.13] — 2026-06-15

### Fixed
- Plugin: [sales-call-blueprint-superengine](plugins/sales-call-blueprint-superengine/CHANGELOG.md) v0.1.1 — skills now reference bundled `references/` and `templates/` files via `${CLAUDE_PLUGIN_ROOT}` instead of bare relative paths, so the frameworks, templates, and quality checklist load reliably once the plugin is installed on a client machine (bare paths could resolve against the user's working directory and silently fail to load).

## [0.1.12] — 2026-06-15

### Added
- **New plugin: [sales-call-blueprint-superengine](plugins/sales-call-blueprint-superengine/CHANGELOG.md) v0.1.0** — turns a pre-call DM thread into a customized, psychology-driven sales-call blueprint for coaches and closers. 5 skills (`start`, `setup`, `guide`, `triage-blueprint`, `strategy-blueprint`) + a `sales-blueprint-builder` batch agent. Two output modes (deep Pre-Call Prep doc / live Call-Time card), source-agnostic transcript pull (Fathom/Fireflies/Granola/GHL/manual/local-audio), pluggable delivery (Google Drive/local/GHL note/chat/custom), and a config-driven setup that ships with placeholders so each installer runs `setup` fresh. Pricing is never stored — supplied live. Catalog now ships 7 plugins.

## [0.1.10] — 2026-06-04

### Added
- **New plugin: [gokollab-community-superengine](plugins/gokollab-community-superengine/CHANGELOG.md) v0.1.0** — install-and-run community automation for clientclub / GoHighLevel (GoKollab) coaches: tiered member onboarding, group-call recap posts, and 1:1 call-history upkeep. Self-installs dependencies, captures the operator's own login (browser-MCP localStorage token capture, no terminal), discovers + confirms the community channel map, and runs an "ask the coach" setup interview. Bundles the clientclub CLI for Windows/macOS/Linux. Catalog now ships 6 plugins.

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
