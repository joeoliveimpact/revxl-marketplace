#!/usr/bin/env python3
"""Whole-cut silence budget -- the aggregate gate.

Every other check in this skill is LOCAL: is this boundary clean, is this gap
under its cap, is this fragment an orphan. A cut can pass all of them and still
drag, because the defect is the SUM. The reference cut shipped at 70.85s with 16.63s of
silence -- 23% of the reel -- and every boundary gate was green. The human caught
it by ear in one pass and named three gaps; the real finding was systemic.

Run this on the RENDERED cut, before the ear pass. It answers one question the
per-gap caps cannot: how much of this reel is nobody talking.

    python silence_budget.py CUT.mp4 --probe work/probe.json
    python silence_budget.py CUT.mp4 --probe work/probe.json --budget 0.10 --words work/cut/tx-cut.json

The silence threshold is the file's own: probe.json's calibrated silence floor
(`calibration.gap_db`). With no probe.json, or none in it, it falls back to the
cut's own level: 22 dB under the 90th percentile of its 50 ms windows, never below
-55 dB (ported from Shorts Studio, MIT; see LICENSES/NOTICE). --noise overrides both.

Exit 0 = within budget, 1 = over, 2 = could not measure.

Notes
-----
* silencedetect logs at INFO. Do NOT pass `-v error` -- the detector output
  vanishes and the cut reads as having no silences at all.
* Label words come from a Whisper-style JSON (`words[] {word,start,end}`) of the
  CUT itself (work/cut/tx-cut.json), in cut time: the raw's transcript would name
  every gap with the wrong words. ASR
  word boundaries PAD over silence, so they are used only to name a gap, never
  to measure one. The waveform is the measurement.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import runtime as rt  # noqa: E402

SETUP = "The editor's setup isn't finished: its video tools are missing. Run the editor setup (editor-doctor), then try again."
FFMPEG = FFPROBE = None


def die(m):
    print("ERROR: %s" % m, file=sys.stderr)
    raise SystemExit(2)


def find_tools():
    """ffmpeg/ffprobe come from the editor's install (_shared/runtime.py), never PATH."""
    global FFMPEG, FFPROBE
    try:
        FFMPEG, FFPROBE = rt.tool("ffmpeg"), rt.tool("ffprobe")
    except (KeyError, OSError, ValueError):
        die(SETUP)
    if not (Path(FFMPEG).exists() and Path(FFPROBE).exists()):
        die(SETUP)


def run_silencedetect(path, noise_db, min_dur):
    cmd = [FFMPEG, '-i', path, '-af',
           'silencedetect=noise=%.2fdB:d=%.3f' % (noise_db, min_dur), '-f', 'null', '-']
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'replace')
    starts, ends = [], []
    for m in re.finditer(r'silence_(start|end):\s*(-?[0-9.]+)', out):
        (starts if m.group(1) == 'start' else ends).append(float(m.group(2)))
    return [(a, b) for a, b in zip(starts, ends) if b > a], out


