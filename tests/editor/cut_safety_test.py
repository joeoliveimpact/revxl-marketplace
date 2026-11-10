#!/usr/bin/env python3
"""S4b.1 check for reel-first-cuts' cut safety: beats after punctuation kept (F-1), whole words at cut edges
and short pieces that hold speech (F-2), frame-exact cuts (F-3), no digital-zero runs at a concat (F-15),
click guards at interior cuts (VU-4), the -/filter_complex flag (F-6), the missing cuts.json stop (H-R2) and the
editor's own ffmpeg/ffprobe, never PATH's (SC5).

usage: python tests/editor/cut_safety_test.py <scratch-dir> [--case NAME]
                                              [--take REEL_018 take1] [--s3-work its S3 work folder] [--vfr iPhone.mp4]
The real take (frames, frames-master, zeros, tools) comes from --take, else the env var EDITOR_SE_TEST_TAKE.
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case (each one runs in under 150 s);
without it every case runs. Cases: beat, beat-real, edge, island, internal-word, frames, frames-phone, zeros, pop,
filtercomplex, cuts-missing, tools, frames-master.

H-LOCK-1: pop, filtercomplex, frames, frames-phone, zeros and tools render TINY (360x640, at most 10 s) through render.py's own main(),
with no heavy_lock; they run one at a time and exit 76 below 1 GB free RAM. frames-master is the one real 1080x1920
render: run it under heavy_lock.py --min-gb 3.

Tools come from the editor state folder (EDITOR_SE_HOME, else the default): its ffmpeg/ffprobe and its venv
Python, which runs every script as `python -X utf8 -I`. Synthetic media carry a planted, known answer wherever
a case needs one; the real fixtures are read only (the 10 s CFR excerpts and the 10 s VFR copy are cut into the
scratch dir).
"""
import argparse, array, contextlib, ctypes, importlib.util, io, json, math, os, random, re, shutil, struct, subprocess, sys, time, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-first-cuts" / "scripts"
sys.path.insert(0, str(REPO / "plugins" / "editor-superengine" / "skills" / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

ENV = rt.python_env()                 # the state's ffmpeg first on PATH
os.environ["PATH"] = ENV["PATH"]      # the in-process render (pop, filtercomplex) finds the same ffmpeg
PY = rt.tool("python") if Path(rt.tool("python")).exists() else sys.executable

TAKE = os.environ.get("EDITOR_SE_TEST_TAKE", "")   # the real take: --take or this env var, never a path in this file
S3_WORK = r"C:/Work/_scratch/editor-superengine-0.2.0/a2/s3-full2/take/work"
VFR = r"C:/Workspaces/Content Studio/input/editor-tests/iPhone.mp4"
TINY_VF, TINY_SRC = "scale=360:640", "640:360"   # H-LOCK-1: the tiny renders' picture, and their CFR source size

SR = 48000
# the planted take: tone "words" at known times over -63 dB noise. 'connect.' and 'really' are each followed by
# 0.6 s of silence; 'yes' is the lone short word the island case keeps
WORDS = [("We", 0.50, 0.80), ("can", 0.95, 1.25), ("connect.", 1.40, 1.85), ("And", 2.45, 2.75),
         ("really", 2.90, 3.30), ("go", 3.90, 4.25), ("yes", 5.00, 5.20), ("ok", 6.50, 6.80)]
SYN_DUR = 7.5
GUARD = 0.070                         # gaps.py's default --guard
PUNCT = (",", ";", ":", ".", "?", "!", "\u2026", "\u2014")
MARKERS = {"first", "second", "third", "fourth", "fifth", "next", "then", "finally", "lastly", "also",
           "one", "two", "three", "four", "five"}
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def sh(cmd, cwd=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=ENV, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)


def run(name, *args, cwd=None):
    return sh([PY, "-X", "utf8", "-I", SCRIPTS / name] + list(args), cwd=cwd)


def ff(*args):
    p = sh(["ffmpeg", "-y", "-v", "error"] + list(args))
    if p.returncode:
        raise SystemExit("fixture ffmpeg failed: %s" % p.stderr[-800:])


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def module(name):
    spec = importlib.util.spec_from_file_location(Path(name).stem, SCRIPTS / name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fresh(S, name):
    d = S / name
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    return d


def is_protected(word):
    t = word.strip()
    bare = re.sub(r"\W+$", "", t.lower())
    return t.endswith(PUNCT) or bare in MARKERS or bare.isdigit()


def kept_in(cuts, a, b):
    """Seconds of [a, b] the cut list keeps."""
    fps = cuts["fps"]
    return sum(max(0.0, min(b, s["src_out_f"] / fps) - max(a, s["src_in_f"] / fps)) for s in cuts.get("segments", []))


def covers(cuts, a, b):
    fps = cuts["fps"]
    return next((s for s in cuts.get("segments", []) if s["src_in_f"] / fps <= a and s["src_out_f"] / fps >= b), None)


def free_gb():
    if os.name != "nt":
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2 ** 30

    class MS(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("tot", "avail", "totpf", "availpf", "totv", "availv", "ext")]
    m = MS()
    m.len = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2 ** 30


def need_ram():
    """H-LOCK-1: a tiny render skips heavy_lock, so it checks RAM itself: below 1 GB free it refuses, exit 76."""
    gb = free_gb()
    if gb < 1.0:
        print("REFUSED: %.2f GB free RAM < 1.0 GB, so this case is unproven (RAM)" % gb)
        sys.exit(76)


def pcm(path):
    """The first audio stream decoded to float32 mono at its own rate: (samples, rate)."""
    p = sh(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
            "-of", "csv=p=0", path])
    sr = int(p.stdout.split()[0])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-c:a", "pcm_f32le",
                          "-f", "f32le", "-"], env=ENV, capture_output=True, timeout=600).stdout
    x = array.array("f")
    x.frombytes(raw[:len(raw) // 4 * 4])
    return x, sr


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(struct.pack("<%dh" % len(x), *(max(-32767, min(32767, int(round(v * 32767)))) for v in x)))


def mux(d, wav, dur, name):
    out = d / name
    ff("-f", "lavfi", "-i", "color=c=gray:s=320x240:r=30:d=%s" % dur, "-i", wav, "-map", "0:v", "-map", "1:a",
       "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "pcm_s16le", "-shortest", out)
    return out


def synth_words(d):
    """The planted take (WORDS) as a .mov with PCM audio, and its hand-written edit map."""
    rnd, n, ramp = random.Random(18), int(SYN_DUR * SR), int(0.005 * SR)
    x = [rnd.gauss(0.0, 0.0007) for _ in range(n)]
    for _, s, e in WORDS:
        a, b = round(s * SR), round(e * SR)
        for j in range(a, b):
            g = max(0.0, min(1.0, (j - a) / ramp, (b - 1 - j) / ramp))
            x[j] += 0.3 * (0.5 - 0.5 * math.cos(math.pi * g)) * math.sin(2 * math.pi * 220 * (j - a) / SR)
    write_wav(d / "words.wav", x)
    em = d / "edit_map.json"
    em.write_text(json.dumps({"words": [{"id": "w_%04d" % k, "word": w, "start": s, "end": e, "parakeet_start": s,
                                         "status": "aligned"} for k, (w, s, e) in enumerate(WORDS)]}), encoding="utf-8")
    return mux(d, d / "words.wav", SYN_DUR, "words.mov"), em


def synth_step(d):
    """3 s whose audio sits at +0.3 for the first half and -0.3 for the second (a quiet 440 Hz tone on top):
    pieces cut from each half meet at a hard 0.6 step."""
    n = int(3.0 * SR)
    x = [(0.3 if j < n // 2 else -0.3) + 0.02 * math.sin(2 * math.pi * 440 * j / SR) for j in range(n)]
    write_wav(d / "step.wav", x)
    return mux(d, d / "step.wav", 3.0, "step.mov")


def excerpt(S, take, size):
    """The CFR fixture: 10 s of REEL_018 take1 (26-36 s, where it talks) at 30 fps and `size` (w:h), cut once into
    the scratch dir."""
    out = S / "fixtures" / ("reel018-take1-10s-%s.mp4" % size.replace(":", "x"))
    if not out.exists():
        need_ram()
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name("_partial.mp4")
        ff("-ss", "26", "-t", "10", "-i", real_take(take), "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=" + size,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-fps_mode", "cfr", "-r", "30",
           "-c:a", "aac", "-b:a", "192k", tmp)
        tmp.replace(out)
    return out


def real_take(take):
    """The real take a fixture is cut from (--take, else EDITOR_SE_TEST_TAKE); a plain stop when it is missing."""
    if not take or not Path(take).is_file():
        raise SystemExit("this case needs a real take: pass --take <take.mp4> or set EDITOR_SE_TEST_TAKE")
    return take


def vfr_excerpt(S, vfr):
    """The VFR fixture: the first 10 s of iPhone.mp4, stream-copied so its frame times stay as shot (24 fps for
    the first 0.74 s, near 30 after)."""
    out = S / "fixtures" / "iphone-vfr-10s.mp4"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name("_partial.mp4")
        ff("-i", vfr, "-t", "10", "-map", "0:v:0", "-map", "0:a:0", "-c", "copy", tmp)
        tmp.replace(out)
    return out


def probe(src, w):
    p = run("probe.py", src, "-o", w)
    ck("probe.py reads %s" % Path(src).name, p.returncode == 0, p.stderr[-300:])
    return p.returncode == 0


def edl_file(w, cuts):
    f = w / "edl.json"
    f.write_text(json.dumps([{"src_in": a, "src_out": b} for a, b in cuts]), encoding="utf-8")
    return f


# ------------------------------------------------------------------------------------------- cases
def case_beat(S, a):
    """F-1 on the planted take: the silence after 'connect.' is a beat, the one after 'really' is not."""
    d = fresh(S, "beat")
    w = d / "work"
    mov, em = synth_words(d)
    if not probe(mov, w):
        return
    edl = edl_file(w, [(0.3, 4.5)])
    f = 1.0 / load(w / "probe.json")["out_rate"]
    s1, s2 = (1.85, 2.45), (3.30, 3.90)

    def go(*extra, cwd=d):
        p = run("gaps.py", w, "--edl", edl, *extra, cwd=cwd)
        c = load(w / "cuts.json") if p.returncode == 0 else {"fps": 30.0}
        return p, kept_in(c, *s1), kept_in(c, *s2), text(w / "gap-plan.txt") if p.returncode == 0 else ""

    p, k1, k2, plan = go("--words", em)
    ck("F-1: with --words the 0.6 s silence after 'connect.' keeps 0.300 s +-1 frame (kept %.3f)" % k1,
       p.returncode == 0 and abs(k1 - 0.300) <= f + 1e-6, p.stderr[-300:])
    ck("F-1: the 0.6 s silence after 'really' (not protected) is capped at 0.150 s +-1 frame (kept %.3f)" % k2,
       p.returncode == 0 and abs(k2 - 0.150) <= f + 1e-6)
    ck("F-1: gap-plan.txt has the DECISIONS line for the kept beat",
       re.search(r"BEAT kept 0\.300s after 'connect\.' at 1\.85", plan) is not None,
       [l for l in plan.splitlines() if "BEAT" in l])
    p, k1, k2, plan = go()
    ck("F-1 control: without --words both silences are capped at 0.150 s +-1 frame (kept %.3f, %.3f)" % (k1, k2),
       p.returncode == 0 and abs(k1 - 0.150) <= f + 1e-6 and abs(k2 - 0.150) <= f + 1e-6 and "BEAT" not in plan,
       p.stderr[-300:])
    client = d / "client"
    (client / "editor").mkdir(parents=True)
    (client / "editor" / "editor.config.json").write_text(json.dumps({"cuts": {"beat_ms": 350}}), encoding="utf-8")
    p, k1, _, plan = go("--words", em, cwd=client)
    ck("F-1: editor.config.json cuts.beat_ms 350 is honoured (kept %.3f, want 0.350 +-1 frame)" % k1,
       p.returncode == 0 and abs(k1 - 0.350) <= f + 1e-6, p.stderr[-300:])
    p, k1, _, plan = go("--words", em, "--beat", "0.25", cwd=client)
    ck("F-1: --beat 0.25 is honoured over the config (kept %.3f, want 0.250 +-1 frame)" % k1,
       p.returncode == 0 and abs(k1 - 0.250) <= f + 1e-6, p.stderr[-300:])


def case_beat_real(S, a):
    """F-1 on REEL_018's edit map (Parakeet punctuation) with an EDL of the whole take."""
    d = fresh(S, "beat-real")
    w = d / "work"
    for n in ("probe.json", "envelope.json", "edit_map.json"):
        shutil.copy(Path(a.s3_work) / n, w / n)
    em = load(w / "edit_map.json")
    dur = em["duration"]
    p = run("gaps.py", w, "--edl", edl_file(w, [(0.0, dur)]), "--words", w / "edit_map.json", cwd=d)
    ck("gaps.py --words runs on REEL_018", p.returncode == 0, p.stderr[-300:])
    if p.returncode:
        return
    gaps = module("gaps.py")          # Env only: the envelope's silences, the measurement gaps.py cuts by
    envj, pj = load(w / "envelope.json"), load(w / "probe.json")
    env = gaps.Env(envj["db"], envj["win_s"], pj["calibration"])
    words = [x for x in em["words"] if x.get("status") != "unresolved"]
    cuts = load(w / "cuts.json")
    beats = {round(float(t), 2): float(k) for k, t in
             re.findall(r"BEAT kept ([\d.]+)s after '.*?' at ([\d.]+)", text(w / "gap-plan.txt"))}
    found, short_plan, short_out, least = 0, [], [], 9.0
    for ga, gb in env.silences(*env.speech_bounds(0.0, dur), 0.100):
        pw = next((x for x in reversed(words) if x["end"] <= ga + 0.03), None)
        if gb - ga < 0.300 or not pw or not is_protected(pw["word"]):
            continue
        found += 1
        kp, ko = beats.get(round(ga, 2)), kept_in(cuts, ga, gb)
        least = min(least, ko)
        if kp is None or kp < 0.2995:
            short_plan.append((round(ga, 2), pw["word"], kp))
        if ko < 0.300 - 1.0 / cuts["fps"] - 1e-6:
            short_out.append((round(ga, 2), pw["word"], round(ko, 3)))
    ck("F-1 on REEL_018: all %d silences of 0.3 s+ after a protected word keep 0.3 s+ in the plan" % found,
       found > 0 and not short_plan, short_plan[:6])
    ck("F-1 on REEL_018: and in cuts.json, within the one-frame snap (least kept %.3f s)" % least,
       found > 0 and not short_out, short_out[:6])


def case_edge(S, a):
    """F-2: an EDL src_out planted 40 ms inside 'connect.' (1.40-1.85)."""
    d = fresh(S, "edge")
    w, ctl = d / "work", d / "control"
    ctl.mkdir()
    mov, em = synth_words(d)
    if not probe(mov, w):
        return
    raw = [(0.3, 1.81), (2.40, 4.5)]
    edl = edl_file(w, raw)
    shutil.copy(w / "envelope.json", ctl / "envelope.json")
    (ctl / "segments.json").write_text(json.dumps(raw), encoding="utf-8")
    p = run("boundary_audit.py", ctl, em, cwd=d)
    ck("F-2 control: boundary_audit on the raw EDL (before gaps.py) exits 1, an edge inside 'connect.'",
       p.returncode == 1 and "INSIDE 'connect.'" in p.stdout, (p.returncode, p.stdout[-300:], p.stderr[-300:]))
    p = run("gaps.py", w, "--edl", edl, "--words", em, cwd=d)
    plan, cuts = text(w / "gap-plan.txt"), load(w / "cuts.json")
    ck("F-2: gaps.py logs EDGE moved to keep 'connect.'", p.returncode == 0 and "EDGE moved to keep 'connect.'" in plan,
       p.stderr[-300:])
    seg = covers(cuts, 1.40, 1.85) if cuts else None
    ck("F-2: the output keeps the whole word 'connect.' (1.40-1.85 s)", seg is not None, cuts.get("segments"))
    lim = 1.85 + GUARD + 0.5 / 30
    ck("F-2: the edge went past the EDL by at most the word plus the guard (out %.3f <= %.3f)"
       % (seg["src_out_f"] / cuts["fps"] if seg else -1, lim), seg is not None and seg["src_out_f"] / cuts["fps"] <= lim)
    p = run("boundary_audit.py", w, em, cwd=d)
    ck("F-2: boundary_audit exits 0 on gaps.py's segments", p.returncode == 0, (p.stdout[-400:], p.stderr[-300:]))


def case_island(S, a):
    """F-2: a 0.3 s lone EDL cut holding 'yes' is kept; a silent lone cut goes, with a log line. The silent cut
    (5.60-5.72) is 0.12 s: too short for an internal deletion (needs more than 2 x 0.075 + 0.02 s of silence) and,
    with no speech inside, it has no head or tail for a join to take, so no deletion can absorb it as a runt and
    only the short-piece rule can drop it."""
    d = fresh(S, "island")
    w = d / "work"
    mov, em = synth_words(d)
    if not probe(mov, w):
        return
    edl = edl_file(w, [(0.3, 1.33), (4.95, 5.25), (5.6, 5.72), (6.3, 7.0)])
    p = run("gaps.py", w, "--edl", edl, "--words", em, cwd=d)
    plan, cuts = text(w / "gap-plan.txt"), load(w / "cuts.json")
    ck("gaps.py runs on the island EDL", p.returncode == 0, p.stderr[-300:])
    if p.returncode:
        return
    ck("F-2: the 0.3 s lone cut holding 'yes' (5.00-5.20) is in cuts.json", covers(cuts, 5.00, 5.20) is not None,
       cuts.get("segments"))
    ck("F-2: and gap-plan.txt logs it: KEPT short piece (holds speech)",
       re.search(r"cut2\s+KEPT short piece .*\(holds speech\)", plan) is not None,
       [l for l in plan.splitlines() if "cut2" in l])
    silent = kept_in(cuts, 5.6, 5.72)
    ck("F-2: the silent 0.12 s lone cut (5.60-5.72) is dropped from cuts.json (kept %.3f s)" % silent,
       silent == 0, cuts.get("segments"))
    ck("F-2: and gap-plan.txt logs it: DROPPED short piece 0.120s at 5.600 (silent)",
       re.search(r"cut3\s+DROPPED short piece 0\.120s at 5\.600 \(silent\)", plan) is not None,
       [l for l in plan.splitlines() if "cut3" in l])


def case_internal_word(S, a):
    """F-2: an edit-map word inside an internal deletion is kept. 'um' (3.55-3.65) sits in the 0.6 s silence after
    'really' with no audio planted, a soft word the envelope reads as silence: only the edit map names it."""
    d = fresh(S, "internal-word")
    w = d / "work"
    mov, em = synth_words(d)
    if not probe(mov, w):
        return
    m = load(em)
    m["words"].append({"id": "w_0099", "word": "um", "start": 3.55, "end": 3.65, "parakeet_start": 3.55,
                       "status": "aligned"})
    m["words"].sort(key=lambda x: x["start"])
    em.write_text(json.dumps(m), encoding="utf-8")
    edl, s2 = edl_file(w, [(0.3, 4.5)]), (3.30, 3.90)
    p = run("gaps.py", w, "--edl", edl, cwd=d)
    c0 = load(w / "cuts.json") if p.returncode == 0 else {"fps": 30.0}
    ck("F-2 control: without --words the internal deletion takes 'um' (kept %.3f of 3.55-3.65)"
       % kept_in(c0, 3.55, 3.65), p.returncode == 0 and kept_in(c0, 3.55, 3.65) < 0.05, p.stderr[-300:])
    p = run("gaps.py", w, "--edl", edl, "--words", em, cwd=d)
    plan, cuts = text(w / "gap-plan.txt"), load(w / "cuts.json") if p.returncode == 0 else {"fps": 30.0}
    ck("F-2: with --words the whole word 'um' (3.55-3.65) is in cuts.json", p.returncode == 0
       and covers(cuts, 3.55, 3.65) is not None, (cuts.get("segments"), p.stderr[-300:]))
    ck("F-2: gap-plan.txt logs the internal deletion SHRUNK or VETO (word 'um' inside)",
       re.search(r"internal\s+(SHRUNK [\d.]+ -> [\d.]+ s|VETO) \(word 'um' inside\)", plan) is not None,
       [l for l in plan.splitlines() if "3.3" in l or "'um'" in l])
    ck("F-2: the deletion shrank, never widened (silence 3.30-3.90 keeps %.3f s, the control kept %.3f s)"
       % (kept_in(cuts, *s2), kept_in(c0, *s2)), kept_in(cuts, *s2) >= kept_in(c0, *s2) - 1e-6)


def consistent(c):
    """cuts.json's integers: lengths add up, the out ranges run contiguously from 0, out = round(S / speed)."""
    segs, keys = c.get("segments") or [], ("src_in_f", "src_out_f", "out_in_f", "out_out_f")
    ok = bool(segs) and all(type(s.get(k)) is int for s in segs for k in keys)
    S, prev = 0, 0
    for s in segs if ok else ():
        n = s["src_out_f"] - s["src_in_f"]
        ok = ok and n > 0 and s["out_in_f"] == prev == round(S / c["speed"]) \
            and s["out_out_f"] == round((S + n) / c["speed"])
        S, prev = S + n, s["out_out_f"]
    return ok and segs[-1]["out_out_f"] == round(S / c["speed"])


def plan(S, label, src, cuts_s, speed, *extra):
    """probe -> gaps (3-cut EDL) at `speed`, plus any `extra` gaps.py flags. Returns (work, cuts.json), cuts empty
    when probe failed."""
    d = fresh(S, label)
    w = d / "work"
    if not probe(src, w):
        return w, {}
    p = run("gaps.py", w, "--edl", edl_file(w, cuts_s), "--speed", speed, *extra, cwd=d)
    ck("%s: gaps.py --speed %s runs" % (label, speed), p.returncode == 0, p.stderr[-300:])
    return w, load(w / "cuts.json")


def tiny_render(w, src):
    """A TINY master (H-LOCK-1): render.py's own main() - cuts.json, build_graph(), the -/filter_complex encode
    and its frame-count assert - run in-process with conform() swapped for TINY_VF, so the picture is 360x640.
    Returns (exit code, render.py's stderr, master path, frames counted by render.py's count_frames)."""
    need_ram()
    render, argv, err = module("render.py"), sys.argv, io.StringIO()
    render.conform = lambda video: TINY_VF
    sys.argv = ["render.py", str(w), str(src), "--master"]
    try:
        with contextlib.redirect_stderr(err):
            render.main()
        rc = 0
    except SystemExit as e:
        rc = e.code
    finally:
        sys.argv = argv
    master = w / "renders" / ("master-%s.mp4" % ("%.2fx" % load(w / "cuts.json").get("speed", 1.0)).replace(".", ""))
    return rc, err.getvalue(), master, render.count_frames(master)


SOURCES = {"cfr": [(0.3, 3.0), (3.7, 6.4), (7.1, 9.7)], "vfr": [(0.2, 3.0), (3.6, 6.4), (7.0, 9.8)]}


def case_frames(S, a):
    """F-3: rendered frame count == the last out_out_f, exactly, on CFR and VFR sources at 1.0x and 1.15x. A
    segments.json that differs from cuts.json (its last piece gone) is planted before each render, so a render.py
    that takes its times from segments.json fails here."""
    for label, src in (("cfr", excerpt(S, a.take, TINY_SRC)), ("vfr", vfr_excerpt(S, a.vfr))):
        for speed in (1.0, 1.15):
            w, cuts = plan(S, "frames-%s-%s" % (label, speed), src, SOURCES[label], speed)
            if not cuts:
                continue
            segs = load(w / "segments.json")
            ck("H-R2 %s %.2fx: segments.json is cuts.json in seconds" % (label, speed),
               len(segs) == len(cuts["segments"]) and all(
                   abs(x - s["src_in_f"] / cuts["fps"]) < 1e-6 and abs(y - s["src_out_f"] / cuts["fps"]) < 1e-6
                   for (x, y), s in zip(segs, cuts["segments"])), segs)
            planted = [[s["src_in_f"] / cuts["fps"], s["src_out_f"] / cuts["fps"]] for s in cuts["segments"][:-1]]
            (w / "segments.json").write_text(json.dumps(planted), encoding="utf-8")
            rc, err, _, got = tiny_render(w, src)
            want = cuts["segments"][-1]["out_out_f"]
            ck("F-3 %s %.2fx: the master has exactly the last out_out_f frames (%d rendered, %d in cuts.json; "
               "segments.json planted with %d of %d pieces)" % (label, speed, got, want, len(planted),
                                                               len(cuts["segments"])),
               rc == 0 and got == want, (rc, err[-400:]))
            ck("F-3 %s %.2fx: cuts.json integers are consistent (lengths add up, out ranges contiguous from 0)"
               % (label, speed), consistent(cuts), cuts.get("segments"))


# iPhone.mp4: the frame before 4.000 s runs to 4.018 s, the one before 8.000 s from 7.987 to 8.020 s. Piece 1
# starts on a source frame (0.000), so its last frame overshoots by over half a frame and fps= used to add one.
# 204 kept frames: at 1.15x one extra frame also moves the output (177 -> 178), so neither speed hides it
PHONE = [(0.0, 4.0), (5.2, 8.0)]


def overrun(src, t):
    """How far (s) the last source frame that starts before t runs past t, from ffprobe's frame times."""
    p = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "frame=best_effort_timestamp_time,duration_time", "-of", "csv=p=0", src])
    ends = []
    for line in p.stdout.split():
        try:
            pts, dur = (float(v) for v in line.strip(",").split(",")[:2])
        except ValueError:
            continue
        if pts < t - 1e-6:
            ends.append((pts, pts + dur))
    return max(ends)[1] - t if ends else 0.0


def case_frames_phone(S, a):
    """F-3 on real phone footage (H-S4b-12): the VFR iPhone excerpt, two kept pieces with an interior cut, the
    second ending at 8.000 s where a source frame runs past the trim end. fps= used to emit one frame more there
    (241 for 240), so render.py's own assert refused the render. The master must hold exactly the last
    out_out_f frames, at 1.0x and 1.15x. gaps.py's --hold keeps the planted pieces whole (no lead trim)."""
    src = vfr_excerpt(S, a.vfr)
    for speed in (1.0, 1.15):
        w, cuts = plan(S, "frames-phone-%s" % speed, src, PHONE, speed, "--hold", "0:10")
        if not cuts:
            continue
        fps, segs = cuts["fps"], cuts["segments"]
        ends = [(s["src_out_f"], overrun(src, s["src_out_f"] / fps)) for s in segs]
        ck("phone %.2fx: cuts.json holds the planted pieces, and one ends at 8.000 s where a source frame runs "
           "past it (end frame, overrun ms: %s)" % (speed, ", ".join("%d %.1f" % (f, o * 1e3) for f, o in ends)),
           [[s["src_in_f"], s["src_out_f"]] for s in segs] == [[round(x * fps), round(y * fps)] for x, y in PHONE]
           and any(f == round(8.0 * fps) and o > 1e-3 for f, o in ends), segs)
        rc, err, _, got = tiny_render(w, src)
        want = segs[-1]["out_out_f"]
        ck("F-3 phone %.2fx: render.py's own frame-count assert passes" % speed, rc == 0, err[-400:])
        ck("F-3 phone %.2fx: the master has exactly the last out_out_f frames (%d rendered, %d in cuts.json)"
           % (speed, got, want), got == want, (rc, err[-400:]))
        ck("F-3 phone %.2fx: cuts.json integers are consistent (lengths add up, out ranges contiguous from 0)"
           % speed, consistent(cuts), segs)


def case_frames_master(S, a):
    """F-3 at full size: one real render.py --master (1080x1920) of the 10 s CFR excerpt. Run under heavy_lock."""
    src = excerpt(S, a.take, "1920:1080")
    w, cuts = plan(S, "frames-master", src, SOURCES["cfr"], 1.0)
    if not cuts:
        return
    r = run("render.py", w, src, "--master", cwd=w.parent)
    master, render = w / "renders" / "master-100x.mp4", module("render.py")
    want, got = cuts["segments"][-1]["out_out_f"], render.count_frames(master)
    st = render.probe_out(master)["streams"][0] if master.exists() else {}
    ck("F-3 master: render.py --master renders %sx%s with exactly the last out_out_f frames (%d rendered, %d in "
       "cuts.json)" % (st.get("width"), st.get("height"), got, want),
       r.returncode == 0 and got == want and (st.get("width"), st.get("height")) == (1080, 1920), r.stderr[-400:])


def case_zeros(S, a):
    """F-15: no run of exact-zero samples over 2 ms anywhere after the first 10 ms of the master's audio."""
    for label, src, speed in (("cfr", excerpt(S, a.take, TINY_SRC), 1.15), ("vfr", vfr_excerpt(S, a.vfr), 1.0)):
        w, cuts = plan(S, "zeros-%s" % label, src, SOURCES[label], speed)
        rc, err, master, _ = tiny_render(w, src) if cuts else (1, "no probe", None, -1)
        if rc:
            ck("F-15 %s: the master renders" % label, False, err[-400:])
            continue
        x, sr = pcm(master)
        n = audio_end(master, sr)
        worst, at, lim = zero_run(x[:n], sr)
        ck("F-15 %s %.2fx: longest exact-zero run after 10 ms is %d samples (limit %d at %d Hz; %d samples read, of %d "
           "decoded)" % (label, speed, worst, lim, sr, min(n, len(x)), len(x)), sr < n <= len(x) and worst <= lim,
           "run starts at %.3f s" % (at / sr))
        # AAC smears a digital-zero pad into non-zero values, so the master alone can't show one. render.py's own
        # graph, decoded losslessly to float PCM, shows the concat exactly as built.
        graph, wav = w / ("_graph-%s.txt" % master.stem), w / "lossless.wav"
        need_ram()
        p = sh(["ffmpeg", "-y", "-v", "error", "-i", src, "-/filter_complex", graph, "-map", "[a]", "-c:a", "pcm_f32le",
                wav, "-map", "[v]", "-f", "null", "-"])
        x, sr = pcm(wav) if p.returncode == 0 else ([], 48000)
        worst, at, lim = zero_run(x, sr)
        ck("F-15 %s %.2fx lossless: render.py's graph (%s) decoded to PCM has its longest exact-zero run after 10 ms "
           "at %d samples (limit %d; %d samples read)" % (label, speed, graph.name, worst, lim, len(x)),
           p.returncode == 0 and len(x) > sr and worst <= lim, (p.stderr[-300:], "run starts at %.3f s" % (at / sr)))


def audio_end(path, sr):
    """Where the master's audio ends by its own container: the last audio packet's pts + duration, in samples. The
    AAC decoder still emits that last frame's encoder padding past it (ffmpeg 8.1.2: 'discard 0'); that is not audio."""
    j = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                       "stream=time_base:packet=pts,duration", "-of", "json", path]).stdout)
    num, den = map(int, j["streams"][0]["time_base"].split("/"))
    k = j["packets"][-1]
    return round((int(k["pts"]) + int(k["duration"])) * num * sr / den)


