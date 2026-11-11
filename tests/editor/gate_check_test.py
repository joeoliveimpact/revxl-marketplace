#!/usr/bin/env python3
"""LIGHT proof for the Windows half of the 20-test gate.

python tests/editor/gate_check_test.py <scratch-dir> [--case NAME]
Only 360x640, 30 fps, six-second media are made, using the editor's tools.
Both run(ctx) and the standalone command are checked; no production inputs
are changed. Scratch reels live below <scratch-dir>/gate-check-test.
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402

CHECK = cs.REPO / "plugins/editor-superengine/skills/_shared/checks/gate_check.py"
# Literal report() order from the MIT reference; no ignored lane files needed.
IDS = [
    "words_per_screen", "text_chips_on_speaker", "not_grey", "accent_colours",
    "graphic_size", "not_empty", "text_margin", "text_centred", "face_clear",
    "no_camera_zoom", "no_camera_drift", "no_fast_zoom", "no_naked_jump_cut",
    "face_visible", "eyes_on_lens", "no_silent_stare", "no_sparkle_stars",
    "pacing", "layout_holds", "sync",
]
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def write(path, obj):
    path.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def module():
    spec = importlib.util.spec_from_file_location("gate_check_under_test", CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cli(*args):
    return cs.sh([cs.PY, "-X", "utf8", "-I", CHECK, *args])


def media(scratch, silent=False):
    path = scratch / ("silence.mp4" if silent else "speech.mp4")
    audio = "sine=frequency=440:sample_rate=16000:duration=6"
    if silent:
        audio += ",volume=0:enable='between(t,1.5,4.5)'"
    p = cs.sh([cs.rt.tool("ffmpeg"), "-nostdin", "-y", "-v", "error",
               "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=30:duration=6",
               "-f", "lavfi", "-i", audio, "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path])
    if p.returncode:
        raise RuntimeError("fixture ffmpeg failed: " + p.stderr[-1500:])
    return path


def beat(start=0, end=180, layout="full", **extra):
    return dict(id="b1", start_f=start, end_f=end, speech_anchor=None,
                layout=layout, scene=None, broll=None, **extra)


def reel(scratch, name, beats):
    d = cs.fresh(scratch, name)
    write(d / "work/cuts.json", dict(fps=30, segments=[dict(
        src_in_f=0, src_out_f=180, out_in_f=0, out_out_f=180)]))
    write(d / "beat-map-selection.json", dict(beats=beats))
    write(d / "work/edit_map.cut.json", dict(words=[dict(word="Hello", start=1, end=1.2)]))
    return d


def rows(mod, d, render, beats=None):
    return mod.run(dict(reel_dir=d, cuts=cs.load(d / "work/cuts.json"), fps=30,
                        beats=beats if beats is not None else cs.load(d / "beat-map-selection.json")["beats"],
                        render=render))


def valid_rows(found):
    return all(set(("check", "level", "msg", "where", "at")) <= r.keys()
               and r["check"] in ("sync", "no_silent_stare")
               and isinstance(r["at"], (int, float)) and math.isfinite(r["at"])
               and "\n" not in r["msg"] for r in found)


def case_list(scratch, mod):
    p = cli("--list")
    lines = p.stdout.splitlines()
    ck("list: exactly 20 ordered, unique reference IDs, exit 0",
       p.returncode == 0 and len(lines) == 20
       and [ln.split()[0] for ln in lines] == list(IDS), (p.returncode, p.stdout, p.stderr))
    ck("list: PHASE is post and the table has every ID", mod.PHASE == "post"
       and list(mod.GATE_TESTS) == list(IDS), mod.GATE_TESTS)
    ck("list: face clearance includes measured overlay cards",
       "overlay_face_check.py" in mod.GATE_TESTS["face_clear"]["modules"])
    for name, entry in mod.GATE_TESTS.items():
        status = entry.get("status")
        ok = status in ("ported", "covered", "skipped")
        if status == "covered":
            modules = entry.get("modules", ())
            ok = ok and bool(modules) and all((CHECK.parent / m).is_file() for m in modules)
        elif status == "skipped":
            ok = ok and bool(entry.get("reason")) and "\n" not in entry["reason"]
        ck("list: %s has an explicit disposition" % name, ok, entry)
    ck("list: only sync and no_silent_stare are ported",
       {k for k, v in mod.GATE_TESTS.items() if v["status"] == "ported"}
       == {"sync", "no_silent_stare"})
    for name in ("no_fast_zoom", "no_naked_jump_cut"):
        ck("list: %s needs only face reading" % name,
           mod.GATE_TESTS[name]["reason"] == "Needs Apple Vision face reading.")


def case_sync(scratch, mod):
    render = media(scratch)
    for delta in (1, 2, 3, 4, -3, -4):
        b = beat(start=30 + delta)
        b["speech_anchor"] = dict(text="Hello", w0=0, w1=0)
        d = reel(scratch, "sync-%s" % delta, [b])
        found = rows(mod, d, render)
        p = cli(d, "--render", render)
        bad = delta < -3 or delta > 2
        ck("sync: %s frames from the word, matching standalone exit" % delta,
           (p.returncode == 1 and len(found) == 1 and found[0]["check"] == "sync"
            and found[0]["level"] == "block" and valid_rows(found)
            and abs(found[0]["at"] - b["start_f"] / 30) < .01 and "sync" in p.stdout)
           if bad else (found == [] and p.returncode == 0), (found, p.returncode, p.stdout, p.stderr))
    # Decimal word seconds at a rational master FPS; ctx.fps must not replace cuts.json's FPS.
    write(d / "work/cuts.json", dict(fps="30000/1001", segments=[]))
    write(d / "work/edit_map.cut.json", dict(words=[dict(word="Hello", start=1.001, end=1.2)]))
    b["start_f"] = 31
    write(d / "beat-map-selection.json", dict(beats=[b]))
    ck("sync: rational cut FPS and indexed output word start", rows(mod, d, render) == [])

    # Exercise the real builder: the first tiled beat starts at zero, later
    # tiled beats and overlays start at their own rounded word times.
    builder_path = CHECK.parents[2] / "reel-canvas-build/scripts/make_beat_map.py"
    spec = importlib.util.spec_from_file_location("sync_beat_builder", builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    d = reel(scratch, "sync-built", [])
    words_path = d / "work/edit_map.cut.json"
    items = [dict(word="Hello", start=0.20, end=0.6),
             dict(word="coaches", start=2.0, end=2.5)]
    write(words_path, dict(words=items))
    plan = dict(beats=[dict(w0=0, w1=0, layout="full"),
                      dict(w0=1, w1=1, layout="full")])
    bm = builder.build_doc(d, plan, [w["word"] for w in items], items,
                           "work/edit_map.cut.json", words_path, 30, 180)
    ck("sync: real builder opens at zero before the first word", bm["beats"][0]["start_f"] == 0)
    for delta in (0, 4, -3, -4):
        bm["beats"][1]["start_f"] = 60 + delta
        write(d / "beat-map-selection.json", bm)
        found = rows(mod, d, render)
        p = cli(d, "--render", render)
        bad = delta < -3 or delta > 2
        ck("sync: real builder later beat shifted %s frames" % delta,
           (len(found) == 1 and found[0]["check"] == "sync"
            and found[0]["level"] == "block" and found[0]["where"] == "beat b_002"
            and p.returncode == 1) if bad else (found == [] and p.returncode == 0),
           (found, p.returncode, p.stdout, p.stderr))

    overlay = dict(bm["beats"][0], id="overlay", layout="overlay")
    ck("sync: a frame-zero overlay still checks its word",
       any(r["check"] == "sync" for r in rows(mod, d, render, [overlay])))


def case_stare(scratch, mod):
    render = media(scratch, silent=True)
    b = beat()
    d = reel(scratch, "stare", [b])
    found = rows(mod, d, render)
    p = cli(d, "--render", render)
    ck("stare: one middle silent hold warns, exit 0",
       len(found) == 1 and found[0]["check"] == "no_silent_stare"
       and found[0]["level"] == "warn" and valid_rows(found)
       and 1.4 <= found[0]["at"] <= 1.6 and "B-roll" in found[0]["msg"]
       and p.returncode == 0 and "no_silent_stare" in p.stdout,
       (found, p.returncode, p.stdout, p.stderr))
    for cover in ("scene", "broll"):
        b[cover] = dict(id="cover") if cover == "scene" else dict(src="clip.mp4")
        write(d / "beat-map-selection.json", dict(beats=[b]))
        p = cli(d, "--render", render)
        ck("stare: %s over the picture hides the silent hold" % cover,
           rows(mod, d, render, [b]) == [] and p.returncode == 0
           and "no_silent_stare" not in p.stdout, (p.stdout, p.stderr))
        b[cover] = None
    b["scene"] = dict(id="cover")
    write(d / "work/scale_track.json", dict(keys=[dict(f=0, layout="pip")], tweens=[]))
    ck("stare: saved pip keeps the speaker visible above a scene",
       len(rows(mod, d, render, [b])) == 1)
    b["layout"] = "pip"
    write(d / "work/scale_track.json", dict(keys=[dict(f=0, layout="full")], tweens=[]))
    ck("stare: saved full layout takes precedence over the beat's pip",
       rows(mod, d, render, [b]) == [])
    move = dict(start_f=15, end_f=30, prop="layout", **{"from": "full", "to": "pip"})
    write(d / "work/scale_track.json", dict(keys=[dict(f=0, layout="full")], tweens=[move]))
    found = rows(mod, d, render, [b])
    ck("stare: completed full-to-pip move leaves the speaker visible",
       len(found) == 1 and found[0]["at"] > 1.4, found)
    move.update({"from": "pip", "to": "full"})
    write(d / "work/scale_track.json", dict(keys=[dict(f=0, layout="pip")], tweens=[move]))
    ck("stare: completed pip-to-full move leaves the speaker covered",
       rows(mod, d, render, [b]) == [])
    move.update({"from": "full", "to": "pip"})
    write(d / "work/scale_track.json", dict(
        keys=[dict(f=0, layout="full"), dict(f=45, layout="full")], tweens=[move]))
    ck("stare: later hard layout key overrides a completed move",
       rows(mod, d, render, [b]) == [])
    write(d / "work/scale_track.json", dict(
        keys=[dict(f=0, layout="full"), dict(f=20, layout="full")], tweens=[move]))
    found = rows(mod, d, render, [b])
    ck("stare: a key inside a move cannot erase its later destination",
       len(found) == 1 and found[0]["at"] > 1.4, found)
    move.update(start_f=30, end_f=150)
    write(d / "work/scale_track.json", dict(keys=[dict(f=0, layout="full")], tweens=[move]))
    found = rows(mod, d, render, [b])
    ck("stare: silence wholly inside a move into pip remains visible",
       len(found) == 1 and 1.4 < found[0]["at"] < 1.6, found)
    b["scene"] = None
    (d / "work/scale_track.json").unlink()
    # A scene covers the middle except for two short fragments, each below the limit.
    cover = beat(start=48, end=132)
    cover["scene"] = dict(id="cover")
    ck("stare: hidden time cannot join two short visible silences",
       rows(mod, d, render, [cover]) == [])


def case_clean(scratch, mod):
    render = media(scratch)
    d = reel(scratch, "clean", [beat()])
    final = d / "renders"
    final.mkdir()
    import shutil
    shutil.copyfile(render, final / "Clean Master - 11.06.26.mp4")
    p = cli(d)
    ck("clean: speech has no rows and automatic Master selection exits 0",
       rows(mod, d, render) == [] and p.returncode == 0, (p.returncode, p.stdout, p.stderr))


CASES = dict(list=case_list, sync=case_sync, stare=case_stare, clean=case_clean)


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = args.scratch.resolve() / "gate-check-test"
    scratch.mkdir(parents=True, exist_ok=True)
    print("python %s" % cs.PY)
    mod = module()
    for name in [args.case] if args.case else CASES:
        print("-- " + name)
        CASES[name](scratch, mod)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
