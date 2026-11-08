"""G5 no-handle transitions: the menu, validation, gate spans and root-timeline layers.

Cut durations are frames EACH SIDE: [cut-dur, cut+dur). Overlay windows stay inside
their beat. Nothing is selected by default and no audio is added here.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
import fps as fpsmod
import runtime as rt
import saved_style
from win_encoding import ensure_utf8_output

SHADERS = ["light-leak", "sdf-iris", "chromatic-split", "cross-warp-morph", "flash-through-white", "glitch"]
MENU = {
    "flash": {"kind": "cut", "params": {"color": "color"}, "dur_min": 1, "dur_max": "ceil(fps/3)"},
    "whip": {"kind": "cut", "moves_aroll": True, "params": {"dir": ["l", "r", "u", "d"]}, "dur_min": 1, "dur_max": "ceil(fps/3)"},
    "zoom": {"kind": "cut", "moves_aroll": True, "params": {}, "dur_min": 1, "dur_max": "ceil(fps/3)"},
    "glitch": {"kind": "cut", "moves_aroll": True, "params": {}, "dur_min": 1, "dur_max": "ceil(fps/3)"},
    "fade": {"kind": "overlay", "params": {}, "dur_min": 1, "dur_max": "min(fps,beat_length/2)"},
    "push": {"kind": "overlay", "params": {"dir": ["l", "r", "u", "d"]}, "dur_min": 1, "dur_max": "min(fps,beat_length/2)"},
    "wipe": {"kind": "overlay", "params": {"dir": ["l", "r", "u", "d"]}, "dur_min": 1, "dur_max": "min(fps,beat_length/2)"},
    "shader": {"kind": "overlay", "params": {"shader": SHADERS}, "dur_min": 1, "dur_max": "min(fps,beat_length/2)"},
}
FALLBACK = "shader not available on this machine, used a fade"


def integer(v):
    return isinstance(v, int) and not isinstance(v, bool)


def options_problems(options):
    if options is None:
        return []
    if not isinstance(options, dict):
        return ["Transition choices need an object with allowed and sfx_pair"]
    out = []
    if set(options) - {"allowed", "sfx_pair"}:
        out.append("Transition choices have unknown settings; use allowed and sfx_pair")
    allowed = options.get("allowed")
    if allowed is not None and (not isinstance(allowed, list) or any(not isinstance(t, str) or t not in MENU for t in allowed)):
        out.append("The allowed transition list needs types from the transition menu")
    if "sfx_pair" in options and not isinstance(options["sfx_pair"], bool):
        out.append("Transition sound pairing must be true or false")
    return out


def beat_problems(beat, fps=None):
    """Shape and duration rules, with no cut membership check (schema uses this too)."""
    t = beat.get("transition")
    if t is None:
        return []
    where = "beat " + str(beat.get("id", "?")) + " transition"
    if not isinstance(t, dict):
        return [where + " is not an object; choose a transition or none"]
    name = t.get("type")
    if not isinstance(name, str) or name not in MENU:
        return [where + " needs a type from the transition menu"]
    spec = MENU[name]
    keys = {"type", "at_cut_frame", "dur_frames"} | set(spec["params"])
    required = {"type", "at_cut_frame", "dur_frames"}
    out = []
    if spec["kind"] == "overlay":
        if not (integer(beat.get("start_f")) and integer(beat.get("end_f")) and 0 <= beat["start_f"] < beat["end_f"]):
            out.append(where + " needs whole start and end frames for its overlay beat")
        keys.add("edge")
        required.add("edge")
    if name == "shader":
        required.add("shader")
    if set(t) - keys:
        out.append(where + " has unknown keys " + ", ".join(sorted(set(t) - keys)))
    if required - set(t):
        out.append(where + " is missing " + ", ".join(sorted(required - set(t))))
    d = t.get("dur_frames")
    hi = None
    if fps is not None:
        try:
            rate = fpsmod.as_fraction(str(fps))
            hi = math.ceil(rate / 3) if spec["kind"] == "cut" else math.floor(rate)
        except ValueError:
            return [where + " needs the reel's positive frame rate"]
    if spec["kind"] == "overlay":
        if t.get("at_cut_frame") is not None:
            out.append(where + " needs at_cut_frame null for an overlay")
        if t.get("edge") not in ("in", "out", "both"):
            out.append(where + " needs edge in, out or both")
        if not (beat.get("layout") == "overlay" or beat.get("scene") or beat.get("broll")):
            out.append(where + " needs an overlay layout, scene or B-roll")
        if name == "shader" and not beat.get("scene"):
            out.append(where + " needs a scene for a shader")
        if integer(beat.get("start_f")) and integer(beat.get("end_f")):
            half = (beat["end_f"] - beat["start_f"]) // 2
            hi = half if hi is None else min(hi, half)
    elif not integer(t.get("at_cut_frame")) or t["at_cut_frame"] <= 0:
        out.append(where + " needs a whole cut frame greater than zero")
    if not integer(d) or d < 1 or (hi is not None and d > hi):
        out.append(where + " dur_frames must be a whole number from 1 to " + (str(hi) if hi is not None else "the frame limit"))
    for key, choices in spec["params"].items():
        if key not in t:
            continue
        value = t[key]
        valid = (isinstance(value, str) and (value in ("white", "black") or
                 re.fullmatch(r"#[0-9a-fA-F]{6}", value))) if choices == "color" else isinstance(value, str) and value in choices
        if not valid:
            out.append(where + " has an invalid " + key + "; choose a value from its control")
    return out


def spans(beats):
    """Transition spans carry their declaration so the gate cannot exempt an untyped effect."""
    out = []
    for b in beats:
        t = b.get("transition")
        if not isinstance(t, dict) or not integer(t.get("dur_frames")):
            continue
        spec = MENU.get(t.get("type")) if isinstance(t.get("type"), str) else None
        if spec is None:
            continue
        base = {"layer": "transition", "id": b.get("id", "?"), "transition": t,
                "beat_start_f": b.get("start_f"), "beat_end_f": b.get("end_f"),
                "beat": b}
        d, c = t["dur_frames"], t.get("at_cut_frame")
        if spec["kind"] == "cut" and integer(c):
            out.append(dict(base, start_f=c - d, end_f=c + d))
        elif spec["kind"] == "overlay" and integer(b.get("start_f")) and integer(b.get("end_f")):
            if t.get("edge") in ("in", "both"):
                out.append(dict(base, start_f=b["start_f"], end_f=b["start_f"] + d))
            if t.get("edge") in ("out", "both"):
                out.append(dict(base, start_f=b["end_f"] - d, end_f=b["end_f"]))
    return out


def problems(beats, cut_frames, fps, allowed=None):
    try:
        rate = fpsmod.as_fraction(str(fps))
    except (ValueError, TypeError, ZeroDivisionError):
        return ["Transitions need the reel's frame rate"]
    if not isinstance(beats, list) or not all(isinstance(b, dict) for b in beats):
        return ["Transitions need a list of beats"]
    if allowed is not None and (not isinstance(allowed, list) or any(not isinstance(t, str) or t not in MENU for t in allowed)):
        return ["The saved transition menu has an unknown type; choose types from the transition menu"]
    out, seen = [], set()
    shader_end = -1
    for b in beats:
        bad = beat_problems(b, rate)
        out.extend(bad)
        t = b.get("transition")
        if bad or t is None:
            continue
        if allowed and t["type"] not in allowed:
            out.append("beat " + str(b.get("id", "?")) + " transition is outside the saved allowed menu")
        if t["type"] == "shader":
            if b["start_f"] < shader_end:
                out.append("Shader scene beats cannot overlap with this pinned renderer; choose fade on one beat")
            shader_end = max(shader_end, b["end_f"])
        if MENU[t["type"]]["kind"] == "cut":
            c, d = t["at_cut_frame"], t["dur_frames"]
            if cut_frames is not None and (c not in cut_frames or sum(c - d < f < c + d for f in cut_frames) != 1):
                out.append("beat " + str(b.get("id", "?")) + " transition must cover exactly one cut and name that cut")
            if c - d < 0:
                out.append("The transition starts before the master; choose a shorter duration")
            if c in seen:
                out.append("Two transitions name the same cut at frame " + str(c) + "; keep one")
            seen.add(c)
    return out


def shader_bundle():
    package = rt.state_dir() / "hyperframes/node_modules/@hyperframes/shader-transitions"
    if json.loads((package / "package.json").read_text(encoding="utf-8")).get("version") != "0.8.184":
        raise ValueError("The shader package needs the pinned version 0.8.184; repair the editor setup")
    bundle = package / "dist/index.global.js"
    if not bundle.is_file():
        raise ValueError("The installed shader bundle is missing; repair the editor setup")
    return bundle


def shader_available():
    """Probe the installed render browser, using the render environment; no downloads."""
    shader_bundle()
    pup = rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
    script = r"""const {pathToFileURL}=require('url');
