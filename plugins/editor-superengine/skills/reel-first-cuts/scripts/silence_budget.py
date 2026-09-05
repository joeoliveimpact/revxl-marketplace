#!/usr/bin/env python3
"""Whole-cut silence budget -- the aggregate gate.

Every other check in this skill is LOCAL: is this boundary clean, is this gap
under its cap, is this fragment an orphan. A cut can pass all of them and still
drag, because the defect is the SUM. The reference cut shipped at 70.85s with 16.63s of
silence -- 23% of the reel -- and every boundary gate was green. The human caught
it by ear in one pass and named three gaps; the real finding was systemic.

Run this on the RENDERED cut, before the ear pass. It answers one question the
per-gap caps cannot: how much of this reel is nobody talking.

    python silence_budget.py CUT.mp4
    python silence_budget.py CUT.mp4 --budget 0.10 --words v3_tx.json

Exit 0 = within budget, 1 = over, 2 = could not measure.

Notes
-----
* silencedetect logs at INFO. Do NOT pass `-v error` -- the detector output
  vanishes and the cut reads as having no silences at all.
* Label words come from a Whisper-style JSON (`words[] {word,start,end}`). ASR
  word boundaries PAD over silence, so they are used only to name a gap, never
  to measure one. The waveform is the measurement.
"""
import argparse
import json
import os
import re
import subprocess
import sys


def run_silencedetect(path, noise_db, min_dur):
    cmd = ['ffmpeg', '-i', path, '-af',
           'silencedetect=noise=%ddB:d=%.3f' % (noise_db, min_dur), '-f', 'null', '-']
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'replace')
    starts, ends = [], []
    for m in re.finditer(r'silence_(start|end):\s*(-?[0-9.]+)', out):
        (starts if m.group(1) == 'start' else ends).append(float(m.group(2)))
    return [(a, b) for a, b in zip(starts, ends) if b > a], out


def duration(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
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
    ap.add_argument('--noise', type=int, default=-40, help='silence threshold in dB (default -40)')
    ap.add_argument('--min', dest='min_dur', type=float, default=0.12,
                    help='ignore silences shorter than this (default 0.12s)')
    ap.add_argument('--show', type=float, default=0.25, help='list gaps >= this (default 0.25s)')
    ap.add_argument('--words', help='Whisper-style JSON, used only to NAME gaps')
    a = ap.parse_args()

    total = duration(a.cut)
    if total <= 0:
        print('could not read duration: %s' % a.cut)
        return 2

    sil, raw = run_silencedetect(a.cut, a.noise, a.min_dur)
    if not sil and 'silencedetect' not in raw:
        print('silencedetect produced no output -- is ffmpeg logging at info level?')
        return 2

    words = load_words(a.words)
    quiet = sum(b - x for x, b in sil)
    frac = quiet / total

    print('cut          %s' % os.path.basename(a.cut))
    print('runtime      %.2fs' % total)
    print('silence      %.2fs across %d gaps  (threshold %ddB, min %.2fs)'
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
