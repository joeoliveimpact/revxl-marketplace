#!/usr/bin/env python3
"""Heavy check: every Beat Map catalog pick passes compose's preview gate and takeover black-picture rule.

usage: python -X utf8 -I tests/editor/scene_picks_test.py [--scene <id> ...] [--render]
Requires EDITOR_SE_HOME with the installed runtime. Default: lint every offered scene; --render also
renders each pick once through compose.hf_render and checks takeover picks flattened over black against
tri2.black_gap_s from tuning.json. Overlay picks skip the black-picture check because they sit on the
speaker's picture, which is never black. Uses scene_render_test's offline environment and cleanup.
Prints PASS/FAIL per check; exit 0 = all passed. Refuses to start below 10 GB free disk.
"""
import argparse, json, re, shutil, sys, tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scene_render_test as heavy  # noqa: E402
import scene_fill  # noqa: E402  (the Beat Map builder's catalog, on compose's script path)

compose, ck = heavy.compose, heavy.ck


def scene_test(item, tmp, env, log, render):
    sid = item["id"]
    folder = heavy.SCENES / sid
    spec = json.loads((folder / "scene.json").read_text(encoding="utf-8"))
    html = (folder / "scene.html").read_text(encoding="utf-8")
    root = re.search(r'<[^>]*\bdata-composition-id="%s"[^>]*>' % re.escape(sid), html)
    duration = float(re.search(r'data-duration="([\d.]+)"', root.group(0)).group(1))
    pick = {"id": sid, "slots": {n: s["default"] for n, s in spec["slots"].items()},
            "params": {n: p["default"] for n, p in spec["params"].items()}}
    beat = {"id": "b_001", "start_f": heavy.FPS, "end_f": heavy.FPS + round(duration * heavy.FPS), "scene": pick}
    selection = tmp / "beat-map-selection.json"
    selection.write_bytes(json.dumps({"beats": [beat]}).encode("utf-8"))
    beat = json.loads(selection.read_text(encoding="utf-8"))["beats"][0]
    # Default numeric displays are sample claims, backed by a fixture transcript just like the brand proof.
    words = " ".join(list(pick["slots"].values()) + [str(pick["params"].get("value", ""))]).split()
    problems = compose.scene_check.fill_problems(sid, beat, words=words)
    if not ck(f"{sid}: Beat Map pick passes compose's fill validation", not problems, "; ".join(problems)):
        return
    proj = tmp / "project"
    compose.scene_project(proj, beat, Fraction(heavy.FPS))
    ok, lines = compose.lint_or_stop(proj, f"scene {sid} (beat {beat['id']})", env)
    ck(f"{sid}: Beat Map pick passes compose's preview gate", ok is True and not any(
        line.startswith("✗") for line in lines), " | ".join(lines))
    if render and ok and not any(line.startswith("✗") for line in lines):
        vf = tmp / "pick.vars.json"
        vf.write_bytes(json.dumps({**beat["scene"]["slots"], **beat["scene"]["params"]}).encode("utf-8"))
        cache = tmp / "hf-cache"
        cache.mkdir()
        mov = tmp / "pick.mov"
        compose.hf_render(proj, mov, env, f"scene {sid} (beat {beat['id']})",
                          ["--format", "mov", "--fps", str(heavy.FPS), "--strict-variables", "--variables-file", vf,
                           "--frames-cache-dir", cache, "--workers", "2"])
        stream = heavy.probe(mov)
        ck(f"{sid}: Beat Map pick renders with the beat's frame count",
           int(stream.get("nb_read_frames") or -1) == beat["end_f"] - beat["start_f"], str(stream))
        if spec.get("kind") == "takeover":
            gap = heavy.black_gap_s()
            clean, detail = heavy.black_picture(mov, gap)
            ck(f"{sid}: Beat Map pick never reads as a black picture (no black stretch >= {gap:g} s)", clean, detail)
    n = len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0
    ck(f"{sid}: no network attempts during the preview gate and render ({n} logged)", n == 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene", action="append", help="scene id (repeatable); default every Beat Map catalog scene")
    ap.add_argument("--render", action="store_true", help="also render each pick once through compose")
    a = ap.parse_args()
    if a.render:
        print("info: overlay scenes skip the black-picture check: they sit on the speaker's picture, which is never black.")
    free = shutil.disk_usage(tempfile.gettempdir()).free / 2 ** 30
    if free < heavy.MIN_FREE_GB:
        print(f"FAIL only {free:.1f} GB free disk; renders need {heavy.MIN_FREE_GB} GB. Free some space and run again.")
        return 1
    try:
        items = scene_fill.catalog()
        ck("the Beat Map catalog offers scenes", bool(items))
        offered = {item["id"]: item for item in items}
        ids = a.scene or list(offered)
        for sid in ids:
            if not ck(f"{sid}: offered by the Beat Map catalog", sid in offered):
                continue
            tmp = Path(tempfile.mkdtemp(prefix=f"scene-pick-{sid}-"))
            try:
                env, log = heavy.make_env(tmp)
                scene_test(offered[sid], tmp, env, log, a.render)
            except Exception as e:  # a crash is a failed check, never a pass
                detail = " | ".join(e.lines) if isinstance(e, compose.Stop) else str(e)
                ck(f"{sid}: test run", False, f"stopped: {type(e).__name__}: {detail}")
            finally:
                heavy.kill_warm()
                heavy.ost.remove(tmp)
    except Exception as e:
        ck("Beat Map picks test run", False, f"stopped: {type(e).__name__}: {e}")
    print("%d failed" % len(heavy.fails) if heavy.fails else "all passed")
    return 1 if heavy.fails else 0


if __name__ == "__main__":
    sys.exit(main())