def zero_run(x, sr):
    """The longest run of exact-zero samples after the first 10 ms: (length, start sample, the 2 ms limit)."""
    lim, run_, worst, at = round(0.002 * sr), 0, 0, 0
    for k in range(int(0.010 * sr), len(x)):
        run_ = run_ + 1 if x[k] == 0.0 else 0
        if run_ > worst:
            worst, at = run_, k - run_ + 1
    return worst, at, lim


def max_jump(path, t, reach=0.005):
    x, sr = pcm(path)
    i0, r = round(t * sr), round(reach * sr)
    return max(abs(x[k + 1] - x[k]) for k in range(max(0, i0 - r), min(len(x) - 1, i0 + r)))


def case_pop(S, a):
    """VU-4: two kept pieces meet at a planted 0.6 step; the 12/18 ms fades keep the join click-free."""
    d = fresh(S, "pop")
    w = d / "work"
    src = synth_step(d)
    if not probe(src, w):
        return
    gaps, render = module("gaps.py"), module("render.py")
    pj = load(w / "probe.json")
    cuts = gaps.snap_cuts([(0.2, 1.0), (2.0, 2.8)], pj["out_rate"], 1.0)
    gaps.write_cuts(w, cuts)
    t = cuts["segments"][0]["out_out_f"] / cuts["fps"]
    rc, err, master, _ = tiny_render(w, src)
    if rc:
        ck("VU-4: the master renders", False, err[-400:])
        return
    faded = max_jump(master, t)
    # the no-fade reference: render.py's own graph with its afade filters taken out, through its own encode
    g = re.sub(r",afade=[^,\[;]*", "", render.build_graph(cuts, SR, TINY_VF, 0))
    (w / "_graph-nofade.txt").write_text(g, encoding="utf-8")
    need_ram()
    try:
        render.encode(src, w / "_graph-nofade.txt", w / "nofade.mp4", cuts["fps"], pj["fps_flag"], 14, "slow", 30, "192k")
        bare = max_jump(w / "nofade.mp4", t)
    except SystemExit as e:
        ck("VU-4: the no-fade reference renders", False, e)
        return
    thr = bare / 4
    ck("VU-4: the no-fade reference shows the planted step (largest jump %.4f >= 0.2, afade gone: %s)"
       % (bare, "afade" not in g), bare >= 0.2 and "afade" not in g)
    ck("VU-4: with the 12/18 ms fades the largest sample jump within 5 ms of the cut at %.3f s is %.4f < %.4f "
       "(a quarter of the no-fade %.4f)" % (t, faded, thr, bare), faded < thr)


