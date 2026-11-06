#!/usr/bin/env python3
"""S6b render engine check: compose.py (preview, OK, Master) on synthetic reels and a real take.

usage (one case per call; the render cases under the heavy lock; EDITOR_SE_HOME = a state folder with ffmpeg,
node, chrome and hyperframes installed; run with that state's Python):
  python -I "<heavy_lock.py>" --wait 600 -- <editor python> -X utf8 -I tests/editor/render_engine_test.py --case <name>
    [--take <a real talking-head take>] [--out <folder for kept outputs>]
cases: selftest, preview, master-refused, master, gate-block, bad-input, joi-frames, colour, frame0, frame0-scene,
cut-span-block, scene-no-params, lint, audio, licence, master-older, hook-limits, hub-review, ask, style-cut, style-143, layout-cut,
layout-move, split-top, pip-above, style-fps, rvm-info (default: all, in that order)
joi-frames and rvm-info need a real take: --take or env EDITOR_SE_TEST_TAKE (read only, never copied into the repo).
rvm-info is information only (it never fails the run). frame0 and frame0-scene keep their frame-0 PNGs in --out
(default: render-out next to the fixtures).
Fixtures live in a temp folder next to the state folder (EDITOR_SE_HOME's parent; --tmp to override) and are
deleted at the end, also on failure: a reel with a 4 s 1080x1920 25 fps test pattern + 1 kHz tone cut master
(render.py's encode settings), a 2-segment work/cuts.json (one interior cut at frame 50), a cut word list and a
Beat Map Send (beat 1 full 0-50, beat 2 full 50-100 with a lower-third scene) whose edit_style is the identity
(punch-in at 1.0, no moves), so those cases render exactly as before the editing styles. Some cases swap the picture
(a flat known-colour patch, a static dark frame) or drop the scene. The S6c cases (style-cut ... style-fps) use a 6 s
3-segment reel (cuts at 50 and 100) with a real edit_style; ask has no style anywhere.
Prints PASS/FAIL per check; exit 0 only if all pass. Refuses to start below 10 GB free disk.
"""
import argparse, contextlib, hashlib, http.client, importlib.util, io, json, math, os, re, shutil, socket, subprocess, sys
import tempfile, threading, time
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "editor-superengine"
SCRIPTS = PLUGIN / "skills" / "reel-canvas-build" / "scripts"
FIRST_CUTS = PLUGIN / "skills" / "reel-first-cuts" / "scripts"
DOCTOR = PLUGIN / "skills" / "editor-doctor" / "scripts"
COMPOSE = SCRIPTS / "compose.py"
FIXTURES = HERE / "fixtures"
CLICK = HERE / "boards_click.js"
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
import runtime as rt  # noqa: E402

REEL = "demo-reel"
MASTER_RE = re.compile(r"^.+ master - \d{2}\.\d{2}\.\d{2}\.mp4$", re.I)  # hooks/mod/logic.ts MASTER
WORDS = [("Three", 0.10), ("edits", 0.46), ("that", 0.82), ("save", 1.18), ("hours", 1.54),
         ("Meet", 2.10), ("Alex", 2.60), ("today", 3.10)]
HOOK = "Three edits that save hours"
MIN_FREE_GB = 10
TESTSRC = "testsrc2=size=1080x1920:rate=25:duration=4"
PATCH_RGB = (200, 60, 40)
PATCH = (360, 1100, 360, 360)  # x, y, w, h at 1080x1920: well below the hook title
COLOUR_SRC = ("color=c=0x808080:s=1080x1920:r=25:d=4,format=rgb24,drawbox=x=%d:y=%d:w=%d:h=%d:color=0x%02X%02X%02X:t=fill,"
              "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" % (PATCH + PATCH_RGB))
STATIC_SRC = "color=c=0x1c2230:s=1080x1920:r=25:d=4"  # one flat dark colour, no motion
IDENTITY = {"style": "punch-in", "punch_scale": 1.0,  # test fixture: a style that changes nothing
            "moves": {"opening_settle": False, "follow_cam": False, "word_punches": None}}
NONE = {"style": "none"}
MARKS = ((240, 900), (840, 1400))  # MARK_SRC's two 60 px white squares (centres, 1080x1920), below the hook title
MARK_SRC = ("color=c=0x303030:s=1080x1920:r=%s:d=%s," + ",".join(
    "drawbox=x=%d:y=%d:w=60:h=60:color=white:t=fill" % (x - 30, y - 30) for x, y in MARKS))
SEGS3 = [(0, 50), (50, 100), (100, 150)]
PLATE = (10, 12, 18)  # the layouts' card plate colour #0a0c12
GREY_SRC = "color=c=0x808080:s=1080x1920:r=25:d=6"  # flat mid grey: video vs plate can't be confused
TAKE_PIECES = [[1.0, 4.2], [5.0, 8.1], [9.0, 12.0]]  # raw seconds kept from the real take, about 10 s in all
TEXT_PIXELS = 1000  # frame0: at least this many bright (> 230 luma) pixels inside the hook box at 720x1280
TITLE_BOX = (90, 545, 930, 1145)  # frame0-scene: the hook-title scene's text block at 1080x1920 (x0, y0, x1, y1)
OPT = {"take": None, "out": None}
fails = []


def load(name, folder=SCRIPTS):
    spec = importlib.util.spec_from_file_location("editor_" + name, folder / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fpsmod = load("fps")
_compose = []


def compose_mod():
    """compose.py imported once, for the cases that call its functions in this process."""
    if not _compose:
        _compose.append(load("compose"))
    return _compose[0]


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (("  [%s]" % (detail,)) if detail and not ok else ""), flush=True)
    if not ok:
        fails.append(name)
    return ok


def run(cmd, cwd=None, timeout=900):
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=cwd, env=dict(os.environ), timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def compose(ws, *args):
    t0 = time.perf_counter()
    rc, out = run([sys.executable, "-X", "utf8", "-I", COMPOSE, *args], cwd=ws)
    print(f"  compose {' '.join(map(str, args))} -> exit {rc} in {time.perf_counter() - t0:.1f} s")
    for line in out.strip().splitlines():
        print("    | " + line)
    return rc, out


def beat(bid, s, e, w0, w1, scene=None, layout="full"):
    text = " ".join(w for w, _ in WORDS[w0:w1 + 1])
    return {"id": bid, "start_f": s, "end_f": e, "speech_anchor": {"text": text, "w0": w0, "w1": w1},
            "layout": layout, "value": None, "scene": scene, "broll": None, "transition": None}


def make_reel(root, gate_block=False, src=TESTSRC, scene=True):
    """A workspace with videos/<REEL>/ ready for compose.py. Returns (workspace, reel).
    src = the cut master's picture (a lavfi source); scene=False drops beat 2's lower-third."""
    ws, reel = new_reel(root, src, 25, 100)
    wj(reel / "work" / "cuts.json", {"fps": 25, "speed": 1.0, "segments": [
        {"src_in_f": 0, "src_out_f": 50, "out_in_f": 0, "out_out_f": 50},
        {"src_in_f": 60, "src_out_f": 110, "out_in_f": 50, "out_out_f": 100}]})
    if gate_block:
        beats = [beat("b_001", 0, 50, 0, 4),
                 beat("b_ov", 40, 70, 4, 4, {"id": "hook-title", "params": {},
                                             "slots": {"kicker": "Part 1", "title": "Three edits that save hours"}},
                      layout="overlay"),
                 beat("b_002", 50, 100, 5, 7, {"id": "cta-end-card", "params": {}, "slots": {
                     "headline": "Want more like this?", "action": "Follow for part 2", "handle": "@samplestudio"}})]
    else:
        beats = [beat("b_001", 0, 50, 0, 4),
                 beat("b_002", 50, 100, 5, 7, {"id": "lower-third", "params": {},
                                               "slots": {"name": "Alex Rivera", "title": "Founder, Sample Studio"}}
                      if scene else None)]
    write_send(reel, beats, 25)
    return ws, reel


def new_reel(root, src, rate, frames):
    """A workspace with videos/<REEL>/work/renders/master-100x.mp4: `frames` frames of src at `rate` + a 1 kHz tone
    (render.py's encode settings). Returns (workspace, reel)."""
    ws = Path(tempfile.mkdtemp(prefix="render-engine-", dir=root))
    reel = ws / "videos" / REEL
    (reel / "work" / "renders").mkdir(parents=True)
    master = reel / "work" / "renders" / "master-100x.mp4"
    secs = float(frames / Fraction(rate))
    rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", src,
                   "-f", "lavfi", "-i", f"sine=frequency=1000:sample_rate=48000:duration={secs}", "-map", "0:v", "-map", "1:a",
                   "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-g", "25", "-keyint_min", "25", "-sc_threshold", "0",
                   "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                   "-color_range", "tv", "-fps_mode", "cfr", "-r", str(rate), "-frames:v", str(frames), "-c:a", "aac",
                   "-b:a", "192k", "-movflags", "+faststart", master], timeout=300)
    if rc != 0 or not master.is_file():
        raise RuntimeError(f"couldn't make the synthetic master: {out[-300:]}")
    return ws, reel


def style_reel(root, src, style, layouts=("full", "full", "full"), rate="25", cut_fps=25):
    """The S6c reel: 150 frames of src in 3 segments (cuts at 50 and 100), one beat per segment with these layouts,
    no scenes, the Send's edit_style = style."""
    ws, reel = new_reel(root, src, rate, 150)
    wj(reel / "work" / "cuts.json", {"fps": cut_fps, "speed": 1.0, "segments": [
        {"src_in_f": a + 10 * i, "src_out_f": e + 10 * i, "out_in_f": a, "out_out_f": e} for i, (a, e) in enumerate(SEGS3)]})
    beats = [beat(f"b_00{i + 1}", a, e, w0, w1, layout=lay)
             for i, ((a, e), (w0, w1), lay) in enumerate(zip(SEGS3, ((0, 4), (5, 6), (7, 7)), layouts))]
    write_send(reel, beats, cut_fps, style)
    return ws, reel


def write_send(reel, beats, fps, edit_style=IDENTITY, caption_style=NONE):
    """The cut word list and the Beat Map Send for these beats (edit_style None = no style in the Send)."""
    words = [{"id": f"w_{i:04d}", "word": w, "start": st, "end": round(st + 0.3, 2)} for i, (w, st) in enumerate(WORDS)]
    wj(reel / "work" / "edit_map.cut.json", {"words": words})
    wj(reel / "beat-map-selection.json", {"schema": 1, "reel": REEL, "fps": fps, "words": "work/edit_map.cut.json",
                                          "beats": beats, "word_marks": [], "proposed": {}, "notes": {}, "needs": "",
                                          "sent_at": "2026-11-05T10:00:00Z",
                                          **({} if caption_style is None else {"caption_style": caption_style}),
                                          **({} if edit_style is None else {"edit_style": edit_style})})


def wj(path, obj):
    path.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def names():
    day = datetime.now().strftime("%m.%d.%y")
    return f"{REEL} Preview 720p - {day}.mp4", f"{REEL} Master - {day}.mp4"


def summary(out):
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {}


def size(video):
    rc, out = run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                   "-of", "json", video])
    try:
        s = json.loads(out)["streams"][0]
        return s["width"], s["height"]
    except (ValueError, KeyError, IndexError):
        return None


