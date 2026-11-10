"""The compositor (S6b): turn the client's Beat Map Send into the 720p preview, the OK, and the Master.

Run from the client's workspace folder with the editor's own Python:
  compose.py preview --reel-dir videos/<reel> [--hook-text "<text>"]   720x1280, renders/<Reel> Preview 720p - MM.DD.YY.mp4
  compose.py ok      --reel-dir videos/<reel> [--from-review]          records the client's OK of the latest preview
  compose.py master  --reel-dir videos/<reel> [--hook-text "<text>"]   1080x1920, renders/<Reel> Master - MM.DD.YY.mp4
  compose.py --selftest                                                 the rules below, no tools
Exit 0 done, 1 stopped by a check (the plain lines say why and what to do), 2 bad or missing input. The last line
of a successful render is one JSON summary {tier, out, frames, fps, audio, scenes, seconds}.

What a render does: the editing style's plan first (styles.py, in this process with the master's own frame rate;
no style in the Send or the saved style = stop with the ask line, before anything renders), written to
work/scale_track.json; the cut master (work/renders/master-<tag>.mp4) as the a-roll, untouched, inside a box that
takes each key's layout (layouts/<layout>.html, set hard on its frame; the beat's card plate shows over the beat's
frames) and a wrapper that takes the style's punch-ins and moves (the video element itself is never animated);
every beat's G2 scene
rendered on its own as an alpha MOV and placed over its frames (a scene on the first beat that has the `entrance`
param gets entrance "none", so it is complete at frame 0); a still hook title at frame 0 when the first beat
has no scene; the VES-1 effect gate before anything renders; `hyperframes lint` before every render; then ONE audio
stream muxed by stream copy: the sound pass's mix when it passed on this exact cut, else the cut's own sound.
compose.py ok is the only writer of work/render-ok.json; master refuses without an OK of the latest preview.
The picked caption look sits above the picture and scenes, clear of the speaker's head where space allows.
"""
import argparse
import contextlib
import html
import importlib.util
import io
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import unicodedata
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
import saved_style  # noqa: E402
import beat_schema  # noqa: E402
import effect_gate  # noqa: E402
import fps as fpsmod  # noqa: E402
import styles  # noqa: E402  (S6c: the editing style's plan)
import scene_check  # noqa: E402  (P/scripts: the G2-a scene contract)
import licence_rows  # noqa: E402  (G4's licence check, as mix.py imports it)
import footage_check  # noqa: E402
import check as qa_check  # noqa: E402
# --- G5 transitions (VES-1) ---
import transitions
# --- end G5 ---

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
LAYOUTS = SKILL / "layouts"  # split, stack, pip, overlay; "full" is the whole frame with no card
PLATE_Z = Z_SCENE - 1        # a layout's card plate sits on the scene band's floor, under the beat's own scene


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


def us(f, rate):
    """Frame f's time in whole microseconds, rounded DOWN from the exact Fraction: HyperFrames seeks frame n to
    n / fps, so a set or a move placed here takes effect on frame f itself, never a frame late."""
    return math.floor(Fraction(f) / rate * 1_000_000)


def secs(n):
    return f"{n // 1_000_000}.{n % 1_000_000:06d}".rstrip("0").rstrip(".")


def at(f, rate):
    """Frame f as timeline seconds for a style key or move (see us)."""
    return secs(us(f, rate))


def layout(name, s):
    """A layout at scale s (render width / 1080): {box [x, y, w, h], radius, shadow, z, plate (markup)}."""
    if name == "full":
        return {"box": [0, 0, round(1080 * s, 2), round(1920 * s, 2)], "radius": 0, "shadow": "none", "z": Z_AROLL,
                "plate": ""}
    text = re.sub(r"<!--.*?-->", "", (LAYOUTS / f"{name}.html").read_text(encoding="utf-8"), flags=re.S).strip()
    text = re.sub(r"(\d+(?:\.\d+)?)px", lambda m: f"{round(float(m.group(1)) * s, 2):g}px", text)

    def attr(k, default):
        m = re.search(r'\bdata-%s="([^"]*)"' % k, text)
        return m.group(1) if m else default
    return {"box": [round(float(v) * s, 2) for v in attr("box", "").split()],
            "radius": round(float(attr("box-radius", "0")) * s, 2), "shadow": attr("box-shadow", "none"),
            "z": Z_PIP if name == "pip" else Z_AROLL, "plate": text}  # the pip box paints above its card plate


def geom(lay):
    """The box rectangle as GSAP vars: position as x/y transforms (the box sits at left 0, top 0), so a layout move
    never tweens left/top (lint gsap_non_transform_motion); width/height stay box sizes (the video re-covers them)."""
    x, y, w, h = lay["box"]
    return f"x: {x:g}, y: {y:g}, width: {w:g}, height: {h:g}, borderRadius: {lay['radius']:g}"


def chrome(lay):
    return f"zIndex: {lay['z']}, boxShadow: {json.dumps(lay['shadow'])}"


def origin(ox, oy):
    return f"{round(ox * 100, 3):g}% {round(oy * 100, 3):g}%"


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


def hook_words(text):
    """Spoken-hook comparison ignores case and punctuation, never word order."""
    return [word for token in text.lower().split()
            if (word := "".join(c for c in token if not unicodedata.category(c).startswith("P")))]


def title_lines(text, width, size):
    """Estimate Inter wrapping at 0.55 em plus 10% room; retain wide-letter clearance."""
    text = " ".join(text.split())
    average = .55 + .4 * sum(c in "MWmw@%" for c in text) / max(1, len(text))
    chars = max(1, math.floor(width / (size * average * 1.1)))
    return max(1, len(textwrap.wrap(text, width=chars)))


def hook_record(inp):
    """The opening hook actually drawn, in master pixels, regardless of its source."""
    import placer
    opening = next((h for h in inp["hooks"] if h["start_f"] == 0), None)
    if opening is not None:
        return dict(schema=1, kind="plain", text=opening["text"], start_f=0, end_f=opening["end_f"],
                    box=list(placer.hook_still(opening["text"], 0, opening["end_f"])[2]),
                    spoken=opening["spoken"], words_shown=opening["word_count"] if opening["spoken"] else 0)
    first = next((b for b in inp["beats"] if b["start_f"] == 0 and b.get("scene")), None)
    if first is not None and first["scene"]["id"] == "hf-hook-title":
        scene = first["scene"]
        params = {k: p["default"] for k, p in scene_params(scene).items()}
        params.update(scene.get("params", {}))
        box = [60, params["top"], 960, params["top"] + params["height"]]
        return dict(schema=1, kind="scene", text=scene.get("slots", {}).get("title", ""),
                    start_f=0, end_f=first["end_f"], box=box, spoken=False, words_shown=0)
    return dict(schema=1, kind="none", text="", start_f=0, end_f=0,
                box=[0, 0, 0, 0], spoken=False, words_shown=0)


def saved_hooks(reel, fallback=None):
    """Hook-file authority for every QA reader; only a missing file uses legacy inputs."""
    try:
        record = json.loads((Path(reel) / "work/hook.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback
    if (not isinstance(record, dict) or record.get("schema") != 1
            or record.get("kind") not in ("plain", "scene", "none")
            or not isinstance(record.get("text"), str) or type(record.get("spoken")) is not bool
            or record.get("start_f") != 0 or type(record.get("end_f")) is not int or record["end_f"] < 0
            or type(record.get("words_shown")) is not int or record["words_shown"] < 0
            or not isinstance(record.get("box"), list) or len(record["box"]) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in record["box"])):
        raise ValueError("The saved hook record is incomplete; make the preview again.")
    later = [h for h in (fallback or []) if h["start_f"] > 0]
    if record["kind"] == "none":
        return later
    count = len(hook_words(record["text"]))
    if (record["end_f"] <= 0 or record["box"][0] >= record["box"][2]
            or record["box"][1] >= record["box"][3]
            or record["words_shown"] != (count if record["spoken"] else 0)):
        raise ValueError("The saved hook record does not match its words; make the preview again.")
    return [dict(text=record["text"], start_f=0, end_f=record["end_f"], box=record["box"],
                 spoken=record["spoken"], word_count=count, shown_words=list(range(record["words_shown"])))] + later


def plain_hook(text, first, rate, words, total):
    """Resolve the opening still once, for rendering, placement and saved QA."""
    text = " ".join(text.split())
    tokens = hook_words(text)
    count = len(tokens)
    spoken = bool(count and count <= len(words) and tokens == hook_words(" ".join(
        w["word"] if isinstance(w, dict) else w for w in words[:count])))
    minimum = round(Fraction(3, 2) * rate)
    beat_end = first["end_f"] if first else total
    limit = min(total, max(beat_end, minimum) if spoken else beat_end, round(HOOK_MAX_S * rate))
    end = limit
    if spoken and isinstance(words[count - 1], dict):
        end = min(limit, max(minimum,
                             round(Fraction(str(words[count - 1]["end"])) * rate)))
    return dict(text=text, start_f=0, end_f=end, spoken=spoken, word_count=count, shown_words=[])


def hook_captions(doc, hooks):
    """The still supplies all-hook chunks; a mixed or later chunk stays visible."""
    skipped = 0
    for hook in hooks:
        hook["shown_words"] = []
        kept = []
        for chunk in doc["chunks"]:
            positions = list(range(chunk["w0"], chunk["w1"] + 1))
            if (hook["spoken"] and hook["start_f"] <= chunk["start_f"] < hook["end_f"]
                    and positions and all(0 <= w < hook["word_count"] for w in positions)):
                hook["shown_words"].extend(positions)
                skipped += 1
            else:
                kept.append(chunk)
        doc["chunks"] = kept
    doc["hooks"] = hooks
    for i, chunk in enumerate(doc["chunks"]):
        chunk["i"] = i
    print(f"info: {skipped} captions are shown by the hook title instead")
    return skipped


def hook_shown_positions(hooks, words):
    """Validate saved hook coverage before counting omitted captions as shown."""
    shown = set()
    for hook in hooks:
        positions = hook.get("shown_words", [])
        if not positions:
            continue
        count = hook["word_count"]
        if (not hook["spoken"] or hook["start_f"] != 0 or hook["end_f"] <= 0
                or type(count) is not int or not 0 < count <= len(words)
                or len(hook_words(hook["text"])) != count
                or hook_words(hook["text"]) != hook_words(" ".join(w["word"] for w in words[:count]))
                or any(type(w) is not int or not 0 <= w < count for w in positions)):
            raise ValueError("The saved hook words do not match the speech; make the captions again.")
        shown.update(positions)
    return shown


def build_spans(beats, kinds, hook_f, extra_spans=None):
    """Gate spans: the scenes (spans_from_beats; the a-roll's own moves are not made here) + the compose hook as an
    overlay + extra_spans (the editing style's moves from styles.py, so they face the same VES-1 check)."""
    spans = effect_gate.spans_from_beats(beats, 0, scene_kind=kinds)
    if hook_f:
        spans.append({"layer": "overlay", "start_f": 0, "end_f": hook_f, "id": "hook title"})
    return spans + list(extra_spans or [])


# ---- tools ---------------------------------------------------------------------------------------------------
class RenderProgress:
    """Plain, flushed updates at each 10% advance or after 30 seconds of silence."""

    def __init__(self, what):
        self.what = what
        self.start = self.last = time.monotonic()
        self.step, self.percent = -1, None

    def __call__(self, line=""):
        now = time.monotonic()
        found = re.search(r"(?<![\d.])(100|\d{1,2})(?:\.\d+)?\s*%", line)
        if found:
            self.percent = max(self.percent or 0, int(found[1]))
        step = self.percent // 10 if self.percent is not None else -1
        if step <= self.step and now - self.last < 30:
            return
        elapsed = max(0, int(now - self.start))
        percent = f"{self.percent}% " if self.percent is not None else ""
        print(f"Rendering the {self.what}: {percent}({elapsed // 60}:{elapsed % 60:02d} elapsed)", flush=True)
        self.step, self.last = step, now


def run(cmd, env, timeout=None, *, progress=None):
    try:
        if progress is not None:
            return stream_render(cmd, env, progress, timeout)
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def stream_render(cmd, env, what, timeout=None):
    """Drain the render pipe while it runs; retain its log for the existing failure parser."""
    progress, output, pending = RenderProgress(what), [], queue.Queue()
    with subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", bufsize=1, env=env) as process:
        def read_output():
            try:
                for line in process.stdout:
                    pending.put(line)
            finally:
                pending.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            while True:
                if timeout is not None and time.monotonic() - progress.start >= timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)
                try:
                    line = pending.get(timeout=1)
                except queue.Empty:
                    progress()
                    continue
                if line is None:
                    break
                output.append(line)
                progress(line)
            while process.poll() is None:
                if timeout is not None and time.monotonic() - progress.start >= timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    progress()
            return process.returncode, "".join(output), ""
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            reader.join()
            process.stdout.close()


