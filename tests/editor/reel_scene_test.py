#!/usr/bin/env python3
"""MB1 reel scenes: static contract, resolver and compose integration; no render."""
import contextlib
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
sys.path.insert(0, str(P / "scripts"))
sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
import scene_check
import scene_fill
import compose

SID = "reel-test-world"
HTML = """<!doctype html>
<html data-composition-variables='[{"id":"text","type":"string","label":"Text","default":"A clear world"},{"id":"accent","type":"color","label":"Accent","default":"#4f8cff"},{"id":"font","type":"string","label":"Font","default":"Inter"}]'>
<head><script src="./vendor/gsap.min.js"></script><style>
@font-face { font-family: "Inter"; src: url("./fonts/Inter-Regular.woff2"); font-weight: 400; font-style: normal; }
html, body { width: 1080px; height: 1920px; }
#reel-test-world { width: 1080px; height: 1920px; z-index: 400; font-family: "Inter"; font-weight: 400; }
.plate { position: absolute; left: 60px; top: 400px; width: 900px; height: 400px; background: #123456; }
</style></head><body>
<div id="reel-test-world" data-composition-id="reel-test-world" data-duration="3" data-width="1080" data-height="1920"><div class="plate"><span data-slot="text"></span></div></div>
<script>
const v = window.__hyperframes.getVariables();
const root = document.getElementById("reel-test-world");
root.querySelector("[data-slot]").textContent = v.text;
root.style.color = v.accent; root.style.fontFamily = v.font;
const tl = gsap.timeline({ paused: true });
tl.fromTo(root, {opacity: 0}, {opacity: 1, duration: 0.2}, 0);
window.__timelines = window.__timelines || {};
window.__timelines["reel-test-world"] = tl;
</script></body></html>
"""


def write(path, data):
    text = data if isinstance(data, str) else json.dumps(data)
    raw = text.encode("utf-8")
    assert b"\r" not in raw
    path.write_bytes(raw)


