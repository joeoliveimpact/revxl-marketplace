"""The scene validator (G2-a, stdlib only): checks the shipped scenes and one beat's scene fill.

The scene contract. A scene is a folder scenes/<id>/ holding exactly what a beat's `scene:{id, slots, params}`
needs to render it:
  scene.json   {id, kind, slots, dur, params, source, licence}
               id       = the folder name
               kind     = "overlay" (sits over the a-roll, leaves most of the frame clear) or
                          "takeover" (may fill the frame)
               slots    = {<name>: {maxChars: int >= 1, default: sample text, hint?}}: the words a beat fills in
               dur      = [min_s, max_s], 0 < min <= max
               params   = {<name>: {type: number|string|boolean|color, default, min?, max?, maxChars?, hint?}}
               source, licence = where it came from and under what terms (never empty)
  scene.html   a 1080x1920 HyperFrames composition of our own:
               - root element data-composition-id="<id>" with data-duration inside dur, CSS z-index in the
                 scene band 400-499 (nothing in the scene outside it), and no background on html, body or the
                 root (only the scene's own cards and plates are filled; their class is "plate")
               - slots and params arrive as HyperFrames variables: <html data-composition-variables> declares
                 every slot (type string) and param with scene.json's defaults, the script reads
                 window.__hyperframes.getVariables(), and each slot's text goes into its data-slot="<name>"
                 element; `accent` and `font` are params so a saved style can override the look
               - offline: GSAP only from <script src="./vendor/gsap.min.js"> (the shipped runtime/gsap copy,
                 never inlined), no remote URL anywhere, fonts only from local @font-face rules whose file is
                 in runtime/fonts (a render copies them to ./fonts), every family used declared, weight 400 only
               - deterministic: one paused GSAP timeline, registered as window.__timelines["<id>"]; no
                 Math.random, Date.now, new Date, performance.now, setTimeout, setInterval,
                 requestAnimationFrame; no CSS @keyframes, animation or transition; centring with GSAP
                 xPercent/yPercent, never CSS translate(-50%...) or translate: -50%
  preview.png  a real 9:16 PNG thumbnail rendered from the scene (tests/editor/scene_render_test.py
               --write-previews), never hand-made

A fill is one beat's `scene` object {id, slots, params} (a whole beat holding one is accepted too). Every slot
is given (use "" to leave one empty), no slot is longer than its maxChars, no unknown slot or param, every param
has its type and range. The counter's display (prefix + value with commas and decimals + suffix) fits its
maxChars, and so does its start (prefix + from + suffix); from lies between 0 and the value, so no number shown
mid-count is longer than the final one. On a whole beat the counter's value equals the beat's value.
Never invent numbers (VES-3 f): for the counter and the stat card, params.value and every number written in
the slot text must appear in the transcript. "Appears" means some number said in the transcript is equal
in value: commas are dropped, so "1,200" and "1200" match; a k/m/b or thousand/million/billion right after a
number scales it, so "1.2k" and "1.2 thousand" read as 1200 (and also match the bare 1.2, so a counter showing
1.2 with the suffix "M" matches "1.2 million"); $ and % are ignored. Numbers spelled out in words
("forty-seven") are not read, so they never count as said. No transcript = fail, never a pass.

  scene_check.py check [<scenes dir>]
  scene_check.py fill <scene id> <fill.json> [--transcript <words.json>] [--scenes DIR]
  scene_check.py --selftest
Prints one "OK <id>" or one "FAIL <id>: <reason>" per problem; exit 0 only when everything passes, 1 when
something fails, 2 when the check itself could not run.
"""
import argparse
import json
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "skills" / "_shared"))
sys.path.insert(0, str(P / "skills" / "editor-doctor" / "scripts"))
sys.path.insert(0, str(P / "skills" / "reel-canvas-build" / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
from offline_selftest import REMOTE, INLINE_SCRIPT, GSAP_MARKS  # noqa: E402  (the S1c offline rules, reused)
from beat_schema import load_words, SchemaError  # noqa: E402  (S3/S6a transcript word lists)

SCENES = P / "scenes"
FONTS = P / "runtime" / "fonts"
GSAP_SRC = "./vendor/gsap.min.js"
FILES = ("scene.html", "scene.json", "preview.png")
KEYS = ("id", "kind", "slots", "dur", "params", "source", "licence")
KINDS = ("overlay", "takeover")
PARAM_TYPES = ("number", "string", "boolean", "color")
NUMBER_SCENES = ("counter", "stat-card")  # scenes that show a number, so VES-3 f applies
BAND = (400, 499)
W, H = 1080, 1920
BANNED = [
    (re.compile(r"@keyframes", re.I), "uses CSS @keyframes; put every move on the scene's GSAP timeline (TRI-4)"),
    (re.compile(r"\banimation(-[a-z]+)?\s*:", re.I), "uses a CSS animation; put every move on the GSAP timeline (TRI-4)"),
    (re.compile(r"\btransition(-[a-z]+)?\s*:", re.I), "uses a CSS transition; put every move on the GSAP timeline (TRI-4)"),
    (re.compile(r"translate(?:X|Y|3d)?\(\s*-50%", re.I),
     "centres with CSS translate(-50%...); centre with GSAP xPercent: -50 / yPercent: -50 instead (TRI-4)"),
    (re.compile(r"(?<![\w-])translate\s*:[^;}]*-50%", re.I),
     "centres with the CSS translate property (-50%); centre with GSAP xPercent: -50 / yPercent: -50 instead (TRI-4)"),
]
NONDETERMINISTIC = ("Math.random", "Date.now", "new Date", "performance.now", "setTimeout", "setInterval",
                    "requestAnimationFrame")
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "emoji", "math",
                 "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded"}
FONT_KEYWORDS = {"inherit", "initial", "unset", "revert"}
NUM = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?:\s*(thousand|million|billion|bn|k|m|b)(?![a-z]))?", re.I)
SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}
HEX = re.compile(r"#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})", re.I)


