# Copyright 2026 HeyGen, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# You may use this file only in compliance with that License; a copy is in
# LICENSES/Apache-2.0-HyperFrames.txt. Distributed on an AS IS BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations.
# Source: HyperFrames, heygen-com/hyperframes, tag v0.8.184, commit
# d15a274c198cf18bc1df177cbe20df95392a8947, packages/core/src/audioCarve.ts.
# Changed by editor-superengine: rewritten in Python + numpy; one voice stem;
# the broadband level duck not ported; filters rendered as an STFT mask of the
# same peaking response instead of Web Audio biquads; default strength 0.8;
# no Studio code and no telemetry.
"""Voice bands and their gain lanes, with deterministic magnitude-only rendering.

All times are seconds on the reel clock. Analysis uses mono; rendering preserves
the bed's channels. The broadband level is never changed here.
"""
import math

import numpy as np

FRAME, HOP = 4096, 2048
CENTRES = (160, 250, 400, 630, 1000, 1600, 2500, 4000, 6000)
WINDOW = np.hanning(FRAME).astype(np.float32)  # symmetric, like upstream's Float32Array


def fixed(value, digits):
    """Positive JS toFixed/Math.round parity (gain magnitudes are rounded before negation)."""
    scale = 10 ** digits
    return math.floor(value * scale + 0.5) / scale


def profile(strength=0.8):
    s = float(strength)
    s = min(1.0, max(0.0, s)) if math.isfinite(s) else 0.8
    return {"strength": s, "maxCutDb": fixed(2 + 16 * s, 2),
            "bands": max(1, min(6, math.floor(1 + 6 * s + 0.5))),
            "q": fixed(1.1 + 1.2 * s, 2), "bias": fixed(min(1, 0.6 + 0.4 * s), 2)}


def mono(samples):
    x = np.asarray(samples, np.float32)
    x = x.mean(axis=1, dtype=np.float32) if x.ndim == 2 else x
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("The voice samples must be finite mono or multichannel audio.")
    return x


