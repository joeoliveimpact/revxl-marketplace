---
name: editor-superengine:editor-start-here
description: The router for editor-superengine. Use when someone says "edit my reel", "where do I start with editing", "cut this talking head", "first cut", "tighten the gaps", "design the hook", "motion comps", "check my setup before I record", "write my post caption", "tear down this reel", "copy this creator's editing style", "make mine look like this reel", "sound pass", "add sound effects", "mix the sound", "clean up my voice", "is the editor ready", "check the editor's setup or tools", or "editor superengine", or any time it is not clear which editing skill an ask belongs to. Names the one skill the ask goes to, says why, and hands it over. Not a skill that edits, renders or installs anything itself.
---

# Editor superengine: start here

## Output contract

Every run returns, in this order:

1. One plain line naming the job and why, never a skill name, e.g. "This is your raw recording,
   so I'll start your first cut."
2. That skill, invoked with the Skill tool by its full name from the table below.
3. When nothing fits, say so plainly: "That isn't something the editor does." When the ask is on
   the not-built list, say the one line "That's coming in this release, not built yet." Never
   improvise either one.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke this skill again before
  going on. Re-running is safe: the router only reads the ask and hands it over.
- One hand-off per ask. Once a skill has the work, don't route again unless the ask changes.

## Pipeline order

```
recording-preflight      before recording: check the setup, test clip
   -> recording
   -> reel-first-cuts    the spoken edit (fixes a joined master first)
   -> PICTURE LOCK       the cut is signed off and the timeline stops moving
   -> reel-canvas-build  the visuals
   -> reel-sound-pass    the sound: effects, voice clean-up, loudness (on the locked picture)

caption-writer           any time after the cut
reel-teardown            separate: someone else's reel, or an old posted one
style-decoder            separate: measure how a reel is edited, to copy the style
```

**Nothing about the visuals starts before picture lock.** Every comp is timed against the cut,
so a cut that moves invalidates every timing derived from it.

## Which skill

| The ask | Invoke |
|---|---|
| first-time setup, "is the editor ready", "check the editor's setup or tools", a missing or broken tool, anything another skill says isn't set up | `editor-superengine:editor-doctor` |
| "before I record", "check my setup" (before filming), "test clip", "will my mic and light work" (light gets advice; the test clip checks the camera and sound) | `editor-superengine:recording-preflight` |
| a master joined from several clips; words chopped after the first clip in a cut | `editor-superengine:reel-first-cuts` |
| "cut this", "build the A-roll", "make a first pass", "tighten the gaps", "the pause after X drags", "speed it up", "did the cut clip a word" | `editor-superengine:reel-first-cuts` |
| "build the beat map", "plan what goes on screen", "pick a layout", "design the hook", "motion comps", "comp the intro", "direction options", "ladder the blur", "will the Instagram buttons cover this" | `editor-superengine:reel-canvas-build` |
| "sound pass", "add sound effects", "mix the sound", "master the audio", "clean up my voice", "run Auphonic" | `editor-superengine:reel-sound-pass` |
| write or check the post caption (the text under the post), the hook line, alt text, hashtags | `editor-superengine:caption-writer` |
| tear down a posted reel, "what would we fix", "make a page to send them" | `editor-superengine:reel-teardown` |
| copy a creator's editing style, measure how a reel is edited, "make mine look like this reel", "decode this reel's style", "build a template from this style" | `editor-superengine:style-decoder` |

An ask that says "caption" but not which: ask once, "The words on the video, or the text under
the post?" The text under the post is caption-writer. Words on the video (burned-in captions)
are not built yet.

Every skill here is invoked as `editor-superengine:<skill folder>`.

### Not built yet

Music, burned-in captions, rendering scenes, colour grading, B-roll, a cover,
trial reels, the hub page, putting a copied style onto your own reel, or a hand-off to another
editor: say "That's coming in this release, not built yet." Say it plainly and stop. Never improvise it here or in another skill.

## Before the first skill that runs anything

`<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes.
Check that it exists with a file check only: `[ -f <editor python> ]`.

If it doesn't exist, or any skill reports a missing tool, invoke
`editor-superengine:editor-doctor`. Nothing here installs anything, and the client never types a
command.

## What the client hears

The client never sees file names, paths, JSON, STATUS or FIX lines, or script names. Translate
every one into plain words. How, with a line for each moment:
`${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-coach-hears.md`.

## The four shared references

| Reference | Applies when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md` | Always, before the first file. Duplicate the source, fewest generations, never judge picture on a proxy, load the governing docs first. |
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/preview-before-render.md` | Before any render, export or master. Cheap previews go to the reviewer first. |
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/frame-zero-hook.md` | Any time the hook frame is being designed or checked. |
| `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/design-prompt.md` | Handing a design canvas the art-director brief. |

## The one rule that outranks the router

**The human rules from frames and from the ear, never from prose.**

Do not ask for approval of a description, a plan or a table when the thing being judged is a
picture or a sound. Render the frame. Serve the cut. Every gate in this plugin measures *fit*;
none of them measures whether it lands. Three stages of `reel-first-cuts` stop for a ruling, and
every look in `reel-canvas-build` is picked off a rendered comp; the Beat Map only plans which look goes where. That is the design, not a
formality.
