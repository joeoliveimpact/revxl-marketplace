"""Measure a face-centred conform crop, or head-band anchors for the cut's segments.

crop --work <reel>/work --take <video> [--engine auto|rvm|remove-background]
anchors --reel-dir <reel> [--engine ...]
--selftest runs pure checks, without video tools or matting.
Exit 0 done, 1 stopped by a check, 2 bad input. Successful commands end with JSON.
"""
import argparse
import json
import math
import shutil
import statistics
import subprocess
import sys
from collections import deque
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

ENGINES = ("auto", "rvm", "remove-background")
K = 6  # Consecutive copies per sample let recurrent matting settle.
BATCH = 90  # ffmpeg's select expression fails above ~100 eq() terms.
BOX_SHARE = .75  # taste: occupied-height share reserved for the head and neck.
# ponytail: A person-share box is cautious on wide shots; a real face/chin
# finder is the upgrade path (v0.3.0).


class Stop(Exception):
    """A plain-English stop with its exit code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def cover_scaled_width(video):
    """Width after autorotation and FFmpeg 8's cover scale, divisible by two.

    scale_eval.c rescales to the nearest multiple of force_divisible_by (ties
    up), then takes the maximum with the requested width. SAR is unchanged by
    this scale filter; only the coded dimensions and rotation affect its width.
    """
    w, h = int(video["width"]), int(video["height"])
    if w <= 0 or h <= 0:
        raise ValueError("the source picture width and height must be positive")
    if round(float(video.get("rotation", 0) or 0)) % 180:
        w, h = h, w
    return max(1080, ((1920 * w + h) // (2 * h)) * 2)


def crop_x(face_x, scaled_w):
    """Nearest even crop offset, bounded to the cover-scaled picture."""
    return max(0, min(scaled_w - 1080, 2 * round((face_x * scaled_w - 540) / 2)))


def sample_frames(cuts, prefix):
    """Three integer quarter points in each half-open source/output span."""
    return [(i, s[prefix + "_in_f"] + (s[prefix + "_out_f"] - s[prefix + "_in_f"]) * q // 4)
            for i, s in enumerate(cuts["segments"]) for q in (1, 2, 3)]


def settled_frames(count):
    """Proxy indices of the last copy of each original sample."""
    return [i * K + K - 1 for i in range(count)]


def batches(frames, size=BATCH):
    """Consecutive chunks of the sorted unique frame list."""
    return [frames[i:i + size] for i in range(0, len(frames), size)]


class HeadBand(tuple):
    """The existing (cx, cy) pair, with a head-and-neck frame-fraction box attached."""

    def __new__(cls, centre, box):
        point = super().__new__(cls, centre)
        point.box = box
        return point


def head_band(alpha, w, h):
    """Head-band centroid and box of the largest 4-connected component, or None.

    The reference is the row 10% down the occupied height. From there, stop
    before the first row wider than 1.6 times that row, or at 22% of occupied
    height. Counting starts at the first occupied row, including the head top.
    A band whose component pixels average less than 200 alpha is a ghost: None.
    The box covers 75% of occupied height, and at least the entire centroid
    band; it does not change the centroid band or use a shoulder-width stop.
    alpha is one flat, 8-bit plane (bytes, bytearray, or a sequence of ints).
    """
    if w <= 0 or h <= 0 or len(alpha) != w * h:
        raise ValueError("the alpha plane does not match its picture size")
    # Each pixel is scanned once and enqueued at most once: O(w*h) time.
    remaining = bytearray(a >= 128 for a in alpha)
    largest = []
    size = w * h
    for seed, occupied in enumerate(remaining):
        if not occupied:
            continue
        queue = deque([seed])
        remaining[seed] = 0
        component = []
        while queue:
            pixel = queue.popleft()
            component.append(pixel)
            x = pixel % w
            for neighbor in (pixel - w if pixel >= w else -1,
                             pixel + w if pixel + w < size else -1,
                             pixel - 1 if x else -1,
                             pixel + 1 if x + 1 < w else -1):
                if neighbor >= 0 and remaining[neighbor]:
                    remaining[neighbor] = 0
                    queue.append(neighbor)
        if len(component) > len(largest):
            largest = component
    counts, sums, opacity = [0] * h, [0] * h, [0] * h
    for pixel in largest:
        y, x = divmod(pixel, w)
        counts[y] += 1
        sums[y] += x
        opacity[y] += alpha[pixel]
    if sum(counts) < w * h * .005:
        return None
    top = next(y for y, n in enumerate(counts) if n)
    bottom = next(y for y in range(h - 1, -1, -1) if counts[y])
    height = bottom - top + 1
    ref = min(bottom, top + height // 10)
    end = min(bottom + 1, top + max(1, math.ceil(height * .22)))
    for y in range(ref + 1, end):
        if counts[y] > 1.6 * counts[ref]:
            end = y
            break
    n = sum(counts[top:end])
    if sum(opacity[top:end]) < 200 * n:
        return None
    box_end = min(h, max(end, top + math.ceil(BOX_SHARE * height)))
    xs = [pixel % w for pixel in largest if top <= pixel // w < box_end]
    # Upper edges are exclusive so even a one-pixel band has a nonzero box.
    box = (min(xs) / w, top / h, (max(xs) + 1) / w, box_end / h)
    return HeadBand((sum(sums[top:end]) / n / w, sum(y * counts[y] for y in range(top, end)) / n / h), box)


def reject_outliers(samples, points):
    """Keep points within 0.15 of the reel's component-wise median; note every drop."""
    valid = [points[f] for _, f in samples if points[f] is not None]
    kept = dict(points)
    if not valid:
        return kept
    mx = statistics.median(p[0] for p in valid)
    my = statistics.median(p[1] for p in valid)
    for _, f in samples:
        point = points[f]
        if point is not None and math.hypot(point[0] - mx, point[1] - my) > .15:
            kept[f] = None
            print(f"note: Dropped face sample at frame {f}: farther than 0.15 from the reel's median head position.")
    return kept


