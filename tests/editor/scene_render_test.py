#!/usr/bin/env python3
"""G2-a/G2-b heavy check: every shipped scene lints clean and renders offline with alpha, text inside the safe box.

usage (heavy job, one scene per call keeps each run short; EDITOR_SE_HOME = a state folder with node, chrome,
ffmpeg and hyperframes installed):
  python -I "C:/Workspaces/Content Studio/output/scripts/heavy_lock.py" --min-gb 3 -- \
    python -X utf8 -I tests/editor/scene_render_test.py [--scene <id> ...] [--part all|base|counter|seek]
      [--write-previews]
Default = every scene folder present (the 8 own ones and any vendored hf-*). For each scene, in a temp project built the offline_selftest way (scene.html as
index.html + the shipped GSAP in ./vendor and the shipped fonts in ./fonts, cold font cache, Node network guard,
proxies to a dead port):
  - `hyperframes lint --json`: exit 0, 0 errors, 0 warnings
  - render of the default fill at 1080x1920 as MOV (ProRes 4444 with alpha), zero network attempts,
    frame count = data-duration x data-fps
  - worst-case fill (every slot "W" x maxChars, string params with maxChars "W"-filled too) rendered as a
    TEXT-ONLY variant: the test injects one stylesheet that makes every `.plate` element (cards, bars, backdrops)
    paint nothing, so every pixel whose alpha is above 0 in any frame is text; all of them must lie inside the
    900x1250 safe box (x 60..959, y 220..1469; ig-safe-zones.py), and some must exist (a blank render fails)
  - counter part, every scene of category "counter" (counter, hf-counter): last frame of value 47 counting up ==
    (or PSNR >= 45 dB vs) the animate:false frame for 47, and PSNR < 40 dB vs the animate:false frame for 46
  - seek part (in `all` for every vendored scene, licence not "own", which moved from GSAP 3.14.2 to 3.15.0; any
    scene with --part seek). Jump method: a different worker split (the pin's dist/docs/rendering.md documents
    only `-w, --workers` for this; it documents no range render). The default fill is rendered twice: --workers 1
    (one page plays frames 0..F-1 in order) and --workers 2 (the pinned CLI's distributeFrames gives worker 1 the
    contiguous chunk starting at ceil(F/2), so its fresh page jumps from load straight to that frame). Both
    renders run with PRODUCER_FORCE_SCREENSHOT=true (a pinned-CLI env switch, not in the docs) and must report
    "screenshot capture": by default 1 worker takes the drawElement path and 2 workers the screenshot path, and
    those two paths differ by a few antialiased pixels on every frame, jump or not (lower-third: 166 px, 62.9 dB),
    which would hide the jump. Frame N = ceil(F/2) of the two renders, decoded in the stream's own pixel format,
    must be byte-identical, and not blank (some alpha above 0)
--write-previews  also writes scenes/<id>/preview.png (270x480, RGBA) from the default render's last frame.
Prints PASS/FAIL per check; exit 0 = all passed. Refuses to start below 10 GB free disk.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "editor-superengine"
SCENES = PLUGIN / "scenes"
DOCTOR = PLUGIN / "skills" / "editor-doctor" / "scripts"
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
sys.path.insert(0, str(DOCTOR))
import runtime as rt  # noqa: E402
import offline_selftest as ost  # noqa: E402  (NETGUARD, DEAD, run, remove: the offline pattern, reused)

W, H, FPS = 1080, 1920, 30
SAFE = (60, 220, 960, 1470)  # x0, y0, x1, y1 (exclusive), the 900x1250 box
TEXT_ONLY_CSS = ("<style>.plate{background:transparent!important;border-color:transparent!important;"
                 "box-shadow:none!important;outline:none!important}</style>")
WORST_NUMBERS = {"counter": {"value": 8888},  # by category, each key only where the scene has that param;
                 "stat-card": {"value": 9999, "decimals": 2}}  # "WW"+"8,888"+"WW" = 9 chars; "9,999.00"+"WW" = 10
MIN_FREE_GB = 10
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (("  [%s]" % (detail,)) if detail else ""), flush=True)
    if not ok:
        fails.append(name)
    return ok


def fills(spec, sid):
    default = {k: s["default"] for k, s in spec["slots"].items()}
    default.update({k: p["default"] for k, p in spec["params"].items()})
    worst = dict(default)
    worst.update({k: "W" * s["maxChars"] for k, s in spec["slots"].items()})
    worst.update({k: "W" * p["maxChars"] for k, p in spec["params"].items()
                  if p["type"] == "string" and "maxChars" in p})
    worst.update({k: v for k, v in WORST_NUMBERS.get(spec.get("category"), {}).items() if k in spec["params"]})
    return default, worst


def kill_warm():
    """Stop this state's leftover HyperFrames warmCheck.js daemon (it holds the temp project open on Windows)."""
    node = str(Path(rt.tool("node")).resolve())
    if os.name == "nt":
        ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        ost.run([ps, "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq "
                 f"'{node}' -and $_.CommandLine -like '*warmCheck.js*' }} | ForEach-Object {{ Stop-Process -Id "
                 "$_.ProcessId -Force }"], timeout=60)
    else:
        ost.run(["pkill", "-f", "warmCheck.js"], timeout=30)