def case_filtercomplex(S, a):
    """F-6: the render's encode command uses -/filter_complex, and the encode exits 0."""
    d = fresh(S, "filtercomplex")
    w = d / "work"
    src = synth_step(d)
    if not probe(src, w):
        return
    gaps, render = module("gaps.py"), module("render.py")
    gaps.write_cuts(w, gaps.snap_cuts([(0.2, 1.0), (2.0, 2.8)], load(w / "probe.json")["out_rate"], 1.0))
    calls, popens, real, real_popen = [], [], subprocess.run, subprocess.Popen

    def spy(cmd, *x, **k):
        p = real(cmd, *x, **k)
        calls.append(([str(c) for c in cmd], p.returncode))
        return p

    class SpyPopen(real_popen):  # the encode streams its progress through Popen
        def __init__(self, cmd, *x, **k):
            super().__init__(cmd, *x, **k)
            popens.append(([str(c) for c in cmd], self))

    subprocess.run, subprocess.Popen = spy, SpyPopen
    try:
        rc, _, master, _ = tiny_render(w, src)
    finally:
        subprocess.run, subprocess.Popen = real, real_popen
    calls += [(c, p.returncode) for c, p in popens]
    enc = [(c, r) for c, r in calls if Path(c[0]).stem == "ffmpeg" and "-map" in c]
    ver = sh(["ffmpeg", "-version"]).stdout.split("\n")[0]
    ck("F-6: the encode command uses -/filter_complex, never -filter_complex_script",
       bool(enc) and all("-/filter_complex" in c and "-filter_complex_script" not in c for c, _ in enc),
       [c[:12] for c, _ in enc])
    ck("F-6: and the encode exits 0 (%s)" % ver, bool(enc) and rc == 0 and all(r == 0 for _, r in enc)
       and master.exists(), (rc, [r for _, r in enc]))


