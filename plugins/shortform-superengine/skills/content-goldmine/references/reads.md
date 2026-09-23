# The three reads: PAPS, Topic Map, Pattern Read

Everything else in the Content Goldmine is computed by `scripts/goldmine_build.py`. These three
are the parts only Claude can do: reading what each breakout reel actually says. They run on
**every** pull, from the reads packet, and are checked before the dashboard is built.

## Order of work

1. `goldmine_build.py reads <project>` writes `reel-build/Goldmine Reads Packet - <n> - <date>.json`.
   It holds every breakout: `shortcode`, `handle`, `url`, `mult`, `views`, `duration_seconds`,
   `engine_hook`, `engine_themes`, `caption`, `transcript`, `is_cta`, `trigger_word`,
   `trigger_detection_rule`, `popularity_rank`. Its `write_to` block names the three files to write.
   **Read the packet. Never edit it.**
2. Write the PAPS file, then the Topic Map, then the Pattern Read (it names the topics), all into
   `reel-build/`, under exactly the names in `write_to`.
3. `goldmine_build.py check-reads <project>`. On FAIL, fix the named rows and run it again. The
   dashboard is only built from reads that passed.

## Rules for all three

- **Read, never invent.** Every value comes from the reel's own caption, transcript or on-screen
  text in the packet. Where the reel genuinely does not say something, the field is `null`.
- An empty `transcript` means there is no usable speech (music-only, or not transcribed). Read the
  caption, and say so in `source_surface`.
- Plain English. No em or en dashes. Short lines: these render in a dashboard.
- Frozen: a later re-read is a new dated file, never an edit of an old one.
- Mechanical fields (`shortcode`, `handle`, `url`, `mult`, `views`, `duration_seconds`,
  `trigger_word`, `trigger_detection_rule`, `popularity_rank`) are copied from the packet
  verbatim. They are never retyped or rounded.

## 1. Lead Magnet PAPS

One row for **every** breakout where the packet says `is_cta: true` (a caption asking for a
trigger-word comment in exchange for something). Non-CTA breakouts are listed by shortcode only.

```json
{
  "_note": "PAPS read of every trigger-CTA breakout in this pull. Mechanical fields are copied from the reads packet; PAPS fields are read from each reel's transcript and caption. An element the reel does not contain is null, never inferred.",
  "generated_at": "2026-09-23T15:04:00Z",
  "window": {"from": "<packet window.from>", "to": "<packet window.to>"},
  "corpus": {"breakouts_total": 76, "cta_breakouts": 43, "non_cta_breakouts": 33},
  "field_notes": {
    "problem": "The pain the reel names. Null where the reel names none.",
    "agitation": "How the reel twists the pain harder. Null where it skips this.",
    "promise": "The outcome offered in exchange for the comment.",
    "solution_delivery": "What the thing actually is and how it reaches the viewer.",
    "source_surface": "Which surfaces the PAPS was read from: spoken, on_screen_text, caption."
  },
  "paps": [
    {
      "shortcode": "Abc123XyZ",
      "handle": "examplecreator",
      "url": "https://www.instagram.com/reel/Abc123XyZ/",
      "mult": 6.412,
      "views": 84210,
      "duration_seconds": 41.2,
      "trigger_word": "GUIDE",
      "trigger_detection_rule": "bare_caps",
      "topic": "Booking discovery calls from Instagram DMs",
      "problem": "Leads go cold in the DMs because the coach answers every message by hand.",
      "agitation": "\"You are losing the ones who were ready to buy while you type.\"",
      "promise": "A DM flow that books the call without you typing a word.",
      "solution_delivery": "A free Notion guide with the five DM scripts, sent by automated DM after the comment.",
      "source_surface": ["spoken", "caption"],
      "popularity_rank": {"rank_by_benchmark": 3, "benchmark_x": 12.4, "rank_by_raw_rate": 5, "comment_rate": 0.0182, "benchmark_unavailable_reason": null},
      "note": null
    }
  ],
  "non_cta": ["Def456UvW", "Ghi789RsT"]
}
```

