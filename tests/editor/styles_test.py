#!/usr/bin/env python3
"""S6c check for the editing-style planner (styles.py) on small made-up reels.

usage: EDITOR_SE_HOME=<a state with ffmpeg> python -X utf8 -I tests/editor/styles_test.py [--case <name>]...
cases: ask, saved, cut-set, punch-143, one-per-sentence, clip, follow-cam, planted-cross, layout-switch, frames,
ceiling, merge, fps-master, ratchet, camera, camera-defaults, camera-refusals, camera-drops (default: all).
styles.py reads the frame rate from the cut master, so each reel gets a
tiny black master-100x.mp4 (64x64, made once per rate with that state's ffmpeg). Most cases run `styles.py plan` as the client's Claude would; punch-143, ceiling and
planted-cross call styles.plan in this process, because they swap in a test preset, a test tuning.json or a
planted span. EDITOR_SE_HOME then points at an empty temp state (its state.json names only the real ffmpeg and
ffprobe), so a real saved style never leaks in.
Prints PASS/FAIL per check; exit 0 only if all pass.
"""
import argparse, importlib.util, json, os, shutil, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-canvas-build" / "scripts"
STYLES = SCRIPTS / "styles.py"
sys.path.insert(0, str(REPO / "plugins" / "editor-superengine" / "skills" / "_shared"))
import runtime as rt  # noqa: E402
fails = []
TOOLS = {}  # ffmpeg / ffprobe of the real state, read before EDITOR_SE_HOME moves to the temp state
MASTERS = {}  # rate -> a cached tiny master


def load(name):
    spec = importlib.util.spec_from_file_location("editor_" + name, SCRIPTS / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


st, eg = load("styles"), load("effect_gate")
FPS = 25
CUTS = [50, 100]


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (str(detail)[:400],)), flush=True)
    if not ok:
        fails.append(name)
    return ok


def make_reel(root, *a, rate="25", **kw):
    """st.make_reel plus a tiny 150-frame cut master at `rate` (styles.py reads the reel's rate from it)."""
    reel = st.make_reel(root, *a, **kw)
    if rate not in MASTERS:
        m = Path(root) / f"master-{len(MASTERS)}.mp4"
        subprocess.run([TOOLS["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:r={rate}",
                        "-frames:v", "150", "-c:v", "libx264", "-pix_fmt", "yuv420p", m], check=True, timeout=60)
        MASTERS[rate] = m
    (reel / "work" / "renders").mkdir()
    shutil.copyfile(MASTERS[rate], reel / "work" / "renders" / "master-100x.mp4")
    return reel


def plan_cli(reel):
    p = subprocess.run([sys.executable, "-X", "utf8", "-I", STYLES, "plan", "--reel-dir", reel], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=dict(os.environ), timeout=60)
    out = p.stdout + p.stderr
    ck(f"no traceback ({reel.name})", "Traceback" not in out, out)
    track = reel / "work" / "scale_track.json"
    return p.returncode, p.stdout, json.loads(track.read_text(encoding="utf-8")) if track.exists() else None


def pin(punch_scale=1.12, **moves):
    return {"style": "punch-in", "punch_scale": punch_scale, "moves": moves}


def key(track, f):
    return next((k for k in track["keys"] if k["f"] == f), None)


def onset(w):
    return round((Fraction(str(st.WORDS[w][1])) - Fraction(1, 20)) * FPS)


def crosses(spans):
    return [s for s in spans for c in CUTS if s["start_f"] < c < s["end_f"]]


P130 = {"dramatic": dict(st.PRESETS["dramatic"], peak=1.30), "subtle": st.PRESETS["subtle"]}
ANCH = {0: [(0, 0.5, 0.30), (20, 0.55, 0.32), (40, 0.6, 0.34)], 1: [(52, 0.4, 0.4), (70, 0.42, 0.41), (96, 0.45, 0.42)]}


def c_ask(root):
    reel = make_reel(root)
    rc, out, track = plan_cli(reel)
    ck("ask: exit 1 with the ask line, nothing written",
       rc == 1 and out.strip().splitlines()[-1] == st.ASK and track is None, out)


def c_saved(root):
    sd = Path(os.environ["EDITOR_SE_HOME"]) / "styles"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "default.json").write_bytes(json.dumps({"schema": 1, "edit_style": {"style": "punch-in",
                                                                               "punch_scale": 1.2}}).encode())
    try:
        reel = make_reel(root)
        rc, out, _ = plan_cli(reel)
        ck("saved: an unpicked reel still asks", rc == 1 and "ask: which editing style?" in out, out)
        st.saved_style.pick(reel, "default")
        rc, out, track = plan_cli(reel)
        ck("saved: the saved style is used when the Send has none (source saved, its punch level on frame 50)",
           rc == 0 and track["source"] == "saved" and key(track, 50)["scale"] == 1.2, out)
        rc, out, track = plan_cli(make_reel(root, {"style": "layout-switch"}))
        ck("saved: the Send's style wins over the saved one", rc == 0 and track["source"] == "reel"
           and track["style"]["style"] == "layout-switch", out)
    finally:
        (sd / "default.json").unlink()
        (sd / "_index.json").unlink(missing_ok=True)


