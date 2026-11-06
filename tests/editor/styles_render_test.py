#!/usr/bin/env python3
"""S6c.4: a real 60-second cut, style pixels and measured tuning (stdlib only).

The lane launches ONE --case under heavy_lock.py, with --take (or
EDITOR_SE_TEST_TAKE), --out and --keep. Run build first, then punch-dramatic,
punch-subtle, layout-switch, follow-cam, ceiling, tri2; finally --write-tuning.
An explicit --out is also deleted unless --keep is given: use --keep for the
multi-call lane. --selftest needs neither video tools nor the heavy lock.

Words/sentences are planted test labels, not a transcription. As in the existing
render_engine_test style-143 case, ONLY the dramatic worker plants peak=1.30.
Overlay is additive: the previous solid layout persists beneath its glass card.
Ceiling uses direct delivery-quality HyperFrames renders of one lossless 2 s
span, at fixed scales, without the compose Master approval flow.
"""
import argparse
import contextlib
import ctypes
import hashlib
import importlib.util
import json
import math
import multiprocessing
import os
import re
import shutil
import statistics
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "editor-superengine"
SCRIPTS = PLUGIN / "skills" / "reel-canvas-build" / "scripts"
FIRST_CUTS = PLUGIN / "skills" / "reel-first-cuts" / "scripts"
TUNING = SCRIPTS.parent / "references" / "tuning.json"
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
import runtime as rt  # noqa: E402

CASES = ("build", "punch-dramatic", "punch-subtle", "layout-switch",
         "follow-cam", "ceiling", "tri2")
SEARCH = (1.30, 1.25, 1.20, 1.15, 1.10)
# H-S6c-2: 60 % of the unscaled sharpness (80 % was unreachable for an upscaled 1080 master)
CEILING_KEEP = 0.60
RATE, TOTAL = 30, 1800
PREVIEW = (720, 1280)
MASTER = (1080, 1920)
PICK_SEGMENTS = (1, 4, 7, 10)
LAYOUTS = ("full", "split", "stack", "pip", "overlay")
PLATE = (10, 12, 18)


