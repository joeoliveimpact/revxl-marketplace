# stylespec contract — style-spec.json, the style library, and how consumers load it

> Companion to `scripts/stylespec.py`. Also the **consumer handoff spec**: any editing
> session that wants to "edit in style X" reads this file plus that style's
> `style-spec.json`. Siblings: `styleframes-contract.md` (measurement),
> `designsystem-contract.md` (the look layer), `styletemplate-contract.md` (builds).

## Contents
- What a style system is
- Library layout
- Sources — local files only
- Schema (field groups)
- Layer + resolution (the templatizer fields)
- Merge (refine with a second reel)
- The confirmation ladder
- Determinism requirements
- Consuming a style system
- Validation gates (fail-closed)
- Retention

## What a style system is

A decoded **editing design system**: every rule needed to recreate a reel's editing
on new footage (layouts, typography, colour, motion, pacing, structure, assets,
audio), split into two kinds of fact:

- **Measured facts** (scripts produce): cut timestamps, pacing stats, palettes,
  loudness. No confidence field; they are computed.
- **Judgment rules** (Claude produces by reading frames). Every one MUST carry:
  - `evidence[]` — frame paths **relative to the style dir**
    (`sources/src-01/frames/base_0012_t8000.jpg`). ≥1; validate checks they exist.
  - `confidence` — `provisional` (1 source) | `confirmed` (2+ sources).
  - `observed_in[]` — source ids, a subset of `spec.sources[].id`.

**`UNKNOWN` is a legal value.** The spec never guesses. Micro-bursts shrink the
UNKNOWN set (durations measured, easing *classed* `linear | power-out |
back/elastic | UNKNOWN`), never eliminate it. Audio `character` fields are
**HUMAN-INPUT**: the person describes the music/SFX feel in one line at the review
gate, or marks `n/a`. Nothing in the decoder listens to audio.

## Library layout

```
<library>/                        # style.library_dir, "" = <data_dir>/styles
├── index.json                    # rebuilt by `stylespec.py index`
└── <style-slug>/
    ├── style-spec.json           # CANONICAL, undated (it IS the live state)
    ├── <Name> - Style Runbook - MM.DD.YY.md
    ├── heldout.json              # rung-3 frames + verdict slots (`heldout`)
    ├── sources/<src-id>/
    │   ├── source.mp4            # byte copy of the local file (add-source)
    │   ├── source.json           # provenance + fingerprint
    │   ├── frames/  captions/    # styleframes passes
    │   ├── cuts.json  pacing.json  palette.json  audio.json
    │   ├── layout_timeline.json  # Claude's mode-per-second classification
    │   └── transcript.json       # optional, word-level
    └── evidence/                 # contact sheets + sidecar MDs
```

`data_dir` defaults to `editor/style-decoder/` under the workspace. Dated
deliverables follow `[TOPIC] - [Type] - [MM.DD.YY].ext`; state files are undated.

## Sources — local files only

`stylespec.py add-source <slug> <file>` copies a video that is already on the
computer to `sources/src-NN/source.mp4` (byte copy, no re-encode), probes it, and
appends `{id, platform: "local", file, added, duration_s, resolution, fps,
fingerprint{size, duration}}` to `spec.sources` and `source.json`. It refuses a link
(anything with a `scheme://` or `www.`), a missing file, an unreadable video, and a
video already registered (same size + duration). There is no download path.

## Schema (field groups)

Top level: `spec_version` (`"1.0"`) · `style{slug, name, version, status, created,
updated}` · `sources[]` · `canvas` · `transitions[]` · `typography` · `color` ·
`motion` · `pacing` · `structure` · `assets` · `audio` · `ingredients[]` ·
`adapters` · `merge_log[]`. `SPEC_TEMPLATE` in `stylespec.py` is the normative
shape; `init` writes it and a fresh spec passes `validate`.

- **canvas** — `aspect`, `safe_zones_px` (off full-res frames), `layout_modes[]`
  (zones as `rect_pct` [x,y,w,h]), `layout_grammar[]`, an inlined
  `layout_timeline`, `overlay_treatments[]`.