def make_env(tmp):
    """offline_selftest.render_checks' environment: cold caches in tmp, Node network guard, dead proxies."""
    for d in ("home", "cache", "tmp"):
        (tmp / d).mkdir(exist_ok=True)
    log = tmp / "netguard.jsonl"
    env = rt.hyperframes_env()
    env.update(HOME=str(tmp / "home"), USERPROFILE=str(tmp / "home"), XDG_CACHE_HOME=str(tmp / "cache"),
               TEMP=str(tmp / "tmp"), TMP=str(tmp / "tmp"), TMPDIR=str(tmp / "tmp"),
               NODE_OPTIONS=f'--require "{ost.NETGUARD.as_posix()}"', NETGUARD_LOG=str(log),
               GIT_ALLOW_PROTOCOL="file", NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env[k] = env[k.lower()] = ost.DEAD
    env.pop("NETGUARD_ALLOW", None)
    return env, log


def project(tmp, name, html):
    proj = tmp / name
    (proj / "vendor").mkdir(parents=True)
    shutil.copy2(PLUGIN / "runtime" / "gsap" / "gsap.min.js", proj / "vendor" / "gsap.min.js")
    shutil.copytree(PLUGIN / "runtime" / "fonts", proj / "fonts")
    (proj / "index.html").write_bytes(html.encode("utf-8"))
    return proj


def render(proj, fill, out, env, workers=2, seen=None):
    """seen: a list that gets the render log's lines naming workers (the seek part shows them)."""
    vf = out.with_suffix(".vars.json")
    vf.write_bytes(json.dumps(fill).encode("utf-8"))
    t0 = time.perf_counter()
    rc, o, e = ost.run(rt.hyperframes_cmd("render", proj, "--format", "mov", "--workers", str(workers),
                                          "--strict-variables", "--variables-file", vf, "-o", out), env, timeout=600)
    kill_warm()
    if seen is not None:
        seen.extend(l.strip()[:160] for l in (o + e).splitlines()
                    if re.search(r"\d workers\b|\bcapture ·", l) and "Capturing frame" not in l)
    print(f"  rendered {out.name} in {time.perf_counter() - t0:.0f} s", flush=True)
    return rc == 0 and out.exists(), f"exit {rc}: {ost.tail(o + e)}"


def probe(video):
    rc, o, e = ost.run([rt.tool("ffprobe"), "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames,width,height,codec_name,pix_fmt", "-of", "json", video])
    try:
        return json.loads(o)["streams"][0]
    except (ValueError, KeyError, IndexError):
        return {}


def raw(video, vf, pix, frame=None):
    sel = f"select=eq(n\\,{frame})," if frame is not None else ""
    r = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-i", str(video), "-vf", sel + vf, "-f", "rawvideo",
                        "-pix_fmt", pix, "-"], capture_output=True, timeout=300)
    return r.stdout


