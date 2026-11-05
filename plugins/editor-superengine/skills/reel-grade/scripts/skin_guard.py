"""Skin guard: refuse a grade that changes how skin looks too much.

    <editor python> -X utf8 -I skin_guard.py --face <frame.jpg> <grade>.cube [<grade>.cube ...] [--neutral]

The skin colour is measured, not assumed: the dominant saturated hue in the upper-centre of the frame (where the
face sits in a talking-head shot), then the median RGB of the pixels near that hue. A fixed 0-50 deg "skin band" is
wrong for cool-lit cameras, where raw skin can read near 330 deg. That colour goes through each cube (the same
trilinear sampling the bake uses), and in CIE Lab:
  - its hue may move at most HUE_MAX_DEG,
  - its chroma (colourfulness) must keep at least CHROMA_FLOOR of what it had,
  - for a neutral look (looks.json "neutral": true, e.g. Mono) only its brightness is checked: L* may move at most
    LIGHTNESS_MAX_NEUTRAL, because removing colour is the point of that look.
grade_match.py also calls check() with ref_out, to compare a matched take's skin with the reference take's.
Exit 0 = every cube passes; exit 1 = refused, with one plain line per refused cube.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import grade_math as gm  # noqa: E402
from bake_grade import through_cube  # noqa: E402

# Thresholds, tuned 11.05.26 on the test fixture: a 10 s talking-head excerpt (one presenter, warm skin under a
# cool-lit set, 640 px wide), skin measured on make_grade's face frame, each look at strength 1.
# Measured (hue shift deg / chroma kept / L* move):
#   Natural 0.02 / 1.12 / 0.18 · Warm 2.66 / 1.26 / 0.70 · Punchy 0.01 / 1.38 / 0.58 · Soft matte 0.16 / 0.76 / 2.90
#   Mono (neutral, brightness only) L* move 2.44 · a planted 25 deg skin rotation 38.58 / 1.03 / 7.34 (must refuse)
#   grade_match on a take pushed +0.3 stop and warm: matched skin within 0.66 deg (face dE 1.62) of the reference take.
# Limits: hue 6 deg is over 2x the warmest look and far under the planted turn; the chroma floor 0.6 sits under Soft
# matte's 0.76; the neutral L* limit 8 is 3x Mono's move.
HUE_MAX_DEG = 6.0
CHROMA_FLOOR = 0.6
LIGHTNESS_MAX_NEUTRAL = 8.0

SAT_FLOOR = 0.12         # below this a pixel has no usable hue (grey wall, black shirt)
HUE_WIN = 20.0           # refine the dominant hue inside this window of the histogram peak
MASK_WIN = 25.0          # skin mask half-width around the dominant hue
REGION = (0.12, 0.60, 0.30, 0.70)   # rows top..bottom, cols left..right: the upper-centre, where a face sits
DARK_FLOOR = 0.6         # skin pixels must be at least this fraction of the mask's median brightness
BLOB_DENSITY = 0.5      # a block (1/80 of the width) counts toward the face blob when half its pixels read as skin


def _region(img):
    h, w, _ = img.shape
    return img[int(REGION[0] * h):int(REGION[1] * h), int(REGION[2] * w):int(REGION[3] * w)]


def dominant_hue(img):
    """Dominant saturated hue in the upper-centre region -> (hue deg, sat) or None."""
    hh, ss, vv = gm.rgb_to_hsv(_region(img))
    ok = (ss >= SAT_FLOOR) & (vv > 0.10) & (vv < 0.98)
    if ok.sum() < 200:
        return None
    hs, sats = hh[ok], ss[ok]
    # 5 deg bins, box-smoothed circularly so the pick is a lobe and not one spiky bin
    counts = np.bincount((hs / 5.0).astype(int) % 72, minlength=72).astype(np.float64)
    sm = counts + np.roll(counts, 1) + np.roll(counts, -1)
    peak = float(np.argmax(sm)) * 5.0 + 2.5
    d = hs - peak
    d = d - 360.0 * np.floor((d + 180.0) / 360.0)
    near = np.abs(d) <= HUE_WIN
    if near.sum() < 100:
        return float(peak % 360.0), float(np.median(sats))
    return (peak + float(np.median(d[near]))) % 360.0, float(np.median(sats[near]))


def _largest_blob(m):
    """Keep only the largest 4-connected group of dense blocks: the face, not scattered warm bits of the set."""
    h, w = m.shape
    bs = max(4, w // 80)
    bh, bw = h // bs, w // bs
    dense = m[:bh * bs, :bw * bs].reshape(bh, bs, bw, bs).mean((1, 3)) >= BLOB_DENSITY
    lab = np.zeros(dense.shape, np.int32)
    best, best_n, n = 0, 0, 0
    for y, x in zip(*np.nonzero(dense)):
        if lab[y, x]:
            continue
        n += 1
        lab[y, x], todo, cnt = n, [(y, x)], 0
        while todo:
            cy, cx = todo.pop()
            cnt += 1
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < bh and 0 <= nx < bw and dense[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    todo.append((ny, nx))
        if cnt > best_n:
            best, best_n = n, cnt
    keep = np.zeros(m.shape, bool)
    if best:
        keep[:bh * bs, :bw * bs] = np.repeat(np.repeat(lab == best, bs, 0), bs, 1)
    return m & keep


def skin_mask(img, hue):
    """Pixels near the skin hue with usable saturation and brightness, in the face region's largest blob."""
    hh, ss, vv = gm.rgb_to_hsv(img)
    d = hh - hue
    d = d - 360.0 * np.floor((d + 180.0) / 360.0)
    m = (np.abs(d) <= MASK_WIN) & (ss >= SAT_FLOOR) & (ss <= 0.75) & (vv >= 0.12) & (vv <= 0.97)
    keep = np.zeros(m.shape, bool)
    h, w = m.shape
    keep[int(REGION[0] * h):int(REGION[1] * h), int(REGION[2] * w):int(REGION[3] * w)] = True
    m &= keep
    if m.any():
        # dark pixels (chair, hair, beard) carry no reliable hue: a floor relative to the face's own brightness drops
        # them and moves with the exposure, so a brighter take is masked on the same kind of pixels
        m &= vv >= DARK_FLOOR * float(np.median(vv[m]))
    return _largest_blob(m)


