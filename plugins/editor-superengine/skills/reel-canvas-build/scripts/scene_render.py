#!/usr/bin/env python3
"""G2-a/G2-b heavy check: every shipped scene lints clean and renders offline with alpha, text inside the safe box.

usage (heavy job, one scene per call keeps each run short; EDITOR_SE_HOME = a state folder with node, chrome,
ffmpeg and hyperframes installed):
  <editor python> -X utf8 -I scene_render.py [--scene <id> ...] [--part all|base|brand|counter|seek]
      [--scenes-dir <dir>] [--write-previews] [--write-stills <dir>]
Default = every scene folder present (own scenes and any vendored hf-*). For each scene, in a temp project built the offline_selftest way (scene.html as
index.html + the shipped GSAP in ./vendor and the shipped fonts in ./fonts, cold font cache, Node network guard,
proxies to a dead port):
  - `hyperframes lint --json`: exit 0, 0 errors; only composition_file_too_large warnings are allowed
  - render of the default fill at 1080x1920 as MOV (ProRes 4444 with alpha), zero network attempts,
    frame count = data-duration x data-fps
  - worst-case fill (every slot "W" x maxChars, string params with maxChars "W"-filled too) rendered as a
    TEXT-ONLY variant: the test injects one stylesheet that makes every `.plate` element (cards, bars, backdrops)
    paint nothing, so every pixel whose alpha is above 0 in any frame is text; all of them must lie inside the
    900x1250 safe box (x 60..959, y 220..1469; ig-safe-zones.py), and some must exist (a blank render fails)
  - scenes of kind "takeover": default, full-scene worst-case and short-fill renders flattened over black have
    no black stretch at least tri2.black_gap_s from tuning.json (the master check's blackdetect rule);
    short fills use "Go" for required slots, empty optional slots and default params
  - counter part, every scene of category "counter" (counter, hf-counter): last frame of value 47 counting up ==
    (or PSNR >= 45 dB vs) the animate:false frame for 47, and PSNR < 40 dB vs the animate:false frame for 46
  - brand part, every scene: a temporary saved-style fixture applies lime and licensed Inter; the fill passes
    scene_check and the final frame has lime pixels (each channel within 40), absent from the default frame;
    an unavailable fixture font is refused with a note, keeping the scene default, without another render
  - world scenes: worst-case slot text is inside SAFE and clear of frame edges at holds only;
    all text is clear of caption_band at those holds (param/numeric seconds + 0.25 s, plus last frame)
  - seek part (in `all` for every reel- or vendored scene, licence not "own", which moved from GSAP 3.14.2 to 3.15.0; any
    scene with --part seek). Jump method: a different worker split (the pin's dist/docs/rendering.md documents
    only `-w, --workers` for this; it documents no range render). The default fill is rendered twice: --workers 1
    (one page plays frames 0..F-1 in order) and --workers 2 (the pinned CLI's distributeFrames gives worker 1 the
    contiguous chunk starting at ceil(F/2), so its fresh page jumps from load straight to that frame). Both
    renders run with PRODUCER_FORCE_SCREENSHOT=true (a pinned-CLI env switch, not in the docs) and must report
    "screenshot capture": by default 1 worker takes the drawElement path and 2 workers the screenshot path, and
    those two paths differ by a few antialiased pixels on every frame, jump or not (lower-third: 166 px, 62.9 dB),
    which would hide the jump. Frame N = ceil(F/2) must not be blank. Catalog scenes remain byte-identical in
    the stream's own pixel format; world scenes allow max RGBA channel delta 4/255 and 5% differing pixels.
    Both kinds also require exactly equal DOM state after sequential stepping and a fresh-page seek.
--write-previews  also writes scenes/<id>/preview.png (270x480, RGBA) from the default render's last frame.
--write-stills <dir>  writes default and short-fill PNGs flattened over black at frame 0 and nearest 0.5 s in the
base part, plus the default render's middle frame for takeover scenes.
Prints PASS/FAIL per check; exit 0 = all passed. Refuses to start below 10 GB free disk.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
SCENES = PLUGIN / "scenes"
DOCTOR = PLUGIN / "skills" / "editor-doctor" / "scripts"
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
sys.path.insert(0, str(DOCTOR))
sys.path.insert(0, str(PLUGIN / "skills" / "reel-canvas-build" / "scripts"))
import runtime as rt  # noqa: E402
import offline_selftest as ost  # noqa: E402  (NETGUARD, DEAD, run, remove: the offline pattern, reused)
import compose  # noqa: E402  (brand_params is pure: no saved state is read)

W, H, FPS = 1080, 1920, 30
SAFE = (60, 220, 960, 1470)  # x0, y0, x1, y1 (exclusive), the 900x1250 box
TEXT_ONLY_CSS = ("<style>.plate{background:transparent!important;border-color:transparent!important;"
                 "box-shadow:none!important;outline:none!important}</style>")
WORLD_TEXT_ONLY_CSS = ("<style>*,*::before,*::after{background:transparent!important;"
                       "border-color:transparent!important;box-shadow:none!important;outline:none!important}"
                       "img,video,canvas,iframe{visibility:hidden!important}"
                       "svg path,svg rect,svg circle,svg ellipse,svg line,svg polyline,svg polygon,svg image,svg use"
                       "{visibility:hidden!important}</style>")
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
    short = dict(default)
    short.update({k: "Go" if s.get("required") is True else "" for k, s in spec["slots"].items()})
    return default, worst, short


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


def project(tmp, name, html, scene_folder=None):
    proj = tmp / name
    (proj / "vendor").mkdir(parents=True)
    shutil.copy2(PLUGIN / "runtime" / "gsap" / "gsap.min.js", proj / "vendor" / "gsap.min.js")
    shutil.copytree(PLUGIN / "runtime" / "fonts", proj / "fonts")
    if scene_folder is not None and scene_folder.name.startswith("reel-"):
        for asset, source in compose.scene_check.reel_assets(scene_folder, html).items():
            (proj / "assets").mkdir(exist_ok=True)
            shutil.copy2(source, proj / "assets" / asset)
    (proj / "index.html").write_bytes(html.encode("utf-8"))
    return proj


def render(proj, fill, out, env, workers=2, seen=None, fps=FPS):
    """seen: a list that gets the render log's lines naming workers (the seek part shows them)."""
    vf = out.with_suffix(".vars.json")
    vf.write_bytes(json.dumps(fill).encode("utf-8"))
    t0 = time.perf_counter()
    rc, o, e = ost.run(rt.hyperframes_cmd("render", proj, "--format", "mov", "--fps", compose.fpsmod.parse_fps(str(fps)),
                                          "--workers", str(workers),
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


def hold_frames(spec, params, dur_frames, fps=FPS):
    """Resolve hold seconds using the rendered fill; round to the nearest frame and clamp."""
    frames = {dur_frames - 1}
    for hold in spec["holds"]:
        value = params.get(hold, spec["params"][hold]["default"]) if isinstance(hold, str) else hold
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("Hold times must be non-negative finite seconds.")
        frames.add(min(dur_frames - 1, round((value + .25) * fps)))
    return sorted(frames)


def hold_problems(slot_boxes, text_boxes, band, area="full"):
    """Judge exclusive pixel boxes at one hold; no renderer or image library required."""
    problems = []
    x, y, w, h = compose.world_area(area)
    safe = (max(SAFE[0], x) - x, max(SAFE[1], y) - y,
            min(SAFE[2], x + w) - x, min(SAFE[3], y + h) - y)
    if not slot_boxes:
        problems.append("no slot text")
    if any(x0 < safe[0] or y0 < safe[1] or x1 > safe[2] or y1 > safe[3]
           for x0, y0, x1, y1 in slot_boxes):
        problems.append("safe box")
    if any(x0 <= 0 or y0 <= 0 or x1 >= w or y1 >= h for x0, y0, x1, y1 in slot_boxes):
        problems.append("frame edge")
    if any(y0 < band[1] and y1 > band[0] for _, y0, _, y1 in text_boxes):
        problems.append("caption band")
    return problems


def hold_pixel_boxes(video, frame, area="full"):
    """One box per painted alpha row, preserving empty gaps (especially the caption band)."""
    buf = raw(video, "alphaextract", "gray", frame)
    _, _, w, h = map(int, compose.world_area(area))
    if len(buf) != w * h:
        raise ValueError(f"Could not decode hold frame {frame} of {video.name}")
    boxes = []
    for y in range(h):
        row = buf[y * w:(y + 1) * w]
        if row.count(0) != w:
            boxes.append((w - len(row.lstrip(b"\0")), y, len(row.rstrip(b"\0")), y + 1))
    return boxes


def caption_band_ranges(video, frames, band, area="full"):
    """Exclusive frame ranges with any painted band pixel; one native-size alpha decode, stride 1."""
    started = time.perf_counter()
    buf = raw(video, "alphaextract", "gray")
    _, _, width, height = map(int, compose.world_area(area))
    size = width * height
    if frames < 1 or len(buf) != frames * size:
        raise ValueError(f"Could not decode all {frames} frames of {video.name} for the caption band.")
    first, last = math.floor(band[0]) * width, math.ceil(band[1]) * width
    ranges = []
    for frame in range(frames):
        start, end = frame * size + first, frame * size + last
        if buf.count(0, start, end) != last - first:
            if ranges and ranges[-1][1] == frame:
                ranges[-1] = (ranges[-1][0], frame + 1)
            else:
                ranges.append((frame, frame + 1))
    print(f"  caption band: stride 1, {frames} frames in {time.perf_counter() - started:.3f} s", flush=True)
    return ranges


def slot_text_only(html):
    """Hide non-slot text without changing its layout, including mixed parent/slot content."""
    script = """<script>
(() => {
  const props = ['color', '-webkit-text-fill-color', '-webkit-text-stroke-color', 'text-shadow', 'fill', 'stroke'];
  // Snapshot before hiding ancestors, so nested slots retain their original inherited paint.
  const slots = Array.from(document.querySelectorAll('[data-slot], [data-slot] *')).map(el => {
    const css = getComputedStyle(el);
    return [el, props.map(p => css.getPropertyValue(p))];
  });
  for (const el of document.querySelectorAll('body, body *')) {
    if (!el.closest('[data-slot]')) el.setAttribute('data-mb-nonslot', '');
  }
  const css = document.createElement('style');
  css.textContent = '[data-mb-nonslot], [data-mb-nonslot]::before, [data-mb-nonslot]::after {' +
    'color:transparent!important;-webkit-text-fill-color:transparent!important;' +
    '-webkit-text-stroke-color:transparent!important;text-shadow:none!important;' +
    'fill:transparent!important;stroke:transparent!important}';
  document.head.appendChild(css);
  for (const [el, values] of slots) {
    for (let i = 0; i < props.length; i++) {
      el.style.setProperty(props[i], values[i], 'important');
    }
  }
})();
</script>"""
    return html.replace("</body>", script + "\n</body>", 1)


def world_hold_checks(sid, d, html, spec, frames, worst, tmov, tmp, env, fps=FPS):
    slots = project(tmp, sid + "-slotsonly", slot_text_only(html).replace(
        "</head>", WORLD_TEXT_ONLY_CSS + "\n</head>", 1), d)
    smov = tmp / f"{sid}-slotsonly.mov"
    ok, why = render(slots, worst, smov, env, fps=fps)
    if not ck(f"{sid}: renders (worst-case fill, slot text only)", ok, "" if ok else why):
        return
    for frame in hold_frames(spec, worst, frames, fps=fps):
        area = spec["area"]
        problems = hold_problems(hold_pixel_boxes(smov, frame, area), hold_pixel_boxes(tmov, frame, area),
                                 spec["caption_band"], area)
        for rule in ("no slot text", "safe box", "frame edge", "caption band"):
            ck(f"{sid}: hold frame {frame}: {rule}", rule not in problems)


def scene_test(sid, tmp, env, log, write_preview, part, write_stills=None, scenes_dir=SCENES,
               *, html_override=None, fill_override=None, fps=FPS):
    compose.scene_check._check_id(sid)
    d = scenes_dir / sid
    if not d.resolve().is_relative_to(scenes_dir.resolve()):
        raise ValueError("Scene folder points outside --scenes-dir")
    if sid.startswith("reel-"):
        problems = compose.scene_check.scene_problems(d)
        if not ck(f"{sid}: static scene contract", not problems, "; ".join(problems)):
            return
    spec = json.loads((d / "scene.json").read_text(encoding="utf-8"))
    html = html_override if html_override is not None else (d / "scene.html").read_text(encoding="utf-8")
    m = re.search(r'data-composition-id="%s"[^>]*' % re.escape(sid), html)
    dur = compose.Fraction(re.search(r'data-duration="([\d.]+)"', m.group(0)).group(1)) if m else 0
    fps = compose.fpsmod.as_fraction(str(fps))
    frames = round(dur * fps)
    default, worst, short = fills(spec, sid)
    if fill_override is not None:
        default.update(fill_override)
        # Keep worst-case text, but judge it at the selected word times and other selected params.
        worst.update({k: v for k, v in fill_override.items() if k in spec["params"] and
                      not (spec["params"][k]["type"] == "string" and "maxChars" in spec["params"][k])})
        short.update({k: v for k, v in fill_override.items() if k in spec["params"]})
    proj = project(tmp, sid, html, d)
    if part in ("all", "base", "review"):
        base_checks(sid, d, html, spec, frames, float(dur), default, worst, short, proj, tmp, env,
                    write_preview, write_stills, fps=fps)
    if part in ("all", "brand"):
        brand_checks(sid, html, spec, frames, default, proj, tmp, env, scenes_dir, fps=fps)
    if spec.get("category") == "counter" and part in ("all", "counter"):
        counter_checks(sid, spec, default, frames, proj, tmp, env, fps=fps)
    if part in ("seek", "review") or part == "all" and (sid.startswith("reel-") or spec.get("licence") != "own"):
        seek_checks(sid, frames, default, proj, tmp, env, fps=fps, world=spec.get("kind") == "world")
    n = sum(1 for _ in open(log, encoding="utf-8")) if log.exists() else 0
    ck(f"{sid}: no network attempts during lint and renders ({n} logged)", n == 0)


def base_checks(sid, d, html, spec, frames, dur, default, worst, short, proj, tmp, env, write_preview,
                write_stills=None, fps=FPS):
    rc, o, e = ost.run(rt.hyperframes_cmd("lint", proj, "--json"), env)
    kill_warm()
    try:
        j = json.loads(o[o.index("{"):])
        errs, warns = j["errorCount"], j["warningCount"]
        warnings = [x for x in j.get("findings", []) if x.get("severity") == "warning"]
        allowed = warns == len(warnings) and all(x.get("code") == "composition_file_too_large" for x in warnings)
        found = "; ".join(f"{x['code']}: {x['message']}" for x in j.get("findings", []))
    except (ValueError, KeyError):
        errs = warns = None
        allowed = False
        found = ost.tail(o + e)
    ck(f"{sid}: lint exit 0, 0 errors, only composition_file_too_large warnings", rc == 0 and errs == 0 and allowed,
       f"exit {rc}, {errs} errors, {warns} warnings" + (f": {found}" if found else ""))

    mov = tmp / f"{sid}.mov"
    ok, why = render(proj, default, mov, env, fps=fps)
    default_ok = ok
    if ck(f"{sid}: renders (default fill, MOV with alpha)", ok, "" if ok else why):
        s = probe(mov)
        width, height = map(int, compose.world_area(spec["area"])[2:]) if spec.get("kind") == "world" else (W, H)
        ck(f"{sid}: {s.get('width')}x{s.get('height')} {s.get('codec_name')} {s.get('pix_fmt')}, "
           f"{s.get('nb_read_frames')} frames (want {width}x{height} with alpha, {frames} = {dur} s x {fps})",
           (s.get("width"), s.get("height")) == (width, height) and str(s.get("pix_fmt", "")).startswith("yuva")
           and int(s.get("nb_read_frames") or -1) == frames)
        if write_preview:
            r = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", str(mov), "-vf",
                                f"select=eq(n\\,{frames - 1}),scale=270:480:flags=lanczos,format=rgba",
                                "-frames:v", "1", str(d / "preview.png")], capture_output=True, timeout=120)
            ck(f"{sid}: preview.png written from frame {frames - 1}", r.returncode == 0 and (d / "preview.png").exists(),
               r.stderr.decode("utf-8", "replace")[-300:])
        if write_stills is not None:
            still_frames = [0, min(frames - 1, round(0.5 * fps))]
            if spec.get("kind") == "takeover":
                still_frames.append(frames // 2)
            save_stills(sid, mov, still_frames, write_stills, fps=fps)

    text_css = WORLD_TEXT_ONLY_CSS if spec.get("kind") == "world" else TEXT_ONLY_CSS
    tproj = project(tmp, sid + "-textonly", html.replace("</head>", text_css + "\n  </head>", 1), d)
    tmov = tmp / f"{sid}-textonly.mov"
    ok, why = render(tproj, worst, tmov, env, fps=fps)
    if ck(f"{sid}: renders (worst-case fill, text only)", ok, "" if ok else why):
        if spec.get("kind") == "world":
            world_hold_checks(sid, d, html, spec, frames, worst, tmov, tmp, env, fps=fps)
        else:
            box, outside, total = text_box(tmov, frames)
            ck(f"{sid}: worst-case text stays in the safe box {SAFE}: text pixels {box}, {outside} of {total} outside",
               box is not None and outside == 0 and total > 0)

    if spec.get("kind") == "overlay" and "dy" in spec["params"]:
        baseline, moved = tmp / f"{sid}-dy-default.mov", tmp / f"{sid}-dy-up.mov"
        baseline_ok, why = render(tproj, default, baseline, env, fps=fps)
        ck(f"{sid}: dy default text render", baseline_ok, "" if baseline_ok else why)
        moved_ok, why = render(tproj, dict(default, dy=-200), moved, env, fps=fps)
        ck(f"{sid}: dy -200 text render", moved_ok, "" if moved_ok else why)
        before = text_box(baseline, frames)[0] if baseline_ok else None
        after = text_box(moved, frames)[0] if moved_ok else None
        expected = (before[0], before[1] - 200, before[2], before[3] - 200) if before else None
        ck(f"{sid}: dy shifts the measured default text box up by 200 pixels", before is not None
           and after is not None and all(abs(a - b) <= 2 for a, b in zip(after, expected)), (before, after, expected))

    if spec.get("kind") == "takeover" or write_stills is not None:
        smov = tmp / f"{sid}-short.mov"
        short_ok, why = render(proj, short, smov, env, fps=fps)
        ck(f"{sid}: renders (short fill, full scene)", short_ok, "" if short_ok else why)
        if short_ok and write_stills is not None:
            save_stills(sid + "-short", smov, (0, min(frames - 1, round(0.5 * fps))), write_stills, fps=fps)

    if spec.get("kind") == "takeover":
        gap = black_gap_s()
        wmov = tmp / f"{sid}-worst.mov"
        worst_ok, why = render(proj, worst, wmov, env, fps=fps)
        ck(f"{sid}: renders (worst-case fill, full scene)", worst_ok, "" if worst_ok else why)
        results = []
        for tag, video, rendered in (("default", mov, default_ok), ("worst-case", wmov, worst_ok),
                                     ("short", smov, short_ok)):
            clean, detail = black_picture(video, gap, fps=fps) if rendered else (False, "render failed")
            results.append((clean, f"{tag}: {detail}"))
        ck(f"{sid}: full-screen card never reads as a black picture (no black stretch >= {gap:g} s)",
           all(clean for clean, _ in results), "; ".join(detail for _, detail in results))


def save_stills(sid, video, frames, directory, fps=FPS):
    directory.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        still = directory / f"{sid}-f{frame:03d}.png"
        rc, o, e = ost.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"color=c=black:s={W}x{H}:r={fps}", "-i", video, "-filter_complex",
                            f"[0:v][1:v]overlay=shortest=1,select=eq(n\\,{frame})",
                            "-frames:v", "1", "-an", still], timeout=120)
        ck(f"{sid}: {still.name} written over black from frame {frame}", rc == 0 and still.exists(),
           ost.tail(o + e))