def stream_types(video):
    rc, out = run([rt.tool("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", video])
    try:
        return sorted(s["codec_type"] for s in json.loads(out)["streams"])
    except (ValueError, KeyError):
        return []


def audio_md5(video):
    rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-i", video, "-map", "0:a", "-c", "copy", "-f", "md5", "-"])
    return out.strip() if rc == 0 else ""


def warm_left():
    """How many warmCheck.js helpers from this state's node are still running (Windows; 0 elsewhere)."""
    if os.name != "nt":
        return 0
    node = str(Path(rt.tool("node")).resolve())
    ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    rc, out = run([ps, "-NoProfile", "-Command", "@(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath "
                   f"-eq '{node}' -and $_.CommandLine -like '*warmCheck.js*' }}).Count"], timeout=60)
    return int(out.strip()) if out.strip().isdigit() else -1


def no_traceback(name, out):
    ck(f"{name}: plain lines only, no traceback", "Traceback" not in out, out[-300:])


def videos_under(*dirs):
    return [p for d in dirs if d.exists() for p in d.rglob("*") if p.suffix.lower() in (".mov", ".mp4")]


# ---- pixels (stdlib: raw frames from ffmpeg, maths in Python) -------------------------------------------------
def colour_tags(video):
    """(scale in_color_matrix, in_range) from the file's own tags; untagged HD is read as BT.709, limited range."""
    rc, out = run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=color_space,color_range", "-of", "json", video])
    try:
        s = json.loads(out)["streams"][0]
    except (ValueError, KeyError, IndexError):
        s = {}
    m = {"bt470bg": "bt601", "smpte170m": "bt601"}.get(s.get("color_space"), "bt709")
    return m, ("pc" if s.get("color_range") == "pc" else "tv")


def grab(video, ns, pix="gray", crop=None, scale=None):
    """{n: raw bytes} for the frames numbered ns (decode order = frame number), as full-range luma ("gray") or
    "rgb24", optionally resized to scale (w, h) first, then cropped to crop (x, y, w, h)."""
    ns = sorted(set(ns))
    m, r = colour_tags(video)
    w, h = scale or size(video)
    vf = ["select='%s'" % "+".join("eq(n,%d)" % n for n in ns),
          f"scale={w}:{h}:flags=lanczos:in_color_matrix={m}:in_range={r}", f"format={pix}"]
    if crop:
        x, y, w, h = crop
        vf.append(f"crop={w}:{h}:{x}:{y}")
    p = subprocess.run([str(rt.tool("ffmpeg")), "-v", "error", "-i", str(video), "-vf", ",".join(vf),
                        "-fps_mode", "passthrough", "-f", "rawvideo", "-"], capture_output=True, timeout=600)
    n = w * h * (3 if pix == "rgb24" else 1)
    if p.returncode or len(p.stdout) != n * len(ns):
        raise RuntimeError(f"couldn't read frames {ns} of {Path(video).name}: got {len(p.stdout)} bytes for "
                           f"{len(ns)} frames; {p.stderr.decode('utf-8', 'replace')[-200:]}")
    return {k: p.stdout[i * n:(i + 1) * n] for i, k in enumerate(ns)}


def psnr(a, b):
    mse = sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)
    return math.inf if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def mean_rgb(b):
    n = len(b) // 3
    return tuple(sum(b[i::3]) / n for i in range(3))


def split_box(gray, w, h, box):
    """(pixels inside box, pixels outside it) of a w x h luma frame; box = (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = (max(0, int(v)) for v in box)
    x1, y1 = min(w, x1), min(h, y1)
    ins, out = bytearray(), bytearray()
    for y in range(h):
        row = gray[y * w:(y + 1) * w]
        if y0 <= y < y1:
            ins += row[x0:x1]
            out += row[:x0] + row[x1:]
        else:
            out += row
    return bytes(ins), bytes(out)


def hook_rect(w, h, margin=0):
    """The hook title's box at the tier size (compose.hook_box, three lines tall), grown by margin pixels."""
    x, y, bw, sz = compose_mod().hook_box(w, h)
    return x - bw / 2 - margin, y - margin, x + bw / 2 + margin, y + sz * 1.15 * 3 + margin


def markers(gray, w, h):
    """Centres of MARK_SRC's two squares in a w x h luma frame: the upper-left one looked for in x < w/2,
    0.39h <= y < 0.70h, the lower-right one in x >= w/2, y >= 0.70h (both clear of the hook title)."""
    out = []
    for x0, x1, y0, y1 in ((0, w // 2, int(h * 0.39), int(h * 0.70)), (w // 2, w, int(h * 0.70), h)):
        sx = sy = n = 0
        for y in range(y0, y1):
            for i, v in enumerate(gray[y * w + x0:y * w + x1]):
                if v > 128:
                    sx, sy, n = sx + x0 + i, sy + y, n + 1
        out.append((sx / n, sy / n) if n else None)
    return out


def scale_between(ref, got, origin):
    """(measured scale of got against ref, worst distance in px of got from ref scaled about origin)."""
    if None in ref or None in got:
        return None, math.inf
    k = math.dist(*got) / math.dist(*ref)
    off = max(math.dist(g, (origin[0] + k * (r[0] - origin[0]), origin[1] + k * (r[1] - origin[1])))
              for r, g in zip(ref, got))
    return k, off


def check_scales(f, frames_want, w=720, h=1280):
    """Measure each frame's scale against the first one; frames_want = [(frame, expected scale vs the first)]."""
    fr = grab(f, [n for n, _ in frames_want])
    ref = markers(fr[frames_want[0][0]], w, h)
    o = (0.5 * w, 0.38 * h)  # the default zoom centre (no head samples in these reels)
    for n, want in frames_want[1:]:
        k, off = scale_between(ref, markers(fr[n], w, h), o)
        ck(f"frame {n}: scale {k if k is None else round(k, 4)} vs frame {frames_want[0][0]} = {want} within 1 %, about "
           f"the zoom centre (worst point {off:.1f} px off)", k is not None and abs(k / want - 1) <= 0.01 and off <= 3,
           (k, off))


def in_process(fn, *args, **kw):
    """Run one compose.py function here, echo what it printed; (return value, the Stop it raised or None, output)."""
    c, buf = compose_mod(), io.StringIO()
    got, stop = None, None
    with contextlib.redirect_stdout(buf):
        try:
            got = fn(*args, **kw)
        except c.Stop as s:
            stop = s
    text = buf.getvalue() + ("\n".join(stop.lines) if stop else "")
    for line in text.strip().splitlines():
        print("    | " + line)
    return got, stop, text


# ---- cases -----------------------------------------------------------------------------------------------------
def c_selftest(root):
    for script in ("compose.py", "effect_gate.py"):
        rc, out = run([sys.executable, "-X", "utf8", "-I", SCRIPTS / script, "--selftest"], timeout=120)
        ck(f"{script} --selftest prints selftest ok", rc == 0 and out.strip() == "selftest ok", out[-400:])


def c_preview(root):
    ws, reel = make_reel(root)
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("preview", out)
    prev = names()[0]
    f = reel / "renders" / prev
    ck(f"preview exits 0 and writes renders/{prev}", rc == 0 and f.is_file(), out[-400:])
    s = summary(out)
    ck("summary JSON: tier preview, 100 frames, 25/1, audio cut, 1 scene",
       (s.get("tier"), s.get("frames"), s.get("fps"), s.get("audio"), s.get("scenes"), s.get("out")) ==
       ("preview", 100, "25/1", "cut", 1, f"renders/{prev}"), s)
    if f.is_file():
        ck("720x1280", size(f) == (720, 1280), size(f))
        rate = Fraction(fpsmod.probe_fps(f))
        ck("fps == 25/1 (probe_fps)", rate == Fraction(25), rate)
        n = fpsmod.frame_count(f)
        ck("100 frames", n == 100, n)
        ck("one video + one audio stream", stream_types(f) == ["audio", "video"], stream_types(f))
        a, b = audio_md5(f), audio_md5(reel / "work" / "renders" / "master-100x.mp4")
        ck("audio packets == the cut master's (stream copy)", a and a == b, f"{a} vs {b}")
    ck("work/render-tmp is gone", not (reel / "work" / "render-tmp").exists())
    ck("the preview name fails the Master rule", not MASTER_RE.match(prev))
    ck("no .partial left in renders/", not list((reel / "renders").glob("*.partial.mp4")))
    return ws


def broll_fixture(root):
    ws, reel = make_reel(root, src=STATIC_SRC, scene=False)
    fc = compose_mod().footage_check
    raw = reel / "work/renders/master-100x.mp4"
    wj(reel / "work/probe.json", {"input": str(raw)})
    (reel / "broll").mkdir()
    src = reel / "broll" / "own.mov"
    rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                   "testsrc2=size=1080x1350:rate=30:duration=3", "-f", "lavfi", "-i",
                   "sine=frequency=440:duration=3", "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest", src])
    if rc:
        raise RuntimeError("couldn't make the B-roll source: " + out[-300:])
    ck("B-roll source has sound to remove", stream_types(src) == ["audio", "video"])
    script = PLUGIN / "skills/reel-broll/scripts/broll_ingest.py"
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, reel])
    if not ck("real B-roll ingest succeeds", rc == 0, out):
        raise RuntimeError(out)
    clip = json.loads((reel / "broll/clips.json").read_text(encoding="utf-8"))["clips"][0]
    row = next(r for r in fc.rows(reel) if r["id"] == clip["ledger_id"])
    ingested = reel / clip["src"]
    ck("ingested sha256 lands in the own footage ledger", row["sha256"] == fc.digest(ingested)
       and row["origin"] == "own" and row["licence"] == "own" and row["role"] == "broll"
       and clip["origin"] == "own")
    ck("ingest drops B-roll sound and matches cut fps", stream_types(ingested) == ["video"]
       and Fraction(fpsmod.probe_fps(ingested)) == 25)
    stamp = ingested.stat().st_mtime_ns
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, reel])
    ck("ingest reuses matching prepared bytes", rc == 0 and ingested.stat().st_mtime_ns == stamp
       and len(fc.rows(reel)) == 2, out)
    # A duplicate encode must retain the canonical row's path; temp names must not touch another destination.
    shutil.copy2(src, reel / "broll/own.partial.mov")
    other = reel / "broll/ingested/own.partial.mp4"
    shutil.copy2(ingested, other)
    other_stamp = other.stat().st_mtime_ns
    (reel / "broll/broken.mov").write_bytes(b"not a video")
    (reel / "broll/notes.txt").write_text("skip me", encoding="utf-8")
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, reel])
    catalog = json.loads((reel / "broll/clips.json").read_text(encoding="utf-8"))["clips"]
    ck("duplicate bytes reuse the canonical ledger path and one picker entry", rc == 0 and len(catalog) == 1
       and catalog[0]["src"] == clip["src"] and catalog[0]["ledger_id"] == clip["ledger_id"]
       and "reused own.partial.mov" in out, (catalog, out))
    ck("cache cleanup preserves a destination named own.partial.mp4", other.is_file()
       and other.stat().st_mtime_ns == other_stamp and fc.digest(other) == row["sha256"])
    ck("unreadable video gets one named skip line; non-video ignored", out.count("skipped broken.mov:") == 1
       and "notes.txt" not in out, out)
    return ws, reel, clip


