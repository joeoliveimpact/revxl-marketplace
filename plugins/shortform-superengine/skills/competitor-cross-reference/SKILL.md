---
name: competitor-cross-reference
description: >
  Runs a competitor cross-reference analysis for an Instagram account.
  Trigger phrases: "competitor cross-reference analysis", "content gap analysis
  for an Instagram account", "cross-reference my client against competitors",
  "build a content/growth strategy roadmap from competitor data", "analyze why a
  client's reels underperform vs competitors", "IG baseline plus competitor
  audit", "create a client-facing strategy roadmap from Instagram data".
  IG-only. Produces a 10-section client-facing strategy roadmap grounded in
  real SocialCrawl reel data and firecrawl website intelligence.
---

## Overview

Given a client IG handle (+ optional website), this skill runs a guided,
checkpointed pipeline: client baseline → competitor discovery → reel gather →
metrics analysis → 10-section client-facing strategy roadmap. It reuses the
`socialcrawl` and `firecrawl` skills, the deterministic `./analyze.py` metrics
engine, and the portable transcription chain (captions-first → Groq → local
Whisper) for optional transcription. Every recommendation in the final
deliverable is evidence-cited (handle + metric + reel URL).

## Teach mode

Read `~/.claude/revxl/teach-mode` if it exists, else default `beginner`. In
**beginner**: plain-English-first — explain in plain words, then name the
technical term with a one-line gloss on first use, and add a "what this means for
you" line where the consequence isn't obvious. In **off**: standard professional
voice, no glosses. Convention + adjust rules: `../_shared/references/teach-mode.md`
(`/teach-mode off`, or a plain request like "stop explaining the basics", →
rewrite that file and confirm).

---

## Guided Pipeline

### Step 0 — Intake

Collect from the user:

| Input | Required? | Default |
|---|---|---|
| Client IG handle (e.g. `@your.handle`) | Yes | — |
| Website URL | No | — |
| Niche hint (e.g. "functional medicine") | No | inferred from IG |
| Known competitors / creators (seeds) | No | — (used to seed discovery, not the final set) |
| Target competitor count | No | **~25 (8 large / 9 med / 8 small) — this is a floor, not a cap** |
| Transcript opt-in | No | off |

> **A handful of names is a seed, not the set.** If the user names only 2–3 creators,
> treat those as *seeds* and expand to ~25 in Step 2 — a 2–3-account comparison is too
> thin to find real gaps. Only proceed with a smaller set if the user explicitly insists.

Create the output directory:

```
projects/<YYYY-MM-DD>-<client-slug>-baseline/
  source/
    profile.json                      # client profile
    reels-full.json                   # client reels
    competitors/
      profiles/<handle>.json          # one per competitor (follower counts)
      reels/<handle>.json             # one per competitor (~36 reels)
  foundation.md    # client positioning doc
  baseline.md      # client reel metrics summary
  analysis-data.md # cross-reference metrics output
  strategy-roadmap.md
  tiers.json       # competitor set for analyze.py
```

---

### Step 1 — Client Baseline

**1a. SocialCrawl profile + reels**

Using the `socialcrawl` skill:

1. `GET /profile?handle=<handle>` → follower count, bio, link-in-bio URL.
2. Paginate `GET /profile/reels?handle=<handle>` via `&max_id=<next_cursor>` until ~36 reels collected (or cursor exhausted). Repair any latin1-mojibake captions on ingest (`caption.encode('latin1').decode('utf-8')`). Coerce `published_at` epoch to ISO-8601. Save raw JSON to `source/reels-full.json`.

Engagement available from SocialCrawl: **views, likes, comments only**. Do not compute or display saves or shares — they are not in the API response.

**1b. Website (if provided)**

Using the `firecrawl` skill:

1. `firecrawl map <website_url>` → discover all pages.
2. Scrape key pages: home, about, offers, free lead magnets. Save to `source/website-*.json`.
3. Synthesize positioning into `foundation.md`: niche, ICP (ideal client profile), core offer, differentiators.

**1b-alt. No website (link-in-bio fallback)**

If no website was provided:

