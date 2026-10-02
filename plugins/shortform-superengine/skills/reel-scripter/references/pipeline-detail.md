# Pipeline detail ... the prose that moved out of SKILL.md

Moved at 0.4.0 and 0.4.2 to bring `skills/reel-scripter/SKILL.md` under the 20,000-byte compaction
ceiling; 0.4.2 also adds detail that lives only here. Moved text was lightly edited (em dashes became "...", paths re-pointed to this file): each section is the text that used to
sit inline at the step named in its heading. `SKILL.md` keeps every step, checkpoint and
guardrail plus a one-line pointer; this file keeps the detail.

## Overview

`reel-scripter` is the **Shortform** format engine. It never guesses what to post: it reads
what already wins in the client's niche (from a `competitor-cross-reference` run) and writes
one reel in the client's own voice off that evidence.

## Inputs

The three layers `reel-scripter` stands on (`SKILL.md`, Overview):

- **The analysis** ... `<project>/analysis-data.json` (the core→format interface produced by
  `competitor-cross-reference/analyze.py`). Ranked gaps, winning hook types, theme×hook,
  outliers, opener patterns. This is the *what to say* layer.
- **The brief** ... `reel-scripter/scripting_brief.py` distils that JSON (+ transcripts when
  present) into `<project>/scripting-brief.md`: attack themes, winning hooks, opener
  patterns, winning structures, length targets. This is the *how it's working* layer.
- **The voice** ... shared `voc/` artifacts (`voice-guide.md`, `voc-profile.md`,
  `business-config`) when available; **degrades** to a fast interim voice-anchor capture
  when they aren't. This is the *sound like the client* layer.

## Definition of done

It is a **guided, checkpointed** pipeline ... you pause for a human decision at each ✋ before
spending the next move. One run = one finished reel script written to `<project>/scripts/<slug>.md`.

> **Definition of done:** a reel script the client could film today ... hook that earns the
> first 3 seconds, a body built on a structure the niche has proven, a CTA matched to the
> goal, a caption, and an honest craft-score + flow-check ... all in the client's voice.

## Method precedence ... the skills, the Vault, Goldmine data

reel-scripter runs the steps; the method lives in the five skills (angles, hook, rehooks,
polarize, viral). Three voices can speak on method: (1) the skills plus the rulings built
into this plugin, (2) the Vault, (3) Goldmine data (`<project>/reel-build/goldmine-run.json`
with `reads.passed` true). When they disagree on method, 2 of the 3 decide. With no
Goldmine data, the skills and the rulings win, and the Vault point is shown to the user as
a suggestion. Vault hits go into the hook call as data, never as rules. At Checkpoint 0,
where Vault doctrine and the brief's local stats disagree, the brief says so in one
sentence and ranks the doctrine first.

## Step 0b ... what the brief writes, and its two modes

This writes `<project_dir>/scripting-brief.md`. Read it ... it is your menu of proven moves, and
its **§8 Avoid list is this niche's own losers** (hooks/themes/opening vocabulary the field
punishes) ... every option you generate later is screened against it.
It auto-detects **FULL** mode (spoken transcripts present) vs **CAPTION-ONLY** degrade
(no transcripts ... structures inferred from captions, flagged in a banner).
When analysis-data.json flags `degraded`, the brief carries a DEGRADED line: Sections 1-3 and
the §8 hook/theme losers are provisional.

## Step 0c ... resolve the voice, the full read rules

