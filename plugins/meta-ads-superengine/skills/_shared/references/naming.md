# Naming — the parseable grammar

One naming convention across campaign → ad set → ad. It is a **grammar, not a
suggestion**: `meta-ads-performance-review` parses pasted CSV exports by it
(split on `-`, fixed field order), and the creative registry in state keys off
the same IDs. campaign-plan writes these names into its artifact;
launch-runbook has the coach enter them verbatim.

Rules: lowercase · hyphens only (no spaces/underscores inside a field) ·
fields in fixed order · never rename a live object (breaks parse history —
new object = new name).

## Campaign

```
<brand>-<objective>-s<stage>-<yyyymm>
acme-coaching-leads-s1-202607
```

| Field | Values |
|---|---|
| brand | the brand slug (state file name) |
| objective | `leads` \| `sales` |
| stage | 1–4 (spend stage at creation — not edited on stage advance) |
| yyyymm | creation month |

## Ad set

```
<audience>-<entered>
broad-202607           ← the Stage-1 default (the only ad set)
pack-20260812          ← a Piliero pack: new-concepts ad set, dated (Stage 3 pattern)
```

`audience`: `broad` | `pack` | `retarget` (high-ticket exception only) |
`engaged` (omnipresent lanes, Stage 4).

## Ad

```
c<N>-<format>-h<N>-v<yyyymmdd>
c3-vsl-h2-v20260716
```

| Field | Values |
|---|---|
| c\<N> | concept ID — **must match `creatives[].id` in state** (the registry join key) |
| format | `static` \| `video` \| `ugc` \| `vsl` \| `carousel` |
| h\<N> | hook variant number (h1 = original) |
| v\<date> | version date — a replaced/refreshed creative bumps the date, never edits in place |

## Parse contract (what performance-review relies on)

- Split any name on `-`: campaign yields `[brand, objective, stage, month]`
  (the BRAND slug may itself contain hyphens — parse stage as the `s\d`
  token, objective = the single `leads|sales` token just before it, brand =
  everything before that).
- Ad names yield `[concept, format, hook, version]` — concept ↔ state
  registry, format ↔ dimensional-test axes, hook ↔ CT-Tool variants.
- Anything that doesn't parse gets reported as "unnamed — can't attribute
  this row to a concept" and excluded from per-concept verdicts (never
  guessed).

## Artifacts (files this plugin writes)

Follow the workspace convention: `<Thing> - <Doc Type> - MM.DD.YY.md`, saved
under the project dir (campaign plans, question sets, scripts). State stores
the path, the coach owns the file.
