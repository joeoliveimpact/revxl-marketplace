"""Turn the Grade Board's Send into the reel's grade, and burn it in only once the client has said yes.

    <editor python> -X utf8 -I grade_from_selection.py --reel-dir <videos/<reel>>
    <editor python> -X utf8 -I grade_from_selection.py --reel-dir <videos/<reel>> --apply <video or still> -o <out> --yes

The first form reads <reel-dir>/grade-selection.json (the board's Send: correction + look + strength), bakes it into
one .cube with bake_grade.py's bake, runs the skin guard on it and writes <reel-dir>/grade.json (one take, the whole
video). Nothing touches a video. A cube that fails the skin guard is refused and grade.json is left as it was.

The second form applies the cube grade.json names to a video (or a still) with apply_grade.py, and only with --yes,
which Claude passes after the client said yes to this grade. It checks the cube's sha256 against grade.json first, so
what gets burnt in is exactly what was approved. A video applied this way is one encode more than the cut itself, so
grade.json records "extra_generations": 1.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]   # -I leaves the script folder off the path
from win_encoding import ensure_utf8_output  # noqa: E402
import grade_math as gm  # noqa: E402
import bake_grade as bg  # noqa: E402
import skin_guard as sg  # noqa: E402
from apply_grade import IMAGES, apply  # noqa: E402
from grade_bounds import clamp  # noqa: E402

KEYS = list(gm.PRE) + list(bg.TUNE)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write(p, doc):
    Path(p).write_bytes((json.dumps(doc, indent=1) + "\n").encode("utf-8"))


def correction_of(sel):
    """The Send's correction, checked against grade_math.json's slider ranges. -> (dict, problem line or None)."""
    corr = sel.get("correction") or {}
    out = {}
    for k, v in corr.items():
        if k not in KEYS:
            return None, f"The Send has a setting this editor doesn't know: {k!r}."
        lo, hi = gm.RANGES[k][0], gm.RANGES[k][1]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            return None, f"The Send's {k} is {v!r}, outside the board's range {lo:g} to {hi:g}."
        out[k] = float(v)
    out, notes = clamp(out)
    for note in notes:
        print("note: " + note)
    return out, None


def bake_selection(reel_dir):
    sel_path, cfg_path = reel_dir / "grade-selection.json", reel_dir / "grade" / "grade-config.json"
    if not sel_path.is_file():
        print(f"There's no grade-selection.json in {reel_dir.name} yet: the client hasn't sent a grade from the Grade Board.")
        return 1
    if not cfg_path.is_file():
        print(f"{reel_dir.name} has no grade set up (grade/grade-config.json). Run make_grade.py first.")
        return 1
    sel, cfg = load(sel_path), load(cfg_path)
    if str(sel.get("math_version")) != gm.SPEC["version"]:
        print(f"The Send was made with grade maths v{sel.get('math_version')}, this editor has v{gm.SPEC['version']}. "
              "Ask the client to open the Grade Board again and press Send.")
        return 1
    old = reel_dir / "grade.json"
    if old.is_file() and len(load(old).get("takes", [])) > 1:
        print(f"{reel_dir.name}'s grade.json holds {len(load(old)['takes'])} matched takes; the Grade Board sets one grade "
              "for the whole cut, so it was not replaced. Ask Claude which one to keep.")
        return 1
    corr, problem = correction_of(sel)
    if problem:
        print(problem)
        return 1
    look = bg.resolve_look(reel_dir, selection=sel.get("look"))
    look = {"id": str(look.get("id") or "none"), "strength": look.get("strength", 1.0)}
    if isinstance(look["strength"], bool) or not isinstance(look["strength"], (int, float)):
        print(f"The Send's look strength is {look['strength']!r}, not a number from 0 to 1.")
        return 1
    _, neutral = bg.look_stack(look)   # refuses an unknown look or a strength outside 0-1, with a plain line
    skin = np.array(cfg["measured"]["skin_rgb"], dtype=np.float64)

    def guard(i, cube):
        ok, _, msg = sg.check(skin, cube, neutral)
        return None if ok else msg
    take = dict(range=[0.0, float(cfg["duration"])], measured=cfg["measured"], correction=corr)
    doc, problems = bg.write_grade(reel_dir, [take], look, guard=guard)
    if problems:
        print(f"{problems[0]} (grade.json was not written)")
        return 1
    print(f"{reel_dir.name}: grade from the Grade Board's Send ({sel.get('saved_at') or 'no time stamp'})")
    print(f"  look {doc['look']['id']} at {doc['look']['strength']:g} · "
          + (", ".join(f"{k} {v:g}" for k, v in corr.items() if v != gm.RANGES[k][3]) or "no correction"))
    print(f"  -> {old} (cube {doc['cube']}). Nothing was applied to the video.")
    return 0


def apply_grade_json(reel_dir, src, out, yes):
    gpath = reel_dir / "grade.json"
    if not yes:
        print("Not applied: burning the grade in needs the client's yes. Show them the grade first, then run this "
              "again with --yes.")
        return 2
    if not gpath.is_file():
        print(f"{reel_dir.name} has no grade.json yet. Bake the Send first (run this without --apply).")
        return 1
    doc = load(gpath)
    cube = reel_dir / doc["cube"]
    if not cube.is_file() or bg.sha256(cube) != doc["cube_sha"]:
        print(f"The cube {doc['cube']} is missing or changed since grade.json was written, so it is not the grade the "
              "client approved. Bake the Send again, then ask again.")
        return 1
    if not Path(src).is_file():
        print(f"There's no file at {src}.")
        return 1
    try:
        secs = apply(src, cube, out)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg could not apply the grade: {(e.stderr or b'').decode('utf-8', 'replace').strip()[-300:]}")
        return 1
    if Path(out).suffix.lower() not in IMAGES:   # a still is a preview; a video is a new generation of the cut
        doc["extra_generations"] = 1
        write(gpath, doc)
    print(f"Applied {doc['cube']} to {Path(src).name} in {secs:.1f}s -> {out}")
    return 0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Grade Board Send -> cube -> grade.json; apply only with the client's yes")
    ap.add_argument("--reel-dir", required=True, help="videos/<reel>")
    ap.add_argument("--apply", metavar="SOURCE", help="a video or still to burn grade.json's cube into")
    ap.add_argument("-o", "--out", help="the graded output (with --apply)")
    ap.add_argument("--yes", action="store_true", help="the client said yes to this grade")
    a = ap.parse_args()
    reel_dir = Path(a.reel_dir).resolve()
    if a.apply:
        if not a.out:
            ap.error("--apply needs -o <out>")
        return apply_grade_json(reel_dir, Path(a.apply), Path(a.out), a.yes)
    return bake_selection(reel_dir)


if __name__ == "__main__":
    sys.exit(main())
