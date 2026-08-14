# Session summary format

Reference for maintainers. The user-facing behavior lives in `/session-closeout` Phase 0.7 (writes the file), Phase 1 (the Checkpoint retrieval header and the 30-day window), Phase 2 (the handoff pointer), and `/session-continue` (reads all three back).

## The one-line version

**One file per session, written at closeout, read by three consumers: a human, the graph, and the next session's kickoff prompt.** The session summary IS the refire prompt. There is no second artifact to keep in sync.

---

## Where the files live

`sessions/` at the workspace root, one file per session:

```
sessions/session-summary-08-14-26.md
sessions/session-summary-08-14-26-1.md   ← second session the same day
sessions/session-summary-08-14-26-2.md   ← third
```

**Naming is a deliberate exception to the house convention.** The house rule is `[TOPIC] - [Doc Type] - [MM.DD.YY]` with spaces and dots. Session summaries use `session-summary-MM-DD-YY` with hyphens instead, because the filename is also a wiki-link target and a machine-parsed handle. Spaces and dots make both worse. This is written down as an exception on purpose so it does not later read as drift.

**Closeout creates `sessions/` if it is missing.** It is not added to `/super-setup`'s scaffold list, because workspaces scaffolded before this feature existed will never re-run setup ... create-on-demand has to work anyway, which makes a setup-time create redundant.

---

## Why one file per session and not an append-only log

Decay has to weight sessions independently. An append-only file has exactly one `date_updated`, and it is always today, so recency weighting cannot tell last Tuesday from this morning. Per-file also gives each session its own frontmatter (`source_count`, `confidence` are per session, not smeared) and a stable wiki-link target.

`Checkpoint.md` stays append-only. That is correct and not a contradiction ... Checkpoint is the terse index, the summary is the expansion.

---

## The frontmatter

Ported verbatim from the second brain's `cascade/AGENTS.md`. Do not invent fields, do not drop fields.

```yaml
---
id: session-summary-08-14-26      # stable slug, matches the filename
tags: [session, episodic, <workspace-slug>]
date_created: 2026-08-14          # the session's date
date_updated: 2026-08-14          # same at write time; only changes on a later correction
source: workspace-canonical
sot_policy: decay
source_count: 1
confidence: 0.8                   # 0.0 to 1.0
---
```

`sot_policy: decay` marks this file **episodic**: recency-weighted, append and decay, never delete, supersession by recency rather than by status flags.

**Episodic and durable never blend.** A session summary records what happened. A decision that should bind every future session is durable and belongs in `RULES.md`, `MEMORY.md` or `GOALS.md` ... never `decay`. `/session-closeout` Phase 2.7 already owns that routing.

---

## Dated H2 headers, inside the file

Every content section is `## [YYYY-MM-DD] <topic>`, even though the filename already carries the date.

**Why the date is duplicated:** graphify chunks at the H2 boundary. The chunk that gets indexed is the header plus the text under it ... the filename is not in the chunk. Put the date in the header and both full-text search and vector search can see it. Leave it out and the chunk is undated.

**Headers are topical, never procedural.**

- `## [2026-08-14] Linear source-of-truth rule` retrieves.
- `## [2026-08-14] Notes` does not. Neither does `Progress`, `Misc`, or `Updates`.

One long section with no H2s averages every topic in it into mush and kills retrieval. Three topics means three headers.

---

## The `## Connections` section

Required at the bottom of every summary. **Be honest about what it does.**

On the `/graphify` skill path it is **mechanically inert.** It becomes an ordinary heading node ... confirmed live. Nothing parses those lines into edges.

Its actual job is **steering the LLM extractor toward the locked verbs**:

```
depends_on   consumes   exposes   integrates_with   runs_on   references
```

Without a Connections block, the generic extractor prompt collapses everything it finds into `references` and `conceptually_related_to`, which is the same as having no edge types at all. **That is a prompt argument, not a parsing one.** Writing the verbs down in the text is what puts them in front of the extractor.

Shape:

```markdown
## Connections

- `depends_on` ... [[session-summary-08-13-26]]
- `consumes` ... handoff.md
- `integrates_with` ... graphify 0.9.42
```

This is the one header in the file that is deliberately neither dated nor topical. It is not content, it is steering.

---

## Wikilinks: structure is free, semantics are paid

**Write that sentence exactly, in these words.** Not "edges are free" ... this project asserted that twice and it was wrong both times. Not "there are no free edges" ... that was the overcorrection.

What is actually true:

- On **graphify 0.9.42**, a free structural pass converts `[[wikilink]]`, `[[wikilink.md]]`, `[text](file.md)` and `[text](./file.md)` into real `references` edges, deterministically, at **`Token cost: 0`**.
- **That pass does not run on the `/graphify` skill path.** That path hands the AST extractor only the `code` bucket, and `.md` is classified as a doc. Free structural edges are a 0.9.42 direct-CLI property, not a property of every route into the graph.
- `graphify` on PATH is 0.8.8, which has no link parser at all. Check `which` and `--version` before making any cost claim about a specific machine.

