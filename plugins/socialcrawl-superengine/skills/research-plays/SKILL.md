---
name: research-plays
description: >
  Guided social research plays on the SocialCrawl API. Use when the user wants
  outcome-level research rather than a single API call: "what are customers /
  the audience saying" (voice-of-customer mining), "what ads is a competitor
  running" (ad-library recon), "does ChatGPT / AI recommend me or my client"
  (AI-visibility audit), "map their offer / link-in-bio", "who is their
  audience" (demographics), "what's happening in dev tools / on Hacker News"
  (dev radar), "vet this creator", "find leads", "share of voice", or any
  multi-endpoint research workflow. Every play pre-flights the credit balance
  and states costs before spending; big-gun one-shots (15–50 credits) are
  always explicitly cost-gated.
---

# Research Plays

Guided multi-endpoint research workflows on SocialCrawl. Each play = when to run it, the
calls with exact credits, a pre-flight estimate, and the output artifact.

**Teach mode:** read `~/.claude/revxl/teach-mode` if it exists; absent = `beginner`. In
beginner voice, explain each play in plain English before running it and translate every
metric in the output.

**Audience tags:** `[C]` = a client deliverable/workflow · `[J]` = operator-facing intel
(the person running this system) · `[CJ]` = both.

## Ground rules (every play)

1. Resolve the API key + policies via the `socialcrawl` skill in this plugin — key
   resolution, response envelope, error handling all live there. Its ⛔ transcription ban
   applies here verbatim: **no `*/transcript` endpoint, ever.**
2. **Pre-flight**: `GET /v1/credits/balance` (0cr) before the first paid call of any play.
   State the play's estimated total cost before starting it.
3. **Loops**: estimate `calls × cost` up front and say it. Never loop a ≥10cr endpoint.
4. **Gates** (from the canon skill): 1cr free-flow · 5cr say-cost-first · 10cr+ explicit
   yes per call · 15–50cr big guns = balance + named cost + explicit confirm, **never
   batched, never auto-repeated**.
5. Cheat codes first: a pasted URL goes through `prism/lookup` (0cr); re-checking many
   posts goes through `prism/post-stats` (1cr per 100 URLs); comment pulls try
   `prism/comments` (1cr) before platform-native comment endpoints.

## Play: Voice-of-Customer mining `[C]`

**When:** building or refreshing a brand brain; hunting pain language, objections, and
audience vocabulary for a niche.

1. `GET /v1/reddit/omni-search?query=<niche keyword>` (1cr) — threads across all of
   Reddit, subreddit attribution, top comments inline. Run 2–4 keyword variants
   (pains, product category, "alternatives to X"). Estimate: ~2–4cr total.
2. Comments under proven content: `GET /v1/prism/comments?url=<top post>` (1cr each) on
   the client's and competitors' top 3–5 posts. Try prism first; fall back to
   platform-native (`instagram/post/comments` 5cr, `tiktok/post/comments` 1cr,
   `youtube/video/comments` 1cr) only if prism coverage fails for that platform.
3. Optional deep add-on (big gun): `prism/audience-questions` (30cr) — see
   [references/big-guns.md](references/big-guns.md).

**Output:** a pain-language doc — verbatim quotes grouped by theme (pains / desired
outcomes / objections / vocabulary), each with source URL. Feeds any brand-brain /
voc-profile artifact.

## Play: Ad-library recon `[CJ]`

**When:** what is a competitor (or the whole niche) running as paid creative right now?

1. Find the advertiser: `GET /v1/facebook/adlibrary/search/companies?query=<name>` (5cr).
2. Pull their ads: `GET /v1/facebook/adlibrary/company/ads?pageId=<id>` (5cr).
3. Detail interesting ads: `GET /v1/facebook/adlibrary/ad?id=<adId>` (5cr each — cap at
   3–5, say the running total).
4. Google/YouTube variant: `google/adlibrary/advertisers/search` → `google/company/ads`
   → `google/ad` (5cr each). LinkedIn B2B variant: `linkedin/ads/search` → `linkedin/ad`
   (5cr each).

