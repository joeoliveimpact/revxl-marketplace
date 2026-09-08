# State schema ... `state/<brand>.json`

The single per-brand journey record. **Every skill reads it at start and writes
its declared keys at end.** Nothing else in the plugin persists journey position.
Routing (`journey-map.md` + `routing.md`) is computed FROM this file: if a fact
is not in state, the compass does not know it.

**Rule zero: no invented keys.** A skill may only write keys this schema declares
for it (see the ownership table). Need a new key? Add it HERE first (additive
minor bump), then write it. Unknown keys found in a file are preserved untouched,
never deleted, never "cleaned up."

## Locations

| Path | What |
|---|---|
| `~/.claude/shortform-superengine/.superengine` | Install marker (JSON): `version`, `onboarded_at`, `transcription_chain`, `connections`, `voice_sources`, `voice_confidence`, `active_brand` (authoritative), `brand` (legacy alias, same value), `brand_brain`, `competitor_pulse`, `tier` |
| `~/.claude/shortform-superengine/state/<brand>.json` | THIS schema, the per-brand journey state |
| `<project>/` | The client's project directory: `analysis-data.json`, the roadmap, `visuals/`, `scripts/`, `content-plan-<week>.md`, `brain-pulls/`, `history/`. `project_path` in state points at it |
| `~/.claude/revxl/<brand>/voc/` | brand-brain's output. **Read-only from this plugin's point of view**: `voc.present` is derived from it |
| `~/.claude/revxl/<brand>/subject/` | subject-matter's output (0.5.0). `subject.present` is derived the same way |
| `~/.claude/socialcrawl-superengine/.superengine` | Read-only probe: is socialcrawl-superengine installed (gate DEEP PLAY, edge F9)? Never written by this plugin |
| `~/.claude/revxl/teach-level` | The family teach dial. Authority for voice level, not state (`teach-mode.md`) |

`<brand>` = normalized brand slug, **same convention as brand-brain**
(`~/.claude/revxl/<brand>/voc/`): lowercase, alphanumeric only, no separators
("Maria G Fit" -> `mariagfit`). One client = usually one brand; an agency = N
files, fully isolated.

## Schema (version 1.0)

```jsonc
{
  "schema_version": "1.0",          // additive-minor: new optional keys bump 1.x; never remove or rename in 1.x
  "brand": "<slug>",                // this file's own slug; the marker's active_brand says which file is live
  "created_at": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DD",       // every writer refreshes this

  // ---- setup (owner: onboarding) ----
  "setup": {
    "complete": false,
    "keys_present": {
      "socialcrawl": false,         // the key resolved through the ladder, never the key itself
      "vault": false                // workspace-superengine's callee owns the Vault key; this is presence only
    },
    "tools": {
      "yt_dlp": false,              // harvest-only since 0.4.0
      "groq": false,
      "whisper": false
    },
    "socialcrawl_superengine_installed": false,  // the DEEP PLAY gate probe, refreshed on each onboarding run
    "ws_superengine_version": null  // the loaded workspace-superengine version at last check, or null
  },

  // ---- direction (owner: shortform-start) ----
  "goal": null,                     // "make-a-reel" | "plan-the-week" | "read-my-results" | "read-the-field" | "set-up"
  "mode": "field-first",            // "field-first" | "subject-first" ... never silently switched
  "project_path": null,             // absolute path to the client's project directory (onboarding seeds, cross-reference confirms)

  // ---- FIELD (owner: competitor-cross-reference) ----
  "analysis": {
    "date": null,                   // YYYY-MM-DD of the last completed run; the 30-day F6 band reads the newer of this and pulse.last_run, the 90-day re-run reads this alone
    "n_competitors": null,
    "themes_set": false,            // true once theme derivation wrote analysis-config.json
    "resume": null                  // {"checkpoint": 2|3, "note": "<one line>", "opened": "YYYY-MM-DD"} or null ... the F1 park pointer
  },

  // ---- VOICE (no writer: derived on read) ----
  "voc": {
    "present": false,               // DERIVED from ~/.claude/revxl/<brand>/voc/ at read time. NEVER written by any skill
    "refreshed_at": null            // DERIVED: the newest mtime under that directory, formatted YYYY-MM-DD, local date; older than 7 days = stale (F7)
  },

  // ---- SUBJECT (owner: subject-matter) ---- 0.5.0, present but unwritten until then
  "subject": {
    "present": false,               // DERIVED from ~/.claude/revxl/<brand>/subject/ the same way voc.present is
    "n_notes": null,
    "refreshed_at": null
  },

  // ---- MAKE ----
  "scripts": [                      // owner: reel-scripter, append-only
    // {"slug": "<slug>", "angle": "<one line>", "source": "field"|"plan"|"subject"|"pulse", "date": "YYYY-MM-DD"}
  ],
  "angles_unpicked": [              // owner: reel-scripter ... the Step-1 angles the client did NOT take, so "script the next angle" survives a session boundary
    // {"angle": "<one line>", "from": "<slug or plan week>", "opened": "YYYY-MM-DD"}
  ],
  "plan": {                         // owner: content-plan
    "week_of": null,                // YYYY-MM-DD, the Monday of the planned week
    "slots": null,                  // integer: posts allocated this week, from the client's real 90-day cadence
    "path": null,                   // <project>/content-plan-<week>.md
    "ideas_unscripted": []          // ["<idea id or slug>"] ... dedupe source for the next pool, drained as scripts[] grows
  },

  // ---- READ (owner: own-content-analysis) ---- 0.5.0, present but unwritten until then
  "own_read": {
    "last_run": null,
    "path": null                    // <project>/own-read-<date>.md
  },

  // ---- PULSE (owner: competitor-pulse) ----
  "pulse": {
    "scheduled": false,
    "day": null,                    // lowercase weekday, e.g. "monday"
    "last_run": null,               // YYYY-MM-DD, local date
    "last_snapshot": null           // path under <project>/history/
  },

  // ---- every skill ----
  "completed_skills": [],           // append the skill name on every completed run
  "open_loops": [],                 // [{"skill", "note", "opened"}] ... unfinished business the compass surfaces
  "declined_offers": [],            // [{"offer", "date"}] ... offer-once discipline
  "teach_level": null               // mirror of ~/.claude/revxl/teach-level at last read. Convenience, not authority
}
```

