#!/usr/bin/env python3
"""MB4 wording and routing checks, without rendering or a browser."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins/editor-superengine"
CANVAS = "skills/reel-canvas-build/"
TOUCHED = (
    "README.md",
    CANVAS + "SKILL.md",
    CANVAS + "references/beat-map.md",
    CANVAS + "references/design-loop.md",
    CANVAS + "references/build.md",
    CANVAS + "references/eye-test-extras.md",
    CANVAS + "boards/sketches/index.html",
    "skills/editor-start-here/SKILL.md",
    "skills/editor-start-here/references/whats-next.md",
)


def wording_problems(files):
    problems = []
    for name, text in files.items():
        folded = " ".join(text.casefold().split())
        phrases = ["final for the motion work", "these choices do not animate anything"]
        phrases.append("lock each beat's motion")
        if name in TOUCHED:
            phrases.append("co" + "ach")
        for phrase in phrases:
            if phrase in folded:
                problems.append(f"{name}: forbidden wording {phrase!r}")
    return problems


class MotionWordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {}
        for path in PLUGIN.rglob("*"):
            if path.is_file():
                try:
                    cls.files[path.relative_to(PLUGIN).as_posix()] = path.read_bytes().decode("utf-8")
                except UnicodeDecodeError:
                    pass  # Binary assets contain no user-facing wording.

    def test_motion_references_exist_and_share_a_routing_row(self):
        skill = self.files[CANVAS + "SKILL.md"]
        rows = [line for line in skill.splitlines() if line.startswith("|")]
        for name in ("motion-build.md", "motion-bar.md"):
            self.assertIn(CANVAS + "references/" + name, self.files)
        self.assertTrue(any("Build the motion from the locked look" in row
                            and "references/motion-build.md" in row
                            and "motion-bar.md" in row
                            and row.index("motion-build.md") < row.index("motion-bar.md")
                            for row in rows), "Missing motion build/bar routing row")

    def test_forbidden_wording_absent(self):
        self.assertEqual(wording_problems(self.files), [])

    def test_sketches_board_names_motion_review(self):
        self.assertIn("motion review", self.files[CANVAS + "boards/sketches/index.html"].casefold())

    def test_sketches_send_routes_to_build_motion(self):
        text = self.files["skills/editor-start-here/references/whats-next.md"]
        row = next(line for line in text.splitlines() if line.startswith("| Sketches |"))
        self.assertEqual(row.split("|")[3].strip(), "reel-canvas-build")
        handoff = text[text.index("**Lock this look is the go-ahead**"):]
        self.assertIn("Build motion", handoff)
        self.assertIn("motion-build.md", handoff)
        self.assertIn("locked_at", handoff)
        self.assertIn("a Sketches Send alone does not authorize Build motion", handoff)

    def test_skill_map_budget_and_lf(self):
        words = len(self.files[CANVAS + "SKILL.md"].split())
        self.assertLessEqual(words * 1.33, 3500)
        for name in TOUCHED:
            with self.subTest(file=name):
                self.assertNotIn("\r", self.files[name])
        self.assertNotIn(b"\r", Path(__file__).read_bytes())

    def test_reintroduced_stale_phrase_fails_in_memory(self):
        name = CANVAS + "references/beat-map.md"
        mutant = dict(self.files)
        mutant[name] += "\nFINAL for the motion work\n"
        self.assertIn(f"{name}: forbidden wording 'final for the motion work'",
                      wording_problems(mutant))
        self.assertNotEqual(mutant[name], self.files[name])


if __name__ == "__main__":
    unittest.main(verbosity=2)
