# Map check and script check

`<editor python>` and the path rule (`work/` is `videos/<reel>/work/`) are in SKILL.md's Ground rules. `<reel>`
is the reel's folder name.

## Contents
- The map check: before every render
- What a block means, and what to say
- The script check: after Stage 1, only on request
- Reworded retakes: the client picks on the Cut Board
- Line scoring: the no-board path

## The map check: before every render

It proves the cut still says what the client picked. Run it after every gaps.py run (Stage 4, and again after
every Stage 9 round), right after the boundary audit in Stage 3 and before render.py:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/word_map.py" videos/<reel>`

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/checks/map_check.py" videos/<reel>`

`word_map.py` writes `work/word_map.json`: every word the cut keeps, where it sits in the raw and where it lands
in the cut. It reads the edit map the cut was made from (the Cut Board take's, else `work/edit_map.json`) and that
take's `cuts.json` in the same folder (`work/cuts.json`, or `work/take2/cuts.json` when the client ruled on take 2),
and stamps a fingerprint of both, so a map written before the last change counts as stale. With no edit map (word
alignment isn't available on this computer), it uses the word times in `work/tx.json`. With no word times at all
it writes nothing, and both scripts say "No word timings on this computer, so the word check was skipped; the cut
can still render": tell the client, and the render goes ahead.

`map_check.py` changes nothing in the cut. It passes only when:
- every word the client picked plays in the cut, once;
- no word the client struck, or never picked, plays;
- the picked words play in the order the client picked them;
- every word lands within 6 ms of where the cut list (`cuts.json`) puts it.

The first three need the Cut Board's `cut-board.config.json` and `cut-selection.json`; without them (the
no-board path) only the word map and its times are checked. Once a Tweak Board exists (`tweak-board.config.json`,
Stage 8), its word times are checked against the cut too, within the same 6 ms, but only while the board was built
from the current `cuts.json`. After a Stage 9 round changes the cut, the old board gives one warn instead ("Tweak
Board is from an older cut, rebuild it to re-check timing"): the render goes ahead, and Stage 8 builds the new
board from it.

**Two clocks for one word.** Every word has two start times. The board anchor time is the speech model's own
estimate: the Cut Board, its 80 ms drift guard and the Tweak Board all place words by it, so a ruling lands the
same way every time. The aligned time is the same word measured again against the audio: gaps.py cuts from it,
and so does the render. The two can differ, so the word map keeps both, each turned into a time in the cut. The
render is checked on the aligned time, the Tweak Board's word times on the anchor time.

Exit 0 is clean; exit 1 means at least one block. Every run prints one line per finding (`BLOCK <name> <message>
(<where>)`, or `WARN ...`) and writes `work/map_check.json` (`{"blocks": [...], "warns": [...]}`, each with its
plain message), so the reason stays on file after the chat moves on.

## What a block means, and what to say

Any block means no render. Say the block's message to the client in plain words; the messages are written for
that ("line L03: the word 'today' was picked but is not in the cut."). Never render around a block, and never
edit `work/word_map.json` or the check by hand.

| Block | What it means | What Claude does |
|---|---|---|
| `word-map-missing`, `word-map-stale` | No word map yet, or the cut list or edit map changed after it was written | Run both commands again. |
| `word-missing`, `word-not-kept`, `word-wrong-piece`, `word-time` | The word map and the cut disagree | Run both commands again; still blocked: a fault in the cut. |
| `word-twice` | One word sits in two pieces of the cut | A fault in the cut. |
| `quote-missing`, `quote-twice`, `quote-extra`, `quote-order` | The cut doesn't say what the client picked: a picked word is missing or plays twice, a struck or unpicked word plays, or the order changed | A fault in the cut. |
| `board-unreadable` | The Cut Board's two files don't fit together | A fault in the cut. |
| `tweak-time` | The Tweak Board's word times don't match this cut, or its file can't be read | What the message says: rebuild the Tweak Board (`make_tweaks.py`) from this cut. |

`tweak-word` is a warn, not a block: the Tweak Board shows a word this cut doesn't keep. Check it by ear.
`tweak-stale` (the Tweak Board is from an older cut) and `no-word-times` (no word timings on this computer) are
warns too: say their line to the client, and the render goes ahead.

**A fault in the cut** means the cut itself is wrong, not the map. Tell the client the line, render nothing, and
find the cause as SKILL.md's failure rules say: one you can't fix in two tries gets the failure report.

## The script check: after Stage 1, only on request

Run it only when the client names their script file, right after Stage 1 and before any Cut Board is built. Its
fixes change the edit map, so a board built before them would be stale (SKILL.md's Re-invoke guard). With several
recordings, run it once per take's edit map (`work/take2/edit_map.json` and so on).

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/script_diff.py" "<script file>" work/edit_map.json [--never "word,word"]`

`<script file>` is the file the client named, by its full path. The check lines the script's words up against
what was heard, then:

- **Under 25 % match:** probably the wrong script. It prints a warning, changes nothing and exits 1. Ask the
  client whether it is the right file; with the right one, run it again.
- **Brand-like words that sound close** are fixed in the edit map: names and products the speech model misheard.
  Brand-like means a capital letter mid-sentence, a capital inside the word, a digit, or a word the workspace's
  `word-fixes.json` already knows (cut-checks.md, check 2). Two or three heard words for one script word are
  merged into one word ("Zen Trova" becomes "Zentrova"). The fixes go through `fix_words.py` (`--at` for one word,
  `--merge` for several into one), which keeps the old file as `<name>.prev` and rechecks the edit map's word-list
  fingerprint. Each prints as `fix: ...`.
- **Everything else** is listed as `REVIEW: heard ... / script ... (why)` and left as it is. Tell the client what
  is on the list in plain words. Change a word only when the client asks, with `fix_words.py --at` on the same
  edit map (cut-checks.md, check 2).
- **The client's never list:** words the client says must never be changed. Pass them as `--never` on every run;
  each one it would have changed prints as `never list, kept`.

Exit 0 means done. Exit 2 means bad input or `fix_words.py` refused the fix; the edit map is unchanged, and it
is a failure as SKILL.md says. Every run writes `work/script_diff.json` next to the edit map: the match share, the
warning, the fixes, the review list and the never-list words it kept.

## Reworded retakes: the client picks on the Cut Board

`make_board.py` flags a line where the speaker said the same thing twice in different words inside one attempt:
two sentences within 15 s that share at least half their content words but are not a word-for-word retake. The
board shows "Said twice in different words: pick one" on that line, with Keep first / Keep second / Keep both.
Keep both is the default: nothing is struck until the client picks. The pick is stored as struck words, rides the
Send into `cut-selection.json`, and `selection_to_edl.py` follows it. Claude never cuts a reworded retake on its
own. "Never, never" said on purpose is not flagged.

Stage 7's repeat check prints the same kind of hit as a `review` line ("said twice in different words: pick one
(not cut)"). It is never cut there either: the client decides.

## Line scoring: the no-board path

With no Cut Board, Stage 2's trim table comes from `line_score.py`. Its steps, command and rules are in
`no-board-path.md`, "Stage 2 in chat".
