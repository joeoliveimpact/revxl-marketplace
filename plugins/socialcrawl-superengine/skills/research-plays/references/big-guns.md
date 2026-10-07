# Big-gun runbooks — priced one-shot deliverables (see the table)

Most of these are flat-priced. **`share-of-voice` is not** — it meters per brand, and
**`creator-vet`** and **`crisis-radar`** hold a ceiling and refund down. Check the table.

Every play here runs the same way, no exceptions. **The pick is the go; the guard asks only at
a cap step, on a can't-count call, or on a command that isn't a plain `curl`.**

1. `GET /v1/credits/balance` (0cr) — show the balance.
2. Name the exact cost: *"This is a premium one-shot: `<endpoint>` costs **N credits**
   (about $X at your plan's rate)."* — **on a metered play, N is the computed worst case
   for the parameters you are actually sending, not the unit price.**
3. Their pick of that priced option is the explicit yes. A vague "sure, whatever's needed"
   earlier in the conversation does NOT count.
4. One call. **Never batched, never looped, never auto-repeated.** A re-run (new keyword,
   second brand) is a new plan and needs its own pick.
5. After the call, report `credits_used` + `credits_remaining` (null on a cache hit).

Params below are the primary ones — full param lists live in
[../../socialcrawl/references/prism.md](../../socialcrawl/references/prism.md) and
[search.md](../../socialcrawl/references/search.md).

| Play | Endpoint | Credits | Metered? |
|------|----------|---------|----------|
| Audience questions (content-seed engine) | `prism/audience-questions` | **30** | flat |
| Creator vetting (partnership due diligence) | `prism/creator-vet` | **50–75** | held ceiling, refunds down — quote 75 |
| Lead discovery (competitor switchers) | `prism/leads` | **50** | flat |
| Share of voice (2–5 brands) | `prism/share-of-voice` | **80–200** | ⚠️ **40cr _per brand_** (20 web-only); `brands=` takes 2–5, so a real call is 80–200cr, never 40 |
| Reputation report (cross-source) | `prism/reputation` | **30** | flat |
| Campaign tracker (launch lift) | `prism/campaign` | **35** | flat (half-refunds fire; measured 17 on a thin window) |
| Earned-media footprint | `prism/earned-media` | **25** | flat |
| Crisis radar (mention-volume breach check) | `prism/crisis-radar` | **15–45** | held ceiling, refunds down — quote 45 |
| TikTok audience overlap (2 creators) | `prism/audience-overlap` | **20** | flat |
| AI-visibility audit | `prism/ai-visibility` | **20–1,605** | ⚠️ **2cr _per probe_** (`prompt × run × engine`); always pass `preset=` |
| Universal search (up to 17 sources) | `search/everywhere` | **20** | flat |

---

## Audience questions — `prism/audience-questions` · 30cr · [C]

**Worth it when:** onboarding a new client niche or a quarterly content refresh — you want
the real questions the audience asks, not guesses.
**Call:** `GET /v1/prism/audience-questions?topic=<niche topic>`
**You get:** questions harvested from Reddit + YouTube threads, clustered by intent
(who / what / why / how / vs).
**Deliverable:** content-seed bank — each cluster becomes a content pillar; the verbatim
questions become hooks. Feeds a brand-brain topics shelf directly.
**Cadence:** once per niche per quarter. Between runs, `reddit/omni-search` covers
incremental mining — cheaper, but **not 1cr**: it is metered at 1cr per search page + 1cr
per expanded thread with a floor of 5, so budget **5–8cr+ per keyword**.

## Creator vetting — `prism/creator-vet` · 50–75cr, quote 75 · [J]

**Worth it when:** real money or brand risk rides on a creator — a partnership, a paid
collab, a high-ticket enrollment. The most expensive call in the API; treat it like a
background check, not a curiosity.
**Call:** `GET /v1/prism/creator-vet?handle=<handle>`
**You get:** engagement quality, commenter authenticity (bot share), posting cadence, and
controversy signals — optionally across platforms.
**Deliverable:** go / no-go one-pager with the three strongest signals quoted.
**Cheaper first pass:** `prism/handle-audit` (5cr) + `prism/creator-card` (5cr) answer
"is this account worth anything" for a fraction of the price — reserve creator-vet for the final
check on a shortlist of one.

## Lead discovery — `prism/leads` · 50cr · [J]

**Worth it when:** one qualified lead is worth far more than the call cost — high-ticket
offers hunting people actively unhappy with a named competitor.
**Call:** `GET /v1/prism/leads?competitor=<brand/product>`
**You get:** a ranked feed of public conversations where people seek alternatives to, or
are switching from, that competitor.
**Deliverable:** lead list — conversation URL, platform, verbatim pain quote, suggested
opening line each. Route into the outreach pipeline the same day; these conversations
go stale in days, not weeks.

## Share of voice — `prism/share-of-voice` · **80–200cr (metered per brand)** · [C]

**Worth it when:** a competitive-audit deliverable needs the headline number — who owns
the conversation in this niche?
**Call:** `GET /v1/prism/share-of-voice?brands=<2-5 brands CSV>`
⚠️ **Cost is 40cr PER BRAND, not 40cr per call** (20cr/brand if you restrict it to web-only).
`brands=` accepts 2–5, so the real range is **80–200cr** — the single most expensive call
this plugin can make. **Count the brands, multiply, and name that number in the gate.**
Measured live: 40cr at one brand.
**You get:** engagement-weighted SoV with web + social split, emotion overlay, and excess
share of voice (ESOV).
**Deliverable:** the flagship page of a competitive audit — SoV pie + "where the gap is"
paragraph. One call per audit; the brand list is fixed at call time, so agree it first —
adding a brand after the fact costs another 40.

## Reputation report — `prism/reputation` · 30cr · [C]

**Worth it when:** a local-biz or product client wants the outside view — what does the
internet collectively say?
**Call:** `GET /v1/prism/reputation?brand=<name>`
**You get:** Trustpilot + app stores + Google Business + web sentiment blended into one
weighted score with themed pros/cons.
**Deliverable:** reputation snapshot — the score, top 3 praise themes, top 3 complaint
themes (each = a content/ops fix), and the single worst-source callout.

## Campaign tracker — `prism/campaign` · 35cr · [C]

**Worth it when:** measuring how a launch actually landed (hashtag or campaign phrase),
pre/during/post.
**Call:** `GET /v1/prism/campaign?query=<hashtag or phrase>`
**You get:** volume lift across the window, cross-platform engagement, ranked top
amplifiers.
**Deliverable:** launch post-mortem — lift chart numbers, the 5 amplifiers to thank/DM,
and one "do differently next launch" line. Run once post-launch, not during.

## Earned media — `prism/earned-media` · 25cr · [C]

**Worth it when:** an authority audit for a personal brand — where do they get cited?
**Call:** `GET /v1/prism/earned-media?brand=<name>`
**You get:** news + tech-press + fresh-web clips, deduped and ranked, outlet-coverage
rollup.
**Deliverable:** press footprint page — coverage list + the two outlets that already know
them (warm pitch targets).

## Crisis radar — `prism/crisis-radar` · 15–45cr, quote 45 · [C]

**Worth it when:** on-demand "is something blowing up?" check — a client saw a nasty
comment thread and wants to know if it's spreading.
**Call:** `GET /v1/prism/crisis-radar?brand=<name>`
**You get:** a stateless z-score on daily mention volume + negative share, with a severity
grade on breach.
**Deliverable:** one-line verdict ("normal noise" vs "elevated — here's the source") +
the volume numbers. NOT a monitoring loop — one check per incident; standing monitoring
is a different tool.

## TikTok audience overlap — `prism/audience-overlap` · 20cr · [C]

**Worth it when:** validating a competitor set for a TikTok-first client — do these two
creators actually share an audience?
**Call:** `GET /v1/prism/audience-overlap?handle_a=<a>&handle_b=<b>`
**You get:** commenter-audience Jaccard overlap, shared-fan count, confidence label.
**Deliverable:** competitor-set validation note — keep/cut verdict per candidate pair.
Pairs are chosen before calling; 3 pairs = 60cr = a conversation, not a default.

## Universal search (up to 17 sources) — `search/everywhere` · 20cr · [CJ]

**Worth it when:** scouting a NEW topic/niche once — "where does this conversation even
live?" Fourteen platforms (up to 17 sources), one ranked + clustered result.
**Call:** `GET /v1/search/everywhere?query=<topic>` (sync JSON or SSE — see
[search.md](../../socialcrawl/references/search.md); auto-refunds if every source fails).
**Deliverable:** platform map — which 2–3 platforms own this topic. Then leave this
endpoint alone and search those platforms at 1cr each.
