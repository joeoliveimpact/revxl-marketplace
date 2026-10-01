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

## Skill roster (15 installed)

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
| `creator-strategy-harvest` | "harvest <creator>'s library", "get everything <creator> teaches", "pull all of <creator>'s content", "build a corpus from <creator>'s videos", "refresh our notebook on <creator>", "refresh the harvest on <creator>" | `yt-dlp` present | a dated, framework-extracted creator corpus + manifest. Writes no state keys |

### MAKE
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `content-plan` | "content plan", "plan my week", "plan the week", "what should I post this week", "weekly topic pool", "topic pool", "idea bank", "20 ideas from the best performers", "lean the plan toward <pillar>", "rebuild the pool, lean <pillar>", "refresh next week's plan" | `analysis` OR `voc.present` OR `subject.present` (at least one source) | `<project>/content-plan-<week>.md` (7 to 15 source-tagged ideas); `plan.*` |
| `reel-scripter` | "write a reel script", "write a reel script from my analysis", "script a reel from my analysis", "turn my competitor analysis into a reel", "draft an IG reel in my voice", "script the next reel for <client>", "give me a reel hook + body + CTA", "script the next angle", "script that reel", "script the top gap", "script the top seed", "script the top idea", "script the top question", "script idea N from my content plan" | field-first: `analysis` set. subject-first: `subject.present` | `<project>/scripts/<slug>.md` + the `Vault:` evidence line; `scripts[]`, `angles_unpicked[]` |
| `hook` | "write me a hook", "opening line", "first 3 seconds of my reel" | none | 3 to 5 Reel openings (spoken line, on-screen text, visual), a primary and an alternative; adapts a proven hook to the topic. Called by reel-scripter at Step 3. Writes no state keys |
| `rehooks` | "add rehooks", "add re-hooks to this script", "keep them watching" | none | a drop-off map and a re-hook per medium or high risk beat. Called by reel-scripter at Steps 2, 3 and 4b. Writes no state keys |
| `viral` | "make this more viral", "punch this up", "more shareable" | none | the rewrite (proposals only on a frozen script), a change list, the share type, three scores. Runs on every reel at reel-scripter Step 4a. Writes no state keys |
| `angles` | "angles on this topic", "ways to cover this" | none | numbered concepts, each with audience, motivation, approach, format and evidence level. Called by reel-scripter at Step 1. Writes no state keys |
| `polarize` | "hot take", "contrarian take", "unpopular opinion" | none | the sharpened take, the Other side line (it need not be fair: straw men allowed, no made-up facts) and the evidence list. Called by reel-scripter at Step 2 for myth-bust/negation and contrarian/curiosity reels. Writes no state keys |

### READ
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `own-content-analysis` | "read my results", "how is my content doing", "read last week's results" | `setup` done | *(0.5.0, not yet installed)* `<project>/own-read-<date>.md`; `own_read.*` |

### PULSE
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `competitor-pulse` | "run the weekly pulse", "run the pulse", "competitor pulse", "what changed this week", "refresh my competitor analysis", "make the pulse weekly", "run the pulse on 14 days", "retry the failed handles", "roster health", "manage my roster", "add <handle> to my roster", "swap a competitor", "backfill and re-analyze", "search the field for <keyword>", "comment pulse", "comment pulse on <url>", "comment pulse on <scope>", "mine the comments on <url>", "what are people saying in <handle>'s comments", "run audience questions" | `analysis` set (a finished cross-reference) | the weekly brief, refreshed charts, `history/` snapshot, comment intel; `pulse.*` |

### API
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `socialcrawl` | "check my SocialCrawl balance", "resolve this social URL", "batch-check engagement", "what does <endpoint> cost", "socialcrawl" | a SocialCrawl API key (env var, else `~/.config/socialcrawl/api_key`) | the raw API response plus `credits_used` and `credits_remaining`. Writes no state keys. Ends on E25 |