**0c. Resolve the voice.** In priority order:
1. Shared `voc/` artifacts ... `voice-guide.md` (rules/tone), `voc-profile.md` (verbatim
   audience pains, vocabulary, phrases to use/avoid), `business-config` (offer, ICP, CTAs).
   Check the shared brand brain FIRST ... `~/.claude/revxl/<brand>/voc/` (brand slug from the
   onboarding marker/config; a brain built from ANY engine lives here) ... then the project,
   then the workspace-level `voc/` if one is wired. On read: compute `days_since_update`
   from the stamp; >7 days → surface the age + offer a brand-brain refresh ONCE, never gate
   scripting on it. If the stamp says `provisional: true` (fewer than 3 sources mined),
   treat rankings and voice reads as hypotheses ... confirm with the user instead of leaning
   bold. Never quote `voc-profile.md` "Mirror Language (hypothesis)" entries as audience
   VoC ... that's the client's own phrasing about themselves, not their market's.
2. **Interim capture (degrade)** ... if no `voc/`, capture a lightweight voice anchor now:
   either 3 to 5 of the client's own top captions/transcripts (already in the project) **or** a
   4-question voice Q&A (Who are you talking to? What do you say that they don't expect? What
   words do you never use? What's your one CTA?). Note in the final script that voice was
   interim, not the full profile.

The refresh is offered only when `declined_offers` holds no `voc_refresh:<voc.refreshed_at>`
entry. Proceeding without the offered refresh records that entry in
`declined_offers` (entry shape: `../../_shared/references/state-schema.md`), written at
once at Step 0c and not at the end, so an abandoned run still keeps the decline and the
compass does not offer it again.

## Step 1 propose ... the angle shape

From `scripting-brief.md`, propose **2 to 3 concrete reel angles**, each = {attack theme ×
winning hook type × the gap it closes}, with the evidence cited (`@handle · metric · reel URL`
from the analysis). Example shape: *"Myth-bust on [under-served high-value theme] ... the field's
myth-bust hooks median Nx the client's; closes the [gap] gap."*

**Widen the set with `angles` first.** Before proposing, call the angles skill once with the Skill tool (its stamp counts only from that call plus a Read of its method file):

```
Skill: shortform-superengine:angles
args:  step: 1
       topic: <the reel's topic, or the brief's top attack theme>
       voice: <the voice anchor confirmed at Checkpoint 0>
       pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json, only when its reads.passed is true; else leave this line out>
       used: <the (theme, hook) pairs already scripted>
```

Its concepts feed the 2 to 3 proposals, each still carrying the brief's evidence. The stamp is
recorded automatically in `<project>/reel-build/provenance.md` when you call the skill with the
Skill tool and then Read its method file (the Checkpoint 1 gate reads it there); never write or edit a `from:` line yourself. The
(theme, hook) dedupe rule in `SKILL.md` Step 1 governs: a concept whose pair is already used
is dropped or named as a deliberate repeat, whatever angles ranked it. A myth-bust or
contrarian angle is proposed as it stands; `polarize` runs at Step 2, for its Other side beat.

## Step 1 field vet ... the report and the verdict branches

**Custom-idea field vet (mandatory when the user brings their OWN topic).** A brief-derived
angle is already field-backed; a user-supplied idea is NOT ... vet it before committing beats.
Run its topic word(s) through the field:

The `field_vet.py` invocation itself is in `SKILL.md` Step 1.

It reports, per keyword, the per-account lift (each competitor's matching reels vs that
account's own median; competitors only, the client's own reels excluded; spoken track PRIMARY,
captions a separate read ... the C7 weighting) + a verdict. Pass the obvious frame word AND its
adjacent candidates (e.g. `carousel design template canva`) so a losing frame surfaces its winning
neighbor. Keywords match whole words, so pass a plural as its own keyword. This is the topic-level twin of §8's hook-level firewall: §8 screens hook *type*, this
screens topic *frame*. **The idea is never vetoed ... only the framing adapts.** Branch on the verdict:

- **WINNER / NEUTRAL** → field-backed. Proceed; frame on the strongest winning word.
- **LOSER (has data, underperforms)** → the field has *tried* this and it flops. **Pivot, don't
  ditch:** keep the creator's core idea, present **2 to 3 data-backed adjustments** (reframe the
  headline to the strongest adjacent WINNER, and/or swap to a proven hook type, and/or narrow to
  the sub-angle that wins) with the numbers. The user picks; you never silently override. If no
  WINNER is in the vetted set, the script says so: re-run with adjacent frame words before
  reframing toward the strongest adjacent WINNER.