def c_broll_ai(root):
    # The editor must never acquire its own Higgsfield transport or spend path.
    forbidden = []
    # the editor's own skills; P/scripts/report_to_joe.py is the shared failure-report template whose comments
    # name other plugins' scripts, and it calls none of them
    for path in (PLUGIN / "skills").rglob("*"):
        if path.is_file():
            content = path.read_bytes().lower()
            if b"hf_rest" in content or b"ledger.py" in content:
                forbidden.append(str(path.relative_to(PLUGIN)))
    ck("editor tree contains no Higgsfield scripts", not forbidden, forbidden)
    ws, reel = make_reel(root, src=STATIC_SRC, scene=False)
    c, fc = compose_mod(), compose_mod().footage_check
    raw = reel / "work/renders/master-100x.mp4"
    wj(reel / "work/probe.json", {"input": str(raw)})
    downloaded = ws / "higgsfield/2026-11-06/download.mp4"
    downloaded.parent.mkdir(parents=True)
    rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                   "testsrc2=size=360x640:rate=30:duration=2", "-f", "lavfi", "-i",
                   "sine=frequency=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest", downloaded])
    if rc:
        raise RuntimeError("couldn't make the downloaded AI fixture: " + out[-300:])
    ck("AI download fixture has sound", stream_types(downloaded) == ["audio", "video"])
    before = hashlib.sha256(downloaded.read_bytes()).hexdigest()
    request = ws / "higgsfield/requests/test.json"
    request.parent.mkdir(parents=True)
    wj(request, {"prompt": "A quiet garden", "aspect_ratio": "9:16", "duration": 2})
    request_sha = hashlib.sha256(request.read_bytes()).hexdigest()
    script = PLUGIN / "skills/reel-broll/scripts/broll_ingest.py"
    command = [sys.executable, "-X", "utf8", "-I", script, reel]
    catalog_path = reel / "broll/clips.json"

    def snapshot():
        return {p.relative_to(reel).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in reel.rglob("*") if p.is_file()}

    def refused(label, args):
        saved = snapshot()
        rc, out = run(command + args)
        ck(label, rc == 1 and len(out.strip().splitlines()) == 1 and "Traceback" not in out
           and snapshot() == saved, out)

    for label, args in (
        ("AI without job id refuses without writes", ["--ai", downloaded, "--request", request]),
        ("AI without request refuses without writes", ["--ai", downloaded, "--job-id", "test-123"]),
        ("missing AI file refuses without writes", ["--ai", downloaded.with_name("missing.mp4"),
                                                   "--job-id", "test-123", "--request", request]),
        ("unreadable AI request refuses without writes", ["--ai", downloaded, "--job-id", "test-123",
                                                         "--request", request.parent])):
        refused(label, args)
    ai_args = ["--ai", downloaded, "--job-id", "test-123", "--request", request]
    rc, out = run(command + ai_args)
    if not ck("real AI ingest succeeds", rc == 0, out):
        raise RuntimeError(out)
    clips = json.loads(catalog_path.read_text(encoding="utf-8"))["clips"]
    clip = clips[0]
    prepared = reel / clip["src"]
    ledger = fc.rows(reel)
    row = next(r for r in ledger if r["id"] == clip["ledger_id"])
    ck("AI ingest logs own a-roll first and AI provenance", len(ledger) == 2 and ledger[0]["role"] == "aroll"
       and ledger[0]["origin"] == "own" and ledger[0]["licence"] == "own"
       and ledger[0]["sha256"] == fc.digest(raw) and row["role"] == "broll" and row["origin"] == "ai"
       and row["job_id"] == "test-123" and row["licence"] == "ai: higgsfield (client's own plan)"
       and row["sha256"] == hashlib.sha256(prepared.read_bytes()).hexdigest(), ledger)
    ck("AI catalog keeps request hash and job id", len(clips) == 1 and clip["origin"] == "ai"
       and clip["job_id"] == "test-123" and clip["request_sha256"] == request_sha, clips)
    ck("AI download bytes unchanged", hashlib.sha256(downloaded.read_bytes()).hexdigest() == before)
    ck("AI preparation is silent at cut fps and length", stream_types(prepared) == ["video"]
       and Fraction(fpsmod.probe_fps(prepared)) == 25 and clip["frames"] == 50)
    rc, out = run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=color_space,color_transfer,color_primaries,width,height", "-of", "json", prepared])
    ck("AI prepared copy is 1080 by 1920 BT.709", rc == 0 and json.loads(out)["streams"] == [
        {"width": 1080, "height": 1920, "color_space": "bt709", "color_transfer": "bt709",
         "color_primaries": "bt709"}], out)
    saved = snapshot()
    rc, out = run(command + ["--reuse", request])
    ck("exact AI request reuses clip without writes", rc == 0 and out.strip() ==
       f"reuse: {clip['ledger_id']} {clip['src']} (job test-123)" and snapshot() == saved, out)
    rc, out = run(command + ai_args)
    ck("repeat AI ingest keeps prepared copy and ledger", rc == 0 and fc.rows(reel) == ledger
       and prepared.stat().st_mtime_ns == saved[clip["src"]][1]
       and json.loads(catalog_path.read_text(encoding="utf-8"))["clips"] == clips, out)
    request_bytes = request.read_bytes()
    request.write_bytes(request_bytes.replace(b"garden", b"gardens"))
    refused("changed AI prompt misses reuse without writes", ["--reuse", request])
    rc, out = run(command + ["--reuse", request])
    ck("reuse miss says no earlier exact request", rc == 1 and out.strip() ==
       "no earlier AI clip for this exact request", out)
    request.write_bytes(request_bytes)
    prepared_bytes = prepared.read_bytes()
    prepared.write_bytes(prepared_bytes[:-1] + bytes([prepared_bytes[-1] ^ 1]))
    refused("changed AI prepared bytes miss reuse without writes", ["--reuse", request])
    prepared.write_bytes(prepared_bytes)
    refused("existing AI ledger unchanged on missing job id", ["--ai", downloaded, "--request", request])

    # A later own-only scan must preserve the paid clip, and AI ingest must preserve own clips.
    own = reel / "broll/own.mov"
    shutil.copy2(raw, own)
    rc, out = run(command)
    mixed = json.loads(catalog_path.read_text(encoding="utf-8"))["clips"]
    ck("own scan retains AI clip and labels own origin", rc == 0 and clip in mixed and
       any(x.get("origin") == "own" for x in mixed), (mixed, out))
    rc, out = run(command + ai_args)
    ck("AI ingest retains own picker entries", rc == 0 and
       json.loads(catalog_path.read_text(encoding="utf-8"))["clips"] == mixed, out)

    beats = [beat("b_001", 0, 50, 0, 4), beat("b_002", 50, 100, 5, 7)]
    beats[0]["broll"] = dict(src=clip["src"], **{"in": 0, "out": 50}, fit="cover", ledger_id=clip["ledger_id"])

    def preflight():
        write_send(reel, beats, 25)
        inp = c.load_inputs(reel)
        c.probe_inputs(inp)
        return inp, in_process(c.plan, inp, None)

    beats[0]["value"] = 12
    _, (_, stopped, text) = preflight()
    ck("ingested AI on value beat BLOCKs as proof", stopped is not None and "BLOCK" in text
       and "would look like proof" in text, text)
    beats[0]["value"] = None
    inp, (_, stopped, text) = preflight()
    ck("ingested AI on plain beat passes compose plan", stopped is None, text)
    _, stopped, text = in_process(c.footage_licences, inp, "master")
    ck("ingested AI passes master licence check with job id", stopped is None, text)
    return ws


