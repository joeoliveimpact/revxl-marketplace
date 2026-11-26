# The render: voice-only preview, sound, preview OK, final video

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
- [ ] 1 Beat Map Sent, a caption look chosen (or no captions)
- [ ] 2 Build motion and Motion review done, or explicit no graphics
- [ ] 3 Preview and sound path in section 1 complete
- [ ] 4 Eligible preview opened for the user
- [ ] 5 `✓ OK recorded` on that preview
- [ ] 6 `✓ Master ready`, opened in the Browser pane
```

A change request: return to the affected stage, then remake the preview. A `BLOCK` line or a missing Beat Map Send: fix the named prerequisite.

Renders can take a few minutes on a long reel: give each render's Bash call a 10-minute timeout.
Motion review and the preview run one at a time; follow Build motion's queue and resource instructions.
Do not launch a second job while the first is queued or running.

## 1. Before rendering

- The user must have pressed Send on the Beat Map. If they haven't, open it
  (`${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/beat-map.md`, section 3) and ask them to.
- A caption look, or "no captions", must be chosen. If the preview stops with `ask: which caption look? …`,
  invoke `editor-superengine:reel-captions`, then come back to step 2.
- Once every planned scene is ticked Leave it, the Motion review Send is the yes to make the voice-only
  preview. The explicit no-graphics choice is also that yes; do not ask again. Previews are 720 by 1280 pixels.
- The opening hook: when no scene opens the reel, the render writes the first beat's words (70 characters at most)
  on screen from the first frame until that beat ends, 5 seconds at most. If those words run longer (the preview
  refuses them with a `✗` line), or the user named a different hook, add `--hook-text "<the hook>"` to the preview command.

When the Motion stage is not done, or the editing style is still missing, follow
[Build motion: Before building](motion-build.md#before-building); it also covers no graphics.

### Preview and OK order (the single owner of this rule)

- Make the voice-only preview first, newer than both `motion-review-selection.json` and the cut master.
  This is the prerequisite for the Sound Board. Do not open Master review or ask for its OK. Say:
  "Your preview is ready with voice only. Next is the Sound Board, where you pick music and effects."
  Invoke `editor-superengine:reel-sound-pass`; Auto edit continues into that skill too.
- After mixing, that skill hands back to `editor-superengine:reel-canvas-build` to make the **preview with
  sound**. Require `audio: "mix"` and a preview newer than `sound/final.mp4`. Only then open Master review,
  offer its Approve button and say: "Watch it through, then tell me it's OK, or what to change."
  Record that OK with section 3, then make the final video with section 4. An early Approve on the first
  preview does not qualify; finish this flow and get approval of the preview with sound.
- In a fresh session at Master, stat the newest finished `renders/* Preview 720p - *.mp4` (exclude
  `.partial.mp4`) and `sound/final.mp4`. A preview newer than the mix is the preview with sound; if the preview
  is not newer, or there is none, make it before inviting approval. With no mix, an existing preview is
  voice-only: follow the sound handoff above unless the user explicitly chose to skip sound.
- If the user skips sound, the voice-only preview is the one they OK: open it in Master review, request
  its OK, then use sections 3-4. No sound pass or second preview is required on that path.

## 2. Make the preview

When a caption look is chosen (not "no captions"), check `<reel folder>/work/anchors.json`.
If it is missing or older than the newest `<reel folder>/work/renders/master-*.mp4`,
run the face step first with `run_in_background`:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/face_crop.py" anchors --reel-dir "<reel folder>"`

`Face anchors saved: 0 frames` means no face was found: go on and tell the user
the captions use the lowest safe spot. If the face step stops, go on with the preview.
Tell the user plainly that captions may sit over their face in places and to check
the preview. Offer the failure report if it stops twice.
See [Keeping captions off the face](placement.md) for why; Follow my face only moves the camera.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" preview --reel-dir "<reel folder>"`

It prints `note:` lines (pass them on in plain words), `info:` lines (for you only), `warning:` lines, then
runs the QA pre check on the saved positions. If blocked, the preview file is available to watch, but it stops
with one line per kind of block before `✓ Preview ready` or any OK invitation. Show those lines, make
the named change, then make the preview again. Otherwise it prints `✓ Preview ready` and one last JSON line. Read two of its fields:

- `audio`: `"cut"` is expected on the voice-only preview, before sound; it is not a fault. After sound,
  `"mix"` means the finished mix is included. If it still says `"cut"`, explain the preceding note in plain words
  (missing, stale or failed mix) and return to `editor-superengine:reel-sound-pass`. Then resume section 1.
- `out`: the preview's place inside the reel folder.

Refresh after the render as [hub.md](../../editor-doctor/references/hub.md) says, then follow section 1's
handoff or approval step. When it calls for Master review (`board=review`), open it using
[board-server.md step 3](../../editor-doctor/references/board-server.md). It plays the latest preview and
the master once there is one, with sound controls. Show the video itself for review, never stills.

## 3. Record the OK

For a preview eligible under section 1, on a clear yes in chat ("that's OK", "make the final"):

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" ok --reel-dir "<reel folder>"`

When the hub's Master review (the hub page where the user watches the preview and approves it) sends an Approve:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" ok --reel-dir "<reel folder>" --from-review`

`✓ OK recorded` means the final video can be made. `ok` reruns the same QA pre check and refuses on any block;
show the grouped lines, make the named change, then make the preview again. With `--from-review`, a review refusal means the review wasn't sent, didn't
approve, or approved an older preview: explain that you need to approve the latest one. `master` checks the OK against
the latest preview, so a hand-written OK would skip the user's review.
A change request is not an OK: make the change, then a new preview.
A re-mix after the OK needs a new preview and OK; Claude remakes the preview for you to OK.

After `ok`, say any printed style lines word for word: a learned change, the Auto edit offer, or Auto edit switched off. For the offer, a yes runs `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/style_learn.py" auto <style> on`; a no runs the same script's `decline <style>`. Quote style names with spaces. Pass `--workspace <workspace folder>` to `auto` for this workspace's unlock setting. If that style isn't the default, add: "It starts by itself once <style> is your default. Make it your default?" On yes, run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" set-default <style>`.

## 4. Make the final video

Require the OK defined in section 1. The master runs the QA pre check itself and stops on a block; see [QA check](qa-check.md).

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/compose.py" master --reel-dir "<reel folder>"`

If the preview had `--hook-text`, add the same one here. `✓ Master ready` means it made `<reel folder>/renders/<reel> Master - MM.DD.YY.mp4`
at full size (1080 wide, 1920 tall), the file the Editor Cockpit (the editor's own panel in Claude, apart from the hub) shows as the final video. Refresh after the render as [hub.md](../../editor-doctor/references/hub.md) says, then open Master review
(`board=review`) using [board-server.md step 3](../../editor-doctor/references/board-server.md). The Master review tab plays the newest preview and the master with its own sound controls. Then give the summary and the next step.

When it refuses, nothing is made. In plain words, with the one next step:

| The line says | What it means | Next step |
|---|---|---|
| The QA check blocks the final | a QA pre check found blocks, grouped by kind | show every grouped line, make the named change, then make the preview again and request its OK |
| it needs your OK first | the user hasn't OK'd the latest preview | show them the latest preview and ask |
| the preview changed after the last OK | a newer preview was made since the OK | ask for an OK of the new one |
| a line about the music's licence | the music's licence record is missing or doesn't match the track | fix it in the sound pass (`editor-superengine:reel-sound-pass`), then make the final video again |
| `ask: which caption look` | no caption look or "no captions" choice yet | invoke `editor-superengine:reel-captions`, then make the preview again |
| `BLOCK` lines | two things clash on screen, e.g. two full-screen scenes at once, or an effect running across a cut | move the beat's edges on the Beat Map, Send, then a new preview |
| a layout check error (`✗` ending in a code in brackets) | a fault in the editor's own page, not the user's | run it once more; if it stays, the failure report, with the step 'the render' |
| a line about the face card's cut-out | a Face card + head pop beat has no cut-out of this cut | make it with section 7, then the preview again |

The preview stops on `BLOCK` and layout check lines the same way. Any other `✗` line names what to fix; exit 2
means a missing input, e.g. no Beat Map Send or no cut yet: go to that step.

## 5. What the render does

The saved brand colour and font restyle every scene, with the font applied only when its licensed file ships with the editor; a beat's own choices win.
The hf-hook-title scene opens complete and sits clear of the eyes and mouth (above them, where it may share the hair, or else below the chin, or smaller); if it cannot fit, a plain hook shows the same title, while missing face anchors keep the default position with a note.

- The cut's picture plays untouched underneath, and section 1's hook text opens the reel.
- A beat that carries a scene gets it over its frames: a first-beat scene opens complete, and back-to-back
  full-screen scenes get a dark panel between them. The user picks scenes with Add a scene on the Beat Map.
- The sound is copied, never re-encoded: the finished sound when it was made on this cut, otherwise the cut's own.
- If the user asks about quality: the picture is compressed twice in all since the camera, once for the cut
  and once here.
- It deletes its scratch folder after every render. If an old one can't be deleted, it stops before rendering:
  close whatever has a file from that folder open, then run it again.

## 6. Transition notes and B-roll at render

A `note:` about a transition (such as the shader shown as a fade on this computer) is passed on in plain words; see `references/transitions.md`.
Own-clip B-roll comes from reel-broll and the Beat Map Send. Before rendering, the footage ledger checks
the clip's bytes and source intervals; AI footage cannot accompany a number. Missing footage licences warn
on previews and refuse the Master, even without music. B-roll is muted at layer 200, under scenes and captions.

## 7. The cutout

Cuts the speaker out of the background. The **Face card + head pop** layout (`facecard` on the Beat Map) needs
it: its head pop is this cut-out. Run it when a beat uses that layout and the preview (or the QA check) says the
cut-out is missing or older than the cut, before the preview, with `run_in_background` (it can take many
minutes; RVM on a graphics card is fastest). Remake it after any change to the cut. `master-<tag>.mp4` is the cut's own full-size render from reel-first-cuts
(not the final video), in `<reel folder>/work/renders/`;
`<tag>` is the cut's speed with the dot dropped, e.g. `master-100x.mp4` at normal speed, `master-115x.mp4` at 1.15x:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/cutout.py" "<reel folder>/work/renders/master-<tag>.mp4" "<reel folder>/work/matte/cutout.mov"`

It uses RVM (a model made for cutting out people) when the editor has it ready, otherwise the backup method. A
`cutout failed:` line says why; the last line is a JSON summary.