- **UNTESTED / THIN / NONE (little or no field data)** → **do NOT treat as a loser.** No data ≠ bad
  idea ... it may be genuinely new or timely (fresh news, a just-shipped tool, first-to-market), which
  is a first-mover *edge*, not a red flag. Two moves: (1) say plainly it's untested ... upside and
  risk both live in the unknown; (2) **de-risk without killing it** ... ride the novel topic on a
  *proven hook type* + the *nearest proven frame word* so the novelty gambles on content, not also
  on structure. Offer that as the safer build; let the user choose bold-novel vs de-risked-novel.
  This branch applies only when the spoken track exists. With zero spoken rows the script
  prints DEGRADED and a caption-only `[cap]` verdict: `THIN/NONE [cap]` is unknown, never
  relayed as a first-mover edge, and a `[cap]` WINNER is a packaging read, not a topic read.

Thin n (<5) counts as UNTESTED, not LOSER ... a handful of reels is a hint, never a rule.

## Step 1 deeper field layer ... the socialcrawl-superengine hand-off

**Deeper field layer (optional, detect-first).** With socialcrawl-superengine installed
(the two-step probe is in `../../_shared/references/socialcrawl-endpoints.md`),
`research-plays` widens the angle set. Absent, do not fake it: hand off to the compass ... say
"what's next in shortform" and it renders the F9 install refusal (edge F9), then continue on
the analysis.

## Step 2 ... structure to beats, and the four screens

For the chosen hook type, pull the matching body skeleton from
`./body-structures.md` (organized by hook bucket: question, numbered/list, myth-bust/negation,
contrarian/curiosity, pain-callout, personal/story, statement). That bucket is the skeleton's
`angle_kind:` line. When the reel's goal matters more than its hook shape, its "By intent"
section gives three shapes by goal; `angle_kind:` stays the hook bucket of the angle picked
at Checkpoint 1. Lay out the beat
list for THIS reel: `Hook → Secondary hook → Body beat 1..n → Proof → CTA`, plus the Other
side beat on a myth-bust or contrarian reel (below). Where the secondary hook and each
re-hook sit comes from `rehooks`, below. Keep it to the length
target the brief gives (most winning reels are short ... respect it).

**Re-hook placement comes from `rehooks`.** With the beat list laid out, call it once with the Skill tool (its stamp counts only from that call plus a Read of its method file) for
the drop-off map and the slots. For each slot (the secondary hook, then each mid-reel
re-hook) it returns where it sits (the beat and the time), the re-hook type and the visual
change:

```
Skill: shortform-superengine:rehooks
args:  step: 2
       script: <the beat list, labels and estimated times, no copy yet>
       length: <the brief's length target>
       voice: <the voice anchor confirmed at Checkpoint 0>
       pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json, only when its reads.passed is true; else leave this line out>
```

The stamp is recorded automatically when you call the skill with the Skill tool and then Read its method file; never write or edit a `from:` line yourself.
In the skeleton, replace `visual_loop: none` only when a visual loop carries the tension,
and tag that loop on its beats too.
Take each slot, with its type and its visual, into the beat list. No lines yet: `rehooks`
writes them at Step 3 (`./step3-options.md`, the secondary-hook pass).

**The Other side beat comes from `polarize`.** When the skeleton's `angle_kind:` is
`myth-bust/negation` or `contrarian/curiosity`, the beat list carries one beat labelled
`Other side`, right after the secondary hook and before the turn (Hook, Secondary hook,
Other side, Turn), tagged `[hold <main loop>]`. It is one line naming what the other camp
believes or does. It need not be fair: a straw man is fine, a made-up fact is not. It does
not count against the length budget. Call `polarize` once with the Skill tool (its stamp counts only from that call plus a Read of its method file) for its line; this call is
required for those two kinds (the Step 4b gate fails without its stamp):

