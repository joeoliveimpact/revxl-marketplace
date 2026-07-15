# Pattern Matrix — two-layer beat/pattern measurement (Step 4c)

Measured production targets for reels, adapted from the long-form "measured beat
blueprint" method (stratified small-n, hand-mapped, medians-with-ranges, format is a
legit reason to stray) and extended with what short-form data uniquely allows: a
**full-corpus quantitative layer** and a **loser control group** (bottom-N per creator),
which winner-only studies never have.

**This file documents the machinery. Niche knowledge (clusters, themes, tool lists) and
every measured number belong to the client run's config + outputs — never hardcode them
into the plugin.**

---

## Layer 1 — deterministic, every transcribed reel (`extract_patterns.py`)

Script-computed, so it runs at corpus scale (hundreds to ~1,000+ reels) and every
dimension gets a **winner-vs-loser lift** with real n. Requires transcripts **with
segment timestamps** (see SKILL.md Transcription — `transcribe_reels.py` produces them).

| Group | Dims |
|---|---|
| Timing (from segments) | duration · hook-end (first-segment end) · time-to-15-words (interpolated) · words/sec overall · hook-WPS vs body (front-loading) · silence share · max dead-air gap · CTA position % · ending type (cta-outro / **loop-back** / hard-stop) |
| Rhetoric (per 100 words) | contrast density · you:I ratio (IRRELEVANCE-killer metric) · hedge count · specificity density (numbers/$/%/timeframes) · curiosity-gap phrases · enumeration ("7 tools that…") · question count · imperative-opener segments · negation-open |
| Content & mechanics | tool-mention league (config-overridable lexicon) · theme tags (config `themes`, same override analyze.py reads) · CTA taxonomy (comment-word bait + captured word / follow / link-in-bio / save-share / DM) · caption↔spoken relationship (repeats-hook / complements / hashtag-dump) + caption length |
| Engagement joins | views · outlier-multiple vs creator median · ER · comment-rate (cross-tab against comment-bait = does the bait pay?) · winner/loser rank · cluster |

Outputs: `_pattern_matrix.json` (row per reel) + `_pattern_stats.md` (W-vs-L medians +
lift, share-of-reels flags, tool league, CTA payoff, cluster medians).

**Spoken-vs-caption check:** analyze.py's hook taxonomy reads caption line 1. The matrix
measures the *spoken* opening — where they diverge, trust the spoken read and say so in
the deliverable.

## Layer 2 — semantic, stratified subset (`select_beatmap_set.py` + Claude)

The selector picks **N winners + N losers per cluster** (default 3+3; clusters from
config, falling back to tiers) into `_beatmap_set.json`. Claude then hand-maps each
pick from its segments — this part is judgment, not regex:

- Spoken hook type (question / claim / negation / numbered / POV / story / news-jack)
- **4 Hook Killers diagnosis** (DELAY / CONFUSION / IRRELEVANCE / DISINTEREST — see `hook-diagnostics.md`)
- Re-hook list with device tags (contrast / open-loop / curiosity) + timestamps → cadence
- Promise placement, explicit vs implied
- Payoff placement % + type (single reveal vs distributed listicle)
- **Open-loop integrity** — does the payoff actually resolve the hook's promise?
- Value shape (teach-how / tool-reveal / rant / story-proof / demo) · proof element
- One evidence-cited **why-won / why-lost** verdict line

## Synthesis — the Reel Beat Blueprint

Merge both layers into a blueprint doc (client-facing or internal per Checkpoint 4):
medians-with-ranges per cluster, W-vs-L lift per dimension, and a
**CONFIRMED / CORRECTED verdict** for every prior assumption (the caption-based hook
taxonomy, any inherited long-form numbers). Targets are yardsticks, not laws — a reel
may stray for format reasons; the blueprint should say when that's fine.

**Out of scope (future pass):** visual dims — on-camera %, visual-change rate — need
video frames (ffmpeg scene-detect on the CDN mp4s), not audio. Flag, don't fake.

## Run order

```bash
python transcribe_reels.py <project_dir>            # same day as the reel pull (CDN expiry!)
python extract_patterns.py <project_dir>            # Layer 1 -> matrix + stats
python select_beatmap_set.py <project_dir>          # Layer 2 picks -> _beatmap_set.json
# Claude hand-maps the picks, then writes the Reel Beat Blueprint
```
