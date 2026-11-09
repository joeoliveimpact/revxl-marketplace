"""Step G5 transitions proof; prints PASS/FAIL per check.

Usage: <editor venv python> -X utf8 -I tests/editor/transitions_test.py
       [--case NAME|all] [--scratch DIR] [--reel-src DIR]
Set EDITOR_SE_HOME to the installed editor state. Cases: selftest, gate,
check, pop (light synthetic media), handoff (no browser or render),
handoff-render (synthetic media and export placement), render (heavy 60 s
preview comparison), board (Beat Map iframe Send, reload and refusal).
Render and handoff-render self-lock with the shared
heavy lock, --wait 600 --min-gb 3; exits 75/76 mean blocked. --locked is internal.
The source fixture is read only; all writes are to scratch. The rendered clip
is kept as <scratch>/g5-transitions-reel.mp4. Decoded grey 180x320 frames count
as visibly changed when max abs pixel diff > 40, above this fixture's measured
encoder noise ceiling of 24. Exit 0 only when every selected case passes.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins/editor-superengine"
SCRIPTS = PLUGIN / "skills/reel-canvas-build/scripts"
sys.path[:0] = [str(HERE), str(SCRIPTS), str(PLUGIN / "skills/_shared/checks")]
import transitions as tr
import effect_gate as eg
import beat_schema as bs
import compose
import transition_check as tc
from editor_test_state import isolated_home
import motion_check_test as motion
import canvas_boards_test as boards

rt = compose.rt
HEAVY = Path("C:/Workspaces/Content Studio/output/scripts/heavy_lock.py")
SOURCE = Path("C:/Work/_scratch/editor-superengine-0.2.0/renders/S7/run1/reel")
CASES = ("selftest", "gate", "check", "pop", "handoff", "handoff-render", "render", "board")
FAILS = []
VISIBLE = 40  # Measured H.264 residue on this fixture has max abs pixel diff <= 24.


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (": " + str(detail) if detail and not ok else ""), flush=True)
    if not ok:
        FAILS.append(name)
    return ok


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=rt.python_env(), timeout=kwargs.pop("timeout", 120), **kwargs)


def command(script, *args, **kwargs):
    return run([sys.executable, "-B", "-X", "utf8", "-I", script, *args], **kwargs)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def beat(name="REEL_A", cut=60, typ="flash", dur=3):
    return {"id": name, "layout": "full", "start_f": 0, "end_f": 120,
            "speech_anchor": {"text": "Clear", "w0": 0, "w1": 0}, "value": None, "scene": None, "broll": None,
            "transition": {"type": typ, "at_cut_frame": cut, "dur_frames": dur}}


def invalid_cases():
    base = beat()
    return [("two cuts", [base], [59, 60]),
            ("not a cut", [dict(base, transition=dict(base["transition"], at_cut_frame=61))], [60]),
            ("duplicate cut", [base, dict(base, id="REEL_B")], [60]),
            ("bad type", [dict(base, transition=dict(base["transition"], type="cut"))], [60]),
            ("bad param", [dict(base, transition=dict(base["transition"], dir="l"))], [60]),
            ("bad duration", [dict(base, transition=dict(base["transition"], dur_frames=11))], [60])]


def case_selftest(root, args):
    for name in ("transitions", "effect_gate", "beat_schema", "compose"):
        p = command(SCRIPTS / (name + ".py"), "--selftest")
        ck(name + " selftest", p.returncode == 0 and "selftest ok" in p.stdout, p.stdout + p.stderr)
    p = command(SCRIPTS / "transitions.py", "--menu-json")
    ck("menu JSON", p.returncode == 0 and json.loads(p.stdout) == tr.MENU)
    for name in tr.MENU:
        b = beat(typ=name)
        if tr.MENU[name]["kind"] == "overlay":
            b.update(layout="overlay", scene={"id": "callout", "slots": {"text": "Clear"}})
            b["transition"].update(at_cut_frame=None, edge="both")
        if name == "shader":
            b["transition"]["shader"] = "sdf-iris"
        ck(name + " schema", not bs.beat_problems(b, fps=30))
        if name != "shader":
            layers, lines, vendor, notes = tr.layer({"beats": [b]}, 720, 1280, Fraction(30))
            ck(name + " layer and registered timeline states", "z-index:700" in "".join(layers)
               and any("tl.set(" in line for line in lines) and not vendor
               and not any("onComplete" in line or "Math.random" in line for line in lines))
    inp = {"beats": [beat()], "cut_frames": [60], "rate": Fraction(30), "reel_dir": root,
           "bm": {"transitions": {"allowed": [], "sfx_pair": True}}}
    tr.plan(inp)
    cues = load(root / "work/transition_cues.json")
    ck("sound suggestions only", cues == [{"beat_id": "REEL_A", "type": "flash", "frame": 60, "suggested_sfx_tag": "hit"}])
    inp["bm"]["transitions"]["sfx_pair"] = False
    tr.plan(inp)
    ck("stale cues removed", not (root / "work/transition_cues.json").exists())
    inp["bm"]["transitions"]["allowed"] = ["zoom"]
    try:
        tr.plan(inp)
        ck("allowed narrowing blocks", False)
    except ValueError:
        ck("allowed narrowing blocks", True)
    saved_reel = root / "saved-reel"
    saved_reel.mkdir()
    choices = {"allowed": ["flash", "fade"], "sfx_pair": True}
    motion.write(saved_reel / compose.SEND, {"transitions": choices})
    saved = compose.saved_style.save_from_reel(saved_reel, workspace=root)
    ck("save_from_reel keeps transition taste fields", saved["transitions"] == choices)
    # Leave later availability checks independent of the saved narrowing above.
    compose.saved_style.save({})
    # Force both availability outcomes without launching a browser in this light case.
    shader = beat(typ="shader")
    shader.update(layout="overlay", scene={"id": "callout"})
    shader["transition"].update(at_cut_frame=None, edge="in", shader="glitch")
    for available in (False, True):
        inp.update(beats=[shader], bm={})
        with patch.object(tr, "shader_available", return_value=available), patch.object(tr, "shader_bundle", return_value=Path("vendor.js")):
            tr.plan(inp)
            _, lines, files, notes = tr.layer(inp, 720, 1280, Fraction(30))
        ck("shader availability " + str(available), inp["transition_shader"] == available
           and bool(any("HyperShader.init" in line for line in lines)) == available
           and bool(files) and (tr.FALLBACK in notes) != available)


def case_gate(root, args):
    # The existing test module is an executable harness. Import it once and retain
    # its helpers after its successful SystemExit, rather than copying gate/run/sp.
    spec = importlib.util.spec_from_file_location("g5_gate_helpers", HERE / "effect_gate_test.py")
    helpers = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(helpers)
    except SystemExit as end:
        ck("existing gate suite", end.code in (None, 0))
    helpers.expect("G5 declared cut admitted", helpers.gate(root, "cut", tr.spans([beat()]), [60], total=120), 0)
    for name, beats, cuts in invalid_cases()[:3]:
        spans = tr.spans(beats)
        helpers.expect("G5 " + name, helpers.gate(root, name.replace(" ", "-"), spans, cuts, total=120), 1)
    helpers.expect("G5 planted a-roll transform still blocked", helpers.gate(root, "planted", [helpers.sp("aroll_transform", 57, 63)], [60]), 1)
    fade = dict(beat(), layout="overlay", transition={"type": "fade", "at_cut_frame": None, "dur_frames": 3, "edge": "both"})
    helpers.expect("G5 overlay fade admitted", helpers.gate(root, "overlay", tr.spans([fade]), [60]), 0)
    altered = tr.spans([fade])
    altered[0]["start_f"] = -1
    ck("overlay outside its beat blocked", bool(eg.check(altered, [60], 30, 120)))
    ck("reused gate helper findings", not helpers.fails, helpers.fails)


def cut_doc(frames=(60,), total=120):
    bounds = [0, *frames, total]
    return {"fps": 30, "speed": 1, "segments": [
        {"src_in_f": a, "src_out_f": b, "out_in_f": a, "out_out_f": b} for a, b in zip(bounds, bounds[1:])]}


def case_check(root, args):
    ck("pre phase", tc.PHASE == "pre")
    rows = tc.run({"reel_dir": root, "fps": 30, "cuts": cut_doc(), "beats": [beat()]})
    ck("clean transition", rows == [], rows)
    for name, beats, frames in invalid_cases():
        rows = tc.run({"reel_dir": root, "fps": 30, "cuts": cut_doc(frames), "beats": beats})
        ck("check blocks " + name, any(r["level"] == "block" for r in rows), rows)
        ck("check row contract " + name, all(set(r) == {"check", "level", "msg", "where"}
           and r["check"] == "transition" and "\n" not in r["msg"] for r in rows))
    four = [beat("REEL_" + str(i), c) for i, c in enumerate((30, 60, 90, 120))]
    rows = tc.run({"reel_dir": root, "fps": 30, "cuts": cut_doc((30, 60, 90, 120), 150), "beats": four})
    ck("four is advisory only", len(rows) == 1 and rows[0]["level"] == "warn" and "2-3 usually reads cleanest" in rows[0]["msg"], rows)
    motion.write(root / "work/cuts.json", cut_doc())
    motion.write(root / "beat-map-selection.json", {"fps": 30, "beats": [beat(cut=61)]})
    p = command(PLUGIN / "skills/_shared/checks/transition_check.py", root)
    ck("standalone blocks without traceback", p.returncode == 1 and "block transition:" in p.stdout
       and "Traceback" not in p.stdout + p.stderr, p.stdout + p.stderr)


def case_pop(root, args):
    motion.ENV, motion.FFMPEG, motion.PY = rt.python_env(), rt.tool("ffmpeg"), sys.executable
    import motion_check
    motion.MC = motion_check
    # Reuse the synthetic moving clip pattern and actual detector assertions.
    motion.case_pop(root)
    motion.case_pop_exempt(root)
    ck("reused pop checks", not motion.FAILS, motion.FAILS)
    reel = motion.media(root, "clean-declared")
    motion.write(reel / "beat-map-selection.json", {"fps": 30, "beats": [beat()]})
    ck("clean clip with a declared flash passes", not motion.kinds(motion.check(reel, 0), "block"))


def handoff_beats():
    planted = []
    for i, typ in enumerate(("whip", "zoom", "glitch", "flash", "fade")):
        b = beat("REEL_" + str(i), (i + 1) * 12, typ)
        b.update(start_f=i * 12, end_f=(i + 1) * 12 if i < 3 else 60 if i == 3 else 84)
        if typ == "fade":
            b.update(start_f=60, layout="overlay")
            b["transition"].update(at_cut_frame=None, edge="both")
        planted.append(b)
    return planted


def case_handoff(root, args):
    import handoff_test as handoff

    beats = handoff_beats()
    expected = [{"start_f": c - 3, "end_f": c + 3, "layout": "transition"} for c in (12, 24, 36)]
    ck("handoff fixture declarations are valid", not tr.problems(beats, [12, 24, 36, 48], 30))
    spans = compose.baked_spans({}, beats, 84)
    ck("only moving cut transitions need the finished picture", spans == expected, spans)
    # The summary must also describe transitions when they merge with a layout.
    for label in ("transition", "pip+transition", "overlay+pip+transition"):
        note = handoff.build.baked_note([dict(expected[0], layout=label)], Fraction(30))
        ck("plain finished-picture note for " + label, "transition" in note and "0:00.3-0:00.5" in note
           and "\n" not in note, note)
    note = handoff.build.baked_note(expected, Fraction(30))
    ck("transition summary counts and names its windows", "3 parts use the finished picture because their transition movement" in note
       and all(text in note for text in ("0:00.3-0:00.5", "0:00.7-0:00.9", "0:01.1-0:01.3")), note)
    inp = {"rate": Fraction(30), "total": 84, "beats": beats, "under": [], "hook_f": 0,
           "hook_text": "", "track": {"keys": [], "tweens": [], "style": {}}}
    full = compose.main_html(inp, 720, 1280, [])
    aroll = compose.main_html(inp, 720, 1280, [], layers="aroll")
    overlay = compose.main_html(inp, 720, 1280, [], layers="overlay")
    ck("finished picture retains the a-roll transition moves", 'tl.set("#g5-aroll-move"' in full
       or 'tl.fromTo("#g5-aroll-move"' in full)
    ck("a-roll handoff never applies a transition twice", not any(
        "#g5-aroll-move" in line for line in aroll.splitlines() if "tl." in line))
    ck("overlay hides on every finished-picture boundary", all(
        f'tl.set("#handoff-overlay", {{ opacity: {opacity}, immediateRender: false }}, {compose.at(frame, Fraction(30))});'
        in overlay for s in expected for frame, opacity in ((s["start_f"], 0), (s["end_f"], 1))))


def case_handoff_render(root, args):
    # Reuse the handoff suite's synthetic fixture and real export helpers. No
    # compositor is needed, but fixture media creation belongs under the lock.
    import handoff_test as handoff

    reel, master = handoff.fixture(root)
    beats = handoff_beats()
    bm = load(reel / compose.SEND)
    bm.update(beats=beats, edit_style={"style": "punch-in", "punch_scale": 1,
              "moves": {"opening_settle": False, "follow_cam": False}})
    handoff.build.save(reel / compose.SEND, bm)
    handoff.build.save(reel / "work/cuts.json", cut_doc((12, 24, 36, 48), 84))
    handoff.build.save(reel / "work/scale_track.json", {
        "keys": [{"f": 0, "layout": "full", "scale": 1, "ox": .5, "oy": .38}],
        "tweens": [], "style": bm["edit_style"], "total_f": 84, "fps": "30/1"})
    expected = compose.baked_spans({}, beats, 84)
    try:
        handoff.fcpx.load_model(reel, master, None)
    except handoff.fcpx.Stop as error:
        ck("moving transitions require the finished Master", error.code == 1
           and str(error) == compose.NEED_BAKED_MASTER and "transitions" in str(error))
    else:
        ck("moving transitions require the finished Master", False)
    finished = reel / "renders/REEL_A Master - 11.06.26.mp4"
    shutil.copyfile(master, finished)  # Synthetic finished picture, as in handoff_test.case_fcpxml.
    media = handoff.build.derive_media(reel, master, finished)
    out = reel / "handoff/transitions.fcpxml"
    summary = handoff.fcpx.write(reel, master, None, out, **media)
    ck("moving transition spans reach the export summary", summary["baked_spans"] == expected
       and len(expected) == 3, summary["baked_spans"])
    note = handoff.build.baked_note(summary["baked_spans"], Fraction(30))
    ck("export summary explains the transitions", "3 parts use the finished picture because their transition movement" in note, note)
    tree = handoff.ET.parse(out)
    clips = tree.findall('.//asset-clip[@lane="4"]')
    refs = {a.get("id"): a.find("media-rep").get("src") for a in tree.findall("resources/asset")}
    windows = [(handoff.fcpx.seconds(c.get("offset")) * 30,
                (handoff.fcpx.seconds(c.get("offset")) + handoff.fcpx.seconds(c.get("duration"))) * 30)
               for c in clips]
    ck("finished-picture lane covers every moving window exactly", windows == [(9, 15), (21, 27), (33, 39)], windows)
    ck("finished-picture clips preserve source time and exclude audio", all(
        c.get("start") == c.get("offset") and c.get("srcEnable") == "video"
        and handoff.fcpx.uri_path(refs[c.get("ref")]) == media["master_picture"].resolve() for c in clips)
       and not handoff.fcpx.probe(media["master_picture"])["audio"])
    ck("flash and fade keep their overlay windows", all(
        not (a < s["end_f"] and s["start_f"] < b)
        for s in tr.spans(beats[3:]) for a, b in windows))
    ck("transition FCPXML checks", handoff.fcpx.check(out) == [], handoff.fcpx.check(out))
    legacy = out.with_suffix(".xml")
    handoff.legacy.write_fcp7(reel, master, None, legacy)
    legacy_clips = handoff.ET.parse(legacy).findall("sequence/media/video/track")[3].findall("clipitem")
    ck("FCP7 keeps the same finished-picture windows", [(int(c.findtext("start")), int(c.findtext("end")))
       for c in legacy_clips] == windows and handoff.legacy.check_fcp7(legacy) == [])


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def decoded_frames(path):
    import numpy as np

    p = subprocess.run([str(rt.tool("ffmpeg")), "-v", "error", "-i", str(path), "-map", "0:v:0",
                        "-vf", "scale=180:320", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, env=rt.python_env(), timeout=300)
    if p.returncode:
        raise ValueError("Frame comparison could not decode the render: " + p.stderr.decode("utf-8", errors="replace")[-200:])
    if len(p.stdout) % (180 * 320):
        raise ValueError("Frame comparison decoded an incomplete grey frame")
    return np.frombuffer(p.stdout, dtype=np.uint8).reshape(-1, 320, 180)


def case_render(root, args):
    source = Path(args.reel_src).resolve()
    if not source.is_dir():
        raise ValueError("The 60 s source fixture is missing; supply --reel-src")
    source_files = [source / "beat-map-selection.json", source / "work/cuts.json", *sorted((source / "work/renders").glob("master-*.mp4"))]
    before = {p: digest(p) for p in source_files}
    run_dir = Path(tempfile.mkdtemp(prefix="render-", dir=root))
    reel = run_dir / "videos/REEL_A"
    try:
        shutil.copytree(source, reel)
        # Only the scratch Send changes; the fixture's cut master and voice stay intact.
        bm = load(reel / compose.SEND)
        bm.pop("loops", None)
        bm.update(reel="REEL_A", transitions={"allowed": [], "sfx_pair": False})
        for b in bm["beats"]:
            b.update(scene=None, broll=None, transition=None)
        if len(bm["beats"]) < 4:
            raise ValueError("The segment fixture needs four solid beats for the four cut effects")
        for b, typ, c in zip(bm["beats"], ("flash", "whip", "zoom", "glitch"), (150, 300, 450, 600)):
            b["transition"] = {"type": typ, "at_cut_frame": c, "dur_frames": 6}
        for j, typ in enumerate(("fade", "push", "wipe", "shader")):
            ob = copy.deepcopy(bm["beats"][0])
            ob.update(id="overlay_" + typ, start_f=720 + j * 210, end_f=780 + j * 210, layout="overlay", value=None,
                      scene={"id": "callout", "slots": {"text": "Clear next step"}}, broll=None,
                      transition={"type": typ, "at_cut_frame": None, "dur_frames": 6, "edge": "both"})
            if typ == "shader":
                ob["transition"]["shader"] = "sdf-iris"
            bm["beats"].append(ob)
        bm["beats"].sort(key=lambda b: b["start_f"])
        # Keep an explicit simple style equal in both renders.
        bm["edit_style"] = {"style": "punch-in", "punch_scale": 1, "moves": {"opening_settle": False, "follow_cam": False}}
        bm["caption_style"] = {"style": "none"}
        motion.write(reel / compose.SEND, bm)
        motion.write(reel / "work/cuts.json", cut_doc(tuple(range(150, 1800, 150)), 1800))
        shutil.rmtree(reel / "sound", ignore_errors=True)
        inp = compose.load_inputs(reel)
        compose.probe_inputs(inp)
        ck("source is 60 s at 30 fps", inp["total"] == 1800 and inp["rate"] == 30)
        if inp["total"] != 1800 or inp["rate"] != 30:
            return
        compose.plan(inp, None)
        ck("gate admits all planted transitions", not eg.check(compose.build_spans(inp["beats"], {"callout": "overlay"}, inp["hook_f"]),
           inp["cut_frames"], inp["fps"], inp["total"]))
        print("shader path: " + ("WebGL" if inp["transition_shader"] else tr.FALLBACK), flush=True)
        first = compose.render(reel, "preview", None, keep_project=True, remember_choices=False)
        rendered = root / "g5-transitions-reel.mp4"
        shutil.copy2(reel / first["out"], rendered)
        # Retain the exact generated project as evidence for pre-encode investigation.
        if (reel / "work/render-tmp/proj/index.html").is_file():
            shutil.copy2(reel / "work/render-tmp/proj/index.html", root / "transition-render.html")
        plain = copy.deepcopy(bm)
        for b in plain["beats"]:
            b["transition"] = None
        motion.write(reel / compose.SEND, plain)
        second = compose.render(reel, "preview", None, remember_choices=False)
        baseline = root / "g5-baseline.mp4"
        shutil.copy2(reel / second["out"], baseline)
        import numpy as np

        a, b = decoded_frames(rendered), decoded_frames(baseline)
        if not ck("equal frame counts", len(a) == len(b) == 1800, (len(a), len(b))):
            return
        # Widen before subtracting so uint8 wrap cannot turn noise into a change.
        max_diff = [int(np.abs(left.astype(np.int16) - right.astype(np.int16)).max())
                    for left, right in zip(a, b)]
        changed = {f for f, peak in enumerate(max_diff) if peak > VISIBLE}
        spans = tr.spans(bm["beats"])
        allowed = {f for s in spans for f in range(s["start_f"], s["end_f"])}
        outside_max = max((peak for f, peak in enumerate(max_diff) if f not in allowed), default=0)
        print("outside-window max abs diff (noise level): " + str(outside_max), flush=True)
        ck("no visible changes outside declared windows", changed <= allowed, sorted(changed - allowed)[:30])
        for s in spans:
            window_changed = sorted(f for f in changed if s["start_f"] <= f < s["end_f"])
            if tr.MENU[s["transition"]["type"]]["kind"] == "cut":
                ck("snapped visible bounds " + s["id"],
                   bool(window_changed) and (window_changed[0], window_changed[-1]) == (s["start_f"], s["end_f"] - 1), window_changed)
                if s["transition"]["type"] == "glitch":
                    ck("glitch visible on every window frame", window_changed == list(range(s["start_f"], s["end_f"])), window_changed)
            else:
                ck("overlay window renders " + s["id"] + " " + str(s["start_f"]), bool(window_changed), window_changed)
        audio = [compose.packet_md5(path, "a") for path in (rendered, baseline, inp["master"])]
        ck("voice packet MD5 unchanged", bool(audio[0]) and len(set(audio)) == 1, audio)
        motion.write(reel / compose.SEND, bm)
        import motion_check
        rows = motion_check.run({"reel_dir": reel, "render": rendered, "fps": 30, "cuts": inp["cuts"], "beats": bm["beats"]})
        ck("motion check on transitions render", not any(row["level"] == "block" for row in rows), rows)
        print("clip: " + str(rendered), flush=True)
    finally:
        ck("source fixture unchanged", all(p.is_file() and digest(p) == sha for p, sha in before.items()))


BOARD_BROWSER = r"""
const fs = require('fs'), {pathToFileURL} = require('url');
(async()=>{
const [pup, chrome, jobPath] = process.argv.slice(1), job=JSON.parse(fs.readFileSync(jobPath,'utf8'));
const {default:p}=await import(pathToFileURL(pup).href);
const browser=await p.launch({executablePath:chrome,headless:'shell',args:['--no-sandbox'],userDataDir:job.profile});
try {
 const page=await browser.newPage(), errors=[];
 page.setDefaultTimeout(15000); page.on('pageerror', e=>errors.push(String(e)));
 const need=(ok,msg)=>{if(!ok)throw new Error(msg);};
 await page.goto(job.url,{waitUntil:'load'}); await page.waitForFunction('window.Hub && Hub.ready');
 await page.click('#tab-beat-map');
 let frame=await (await page.waitForSelector('iframe')).contentFrame();
 await frame.waitForSelector('#transition-0');
 need(await frame.$eval('#transition-0', e=>e.value)==='', 'a transition was selected automatically');
 await frame.select('#transition-0','flash');
 await frame.select('#transition-at_cut_frame-0','120');
 await frame.$eval('#transition-dur_frames-0', e=>{e.value='4';e.dispatchEvent(new Event('input',{bubbles:true}));});
 await frame.evaluate(()=>send()); await frame.waitForSelector('#status[data-state=sent]');
 const sent=JSON.parse(fs.readFileSync(job.selection,'utf8'));
 need(JSON.stringify(sent.beats[0].transition)===JSON.stringify({type:'flash',at_cut_frame:120,dur_frames:4}), 'transition Send shape differs');
 await page.reload({waitUntil:'load'}); await page.waitForFunction('window.Hub && Hub.ready');
 await page.click('#tab-beat-map');
 frame=await (await page.waitForSelector('iframe')).contentFrame();
 await frame.waitForSelector('#transition-0');
 need(await frame.$eval('#transition-0', e=>e.value)==='flash', 'saved transition type did not reload');
 need(await frame.$eval('#transition-at_cut_frame-0', e=>e.value)==='120', 'saved transition cut did not reload');
 need(await frame.$eval('#transition-dur_frames-0', e=>e.value)==='4', 'saved transition duration did not reload');
 const before=fs.readFileSync(job.selection,'utf8');
 await frame.$eval('#transition-dur_frames-0', e=>{e.value='100';e.dispatchEvent(new Event('input',{bubbles:true}));});
 await frame.evaluate(()=>send()); await frame.waitForSelector('#status[data-state=error]');
 need(fs.readFileSync(job.selection,'utf8')===before, 'invalid transition reached Send');
 need(await frame.evaluate(()=>typeof problem()==='string'), 'problem did not explain refusal');
 need(errors.length===0, errors.join('; '));
 console.log(JSON.stringify({ok:true}));
} finally {await browser.close();}
})().catch(e=>{console.log(JSON.stringify({ok:false,error:String(e)}));process.exitCode=1;});
"""


def case_board(root, args):
    tools, missing = boards.find_tools()
    if missing:
        raise ValueError("Board proof needs the installed " + ", ".join(missing))
    ws = root / "ws"
    port = boards.free_port()
    if not boards.check_deps.write_config(ws, ports={"board": port}, engine=None, nle="none"):
        raise ValueError("Could not prepare the board configuration")
    reel = ws / "videos/REEL_A"
    boards.reel_fixture(reel)
    p = command(boards.SEED, "--reel-dir", reel, "--plan", reel / "work/plan.json", cwd=ws)
    if p.returncode:
        raise ValueError("Board fixture seed failed: " + p.stdout + p.stderr)
    bm = load(reel / "beat-map.state.json")
    bm["edit_style"] = {"style": "punch-in", "punch_scale": 1.12}
    motion.write(reel / "beat-map.state.json", bm)
    proc = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-I", str(boards.SERVER), "--root", str(ws)],
                            env=rt.python_env(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    timer = threading.Timer(20, proc.kill)
    try:
        timer.start()
        line = proc.stdout.readline().strip()
        timer.cancel()
        if not line.startswith("Editor boards: http://127.0.0.1:"):
            raise ValueError("Board server did not start: " + line)
        for name in ("board_sync.py", "hub_rows.py"):
            p = command(boards.DOCTOR / name, "--root", ws, cwd=ws)
            if p.returncode:
                raise ValueError("Hub setup failed: " + p.stdout + p.stderr)
        url = line.split("Editor boards: ", 1)[1] + "editor/hub/?reel=REEL_A"
        job = root / "board-job.json"
        motion.write(job, {"url": url, "profile": str(root / "profile"), "selection": str(reel / compose.SEND)})
        p = boards.run([tools["node"], "-e", BOARD_BROWSER, tools["pup"], tools["chrome"], str(job)])
        ck("Beat Map iframe Send, saved controls after reload and invalid refusal",
           p.returncode == 0 and '"ok":true' in p.stdout, p.stdout + p.stderr)
        if p.returncode:
            return
        sent = load(reel / compose.SEND)
        bs.validate_beat_map(sent, boards.WORDS)
        cuts = load(reel / "work/cuts.json")
        inp = {"beats": sent["beats"], "bm": sent, "words": boards.WORDS, "rate": Fraction(30), "fps": "30/1",
               "cuts": cuts, "cut_frames": [120], "total": boards.TOTAL_F, "reel_dir": reel}
        compose.plan(inp, None)
        ck("compose accepts board Send", inp["hook_f"] > 0)
    finally:
        timer.cancel()
        proc.terminate()
        proc.wait(timeout=15)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=(*CASES, "all"), default="all")
    ap.add_argument("--scratch", default=None)
    ap.add_argument("--reel-src", default=str(SOURCE))
    ap.add_argument("--locked", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    root = Path(args.scratch).resolve() if args.scratch else Path(tempfile.mkdtemp(prefix="editor-g5-"))
    root.mkdir(parents=True, exist_ok=True)
    print("scratch: " + str(root), flush=True)
    blocked = 0
    for name in CASES if args.case == "all" else (args.case,):
        if name in ("render", "handoff-render") and not args.locked:
            if not HEAVY.is_file():
                print("BLOCKED " + name + ": heavy_lock.py is missing", flush=True)
                blocked = 75
                continue
            p = run([sys.executable, "-X", "utf8", "-I", HEAVY, "--wait", "600", "--min-gb", "3", "--",
                     sys.executable, "-X", "utf8", "-I", Path(__file__), "--case", name, "--locked",
                     "--scratch", root, "--reel-src", args.reel_src], timeout=2400)
            print(p.stdout + p.stderr, end="")
            if p.returncode in (75, 76):
                blocked = p.returncode
            else:
                ck("locked " + name + " proof", p.returncode == 0)
            continue
        try:
            target = root if name == "render" else root / name
            target.mkdir(parents=True, exist_ok=True)
            with isolated_home(packages=name in ("render", "board")):
                globals()["case_" + name.replace("-", "_")](target, args)
        except Exception as error:
            ck(name, False, " ".join(str(error).splitlines()))
    print(f"{len(FAILS)} failed" + (f", blocked exit {blocked}" if blocked else ""), flush=True)
    return 1 if FAILS else blocked


if __name__ == "__main__":
    sys.exit(main())
