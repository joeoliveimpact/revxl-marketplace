# The Sound Board

A board for spotting sound on a picture-locked reel. The client watches the locked cut, auditions candidate
sounds against the picture in a loop, slides a music bed on a waveform, and sends their decisions back as one
file. It replaces rounds of blind question-and-answer ("does 58.2 feel right?") with one sitting: sound placement
is an ear judgment, so the picture, the candidates and the timeline go in front of the person who decides.

## Setting it up

`new_board.py --reel <reel>` (see SKILL.md for the full command) copies the workspace sound library into the
reel folder (`sfx/`, `beds/`), probes every sound, computes the waveforms, and writes `config.json`,
`waveforms.json` and `sfx_measured.json` into `<paths.videos>/<reel>/` (the waveforms come from
`scripts/make_waveforms.py`, which `new_board.py` calls). The board page itself is
`boards/sound-board/index.html`; it loads those files from `/videos/<reel>/<file>`. Open it at
`/editor/sound-board/?reel=<reel>` on the editor's board server. The client opens it inside the hub (board-server.md step 3); this address is the board's own page.

- `--cues cues.json` seeds proposed cues, a list of `{id, beat, short, why, time, candidates:[...]}`. Leave it
  out for an empty board the client fills.
- `--stops stops.json` seeds proposed music stops, `[{start_s, end_s, label}]`.
- `--bed <file>` presets a music bed (with explicit fade-in and fade-out).
- When the cut was transcribed (`work/cut/tx-cut.json`), the speech stretches go in `speech_spans`, so the board can
  tip when the closer doesn't land in silence.

## What the client gets

- **The locked picture** with frame-accurate transport and a cue-marker timeline.
- **Per cue:** a sound picker showing every file's measured duration and peak, hear (solo), audition (loops the
  picture around the cue so the landing is heard several times, not once), a level slider, keep or reject, move
  to the playhead, and add a copy elsewhere.
- **Suggest a sound here:** park the playhead on a moment that needs something; a new row appears at that time.
- **Music bed:** drag its waveform to slide which part of the track plays, set entry and exit, fade in and out.
  The voice waveform sits above it on the same time axis, so speech gaps are visible.
- **Music:** one line per track (hear its strongest part, title, mood, length, origin, Use); "Add a free track" /
  "Use my own track" set `music_request` so Claude walks the client through it after Send. Level is the music vs
  the voice (-18 suggested). "Carve around the voice" starts on at strength 0.8; its slider (0.25-1) appears
  while it is on. It lowers only the music's voice bands and lets them return through pauses. The preview
  follows the same voice curves when available. The dip under voice (4-12 dB, default 6) remains the fallback,
  and an own track needs the "I have the rights" tick.
- **Music stops:** a stop at the playhead, with cut-at and back-at times. The music fades out to silence by the
  cut, fades back in from the return (defaults 0.3 s and 0.5 s) and keeps running underneath, so it comes back
  mid-phrase.
- **Per cue end:** a length (hard cut) and a hard-cut or fade-out choice: a click should stop dead, a riser
  should breathe out.
- **Latency:** if every hit feels late by the same amount, that is the computer, not the spotting. Nudge until
  they sit right, then judge.
- Decisions survive a reload. Send writes `sound-selection.json`; undecided cues go in its `undecided` list and
  are never mixed.
- Send saves `bed.carve` as `{on, strength}`. Old selections without that key keep their original dip and
  re-bake unchanged. No voice, no usable bands, or a failed carve uses the dip and says so. Resolve receives
  the simpler dip as volume keyframes and a note that the voice carve is applied only in our render.
- **Beat-sync (off by default):** a checkbox on the music row, greyed out with "no steady beat found in this track"
  when the bed's `grid` is null. On, the track start (`offset_s`) snaps to its nearest beat whenever it changes,
  faint beat ticks show on the cue strip, and "Snap cues to the beat" moves only the cues within
  `min(period/8, 80 ms)` of a beat onto it. Turning it off moves nothing back. Send carries `bed.beat_sync`.
- **Peak offsets:** a sound with `peak_s` in its library row starts `peak_s` early, in the preview, the loop and
  the bake, so its hit lands on the marker; every sent cue carries `peak_s` (0 when unknown). Speech never moves.

## Things that matter

- **Levels start matched.** Each candidate's default level brings its measured peak to about -1 dBFS, so sounds
  are auditioned level-matched. A file peaking under -6 dBFS is flagged as a quiet master: mixing can't rescue
  it, it needs a louder copy first.
- **Nothing is trusted from a table.** Durations and peaks are probed, because library notes go stale and
  libraries are not level matched.
- **The board proposes; the client decides.** Seed more cues than should ship, so the client cuts rather than
  accepts.
- The board never touches the sound output itself. `sound-selection.json` is the ruling, and `mix.py` takes it
  from there.