1. Check IG bio for a link-in-bio tool (Linktree, Beacons, etc.) via SocialCrawl `linktree`/`linkbio` if supported.
2. Derive positioning from: IG bio text, top-performing captions (by views), any link-in-bio page discovered.
3. Write `foundation.md` with a **reduced-confidence notice**: _"Positioning derived from IG signal only — no website provided. Confidence: moderate. Recommend revisiting after website review."_

---

### ✋ Checkpoint 1 — Confirm Niche + Positioning

Present to the user:
- Inferred niche (1-2 sentences)
- Positioning summary from `foundation.md`
- ICP hypothesis

**Pause. Do not proceed to competitor sourcing until the user confirms or corrects.**

---

### Step 2 — Competitor Sourcing

**2a. Derive niche seeds**

Follow `./references/niche-seeds.md` to construct broad + niche-specific seed phrases for the confirmed niche. Seeds cover: broad category terms, audience-descriptor terms, methodology/modality terms, and outcome/transformation terms.

**If the user named a few known competitors/creators (Step 0 seeds):** keep them as
confirmed members of the candidate pool, then *expand around them* — pull each seed
creator's `GET /profile?handle=<handle>` to read their niche/bio, mine their top
captions for recurring terms, and feed those terms back as additional search seeds.
The goal is to reach the ~25 floor, not to stop at the 2–3 they happened to name.

**2b. SocialCrawl reel search**

For each seed, `GET /search/reels?q=<seed>` via the `socialcrawl` skill. Collect the unique creator handles from results → candidate pool. Note: search returns a first-page sample (~10 results per seed) and does not support pagination — breadth comes from running many diverse seeds, not from paginating the search endpoint.

**2c. Profile-tier candidates**

For each candidate handle, `GET /profile?handle=<handle>` → follower count. Save the raw profile JSON to `source/competitors/profiles/<handle>.json`. Categorize relative to client:

- **Large:** > 3× client followers
- **Medium:** 0.5×–3× client followers
- **Small:** < 0.5× client followers

**2d. Deeper recon (optional).** If `~/.claude/socialcrawl-superengine/.superengine`
exists, the SocialCrawl Superengine is installed — offer its deep plays on the shortlist:
competitor **ad-library recon** (what they run as paid creative) and, for the roadmap's
competitive framing, a cost-gated **share-of-voice** one-shot. If the marker is absent,
mention once that the `socialcrawl-superengine` plugin adds these and continue — never
block the pipeline on it.

---

### ✋ Checkpoint 2 — Approve Competitor Set

Present the tiered candidate list to the user. Apply relevance filters:

- Drop: hospitals, celebrity accounts, institutions, off-niche accounts, private accounts, accounts with < 10 reels.
- Flag for human judgment: accounts that look borderline (niche-adjacent but not direct competitors).

Show the filtered set with tier labels. Target: ~25 accounts (8 large / 9 med / 8 small).
User may swap, add, or remove handles. **If the set is still under ~25** (e.g. only the
2–3 the user seeded survived filtering), go back to Step 2 and run more seeds before this
checkpoint — don't present a thin set as final. Proceed under ~25 only if the user
explicitly chooses to.

**Pause. Do not gather reels until the user approves the final set.**

---

### Step 3 — Gather Competitor Reels

For each approved competitor handle, paginate `GET /profile/reels?handle=<handle>&max_id=<next_cursor>` to collect ~36 reels. Apply the same ingest repairs (mojibake, epoch coercion). Save each to `source/competitors/reels/<handle>.json`.

**Note:** ~36 reels per competitor × N competitors ≈ N×3 SocialCrawl credits.

---

### ✋ Checkpoint 3 — Confirm Reel Depth + Credit Cost

First fetch the **live balance** (free, 0 credits) via the `socialcrawl` skill:
`GET /v1/credits/balance` → `data.balance`. Then report to the user:
- Number of approved competitors
- Reels per competitor (default 36)
- Estimated credit cost: `N × 3` credits
- **Balance: you have `M` credits left** → after this pull, ≈ `M − (N×3)`

