# Journey map ... the single source of truth

The graph of every shortform-superengine skill: trigger phrases, prerequisites,
and the edge registry. **Anti-rot rule: edges, prereqs, and trigger phrases live
ONLY here.** Skills reference this file, they never hardcode another skill's
trigger phrase or prereq list. Renaming a skill or changing an edge = edit this
file first, then the affected SKILL.md Next-moves blocks to match.
**A terminal path without a registry row is a bug.**

Next-Moves block SHAPE (blocks live inline in each SKILL.md, because skills run
standalone; this file is the edge ledger only): `routing.md`. State keys
referenced below: `state-schema.md`. Prices behind the credit-gated moves:
`socialcrawl-endpoints.md`. Vault trigger points: `vault-api.md`.

## The journey

```
SETUP ......> VOICE ......> FIELD ..........> MAKE .........> READ .........> PULSE
onboarding    brand-brain   competitor-       content-plan    own-content-    competitor-
              subject-      cross-reference   reel-scripter   analysis        pulse
              matter        creator-strategy-                 (0.5.0)            |
              (0.5.0)       harvest                                              |
                                                                                 v
                                                                          back to MAKE

shortform-start (the front door) and shortform-next (the compass) sit outside
the line. They are reachable from anywhere and they route INTO it.
```

Why this order: avatar and offer first, then the baseline, then who to model,
then topic, hook, retention, CTA ramp, cadence, then read the results and loop.
Content built before avatar and offer clarity produces views without sales. The
doctrine behind each handoff, with its note ids, is in `vault-api.md`.

Skills check prereqs in state and **refuse to skip ahead**, with a plain-English
why and the correct door (edge E0).

## Skill roster (9 installed)

Trigger phrases are canonical: Next-moves blocks quote them verbatim from this
table. Every phrase belongs to exactly one skill.

### SETUP
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `shortform-start` | "start shortform", "open shortform", "shortform start", "I'm lost in shortform" | none | `goal`, `mode`, `active_brand`; the marker-to-state migration; a first-run 4-option block |
| `shortform-next` | "what's next in shortform", "shortform next", "where am I in shortform" | none | 2 to 4 ranked moves from state + this map. Writes nothing |
| `onboarding` | "set up shortform superengine", "onboard shortform", "shortform setup", "install the reel plugin", "configure the reel plugin", "get the shortform superengine ready", "finish setting up the content engine", "show my setup" | none | `.superengine` marker (incl. `active_brand`), `setup.*`, key + tool audit |

### VOICE
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `brand-brain` | "capture my voice", "build my brand brain", "mine my calls", "set up my voice", "refresh my voice guide", "update my topics", "add these themes to my brand brain", "add this to my brand brain", "schedule my brain refresh" | none | `~/.claude/revxl/<brand>/voc/` (voice guide, themes, weekly content bank). **Writes no state keys** |
| `subject-matter` | "use my own material", "subject matter", "brain dump on <topic>" | `setup` done | *(0.5.0, not yet installed)* `~/.claude/revxl/<brand>/subject/` + `<project>/subject-brief.md`; `subject.*` |

### FIELD
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `competitor-cross-reference` | "analyze my Instagram against my competitors", "competitor cross-reference analysis", "cross-reference my client against competitors", "content gap analysis for an Instagram account", "IG baseline plus competitor audit", "build a content/growth strategy roadmap from competitor data", "analyze why a client's reels underperform vs competitors", "create a client-facing strategy roadmap from Instagram data", "build my visual dashboards", "regenerate my visuals", "open my visuals", "run more seeds", "shrink the set to N", "resume my cross-reference" | `setup` done (marker + SocialCrawl key) | `<project>/analysis-data.json`, the 10-section roadmap, the visual pack; `analysis.*`, `project_path` |
| `creator-strategy-harvest` | "harvest <creator>'s library", "get everything <creator> teaches", "pull all of <creator>'s content", "build a corpus from <creator>'s videos", "refresh our notebook on <creator>", "refresh the harvest on <creator>", "build a notebook from this harvest" | `yt-dlp` present | a dated, framework-extracted creator corpus + manifest. Writes no state keys |