def show(v, n=60):
    s = repr(v)
    return s if len(s) <= n else s[:n] + "..."


# ---- numbers (VES-3 f) -----------------------------------------------------------------------------------
def numbers(text):
    """[(value, mantissa)] for every number written in text; mantissa is the number before any k/m/b."""
    out = []
    for m in NUM.finditer(text):
        base = float(m.group(1).replace(",", "") + (m.group(2) or ""))
        out.append((base * SCALE.get((m.group(3) or "").lower(), 1), base))
    return out


def said(value, heard):
    """True when value equals a number heard in the transcript (its scaled value or its bare mantissa)."""
    close = lambda a, b: abs(a - b) <= 1e-9 * max(1.0, abs(a))  # noqa: E731
    return any(close(value, v) or close(value, m) for v, m in heard)


def display(params):
    """The counter's final text, as scene.html's fmt() writes it."""
    d = max(0, min(2, round(params.get("decimals", 0))))
    return f"{params.get('prefix', '')}{params['value']:,.{d}f}{params.get('suffix', '')}"


# ---- check: one scene folder ---------------------------------------------------------------------------
def spec_problems(sid, spec):
    if not isinstance(spec, dict):
        return ["scene.json is not a JSON object"]
    out = [f"scene.json is missing {k}" for k in KEYS if k not in spec]
    out += [f"scene.json has an unknown key {show(k)}; the keys are {', '.join(KEYS)}" for k in spec if k not in KEYS]
    if out:
        return out
    if spec["id"] != sid:
        out.append(f"scene.json id {show(spec['id'])} is not the folder name {show(sid)}")
    if spec["kind"] not in KINDS:
        out.append(f"kind {show(spec['kind'])} must be overlay or takeover")
    if not isinstance(spec["slots"], dict) or not spec["slots"]:
        out.append("slots must be an object with at least one slot")
    else:
        for name, s in spec["slots"].items():
            mc = s.get("maxChars") if isinstance(s, dict) else None
            if not (isinstance(mc, int) and not isinstance(mc, bool) and mc >= 1):
                out.append(f"slot {show(name)} needs a whole-number maxChars of 1 or more")
            elif not isinstance(s.get("default"), str) or len(s["default"]) > mc:
                out.append(f"slot {show(name)} needs default sample text no longer than its maxChars ({mc})")
    d = spec["dur"]
    if not (isinstance(d, list) and len(d) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                                         for x in d) and 0 < d[0] <= d[1]):
        out.append(f"dur {show(d)} must be [min seconds, max seconds] with 0 < min <= max")
    if not isinstance(spec["params"], dict):
        out.append("params must be an object")
    else:
        for name, p in spec["params"].items():
            if name in spec["slots"]:
                out.append(f"{show(name)} is both a slot and a param; rename one")
            if not isinstance(p, dict) or p.get("type") not in PARAM_TYPES:
                out.append(f"param {show(name)} needs a type: {', '.join(PARAM_TYPES)}")
            elif "default" not in p or value_problem(name, p, p["default"]):
                out.append(f"param {show(name)} needs a default of its own type and range")
    for k in ("source", "licence"):
        if not (isinstance(spec[k], str) and spec[k].strip()):
            out.append(f"{k} must say where the scene came from and under what terms (it is empty)")
    return out