class ReelScenes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.reel = Path(self.tmp.name)
        self.motion = self.reel / "motion"
        self.scene = self.motion / SID
        self.scene.mkdir(parents=True)
        self.spec = dict(id=SID, category=SID, kind="world", area="full", dur=[1, 10],
                         holds=[0], caption_band=[1320, 1470],
                         slots={"text": {"maxChars": 80, "default": "A clear world"}},
                         params={"accent": {"type": "color", "default": "#4f8cff"},
                                 "font": {"type": "string", "default": "Inter"}},
                         source="Own text-only fixture for beat b_001, locked test direction", licence="own")
        write(self.scene / "scene.json", self.spec)
        write(self.scene / "scene.html", HTML)
        shutil.copyfile(P / "scenes/callout/preview.png", self.scene / "preview.png")
        write(self.motion / "assets.json", {"files": []})
        self.fill = dict(id=SID, slots={"text": "A clear world"}, params={})
        self.beat = dict(id="b_001", scene=self.fill, start_f=0, end_f=75, layout="full", cover_face=True)

    def run_check(self, *args):
        return subprocess.run([sys.executable, "-X", "utf8", "-I", str(P / "scripts/scene_check.py"),
                               *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=60)

    def asset(self, ref="./assets/logo.svg"):
        write(self.scene / "scene.html", HTML.replace("</body>", f'<img src="{ref}"></body>'))
        assets = self.motion / "assets"
        assets.mkdir(exist_ok=True)
        file = assets / "logo.svg"
        write(file, '<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2"/></svg>')
        return file

    def list_asset(self, digest):
        write(self.motion / "assets.json", {"files": [{"path": "logo.svg", "sha256": digest,
              "source": "Own rectangle fixture; no brand artwork"}]})

    def inputs(self):
        return dict(beats=[copy.deepcopy(self.beat)], rate=Fraction(25), fps="25/1", total=75,
                    words=["A", "clear", "world"], cut_frames=[], reel_dir=self.reel)

    def test_contract_and_resolver(self):
        result = self.run_check("check", self.motion)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "OK " + SID)
        self.assertEqual(scene_check.scene_dir(SID, self.reel), self.scene)
        self.assertEqual(scene_check.scene_dir("callout"), scene_check.SCENES / "callout")
        self.assertEqual(scene_fill._scene_dir(SID, self.reel), self.scene)
        self.assertFalse(any(item["id"].startswith("reel-") for item in scene_fill.catalog()))

    def test_reel_check_without_preview(self):
        (self.scene / "preview.png").unlink()
        self.assertEqual({file.name for file in self.scene.iterdir()}, {"scene.json", "scene.html"})
        result = self.run_check("check", self.motion)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "OK " + SID)

    def test_reel_check_rejects_broken_preview(self):
        (self.scene / "preview.png").write_bytes(b"not a PNG")
        result = self.run_check("check", self.motion)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL " + SID + ":", result.stdout)
        self.assertIn("preview.png", result.stdout)

    def test_catalog_check_requires_preview(self):
        scenes = self.reel / "scenes"
        target = scenes / "callout"
        shutil.copytree(P / "scenes/callout", target)
        baseline = self.run_check("check", scenes)
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)
        (target / "preview.png").unlink()
        result = self.run_check("check", scenes)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL callout: the folder is missing preview.png", result.stdout)

    def test_unsafe_and_missing_ids(self):
        for sid, reel in (("reel-x", None), ("../x", self.reel), ("reel-A_b", self.reel),
                          ("reel-", self.reel), ("reel-" + "a" * 60, self.reel),
                          ("reel-missing", self.reel), ("catalog-missing", None),
                          ("a\\b", self.reel), ("/callout", None), (None, self.reel)):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                scene_check.scene_dir(sid, reel)

    def test_asset_unlisted_mismatch_missing_and_pass(self):
        file = self.asset()
        self.assertIn("not listed", " ".join(scene_check.scene_problems(self.scene)))
        self.list_asset("0" * 64)
        self.assertIn("sha256", " ".join(scene_check.scene_problems(self.scene)))
        self.list_asset(hashlib.sha256(file.read_bytes()).hexdigest())
        self.assertEqual(scene_check.scene_problems(self.scene), [])
        result = self.run_check("check", self.motion)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        file.unlink()
        self.assertIn("missing", " ".join(scene_check.scene_problems(self.scene)))

    def test_asset_path_and_manifest_contract(self):
        file = self.asset()
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        self.list_asset(digest)
        for ref in ("../assets/logo.svg", "./assets/../assets/logo.svg", "./logo.svg", "./assets/logo.woff2"):
            self.asset(ref)
            self.assertTrue(scene_check.scene_problems(self.scene), ref)
        self.asset()
        for manifest in ({"files": [{"path": "../logo.svg", "sha256": digest, "source": "test"}]},
                         {"files": [{"path": "logo.svg", "sha256": digest, "source": ""}]},
                         {"files": "wrong"}):
            write(self.motion / "assets.json", manifest)
            self.assertTrue(scene_check.scene_problems(self.scene), manifest)
        write(self.motion / "assets.json", "{")
        self.assertIn("assets.json", " ".join(scene_check.scene_problems(self.scene)))

    def test_asset_names_with_spaces_and_unquoted_references(self):
        file = self.asset()
        official = file.with_name("Official logo.svg")
        file.rename(official)
        write(self.scene / "scene.html", HTML.replace("</body>", '<img src="./assets/Official logo.svg"></body>'))
        write(self.motion / "assets.json", {"files": [{"path": official.name,
              "sha256": hashlib.sha256(official.read_bytes()).hexdigest(), "source": "Own test artwork"}]})
        self.assertEqual(scene_check.scene_problems(self.scene), [])
    def test_unquoted_reference_requires_manifest(self):
        write(self.scene / "scene.html", HTML.replace("</body>", '<img src=./assets/unlisted.svg></body>'))
        self.assertIn("not listed", " ".join(scene_check.scene_problems(self.scene)))

    def test_world_is_reel_only_and_own(self):
        spec = json.loads((P / "scenes/callout/scene.json").read_text(encoding="utf-8"))
        spec["kind"] = "world"
        self.assertIn("reel", " ".join(scene_check.spec_problems("callout", spec)))
        self.spec["licence"] = "Apache-2.0"
        write(self.scene / "scene.json", self.spec)
        self.assertIn("own", " ".join(scene_check.scene_problems(self.scene)))
        self.spec["licence"], self.spec["category"] = "own", "callout"
        write(self.scene / "scene.json", self.spec)
        self.assertIn("category", " ".join(scene_check.scene_problems(self.scene)))

    def test_world_holds_and_caption_band(self):
        self.assertEqual(scene_check.spec_problems(SID, self.spec), [])
        for key in ("holds", "caption_band"):
            spec = copy.deepcopy(self.spec)
            del spec[key]
            self.assertIn(key, " ".join(scene_check.spec_problems(SID, spec)))
        for holds in ([], "t1", [True], [-1], [float("nan")], [float("inf")],
                      ["missing"], ["accent"], [{}]):
            with self.subTest(holds=holds):
                spec = dict(self.spec, holds=holds)
                self.assertIn("holds", " ".join(scene_check.spec_problems(SID, spec)))
        for band in (None, [1320], [219, 1470], [1320, 1471], [1320, 1400],
                     [1470, 1320], [True, 1470], [float("nan"), 1470]):
            with self.subTest(band=band):
                self.assertIn("caption_band", " ".join(scene_check.spec_problems(
                    SID, dict(self.spec, caption_band=band))))
        spec = copy.deepcopy(self.spec)
        spec["params"]["t1"] = {"type": "number", "default": 1.5}
        spec["holds"] = [0, "t1", 2.5]
        self.assertEqual(scene_check.spec_problems(SID, spec), [])
        spec["params"]["t1"]["default"] = -1
        self.assertIn("holds", " ".join(scene_check.spec_problems(SID, spec)))

    def test_hold_keys_forbidden_on_other_kinds(self):
        for kind in ("overlay", "takeover"):
            for key in ("holds", "caption_band"):
                spec = copy.deepcopy(self.spec)
                spec["kind"] = kind
                del spec["caption_band" if key == "holds" else "holds"]
                self.assertIn(key, " ".join(scene_check.spec_problems(SID, spec)))
                catalog = json.loads((P / "scenes/callout/scene.json").read_text(encoding="utf-8"))
                catalog[key] = spec[key]
                self.assertIn(key, " ".join(scene_check.spec_problems("callout", catalog)))

    def test_catalog_cannot_use_reel_id(self):
        target = self.reel / "catalog" / SID
        shutil.copytree(self.scene, target)
        self.assertIn("motion", " ".join(scene_check.scene_problems(target)))

    def test_fill_cli(self):
        fill = self.reel / "fill.json"
        write(fill, self.fill)
        result = self.run_check("fill", SID, fill, "--reel", self.reel)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_check("fill", SID, fill)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reel", result.stdout)

    def test_compose_plan_and_world_layer(self):
        inp = self.inputs()
        with patch.object(compose, "saved_brand", return_value={}), contextlib.redirect_stdout(io.StringIO()):
            compose.plan(inp, None)
        self.assertEqual(inp["scened"][0]["scene"]["id"], SID)
        self.assertEqual(compose.scene_params(self.fill, self.reel), self.spec["params"])
        self.assertEqual(compose.build_spans(inp["beats"], {SID: "world"}, 0, reel=self.reel)[0]["layer"], "takeover")
        self.assertEqual(compose.picture_covers(inp["beats"], "25/1", reel=self.reel), [(0, 75, "full-frame scenes")])
        second = dict(self.beat, id="b_002", start_f=75, end_f=150)
        spans = compose.build_spans([self.beat, second], {SID: "world"}, 0, reel=self.reel)
        self.assertEqual(compose.effect_gate.underlay(spans, "25/1"),
                         [{"layer": "underlay", "start_f": 0, "end_f": 150}])

    def test_compose_refuses_before_other_planning(self):
        write(self.scene / "scene.html", HTML.replace("const v =", "Math.random(); const v ="))
        with patch.object(compose, "broll_plan") as broll, self.assertRaises(compose.Stop) as error:
            compose.plan(self.inputs(), None)
        self.assertEqual(len(error.exception.lines), 1)
        self.assertIn(SID, error.exception.lines[0])
        self.assertIn("Math.random", error.exception.lines[0])
        broll.assert_not_called()

    def test_compose_missing_scene_plain_refusal(self):
        inp = self.inputs()
        inp["beats"][0]["scene"]["id"] = "reel-missing"
        with self.assertRaises(compose.Stop) as error:
            compose.plan(inp, None)
        self.assertEqual(len(error.exception.lines), 1)
        self.assertIn("reel-missing", error.exception.lines[0])

    def test_compose_deleted_scene_names_beat_and_requests_motion_rebuild(self):
        inp = self.inputs()
        before = copy.deepcopy(inp["beats"])
        shutil.rmtree(self.scene)
        with patch.object(compose, "broll_plan") as broll, self.assertRaises(compose.Stop) as error:
            compose.plan(inp, None)
        self.assertEqual(list(error.exception.lines), [
            f"The graphic for beat 1 ({SID}) is missing or unavailable. Ask Claude to rebuild the motion."])
        self.assertEqual(inp["beats"], before)
        broll.assert_not_called()

    def test_project_copies_only_verified_referenced_assets(self):
        file = self.asset()
        self.list_asset(hashlib.sha256(file.read_bytes()).hexdigest())
        write(self.motion / "assets/unused.svg", "unused")
        project = self.reel / "project"
        compose.scene_project(project, self.beat, Fraction(25), self.reel)
        self.assertEqual((project / "assets/logo.svg").read_bytes(), file.read_bytes())
        self.assertFalse((project / "assets/unused.svg").exists())
        self.list_asset("0" * 64)
        with self.assertRaises(compose.Stop):
            compose.scene_project(self.reel / "invalid-project", self.beat, Fraction(25), self.reel)

    def test_existing_qa_resolves_world_with_explicit_face_choice(self):
        import overlay_face_check
        rows = overlay_face_check.run({"reel_dir": self.reel, "beats": [self.beat]})
        self.assertEqual([row["check"] for row in rows], ["world-face-exempt"])
        self.assertEqual(rows[0]["level"], "pass")

    def test_caption_coverage_threads_reel(self):
        import placer
        ctx = dict(reel_dir=self.reel, beats=[self.beat], fps=Fraction(25), layouts={},
                   track={"total_f": 75, "keys": [{"f": 0, "layout": "full"}], "tweens": []})
        self.assertEqual(placer.speaker_spans(ctx, 0, 74), [])

    def test_caption_plan_accepts_world_kind(self):
        sys.path.insert(0, str(P / "skills/reel-captions/scripts"))
        import captions
        (self.reel / "work").mkdir(exist_ok=True)
        write(self.reel / captions.SEND, {"beats": [self.beat]})
        write(self.reel / captions.DEFAULT_WORDS, {"words": [
            {"word": word, "start": i * .2, "end": i * .2 + .16}
            for i, word in enumerate("A clear world".split())]})
        write(self.reel / "work/cuts.json", {"fps": 25, "segments": [{"out_in_f": 0, "out_out_f": 75}]})
        doc = captions.plan(self.reel, _style={"style": "clean", "under_small_overlays": False})
        self.assertTrue(doc["chunks"])
        self.assertFalse(doc["declared_drops"])

    def test_compose_lookups_resolve(self):
        source = (P / "skills/reel-canvas-build/scripts/compose.py").read_text(encoding="utf-8")
        production, selftests = source.split("def selftest():", 1)
        self.assertNotIn("scene_check.SCENES /", production)
        self.assertEqual(selftests.count("scene_check.SCENES /"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
