"""G6: offline cover candidates and a truthful, head-clear optional title.

candidates --reel-dir videos/REEL_A [--video PATH]
apply --reel-dir videos/REEL_A
--selftest
All frame reads select by output frame number. Failures are one plain line.
"""
import argparse
import contextlib
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parents[2]
sys.path[:0] = [str(P / "skills/_shared"), str(P / "skills/_shared/checks"),
               str(P / "skills/reel-canvas-build/scripts"), str(P / "skills/caption-writer/scripts")]
try:
    import numpy as np
    from PIL import Image
    import runtime as rt
    import face_text_check as face
    import check_caption
    from check_caption import numbers
    from win_encoding import ensure_utf8_output
except Exception:
    print("The cover tools could not load; restore the editor installation and try again.")
    sys.exit(1)

W, H = 1080, 1920
TITLE_X, TITLE_W = 60, 900
# cover-title scene: two named Inter sizes, their line heights, 24px plate padding.
TITLE_FONT_SIZE, TITLE_LINE_HEIGHT, TITLE_PADDING, TITLE_MAX_LINES = 72, 79.2, 24, 2
TITLE_SIZES = {"normal": (TITLE_FONT_SIZE, TITLE_LINE_HEIGHT), "smaller": (60, 66)}
TITLE_MAX_CHARS = 28
TITLE_LIMIT = f"Keep the cover title to at most six words and {TITLE_MAX_CHARS} letters."
TITLE_REFUSAL = ("The title doesn't fit beside your face on this frame, even one size smaller. "
                 "Use a shorter title, or pick another cover frame from the picker.")
NO_FACE_NOTE = ("note: no face position for this frame, so the title sits low on the cover; "
                "check it clears your face before you post.")
TITLE_CONTENT_W = TITLE_W - 2 * TITLE_PADDING
HEAD_BAND_FRACTION = .6
FRAME_CHUNK_SIZE = 40
TITLE_TOP, TITLE_BOTTOM, GAP = 220, 1470, 24


class Stop(Exception):
    """A client-readable failure, without tool output or a traceback."""

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop("Choose candidates or apply and give the reel folder; ask the editor to run it again.")


def read(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate key")
            out[key] = value
        return out
    def invalid(value):
        raise ValueError("non-finite number")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=invalid)
    except (OSError, ValueError):
        raise Stop("A required reel file could not be read; restore it or Send the Cover Picker again.") from None


def save(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    temp.replace(path)


def source_words(reel):
    doc = read(Path(reel) / "work/edit_map.cut.json")
    words = doc.get("words") if isinstance(doc, dict) else None
    if not isinstance(words, list) or not words or not all(isinstance(w, dict) and isinstance(w.get("word"), str) for w in words):
        raise Stop("This reel needs its own cut word list before choosing a cover title.")
    return " ".join(w["word"] for w in words)


def tokens(text):
    return [word for part in text.split() if (word := re.sub(r"[^\w]", "", part, flags=re.UNICODE).casefold())]


def validate_title(title, source):
    if title is None or title == "":
        return None
    if not isinstance(title, str):
        raise Stop("The cover title must be a short line of words from this reel.")
    title = " ".join(title.split())
    if not title:
        return None
    heard, used = set(tokens(source)), tokens(title)
    if not used or len(title.split()) > 6 or len(title) > TITLE_MAX_CHARS:
        raise Stop(TITLE_LIMIT)
    if any(value not in numbers(source) for value in numbers(title)):
        raise Stop("A number in the cover title was not said in this reel; use its own words and numbers.")
    if any(word not in heard for word in used):
        raise Stop("A word in the cover title was not said in this reel; use its own words.")
    return title


def inside(box):
    return (isinstance(box, (list, tuple)) and len(box) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in box)
            and 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)


def overlaps(a, b):
    """Fractional rectangles; touching edges do not overlap."""
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def head_band(head):
    return (head[0], head[1], head[2], head[1] + HEAD_BAND_FRACTION * (head[3] - head[1]))


