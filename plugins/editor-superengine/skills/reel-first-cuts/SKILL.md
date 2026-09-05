---
name: editor-superengine:reel-first-cuts
description: Turn a raw talking-head recording into a finished first cut — line selection, a waveform-verified EDL, gap tightening, ear-driven gap corrections, and a speed ramp — in one build pass. Use whenever someone has raw camera footage plus an approved script and wants the spoken edit assembled, on asks like "cut this reel", "build the A-roll", "tighten the gaps", "the pause after X is too long", "make it 1.15x", "why does this cut sound clipped". Also use when a cut already exists and the complaint is audible — an orphaned word, a gap that drags, a clipped consonant. Not for graphics, captions, layout or compositing; those come after picture lock.
---

# Reel First Cuts

Raw recording → finished spoken cut. One build pass, **three human rulings**, one ear pass.

## Definition of done

A rendered cut where:
- every cut boundary sits in verified silence, not an ASR estimate
- no deletion contains sustained speech
- no segment is a stranded fragment
- **the whole cut is inside its silence budget** (Stage 7b) — every other check is local, this one is the sum
- the human has heard it and signed off

## The stages, in order

| # | Stage | Script |
|---|---|---|
| 0 | Probe & calibrate | `probe.py` |
| 1 | Transcribe (word timestamps) | `transcribe_words.py` |
| 2 | ⛔ Line selection — RULING | — |
| 3 | ⛔ EDL + waveform verification — HARD FAIL | — |
| 4 | Tighten gaps | `gaps.py` |
| 5 | ⛔ Speed — RULING | — |
| 6 | Render once, from the raw | `render.py` |
| 7 | Verify (round-trip) | `transcribe_words.py` |
| 7b | Silence budget — HARD FAIL | `silence_budget.py` |
| 8 | ⛔ Ear pass — RULING | — |
| 9 | Gap corrections | — |

Every script lives at `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/`. Three ⛔ stages
stop for a human. **Do not reorder the stages** — the order puts the strongest check first, and
this job took eight passes by hand because each check was weaker than the one run next.

## The governing rule

**Calibrate from the file. Never ship a magic number.**

Where a threshold decides something *audible*, the script proposes and **you dispose** — with the
measured evidence in front of you. Eleven hardcoded constants were wrong in the reference build,
and every one produced confident, plausible, wrong output. See
`${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/why-constants-fail.md` before you are
tempted to hardcode one.

**Corollary:** when a script and your own measurement disagree, measure again — do not adjust the
script until you know which is wrong.

**Second corollary — run this skill, do not re-derive it.** The reference build hand-rolled the
whole pipeline from scratch: word timings, segment construction, boundary refinement, gap capping,
render, round-trip. It arrived empirically at a **150ms** gap cap, which is `gaps.py`'s own
`--internal`/`--join` default. The cost of not reaching for the skill was shipping its
already-known-bad first version to the human, twice. The scripts exist; start there.

## Stages

### 0 · Probe & calibrate — trust nothing
```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/probe.py RAW.mp4 -o work/
```
Establishes, **by measurement**:
- **True frame rate.** Read `avg_frame_rate` and a PTS-delta histogram over the whole file.
  **Never `r_frame_rate`** — it is a container header and it lies (declared 60, was 22.31 VFR).
- **The RMS envelope of the source audio**, extracted once. This is the single measurement
  surface for every later stage. Nothing downstream re-derives it, and **nothing requires a
  render to exist.**
- **Per-file thresholds**: noise floor, speech floor, and the breath/syllable duration split.
- **The duplicate-frame table** for each candidate output rate.
- ffmpeg version → `-fps_mode` (≥5.1) or `-vsync`.

⚠️ On VFR source, speeding up *reduces* duplicate frames — 25.9% at 1.00x vs 14.9% at 1.15x in the
reference build. **That is source-specific.** Report the table; never assert the rule.

### 1 · Transcribe — a contract, not a vendor
```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/transcribe_words.py RAW.mp4 -o work/tx.json
```
That is the default route: it implements the contract, hard-fails on an empty word list, and has
no vocabulary option. Any other backend is fine if it satisfies
`${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/transcription-contract.md`.

Fixed: **`large-v3-turbo`, VAD on, `word_timestamps` on, vocabulary off.** **Batching is
conditional:** on for raw multi-take footage (`--batched 8`), **off for an already-cut file**,
where batched-8 misheard a trigger word as a different real word. Precision and batch size come
from *this* machine. **Hard-fail if word timings are missing** — sentence precision is what
produces the half-second errors this pipeline exists to catch.

### 2 · ⛔ Line selection — RULING
Score every trim candidate and present a ranked table. **Never auto-apply.**
Score by **direction**, not information content: a line carrying zero information but pointing
*forward* opens a loop the viewer stays for; a line restating something already said closes one.
**Only backward-facing lines are free cuts.** In the reference build, two of four proposed
"restatement" cuts were the reel's strongest rehooks.

### 3 · ⛔ EDL + waveform verification — HARD FAIL
Build the EDL (pads, neighbour clamp, merge rule), then audit **every** boundary against the
envelope. Anything above the measured speech floor is **re-derived**, not shipped.
- Mid-sentence trims clamp against the next **word**, not the next sentence.
- Assert zero source overlaps.

