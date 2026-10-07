# Step 3 ... per-section option generation

Moved out of `SKILL.md` at 0.4.0 for the byte ceiling. Step 3
runs **generate ... screen ... score ... gate ... pick** per section, in this order: Hook,
Secondary hook(s), Body beats, Proof, CTA, Text-overlay storyboard, Caption hook. The
skeleton is frozen before any of it: voice may reword a beat, never add, cut, reorder or
re-purpose one.

The named Vault trigger point for the hook (pull #2) stays in `SKILL.md` Step 3 and is
governed by `../../_shared/references/vault-api.md`.

## The lock, the substance, and the interview

The skeleton is frozen. Voice work happens **inside** it: voice may reword a beat, never add /
cut / reorder / re-purpose one, and never soften a beat's move (a myth-bust stays a myth-bust).
Substance comes from the analysis + the client's own input; `voc/` artifacts set **tone and
vocabulary** by default. When a phrase from the coach or their audience is gold (strong
enough to work as it is), keep it word for word. **Mandatory when the angle is the
client's own topic:** BEFORE generating body/proof options, interview them per locked teaching
beat ... one question per beat their brain-dump hasn't already covered (their story, their step,
their number). Options are generated only from what they actually said; if a beat has no answer,
flag it and ask ... never paper over with invented teaching.

## The five passes