def file_threshold(path, below=22.0, floor=-55.0, hop=800):
    """22 dB under the loud end of this file's speech, never below -55 dB."""
    p = subprocess.run([FFMPEG, '-v', 'error', '-i', path, '-map', '0:a:0', '-ac', '1',
                        '-ar', '16000', '-f', 's16le', '-'], stdout=subprocess.PIPE)
    a = array('h')
    a.frombytes(p.stdout[:len(p.stdout) // 2 * 2])
    db = sorted(20 * math.log10(math.sqrt(sum(x * x for x in a[k:k + hop]) / hop) / 32768 + 1e-12)
                for k in range(0, len(a) - hop + 1, hop))
    if not db:
        return None
    i = 0.9 * (len(db) - 1)        # 90th percentile, linear between neighbours
    lo = int(i)
    p90 = db[lo] + (db[min(lo + 1, len(db) - 1)] - db[lo]) * (i - lo)
    return max(p90 - below, floor)


def duration(path):
    p = subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', path], stdout=subprocess.PIPE)
    try:
        return float(p.stdout.decode().strip())
    except ValueError:
        return 0.0


def load_words(path):
    if not path or not os.path.exists(path):
        return []
    d = json.load(open(path, encoding='utf-8'))
    w = d.get('words') or []
    out = []
    for x in w:
        t = (x.get('word') or x.get('text') or '').strip()
        s, e = x.get('start'), x.get('end')
        if s is None:
            s, e = x.get('startTimeMs', 0) / 1000.0, x.get('endTimeMs', 0) / 1000.0
        out.append((float(s), float(e), t))
    return out


def label(words, a, b, pad=0.12):
    if not words:
        return '', ''
    before = [t for s, e, t in words if e <= a + pad]
    after = [t for s, e, t in words if s >= b - pad]
    return ' '.join(before[-4:]), ' '.join(after[:4])


def ascii_(s):
    return s.encode('ascii', 'backslashreplace').decode('ascii')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cut')
    ap.add_argument('--budget', type=float, default=0.12,
                    help='max fraction of runtime that may be silence (default 0.12)')
    ap.add_argument('--noise', type=float, default=None,
                    help='silence threshold in dB (default: from --probe, else the cut itself)')
    ap.add_argument('--probe', help='work/probe.json: its calibrated silence floor is the threshold')
    ap.add_argument('--min', dest='min_dur', type=float, default=0.12,
                    help='ignore silences shorter than this (default 0.12s)')
    ap.add_argument('--show', type=float, default=0.25, help='list gaps >= this (default 0.25s)')
    ap.add_argument('--words', help='Whisper-style JSON, used only to NAME gaps')
    a = ap.parse_args()
    find_tools()

    total = duration(a.cut)
    if total <= 0:
        print('could not read duration: %s' % a.cut)
        return 2

    noise, why = a.noise, 'set by --noise'
    if noise is None and a.probe and os.path.exists(a.probe):
        cal = json.load(open(a.probe, encoding='utf-8')).get('calibration') or {}
        if cal.get('gap_db') is not None:
            noise, why = float(cal['gap_db']), 'calibrated in probe.json'
    if noise is None:
        noise, why = file_threshold(a.cut), "the cut's own level (90th pct - 22 dB, floor -55)"
        if noise is None:
            print('could not read the audio of %s' % a.cut)
            return 2
    a.noise = noise

    sil, raw = run_silencedetect(a.cut, a.noise, a.min_dur)
    if not sil and 'silencedetect' not in raw:
        print('silencedetect produced no output -- is ffmpeg logging at info level?')
        return 2

    words = load_words(a.words)
    quiet = sum(b - x for x, b in sil)
    frac = quiet / total

    print('cut          %s' % os.path.basename(a.cut))
    print('runtime      %.2fs' % total)
    print('threshold    %.1f dB, %s' % (a.noise, why))
    print('silence      %.2fs across %d gaps  (threshold %.1fdB, min %.2fs)'
          % (quiet, len(sil), a.noise, a.min_dur))
    print('budget       %.0f%%   ACTUAL %.0f%%' % (a.budget * 100, frac * 100))
    print()

    big = sorted([s for s in sil if s[1] - s[0] >= a.show], key=lambda s: -(s[1] - s[0]))
    if big:
        print('LONGEST GAPS (>= %.2fs)' % a.show)
        for x, b in big[:20]:
            bf, af = label(words, x, b)
            ctx = ('   ...%-30s >>> %s' % (ascii_(bf)[-30:], ascii_(af)[:30])) if words else ''
            print('  %5.3fs @%8.3f%s' % (b - x, x, ctx))
        print()

    if frac > a.budget:
        over = (frac - a.budget) * total
        print('RESULT: OVER BUDGET by %.2fs.' % over)
        print('  Tighten with gaps.py (--internal/--join default 0.150) and re-render.')
        print('  Trim from the MIDDLE of each silence so no verified boundary moves.')
        return 1

    print('RESULT: within budget.')
    print('  This is an aggregate gate only. It says nothing about whether any single')
    print('  gap is right, and nothing about whether the cut sounds good. Ear pass still runs.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
