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
| `socialcrawl` | The full API canon: key resolution, response envelope, credit gates, the priced transcript gate, cheat codes (a 1–5-credit URL dispatcher, batch stats billed per URL), and 68 generated platform references with **exact credits per endpoint**. |
| `research-plays` | Guided workflows: voice-of-customer mining, competitor ad-library recon, AI-visibility (GEO) audits, link-in-bio offer mapping, TikTok audience demographics, dev/tool radar — plus priced big-gun one-shots (creator vetting, lead discovery, share of voice, reputation reports). |
| `onboarding` | One-time setup: bring-your-own API key (guided signup if needed), a 1-credit verify, a plain-English credit-policy briefing, and the detection marker other engines look for. |

## Setup

1. Install `socialcrawl-superengine` from the `revxl-marketplace` plugin marketplace (or ask
   Claude to install `socialcrawl-superengine@revxl-marketplace` for you), then say
   **"set up socialcrawl"**.
2. Bring your own SocialCrawl API key (accounts start with 100 free credits) — the
   onboarding skill walks the signup if you don't have one.
3. Done. Ask for data ("get @handle's reels") or outcomes ("what are people saying
   about X", "what ads is <competitor> running").

Your key, your data, your credits — nothing routes through anyone else's account.

## Credit discipline (built in)

- Prices are stated before a run, and the option you pick is the go-ahead.
- A silent session limit, as the guard counts it. Before a paid call runs, the guard holds the
  highest price it can count for it (that hold is what the session counts for the call), and it never asks.
  Credits come back later: when SocialCrawl's free ledger shows a charge on that endpoint, made while a call
  to it was open and that call finished cleanly, the guard swaps the endpoint's finished holds for what was
  charged (see the limits below). A few calls it can't price up front are counted at 0, and the limit does
  not stop them, even once it is used up: `POST prism/jobs`, `POST web/batch-scrape`, `POST web/monitors`
  (its checks bill later, unseen), the cohort calls, and the `/v1/monitors` calls (free to make, but each scheduled run then bills the recipe's price plus 1, unseen). A transcript call is counted at one unit's price,
  so one that bills many units is counted low. A call that would take the session past the limit is denied, and so is any command carrying
  a SocialCrawl URL that isn't a plain `curl`, such as a loop, a script or a note. The limit is
  your own limit if you set one in SocialCrawl → Settings, else the smaller of 500 credits and 25% of your balance,
  else 500 when the balance can't be read; the same limit holds for every session, Desktop routine
  and `claude -p` run ([credit-guard.md](skills/_shared/references/credit-guard.md)).
- The research reports ("big guns", up to 243 credits a call (`prism/comment-leads`); a full AI-visibility audit up to 1,605)
  always get a balance check + named price — one call, never batched.
- Transcript endpoints work, and they are **priced and gated**: Claude quotes the per-unit
  price (3cr per YouTube video, ~10cr per item elsewhere) and the
  cheaper route (YouTube captions at 1cr; elsewhere the media URL at 1–5cr plus free
  local transcription). Claude asks first and runs one only on your yes; Blocked makes the guard
  enforce it. In SocialCrawl → Settings you can
  block them: the guard then refuses the transcript calls it knows (the `*/transcript`
  endpoints, `POST youtube/transcripts`, `include=transcript` on any call such as
  `prism/video-intel`, `search/everywhere` with `include_transcripts`, `facebook/post` with
  `get_transcript`, and `prism/brief-check`). It catches the known spellings: a command with odd
  URL encoding is refused as not plain, and a spelling it doesn't know can get past the lock, where it
  is counted at that call's ordinary price, which can be lower than the transcript price. Until you save a choice they run, and are counted.
- **What it needs.** The band and the SocialCrawl pane are a mod, so they need Claude Code 2.1.286 or later with mods on. Without them the guard still holds every session to the automatic limit, or to a budget file already set, as it counts it (the calls it counts at 0, above, are not stopped). The guard reads calls made in the Bash tool, which on Windows needs Git for Windows; a SocialCrawl call through PowerShell is denied.
- **What it covers.** The guard counts the SocialCrawl calls Claude makes as commands. A plugin script that calls SocialCrawl inside itself (shortform-superengine's Goldmine fetch, until shortform 0.7.0) isn't seen. The guard refuses Claude's own Bash, PowerShell and file-tool changes to the budget and the guard's record files when a command or path names them; a glob, a `cd` into the folder followed by a bare file name, a path built at runtime, an 8.3 short name in a command, another spelling of `SC_REVXL_HOME`, a script Claude writes, a name spelled in a disguised shell form (ANSI-C quoting, brace expansion and the like), a link or junction to the folder, an MCP tool, or another plugin can still get past it. The same goes for Save: the guard refuses Claude running Save in any plain form; a deliberately disguised command is not caught. If the guard itself hits an error with you at the prompt, a command that mentions transcripts is refused, but any other call passes uncounted (Claude Code's own permission settings still apply); with nobody there, or in a routine, it is refused.
- **The mod.** With mods on, a band above the prompt shows this session's credits: what is left of your limit (or, before a limit is known, what has been counted so far) and Usage, what SocialCrawl's ledger shows was charged. Its one button, **Open SocialCrawl** (hotkey d), opens a pane with five tabs: Endpoints (one-click calls, each priced), Combos (priced research plays), Suggested (a few picks from your brand notes, your last few prompts and this session's calls; after you first open it, each refresh is one small model call), Round-up (this session's calls) and Settings (your session credit limit and the transcript setting). The status line shows your total balance, and a toast follows each counted call. The [CHANGELOG](CHANGELOG.md) has the full list.
- **When credits come back.** Credits the guard held for a call come back about two minutes after the call returns, at the earliest, and only once the ledger shows a charge on that endpoint this session: a call with no charge there (a cache hit, a free not-found answer, a transcript with no captions) keeps its hold until one appears. Until then the band can read high. A call that fails, is interrupted, runs in the background, or is piped or chained keeps its hold, and can count its hold and its charge together for the rest of the session. Nothing comes back without a key, or after three failed ledger reads in a row. Other spending on your account, on the same endpoint while a call is open, counts against the session, and a charge the vendor records more than about 2 minutes after its call returns can be counted late, or not at all.

## License

MIT — see [LICENSE](LICENSE).