def black_gap_s():
    tuning = PLUGIN / "skills" / "reel-canvas-build" / "references" / "tuning.json"
    return json.loads(tuning.read_text(encoding="utf-8"))["tri2"]["black_gap_s"]


def black_picture(video, gap, fps=FPS):
    """The master blackdetect rule, including the scene's entrance and exit, over opaque black."""
    rc, o, e = ost.run([rt.tool("ffmpeg"), "-v", "info", "-f", "lavfi", "-i",
                        f"color=c=black:s={W}x{H}:r={fps}", "-i", video, "-filter_complex",
                        f"[0:v][1:v]overlay=shortest=1,blackdetect=d={gap}:pix_th=0.10",
                        "-an", "-f", "null", "-"], timeout=300)
    output = o + e
    stretches = [line.strip() for line in output.splitlines() if "black_start:" in line]
    decoded = bool(re.search(r"frame=\s*[1-9]\d*", output))
    clean = rc == 0 and decoded and not stretches
    return clean, "no black stretches" if clean else f"exit {rc}: " + ("; ".join(stretches) or ost.tail(output))



def brand_pixels(video, frame):
    """Visible pixels near fixture lime in the final frame; -1 means the frame did not decode."""
    buf = raw(video, "format=rgba", "rgba", frame)
    if len(buf) != W * H * 4:
        return -1
    return sum(1 for r, g, b, a in zip(buf[0::4], buf[1::4], buf[2::4], buf[3::4])
               if a and abs(r - 198) <= 40 and abs(g - 240) <= 40 and abs(b - 0) <= 40)