```
Skill: shortform-superengine:polarize
args:  step: 2
       angle: <the locked angle>
       beats: <the beat list, with the Other side beat in place>
       stance: <the belief, in the creator's own words, when given>
       evidence: <the creator's evidence, when given>
       voice: <the voice anchor confirmed at Checkpoint 0>
       pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json, only when its reads.passed is true; else leave this line out>
       competitors: <the three closest competitors from the analysis>
```

It returns the line for the Other side beat, and, when the take holds, the sharpened take
and its evidence list (they feed the angle line and the body). When it flags the take as
thin, show the flag at Checkpoint 2; the user decides. Keep the line for Step 3, where it
fills the Other side beat as it came. The stamp is recorded automatically when you call the
skill with the Skill tool and then Read its method file; never write or edit a `from:` line yourself. An Other side beat on any
other kind needs this call too.

**Optimize the skeleton BEFORE showing it (mandatory).** A raw beat list is a draft, not the
skeleton ... screen it against the brief's proven structure the same way Step 3 screens options,
then present the TIGHTENED version with a one-line why per change. Never hand the user an
un-optimized skeleton and wait to be asked. The four screens:
- **One idea, not a list (brief §5).** Winners develop a single mechanism, not five. If the body
  carries 3+ separate develop/proof beats, collapse them ... a demo that IS the proof is one beat,
  not two; two half-payoffs read weaker than one full one.
- **Length budget (brief §6).** Beat count must fit the seconds target (~one beat per 8 to 12s of
  talk). Over budget → merge or cut, never pad to fill. The Other side beat is exempt.
- **One loop, paid late.** The hook opens the curiosity loop; no beat may resolve it early.
  The secondary hook DEEPENS the loop, never answers it. The full payoff aims for the final
  beat; anywhere in the last third passes the gate.
