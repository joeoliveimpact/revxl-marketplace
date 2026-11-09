#!/usr/bin/env python3
"""Per-clip silent-tail guard: <scratch> [--case NAME]. Stdlib, synthetic WAVs only.

Uses the editor's installed ffmpeg via transcribe_words.ff. Each case is under
150 s; no transcriber, model, real take or network is needed.
"""
import argparse
import importlib.util
import math
import random
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path
from unittest.mock import patch

SCRIPT = (Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/"
          "reel-first-cuts/scripts/transcribe_words.py")
spec = importlib.util.spec_from_file_location("transcribe_words", SCRIPT)
tw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tw)
SR = 16000


def fixture(scratch, name, duration, speech, floor_db=-65, noise=False):
    """Checker B5 waveform: seed 1, RMS tones/hiss, clipped 16-bit samples.

    A None floor makes exact-zero pauses for the gated-audio case.
    """
    rng = random.Random(1)
    samples = []
    for i in range(round(duration * SR)):
        t = i / SR
        amplitude = 0 if floor_db is None else 10 ** (floor_db / 20)
        value = (rng.gauss(0, amplitude) if noise else
                 math.sqrt(2) * amplitude * math.sin(2 * math.pi * 83 * t))
        for start, end, db in speech:
            if start <= t < end:
                value += math.sqrt(2) * 10 ** (db / 20) * math.sin(2 * math.pi * 220 * t)
        value = max(-1.0, min(1.0, value))
        samples.append(round(value * 32767))
    wav = scratch / (name + ".wav")
    with wave.open(str(wav), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SR)
        out.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return wav


def case_quiet_keeps_tail(scratch):
    # The last soft sentence is exactly 1.5 s long. The whole clip still clears
    # the separate -45 dB quiet-recording gate, so the tail guard is reachable.
    wav = fixture(scratch, "quiet", 7.0, [(0.25, 3.75, -42), (4.0, 5.5, -44)])
    assert -45 < tw.mean_loudness(wav) < -42
    guards = {}
    end = tw.sound_end(wav, 7.0, guards)
    assert end is not None and 5.49 <= end <= 5.52, (end, guards)
    assert guards["tail_noise_db"] < -35, guards
    words = [{"word": "soft", "start": 4.2}, {"word": "sentence", "start": 5.2}]
    assert tw.trim_tail(words, end) == (words, [])
    # Run the same detector and trimmer with the old fixed level, not an
    # approximation of silencedetect: it incorrectly removes the soft sentence.
    with patch.object(tw, "tail_noise_db", return_value=-35):
        old = tw.sound_end(wav, 7.0)
    assert old is not None and old < 4.0, old
    assert tw.trim_tail(words, old) == ([], words)
    print("  quiet: end %.3f s, old end %.3f s, noise %.1f dB" %
          (end, old, guards["tail_noise_db"]))


def case_loud_drops_tail(scratch):
    wav = fixture(scratch, "loud", 5.75, [(0.25, 3.75, -18)])
    guards = {}
    end = tw.sound_end(wav, 5.75, guards)
    assert end is not None and 3.74 <= end <= 3.77, (end, guards)
    real = {"word": "speech", "start": 3.5}
    fake = {"word": "invented", "start": 4.5}
    assert tw.trim_tail([real, fake], end) == ([real], [fake])
    with patch.object(tw, "tail_noise_db", return_value=-35):
        old = tw.sound_end(wav, 5.75)
    assert old == end, (old, end)
    assert guards["tail_noise_db"] == -35, guards


def case_hiss_known_limit(scratch):
    # Known limit (hub ruling H-HF5-6): the tail level is min(-35 dB, clip peak - 12 dB) with no noise
    # floor, because a whole-clip floor could not tell quiet speech from hiss and cost real speech.
    # On a quiet clip with steady hiss an invented word after the speech can survive (it shows in the
    # captions and can be fixed; lost speech could not). This test records that behaviour on purpose.
    # ponytail: no floor bound; v0.3.0 lead B = measure the floor only in the stretch after the speech ends.
    wav = fixture(scratch, "hiss", 5.75, [(0.25, 3.75, -30)], floor_db=-50, noise=True)
    guards = {}
    end = tw.sound_end(wav, 5.75, guards)
    real = {"word": "speech", "start": 3.5}
    fake = {"word": "invented", "start": 4.5}
    assert -35 >= guards["tail_noise_db"] > -40, guards
    assert end is not None and end > 4.5, (end, guards)
    assert tw.trim_tail([real, fake], end) == ([real, fake], [])
    print("  hiss (known limit): end %.3f s, noise %.1f dB, invented word kept" % (end, guards["tail_noise_db"]))


