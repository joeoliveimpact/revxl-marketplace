# Cut checks (Stage 7)

Four commands run on every render, after it and before the silence budget (SKILL.md, Stage 7).
`<editor python>`, CUT.mp4 and the path rule (`work/` is `videos/<reel>/work/`) are in SKILL.md's
Ground rules.

## Contents
- Render rules (Stage 6)
- 1. Re-transcribe the cut
- 2. Fix misheard words, then check the call to action
- 3. Repeats, restarts and retakes
- 4. Silence-only trims and murmurs
- What the client hears

## Render rules (Stage 6)

No `--speed`: `cuts.json` holds the latest board's ruling (the Tweak Board's after Stage 9); never re-run gaps.py to match a speed.
render.py reads only `work/cuts.json`, asserts the frame count, conforms to
1080×1920 SDR with a dense GOP, and writes the review page. Never build from an intermediate (rule 2 of
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md`).

## 1. Re-transcribe the cut

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py" CUT.mp4 -o work/cut/tx-cut.json --edit-map work/edit_map.cut.json`

The same engine and guards as Stage 1, on the cut. `work/edit_map.cut.json` is what checks 2 and 3 read;
`work/cut/tx-cut.json`, in cut time, is what names the gaps in the silence budget (Stage 7b).
Adjudicate a diff against the raw transcript acoustically (why-constants-fail.md, "The check that lies"). A clean
round-trip is not a clean cut either (ASR rebuilds a sheared word tail): the waveform (Stage 3) judges
boundaries.

## 2. Fix misheard words, then check the call to action

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/fix_words.py" work/edit_map.cut.json`

Corrects names, products and jargon the speech model heard wrong, before they become captions. The fixes
come from `<paths.editor>/word-fixes.json` (`paths.editor` in the workspace's `editor/editor.config.json`;
else `editor/word-fixes.json`), or `--map <file>`:
`{"fixes": {"old": "new"}, "phrases": {"<context words> <old>": "<new>"}, "cta": ["KEYWORD", ...]}`.

- `fixes` replace a word everywhere; `phrases` replace only the last word of a matching sequence.
- One-off mistake: `--at '{"175": "agentic"}'` (list index, from 0).
- The file is updated in place, the previous one kept as `<name>.prev`; the edit map's word-list hash is
  recomputed.
- A word heard wrong in several reels belongs in `word-fixes.json`, not in `--at`.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/fix_words.py" work/edit_map.cut.json --cta-check`

Changes nothing: one line per `cta` keyword. Exit 1 = a keyword is missing from the cut. Chat-automation
triggers are exact-match, so a missing or misheard keyword never fires: check whether it was cut (the
board ruling) or misheard (add a fix), and tell the client which.

## 3. Repeats, restarts and retakes

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/repeat_check.py" work/edit_map.cut.json --audio CUT.mp4`

Finds a word or phrase said twice in a row, a cut-off start ("Man- ManyChat"), a restart (the same 2+
words again within `--gap` s, default 1.5) and a retake (the same 5+ word sentence again within 15 s).
Each hit prints the span to drop: the FIRST copy, so the clean take stays.

`--audio` is deep mode: transcribers often merge a repeat into one copy, so it re-transcribes the cut in
short overlapping windows (`--win`, default 3 s) with the engine the doctor picked.

**Limit:** deep mode catches restarts within about 3 s (both copies inside one window). Retakes further
apart are the shallow finder's job: without `--audio` it reads the whole transcript, so a line said
again 8 s later is found there, not in deep mode.

| Exit | Means | What Claude does |
|---|---|---|
| 0 | No repeats | Go on. |
| 1 | Repeats found | Name each span to the client by the words around it; one they want gone is a cut mark on the Tweak Board (Stage 8). |
| 3 | No transcriber on this computer | Run the shallow check (no `--audio`) and say deep mode didn't run. |
| 5 | A transcriber step failed | Run it once more; still 5: the shallow check, and say deep mode didn't run. |

## 4. Silence-only trims and murmurs

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/cut_qa.py" work/ --words work/edit_map.json`

Runs on the plan, not the render: `work/cuts.json`, the EDL (`--edl`, default `work/edl.json`),
`work/envelope.json` and the source edit map. Levels are against p90 of the whole envelope.

- **silence-only:** a span gaps.py removed inside one EDL cut FAILS when 40 ms of it is above
  p90 - 18 dB (voice was trimmed). Spans between EDL cuts are the client's own edits and are skipped.
- **murmur:** kept audio with 0.28 s between p90 - 24 and p90 - 9 dB that no edit-map word covers (or
  only a word over 0.8 s long) is flagged.

Each line gives the source time and the output frame. Exit 0 = clean; 1 = a check failed or a murmur
was flagged: name each one on the listening checklist, and treat a failed trim as
`${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/correction-loop.md` says (diagnose before
fixing). Exit 2 = an input is missing: re-run the stage that writes it.

## What the client hears

Plain words, per `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-coach-hears.md`:
"I checked the cut for repeated words, missing keywords and any voice the trims touched." Name only the
hits, by the words around them; never script names, exit codes or dB figures unless they ask.