### MAKE
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `content-plan` | "content plan", "plan my week", "plan the week", "what should I post this week", "weekly topic pool", "topic pool", "idea bank", "20 ideas from the best performers", "lean the plan toward <pillar>", "rebuild the pool, lean <pillar>", "refresh next week's plan" | `analysis` OR `voc.present` OR `subject.present` (at least one source) | `<project>/content-plan-<week>.md` (7 to 15 source-tagged ideas); `plan.*` |
| `reel-scripter` | "write a reel script", "write a reel script from my analysis", "script a reel from my analysis", "turn my competitor analysis into a reel", "draft an IG reel in my voice", "script the next reel for <client>", "give me a reel hook + body + CTA", "script the next angle", "script that reel", "script the top gap", "script the top seed", "script the top idea", "script the top question", "script idea N from my content plan" | field-first: `analysis` set. subject-first: `subject.present` | `<project>/scripts/<slug>.md` + the `Vault:` evidence line; `scripts[]`, `angles_unpicked[]` |

### READ
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `own-content-analysis` | "read my results", "how is my content doing", "read last week's results" | `setup` done | *(0.5.0, not yet installed)* `<project>/own-read-<date>.md`; `own_read.*` |

### PULSE
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `competitor-pulse` | "run the weekly pulse", "run the pulse", "competitor pulse", "what changed this week", "refresh my competitor analysis", "make the pulse weekly", "run the pulse on 14 days", "roster health", "manage my roster", "add <handle> to my roster", "swap a competitor", "backfill and re-analyze", "search the field for <keyword>", "comment pulse", "comment pulse on <url>", "comment pulse on <scope>", "mine the comments on <url>", "what are people saying in <handle>'s comments", "run audience questions" | `analysis` set (a finished cross-reference) | the weekly brief, refreshed charts, `history/` snapshot, comment intel; `pulse.*` |

Retired at 0.4.0: the bundled `socialcrawl` skill and its phrases ("SocialCrawl",
"social crawl", "social media API"). The endpoints it documented are now
`socialcrawl-endpoints.md`; everything deeper belongs to socialcrawl-superengine.

## Edge registry

Happy-path edges (E) plus failure edges (F). **Failure edges are load-bearing.**
They are what makes this a no-dead-end flow. E1 to E16 keep the ids they carried
in 0.3.4's `next-moves.md`.

### Generic
| ID | From, condition | Routes to |
|---|---|---|
| E0 | ANY skill, prereq missing (skip-ahead attempt) | the skill that produces the missing prereq, as a written block: what is missing, why the order exists in one plain sentence, and the door as move #1 ("write me a reel script" with no analysis and no subject -> competitor-cross-reference) |
| E0b | ANY skill, deliverable done | Next moves per `routing.md`: #1 = the journey's next unmet step for this state |

> **E0b coverage (secondary and non-happy terminals):** a skill's non-#1
> Next-move options, plus decline / hold / thin-evidence / sub-mode terminals
> (brand-brain's remind-only nudge, cross-reference's "proceed thin",
> competitor-pulse's quiet-week note, any
> "back to the caller" exit) all route via **E0b**: compass-ranked moves from
> current state. They do NOT each get a bespoke edge id. E0b is their registry
> row. Named cross-skill lateral doors are the exception and are listed on the
> E rows below.

