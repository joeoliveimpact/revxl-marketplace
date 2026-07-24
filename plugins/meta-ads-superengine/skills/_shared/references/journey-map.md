# Journey map — the single source of truth

The graph of all 27 skills: trigger phrases, prerequisites, and the edge
registry. **Anti-rot rule: edges, prereqs, and trigger phrases live ONLY
here.** Skills reference this file — they never hardcode another skill's
trigger phrase or prereq list. Renaming a skill or changing an edge = edit
this file first, then the affected SKILL.md next-moves blocks to match.
A terminal path without a registry row is a bug.

Per-skill 8-field contracts: `skill-contracts.md`. Next-Moves block SHAPE
(the choose-your-own-adventure grammar — blocks live inline in each
SKILL.md; this file is the edge ledger only): `routing.md`. State keys
referenced below: `state-schema.md`.

## The journey

```
SETUP ──► FOUNDATIONS ─────────────► CREATIVE-STRATEGY (hub) ──► PRODUCTION ──► TEST
          breakeven-math                  ▲        │              hook-writer     (creative-test,
          → funnel-qualify                │        │              ad-copy         post-launch)
          → lead-questions     best-content        │              static-ads
          → signal-setup    competitor-intel       │              video-script
          → compliance-check   (feed the hub)      ▼
                                             PLAN (stage-check → campaign-plan)
                                                   │
                                             LAUNCH ◄─ GATE: compliance pass (current offer_version)
                                             (launch-runbook)   + funnel.qualified_event + campaign_plan
                                                   │
                                             RUN (daily-brief ⟳ · kpi-tracker · performance-review ⟳)
                                                   │
                                             SCALE (scale-decision) ──► loops back to CREATIVE-STRATEGY
```

Why this order: math sets the floor → the funnel decides what Meta learns →
creative is the engine → produce distinct → launch broad → wait, don't touch →
scale winners. Skills check prereqs in state and **refuse to skip ahead** —
with a plain-English why and the correct door (edge E0).

## Skill roster (27)

Directory names carry the `meta-ads-` prefix (family convention — commands
group together, no cross-plugin collision). Trigger phrases are canonical:
next-moves blocks quote them verbatim from this table.

### Core (5)
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `meta-ads-start` | "meta ads", "start meta ads" | none | routing table, compass pointer, canon-staleness banner |
| `meta-ads-setup` | "set up my ads", "ads setup", "resume setup", "switch brand" | none | `.superengine` marker, `setup.*`, connections audit; resumable |
| `meta-ads-guide` | "show me around meta ads", "ads tour" | none | guided tour → first deliverable |
| `meta-ads-teach` | "teach level", "less hand-holding" | none | `~/.claude/revxl/teach-level` (+ legacy dual-write) |
| `meta-ads-next` | "what's next", "where am I" | none | ranked moves from state + this map |

### Strategy (7)
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `meta-ads-stage-check` | "what stage am I in", "stage check" | `setup.spend_level` | `stage` |
| `meta-ads-breakeven-math` | "run my numbers", "breakeven math" | `setup.offer` + `setup.price` | `targets.*` (`targets_version`++) |
| `meta-ads-funnel-qualify` | "qualify my leads", "funnel strategy" | `targets` set | `funnel.*` (event spec; GHL fast-path or CRM-neutral) |
| `meta-ads-lead-questions` | "write my lead questions" | `funnel.qualification_gate` | form/quiz question set (uses real money-gate number) |
| `meta-ads-signal-setup` | "set up tracking", "pixel and capi" | `funnel.qualified_event` | `signal.*` (Pixel+CAPI dual, dedup, EMQ direction) |
| `meta-ads-compliance-check` | "compliance check" · triage sub-mode: "my ad got rejected", "account restricted" | `setup.offer` | `compliance[]` entry — **always live policy check** |
| `meta-ads-campaign-plan` | "plan my campaign" | `targets` + `stage` | `campaign_plan` artifact (stage-appropriate structure) |

### Creative (9) — orbits the hub
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `meta-ads-creative-strategy` | "creative strategy", "plan my creatives" | `targets` (reads voc/) | PDA matrix → stage-keyed concept count (S1 3–5 ... S4 15–25+; stage unset → S1 labeled); `creatives[]` concept rows |
| `meta-ads-hook-writer` | "write hooks" | concept rows exist | hooks on avatar/offer, voice-matched |
| `meta-ads-ad-copy` | "write my ad copy" | concept rows exist | primary text + headlines (5-slot in-ad variants) |
| `meta-ads-static-ads` | "make static ads" | concept rows exist | static layouts (safe zones 14/35/6, 4:5) |
| `meta-ads-video-script` | "write my video script" | concept rows exist | scripts (15–30s + 90–120s VSL, bipolar) |
| `meta-ads-creative-test` | "test my creatives" | `creatives[].live_at` | dimensional test plan / CT-Tool micro-variants; dual-clock verdicts |
| `meta-ads-competitor-intel` | "competitor ads", "spy on competitors" | own PDA exists (**never before**) | roster (`competitors[]`) + observations seed + longevity ladder → feeds hub. free via Ad Library (MCP-connected or hand-browse); ✋ SocialCrawl enrichment optional |
| `meta-ads-competitor-pulse` | "competitor pulse", "what changed in my niche", "add a competitor", "remove a competitor" | `competitors[]` non-empty | delta brief (new/disappeared/promoted ads) + updated observations |
| `meta-ads-best-content` | "mine my winners", "my best content" | `setup` done | own-winner analysis → feeds hub. ✋ credit-gated crawl |

