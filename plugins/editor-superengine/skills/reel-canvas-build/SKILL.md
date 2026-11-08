---
name: editor-superengine:reel-canvas-build
description: Plans, designs and renders what plays on screen over a reel once the spoken cut is signed off. For the plan, the Beat Map (what the screen shows on each line, plus the numbers and key words to show) and the Sketches board for picking one direction. For the design loop, a few looks for the hook and the intro, tweaked until one lands. For the render, a 720p preview to watch, then the final video once the client OKs it, with the finished sound. Use for "build the beat map", "add a transition", "whip", "glitch", "plan what goes on screen", "add a scene", "lower third", "counter", "end card", "title card", "pick a layout", "punch-ins", "zoom in on that word", "layout switches", "follow my face", "slow push", "ken burns", "design the hook", "motion comps", "render it", "make the final video", "export the reel", saved styles, Auto edit on or off, or rendering own clips picked on the Beat Map. Not for cutting the spoken take (reel-first-cuts) and not for the post caption (caption-writer).
---

# reel-canvas-build: the reel's visuals

## Output contract (every run, in this order)

1. One plain line on where the reel's visuals stand, e.g. no Beat Map yet, a Beat Map waiting for the client, a preview waiting for their OK, or the final video made.
2. When a board or a video is involved: open it in the Browser pane, with one line on what to do there.
3. After a Send or a render: a short plain summary of what changed or what was made, and the next step.
4. On any failure you can't fix in two tries: the failure report below.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke this skill again before going on.
- The spoken cut must be signed off first. A new cut needs a new beat map file and a new preview, and the face step again (style.md): beats point at word numbers in the cut, and words are never renumbered.
- Never replace a board the client has edited without asking them first: their edits live in it.
- Re-opening a board is safe: its work is saved on disk after every change.
- The final video is made only after the client OKs the latest preview, recorded only by `compose.py ok` (`${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/build.md`, section 3).
- Run the style picker first if it has not run for this reel (editor-start-here); in Auto edit, follow section 5 of ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md.

## Ground rules

- **The client never types a command.** Claude runs each command in the Bash tool, from the client's workspace folder, as one command.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first.
- `<reel>` is the reel's folder name, and `<reel folder>` is that folder inside the videos folder that `paths.videos` names in `editor/editor.config.json`.
- Plain English for a busy coach. Gloss a term once, e.g. "beat (one stretch of the reel with one look on screen)". Never show the client file names, paths or JSON.
- Layouts, looks and directions are the client's taste: propose them, never impose them. Never invent a number for the screen; a number shown is one the client says in the cut.
- Boards and videos open from the editor's board server: start or restart it with `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md`.
- `deps.json` lists what `editor-superengine:editor-doctor` installs for this skill. The cutout's RVM path uses torch, torchvision and numpy only when transcription setup already installed them; otherwise it uses the backup method.

For B-roll asks, invoke `editor-superengine:reel-broll` first.

## Areas: open only the one the task needs

| The client wants | Read |
|---|---|
| The plan and picks: what's on screen for each line, the layout per beat, numbers and key words marked, or picks on rough sketches and opening directions (the Beat Map and Sketches boards), or a scene (a ready-made graphic such as a title card, counter, list or end card) on a beat | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/beat-map.md` |
| Punch-ins on jump cuts or layout switches, a zoom on a word, the camera following their face | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/style.md`, then `motion.md` in the same folder for the moves |
| Their saved styles: save this reel's choices as a style, list, rename, make one the default, delete or restore one, Auto edit on or off | ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/saved-styles.md |
| A transition at a cut or on a graphic (flash, whip, zoom, glitch, fade, push, wipe or shader), picked on the Beat Map | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/transitions.md` |
| Where the captions sit: kept off the speaker's face and clear of Instagram's buttons, or the plain note when no spot is fully clear | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/placement.md` |
| The design loop: a few looks for the hook or the opening visuals, a visual tweaked, or a check that Instagram's buttons won't cover the text | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/design-loop.md` |
| The render: the 720p preview (a smaller, quicker copy to watch), the client's OK, then the final video at full size with the finished sound; the render draws the picked caption look from reel-captions; for the caption look or the marked words, invoke `editor-superengine:reel-captions` | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/build.md` |
| Graphics behind the speaker: the cutout (the speaker cut out of the background) | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/build.md`, section 7 |
| An optional 3D glass card over the speaker for one short line or number (the glass-card-3d scene), and its check before the render | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/3d.md` |
| Glass-card glow and dust, and the Fine-tune sliders on the Sketches and Tweak boards | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/leads.md` |
| Check the reel before posting / Run QA | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/qa-check.md` |
| After the finished reel: five yes/no questions Claude answers itself; also a CTA reminder, holds on a moment, how each beat comes in and goes out, and style origin and colours | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/eye-test-extras.md` |
| Reusing an unchanged render instead of rendering again | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/render-skip.md` |

Before the 1080p final, run the pre check; after it, run the full check (see `qa-check.md`).

**Not built yet:** use the single list in `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/SKILL.md`, "Not built yet". When the client asks for one of these, say "That part of the editor isn't built yet; it's coming in a later update." One follow-up is allowed: "If the reel has a Beat Map, I can leave a note on that moment for later." Don't build it any other way: a hand-built version skips the Beat Map checks and the preview OK.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.1.0 --skill reel-canvas-build --step '<the plan, the design loop, the render, the cutout or the before-posting check>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
