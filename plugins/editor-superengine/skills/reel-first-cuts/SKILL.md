---
name: editor-superengine:reel-first-cuts
description: Turns raw talking-head footage into a finished first cut. The client picks lines and takes on the Cut Board, then fixes the cut on the Tweak Board. Use on "cut this reel", "open the Cut Board", "fix it on the Tweak Board", "tighten the gaps", "several clips", "two recordings", "sync camera and mic", "make Shorts from this long recording", long recordings, or a master joined from several clips (words chopping only after the first clip). Not for captions or sound.
---

# Reel First Cuts

## Output contract (every run, in this order)

1. At each ⛔ ruling: the board open in the Browser pane and one plain line on what to do there, then stop
   for its Send. At the hard fail: what failed, in plain words.
2. After the render: the runtime, the silence-budget and cut-check results, and the review page with the
   listening checklist (Stage 8).
3. A last line: what the client does next, or what still stops the cut.
4. On a failure you can't fix in two tries: what went wrong in plain words, then the failure report
   below.

Speak the way `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-user-hears.md` says.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke it again before going on.
- Re-running is safe: the scripts read the raw and write only into `work/` and the board files. Re-run
  from the stage that changed; never render from an earlier render.
- If the raw or its edit map changed after a board was built, build that board again: its Send is stale.
  To carry a Send over, follow `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/boards.md`, "Carry a Send over".
  If it refuses, ask for a new Send.
- If the reel already has a Sound Board (`config.json`) or a Beat Map Send, a new cut means redoing the sound picks and the visuals plan. Tell the client before re-cutting.
- Never skip a ⛔ stage, on a re-run either.
- Run the style picker first if it has not run for this reel (editor-start-here); follow sections 5 and 6 (Auto edit and controls in chat) of ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md.

## Ground rules

- **The client never types a command.** Claude runs each one with the Bash tool from the client's
  workspace folder (the scripts read `editor/editor.config.json` there). Every path below is inside the reel folder `<reel folder>` = `<paths.videos>/<reel>/` (editor/editor.config.json): put that folder in front of it when you run it. RAW.mp4 is the raw; the master render is `work/renders/master-<speed>x.mp4` (1.15x → `115x`).
- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. If it doesn't exist, run `editor-superengine:editor-doctor` first. Every script runs as `<editor python> -X utf8 -I "<script>" ...`, never a bare `python`; the failure report's commands run exactly as written.
- No board available, or the client asks to do it in chat: run Stages 2, 3 and 5 as
  `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/no-board-path.md` says.

## Definition of done

A rendered cut where:
- every cut boundary sits in verified silence, not an ASR estimate
- no deletion contains sustained speech
- no segment is a stranded fragment
- **the whole cut is inside its silence budget** (Stage 7b): every other check is local, this one is the sum
- the client has heard it and signed off

## The stages, in order

| # | Stage | Script |
|---|---|---|
| 0 | Probe & calibrate | `clock_fix.py` (joined clips only), `probe.py` |
| 1 | Transcribe (words, edit map) | `transcribe_words.py` |
| 2 | ⛔ Cut Board — RULING | `make_board.py`, `selection_to_edl.py` |
| 3 | ⛔ Boundary audit + map check — HARD FAIL | `boundary_audit.py`, `word_map.py`, `map_check.py` |
| 4 | Tighten gaps | `gaps.py` |
| 5 | Speed (ruled on the boards) | — |
| 6 | Render once, from the raw | `render.py` |
| 7 | Verify + cut checks | `transcribe_words.py`, `fix_words.py`, `repeat_check.py`, `cut_qa.py` |
| 7b | Silence budget — HARD FAIL | `silence_budget.py` |
| 8 | ⛔ Ear pass + Tweak Board — RULING | `make_tweaks.py` |
| 9 | Gap corrections | `tweaks_to_edl.py`, then Stages 3 to 8 again |

**Do not reorder the stages**: the order puts the strongest check first.

## The governing rule

**Calibrate from the file; never ship a magic number.** Before hardcoding a threshold, read
`${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/why-constants-fail.md`. Run the scripts; don't
re-derive them.

## Stages

### 0 · Probe & calibrate — trust nothing

For a new reel or before probing an existing take, follow `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/recordings.md` (folder creation, either raw layout, single-take copy or several recordings).
If the raw was joined from several clips, or words chop only after the first clip, fix the
master first with `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/master-clock.md`.
A failed proof stops the cut.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/probe.py" RAW.mp4 -o work/`

It measures the true frame rate (never `r_frame_rate`), the source RMS envelope every later stage reads,
per-file thresholds, the duplicate-frame table per speed (report it, never assert a rule), the picture
and `audio_stream` (`--audio-stream N` picks another; with several, confirm it is the voice).
Pass on, word for word, the one-side mic note if probe prints it.

**Several recordings:** each is a take; run Stages 0–1 in its own folder and log it with `footage_check.py add`.
Flow, limits and commands: `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/several-recordings.md`.
**One long recording, several Shorts, or long quiet stretches:** `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/short-clips.md`.

### 1 · Transcribe — a contract, not a vendor

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py" RAW.mp4 -o work/tx.json --probe work/probe.json --edit-map work/edit_map.json`

It writes `work/tx.16k.wav` and the edit map. Pass on, word for word, the backup engine's warning and the stop for a nearly silent track.
Engines and guards:
`${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/transcription-contract.md`.

