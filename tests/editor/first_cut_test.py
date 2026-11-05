#!/usr/bin/env python3
"""S2 check for reel-first-cuts: the three 0.1.0 bugs, the 1080x1920 conform, HLG/PQ tone-map,
the chosen audio stream, rotation-aware portrait, and the cut review page.

usage: python tests/editor/first_cut_test.py <scratch-dir> --take <a long landscape talking-head take>
                                             [--plugin <plugin root>]
Prints PASS/FAIL per check; exit 0 = every check passed. The take is a test fixture and never ships.
--plugin runs the same checks against another tree: on the 0.1.0 tree every bug check fails.

Tools come from the editor state folder (EDITOR_SE_HOME, else the default): ffmpeg/ffprobe (with zscale
and libx265, else PATH), and node, Chrome and puppeteer-core for the page click. Missing ones FAIL.
Known colour (H-R25): CIEDE2000 dE <= 5.0 per patch on the HLG -> SDR case, against the planted value.
"""
import argparse, importlib.util, json, math, os, re, shlex, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "plugins" / "editor-superengine" / "skills" / "_shared"))
import runtime as rt  # noqa: E402

ENV = rt.python_env()          # the state's ffmpeg first on PATH when it is installed
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def sh(cmd, cwd=None, env=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env or ENV, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=3600)


def ff(*args):
    p = sh(["ffmpeg", "-y", "-v", "error"] + list(args))
    if p.returncode:
        raise SystemExit("fixture ffmpeg failed: %s" % p.stderr[-800:])


def vstream(path):
    p = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,nb_frames,color_transfer,color_primaries", "-of", "json", path])
    try:
        return json.loads(p.stdout)["streams"][0]
    except (ValueError, KeyError, IndexError):
        return {}


def dims_ok(path):
    s = vstream(path)
    return (s.get("width"), s.get("height")) == (1080, 1920) and int(s.get("nb_frames") or 0) > 0, s


def script(plugin, name):
    return plugin / "skills" / "reel-first-cuts" / "scripts" / name


EDITOR_PY = "<editor python> -X utf8 -I "


def skill_lines(plugin):
    """Every line of SKILL.md, references/no-board-path.md and references/cut-checks.md, stripped of indent and an
    opening backtick."""
    rfc = plugin / "skills" / "reel-first-cuts"
    return [l.strip().lstrip("`") for d in ("SKILL.md", "references/no-board-path.md", "references/cut-checks.md")
            for l in (rfc / d).read_text(encoding="utf-8").splitlines()]


def skill_cmd(plugin, name, subs):
    """The `<editor python> -X utf8 -I "...scripts/<name>" ...` line the skill documents, placeholders filled in,
    run with this interpreter and the same flags."""
    line = next((l for l in skill_lines(plugin) if l.startswith(EDITOR_PY) and "scripts/%s" % name in l), "")
    if not line:
        return [sys.executable, "-c", "raise SystemExit('no documented command')"], line
    toks = [t.replace("${CLAUDE_PLUGIN_ROOT}", plugin.as_posix()) for t in shlex.split(line.split("`")[0])]
    return [sys.executable] + [subs.get(t, t) for t in toks[2:]], line


def check_skill_commands(plugin):
    """H-S4b-18: every command runs as <editor python> -X utf8 -I; a bare python breaks on a client's machine."""
    lines = skill_lines(plugin)
    cmds = [l for l in lines if l.startswith(EDITOR_PY)]
    bare = [l for l in lines if re.match(r"(python3?|py)\s", l)]
    print("documented <editor python> commands: %d" % len(cmds))
    ck("H-S4b-18: SKILL.md + no-board-path.md + cut-checks.md document commands and none starts with a bare python",
       bool(cmds) and not bare, bare[:3])


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_cuts(plugin, work, segs, speed=1.0):
    """work/cuts.json (render.py's only input) and the segments.json derived from it, through gaps.py's own
    frame snap at probe.json's fps."""
    spec = importlib.util.spec_from_file_location("gaps", script(plugin, "gaps.py"))
    gaps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gaps)
    gaps.write_cuts(work, gaps.snap_cuts(segs, load(Path(work) / "probe.json").get("out_rate", 30.0), speed))


