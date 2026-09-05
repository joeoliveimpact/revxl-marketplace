# Why constants fail — read before hardcoding a threshold

Eleven hardcoded constants were wrong in the reference build. **Every one produced confident,
plausible, wrong output.** None threw an error. Most were caught only because a human listened.

| Constant | What it was | Why it was wrong |
|---|---|---|
| `join = 0.15` | uniform gap inserted at every cut | 9 frames of black per join, +3.45s runtime, and it was *never* right at any join |
| out-pad clamp | clamped to the next **sentence** | does nothing to protect a mid-sentence trim from the next **word**; cut 0.20s into the following word |
| `noise = -42dB` | silence detector floor | consonant onsets sit at −35..−45 dB. Ate a /k/ onset, an /s/ onset, and a whole unstressed function phrase |
| word-shield margins | 120/220ms, then 30/70, 40/90, 50/110 | wrong **data source**, not wrong number — ASR word times are contiguous, so the shield covered whole spans. Three sweeps landed within 0.08s of each other |
| `SLIVER = 0.050` | minimum kept fragment | let a 0.235s orphaned word through |
| island check on the output timeline | orphan guard scope | the fragment only exists *after* the cut-boundary split; on the output timeline the keep looked long enough |
| `peak()` | speech test | reverted a whole deletion on **one** −28.9 dB sample — a splice decay tail, not a word |
| `SPEECH_RUN = 3` | 30ms sustained-speech test | read a 40ms **breath** as speech and restored a 0.678s gap |
| `-r 60` | output frame rate | taken from a container header that lied; invented 3351 duplicate frames |
| `preset slow` default GOP | 250 frames | 4.41s between keyframes; seeks took 678–1527ms and scrubbing felt dead |
| `EPS = 1e-6` | boundary comparison | a time exactly on a cut boundary resolved into the neighbouring cut, mapping a segment across a deleted gap |

## The pattern

Three distinct failure shapes, and they need different responses:

1. **The number was tuned on the wrong quantity.** (`-42dB`, `SPEECH_RUN=3`, `peak()`)
   → Calibrate from the file, and test the *right* property. A breath and a syllable differ in
   **duration**, not level. A splice tail and a word differ in **persistence**, not peak.

2. **The number was fine; the data source was wrong.** (word-shield margins)
   → Sweeping a parameter that lands in the same place three times means **stop sweeping**. The
   input is wrong, not the knob.

3. **The number encoded an assumption about structure.** (`SLIVER`, island scope, `EPS`, the
   sentence clamp) → These are not thresholds at all; they are unstated beliefs about how the
   timeline is shaped. Write the belief down and check it directly.

## The rule

**Calibrate from the file; never ship a magic number.** Where a threshold decides something
audible, the script proposes and the agent disposes — with measured evidence in front of it.

And when a script disagrees with your own measurement: **measure again before touching the
script.** Two of the eleven were "fixed" in the wrong direction first, because the script was
trusted over the waveform.

## The check that lies

A **round-trip transcript diff flags a DIFFERENCE, not a DEFECT.** Whisper drops quiet function
words when surrounding pauses shorten — a pacing artifact, not a clip. The decisive test is
acoustic: compare speech-time above the floor in both versions. In the reference build the
tightened file carried **more** speech than the original in the same window (2.320s vs 2.120s),
proving nothing had been removed — after two near-misses spent "fixing" it.
