"""S12 pro-editor hand-off proof.

Usage: <editor python> -X utf8 -I tests/editor/handoff_test.py [--case NAME]
Set EDITOR_SE_HOME to the editor state. Cases: selftest, package, fcpxml,
fcp7_srt, gate, hub, steps, rcheck, layout-switch, no-scale-track, hook-long,
hook-named, hook-old-ok; default all. Prints PASS/FAIL per check.
Package uses the shared heavy lock; missing lock exits 75. Live Resolve
proof runs separately through its native MCP. EDITOR_SE_TEST_TAKE is hashed read only
before and after every case. All generated media stays in a temporary folder.
"""
import argparse
import ast
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugins/editor-superengine"
SCRIPTS = PLUGIN / "skills/pro-editor-handoff/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))
from editor_test_state import isolated_home
import build_edit as build
import segments_to_fcpxml as fcpx
import export_edit as legacy

rt = fcpx.rt
CASES = ("selftest", "package", "fcpxml", "fcp7_srt", "gate", "hub", "steps", "rcheck",
         "layout-switch", "no-scale-track", "hook-long", "hook-named", "hook-old-ok")
HEAVY = Path("C:/Workspaces/Content Studio/output/scripts/heavy_lock.py")
FAILS = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f": {detail}" if detail and not ok else ""), flush=True)
    if not ok:
        FAILS.append(name)
    return ok


