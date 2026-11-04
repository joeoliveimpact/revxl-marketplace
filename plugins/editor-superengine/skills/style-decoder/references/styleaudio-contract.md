# styleaudio contract — style-decoder audio layer

> Companion to `scripts/styleaudio.py`. Measured audio facts -> `audio.json`. Every
> derived field carries `method`: these are labelled heuristics, not truth. Nothing
> here listens to the audio; it measures levels.

- **Transcript is optional.** `sources/<src-id>/transcript.json` in either word shape:
  `{"words":[{startTimeMs, endTimeMs}]}` or the reel-first-cuts shape
  `{"words":[{start, end}]}` (seconds). Without one, `speech.words` and
  `music.present` are `"UNKNOWN"` with a note, and nothing claims to have heard
  anything.
- **Loudness**: EBU R128 momentary timeline (1 s samples kept) + integrated LUFS (the
  LAST `I:` line; early ones are integration warm-up).
- **Music presence**: energy floor during speech gaps, including lead-in and outro
  tails (fast talkers leave no mid-speech gaps). No gaps ≥ 0.4 s → `UNKNOWN`. A high
  speaking ratio makes this UNKNOWN by construction; that is the script being honest.
- **Bed delta**: average momentary LUFS in gaps minus during speech. A crude ducking
  signal, not a ducking measurement.
- **SFX transients**: momentary jumps ≥ 6 LU within 300 ms, timestamps only.
  Candidates for Claude to correlate with cuts and payoff words.

## Reading transients correctly

A jump detector fires on a sound's **peak**, not its onset. A slow whoosh that ramps
into a cut registers AT the cut, not 0.5–1.0 s earlier where the ramp begins. **Do
not conclude "SFX lands on the cut" from that alignment**: it is equally consistent
with "riser leads into the cut", and only a person listening can separate them.
Record the measurement as *corroboration* of the person's call, never as the call.

## What stays HUMAN-INPUT

Music genre/feel/BPM and SFX character (whoosh vs pop vs click). The spec's
`audio.music.character` and `audio.sfx.character` are filled by the person at the
review gate (one line each), or marked `n/a`.
