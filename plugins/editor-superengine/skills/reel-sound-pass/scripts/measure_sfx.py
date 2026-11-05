"""Measure every sound file a board uses: duration, peak, RMS, integrated loudness for music beds, and for sound
effects peak_s, where the hit lands (seconds from the file start).

  measure_sfx.py --dir <reel folder>

Reads <dir>/sfx and <dir>/beds, writes <dir>/sfx_measured.json.

Why this exists: sound libraries are not level matched, and written duration tables go stale. Everything here
comes from the file. Peak uses astats, not volumedetect, because volumedetect clamps float and reads an overshoot
as -0.0 dB. peak_s is the centre of the file's loudest 10 ms (3 decimals): the board and the bake start the file
peak_s before the cue's time, so the hit lands on it.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import SR, decode, ffmpeg, ffprobe, write_json  # noqa: E402

SOUND_EXT = (".mp3", ".wav")


def run(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def duration(path):
    txt = run([ffprobe(), "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).strip()
    try:
        return round(float(txt.splitlines()[0]), 3)
    except (ValueError, IndexError):
        return None


def levels(path, want_lufs):
    txt = run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path),
               "-af", "astats=measure_overall=Peak_level+RMS_level:measure_perchannel=none",
               "-f", "null", "-"])
    peak = rms = None
    m = re.search(r"Peak level dB:\s*(-?[\d.]+|-?inf)", txt)
    if m and m.group(1) != "-inf":
        peak = round(float(m.group(1)), 2)
    m = re.search(r"RMS level dB:\s*(-?[\d.]+|-?inf)", txt)
    if m and m.group(1) != "-inf":
        rms = round(float(m.group(1)), 2)
    lufs = None
    if want_lufs:
        # the LAST match: ffmpeg prints running values before the summary
        found = re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path),
                                                           "-af", "ebur128=peak=true", "-f", "null", "-"]))
        if found:
            lufs = round(float(found[-1]), 1)
    return peak, rms, lufs


def peak_time(path):
    """Seconds from the file start to the centre of its loudest 10 ms, 3 decimals; None when it can't be read."""
    try:
        e = (decode(path).astype(np.float64) ** 2).sum(1)
    except RuntimeError:
        return None
    w = int(0.010 * SR)
    if len(e) <= w:
        return round(len(e) / 2 / SR, 3)
    c = np.concatenate([[0.0], np.cumsum(e)])
    return round((int(np.argmax(c[w:] - c[:-w])) + w / 2) / SR, 3)


def measure(path, want_lufs=False):
    peak, rms, lufs = levels(path, want_lufs)
    row = {"file": Path(path).name, "duration": duration(path), "peak_dbfs": peak, "rms_dbfs": rms}
    if want_lufs:
        row["lufs"] = lufs
    else:
        row["peak_s"] = peak_time(path)
    return row


def scan(folder, want_lufs):
    rows = []
    if not os.path.isdir(folder):
        return rows
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(SOUND_EXT):
            row = measure(os.path.join(folder, name), want_lufs)
            rows.append(row)
            print("  %-34s %7ss  peak %7s  rms %7s%s" % (name, row["duration"], row["peak_dbfs"], row["rms_dbfs"],
                                                         ("  I %6s" % row["lufs"]) if want_lufs else ""))
    return rows


def measure_dir(root):
    root = Path(root)
    print("Sound effects")
    hits = scan(root / "sfx", want_lufs=False)
    print("Music beds")
    beds = scan(root / "beds", want_lufs=True)
    write_json(root / "sfx_measured.json", {"hits": hits, "beds": beds})
    print("Measured %d sound effects and %d music beds." % (len(hits), len(beds)))
    quiet = [h for h in hits if h["peak_dbfs"] is not None and h["peak_dbfs"] < -6]
    if quiet:
        print("Quiet masters (peak under -6 dBFS; mixing can't rescue them, they need a louder copy):")
        for h in quiet:
            print("  %-34s peak %s dBFS" % (h["file"], h["peak_dbfs"]))
    return {"hits": hits, "beds": beds}


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Measure the sound effects and music beds in a reel folder.")
    ap.add_argument("--dir", required=True, help="the reel folder (its sfx/ and beds/)")
    measure_dir(ap.parse_args(argv).dir)
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