def anchors_result(cuts, samples, points):
    groups = {}
    for seg, f in samples:
        point = points[f]
        if point is not None:
            groups.setdefault(seg, []).append({"f": f, "x": point[0], "y": point[1], "box": list(point.box)})
    return {"schema": 1, "fps": cuts["fps"], "segments": [
        {"seg": seg, "samples": pts} for seg, pts in sorted(groups.items())]}


def read_cuts(work, prefix):
    try:
        cuts = json.loads((work / "cuts.json").read_text(encoding="utf-8"))
        rate = Fraction(str(cuts["fps"]))
        segs = cuts["segments"]
        valid = rate > 0 and isinstance(segs, list) and bool(segs) and all(
            isinstance(s, dict) and all(type(s.get(prefix + k)) is int for k in ("_in_f", "_out_f"))
            and 0 <= s[prefix + "_in_f"] < s[prefix + "_out_f"] for s in segs)
        if not valid:
            raise ValueError("invalid spans")
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
        raise Stop(2, "The cut list work/cuts.json is missing or incomplete; make the cut first.") from None
    return cuts, str(rate)


def run_tool(tool, args, purpose):
    try:
        p = subprocess.run([rt.tool(tool), *args], capture_output=True, env=rt.python_env())
    except (KeyError, OSError, ValueError):
        raise Stop(1, f"The editor couldn't start {tool}; run editor-doctor, then try the face step again.") from None
    if p.returncode:
        raise Stop(1, f"The editor couldn't {purpose}; check the video and the editor's video tools.")
    return p.stdout


def probe_video(path):
    raw = run_tool("ffprobe", ["-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=width,height:stream_side_data=rotation", "-of", "json", str(path)],
                   f"read the picture size of {path.name}")
    try:
        st = json.loads(raw)["streams"][0]
        video = {"width": int(st["width"]), "height": int(st["height"]),
                 "rotation": next((d["rotation"] for d in st.get("side_data_list", []) if "rotation" in d), 0)}
        cover_scaled_width(video)  # reject unusable sizes before decoding
        return video
    except (ValueError, KeyError, IndexError, TypeError):
        raise Stop(1, f"The editor couldn't read the picture size of {path.name}.") from None