## Read/write contract

1. **Read at start.** Every skill loads the active brand's file (create it from
   the template above when absent) and re-reads `~/.claude/revxl/teach-level`.
2. **Write at end.** Only your owned keys, plus always: `updated_at`, a
   `completed_skills` append, and any `open_loops` you opened or closed.
   Exception: read-only skills. shortform-next writes nothing, not even
   updated_at or completed_skills, because the compass may be called many
   times in one session and must never alter the record it reads. One more
   exception: the F7 decline entry is written at Step 0c, the moment the client
   proceeds without the refresh, not at the end, so an abandoned run still keeps
   the decline.
3. **Append, never overwrite** arrays (`scripts`, `angles_unpicked`,
   `open_loops`, `declined_offers`, `completed_skills`).
4. **`voc.present` and `subject.present` are DERIVED on read, never written.**
   Check the directory; `refreshed_at` is the newest mtime inside it.
   brand-brain writes nothing in this file, so there is exactly one answer to
   "does this client have a voice guide": the disk.
5. **Staleness is computed, never stored.** Compare `analysis.date` and
   `voc.refreshed_at` against today at read time using the constants below. F6
   has two clauses and they read different dates: the 30-day band reads the
   NEWER of `analysis.date` and `pulse.last_run` (a null `pulse.last_run` counts
   as over 30 days), and the 90-day full re-run reads `analysis.date` alone,
   because a pulse refreshes the field, it never rebuilds the baseline. A null
   `analysis.date` never fires the 30-day band; the unset clause covers it.
6. **Multi-brand.** Skills operate on the marker's `active_brand`; switching
   brands = switching files, no shared state. A brand name in the client's
   message that does not match `active_brand` STOPS the run and offers the
   switch. Never silently report another brand's numbers.
7. **Schema-version bump on new keys.** Any writer that adds a key introduced
   after the file's stamped `schema_version` also bumps `schema_version` to the
   current version, so the file stays honest about the shape it holds.

## Ownership table (who writes what)

One writer per key. A skill not named here does not write that key.

