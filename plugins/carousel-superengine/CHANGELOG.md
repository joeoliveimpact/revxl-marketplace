# Changelog — carousel-superengine

## 0.2.2 — 2026-07-13

The generator now consults the engine's full intelligence before and during every build: a winning
check against prior inspire/teardown analysis (weak concepts get evidence-cited pivot proposals —
suggest-then-approve, never a gate, SKLLPLG-77), plus the Brain wiring that pulls the
content-strategy vault into the slide map and hook drafting.

- **Brain wiring (content-strategy vault):** `references/vault-api.md` added (same client
  contract as shortform-superengine — key ladder, power params, budget + cache discipline,
  degrade table). `carousel-create` gains 2 named Brain triggers: pull #1 (topic frameworks,
  step 3 slide map) + pull #2 (hook patterns, step 4, optional). ≤2 searches + ≤3 note reads
  per carousel, cached to `brain-pulls/`, never blocking — no key = bundled refs, unchanged
  behavior.

- **NEW step 1.5 in `carousel-create` — consult the data + winning check.** Before the frame lock,
  the resolved concept (topic, repurposed content, or call build — every input mode) is judged
  against what's winning in the niche: the freshest persisted inspire synthesis + relevant
  teardowns, the avatar pain map, and the bundled pattern refs. Strong → one line on why, proceed.
  Needs repackaging → 1-3 pivots/lane shifts that stay close to the original concept, each naming
  its evidence; the coach picks and the original always stays an option. Soft-consume: topic-only
  builds keep working, and a weak verdict never blocks a build.
- **Analysis persistence — plugin data dir only.** `carousel-inspire` now saves its pattern report
  to `${CLAUDE_PLUGIN_DATA}/analysis/inspire-<niche-slug>-<MM.DD.YY>.md` and `carousel-teardown`
  saves its analysis to `${CLAUDE_PLUGIN_DATA}/analysis/teardown-<slug>-<MM.DD.YY>.md`, so Monday's
  research feeds Thursday's build. Reports live in the plugin's own local data dir alongside
  business-config; nothing writes to the shared brand brain or any external knowledge store.
- **Freshness-aware.** The winning check states the report's age every time; >30 days is stale
  niche intel, which earns an offer of ONE credit-gated inspire refresh — then the build proceeds
  either way.

## 0.2.1 — 2026-07-12

Knowledge refresh (2026 algo signals) + config read-path fix. From the vetted 07.08.26 notebook +
skill audit (SKLLPLG-65); contested signals are flagged with dated notes, never hard-coded.

- **2026 algorithm signals** — shares/sends named the strongest distribution signal; saves flagged
  as contested/evolving (some 2026 reporting says downweighted) in slide-architecture +
  platform-nuance; LinkedIn's 2026 dwell-time "Depth Score" + ~60% external-link reach penalty;
  carousel+audio → Reels-tab eligibility; re-serve ranking mechanics behind the Triple Hook.
- **Triple Hook sharpening** — hook-swap play (frontload the proven slide via per-slide like
  insights), 60-90 day upcycle cadence (Mosseri-sanctioned), raw-over-polished named as a 2026
  shift.
- **Per-slide caption guidance** — Instagram's per-slide captions (live June 18, 2026, up to 20):
  when to use single vs multiple, SEO implications, CTA-slide caption lever; caption-length
  sweet-spot claim marked contested (words vs characters) with a test-variable note.
- **Comment-CTA caveat** — conflicting 2026 evidence on comment-CTAs and reach; DM keyword framed
  as a conversion play, vendor benchmarks marked directional-only.
- **Design + QA freshening** — IG UI safe zone (bottom 150-250px / top ~120px), ~1.5s glance-time
  word target, LinkedIn 6-10 pages (7-10 sweet spot, <5 reach-cap risk), LinkedIn PDF 4:5 now
  preferred over 1:1, swipe-retention loop-back close + progress indicators + Q1 2026 benchmarks.
- **Config read-path fix** — every skill now reads the persisted config at
  `${CLAUDE_PLUGIN_DATA}/business-config.md` FIRST when present; the copy in
  `references/business-config.md` is the shipped template only. `carousel-setup` now names its
  exact write target instead of leaving the filename implicit.

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
- Config persists via `${CLAUDE_PLUGIN_DATA}`; brand-brain files read from the canonical shared
  source at `~/.claude/revxl/<brand>/voc/`.
