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
| `socialcrawl` | The full API canon: key resolution, response envelope, credit gates, the priced transcript gate, cheat codes (free URL dispatcher, batch stats billed per URL), and 68 generated platform references with **exact credits per endpoint**. |
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
- A silent, hard session limit: the guard counts each paid call's worst case and never asks.
  A call that would take the session past the limit is denied, and so is any command carrying
  a SocialCrawl URL that isn't a plain `curl`, such as a loop, a script or a note. The limit is
  your session budget if you set one, else the smaller of 500 credits and 25% of your balance,
  else 500 when the balance can't be read; the same limit holds for every session, Desktop routine
  and `claude -p` run ([credit-guard.md](skills/_shared/references/credit-guard.md)).
- The 15–50-credit research reports ("big guns") always get a balance check + named
  price — one call, never batched.
- Transcript endpoints work, and they are **priced and gated**: Claude quotes the per-unit
  price (3cr per YouTube video, ~10cr per item elsewhere) and the
  cheaper route (YouTube captions at 1cr; elsewhere the media URL at 1–5cr plus free
  local transcription). They run only on your explicit yes; the guard counts them.
- **What it needs.** The band and the Budget tab are a mod, so they need Claude Code 2.1.286 or later with mods on. Without them the guard still keeps every session within the automatic limit, or within a budget file already set. The guard reads calls made in the Bash tool, which on Windows needs Git for Windows; a SocialCrawl call through PowerShell is denied.
- **What it covers.** The guard counts the SocialCrawl calls Claude makes as commands. A plugin script that calls SocialCrawl inside itself (shortform-superengine's Goldmine fetch, until shortform 0.7.0) isn't seen. The guard refuses Claude's own Bash, PowerShell and file-tool changes to the budget and the guard's record files when a command or path names them; a glob, a `cd` into the folder followed by a bare file name, a path built at runtime, an 8.3 short name in a command, another spelling of `SC_REVXL_HOME`, a script Claude writes, a name split up with shell quoting, or another plugin can still get past it.
- **The mod.** With mods on, a band above the prompt shows this session's spending, with three buttons: Budget (d), Endpoints (p) and Round-up (r). Endpoints opens one-click calls and every research play, each priced; its Suggested button sends Haiku your brand's business-config.md, your last five prompts and this session's call paths, and shows the few buttons it picks. The status line shows your total balance, and a toast follows each counted call. The [CHANGELOG](CHANGELOG.md) has the full list.

## License

MIT — see [LICENSE](LICENSE).
