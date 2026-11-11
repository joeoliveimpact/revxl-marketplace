#!/usr/bin/env python3
"""N3 light proof and isolated offline render cases for the glass card.

--part data uses only the standard library. Heavy cases require EDITOR_SE_HOME
and the same pinned tools as scene_render_test.py; each case runs in one call.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
SCENE = P / "scenes/glass-card-3d"
CHECKS = P / "skills/_shared/checks"
FAILS = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" [{detail}]" if detail else ""), flush=True)
    if not ok:
        FAILS.append(name)
    return ok


def load_check():
    spec = importlib.util.spec_from_file_location("three_d_check", CHECKS / "three_d_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixture(root, place="bottom", anchors=True, head=(400, 1130, 680, 1390)):
    """Same full-layout, scale-track and normalized face boxes as placer_test."""
    (root / "work").mkdir(parents=True, exist_ok=True)
    beat = dict(id="glass", start_f=0, end_f=120, layout="full",
                speech_anchor={"text": "Three steps"},
                scene=dict(id="glass-card-3d", slots={"text": "Three steps"}, params={"place": place}))
    docs = {
        "work/cuts.json": dict(fps=30, speed=1.0, segments=[dict(out_in_f=0, out_out_f=120)]),
        "work/scale_track.json": dict(schema=1, fps="30/1", total_f=120, style={"style": "punch-in"},
                                      keys=[dict(f=0, scale=1, ox=0.5, oy=0.38, layout="full")], tweens=[]),
        "beat-map-selection.json": dict(fps=30, beats=[beat]),
    }
    if anchors:
        docs["work/anchors.json"] = {"segments": [dict(seg=0, samples=[dict(
            f=0, x=0.5, y=0.65, box=[head[0]/1080, head[1]/1920, head[2]/1080, head[3]/1920])])]}
    for name, doc in docs.items():
        (root / name).write_bytes((json.dumps(doc) + "\n").encode("utf-8"))
    return dict(reel_dir=root, beats=[beat], fps=Fraction(30), cuts=docs["work/cuts.json"], render=None)


def data_checks():
    required = [CHECKS / "three_d_check.py", SCENE / "scene.html", SCENE / "scene.json",
                P / "runtime/three/VERSION.json"]
    if not ck("N3 deliverables exist", all(f.is_file() for f in required)):
        return
    mod = load_check()
    html = (SCENE / "scene.html").read_text(encoding="utf-8")
    spec = json.loads((SCENE / "scene.json").read_text(encoding="utf-8"))
    # D1 visible unions over all frames, WebGL then CSS; include a 12 px margin.
    for place, measured in (("top", ([108, 331, 915, 739], [132, 295, 895, 711])),
                            ("bottom", ([110, 1155, 915, 1446], [132, 1129, 895, 1420]))):
        band = spec["regions"][place]
        padded = [max(band[i], min(box[i] for box in measured) - 12) if i < 2 else
                  min(band[i], max(box[i] for box in measured) + 12) for i in range(4)]
        ck(place + ": card box is the measured union of both modes plus 12 px", spec["card"][place] == padded)
    ck("DR-3D: renderer leaves tone mapping to the composer", bool(re.search(
        r'renderer\.toneMapping\s*=\s*THREE\.NoToneMapping\s*;', html)))
    passes = re.findall(r'composer\.addPass\((.*?)\);', html, re.S)
    ck("DR-3D: final composer effect is ACES or AgX tone mapping", bool(passes)
       and bool(re.search(r'new EffectPass\(camera, new ToneMappingEffect\(\{\s*'
                          r'mode: ToneMappingMode\.(?:ACES_FILMIC|AGX)', passes[-1])))
    for name, value in (("PROBE_TIME", 1.2), ("MIN_VISIBLE_FRACTION", 0.02),
                        ("MIN_MEAN_LUMINANCE", 0.06), ("MIN_LUMINANCE_STDDEV", 0.02),
                        ("FLAT_VISIBLE_FRACTION", 0.60), ("MIN_LUMINANCE_RANGE", 0.08)):
        match = re.search(r'const ' + name + r'\s*=\s*([\d.]+)\s*;', html)
        ck(f"DR-3D: named {name} threshold", bool(match) and float(match[1]) == value)
    ck("DR-3D: probe reads GPU pixels and reports measurements", all(token in html for token in (
        'gl.readPixels(', 'root.dataset["3dProbe"]', 'dead-frame:', 'window.__N3_PLANT')))
    # Hashes of the complete CSS and classic-script blocks at 250cf61. Keep this
    # portable: a source archive need not contain that commit or even have Git.
    for label, pattern, digest in (
        ("styles", r'<style>(.*?)</style>',
         "c1da4b9fa8c72e734aa3ecf4407067e42d53b8831a95db07b13fadded35dc1b3"),
        ("fallback script", r'<script>(.*?)</script>',
         "c3cd8f052621a403d7b23a72b248f53d3a0bbab38795277ec0de70d18bcdff6e"),
    ):
        block = re.search(pattern, html, re.S)
        ck(f"DR-3D: CSS path {label} unchanged versus 250cf61", bool(block)
           and hashlib.sha256(block[1].encode("utf-8")).hexdigest() == digest)
    version = json.loads((P / "runtime/three/VERSION.json").read_text(encoding="utf-8"))
    names = {"three.module.js", "three.core.js", "LICENSE"}
    ck("three version and complete file manifest", version["package"] == "three" and
       version["version"] == "0.186.1" and set(version["files"]) == names and
       version["tarball_sha256"] == "8cd068708ea44f2c73c944b1cead2ba2f0d5c15c8fc194e5700f4e4f4a033fe7")
    sources = REPO / ".n3-notes/src/package"
    if not sources.is_dir():
        print("SKIP three: pinned sources not present; manifest SHA256s checked", flush=True)
    for name in sorted(names):
        blob = (P / "runtime/three" / name).read_bytes()
        ck(f"vendored {name} matches manifest", hashlib.sha256(blob).hexdigest() == version["files"][name])
        source = sources / (name if name == "LICENSE" else "build/" + name)
        if sources.is_dir():
            ck(f"vendored {name} is byte-identical to pinned source", source.is_file() and blob == source.read_bytes())
    refs = re.findall(r'(?:src|href)\s*=\s*[\"\']([^\"\']+)', html)
    refs += re.findall(r'url\([\"\']?([^\)\"\']+)', html)
    refs += re.findall(r'"three"\s*:\s*"([^"]+)"', html)
    ck("scene references only local runtime and fonts", bool(refs) and all(
        x in ("./vendor/gsap.min.js", "./vendor/three.module.js") or x.startswith("./fonts/") for x in refs)
       and "./vendor/three.module.js" in refs and not re.search(r'https?\s*:', html, re.I))
    problems = mod.capture_problems(html)
    ck("shipped capture is clean", problems == [], "; ".join(problems))
    cases = [
        ("variable colour", '<div id="card" data-capture style="color:var(--x)"></div>'),
        ("transparent gradient", '<style>#card{background:linear-gradient(transparent,#fff)}</style><div id="card" data-capture></div>'),
        ("thin gradient child", '<style>.bar{height:2px;background:linear-gradient(#fff,#aaa)}</style><div id="card" data-capture><i class="bar"></i></div>'),
        ("faint rgba stop", '<div data-capture style="background:linear-gradient(rgba(1,2,3,0.1),#fff)"></div>'),
        ("faint hsla stop", '<div data-capture style="background:linear-gradient(hsla(10,20%,30%,0.1),#fff)"></div>'),
        ("faint hex stop", '<div data-capture style="background:linear-gradient(#ffffff10,#fff)"></div>'),
        ("scene missing literal background", '<div class="scene" data-capture></div>'),
        ("invalid background keyword", '<div class="scene" data-capture style="background-color:none"></div>'),
        ("invalid hex background", '<div class="scene" data-capture style="background-color:#12345"></div>'),
        ("compound descendant selector", '<style>main > div#card.plate[data-capture]{color:var(--x)}</style><main><div id="card" class="plate" data-capture></div></main>'),
    ]
    for name, planted in cases:
        ck(f"capture rejects {name}", bool(mod.capture_problems(planted)))
    ck("capture excludes no-capture subtree", mod.capture_problems(
        '<div data-capture><div data-no-capture><b style="color:var(--x)"></b></div></div>') == [])
    ck("capture matches attributes rather than unrelated rules", mod.capture_problems(
        '<style>[data-x="yes"]{color:var(--x)}</style><div data-capture data-x="no"></div>') == [])
    scripts = "\n".join(re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S | re.I))
    ck("own scripts have no wall clock or autonomous frame loop", not re.search(
        r'Math\.random|\bDate\b|performance\.now|requestAnimationFrame|setTimeout|setInterval|setAnimationLoop', scripts))
    ck("no CSS animation or transition", not re.search(r'@keyframes|\b(?:animation|transition)\s*:', html))
    with tempfile.TemporaryDirectory(prefix="three-data-") as tmp:
        root = Path(tmp)
        bottom = fixture(root / "bottom")
        rows = mod.run(bottom)
        ck("bottom band blocks measured face", any(r["check"] == "3d-head-band" and r["level"] == "block" for r in rows))
        covered = fixture(root / "covered", head=(0, 386, 1080, 1692))
        covered["beats"][0]["broll"] = {"fit": "cover"}
        (covered["reel_dir"] / "beat-map-selection.json").write_bytes(
            (json.dumps(dict(fps=30, beats=covered["beats"])) + "\n").encode("utf-8"))
        ck("covered tight shot does not block the 3D card", mod.run(covered) == [])
        import scene_fill
        pick = dict(covered["beats"][0], speech_anchor=dict(text="Three steps", w0=0, w1=1))
        scene_fill.write_catalog(covered["reel_dir"], [pick], ["Three", "steps"], 30)
        suggestions = json.loads((covered["reel_dir"] / "scenes/suggest.json").read_text(encoding="utf-8"))
        ck("covered tight shot does not grey the 3D pick", "glass-card-3d" in suggestions["glass"])
        pick.pop("broll")
        scene_fill.write_catalog(covered["reel_dir"], [pick], ["Three", "steps"], 30)
        suggestions = json.loads((covered["reel_dir"] / "scenes/suggest.json").read_text(encoding="utf-8"))
        ck("catalog uses current picks rather than an older covered Send", "glass-card-3d" not in suggestions["glass"])
        top = fixture(root / "top", "top")
        ck("top band clears measured face", mod.run(top) == [])
        board = (P / "skills/reel-canvas-build/boards/beat-map/index.html").read_text(encoding="utf-8")
        remove = re.search(r'class: "remove-scene", text: "([^"]+)"', board)[1]
        ck("place advice uses the board's param label", 'text: param.name +' in board
           and "place" in spec["params"])
        for place in ("top", "bottom"):
            tight = fixture(root / ("tight-" + place), place, head=(0, 386, 1080, 1692))
            found = mod.run(tight)
            message = "This shot is too tight for the 3D card on beat 1."
            advice = f'On the Beat Map, open that beat and press "{remove}", or pick another card.'
            ck(place + ": both places hit, one block with truthful removal advice", len(found) == 1
               and found[0]["check"] == "3d-head-band" and found[0]["level"] == "block"
               and found[0]["msg"] == message and found[0]["advice"] == advice, str(found))
            ck(place + ": grouped refusal retains 3D advice", len(found) == 1
               and advice in mod.placer.compose.qa_block_lines(found)[0])
            early = mod.placer.compose.qa_check.run_checks(tight, "pre", only={"three_d_check"})
            ck(place + ": early subset reaches the real 3D block only", len(early) == 1
               and early[0]["check"] == "3d-head-band" and early[0]["module"] == "three_d_check", str(early))
        high = fixture(root / "high", "top", head=(200, 150, 880, 700))
        found = mod.run(high)
        ck("high head: top directs you only to clear bottom", len(found) == 1
           and found[0]["msg"] == "The 3D card would cover your eyes or mouth on beat 1."
           and found[0]["advice"] == 'On the Beat Map, set the 3D card\'s "place" to "bottom" on that beat, then Send.', str(found))
        high["beats"][0]["scene"]["params"]["place"] = "bottom"
        ck("high head: chosen bottom is clear", mod.run(high) == [])
        # Hair/chin alone must not block: only the shared eyes-and-mouth band counts.
        ck("card box, not declared band or full head", mod.region_problems({},
           {"scene": {"params": {"place": "top"}}},
           dict(spec, card=dict(spec["card"], top=[150, 402, 870, 450])), (0, 386, 1080, 1692)) == [])
        unknown = fixture(root / "unknown", anchors=False)
        ck("missing anchors warn", any(r["check"] == "3d-head-band" and r["level"] == "warn" for r in mod.run(unknown)))
        (unknown["reel_dir"] / "work/scale_track.json").write_bytes(b'{}\n')
        ck("broken placer inputs warn without crashing", any(r["level"] == "warn" for r in mod.run(unknown)))
        for param in ("place", "mode"):
            top["beats"][0]["scene"]["params"][param] = "unknown"
            ck(f"unknown {param} blocks", any(r["check"] == "3d-fill" and r["level"] == "block" for r in mod.run(top)))
            top["beats"][0]["scene"]["params"].pop(param)
        top["beats"][0]["scene"]["slots"]["text"] = "W" * 29
        ck("overlong slot blocks", any(r["check"] == "3d-fill" for r in mod.run(top)))
        ck("non-3D beats produce no rows", mod.run(dict(bottom, beats=[dict(scene={"id": "counter"})])) == [])
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(CHECKS / "check.py"),
                                 str(bottom["reel_dir"]), "--phase", "pre"], capture_output=True, text=True, timeout=30)
        report = json.loads((bottom["reel_dir"] / "work/qa.json").read_text(encoding="utf-8"))
        ck("hub discovers 3D pre check", result.returncode == 1 and any(
            r["check"] == "3d-head-band" and r["module"] == "three_d_check" for r in report["checks"]))
        ck("3D has a single face-check owner", sum(r["check"] == "3d-head-band" and r["level"] == "block"
           for r in report["checks"]) == 1 and not any(r["check"] == "card-on-face" for r in report["checks"]))
        ck("rows name the beat and start time", all(r["where"] == "Beat glass" and r["at"] == 0 for r in rows))
    ck("region function rejects overlap", bool(mod.region_problems({}, {"scene": {"params": {"place": "bottom"}}},
                                                                     spec, (400, 1200, 680, 1400))))


BLOCK_CONTEXT = """<script>
(() => {
  const get = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (name, ...args) {
    return /^(webgl|webgl2|experimental-webgl)$/.test(name) ? null : get.call(this, name, ...args);
  };
})();
</script>"""


def heavy_checks(args):
    """Reuse the offline builder, cold-cache environment and decoding tools.

    The lane chooses one --part per invocation. No tool imports occur for data.
    Every comparison uses screenshot capture on both sides, as in the existing
    seek harness, so GPU drawElement capture cannot disguise a seek mismatch.
    """
    import shutil
    import time
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import scene_render_test as harness

    if not ck("render disk headroom", shutil.disk_usage(tempfile.gettempdir()).free >= 10 * 2**30):
        return
    html = (SCENE / "scene.html").read_text(encoding="utf-8")
    spec = json.loads((SCENE / "scene.json").read_text(encoding="utf-8"))
    default = {k: v["default"] for group in ("slots", "params") for k, v in spec[group].items()}
    tmp = Path(tempfile.mkdtemp(prefix="three-render-"))
    cache = {}
    environments = {}
    try:
        def render(tag, mode, seed=7, place="bottom", workers=2, nogpu=False, blocked=False, fresh=False):
            key = (mode, seed, place, workers, nogpu, blocked)
            if key in cache and not fresh:
                return cache[key]
            # Each render gets its own home/cache/tmp folders, including repeats.
            case = tmp / tag
            case.mkdir()
            env, log = harness.make_env(case)
            env["PRODUCER_FORCE_SCREENSHOT"] = "true"
            page = html.replace('<script src=', BLOCK_CONTEXT + '\n<script src=', 1) if blocked else html
            # Fail a forced GPU case that silently falls back. This observer is
            # test-only: a wrong path makes the picture blank, which fails the
            # visibility assertion; correct-path pixels remain untouched.
            expected = "webgl" if mode == "webgl" else "css"
            path_guard = """
      const assertPath = () => { root.style.opacity = root.dataset['3dPath'] === EXPECTED ? '1' : '0'; };
      new MutationObserver(assertPath).observe(root, { attributes: true, attributeFilter: ['data-3d-path'] });
      assertPath();