def tail(s, n=300):
    return " ".join(s.split())[-n:]


def free_ram_mb():
    """Available physical RAM in MB, or None when this machine cannot report it."""
    try:
        if sys.platform == "win32":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [
                    (name, ctypes.c_ulonglong) for name in (
                        "total_phys", "avail_phys", "total_page", "avail_page",
                        "total_virtual", "avail_virtual", "avail_extended")]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.avail_phys // (1024 * 1024)
        elif sys.platform.startswith("linux"):
            return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024)
    except Exception:
        pass  # A failed RAM read uses the conservative one-worker budget.
    return None


def master_budget(free_mb, gpu):
    # ponytail: GPU and CPU caps are 2; masked-CPU 2 workers took 286 s, peak 2.4 GB Node.
    # Raise either cap only after a measured 3-worker pass.
    if free_mb is None:
        workers = 1
    elif not gpu:
        workers = 2 if free_mb >= 4096 else 1
    else:
        workers = max(1, min(2, (free_mb - 2048) // 2560))
    return workers, 1024 + 1536 * workers


def render_cause(output):
    if any(cause in output.lower() for cause in ("heap out of memory", "reached heap limit", "allocation failed")):
        return "ran out of memory; close other apps first"
    lines = output.splitlines()
    fatal = [line for line in lines if "fatal error" in line.lower()]
    if fatal:
        return tail(fatal[-1])
    lines = [line for line in lines if line.strip() and not line.lstrip().startswith("Lint:")
             and "--strict" not in line and not re.match(r"^\s*\d+:\s+[0-9A-Fa-f]{6,}", line)]
    errors = [line for line in lines if "error" in line.lower()]
    return tail(errors[-1] if errors else lines[-1] if lines else output)


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
    rc, out, _ = run([rt.tool("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,duration,pix_fmt", "-of", "json",
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
        timed_words = read_json(reel / beat_schema.DEFAULT_WORDS, "The cut word list is missing.").get("words")
        beat_schema.validate_beat_map(bm, words, timed_words if "loops" in bm else None)
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
    return {"bm": bm, "beats": bm["beats"], "words": words, "timed_words": timed_words,
            "cuts": cuts, "master": master, "reel_dir": reel}


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


def broll_plan(inp):
    """Integrity and proof checks block both tiers; placement suggestions are only notes."""
    clips = [b for b in inp["beats"] if b.get("broll")]
    if not clips:
        return
    reel = inp["reel_dir"]
    uses = [dict(path=b["broll"]["src"], src_in_f=b["broll"]["in"], src_out_f=b["broll"]["out"]) for b in clips]
    problems = ["BLOCK " + p for p in footage_check.check(reel, uses)]
    if problems:
        raise Stop(1, *problems)
    try:
        ledger = footage_check.rows(reel)
        resolved = footage_check.resolve_rows(reel, ledger)
        for b in clips:
            clip = b["broll"]
            matches = [r for r, path in resolved if r.get("id") == clip["ledger_id"] and
                       footage_check.normalized(path) ==
                       footage_check.normalized(reel / clip["src"])]
            if len(matches) != 1:
                problems.append(f"BLOCK beat {b['id']}: the clip needs its matching footage ledger row")
                continue
            row = matches[0]
            category = None
            if b.get("scene"):
                spec = json.loads((scene_check.SCENES / b["scene"]["id"] / "scene.json").read_text(encoding="utf-8"))
                category = spec.get("category")
            if row.get("origin") == "ai" and (b.get("value") is not None or category in scene_check.NUMBER_SCENES):
                problems.append(f"BLOCK beat {b['id']}: an AI clip can't sit on a beat that shows a number: it would look like proof")
            if clip["out"] > fpsmod.frame_count(reel / clip["src"]):
                problems.append(f"BLOCK beat {b['id']}: the B-roll clip is too short for this source range")
            if b["start_f"] < 3 * inp["rate"] or b["end_f"] > inp["total"] - 3 * inp["rate"]:
                print(f"note: beat {b['id']} uses B-roll in the first or last 3 seconds; consider leaving the speaker visible there")
            count = lambda beat: sum(beat["start_f"] < c < beat["end_f"] for c in inp["cut_frames"])
            dense = next((other for other in inp["beats"] if other["end_f"] - other["start_f"] == b["end_f"] - b["start_f"]
                          and count(other) >= 2), None)
            if count(b) == 0 and dense:
                print(f"note: consider B-roll on beat {dense['id']} instead of {b['id']}; it covers more jump cuts")
    except (OSError, ValueError, KeyError, TypeError) as e:
        problems.append("BLOCK the B-roll could not be checked: " + str(e).splitlines()[0])
    if problems:
        raise Stop(1, *problems, "Nothing was rendered; fix the B-roll and Send again.")


def footage_licences(inp, tier):
    rows = licence_rows.footage({"reel_dir": inp["reel_dir"], "cuts": inp["cuts"], "beats": inp["beats"]})
    blocks = [r["msg"] for r in rows if r["level"] == "block"]
    if blocks and tier == "master":
        raise Stop(1, *["BLOCK " + m for m in blocks], "The Master wasn't made; complete the footage licence rows first.")
    for m in blocks:
        print(f"warning: {m} (the Master will refuse until it's fixed)")


def brand_params(spec, html, beat_params, saved):
    """Saved brand choices for declared scene params, then the beat's more specific choices; no I/O."""
    params, notes = {}, []
    declared = spec.get("params", {})
    if "accent" in declared and "accent" in saved:
        accent = saved["accent"]
        if isinstance(accent, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
            params["accent"] = accent
        else:
            notes.append("Your saved brand colour needs six colour digits, such as #E0218A, so the scenes use their own colours.")
    if "font" in declared and "font" in saved:
        font = saved["font"]
        if not isinstance(font, str) or not font.strip():
            notes.append("Your saved brand font needs a family name, so the scenes use their own fonts.")
        elif font not in scene_check.font_faces(html):
            notes.append(f"Your brand font {font} isn't available for on-screen graphics yet, "
                         f"so they use {declared['font']['default']}.")
        else:
            params["font"] = font
    params.update(beat_params)
    return params, notes


def saved_brand(reel=None):
    """Read only the saved brand keys; missing or unreadable taste choices never stop a render."""
    try:
        with contextlib.redirect_stderr(io.StringIO()) as note:
            saved = saved_style.load(reel)
        if note.getvalue():
            raise ValueError("saved style could not be read")
        if not isinstance(saved, dict):
            raise ValueError("saved style must be an object")
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        print("note: Your saved brand style couldn't be read, so the scenes use their own colours and fonts.")
        return {}
    return {key: saved[key] for key in ("accent", "font") if key in saved}


def plan(inp, hook_text, extra_spans=None, *, ctx=None):
    """Notes, scene checks, the hook, and the effect gate; raises Stop before anything renders."""
    beats, rate = inp["beats"], inp["rate"]
    broll_plan(inp)
    # --- G5 transitions (VES-1) ---
    try:
        transitions.plan(inp)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        raise Stop(1, " ".join(str(error).splitlines())) from None
    # --- end G5 ---
    scened = [b for b in beats if b["scene"] is not None]
    saved = saved_brand(inp.get("style_reel", inp.get("reel_dir"))) if scened else {}
    brand_notes = set()
    opens = set()  # H-S6b-19: a scene that opens the reel is complete at frame 0 when it can be
    for b in scened:
        params = b["scene"].get("params", {})  # no params key = {} (as fill_problems reads it)
        declared = scene_params(b["scene"])
        if isinstance(params, dict):
            try:
                page = (scene_check.SCENES / b["scene"]["id"] / "scene.html").read_text(encoding="utf-8")
            except OSError:
                page = ""  # fill_problems names the missing scene below
            params, notes = brand_params({"params": declared}, page, params, saved)
            b["scene"] = dict(b["scene"], params=params)
            for note in notes:
                if note not in brand_notes:
                    print(f"note: {note}")
                    brand_notes.add(note)
        if b["start_f"] == 0 and isinstance(params, dict) and "entrance" in declared:
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
        if b["scene"]["id"] == "slots":
            params = {k: p["default"] for k, p in specs["slots"]["params"].items()}
            params.update(b["scene"].get("params", {}))
            if any(float(t) >= float(secs) for t in params["section_starts"].split(",")):
                problems.append("The slots section starts must fit inside their existing beat; choose earlier starts or another scene.")
    first = next((b for b in beats if b["start_f"] == 0), None)
    hook_f, text, hooks = 0, None, []
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
        hook = plain_hook(text, first, rate, inp.get("timed_words") or inp["words"], inp["total"])
        hooks.append(hook)
        hook_f = hook["end_f"]
    else:
        print("note: no beat starts at frame 0, so there's no hook title; tell me the hook text to add one")
    inp.update(scened=scened, hook_f=hook_f, hook_text=text, hooks=hooks,
               hook_spoken=bool(hooks and hooks[0]["spoken"]))
    title_notes = place_hook_titles(inp, ctx) if ctx is not None else []
    kinds = {sid: spec["kind"] for sid, spec in specs.items()}
    try:
        spans = build_spans(beats, kinds, inp["hook_f"], extra_spans)
        spans.extend(dict(layer="overlay", start_f=h["start_f"], end_f=h["end_f"], id="hook title")
                     for h in inp["hooks"] if h["start_f"] > 0)
    except ValueError as e:
        raise Stop(1, f"✗ {e}") from None
    problems += [f"BLOCK {p}" for p in effect_gate.check(spans, inp["cut_frames"], inp["fps"], inp["total"])]
    if problems:
        raise Stop(1, *problems, "Nothing was rendered; fix these on the Beat Map board and Send again.")
    inp["under"] = effect_gate.underlay(spans, inp["fps"])
    return title_notes


def scene_params(scene):
    """The params a scene's scene.json declares ({} when it can't be read; fill_problems then says why)."""
    try:
        spec = json.loads((scene_check.SCENES / str(scene.get("id")) / "scene.json").read_text(encoding="utf-8"))
        return spec.get("params") or {}
    except (OSError, ValueError, AttributeError):
        return {}


def hook_title_placement(ctx, beat):
    """Fit above the head, or request a plain still instead of covering the face."""
    import placer
    explicit = beat["scene"].get("params", {})
    placed = {"top": 220, "height": 1250, "size": 120}
    head = placer.head_box_at(ctx, beat["start_f"], beat["end_f"] - 1)
    if head is None:
        placed.update({k: explicit[k] for k in placed if k in explicit})
        return placed, "The hook title wasn't checked against your face because no face anchors were found."
    safe_top, safe_bottom = placer.SAFE[1], placer.SAFE[3]
    protected = placer.face_band(head, top=0)
    ceiling = min(safe_bottom, protected[1] - placer.UNDER_HEAD_GAP)
    placed.update(top=safe_top, height=max(0, ceiling - safe_top))
    placed.update({k: explicit[k] for k in placed if k in explicit})
    title = beat["scene"].get("slots", {}).get("title", "Nobody tells you this about editing")

    def fits(size):
        # The line is 640px wide; include its breath and the bow's 6-degree tilt.
        lines = title_lines(title, 640, size)
        half = lines * size * 1.05 * 1.035 / 2
        angle = math.radians(6)
        projected = half * math.cos(angle) / (1 - half * math.sin(angle) / 950)
        return 2 * projected + 48 <= placed["height"]  # room for fringe and rest blur

    if "size" not in explicit:
        while placed["size"] > 56 and not fits(placed["size"]):
            placed["size"] -= 1
    if (not fits(placed["size"]) or placed["top"] < safe_top
            or placed["top"] + placed["height"] > ceiling):
        return None, "The hook title didn't fit above your face, so a plain hook title is used."
    return placed, None


def placement_hooks(inp):
    """Plain hooks plus fitted scene text boxes, solely for placement and QA."""
    hooks = list(inp["hooks"])
    for beat in inp["beats"]:
        scene = beat.get("scene")
        if scene and scene["id"] == "hf-hook-title":
            params = scene["params"]
            hooks.append(dict(text=scene["slots"]["title"], start_f=beat["start_f"], end_f=beat["end_f"],
                              box=[60, params["top"], 960, params["top"] + params["height"]],
                              spoken=False, word_count=len(hook_words(scene["slots"]["title"])), shown_words=[]))
    return hooks


def place_hook_titles(inp, ctx):
    """Drop unfit prism scenes only for this render; preserve their title in a still."""
    notes = []
    for beat in inp["beats"]:
        scene = beat.get("scene")
        if not scene or scene["id"] != "hf-hook-title":
            continue
        placed, note = hook_title_placement(ctx, beat)
        if placed is not None:
            scene.setdefault("params", {}).update(placed)
        else:
            beat["scene"] = None
            text = scene["slots"]["title"]
            if beat["start_f"] == 0:
                hook = plain_hook(text, beat, inp["rate"], inp.get("timed_words") or inp["words"], inp["total"])
                inp["hooks"] = [h for h in inp["hooks"] if h["start_f"] != 0] + [hook]
                inp.update(hook_text=text, hook_f=hook["end_f"], hook_spoken=hook["spoken"])
            else:
                inp["hooks"].append(dict(text=text, start_f=beat["start_f"],
                                         end_f=min(beat["end_f"], beat["start_f"] + round(HOOK_MAX_S * inp["rate"])),
                                         spoken=False, word_count=len(hook_words(text)), shown_words=[]))
        if note and note not in notes:
            notes.append(note)
    inp["scened"] = [b for b in inp["beats"] if b.get("scene") is not None]
    import placer
    placer.set_hook_stills(ctx, placement_hooks(inp))
    return notes


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
        rows = licence_rows.music({"reel_dir": reel, "fps": float(inp["rate"]), "cuts": inp["cuts"],
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


def hf_render(proj, out, env, what, extra, *, tier=None):
    ok, lines = lint_or_stop(proj, what, env)
    print(f"info: lint {what}: {sum(l.startswith('✗') for l in lines)} errors, "
          f"{sum(l.startswith('warning:') for l in lines)} warnings")
    if not ok:
        raise Stop(1, *lines, "Nothing was rendered.")
    for line in lines:
        print(line)
    if tier == "master":
        free_mb, gpu = free_ram_mb(), rt.has_nvidia_gpu()
        workers, heap_mb = master_budget(free_mb, gpu)
        env = dict(env)
        options = re.sub(r'(?<!\S)(?:"--max-old-space-size(?:=|\s+)\d+"|'
                         r'--max-old-space-size(?:=|\s+)(?:"\d+"|\d+))(?=\s|$)',
                         "", env.get("NODE_OPTIONS", "")).strip()
        env["NODE_OPTIONS"] = f"{options} --max-old-space-size={heap_mb}".strip()
        extra = [*extra, "--workers", str(workers)]
        memory = "free RAM unknown" if free_mb is None else f"{free_mb / 1024:.1f} GB free"
        print(f"info: master render: {workers} worker{'s' if workers != 1 else ''}, {heap_mb} MB Node heap "
              f"({'NVIDIA GPU' if gpu else 'CPU only'}, {memory})")
    t0 = time.perf_counter()
    print(f"Rendering the {what}.", flush=True)
    rc, o, e = run(rt.hyperframes_cmd("render", proj, *extra, "-o", out), env, progress=what)
    kill_warm()
    if rc != 0 or not out.is_file():
        cause = render_cause(o + "\n" + e)
        reason = cause if cause.startswith("ran out of memory") else f"stopped (exit {rc}: {cause})"
        raise Stop(1, f"✗ The {what} render {reason}; run it again, and if it fails "
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


# ---- N3: 3D scenes (category "3d", layer band 300-399, three.js from ./vendor) ----
Z_3D = 300
THREE_RUNTIME = P / "runtime" / "three"
_n3_scene_project = scene_project


def scene_is_3d(beat):
    scene = beat.get("scene")
    if not scene:
        return False
    spec = json.loads((scene_check.SCENES / scene["id"] / "scene.json").read_text(encoding="utf-8"))
    return spec.get("category") == "3d"


def scene_z(beat, i):
    if scene_is_3d(beat):
        z = Z_3D + i
        if z >= 400:
            raise Stop(1, "This reel has more scenes than the 3D layer holds; use fewer scenes.")
        return z
    return Z_SCENE + i


def scene_project(dst, beat, rate):
    result = _n3_scene_project(dst, beat, rate)
    if scene_is_3d(beat):
        files = ("three.module.js", "three.core.js")
        if not all((THREE_RUNTIME / name).is_file() for name in files):
            raise Stop(1, "The 3D engine files are missing, reinstall the editor.")
        for name in files:
            shutil.copy2(THREE_RUNTIME / name, dst / "vendor" / name)
    return result


# ---- G2-c: copy exactly the optional local runtime files a scene names ----
MOTION_RUNTIME = P / "runtime" / "motion"
_g2c_scene_project = scene_project


def scene_project(dst, beat, rate):
    result = _g2c_scene_project(dst, beat, rate)
    html = (scene_check.SCENES / beat["scene"]["id"] / "scene.html").read_text(encoding="utf-8")
    parser = scene_check._N3Scripts()
    parser.feed(html)
    sources = [attrs.get("src") for attrs, _ in parser.scripts]
    if scene_check.MOTION_SRC in sources:
        source = MOTION_RUNTIME / "motion.js"
        if not source.is_file():
            raise Stop(1, "The Motion engine file is missing, reinstall the editor.")
        shutil.copy2(source, dst / "vendor" / source.name)
    if scene_is_3d(beat):
        # Validate before using map values as filesystem paths.
        maps = [body for attrs, body in parser.scripts if attrs.get("type", "").strip().lower() == "importmap"]
        if maps:
            try:
                doc = json.loads(maps[0])
                imports = doc["imports"]
                if (len(maps) != 1 or set(doc) != {"imports"} or "three" not in imports
                        or not all(scene_check.LEAD_IMPORTS.get(k) == v for k, v in imports.items())):
                    raise ValueError
            except (ValueError, TypeError, KeyError, AttributeError):
                raise Stop(1, "The 3D scene import map is invalid; use the shipped local engine files.")
            for value in imports.values():
                name = value.removeprefix("./vendor/")
                source = THREE_RUNTIME / name
                if not source.is_file():
                    raise Stop(1, "The 3D engine files are missing, reinstall the editor.")
                shutil.copy2(source, dst / "vendor" / name)
    return result


def safe_id(bid, i):
    return bid if re.fullmatch(r"[A-Za-z0-9_-]+", bid) else f"beat-{i}"


def broll_name(beat, i):
    # Include the index so two ids that need sanitizing can never collide.
    return f"broll-{safe_id(beat['id'], i)}-{i}"


def main_html(inp, w, h, scene_files, layers="all"):
    if layers not in ("all", "aroll", "overlay", "captions"):
        raise ValueError("unknown render layers")
    which = layers
    if which == "aroll":
        inp = dict(inp, beats=[], under=[], hook_f=0, hooks=[], captions=None)
        scene_files = []
    elif which == "captions":
        inp = dict(inp, beats=[], under=[], hook_f=0, hooks=[], track={"keys": [], "tweens": [], "style": {}})
        scene_files = []
    elif which == "overlay":
        inp = dict(inp, captions=None)
    rate, s = inp["rate"], w / 1080
    track = inp.get("track") or {"keys": [], "tweens": [], "style": {}}
    baked = baked_spans(track, inp.get("beats", []), inp["total"]) if which == "overlay" else []
    if which == "overlay":
        track = dict(track, keys=[], tweens=[])
    lays = {}

    def lay(name):
        if name not in lays:
            lays[name] = layout(name, s)
        return lays[name]
    # the box takes the layout, the wrapper takes the style's scale and zoom centre; the video is never animated
    layers = [f'      <div id="aroll-box" class="band" style="z-index: {Z_AROLL}; overflow: hidden">'
              f'<div id="aroll-move" style="position: absolute; left: 0; top: 0; width: 100%; height: 100%">'
              f'<video id="aroll" class="clip" src="media/aroll.mp4" data-start="0" '
              f'data-duration="{ts(inp["total"], rate)}" data-track-index="0" muted playsinline preload="auto" '
              f'style="width: 100%; height: 100%"></video></div></div>'] if which in ("all", "aroll") else []
    tl = []
    for i, b in enumerate(b for b in inp.get("beats", []) if b.get("broll")):
        clip, name = b["broll"], broll_name(b, i)
        videos = []
        fits = ("broll-back", "broll-front") if clip["fit"] == "blur-fill" else ("",)
        for j, css in enumerate(fits):
            # every <video> needs an id (HyperFrames finds media by id; without one it renders frozen), and the
            # blurred back plate reads its own copy so the two never look like one duplicated media entry
            vid = name + ("-back" if css == "broll-back" else "")
            videos.append(f'<video id="{vid}" class="clip {css}" src="media/{vid}.mp4" '
                          f'data-start="{ts(b["start_f"], rate)}" data-duration="{ts(b["end_f"] - b["start_f"], rate)}" '
                          f'data-media-start="{ts(clip["in"], rate)}" data-track-index="{len(scene_files) + 1 + i * 2 + j}" '
                          f'muted playsinline preload="auto"></video>')
        layers.append('<div class="band" style="z-index: 200">' + "".join(videos) + '</div>')
    for k in track["keys"]:  # a key = the whole a-roll state, set hard on its frame
        t, imm = at(k["f"], rate), "true" if k["f"] == 0 else "false"
        tl.append(f'        tl.set("#aroll-move", {{ scale: {k["scale"]}, transformOrigin: "{origin(k["ox"], k["oy"])}", '
                  f'immediateRender: {imm} }}, {t});')
        tl.append(f'        tl.set("#aroll-box", {{ {geom(lay(k["layout"]))}, {chrome(lay(k["layout"]))}, '
                  f'immediateRender: {imm} }}, {t});')
    for m in track["tweens"]:  # a move = one fromTo, starting AND ending on whole frames (F-13)
        t0 = at(m["start_f"], rate)
        end = (f'duration: {secs(us(m["end_f"], rate) - us(m["start_f"], rate))}, ease: "{m["ease"]}", '
               f'immediateRender: false }}, {t0});')
        if m["prop"] == "scale":
            tl.append(f'        tl.fromTo("#aroll-move", {{ scale: {m["from"]} }}, {{ scale: {m["to"]}, {end}')
        elif m["prop"] == "origin":
            tl.append(f'        tl.fromTo("#aroll-move", {{ transformOrigin: "{origin(*m["from"])}" }}, '
                      f'{{ transformOrigin: "{origin(*m["to"])}", {end}')
        else:  # a layout move: the geometry moves; stacking and ring are the pip side's for the whole move
            a, b = lay(m["from"]), lay(m["to"])
            tl.append(f'        tl.set("#aroll-box", {{ {chrome(a if a["z"] > b["z"] else b)}, immediateRender: false }}, '
                      f'{t0});')
            tl.append(f'        tl.fromTo("#aroll-box", {{ {geom(a)} }}, {{ {geom(b)}, {end}')
            tl.append(f'        tl.set("#aroll-box", {{ {chrome(b)}, immediateRender: false }}, {at(m["end_f"], rate)});')
    for i, (b, name) in enumerate(scene_files):
        z = scene_z(b, i)
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
    if track["style"].get("style") == "layout-switch":  # each non-full beat's card plate over the beat's frames
        for k, b in enumerate(b for b in inp["beats"] if b["layout"] != "full"):
            el = f'"#plate-{k}"'
            layers.append(f'      <div id="plate-{k}" class="band" style="z-index: {PLATE_Z}; opacity: 0; '
                          f'visibility: hidden">{lay(b["layout"])["plate"]}</div>')
            tl.append(f"        tl.set({el}, {{ autoAlpha: 1, immediateRender: {'true' if b['start_f'] == 0 else 'false'} "
                      f"}}, {at(b['start_f'], rate)});")
            if b["end_f"] < inp["total"]:
                tl.append(f"        tl.set({el}, {{ autoAlpha: 0, immediateRender: false }}, {at(b['end_f'], rate)});")
    x, y, bw, size = hook_box(w, h)
    hooks = inp.get("hooks", [dict(text=inp["hook_text"], start_f=0, end_f=inp["hook_f"])]
                    if inp["hook_f"] else [])
    for i, hook in enumerate(hooks):
        hid = "hook" if hook["start_f"] == 0 else f"hook-{i}"
        layers.append(f'      <div id="{hid}" class="plain-hook" style="opacity: 0; visibility: hidden">'
                      f'{html.escape(hook["text"])}</div>')
        imm = "true" if hook["start_f"] == 0 else "false"
        tl.append(f'        tl.set("#{hid}", {{ xPercent: -50, autoAlpha: 1, immediateRender: {imm} }}, '
                  f'{ts(hook["start_f"], rate)});')
        tl.append(f'        tl.set("#{hid}", {{ autoAlpha: 0, immediateRender: false }}, {ts(hook["end_f"], rate)});')
    caption_css = ""
    doc = inp.get("captions")
    if doc and doc["chunks"]:
        sys.path.insert(0, str(HERE.parents[1] / "reel-captions" / "scripts"))
        import captions
        caption_css, caption_layers, caption_tl = captions.layer(
            doc, [c["box"] for c in doc["chunks"]], s, lambda f: at(f, rate))
        layers.extend(caption_layers)
        tl.extend(caption_tl)
    # --- G5 transitions (VES-1) ---
    # A-roll handoff pages keep the base picture: the Master clip carries the move.
    if which in ("all", "overlay"):
        transition_layers, transition_tl, _, _ = transitions.layer(inp, w, h, rate)
        layers.extend(transition_layers)
        tl.extend(transition_tl)
    # --- end G5 ---
    if baked:
        layers = ['      <div id="handoff-overlay" class="band">' + "\n".join(layers) + '</div>']
        tl.append('        tl.set("#handoff-overlay", { opacity: 1, immediateRender: true }, 0);')
        for span in baked:
            imm = "true" if span["start_f"] == 0 else "false"
            tl.append(f'        tl.set("#handoff-overlay", {{ opacity: 0, immediateRender: {imm} }}, {at(span["start_f"], rate)});')
            tl.append(f'        tl.set("#handoff-overlay", {{ opacity: 1, immediateRender: false }}, {at(span["end_f"], rate)});')
    fill = {"W": str(w), "H": str(h), "UNDERLAY": UNDERLAY, "HOOK_X": f"{x:.1f}", "HOOK_Y": f"{y:.1f}",
            "HOOK_W": f"{bw:.1f}", "HOOK_SIZE": f"{size:.1f}", "DURATION": ts(inp["total"], rate),
            "HOOK_SHADOW": f"0 0 {6 * s:.1f}px rgba(0, 0, 0, 0.9), 0 {2 * s:.1f}px {4 * s:.1f}px rgba(0, 0, 0, 0.9)",
            "LAYERS": "\n".join(layers), "TIMELINE": "\n".join(tl), "CAPTION_CSS": caption_css}
    out = TEMPLATE.read_text(encoding="utf-8").replace("#hook {", ".plain-hook {")
    if which in ("overlay", "captions"):
        out = out.replace("background: #000000;", "background: transparent;")
    for k, v in fill.items():
        out = out.replace("{{" + k + "}}", v)
    if "{{" in out:
        raise ValueError("the render template has an unfilled field")
    return out


def baked_spans(track, beats, total):
    """Frames needing the finished picture; touching ranges merge, with combined layout labels."""
    ranges = []

    def add(start, end, layout):
        start, end = max(0, start), min(total, end)
        if start < end:
            ranges.append({"start_f": start, "end_f": end, "layout": layout})

    keys = sorted(track.get("keys", []), key=lambda k: k["f"])
    for i, key in enumerate(keys):
        if key["layout"] in ("pip", "overlay"):
            add(key["f"], keys[i + 1]["f"] if i + 1 < len(keys) else total, key["layout"])
    for move in track.get("tweens", []):
        if move["prop"] == "layout":
            for name in ("pip", "overlay"):
                if name in (move["from"], move["to"]):
                    add(move["start_f"], move["end_f"], name)
    if track.get("style", {}).get("style") == "layout-switch":
        for beat in beats:
            if beat["layout"] in ("pip", "overlay"):
                add(beat["start_f"], beat["end_f"], beat["layout"])
    # --- G5 transitions (VES-1) ---
    # Flash and overlay types (fade, push, wipe, shader) stay in the overlay layer;
    # only cut types that move the a-roll need frames from the finished Master.
    for span in transitions.spans(beats):
        spec = transitions.MENU[span["transition"]["type"]]
        if spec["kind"] == "cut" and spec.get("moves_aroll"):
            add(span["start_f"], span["end_f"], "transition")
    # --- end G5 ---
    merged = []
    for span in sorted(ranges, key=lambda r: (r["start_f"], r["end_f"])):
        if merged and span["start_f"] <= merged[-1]["end_f"]:
            merged[-1]["end_f"] = max(merged[-1]["end_f"], span["end_f"])
            merged[-1]["layout"] = "+".join(sorted(set(merged[-1]["layout"].split("+")) | {span["layout"]}))
        else:
            merged.append(dict(span))
    return merged


# --- G5 transitions (VES-1) ---
NEED_BAKED_MASTER = "Render the Master first: the picture-in-picture or blurred-card parts or transitions are taken from it."
# --- end G5 ---


def require_baked_master(reel, spans, total, rate):
    if not spans:
        return None
    candidates = [p for p in (reel / "renders").glob("*") if p.is_file() and MASTER_RE.fullmatch(p.name)]
    latest = max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name)) if candidates else None
    try:
        if latest is not None and fpsmod.as_fraction(fpsmod.resolve_fps(latest)) == rate and fpsmod.frame_count(latest) == total:
            return latest
    except (OSError, ValueError):
        pass
    raise Stop(1, NEED_BAKED_MASTER)


def render(reel, tier, hook_text, extra_spans=None, keep_project=False, layers="all", *, remember_choices=True, style_reel=None):
    """One preview or Master. extra_spans (internal, no CLI flag): more gate spans, e.g. a test's planted move."""
    t_start = time.perf_counter()
    if layers not in ("all", "aroll", "overlay", "captions"):
        raise Stop(2, "Choose all, aroll, overlay or captions layers.")
    if layers != "all":
        tier = "master"
    tmp = reel / "work" / "render-tmp"
    if tmp.exists() and not remove_tree(tmp):  # an earlier run that crashed can leave it behind
        raise Stop(1, f"✗ The old work/render-tmp folder can't be deleted; close what uses it, then run this again.")
    inp = load_inputs(reel)
    style_reel = reel if style_reel is None else style_reel
    inp["style_reel"] = style_reel
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
    try:  # H-R36: no editing style anywhere = the ask line, and nothing renders
        track = styles.plan(reel, fps=inp["fps"], remember_choices=remember_choices, style_reel=style_reel)
    except styles.Stop as e:
        raise Stop(e.code, *e.lines) from None
    for line in track["warnings"]:
        print(f"note: {line}")
    inp["track"] = track
    styles.write_json(reel / styles.TRACK, track)  # S7 reads it
    sys.path.insert(0, str(HERE.parents[1] / "reel-captions" / "scripts"))
    import captions
    import placer  # placer imports compose; keep this import inside render()
    import broll_bands
    try:
        ctx = None
        band_notes = []
        if any(b.get("scene") and b["scene"]["id"] == "hf-hook-title" for b in inp["beats"]):
            band_notes.extend(broll_bands.measure(reel, inp["beats"]))
            ctx = placer.load_ctx(reel)
        title_notes = plan(inp, hook_text, track["spans"] + list(extra_spans or []), ctx=ctx)
        baked = baked_spans(track, inp["beats"], inp["total"]) if layers != "all" else []
        require_baked_master(reel, baked, inp["total"], inp["rate"])
        footage_licences(inp, tier)
        if remember_choices:
            doc = captions.plan(reel, fps=inp["fps"], style_reel=style_reel, render_beats=inp["beats"])
        else:  # N5 scratch renders must not rewrite the shared saved caption choice.
            cs, _ = captions.pick_style(reel, remember=False, style_reel=style_reel)
            doc = captions.plan(reel, fps=inp["fps"], _style=cs, style_reel=style_reel, render_beats=inp["beats"])
        hook_captions(doc, inp["hooks"])
        doc["hooks"] = placement_hooks(inp)
        doc["notes"].extend(title_notes)
        if doc["chunks"]:
            if ctx is None:
                band_notes.extend(broll_bands.measure(reel, inp["beats"]))
                ctx = placer.load_ctx(reel, hook=(inp["hook_text"], inp["hook_f"]) if inp["hook_f"] else None)
            placer.set_hook_stills(ctx, doc["hooks"])
            spec = captions.STYLES[doc["style"]["style"]]
            bands = []
            for c in doc["chunks"]:
                # Captions end exclusively; placer's public spans end inclusively.
                c["box"] = placer.place(ctx, c["start_f"], c["end_f"] - 1, captions.band_h(spec))
                bands.append(dict(start_f=c["start_f"], end_f=c["end_f"] - 1, box=c["box"]))
            doc["notes"].extend(ctx["notes"] + placer.ghosts(ctx, bands))
        doc["notes"].extend(band_notes)
    except captions.Stop as e:
        raise Stop(e.code, *e.lines) from None
    except (placer.NoRoom, ValueError) as e:
        raise Stop(2, str(e)) from None
    inp["captions"] = doc
    captions.write(reel, doc)  # S9 reads the placed chunks, including advisory notes
    if layers == "all":  # layer-only handoffs must not replace the preview/master QA record
        write_json(reel / "work/hook.json", hook_record(inp))
    for line in doc["notes"]:
        print(f"note: {line}")
    printed_notes = len(doc["notes"])
    audio, audio_src = choose_audio(reel, inp, tier) if layers == "all" else ("cut", inp["master"])
    w, h = TIERS[tier]
    name = out_names(reel.name, datetime.now().strftime("%m.%d.%y"))[0 if tier == "preview" else 1]
    renders = reel / "renders"
    if layers != "all":
        ext = "mov" if layers in ("overlay", "captions") else "mp4"
        label = {"overlay": "Overlay", "captions": "Captions", "aroll": "A-roll"}[layers]
        name = f"{reel.name} {label} - {datetime.now().strftime('%m.%d.%y')}.{ext}"
        renders = reel / "handoff"
    final, partial = renders / name, renders / (name[:-4] + ".partial.mp4")
    if layers in ("overlay", "captions"):
        partial = renders / (name[:-4] + ".partial.mov")
    print("info: encode generations: camera -> cut master (1) -> this render (2)")
    env, cache = rt.hyperframes_env(), tmp / "hf-cache"
    proj = tmp / "proj"
    try:
        (proj / "media").mkdir(parents=True)
        cache.mkdir()
        scene_files = []
        for i, b in enumerate(inp["scened"] if layers in ("all", "overlay") else []):
            sid, name_i = b["scene"]["id"], safe_id(b["id"], i)
            sproj = tmp / "scenes" / name_i
            scene_project(sproj, b, inp["rate"])
            vf = tmp / "scenes" / f"{name_i}.vars.json"
            vf.write_bytes(json.dumps({**b["scene"]["slots"], **(b["scene"].get("params") or {})}).encode("utf-8"))
            mov = proj / "media" / f"{name_i}.mov"
            hf_render(sproj, mov, env, f"scene {sid} (beat {b['id']})",
                      ["--format", "mov", "--fps", inp["fps"], "--strict-variables", "--variables-file", vf,
                       "--frames-cache-dir", cache])
            got, want = fpsmod.frame_count(mov), b["end_f"] - b["start_f"]
            if got != want:
                raise Stop(1, f"✗ The {sid} scene came out {got} frames long, not {want}; run it again.")
            scene_files.append((b, name_i))
        if layers in ("all", "aroll"):
            link_or_copy(inp["master"], proj / "media" / "aroll.mp4")
        for i, b in enumerate(b for b in inp["beats"] if b.get("broll") and layers in ("all", "overlay")):
            names = [broll_name(b, i)] + ([broll_name(b, i) + "-back"] if b["broll"]["fit"] == "blur-fill" else [])
            for n in names:
                link_or_copy(reel / b["broll"]["src"], proj / "media" / (n + ".mp4"))
        (proj / "vendor").mkdir()
        shutil.copy2(P / "runtime" / "gsap" / "gsap.min.js", proj / "vendor" / "gsap.min.js")
        # --- G5 transitions (VES-1) ---
        transitions.copy_vendor(inp, proj, layers)
        # --- end G5 ---
        shutil.copytree(P / "runtime" / "fonts", proj / "fonts")
        page = main_html(inp, w, h, scene_files, layers=layers).encode("utf-8")
        # --- G6 cover (embed) ---
        cover_file, cover_image = reel / "cover.json", reel / "cover.jpg"
        if layers == "all" and cover_file.is_file() and cover_image.is_file():
            cover = read_json(cover_file, "The cover choice could not be read; Send the Cover Picker again.")
            if cover.get("embed_first_frame") is True:
                link_or_copy(cover_image, proj / "media" / "cover.jpg")
                still = (f'<img id="cover-first-frame" src="media/cover.jpg" alt="" '
                         f'style="position:absolute;left:0;top:0;width:{w}px;height:{h}px;z-index:650;'
                         'visibility:hidden;object-fit:fill">\n')
                sets = ('        tl.set("#cover-first-frame", { autoAlpha: 1, immediateRender: true }, 0);\n'
                        f'        tl.set("#cover-first-frame", {{ autoAlpha: 0, immediateRender: false }}, {at(1, inp["rate"])});\n')
                page = page.replace(b'    </div>\n    <script>', still.encode("utf-8") + b'    </div>\n    <script>', 1)
                page = page.replace(b'        window.__timelines =', sets.encode("utf-8") + b'        window.__timelines =', 1)
        # --- end G6 ---
        captions.write(reel, doc)  # layer() can add fitting notes
        for line in doc["notes"][printed_notes:]:
            print(f"note: {line}")
        assert b"\r" not in page
        (proj / "index.html").write_bytes(page)
        video = tmp / ("video.mov" if layers in ("overlay", "captions") else "video.mp4")
        hf_render(proj, video, env, f"{tier} ({w}x{h})",
                  ["--fps", inp["fps"], "--frames-cache-dir", cache, *QUALITY[tier],
                   *(["--format", "mov"] if layers in ("overlay", "captions") else [])], tier=tier)
        renders.mkdir(exist_ok=True)
        t0 = time.perf_counter()
        if layers in ("overlay", "captions"):
            rc, o, e = ffmpeg("-y", "-i", video, "-map", "0:v:0", "-an", "-c:v", "copy", partial)
        else:
            rc, o, e = ffmpeg("-y", "-i", video, "-i", audio_src, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                              "-c:a", "copy", "-movflags", "+faststart", partial)
        if rc != 0 or not partial.is_file():
            raise Stop(1, f"✗ Adding the sound stopped (exit {rc}: {tail(o + e)}); run it again.")
        print(f"info: sound added in {time.perf_counter() - t0:.1f} s")
        got = fpsmod.frame_count(partial)
        st = streams(partial)
        dur = {s.get("codec_type"): float(s.get("duration") or 0) for s in st}
        kinds = sorted(s.get("codec_type") for s in st)
        if layers in ("overlay", "captions"):
            pix = next((s.get("pix_fmt", "") for s in st if s.get("codec_type") == "video"), "")
            if got != inp["total"] or kinds != ["video"] or not alpha_pix_fmt(pix):
                raise Stop(1, f"The {layers} layer has the wrong frame count or no transparent channel; run it again.")
        elif got != inp["total"] or kinds != ["audio", "video"] or abs(dur["audio"] - dur["video"]) > 1 / float(inp["rate"]):
            raise Stop(1, f"✗ The render came out wrong ({got} frames for {inp['total']}, streams {kinds}, sound "
                          f"{dur.get('audio', 0):.3f} s against picture {dur.get('video', 0):.3f} s), so it was "
                          f"deleted; run it again.")
        os.replace(partial, final)
    finally:
        partial.unlink(missing_ok=True)
        kill_warm()
        if keep_project and proj.is_dir():
            print(f"info: render project kept at {proj}")
        elif not remove_tree(tmp):
            print("note: work/render-tmp couldn't be deleted; it's safe to delete by hand")
    label = tier.capitalize() if layers == "all" else {"aroll": "A-roll", "overlay": "Overlay", "captions": "Captions"}[layers]
    if tier == "master" and layers == "all":
        write_json(reel / OK_FILE, dict(ok, hook_text=inp["hook_text"] if hook_text is not None else None))
    print(f"✓ {label} ready: {renders.name}/{final.name}")
    return {"tier": tier, "out": f"{renders.name}/{final.name}", "frames": inp["total"], "fps": inp["fps"], "audio": None if layers in ("overlay", "captions") else audio,
            "scenes": len(inp["scened"]), "seconds": round(time.perf_counter() - t_start, 1)}


def alpha_pix_fmt(pix):
    return pix.startswith(("yuva", "gbrap", "rgba", "bgra", "argb", "abgr", "ya")) or pix in ("ayuv64le", "ayuv64be")


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
    try:
        import style_learn
        for line in style_learn.record_approval(reel):
            print(line)
    except (OSError, ValueError):
        print("I couldn't update your style's learning history; your OK is still recorded.")
    print(f"✓ OK recorded for {latest.name}; the Master can be made now.")
    return doc


# ---- selftest ------------------------------------------------------------------------------------------------
def selftest():
    import tempfile
    from unittest.mock import Mock, patch
    fails = []

    def expect(name, ok):
        if not ok:
            fails.append(name)

    with contextlib.redirect_stdout(io.StringIO()) as said:
        with patch.object(time, "monotonic", return_value=0):
            progress = RenderProgress("preview")
        for percent in range(0, 101):
            with patch.object(time, "monotonic", return_value=percent / 10):
                progress(f"Rendering frames: {percent}%")
    expect("render progress: every 10% step is printed",
           [int(re.search(r"(\d+)%", line)[1]) for line in said.getvalue().splitlines()]
           == list(range(0, 101, 10)))
    with contextlib.redirect_stdout(io.StringIO()) as said:
        with patch.object(time, "monotonic", return_value=0):
            progress = RenderProgress("master")
            progress("Rendering frames: 10%")
        with patch.object(time, "monotonic", return_value=29):
            progress()
        expect("render progress: no early heartbeat", len(said.getvalue().splitlines()) == 1)
        with patch.object(time, "monotonic", return_value=30):
            progress()
    expect("render progress: silent renderer gets a 30 second heartbeat",
           len(said.getvalue().splitlines()) == 2 and "0:30 elapsed" in said.getvalue())

    for free_mb, gpu, wanted in ((None, True, (1, 2560)), (None, False, (1, 2560)),
                                 (10_650, False, (2, 4096)), (3_000, False, (1, 2560)),
                                 (4_096, False, (2, 4096)),
                                 (11_000, True, (2, 4096)), (4_000, True, (1, 2560))):
        expect(f"master budget: {free_mb}, GPU {gpu}", master_budget(free_mb, gpu) == wanted)
    trace = "\n" + "  v8::internal::Heap::CollectGarbage\n" * 100
    for message in ("FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory",
                    "Reached heap limit", "Allocation failed"):
        cause = render_cause(message + trace)
        expect("render cause: memory failure survives the native trace",
               "ran out of memory" in cause and "close other apps first" in cause and "v8::" not in cause)
    expect("render cause: plain error", render_cause("Error: boom") == "Error: boom")
    expect("render cause: last error wins over a native trace",
           render_cause("Error: first\nerror: last" + trace) == "error: last")
    lint = ("Lint: 0 error(s), 1 warning(s)\n"
            "Continuing render despite lint issues. Use --strict to block errors.")
    native_trace = "  1: 00007FF node::errors::TriggerUncaughtException+123"
    for output, wanted in (
            (lint + "\nChrome exited unexpectedly (signal 11)", "Chrome exited unexpectedly (signal 11)"),
            ("Chrome exited unexpectedly (signal 11)\n" + native_trace + "\n" + lint,
             "Chrome exited unexpectedly (signal 11)"),
            ("FATAL ERROR: v8::ToLocalChecked Empty MaybeLocal\n" + native_trace + "\n" + lint,
             "FATAL ERROR: v8::ToLocalChecked Empty MaybeLocal"),
            ("fatal error: first\nFaTaL ErRoR: last\nError: later\n" + lint, "FaTaL ErRoR: last"),
            ("Error: Protocol error (Target closed)\n" + lint, "Error: Protocol error (Target closed)"),
            ("ERROR: first\nERROR: last\n" + native_trace + "\n" + lint, "ERROR: last"),
            ("Reached heap limit\nFATAL ERROR: later\n" + native_trace + "\n" + lint,
             "ran out of memory; close other apps first"),
            (lint, "Lint: 0 error(s), 1 warning(s) Continuing render despite lint issues. Use --strict to block errors."),
            ("", ""), ("Error: " + "x" * 400, "x" * 300)):
        expect(f"render cause: {wanted}", render_cause(output) == wanted)
    expect("render cause: unknown failure uses the old tail", render_cause("x" * 400) == "x" * 300)
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "video.mp4"
        out.write_bytes(b"fixture")
        for tier, free_mb, gpu, options in (
                ("master", 11_000, True, "--trace-warnings --max-old-space-size=512 --no-warnings"),
                ("master", 10_650, False, "--max-old-space-size 512 --trace-warnings"),
                ("master", None, False, "--trace-warnings"),
                ("master", 3_000, False, ""), ("master", 4_096, False, ""),
                ("master", None, True, '"--max-old-space-size=512" --trace-warnings'),
                ("master", 4_000, True, ""), ("preview", 11_000, True, "--max-old-space-size=512"),
                (None, 11_000, True, "--trace-warnings")):
            env = {"NODE_OPTIONS": options, "KEEP": "unchanged"}
            extra = ["--fps", "30/1"]
            with patch.dict(globals(), lint_or_stop=lambda *args: (True, []), kill_warm=lambda: None), \
                    patch.object(rt, "hyperframes_cmd", side_effect=lambda *args: list(args)), \
                    patch.object(rt, "has_nvidia_gpu", return_value=gpu) as gpu_read, \
                    patch.dict(globals(), free_ram_mb=lambda: free_mb), \
                    patch.dict(globals(), run=Mock(return_value=(0, "", ""))) as patched, \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                hf_render(Path(t), out, env, "fixture", extra, tier=tier)
                cmd, used_env = patched["run"].call_args.args
            expect("master budget: caller's environment and arguments stay unchanged",
                   env == {"NODE_OPTIONS": options, "KEEP": "unchanged"} and extra == ["--fps", "30/1"])
            if tier == "master":
                workers, heap_mb = master_budget(free_mb, gpu)
                expect("master budget: explicit workers and heap reach HyperFrames",
                       cmd[cmd.index("--workers") + 1] == str(workers)
                       and used_env is not env and used_env["KEEP"] == "unchanged"
                       and used_env["NODE_OPTIONS"].count("--max-old-space-size") == 1
                       and f"--max-old-space-size={heap_mb}" in used_env["NODE_OPTIONS"]
                       and "512" not in used_env["NODE_OPTIONS"] and gpu_read.call_count == 1
                       and said.getvalue().count("info: master render:") == 1)
                expect("master budget: unrelated Node options survive",
                       all(flag in used_env["NODE_OPTIONS"] for flag in ("--trace-warnings", "--no-warnings")
                           if flag in options))
            else:
                expect("master budget: previews and scenes keep their environment and worker choice",
                       used_env is env and "--workers" not in cmd and not gpu_read.called
                       and "info: master render:" not in said.getvalue())

    with tempfile.TemporaryDirectory() as t:
        reel = Path(t)
        block = dict(check="fixture", level="block", msg="Fix the fixture.", module="fixture")
        warn = dict(check="fixture", level="warn", msg="Check the fixture.", module="fixture")
        for rows in ([warn, block], [warn], []):
            rendered = Mock(return_value={"rendered": True})
            with patch.object(qa_check, "run_checks", return_value=rows) as checks, \
                    patch.dict(globals(), render=rendered), \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                code = main(["master", "--reel-dir", str(reel)])
            output = said.getvalue()
            if block in rows:
                expect("QA: a block stops master before rendering with the next step",
                       code == 1 and "✗ The QA check blocks the final: Fix the fixture." in output
                       and "Fix what it names, run the QA check again, then make the final." in output
                       and not rendered.called)
            else:
                expect("QA: warnings and all-clear allow master to render", code == 0 and rendered.call_count == 1)
            expect("QA: master runs the pre checks in process", checks.call_count == 1
                   and checks.call_args.args[1] == "pre" and checks.call_args.args[0]["reel_dir"] == reel.resolve())
            report_path = reel / "work/qa.json"
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
            expect("QA: master saves the standard report with all rows and LF endings",
                   report.get("phase") == "pre" and report.get("blocks") == int(block in rows)
                   and report.get("warns") == int(warn in rows) and report.get("render") is None
                   and bool(report.get("ran_at")) and report.get("checks") == (rows or [dict(
                       check="all-clear", level="pass", msg="Every check passed.", module="check")])
                   and b"\r" not in report_path.read_bytes())

    spec = {"params": {"accent": {"default": "#4f8cff"}, "font": {"default": "Inter"}}}
    face = '@font-face {font-family: "Inter"; src: url("./fonts/Inter-Regular.woff2");}'
    saved = {"accent": "#E0218A", "font": "Inter"}
    expect("brand: saved accent and licensed Inter apply",
           brand_params(spec, face, {}, saved) == (saved, []))
    beat_params = {"accent": "#123abc", "font": "Scene Font"}
    expect("brand: beat accent and font win",
           brand_params(spec, face, beat_params, saved)[0] == beat_params)
    params, notes = brand_params(spec, face, {}, {"font": "Comic Sans MS"})
    expect("brand: unlicensed font falls back with the plain note",
           params == {} and notes == ["Your brand font Comic Sans MS isn't available for on-screen graphics yet, "
                                     "so they use Inter."])
    for accent in ("magenta", "#123", "#E0218A\n", None, [], 123):
        params, notes = brand_params(spec, face, {}, {"accent": accent})
        expect(f"brand: malformed accent {accent!r} is ignored with a note", params == {} and bool(notes))
    for font in (None, [], 123, "", "   "):
        params, notes = brand_params(spec, face, {}, {"font": font})
        expect(f"brand: malformed font {font!r} is ignored with a note", params == {} and bool(notes))
    expect("brand: undeclared keys never added", brand_params({"params": {}}, face, {}, saved) == ({}, []))
    expect("brand: no saved brand preserves beat params", brand_params(spec, face, beat_params, {}) == (beat_params, []))
    expect("brand: inputs stay unchanged", saved == {"accent": "#E0218A", "font": "Inter"}
           and beat_params == {"accent": "#123abc", "font": "Scene Font"})

    for rate in (Fraction(25), Fraction(30000, 1001), Fraction(24000, 1001)):
        expect(f"style times at {rate}: never after the frame, on the frame",
               all(Fraction(at(f, rate)) <= f / rate and round(float(at(f, rate)) * rate) == f for f in range(0, 5000, 7)))
    want = {"split": [0, 960, 1080, 960], "stack": [0, 0, 1080, 844], "pip": [738, 28, 312, 555],
            "overlay": [0, 0, 1080, 1920], "full": [0, 0, 1080, 1920]}
    expect("layout boxes on the 1080x1920 grid", all(layout(n, 1)["box"] == b for n, b in want.items()))
    expect("split's plate is the top half, at 720 wide too",
           "top: 0px; width: 720px; height: 640px; background: #0a0c12" in layout("split", 720 / 1080)["plate"]
           and layout("split", 720 / 1080)["box"] == [0, 640, 720, 640])
    expect("only pip's box paints above the plates", [n for n in want if layout(n, 1)["z"] > PLATE_Z] == ["pip"])
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
    br = beat("br", 40, 70)
    br["broll"] = {"src": "broll/ingested/own.mp4", "in": 6, "out": 36, "fit": "cover", "ledger_id": "f01"}
    sp = build_spans([br], {}, 0)
    expect("broll emits one span and crosses cuts", sp == [{"layer": "broll", "start_f": 40, "end_f": 70, "id": "br"}]
           and effect_gate.check(sp, [50], "25/1", 100) == [])
    expect("broll overlap blocks", any("overlaps broll" in p for p in effect_gate.check(
        sp + [{"layer": "broll", "start_f": 69, "end_f": 80}], [50], "25/1", 100)))
    expect("broll touching passes", effect_gate.check(
        sp + [{"layer": "broll", "start_f": 70, "end_f": 80}], [50], "25/1", 100) == [])
    sp = build_spans([beat("b1", 0, 50), beat("ov", 40, 70, "overlay", "hook-title"),
                      beat("b2", 50, 100, scene="cta-end-card")], kinds, 40)
    expect("gate blocks two takeovers at once", any("overlaps takeover" in p for p in effect_gate.check(sp, [50], "25/1", 100)))
    sp = build_spans([beat("b1", 0, 50), beat("b2", 50, 100)], kinds, 50,
                     [{"layer": "aroll_transform", "start_f": 48, "end_f": 52, "id": "move"}])
    expect("extra spans join the gate", any("runs across the cut" in p for p in effect_gate.check(sp, [50], "25/1", 100)))
    for sid, slots, opens, keyed in (("hook-title", {"kicker": "Part 1", "title": "Hi"}, True, True),
                                     ("hook-title", {"kicker": "Part 1", "title": "Hi"}, True, False),
                                     ("hf-hook-title", {"title": "Hi"}, True, True),
                                     ("hf-hook-title", {"title": "Hi"}, True, False),
                                     ("lower-third", {"name": "Alex", "title": "Founder"}, False, True)):
        b0 = beat("b1", 0, 50, scene=sid)
        b0["scene"]["slots"], b0["scene"]["params"] = slots, ({"entrance": "fade"} if opens else {})
        if not keyed:
            del b0["scene"]["params"]
        inp = {"beats": [b0, beat("b2", 50, 100)], "rate": Fraction(25), "words": [], "total": 100,
               "cut_frames": [50], "fps": "25/1"}
        with tempfile.TemporaryDirectory() as home, patch.object(rt, "state_dir", return_value=Path(home)), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            plan(inp, None)
        expect(f"beat-0 {sid}{'' if keyed else ' (no params key)'}: entrance none only when the scene has it, the warning only when it hasn't, no hook",
               b0["scene"].get("params", {}).get("entrance") == ("none" if opens else None)
               and ("note: the first beat has a scene" in said.getvalue()) != opens and inp["hook_f"] == 0)
    import placer
    spoken_words = [{"word": word, "start": i / 10, "end": (i + 1) / 10}
                    for i, word in enumerate(("Claude", "just", "killed", "Instagram.", "Today"))]
    for word_end, beat_end, expected in ((.4, 200, 38), (2.4, 200, 60), (8, 200, 125),
                                         (.4, 20, 20), (8, 60, 60)):
        first = beat("spoken", 0, beat_end)
        first["speech_anchor"]["text"] = "Claude just killed Instagram."
        timed = [dict(w) for w in spoken_words]
        timed[3]["end"] = word_end
        opening = {"beats": [first], "rate": Fraction(25), "words": [w["word"] for w in timed],
                   "timed_words": timed, "total": beat_end, "cut_frames": [], "fps": "25/1"}
        with contextlib.redirect_stdout(io.StringIO()):
            plan(opening, "CLAUDE, just killed Instagram!")
        expect(f"spoken hook: word-end timing and clamps ({word_end}, {beat_end})",
               opening["hook_spoken"] and opening["hook_f"] == expected)
    first["end_f"] = 200
    short_beat = beat("short-opening", 0, 24)
    short_hook = plain_hook("Claude just killed Instagram.", short_beat, Fraction(30), spoken_words, 600)
    expect("spoken hook: 0.8-second first beat in a 20-second reel still shows for 1.5 seconds",
           short_hook["end_f"] == 45)
    different = plain_hook("Watch this before you post", first, Fraction(25), spoken_words, 200)
    expect("different-text hook: keeps today's end", not different["spoken"] and different["end_f"] == 125)
    expect("hook lines: average Inter advances keep the different-text hook to two lines",
           title_lines("Watch this before you post", 840, 72) == 2)
    matching = plain_hook("Claude just killed Instagram.", first, Fraction(25), spoken_words, 200)
    chunks = [{"i": i, "w0": a, "w1": b, "start_f": start, "end_f": start + 10,
               "text": " ".join(w["word"] for w in spoken_words[a:b + 1]),
               "words": [{"w": w, "text": spoken_words[w]["word"], "start_f": start,
                          "mark": None, "punch": False} for w in range(a, b + 1)]}
              for i, (a, b, start) in enumerate(((0, 1, 0), (2, 4, 5), (0, 0, 38)))]
    doc = {"chunks": [dict(c) for c in chunks]}
    with contextlib.redirect_stdout(io.StringIO()) as said:
        skipped = hook_captions(doc, [matching])
    expect("spoken hook: drops only all-hook chunks before its end, keeps mixed and later chunks",
           skipped == 1 and [c["w1"] for c in doc["chunks"]] == [4, 0]
           and [c["i"] for c in doc["chunks"]] == [0, 1]
           and hook_shown_positions(doc["hooks"], spoken_words) == {0, 1}
           and "info: 1 captions are shown by the hook title instead" in said.getvalue())
    doc = {"chunks": [dict(c) for c in chunks]}
    with contextlib.redirect_stdout(io.StringIO()):
        skipped = hook_captions(doc, [different])
    expect("different-text hook: keeps every caption", skipped == 0 and len(doc["chunks"]) == 3)
    head = (200, 650, 880, 1250)
    ctx = {"track": {"total_f": 100, "keys": [{"f": 0}], "tweens": []},
           "segments": [(0, 100)], "boxes": {0: head}, "median_box": head,
           "layouts": {"full": (0, 0, 1080, 1920)}, "stills": [], "notes": [], "fps": Fraction(25)}
    title_beat = beat("title", 0, 50, scene="hf-hook-title")
    title_beat["scene"]["slots"] = {"title": "Nobody tells you this about editing"}
    placed, note = hook_title_placement(ctx, title_beat)
    expect("hook title: shrinks and stays wholly above the head with a gap",
           placed["top"] >= 220 and placed["top"] + placed["height"] <= 1470
           and placed["top"] + placed["height"] <= 610
           and 56 <= placed["size"] < 120 and note is None)
    title_beat["start_f"] = 50
    title_beat["end_f"] = 100
    later, _ = hook_title_placement(ctx, title_beat)
    expect("hook title: later beats also clear the face", later == placed)
    ctx["boxes"][0] = ctx["median_box"] = (200, 1320, 880, 1500)
    title_beat["scene"]["slots"]["title"] = "W" * 40
    tilted, note = hook_title_placement(ctx, title_beat)
    expect("hook title: perspective expansion of a tall title also clears the face",
           tilted["top"] + tilted["height"] <= 1320 and tilted["size"] < 120 and note is None)
    title_beat["scene"]["slots"]["title"] = "Nobody tells you this about editing"
    ctx["boxes"][0] = ctx["median_box"] = head
    title_beat["scene"]["params"] = {"top": 250, "height": 350, "size": 56}
    explicit, _ = hook_title_placement(ctx, title_beat)
    expect("hook title: safe explicit placement wins", explicit == {"top": 250, "height": 350, "size": 56})
    title_beat["scene"]["params"] = {}
    ctx["boxes"][0] = ctx["median_box"] = (0, 384, 1080, 1920)
    tight, note = hook_title_placement(ctx, title_beat)
    expect("hook title: impossible fit asks for a plain replacement",
           tight is None and note == "The hook title didn't fit above your face, so a plain hook title is used.")
    mouth = (200, 1400, 880, 1450)
    expect("hook title: protected top 75% includes the mouth beyond 60%",
           placer.hits(mouth, placer.face_band(ctx["median_box"], top=0)))
    title_beat["start_f"], title_beat["end_f"] = 0, 50
    title_beat["scene"]["slots"]["title"] = "Hi"
    ctx["boxes"][0] = ctx["median_box"] = (0, 220, 1080, 1920)
    fallback = {"beats": [title_beat], "scened": [title_beat], "hooks": [], "rate": Fraction(25),
                "words": ["Hi"], "timed_words": [{"word": "Hi", "start": 0, "end": .2}], "total": 100}
    notes = place_hook_titles(fallback, ctx)
    expect("hook title: unfit scene becomes the same plain spoken hook",
           title_beat["scene"] is None and fallback["scened"] == []
           and fallback["hook_text"] == "Hi" and fallback["hook_spoken"] and fallback["hook_f"] == 38
           and notes == ["The hook title didn't fit above your face, so a plain hook title is used."])
    # The checker's fitted-title probe must survive the same still setup as render().
    fitted_beat = beat("fitted", 0, 50, scene="hf-hook-title")
    fitted_beat["scene"]["slots"] = {"title": "Claude just killed Instagram."}
    head = (200, 700, 880, 1450)
    fitted_ctx = dict(ctx, boxes={0: head}, median_box=head, stills=[], notes=[])
    fitted = {"beats": [fitted_beat], "hooks": [], "rate": Fraction(25), "words": [], "total": 100}
    place_hook_titles(fitted, fitted_ctx)
    expect("fitted title: checker geometry", fitted_beat["scene"]["params"] == {
        "top": 220, "height": 440, "size": 93})
    placer.set_hook_stills(fitted_ctx, placement_hooks(fitted))
    fitted_box = hook_record(fitted)["box"]
    caption_box = placer.place(fitted_ctx, 0, 49)
    expect("fitted title: caption clears the scene text box and face band",
           placer.active_hook(fitted_ctx, 0) is not None and not placer.hits(caption_box, fitted_box)
           and not placer.hits(caption_box, placer.face_band(head), placer.CAPTION_PAD))
    expect("fitted title: exclusive scene end restores base placement", placer.active_hook(fitted_ctx, 50) is None)
    gated_beat = beat("gated-title", 0, 50, scene="hf-hook-title")
    gated_beat["scene"]["slots"] = {"title": "Hi"}
    gated = {"beats": [gated_beat], "rate": Fraction(25), "words": ["Hi"], "total": 100,
             "cut_frames": [], "fps": "25/1"}
    with patch.object(effect_gate, "check", wraps=effect_gate.check) as checked, \
            contextlib.redirect_stdout(io.StringIO()):
        plan(gated, None, ctx=ctx)
    expect("gate: fallback is checked as its rendered plain overlay",
           gated_beat["scene"] is None and checked.call_count == 1
           and checked.call_args.args[0] == [dict(layer="overlay", start_f=0, end_f=50, id="hook title")])
    scene_beat = beat("record-scene", 0, 50, scene="hf-hook-title")
    scene_beat["scene"].update(slots={"title": "Hi"}, params={"top": 220, "height": 390, "size": 64})
    records = [("plain", hook_record({"hooks": [different], "beats": []})),
               ("scene", hook_record({"hooks": [], "beats": [scene_beat]})),
               ("fallback", hook_record(fallback)),
               ("none", hook_record({"hooks": [], "beats": []}))]
    with tempfile.TemporaryDirectory() as home:
        record_path = Path(home) / "work/hook.json"
        for name, record in records:
            with patch.object(os, "replace", wraps=os.replace) as replaced:
                write_json(record_path, record)
            data = record_path.read_bytes()
            expect(f"hook record: {name} is written atomically as UTF-8 with LF",
                   json.loads(data.decode("utf-8")) == record and data.endswith(b"\n") and b"\r" not in data
                   and replaced.call_count == 1 and not record_path.with_name("hook.json.tmp").exists())
            expect(f"hook record: {name} describes the render",
                   record["schema"] == 1 and record["start_f"] == 0
                   and record["kind"] == ("plain" if name == "fallback" else name))
        expect("hook record: different text stores the exact still envelope and no spoken coverage",
               records[0][1]["box"] == [90, 280, 930, 445.6]
               and records[0][1]["end_f"] == 125 and not records[0][1]["spoken"]
               and records[0][1]["words_shown"] == 0)
        expect("hook record: a scene stores its fitted box and lifetime",
               records[1][1]["box"] == [60, 220, 960, 610] and records[1][1]["end_f"] == 50)
        write_json(record_path, records[1][1])
        saved_scene = saved_hooks(Path(home))
        expect("hook record: QA restores the exact scene box without claiming spoken coverage",
               len(saved_scene) == 1 and saved_scene[0]["box"] == [60, 220, 960, 610]
               and saved_scene[0]["end_f"] == 50 and not saved_scene[0]["spoken"]
               and saved_scene[0]["shown_words"] == [])
        expect("hook record: fallback preserves spoken words and duration",
               records[2][1]["spoken"] and records[2][1]["words_shown"] == 1
               and records[2][1]["end_f"] == 38)
    title_beat["scene"] = {"id": "hf-hook-title", "slots": {"title": "Hi"}, "params": {}}
    title_beat["start_f"], title_beat["end_f"] = 50, 100
    later_fallback = {"beats": [title_beat], "scened": [title_beat], "hooks": [],
                      "rate": Fraction(25), "words": ["Hi"], "total": 100}
    place_hook_titles(later_fallback, ctx)
    expect("hook title: a later replacement stays on its beat",
           later_fallback["scened"] == [] and later_fallback["hooks"][0]["start_f"] == 50
           and later_fallback["hooks"][0]["end_f"] == 100 and not later_fallback["hooks"][0]["spoken"])
    title_beat["scene"] = {"id": "hf-hook-title", "slots": {"title": "Hi"}, "params": {}}
    ctx["median_box"] = None
    unchecked, note = hook_title_placement(ctx, title_beat)
    expect("hook title: missing anchors keep defaults with a face-check note",
           unchecked == {"top": 220, "height": 1250, "size": 120}
           and note is not None and "wasn't checked against your face" in note)
    for w, h in TIERS.values():
        x, y, bw, size = hook_box(w, h)
        expect(f"hook box inside the safe zone at {w}x{h}",
               not _ig.violations("hook", x - bw / 2, y, bw, size * 1.15 * 3, w, h))
    with tempfile.TemporaryDirectory() as t:
        r = Path(t)
        state = r / "state"
        with patch.object(rt, "state_dir", return_value=state):
            expect("brand: missing saved style is empty", saved_brand(r) == {})
            path = state / "styles/default.json"
            write_json(path, {**saved, "caption_style": {"style": "clean"}})
            expect("brand: an unpicked reel does not use the default", saved_brand(r) == {})
            saved_style.pick(r, "default")
            expect("brand: only brand keys are loaded", saved_brand(r) == saved)
            for data in (b"{", b"[]", b"\xff"):
                path.write_bytes(data)
                with contextlib.redirect_stdout(io.StringIO()) as said:
                    got = saved_brand(r)
                expect("brand: unreadable style is a note, never a stop", got == {} and "note: " in said.getvalue())
            write_json(path, {"accent": "#E0218A", "font": "Comic Sans MS"})
            first = beat("brand-first", 0, 50, scene="hook-title")
            first["scene"].update(slots={"kicker": "Part 1", "title": "Hi"}, params={"accent": "#123abc"})
            second = beat("brand-second", 50, 100, scene="lower-third")
            second["scene"]["slots"] = {"name": "Alex", "title": "Founder"}
            branded = {"beats": [first, second], "rate": Fraction(25), "words": [], "total": 100,
                       "cut_frames": [50], "fps": "25/1", "style_reel": r}
            with contextlib.redirect_stdout(io.StringIO()) as said:
                plan(branded, None)
            expect("brand: plan applies before fill checks, keeps beat override and entrance none",
                   first["scene"]["params"] == {"accent": "#123abc", "entrance": "none"}
                   and second["scene"]["params"] == {"accent": "#E0218A"})
            expect("brand: plan prints each distinct font note once",
                   said.getvalue().count("note: Your brand font Comic Sans MS") == 1)
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
        later_hook = dict(text="Later hook", start_f=50, end_f=100)
        replacement_page = main_html(dict(inp, hooks=[later_hook], hook_f=0), 720, 1280, [])
        expect("page: later plain replacements are hidden before their beat and end with it",
               'id="hook-0" class="plain-hook" style="opacity: 0; visibility: hidden"' in replacement_page
               and 'tl.set("#hook-0", { xPercent: -50, autoAlpha: 1, immediateRender: false }, 2);' in replacement_page
               and 'tl.set("#hook-0", { autoAlpha: 0, immediateRender: false }, 4);' in replacement_page)
        br["broll"]["fit"] = "blur-fill"
        bpage = main_html(dict(inp, beats=[br]), 720, 1280, [(beat("scene", 50, 100), "scene")])
        expect("broll page: two muted videos with ids, own copies, one offset, tracks distinct from scenes",
               bpage.count('src="media/broll-br-0.mp4"') == 1 and bpage.count('src="media/broll-br-0-back.mp4"') == 1
               and 'id="broll-br-0"' in bpage and 'id="broll-br-0-back"' in bpage and bpage.count('data-media-start="0.24"') == 2
               and 'data-track-index="2" muted' in bpage and 'data-track-index="3" muted' in bpage
               and 'class="clip broll-front"' in bpage and 'z-index: 200' in bpage)
        expect("page: underlay from frame 0 is opaque at 0", 'tl.set("#underlay-0", { opacity: 1, immediateRender: true }, 0)'
               in page)
        expect("page: caption CSS field is empty without captions",
               "{{CAPTION_CSS}}" not in page and "#captions" not in page and "\n\n    </style>" in page)
        doc = {"style": {"style": "clean", "accent": "#FFD84D"}, "notes": [], "chunks": [
            {"i": i, "start_f": a, "end_f": e, "text": "Caption", "box": [100, 1400, 900, 1600],
             "words": [{"w": i, "text": "Caption", "start_f": a, "mark": None, "punch": False}]}
            for i, (a, e) in enumerate(((5, 25), (40, 60)))]}
        cap_page = main_html(dict(inp, captions=doc), 720, 1280, [])
        expect("page: captions sit at 600 and fill their CSS", 'id="captions" style="z-index: 600"' in cap_page
               and "#captions .caption" in cap_page and "{{CAPTION_CSS}}" not in cap_page)
        for c in doc["chunks"]:
            expect(f"page: caption {c['i']} centres and hard-kills on its end frame",
                   f'tl.set("#cap-{c["i"]}", {{xPercent: -50, autoAlpha: 0, immediateRender: true}}, 0);' in cap_page
                   and f'tl.set("#cap-{c["i"]}", {{autoAlpha: 0}}, {at(c["end_f"], inp["rate"])});' in cap_page)
        expect("page: captions use the root timeline only", "@keyframes" not in cap_page and "translateX" not in cap_page)
        aroll_page = main_html(dict(inp, captions=doc), 720, 1280, [(beat("scene", 50, 100), "scene")], layers="aroll")
        overlay_page = main_html(dict(inp, captions=doc), 720, 1280, [], layers="overlay")
        captions_page = main_html(dict(inp, captions=doc), 720, 1280, [(beat("scene", 50, 100), "scene")], layers="captions")
        expect("layers: captions alone on transparency", 'id="captions"' in captions_page and 'id="aroll-box"' not in captions_page
               and 'id="scene-' not in captions_page and '"#aroll-box"' not in captions_page and "background: transparent;" in captions_page)
        expect("layers: overlay excludes captions", "#captions" not in overlay_page and 'id="captions"' not in overlay_page)
        expect("layers: a-roll alone", 'id="aroll-box"' in aroll_page and "#captions" not in aroll_page
               and 'id="scene-' not in aroll_page and 'id="underlay-' not in aroll_page)
        expect("layers: transparent overlay without a-roll", 'id="aroll-box"' not in overlay_page
               and '"#aroll-box"' not in overlay_page and "background: transparent;" in overlay_page)
        expect("layers: all preserves the default page", cap_page == main_html(dict(inp, captions=doc), 720, 1280, [], layers="all"))
        fallback = {"keys": [{"f": f, "layout": name} for f, name in ((0, "full"), (20, "pip"), (30, "pip"), (50, "full"))],
                    "tweens": [{"prop": "layout", "from": "full", "to": "pip", "start_f": 15, "end_f": 20},
                               {"prop": "layout", "from": "pip", "to": "full", "start_f": 45, "end_f": 55}],
                    "style": {"style": "layout-switch"}}
        fallback_beats = [beat("plain", 0, 60), beat("glass", 60, 75, "overlay"), beat("plain-end", 75, 100)]
        expect("layers: pip moves and blurred-card frames become two finished-picture spans",
               baked_spans(fallback, fallback_beats, 100) == [
                   {"start_f": 15, "end_f": 55, "layout": "pip"}, {"start_f": 60, "end_f": 75, "layout": "overlay"}])
        expect("layers: touching spans merge with both layout names",
               baked_spans({"keys": [{"f": 0, "layout": "pip"}, {"f": 25, "layout": "full"}],
                            "tweens": [], "style": {"style": "layout-switch"}},
                           [beat("glass", 25, 50, "overlay")], 50) == [{"start_f": 0, "end_f": 50, "layout": "overlay+pip"}])
        expect("layers: full, split, stack and overlays without a blurred card need no finished picture",
               all(baked_spans({"keys": [{"f": 0, "layout": name}], "tweens": []}, [], 100) == []
                   for name in ("full", "split", "stack"))
               and baked_spans({"keys": [{"f": 0, "layout": "full"}], "tweens": [], "style": {"style": "punch-in"}},
                               [beat("plain-overlay", 0, 100, "overlay")], 100) == [])
        # --- G5 transitions (VES-1) ---
        whip = dict(beat("whip", 0, 100), transition={"type": "whip", "at_cut_frame": 60, "dur_frames": 3})
        expect("layers: a moving cut transition uses the finished picture",
               baked_spans({}, [whip], 100) == [{"start_f": 57, "end_f": 63, "layout": "transition"}])
        expect("layers: flash and fade stay in the overlay layer",
               baked_spans({}, [dict(whip, transition=dict(whip["transition"], type="flash")),
                                dict(beat("fade", 0, 100, "overlay"), transition={
                                    "type": "fade", "at_cut_frame": None, "dur_frames": 3, "edge": "both"})], 100) == [])
        expect("layers: a transition touching pip merges with both names",
               baked_spans({"keys": [{"f": 0, "layout": "pip"}, {"f": 57, "layout": "full"}]},
                           [whip], 100) == [{"start_f": 0, "end_f": 63, "layout": "pip+transition"}])
        # --- end G5 ---
        masked = main_html(dict(inp, track=fallback, beats=fallback_beats), 720, 1280, [], layers="overlay")
        expect("layers: the overlay hides and restores on each finished-picture boundary",
               'id="handoff-overlay"' in masked and all(
                   f'tl.set("#handoff-overlay", {{ opacity: {opacity}, immediateRender: false }}, {at(frame, inp["rate"])});' in masked
                   for frame, opacity in ((15, 0), (55, 1), (60, 0), (75, 1))))
        masked_all = main_html(dict(inp, track={"keys": [{"f": 0, "layout": "pip"}], "tweens": [], "style": {}}),
                               720, 1280, [], layers="overlay")
        expect("layers: a finished-picture span can cover frame zero through the exclusive end",
               'tl.set("#handoff-overlay", { opacity: 0, immediateRender: true }, 0);' in masked_all
               and f'tl.set("#handoff-overlay", {{ opacity: 1, immediateRender: false }}, {at(inp["total"], inp["rate"])});' in masked_all)
        trk = {"style": {"style": "layout-switch"},
               "keys": [{"f": 0, "scale": 1.0, "ox": 0.5, "oy": 0.38, "layout": "full"},
                        {"f": 50, "scale": 1.0, "ox": 0.5, "oy": 0.38, "layout": "pip"}],
               "tweens": [{"start_f": 60, "end_f": 75, "prop": "layout", "from": "pip", "to": "split",
                           "ease": "power2.inOut", "id": "layout b3"}]}
        sb = [beat("b1", 0, 50), beat("b2", 50, 60, "pip"), beat("b3", 60, 100, "split")]
        page = main_html(dict(inp, track=trk, beats=sb), 720, 1280, [])
        pip = 'x: 492, y: 18.67, width: 208, height: 370, borderRadius: 9.33'
        expect("page: the layout is set hard on the cut frame, the move is one fromTo of whole frames",
               f'tl.set("#aroll-box", {{ {pip}, zIndex: 500' in page
               and page.split(f'tl.set("#aroll-box", {{ {pip}')[1].split("\n")[0].endswith(", 2);")
               and f'tl.fromTo("#aroll-box", {{ {pip} }}, {{ x: 0, y: 640, width: 720, height: 640, borderRadius: 0, '
                   f'duration: 0.6, ease: "power2.inOut", immediateRender: false }}, 2.4);' in page)
        expect("page: no move tweens left/top (they snap to whole pixels; lint gsap_non_transform_motion)",
               not any(("left:" in l or "top:" in l) for l in page.splitlines() if "tl.fromTo(" in l or "tl.to(" in l))
        expect("page: the video element is never animated; one plate per non-full beat",
               '"#aroll"' not in page and page.count('class="layout-card"') == 2 and 'id="plate-1"' in page)
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        scenes = root / "scenes"
        shutil.copytree(scene_check.SCENES / "callout", scenes / "callout")
        spec_path = scenes / "callout" / "scene.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["category"] = "3d"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        three = root / "runtime" / "three"
        three.mkdir(parents=True)
        for name in ("three.module.js", "three.core.js"):
            (three / name).write_bytes(f"// {name}\n".encode("utf-8"))
        b = beat("three", 0, 50, scene="callout")
        with patch.object(scene_check, "SCENES", scenes), patch.dict(globals(), THREE_RUNTIME=three):
            expect("3d: scene video starts in the 3D band", scene_z(b, 7) == 307)
            expect("3d: the composition uses the 3D layer for its scene video",
                   '<div class="band" style="z-index: 300"><video id="scene-three"' in main_html(
                       {"rate": Fraction(25), "total": 50, "under": [], "hook_f": 0}, 720, 1280, [(b, "three")]))
            expect("3d: last 3D layer stays below 400", scene_z(b, 99) == 399)
            try:
                scene_z(b, 100)
                expect("3d: too many scenes stop", False)
            except Stop as s:
                expect("3d: too many scenes stop", s.code == 1 and "3D layer" in s.lines[0])
            scene_project(root / "project", b, Fraction(25))
            expect("3d: the project copies both engine files",
                   all((root / "project" / "vendor" / name).read_bytes() == (three / name).read_bytes()
                       for name in ("three.module.js", "three.core.js")))
            with patch.dict(globals(), THREE_RUNTIME=root / "missing"):
                try:
                    scene_project(root / "missing-project", b, Fraction(25))
                    expect("3d: missing runtime stops", False)
                except Stop as s:
                    expect("3d: missing runtime stops with a plain line", s.code == 1 and s.lines == (
                        "The 3D engine files are missing, reinstall the editor.",))
            spec["category"] = "callout"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            expect("3d: 2d scenes keep their layer", scene_z(b, 7) == 408)
            with patch.dict(globals(), THREE_RUNTIME=root / "missing"):
                scene_project(root / "2d-project", b, Fraction(25))
            expect("3d: 2d projects do not need the engine",
                   not (root / "2d-project" / "vendor" / "three.module.js").exists())
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
        p.add_argument("--keep-project", action="store_true", help="keep the render project for inspection")
    p = sub.add_parser("layers", help="render the approved a-roll, transparent overlay and captions for an editor")
    p.add_argument("--reel-dir", required=True)
    p.add_argument("--which", choices=("aroll", "overlay", "captions", "all"), default="all")
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
        if a.cmd == "master":
            try:
                ctx = qa_check.build_context(reel)
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                findings = [dict(check="inputs-unreadable", level="block",
                                 msg="The cut list or Beat Map could not be read. Restore these files and run QA again.",
                                 where="work/cuts.json, beat-map-selection.json", module="check")]
            else:
                findings = qa_check.run_checks(ctx, "pre")
            if not findings:
                findings = [dict(check="all-clear", level="pass", msg="Every check passed.", module="check")]
            blocks = [row for row in findings if row["level"] == "block"]
            qa_check.write_report(reel, dict(
                phase="pre", ran_at=datetime.now().astimezone().isoformat(), render=None,
                blocks=len(blocks), warns=sum(row["level"] == "warn" for row in findings), checks=findings))
            if blocks:
                print(f"✗ The QA check blocks the final: {blocks[0]['msg']}")
                print("Fix what it names, run the QA check again, then make the final.")
                return 1
        if a.cmd == "layers":
            summary = [render(reel, "master", None, layers=which)
                       for which in (("aroll", "overlay", "captions") if a.which == "all" else (a.which,))]
            print(json.dumps(summary, ensure_ascii=False))
            return 0
        summary = cmd_ok(reel, a.from_review) if a.cmd == "ok" else render(
            reel, a.cmd, a.hook_text, keep_project=a.keep_project)
    except Stop as s:
        if a.cmd == "layers":
            print(" ".join(s.lines))
            return s.code
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
