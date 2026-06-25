# Competitor Cross-Reference — Niche Seed Strategy

## Overview

SocialCrawl's `search/reels` endpoint returns reels, not profiles. You derive competitor candidates from the accounts that keep appearing in relevant reel results, then pull real follower counts via the profile endpoint to tier them. This document covers how to build the seed query set that surfaces the right candidates.

---

## Two-Band Seed Strategy

Run discovery in TWO bands. Using only broad terms consistently over-surfaces large off-niche accounts (hospitals, celebrity doctors, generic wellness media) and under-surfaces the small dedicated coaches who are often the most useful benchmarks.

### Band A — Broad Niche Terms
The condition, topic, or audience descriptor at the category level.
- Purpose: surfaces large-to-mid accounts, establishes the competitive ceiling.
- Examples for a thyroid-metabolic-health niche: `thyroid health`, `hormonal imbalance`, `gut health`, `stress cortisol`, `nervous system healing`
- Expect noise: big media accounts, hospitals, product brands will appear — filter them out (see below).

### Band B — Niche-Specific Terms
Method names, modality labels, practitioner frameworks, and community vocabulary that only dedicated niche creators use.
- Purpose: surfaces small dedicated coaches who outperform on reach efficiency — often the most instructive comparators.
- Examples for the same niche: `HTMA minerals`, `root cause healing`, `nervous system reset`, `somatic healing coach`, `pro-metabolic`, `functional nutrition coach`, `hair tissue mineral analysis`
- Rule of thumb: if the term would appear on a practitioner's bio but NOT on a hospital homepage, it belongs in Band B.

---

## Relevance Filter Heuristics

After collecting candidates, DROP accounts that match any of the following:

| Drop condition | Reason |
|---|---|
| Hospitals, clinics, academic medical centers | Off-niche scale; institutional tone; algorithm behaves differently |
| Celebrity doctors / mass-media personalities | Reach driven by celebrity, not content strategy — not a useful benchmark |
| Generic wellness broadcasters (health magazines, news accounts) | No specialization; engagement patterns don't transfer |
| Industry associations / non-profits | Institutional, not creator-driven |
| Device, supplement, or product brands | Commercial algorithm boost; not peer creators |
| Off-geography or off-language accounts | Audience and algorithm context differ |
| Plastic surgery / aesthetics accounts | Different niche, different audience intent |

KEEP: individual coaches, practitioners, educators, and creators in the client's actual lane — same audience pain, same content medium (reels), similar positioning tier.

---

## Candidate Tiering

SocialCrawl `search/reels` returns view counts, not follower counts. After collecting candidates:

1. Pull each candidate's profile via SocialCrawl to get real follower counts.
2. Tier relative to the CLIENT's follower count (not absolute thresholds):
   - **LARGE:** ≥ 3× client followers
   - **MED:** 0.5×–3× client followers
   - **SMALL:** < 0.5× client followers

Default competitor set size: **25 accounts** — target **8 LARGE / 9 MED / 8 SMALL**.

Rationale: small-tier accounts are often the best reach-efficiency benchmarks (they're growing fast in the niche); large-tier shows the content ceiling; med-tier shows the achievable near-term benchmark.

---

## Human Approval Gate

**Do not run the big reel pull until the human approves the competitor set.**

Present the 25 candidates as a tiered list (LARGE / MED / SMALL) with: handle · follower count · one-line description of their angle. Ask the client to confirm, swap, or drop accounts before proceeding. The reel pull is expensive in API credits — don't waste it on accounts the client will reject.

---

## Pagination Note

SocialCrawl IG profile/reels paginates via `&max_id=<next_cursor>`. Do NOT use `cursor`, `pagination_token`, or `after` — they silently return page 1. Check for a `next_cursor` field in each response and loop until exhausted or your per-account reel cap is hit.

---

*Reference: derived from a production baseline run (25-competitor set, ~900 reels across 3 tiers).*
