# Pipeline detail

Relocated verbatim from `SKILL.md` at 0.4.0 so the routing blocks fit inside
the compaction window. Nothing here is optional reading for a real run: each
numbered step names the piece it needs.

## Step 0 intake

| Input | Required? | Default |
|---|---|---|
| Client IG handle (e.g. `@your.handle`) | Yes | none |
| Website URL | No | none |
| Niche hint (e.g. "functional medicine") | No | inferred from IG |
| Known competitors / creators (seeds) | No | none (used to seed discovery, not the final set) |
| Target competitor count | No | **~25 (8 large / 9 med / 8 small) ... this is a floor, not a cap** |
| Transcription | No | **on ... automatic** (user may explicitly opt out) |

> **A handful of names is a seed, not the set.** If the user names only 2 to 3 creators,
> treat those as *seeds* and expand to ~25 in Step 2 ... a 2 to 3 account comparison is too
> thin to find real gaps. Only proceed with a smaller set if the user explicitly insists.

## Step 1 positioning

Engagement available from SocialCrawl: **views, likes, comments only**. Do not compute or display saves or shares ... they are not in the API response.

**1b. Website (if provided)**

Using the `firecrawl` skill:

1. `firecrawl map <website_url>` → discover all pages.
2. Scrape key pages: home, about, offers, free lead magnets. Save to `source/website-*.json`.
3. Synthesize positioning into `foundation.md`: niche, ICP (ideal client profile), core offer, differentiators.

**1b-alt. No website (link-in-bio fallback)**

If no website was provided:

1. Check IG bio for a link-in-bio tool (Linktree, Beacons, etc.) via SocialCrawl `linktree`/`linkbio` if supported.
2. Derive positioning from: IG bio text, top-performing captions (by views), any link-in-bio page discovered.
3. Write `foundation.md` with a **reduced-confidence notice**: _"Positioning derived from IG signal only ... no website provided. Confidence: moderate. Recommend revisiting after website review."_

## Step 2 seed expansion

**If the user named a few known competitors/creators (Step 0 seeds):** keep them as
confirmed members of the candidate pool, then *expand around them* ... pull each seed
creator's `GET /profile?handle=<handle>` to read their niche/bio, mine their top
captions for recurring terms, and feed those terms back as additional search seeds.
The goal is to reach the ~25 floor, not to stop at the 2 to 3 they happened to name.

## Step 2 tier bands