(async()=>{const {default:p}=await import(pathToFileURL(process.argv[1]).href);
const b=await p.launch({executablePath:process.argv[2],headless:'shell',args:['--no-sandbox']});
try {const page=await b.newPage(); console.log(await page.evaluate(()=>!!document.createElement('canvas').getContext('webgl')) ? 'webgl' : 'fade');}
finally {await b.close();}})().catch(()=>process.exit(1));"""
    p = subprocess.run([str(rt.tool("node")), "-e", script, str(pup), str(rt.tool("chrome"))],
                       capture_output=True, text=True, encoding="utf-8", env=rt.hyperframes_env(), timeout=45)
    answer = p.stdout.strip().splitlines()
    if p.returncode or not answer or answer[-1] not in ("webgl", "fade"):
        raise ValueError("The shader availability check could not run; repair the editor setup and try again")
    return answer[-1] == "webgl"


def plan(inp):
    saved = saved_style.load(inp.get("style_reel", inp.get("reel_dir")))
    bad = options_problems((inp.get("bm") or {}).get("transitions"))
    if bad:
        raise ValueError(" ".join(bad))
    allowed, _ = saved_style.resolve("transitions.allowed", reel=inp.get("bm"), saved=saved)
    bad = problems(inp["beats"], inp["cut_frames"], inp["rate"], allowed)
    if bad:
        raise ValueError(" ".join(bad))
    gate_bad = []
    if "total" in inp:
        for span in spans(inp["beats"]):
            if span["end_f"] > inp["total"]:
                gate_bad.append("The transition ends past the master; choose a shorter duration")
    if gate_bad:
        raise ValueError(gate_bad[0])
    inp["transition_shader"] = False
    if any((b.get("transition") or {}).get("type") == "shader" for b in inp["beats"]):
        inp["transition_shader"] = shader_available()
        print("note: shader path: WebGL" if inp["transition_shader"] else "note: " + FALLBACK)
    paired, _ = saved_style.resolve("transitions.sfx_pair", reel=inp.get("bm"), saved=saved)
    if paired is not None and not isinstance(paired, bool):
        raise ValueError("Transition sound pairing must be true or false in the saved style")
    if "reel_dir" not in inp:  # Pure compose selftests have no files or reel folder.
        return
    path = Path(inp["reel_dir"]) / "work/transition_cues.json"
    if paired is True:
        cues = []
        for span in spans(inp["beats"]):
            t = span["transition"]
            cues.append({"beat_id": span["id"], "type": t["type"],
                         "frame": t["at_cut_frame"] if MENU[t["type"]]["kind"] == "cut" else span["start_f"],
                         "suggested_sfx_tag": {"flash": "hit", "glitch": "digital"}.get(t["type"], "whoosh")})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(cues, indent=1) + "\n").encode("utf-8"))
    else:
        path.unlink(missing_ok=True)


def copy_vendor(inp, project, which="all"):
    if which in ("all", "overlay") and any((b.get("transition") or {}).get("type") == "shader" for b in inp["beats"]):
        shutil.copy2(shader_bundle(), project / "vendor/shader-transitions.js")


def layer(inp, w, h, rate):
    """One layer per declaration. Every state change is a frame-snapped root tl.set.

    A dedicated nested a-roll wrapper isolates transition state from the editing style.
    Overlay wrappers contain only that beat's own scene, B-roll or card plate.
    """
    layers, lines, vendors, notes = [], [], [], []
    shader_jobs = []
    beats = inp.get("beats", [])
    time = lambda f: str(math.floor(Fraction(f) / rate * 1_000_000) / 1_000_000)

    def state(selector, values, frame):
        lines.append(f'tl.set({json.dumps(selector)}, {json.dumps(dict(values, immediateRender=False))}, {time(frame)});')

    active = [(i, b) for i, b in enumerate(beats) if b.get("transition")]
    if any(b["transition"]["type"] == "shader" for _, b in active):
        layers.append('<script src="./vendor/shader-transitions.js"></script>')
        # Hidden by CSS until its window (a tl.set at 0 does not render at frame 0, lint
        # gsap_timeline_set_initial_hide); the root tl shows it only inside each window.
        layers.append('<style>#gl-canvas, #__hf-page-side-compositor{z-index:700;opacity:0}</style>')
        vendors = [(shader_bundle(), "shader-transitions.js")]
    if any(b["transition"]["type"] in ("whip", "zoom", "glitch") for _, b in active):
        lines.append('const g5Move = document.getElementById("aroll-move"); if (g5Move) { const wrap = document.createElement("div"); '
                     'wrap.id = "g5-aroll-move"; wrap.style.cssText = "width:100%;height:100%;position:absolute"; '
                     'g5Move.parentNode.insertBefore(wrap, g5Move); wrap.appendChild(g5Move); }')
    for i, b in active:
        t, name = b["transition"], "g5-transition-" + str(i)
        typ, d = t["type"], t["dur_frames"]
        el = "#" + name
        scene_class = " scene" if typ == "shader" and inp.get("transition_shader") else ""
        resting = "visibility:hidden" if MENU[typ]["kind"] == "cut" else "display:contents"
        layers.append(f'<div id="{name}" class="band{scene_class}" '
                      f'style="z-index:700;pointer-events:none;{resting}"></div>')
        if MENU[typ]["kind"] == "cut":
            c = t["at_cut_frame"]
            start, end = c - d, c + d
            if typ == "whip":
                layers.append(f'<svg width="0" height="0" aria-hidden="true"><defs><filter id="{name}-blur" '
                              'x="-20%" y="-20%" width="140%" height="140%">'
                              f'<feGaussianBlur id="{name}-blur-amount" stdDeviation="0 0"/></filter></defs></svg>')
            if typ == "glitch":
                layers.append(f'<svg width="0" height="0" aria-hidden="true"><defs><filter id="{name}-rgb" '
                              'x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">'
                              '<feColorMatrix in="SourceGraphic" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0" result="red"/>'
                              f'<feOffset id="{name}-red" in="red" result="redShift"/>'
                              '<feColorMatrix in="SourceGraphic" values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0" result="green"/>'
                              '<feColorMatrix in="SourceGraphic" values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0" result="blue"/>'
                              f'<feOffset id="{name}-blue" in="blue" result="blueShift"/>'
                              '<feBlend in="redShift" in2="green" mode="screen" result="rg"/>'
                              '<feBlend in="rg" in2="blueShift" mode="screen"/></filter></defs></svg>')
            for f in range(start, end):
                p = (f - start + 1) / (d + 1) if f < c else (end - f) / d
                values = {"autoAlpha": p}
                if typ == "flash":
                    values["backgroundColor"] = t.get("color", "white")
                elif typ == "whip":
                    dx, dy = {"l": (-1, 0), "r": (1, 0), "u": (0, -1), "d": (0, 1)}[t.get("dir", "r")]
                    angle = 90 if dx else 0
                    values.update(background=f"linear-gradient({angle}deg,transparent,rgba(255,255,255,.55),transparent)", x=dx * w * (p - .5), y=dy * h * (p - .5))
                    state("#g5-aroll-move", {"x": dx * w * .045 * p, "y": dy * h * .045 * p,
                                            "filter": f"url(#{name}-blur)", "scale": 1 + p * .1}, f)
                    state("#" + name + "-blur-amount", {"attr": {"stdDeviation": f"{abs(dx) * p * 18:g} {abs(dy) * p * 18:g}"}}, f)
                elif typ == "zoom":
                    values.update(background="radial-gradient(ellipse,transparent,rgba(255,255,255,.22))")
                    state("#g5-aroll-move", {"scale": 1 + p * .23, "filter": f"blur({p * 3:g}px)"}, f)
                else:
                    seed = int.from_bytes(hashlib.sha256((str(b["id"]) + ":" + str(f)).encode()).digest()[:4], "big")
                    # Do not taper displacement to zero at the window edges (or
                    # let a seeded zero sample erase a frame of the transition).
                    shift = (-1 if seed & 1 else 1) * (12 + seed % 13)
                    values.update(background="repeating-linear-gradient(0deg,rgba(255,0,70,.28) 0 9px,transparent 9px 31px,rgba(0,240,255,.28) 31px 42px)",
                                  clipPath=f"inset({seed % 35}% 0 {seed % 23}% 0)", x=shift)
                    state("#g5-aroll-move", {"x": shift, "filter": f"url(#{name}-rgb)"}, f)
                    state("#" + name + "-red", {"attr": {"dx": 2 + abs(shift), "dy": seed % 3 - 1}}, f)
                    state("#" + name + "-blue", {"attr": {"dx": -2 - abs(shift), "dy": 1 - seed % 3}}, f)
                state(el, values, f)
            state(el, {"autoAlpha": 0, "x": 0, "y": 0}, end)
            if typ in ("whip", "zoom", "glitch"):
                state("#g5-aroll-move", {"x": 0, "y": 0, "scale": 1, "filter": "none"}, end)
            continue
        # Keep ids identical to compose.safe_id / broll_name, without importing compose.
        bid = b["id"] if re.fullmatch(r"[A-Za-z0-9_-]+", b["id"]) else None
        selectors = []
        scened = [a for a in beats if a.get("scene")]
        if b.get("scene"):
            si = scened.index(b)
            selectors.append("#scene-" + (bid or f"beat-{si}"))
        if b.get("broll"):
            bi = [a for a in beats if a.get("broll")].index(b)
            selectors.append("#broll-" + (bid or f"beat-{bi}") + "-" + str(bi))
        if b["layout"] != "full":
            pi = [a for a in beats if a["layout"] != "full"].index(b)
            selectors.append("#plate-" + str(pi))
        lines.append(f'for (const selector of {json.dumps(selectors)}) {{ const target = document.querySelector(selector); '
                     f'if (target) document.getElementById({json.dumps(name)}).appendChild(target.tagName === "VIDEO" ? target.parentNode : target); }}')
        # display:contents outside the windows leaves the original scene/B-roll/plate
        # band in its original stacking order, including beneath captions and PIP.
        for edge in ("in", "out"):
            if t["edge"] in (edge, "both"):
                start = b["start_f"] if edge == "in" else b["end_f"] - d
                state(el, {"display": "block", "visibility": "visible"}, start)
                state(el, {"display": "contents"}, start + d)
        shader = typ == "shader" and inp.get("transition_shader", False)
        if typ == "shader" and not shader:
            notes.append(FALLBACK)
        if shader:
            # The package sees only overlay-owned pixels and transparent scenes, never a-roll handles.
            layers.append(f'<div id="{name}-empty" class="band scene" style="z-index:700;pointer-events:none"></div>')
            shader_jobs.append((b, name))
        else:
            for edge in ("in", "out"):
                if t["edge"] not in (edge, "both"):
                    continue
                start = b["start_f"] if edge == "in" else b["end_f"] - d
                for f in range(start, start + d):
                    p = (f - start) / d if edge == "in" else (start + d - f - 1) / d
                    v = {"opacity": p}
                    if typ == "push":
                        dx, dy = {"l": (-1, 0), "r": (1, 0), "u": (0, -1), "d": (0, 1)}[t.get("dir", "r")]
                        v = {"x": dx * w * (1 - p), "y": dy * h * (1 - p)}
                    elif typ == "wipe":
                        clips = {"l": f"inset(0 0 0 {(1-p)*100:g}%)", "r": f"inset(0 {(1-p)*100:g}% 0 0)",
                                 "u": f"inset({(1-p)*100:g}% 0 0 0)", "d": f"inset(0 0 {(1-p)*100:g}% 0)"}
                        v = {"clipPath": clips[t.get("dir", "r")]}
                    state(el, v, f)
                state(el, {"opacity": 1, "x": 0, "y": 0, "clipPath": "none"}, start + d)
    if shader_jobs:
        # One package init: its engine metadata is one scene list, even for several shader beats.
        layers.append('<div id="g5-shader-empty" class="band scene" style="z-index:700;pointer-events:none"></div>')
        ids, configs = ["g5-shader-empty"], []
        previous_end = -1
        for b, name in sorted(shader_jobs, key=lambda item: item[0]["start_f"]):
            if b["start_f"] < previous_end:
                raise ValueError("Shader scene beats cannot overlap with this pinned renderer; use fade on one beat")
            previous_end = b["end_f"]
            t, start, end = b["transition"], b["start_f"], b["end_f"]
            for edge, frame, target in (("in", start, name), ("out", end - t["dur_frames"], name + "-empty")):
                chosen = t["edge"] in (edge, "both")
                if not chosen and edge == "out":
                    frame = end
                duration = float(Fraction(t["dur_frames"]) / rate) if chosen else 0
                config = {"time": float(time(frame)), "duration": duration, "ease": "none"}
                if chosen:
                    config["shader"] = t["shader"]
                configs.append(config)
                ids.append(target)
        lines.append("HyperShader.init(" + json.dumps({"bgColor": "#00000000", "scenes": ids, "transitions": configs, "compositionId": "main"})[:-1] + ", timeline: tl});")
        # time/duration are seconds, but package/compositor playback can retain
        # a shader past its declared end. Own the visible window on the root tl.
        # Opacity also clamps a compositor that changes display after seeking.
        canvas = "#gl-canvas, #__hf-page-side-compositor"
        for b, name in sorted(shader_jobs, key=lambda item: item[0]["start_f"]):
            t = b["transition"]
            for edge in ("in", "out"):
                if t["edge"] not in (edge, "both"):
                    continue
                start = b["start_f"] if edge == "in" else b["end_f"] - t["dur_frames"]
                state(canvas, {"opacity": 1}, start)
                state(canvas, {"opacity": 0}, start + t["dur_frames"])
                restored = {"opacity": 1 if edge == "in" else 0,
                            "visibility": "visible" if edge == "in" else "hidden"}
                if edge == "out":
                    restored["display"] = "none"
                state("#" + name, restored, start + t["dur_frames"])
    return layers, lines, vendors, list(dict.fromkeys(notes))


def selftest():
    bad = {"id": "o", "start_f": 10, "end_f": 5, "layout": "overlay",
           "transition": {"type": "fade", "at_cut_frame": None, "dur_frames": 2, "edge": "in"}}
    assert any("whole start and end frames" in m for m in beat_problems(bad)), "bad overlay frames need a plain line"
    b = {"id": "REEL_A", "start_f": 0, "end_f": 120, "layout": "full", "transition": {"type": "flash", "at_cut_frame": 60, "dur_frames": 3}}
    assert not problems([b], [60], 30, [])
    for change in ({"type": "cut"}, {"x": 1}, {"dur_frames": 0}, {"dur_frames": 11}, {"dur_frames": True},
                   {"at_cut_frame": 61}, {"at_cut_frame": None}, {"at_cut_frame": True}, {"at_cut_frame": 60.0}, {"color": "bad"}):
        assert problems([dict(b, transition=dict(b["transition"], **change))], [60], 30, [])
    assert problems([b, b], [60], 30, [])
    assert problems([b], [60], 30, ["zoom"])
    assert problems([b], [59, 60], 30, [])
    assert [(s["start_f"], s["end_f"]) for s in spans([b])] == [(57, 63)]
    overlay = dict(b, layout="overlay", start_f=5, end_f=125, transition={
        "type": "fade", "at_cut_frame": None, "dur_frames": 3, "edge": "both"})
    assert [(s["start_f"], s["end_f"]) for s in spans([overlay])] == [(5, 8), (122, 125)]
    assert problems([dict(overlay, transition=dict(overlay["transition"], edge="middle"))], [60], 30, [])
    assert problems([dict(overlay, transition=dict(overlay["transition"], dur_frames=31))], [60], 30, [])
    # Inspect emitted root-timeline states without a browser. A zero/weak seeded
    # sample or a missing boundary state must fail, including dur_frames=1.
    def states(lines, selector):
        found = []
        for line in lines:
            match = re.fullmatch(r'tl\.set\(("[^"]+"), (\{.*\}), ([\d.]+)\);', line)
            if match and json.loads(match[1]) == selector:
                found.append((float(match[3]), json.loads(match[2])))
        return found

    for bid in ("REEL_A", "REEL_B", "REEL_C"):
        for d in (1, 6, 10):
            glitch = dict(b, id=bid, transition={"type": "glitch", "at_cut_frame": 60, "dur_frames": d})
            _, lines, _, _ = layer({"beats": [glitch]}, 720, 1280, Fraction(30))
            moves = states(lines, "#g5-aroll-move")
            assert [at for at, _ in moves] == [math.floor(Fraction(f, 30) * 1_000_000) / 1_000_000
                                              for f in range(60 - d, 60 + d + 1)]
            assert all(abs(v["x"]) >= 12 for _, v in moves[:-1]), "glitch needs displacement on every window frame"
            assert moves[-1][1]["x"] == 0 and moves[-1][1]["filter"] == "none"
            assert lines == layer({"beats": [glitch]}, 720, 1280, Fraction(30))[1], "glitch must stay seeded"

    from unittest.mock import patch
    canvas = "#gl-canvas, #__hf-page-side-compositor"
    for edge, windows in (("in", [(45.0, 45.2)]), ("out", [(46.8, 47.0)]),
                          ("both", [(45.0, 45.2), (46.8, 47.0)])):
        shader = dict(overlay, start_f=1350, end_f=1410, scene={"id": "callout"}, transition={
            "type": "shader", "at_cut_frame": None, "dur_frames": 6, "edge": edge, "shader": "sdf-iris"})
        with patch(__name__ + ".shader_bundle", return_value=Path("vendor.js")):
            _, lines, _, _ = layer({"beats": [shader], "transition_shader": True}, 720, 1280, Fraction(30))
        clamps = [(at, v["opacity"]) for at, v in states(lines, canvas) if "opacity" in v]
        assert clamps == [(at, opacity) for start, end in windows
                                      for at, opacity in ((start, 1), (end, 0))], "shader canvas must stop at each exclusive end"
        init = next(i for i, line in enumerate(lines) if line.startswith("HyperShader.init("))
        config = json.loads(lines[init][len("HyperShader.init("):].removesuffix(", timeline: tl});") + "}")
        assert [c["duration"] for c in config["transitions"] if c.get("shader")] == [0.2] * len(windows)
        assert all(i > init for i, line in enumerate(lines) if line.startswith('tl.set(' + json.dumps(canvas)))
        scene_states = states(lines[init + 1:], "#g5-transition-0")
        for start, end in windows:
            assert any(at == end and v.get("opacity") == (1 if start == 45.0 else 0)
                       for at, v in scene_states), "shader end must restore the live scene"
    for name, spec in MENU.items():
        t = {"type": name, "at_cut_frame": 60, "dur_frames": 3}
        ob = dict(b, transition=t)
        if spec["kind"] == "overlay":
            t.update(at_cut_frame=None, edge="both")
            ob.update(layout="overlay", scene={"id": "callout"})
        if name == "shader":
            t["shader"] = SHADERS[0]
        assert not problems([ob], [60], 30, []), name
    # The board's inline menu is a generated copy; keep every rule equal.
    board = (HERE.parent / "boards/beat-map/index.html").read_text(encoding="utf-8")
    assert json.loads(re.search(r"const TRANSITION_MENU = (\{[^\n]+\});", board).group(1)) == MENU
    print("selftest ok")
    return 0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--menu-json", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.menu_json:
        print(json.dumps(MENU))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("Transition step stopped: " + (str(exc).splitlines() or ["check the transition choices"])[0])
        sys.exit(1)