def brand_checks(sid, html, spec, frames, default, proj, tmp, env, scenes_dir=SCENES, fps=FPS):
    # H-B5: this fixture is independent of EDITOR_SE_HOME and never reads or writes the real saved style.
    fixture = tmp / "styles" / "default.json"
    fixture.parent.mkdir(exist_ok=True)
    fixture.write_bytes(b'{"accent": "#C6F000", "font": "Inter"}\n')
    saved = json.loads(fixture.read_text(encoding="utf-8"))
    params, notes = compose.brand_params(spec, html, {}, saved)
    ck(f"{sid}: fixture brand accent and Inter apply without notes", params == saved and not notes)
    refused, notes = compose.brand_params(spec, html, {}, {"font": "Comic Sans MS"})
    ck(f"{sid}: unavailable brand font is refused with a note and the scene default stays",
       refused["font"] == spec["params"]["font"]["default"] and "Comic Sans MS" not in json.dumps(refused)
       and len(notes) == 1
       and notes[0].startswith("Your style's font Comic Sans MS isn't one of the editor's built-in fonts, so it uses ")
       and spec["params"]["font"]["default"] in notes[0] and notes[0].endswith(" instead."))
    fill = {"id": sid, "slots": {key: default[key] for key in spec["slots"]},
            "params": {**{key: default[key] for key in spec["params"]}, **params}}
    # Default numeric displays need a fixture transcript too (VES-3); these are sample claims, never client words.
    words = list(fill["slots"].values()) + ([str(default["value"])] if "value" in default else [])
    problems = compose.scene_check.fill_problems(sid, fill, scenes=scenes_dir, words=words,
                                               reel=scenes_dir.parent if sid.startswith("reel-") else None)
    if not ck(f"{sid}: brand-applied fill passes scene_check", not problems, "; ".join(problems)):
        return
    branded = tmp / f"{sid}-brand.mov"
    ok, why = render(proj, {**default, **params}, branded, env, fps=fps)
    if ck(f"{sid}: renders fixture brand fill", ok, "" if ok else why):
        s = probe(branded)
        ck(f"{sid}: brand render is {W}x{H} with alpha and {frames} frames",
           (s.get("width"), s.get("height")) == (W, H) and str(s.get("pix_fmt", "")).startswith("yuva")
           and int(s.get("nb_read_frames") or -1) == frames)
        count = brand_pixels(branded, frames - 1)
        ck(f"{sid}: brand frame has pixels within 40 per channel of #C6F000", count > 0, f"{count} pixels")
    baseline = tmp / f"{sid}.mov"  # reuse the base part's default render when available
    if not baseline.exists():
        ok, why = render(proj, default, baseline, env, fps=fps)
        if not ck(f"{sid}: renders default fill for brand comparison", ok, "" if ok else why):
            return
    count = brand_pixels(baseline, frames - 1)
    ck(f"{sid}: default frame has no fixture lime", count == 0, f"{count} pixels")