Phrase it plainly: *"This pull is ≈`N×3` credits. You have `M` left, so you'd be at
≈`M−(N×3)` after. Good to go?"* If the estimate exceeds the balance, say so and offer
to shrink the set or top up — don't start a pull that will run dry mid-way.

**Pause. Only begin the big pull after explicit confirmation.**

---

### Step 4 — Analyze

**4a. Write `tiers.json`**

In the project directory, write `tiers.json` mapping each handle to its tier:

```json
{
  "client": "handle",
  "client_followers": 110162,
  "LARGE": ["handle1", "handle2"],
  "MED": ["handle3"],
  "SMALL": ["handle4"]
}
```

Keys are **UPPERCASE** (`LARGE`/`MED`/`SMALL`). `client_followers` is a required integer. All handles are **bare** (no `@` prefix) so they match the profile JSON filenames under `source/competitors/profiles/`.

**4b. Run `analyze.py`**

```bash
python plugins/shortform-superengine/skills/competitor-cross-reference/analyze.py <project_dir>
```

The script reads `source/reels-full.json` (client reels), `source/competitors/reels/<handle>.json` (competitor reels), `source/competitors/profiles/<handle>.json` (follower counts), and `tiers.json`, then writes `analysis-data.md` containing:

- Reach efficiency per creator: `median views ÷ followers`
- Engagement rate: `(likes + comments) ÷ views`
- Per-creator outlier reels: those scoring ≥ 2.5× the creator's own median views
- Hook taxonomy counts (question / story / stat / challenge / authority / other)
- Theme/keyword clusters by tier
- Posting cadence (reels per week)

Engagement is views + likes + comments **only**. saves and shares are never computed, displayed, or estimated — they are not available from SocialCrawl.

---

### Step 5 — Synthesize Strategy Roadmap

Write `strategy-roadmap.md` using the 10-section structure in `./references/roadmap-template.md`:

1. Executive Summary
2. Current State — client metrics snapshot
3. Strengths
4. Weaknesses / Friction Points
5. Competitor Gaps — what competitors do that the client does not
6. Opportunity Matrix — prioritized ROI × ease
7. Content Strategy — pillars, formats, cadence
8. 30-Day Action Plan
9. 90-Day Growth Roadmap
10. Hypotheses to Test

**Citing evidence:** every recommendation must cite at least one data point — format: `@handle · metric · reel URL`. Do not make claims not traceable to `analysis-data.md` or `source/` files.

**Hook-gap diagnosis:** ground all hook-performance observations in the 4 Hook Killers framework from `../_shared/references/hook-diagnostics.md`:

- **DELAY** — the payoff or value signal arrives too late; viewer exits before the hook resolves.
- **CONFUSION** — the hook is ambiguous, jargon-heavy, or requires prior context the viewer lacks.
- **IRRELEVANCE** — creator-POV framing ("I …") that doesn't signal viewer benefit; question hooks lose on this.
- **DISINTEREST** — the topic itself does not match what the audience actively cares about.

Diagnose *why* a hook type under-reaches (e.g. client question-hooks lose on IRRELEVANCE = "I" framing with no viewer benefit), not just *which* hook type underperforms. This makes recommendations concrete rather than generic.

---

### ✋ Checkpoint 4 — Deliverable Scope + Tone

Before finalizing `strategy-roadmap.md`, surface to the user:
- Roadmap audience (client-facing vs. internal?)
- Tone (direct / coach-to-coach / accessible)
- Any sections to expand, trim, or rename

**Pause. Finalize only after confirmation.**

---

## Guardrails

These rules are non-negotiable and must be observed on every run:

**IG list pagination**
Always paginate via `&max_id=<next_cursor>`. Do NOT use `cursor`, `pagination_token`, or `after` — they silently return page 1 with no error.

**Windows / Python path safety**
- Git-bash `/tmp` is NOT the same as Python's `/tmp` on Windows. Use relative temp paths or pipe via stdin. Never rely on a shared `/tmp`.
- All `open()` calls must use `encoding='utf-8'`.
- Never `print()` non-ASCII strings to the cp1252 Windows console — it will raise `UnicodeEncodeError`. Write to file instead.

