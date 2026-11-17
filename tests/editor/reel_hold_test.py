#!/usr/bin/env python3
"""MB2 hold timing and pixel judgement, without rendering."""
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene_render_test as render
import motion_review as review


class HoldTests(unittest.TestCase):
    def test_one_frame_between_holds_reports_reel_time_and_cut_words(self):
        # Hold frames are 8, 53 and 89; only frame 15 paints in the band.
        width, height = map(int, render.compose.world_area("stack")[2:])
        buf = bytearray(90 * width * height)
        buf[(15 * height + 185) * width + 10] = 1
        beat = {"id": "b_003", "start_f": 190, "end_f": 280}
        decoded = subprocess.CompletedProcess([], 0, stdout=bytes(buf), stderr=b"")
        with (patch.object(render.rt, "tool", return_value="ffmpeg"),
              patch.object(render.subprocess, "run", return_value=decoded) as decode):
            ranges = render.caption_band_ranges(Path("selected.mov"), 90, [185, 335], "stack")
        self.assertEqual(decode.call_count, 1)
        args = decode.call_args.args[0]
        self.assertEqual(args[args.index("-vf") + 1], "alphaextract")
        self.assertEqual(args[args.index("-pix_fmt") + 1], "gray")
        self.assertEqual(ranges, [(15, 16)])
        with tempfile.TemporaryDirectory() as home:
            reel = Path(home)
            (reel / "work").mkdir()
            words = [{"id": "w_0001", "word": "Claude", "out_start": 6.80, "out_end": 6.84,
                      "src_start": 100, "src_end": 101},
                     {"id": "w_0002", "word": "can", "out_start": 6.84, "out_end": 6.90},
                     {"id": "w_0003", "word": "later", "out_start": 7, "out_end": 8}]
            (reel / "work/word_map.json").write_bytes(json.dumps({"words": words}).encode())
            self.assertEqual(review.caption_band_lines(reel, beat, render.compose.Fraction(30), ranges), [
                "Beat b_003: from 6.83 to 6.87 s the graphic crosses the caption band, "
                "under the words 'Claude can'. Move it out of the band."])

    def test_band_words_use_rational_reel_rate_and_half_open_cut_times(self):
        with tempfile.TemporaryDirectory() as home:
            reel = Path(home)
            (reel / "work").mkdir()
            words = [{"id": "w_0001", "word": "done", "out_start": 1, "out_end": 2.002},
                     {"id": "w_0002", "word": "inside", "out_start": 2.002, "out_end": 2.1},
                     {"id": "w_0003", "word": "boundary", "out_start": 2.035366666666667,
                      "out_end": 2.2}]
            (reel / "work/word_map.json").write_bytes(json.dumps({"words": words}).encode())
            beat = {"id": "b_ntsc", "start_f": 30, "end_f": 120}
            self.assertEqual(review.caption_band_lines(reel, beat, render.compose.Fraction(30000, 1001), [(30, 31)]), [
                "Beat b_ntsc: from 2.00 to 2.04 s the graphic crosses the caption band, "
                "under the words 'inside'. Move it out of the band."])
            (reel / "work/word_map.json").unlink()
            self.assertEqual(review.caption_band_lines(reel, beat, render.compose.Fraction(30), []), [])

    def test_all_frame_band_scan_clear_outside_band_and_separate_ranges(self):
        with patch.object(render.compose, "world_area", return_value=(0, 0, 4, 6)):
            for painted, expected in (([], []), ([(1, 1), (2, 4)], []),
                                      ([(0, 2), (1, 3), (3, 2), (5, 3)], [(0, 2), (3, 4), (5, 6)])):
                buf = bytearray(6 * 4 * 6)
                for frame, row in painted:
                    buf[(frame * 6 + row) * 4] = 255
                with self.subTest(painted=painted), patch.object(render, "raw", return_value=bytes(buf)):
                    self.assertEqual(render.caption_band_ranges(Path("selected.mov"), 6, [2, 4]), expected)
            for buf in (b"", bytes(143), bytes(145)):
                with self.subTest(size=len(buf)), patch.object(render, "raw", return_value=buf):
                    with self.assertRaisesRegex(ValueError, "decode.*caption band"):
                        render.caption_band_ranges(Path("selected.mov"), 6, [2, 4])

    def test_seek_pixel_tolerance_boundaries_and_catalog_exactness(self):
        straight = bytes(1000 * 4)
        for delta, count, world, expected in ((4, 50, True, True), (5, 50, True, False),
                                               (4, 51, True, False), (1, 1, False, False),
                                               (0, 0, False, True)):
            jump = bytearray(straight)
            for pixel in range(count):
                jump[pixel * 4 + 2] = delta
            with self.subTest(delta=delta, count=count, world=world):
                ok, maximum, share = render.compare_seek_pixels(straight, jump, world=world)
                self.assertEqual(ok, expected)
                self.assertEqual(maximum, delta)
                self.assertEqual(share, count / 1000)
        for straight, jump in ((b"", b""), (b"1234", b"123"), (b"123", b"123")):
            with self.assertRaises(ValueError):
                render.compare_seek_pixels(straight, jump, world=True)
        self.assertEqual(render.compare_seek_pixels(bytes(4000), bytes([4] * 200 + [0] * 3800), world=True),
                         (True, 4, .05))

    def test_seek_dom_difference_names_first_element_and_property(self):
        straight = [{"element": "div#camera", "style": "transform: translateX(0px)",
                     "transform": "matrix(1, 0, 0, 1, 0, 0)", "opacity": "1",
                     "visibility": "visible", "textContent": "Hello", "svg.d": "M0 0"}]
        self.assertIsNone(render.first_dom_difference(straight, straight))
        for prop in ("element", "style", "transform", "opacity", "visibility", "textContent", "svg.d"):
            jump = [dict(straight[0], **{prop: "changed"})]
            with self.subTest(prop=prop):
                difference = render.first_dom_difference(straight, jump)
                self.assertIn("div#camera", difference)
                self.assertIn(prop, difference)
        self.assertIn("svg.d", render.first_dom_difference(straight, [dict(straight[0], **{"svg.d": None})]))
        self.assertIn("element count", render.first_dom_difference(straight, []))

    def test_seek_dom_failure_is_not_relaxed_with_world_pixels(self):
        straight = [{"element": "span#slot", "style": "left: 0px"}]
        jump = [{"element": "span#slot", "style": "left: 1px"}]

        def fake_render(proj, fill, out, env, **kwargs):
            kwargs["seen"].append("screenshot capture")
            return True, ""

        def fake_raw(video, vf, pix, frame):
            if vf == "alphaextract":
                return b"\xff"
            # Identical decoded pixels do not excuse a different DOM state.
            return bytes(20 * 10 * 4)

        with tempfile.TemporaryDirectory() as home:
            tmp = Path(home)
            output = io.StringIO()
            with (patch.object(render.ost, "run", return_value=(0, json.dumps({"straight": straight, "jump": jump}), "")),
                  patch.object(render.rt, "tool", return_value="unused"),
                  patch.object(render, "render", side_effect=fake_render),
                  patch.object(render, "probe", return_value={"width": 20, "height": 10, "pix_fmt": "rgba"}),
                  patch.object(render, "raw", side_effect=fake_raw), patch.object(render, "fails", []) as failures,
                  contextlib.redirect_stdout(output)):
                render.seek_checks("reel-test", 90, {}, tmp, tmp, {}, world=True)
                self.assertEqual(len(failures), 1)
                self.assertIn("span#slot property style", failures[0])
            self.assertIn("FAIL reel-test: frame 45 DOM state after a jump differs", output.getvalue())
            self.assertIn("matches the straight render within tolerance: max difference 0", output.getvalue())

    def test_catalog_seek_keeps_native_bytes_exact_and_failure_wording(self):
        def fake_render(proj, fill, out, env, **kwargs):
            kwargs["seen"].append("screenshot capture")
            return True, ""

        def fake_raw(video, vf, pix, frame):
            if vf == "alphaextract":
                return b"\xff"
            if vf == "null":
                return b"straight" if "sequential" in video.name else b"jump"
            return bytes(800)

        with tempfile.TemporaryDirectory() as home:
            tmp = Path(home)
            output = io.StringIO()
            with (patch.object(render, "seek_dom_check"), patch.object(render, "render", side_effect=fake_render),
                  patch.object(render, "probe", return_value={"width": 20, "height": 10}),
                  patch.object(render, "raw", side_effect=fake_raw), patch.object(render, "fails", []) as failures,
                  contextlib.redirect_stdout(output)):
                render.seek_checks("hf-test", 90, {}, tmp, tmp, {})
                self.assertEqual(len(failures), 1)
            self.assertIn("FAIL hf-test: frame 45 after a jump differs from the straight render", output.getvalue())
            self.assertIn("native frame bytes differ", output.getvalue())
            self.assertNotIn("matches the straight render", output.getvalue())

    def test_hold_frames_defaults_overrides_clamp_and_last(self):
        spec = {"holds": [0, "t1", 100], "params": {"t1": {"default": 1}}}
        self.assertEqual(render.hold_frames(spec, {}, 90, 30), [8, 38, 89])
        self.assertEqual(render.hold_frames(spec, {"t1": 2}, 90, 30), [8, 68, 89])
        self.assertEqual(render.hold_frames(spec, {}, 1, 30), [0])
        for value in (-1, True, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render.hold_frames(spec, {"t1": value}, 90, 30)

    def test_hold_judgement(self):
        clean = [(100, 300, 500, 400)]
        band = [1320, 1470]
        self.assertEqual(render.hold_problems(clean, clean, band), [])
        self.assertEqual(render.hold_problems(clean, clean + [(100, 1340, 500, 1390)], band), ["caption band"])
        self.assertIn("frame edge", render.hold_problems([(0, 300, 100, 400)], clean, band))
        self.assertEqual(render.hold_problems([(59, 300, 100, 400)], clean, band), ["safe box"])
        for box in ((100, 300, 1080, 400), (100, 0, 500, 400), (100, 300, 500, 1920)):
            self.assertIn("frame edge", render.hold_problems([box], clean, band))
        self.assertEqual(render.hold_problems([(60, 220, 960, 1320)], [(60, 220, 960, 1320)], band), [])
        self.assertEqual(render.hold_problems(clean, [(100, 1470, 500, 1500)], band), [])
        self.assertIn("no slot text", render.hold_problems([], clean, band))

    def test_decode_samples_only_requested_hold_and_preserves_empty_rows(self):
        buf = bytearray(render.W * render.H)
        buf[300 * render.W + 100] = 255
        buf[1500 * render.W + 200] = 255
        with patch.object(render, "raw", return_value=bytes(buf)) as raw:
            boxes = render.hold_pixel_boxes(Path("fixture.mov"), 52)
        raw.assert_called_once_with(Path("fixture.mov"), "alphaextract", "gray", 52)
        self.assertEqual(boxes, [(100, 300, 101, 301), (200, 1500, 201, 1501)])
        self.assertNotIn("caption band", render.hold_problems(boxes[:1], boxes, [1320, 1470]))
        with patch.object(render, "raw", return_value=b""), self.assertRaises(ValueError):
            render.hold_pixel_boxes(Path("fixture.mov"), 52)

    def test_fixture_static_contract_and_reel_seek_in_all(self):
        motion = Path(__file__).resolve().parent / "fixtures/reel-motion/motion"
        for sid in ("reel-good-world", "reel-band-world", "reel-seek-world"):
            with self.subTest(sid=sid):
                self.assertEqual(render.compose.scene_check.scene_problems(motion / sid), [])
                with tempfile.TemporaryDirectory() as home:
                    tmp = Path(home)
                    with (patch.object(render, "project", return_value=tmp) as project,
                          patch.object(render, "base_checks") as base,
                          patch.object(render, "brand_checks"), patch.object(render, "seek_checks") as seek,
                          contextlib.redirect_stdout(io.StringIO())):
                        render.scene_test(sid, tmp, {}, tmp / "net.jsonl", False, "all", scenes_dir=motion)
                        self.assertEqual(project.call_args.args[3], motion / sid)
                        self.assertEqual(base.call_args.args[1], motion / sid)
                        seek.assert_called_once()
                        self.assertTrue(seek.call_args.kwargs["world"])
        for sid, expected in (("callout", False), ("hf-callout", True)):
            with (tempfile.TemporaryDirectory() as home, patch.object(render, "project"),
                  patch.object(render, "base_checks"), patch.object(render, "brand_checks"),
                  patch.object(render, "seek_checks") as seek, contextlib.redirect_stdout(io.StringIO())):
                render.scene_test(sid, Path(home), {}, Path(home) / "net.jsonl", False, "all")
                self.assertEqual(seek.called, expected)
                if expected:
                    self.assertFalse(seek.call_args.kwargs["world"])

    def test_render_projects_reuse_verified_reel_assets(self):
        with tempfile.TemporaryDirectory() as home:
            tmp = Path(home)
            motion = tmp / "motion"
            folder = motion / "reel-asset-world"
            folder.mkdir(parents=True)
            (motion / "assets").mkdir()
            asset = motion / "assets/row.svg"
            asset.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')
            (motion / "assets.json").write_bytes(json.dumps({"files": [{"path": "row.svg",
                "source": "Own text fixture", "sha256": hashlib.sha256(asset.read_bytes()).hexdigest()}]}).encode())
            html = '<img src="./assets/row.svg">'
            (folder / "scene.html").write_bytes(html.encode())
            project = render.project(tmp, "project", html, folder)
            self.assertEqual((project / "assets/row.svg").read_bytes(), asset.read_bytes())
            asset.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "sha256"):
                render.project(tmp, "invalid-project", html, folder)


if __name__ == "__main__":
    unittest.main(verbosity=2)