| Key | Writer |
|---|---|
| `setup.*` | onboarding only. shortform-start (first run, migration) and competitor-pulse (its marker fallback) may SEED setup.* when either CREATES the file, and neither overwrites it afterwards. `socialcrawl_superengine_installed` and `ws_superengine_version` are seeded by onboarding and shortform-start only (competitor-pulse runs no probes); the deep-play gate reads the disk, never these mirrors |
| `goal`, `mode` | shortform-start (and any skill on an explicit plain request, which then says so) |
| `project_path` | onboarding seeds it, competitor-cross-reference confirms or corrects it. shortform-start (first run, migration) and competitor-pulse (its marker fallback) may SEED project_path from the marker's `competitor_pulse.project` when either CREATES the file, and neither overwrites it afterwards |
| `analysis.*` (incl. `analysis.resume`) | competitor-cross-reference only. shortform-start (the E18 migration) and competitor-pulse (its marker fallback) may SEED analysis.* at file creation, from an `analysis-data.json` already on disk, and neither overwrites it afterwards |
| `voc.present`, `voc.refreshed_at` | **nobody.** Derived on read from `~/.claude/revxl/<brand>/voc/`. brand-brain writes NOTHING in this file |
| `subject.*` | subject-matter (0.5.0); `present` derived on read the same way `voc.present` is |
| `scripts[]`, `angles_unpicked[]` | reel-scripter only |
| `plan.*` | content-plan only (NOT reel-scripter: the topic-pool mode moved out at 0.4.0) |
| `own_read.*` | own-content-analysis (0.5.0) |
| `pulse.*` | competitor-pulse only. shortform-start may SEED pulse.* from the marker's `competitor_pulse` block when it creates the file (first run, migration) and never overwrites it afterwards |
| `teach_level` | every skill (mirror of `~/.claude/revxl/teach-level` at last read; the file is authority) |
| `completed_skills`, `open_loops`, `declined_offers`, `updated_at` | every skill |

> **Marker (`.superengine`):** owned by **onboarding**. It writes `active_brand`
> (authoritative) and keeps `brand` as a legacy alias holding the same value, so
> 0.3.4 readers keep working. `shortform-start`'s migration reads `active_brand`,
> then `brand`, then the state-directory scan, then asks once, and may write `active_brand` when it was absent
> or null. So may the ask-once rung of any skill that resolves the brand
> (competitor-cross-reference Step 0a, competitor-pulse State), write-if-absent
> only, never an overwrite. Those are the only writers.
> **Migration (first run of shortform-start on a marker-only home):** the
> marker's `competitor_pulse` scheduling block
> (`{scheduled, cadence, runtime, project, last_run}`) is copied INTO
> `state.pulse` and the marker copy is thereafter **ignored**, never re-read and
> never deleted. A migrated home is never re-offered the pulse schedule it
> already accepted.
> The marker's competitor_pulse.project seeds project_path at creation
> when it is set; competitor-cross-reference still confirms or corrects it.
> **`voc_present` in the marker is vestigial** from 0.4.0: onboarding stops
> writing it, its verify step drops it, and nothing reads it. An existing value
> is left in place (rule zero) and never trusted; `voc.present` is derived.

## Staleness constants

| What | Stale after | Edge |
|---|---|---|
| `analysis.date` | 30 days, measured against the newer of `analysis.date` and `pulse.last_run`; full re-run at 90 days, measured against `analysis.date` alone | F6 ... the pulse at 30 days on the newer date, a full cross-reference re-run at 90 on `analysis.date` |
| `voc.refreshed_at` | 7 days | F7 ... offer a brand-brain refresh, once per journey |

The F7 decline is one `declined_offers` entry,
`{"offer": "voc_refresh:<the stale voc.refreshed_at>", "date": "YYYY-MM-DD"}`,
where the `voc_refresh:` key carries `voc.refreshed_at` in the same YYYY-MM-DD
local-date form the schema declares above. The entry is
written by whichever skill made the offer (reel-scripter Step 0c, content-plan
Step 0) when the client proceeds without refreshing. The compass reads it and
suppresses the F7 line while it is there; the compass writes nothing itself, so
an offer declined at the compass is only recorded once one of those skills acts
on it. A later refresh moves `voc.refreshed_at`, so the next stale window gets
its own entry and its own single offer.

## Versioning

`schema_version` follows additive-minor: 1.x changes may ADD optional keys only.
Removing or renaming a key = 2.0 plus a migration note in this file. Skills
tolerate missing optional keys (treat as null) and never crash on an older file.
`subject` and `own_read` are declared here at 1.0 and stay null until 0.5.0
installs their writers.
