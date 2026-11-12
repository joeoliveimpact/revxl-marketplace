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

A plan beat may also carry `check` (see `shows` below); leave it out unless the client has a decision to make on that beat.

- A beat is one stretch with one look on screen, usually one line or one idea. List the beats in
  speaking order; `w0`/`w1` are its first and last word. The beats cover the whole cut: the first
  starts at frame 0 and each runs until the next one starts.
- Every `layout` keeps the client's face on screen. `full`: the face fills the screen; `split`: graphic on the
  top half, the face on the bottom half; `stack`: the face on top, graphic below;
  `pip` (picture-in-picture): graphic fills the screen, the face in a small box at the top right;
  `overlay`: the face fills the screen with a card over the lower part, on top of the other beats for just
  its own words. Propose layouts; the client changes any they don't like. A layout other than full shows only when the editing style is
  **Layout switches** (style.md). With Punch-ins every beat stays full screen, whatever its layout.
- `value` is a number the beat's scene would show, and only one the client says in those words.
  Otherwise `null`.
- `shows` and `why`: one plain line each, what would be on screen and why it helps that line.
  Describe only what the chosen layout can draw; never write "graphic only" or "no face". When the
  idea needs the face gone, pick the closest layout and add `check` to that plan beat: one plain line
  saying what you wanted and what this layout does instead. The board flags it for the client with that line.
  For example: `"check": "I wanted the graphic alone here. Stack keeps your face on top; say if you want it that way."`
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
which keeps the old one beside the new one, keeps picks on beats whose words did not change and your
"Anything you need from Claude?" text, and lists any it could not keep. If the Beat Map is open, reload the hub at that board (the same address)
straight after a replace: an open board still holds the old beat map file and would save it back over the new one.

## 3. Open the Beat Map

Start the boards (`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md`), then open the Beat Map inside the hub:
`{url}editor/hub/?reel=<reel>&board=beat-map&view=full` with `Claude_Browser:preview_start`.
The timeline shows every beat with a sketch of the face and the graphic area. The focused beat sits directly
below it, with Editing style further down, before "Anything you need from Claude?". Open a beat, pick its layout,
then press **Looks good, next**. Flagged beats show a dot and a reason. The client clears a review flag by
pressing **Looks good** or changing the layout; a missing layout must be fixed. A bad number or B-roll start in More stays flagged until it is fixed; Looks good does not clear it.
**More** holds the number, scene, B-roll, transition and note controls; tap spoken words to mark them.
Changes save as you go. Press **Send to Claude** when ready; looked-at progress stays in this browser only.
Tell the client: check each beat's layout on the timeline, pick the one that looks right, tap words to mark them, open More for the number, scene, B-roll, transition or a note, then press Send to Claude. Their work saves as they go.

Open a beat, then **More**, then **Add a scene**, or use **Add a scene** on its Sketches card, to choose a thumbnail. Suggestions come first,
filled from that beat's cut words in `scenes/suggest.json`; `scenes/why.json` explains why grey choices don't fit.
When you ask to rebuild the scene choices after changing "Number shown" in **More**, run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/scene_fill.py" catalog --reel-dir "<reel folder>"`.
The 3D card's choices depend on your face position: refresh with the same command after the face step; shots too tight for either place grey the card, and a clear place is suggested to keep the card box off your eyes and mouth.
Edit the slots within their character limits and the scene values within their bounds. A counter's value
comes from the beat's number: change that number in **More** on the open beat. Remove scene clears the choice.
When the beat has no scene, the Beat Map offers a scene picked in Sketches in one click.
The render reads the Beat Map's Send (`beat-map-selection.json`), so use the Sketches pick there and Send.

The Editing style panel offers Steps (ratchet) and Camera move choices for punch-ins; custom saved settings stay as set until that control changes.

### Editing style

