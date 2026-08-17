# SocialCrawl Superengine

Deep social research engine on the [SocialCrawl](https://www.socialcrawl.dev) API — the
full **48-platform / 381-endpoint** canon with exact per-call credit costs, plus guided
research plays that turn raw endpoints into finished research artifacts.

Runs standalone, and pairs with the RevXL format engines (shortform-superengine etc.):
when this plugin is installed, they detect it and offer its deep plays from inside their
own workflows. They never require it — their bundled lean core covers their day-to-day
calls.

## Skills

| Skill | What it does |
|-------|--------------|
| `socialcrawl` | The full API canon: key resolution, response envelope, credit gates, the ⛔ transcript ban, cheat codes (free URL dispatcher, 1-credit batch stats), and 43 generated platform references with **exact credits per endpoint**. |
| `research-plays` | Guided workflows: voice-of-customer mining, competitor ad-library recon, AI-visibility (GEO) audits, link-in-bio offer mapping, TikTok audience demographics, dev/tool radar — plus hard-gated big-gun one-shots (creator vetting, lead discovery, share of voice, reputation reports). |
| `onboarding` | One-time setup: bring-your-own API key (guided signup if needed), a 1-credit verify, a plain-English credit-policy briefing, and the detection marker other engines look for. |

## Setup

1. Install the plugin, then say **"set up socialcrawl"**.
2. Bring your own SocialCrawl API key (accounts start with 100 free credits) — the
   onboarding skill walks the signup if you don't have one.
3. Done. Ask for data ("get @handle's reels") or outcomes ("what are people saying
   about X", "what ads is <competitor> running").

Your key, your data, your credits — nothing routes through anyone else's account.

## Credit discipline (built in)

- Most calls cost 1 credit; the skill states costs before anything at 5+.
- 10+ credit calls require an explicit yes, every time, never in a loop.
- The 15–50-credit research reports ("big guns") always get a balance check + named
  price + confirmation — one call, never batched.
- Transcript endpoints are **banned outright** — transcription happens free on your
  machine (captions → Groq → local Whisper), never on your credit balance.

## License

MIT — see [LICENSE](LICENSE).
