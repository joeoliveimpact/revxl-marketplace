# Adapted from video-use tests/test_render_fps.py (https://github.com/browser-use/video-use), MIT License, Copyright (c) 2026 Browser Use. Changes: tests fps.py; dropped the r_frame_rate and 24-fps fallbacks (a failed probe now raises); added real-ffprobe checks on synthetic clips.
"""S6b check for reel-canvas-build/scripts/fps.py: rate parsing, the avg-only probe, and real ffprobe runs.

usage: python -X utf8 -I tests/editor/test_render_fps.py -v
ffmpeg/ffprobe come from the editor state (EDITOR_SE_HOME) via runtime.tool, else PATH. Missing = FAIL.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-canvas-build" / "scripts"
MODULE_PATH = SCRIPTS / "fps.py"
SPEC = importlib.util.spec_from_file_location("editor_fps", MODULE_PATH)
assert SPEC and SPEC.loader
fps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fps)
rt = fps.runtime


def _tools():
    """(ffmpeg, ffprobe) or (None, None)."""
    if os.environ.get("EDITOR_SE_HOME"):
        try:
            return rt.tool("ffmpeg"), rt.tool("ffprobe")
        except KeyError:
            pass
    ffm, ffp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    return (ffm, ffp) if ffm and ffp else (None, None)


class ParseFpsTests(unittest.TestCase):
    def test_accepts_integer_decimal_and_rational_rates(self):
        expected = {"60": "60/1", "29.97": "2997/100", "30000/1001": "30000/1001"}
        for value, canonical in expected.items():
            with self.subTest(value=value):
                self.assertEqual(fps.parse_fps(value), canonical)

    def test_canonical_rates_are_idempotent(self):
        for value in ("60", "29.97", "30000/1001"):
            with self.subTest(value=value):
                canonical = fps.parse_fps(value)
                self.assertEqual(fps.parse_fps(canonical), canonical)

    def test_rejects_invalid_or_non_positive_rates(self):
        for value in ("", "nope", "0", "-24", "1/0", "1e3", "1_000", "0.12345678901234567890", "1" * 33,
                      "2147483648", "1/2147483648"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    fps.parse_fps(value)


class ProbeFpsTests(unittest.TestCase):
    @staticmethod
    def _probe_result(avg, nominal):
        stdout = json.dumps({"streams": [{"avg_frame_rate": avg, "r_frame_rate": nominal}]})
        return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")

    def test_prefers_average_rate(self):
        result = self._probe_result("30000/1001", "30/1")
        with patch.object(fps.subprocess, "run", return_value=result):
            self.assertEqual(fps.probe_fps(Path("source.mp4"), ffprobe="ffprobe"), "30000/1001")

    def test_no_nominal_fallback(self):
        result = self._probe_result("0/0", "60/1")
        with patch.object(fps.subprocess, "run", return_value=result):
            with self.assertRaises(fps.FpsError):
                fps.probe_fps(Path("source.mp4"), ffprobe="ffprobe")

    def test_raises_for_unusable_probe_output(self):
        result = subprocess.CompletedProcess([], 0, stdout='{"streams": []}', stderr="")
        with patch.object(fps.subprocess, "run", return_value=result):
            with self.assertRaises(fps.FpsError):
                fps.probe_fps(Path("source.mp4"), ffprobe="ffprobe")

    def test_raises_when_ffprobe_fails(self):
        error = subprocess.CalledProcessError(1, ["ffprobe"])
        with patch.object(fps.subprocess, "run", side_effect=error):
            with self.assertRaises(fps.FpsError):
                fps.probe_fps(Path("source.mp4"), ffprobe="ffprobe")

    def test_argv_never_asks_for_r_frame_rate(self):
        result = self._probe_result("25/1", "50/1")
        with patch.object(fps.subprocess, "run", return_value=result) as run:
            fps.probe_fps(Path("source.mp4"), ffprobe="ffprobe")
        argv = run.call_args.args[0]
        self.assertFalse(any("r_frame_rate" in a for a in argv), argv)
        self.assertIn("stream=avg_frame_rate", argv)


class ResolveFpsTests(unittest.TestCase):
    def test_explicit_rate_skips_probe(self):
        with patch.object(fps, "probe_fps") as probe:
            self.assertEqual(fps.resolve_fps(Path("source.mp4"), explicit="30"), "30/1")
        probe.assert_not_called()

    def test_no_explicit_rate_probes_once(self):
        with patch.object(fps, "probe_fps", return_value="25/1") as probe:
            self.assertEqual(fps.resolve_fps(Path("source.mp4"), ffprobe="ffprobe"), "25/1")
        probe.assert_called_once_with(Path("source.mp4"), "ffprobe")


class RealFfprobeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg, cls.ffprobe = _tools()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.clips = {}
        if not cls.ffmpeg:
            return
        t = Path(cls.tmp.name)
        for name, src, extra in (
            ("25", "testsrc2=r=25:d=2:s=320x240", []),
            ("ntsc", "testsrc2=r=30000/1001:d=2:s=320x240", []),
            ("vfr", "testsrc2=r=30:d=2:s=320x240", ["-vf", r"select='not(eq(mod(n\,5)\,0))'", "-fps_mode", "vfr"]),
        ):
            out = t / f"{name}.mp4"
            p = subprocess.run([cls.ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", src, *extra,
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if p.returncode == 0:
                cls.clips[name] = out
            else:
                cls.clips[name] = p.stderr[-400:]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def clip(self, name):
        self.assertTrue(self.ffmpeg and self.ffprobe, "no ffmpeg/ffprobe in the editor state or on PATH")
        self.assertIsInstance(self.clips.get(name), Path, f"fixture {name} failed: {self.clips.get(name)}")
        return self.clips[name]

    def test_25fps_clip(self):
        c = self.clip("25")
        self.assertEqual(fps.probe_fps(c, self.ffprobe), "25/1")
        self.assertFalse(fps.is_vfr(c, self.ffprobe))
        self.assertEqual(fps.frame_count(c, self.ffprobe), 50)

    def test_ntsc_clip(self):
        c = self.clip("ntsc")
        self.assertEqual(fps.probe_fps(c, self.ffprobe), "30000/1001")
        self.assertFalse(fps.is_vfr(c, self.ffprobe))
        self.assertEqual(fps.frame_count(c, self.ffprobe), 60)

    def test_vfr_clip(self):
        c = self.clip("vfr")
        self.assertTrue(fps.is_vfr(c, self.ffprobe))
        self.assertEqual(fps.frame_count(c, self.ffprobe), 48)

    def test_cli_probe_round_trip(self):
        c = self.clip("25")
        p = subprocess.run([sys.executable, str(MODULE_PATH), "probe", str(c), "--ffprobe", self.ffprobe],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout), {"fps": "25/1", "vfr": False, "frames": 50})


if __name__ == "__main__":
    unittest.main()
