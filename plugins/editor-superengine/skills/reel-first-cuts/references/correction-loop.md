# The correction loop (Stage 9)

The human names a gap in plain language. You find it, measure it, and fix the
**mechanism** — not the instance.

**This stage exists because it is where the real defects were found.** In the reference build the
automated gates passed on every single one.

## The loop

### 1. Locate — never guess
Map the quoted phrase → source time → current output time. Speed ramps and prior deletions both
move things; a beat table is a plan, not a measurement.

### 2. Measure — print the envelope around it
State what is actually there before proposing anything. Twice in the reference build the audio
disproved the diagnosis that seemed obvious from the segment list.

### 3. Diagnose BEFORE fixing
Four similar-sounding complaints had **four different causes**:

| Complaint | Actual cause |
|---|---|
| "orphan after the last word of a line" | orphan guard's fragment floor was 50ms — a word was stranded |
| "gap before the next line is too long" | the guard **over-reverting** and restoring the whole gap |
| "the pause after that line drags" | a single −28.9 dB sample tripping a peak-based speech test |
| (found alongside) 0.575s dead lead-in | same over-revert, invisible to any transcript diff |

A fix aimed at the symptom would have addressed one and left three.

### 4. Fix the mechanism, not the instance
A hardcoded exception for one timestamp is a bug waiting to recur, and it will not survive the
next reel. Each mechanism fix in the reference build **caught siblings the human had not yet
noticed** — the absorb/revert change fixed two named gaps plus the lead-in nobody had mentioned.

### 5. Re-verify BOTH directions
The named defect is gone **and** nothing else regressed. Re-run every gate, not just the one that
found the complaint: the boundary audit in Stage 3, the gap plan in Stage 4, and the silence
budget in Stage 7b.

⚠️ **Every fix in this area broke something else on the first attempt:**
- The orphan-guard fix *caused* three further defects by reverting whole gaps.
- Absorbing silent runts fixed two of those and left one standing, because a breath read as
  speech.
- The sustained-run test that fixed the breath raised the loudest deleted window from −52 dB to
  −28.9 dB — a real trade that had to be stated, not hidden.

## What to say when handing it back

Report the **trade**, not just the win. If a fix moved a threshold, say what it now permits. The
−28.9 dB figure above is a breath being deliberately deleted; that is fine, and it is still worth
saying out loud, because the next person reading a "loudest deletion" line will otherwise assume
the floor held.

## Calibrating the human's ear

Hand over `work/listen.txt` with the review page. It names, from the run's own decisions:
- every gap deliberately left above cap
- every runt absorbed, and every gap restored because a runt held speech
- any deletion that reached above the speech floor
- every protected beat, and whether the timing still lands
- the first half second

**Aim the ear. Do not ask it to wander.**

## When the human is right and the measurement disagrees

They were right every time in the reference build. If the envelope says a gap is within cap and
they say it drags, the **cap is wrong for that position**, not the ear. Beat-change joins are the
usual culprit: technically in-spec at 320ms and still too slow at a hard pivot.