**This gate is not optional even when transcription is configured perfectly.** Word timings are
estimates by nature; the reference build measured errors up to **0.54s** with every setting
correct — enough to amputate the punchline of the best line in the reel.

### 4 · Tighten gaps — in source coordinates, no render
```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/gaps.py work/ --plan
```
Per-function caps (internal / join / beat-join / lead / tail) plus a protect list.
- Every deletion **proven** free of *sustained* speech — a single loud 10ms window at a splice is
  a decay tail, not a word.
- **Orphan guard on post-split segments**: a silent runt is *absorbed*; a speech-bearing runt
  *reverts* the deletion. Checking before the cut-boundary split misses the fragment entirely.
- Every borderline decision is surfaced for the agent to rule on, not silently resolved.

### 5 · ⛔ Speed — RULING
Present runtime **and measured duplicate-frame %** per candidate. `atempo` preserves pitch.

### 6 · Render once, from the raw
```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/render.py work/ RAW.mp4 --speed 1.15 --master --scrub
```
Single `filter_complex`: `trim` + `atrim` + `concat` + `setpts`/`atempo`.
- Master: CRF 14 `slow`, **`-g <fps>`**.
- Scrub copy: 1080p CRF 20, `-g <fps/2>`.

**Dense GOP is not optional on anything a human will scrub.** `preset slow` defaults to a
250-frame GOP; seeks measured 678–1527ms and dragging the playhead felt dead.

Never build from an intermediate. Grade, speed and captions fold into one pass. See rule 2 of
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md`.

### 7 · Verify
Round-trip transcribe every segment. **A transcript diff flags a DIFFERENCE, not a DEFECT** —
adjudicate acoustically before calling anything broken. Quiet function words drop out of ASR when
surrounding pauses shorten; that is a pacing artifact. In the reference build this false alarm
nearly triggered two "fixes" to audio that was never damaged.

⚠️ **And it fails the other way too — a clean round-trip is not a clean cut.** In the reference
build every word round-tripped perfectly (204 in, 204 out) on a cut that was slicing word tails at
**−16 dB, full speech level, on 7 of 13 boundaries.** ASR reconstructs a word from partial
phonemes, so a sheared tail is exactly what it papers over. **The waveform is the instrument for
boundary damage; the transcript is only the instrument for missing content.** Never let a passing
round-trip stand in for Stage 3.

Then emit the **targeted listening checklist** (Stage 8 depends on it).

### 7b · Silence budget — HARD FAIL
```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/silence_budget.py CUT.mp4 --words work/tx.json
```
Measures what fraction of the **rendered** cut is nobody talking. Default budget **12%**; exits 1
when over, and ranks the offending gaps by length with the words either side.

**Every other gate in this skill is local** — is this boundary clean, is this gap under its cap, is
this fragment an orphan. A cut can pass all of them and still drag, because the defect is the
**sum**. The reference build shipped to the human at 70.85s with **16.63s of silence, 23% of the
reel** — and every boundary gate was green. He caught it by ear in one pass, named three gaps, and
the real finding was systemic: 48 gaps, none individually fatal.

Re-running the gate on that rejected cut reports **23%, and ranks his three complaints in his own
order of severity.** It would have caught it before he ever saw it.

⚠️ `silencedetect` logs at **info**. Passing `-v error` makes the detector output vanish and the
cut reads as having no silence at all.

**Within budget is not approval.** It says nothing about whether any single gap is *right*, and
nothing about whether the cut sounds good. Stage 8 still runs.

### 8 · ⛔ Ear pass — RULING
Hand over the review page **and the checklist**, and state plainly what the gates cannot see.
The preview rules apply:
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/preview-before-render.md`.

**Every automated gate passed on all four defects the human caught in the reference build.** This
stage is not a formality.

### 9 · Gap corrections — the ear-driven loop
Full protocol:
`${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/correction-loop.md`.

The human names a gap in plain language ("the pause after that line drags", "there's an orphan
word after the second beat"). For each:

1. **Locate it.** Map the phrase → source time → current output time. Never guess from the beat
   table.
2. **Measure it.** Print the envelope around it. State what is actually there.
3. **Diagnose before fixing.** In the reference build the four complaints had *four different*
   causes: an orphan guard stranding a word; the same guard over-reverting and restoring a full
   gap; a peak test tripping on a single sample; and a breath being read as speech.
4. **Fix the mechanism, not the instance.** A hardcoded exception for one timestamp is a bug
   waiting to recur. Each of those four fixes generalised and caught siblings the human had not
   yet noticed.
5. **Re-verify both directions** — the gap is fixed *and* nothing else regressed. Every fix in the
   reference build broke something else on the first attempt.

Loop until the human signs off.

## What this skill will not decide

- **Which lines to cut** — scoring is mechanical, the ruling is not.
- **Runtime and speed.**
- **Protected beats.** Comedic timing is unmarked in audio. Propose candidates from the script,
  then ask.
- **Whether it sounds right.**

## Portability

Nothing here is machine-specific. Do not inherit another box's `compute_type`, `batch_size`,
paths, or interpreter. Detect `python3`/`python`, check the ffmpeg version, use `pathlib`, keep
scratch off synced folders, and never print non-ASCII to a Windows console.