- `promise` and `solution_delivery` are never null: a CTA always offers something. If the reel
  truly does not say what, write what the caption says it is ("the link", "the template") and use
  `note` to say the reel does not describe it.
- `topic` is a short plain phrase for what the reel is about (the Topic Map's `angle` may reuse it).
- `agitation` may quote the reel. Quote exactly or not at all.
- `corpus` counts must match the packet (`breakouts`, `cta_breakouts`).

## 2. Topic Map (`goldmine-topic-map/1`)

The engine's themes are broad bins. This read finds the real topics inside them.

```json
{
  "schema": "goldmine-topic-map/1",
  "pull": {"manifest": "<packet manifest>", "n": 76},
  "read": "Angles and topics read by Claude on <date> from each reel's transcript and caption. Topics clustered bottom-up from the angles, each homed under one engine theme.",
  "no_theme_label": "(no engine theme)",
  "topics": [
    {"id": "t01", "name": "DM automation for bookings", "theme": "leads-sales-offers", "summary": "Reels that turn DMs into booked calls with an automated flow."}
  ],
  "reels": {
    "Abc123XyZ": {"topic": "t01", "angle": "Five DM scripts that book discovery calls on autopilot"}
  }
}
```

- `angle` = one plain line saying what THIS reel is about. Never a hook quote, never a category.
- Write every angle first. Then cluster topics bottom-up from the angles, then home each topic
  under ONE engine theme, the one most of its reels carry in `engine_themes`. The dashboard flags
  reels whose home theme is not among their own. A topic whose reels carry no engine theme
  goes under `no_theme_label`. **Never invent a theme**; the check rejects one.
- Every breakout gets exactly one row, pointing at a real topic id.
- Topic ids are `t01`, `t02`, ... in order of first appearance.

## 3. Pattern Read (`goldmine-pattern-read/1`)

How the winners open, what they give away, and which topics run together.

```json
{
  "schema": "goldmine-pattern-read/1",
  "pull": {"manifest": "<packet manifest>", "n": 76, "cta_n": 43},
  "read": "Hook formulas, lead-magnet types and topic threads read by Claude on <date> from each reel's full hook and the PAPS solution_delivery text. Every number shown against them is computed by the generator.",
  "formulas": [
    {"id": "f_if", "name": "Qualifier open", "template": "If you [are / do X]...", "summary": "Names who this is for in the first breath, then promises the payoff."}
  ],
  "lm_types": [
    {"id": "lm_guide", "name": "Guide or breakdown", "summary": "A written walkthrough or setup guide."}
  ],
  "threads": [
    {"id": "th_dms", "name": "Turn DMs into calls", "topics": ["t01", "t04"], "summary": "Everything about booking from the inbox."}
  ],
  "reels": {
    "Abc123XyZ": {"formula": "f_if", "lm_type": "lm_guide", "magnet": "Five DM scripts in a Notion guide"},
    "Def456UvW": {"formula": "f_list"}
  }
}
```

- A **formula** is the SHAPE of the opening line, read off the reel's first sentence in the
  transcript (or the caption's first line when there is no speech). It is never the engine's hook
  type. Name it so a coach could write a new line from the `template`.
- **Every** breakout gets a `formula`. Every CTA breakout also gets `lm_type` and `magnet` (a short
  plain name for what they actually send, read from the PAPS `solution_delivery`).
- **Threads** group related topics. Every Topic Map topic sits in exactly one thread.
- Ids: formulas `f_<word>`, magnet types `lm_<word>`, threads `th_<word>`; unique within the file.

## What check-reads rejects

Missing files or invalid JSON; a missing CTA row or a row that is not a breakout; null `promise`
or `solution_delivery`; `corpus` counts that do not match the packet; a wrong `schema`; a
breakout with no Topic Map or Pattern Read row; an unknown topic, formula or magnet type id; a
CTA row without `lm_type` and `magnet`; a theme that is not an engine theme; a topic in zero or
two threads; duplicate ids.
