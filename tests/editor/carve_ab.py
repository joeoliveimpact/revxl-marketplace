"""Local listening proof: python -X utf8 -I tests/editor/carve_ab.py --out <dir>.

Writes two 15 s WAV clips and one captioned 30 s MP4 (carve, then dip), at the
same bed level over the licensed speech10s.flac fixture, each mastered to
-14 LUFS integrated and at most -1 dBTP using the real sound-pass master.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
SCRIPTS = PLUGIN / "skills/reel-sound-pass/scripts"
if __name__ == "__main__":
    sys.path.insert(0, str(SCRIPTS))  # imported tests keep their explicit --plugin path
import _media as M  # noqa: E402
import carve  # noqa: E402
import master_audio as MA  # noqa: E402
import music_fit as MF  # noqa: E402


def fixture(plugin=PLUGIN):
    sr, n = M.SR, 15 * M.SR
    source = M.decode(Path(plugin) / "skills/editor-doctor/selftest/speech10s.flac")
    voice = np.zeros((n, 2), np.float32)
    count = min(len(source), 10 * sr)
    voice[sr:sr + count] = source[:count]
    rng = np.random.default_rng(2184)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    z = np.fft.rfft(rng.standard_normal((n, 2)), axis=0)
    z *= (1 / np.sqrt(np.maximum(freqs, 20)))[:, None]
    z[freqs < 20] = 0
    bed = np.fft.irfft(z, n=n, axis=0)
    bed *= 10 ** (-18 / 20) / np.sqrt(np.mean(bed ** 2))
    # The transcript surrogate follows actual energy, so the dip and spectral
    # comparisons use the same words rather than a single ten-second rectangle.
    hop = 4096
    p = [float(np.mean(voice[i:i + hop].astype(np.float64) ** 2)) for i in range(0, n, hop)]
    peak = max(p)
    spans = []
    for i, power in enumerate(p):
        if power <= peak * 10 ** (-30 / 10):
            continue
        a, b = i * hop / sr, min(n, (i + 1) * hop) / sr
        if spans and a - spans[-1]["end_s"] < MF.GAP_S:
            spans[-1]["end_s"] = b
        else:
            spans.append({"start_s": a, "end_s": b})
    return voice, bed.astype(np.float32), spans


def measurements(voice, reference, carved, dip, detail, sr):
    """Windowed band powers on the same speech windows; no thresholds adjusted here."""
    frame, hop = 4096, 2048
    starts = list(range(0, len(voice) - frame + 1, hop))
    power = np.array([np.mean(voice[i:i + frame].astype(np.float64) ** 2) for i in starts])
    speaking = power > power.max() * 10 ** (-15 / 10)
    # A continuous tail pause >=1 s, starting at least 0.5 s past the last
    # detected speech (peak -30 dB). It must really be quiet in the fixture.
    last_speech = max(i + frame for i, p in zip(starts, power) if p > power.max() * 0.001)
    pause = np.array([i >= last_speech + 0.5 * sr for i in starts])
    assert pause.sum() * hop / sr >= 1, "The fixture has no qualifying pause"
    freqs = np.fft.rfftfreq(frame, 1 / sr)
    window = np.hanning(frame)
    spectra = []
    for x in (reference, carved, dip):
        spectra.append(np.array([np.abs(np.fft.rfft(x[i:i + frame].astype(np.float64) * window[:, None], axis=0)) ** 2
                                 for i in starts]).mean(axis=2))

    def drop(a, b, lo, hi, times=speaking):
        bins = (freqs >= lo) & (freqs < hi)
        pa, pb = spectra[a][times][:, bins].mean(), spectra[b][times][:, bins].mean()
        return float(10 * np.log10(max(pa, 1e-30) / max(pb, 1e-30)))

    bands = detail["bands"]
    cuts = [drop(0, 1, b["freq"] / 2 ** (1 / 6), b["freq"] * 2 ** (1 / 6)) for b in bands]
    strongest = min(range(len(bands)), key=lambda i: bands[i]["gainDb"])
    return {"band_hz": [b["freq"] for b in bands], "band_drop_db": cuts, "strongest_drop_db": cuts[strongest],
            "outer_drop_db": [drop(0, 1, lo, hi) for lo, hi in ((20, 60), (12000, 16000))],
            "dip_outer_drop_db": [drop(0, 2, lo, hi) for lo, hi in ((20, 60), (12000, 16000))],
            "pause_drop_db": [drop(0, 1, b["freq"] / 2 ** (1 / 6), b["freq"] * 2 ** (1 / 6), pause) for b in bands],
            # Voice cancels in the difference between the two voice/bed ratios.
            "ratio_advantage_db": drop(2, 1, 1000, 4000)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--strength", type=float, default=0.8, help="Carve strength, 0.25 to 1 (default: 0.8)")
    args = parser.parse_args()
    if not 0.25 <= args.strength <= 1:
        parser.error("--strength must be between 0.25 and 1")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    voice, bed, spans = fixture()
    M.write_wav(out / "bed-source.wav", bed)
    M.write_wav(out / "voice.wav", voice)
    M.write_json(out / "work/cut/tx-cut.json", {"words": [{"start": s["start_s"], "end": s["end_s"]} for s in spans]})
    (out / "beds").mkdir(exist_ok=True)
    (out / "beds/bed.wav").write_bytes((out / "bed-source.wav").read_bytes())
    b = {"file": "bed.wav", "gain_db": -18, "duck_db": 6, "entry_s": 0, "exit_s": 15,
         "offset_s": 0, "fade_in_s": 0, "fade_out_s": 0, "stops": []}
    carved, info = MF.place(out, dict(b, carve={"on": True, "strength": args.strength}), len(bed), 15, out / "voice.wav")
    if info["mode"] != "carve":
        raise RuntimeError("The A/B requires a successful carve")
    dipped, _ = MF.place(out, b, len(bed), 15, out / "voice.wav")
    masters = {}
    for name, mix in (("carve", voice + carved), ("dip", voice + dipped),
                      ("ab", np.vstack([voice + carved, voice + dipped]))):
        raw = out / "work" / (name + "-mix.wav")
        M.write_wav(raw, mix)
        masters[name] = MA.master(raw, out / (name + ".wav"), target=-14.0, tp_max=-1.0)
        assert abs(masters[name]["out_lufs"] + 14) <= 0.5, (name, masters[name])
        assert masters[name]["out_true_peak_dbtp"] <= -1.0, (name, masters[name])
    font = PLUGIN / "runtime/fonts/Inter-Regular.woff2"
    captions = (
        f"drawtext=fontfile={font.name}:text='Carve {args.strength:g}':fontsize=42:fontcolor=white:"
        "x=(w-tw)/2:y=(h-th)/2:enable='lt(t,15)',"
        f"drawtext=fontfile={font.name}:text='Dip 6 dB':fontsize=42:fontcolor=white:"
        "x=(w-tw)/2:y=(h-th)/2:enable='gte(t,15)'"
    )
    mp4 = out / "carve-then-dip.mp4"
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x18222a:s=640x360:r=30:d=30",
                    "-i", str(out / "ab.wav"), "-vf", captions, "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-t", "30", str(mp4)], check=True, cwd=font.parent)
    ok, delivered, problems = MA.gate(mp4)
    assert ok, problems
    M.write_json(out / "carve.json", dict(info["carve"], switch_s=15,
                 measured_lufs={**{name: m["out_lufs"] for name, m in masters.items()},
                                "mp4": delivered["integrated_lufs"]},
                 masters=masters, delivered=delivered))
    print(json.dumps({"clips": [str(out / "carve.wav"), str(out / "dip.wav")],
                      "ab": str(out / "carve-then-dip.mp4"), "order": "0-15 s carve; 15-30 s dip"}))


if __name__ == "__main__":
    main()
