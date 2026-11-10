---
name: editor-superengine:reel-captions
description: Plans burned-in captions for the signed-off spoken cut, proposes truthful word marks, and picks a caption look before rendering. Use for captions, subtitles, caption style, burned-in captions, karaoke captions, pick a caption look, highlight these words, change the caption colour, turn captions off, or make this my default caption look. For words on the video; the post caption belongs to caption-writer.
---

## Output contract (every run, in this order)

1. One plain line saying whether the caption look needs picking, the caption plan is ready, or a check stopped it.
2. If the look is unset, ask exactly: “Which caption look? Clean, Bold pop, Boxed, Karaoke or Outline caps (or no captions)”.
3. After planning, a short summary of the look, any words left off and any notes, plus the next step.
4. On a failure you cannot fix in two tries, offer the failure report below.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke it again before going on.
- The spoken cut must be signed off. A changed cut needs a new Beat Map Send and a fresh caption plan;
  marks refer to positions in that cut's word list, and words are never renumbered.
- Keep the client's existing choices. Ask before replacing a board they edited.
- A plan does not mean a render. The final video still needs the client's OK of the latest preview,
  recorded by reel-canvas-build's `compose.py ok`.
- Follow sections 5 and 6 (Auto edit and controls in chat) of ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md.

## Ground rules

- **The client never types a command.** Claude runs each command from the client's workspace folder.
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes. If it's missing, run `editor-superengine:editor-doctor` first.
- Plain English for a busy user. Never show file names, paths or JSON to the client.
- There is no default look. “No captions” is an explicit choice, never a fallback.
- Your captions automatically get a dark backing over B-roll when your chosen look has no plate.
- All looks and options are the client's taste. Read `${CLAUDE_PLUGIN_ROOT}/skills/reel-captions/references/looks.md`.
- Use Inter Regular only, weight 400, with its licence on file. Use the literal family name Inter.
- Keep the smallest truthful phrase: “doesn't work”, never “work” alone.
- At most one punch event per sentence, even when it spans several words. Later marks keep their accent;
  numbers and calls to action never punch. Do not remove qualifiers to make a phrase fit.
- A truthful marked phrase longer than three words, or one that straddles a layout change, is shown
  without its stress, with a plain note. Offer a shorter truthful phrase if the client wants it stressed.

## Flow

1. `captions.py plan` reads the reel's Sends and the active saved style itself; don't read the style file. With no choice, ask the plain look question above. Never infer a look from the editing style.
   To compare looks on the client's own cut, run:

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-captions/scripts/captions.py" picker --reel-dir "<reel folder>"`

   Open the Look Picker tab in the hub. The client compares the looks, picks the options and presses Send.
   A remembered look is highlighted as “Your last pick”; it is recommended, and the client still chooses and presses Send.
   When clients explain their pick, keep their words: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/standing_notes.py" pick <key> --value <json> --note "<their words>"`.
   Layouts there are previews only. IDs are `clean`, `bold-pop`, `boxed`, `karaoke`, `outline-caps`, or `none`.
   On `make_default: true`, run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/saved_style.py" set caption_style '<the Send's caption_style JSON>' --reel "<reel folder>"`, then plan and make the normal preview below.
2. Offer marks on numbers, key words, a phrase to stress or a call to action. Run:

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-captions/scripts/captions.py" marks --reel-dir "<reel folder>" --candidates '<JSON list of {w, mark}>'`

   Use only `num`, `key`, `emph`, `cta`. The returned JSON is the truthful expanded word positions for the
   Beat Map plan's `word_marks`. Preserve the one-punch note; later marks keep their accents.
    If the Beat Map was already sent, tell the client which marks changed and ask whether to update it; on yes, rebuild it as `reel-canvas-build/references/beat-map.md` says (`--replace`, only after their OK) and have them Send it again; on no, leave it as sent.
   Optionally add `--loud` to suggest marks from louder words. `loud_emphasis: true` uses these only when
   the Send has no word marks. Offer `mark_look: "marker"` for a swipe behind the whole marked phrase;
   the default stays `"accent"`. Both options preserve truthful spans and the one-punch limit.
3. Save the choices, then plan:

   `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-captions/scripts/captions.py" plan --reel-dir "<reel folder>"`

   This writes `work/captions.json`. Exit 1 means a plain stop or the look question; exit 2 means input
   needs fixing. Echo and overlay exclusions are declared by word position; empty words and captions
   off are declared too. Minimum reading time is a note, never a reason to drop words.
4. Rendering belongs to reel-canvas-build's `compose.py`: every preview and final draws the picked look.
   Read `${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/build.md` and follow its preview/OK flow.
   Do not render another way.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.0 --skill reel-captions --step '<the caption look, the word marks or the caption plan>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