def measure(work, source, frames, rate, engine):
    """Repeat each unique frame K times; map settled mattes back by source number.

    Reordered or repeated source spans still get the correct segment samples.
    The private face folder is removed even when extraction or matting stops.
    """
    scratch = work / "render-tmp" / "face"
    if not scratch.resolve().is_relative_to(work.resolve()) or scratch.exists() or scratch.is_symlink():
        raise Stop(1, "The face scratch folder is already in use or outside this reel; clear it before trying again.")
    scratch.mkdir(parents=True)
    try:
        unique = sorted(set(frames))
        points = {}
        for i, chunk in enumerate(batches(unique)):
            folder = scratch / str(i)
            folder.mkdir()
            clip, matte = folder / "samples.mp4", folder / "matte.mov"
            copies = "".join(f"[copy{i}]" for i in range(K))
            # Equal timestamps on the split streams interleave as K consecutive
            # copies of each sample; reset PTS afterwards for the CFR proxy clip.
            vf = ("[0:v:0]select='" + "+".join(f"eq(n,{f})" for f in chunk) + "',"
                  f"setpts=N/(({rate})*TB),scale=540:-2,setsar=1,split={K}{copies};"
                  f"{copies}interleave=nb_inputs={K}:duration=longest,setpts=N/(({rate})*TB)[samples]")
            graph = folder / "select.txt"
            graph.write_bytes(vf.encode("utf-8"))
            run_tool("ffmpeg", ["-v", "error", "-y", "-i", str(source), "-an", "-sn", "-dn",
                     "-/filter_complex", str(graph), "-map", "[samples]", "-fps_mode", "cfr", "-r", rate,
                     "-c:v", "libx264", "-preset", "fast",
                     "-crf", "10", "-pix_fmt", "yuv420p", str(clip)], "extract the face sample frames")
            try:
                p = subprocess.run([sys.executable, "-X", "utf8", "-I", str(HERE / "cutout.py"), str(clip), str(matte),
                                    "--engine", engine, "--tmp", str(folder)], capture_output=True, env=rt.python_env())
            except OSError:
                raise Stop(1, "The editor couldn't start the cutout step; check its Python setup.") from None
            if p.returncode:
                raise Stop(1, "The cutout step couldn't matte the face samples; check its setup and try again.")
            try:
                summary = json.loads(p.stdout.decode("utf-8").strip().splitlines()[-1])
                used = summary["engine"]
                if used not in ENGINES[1:] or summary["frames"] != len(chunk) * K:
                    raise ValueError("cutout frame count or engine differs")
            except (ValueError, KeyError, IndexError, TypeError):
                raise Stop(1, "The cutout step didn't return every sample frame and its matting engine; nothing was written.") from None
            if i == 0:
                engine = used
            video = probe_video(matte)
            w, h = video["width"], video["height"]
            points.update(read_alpha(matte, w, h, chunk, folder))
        return points, engine
    finally:
        shutil.rmtree(scratch)


def read_alpha(matte, w, h, frames, scratch):
    """Read only each group's last gray alpha plane, one plane at a time."""
    points = {}
    graph = scratch / "alpha.txt"
    graph.write_bytes(("select='" + "+".join(f"eq(n,{f})" for f in settled_frames(len(frames)))
                       + "',alphaextract").encode("utf-8"))
    with (scratch / "alpha.log").open("wb") as err:
        try:
            dec = subprocess.Popen([rt.tool("ffmpeg"), "-v", "error", "-i", str(matte), "-map", "0:v:0",
                                    "-/filter:v", str(graph), "-pix_fmt", "gray", "-fps_mode", "passthrough",
                                    "-f", "rawvideo", "-"],
                                   stdout=subprocess.PIPE, stderr=err, env=rt.python_env())
        except (KeyError, OSError, ValueError):
            raise Stop(1, "The editor couldn't start the alpha reader; check its video tools.") from None
        try:
            for f in frames:
                alpha = dec.stdout.read(w * h)
                if len(alpha) != w * h:
                    raise Stop(1, "The face matte ended before every sample could be read; nothing was written.")
                points[f] = head_band(alpha, w, h)
            if dec.stdout.read(1) or dec.wait():
                raise Stop(1, "The face matte didn't match the sample clip; nothing was written.")
        finally:
            dec.stdout.close()
            if dec.poll() is None:
                dec.kill()
            dec.wait()
    return points


