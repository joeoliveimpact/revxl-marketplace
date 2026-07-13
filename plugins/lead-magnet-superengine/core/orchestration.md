# Orchestration — Routing Tree & Subagent Dispatch

The orchestrator's job is routing, not doing. It reads the client profile, detects live capabilities, picks the right chain for each job, and dispatches heavy work to the `lm-research` subagent. It never runs multi-source harvesting in the main context.

---

## Routing decision tree

Source: Dependency Audit & Routing Map §3 (06.17.26). Reproduced verbatim as the canonical routing contract.

```
JOB: quick fact / single lookup
  → WebSearch floor                                   (cheap, done)

JOB: broad competitor discovery ("who/what magnets in <niche>")
  → SearXNG (if up) → Tavily/Exa (if key) → WebSearch floor
  → then SocialCrawl (if key) for social-native discovery

JOB: extract a found page (opt-in page, landing, ad)
  → Firecrawl (if key) → Playwright (always) → WebFetch floor

JOB: competitor social "what's working" (engagement/format)
  → Metricool (named watchlist, deep)  ⨉  SocialCrawl (discovery, broad)
  → WebSearch floor if neither

JOB: tear down a competitor video/webinar/VSL
  → yt-dlp (pull) → ffmpeg (audio/frames)
  → Whisper server (profile endpoint) → Groq (if key)
  → video-use for visual scenes

JOB: synthesis / recall / framework
  → bundled ${CLAUDE_PLUGIN_ROOT}/references/ docs (frameworks, benchmarks, anti-patterns — always available)

RULE: heavy lifting (transcribe, scrape, search) → LOCAL/FREE tools.
      Claude tokens spent ONLY on reasoning + synthesis + copy.
```

---

## Why a tree, not blast-everything

Parallel-blasting all tools wastes credits/tokens, returns redundant data, and slows the run. The tree picks one primary per job, falls back only on failure, and de-dups before synthesis.

Three concrete costs of blasting:
1. **Token burn** — feeding Claude 10 redundant search result sets costs 5–10× more per run than a single filtered result.
2. **Redundant data** — SearXNG, Tavily, and WebSearch often return overlapping URLs; synthesis overhead outweighs any coverage gain.
3. **Latency** — waiting for all parallel fetches before synthesis delays output by the slowest tool in the blast, not just the needed one.

The tree is cheaper, faster, and easier to debug when a source fails.

---

## Subagent dispatch rule

**Threshold:** any job that requires more than one remote call (scrape N pages, transcribe N videos, pull Metricool for N competitors) is dispatched to the `lm-research` subagent.

**What the orchestrator keeps in main context:**
- Profile load and capability detection (`lib.profile.load_profile`, `lib.capability_detect.detect`)
- Job-type classification (which row of the routing tree applies)
- Chain construction (building the ordered source list for `lib.sources.search`)
- Receiving and routing the harvested data back into Stage 2 (draft) of `${CLAUDE_PLUGIN_ROOT}/core/build-core.md`
- Intake questions when all sources fail (the `"qa"` fallback in `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md`)

**What is dispatched to `${CLAUDE_PLUGIN_ROOT}/agents/lm-research.md`:**
- Scraping multiple competitor landing pages via Firecrawl / Playwright
- Downloading and transcribing competitor videos (yt-dlp → ffmpeg → Whisper chain)
- Pulling Metricool engagement benchmarks for N brands
- Running SocialCrawl across multiple accounts
- Synthesizing a structured research brief from all harvested sources

The subagent returns a structured dict (competitor intel, transcripts, social benchmarks, extracted copy) to the orchestrator, which folds it into the blueprint stage of the build.

---

## Capability-gated routing

Before dispatching any job, the orchestrator resolves live capabilities:

```python
from lib.profile import load_profile, resolve
from lib.capability_detect import detect

import os
# Active profile persists at ${CLAUDE_PLUGIN_DATA}/profiles/<name>.json
profile = load_profile(os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], "profiles", "client.json"))
# Build probes from the profile (endpoints, env keys) — see the lm-setup skill.
# detect() returns False for any enabled capability without a probe (honest default).
caps = detect(profile, probes)  # {"search": bool, "scrape": bool, ...}
```

If `caps["search"]` is `False`, the `SearXNG` slot is skipped; the chain falls to `Tavily` or the WebSearch floor. If `caps["scrape"]` is `False`, Firecrawl is skipped; Playwright is always available as the next step. The routing tree is the same structure regardless — only the available slots change.

---

## Cross-reference index

| Path | Role in orchestration |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/lib/profile.py` | `load_profile(path)` / `resolve(profile, capability)` — reads client upgrade config |
| `${CLAUDE_PLUGIN_ROOT}/lib/capability_detect.py` | `detect(profile, probes)` — live probe of enabled capabilities |
| `${CLAUDE_PLUGIN_ROOT}/lib/sources.py` | `search(query, chain)` — chain-walking sourcing with fallback |
| `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md` | Per-job chain definitions and user fallback questions |
| `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` | The five-stage pipeline that orchestration feeds into |
| `${CLAUDE_PLUGIN_ROOT}/profiles/client.blank.json` | Shipped blank template (active copy lives at `${CLAUDE_PLUGIN_DATA}/profiles/<name>.json`); upgrade keys: `search`, `scrape`, `ranked`, `transcribe`, `social` |
| `${CLAUDE_PLUGIN_ROOT}/agents/lm-research.md` | Subagent that owns heavy multi-source harvesting |