def counter_checks(sid, spec, default, frames, proj, tmp, env, fps=FPS):
    if not ck(f"{sid}: has the counter params value and animate", {"value", "animate"} <= set(spec["params"])):
        return
    last = {}
    for tag, val, anim in (("count47", 47, True), ("static47", 47, False), ("static46", 46, False)):
        f = dict(default, value=val, animate=anim)
        out = tmp / f"{sid}-{tag}.mov"
        ok, why = render(proj, f, out, env, fps=fps)
        if ck(f"{sid}: renders {tag}", ok, "" if ok else why):
            last[tag] = raw(out, "format=rgba", "rgba", frames - 1)
    if len(last) == 3:
        same, diff = psnr(last["count47"], last["static47"]), psnr(last["count47"], last["static46"])
        ck(f"{sid}: last frame counting to 47 matches the static 47 frame (PSNR {same:.2f} dB, needs >= 45)",
           same >= 45)
        ck(f"{sid}: and differs from the static 46 frame (PSNR {diff:.2f} dB, needs < 40)", 0 <= diff < 40)


def compare_seek_pixels(straight, jump, *, world=False):
    """Compare 8-bit RGBA buffers; count a pixel once if any of its four channels differs."""
    if not straight or len(straight) != len(jump) or len(straight) % 4:
        raise ValueError("seek comparison needs two complete, equally sized RGBA frames")
    maximum = changed = 0
    for i in range(0, len(straight), 4):
        delta = max(abs(straight[i + c] - jump[i + c]) for c in range(4))
        maximum = max(maximum, delta)
        changed += delta != 0
    pixels = len(straight) // 4
    share = changed / pixels
    return (maximum <= 4 and changed * 20 <= pixels if world else straight == jump), maximum, share


