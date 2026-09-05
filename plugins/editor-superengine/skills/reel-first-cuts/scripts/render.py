#!/usr/bin/env python3
"""Stage 6 - render once, from the raw.

trim + atrim + concat + setpts/atempo in ONE filter graph. Never builds from an
intermediate: each lossy generation costs detail permanently, and a chain of more
than two is wrong.

  python render.py work/ RAW.mp4 --speed 1.15 --master --scrub

Master : source resolution, CRF 14 slow, keyframe every second
Scrub  : 1080p, CRF 20, keyframe every half second - for TIMING only, never picture

Dense GOP is not optional on anything a human will scrub. preset slow defaults to
a 250-frame GOP; seeks measured 678-1527ms and dragging the playhead felt dead.
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

FADE_IN, FADE_OUT = 0.012, 0.018   # click guards; they sit inside the pads


def die(m):
    print("ERROR: %s" % m, file=sys.stderr)
    raise SystemExit(2)


def build_graph(segs, speed, scale_to=None):
    """One filter graph for the whole cut. Written to a file, not the command
    line - 40+ segments blow past argument limits on every platform."""
    L = []
    for i, (a, b) in enumerate(segs):
        d = b - a
        L.append("[0:v]trim=start=%.4f:end=%.4f,setpts=PTS-STARTPTS[v%d];" % (a, b, i))
        L.append("[0:a]atrim=start=%.4f:end=%.4f,asetpts=PTS-STARTPTS,"
                 "afade=t=in:st=0:d=%.3f,afade=t=out:st=%.4f:d=%.3f[a%d];"
                 % (a, b, FADE_IN, max(0.0, d - FADE_OUT), FADE_OUT, i))
    join = "".join("[v%d][a%d]" % (i, i) for i in range(len(segs)))
    tail = []
    if abs(speed - 1.0) < 1e-9 and not scale_to:
        L.append(join + "concat=n=%d:v=1:a=1[v][a]" % len(segs))
    else:
        L.append(join + "concat=n=%d:v=1:a=1[vc][ac];" % len(segs))
        vf = []
        if abs(speed - 1.0) >= 1e-9:
            vf.append("setpts=PTS/%s" % speed)
        if scale_to:
            vf.append("scale=%d:%d:flags=lanczos" % scale_to)
        L.append("[vc]%s[v];" % ",".join(vf) if vf else "[vc]null[v];")
        # atempo preserves pitch; it accepts 0.5-2.0 per stage
        L.append("[ac]atempo=%s[a]" % speed if abs(speed - 1.0) >= 1e-9 else "[ac]anull[a]")
    return "\n".join(L + tail)


def encode(raw, graph_path, out, fps, fps_flag, crf, preset, gop, abitrate):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats", "-i", str(raw),
           "-filter_complex_script", str(graph_path), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
           "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
           "-pix_fmt", "yuv420p", fps_flag, "cfr", "-r", str(fps),
           "-c:a", "aac", "-b:a", abitrate, "-movflags", "+faststart", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        die("encode failed:\n%s" % p.stderr.strip()[-1500:])
    return p.stderr


def probe_out(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-show_entries",
                        "stream=width,height,nb_frames", "-of", "json", str(path)],
                       capture_output=True, text=True)
    return json.loads(p.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("raw")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--master", action="store_true")
    ap.add_argument("--scrub", action="store_true")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        die("ffmpeg not on PATH")
    work = Path(a.work)
    segs = json.loads((work / "segments.json").read_text(encoding="utf-8"))
    probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
    fps = probe["out_rate"]
    fps_flag = probe.get("fps_flag", "-fps_mode")
    if not (a.master or a.scrub):
        a.master = a.scrub = True

    tag = a.tag or ("%.2fx" % a.speed).replace(".", "")
    expected = sum(b - x for x, b in segs) / a.speed
    outdir = work / "renders"
    outdir.mkdir(exist_ok=True)
    print("segments %d | expected runtime %.2fs at %.2fx" % (len(segs), expected, a.speed))

    results = []
    if a.master:
        g = work / ("_graph-master-%s.txt" % tag)
        g.write_text(build_graph(segs, a.speed), encoding="utf-8")
        out = outdir / ("master-%s.mp4" % tag)
        encode(a.raw, g, out, fps, fps_flag, 14, "slow", int(round(fps)), "192k")
        results.append(("master", out))
    if a.scrub:
        g = work / ("_graph-scrub-%s.txt" % tag)
        g.write_text(build_graph(segs, a.speed, scale_to=(1920, 1080)), encoding="utf-8")
        out = outdir / ("scrub-%s.mp4" % tag)
        encode(a.raw, g, out, fps, fps_flag, 20, "veryfast", max(1, int(round(fps / 2))), "160k")
        results.append(("scrub", out))

    print()
    for kind, out in results:
        info = probe_out(out)
        dur = float(info["format"]["duration"])
        st = info["streams"][0]
        drift = dur - expected
        # Each segment can round up to one frame, so tolerance scales with the
        # segment count. A flat threshold flags normal quantisation as a fault.
        tol = max(0.25, len(segs) / fps * 0.6)
        flag = "  <- DRIFT beyond quantisation" if abs(drift) > tol else ""
        print("%-7s %s" % (kind, out.name))
        print("        %sx%s  %.3fs  (expected %.2f, drift %+.3f)%s"
              % (st.get("width"), st.get("height"), dur, expected, drift, flag))
    print()
    print("Frame-quantisation drift of a few hundred ms across many segments is normal.")
    print("Judge PACING on the scrub copy at ship speed. Judge PICTURE only on the master.")


if __name__ == "__main__":
    main()