def title_lines(title, size="normal"):
    """Measure wrapping in installed Chrome with the scene's shipped Inter font."""
    script = r"""
const fs = require('fs');
const [pup, chrome, font, text, width, size, lineHeight] = JSON.parse(fs.readFileSync(0, 'utf8'));
(async () => {
  const browser = await require(pup).launch({executablePath: chrome, headless: true});
  try {
    const page = await browser.newPage();
    const result = await page.evaluate(async (font, text, width, size, lineHeight) => {
      const face = new FontFace('CoverInter', `url(data:font/woff2;base64,${font})`);
      document.fonts.add(await face.load());
      const el = document.createElement('div');
      Object.assign(el.style, {width: width + 'px', fontFamily: 'CoverInter', fontSize: size + 'px',
        fontWeight: '400', lineHeight: lineHeight + 'px', overflowWrap: 'anywhere'});
      el.textContent = text;
      document.body.append(el);
      return {lines: Math.round(el.getBoundingClientRect().height / lineHeight),
              fits: el.scrollWidth <= el.clientWidth};
    }, fs.readFileSync(font).toString('base64'), text, width, size, lineHeight);
    process.stdout.write(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(() => { process.exitCode = 1; });
"""
    pup = rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
    try:
        result = subprocess.run([rt.tool("node"), "-e", script],
                                input=json.dumps([str(pup), rt.tool("chrome"),
                                      str(P / "runtime/fonts/Inter-Regular.woff2"), title,
                                      TITLE_CONTENT_W, *TITLE_SIZES[size]]),
                                env=rt.python_env(), capture_output=True, text=True, encoding="utf-8", timeout=60)
        measured = json.loads(result.stdout) if result.returncode == 0 else None
        if not isinstance(measured, dict) or type(measured.get("lines")) is not int:
            raise ValueError("missing title measurement")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise Stop("The cover title could not be measured offline; check the editor tools and try again.") from None
    if not measured.get("fits") or measured["lines"] < 1:
        raise Stop("Shorten the title to fit at most two lines.")
    return measured["lines"]


def title_default_y():
    return read(P / "scenes/cover-title/scene.json")["params"]["y"]["default"]


def title_box(head, lines=1, size="normal"):
    if type(lines) is not int or not 1 <= lines <= TITLE_MAX_LINES:
        raise Stop("Shorten the title to fit at most two lines.")
    height = math.ceil(TITLE_SIZES[size][1] * lines + 2 * TITLE_PADDING)
    if head is not None and not inside(head):
        raise Stop("The head box is outside this frame; choose another frame or measure the face again.")
    # The whole-frame box is explicitly unplaceable, even with a reduced band.
    if head is not None and tuple(head) == (0, 0, 1, 1):
        raise Stop(TITLE_REFUSAL)
    band = head_band(head) if head is not None else None
    below = title_default_y() if band is None else max(TITLE_TOP, math.ceil(band[3] * H) + GAP)
    above = below if band is None else min(TITLE_BOTTOM - height, math.floor(band[1] * H) - GAP - height)
    for y in (below, above):
        box = (TITLE_X / W, y / H, (TITLE_X + TITLE_W) / W, (y + height) / H)
        if TITLE_TOP <= y and y + height <= TITLE_BOTTOM and (band is None or not overlaps(box, band)):
            return box
    raise Stop(TITLE_REFUSAL)


def title_placement(head, lines=1, title=None):
    """Try below then above at normal size, then remeasure one named size smaller."""
    if head is not None and not inside(head):
        raise Stop("The head box is outside this frame; choose another frame or measure the face again.")
    for size in TITLE_SIZES:
        measured_lines = title_lines(title, size) if title is not None else lines
        try:
            box = title_box(head, measured_lines, size)
        except Stop:
            continue
        band = head_band(head) if head is not None else None
        assert band is None or not overlaps(box, band)  # protects eyes and mouth inside the band
        return {"box": box, "lines": measured_lines, "size": size}
    raise Stop(TITLE_REFUSAL)


def can_place(head, lines=1):
    try:
        title_placement(head, lines)
        return True
    except Stop:
        return False


def laplacian_variance(gray, width=None, height=None):
    """Population variance of the 3x3 cross Laplacian, discarding the border.

    Port of the styles-render proof, vectorised with numpy; no test import.
    """
    plane = np.asarray(gray, dtype=np.float64)
    if width is not None:
        plane = plane.reshape(height, width)
    if plane.ndim != 2 or min(plane.shape) < 3:
        raise Stop("The frame is too small to score; choose a full reel video.")
    lap = plane[:-2, 1:-1] + plane[2:, 1:-1] + plane[1:-1, :-2] + plane[1:-1, 2:] - 4 * plane[1:-1, 1:-1]
    return float(np.var(lap))


