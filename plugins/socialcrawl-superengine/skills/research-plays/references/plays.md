# Play runbooks — the roster and the six plays

## The roster

**Never hand-write `~/.claude/revxl/entities.jsonl`.** Its reader is tolerant and therefore
silent — a line under the wrong field parses fine, never fires, and never says so. The writer
refuses what that reader could not match (too short, too long, a URL, past its read window) and
names the rule; relay that reason, don't work around it. `SC_REVXL_HOME` moves the file.

**What it buys them:** next session *"research …"* or *"look into …"* beside that handle wakes
the `research-suggest` hook. It is a co-occurrence signal — phrase AND handle, so a rostered
name in ordinary chatter stays quiet. Free: one local file, no call out.

## Voice-of-Customer mining `[C]`

**Row:** `people_saying` in [packages.json](packages.json).

**When:** building or refreshing a brand brain; hunting pain language, objections, and
audience vocabulary for a niche.

1. `GET /v1/reddit/omni-search?query=<niche keyword>` (**5–8cr+ each**, metered: 1cr per
   search page + 1cr per successfully-expanded thread, min 5; failed threads refunded) —
   threads across all of Reddit, subreddit attribution, top comments inline. Run 2–4
   keyword variants (pains, product category, "alternatives to X"), each its own plain `curl`
   call ([execution.md](execution.md) §1), never a loop. **Estimate: ~20–32cr
   total** — say it before the first call.
2. Comments under proven content: `GET /v1/prism/comments?url=<top post>` (**2–5cr+ each**,
   metered: 1cr per internal page with a floor of 2, driven by `max=`; an Instagram URL is
   a flat 5cr) on the client's and competitors' top 3–5 posts. Say the running total.
   Try prism first; fall back to platform-native (`instagram/post/comments` 5cr,
   `tiktok/post/comments` 1cr, `youtube/video/comments` 1cr) only if prism coverage fails
   for that platform.
3. Optional deep add-on (big gun): `prism/audience-questions` (30cr) — see
   [big-guns.md](big-guns.md).

**Output:** a pain-language doc — verbatim quotes grouped by theme (pains / desired
outcomes / objections / vocabulary), each with source URL. Feeds any brand-brain /
voc-profile artifact.

## Ad-library recon `[CJ]`

**Row:** `competitor_ads` in [packages.json](packages.json).

**When:** what is a competitor (or the whole niche) running as paid creative right now?

1. Find the advertiser: `GET /v1/facebook/adlibrary/search/companies?query=<name>` (5cr).
2. Pull their ads: `GET /v1/facebook/adlibrary/company/ads?pageId=<id>` (5–35cr, metered: 5 a
   page, and `include=audience` holds 1cr per ad).
3. Detail interesting ads: `GET /v1/facebook/adlibrary/ad?id=<adId>` (5cr each — cap at
   3–5, say the running total).
4. Google/YouTube variant: `google/adlibrary/advertisers/search` → `google/company/ads`
   → `google/ad` (5cr each). LinkedIn B2B variant: `linkedin/ads/search` → `linkedin/ad`
   (5cr each).

**Pre-flight estimate:** a one-competitor teardown ≈ 15–65cr. Say it before step 1.
**Output:** ad teardown table — hook / creative format / offer / CTA / landing URL per ad,
with a "what to steal" line each. For spoken ad copy, `facebook/adlibrary/ad/transcript`
bills **10cr per ad** and the guard asks before it runs — quote that, offer the cheaper
route (pull the ad's media URL at 1–5cr and transcribe it locally for free), and run the
paid call only on an explicit yes.

## AI-visibility (GEO) audit `[CJ]`

**Row:** `ai_visibility` in [packages.json](packages.json).

**When:** "does ChatGPT/Perplexity/AI search surface me (or my client) when my topic is
asked?" — the AI-era SEO check.

1. Draft 5–10 prompts a real buyer would ask an AI (topic + "best X for Y" + "who should
   I follow for X").
2. `GET /v1/prism/ai-visibility?...` — ⚠️ **the most under-quoted endpoint in the system.**
   It is **2cr per probe, and a probe is `prompt × run × engine`**, not per prompt. At
   defaults (`runs=8` × 2 engines = 16 probes per prompt) a **5-prompt audit is ~160cr, not
   10.** Measured live: `preset=quick` = **20cr**; 20 prompts × 20 runs = **1,600cr**.
   **Always pass an explicit `preset=` for a flat budget, state the number, and get an
   explicit yes.** This is a big-gun gate, not a 2cr call.
3. Read per-engine appearance-% + the cited-domain ranking.

**Output:** AI-visibility report — per prompt: which engines mention the brand, who IS
being recommended instead, and the cited domains to target. Repeat quarterly; the deltas
are the story.

## Link-in-bio / offer recon `[CJ]`

**Row:** `competitor_offer` in [packages.json](packages.json).

**When:** map a competitor's (or prospect's) full offer ladder from their social bio.

1. Get the bio URL from the profile you already have (or `instagram/profile` 1cr).
2. `GET /v1/prism/lookup?url=<bio url>` (**1–5cr**, worst case 5 — 1 for most social
   links, 5 for an advanced one such as Amazon or LinkedIn) — dispatches linktree/linkbio/linkme/
   komi/pillar automatically; direct page endpoints are 1cr if needed.
3. For non-link-in-bio sites, note the URL for a web-scrape tool (outside this API).

**Output:** offer-ladder map — every link, its offer, price point if visible, and funnel
position (lead magnet → low ticket → core → high ticket). Cost: **2–7cr**. The
`free-offer-sketch` play builds the same artifact for **0cr** from public pages; the 2–7cr
here buys the dispatcher resolving a hosted link page the free route cannot open cleanly.

## Audience demographics `[C]`

**Row:** `who_is` in [packages.json](packages.json).

**When:** validate an ICP claim with real data — "is your audience actually 35+ women?"
TikTok only (nothing comparable exists on IG).

1. `GET /v1/tiktok/user/audience?handle=<handle>` (5cr — say cost first).

**Output:** ICP-validation one-pager: age/gender/geo split vs the claimed ICP, one
"match / mismatch" verdict line, and what to change if mismatched (content targeting, not
identity). Pairs well with a competitor handle for contrast (+5cr, confirm).

## Dev radar `[J]`

**Row:** `dev_radar` in [packages.json](packages.json).

**When:** operator-side intel — track what's shipping in AI/dev tooling, monitor repos this
stack depends on, mine tool complaints for build ideas.

1. Pulse: `GET /v1/hackernews/search?query=<tool/topic>` (1cr) → interesting story →
   `hackernews/story/comments` (1cr).
2. Repo watch: `github/repo/releases` · `repo/issues` · `repo/readme` (1cr each).
3. Build-gap radar: `github/repo/top-issues` (5cr) — a repo's top feature request + top
   complaint in one call. Deeper: `github/repo/dossier` (5cr).
4. Gated bundles when it matters (see big-guns): `prism/launch-echo` (20cr flat, how a launch
   landed), `prism/devtool-pulse` (20cr flat), `prism/org-radar` (**6–26cr**, metered: 1cr to
   resolve the org + 5cr per repo dossiered; unused per-repo credits auto-refund, so 1 repo
   measured at 6cr and 26 is the ceiling reservation, not the price).

**Output:** a dated radar note — what moved, what broke, what people are begging for, and
any build idea it suggests.