def text_box(video, frames):
    """(x0, y0, x1, y1) of every pixel with alpha > 0 over all frames, the count outside SAFE, and the total."""
    buf = raw(video, "alphaextract", "gray")
    if len(buf) != frames * W * H:
        return None, None, 0
    zero = bytes(W)
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    outside = total = 0
    for f in range(frames):
        base = f * W * H
        for y in range(H):
            row = buf[base + y * W: base + (y + 1) * W]
            if row == zero:
                continue
            lead, trail = W - len(row.lstrip(b"\0")), W - len(row.rstrip(b"\0"))
            n = W - row.count(0)
            total += n
            x0, x1, y0, y1 = min(x0, lead), max(x1, W - trail), min(y0, y), max(y1, y + 1)
            if y < SAFE[1] or y >= SAFE[3]:
                outside += n
            else:
                outside += (SAFE[0] - row[:SAFE[0]].count(0)) + ((W - SAFE[2]) - row[SAFE[2]:].count(0))
    return ((x0, y0, x1, y1) if total else None), outside, total


def psnr(a, b):
    if len(a) != len(b) or not a:
        return -1.0
    if a == b:
        return math.inf
    mse = sum((x - y) * (x - y) for x, y in zip(a, b)) / len(a)
    return 10 * math.log10(255 * 255 / mse)


def scene_test(sid, tmp, env, log, write_preview, part):
    d = SCENES / sid
    spec = json.loads((d / "scene.json").read_text(encoding="utf-8"))
    html = (d / "scene.html").read_text(encoding="utf-8")
    m = re.search(r'data-composition-id="%s"[^>]*' % re.escape(sid), html)
    dur = float(re.search(r'data-duration="([\d.]+)"', m.group(0)).group(1)) if m else 0
    frames = round(dur * FPS)
    default, worst = fills(spec, sid)
    proj = project(tmp, sid, html)
    if part in ("all", "base"):
        base_checks(sid, d, html, spec, frames, dur, default, worst, proj, tmp, env, write_preview)
    if spec.get("category") == "counter" and part in ("all", "counter"):
        counter_checks(sid, spec, default, frames, proj, tmp, env)
    if part == "seek" or part == "all" and spec.get("licence") != "own":
        seek_checks(sid, frames, default, proj, tmp, env)
    n = sum(1 for _ in open(log, encoding="utf-8")) if log.exists() else 0
    ck(f"{sid}: no network attempts during lint and renders ({n} logged)", n == 0)


def base_checks(sid, d, html, spec, frames, dur, default, worst, proj, tmp, env, write_preview):
    rc, o, e = ost.run(rt.hyperframes_cmd("lint", proj, "--json"), env)
    kill_warm()
    try:
        j = json.loads(o[o.index("{"):])
        errs, warns = j["errorCount"], j["warningCount"]
        found = "; ".join(f"{x['code']}: {x['message']}" for x in j.get("findings", []))
    except (ValueError, KeyError):
        errs = warns = None
        found = ost.tail(o + e)
    ck(f"{sid}: lint exit 0, 0 errors, 0 warnings", rc == 0 and errs == 0 and warns == 0,
       f"exit {rc}, {errs} errors, {warns} warnings" + (f": {found}" if found else ""))

    mov = tmp / f"{sid}.mov"
    ok, why = render(proj, default, mov, env)
    if ck(f"{sid}: renders (default fill, MOV with alpha)", ok, "" if ok else why):
        s = probe(mov)
        ck(f"{sid}: {s.get('width')}x{s.get('height')} {s.get('codec_name')} {s.get('pix_fmt')}, "
           f"{s.get('nb_read_frames')} frames (want {W}x{H} with alpha, {frames} = {dur} s x {FPS})",
           (s.get("width"), s.get("height")) == (W, H) and str(s.get("pix_fmt", "")).startswith("yuva")
           and int(s.get("nb_read_frames") or -1) == frames)
        if write_preview:
            r = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", str(mov), "-vf",
                                f"select=eq(n\\,{frames - 1}),scale=270:480:flags=lanczos,format=rgba",
                                "-frames:v", "1", str(d / "preview.png")], capture_output=True, timeout=120)
            ck(f"{sid}: preview.png written from frame {frames - 1}", r.returncode == 0 and (d / "preview.png").exists(),
               r.stderr.decode("utf-8", "replace")[-300:])

    tproj = project(tmp, sid + "-textonly", html.replace("</head>", TEXT_ONLY_CSS + "\n  </head>", 1))
    tmov = tmp / f"{sid}-textonly.mov"
    ok, why = render(tproj, worst, tmov, env)
    if ck(f"{sid}: renders (worst-case fill, text only)", ok, "" if ok else why):
        box, outside, total = text_box(tmov, frames)
        ck(f"{sid}: worst-case text stays in the safe box {SAFE}: text pixels {box}, {outside} of {total} outside",
           box is not None and outside == 0 and total > 0)