def c_cut_set(root):
    rc, out, track = plan_cli(make_reel(root, pin()))
    ck("cut-set: punch level changes exactly on each cut frame (1.0, 1.12, 1.0), no tween",
       rc == 0 and [(k["f"], k["scale"]) for k in track["keys"]] == [(0, 1.0), (50, 1.12), (100, 1.0)]
       and track["tweens"] == [] and track["spans"] == [], out)
    lines = out.strip().splitlines()
    ck("cut-set: the done line and the JSON summary last",
       "✓ Style planned: punch-in, 0 moves" in lines and json.loads(lines[-1]) == {"style": "punch-in", "keys": 3,
                                                                                   "tweens": 0, "warnings": 0}, out)


def c_punch_143(root):
    es = pin(1.10, word_punches={"preset": "dramatic", "shape": "hard-cut", "picks": [7]})
    t = st.plan(make_reel(root, es), presets=P130, tuning=Path(root) / "none.json")
    k = key(t, onset(7))
    ck("punch-143: segment 1.10 x peak 1.30 = key scale 1.43 on the onset frame, not capped",
       k is not None and k["scale"] == 1.43, t["keys"])
    es["moves"]["word_punches"]["shape"] = "eased"
    t = st.plan(make_reel(root, es), presets=P130, tuning=Path(root) / "none.json")
    ck("punch-143: the eased shape peaks at 1.43 too", any(x["to"] == 1.43 for x in t["tweens"]), t["tweens"])


def c_one_per_sentence(root):
    es = pin(word_punches={"preset": "dramatic", "shape": "eased", "picks": [0, 1, 3, 7]})
    rc, out, track = plan_cli(make_reel(root, es))
    ids = {x["id"].split()[1] for x in track["tweens"]} if track else set()
    ck("one-per-sentence: words 1 and 3 dropped, 0 and 7 kept", rc == 0 and ids == {"0", "7"}, track)
    ck("one-per-sentence: a note names each dropped word",
       'note: word punch on "edits" (word 1) dropped' in out and 'note: word punch on "save." (word 3) dropped' in out,
       out)


def c_clip(root):
    es = pin(word_punches={"preset": "dramatic", "shape": "eased", "picks": [6, 10]})
    rc, out, track = plan_cli(make_reel(root, es))
    p6 = [x for x in track["tweens"] if x["id"].startswith("punch 6")] if track else []
    ck("clip: the punch near the cut starts on its onset and is back by the segment's last frame (49)",
       rc == 0 and p6 and p6[0]["start_f"] == onset(6) and p6[-1]["end_f"] == 49 and p6[-1]["to"] == 1.0, p6)
    ck("clip: a punch whose way in doesn't fit is dropped with a note", 'word punch on "time." (word 10) dropped' in out,
       out)
    ck("clip: no span crosses a cut", track and not crosses(track["spans"]), track and track["spans"])


def c_follow_cam(root):
    rc, out, track = plan_cli(make_reel(root, pin(follow_cam=True), anchors=ANCH))
    og = [(x["start_f"], x["end_f"]) for x in track["tweens"]] if track else []
    ck("follow-cam: origin moves stay inside their segment", rc == 0 and og == [(0, 20), (20, 40), (52, 70), (70, 96)]
       and all(x["prop"] == "origin" and x["ease"] == "none" for x in track["tweens"]), track and track["tweens"])
    k = key(track, 50) if track else None
    ck("follow-cam: restarts on the cut frame at the new segment's first sample",
       k is not None and (k["ox"], k["oy"]) == (0.4, 0.4), k)
    ck("follow-cam: the effect gate is OK with its spans",
       track and not eg.check(track["spans"], CUTS, track["fps"], track["total_f"]), track and track["spans"])


