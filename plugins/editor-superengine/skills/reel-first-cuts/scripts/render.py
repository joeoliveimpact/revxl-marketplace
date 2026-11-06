#!/usr/bin/env python3
"""Stage 6 - render once, from the raw.

trim + atrim + concat + setpts/atempo in ONE filter graph. Never builds from an
intermediate: each lossy generation costs detail permanently, and a chain of more
than two is wrong.

The cut comes only from work/cuts.json (gaps.py writes it): whole frames at the
master's fps, and the speed. The rendered frame count must equal its last out_out_f.
With multiple takes, each raw is conformed from its own probe in the same one-encode graph.

  python render.py work/ RAW.mp4 --speed 1.15 --master --scrub
  python render.py work/ RAW.mp4 --grade videos/<reel>/grade.json   # the reel's grade, baked in the same encode

Master : 1080x1920, CRF 14 slow, keyframe every second
Scrub  : 1080x1920, CRF 20, keyframe every half second - for TIMING only, never picture

Both are conformed in the same encode: centre-cropped to 9:16, HLG/PQ tone-mapped to
SDR, tagged BT.709, cut from the audio stream probe.json names. The scrub then gets
the review page, work/cut-review.html.

Dense GOP is not optional on anything a human will scrub. preset slow defaults to
a 250-frame GOP; seeks measured 678-1527ms and dragging the playhead felt dead.
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import review_page
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

FADE_IN, FADE_OUT = 0.012, 0.018   # click guards; they sit inside the pads
CANVAS = (1080, 1920)              # every master is a 9:16 short
SETUP = "The editor's setup isn't finished: its video tools are missing. Run the editor setup (editor-doctor), then try again."
FFMPEG = FFPROBE = None


def die(m):
    print("ERROR: %s" % m, file=sys.stderr)
    raise SystemExit(2)


def find_tools():
    """ffmpeg/ffprobe come from the editor's install (_shared/runtime.py), never PATH. Looked up on first use,
    so the helpers below also work when another script imports them."""
    global FFMPEG, FFPROBE
    if FFMPEG:
        return
    try:
        ffmpeg, ffprobe = rt.tool("ffmpeg"), rt.tool("ffprobe")
    except (KeyError, OSError, ValueError):
        die(SETUP)
    if not (Path(ffmpeg).exists() and Path(ffprobe).exists()):
        die(SETUP)
    FFMPEG, FFPROBE = ffmpeg, ffprobe


def conform(video, crop=None):
    """9:16 at 1080x1920, and HDR to SDR, inside the encode the cut already does.

    Scale to cover, then crop exact: the crop never asks x264 for an odd width (a
    2160-tall source cut straight to 9:16 is 1215 wide, and x264 writes 0 frames).
    The crop is centred; ffmpeg has already applied a phone's rotation by here.

    HLG/PQ: linearise at 100 nits, BT.2020 -> BT.709, then mobius, which keeps
    in-range colour and rolls off only what lies above SDR white. HLG is relative,
    so its peak IS SDR white (peak=1); PQ keeps its real peak. hable fails only
    without peak=1, where it darkens in-range colour far past the known-colour
    tolerance (max dE 23.8 vs 5.0 on S2's planted HLG patches, 11.04.26); with
    peak=1 it passes (3.9), but mobius sits closer (1.2), so mobius is used."""
    f = ["scale=%d:%d:force_original_aspect_ratio=increase:force_divisible_by=2:flags=lanczos"
         % CANVAS, "crop=%d:%d" % CANVAS, "setsar=1"]
    if crop is not None:
        import importlib.util
        path = Path(__file__).resolve().parents[2] / "reel-canvas-build" / "scripts" / "face_crop.py"
        spec = importlib.util.spec_from_file_location("face_crop", path)
        face = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(face)
        try:
            width = face.cover_scaled_width(video)
            if crop["scaled_w"] != width:
                print("note: The face crop was measured on a different source; keeping the centred crop.")
            elif type(crop.get("x")) is not int or crop["x"] % 2 or not 0 <= crop["x"] <= width - CANVAS[0]:
                die("work/crop.json needs an even crop x inside the scaled picture; run the face crop step again")
            else:
                f[1] += ":%d:0" % crop["x"]
        except (KeyError, TypeError, ValueError):
            die("work/crop.json or the source picture size is incomplete; run the face crop step again")
    f += tonemap(video)
    return ",".join(f)


def tonemap(video):
    """S2's HDR-to-SDR filters, shared with own-clip B-roll ingest."""
    f = []
    tr = (video or {}).get("color_transfer")
    if tr in ("arib-std-b67", "smpte2084"):
        f += ["zscale=t=linear:npl=100", "format=gbrpf32le", "zscale=p=bt709",
              "tonemap=tonemap=mobius:desat=0" + (":peak=1" if tr == "arib-std-b67" else ""),
              "zscale=t=bt709:m=bt709:r=tv", "format=yuv420p"]
    return f


def grade_filter(grade_json):
    """--grade: ONE lut3d, the cube grade.json names (its path is relative to the reel folder, grade.json's own),
    added after the conform, so the graded plate comes from the raw in the same one generation. A cube whose sha256
    isn't grade.json's cube_sha is refused before anything renders. The path is quoted the way reel-grade's
    apply_grade.py quotes it: forward slashes, the drive colon escaped, the whole path single-quoted. The lut3d gets
    16-bit planar RGB: left to pick its own, ffmpeg hands it packed rgb24, and that round trip alone darkens every
    colour by 2-3 levels (an identity cube moved mid-grey 128 to 125 on ffmpeg 8.1.2; through gbrp16le, 0 levels)."""
    g = Path(grade_json)
    try:
        doc = json.loads(g.read_text(encoding="utf-8"))
        cube, sha = (g.parent / doc["cube"]).resolve(), doc["cube_sha"]
    except (OSError, ValueError, KeyError, TypeError):
        die("%s isn't a saved grade (it needs a cube and its cube_sha): save the grade in reel-grade, then render again" % g)
    if not cube.is_file():
        die("the grade's cube %s is missing: save the grade in reel-grade again, then render again" % cube)
    if hashlib.sha256(cube.read_bytes()).hexdigest() != sha:
        die("the grade's cube %s doesn't match grade.json (it changed after the grade was saved), so nothing was "
            "rendered: save the grade in reel-grade again, then render again" % cube.name)
    p = str(cube)
    if "'" in p:
        die("the cube's folder path has an apostrophe, which ffmpeg can't read: %s. Move it, then render again." % p)
    return "format=gbrp16le,lut3d=file='" + p.replace("\\", "/").replace(":", "\\:") + "'"


def video_cut(segment, fps):
    """Keep whole source frames before joining; speed belongs only after concat."""
    return ("trim=start=%r:end=%r,setpts=PTS-STARTPTS,fps=%r,trim=end_frame=%d"
            % (segment["src_in_f"] / fps, segment["src_out_f"] / fps, fps,
               segment["src_out_f"] - segment["src_in_f"]))


def audio_cut(segment, fps, sr):
    """Trim samples at the same frame times, with the single-take click guards."""
    a, b = segment["src_in_f"] / fps, segment["src_out_f"] / fps
    d = (segment["src_out_f"] - segment["src_in_f"]) / fps
    return ("atrim=start_sample=%d:end_sample=%d,asetpts=PTS-STARTPTS,"
            "afade=t=in:st=0:d=%.3f,afade=t=out:st=%.4f:d=%.3f"
            % (round(a * sr), round(b * sr), FADE_IN, max(0.0, d - FADE_OUT), FADE_OUT))


def joined_tail(count, fps, speed, vfilter="null", audio=True):
    """Join the source-length pieces, then apply the proven single-take speed tail."""
    join = "".join(("[v%d][a%d]" % (i, i)) if audio else "[v%d]" % i for i in range(count))
    lines = [join + ("concat=n=%d:v=1:a=1[vc][ac];" % count if audio else
                     "concat=n=%d:v=1:a=0[vc];" % count)]
    vf = ["setpts=PTS/%r" % speed, "fps=%r" % fps] if abs(speed - 1.0) >= 1e-9 else []
    lines.append("[vc]%s[v]" % ",".join(vf + [vfilter]) + (";" if audio else ""))
    if audio:
        # atempo preserves pitch; it accepts 0.5-2.0 per stage
        lines.append("[ac]atempo=%r[a]" % speed if abs(speed - 1.0) >= 1e-9 else "[ac]anull[a]")
    return lines


def build_graph(cuts, sr, vfilter, astream=0):
    """One filter graph for the whole cut, from cuts.json. Written to a file, not the
    command line - 40+ segments blow past argument limits on every platform.

    F-3: each segment is trimmed at frames/fps exactly and re-timed by fps= to whole
    frames, so it carries exactly src_out_f - src_in_f frames on a CFR or a VFR source.
    The speed change re-times the joined cut once (fps= again), which lands it on the
    cumulative out frames. F-15: the audio is trimmed in samples at the same frame
    times, so each segment's audio is as long as its picture and concat never pads."""
    if len(cuts.get("takes") or {}) > 1:
        return build_mixed_graph(cuts, sr, vfilter, astream)
    fps, speed, segs, L = cuts["fps"], cuts["speed"], cuts["segments"], []
    for i, s in enumerate(segs):
        L.append("[0:v]%s[v%d];" % (video_cut(s, fps), i))
        L.append("[0:a:%d]%s[a%d];" % (astream, audio_cut(s, fps, sr), i))
    L.extend(joined_tail(len(segs), fps, speed, vfilter))
    return "\n".join(L)


def build_mixed_graph(cuts, sr, filters, astreams):
    """Conform each raw once, split to its pieces, resample all audio to the first take's rate."""
    fps, speed, segs, lines = cuts["fps"], cuts["speed"], cuts["segments"], []
    for index, n in enumerate(sorted(cuts["takes"], key=int)):
        indices = [i for i, s in enumerate(segs) if str(s.get("take", 1)) == n]
        if not indices:
            continue
        vf = filters[n] if isinstance(filters, dict) else filters
        stream = astreams[n] if isinstance(astreams, dict) else astreams
        lines.append("[%d:v]%s,split=%d%s;" % (index, vf, len(indices),
                     "".join("[sv%d]" % i for i in indices)))
        lines.append("[%d:a:%d]aresample=%d,aformat=channel_layouts=stereo,asplit=%d%s;" %
                     (index, stream, sr, len(indices), "".join("[sa%d]" % i for i in indices)))
        for i in indices:
            s = segs[i]
            lines.append("[sv%d]%s[v%d];" % (i, video_cut(s, fps), i))
            lines.append("[sa%d]%s[a%d];" % (i, audio_cut(s, fps, sr), i))
    lines.extend(joined_tail(len(segs), fps, speed))
    return "\n".join(lines)


def mixed_inputs(cuts, raw):
    """Keep take numbers; the lowest numbered used take supplies the positional raw."""
    sources = [cuts["takes"][n]["raw"] for n in sorted(cuts["takes"], key=int)]
    if os.path.normcase(os.path.abspath(raw)) != os.path.normcase(os.path.abspath(sources[0])):
        die("the positional raw must match the first take's raw in cuts.json")
    return sources


def footage_guard(work, cuts, raw):
    """Legacy single-take reels without a ledger never invoke the footage check."""
    work = Path(work).resolve()
    reel = next((p for p in (work.parent, *work.parent.parents) if (p / "footage/ledger.json").exists()
                 or (p / "cut-board.config.json").exists()), work.parent)
    mixed = len(cuts.get("takes") or {}) > 1
    if not mixed and not (reel / "footage/ledger.json").exists():
        return
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared/checks"))
    import footage_check
    if mixed and not (reel / "footage/ledger.json").exists():
        die("log the recordings first: footage_check.py add <reel_dir> <path> --role aroll --origin own --licence own")
    blocks = footage_check.check(reel, footage_check.cut_uses(cuts, raw))
    if blocks:
        for line in blocks:
            print(line, file=sys.stderr)
        raise SystemExit(3)


def sample_rate(raw, astream):
    find_tools()
    p = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a:%d" % astream, "-show_entries",
                        "stream=sample_rate", "-of", "csv=p=0", str(raw)], capture_output=True, text=True)
    try:
        return int(p.stdout.split()[0])
    except (IndexError, ValueError):
        die("could not read the sample rate of audio stream %d in %s" % (astream, raw))