def run(args, cwd=None, env=None, timeout=1200):
    return subprocess.run([str(a) for a in args], cwd=cwd, env=env or rt.python_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def command(script, *args, cwd=None, env=None):
    return run([sys.executable, "-X", "utf8", "-I", "-B", script, *args], cwd=cwd, env=env)


def must(args):
    p = run(args)
    if p.returncode:
        raise RuntimeError((p.stdout + p.stderr)[-800:])


def picture(master, rate="30"):
    master.parent.mkdir(parents=True, exist_ok=True)
    seconds = str(float(Fraction(84) / Fraction(rate)))
    must([rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
          f"testsrc2=size=1080x1920:rate={rate}:duration={seconds}", "-f", "lavfi", "-i",
          f"sine=frequency=1000:sample_rate=48000:duration={seconds}", "-map", "0:v", "-map", "1:a",
          "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-threads", "2", "-pix_fmt", "yuv420p",
          "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
          "-frames:v", "84", "-r", rate, "-ac", "2", "-c:a", "aac", "-b:a", "192k", master])


def fixture(root, rate="30"):
    """Original media, two output-frame cuts, approved preview, and saved style."""
    reel = root / "videos/REEL_A"
    master = reel / "work/renders/master-100x.mp4"
    picture(master, rate)
    build.save(reel / "work/cuts.json", {"fps": float(Fraction(rate)), "speed": 1, "segments": [
        {"src_in_f": 0, "src_out_f": 42, "out_in_f": 0, "out_out_f": 42},
        {"src_in_f": 50, "src_out_f": 92, "out_in_f": 42, "out_out_f": 84}]})
    words = [{"id": f"w_{i:04d}", "word": word, "start": start, "end": start + .18}
             for i, (word, start) in enumerate(zip("Clear cuts make edits easy to finish today".split(),
                                                   (.1, .4, .7, 1., 1.6, 1.9, 2.2, 2.5)))]
    build.save(reel / "work/edit_map.cut.json", {"words": words})
    style = {"style": "punch-in", "punch_scale": 1.18, "moves": {"opening_settle": False, "follow_cam": False,
             "word_punches": {"preset": "subtle", "shape": "eased", "picks": [5]}}}
    beats = [{"id": f"b_00{i + 1}", "start_f": a, "end_f": b,
              "speech_anchor": {"text": " ".join(w["word"] for w in words[w0:w1 + 1]), "w0": w0, "w1": w1},
              "layout": "full", "value": None, "scene": None, "broll": None, "transition": None}
             for i, (a, b, w0, w1) in enumerate(((0, 42, 0, 3), (42, 84, 4, 7)))]
    build.save(root / "state/styles/default.json", style)
    build.save(reel / "beat-map-selection.json", {"schema": 1, "reel": reel.name, "fps": float(Fraction(rate)),
               "words": "work/edit_map.cut.json", "beats": beats, "word_marks": [], "proposed": {}, "notes": {},
               "needs": "", "sent_at": "2026-11-06T10:00:00Z", "edit_style": style, "caption_style": {"style": "clean"}})
    build.save(reel / "work/captions.json", {"chunks": [
        {"i": 0, "start_f": 3, "end_f": 32, "text": "Clear cuts"},
        {"i": 1, "start_f": 34, "end_f": 60, "text": "Easy edits"},
        {"i": 2, "start_f": 65, "end_f": 82, "text": "Finish today"}]})
    for folder, name, duration, frequency in (("beds", "bed.wav", 5, 220), ("sfx", "hit.wav", .4, 700)):
        p = reel / folder / name
        p.parent.mkdir()
        must([rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
              f"aevalsrc=0.15*sin(2*PI*{frequency}*t)|0.1*sin(2*PI*{frequency * 2}*t):s=48000:d={duration}", p])
    build.save(reel / "sound-selection.json", {"cues": [
        {"id": "hit", "file": "hit.wav", "time": 1.01335, "peak_s": .0833, "gain_db": -8,
         "length_s": .3, "end_mode": "fade", "fade_out_s": .05},
        {"id": "early", "file": "hit.wav", "time": .1, "peak_s": .2, "gain_db": -10,
         "length_s": .3, "end_mode": "cut", "fade_out_s": .05}]})
    build.save(reel / "sound/placement.json", {"fps": float(Fraction(rate)), "sr": 48000,
        "bed": {"source": "beds/bed.wav", "entry_s": .2, "exit_s": 2.6, "offset_s": .4,
                "fade_in_s": .1, "fade_out_s": .2, "stops": [], "level": {"gain_db_applied": -12},
                "duck": {"keyframes": [{"t_s": .2, "gain_db": 0}, {"t_s": .5, "gain_db": -6},
                                       {"t_s": 2, "gain_db": -6}, {"t_s": 2.6, "gain_db": 0}]}},
        "cues": [{"id": "hit", "start_sample": 43200, "lane": 0},
                 {"id": "early", "start_sample": 0, "lane": 1}]})
    build.save(root / "editor/editor.config.json", {"nle": "resolve"})
    preview = reel / f"renders/REEL_A Preview 720p - {datetime.now().strftime('%m.%d.%y')}.mp4"
    preview.parent.mkdir()
    shutil.copyfile(master, preview)
    past = time.time() - 5  # the client OKs after watching; a same-instant OK races the file clock on Windows
    os.utime(preview, (past, past))
    build.save(reel / "work/render-ok.json", {"ok_at": datetime.now().astimezone().isoformat(),
               "preview": preview.name, "hook_text": None})
    return reel, master


def case_selftest(root):
    for script in (SCRIPTS / "build_edit.py", PLUGIN / "skills/reel-canvas-build/scripts/compose.py"):
        p = command(script, "--selftest")
        ck(script.name + " selftest", p.returncode == 0 and "selftest ok" in p.stdout, p.stdout + p.stderr)
    note = build.baked_note([{"start_f": 36, "end_f": 60, "layout": "pip"},
                            {"start_f": 75, "end_f": 84, "layout": "overlay"}], Fraction(30))
    ck("baked note names the spans in plain time", note.startswith("note: 2 parts use the finished picture")
       and "0:01.2-0:02.0 (picture-in-picture)" in note and "0:02.5-0:02.8 (blurred card)" in note and "\n" not in note)
    for length in (None, -.1, 1):
        timing = fcpx.sfx_timing({"time": 1, "length_s": length, "end_mode": "cut", "fade_out_s": .1}, Fraction(2, 5))
        ck("SFX missing or invalid length keeps the original", timing["duration"] == Fraction(2, 5) and timing["fade_out"] == 0)
    for fade, want in ((None, Fraction(1, 4)), (0, Fraction(1, 4)), (.001, Fraction(1, 50)), (1, Fraction(3, 10))):
        timing = fcpx.sfx_timing({"time": 1, "length_s": .3, "end_mode": "fade", "fade_out_s": fade}, Fraction(2, 5))
        ck("SFX fade default, floor and duration cap", timing["fade_out"] == want)


def case_fcpxml(root):
    reel, master = fixture(root)
    out = reel / "handoff/test.fcpxml"
    def write(reel, aroll, overlay, out):
        model = fcpx.load_model(reel, aroll, overlay)
        source = next((a["path"] for a in model["assets"] if a["id"] == model["master"]), None)
        media = build.derive_media(reel, aroll, source)
        return fcpx.write(reel, aroll, overlay, out, **media)

    summary = write(reel, master, None, out)
    ck("FCPXML checks", fcpx.check(out) == [], fcpx.check(out))
    tree = ET.parse(out)
    fmt = tree.find("resources/format")
    ck("1080x1920 exact 30fps", (fmt.get("width"), fmt.get("height"), fmt.get("frameDuration")) == ("1080", "1920", "1/30s"))
    spine = tree.findall(".//spine/asset-clip")
    assets = {a.get("id"): a.find("media-rep").get("src") for a in tree.findall("resources/asset")}
    ck("one continuous voice spine", len(spine) == 1 and " Voice - " in fcpx.uri_path(assets[spine[0].get("ref")]).name
       and all(fcpx.seconds(spine[0].get(k)) == 0 for k in ("offset", "start"))
       and fcpx.seconds(spine[0].get("duration")) == Fraction(14, 5))
    clips = tree.findall('.//spine/asset-clip/asset-clip[@lane="1"]')
    ck("picture clips at every cut", len(clips) == 2 and all(" Picture - " in fcpx.uri_path(assets[c.get("ref")]).name for c in clips)
       and [(fcpx.seconds(c.get("offset")), fcpx.seconds(c.get("start")), fcpx.seconds(c.get("duration")))
            for c in clips] == [(Fraction(0), Fraction(0), Fraction(7, 5)), (Fraction(7, 5), Fraction(7, 5), Fraction(7, 5))])
    ck("A/V a-roll is absent", master.resolve().as_uri() not in assets.values())
    ck("full layout has no finished-picture clips", not tree.findall('.//asset-clip[@lane="4"]') and summary["baked_spans"] == [])
    refs = [r.get("src") for r in tree.findall(".//media-rep")]
    ck("original bed and SFX", any("/beds/" in r for r in refs) and any("/sfx/" in r for r in refs)
       and all("/sound/music.wav" not in r and "/sound/cues/" not in r for r in refs))
    keys = tree.findall('.//asset-clip[@lane="-1"]//keyframe')
    ck("all four live duck points and applied level", len(keys) == 4 and keys[1].get("value") == "-18dB")
    ck("duck times are local to bed entry", keys[1].get("time") == "3/10s")
    sfx = tree.find('.//asset-clip[@lane="-2"]')
    picked = fcpx.read(reel / "sound-selection.json")["cues"][0]
    onset = Fraction(round((picked["time"] - picked["peak_s"]) * 48000), 48000)
    ck("original SFX onset ignores padded placement start", fcpx.seconds(sfx.get("offset")) == onset
       and onset != Fraction(43200, 48000) and sfx.get("start") == "0/1s")
    ck("original SFX gain and requested fade", sfx.find("adjust-volume").get("amount") == "-8dB"
       and sfx.find(".//fadeOut").get("duration") == "1/20s")
    early = tree.find('.//asset-clip[@lane="-3"]')
    ck("before-zero SFX trims source head", fcpx.seconds(early.get("offset")) == 0
       and fcpx.seconds(early.get("start")) == Fraction(1, 10)
       and fcpx.seconds(early.get("duration")) == Fraction(1, 5))
    ck("cut SFX has no fade", early.find(".//fadeOut") is None)
    ck("every referenced file is summarized", len(summary["paths"]) == 4)
    # Carve stays in our render; the native hand-off retains these exact dip points.
    import contextlib
    import io
    placement = fcpx.read(reel / "sound/placement.json")
    placement["bed"]["mode"] = "carve"
    build.save(reel / "sound/placement.json", placement)
    stream = io.StringIO()
    media = build.derive_media(reel, master, None)
    carved_out = out.with_name("carve.fcpxml")
    with contextlib.redirect_stdout(stream):
        carved_summary = fcpx.write(reel, master, None, carved_out, **media)
    note = "The music's voice carve is applied only in our render; Resolve gets the simpler dip."
    ck("carve hand-off prints and records one plain note", stream.getvalue().count(note) == 1
       and carved_summary.get("notes") == [note], stream.getvalue())
    ck("carve hand-off retains the original dip keyframes", carved_out.read_bytes() == out.read_bytes())
    placement["bed"].pop("mode")
    build.save(reel / "sound/placement.json", placement)
    clips[1].set("ref", spine[0].get("ref"))
    tree.write(out)
    ck("voice used as a cut picture rejected", bool(fcpx.check(out)))
    write(reel, master, None, out)
    tree = ET.parse(out)
    tree.find(".//spine").append(copy.deepcopy(tree.find(".//spine/asset-clip")))
    tree.write(out)
    ck("split voice spine rejected", bool(fcpx.check(out)))
    write(reel, master, None, out)
    tree = ET.parse(out)
    picture_ref = tree.find('.//asset-clip[@lane="1"]').get("ref")
    tree.find(f'resources/asset[@id="{picture_ref}"]/media-rep').set("src", master.resolve().as_uri())
    tree.write(out)
    ck("A/V a-roll reference rejected", bool(fcpx.check(out)))
    write(reel, master, None, out)
    tree = ET.parse(out)
    tree.find("resources/format").set("frameDuration", "1/25s")
    tree.write(out)
    ck("format mutation rejected", bool(fcpx.check(out)))
    write(reel, master, None, out)
    (reel / "beds/bed.wav").unlink()
    ck("deleted original detected", any("missing" in p for p in fcpx.check(out)))
    ntsc_root = root / "ntsc"
    ntsc_reel, ntsc_master = fixture(ntsc_root, "30000/1001")
    ntsc = ntsc_reel / "handoff/ntsc.fcpxml"
    write(ntsc_reel, ntsc_master, None, ntsc)
    ck("NTSC stays rational", ET.parse(ntsc).find("resources/format").get("frameDuration") == "1001/30000s")
    ck("NTSC FCPXML checks with float cut metadata", fcpx.check(ntsc) == [], fcpx.check(ntsc))
    voice_path = next(fcpx.uri_path(r.get("src")) for r in ET.parse(ntsc).findall(".//media-rep")
                      if fcpx.uri_path(r.get("src")).suffix == ".wav" and " Voice - " in fcpx.uri_path(r.get("src")).name)
    ck("NTSC voice covers the fractional sample at the reel end", fcpx.probe(voice_path)["duration"] == Fraction(134535, 48000))
    ntsc_fcp7, ntsc_srt = ntsc.with_suffix(".xml"), ntsc.with_suffix(".srt")
    legacy.write_fcp7(ntsc_reel, ntsc_master, None, ntsc_fcp7)
    legacy.write_srt(ntsc_reel, ntsc_srt)
    ck("NTSC FCP7 and SRT accept float cut metadata", legacy.check_fcp7(ntsc_fcp7) == [] and legacy.check_srt(ntsc_srt) == []
       and ET.parse(ntsc_fcp7).findtext("sequence/rate/ntsc") == "TRUE")
    # The same source bed is split at a stop; neither piece restarts its source playhead.
    placement = fcpx.read(ntsc_reel / "sound/placement.json")
    placement["bed"]["stops"] = [{"start_s": 1, "end_s": 1.4, "fade_out_s": .1, "fade_in_s": .2}]
    build.save(ntsc_reel / "sound/placement.json", placement)
    write(ntsc_reel, ntsc_master, None, ntsc)
    beds = ET.parse(ntsc).findall('.//asset-clip[@lane="-1"]')
    ck("stops remain gaps with source continuity and fades", len(beds) == 2 and beds[1].get("start") == "8/5s"
       and len(ET.parse(ntsc).findall(".//fadeIn")) == 2 and len(ET.parse(ntsc).findall(".//fadeOut")) == 3)
    # Only synthetic ffmpeg media: no second compositor render is needed for the layout fallback.
    composite = ntsc_reel / "renders/REEL_A Master - 11.06.26.mp4"
    track = {"keys": [{"f": 0, "layout": "full", "scale": 1, "ox": .5, "oy": .38},
                      {"f": 42, "layout": "pip", "scale": 1, "ox": .5, "oy": .38}],
             "tweens": [], "style": {"style": "layout-switch"}, "total_f": 84, "fps": "30000/1001"}
    build.save(ntsc_reel / "work/scale_track.json", track)
    beat_map = fcpx.read(ntsc_reel / "beat-map-selection.json")
    beat_map["beats"][1]["layout"] = "pip"
    beat_map["edit_style"] = {"style": "layout-switch", "punch_scale": 1,
                              "moves": {"opening_settle": False, "follow_cam": False, "word_punches": None}}
    build.save(ntsc_reel / "beat-map-selection.json", beat_map)
    try:
        write(ntsc_reel, ntsc_master, None, ntsc)
    except fcpx.Stop as e:
        ck("baked parts require a finished Master", e.code == 1 and str(e) == build.compose_module().NEED_BAKED_MASTER)
    else:
        ck("baked parts require a finished Master", False)
    shutil.copyfile(master, composite)  # The 30 fps picture must not stand in for the NTSC Master.
    try:
        write(ntsc_reel, ntsc_master, None, ntsc)
    except fcpx.Stop as e:
        ck("baked parts reject a Master at the wrong rate", e.code == 1 and str(e) == build.compose_module().NEED_BAKED_MASTER)
    else:
        ck("baked parts reject a Master at the wrong rate", False)
    picture(composite, "30000/1001")
    summary = write(ntsc_reel, ntsc_master, None, ntsc)
    tree = ET.parse(ntsc)
    finished = tree.findall('.//asset-clip[@lane="4"]')
    ck("one finished Master clip covers the pip span", len(finished) == 1
       and finished[0].get("srcEnable") == "video" and fcpx.seconds(finished[0].get("offset")) == Fraction(42 * 1001, 30000)
       and finished[0].get("start") == finished[0].get("offset")
       and fcpx.seconds(finished[0].get("duration")) == Fraction(42 * 1001, 30000))
    refs = {a.get("id"): a.find("media-rep").get("src") for a in tree.findall("resources/asset")}
    baked_picture = fcpx.uri_path(refs[finished[0].get("ref")])
    ck("baked clip references a picture-only Master copy", " Master Picture - " in baked_picture.name
       and not fcpx.probe(baked_picture)["audio"] and composite.resolve().as_uri() not in refs.values())
    ck("baked spans are summarized", summary["baked_spans"] == [{"start_f": 42, "end_f": 84, "layout": "pip"}])
    ck("FCPXML accepts baked Master frames", fcpx.check(ntsc) == [], fcpx.check(ntsc))
    legacy.write_fcp7(ntsc_reel, ntsc_master, None, ntsc_fcp7)
    ck("FCP7 accepts baked Master frames", legacy.check_fcp7(ntsc_fcp7) == [], legacy.check_fcp7(ntsc_fcp7))
    legacy_tree = ET.parse(ntsc_fcp7)
    v3 = legacy_tree.findall("sequence/media/video/track")[3].findall("clipitem")
    ck("FCP7 V4 carries the pip frames as video only", len(v3) == 1 and v3[0].findtext("start") == "42"
       and v3[0].findtext("end") == "84" and v3[0].findtext("in") == "42" and v3[0].findtext("out") == "84"
       and v3[0].findtext("sourcetrack/mediatype") == "video")
    finished[0].set("duration", "1/60000s")
    tree.write(ntsc)
    ck("FCPXML rejects a fractional baked frame", any("span" in p for p in fcpx.check(ntsc)))
    write(ntsc_reel, ntsc_master, None, ntsc)
    v3[0].find("in").text = "41"
    legacy_tree.write(ntsc_fcp7)
    ck("FCP7 rejects a shifted baked source frame", any("span" in p for p in legacy.check_fcp7(ntsc_fcp7)))
    legacy.write_fcp7(ntsc_reel, ntsc_master, None, ntsc_fcp7)
    composite.unlink()
    baked_picture.unlink()
    ck("FCPXML reports a missing baked Master", any("Master" in p and "missing" in p for p in fcpx.check(ntsc)))
    ck("FCP7 reports a missing baked Master", any("Master" in p and "missing" in p for p in legacy.check_fcp7(ntsc_fcp7)))


def case_fcp7_srt(root):
    reel, master = fixture(root)
    xml, srt = reel / "handoff/test.xml", reel / "handoff/test.srt"
    legacy.write_fcp7(reel, master, None, xml)
    summary = legacy.write_srt(reel, srt)
    ck("FCP7 checks", legacy.check_fcp7(xml) == [], legacy.check_fcp7(xml))
    tree = ET.parse(xml)
    files = {f.get("id"): f.findtext("pathurl") for f in tree.findall(".//file") if f.find("pathurl") is not None}
    for folder in ("beds", "sfx"):
        channels = [int(c.findtext("sourcetrack/trackindex")) for c in tree.findall(".//audio/track/clipitem")
                    if f"/{folder}/" in files.get(c.find("file").get("id"), "")]
        ck(folder + " stereo channels preserved", sorted(channels) == ([1, 2] if folder == "beds" else [1, 1, 2, 2]), channels)
    effects = [c for c in tree.findall(".//audio/track/clipitem") if "/sfx/" in files.get(c.find("file").get("id"), "")]
    picked = fcpx.read(reel / "sound-selection.json")["cues"][0]
    onset = Fraction(round((picked["time"] - picked["peak_s"]) * 48000), 48000)
    for clip in effects:
        early = int(clip.findtext("start")) == 0
        ck("FCP7 original SFX timing and trim", (int(clip.findtext("start")), int(clip.findtext("in")),
           int(clip.findtext("end")) - int(clip.findtext("start"))) ==
           ((0, 3, 6) if early else (round(onset * 30), 0, 9)))
        keys = clip.findall("filter/effect/parameter/keyframe")
        ck("FCP7 fades only fade-mode SFX", not keys if early else len(keys) >= 2 and keys[-1].findtext("value") == "0")
    ck("FCP7 references originals only", all("/sound/cues/" not in p and "/sound/music.wav" not in p
       and "/sound/sfx.wav" not in p for p in files.values()))
    ck("SRT checks", legacy.check_srt(srt) == [], legacy.check_srt(srt))
    ck("caption count and first start", summary["entries"] == 3 and legacy.srt_entries(srt)[0][1] == 100)
    srt.write_bytes(b"1\n00:00:00,000 --> 00:00:01,000\nFirst\n\n2\n00:00:00,500 --> 00:00:02,000\nNext\n\n")
    ck("overlapping subtitle rejected", bool(legacy.check_srt(srt)))


def case_gate(root):
    reel = root / "videos/REEL_A"
    reel.mkdir(parents=True)
    build.save(reel / "work/render-ok.json", {"preview": "old preview"})
    before = {p.relative_to(reel): p.read_bytes() for p in reel.rglob("*") if p.is_file()}
    p = command(SCRIPTS / "build_edit.py", "package", "--reel-dir", reel, cwd=root)
    ck("missing final video is reported before approval details", p.returncode == 1 and p.stdout.strip() ==
       "There's no final video yet. Make the final video, then package it." and not p.stderr, p.stdout + p.stderr)
    ck("missing final video writes nothing", not (reel / "handoff").exists()
       and {p.relative_to(reel): p.read_bytes() for p in reel.rglob("*") if p.is_file()} == before)
    build.save(root / "editor/editor.config.json", {"nle": "none"})
    p = command(SCRIPTS / "build_edit.py", "resolve-steps", "--reel-dir", reel, cwd=root)
    ck("unconfigured Resolve exits 3 with one line", p.returncode == 3 and len(p.stdout.strip().splitlines()) == 1
       and "isn't set up" in p.stdout and "Traceback" not in p.stderr, p.stdout + p.stderr)


def frame(path, number, alpha=False):
    p = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{number})",
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba" if alpha else "rgb24", "-"], capture_output=True)
    if p.returncode:
        raise RuntimeError("Frame decode failed")
    import numpy as np
    return np.frombuffer(p.stdout, dtype=np.uint8).reshape(1920, 1080, 4 if alpha else 3)


