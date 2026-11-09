# Changed from shorts-studio scripts/lipsync_check.py (MIT): current-cut/raw frame matching, shared conform geometry, normalised correlation, bounded single-pass decoding, pre-check rows and standalone exit.
"""Catch a cut camera file left over from an older cuts.json, before composition.

python lipsync_check.py <reel_dir>

Match up to twelve half-second pieces by FRAME NUMBER, searching two seconds
either side of the current source position. Each file gets one selected-frame
ffmpeg decode, shared by all pieces (including repeated uses of a raw take).
Spatial normalisation tolerates exposure/contrast changes. Static pictures are
uncheckable, not evidence of stale media. No cut video yet means no rows.
Reported offsets are output seconds (source offset divided by playback speed).
No files are written by this check.
"""
import argparse
from array import array
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

try:
    import numpy as np
except ImportError:
    np = None

PHASE = "pre"
W, H = 64, 114
MAX_PIECES = 12
MIN_CORRELATION, MIN_GAIN = 0.70, 0.025
_render = None


def render_module():
    """render and review_page import only stdlib and runtime; reuse its geometry."""
    global _render
    if _render is None:
        path = HERE.parents[1] / "reel-first-cuts/scripts/render.py"
        sys.path.insert(0, str(path.parent))
        spec = importlib.util.spec_from_file_location("_lipsync_render", path)
        _render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_render)
    return _render


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def local_path(reel, value):
    p = Path(value)
    return p.resolve() if p.is_absolute() else (reel / p).resolve()


def unchecked(where, reason):
    return [dict(check="lipsync-unchecked", level="warn", where=str(where),
                 msg="The video timing could not be checked: %s. Ask Claude to check it before rendering." % reason)]


def probe(path):
    p = subprocess.run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames,width,height,color_transfer", "-of", "json", str(path)],
                       capture_output=True, check=True, timeout=120)
    return json.loads(p.stdout)["streams"][0]


def select_ranges(numbers):
    """Coalesce all needed frame numbers into a single select expression."""
    numbers = sorted(numbers)
    runs = []
    for n in numbers:
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    return "+".join("between(n,%d,%d)" % (a, b) for a, b in runs)


def normalise(frame):
    if np is not None:
        f = np.frombuffer(frame, dtype=np.uint8).astype(np.float32)
        std = float(f.std())
        return (f - f.mean()) / std if std >= 2.0 else None
    mean = sum(frame) / len(frame)
    std = math.sqrt(sum((v - mean) ** 2 for v in frame) / len(frame))
    return array("f", ((v - mean) / std for v in frame)) if std >= 2.0 else None