# ------------------------------------------------------------------- colour (CIEDE2000)
def lab(c):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = map(lin, c)
    X, Y, Z = (0.4124 * r + 0.3576 * g + 0.1805 * b, 0.2126 * r + 0.7152 * g + 0.0722 * b,
               0.0193 * r + 0.1192 * g + 0.9505 * b)
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(X / 0.95047), f(Y), f(Z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de2000(c1, c2):
    (L1, a1, b1), (L2, a2, b2) = lab(c1), lab(c2)
    Cb = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1, C2 = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1, h2 = math.degrees(math.atan2(b1, a1p)) % 360, math.degrees(math.atan2(b2, a2p)) % 360
    dh = 0 if C1 * C2 == 0 else ((h2 - h1 + 180) % 360) - 180
    dH = 2 * math.sqrt(C1 * C2) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1 + C2) / 2
    if C1 * C2 == 0:
        hb = h1 + h2
    elif abs(h1 - h2) <= 180:
        hb = (h1 + h2) / 2
    else:
        hb = (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb))
         + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63)))
    RC = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    SL = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    RT = -math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2))) * RC
    dL, dC = L2 - L1, C2 - C1
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


# ColorChecker-like patches and a grey ramp, laid out 4 x 6 on a portrait frame (asymmetric on purpose:
# a wrong rotation puts the wrong colour under every probe)
PATCHES = [(115, 82, 68), (194, 150, 130), (98, 122, 157), (87, 108, 67), (133, 128, 177), (103, 189, 170),
           (214, 126, 44), (80, 91, 166), (193, 90, 99), (94, 60, 108), (157, 188, 64), (224, 163, 46),
           (56, 61, 150), (70, 148, 73), (175, 54, 60), (231, 199, 31), (187, 86, 149), (8, 133, 161),
           (243, 243, 242), (200, 200, 200), (160, 160, 160), (122, 122, 121), (85, 85, 85), (52, 52, 52)]
COLS, ROWS = 4, 6