""".replace("EXPECTED", json.dumps(expected))
            page = page.replace('finally { loading.itemsLoaded = 1; loading.itemEnd("glass-card-setup"); }',
                                'finally { loading.itemsLoaded = 1; loading.itemEnd("glass-card-setup"); }' + path_guard)
            proj = harness.project(case, "project", page)
            imports = json.loads(re.search(r'<script type="importmap">(.*?)</script>', page, re.S)[1])["imports"]
            for name in {"three.module.js", "three.core.js", *(Path(value).name for value in imports.values())}:
                shutil.copy2(P / "runtime/three" / name, proj / "vendor" / name)
            out = case / "card.mov"
            vf = case / "variables.json"
            vf.write_bytes(json.dumps(dict(default, mode=mode, seed=seed, place=place)).encode("utf-8"))
            limit = 170 if nogpu or blocked else 600
            command = harness.rt.hyperframes_cmd("render", proj, "--format", "mov", "--workers", str(workers),
                                                 "--strict-variables", "--variables-file", vf, "-o", out)
            if nogpu:
                command.append("--no-browser-gpu")
            start = time.monotonic()
            rc, stdout, stderr = harness.ost.run(command, env, timeout=limit)
            elapsed = time.monotonic() - start
            harness.kill_warm()
            network = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
            ok = ck(f"{tag}: MOV render finishes", rc == 0 and out.is_file() and elapsed < limit,
                    f"{elapsed:.1f}s; exit {rc}; " + harness.ost.tail(stderr if rc else stdout))
            ck(f"{tag}: zero network attempts", not network, str(len(network)))
            ck(f"{tag}: screenshot capture", "screenshot capture" in stdout + stderr)
            if not ok:
                return None
            stream = harness.probe(out)
            ck(f"{tag}: 1080x1920, 120 alpha frames", (stream.get("width"), stream.get("height")) == (1080, 1920)
               and int(stream.get("nb_read_frames") or -1) == 120 and str(stream.get("pix_fmt", "")).startswith("yuva"))
            alpha = harness.raw(out, "alphaextract", "gray", 60)
            ck(f"{tag}: visible picture", len(alpha) == 1080 * 1920 and sum(v > 0 for v in alpha) > 10000)
            result = (out, stream)
            environments[out] = env
            cache[key] = result
            return result

        def hashes(result):
            if result is None:
                return []
            out, stream = result
            rc, stdout, stderr = harness.ost.run([harness.rt.tool("ffmpeg"), "-v", "error", "-i", out,
                "-map", "0:v:0", "-pix_fmt", stream["pix_fmt"], "-f", "framemd5", "-"], timeout=300)
            frames = [line.rsplit(",", 1)[-1].strip() for line in stdout.splitlines() if line and not line.startswith("#")]
            ck(f"{out.parent.name}: decode every frame for hashing", rc == 0 and len(frames) == 120, stderr[-200:])
            return frames

        def equal(name, left, right, every=True):
            a, b = hashes(left), hashes(right)
            ck(name, len(a) == len(b) == 120 and (a == b if every else a[60] == b[60]))

        parts = {"render", "nogpu", "blocked", "seed", "seek", "region"} if args.part == "all" else {args.part}
        if "render" in parts:
            render("webgl", "webgl")
        if "nogpu" in parts:
            equal("auto without GPU frame 60 equals CSS", render("nogpu", "auto", nogpu=True),
                  render("nogpu-css", "css", nogpu=True), every=False)
        if "blocked" in parts:
            equal("blocked WebGL auto equals CSS on every frame", render("blocked", "auto", blocked=True),
                  render("blocked-css", "css", blocked=True))
        if "seed" in parts:
            for mode in ("webgl", "css"):
                first = render(f"{mode}-seed7-a", mode)
                second = render(f"{mode}-seed7-b", mode, fresh=True)
                equal(f"{mode}: same seed identical on all frames", first, second)
                one, other = hashes(first), hashes(render(f"{mode}-seed8", mode, seed=8))
                ck(f"{mode}: seed 8 changes the picture", len(one) == len(other) == 120 and one != other)
        if "seek" in parts:
            for mode in ("webgl", "css"):
                one = render(f"{mode}-sequential", mode, workers=1)
                two = render(f"{mode}-jump", mode, workers=2)
                if one and two:
                    # Preserve native pixel precision, matching scene_render_test.
                    a = harness.raw(one[0], "null", one[1]["pix_fmt"], 60)
                    b = harness.raw(two[0], "null", two[1]["pix_fmt"], 60)
                    ck(f"{mode}: frame 60 identical after a fresh-page jump", bool(a) and a == b)
        if "region" in parts:
            for mode in ("webgl", "css"):
                for place in ("top", "bottom"):
                    result = render(f"{mode}-{place}", mode, place=place)
                    if result:
                        region_check(harness, result[0], spec["regions"][place], f"{mode}-{place}")
                        measured = harness.compose.measure_scene_box(result[0], environments[result[0]])
                        x0, y0, x1, y1 = spec["card"][place]
                        ck(f"{mode}-{place}: D1 visible union inside declared card", measured is not None
                           and x0 <= measured[0] < measured[2] <= x1
                           and y0 <= measured[1] < measured[3] <= y1, str(measured))
        if args.write_previews:
            result = render("preview", "webgl")
            if result:
                rc, _, err = harness.ost.run([harness.rt.tool("ffmpeg"), "-v", "error", "-y", "-i", result[0],
                    "-vf", "select=eq(n\\,119),scale=270:480:flags=lanczos,format=rgba", "-frames:v", "1", SCENE / "preview.png"])
                ck("preview written from final frame", rc == 0 and (SCENE / "preview.png").is_file(), err[-200:])
        if args.write_clips:
            args.write_clips.mkdir(parents=True, exist_ok=True)
            for mode in ("webgl", "css"):
                result = render(f"clip-{mode}", mode)
                if result:
                    out = args.write_clips / f"glass-card-3d-{mode}.mp4"
                    rc, _, err = harness.ost.run([harness.rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=0x808080:s=1080x1920:r=30:d=4", "-i", result[0], "-filter_complex",
                        "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]", "-map", "[v]", "-an",
                        "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", out], timeout=300)
                    ck(f"{mode}: mid-grey MP4 clip written", rc == 0 and out.is_file(), err[-200:])
    finally:
        harness.kill_warm()
        harness.ost.remove(tmp)


def region_check(harness, video, region, name):
    """Scan 16-bit alpha, including sub-8-bit values, across all 120 frames."""
    x0, y0, x1, y1 = region
    command = [harness.rt.tool("ffmpeg"), "-v", "error", "-i", str(video), "-vf", "alphaextract",
               "-pix_fmt", "gray16le", "-f", "rawvideo", "-"]
    # A temporary file avoids retaining half a gigabyte of decoded alpha in RAM.
    with tempfile.TemporaryFile() as decoded:
        result = subprocess.run(command, stdout=decoded, stderr=subprocess.PIPE, timeout=300)
        decoded.seek(0)
        frames, outside, visible = 0, False, False
        while True:
            frame = decoded.read(1080 * 1920 * 2)
            if not frame:
                break
            if len(frame) != 1080 * 1920 * 2:
                outside = True
                break
            frames += 1
            visible = visible or any(frame)
            for y in range(1920):
                row = frame[y * 2160:(y + 1) * 2160]
                if y < y0 or y >= y1:
                    outside = outside or any(row)
                else:
                    outside = outside or any(row[:x0 * 2]) or any(row[x1 * 2:])
        ck(f"{name}: every nonzero alpha pixel stays inside band", result.returncode == 0 and
           frames == 120 and visible and not outside, f"{frames} frames; outside={outside}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part", choices=("data", "render", "nogpu", "blocked", "seed", "seek", "region", "all"), default="data")
    ap.add_argument("--write-previews", action="store_true")
    ap.add_argument("--write-clips", type=Path)
    args = ap.parse_args()
    try:
        if args.part in ("data", "all"):
            data_checks()
        if args.part != "data" or args.write_previews or args.write_clips:
            heavy_checks(args)
    except Exception as exc:
        ck("test completes", False, f"{type(exc).__name__}: {exc}")
    print(f"{len(FAILS)} failed" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
