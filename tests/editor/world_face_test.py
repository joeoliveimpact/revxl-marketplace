"""MB3 world area, face choice and Beat Map regressions; no renderer."""
import contextlib
import copy
import io
import json
import re
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reel_scene_test as fixtures
from reel_scene_test import HTML, SID, P, write
import compose
import beat_schema
import overlay_face_check
import scene_check
import scene_render_test


LABEL = "Graphics take the whole screen (hides you)"


def check_cover_control(html):
    """Static board contract, including both directions of the saved choice."""
    control = html.split('if (fill) {', 1)[1].split('if (spec) {', 1)[0]
    for token in ('type: "checkbox"', '"data-cover-face"', LABEL,
                  'b.cover_face === true', 'b.cover_face = true', 'delete b.cover_face',
                  'addEventListener("change"', 'edited()'):
        if token not in control:
            raise AssertionError("Beat Map face choice missing: " + token)
    if 'body: JSON.stringify(doc)' not in html:
        raise AssertionError("Beat Map Send drops the document")


def cover_control_case():
    page = (P / "skills/reel-canvas-build/boards/beat-map/index.html").read_text(encoding="utf-8")
    check_cover_control(page)
    for token in (LABEL, 'b.cover_face = true', 'delete b.cover_face'):
        mutant = page.replace(token, "", 1)
        try:
            check_cover_control(mutant)
        except AssertionError:
            continue
        raise AssertionError("Beat Map face choice mutant survived: " + token)


