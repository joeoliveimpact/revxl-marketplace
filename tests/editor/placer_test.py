#!/usr/bin/env python3
"""Synthetic S7.2 caption-placement checks; no video, tools or third-party modules.

Run: python -X utf8 -I tests/editor/placer_test.py
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins/editor-superengine/skills/reel-canvas-build/scripts"
sys.path.insert(0, str(SCRIPTS))
import placer  # noqa: E402


def key(f=0, scale=1.0, ox=0.5, oy=0.38, layout="full"):
    return dict(f=f, scale=scale, ox=ox, oy=oy, layout=layout)


def sample(box=None, f=0, x=0.5, y=0.38):
    point = dict(f=f, x=x, y=y)
    if box is not None:
        point["box"] = [v / d for v, d in zip(box, (1080, 1920, 1080, 1920))]
    return point


def beat(start=0, end=50, layout="full", scene=None):
    return dict(id=f"beat-{start}", start_f=start, end_f=end, layout=layout,
                scene=scene, speech_anchor={"text": "A short hook"})


class PlacerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.serial = 0

    def ctx(self, keys=None, tweens=None, anchors=None, segments=None, beats=None, style="punch-in"):
        self.serial += 1
        reel = self.root / str(self.serial)
        (reel / "work").mkdir(parents=True)
        segments = segments or [(0, 50)]
        docs = {
            "work/scale_track.json": dict(schema=1, fps="25/1", total_f=segments[-1][1],
                                          style={"style": style}, keys=keys or [key()], tweens=tweens or []),
            "work/cuts.json": dict(fps=25, speed=1.0, segments=[
                dict(out_in_f=a, out_out_f=e) for a, e in segments]),
            "beat-map-selection.json": dict(fps=25, beats=beats or [beat(end=segments[-1][1])]),
        }
        if anchors is not None:
            docs["work/anchors.json"] = {"segments": [dict(seg=i, samples=points)
                                                     for i, points in anchors.items()]}
        for name, doc in docs.items():
            (reel / name).write_bytes((json.dumps(doc) + "\n").encode("utf-8"))
        return placer.load_ctx(reel)

    def safe(self, box, height=134):
        self.assertEqual(box[0], 60)
        self.assertEqual(box[2], 960)
        self.assertGreaterEqual(box[1], 220)
        self.assertLessEqual(box[3], 1470)
        self.assertEqual(box[3] - box[1], height)

    def clear(self, box, head):
        self.assertTrue(head is None or not placer.hits(box, head, placer.CAPTION_PAD))

    def same_box(self, actual, expected):
        self.assertIsNotNone(actual)
        for value, want in zip(actual, expected):
            self.assertAlmostEqual(value, want)

    def test_a_az2_punch_112_moves_naive_band(self):
        anchors = {0: [sample((400, 1050, 680, 1290))]}
        plain = self.ctx(anchors=anchors)
        punched = self.ctx(keys=[key(scale=1.12)], anchors=anchors)
        naive = placer.place(plain, 0, 49)
        self.assertEqual(naive, (60, 1336, 960, 1470))
        self.clear(naive, placer.head_box_at(plain, 0, 49))
        zoomed_head = placer.head_box_at(punched, 0, 49)
        self.assertTrue(placer.hits(naive, zoomed_head, placer.CAPTION_PAD))
        placed = placer.place(punched, 0, 49)
        self.assertNotEqual(placed, naive)
        self.clear(placed, zoomed_head)
        self.safe(placed)

    def test_b_peak_143_is_never_clamped(self):
        ctx = self.ctx(keys=[key(scale=1.43)], anchors={0: [sample((400, 1050, 680, 1290))]})
        original = copy.deepcopy(ctx["track"])
        head = placer.head_box_at(ctx, 0, 49)
        self.assertAlmostEqual(head[3], (1290 + placer.HEAD_PAD - 729.6) * 1.43 + 729.6)
        box = placer.place(ctx, 0, 49)
        self.clear(box, head)
        self.safe(box)
        self.assertEqual(ctx["notes"], [])
        self.assertEqual(ctx.get("fallbacks", []), [])
        self.assertEqual(ctx["track"], original)

    def test_b_no_clear_spot_returns_least_overlap_and_timed_note(self):
        for measured, expected, area in (
                ((400, 260, 680, 1500), (60, 220, 960, 354), 38704),
                ((400, 0, 680, 1390), (60, 1336, 960, 1470), 25584)):
            with self.subTest(head=measured):
                ctx = self.ctx(anchors={0: [sample(measured)]})
                head = placer.head_box_at(ctx, 0, 49)
                box = placer.place(ctx, 0, 49)
                self.assertEqual(box, expected)
                self.safe(box)
                for candidate in ((60, 1336, 960, 1470), (60, 220, 960, 354)):
                    overlap = (max(0, min(candidate[2], head[2]) - max(candidate[0], head[0]))
                               * max(0, min(candidate[3], head[3]) - max(candidate[1], head[1])))
                    self.assertLessEqual(area, overlap)
                self.assertEqual(len(ctx["notes"]), 1)
                self.assertIn("0.00 to 1.96 seconds", ctx["notes"][0])
                self.assertIn("overlap part of the speaker's head", ctx["notes"][0])
                self.assertIn("may shorten or drop", ctx["notes"][0])
                self.assertEqual(ctx["fallbacks"], [dict(start_f=0, end_f=49, box=box, overlap_px=area)])
                self.assertEqual(placer.place(ctx, 0, 49), box)
                self.assertEqual(len(ctx["notes"]), 1)
                self.assertEqual(len(ctx["fallbacks"]), 1)

    def test_b_equal_overlap_picks_lower_spot(self):
        ctx = self.ctx(keys=[key(scale=1.43)], anchors={0: [sample((0, 0, 1080, 1920))]})
        box = placer.place(ctx, 0, 49)
        self.assertEqual(box, (60, 1336, 960, 1470))
        self.safe(box)
        self.assertEqual(ctx["fallbacks"][0]["overlap_px"], 900 * 134)

    def test_b_fallback_uses_head_envelope_over_entire_span(self):
        ctx = self.ctx(segments=[(0, 25), (25, 50)], keys=[key(), key(25)], anchors={
            0: [sample((400, 260, 680, 1500))],
            1: [sample((400, 0, 680, 1390), f=25)]})
        self.assertEqual(placer.place(ctx, 0, 24), (60, 220, 960, 354))
        box = placer.place(ctx, 0, 49)
        self.assertEqual(box, (60, 1336, 960, 1470))
        self.assertEqual(ctx["fallbacks"][-1], dict(start_f=0, end_f=49, box=box, overlap_px=43952))

    def test_b_impossible_band_height_still_raises_no_room(self):
        ctx = self.ctx(anchors={0: [sample((0, 0, 1080, 1920))]})
        with self.assertRaises(placer.NoRoom) as caught:
            placer.place(ctx, 0, 49, 1251)
        self.assertEqual(len(caught.exception.lines), 1)
        self.assertIn("0.00 to 1.96 seconds", caught.exception.lines[0])
        self.assertIn("safe text area", caught.exception.lines[0])
        self.assertEqual(str(caught.exception), caught.exception.lines[0])
        self.assertEqual(ctx["notes"], [])
        self.assertEqual(ctx.get("fallbacks", []), [])

    def test_c_middle_of_origin_move_rejects_endpoint_clear_band(self):
        anchors = {0: [sample((500, 920, 580, 980))]}
        start = self.ctx(keys=[key(scale=3, ox=0)], anchors=anchors)
        end = self.ctx(keys=[key(scale=3, ox=1)], anchors=anchors)
        naive = (60, 1336, 960, 1470)
        self.clear(naive, placer.head_box_at(start, 0, 49))
        self.clear(naive, placer.head_box_at(end, 0, 49))
        ctx = self.ctx(keys=[key(scale=3, ox=0)], anchors=anchors, tweens=[
            dict(start_f=0, end_f=49, prop="origin", **{"from": [0, 0.38], "to": [1, 0.38]},
                 ease="sine.inOut")])
        head = placer.head_box_at(ctx, 0, 49)
        self.assertTrue(placer.hits(naive, head))
        placed = placer.place(ctx, 0, 49)
        self.assertNotEqual(placed, naive)
        self.clear(placed, head)

    def test_c_scale_origin_grid_includes_independent_progress(self):
        anchors = {0: [sample((400, 1050, 680, 1290))]}
        ctx = self.ctx(anchors=anchors, tweens=[
            dict(start_f=0, end_f=40, prop="scale", **{"from": 1, "to": 1.43}, ease="power2.out"),
            dict(start_f=10, end_f=49, prop="origin", **{"from": [0.2, 0.1], "to": [0.8, 0.9]}, ease="none")])
        union = placer.head_box_at(ctx, 10, 20)
        # Different move timings require a product, not pairs at the same progress.
        corner = self.ctx(keys=[key(scale=1.43, ox=0.2, oy=0.1)], anchors=anchors)
        expected = placer.head_box_at(corner, 0, 49)
        self.assertLessEqual(union[0], expected[0])
        self.assertLessEqual(union[1], expected[1])
        self.assertGreaterEqual(union[2], expected[2])
        self.assertGreaterEqual(union[3], expected[3])

    def test_d_each_layout_cover_fits_then_transforms_then_clips(self):
        # Independent expected coordinates, including padding in master pixels.
        expected = {
            "full": (376, 776, 704, 1024),
            "overlay": (376, 776, 704, 1024),
            "split": (376, 1256, 704, 1504),
            "stack": (376, 238, 704, 486),
            "pip": (846.59375, 252.3125, 941.40625, 324),
        }
        for name, want in expected.items():
            with self.subTest(layout=name):
                ctx = self.ctx(keys=[key(layout=name)], anchors={0: [sample((400, 800, 680, 1000))]})
                for actual, value in zip(placer.head_box_at(ctx, 0, 49), want):
                    self.assertAlmostEqual(actual, value)
                self.safe(placer.place(ctx, 0, 49))
        ctx = self.ctx(keys=[key(layout="split", scale=2)], anchors={0: [sample((0, 0, 1080, 1920))]})
        self.assertEqual(placer.head_box_at(ctx, 0, 49), (0, 960, 1080, 1920))

    def test_d_layout_tween_covers_intermediate_box(self):
        ctx = self.ctx(anchors={0: [sample((400, 800, 680, 1000))]}, tweens=[
            dict(start_f=0, end_f=49, prop="layout", **{"from": "full", "to": "split"}, ease="power2.inOut")])
        head = placer.head_box_at(ctx, 0, 49)
        self.assertLessEqual(head[1], 776)
        self.assertGreaterEqual(head[3], 1504)
        self.clear(placer.place(ctx, 0, 49), head)

    def test_e_ghost_hook_and_split_plate_have_spatial_and_time_checks(self):
        ctx = self.ctx(segments=[(0, 50), (50, 100)], beats=[beat(), beat(50, 100, "split")],
                       keys=[key(), key(50, layout="split")], style="layout-switch")
        bands = [dict(start_f=0, end_f=49, box=(60, 280, 960, 414)),
                 dict(start_f=50, end_f=99, box=(60, 600, 960, 734))]
        notes = placer.ghosts(ctx, bands)
        self.assertEqual(len(notes), 2)
        self.assertIn("hook title", notes[0])
        self.assertIn("split card plate", notes[1])
        self.assertIn("seconds", notes[0])
        self.assertEqual(placer.ghosts(ctx, [dict(start_f=0, end_f=99, box=(60, 1200, 960, 1334))]), [])
        self.assertEqual(placer.ghosts(ctx, [dict(start_f=50, end_f=50, box=(60, 1000, 960, 1134))]), [])
        self.assertEqual(placer.ghosts(ctx, [dict(start_f=100, end_f=110, box=(60, 280, 960, 414))]), [])

    def test_e_no_hook_for_opening_scene_and_no_plates_in_punch_style(self):
        ctx = self.ctx(beats=[beat(layout="split", scene={"id": "hook-title"})])
        self.assertEqual(placer.ghosts(ctx, [dict(start_f=0, end_f=49, box=(60, 280, 960, 414))]), [])

    def test_f_missing_segment_uses_reel_median_and_unions_samples(self):
        ctx = self.ctx(segments=[(0, 50), (50, 100)], keys=[key(), key(50)], anchors={0: [
            sample((400, 500, 600, 700)), sample((500, 600, 700, 800), f=40)]})
        self.same_box(placer.head_box_at(ctx, 0, 0), (376, 476, 724, 824))
        self.same_box(placer.head_box_at(ctx, 50, 99), (426, 526, 674, 774))
        self.clear(placer.place(ctx, 40, 60), placer.head_box_at(ctx, 40, 60))

    def test_f_no_anchors_lowest_spot_with_note_and_safe_heights(self):
        for anchors in (None, {}, {0: []}):
            ctx = self.ctx(anchors=anchors)
            self.assertIsNone(placer.head_box_at(ctx, 0, 49))
            self.assertEqual(placer.place(ctx, 0, 49), (60, 1336, 960, 1470))
            self.assertTrue(any("No head samples" in note for note in ctx["notes"]))
            for height in (1, 134, 300, 1250):
                box = placer.place(ctx, 0, 49, height)
                self.safe(box, height)
                self.assertEqual(box[3], 1470)
            with self.assertRaises(placer.NoRoom):
                placer.place(ctx, 0, 49, 1251)

    def test_f_point_sample_gets_fixed_box_and_cuts_union_both_sides(self):
        ctx = self.ctx(segments=[(0, 50), (50, 100)], keys=[key(), key(50, scale=1.12)],
                       anchors={0: [sample(x=0.5, y=0.32)], 1: [sample(f=50, x=0.5, y=0.65)]})
        first = placer.head_box_at(ctx, 0, 49)
        second = placer.head_box_at(ctx, 50, 99)
        self.assertAlmostEqual(first[2] - first[0], 1080 * 0.22 + 2 * placer.HEAD_PAD)
        self.assertAlmostEqual(first[3] - first[1], 1920 * 0.20 + 2 * placer.HEAD_PAD)
        union = placer.head_box_at(ctx, 49, 50)
        self.assertEqual(union, (min(first[0], second[0]), min(first[1], second[1]),
                                 max(first[2], second[2]), max(first[3], second[3])))
        self.clear(placer.place(ctx, 49, 50), union)


if __name__ == "__main__":
    unittest.main(verbosity=2)
