"""MB7-A reel-world frame-rate matrix; real source encodes, mocked scene renders.

Run: python -X utf8 -I tests/editor/reel_fps_matrix_test.py -v
NTSC labels below mean the exact rationals, not the rounded decimal strings.
The optional scene encode is omitted: the shipped review path has no tiny-size
option and renders several 1080x1920 passes before making a 720-wide loop.
"""
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins/editor-superengine/skills/reel-canvas-build/scripts"
FIXTURE = REPO / "tests/editor/fixtures/reel-motion/motion/reel-good-world"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
import compose
import fps
import make_beat_map
import motion_review as review
import scene_render as sr

RATES = (
    ("23.976", "24000/1001"), ("24", "24/1"), ("25", "25/1"),
    ("29.97", "30000/1001"), ("30", "30/1"), ("50", "50/1"),
    ("59.94", "60000/1001"),
)
SID = "reel-good-world"
BEAT_START = 1.234
WORD_STARTS = (1.901, 3.517)
BEAT_END = 4.111


def _tools():
    """Editor-state tools (including the default state), then PATH, independently.

    Unlike the older _tools pattern, a missing ffprobe must not masquerade as
    missing ffmpeg: only truly missing ffmpeg permits a skip in this matrix.
    """
    found = []
    for name in ("ffmpeg", "ffprobe"):
        try:
            candidate = sr.rt.tool(name)
        except KeyError:
            candidate = None
        found.append(shutil.which(candidate) if candidate else None)
        if not found[-1]:
            found[-1] = shutil.which(name)
    return tuple(found)


