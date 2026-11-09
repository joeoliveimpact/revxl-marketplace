# Adapted from video-use/tests/test_render_captions.py, ChunkWordsTests (MIT).
# Changes by REVXL: word dictionaries, inclusive caption ranges, frame timing,
# layout-switch check; SRT and subtitle-path tests removed.
#
# MIT License
#
# Copyright (c) 2026 Browser Use
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/reel-captions/scripts/captions.py"
SPEC = importlib.util.spec_from_file_location("captions", MODULE_PATH)
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def w(text, start, end):
    return {"word": text, "start": start, "end": end}


# Scribe word timings of a real take: "90% of what a web agent does is completely wasted. We fix this."
TAKE = [
    w("90%", 2.64, 3.04), w("of", 3.06, 3.14), w("what", 3.16, 3.26), w("a", 3.30, 3.34),
    w("web", 3.36, 3.50), w("agent", 3.54, 3.82), w("does", 3.86, 4.14), w("is", 4.48, 4.56),
    w("completely", 4.58, 4.90), w("wasted.", 4.94, 5.34), w("We", 6.08, 6.18), w("fix", 6.24, 6.42),
    w("this.", 6.48, 6.70),
]


def cues(items, switches=()):
    return render.chunk(items, 100, switches, 1000)


def texts(items, chunks=None):
    return [" ".join(items[i]["word"] for i in range(c["w0"], c["w1"] + 1)
                     if items[i]["word"].strip()) for c in (cues(items) if chunks is None else chunks)]


class ChunkWordsTests(unittest.TestCase):
    def test_real_take(self):
        self.assertEqual(texts(TAKE),
                         ["90% of", "what a web", "agent does", "is completely", "wasted.", "We fix this."])

    def test_pause_splits_across_words(self):
        self.assertNotIn("does is", [c.lower() for c in texts(TAKE)])

    def test_no_multiword_cue_flashes(self):
        for c in cues(TAKE):
            count = c["w1"] - c["w0"] + 1
            if 1 < count < 3:
                self.assertGreaterEqual(TAKE[c["w1"]]["end"] - TAKE[c["w0"]]["start"], 0.35)
                self.assertGreaterEqual(c["end_f"] - c["start_f"], 35)

    def test_punctuation_still_breaks(self):
        self.assertEqual(texts([w("Hi,", 0, 0.1), w("there", 0.12, 0.2)]), ["Hi,", "there"])

    def test_caps_at_max_words(self):
        fast = [w(f"w{i}", i * 0.05, i * 0.05 + 0.04) for i in range(7)]
        self.assertTrue(all(c["w1"] - c["w0"] + 1 <= 3 for c in cues(fast)))

    def test_skips_empty_words(self):
        self.assertEqual(texts([w(" ", 0, 0.1), w("ok", 0.1, 0.5)]), ["ok"])

    def test_layout_switch_splits_mid_phrase(self):
        items = [w("a", 0, 0.08), w("new", 0.1, 0.18), w("look", 0.2, 0.28)]
        chunks = cues(items, [10])
        self.assertEqual(texts(items, chunks), ["a", "new look"])
        self.assertTrue(all(not c["start_f"] < 10 < c["end_f"] for c in chunks))


if __name__ == "__main__":
    unittest.main()
