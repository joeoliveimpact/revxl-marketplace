#!/usr/bin/env python3
"""S9.1 proof: one QA entry point, anchor and scene checks, and the hub's qa.json.

    python tests/editor/qa_test.py <scratch-dir> [--case NAME]

Synthetic reels only: no media or rendering. Prints PASS/FAIL lines; exits 0 only
when every check passes. Child scripts use the editor Python, else this Python,
with -X utf8 -I, as in n1_map_test.py. All fixture writes stay under scratch.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402

P = HERE.parents[1] / "plugins" / "editor-superengine"
CHECKS = P / "skills" / "_shared" / "checks"
CHECK = CHECKS / "check.py"
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def reel(scratch, name):
    d = cs.fresh(scratch, name)
    words = [dict(id="w_%04d" % i, word=w, start=i * .5, end=i * .5 + .4,
                  parakeet_start=i * .5, status="aligned")
             for i, w in enumerate(["We", "help", "250", "people"])]
    cuts = dict(fps=30, segments=[dict(src_in_f=0, src_out_f=120, out_in_f=0, out_out_f=120)])
    write(d / "work/cuts.json", cuts)
    write(d / "work/edit_map.json", dict(words=words))
    write(d / "work/edit_map.cut.json", dict(words=words))
    beats = [dict(id="b_001", start_f=0, end_f=60, speech_anchor=dict(text="We help", w0=0, w1=1),
                  layout="full", value=None, scene=None, broll=None, transition=None),
             dict(id="b_002", start_f=60, end_f=120, speech_anchor=dict(text="250 people", w0=2, w1=3),
                  layout="overlay", value=250, broll=None, transition=None,
                  scene=dict(id="counter", slots=dict(label="people"), params=dict(value=250)))]
    write(d / "beat-map-selection.json", dict(schema=1, reel=name, fps=30, words="work/edit_map.cut.json",
          beats=beats, word_marks=[], proposed={}, notes={}, needs="", sent_at="2026-11-06T12:00:00+00:00"))
    p = cs.run("word_map.py", d)
    if p.returncode:
        raise RuntimeError("Fixture word map failed: " + p.stdout + p.stderr)
    return d


def qa(d, script=CHECK, *args):
    p = cs.sh([cs.PY, "-X", "utf8", "-I", script, d, *args])
    return p, cs.load(d / "work/qa.json")


def has(report, check):
    return any(h.get("check") == check and h.get("level") == "block" for h in report.get("checks", []))


def edit_beats(d, change):
    path = d / "beat-map-selection.json"
    data = cs.load(path)
    change(data["beats"])
    write(path, data)


def clean_without(scratch, check):
    p, report = qa(reel(scratch, "reverse-" + check))
    ck(check + ": absent from a clean reel", p.returncode == 0 and not has(report, check),
       (p.returncode, report, p.stderr))


def case_clean(scratch):
    d = reel(scratch, "clean")
    p, report = qa(d)
    ck("clean: exit 0 and no blocks", p.returncode == 0 and report.get("blocks") == 0,
       (p.returncode, report, p.stderr))
    ck("clean: all-clear row", dict(check="all-clear", level="pass", msg="Every check passed.",
       module="check") in report.get("checks", []), report)
    ck("clean: pre phase, no render, no warnings", report.get("phase") == "pre"
       and report.get("render") is None and report.get("warns") == 0, report)
    stamp = datetime.fromisoformat(report["ran_at"])
    ck("clean: timestamp has an offset", stamp.utcoffset() is not None, report)
    ck("clean: plain summary", p.stdout.splitlines() == ["QA: 0 blocks, 0 warnings (pre)"], p.stdout)
    raw = (d / "work/qa.json").read_bytes()
    ck("clean: UTF-8 and LF", b"\r" not in raw and json.loads(raw.decode("utf-8")) == report)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "anchor_check.py", d])
    ck("clean: standalone anchor passes", p.returncode == 0, p.stdout + p.stderr)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "scene_fill_check.py", d])
    ck("clean: standalone scene fill passes", p.returncode == 0, p.stdout + p.stderr)
    for phase in ("post", "all"):
        p, report = qa(d, CHECK, "--phase", phase)
        ck("clean: %s needs a finished video" % phase, p.returncode == 1
           and report.get("phase") == phase and report.get("render") is None
           and report.get("blocks") == 1 and len(report.get("checks", [])) == 1
           and report["checks"][0].get("msg") == "No finished video to check yet. Make the final video first, then run the check again.", report)


def case_anchor(scratch):
    d = reel(scratch, "anchor")
    edit_beats(d, lambda beats: beats[0]["speech_anchor"].update(text="We stopped"))
    p, report = qa(d)
    ck("anchor: stale speech quote blocks", p.returncode == 1 and has(report, "anchor-lost"),
       (p.returncode, report, p.stderr))
    ck("anchor: beat location", any(h.get("check") == "anchor-lost" and h.get("where") == "beat b_001"
       for h in report.get("checks", [])), report)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "anchor_check.py", d])
    ck("anchor: standalone exits 1", p.returncode == 1 and "anchor-lost" in p.stdout, p.stdout + p.stderr)
    clean_without(scratch, "anchor-lost")


def case_overflow(scratch):
    d = reel(scratch, "overflow")
    edit_beats(d, lambda beats: beats[1]["scene"]["slots"].update(label="x" * 31))
    p, report = qa(d)
    ck("overflow: long slot blocks", p.returncode == 1 and has(report, "slot-overflow"),
       (p.returncode, report, p.stderr))
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "scene_fill_check.py", d])
    ck("overflow: standalone exits 1", p.returncode == 1 and "slot-overflow" in p.stdout, p.stdout + p.stderr)
    edit_beats(d, lambda beats: beats[1]["scene"].update(slots=dict(label="people"),
                                                        params=dict(value=1234567890)))
    p, report = qa(d)
    ck("overflow: counter display also blocks", p.returncode == 1 and has(report, "slot-overflow"), report)
    clean_without(scratch, "slot-overflow")


def case_number(scratch):
    d = reel(scratch, "number")
    edit_beats(d, lambda beats: beats[1].update(value=249))
    p, report = qa(d)
    ck("number: final counter differs from beat", p.returncode == 1 and has(report, "final-number"),
       (p.returncode, report, p.stderr))
    clean_without(scratch, "final-number")


def case_plain_scene(scratch):
    d = reel(scratch, "plain-scene")
    edit_beats(d, lambda beats: beats[1]["scene"].update(params=dict(value=1234567890)))
    _, report = qa(d)
    messages = [r["msg"] for r in report["checks"] if r.get("module") == "scene_fill_check"]
    ck("plain-scene: long counter names problem and fix", any("too long" in m and "Shorten" in m for m in messages), messages)
    ck("plain-scene: wrong number is readable", any("1,234,567,890" in m and "spoken" in m for m in messages), messages)
    ck("plain-scene: no internal scene wording", all("prefix +" not in m and "e+" not in m for m in messages), messages)


def case_row_values(scratch):
    checks = copy_checks(scratch)
    (checks / "zz_values.py").write_bytes(
        b'PHASE = "pre"\ndef run(ctx):\n'
        b'    return [dict(check="value", level=level, msg="A suggestion.", at=at)\n'
        b'            for level, at in [("warn", 1.23456), ("pass", True), ("odd", "1.2"), ("warn", None)]]\n')
    _, report = qa(reel(scratch, "row-values"), checks / "check.py")
    rows = [r for r in report["checks"] if r.get("module") == "zz_values"]
    ck("row-values: numeric at rounded, other values omitted, unknown levels warn", len(rows) == 4
       and rows[0].get("at") == 1.23 and all("at" not in r for r in rows[1:])
       and all(r["level"] == "warn" for r in rows), report)


def case_staleaids(scratch):
    d = reel(scratch, "staleaids")
    index = d / "work/qa/index.json"
    aids = dict(strips=[], contact="work/qa/contact.jpg", phone=None)
    write(index, aids)
    p, report = qa(d)
    ck("staleaids: pre omits existing aids", p.returncode == 0 and "aids" not in report, report)
    for phase in ("post", "all"):
        _, report = qa(d, CHECK, "--phase", phase)
        ck("staleaids: %s without a render omits aids" % phase, "aids" not in report, report)
    # Isolate the report's freshness gate from video decoding; the real runner
    # still discovers and executes a post module against the selected render.
    checks = copy_checks(scratch)
    for path in checks.glob("*.py"):
        if path.name != "check.py":
            path.unlink()
    (checks / "post_probe.py").write_bytes(
        b'PHASE = "post"\ndef run(ctx):\n'
        b'    return [dict(check="post-ran", level="warn", msg="The post check ran.")]\n')
    render = d / "renders/staleaids Master - 11.06.26.mp4"
    render.parent.mkdir()
    render.write_bytes(b"report gate fixture")
    os.utime(render, ns=(2_000_000_000, 2_000_000_000))
    for stamp, included in ((1_000_000_000, False), (2_000_000_000, True), (3_000_000_000, True)):
        os.utime(index, ns=(stamp, stamp))
        _, report = qa(d, checks / "check.py", "--phase", "post")
        ck("staleaids: post ran", any(r["check"] == "post-ran" for r in report.get("checks", [])), report)
        ck("staleaids: index mtime %d controls aids" % stamp,
           report.get("aids") == aids if included else "aids" not in report, report)
    write(d / "work/cuts.json", {})
    _, report = qa(d, checks / "check.py", "--phase", "post")
    ck("staleaids: unreadable context omits fresh aids", has(report, "inputs-unreadable")
       and "aids" not in report, report)


def copy_checks(scratch):
    """Copy the checks and their Python/scene dependencies with the plugin's relative layout."""
    dest = cs.fresh(scratch, "checks-copy") / "plugin"
    for rel in ("skills/_shared", "skills/_shared/checks", "skills/reel-canvas-build/scripts",
                "skills/reel-first-cuts/scripts", "skills/editor-doctor/scripts", "scripts"):
        target = dest / rel
        target.mkdir(parents=True, exist_ok=True)
        for source in (P / rel).glob("*.py"):
            shutil.copy2(source, target / source.name)
    target = dest / "scenes/counter"
    target.mkdir(parents=True)
    for name in ("scene.json", "scene.html"):
        shutil.copy2(P / "scenes/counter" / name, target / name)
    return dest / "skills/_shared/checks"