If it says word alignment isn't available on this Mac, there's no edit map and no Cut Board: run Stages
2, 3 and 5 by the no-board path, using `work/tx.json` wherever a command says `work/edit_map.json`.
Skip cut checks 2 and 3 (both read the cut's edit map), and say so.

**Script check** (only if the client names their script file): run `script_diff.py` before any Cut Board,
as `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/map-and-script-checks.md` says. It fixes
misheard brand names, warns under 25 % match and lists the rest for review.

### 2 · ⛔ Cut Board — RULING
With the Write tool, put the approved script in `script.md` (one spoken line per line) (no script: write it from the transcript, one line per spoken sentence, and tell the client you did) and the shots in
`shots.json` (`{"vocab": ["talking head", "screen"], "default": "talking head"}`), then:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/make_board.py" --script script.md --take 1:work/edit_map.json:work/tx.16k.wav [--take 2:work/take2/edit_map.json:work/take2/tx.16k.wav] --shots shots.json --reel <reel> -o <reel folder>`

Open the Cut Board as `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/boards.md`, "Cut Board", says.
A line said twice in different words shows Keep first / Keep second / Keep both: the client picks; never cut one yourself. Then:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/selection_to_edl.py" cut-selection.json cut-board.config.json`

It writes `work/edl.json` with each cut's take and prints the gaps.py command (takes.py for a mixed ruling);
Stage 4 runs that line. `REFUSED` (exit 3: word times drifted over 80 ms, or a stale board): rebuild the board and ask for a new Send.

### 3 · ⛔ Boundary audit + map check — HARD FAIL
After every gaps.py run, before anything renders:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/boundary_audit.py" work/ work/edit_map.json`

Exit 1 names each boundary inside a word or next to speech energy and prints how to re-derive it: run what it prints, then audit again. Never ship a flagged boundary.
Not optional: word times are estimates (transcription-contract.md).

Then `word_map.py`, then `map_check.py` (map-and-script-checks.md). Any block means no render: say its
line to the client in plain words (also in `work/map_check.json`).

### 4 · Tighten gaps — in source coordinates, no render
Run the gaps.py or takes.py command Stage 2 (or 9) printed, exactly as printed. It writes `work/cuts.json` (whole
frames; `segments.json` is derived for the old path), `work/gap-plan.txt` and `work/listen.txt`. Each deletion is proven free of *sustained*
speech; a silent runt is absorbed, a speech-bearing runt reverts its deletion. Rule on every borderline
it surfaces; never resolve one silently.

### 5 · Speed — ruled on the boards
`atempo` keeps the pitch.

### 6 · Render once, from the raw

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/render.py" work/ RAW.mp4 --master --scrub`

If the client approved a grade (reel-grade step 4), add `--grade grade.json`, so a new cut keeps the colour.
Read `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/cut-checks.md`, "Render rules (Stage 6)".

### 7 · Verify + cut checks
Run the four checks in `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/cut-checks.md`, in its
order, and act on each hit as it says.

### 7b · Silence budget — HARD FAIL

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/silence_budget.py" work/renders/master-<speed>x.mp4 --probe work/probe.json --words work/cut/tx-cut.json`

The share of the **rendered** cut where nobody talks: budget **12%**, exit 1 when over, the offending
gaps ranked with the words either side. `silencedetect` logs at **info**: never pass it `-v error`. **Within budget is not approval.**

### 8 · ⛔ Ear pass + Tweak Board — RULING
A cut whose `work/cuts.json` has `takes` has no Tweak Board yet: follow `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/several-recordings.md`. Otherwise:
Hand over the review page, `work/cut-review.html` (raw and cut side by side, the 20 largest cuts),
**with the checklist** (`work/listen.txt`), and say plainly what the gates cannot see: they passed on
all four defects the client caught in the reference build. Run `long_silence.py work --json` (short-clips.md, "After the cut"), then:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/make_tweaks.py" --cut work/renders/master-<speed>x.mp4 --work work --config cut-board.config.json --take 1 --version v<N> -o <reel folder>`

For version numbers and the Tweak Board, follow `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/boards.md`, "Tweak Board".
Preview rules: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/preview-before-render.md`.

### 9 · Gap corrections — the ear-driven loop
Only for cuts without `takes`; otherwise follow Stage 8's Cut Board path.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/tweaks_to_edl.py" tweak-selection.json work`

It maps the marks back to source time (exit 3 on a word time drifted over 80 ms), holds untouched
segments whole, carries the Cut Board's beat, writes `work/edl.json` and prints the next gaps.py
command. Run it, then Stages 3 to 8 again.

A Tweak Board Send with **no marks is the sign-off**. Still run `tweaks_to_edl.py` and the gaps.py command it
prints (an empty Send gives back the cut's own `work/cuts.json`, which moves the hub past "Ear pass"), then
go on to the next step. Don't re-render or open a new Tweak Board version.

A complaint in plain words instead ("that pause drags"): **diagnose before fixing** and fix the
mechanism, as `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/correction-loop.md` says. Loop
until the client signs off.

## What this skill will not decide

- **Lines, takes, runtime and speed**: the client rules on the boards.
- **Protected beats.** Comedic timing is unmarked in audio: propose candidates from the script, then ask.
- **Whether it sounds right.**

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.0 --skill reel-first-cuts --step '<the stage that failed>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
