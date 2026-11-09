#!/usr/bin/env python3
# Changed from shorts-studio scripts/sync.py (MIT): editor media tools and helpers, UTF-8 and plain failures.
"""Use the picture from one recording and the sound from another, in time.

<editor python> -X utf8 -I sync.py --video camera.mov --audio microphone.mov --out work
Writes synced.mp4, screen.mp4 when the microphone file has video, and sync.json.
A match below 0.3 stops before encoding: the files probably are not the same take.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "reel-sound-pass/scripts"))
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output


def main():
    ensure_utf8_output()
    from _sync import load, env_db, lag_ms, SR
    import _media
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video", required=True, help="the file whose picture you want, usually the camera")
    ap.add_argument("--audio", required=True, help="the file whose sound you want, usually the good microphone")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-offset", type=float, default=60, help="largest start difference to search, seconds")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cam, mic = load(a.video), load(a.audio)
    lag, score = lag_ms(env_db(cam), env_db(mic), int(a.max_offset * 1000))
    # Microphone time t + lag belongs with camera time t.
    off = lag / 1000.
    dv = _media.probe(a.video)["dur"]
    da = _media.probe(a.audio)["dur"]
    t_cam0 = max(0., -off)
    t_mic0 = t_cam0 + off
    length = min(dv - t_cam0, da - t_mic0)
    rep = dict(video=a.video, audio=a.audio, offset_s=round(off, 3), score=round(score, 3),
               camera_from=round(t_cam0, 3), screen_from=round(t_mic0, 3), length_s=round(length, 3))
    _media.write_json(out / "sync.json", rep)
    if score < .3:
        print("The voices do not match well (score %.2f). Are these two files the same take?" % score)
        return 2
    if length <= 0:
        raise ValueError("the recordings have no shared time after matching")
    enc = ["-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p"]
    subprocess.run([_media.ffmpeg(), "-v", "error", "-y", "-ss", "%.3f" % t_cam0, "-i", a.video,
                    "-ss", "%.3f" % t_mic0, "-i", a.audio, "-t", "%.3f" % length,
                    "-map", "0:v:0", "-map", "1:a:0", *enc, "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                    str(out / "synced.mp4")], check=True, capture_output=True)
    has_video = subprocess.check_output([_media.ffprobe(), "-v", "error", "-select_streams", "v",
                                        "-show_entries", "stream=index", "-of", "csv=p=0", a.audio]).strip()
    if has_video:
        subprocess.run([_media.ffmpeg(), "-v", "error", "-y", "-ss", "%.3f" % t_mic0, "-i", a.audio,
                        "-t", "%.3f" % length, "-an", *enc, str(out / "screen.mp4")], check=True, capture_output=True)
    # Check that the new sound lines up with the camera's original voice.
    chk, _ = lag_ms(env_db(cam[int(t_cam0 * SR):int((t_cam0 + min(length, 60)) * SR)]),
                    env_db(load(out / "synced.mp4")[:int(min(length, 60) * SR)]), 500)
    rep["check_lag_ms"] = chk
    _media.write_json(out / "sync.json", rep)
    print("synced: offset %+.3f s (match %.2f), %.1f s, check lag %d ms (%s) -> %s%s" %
          (off, score, length, chk, "OK" if abs(chk) <= 20 else "CHECK BY EAR", out / "synced.mp4",
           " + screen.mp4" if has_video else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("the recordings could not be synced: " + str(e).strip().splitlines()[0], file=sys.stderr)
        sys.exit(2)
