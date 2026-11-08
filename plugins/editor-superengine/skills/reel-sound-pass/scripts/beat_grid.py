"""Find a music track's beat grid: its tempo, where the beats fall, and which beat starts a bar.

  beat_grid.py <file>      prints the grid as JSON; a plain line and exit 1 when there is no steady beat

grid(path) -> {"bpm", "period_s", "phase_s", "downbeat_s", "confidence"} or None. Times are seconds into the track:
beats sit at phase_s + k*period_s (phase_s is the first one), bars start at downbeat_s + 4*k*period_s.

How it listens (standard library + numpy; the editor's ffmpeg decodes):
  1. The track is read twice as mono 22,050 Hz: the full sound, and only its lows (under about 120 Hz, the kick).
  2. Each is turned into an onset curve: how much louder each 5 ms step is than the 10 ms before it (rises only).
     The two are scaled alike and added, so the kick counts twice: the "hit curve".
  3. Tempo: the hit curve's best self-matches over 60-200 BPM are seed beat lengths. Each seed and its relatives
     (1/2, 2/3, 3/4, 4/3, 3/2, 2 times it) are scored with a comb: how hard the curve hits on the best-placed grid
     of that length. The best length wins, then its own relatives are tried until none scores higher. This is what
     keeps a trap beat (kicks on 1 and the and-of-2, hats in triplets) from reading as 2/3 or 4/3 of its tempo.
  4. Where the beats fall: the hit curve is folded on that beat length and the strongest fold wins. Then a
     straight line is fitted through the hit nearest each beat (within 25 ms; stray ones dropped), which fixes the
     beat length and the first beat together.
  5. Double or half: score each allowed beat length against strong onsets from the full sound and the kick.
     Balance the share of grid lines with hits and the share of hits covered by lines; ties favour 90-130 BPM.
  6. Bar start: of the four beat positions in a bar, the one with the most kick.
  7. Confidence: the share of beats with a clear onset (full sound or kick) within an eighth of a beat, counted over
     what chance would give, so dense hats can't lift a wrong grid. No grid when it is under MIN_CONFIDENCE, or when
     the comb at the beat isn't STEADY_AT times harder than at nearby unrelated lengths (steady noise, a pad).
  8. Residual: take the nearest onset peak within an eighth beat of each final grid line, keeping at least eight.
     Refit those peaks against their line indices; their GATE_PCTL percentile miss must be at most MAX_RESIDUAL.
     The median gates acceptance; the 90th percentile and largest miss are also reported.
No tempo hint is ever taken: the track alone decides.
ponytail: one steady tempo and 4/4 bars only; a track that speeds up or swings beyond the residual limit has no
grid. Track the tempo per section if that is ever needed.
"""
import json, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import ffmpeg  # noqa: E402

SR = 22050
HOP = 110                       # about 5 ms
H = HOP / SR
MIN_BPM, MAX_BPM = 60.0, 200.0
MIN_CONFIDENCE = 0.25           # chance-corrected (step 7): steady noise scores about 0, a weak real beat 0.3
ONSET_K = 3.0                   # an onset stands this many standard deviations above the curve's mean
CONF_K = 2.5                    # the same, for the confidence count
REL = (0.5, 2 / 3, 0.75, 4 / 3, 1.5, 2.0)    # beat lengths a beat is mistaken for, as multiples of the true one
SEEDS = 4                       # self-match peaks tried as seeds
CHUNK_S = 12.0                  # the comb's stretch length
DECOYS = (0.87, 0.91, 0.95, 1.05, 1.09, 1.13)  # beat lengths near the found one but not musically related
STEADY_AT = 1.4                 # a steady beat combs this much harder than every decoy
FIT_W = 0.025                   # the line fit takes the onset within this of each beat (dense music: the nearest hit)
GATE_PCTL = 50                  # percentile of absolute nearest-peak residuals after refitting
MAX_RESIDUAL = 0.010            # largest allowed gated statistic, in seconds
# ponytail: the 10 ms median cutoff is tuned on 3 shipped beds (3.5-5.6 ms) and a synthetic 116->124 BPM drift
# (17-22 ms); widen it if real client music with a steady beat gets refused.
VERSION = 3
LAST_REASON = None              # "drift", "no beat", or None after acceptance


