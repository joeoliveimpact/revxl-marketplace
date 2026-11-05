"""Match the takes inside one video so the skin and light look the same from take to take.

    <editor python> -X utf8 -I grade_match.py --video <raw .mp4> --reel-dir <videos/<reel>> \
        --take 0-41.5 --take 41.5-88 [--ref 1] [--look <id> --strength <0-1>]

A take here is a time range inside ONE file (seconds, a-b). Separate recordings are separate cuts (the Cut Board
never mixes takes), so with one take, or no --take at all, there is nothing to match: it says so and exits 0.

Each take is measured once over its whole length: FRAMES evenly spaced frames across the range. The face is the
dominant-hue skin mask (skin_guard.py). The skin pixels' CIE Lab mean and spread are fitted toward the reference
take's (a Reinhard transfer, the spread gain capped at GAIN_CAP so contrast never explodes). Then exposure, temp and
tint, and after them con and sat, are solved by coordinate descent through grade_math, so each take gets ordinary tune numbers
and the normal bake makes one cube per take. The skin guard checks each take's cube against the reference take's
skin; a refusal writes nothing. Writes <reel-dir>/grade.json (keeping its look unless --look is given).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import grade_math as gm  # noqa: E402
import bake_grade as bg  # noqa: E402
import skin_guard as sg  # noqa: E402
from apply_grade import duration, read_frame  # noqa: E402

FRAMES = 6            # frames per take, spread evenly over the whole range
MEASURE_W = 640       # measured at this width at most
MAX_PX = 6000         # skin pixels per take the solver works on (an even stride through the mask)
GAIN_CAP = 1.6        # Reinhard spread gain is held inside [1/1.6, 1.6]
BALANCE = ("exposure", "temp", "tint")   # solved first: these carry a lighting change
SPREAD = ("con", "sat")                  # then these, on the settled mask (solving all five at once lets con/sat
SOLVE = BALANCE + SPREAD                 # trade against temp and lands on a wrong skin colour with a right mean)
ROUNDS = 3            # re-mask and re-solve rounds per take


def parse_take(s):
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*", s)
    if not m or float(m.group(1)) >= float(m.group(2)):
        raise SystemExit(f"--take {s!r}: write it as start-end in seconds, e.g. 0-41.5")
    return float(m.group(1)), float(m.group(2))


def grade_px(px, p):
    pre = gm.defaults(gm.PRE)
    pre["exposure"] = p["exposure"]
    return gm.slot_tune(gm.pre_pass(px, pre), {k: p[k] for k in SOLVE[1:]})


def measure(imgs, p):
    """Skin pixels of a take's frames (original values), masked on the frames as graded by p. None if no face."""
    px = []
    for img in imgs:
        g = grade_px(img, p) if any(p.values()) else img
        dh = sg.dominant_hue(g)
        if dh is not None:
            px.append(img[sg.skin_mask(g, dh[0])])
    px = np.concatenate(px) if px else np.zeros((0, 3))
    if len(px) < 200:
        return None
    px = px[::max(1, len(px) // MAX_PX)][:MAX_PX]
    lab = sg.rgb_to_lab(px)
    return dict(px=px, lab=lab, mean=lab.mean(0), std=lab.std(0) + 1e-6, skin=np.median(px, 0))


def solve(px, target, start, keys):
    """Coordinate descent on the keys' tune numbers: graded skin pixels -> as close as possible to the target Lab."""
    def loss(p):
        return float(((sg.rgb_to_lab(grade_px(px, p)) - target) ** 2).sum(-1).mean())
    p = dict(start)
    best, step, evals = loss(p), 0.08, 0
    while step >= 0.005 and evals < 600:
        moved = False
        for k in keys:
            lo, hi = gm.RANGES[k][0], gm.RANGES[k][1]
            for d in (step, -step):
                q = dict(p, **{k: min(hi, max(lo, p[k] + d))})
                lq = loss(q)
                evals += 1
                if lq < best - 1e-9:
                    p, best, moved = q, lq, True
                    break
        if not moved:
            step /= 2.0
    return {k: round(v, 3) for k, v in p.items()}


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Match the takes inside one video")
    ap.add_argument("--video", required=True)
    ap.add_argument("--reel-dir", required=True, help="videos/<reel>")
    ap.add_argument("--take", action="append", default=[], help="start-end seconds; give one per take")
    ap.add_argument("--ref", type=int, default=1, help="the take the others match (1 = the first)")
    ap.add_argument("--look", default=None)
    ap.add_argument("--strength", type=float, default=1.0)
    a = ap.parse_args()

    takes = [parse_take(s) for s in a.take]
    if len(takes) < 2:
        print("Nothing to match: this video has one take.")
        return 0
    video, reel_dir = Path(a.video).resolve(), Path(a.reel_dir).resolve()
    if not video.is_file():
        print(f"There's no video at {video}.")
        return 1
    dur = duration(video)
    for t0, t1 in takes:
        if t1 > dur + 0.05:
            print(f"Take {t0:g}-{t1:g} runs past the end of the video ({dur:.2f}s).")
            return 1
    if not 1 <= a.ref <= len(takes):
        print(f"--ref {a.ref}: there are {len(takes)} takes.")
        return 1
    ref = a.ref - 1
    gj = reel_dir / "grade.json"
    look = {"id": a.look, "strength": a.strength} if a.look else (
        json.loads(gj.read_text(encoding="utf-8")).get("look") if gj.is_file() else None) or {"id": "none"}
    _, neutral = bg.look_stack(look)

    frames, meas = [], []
    for i, (t0, t1) in enumerate(takes, 1):
        imgs = [read_frame(video, t0 + (j + 0.5) * (t1 - t0) / FRAMES, MEASURE_W) for j in range(FRAMES)]
        frames.append(imgs)
        m = measure(imgs, dict.fromkeys(SOLVE, 0.0))
        if m is None:
            print(f"No face found in take {i} ({t0:g}-{t1:g}s), so it can't be matched.")
            return 1
        meas.append(m)

    mr, sr = meas[ref]["mean"], meas[ref]["std"]
    out = []
    for i, (t0, t1) in enumerate(takes):
        params = dict.fromkeys(SOLVE, 0.0)
        if i != ref:
            # the mask is re-found on the graded frames each round, so both takes are measured on the same kind of
            # pixels (a lighting change moves which pixels read as skin; the first round alone mis-picks them).
            # Balance first (exposure, temp, tint), then the spread (con, sat) on the settled mask.
            for keys in [BALANCE] * ROUNDS + [SPREAD]:
                m = measure(frames[i], params)
                if m is None:
                    print(f"No face found in take {i + 1} ({t0:g}-{t1:g}s), so it can't be matched.")
                    return 1
                target = (m["lab"] - m["mean"]) * np.clip(sr / m["std"], 1 / GAIN_CAP, GAIN_CAP) + mr
                params = solve(m["px"], target, params, keys)
            meas[i] = m
        m = meas[i]
        corr = gm.defaults(gm.PRE)
        corr.update(params)
        out.append(dict(range=[t0, t1], measured=dict(frames=FRAMES, skin_rgb=[round(float(x), 4) for x in m["skin"]],
                                                      lab_mean=[round(float(x), 2) for x in m["mean"]],
                                                      lab_std=[round(float(x), 2) for x in m["std"]]),
                        correction=corr))
        print(f"take {i + 1} {t0:g}-{t1:g}s: " + ("reference" if i == ref else
              ", ".join(f"{k} {v:+.3f}" for k, v in params.items())))

    ref_skin = meas[ref]["skin"]

    def guard(i, cube):
        if i == ref:
            ok, _, msg = sg.check(ref_skin, cube, neutral)
        else:
            ref_out = bg.through_cube(reel_dir / "grade" / f"take-{ref + 1}.cube", ref_skin)
            ok, _, msg = sg.check(meas[i]["skin"], cube, neutral, ref_out=ref_out)
        return None if ok else f"Take {i + 1}: {msg}"
    doc, problems = bg.write_grade(reel_dir, out, look, ref=ref, guard=guard)
    if problems:
        print("\n".join(problems) + " (grade.json was not written)")
        return 1
    print(f"-> {gj} ({len(out)} takes, reference take {a.ref}, look {doc['look']['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
