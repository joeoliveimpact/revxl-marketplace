# Build motion: from the locked look to real scenes in the reel

After the user locks the look on Sketches, build its scenes before the Sound Board. Read
[the motion bar](motion-bar.md) and [the scene contract and example](motion-scene.md).
Speak as [What the user hears](../../editor-start-here/references/what-the-user-hears.md) says.

## Contents
- No graphics
- Before building
- Scene areas and the face
- Order of work
- After the Motion review Send
- After a recut or Beat Map change

## No graphics

If no custom motion scenes are planned, ask once: "No motion graphics on this one?"
Built-in title cards alone do not require custom motion scenes. Only on a yes, and only if no review
has been sent, record it with:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py" none --reel-dir "<reel folder>"`

Never infer this choice from empty scenes. If the user changes their mind after a review Send and requests
removing the custom scenes, archive those scene folders, `motion/review/` and the old Motion Send outside
`motion/`, clear their `beat.scene` entries in both Beat Map files, then run `none`. Keep the archived notes.
If the user later asks for graphics, `build` clears the obsolete
`motion-review-selection.json` whose `none` is true and whose `sections` is empty once there are scenes to review.

## Before building

- Require the Beat Map Send, `work/edit_map.cut.json`, `work/word_map.json`, and a cut master in
  `work/renders/master-*.mp4`. Missing input: return to the cut or Beat Map first.
- Resolve the editing style **before Build motion**, including the no-graphics path. Recorded means `edit_style` in the Beat Map Send,
  or the saved choice for this reel. If absent, ask once: "Should key words zoom in, or should the layout switch?"
  Record the answer with the following command, choosing one of `punch-in` and `layout-switch` for `<choice>`:

  `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py" style --reel-dir "<reel folder>" --style <choice>`

  It updates the Send and `beat-map.state.json` if it exists, preserving other choices. Reload an open
  Beat Map so a later Send retains it. `apply` also copies a saved choice when absent;
  if it prints `STYLE_ASK`, resolve it by this same rule. See [style.md](style.md) for the choices.

## Scene areas and the face

Default to stack, split or pip. Build at the area's native size; never crop or squeeze another area's scene.

- Match the scene area to the beat: `stack` below the face, `split` above it, or `full` for `pip` with
  the small face box on top. A pip beat refuses a stack or split scene. When a reel world scene's area
  matches, the face slot is held under either editing style; Motion review draws it as compose will.
- A beat whose layout is `full` needs area `full` and the user's **Graphics take the whole screen
  (hides you)** tick (`cover_face: true`). On stack, split and pip beats the tick also allows area `full`.
  A pip world still holds its face box; other full-area choices follow the editing style.
  Never tick it yourself or suggest hiding the face unprompted. If a build needs it, ask once whether the
  user wants pip or that tick, then let the user choose on the Beat Map and Send.
- `overlay` beats take no world scene, even with the tick. Choose another layout.

## Order of work

1. Say how many scenes are planned. Build one distinct scene per beat sketch that shows a graphic;
   plain talking head and B-roll need none. The opening look belongs to the first beat's id from the Send.
2. Plan each world map and camera path, then write its scene folder as the [scene contract](motion-scene.md)
   describes. Use `<reel folder>/motion/reel-b001-<name>/` for beat `b_001` (remove the underscore; lowercase letters, digits and
   hyphens only, 64 characters at most). `source` must name exactly one literal beat id, e.g.
   `"Beat b_001, Quiet Desk look"`. It supplies the card's built text; the title comes from the id, not a `title` key.
   Get timed word ids from `work/word_map.json` (`words[].id`, `out_start`), then run using that beat's id:

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py" times --reel-dir "<reel folder>" --beat b_001 --words w_0013,w_0016`

   Copy each returned beat-local second into `params.t1.default`, `params.t2.default`, etc. in `scene.json`,
   with `type: "number"` and the matching `word` id. Keep any Beat Map scene-param overrides equal to these
   times. Wrong or stale timed params stop the entire build before rendering.
