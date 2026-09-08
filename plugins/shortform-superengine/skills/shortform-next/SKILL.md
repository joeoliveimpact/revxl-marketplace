---
name: shortform-next
description: The compass for shortform-superengine. Reads the per-brand journey state and the journey map, says where the client is in one line, and returns 2 to 4 ranked moves with the exact phrase to say for each. Callable any time, from anywhere; reads everything and writes nothing. Trigger phrases include "what's next in shortform", "shortform next", "where am I in shortform".
---

# shortform-next ... the compass

The routing block on demand. This skill IS the ranking engine: other skills hand
a complicated mid-journey state to it instead of duplicating the logic.

## Load (in order)

1. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/journey-map.md` ... the roster, the edge registry, the gates. Every phrase below is quoted from that roster
2. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/routing.md` ... the block grammar and the eight rules
3. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/state-schema.md` ... key ownership, derived keys, the staleness constants
4. `~/.claude/shortform-superengine/.superengine` -> the active brand -> `~/.claude/shortform-superengine/state/<brand>.json`
5. `~/.claude/revxl/teach-level` (see Teach mode)

## Teach mode

```
level = read("~/.claude/revxl/teach-level").trim()          if it exists
   else map(read("~/.claude/revxl/teach-mode").trim())      if THAT exists
        where "beginner" -> "new", "off" -> "pro"
   else "new"
```

`new` (the default when neither file exists): plain English first, the term with
a one-line gloss on first use, and a one-line "why this is the move" under each
option. `learning`: plain English with the term inline, why on the big calls
only. `pro`: the position line and bare moves. Re-read at every start. This
skill does not mirror the level into state, because it writes nothing.

## Terminal paths

The `(E..)` / `(F..)` line under each header is the ledger citation for
`check_routing.py`, never printed to the client.

**Next moves**
(E20) the compass rendered against state. These are conditional lines in rank
order, not a menu: render only the ones whose gate holds, plus any open-loop
candidate the Sweep found, at most four, renumbered from 1 with `<- start here`
on the rendered #1, and each naming the state fact that makes it the move. When every move the client came for is
gated, the highest unmet gate's unblock phrase is #1, because a compass that
ranks a blocked move has walked them into a wall.
1. *If the marker is on disk and no state file is:* open the front door, which writes the journey file from the marker (E18) and then comes back here. Say: "start shortform"
2. *If `analysis` is unset:* build the field baseline the rest of the engine reads ... nothing downstream is actionable until it exists. Say: "analyze my Instagram against my competitors"
3. *If `analysis.date` is older than 30 days (F6):* keep the field current, a cheap weekly delta, before anything leans on a stale read. Say: "run the weekly pulse"
4. *If `voc.refreshed_at` is over 7 days old AND `declined_offers` holds no `voc_refresh` entry (F7):* refresh the voice guide once, then proceed on it either way. Say: "refresh my voice guide"
5. *If `voc.present` is false:* capture your voice ... pillars and the language you already own, before any draft. Say: "capture my voice"
6. *If `analysis` is set, under 30 days, and `goal` is make-a-reel:* script the top gap, the biggest hole your field read found, in your voice. Say: "script the top gap"
7. *If `goal` is plan-the-week and at least one source exists:* plan the week, 7 to 15 source-tagged ideas deduped against what you have already scripted. Say: "plan my week"
8. *If `pulse.scheduled` is false and `analysis` is set:* have the weekly delta land on your desk on your day. Say: "make the pulse weekly"

**Next moves ... nothing on disk**
(E0) no marker and no state file for this brand. Hardcoded, because there is no
state to rank from. A missing marker never stalls here.
1. Open the front door ... two questions, then I put you on the right road. Say: "start shortform"  <- start here
2. Set up the engine ... the key, the project folder and your brand, about 10 minutes. Say: "set up shortform superengine"

**Next moves ... Vault degraded**
(F3) the `revxl-vault-search` skill does not resolve, so workspace-superengine
is not installed. Say the degrade in one line, "workspace-superengine is
missing, running on the built-in library", then rank as normal: every move below
runs without the Vault, so the journey continues.
1. The next move on your journey, unchanged ... nothing here needs the Vault. Say: "script the top gap"  <- start here
2. Capture your voice ... bundled references only. Say: "capture my voice"
3. Build or refresh the field baseline ... SocialCrawl only. Say: "analyze my Instagram against my competitors"

**Next moves ... deep play needs socialcrawl-superengine**
(F9) the highest-ranked move is a play beyond `socialcrawl-endpoints.md` (field
search outside the roster, creator vetting, share of voice, lead finding) and
the socialcrawl-superengine marker is absent. The refusal is move 1 and it
routes: it never becomes a stall, and this plugin never fakes the play with the
endpoints it has.
1. Get it installed, then run the play there ... ask me to install socialcrawl-superengine from the RevXL marketplace, then say the phrase. Say: "vet this creator" (if installed)  <- start here
2. What runs today on this plugin's table: a keyword search across your own roster. Say: "search the field for <keyword>"
3. The next move that needs none of it. Say: "plan my week"

## Prereq (E0)

**None.** The compass is callable from anywhere at any time. With no state it
renders the hardcoded "nothing on disk" block above; it never refuses and it
never asks the client to go set something up before it will answer.

## Compute, in order

**1. Nothing on disk** (no marker and no state file): render the "nothing on
disk" block and stop.

**2. Position.** Walk the journey graph
(SETUP > VOICE > FIELD > MAKE > READ > PULSE) against state: which stage is done
(its keys written), which is current (started, incomplete), which is next. One
line at `new` ("setup done, voice done, field read 6 days old, you are at MAKE"),
the stage line bare at `pro`.

**3. Sweep before ranking.** Each of these produces a candidate move:

- every entry in `open_loops` (a parked cross-reference, an unscripted plan idea)
- `analysis.date` older than 30 days -> refresh the field (F6)
- `voc.refreshed_at` older than 7 days AND no `voc_refresh:<refreshed_at>` entry in `declined_offers` -> offer a brand-brain refresh (F7). The entry is written by reel-scripter Step 0c or content-plan Step 0 when the client proceeds without refreshing; this skill writes nothing, so it can only read that record, never make it
- `pulse.scheduled` false while `analysis` is set -> offer the schedule. `pulse.scheduled` true -> **never offer it again**, including on a home migrated from a 0.3.x marker
- `mode` is `subject-first` and `subject.present` is false -> subject-matter "(if installed)", else switch to `field-first` and say so (F8)
- gates from the journey map: SETUP, ANALYSIS, VOICE, SUBJECT, DEEP PLAY. A blocked move is never ranked; its unblock route is ranked instead

**4. Rank.** In this order:
1. `goal` ... the client said why they are here, so their goal's door outranks everything else that is legal.
2. Position ... the earliest unmet stage in SETUP > VOICE > FIELD > MAKE > READ > PULSE.
3. Open loops and staleness ... an open loop beats a fresh start; stale field data beats building on top of it.

**5. Guard rails on the render.** #1 must be actionable now, with its prereqs
already met in state; if the goal's door is gated, rank the unblock as #1 and
say why in one plain sentence. A refusal (no marker, socialcrawl-superengine
absent on a deep play, a missing prereq) is itself move 1, with its reason.
Workspace-superengine missing is a one-line degrade, never a blocked move.
2 to 4 moves, phrases verbatim from the roster, never a bare menu.

## Worked renders

Three states, three renders. These are what the client sees, so the ledger ids
are absent from them by design.

Persona 1, new client, nothing on disk:

```
Nothing on disk for this brand yet, so you are at the very start.

