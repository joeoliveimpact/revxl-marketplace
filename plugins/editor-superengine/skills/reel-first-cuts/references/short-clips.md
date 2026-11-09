# Shorts from one recording

Use `scripts/clip_cut.py` when one long recording contains several independent
ideas. Read the transcript first, choose complete thoughts, and cut them into
separate folders. Each Short then starts its own reel workflow with its own
`source.mp4`; these cuts do not replace the frame-based final edit.

Run with the editor Python and runtime tools:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/clip_cut.py" RAW.mp4 --words work/edit_map.json --clips work/clips.json --out "<videos folder>"`

Use `work/tx.json` only when there is no edit map. Each clip folder is named as its reel, and each clip's `source.mp4` becomes the new reel's `RAW.mp4`.

`--words` accepts `work/tx.json`, `work/edit_map.json`, or a flat list of
`{i, text, start, end}` words. Object transcripts use list position as the word
index and accept `word` in place of `text`. Times are original recording seconds.

`clips.json` is a list. Use inclusive word indices, or explicit seconds:

```json
[
  {"name":"one-idea", "from":12, "to":88, "why":"a complete question and answer"},
  {"name":"another-idea", "start":110.2, "end":143.7, "why":"a useful example"}
]
```

Word ranges get 0.15 seconds of padding on each side (`--pad` changes it).
Seconds ranges include only words wholly inside them. The output is
`<out>/<name>/source.mp4` and `words_raw.json`, with zero-based indices and clip
times. `--also screen.mp4` cuts a second synchronized recording into `screen.mp4`.
Names omitted from the list become `clip-1`, `clip-2`, and so on.

The whole request is checked before any output is written. A range beyond the
recording duration, word indices beyond the list, invalid or backwards ranges,
unsafe folder names, duplicate names, or existing clip folders are refused with
exit 2; padding past the recording is trimmed to its edge. An optional synchronized recording must cover the same range.
Folders are never overwritten. A tool failure after encoding begins can leave
an incomplete new folder; inspect it and choose a fresh name for the retry.

This is another encode generation, disclosed by
`info: encode generations +1 (re-encode crf 16)`. Lengths outside 15-75 seconds
are flagged for editorial review, rather than silently shortened.

## Intake before cutting

After the recording probe, run:

```text
<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/caption_scan.py" RAW.mp4 --work work
```

The scan samples the entire recording at 1 fps. `work/intake-sheet.png` shows
every sample, and `work/intake.json` records `burned_in`, `score` (the fraction
of flagged samples), and `flagged_s`. The detector looks for many alternating
contrast edges in a shallow horizontal band that recurs in two or more samples.
It does not read words. It is tuned on synthetic clips; texture and signs can
look like text. Claude must inspect the sheet before refusing real footage.

Exit 3 flags likely burned-in words: the footage already has words burned in;
the editor won't cover them. Return the original footage untouched once visual
inspection confirms the finding. Exit 0 means no persistent band was found;
still inspect the sheet. Text lasting less than a second can fall between
samples. Exit 2 means the scan could not finish, not that the recording is clean.

## After the cut

Run `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/long_silence.py" work --json` after the frame cut list has been made. It maps
original word intervals through the kept segments and speed, then asks about
each output interval with no words for at least 3 seconds:
linger on the last caption / title card / cut it? The line names its output
time. You can also pick in the Tweak board's "Long quiet stretches" panel; a saved pick is printed and is the answer.
Cut means the board's cut mark is applied by the next re-cut; title card means add a title scene on that beat;
keep the caption means hold the last caption through the gap. Present the question in chat only for gaps without a pick.
The optional report is `work/long-silences.json`, with `silences` containing
`{start, end, duration}` in output seconds. It always exits 0 because this is a
conversation prompt, including when the inputs need repair.