class _Tags(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.by_id = {}
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.by_id[attrs["id"]] = attrs


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8"))


class ReelFpsMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mb7-fps-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _beat_doc(self, reel, rate, items):
        # build_doc tiles the first beat from zero, so a lead-in is necessary
        # to get a real nonzero, word-derived scene start. Only b_002 has a scene.
        plan = {"beats": [
            {"w0": 0, "w1": 0, "layout": "full"},
            {"w0": 1, "w1": 3, "layout": "full"},
            {"w0": 4, "w1": 4, "layout": "full"},
        ]}
        return make_beat_map.build_doc(
            reel, plan, [w["word"] for w in items], items,
            "work/word_map.json", reel / "work/word_map.json", rate, round(5 * rate))

    def _reel(self, canonical):
        rate = Fraction(canonical)
        reel = self.root / canonical.replace("/", "-")
        folder = reel / "motion" / SID
        folder.mkdir(parents=True)
        items = [{"word": word, "start": start, "end": end} for word, start, end in (
            ("Lead", 0.0, 1.1), ("Beat", BEAT_START, 1.5),
            ("First", WORD_STARTS[0], 2.1), ("Second", WORD_STARTS[1], 3.8),
            ("Tail", BEAT_END, 5.0),
        )]
        for i, word in enumerate(items):
            word.update(id=f"w_{i:04d}", out_start=word["start"])
        _write_json(reel / "work/word_map.json", {"words": items})
        doc = self._beat_doc(reel, rate, items)
        beat = doc["beats"][1]
        params = {f"t{i}": compose.word_param(beat, word, rate)
                  for i, word in enumerate(items[2:4], 1)}
        spec = json.loads((FIXTURE / "scene.json").read_text(encoding="utf-8"))
        spec["holds"] = [0, "t1", "t2"]
        for name, value in params.items():
            spec["params"][name] = {"type": "number", "default": value, "min": 0, "max": 5,
                                    "word": items[int(name[1:]) + 1]["id"]}
        _write_json(folder / "scene.json", spec)
        page = (FIXTURE / "scene.html").read_text(encoding="utf-8")
        variables = [{"id": name, "type": "string", "label": name, "default": s["default"]}
                     for name, s in spec["slots"].items()]
        variables += [{"id": name, "type": p["type"], "label": name, "default": p["default"]}
                      for name, p in spec["params"].items()]
        page = re.sub(r"data-composition-variables='[^']*'",
                      lambda _: "data-composition-variables='" + json.dumps(variables) + "'", page)
        # Give the copied world two explicit GSAP cue positions in seconds.
        page = re.sub(r"tl\.fromTo\(camera,.*?(?=window\.__timelines)",
                      'tl.set(camera, {x: -150}, Number(v.t1));\n'
                      'tl.set(camera, {x: 0}, Number(v.t2));\n\n', page, flags=re.S)
        (folder / "scene.html").write_bytes(page.encode("utf-8"))
        beat.update(cover_face=True, scene={"id": SID, "slots": {"text": "Word cues"}, "params": params})
        doc["fps"] = canonical
        _write_json(reel / "beat-map-selection.json", doc)
        self.assertEqual(compose.scene_check.scene_problems(folder), [])
        self.assertEqual((beat["start_f"], beat["end_f"]),
                         (round(BEAT_START * rate), round(BEAT_END * rate)))
        return reel, rate, beat, spec, items

    def test_composite_position_and_seconds_round_trip(self):
        for label, canonical in RATES:
            with self.subTest(rate=label, rational=canonical):
                reel, rate, beat, _, _ = self._reel(canonical)
                inp = dict(rate=rate, total=round(5 * rate), beats=[beat], reel_dir=reel,
                           under=[], hook_f=0, hook_text="", hooks=[])
                page = compose.main_html(inp, 360, 640, [(beat, "matrix")])
                attrs = _Tags(page).by_id["scene-matrix"]
                for key, frame in (("data-start", beat["start_f"]),
                                   ("data-duration", beat["end_f"] - beat["start_f"])):
                    self.assertEqual(attrs[key], compose.ts(frame, rate))
                    self.assertEqual(round(float(attrs[key]) * rate), frame)
                self.assertEqual(attrs["src"], "media/matrix.mov")

    def test_word_frames_equal_absolute_word_frames(self):
        for label, canonical in RATES:
            with self.subTest(rate=label, rational=canonical):
                reel, rate, beat, _, items = self._reel(canonical)
                project = reel / "word-scene"
                self.assertIsNone(compose.scene_project(project, beat, rate, reel))
                page = (project / "index.html").read_text(encoding="utf-8")
                for i, word_start in enumerate(WORD_STARTS, 1):
                    with self.subTest(param=f"t{i}"):
                        self.assertIn(f"Number(v.t{i})", page)
                        # The copied world passes Number(v.tN) straight
                        # to GSAP; scene_project changes duration, not cue seconds.
                        # Judge the cue's nearest frame, without the hold's +0.25 s offset.
                        local = round(beat["scene"]["params"][f"t{i}"] * rate)
                        self.assertEqual(local, round(compose.word_param(beat, items[i + 1], rate) * rate))
                        absolute = beat["start_f"] + local
                        word_frame = round(word_start * rate)
                        self.assertEqual(absolute, word_frame,
                                         f"t{i}: composite {absolute}, word {word_frame}, drift {absolute - word_frame:+d}")

    def _assert_helper_word_frames(self, beat, words, rate):
        for word in words:
            self.assertEqual(beat["start_f"] + round(compose.word_param(beat, word, rate) * rate),
                             round(Fraction(str(word["out_start"])) * rate))

    def _assert_timing_refused_before_work(self, reel, rate, beat):
        # Both entry paths must reject before any render or job lock.
        message = r"Beat b_002.*t2.*w_0003"
        with (patch.object(compose, "heavy_job") as lock, patch.object(compose, "broll_plan") as render,
              self.assertRaisesRegex(compose.Stop, message)):
            compose.plan({"beats": [beat], "rate": rate, "reel_dir": reel}, None)
        lock.assert_not_called()
        render.assert_not_called()
        for tier in ("preview", "master"):
            with (self.subTest(tier=tier),
                  patch.object(compose, "load_inputs", return_value={"beats": [beat], "rate": rate}),
                  patch.object(compose, "probe_inputs"), patch.object(compose, "ok_problem", return_value=None),
                  patch.object(compose.styles, "plan") as planning, patch.object(compose, "heavy_job") as lock,
                  patch.object(compose, "hf_render") as render, self.assertRaisesRegex(compose.Stop, message)):
                compose.render(reel, tier, None)
            planning.assert_not_called()
            lock.assert_not_called()
            render.assert_not_called()
        with (patch.object(review, "heavy_job") as lock, patch.object(review, "build_media") as render,
              self.assertRaisesRegex(ValueError, message)):
            review.build(reel)
        lock.assert_not_called()
        render.assert_not_called()

    def test_mutant_word_helper_one_frame_is_caught_and_refused(self):
        original = compose.word_param
        for label, canonical in RATES:
            with self.subTest(rate=label):
                reel, rate, beat, _, items = self._reel(canonical)
                self._assert_helper_word_frames(beat, items[2:4], rate)
                def mutant(b, word, r):
                    value = original(b, word, r)
                    return value + float(1 / r) if word["id"] == "w_0003" else value
                with patch.object(compose, "word_param", side_effect=mutant):
                    with self.assertRaises(AssertionError):
                        self._assert_helper_word_frames(beat, items[2:4], rate)
                    self._assert_timing_refused_before_work(reel, rate, beat)

    def test_old_first_word_time_is_refused(self):
        reel, rate, beat, _, _ = self._reel("24/1")
        beat["scene"]["params"]["t2"] = WORD_STARTS[1] - BEAT_START
        doc = json.loads((reel / "beat-map-selection.json").read_text())
        doc["beats"][1] = beat
        # Validate every use, even a later beat sharing an already-reviewed scene.
        doc["beats"].insert(0, dict(beat, id="b_good", scene=dict(beat["scene"], params={"t2": 2.25})))
        _write_json(reel / "beat-map-selection.json", doc)
        self._assert_timing_refused_before_work(reel, rate, beat)

    def test_word_param_boundaries_and_invalid_times(self):
        beat, rate = {"id": "b_test", "start_f": 30, "end_f": 90}, Fraction(30)
        self.assertEqual(compose.word_param(beat, {"id": "w_0001", "out_start": 1}, rate), 0)
        self.assertEqual(round(compose.word_param(beat, {"out_start": 2.5}, rate) * rate), 45)
        for start in (0, .9999, 3, 3.0001, 4):
            with self.subTest(start=start), self.assertRaisesRegex(ValueError, "outside beat b_test"):
                compose.word_param(beat, {"id": "w_0001", "out_start": start}, rate)
        for word in ({"start": 2}, {"out_start": True}, {"out_start": float("nan")}):
            with self.subTest(word=word), self.assertRaisesRegex(ValueError, "cut start time"):
                compose.word_param(beat, word, rate)

    def test_times_cli_uses_cut_times_and_reports_bad_references(self):
        reel, rate, beat, _, items = self._reel("24000/1001")
        # A source transcript timestamp must not override the cut's out_start.
        items[3]["start"] = 999
        _write_json(reel / "work/word_map.json", {"words": items})
        argv = [str(SCRIPTS / "motion_review.py"), "times", "--reel-dir", str(reel),
                "--beat", beat["id"], "--words", "w_0002,w_0003"]
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", *argv], capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        params = json.loads(result.stdout)
        self.assertEqual(params, beat["scene"]["params"])
        for i, word in enumerate(items[2:4], 1):
            self.assertEqual(beat["start_f"] + round(params[f"t{i}"] * rate),
                             round(Fraction(str(word["out_start"])) * rate))
        for bid, words, reason in (("missing", "w_0002", "Beat missing"),
                                   (beat["id"], "w_9999", "Word w_9999"),
                                   (beat["id"], "w_0000", "outside beat")):
            with self.subTest(beat=bid, words=words):
                with patch.object(sys, "argv", argv[:3] + [str(reel), "--beat", bid, "--words", words]), \
                        contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(review.main(), 1)
                self.assertIn(reason, out.getvalue())

    def test_scene_word_reference_shape_only(self):
        _, _, _, spec, _ = self._reel("24/1")
        for word in ("w_0013", "w_999999"):
            spec["params"]["t1"]["word"] = word
            self.assertEqual(compose.scene_check.spec_problems(SID, spec), [])
        for word in (None, 13, "", "../w_0013", "w_nope"):
            spec["params"]["t1"]["word"] = word
            with self.subTest(word=word):
                self.assertTrue(any("word" in p for p in compose.scene_check.spec_problems(SID, spec)))

    def test_mutant_first_word_beat_start_is_caught(self):
        drifts = []
        for label, canonical in RATES:
            _, rate, beat, _, _ = self._reel(canonical)
            for word_start in WORD_STARTS:
                old_param = word_start - BEAT_START
                absolute = beat["start_f"] + round(old_param * rate)
                if absolute != round(word_start * rate):
                    drifts.append((label, word_start))
        self.assertTrue(drifts, "The old first-word-time interpretation must fail exact word-frame equality")

    def test_hold_frames_and_judgement_not_before_words(self):
        for label, canonical in RATES:
            with self.subTest(rate=label, rational=canonical):
                _, rate, beat, spec, _ = self._reel(canonical)
                duration = beat["end_f"] - beat["start_f"]
                params = beat["scene"]["params"]
                expected = {duration - 1, min(duration - 1, round(.25 * rate))}
                for i, word_start in enumerate(WORD_STARTS, 1):
                    judged = min(duration - 1, round((params[f"t{i}"] + .25) * rate))
                    expected.add(judged)
                    self.assertGreaterEqual(beat["start_f"] + judged, round(word_start * rate))
                self.assertEqual(sr.hold_frames(spec, params, duration, fps=rate), sorted(expected))
                self.assertEqual(sr.hold_frames(spec, {}, duration, fps=rate), sorted(expected))
                # A numeric zero hold is judged at +0.25 s, not at frame zero.
                self.assertEqual(sr.hold_frames(spec, params, 1, fps=rate), [0])

    def _review_media(self, reel, rate, beat):
        send = review.read(reel / "beat-map-selection.json")
        _write_json(reel / "beat-map-selection.json", dict(send, edit_style={"style": "punch-in"}))
        work = Path(tempfile.mkdtemp(prefix="review-", dir=reel))
        renders = reel / "work/renders"
        renders.mkdir(exist_ok=True)
        (renders / "master-fixture.mp4").write_bytes(b"mocked media boundary\n")
        entry, = review.entries(reel)
        self.assertEqual(entry["_rate"], rate)
        # Keep build_media, scene_project and scene_test real. Only rendering,
        # offline tool setup and media IO are replaced; capture the actual
        # frame count scene_test hands to its expensive checks.
        with (patch.object(sr, "make_env", return_value=({}, work / "net.jsonl")),
              patch.object(sr, "project", return_value=work),
              patch.object(sr, "base_checks") as base,
              patch.object(sr, "seek_checks") as seek,
              patch.object(sr, "probe", side_effect=lambda _: {"nb_read_frames": base.call_args.args[4]}),
              patch.object(sr, "caption_band_ranges", return_value=[]),
              patch.object(sr, "kill_warm"), patch.object(review, "run_media") as media,
              contextlib.redirect_stdout(io.StringIO())):
            review.build_media(reel, entry, work)
        self.assertEqual(base.call_count, 2, "Authored and selected fills must both reach checks")
        self.assertEqual(seek.call_count, 2)
        self.assertEqual(base.call_args_list[0].kwargs["fps"], 30)
        self.assertEqual(base.call_args.kwargs["fps"], rate)
        self.assertEqual(seek.call_args.kwargs["fps"], rate)
        self.assertEqual(base.call_args.args[6]["t2"], beat["scene"]["params"]["t2"])
        self.assertEqual(len(media.call_args_list), 3)
        page = (work / "selected/index.html").read_text(encoding="utf-8")
        loop = media.call_args_list[-1].args[0]
        return page, loop, base.call_args.args[4]

    def _assert_review_duration(self, page, loop, rate, beat):
        duration = beat["end_f"] - beat["start_f"]
        attrs = _Tags(page).by_id[SID]
        self.assertEqual(round(float(attrs["data-duration"]) * rate), duration,
                         "Selected scene duration must round-trip to the beat's frame count")
        self.assertEqual(round(float(loop[loop.index("-t") + 1]) * rate), duration)
        self.assertEqual(round(float(loop[loop.index("-ss") + 1]) * rate), beat["start_f"])
        self.assertEqual(Fraction(loop[loop.index("-r") + 1]), rate)
        self.assertEqual(int(loop[loop.index("-frames:v") + 1]), duration)

    def test_motion_review_selected_and_loop_frame_counts(self):
        for label, canonical in RATES:
            with self.subTest(rate=label, rational=canonical):
                reel, rate, beat, _, _ = self._reel(canonical)
                page, loop, checked_frames = self._review_media(reel, rate, beat)
                self._assert_review_duration(page, loop, rate, beat)
                self.assertEqual(checked_frames, beat["end_f"] - beat["start_f"],
                                 "Selected review render/checks must use the reel's frame rate")

    def test_mutant_one_frame_duration_is_caught(self):
        original_ts = compose.ts
        for label, canonical in RATES:
            with self.subTest(rate=label, rational=canonical):
                reel, rate, beat, _, _ = self._reel(canonical)
                page, loop, _ = self._review_media(reel, rate, beat)
                self._assert_review_duration(page, loop, rate, beat)
                # Mutate duration formatting without also mutating the word helper's cue times.
                duration = beat["end_f"] - beat["start_f"]
                with patch.object(compose, "ts", side_effect=lambda f, r: original_ts(
                        f + 1 if f == duration else f, r)) as mutant:
                    page, loop, _ = self._review_media(reel, rate, beat)
                    mutant.assert_called()
                    with self.assertRaisesRegex(AssertionError, "Selected scene duration"):
                        self._assert_review_duration(page, loop, rate, beat)

    def test_real_b_frame_source_probe_and_beat_frames(self):
        ffmpeg, ffprobe = _tools()
        for label, canonical in RATES:
            with self.subTest(rate=label, rational=canonical):
                if not ffmpeg:
                    self.skipTest("ffmpeg is absent from editor state and PATH")
                self.assertIsNotNone(ffprobe, "ffmpeg exists but ffprobe is missing; cannot prove source frames")
                reel, rate, beat, _, items = self._reel(canonical)
                clip = reel / "source.mp4"
                frames = round(2 * rate)
                encoded = subprocess.run([
                    ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"testsrc2=size=160x284:rate={canonical}", "-frames:v", str(frames),
                    "-r", canonical, "-c:v", "libx264", "-preset", "ultrafast", "-bf", "2",
                    "-pix_fmt", "yuv420p", str(clip),
                ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
                self.assertEqual(encoded.returncode, 0, encoded.stderr)
                probed = fps.probe_fps(clip, ffprobe)
                self.assertEqual(probed, canonical)
                self.assertEqual(fps.parse_fps(probed), canonical)
                self.assertEqual(fps.frame_count(clip, ffprobe), frames)
                stream = subprocess.run([
                    ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                    "stream=has_b_frames,width,height", "-of", "json", str(clip),
                ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=True)
                metadata, = json.loads(stream.stdout)["streams"]
                self.assertGreater(metadata["has_b_frames"], 0)
                self.assertEqual((metadata["width"], metadata["height"]), (160, 284))
                measured = self._beat_doc(reel, fps.as_fraction(probed), items)
                saved = json.loads((reel / "beat-map-selection.json").read_text(encoding="utf-8"))
                self.assertEqual([(b["start_f"], b["end_f"]) for b in measured["beats"]],
                                 [(b["start_f"], b["end_f"]) for b in saved["beats"]])
                self.assertEqual((measured["beats"][1]["start_f"], measured["beats"][1]["end_f"]),
                                 (beat["start_f"], beat["end_f"]))


if __name__ == "__main__":
    unittest.main()
