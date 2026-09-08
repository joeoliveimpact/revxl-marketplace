---
name: shortform-start
description: The front door for shortform-superengine. Works out whether this is a first run, a 0.3.x marker-only home that needs migrating, or a returning client; captures the goal; then hands off to the compass. Trigger phrases include "start shortform", "open shortform", "shortform start", "I'm lost in shortform".
---

# shortform-start ... the front door

One job: work out where this client already is, capture what they came for, and
route. It produces no analysis, no script and no plan of its own, and it never
refuses a client.

## Load (in order)

1. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/journey-map.md` ... the roster, the edge registry, the gates. Every phrase this skill quotes comes from that roster, verbatim
2. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/routing.md` ... the Next-moves block grammar
3. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/state-schema.md` ... key ownership and the staleness constants
4. `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/teach-mode.md` ... then read the dial, below
5. `~/.claude/shortform-superengine/.superengine` (the install marker) and `~/.claude/shortform-superengine/state/<brand>.json` (the journey record)

## Teach mode

```
level = read("~/.claude/revxl/teach-level").trim()          if it exists
   else map(read("~/.claude/revxl/teach-mode").trim())      if THAT exists
        where "beginner" -> "new", "off" -> "pro"
   else "new"
```

`new` (the default when neither file exists): plain English first, then the term
with a one-line gloss on first use, plus a "what this means for you" line where
the consequence is not obvious. `learning`: plain English with the term inline.
`pro`: ordinary professional voice, no scaffolding. Re-read this at every start,
never trust a value cached earlier in the session, and mirror it into
`state.teach_level` (the file stays the authority).

## Terminal paths

Every ending this skill can reach is written below. The `(E..)` / `(F..)` line
under each header is the ledger citation for `check_routing.py`: it is authoring
metadata, **never printed to the client**.

**Next moves ... first run**
(E17) no marker and no state on disk. Name the goal the client just picked in
move 1, so the door is obviously theirs and not a generic menu.
1. Set up the engine ... about 10 minutes: the SocialCrawl key, the project folder and your brand. Every goal goes through this door first. Say: "set up shortform superengine"  <- start here
2. Capture your voice while you are here ... no keys and no credits, and every later draft sounds like you instead of like a robot. Say: "capture my voice"
3. See the road at any point ... where you are, what is next, one line. Say: "what's next in shortform"
4. Just ask ... plain-English answers about how this engine works, no setup needed.

**Next moves ... migrated**
(E18) a marker was found with no journey file, and the journey file has just
been written from it. Say the migration in ONE line first ("I found your 0.3.x
setup and carried it over, including your pulse schedule"), then invoke
`shortform-next`. This block is the floor if the compass does not resolve.
1. Pick up where you actually are ... your position and the ranked moves from the state I just wrote. Say: "what's next in shortform"  <- start here
2. *If `analysis` is set, `analysis.date` is under 90 days, and the 30-day band does not hold:* script the biggest gap your existing analysis already found. Say: "script the top gap"
3. *If `analysis` is empty:* build the field baseline the rest of the engine reads. Say: "analyze my Instagram against my competitors"

**Next moves ... returning**
(E19) state present, marker either way. One line of position first (stage, last
completed skill, open loops, staleness), then invoke `shortform-next`. This
block is the floor if the compass does not resolve.
1. The ranked moves for exactly where you are. Say: "what's next in shortform"  <- start here
2. *If the marker is absent:* finish setup; the compass ranks it first. Say: "set up shortform superengine"
3. *If `analysis.date` and `pulse.last_run` are both over 30 days old (F6), a null `pulse.last_run` counting as over 30:* refresh the field first, because everything downstream reads it. The 30-day band reads the newer of the two dates; the full re-run at 90 days reads `analysis.date` alone, whatever the pulse did. Say: "run the weekly pulse"
4. *If an open loop holds a parked cross-reference (F1):* pick it back up at the checkpoint it stopped at, nothing is re-spent. Say: "resume my cross-reference"
5. Plan the week off whatever sources you already have ... 7 to 15 ideas, nothing paid. Say: "plan my week"

**Next moves ... Vault degraded**
(F3) the `revxl-vault-search` skill does not resolve, so workspace-superengine
is not installed. Say one line, "workspace-superengine is missing, running on
the built-in library", print `Vault: 0 searches, 0 reads | skipped:
workspace-superengine not installed`, and carry on. This never blocks the
journey.
1. Keep going ... the ranked moves, all of which run on the bundled references. Say: "what's next in shortform"  <- start here
2. Capture your voice ... nothing in it touches the Vault. Say: "capture my voice"
3. Build the field baseline ... SocialCrawl only, no Vault involved. Say: "analyze my Instagram against my competitors"

**Next moves ... deep play needs socialcrawl-superengine**
(F9) the client asked for a play beyond `socialcrawl-endpoints.md`: field search
outside their own roster, creator vetting, share of voice, or lead finding.
Those live in socialcrawl-superengine. This plugin will not fake them with the
endpoints it has, because a confident wrong answer about the field costs more
than the install does.
1. Get it installed, then run the play there ... ask me to install socialcrawl-superengine from the RevXL marketplace, then say the phrase. Say: "vet this creator" (if installed)  <- start here
2. What runs today on this plugin's table: a keyword search across your own roster. Say: "search the field for <keyword>"
3. Back to the journey. Say: "what's next in shortform"

## Prereq (E0)

**None.** This skill IS the door, so it has nothing to refuse for. Nothing on
disk is not an error, it is the first-run path: render the E17 block above.
Every real gate (a key, an analysis, a voice guide, a subject) is checked in the
skill that needs it, and E0 is written there.

## Steps

**1. Read the disk. No writes in this step.**

- the marker `~/.claude/shortform-superengine/.superengine`
- the brand: marker `active_brand`, then marker `brand` (legacy alias, same value), then scan `~/.claude/shortform-superengine/state/*.json` (exactly one file, take its `brand`; several, ask which), then ask once. Slug convention is brand-brain's: lowercase, alphanumeric only, no separators ("Maria G Fit" -> `mariagfit`)
- `~/.claude/shortform-superengine/state/<brand>.json`
- derive, never read from the file: `voc.present` and `voc.refreshed_at` from `~/.claude/revxl/<brand>/voc/` (exists, newest mtime inside); `subject.*` from `~/.claude/revxl/<brand>/subject/` the same way
- probe 1, socialcrawl-superengine: `~/.claude/socialcrawl-superengine/.superengine` exists, OR a directory matching `~/.claude/plugins/cache/*/socialcrawl-superengine/` exists
- probe 2, workspace-superengine: the `revxl-vault-search` skill resolves in the available skill list. Absent is the F3 path, never a stall

**2. Branch on what step 1 found.**

| On disk | Path |
|---|---|
| no marker, no state | FIRST RUN, step 3 |
| marker, no state | MIGRATE, step 4 |
| state present (marker either way) | RETURNING, step 5. A missing marker is named in the same position line and onboarding stays on the block |

**3. FIRST RUN.** Two questions, then the block. Ask the goal with these five,
in plain words, hardcoded here (they are the enum in `state.goal`, not trigger
phrases, so do not dress them as `Say:` lines):

- **make a reel** (`make-a-reel`) ... you want a script you can film
- **plan the week** (`plan-the-week`) ... you want the week's topics decided
- **read my results** (`read-my-results`) ... you want to know what is working
- **read the field** (`read-the-field`) ... you want to know what your competitors are doing
- **set up** (`set-up`) ... you just want the engine installed and working

Ask the brand name once (it names the state file). Then write
`state/<brand>.json` from the schema template with `goal` set and step 1's two
probes recorded in `setup.socialcrawl_superengine_installed` and
`setup.ws_superengine_version`, seeded at file creation only, and render E17.
Do NOT write a marker: the marker is onboarding's, and a marker written here
would claim a setup that has not happened.

Where each goal goes once setup is done, so move 1 can name it:

| Goal | The door, given what is on disk |
|---|---|
| make-a-reel | no marker: onboarding. Marker but no `analysis` in `field-first`: competitor-cross-reference (F2). Otherwise reel-scripter |
| plan-the-week | no marker: onboarding. No source at all (`analysis`, `voc.present`, `subject.present` all empty): brand-brain, or competitor-cross-reference if they would rather start from the field. Otherwise content-plan |
| read-my-results | no marker: onboarding, then own-content-analysis "(if installed)". Until 0.5.0 ships it, say so in one line and offer competitor-pulse, which reads the field rather than their own account |
| read-the-field | no marker: onboarding, then no `analysis`: competitor-cross-reference. `analysis` set: competitor-pulse |
| set-up | onboarding |

**4. MIGRATE (marker present, no state file).** Write `state/<brand>.json` from
the schema template, filled from the marker:

- `brand` = the resolved slug. If the marker's `active_brand` was absent or null, write it into the marker now with that same value. That is the only marker write this skill makes
- `setup.complete` = true (a marker means onboarding ran), `setup.keys_present.socialcrawl` from `connections.socialcrawl`
- `setup.socialcrawl_superengine_installed` and `setup.ws_superengine_version` from step 1's two probes, seeded at file creation only
- the marker's `competitor_pulse` block INTO `state.pulse`: `scheduled` -> `scheduled`, `last_run` -> `last_run`, `cadence` -> `day` lowercased, only when it names a weekday (otherwise null). From here the marker copy is ignored: never re-read, never deleted. **A migrated home is never re-offered the pulse schedule it already accepted**
- `project_path` from `competitor_pulse.project` when it is set, so the client is not asked for a folder they already gave
- `analysis` when an `analysis-data.json` is found (look at `competitor_pulse.project` first, then scan for a project directory holding one): `date` = that file's modified time as YYYY-MM-DD, `n_competitors` = the competitor count inside it, `themes_set` false, `resume` null. Seeded at file creation only; `analysis.*` is competitor-cross-reference's from then on. Without the seed the compass reads `analysis` as null on a machine that plainly has one and sends the client back to build it again

Say it in ONE line, render E18, then invoke `shortform-next`.

**5. RETURNING (state present).** One line of position, then invoke
`shortform-next`. The line carries: the stage from the journey map, the last
entry in `completed_skills`, how many `open_loops` are open, and any staleness
that holds ... the 30-day band on the newer of `analysis.date` and
`pulse.last_run` (F6), the full re-run at 90 days on `analysis.date` alone,
`voc.refreshed_at` older than 7 days (F7), `pulse.scheduled` false. Render E19
as the floor.

**6. At any point.** A deep-play request with probe 1 false is F9. Probe 2 false
is F3, stated once and then carried, never repeated per move.

## What this skill writes

| Written | When |
|---|---|
| `goal` | first run, and any later run where the client plainly says the goal changed (say so in one line) |
| `active_brand` in the marker | migration only, and only when it was absent or null |
| the state file itself | first run and migration (creation), from the schema template |
| `updated_at`, a `completed_skills` append, `open_loops`, `declined_offers`, `teach_level` | every run, per the every-skill rule |

Never written here: `analysis.*`, `voc.*`, `subject.*`, `scripts[]`,
`angles_unpicked[]`, `plan.*`, `own_read.*`, and `pulse.*` or `setup.*` after
the migration created them. `mode` stays at the template's `field-first` unless
the client explicitly asks for subject-first, which is a 0.5.0 path.

## Rules

- **Never invent a phrase.** Every `Say:` line is copied from the journey-map roster; a phrase that is not in the roster is a bug, not a shortcut.
- **The `(E..)` and `(F..)` citations are not client-facing.** They exist for the routing check.
- **Refusal-free door.** Whatever the client asks for, route it. Gates live in the target skill.
- **One brand at a time.** A brand named in the client's message that does not match the resolved brand STOPS the run and offers the switch. Never report another brand's numbers.
- **Two lines the client always gets:** where they are, and what to say next. A block, never a bare menu.
