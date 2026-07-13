---
name: lm-setup
description: Guided installer for the lead-magnet engine's optional capability upgrades (search, transcription, social, PDF extras). Explains each upgrade in plain English, detects what's actually live on the system, health-checks connections, and writes results to the user's profile. Trigger when the user says "set up lead magnet upgrades", "connect research sources", or runs /lm-setup.
---

# `/lm-setup` — Guided Installer for Lead-Magnet Upgrades

This skill walks through each of the five capability upgrades that power the lead-magnet build pipeline. For each one it explains what the upgrade adds and why, detects whether it's live on your system, health-checks the connection, and writes the result back to your profile via `${CLAUDE_PLUGIN_ROOT}/lib/profile.py`.

**Never assume a source is available** — detection runs on every invocation. If something is down or not configured, the skill explains what to do instead of silently failing.

---

## Profile setup

The ACTIVE client profile lives in the plugin's persistent data directory —
`${CLAUDE_PLUGIN_DATA}/profiles/<name>.json` — so it survives plugin updates and
never ships inside the package. The blank template ships at
`${CLAUDE_PLUGIN_ROOT}/profiles/client.blank.json`.

**First run:** if no profile exists under `${CLAUDE_PLUGIN_DATA}/profiles/`, copy
the blank template there (e.g. as `client.json`), then work on the copy.

Load the target profile at skill start:

```python
import os, shutil
from lib import profile as P

DATA = os.environ["CLAUDE_PLUGIN_DATA"]
ROOT = os.environ["CLAUDE_PLUGIN_ROOT"]
active = os.path.join(DATA, "profiles", "client.json")  # or another <name>.json

if not os.path.exists(active):  # first run: seed from the shipped template
    os.makedirs(os.path.dirname(active), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "profiles", "client.blank.json"), active)

prof = P.load_profile(active)
```

After detection and health-checks, use `P.resolve(prof, capability)` to READ-verify each block is accessible (it returns the block dict or None — it does not write anything). Save the updated profile with `P.save_profile(prof, path)` if the user confirms any changes.

---

## Upgrade 1 — Search (`search`) ← START HERE

**What it adds:** Broad, unlimited meta-search across Google and 70+ other engines without API cost. The build pipeline uses this for competitor discovery — who's in the niche and what magnets they offer.

**Why it matters:** Without search, the pipeline has to ask you to name competitors manually. With a SearXNG instance you can reach, it finds them automatically and chains into the rest of the research flow.

**How to enable:** Run (or get access to) a SearXNG instance with `format=json` enabled, then set `"enabled": true` and `"endpoint": "http://<your-searxng-host>:<port>"` in your profile's `search` block. No endpoint configured = capability stays off and the chain degrades gracefully.

**Detection — profile-driven probe:**

```python
from urllib.parse import urlparse
from lib.capability_detect import probe_port, probe_http, detect

ep = prof["upgrades"]["search"].get("endpoint", "")
host, port = (urlparse(ep).hostname, urlparse(ep).port or 80) if ep else (None, None)

probes = {
    "search": lambda: bool(ep) and (
        probe_port(host, port)                   # 1. port reachable
        and probe_http(                          # 2. HTTP health check
            f"{ep}/search?q=test&format=json"
        )
    )
}
results = detect(prof, probes)
```

The `probes` argument is a **dict** mapping capability name → a callable that returns `bool`. `detect()` calls each probe only when the profile has `"enabled": true` for that capability. An empty/absent endpoint means the probe returns `False` — the honest default.

**Health-check URL (primary):**
```
GET <endpoint>/search?q=test&format=json
```
Expect HTTP 200 with a JSON body containing a `results` key. If you get a connection error, check:
1. Is the host reachable from this machine (VPN/tailnet up, DNS resolving)?
2. Is the port in your endpoint actually published by the SearXNG container/service?
3. Does the instance allow `format=json` (bot-limiter off for JSON)?

**On failure:** skip SearXNG in the chain; Tavily (if `ranked` key present) takes over, then the built-in WebSearch floor. The pipeline never hard-fails — it degrades gracefully and tells you which tier it's using.

---

## Upgrade 2 — Scrape (`scrape`)

**What it adds:** Clean text and structure extraction from competitor landing pages, opt-in pages, and ad copy. Powered by Firecrawl, which strips nav/footer noise and returns just the meaningful page content.

**Why it matters:** Raw HTML is messy. Firecrawl gives the pipeline clean copy to analyze — headline structures, offer framing, CTA language — without manual copy-paste.

**How to enable:** Set `FIRECRAWL_API_KEY` in your environment. The profile's `key_env` field tells the pipeline where to look (`"key_env": "FIRECRAWL_API_KEY"`).

**Detection:**

```python
import os
probes["scrape"] = lambda: bool(os.getenv("FIRECRAWL_API_KEY"))
```

**Health-check:** attempt a test scrape of a known public URL. If the key is missing or invalid, Firecrawl calls return 401/403. The pipeline falls back to Playwright scrape (always available) → WebFetch floor.