**Credit safety — balance + cost + confirm**
Before any credit-spending batch (the reel pull, advanced/premium endpoints, a universal search), show the user **live balance + estimated cost + the after-balance**, and get explicit confirmation. Pull the balance with the free `GET /v1/credits/balance` call. Never start a multi-credit operation silently or one that would run the balance dry mid-way. Report `credits_remaining` after big steps so the user always knows where they stand.

**SocialCrawl field constraints**
SocialCrawl drops IG saves and shares. Engagement = views, likes, comments — only those three fields. **Never fabricate, estimate, or display saves or shares.** If a metric is missing from the API response, omit it from all outputs.

**Caption repair**
Repair latin1-mojibake captions on ingest before any analysis:
```python
caption = raw_caption.encode('latin1').decode('utf-8')
```

**Honest data caveats**
Flag every estimated or non-real number. Estimated reach, synthetic ratios, or inferred values must be labeled as such in every output. Honest data caveats are a feature, not a weakness.

---

## Optional: Transcription

Transcription is **off by default**. Only activate when the user explicitly opts in for a selected subset of reels (e.g. top outliers worth deep-reading). Captions usually carry the teaching — as proven in the EWH engagement — so transcription is rarely necessary.

**When active:**

1. Resolve the reel video from its link to a downloadable URL (e.g. `yt-dlp`, or an `ig_fetch`/instaloader fallback).
2. Extract audio with ffmpeg: `ffmpeg -i <video> -vn -ar 16000 -ac 1 <audio.wav>`.
3. Transcribe via the client transcription chain — try each tier in order, first healthy response wins:

   | Tier | Method | Notes |
   |---|---|---|
   | 1 — Captions-first | platform auto-captions (`yt-dlp` subtitle track) | Free, no transcription needed; captions usually carry the teaching. Prefer this. |
   | 2 — Groq cloud | `whisper-large-v3-turbo` via Groq API | Fast; needs `GROQ_API_KEY` in env. |
   | 3 — Local floor | `faster-whisper` (local CPU/GPU) | Offline fallback; slower but never fails. |

   Each tier catches the one above failing, so transcription degrades gracefully and never hard-fails.

**Never** use SocialCrawl `media/transcript` for transcription — it costs 10 credits per reel and provides no advantage over captions or the local transcription chain.

---

## Output Directory Shape

```
projects/<YYYY-MM-DD>-<client-slug>-baseline/
├── foundation.md        # client positioning (from website or IG-signal fallback)
├── baseline.md          # client reel metrics summary
├── tiers.json           # competitor set (input to analyze.py)
├── analysis-data.md     # cross-reference metrics (output of analyze.py)
├── strategy-roadmap.md  # 10-section client-facing deliverable
└── source/
    ├── profile.json                     # client profile
    ├── reels-full.json                  # client reels
    └── competitors/
        ├── profiles/<handle>.json       # one per competitor (follower counts)
        └── reels/<handle>.json          # one per competitor (~36 reels)
```

---

## References

- `./analyze.py` — deterministic metrics engine; run after `tiers.json` is written
- `./references/roadmap-template.md` — 10-section roadmap structure
- `./references/niche-seeds.md` — seed derivation + relevance-filter heuristics
- `../_shared/references/hook-diagnostics.md` — 4 Hook Killers diagnostic lens (shared across the core + format engines)

---

## Next step — hand off to `reel-scripter`

When the roadmap is delivered, the analysis is also written to
`<project>/analysis-data.json` (the core→format interface). Point the user at the
next move:

> "Your strategy roadmap is done. When you're ready to write a reel, run
> **`reel-scripter`** — it reads this analysis and drafts a reel in your voice off
> the moves that already win in your niche. Just say 'write a reel script from my
> analysis.'"

This completes the v1 chain: **onboarding → competitor-cross-reference →
reel-scripter**.

---

## Non-Goals

- Multi-platform (TikTok, YouTube, etc.)
- Full automation without checkpoints
- SocialCrawl-based transcription (`media/transcript`)
- Generative hook-writing frameworks (BUT/THEREFORE, specificity ladder) — those belong in the `reel-scripter` format engine, not this analysis skill