**Pre-flight estimate:** a one-competitor teardown ≈ 15–35cr. Say it before step 1.
**Output:** ad teardown table — hook / creative format / offer / CTA / landing URL per ad,
with a "what to steal" line each. ⛔ Never call `facebook/adlibrary/ad/transcript` — banned;
video-ad spoken content comes from the local transcription chain if truly needed.

## Play: AI-visibility (GEO) audit `[CJ]`

**When:** "does ChatGPT/Perplexity/AI search surface me (or my client) when my topic is
asked?" — the AI-era SEO check.

1. Draft 5–10 prompts a real buyer would ask an AI (topic + "best X for Y" + "who should
   I follow for X").
2. `GET /v1/prism/ai-visibility?...` (**2cr per topic/prompt set** — estimate total first;
   a 5-prompt audit ≈ 10cr, confirm).
3. Read per-engine appearance-% + the cited-domain ranking.

**Output:** AI-visibility report — per prompt: which engines mention the brand, who IS
being recommended instead, and the cited domains to target. Repeat quarterly; the deltas
are the story.

## Play: Link-in-bio / offer recon `[CJ]`

**When:** map a competitor's (or prospect's) full offer ladder from their social bio.

1. Get the bio URL from the profile you already have (or `instagram/profile` 1cr).
2. `GET /v1/prism/lookup?url=<bio url>` (**0cr**) — dispatches linktree/linkbio/linkme/
   komi/pillar automatically; direct page endpoints are 1cr if needed.
3. For non-link-in-bio sites, note the URL for a web-scrape tool (outside this API).

**Output:** offer-ladder map — every link, its offer, price point if visible, and funnel
position (lead magnet → low ticket → core → high ticket). Cost: ~0–2cr. The cheapest
competitive-positioning artifact in the whole system.

## Play: Audience demographics `[C]`

**When:** validate an ICP claim with real data — "is your audience actually 35+ women?"
TikTok only (nothing comparable exists on IG).

1. `GET /v1/tiktok/user/audience?handle=<handle>` (5cr — say cost first).

**Output:** ICP-validation one-pager: age/gender/geo split vs the claimed ICP, one
"match / mismatch" verdict line, and what to change if mismatched (content targeting, not
identity). Pairs well with a competitor handle for contrast (+5cr, confirm).

## Play: Dev radar `[J]`

**When:** operator-side intel — track what's shipping in AI/dev tooling, monitor repos this
stack depends on, mine tool complaints for build ideas.

1. Pulse: `GET /v1/hackernews/search?query=<tool/topic>` (1cr) → interesting story →
   `hackernews/story/comments` (1cr).
2. Repo watch: `github/repo/releases` · `repo/issues` · `repo/readme` (1cr each).
3. Build-gap radar: `github/repo/top-issues` (5cr) — a repo's top feature request + top
   complaint in one call. Deeper: `github/repo/dossier` (5cr).
4. Gated bundles when it matters (see big-guns): `prism/launch-echo` (20cr, how a launch
   landed), `prism/devtool-pulse` (20cr), `prism/org-radar` (26cr).

**Output:** a dated radar note — what moved, what broke, what people are begging for, and
any build idea it suggests.

## Big guns — one-shot deliverables (15–50 credits, ALWAYS gated)

High-cost Prism bundles that replace hours of manual research with one call. Rules: never
batched, never looped, never called without balance + named cost + an explicit yes.
Per-play runbooks: **[references/big-guns.md](references/big-guns.md)**.

| Play | Endpoint | Credits |
|------|----------|---------|
| Audience questions (content-seed engine) | `prism/audience-questions` | **30** |
| Creator vetting (partnership due diligence) | `prism/creator-vet` | **50** |
| Lead discovery (competitor switchers) | `prism/leads` | **50** |
| Share of voice (2–5 brands) | `prism/share-of-voice` | **40** |
| Reputation report (cross-source) | `prism/reputation` | **30** |
| Campaign tracker (launch lift) | `prism/campaign` | **35** |
| Earned-media footprint | `prism/earned-media` | **25** |
| Crisis radar (mention-volume breach check) | `prism/crisis-radar` | **15** |
| TikTok audience overlap (2 creators) | `prism/audience-overlap` | **20** |
| Universal 12-source search | `search/everywhere` | **20** |
