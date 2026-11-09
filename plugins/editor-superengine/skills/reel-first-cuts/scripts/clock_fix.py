#!/usr/bin/env python3
"""Build a multi-clip master whose AUDIO clock is the same clock the render cuts on, and prove it.

    <editor python> clock_fix.py <master.mp4> -o <master.mov>            # fix an existing concat
    <editor python> clock_fix.py --concat <list.txt> -o <master.mov>     # concat-demux the clips first (stream copy)

ffmpeg/ffprobe come from the editor's install (_shared/runtime.py), never PATH.
Exit 0 clocks agree, 1 proof FAIL, 2 plain-line error, 3 not enough clear speech to run the proof.

Video is stream-copied (generation 0 untouched). Audio is decoded once with every pts gap padded
(aresample=async=1:min_hard_comp=0.005:first_pts=0) and written as PCM 24-bit, so a plain WAV
extraction of the .mov lands on the pts clock. ffmpeg's default min_hard_comp is 0.1 s: async=1
alone leaves every gap under 100 ms in place (measured 09.17.26: still 52 to 99 ms adrift).

Proof: a plain 16 kHz WAV of the OUTPUT is cross-correlated against atrim decodes of the INPUT
(what render.py cuts) at ~12 speaking windows across the file. Exit 1 if any lag is over --tol ms,
3 if fewer than MIN_CHECKED windows hold clear speech. A join receipt (per-clip audio/video gap) is printed either way.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

SETUP = "The editor's setup isn't finished: its video tools are missing. Run the editor setup (editor-doctor), then try again."

try:
    import numpy as np
except ImportError:
    print("ERROR: " + SETUP, file=sys.stderr)
    sys.exit(2)

SR = 16000  # keeps speech up to 8 kHz; one sample is 0.0625 ms, far finer than the 2 ms --tol
WIN = 3.0  # s of input per window: several words, so one clear correlation peak, not a lock on one syllable
SEARCH = 0.8  # s searched either side: the worst drift measured was 479 ms by clip 11 (09.17.26), plus margin
SPEECH_DB = 30  # a window counts as speech within 30 dB of the file's loudest window; room tone sits further down
MIN_Q = 0.9  # the output is the input's own audio, so a true lock scores ~1.0; below 0.9 the peak may be a wrong lag
MIN_CHECKED = 3  # fewer windows can all sit before the first join, where there is no drift to catch
NO_SPEECH = ("Not enough clear speech to check the sound against the picture (%d of %d spots usable, need %d)."
             " Nothing was saved. Check the recording's sound isn't muted or empty, then run again with --points 24.")
FFMPEG = FFPROBE = None


def die(msg, detail=None):
    print("ERROR: " + msg, file=sys.stderr)
    if detail:
        detail = re.sub(r'(?:[A-Za-z]:)?[\\/](?:[^\\/:\n"\']+[\\/])+', '', str(detail))
        print("detail: " + detail[-300:].strip(), file=sys.stderr)
    raise SystemExit(2)


def find_tools():
    global FFMPEG, FFPROBE
    try:
        FFMPEG, FFPROBE = rt.tool("ffmpeg"), rt.tool("ffprobe")
    except (KeyError, OSError, ValueError):
        die(SETUP)
    if not (Path(FFMPEG).exists() and Path(FFPROBE).exists()):
        die(SETUP)


def launch(cmd, **kw):
    try:
        return subprocess.run(cmd, **kw)
    except FileNotFoundError:
        die(SETUP)


def run(cmd, **kw):
    return launch(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=kw.pop("timeout", 1800), **kw)


def stream_durations(path):
    p = run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,duration,start_time", "-of", "json", str(path)])
    try:
        if p.returncode:
            raise ValueError
        streams = json.loads(p.stdout).get("streams", [])
    except ValueError:
        die("Couldn't read %s: it may be damaged or not a video." % Path(path).name, p.stderr)
    d = {}
    for s in streams:
        d[s["codec_type"]] = (float(s.get("start_time", 0) or 0), float(s.get("duration", 0) or 0))
    return d


def decode_atrim(path, t0, t1):
    p = launch([FFMPEG, "-v", "error", "-i", str(path), "-af", "atrim=start=%s:end=%s,asetpts=PTS-STARTPTS,aresample=async=1:min_hard_comp=0.005:first_pts=0" % (t0, t1),
                        "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, timeout=300)
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768


def plain_wav(path, out):
    launch([FFMPEG, "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True, timeout=1800)
    with wave.open(str(out)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def lag_ms(ref, src_path, t, win=WIN, search=SEARCH):
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
    find_tools()
    tmp = Path(tempfile.mkdtemp(prefix="clockfix_selftest_"))
    try:
        files = []
        for i, gap in enumerate((40, 60, 80, 50)):  # ms of audio missing at the end of each clip
            clip = tmp / ("clip%d.mp4" % i)
            r = run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=6", "-f", "lavfi", "-i",
                     "anoisesrc=color=pink:seed=%d:amplitude=0.3:sample_rate=48000:duration=%.3f,lowpass=f=3000" % (i + 1, 6 - gap / 1000),
                     "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", str(clip)])
            if r.returncode:
                sys.exit("selftest FAIL: could not make clip %d: %s" % (i, r.stderr))
            files.append("file '%s'" % clip.name)
        (tmp / "list.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
        master = tmp / "master.mp4"
        r = run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(master)])
        if r.returncode:
            sys.exit("selftest FAIL: concat: " + r.stderr)
        lag, q, rms = lag_ms(plain_wav(master, tmp / "plain.wav"), master, 19.0)  # a window inside the last clip
        print("planted drift, unfixed master, last clip: %s ms (q %.2f, rms %.0f dB)" % ("none" if lag is None else "%+.1f" % lag, q, rms))
        if lag is None or q < MIN_Q or abs(lag) <= 20:
            sys.exit("selftest FAIL: the planted drift did not show on the unfixed master")
        r = run([sys.executable, __file__, str(master), "-o", str(tmp / "fixed.mov")])
        print(r.stdout + r.stderr)
        if r.returncode or "CLOCKS AGREE" not in r.stdout:
            sys.exit("selftest FAIL: the fix did not make the clocks agree (exit %d)" % r.returncode)
        lag, q, _ = lag_ms(plain_wav(tmp / "fixed.mov", tmp / "fixed16k.wav"), master, 11.9)  # window across the 12 s join
        print("window across a join (t=11.9 s), fixed output: %s ms (q %.2f)" % ("none" if lag is None else "%+.1f" % lag, q))
        if not (lag is not None and q >= MIN_Q and abs(lag) <= 2):
            sys.exit("selftest FAIL: a proof window across a join mis-reads")
        print("selftest ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ensure_utf8_output()
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
        die("Give one recording or one --concat list, not both.")
    find_tools()
    src = a.master or a.concat
    if not Path(src).exists():
        die("Couldn't find %s." % Path(src).name)
    tmp = Path(tempfile.mkdtemp(prefix="clockfix_"))
    out, part, ok = None, None, False
    try:
        master = Path(a.master) if a.master else tmp / "concat.mp4"
        if a.concat:
            r = run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", a.concat, "-c", "copy", str(master)])
            if r.returncode:
                die("Joining the clips failed.", r.stderr)
            print("JOINS (video - audio duration per clip = pts gap left at its join):")
            for line in Path(a.concat).read_text(encoding="utf-8").splitlines():
                if line.startswith("file "):
                    f = Path(a.concat).parent / line[5:].strip().strip("'\"")
                    d = stream_durations(f)
                    print("  %+7.1f ms  %s" % ((d.get("video", (0, 0))[1] - d.get("audio", (0, 0))[1]) * 1000, f.name))
        d = stream_durations(master)
        if "video" not in d or "audio" not in d:
            die("%s has no picture or no sound, so there is nothing to line up." % master.name)
        print("input : video %.3f s | audio %.3f s | audio short by %+.1f ms" % (d["video"][1], d["audio"][1], (d["video"][1] - d["audio"][1]) * 1000))

        if Path(a.out).resolve() == master.resolve():
            die("Write the fixed master to a new file, not over the recording.")
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_name(out.stem + ".partial" + out.suffix)  # same folder, so the move is atomic
        r = run([FFMPEG, "-y", "-v", "error", "-i", str(master), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
                 "-af", "aresample=async=1:min_hard_comp=0.005:first_pts=0", "-c:a", "pcm_s24le", str(part)])
        if r.returncode:
            die("Writing the fixed recording failed.", r.stderr)
        do = stream_durations(part)

        try:
            ref = plain_wav(part, tmp / "out16k.wav")
        except subprocess.CalledProcessError:
            die("Reading the fixed recording's sound failed.")
        total = len(ref) / SR
        ts = [total * (i + 0.5) / a.points for i in range(a.points)]
        # each window needs SEARCH of output before it and WIN + SEARCH after it, inside the file
        res = [(t,) + lag_ms(ref, master, t) for t in (max(SEARCH, min(t, total - WIN - SEARCH)) for t in ts)]
        loud = [rms for _, lag, _, rms in res if lag is not None]
        gate = (max(loud) if loud else 0.0) - SPEECH_DB  # calibrated from this file, so a quiet recording still passes
        worst, rows, checked = 0.0, [], 0
        for t, lag, q, rms in res:
            if lag is None or rms < gate or q < MIN_Q:
                rows.append("  t=%6.1fs  skipped (silence or weak match: rms %.0f dB, q %.2f)" % (t, rms, q)); continue
            checked += 1; worst = max(worst, abs(lag))
            rows.append("  t=%6.1fs  lag %+6.1f ms  q %.2f" % (t, lag, q))
        print("PROOF: plain WAV of the output vs atrim decodes of the input (the render clock), speech gate %.0f dB" % gate)
        print("\n".join(rows))
        if worst > a.tol:
            print("worst |lag| %.1f ms over %d speaking windows -> FAIL" % (worst, checked))
            sys.exit(1)
        if checked < MIN_CHECKED:
            print(NO_SPEECH % (checked, len(ts), MIN_CHECKED))
            sys.exit(3)
        print("worst |lag| %.1f ms over %d speaking windows -> CLOCKS AGREE" % (worst, checked))
        os.replace(part, out)
        print("output: video %.3f s | audio %.3f s  -> %s" % (do["video"][1], do["audio"][1], out))
    finally:
        if part and part.exists():  # never leave an unproven master behind
            part.unlink()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
