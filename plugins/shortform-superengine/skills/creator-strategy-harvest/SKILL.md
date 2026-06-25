---
name: creator-strategy-harvest
description: Harvest a creator's full content-strategy library (YouTube channel + playlists + newsletter) into a dated, recency-ruled, vault-ready corpus + framework extraction. Use when the user wants to capture/refresh a thought-leader's frameworks (e.g. Kallaway, heyDominik, Hormozi) for a knowledge base. Triggers include "harvest X's library", "get everything Y teaches", "pull all of Z's content", "refresh our notebook on <creator>", "build a corpus from <creator>'s videos".
---

# creator-strategy-harvest

Turn a creator's scattered output into a clean, dated, **recency-ruled** corpus + framework extraction, ready to ingest into a knowledge vault. Built captions-first (seconds, not Whisper). Proven on Kane Kallaway (88 videos + 92 shorts + 64 newsletter issues) + heyDominik.

## Teach mode

Read `~/.claude/revxl/teach-mode` if it exists, else default `beginner`. In **beginner**: plain-English-first — explain in plain words, then name the technical term with a one-line gloss on first use, and add a "what this means for you" line where the consequence isn't obvious. In **off**: standard professional voice, no glosses. Convention + adjust rules: `../_shared/references/teach-mode.md` (`/teach-mode off`, or a plain request like "stop explaining the basics", → rewrite that file and confirm).

## When to use
- You want a thought-leader's frameworks captured systematically (not ad-hoc).
- The source is mostly YouTube (channels/playlists) ± a web newsletter.

## Core principle (from the user)
**Newest = source of truth per concept.** Social-media frameworks decay; recency wins. Every item is dated; contradictions resolve to the newest version; older versions are archived (superseded log), not deleted. Knowledge *structuring* (recency, platform, links) is the **vault's** job — this skill produces clean dated INPUT, it does not hand-build a parallel knowledge store.

## The pipeline

### 1. Map the real footprint (don't trust the main feed)
A creator's `/videos` tab is often a wiped/curated subset. Enumerate **all playlists** and **secondary channels** — the strategy library frequently lives there:
```
yt-dlp --flat-playlist --print "%(title)s | %(id)s" "https://www.youtube.com/@HANDLE/playlists"
yt-dlp --flat-playlist --print "%(id)s|%(title)s" "https://www.youtube.com/@HANDLE/videos" | wc -l
```
Check for a `@HANDLEmarketing`-style second channel (search the web for "<creator> newsletter / channels"). Dedup across playlists by video id.

### 2. Inventory current vs what you already have (gap analysis)
- **Current:** flat-list the target channel(s)/playlists → ids + titles. Fetch upload dates for the relevant slice (`-I 1:N --print "%(upload_date)s|%(title)s|%(id)s"`).
- **Have:** if a NotebookLM notebook exists, list its sources + dates: `notebooklm use <id>` then `notebooklm source list`. Note the pull date.
- **Gap (use a Sonnet sub):** diff current vs have → buckets **HAVE / MISSING / STALE-DUP**. The MISSING list is the harvest target. Lean MISSING when unsure.

### 3. Harvest — captions FIRST (the key lesson)
**YouTube has auto-captions yt-dlp pulls in seconds. Do NOT download audio + run Whisper for YouTube** (that's the trap — Whisper is only needed where no captions exist, e.g. IG reels). Per video:
```
yt-dlp -q --skip-download --write-auto-subs --write-subs --sub-lang en --sub-format json3 --write-info-json -o "subs/%(id)s.%(ext)s" "https://www.youtube.com/watch?v=ID"
```
Parse json3 (event-level join: `''.join` segs within an event, `' '.join` across events; collapse whitespace). Write a dated transcript md with a metadata header (`creator`, `upload_date`, `video_id`, `url`, `source: youtube auto-captions`). Resumable (skip existing). **Whisper fallback** only for the few videos with no caption track (`get_audio` → local-GPU `faster_whisper`).
- Filenames: `<creator> - <slug(title)> - <upload_date>.md`.
- Shorts: same method (his hooks in practice — keep as a separate set).

### 4. Newsletter (if any) — firecrawl, not yt-dlp
A web newsletter isn't video; yt-dlp can't. `firecrawl map "<site>"` → grep `/p/` issue URLs → `firecrawl scrape <url> -o newsletter/<issue>.md` each. Issue number = recency proxy.

### 5. Extract frameworks (batched Sonnet subs — cheap models for the cheap work)
Chunk the corpus (~22 long videos / ~32 newsletter / ~46 shorts per sub) via manifest files. Each sub extracts EVERY framework/hook/retention-device/structure/metric/posting-rule as a dated, bucket-labeled bullet: `- **[Bucket]** — mechanic + specifics/numbers. [src: <title>, <date>]`. Consistent bucket labels (Hook structure, Retention device, Algorithm ranking, Story structure, Virality, Share-rate, Cadence, Content pillars, Scripting, Monetization, Audience). Shorts → a hook **swipe file** (verbatim opening + type + date).

### 6. Synthesize recency-ruled masters (Opus sub)
Fold the extraction partials into: a **canonical master** (concept buckets; newest version wins per bucket; specifics + dates) + a **superseded log** (`⊘ <old> [date] — superseded by <new> [date]`, grouped by bucket). For multi-creator merges, apply **primary-per-topic ownership** (assign each bucket an owner; the owner's current version is canonical; a strong current dissent from another creator is noted, never dropped; flag live conflicts loudly).

### 7. Hand off to the vault (don't hand-build the knowledge store)
Produce a **manifest** (per-file: path, author, content_type, source_platform, date, url) + a **HANDOFF brief**: corpus location, the recency rule (the vault applies it via date facets + sot_policy), the **advice-platform** note (every file is YouTube but the *advice* spans IG/TikTok/YT — the platform that matters is the advice's; if the vault lacks an `advice_platform` facet, that's a schema gap to fill, not a hand-tag job), what's INPUT (raw transcripts) vs SUMMARY (your synthesis docs — not source of truth). Then the vault graphifies and the downstream rubric is derived by querying it.

## Encoded guardrails
- **YouTube → captions (yt-dlp), not Whisper.** Whisper only for no-caption sources.
- CDN/caption URLs are fine fresh; for long audio runs (IG reels) yt-dlp re-resolves expired URLs.
- cp1252: never `print` non-ascii to a Windows console; write files `encoding='utf-8'`; read CLI output `errors='replace'` (mojibake/surrogates).
- NotebookLM `source delete` needs `-y`; YouTube `source add` throttles after ~9 rapid adds → fall back to adding the local transcript `.md` as a text source.
- Recency is the VAULT's job — feed clean dates, don't hand-resolve. Advice-platform is the one facet to verify/add.
- Date everything (MM.DD.YY + each source's own upload date / issue number).

## Output
`research/creator-strategy-harvest-<date>/harvest/`: `inventory/`, `gap-report-<date>.md`, `transcripts/`, `newsletter/`, `extracted/` (partials + masters + superseded log + hook swipe), `HANDOFF-*.md` + manifest.

## Reuses
`yt-dlp` + `ffmpeg` + local `faster_whisper`; `firecrawl-map`/`firecrawl-scrape` skills; `notebooklm-ask` skill (source list/add); the vault `/graphify` for ingest. Scripts: `scripts/caption_harvest.py`, `scripts/build_manifest.py`.

## Non-goals
Hand-building the knowledge graph (vault's job); Whisper-transcribing YouTube when captions exist; treating synthesis docs as source of truth over the vault.