def write_json(path, doc):
    # write_bytes keeps all JSON LF-only on Windows as well as macOS.
    data = (json.dumps(doc, indent=1, ensure_ascii=True) + "\n").encode("utf-8")
    path.write_bytes(data)


def execute(a):
    work = Path(a.work).resolve() if a.cmd == "crop" else Path(a.reel_dir).resolve() / "work"
    cuts, rate = read_cuts(work, "src" if a.cmd == "crop" else "out")
    if a.cmd == "crop":
        source = Path(a.take).resolve()
    else:
        masters = list((work / "renders").glob("master-*.mp4"))
        if not masters:
            raise Stop(2, "There's no cut master in work/renders; render the cut before measuring face anchors.")
        source = max(masters, key=lambda p: p.stat().st_mtime_ns)
    if not source.is_file():
        raise Stop(2, f"The source video {source.name} is missing; check the take path.")
    samples = sample_frames(cuts, "src" if a.cmd == "crop" else "out")
    video = probe_video(source) if a.cmd == "crop" else None
    points, engine = measure(work, source, [f for _, f in samples], rate, a.engine)
    points = reject_outliers(samples, points)
    if a.cmd == "crop":
        xs = [points[f][0] for _, f in samples if points[f] is not None]
        if not xs:
            (work / "crop.json").unlink(missing_ok=True)
            raise Stop(1, "No face matte was found in the sample frames; render will keep the centred crop.")
        face_x = statistics.median(xs)
        width = cover_scaled_width(video)
        doc = {"schema": 1, "x": crop_x(face_x, width), "scaled_w": width, "face_x": face_x,
               "samples": len(xs), "engine": engine, "measured_on": source.name}
        write_json(work / "crop.json", doc)
        if width == 1080:
            print("note: The source is already 9:16 or narrower; the horizontal crop stays at 0.")
        print(f"✓ Face crop: x {doc['x']} of {width}")
        print(json.dumps(doc))
    else:
        doc = anchors_result(cuts, samples, points)
        write_json(work / "anchors.json", doc)
        frames = sum(len(segment["samples"]) for segment in doc["segments"])
        print(f"Face anchors saved: {frames} frames -> {work / 'anchors.json'}")
    return 0


