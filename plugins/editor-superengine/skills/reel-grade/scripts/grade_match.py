"""Match takes across recordings so the skin and light look the same from take to take.

    <editor python> -X utf8 -I grade_match.py --video <raw .mp4> --reel-dir <videos/<reel>> \
        --take 0-41.5 --take 41.5-88 [--ref 1] [--look <id> --strength <0-1>]

A take is start-end seconds in --video, or file::start-end. --from-cuts <reel_dir> groups that reel's kept ranges
by recording number. Explicit file takes use recording numbers from work/cuts.json when it has takes; without
cuts.json takes, they use argument order. With fewer than two takes there is nothing to match: it says so and exits 0.

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
import os
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


def cut_takes(reel_dir):
    """One measurement and cube per used recording, over its kept source ranges only."""
    cuts = json.loads((reel_dir / "work/cuts.json").read_text(encoding="utf-8"))
    fps = float(cuts["fps"])
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("cuts.json needs a positive frame rate.")
    takes = []
    for n in sorted(cuts["takes"], key=int):
        ranges = [(s["src_in_f"] / fps, s["src_out_f"] / fps) for s in cuts["segments"]
                  if str(s.get("take", 1)) == n]
        if not ranges:
            continue
        if any(not (np.isfinite(t0) and np.isfinite(t1) and 0 <= t0 < t1) for t0, t1 in ranges):
            raise ValueError(f"Take {n} has an invalid kept range in cuts.json.")
        raw = Path(cuts["takes"][n]["raw"])
        raw = raw if raw.is_absolute() else reel_dir / raw
        takes.append(dict(id=n, raw=raw.resolve(), ranges=ranges))
    return takes


def sample_times(ranges):
    """Keep the six-frame cap, sampling evenly across the cumulative kept duration."""
    total = sum(t1 - t0 for t0, t1 in ranges)
    for j in range(FRAMES):
        offset = (j + 0.5) * total / FRAMES
        for t0, t1 in ranges:
            if offset < t1 - t0:
                yield t0 + offset
                break
            offset -= t1 - t0


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
    ap = argparse.ArgumentParser(description="Match takes inside or across recordings")
    ap.add_argument("--video", help="default recording for a bare start-end take")
    ap.add_argument("--reel-dir", help="videos/<reel>; defaults to --from-cuts")
    source = ap.add_mutually_exclusive_group()
    source.add_argument("--take", action="append", default=[], help="start-end or file::start-end; one per take")
    source.add_argument("--from-cuts", help="reel folder whose work/cuts.json supplies recordings and kept ranges")
    ap.add_argument("--ref", type=int, default=1, help="the take the others match (1 = the first)")
    ap.add_argument("--look", default=None)
    ap.add_argument("--strength", type=float, default=1.0)
    a = ap.parse_args()

    if not (a.reel_dir or a.from_cuts):
        ap.error("give --reel-dir, or use --from-cuts <reel_dir>")
    reel_dir = Path(a.reel_dir or a.from_cuts).resolve()
    mapped = bool(a.from_cuts or any("::" in s for s in a.take))
    try:
        if a.from_cuts:
            takes = cut_takes(Path(a.from_cuts).resolve())
        else:
            recording_ids = {}
            cuts_path = reel_dir / "work/cuts.json"
            if mapped and cuts_path.is_file():
                recordings = json.loads(cuts_path.read_text(encoding="utf-8")).get("takes") or {}
                for n, recording in recordings.items():
                    raw = Path(recording["raw"])
                    raw = raw if raw.is_absolute() else reel_dir / raw
                    recording_ids[os.path.normcase(str(raw.resolve()))] = str(n)
            takes = []
            for i, s in enumerate(a.take, 1):
                raw, span = s.rsplit("::", 1) if "::" in s else (a.video, s)
                if not raw:
                    ap.error("a bare --take start-end needs --video <file>")
                raw = Path(raw).resolve()
                take_id = str(i)
                if recording_ids:
                    key = os.path.normcase(str(raw))
                    if key not in recording_ids:
                        raise ValueError(f"This recording is not part of this reel: {raw.name}.")
                    take_id = recording_ids[key]
                    if any(tk["id"] == take_id for tk in takes):
                        print("Two of these takes come from the same recording; match takes from different "
                              "recordings, or match inside that recording on its own.")
                        return 1
                takes.append(dict(id=take_id, raw=raw, ranges=[parse_take(span)]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("The take list could not be read: " + str(error).splitlines()[0])
        return 1
    if len(takes) < 2:
        print("Nothing to match: this video has one take.")
        return 0
    durations = {}
    for tk in takes:
        video = tk["raw"]
        if not video.is_file():
            print(f"There's no video at {video}.")
            return 1
        if video not in durations:
            durations[video] = duration(video)
        for t0, t1 in tk["ranges"]:
            if t1 > durations[video] + 0.05:
                print(f"Take {t0:g}-{t1:g} runs past the end of {video.name} ({durations[video]:.2f}s).")
                return 1
    if not 1 <= a.ref <= len(takes):
        print(f"--ref {a.ref}: there are {len(takes)} takes.")
        return 1
    ref = a.ref - 1
    gj = reel_dir / "grade.json"
    look = bg.resolve_look(reel_dir, explicit={"id": a.look, "strength": a.strength} if a.look else None)
    _, neutral = bg.look_stack(look)

    frames, meas = [], []
    for i, tk in enumerate(takes, 1):
        t0, t1 = tk["ranges"][0]
        imgs = [read_frame(tk["raw"], time, MEASURE_W) for time in sample_times(tk["ranges"])]
        frames.append(imgs)
        m = measure(imgs, dict.fromkeys(SOLVE, 0.0))
        if m is None:
            print(f"No face found in take {i} ({t0:g}-{t1:g}s), so it can't be matched.")
            return 1
        meas.append(m)

    mr, sr = meas[ref]["mean"], meas[ref]["std"]
    out = []
    for i, tk in enumerate(takes):
        t0, t1 = tk["ranges"][0]
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
        if mapped:
            out[-1].update(raw=str(tk["raw"]), ranges=[list(r) for r in tk["ranges"]])
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
    doc, problems = bg.write_grade(reel_dir, out, look, ref=ref, guard=guard,
                                   take_ids=[tk["id"] for tk in takes] if mapped else None)
    if problems:
        print("\n".join(problems) + " (grade.json was not written)")
        return 1
    print(f"-> {gj} ({len(out)} takes, reference take {a.ref}, look {doc['look']['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
