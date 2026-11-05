"""Prove grade_math.py and grade_math.js are the same maths.

200 random colours (plus 4 corners) through random pre-pass + slot parameters, in Python and in the
editor's own node, asserting a max absolute difference under 1e-5. Two implementations of one maths
is how a grade board fails silently: you judge one thing on the page and ship another out of the bake.
Run it after ANY edit to grade_math.json, grade_math.py or grade_math.js.

    <editor python> -X utf8 -I selftest_math.py

Exit 0 = the page and the bake agree; exit 1 = they diverged (fix the maths, never the threshold).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import grade_math as gm  # noqa: E402

BOARD = HERE.parent / "boards" / "grade-board"
TOL = 1e-5
N = 200

DRIVER = """
const GM = require('{js}');
GM.init(require('{json}'));
const cases = JSON.parse(require('fs').readFileSync('{inp}', 'utf8'));
const out = cases.map(c => GM.applySlot(GM.prePass(c.rgb, c.pre), c.lut, c.tune));
require('fs').writeFileSync('{out}', JSON.stringify(out));
"""


def random_cases(n, seed=20260909):
    r = np.random.default_rng(seed)

    def draw(name):
        lo, hi = gm.RANGES[name][0], gm.RANGES[name][1]
        return float(r.uniform(lo, hi))
    cases = []
    for _ in range(n):
        cases.append(dict(rgb=[float(x) for x in r.random(3)], lut=[float(x) for x in r.random(3)],
                          pre={k: draw(k) for k in gm.PRE}, tune={k: draw(k) for k in gm.SLOT}))
    # pin the corners too: pure black, pure white, mid grey, a saturated skin-ish red
    for rgb in ([0, 0, 0], [1, 1, 1], [0.5, 0.5, 0.5], [0.62, 0.36, 0.33]):
        cases.append(dict(rgb=[float(x) for x in rgb], lut=[float(x) for x in rgb],
                          pre=gm.defaults(gm.PRE), tune=gm.defaults(gm.SLOT)))
    return cases


def py_side(cases):
    out = [gm.apply_slot(gm.pre_pass(np.array(c["rgb"]), c["pre"]), np.array(c["lut"]), c["tune"]) for c in cases]
    return np.array(out, dtype=np.float64)


def js_side(cases):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inp, outp = td / "cases.json", td / "out.json"
        inp.write_text(json.dumps(cases), encoding="utf-8")
        src = DRIVER.format(js=(BOARD / "grade_math.js").as_posix(), json=(BOARD / "grade_math.json").as_posix(),
                            inp=inp.as_posix(), out=outp.as_posix())
        p = subprocess.run([rt.tool("node"), "-e", src], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
        if p.returncode != 0:
            print(p.stdout, p.stderr, file=sys.stderr)
            raise SystemExit("The editor's node could not run grade_math.js. Ask Claude to check your editor.")
        return np.array(json.loads(outp.read_text(encoding="utf-8")), dtype=np.float64)


def main():
    ensure_utf8_output()
    cases = random_cases(N)
    a, b = py_side(cases), js_side(cases)
    if a.shape != b.shape:
        print(f"MATHS DIVERGED: shape {a.shape} vs {b.shape}")
        return 1
    diff = np.abs(a - b)
    worst = int(diff.max(axis=1).argmax())
    print(f"{len(cases)} colours (200 random + 4 corners) | max abs diff {diff.max():.3e} "
          f"| mean {diff.mean():.3e} | tolerance {TOL:.0e}")
    print(f"worst case #{worst}: py {a[worst].round(8).tolist()} js {b[worst].round(8).tolist()}")
    # defaults must be identity, or the whole board starts already graded
    ident = np.array([[0.0, 0.0, 0.0], [0.3, 0.55, 0.8], [1.0, 1.0, 1.0]])
    if np.abs(gm.apply_slot(gm.pre_pass(ident, gm.defaults(gm.PRE)), ident, gm.defaults(gm.SLOT)) - ident).max() >= 1e-12:
        print("MATHS BROKEN: the defaults are not identity")
        return 1
    if not diff.max() < TOL:
        print(f"MATHS DIVERGED: {diff.max():.3e} >= {TOL:.0e} - fix the maths, never the threshold")
        return 1
    print("PASS - the page and the bake are the same maths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
