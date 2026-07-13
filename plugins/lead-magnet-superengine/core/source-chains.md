# Source Chains — Data-Substitution Map

Every piece of data the build pipeline needs has an ordered source chain. The engine walks the chain from left to right, stops at the first source that returns results, and falls back to asking the user only when every automated source fails.

`${CLAUDE_PLUGIN_ROOT}/lib/sources.py` implements the chain-walking logic via `search(query, chain, fetch=None) -> dict`. When all chain members fail it returns `{"source": "qa", "results": []}` — the `"qa"` source key is the signal to trigger the user question below.

---

## Chain table

| Build input | Ordered source chain | User question (if all fail) |
|---|---|---|
| **Competitor discovery** — who is in this niche, what magnets do they offer | SearXNG (endpoint from profile `search` block) → Tavily (if `ranked` key present) → WebSearch floor | `"Name 2-3 competitors and what you've seen them offer."` |
| **Competitor social — what's working** (engagement, best formats, top-performing reels) | Metricool MCP (named watchlist, deep analytics) → SocialCrawl skill (if `social` key present, broad discovery) → WebSearch floor | `"Which of your competitors are most active on social, and what kinds of posts seem to perform best for them?"` |
| **Page extraction** — clean text/structure from a found landing page, opt-in page, or ad | Firecrawl (if `scrape` key present) → Playwright scrape (always available) → WebFetch floor | `"Paste the key copy from the page you want analyzed."` |
| **Video / webinar / VSL teardown** — transcript + visual breakdown of a competitor video | yt-dlp (pull) → ffmpeg (audio extract / frame grab) → Whisper server (endpoint from profile `transcribe` block) → Groq (if `GROQ_API_KEY` present) → `video-use` skill (visual scene analysis) | `"Paste the transcript of the video, or describe the key points you remember from it."` |
| **Synthesis / recall / framework lookup** — Hormozi framing, benchmarks, anti-patterns | Bundled `${CLAUDE_PLUGIN_ROOT}/references/` docs (always available, no upgrade): `lead-magnet-frameworks.md`, `format-by-niche-matrix.md`, `conversion-benchmarks.md`, `lead-magnet-mistakes.md`, `hooks-and-titles.md`, `nurture-handoff.md` | `"What framework or approach do you want to apply? Describe the model or paste the relevant excerpt."` |

---

## Search example — competitor discovery (verbatim)

```
SearXNG @ <endpoint from profile "search" block>
  GET <endpoint>/search?q=<URL-encoded query>&format=json
  ↓ on empty / 000 response (or no endpoint configured)
Tavily (if TAVILY_API_KEY present in env)
  ↓ on no key / failure
WebSearch floor (built-in, always-on)
  ↓ if all fail
→ ask: "Name 2-3 competitors and what you've seen them offer."
```

Call via `lib.sources.searxng_url(query, base)` (where `base` is the profile's `search` endpoint) to build the URL, then pass a `chain` list to `lib.sources.search()` — each searxng chain spec carries its `base` from the profile.

---

## Source availability detection

Before building the chain, call `lib.capability_detect.detect(profile, probes)` to get a live `dict[str, bool]` of what's actually reachable. Profile is loaded via `lib.profile.load_profile(path)` and `lib.profile.resolve(profile, capability)` returns the upgrade block (or `None` if disabled). The five upgrade keys in `${CLAUDE_PLUGIN_ROOT}/profiles/client.blank.json` (template — the active copy lives at `${CLAUDE_PLUGIN_DATA}/profiles/<name>.json`) map directly to chain decisions:

| Profile key | Unlocks |
|---|---|
| `search` | SearXNG as primary; endpoint set in profile |
| `ranked` | Tavily as ranked fallback |
| `scrape` | Firecrawl for page extraction |
| `transcribe` | Whisper transcription; endpoint set in profile |
| `social` | SocialCrawl for competitor social discovery |

Framework recall is not gated by any profile key — the bundled `${CLAUDE_PLUGIN_ROOT}/references/` docs are always available.

If a capability is `"enabled": false` in the profile, its chain slot is skipped — the next member in the chain takes over.

---

## Heavy harvesting note

When a chain step involves scraping N competitor pages, transcribing multiple videos, or pulling Metricool data for a full benchmark, that work is dispatched to the `lm-research` subagent (`${CLAUDE_PLUGIN_ROOT}/agents/lm-research.md`). The orchestrator skill stays in the main context for intake and routing decisions only. See `${CLAUDE_PLUGIN_ROOT}/core/orchestration.md`.
