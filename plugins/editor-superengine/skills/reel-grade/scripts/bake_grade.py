"""Bake a grade into one .cube.

    <editor python> -X utf8 -I bake_grade.py <grade-spec.json> -o <out>.cube [--size 33|65]

A grade spec is {"correction": {...}, "stack": [{...}, ...], "look": {"id": "warm", "strength": 0.8}}, every key
optional. correction is a flat dict of grade_math numbers: the pre-pass ones (exposure, black, white, skin_hue,
skin_rot, skin_band) and the slot ones (temp, tint, con, sat, mat) become a pre-pass and one slot. Then each stack
slot, then the look's slots from ../looks/looks.json scaled by strength. An empty spec bakes the identity.

identity lattice -> pre-pass -> each slot in order -> clamp -> .cube. The maths is grade_math.py, which is the same
maths grade_math.js runs on the Grade Board (selftest_math.py proves it). One .cube out, because ffmpeg writes the
pixels: the browser's colour management shifts what the page shows, so the page is where you judge and ffmpeg is
what renders.

Also the home of the .cube reader (parse_cube), the lattice sampler (trilinear) and the grade.json writer
(write_grade) that make_grade.py and grade_match.py share.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import grade_math as gm  # noqa: E402

LOOKS_PATH = HERE.parent / "looks" / "looks.json"
TUNE = ("temp", "tint", "con", "sat", "mat")


def parse_cube(path):
    """-> (size, arr[b, g, r, 3] float64, title). Handles files with and without a TITLE line."""
    size, title, rows = None, "", []
    dmin, dmax = np.zeros(3), np.ones(3)
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        up = s.upper()
        if up.startswith("TITLE"):
            title = s[5:].strip().strip('"')
        elif up.startswith("LUT_3D_SIZE"):
            size = int(s.split()[-1])
        elif up.startswith("DOMAIN_MIN"):
            dmin = np.array([float(x) for x in s.split()[1:4]])
        elif up.startswith("DOMAIN_MAX"):
            dmax = np.array([float(x) for x in s.split()[1:4]])
        elif up.startswith("LUT_1D_SIZE"):
            raise ValueError(f"{Path(path).name}: 1D LUT, only 3D cubes are read")
        else:
            rows.append(s)
    if size is None:
        raise ValueError(f"{Path(path).name}: no LUT_3D_SIZE")
    arr = np.array([[float(x) for x in r.split()[:3]] for r in rows], dtype=np.float64)
    if len(arr) != size ** 3:
        raise ValueError(f"{Path(path).name}: {len(arr)} entries, expected {size ** 3}")
    if not (np.allclose(dmin, 0.0) and np.allclose(dmax, 1.0)):
        arr = (arr - dmin) / np.maximum(dmax - dmin, 1e-9)
    # .cube is red-fastest, so reshaping straight to (b, g, r) puts the axes in memory order
    return size, arr.reshape(size, size, size, 3), title


def trilinear(arr, size, pts):
    """Sample arr[b,g,r,3] at pts (M,3) in [0,1]. Same interpolation the GPU does with GL_LINEAR."""
    x = np.clip(np.asarray(pts, dtype=np.float64).reshape(-1, 3), 0.0, 1.0) * (size - 1)
    i0 = np.clip(np.floor(x).astype(np.int64), 0, size - 2)
    f = x - i0
    r0, g0, b0 = i0[:, 0], i0[:, 1], i0[:, 2]
    fr, fg, fb = f[:, 0:1], f[:, 1:2], f[:, 2:3]
    r1, g1, b1 = r0 + 1, g0 + 1, b0 + 1

    def lerp(a, b, t):
        return a + (b - a) * t
    c00 = lerp(arr[b0, g0, r0], arr[b0, g0, r1], fr)
    c01 = lerp(arr[b0, g1, r0], arr[b0, g1, r1], fr)
    c10 = lerp(arr[b1, g0, r0], arr[b1, g0, r1], fr)
    c11 = lerp(arr[b1, g1, r0], arr[b1, g1, r1], fr)
    return lerp(lerp(c00, c01, fg), lerp(c10, c11, fg), fb)


def through_cube(path, rgb):
    """rgb (..., 3) in [0,1] through a .cube file, same shape out."""
    n, arr, _ = parse_cube(path)
    rgb = np.asarray(rgb, dtype=np.float64)
    return trilinear(arr, n, rgb).reshape(rgb.shape)


def identity_lattice(size):
    """(size**3, 3) in .cube write order - red fastest, then green, then blue."""
    i = np.arange(size ** 3)
    r, g, b = i % size, (i // size) % size, i // (size * size)
    return np.stack([r, g, b], axis=-1).astype(np.float64) / (size - 1)


def load_looks():
    return {lk["id"]: lk for lk in json.loads(LOOKS_PATH.read_text(encoding="utf-8"))["looks"]}


def look_stack(look):
    """{"id", "strength"} -> (slots, neutral). 'none' or strength 0 = no slots. Strength scales tune numbers linearly."""
    look = look or {}
    lid = str(look.get("id") or "none")
    if lid == "none":
        return [], False
    looks = load_looks()
    if lid not in looks:
        raise SystemExit(f"There is no look called {lid!r}. The looks are: none, {', '.join(looks)}.")
    s = float(look.get("strength", 1.0))
    if not 0.0 <= s <= 1.0:
        raise SystemExit(f"Look strength {s:g} is outside 0-1.")
    slots = [{k: float(v) * s for k, v in slot.items() if k in TUNE} for slot in looks[lid]["stack"]]
    return slots, bool(looks[lid].get("neutral"))


def bake(spec, size=33):
    """-> (lattice (size**3, 3), pre-pass used, slot notes)."""
    corr = dict(spec.get("correction") or {})
    pre = gm.defaults(gm.PRE)
    pre.update({k: float(v) for k, v in corr.items() if k in pre})
    first = {k: float(v) for k, v in corr.items() if k in TUNE}
    stack = ([first] if any(first.values()) else []) + list(spec.get("stack") or [])
    look_slots, _ = look_stack(spec.get("look"))
    c = gm.pre_pass(identity_lattice(size), pre)
    used = []
    for i, slot in enumerate(stack + look_slots, 1):
        if slot.get("lut") not in (None, "", "none"):
            raise SystemExit(f"Slot {i} names a LUT file. This editor bakes looks from its own tune numbers only.")
        tune = gm.defaults(gm.SLOT)
        tune.update({k: float(v) for k, v in slot.items() if k in tune})
        c = gm.apply_slot(c, c, tune)          # tune-only slot: the "LUT" is identity, so mix does nothing
        used.append(", ".join(f"{k} {tune[k]:g}" for k in TUNE if tune[k]) or "(identity)")
    return np.clip(c, 0.0, 1.0), pre, used


def write_cube(path, lattice, size, title):
    out = [f'TITLE "{title}"', f"LUT_3D_SIZE {size}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0", ""]
    out += [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in lattice]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(("\n".join(out) + "\n").encode("utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_grade(reel_dir, takes, look, ref=0, size=33, guard=None):
    """Bake one cube per take (its correction + the look); write <reel_dir>/grade.json only if every cube passes.

    takes: [{"range": [a, b], "measured": {...}, "correction": {...}}]. The top-level cube is the reference take's:
    one cut is one take, so that is the cube for the whole cut. guard(take_index, cube_path) returns None when the
    cube is fine, else a plain refusal line. -> (grade.json dict or None, [refusal lines]).
    """
    reel_dir = Path(reel_dir)
    look = {"id": str((look or {}).get("id") or "none"), "strength": float((look or {}).get("strength", 1.0))}
    out = []
    for i, tk in enumerate(takes, 1):
        rel = f"grade/take-{i}.cube"
        lat, _, _ = bake({"correction": tk["correction"], "look": look}, size)
        write_cube(reel_dir / rel, lat, size, f"take {i} grade, look {look['id']}")
        out.append(dict(tk, cube=rel, cube_sha=sha256(reel_dir / rel)))
    problems = [m for m in (guard(i, reel_dir / tk["cube"]) for i, tk in enumerate(out)) if m] if guard else []
    if problems:
        return None, problems
    doc = {"takes": out, "look": look, "cube": out[ref]["cube"], "cube_sha": out[ref]["cube_sha"]}
    (reel_dir / "grade.json").write_bytes((json.dumps(doc, indent=1) + "\n").encode("utf-8"))
    return doc, []


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Bake a grade spec into one .cube")
    ap.add_argument("spec", help="grade spec json: correction, stack, look (all optional)")
    ap.add_argument("-o", "--out", required=True, help="output .cube")
    ap.add_argument("--size", type=int, default=33, choices=[33, 65],
                    help="bake lattice; 65 if a deep stack shows banding")
    a = ap.parse_args()
    t0 = time.time()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    lat, pre, used = bake(spec, a.size)
    write_cube(a.out, lat, a.size, f"grade - {len(used)} slot(s)")
    print(f"{a.size}^3 lattice ({a.size ** 3} entries) in {time.time() - t0:.2f}s -> {a.out}")
    print("  pre-pass: " + ", ".join(f"{k} {v:g}" for k, v in pre.items()))
    for i, u in enumerate(used, 1):
        print(f"  slot {i}: {u}")
    if not used:
        print("  no slots - this cube is the pre-pass alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
