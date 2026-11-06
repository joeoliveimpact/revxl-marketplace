# Several recordings in one reel

Each recording is a take. Run Stages 0 and 1 per take: `work/` for take 1, `work/take2/` for take 2, and so on.
Keep each probe, envelope and edit map beside that take's transcript. Paths below follow SKILL.md's Ground rules.

Before cutting, log each raw:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/checks/footage_check.py" add videos/<reel> RAW.mp4 --role aroll --origin own --licence own`

Repeat for every recording. `videos/<reel>/footage/ledger.json` holds one row per SHA-256: `id` (`f01`, `f02`, ...),
`sha256`, `path`, `role` (`aroll` or `broll`), `origin` (`own` or `ai`), `licence`, and optional `job_id`.
Adding the same bytes again returns the existing ID. Use the logged path in the take's probe.

Build one Cut Board with `--take N:edit_map.json:tx.16k.wav` for every take, as Stage 2 shows. The client may pick
any line from any take. Each EDL cut carries its take; old cuts without it mean take 1. A one-take ruling on
take 1 still prints gaps.py. A one-take ruling on any take but 1 still goes through takes.py: Claude runs
`takes.py work/ --edl work/edl.json --take N:work/takeN:work/takeN/edit_map.json --speed <speed>`, so the cut
lands in `work/`. A mixed ruling prints takes.py with one `--take N:folder:edit_map.json` per used take.
Keep its output in the reel's `work/`.

Run the appropriate command, including pause protections, beat and speed. takes.py runs gaps.py separately on each
consecutive run of the same take, in `work/runs/rNN/`. A recording change is always a hard cut: no pause joining
across it. Mixed `--protect` ranges are `N:from:to:cap`; their times belong only to that take. Boundary audits run
on each run with its own edit map: takes.py prints one `boundary_audit.py work/runs/rNN/ <that take's edit map>`
line per run (run every one; each must exit 0) and removes any old `work/segments.json`. The word-map and map checks read the merged cuts and all used maps.

A cut whose `work/cuts.json` has `takes` has no Tweak Board yet. Give the review page and the listening
checklist at Stage 8. Take fixes back to the Cut Board (a new Send, then the printed takes.py), or rerun
takes.py with `--protect N:from:to:cap` / `--hold`. Never run make_tweaks.py or tweaks_to_edl.py on it.
The client makes the picks; Claude runs the commands.

Hard rules:

- A used recording must exist, have exactly one matching ledger path and still match its SHA-256. A changed file stops the render.
- Two uses of the same recording bytes cannot overlap in source frames. Touching intervals pass. Picking each scene once is not enforced.
- Measured frame rates must be within 0.5%. Probe all takes with one master `--out-rate` and use one speed. Per-take frame-rate conversion is not built.

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/checks/footage_check.py" check videos/<reel> work`

Exit 3 prints each block in plain words. Fix every block before rendering. Mixed reels need a ledger; a legacy
single-take reel without one keeps its old path.

Render with Stage 6's command, passing the lowest numbered used take's raw positionally, without renumbering.
Every raw is
an input to one filter graph and one encode, with its own size, HDR conversion and audio stream. The first take's
sample rate is shared. A face `crop.json` applies only to take 1; other takes get a centred crop, with a note.
The assembled master is the single source for later picture and sound work.

gaps.py and takes.py write `work/timemap.json`: master fps, speed and segments containing output frame bounds,
take, raw file, ledger SHA-256 (null when unlogged), and source in/out frames. Render joins whole source frames,
then changes speed once. For output frame `f`, joined frame `j = min(total_source_frames - 1, ceil((f + 0.5) * speed) - 1)`
is the last frame due under ffmpeg's nearest timestamp rounding. Find its segment by cumulative
`src_out_f - src_in_f`; the source frame is `src_in_f + j - cumulative_source_frames_before_segment`.
An output segment start can still show the previous segment; the cut's output bounds stay unchanged.
Word timing keeps `out_in_f/fps + (src_t - src_in_f/fps)/speed`. Mixed word maps qualify IDs as `tN:<source ID>` and keep `source_id`.

## A separate camera and good microphone

Match their shared voice before probing and transcribing:

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/sync.py" --video camera.mov --audio microphone.mov --out work/sync`

It writes `synced.mp4` (camera picture and microphone sound), `screen.mp4` when the microphone recording has video,
and `sync.json` (offset, score and check lag). Below 0.3 it stops: confirm both files are the same take. Listen to the
match. Log and use `synced.mp4` as the take's raw, then run Stages 0–1 on it.

## A synced screen recording

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/follow_cut.py" work/sync/screen.mp4 --cuts work/cuts.json --out work/screen-cut.mp4`

This trims the screen on the same frames at the same speed and asserts the output frame count. It stops on mixed
takes: one screen recording can follow only one recording's cut.
