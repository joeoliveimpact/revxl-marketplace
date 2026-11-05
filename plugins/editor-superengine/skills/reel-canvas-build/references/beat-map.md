# Beat Map and Sketches: plan what's on screen, then let the client pick

## Contents
- What you need first
- 1. Plan the beats
- 2. Build the beat map file
- 3. Open the Beat Map
- 4. Read what the client sent
- 5. Sketches and opening directions
- The saved shapes

```text
Beat Map progress:
- [ ] 1 Beat plan written
- [ ] 2 `✓ Beat map ready`
- [ ] 3 Beat Map open in the Browser pane
- [ ] 4 The client's Send checked and summarised
- [ ] 5 Sketches checked and open, when a direction is still open
```

A `✗` from step 2: fix the plan and run step 2 again. A `✗` from a check in step 4 or 5: fix that file and run the
check again. A new cut: return to step 1. Client changes on the board need no rebuild: act on them in step 4.

The scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/`.

## What you need first

The signed-off cut's word list `<reel folder>/work/edit_map.cut.json` and its frame list
`<reel folder>/work/cuts.json`. Both come from the Cut Board in `editor-superengine:reel-first-cuts`.
If either is missing, the cut isn't signed off yet: say so and go there first.

## 1. Plan the beats

Read the cut's words (`words[i].word`; `i` is the word's number, counted from 0 in list order). Then,
with the Write tool, put the plan in `<reel folder>/work/beat-plan.json`:

`{"beats": [{"w0": 0, "w1": 11, "layout": "full", "value": null, "shows": "...", "why": "..."}], "word_marks": [{"w": 4, "mark": "num"}]}`

- A beat is one stretch with one look on screen, usually one line or one idea. List the beats in
  speaking order; `w0`/`w1` are its first and last word. The beats cover the whole cut: the first
  starts at frame 0 and each runs until the next one starts.
- `layout` is one of `full` (the client full screen), `split`, `stack`, `pip` (picture-in-picture) or
  `overlay`. An `overlay` beat sits on top of the others for just its own words. Propose layouts;
  the client changes any they don't like. Only `full` renders yet; when you propose another layout,
  tell the client it shows full screen for now.
- `value` is a number the beat's scene would show, and only one the client says in those words.
  Otherwise `null`.
- `shows` and `why`: one plain line each, what would be on screen and why it helps that line.
- `word_marks`, one mark per word: `num` a number said aloud, `key` a key word of the line, `emph` a
  word to stress, `cta` the call to action. Zoom punches and captions later read `emph` and `key` as
  suggestions only.
- Ask the client in the chat for anything you need from them (a logo, a photo). The board's
  `needs` box is theirs: what they need from you.

## 2. Build the beat map file

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/make_beat_map.py" --reel-dir "<reel folder>" --plan "<reel folder>/work/beat-plan.json"`

It turns word numbers into frames, checks every beat, and saves the beat map file. `✓ Beat map ready` means
done. A `✗` line names what to fix in the plan; fix it and run it again. If the reel already has a
beat map file, it refuses, because the client's edits are in it: ask the client before adding `--replace`,
which keeps the old one beside the new one (the new beat map file starts with an empty `needs` box, so carry
over anything the client wrote there). If the Beat Map is open, reopen it with `Claude_Browser:preview_start`
straight after a replace: an open board still holds the old beat map file and would save it back over the new one.

## 3. Open the Beat Map

Start the boards (`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md`), then open
`{url}editor/beat-map/?reel=<reel>` with `Claude_Browser:preview_start`. Tell the client: change any layout, type a
number to show, tap words to mark them, add notes, then press Send to Claude. Their work saves as they go.

## 4. Read what the client sent

Send saves `<reel folder>/beat-map-selection.json`. Check it first:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/beat_schema.py" check "<reel folder>/beat-map-selection.json"`

Then tell the client, in plain words, what changed: beats whose layout or number differs from
`proposed`, their notes (`notes`), the marked words, and `needs` (what they need from you). `sent_at` is when they sent it. Act on the notes, or ask about any
you can't act on yet.

## 5. Sketches and opening directions

The Sketches board shows rough sketches per beat and 2 to 4 directions for an open decision (most often
the opening look); the client picks one direction and leaves notes. Make the sketches and direction
frames with the design loop (`${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/design-loop.md`),
save them inside the reel folder, then write `<reel folder>/sketches.state.json` with the Write tool
(shape below) and check it:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/beat_schema.py" check-sketches "<reel folder>/sketches.state.json" --beat-map "<reel folder>/beat-map.state.json"`

Once it passes, if the Sketches board is open, reopen it with `Claude_Browser:preview_start`, so it doesn't save its
old copy over yours.

Open `{url}editor/sketches/?reel=<reel>`. Its Send saves `<reel folder>/sketches-selection.json`:
read `pick` (the chosen direction) and every `note`. When the client presses Lock this look,
`locked_at` is set in `sketches.state.json` at once (it reaches `sketches-selection.json` only on their next Send): that direction is final for the motion work, so build on it and don't offer
new directions unless they unlock it. When there's more to show, add it to the page.

## The saved shapes

`beat_schema.py` holds the checks; these are what the boards save. The board pages themselves live in
`boards/beat-map/` and `boards/sketches/` (the board server copies them into the workspace).

- **Beat map file** (`beat-map.state.json`, and `beat-map-selection.json` on Send): `schema` 1, `reel`,
  `fps`, `words` (`work/edit_map.cut.json`), `beats`, `word_marks`, `proposed` (your picks per beat:
  `layout`, `value`, `shows`, `why`), `notes` (the client's, per beat), `needs`, `sent_at` (`null`, or
  the time of the last Send).
- **Beat:** `{id, start_f, end_f, speech_anchor: {text, w0, w1}, layout, value, scene, broll, transition}`.
  Frames are the cut's frames at `fps`; `end_f` is where the next beat starts. `scene`, `broll` and
  `transition` stay `null` in this version.
- **Sketches** (`sketches.state.json`, and `sketches-selection.json` on Send): `schema` 1, `reel`,
  `rough` (a whole-reel rough video, or `null`), `directions` (`{id, name, why, frames, note}`),
  `pick` (a direction id, or `null`), `sketches` (`{id, beat, title, media, note}`; `beat` is a beat
  id), `note`, `sent_at`, `locked_at` (`null`, or when the client locked the pick). Every file path is relative to the reel folder.
