# styletemplate contract — build a composition FROM a style-spec

> Companion to `scripts/styletemplate.py`. `plan` → `build` → `check`. Optional: the
> decode is complete without it. A build needs a design-system entry
> (`designsystem-contract.md`) and a local copy of `gsap.min.js`.

```
styletemplate.py plan  <style> --inputs inputs.json [--stamp MM.DD.YY]
styletemplate.py build <plan_dir> --inputs inputs.json --gsap <local gsap.min.js>
styletemplate.py check <build_dir>
```

## Exit codes

`0` ok · `1` hard fail · `2` **written, but a human gate is required** (the
`stylespec.py merge` meaning). There is deliberately **no `--yes` flag**: a flag
that skips the gate is what makes clones fail silently.

## The load-bearing claim

`build` is a **pure function** of (spec, plan, media bytes). All judgment,
interaction and defaulting lives in `plan`; `build` never asks and never guesses.

## Read-only on the style directory

The spec is opened read-only; no write path into the style dir exists. Output goes
only to `<data_dir>/builds/<slug>-<MM.DD.YY>-<nn>/`.

## Provenance tagging

Every value in the build plan carries `from-spec` / `derived` /
`default-for-UNKNOWN` / `generator-invented`. A generator cannot emit UNKNOWN into
HTML, so without tagging every provisional rule silently becomes a confident number.
Tagging makes "the generator is the author" **countable**; that count is the rung-5
result.

## OBS / PARAM partition — the highest-consequence guard

`transitions[].instances_s`, `panel_content_types[].segments_s`,
`pacing.swap_times_s`, `canvas.layout_timeline` and `beats[].params.start_s` record
**where something happened in a source reel**. A generator that replays them
produces the source's structure stretched over new words, which looks on-style and
passes most reproduction metrics *because it is the source*. So the spec is
partitioned at load:

- `OBSERVATION_KEYS` / `OBSERVATION_PATHS` — quarantined; readable only through a
  declared derivation.
- `PARAMETER_KEYS` — durations of a *mechanism* (how long a tween runs). Readable.
- **Any unclassified timestamp-bearing field is a HARD FAIL.**

`plan` also reports caption starts that equal an observed timestamp. Rebuilding a
source against its own transcript produces these legitimately, so they WARN.

## Effective parameters — one value per field

The same number can live in `params`, `variants[0].params`, `resolution[].default`
and a tween literal. Precedence, declared once: **`resolution` wins for
range/choice · `compute` for derived · `condition` for invariant · `params` only
where no resolution targets the field.** Materialised to `effective-params.json`,
the file a human should review.

Two guards on `invariant`: a **type guard** (a string into a dict/list field, e.g.
a merge note in the value slot) and a **vocabulary guard** (prose-shaped: >4 words
or mentions "source"). A rejected value is never written; it becomes an
`interpretations_required[]` entry and forces exit 2. A `range` whose scalar
`default` targets a list field is a tolerance, never written.

## Ingredient gate — runs first

`inputs.json` must name a file per required ingredient (missing = exit 1), plus
mechanical corroboration: existence; `in2` is a **rate** (≥ 1 artifact per 4 s of
proof); `in4` transcript end vs footage duration (right shape, wrong content =
perfectly out-of-sync captions); `in10` whoosh 0.4–2.0 s. The shopping list printed
on failure is **generated from `ingredients[]`**. The `in4` transcript uses the
`{"words":[{text, startTimeMs, endTimeMs}]}` shape.

## `artifact` rules — acknowledge and exclude

`plan` refuses while any rule carries an unacknowledged `resolution.kind: artifact`.
Naming it in `inputs.artifact_acknowledged` omits its beat and prints `!! THIS BUILD
HAS NO <id> BEAT`.

## Caption engine

Grouping runs in **integer ms**; placement in **integer frames**, so groups are
contiguous with zero float drift. Four break conditions: pause ≥
`group_break_pause_ms` · word cap · hard cap `max_group_duration_ms` · **and the
measured median hold**, which is the one that matters (the hard cap is an outlier,
not the shape of a group). A numeral is never split across groups. Hold scales
inversely with the new transcript's wpm, clamped. Caption tracks alternate
`20 + (i % 2)` so many groups never walk into other lanes.

Recurring beats (`anchor.type: recurring`) get claim-payoff **candidates** (position
window, big numeral, long hold, superlative); `plan` never chooses. An unconfirmed
recurring beat is exit 2. The position window is tagged `generator-invented`.

## `build`

Emits a standalone HyperFrames composition: sized root in `<body>`, one paused
timeline at `window.__timelines['main']`, media copied into `assets/`.

**Look comes from the design system; size comes from the spec.**
`palette.bg.page`, `palette.ink.primary`, `type.body.family`/`weight` resolve through
`designsystem.resolve_role`. Caption size and position come from the **one**
`typography.roles` entry marked `caption_default: true`: its `size_pct_of_width` and
`baseline_y_pct_of_height`. **This fails closed.** No such role, more than one, or a
missing or non-numeric field (including `UNKNOWN`) exits 1 with an error naming the
role and field. There is no literal fallback: a guessed size is a silently wrong
frame. (Size is `edit`; the registry deliberately has no size role.)

**GSAP is a required local file.** `--gsap <path>` must name a `gsap.min.js` already
on the computer; it is copied to `assets/gsap.min.js` and loaded from there, and its
sha256 goes into `build.json`. A link (`scheme:` or `//`) or a missing file is
refused, and `build` will not run without the flag. Nothing is ever downloaded.

**Fonts are vendored, never CDN.** Every declared family is copied into `assets/`
and emitted as `@font-face … url()`. A missing file is exit 1: an offline render
otherwise exits 0 in the fallback font and corrupts geometry rules that hug text
ink boxes.

Tweens are a **table of Python emitters**, not string substitution: decoded
`tween_recipes` are often prose-contaminated, and `hyperframes lint` checks
structure, not JS semantics. Entrances emit `fromTo` with an explicit visible end
state (cold render workers otherwise encode the element invisible).

Cumulative word reveal uses `tl.set()` on `display` (a set at a timeline position,
not a tween), because the line must grow and re-centre and an `autoAlpha` span still
takes its box. The separating space lives **inside** the word's span (`&#32;word`),
or a hidden word's space is still laid out and words render glued together; a
numeral continuation takes no separator.

## `check`

Pure Python, no Node; runs at the end of `build`.

1. **wrong-`data-start` detector**: `round(float(data-start) * fps)` equals the frame
   the plan committed to, for every clip
2. exactly one `gsap.timeline({paused:true})`, registered under the root's
   `data-composition-id`
3. determinism bans: `setTimeout`, `setInterval`, `Math.random`, `Date.now`, `fetch`,
   `requestAnimationFrame`, `new Promise`
4. `class="clip"` on every element carrying `data-start`
5. **no remote `src`** (anything not under `assets/` is an error), and every local
   `src` resolves on disk
6. every `font-family` has an `@font-face` whose file exists
7. every GSAP selector id exists in the DOM (GSAP silently no-ops on a missing one)
8. same-track clips do not overlap

A negative test that mutates nothing passes for free: assert the mutation applied
before trusting a green result.

## Fixed constants (not read from the spec yet)

Canvas 720×1280, default fps 30, the ingredient ids `in1`/`in2`/`in4`/`in10`, the
caption-engine fallbacks and the claim-payoff window are constants in the script.
They are listed here so nobody mistakes them for spec values.

## Still to build

Shot plan / panel geometry (modes, skins, cards, swaps) · an sfx clip before every
swap · preset staleness keyed on a rules fingerprint · `check --twice` (byte-diff a
re-build).