def c_broll(root):
    ws, reel, clip = broll_fixture(root)
    # At frame 60, ten frames after the cut, with a six-frame source offset.
    beats = [beat("b_001", 0, 50, 0, 4), beat("b_002", 60, 85, 5, 7)]
    prepared = reel / clip["src"]
    for fit in ("cover", "blur-fill"):
        beats[1]["broll"] = dict(src=clip["src"], **{"in": 6, "out": 31}, fit=fit, ledger_id=clip["ledger_id"])
        write_send(reel, beats, 25)
        rc, out = compose(ws, "preview", "--reel-dir", reel, "--keep-project")
        no_traceback("B-roll " + fit, out)
        final = reel / "renders" / names()[0]
        if not ck(f"B-roll {fit} preview renders", rc == 0 and final.is_file(), out[-500:]):
            continue
        page = (reel / "work/render-tmp/proj/index.html").read_text(encoding="utf-8")
        ck(f"{fit}: source offset and muted layer 200", 'data-media-start="0.24"' in page
           and 'z-index: 200' in page and page.count('src="media/broll-') == (2 if fit == "blur-fill" else 1)
           and page.count('<video id="broll-') == (2 if fit == "blur-fill" else 1))
        # Compare luma; crop only the centre for contained footage, away from the blurred fill.
        if fit == "cover":
            iw, ih = size(prepared)
            rw = round(iw * 1280 / ih)
            expected = grab(prepared, [6], scale=(rw, 1280), crop=((rw - 720) // 2, 0, 720, 1280))[6]
            frames = grab(final, [59, 60, 85])
            threshold = 35
            actual, before = frames[60], frames[59]
            ck("B-roll disappears on its exclusive end frame", psnr(frames[85], expected) < 35)
        else:
            # The 4:5 clip contains at 720x900, with 190px above and below it.
            expected = grab(prepared, [6], scale=(720, 900), crop=(240, 340, 240, 220))[6]
            frames = grab(final, [59, 60], crop=(240, 530, 240, 220))
            threshold = 30
            actual, before = frames[60], frames[59]
        score = psnr(actual, expected)
        ck(f"{fit}: first B-roll frame matches source frame 6 (PSNR >= {threshold})", score >= threshold, score)
        ck(f"{fit}: previous frame is a-roll (PSNR < 35)", psnr(before, expected) < 35)
        master_audio = audio_md5(reel / "work/renders/master-100x.mp4")
        ck(f"{fit}: voice packets unchanged, B-roll muted", bool(master_audio) and audio_md5(final) == master_audio)
    return ws


def c_broll_recording_paths(root):
    """Own B-roll finds a single take from legacy relative and new absolute probe inputs."""
    ws, reel = make_reel(root, src=STATIC_SRC, scene=False)
    c, fc = compose_mod(), compose_mod().footage_check
    raw = reel / "RAW.mp4"
    shutil.copy2(reel / "work/renders/master-100x.mp4", raw)
    (reel / "broll").mkdir()
    shutil.copy2(raw, reel / "broll/own.mov")
    work = reel / "work"
    relative = raw.relative_to(ws)
    rc, out = run([sys.executable, "-X", "utf8", "-I", FIRST_CUTS / "probe.py",
                   relative, "-o", work], cwd=ws)
    if not ck("probe accepts a workspace-relative recording", rc == 0, out):
        raise RuntimeError(out)
    probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
    ck("probe stores the recording's absolute path", probe["input"] == str(raw.resolve()), probe["input"])
    script = PLUGIN / "skills/reel-broll/scripts/broll_ingest.py"
    for label, path in (("legacy relative", str(relative)), ("new absolute", str(raw.resolve()))):
        wj(work / "probe.json", dict(probe, input=path))
        rc, out = run([sys.executable, "-X", "utf8", "-I", script, reel], cwd=ws)
        if not ck(f"{label}: own B-roll ingest finds the recording", rc == 0, out):
            continue
        clip = json.loads((reel / "broll/clips.json").read_text(encoding="utf-8"))["clips"][0]
        beats = [beat("b_001", 0, 50, 0, 4), beat("b_002", 50, 100, 5, 7)]
        beats[0]["broll"] = dict(src=clip["src"], **{"in": 0, "out": 50}, fit="cover",
                                 ledger_id=clip["ledger_id"])
        write_send(reel, beats, 25)
        ledger = fc.rows(reel)
        raw_rows = [r for r in ledger if r["path"] == str(raw.resolve())]
        ck(f"{label}: ingest logs one own recording with matching bytes", len(raw_rows) == 1
           and raw_rows[0]["role"] == "aroll" and raw_rows[0]["origin"] == "own"
           and raw_rows[0]["licence"] == "own" and raw_rows[0]["sha256"] == fc.digest(raw), raw_rows)
        rc, out = run([sys.executable, "-X", "utf8", "-I", PLUGIN / "skills/_shared/checks/footage_check.py",
                       "check", reel, work], cwd=ws)
        ck(f"{label}: footage ledger check finds the recording", rc == 0, out)
        previous = Path.cwd()
        try:
            os.chdir(ws)
            rows = c.licence_rows.footage({"reel_dir": reel})
            ck(f"{label}: recording and own B-roll licence rows pass", not rows, rows)
            ck(f"{label}: reel-relative recording fallback still works", fc.asset(reel, "RAW.mp4") == raw)
        finally:
            os.chdir(previous)
    return ws


def c_broll_blocks(root):
    ws, reel = make_reel(root, scene=False)
    c, fc = compose_mod(), compose_mod().footage_check
    raw = reel / "work/renders/master-100x.mp4"
    wj(reel / "work/probe.json", {"input": str(raw)})
    ledger_path = reel / "footage/ledger.json"
    ck("fresh single-take B-roll reel has no ledger", not ledger_path.exists())
    (reel / "broll").mkdir()
    shutil.copy2(raw, reel / "broll/own.mov")
    script = PLUGIN / "skills/reel-broll/scripts/broll_ingest.py"
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, reel])
    if not ck("real ingest starts with no footage ledger", rc == 0, out):
        raise RuntimeError(out)
    ledger = fc.rows(reel)
    raw_rows = [r for r in ledger if fc.normalized(fc.asset(reel, r["path"])) == fc.normalized(raw)]
    ck("ingest logs the a-roll's role, own rights and raw sha256", len(raw_rows) == 1 and
       raw_rows[0]["role"] == "aroll" and raw_rows[0]["origin"] == "own" and
       raw_rows[0]["licence"] == "own" and raw_rows[0]["sha256"] == fc.digest(raw), raw_rows)
    ck("ingest explains the new recording row once", out.splitlines().count(
       f"logged your recording {raw.name} in the footage list, so B-roll and the final can check it") == 1, out)
    raw_id = raw_rows[0]["id"]
    folder = reel / "broll/ingested"
    clip = json.loads((reel / "broll/clips.json").read_text(encoding="utf-8"))["clips"][0]
    prepared = reel / clip["src"]
    ident = clip["ledger_id"]
    ck("fresh ingest also logs the B-roll row", len(ledger) == 2 and any(r["id"] == ident and
       r["role"] == "broll" and r["sha256"] == fc.digest(prepared) for r in ledger), ledger)
    own = dict(src=clip["src"], **{"in": 0, "out": 50}, fit="cover", ledger_id=ident)
    beats = [beat("b_001", 0, 50, 0, 4), beat("b_002", 50, 100, 5, 7)]
    beats[0]["broll"] = dict(own)
    write_send(reel, beats, 25)
    rows = c.licence_rows.footage({"reel_dir": reel})
    ck("ingest-logged single take has no footage licence blocks", not rows, rows)
    rc, out = run([sys.executable, "-X", "utf8", "-I", PLUGIN / "skills/_shared/checks/footage_check.py",
                   "check", reel, reel / "work"])
    ck("single-take re-cut footage check passes after ingest", rc == 0, out)
    beats[0]["broll"] = None
    write_send(reel, beats, 25)
    rows = c.licence_rows.footage({"reel_dir": reel})
    ck("clearing every B-roll beat leaves no footage licence blocks", not rows, rows)
    beats[0]["broll"] = dict(own)

    # One missing recording must stop the whole ingest before any ledger or clip is written.
    missing_reel = ws / "videos/missing-recording"
    (missing_reel / "work").mkdir(parents=True)
    (missing_reel / "broll").mkdir()
    shutil.copy2(reel / "work/cuts.json", missing_reel / "work/cuts.json")
    shutil.copy2(raw, missing_reel / "broll/own.mov")
    missing_raw = missing_reel / "raw.mp4"
    wj(missing_reel / "work/probe.json", {"input": str(missing_raw)})
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, missing_reel])
    ck("missing raw stops ingest with one plain named line", rc == 1 and out.splitlines() == [
       "your recording raw.mp4 is missing; restore it before adding B-roll"], out)
    ck("missing raw writes no ledger or prepared clips", not (missing_reel / "footage/ledger.json").exists()
       and not (missing_reel / "broll/clips.json").exists() and not (missing_reel / "broll/ingested").exists())
    mixed_cuts = json.loads((reel / "work/cuts.json").read_text(encoding="utf-8"))
    mixed_cuts["takes"] = {"1": {"raw": str(raw)}, "2": {"raw": str(missing_raw)},
                           "3": {"raw": str(missing_reel / "unused.mp4")}}
    for i, segment in enumerate(mixed_cuts["segments"], 1):
        segment["take"] = i
    wj(missing_reel / "work/cuts.json", mixed_cuts)
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, missing_reel])
    ck("missing later mixed take stops before logging the first recording", rc == 1 and out.splitlines() == [
       "your recording raw.mp4 is missing; restore it before adding B-roll"]
       and not (missing_reel / "footage/ledger.json").exists(), out)
    missing_raw.write_bytes(raw.read_bytes() + b"second-recording")
    (missing_reel / "work/probe.json").unlink()
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, missing_reel])
    mixed_rows = fc.rows(missing_reel)
    ck("mixed ingest logs every used recording from takes without probe input", rc == 0 and
       {r["sha256"] for r in mixed_rows if r["role"] == "aroll"} == {fc.digest(raw), fc.digest(missing_raw)} and
       out.count("logged your recording ") == 2 and len(mixed_rows) == 3, (mixed_rows, out))
    rc, out = run([sys.executable, "-X", "utf8", "-I", script, missing_reel])
    ck("repeat ingest keeps existing recording rows and logs none again", rc == 0 and
       fc.rows(missing_reel) == mixed_rows and "logged your recording " not in out, out)

    def preflight():
        write_send(reel, beats, 25)
        inp = c.load_inputs(reel)
        c.probe_inputs(inp)
        return in_process(c.plan, inp, None)

    original = prepared.read_bytes()
    prepared.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    _, stopped, text = preflight()
    ck("changed B-roll bytes BLOCK before rendering", stopped is not None and "BLOCK" in text and "changed after it was logged" in text, text)
    prepared.write_bytes(original)
    beats[1]["broll"] = dict(own, **{"in": 25, "out": 75})
    _, stopped, text = preflight()
    ck("same clip source frames overlapping BLOCK", stopped is not None and "BLOCK" in text and "used twice" in text, text)
    beats[1]["broll"].update({"in": 50, "out": 100})
    _, stopped, text = preflight()
    ck("touching source intervals pass", stopped is None, text)
    beats[1]["broll"] = None
    # add() must log an AI asset with different bytes, rather than deduping the own clip.
    ai = folder / "ai.mp4"
    ai.write_bytes(original + b"ai-fixture")
    ai_id = fc.add(reel, ai, role="broll", origin="ai", licence="ai", job_id="test")
    beats[0]["broll"] = dict(own, src="broll/ingested/ai.mp4", ledger_id=ai_id)
    beats[0]["value"] = 12
    _, stopped, text = preflight()
    ck("AI with a value BLOCKs as false proof", stopped is not None and "BLOCK" in text and "would look like proof" in text, text)
    beats[0]["value"] = None
    beats[0]["scene"] = {"id": "stat-card", "slots": {"stat": "3", "label": "edits"}}
    _, stopped, text = preflight()
    ck("AI on a stat-card BLOCKs as false proof", stopped is not None and "BLOCK" in text and "would look like proof" in text, text)
    beats[0]["scene"] = None
    _, stopped, text = preflight()
    ck("AI on a plain beat passes", stopped is None, text)
    beats[0]["broll"] = dict(own)
    beats[0]["value"] = 12
    _, stopped, text = preflight()
    ck("own footage on a value beat passes", stopped is None, text)
    ledger = fc.rows(reel)
    own_row = next(r for r in ledger if r["id"] == ident)
    ai_row = next(r for r in ledger if r["id"] == ai_id)
    own_row["licence"] = ""
    wj(ledger_path, ledger)
    write_send(reel, beats, 25)
    dummy_preview(reel)
    c.cmd_ok(reel, False)
    _, stopped, text = in_process(c.render, reel, "master", None)
    ck("Master without music refuses empty footage licence before output", stopped is not None and "licence" in text
       and not (reel / "renders" / names()[1]).exists() and not (reel / "work/render-tmp/proj").exists(), text)
    inp = c.load_inputs(reel)
    c.probe_inputs(inp)
    _, stopped, text = in_process(c.footage_licences, inp, "preview")
    ck("preview footage licence is warning only", stopped is None and "warning:" in text and "licence" in text, text)
    own_row["licence"] = "own"
    ai_row.pop("job_id")
    wj(ledger_path, ledger)
    beats[0]["broll"] = dict(own, src="broll/ingested/ai.mp4", ledger_id=ai_id)
    write_send(reel, beats, 25)
    rows = c.licence_rows.run({"reel_dir": reel})
    ck("AI licence requires job id even without music", any(r["level"] == "block" and "job id" in r["msg"] for r in rows), rows)
    cuts = {"takes": {"1": {"raw": str(prepared)}}, "segments": [
        {"take": 1, "src_in_f": 0, "src_out_f": 50}]}
    own_row["role"], own_row["licence"] = "aroll", ""
    wj(ledger_path, ledger)
    rows = c.licence_rows.run({"reel_dir": reel, "cuts": cuts, "beats": []})
    ck("cut_uses checks used a-roll licence without a bed", any(ident in r["msg"] and "licence" in r["msg"] for r in rows), rows)
    own_row["licence"] = "own"
    wj(ledger_path, ledger)
    rows = c.licence_rows.run({"reel_dir": reel, "cuts": cuts, "beats": []})
    ck("unused AI footage row needs no licence job id on this cut", not rows, rows)
    # The direct check CLI runs with -I in the existing sound-pass harness too.
    beats[0]["broll"] = dict(own)
    write_send(reel, beats, 25)
    cli = PLUGIN / "skills/_shared/checks/licence_rows.py"
    rc, out = run([sys.executable, "-X", "utf8", "-I", cli, reel])
    ck("isolated licence CLI imports footage_check and accepts complete used rows", rc == 0 and "nothing missing" in out, out)
    raw_row = next(r for r in ledger if r["id"] == raw_id)
    raw_row["licence"] = ""
    wj(ledger_path, ledger)
    rows = c.licence_rows.run({"reel_dir": reel})
    ck("two-segment single-take a-roll licence problem appears once", [r["msg"] for r in rows] == [
       f"the footage row {raw_id} needs a licence"], rows)
    # Missing rows used to repeat per segment too; preserve the order of distinct messages.
    wj(ledger_path, [r for r in ledger if r["id"] != raw_id])
    beats[0]["broll"] = dict(own, ledger_id="f99")
    rows = c.licence_rows.footage({"reel_dir": reel, "beats": beats})
    ck("repeated missing recording lines are deduplicated in first-appearance order", [r["msg"] for r in rows] == [
       f"the footage {own['src']} has no matching licence row",
       f"the recording {raw.name} has no matching licence row"], rows)
    wj(ledger_path, ledger)
    probe_path = reel / "work/probe.json"
    for name, content in (("missing", None), ("unreadable", "{"), ("no input", "{}")):
        if content is None:
            probe_path.unlink(missing_ok=True)
        else:
            probe_path.write_text(content, encoding="utf-8")
        rows = c.licence_rows.run({"reel_dir": reel})
        ck(f"{name} source details cannot bypass a-roll licence check", any(r["level"] == "block" and
           r["where"] == "work/probe.json" for r in rows), rows)
    return ws


def dummy_preview(reel):
    """ok only reads the newest preview's name and time, so a placeholder file stands in for a real render."""
    (reel / "renders").mkdir(exist_ok=True)
    p = reel / "renders" / names()[0]
    p.write_bytes(b"placeholder")
    t = time.time() - 60
    os.utime(p, (t, t))
    return p


def c_master_refused(root):
    ws, reel = make_reel(root)
    mast = reel / "renders" / names()[1]
    p = dummy_preview(reel)
    rc, out = compose(ws, "master", "--reel-dir", f"videos/{REEL}")
    no_traceback("master before OK", out)
    ck("master before any OK: exit 1, plain line, no Master",
       rc == 1 and "needs your OK first" in out and not mast.exists(), out[-300:])
    rc, out = compose(ws, "ok", "--reel-dir", f"videos/{REEL}")
    okf = reel / "work" / "render-ok.json"
    doc = json.loads(okf.read_text(encoding="utf-8")) if okf.is_file() else {}
    ck("ok: exit 0, render-ok.json names the latest preview", rc == 0 and doc.get("preview") == p.name, doc)
    ck("render-ok.json has LF line ends only", okf.is_file() and b"\r" not in okf.read_bytes())
    t = time.time() + 30
    os.utime(p, (t, t))
    rc, out = compose(ws, "master", "--reel-dir", f"videos/{REEL}")
    no_traceback("master after a changed preview", out)
    ck("preview touched after the OK: refused again, no Master",
       rc == 1 and "needs your OK first" in out and not mast.exists(), out[-300:])
    return ws


