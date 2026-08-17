# Changelog — socialcrawl-superengine

## 0.2.0 — 2026-08-16

### Fixed
- **Batch endpoints bill per row, not per call — the previous release understated some
  costs by up to 500×.** 0.1.0 advertised `prism/post-stats` as "refresh a whole watchlist
  for 1 credit". It is metered per successful URL at that URL's platform rate, so 100
  Instagram links is **500 credits**, not 1. Eight endpoints bill per row / item / 50-id
  chunk / page; every one now renders its unit in the refs, and the credit guard always
  asks before a metered call. The error was inherited from SocialCrawl's own docs and was
  caught by a live test. **If you ran a large batch on 0.1.x, check your balance.**
- **Pagination guidance was teaching retired parameters.** SocialCrawl shipped a universal
  `cursor` parameter; the refs still directed you at each platform's native param
  (`max_id`, `next_max_id`, `page`). Send `pagination.next_cursor` back verbatim and the
  API maps it for you. 24 of 48 refs were affected.
- **The credit guard mis-priced two endpoints.** `costs.json` was keyed by bare path, so
  `POST /web/sessions` (5cr) passed as free against `GET /web/sessions` (0cr); costs are
  now verb-qualified. `POST /web/agent` (25cr) was missing entirely.
- `POST /youtube/transcripts` is now correctly denied — it is a transcript endpoint, and a
  live test confirmed 3 credits **per video**, so there is no batch discount to justify it.

### Added
- **Full catalogue coverage: 48 platforms / 381 endpoints** (was 43 / 333). New platform
  refs: ebay, home_depot, target, walmart, web. Every endpoint now carries the API's own
  description, its parameters and a ready-to-run curl.
- **"Which endpoint should I use?"** — seven decision tables plus a five-rung search ladder,
  so the cheapest correct endpoint is reachable. Previously every cross-platform search
  routed to `search/everywhere` at 20 credits while `search/forums` at 10 appeared nowhere.
- Endpoint-selection guidance for all 48 platforms, and stories/highlights routing.
- A Pagination section in `api-overview.md`, including the warning that **each page is a
  separately billed call**.

### Changed
- Refs are now generated from SocialCrawl's OpenAPI spec rather than its prose docs, and
  verified against the **live** catalogue. The old source documented GET operations only
  and could never see the 17 non-GET endpoints on web / youtube / prism.

## 0.1.1 — 2026-07-05

- Enforced credit-guard hook + prompt-injection defense (published directly to the
  marketplace; backfilled here for an accurate history).

## 0.1.0 — 2026-07-04

Initial release.

- **`socialcrawl` skill (canon):** full 43-platform / 333-endpoint reference set,
  generated from SocialCrawl's own docs + pricing registry — every endpoint row carries
  its **exact** credit cost (the public 1/5/10 tier model hides ~30 flat-override
  endpoints priced up to 50 credits; the refs don't). Cheat-codes section (free
  `prism/lookup` URL dispatcher, 1-credit `prism/post-stats` for 100 URLs, 1-credit
  `prism/comments`, 1-credit `reddit/omni-search` VoC sweep, 5-credit
  `prism/handle-audit` pre-pull gate). Hardened ⛔ transcription ban on all 9
  `*/transcript` endpoints.
- **`research-plays` skill:** 6 guided plays (VoC mining, ad-library recon,
  AI-visibility audit, link-in-bio offer recon, TikTok audience demographics, dev
  radar) + 10 big-gun one-shot runbooks (15–50cr) behind a strict gate ritual
  (balance + named cost + explicit confirm, never batched).
- **`onboarding` skill:** BYO-key setup with guided signup, 1-credit verify,
  plain-English credit briefing, and the `~/.claude/socialcrawl-superengine/.superengine`
  marker that RevXL format engines detect to offer deep plays.