def c_planted_cross(root):
    reel = make_reel(root, pin(follow_cam=True), anchors=ANCH)
    planted = [{"layer": "aroll_transform", "start_f": 40, "end_f": 60, "id": "planted follow-cam"}]
    rc = st.cmd_plan(reel, extra_spans=planted)
    ck("planted-cross: a move across the cut at frame 50 stops the plan (exit 1), nothing written",
       rc == 1 and not (reel / "work" / "scale_track.json").exists(), rc)
    try:
        st.plan(reel, extra_spans=planted)
        ck("planted-cross: a BLOCK line names the move and the cut", False, "no stop")
    except st.Stop as s:
        ck("planted-cross: a BLOCK line names the move and the cut",
           any(l.startswith("BLOCK aroll_transform 'planted follow-cam'") and "frame 50" in l for l in s.lines), s.lines)


def c_layout_switch(root):
    beats = [st.beat("b_001", 0, 50, 0, 6), st.beat("b_002", 50, 70, 7, 8, "split"),
             st.beat("b_003", 70, 150, 9, 12, "stack")]
    rc, out, track = plan_cli(make_reel(root, {"style": "layout-switch"}, beats=beats))
    ck("layout-switch: the change on the cut frame 50 is a key only",
       rc == 0 and key(track, 50)["layout"] == "split" and not any(x["start_f"] == 50 for x in track["tweens"]), track)
    move_f = round(Fraction("0.6") * FPS)
    ck("layout-switch: the change mid-segment is one power2.inOut tween of move_f frames",
       track and track["tweens"] == [{"start_f": 70, "end_f": 70 + move_f, "prop": "layout", "from": "split",
                                       "to": "stack", "ease": "power2.inOut", "id": "layout b_003"}],
       track and track["tweens"])
    rc, out, track = plan_cli(make_reel(root, {"style": "layout-switch", "moves": {"follow_cam": True}}))
    ck("layout-switch: moves refused (exit 2, plain line, nothing written)",
       rc == 2 and "belong to the punch-in style" in out and track is None, out)


def c_frames(root):
    es = pin(opening_settle=True, follow_cam=True,
             word_punches={"preset": "dramatic", "shape": "eased", "picks": [4, 7, 11]})
    rc, out, track = plan_cli(make_reel(root, es, anchors=ANCH))
    isint = lambda v: isinstance(v, int) and not isinstance(v, bool)  # noqa: E731
    ck("frames: every key f, tween start and end, span start and end is a whole frame",
       rc == 0 and all(isint(k["f"]) for k in track["keys"])
       and all(isint(x["start_f"]) and isint(x["end_f"]) for x in track["tweens"] + track["spans"]), track)
    starts = {x["id"]: x["start_f"] for x in track["tweens"]} if track else {}
    ck("frames: each punch starts on round((start - 0.05) x fps)",
       all(starts.get(f"punch {w} in") == onset(w) for w in (4, 7, 11)), starts)


def c_ceiling(root):
    tun = Path(root) / "tuning.json"
    tun.write_bytes(json.dumps({"softness_ceiling": 1.25}).encode())
    es = pin(1.10, word_punches={"preset": "dramatic", "shape": "hard-cut", "picks": [7]})
    t = st.plan(make_reel(root, es), presets=P130, tuning=tun)
    ck("ceiling: 1.43 above 1.25 gives the softness note, the value unchanged",
       "softness: beat b_002 reaches 1.43" in t["warnings"] and key(t, onset(7))["scale"] == 1.43, t["warnings"])
    t = st.plan(make_reel(root, es), tuning=tun)
    ck("ceiling: the start preset (1.10 x 1.22 = 1.342) is noted too; the 1.0 segment stays quiet",
       "softness: beat b_002 reaches 1.342" in t["warnings"]
       and not any("b_001" in w for w in t["warnings"]), t["warnings"])