- **transitions[]** — mode→mode `type` + measured `duration_s`.
- **typography** — `roles[]`: each carries `font_guess` **and** `closest_available`
  (a font the build stack has), stroke/shadow/letter-spacing, `size_pct_of_width` +
  `size_metric`, `mode_scope[]`. Exactly one role is the default caption voice and
  carries `caption_default: true` plus `baseline_y_pct_of_height` (the template
  build reads these and fails closed without them). `caption_mechanics` and
  `caption_content_rules` are what you need to *write* new captions in-style.
- **color** — `tokens[]` (hex + role), `skins[]` (zone colours + alternation rule).
- **motion** — `rules[]` and `audio_synced_rules[]`, with `params` incl. measured
  `duration_s` + `easing_class`, and `anchor: word | cut | absolute`. Word anchors
  name the *class* of word, not a timestamp.
- **pacing** — computed: median shot, cuts/10s, histogram, hook-window stats.
- **structure** — `beats[]` (`absolute` second anchors for opens, `proportional`
  % for the CTA, `recurring` + `trigger` for devices that fire on a content
  condition), `patterns[]` and `screens[]` (pass/fail criteria).
- **assets** — `recurring_motifs[]`, `panel_content_types[]`, `panel_treatments[]`.
- **audio** — music presence/ducking (measured), `character` HUMAN-INPUT, SFX
  transient timestamps (measured), loudness.
- **ingredients[]** — the clone's shopping list (footage and assets a new video
  must supply). **An editing session checks this FIRST.**
- **adapters** — `hyperframes{constants, track_map, tween_recipes,
  clip_conventions}` + `human_editor{checklist}`. `track_map` starts empty and is
  filled for the stack that builds.

**Before resolving an anchor conflict, ask whether the beat is anchored at all.**
Two decodes of a device that fires several times per video will always disagree on
a single timestamp; that is a `recurring` beat, not a conflict.

## Layer + resolution (the templatizer fields)

Optional per rule; a malformed one is an ERROR, a missing `layer` a WARNING (the
build treats untagged rules as `ask`).

| `layer` | Meaning |
|---|---|
| `edit` | Design system may not touch it. **All motion timing is `edit`.** |
| `look` | Design system supplies it entirely (skins, treatments, motifs). |
| `both` | Split field by field (role assignment is edit, font and colour look). |
| `ask` | Undecidable; the build asks and saves the answer to a preset. |

`resolution` is a **list** (one rule can be a `choice` about where it applies and a
`derived` about its rect):

| `kind` | Required payload | Meaning |
|---|---|---|
| `invariant` | `field`, `condition[]` | One conditional rule that read as two. |
| `range` | `field`, `default`, `bounds` | Numeric spread; `default` inside `bounds`. |
| `choice` | `field`, `options[]` (2+) | A real either/or: a build parameter. |
| `derived` | `field`, `compute` | Computed from content at build time. |
| `conflict` | — | Unresolved, awaiting the user gate. |
| `artifact` | — | The decode is wrong. Re-decode; do not resolve. |

`field` is dotted (`params.duration_s`) and may select list elements
(`zones[].rect_pct`, `zones[id=caption].rect_pct`), **by id, never position**.
**A field path that resolves to nothing is an ERROR**: otherwise the consumer falls
back to raw `params` and the resolution silently never fires. `conflict: true` must
be set **if and only if** an open kind (`conflict`/`artifact`) is present.

`tween_recipes` are templates, never literals: a numeric literal in a recipe
silently reverts a resolution. Recipes emit `fromTo` with an explicit visible end
state (cold render workers otherwise encode the element invisible). The UNKNOWN
census matches on prefix, so `"UNKNOWN (not measured)"` still counts.

## Merge (refine with a second reel)

`stylespec.py merge <slug> --source <src-id> --candidate <file> [--dry-run]`.
Always dry-run first; merge mutates in place. Per rule id:

- **Match** (every semantic field compatible) → `confirmed`, numerics averaged,
  per-source values in `params_by_source` / `fields_by_source`, evidence and
  `observed_in` unioned, fields the existing rule lacked adopted.
- **New** → appended as `provisional`.
- **Conflict** → existing rule kept, candidate's differing fields in `variants[]`,
  `conflict: true`, exit 2 = **user gate**; the ruling goes in
  `merge_log[].resolutions`. Never silently averaged.

