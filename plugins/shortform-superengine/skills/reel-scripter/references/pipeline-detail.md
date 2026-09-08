# Pipeline detail ... the prose that moved out of SKILL.md

Moved at 0.4.0 to bring `skills/reel-scripter/SKILL.md` under the 20,000-byte compaction
ceiling. Nothing here is new and nothing was reworded: each section is the text that used to
sit inline at the step named in its heading. `SKILL.md` keeps every step, checkpoint and
guardrail plus a one-line pointer; this file keeps the detail.

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

## Step 0b ... what the brief writes, and its two modes

This writes `<project_dir>/scripting-brief.md`. Read it ... it is your menu of proven moves, and
its **§8 Avoid list is this niche's own losers** (hooks/themes/opening vocabulary the field
punishes) ... every option you generate later is screened against it.
It auto-detects **FULL** mode (spoken transcripts present) vs **CAPTION-ONLY** degrade
(no transcripts ... structures inferred from captions, flagged in a banner).

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

Proceeding without the offered refresh records `voc_refresh:<voc.refreshed_at>` in
`declined_offers` (entry shape: `../../_shared/references/state-schema.md`), written at
once at Step 0c and not at the end, so an abandoned run still keeps the decline.

## Step 1 propose ... the angle shape

From `scripting-brief.md`, propose **2 to 3 concrete reel angles**, each = {attack theme ×
winning hook type × the gap it closes}, with the evidence cited (`@handle · metric · reel URL`
from the analysis). Example shape: *"Myth-bust on [under-served high-value theme] ... the field's
myth-bust hooks median Nx the client's; closes the [gap] gap."*

## Step 1 field vet ... the report and the verdict branches

**Custom-idea field vet (mandatory when the user brings their OWN topic).** A brief-derived
angle is already field-backed; a user-supplied idea is NOT ... vet it before committing beats.
Run its topic word(s) through the field:

The `field_vet.py` invocation itself is in `SKILL.md` Step 1.

It reports, per keyword, the field's median views vs the field median (spoken track PRIMARY,
captions a separate read ... the C7 weighting) + a verdict. Pass the obvious frame word AND its
adjacent candidates (e.g. `carousel design template canva`) so a losing frame surfaces its winning
neighbor. This is the topic-level twin of §8's hook-level firewall: §8 screens hook *type*, this
screens topic *frame*. **The idea is never vetoed ... only the framing adapts.** Branch on the verdict:

- **WINNER / NEUTRAL** → field-backed. Proceed; frame on the strongest winning word.
- **LOSER (has data, underperforms)** → the field has *tried* this and it flops. **Pivot, don't
  ditch:** keep the creator's core idea, present **2 to 3 data-backed adjustments** (reframe the
  headline to the strongest adjacent WINNER, and/or swap to a proven hook type, and/or narrow to
  the sub-angle that wins) with the numbers. The user picks; you never silently override.
- **UNTESTED / THIN / NONE (little or no field data)** → **do NOT treat as a loser.** No data ≠ bad
  idea ... it may be genuinely new or timely (fresh news, a just-shipped tool, first-to-market), which
  is a first-mover *edge*, not a red flag. Two moves: (1) say plainly it's untested ... upside and
  risk both live in the unknown; (2) **de-risk without killing it** ... ride the novel topic on a
  *proven hook type* + the *nearest proven frame word* so the novelty gambles on content, not also
  on structure. Offer that as the safer build; let the user choose bold-novel vs de-risked-novel.

Thin n (<5) counts as UNTESTED, not LOSER ... a handful of reels is a hint, never a rule.

## Step 2 ... structure to beats, and the four screens

For the chosen hook type, pull the matching body skeleton from
`./body-structures.md` (organized by hook bucket: question / myth-bust / listicle /
story / pain-callout / contrarian / statement). Consult `./retention-psychology.md`
to pick the post-hook structure by intent (Transformation Arc / Myth-Buster / Authority Solution)
and plan the loops: where the primary loop pays off, secondary-hook count + placement for the
length (strongest at the 12 to 15s window), and the beat-to-beat question chain. Lay out the beat
list for THIS reel: `Hook → Secondary hook → Body beat 1..n → Proof → CTA`. Keep it to the length
target the brief gives (most winning reels are short ... respect it).

