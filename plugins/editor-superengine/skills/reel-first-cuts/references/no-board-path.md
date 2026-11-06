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

`line_score.py` ranks the table, so that rule holds every time:

1. With the Write tool, put every trim candidate in `work/line-labels.json` with its direction (`forward`,
   `backward` or `neutral`) and why:
   `{"lines": [{"id": "L04", "text": "<the line>", "src_in": 12.40, "src_out": 15.10, "direction": "backward", "why": "restates the opening claim"}]}`
2. Run:
   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/line_score.py" videos/<reel>`
   It prints the ranked table and writes it to `work/line-table.md`: free cuts (backward) first, then
   "your call" (neutral), then keeps (forward). A forward line is never a free cut. It writes no EDL and
   no selection. Exit 2 means it refused and wrote nothing: a line has no id, no direction or no why, an
   unknown direction, or a repeated id. Fix the lines it names and run it again.
3. Show the client the table, then stop for their pick.

With several recordings, the client can pick each line's take. Log the raws and use takes.py for a mixed cut,
as `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/several-recordings.md` says.

## Stage 3 by hand: the EDL

Build the EDL from the client's pick as `work/edl.json`, one `{src_in, src_out, take}` per cut, in reel order (take defaults to 1):

- Pads, a neighbour clamp and a merge rule. Mid-sentence trims clamp against the next **word**, not the
  next sentence.
- Assert zero source overlaps within each recording.

Then run gaps.py on it yourself (there is no printed command on this path):

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/gaps.py" work/ --edl work/edl.json --words work/edit_map.json --speed <speed>`

and the boundary audit after it, exactly as SKILL.md's Stage 3 says. Anything above the measured speech
floor is **re-derived**, not shipped.

## Stage 5 in chat: the speed table

Before gaps.py runs, present the runtime **and the measured duplicate-frame %** per candidate speed
(probe.json's table), then stop for the client's pick. Pass the pick to
gaps.py as `--speed` and to render.py as the same `--speed`.