def power_spectrum(voice, sr):
    x = mono(voice)
    if len(x) < FRAME:
        x = np.pad(x, (0, FRAME - len(x)))
    acc = np.zeros(FRAME // 2 + 1)
    count = 0
    for start in range(0, len(x) - FRAME + 1, HOP):
        z = np.fft.rfft(x[start:start + FRAME].astype(np.float64) * WINDOW)
        acc += z.real ** 2 + z.imag ** 2
        count += 1
    return np.fft.rfftfreq(FRAME, 1 / sr), acc / max(1, count)


def band_power(freqs, power, centre):
    selected = power[(freqs >= centre / 2 ** (1 / 6)) & (freqs < centre * 2 ** (1 / 6))]
    return float(selected.mean()) if len(selected) else 0.0


def bias_penalty(centre, bias):
    return bias * 30 * (1 - math.exp(-math.log2(centre / 2000) ** 2 / 2))


def analyse_bands(voice, sr, settings):
    if not len(voice):
        return []
    freqs, power = power_spectrum(voice, sr)
    scored = []
    for centre in CENTRES:
        p = band_power(freqs, power, centre)
        if p > 0:
            scored.append((centre, 10 * math.log10(p) - bias_penalty(centre, settings["bias"])))
    scored.sort(key=lambda b: -b[1])  # stable ties follow CENTRES
    selected = scored[:settings["bands"]]
    if not selected:
        return []
    top, cut = selected[0][1], settings["maxCutDb"]
    return sorted([{"freq": c, "gainDb": -fixed(min(cut, max(cut / 2, cut * 10 ** ((s - top) / 10))), 2),
                    "q": settings["q"]} for c, s in selected], key=lambda b: b["freq"])


def simplify_points(raw):
    points, last, index = [{"t": 0.0, "v": 0.0}], 0.0, -1
    for i, pt in enumerate(raw):
        if i != len(raw) - 1 and abs(pt["v"] - last) < 0.5:
            continue
        if i > 0 and index != i - 1:
            points.append(raw[i - 1])
        points.append(pt)
        last, index = pt["v"], i
    return points


def analyse_dynamics(voice, sr, bands):
    x = mono(voice)
    if not len(x) or not bands:
        return []
    hop = max(FRAME, math.ceil(len(x) / 400))
    freqs = np.fft.rfftfreq(FRAME, 1 / sr)
    powers, times = [], []
    for start in range(0, len(x), hop):
        chunk = x[start:start + FRAME].astype(np.float64)
        chunk = np.pad(chunk, (0, FRAME - len(chunk)))
        z = np.fft.rfft(chunk * WINDOW)
        p = z.real ** 2 + z.imag ** 2
        powers.append([band_power(freqs, p, b["freq"]) for b in bands])
        times.append(fixed((start + FRAME / 2) / sr, 3))
    powers = np.asarray(powers)
    attack, release = 1 - math.exp(-hop / sr / 0.05), 1 - math.exp(-hop / sr / 0.25)
    lanes = []
    for j, band in enumerate(bands):
        peak, level, raw = float(powers[:, j].max()), 0.0, []
        for t, p in zip(times, powers[:, j]):
            target = max(0.0, 1 + 10 * math.log10(p / peak) / 30) if p > 0 and peak > 0 else 0.0
            level += (attack if target > level else release) * (target - level)
            depth = -band["gainDb"] * level
            raw.append({"t": t, "v": 0.0 if depth < 0.2 else -fixed(depth, 1)})
        points = simplify_points(raw)
        points.append({"t": fixed(max(len(x) / sr, points[-1]["t"]), 3), "v": 0.0})
        lanes.append({"freq": band["freq"], "points": points})
    return lanes


def analyse(voice, sr=48000, strength=0.8):
    p = profile(strength)
    bands = analyse_bands(voice, sr, p)
    return {"strength": p["strength"], "bands": bands, "points": analyse_dynamics(voice, sr, bands)}


def peaking_magnitude(freqs, sr, centre, q, gain_db):
    """RBJ/Web Audio peaking response, evaluated exactly at every FFT frequency."""
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * centre / sr
    alpha, cosine = math.sin(w0) / (2 * q), math.cos(w0)
    z = np.exp(-2j * np.pi * freqs / sr)
    numerator = (1 + alpha * a) - 2 * cosine * z + (1 - alpha * a) * z ** 2
    denominator = (1 + alpha / a) - 2 * cosine * z + (1 - alpha / a) * z ** 2
    return np.abs(numerator / denominator)


def render(bed, detail, sr=48000):
    """Centred STFT, exact per-frame peaking magnitude, normalized overlap-add."""
    src = np.asarray(bed, np.float32)
    if not detail["bands"] or not len(src):
        return src.copy()
    if src.ndim != 2 or not np.isfinite(src).all():
        raise ValueError("The bed must contain finite multichannel audio.")
    half = FRAME // 2
    padded = np.pad(src, ((half, FRAME), (0, 0)))
    out, norm = np.zeros_like(padded, dtype=np.float64), np.zeros(len(padded))
    freqs = np.fft.rfftfreq(FRAME, 1 / sr)
    window = WINDOW.astype(np.float64)
    lanes = {lane["freq"]: lane["points"] for lane in detail["points"]}
    for start in range(0, len(padded) - FRAME + 1, HOP):
        mask = np.ones(len(freqs))
        for b in detail["bands"]:
            pts = lanes[b["freq"]]
            gain = float(np.interp(start / sr, [p["t"] for p in pts], [p["v"] for p in pts]))
            if gain:
                mask *= peaking_magnitude(freqs, sr, b["freq"], b["q"], gain)
        spectrum = np.fft.rfft(padded[start:start + FRAME] * window[:, None], axis=0)
        out[start:start + FRAME] += np.fft.irfft(spectrum * mask[:, None], n=FRAME, axis=0) * window[:, None]
        norm[start:start + FRAME] += window ** 2
    out /= np.maximum(norm[:, None], 1e-20)
    return out[half:half + len(src)].astype(np.float32)


def selftest():
    assert profile()["strength"] == 0.8 and profile()["maxCutDb"] == 14.8 and profile()["bands"] == 6
    assert profile()["q"] == 2.06 and profile()["bias"] == 0.92
    assert profile(0.25)["bands"] == 3 and profile(1)["bands"] == 6
    assert fixed(2.5, 0) == 3 and fixed(0.25, 1) == 0.3
    assert profile(float("nan"))["strength"] == 0.8
    assert not analyse(np.zeros(8192))["bands"]
    assert not analyse(np.zeros(0))["bands"]
    sr = 48000
    t = np.arange(2 * sr) / sr
    voice = (np.sin(2 * np.pi * 1600 * t) * ((t > 0.25) & (t < 1))).astype(np.float32)
    detail = analyse(voice, sr)
    assert any(b["freq"] == 1600 for b in detail["bands"])
    for lane in detail["points"]:
        assert lane["points"][0] == {"t": 0.0, "v": 0.0}
        assert lane["points"][-1]["v"] == 0
    bed = np.column_stack([voice, voice])
    a, b = render(bed, detail, sr), render(bed, detail, sr)
    assert np.array_equal(a, b) and a.shape == bed.shape and np.isfinite(a).all()
    identity = {"bands": [{"freq": 1600, "q": 1.7}], "points": [{"freq": 1600, "points": [{"t": 0, "v": 0}]}]}
    assert np.max(np.abs(render(bed, identity, sr) - bed)) < 1e-7
    f = np.array([0., 1600., sr / 2])
    response = peaking_magnitude(f, sr, 1600, 1.7, -10)
    assert np.allclose(response, [1, 10 ** (-10 / 20), 1], atol=1e-9)
    print("PASS carve selftest: profile, rounding, silence, bands, pinned lanes, response, overlap-add, determinism")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", required=True)
    parser.parse_args()
    selftest()