def c_master(root):
    ws, reel = make_reel(root)
    dummy_preview(reel)
    rc, out = compose(ws, "ok", "--reel-dir", f"videos/{REEL}")
    ck("ok: exit 0", rc == 0, out[-300:])
    rc, out = compose(ws, "master", "--reel-dir", f"videos/{REEL}")
    no_traceback("master", out)
    mast = names()[1]
    f = reel / "renders" / mast
    ck(f"master exits 0 and writes renders/{mast}", rc == 0 and f.is_file(), out[-400:])
    if f.is_file():
        ck("1080x1920", size(f) == (1080, 1920), size(f))
        n = fpsmod.frame_count(f)
        ck("100 frames", n == 100, n)
    ck("the Master name matches the Master rule", bool(MASTER_RE.match(mast)))
    ck("summary JSON: tier master, audio cut", (summary(out).get("tier"), summary(out).get("audio")) == ("master", "cut"),
       summary(out))
    ck("work/render-tmp is gone", not (reel / "work" / "render-tmp").exists())
    return ws


def c_gate_block(root):
    ws, reel = make_reel(root, gate_block=True)
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("gate-block", out)
    ck("two takeovers at once: exit 1 with a BLOCK takeover ... overlaps takeover ... line",
       rc == 1 and re.search(r"^BLOCK takeover .* overlaps takeover ", out, re.M) is not None, out[-400:])
    left = videos_under(reel / "work" / "render-tmp", reel / "renders")
    ck("nothing rendered (no .mov/.mp4 under work/render-tmp or renders)", not left, left)
    return ws


def c_bad_input(root):
    ws, reel = make_reel(root)
    send = reel / "beat-map-selection.json"
    keep = send.read_bytes()
    send.unlink()
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("no Beat Map Send", out)
    ck("no beat-map-selection.json: exit 2, 'Send the Beat Map first'", rc == 2 and "Send the Beat Map first" in out,
       out[-300:])
    send.write_bytes(keep)
    cuts = reel / "work" / "cuts.json"
    wj(cuts, dict(json.loads(cuts.read_text(encoding="utf-8")), fps=30))
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("cut list fps != master fps", out)
    ck("cuts fps 30 vs the 25 fps master: exit 1, plain line", rc == 1 and "rebuild the Beat Map" in out, out[-300:])
    ck("nothing rendered", not videos_under(reel / "work" / "render-tmp", reel / "renders"))
    return ws


def preview_ok_master(ws, *extra):
    """preview, then ok, then master; (preview file, Master file, the three outputs)."""
    outs = [compose(ws, "preview", "--reel-dir", f"videos/{REEL}", *extra)[1],
            compose(ws, "ok", "--reel-dir", f"videos/{REEL}")[1],
            compose(ws, "master", "--reel-dir", f"videos/{REEL}", *extra)[1]]
    reel = ws / "videos" / REEL
    prev, mast = (reel / "renders" / n for n in names())
    ck("preview and Master both rendered", prev.is_file() and mast.is_file(), outs[-1][-400:])
    return prev, mast, outs


def need_take():
    take = OPT["take"]
    if not take or not Path(take).is_file():
        return None
    return Path(take)