def count_frames(path):
    find_tools()
    p = subprocess.run([FFPROBE, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return int(p.stdout.strip().split(",")[0])
    except ValueError:
        return -1


def encode(raw, graph_path, out, fps, fps_flag, crf, preset, gop, abitrate):
    find_tools()
    inputs = raw if isinstance(raw, (list, tuple)) else [raw]
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-stats"]
    for source in inputs:
        cmd += ["-i", str(source)]
    cmd += [
           "-/filter_complex", str(graph_path), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
           "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
           "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-colorspace", "bt709", "-color_range", "tv", fps_flag, "cfr", "-r", str(fps),
           "-c:a", "aac", "-b:a", abitrate, "-movflags", "+faststart", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        die("encode failed: %s" % " ".join(p.stderr.strip().splitlines())[-1500:])
    return p.stderr


def probe_out(path):
    find_tools()
    p = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "format=duration", "-show_entries",
                        "stream=width,height,nb_frames", "-of", "json", str(path)],
                       capture_output=True, text=True)
    return json.loads(p.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("raw")
    ap.add_argument("--speed", type=float, default=None, help="must match cuts.json's speed (gaps.py --speed)")
    ap.add_argument("--master", action="store_true")
    ap.add_argument("--scrub", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--grade", default=None, help="videos/<reel>/grade.json: bake its cube into this render (one lut3d)")
    a = ap.parse_args()
    ensure_utf8_output()

    find_tools()
    work = Path(a.work)
    if not (work / "cuts.json").exists():
        die("work/cuts.json is missing: run gaps.py first")
    cuts = json.loads((work / "cuts.json").read_text(encoding="utf-8"))
    speed, fps = cuts["speed"], cuts["fps"]
    if a.speed is not None and abs(a.speed - speed) > 1e-9:
        die("--speed %s differs from cuts.json's speed %s: run gaps.py with --speed %s first" % (a.speed, speed, a.speed))
    if not cuts["segments"]:
        die("cuts.json has no segments")
    mixed = len(cuts.get("takes") or {}) > 1
    inputs = a.raw
    if mixed:
        inputs = mixed_inputs(cuts, a.raw)
    footage_guard(work, cuts, a.raw)
    segs = [(s["src_in_f"] / fps, s["src_out_f"] / fps) for s in cuts["segments"]]
    frames = cuts["segments"][-1]["out_out_f"]
    reel = work.resolve().parent
    probes = {n: json.loads((reel / t["work"] / "probe.json").read_text(encoding="utf-8"))
              for n, t in cuts["takes"].items()} if mixed else {}
    probe = probes[min(probes, key=int)] if mixed else json.loads((work / "probe.json").read_text(encoding="utf-8"))
    crop = None
    if (work / "crop.json").exists():
        try:
            crop = json.loads((work / "crop.json").read_text(encoding="utf-8"))
            if not isinstance(crop, dict):
                die("work/crop.json needs a crop object; run the face crop step again")
        except (OSError, ValueError):
            die("work/crop.json can't be read; run the face crop step again")
    fps_flag = probe.get("fps_flag", "-fps_mode")
    if mixed:
        if crop is not None:
            print("note: The face crop applies to take 1 only; the other recordings use a centred crop.")
        vfilter = {n: conform(p.get("video"), crop if n == "1" else None) for n, p in probes.items()}
        if a.grade:
            grade = grade_filter(a.grade)
            vfilter = {n: v + "," + grade for n, v in vfilter.items()}
        astream = {n: int(p.get("audio_stream", 0)) for n, p in probes.items()}
    else:
        vfilter = conform(probe.get("video"), crop) if crop is not None else conform(probe.get("video"))
        if a.grade:
            vfilter += "," + grade_filter(a.grade)
        astream = int(probe.get("audio_stream", 0))
    sr = sample_rate(a.raw, astream[min(probes, key=int)] if mixed else astream)
    if not (a.master or a.scrub):
        a.master = a.scrub = True

    tag = a.tag or ("%.2fx" % speed).replace(".", "")
    expected = frames / fps
    outdir = work / "renders"
    outdir.mkdir(exist_ok=True)
    print("segments %d | %d frames, %.2fs at %.2fx" % (len(segs), frames, expected, speed))

    results = []
    if a.master:
        g = work / ("_graph-master-%s.txt" % tag)
        g.write_text(build_graph(cuts, sr, vfilter, astream), encoding="utf-8")
        out = outdir / ("master-%s.mp4" % tag)
        encode(inputs, g, out, fps, fps_flag, 14, "slow", int(round(fps)), "192k")
        results.append(("master", out))
    if a.scrub:
        g = work / ("_graph-scrub-%s.txt" % tag)
        g.write_text(build_graph(cuts, sr, vfilter, astream), encoding="utf-8")
        out = outdir / ("scrub-%s.mp4" % tag)
        encode(inputs, g, out, fps, fps_flag, 20, "veryfast", max(1, int(round(fps / 2))), "160k")
        results.append(("scrub", out))

    print()
    for kind, out in results:
        info = probe_out(out)
        dur = float(info["format"]["duration"])
        st = info["streams"][0]
        got = count_frames(out)
        print("%-7s %s" % (kind, out.name))
        print("        %sx%s  %.3fs  %d frames (cuts.json: %d)" % (st.get("width"), st.get("height"), dur, got, frames))
        # F-3: the cut list is exact, so the frame count is too. A mismatch is a failure, never a warning.
        if got != frames:
            die("%s has %d frames but cuts.json says %d: the render does not match the cut list"
                % (out.name, got, frames))
    page = review_page.write(work, a.raw, results[-1][1], segs, speed)
    print("review page: %s" % page)
    print()
    print("Judge PACING on the scrub copy at ship speed. Judge PICTURE only on the master.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        die("the render could not finish: " + str(e).splitlines()[0])
