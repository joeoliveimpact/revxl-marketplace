#!/usr/bin/env python3
"""X6 synthetic proofs. The lane runs these with the installed editor Python.

Usage: x6_riders_test.py <scratch> --case NAME|all
Each case uses at most 640 px / 10 s media and must finish within 150 s.
"""
import argparse
import contextlib
from fractions import Fraction
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs
import qa_test as qa
from editor_test_state import isolated_home
from win_encoding import ensure_utf8_output

P = HERE.parents[1] / "plugins/editor-superengine"
SHARED = P / "skills/_shared"
CUT = P / "skills/reel-first-cuts/scripts"
GRADE = P / "skills/reel-grade/scripts"
CANVAS = P / "skills/reel-canvas-build/scripts"
sys.path[:0] = [str(SHARED), str(CUT), str(GRADE), str(CANVAS)]
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)), flush=True)
    if not ok:
        fails.append(name)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def mod(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sh(cmd):
    return subprocess.run(list(map(str, cmd)), env=cs.ENV, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=140)


def script(path, *args):
    return sh([cs.PY, "-X", "utf8", "-I", path, *args])


def ff(*args):
    p = sh([cs.rt.tool("ffmpeg"), "-y", "-v", "error", *args])
    if p.returncode:
        raise RuntimeError("fixture encode failed: " + p.stderr[-600:])


def ctx(d):
    return mod(SHARED / "checks/check.py").build_context(d)


def cut_clip(d, src, words, clips, out=None):
    write(d / "clips.json", clips)
    return script(CUT / "clip_cut.py", src, "--words", words, "--clips", d / "clips.json",
                  "--out", out or d / "clips")


def case_clip_end(scratch):
    d = cs.fresh(scratch, "clip-end")
    cs.need_ram()
    src, words = cs.synth_words(d)
    for item in [dict(name="late", start=5, end=9), dict(name="late2", **{"from": 5, "to": 12}),
                 dict(name="../escape", start=1, end=2), dict(name="bad\\name", start=1, end=2)]:
        p = cut_clip(d, src, words, [item])
        ck("clip-end: unsafe range/name refused before writing", p.returncode == 2
           and not (d / "clips").exists(), p.stdout + p.stderr)
    p = cut_clip(d, src, words, [dict(name="early", start=1, end=2), dict(name="late", start=5, end=9)])
    ck("clip-end: preflight covers the entire batch", p.returncode == 2 and not (d / "clips").exists(), p.stdout)
    p = cut_clip(d, src, words, [dict(name="early", start=1, end=2)])
    target = d / "clips/early/source.mp4"
    ck("clip-end: valid seconds pass", p.returncode == 0 and target.is_file(), p.stdout + p.stderr)
    if target.is_file():
        before = target.read_bytes()
        p = cut_clip(d, src, words, [dict(name="early", start=1, end=2)])
        ck("clip-end: existing folder refused, original kept", p.returncode == 2 and target.read_bytes() == before, p.stdout)


def case_clip_words(scratch):
    d = cs.fresh(scratch, "clip-words")
    cs.need_ram()
    src, words = cs.synth_words(d)
    docs = [cs.load(words), {"words": [{"word": w, "start": s, "end": e} for w, s, e in cs.WORDS]},
            [{"i": i, "text": w, "start": s, "end": e} for i, (w, s, e) in enumerate(cs.WORDS)]]
    for i, doc in enumerate(docs):
        wp = d / ("words-%d.json" % i)
        write(wp, doc)
        p = cut_clip(d, src, wp, [{"name": "short", "from": 1, "to": 3}], d / ("out-%d" % i))
        folder = d / ("out-%d/short" % i)
        ws = cs.load(folder / "words_raw.json")
        ck("clip-words: adapter %d and retiming" % i, p.returncode == 0 and len(ws) == 3
           and ws[0] == dict(i=0, text="can", start=.15, end=.45)
           and ws[-1]["text"] == "And" and ws[-1]["end"] == 1.95, (p.stdout, p.stderr, ws))
        if p.returncode:
            continue
        media = folder / "source.mp4"
        j = json.loads(sh([cs.rt.tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", media]).stdout)
        ck("clip-words: duration within one frame", abs(float(j["format"]["duration"]) - 2.10) <= 1 / 30, j)
        x, sr = cs.pcm(media)
        for word in (ws[0], ws[-1]):
            samples = x[round((word["start"] + .04) * sr):round((word["end"] - .04) * sr)]
            ck("clip-words: edge word retains tone", bool(samples) and sum(v * v for v in samples) / len(samples) > .002)
        ck("clip-words: encode generation disclosed once", p.stdout.count("info: encode generations +1 (re-encode crf 16)") == 1, p.stdout)
    # A Short whose last word ends inside the padding of the recording's end is kept,
    # its padded end held at the recording's end (only the listed range is refused past the end).
    last = len(cs.WORDS) - 1
    write(d / "clips-tail.json", [{"name": "tail", "from": last - 1, "to": last}])
    p = script(CUT / "clip_cut.py", src, "--words", d / "words-0.json", "--clips", d / "clips-tail.json",
               "--out", d / "out-tail", "--pad", "0.8")
    ck("clip-words: last word near the recording's end is kept, end held at the end",
       p.returncode == 0 and (d / "out-tail/tail/source.mp4").is_file(), (p.stdout, p.stderr))


def case_burned(scratch):
    d = cs.fresh(scratch, "burned")
    cs.need_ram()
    font = (P / "runtime/fonts/Inter-Regular.woff2").as_posix().replace(":", "\\:")
    for name, text in (("clean", False), ("planted", True)):
        src = d / (name + ".mp4")
        vf = "noise=alls=2:allf=t+u"
        if text:
            vf += f",drawtext=fontfile='{font}':text='WORDS STAY HERE':fontsize=32:fontcolor=white:borderw=3:bordercolor=black:x=(w-tw)/2:y=h*0.7:enable='between(t,2,5)'"
        ff("-f", "lavfi", "-i", "color=c=0x465565:s=360x640:r=30:d=6", "-vf", vf,
           "-an", "-c:v", "libx264", "-preset", "ultrafast", src)
        work = d / name / "work"
        p = script(CUT / "caption_scan.py", src, "--work", work)
        doc = cs.load(work / "intake.json")
        ck("burned: %s exits correctly" % name, p.returncode == (3 if text else 0)
           and doc.get("burned_in") is text, p.stdout + p.stderr + str(doc))
        ck("burned: full 1 fps sheet exists", (work / "intake-sheet.png").is_file())
        if text:
            ck("burned: mid-clip words located", len(doc.get("flagged_s", [])) >= 2
               and all(2 <= t <= 5 for t in doc["flagged_s"]), doc)


def case_silence(scratch):
    d = cs.fresh(scratch, "silence")
    cuts = dict(fps=30, speed=1, segments=[dict(src_in_f=0, src_out_f=180, out_in_f=0, out_out_f=180)])
    write(d / "work/cuts.json", cuts)
    for late, want in ((4.9, True), (3.4, False)):  # 3.5 s kept silence asks; 2.0 s does not
        write(d / "work/edit_map.json", dict(words=[dict(start=1, end=1.4), dict(start=late, end=late + .4)]))
        p = script(CUT / "long_silence.py", d / "work", "--json")
        doc = cs.load(d / "work/long-silences.json")
        ck("silence: ask only for long kept silence", p.returncode == 0 and bool(doc["silences"]) == want
           and (("linger on the last caption" in p.stdout and "title card" in p.stdout and "cut it" in p.stdout
                 and "1.40" in p.stdout) if want else not p.stdout.strip()), (p.stdout, p.stderr, doc))
    write(d / "work/edit_map.json", dict(words=[dict(start=1, end=1.4), dict(start=4.9, end=5.3)]))
    for choice in ("linger", "title", "cut"):
        write(d / "tweak-selection.json", dict(silences=[dict(start=1.44, end=4.9, choice=choice)]))
        p = script(CUT / "long_silence.py", d / "work", "--json")
        gaps = cs.load(d / "work/long-silences.json")["silences"]
        ck("silence: saved " + choice + " answers the gap", p.returncode == 0 and "the client chose" in p.stdout
           and "?" not in p.stdout and gaps[0].get("choice") == choice, (p.stdout, gaps))
    for broken in ('{', '[]', '{"silences": null}', '{"silences": [null, {"start": "bad", "choice": "cut"}]}',
                   json.dumps(dict(silences=[dict(start=10 ** 400, choice="cut")]))):
        (d / "tweak-selection.json").write_bytes(broken.encode("utf-8"))
        p = script(CUT / "long_silence.py", d / "work", "--json")
        ck("silence: broken selection still asks", p.returncode == 0 and "cut it?" in p.stdout
           and "choice" not in cs.load(d / "work/long-silences.json")["silences"][0], p.stdout)
    (d / "tweak-selection.json").unlink()
    # Removed source time cannot create a false ask; speed is output time.
    write(d / "work/cuts.json", dict(fps=30, speed=2, segments=[
        dict(src_in_f=0, src_out_f=60, out_in_f=0, out_out_f=30),
        dict(src_in_f=120, src_out_f=180, out_in_f=30, out_out_f=60)]))
    p = script(CUT / "long_silence.py", d / "work")
    ck("silence: discarded time and speed respected", p.returncode == 0 and not p.stdout.strip(), p.stdout + p.stderr)
    write(d / "work/cuts.json", dict(fps=30, speed=1, takes={"1": {"work": "work"}, "2": {"work": "work/take2"}},
          segments=[dict(take=1, src_in_f=0, src_out_f=60, out_in_f=0, out_out_f=60),
                    dict(take=2, src_in_f=0, src_out_f=120, out_in_f=60, out_out_f=180)]))
    write(d / "work/edit_map.json", dict(words=[dict(start=.5, end=1)]))
    write(d / "work/take2/edit_map.json", dict(words=[dict(start=1, end=1.4), dict(start=3, end=3.4)]))
    p = script(CUT / "long_silence.py", d / "work")
    ck("silence: each take uses its own word map", p.returncode == 0 and not p.stdout.strip(), p.stdout + p.stderr)


def case_covered(scratch):
    m = mod(SHARED / "checks/covered_words.py")
    ck("covered: function word can rank as pass", m.verdict("of", "a shelf of useful books", 85) == "pass")
    ck("covered: meaning word escalates", m.verdict("building", "building lasting habits", 85) == "escalate")
    ck("covered: small coverage passes", m.verdict("building", "building lasting habits", 40) == "pass")
    ck("covered: adjacent half-covered words escalate", m.verdict("of", "a shelf of useful books", 65, [55]) == "escalate")
    ck("covered: key letters escalate", m.verdict({"text": "of", "key_letters": True}, "a shelf of books", 70) == "escalate")
    ck("covered: library cannot weaken layout gate", not hasattr(m, "PHASE"))


def case_eye(scratch):
    d = qa.reel(scratch, "eye")
    m = mod(SHARED / "checks/eye_test_check.py")
    ck("eye: no file stays silent", m.run(ctx(d)) == [])
    answers = [dict(id=k, answer="yes") for k in ("poster", "confident", "hierarchy", "handshake", "rests")]
    write(d / "work/eye-test.json", dict(answers=answers))
    ck("eye: five yes answers stay silent", m.run(ctx(d)) == [])
    answers[0]["answer"] = "no"
    write(d / "work/eye-test.json", dict(answers=answers))
    rows = m.run(ctx(d))
    ck("eye: no warns, never blocks", len(rows) == 1 and all(r["level"] == "warn" for r in rows), rows)
    write(d / "work/eye-test.json", dict(answers=answers[1:] + [answers[1]]))
    rows = m.run(ctx(d))
    ck("eye: duplicate and missing ids warn", len(rows) == 2 and all(r["level"] == "warn" for r in rows), rows)


def video_packets(path):
    p = sh([cs.rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=time_base:packet=pts,flags", "-of", "json", path])
    p.check_returncode()
    return json.loads(p.stdout)


def grid_ok(path, rate):
    j = video_packets(path)
    tb, fps = Fraction(j["streams"][0]["time_base"]), Fraction(str(rate))
    pts = sorted(int(p["pts"]) for p in j["packets"])
    # Integer equality via Fraction; a rounded millisecond clock cannot pass.
    return bool(pts) and all(Fraction(t) * tb * fps == i for i, t in enumerate(pts))


def gop_ok(path):
    j = video_packets(path)
    tb = Fraction(j["streams"][0]["time_base"])
    pts = sorted(int(p["pts"]) for p in j["packets"])
    keys = sorted(int(p["pts"]) for p in j["packets"] if "K" in p.get("flags", ""))
    edges = keys + ([pts[-1]] if pts else [])
    return bool(keys) and keys[0] == pts[0] and all((b - a) * tb < Fraction(105, 100)
                                                               for a, b in zip(edges, edges[1:]))


def quiet_run(x, floor=1e-3):
    """Longest run of near-silent samples (below -60 dBFS). AAC priming decodes as
    near-silence, not exact zeros, so an exact-zero count misses it."""
    run_ = worst = 0
    for v in x:
        run_ = run_ + 1 if abs(v) < floor else 0
        worst = max(worst, run_)
    return worst


def priming_ok(path, splices):
    x, sr = cs.pcm(path)
    limit = round(0.002 * sr)
    for t in splices:
        window = x[max(0, round((t - .05) * sr)):round((t + .05) * sr)]
        if len(window) < .08 * sr or quiet_run(window) >= limit:
            return False
    return True


def case_frames(scratch):
    d = cs.fresh(scratch, "frames")
    cs.need_ram()
    outputs = []
    for label in ("30", "30000/1001", "60"):
        rate = Fraction(label)
        src = d / ("source-" + label.replace("/", "-") + ".mov")
        ff("-f", "lavfi", "-i", "color=c=gray:s=360x640:r=%s:d=4" % label,
           "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
           "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "pcm_s16le", "-shortest", src)
        def probe_at_rate(source, work):
            p = script(CUT / "probe.py", source, "-o", work, "--out-rate", str(float(rate)))
            ck("frames: %s probe uses requested output rate" % label, p.returncode == 0, p.stderr)
            return p.returncode == 0

        with patch.object(cs, "probe", side_effect=probe_at_rate):
            w, cuts = cs.plan(d, "rate-" + label.replace("/", "-"), src, [(0, 1.5), (2, 3.5)], 1)
        if not cuts:
            ck("frames: %s plan exists" % label, False)
            continue
        # Exercise the production float-rate path, then judge it on the exact
        # requested rational grid. Never round PTS to make a failure pass.
        try:
            rc, err, master, got = cs.tiny_render(w, src)
            ck("frames: %s production render and frame count" % label,
               rc == 0 and got == cuts["segments"][-1]["out_out_f"], err)
            ck("frames: %s exact PTS grid" % label, grid_ok(master, rate), cuts["fps"])
            ck("frames: %s GOP <= 1.05 s" % label, gop_ok(master))
            joins = [s["out_in_f"] / float(rate) for s in cuts["segments"][1:]]
            ck("frames: %s no splice priming gap" % label, priming_ok(master, joins))
            outputs.append(master)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            ck("frames: %s production render" % label, False, str(e))
    if not outputs:
        return
    off = d / "off-grid.mp4"
    ff("-i", outputs[0], "-c", "copy", "-video_track_timescale", "1000", off)
    ck("frames: planted millisecond clock FAILS grid checker", not grid_ok(off, 30))
    if len(outputs) > 1:
        off2997 = d / "off-grid-2997.mp4"
        ff("-i", outputs[1], "-c", "copy", "-video_track_timescale", "1000", off2997)
        ck("frames: 29.97 render passes the exact grid", grid_ok(outputs[1], Fraction(30000, 1001)))
        ck("frames: planted 29.97 cut off the frame grid FAILS grid checker",
           not grid_ok(off2997, Fraction(30000, 1001)))
    gop105 = d / "gop-105.mp4"
    ff("-f", "lavfi", "-i", "color=c=gray:s=360x640:r=20:d=4", "-c:v", "libx264", "-g", "21",
       "-keyint_min", "21", "-sc_threshold", "0", gop105)
    ck("frames: planted keyframe spacing of exactly 1.05 s FAILS GOP checker", not gop_ok(gop105))
    gop = d / "long-gop.mp4"
    ff("-f", "lavfi", "-i", "color=c=gray:s=360x640:r=30:d=4", "-c:v", "libx264", "-g", "60",
       "-keyint_min", "60", "-sc_threshold", "0", gop)
    ck("frames: planted two-second GOP FAILS GOP checker", not gop_ok(gop))
    # ADTS retains each independently encoded piece's priming samples. Joining
    # these packets, rather than one continuous encode, leaves a splice gap.
    parts = []
    for i in range(2):
        part = d / ("piece-%d.aac" % i)
        ff("-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
           "-c:a", "aac", "-b:a", "192k", "-f", "adts", part)
        parts.append(part)
    joined = d / "joined.aac"
    joined.write_bytes(b"".join(p.read_bytes() for p in parts))
    piece_samples, piece_rate = cs.pcm(parts[0])
    join = len(piece_samples) / piece_rate
    ck("frames: separately encoded AAC pieces FAIL priming checker", not priming_ok(joined, [join]),
       "unpadded independently encoded packets; splice %.6f s" % join)


def case_grade_bounds(scratch):
    m = mod(GRADE / "grade_bounds.py")
    values = dict(exposure=.9, temp=-.8, tint=.7, con=.7, sat=-.8)
    held, notes = m.clamp(values)
    ck("grade-bounds: values held in board units", held == dict(exposure=.35, temp=-.4, tint=.25, con=.3, sat=-.3)
       and len(notes) == 5 and values["exposure"] == .9, (held, notes))
    good = dict(exposure=.1, temp=.2, sat=.1)
    ck("grade-bounds: in-bounds silent", m.clamp(good) == (good, []))
    g = mod(GRADE / "grade_from_selection.py")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        corr, problem = g.correction_of(dict(correction=values))
    ck("grade-bounds: board selection uses clamp and says why", problem is None and corr == held
       and "held" in out.getvalue(), out.getvalue())
    ck("grade-bounds: invalid board input still refused", g.correction_of(dict(correction={"exposure": 2}))[0] is None)


def case_sheet(scratch):
    from PIL import Image
    d = cs.fresh(scratch, "sheet")
    cs.need_ram()
    src, after = d / "before.mp4", d / "after.mp4"
    ff("-f", "lavfi", "-i", "color=c=0xb6856b:s=180x320:r=30:d=3", "-c:v", "libx264", src)
    ff("-i", src, "-vf", "eq=brightness=0.15", "-c:v", "libx264", after)
    out = d / "sheet.png"
    p = script(GRADE / "before_after_sheet.py", src, after, "--out", out, "--tile", "180")
    ck("sheet: PNG produced", p.returncode == 0 and out.is_file(), p.stdout + p.stderr)
    if out.is_file():
        with Image.open(out) as im:
            ck("sheet: three before/after pairs", im.size == (360, 960) and all(
                im.getpixel((90, y)) != im.getpixel((270, y)) for y in (160, 480, 800)), im.size)
    out.unlink(missing_ok=True)
    p = script(GRADE / "before_after_sheet.py", src, d / "missing.mp4", "--out", out)
    ck("sheet: missing comparison refused without output", p.returncode != 0 and not out.exists(), p.stdout + p.stderr)


def case_render_skip(scratch):
    d = qa.reel(scratch, "render-skip")
    m = mod(CANVAS / "render_skip.py")
    output = d / "renders/REEL_018 Preview 720p - 11.07.26.mp4"

    def rendered(*args, **kwargs):
        output.parent.mkdir(exist_ok=True)
        output.write_bytes(b"successful render")
        # Actual compose writes generated caption/track files. They must not
        # poison the next fingerprint.
        write(d / "work/scale_track.json", {"keys": []})
        return dict(out=output.relative_to(d).as_posix())

    with isolated_home(), patch.object(m.compose, "render", side_effect=rendered) as call:
        m.render(d, "preview")
        ck("render-skip: first render called", call.call_count == 1)
        call.reset_mock()
        m.render(d, "preview")
        ck("render-skip: unchanged skips", call.call_count == 0)
        doc = cs.load(d / "beat-map-selection.json")
        doc["beats"][0]["value"] = 42
        write(d / "beat-map-selection.json", doc)
        m.render(d, "preview")
        ck("render-skip: changed beat renders once", call.call_count == 1)
        call.reset_mock()
        # Referenced media can have any valid container suffix, including a
        # path otherwise excluded as an output directory.
        media = d / "renders/broll.m4v"
        media.write_bytes(b"first media")
        doc["beats"][1]["broll"] = dict(src="renders/broll.m4v")
        write(d / "beat-map-selection.json", doc)
        m.render(d, "preview")
        call.reset_mock()
        media.write_bytes(b"changed referenced media")
        m.render(d, "preview")
        ck("render-skip: referenced B-roll change renders", call.call_count == 1)
        call.reset_mock()
        (d / "credits.txt").write_bytes(b"Attribution required by this licence.\n")
        m.render(d, "preview")
        ck("render-skip: credit change invalidates reuse", call.call_count == 1)
        call.reset_mock()
        m.render(d, "preview", force=True)
        ck("render-skip: force renders once", call.call_count == 1)
        call.reset_mock()
        output.unlink()
        m.render(d, "preview")
        ck("render-skip: missing output renders", call.call_count == 1)
        before = (d / "work/.render-fp.json").read_bytes()
        call.side_effect = RuntimeError("planted render failure")
        try:
            m.render(d, "preview", force=True)
        except RuntimeError:
            pass
        ck("render-skip: failed render cannot save state", (d / "work/.render-fp.json").read_bytes() == before)
        call.side_effect = rendered
        m.render(d, "master")
        call.reset_mock()
        output.write_bytes(b"preview replaced since the approved master")
        m.render(d, "master")
        ck("render-skip: replaced approval preview forces render", call.call_count == 1)


def case_cta(scratch):
    d = qa.reel(scratch, "cta")
    m = mod(SHARED / "checks/cta_reminder_check.py")
    ck("cta: absent stays silent", m.run(ctx(d)) == [])
    reminder = d / "cta-reminder.json"
    write(reminder, dict(at_s=2.8, hold_s=.5, gain=.1))
    ck("cta: reminder at 70 % with audio at 10 % stays silent", m.run(ctx(d)) == [])
    html = (P / "scenes/cta-reminder/scene.html").read_text(encoding="utf-8").lower()
    ck("cta: reminder scene carries no sound of its own", "<audio" not in html and "<video" not in html)
    write(reminder, dict(at_s=.5, hold_s=.5, gain=.1))
    ck("cta: early placement warns", [r["level"] for r in m.run(ctx(d))] == ["warn"])
    write(reminder, dict(at_s=2.5, hold_s=.5, gain=.11))
    ck("cta: loud reminder blocks", any(r["level"] == "block" for r in m.run(ctx(d))))
    write(reminder, dict(at_s=2.5, hold_s=.5, gain=0))
    doc = cs.load(d / "beat-map-selection.json")
    doc["beats"][1]["scene"] = dict(id="cta-end-card", slots={}, params={})
    write(d / "beat-map-selection.json", doc)
    ck("cta: end-card overlap blocks", any(r["check"] == "cta-overlap" and r["level"] == "block" for r in m.run(ctx(d))))
    doc["beats"][1]["scene"] = None
    doc["word_marks"] = [dict(w=0, mark="cta")]
    write(d / "beat-map-selection.json", doc)
    write(d / "work/edit_map.cut.json", dict(words=[dict(word="comment", start=2.4, end=2.8)]))
    ck("cta: word-mark overlap blocks", any(r["check"] == "cta-overlap" for r in m.run(ctx(d))))
    # The document choice wins even when an older side file is still present.
    doc["word_marks"] = []
    doc["cta_reminder"] = dict(at_s=2.8, hold_s=.5, gain=0, keyword="NOTES")
    write(d / "beat-map-selection.json", doc)
    write(reminder, dict(at_s=2.5, hold_s=.5, gain=.15))
    ck("cta: document overrides loud side file", m.run(ctx(d)) == [])
    reminder.unlink()
    ck("cta: document alone stays silent", m.run(ctx(d)) == [])
    doc["cta_reminder"]["gain"] = .15
    write(d / "beat-map-selection.json", doc)
    ck("cta: document gain blocks", any(r["check"] == "cta-gain" for r in m.run(ctx(d))))
    doc["cta_reminder"] = None
    write(d / "beat-map-selection.json", doc)
    write(reminder, dict(at_s=2.8, hold_s=.5, gain=0))
    ck("cta: present invalid key cannot fall back", any(r["check"] == "cta-input" for r in m.run(ctx(d))))
    del doc["cta_reminder"]
    write(d / "beat-map-selection.json", doc)
    ck("cta: absent key falls back", m.run(ctx(d)) == [])


def case_hold(scratch):
    d = qa.reel(scratch, "hold")
    m = mod(SHARED / "checks/hold_gap_check.py")
    ck("hold: clean QA reel stays silent", m.run(ctx(d)) == [])
    doc = cs.load(d / "beat-map-selection.json")
    doc["beats"][0]["end_f"] = 75
    doc["beats"][1]["start_f"] = 75
    write(d / "beat-map-selection.json", doc)
    rows = m.run(ctx(d))
    ck("hold: 2.5 s without reason warns", len(rows) == 1 and rows[0]["level"] == "warn", rows)
    write(d / "work/holds.json", dict(holds=[dict(at_f=30, reason="Let the viewer read the comparison.")]))
    ck("hold: reason within gap stays silent", m.run(ctx(d)) == [])
    write(d / "work/holds.json", dict(holds=[dict(at_f=100, reason="This is a different gap.")]))
    ck("hold: unrelated reason cannot waive gap", len(m.run(ctx(d))) == 1)
    doc["holds"] = [dict(at_f=0, reason="Let the viewer read the comparison.")]
    write(d / "beat-map-selection.json", doc)
    ck("hold: document reason joins side file", m.run(ctx(d)) == [])
    (d / "work/holds.json").unlink()
    ck("hold: document alone explains gap", m.run(ctx(d)) == [])
    doc["holds"] = [dict(at_f=100, reason="A different gap.")]
    write(d / "beat-map-selection.json", doc)
    write(d / "work/holds.json", dict(holds=[dict(at_f=30, reason="Read the comparison.")]))
    ck("hold: side file joins unrelated document reason", m.run(ctx(d)) == [])
    # A malformed source must not discard a valid reason from the other source.
    write(d / "work/holds.json", dict(holds=None))
    doc["holds"] = [dict(at_f=0, reason="Read the comparison.")]
    write(d / "beat-map-selection.json", doc)
    ck("hold: malformed side file preserves document reason", m.run(ctx(d)) == [])
    for bad in (dict(at_f=True, reason="Read"), dict(at_f=0, reason=" "), dict(at_f=75, reason="After gap")):
        doc["holds"] = [bad]
        write(d / "beat-map-selection.json", doc)
        ck("hold: invalid or end-boundary reason cannot waive gap", len(m.run(ctx(d))) == 1, bad)


def case_style_intake(scratch):
    m = mod(SHARED / "style_intake.py")
    colours = [dict(hex="#123456", meaning="Body text")]
    with isolated_home() as home:
        m.save("reel-018", "client", colours)
        doc = m.read("reel-018")
        ck("style-intake: origin and meaning persist", doc == dict(origin="client", colours=colours)
           and (home / "styles/reel-018.intake.json").is_file(), doc)
        ck("style-intake: own readback", "client" in m.readback("reel-018") and "Body text" in m.readback("reel-018"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            m.save("reel-018", "reference", colours * 6)
        ck("style-intake: six warn and ask, all kept", "which" in out.getvalue().lower()
           and len(m.read("reel-018")["colours"]) == 6, out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            m.save("reel-018", "default", colours)
        ck("style-intake: <= five no warning", "warn" not in out.getvalue().lower(), out.getvalue())


def case_storyboard(scratch):
    d = qa.reel(scratch, "storyboard")
    m = mod(SHARED / "checks/storyboard_check.py")
    ck("storyboard: absent stays silent", m.run(ctx(d)) == [])
    path = d / "storyboard.json"
    beats = {"b_002": {"in": "slide", "out": "fade", "ease_in": "soft", "ease_out": "soft"},
             "b_001": {"in": "fade", "out": "hold", "ease_in": "soft", "ease_out": "soft"}}
    write(path, dict(beats=beats))
    rows = m.run(ctx(d))
    ck("storyboard: mismatch one suggestion, beat order", len(rows) == 1 and rows[0]["level"] == "warn"
       and "suggestion" in rows[0]["msg"].lower(), rows)
    beats["b_001"]["out"] = "slide"
    write(path, dict(beats=beats))
    ck("storyboard: matching transforms stay silent", m.run(ctx(d)) == [])
    selection = d / "sketches-selection.json"
    beats["b_001"]["out"] = "hold"
    write(selection, dict(storyboard=dict(beats=beats)))
    rows = m.run(ctx(d))
    ck("storyboard: doc mismatch wins over matching side file", len(rows) == 1 and rows[0]["level"] == "warn", rows)
    write(path, dict(beats=beats))
    beats["b_001"]["out"] = "slide"
    write(selection, dict(storyboard=dict(beats=beats)))
    ck("storyboard: matching doc wins over conflicting side file", m.run(ctx(d)) == [])
    write(selection, {})
    ck("storyboard: absent key falls back", len(m.run(ctx(d))) == 1)
    import beat_schema
    doc = dict(schema=1, reel=d.name, rough=None, directions=[], pick=None, sketches=[], note="", sent_at=None,
               locked_at=None, storyboard=dict(beats=beats))
    beat_map = cs.load(d / "beat-map-selection.json")
    ck("storyboard: schema accepts optional fields", beat_schema.sketches_problems(doc, beat_map) == [])
    for bad in ({"unknown": {"in": "fade"}}, {"b_001": {"unknown": "fade"}}, {"b_001": {"in": 4}},
                {"b_001": {"in": " "}}, {"b_001": {"in": "x" * 25}}):
        doc["storyboard"] = dict(beats=bad)
        ck("storyboard: schema rejects bad beat or field", bool(beat_schema.sketches_problems(doc, beat_map)), bad)


CASES = {"clip-end": case_clip_end, "clip-words": case_clip_words, "burned": case_burned,
         "silence": case_silence, "covered": case_covered, "eye": case_eye, "frames": case_frames,
         "grade-bounds": case_grade_bounds, "sheet": case_sheet, "render-skip": case_render_skip,
         "cta": case_cta, "hold": case_hold, "style-intake": case_style_intake, "storyboard": case_storyboard}


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--case", choices=[*CASES, "all"], default="all")
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    for name in CASES if a.case == "all" else [a.case]:
        start = time.monotonic()
        try:
            CASES[name](a.scratch)
        except Exception as e:
            ck(name + ": ran without crashing", False, "%s: %s" % (type(e).__name__, e))
        elapsed = time.monotonic() - start
        ck(name + ": under 150 s", elapsed < 150, elapsed)
    print("X6: %d failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
