"""Check the delivered file against the baked stems: every cue survived, and the music kept the board's ratio.

  mix_check.py <final.mp4> --voice <cleaned voice.wav> --sound <reel>/sound

The voice control is the PROCESSED voice (cleaned and re-gained, the one that went into the mix): the raw voice
stem would false-fail, because a clean-up changes the quiet stretches by tens of dB. Each track's level is solved by
least squares (mix = gv*voice + sum gl*lane + gb*music), so nothing has to be taken on trust.
  cue survival: in each cue's highest-energy placed 0.5 s inside the reel (the whole cue if shorter), what is left after everything else is taken away must match the cue (correlation >= 0.9); windows under 50 ms are weak.
  music ratio:  in 0.5 s windows where the voice speaks under audible music, the music-to-voice level is solved
                again; its spread (10th to 90th percentile) must stay under 1 dB, so nothing dynamic re-levelled it.
Prints JSON; exit 0 pass, 1 fail.
"""
import argparse, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import SR, decode, loudness  # noqa: E402

WEAK_CORR, SPREAD_DB = 0.9, 1.0


def fit(n, x):
    out = np.zeros(n)
    m = min(n, len(x))
    out[:m] = x[:m]
    return out


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def check(final, voice_path, sound):
    sound = Path(sound)
    P = json.loads((sound / "placement.json").read_text(encoding="utf-8"))
    y = decode(final).astype(np.float64).mean(1)
    N = len(y)
    voice = fit(N, decode(voice_path).astype(np.float64).mean(1))
    bed = fit(N, decode(sound / P["bed"]["file"]).astype(np.float64).mean(1))
    lanes = [np.zeros(N) for _ in range(P["lanes"])]
    alone = []
    for c in P["cues"]:
        x = decode(sound / c["file"]).astype(np.float64).mean(1)
        s = c["start_sample"]
        e = min(N, s + len(x))
        one = np.zeros(N)
        one[s:e] = x[:max(0, e - s)]
        lanes[c["lane"]] += one
        alone.append((one, s, e))

    A = np.stack([voice] + lanes + [bed], 1)
    g, *_ = np.linalg.lstsq(A, y, rcond=None)
    model = A @ g
    names = ["voice", *["sfx %d" % (i + 1) for i in range(P["lanes"])], "music"]
    gains = {n: (round(20 * np.log10(abs(v)), 2) if abs(v) > 1e-6 else None) for n, v in zip(names, g)}

    cues = []
    for c, (one, cue_start, cue_end) in zip(P["cues"], alone):
        placed = one[cue_start:cue_end]
        if np.any(placed):
            win = min(SR // 2, len(placed))
            # Prefix sums score every sample-aligned window in linear time.
            energy = np.concatenate(([0.0], np.cumsum((g[1 + c["lane"]] * placed) ** 2)))
            s = cue_start + int(np.argmax(energy[win:] - energy[:-win]))
            e = s + win
        else:  # silent cue: retain the timing fallback, still bounded by the cue's end
            s = int(round(max(0.0, c["time"] - c.get("peak_s", 0)) * SR))
            e = min(N, cue_end, s + int(min(c["seconds"], 0.5) * SR))
        own = (g[1 + c["lane"]] * one)[s:e]
        rest = (y - model)[s:e] + own                 # everything else taken away
        too_short = e - s < SR * 0.05
        corr = float(np.corrcoef(rest, own)[0, 1]) if not too_short and np.std(own) > 0 else 0.0
        row = {"id": c["id"], "beat": c["beat"][:24], "corr": round(corr, 3),
               "over_voice_db": round(rms_db(own) - rms_db(g[0] * voice[s:e]), 1)}
        if too_short:
            row["too_short"] = True
        cues.append(row)

    ratios = []
    if np.abs(bed).max() > 0:
        r = y - sum(g[1 + k] * lanes[k] for k in range(P["lanes"]))
        win = SR // 2
        for i in range(0, N - win, win):
            v, b = voice[i:i + win], bed[i:i + win]
            if rms_db(v) > -40 and rms_db(b) > max(-60, rms_db(v) - 30):
                (a, bb), *_ = np.linalg.lstsq(np.stack([v, b], 1), r[i:i + win], rcond=None)
                if a > 0 and bb > 0:
                    ratios.append(20 * np.log10(bb / a))
    spread = float(np.percentile(ratios, 90) - np.percentile(ratios, 10)) if len(ratios) >= 3 else None

    I, TP = loudness(final)
    weak = [c for c in cues if c["corr"] < WEAK_CORR]
    return {"integrated_lufs": I, "true_peak_dbtp": TP, "track_gain_db": gains,
            "model_residual_db": round(float(10 * np.log10(np.mean((y - model) ** 2) / (np.mean(y ** 2) + 1e-20) + 1e-20)), 1),
            "music_ratio_db": round(float(np.median(ratios)), 2) if ratios else None,
            "music_ratio_spread_db": round(spread, 2) if spread is not None else None,
            "music_windows": len(ratios), "weak_cues": weak, "cues": cues,
            "pass": not weak and (spread is None or spread < SPREAD_DB)}


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Check the delivered mix against its stems.")
    ap.add_argument("final")
    ap.add_argument("--voice", required=True, help="the cleaned, re-gained voice that went into the mix")
    ap.add_argument("--sound", required=True, help="the reel's sound folder (placement.json, cues/, music.wav)")
    a = ap.parse_args(argv)
    r = check(a.final, a.voice, a.sound)
    print(json.dumps(r, indent=1))
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