def patch_frame(w, h):
    buf = bytearray(w * h * 3)
    for y in range(h):
        row = min(y * ROWS // h, ROWS - 1) * COLS
        for x in range(w):
            i = (y * w + x) * 3
            buf[i:i + 3] = bytes(PATCHES[row + min(x * COLS // w, COLS - 1)])
    return bytes(buf)


def patch_means(rgb, w, h):
    out = []
    for k in range(len(PATCHES)):
        r0, c0 = divmod(k, COLS)
        x0, x1 = (4 * c0 + 1) * w // (4 * COLS), (4 * c0 + 3) * w // (4 * COLS)
        y0, y1 = (4 * r0 + 1) * h // (4 * ROWS), (4 * r0 + 3) * h // (4 * ROWS)
        acc, n = [0, 0, 0], 0
        for y in range(y0, y1, 4):
            for x in range(x0, x1, 4):
                i = (y * w + x) * 3
                for j in range(3):
                    acc[j] += rgb[i + j]
                n += 1
        out.append(tuple(a / n for a in acc))
    return out


# ------------------------------------------------------------------------------ checks
def check_take(S, plugin, take):
    """The 0.1.0 bugs, the conform and the review page, on a real take."""
    base = S / "take"
    w = base / "work"
    shutil.rmtree(base, ignore_errors=True)
    w.mkdir(parents=True)
    p = sh([sys.executable, script(plugin, "probe.py"), take, "-o", w])
    pj = load(w / "probe.json")
    ck("VU-2: probe counts the audio streams and stores the chosen one as audio_stream",
       p.returncode == 0 and pj.get("audio_streams", 0) >= 1 and pj.get("audio_stream") == 0,
       "rc %s, audio_streams %s, audio_stream %s" % (p.returncode, pj.get("audio_streams"), pj.get("audio_stream")))
    if p.returncode:
        print(p.stderr[-800:])
        return
    # 24 short ranges: more than 20 cuts, so the review page's list must stop at 20
    edl = [{"src_in": round(1.0 + 1.2 * k, 3), "src_out": round(1.8 + 1.2 * k, 3)} for k in range(24)]
    (w / "edl.json").write_text(json.dumps(edl), encoding="utf-8")
    (w / "edit_map.json").write_text(json.dumps({"words": []}), encoding="utf-8")   # the command's --words

    cmd, line = skill_cmd(plugin, "gaps.py", {"<speed>": "1.0"})
    p = sh(cmd, cwd=base)
    ck("bug 1: the skill's gaps.py command runs (--edl, no --plan)",
       p.returncode == 0 and (w / "segments.json").exists(), "%r -> rc %s %s" % (line, p.returncode, p.stderr[-200:]))
    # the render checks render the EDL itself (25 cuts), so they stand apart from bug 1 and from gap tightening
    speed = 1.15
    write_cuts(plugin, w, [[c["src_in"], c["src_out"]] for c in edl], speed)

    p = sh([sys.executable, script(plugin, "render.py"), w, take, "--speed", speed])
    if p.returncode:
        print(p.stderr[-800:])
    ok, s = dims_ok(w / "renders" / "scrub-115x.mp4")
    ck("bug 2: the scrub is 9:16, 1080x1920, with frames", ok, s)
    ok, s = dims_ok(w / "renders" / "master-115x.mp4")
    ck("conform: the master is 1080x1920 with frames", ok, s)

    cut = (w / "renders" / "scrub-115x.mp4").as_posix()
    cmd, line = skill_cmd(plugin, "silence_budget.py", {"CUT.mp4": cut})
    p = sh(cmd, cwd=base)
    m = re.search(r"threshold\s+(-?[\d.]+) dB, calibrated in probe\.json", p.stdout)
    gap = (pj.get("calibration") or {}).get("gap_db")
    ck("bug 3: SKILL.md's Stage 7b silence budget reads probe.json's threshold (%s dB)" % gap,
       bool(m) and gap is not None and abs(float(m.group(1)) - gap) < 0.05,
       "%r -> rc %s %s" % (line, p.returncode, (p.stdout + p.stderr)[-300:]))

    # H-R26: the review page, opened from disk, against cuts computed here from segments.json
    page = w / "cut-review.html"
    ck("H-R26: render writes the review page", page.exists(), page)
    if not page.exists():
        return
    segs = sorted(load(w / "segments.json"))
    total = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                      take]).stdout.strip())
    exp, prev, kept = [], 0.0, 0.0
    for a, b in segs + [[total, total]]:
        if a - prev > 1e-3:
            exp.append((a - prev, prev, kept / speed))
        kept, prev = kept + (b - a), max(prev, b)
    top = sorted(exp, key=lambda c: -c[0])[:20]
    try:
        pup = rt.state_dir() / "hyperframes" / "node_modules" / "puppeteer-core"
        p = sh([rt.tool("node"), HERE / "review_page_click.js", page, pup, rt.tool("chrome")])
        r = json.loads(p.stdout)
    except (KeyError, OSError, ValueError) as e:
        ck("H-R26: the page opens in headless Chrome from disk", False, e)
        return
    rows = r.get("rows") or []
    ck("H-R26: the page opens from disk with no script errors and both videos found",
       not r["errors"] and all(r["srcExists"]) and len(r["srcExists"]) == 2, (r["errors"], r["srcs"]))
    ck("H-R26: it lists the 20 largest cuts, largest first (%d cuts in all)" % len(exp),
       len(exp) > 20 and len(rows) == 20                                   # ties may list in any order:
       and all(abs(x["len"] - e[0]) < 0.011 for x, e in zip(rows, top))  # the lengths match the top 20,
       and all(any(abs(x["start"] - c[1]) < 0.002 and abs(x["len"] - c[0]) < 0.011 for c in exp) for x in rows),
       (len(rows), rows[:3], top[:3]))
    want = (max(0.0, top[0][1] - 0.5), max(0.0, top[0][2] - 0.5))
    got = (r["rowClick"]["raw"], r["rowClick"]["cut"])
    ck("H-R26: clicking a cut seeks both players to 0.5 s before it", all(abs(g - x) < 0.02 for g, x in zip(got, want)),
       "got %s want %s" % (got, want))
    got = r["markClick"]["raw"]
    ck("H-R26: clicking the widest red mark on the bar seeks the raw to 0.5 s before it",
       abs(got - want[0]) < 0.02, "got %s want %s" % (got, want[0]))


def check_hlg(S, plugin):
    """VU-1 + VU-5 a: a planted iPhone-style clip, HLG BT.2020 10-bit, stored landscape with a -90
    display rotation, conforms to a 1080x1920 SDR master with known colour."""
    d = S / "hlg"
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    W, H = 720, 1280
    (d / "patch.rgb").write_bytes(patch_frame(W, H))
    hlg = (" scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
           "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,"
           "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt2020:t=arib-std-b67:m=bt2020nc:r=tv,"
           "format=yuv420p10le,transpose=cclock").strip()
    ff("-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", "30", "-stream_loop", "59",
       "-i", d / "patch.rgb", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
       "-vf", hlg, "-c:v", "libx265", "-crf", "8", "-tag:v", "hvc1", "-x265-params",
       "log-level=error:keyint=30:no-open-gop=1:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited",
       "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-color_range", "tv",
       "-c:a", "aac", "-shortest", d / "coded.mp4")
    ff("-display_rotation:v:0", "-90", "-i", d / "coded.mp4", "-map", "0", "-c", "copy", d / "iphone-hlg.mp4")
    clip = d / "iphone-hlg.mp4"

    p = sh([sys.executable, script(plugin, "probe.py"), clip, "-o", d / "work"])
    v = load(d / "work" / "probe.json").get("video") or {}
    ck("VU-5 a: the planted rotated phone clip (stored %sx%s) is detected as portrait" % (v.get("width"), v.get("height")),
       p.returncode == 0 and v.get("portrait") is True and v.get("rotation") in (-90, 90, 270), v or p.stderr[-300:])
    write_cuts(plugin, d / "work", [[0.2, 1.8]])
    p = sh([sys.executable, script(plugin, "render.py"), d / "work", clip, "--master"])
    master = d / "work" / "renders" / "master-100x.mp4"
    ok, s = dims_ok(master)
    ck("VU-5 a: the rotated clip conforms to 1080x1920 with frames", ok, s or p.stderr[-300:])
    graph = d / "work" / "_graph-master-100x.txt"
    ck("VU-1: the tone-map sits inside the render's one filter graph (no extra generation)",
       graph.exists() and "tonemap" in graph.read_text(encoding="utf-8"), graph)
    ck("VU-1: the master is tagged SDR BT.709",
       (s.get("color_transfer"), s.get("color_primaries")) == ("bt709", "bt709"), s)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.5", "-i", str(master), "-frames:v", "1", "-vf",
                          "scale=in_color_matrix=bt709:in_range=tv,format=rgb24", "-f", "rawvideo", "-"],
                         env=ENV, capture_output=True, timeout=600).stdout
    if len(raw) != 1080 * 1920 * 3:
        ck("VU-1: known colour within dE 5.0 (H-R25)", False, "no 1080x1920 frame to measure")
        return
    des = [de2000(e, m) for e, m in zip(PATCHES, patch_means(raw, 1080, 1920))]
    worst = max(range(len(des)), key=des.__getitem__)
    ck("VU-1: HLG -> SDR known colour, max CIEDE2000 dE %.2f <= 5.0 over %d patches (H-R25)" % (des[worst], len(des)),
       des[worst] <= 5.0, "worst patch %d %s" % (worst, PATCHES[worst]))