def case_crash(scratch):
    checks = copy_checks(scratch)
    (checks / "aaa_broken.py").write_bytes(
        b'PHASE = "pre"\ndef run(ctx):\n    raise RuntimeError("planted crash")\n')
    (checks / "aab_import_broken.py").write_bytes(b'raise RuntimeError("planted import crash")\n')
    (checks / "aac_post.py").write_bytes(
        b'PHASE = "post"\ndef run(ctx):\n    raise RuntimeError("post must not run in pre")\n')
    (checks / "zzz_after.py").write_bytes(
        b'from pathlib import Path\nPHASE = "pre"\ndef run(ctx):\n'
        b'    assert isinstance(ctx["reel_dir"], Path) and ctx["fps"] == 30\n'
        b'    assert ctx["cuts"]["fps"] == 30 and len(ctx["beats"]) == 2\n'
        b'    assert ctx["render"] is None\n'
        b'    return [dict(check="after", level="pass", msg="The later check ran.", at=0.5)]\n')
    d = reel(scratch, "crash")
    edit_beats(d, lambda beats: beats[0]["speech_anchor"].update(text="Wrong quote"))
    p, report = qa(d, checks / "check.py")
    for name in ("aaa_broken", "aab_import_broken"):
        ck("crash: " + name + " blocks", p.returncode == 1 and has(report, name + "-crashed"),
           (p.returncode, report, p.stderr))
        ck("crash: " + name + " report shape", any(h.get("check") == name + "-crashed"
           and h.get("module") == name and h.get("where") == name + ".py"
           and h.get("msg") == "The %s check broke before it finished. Claude will report this." % name
           for h in report.get("checks", [])), report)
        clean_without(scratch, name + "-crashed")
    ck("crash: real anchor module still ran", has(report, "anchor-lost"), report)
    ck("crash: post module skipped during pre", not has(report, "aac_post-crashed"), report)
    ck("crash: later module ran with context and seek time", any(h.get("module") == "zzz_after"
       and h.get("check") == "after" and h.get("at") == .5 for h in report.get("checks", [])), report)


