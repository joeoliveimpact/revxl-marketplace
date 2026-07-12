# Changelog — carousel-superengine

## [Unreleased]

- **Brain wiring (content-strategy vault):** `references/vault-api.md` added (same client
  contract as shortform-superengine — key ladder, power params, budget + cache discipline,
  degrade table). `carousel-create` gains 2 named Brain triggers: pull #1 (topic frameworks,
  step 3 slide map) + pull #2 (hook patterns, step 4, optional). ≤2 searches + ≤3 note reads
  per carousel, cached to `brain-pulls/`, never blocking — no key = bundled refs, unchanged
  behavior.

## 0.1.0 — 2026-07-05

Initial release.

- 5 commands: `carousel-start-here`, `carousel-setup`, `carousel-guide`, `carousel-create`,
  `carousel-teardown` + bundled `brand-brain` producer (shared VoC contract at
  `~/.claude/revxl/<brand>/voc/`).
- Generation: 3 build blueprints (educational, story-led, case-study), Triple Hook architecture,
  swipe-retention devices, dual-CTA sequencing, per-slide design directions, 4-part SEO caption,
  alt text, platform variants (IG 4:5 native / LinkedIn 1:1 PDF).
- Teardown: SocialCrawl bring-your-own-key post pull (cover + caption + metrics, cover-only stated
  honestly) with optional full-slide local fetch on Claude Code (`scripts/carousel_fetch.py`,
  public posts, rate-respecting).
- Knowledge base distilled from a 56-source curated 2026 research notebook.
- Quality gate + genericized full-depth exemplar as the density bar.
- Config persists via `${CLAUDE_PLUGIN_DATA}`; brand-brain files synced from the canonical source
  via `scripts/sync-brand-brain.py`.
