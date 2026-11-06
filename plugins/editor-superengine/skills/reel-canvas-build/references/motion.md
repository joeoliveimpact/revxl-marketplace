# Moves within punch-ins

These options belong to **Punch-ins on jump cuts**. Choose them in the Beat Map's
Editing style panel and press **Send to Claude** before making the preview.
They do not apply to Layout switches. Claude handles the settings below;
the client only needs the controls and plain descriptions.

## Settle in at the start

The opening begins 6% closer and eases back over 0.6 seconds. It ends sooner when
the first cut or an early word punch needs that space. If a word punch starts on
the first frame, the settle is skipped with a note.
This is `moves.opening_settle`, off unless chosen.

## Word punches

Mark a word as **stress** by tapping it on the Beat Map, then choose:

| Control | What it does |
|---|---|
| Off | No word punches |
| Strong | A larger, quicker emphasis: 1.22 times the segment's zoom at its peak |
| Gentle | A smaller, slower emphasis: 1.06 times the segment's zoom at its peak |
| Smooth | Ease into the closer view and ease back |
| Snap | Switch straight to the closer view, hold it, then switch back |

Claude's settings use `moves.word_punches`: Off is `null`; Strong and Gentle are
presets `dramatic` and `subtle`; Smooth and Snap are shapes `eased` and `hard-cut`.
The `picks` are the word numbers currently marked `emph`, read when saving or
sending, so changing the word marks changes where the punches land.
With punches on and no stress marks, the board says:
"Mark the words to stress first; the punches land on them." The picks stay empty.

A punch starts 0.05 seconds before its word, rounded to a whole output frame and
never before that segment starts. Its end also falls on a whole frame, by the
segment's last frame. Near a cut, the hold shrinks first, then the return; a punch
that cannot fit is skipped with a note. At most one punch lands in each sentence.

Total zoom is the segment's punch level **multiplied by** the word's peak.
For example, 1.12 with Strong reaches 1.3664. The value is never capped: above the
softness ceiling in `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/tuning.json`
means a warning, not a block. Preview it to judge how the face looks.
Moves on the same property that touch or overlap can merge into one smooth gesture.

## Follow my face

`moves.follow_cam` follows the measured head positions within each segment and
starts again at every cut. It needs head samples from the face step after the cut
master is made.
It is off unless chosen. The effect gate refuses any move across a cut.

When the client turns it on, after the cut master exists and before the preview, run with
`run_in_background`: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/face_crop.py" anchors --reel-dir "<reel folder>"`.
`✓ Face anchors: 0 segments` means no face was found: the camera stays put; tell the client.
Exit 2: the cut master is missing; make the cut first. After any new cut, run it again before
the preview; if Follow my face is off, delete `<reel folder>/work/anchors.json` instead.

## Steps (ratchet)

The view steps closer two to four times, then snaps back to the shot's own size
(normal size on an unpunched shot). Suits a word that builds emphasis. Choose
**Steps (ratchet)** for three steps on stress words; Claude can set two or four
with `moves.ratchet: {picks: [word numbers], levels: 2|3|4}`. Smooth/Snap hides.
Each hard step adds 8% of the shot's size, with 0.2 seconds between steps and
0.3 seconds at the top. It starts with the word-punch onset rule above. Near a
cut, fewer levels are used down to two; if two cannot fit, it is skipped with a note.
A ratchet counts as one sentence's punch, however many steps it has. With word
punches too, the first event in that sentence keeps the punch; later ones get a note.

## Slow push in

The view moves steadily closer across one shot. Suits a line that needs growing
attention. **Camera move → Slow push in** sets `moves.push: {segments: "all", to: 1.06}`.
Claude can name segment numbers instead, counted from 0, or set a multiplier from
1 to 2. The scale moves from the shot's own size to that size times `to`, from
its first frame to its last frame, with `ease: "none"` (a constant speed).

## Slow drift (Ken Burns)

The view eases closer while its zoom centre drifts sideways. Suits a quieter line.
**Slow drift (Ken Burns)** sets `moves.ken_burns: {segments: "all", to: 1.08}`.
Claude can name shots or change `to` from 1 to 2. Scale and centre move together
from the shot's first to last frame with `sine.inOut`; the centre starts 4% left
of its usual position and ends 4% right, kept inside the frame. It stays inside
one shot: the effect gate blocks a move planted across a cut.

## Keep an edge in place

**Keep the top of the frame** sets `moves.reframe: {segments: "all", edge: "top"}`.
Suits a closer view where the top should stay put. Claude can name shots and use
`bottom`, `left` or `right` instead. The centre is set hard on the first frame so
that edge holds during zooms; without any zoom, a note says it has nothing to hold.

All four are off unless the client asks. Pick one moving camera per shot: push
and Ken Burns cannot share a shot. Ken Burns and reframe also conflict because
both place the zoom centre; push can use a reframe. On push or Ken Burns shots,
word punches and ratchets are skipped with notes, as is the opening settle on
shot 0. Follow my face is skipped with a note on Ken Burns and reframe shots.
The panel shows saved settings outside these quick choices as **Custom (set by
Claude)** and keeps them until that control changes.