def case_skip_lib(scratch):
    p, report = qa(reel(scratch, "skip-lib"))
    ck("skip-lib: clean exit", p.returncode == 0, p.stdout + p.stderr)
    ck("skip-lib: footage library produces no rows or crashes", bool(report.get("checks"))
       and not any(h.get("module") == "footage_check" or h.get("check") == "footage_check-crashed"
                   for h in report.get("checks", [])), report)


def case_hubshape(scratch):
    hub = (P / "skills/editor-doctor/references/hub.md").read_text(encoding="utf-8")
    qa_rows = [row for row in hub.splitlines() if row.startswith("|") and "`qa`" in row.split("|")[1]]
    ck("hubshape: QA routes to canvas build", len(qa_rows) == 1
       and "not built" not in qa_rows[0].lower() and "not-built" not in qa_rows[0].lower()
       and "editor-superengine:reel-canvas-build" in qa_rows[0], qa_rows)
    d = reel(scratch, "hubshape")
    edit_beats(d, lambda beats: beats[0]["speech_anchor"].update(text="Changed quote"))
    for name in ("clean", "block", "warn"):
        if name == "clean":
            p, report = qa(reel(scratch, "hubshape-clean"))
        else:
            if name == "warn":
                (d / "work/edit_map.json").unlink()
            p, report = qa(d)
        rows = report.get("checks", [])
        ck("hubshape: %s rows fit the hub" % name, bool(rows) and all(
            {"check", "level", "msg", "module"} <= h.keys() and h["level"] in {"block", "warn", "pass"}
            and isinstance(h["msg"], str) and bool(h["msg"]) and len(h["msg"].splitlines()) == 1 for h in rows), report)
        ck("hubshape: %s counts and exit agree" % name,
           report.get("blocks") == sum(h["level"] == "block" for h in rows)
           and report.get("warns") == sum(h["level"] == "warn" for h in rows)
           and p.returncode == int(report.get("blocks", 0) > 0), report)
        if name == "warn":
            ck("hubshape: warnings are counted", report.get("warns", 0) > 0, report)


CASES = {"clean": case_clean, "anchor": case_anchor, "overflow": case_overflow, "number": case_number,
         "crash": case_crash, "skip-lib": case_skip_lib, "hubshape": case_hubshape,
         "plain-scene": case_plain_scene, "row-values": case_row_values, "staleaids": case_staleaids}


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    print("python %s" % cs.PY)
    for name in [args.case] if args.case else CASES:
        print("-- " + name)
        try:
            CASES[name](scratch)
        except Exception as e:
            ck(name + ": completed", False, str(e))
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
