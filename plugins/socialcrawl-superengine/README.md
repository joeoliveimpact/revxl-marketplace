# SocialCrawl Superengine

Deep social research engine on the [SocialCrawl](https://www.socialcrawl.dev/?ref=AQNU384G) API — the
full canon — **645 endpoints across 68 platform namespaces** — with exact per-call credit costs, plus guided
research plays that turn raw endpoints into finished research artifacts.

Runs standalone, and pairs with the RevXL format engines (shortform-superengine etc.):
when this plugin is installed, they detect it and offer its deep plays from inside their
own workflows. They never require it — their bundled lean core covers their day-to-day
calls.

## Skills

| Skill | What it does |
|-------|--------------|
| `socialcrawl` | The full API canon: key resolution, response envelope, credit gates, the priced transcript gate, cheat codes (free URL dispatcher, 1-credit batch stats), and 43 generated platform references with **exact credits per endpoint**. |
| `research-plays` | Guided workflows: voice-of-customer mining, competitor ad-library recon, AI-visibility (GEO) audits, link-in-bio offer mapping, TikTok audience demographics, dev/tool radar — plus priced big-gun one-shots (creator vetting, lead discovery, share of voice, reputation reports). |
| `onboarding` | One-time setup: bring-your-own API key (guided signup if needed), a 1-credit verify, a plain-English credit-policy briefing, and the detection marker other engines look for. |

## Setup

1. Install the plugin, then say **"set up socialcrawl"**.
2. Bring your own SocialCrawl API key (accounts start with 100 free credits) — the
   onboarding skill walks the signup if you don't have one.
3. Done. Ask for data ("get @handle's reels") or outcomes ("what are people saying
   about X", "what ads is <competitor> running").

Your key, your data, your credits — nothing routes through anyone else's account.

## Credit discipline (built in)

- Prices are stated before a run, and the option you pick is the go-ahead.
- A silent session cap: the guard counts each paid call's worst case and asks once each
  time the session's total crosses a step of min(500 credits, 25% of your balance), before
  any call it can't count up front, and on any command carrying a SocialCrawl URL that isn't
  a plain `curl`, such as a loop, a script or a note.
- The 15–50-credit research reports ("big guns") always get a balance check + named
  price — one call, never batched.
- Transcript endpoints work, and they are **priced and gated**: the guard pauses and asks,
  quoting the per-unit price (3cr per YouTube video, ~10cr per item elsewhere) and the
  cheaper route (YouTube captions at 1cr; elsewhere the media URL at 1–5cr plus free
  local transcription). They run only on your explicit yes.

## License

MIT — see [LICENSE](LICENSE).