def require(ok, message):
    if not ok:
        raise AssertionError(message)
    print("PASS " + message, flush=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, doc):
    path = Path(path)
    data = (json.dumps(doc, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    assert b"\r" not in data
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def load(name, folder=SCRIPTS):
    spec = importlib.util.spec_from_file_location("styles_render_" + name, folder / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def laplacian_variance(gray, width, height):
    """Population variance of the 3x3 cross Laplacian; discard the outer border."""
    if width < 3 or height < 3 or len(gray) != width * height:
        raise ValueError("Laplacian needs a matching plane at least 3x3")
    total = squares = count = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            i = y * width + x
            v = gray[i - width] + gray[i + width] + gray[i - 1] + gray[i + 1] - 4 * gray[i]
            total += v
            squares += v * v
            count += 1
    return max(0.0, squares / count - (total / count) ** 2)


def scale_from_points(before, after):
    """Distance ratio of two corresponding points; common translation cancels."""
    distance = math.dist(*before)
    if distance == 0:
        raise ValueError("the two reference points must differ")
    return math.dist(*after) / distance


def ceiling_search(measure):
    """Measure baseline, then descending scales; stop at the first inclusive CEILING_KEEP pass."""
    scores = {1.0: measure(1.0)}
    if not math.isfinite(scores[1.0]) or scores[1.0] <= 0:
        raise ValueError("baseline face region has no measurable detail")
    for scale in SEARCH:
        scores[scale] = measure(scale)
        if not math.isfinite(scores[scale]) or scores[scale] < 0:
            raise ValueError("invalid sharpness measurement")
        if scores[scale] >= CEILING_KEEP * scores[1.0]:
            return scale, scores
    return 1.0, scores


def parse_tri2(log, duration):
    """Parse blackdetect and freezedetect, including a freeze continuing to EOF."""
    number = r"([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)"
    black = [float(v) for v in re.findall(r"\bblack_duration:\s*" + number, log)]
    frozen, start, reported = [], None, False
    for line in log.splitlines():
        m = re.search(r"freeze_start:\s*" + number, line)
        if m:
            start, reported = float(m[1]), False
        m = re.search(r"freeze_duration:\s*" + number, line)
        if m:
            frozen.append(float(m[1]))
            reported = True
        m = re.search(r"freeze_end:\s*" + number, line)
        if m:
            if start is not None and not reported:
                frozen.append(float(m[1]) - start)
            start = None
    if start is not None and not reported:
        frozen.append(max(0.0, duration - start))
    return {"black": black, "frozen": frozen}


def clean_threshold(default, durations, rate=RATE):
    """Smallest frame-grid duration above all detections (keep an already clean default)."""
    return max(default, (math.floor(max(durations) * rate + 1e-6) + 1) / rate) if durations else default


def sample(gray, w, h, x, y):
    """Bilinear luma sample, or None outside the picture."""
    if not (0 <= x < w - 1 and 0 <= y < h - 1):
        return None
    ix, iy = int(x), int(y)
    dx, dy = x - ix, y - iy
    i = iy * w + ix
    return ((gray[i] * (1 - dx) + gray[i + 1] * dx) * (1 - dy)
            + (gray[i + w] * (1 - dx) + gray[i + w + 1] * dx) * dy)


def fit_scale(ref, got, w, h, origin, excluded=(), box=None, channels=1):
    """Best (scale, MAE, PSNR) against the SAME cut-master frame, never cut-1.

    Search every 0.005 step in [0.95, 1.50]. The default domain is the central
    60% in each dimension, minus title/card rectangles (x0, y0, x1, y1).
    A box instead fits the source with object-fit:cover into the pip rectangle,
    inset 6 preview pixels to avoid its rounded edge and ring.

    A sparse pass only orders candidates. The winner minimizes MAE over ALL
    domain pixels: nonnegative partial sums may reject a candidate only after
    they exceed the incumbent's complete sum. No expected scale enters the fit.
    """
    if channels not in (1, 3) or len(ref) != w * h * channels or len(got) != len(ref):
        raise ValueError("scale fit needs matching gray or RGB frames")
    bx, by, bw, bh = box if box is not None else (0, 0, w, h)
    cover = max(bw / w, bh / h)
    ox, oy = bx + origin[0] / w * bw, by + origin[1] / h * bh
    if box is None:
        left, top, right, bottom = math.ceil(.2 * w), math.ceil(.2 * h), math.ceil(.8 * w), math.ceil(.8 * h)
    else:
        left, top, right, bottom = math.ceil(bx + 6), math.ceil(by + 6), math.ceil(bx + bw - 6), math.ceil(by + bh - 6)
    if not (0 <= left < right <= w and 0 <= top < bottom <= h):
        raise ValueError("scale fit domain leaves the frame")
    rows = []
    for y in range(top, bottom):
        spans = [(left, right)]
        for x0, y0, x1, y1 in excluded:
            if y0 <= y < y1:
                spans = [(c, d) for a, b in spans for c, d in
                         ((a, min(b, math.ceil(x0))), (max(a, math.ceil(x1)), b)) if c < d]
        rows.append((y, spans))
    count = sum(b - a for _, spans in rows for a, b in spans) * channels
    if not count:
        raise ValueError("scale fit has no unmasked pixels")

    def axis(p, pivot, start, length, source, scale):
        v = source / 2 + (pivot + (p - pivot) / scale - start - length / 2) / cover
        return (math.floor(v), v % 1) if 0 <= v < source - 1 else None

    def scan(xs, ys, stride=1, limit=math.inf):
        total = squares = n = 0
        for y, spans in rows[::stride]:
            ym = ys[y - top]
            for a, b in spans:
                for x in range(a, b, stride):
                    xm = xs[x - left]
                    j = (y * w + x) * channels
                    if xm is None or ym is None:
                        for c in range(channels):
                            error = got[j + c]  # uncovered source is the black canvas
                            total += error
                            squares += error * error
                    else:
                        ix, dx = xm
                        iy, dy = ym
                        i = (iy * w + ix) * channels
                        down = i + w * channels
                        for c in range(channels):
                            expected = ((ref[i + c] * (1 - dx) + ref[i + channels + c] * dx) * (1 - dy)
                                        + (ref[down + c] * (1 - dx) + ref[down + channels + c] * dx) * dy)
                            error = abs(got[j + c] - expected)
                            total += error
                            squares += error * error
                    n += channels
            if total > limit:
                return math.inf, math.inf
        return (total / n, squares / n) if n else (math.inf, math.inf)

    candidates = []
    for tick in range(190, 301):
        scale = tick / 200
        xs = [axis(x, ox, bx, bw, w, scale) for x in range(left, right)]
        ys = [axis(y, oy, by, bh, h, scale) for y in range(top, bottom)]
        score, _ = scan(xs, ys, stride=max(1, min(w, h) // 24))
        candidates.append((score, scale, xs, ys))
    best, best_scale, mse = math.inf, math.inf, math.inf
    for _, scale, xs, ys in sorted(candidates, key=lambda c: c[:2]):
        score, squared = scan(xs, ys, limit=best * count)
        if (score, scale) < (best, best_scale):
            best, best_scale, mse = score, scale, squared
    return best_scale, best, math.inf if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def measure_scale(ref, got, w, h, origin, excluded=()):
    return fit_scale(ref, got, w, h, origin, excluded)[0]


def measure_frame(task):
    """CPU-only pool worker; read one same-number pair from disk-backed Frames."""
    f, ref_path, got_path, offset, size, origin, excluded = task
    length = size[0] * size[1]
    with Path(ref_path).open("rb") as stream:
        stream.seek(offset)
        ref = stream.read(length)
    with Path(got_path).open("rb") as stream:
        stream.seek(offset)
        got = stream.read(length)
    return f, measure_scale(ref, got, *size, origin, excluded)


def frame_filter_args(path, graph):
    """Keep arbitrarily long frame selections out of Windows' command line."""
    path.write_bytes((graph + "\n").encode("utf-8"))
    return ["-/filter:v", str(path)]


def windows_argv(command):
    count = ctypes.c_int()
    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(ctypes.c_wchar_p)
    args = parse(command, ctypes.byref(count))
    if not args:
        return []
    try:
        return [args[i] for i in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(args, ctypes.c_void_p))


def require_heavy_lock():
    """Fail closed unless a live ancestor is the lane's heavy_lock.py launcher.

    No environment bypass and no hard-coded machine path. The lane owns the
    lock protocol; this checks its launch ancestry, not a second competing lock.
    """
    ancestors = []
    if os.name == "nt":
        script = (f"$p={os.getppid()}; $seen=@{{}}; $r=@(); "
                  "while($p -and -not $seen.ContainsKey($p)) { $seen[$p]=$true; "
                  "$v=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p); if(-not $v){break}; "
                  "$r+=@{pid=$v.ProcessId;cmd=$v.CommandLine}; $p=[int]$v.ParentProcessId }; "
                  "ConvertTo-Json -InputObject @($r) -Compress")
        p = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        if p.returncode:
            raise RuntimeError("cannot verify the heavy-lock ancestor; nothing rendered")
        for item in json.loads(p.stdout):
            ancestors.append((item["pid"], windows_argv(item["cmd"] or "")))
    else:
        pid, seen = os.getppid(), set()
        while pid and pid not in seen:
            seen.add(pid)
            base = Path("/proc") / str(pid)
            try:
                args = [v.decode("utf-8", "replace") for v in (base / "cmdline").read_bytes().split(b"\0") if v]
                status = (base / "status").read_text()
            except OSError:
                break
            ancestors.append((pid, args))
            pid = int(re.search(r"^PPid:\s*(\d+)", status, re.M)[1])
    for pid, args in ancestors:
        if "--" in args and any(Path(a.replace("\\", "/")).name == "heavy_lock.py"
                                  for a in args[:args.index("--")]):
            print(f"info: heavy-lock launcher verified (ancestor {pid})", flush=True)
            return
    raise RuntimeError("render refused: launch this case under the lane's heavy_lock.py --wait 600 -- ...")


class Harness:
    def __init__(self, out):
        self.out = out
        self.reel = out / "reel"
        self.deadline = time.monotonic() + 580
        self.serial = 0
        self.name = "setup"

    def remaining(self):
        seconds = self.deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("case exceeded its 580 s work budget; keep below the lane's 590 s limit")
        return seconds

    def run(self, args, raw_out=None):
        self.remaining()
        self.serial += 1
        log = self.out / "logs" / f"{self.name}-{self.serial:03d}.log"
        log.parent.mkdir(exist_ok=True)
        start = time.monotonic()
        with contextlib.ExitStack() as stack:
            err = stack.enter_context(log.open("wb"))
            dest = stack.enter_context(raw_out.open("wb")) if raw_out else err
            options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
            proc = subprocess.Popen([str(a) for a in args], cwd=self.out, env=rt.python_env(),
                                    stdout=dest, stderr=err if raw_out else subprocess.STDOUT, **options)
            try:
                rc = proc.wait(timeout=self.remaining())
            except (subprocess.TimeoutExpired, TimeoutError):
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True, timeout=5)
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
                raise TimeoutError(f"{self.name} timed out; process tree terminated; see {log.name}") from None
        output = log.read_text(encoding="utf-8", errors="replace")
        print(f"info: {Path(str(args[0])).name}: exit {rc}, {time.monotonic() - start:.1f} s ({log.name})", flush=True)
        if rc:
            raise RuntimeError(f"child exit {rc}: {output[-1600:]}")
        return output

    def worker(self, kind, *args):
        return self.run([sys.executable, "-B", "-X", "utf8", "-I", Path(__file__).resolve(), "--_worker", kind, *args])

    def probe(self, video, count=True):
        return json.loads(self.run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
                                   *(["-count_frames"] if count else []), "-show_entries",
                                   "stream=width,height,nb_read_frames,r_frame_rate,color_space,color_range:format=duration",
                                   "-of", "json", video]))

    def build_info(self):
        doc = read_json(self.out / "build.json")
        if doc["code"] != code_fingerprint():
            raise ValueError("cached build belongs to different code; run build again")
        if digest(self.reel / "work" / "cuts.json") != doc["cuts_sha256"]:
            raise ValueError("cached cut list changed; run build again")
        return doc

    def result(self, name):
        doc = read_json(self.out / (name + ".json"))
        if doc.get("status") != "passed" or doc.get("build_id") != self.build_info()["id"]:
            raise ValueError(f"{name} has no passing result for this build; run it first")
        if "video" in doc:
            path = safe_artifact(self.out, doc["video"])
            if digest(path) != doc["sha256"]:
                raise ValueError(f"{name} preview changed since its checks; run it again")
        return doc


def code_fingerprint():
    paths = [Path(__file__), SCRIPTS / "styles.py", SCRIPTS / "compose.py", SCRIPTS / "face_crop.py",
             FIRST_CUTS / "render.py", FIRST_CUTS / "gaps.py"]
    return {p.name: digest(p) for p in paths}


def safe_artifact(out, relative):
    path = (out / relative).resolve()
    if not path.is_relative_to(out) or path == out:
        raise ValueError("cached artifact escapes --out")
    return path


def select_expr(numbers):
    """Sorted unique frame numbers -> eq/between runs; long eq() chains make ffmpeg ENOMEM."""
    runs = []
    for n in sorted(set(numbers)):
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    return "+".join(f"eq(n,{a})" if a == b else f"between(n,{a},{b})" for a, b in runs)


class Frames:
    """Disk-backed selected raw frames: keep hundreds of wobble frames out of RAM."""
    def __init__(self, harness, video, numbers, label, pix="gray", size=PREVIEW):
        self.numbers = sorted(set(numbers))
        self.width, self.height = size
        self.channels = 3 if pix == "rgb24" else 1
        self.length = self.width * self.height * self.channels
        self.path = harness.out / (label + ".raw")
        stream = harness.probe(video, count=False)["streams"][0]
        matrix = {"bt470bg": "bt601", "smpte170m": "bt601"}.get(stream.get("color_space"), "bt709")
        range_in = "pc" if stream.get("color_range") == "pc" else "tv"
        select = select_expr(self.numbers)
        vf = (f"select='{select}',scale={size[0]}:{size[1]}:flags=lanczos:"
              f"in_color_matrix={matrix}:in_range={range_in}:out_range=pc,format={pix}")
        graph = self.path.with_suffix(".filter")
        try:
            harness.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", video, "-an",
                         *frame_filter_args(graph, vf), "-fps_mode", "passthrough",
                         "-pix_fmt", pix, "-f", "rawvideo", "-"], raw_out=self.path)
        finally:
            graph.unlink(missing_ok=True)
        if self.path.stat().st_size != self.length * len(self.numbers):
            raise ValueError("decoded frame count/size differs from selected frames")
        self.index = {n: i for i, n in enumerate(self.numbers)}
        self.stream = self.path.open("rb")

    def __getitem__(self, number):
        self.stream.seek(self.index[number] * self.length)
        frame = self.stream.read(self.length)
        if len(frame) != self.length:
            raise ValueError("raw frame ended early")
        return frame

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()
        self.path.unlink()