The bundled lean core is where the API method, the per-platform references and
the credit guidelines live. `socialcrawl-endpoints.md` stays the list of calls the
pipeline itself makes; socialcrawl-superengine, when installed, executes the
searches.

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
| E1 | onboarding, Step 8 activation | competitor-cross-reference (primary, whatever the goal) - shortform-next always, whatever the goal - brand-brain (if skipped at 4b) - creator-strategy-harvest - pulse schedule (only if an analysis exists AND neither state nor marker says scheduled) - reel-scripter "write a reel script from my analysis" (a prior analysis on disk) - shortform-start "start shortform" (a prior analysis on disk) |
| E2 | onboarding, sub-mode exits | back to work - shortform-next - "show my setup" |
| E3 | competitor-cross-reference, roadmap delivered | visual pack - script the top gap (reel-scripter) - feed themes to brand-brain - content-plan - weekly pulse [schedule] |
| E4 | competitor-cross-reference, stopped at checkpoint 2 (thin set) | run more seeds - park and resume (F1) - proceed thin (explicit) |
| E5 | competitor-cross-reference, stopped at checkpoint 3 (credit decline) | shrink the set - top up and resume (F1) - park (F4) |
| E6 | reel-scripter, script written | script the next angle (from `angles_unpicked[]`) - content-plan - first cut of the recorded reel (editor-superengine, if installed; Cross-plugin triggers) - weekly pulse [schedule] |
| E7 | content-plan, an idea picked from the plan | reel-scripter Step 1 with that idea as the angle (the pick carries its source tag and angle) |
| E8 | content-plan, plan presented, no pick | saved pointer ("script idea N from my content plan") - weekly refresh via the pulse - lean the plan toward a pillar - script the top idea |
| E9 | reel-scripter, Step 0a no analysis (field-first) | competitor-cross-reference, as a written block with the reason. This ending's general form across the MAKE skills is F2 |
| E10 | brand-brain, mine or refresh complete | script the top seed (reel-scripter) - refresh schedule [schedule, if unset] - back to the caller |
| E11 | brand-brain, refresh declined | proceed on the current brain - remind-only nudge [schedule] - top-patterns quick pass |
| E12 | brand-brain, interview floor | wire a recording source - first-refresh suggestion [schedule] - script on the interim voice |
| E13 | creator-strategy-harvest, manifest written | `subject-matter` "(if installed)" as the corpus consumer - NotebookLM (detect-first) - harvest another creator - refresh later. **The 0.3.4 "vault ingest / send Joe the HANDOFF" option is removed (SKLLPLG-78): engines never write to the Vault** |
| E14 | competitor-pulse, weekly brief | script the week's winner - open my visuals - roster ops - make the pulse weekly [schedule, if unset] - monthly roster pass |
| E15 | competitor-pulse, roster op done | backfill and re-analyze - defer to the next pulse - run the pulse now |
| E16 | competitor-pulse, empty week | quiet-week note (no extra spend) - run the pulse on 14 days (E23) - plan my week - script from the content plan [if a plan is on disk] - make the pulse weekly [schedule, if unset] |
| E17 | shortform-start, first run (no marker, no state) | the five goals asked as a plain question (make a reel / plan the week / read my results / read the field / set up), then the four-move block whose #1 is the door that goal needs first |
| E18 | shortform-start, marker present and state absent (migration) | writes `state/<brand>.json` from the marker (incl. the `competitor_pulse` block), sets `active_brand`, says so in one line, then delegates to shortform-next |
| E19 | shortform-start, returning client | one-line position + open loops, then shortform-next |
| E20 | shortform-next, compass rendered | the ranked moves themselves. The (E20) block's line order is the rank; `goal` reorders the two MAKE lines only; open-loop candidates rank after the last firing gated line. Open-loop candidates whose own skill is not blocked outrank gated lines for the free slots and are never dropped in favour of a gated line, but at most four moves render: when loops outnumber the free slots, the oldest loops render and the rest are named in the position line. When a blocking unblock line fires (shortform-next guard rail 6), it keeps slot 1, open-loop candidates whose own skill is not blocked fill the remaining slots before any other gated line, and still at most four moves render. A loop whose own skill is blocked is never ranked; its unblock route is ranked instead, once (shortform-next step 4). Lines 11 to 13 carry the loop phrases by the entry's `skill` (competitor-cross-reference "resume my cross-reference", content-plan "script idea N from my content plan", reel-scripter "script that reel"), one move per entry, oldest first; an entry from any other skill is said in the position line, never ranked. #1 must be actionable now |
| E21 | content-plan, plan written | script idea 1 (reel-scripter, primary) - lean the plan toward a pillar - refresh next week's plan (pulse) - read last week's results (own-content-analysis "(if installed)") |
| E22 | competitor-cross-reference, resumed from `analysis.resume` | back into the pipeline at the stored checkpoint, then E3 |
| E23 | competitor-pulse, 14-day window run | the widened brief, then E14's moves |
| E24 | competitor-pulse, roster-health pass | roster ops (add / remove / swap) - run the pulse now - monthly roster pass [schedule] |
| E25 | socialcrawl, call made | the calling skill's next step, balance, endpoint cost |
| E26 | hook, openings delivered, or the ask is not a hook job (its "When NOT to use this") | rehooks "add rehooks" (a script body exists) - reel-scripter "write a reel script" (no script yet, an analysis on disk) - shortform-next. Not a hook job: rehooks (viewers leave mid-reel) - viral (the whole script) - angles (the topic is undecided). Called by reel-scripter: back to the caller (E0b) |
| E27 | rehooks, re-hooks delivered, or the ask is not a rehooks job | hook "write me a hook" (the opening is still weak) - viral "make this more viral" - shortform-next. Not a rehooks job: hook (the opening is the problem, an immediate drop) - viral (the whole script) - angles (no script yet). Called by reel-scripter: back to the caller (E0b) |
| E28 | viral, rewrite delivered, or the ask is not a viral job | rehooks "add rehooks" - hook "write me a hook" - shortform-next. Not a viral job: angles (no script yet) - hook (only the opening is weak) - rehooks (viewers leave mid-reel) - polarize (a soft take made sharper). Called by reel-scripter: back to the caller (E0b) |
| E29 | angles, concepts delivered, or the ask is not an angles job | reel-scripter "write a reel script" (an analysis on disk) - hook "write me a hook" - polarize "hot take" (a concept that holds a stance) - shortform-next. Not an angles job: viral (a script needs polish) - hook (only the opening) - rehooks (viewers leave mid-reel) - polarize (a stance to state with conviction). Called by reel-scripter: back to the caller (E0b) |
| E30 | polarize, take delivered, or not a take (no real position, or the main message takes no side) | rehooks "add rehooks" - hook "write me a hook" - shortform-next. Not a take: angles "angles on this topic" - viral "make this more viral" (more shares is the real goal). Called by reel-scripter: back to the caller (E0b) |