**Note (Joe's profile):** `scrape` is marked `"enabled": true` as an intended target. Runtime detection resolves the real state — if the key isn't set, this probe returns `False` and the chain uses the Playwright fallback automatically.

---

## Upgrade 3 — Ranked Search (`ranked`)

**What it adds:** Tavily as a ranked fallback search when SearXNG is unreachable. Tavily returns pre-ranked, relevance-scored results, which can be better for niche queries.

**Why it matters:** Optional free-tier safety net. If SearXNG is down or the Tailnet is unavailable, Tavily keeps research moving without asking you to name competitors manually.

**How to enable:** Set `TAVILY_API_KEY` in your environment. Profile `key_env` is `"TAVILY_API_KEY"`.

**Detection:**

```python
import os
probes["ranked"] = lambda: bool(os.getenv("TAVILY_API_KEY"))
```

**Note (Joe's profile):** Currently `"enabled": false` — Tavily is not yet configured. The pipeline will use SearXNG (primary) and the WebSearch floor when SearXNG is down. Enable this when/if you add a Tavily key.

---

## Upgrade 4 — Transcribe (`transcribe`)

**What it adds:** Automatic audio/video transcription for competitor VSLs, webinars, and reels. The pipeline extracts audio via ffmpeg, then sends it to your Whisper server.

**Why it matters:** Video teardowns are one of the highest-signal competitive research moves. Without transcription, you have to watch the whole video and paste key points manually.

**How to enable:** Run a Whisper server (Whisper.cpp, faster-whisper, or any compatible endpoint) and set `"enabled": true` and `"endpoint": "http://<your-whisper-host>:<port>"` in your profile's `transcribe` block. Groq's `whisper-large-v3-turbo` works as an API fallback if you set `GROQ_API_KEY`.

**Detection:**

```python
tep = prof["upgrades"]["transcribe"].get("endpoint", "")
probes["transcribe"] = lambda: bool(tep) and probe_http(f"{tep}/health")
```

**Health-check:** `GET <endpoint>/health` → expect 200. If the endpoint is down or unset, the chain degrades: Groq (if `GROQ_API_KEY` is set) → ask the user to paste the transcript. The pipeline never hard-fails.

---

## Upgrade 5 — Social (`social`)

**What it adds:** Competitor social intelligence — what's performing, which formats, top-engaging posts — via Metricool MCP (named watchlist, deep analytics) and the SocialCrawl skill for broader discovery.

**Why it matters:** Knowing what's working for competitors on social tells you what hooks, formats, and angles resonate with your shared audience — before you spend time creating.

**How to enable:** Metricool MCP must be connected (supports up to 10 brands in the watchlist). No additional env var needed beyond MCP connection.

**Detection:** MCP handshake — the skill checks whether `Metricool` appears in the connected MCP manifest.

```python
# Pseudocode — actual probe checks MCP server list at runtime
probes["social"] = lambda: mcp_connected("metricool")
```

> **Honest default:** `detect()` returns `False` for any enabled capability that has no probe callable supplied — unprobed means unverified, so it never falsely reports "live". Until a live MCP-handshake probe is wired up, an enabled `social` upgrade will show as unavailable and the chain degrades gracefully to its fallback.

**Health-check:** attempt a `get_social_accounts` call; if it returns data, social is live.

> **Framework recall needs no upgrade.** Lead-magnet frameworks, format-by-niche guidance, benchmarks, and anti-patterns ship bundled under `${CLAUDE_PLUGIN_ROOT}/references/` — always available, no external service required.

---

## Detection run (full example)

```python
from lib import profile as P
from lib.capability_detect import detect, probe_port, probe_http
import os

prof = P.load_profile(active)  # ${CLAUDE_PLUGIN_DATA}/profiles/<name>.json — see Profile setup

sep = prof["upgrades"]["search"].get("endpoint", "")
tep = prof["upgrades"]["transcribe"].get("endpoint", "")

probes = {
    "search":     lambda: bool(sep) and probe_http(f"{sep}/search?q=test&format=json"),
    "scrape":     lambda: bool(os.getenv("FIRECRAWL_API_KEY")),
    "ranked":     lambda: bool(os.getenv("TAVILY_API_KEY")),
    "transcribe": lambda: bool(tep) and probe_http(f"{tep}/health"),
    # social: MCP handshake (runtime, not shown here)
}

live = detect(prof, probes)
# live is a dict[str, bool] — True = enabled + probe passed, False = disabled or unreachable
```

After detection, present results to the user: which upgrades are live, which are down (with the fallback that will be used), and what to do to bring disabled ones online.

---

## Writing results to profile

If the user confirms a change (e.g., toggling an upgrade on/off or updating an endpoint):

```python
prof["upgrades"]["search"]["enabled"] = True  # example
P.save_profile(prof, active)  # active = ${CLAUDE_PLUGIN_DATA}/profiles/<name>.json; validates + writes pretty JSON
```

Always reload with `P.load_profile()` after writing to confirm the file is valid (catches JSON errors before the next build run hits them).

The upgrades configured here map to the fallback chains that govern how each capability degrades when unavailable — see `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md` for the full source-chain definitions.

---

## Summary table

| Upgrade | Key | Primary source | Fallback |
|---------|-----|---------------|---------|
| Search | `search` | SearXNG (endpoint in profile) | Tavily → WebSearch floor |
| Scrape | `scrape` | Firecrawl (`FIRECRAWL_API_KEY`) | Playwright → WebFetch |
| Ranked | `ranked` | Tavily (`TAVILY_API_KEY`) | WebSearch floor |
| Transcribe | `transcribe` | Whisper server (endpoint in profile) | Groq (`GROQ_API_KEY`) → paste transcript |
| Social | `social` | Metricool MCP | SocialCrawl → WebSearch floor |

Framework recall (Hormozi magnet types, benchmarks, anti-patterns) is not an upgrade — it ships bundled in `${CLAUDE_PLUGIN_ROOT}/references/`.
