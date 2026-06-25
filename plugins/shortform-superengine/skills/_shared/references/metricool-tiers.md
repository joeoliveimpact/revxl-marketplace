# Metricool tiers — capability + limits reference

> The system reads this when wiring a coach's Metricool connection: detect what their tier allows, and **warn them about limits before they hit a wall**. Pricing/limits current as of **June 2026** — re-verify periodically (Metricool changes plans).

## The one rule that gates everything

**API + MCP + Zapier access = Advanced plan or higher.** Free and Starter have **no API**.

- **Automated** scheduling / publishing / competitor-add / analytics pull *via the plugin* → requires the coach on **Advanced** (~€43/mo annual · ~$53/mo · up to 15 brands).
- **Free / Starter** coaches → the plugin can still **READ analytics via the proven web-session method** (read-only), and the coach can schedule + add competitors **manually** in Metricool — but the plugin cannot drive Metricool's API for them.

## Tier table

| | Free (forever) | Starter (~€16–20/mo) | Advanced (~€43–54/mo) | Custom |
|---|---|---|---|---|
| Brands | 1 | 5 or 10 | up to 15 | 50+ |
| Scheduling | 20 posts/mo · all nets **except LinkedIn + X** | Unlimited (fair-use) | Unlimited (fair-use) | Unlimited |
| Analytics history | 30 days | Full | Full | Full |
| Competitors tracked | 5 profiles (**FB/IG/Bluesky/Twitch only** — no YT/X) | 5 per brand | 25 per brand | Custom |
| API / MCP / Zapier | ❌ | ❌ | ✅ | ✅ |
| Looker Studio · team · approvals | ❌ | ❌ | ✅ | ✅ |

## Cross-cutting limits

- **X/Twitter** is in no plan by default — paid add-on (~€5 per connected premium account).
- **YouTube competitor tracking** — paid only, **max 10**.
- **Competitor post history** — Premium syncs up to 300 posts at connect, then last 100 posts / 30 days ongoing.
- "Unlimited" scheduling is subject to Metricool's Fair Use Policy.

## How the plugin adapts per tier (decision logic)

1. **Detect/ask the coach's tier** at onboarding.
2. **Advanced+** → offer full: auto-schedule, auto-measure, auto-promote competitors (API/MCP). Cap competitor-promote suggestions at **25/brand** (10 for YouTube).
3. **Starter** → measure (web-session read) + plan-only calendar; competitor tracking manual (5/brand); warn: *"auto-schedule + competitor-add need Advanced (API)."*
4. **Free** → measure (web-session read, 30-day history) + plan-only calendar; warn: *"20 posts/mo, no LinkedIn/X scheduling, 5 competitors (FB/IG/Bluesky/Twitch), no API — upgrade to Advanced for automation."*

## Sources

- https://metricool.com/pricing/
- https://help.metricool.com/en/article/competitor-analysis-1vs9jxy/
- 2026 pricing roundups (CheckThat.ai, socialk.it, costbench) — re-verify; plans change.
