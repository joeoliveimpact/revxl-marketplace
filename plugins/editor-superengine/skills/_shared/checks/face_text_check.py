#!/usr/bin/env python3
"""Post-render check: captions leave the face clear and have readable contrast.

Usage: python face_text_check.py <reel_dir> [--render <mp4>]
Without --render, use the newest renders/* Master - *.mp4 by modification time.
Exit 1 on any block, otherwise 0. This check writes nothing; stdlib only.

H-B6: PHASE = "post"; run(ctx) returns [{check, level, msg, where, at?}],
ctx = {reel_dir, fps, cuts, beats, render}. Caption and beat ends are exclusive.
Sample caption midpoints, or beat midpoints without captions. Decode by frame
NUMBER (F-12), never seek by time. Placer supplies the protected head envelope
on its 1080x1920 grid, including its unsafe margin. Settled layout, cover-fit,
zoom and origin are inverted to compare the same a-roll pixels. Active moves
have conservative envelopes rather than an exact mapping: skip those samples.
Scenes/b-roll hiding the a-roll are skipped too (pip remains above them).

Face differences must exceed 36 RGB levels in at least 12% of the protected
box, allowing normal compression/resampling noise. Contrast is the WCAG-style
ratio of mean linear RGB luminance in the brightest/darkest 10% of the caption
box; below 3 blocks. This is a rendered-pixel heuristic, not text recognition.
Missing face inputs warn once; missing captions produce no contrast findings.
"""
import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "post"
LINEAR = tuple(v / 255 / 12.92 if v / 255 <= 0.04045 else
               ((v / 255 + 0.055) / 1.055) ** 2.4 for v in range(256))


def row(check, level, msg, where, **extra):
    return dict(check=check, level=level, msg=msg, where=str(where), **extra)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def command(name, *args, timeout=120):
    p = subprocess.run([rt.tool(name), *map(str, args)], env=rt.python_env(),
                       capture_output=True, timeout=timeout)
    if p.returncode:
        raise ValueError("The media tool could not read the picture.")
    return p.stdout


def dimensions(path):
    info = json.loads(command("ffprobe", "-v", "error", "-select_streams", "v:0",
                              "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
                              "-of", "json", path))
    stream = info["streams"][0]
    duration = float(info["format"]["duration"])
    width, height = int(stream["width"]), int(stream["height"])
    if width <= 0 or height <= 0 or not math.isfinite(duration) or duration <= 0:
        raise ValueError("The picture size could not be read.")
    # Retain aspect ratio, keep decoded frames small, never upscale.
    factor = min(1, 360 / width, 640 / height)
    return (max(1, round(width * factor)), max(1, round(height * factor)),
            stream["avg_frame_rate"], duration)