def check_audio_stream(S, plugin):
    """VU-2: a planted two-track file; the chosen stream is the one the conform carries."""
    d = S / "two"
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    clip = d / "two-tracks.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=30:d=2",
       "-f", "lavfi", "-i", "aevalsrc=0.001*sin(2*PI*300*t):s=48000:d=2",
       "-f", "lavfi", "-i", "aevalsrc=0.3*sin(2*PI*1000*t):s=48000:d=2",
       "-map", "0", "-map", "1", "-map", "2", "-c:v", "libx264", "-c:a", "aac", clip)
    p = sh([sys.executable, script(plugin, "probe.py"), clip, "-o", d / "work", "--audio-stream", "1"])
    pj = load(d / "work" / "probe.json")
    ck("VU-2: probe --audio-stream 1 stores audio_stream 1 of 2",
       p.returncode == 0 and pj.get("audio_streams") == 2 and pj.get("audio_stream") == 1, pj or p.stderr[-300:])
    write_cuts(plugin, d / "work", [[0.2, 1.8]])
    sh([sys.executable, script(plugin, "render.py"), d / "work", clip, "--master"])
    p = sh(["ffmpeg", "-i", d / "work" / "renders" / "master-100x.mp4", "-map", "0:a:0", "-af", "volumedetect",
            "-f", "null", "-"])
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", p.stderr)
    ck("VU-2: the conform carries the chosen stream (the loud one, not the -63 dB one)",
       bool(m) and float(m.group(1)) > -25, m and m.group(0))