def c_merge(root):
    beats = [st.beat("b_001", 0, 60, 0, 7), st.beat("b_002", 60, 65, 8, 8, "split"),
             st.beat("b_003", 65, 150, 9, 12, "pip")]
    rc, out, track = plan_cli(make_reel(root, {"style": "layout-switch"}, beats=beats))
    ck("merge: two overlapping layout moves become one power2.inOut gesture, first start to last end",
       rc == 0 and [(x["start_f"], x["end_f"], x["from"], x["to"], x["ease"]) for x in track["tweens"]]
       == [(60, 80, "full", "pip", "power2.inOut")], track and track["tweens"])
    es = pin(opening_settle=True, word_punches={"preset": "dramatic", "shape": "eased", "picks": [0]})
    rc, out, track = plan_cli(make_reel(root, es))
    first = track["tweens"][0] if track and track["tweens"] else {}
    ck("merge: the settle and a touching punch become one power2.inOut move 1.06 -> 1.22",
       (first.get("start_f"), first.get("end_f"), first.get("from"), first.get("to"), first.get("ease"))
       == (0, onset(0) + 3, 1.06, 1.22, "power2.inOut"), track and track["tweens"])


def c_fps_master(root):
    rc, out, track = plan_cli(make_reel(root, pin(), fps=29.97, rate="30000/1001"))
    ck("fps-master: a 30000/1001 master with a 29.97 cuts.json -> plan fps 30000/1001",
       rc == 0 and track["fps"] == "30000/1001", out)
    rc, out, track = plan_cli(make_reel(root, pin(), fps=29.97, rate="25"))
    ck("fps-master: a 25 fps master under a 29.97 cuts.json stops the plan (exit 1, nothing written)",
       rc == 1 and "runs at 25.000 fps" in out and track is None, out)


def c_ratchet(root):
    for levels in (2, 3, 4):
        for w, base in ((0, 1.0), (7, 1.12)):
            rc, out, t = plan_cli(make_reel(root, pin(ratchet={"picks": [w], "levels": levels})))
            on = max(onset(w), 50 if w == 7 else 0)
            expected = [(on + n * 5, st.r4(base * (1 + (n + 1) * 0.08))) for n in range(levels)]
            expected.append((on + (levels - 1) * 5 + 8, base))
            ck(f"ratchet: {levels} hard up-steps on segment scale {base}, then a hard return",
               rc == 0 and [(k["f"], k["scale"]) for k in t["keys"] if on <= k["f"] <= expected[-1][0]]
               == expected and not t["tweens"], out)
    rc, out, t = plan_cli(make_reel(root, pin(ratchet={"picks": [4], "levels": 4})))
    ck("ratchet: cut reduces four levels to two with a note and return by frame 49",
       rc == 0 and [(k["f"], k["scale"]) for k in t["keys"] if 36 <= k["f"] < 50]
       == [(36, 1.08), (41, 1.16), (49, 1.0)] and "note: ratchet" in out and "2 levels" in out, out)
    rc, out, t = plan_cli(make_reel(root, pin(ratchet={"picks": [6], "levels": 2})))
    ck("ratchet: fewer than two levels fit, dropped with a note",
       rc == 0 and "note: ratchet" in out and "dropped" in out and len(t["keys"]) == 3, out)
    for rp, wp, survivor in (([0], [2], "ratchet"), ([2], [0], "word punch")):
        rc, out, t = plan_cli(make_reel(root, pin(ratchet={"picks": rp, "levels": 3},
            word_punches={"preset": "dramatic", "shape": "hard-cut", "picks": wp})))
        ck(f"ratchet: shared sentence budget, first event is {survivor}",
           rc == 0 and "one punch per sentence" in out and len(t["keys"]) == (7 if survivor == "ratchet" else 5), out)
    rc, out, t = plan_cli(make_reel(root, pin(ratchet={"picks": [7], "levels": 3},
        word_punches={"preset": "dramatic", "shape": "hard-cut", "picks": [0]})))
    ck("ratchet: separate sentences keep both events", rc == 0 and len(t["keys"]) == 9
       and "one punch per sentence" not in out, out)
    words = list(st.WORDS)
    words[7] = (words[7][0], 2.0)
    rc, out, t = plan_cli(make_reel(root, pin(ratchet={"picks": [7], "levels": 2}), words=words))
    ck("ratchet: early onset clamped to segment's first frame", rc == 0 and
       [(k["f"], k["scale"]) for k in t["keys"] if 50 <= k["f"] < 100]
       == [(50, 1.2096), (55, 1.2992), (63, 1.12)], out)


