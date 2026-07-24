---
name: meta-ads-superengine:meta-ads-competitor-intel
description: Builds and scans the coach's competitor roster from Meta's Ad Library — writes a tracked roster, seeds ad observations, and renders the longevity ladder (30d good / 60d great / 6mo-plus must-study) plus niche angle candidates that feed the creative matrix. Only offered after the coach's own creative strategy exists. Trigger phrases include "competitor ads", "spy on competitors", "what ads are running in my niche", "ad library check".
---

# meta-ads-competitor-intel — roster builder + first scan

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #19.
Intel is seasoning, not foundation — it feeds a PDA matrix that already
exists; it never replaces one. This skill BUILDS the roster and takes the
first scan; the weekly delta lives in `meta-ads-competitor-pulse`.

## Load
- shared refs
- Active brand state → `creatives` (the PDA gate), `setup.offer` (niche),
  `competitors` (existing roster, if any)
- Meta MCP connected? (`ads_library_search` available — the scan tool)
- shortform-superengine marker + `analysis-config.json` (detect-first, for a
  seed roster — mirror best-content's reuse-first detect)
- SocialCrawl key: env → `~/.config/socialcrawl/api_key` (optional)

## Prereq — THE PDA GATE (E0)
`creative-strategy` completed (concept rows exist). Missing → refuse + route:
*"Competitor intel calibrates YOUR angles — without your own matrix it just
produces copycat ads. Creative strategy first."* → Say: "creative strategy".

## Empirical reality (locked — from live Ad Library probes)
`ads_library_search` returns per ad ONLY: `id`, `page_id`/`page_name`,
`ad_creative_link_title` (the one piece of creative text), `ad_creation_time`,
`ad_delivery_start_time` (the **longevity anchor**), `ad_snapshot_url`,
`currency`. No creative body, no video duration, no stop time. No pagination,
no date filter, no sort — results are newest-first by creation time. So:
- **Run-length = today − `ad_delivery_start_time` on a STILL-ACTIVE ad = proven
  spend.** That single field is the whole ladder.
- The ACTIVE bucket per page is small (usually <50 → fully retrievable in one
  `limit: 50` pull). Status counts (total / active / retired) are an intensity
  proxy.
- Raw term-search is noisy (spam pages, wrong markets mixed in) → the
  **relevance post-filter is mandatory** (below).
- Competitor `ad_snapshot_url` is **403 anonymously** — the full creative
  teardown needs a logged-in browser surface (Tier 2 below), never a raw fetch.

## Steps

**1. The scan tool — `ads_library_search` when the Meta MCP is connected.**
Page_ids-scoped per roster competitor is the reliable path (each page = its
full running back-catalog). Term-search is for DISCOVERY only, and every
term-search result runs the **mandatory relevance post-filter**: drop pages
whose `page_name`/`ad_creative_link_title` aren't in the niche; drop
wrong-market currencies (non-USD unless the coach says they run
international). **Unconnected path (first-class, honest ... manual paste
capture):** the coach browses the Meta Ad Library by hand and pastes what the
UI shows; I file it into the same observation rows the connected scan writes.
Per roster competitor: paste the page's Ad Library URL (I extract the `page_id`
from its `view_all_page_id=` parameter). Then for each NOTABLE ad (long-runners
first, plus recurring angles): paste the **Library ID** (= the ad id), the
**"Started running on"** date (= `delivery_start`), and the headline
(= `link_title`). Honest scope: this captures the ads you choose to log, not
the full catalog ... the longevity ladder renders over the captured ads and is
labeled **"partial (manual capture)"**; connected mode pulls and watches the
whole catalog automatically. Never gate the skill on the MCP.

**2. Build the roster (target 3–8 pages — ad rosters are smaller than organic
because each page exposes a full back-catalog; say why).**
- **Seed offer (detect-first):** if shortform's competitor roster exists
  (marker + `analysis-config.json`), offer to seed the matching handles —
  resolve each handle/name to a `page_id` via a library term-search on it;
  unresolvable → note it, skip it, never guess.
- **Manual adds:** the coach names competitors → resolve each to a `page_id`
  the same way (connected), or read it from the pasted Ad Library URL's
  `view_all_page_id=` when unconnected (the manual-capture path above). The
  `"manual"` source tag already covers hand-added rows.
- Write the confirmed set to `competitors[]` (rows `{page_id, page_name,
  added_at, source}` — `source`: `"manual"` | `"shortform-seed"` |
  `"library-search"`).