def first_dom_difference(straight, jump):
    for a, b in zip(straight, jump):
        for prop in dict.fromkeys([*a, *b]):
            if (prop in a) != (prop in b) or a.get(prop) != b.get(prop):
                return f"{a['element']} property {prop}: straight {a.get(prop)!r}, jump {b.get(prop)!r}"
    if len(straight) != len(jump):
        extra = (straight if len(straight) > len(jump) else jump)[min(len(straight), len(jump))]
        return f"{extra['element']} property element count: straight {len(straight)}, jump {len(jump)}"
    return None


def seek_dom_check(sid, n, default, proj, tmp, env, fps=FPS):
    variables = tmp / f"{sid}-seek-dom.vars.json"
    variables.write_bytes(json.dumps(default).encode("utf-8"))
    puppeteer = rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
    rc, out, err = ost.run([rt.tool("node"), HERE / "seek_snapshot.cjs", puppeteer, rt.tool("chrome"),
                            proj / "index.html", variables, sid, str(n), str(float(fps))], env, timeout=120)
    try:
        if rc:
            raise ValueError(f"DOM probe exit {rc}: {ost.tail(out + err)}")
        snapshots = json.loads(out)
        if not snapshots["straight"] or not snapshots["jump"]:
            raise ValueError("DOM probe returned an empty snapshot")
        difference = first_dom_difference(snapshots["straight"], snapshots["jump"])
    except (ValueError, KeyError, TypeError) as e:
        difference = str(e)
    ck(f"{sid}: frame {n} DOM state after a jump " +
       ("differs from the straight render: " + difference if difference else "matches the straight render exactly"),
       difference is None)