def video_path(reel, video=None):
    if video is not None:
        path = Path(video).resolve()
        if not path.is_file():
            raise Stop("The chosen video is missing; make the cut or final video first.")
        return path
    # A preview or partial render is never mistaken for a finished final.
    finals = [p for p in (reel / "renders").glob("*.mp4")
              if re.fullmatch(r".+ (?:master|final) - \d{2}\.\d{2}\.\d{2}\.mp4", p.name, re.I)]
    choices = finals or list((reel / "work/renders").glob("master-*.mp4"))
    if not choices:
        raise Stop("This reel needs a cut master or final video before picking a cover.")
    return max(choices, key=lambda p: p.stat().st_mtime_ns).resolve()


def video_info(video):
    width, height, rate, duration = face.dimensions(video)
    fps = float(Fraction(rate))
    if not math.isfinite(fps) or fps <= 0:
        raise Stop("The video has no usable frame rate; make its cut again.")
    info = json.loads(face.command("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                                   "-show_entries", "stream=nb_read_frames", "-of", "json", video))
    count = int(info["streams"][0]["nb_read_frames"])
    if count < 1:
        raise Stop("This video has no readable frames; make its cut again.")
    return (width, height), fps, duration, count


def load_anchors(reel):
    path = reel / "work/anchors.json"
    if not path.is_file():
        return [], []
    anchors = read(path)
    cuts = read(reel / "work/cuts.json")
    groups, segments = anchors.get("segments"), cuts.get("segments")
    if not isinstance(groups, list) or not isinstance(segments, list) or not segments:
        raise Stop("The face anchors need their cut segments; measure the face again.")
    seen = set()
    for group in groups:
        seg = group.get("seg")
        if type(seg) is not int or not 0 <= seg < len(segments) or seg in seen or not isinstance(group.get("samples"), list):
            raise Stop("The face anchors have an invalid segment; measure the face again.")
        seen.add(seg)
        start, end = segments[seg]["out_in_f"], segments[seg]["out_out_f"]
        for sample in group["samples"]:
            box = sample.get("box")
            if (type(sample.get("f")) is not int or not start <= sample["f"] < end
                    or not isinstance(box, list) or len(box) != 4
                    or not all(type(v) in (int, float) and math.isfinite(v) for v in box)
                    or box[0] >= box[2] or box[1] >= box[3]):
                raise Stop("A face sample needs a frame and four head-box corners; measure the face again.")
    return groups, segments


def head_at(frame, anchors, segments):
    seg = next((i for i, s in enumerate(segments) if s["out_in_f"] <= frame < s["out_out_f"]), None)
    samples = next((g["samples"] for g in anchors if g["seg"] == seg), [])
    return min(samples, key=lambda p: (abs(p["f"] - frame), p["f"]))["box"] if samples else None


def pool_frames(count, fps, anchors):
    step = max(1, round(fps * .5))
    # All opening frames are needed to choose the sharpest early replacement.
    opening = range(min(count, max(1, math.ceil(fps * .5))))
    return sorted(set(range(0, count, step)) | set(opening)
                  | {p["f"] for g in anchors for p in g["samples"] if 0 <= p["f"] < count})


def decode_frames(video, frames, size, duration):
    """One decode per chunk, bounding the ffmpeg select filter's size."""
    frames = sorted(set(frames))
    pictures = {}
    for start in range(0, len(frames), FRAME_CHUNK_SIZE):
        pictures.update(face.frames(video, frames[start:start + FRAME_CHUNK_SIZE], size, duration))
    return pictures


def score_pool(pictures, size, anchors, segments):
    raw = []
    width, height = size
    for frame, data in sorted(pictures.items()):
        rgb = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
        gray = rgb.astype(float) @ np.array([.299, .587, .114])
        sharp = laplacian_variance(gray)
        box = head_at(frame, anchors, segments)
        eyes = 0.0
        if inside(box):
            x0, y0, x1, y1 = box
            top, bottom = y0 + .25 * (y1 - y0), y0 + .5 * (y1 - y0)
            band = gray[math.floor(top * height):math.ceil(bottom * height),
                        math.floor(x0 * width):math.ceil(x1 * width)]
            eyes = float(np.std(band)) / 127.5 if band.size else 0.0
        raw.append({"frame": frame, "head_box": box, "raw_sharpness": sharp,
                    "parts": {"sharpness": sharp, "eyes": min(1.0, eyes),
                              "head_in_frame": inside(box) if anchors else True}})
    maximum = max((r["raw_sharpness"] for r in raw), default=0)
    for row in raw:
        parts = row["parts"]
        parts["sharpness"] = row["raw_sharpness"] / maximum if maximum else 0.0
        row["score"] = (.6 * parts["sharpness"] + .4 * parts["eyes"]) if anchors else parts["sharpness"]
    return raw


def recommended_frame(rows, fps):
    first = next((r for r in rows if r["frame"] == 0), None)
    if first is None:
        raise Stop("The opening frame could not be read; make the cut again.")
    median = float(np.median([r["raw_sharpness"] for r in rows]))
    if first["raw_sharpness"] < .5 * median:
        early = [r for r in rows if r["frame"] < max(1, math.ceil(fps * .5))]
        return max(early, key=lambda r: (r["raw_sharpness"], -r["frame"]))["frame"]
    return 0


def choose_candidates(rows, fps):
    recommended = recommended_frame(rows, fps)
    picked = [next(r for r in rows if r["frame"] == recommended)]
    for row in sorted(rows, key=lambda r: (not r["parts"]["head_in_frame"], -r["score"], r["frame"])):
        if len(picked) == 6:
            break
        if all(abs(row["frame"] - other["frame"]) / fps >= 1 for other in picked):
            picked.append(row)
    return [{"frame": r["frame"], "t": r["frame"] / fps, "score": r["score"], "parts": r["parts"],
             "head_box": r["head_box"], "recommended": i == 0} for i, r in enumerate(picked)]


def full_frame(video, frame, duration):
    data = face.frames(video, [frame], (W, H), duration).get(frame)
    if data is None:
        raise Stop("The chosen frame does not exist in this video; prepare the covers again.")
    return Image.frombytes("RGB", (W, H), bytes(data))


def candidates(reel, video=None):
    reel = Path(reel).resolve()
    video = video_path(reel, video)
    size, fps, duration, count = video_info(video)
    anchors, segments = load_anchors(reel)
    source = source_words(reel) if (reel / "work/edit_map.cut.json").is_file() else ""
    rows = score_pool(decode_frames(video, pool_frames(count, fps, anchors), size, duration), size, anchors, segments)
    chosen = choose_candidates(rows, fps)
    folder = reel / "cover"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(P / "runtime/fonts/Inter-Regular.woff2", folder / "title-font.woff2")
    for row in chosen:
        full_frame(video, row["frame"], duration).save(folder / f'cand-{row["frame"]}.jpg', quality=98, subsampling=0)
    save(folder / "candidates.json", {"video": str(video), "final": not video.is_relative_to(reel / "work"),
         "fps": fps, "candidates": chosen,
         "words": sorted(set(tokens(source))), "numbers": list(numbers(source)),
         "number_rules": {"small": check_caption.SMALL, "mult": check_caption.MULT, "suffix": check_caption.SUFFIX,
                          "pattern": check_caption.NUM.pattern},
         "title_layout": {"x": TITLE_X, "width": TITLE_W, "top": TITLE_TOP,
                          "default_y": title_default_y(),
                          "bottom": TITLE_BOTTOM, "gap": GAP, "head_fraction": HEAD_BAND_FRACTION,
                          "font_size": TITLE_FONT_SIZE, "line_height": TITLE_LINE_HEIGHT,
                          "sizes": {name: {"font_size": values[0], "line_height": values[1]}
                                    for name, values in TITLE_SIZES.items()},
                          "max_chars": TITLE_MAX_CHARS, "refusal": TITLE_REFUSAL,
                          "padding": TITLE_PADDING, "max_lines": TITLE_MAX_LINES},
         "note": "No face anchors: scored by sharpness only." if not anchors else "Eyes are a weak contrast proxy, not a blink detector."})
    print("Cover candidates are ready." + (" No face anchors: scored by sharpness only." if not anchors else ""))


def render_title(still, title, head, lines=None, size="normal"):
    """Reuse the installed scene-project and offline HyperFrames render path."""
    import compose
    if lines is None:
        placement = title_placement(head, title=title)
        box, lines, size = placement["box"], placement["lines"], placement["size"]
    else:
        box = title_box(head, lines, size)
    with tempfile.TemporaryDirectory(prefix="editor-cover-") as folder:
        root = Path(folder)
        project = root / "scene"
        beat = {"start_f": 0, "end_f": 1, "scene": {"id": "cover-title"}}
        compose.scene_project(project, beat, Fraction(30))
        fill = root / "fill.json"
        save(fill, {"title": title, "kicker": "", "y": round(box[1] * H), "align": "center",
                    "accent": "#4f8cff", "font": "Inter", "size": size})
        mov = root / "title.mov"
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                compose.hf_render(project, mov, rt.hyperframes_env(), "cover title",
                                  ["--format", "mov", "--fps", "30", "--workers", "1",
                                   "--strict-variables", "--variables-file", fill])
        except compose.Stop as error:
            detail = str(error.lines[0]).splitlines()[0] if error.lines else None
            raise Stop("The cover title could not render offline; check the editor tools and try again.", detail) from None
        except Exception:
            raise Stop("The cover title could not render offline; check the editor tools and try again.") from None
        rgba = face.command("ffmpeg", "-v", "error", "-i", mov, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "-")
        overlay = Image.frombytes("RGBA", (W, H), rgba)
        # Pixel proof guards the actual title, including its plate and glyphs.
        bounds = overlay.getchannel("A").getbbox()
        band = head_band(head) if head is not None else None
        if (bounds is None or bounds[0] < TITLE_X or bounds[2] > TITLE_X + TITLE_W
                or bounds[1] < box[1] * H - 1 or bounds[3] > box[3] * H + 1
                or (band is not None and overlaps((bounds[0] / W, bounds[1] / H, bounds[2] / W, bounds[3] / H), band))):
            raise Stop("The title did not fit its clear box; shorten it or choose another frame.")
        return Image.alpha_composite(still.convert("RGBA"), overlay).convert("RGB")


def apply(reel):
    reel = Path(reel).resolve()
    selection = read(reel / "cover-picker-selection.json")
    board = read(reel / "cover/candidates.json")
    if not isinstance(selection, dict) or set(selection) != {"frame", "title", "embed_first_frame"}:
        raise Stop("Send a frame, optional title and first-frame choice from the Cover Picker again.")
    frame = selection["frame"]
    if type(frame) is not int or frame < 0 or type(selection["embed_first_frame"]) is not bool:
        raise Stop("Choose a video frame and a first-frame checkbox value in the Cover Picker again.")
    video = Path(board["video"])
    size, fps, duration, count = video_info(video)
    if frame >= count:
        raise Stop("The chosen frame does not exist in this video; choose another frame.")
    if abs(fps - board["fps"]) > .001:
        raise Stop("The video frame rate changed; prepare the cover candidates again.")
    title = validate_title(selection["title"], source_words(reel) if selection["title"] else "")
    anchors, segments = load_anchors(reel)
    head = head_at(frame, anchors, segments)
    placement = title_placement(head, title=title) if title is not None else None
    row = next((r for r in board["candidates"] if r["frame"] == frame), None)
    if row is None:
        # A valid frame supplied outside the board still gets a real pool score.
        pool = sorted(set(pool_frames(count, fps, anchors)) | {frame})
        scored = score_pool(decode_frames(video, pool, size, duration), size, anchors, segments)
        row = next(r for r in scored if r["frame"] == frame)
    still = full_frame(video, frame, duration)
    if title is not None:
        still = render_title(still, title, head, placement["lines"], placement["size"])
    temp = reel / "cover.tmp.jpg"
    still.save(temp, quality=98, subsampling=0)
    temp.replace(reel / "cover.jpg")
    save(reel / "cover.json", {"frame": frame, "score": row["score"], "title": title,
                              "embed_first_frame": selection["embed_first_frame"]})
    if title is not None and head is None:
        print(NO_FACE_NOTE)
    print(f"Cover saved from frame {frame}; title {'added' if title else 'off'}; first-frame cover {'on' if selection['embed_first_frame'] else 'off'}.")


def selftest():
    from PIL import ImageFilter
    from unittest.mock import patch
    calls = []
    def decode(video, frames, size, duration):
        calls.append(list(frames))
        assert len(frames) <= 40
        return {f: bytes([f]) for f in frames}
    with patch.object(face, "frames", side_effect=decode):
        assert len(decode_frames("fixture.mp4", list(range(156)), (1, 1), 60)) == 156
    assert [len(chunk) for chunk in calls] == [40, 40, 40, 36]
    sharp = np.random.default_rng(6).integers(0, 256, (64, 64), dtype="uint8")
    blurred = np.asarray(Image.fromarray(sharp).filter(ImageFilter.GaussianBlur(4)))
    assert laplacian_variance(blurred) < laplacian_variance(sharp)
    assert validate_title("Clear cuts!", "Clear cuts help two hundred people") == "Clear cuts!"
    for bad in ("unsaidword", "99", "two hundred", "a b c d e f g", "W" * (TITLE_MAX_CHARS + 1)):
        try:
            validate_title(bad, "Clear cuts help two people and hundred more")
        except Stop:
            pass
        else:
            raise AssertionError("unsaid or overlong title passed")
    head = [.1, .2, .9, .65]
    assert not overlaps(title_box(head), head_band(head))
    fixture_head = [0, .176, 1, .84]
    for lines in (1, 2):
        placement = title_placement(fixture_head, lines)
        assert placement["size"] == "normal"
        box = placement["box"]
        assert can_place(fixture_head, lines)
        assert box[1] * H >= math.ceil(head_band(fixture_head)[3] * H) + GAP
        assert not overlaps(box, head_band(fixture_head))
        assert round((box[3] - box[1]) * H) == math.ceil(TITLE_LINE_HEIGHT * lines + 2 * TITLE_PADDING)
        assert box[3] * H <= TITLE_BOTTOM
        for start, end in ((.25, .5), (.5, .6)):  # eyes and mouth within the protected band
            feature = (0, fixture_head[1] + start * (fixture_head[3] - fixture_head[1]),
                       1, fixture_head[1] + end * (fixture_head[3] - fixture_head[1]))
            assert not overlaps(box, feature)
    smaller_head = [0, .116, 1, 1]
    placement = title_placement(smaller_head, 2)
    assert placement["size"] == "smaller" and not overlaps(placement["box"], head_band(smaller_head))
    assert round((placement["box"][3] - placement["box"][1]) * H) == math.ceil(2 * TITLE_SIZES["smaller"][1] + 2 * TITLE_PADDING)
    try:
        title_placement([0, .2, 1, 1], 2)
    except Stop as error:
        assert str(error) == TITLE_REFUSAL and len(str(error).splitlines()) == 1
        assert "Use a shorter title" in str(error) and "pick another cover frame from the picker" in str(error)
    else:
        raise AssertionError("no-room title passed")
    assert not can_place([0, 0, 1, 1])
    assert not can_place([0, 0, 1, 1], 2)
    assert can_place([0, .7, 1, 1])  # above, with touching frame edges allowed
    rows = [{"frame": i, "raw_sharpness": 1 if i == 0 else i + 20} for i in range(60)]
    assert recommended_frame(rows, 30) == 14
    rows[0]["raw_sharpness"] = 100
    assert recommended_frame(rows, 30) == 0
    # Missing per-segment samples never borrow a different segment's head.
    assert head_at(31, [{"seg": 0, "samples": [{"f": 0, "box": head}]}],
                   [{"out_in_f": 0, "out_out_f": 30}, {"out_in_f": 30, "out_out_f": 60}]) is None
    with tempfile.TemporaryDirectory() as folder:
        reel = Path(folder)
        for relative, final in (("work/renders/master-1.mp4", False), ("renders/Reel final - 01.01.26.mp4", True)):
            video = reel / relative
            video.parent.mkdir(parents=True, exist_ok=True)
            video.touch()
            with patch.object(sys.modules[__name__], "video_info", return_value=((4, 4), 30, 1 / 30, 1)), patch.object(
                    face, "frames", side_effect=lambda video, frames, size, duration:
                    {f: bytes(size[0] * size[1] * 3) for f in frames}), contextlib.redirect_stdout(io.StringIO()):
                candidates(reel)
            board = read(reel / "cover/candidates.json")
            assert board["video"] == str(video.resolve())
            assert board.get("final") is final, "candidates must distinguish a cut master from a final video"
    print("cover selftest ok")


def main():
    ensure_utf8_output()
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("--selftest", action="store_true")
        subs = parser.add_subparsers(dest="command", parser_class=Parser)
        pick = subs.add_parser("candidates")
        pick.add_argument("--reel-dir", type=Path, required=True)
        pick.add_argument("--video", type=Path)
        use = subs.add_parser("apply")
        use.add_argument("--reel-dir", type=Path, required=True)
        args = parser.parse_args()
        if args.selftest:
            selftest()
        elif args.command == "candidates":
            candidates(args.reel_dir, args.video)
        elif args.command == "apply":
            apply(args.reel_dir)
        else:
            raise Stop("Choose candidates or apply for an existing reel folder.")
        return 0
    except Stop as error:
        print(" ".join(str(error).split()))
        if error.detail:
            print("detail: " + error.detail)
        return 1
    except Exception:
        print("The cover could not be prepared; check the reel files and editor tools, then try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
