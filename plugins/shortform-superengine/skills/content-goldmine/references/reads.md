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
   The same step pre-fills the three files named in `write_to` with every mechanical field
   (below), one row per breakout, and leaves each judgement field `null` or an empty list. A file
   that already exists is left alone.
2. Fill in the PAPS file, then the Topic Map, then the Pattern Read (it names the topics). Write
   only the `null` and empty judgement fields; never retype a pre-filled value.
3. `goldmine_build.py check-reads <project>`. On FAIL, fix the named rows and run it again. The
   dashboard is only built from reads that passed. A pass also writes the Proven Hooks file (4).

## Rules for all three

- **Read, never invent.** Every value comes from the reel's own caption, transcript or on-screen
  text in the packet. Where the reel genuinely does not say something, the field is `null`.
- An empty `transcript` means there is no usable speech (music-only, or not transcribed). Read the
  caption, and say so in `source_surface`.
- Plain English. No em or en dashes. Short lines: these render in a dashboard.
- Frozen: a later re-read is a new dated file, never an edit of an old one.
- Mechanical fields (`shortcode`, `handle`, `url`, `mult`, `views`, `duration_seconds`,
  `trigger_word`, `trigger_detection_rule`, `popularity_rank`) are copied from the packet
  verbatim. They are never retyped or rounded. The reads step pre-fills them.
- `trigger_detection_rule` names the caption rule that matched. `named_word` is an explicit
  "comment the word X". A name ending in `_weak` is a comment ask with no payoff ("type X if you
  agree"): read it closely, it is usually an engagement ask.

## 1. Lead Magnet PAPS

One row for **every** breakout where the packet says `is_cta: true` (a caption asking for a
trigger-word comment in exchange for something). Non-CTA breakouts are listed by shortcode only.

```json
{
  "_note": "PAPS read of every trigger-CTA breakout in this pull. Mechanical fields are copied from the reads packet; PAPS fields are read from each reel's transcript and caption. An element the reel does not contain is null, never inferred.",
  "generated_at": "2000-01-15T12:00:00Z",
  "window": {"from": "<packet window.from>", "to": "<packet window.to>"},
  "corpus": {"breakouts_total": 12, "cta_breakouts": 7, "non_cta_breakouts": 5},
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
      "mult": 4.2,
      "views": 31500,
      "duration_seconds": 38.5,
      "trigger_word": "GUIDE",
      "trigger_detection_rule": "bare_caps",
      "topic": "Booking discovery calls from Instagram DMs",
      "problem": "Leads go cold in the DMs because the coach answers every message by hand.",
      "agitation": "\"You are losing the ones who were ready to buy while you type.\"",
      "promise": "A DM flow that books the call without you typing a word.",
      "solution_delivery": "A free Notion guide with the five DM scripts, sent by automated DM after the comment.",
      "source_surface": ["spoken", "caption"],
      "popularity_rank": {"rank_by_benchmark": 2, "benchmark_x": 3.1, "rank_by_raw_rate": 4, "comment_rate": 0.0125, "benchmark_unavailable_reason": null},
      "note": null
    }
  ],
  "non_cta": ["Def456UvW", "Ghi789RsT"]
}
```

- `promise` and `solution_delivery` are never null when the reel offers something. If the reel
  truly does not say what, write what the caption says it is ("the link", "the template") and use
  `note` to say the reel does not describe it.
- **Engagement bait is not a lead magnet.** A comment ask with no offer behind it ("comment AMEN",
  "type YES if you agree") keeps its row, with `promise` and `solution_delivery` set to `null` and
  `note: "engagement ask: no offer"`. In the Pattern Read it is `lm_type: "lm_none"` with
  `magnet: "engagement ask"`. **Never invent a lead magnet** to fill the gap.
- `topic` and `source_surface` are never null.
- `topic` is a short plain phrase for what the reel is about (the Topic Map's `angle` may reuse it).
- `agitation` may quote the reel. Quote exactly or not at all.
- `corpus` counts must match the packet (`breakouts`, `cta_breakouts`).

## 2. Topic Map (`goldmine-topic-map/1`)

The engine's themes are broad bins. This read finds the real topics inside them.

```json
{
  "schema": "goldmine-topic-map/1",
  "pull": {"manifest": "<packet manifest>", "n": 12},
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
  "pull": {"manifest": "<packet manifest>", "n": 12, "cta_n": 7},
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
- `lm_types` is required only when the pull has CTA breakouts. With none, it may be empty.
- An engagement ask (no offer) is `lm_type: "lm_none"` and `magnet: "engagement ask"`, with
  `{"id": "lm_none", "name": "Engagement ask", "summary": "A comment ask with no offer behind it."}`
  in `lm_types`.
- **Threads** group related topics. Every Topic Map topic sits in exactly one thread.
- Ids: formulas `f_<word>`, magnet types `lm_<word>`, threads `th_<word>`; unique within the file.

## 4. Proven Hooks (`goldmine-proven-hooks/1`), written by check-reads

Not a read: `check-reads` writes it on a pass, as `reel-build/Proven Hooks - <n> - <date>.json`
(the packet's name with "Goldmine Reads Packet" swapped for "Proven Hooks"), and records that name
in `reel-build/goldmine-run.json` under `reads.proven_hooks`. Find it by that key, never by the
newest file name. It holds the top 3 breakouts by `mult` (ties on shortcode; fewer when the pull
has fewer than 3):

```json
{
  "schema": "goldmine-proven-hooks/1",
  "generated_at": "2000-01-01T00:00:00Z",
  "packet": "<reads.packet>",
  "patternread": "<reads.patternread>",
  "hooks": [
    {"shortcode": "Abc123XyZ", "handle": "examplecreator", "url": "https://www.instagram.com/reel/Abc123XyZ/",
     "mult": 4.2, "views": 31500, "opening_line": "<the manifest's hook_line>",
     "formula": {"id": "f_if", "name": "Qualifier open", "template": "If you [are / do X]..."}}
  ]
}
```

## What check-reads rejects

Missing files or invalid JSON; a missing CTA row, a row that is not a breakout, or a row for a
breakout that is not a CTA (a stale row); a PAPS file that is not the newest `Lead Magnet PAPS`
file in `reel-build/` (the dashboard reads the newest); a null `topic` or `source_surface`; null
`promise` or `solution_delivery` on a row the Pattern Read does not mark `lm_none`; an `lm_none`
row whose magnet is not "engagement ask"; `corpus` counts that do not match the packet; a wrong
`schema`; a breakout with no Topic Map or Pattern Read row; an unknown topic, formula or magnet
type id; a CTA row without `lm_type` and `magnet`; empty `lm_types` when there are CTA rows; a
theme that is not an engine theme; a topic in zero or two threads; duplicate ids.