def c_joi_frames(root):
    """F-3 on a real take, no Resolve: S4b's own snap -> cuts.json -> render.py master, then the Master is frame
    exact against it (same frame count, cuts on out_in_f, every probed frame closest to the cut master's own)."""
    take = need_take()
    if not ck("joi-frames: a real take given (--take or EDITOR_SE_TEST_TAKE) and readable", take is not None,
              OPT["take"]):
        return None
    ws = Path(tempfile.mkdtemp(prefix="render-engine-", dir=root))
    reel = ws / "videos" / REEL
    work = reel / "work"
    work.mkdir(parents=True)
    probe, gaps = load("probe", FIRST_CUTS), load("gaps", FIRST_CUTS)
    probe.find_tools()
    # render.py reads fps_flag, video and audio_stream from probe.json; S4b's cut fps is probe.json's out_rate
    wj(work / "probe.json", {"fps_flag": probe.fps_flag(), "video": probe.video_facts(take), "audio_stream": 0,
                             "out_rate": 30.0})
    cuts = gaps.snap_cuts(TAKE_PIECES, 30.0, speed=1.0)
    gaps.write_cuts(work, cuts)
    t0 = time.perf_counter()
    rc, out = run([sys.executable, "-X", "utf8", "-I", FIRST_CUTS / "render.py", work, take, "--master"])
    print(f"  render.py --master -> exit {rc} in {time.perf_counter() - t0:.1f} s")
    cut = work / "renders" / "master-100x.mp4"
    if not ck("render.py made the cut master", rc == 0 and cut.is_file(), out[-400:]):
        return ws
    segs = cuts["segments"]
    total, cut_f = segs[-1]["out_out_f"], [s["out_in_f"] for s in segs[1:]]
    print(f"  cuts.json: {len(segs)} segments, {total} frames at {cuts['fps']} fps, interior cuts {cut_f}")
    write_send(reel, [beat("b_001", 0, cut_f[0], 0, 4), beat("b_002", cut_f[0], cut_f[1], 5, 6),
                      beat("b_003", cut_f[1], total, 7, 7)], cuts["fps"])
    _, mast, outs = preview_ok_master(ws)
    no_traceback("joi-frames", "".join(outs))
    if not mast.is_file():
        return ws
    n = fpsmod.frame_count(mast)
    ck(f"Master frame count == last out_out_f ({total})", n == total, n)
    t0 = time.perf_counter()
    ks = sorted({k for s in segs for k in (s["out_in_f"], (s["out_in_f"] + s["out_out_f"] - 1) // 2, s["out_out_f"] - 1)})
    region = (108, 768, 864, 960)  # 1080x1920: below the hook title, across the speaker
    got = grab(mast, ks, crop=region)
    ref = grab(cut, [j for k in ks for j in (k - 1, k, k + 1) if 0 <= j < total], crop=region)
    exact = {}
    for k in ks:
        p = {d: psnr(got[k], ref[k + d]) for d in (-1, 0, 1) if k + d in ref}
        exact[k] = p[0] >= 30 and all(p[0] > v for d, v in p.items() if d)
        ck(f"frame {k}: the Master's frame is the cut master's frame {k} (PSNR n {p[0]:.2f} dB"
           + "".join(f", n{d:+d} {v:.2f}" for d, v in sorted(p.items()) if d) + "; >= 30 and best at n)", exact[k], p)
    ck(f"interior cuts land on out_in_f of segments[1:] {cut_f} (their first frames match exactly)",
       all(exact[c] for c in cut_f))
    print(f"  frame comparison took {time.perf_counter() - t0:.1f} s")
    return ws


def c_colour(root):
    """A known colour survives the render: the patch's mean in the Master vs the cut master, CIEDE2000 <= 2.0."""
    spec = importlib.util.spec_from_file_location("first_cut_test", HERE / "first_cut_test.py")
    fct = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fct)
    ws, reel = make_reel(root, src=COLOUR_SRC, scene=False)
    prev, mast, outs = preview_ok_master(ws)
    no_traceback("colour", "".join(outs))
    cut = reel / "work" / "renders" / "master-100x.mp4"
    x, y, w, h = PATCH
    inner = (x + 60, y + 60, w - 120, h - 120)  # clear of the 4:2:0 edges
    f = 75  # after the hook title is gone
    c = mean_rgb(grab(cut, [f], "rgb24", crop=inner)[f])
    print(f"  tags: cut master {colour_tags(cut)}, Master {colour_tags(mast) if mast.is_file() else '-'}")
    print(f"  info: cut master patch {tuple(round(v, 1) for v in c)} vs planted {PATCH_RGB}: "
          f"dE2000 {fct.de2000(c, PATCH_RGB):.2f}")
    if prev.is_file():
        s = 720 / 1080
        p = mean_rgb(grab(prev, [f], "rgb24", crop=tuple(round(v * s) for v in inner))[f])
        print(f"  info: preview patch {tuple(round(v, 1) for v in p)}: dE2000 vs the cut master {fct.de2000(p, c):.2f}")
    if mast.is_file():
        m = mean_rgb(grab(mast, [f], "rgb24", crop=inner)[f])
        d = fct.de2000(m, c)
        print(f"  Master patch {tuple(round(v, 1) for v in m)}: dE2000 vs the cut master {d:.2f}")
        ck(f"Master colour: dE2000 {d:.2f} <= 2.0 against the cut master", d <= 2.0, (m, c))
    return ws


def c_frame0(root):
    """H-S6b-7: frame 0 already shows the whole hook title, fully opaque, still, over the untouched picture."""
    ws, reel = make_reel(root, src=STATIC_SRC, scene=False)
    prev, mast, outs = preview_ok_master(ws)
    no_traceback("frame0", "".join(outs))
    cut = reel / "work" / "renders" / "master-100x.mp4"
    keep = Path(OPT["out"]) / "frame0"
    keep.mkdir(parents=True, exist_ok=True)
    last = 50 - 1  # the hook shows over [0, min(first beat end 50, 5 s)) at 25 fps
    for tier, f, (w, h) in (("preview", prev, (720, 1280)), ("Master", mast, (1080, 1920))):
        if not f.is_file():
            continue
        fr = grab(f, [0, last])
        base = grab(cut, [0], scale=(w, h))[0]
        ck(f"{tier}: frame 0 == the last hook frame {last} (PSNR {psnr(fr[0], fr[last]):.2f} dB >= 45: no fade, "
           f"no slide-in)", psnr(fr[0], fr[last]) >= 45)
        ins, _ = split_box(fr[0], w, h, hook_rect(w, h))
        bins, _ = split_box(base, w, h, hook_rect(w, h))
        bright = sum(v > 230 for v in ins)
        want = TEXT_PIXELS * (w / 720) ** 2
        ck(f"{tier}: text in the hook box at frame 0 ({bright} pixels > 230 luma, >= {want:.0f}; the cut master "
           f"has {sum(v > 230 for v in bins)})", bright >= want and not any(v > 230 for v in bins))
        ck(f"{tier}: the brightest text pixel reaches {max(ins)} >= 245 (fully opaque white)", max(ins) >= 245)
        _, out = split_box(fr[0], w, h, hook_rect(w, h, margin=round(16 * w / 1080)))
        _, bout = split_box(base, w, h, hook_rect(w, h, margin=round(16 * w / 1080)))
        ck(f"{tier}: outside the hook box frame 0 == the cut master (PSNR {psnr(out, bout):.2f} dB >= 40: no backdrop)",
           psnr(out, bout) >= 40)
        png = keep / f"frame0-{tier.lower()}.png"
        rc, o = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", f, "-vf", "select='eq(n,0)'", "-frames:v", "1", png])
        ck(f"{tier}: frame 0 saved as a PNG", rc == 0 and png.is_file(), o[-200:])
        print(f"  frame 0 ({tier}): {png}")
    return ws


def c_frame0_scene(root):
    """H-S6b-19: a hook-title scene on the first beat opens complete (entrance none): frame 0 == its last frame."""
    ws, reel = make_reel(root, src=STATIC_SRC, scene=False)
    send = reel / "beat-map-selection.json"
    bm = json.loads(send.read_text(encoding="utf-8"))
    bm["beats"][0]["scene"] = {"id": "hook-title", "params": {}, "slots": {"kicker": "Part 1", "title": HOOK}}
    wj(send, bm)
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("frame0-scene", out)
    f = reel / "renders" / names()[0]
    ck("preview exits 0 with 1 scene", rc == 0 and f.is_file() and summary(out).get("scenes") == 1, out[-400:])
    ck("no 'check that frame 0 reads as a complete hook' warning (the scene opens complete)",
       "reads as a complete hook" not in out)
    if not f.is_file():
        return ws
    w, h = 720, 1280
    last = 50 - 1  # the scene runs over the first beat, frames 0-49
    fr = grab(f, [0, last])
    base = grab(reel / "work" / "renders" / "master-100x.mp4", [0], scale=(w, h))[0]
    p = psnr(fr[0], fr[last])
    ck(f"frame 0 == the scene's last frame {last} on the beat (PSNR {p:.2f} dB >= 45: complete from frame 0)", p >= 45)
    box = [v * w / 1080 for v in TITLE_BOX]
    ins, _ = split_box(fr[0], w, h, box)
    bins, _ = split_box(base, w, h, box)
    bright = sum(v > 230 for v in ins)
    ck(f"title text in the title box at frame 0 ({bright} pixels > 230 luma, >= {TEXT_PIXELS}; the cut master has "
       f"{sum(v > 230 for v in bins)})", bright >= TEXT_PIXELS and not any(v > 230 for v in bins))
    ck(f"the brightest title pixel at frame 0 reaches {max(ins)} >= 245 (fully opaque white)", max(ins) >= 245)
    keep = Path(OPT["out"]) / "frame0-scene"
    keep.mkdir(parents=True, exist_ok=True)
    png = keep / "frame0-scene-preview.png"
    rc, o = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", f, "-vf", "select='eq(n,0)'", "-frames:v", "1", png])
    ck("frame 0 saved as a PNG", rc == 0 and png.is_file(), o[-200:])
    print(f"  frame 0 (preview, hook-title scene): {png}")
    return ws


def c_scene_no_params(root):
    """An optional scene params key stays optional through the scene variables write."""
    ws, reel = make_reel(root, src=STATIC_SRC, scene=False)
    send = reel / "beat-map-selection.json"
    bm = json.loads(send.read_text(encoding="utf-8"))
    # The first-beat entrance override inserts params for hook-title, masking this bug.
    bm["beats"][1]["scene"] = {"id": "hook-title", "slots": {"kicker": "", "title": "Meet Alex today"}}
    ck("scene fixture omits params", "params" not in bm["beats"][1]["scene"])
    wj(send, bm)
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("scene-no-params", out)
    ck("preview exits 0 without scene params", rc == 0, out[-400:])
    ck("preview file exists without scene params", (reel / "renders" / names()[0]).is_file())
    return ws


def c_cut_span_block(root):
    """VES-1: an a-roll move planted across the cut (compose's internal extra_spans) stops the render."""
    ws, reel = make_reel(root, scene=False)
    stale = reel / "work" / "render-tmp" / "left-by-a-crash"
    stale.mkdir(parents=True)
    (stale / "half.mp4").write_bytes(b"x")
    plant = [{"layer": "aroll_transform", "start_f": 50 - 2, "end_f": 50 + 2, "id": "plant"}]
    _, stop, text = in_process(compose_mod().render, reel, "preview", None, extra_spans=plant)
    no_traceback("cut-span-block", text)
    ck("the planted move across the cut at 50: stopped (exit 1) with a BLOCK aroll_transform ... runs across the cut line",
       stop is not None and stop.code == 1 and any(re.match(r"BLOCK aroll_transform .*runs across the cut", l)
                                                  for l in stop.lines), text[-400:])
    ck("nothing rendered", not videos_under(reel / "renders", reel / "work" / "render-tmp"))
    ck("work/render-tmp is gone, the leftover of an earlier crash too", not (reel / "work" / "render-tmp").exists())
    return ws


LINT_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <script src="./vendor/gsap.min.js"></script>
    <style>
      @font-face { font-family: "Inter"; src: url("./fonts/Inter-Regular.woff2") format("woff2"); }
      * { margin: 0; padding: 0; }
      html, body { width: 720px; height: 1280px; overflow: hidden; background: #000000; }
      #t { position: absolute; left: 100px; top: 300px; color: #ffffff; font-size: 48px; font-family: "%(font)s"; }
    </style>
  </head>
  <body>
    <div id="main" data-composition-id="main" data-start="0" data-duration="1" data-width="720" data-height="1280">
      <div id="t" %(clip)sdata-start="0" data-duration="1" data-track-index="0">Planted</div>
    </div>
    <script>
      (function () {
        const tl = gsap.timeline({ paused: true });
        tl.set("#t", { opacity: 1 }, 0);
        window.__timelines = window.__timelines || {};
        window.__timelines["main"] = tl;
      })();
    </script>
  </body>
</html>
"""
# HyperFrames 0.8.184: a font family with no @font-face (and not one it supplies itself) is an ERROR; a timed
# element without class="clip" is a warning. Checked with `hyperframes lint --json`.
LINT_PLANTS = {"clean": {"font": "Inter", "clip": 'class="clip" '},
               "error": {"font": "Plantedfont", "clip": 'class="clip" '},
               "warning": {"font": "Inter", "clip": ""}}


def c_lint(root):
    """TRI-3 through compose.lint_or_stop: clean 0 lines, one error stops the render before `hyperframes render`,
    a warning is one plain line and the render goes on."""
    c, env = compose_mod(), rt.hyperframes_env()
    d = Path(tempfile.mkdtemp(prefix="render-engine-", dir=root))
    projs = {}
    for k, v in LINT_PLANTS.items():
        p = d / k
        (p / "vendor").mkdir(parents=True)
        shutil.copy2(PLUGIN / "runtime" / "gsap" / "gsap.min.js", p / "vendor" / "gsap.min.js")
        shutil.copytree(PLUGIN / "runtime" / "fonts", p / "fonts")
        (p / "index.html").write_bytes((LINT_PAGE % v).encode("utf-8"))
        projs[k] = p
    res = {}
    for k, p in projs.items():
        (ok, lines), _, _ = in_process(c.lint_or_stop, p, f"planted {k}", env)
        print(f"  lint_or_stop(planted {k}) -> ok {ok}, {len(lines)} line(s)")
        for line in lines:
            print("    | " + line)
        res[k] = (ok, lines)
    ok, lines = res["clean"]
    ck("clean project: ok, no lines", ok is True and lines == [], lines)
    ok, lines = res["error"]
    ck("one lint error: not ok, a plain line naming it", ok is False and len(lines) == 1 and lines[0].startswith("✗ ")
       and "[font_family_without_font_face]" in lines[0] and "Traceback" not in lines[0], lines)
    ok, lines = res["warning"]
    ck("warning only: ok + one plain warning line", ok is True and len(lines) == 1 and lines[0].startswith("warning: ")
       and "[timed_element_missing_clip_class]" in lines[0], lines)
    calls, real = [], c.run

    def spy(cmd, env, timeout=None):
        calls.append([str(x) for x in cmd])
        return real(cmd, env, timeout)
    c.run = spy
    try:
        (d / "hf-cache").mkdir()
        args = ["--fps", "25/1", "--frames-cache-dir", d / "hf-cache", "--quality", "draft"]
        _, stop, text = in_process(c.hf_render, projs["error"], d / "error.mp4", env, "planted error", args)
        ran = [x[2] for x in calls if len(x) > 2]
        ck("the render function refuses the error project: exit 1, the line, 'Nothing was rendered.'",
           stop is not None and stop.code == 1 and "[font_family_without_font_face]" in text
           and "Nothing was rendered." in stop.lines, text[-300:])
        ck("... before calling `hyperframes render` (lint ran, render never did; no video written)",
           "lint" in ran and "render" not in ran and not (d / "error.mp4").exists(), ran)
        calls.clear()
        _, stop, text = in_process(c.hf_render, projs["warning"], d / "warning.mp4", env, "planted warning", args)
        ck("the warning project renders, with its plain warning line printed",
           stop is None and (d / "warning.mp4").is_file() and re.search(r"^warning: planted warning: .*"
                                                                       r"\[timed_element_missing_clip_class\]",
                                                                       text, re.M) is not None, text[-300:])
    finally:
        c.run = real
    return d


def plant_mix(reel, report=None):
    """sound/final.mp4 = the cut master's picture (stream copy) + a different track (440 Hz), and its mix-report."""
    cut = reel / "work" / "renders" / "master-100x.mp4"
    snd = reel / "sound"
    snd.mkdir(exist_ok=True)
    final = snd / "final.mp4"
    rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", cut, "-f", "lavfi", "-i",
                   "sine=frequency=440:sample_rate=48000:duration=4", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final])
    if rc != 0:
        raise RuntimeError(f"couldn't make sound/final.mp4: {out[-300:]}")
    rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-i", cut, "-map", "0:v", "-c", "copy", "-f", "md5", "-"])
    wj(snd / "mix-report.json", dict({"pass": True, "video_md5": out.strip(), "final": "final.mp4"}, **(report or {})))
    return final


def c_audio(root):
    """H-S6b-14/-18: the preview carries the mix only when it passed on this exact cut, else the cut's sound + why."""
    ws, reel = make_reel(root, scene=False)
    cut = reel / "work" / "renders" / "master-100x.mp4"
    final = plant_mix(reel)
    prev = reel / "renders" / names()[0]
    cut_a, mix_a = audio_md5(cut), audio_md5(final)
    ck("the planted mix's sound differs from the cut's", cut_a and mix_a and cut_a != mix_a)
    good = json.loads((reel / "sound" / "mix-report.json").read_text(encoding="utf-8"))
    plans = [("a: a passed mix on this cut", {}, "mix", mix_a, None),
             ("b: a mix made on another picture", {"video_md5": "MD5=" + "0" * 32}, "cut", cut_a, "mixed on an older cut"),
             ("c: a mix that didn't pass", {"pass": False}, "cut", cut_a, "didn't pass its check"),
             ("d: no sound folder", None, "cut", cut_a, "hasn't run")]
    for what, change, kind, want, line in plans:
        if change is None:
            shutil.rmtree(reel / "sound")
        else:
            wj(reel / "sound" / "mix-report.json", dict(good, **change))
        rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
        no_traceback(what, out)
        got = audio_md5(prev) if prev.is_file() else ""
        ck(f"{what}: exit 0, JSON audio {kind!r}, the preview's audio packets == the {kind}'s",
           rc == 0 and summary(out).get("audio") == kind and got == want, (rc, summary(out), got, want))
        if line:
            ck(f"{what}: the plain line says {line!r}", re.search(r"^note: the preview uses the cut's own sound: .*"
                                                                + re.escape(line), out, re.M) is not None, out[-300:])
        else:
            ck(f"{what}: no 'cut's own sound' line", "cut's own sound" not in out, out[-300:])
    return ws


def c_licence(root):
    """G4: a mixed bed with no licence row: the preview warns, the Master refuses."""
    ws, reel = make_reel(root, scene=False)
    plant_mix(reel)
    wj(reel / "sound-selection.json", {"bed": {"file": "planted-bed.wav"}})
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("licence preview", out)
    ck("preview: renders with the mix and a plain licence warning line",
       rc == 0 and summary(out).get("audio") == "mix"
       and re.search(r"^warning: the music planted-bed\.wav has no licence row yet", out, re.M) is not None, out[-400:])
    rc, out = compose(ws, "ok", "--reel-dir", f"videos/{REEL}")
    ck("ok: exit 0", rc == 0, out[-200:])
    rc, out = compose(ws, "master", "--reel-dir", f"videos/{REEL}")
    no_traceback("licence master", out)
    mast = reel / "renders" / names()[1]
    ck("master: exit 1 with the licence message, no Master file",
       rc == 1 and "planted-bed.wav has no licence row yet" in out and not mast.exists(), out[-400:])
    return ws


def c_master_older(root):
    """H-S6b-1: an OK of an older preview doesn't let the Master through once a newer preview exists."""
    ws, reel = make_reel(root, scene=False)
    (reel / "renders").mkdir()
    day = (datetime.now() - timedelta(days=2)).strftime("%m.%d.%y")
    older = reel / "renders" / f"{REEL} Preview 720p - {day}.mp4"
    older.write_bytes(b"placeholder")
    t = time.time() - 120
    os.utime(older, (t, t))
    rc, out = compose(ws, "ok", "--reel-dir", f"videos/{REEL}")
    doc = json.loads((reel / "work" / "render-ok.json").read_text(encoding="utf-8")) if rc == 0 else {}
    ck("ok while only the older preview exists: render-ok.json names it", doc.get("preview") == older.name, doc)
    newer = dummy_preview(reel)  # today's name, older than the OK but newer than the other preview
    rc, out = compose(ws, "master", "--reel-dir", f"videos/{REEL}")
    no_traceback("master-older", out)
    ck(f"a newer preview ({newer.name}) exists: Master refused (exit 1, needs your OK), no Master",
       rc == 1 and "needs your OK first" in out and not (reel / "renders" / names()[1]).exists(), out[-300:])
    return ws


def c_hook_limits(root):
    """The hook title: over 70 characters stops plainly; --hook-text replaces the first beat's words."""
    ws, reel = make_reel(root, scene=False)
    long = "Three edits that save hours every single week for busy small studio teams"[:71]
    ck("the planted hook text is 71 characters", len(" ".join(long.split())) == 71, len(long))
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}", "--hook-text", long)
    no_traceback("hook-limits", out)
    ck("71 characters: exit 1, 'the hook line is long', nothing rendered",
       rc == 1 and "hook line is long" in out and not videos_under(reel / "renders", reel / "work" / "render-tmp"),
       out[-300:])
    c, own = compose_mod(), "Your own words up top"
    inp = c.load_inputs(reel)
    c.probe_inputs(inp)
    _, stop, _ = in_process(c.plan, inp, own)
    page = c.main_html(inp, 720, 1280, []) if stop is None else ""
    ck("--hook-text overrides the anchor: the composed HTML carries it, not the first beat's words",
       f'<div id="hook">{own}</div>' in page and HOOK not in page, stop and stop.lines)
    inp = c.load_inputs(reel)
    c.probe_inputs(inp)
    _, stop, _ = in_process(c.plan, inp, long[:70])
    ck("70 characters is still fine", stop is None and inp.get("hook_text") == " ".join(long[:70].split()),
       stop and stop.lines)
    return ws


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(server_py, ws, env, label):
    p = subprocess.Popen([sys.executable, "-X", "utf8", "-I", str(server_py), "--root", str(ws)], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    t = threading.Timer(20, p.kill)  # a hung start fails the case instead of blocking the test
    t.start()
    line = p.stdout.readline().strip()
    t.cancel()
    print(f"  board server ({label}): {line}")
    if not (line.startswith("Editor boards: http://127.0.0.1:") and line.endswith("/")):
        p.kill()
        raise RuntimeError(f"the board server said {line!r}")
    return p, int(line.rsplit(":", 1)[1].rstrip("/"))


def stop_server(p):
    if p.poll() is None:
        p.kill()
        p.wait(10)
    p.stdout.close()


def post_review(port, reel_name):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps({"approve": True, "preview": "x.mp4", "note": "", "sent_at": "2026-11-05T10:00:00Z"}).encode()
    c.request("POST", f"/videos/{reel_name}/__save?board=hub&name=review.json", body=body,
              headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"})
    status = c.getresponse().status
    c.close()
    return status


def c_hub_review(root):
    """H-HUB-1 / H-S6b-16: Approve in a (test-only) Master review tab writes review.json through the board server;
    ok --from-review then records the OK and the Master renders. Without boards.json's line the save is refused."""
    sys.path.insert(0, str(DOCTOR))
    import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)
    ws, reel = make_reel(root, scene=False)
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": free_port()}}))
    ck("editor.config.json written (check_deps.write_config, engine none, nle none)",
       bool(check_deps.write_config(ws, engine=None, nle="none")))
    cfg = rt.read_config(ws)["paths"]
    ck("the config's videos folder is the reel's", ws / cfg["videos"] == reel.parent, cfg)
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    prev = reel / "renders" / names()[0]
    if not ck("a rendered preview", rc == 0 and prev.is_file(), out[-300:]):
        return ws
    hub = ws / cfg["editor"] / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    home = ws / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    ck("no review.json before the click", not (reel / "review.json").exists())
    srv, port = start_server(DOCTOR / "board_server.py", ws, env, "this worktree's plugin")
    try:
        # Startup board_sync installs the real hub; overlay the test fixtures only after it finishes.
        shutil.copyfile(FIXTURES / "review-host.html", hub / "index.html")
        shutil.copyfile(FIXTURES / "master-review.html", hub / "review.html")
        pup = rt.state_dir() / "hyperframes" / "node_modules" / "puppeteer-core" / "lib" / "puppeteer" / "puppeteer-core.js"
        q = f"?reel={REEL}&preview={prev.name.replace(' ', '%20')}"
        dur_js = ("new Promise((res) => { const v = document.getElementById('v'); if (v.error) return res(-1); "
                  "if (v.readyState >= 1) return res(v.duration); v.addEventListener('loadedmetadata', () => "
                  "res(v.duration), {once: true}); v.addEventListener('error', () => res(-1), {once: true}); })")
        job = ws / "job.json"
        wj(job, {"base": f"http://127.0.0.1:{port}", "userDataDir": str(ws / "profile"), "actions": [
            {"do": "goto", "path": "/editor/hub/" + q, "wait": "#tab-review"},
            {"do": "click", "sel": "#tab-review"},
            {"do": "frame", "sel": ".frame iframe", "wait": "#approve"},
            {"do": "eval", "js": dur_js},
            {"do": "click", "sel": "#approve"},
            {"do": "waitText", "sel": "#sendmsg", "re": "written to|FAILED"},
            {"do": "eval", "js": "document.getElementById('sendmsg').textContent"}]})
        t0 = time.perf_counter()
        rc, out = run([rt.tool("node"), CLICK, pup, rt.tool("chrome"), job], timeout=120)
        print(f"  click driver -> exit {rc} in {time.perf_counter() - t0:.1f} s")
        try:
            res = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            res = {}
        ck("the click run finished with no page errors", rc == 0 and not res.get("errors") and not res.get("error"),
           res.get("error") or res.get("errors") or out[-300:])
        reads = res.get("reads") or [None, None]
        print(f"  frame video duration {reads[0]}; save reply {reads[-1]!r}")
        ck("the framed review page plays the preview: duration within 0.1 s of the reel's 4 s",
           isinstance(reads[0], (int, float)) and abs(reads[0] - 4.0) <= 0.1, reads[0])
        saves = [u for u in res.get("requests", []) if "/__save?" in u]
        print(f"  save request(s) the page made: {saves}")
        ck("Approve saved through the board server (board hub, name review.json) and it answered",
           saves == [f"http://127.0.0.1:{port}/videos/{REEL}/__save?board=hub&name=review.json"]
           and reads[-1] == f"written to videos/{REEL}/review.json", (saves, reads[-1]))
    finally:
        stop_server(srv)
    rv = reel / "review.json"
    doc = json.loads(rv.read_text(encoding="utf-8")) if rv.is_file() else {}
    try:
        sent = datetime.fromisoformat(str(doc.get("sent_at")).replace("Z", "+00:00"))
    except ValueError:
        sent = None
    ck("review.json = {approve: true, preview: <the preview>, note: '', sent_at: ISO}",
       set(doc) == {"approve", "preview", "note", "sent_at"} and doc.get("approve") is True
       and doc.get("preview") == prev.name and doc.get("note") == "" and sent is not None, doc)
    rc, out = compose(ws, "ok", "--reel-dir", f"videos/{REEL}", "--from-review")
    okf = reel / "work" / "render-ok.json"
    ok = json.loads(okf.read_text(encoding="utf-8")) if okf.is_file() else {}
    ck("ok --from-review: exit 0, render-ok.json names that preview", rc == 0 and ok.get("preview") == prev.name, ok)
    rc, out = compose(ws, "master", "--reel-dir", f"videos/{REEL}")
    no_traceback("hub-review master", out)
    ck("master after the review OK: the Master exists", rc == 0 and (reel / "renders" / names()[1]).is_file(), out[-300:])
    # the same save without boards.json's line, on a copy of the plugin (the server reads the plugin's boards.json)
    copy = Path(tempfile.mkdtemp(prefix="render-engine-", dir=root)) / PLUGIN.name
    shutil.copytree(PLUGIN, copy, ignore=shutil.ignore_patterns("__pycache__"))
    bj = copy / "skills" / "editor-doctor" / "scripts" / "boards.json"
    text = bj.read_text(encoding="utf-8")
    line = ('"template": "skills/editor-doctor/boards/hub", '
            '"writes": ["review.json", "reel-notes.json", "hub-requests.json"]}')
    ck("the copy's boards.json has the hub line once", text.count(line) == 1)
    bj.write_bytes(text.replace(line, line.replace('"review.json", ', "")).encode("utf-8"))
    before = rv.read_bytes() if rv.is_file() else b""
    srv, port = start_server(copy / "skills" / "editor-doctor" / "scripts" / "board_server.py", ws, env,
                             "a plugin copy without the hub writes line")
    try:
        serving = srv.poll() is None  # the copy's own server, not a hand-off to an older one
        status = post_review(port, REEL)
    finally:
        stop_server(srv)
    ck(f"without the hub writes line (a plugin copy) the save of review.json is refused: HTTP {status}, file unchanged",
       serving and status == 403 and rv.is_file() and rv.read_bytes() == before, (serving, status))
    return ws


def c_rvm_info(root):
    """H-M14, information only (never fails the run): RVM's CPU time on the first 1 s of the real 4K take."""
    take = need_take()
    if take is None:
        print(f"  info: rvm-info needs a real take (--take or EDITOR_SE_TEST_TAKE); got {OPT['take']!r}")
        return None
    d = Path(tempfile.mkdtemp(prefix="render-engine-", dir=root))
    try:
        rate = fpsmod.probe_fps(take)
        clip = d / "first-second.mp4"
        t0 = time.perf_counter()
        rc, out = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", take, "-t", "1", "-map", "0:v:0", "-an",
                       "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                       "-fps_mode", "cfr", "-r", rate, clip])
        print(f"  info: first 1 s at its own size, CFR {rate}: {size(clip)}, {fpsmod.frame_count(clip) if rc == 0 else '-'}"
              f" frames, made in {time.perf_counter() - t0:.1f} s" + ("" if rc == 0 else f" (ffmpeg: {out[-200:]})"))
        if rc != 0:
            return d
        t0 = time.perf_counter()
        rc, out = run([sys.executable, "-X", "utf8", "-I", SCRIPTS / "cutout.py", clip, d / "cutout.mov",
                       "--engine", "rvm", "--tmp", d / "tmp"])
        print(f"  info: cutout.py --engine rvm -> exit {rc} in {time.perf_counter() - t0:.1f} s wall")
        lines = out.strip().splitlines()
        for line in [l for l in lines if l.startswith("info:")] + lines[-1:]:
            print("    | " + line)
    except Exception as e:  # information only
        print(f"  info: rvm-info couldn't finish: {type(e).__name__}: {e}")
    return d


def c_ask(root):
    """H-R36: no edit_style in the Send and none saved: compose stops with the ask line before rendering anything."""
    try:
        saved = json.loads((rt.state_dir() / "styles" / "default.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if not ck("the state's saved style has no edit_style (precondition)", "edit_style" not in saved, saved):
        return None
    ws, reel = make_reel(root, scene=False)
    write_send(reel, [beat("b_001", 0, 50, 0, 4), beat("b_002", 50, 100, 5, 7)], 25, edit_style=None)
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("ask", out)
    ck("no style anywhere: exit 1, the last line is the ask line",
       rc == 1 and out.strip().splitlines()[-1] == compose_mod().styles.ASK, out[-300:])
    ck("nothing rendered, no scale_track.json", not videos_under(reel / "renders", reel / "work" / "render-tmp")
       and not (reel / "work" / "scale_track.json").exists())
    return ws


def preview_of(ws, reel):
    rc, out = compose(ws, "preview", "--reel-dir", f"videos/{REEL}")
    no_traceback("preview", out)
    f = reel / "renders" / names()[0]
    ck("preview exits 0", rc == 0 and f.is_file(), out[-400:])
    return f if f.is_file() else None, out


def c_style_cut(root):
    """Punch-in 1.12: frame cut-1 unscaled, frame cut scaled 1.12 about the zoom centre (hard set, no move)."""
    ws, reel = style_reel(root, MARK_SRC % (25, 6), {"style": "punch-in", "punch_scale": 1.12})
    f, _ = preview_of(ws, reel)
    if f:
        check_scales(f, [(49, 1.0), (50, 1.12), (75, 1.12), (99, 1.12), (100, 1.0)])
    return ws


def c_style_143(root):
    """Segment 1.10 x a planted 1.30 word punch (hard cut) = 1.43 on the hold frame (A5: never max, never capped)."""
    ws, reel = style_reel(root, MARK_SRC % (25, 6), {"style": "punch-in", "punch_scale": 1.10, "moves": {
        "word_punches": {"preset": "dramatic", "shape": "hard-cut", "picks": [5]}}})
    c = compose_mod()
    keep = c.styles.PRESETS["dramatic"]
    c.styles.PRESETS["dramatic"] = dict(keep, peak=1.30)  # the plant: only this process's planner sees it
    try:
        _, stop, text = in_process(c.render, reel, "preview", None)
    finally:
        c.styles.PRESETS["dramatic"] = keep
    no_traceback("style-143", text)
    f = reel / "renders" / names()[0]
    if not ck("preview rendered", stop is None and f.is_file(), text[-300:]):
        return ws
    track = json.loads((reel / "work" / "scale_track.json").read_text(encoding="utf-8"))
    on = round((Fraction("2.10") - Fraction(1, 20)) * 25)
    ck(f"scale_track.json: 1.43 set on the onset frame {on}", any(k["f"] == on and k["scale"] == 1.43
                                                                   for k in track["keys"]), track["keys"])
    check_scales(f, [(49, 1.0), (50, 1.10), (on + 4, 1.43)])
    return ws


def c_layout_cut(root):
    """Layout-switch full -> split exactly on the cut frame 50: frame 49 full, frame 50 split, no in-between."""
    ws, reel = style_reel(root, TESTSRC.replace("duration=4", "duration=6"), {"style": "layout-switch"},
                          ("full", "split", "full"))
    f, _ = preview_of(ws, reel)
    if not f:
        return ws
    cut, w = reel / "work" / "renders" / "master-100x.mp4", 720
    fr, ref = grab(f, [49, 50], "rgb24"), grab(cut, [49, 50], "rgb24", scale=(720, 1280))
    low = slice(400 * w * 3, None)  # below the hook title
    ck(f"frame 49 is full screen (PSNR {psnr(fr[49][low], ref[49][low]):.2f} dB vs the cut master >= 25; Chrome's scaler vs ffmpeg's caps it near 30)",
       psnr(fr[49][low], ref[49][low]) >= 25)
    top, bottom = fr[50][:632 * w * 3], fr[50][640 * w * 3:]  # 8 rows clear of the edge
    ck(f"frame 50 top half (rows 0-631) is the card plate (max channel {max(top)} <= 40, mean {tuple(round(v, 1) for v in mean_rgb(top))})",
       max(top) <= 40)
    want = ref[50][320 * w * 3:960 * w * 3]  # the box shows the video's middle at object-fit: cover
    ck(f"frame 50 bottom half is the video (PSNR {psnr(bottom, want):.2f} dB vs the cut master's middle >= 25)",
       psnr(bottom, want) >= 25)
    return ws


def c_layout_move(root):
    """Layout-switch full -> split in mid-segment (beat edge 75, no cut there): one 15-frame move of the box that
    passes the lint (x/y transforms, never left/top) and renders: the lower-right marker slides down from its full
    place (frame 74) to its split place (frames 90-99) through in-between places, and the cut at 100 is full again."""
    ws, reel = new_reel(root, MARK_SRC % (25, 6), "25", 150)
    wj(reel / "work" / "cuts.json", {"fps": 25, "speed": 1.0, "segments": [
        {"src_in_f": a + 10 * i, "src_out_f": e + 10 * i, "out_in_f": a, "out_out_f": e} for i, (a, e) in enumerate(SEGS3)]})
    write_send(reel, [beat("b_001", 0, 50, 0, 4), beat("b_002", 50, 75, 5, 5), beat("b_003", 75, 100, 6, 6, layout="split"),
                      beat("b_004", 100, 150, 7, 7)], 25, {"style": "layout-switch"})
    f, out = preview_of(ws, reel)
    ck("the preview's lint: 0 errors", "info: lint preview (720x1280): 0 errors," in out, out[-400:])
    tp = reel / "work" / "scale_track.json"
    tw = json.loads(tp.read_text(encoding="utf-8"))["tweens"] if tp.is_file() else []
    ck("scale_track.json plans the move: layout full -> split, frames 75-90",
       [(m["prop"], m["start_f"], m["end_f"], m["from"], m["to"]) for m in tw] == [("layout", 75, 90, "full", "split")], tw)
    if not f:
        return ws
    w, h, ns = 720, 1280, (74, 75, 80, 85, 90, 99, 100)
    fr = grab(f, ns)

    def marker_y(g):  # the lower-right square (x 560 at 720 wide) in the bottom half, clear of the card plate
        ys = [y for y in range(h // 2, h) for v in g[y * w + 500:y * w + 620] if v > 128]
        return sum(ys) / len(ys) if ys else None
    y = {n: marker_y(fr[n]) for n in ns}
    full, split = 1400 * h / 1920, 1400 * h / 1920 + 320  # split: the box's video is the frame's middle, 320 px lower
    ck(f"frames 74, 75 and 100: the marker at its full place {full:.0f} (within 2 px): {y[74]}, {y[75]}, {y[100]}",
       all(y[n] is not None and abs(y[n] - full) <= 2 for n in (74, 75, 100)), y)
    ck(f"frames 90 and 99: the marker at its split place {split:.0f} (within 2 px): {y[90]}, {y[99]}",
       all(y[n] is not None and abs(y[n] - split) <= 2 for n in (90, 99)), y)
    ck(f"frames 80 and 85 are in between and in order: {y[80]}, {y[85]}",
       None not in (y[80], y[85]) and full + 2 < y[80] < y[85] < split - 2, y)
    return ws


def c_split_top(root):
    """Split (hard rule): the card plate fills the top half, the video the bottom half (pixel probes, frame 125)."""
    ws, reel = style_reel(root, GREY_SRC, {"style": "layout-switch"}, ("full", "full", "split"))
    f, _ = preview_of(ws, reel)
    if not f:
        return ws
    w, n = 720, 125
    fr = grab(f, [n], "rgb24")[n]
    ref = grab(reel / "work" / "renders" / "master-100x.mp4", [n], "rgb24", scale=(720, 1280))[n]

    def px(img, x, y):
        return tuple(img[(y * w + x) * 3:(y * w + x) * 3 + 3])
    probes = [(x, y) for y in (4, 160, 320, 480, 628) for x in (4, 360, 715)]
    plate = [px(fr, x, y) for x, y in probes]
    ck(f"{len(probes)} probes in the top half (rows 4-628) show the plate {PLATE} (each channel within 12)",
       all(abs(a - b) <= 12 for p in plate for a, b in zip(p, PLATE)), plate)
    vid = [(px(fr, x, y), px(ref, x, y - 320)) for y in (652, 800, 960, 1120, 1275) for x in (40, 360, 680)]
    ck("15 probes in the bottom half (rows 652-1275) show the video (each channel within 12 of the cut master)",
       all(abs(a - b) <= 12 for g, r in vid for a, b in zip(g, r)), vid)
    return ws


def c_pip_above(root):
    """Pip: the pill's box paints above its card plate: pixels inside the pill are video, around it the plate."""
    ws, reel = style_reel(root, GREY_SRC, {"style": "layout-switch"}, ("full", "pip", "full"))
    f, _ = preview_of(ws, reel)
    if not f:
        return ws
    n, s = 75, 720 / 1080
    x, y, bw, bh = (v * s for v in (738, 28, 312, 555))
    cx, cy = round(x + bw / 2), round(y + bh / 2)
    inside = mean_rgb(grab(f, [n], "rgb24", crop=(cx - 40, cy - 60, 80, 120))[n])
    video = mean_rgb(grab(reel / "work" / "renders" / "master-100x.mp4", [n], "rgb24", scale=(720, 1280),
                          crop=(cx - 40, cy - 60, 80, 120))[n])
    around = mean_rgb(grab(f, [n], "rgb24", crop=(100, 700, 200, 200))[n])
    ck(f"inside the pill: video {tuple(round(v, 1) for v in inside)} (cut master {tuple(round(v, 1) for v in video)}, "
       f"each channel within 6), not the plate", all(abs(a - b) <= 6 for a, b in zip(inside, video)), (inside, video))
    ck(f"around the pill: the card plate {tuple(round(v, 1) for v in around)} (within 6 of {PLATE})",
       all(abs(a - b) <= 6 for a, b in zip(around, PLATE)), around)
    return ws


def c_style_fps(root):
    """A 30000/1001 master under a 29.97 cut list: scale_track.json fps == compose's fps string, and the punch-in
    still lands exactly on the cut frame (style times come from the exact Fraction)."""
    ws, reel = style_reel(root, MARK_SRC % ("30000/1001", 5.005), {"style": "punch-in", "punch_scale": 1.12},
                          rate="30000/1001", cut_fps=29.97)
    f, out = preview_of(ws, reel)
    tp = reel / "work" / "scale_track.json"
    track = json.loads(tp.read_text(encoding="utf-8")) if tp.is_file() else {}
    ck(f"scale_track.json fps {track.get('fps')!r} == compose's {summary(out).get('fps')!r} == '30000/1001'",
       track.get("fps") == summary(out).get("fps") == "30000/1001", (track.get("fps"), summary(out)))
    if f:
        check_scales(f, [(49, 1.0), (50, 1.12), (99, 1.12), (100, 1.0)])
    return ws


CASES = {"broll": c_broll, "broll-blocks": c_broll_blocks, "broll-ai": c_broll_ai,
         "broll-recording-paths": c_broll_recording_paths,
         "selftest": c_selftest, "preview": c_preview, "master-refused": c_master_refused, "master": c_master,
         "gate-block": c_gate_block, "bad-input": c_bad_input, "joi-frames": c_joi_frames, "colour": c_colour,
         "frame0": c_frame0, "frame0-scene": c_frame0_scene, "cut-span-block": c_cut_span_block, "lint": c_lint,
         "scene-no-params": c_scene_no_params, "audio": c_audio,
         "licence": c_licence, "master-older": c_master_older, "hook-limits": c_hook_limits,
         "hub-review": c_hub_review, "ask": c_ask, "style-cut": c_style_cut, "style-143": c_style_143,
         "layout-cut": c_layout_cut, "layout-move": c_layout_move, "split-top": c_split_top, "pip-above": c_pip_above, "style-fps": c_style_fps,
         "rvm-info": c_rvm_info}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", action="append", choices=list(CASES), help="case to run (repeatable); default all")
    ap.add_argument("--tmp", help="folder for the fixtures (default: next to the state folder)")
    ap.add_argument("--take", help="a real talking-head take for joi-frames and rvm-info (default: env "
                                   "EDITOR_SE_TEST_TAKE); read only")
    ap.add_argument("--out", help="folder for the outputs a case keeps, e.g. frame0's PNGs (default: render-out "
                                  "next to the fixtures)")
    a = ap.parse_args()
    home = os.environ.get("EDITOR_SE_HOME")
    root = Path(a.tmp or (Path(home).parent if home else tempfile.gettempdir()))
    OPT["take"] = a.take or os.environ.get("EDITOR_SE_TEST_TAKE") or None
    OPT["out"] = Path(a.out or root / "render-out")
    free = shutil.disk_usage(root).free / 2 ** 30
    if free < MIN_FREE_GB:
        print(f"FAIL only {free:.1f} GB free disk; renders need {MIN_FREE_GB} GB. Free some space and run again.")
        return 1
    for name in a.case or list(CASES):
        print(f"== {name}", flush=True)
        t0, ws = time.perf_counter(), None
        try:
            ws = CASES[name](root)
        except Exception as e:  # a crash is a failed check, never a pass
            ck(f"{name}: test run", False, f"stopped: {type(e).__name__}: {e}")
        finally:
            for d in root.glob("render-engine-*"):
                shutil.rmtree(d, ignore_errors=True)
            if name != "selftest":
                ck(f"{name}: no warmCheck.js left running", warm_left() == 0)
        print(f"== {name} took {time.perf_counter() - t0:.1f} s", flush=True)
    print("%d failed" % len(fails) if fails else "all passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
