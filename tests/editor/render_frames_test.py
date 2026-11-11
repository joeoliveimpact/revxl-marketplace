#!/usr/bin/env python3
"""Frame-count matrix for the first-cut render: every source rate x every Cut Board speed.

usage: python tests/editor/render_frames_test.py <scratch-dir> [--plugin <plugin root>]
                                                 [--rates 25,30] [--speeds 1.15]
For each pair it makes a small silent-safe synthetic clip (test picture + a quiet tone; nothing is
played), cuts it with gaps.snap_cuts at several lengths, builds the graph with render.build_graph and
encodes it with render.encode. It then asserts, per cut:
  - the rendered frame count equals cuts.json's last out_out_f (the check render.py itself dies on)
  - the duration is frames / fps
  - the sound and the picture end together (within one frame)
  - the last frame is real picture, not a black or repeated pad (it differs from the frame before it)
One more case pins a known limit: when a recording's picture starts after its sound (0.5 s here), the cut
keeps the exact frame count and the sound stays in step, and the first picture is held for the gap.
Prints PASS/FAIL per pair; exit 0 = every pair passed. --plugin runs it against another tree.
Light job: 180x320 clips of a few seconds. Tools come from the editor state folder (EDITOR_SE_HOME).
"""
import argparse, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RATES = ["24000/1001", "24", "25", "30000/1001", "30", "50", "60000/1001", "60"]
SPEEDS = [1.0, 1.1, 1.15, 1.2]     # make_board.py speed_options
OUT_RATE = 30.0                    # probe.py --out-rate default: the master's fps
# Kept pieces in seconds, ending at awkward times; each list is one cut. The totals step through
# neighbouring frame counts so every rounding case of total/speed is met, ties included.
CUTS = [[[0.31 + k * 0.007, 1.07], [1.52 + k * 0.011, 2.33], [2.9, 3.0 + k / 30.0]] for k in range(0, 9)]
# One-piece cuts of 57..62 frames: 57/1.2 is exactly 47.5, the tie the cut list and ffmpeg round differently.
CUTS += [[[0.3, 0.3 + s / 30.0]] for s in range(57, 63)]
fails = []