### Launch (1)
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `meta-ads-launch-runbook` | "launch my campaign", "launch it", "I turned my ads back on" | **GATE:** `campaign_plan` + `compliance` pass @ current `offer_version` + `funnel.qualified_event` | guided Ads-Manager click-path (paused→published); writes `launched_at` + `creatives[].live_at` |

### Ops (5)
| Skill | Trigger phrases | Prereqs (state) | Produces |
|---|---|---|---|
| `meta-ads-ops-setup` | "connect ads manager", "ops setup" | `setup` done | MCP (client, OAuth; server-side write gate) / CLI (operator) hookup; manual-paste stays first-class |
| `meta-ads-daily-brief` | "daily brief", "how are my ads doing" | `launched_at` (runbook or F5 import backfill) | 60-second glance; S1 = read-only + 72h lockout enforcement; `bad_day_counter` |
| `meta-ads-kpi-tracker` | "show my trends" | `targets` | kpi-log.json append + trend render (data layer; invoked BY brief/review) |
| `meta-ads-performance-review` | "review my ads", "weekly review" | `launched_at` (or import mode) | diagnosis vs stage framework → ROUTES to the fix; `last_review` |
| `meta-ads-scale-decision` | "should I scale" | `kpi_log` evidence | stage-exit audit; raise-in-place ≤20%/48–72h; 20% testing-budget guardrail |

## Edge registry

Happy-path edges (E) + failure edges (F). Failure edges are load-bearing —
they are what makes this the no-dead-end reference implementation.

### Generic
| ID | From · condition | Routes to |
|---|---|---|
| E0 | ANY skill · prereq missing (skip-ahead attempt) | the skill that produces the missing prereq, with a plain-English why ("write me ads" pre-setup → setup) |
| E0b | ANY skill · deliverable done | next-moves per `routing.md`: #1 = the journey's next unmet step for this state |

> **E0b coverage (secondary & non-happy terminals):** a skill's non-#1
> next-move options, plus decline / hold / insufficient-evidence / sub-mode
> terminals (e.g. stage-check "advance requested, evidence missing",
> ops-setup "declined", scale-decision HOLD / CEILING, performance-review
> monthly-audit, the E12 exit-audit fix-routes) all route via **E0b** —
> compass-ranked moves from current state. They do NOT each get a bespoke
> edge ID; E0b is their registry row. Named cross-skill lateral doors between
> the creative skills are the exception — those are listed on E10/E11/E19.

### Happy path
| ID | From · ending | Routes to |
|---|---|---|
| E1 | start · first-run detected | guide (primary; setup primary when the opener signals existing ads — F5 onramp) · setup · next |
| E2 | start · returning user | next (primary) · resume open_loops · named skill |
| E3 | setup · minimal-viable reached (offer+price+spend) | breakeven-math (primary) · finish remaining setup · guide |
| E4 | setup · paused mid-interview | resume setup ("we're N% through") · breakeven-math if minimal met |
| E5 | breakeven-math · targets computed | funnel-qualify (primary) · stage-check · compliance-check (early, parallel-safe) |
| E6 | funnel-qualify · event spec written | lead-questions (primary) · signal-setup |
| E7 | lead-questions · question set delivered | signal-setup (primary) · compliance-check |
| E8 | signal-setup · dual-tracking live | compliance-check (primary) · creative-strategy |
| E9 | compliance-check · PASS recorded | creative-strategy (primary, if no creatives) · campaign-plan (if creatives exist) · launch-runbook (if plan exists) |
| E10 | creative-strategy · concepts locked | hook-writer / ad-copy / static-ads / video-script (per concept format mix) · best-content (feed the hub) · competitor-intel (field view, once own PDA exists) |
| E11 | any production skill · asset delivered | next unproduced concept (primary) · campaign-plan (when S1 concept count met, 3–5) · another format for this concept · best-content (mine winners for Post-ID reuse) |
| E12 | stage-check · stage diagnosed | campaign-plan (primary) · scale-decision (if S3/4 exit-criteria question) |
| E13 | campaign-plan · plan artifact written | launch-runbook (primary — if gate met) · missing gate item (compliance/funnel) via E0 |
| E14 | launch-runbook · campaign live (published) | daily-brief tomorrow (primary) + the 72h do-not-touch speech · kpi-tracker baseline |
| E15 | daily-brief · normal day | nothing to do (S1: numbers + hands-off) · performance-review if review day · next |
| E16 | performance-review · verdict delivered | the diagnosed fix: creative-strategy (fatigue) / signal-setup (weak signal) / scale-decision (exit criteria met) |
| E17 | scale-decision · raise approved | raise-in-place instructions · daily-brief cadence · creative pipeline check (creative-strategy) |
| E18 | creative-test · verdict (dual-clock) | replicate→iterate→net-new priority: creative-strategy iterate (primary) · kill+replace via production skills |
| E19 | competitor-intel / best-content · intel delivered | creative-strategy (feed the PDA — the only intel CONSUMER, primary) · lateral doors: production skill (a proven angle → an unproduced concept) · the sibling intel skill (best-content ⇄ competitor-intel cross-check) · campaign-plan (a launch-ready organic winner runs via Post ID) |
| E20 | ops-setup · connection state changed | performance-review (data now flows) · daily-brief · back to caller |
| E21 | teach · level changed | back to what you were doing (session resumes) · next |
| E22 | guide · tour done | setup (primary if incomplete) · first deliverable per state · next |
| E23 | kpi-tracker · trends rendered | back to caller (brief/review) · scale-decision if exit criteria trending met |
| E24 | competitor-pulse · delta delivered | creative-strategy (a proven/promoted angle maps to the matrix, primary) · teardown nominations (6mo+ promotions, ✋ effort-gated) · roster ops (add/remove) · back to caller |

