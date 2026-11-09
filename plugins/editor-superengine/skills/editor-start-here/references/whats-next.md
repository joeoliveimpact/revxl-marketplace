# What's next / act on my Send

Ask which reel only when unclear. Keep paths and skill names out of client-facing lines.
`<reel folder>` is `<paths.videos>/<reel>` from `editor/editor.config.json` (default `videos`);
`<paths.editor>` defaults to `editor`. Use these configured folders throughout.

## Refresh progress

Use the editor Python defined in the router. From the workspace, run the hub's refresh commands verbatim:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/board_sync.py"`

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/hub_rows.py"`

Then read only the reel's row in `<paths.editor>/hub/hub-data.json`: `stage`, `cur`, `done`,
`open_sends`, `qa`, `boards` and `lanes`. Do not Read any Send file to inspect progress: a successful
main-agent Read acknowledges that Send in the Cockpit. The mod exports baseline and acknowledgements to
`<paths.editor>/hub/cockpit-state.json`; the refresh computes `open_sends` without acknowledging them.
If refresh fails or its row is unreadable, say progress is unknown and ask the client which step they reached.
Before editing, handle pending controls requests as described in
`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/hub.md`.

## Next move

First inspect `open_sends`. One unacted Send takes priority over every stage: say "Claude's move: pick up your
<board> Send from <time>." Use its `board` and `mtimeMs` to name the board and time before acting. Ask which
board only when two or more boards have unacted Sends. Finding a Send never authorizes action; wait for the
client's go-ahead, then use Act on my Send below. Never inspect a Send with Read just to list options.

No reel yet, including "Start a new reel": invoke `editor-superengine:reel-first-cuts` for its recording intake.
It creates the configured reel folder, tells the client where to drop their take, and invokes recording-preflight.
The client types no command. `RAW.mp4` at the top or any video in `raw/` makes the stage Cut; several
recordings go through first-cuts' several-recordings path.

Otherwise use `stage` from the refreshed row with this table. Grade is offered before visuals and sound,
while the next move is Ear pass or Beat map; it is optional and never becomes the next move.

| Stage | Skill (prefix every invocation with `editor-superengine:`) |
|---|---|
| Record | recording-preflight |
| Cut | reel-first-cuts |
| Ear pass | reel-first-cuts |
| Grade (optional) | reel-grade |
| Beat map | reel-canvas-build |
| Motion | reel-canvas-build |
| Sound | reel-sound-pass |
| Master | reel-canvas-build |
| Post | caption-writer |

Routing exception: after open Sends, use an editor-Python filesystem check (not Read) for no
`<reel folder>/beat-map-selection.json` and an existing `<reel folder>/sound/final.mp4`.
That reel is finished: the next move is Post; offer visuals and captions as options. This exception does not
change the Cockpit's stage artifacts. Post offers writing the post caption; never publish automatically.
Say one plain line: whose move, what, why; then invoke its skill. Keep the owner's price-and-ask, preview and
approval gates. Example: "Your move: review the cut, because your recording is ready."

## Act on my Send

"Go ahead with my <board> Send" authorizes its owner, including a named Send already acknowledged or older
than the baseline. Do not reject a named go-ahead just because `open_sends` is empty. For an unnamed
Send, use `open_sends`: one selects its owner; two or more boards require a choice; none means ask which
board they meant. For a named Send absent from `open_sends`, get its time with an editor-Python stat.
Before reading or invoking, stat its downstream files too: if newer output exists, explain that it looks
already done and ask whether to redo it. Name the selected board and time first, then Read the whole Send
and invoke its owner. If missing or unreadable, ask instead. The owner's price-and-ask, preview and approval gates still apply.

All paths below are relative to `<reel folder>`. Owners and picker/trial writes come from
`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/scripts/boards.json`.

| Board | Send | Owner | Downstream files |
|---|---|---|---|
| Cut Board | `cut-selection.json` | reel-first-cuts | `work/cuts.json`, `work/edl.json` |
| Tweak Board | `tweak-selection.json` | reel-first-cuts | same as Cut |
| Beat Map | `beat-map-selection.json` | reel-canvas-build | `sketches.state.json` |
| Sketches | `sketches-selection.json` | reel-canvas-build | none |
| Sound Board | `sound-selection.json` | reel-sound-pass | none |
| Grade Board | `grade-selection.json` | reel-grade | none |
| Look Picker | `look-picker-selection.json` | reel-captions | owner's Send flow |
| Cover Picker | `cover-picker-selection.json` | reel-cover | owner's Send flow |
| Trial reels | `trials-selection.json` | reel-trials | owner's Send flow |


For pickers/trials, follow the owning skill's Send flow. Do not invent receipt files. Refresh again after acting.

## Optional steps not done

List missing options briefly alongside the next move; never add them automatically. Check existence with
editor Python. To inspect Beat Map options, use its JSON module in the Bash tool, never the Read tool.

- Grade: `grade-selection.json`; reel-grade. Offer while the next move is Ear pass or Beat map, before visuals and sound.
- Captions: `work/captions.json` (explicit off is a choice); reel-captions.
- Cover: both `cover.json` and `cover.jpg`; reel-cover. Offer while the next move is Master, after the preview and before the final video.
- B-roll: non-null `beats[].broll` in `beat-map-selection.json`; reel-broll. Ingest alone isn't placement.
- Transitions: non-null `beats[].transition` in that same Send; reel-canvas-build.
- Trial reels: `trials/trials.json` is a plan; inspect `trials/trials-report.json` for rendered results; reel-trials.
- 3D: a sent beat's scene manifest has `category: "3d"`; reel-canvas-build. No separate completion file: ask if unclear.
- QA result: use the row's `qa`, including blocks and warnings; missing isn't passed. Owner: reel-canvas-build.

Offer pro-editor-handoff only for configured `nle: resolve` or `nle: mcp`, as
`${CLAUDE_PLUGIN_ROOT}/skills/pro-editor-handoff/SKILL.md` requires; never for `none`, `auto` or unset.
Read the workspace's editor config; only invoke when asked.