def _mono(path, af=None):
    p = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SR)]
                       + (["-af", af] if af else []) + ["-f", "f32le", "-"], capture_output=True)
    if p.returncode:
        raise RuntimeError("could not read the sound in %s" % Path(path).name)
    return np.frombuffer(p.stdout, np.float32).astype(np.float64)


def onset_curve(x):
    """Per 5 ms step: the RMS of the next 10 ms minus the RMS of the 10 ms before, rises only. Index i is time i*H."""
    n = len(x) // HOP
    if n < 4:
        return np.zeros(max(n, 0))
    e = (x[:n * HOP].reshape(n, HOP) ** 2).mean(1)
    two = np.sqrt((e + np.concatenate([e[1:], [e[-1]]])) / 2)        # 10 ms window starting at step i
    d = two - np.concatenate([[two[0], two[0]], two[:-2]])
    return np.maximum(d, 0)


def _parab(y, j):
    if 0 < j < len(y) - 1:
        a, b, c = y[j - 1], y[j], y[j + 1]
        den = a - 2 * b + c
        if den < 0:
            return j + 0.5 * (a - c) / den
    return float(j)


def _z(e):
    s = e.std()
    return (e - e.mean()) / s if s > 0 else e * 0


def _comb(acc, period):
    """How hard the curve hits on a grid of this beat length: in each CHUNK_S stretch, the mean of the curve on its
    best-placed grid (a line takes the largest value within one step), averaged over the stretches. Short stretches
    keep a tiny beat-length error from smearing the grid over a long track."""
    p, m, out = period / H, int(CHUNK_S / H), []
    j = np.arange(int(np.ceil(p)))
    for s in range(0, max(1, len(acc) - m // 2), m):
        seg = acc[s:s + m]
        nb = int(len(seg) / p)
        if nb < 2:
            continue
        prof = seg[np.minimum(np.rint(j[:, None] + np.arange(nb)[None, :] * p).astype(int), len(seg) - 1)].mean(1)
        out.append(float(np.maximum(prof, np.maximum(np.roll(prof, 1), np.roll(prof, -1))).max()))
    return float(np.mean(out)) if out else 0.0


def _tempo(acc):
    """Beat length (s). The curve's self-match gives a few seed lengths over 60-200 BPM (each sharpened on its 2nd,
    4th, 8th ... repeat); each seed and its musical relatives (REL) are scored with the comb and the best wins, then
    its own relatives get the same test until none beats it. The self-match alone mistakes a trap kick pattern's
    dotted beat (1.5 beats) for the beat; the comb sees most of its lines miss the snares and the downbeats."""
    a = acc - acc.mean()
    n = len(a)
    acf = np.fft.irfft(np.abs(np.fft.rfft(a, 2 * n)) ** 2)[:n]
    lo, hi = int(60 / MAX_BPM / H), int(np.ceil(60 / MIN_BPM / H))
    if hi + 2 >= n:
        return None
    seg = acf[lo:hi + 1]
    tops = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] > seg[i + 1]]
    seeds = []
    for i in sorted(tops, key=lambda i: -seg[i])[:SEEDS]:
        lag, m = _parab(acf, lo + i), 2
        while np.isfinite(lag) and m * lag + 4 < n / 2:
            c = int(round(m * lag))
            if c - 3 < 0 or c + 4 > n:
                break
            refined = _parab(acf, c - 3 + int(np.argmax(acf[c - 3:c + 4]))) / m
            if not np.isfinite(refined) or m * refined - 3 < 0 or m * refined + 4 > n:
                break  # keep the last usable lag when interpolation leaves the curve
            lag = refined
            m *= 2
        seeds.append(lag * H)
    if not seeds:
        return None
    fits = lambda p: MIN_BPM * 0.98 <= 60 / p <= MAX_BPM * 1.02  # noqa: E731
    best = max((s * r for s in seeds for r in (1.0,) + REL if fits(s * r)), key=lambda p: _comb(acc, p), default=None)
    while best:
        nxt = max([best] + [best * r for r in REL if fits(best * r)], key=lambda p: _comb(acc, p))
        if nxt == best:
            break
        best = nxt
    return best


