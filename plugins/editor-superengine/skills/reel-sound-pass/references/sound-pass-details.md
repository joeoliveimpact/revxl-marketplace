# Sound pass: stage detail, checks and why

Picture-locked reel in, finished sound out. The mix is the client's; the machinery only preserves it. Every
stage below exists because a looser version once shipped a reel with its sound effects missing or its music
re-levelled behind the client's back.

Packages: the scripts need numpy and ffmpeg, which the editor install puts in the editor's own Python (run
`editor-superengine:editor-doctor` if they are missing; it does the equivalent of `pip install numpy`). `runtime`,
`board_sync`, `cost_ask` and `win_encoding` are the plugin's own modules, not pip packages.

## The governing rules

1. **Sound is finished after picture lock.** Cue times are spotted against the locked picture. If the picture
   changes, the cue list is stale: open the board again.
2. **A ratio the client set by ear is frozen.** Nothing re-levels it: no leveler on the mix, no ducking except the speech dip the
   client set on the board, no "background/foreground"
   processing. Auphonic's multitrack mode always re-levels each track to its own targets
   (a quiet bed came back about 12 dB louder, a hot one about 20 dB quieter) and no setting turns that off, so
   board-mixed tracks never go to multitrack.
3. **The sound goes onto the picture last.** Anything that replaces the sound after the effects are mixed in
   deletes them. Every check runs on the delivered file, never an in-between one.
4. **Measure the file, never trust a table.** Sound libraries are not level matched and written duration tables
   go stale. Every sound is probed when the board is built.

## Stages (what `mix.py` runs)

1. **Quiet gate.** The recording's average loudness, as the transcription step measured it
   (`work/probe.json` `mean_loudness_db`, or measured the same way when it's missing). Under -45 dB the mix
   stops and nothing is written: the wrong microphone was almost certainly recording.
2. **Stems (`bake.py`).** From the board's Send, baked exactly as the board played them: voice, sound effects
   and music, float 48 kHz stereo, one length (the picture's), every sound placed to the sample at the
   picture's real frame rate. Gains, length caps and fades come straight from the Send, and so do music stops
   (the music is silent inside each stop; its fade-out ends where the stop starts and its fade-in starts where
   the stop ends, while the track keeps running underneath). Float overs are not clamped; the limiter handles
   peaks. Each cue's file starts `peak_s` (where its hit lands) before the cue's time, so the hit lands on the
   time; a start before 0 trims the file's head instead. With beat-sync on, the music's track start snaps to a
   beat and steps back whole bars until the track lasts the reel; the speech cuts never move. Checks: the sum is
   exactly voice + effects + music; the effects track is exactly its cues; every cue's
   own sound is present in its window; the voice is bit-exact to the picture's sound; the music is silent in
   every stop. Each cue is also written as its own clip with a `placement.json` (frame, lane), for an editor
   that places clips on frames. Without a Send (or a library) the stems are voice only.
3. **Voice clean-up, on the voice track only.** Free: a low cut at 80 Hz and light compression. Auphonic
   (the client's choice, paid): one singletrack production on the voice track, never the summed mix, with
   leveler, -14 LUFS loudness, -1 dB max peak, dynamic denoise and studio-voice filtering, WAV out. Its result
   is lined up with the original to the millisecond (more than 2 ms left over: nothing is replaced).
4. **Ratio-keeping sum.** One static gain brings the cleaned voice back to the original voice track's
   integrated loudness, then voice + effects + music are summed at unity. The board's ratio holds by
   construction. A dead-silent hole (50 ms or more of digital silence) stops the mix here.
5. **Master (`master_audio.py`).** One static gain to -14 LUFS integrated, measured after the limiter, then
   ffmpeg's `alimiter` with `level=disabled` (otherwise it auto-levels to 0 dB) and `latency=enabled` (otherwise
   the sound shifts about 5 ms against the picture). The limiter caps the sample peak, not the true peak, so its
   threshold is swept until the measured true peak is at or under -1.0 dBTP.
6. **Onto the picture, last.** The picture stream is copied, never re-encoded; the sound is stereo AAC at
   192 kbps. Nothing is truncated and nothing is looped.
7. **Delivery gate (F-4).** On the delivered file: stereo (a mono file plays about 3 dB quiet on phones, so it
   is refused), -14 LUFS within 0.5, true peak at or under -1.0 dBTP, and the picture stream's MD5 identical to
   the locked picture's. Outside the window, one corrective static gain and one more pass of 5-7; still
   outside, it stops with the numbers.
8. **Cue check (`mix_check.py`).** When there are cues: each track's level is solved from the delivered file
   by least squares, with the PROCESSED voice as the control (the raw voice would false-fail, because a
   clean-up changes the quiet stretches by tens of dB). Every cue must still be there (its own sound, with
   everything else taken away, correlates at 0.9 or better), and the music-to-voice ratio, solved again in
   half-second windows where the voice speaks over audible music, must spread less than 1 dB (nothing dynamic
   touched it). Everything goes in `sound/mix-report.json`.

## Room tone

Any gap the sound pass inserts (a voice track shorter than the picture, the few milliseconds an alignment adds)
is filled with the recording's own room tone: its quietest stretch of at least 0.4 s that isn't digital silence,
looped with short crossfades. Never generated silence and never zero padding; a dead-silent hole sounds like a
dropout on a phone.

## The measured alternative (settled, don't re-test)

Auphonic singletrack on the summed mix, with its "keep music" studio-voice option, avoids the multitrack
disaster (the bed moved under 1 dB on average and transients survived), because it hears the whole mix as speech
and can only move everything together. But its adaptive leveler lets the music-to-voice ratio wander 2-3 dB from
window to window, where the split chain above holds it to hundredths of a dB. "Keep music" names the noise
remover's model, not any level protection. The split chain stays the house path.

Format physics, on every path: a hit mixed far over the speech (around +24 dB) loses about 11 dB of prominence
in any -14 LUFS / -1 dBTP master. If a hit must slam harder, the lever is its level on the board relative to the
mix, not the mastering.

Open item: studio-voice processing may shift the voice by about 10 ms. That is unconfirmed and inside the
broadcast tolerance for sound running late (45 ms); the alignment step measures and corrects it anyway.

## Listening

A passing check table is not approval. Hand the client a short list to listen for: every place the limiter works
hardest (they are all cue transients; the hottest hit takes the most), the risers, the music stops, the closer.
The client says ship, or names the moment; fix the cause, then mix again.