**Rules that make authored links pay off when the free pass does run:**

- Keep wikilink targets **resolvable to a same-folder sibling, path-relative.** Summary-to-summary links inside `sessions/` qualify. `Checkpoint.md` pointing into `sessions/` does not ... that link is an address for a human and for Obsidian, not a free structural edge. Say so rather than over-claiming.
- **Wikilinks inside fenced code blocks are skipped.** A link that only appears inside a fence produces nothing.

Authored links are worth writing regardless of which path runs, for navigation and for the address they give the next session. They are just not a guaranteed edge.

---

## `Checkpoint.md` keeps its job

The 08.12 question was "index or retire?" and the answer was **neither.** Checkpoint stays the terse burst of what happened. The summary is its expansion.

Checkpoint gains a **retrieval header** with two deliberately separate line types:

| Line | What it is | Failure mode it has |
|---|---|---|
| `**Summary:**` | the **handle** ... the summary's frontmatter `id` (or its filename). A deterministic address. | Cannot half-work. It resolves and pulls that one file whole, or the file is missing and you know immediately. |
| `**Terms:**` | **topic terms** ... fuzzy concepts that fan out through hub search and pull the whole neighborhood, including notes written later, in other sessions or other workspaces. | Can return nothing. |

**They stay on separate lines.** Merged into one line, a term that returns nothing reads as a broken pointer. Split, it reads as a miss, which is what it is.

**The handle works with no graph at all.** Terms need the hub's term-resolution index (SKLLPLG-140) to be verifiable, and the hub does not exist yet ... so terms are written with an honest `(unverified ... no hub yet)` marker until it does. Checkpoint's *full* usefulness is coupled to the hub. Its *baseline* usefulness is not, and the handle path is what has to degrade cleanly.

### The 30-day rolling window

Same file, two zones, newest first:

- **Inside 30 days:** full burst plus handle plus terms.
- **Older:** compressed to one line each, still retrievable:
  `- 2026-07-02 · Linear source-of-truth rule → [[session-summary-07-02-26]] · terms: linear, source of truth`
- **Floor of 5 sessions** in the full zone, so a quiet month cannot empty the top of the file.
- **No second archive artifact.** The tail lives in `Checkpoint.md`.
- **Closeout does the demotion, not the night job.** Checkpoint has to work before any graph exists, and the night job is gated behind SKLLPLG-141.

**Compression only applies to entries that have a resolvable handle.** An entry written before session summaries existed has its body in exactly one place. Compressing it destroys the only copy. Those stay full until the backfill converts them, and the backfill is blocked (see below).

**Expect entries to get much shorter.** A pre-summary top entry runs about 60 lines. Under this model the body moves to the summary and the entry becomes a burst plus two pointer lines. **That is the bloat fix working, not information loss** ... the body is one wiki-link away.

---

## `handoff.md`

Unchanged in structure ... it gains a `## Session summary` pointer section that wiki-links the summary. The five section names `/session-continue` reads (`## Last session`, `## Session summary`, `## P0 — Next Actions`, `## Key files from last session`, `## Verify before building`) are load-bearing. **Do not rename or restructure them** ... `## Session summary` included, since that is how the kickoff prompt finds the summary file at all.

---

## The backfill: documented, not built. Do not run it.

Converting historical `Checkpoint.md` entries into dated summary files is a bulk rewrite of months of historical records across every workspace ... one workspace alone holds 308 KB of Checkpoint in a single file.

**It is gated behind SKLLPLG-143's Recycle Bin existing as a recovery path.** Until then there is no undo, and this is second only to SKLLPLG-145 on data risk. **No skill in this plugin runs it, and no command that runs it exists.**

The contract it will run under when it is unblocked, recorded now so it is not re-derived later:

1. **Convert by copy, never in place.** The original `Checkpoint.md` is not edited during conversion.
2. **Originals retire to `_recycle-bin/` only after an arithmetic check passes:**
   - file count in equals file count out,
   - every converted entry's H2 date matches its source entry's date,
   - originals are still recoverable at the moment of retirement.
3. **Absence of exception is not verification.** A conversion pass that threw no errors has proven nothing. The count has to be counted and the dates have to be compared.

---

## One caveat this format does not fix

**The cascade mirror has not run since 2026-06-10.** The workspace-to-brain pipe exists but is **not currently running**, because it is an unscheduled job ... which is what SKLLPLG-141 exists to fix.

So: summaries written today land on disk and are readable by a human, by `/session-continue`, and by a manual graphify run. They do **not** automatically reach the second brain. Nothing in this format may assume that pipe works today.