def package_reel(root):
    reel, master = fixture(root)
    shutil.copyfile(master, reel / f"renders/REEL_A Master - {datetime.now().strftime('%m.%d.%y')}.mp4")
    p = command(SCRIPTS / "build_edit.py", "package", "--reel-dir", reel, cwd=root)
    if not ck("package command", p.returncode == 0, p.stdout + p.stderr):
        raise RuntimeError("Package failed")
    return reel, master


def case_package(root):
    import numpy as np
    reel, master = package_reel(root)
    manifest = fcpx.read(reel / "handoff/handoff.json")
    files = manifest["sha256"]
    ck("package has three layers, Picture, Voice, XMLs and subtitles", len(files) == 8
       and all((reel / "handoff" / p).is_file() for p in files))
    ck("full-layout package records no baked parts or note", manifest["baked_spans"] == [] and manifest["baked_note"] == "")
    ck("all payload SHA256s", all(build.digest(reel / "handoff" / p) == sha for p, sha in files.items()))
    aroll, overlay = [(reel / manifest["layers"][k]["out"]) for k in ("aroll", "overlay")]
    ck("a-roll has all frames and voice", fcpx.fpsmod.frame_count(aroll) == 84 and fcpx.probe(aroll)["audio"])
    picture_path, voice = (reel / manifest["derived"][k] for k in ("picture", "voice"))
    ck("Picture keeps frames without audio", fcpx.fpsmod.frame_count(picture_path) == 84
       and not fcpx.probe(picture_path)["audio"] and fcpx.probe(picture_path)["duration"] == Fraction(14, 5))
    voice_info = fcpx.probe(voice)
    ck("Voice is full-length 24-bit 48kHz with the original channels", not voice_info["video"]
       and voice_info["duration"] == Fraction(14, 5) and voice_info["sample_rate"] == 48000
       and voice_info["channels"] == fcpx.probe(aroll)["channels"] and voice_info["audio_codec"] == "pcm_s24le")
    ck("Picture stream copy preserves pixels", np.array_equal(frame(picture_path, 65), frame(aroll, 65)))
    compose = build.compose_module()
    approval = fcpx.read(reel / compose.OK_FILE)
    approval.pop("hook_text")
    build.save(reel / compose.OK_FILE, approval)
    compose.render(reel, "master", None)
    ck("Master saves null when using first-beat words", fcpx.read(reel / compose.OK_FILE) == dict(approval, hook_text=None))
    pix = next(s["pix_fmt"] for s in compose.streams(overlay) if s["codec_type"] == "video")
    ck("overlay MOV has alpha, no sound and all frames", overlay.suffix == ".mov" and compose.alpha_pix_fmt(pix)
       and not fcpx.probe(overlay)["audio"] and fcpx.fpsmod.frame_count(overlay) == 84)
    ck("overlay corner is transparent", frame(overlay, 15, True)[0, 0, 3] == 0)
    captions = reel / manifest["layers"]["captions"]["out"]
    pix = next(s["pix_fmt"] for s in compose.streams(captions) if s["codec_type"] == "video")
    ck("captions MOV has alpha, no sound and all frames", captions.suffix == ".mov" and compose.alpha_pix_fmt(pix)
       and not fcpx.probe(captions)["audio"] and fcpx.fpsmod.frame_count(captions) == 84)
    ck("captions layer contains visible text and a transparent corner", frame(captions, 15, True)[:, :, 3].max() > 0
       and frame(captions, 15, True)[0, 0, 3] == 0)
    inp = compose.load_inputs(reel)
    compose.probe_inputs(inp)
    inp.update(track=fcpx.read(reel / "work/scale_track.json"), captions=fcpx.read(reel / "work/captions.json"), under=[], hook_f=0)
    ck("overlay page excludes captions", "#captions" not in compose.main_html(inp, 1080, 1920, [], layers="overlay"))
    trk = fcpx.read(reel / "work/scale_track.json")
    ck("saved style produced a scale move", any(abs(k["scale"] - 1) > 1e-6 for k in trk["keys"])
       or any(t["prop"] == "scale" and t["from"] != t["to"] for t in trk["tweens"]), trk)
    def difference(n):
        return float(np.mean(np.abs(frame(aroll, n).astype(np.float32) - frame(master, n).astype(np.float32))))
    outside, inside = difference(15), difference(65)
    ck("unpunched frame matches", outside < 6, outside)
    ck("punched frame visibly moves", inside > 12 and inside > outside * 3, (outside, inside))
    ck("layer outputs never enter renders", all("A-roll" not in p.name and "Overlay" not in p.name for p in (reel / "renders").iterdir()))
    # Re-approving a new preview with the same cut list must invalidate the reused picture layer.
    preview = compose.latest_preview(reel / "renders")
    preview.touch()
    p = command(PLUGIN / "skills/reel-canvas-build/scripts/compose.py", "ok", "--reel-dir", reel, cwd=root)
    ck("re-approval recorded by compose.py ok", p.returncode == 0, p.stdout + p.stderr)
    compose.render(reel, "master", None)
    p = command(SCRIPTS / "build_edit.py", "package", "--reel-dir", reel, "--which", "none", cwd=root)
    ck("new approval invalidates reused layers", p.returncode == 1 and "approved preview changed" in p.stdout, p.stdout + p.stderr)


