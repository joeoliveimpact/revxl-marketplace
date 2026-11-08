# First-cut boards

## Carry a Send over

If only the recording or its clock changed and the words are the same, copy the old Send and board
config aside before the rebuild, then carry the Send over: `<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/port_selection.py" <old cut-selection.json> <old cut-board.config.json> cut-board.config.json -o cut-selection.json`.
If it refuses, ask for a new Send.

## Cut Board

It writes `cut-board.config.json` (every attempt of every line in every take; default: the last attempt
wins). Give the client probe.json's duplicate-frame % per speed (the board shows
the length). Start the board server and open the Cut Board (its hub tab, order 10) at `/editor/cut-board/?reel=<reel>` in the Browser pane, as
`${CLAUDE_PLUGIN_ROOT}/skills/editor-doctor/references/board-server.md` says. The client picks lines and
takes, strikes words, sets "Pause after commas" (0.20-0.40 s) and the speed, then presses Send (it
writes `cut-selection.json`).

## Tweak Board

For the `make_tweaks.py` command in SKILL.md Stage 8, `--take` is the take `selection_to_edl.py` named. `<N>` is 1 the first time, then one more than the
`version` in the current `tweak-board.config.json` on every Stage 9 round; a new version opens the board
empty. It writes `tweak-board.config.json` from
`work/cuts.json`. Open the Tweak Board (its hub tab, order 40) at `/editor/tweak-board/?reel=<reel>`
the same way. The client marks cuts, tight and loose pauses and the speed, then presses Send (it writes
`tweak-selection.json`).