def selftest():
    import contextlib
    import io
    import random

    w, h, cx, cy = 240, 300, 175, 65
    alpha = bytes(255 if (x - cx) ** 2 + (y - cy) ** 2 <= 25 ** 2
                  or (90 <= y < 275 and abs(x - cx) <= 60) else 0 for y in range(h) for x in range(w))
    point = head_band(alpha, w, h)
    checks = [point is not None and abs(point[0] - cx / w) < .02 and abs(point[1] - cy / h) < .02,
              head_band(bytes(w * h), w, h) is None,
              cover_scaled_width({"width": 3840, "height": 2160}) == 3414,
              crop_x(0, 3414) == 0, crop_x(1, 3414) == 2334, crop_x(.5, 1080) == 0,
              all(crop_x(i / 100, 3414) % 2 == 0 for i in range(101)),
              sample_frames({"segments": [{"src_in_f": 100, "src_out_f": 140}]}, "src")
              == [(0, 110), (0, 120), (0, 130)],
              sample_frames({"segments": [{"out_in_f": 0, "out_out_f": 8}]}, "out")
              == [(0, 2), (0, 4), (0, 6)]]
    specked = bytearray(alpha)
    for y in range(5, 25):
        specked[y * w + 4:y * w + 47] = bytes([255]) * 43
    specked[25 * w + 4:25 * w + 10] = bytes([255]) * 6
    point = head_band(specked, w, h)
    checks.append(point is not None and abs(point[0] - cx / w) < .02 and abs(point[1] - cy / h) < .02)
    points = {10: (.48, .35), 20: (.49, .34), 30: (.5, .35), 40: (.51, .36), 50: (.52, .35),
              60: (.64, .22), 70: (.85, .1)}
    with contextlib.redirect_stdout(io.StringIO()) as notes:
        kept = reject_outliers([(0, f) for f in points], points)
    checks.append(kept == (points | {60: None, 70: None}) and len(notes.getvalue().splitlines()) == 2
                  and statistics.median(p[0] for p in kept.values() if p is not None) == .5)
    checks.append(K == 6 and 3 * K == 18 and settled_frames(3) == [5, 11, 17])
    chunks = batches(list(range(141)))
    checks.append(len(chunks) == 2 and all(len(chunk) <= 90 for chunk in chunks)
                  and [f for chunk in chunks for f in chunk] == list(range(141))
                  and batches(list(range(90))) == [list(range(90))])
    checks.append(all(head_band(bytes(a if v else 0 for v in alpha), w, h) is None for a in (120, 160, 199)))
    point = head_band(bytes(200 if v else 0 for v in alpha), w, h)
    checks.append(point is not None and abs(point[0] - cx / w) < .02 and abs(point[1] - cy / h) < .02)
    def valid_box(point):
        x0, y0, x1, y1 = point.box
        return (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
                and x0 <= point[0] <= x1 and y0 <= point[1] <= y1)

    def close_up(cx):
        return bytes(255 if (x - cx) ** 2 + (y - 80) ** 2 <= 60 ** 2
                     or (140 <= y < 174 and abs(x - cx) <= 18)
                     or (110 <= y and 80 <= abs(x - cx) <= 110)
                     or (174 <= y and abs(x - cx) <= 110) else 0 for y in range(h) for x in range(w))

    point = head_band(close_up(120), w, h)
    # Head and neck occupy 55%; shirt sides rise above the chin and neck.
    checks.append(point is not None and valid_box(point) and point.box == (10 / w, 20 / h, 231 / w, 230 / h)
                  and point.box[1] <= 125 / h < 141 / h <= 174 / h <= point.box[3]
                  and point.box[3] - point.box[1] > .4)
    hands = bytearray(close_up(120))
    for y in range(30, 36):
        hands[y * w + 5:y * w + 235] = bytes([255]) * 230
    point = head_band(hands, w, h)
    checks.append(point is not None and valid_box(point) and point.box == (5 / w, 20 / h, 235 / w, 230 / h)
                  and point.box[3] >= 174 / h)
    bun = bytearray(close_up(120))
    for y in range(21):
        for x in range(w):
            if (x - 120) ** 2 + (y - 10) ** 2 <= 10 ** 2:
                bun[y * w + x] = 255
    point = head_band(bun, w, h)
    checks.append(point is not None and valid_box(point) and point.box == (10 / w, 0., 231 / w, 225 / h)
                  and point.box[3] >= 174 / h)
    column = bytes(255 if 20 <= y and 60 <= x < 181 else 0 for y in range(h) for x in range(w))
    point = head_band(column, w, h)
    # 75% of the 280 occupied rows ends at row 230.
    checks.append(point is not None and valid_box(point) and point.box == (60 / w, 20 / h, 181 / w, 230 / h))
    point = head_band(close_up(180), w, h)
    checks.append(point is not None and valid_box(point) and point.box == (70 / w, 20 / h, 1.0, 230 / h))
    rng = random.Random(710)
    for _ in range(200):
        rw, rh = rng.randint(1, 48), rng.randint(1, 64)
        plane = bytes(rng.choice((0, 0, 0, 200, 255, 255)) for _ in range(rw * rh))
        point = head_band(plane, rw, rh)
        checks.append(point is None or valid_box(point))
    if not all(checks):
        print("selftest FAILED: head band/box, ghosts, settling, outliers, crop maths or sample frames")
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("crop", help="write work/crop.json from the source take")
    p.add_argument("--work", required=True)
    p.add_argument("--take", required=True)
    q = sub.add_parser("anchors", help="write work/anchors.json from the newest cut master")
    q.add_argument("--reel-dir", required=True)
    for parser in (p, q):
        parser.add_argument("--engine", choices=ENGINES, default="auto")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd is None:
        ap.print_help()
        return 2
    return execute(a)


def guarded(fn):
    try:
        return fn()
    except Stop as e:
        print(str(e))
        return e.code
    except Exception:
        print("The face step stopped unexpectedly; check the inputs and editor setup, then try again.")
        return 1


if __name__ == "__main__":
    sys.exit(guarded(main))