class WorldFaces(unittest.TestCase):
    setUp = fixtures.ReelScenes.setUp
    inputs = fixtures.ReelScenes.inputs

    def set_area(self, area):
        self.spec.update(area=area, caption_band=[300, 500])
        write(self.scene / "scene.json", self.spec)
        height = {"full": 1920, "stack": 1076, "split": 960}[area]
        write(self.scene / "scene.html", HTML.replace("1920", str(height)))

    def plan(self, inp=None):
        inp = self.inputs() if inp is None else inp
        with patch.object(compose, "saved_brand", return_value={}), contextlib.redirect_stdout(io.StringIO()):
            compose.plan(inp, None)
        return inp

    def test_T1_full_on_stack_refused_before_render(self):
        self.set_area("full")
        self.beat.update(layout="stack")
        self.beat.pop("cover_face", None)
        with self.assertRaises(compose.Stop) as error:
            self.plan()
        self.assertEqual(error.exception.lines, (
            "Reel test world covers the whole screen, which hides you on beat b_001. "
            "Switch this beat to the pip layout, or tick '" + LABEL + "' for this beat.",))
        rows = overlay_face_check.run(dict(reel_dir=self.reel, beats=[self.beat], fps=25))
        self.assertEqual(rows[0]["level"], "block")
        self.assertEqual(compose.qa_block_lines(rows), list(error.exception.lines))

    def test_full_area_refusal_advice_on_full_and_split(self):
        self.set_area("full")
        self.beat.pop("cover_face", None)
        for layout in ("full", "split"):
            self.beat.update(layout=layout)
            with self.subTest(layout=layout), self.assertRaises(compose.Stop) as error:
                self.plan()
            self.assertEqual(error.exception.lines, (
                "Reel test world covers the whole screen, which hides you on beat b_001. "
                "Switch this beat to the pip layout, or tick '" + LABEL + "' for this beat.",))

    def test_area_mismatch_advice_names_working_fixes(self):
        for area in ("stack", "split"):
            self.set_area(area)
            for layout in ("full", "stack", "split", "pip"):
                if area == layout:
                    continue
                target = "full" if layout == "pip" else layout
                advice = ("ask Claude to build a full-screen version and tick '" + LABEL + "'."
                          if layout == "full" else
                          f"ask Claude to build this graphic for the {target} area.")
                for cover in (False, True):
                    self.beat.update(layout=layout, cover_face=cover)
                    with self.subTest(area=area, layout=layout, cover=cover):
                        with self.assertRaises(compose.Stop) as error:
                            self.plan()
                        self.assertEqual(error.exception.lines, (
                            f"Reel test world was made for the {area} layout, "
                            f"but beat b_001 uses the {layout} layout. "
                            f"Switch the beat to the {area} layout, or {advice}",))

    def test_overlay_refusal_advice_names_supported_layouts(self):
        for area in ("full", "stack", "split"):
            self.set_area(area)
            for cover in (False, True):
                self.beat.update(layout="overlay", cover_face=cover)
                with self.subTest(area=area, cover=cover):
                    with self.assertRaises(compose.Stop) as error:
                        self.plan()
                    self.assertEqual(error.exception.lines, (
                        "Beat b_001 uses the overlay layout, which can't hold a full graphic. "
                        "Pick full, stack, split or pip for this beat.",))

    def test_T2_cover_face_allows_full_and_reports_exemption(self):
        self.set_area("full")
        self.beat.update(layout="stack", cover_face=True)
        self.plan()
        rows = overlay_face_check.run(dict(reel_dir=self.reel, beats=[self.beat], fps=25))
        self.assertTrue(any(r["level"] == "pass" and "exempt" in r["msg"] for r in rows))
        self.assertFalse(any(r["level"] == "block" for r in rows))
        rows = compose.qa_check.run_checks(dict(reel_dir=self.reel, beats=[self.beat], fps=25, render=None),
                                           "pre", only={"overlay_face_check"})
        self.assertEqual([(r["check"], r["level"]) for r in rows], [("world-face-exempt", "pass")])

    def test_T3_authored_size_must_match_area_in_attributes_and_css(self):
        self.set_area("stack")
        for bad in (HTML, HTML.replace('height: 1920px', 'height: 1076px'),
                    HTML.replace('data-height="1920"', 'data-height="1076"'),
                    HTML.replace('1920', '1076').replace('height: 1076px', 'height: 960px', 1)):
            with self.subTest(html=bad):
                write(self.scene / "scene.html", bad)
                problems = scene_check.scene_problems(self.scene)
                self.assertTrue(any("made at" in p and "its area stack is 1080x1076" in p for p in problems), problems)

    def test_T4_stack_native_project_and_main_html(self):
        self.set_area("stack")
        self.beat.update(layout="stack", cover_face=False)
        self.assertEqual(scene_check.scene_problems(self.scene), [])
        inp = self.plan()
        compose.scene_project(self.reel / "project", self.beat, Fraction(25), self.reel)
        project = (self.reel / "project/index.html").read_text(encoding="utf-8")
        self.assertIn('data-height="1076"', project)
        page = compose.main_html(inp, 1080, 1920, [(self.beat, "world")])
        video = re.search(r'<video id="scene-world"[^>]+>', page)[0]
        for decl in ('left: 0px', 'top: 844px', 'width: 1080px', 'height: 1076px', 'object-fit: fill'):
            self.assertIn(decl, video)
        self.assertEqual(overlay_face_check.run(dict(reel_dir=self.reel, beats=[self.beat])), [])
        import placer
        ctx = dict(reel_dir=self.reel, beats=[self.beat], fps=Fraction(25), track={"total_f": 75})
        self.assertEqual(placer.place(ctx, 0, 74, 134), (60, 1177, 960, 1311))

    def test_css_effective_size_cannot_be_hidden_by_lower_priority_declarations(self):
        self.set_area("stack")
        page = HTML.replace("1920", "1076")
        for css in (f"#{SID} {{height:1920px!important}} #{SID} {{height:1076px}}",
                    f"#{SID} {{height:1920px}} div {{height:1076px}}"):
            write(self.scene / "scene.html", page.replace("</style>", css + "</style>"))
            self.assertTrue(any("made at" in p for p in scene_check.scene_problems(self.scene)))

    def test_T5_boolean_only_and_send_round_trip(self):
        beat = dict(self.beat, speech_anchor=dict(text="A clear world", w0=0, w1=2),
                    value=None, broll=None, transition=None)
        for value in (True, False):
            sent = json.loads(json.dumps(dict(schema=1, reel="test-world", fps=25,
                words="work/edit_map.cut.json", beats=[dict(beat, cover_face=value)],
                word_marks=[], proposed={}, notes={}, needs="", sent_at=None)))
            beat_schema.validate_beat_map(sent)
            self.assertEqual(beat_schema.beat_problems(sent["beats"][0]), [])
            self.assertIs(sent["beats"][0]["cover_face"], value)
        for bad in ("yes", 1, 0, None, [], {}):
            problems = beat_schema.beat_problems(dict(beat, cover_face=bad))
            self.assertTrue(any("cover_face" in p and "boolean" in p for p in problems), problems)

    def test_T6_board_static_and_dropped_choice_mutant(self):
        cover_control_case()

    def test_area_layout_matrix_and_overlay_never_allowed(self):
        for area in ("full", "stack", "split"):
            self.set_area(area)
            for layout in ("full", "stack", "split", "pip", "overlay"):
                for cover in (False, True):
                    self.beat.update(layout=layout, cover_face=cover)
                    accepted = layout != "overlay" and (area == "full" and (cover or layout == "pip")
                                                        or area == layout and area != "full")
                    with self.subTest(area=area, layout=layout, cover=cover):
                        if accepted:
                            self.plan()
                        else:
                            with self.assertRaises(compose.Stop):
                                self.plan()

    def test_world_safe_box_and_caption_band_use_local_coordinates(self):
        self.set_area("stack")
        self.assertEqual(scene_render_test.hold_problems([(60, 1, 960, 200)], [(60, 1, 960, 200)],
                         [300, 500], area="stack"), [])
        self.assertIn("safe box", scene_render_test.hold_problems([(60, 627, 960, 700)], [],
                      [300, 500], area="stack"))
        self.assertIn("frame edge", scene_render_test.hold_problems([(60, 1070, 960, 1076)], [],
                      [300, 500], area="stack"))
        for area in (None, "unknown", True):
            spec = dict(self.spec, area=area)
            self.assertTrue(scene_check.spec_problems(SID, spec))
        for band in ([-1, 200], [900, 1100]):
            self.assertTrue(scene_check.spec_problems(SID, dict(self.spec, caption_band=band)))

    def test_hold_decoder_uses_area_height(self):
        buf = bytearray(1080 * 1076)
        buf[900 * 1080 + 80] = 255
        with patch.object(scene_render_test, "raw", return_value=bytes(buf)):
            self.assertEqual(scene_render_test.hold_pixel_boxes(Path("stack.mov"), 8, "stack"),
                             [(80, 900, 81, 901)])

    def test_consecutive_stack_worlds_never_get_full_frame_underlay_or_hide_speaker(self):
        self.set_area("stack")
        self.beat.update(layout="stack", cover_face=False)
        inp = self.inputs()
        inp["beats"].append(dict(copy.deepcopy(self.beat), id="b_002", start_f=75, end_f=150))
        inp["total"] = 150
        self.plan(inp)
        self.assertEqual(inp["under"], [])
        self.assertEqual(compose.picture_covers(inp["beats"], 25, reel=self.reel), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
