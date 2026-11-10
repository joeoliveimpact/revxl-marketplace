#!/usr/bin/env python3
"""Synthetic S7.2 caption-placement checks; no video, tools or third-party modules.

Run: python -X utf8 -I tests/editor/placer_test.py
"""
import copy
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        # FX2b prefers under-hook captions; isolate this head-only punch case.
        for ctx in (plain, punched):
            placer.set_hook_stills(ctx, [])
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
                # Least head overlap applies when no hook excludes a candidate.
                placer.set_hook_stills(ctx, [])
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
        # Keep the envelope/tie-break proof independent of FX2b's hook obstacle.
        placer.set_hook_stills(ctx, [])
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
        placed = placer.place(ctx, 49, 50)
        # FX2b allows hair under an active hook, but still protects the face
        # across both cut segments, classifying the caption by its start.
        self.assertTrue(placer.hits(placed, union))
        self.clear(placed, placer.caption_protection(ctx, 49, union))
        self.assertFalse(placer.hits(placed, ctx["stills"][0][2], placer.CAPTION_PAD))

    def broll_ctx(self, rows, end=50, layout="full", fit="cover"):
        b = beat(end=end, layout=layout, scene={"id": "opening"})
        b["broll"] = dict(src="clip.mp4", **{"in": 0, "out": end}, fit=fit)
        ctx = self.ctx(beats=[b], anchors={0: [sample((200, 850, 880, 1500))]})
        # This is the on-disk cache contract, independent of the measuring code.
        identity = json.dumps([0, end, "clip.mp4", 0, end, fit, layout], separators=(",", ":"))
        cache = {"schema": 1, "beats": {identity: dict(rows=rows, mtime_ns=1, size=1)}}
        reel = self.root / str(self.serial)
        (reel / "work/broll-bands.json").write_bytes(json.dumps(cache).encode("utf-8"))
        return placer.load_ctx(reel)

    def test_g_broll_dense_top_uses_plain_bottom_ignoring_hidden_head(self):
        ctx = self.broll_ctx([10] * 65 + [0] * 55)
        box = placer.place(ctx, 0, 49)
        self.assertEqual(box, (60, 1336, 960, 1470))
        self.assertTrue(placer.hits(box, placer.head_box_at(ctx, 0, 49)))
        self.assertEqual(ctx["notes"], [])

    def test_g_broll_dense_bottom_uses_plain_middle(self):
        ctx = self.broll_ctx([10] * 40 + [0] * 25 + [10] * 55)
        box = placer.place(ctx, 0, 49)
        self.assertGreaterEqual(box[1], 648)
        self.assertLessEqual(box[3], 1032)
        self.safe(box)

    def test_g_broll_hook_blocks_plainest_band(self):
        ctx = self.broll_ctx([10] * 120)
        rows = next(iter(ctx["broll_bands"].values()))["rows"]
        rows[15:36] = [0] * 21
        rows[55:75] = [1] * 20
        ctx["stills"] = [(0, 50, (60, 220, 960, 600), "hook title")]
        box = placer.place(ctx, 0, 49)
        self.assertGreaterEqual(box[1], 888)
        self.assertLessEqual(box[3], 1192)
        self.assertFalse(placer.hits(box, ctx["stills"][0][2], placer.CAPTION_PAD))

    def test_g_aroll_minority_missing_profile_and_other_fits_keep_old_placement(self):
        for end, layout, fit, missing in ((24, "full", "cover", False),
                                          (25, "full", "cover", False),
                                          (50, "split", "cover", False),
                                          (50, "full", "contain", False),
                                          (50, "full", "cover", True)):
            with self.subTest(end=end, layout=layout, fit=fit, missing=missing):
                ctx = self.broll_ctx([10] * 65 + [0] * 55, end, layout, fit)
                if missing:
                    ctx["broll_bands"] = {}
                old = placer.place(dict(ctx, broll_bands={}), 0, 49)
                self.assertEqual(placer.place(ctx, 0, 49), old)
        ctx = self.broll_ctx([10] * 65 + [0] * 55, end=26)
        self.assertEqual(placer.place(ctx, 0, 49)[1], 1336)

    def test_g_aroll_span_after_broll_is_unchanged(self):
        ctx = self.broll_ctx([0] * 120, end=25)
        self.assertEqual(placer.place(ctx, 25, 49),
                         placer.place(dict(ctx, broll_bands={}), 25, 49))

    def test_g_adjacent_broll_beats_count_together_for_majority(self):
        ctx = self.broll_ctx([10] * 65 + [0] * 55, end=25)
        second = copy.deepcopy(ctx["beats"][0])
        second.update(start_f=25, end_f=50)
        ctx["beats"].append(second)
        identity = json.dumps([25, 50, "clip.mp4", 0, 25, "cover", "full"], separators=(",", ":"))
        ctx["broll_bands"][identity] = dict(rows=[20] * 65 + [0] * 55)
        self.assertEqual(placer.place(ctx, 0, 49), (60, 1336, 960, 1470))

    def test_g_load_ctx_only_reads_cache_without_decoding_or_writing(self):
        self.broll_ctx([10] * 65 + [0] * 55)
        reel = self.root / str(self.serial)
        with patch.object(placer.broll_bands.subprocess, "run", side_effect=AssertionError("decoded in load_ctx")), \
                patch.object(Path, "write_bytes", side_effect=AssertionError("wrote in load_ctx")):
            ctx = placer.load_ctx(reel)
            self.assertEqual(placer.place(ctx, 0, 49)[1], 1336)


