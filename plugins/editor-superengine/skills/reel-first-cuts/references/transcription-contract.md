# Transcription contract

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

The bundled transcriber implements this table:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py RAW.mp4 -o work/tx.json
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