def value_problem(name, p, v):
    """A plain reason v doesn't fit param spec p, or None."""
    t = p["type"]
    if t == "number":
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return f"param {name} must be a number, not {show(v)}"
        if "min" in p and v < p["min"] or "max" in p and v > p["max"]:
            return f"param {name} {show(v)} must be between {p.get('min', '-')} and {p.get('max', '-')}"
    elif t == "boolean" and not isinstance(v, bool):
        return f"param {name} must be true or false, not {show(v)}"
    elif t == "string":
        if not isinstance(v, str):
            return f"param {name} must be text, not {show(v)}"
        if "maxChars" in p and len(v) > p["maxChars"]:
            return f"param {name} is {len(v)} characters; it fits {p['maxChars']} at most"
    elif t == "color" and not (isinstance(v, str) and HEX.fullmatch(v)):
        return f"param {name} must be a hex colour like #4f8cff, not {show(v)}"
    return None


def font_faces(html):
    """{family: [src urls]} from the @font-face rules."""
    faces = {}
    for block in re.findall(r"@font-face\s*\{([^}]*)\}", html, re.I):
        fam = re.search(r"font-family\s*:\s*([^;]+)", block, re.I)
        src = re.search(r"\bsrc\s*:\s*([^;]+)", block, re.I)
        name = fam.group(1).strip().strip("\"'") if fam else ""
        faces.setdefault(name, []).extend(re.findall(r"(?:url|local)\(\s*[\"']?([^\"')]+)", src.group(1)) if src else [])
        if src and re.search(r"\blocal\(", src.group(1), re.I):
            faces[name].append("local()")
    return faces


