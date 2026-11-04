# designsystem contract — the swappable LOOK layer

> Companion to `scripts/designsystem.py`. Sibling of `stylespec-contract.md`: a style
> spec says how a video is CUT, a design system says how it LOOKS. The registry lives
> at `<data_dir>/designsystems/` (config `designsystem.registry_dir`). **It ships
> empty.** Entries are authored per workspace; with none, `list` says so and exits 0,
> `index` writes an empty index, and `validate --all` exits 1 (nothing to pass).

## What a design system is here

An editing style owns cut timing, caption grouping, beat structure and motion. A
design system owns palette, type, radii, border weights, spacing and panel margins.
The split is per rule, in the spec as `layer` (`edit` / `look` / `both` / `ask`).

Reskin depth is deliberately bounded:

- **Motion has no roles.** Easing and duration ARE the editing style. A design
  system's `--dur-*` / `--ease-*` are not consulted.
- **Type SIZE has no roles.** `size_pct_of_width` stays `edit`: a caption's size
  relative to the frame is what makes the composition read.

Both exclusions are structural: the entry schema is **closed**. An unknown role key
or an unknown top-level block is an ERROR, because the alternative is silence.

## Two kinds, and the one hard rule

| kind | meaning |
|---|---|
| `base` | selectable as a build's look |
| `enclave` | **never** selectable; paints only the elements it owns (e.g. a product UI shown on screen) |

**No value ever falls back from one entry to another.** Gaps close *inside* an entry:
alias a sibling role, or omit and don't draw the element. That makes cross-system
colour bleed structurally impossible.

## Entry shape

```
{ registry_version, id, name, kind, reference_width_px, authored, provenance,
  source_files[{path, sha256, read}], exclusive_colors[], owns_nouns[],
  type_policy?, geometry_policy?,          # enclaves: "inherit_base"
  palette{}, type{}, geometry{}, effect{}, # values, keyed by role
  fonts[{family, weights, styles, files, license}],
  absent{role: "omit" | "alias:<role>"}, notes }
```

Every value is `{v, from, note?}`. **`from` is required**: a value with no recorded
source is unreviewable. The CSS-var-to-role mapping lives inline next to the value.

| provenance | meaning |
|---|---|
| `authored` | `v` came straight from a source token |
| `derived` | a person computed or chose `v` from the source (recorded in `from`) |
| `aliased` | role absent; resolves to a named sibling **in the same entry** |
| `omitted` | role absent; the element is **not drawn** |

There is no "inherit", no "default", no implicit fallback. **Completeness
invariant:** every role appears in exactly one of {a value block, `absent`}, so a
typo'd role is an ERROR, never a silent absence.

## Roles — 36, of which 10 required

Palette 15 · type 10 · geometry 8 · effect 3 (the `ROLES` table in the script, each
with a one-line purpose). Every role traces to a `look`/`both` field in a style
spec. The required set is the floor a thin real-world system can clear, so
"required" never means "unusable".

**No spacing ramp is stored.** Two systems' `--sp-2` can mean 16px and 8px; storing
ramps imports that collision. Only what a video places is stored: a panel margin and
a base step (plus optional tight/loose).

## One length unit

Every length is a **float percent of output width**, suffix `_pct_w`, converted once
at authoring time against a required `reference_width_px`. `show --width N` emits a
`*_px` sibling for each, so no consumer re-derives the scaling. Special value
`"full"` (pill radius) means half-height. Vertical geometry is `edit` and never
enters the registry.

## Fonts are a correctness gate

An offline render with a CDN-only font **exits 0 entirely in the fallback font** and
corrupts geometry that hugs text ink boxes. So:

- families are vendored as woff2 under `<registry_dir>/_fonts/<Family>/`;
- builds emit `@font-face` with the vendored `url()`; nothing loads from a CDN;
- `validate` **exits 1** on a declared family with no file, and on a `type.*.family`
  used but not declared in `fonts[]`.

Authoring rules: **a font STACK is not a font** (`system-ui, …` resolves differently
per machine; pin one family and record the substitution in `from`). **Declare the
font's REAL weight**: declaring 900 on a one-weight face makes the browser synthesise
a fake bold that looks nearly right.

## Enclaves

1. `kind: enclave` cannot be passed as a build's look.
2. `exclusive_colors`: `validate` fails any *other* entry that contains one.
3. No role is named after a colour (no "coral", no "gold"), so unrelated
   similar-looking colours have nothing to collapse into.

An element classified `enclave` with no enclave loaded is a **hard error, never a
fallback**.

## Hand-authored, not parsed

`scaffold --css <path> [--scope <selector>]` prints a stub with the parsed candidates
listed and **writes nothing**. Mapping a CSS var to a semantic role is a judgment
(which of `--accent-200..700` is `accent.primary`?), and a parser answers
confidently and wrongly. Some systems simply have no token for a 9:16 panel margin;
a parser would pick a wrong one.

**Drift is a WARNING** (a comment edit must not break a build):
`source_files[].sha256` is re-hashed on every `validate`; `--reseal` rewrites the
hashes once a person has confirmed the diff is not semantic.

## Reporting

`capabilities <id>` ends with **LOUDEST CONSEQUENCES**, naming the *visible* result of
each alias ("every serif caption role renders sans"), because "10 aliased" is a
number people skim past.

## The look-map + `validate-map`

A registry entry says what a system *has*, never which **field of which rule**
consumes it. That join lives in `<style-dir>/look-map.json`, so the approved spec is
untouched. Four classes, one per field, no defaults:

| class | meaning |
|---|---|
| `map` | the design system supplies it; `roles[]` must be real `ROLES` keys |
| `edit` | style-owned; the design system may **not** touch it |
| `observation` | measured evidence; a generator must NEVER read it as an instruction |
| `omit` | intentionally unmapped, `reason` required |

`designsystem.py validate-map <style-slug>` is fail-closed both ways: every
`look`/`both` rule must be in the map; every field of those rules must carry exactly
one class; a map entry for a non-look rule or a field path the rule lacks is an
ERROR; every classified path must `resolve_field()`; `map` with no roles, an unknown
role, or `omit` without a reason fail. Required roles that no rule reaches are
WARNINGS; declared `known_gaps` are listed rather than papered over.

## Exit codes

`0` ok · `1` fail · `2` reserved for "written, human gate required".