### Failure edges
| ID | From, condition | Routes to |
|---|---|---|
| F1 | competitor-cross-reference, parked at checkpoint 2 or 3 | "resume my cross-reference" reads `analysis.resume` and re-enters at the stored checkpoint (E22). The pointer is persisted, never session-memory |
| F2 | any MAKE skill (reel-scripter, content-plan) in `field-first`, no analysis on disk | competitor-cross-reference as move #1, with the reason in one plain sentence. reel-scripter's own Step 0a instance is E9 |
| F3 | any Vault trigger point, no key / workspace-superengine missing / the callee reports an error | continue on the bundled references, print `Vault: 0 searches, 0 reads \| skipped: <reason>`, and one line: "workspace-superengine is missing, running on the built-in library". **Never blocks the journey** |
| F4 | any credit-gated step, SocialCrawl balance short | shrink the set - top up and resume - park it (the parked pointer is `analysis.resume`). Never spend silently |
| F5 | competitor-pulse, `failed > 0` accounts | a failed-handles-only retry pass inside the run, before the Step 4 merge; still failing, the F5 block's retry move "retry the failed handles" (the failed-only router row, never the full pulse) - roster health (E24), with no removal recommendation before three failed probes since the handle's last `probe-ok` across at least two separate runs - script this week's top reel from `period_breakouts` on the partial set ("script that reel") |
| F6 | any skill, BOTH `analysis.date` and `pulse.last_run` older than 30 days (a null `pulse.last_run` counts as over 30 days), or `analysis.date` alone 90 days or older, which the pulse never refreshes | 30 to 90 days: refresh the field via the pulse as move #1, with the staleness named. `analysis.date` 90 days or older: a full competitor-cross-reference re-run instead, with its `N x 6` credit cost stated |
| F7 | any voice-consuming skill, `voc.refreshed_at` older than 7 days | offer a brand-brain refresh **once** per journey (`declined_offers`), then proceed on the current voice guide, labelled |
| F8 | reel-scripter or content-plan in `subject-first`, no subject on disk | `subject-matter` "(if installed)" as move #1, else switch to `field-first` and say so |
| F9 | a deep play requested and the socialcrawl-superengine marker is absent | the install refusal block as move #1: which plays need it (field search beyond `socialcrawl-endpoints.md`, creator vetting, share of voice, lead finding), why this plugin will not fake them, then the exact phrase to say once it is installed. A refusal that routes, never a stall |
| F10 | socialcrawl, call failed after the idempotent retry | balance check, then the compass |