3. Place the scenes on the Beat Map:

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py" place --reel-dir "<reel folder>"`

   It fills `beat.scene` in both `beat-map.state.json` and `beat-map-selection.json` and refreshes
   `scenes/catalog.json`. Slots get the beat's first spoken words that fit; params default to `{}`.
   It keeps existing slots and params only for the same scene id, and replaces any other scene on that
   beat, including a catalog pick. For other text, follow [the scene contract](motion-scene.md#starting-example).
   Check `Placed N scenes on the Beat Map.` matches the plan, then reload an open Beat Map.
   A placement refusal writes neither map: fix its named scene or beat and run again.
   Internal `place`, `style` and saved-style writes retain the user Send's timestamp, so they do not
   reopen it in the Cockpit. Resume Build motion; a later user Send still opens normally.
4. Start this once with `run_in_background`; it renders pending scenes sequentially, runs hold and seek
   checks, makes the start frames and scene videos over the real picture, and refreshes Motion review:

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py" build --reel-dir "<reel folder>"`

   - Optionally check before rendering with
     `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/scripts/scene_check.py" check "<reel folder>/motion"`.
     Fix every FAIL; build runs this check too.
   - Relay the estimate in plain words (about four minutes for a four-second scene). On a first build,
     its scene count must match the plan. `No motion scenes are on the Beat Map yet. Run place first.`
     is a refusal: stop and place them. An `About 0 seconds for 0 scenes` estimate is normal when all are locked.
   - Locked scenes are excluded from the estimate. Check `motion/review/review.json` cards cover every
     planned scene, with `checks: "passed"`. A partial failure writes only passing cards and exits 1;
     fix all failed scenes and run again before inviting review.
5. Open Motion review (`board=motion-review`, Full view) using
   [board-server.md step 3](../../editor-doctor/references/board-server.md).
   Say: "Watch each scene play. Tick Leave it if you're happy with it, or write what to change, then press Send."

Motion review and the preview share one heavy-job lock: run one at a time. If queued, say another render
is finishing and wait; do not launch a duplicate. It can wait up to two hours. If it stops for less than 3 GB
available RAM or 10 GB free disk, explain what to free, then retry once the resource is available.

## After the Motion review Send

- Apply it to lock scenes marked Leave it and print notes on the others:

  `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py" apply --reel-dir "<reel folder>"`

- Leave it plus a note locks the scene and ignores the note: ask which choice the user intends,
  then delete its `locked` file if they want the change.
  Neither tick nor note: ask what they want for that scene. Do not treat missing failed cards as approved.
- Rebuild only scenes the user wants changed, against their notes and the bar. An unchanged `scene.html`
  with a matching `locked` file reuses its card. Before an authorized revision or look unlock, delete only
  that scene's `<reel folder>/motion/<scene id>/locked` file; there is no unlock command. The lock hashes
  only `scene.html`, so also remove it when changing metadata, assets or timings. Repeat steps 4-5 (step 3
  too if placement changed) and ask
  for a new Send. Never rewrite a locked scene without the user's request.
- Once every planned scene passes and is ticked Leave it, follow [build.md](build.md) for the sound pass
  and the preview OK. Auto edit also stops for this review; it never writes Leave it for the user.

## After a recut or Beat Map change

Rerun `times` for affected beats and update word ids and defaults in `scene.json`. Clear `beat.scene` on
those beats in both Beat Map files, then run `place`; the empty params use the new scene defaults rather
than stale `t*` overrides. Restore any authorized slot text without restoring old timing overrides.
Delete the affected scenes' `locked` files, then repeat steps 4-5 and request a new Send.
A `--replace` Beat Map can keep scene picks even when their times move.

Reel scenes stay in the reel's `motion/`, never the plugin's `scenes/`. Build from the user's sketches and
the bar; never copy another creator's files, prompts or graphics.