def c_camera(root):
    rc, out, t = plan_cli(make_reel(root, pin(push={"segments": "all"}, follow_cam=True), anchors=ANCH))
    scales = [x for x in t["tweens"] if x["prop"] == "scale"] if t else []
    ck("push: one linear tween per shot, keeps none after merge with follow-cam",
       rc == 0 and [(x["start_f"], x["end_f"], x["from"], x["to"], x["ease"]) for x in scales]
       == [(0, 49, 1.0, 1.06, "none"), (50, 99, 1.12, 1.1872, "none"), (100, 149, 1.0, 1.06, "none")], out)
    rc, out, t = plan_cli(make_reel(root, pin(ken_burns={"segments": [1]}), anchors=ANCH))
    ck("ken-burns: scale and origin share the shot's first and last frames",
       rc == 0 and len(t["tweens"]) == 2 and all(x["start_f"] == 50 and x["end_f"] == 99
       and x["ease"] == "sine.inOut" for x in t["tweens"])
       and next(x for x in t["tweens"] if x["prop"] == "scale")["to"] == 1.2096
       and next(x for x in t["tweens"] if x["prop"] == "origin")["from"] == [0.36, 0.4]
       and next(x for x in t["tweens"] if x["prop"] == "origin")["to"] == [0.44, 0.4]
       and (key(t, 50)["ox"], key(t, 50)["oy"]) == (0.36, 0.4)
       and not eg.check(t["spans"], CUTS, t["fps"], t["total_f"]), out)
    reel = make_reel(root, pin(ken_burns={"segments": [0]}))
    try:
        st.plan(reel, extra_spans=[{"layer": "aroll_transform", "start_f": 40, "end_f": 60,
                                  "id": "planted Ken Burns"}])
        ck("ken-burns: planted cut crossing blocked", False)
    except st.Stop as s:
        ck("ken-burns: planted cut crossing blocked", s.code == 1 and any(
            l.startswith("BLOCK aroll_transform 'planted Ken Burns'") and "frame 50" in l for l in s.lines), s.lines)
    for edge, xy in (("top", (0.4, 0)), ("bottom", (0.4, 1)), ("left", (0, 0.4)), ("right", (1, 0.4))):
        rc, out, t = plan_cli(make_reel(root, pin(reframe={"segments": [1], "edge": edge}), anchors=ANCH))
        ck(f"reframe: {edge} edge hard-set on first frame", rc == 0 and
           (key(t, 50)["ox"], key(t, 50)["oy"]) == xy and not t["tweens"], out)
    rc, out, t = plan_cli(make_reel(root, pin(reframe={"segments": [0], "edge": "top"})))
    ck("reframe: no zoom gets a note", rc == 0 and
       "the reframe has nothing to hold: segment 0 isn't zoomed" in out, out)
    rc, out, t = plan_cli(make_reel(root, pin(push={"segments": [1], "to": 1.2},
        ken_burns={"segments": [2], "to": 1.1}, reframe={"segments": [1], "edge": "right"})))
    ck("camera: disjoint push and drift plus push with reframe are allowed",
       rc == 0 and next(x for x in t["tweens"] if x["id"] == "push 1")["to"] == 1.344
       and next(x for x in t["tweens"] if x["id"] == "ken-burns 2 scale")["to"] == 1.1, out)
    rc, out, t = plan_cli(make_reel(root, pin(ken_burns={"segments": [0]}),
        anchors={0: [(0, 0.01, 0.2)]}))
    ck("ken-burns: pan clamped inside frame", rc == 0 and key(t, 0)["ox"] == 0
       and next(x for x in t["tweens"] if x["prop"] == "origin")["to"] == [0.05, 0.2], out)


def c_camera_defaults(root):
    for moves in ({}, {n: None for n in ("ratchet", "push", "ken_burns", "reframe")}):
        raw = {"style": "punch-in", "moves": moves} if moves else {"style": "punch-in"}
        es = st.check_style(raw, "reel", len(st.WORDS))
        rc, out, t = plan_cli(make_reel(root, raw))
        ck("camera: absent and null options are off, no extra keys or tweens", rc == 0 and
           all(es["moves"][n] is None for n in ("ratchet", "push", "ken_burns", "reframe"))
           and [(k["f"], k["scale"]) for k in t["keys"]] == [(0, 1.0), (50, 1.12), (100, 1.0)]
           and not t["tweens"], out)


