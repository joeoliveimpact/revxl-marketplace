# No-board path (Stages 2, 3 and 5 in chat)

Use this when no board is available (the board server won't start, or there is no Browser pane), or when
the client asks to do the cut in chat. Every other stage runs as SKILL.md says. `<editor python>` and the
path rule (`work/` is `videos/<reel>/work/`) are in SKILL.md's Ground rules.

## Contents
- Stage 2 in chat: the line-selection table
- Stage 3 by hand: the EDL
- Stage 5 in chat: the speed table

## Stage 2 in chat: the line-selection table

Score every trim candidate and present a ranked table. **Never auto-apply.** Then stop for the
client's pick.

Score by **direction**, not information content: a line carrying zero information but pointing
*forward* opens a loop the viewer stays for; a line restating something already said closes one.
**Only backward-facing lines are free cuts.** In the reference build, two of four proposed
"restatement" cuts were the reel's strongest rehooks.

With several recordings, pick one take for the whole cut: render.py takes one raw file.

## Stage 3 by hand: the EDL

Build the EDL from the client's pick as `work/edl.json`, one `{src_in, src_out}` per cut, in reel order:

- Pads, a neighbour clamp and a merge rule. Mid-sentence trims clamp against the next **word**, not the
  next sentence.
- Assert zero source overlaps.

Then run gaps.py on it yourself (there is no printed command on this path):

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/gaps.py" work/ --edl work/edl.json --words work/edit_map.json --speed <speed>`

and the boundary audit after it, exactly as SKILL.md's Stage 3 says. Anything above the measured speech
floor is **re-derived**, not shipped.

## Stage 5 in chat: the speed table

Before gaps.py runs, present the runtime **and the measured duplicate-frame %** per candidate speed
(probe.json's table), then stop for the client's pick. Pass the pick to
gaps.py as `--speed` and to render.py as the same `--speed`.
