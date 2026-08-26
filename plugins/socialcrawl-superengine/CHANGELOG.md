# Changelog — socialcrawl-superengine

## 0.2.1 - 2026-08-25

### Fixed
- **The credit guard has never once fired since 0.1.1 - it now does (in terminal sessions).**
  The hook emitted a decision missing the required `hookEventName`, and put its reason in
  `systemMessage` rather than `permissionDecisionReason`. Claude Code cannot route such a
  decision, so it discarded the output and ran the command - exit 0, no error, nothing
  logged. Invoked by hand the script printed a perfect-looking `deny`, which is why three
  earlier investigations cleared it. Every banned transcript call and every un-confirmed
  paid call since 0.1.1 went through unguarded.

  **Coverage - please read, and note what is NOT claimed:**
  - **Terminal `claude` sessions: enforcement confirmed.** Measured.
  - **Claude Desktop: unverified, and not previously testable.** Earlier notes said the hook
    "is not invoked" in Desktop. That was never established. Desktop materialises plugins from
    the *published* marketplace version, and every published build until this one carried the
    inert guard above - so what was measured was a dead hook failing to fire, which says
    nothing about whether Desktop invokes hooks at all. **0.2.1 is the first build on which
    that question can actually be answered.** Until it is, assume Desktop is unguarded.
  - **Cowork: not enforced.** Plugin hooks are never loaded there. Independently confirmed.

  If you rely on the guard, run SocialCrawl work from a terminal session.
- **Six metered endpoints were priced as flat calls.** Worst is `prism/ai-visibility`,
  stored at 2 credits but billed **2 per probe** - its defaults (8 runs x 2 engines) make
  the cheapest real call **32 credits**, and at 2 it sat below the guard's 5-credit ask
  threshold, so it spent silently. Also `prism/share-of-voice` (40/brand, 2-5 brands),
  `prism/org-radar` (5/repo), `prism/comments` (1 per page scanned), `reddit/omni-search`
  (per page + per expanded thread) and `search/news` (per leg). `_perUnit` now carries 14
  entries; the guard quotes the unit and the realistic worst case, never the unit price
  alone.
- **`prism/lookup` was hardcoded as free but bills 1 credit.** Measured live and uncached:
  the catalog, the vendor's pricing page and the utility endpoint all store 0; two successful
  calls each billed 1. The guard returned 0 *before* consulting the cost map, so the spend was
  not merely mispriced - it was never recorded at all, and could never contribute to the
  15-credit "still going?" prompt. A loop of lookups reported nothing and gated nothing. The
  override lives in the hook rather than in `costs.json`, because that file is generated from
  the vendor spec and a regeneration would silently restore the 0.
- **The cost figures the skills quote were wrong wherever an endpoint is metered.** The
  guidance told the model that a client with a *low balance* should be offered "the free/1cr
  cheat codes" - a list on which `prism/post-stats` really bills per URL (100 Instagram links
  = 500 credits), `prism/comments` 2-5+, and `reddit/omni-search` 5-8+. That pointed the
  broke client at the most expensive endpoint available. Every metered endpoint now quotes a
  `low-high` range with the parameter that drives it, and the cheat-code list is replaced by a
  real-cost table. `share-of-voice` 40 -> 80-200, `org-radar` 26 -> 6-26, `ai-visibility`
  "~10cr" -> 20-1,600.
- **The API key is no longer written into commands or requested in chat.** The skill
  previously inlined the key value into every curl - putting it in the transcript - and
  onboarding asked you to paste it into the conversation. Calls now read it at run time
  from the key file. Both instructions were inherited verbatim from upstream. **If you set
  up on 0.1.x or 0.2.0, rotate your key.**

### Added
- **`setup/` - a double-clickable key helper** (`setup-key.bat`/`.ps1` on Windows,
  `setup-key.command` on macOS/Linux). Opens its own window, hides the key as you type,
  verifies it against the free balance endpoint before saving, writes it with owner-only
  permissions, and writes nothing at all if verification fails. The key never touches the
  chat. The Windows path is verified; the macOS/Linux script ships untested.

### Known stale
- The plugin describes itself as covering **48 platforms / 381 endpoints**. A full live sweep
  on 2026-08-23 measured **400**. The reference files also disagree with each other (one tier
  table sums to 417 directly above a "Total: 381"). These counts are descriptive only - no
  cost or gating decision reads them - and correcting them requires regenerating the reference
  set, which is deliberately not bundled into a guard-safety release.

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
