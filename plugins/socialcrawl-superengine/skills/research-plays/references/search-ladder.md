# The search ladder — climb it cheap-first, never open at the top

6. **Search cheap-first — climb the ladder, never open at the top.** Any play that searches
   starts on the cheapest rung that answers the question: `/v1/{platform}/search` (**1cr on the
   social platforms, 5cr on the retail ones** — `ebay`, `home_depot`, `walmart`, `wayfair`; and
   `threads/search` is metered **1–7cr**) when the platform is known. ⚠️ **Four platforms have no
   `{platform}/search` at all, so there is no 1cr rung to climb to:** LinkedIn's cheapest content
   search is `linkedin/search/posts` at **5cr** (`/people` and `/jobs` are **10cr**; the 1cr
   `/industry`, `/location`, `/schools` are id resolvers, not search), X/Twitter's only option is
   `twitter/ai-search` at **5cr**, Facebook has no general content search (only the narrow
   `events/search` and `marketplace/search` at 1cr, plus `adlibrary/search/*` at 5cr), and
   Snapchat has no search at all. Check the platform before quoting a floor ·
   `/v1/reddit/omni-search` (**5–8cr+**, metered: 1cr per search page + 1cr per expanded
   thread, min 5) for all of Reddit with top comments inline ·
   `/v1/search/news` (**~7cr**, metered: base fee + 1cr per leg that returns articles) for
   news · `/v1/search/forums` (**10cr flat**) for Reddit + Hacker News + Naver together ·
   `/v1/search/everywhere` (**20cr flat**) only for a true cross-platform sweep (14 platforms, up to 17 sources). A request that
   merely *sounds* broad is not a reason to escalate — "what are people saying about X on
   Reddit" is a single-platform question, and the per-platform `search` at 1cr is the rung
   that answers it.

> **Before booking the 20cr sweep, climb the search ladder.** Most voice-of-customer questions
> are answered a rung or two lower — but the bottom rung's price varies by platform and the two
> middle rungs are metered, so quote the range. Only the top two are flat:
>
> | Scope of the question | Endpoint | Credits | What drives it |
> |----------------------|----------|---------|----------------|
> | One platform (named or implied) | `/v1/{platform}/search` | **1–7** | 1cr on the social platforms · 5cr retail (`ebay`, `home_depot`, `walmart`, `wayfair`) · `threads/search` metered 1–7 |
> | All of Reddit, top comments inline | `/v1/reddit/omni-search` | **5–8+** | 1cr/search page + 1cr/expanded thread, min 5 |
> | News across the web | `/v1/search/news` | **~7** | base fee + 1cr/leg returning articles |
> | Discussion sites together (Reddit + Hacker News + Naver) | `/v1/search/forums` | **10** | flat |
> | A true cross-platform sweep (up to 17 sources) | `/v1/search/everywhere` | **20** | flat; auto-refunds if every source fails |
>
> `search/forums` is the missing middle rung — reach for it when the question spans discussion
> sites but does not need Instagram/TikTok/YouTube in the mix. Only pay 20cr when you actually
> want the planned, fused, reranked cross-platform result.

**The ladder inside a package row.** Each row in [packages.json](packages.json) is this ladder
for one kind of ask: its `free` path, when it has one, is the bottom rung and its paid `options`
sit above it. Start on the free rung; step up to a paid option only when the free one cannot answer.