### Failure edges
| ID | From · condition | Routes to |
|---|---|---|
| F1 | compliance-check · FAIL / category triggered | fix path (offer framing / creative changes, explained) → re-run compliance-check. LAUNCH stays blocked. |
| F2 | performance-review · junk-leads diagnosis (CRM disagrees with Meta) | funnel-qualify (tighten gate) → signal-setup (verify event) |
| F3 | performance-review / scale-decision · actuals diverge from setup assumptions (close rate, show rate) | breakeven-math re-run → `targets_version`++ cascades: consumers must re-check against new targets |
| F4 | creative-test / performance-review · S1 total failure (all concepts dead at kill window) | creative-strategy new batch (primary). SECOND total failure → breakeven-math + funnel-qualify re-check (the problem is offer/funnel, not creative) |
| F5 | setup · `currently_spending: true` (already-running coach) | onramp: import history → stage-check → backfill state (incl. `launched_at`, via performance-review import mode) — **WITHOUT pausing live campaigns** |
| F6 | breakeven-math · no-go (math doesn't work at any realistic CPL) | honest exit: revisit offer/price in setup (primary) · park ads ("your economics don't support paid traffic yet — here's the number that has to change") |
| F7 | daily-brief · `bad_day_counter` reaches 3 | performance-review (mandatory before any cut) · bad-day protocol: cut ≤20%, never below `targets.hard_deck` |
| F8 | launch-runbook / daily-brief / performance-review · ad rejected or account restricted | compliance-check **rejection-triage sub-mode** (live policy lookup, appeal path, don't-touch-warnings) |
| F9 | any Brain-wired step · API degrade (401/403/429/503/timeout) | proceed on bundled refs + one-line notice per `vault-api.md` — never blocks the journey |
| F10 | any voice-consuming skill (creative production OR lead-questions) · voc/ absent | reuse `voice_sketch` if present (low confidence, no re-interview) · else offer voice capture (brand-brain if installed, else minimal inline interview, write `voice_sketch`) · capture declined → proceed and do not re-offer this session (label only) · proceed labeled "voice confidence: low" — never silently generic |
| F11 | compliance-check · unverified (live policy lookup unavailable) | keep building in parallel (creative-strategy) · re-run when back online (compliance-check). LAUNCH stays blocked until a real pass. |

## Gates (hard blocks, checked in state)

| Gate | Condition | Blocked skill | Unblock route |
|---|---|---|---|
| LAUNCH | `compliance[]` pass matching current `offer_version` AND `funnel.qualified_event` set AND `campaign_plan` exists | launch-runbook | E0 to whichever is missing |
| SCALE | `kpi_log` evidence exists (never vibes) | scale-decision (raise path) | kpi-tracker + wait window |
| S1 ops | `stage == 1` → daily-brief is READ-ONLY; optimization actions unlock stage ≥2 | daily-brief actions | stage-check re-diagnosis |
| Competitor | own PDA exists (`creative-strategy` completed) | competitor-intel · competitor-pulse (transitive: empty `competitors[]` → intel builds the roster → PDA gate) | E0 → creative-strategy |

## Cross-plugin triggers (external — detect-first, one line when absent)

Blocks may quote these ONLY behind an *installed* conditional:
- "build my brand brain" — the bundled/sibling brand-brain skill (voc/ producer).
- "write a reel script from my analysis" — shortform-superengine (organic reels).
- Carousel slide production — carousel-superengine (pointer line, no trigger quote).

## Maintenance

Adding a skill or ending: add the roster row + registry row HERE first, then
write the skill's inline next-moves block to match. Build verification greps
for trigger phrases hardcoded outside this file (premortem #2).
