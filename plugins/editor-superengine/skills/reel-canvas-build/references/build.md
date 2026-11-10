# The render: the 720p preview, the client's OK, then the final video

## Contents
- 1. Before rendering
- 2. Make the preview
- 3. Record the OK
- 4. Make the final video
- 5. What the render does
- 6. Transition notes and B-roll at render
- 7. The cutout

```text
Render progress:
- [ ] 1 Beat Map Sent, a caption look chosen (or no captions), and a yes to the preview
- [ ] 2 `✓ Preview ready`, opened in the Browser pane
- [ ] 3 `✓ OK recorded`
- [ ] 4 `✓ Master ready`, opened in the Browser pane
```

A change request: return to step 2. A `BLOCK` line or a missing Beat Map Send: return to step 1.

Renders can take a few minutes on a long reel: give each render's Bash call a 10-minute timeout.

## 1. Before rendering

- The client must have pressed Send on the Beat Map. If they haven't, open it
  (`${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/beat-map.md`, section 3) and ask them to.
- A caption look, or "no captions", must be chosen. If the preview stops with `ask: which caption look? …`,
  invoke `editor-superengine:reel-captions`, then come back to step 2.
- Ask: "Shall I make the 720p preview?" The 720p preview (720 by 1280 pixels, a smaller copy that renders quickly)
  is the cheap look before the final video.
  Nothing renders without a yes. In Auto edit (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md`, section 5), make it without asking.
- The opening hook: when no scene opens the reel, the render writes the first beat's words (70 characters at most)
  on screen from the first frame until that beat ends, 5 seconds at most. If those words run longer (the preview
  refuses them with a `✗` line), or the client named a different hook, add `--hook-text "<the hook>"` to the preview command.

## 2. Make the preview

When a caption look is chosen (not "no captions"), check `<reel folder>/work/anchors.json`.
If it is missing or older than the newest `<reel folder>/work/renders/master-*.mp4`,
run the face step first with `run_in_background`:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/face_crop.py" anchors --reel-dir "<reel folder>"`

`Face anchors saved: 0 frames` means no face was found: go on and tell the client
the captions use the lowest safe spot. If the face step stops, go on with the preview.
Tell the client plainly that captions may sit over their face in places and to check
the preview. Offer the failure report if it stops twice.
See [Keeping captions off the face](placement.md) for why; Follow my face only moves the camera.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" preview --reel-dir "<reel folder>"`

It prints `note:` lines (pass them on in plain words), `info:` lines (for you only), `warning:` lines, then
`✓ Preview ready` and one last JSON line. Read two of its fields:

- `audio`: `"mix"` means the finished sound from the sound pass is in it. `"cut"` means it carries the cut's own
  sound, and the `note:` line just before says why: the sound pass hasn't run, the sound was mixed on an older cut,
  or the last mix didn't pass its check. Tell the client that plainly and offer the sound pass
  (`editor-superengine:reel-sound-pass`); the final video picks up the finished sound once it's mixed on this cut.
- `out`: the preview's place inside the reel folder.

Open `{url}videos/<reel>/<out>` (`{url}` is the address the board server printed) with `Claude_Browser:preview_start`,
each space written as `%20`. Tell the client: "Watch it through, then tell me it's OK, or what to change." Never hand back stills taken off the finished file: the video
itself is what they review.

## 3. Record the OK

On a clear yes in the chat ("that's OK", "make the final"):

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" ok --reel-dir "<reel folder>"`

When the hub's Master review (the hub page where the client watches the preview and approves it) sends an Approve:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" ok --reel-dir "<reel folder>" --from-review`

`✓ OK recorded` means the final video can be made. With `--from-review`, a refusal means the review wasn't sent, didn't
approve, or approved an older preview: tell the client it has to approve the latest one. `master` checks the OK against
the latest preview, so a hand-written OK would skip the client's review.
A change request is not an OK: make the change, then a new preview.

After `ok`, say any printed style lines word for word: a learned change, the Auto edit offer, or Auto edit switched off. For the offer, a yes runs `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/style_learn.py" auto <style> on`; a no runs the same script's `decline <style>`. Quote style names with spaces. Pass `--workspace <workspace folder>` to `auto` for this workspace's unlock setting. If that style isn't the default, add: "It starts by itself once <style> is your default. Make it your default?" On yes, run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" set-default <style>`.

## 4. Make the final video

The master runs the QA pre check itself and stops on a block; see [QA check](qa-check.md).

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" master --reel-dir "<reel folder>"`

If the preview had `--hook-text`, add the same one here. `✓ Master ready` means it made `<reel folder>/renders/<reel> Master - MM.DD.YY.mp4`
at full size (1080 wide, 1920 tall), the file the Editor Cockpit (the editor's own panel in Claude, apart from the hub) shows as the final video. Open it in the Browser pane the same way as the preview, then give the
summary and the next step.

When it refuses, nothing is made. In plain words, with the one next step:

| The line says | What it means | Next step |
|---|---|---|
| The QA check blocks the final | a QA pre check found a block | fix what it names, run the QA check again, then make the final |
| it needs your OK first | the client hasn't OK'd the latest preview | show them the latest preview and ask |
| the preview changed after the last OK | a newer preview was made since the OK | ask for an OK of the new one |
| a line about the music's licence | the music's licence record is missing or doesn't match the track | fix it in the sound pass (`editor-superengine:reel-sound-pass`), then make the final video again |
| `ask: which caption look` | no caption look or "no captions" choice yet | invoke `editor-superengine:reel-captions`, then make the preview again |
| `BLOCK` lines | two things clash on screen, e.g. two full-screen scenes at once, or an effect running across a cut | move the beat's edges on the Beat Map, Send, then a new preview |
| a layout check error (`✗` ending in a code in brackets) | a fault in the editor's own page, not the client's | run it once more; if it stays, the failure report, with the step 'the render' |

The preview stops on `BLOCK` and layout check lines the same way. Any other `✗` line names what to fix; exit 2
means a missing input, e.g. no Beat Map Send or no cut yet: go to that step.

## 5. What the render does

The saved brand colour and font restyle every scene, with the font applied only when its licensed file ships with the editor; a beat's own choices win.
The hf-hook-title scene opens complete and fits above the head; if it cannot fit, a plain hook shows the same title, while missing face anchors keep the default position with a note.

- The cut's picture plays untouched underneath, and section 1's hook text opens the reel.
- A beat that carries a scene gets it over its frames: a first-beat scene opens complete, and back-to-back
  full-screen scenes get a dark panel between them. The client picks scenes with Add a scene on the Beat Map.
- The sound is copied, never re-encoded: the finished sound when it was made on this cut, otherwise the cut's own.
- If the client asks about quality: the picture is compressed twice in all since the camera, once for the cut
  and once here.
- It deletes its scratch folder after every render. If an old one can't be deleted, it stops before rendering:
  close whatever has a file from that folder open, then run it again.

## 6. Transition notes and B-roll at render

A `note:` about a transition (such as the shader shown as a fade on this computer) is passed on in plain words; see `references/transitions.md`.
Own-clip B-roll comes from reel-broll and the Beat Map Send. Before rendering, the footage ledger checks
the clip's bytes and source intervals; AI footage cannot accompany a number. Missing footage licences warn
on previews and refuse the Master, even without music. B-roll is muted at layer 200, under scenes and captions.

## 7. The cutout

Cuts the speaker out of the background, for later looks that put graphics behind them. Run it only when a look
the client picked puts graphics behind the speaker (none of the built looks does yet), with `run_in_background`
(it can take many minutes). `master-<tag>.mp4` is the cut's own full-size render from reel-first-cuts
(not the final video), in `<reel folder>/work/renders/`;
`<tag>` is the cut's speed with the dot dropped, e.g. `master-100x.mp4` at normal speed, `master-115x.mp4` at 1.15x:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/cutout.py" "<reel folder>/work/renders/master-<tag>.mp4" "<reel folder>/work/matte/cutout.mov"`

It uses RVM (a model made for cutting out people) when the editor has it ready, otherwise the backup method. A
`cutout failed:` line says why; the last line is a JSON summary.
