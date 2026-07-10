# Changelog — carousel-superengine

## 0.2.0 — 2026-07-10

The engine now finishes the job: from topic to posted-ready slide IMAGES, with a compounding
template loop, niche-wide competitor intelligence, carousel-from-your-calls, and optional
scheduled draft builds. 6 skills → 9. Every skill now ends by offering the next step — no dead
ends anywhere in the engine.

- **NEW `carousel-render`** — package → finished images, routed per slide: **Path A** image-gen in
  the coach's look (ANCHOR → ONE-AT-A-TIME briefing per `references/render/render-briefing.md`;
  optional trained face via the Higgsfield Soul — always optional, never a gate) · **Path C** ONE
  paste-ready Claude Design prompt with the guardrails baked in · **workspace render** (Claude Code
  only): local HTML→PNG at exact 1080×1350 via `scripts/render_slides.py`, LinkedIn as a single
  5-10 page PDF. Degradation ladder — a render path always exists, down to the Canva-executable
  design directions.
- **NEW `carousel-templates`** — "save this look" captures a finished build as a per-brand design
  system (`~/.claude/revxl/<brand>/carousel/templates/`); "use my template" drops new copy into it
  and skips every design question. 90-day staleness nudge honors the run-the-system rule.
- **NEW `carousel-inspire`** — niche-wide synthesis across accounts + hashtag discovery: winning
  hooks/structures/topics/visual systems, every claim cited `@handle · metric · URL`, ranked build
  candidates in the coach's positioning. Hard credit gates with live balance at every rung.
- **Carousel from your calls** — "carousel from my last call": paste-first transcript intake
  (`references/transcript-intake.md`), auto-pull via the coach's connected recorder
  (`{{TRANSCRIPT_SOURCE}}`), graceful fallback to memory-with-flag. Client language always
  anonymized to avatar language on slides.
- **Scheduled draft builds (suggest-only)** — weekly/daily autopilot DRAFTS from the coach's
  topics/calls/templates (`references/scheduled-builds.md`). The engine never schedules without an
  explicit yes, scheduled runs spend zero credits by default, and posting is never automated.
  Config section F + `schedule-log.md` track it; "stop the weekly carousel" kills it.
- **Own-post review mode** in teardown — the coach's own posts get keep/change/try-next framing
  against their baseline, then "build the next iteration."
- **Teardown → render handoff** — downloaded slides now travel with the rebuild as the Path A
  visual reference set (style borrowed, content never).
- Wiring: setup captures data sources + render prefs + optional Soul (plain-English, skippable) +
  environment detect; create emits a per-slide render-handoff block; start-here routes all new
  intents; config gains `{{TRANSCRIPT_SOURCE}}`, rendering tokens, and section F.

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
