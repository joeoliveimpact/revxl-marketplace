# Changelog — carousel-superengine

## 0.1.1 — 2026-07-06

Full-slide teardown fetch rebuilt for the post-2026 Instagram reality.

- **Fetch swapped to Instagram's authenticated mobile API** (`scripts/carousel_fetch.py`) — the only
  path that still returns every slide. Anonymous fetch and instaloader's web path are both dead
  (`403 login_required`, mid-2026); the old `Post.from_shortcode` mechanism no longer works.
- **Capture is a cookie paste** — the client exports their Instagram cookies once with the free
  Cookie-Editor browser extension (setup walks them through it, see `references/ig-cookie-setup.md`) and
  the engine saves them to `${CLAUDE_PLUGIN_DATA}`. No browser automation, no login script, no terminal.
- **Fetch is stdlib-only** — no pip install at all (dropped both the old instaloader dependency and the
  interim patchright approach). Per-client own cookies, never a shared account. Refresh only when a
  fetch reports `login_required` (no scheduled expiry). stdout JSON contract unchanged.
- Proven live: 8-slide carousel pulled end-to-end from a cookie export.

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