def counter_checks(sid, spec, default, frames, proj, tmp, env):
    if not ck(f"{sid}: has the counter params value and animate", {"value", "animate"} <= set(spec["params"])):
        return
    last = {}
    for tag, val, anim in (("count47", 47, True), ("static47", 47, False), ("static46", 46, False)):
        f = dict(default, value=val, animate=anim)
        out = tmp / f"{sid}-{tag}.mov"
        ok, why = render(proj, f, out, env)
        if ck(f"{sid}: renders {tag}", ok, "" if ok else why):
            last[tag] = raw(out, "format=rgba", "rgba", frames - 1)
    if len(last) == 3:
        same, diff = psnr(last["count47"], last["static47"]), psnr(last["count47"], last["static46"])
        ck(f"{sid}: last frame counting to 47 matches the static 47 frame (PSNR {same:.2f} dB, needs >= 45)",
           same >= 45)
        ck(f"{sid}: and differs from the static 46 frame (PSNR {diff:.2f} dB, needs < 40)", 0 <= diff < 40)


def seek_checks(sid, frames, default, proj, tmp, env):
    """Frame N of a sequential render (--workers 1) == frame N reached after a jump (--workers 2's second chunk),
    both on the screenshot capture path so only the jump differs."""
    n = math.ceil(frames / 2)
    got, alpha = {}, b""
    senv = dict(env, PRODUCER_FORCE_SCREENSHOT="true")
    for tag, w in (("sequential", 1), ("jump", 2)):
        seen = []
        out = tmp / f"{sid}-seek-{tag}.mov"
        ok, why = render(proj, default, out, senv, workers=w, seen=seen)
        shot = any("screenshot capture" in l for l in seen)
        if ck(f"{sid}: seek render {tag} (--workers {w}, screenshot capture)", ok and shot,
              why if not ok else " | ".join(seen[:3])):
            got[tag] = raw(out, "null", probe(out).get("pix_fmt") or "yuva444p10le", n)
            alpha = raw(out, "alphaextract", "gray", n) if w == 2 else alpha
    if len(got) == 2:
        ck(f"{sid}: frame {n} ({n / FPS:.2f} s) is not blank", any(alpha))
        ck(f"{sid}: frame {n} of the sequential render == frame {n} after the jump, byte for byte "
           f"({len(got['sequential'])} vs {len(got['jump'])} bytes)", bool(got["jump"]) and got["sequential"] == got["jump"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene", action="append", help="scene id (repeatable); default every scene folder")
    ap.add_argument("--write-previews", action="store_true", help="write scenes/<id>/preview.png from the render")
    ap.add_argument("--part", choices=("all", "base", "counter", "seek"), default="all",
                    help="base = lint + default + worst-case renders; counter = the 47/46 frame proof (category "
                         "counter); seek = frame N sequential vs after a jump (all = these, seek on vendored only)")
    a = ap.parse_args()
    free = shutil.disk_usage(tempfile.gettempdir()).free / 2 ** 30
    if free < MIN_FREE_GB:
        print(f"FAIL only {free:.1f} GB free disk; renders need {MIN_FREE_GB} GB. Free some space and run again.")
        return 1
    ids = a.scene or sorted(p.name for p in SCENES.iterdir() if (p / "scene.json").exists())
    for sid in ids:
        tmp = Path(tempfile.mkdtemp(prefix=f"scene-render-{sid}-"))
        try:
            env, log = make_env(tmp)
            scene_test(sid, tmp, env, log, a.write_previews, a.part)
        except Exception as e:  # a crash is a failed check, never a pass
            ck(f"{sid}: test run", False, f"stopped: {type(e).__name__}: {e}")
        finally:
            kill_warm()
            ost.remove(tmp)
    print("%d failed" % len(fails) if fails else "all passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