def planted_send(reel, cuts, style, layouts=False):
    words, beats = [], []
    for i, seg in enumerate(cuts["segments"]):
        a, e = seg["out_in_f"], seg["out_out_f"]
        w0 = len(words)
        labels = ("Style", "test", "emphasis", "ends.")
        for label, seconds in zip(labels, (.4, 1.0, 1.5, 4.0)):
            start = a / RATE + seconds
            words.append({"id": f"w_{len(words):04d}", "word": label, "start": start, "end": start + .25})
        beats.append({"id": f"b_{i + 1:03d}", "start_f": a, "end_f": e,
                      "speech_anchor": {"text": " ".join(labels), "w0": w0, "w1": len(words) - 1},
                      "layout": LAYOUTS[i % len(LAYOUTS)] if layouts else "full",
                      "value": None, "scene": None, "broll": None, "transition": None})
    write_json(reel / "work" / "edit_map.cut.json", {"words": words})
    write_json(reel / "beat-map-selection.json", {
        "schema": 1, "reel": reel.name, "fps": RATE, "words": "work/edit_map.cut.json", "beats": beats,
        "word_marks": [{"w": i * 4 + 2, "mark": "emph"} for i in PICK_SEGMENTS],
        "proposed": {}, "notes": {}, "needs": "", "sent_at": datetime.now().astimezone().isoformat(),
        "edit_style": style, "caption_style": {"style": "none"}})


def build(h, take):
    if take is None or not take.is_file():
        raise ValueError("build needs a readable --take or EDITOR_SE_TEST_TAKE")
    cache = h.out / "build.json"
    if cache.exists():
        old = h.build_info()
        if old["source"] == source_id(take):
            require((h.reel / "work" / "anchors.json").is_file(), "cached build has real face anchors")
            print("info: cached --out/reel reused; no render", flush=True)
            return {"cached": True}
        raise ValueError("--out already contains a different take; choose a fresh output directory")
    if h.reel.exists():
        raise ValueError("incomplete --out/reel exists; use a fresh --out rather than silently replacing it")
    probe = load("probe", FIRST_CUTS)
    gaps = load("gaps", FIRST_CUTS)
    # probe's functions use module tool paths; supply rt.tool rather than PATH discovery.
    probe.FFMPEG, probe.FFPROBE = rt.tool("ffmpeg"), rt.tool("ffprobe")
    probe.run = lambda args: subprocess.run(args, capture_output=True, text=True,
                                            env=rt.python_env(), timeout=h.remaining())
    facts = probe.video_facts(take)
    if "width" not in facts or "height" not in facts:
        raise ValueError("source dimensions could not be read")
    src_probe = h.probe(take, count=False)
    require(float(src_probe["format"]["duration"]) >= 71, "take covers twelve 5 s pieces and eleven 1 s skips")
    work = h.reel / "work"
    work.mkdir(parents=True)
    cuts = gaps.snap_cuts([[i * 6.0, i * 6.0 + 5.0] for i in range(12)], RATE, speed=1.0)
    gaps.write_cuts(work, cuts)
    # gaps.write_cuts uses text IO on Windows; normalise only the new scratch artifacts.
    for name in ("cuts.json", "segments.json"):
        write_json(work / name, read_json(work / name))
    require(len(cuts["segments"]) == 12 and cuts["segments"][-1]["out_out_f"] == TOTAL,
            "build: exactly 60 s, twelve pieces and eleven cuts")
    write_json(work / "probe.json", {"fps_flag": probe.fps_flag(), "video": facts,
                                    "audio_stream": 0, "out_rate": RATE})
    h.worker("face", "crop", "--work", work, "--take", take)
    crop = read_json(work / "crop.json")
    h.worker("render", work, take, "--master")
    h.worker("face", "anchors", "--reel-dir", h.reel)
    anchors = read_json(work / "anchors.json")
    # Real footage: a lean-in/out sample is dropped on purpose (face_crop's outlier and ghost rules), so ask for
    # most segments, not all; follow-cam keeps the default anchor where a segment has fewer than two.
    two = {s["seg"] for s in anchors["segments"] if len(s["samples"]) >= 2}
    require(len(two) >= 8, "build: at least 8 of 12 segments have two or more real anchors for follow-cam")
    master = work / "renders" / "master-100x.mp4"
    st = h.probe(master)["streams"][0]
    require(int(st["nb_read_frames"]) == TOTAL and (st["width"], st["height"]) == MASTER,
            "build: cut master has 1800 frames at 1080x1920")
    planted_send(h.reel, cuts, {"style": "punch-in", "punch_scale": 1.1})
    write_json(cache, {"id": uuid.uuid4().hex, "code": code_fingerprint(), "source": source_id(take),
                       "width": facts["width"], "height": facts["height"], "engine": "HyperFrames delivery",
                       "face_engine": crop["engine"],
                       "date": datetime.now().strftime("%m.%d.%y"), "cuts_sha256": digest(work / "cuts.json"),
                       "master_sha256": digest(master), "anchors_sha256": digest(work / "anchors.json")})
    return {"cached": False}


