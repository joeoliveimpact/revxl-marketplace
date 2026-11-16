# The search ladder — climb it cheap-first, never open at the top

6. **Search cheap-first — climb the ladder, never open at the top.** Any play that searches
   starts on the cheapest rung that answers the question: `/v1/{platform}/search` (**1–125cr: 1cr a page on many
   social platforms, 5cr on the retail ones** — `ebay`, `home_depot`, `walmart`, `wayfair`; and
   metered on others: `threads/search` **1–34cr**, `tiktok/search` **1–42cr**, `douyin/search` up to **125cr**) when the platform is known. ⚠️ **Four platforms have no
   `{platform}/search` at all, so check which search each one has:** LinkedIn's cheapest content
   search is `linkedin/search/posts` at **1–56cr**, metered (`/people` is **10–50cr**, `/jobs` **10cr**; the 1cr
   `/industry`, `/location`, `/schools` are id resolvers, not search), X/Twitter has
   `twitter/search/tweets` at **1–9cr** (1 a page) plus `twitter/ai-search` at **5cr** for a question, Facebook has
   `facebook/search/posts` at **1–9cr** (1 a page) plus the narrow `events/search` and `marketplace/search` at 1cr and `adlibrary/search/*` at 5cr, and
   Snapchat has no search at all. Check the platform before quoting a floor ·
   `/v1/reddit/omni-search` (**5–9cr**, metered: 1cr per search page + 1cr per expanded
   thread, min 5) for all of Reddit with top comments inline ·
   `/v1/search/news` (**2–62cr**, metered: base fee + 1cr per leg that returns articles) for
   news · `/v1/search/forums` (**10cr flat**) for Reddit + Hacker News + Naver together ·
   `/v1/search/everywhere` (**20cr flat**) only for a true cross-platform sweep (14 platforms, up to 17 sources). A request that
   merely *sounds* broad is not a reason to escalate — "what are people saying about X on
   Reddit" is a single-platform question, and the per-platform `search` (here `reddit/search`, 1cr a page, up to 34cr with
   `include_body=`, `relevant_to=` and a paid `label=`) is the rung that answers it.

> **Before booking the 20cr sweep, climb the search ladder.** Most voice-of-customer questions
> are answered a rung or two lower — but the bottom rung's price varies by platform and the two
> middle rungs are metered, so quote the range. Only the top two are flat:
>
> | Scope of the question | Endpoint | Credits | What drives it |
> |----------------------|----------|---------|----------------|
> | One platform (named or implied) | `/v1/{platform}/search` | **1–125cr** | 1cr a page on many social platforms · 5cr retail (`ebay`, `home_depot`, `walmart`, `wayfair`) · metered on others: `threads/search` 1–34, `tiktok/search` 1–42, `douyin/search` 5–125 |
> | All of Reddit, top comments inline | `/v1/reddit/omni-search` | **5–9cr** | 1cr/search page + 1cr/expanded thread, min 5 |
> | News across the web | `/v1/search/news` | **2–62cr** | base fee + 1cr/leg returning articles |
> | Discussion sites together (Reddit + Hacker News + Naver) | `/v1/search/forums` | **10** | flat |
> | A true cross-platform sweep (up to 17 sources) | `/v1/search/everywhere` | **20** | flat; auto-refunds if every source fails |
>
> `search/forums` is the missing middle rung — reach for it when the question spans discussion
> sites but does not need Instagram/TikTok/YouTube in the mix. Only pay 20cr when you actually
> want the planned, fused, reranked cross-platform result.

**The ladder inside a package row.** Each row in [packages.json](packages.json) is this ladder
for one kind of ask: its `free` path, when it has one, is the bottom rung and its paid `options`
sit above it. Start on the free rung; step up to a paid option only when the free one cannot answer.