def hook_package(root, first_line, hook):
    reel, master = fixture(root)
    compose = build.compose_module()
    bm = fcpx.read(reel / "beat-map-selection.json")
    spoken = first_line.split()
    words = fcpx.read(reel / "work/edit_map.cut.json")["words"]
    opening = [{"id": f"hook_{i:04d}", "word": word, "start": .1 + i / len(spoken),
                "end": .1 + (i + .8) / len(spoken)} for i, word in enumerate(spoken)]
    build.save(reel / "work/edit_map.cut.json", {"words": opening + words[4:]})
    bm["beats"][0]["speech_anchor"].update(text=first_line, w1=len(spoken) - 1)
    bm["beats"][1]["speech_anchor"].update(w0=len(spoken), w1=len(spoken) + 3)
    bm["edit_style"]["moves"]["word_punches"]["picks"] = [len(spoken) + 1]
    build.save(reel / "beat-map-selection.json", bm)
    approval = fcpx.read(reel / compose.OK_FILE)
    approval.pop("hook_text")
    build.save(reel / compose.OK_FILE, approval)
    compose.render(reel, "master", hook)
    used = " ".join(hook.split())
    ck("Master saves the hook actually used and preserves approval",
       fcpx.read(reel / compose.OK_FILE) == dict(approval, hook_text=used))
    calls = []

    def render_layer(reel_arg, tier, hook_arg, *, layers):
        calls.append((reel_arg, tier, hook_arg, layers))
        path = reel / "handoff" / (layers + (".mp4" if layers == "aroll" else ".mov"))
        if layers == "aroll":
            shutil.copyfile(master, path)
        else:
            must([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", master, "-an", "-c:v", "copy", path])
        return {"out": path.relative_to(reel).as_posix()}

    # Keep packaging real; only replace the expensive layer compositor and inspect its inputs.
    with patch.object(compose, "render", side_effect=render_layer):
        manifest = build.package(reel)
    ck("package passes the approved hook to every layer", calls == [
        (reel, "master", used, "aroll"), (reel, "master", used, "overlay"), (reel, "master", used, "captions")], calls)
    ck("hook package writes its manifest", bool(manifest["sha256"]) and (reel / "handoff/handoff.json").is_file())
    ck("layer renders preserve the saved hook", fcpx.read(reel / compose.OK_FILE) == dict(approval, hook_text=used))


def case_hook_long(root):
    hook_package(root, "This first spoken line is deliberately longer than seventy characters so packaging must reuse the approved short title.",
                 "  Clear   cuts make edits easy  ")


def case_hook_named(root):
    hook_package(root, "Clear cuts", "Your client-named opening")


def case_hook_old_ok(root):
    reel, master = fixture(root)
    shutil.copyfile(master, reel / f"renders/REEL_A Master - {datetime.now().strftime('%m.%d.%y')}.mp4")
    approval = fcpx.read(reel / "work/render-ok.json")
    approval.pop("hook_text")
    build.save(reel / "work/render-ok.json", approval)
    before = {p.relative_to(reel): p.read_bytes() for p in reel.rglob("*") if p.is_file()}
    p = command(SCRIPTS / "build_edit.py", "package", "--reel-dir", reel, cwd=root)
    ck("old approval stops with one plain line", p.returncode == 1 and p.stdout.strip() ==
       "This reel's approval is from before hook text was saved; re-run the master render, then package again."
       and not p.stderr, p.stdout + p.stderr)
    ck("old approval writes nothing", not (reel / "handoff").exists()
       and {p.relative_to(reel): p.read_bytes() for p in reel.rglob("*") if p.is_file()} == before)


def case_hub(root):
    sys.path.insert(0, str(HERE))
    import hub_test
    p = hub_test.Proof(root)
    try:
        config = fcpx.read(p.ws / "editor/editor.config.json")
        for nle, expected in (("resolve", ["DaVinci Resolve", "Another editor (files)"]), ("mcp", ["Another editor (files)"]), ("none", [])):
            build.save(p.ws / "editor/editor.config.json", dict(config, nle=nle))
            p.refresh()
            options = p.snapshot("Array.from(document.querySelector('#handoff-editor')?.options || [], o=>o.textContent)")
            ck(nle + " hand-off choices", options == expected, options)
            if not expected:
                ck("none hides hand-off", not p.snapshot("!!document.querySelector('[data-skill=handoff]')"))
                continue
            p.browse([{"do": "set", "sel": "#handoff-editor", "value": expected[-1]},
                      {"do": "click", "sel": "[data-skill=handoff]"}, {"do": "waitFn", "js": "Hub.pending===0"}])
            request = fcpx.read(p.videos / "reel-01/hub-requests.json")[-1]
            ck(nle + " Send preserves client choice", request["skill"] == "handoff" and request["choices"]["editor"] == expected[-1])
    finally:
        p.close()


def steps_fixture(root):
    """Use synthetic interchange files, without a compositor render or Resolve."""
    reel, master = fixture(root)
    out = reel / "handoff"
    out.mkdir()
    layers = {}
    for layer, label, ext in (("aroll", "A-roll", "mp4"), ("overlay", "Overlay", "mov"), ("captions", "Captions", "mov")):
        path = out / f"REEL_A {label} - 11.06.26.{ext}"
        if layer == "aroll":
            shutil.copyfile(master, path)
        else:
            must([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", master, "-an", "-c:v", "copy", path])
        layers[layer] = {"out": path.relative_to(reel).as_posix()}
    paths = {key: reel / value["out"] for key, value in layers.items()}
    derived = build.derive_media(reel, paths["aroll"])
    xml = out / "REEL_A - Resolve.fcpxml"
    summary = fcpx.write(reel, paths["aroll"], paths["overlay"], xml, captions=paths["captions"], **derived)
    fcp7 = out / "REEL_A - FCP7.xml"
    legacy.write_fcp7(reel, paths["aroll"], paths["overlay"], fcp7, captions=paths["captions"])
    srt = out / "REEL_A - Captions.srt"
    legacy.write_srt(reel, srt)
    build.save(reel / "work/scale_track.json", {"keys": [
        {"f": 0, "scale": 1}, {"f": 42, "scale": 1.18}], "tweens": [], "total_f": 84})
    build.save(out / "handoff.json", {"schema": 2, "layers": layers, "summaries": {"fcpxml": summary}, "baked_spans": [],
               "derived": {k: p.relative_to(reel).as_posix() for k, p in derived.items()},
               "sha256": {p.name: build.digest(p) for p in [*paths.values(), *derived.values(), xml, fcp7, srt]}})
    return reel, master


def case_steps(root):
    reel, _ = steps_fixture(root)
    p = command(SCRIPTS / "build_edit.py", "resolve-steps", "--reel-dir", reel, "--project", "S12 native proof", cwd=root)
    if not ck("native steps command", p.returncode == 0, p.stdout + p.stderr):
        return
    steps = fcpx.read(reel / "handoff/resolve-steps.json")
    ck("native steps are ordered", [s["id"] for s in steps] == ["ready", "project", "import", "captions", "report"])
    for step in steps:
        tree = ast.parse(step["script"])
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        names = [alias.name for n in imports if isinstance(n, ast.Import) for alias in n.names]
        names += [n.module for n in imports if isinstance(n, ast.ImportFrom)]
        ck(step["id"] + " sandbox imports", all(n in ("time", "json") for n in names) and "open(" not in step["script"])
        ck(step["id"] + " returns result", any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
           and n.id == "result" for n in ast.walk(tree)))
        ck(step["id"] + " timeout and client line", 0 < step["timeout"] <= 60 and "\n" not in step["say"])
        ck(step["id"] + " never appends subtitles", "AppendToTimeline" not in step["script"] and "LoadProject" not in step["script"])
    by_id = {s["id"]: s["script"] for s in steps}
    for step, path in (("import", reel / "handoff/REEL_A - Resolve.fcpxml"),
                       ("captions", reel / "handoff/REEL_A - Captions.srt")):
        strings = [n.value for n in ast.walk(ast.parse(by_id[step])) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        ck(step + " embeds the real absolute handoff path", str(path.resolve()) in strings)
    ck("import links sources and fixes timeline settings", "importSourceClips" in by_id["import"]
       and "sourceClipsPath" in by_id["import"] and "useCustomSettings" in by_id["import"])
    tree = ET.parse(reel / "handoff/REEL_A - Resolve.fcpxml")
    ck("overlay and captions use lanes two and three and SRT is separate",
       len(tree.findall('.//asset-clip[@lane="2"]')) == 1 and len(tree.findall('.//asset-clip[@lane="3"]')) == 1
       and ".srt" not in ET.tostring(tree.getroot(), encoding="unicode"))
    fcp7 = reel / "handoff/REEL_A - FCP7.xml"
    tracks = ET.parse(fcp7).findall("sequence/media/video/track")
    ck("FCP7 captions have their own V3 track", legacy.check_fcp7(fcp7) == []
       and len(tracks[2].findall("clipitem")) == 1 and "Captions" in tracks[2].findtext("clipitem/name"))

    class Project:
        def __init__(self, name):
            self.name = name

        def GetName(self):
            return self.name

    class Manager:
        fail = False
        current = Project("An existing project")

        def GetProjectListInCurrentFolder(self):
            return ["S12 native proof", "S12 native proof (2)"]

        def CreateProject(self, name):
            if self.fail:
                return False
            self.current = Project(name)
            return True  # Require a re-read, even when creation returns no project proxy.

        def GetCurrentProject(self):
            return self.current

    class Resolve:
        manager = Manager()

        def GetProjectManager(self):
            return self.manager

    stub = Resolve()
    scope = {"resolve": stub, "project": stub.manager.current}
    exec(by_id["project"], scope)
    ck("project collisions create the next new name and re-read current project", scope["result"].get("ok") is True
       and scope["result"].get("name") == "S12 native proof (3)" and scope["project"] is stub.manager.current)
    stub.manager.fail = True
    before = stub.manager.current
    exec(by_id["project"], scope)
    ck("creation failure stops without changing the existing project", scope["result"].get("ok") is False
       and stub.manager.current is before)
    build.save(reel / "work/scale_track.json", {"keys": [{"f": 0, "scale": 1}], "tweens": []})
    p = command(SCRIPTS / "build_edit.py", "resolve-steps", "--reel-dir", reel, cwd=root)
    ck("no punch still prepares Resolve steps", p.returncode == 0, p.stdout + p.stderr)
    steps = fcpx.read(reel / "handoff/resolve-steps.json")
    ck("no punch is noted in the saved steps", any("punched comparison was skipped" in note
       for step in steps for note in step.get("notes", [])))
    for keys, spans, expected in (([{"f": 0, "scale": 1.18}], [], {"punched": 42}),
                                  ([{"f": 0, "scale": 1}], [{"start_f": 0, "end_f": 84}], {})):
        build.save(reel / "work/scale_track.json", {"keys": keys, "tweens": []})
        manifest = fcpx.read(reel / "handoff/handoff.json")
        build.save(reel / "handoff/handoff.json", dict(manifest, baked_spans=spans))
        ck("proof returns whichever frames exist", build.proof_frames(reel) == expected)


def case_rcheck(root, frame_mode=None):
    reel, master = steps_fixture(root)
    manifest = fcpx.read(reel / "handoff/handoff.json")
    if frame_mode == "layout-switch":
        compose = build.compose_module()
        bm = fcpx.read(reel / "beat-map-selection.json")
        bm["edit_style"] = {"style": "layout-switch", "moves": {}}
        build.save(reel / "beat-map-selection.json", bm)
        build.save(reel / "work/scale_track.json", compose.styles.plan(reel, fps="30"))
    elif frame_mode == "no-scale-track":
        (reel / "work/scale_track.json").unlink()
    p = command(SCRIPTS / "build_edit.py", "resolve-steps", "--reel-dir", reel, cwd=root)
    if not ck("rcheck prepares native steps", p.returncode == 0, p.stdout + p.stderr):
        return
    steps = fcpx.read(reel / "handoff/resolve-steps.json")
    frames = build.proof_frames(reel)
    if frame_mode:
        ck(frame_mode + " has only an unpunched frame", frames == {"unpunched": 42}, frames)
        ck(frame_mode + " notes skipped punched comparison in steps", any("punched comparison was skipped" in note
           for step in steps for note in step.get("notes", [])))
    out = reel / "handoff"
    picture_path = reel / manifest["derived"]["picture"]
    voice = reel / manifest["derived"]["voice"]
    stills = []
    for kind, number in frames.items():
        target = out / f"resolve-still-{number}.png"
        vf = f"select=eq(n\\,{number})" + (",crop=iw/1.18:ih/1.18,scale=1080:1920" if kind == "punched" else "")
        must([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", master, "-vf", vf, "-frames:v", "1", target])
        stills.append({"frame": number, "path": str(target.resolve()), "exported": True})
    items = [{"kind": "video", "track": 1, "name": "A-roll", "start": a, "end": b,
              "media_path": str(picture_path.resolve()), "offline": False, "media_pool": True}
             for a, b in ((0, 42), (42, 84))]
    for layer, track in (("overlay", 2), ("captions", 3)):
        items.append({"kind": "video", "track": track, "name": layer, "start": 0, "end": 84,
                      "media_path": str((reel / manifest["layers"][layer]["out"]).resolve()), "offline": False, "media_pool": True})
    for path, count in manifest["summaries"]["fcpxml"]["audio_items"].items():
        for _ in range(count):
            items.append({"kind": "audio", "track": 1 if Path(path) == voice.resolve() else 2,
                          "name": Path(path).name, "start": 0, "end": 84,
                          "media_path": path, "offline": False, "media_pool": True, "volume_db": -12 if "/beds/" in path.replace("\\", "/") else 0})
    good = {s["id"]: {"ok": True} for s in steps}
    good["ready"].update(product="DaVinci Resolve Studio", version=[21, 1, 0, 17])
    good["project"].update(name="REEL_A hand-off", created=True)
    good["report"].update(width="1080", height="1920", frame_rate="30", project_width="1080", project_height="1920",
                          start_frame=0, items=items, stills=stills,
                          pool=[{"name": "REEL_A - Captions.srt", "path": str((out / "REEL_A - Captions.srt").resolve())}])
    result_path = out / "resolve-result.json"

    def check_result(data, label, expected, text=""):
        build.save(result_path, data)
        p = command(SCRIPTS / "build_edit.py", "resolve-check", "--reel-dir", reel, "--result", result_path, cwd=root)
        ck(label, p.returncode == expected and (not expected or len(p.stdout.strip().splitlines()) == 1
           and text in p.stdout and "Traceback" not in p.stderr), p.stdout + p.stderr)
        ck(label + " writes report", (out / "resolve-report.json").is_file()
           and bool(fcpx.read(out / "resolve-report.json")["problems"]) == bool(expected))
    check_result(good, "synthetic native result passes", 0)
    if frame_mode:
        report = fcpx.read(out / "resolve-report.json")
        ck(frame_mode + " verifies available frame and notes skipped comparison",
           set(report["frame_differences"]) == {"unpunched"} and any(
               "punched comparison was skipped" in note for note in report["notes"]))
    bad = copy.deepcopy(good)
    first_voice = next(i for i in bad["report"]["items"] if i["kind"] == "audio" and i["track"] == 1)
    first_voice["end"] = 42
    bad["report"]["items"].append(dict(first_voice, track=3, start=42, end=84))
    check_result(bad, "voice split across tracks rejected", 1, "voice")
    bad = copy.deepcopy(good)
    next(i for i in bad["report"]["items"] if i["kind"] == "audio" and i["track"] == 1)["track"] = 3
    check_result(bad, "whole voice on wrong track rejected", 1, "voice")
    bad = copy.deepcopy(good)
    bad["report"]["items"][0]["media_path"] = str((reel / manifest["layers"]["aroll"]["out"]).resolve())
    check_result(bad, "A-roll mp4 item rejected", 1, "A-roll")
    bad = copy.deepcopy(good)
    bad["report"]["items"] = [i for i in bad["report"]["items"] if "beds" not in Path(i["media_path"]).parts]
    check_result(bad, "missing bed rejected", 1, "music")
    bad = copy.deepcopy(good)
    bad["report"]["width"] = "1920"
    check_result(bad, "wrong resolution rejected", 1, "size")
    bad = copy.deepcopy(good)
    bad["report"]["items"][0]["offline"] = True
    check_result(bad, "offline item rejected", 1, "offline")
    bad = copy.deepcopy(good)
    bad["report"]["items"] = [i for i in items if not (i["kind"] == "video" and i["track"] == 3)]
    check_result(bad, "missing captions layer rejected", 1, "captions")
    bad = copy.deepcopy(good)
    bad["report"]["items"].pop(0)
    check_result(bad, "wrong V1 count rejected", 1, "cut")
    bad = copy.deepcopy(good)
    next(i for i in bad["report"]["items"] if "beds" in i["media_path"])["volume_db"] = -11
    check_result(bad, "wrong bed volume rejected", 1, "volume")
    bad = copy.deepcopy(good)
    bad["report"]["pool"] = []
    check_result(bad, "SRT missing from pool rejected", 1, "SRT")
    bad = copy.deepcopy(good)
    bad["report"]["stills"] = []
    check_result(bad, "missing frame proof rejected", 1, "still")
    bad = copy.deepcopy(good)
    bad["import"] = {"ok": False, "error": "Import refused"}
    check_result(bad, "native error rejected", 1, "Import refused")


def case_layout_switch(root):
    case_rcheck(root, "layout-switch")


def case_no_scale_track(root):
    case_rcheck(root, "no-scale-track")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=(*CASES, "all"), default="all")
    ap.add_argument("--locked", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    cases = CASES if a.case == "all" else (a.case,)
    take = Path(os.environ["EDITOR_SE_TEST_TAKE"]) if os.environ.get("EDITOR_SE_TEST_TAKE") else None
    blocked = 0
    for name in cases:
        sha = build.digest(take) if take else None
        try:
            heavy = name in ("package", "hook-long", "hook-named")
            if heavy and not a.locked:
                if not HEAVY.is_file():
                    print("BLOCKED " + name + ": heavy_lock.py is missing", flush=True)
                    blocked = 75
                    continue
                p = run([sys.executable, "-X", "utf8", "-I", HEAVY, "--wait", "600", "--min-gb", "3", "--",
                         sys.executable, "-X", "utf8", "-I", Path(__file__), "--case", name, "--locked"], timeout=2400)
                print(p.stdout + p.stderr, end="")
                if p.returncode in (75, 76):
                    blocked = p.returncode
                else:
                    ck(name + " locked proof", p.returncode == 0)
                continue
            with tempfile.TemporaryDirectory(prefix="editor-s12-") as temp:
                root = Path(temp)
                with isolated_home(packages=name in ("selftest", "package", "hub", "hook-long", "hook-named")):
                    globals()["case_" + name.replace("-", "_")](root)
        except Exception as e:
            ck(name, False, f"{type(e).__name__}: {e}")
        finally:
            if take:
                ck(name + " take SHA256 unchanged", build.digest(take) == sha)
    print(f"{len(FAILS)} failed" + (f", blocked exit {blocked}" if blocked else ""))
    return 1 if FAILS else blocked


if __name__ == "__main__":
    sys.exit(main())