def seek_checks(sid, frames, default, proj, tmp, env, fps=FPS, *, world=False):
    """Frame N of a sequential render (--workers 1) == frame N reached after a jump (--workers 2's second chunk),
    both on the screenshot capture path so only the jump differs."""
    n = math.ceil(frames / 2)
    seek_dom_check(sid, n, default, proj, tmp, env, fps=fps)
    got, pixels, alpha = {}, {}, b""
    senv = dict(env, PRODUCER_FORCE_SCREENSHOT="true")
    for tag, w in (("sequential", 1), ("jump", 2)):
        seen = []
        out = tmp / f"{sid}-seek-{tag}.mov"
        ok, why = render(proj, default, out, senv, workers=w, seen=seen, fps=fps)
        shot = any("screenshot capture" in l for l in seen)
        if ck(f"{sid}: seek render {tag} (--workers {w}, screenshot capture)", ok and shot,
              why if not ok else " | ".join(seen[:3])):
            stream = probe(out)
            pixels[tag] = raw(out, "format=rgba", "rgba", n)
            expected = int(stream.get("width", 0)) * int(stream.get("height", 0)) * 4
            if not ck(f"{sid}: seek frame {tag} decodes completely", expected > 0 and len(pixels[tag]) == expected,
                      f"{len(pixels[tag])} RGBA bytes, expected {expected}"):
                continue
            got[tag] = pixels[tag] if world else raw(out, "null", stream.get("pix_fmt") or "yuva444p10le", n)
            alpha = raw(out, "alphaextract", "gray", n) if w == 2 else alpha
    if len(got) == 2:
        ck(f"{sid}: frame {n} ({n / fps:.2f} s) is not blank", any(alpha))
        ok, maximum, share = compare_seek_pixels(pixels["sequential"], pixels["jump"], world=world)
        if not world:
            ok = bool(got["jump"]) and got["sequential"] == got["jump"]
        verdict = ("matches the straight render within tolerance" if world else
                   "matches the straight render byte for byte") if ok else "differs from the straight render"
        limits = " (limit 4)" if world else ""
        share_limit = " (limit 5%)" if world else " (byte-exact required)"
        native = "native frame bytes differ; " if not world and not ok else ""
        ck(f"{sid}: frame {n} after a jump {verdict}: {native}max difference {maximum} of 255{limits}, "
           f"{share * 100:.4f}% of pixels differ{share_limit}", ok)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene", action="append", help="scene id (repeatable); default every scene folder")
    ap.add_argument("--scenes-dir", type=Path, default=SCENES, help="scene folders (default: plugin scenes/)")
    ap.add_argument("--write-previews", action="store_true", help="write scenes/<id>/preview.png from the render")
    ap.add_argument("--write-stills", type=Path, metavar="DIR",
                    help="write default-render PNGs over black at frame 0 and nearest 0.5 s (base part)")
    ap.add_argument("--part", choices=("all", "base", "brand", "counter", "seek"), default="all",
                    help="base = lint + default + worst-case renders; counter = the 47/46 frame proof (category "
                         "counter); brand = fixture colour and font proof; seek = frame N sequential vs after a "
                         "jump (all = these, seek on reel- and vendored scenes)")
    a = ap.parse_args()
    free = shutil.disk_usage(tempfile.gettempdir()).free / 2 ** 30
    if free < MIN_FREE_GB:
        print(f"FAIL only {free:.1f} GB free disk; renders need {MIN_FREE_GB} GB. Free some space and run again.")
        return 1
    ids = a.scene or sorted(p.name for p in a.scenes_dir.iterdir() if (p / "scene.json").exists())
    for sid in ids:
        tmp = Path(tempfile.mkdtemp(prefix=f"scene-render-{sid}-"))
        try:
            env, log = make_env(tmp)
            scene_test(sid, tmp, env, log, a.write_previews, a.part, a.write_stills, a.scenes_dir)
        except Exception as e:  # a crash is a failed check, never a pass
            ck(f"{sid}: test run", False, f"stopped: {type(e).__name__}: {e}")
        finally:
            kill_warm()
            ost.remove(tmp)
    print("%d failed" % len(fails) if fails else "all passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