Comparison rules: prose fields (`rule`, `desc`, `pass`, `fail`, `font_guess`,
`content`…) are never compared, at any depth · parenthetical annotations are
stripped before compare · numeric vectors compare elementwise within
`style.merge_tolerance` · tag lists compare as sets · lists of objects compare by
`id` · a side that is absent, `UNKNOWN` or `HUMAN-INPUT` never conflicts. Keep tokens
in token fields and measurement prose in a sibling. Merge bumps the minor version.

## The confirmation ladder

`validate` passing means *well-formed*, not *right*, and not *sufficient*.

| # | Rung | Tests |
|---|---|---|
| 1 | `validate` | Every judgment rule has existing evidence, legal confidence, known sources. |
| 2 | `coverage` | Mechanical completeness: runtime spans, empty groups, unanchored beats, missing fonts/constants/tweens/ingredients, the determinism fields below, plus a full UNKNOWN census. |
| 3 | `heldout` | **Over-fitting.** Score every rule against base frames the spec does NOT cite. |
| 4 | Blind reconstruction | **Transmission.** A fresh subagent reads ONLY spec + runbook + transcript and predicts named frames; every guess is a missing field. |
| 5 | Rebuild test | **Sufficiency.** Build 5–10 s from the spec on new footage, A/B it against the source, record the verdict in `merge_log`. |

`stylespec.py heldout <slug> [--n 10] [--frames a,b]` collects the cited set
(every rule's `evidence[]`, plus `variants[].evidence`) across all rule groups,
picks `min(n, available)` uncited `frames/base_*.jpg` spread evenly across the
runtime, and writes `heldout.json`: the frames, the rule ids, and
`verdicts{frame: {rule_id: null}}`. Claude fills each slot `pass | fail | n/a`;
scoring is judgment, never the script's. `--frames` (a bare frame name or a
style-dir path) refuses any cited frame, naming it, with exit 1. A
`heldout.json` that already holds scores is never overwritten.

Until rung 5 has run once, `status: approved` means "faithfully describes the
source", not "proven to reproduce it". Say so when a consumer loads it.

## Determinism requirements

A spec can pass rungs 1–3 and still let two editors make different frames.
`coverage` gates the fields that decide this:

| Field(s) | Why a description isn't enough |
|---|---|
| inlined `canvas.layout_timeline` (or `layout_grammar_mode_sequence`) | Grammar gives rhythm, not order. A file reference outsources the most consequential fact. |
| `caption_mechanics.grouping_algorithm` + break/duration/word thresholds | "1–3 words per group" is a distribution; thresholds are what new footage needs. |
| `caption_content_rules.lexicon` + `role_precedence[]` + per-role `mode_scope[]` | "Brand nouns render serif" is undecidable without the list and a tiebreaker. |
| `caption_content_rules.transcript_normalization` | **Verbatim means the spoken word, not the ASR token**, or a mis-heard name is burned into frame. |
| per-role `size_metric` | 8 % of width is ~1.5× different as cap-height vs em. |

A catalogue is not a mapping: listing content types without a selection predicate
stays a guess. Never restate a rule in a second place; reference its id (coverage
flags duplicate ids).

## Consuming a style system

1. `<library>/index.json` → slug → `style-spec.json`. Prefer `approved`; say so out
   loud when using a `draft`.
2. Check `ingredients[]` against the footage on hand. A missing required one →
   stop and tell the user what the style needs.
3. Map onto the stack: `typography.roles` → caption classes with
   `closest_available` fonts; `motion.rules` + `tween_recipes` → tweens respecting
   `anchor`; `structure.beats` → beat anchors; `UNKNOWN` easing → stack default,
   noted as a deviation.
4. `pacing` is the rhythm target. Match the distribution, not each number.

## Validation gates (fail-closed)

`validate` exits 1 on: missing group · judgment rule without evidence · evidence
missing on disk · bad confidence · empty or unknown `observed_in` · slug mismatch ·
`approved` with errors. `index` downgrades a failing approved spec to draft.
`status: approved` is only ever set at the user's approval gate, never by a script.

## Retention

Per source after approval: `source.mp4` deletable (fingerprint kept) · frames cited
as evidence KEEP · unreferenced burst frames deletable · `evidence/` sheets, all
JSONs and `heldout.json` KEEP.