Choose **Punch-ins on jump cuts** for alternating closer views, or **Layout switches** for the beat layouts (the panel now sits below the open beat).
Punch-ins also offers the punch level, a settle at the start, following the face and punches on words marked stress.
**Ask me before the preview** leaves this reel's choice open; the style picked for this reel at its start, if any, still applies, otherwise Claude asks.
Changes save as you go; press **Send to Claude** to use them in the preview. See [style.md](style.md) for the rules.

## 4. Read what the client sent

Send saves `<reel folder>/beat-map-selection.json`. Check it first:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/beat_schema.py" check "<reel folder>/beat-map-selection.json"`

Then tell the client, in plain words, what changed: beats whose layout or number differs from
`proposed`, their notes (`notes`), the marked words, and `needs` (what they need from you). `sent_at` is when they sent it. Act on the notes, or ask about any
you can't act on yet.
A beat that still carries `check` and whose layout equals the proposed layout was left as planned.

## 5. Sketches and opening directions

The Sketches board shows rough sketches per beat and 2 to 4 directions for an open decision (most often
the opening look); the client picks one direction and leaves notes. Make the sketches and direction
frames with the design loop (`${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/design-loop.md`),
save them inside the reel folder, then write `<reel folder>/sketches.state.json` with the Write tool
(shape below) and check it:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/beat_schema.py" check-sketches "<reel folder>/sketches.state.json" --beat-map "<reel folder>/beat-map.state.json"`

Once it passes, if the Sketches board is open, reload the hub at that board (the same address) straight after writing sketches, so it doesn't save its
old copy over yours.

Open Sketches inside the hub: `{url}editor/hub/?reel=<reel>&board=sketches&view=full`. Its Send saves `<reel folder>/sketches-selection.json`:
read `pick` (the chosen direction) and every `note`. When the client presses Lock this look,
`locked_at` is set in `sketches.state.json` at once (it reaches `sketches-selection.json` only on their next Send): that direction is final for the motion work, so build on it and don't offer
new directions unless they unlock it. When there's more to show, add it to the page.

## The saved shapes

`beat_schema.py` holds the checks; these are what the boards save. The board pages themselves live in
`boards/beat-map/` and `boards/sketches/` (the board server copies them into the workspace).

- **Beat map file** (`beat-map.state.json`, and `beat-map-selection.json` on Send): `schema` 1, `reel`,
  `fps`, `words` (`work/edit_map.cut.json`), `beats`, `word_marks`, `proposed` (your picks per beat:
  `layout`, `value`, `shows`, `why`, and optional `check`), `notes` (the client's, per beat), `needs`, `sent_at` (`null`, or
  the time of the last Send).
- **Beat:** `{id, start_f, end_f, speech_anchor: {text, w0, w1}, layout, value, scene, broll, transition}`.
  Frames are the cut's frames at `fps`; `end_f` is where the next beat starts. `scene` is `null` or
  `{id, slots: {<name>: "<text>"}, params?: {<name>: <number|string|bool>}}`; every slot is given,
  with `""` to leave it empty. Scene-specific limits, transcript numbers and duration are checked before render.
  `broll` is `null` or `{src, in, out, fit, ledger_id}` from reel-broll: source frames at the cut's fps,
  `out - in == end_f - start_f`, fit `cover` or `blur-fill`. Pick it in the Beat Map tab and Send once.
  `transition` is `null` (a hard cut) or an object as in transitions.md.
- **Sketches** (`sketches.state.json`, and `sketches-selection.json` on Send): `schema` 1, `reel`,
  `rough` (a whole-reel rough video, or `null`), `directions` (`{id, name, why, frames, note}`),
  `pick` (a direction id, or `null`), `sketches` (`{id, beat, title, media, note}`; `beat` is a beat
  id), `note`, `sent_at`, `locked_at` (`null`, or when the client locked the pick), and optional
  `scenes: {<beat id>: <scene object>}` with the same scene shape. Every file path is relative to the reel folder.