def frames(path, numbers, size, duration):
    """Decode every requested frame number in one pass, in ascending order."""
    numbers = sorted(set(numbers))
    if not numbers:
        return {}
    w, h = size
    select = "+".join(f"eq(n,{number})" for number in numbers)
    data = command("ffmpeg", "-nostdin", "-v", "error", "-i", path,
                   "-map", "0:v:0", "-vf", f"select='{select}',scale={w}:{h}",
                   "-vsync", "0", "-frames:v", str(len(numbers)), "-an", "-sn", "-threads", "1",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-", timeout=60 + 2 * duration)
    frame_bytes = w * h * 3
    if len(data) % frame_bytes:
        raise ValueError("The requested picture frame could not be read.")
    # Missing late frames remain absent, so earlier samples can still be checked.
    pixels = memoryview(data)
    return {number: pixels[i * frame_bytes:(i + 1) * frame_bytes]
            for i, number in enumerate(numbers) if (i + 1) * frame_bytes <= len(data)}


def pixel_box(box, size, master_size=(1080, 1920)):
    w, h = size
    mw, mh = master_size
    x0, y0, x1, y1 = box
    return (max(0, min(w, math.ceil(x0 * w / mw))),
            max(0, min(h, math.ceil(y0 * h / mh))),
            max(0, min(w, math.floor(x1 * w / mw))),
            max(0, min(h, math.floor(y1 * h / mh))))


def contrast(data, size, box):
    w, _ = size
    x0, y0, x1, y1 = pixel_box(box, size)
    luminance = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            i = (y * w + x) * 3
            luminance.append(0.2126 * LINEAR[data[i]] + 0.7152 * LINEAR[data[i + 1]]
                             + 0.0722 * LINEAR[data[i + 2]])
    if not luminance:
        raise ValueError("The caption box has no visible pixels.")
    luminance.sort()
    count = max(1, math.ceil(len(luminance) * 0.1))
    return (sum(luminance[-count:]) / count + 0.05) / (sum(luminance[:count]) / count + 0.05)


def aroll_path(reel, cuts):
    # Compose chooses the cut's speed tag, not the newest unrelated work render.
    if "speed" in cuts:
        tag = ("%.2fx" % cuts["speed"]).replace(".", "")
        exact = reel / "work/renders" / f"master-{tag}.mp4"
        if exact.is_file():
            return exact
    candidates = list((reel / "work/renders").glob("master-*.mp4"))
    # A single alternate tag supports imported masters (and master-test fixtures).
    return candidates[0] if len(candidates) == 1 else None


def mapping(placer, pc, number):
    if any(t["start_f"] <= number < t["end_f"] for t in pc["track"]["tweens"]):
        return None
    scale, origin, layout = [placer._options(pc, p, number)[0]
                             for p in ("scale", "origin", "layout")]
    if scale <= 0:
        return None
    # B-roll and scenes cover the a-roll except when it is the foreground pip.
    pip = pc["layouts"].get("pip")
    for beat in pc["beats"]:
        if beat["start_f"] <= number < beat["end_f"] and (beat.get("broll") or beat.get("scene")):
            if layout != pip:
                return None
    return scale, origin, layout


def face_changed(rendered, size, source, src_size, box, transform, master_size):
    """Inverse of placer._map before clipping; bilinear RGB for subpixel samples."""
    scale, origin, (bx, by, bw, bh) = transform
    mw, mh = master_size
    cover = max(bw / mw, bh / mh)
    dx, dy = (bw - mw * cover) / 2, (bh - mh * cover) / 2
    ox, oy = origin[0] * bw, origin[1] * bh
    w, h = size
    sw, sh = src_size
    x0, y0, x1, y1 = pixel_box(box, size, master_size)
    changed = total = 0
    for y in range(y0, y1):
        sy = (((y + 0.5) * mh / h - by - oy) / scale + oy - dy) / cover * sh / mh - 0.5
        for x in range(x0, x1):
            sx = (((x + 0.5) * mw / w - bx - ox) / scale + ox - dx) / cover * sw / mw - 0.5
            if not (-0.5 <= sx < sw - 0.5 and -0.5 <= sy < sh - 0.5):
                continue
            sx, sy_clamped = max(0, min(sw - 1, sx)), max(0, min(sh - 1, sy))
            ix, iy = int(sx), int(sy_clamped)
            fx, fy = sx - ix, sy_clamped - iy
            ix1, iy1 = min(sw - 1, ix + 1), min(sh - 1, iy + 1)
            indices = ((iy * sw + ix) * 3, (iy * sw + ix1) * 3,
                       (iy1 * sw + ix) * 3, (iy1 * sw + ix1) * 3)
            i = (y * w + x) * 3
            difference = 0
            for channel in range(3):
                a, b, c, d = (source[j + channel] for j in indices)
                expected = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
                difference += abs(rendered[i + channel] - expected)
            changed += difference / 3 > 36
            total += 1
    return total > 0 and changed / total >= 0.12


def run(ctx):
    reel = Path(ctx["reel_dir"])
    out = []
    render = ctx.get("render")
    if render is None:
        render = max((reel / "renders").glob("* Master - *.mp4"),
                     key=lambda p: p.stat().st_mtime_ns, default=None)
    if render is None or not Path(render).is_file():
        return [row("no-render", "block", "There is no finished Master to check; render it first.", reel / "renders")]
    render = Path(render)
    errors = (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError,
              ZeroDivisionError, subprocess.SubprocessError)
    try:
        size_info = dimensions(render)
        size = size_info[:2]
        cuts = ctx.get("cuts")
        if cuts is None:
            cuts = read(reel / "work/cuts.json") if (reel / "work/cuts.json").is_file() else {}
        rate = Fraction(str(ctx.get("fps") or cuts.get("fps") or size_info[2]))
        if rate <= 0:
            raise ValueError("Invalid frame rate")
    except errors:
        return [row("render-unreadable", "block", "The Master's picture or frame rate could not be read; "
                    "check the cut files and render it again.", render)]
    caps_path = reel / "work/captions.json"
    try:
        chunks = read(caps_path)["chunks"] if caps_path.is_file() else []
        for chunk in chunks:
            a, e = chunk["start_f"], chunk["end_f"]
            box = chunk["box"]
            if not (type(a) is int and type(e) is int and 0 <= a < e and len(box) == 4
                    and all(isinstance(v, (int, float)) and math.isfinite(v) for v in box)
                    and box[0] < box[2] and box[1] < box[3]):
                raise ValueError("Invalid caption box or frames")
    except errors:
        return [row("captions-unreadable", "block", "The caption positions or frames could not be read; "
                    "build the captions again before checking the picture.", caps_path)]
    pc = source = src_size = None
    try:
        sys.path.insert(0, str(HERE.parents[2] / "reel-canvas-build/scripts"))
        import placer
        pc = placer.load_ctx(reel)
        source = aroll_path(reel, cuts)
        if pc["median_box"] is None or source is None:
            raise ValueError("Missing face inputs")
        src_info = dimensions(source)
        src_size, src_duration = src_info[:2], src_info[3]
    except errors:
        out.append(row("face-unchecked", "warn", "The original picture or face track is missing or unreadable, "
                       "so the face is unchecked; restore the cut master and run the face step again.", reel / "work"))
        pc = None
    try:
        spans = chunks
        if not spans:
            beats = ctx.get("beats")
            if beats is None:
                beats = pc["beats"] if pc else read(reel / "beat-map-selection.json")["beats"]
            spans = beats
        samples = sorted({(s["start_f"] + s["end_f"]) // 2 for s in spans})
    except errors:
        out.append(row("beats-unreadable", "warn", "The beat positions could not be read; send the Beat Map "
                       "again to check the face without captions.", reel / "beat-map-selection.json"))
        samples = []
    try:
        pictures = frames(render, samples, size, size_info[3])
    except errors:
        pictures = {}
    originals = None
    for number in samples:
        at = float(Fraction(number) / rate)
        try:
            picture = pictures[number]
            # Shared midpoints reuse the same decoded pixels.
            for chunk in chunks:
                if (chunk["start_f"] + chunk["end_f"]) // 2 != number:
                    continue
                ratio = contrast(picture, size, chunk["box"])
                if ratio < 3:
                    out.append(row("low-contrast", "block", f"The caption at {at:.2f} seconds is hard to read "
                                   "against the picture behind it. Use a clearer text or plate colour.",
                                   caps_path, at=at))
            if pc is None:
                continue
            transform = mapping(placer, pc, number)
            if transform is None:
                continue
            head = placer.head_box_at(pc, number, number)
            if head is None:
                continue
            try:
                if originals is None:
                    originals = frames(source, samples, src_size, src_duration)
                original = originals[number]
            except errors:
                if not any(r["check"] == "face-unchecked" for r in out):
                    out.append(row("face-unchecked", "warn", "The original picture could not be read, so the face "
                                   "is unchecked; restore the cut master and check again.", source))
                pc = None
                continue
            if face_changed(picture, size, original, src_size, head, transform, pc["master_size"]):
                out.append(row("face-covered", "block", f"Something covers the speaker's face at {at:.2f} seconds; "
                               "move the caption or graphic clear of the face and render again.", render, at=at))
        except errors:
            out.append(row("picture-unreadable", "block", f"The picture or caption at {at:.2f} seconds could not "
                           "be checked; rebuild the captions and render again.", render, at=at))
    return out


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    ap.add_argument("--render", type=Path)
    args = ap.parse_args()
    findings = run(dict(reel_dir=args.reel_dir, render=args.render))
    for hit in findings:
        print("%s  %s  %s  (%s)" % (hit["level"].upper(), hit["check"], hit["msg"], hit["where"]))
    blocks = sum(h["level"] == "block" for h in findings)
    print(f"face/text check: {blocks} block(s), {len(findings) - blocks} warning(s)")
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