**Next moves ... nothing on disk**
1. Open the front door ... two questions, then I put you on the right road. Say: "start shortform"  <- start here
2. Set up the engine ... the key, the project folder and your brand, about 10 minutes. Say: "set up shortform superengine"
```

Persona 2, returning with an analysis (goal `make-a-reel`, `analysis.date` 6
days old, `voc.present` true, `pulse.scheduled` false):

```
Setup and voice are done, your field read is 6 days old, and no pulse is scheduled. You came here to make a reel.

**Next moves**
1. Script the top gap ... the biggest hole your analysis found, written in your voice. Say: "script the top gap"  <- start here
2. Plan the week around it ... 7 to 15 source-tagged ideas so next week is decided. Say: "plan my week"
3. Put the weekly delta on your calendar ... your day, so this read never goes stale on you. Say: "make the pulse weekly"
```

Persona 3, returning with a pulse scheduled (`analysis.date` 34 days old,
`pulse.scheduled` true for Monday, one open loop: a cross-reference parked at
checkpoint 2):

```
Your field read is 34 days old, which is past the 30-day mark I treat as stale. Your pulse already runs Mondays, so I am not offering to schedule it again. One thing is still open: a cross-reference parked at checkpoint 2.

**Next moves**
1. Run the pulse now ... refreshes the 34-day-old field read before anything downstream leans on it. Say: "run the weekly pulse"  <- start here
2. Pick the parked cross-reference back up ... it re-enters at checkpoint 2, nothing already paid for is re-spent. Say: "resume my cross-reference"
3. Script from what you already have ... your last plan still has unscripted ideas. Say: "script idea N from my content plan"
```

Note for `check_routing.py`: the three renders above sit inside fenced code
blocks. The scanner skips fenced blocks, so they are examples, not registry
blocks, and they carry no `(E..)` line.

## Handing off to the compass

Per `routing.md`: a skill that reaches a mid-journey state with more than one
honest next step **invokes this skill** instead of writing its own ranking. The
caller says one line of context ("your plan is written, three ideas still
unscripted"), then invokes `shortform-next` and lets the block come from here.
Two conditions on the caller: it writes its own state keys BEFORE handing off
(this skill writes nothing and would lose them), and it still carries its own
written block for that terminal, as the floor for when the compass does not
resolve.

## Rules

- **Reads everything, writes nothing.** Not `completed_skills`, not `updated_at`, not `teach_level`, not `declined_offers`. The compass can be called a dozen times in one session and must never change the record it is reading. An offer declined here is recorded by the skill that acts on it.
- **Never generic.** Every move names the state fact that makes it the move ("your analysis is 34 days old"), not a category.
- **Gates surface honestly.** "The pulse is blocked until a cross-reference exists" beats hiding the option.
- **Phrases are quoted, never paraphrased.** They come from the journey-map roster; a phrase the roster does not assign is a bug.
- **Never the bare two-word compass phrase** without `in shortform`: that one belongs to another plugin, and skill selection is catalog-wide.
