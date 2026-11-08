# Transcription contract

## Contents
- Engines
- Transcript guards (HF-5, hard rule)
- The edit map
- The backup's settings
- Batching is conditional
- Precision and batch size are NOT part of the contract
- Vocabulary is opt-in, per call, never a default
- Word timings are estimates — always
- A second trap: contiguous word times

## Engines

`transcribe_words.py` uses the engine the doctor's machine test picked (`engine` in the editor's state):

| Engine | When | Word times |
|---|---|---|
| Parakeet TDT 0.6B v2, int8 (`parakeet_local.py`) | the default, on the GPU or the CPU; English only | token starts; each end is the next word's start |
| faster-whisper `large-v3-turbo` (the backup) | where Parakeet can't install, or the workspace `language` isn't English | the settings table below |

The backup always prints its plain warning (it can drop a retake), so Parakeet's absence is never
silent. Either engine reads a 16 kHz mono copy of probe.json's `audio_stream`.

All workspaces share one install, which holds one engine. When this workspace's language needs the
other one (an English workspace after a Spanish one), the run first calls the editor doctor, which
re-picks for this workspace, says in its STATUS line that it is switching, and reinstalls.

## Transcript guards (HF-5, hard rule)

Every transcript gets them, the raw one and the re-transcribed cut:

1. **Silent tail.** The tail level follows the clip: its loudest point minus 12 dB, never louder than
   -35 dB (H-HF5-1); `silencedetect` uses this level for 0.6 s. Known limit (H-HF5-6): there is no
   noise-floor bound, so on a quiet clip with steady hiss an invented word after the speech can survive;
   it shows in the captions and can be fixed, while real speech is never dropped.
   When the clip ends in more than 0.8 s of
   silence, words that start more than 0.4 s after the sound ends are dropped: the engine invented
   them. `guards.tail_dropped` lists them.
2. **Near silence.** The chosen track's mean loudness (ffmpeg `volumedetect`) is stored as
   `mean_loudness_db` in `work/probe.json`; the sound pass's quiet-recording gate reuses it. Under
   -45 dB the run stops (exit 4) with a plain message that names the file's other audio tracks.
3. **Untimed words.** A word with no time shares the span between its timed neighbours, and a word
   with no length ends where the next later word starts (`filled`).

## The edit map

`--edit-map work/edit_map.json` runs three steps on the same words and track:

- `align_words.py`: wav2vec2 forced alignment, a real start and end per word on a 20 ms grid.
- `vocal_truth.py`: the voiced sounds the engine left out, as `[vocal]` and `[breath]` events.
- `build_edit_map.py`: words, events and silence islands, validated before anything is written.

`parakeet_start` is the cut anchor; with the backup it holds the backup's start time.
`--report-md` on the last two writes a readable report, and refuses to overwrite any file that
isn't one of its own reports. Intel Macs skip alignment (no tested torch), so they get words but
no edit map.

## The backup's settings

The **model and mode are fixed. The runtime is not.** Any backend satisfying the table below
works — the bundled `transcribe_words.py`, another local library, an HTTP endpoint, a GPU box on
a tailnet.

| Setting | Value | Why |
|---|---|---|
| model | **`large-v3-turbo`** | Measured no worse than full `large-v3` on proper nouns, and **safer with a prompt** — `v3` + prompt dropped 219 characters of real speech in an A/B. |
| **VAD** | **ON — non-negotiable** | **Sequential mode hallucinates over silence**, inventing whole sentences (including foreign-language fragments) over trailing quiet. VAD is what suppresses it. This is the accuracy rule. |
| **batching** | **ON for raw footage · OFF for an already-cut file** | See "Batching is conditional" below. VAD is the part that is never optional; batching is a judgment call about how much silence the source carries. |
| `word_timestamps` | **ON — hard precondition** | This pipeline cuts on word edges. |
| `hotwords` / vocabulary | **OFF by default** | See below. |
| output | `{text, words: [{word, start, end}]}` | **Hard-fail if `words` is empty or absent.** |

The bundled backup implements this table, through the same command:

```bash
<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py" RAW.mp4 -o work/tx.json --probe work/probe.json
```

VAD and word timestamps are always on and cannot be turned off. Batching is `--batched N`,
off by default. There is no vocabulary option at all.