def _lines(phase, period, dur):
    k = np.arange(int(max(0.0, dur - phase) / period) + 1)
    t = phase + k * period
    return k[t < dur], t[t < dur]


def _near(env, t, w):
    """(largest curve value within +-w s of each time, where it is in s)."""
    if not len(t):
        return np.zeros(0), np.zeros(0)
    half = max(1, int(round(w / H)))
    idx = np.clip(np.rint(np.asarray(t) / H).astype(int)[:, None] + np.arange(-half, half + 1)[None, :], 0, len(env) - 1)
    v = env[idx]
    j = np.argmax(v, 1)
    return v[np.arange(len(t)), j], idx[np.arange(len(t)), j] * H


def _phase(env, period):
    """The first beat (s) by folding the curve on the beat length."""
    n = len(env)
    j = np.arange(int(np.ceil(period / H)))
    k = np.arange(int(n * H / period) + 1)
    idx = np.rint(j[:, None] + k[None, :] * (period / H)).astype(int)
    s = np.where(idx < n, env[np.minimum(idx, n - 1)], 0).sum(1)
    return float(j[int(np.argmax(s))] * H)


def _fit(env, period, phase, dur, thr):
    """Least-squares line through the onset nearest each beat (strays dropped): (beat length, first beat)."""
    for _ in range(3):
        k, t = _lines(phase, period, dur)
        v, at = _near(env, t, min(period / 8, FIT_W))
        keep = v > thr
        if keep.sum() < 8:
            break
        kk, tt = k[keep].astype(float), at[keep]
        for _ in range(2):
            p, c = np.polyfit(kk, tt, 1)
            r = np.abs(tt - (c + p * kk))
            ok = r <= max(2 * H, 3 * np.median(r))
            if ok.sum() < 8:
                break
            kk, tt = kk[ok], tt[ok]
        p, c = np.polyfit(kk, tt, 1)
        if not (60 / MAX_BPM * 0.9 < p < 60 / MIN_BPM * 1.1):
            break
        period, phase = float(p), float(c % p)
    return period, phase


def _strength(env, t, w):
    return float(_near(env, t, w)[0].mean()) if len(t) else 0.0


def _confidence(full, kick, t, w):
    """The share of beats with a clear onset (full sound or kick) within w, counted over what chance gives:
    (hit - chance) / (1 - chance), where chance is the share of all moments with such an onset within w. Dense hats
    or triplet rolls raise the chance, so they can't buy a wrong grid its confidence; steady noise scores about 0."""
    if not len(t):
        return 0.0
    tf, tk = full.mean() + CONF_K * full.std(), kick.mean() + CONF_K * kick.std()
    hit = float(np.mean((_near(full, t, w)[0] > tf) | (_near(kick, t, w)[0] > tk)))
    half = max(1, int(round(w / H)))
    near = np.convolve(((full > tf) | (kick > tk)).astype(float), np.ones(2 * half + 1), "same") > 0
    chance = float(near.mean())
    return (hit - chance) / (1 - chance) if chance < 1 else 0.0