def case_gated_keeps_tail(scratch):
    # A quiet gated clip (exact-zero pauses) keeps its soft last sentence.
    wav = fixture(scratch, "gated", 7.0, [(0.25, 3.75, -42), (4.0, 5.5, -44)], floor_db=None)
    assert -45 < tw.mean_loudness(wav) < -42
    guards = {}
    end = tw.sound_end(wav, 7.0, guards)
    assert end is not None and 5.49 <= end <= 5.52, (end, guards)
    words = [{"word": "soft", "start": 4.2}, {"word": "sentence", "start": 5.2}]
    assert tw.trim_tail(words, end) == (words, [])
    print("  gated: end %.3f s, noise %.1f dB" % (end, guards["tail_noise_db"]))


def case_sparse_gates_keep_words(scratch):
    """H-HF5-5: gated clips whose gaps are short AND rare keep every word (checker probes 4-6)."""
    cases = []
    for gap in (0.03, 0.05, 0.07, 0.09):
        for seg in (0.6, 1.2, 2.0):
            segs, t, i = [], 0.25, 0
            while t + seg <= 5.0:
                segs.append((t, t + seg, -42 if t + seg < 4.0 else -44))
                t += seg + gap
                i += 1
            cases.append(("gap%d-seg%d" % (gap * 1000, seg * 10), segs, 6.0))
    cases.append(("soft-2db", [(0.25, 3.0, -38), (3.05, 5.0, -40)], 6.0))
    for name, segs, duration in cases:
        wav = fixture(scratch, "sparse-" + name, duration, segs, floor_db=None)
        guards = {}
        end = tw.sound_end(wav, duration, guards)
        words = [{"word": "w%d" % n, "start": a + 0.05} for n, (a, _, _) in enumerate(segs)]
        words.append({"word": "last", "start": segs[-1][1] - 0.2})
        assert tw.trim_tail(words, end) == (words, []), (name, end, guards)
    print("  sparse gates: %d clips keep every word" % len(cases))


def case_never_louder(scratch):
    wav = fixture(scratch, "very-loud", 4.0, [(0.25, 2.0, -3.5)])
    guards = {}
    with patch.object(tw, "ff", wraps=tw.ff) as calls:
        end = tw.sound_end(wav, 4.0, guards)
    assert guards["tail_noise_db"] == -35, guards
    filters = [c.args[c.args.index("-af") + 1] for c in calls.call_args_list if "-af" in c.args]
    assert "silencedetect=noise=-35dB:d=0.6" in filters, filters
    assert end is not None and 1.99 <= end <= 2.02, end


def case_fallback(scratch):
    wav = fixture(scratch, "fallback", 4.0, [(0.25, 2.0, -18)])
    real_ff = tw.ff
    # Only the measurement fails; detection still runs through real ffmpeg.
    # Reject nonzero exits even if stderr contains a plausible peak, and reject
    # absent, malformed and nonfinite readings instead of treating them as quiet.
    failures = [subprocess.CompletedProcess([], 1, "", "max_volume: -50.0 dB"),
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "", "max_volume: ... dB"),
                subprocess.CompletedProcess([], 0, "", "max_volume: -inf dB"),
                OSError("measurement unavailable")]
    for failure in failures:
        def ff(tool, *args):
            if "volumedetect" in args:
                if isinstance(failure, Exception):
                    raise failure
                return failure
            return real_ff(tool, *args)

        guards = {}
        with patch.object(tw, "ff", side_effect=ff) as calls:
            end = tw.sound_end(wav, 4.0, guards)
        assert guards["tail_noise_db"] == -35, (failure, guards)
        filters = [c.args[c.args.index("-af") + 1] for c in calls.call_args_list if "-af" in c.args]
        assert "silencedetect=noise=-35dB:d=0.6" in filters, filters
        assert end is not None and 1.99 <= end <= 2.02, (failure, end)


CASES = {"quiet-keeps-tail": case_quiet_keeps_tail, "loud-drops-tail": case_loud_drops_tail,
         "gated-keeps-tail": case_gated_keeps_tail, "sparse-gates-keep-words": case_sparse_gates_keep_words,
         "hiss-known-limit": case_hiss_known_limit, "never-louder": case_never_louder, "fallback": case_fallback}


def main():
    tw.ensure_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch")
    parser.add_argument("--case", choices=list(CASES))
    args = parser.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name in [args.case] if args.case else CASES:
        started = time.monotonic()
        try:
            CASES[name](scratch)
            print("PASS %s (%.1f s)" % (name, time.monotonic() - started))
        except Exception as error:
            failures += 1
            print("FAIL %s: %s: %s" % (name, type(error).__name__, error))
    print("%d failed" % failures if failures else "all passed")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
