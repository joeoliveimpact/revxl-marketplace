# Choose the reel's editing style

Use this after the spoken cut is signed off. Keep the choice in the client's words;
Claude handles the saved settings. Never show the client paths, filenames or JSON.

## Two choices

- **Punch-ins on jump cuts:** alternate between the normal view and a closer view
  at each cut, starting at normal size. Suits a reel where the speaker carries the
  explanation and a closer view adds emphasis without changing the arrangement.
- **Layout switches:** use each beat's chosen arrangement. Suits a reel with steps,
  comparisons or supporting graphics that need space beside the speaker.

At a cut, the change happens on that exact frame. A layout change between cuts
takes 0.6 seconds when there is room and must finish before the next cut.
The punch-in moves are explained in `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/motion.md`.
Ratchet steps, a slow push, Ken Burns and an edge reframe are optional punch-in moves, all off unless chosen.

## Choose it with the client

The Beat Map's **Editing style** panel is the easy way to choose for this reel.
Its changes save as the client works; **Send to Claude** makes the choice available
to the preview. The reel's Send uses `edit_style` with `style: "punch-in"` or
`style: "layout-switch"`. Layout switches needs only that one key.

If the Send has no `edit_style`, compose uses the `edit_style` of the style picked for this reel at its start, if any.
If neither has one, compose stops before rendering; its last line is:

`ask: which editing style? punch-ins on jump cuts, or layout switches`

Ask the client: "Do you want punch-ins on the jump cuts, or layout switches?"
Then put their pick in the reel's Beat Map Send (`beat-map-selection.json`),
under `edit_style`. The board control is easiest; Claude may write the Send for
the client, preserving their other choices and checking it before previewing.
**Ask me before the preview** removes the reel's choice; the style picked for this reel at its start, if any, still applies.

**Saved styles** (save, default, rename and other saved choices): ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/saved-styles.md.

## The arrangements

Full screen keeps the speaker across the picture. The four alternatives are:

- **Split:** a card fills the top half, with the speaker below it.
- **Stack:** the speaker sits above a larger card area.
- **Picture-in-picture:** the speaker appears in a small rounded box near the top
  right, above a card that fills the picture.
- **Overlay:** the speaker stays full screen with a panel over the lower area.

The Beat Map chooses the arrangement per beat. Layout switches does not invent
graphics or pick a different layout for the client.

## Face position and limits

`face_crop.py crop` measures the face from samples of the source take before the
cut is conformed to portrait. The first-cut renderer uses the resulting crop;
this is a face-centred crop, not a moving camera. With no usable face measurement,
the renderer keeps the centred crop.

After the cut master exists, `face_crop.py anchors` measures head positions within
each cut segment. The first head sample sets that segment's zoom centre; without
samples, the planner uses its default near the eyes. **Follow my face** moves
between those samples inside the segment; without them it stays put. Follow the face
step in [motion.md, Follow my face](motion.md#follow-my-face), including rerunning it
after a new cut, or deleting the samples when Follow my face is off.
Neither selecting a style nor previewing automatically makes face measurements.

The measured softness ceiling is currently **1.15**, from
`${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/tuning.json`.
Zoom above it produces a warning; it never blocks the preview or caps the zoom.
Word punches allow one word per sentence; later picks in that sentence are skipped
with a note. Every move passes the effect gate and must stay inside one segment:
a move that crosses a cut stops the plan before rendering.
