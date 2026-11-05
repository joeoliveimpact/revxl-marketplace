---
name: editor-superengine:reel-canvas-build
description: Plans and designs what plays on screen over a reel once the spoken cut is signed off. Builds the Beat Map (what the screen shows on each line - full screen, split, stack, picture-in-picture or an overlay - plus the numbers and key words to show), opens the Sketches board for picking one direction for the opening visuals, and runs the design loop for hook and intro comps. Use for "build the beat map", "plan what goes on screen", "pick a layout", "show me a few looks for the opening visuals", "design the hook", "comp the intro", "will the Instagram buttons cover this", or to plan where B-roll and graphics will go (placing them isn't built yet). Not for cutting the spoken take (reel-first-cuts) and not for the post caption (caption-writer).
---

# reel-canvas-build: the reel's visuals

## Output contract (every run, in this order)

1. One plain line on where the reel's visuals stand: no beat map yet, a beat map waiting for the client's review, or what they sent.
2. When a board is involved: the board open in the Browser pane, and one line on what to do there, e.g. "Change any layout, tap words to mark them, then press Send to Claude."
3. After a Send: a short plain summary of what the client changed (layouts, numbers, marked words, notes, the picked direction) and the next step.
4. On any failure you can't fix in two tries: what went wrong in plain words, then the failure report offer below.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on.
- The spoken cut must be signed off first. The Beat Map points at the cut's words by their number in the cut's word list, so a new cut needs a new beat map. Words are never renumbered.
- Never replace a beat map or a sketches page the client has edited without asking them first. The beat map builder refuses, and when told to replace it keeps the old one beside it.
- Re-opening a board is always safe: its work is saved on disk after every change.

## Ground rules

- **The client never types a command.** Claude runs each command in the Bash tool, from the client's workspace folder, as one command.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first.
- Plain English for a busy coach. Gloss a term once, e.g. "beat (one stretch of the reel with one look on screen)". Never show the client file names, paths or JSON.
- Layouts, looks and directions are the client's taste: propose them, never impose them. Never invent a number for the screen; a number shown is one the client says in the cut.
- Boards run on the editor's board server: start or restart it with `${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md`.

## Areas: open only the one the task needs

| The client wants | Read |
|---|---|
| A plan of what's on screen for each line, the layout per beat, numbers and key words marked, or picks on rough sketches and opening directions (the Beat Map and Sketches boards) | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/beat-map.md` |
| A few looks for the hook or the opening visuals, a visual tweaked, or a check that Instagram's buttons won't cover the text (the design loop) | `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/design-loop.md` |

**Not built yet in this version:** the final render, zoom styles, placing graphics around the face, scenes (lower thirds, counters, lists), transitions, B-roll and the before-posting check. When the client asks for one of these, say plainly that this part of the editor is coming. If the reel has a Beat Map, the client can leave a note on that beat for later. Don't build it any other way.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.1.0 --skill reel-canvas-build --step '<beat map, sketches or design loop>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