def case_cuts_missing(S, a):
    """H-R2: render.py reads only cuts.json, and stops plainly without it. SC1: make_tweaks.py stops plainly (exit 2,
    one line) without cuts.json and on a --take the Cut Board doesn't have, never with a traceback."""
    d = fresh(S, "cuts-missing")
    w = d / "work"
    src = synth_step(d)
    if not probe(src, w):
        return
    p = run("render.py", w, src, "--master", cwd=d)
    err = p.stderr.strip().splitlines()
    ck("H-R2: render.py without cuts.json exits 2 with one plain line", p.returncode == 2 and len(err) == 1
       and "work/cuts.json is missing: run gaps.py first" in err[0], (p.returncode, p.stderr[-300:]))
    cfg = d / "cut-board.config.json"
    cfg.write_text(json.dumps({"reel": "cm", "takes": {"1": {"words": [], "edit_map": "work/edit_map.json"}}}),
                   encoding="utf-8")
    tw = lambda take: run("make_tweaks.py", "--cut", src, "--work", "work", "--config", cfg, "--take", take, "-o", d,
                          cwd=d)
    p = tw("1")
    err = p.stderr.strip().splitlines()
    ck("SC1: make_tweaks.py without cuts.json exits 2 with one plain line", p.returncode == 2 and len(err) == 1
       and "work/cuts.json is missing: run gaps.py first" in err[0], (p.returncode, p.stderr[-300:]))
    gaps = module("gaps.py")
    gaps.write_cuts(w, gaps.snap_cuts([(0.2, 1.0)], load(w / "probe.json")["out_rate"], 1.0))
    p = tw("9")
    err = p.stderr.strip().splitlines()
    ck("SC1: make_tweaks.py on a take not on the Cut Board exits 2 with one plain line", p.returncode == 2
       and len(err) == 1 and "take 9 is not on this Cut Board (takes: 1)" in err[0], (p.returncode, p.stderr[-300:]))
    p = run("render.py", w, src, "--master", "--speed", "1.15", cwd=d)
    err = p.stderr.strip().splitlines()
    ck("H-R2: a --speed that differs from cuts.json exits 2 with one plain line", p.returncode == 2 and len(err) == 1
       and "differs from cuts.json" in err[0], (p.returncode, p.stderr[-300:]))