1. **Generate** options in the client's voice, each built on the brief's proven moves:
   - **Hook (the hook pass): 3 to 5 openings, all from the `hook` skill; none written here.**
     Each opening comes back with its spoken line, its on-screen text and its visual. The
     on-screen text is its own line, not the spoken line copied (the hook skill's Written
     hook). A gold phrase from the coach or their audience goes in word for word.
     **Goldmine data is on by default; never ask whether to use it.** When
     `<project>/reel-build/goldmine-run.json` shows `reads.passed` true, always pass the
     Pattern Read and the proven hooks below (read that file before this call if you have not); the hook skill adapts them through its copy's
     "Adapting a proven hook" section, never copied. The one off switch: the client said
     plainly to use their own hook or to ignore the data. Then no Goldmine data goes to any
     skill for this reel. A hook the client gave goes in as `candidates`, beside the proven
     ones. Call `hook` once with the Skill tool (its stamp counts only from that call plus a Read of its method file):

     ```
     Skill: shortform-superengine:hook
     args:  step: 3-hook
            topic: <the locked angle>
            body: <the approved skeleton>
            voice: <the voice anchor confirmed at Checkpoint 0>
            candidates: <the client's own hook, word for word, when they gave one; leave this line out when there is none>
            pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json,
                          only when its reads.passed is true and the client has not said to ignore the data or
                          use their own hook; else leave this line out>
            proven_hooks: <same condition (reads.passed true, and the client has not said to ignore the data or use
                          their own hook): the file named by reads.proven_hooks; when that key is missing, the top 3
                          breakouts by mult from reads.packet, each with its Pattern Read formula (name and
                          template), its opening line and @handle, mult, URL; else leave this line out>
            redo: <what cut the first set, or which killer fired and why>
     ```

     With no Goldmine data, or after the off switch, leave `pattern_read` and `proven_hooks` out. Vault pull #2
     hits, when there are any, ride in the `topic:` line as data, never as rules. The stamp is
     recorded automatically when you call the skill with the Skill tool and then Read its method file; never write or edit a `from:` line yourself. You
     write nothing else to `<project>/reel-build/provenance.md` either.

     The proven hooks go through its "Adapting a proven hook" section, so each comes back
     rebuilt for this reel's subject or refused as a bad fit. Its openings run the passes
     below like any other option. To regenerate, make one more `hook` call that carries what
     cut the first set; never write an opening here.
   - **Secondary hook and re-hooks (the secondary-hook pass): 3 options per slot, all from
     `rehooks`; none written here.** The slots (where each sits, its type and its visual) came
     from `rehooks` at Step 2 and are locked in the skeleton. Call `rehooks` in its Step-3
     mode, with the Skill tool (its stamp counts only from that call plus a Read of its method file): the secondary hook FIRST, right after the hook pick; the mid-reel re-hooks in a
     second call, after the body and proof picks, so each one sits on value the viewer just got.

     ```
     Skill: shortform-superengine:rehooks
     args:  step: 3-lines
            slots: <the slots to write now, each with where it sits, its type and its visual:
                   the secondary hook slot first, right after the hook pick; the mid-reel
                   re-hook slots in a later call, after the body and proof picks>
            picks: <the lines picked so far, in beat order>
            voice: <the voice anchor confirmed at Checkpoint 0>
            pattern_read: <the reel-build/ file named by reads.patternread in <project>/reel-build/goldmine-run.json, only when its reads.passed is true and the client has not said to ignore the data or use their own hook; else leave this line out>
            redo: <what cut the first set, or which killer fired and why>
     ```

     Each slot comes back with 3 options: a spoken line, its on-screen text and its visual
     change. The stamp is recorded automatically when you call the skill with the Skill tool and then Read its method file
     (Step 4b's gate fails without it); never write or edit a `from:` line yourself. A short reel with
     no slot still makes the call. To regenerate, make one more `rehooks` call with
     `step: 3-lines`, the same slot and what cut the first options.
   - **Body beats + Proof (2 to 3 options per beat)** ... fill the skeleton one idea per beat and
     keep each beat's loop tag true (Step 4b checks it). The Other side beat takes `polarize`'s
     line from Step 2 as it came; it is not rewritten here. After the body and proof picks, make
     the mid-reel re-hook call (the secondary-hook pass above).
   - **CTA (2 to 3 options)** ... matching scaffold from `./cta-scaffolds.md`, mapped to
     the client's actual goal/offer (from `business-config`). ONE ask only.
   - **Text-overlay storyboard (2 whole-storyboard options)** ... the on-screen text and visual
     plan for the entire reel: a table over the frozen skeleton, one row per 3 to 5 seconds,
     not one per beat: every beat covered in order (none skipped, none added), and a beat longer
     than 5 s split into as many rows as it needs. Four columns: beat, seconds (that row's span),
     overlay line, visual cue. The frame-1 overlay is the picked hook's on-screen text, not
     the spoken hook. At each `rehooks` slot (the secondary hook, each re-hook), the overlay
     line is the on-screen text `rehooks` gave with the picked line. Overlay lines are written
     here only at beats no skill gave on-screen text for: each is **≤6 words**, reinforcing the beat's move,
     never transcribing the spoken line. Each row has exactly one visual cue: anything that
     redirects focus (a cut, a zoom, a camera-angle change, a scene shift, an animation, new
     on-screen text). Example: a 12 s beat is three rows (0-4, 4-8, 8-12), each with its own cue.
     At each re-hook, the cue is the visual `rehooks` gave for that slot. Must pass the
     **silent-scroll glance test**: the overlays alone, read in order with the sound off,
     still tell the story arc.
   - **Caption hook (2 to 3 options)** ... a second angle on the idea, not a copy of the spoken hook.
2. **Screen** every option ... the brief's **§8 Avoid list first** (this niche's losers), then the
   universal tables (`../../_shared/references/say-this-not-that.md`: the losing openers and the
   approach losers). A hit disqualifies the option outright; **brand-voice phrasing is not exempt.**
   When a §8 layer reads "no confident avoid" (or §8 is empty), that layer screens nothing: screen
   on the universal tables alone, say so once at the gate, and never invent niche losers to fill it.
3. **Score each surviving option 1 to 10:** hooks on single-subject clarity / single question
   planted / scroll-stop power; secondary hooks on information-gap / narrative fit / value
   balance; body + proof on the Story Locks rubric (`./story-locks.md`); CTA on
   clarity / alignment / friction; storyboards on silent-scroll story / beat reinforcement /
   ≤6-word discipline; caption hook on cut-off curiosity / keyword / complementary
   angle. Every score is set against the 9 / 7 / 6-or-below anchors in `./story-locks.md`
   "How this scores".
4. **Gate:** present only options scoring **≥7**, with scores and a withheld count ("8 generated,
   3 cleared"). Fewer than 2 clear → regenerate once, then show the best available flagged
   "below bar". The bar defaults to 7; the user can move it for the run. For the hook,
   regenerate means one more `hook` call carrying what cut the first set; for the secondary
   hook and re-hooks, one more `rehooks` call (`step: 3-lines`). Never an option written here
   for those.
   Under the cleared options, list every withheld one on its own line with what cut it: its
   score if it was scored below the bar, or the screen that disqualified it (§8 Avoid, a losing
   opener, a say-this-not-that loser) if it never reached scoring.
5. **The user picks** ... by score plus *"which sounds most like something you'd actually say."*
   No auto-alternatives: a redo comes only on request, per option; for a hook, secondary hook
   or re-hook option it is one more `hook` or `rehooks` call. The pick locks; the next
   section's options are generated **in continuity with everything picked so far**.

## After every section is picked

The three-hook alignment check and the 6 Swaps pass stay in `SKILL.md` Step 3; the swaps
themselves are the table in `./story-locks.md`. On a line another skill wrote, a swap is a
flag for the user, never a rewrite (the rule for every pass after the picks: `SKILL.md` Step 3).