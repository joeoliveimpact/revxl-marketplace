#!/usr/bin/env python3
"""Heavy seek mutants. Run one at a time under heavy_lock.py, like scene_render_test.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene_render_test as render

SID = "reel-seek-world"
FOLDER = Path(__file__).resolve().parent / "fixtures/reel-motion/motion" / SID


class SeekMutants(unittest.TestCase):
    def check_mutant(self, callback, *, pixel_failure_required=False):
        html = (FOLDER / "scene.html").read_text(encoding="utf-8")
        html = html.replace('window.__timelines =', callback + '\nwindow.__timelines =', 1)
        spec = json.loads((FOLDER / "scene.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="seek-mutant-") as home:
            tmp = Path(home)
            # The hidden dependencies must evade the static validator, then fail the dynamic proof.
            scene = tmp / "motion" / SID
            scene.mkdir(parents=True)
            (scene / "scene.html").write_bytes(html.encode("utf-8"))
            (scene / "scene.json").write_bytes(json.dumps(spec).encode("utf-8"))
            self.assertEqual(render.compose.scene_check.scene_problems(scene), [])
            proj = render.project(tmp, "project", html, scene)
            env, log = render.make_env(tmp)
            default, _, _ = render.fills(spec, SID)
            with (patch.object(render, "fails", []) as failures,
                  patch.object(render, "ck", wraps=render.ck) as checks):
                try:
                    render.seek_checks(SID, 90, default, proj, tmp, env, world=True)
                finally:
                    render.kill_warm()
                dom_failures = [line for line in failures if "DOM state" in line]
                pixel_failures = [line for line in failures if "max difference" in line]
                self.assertEqual(len(dom_failures), 1, failures)
                self.assertIn("property style", dom_failures[0])
                measurements = [call.args for call in checks.call_args_list if "max difference" in call.args[0]]
                self.assertEqual(len(measurements), 1, failures)
                self.assertIn("% of pixels differ", measurements[0][0])
                if pixel_failure_required:
                    self.assertFalse(measurements[0][1], measurements)
                # Random samples can rasterise alike; the exact DOM check must still fail.
                self.assertEqual(len(pixel_failures), int(not measurements[0][1]), failures)
                self.assertEqual(len(failures), 1 + len(pixel_failures), failures)
            self.assertFalse(log.exists() and log.read_text(encoding="utf-8").strip())

    def test_one_pixel_jump_dependency(self):
        self.check_mutant('''let previous = 0;
tl.eventCallback("onUpdate", () => {
  const now = tl.time();
  root.querySelector('[data-slot]').style.transform =
    'translateX(' + (now - previous > .05 ? 1 : 0) + 'px)';
  previous = now;
});''', pixel_failure_required=True)

    def test_hidden_random_dependency(self):
        self.check_mutant('''tl.eventCallback("onUpdate", () => {
  root.querySelector('[data-slot]').style.transform =
    'translateX(' + (20 + window["Math"]["rand"+"om"]() * 200) + 'px)';
});''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
