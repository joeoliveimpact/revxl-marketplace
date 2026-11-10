"""Pure face-crop checks: python -I tests/editor/face_crop_test.py [--case NAME]."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import isolated_home

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "plugins/editor-superengine/skills"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def face():
    path = SKILLS / "reel-canvas-build/scripts/face_crop.py"
    assert path.is_file(), "the face-crop implementation is missing"
    return module("face_crop_tested", path)


def render():
    return module("face_render_tested", SKILLS / "reel-first-cuts/scripts/render.py")


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc) + "\n").encode("utf-8"))


CUTS = {"fps": 25, "speed": 1.0, "segments": [
    {"src_in_f": 100, "src_out_f": 140, "out_in_f": 0, "out_out_f": 40},
    {"src_in_f": 200, "src_out_f": 208, "out_in_f": 40, "out_out_f": 48}]}


def band():
    m = face()
    w, h = 240, 300
    for cx in (65, 175):
        alpha = bytearray(w * h)
        for y in range(h):
            for x in range(w):
                if (x - cx) ** 2 + (y - 65) ** 2 <= 25 ** 2 or (90 <= y < 275 and abs(x - cx) <= 60):
                    alpha[y * w + x] = 255
        x, y = m.head_band(alpha, w, h)
        assert abs(x - cx / w) < .02 and abs(y - 65 / h) < .02, (x, y)
        specked = bytearray(alpha)
        for sy in range(5, 25):
            specked[sy * w + 4:sy * w + 47] = bytes([255]) * 43
        specked[25 * w + 4:25 * w + 10] = bytes([255]) * 6
        x, y = m.head_band(specked, w, h)  # 866 stray pixels above and left of the head
        assert abs(x - cx / w) < .02 and abs(y - 65 / h) < .02, (x, y)
    assert m.head_band(bytes(w * h), w, h) is None
    assert m.head_band(bytes([255]) * 359 + bytes(w * h - 359), w, h) is None
    diagonal = bytearray(100 * 100)
    for offset in (0, 7):
        for y in range(offset, offset + 7):
            diagonal[y * 100 + offset:y * 100 + offset + 7] = bytes([255]) * 7
    # Diagonal contact does not join two 49-pixel components into a valid matte.
    assert m.head_band(diagonal, 100, 100) is None


def ghost():
    m = face()
    w, h, cx, cy = 240, 300, 175, 65
    shape = bytes(255 if (x - cx) ** 2 + (y - cy) ** 2 <= 25 ** 2
                  or (90 <= y < 275 and abs(x - cx) <= 60) else 0 for y in range(h) for x in range(w))
    for opacity in (120, 160, 199):
        alpha = bytes(opacity if a else 0 for a in shape)
        assert m.head_band(alpha, w, h) is None, f"a {opacity}-alpha ghost survived"
    for opacity in (200, 255):
        x, y = m.head_band(bytes(opacity if a else 0 for a in shape), w, h)
        assert abs(x - cx / w) < .02 and abs(y - cy / h) < .02, (x, y)
    # An opaque body must not hide a translucent head-band's mean alpha.
    assert m.head_band(bytes(160 if a and i // w < 90 else a for i, a in enumerate(shape)), w, h) is None


def settle():
    m = face()
    assert m.K == 6 and m.settled_frames(3) == [5, 11, 17]
    with tempfile.TemporaryDirectory() as root:
        work = Path(root)
        selected = []
        read_frames = []
        cutouts = []
        expected = {10: (.5, .3), 20: (.5, .3), 30: (.5, .3)}

        def tool(tool, args, purpose):
            graph = Path(args[args.index("-/filter_complex") + 1]).read_text(encoding="utf-8")
            source_frames = [int(f) for f in re.findall(r"eq\(n,(\d+)\)", graph)]
            assert source_frames == [10, 20, 30]
            copies = int(re.search(r"split=(\d+)", graph)[1])
            assert copies == 6 and f"interleave=nb_inputs={copies}:duration=longest" in graph
            # Each split receives the same timestamped frames; interleave emits
            # every copy at that timestamp before the next source sample.
            selected.extend(f for f in source_frames for _ in range(copies))
            assert args[args.index("-map") + 1] == "[samples]"
            return b""

        def cutout(cmd, **kwargs):
            cutouts.append(cmd)
            assert Path(cmd[4]).name == "cutout.py"
            return subprocess.CompletedProcess(cmd, 0, b'{"engine":"rvm","frames":18}\n', b"")

        class Decoder:
            def __init__(self, cmd, **kwargs):
                graph = Path(cmd[cmd.index("-/filter:v") + 1]).read_text(encoding="utf-8")
                read_frames.extend(int(f) for f in re.findall(r"eq\(n,(\d+)\)", graph))
                assert read_frames == [5, 11, 17] and graph.endswith(",alphaextract")
                assert cmd[cmd.index("-fps_mode") + 1] == "passthrough"
                self.stdout = io.BytesIO(bytes([255]) * 3)

            def wait(self):
                return 0

            def poll(self):
                return 0

        with patch.object(m, "run_tool", side_effect=tool), patch.object(m.subprocess, "run", side_effect=cutout), \
                patch.object(m, "probe_video", return_value={"width": 1, "height": 1}), \
                patch.object(m.subprocess, "Popen", Decoder), patch.object(m, "head_band", return_value=(.5, .3)), \
                patch.object(m.rt, "tool", return_value="ffmpeg"):
            points, engine = m.measure(work, work / "source.mp4", [30, 10, 20, 10], "25", "auto")
        assert selected == [10] * 6 + [20] * 6 + [30] * 6 and len(selected) == 18
        assert points == expected and engine == "rvm" and len(cutouts) == 1
        assert not (work / "render-tmp/face").exists()


def outliers():
    m = face()
    pts = {10: (.48, .35), 20: (.49, .34), 30: (.50, .35), 40: (.51, .36), 50: (.52, .35),
           60: (.64, .22), 70: (.85, .1), 80: None}
    refs = [(0, f) for f in pts]
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        kept = m.reject_outliers(refs, pts)
    assert kept == (pts | {60: None, 70: None})
    assert pts[60] == (.64, .22) and pts[70] == (.85, .1), "input samples were mutated"
    lines = log.getvalue().splitlines()
    assert len(lines) == 2 and all(line.startswith("note:") for line in lines)
    assert "frame 60" in lines[0] and "frame 70" in lines[1], lines
    assert m.reject_outliers([(0, 1)], {1: None}) == {1: None}
    assert m.reject_outliers([(0, 1)], {1: (.5, .35)}) == {1: (.5, .35)}

    with tempfile.TemporaryDirectory() as root:
        reel, work = Path(root), Path(root) / "work"
        cuts = {"fps": 25, "speed": 1, "segments": [
            {"src_in_f": 0, "src_out_f": 40, "out_in_f": 0, "out_out_f": 40},
            {"src_in_f": 40, "src_out_f": 80, "out_in_f": 40, "out_out_f": 80},
            {"src_in_f": 80, "src_out_f": 120, "out_in_f": 80, "out_out_f": 120}]}
        write(work / "cuts.json", cuts)
        source = reel / "take.mp4"
        source.touch()
        (work / "renders").mkdir()
        (work / "renders/master-test.mp4").touch()
        measured = {10: (.48, .35), 20: (.49, .34), 30: (.5, .35), 50: (.51, .36), 60: (.52, .35),
                    70: None, 90: (.64, .22), 100: (.85, .1), 110: None}
        measured = {f: None if p is None else m.HeadBand(p, (p[0] - .05, p[1] - .05, p[0] + .05, p[1] + .05))
                    for f, p in measured.items()}
        with patch.object(m, "probe_video", return_value={"width": 3840, "height": 2160}), \
                patch.object(m, "measure", return_value=(measured, "rvm")):
            for argv in (["crop", "--work", str(work), "--take", str(source)],
                         ["anchors", "--reel-dir", str(reel)]):
                log = io.StringIO()
                with contextlib.redirect_stdout(log):
                    assert m.main(argv) == 0
                notes = [line for line in log.getvalue().splitlines() if line.startswith("note:")]
                assert len(notes) == 2 and "frame 90" in notes[0] and "frame 100" in notes[1], notes
        crop = json.loads((work / "crop.json").read_bytes())
        assert crop["face_x"] == .5 and crop["samples"] == 5 and crop["x"] == 1168, crop
        anchors = json.loads((work / "anchors.json").read_bytes())
        assert [s["seg"] for s in anchors["segments"]] == [0, 1]
        assert [p["f"] for s in anchors["segments"] for p in s["samples"]] == [10, 20, 30, 50, 60]
        # Four opposed corners leave no sample within 0.15 of the median.
        extremes = {f: None for f in measured} | {10: (0., 0.), 20: (1., 1.), 30: (0., 0.), 50: (1., 1.)}
        with patch.object(m, "probe_video", return_value={"width": 3840, "height": 2160}), \
                patch.object(m, "measure", return_value=(extremes, "rvm")), contextlib.redirect_stdout(io.StringIO()):
            assert m.guarded(lambda: m.main(["crop", "--work", str(work), "--take", str(source)])) == 1
            assert not (work / "crop.json").exists()
            assert m.main(["anchors", "--reel-dir", str(reel)]) == 0
            assert json.loads((work / "anchors.json").read_bytes())["segments"] == []


def conform_none():
    m = render()
    base = ("scale=1080:1920:force_original_aspect_ratio=increase:force_divisible_by=2:flags=lanczos,"
            "crop=1080:1920,setsar=1")
    for v in ({"width": 3840, "height": 2160}, {"width": 1920, "height": 1080, "rotation": 90},
              {"width": 1080, "height": 1920}):
        assert m.conform(v) == base
        assert m.conform(v, None) == base
        for tr, peak in (("arib-std-b67", ":peak=1"), ("smpte2084", "")):
            assert m.conform(dict(v, color_transfer=tr)) == (base + ",zscale=t=linear:npl=100,format=gbrpf32le,"
                "zscale=p=bt709,tonemap=tonemap=mobius:desat=0" + peak + ",zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def conform_crop():
    m = render()
    v = {"width": 3840, "height": 2160}
    assert "crop=1080:1920:600:0" in m.conform(v, {"x": 600, "scaled_w": 3414})
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        got = m.conform(v, {"x": 600, "scaled_w": 3400})
    assert got == m.conform(v)
    assert len(log.getvalue().splitlines()) == 1 and log.getvalue().startswith("note:")
    assert "crop=1080:1920:0:0" in m.conform({"width": 1920, "height": 1080, "rotation": -90},
                                          {"x": 0, "scaled_w": 1080})


def crop_maths():
    m = face()
    for video, want in (({"width": 3840, "height": 2160}, 3414),
                        ({"width": 1920, "height": 1080, "rotation": 90}, 1080),
                        ({"width": 1080, "height": 1920}, 1080),
                        ({"width": 720, "height": 1600}, 1080),
                        ({"width": 1919, "height": 1080}, 3412)):
        assert m.cover_scaled_width(video) == want
    for fx, width, want in ((0, 3414, 0), (1, 3414, 2334), (.5, 1080, 0), (.5, 3414, 1168)):
        assert m.crop_x(fx, width) == want
    for i in range(1001):
        x = m.crop_x(i / 1000, 3414)
        assert x % 2 == 0 and 0 <= x <= 2334


def samples():
    m = face()
    assert m.sample_frames(CUTS, "src") == [(0, 110), (0, 120), (0, 130), (1, 202), (1, 204), (1, 206)]
    assert m.sample_frames(CUTS, "out") == [(0, 10), (0, 20), (0, 30), (1, 42), (1, 44), (1, 46)]
    short = {"segments": [{"src_in_f": 9, "src_out_f": 10}]}
    assert m.sample_frames(short, "src") == [(0, 9)] * 3


def anchors_shape():
    m = face()
    styles = module("face_styles_tested", SKILLS / "reel-canvas-build/scripts/styles.py")
    doc = m.anchors_result(CUTS, [(0, 10), (0, 20), (0, 30), (1, 42)],
                           {10: m.HeadBand((.27, .31), (.2, .2, .4, .4)), 20: None,
                            30: m.HeadBand((.29, .33), (.2, .2, .4, .4)), 42: None})
    assert doc == {"schema": 1, "fps": 25, "segments": [{"seg": 0, "samples": [
        {"f": 10, "x": .27, "y": .31, "box": [.2, .2, .4, .4]},
        {"f": 30, "x": .29, "y": .33, "box": [.2, .2, .4, .4]}]}]}
    with tempfile.TemporaryDirectory() as root:
        reel = styles.make_reel(root, {"style": "punch-in"})
        write(reel / "work/anchors.json", doc)
        assert styles.load_anchors(reel, styles.SEGS) == {0: [(10, .27, .31), (30, .29, .33)]}
        track = styles.plan(reel, tuning=Path(root) / "absent.json", fps="25")  # no master in this fixture
        assert (track["keys"][0]["ox"], track["keys"][0]["oy"]) == (.27, .31)
        assert (track["keys"][1]["ox"], track["keys"][1]["oy"]) == styles.ORIGIN


def anchors_box():
    """Written boxes follow the retained head band; styles still reads its centres."""
    m = face()
    styles = module("face_box_styles_tested", SKILLS / "reel-canvas-build/scripts/styles.py")
    w, h = 200, 160

    def silhouette(cx, opacity=255):
        return bytearray(opacity if (x - cx) ** 2 + (y - 42) ** 2 <= 32 ** 2
                         or (74 <= y < 92 and abs(x - cx) <= 10)
                         or (60 <= y and 35 <= abs(x - cx) <= 45)
                         or (92 <= y and abs(x - cx) <= 45) else 0
                         for y in range(h) for x in range(w))

    specked = silhouette(100)
    specked[2 * w:2 * w + 8] = bytes([255]) * 8
    planes = [silhouette(100), silhouette(100, 199), specked,
              silhouette(100), silhouette(170), bytes(w * h)]
    points = {f: m.head_band(alpha, w, h) for (_, f), alpha in zip(m.sample_frames(CUTS, "out"), planes)}
    with tempfile.TemporaryDirectory() as root:
        reel, work = Path(root), Path(root) / "work"
        write(work / "cuts.json", CUTS)
        (work / "renders").mkdir()
        (work / "renders/master-test.mp4").touch()
        log = io.StringIO()
        with patch.object(m, "measure", return_value=(points, "rvm")), contextlib.redirect_stdout(log):
            assert m.main(["anchors", "--reel-dir", str(reel)]) == 0
        raw = (work / "anchors.json").read_bytes()
        doc = json.loads(raw)
        written = [p for seg in doc["segments"] for p in seg["samples"]]
        summary = [line for line in log.getvalue().splitlines() if not line.startswith("note:")]
        assert summary == [f"Face anchors saved: 3 frames -> {work / 'anchors.json'}"], log.getvalue()
        assert [p["f"] for p in written] == [10, 30, 42], written
        for p in written:
            assert "box" in p, "a retained sample has no head box"
            assert isinstance(p["box"], list) and len(p["box"]) == 4, p
            x0, y0, x1, y1 = p["box"]
            assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, p
            assert x0 <= p["x"] <= x1 and y0 <= p["y"] <= y1, p
            assert y1 >= p["y"], "the head box ends above the band's centroid"
            assert y1 >= 74 / h, "the head box misses the planted chin"
            assert y1 >= 92 / h, "the head box misses the planted neck"
            assert p["box"] == [55 / w, 10 / h, 146 / w, 123 / h], p
        assert b"\r" not in raw
        assert styles.load_anchors(reel, [(0, 40), (40, 48)]) == {
            0: [(p["f"], p["x"], p["y"]) for p in written[:2]],
            1: [(42, written[2]["x"], written[2]["y"])]}


def render_crop():
    m = render()
    with tempfile.TemporaryDirectory() as root:
        work = Path(root)
        write(work / "cuts.json", CUTS)
        write(work / "probe.json", {"video": {"width": 3840, "height": 2160}})
        write(work / "crop.json", {"x": 600, "scaled_w": 3414})
        with patch.object(sys, "argv", ["render.py", str(work), "take.mp4", "--master"]), \
                patch.object(m, "find_tools"), patch.object(m, "sample_rate", return_value=48000), \
                patch.object(m, "encode"), patch.object(m, "count_frames", return_value=48), \
                patch.object(m, "probe_out", return_value={"format": {"duration": 1.92}, "streams": [{}]}), \
                patch.object(m.review_page, "write", return_value="review.html"), \
                contextlib.redirect_stdout(io.StringIO()):
            m.main()
            graph = next(work.glob("_graph-master-*.txt")).read_text(encoding="utf-8")
            assert "crop=1080:1920:600:0" in graph
            (work / "crop.json").unlink()
            # The existing cut-safety harness swaps in a one-argument conform.
            with patch.object(m, "conform", lambda video: "scale=360:640"):
                m.main()
            assert "scale=360:640" in next(work.glob("_graph-master-*.txt")).read_text(encoding="utf-8")


def pipeline():
    """CLI artifacts, engine reporting, newest master, and scratch cleanup without media tools."""
    m = face()
    with tempfile.TemporaryDirectory() as root:
        reel, work = Path(root), Path(root) / "work"
        write(work / "cuts.json", CUTS)
        source = reel / "off-centre.mp4"
        source.touch()
        probe = {"width": 3840, "height": 2160}
        pts = {110: (.3, .2), 120: None, 130: (.4, .2), 202: (.8, .3), 204: (.6, .2), 206: (.5, .3)}
        log = io.StringIO()
        with patch.object(m, "probe_video", return_value=probe), \
                patch.object(m, "measure", return_value=(pts, "remove-background")), contextlib.redirect_stdout(log):
            assert m.guarded(lambda: m.main(["crop", "--work", str(work), "--take", str(source)])) == 0
        doc = json.loads((work / "crop.json").read_bytes())
        assert doc == {"schema": 1, "x": 1168, "scaled_w": 3414, "face_x": .5, "samples": 3,
                       "engine": "remove-background", "measured_on": "off-centre.mp4"}
        assert json.loads(log.getvalue().splitlines()[-1]) == doc
        assert b"\r" not in (work / "crop.json").read_bytes()
        with patch.object(m, "probe_video", return_value=probe), \
                patch.object(m, "measure", return_value=({f: None for f in pts}, "rvm")), \
                contextlib.redirect_stdout(io.StringIO()):
            assert m.guarded(lambda: m.main(["crop", "--work", str(work), "--take", str(source)])) == 1
        assert not (work / "crop.json").exists()

        (work / "renders").mkdir()
        old, newest = work / "renders/master-z.mp4", work / "renders/master-a.mp4"
        old.touch()
        newest.touch()
        os.utime(old, (100, 100))
        os.utime(newest, (200, 200))

        def measured(_work, selected, frames, rate, engine):
            assert selected == newest
            return {f: m.HeadBand((.25, .35), (.2, .3, .3, .4)) if f < 40 else None for f in frames}, "rvm"

        with patch.object(m, "measure", side_effect=measured), contextlib.redirect_stdout(io.StringIO()):
            assert m.main(["anchors", "--reel-dir", str(reel)]) == 0
        doc = json.loads((work / "anchors.json").read_bytes())
        assert doc["fps"] == 25 and len(doc["segments"]) == 1
        assert [s["f"] for s in doc["segments"][0]["samples"]] == [10, 20, 30]

        def tool(tool, args, purpose):
            if tool == "ffmpeg":
                # A deliberately reordered/repeated request must map selected frames back correctly.
                graph = (work / "render-tmp/face/0/select.txt").read_text(encoding="utf-8")  # one folder per batch (FX2)
                assert "eq(n,10)+eq(n,20)+eq(n,30)" in graph
            return b""

        ok = subprocess.CompletedProcess([], 0, b'{"engine":"rvm","frames":18}\n', b"")
        with patch.object(m, "run_tool", side_effect=tool), patch.object(m.subprocess, "run", return_value=ok), \
                patch.object(m, "probe_video", return_value={"width": 540, "height": 304}), \
                patch.object(m, "read_alpha", return_value={10: (.1, .2), 20: None, 30: (.3, .2)}):
            points, used = m.measure(work, source, [30, 10, 20, 10], "25", "auto")
        assert used == "rvm" and points[10] == (.1, .2) and points[20] is None
        assert not (work / "render-tmp/face").exists()
        with patch.object(m, "run_tool", side_effect=m.Stop(1, "Extraction stopped.")):
            try:
                m.measure(work, source, [10], "25", "auto")
                raise AssertionError("failed extraction was accepted")
            except m.Stop as e:
                assert e.code == 1
        assert not (work / "render-tmp/face").exists()
        with contextlib.redirect_stdout(io.StringIO()):
            assert m.guarded(lambda: m.main(["crop", "--work", str(reel / "missing"),
                                           "--take", str(source)])) == 2


CASES = {"band": band, "conform-none": conform_none, "conform-crop": conform_crop, "crop-maths": crop_maths,
         "samples": samples, "anchors-shape": anchors_shape, "render-crop": render_crop, "pipeline": pipeline,
         "outliers": outliers, "settle": settle, "ghost": ghost, "anchors-box": anchors_box}


@isolated_home()
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=list(CASES))
    a = ap.parse_args()
    failed = 0
    for name in [a.case] if a.case else CASES:
        try:
            CASES[name]()
            print(f"PASS {name}")
        except Exception as e:
            print(f"FAIL {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"{failed} failed" if failed else "all passed")
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