### Happy path
| ID | From, ending | Routes to |
|---|---|---|
| E1 | onboarding, Step 8 activation | `shortform-start` (primary, captures the goal) - competitor-cross-reference - brand-brain (if skipped at 4b) - creator-strategy-harvest - pulse schedule (only if an analysis exists) |
| E2 | onboarding, sub-mode exits | back to work - shortform-next - "show my setup" |
| E3 | competitor-cross-reference, roadmap delivered | visual pack - script the top gap (reel-scripter) - feed themes to brand-brain - content-plan - weekly pulse [schedule] |
| E4 | competitor-cross-reference, stopped at checkpoint 2 (thin set) | run more seeds - park and resume (F1) - proceed thin (explicit) |
| E5 | competitor-cross-reference, stopped at checkpoint 3 (credit decline) | shrink the set - top up and resume (F1) - park (F4) |
| E6 | reel-scripter, script written | script the next angle (from `angles_unpicked[]`) - content-plan - regenerate visuals - weekly pulse [schedule] |
| E7 | content-plan, an idea picked from the plan | reel-scripter Step 1 with that idea as the angle (the pick carries its source tag and angle) |
| E8 | content-plan, plan presented, no pick | saved pointer ("script idea N from my content plan") - weekly refresh via the pulse - lean the plan toward a pillar - script the top idea |
| E9 | reel-scripter, Step 0a no analysis (field-first) | competitor-cross-reference, as a written block with the reason. This ending's general form across the MAKE skills is F2 |
| E10 | brand-brain, mine or refresh complete | script the top seed (reel-scripter) - refresh schedule [schedule, if unset] - back to the caller |
| E11 | brand-brain, refresh declined | proceed on the current brain - remind-only nudge [schedule] - top-patterns quick pass |
| E12 | brand-brain, interview floor | wire a recording source - first-refresh suggestion [schedule] - script on the interim voice |
| E13 | creator-strategy-harvest, manifest written | `subject-matter` "(if installed)" as the corpus consumer - NotebookLM (detect-first) - harvest another creator - refresh later. **The 0.3.4 "vault ingest / send Joe the HANDOFF" option is removed (SKLLPLG-78): engines never write to the Vault** |
| E14 | competitor-pulse, weekly brief | script the week's winner - open my visuals - roster ops - make the pulse weekly [schedule, if unset] - monthly roster pass |
| E15 | competitor-pulse, roster op done | backfill and re-analyze - defer to the next pulse - run the pulse now |
| E16 | competitor-pulse, empty week | quiet-week note (no extra spend) - script from the content plan - run the pulse on 14 days (E23) - roster health (E24) |
| E17 | shortform-start, first run (no marker, no state) | the five goals asked as a plain question (make a reel / plan the week / read my results / read the field / set up), then the four-move block whose #1 is the door that goal needs first |
| E18 | shortform-start, marker present and state absent (migration) | writes `state/<brand>.json` from the marker (incl. the `competitor_pulse` block), sets `active_brand`, says so in one line, then delegates to shortform-next |
| E19 | shortform-start, returning client | one-line position + open loops, then shortform-next |
| E20 | shortform-next, compass rendered | the ranked moves themselves. Ranking order: `goal`, then position, then open loops and staleness. #1 must be actionable now |
| E21 | content-plan, plan written | script idea 1 (reel-scripter, primary) - lean the plan toward a pillar - refresh next week's plan (pulse) - read last week's results (own-content-analysis "(if installed)") |
| E22 | competitor-cross-reference, resumed from `analysis.resume` | back into the pipeline at the stored checkpoint, then E3 |
| E23 | competitor-pulse, 14-day window run | the widened brief, then E14's moves |
| E24 | competitor-pulse, roster-health pass | roster ops (add / remove / swap) - run the pulse now - monthly roster pass [schedule] |

