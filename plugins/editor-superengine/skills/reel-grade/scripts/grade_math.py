"""The grade tune maths, Python side. Every constant comes from ../boards/grade-board/grade_math.json.

The bake runs through this file; the Grade Board page runs through grade_math.js beside that json;
selftest_math.py proves the two agree. Do not put a number in here - put it in grade_math.json.

Vectorised on purpose: bake_grade.py pushes a 33**3 (or 65**3) lattice through the same calls the
selftest sends three floats through, so there is one code path, not a fast one and a careful one.

    <editor python> -X utf8 -I grade_math.py      # self-check: defaults are identity
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE.parent / "boards" / "grade-board" / "grade_math.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
K = SPEC["constants"]
RANGES = SPEC["ranges"]
PRE = SPEC["pre_pass"]["params"]
SLOT = SPEC["slot"]["params"]
LUMA = np.array([K["luma_r"], K["luma_g"], K["luma_b"]], dtype=np.float64)


def defaults(names) -> dict:
    """Slider defaults straight out of the ranges table (the [min,max,step,default] 4th slot)."""
    return {n: float(RANGES[n][3]) for n in names}


def _wrap360(h):
    return h - 360.0 * np.floor(h / 360.0)


def _wrap180(d):
    return d - 360.0 * np.floor((d + 180.0) / 360.0)


def rgb_to_hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    d = mx - mn
    v = mx
    s = np.where(mx > 0.0, d / np.where(mx > 0.0, mx, 1.0), 0.0)
    safe = np.where(d > 0.0, d, 1.0)
    # branch order is r, then g, then b - grade_math.js uses the same if/else-if chain
    h = np.where(mx == r, 60.0 * ((g - b) / safe),
        np.where(mx == g, 60.0 * ((b - r) / safe + 2.0),
                          60.0 * ((r - g) / safe + 4.0)))
    h = np.where(d > 0.0, h, 0.0)
    h = np.where(h < 0.0, h + 360.0, h)
    return h, s, v


def hsv_to_rgb(h, s, v):
    c = v * s
    hh = h / 60.0
    hh = hh - 6.0 * np.floor(hh / 6.0)
    x = c * (1.0 - np.abs(hh - 2.0 * np.floor(hh / 2.0) - 1.0))
    m = v - c
    z = np.zeros_like(c)
    i = np.clip(np.floor(hh), 0.0, 5.0)
    sel = [i == 0.0, i == 1.0, i == 2.0, i == 3.0, i == 4.0, i == 5.0]
    r = np.select(sel, [c, x, z, z, x, c])
    g = np.select(sel, [x, c, c, x, z, z])
    b = np.select(sel, [z, z, x, c, c, x])
    return np.stack([r + m, g + m, b + m], axis=-1)


def pre_pass(c, p):
    """Exposure -> levels -> clamp -> hue-selective skin rotation -> clamp."""
    c = np.asarray(c, dtype=np.float64)
    c = c * (2.0 ** float(p["exposure"]))
    black, white = float(p["black"]), float(p["white"])
    c = (c - black) / max(white - black, K["levels_eps"])
    c = np.clip(c, 0.0, 1.0)
    h, s, v = rgb_to_hsv(c)
    d = _wrap180(h - float(p["skin_hue"]))
    t = np.minimum(np.abs(d) / max(float(p["skin_band"]), 1e-6), 1.0)
    w = 1.0 - t * t * (3.0 - 2.0 * t)
    h = _wrap360(h + float(p["skin_rot"]) * w)
    c = hsv_to_rgb(h, s, v)
    return np.clip(c, 0.0, 1.0)


def slot_tune(c, t):
    """temp -> tint -> contrast -> saturation -> matte -> clamp. Takes the already-mixed colour."""
    c = np.asarray(c, dtype=np.float64)
    temp, tint = float(t.get("temp", 0.0)), float(t.get("tint", 0.0))
    con, sat, mat = float(t.get("con", 0.0)), float(t.get("sat", 0.0)), float(t.get("mat", 0.0))
    c = c + np.array([temp * K["temp_r"], 0.0, -temp * K["temp_b"]])
    c = c + np.array([-tint * K["tint_rb"], tint * K["tint_g"], -tint * K["tint_rb"]])
    piv = K["contrast_pivot"]
    c = (c - piv) * (1.0 + con * K["contrast_gain"]) + piv
    l = (c * LUMA).sum(axis=-1, keepdims=True)
    c = l + (c - l) * (1.0 + sat * K["sat_gain"])
    m = mat * K["matte_max"]
    c = c * (1.0 - m) + m
    return np.clip(c, 0.0, 1.0)


def apply_slot(c, lut_rgb, t):
    """mix (lerp identity -> LUT) then the tune."""
    c = np.asarray(c, dtype=np.float64)
    lut_rgb = np.asarray(lut_rgb, dtype=np.float64)
    mix = float(t.get("mix", 1.0))
    return slot_tune(c + (lut_rgb - c) * mix, t)


def main():
    sys.path.insert(0, str(HERE.parents[1] / "_shared"))
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    # smallest check that fails if the maths breaks: identity in, identity out.
    ident = np.array([[0.0, 0.0, 0.0], [0.25, 0.5, 0.75], [1.0, 1.0, 1.0], [0.3, 0.3, 0.3]])
    p = defaults(PRE)
    assert np.abs(pre_pass(ident, p) - ident).max() < 1e-12, "pre-pass defaults are not identity"
    t = defaults(SLOT)
    assert np.abs(apply_slot(ident, ident, t) - ident).max() < 1e-12, "slot defaults are not identity"
    assert np.abs(apply_slot(ident, 1.0 - ident, dict(t, mix=1.0)) - (1.0 - ident)).max() < 1e-12
    print("grade_math.py ok - defaults are identity, mix=1 is the LUT")


if __name__ == "__main__":
    main()
