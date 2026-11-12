---
name: editor-superengine:recording-preflight
description: Checks the client's camera and sound before they record a reel, using a 10-second test clip. Use on "I'm about to record", "check my setup before I film", "does my mic sound ok", "test my camera", "why does my video look choppy", or "my audio sounds distorted". NOT for editing a finished recording (that's reel-first-cuts) or the editor's own tools (that's editor-doctor).
---

# recording-preflight: a 10-second check before the real take

## Output contract (every run, in this order)

1. The set-up suggestions below, short, as options.
2. "Record about 10 seconds of you talking and drop the file here."
3. One plain line per check: ✓ good, ⚠ worth fixing, ✗ must fix.
4. A last line: "Good to record", or the one or two fixes that matter most.

Speak to the client the way `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-user-hears.md` says: no file names, paths, script names or raw output.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke it again before going on.
- Re-running is safe. The check only reads the clip; it never changes or keeps it.
- Check the test clip, not the real take. If the client drops a long recording, offer the check, but say it's meant for a short test.
- **Already have the take?** (They drop a finished recording, or intake finds one.) Skip the set-up suggestions and the 10-second ask. Start with "You can still edit this take.", then for each ⚠ / ✗ say what it means for editing this take, and give any set-up fix as "next time". Never a fix that only works by recording again, unless they ask to re-record. The last line is "Good to edit", or the one thing to listen for.

## Ground rules

- **The client never types a command.** Claude runs the check with the Bash tool.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. If it doesn't exist, run `editor-superengine:editor-doctor` first.

## 1. Set-up suggestions (options, never rules)

- **Light in front of you**, not behind. A window behind you turns you into a silhouette. The check can't see light, so look at the test clip yourself.
- **Mic close:** a clip-on mic, or the phone about an arm's length away. A quiet room.
- **Framing:** head and shoulders, some space above your head, and the lower part of the frame kept clear. Captions and the app's buttons sit there (the safe zone).
- **Phone settings:** 1080p or 4K, 30 fps (frames per second), exposure and focus locked, Do Not Disturb on, lens wiped.
- **HDR is fine.** The editor converts it.

## 2. Run the check

`<editor python> "${CLAUDE_PLUGIN_ROOT}/skills/recording-preflight/scripts/preflight_check.py" "<clip>"`

It checks, in plain words:
- picture size and whether the phone was upright (it reads the phone's rotation tag)
- the real frame rate, and whether it's VFR (variable frame rate: the phone changes speed mid-clip). VFR is a note, not a problem: the editor evens it out.
- freezes and repeated frames: the recorder dropped frames, so close other apps
- HDR: a note, the editor converts it
- sound: none recorded is ✗; too loud is likely clipping (distortion that can't be fixed later); too quiet means move the mic closer
- length: a test too short to judge

Exit 0 means nothing is ✗. Exit 1 means a ✗ line, or a line saying the clip isn't there. `The editor's setup isn't finished yet.` means no video tools were found: run `editor-superengine:editor-doctor`, then the check again.

## 3. Tell the client

Pass on each ✓ / ⚠ / ✗ line in your own plain words, then the last line from the output contract. Pick the one or two fixes that matter most; don't list every ⚠. A small-picture ⚠ on a clip sent from a messaging app may just be the app shrinking it: ask for the original file.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.2 --skill recording-preflight --step 'check' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