def decode(path, numbers, geometry=""):
    """No seeking, timestamps or output fps conversion: select uses input n."""
    numbers = sorted(numbers) if numbers is not None else None
    if numbers == []:
        return {}
    vf = "select='%s'," % select_ranges(numbers) if numbers is not None else ""
    vf += (geometry + "," if geometry else "") + "scale=%d:%d:flags=area,format=gray" % (W, H)
    p = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-i", str(path), "-map", "0:v:0",
                        "-an", "-vf", vf, "-fps_mode", "passthrough", "-pix_fmt", "gray",
                        "-f", "rawvideo", "pipe:1"], capture_output=True, check=True, timeout=180)
    size = W * H
    if len(p.stdout) % size:
        raise ValueError("incomplete picture data")
    if numbers is None:
        numbers = range(len(p.stdout) // size)
    # Missing trailing frames (a search window beyond EOF) are simply absent.
    return {n: normalise(p.stdout[i * size:(i + 1) * size])
            for i, n in enumerate(numbers[:len(p.stdout) // size])}


def correlation(a, b):
    if np is not None:
        return float(np.dot(a, b)) / (W * H)
    return sum(x * y for x, y in zip(a, b)) / (W * H)


def pieces(cuts, sources):
    fps, speed = float(cuts["fps"]), float(cuts.get("speed", 1.0))
    size = max(2, round(fps * 0.5))
    candidates = []
    for seg in cuts["segments"]:
        length = seg["out_out_f"] - seg["out_in_f"]
        if length < 2:
            continue
        width = min(size, length)
        starts = list(range(0, length - width + 1, size))
        if starts[-1] != length - width:
            starts.append(length - width)
        for k in starts:
            src = [round(seg["src_in_f"] + (k + j) * speed) for j in range(width)]
            candidates.append(dict(out=list(range(seg["out_in_f"] + k, seg["out_in_f"] + k + width)),
                                   src=src, path=sources[str(seg.get("take", 1))][0]))
    if len(candidates) > MAX_PIECES:
        candidates = [candidates[round(i * (len(candidates) - 1) / (MAX_PIECES - 1))]
                      for i in range(MAX_PIECES)]
    return candidates


def match(piece, master, raw, radius):
    target = [master.get(n) for n in piece["out"]]
    if any(f is None for f in target):
        return None
    # A static face or a flat plate cannot locate the source moment reliably.
    if 2.0 - 2.0 * correlation(target[0], target[-1]) < 0.001:
        return None
    scores = {}
    for lag in range(-radius, radius + 1):
        frames = [raw.get(n + lag) for n in piece["src"]]
        if any(f is None for f in frames):
            continue
        scores[lag] = sum(correlation(a, b) for a, b in zip(target, frames)) / len(target)
    if 0 not in scores:
        return None
    best = max(scores, key=lambda n: (scores[n], -abs(n)))
    if scores[best] < MIN_CORRELATION:
        return None
    # Compare with the whole allowed +/-1-frame neighbourhood too: rounding or
    # an allowed one-frame offset must not turn into a grade-induced false block.
    baseline = max(scores.get(n, -1) for n in (-1, 0, 1))
    return best, scores[best] - baseline


def run(ctx):
    reel = Path(ctx["reel_dir"]).resolve()
    work = reel / "work"
    try:
        cuts = ctx.get("cuts")
        if cuts is None:
            cuts = read(work / "cuts.json")
        fps = float(cuts["fps"])
        speed = float(cuts.get("speed", 1.0))
        if not math.isfinite(fps) or fps <= 0 or not math.isfinite(speed) or speed <= 0:
            raise ValueError("invalid cut rate")
        segs = cuts["segments"]
        if not segs:
            return unchecked(work / "cuts.json", "the cut has no pieces yet")
        # Exactly compose.load_inputs()'s choice; never newest/first glob match.
        tag = ("%.2fx" % speed).replace(".", "")
        master = work / "renders" / ("master-%s.mp4" % tag)
        if not master.is_file():
            return []
        takes = cuts.get("takes") or {}
        mixed = len(takes) > 1
        sources = {}
        for take in {str(s.get("take", 1)) for s in segs}:
            info = takes.get(take)
            probe_path = local_path(reel, info["work"]) / "probe.json" if mixed else work / "probe.json"
            saved = read(probe_path) if probe_path.is_file() else {}
            raw_name = info.get("raw") if info else saved.get("input")
            if not raw_name:
                return unchecked(probe_path, "the original recording is missing; restore it")
            raw = local_path(reel, raw_name)
            if not raw.is_file():
                return unchecked(raw, "the original recording is missing; restore it")
            sources[take] = (raw, saved.get("video"), take)
        # Missing raw always warns, even if the master also has the wrong length.
        total = segs[-1]["out_out_f"]
        recorded_count = probe(master).get("nb_frames", "")
        camera = None
        if str(recorded_count).isdigit():
            got = int(recorded_count)
        else:
            # A container without a count needs a decode to count frames. Keep
            # that same tiny decode for matching; never decode the file twice.
            camera = decode(master, None)
            got = len(camera)
        if got != total:
            return [dict(check="camera-stale", level="block", where=str(master), at=0.0,
                         msg="The cut video has %d frames, but your latest cut needs %d. "
                             "Ask Claude to remake the cut video." % (got, total))]
        samples = pieces(cuts, sources)
        radius = round(2 * fps)
        needed = {}
        for piece in samples:
            needed.setdefault(piece["path"], set()).update(
                range(max(0, min(piece["src"]) - radius), max(piece["src"]) + radius + 1))
        if camera is None:
            camera = decode(master, {n for piece in samples for n in piece["out"]})
        crop = read(work / "crop.json") if (work / "crop.json").is_file() else None
        raws = {}
        for raw, video, take in sources.values():
            if raw in raws or raw not in needed:
                continue
            video = video or probe(raw)
            geometry = render_module().conform(video, crop if not mixed or take == "1" else None)
            raws[raw] = decode(raw, needed[raw], geometry)
        hits, checked = [], 0
        for piece in samples:
            result = match(piece, camera, raws[piece["path"]], radius)
            if result is None:
                continue
            checked += 1
            offset, gain = result
            if abs(offset) > 1 and gain >= MIN_GAIN:
                at = piece["out"][0] / fps
                hits.append(dict(check="camera-stale", level="block", where=str(master), at=at,
                                 msg="The video and the voice are out of step by about %.2f s from %.2f s: "
                                     "the cut video is older than your latest cut. "
                                     "Ask Claude to remake the cut video." % (abs(offset) / fps / speed, at)))
        return hits if checked else unchecked(master, "the picture changes too little to match reliably")
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError, SystemExit):
        return unchecked(work, "the cut or its pictures could not be read; check the recordings and editor setup")


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    a = ap.parse_args()
    hits = run(dict(reel_dir=a.reel_dir))
    for hit in hits:
        print("%s  %s  %s  (%s)" % (hit["level"].upper(), hit["check"], hit["msg"], hit["where"]))
    if not hits:
        print("lipsync check: clean, the cut video matches your latest cut")
    return 1 if any(h["level"] == "block" for h in hits) else 0


if __name__ == "__main__":
    sys.exit(main())
