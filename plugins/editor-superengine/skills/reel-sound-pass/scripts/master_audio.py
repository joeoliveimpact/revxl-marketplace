"""Loudness master: one static gain, then a true-peak-safe limiter. And the F-4 gate on a finished file.

  master_audio.py <mix.wav> <master.wav> [--target -14] [--tp-max -1.0]
      Target -14.0 LUFS integrated (measured AFTER the limiter), true peak <= -1.0 dBTP.
      alimiter: level=disabled (else it auto-levels to 0 dB), latency=enabled (else a ~5 ms shift against the
      picture). It caps the SAMPLE peak, not the true peak, so the threshold is swept until the measured true
      peak passes.
  master_audio.py --gate <final.mp4>
      F-4 (hard rule): the delivered file's sound is stereo, -14 LUFS within 0.5, true peak <= -1.0 dBTP.
      A mono delivery reads about 3 dB low on phones, so it is refused. Exit 0 pass, 1 fail.
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import ffmpeg, loudness, channels  # noqa: E402

TARGET_I, TP_MAX, GATE_LU = -14.0, -1.0, 0.5


def loudnorm_i(path):
    log = subprocess.run([ffmpeg(), "-nostats", "-i", str(path), "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return float(json.loads(log[log.rindex("{"):log.rindex("}") + 1])["input_i"])


def chain(gain_db, limit_db):
    return ("volume=%.3fdB,alimiter=limit=%.4f:level=disabled:latency=enabled:attack=5:release=50"
            % (gain_db, 10 ** (limit_db / 20)))


def master(src, dst, target=TARGET_I, tp_max=TP_MAX):
    """Writes dst (float WAV); returns the numbers, with pass = within 0.1 LU and under the true-peak line."""
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    i_in = loudnorm_i(src)
    gain, limit = target - i_in, -1.5
    for _ in range(12):
        i_out, tp = loudness(src, chain(gain, limit))
        if tp > tp_max:
            limit -= 0.2
            continue
        if abs(i_out - target) > 0.05:
            gain += target - i_out
            continue
        break
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(src), "-vn", "-af", chain(gain, limit), "-c:a", "pcm_f32le",
                    str(dst)], check=True)
    i_f, tp_f = loudness(dst)
    return {"input_lufs": i_in, "gain_db": round(gain, 3), "limit_dbfs": round(limit, 2),
            "out_lufs": i_f, "out_true_peak_dbtp": tp_f,
            "pass": abs(i_f - target) <= 0.1 and tp_f <= tp_max}


def gate(path):
    """F-4 on the delivered file: (ok, numbers, plain problems)."""
    ch = channels(path)
    i, tp = loudness(path)
    problems = []
    if ch != 2:
        problems.append("the sound is %s, not stereo (a mono file plays about 3 dB quiet)"
                        % ("mono" if ch == 1 else "%d-channel" % ch))
    if abs(i - TARGET_I) > GATE_LU:
        problems.append("loudness is %.1f LUFS, not %.1f (within %.1f)" % (i, TARGET_I, GATE_LU))
    if tp > TP_MAX:
        problems.append("the loudest peak is %.1f dBTP, over %.1f" % (tp, TP_MAX))
    return not problems, {"integrated_lufs": i, "true_peak_dbtp": tp, "channels": ch}, problems


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Loudness master, or the F-4 gate on a finished file.")
    ap.add_argument("files", nargs="+", help="<mix.wav> <master.wav>, or one file with --gate")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--target", type=float, default=TARGET_I)
    ap.add_argument("--tp-max", type=float, default=TP_MAX)
    a = ap.parse_args(argv)
    if a.gate:
        ok, nums, problems = gate(a.files[0])
        print(json.dumps(nums))
        print("Sound check passed." if ok else "Sound check failed: " + "; ".join(problems) + ".")
        return 0 if ok else 1
    if len(a.files) != 2:
        ap.error("give the mix and the master file")
    r = master(a.files[0], a.files[1], a.target, a.tp_max)
    print(json.dumps(r))
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