def load(plugin, name):
    path = plugin / "skills" / "reel-first-cuts" / "scripts" / name
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(plugin / "skills" / "_shared"))
    spec = importlib.util.spec_from_file_location(name[:-3] + "_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=600)


def stream_end(render, path, kind):
    p = run([render.FFPROBE, "-v", "error", "-select_streams", kind + ":0", "-show_entries",
             "stream=start_time,duration", "-of", "json", path])
    s = json.loads(p.stdout)["streams"][0]
    return float(s.get("start_time") or 0) + float(s["duration"])


def last_two_differ(render, path, frames, folder):
    """The final frame must be new picture: testsrc2 changes every source frame, so a pad would repeat."""
    if frames < 2:
        return True
    out = folder / "tail-%d.raw"
    p = run([render.FFMPEG, "-y", "-v", "error", "-i", path, "-vf", "select=gte(n\\,%d)" % (frames - 2),
             "-fps_mode", "passthrough", "-f", "image2", "-pix_fmt", "gray", "-c:v", "rawvideo", out])
    a, b = folder / "tail-1.raw", folder / "tail-2.raw"
    if p.returncode or not (a.exists() and b.exists()):
        return False
    return hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest()


def late_start(render, gaps, S):
    """Known limit, pinned: the picture stream starts 0.5 s after the sound. The first picture is held for
    the gap (15 frames at the master rate), the count is exact and the sound and picture end together."""
    name, delay, w, h = "picture starting 0.5 s after the sound: exact frames, first picture held for the gap", 0.5, 180, 320
    pic, clip = S / "late-pic.mp4", S / "late.mp4"
    for cmd in ([render.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=%dx%d:r=30:d=4" % (w, h),
                 "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", pic],
                [render.FFMPEG, "-y", "-v", "error", "-itsoffset", delay, "-i", pic, "-f", "lavfi", "-i",
                 "sine=frequency=330:sample_rate=48000:duration=4.5", "-af", "volume=0.05", "-map", "0:v", "-map", "1:a",
                 "-c:v", "copy", "-c:a", "aac", clip]):
        p = run(cmd)
        if p.returncode:
            raise SystemExit("fixture ffmpeg failed: %s" % p.stderr[-800:])
    cuts = gaps.snap_cuts([[0.0, 1.5]], OUT_RATE, 1.0)
    want, bad = cuts["segments"][-1]["out_out_f"], []
    graph, out = S / "graph.txt", S / "out.mp4"
    graph.write_text(render.build_graph(cuts, 48000, "null"), encoding="utf-8")
    try:
        render.encode(clip, graph, out, OUT_RATE, "-fps_mode", 30, "ultrafast", 30, "64k")
    except SystemExit:
        bad.append("the encode failed")
    if not bad:
        raw = subprocess.run([str(render.FFMPEG), "-v", "error", "-i", str(out), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, timeout=600).stdout
        frames = [raw[i:i + w * h] for i in range(0, len(raw), w * h)]
        # A held picture survives the encode almost unchanged; a new one moves well over 1% of the pixels.
        moved = lambda f: sum(1 for a, b in zip(f, frames[0]) if abs(a - b) > 24) * 1000 // (w * h) >= 5
        held = next((i for i, f in enumerate(frames) if moved(f)), len(frames)) if frames else 0
        gap = round(delay * OUT_RATE)
        v_end, a_end = stream_end(render, out, "v"), stream_end(render, out, "a")
        if len(frames) != want:
            bad.append("%d frames, cut list says %d" % (len(frames), want))
        elif not gap <= held <= gap + 2:
            bad.append("the first picture shows for %d frames, expected about %d (the gap, then itself)" % (held, gap + 1))
        elif abs(a_end - v_end) > 1.0 / OUT_RATE:
            bad.append("sound ends at %.3fs, picture at %.3fs" % (a_end, v_end))
    print(("PASS " if not bad else "FAIL ") + name + ("" if not bad else "  [%s]" % "; ".join(bad)))
    if bad:
        fails.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--plugin", default=str(REPO / "plugins" / "editor-superengine"))
    ap.add_argument("--rates", default=",".join(RATES))
    ap.add_argument("--speeds", default=",".join(str(s) for s in SPEEDS))
    a = ap.parse_args()
    S, plugin = Path(a.scratch).resolve(), Path(a.plugin).resolve()
    S.mkdir(parents=True, exist_ok=True)
    render, gaps = load(plugin, "render.py"), load(plugin, "gaps.py")
    render.find_tools()
    print("plugin %s\nffmpeg %s" % (plugin, render.FFMPEG))
    for rate in a.rates.split(","):
        clip = S / ("src-%s.mp4" % rate.replace("/", "_"))
        p = run([render.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=180x320:r=%s:d=5" % rate,
                 "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:duration=5", "-af", "volume=0.05",
                 "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", clip])
        if p.returncode:
            raise SystemExit("fixture ffmpeg failed: %s" % p.stderr[-800:])
        for speed in [float(x) for x in a.speeds.split(",")]:
            bad = []
            for k, pieces in enumerate(CUTS):
                cuts = gaps.snap_cuts(pieces, OUT_RATE, speed)
                want = cuts["segments"][-1]["out_out_f"]
                graph, out = S / "graph.txt", S / "out.mp4"
                graph.write_text(render.build_graph(cuts, 48000, "null"), encoding="utf-8")
                try:
                    render.encode(clip, graph, out, OUT_RATE, "-fps_mode", 30, "ultrafast", 30, "64k")
                except SystemExit:
                    bad.append("cut %d: the encode failed" % k)
                    continue
                got = render.count_frames(out)
                v_end, a_end = stream_end(render, out, "v"), stream_end(render, out, "a")
                if got != want:
                    bad.append("cut %d: %d frames, cut list says %d" % (k, got, want))
                elif abs(v_end - want / OUT_RATE) > 0.002:
                    bad.append("cut %d: picture is %.3fs, cut list says %.3fs" % (k, v_end, want / OUT_RATE))
                elif abs(a_end - v_end) > 1.0 / OUT_RATE:
                    bad.append("cut %d: sound ends at %.3fs, picture at %.3fs" % (k, a_end, v_end))
                elif not last_two_differ(render, out, got, S):
                    bad.append("cut %d: the last frame repeats the one before it" % k)
            name = "source %s fps at %sx: frames, length and sound match the cut list" % (rate, speed)
            print(("PASS " if not bad else "FAIL ") + name + ("" if not bad else "  [%s]" % "; ".join(bad)))
            if bad:
                fails.append(name)
    late_start(render, gaps, S)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
