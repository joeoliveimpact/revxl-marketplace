# Teach-mode v2 — one dial, three levels, two vocabulary axes

The failure this fixes (verified across the superengine family): existing
teach mechanisms gloss **tech-speak only** — a "beginner" still gets
CBO/CAPI/lookalike/awareness-ladder raw. Coaches here are learning Claude,
plugins, AND Meta ads simultaneously. Two vocabulary axes, both glossed.

## The dial

| Level | Claude/tooling terms | Meta-ads/strategy terms | Why-teaching |
|---|---|---|---|
| `new` (default) | Glossed first use + "what this means for you" | **Deep-gloss contract below** | WHY behind each move, 8th-grade language |
| `learning` | Assumed | Glossed first use per session (one-liner tier) | Brief why on major decisions |
| `pro` | Assumed | Assumed | None — terse operator voice |

## The `new` deep-gloss contract (fires ONLY at `new`)

The coach audience does not know ROI, ROAS, clickthrough, static ad — assume
ZERO ads vocabulary. At `new`:

1. **Plain-English-FIRST ordering is mandatory.** Explain the thing in plain
   words → THEN name the term → one-line gloss → "what this means for you"
   wherever the consequence isn't obvious. Never lead with the term. Never
   strip the real vocabulary either — translate alongside it so the terms
   get learned.
2. **Money/metric terms get a worked micro-example on first use per session**
   (ROAS, ROI, CPL, CPQL, CPM, CTR, breakeven, MER…): use the coach's OWN
   numbers when state has them (`targets`, `setup.price`) — *"your $3,000
   offer closing 1 in 5 calls means a booked call is worth $600 to you"* —
   else generic small numbers (*"you spent $100 and got 4 leads — that's $25
   a lead"*). The `new`-tier entries in `glossary.md` carry these examples.
3. **Deep-tier glosses come from `glossary.md`'s `new`-tier section** where
   one exists; one-liner tier otherwise; inline for unlisted terms (flag for
   glossary addition).

`learning` and `pro` are UNCHANGED by this contract — the one-liner tier and
bare voice respectively. Deep glossing never leaks upward.

## Split-axis rule (ads-expert / Claude-novice)

The dial's two vocabulary columns usually move together ... one level, both
axes glossed the same. But a coach can be expert on ONE axis and new on the
other (the already-running coach who knows CBO/CAPI cold but has never touched
Claude). That persona needs the axes to split.

- **Storage.** The family file `~/.claude/revxl/teach-level` keeps its one word,
  set by the **Meta-ads-familiarity** answer (its family-shared format is
  untouched ... the split lives ONLY here). When the two calibration answers
  DIVERGE, this plugin's own marker records `tooling_level` (the
  **Claude/plugins-familiarity** answer: `new` / `learning` / `pro`). Answers
  match → no `tooling_level` written.
- **Rendering (two axes, two sources).** Meta-ads/strategy terms gloss per
  `teach-level`; Claude/tooling terms gloss per `tooling_level` when it is set.
  Absent `tooling_level` = the axes match, so both render per `teach-level`
  (today's behavior).
- **Calibration mapping.** Setup's two existing questions map one-to-one to the
  axes ("How familiar with Meta ads?" → `teach-level`; "How familiar with
  Claude and plugins?" → `tooling_level` on divergence) instead of collapsing
  to a single level.

## Storage + back-compat (dual-write)

- **Authority:** `~/.claude/revxl/teach-level` — one word: `new` / `learning`
  / `pro`. Family-shared (one dial across all superengines).
- **Legacy dual-write:** on every write, also write
  `~/.claude/revxl/teach-mode` for older siblings:
  `new`→`beginner`, `learning`→`beginner`, `pro`→`off`.
- **Legacy read fallback:** if `teach-level` is absent but `teach-mode`
  exists: `beginner`→`new`, `off`→`pro`. Then write both (migrates in place).
- **Conflict guard:** if BOTH files exist but the legacy `teach-mode` is newer
  (mtime) than `teach-level` AND maps to a different level (a sibling wrote it
  after this file), ask once before overwriting — don't silently clobber a
  level the coach may have just set elsewhere.
- Neither file exists → `new`, and setup's calibration is the natural fix.

## Lifecycle

1. **Calibrate in setup:** two questions — "How familiar are you with Meta
   ads?" / "How familiar with Claude plugins?" → pick the level, save both
   files, explain how to change it.
2. **Re-read at every skill start** (drift guard) — never trust a cached
   value from earlier in the session. Mirror to `state.teach_level` for the
   record; the file is authority.
3. **Change anytime:** the `meta-ads-teach` skill, or a plain request
   mid-session — "plain" (drop a level for the last explanation), "less
   hand-holding" (offer a bump). Session-adjust immediately + offer to
   persist.

## Rendering rules

- **Gloss source = `glossary.md`** — two tiers: one-liners (used at
  `learning`, and at `new` for terms without a deep entry) + the `new`-tier
  deep entries (analogy + worked example + consequence line). Skills pull
  from it, never improvise a gloss (consistent, corrected once). A domain
  term not in the glossary that needs glossing at `new` → gloss inline AND
  flag it for glossary addition in the handback/commit.
- **First use per session** is what gets glossed — not every occurrence.
- **Next-Moves blocks render per level** (`routing.md` rule 4).
- **`new` additionally gets:** the "what this means for you" consequence line
  wherever the implication isn't obvious, and the WHY before each prescribed
  action (the 72h lockout speech, the broad-targeting explanation).
- **Numbers stay honest at every level:** DIRECTIONAL canon facts are phrased
  as direction ("raise gradually, roughly 10–20% every couple of days"), never
  fake precision — see `canon.md`.
- `pro` is terse but never *less safe*: gates, refusals, and compliance
  warnings render at full strength at all levels.