def grid(path):
    """The track's beat grid (see the module notes), or None when it has no steady beat."""
    global LAST_REASON
    LAST_REASON = "no beat"
    full = onset_curve(_mono(path))
    kick = onset_curve(_mono(path, "lowpass=f=120,lowpass=f=120"))
    dur = len(full) * H
    if dur < 4 * 60 / MIN_BPM or full.max() <= 0:
        return None
    if kick.max() < 0.05 * full.max():                      # no lows to speak of: the full sound marks the beats
        kick = full
    acc = _z(full) + _z(kick)                               # every hit, the kick's counted twice
    thr_a = acc.mean() + ONSET_K * acc.std()
    period = _tempo(acc)
    if not period:
        return None
    phase = _phase(acc, period)
    period, phase = _fit(acc, period, phase, dur, thr_a)
    peaks = np.flatnonzero((acc > thr_a) & (acc >= np.r_[-np.inf, acc[:-1]])
                           & (acc > np.r_[acc[1:], -np.inf]))
    hits = peaks * H
    if not len(hits):
        return None
    tempo_check, choices = [], []
    for candidate in sorted({period * 2, period, period / 2}):
        bpm = 60 / candidate
        eligible = bool(MIN_BPM <= bpm <= MAX_BPM)
        record = {"bpm": round(float(bpm), 3), "precision": None, "recall": None, "eligible": eligible}
        tempo_check.append(record)
        if not eligible:
            continue
        folded = _phase(acc, candidate)
        _, lines = _lines(folded, candidate, dur)
        if not len(lines):
            continue
        # Search sorted times in both directions without building a track-length squared array.
        def matched(a, b):
            j = np.searchsorted(b, a)
            distance = np.minimum(np.abs(a - b[np.clip(j, 0, len(b) - 1)]),
                                  np.abs(a - b[np.clip(j - 1, 0, len(b) - 1)]))
            return float(np.mean(distance <= 0.025))
        precision, recall = matched(lines, hits), matched(hits, lines)
        score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        preference = max(90 - bpm, 0, bpm - 130)
        record.update(precision=round(precision, 4), recall=round(recall, 4))
        choices.append((score, -preference, candidate, folded))
    if not choices:
        return None
    _, _, period, phase = max(choices, key=lambda row: row[:2])
    period, phase = _fit(acc, period, phase, dur, thr_a)
    k, t = _lines(phase, period, dur)
    v = _near(kick, t, period / 8)[0]
    bar = [float(v[k % 4 == r].sum()) for r in range(4)]
    downbeat = phase + int(np.argmax(bar)) * period
    conf = _confidence(full, kick, t, period / 8)
    steady = _comb(acc, period) >= STEADY_AT * max(_comb(acc, period * r) for r in DECOYS)
    if conf < MIN_CONFIDENCE or not steady:
        return None
    j = np.searchsorted(hits, t)
    left, right = hits[np.clip(j - 1, 0, len(hits) - 1)], hits[np.clip(j, 0, len(hits) - 1)]
    at = np.where(np.abs(t - left) <= np.abs(t - right), left, right)
    keep = np.abs(at - t) <= period / 8
    if keep.sum() < 8:                                       # too few hits to judge: no beat, not drift
        LAST_REASON = "no beat"
        return None
    p, c = np.polyfit(k[keep], at[keep], 1)
    residuals = np.abs(at[keep] - (c + p * k[keep]))
    residual = float(np.percentile(residuals, GATE_PCTL))
    if residual > MAX_RESIDUAL:
        LAST_REASON = "drift"
        return None
    kicks = [[round(float(at), 4), round(float(strength), 3)] for at, strength in zip(t, v)]
    LAST_REASON = None
    return {"bpm": round(float(60 / period), 3), "period_s": round(float(period), 6), "phase_s": round(float(phase), 4),
            "downbeat_s": round(float(downbeat), 4), "confidence": round(conf, 3),
            "residual_ms": round(residual * 1000, 1),
            "residual_p90_ms": round(float(np.percentile(residuals, 90)) * 1000, 1),
            "residual_max_ms": round(float(np.max(residuals)) * 1000, 1), "tempo_check": tempo_check, "kicks": kicks}


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: beat_grid.py <music file>")
        return 2
    if not Path(argv[0]).is_file():
        print("There is no music file at %s." % argv[0])
        return 2
    g = grid(argv[0])
    if not g:
        if LAST_REASON == "drift":
            print("The beat in %s drifts, so the music starts where the board set it and nothing snaps to the beat."
                  % Path(argv[0]).name)
        else:
            print("No steady beat was found in %s." % Path(argv[0]).name)
        return 1
    print(json.dumps(g))
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