## Gates (hard blocks, checked in state)

| Gate | Condition | Blocked skill | Unblock route |
|---|---|---|---|
| SETUP | the `.superengine` marker exists AND the SocialCrawl key resolves | competitor-cross-reference, competitor-pulse, content-plan's FIELD and FRESH sources | E0 -> onboarding |
| ANALYSIS | `analysis.date` set AND `<project>/analysis-data.json` exists | competitor-pulse, reel-scripter in `field-first`, content-plan's FIELD source | E0 -> competitor-cross-reference (F2) |
| VOICE | `voc.present` (derived from `~/.claude/revxl/<brand>/voc/`) | an in-voice draft. reel-scripter still runs, labelled "voice confidence: low" | brand-brain (F7) |
| SUBJECT | `subject.present`, only in `mode: subject-first` | reel-scripter's subject-first angle source | subject-matter, 0.5.0 (F8) |
| DEEP PLAY | the socialcrawl-superengine marker | field search beyond the endpoints table, creator vetting, share of voice, lead finding | F9 install refusal block |

## Cross-plugin triggers (external, detect-first, one line when absent)

Blocks may quote these behind an *installed* conditional, or always render a move that carries its own install clause (ask me to install it from the RevXL marketplace first) and ends with `(if installed)`, as F9 move 1 and E6 move 3 do. A move with no install clause still needs the conditional.

| Plugin | Detect | Skill / phrase | When |
|---|---|---|---|
| socialcrawl-superengine | `~/.claude/socialcrawl-superengine/.superengine` OR a directory matching `~/.claude/plugins/cache/*/socialcrawl-superengine/` | `research-plays` ... the client-facing phrase is "vet this creator" (if installed) | a deep play beyond `socialcrawl-endpoints.md`. Absent -> F9, never a stall. To install it the client asks Claude to add the RevXL marketplace `joeoliveimpact/revxl-marketplace` and install the plugin; the client types nothing |
| workspace-superengine | the `revxl-vault-search` skill resolves | `workspace-superengine:revxl-vault-search` | the named Vault trigger points in `vault-api.md`. This is a Skill call the plugin makes, never a phrase quoted to the client. Absent -> F3 |
| notebooklm-superengine | the `notebooklm-build` skill resolves, or the local NotebookLM CLI is on PATH | `notebooklm-build` ... the client-facing phrase is "build a notebook" (if installed) | E13 only, over a finished harvest folder |
| editor-superengine | the `reel-first-cuts` skill resolves | `reel-first-cuts` ... the client-facing phrase is "cut this reel" (if installed) | E6 only, once the client has recorded the script and says where the raw video is |

## Maintenance

Adding a skill or an ending: add the roster row and the registry row HERE first,
then write the skill's inline Next-moves block to match. `scripts/check_routing.py`
fails the build when a happy-path or failure row's id is cited by no Next-moves
block in the skill the row comes FROM, or in a skill its "Routes to" cell names
(a row whose From cell opens with "any", "a", "an" or "the" is generic: any
skill's block may cite it). It warns, and never fails, when a `Say:` phrase
resolves nowhere (phrases
marked "(if installed)" are exempt). Retired 0.3.4 wording kept as an accepted alias, never as a canonical
phrase: "script idea N from my topic pool" (now "script idea N from my content
plan"), "make this weekly" (now "make the pulse weekly"), "make the
charts" (now "build my visual dashboards"), "add/remove/swap a
competitor" (now "swap a competitor" and "add <handle> to my roster").
