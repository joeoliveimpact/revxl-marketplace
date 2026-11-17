#!/usr/bin/env python3
"""MB2 placement regression, with a recorded MB1 non-world result."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from placer_test import PlacerTests, beat
import placer


class WorldPlacement(PlacerTests):
    # Reuse only the fixture builder, not the inherited test suite.
    def test_world_box_inside_band(self):
        ctx = self.ctx(beats=[beat(scene={"id": "reel-world", "slots": {}, "params": {}})])
        folder = ctx["reel_dir"] / "motion/reel-world"
        folder.mkdir(parents=True)
        (folder / "scene.json").write_bytes(b'{"kind":"world","area":"full","caption_band":[700,900]}\n')
        box = placer.place(ctx, 10, 20, 134)
        self.assertEqual(box, (60, 733, 960, 867))
        self.assertGreaterEqual(box[1], 700)
        self.assertLessEqual(box[3], 900)
        with self.assertRaises(placer.NoRoom):
            placer.place(ctx, 10, 20, 201)

    def test_nonworld_recorded_mb1_result(self):
        ctx = self.ctx()
        placer.set_hook_stills(ctx, [])
        # Recorded from 82365b3 (503c9ef + MB1), before MB2 implementation.
        actual = json.dumps(placer.place(ctx, 10, 20, 134), separators=(",", ":")).encode()
        self.assertEqual(actual, b"[60,1336,960,1470]")

    def test_crossing_world_boundaries(self):
        ctx = self.ctx(segments=[(0, 100)], beats=[beat(0, 25),
            beat(25, 75, scene={"id": "reel-world", "slots": {}, "params": {}}), beat(75, 100)])
        folder = ctx["reel_dir"] / "motion/reel-world"
        folder.mkdir(parents=True)
        (folder / "scene.json").write_bytes(b'{"kind":"world","area":"full","caption_band":[700,900]}\n')
        placer.set_hook_stills(ctx, [])
        sys.path.insert(0, str(placer.HERE.parents[1] / "reel-captions/scripts"))
        import captions
        switches = placer.world_switches(ctx["beats"], ctx["reel_dir"])
        self.assertEqual(switches, [25, 75])
        words = [{"word": "Keep", "start": t, "end": t + .15} for t in (.4, .8, 1.2, 2.4, 2.8, 3.2)]
        chunks = captions.chunk(words, 25, switches, 100)
        (ctx["reel_dir"] / captions.DEFAULT_WORDS).write_bytes(json.dumps({"words": words}).encode())
        planned = captions.plan(ctx["reel_dir"], _style={"style": "clean", "under_small_overlays": False})
        self.assertEqual([(c["start_f"], c["end_f"]) for c in planned["chunks"]],
                         [(c["start_f"], c["end_f"]) for c in chunks])
        for c in chunks:
            self.assertFalse(any(c["start_f"] < f < c["end_f"] for f in switches))
            box = placer.place(ctx, c["start_f"], c["end_f"] - 1, 134)
            self.assertEqual(box, (60, 733, 960, 867) if 25 <= c["start_f"] < 75
                             else (60, 1336, 960, 1470))


if __name__ == "__main__":
    suite = unittest.TestSuite(WorldPlacement(name) for name in (
        "test_world_box_inside_band", "test_nonworld_recorded_mb1_result", "test_crossing_world_boundaries"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