def source_id(take):
    st = take.stat()
    return {"path": str(take), "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}


def cached_inputs(h):
    doc = h.build_info()
    work = h.reel / "work"
    master = work / "renders" / "master-100x.mp4"
    if digest(master) != doc["master_sha256"] or digest(work / "anchors.json") != doc["anchors_sha256"]:
        raise ValueError("cached master/anchors changed; use a fresh build")
    return read_json(work / "cuts.json"), master


def preview(h, name):
    cuts, master = cached_inputs(h)
    moves = {}
    if name.startswith("punch-"):
        moves = {"opening_settle": name == "punch-dramatic", "word_punches": {
            "preset": "dramatic" if name == "punch-dramatic" else "subtle", "shape": "eased",
            "picks": [i * 4 + 2 for i in PICK_SEGMENTS]}}
    elif name == "follow-cam":
        moves = {"follow_cam": True}
    style = {"style": "layout-switch" if name == "layout-switch" else "punch-in",
             "punch_scale": 1.1, "moves": moves}
    planted_send(h.reel, cuts, style, layouts=name == "layout-switch")
    log = h.worker("dramatic" if name == "punch-dramatic" else "compose", "preview", "--reel-dir", h.reel)
    summary = json.loads(log.strip().splitlines()[-1])
    video = h.reel / summary["out"]
    destination = h.out / (name + ".mp4")
    shutil.copyfile(video, destination)
    track = read_json(h.reel / "work" / "scale_track.json")
    write_json(h.out / (name + "-scale_track.json"), track)
    stream = h.probe(destination)["streams"][0]
    require((stream["width"], stream["height"]) == PREVIEW, name + ": preview is 720x1280")
    require(int(stream["nb_read_frames"]) == cuts["segments"][-1]["out_out_f"] == TOTAL,
            name + ": output frame count equals cut master")
    require(summary["tier"] == "preview" and summary["frames"] == TOTAL, name + ": compose preview exit 0")
    return destination, track, cuts, master, summary


def key_on(track, f):
    return next(k for k in track["keys"] if k["f"] == f)


def cut_frames(cuts):
    return [s["out_in_f"] for s in cuts["segments"][1:]]


def check_no_cross(track, cuts):
    frames = cut_frames(cuts)
    require(len(frames) == 11, "eleven interior cut frames")
    require(not [(t["id"], c) for t in track["tweens"] for c in frames
                 if t["start_f"] < c < t["end_f"]], "no transform tween crosses any cut")


def punch(h, name):
    video, track, cuts, master, summary = preview(h, name)
    check_no_cross(track, cuts)
    if name == "punch-dramatic":
        require(key_on(track, 0)["scale"] == 1.06 and any(
            t["id"] == "opening settle" and t["start_f"] == 0 and t["to"] == 1.0
            for t in track["tweens"]), "punch-dramatic: opening settle is enabled")
    gestures = []
    for seg in PICK_SEGMENTS:
        word = seg * 4 + 2
        into = next(t for t in track["tweens"] if t["id"] == f"punch {word} in")
        back = next(t for t in track["tweens"] if t["id"] == f"punch {word} out")
        gestures.append((seg, into, back))
    ns = {f for c in cut_frames(cuts) for f in (c - 1, c)}
    for _, into, back in gestures:
        ns.update((into["start_f"] - 1, into["end_f"], max(into["end_f"], back["start_f"] - 1)))
        if name == "punch-subtle":
            ns.update(range(into["start_f"], back["end_f"] + 1))
    measurements = {}
    with Frames(h, master, ns, name + "-ref") as refs, Frames(h, video, ns, name + "-got") as got:
        tasks = []
        for f in sorted(ns):
            key = max((k for k in track["keys"] if k["f"] <= f), key=lambda k: k["f"])
            # The planted punch beats are full-frame and have no cards or
            # plates. Mask the opening hook's entire three-line box plus
            # its shadow (compose.hook_box on the 1080x1920 grid).
            excluded = (tuple(v * 2 / 3 for v in (84, 274, 936, 535)),) if f < RATE * 5 else ()
            tasks.append((f, refs.path, got.path, refs.index[f] * refs.length, PREVIEW,
                          (key["ox"] * PREVIEW[0], key["oy"] * PREVIEW[1]), excluded))
        # Full-domain MAE is CPU-bound. Spawn a bounded pool for independent
        # frames, not renders; disk offsets avoid copying hundreds of frames.
        # Pool's context terminates all workers on a timeout or failed check.
        with multiprocessing.get_context("spawn").Pool(min(8, os.cpu_count() or 1)) as pool:
            pending = pool.imap_unordered(measure_frame, tasks)
            for _ in tasks:
                try:
                    f, value = pending.next(timeout=h.remaining())
                except multiprocessing.TimeoutError:
                    raise TimeoutError("pixel measurements exceeded the case's 580 s work budget") from None
                measurements[f] = value
                h.remaining()
        measured = measurements.__getitem__

        for i, c in enumerate(cut_frames(cuts), 1):
            before, after = measured(c - 1), measured(c)
            wants = (1.1 if (i - 1) % 2 else 1.0, 1.1 if i % 2 else 1.0)
            require(all(abs(g / w - 1) <= .02 for g, w in zip((before, after), wants)),
                    f"{name}: cut {c}, pixels at cut-1/cut set {wants} (got {before:.4f}/{after:.4f})")
            require(key_on(track, c)["scale"] == wants[1], f"{name}: hard scale key exactly on cut {c}")
        for seg, into, back in gestures:
            base = 1.1 if seg % 2 else 1.0
            peak = 1.30 if name == "punch-dramatic" else 1.06
            onset, hold = into["start_f"], into["end_f"]
            # Compare the whole-region scales before onset and at hold, each
            # registered to its own source frame, then restore segment scale.
            before, top = measured(onset - 1), measured(hold)
            total = top / before * base
            require(abs(total / (base * peak) - 1) <= .02 and abs(top / (base * peak) - 1) <= .02,
                    f"{name}: segment {seg} hold {hold} vs pre-onset {onset - 1}, total {total:.4f}, want {base * peak:.4f}")
            if name == "punch-subtle":
                ks = [(f, measured(f)) for f in range(onset, back["end_f"] + 1)]
                worst, frame = max((abs(b / a - 1), f1) for (f0, a), (f1, b) in zip(ks, ks[1:]))
                require(worst <= .01, f"TRI-5: subtle gesture {seg}, max adjacent scale jump {worst:.3%} at {frame} <= 1%; report failure, linear shape is X2")
    return {"video": video.name, "sha256": digest(video), "render_seconds": summary["seconds"],
            "measured_scales": measurements, "dramatic_peak_plant": 1.30 if name == "punch-dramatic" else None}


def rgb_at(frame, x, y):
    i = (round(y) * PREVIEW[0] + round(x)) * 3
    return tuple(frame[i:i + 3])


def rgb_sample(frame, x, y):
    w, h = PREVIEW
    if not (0 <= x < w - 1 and 0 <= y < h - 1):
        raise ValueError("layout reference pixel is outside the source")
    ix, iy = int(x), int(y)
    dx, dy = x - ix, y - iy
    return tuple(sum(frame[(yy * w + xx) * 3 + c] * weight for xx, yy, weight in (
        (ix, iy, (1 - dx) * (1 - dy)), (ix + 1, iy, dx * (1 - dy)),
        (ix, iy + 1, (1 - dx) * dy), (ix + 1, iy + 1, dx * dy))) for c in range(3))


def block_mean(read, frame, x, y, step=1, r=4):
    """Mean RGB of a 9x9 grid around x, y; edges and compression noise average out."""
    pts = [read(frame, x + i * step, y + j * step) for j in range(-r, r + 1) for i in range(-r, r + 1)]
    return tuple(sum(p[c] for p in pts) / len(pts) for c in range(3))


def layout_pixels(frame, ref, solid, overlay=False, origin=None):
    """Independent geometry probes (Master grid), away from radii, shadows and hook text."""
    boxes = {"full": (0, 0, 1080, 1920), "split": (0, 960, 1080, 960),
             "stack": (0, 0, 1080, 844), "pip": (738, 28, 312, 555)}
    x, y, w, h = (v * 2 / 3 for v in boxes[solid])
    errors, plate_errors, video_contrast = [], [], []
    # Video sample pairs apply object-fit:cover, including split/stack's middle crop.
    cover = max(w / PREVIEW[0], h / PREVIEW[1])
    for fx, fy in ((.25, .2), (.5, .3), (.75, .4), (.25, .6), (.5, .7), (.75, .8)):
        px, py = round(x + fx * w), round(y + fy * h)
        if solid == "full" and 200 < py < 600:
            continue  # opening hook title is intentionally present only in the first piece
        mx, my = (px - x - w / 2) / cover + PREVIEW[0] / 2, (py - y - h / 2) / cover + PREVIEW[1] / 2
        if solid != "pip":
            # Same 9x9 block in both: preview pixels vs their cover-mapped master points.
            expected = block_mean(rgb_sample, ref, mx, my, 1 / cover)
            actual = block_mean(rgb_at, frame, px, py)
            errors.extend(abs(a - b) for a, b in zip(actual, expected))
        video_contrast.extend(abs(a - b) for a, b in zip(rgb_sample(ref, mx, my), PLATE))
    if max(video_contrast, default=0) <= 24:
        raise ValueError("layout probes cannot distinguish this dark take from the card plate")
    if solid == "pip":
        if origin is None:
            raise ValueError("pip registration needs this frame's scale-track origin")
        scale, mae, psnr = fit_scale(ref, frame, *PREVIEW, origin, box=(x, y, w, h), channels=3)
        require(mae <= 18 or psnr >= 22,
                f"pip video above card: inset rectangle best scale {scale:.3f}, MAE {mae:.2f} <= 18 OR PSNR {psnr:.2f} dB >= 22")
    if solid == "split":
        plate_probes = ((100, 100), (540, 320), (980, 800))
    elif solid == "stack":
        plate_probes = ((100, 1000), (540, 1300), (980, 1780))
    elif solid == "pip":
        plate_probes = ((100, 100), (540, 640), (100, 1100))
    else:
        plate_probes = ()
    for px, py in plate_probes:
        actual = rgb_at(frame, px * 2 / 3, py * 2 / 3)
        expected = (0, 0, 0) if overlay else PLATE
        plate_errors.extend(abs(a - b) for a, b in zip(actual, expected))
    if solid == "pip":
        require(max(plate_errors) <= 18, f"pip plate colour outside pill: pixel error {max(plate_errors):.1f} <= 18")
    if overlay:
        # Here overlay follows pip. Its translucent card is over the black
        # canvas; the pip window retains its previous solid geometry above it.
        actual = rgb_at(frame, 540 * 2 / 3, 1500 * 2 / 3)
        require(max(abs(a - .78 * b) for a, b in zip(actual, (15, 16, 22))) <= 6,
                "overlay glass-card pixels appear over the canvas")
        require(max(rgb_at(frame, 100 * 2 / 3, 640 * 2 / 3)) <= 6,
                "overlay leaves the canvas outside its card transparent")
    # (max error, max video-block error, max plate pixel error); None = no probes of that kind.
    return (max(errors + plate_errors, default=math.inf), max(errors, default=None),
            max(plate_errors, default=None))


def layout_switch(h):
    video, track, cuts, master, summary = preview(h, "layout-switch")
    require(not track["tweens"], "layout-switch: cut-aligned layouts have no tweens")
    ns = {f for c in cut_frames(cuts) for f in (c - 1, c)}
    with Frames(h, master, ns, "layout-ref", "rgb24") as refs, Frames(h, video, ns, "layout-got", "rgb24") as got:
        for f in sorted(ns):
            seg = f // (RATE * 5)
            layout = LAYOUTS[seg % len(LAYOUTS)]
            solid = "pip" if layout == "overlay" else layout
            key = max((k for k in track["keys"] if k["f"] <= f), key=lambda k: k["f"])
            error, video_err, plate_err = layout_pixels(got[f], refs[f], solid, layout == "overlay",
                                                        (key["ox"] * PREVIEW[0], key["oy"] * PREVIEW[1]))
            detail = (f"layout-switch: frame {f} is {layout}, video 9x9-block error {video_err}, "
                      f"plate pixel error {plate_err}, max {error:.1f} <= 18")
            print(("PASS " if error <= 18 else "FAIL ") + detail, flush=True)
            require(error <= 18, detail)
        for c in cut_frames(cuts):
            name = LAYOUTS[(c // (RATE * 5)) % len(LAYOUTS)]
            require(key_on(track, c)["layout"] == ("pip" if name == "overlay" else name),
                    f"layout-switch: hard layout key on cut {c} (overlay retains solid layout)")
    return {"video": video.name, "sha256": digest(video), "render_seconds": summary["seconds"]}


def follow_cam(h):
    video, track, cuts, master, summary = preview(h, "follow-cam")
    check_no_cross(track, cuts)
    require(track["style"]["moves"]["follow_cam"], "follow-cam: enabled with real anchors (a static face may need no moves)")
    anchors = read_json(h.reel / "work" / "anchors.json")
    for s in anchors["segments"]:
        f = cuts["segments"][s["seg"]]["out_in_f"]
        k, p = key_on(track, f), s["samples"][0]
        require(abs(k["ox"] - p["x"]) <= .0001 and abs(k["oy"] - p["y"]) <= .0001,
                f"follow-cam: anchor resets on segment {s['seg']} cut frame {f}")
    return {"video": video.name, "sha256": digest(video), "render_seconds": summary["seconds"]}


def crop_gray(frame, width, height, centre, side):
    side = round(side)
    x, y = round(centre[0] - side / 2), round(centre[1] - side / 2)
    if x < 0 or y < 0 or x + side > width or y + side > height:
        raise ValueError("scaled 216x216 face square leaves the frame; cannot compare the same face area")
    return b"".join(frame[j * width + x:j * width + x + side] for j in range(y, y + side)), side


def ceiling(h):
    cuts, master = cached_inputs(h)
    anchors = read_json(h.reel / "work" / "anchors.json")
    chosen = next(s for s in anchors["segments"] if s["seg"] == 1)
    p = chosen["samples"][len(chosen["samples"]) // 2]
    # One span, well inside the piece, shared by every candidate. Lossless
    # extraction adds no softness before the direct delivery-quality HF encode.
    start = max(5, min(8, p["f"] // RATE))
    span = h.out / "ceiling-source.mp4"
    h.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-ss", str(start), "-i", master, "-t", "2",
           "-an", "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv", span])
    require(int(h.probe(span)["streams"][0]["nb_read_frames"]) == RATE * 2, "ceiling: shared span is exactly 2 s")
    frames = (6, 18, 30, 42, 54)
    centre = (p["x"] * MASTER[0], p["y"] * MASTER[1])

    def measure(scale):
        h.remaining()
        output = h.out / f"ceiling-{scale:.2f}.mp4"
        h.worker("ceiling", span, output, str(scale), str(p["x"]), str(p["y"]))
        require(int(h.probe(output)["streams"][0]["nb_read_frames"]) == RATE * 2,
                f"ceiling: scale {scale:.2f} is 60 Master frames")
        values = []
        with Frames(h, output, frames, f"ceiling-{scale:.2f}", size=MASTER) as decoded:
            for f in frames:
                face, side = crop_gray(decoded[f], *MASTER, centre, 216 * scale)
                values.append(laplacian_variance(face, side, side))
        score = statistics.mean(values)
        print(f"sharpness scale={scale:.2f}: {score:.6f}; five frames {values}", flush=True)
        return score

    value, scores = ceiling_search(measure)
    print(f"softness_ceiling={value:.2f}; baseline*{CEILING_KEEP:.2f}={scores[1.0] * CEILING_KEEP:.6f}", flush=True)
    return {"softness_ceiling": value, "scores": {str(k): v for k, v in scores.items()}, "frames": list(frames),
            "source_start_s": start, "anchor": {"x": p["x"], "y": p["y"]},
            "method": "direct HyperFrames delivery, fixed scale, lossless 2 s input, 216x216 anchor square scaled with punch",
            "date": datetime.now().strftime("%m.%d.%y")}


def tri2(h):
    previews = [h.result(n) for n in ("punch-dramatic", "layout-switch")]

    def detect(doc, black, frozen):
        log = h.run([rt.tool("ffmpeg"), "-hide_banner", "-nostats", "-i", safe_artifact(h.out, doc["video"]),
                     "-an", "-vf", f"blackdetect=d={black:.9f}:pix_th=0.10,freezedetect=n=-60dB:d={frozen:.9f}",
                     "-f", "null", "-"])
        return parse_tri2(log, 60)

    events = [detect(d, .5, 3) for d in previews]
    thresholds = {"black_gap_s": clean_threshold(.5, [s for e in events for s in e["black"]]),
                  "frozen_s": clean_threshold(3, [s for e in events for s in e["frozen"]])}
    if any(e["black"] or e["frozen"] for e in events):
        print(f"TRI-2 clean-render detections: {events}; smallest passing frame-grid thresholds proposed: {thresholds}", flush=True)
        verified = [detect(d, thresholds["black_gap_s"], thresholds["frozen_s"]) for d in previews]
        require(not any(e["black"] or e["frozen"] for e in verified), "TRI-2: adjusted thresholds pass both clean renders")
    else:
        require(thresholds == {"black_gap_s": .5, "frozen_s": 3}, "TRI-2: both renders clean at 0.5 s / 3 s")
    print("tri2=" + json.dumps(thresholds), flush=True)
    return {"tri2": thresholds, "detections": events, "preview_sha256": [d["sha256"] for d in previews]}


def write_tuning(h):
    info = h.build_info()
    soft, tri = h.result("ceiling"), h.result("tri2")
    # Recheck the inputs even when --write-tuning runs in a later host call.
    cached_inputs(h)
    current = [h.result(n)["sha256"] for n in ("punch-dramatic", "layout-switch")]
    require(current == tri["preview_sha256"], "tuning: TRI-2 measured these exact passing previews")
    base = soft["scores"]["1.0"]
    doc = {"softness_ceiling": soft["softness_ceiling"], "tri2": tri["tri2"],
           "measured_on": (f"{soft['date']}, 60 s cut, {info['width']}x{info['height']} source, "
                           f"Master 1080x1920, {info['engine']}"),
           "softness_rule": (f"largest tested scale keeping >= {CEILING_KEEP * 100:.0f} % of the unscaled face sharpness "
                             "(variance of the Laplacian), H-S6c-2"),
           "softness_table": {f"{float(k):.2f}": round(v / base, 3)
                              for k, v in sorted(soft["scores"].items(), key=lambda kv: float(kv[0]))}}
    require(doc["softness_ceiling"] in (1.0, *SEARCH), "tuning: measured ceiling is a tested candidate")
    require(all(math.isfinite(v) and v > 0 for v in doc["tri2"].values()), "tuning: thresholds are finite real measurements")
    write_json(TUNING, doc)
    print("wrote " + TUNING.relative_to(REPO).as_posix(), flush=True)


def worker(kind, args):
    """Run real script entrypoints in a killable child; never change production code."""
    require_heavy_lock()
    # Production face/cutout children use -I, which ignores PYTHONDONTWRITEBYTECODE.
    # Propagate -B to Python descendants so no __pycache__ is written into the checkout.
    original_popen = subprocess.Popen

    class NoBytecodePopen(original_popen):
        def __init__(self, args, *pos, **kw):
            if isinstance(args, (list, tuple)) and args and Path(str(args[0])).name.lower().startswith("python"):
                args = [args[0], "-B", *args[1:]]
            super().__init__(args, *pos, **kw)

    subprocess.Popen = NoBytecodePopen
    if kind == "face":
        mod = load("face_crop")
        return mod.guarded(lambda: mod.main([str(a) for a in args]))
    if kind == "render":
        mod = load("render", FIRST_CUTS)
        sys.argv = [str(FIRST_CUTS / "render.py"), *map(str, args)]
        return mod.main()
    if kind in ("compose", "dramatic"):
        mod = load("compose")
        if kind == "dramatic":
            mod.styles.PRESETS["dramatic"] = dict(mod.styles.PRESETS["dramatic"], peak=1.30)
            print("info: test-only dramatic peak planted at 1.30 (segment 1.10 x peak = 1.43)", flush=True)
        return mod.guarded(lambda: mod.main([str(a) for a in args]))
    if kind != "ceiling":
        raise ValueError("unknown internal worker")
    mod = load("compose")
    span, output = (Path(a).resolve() for a in args[:2])
    scale, ox, oy = map(float, args[2:])
    project = output.parent / (output.stem + "-project")
    project.mkdir(exist_ok=True)
    (project / "media").mkdir(exist_ok=True)
    (project / "vendor").mkdir(exist_ok=True)
    shutil.copyfile(span, project / "media" / "aroll.mp4")
    shutil.copyfile(PLUGIN / "runtime" / "gsap" / "gsap.min.js", project / "vendor" / "gsap.min.js")
    if not (project / "fonts").exists():
        shutil.copytree(PLUGIN / "runtime" / "fonts", project / "fonts")
    inp = {"rate": Fraction(RATE), "total": RATE * 2, "beats": [], "under": [], "hook_f": 0,
           "track": {"keys": [{"f": 0, "scale": scale, "ox": ox, "oy": oy, "layout": "full"}],
                     "tweens": [], "style": {"style": "punch-in"}}}
    page = mod.main_html(inp, *MASTER, []).encode("utf-8")
    assert b"\r" not in page
    (project / "index.html").write_bytes(page)
    cache = project / "cache"
    cache.mkdir(exist_ok=True)
    mod.hf_render(project, output, rt.hyperframes_env(), "ceiling Master span",
                  ["--fps", str(RATE), "--frames-cache-dir", cache, *mod.QUALITY["master"]])
    return 0


def selftest():
    """Pure helpers, no video tools or installed editor runtime state."""
    checks = 0

    def check(name, ok):
        nonlocal checks
        require(ok, name)
        checks += 1

    checker = bytes(255 * ((x + y) % 2) for y in range(16) for x in range(16))
    blurred = bytes(round((4 * v + 5 * (255 - v)) / 9) for v in checker)
    check("Laplacian: checkerboard sharper than 3x3 box blur",
          laplacian_variance(checker, 16, 16) > 50 * laplacian_variance(blurred, 16, 16))
    check("Laplacian: flat plane is zero", laplacian_variance(bytes(256), 16, 16) == 0)
    impulse = bytes(255 if i == 12 else 0 for i in range(25))  # one bright pixel at the centre of a 5x5 plane
    check("Laplacian: cross kernel pinned (centre weight -4, one impulse = 20 * 255^2 / 9)",
          laplacian_variance(impulse, 5, 5) == 20 * 255 ** 2 / 9)
    ramp = bytes(10 * x + 3 * y for y in range(8) for x in range(8))
    check("Laplacian: a linear ramp has zero variance", laplacian_variance(ramp, 8, 8) == 0)
    check("two points: 1.43 scale independent of translation",
          abs(scale_from_points(((10, 20), (50, 80)), ((19.3, 26.6), (76.5, 112.4))) - 1.43) < 1e-12)
    for values, want, order in (
            ({1.0: 100, 1.30: 60}, 1.30, [1.0, 1.30]),
            ({1.0: 100, 1.30: 59.9, 1.25: 59, 1.20: 50, 1.15: 60}, 1.15, [1.0, 1.30, 1.25, 1.20, 1.15]),
            ({1.0: 100, **{s: 50 for s in SEARCH}}, 1.0, [1.0, *SEARCH])):
        calls = []

        def measure(scale):
            calls.append(scale)
            return values[scale]

        value, scores = ceiling_search(measure)
        check(f"ceiling: descending search, inclusive 60 percent, result {want}",
              value == want and calls == order and list(scores) == order)
    try:
        ceiling_search(lambda _: 0)
    except ValueError:
        check("ceiling: refuse zero-detail baseline", True)
    else:
        check("ceiling: refuse zero-detail baseline", False)
    log = ("[blackdetect @ a] black_start:1.2 black_end:2 black_duration:0.8\n"
           "[freezedetect @ a] lavfi.freezedetect.freeze_start: 4\n"
           "[freezedetect @ a] lavfi.freezedetect.freeze_duration: 3.25\n"
           "[freezedetect @ a] lavfi.freezedetect.freeze_end: 7.25\n"
           "[freezedetect @ a] lavfi.freezedetect.freeze_start: 9\n")
    check("TRI-2: black/freeze intervals and freeze through EOF",
          parse_tri2(log, 12) == {"black": [.8], "frozen": [3.25, 3.0]})
    check("TRI-2: no detections", parse_tri2("frame=1800\n", 60) == {"black": [], "frozen": []})
    check("TRI-2: first passing frame-grid threshold", clean_threshold(.5, [.8], 30) == 25 / 30)
    check("TRI-2: clean defaults unchanged", (clean_threshold(.5, []), clean_threshold(3, [])) == (.5, 3))
    # Exercise same-moment registration on independently planted textured images.
    w, h, origin, scale = 160, 200, (80, 70), 1.43
    ref = bytes(round(128 + 40 * math.sin(x * .21) + 35 * math.cos(y * .29)
                      + 25 * math.sin(x * .31 + y * .19)) for y in range(h) for x in range(w))
    got = bytes(round(sample(ref, w, h, origin[0] + (x - origin[0]) / scale,
                             origin[1] + (y - origin[1]) / scale) or 0) for y in range(h) for x in range(w))
    check("same-frame MAE: rendered 1.43 recovered within 2 percent",
          abs(measure_scale(ref, got, w, h, origin) / scale - 1) <= .02)
    small = bytes(round(sample(ref, w, h, origin[0] + (x - origin[0]) / .95,
                               origin[1] + (y - origin[1]) / .95) or 0)
                  for y in range(h) for x in range(w))
    check("same-frame MAE: search includes the 0.95 endpoint",
          measure_scale(ref, small, w, h, origin) == .95)
    masked = bytearray(got)
    for y in range(40, 100):
        masked[y * w + 32:y * w + 128] = bytes([255]) * 96
    check("same-frame MAE: title/card pixels excluded from the fit",
          abs(measure_scale(ref, masked, w, h, origin, excluded=((32, 40, 128, 100),)) / scale - 1) <= .02)
    with tempfile.TemporaryDirectory(prefix="styles-filter-selftest-") as tmp:
        ref_path, got_path = Path(tmp) / "ref.raw", Path(tmp) / "got.raw"
        ref_path.write_bytes(bytes(reversed(ref)) + ref)
        got_path.write_bytes(bytes(len(got)) + got)
        f, value = measure_frame((7, ref_path, got_path, len(ref), (w, h), origin, ()))
        check("same-frame MAE: disk worker uses matching frame offsets despite source motion",
              f == 7 and abs(value / scale - 1) <= .02)
        graph = "select='" + "+".join(f"eq(n,{n})" for n in range(0, 20000, 2)) + "',format=gray"
        path = Path(tmp) / "selected frames.filter"
        args = frame_filter_args(path, graph)
        check("frame extraction: long graph stays in an LF filter script, off the command line",
              len(subprocess.list2cmdline(args)) < 512 and args == ["-/filter:v", str(path)]
              and path.read_bytes() == (graph + "\n").encode("utf-8"))
    check("frame extraction: contiguous frames collapse to one between() run",
          select_expr(range(100, 600)) == "between(n,100,599)"
          and select_expr([5, 1, 2, 3, 9]) == "between(n,1,3)+eq(n,5)+eq(n,9)")
    # RGB, object-fit:cover, and the pip inset use the same registration path.
    rgb_ref = bytes(c for v in ref for c in (v, 255 - v, v // 2))
    pill = bytearray(bytes(PLATE) * (w * h))
    for y in range(10, 82):
        for x in range(110, 150):
            v = sample(ref, w, h, w / 2 + (x - 130) / .36, h / 2 + (y - 46) / .36)
            if v is not None:
                i = (y * w + x) * 3
                pill[i:i + 3] = bytes((round(v), round(255 - v), round(v / 2)))
    fitted, mae, psnr = fit_scale(rgb_ref, pill, w, h, origin, box=(110, 10, 40, 72), channels=3)
    check("pip: inset RGB rectangle fits covered source independently of the plate",
          fitted == 1.0 and mae < 1 and psnr > 45)
    flat = bytes((120, 130, 140)) * (PREVIEW[0] * PREVIEW[1])
    salted = bytearray(flat)
    i = (768 * PREVIEW[0] + 180) * 3  # "full" probe (.25, .6)
    salted[i:i + 3] = bytes((255, 255, 255))
    check("layout: one salt pixel at a video probe fails a single-pixel compare, passes the 9x9 block mean",
          max(abs(a - b) for a, b in zip(rgb_at(salted, 180, 768), rgb_sample(flat, 180, 768))) > 18
          and layout_pixels(bytes(salted), flat, "full")[0] <= 18)
    check("face region scales with punch", len(crop_gray(bytes(1080 * 1920), 1080, 1920, (540, 600), 216 * 1.25)[0]) == 270 ** 2)
    print(f"selftest ok ({checks} checks)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--selftest", action="store_true")
    action.add_argument("--write-tuning", action="store_true")
    action.add_argument("--case", choices=(*CASES, "all"))
    parser.add_argument("--take", default=os.environ.get("EDITOR_SE_TEST_TAKE"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--keep", action="store_true", help="retain --out, required for cached one-case-per-call runs")
    a = parser.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.write_tuning and a.out is None:
        parser.error("--write-tuning needs the --out containing measured ceiling and tri2 results")
    if a.write_tuning:
        h = Harness(a.out.resolve())
        write_tuning(h)
        return 0
    require_heavy_lock()  # before creating any scratch or starting any video tool
    out = a.out.resolve() if a.out else Path(tempfile.mkdtemp(prefix="editor-styles-render-"))
    if out == REPO or out.is_relative_to(REPO) or REPO.is_relative_to(out):
        raise ValueError("--out must be outside this checkout and cannot contain it")
    existed = out.exists()
    if existed and any(out.iterdir()) and not (out / "styles-render-owned.json").is_file():
        raise ValueError("nonempty --out was not created by this test; choose a fresh directory")
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "styles-render-owned.json", {"schema": 1, "purpose": "S6c.4 test artifacts"})
    h = Harness(out)
    take = Path(a.take).expanduser().resolve() if a.take else None
    names = CASES if a.case in (None, "all") else (a.case,)
    failed = []
    try:
        for name in names:
            h.name, h.deadline = name, time.monotonic() + 580
            start = time.monotonic()
            result_path = out / (name + ".json")
            if name != "build":
                result_path.unlink(missing_ok=True)  # no stale pass after a failed rerun
            try:
                if name == "build":
                    result = build(h, take)
                else:
                    info = h.build_info()
                    if take and source_id(take) != info["source"]:
                        raise ValueError("--take differs from the cached build")
                    result = (punch(h, name) if name.startswith("punch-") else
                              {"layout-switch": layout_switch, "follow-cam": follow_cam,
                               "ceiling": ceiling, "tri2": tri2}[name](h))
                    h.remaining()
                    write_json(result_path, {"status": "passed", "build_id": info["id"],
                                             "seconds": round(time.monotonic() - start, 3), **result})
                h.remaining()
                print(f"PASS {name}: {time.monotonic() - start:.1f} s", flush=True)
            except (AssertionError, OSError, ValueError, KeyError, StopIteration, RuntimeError, TimeoutError,
                    subprocess.SubprocessError) as exc:
                failed.append(name)
                print(f"FAIL {name}: {type(exc).__name__}: {exc}", flush=True)
                if name != "build":
                    write_json(result_path, {"status": "failed", "reason": str(exc),
                                             "seconds": round(time.monotonic() - start, 3)})
                if name == "build":
                    break
        print("all passed" if not failed else "failed: " + ", ".join(failed), flush=True)
        return 1 if failed else 0
    finally:
        if not a.keep:
            # Only remove a verified test-owned tree, never a computed parent or a symlink target.
            resolved = out.resolve()
            if resolved != out or out.is_symlink() or not (out / "styles-render-owned.json").is_file():
                raise RuntimeError("cleanup refused: output ownership/path changed")
            shutil.rmtree(out)
        else:
            print("kept outputs: " + str(out), flush=True)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 2 and sys.argv[1] == "--_worker":
            sys.exit(worker(sys.argv[2], sys.argv[3:]))
        sys.exit(main())
    except (AssertionError, OSError, ValueError, KeyError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        print(f"FAIL {type(exc).__name__}: {exc}", flush=True)
        sys.exit(1)
