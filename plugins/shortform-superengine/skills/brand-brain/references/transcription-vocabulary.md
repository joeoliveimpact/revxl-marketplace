# Transcription vocabulary — feeding brand-brain into Whisper

Read this before transcribing anything where brand, product, or person names matter.

## The problem

Whisper has never seen your client's product names. When it hits one it substitutes
the nearest common-English phrase, confidently and silently:

| Said | Transcribed |
|---|---|
| Higgsfield | "Higgs field", "Hicksfield" |
| Kling 01 | "cling a one" |
| Claude | "claw", "clod" |
| Promptception | "promptception" (lowercased) |

Measured on 48 minutes of real audio: **the correct brand name appeared 3 times and
a mangled version 18 times** — wrong 86% of the time it was spoken.

This is not cosmetic. In one case a reviewer read `"uh cling a one"` as the speaker
stumbling and marked **9.4 seconds for deletion**. The speaker had said "Kling 01"
perfectly. A transcription error became an editorial decision about their performance.

## The fix: brand-brain already knows the names

Both Whisper (via `initial_prompt`/`hotwords`) and Groq (via `prompt`) accept a short
text hint that biases decoding toward spellings you supply. The names to put in it
are already mined and stored:

- `~/.claude/revxl/<brand>/voc/business-config.md` — entity, company, and offer names
  (this is where a spelling like "BizFixx — double-Z, double-X" lives)
- `~/.claude/revxl/<brand>/voc/voice-guide.md` — the `## Vocabulary` section: coined
  terms and signature phrases

Do not build a second glossary. Read these.

## Building the prompt

Pull the proper nouns and coined terms, then write them into **one natural sentence**:

```
"This is a video about Engine For Impact, BizFixx, Higgsfield, Promptception, and n8n."
```

Keep it to roughly 5–15 terms. Groq caps the field at **224 tokens**, and a long list
starts steering the transcript toward its own subject matter.

Spell each term exactly as you want it to appear — that spelling is what the model is
biased toward.

## Two rules that decide whether this helps or hurts

**1. Write a punctuated sentence, never a bare comma list.**

```
GOOD:  "This is a video about Higgsfield, Promptception, and n8n."
BAD:   "Higgsfield, Promptception, n8n"
```

Whisper imitates the *style* of its prompt. A prompt with no capitalization and no
sentence punctuation teaches it to emit a transcript with none either — across the
whole file, including audio unrelated to those words. Verified by controlled A/B on
identical audio:

| Prompt form | Output |
|---|---|
| bare list | `and so my fellow americans ask not what your country can do for you` |
| prose sentence | `And so, my fellow Americans, ask not what your country can do for you,` |

**2. A prompt can cause real speech to be dropped. Check the length.**

Whisper suppresses what looks like a repetition loop, and a speaker's genuine retakes
look exactly like one. A vocabulary prompt makes the decoder confident enough to
discard them.

Measured across four clips on Groq `whisper-large-v3-turbo`: three gained text while
fixing every name; one lost 93 characters, part of which was a twice-spoken phrase
collapsed into one.

So: **compare the character count against a run with no prompt.** A large drop means
speech was eaten, not that the transcript got tidier. This matters most on raw
multi-take footage, where a dropped line goes unnoticed.

If the transcript feeds a pipeline unattended, prefer transcribing **without** a
prompt and correcting names afterwards with a find-and-replace map built from the
same brand-brain terms. That cannot lose audio. Mind word boundaries — replacing a
short token like `claw` blindly will corrupt legitimate uses.

## Model choice

On Groq, prefer **`whisper-large-v3-turbo`**. Measured against full `whisper-large-v3`
on the same audio: turbo was no worse on proper nouns, is roughly 3× cheaper, and lost
no speech with a prompt where full v3 dropped 219 characters.

Groq exposes only `file`/`url`, `model`, `language`, `prompt`, `response_format`,
`temperature`, and `timestamp_granularities[]`. There are **no decoding controls** —
no VAD, no repetition-suppression threshold. The behaviour above can be triggered
there but not tuned, which is why the length check is the only safeguard.