def html_problems(sid, spec, html):
    out = []
    root = re.search(r"<[a-z]+\b[^>]*\bdata-composition-id\s*=\s*[\"']%s[\"'][^>]*>" % re.escape(sid), html, re.I)
    if not root:
        return [f"scene.html has no root element with data-composition-id=\"{sid}\""]
    tag = root.group(0)
    attr = lambda n: (re.search(r'\b%s\s*=\s*"([^"]*)"' % n, tag) or [None, None])[1]  # noqa: E731
    if (attr("data-width"), attr("data-height")) != (str(W), str(H)):
        out.append(f"the root must be data-width=\"{W}\" data-height=\"{H}\"")
    try:
        dur = float(attr("data-duration"))
        if isinstance(spec.get("dur"), list) and len(spec["dur"]) == 2 and not spec["dur"][0] <= dur <= spec["dur"][1]:
            out.append(f"the root's data-duration {dur} is outside dur {spec['dur']}")
    except (TypeError, ValueError):
        out.append("the root needs a data-duration in seconds")
    if not re.search(r"\bid\s*=\s*[\"']%s[\"']" % re.escape(sid), tag):
        out.append(f"the root element needs id=\"{sid}\" (the scene's CSS and script are scoped to it)")

    # slots and params arrive as HyperFrames variables
    used = set(re.findall(r"\bdata-slot\s*=\s*[\"']([^\"']+)[\"']", html))
    slots, params = set(spec["slots"]), set(spec["params"])
    out += [f"slot {show(s)} is in scene.json but no element in scene.html has data-slot=\"{s}\"" for s in sorted(slots - used)]
    out += [f"scene.html fills data-slot=\"{s}\" but scene.json has no slot {show(s)}" for s in sorted(used - slots)]
    m = re.search(r"<html\b[^>]*\bdata-composition-variables\s*=\s*'([^']*)'", html, re.I)
    try:
        decl = {d["id"]: d for d in json.loads(m.group(1))} if m else None
    except (ValueError, KeyError, TypeError):
        decl = None
    if decl is None:
        out.append("<html> needs data-composition-variables='[...]' declaring every slot and param")
    else:
        for name in sorted(set(decl) - slots - params):
            out.append(f"scene.html declares the variable {show(name)} that scene.json doesn't have")
        for name in sorted((slots | params) - set(decl)):
            out.append(f"{show(name)} is in scene.json but not declared in data-composition-variables")
        for name in sorted((slots | params) & set(decl)):
            want = spec["slots"][name] if name in slots else spec["params"][name]
            wtype = "string" if name in slots else want.get("type")
            if decl[name].get("type") != wtype or decl[name].get("default") != want.get("default"):
                out.append(f"variable {show(name)} is declared as {decl[name].get('type')} {show(decl[name].get('default'))}"
                           f" but scene.json says {wtype} {show(want.get('default'))}")
    if "__hyperframes.getVariables()" not in html:
        out.append("the script never reads window.__hyperframes.getVariables(), so fills can't reach the scene")

    # offline: no remote URL, GSAP local and never inlined
    for rx in (REMOTE, re.compile(r"\bhttps?://|\b(?:src|href)\s*=\s*[\"']?\s*//", re.I)):
        for mm in rx.finditer(html):
            out.append(f"scene.html reaches the internet ({show(mm.group(0), 50)}); a scene must work offline")
    srcs = re.findall(r"<script\b[^>]*\bsrc\s*=\s*[\"']([^\"']*)[\"']", html, re.I)
    if srcs != [GSAP_SRC]:
        out.append(f"scene.html must load exactly one script file, GSAP from {GSAP_SRC} (it loads {show(srcs)})")
    if any(k in s.lower() for s in INLINE_SCRIPT.findall(html) for k in GSAP_MARKS):
        out.append(f"GSAP is pasted into the page; load the shipped copy from {GSAP_SRC} instead")

    # fonts: every family declared by a local @font-face with a shipped file, weight 400 only
    faces = font_faces(html)
    for fam, urls in faces.items():
        for u in urls:
            if u == "local()" or not u.startswith("./fonts/") or not (FONTS / u[len("./fonts/"):]).is_file():
                out.append(f"@font-face {show(fam)} points at {show(u)}; it must be ./fonts/<a file shipped in "
                           f"runtime/fonts>")
        if not urls:
            out.append(f"@font-face {show(fam)} has no src file")
    body = re.sub(r"@font-face\s*\{[^}]*\}", "", html, flags=re.I)
    fams = set()
    for val in re.findall(r"font-family\s*:\s*([^;}\n]+)", body, re.I):
        fams.update(f.strip().strip("\"'") for f in val.split(","))
    fams.update(re.findall(r"fontFamily\s*[:=]\s*[\"']([^\"']+)[\"']", body))
    if isinstance(spec["params"].get("font"), dict):
        fams.add(spec["params"]["font"].get("default"))
    for f in sorted(x for x in fams if x and x.lower() not in FONT_KEYWORDS):
        if f.lower() in GENERIC_FONTS:
            out.append(f"font family {show(f)} is a system font; use a shipped font through @font-face (HF-8)")
        elif f not in faces:
            out.append(f"font family {show(f)} has no @font-face in scene.html, so the render would use some "
                       f"other font; add one pointing at a font in runtime/fonts (HF-8)")
    for w in re.findall(r"font-weight\s*:\s*([^;}\"']+)", html, re.I) + re.findall(r"fontWeight\s*[:=]\s*[\"']?(\w+)", html):
        if w.strip().lower() not in ("400", "normal"):
            out.append(f"font-weight {w.strip()} has no shipped face, so the browser would fake it; use 400")
    if re.search(r"\bfont\s*:[^;}]*\b(bold|bolder|[5-9]00)\b", html, re.I) or re.search(r"<(b|strong|h[1-6]|th)\b", html, re.I):
        out.append("bold text (a bold font value, or a <b>, <strong>, <h1>-<h6> or <th> tag) has no shipped face; "
                   "use spans at weight 400")

    # TRI-4 and F-13
    for rx, why in BANNED:
        if rx.search(html):
            out.append(why)
    for word in NONDETERMINISTIC:
        if word in html:
            out.append(f"uses {word}, so two renders could differ; scenes must be deterministic (F-13)")
    tls = re.findall(r"gsap\.timeline\(([^)]*)\)", html)
    if len(tls) != 1 or not re.search(r"paused\s*:\s*true", tls[0]):
        out.append(f"needs exactly one gsap.timeline({{ paused: true }}) (found {len(tls)})")
    if not re.search(r"window\.__timelines\[\s*[\"']%s[\"']\s*\]\s*=" % re.escape(sid), html):
        out.append(f"the timeline must be registered as window.__timelines[\"{sid}\"] (the HyperFrames clock)")

    # H-R5 layer band
    zs = [int(z) for z in re.findall(r"z-index\s*:\s*(-?\d+)", html, re.I) + re.findall(r"zIndex\s*[:=]\s*[\"']?(-?\d+)", html)]
    if not zs:
        out.append(f"the root needs z-index: {BAND[0]} (the scene layer band {BAND[0]}-{BAND[1]})")
    out += [f"z-index {z} is outside the scene layer band {BAND[0]}-{BAND[1]}" for z in zs if not BAND[0] <= z <= BAND[1]]

    # transparent root
    rootish = {"html", "body", ":root", "*", f"#{sid}"}
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", " ".join(re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.S | re.I)))
    for sel, decls in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        subjects = {s.split()[-1] for s in sel.split(",") if s.split()}
        if subjects & rootish or any(s.startswith("[data-composition-id") for s in subjects):
            for prop, val in re.findall(r"\b(background(?:-color|-image)?)\s*:\s*([^;]+)", decls, re.I):
                if val.strip().lower() not in ("transparent", "none"):
                    out.append(f"{sel.strip()} has {prop}: {val.strip()}; html, body and the root stay transparent "
                               "(only cards and plates are filled)")
    for t in re.findall(r"<(?:html|body)\b[^>]*>", html, re.I) + [tag]:
        if re.search(r"\bstyle\s*=\s*[\"'][^\"']*background", t, re.I):
            out.append("html, body or the root has an inline background; they must stay transparent")
    if re.search(r"(document\.body|document\.documentElement|\broot)\.style\.background", html):
        out.append("the script paints a background on the page or the root; they must stay transparent")
    return out