def fake_tools(fake, marker):
    """A fake ffmpeg and ffprobe that only append their command line to `marker` and exit 1: a sh script and a .cmd,
    plus an .exe on Windows (a bare subprocess call there finds only an .exe), built with the csc of the .NET
    Framework that Windows ships."""
    fake.mkdir()
    for t in ("ffmpeg", "ffprobe"):
        (fake / t).write_bytes(('#!/bin/sh\necho "$0 $*" >> "%s"\nexit 1\n' % marker.as_posix()).encode())
        (fake / t).chmod(0o755)
        (fake / (t + ".cmd")).write_bytes(('@echo off\r\necho %%~nx0 %%*>> "%s"\r\nexit /b 1\r\n' % marker).encode())
    csc = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
    if os.name == "nt" and csc.exists():
        cs = fake / "fake.cs"
        cs.write_bytes(('class F{static int Main(){System.IO.File.AppendAllText(@"%s",'
                        'System.Environment.CommandLine+"\\n");return 1;}}' % marker).encode())
        sh([csc, "-nologo", "-out:%s" % (fake / "ffmpeg.exe"), cs])
        if (fake / "ffmpeg.exe").exists():
            shutil.copyfile(fake / "ffmpeg.exe", fake / "ffprobe.exe")


def case_tools(S, a):
    """SC5: probe.py, render.py, review_page.py, silence_budget.py and make_tweaks.py take ffmpeg/ffprobe from the
    editor's install (runtime.tool), never PATH. With a fake ffmpeg/ffprobe first on PATH (it writes a marker when
    called), probe.py on the 10 s CFR excerpt, a TINY render (render.py's main() writes the review page),
    silence_budget.py on that cut and make_tweaks.py on it must all succeed and leave no marker."""
    src = excerpt(S, a.take, TINY_SRC)          # cut before the fakes go on PATH
    d = fresh(S, "tools")
    w = d / "work"
    fake, marker = d / "fakebin", d / "path-tool-called.txt"
    fake_tools(fake, marker)
    saved = ENV["PATH"]
    # Windows looks a bare command up on this process's PATH, other systems on the child's env: set both
    ENV["PATH"] = os.environ["PATH"] = str(fake) + os.pathsep + saved
    try:
        try:
            sh(["ffprobe", "-version"])
        except OSError:
            pass
        ck("tools control: a bare ffprobe call finds the fake first on PATH, and it writes the marker",
           marker.exists())
        marker.unlink(missing_ok=True)
        ok = probe(src, w)
        ck("tools: probe.py called no ffmpeg/ffprobe from PATH (marker absent)", not marker.exists(),
           text(marker)[-300:])
        if not ok:
            return
        gaps = module("gaps.py")
        cuts = gaps.snap_cuts(SOURCES["cfr"], load(w / "probe.json")["out_rate"], 1.0)
        gaps.write_cuts(w, cuts)
        rc, err, master, got = tiny_render(w, src)
        want = cuts["segments"][-1]["out_out_f"]
        ck("tools: the TINY render succeeds with the editor's own tools (%d frames rendered, %d in cuts.json)"
           % (got, want), rc == 0 and got == want, (rc, err[-400:]))
        ck("tools: render.py and its review page called no ffmpeg/ffprobe from PATH (marker absent)",
           not marker.exists(), text(marker)[-300:])
        if rc != 0 or not master.exists():
            return
        p = run("silence_budget.py", master, "--probe", w / "probe.json")
        ck("tools: silence_budget.py measures the cut with the editor's own tools (exit 0 or 1, a RESULT line)",
           p.returncode in (0, 1) and "RESULT:" in p.stdout, (p.returncode, p.stdout[-300:], p.stderr[-300:]))
        ck("tools: silence_budget.py called no ffmpeg/ffprobe from PATH (marker absent)", not marker.exists(),
           text(marker)[-300:])
        cfg = d / "cut-board.config.json"
        cfg.write_text(json.dumps({"reel": "tools", "takes": {"1": {"words": [], "edit_map": "work/edit_map.json"}}}),
                       encoding="utf-8")
        (w / "edit_map.json").write_text(json.dumps({"words": []}), encoding="utf-8")  # the Cut Board's map (FX1-W1d)
        p = run("make_tweaks.py", "--cut", master, "--work", w, "--config", cfg, "--take", "1", "-o", d)
        ck("tools: make_tweaks.py writes tweak-board.config.json with the editor's own tools",
           p.returncode == 0 and (d / "tweak-board.config.json").is_file(), (p.returncode, p.stderr[-300:]))
        ck("tools: make_tweaks.py called no ffmpeg/ffprobe from PATH (marker absent)", not marker.exists(),
           text(marker)[-300:])
    finally:
        ENV["PATH"] = os.environ["PATH"] = saved


CASES = {"beat": case_beat, "beat-real": case_beat_real, "edge": case_edge, "island": case_island,
         "internal-word": case_internal_word, "frames": case_frames, "frames-phone": case_frames_phone,
         "zeros": case_zeros, "pop": case_pop,
         "filtercomplex": case_filtercomplex, "cuts-missing": case_cuts_missing, "tools": case_tools,
         "frames-master": case_frames_master}


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    ap.add_argument("--take", default=TAKE)
    ap.add_argument("--s3-work", default=S3_WORK)
    ap.add_argument("--vfr", default=VFR)
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    print("python %s\nffmpeg %s" % (PY, shutil.which("ffmpeg")))
    for name in [a.case] if a.case else list(CASES):
        t0 = time.time()
        print("-- %s" % name)
        CASES[name](S, a)
        print("   (%s: %.0f s)" % (name, time.time() - t0))
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
