# Content plan sources ... doctrine, calls, and the file format

Reference for `content-plan`. The SKILL.md carries the steps and the blocks;
this file carries the per-source doctrine, the exact calls with their credits,
and the format of what gets written. Prices are the endpoints table
(`../../_shared/references/socialcrawl-endpoints.md`); the spend ritual is
`../../_shared/references/credit-guard.md`.

## 1. FIELD ... what already wins in this niche

Source: `<project>/analysis-data.json`, produced by `competitor-cross-reference`.

| Field | What it gives the pool |
|---|---|
| `outliers` | the all-time leaderboard: reels at or above 2.5x their own creator's median, client excluded. Evergreen ideas |
| `period_breakouts` (when present) | what broke out INSIDE the window, per account, at the same 2.5x bar. Newer analyze.py runs emit it; older projects do not. When it is absent, say so in one line and work from `outliers` alone |
| themes, hook buckets, theme x hook, the ranked gaps | the angle each idea rides, and the gap it closes |

Doctrine (`kallaway/Lf7ZXu4WiUs`, `kallaway/pirnGDCZD3Y`): rank on outlier score
(views against that channel's own average), never raw views; the roster already
excludes accounts over 1M and sits in the 10k to 250k band. Steal bricks, not
videos: topic, angle, hook structure, story structure, visual format, key
visuals, audio ... hold four of five constant and change exactly one, preferring
the format or the idea as the swap.

Evidence line, mandatory on every field idea, the same discipline reel-scripter
uses on angles:

```
Evidence: @handle · <metric, e.g. 47x their median, 1.2M views> · <reel URL>
```

## 2. OWN MATERIAL ... what the client already knows and says

| Source | Path | Notes |
|---|---|---|
| The weekly bank | `~/.claude/revxl/<brand>/voc/weekly-content-bank.md` | brand-brain's fast shelf mined from call recordings: this week's themes, hot objections, questions coming up, topical seeds. 7-day TTL, so entries older than a week are expired, not used. Nothing else in this plugin consumes it |
| The voice guide | `~/.claude/revxl/<brand>/voc/voice-guide.md` | read for what the client actually says, not to write copy here |
| The subject brief | `<project>/subject-brief.md` (if present, 0.5.0) | subject-matter's output. In `mode: subject-first` its angles outrank a field rewrap |

Doctrine (`heydominik/bZettD3oFWE`): the job is not to invent new topics every
time, it is to rewrap the ones that already work. The client's own expertise is
the uncopyable lane: a timed brain dump split into ideas, then three filters in
order ... what does everyone get wrong, what would most people disagree with,
and a counterintuitive fact known from experience, which is the strongest of the
three. Mining only inside the niche produces a cheap knockoff of everyone else,
so a format transposed from outside the niche onto the client's own subject is
the named high-ROI move (`kallaway/ceRZVxO8KF8`).

An own-material idea cites the bank entry (dated) or the brief section it came
from. It is still an idea, not a script: no lines are written here.

## 3. FRESH ... what is moving right now (paid)

About 10cr for a weekly refresh. Every call below is priced, stated to the
client, and made only through this table.

| Call | Credits | Params | What it is for |
|---|---|---|---|
| `google_news/search` | 1 | `keyword`, `time_range` week or month | timely topics, the 7 to 14 day window |
| `google_trends/explore` | 5 | `keywords` (1 to 5, comma separated) | is this topic rising or fading. State the cost before the call |
| `reddit/search` | 1 | `query` | what the niche is actually asking, in its own words |
| `instagram/search/reels` | 1 documented, priced at 5 by competitor-pulse | `query` | new field winners outside the roster. Verify `credits_used` before any loop |
| `search/everywhere` | 20 | `query` | a 12-platform sweep. Offered with the cost named, never automatic |

Windows: 7 to 14 days for timely, 3 to 12 months for evergreen
(`heydominik/5xOo4NuNG8k`, `kallaway/pirnGDCZD3Y`). Trending audio is rationed:
at most one audio-led idea a week, and the audio is never the reason for an
idea. The reason this lane exists: outdated hooks are the number one reason
accounts that grew a year ago stop growing.

**The gate.** Balance check is free. State the estimate before the pass. Any
call over 5cr is confirmed with the client BEFORE it is made, and a 10cr or
larger call is never inside a loop. Balance short: render the credits-short
block and build from disk instead.

## 4. AUDIENCE ... what their people are already asking

| Call | Credits | Params | What it is for |
|---|---|---|---|
| `prism/comments` | 1 per page documented, about 5 per Instagram reel measured | `url` | the questions and objections under the week's winners. Budget with the measured number |
| `prism/audience-questions` | 30 | `topic` | clustered real audience questions. OFFERED, cost named, explicit yes, never automatic |

`reddit/search` (section 3) doubles as a free-ish audience read at 1cr.

Doctrine: an audience question quoted back is the cheapest route to a hook that
names the client's exact situation, which is what the hook doctrine asks for.
An idea from this lane cites the source URL and the quoted question.

## 5. Pillars ... the balance rule

Ladder, in order, stop at the first hit:

1. `<project>/roadmap*.md`, section 7 "Recommended Content Strategy ... Pillars":
   3 to 5 named pillars, each with frequency and rationale. This is where a
   finished cross-reference writes them.
2. `~/.claude/revxl/<brand>/voc/business-config.md` when it names pillars.
3. Ask once, in one question, and write the answer into the plan header so the
   next run reads it back instead of asking again.

Doctrine (`heydominik/bZettD3oFWE`): any niche has 3 to 4 core topics and the 3
to 5 pillars are written before the ideas. The pool spreads across them; no
pillar eats the pool; a pillar that came back with zero ideas is named in one
line, never filled with filler.

## 6. Cadence and slots

Slots come from the client's REAL 90-day count, not an aspiration
(`brock_johnson/pXtzH3NJX9Q`): what they actually posted in the last 90 days,
divided by 13, pushed slightly past it. Floor 3 to 4 posts a week, never a gap
over 48 hours. Rhythm: post daily, create 1 to 3 times a week, plan weekly,
review monthly. Expect a 30 to 60 day dip when the cadence steps up, and say so
once at teach level `new`. Store the result in `state.plan.slots` and ask only
when state has no cadence.

## 7. Dedupe

Checked before an idea enters the pool:

1. `state.scripts[]` ... every angle already scripted, with its slug and source.
2. the previous `content-plan-*.md` files in `<project>/` ... their idea titles
   and angles. `state.plan.ideas_unscripted` names what was left unwritten; those
   may carry forward, labelled "carried".
3. `<project>/scripts/*.md` `Angle:` lines ... what was written outside a plan.

A near-duplicate is dropped, or explicitly reframed as a different hook type on
the same theme and labelled as the reframe. Repetition of a winner is a
deliberate, labelled decision, never an accident of the pool.

## 8. The idea block

Each idea in the plan is one tight block:

```
N. <Idea title ... the angle in one line>
   Source: field | own | fresh | audience  ·  Pillar: <pillar>  ·  Angle: <theme> x <hook type>
   Why it wins: <the proven move it is drawn from, one line>
   Evidence: @handle · <metric> · <URL>      (own: the dated bank entry or brief section;
                                              fresh: the query and the date it was run)
   Doctrine: <note id>
```

`[avoid-list]` is appended to the title of any idea riding a hook bucket or
theme the brief's Avoid list names as a niche loser.

## 9. The plan file

`<project>/content-plan-<YYYY-Www>.md`, ISO week (for example
`content-plan-2026-W37.md`):

1. **Header:** week of (Monday's date), brand, sources used, pillars, slots,
   the mode, and the `Vault:` evidence line.
2. **The ideas,** numbered, grouped by pillar, in the block shape above.
3. **The slot table:**

   | Slot | Day | Idea | Pillar | Source |
   |---|---|---|---|---|

4. **Skipped:** one line per source that came back empty or was declined, and
   what that costs the plan.

The ideas are in the field's language, not yet the client's: voice work happens
when one is picked and reel-scripter runs.

## 10. The Vault trigger point

One named step, before the pool is written, at `depth=med` (1 search, up to 2
reads for this step, total). The call shape, the cache rule and the degrade
behaviour are in `../../_shared/references/vault-api.md`; the MAKE-topic row is
the recipe this skill uses, and its `angles:` are `content_ideation`,
`transpositioning` and `evergreen_content`. The ids are search terms, never a
validation list: a hit that uses none of them is still a hit.

When the corpus comes back on both sides of the in-niche versus transposed
question (contradiction C7), this plugin's side is: the in-niche roster is what
`competitor-cross-reference` produced and it governs the FIELD lane, while
transposition governs topic selection here. Say that in one line rather than
presenting both and leaving the client to choose.