**3. First scan, per roster page:** connected → ACTIVE pull (`limit: 50`) +
status counts; unconnected → the manual-capture rows the coach pasted (Step 1).
Either way, **seed `ad-observations.json`** (one row per ad: `ad_id`, `page_id`,
`delivery_start`, `link_title`, `first_seen`=today, `last_seen`=today,
`status_at_last_seen`, `tier`, `teardown_artifact`=null ... on the manual lane
`status_at_last_seen`=`active` for an ad the Library shows as live, `tier`
derives from `delivery_start`, and any field the UI doesn't expose stays
`null`, never guessed) → render the
**longevity ladder table** (per page: active count, total ever, oldest-active
run-length, tier flags ... labeled **"partial (manual capture)"** on the
unconnected lane) → pull **top angle candidates** from
`ad_creative_link_title`, each mapped to a PDA cell (validate / contradict /
add). Guardrails ARE the analysis: mine ANGLES and hooks, never structure;
model brands 1–2 steps bigger, **never clone 8-figure brands** (their ads work
because of their brand, not their copy).

### The tier ladder (label corpus vs house every time)
- **30d = good** — a month of consistent spend (Cockpit: a 4-week run is a
  winning-hook signal). *Corpus-backed.*
- **60d = great** — house heuristic, interpolated. *Label it as house.*
- **6mo+ = MUST-STUDY, proven spend** — staged-framework canon. *Corpus-backed.*

Computed from `delivery_start` on ACTIVE ads. Observed run (a later pulse
seeing `first_seen`→`last_seen` both ACTIVE) corroborates it over time.

**4. Tier-2 teardown offer (✋ EFFORT gate — consent, not credits).**
Nominate ads already ≥6mo (and notable 30/60d newcomers). The gate is work,
not spend: *"Each teardown = opening the ad in your logged-in browser + a
structured read of video length, caption, layout, script framework — worth it
for the N nominated ads?"* On yes, per ad: the coach (or Claude with browser
access) opens `ad_snapshot_url` → a structured teardown (duration / caption
structure / visual layout / script framework / offer-angle) → record the
`teardown_artifact` path on that observation row. SocialCrawl enrichment stays
optional and ✋ credit-gated — no longer the depth path, just an add-on.

**5. Write** `competitors[]` + seeded `ad-observations.json`; open_loop "feed
intel to creative-strategy".

> Your OWN ads are a different job: pulling your creative body/title/CTA,
> video length, and rendered preview is MCP-native and lives in
> best-content / creative-test — not here.

## Terminal paths — inline blocks (routing.md grammar)

**Intel delivered (E19):** preamble = the roster written + the ladder table +
top angles and what they validate/add in the matrix, then:

**Next moves**
1. Fold this into your creative plan — the matrix gets the new angles. Say: "creative strategy"  ← start here
2. *If a proven competitor angle maps to an unproduced concept:* produce it now. Say: "<the format's trigger>"
3. Track this roster over time — weekly, I flag new ads, disappearances, and longevity promotions. Say: "competitor pulse"
4. Check your own winners against the field. Say: "mine my winners"

**Next moves — teardown declined (✋ effort)**
1. Skip the teardowns — the ladder + angles are already in hand. Say: "creative strategy"
2. Park them — I'll re-offer only if you ask.

**Next moves — credit checkpoint declined (✋)**
1. Proceed on the free Ad Library findings alone — already in hand. Say: "creative strategy"
2. Park the enrichment — re-offer only if you ask.

## Teach mode
In `new`: plain-English-first — Ad Library deep-glossed ("Meta's public
archive of every running ad — free"); the longevity ladder explained ("an ad
running 6 months is spending money on purpose — that's proof it works"), each
tier labeled corpus vs house; the never-clone rule gets "what this means for
you." In `learning`: gloss Ad Library first use, one-liner tiers. In `pro`:
roster + ladder table + matrix mapping, terse.

## Guardrails
- The PDA gate is hard — never before the coach's own matrix exists.
- ✋ before ANY credit spend (SocialCrawl), cost named, offer-once (declined →
  not re-offered this session). The teardown ✋ is EFFORT, not credits.
- Relevance post-filter is mandatory on every term-search.
- No Brain step (this skill mines the MARKET, not the vault).
- Findings are angle candidates, never scripts to copy. Competitor snapshot
  URLs are browser-gated (403 anonymously) — never claim a teardown from a raw
  fetch.
