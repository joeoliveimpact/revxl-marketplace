#!/usr/bin/env python3
"""Build a multi-clip master whose AUDIO clock is the same clock the render cuts on, and prove it.

    python clock_fix.py <master.mp4> -o <master.mov>            # fix an existing concat
    python clock_fix.py --concat <list.txt> -o <master.mov>     # concat-demux the clips first (stream copy)

Video is stream-copied (generation 0 untouched). Audio is decoded once with every pts gap padded
(aresample=async=1:min_hard_comp=0.005:first_pts=0) and written as PCM 24-bit, so a plain WAV
extraction of the .mov lands on the pts clock. ffmpeg's default min_hard_comp is 0.1 s: async=1
alone leaves every gap under 100 ms in place (measured 09.17.26: still 52 to 99 ms adrift).

Proof: a plain 16 kHz WAV of the OUTPUT is cross-correlated against atrim decodes of the INPUT
(what render.py cuts) at ~12 speaking windows across the file. Exit 1 unless every lag is within
--tol ms. A join receipt (per-clip audio/video gap) is printed either way.
"""
import argparse, json, shutil, subprocess, sys, tempfile, wave
from pathlib import Path

import numpy as np

SR = 16000


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=kw.pop("timeout", 1800), **kw)


def stream_durations(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration,start_time", "-of", "json", str(path)])
    d = {}
    for s in json.loads(p.stdout).get("streams", []):
        d[s["codec_type"]] = (float(s.get("start_time", 0) or 0), float(s.get("duration", 0) or 0))
    return d


def decode_atrim(path, t0, t1):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-af", "atrim=start=%s:end=%s,asetpts=PTS-STARTPTS,aresample=async=1:min_hard_comp=0.005:first_pts=0" % (t0, t1),
                        "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, timeout=300)
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768


def plain_wav(path, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True, timeout=1800)
    with wave.open(str(out)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def lag_ms(ref, src_path, t, win=3.0, search=0.8):
    seg = decode_atrim(src_path, t, t + win)
    a = ref[int((t - search) * SR):int((t + win + search) * SR)]
    if len(seg) < SR or len(a) <= len(seg):
        return None, 0.0, -120.0
    seg = seg - seg.mean(); a = a - a.mean()
    rms = 20 * np.log10(np.sqrt(np.mean(seg * seg)) + 1e-9)
    c = np.correlate(a, seg, mode="valid"); k = int(np.argmax(c))
    q = c[k] / (np.linalg.norm(a[k:k + len(seg)]) * np.linalg.norm(seg) + 1e-9)
    return (k / SR - search) * 1000.0, float(q), float(rms)


def selftest():
    """Plant sub-100 ms audio gaps in a synthetic 4-clip master, show the drift, then show the fix removes it."""
    tmp = Path(tempfile.mkdtemp(prefix="clockfix_selftest_"))
    try:
        files = []
        for i, gap in enumerate((40, 60, 80, 50)):  # ms of audio missing at the end of each clip
            clip = tmp / ("clip%d.mp4" % i)
            r = run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=6", "-f", "lavfi", "-i",
                     "anoisesrc=color=pink:seed=%d:amplitude=0.3:sample_rate=48000:duration=%.3f,lowpass=f=3000" % (i + 1, 6 - gap / 1000),
                     "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", str(clip)])
            if r.returncode:
                sys.exit("selftest FAIL: could not make clip %d: %s" % (i, r.stderr))
            files.append("file '%s'" % clip.name)
        (tmp / "list.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
        master = tmp / "master.mp4"
        r = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(master)])
        if r.returncode:
            sys.exit("selftest FAIL: concat: " + r.stderr)
        lag, q, rms = lag_ms(plain_wav(master, tmp / "plain.wav"), master, 19.0)  # a window inside the last clip
        print("planted drift, unfixed master, last clip: %s ms (q %.2f, rms %.0f dB)" % ("none" if lag is None else "%+.1f" % lag, q, rms))
        if lag is None or q < 0.9 or abs(lag) <= 20:
            sys.exit("selftest FAIL: the planted drift did not show on the unfixed master")
        r = run([sys.executable, __file__, str(master), "-o", str(tmp / "fixed.mov")])
        print(r.stdout + r.stderr)
        if r.returncode or "CLOCKS AGREE" not in r.stdout:
            sys.exit("selftest FAIL: the fix did not make the clocks agree (exit %d)" % r.returncode)
        lag, q, _ = lag_ms(plain_wav(tmp / "fixed.mov", tmp / "fixed16k.wav"), master, 11.9)  # window across the 12 s join
        print("window across a join (t=11.9 s), fixed output: %s ms (q %.2f)" % ("none" if lag is None else "%+.1f" % lag, q))
        if not (lag is not None and q >= 0.9 and abs(lag) <= 2):
            sys.exit("selftest FAIL: a proof window across a join mis-reads")
        print("selftest ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("master", nargs="?", help="existing concatenated master (mp4)")
    ap.add_argument("--concat", help="concat-demuxer list: build the stream-copied master first")
    ap.add_argument("-o", "--out", help="output .mov (video copy + padded PCM audio)")
    ap.add_argument("--points", type=int, default=12)
    ap.add_argument("--tol", type=float, default=2.0, help="ms: max |lag| allowed at any speaking window")
    ap.add_argument("--selftest", action="store_true", help="build a synthetic multi-clip master with planted gaps and prove the fix")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.out:
        ap.error("-o/--out is required")
    if bool(a.master) == bool(a.concat):
        sys.exit("give a master OR --concat, not both")
    tmp = Path(tempfile.mkdtemp(prefix="clockfix_"))
    master = Path(a.master) if a.master else tmp / "concat.mp4"
    if a.concat:
        r = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", a.concat, "-c", "copy", str(master)])
        if r.returncode:
            sys.exit(r.stderr)
        print("JOINS (video - audio duration per clip = pts gap left at its join):")
        for line in Path(a.concat).read_text(encoding="utf-8").splitlines():
            if line.startswith("file "):
                f = Path(a.concat).parent / line[5:].strip().strip("'\"")
                d = stream_durations(f)
                print("  %+7.1f ms  %s" % ((d.get("video", (0, 0))[1] - d.get("audio", (0, 0))[1]) * 1000, f.name))
    d = stream_durations(master)
    print("input : video %.3f s | audio %.3f s | audio short by %+.1f ms" % (d["video"][1], d["audio"][1], (d["video"][1] - d["audio"][1]) * 1000))

    out = Path(a.out)
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(master), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
             "-af", "aresample=async=1:min_hard_comp=0.005:first_pts=0", "-c:a", "pcm_s24le", str(out)])
    if r.returncode:
        sys.exit(r.stderr)
    do = stream_durations(out)
    print("output: video %.3f s | audio %.3f s  -> %s" % (do["video"][1], do["audio"][1], out))

    ref = plain_wav(out, tmp / "out16k.wav")
    total = len(ref) / SR
    ts = [total * (i + 0.5) / a.points for i in range(a.points)]
    worst, rows, checked = 0.0, [], 0
    for t in ts:
        t = max(1.0, min(t, total - 4.0))
        lag, q, rms = lag_ms(ref, master, t)
        if lag is None or rms < -45 or q < 0.9:
            rows.append("  t=%6.1fs  skipped (silence or weak match: rms %.0f dB, q %.2f)" % (t, rms, q)); continue
        checked += 1; worst = max(worst, abs(lag))
        rows.append("  t=%6.1fs  lag %+6.1f ms  q %.2f" % (t, lag, q))
    print("PROOF: plain WAV of the output vs atrim decodes of the input (the render clock)")
    print("\n".join(rows))
    ok = checked >= 3 and worst <= a.tol
    print("worst |lag| %.1f ms over %d speaking windows -> %s" % (worst, checked, "CLOCKS AGREE" if ok else "FAIL"))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