def c_camera_refusals(root):
    bad = [pin(push={"segments": [1]}, ken_burns={"segments": "all"}),
           pin(ken_burns={"segments": [1]}, reframe={"segments": [1], "edge": "top"}),
           pin(ratchet={"picks": [0], "levels": 5}),
           pin(reframe={"segments": [0], "edge": "middle"})]
    valid = {"ratchet": {"picks": [0], "levels": 2}, "push": {"segments": "all"},
             "ken_burns": {"segments": "all"}, "reframe": {"segments": "all", "edge": "top"}}
    bad += [{"style": "layout-switch", "moves": {n: v}} for n, v in valid.items()]
    for n in ("push", "ken_burns", "reframe"):
        bad += [pin(**{n: dict(valid[n], segments=v)}) for v in ([3], [-1], [True], "each", None)]
    bad += [pin(ratchet={"picks": v, "levels": 2}) for v in ([True], [-1], [len(st.WORDS)], "0")]
    bad += [pin(ratchet={"picks": [0], "levels": v}) for v in (True, 2.0, None)]
    for n, v in valid.items():
        bad.append(pin(**{n: dict(v, unknown=True)}))
        bad.append(pin(**{n: []}))
    for n in ("push", "ken_burns"):
        bad += [pin(**{n: dict(valid[n], to=v)}) for v in (0.9, 2.1, True, "1.1", None)]
    for i, raw in enumerate(bad):
        rc, out, t = plan_cli(make_reel(root, raw))
        ck(f"camera: refusal {i} is plain Stop(2), nothing written", rc == 2 and
           any(l.startswith("✗ ") for l in out.splitlines()) and "Traceback" not in out and t is None, out)


def c_camera_drops(root):
    rc, out, t = plan_cli(make_reel(root, pin(push={"segments": [0]}, opening_settle=True,
        ratchet={"picks": [2], "levels": 3},
        word_punches={"preset": "dramatic", "shape": "eased", "picks": [0]})))
    ck("camera: push drops word punch, ratchet and opening settle with notes", rc == 0 and
       all(f"note: {name}" in out for name in ("word punch", "ratchet", "opening settle skipped"))
       and len(t["tweens"]) == 1 and len(t["keys"]) == 3, out)
    rc, out, t = plan_cli(make_reel(root, pin(ken_burns={"segments": [0]},
        reframe={"segments": [1], "edge": "top"}, follow_cam=True), anchors=ANCH))
    ck("camera: follow-cam skipped where drift or reframe owns the centre", rc == 0 and
       "note: follow-cam skipped on segment 0" in out and "note: follow-cam skipped on segment 1" in out
       and not any(x["id"].startswith("follow-cam") for x in t["tweens"]), out)


CASES = {"ask": c_ask, "saved": c_saved, "cut-set": c_cut_set, "punch-143": c_punch_143,
         "one-per-sentence": c_one_per_sentence, "clip": c_clip, "follow-cam": c_follow_cam,
         "planted-cross": c_planted_cross, "layout-switch": c_layout_switch, "frames": c_frames, "ceiling": c_ceiling,
         "merge": c_merge, "fps-master": c_fps_master, "ratchet": c_ratchet, "camera": c_camera,
         "camera-defaults": c_camera_defaults, "camera-refusals": c_camera_refusals, "camera-drops": c_camera_drops}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", action="append", choices=list(CASES), help="case to run (repeatable); default all")
    a = ap.parse_args()
    TOOLS.update({n: rt.tool(n) for n in ("ffmpeg", "ffprobe")})
    with tempfile.TemporaryDirectory() as root, \
            patch.dict(os.environ, {"EDITOR_SE_HOME": str(Path(root) / "state")}):
        (Path(root) / "state").mkdir()
        (Path(root) / "state" / "state.json").write_bytes(json.dumps({"components": {"ffmpeg": {"bins": TOOLS}}}).encode())
        for name in a.case or list(CASES):
            print(f"== {name}", flush=True)
            try:
                CASES[name](root)
            except Exception as e:  # a crash is a failed check, never a pass
                ck(f"{name}: test run", False, f"stopped: {type(e).__name__}: {e}")
    print("%d failed" % len(fails) if fails else "all passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
