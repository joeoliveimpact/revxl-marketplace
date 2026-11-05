"""The compositor (S6b): turn the client's Beat Map Send into the 720p preview, the OK, and the Master.

Run from the client's workspace folder with the editor's own Python:
  compose.py preview --reel-dir videos/<reel> [--hook-text "<text>"]   720x1280, renders/<Reel> Preview 720p - MM.DD.YY.mp4
  compose.py ok      --reel-dir videos/<reel> [--from-review]          records the client's OK of the latest preview
  compose.py master  --reel-dir videos/<reel> [--hook-text "<text>"]   1080x1920, renders/<Reel> Master - MM.DD.YY.mp4
  compose.py --selftest                                                 the rules below, no tools
Exit 0 done, 1 stopped by a check (the plain lines say why and what to do), 2 bad or missing input. The last line
of a successful render is one JSON summary {tier, out, frames, fps, audio, scenes, seconds}.

What a render does: the cut master (work/renders/master-<tag>.mp4) untouched as the a-roll; every beat's G2 scene
rendered on its own as an alpha MOV and placed over its frames (a scene on the first beat that has the `entrance`
param gets entrance "none", so it is complete at frame 0); a still hook title at frame 0 when the first beat
has no scene; the VES-1 effect gate before anything renders; `hyperframes lint` before every render; then ONE audio
stream muxed by stream copy: the sound pass's mix when it passed on this exact cut, else the cut's own sound.
compose.py ok is the only writer of work/render-ok.json; master refuses without an OK of the latest preview.
"""
import argparse
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
P = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "checks"))
sys.path.insert(0, str(P / "scripts"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import beat_schema  # noqa: E402
import effect_gate  # noqa: E402
import fps as fpsmod  # noqa: E402
import scene_check  # noqa: E402  (P/scripts: the G2-a scene contract)
import licence_rows  # noqa: E402  (G4's licence check, as mix.py imports it)

_spec = importlib.util.spec_from_file_location("ig_safe_zones", HERE / "ig-safe-zones.py")
_ig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ig)
RESERVE = _ig.RESERVE  # Instagram's covered margins, as fractions of the frame

TIERS = {"preview": (720, 1280), "master": (1080, 1920)}
QUALITY = {"preview": ["--quality", "draft"], "master": ["--quality", "delivery", "--video-frame-format", "png"]}
MASTER_RE = re.compile(r"^.+ master - \d{2}\.\d{2}\.\d{2}\.mp4$", re.I)  # the Cockpit's rule (hooks/mod/logic.ts MASTER)
UNDERLAY = "#0e0f12"  # taste, not a rule: the neutral dark panel under back-to-back takeovers
FADE_F = 3            # underlay fade in and fade out, frames each (6 in total at most)
HOOK_MAX_CHARS = 70
HOOK_MAX_S = 5        # the hook title shows for the first beat, 5 s at most
Z_AROLL, Z_SCENE, Z_HOOK, Z_PIP = 100, 401, 450, 500  # H-R5 bands; the underlay sits on the scene floor (400)
SEND = "beat-map-selection.json"
OK_FILE = "work/render-ok.json"
NEED_OK = "The 720p preview needs your OK first: watch it, then tell me it's OK (or approve it in the Master review)."
NO_MIX = "the sound pass hasn't run; the final will pick up its sound once it has"
STALE_MIX = "the sound was mixed on an older cut; run the sound pass again"
FAILED_MIX = "the last sound mix didn't pass its check; run the sound pass again"
TEMPLATE = SKILL / "templates" / "render" / "index.html"


class Stop(Exception):
    """A plain stop: exit code + the lines that say why and what to do."""

    def __init__(self, code, *lines):
        super().__init__(lines[0] if lines else "")
        self.code, self.lines = code, lines


# ---- pure rules (selftest covers these) ------------------------------------------------------------------
def ts(f, rate):
    """Frame f as seconds text that round(t * fps) turns back into f (from the exact Fraction, never summed floats)."""
    s = f"{float(round(Fraction(f) / rate, 6)):.6f}".rstrip("0").rstrip(".") or "0"
    if round(float(s) * rate) != f:
        raise ValueError(f"time for frame {f} at {rate} fps doesn't round back")
    return s


def out_names(reel, day):
    """(preview name, Master name) for the reel and date; the preview never passes the Master rule, the Master does."""
    prev, mast = f"{reel} Preview 720p - {day}.mp4", f"{reel} Master - {day}.mp4"
    if MASTER_RE.match(prev) or not MASTER_RE.match(mast):
        raise ValueError(f"output names break the Master rule: {prev!r} / {mast!r}")
    return prev, mast


def latest_preview(renders):
    """The newest finished preview in renders/ (never a .partial), or None."""
    found = [p for p in Path(renders).glob("* Preview 720p - *.mp4")
             if p.is_file() and not p.name.endswith(".partial.mp4")]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def ok_problem(ok, name, mtime):
    """None when render-ok.json okays this preview (by name) and the preview hasn't changed since; else the line."""
    if name is None:
        return "There's no 720p preview yet; make the preview first, then OK it."
    if not isinstance(ok, dict) or ok.get("preview") != name:
        return NEED_OK
    try:
        at = datetime.fromisoformat(str(ok.get("ok_at"))).timestamp()
    except ValueError:
        return NEED_OK
    if mtime > at:
        return NEED_OK + " The preview changed after the last OK."
    return None


def review_problem(review, name):
    """None when the Master review Send approves exactly the latest preview; else the plain line."""
    if not isinstance(review, dict) or review.get("approve") is not True:
        return "The Master review doesn't approve the preview, so nothing was recorded; fix what it asks, then preview again."
    if review.get("preview") != name:
        return (f"The Master review approved {review.get('preview')!r}, but the latest preview is {name!r}; "
                f"review the latest one first.")
    return None


def audio_choice(report, cut_md5, has_final):
    """("mix" | "cut", plain line or None): the sound pass's mix only when it passed on this exact cut."""
    if not isinstance(report, dict) or not has_final:
        return "cut", NO_MIX
    if report.get("pass") is not True:
        return "cut", FAILED_MIX
    if not cut_md5 or report.get("video_md5") != cut_md5:
        return "cut", STALE_MIX
    return "mix", None


def hook_box(w, h):
    """(centre x, top y, width, font size) of the hook title, inside the Instagram safe zone, in tier pixels."""
    s = w / 1080
    x0, x1 = RESERVE["left"] * w, (1 - RESERVE["right"]) * w
    return (x0 + x1) / 2, RESERVE["top"] * h + 60 * s, (x1 - x0) - 60 * s, 72 * s


def build_spans(beats, kinds, hook_f, extra_spans=None):
    """Gate spans: the scenes (spans_from_beats, no layout moves before S6c) + the compose hook as an overlay
    + extra_spans (internal: S6c passes its camera moves here, so they face the same VES-1 check)."""
    spans = effect_gate.spans_from_beats(beats, 0, scene_kind=kinds)
    if hook_f:
        spans.append({"layer": "overlay", "start_f": 0, "end_f": hook_f, "id": "hook title"})
    return spans + list(extra_spans or [])


# ---- tools ---------------------------------------------------------------------------------------------------
def run(cmd, env, timeout=None):
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def tail(s, n=300):
    return " ".join(s.split())[-n:]


def kill_warm():
    """Stop HyperFrames' leftover warmCheck.js helper from this install (on Windows it keeps the project open)."""
    try:
        node = str(Path(rt.tool("node")).resolve())
    except (KeyError, OSError):
        return
    if os.name == "nt":
        ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        run([ps, "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq "
             f"'{node}' -and $_.CommandLine -like '*warmCheck.js*' }} | ForEach-Object {{ Stop-Process -Id "
             "$_.ProcessId -Force }"], None, 60)
    else:
        run(["pkill", "-f", "warmCheck.js"], None, 30)


def remove_tree(d):
    for _ in range(5):
        shutil.rmtree(d, ignore_errors=True)
        if not d.exists():
            return True
        kill_warm()
        time.sleep(2)
    return False


def ffmpeg(*args):
    return run([rt.tool("ffmpeg"), "-v", "error", *args], rt.python_env())


def packet_md5(path, sel):
    """MD5 of a stream's packets ("v" or "a"): a stream copy keeps it, a re-encode changes it."""
    rc, out, _ = ffmpeg("-i", path, "-map", f"0:{sel}", "-c", "copy", "-f", "md5", "-")
    return out.strip() if rc == 0 else ""


def streams(path):
    rc, out, _ = run([rt.tool("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json",
                      path], rt.python_env())
    try:
        return json.loads(out).get("streams") or []
    except ValueError:
        return []


def link_or_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def write_json(path, obj):
    data = (json.dumps(obj, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    assert b"\r" not in data
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def read_json(path, missing):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Stop(2, missing) from None
    except (OSError, ValueError) as e:
        raise Stop(2, f"✗ {path.name} can't be read ({e}); save it again from its board.") from None


# ---- inputs --------------------------------------------------------------------------------------------------
def load_inputs(reel):
    if not reel.is_dir():
        raise Stop(2, f"✗ There's no reel folder at {reel}; point --reel-dir at videos/<reel>.")
    bm = read_json(reel / SEND, "✗ Send the Beat Map first: press Send on the Beat Map board, then run this again.")
    try:
        words = beat_schema.load_words(reel / beat_schema.DEFAULT_WORDS)
        beat_schema.validate_beat_map(bm, words)
        if (reel / "sketches-selection.json").exists():
            beat_schema.validate_sketches(read_json(reel / "sketches-selection.json", ""), bm)
    except beat_schema.SchemaError as e:
        raise Stop(2, *[f"✗ {p}" for p in e.problems], "Fix it on the board and Send again.") from None
    cuts = read_json(reel / "work" / "cuts.json", "✗ There's no cut list (work/cuts.json) yet; make the cut first.")
    segs = cuts.get("segments") if isinstance(cuts, dict) else None
    num = (int, float)
    if not (isinstance(cuts, dict) and isinstance(cuts.get("fps"), num) and isinstance(cuts.get("speed"), num)
            and isinstance(segs, list) and segs and all(isinstance(s, dict) and isinstance(s.get("out_in_f"), int)
                                                       and isinstance(s.get("out_out_f"), int) for s in segs)):
        raise Stop(2, "✗ The cut list work/cuts.json is incomplete; make the cut again.")
    tag = ("%.2fx" % cuts["speed"]).replace(".", "")
    master = reel / "work" / "renders" / f"master-{tag}.mp4"
    if not master.is_file():
        raise Stop(2, f"✗ The cut master work/renders/{master.name} is missing; make the cut first.")
    return {"bm": bm, "beats": bm["beats"], "words": words, "cuts": cuts, "master": master}


def probe_inputs(inp):
    """The real frame rate and length of the cut master, held against the cut list and the Beat Map."""
    try:
        fps_s = fpsmod.resolve_fps(inp["master"])
        rate = fpsmod.as_fraction(fps_s)
    except ValueError as e:
        raise Stop(2, f"✗ {e}") from None
    for what, v in (("cut list", inp["cuts"]["fps"]), ("Beat Map", inp["bm"]["fps"])):
        if abs(float(rate) - v) > 1e-3:
            raise Stop(1, f"✗ The cut master runs at {float(rate):.3f} fps but the {what} says {v} fps: the cut "
                          f"changed since the Beat Map; rebuild the Beat Map (make the cut again first if the cut "
                          f"list is the odd one out).")
    total = inp["cuts"]["segments"][-1]["out_out_f"]
    try:
        got = fpsmod.frame_count(inp["master"])
    except ValueError as e:
        raise Stop(2, f"✗ {e}") from None
    if got != total:
        raise Stop(1, f"✗ The cut master has {got} frames but the cut list says {total}; make the cut again.")
    inp.update(fps=fps_s, rate=rate, total=total, cut_frames=[s["out_in_f"] for s in inp["cuts"]["segments"][1:]])


def plan(inp, hook_text, extra_spans=None):
    """Notes, scene checks, the hook, and the effect gate; raises Stop before anything renders."""
    beats, rate = inp["beats"], inp["rate"]
    for b in beats:
        if b["layout"] != "full":
            print(f"note: beat {b['id']} asks for {b['layout']}; layouts come with the editing styles step, "
                  f"so it shows full screen for now")
        if b["broll"] is not None:
            print(f"note: beat {b['id']} has B-roll; B-roll is not built yet, skipped")
        if b["transition"] is not None:
            print(f"note: beat {b['id']} has a transition; transitions are not built yet, skipped")
    scened = [b for b in beats if b["scene"] is not None]
    opens = set()  # H-S6b-19: a scene that opens the reel is complete at frame 0 when it can be
    for b in scened:
        params = b["scene"].get("params", {})  # no params key = {} (as fill_problems reads it)
        if b["start_f"] == 0 and isinstance(params, dict) and "entrance" in scene_params(b["scene"]):
            b["scene"] = dict(b["scene"], params=dict(params, entrance="none"))
            opens.add(b["id"])
    bad = [f"✗ beat {b['id']}: {p}" for b in scened
           for p in scene_check.fill_problems(b["scene"].get("id"), b, words=inp["words"])]
    if bad:
        raise Stop(1, *bad, "Fix the scene on the Beat Map board and Send again; nothing was rendered.")
    specs = {b["scene"]["id"]: json.loads((scene_check.SCENES / b["scene"]["id"] / "scene.json")
                                          .read_text(encoding="utf-8")) for b in scened}
    problems = []
    for b in scened:
        lo, hi = specs[b["scene"]["id"]]["dur"]
        secs = Fraction(b["end_f"] - b["start_f"]) / rate
        if not lo <= secs <= hi:
            problems.append(f"✗ beat {b['id']} runs {float(secs):.2f} s, but the {b['scene']['id']} scene fits "
                            f"{lo}-{hi} s; move the beat's edges or pick another scene")
    first = next((b for b in beats if b["start_f"] == 0), None)
    hook_f, text = 0, None
    if any(b["start_f"] == 0 and b["scene"] is not None for b in beats):
        if any(b["start_f"] == 0 and b["id"] not in opens for b in scened):
            print("note: the first beat has a scene, so frame 0 shows that scene rather than a hook title; check that "
                  "frame 0 reads as a complete hook")
    elif first is not None or hook_text:
        text = " ".join((hook_text if hook_text is not None else first["speech_anchor"]["text"]).split())
        if not text:
            raise Stop(1, "✗ The first beat has no words for the hook title; tell me the hook text.")
        if len(text) > HOOK_MAX_CHARS:
            raise Stop(1, f"✗ The hook line is long ({len(text)} characters, {HOOK_MAX_CHARS} at most); "
                          f"shorten it or tell me the hook text.")
        five = round(HOOK_MAX_S * rate)
        hook_f = min(first["end_f"], five) if first is not None else min(inp["total"], five)
    else:
        print("note: no beat starts at frame 0, so there's no hook title; tell me the hook text to add one")
    kinds = {sid: spec["kind"] for sid, spec in specs.items()}
    try:
        spans = build_spans(beats, kinds, hook_f, extra_spans)
    except ValueError as e:
        raise Stop(1, f"✗ {e}") from None
    problems += [f"BLOCK {p}" for p in effect_gate.check(spans, inp["cut_frames"], inp["fps"], inp["total"])]
    if problems:
        raise Stop(1, *problems, "Nothing was rendered; fix these on the Beat Map board and Send again.")
    inp.update(scened=scened, hook_f=hook_f, hook_text=text, under=effect_gate.underlay(spans, inp["fps"]))


def scene_params(scene):
    """The params a scene's scene.json declares ({} when it can't be read; fill_problems then says why)."""
    try:
        spec = json.loads((scene_check.SCENES / str(scene.get("id")) / "scene.json").read_text(encoding="utf-8"))
        return spec.get("params") or {}
    except (OSError, ValueError, AttributeError):
        return {}


def choose_audio(reel, inp, tier):
    report = None
    try:
        report = json.loads((reel / "sound" / "mix-report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    final = reel / "sound" / "final.mp4"
    kind, line = audio_choice(report, packet_md5(inp["master"], "v") if report else "", final.is_file())
    if line:
        print(f"note: the {tier} uses the cut's own sound: {line}")
    if kind == "mix":
        rows = licence_rows.run({"reel_dir": reel, "fps": float(inp["rate"]), "cuts": inp["cuts"],
                                 "beats": inp["beats"], "render": None})
        blocks = [r["msg"] for r in rows if r["level"] == "block"]
        if blocks and tier == "master":
            raise Stop(1, *[f"✗ {m}" for m in blocks], "The Master wasn't made: fix the music's licence row, "
                                                         "or pick other music on the Sound board.")
        for m in blocks:
            print(f"warning: {m} (the Master will refuse until it's fixed)")
    return kind, (final if kind == "mix" else inp["master"])


# ---- render --------------------------------------------------------------------------------------------------
def lint_or_stop(proj, what="the composition", env=None):
    """TRI-3, the gate before every render: `hyperframes lint --json` -> (ok, plain lines). Any error (or a lint
    that can't run) makes ok False and the render must not start; warnings are lines and the render goes on."""
    rc, out, err = run(rt.hyperframes_cmd("lint", proj, "--json"), env or rt.hyperframes_env(), 600)
    kill_warm()
    try:
        j = json.loads(out[out.index("{"):])
        errors = j["errorCount"]
        found = j.get("findings") or []
    except (ValueError, KeyError):
        return False, [f"✗ The layout check couldn't run on {what} (exit {rc}: {tail(out + err)}); run it again, "
                       f"and if it fails twice offer the failure report."]
    lines = [f"✗ {what}: {f.get('message', '')} [{f.get('code', '?')}]" for f in found if f.get("severity") == "error"]
    if errors and not lines:
        lines = [f"✗ {what}: {errors} layout errors"]
    lines += [f"warning: {what}: {f.get('message', '')} [{f.get('code', '?')}]" for f in found
              if f.get("severity") != "error"]
    return not errors, lines


def hf_render(proj, out, env, what, extra):
    ok, lines = lint_or_stop(proj, what, env)
    print(f"info: lint {what}: {sum(l.startswith('✗') for l in lines)} errors, "
          f"{sum(l.startswith('warning:') for l in lines)} warnings")
    if not ok:
        raise Stop(1, *lines, "Nothing was rendered.")
    for line in lines:
        print(line)
    t0 = time.perf_counter()
    rc, o, e = run(rt.hyperframes_cmd("render", proj, *extra, "-o", out), env)
    kill_warm()
    if rc != 0 or not out.is_file():
        raise Stop(1, f"✗ The {what} render stopped (exit {rc}: {tail(o + e)}); run it again, and if it fails "
                      f"twice offer the failure report.")
    print(f"info: {what} rendered in {time.perf_counter() - t0:.1f} s")


def scene_project(dst, beat, rate):
    sid = beat["scene"]["id"]
    src = (scene_check.SCENES / sid / "scene.html").read_text(encoding="utf-8")
    root = re.search(r'<[^>]*\bdata-composition-id="%s"[^>]*>' % re.escape(sid), src)
    if not root or 'data-duration="' not in root.group(0):
        raise Stop(1, f"✗ The {sid} scene has no root duration to set; the scene file is damaged, reinstall the editor.")
    tag = re.sub(r'data-duration="[^"]*"', f'data-duration="{ts(beat["end_f"] - beat["start_f"], rate)}"',
                 root.group(0), count=1)
    (dst / "vendor").mkdir(parents=True)
    shutil.copy2(P / "runtime" / "gsap" / "gsap.min.js", dst / "vendor" / "gsap.min.js")
    shutil.copytree(P / "runtime" / "fonts", dst / "fonts")
    (dst / "index.html").write_bytes((src[:root.start()] + tag + src[root.end():]).encode("utf-8"))


def safe_id(bid, i):
    return bid if re.fullmatch(r"[A-Za-z0-9_-]+", bid) else f"beat-{i}"


def main_html(inp, w, h, scene_files):
    rate = inp["rate"]
    layers = [f'      <div class="band" style="z-index: {Z_AROLL}"><video id="aroll" class="clip" src="media/aroll.mp4" '
              f'data-start="0" data-duration="{ts(inp["total"], rate)}" data-track-index="0" muted playsinline '
              f'preload="auto"></video></div>']
    tl = []
    for i, (b, name) in enumerate(scene_files):
        z = Z_SCENE + i
        if z >= Z_PIP:
            raise Stop(1, "✗ This reel has more scenes than the scene layer holds; use fewer scenes.")
        layers.append(f'      <div class="band" style="z-index: {z}"><video id="scene-{name}" class="clip" '
                      f'src="media/{name}.mov" data-start="{ts(b["start_f"], rate)}" '
                      f'data-duration="{ts(b["end_f"] - b["start_f"], rate)}" data-track-index="{i + 1}" muted '
                      f'playsinline preload="auto"></video></div>')
    for k, u in enumerate(inp["under"]):
        el, n = f'"#underlay-{k}"', u["end_f"] - u["start_f"]
        f = min(FADE_F, n // 2)
        layers.append(f'      <div id="underlay-{k}" class="underlay" style="opacity: 0"></div>')
        if u["start_f"] == 0 or not f:  # a run that starts the reel is opaque at frame 0
            tl.append(f"        tl.set({el}, {{ opacity: 1, immediateRender: {'true' if u['start_f'] == 0 else 'false'} }}, "
                      f"{ts(u['start_f'], rate)});")
        else:
            tl.append(f"        tl.fromTo({el}, {{ opacity: 0 }}, {{ opacity: 1, duration: {ts(f, rate)}, ease: \"none\", "
                      f"immediateRender: false }}, {ts(u['start_f'], rate)});")
        if f:
            tl.append(f"        tl.fromTo({el}, {{ opacity: 1 }}, {{ opacity: 0, duration: {ts(f, rate)}, ease: \"none\", "
                      f"immediateRender: false }}, {ts(u['end_f'] - f, rate)});")
        else:
            tl.append(f"        tl.set({el}, {{ opacity: 0 }}, {ts(u['end_f'], rate)});")
    x, y, bw, size = hook_box(w, h)
    s = w / 1080
    if inp["hook_f"]:
        layers.append(f'      <div id="hook">{html.escape(inp["hook_text"])}</div>')
        # complete and still from frame 0: set (never tweened) at 0 and rendered at once, then a hard cut out
        tl.append('        tl.set("#hook", { xPercent: -50, autoAlpha: 1, immediateRender: true }, 0);')
        tl.append(f'        tl.set("#hook", {{ autoAlpha: 0 }}, {ts(inp["hook_f"], rate)});')
    fill = {"W": str(w), "H": str(h), "UNDERLAY": UNDERLAY, "HOOK_X": f"{x:.1f}", "HOOK_Y": f"{y:.1f}",
            "HOOK_W": f"{bw:.1f}", "HOOK_SIZE": f"{size:.1f}", "DURATION": ts(inp["total"], rate),
            "HOOK_SHADOW": f"0 0 {6 * s:.1f}px rgba(0, 0, 0, 0.9), 0 {2 * s:.1f}px {4 * s:.1f}px rgba(0, 0, 0, 0.9)",
            "LAYERS": "\n".join(layers), "TIMELINE": "\n".join(tl)}
    out = TEMPLATE.read_text(encoding="utf-8")
    for k, v in fill.items():
        out = out.replace("{{" + k + "}}", v)
    if "{{" in out:
        raise ValueError("the render template has an unfilled field")
    return out


def render(reel, tier, hook_text, extra_spans=None):
    """One preview or Master. extra_spans (internal, no CLI flag): more gate spans, e.g. S6c's camera moves."""
    t_start = time.perf_counter()
    tmp = reel / "work" / "render-tmp"
    if tmp.exists() and not remove_tree(tmp):  # an earlier run that crashed can leave it behind
        raise Stop(1, f"✗ The old work/render-tmp folder can't be deleted; close what uses it, then run this again.")
    inp = load_inputs(reel)
    if tier == "master":
        latest = latest_preview(reel / "renders")
        ok = None
        try:
            ok = json.loads((reel / OK_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        line = ok_problem(ok, latest.name if latest else None, latest.stat().st_mtime if latest else 0)
        if line:
            raise Stop(1, f"✗ {line}")
    probe_inputs(inp)
    plan(inp, hook_text, extra_spans)
    audio, audio_src = choose_audio(reel, inp, tier)
    w, h = TIERS[tier]
    name = out_names(reel.name, datetime.now().strftime("%m.%d.%y"))[0 if tier == "preview" else 1]
    renders = reel / "renders"
    final, partial = renders / name, renders / (name[:-4] + ".partial.mp4")
    print("info: encode generations: camera -> cut master (1) -> this render (2)")
    env, cache = rt.hyperframes_env(), tmp / "hf-cache"
    proj = tmp / "proj"
    try:
        (proj / "media").mkdir(parents=True)
        cache.mkdir()
        scene_files = []
        for i, b in enumerate(inp["scened"]):
            sid, name_i = b["scene"]["id"], safe_id(b["id"], i)
            sproj = tmp / "scenes" / name_i
            scene_project(sproj, b, inp["rate"])
            vf = tmp / "scenes" / f"{name_i}.vars.json"
            vf.write_bytes(json.dumps({**b["scene"]["slots"], **b["scene"]["params"]}).encode("utf-8"))
            mov = proj / "media" / f"{name_i}.mov"
            hf_render(sproj, mov, env, f"scene {sid} (beat {b['id']})",
                      ["--format", "mov", "--fps", inp["fps"], "--strict-variables", "--variables-file", vf,
                       "--frames-cache-dir", cache])
            got, want = fpsmod.frame_count(mov), b["end_f"] - b["start_f"]
            if got != want:
                raise Stop(1, f"✗ The {sid} scene came out {got} frames long, not {want}; run it again.")
            scene_files.append((b, name_i))
        link_or_copy(inp["master"], proj / "media" / "aroll.mp4")
        (proj / "vendor").mkdir()
        shutil.copy2(P / "runtime" / "gsap" / "gsap.min.js", proj / "vendor" / "gsap.min.js")
        shutil.copytree(P / "runtime" / "fonts", proj / "fonts")
        page = main_html(inp, w, h, scene_files).encode("utf-8")
        assert b"\r" not in page
        (proj / "index.html").write_bytes(page)
        video = tmp / "video.mp4"
        hf_render(proj, video, env, f"{tier} ({w}x{h})",
                  ["--fps", inp["fps"], "--frames-cache-dir", cache, *QUALITY[tier]])
        renders.mkdir(exist_ok=True)
        t0 = time.perf_counter()
        rc, o, e = ffmpeg("-y", "-i", video, "-i", audio_src, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                          "-c:a", "copy", "-movflags", "+faststart", partial)
        if rc != 0 or not partial.is_file():
            raise Stop(1, f"✗ Adding the sound stopped (exit {rc}: {tail(o + e)}); run it again.")
        print(f"info: sound added in {time.perf_counter() - t0:.1f} s")
        got = fpsmod.frame_count(partial)
        st = streams(partial)
        dur = {s.get("codec_type"): float(s.get("duration") or 0) for s in st}
        kinds = sorted(s.get("codec_type") for s in st)
        if got != inp["total"] or kinds != ["audio", "video"] or abs(dur["audio"] - dur["video"]) > 1 / float(inp["rate"]):
            raise Stop(1, f"✗ The render came out wrong ({got} frames for {inp['total']}, streams {kinds}, sound "
                          f"{dur.get('audio', 0):.3f} s against picture {dur.get('video', 0):.3f} s), so it was "
                          f"deleted; run it again.")
        os.replace(partial, final)
    finally:
        partial.unlink(missing_ok=True)
        kill_warm()
        if not remove_tree(tmp):
            print("note: work/render-tmp couldn't be deleted; it's safe to delete by hand")
    print(f"✓ {tier.capitalize()} ready: renders/{final.name}")
    return {"tier": tier, "out": f"renders/{final.name}", "frames": inp["total"], "fps": inp["fps"], "audio": audio,
            "scenes": len(inp["scened"]), "seconds": round(time.perf_counter() - t_start, 1)}


def cmd_ok(reel, from_review):
    if not reel.is_dir():
        raise Stop(2, f"✗ There's no reel folder at {reel}; point --reel-dir at videos/<reel>.")
    latest = latest_preview(reel / "renders")
    if latest is None:
        raise Stop(1, "✗ There's no 720p preview to OK yet; make the preview first.")
    if from_review:
        review = read_json(reel / "review.json", "✗ There's no Master review Send (review.json) yet; "
                                                 "send it from the Master review first.")
        line = review_problem(review, latest.name)
        if line:
            raise Stop(1, f"✗ {line}")
    doc = {"ok_at": datetime.now().astimezone().isoformat(), "preview": latest.name}
    write_json(reel / OK_FILE, doc)
    print(f"✓ OK recorded for {latest.name}; the Master can be made now.")
    return doc


# ---- selftest ------------------------------------------------------------------------------------------------
def selftest():
    import tempfile
    fails = []

    def expect(name, ok):
        if not ok:
            fails.append(name)

    prev, mast = out_names("Reel 7", "11.05.26")
    expect("names", (prev, mast) == ("Reel 7 Preview 720p - 11.05.26.mp4", "Reel 7 Master - 11.05.26.mp4"))
    expect("Master rule: preview fails, Master passes, a partial fails",
           not MASTER_RE.match(prev) and MASTER_RE.match(mast) and not MASTER_RE.match("Reel 7 Master - 11.05.26.partial.mp4"))
    expect("a reel named like a Master still gets a non-Master preview",
           not MASTER_RE.match(out_names("x Master - 01.02.03", "11.05.26")[0]))
    for rate in (Fraction(25), Fraction(30000, 1001), Fraction(24000, 1001), Fraction(60)):
        expect(f"times round back at {rate}", all(round(float(ts(f, rate)) * rate) == f for f in range(0, 20000, 7)))
    now = time.time()
    ok = {"ok_at": datetime.fromtimestamp(now).astimezone().isoformat(), "preview": prev}
    expect("OK of this preview passes", ok_problem(ok, prev, now - 5) is None)
    expect("no OK refuses", ok_problem(None, prev, now - 5) == NEED_OK)
    expect("OK of another preview refuses", ok_problem(dict(ok, preview="old.mp4"), prev, now - 5) == NEED_OK)
    expect("preview newer than the OK refuses", ok_problem(ok, prev, now + 5).startswith(NEED_OK))
    expect("no preview refuses", "no 720p preview" in ok_problem(ok, None, 0))
    rev = {"approve": True, "preview": prev, "note": "", "sent_at": "2026-11-05T10:00:00Z"}
    expect("review approving the latest passes", review_problem(rev, prev) is None)
    expect("review not approving refuses", review_problem(dict(rev, approve=False), prev) is not None)
    expect("review of an older preview refuses", review_problem(rev, "other.mp4") is not None)
    rep = {"pass": True, "video_md5": "abc"}
    expect("audio: passed mix on this cut", audio_choice(rep, "abc", True) == ("mix", None))
    expect("audio: no mix", audio_choice(None, "abc", False) == ("cut", NO_MIX))
    expect("audio: report but no final", audio_choice(rep, "abc", False) == ("cut", NO_MIX))
    expect("audio: stale mix", audio_choice(rep, "def", True) == ("cut", STALE_MIX))
    expect("audio: failed mix", audio_choice(dict(rep, **{"pass": False}), "abc", True) == ("cut", FAILED_MIX))

    def beat(i, s, e, layout="full", scene=None):
        return {"id": i, "start_f": s, "end_f": e, "speech_anchor": {"text": "", "w0": 0, "w1": 0}, "layout": layout,
                "value": None, "scene": scene and {"id": scene, "slots": {}, "params": {}}, "broll": None,
                "transition": None}
    kinds = {"lower-third": "overlay", "hook-title": "takeover", "cta-end-card": "takeover"}
    sp = build_spans([beat("b1", 0, 50), beat("b2", 50, 100, scene="lower-third")], kinds, 50)
    expect("spans: scene overlay + hook overlay, no moves",
           sorted((s["layer"], s["start_f"], s["end_f"]) for s in sp) == [("overlay", 0, 50), ("overlay", 50, 100)])
    expect("gate passes the plain reel", effect_gate.check(sp, [50], "25/1", 100) == [])
    sp = build_spans([beat("b1", 0, 50), beat("ov", 40, 70, "overlay", "hook-title"),
                      beat("b2", 50, 100, scene="cta-end-card")], kinds, 40)
    expect("gate blocks two takeovers at once", any("overlaps takeover" in p for p in effect_gate.check(sp, [50], "25/1", 100)))
    sp = build_spans([beat("b1", 0, 50), beat("b2", 50, 100)], kinds, 50,
                     [{"layer": "aroll_transform", "start_f": 48, "end_f": 52, "id": "move"}])
    expect("extra spans join the gate", any("runs across the cut" in p for p in effect_gate.check(sp, [50], "25/1", 100)))
    import contextlib
    import io
    for sid, slots, opens, keyed in (("hook-title", {"kicker": "Part 1", "title": "Hi"}, True, True),
                                     ("hook-title", {"kicker": "Part 1", "title": "Hi"}, True, False),
                                     ("lower-third", {"name": "Alex", "title": "Founder"}, False, True)):
        b0 = beat("b1", 0, 50, scene=sid)
        b0["scene"]["slots"], b0["scene"]["params"] = slots, ({"entrance": "fade"} if opens else {})
        if not keyed:
            del b0["scene"]["params"]
        inp = {"beats": [b0, beat("b2", 50, 100)], "rate": Fraction(25), "words": [], "total": 100,
               "cut_frames": [50], "fps": "25/1"}
        with contextlib.redirect_stdout(io.StringIO()) as said:
            plan(inp, None)
        expect(f"beat-0 {sid}{'' if keyed else ' (no params key)'}: entrance none only when the scene has it, the warning only when it hasn't, no hook",
               b0["scene"].get("params", {}).get("entrance") == ("none" if opens else None)
               and ("note: the first beat has a scene" in said.getvalue()) != opens and inp["hook_f"] == 0)
    for w, h in TIERS.values():
        x, y, bw, size = hook_box(w, h)
        expect(f"hook box inside the safe zone at {w}x{h}",
               not _ig.violations("hook", x - bw / 2, y, bw, size * 1.15 * 3, w, h))
    with tempfile.TemporaryDirectory() as t:
        r = Path(t)
        for i, n in enumerate((prev, "Reel 7 Preview 720p - 11.04.26.mp4", "Reel 7 Preview 720p - 11.06.26.partial.mp4")):
            (r / n).write_bytes(b"x")
            os.utime(r / n, (now - 100 + i * 10, now - 100 + i * 10))
        expect("latest preview: newest, never a partial", latest_preview(r).name == "Reel 7 Preview 720p - 11.04.26.mp4")
        inp = {"rate": Fraction(25), "total": 100, "under": [{"layer": "underlay", "start_f": 0, "end_f": 60}],
               "hook_f": 50, "hook_text": "Three <edits> & more"}
        page = main_html(inp, 720, 1280, [(beat("b2", 50, 100, scene="lower-third"), "b2")])
        expect("page: filled, escaped, no CR", "{{" not in page and "Three &lt;edits&gt; &amp; more" in page
               and "\r" not in page)
        expect("page: TRI-4 / F-13 rules", "repeat: -1" not in page and "translateX(-50%" not in page
               and "@keyframes" not in page and "onComplete" not in page and "xPercent: -50" in page)
        expect("page: underlay from frame 0 is opaque at 0", 'tl.set("#underlay-0", { opacity: 1, immediateRender: true }, 0)'
               in page)
    for f in fails:
        print(f"selftest FAILED: {f}")
    if not fails:
        print("selftest ok")
    return 1 if fails else 0


# ---- CLI -----------------------------------------------------------------------------------------------------
def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Compose a reel: the 720p preview, the OK, and the Master.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks (no tools) and exit")
    sub = ap.add_subparsers(dest="cmd")
    for name, what in (("preview", "render the 720p preview"), ("master", "render the 1080p Master (needs the OK)")):
        p = sub.add_parser(name, help=what)
        p.add_argument("--reel-dir", required=True, help="the reel folder, videos/<reel>")
        p.add_argument("--hook-text", help="the hook title's words (default: the first beat's words)")
    o = sub.add_parser("ok", help="record the client's OK of the latest preview")
    o.add_argument("--reel-dir", required=True, help="the reel folder, videos/<reel>")
    o.add_argument("--from-review", action="store_true", help="take the OK from the Master review Send (review.json)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help()
        return 2
    reel = Path(a.reel_dir).resolve()
    try:
        summary = cmd_ok(reel, a.from_review) if a.cmd == "ok" else render(reel, a.cmd, a.hook_text)
    except Stop as s:
        for line in s.lines:
            print(line)
        return s.code
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def guarded(fn):
    """The last line of defence: an unexpected failure is one plain line and exit 1, never a traceback."""
    try:
        return fn()
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001  (known failures print their own lines)
        msg = str(e).strip().splitlines()[0][:200] if str(e).strip() else ""
        print(f"✗ The render step stopped unexpectedly ({type(e).__name__}{': ' + msg if msg else ''}). Run it again; "
              f"if it fails twice, offer the failure report.")
        return 1


if __name__ == "__main__":
    sys.exit(guarded(main))