def check_threshold_fallback(S, plugin):
    """Bug 3's fallback (port 3): no calibration in probe.json -> 22 dB under the file's 90th percentile,
    never below -55 dB. Planted tones make the answer known: a -20 dB RMS tone -> -42; a -40 one -> -55."""
    d = S / "tones"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    (d / "probe.json").write_text("{}", encoding="utf-8")
    for amp, want in (("0.1414214", -42.0), ("0.01414214", -55.0)):
        f = d / ("tone-%s.wav" % want)
        ff("-f", "lavfi", "-i", "aevalsrc=if(lt(t\\,6)\\,%s*sin(2*PI*1000*t)\\,0):s=16000:d=10" % amp, "-c:a", "pcm_s16le", f)
        p = sh([sys.executable, script(plugin, "silence_budget.py"), f, "--probe", d / "probe.json"])
        m = re.search(r"threshold\s+(-?[\d.]+) dB, the cut's own level", p.stdout)
        ck("bug 3 fallback: a probe.json without a threshold uses the file's own level (%.0f dB)" % want,
           bool(m) and abs(float(m.group(1)) - want) < 0.2, (p.stdout + p.stderr)[-300:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--take", required=True)
    ap.add_argument("--plugin", default=str(REPO / "plugins" / "editor-superengine"))
    a = ap.parse_args()
    S, plugin = Path(a.scratch).resolve(), Path(a.plugin).resolve()
    S.mkdir(parents=True, exist_ok=True)
    print("plugin %s\nffmpeg %s" % (plugin, shutil.which("ffmpeg", path=ENV.get("PATH"))))

    p = sh([sys.executable, "-m", "unittest", "-q", HERE / "test_portrait_detection.py"],
           env=dict(ENV, EDITOR_SE_PLUGIN=str(plugin)))
    ck("VU-5 a: the 6 ported portrait-detection tests pass", p.returncode == 0, p.stderr[-400:])
    check_skill_commands(plugin)
    check_threshold_fallback(S, plugin)
    check_audio_stream(S, plugin)
    check_hlg(S, plugin)
    check_take(S, plugin, Path(a.take).resolve())
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