**Optimize the skeleton BEFORE showing it (mandatory).** A raw beat list is a draft, not the
skeleton ... screen it against the brief's proven structure the same way Step 3 screens options,
then present the TIGHTENED version with a one-line why per change. Never hand the user an
un-optimized skeleton and wait to be asked. The four screens:
- **One idea, not a list (brief §5).** Winners develop a single mechanism, not five. If the body
  carries 3+ separate develop/proof beats, collapse them ... a demo that IS the proof is one beat,
  not two; two half-payoffs read weaker than one full one.
- **Length budget (brief §6).** Beat count must fit the seconds target (~one beat per 8 to 12s of
  talk). Over budget → merge or cut, never pad to fill.
- **One loop, paid late (`retention-psychology.md`).** The hook opens the curiosity loop; no beat
  may resolve it early. The secondary hook DEEPENS the loop, never answers it; the full payoff
  lands in the last third.
- **Single lever (no second idea).** Kill any beat that introduces a second topic ("…and also
  what it costs") ... that's a different reel. One reel, one lever.
State what you trimmed and why ("6 → 5: merged demo+receipt ... one payoff, not two"). The user
still owns Checkpoint 2 and can override any trim (their call beats the data) ... but they approve
an already-optimized skeleton, not a raw dump.

## Step 4a ... the hook lens in full

**4a. Hook lens ... the 4 Hook Killers.** Run the hook through
`../../_shared/references/hook-diagnostics.md`: does it lose on **DELAY** (payoff too late),
**CONFUSION** (ambiguous/jargon), **IRRELEVANCE** ("I"-framing, no viewer benefit), or
**DISINTEREST** (topic the audience doesn't care about)? Fix any that fire before scoring.
Re-scan the full assembled wording (hook, body, CTA, caption, overlays) against the brief's §8 Avoid list
and the universal losing tables ... line edits and voice phrasing are not exempt.

## Step 4b ... loop integrity, the walk and the fail conditions

**4b. Loop integrity ... open/close looping (mandatory, run before the flow read).** The #1 retention
mechanic is keeping a curiosity loop open at ALL times ... a loop may only resolve once the next is
already open and pulling. Walk the beat **seams** (the gap between every pair of adjacent beats) and
label, at each seam, which loop is still OPEN. Fail conditions to fix before Checkpoint 4:
- **Dead seam** ... a seam where every loop opened so far is already resolved and no new one is open.
  The attention drops there. Fix: hold a reveal longer, or plant a connective re-hook at that seam
  ("but that's not even the part that…", "here's what I didn't expect", "and that's when it got
  weird") so a loop is live across it.
- **Early close** ... the reel's spanning loop pays off before the last third. Hold the payoff later.
- **Flat run** ... 2+ consecutive beats that are pure declaration with no forward pull. Convert one
  into a question-chain link that opens the next beat.

## Step 4c and 4d ... flow-check, skeleton integrity, craft score

**4c. Flow-check + skeleton integrity.** Read the script top to bottom as a viewer: does each
beat earn the next? Any dead beat, any place the attention drops ... flag and tighten. Then
confirm the draft matches the Checkpoint-2 skeleton **beat-for-beat** (no beat added / cut /
reordered, no move softened) ... any drift gets flagged at Checkpoint 4. A change the **user**
asks for at Checkpoint 4 is always allowed ... the lock binds voice, not the user.

**4d. Craft score.** Score **Hook / Body / CTA / overall (0 to 100)** against the **Story Locks rubric**
(`./story-locks.md`) ... how many of the 6 Story Locks + 8 Swaps the script lands (contrast,
zero hedges, named framework, negative-frame, loop-openers at cadence, viewer-framing). This is an
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
  Body:
  Proof:
  CTA:
## Text overlays
  <beat → on-screen line table; frame-1 = the hook verbatim>
## Caption
## Craft score
  Hook __/100 · Body __/100 · CTA __/100 · Overall __/100 ... top fix: ...
## Evidence
  <@handle · metric · reel URL> citations from the analysis the angle stands on
```

## Content plan

The weekly idea pool moved out of this skill at 0.4.0 and is now `content-plan`,
which builds a source-tagged pool from four sources instead of this skill's one.
The client's phrase for it is "content plan".

## Non-Goals

- A content calendar or a batch of finished reels ... one script per run; the
  weekly pool is `content-plan`'s job.
- Multi-platform (TikTok/Shorts/YouTube) ... IG reels only; sibling format engines own the rest.
- Running the competitor analysis ... that's `competitor-cross-reference`; this consumes its output.
- Predicting performance ... craft quality only, never a views/virality forecast.
- Building the voice profile ... that's the shared voice-matching skill; this consumes `voc/` or
  degrades to interim capture.