### Failure edges
| ID | From, condition | Routes to |
|---|---|---|
| F1 | competitor-cross-reference, parked at checkpoint 2 or 3 | "resume my cross-reference" reads `analysis.resume` and re-enters at the stored checkpoint (E22). The pointer is persisted, never session-memory |
| F2 | any MAKE skill (reel-scripter, content-plan) in `field-first`, no analysis on disk | competitor-cross-reference as move #1, with the reason in one plain sentence. reel-scripter's own Step 0a instance is E9 |
| F3 | any Vault trigger point, no key / workspace-superengine missing / the callee reports an error | continue on the bundled references, print `Vault: 0 searches, 0 reads \| skipped: <reason>`, and one line: "workspace-superengine is missing, running on the built-in library". **Never blocks the journey** |
| F4 | any credit-gated step, SocialCrawl balance short | shrink the set - top up and resume - park it (the parked pointer is `analysis.resume`). Never spend silently |
| F5 | competitor-pulse, `failed > 0` accounts | a retry pass over the failed handles (primary) - roster health (E24) - proceed on the partial set with the coverage caveat stated |
| F6 | any skill, `analysis.date` older than 30 days | refresh the field via the pulse as move #1, with the staleness named |
| F7 | any voice-consuming skill, `voc.refreshed_at` older than 7 days | offer a brand-brain refresh **once** per journey (`declined_offers`), then proceed on the current voice guide, labelled |
| F8 | reel-scripter or content-plan in `subject-first`, no subject on disk | `subject-matter` "(if installed)" as move #1, else switch to `field-first` and say so |
| F9 | a deep play requested and the socialcrawl-superengine marker is absent | the install refusal block as move #1: which plays need it (field search beyond `socialcrawl-endpoints.md`, creator vetting, share of voice, lead finding), why this plugin will not fake them, then the exact phrase to say once it is installed. A refusal that routes, never a stall |

## Gates (hard blocks, checked in state)

| Gate | Condition | Blocked skill | Unblock route |
|---|---|---|---|
| SETUP | the `.superengine` marker exists AND the SocialCrawl key resolves | competitor-cross-reference, competitor-pulse, content-plan's FIELD and FRESH sources | E0 -> onboarding |
| ANALYSIS | `analysis.date` set AND `<project>/analysis-data.json` exists | competitor-pulse, reel-scripter in `field-first`, content-plan's FIELD source | E0 -> competitor-cross-reference (F2) |
| VOICE | `voc.present` (derived from `~/.claude/revxl/<brand>/voc/`) | an in-voice draft. reel-scripter still runs, labelled "voice confidence: low" | brand-brain (F7) |
| SUBJECT | `subject.present`, only in `mode: subject-first` | reel-scripter's subject-first angle source | subject-matter, 0.5.0 (F8) |
| DEEP PLAY | the socialcrawl-superengine marker | field search beyond the endpoints table, creator vetting, share of voice, lead finding | F9 install refusal block |

## Cross-plugin triggers (external, detect-first, one line when absent)

Blocks may quote these ONLY behind an *installed* conditional.

| Plugin | Detect | Skill / phrase | When |
|---|---|---|---|
| socialcrawl-superengine | `~/.claude/socialcrawl-superengine/.superengine` OR a directory matching `~/.claude/plugins/cache/*/socialcrawl-superengine/` | `research-plays` ... the client-facing phrase is "vet this creator" (if installed) | a deep play beyond `socialcrawl-endpoints.md`. Absent -> F9, never a stall |
| workspace-superengine | the `revxl-vault-search` skill resolves | `workspace-superengine:revxl-vault-search` | the named Vault trigger points in `vault-api.md`. This is a Skill call the plugin makes, never a phrase quoted to the client. Absent -> F3 |
| NotebookLM tooling | the local CLI is on PATH | a notebook from a finished harvest | E13 only |

## Maintenance

Adding a skill or an ending: add the roster row and the registry row HERE first,
then write the skill's inline Next-moves block to match. `scripts/check_routing.py`
fails the build when a registry row's ending has no block in the named skill, and
warns when a `Say:` phrase resolves nowhere (phrases marked "(if installed)" are
exempt). Retired 0.3.4 wording kept as an accepted alias, never as a canonical
phrase: "script idea N from my topic pool" (now "script idea N from my content
plan"), "make this weekly" (now "make the pulse weekly"), "make the
charts" (now "build my visual dashboards"), "add/remove/swap a
competitor" (now "swap a competitor" and "add <handle> to my roster").