def png_problem(path):
    b = path.read_bytes()[:24]
    if len(b) < 24 or b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        return "preview.png is not a PNG image; regenerate it with scene_render_test.py --write-previews"
    w, h = struct.unpack(">II", b[16:24])
    if not (w and h and w * 16 == h * 9):
        return f"preview.png is {w}x{h}; it must be a 9:16 thumbnail like 270x480"
    return None


def scene_problems(d):
    sid = d.name
    missing = [f for f in FILES if not (d / f).is_file()]
    if missing:
        return [f"the folder is missing {', '.join(missing)}"]
    try:
        spec = json.loads((d / "scene.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"scene.json can't be read as JSON ({e})"]
    out = spec_problems(sid, spec)
    if out:
        return out
    out += html_problems(sid, spec, (d / "scene.html").read_text(encoding="utf-8"))
    p = png_problem(d / "preview.png")
    return out + ([p] if p else [])


def cmd_check(scenes):
    scenes = Path(scenes)
    dirs = sorted(p for p in scenes.iterdir() if p.is_dir()) if scenes.is_dir() else []
    if not dirs:
        print(f"FAIL {scenes.name}: no scene folders in {scenes}")
        return 1
    bad = 0
    for d in dirs:
        probs = scene_problems(d)
        bad += bool(probs)
        for p in probs:
            print(f"FAIL {d.name}: {p}")
        if not probs:
            print(f"OK {d.name}")
    return 1 if bad else 0


# ---- fill: one beat's scene --------------------------------------------------------------------------------
def fill_problems(sid, fill, scenes=SCENES, words=None):
    """Plain problems with one beat's scene fill. words = the transcript's word strings, or None if not given."""
    d = Path(scenes) / sid
    try:
        spec = json.loads((d / "scene.json").read_text(encoding="utf-8"))
        html = (d / "scene.html").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return [f"there is no scene {show(sid)} in {scenes}"]
    beat_value = None
    if isinstance(fill, dict) and isinstance(fill.get("scene"), dict):  # a whole beat
        beat_value, fill = fill.get("value"), fill["scene"]
    if not isinstance(fill, dict):
        return ["the fill must be a JSON object {id, slots, params}"]
    out = [f"the fill has an unknown key {show(k)}; use id, slots and params" for k in fill if k not in ("id", "slots", "params")]
    if fill.get("id") != sid:
        out.append(f"the fill is for scene {show(fill.get('id'))}, not {show(sid)}")
    slots, params = fill.get("slots", {}), fill.get("params", {})
    if not isinstance(slots, dict) or not isinstance(params, dict):
        return out + ["slots and params must be objects"]
    for name, text in slots.items():
        s = spec["slots"].get(name)
        if s is None:
            out.append(f"{sid} has no slot {show(name)}; its slots are {', '.join(spec['slots'])}")
        elif not isinstance(text, str):
            out.append(f"slot {name} must be text, not {show(text)}")
        elif len(text) > s["maxChars"]:
            out.append(f"slot {name} is {len(text)} characters ({show(text, 40)}); it fits {s['maxChars']} at most, "
                       f"so shorten it (F-11)")
    out += [f"slot {n} is missing; fill it (or give \"\" to leave it empty)" for n in spec["slots"] if n not in slots]
    for name, v in params.items():
        p = spec["params"].get(name)
        if p is None:
            out.append(f"{sid} has no param {show(name)}; its params are {', '.join(spec['params'])}")
        else:
            why = value_problem(name, p, v)
            if why:
                out.append(why)
    if out:
        return out
    merged = {k: p["default"] for k, p in spec["params"].items()}
    merged.update(params)
    if "font" in params and params["font"] not in font_faces(html):
        out.append(f"font {show(params['font'])} has no @font-face in this scene, so the render would use another "
                   f"font; it has {', '.join(font_faces(html))}")
    if sid == "counter":
        for k in ("value", "from"):  # the count runs from -> value, so both ends must fit the display
            shown = display(dict(merged, value=merged[k]))
            if len(shown) > spec["params"]["value"]["maxChars"]:
                out.append(f"the counter would show {show(shown)} ({k}), {len(shown)} characters; it fits "
                           f"{spec['params']['value']['maxChars']} (prefix + number + suffix), so shorten it (F-11)")
        lo, hi = sorted((0, merged["value"]))
        if not lo <= merged["from"] <= hi:
            out.append(f"the counter counts from {merged['from']} to {merged['value']}; from must lie between 0 and "
                       f"the value, so every number shown mid-count fits the display (F-11)")
        if isinstance(beat_value, (int, float)) and not isinstance(beat_value, bool) and merged["value"] != beat_value:
            out.append(f"the counter ends on {merged['value']} but the beat's value is {beat_value}; they must match")
    if sid in NUMBER_SCENES:
        claims = ([merged["value"]] if "value" in merged else []) + [v for t in slots.values() for v, _ in numbers(t)]
        if words is None:
            out.append(f"the {sid} shows a number, so it needs the transcript (--transcript <words.json>) to prove the "
                       "number was said; it was not given")
        else:
            heard = numbers(" ".join(words))
            out += [f"{n:g} is not said in the transcript; a {sid} may only show numbers the speaker says (VES-3 f)"
                    for n in claims if not said(n, heard)]
    return out


def cmd_fill(sid, fill_path, transcript, scenes):
    try:
        fill = json.loads(Path(fill_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"FAIL {sid}: the fill {fill_path} can't be read as JSON ({e})")
        return 1
    words = None
    if transcript:
        try:
            words = load_words(transcript)
        except SchemaError as e:
            print(f"FAIL {sid}: {e}")
            return 1
    probs = fill_problems(sid, fill, scenes, words)
    for p in probs:
        print(f"FAIL {sid}: {p}")
    if not probs:
        print(f"OK {sid}")
    return 1 if probs else 0


# ---- selftest ------------------------------------------------------------------------------------------------
def selftest():
    fails = []

    def expect(name, ok):
        if not ok:
            fails.append(name)

    expect("numbers: 1,200 / 1200 / 1.2k / 1.2 thousand all read 1200",
           all(said(1200, numbers(t)) for t in ("1,200 people", "1200", "about 1.2k", "1.2 thousand")))
    expect("numbers: 1.2 million matches 1.2 and 1200000", said(1.2, numbers("1.2 million")) and said(1.2e6, numbers("1.2 million")))
    expect("numbers: 3x, 47%, $29 read 3, 47, 29", [v for v, _ in numbers("3x 47% $29")] == [3, 47, 29])
    expect("numbers: 46 is not 47, 3 kids is not 3000", not said(47, numbers("46")) and not said(3000, numbers("3 kids")))
    expect("counter display", display({"value": 1234.5, "decimals": 1, "prefix": "$", "suffix": "k"}) == "$1,234.5k")
    with tempfile.TemporaryDirectory() as t:
        good = Path(t) / "scenes"
        shutil.copytree(SCENES, good)
        expect("every shipped scene passes", all(not scene_problems(d) for d in good.iterdir() if d.is_dir()))
        h = good / "counter" / "scene.html"
        h.write_text(h.read_text(encoding="utf-8").replace('src="./vendor/gsap.min.js"',
                     'src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"'), encoding="utf-8")
        expect("a CDN GSAP fails", any("internet" in p for p in scene_problems(good / "counter")))
        fill = {"id": "counter", "slots": {"label": "sign-ups"}, "params": {"value": 47}}
        expect("counter 47 said passes", fill_problems("counter", fill, SCENES, ["we", "got", "47", "sign-ups"]) == [])
        expect("counter 47 unsaid fails", any("VES-3" in p for p in fill_problems("counter", fill, SCENES, ["46"])))
        expect("counter without transcript fails", any("transcript" in p for p in fill_problems("counter", fill, SCENES)))
        long = {"id": "callout", "slots": {"text": "x" * 33}, "params": {}}
        expect("over maxChars fails", any("F-11" in p for p in fill_problems("callout", long, SCENES)))
    for f in fails:
        print(f"selftest FAILED: {f}")
    if not fails:
        print("selftest ok")
    return 1 if fails else 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Check the editor's scenes, or one beat's scene fill.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="check every scene folder")
    c.add_argument("scenes", nargs="?", default=str(SCENES))
    f = sub.add_parser("fill", help="check one beat's scene {id, slots, params}")
    f.add_argument("id")
    f.add_argument("fill")
    f.add_argument("--transcript", help="the transcript words JSON ({words:[{word,...}]}, as S3 writes it)")
    f.add_argument("--scenes", default=str(SCENES))
    a = ap.parse_args(argv)
    try:
        if a.selftest:
            return selftest()
        if a.cmd == "check":
            return cmd_check(a.scenes)
        if a.cmd == "fill":
            return cmd_fill(a.id, a.fill, a.transcript, a.scenes)
    except Exception as e:  # the check itself broke: say so plainly, never pass
        print(f"The scene check could not run ({type(e).__name__}: {e}). Nothing was checked; show this line to Claude.")
        return 2
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
