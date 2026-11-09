"""Precompute the waveform peaks the Sound Board draws.

  make_waveforms.py --dir <reel folder> --video <picture-locked video>

Reads the video's sound and every file in <dir>/beds, writes <dir>/waveforms.json. 20 bins per second, each bin the
largest sample in that window, scaled per file so a quiet bed still draws a readable shape.
"""
import argparse, os, struct, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import ffmpeg, write_json  # noqa: E402

SR = 8000
BINS_PER_S = 20
SAMPLES_PER_BIN = SR // BINS_PER_S


def peaks(path):
    p = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-map", "0:a:0",
                        "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True)
    if p.returncode != 0:
        raise SystemExit("Couldn't read the sound in %s: %s" % (Path(path).name, p.stderr.decode(errors="replace")[:300]))
    raw = p.stdout
    n = len(raw) // 2
    if n == 0:
        raise SystemExit("There is no sound in %s." % Path(path).name)
    vals = struct.unpack("<%dh" % n, raw[:n * 2])
    out = []
    for i in range(0, n, SAMPLES_PER_BIN):
        chunk = vals[i:i + SAMPLES_PER_BIN]
        out.append(max(abs(v) for v in chunk) if chunk else 0)
    mx = max(out) or 1
    return [round(v / mx, 3) for v in out], round(n / SR, 3)


def make(root, video):
    root = Path(root)
    v, dur = peaks(video)
    data = {"bins_per_s": BINS_PER_S, "voice": {"peaks": v, "duration": dur}, "beds": {}}
    print("voice: %d bins, %.3fs" % (len(v), dur))
    bed_dir = root / "beds"
    if bed_dir.is_dir():
        for name in sorted(os.listdir(bed_dir)):
            if name.lower().endswith((".mp3", ".wav")):
                pk, d = peaks(bed_dir / name)
                data["beds"][name] = {"peaks": pk, "duration": d}
                print("%s: %d bins, %.3fs" % (name, len(pk), d))
    write_json(root / "waveforms.json", data, indent=None)
    return data


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Waveform peaks for the Sound Board.")
    ap.add_argument("--dir", required=True, help="the reel folder")
    ap.add_argument("--video", required=True, help="the picture-locked video")
    a = ap.parse_args(argv)
    make(a.dir, a.video)
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