- **Single lever (no second idea).** Kill any beat that introduces a second topic ("…and also
  what it costs") ... that's a different reel. One reel, one lever.
State what you trimmed and why ("6 → 5: merged demo+receipt ... one payoff, not two"). The user
still owns Checkpoint 2 and can override any trim (their call beats the data) ... but they approve
an already-optimized skeleton, not a raw dump.

## Step 4a ... the viral pass (every reel), then the hook lens

**4a. The viral pass, on every reel.** After the Step 3 picks and before the Step 4b gate,
call `viral` once with the drafted lines. Call it with the Skill tool: its stamp counts only from
that call plus a Read of its method file, and reading a skill's files for its stamp line is a failed run.

```
Skill: shortform-superengine:viral
args:  step: 4a-viral
       script: <the drafted lines: the Step 3 picks in beat order>
       final: yes (the skeleton is locked; suggestions only, each paired with its exact line)
       voice: <the voice anchor confirmed at Checkpoint 0>
       pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json, only when its reads.passed is true; else leave this line out>
```

It returns suggestions, each paired with the exact line it would replace, plus the share
type and three scores. Show them; the user picks which apply, and only those are applied.
None adds, cuts or reorders a beat. A suggestion on a line another skill wrote (hook,
rehooks, polarize) says so. The stamp is recorded automatically when you call the skill with
the Skill tool and then Read its method file (the Step 4b gate fails without it); never write or edit a `from:` line yourself. The share type and
the three scores go to Checkpoint 4 beside the craft score.

**Then the hook lens ... the 4 Hook Killers.** Run the hook through
`../../_shared/references/hook-diagnostics.md`: does it lose on **DELAY** (payoff too late),
**CONFUSION** (ambiguous/jargon), **IRRELEVANCE** ("I"-framing, no viewer benefit), or
**DISINTEREST** (no open question: no A-vs-B tension)? Flag any that fire and show why.
Never rewrite the hook here: a fix is one more `hook` call carrying what fired
(`./step3-options.md`, the hook pass).
Re-scan the full assembled wording (hook, body, CTA, caption, overlays) against the brief's §8 Avoid list
and the universal losing tables ... line edits and voice phrasing are not exempt. When a §8
layer reads "no confident avoid", it screens nothing: `./step3-options.md` pass 2, "Screen".

## Step 4b ... loop integrity, the walk and the fail conditions

**4b. Loop integrity ... open/close looping (mandatory, run before the flow read).** The #1 retention
mechanic is keeping a curiosity loop open at ALL times ... a loop may only resolve once the next is
already open and pulling. Walk the beat **seams** (the gap between every pair of adjacent beats) and
label, at each seam, which loop is still OPEN. Fail conditions to fix before Checkpoint 4:
- **Dead seam** ... a seam where every loop opened so far is already resolved and no new one is open.
  The attention drops there. Fix: hold a reveal longer, or put a re-hook at that seam so a loop
  is live across it; `rehooks` writes it (below).
- **Early close** ... the reel's spanning loop pays off before the last third. Hold the payoff later.
- **Flat run** ... 2+ consecutive beats that are pure declaration with no forward pull. Convert one
  into a question-chain link that opens the next beat.

Rule: from the hook to the CTA there is never a moment with zero open loops. The spanning loop
(opened at hook or secondary) aims to resolve in the final beat; a payoff anywhere in the
last third passes the gate.

**The gate's other exits.** Exit 2: rewrite the file in the Checkpoint 2 shape, re-run ("can't
open file" = wrong path: fix it). No Python at all: say so and stop; a hand walk cannot check
stamps.

**Stamps live in `<project>/reel-build/provenance.md`.** Each called skill (angles, rehooks at
Step 2 and again at Step 3, hook, polarize when the angle needs it, viral) gets its `from:`
line recorded there automatically when you call it with the Skill tool and then Read its method file; never write or edit a `from:` line yourself. The
only lines you write to that file are `goldmine:` lines, written by the hook skill's step. A
`from:` line in the skeleton or the angles file fails the gate. The gate reads the stamps there and
clears them on a pass. After a pass the file holds one `passed:` line for that skeleton, so a
re-run on the same skeleton passes, and the next reel needs its own calls and its own stamps.
A skeleton changed after it passed needs fresh stamps too. Run the `--angles` check once,
before Checkpoint 1: on a pass it trims the file to the angles line.

**`rehooks` writes the fix for each dead seam.** For every dead seam the gate or the walk
names, call it once with the whole draft:

```
Skill: shortform-superengine:rehooks
args:  step: 4b
       script: <the assembled draft>
       final: yes (the skeleton is locked)
       dead_seams: <each dead seam, as the two beats it sits between>
       voice: <the voice anchor confirmed at Checkpoint 0>
       pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json, only when its reads.passed is true; else leave this line out>
```

It returns one re-hook proposal per dead seam, anchored to the exact line it follows. Apply
the ones the user accepts; a beat added, cut or moved is still the user's call.

## Step 4c and 4d ... flow-check, skeleton integrity, craft score

**4c. Flow-check + skeleton integrity.** Read the script top to bottom as a viewer: does each
beat earn the next? Any dead beat, any place the attention drops ... flag and tighten (another skill's line: flag it, never rewrite it). Then
confirm the draft matches the Checkpoint-2 skeleton **beat-for-beat** (no beat added / cut /
reordered, no move softened) ... any drift gets flagged at Checkpoint 4. A change the **user**
asks for at Checkpoint 4 is always allowed ... the lock binds voice, not the user.
Re-hook timing (the `rehooks` rhythm, about one every 30 s at any length): flag a stretch of
40+ s with no spoken re-hook, only in reels long enough to have one. Guidance, never a hard fail.

**4d. Craft score.** Score **Hook / Body / CTA / overall (0 to 100)** against the **Story Locks rubric**
(`./story-locks.md`): how many of the 4 Story Locks + 6 Swaps the script lands (contrast,
zero hedges, a negative frame where the content calls for it, re-hooks at rehooks' slots,
viewer-framing). This is an
honest **craft** read, **not** a performance prediction: it never claims views. State the one
highest-leverage fix. *(This is the **single** craft score for the script ... the dashboard's Scripting
Studio displays it, it does not recompute its own.)*

## Step 5 template ... the script file shape

`<project>/scripts/<slug>.md`, slug = short kebab of the angle:

```
# <Reel title / angle>
> Voice: <full voc | interim>  ·  Mode: <full | caption-only>  ·  Angle: <theme × hook>

## On-screen hook
## Script
  Hook:
  Secondary:
  Other side:  <on myth-bust/negation and contrarian/curiosity reels>
  Body:
  Proof:
  CTA:
## Text overlays
  | Beat | Seconds | Overlay | Visual cue |
  <one row per 3 to 5 s, one visual cue per row; every script section gets a row; times run
   back to back from 0:00; frame-1 overlay = the on-screen hook, not the spoken hook>
## Caption
## Craft score
  Hook __/100 · Body __/100 · CTA __/100 · Overall __/100 ... top fix: ...
## Evidence
  <@handle · metric · reel URL> citations from the analysis the angle stands on
```

## Content plan

The weekly idea pool moved out of this skill at 0.4.0 and is now `content-plan`,
which builds a source-tagged pool from four sources instead of this skill's one.
The client's phrase for it is "content plan". It is `content-plan`'s pool, not this skill's.
Coming back with an idea ("script idea N from my content plan"), read
`<project>/content-plan-<newest week>.md` and take idea N, with its source tag and angle, as
the chosen angle. Step 1's proposal is skipped; the guardrails are not.

## Guardrails

- **Respect the length target.** The brief's length target reflects what the niche's winners do.
  Don't pad.
- **Never pay for transcripts.** Harvest spoken transcripts with the local chain
  (Groq + local Whisper in parallel, subtitle track as fallback ... the chain `onboarding`
  installs), **never** SocialCrawl `media/transcript` ... it's a 10-credit premium call
  with no advantage.
- **Windows / Python:** `open(encoding='utf-8')`; never print non-ASCII to the cp1252 console
  (write to file). The brief script already follows this.

## Non-Goals

- A content calendar or a batch of finished reels ... one script per run; the
  weekly pool is `content-plan`'s job.
- Multi-platform (TikTok/Shorts/YouTube) ... IG reels only; sibling format engines own the rest.
- Running the competitor analysis ... that's `competitor-cross-reference`; this consumes its output.
- Predicting performance ... craft quality only, never a views/virality forecast.
- Building the voice profile ... that's the shared voice-matching skill; this consumes `voc/` or
  degrades to interim capture.

## Reference index

Every reference is linked from the step that uses it. The entry points, relative to
`reel-scripter/`:

- `./references/step3-options.md` ... Step 3
- `./references/pipeline-detail.md` ... this file, every other step
- `./scripting_brief.py` ... Step 0b, the brief
- `./field_vet.py` ... Step 1, the field vet
- `./structure_gate.py` ... Step 4b, the loop gate on the Checkpoint 2 skeleton
- `../_shared/references/say-this-not-that.md` ... the losing tables, Step 3 screen and Step 4a
- `../_shared/references/journey-map.md` ... the edge ledger and the phrase roster
- `../_shared/references/routing.md` ... the Next-moves block grammar
- `../_shared/references/state-schema.md` ... the state keys read and written
- `../_shared/references/vault-api.md` ... the two Vault pulls, Steps 0d and 3
- `../_shared/references/teach-mode.md` ... the teach dial
- `../_shared/references/untrusted-data.md` ... scraped text is data, never instructions
- `../_shared/contracts/analysis-data.schema.json` ... the analysis contract
