# Your saved styles

Run each command from your workspace with the editor Python defined in editor-superengine:editor-start-here. You never type a command; Claude runs it.

## 1. Save this reel as a style

When the client says **"save this as my style"**, save a new style:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" save-from-reel <reel folder>`

Read back the choices, say the new name (Style N), and offer a rename in the same line.
A new name runs the same script's `rename <style name> "<new name>"`.
`save-from-reel <reel folder> --name <style name>` (quote names with spaces) updates an existing style, keeps its other settings,
and writes the client's workspace skill. Tell the client: "Your default doesn't carry word punches to later reels. To get them on a later reel, pick Punch-ins and a Word punches setting in that reel's Editing style panel, then mark the words to stress; that reel then uses its panel choices instead of your default."

## 2. Make one the default

For **"make it my default"**, ask which saved style, then run the same script's `set-default <style name>`.

## 3. List, show, rename, delete, restore

Use the saved-style store for named styles; decoded specs are referenced by id.
Run with the `<editor python>` defined above:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" show [style name]`

Read it back in plain words. The same script's `list` lists saved styles; `show [style name]` reads one
(without a name, the active style). `rename <style name> <label>` changes its name; `set-default <style name>`
makes it the recommended pick. `delete <style name>` moves it to the archive, restorable with `restore <archived version>`.
Quote names with spaces; ids also work.

## 4. Change one saved choice

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" set <key> '<json>' --reel "<reel folder>"`

This changes one saved choice in this reel's picked style and keeps its other choices. Without a saved style picked, pick one first. For named-style management without a reel, use `--style "<style name>"` instead of `--reel`. Use `fields` on the same script for the allowed keys. It archives the previous version when the choice changes.

## 5. Save a decoded style as a new style

After the client approves the decode, run:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" save-from-reel <reel folder> --from-decoded <slug>`

This saves a NEW Style N and uses it on this reel when its pick is Copy or missing; an existing different pick stays as chosen. It never makes the copied style the default unless the client asks for `set-default`. Say the new name and offer a rename in the same line.

Copied choices: the editor edit style, caption look and grade look; the caption-default role's closest available font; the first valid accent colour (brand and captions); minimum caption reading time; and recognised transition types (whip, zoom, glitch, flash, fade, push, wipe, shader). Plain cuts need no setting. This reel's board Sends win over the decoded choices. Shot rhythm and speech distributions do not set the pause between lines.

Before `index`, style-decoder writes `adapters.editor`, judging the closest choices from the frames (use `UNKNOWN` where unmeasurable). When the client came from "Copy a reel I like", after approval save the decoded style with this section's command. Allowed choices:
- `edit_style`: `punch-in`, `layout-switch`, or `UNKNOWN`.
- `caption_style`: `clean`, `bold-pop`, `boxed`, `karaoke`, `outline-caps`, `none`, or `UNKNOWN`.
- `look`: `natural`, `warm`, `punchy`, `soft-matte`, `mono`, `none`, or `UNKNOWN`.

Say every "Not copied" line in plain words: layouts, motion rules, structure, assets, colour skins, audio and other typography details have no editor setting yet. Unknown or unsupported choices are named too. A draft is saved with a draft notice; if nothing matches and this reel has no choices, nothing is saved and the reel starts fresh. The decoded reference stays with the style. To fill an older style that holds only that reference, re-run with `--name "<style name>" --from-decoded <slug>`; other saved settings are kept.

## 6. Standing notes

For Standing notes, run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/standing_notes.py" add` or `list`; `add --help` explains matching a choice. Tell the client plainly when a note "Could not be matched".

## 7. Auto edit on or off for good

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/style_learn.py" auto <style> on|off --workspace <workspace folder>`

Only your default style starts Auto edit; "stop" or "normal mode" covers one reel.

## 8. Keep your workspace skill current

`save-from-reel`, `rename`, `set-default` and `delete` keep your my-editing-style skill current.