## Batching is conditional

The original rule said "batched + VAD, ON, non-negotiable" as one inseparable setting. **It is
two settings, and only VAD is unconditional.**

Measured on an approved cut — same model (`large-v3-turbo`), same file, same card, **207 tokens
both ways**:

| Decode path | The trigger word at 58.10s |
|---|---|
| sequential + VAD | correct ✅ |
| batched-8 + VAD | a different real word ❌ |

One word in 207, and it was the word the entire call to action depended on. Chat-automation
triggers are exact-match, so a corrupted trigger simply never fires — and no text-level check
would have caught it, because the wrong word is a real word in a grammatical sentence.

**Batching is the variable, not VAD.** Batched mode cannot run with `vad_filter=False` at all
(`RuntimeError: No clip timestamps found`), so VAD was on in both arms.

**When to use which:**

- **Raw multi-take footage → batched.** Long trailing silences are exactly where sequential
  invents sentences. The original rule holds and is why it was written.
- **An already-cut file → sequential.** A finished cut carries a few seconds of silence total
  with every gap capped, so there is almost nothing for sequential to hallucinate over, while
  batching's accuracy cost is fully realised.

**The condition generalises; the setting does not.** Ask how much silence the source carries
before choosing, and keep VAD on either way.

## Precision and batch size are NOT part of the contract

Do **not** copy `compute_type` or `batch_size` from another machine's configuration. Those are
memory compromises, not quality settings.

A reference box runs `int8_float16` with `batch_size 4` because it has **8 GB of unified memory
and 535 MB of measured headroom at peak**. Inheriting that would ship a needlessly quantized
model to a machine with room to spare. **Where memory allows, `float16` is more accurate than
`int8_float16`.** Derive both from the hardware actually running.

Keep scratch and work folders off synced folders (OneDrive, Dropbox, iCloud): the sync app locks and
re-uploads the large WAVs and renders while they are written. Use `pathlib` for paths so the same code runs
on Windows and macOS.

## Vocabulary is opt-in, per call, never a default

A vocabulary prompt can make Whisper **silently delete real speech**. Measured: 946 characters
became **773** — about 28 words gone, with no error and no gap in the output. What vanished were
the speaker's *retakes*; Whisper suppresses apparent repetition loops, and a genuine re-recorded
take looks exactly like one.

**A wrong name is visible and fixable. Missing speech is neither.**

Raw multi-take footage — which is most source material for this skill — is precisely the case
where it must stay off. This is why the bundled transcriber ships no vocabulary option. For
unattended pipelines, fix names with a post-transcription find-and-replace map instead.

If you do use it on another backend:
- **Write it as a punctuated prose sentence, never a bare comma list.** Whisper imitates the style
  of its prompt: a bare comma list produces output with no capitals and no punctuation at all.
  Correct: `"This is a tutorial about Acme, Widgets, and n8n."`
- **Compare the character count against a no-vocabulary run.** A large drop means speech was
  eaten, not that the transcript got tidier.

## Word timings are estimates — always

Even with every setting above correct, word boundaries are approximations. Measured on the
reference build, with `large-v3-turbo`, batched, VAD on, no vocabulary:

| Boundary | ASR said | Waveform | Error |
|---|--:|--:|--:|
| end of a sentence-final word | 176.18 | 176.72 | **0.54s** |
| start of a stressed word | 122.04 | 122.53 | 0.49s |
| end of an abbreviation | 172.02 | 172.30 | 0.28s |
| end of a clause-final word | 67.68 | 67.85 | 0.17s |

**Word ends run early.** That 0.54s error would have amputated the punchline of the best line in
the reel, and no text-level check could have seen it.

This is a property of the model, not a misconfiguration. It is why Stage 3's waveform
verification is a hard gate. **Never skip it on the grounds that transcription is configured
correctly** — it was.

## A second trap: contiguous word times

ASR word timings are **contiguous** — word N ends exactly where word N+1 starts, even across a
real pause. They therefore cannot be used to locate silence, and must not be intersected with an
acoustic measurement. Attempting it removed 0.41s of a 9.7s target. Use the envelope for silence;
use word times only for *identity* and *ordering*.
