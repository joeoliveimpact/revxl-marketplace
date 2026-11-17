"""Hide private areas on ingested B-roll, offline, with ffmpeg and the standard library.

  broll_mask.py check --reel-dir <reel>
  broll_mask.py --selftest
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime as rt
import beat_schema
from win_encoding import ensure_utf8_output

MASK_VERSION = "1"
RETRY = "The private areas could not be checked; save them again or ask Claude to check the clip."


class MaskError(ValueError):
    pass


def _run(tool, args):
    result = subprocess.run([str(rt.tool(tool)), *map(str, args)], capture_output=True,
                            env=rt.python_env(), timeout=600)
    if result.returncode or result.stderr.strip():
        raise MaskError(RETRY)
    return result.stdout


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def mask_key(original_sha, boxes):
    canonical = json.dumps(boxes, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256((original_sha + canonical + MASK_VERSION).encode("utf-8")).hexdigest()


def pixel_box(box, width=1080, height=1920):
    """Even coordinates and sizes, clamped to fit, including sub-pixel boxes."""
    def axis(start, size, limit):
        end = limit // 2 * 2
        pos = max(0, min(end - 2, round(start * limit / 2) * 2))
        length = max(2, min(end - pos, round(size * limit / 2) * 2))
        return pos, length
    x, w = axis(box["x"], box["w"], width)
    y, h = axis(box["y"], box["h"], height)
    return x, y, w, h


def facts(video, *, count=False):
    args = ["-v", "error", "-select_streams", "v:0"]
    if count:
        args += ["-count_frames"]
    args += ["-show_entries", "stream=width,height,r_frame_rate,nb_frames,nb_read_frames", "-of", "json", video]
    stream = json.loads(_run("ffprobe", args))["streams"][0]
    frames = stream.get("nb_read_frames" if count else "nb_frames")
    if frames in (None, "N/A") and not count:
        return facts(video, count=True)
    result = (int(stream["width"]), int(stream["height"]), Fraction(stream["r_frame_rate"]), int(frames))
    if min(result[0], result[1]) < 2 or result[2] <= 0 or result[3] <= 0:
        raise MaskError(RETRY)
    return result


def sample_times(box, rate, frames):
    """At most three actual frame times strictly inside the requested interval."""
    start = max(0, math.ceil(box.get("from", 0) * rate))
    stop = min(frames, math.ceil(box["to"] * rate)) if "to" in box else frames
    if stop <= start:
        return []
    return [float(Fraction(i) / rate) for i in sorted({start, (start + stop - 1) // 2, stop - 1})]


def _valid(boxes):
    if beat_schema.broll_masks_problems({"f00": boxes}):
        raise MaskError(RETRY)


def _complete(path, expected):
    try:
        return path.is_file() and facts(path, count=True) == expected
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError):
        return False


def _filters(boxes, width, height):
    parts, current = [], "0:v"
    for i, box in enumerate(boxes):
        x, y, w, h = pixel_box(box, width, height)
        output = f"m{i}"
        enable = f":enable='between(t,{box['from']},{box['to']})'" if "from" in box else ""
        if box["kind"] == "fill":
            parts.append(f"[{current}]drawbox=x={x}:y={y}:w={w}:h={h}:color=black:t=fill{enable}[{output}]")
        else:
            radius = min(max(2, min(w, h) // 4), min(w, h) // 2)
            parts += [f"[{current}]split=2[base{i}][area{i}]",
                      f"[area{i}]crop={w}:{h}:{x}:{y},scale={max(1, w // 16)}:{max(1, h // 16)}:flags=area,"
                      f"scale={w}:{h}:flags=bilinear,boxblur=luma_radius={radius}:luma_power=2:chroma_radius=0:chroma_power=0[blur{i}]",
                      f"[base{i}][blur{i}]overlay=x={x}:y={y}:format=yuv420{enable}[{output}]"]
        current = output
    return ";".join(parts), current


def masked_copy(reel, src_rel, boxes):
    source = Path(reel) / src_rel
    if not boxes:
        return source
    _valid(boxes)
    width, height, rate, frames = expected = facts(source)
    key = mask_key(sha256(source), boxes)
    folder = Path(reel) / "broll/masked"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{source.stem}-{key[:12]}.mp4"
    if _complete(target, expected):
        return target
    fd, name = tempfile.mkstemp(prefix=".mask-", suffix=".mp4", dir=folder)
    os.close(fd)
    partial = Path(name)
    try:
        filters, output = _filters(boxes, width, height)
        _run("ffmpeg", ["-v", "error", "-y", "-fflags", "+bitexact", "-i", source,
                        "-filter_complex_threads", "1", "-filter_complex", filters, "-map", f"[{output}]",
                        "-an", "-sn", "-dn", "-c:v", "libx264", "-preset", "fast", "-crf", "8",
                        "-pix_fmt", "yuv420p", "-threads", "1", "-flags:v", "+bitexact", "-fflags", "+bitexact",
                        "-map_metadata", "-1", "-r", rate, "-frames:v", frames, partial])
        if not _complete(partial, expected):
            raise MaskError(RETRY)
        os.replace(partial, target)
        return target
    finally:
        partial.unlink(missing_ok=True)


def gray_region(video, box_px, t):
    x, y, w, h = box_px
    data = _run("ffmpeg", ["-v", "error", "-ss", f"{t:.9f}", "-i", video, "-frames:v", "1",
                           "-vf", f"crop={w}:{h}:{x}:{y},format=gray", "-an", "-f", "rawvideo", "pipe:1"])
    if len(data) != w * h:
        raise MaskError(RETRY)
    return data


def edge_energy(pixels, width, height):
    """Mean absolute four-neighbour Laplacian; no padding at the boundary."""
    if width < 3 or height < 3:
        return 0.0
    total = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            i = y * width + x
            total += abs(4 * pixels[i] - pixels[i - 1] - pixels[i + 1] - pixels[i - width] - pixels[i + width])
    return total / ((width - 2) * (height - 2))


def edge_energy_of(video, box_px, t):
    return edge_energy(gray_region(video, box_px, t), box_px[2], box_px[3])


def _clip_name(reel, src_rel):
    """Find the ledger id without changing the ledger or trusting a masked file."""
    try:
        doc = json.loads((Path(reel) / "beat-map-selection.json").read_text(encoding="utf-8"))
        for beat in doc["beats"]:
            clip = beat.get("broll")
            if clip and clip["src"] == src_rel:
                return clip["ledger_id"]
        rows = json.loads((Path(reel) / "footage/ledger.json").read_text(encoding="utf-8"))
        for row in rows:
            if (Path(reel) / row["path"]).resolve() == (Path(reel) / src_rel).resolve():
                return row["id"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return Path(src_rel).stem


def check(reel, src_rel, boxes, masked_path):
    if not boxes:
        return []
    ident = _clip_name(reel, src_rel)
    try:
        _valid(boxes)
        source = Path(reel) / src_rel
        width, height, rate, frames = expected = facts(source)
        if not _complete(Path(masked_path), expected):
            raise MaskError(RETRY)
        problems = []
        for i, box in enumerate(boxes, 1):
            box_px = pixel_box(box, width, height)
            times = sample_times(box, rate, frames)
            if not times:
                problems.append(f"Box {i} on clip {ident} has no picture at its times; set its times again.")
            for t in times:
                original = edge_energy_of(source, box_px, t)
                pixels = gray_region(masked_path, box_px, t)
                energy = edge_energy(pixels, box_px[2], box_px[3])
                clean = energy <= original * .1 or energy <= 1.5
                if box["kind"] == "fill":
                    clean = sum(pixels) / len(pixels) <= 16 and energy <= 1.5
                if not clean:
                    problems.append(f"Box {i} on clip {ident} is still readable at {t:.1f} s; hide it again before rendering.")
        return problems
    except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.SubprocessError):
        return [f"The private areas on clip {ident} could not be checked; save them again or ask Claude to check the clip."]


def selftest():
    box = dict(x=.1, y=.2, w=.3, h=.1, kind="blur")
    assert pixel_box(box) == (108, 384, 324, 192)
    assert pixel_box(dict(box, x=.999999, y=.999999, w=.000001, h=.000001)) == (1078, 1918, 2, 2)
    assert pixel_box(dict(box, x=0, y=0, w=1.0000005, h=1)) == (0, 0, 1080, 1920)
    assert mask_key("a" * 64, [box]) == mask_key("a" * 64, [dict(reversed(list(box.items())))])
    assert mask_key("a" * 64, [box]) != mask_key("b" * 64, [box])
    assert mask_key("a" * 64, [box]) != mask_key("a" * 64, [dict(box, kind="fill")])
    assert sample_times(box, Fraction(25), 100) == [0, 1.96, 3.96]
    ranged = dict(box, **{"from": 1.01, "to": 1.13})
    assert sample_times(ranged, Fraction(25), 100) == [1.04, 1.08, 1.12]
    assert sample_times(dict(box, **{"from": 5, "to": 6}), Fraction(25), 100) == []
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    command = sub.add_parser("check")
    command.add_argument("--reel-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.cmd != "check":
        ap.print_help()
        return 2
    try:
        doc = json.loads((args.reel_dir / "beat-map-selection.json").read_text(encoding="utf-8"))
        beat_schema.validate_beat_map(doc)
        problems = []
        for ident, boxes in doc.get("broll_masks", {}).items():
            if not boxes:
                continue
            clips = {b["broll"]["src"] for b in doc["beats"] if b.get("broll") and b["broll"]["ledger_id"] == ident}
            if not clips:
                clips = {c["src"] for c in json.loads((args.reel_dir / "broll/clips.json").read_text(encoding="utf-8"))["clips"]
                         if c["ledger_id"] == ident}
            if not clips:
                problems.append(f"Clip {ident} is missing; restore it or remove its hidden areas.")
            for src in sorted(clips):
                problems += check(args.reel_dir, src, boxes, masked_copy(args.reel_dir, src, boxes))
        for line in problems:
            print(line)
        return 1 if problems else 0
    except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.SubprocessError):
        print(RETRY)
        return 1


if __name__ == "__main__":
    sys.exit(main())