def face_pixels(imgs):
    """Skin pixels (N, 3) of one or more frames, each frame masked at its own dominant hue. None if no face."""
    px = []
    for img in imgs:
        dh = dominant_hue(img)
        if dh is not None:
            px.append(img[skin_mask(img, dh[0])])
    px = np.concatenate(px) if px else np.zeros((0, 3))
    return px if len(px) >= 200 else None


def skin_rgb(imgs):
    """The measured skin colour: median RGB of the face mask. None if no face was found."""
    px = face_pixels(imgs)
    return None if px is None else np.median(px, axis=0)


# ---------- sRGB <-> CIE Lab (D65) ----------
_M = np.array([[0.4124564, 0.3575761, 0.1804375],
               [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]])
_MI = np.linalg.inv(_M)
_WP = np.array([0.95047, 1.0, 1.08883])
_D = 6.0 / 29.0


def rgb_to_lab(rgb):
    c = np.asarray(rgb, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    t = lin @ _M.T / _WP
    f = np.where(t > _D ** 3, np.cbrt(t), t / (3 * _D * _D) + 4.0 / 29.0)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_rgb(lab):
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    xyz = np.where(f > _D, f ** 3, 3 * _D * _D * (f - 4.0 / 29.0)) * _WP
    lin = np.clip(xyz @ _MI.T, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def lch(rgb):
    lab = rgb_to_lab(rgb)
    return float(lab[0]), float(np.hypot(lab[1], lab[2])), float(np.degrees(np.arctan2(lab[2], lab[1])) % 360.0)


def check(skin_in, cube, neutral=False, ref_out=None):
    """-> (ok, numbers, plain message). The skin through the cube vs its own colour (or vs ref_out, for a match)."""
    out = through_cube(cube, np.asarray(skin_in, dtype=np.float64))
    L0, C0, h0 = lch(skin_in if ref_out is None else ref_out)
    L1, C1, h1 = lch(out)
    dh = abs((h1 - h0 + 180.0) % 360.0 - 180.0)
    kept = C1 / max(C0, 1e-6)
    nums = {"hue_shift_deg": round(dh, 2), "chroma_kept": round(kept, 3), "lightness_move": round(abs(L1 - L0), 2)}
    problems = []
    if neutral:
        if abs(L1 - L0) > LIGHTNESS_MAX_NEUTRAL:
            problems.append(f"changes skin brightness by {abs(L1 - L0):.1f} (the limit is {LIGHTNESS_MAX_NEUTRAL:g})")
    else:
        if dh > HUE_MAX_DEG:
            problems.append(f"turns skin {dh:.1f}° away from its colour (the limit is {HUE_MAX_DEG:g}°)")
        if kept < CHROMA_FLOOR:
            problems.append(f"drains skin to {kept:.0%} of its colour (the floor is {CHROMA_FLOOR:.0%})")
    ok = not problems
    msg = "ok" if ok else "Refused: this grade " + " and ".join(problems) + ". Pick another look or lower its strength."
    return ok, nums, msg


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Refuse a grade that moves skin too far")
    ap.add_argument("cubes", nargs="+")
    ap.add_argument("--face", required=True, help="a frame with the face in it (jpg/png)")
    ap.add_argument("--neutral", action="store_true", help="a look that removes colour on purpose: check brightness only")
    a = ap.parse_args()
    from PIL import Image
    img = np.asarray(Image.open(a.face).convert("RGB"), dtype=np.float64) / 255.0
    skin = skin_rgb([img])
    if skin is None:
        print("No face found in the upper-centre of that frame, so the skin can't be checked. Pick a frame with the face in it.")
        return 1
    print(f"skin colour (median RGB of the face mask): {tuple(int(round(x * 255)) for x in skin)}")
    bad = 0
    for c in a.cubes:
        ok, nums, msg = check(skin, c, a.neutral)
        bad += not ok
        print(f"{'✓' if ok else '✗'} {Path(c).name}: {msg} {nums}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