class BrollMeasurementTests(unittest.TestCase):
    def setUp(self):
        import broll_bands
        self.bands = broll_bands
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reel = Path(self.temp.name)
        (self.reel / "work").mkdir()
        self.beat = beat(scene={"id": "opening"})
        self.beat["broll"] = dict(src="clip.mkv", **{"in": 0, "out": 50}, fit="cover")
        (self.reel / "beat-map-selection.json").write_bytes(json.dumps(
            dict(fps=25, beats=[self.beat])).encode("utf-8"))

    def clip(self, changing=False):
        try:
            ffmpeg = self.bands.rt.tool("ffmpeg")
        except (OSError, KeyError, ValueError):
            self.skipTest("SKIP: editor ffmpeg is not installed")
        graph = "color=white:s=270x480:r=25:d=2,drawbox=x=0:y=288:w=270:h=192:color=gray:t=fill"
        for y in range(8, 280, 16):
            graph += f",drawbox=x=20:y={y}:w=210:h=4:color=black:t=fill"
            if changing:
                graph += ":enable='lt(t,1)'"
        if changing:
            for y in range(300, 470, 16):
                graph += f",drawbox=x=20:y={y}:w=210:h=4:color=black:t=fill:enable='gte(t,1)'"
        result = subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", graph,
                                 "-c:v", "ffv1", str(self.reel / "clip.mkv")],
                                capture_output=True, env=self.bands.rt.python_env(), timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_h_measured_clip_plainest_region_is_lower_and_cache_refreshes_on_mtime(self):
        self.clip()
        self.bands.measure(self.reel)
        cache = self.bands.read_cache(self.reel)
        rows = next(iter(cache.values()))["rows"]
        self.assertEqual(len(rows), 120)
        self.assertGreater(sum(rows[15:65]), sum(rows[75:110]))
        self.assertLessEqual(min(rows[75:90]), min(rows[15:65]))
        cached_bytes = (self.reel / "work/broll-bands.json").read_bytes()
        with patch.object(self.bands.subprocess, "run", side_effect=AssertionError("decoded a fresh cache")):
            self.bands.measure(self.reel)
        self.assertEqual((self.reel / "work/broll-bands.json").read_bytes(), cached_bytes)
        clip = self.reel / "clip.mkv"
        stat = clip.stat()
        os.utime(clip, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        # Poison the old result: freshness must cause real decoding, not only new metadata.
        path = self.reel / "work/broll-bands.json"
        stale = json.loads(path.read_text(encoding="utf-8"))
        next(iter(stale["beats"].values()))["rows"] = [999] * 120
        path.write_bytes(json.dumps(stale).encode("utf-8"))
        self.bands.measure(self.reel)
        updated = next(iter(self.bands.read_cache(self.reel).values()))
        self.assertEqual(updated["mtime_ns"], clip.stat().st_mtime_ns)
        self.assertLess(max(updated["rows"]), 999)
        self.assertEqual(updated["rows"], rows)

    def test_h_sampled_range_and_beat_edits_refresh_profile(self):
        self.clip(changing=True)
        self.beat["end_f"] = self.beat["broll"]["out"] = 25
        self.assertEqual(self.bands.measure(self.reel, [self.beat]), [])
        first = next(iter(self.bands.read_cache(self.reel).values()))["rows"]
        self.assertGreater(sum(first[15:65]), sum(first[80:110]))
        self.beat["broll"].update({"in": 25, "out": 50})
        self.assertEqual(self.bands.measure(self.reel, [self.beat]), [])
        last = self.bands.read_cache(self.reel)
        self.assertEqual(len(last), 1)
        rows = next(iter(last.values()))["rows"]
        self.assertGreater(sum(rows[80:110]), sum(rows[15:65]))

    def test_h_unreadable_clip_has_no_profile_and_plain_note(self):
        (self.reel / "clip.mkv").write_bytes(b"not a clip")
        notes = self.bands.measure(self.reel)
        self.assertEqual(self.bands.read_cache(self.reel), {})
        self.assertTrue(any("clip.mkv" in n and "could not" in n.lower() for n in notes), notes)


class RealBrollTests(unittest.TestCase):
    def check_reel(self, variable):
        import broll_bands
        sys.path.insert(0, str(SCRIPTS.parents[1] / "reel-captions/scripts"))
        import captions
        original = Path(os.environ[variable])
        with tempfile.TemporaryDirectory(prefix="broll-placement-") as home:
            reel = Path(home)
            for path in list(original.glob("*.json")) + list((original / "work").rglob("*.json")):
                target = reel / path.relative_to(original)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            send = json.loads((reel / "beat-map-selection.json").read_text(encoding="utf-8"))
            for b in send["beats"]:
                if b.get("broll"):
                    relative = Path(b["broll"]["src"])
                    self.assertFalse(relative.is_absolute())
                    target = (reel / relative).resolve()
                    self.assertTrue(target.is_relative_to(reel.resolve()))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original / relative, target)
            (reel / "work/broll-bands.json").unlink(missing_ok=True)
            notes = broll_bands.measure(reel)
            self.assertEqual(notes, [])
            ctx = placer.load_ctx(reel)
            doc = json.loads((reel / "work/captions.json").read_text(encoding="utf-8"))
            placer.set_hook_stills(ctx, doc["hooks"])
            height = captions.band_h(captions.STYLES[doc["style"]["style"]])
            checked = 0
            for chunk in doc["chunks"]:
                start, end = chunk["start_f"], chunk["end_f"] - 1
                old = placer.place(dict(ctx, broll_bands={}, notes=[]), start, end, height)
                new = placer.place(ctx, start, end, height)
                seconds = float(start / ctx["fps"])
                stop = float((end + 1) / ctx["fps"])
                spotlight = (seconds < 34 and stop > 30) or (seconds < 52 and stop > 49)
                overlapping = [b for b in send["beats"] if start < b["end_f"] and end >= b["start_f"]]
                beat_info = "; ".join(
                    f"{b['id']} [{b['start_f']},{b['end_f']}) layout={b['layout']} "
                    + (f"B-roll fit={b['broll']['fit']} profile="
                       f"{broll_bands.beat_key(b) in ctx['broll_bands']}" if b.get("broll") else "a-roll")
                    for b in overlapping)
                full = [b for b in send["beats"] if b.get("broll") and b["layout"] == "full"
                        and b["broll"]["fit"] == "cover" and b["start_f"] <= start and end < b["end_f"]]
                if full:
                    checked += 1
                    rows = ctx["broll_bands"][broll_bands.beat_key(full[0])]["rows"]
                    def score(y):
                        lo, hi = max(0, math.floor((y - 8) / 16)), min(120, math.ceil((y + height + 8) / 16))
                        return sum(rows[lo:hi]) / (hi - lo)
                    scores = []
                    # Match the complete whole-pixel candidate set, so equality
                    # to the best proves that a retained top band is plainest.
                    for y in set(range(220, math.floor(1470 - height) + 1)) | {
                            1470 - height, min(placer.LOW_Y, 1470 - height)}:
                        box = (60, y, 960, y + height)
                        if placer.active_hook(ctx, start) is None or all(
                                not placer.hits(box, still, 8) for a, e, still, _ in ctx["stills"]
                                if start < e and end >= a):
                            scores.append(score(y))
                    if spotlight:
                        print(f"{variable} {seconds:.2f}-{stop:.2f}s: old y={old[1]}, new y={new[1]}; "
                              f"score chosen={score(new[1]):.6f}, best={min(scores):.6f}, "
                              f"worst={max(scores):.6f}; hook={placer.active_hook(ctx, start) is not None}; "
                              + beat_info)
                    self.assertAlmostEqual(score(new[1]), min(scores), delta=1e-9)
                    self.assertLessEqual(score(new[1]), score(old[1]) + 1e-9)
                    self.assertLessEqual(score(new[1]), sorted(scores)[len(scores) // 4] + 1e-9)
                elif not any(b.get("broll") for b in overlapping):
                    self.assertEqual(new, old)
                    if spotlight:
                        print(f"{variable} {seconds:.2f}-{stop:.2f}s: old y={old[1]}, new y={new[1]}; "
                              "score chosen/best/worst=N/A; reason=a-roll, no B-roll profile applies; " + beat_info)
                elif spotlight:
                    print(f"{variable} {seconds:.2f}-{stop:.2f}s: old y={old[1]}, new y={new[1]}; "
                          "reason=caption crosses a beat boundary or is outside full/cover B-roll; " + beat_info)
            self.assertGreater(checked, 0, "No caption chunks inside full-frame B-roll were checked")

    @unittest.skipUnless(os.environ.get("EDITOR_SE_TEST_REEL_W2E"), "SKIP: EDITOR_SE_TEST_REEL_W2E is unset")
    def test_w2e_broll_chunks_use_plainest_quarter(self):
        self.check_reel("EDITOR_SE_TEST_REEL_W2E")

    @unittest.skipUnless(os.environ.get("EDITOR_SE_TEST_REEL_W1E"), "SKIP: EDITOR_SE_TEST_REEL_W1E is unset")
    def test_w1e_broll_chunks_use_plainest_quarter(self):
        self.check_reel("EDITOR_SE_TEST_REEL_W1E")


if __name__ == "__main__":
    unittest.main(verbosity=2)