- **Guru:** ≥ 500k followers (floor adjustable per run) ... household-authority accounts kept for aspirational pattern reference but **not size-comparable**. Splitting them out keeps the LARGE benchmark honest; essential when the client is small (a 1.9k-follower client vs a 4.8M account is not a "large competitor," it's a different universe ... field-proven 07.12.26).
- **Large:** > 3× client followers (below the Guru floor)
- **Medium:** 0.5× to 3× client followers
- **Small:** < 0.5× client followers

## Checkpoint 2 relevance filters

Present the tiered candidate list to the user. Apply relevance filters:

- Drop: hospitals, celebrity accounts, institutions, off-niche accounts, private accounts, accounts with < 10 reels.
- Flag for human judgment: accounts that look borderline (niche-adjacent but not direct competitors).

Show the filtered set with tier labels. Target: ~25 accounts (8 large / 9 med / 8 small).
User may swap, add, or remove handles. **If the set is still under ~25** (e.g. only the
2 to 3 the user seeded survived filtering), go back to Step 2 and run more seeds before this
checkpoint ... don't present a thin set as final. Proceed under ~25 only if the user
explicitly chooses to.

## Checkpoint 3 phrasing

Phrase it plainly: *"This pull is ≈`N×3` credits. You have `M` left, so you'd be at
≈`M−(N×3)` after. Good to go?"* If the estimate exceeds the balance, say so and offer
to shrink the set or top up ... don't start a pull that will run dry mid-way.

## Step 4a tiers.json

In the project directory, write `tiers.json` mapping each handle to its tier:

```json
{
  "client": "handle",
  "client_followers": 110162,
  "GURU": ["handle0"],
  "LARGE": ["handle1", "handle2"],
  "MED": ["handle3"],
  "SMALL": ["handle4"]
}
```

Keys are **UPPERCASE** (`GURU`/`LARGE`/`MED`/`SMALL`). `GURU` is optional ... omit the key entirely and the engine runs the identical legacy 3-tier path. `client_followers` is a required integer. All handles are **bare** (no `@` prefix) so they match the profile JSON filenames under `source/competitors/profiles/`.

## Step 4b what analyze.py reads and writes

The script reads `source/reels-full.json` (client reels), `source/competitors/reels/<handle>.json` (competitor reels), `source/competitors/profiles/<handle>.json` (follower counts), and `tiers.json`, then writes `analysis-data.md` containing:

- Reach efficiency per creator: `median views ÷ followers`
- Engagement rate: `(likes + comments) ÷ views`
- Per-creator outlier reels: those scoring ≥ 2.5× the creator's own median views
- Hook taxonomy counts (question / story / stat / challenge / authority / other)
- Theme/keyword clusters by tier
- Posting cadence (reels per week)

Engagement is views + likes + comments **only**. saves and shares are never computed, displayed, or estimated ... they are not available from SocialCrawl.

## Step 4c the two-layer pattern matrix

Layer 1 gives corpus-scale statistics (`_pattern_matrix.json` + `_pattern_stats.md`);
Layer 2 picks a stratified subset (`_beatmap_set.json`) that Claude hand-maps (hook type,
4 Hook Killers, re-hook devices, payoff, open-loop integrity, why-won/why-lost) into a
**Reel Beat Blueprint** feeding Step 5 and reel-scripter. Clusters/themes/tools come from
`analysis-config.json` ... niche knowledge lives in the run config, never in these scripts
(theme construction method: `./references/theme-derivation.md`).

## Step 5 the 10 roadmap sections

Section shapes: `./roadmap-template.md`.

1. Executive Summary
2. Current State ... client metrics snapshot
3. Strengths
4. Weaknesses / Friction Points
5. Competitor Gaps ... what competitors do that the client does not
6. Opportunity Matrix ... prioritized ROI × ease
7. Content Strategy ... pillars, formats, cadence
8. 30-Day Action Plan
9. 90-Day Growth Roadmap
10. Hypotheses to Test

## Step 2b search pagination

Search returns a first-page sample (~10 results per seed) and does not support
pagination: breadth comes from running many diverse seeds, not from paginating
the search endpoint.

## Step 4b transcribe first

**Transcribe first.** Run the transcription pass BEFORE `analyze.py`. With transcripts on disk (`source/client-transcripts.json` + `source/competitors/transcripts/`), hook and theme diagnosis key on the **spoken track**, roughly 80% of the signal, and the caption-keyed read is emitted as a separate **Caption patterns** section (the packaging and SEO surface, 20% at most), never mixed into the spoken diagnosis. If `analyze.py` already ran caption-only, re-run it after transcription: the md and json upgrade in place. `meta.transcript_coverage` reports how much of the field was covered. Method, engines and the CDN expiry trap: `./references/transcription.md`.

## The bundled scripts, as the References section listed them

- `./analyze.py` ... deterministic metrics engine; run after `tiers.json` is written
- `./transcribe_reels.py` ... batch transcription off the pulled CDN URLs (no downloading); segments included
- `./extract_patterns.py` ... Layer-1 pattern matrix (~30 dims/reel, winner-vs-loser stats)
- `./select_beatmap_set.py` ... stratified Layer-2 pick (N winners + N losers per cluster)
- `./references/roadmap-template.md` ... 10-section roadmap structure
- `./references/pattern-matrix.md` ... two-layer pattern-matrix method + dimension list
- `./references/theme-derivation.md` ... how to build the per-lane `themes` override (method, not preset)
- `./references/niche-seeds.md` ... seed derivation + relevance-filter heuristics
- `../_shared/references/hook-diagnostics.md` ... 4 Hook Killers diagnostic lens (shared across the core + format engines)

## Checkpoint 3 report lines

- Number of approved competitors
- Reels per competitor (default 36)
- Estimated credit cost: `N × 3` credits
- **Balance: you have `M` credits left** → after this pull, ≈ `M − (N×3)`

## Checkpoint 1 what to present

Present to the user:
- Inferred niche (1-2 sentences)
- Positioning summary from `foundation.md`
- ICP hypothesis

## Checkpoint 4 what to surface

Before finalizing `strategy-roadmap.md`, surface to the user:
- Roadmap audience (client-facing vs. internal?)
- Tone (direct / peer-to-peer / accessible)
- Any sections to expand, trim, or rename

## The reference index

Scripts: `./analyze.py`, `./transcribe_reels.py`, `./extract_patterns.py`,
`./select_beatmap_set.py`, `./render_visuals.py`. Bundled: `./references/`
(`pipeline-detail.md`, `transcription.md`, `guardrails.md`,
`project-shape.md`, `roadmap-template.md`, `pattern-matrix.md`,
`theme-derivation.md`, `niche-seeds.md`). Shared: `../_shared/references/`
(`journey-map.md`, `routing.md`, `state-schema.md`,
`socialcrawl-endpoints.md`, `vault-api.md`, `teach-mode.md`,
`hook-diagnostics.md`, `credit-guard.md`, `untrusted-data.md`). Each is named
at the step that needs it.
