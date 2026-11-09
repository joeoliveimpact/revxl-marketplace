#!/usr/bin/env python3
"""G2-c provenance, board assets, local runtime rules and isolated seek proofs.

Light: --part data (standard library only). Heavy: one of motion, bloom,
quarks, region, contrast or deadframe, using three_d_test's offline MOV harness.
A missing/withheld lead fails its heavy proof; it never falls back to another
lead. The lane must pass each heavy proof before offering that render lead.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
SOURCES = REPO / ".n3-notes/g2c"
SCENE = P / "scenes/glass-card-3d"
SKETCHES = P / "skills/reel-canvas-build/boards/sketches"
TWEAK = P / "skills/reel-first-cuts/boards/tweak-board"
FAILS = []
PINNED_TARBALLS = {
    "motion": "c95d4f404fcd111d85e3e22497956cc3afc1d17c01f5ce1c218aaafb6095693b",
    "postprocessing": "ce7495c521102470ce6284563436f6bb673050282a795328a64857ea282e6222",
    "three.quarks": "512c3cd57f52ec2d77a2be7562273ceecc20c2d61ad313dcc6bcb078f05040f7",
    "quarks.core": "2cc16d071de883b1c607e74b7a4c5492f4977576648775df3f31f62f08821871",
    "tweakpane": "8cf819860e51128ea6031528c2ec6a92413785928d49c16170562d3f9f39134d",
}


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" [{detail}]" if detail else ""), flush=True)
    if not ok:
        FAILS.append(name)
    return ok


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def provenance(package, version, folder, manifest_name, files):
    manifest_path = folder / manifest_name
    if not ck(f"{package}: manifest exists", manifest_path.is_file()):
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tarball = SOURCES / f"{package}-{version}.tgz"
    ck(f"{package}: pinned identity and complete manifest", manifest.get("package") == package
       and manifest.get("version") == version and set(manifest.get("files", {})) == set(files))
    ck(f"{package}: pinned tarball SHA256", manifest.get("tarball_sha256") == PINNED_TARBALLS[package])
    if tarball.is_file():
        ck(f"{package}: tarball SHA256", sha(tarball.read_bytes()) == manifest.get("tarball_sha256"))
    else:
        print(f"SKIP {package}: pinned sources not present; manifest SHA256s checked", flush=True)
    with (tarfile.open(tarball, "r:gz") if tarball.is_file() else contextlib.nullcontext()) as archive:
        for name, source in files.items():
            file = folder / name
            if not ck(f"{package}: {name} exists", file.is_file()):
                continue
            blob = file.read_bytes()
            entry = manifest["files"].get(name)
            digest = entry.get("sha256") if isinstance(entry, dict) else entry
            ck(f"{package}: {name} manifest SHA256", sha(blob) == digest)
            converted = isinstance(entry, dict) and entry.get("line_endings") == "CRLF->LF"
            if isinstance(entry, dict):
                ck(f"{package}: {name} declared LF conversion", converted and b"\r" not in blob
                   and set(entry) == {"sha256", "upstream_sha256", "line_endings"}
                   and bool(re.fullmatch(r"[0-9a-f]{64}", entry.get("upstream_sha256", ""))))
            if archive is not None:
                member = archive.extractfile("package/" + source)
                upstream = member.read() if member is not None else None
                if converted and upstream is not None:
                    ck(f"{package}: {name} upstream SHA256", sha(upstream) == entry["upstream_sha256"])
                ck(f"{package}: {name} equals tarball file" + (" after CRLF->LF" if converted else " byte for byte"),
                   upstream is not None and (upstream.replace(b"\r\n", b"\n") if converted else upstream) == blob)


def runtime_checks():
    """New expectations live here because the original selftests are outside N3."""
    sys.path.insert(0, str(P / "scripts"))
    sys.path.insert(0, str(P / "skills/_shared"))
    sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
    import scene_check
    import compose

    spec = json.loads((SCENE / "scene.json").read_text(encoding="utf-8"))
    html = (SCENE / "scene.html").read_text(encoding="utf-8")
    minimal_map = '<script type="importmap">{"imports":{"three":"./vendor/three.module.js"}}</script>'
    page = re.sub(r'<script type="importmap">.*?</script>', minimal_map, html, flags=re.S)
    # Remove the shipped optional module import when testing a minimal map.
    page = page.replace('await import("postprocessing")', 'await Promise.resolve({})')
    page = page.replace('await import("three.quarks")', 'await Promise.resolve({})')
    for name in ("postprocessing", "three.quarks", "quarks.core"):
        mapping = {"three": "./vendor/three.module.js", name: f"./vendor/{name}.js"}
        mapped = page.replace(minimal_map, '<script type="importmap">' + json.dumps({"imports": mapping}) + '</script>')
        mapped = mapped.replace('import * as THREE from "three";', f'import * as THREE from "three"; import * as Lead from "{name}";')
        ck(f"checker: exact {name} import passes", scene_check.html_problems(spec["id"], spec, mapped) == [])
        for label, bad in (("other name", mapped.replace('"' + name + '":', '"unknown":')),
                           ("other path", mapped.replace(f"./vendor/{name}.js", "./vendor/other.js"))):
            ck(f"checker: {name} {label} fails", bool(scene_check.html_problems(spec["id"], spec, bad)))
        ck(f"checker: {name} without mapping fails", bool(scene_check.html_problems(spec["id"], spec,
           page.replace('import * as THREE from "three";', f'import * as THREE from "three"; import "{name}";'))))
    src = '<script src="./vendor/motion.js"></script>'
    gsap = '<script src="./vendor/gsap.min.js"></script>'
    for sid in ("callout", "glass-card-3d"):
        folder = P / "scenes" / sid
        doc = json.loads((folder / "scene.json").read_text(encoding="utf-8"))
        original = (folder / "scene.html").read_text(encoding="utf-8")
        ck(f"checker: {sid} Motion second passes", scene_check.html_problems(sid, doc, original.replace(gsap, gsap + src)) == [])
        for label, bad in (("first", src + gsap), ("duplicate", gsap + src + src),
                           ("other script", gsap + src.replace("motion.js", "other.js")),
                           ("async", gsap + src.replace("<script ", "<script async "))):
            ck(f"checker: {sid} Motion {label} fails", bool(scene_check.html_problems(sid, doc, original.replace(gsap, bad))))
    with tempfile.TemporaryDirectory(prefix="leads-data-") as tmp:
        root = Path(tmp)
        scenes = root / "scenes"
        shutil.copytree(P / "scenes/callout", scenes / "callout")
        sp = scenes / "callout/scene.json"
        hp = scenes / "callout/scene.html"
        doc = json.loads(sp.read_text(encoding="utf-8"))
        doc["category"] = "3d"
        sp.write_bytes(json.dumps(doc).encode("utf-8"))
        imports = {"imports": dict(scene_check.LEAD_IMPORTS)}
        hp.write_bytes((hp.read_text(encoding="utf-8").replace(gsap, gsap + src)
                        + '<script type="importmap">' + json.dumps(imports) + '</script>').encode("utf-8"))
        runtime = root / "three"
        runtime.mkdir()
        for name in ("three.module.js", "three.core.js", "postprocessing.js", "three.quarks.js", "quarks.core.js"):
            (runtime / name).write_bytes(("// fixture " + name + "\n").encode("utf-8"))
        motion = root / "motion"
        motion.mkdir()
        (motion / "motion.js").write_bytes(b"// fixture motion\n")
        beat = dict(id="lead", start_f=0, end_f=120, scene=dict(id="callout", slots={"text": "Hello"}, params={}))
        with patch.object(scene_check, "SCENES", scenes), patch.object(compose, "THREE_RUNTIME", runtime), patch.object(compose, "MOTION_RUNTIME", motion):
            project = root / "project"
            compose.scene_project(project, beat, Fraction(30))
            ck("compose: copies every import-map runtime byte for byte", all(
                (project / "vendor" / f.name).read_bytes() == f.read_bytes() for f in runtime.iterdir()))
            ck("compose: copies Motion byte for byte", (project / "vendor/motion.js").read_bytes() == (motion / "motion.js").read_bytes())
            for missing in ("postprocessing.js", "three.quarks.js", "quarks.core.js"):
                blob = (runtime / missing).read_bytes()
                (runtime / missing).unlink()
                try:
                    compose.scene_project(root / ("missing-" + missing), beat, Fraction(30))
                    ck(f"compose: missing {missing} stops", False)
                except compose.Stop as error:
                    ck(f"compose: missing {missing} stops with plain line", error.code == 1 and error.lines == (
                        "The 3D engine files are missing, reinstall the editor.",))
                (runtime / missing).write_bytes(blob)
            doc["category"] = "callout"
            sp.write_bytes(json.dumps(doc).encode("utf-8"))
            compose.scene_project(root / "2d", beat, Fraction(30))
            ck("compose: 2D Motion needs no 3D engine", (root / "2d/vendor/motion.js").is_file()
               and not (root / "2d/vendor/three.module.js").exists())
            (motion / "motion.js").unlink()
            try:
                compose.scene_project(root / "missing-motion", beat, Fraction(30))
                ck("compose: missing Motion stops", False)
            except compose.Stop as error:
                ck("compose: missing Motion stops with plain line", error.code == 1 and error.lines == (
                    "The Motion engine file is missing, reinstall the editor.",))


def data_checks():
    provenance("motion", "14.6.0", P / "runtime/motion", "VERSION.json",
               {"motion.js": "dist/motion.js", "LICENSE": "LICENSE.md"})
    provenance("postprocessing", "6.39.5", P / "runtime/three", "VERSION-postprocessing.json",
               {"postprocessing.js": "build/index.js", "LICENSE-postprocessing": "LICENSE.md"})
    for package in ("three.quarks", "quarks.core"):
        provenance(package, "0.17.1", P / "runtime/three", f"VERSION-{package}.json",
                   {f"{package}.js": f"dist/{package}.esm.js", f"LICENSE-{package}": "LICENSE"})
    for folder in (SKETCHES, TWEAK):
        provenance("tweakpane", "4.0.5", folder, "VERSION.json", {"tweakpane.min.js": "dist/tweakpane.min.js"})
        ck(f"{folder.name}: Tweakpane licence supplied", (folder / "LICENSE-tweakpane").is_file())
        manifest = json.loads((folder / "VERSION.json").read_text(encoding="utf-8"))
        licence = manifest.get("licence", {})
        ck(f"{folder.name}: pinned upstream Tweakpane licence", licence == {
            "source_url": "https://raw.githubusercontent.com/cocopon/tweakpane/4.0.5/LICENSE.txt",
            "sha256": "385accdd560bac0013a2965fe9d39c45808b7542d2bbb3ef0cceeb60b7da71c3"}
            and (folder / "LICENSE-tweakpane").is_file()
            and sha((folder / "LICENSE-tweakpane").read_bytes()) == licence["sha256"])
        source = SOURCES / "tweakpane-LICENSE.txt"
        if source.is_file():
            ck(f"{folder.name}: Tweakpane licence equals pinned source",
               (folder / "LICENSE-tweakpane").read_bytes() == source.read_bytes())
        else:
            print("SKIP tweakpane licence: pinned sources not present; manifest SHA256s checked", flush=True)
    ck("Tweakpane board copies are byte-identical", (SKETCHES / "tweakpane.min.js").read_bytes() == (TWEAK / "tweakpane.min.js").read_bytes())
    spec = json.loads((SCENE / "scene.json").read_text(encoding="utf-8"))
    html = (SCENE / "scene.html").read_text(encoding="utf-8")
    declarations = {v["id"]: v for v in json.loads(re.search(r"data-composition-variables='(.*?)'", html, re.S)[1])}
    for name, choices, default in (("glow", ["soft", "bloom"], "bloom"), ("dust", ["points", "quarks"], "quarks")):
        ck(f"{name} enum and defaults agree", spec["params"].get(name) == dict(type="string", enum=choices, default=default)
           and declarations.get(name) == dict(id=name, type="string", default=default))
    ck("scene map uses exact local lead paths", json.loads(re.search(r'<script type="importmap">(.*?)</script>', html, re.S)[1]) == {
        "imports": {"three": "./vendor/three.module.js", "postprocessing": "./vendor/postprocessing.js",
                    "three.quarks": "./vendor/three.quarks.js", "quarks.core": "./vendor/quarks.core.js"}})
    runtime_checks()
    for name, file, args in (
            ("scene_check selftest", P / "scripts/scene_check.py", ["--selftest"]),
            ("scene_check shipped scenes", P / "scripts/scene_check.py", ["check", str(P / "scenes")]),
            ("compose selftest", P / "skills/reel-canvas-build/scripts/compose.py", ["--selftest"])):
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(file), *args], capture_output=True,
                                text=True, encoding="utf-8", timeout=90)
        ck(name, result.returncode == 0, result.stdout.strip() + result.stderr.strip())
    sys.path.insert(0, str(P / "skills/editor-doctor/scripts"))
    import board_sync
    for folder in (SKETCHES, TWEAK):
        ck(f"{folder.name}: board sync includes library, manifest and licence", all(
            name in board_sync.template_files(folder) for name in ("tweakpane.min.js", "VERSION.json", "LICENSE-tweakpane")))
    ck("lead reference is at most 80 lines", len((P / "skills/reel-canvas-build/references/leads.md").read_text(encoding="utf-8").splitlines()) <= 80)


def motion_fixture():
    """Temporary, never a catalog scene. Direct WAAPI properties only."""
    return '''<!doctype html>
<html lang="en" data-composition-variables='[]'><head><meta charset="utf-8">
<script src="./vendor/gsap.min.js"></script><script src="./vendor/motion.js"></script>
<style>html,body{margin:0;width:1080px;height:1920px;overflow:hidden}
#motion-proof{position:relative;width:1080px;height:1920px}
#tile{position:absolute;left:160px;top:600px;width:300px;height:300px;background:#4f8cff}</style>
</head><body><div id="motion-proof" data-composition-id="motion-proof" data-start="0"
 data-duration="4" data-fps="30" data-width="1080" data-height="1920"><div id="tile"></div></div>
<script>
window.__hyperframes.getVariables();
window.__timelines = window.__timelines || {};
const state = {t:0}, tl = gsap.timeline({paused:true});
tl.to(state, {t:4, duration:4, ease:"none"}); window.__timelines["motion-proof"] = tl;
Motion.animate(document.getElementById("tile"), {
  transform:["translateX(0px)","translateX(420px)"], opacity:[0.35,1]
}, {duration:4, ease:"linear", autoplay:false});
// If Motion chooses its JS driver, this fixture must fail visibly. The
// HyperFrames WAAPI adapter owns currentTime; the scene never seeks it itself.
if (!document.getAnimations().length) document.getElementById("tile").hidden = true;
</script></body></html>'''


def heavy_checks(args):
    part = args.part
    import time
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import scene_render_test as harness
    import three_d_test
    if not ck("render disk headroom", shutil.disk_usage(tempfile.gettempdir()).free >= 10 * 2**30):
        return
    spec = json.loads((SCENE / "scene.json").read_text(encoding="utf-8"))
    defaults = {k: v["default"] for group in ("slots", "params") for k, v in spec[group].items()}
    tmp = Path(tempfile.mkdtemp(prefix="leads-render-"))
    clips = {}
    try:
        def render(lead, tag, workers, place="bottom", mode="webgl", plant=None):
            case = tmp / tag
            case.mkdir()
            env, network_log = harness.make_env(case)
            env["PRODUCER_FORCE_SCREENSHOT"] = "true"
            page = motion_fixture() if lead == "motion" else (SCENE / "scene.html").read_text(encoding="utf-8")
            if lead != "motion":
                if plant:
                    # Test fixture only: production never assigns __N3_PLANT.
                    injection = '<script>window.__N3_PLANT = ' + json.dumps(plant) + ''';
window.__N3_WARNINGS = [];
const originalWarn = console.warn;
console.warn = (...args) => { window.__N3_WARNINGS.push(args.join(" ")); originalWarn.apply(console, args); };
</script>
'''
                    page = page.replace('<script type="module">', injection + '<script type="module">', 1)
                # A CSS fallback must never count as a successful GPU lead.
                guard = '''
      const assertPath = () => { root.style.opacity = PATH_READY ? '1' : '0'; };
      new MutationObserver(assertPath).observe(root, {attributes:true, attributeFilter:['data-3d-path']});
      assertPath();
'''.replace("PATH_READY", "root.dataset['3dPath'] === 'css'" if mode == "css" or plant else
            "root.dataset['3dPath'] === 'webgl' && root.dataset['3dGlow'] === 'bloom' && "
            "root.dataset['3dDust'] === 'quarks' && root.dataset['3dFocus'] === 'depth-of-field'")
                if plant or mode != "css":
                    reason = {"black": "near-black", "flat": "flat", "lowcontrast": "lowcontrast"}.get(plant)
                    probe_guard = '''
      const probe = JSON.parse(root.dataset['3dProbe'] || '{}');
      const measured = ['visibleFraction', 'mean', 'stddev', 'p5', 'p95', 'range'];
      const probeOK = probe.time === 1.2 && measured.every(k => Number.isFinite(probe[k]))
        && probe.reason === REASON && FALLBACK_OK;
      console.log('DR-3D probe: ' + JSON.stringify(probe));
      if (!probeOK) root.style.opacity = '0';
'''.replace("REASON", json.dumps(reason)).replace("FALLBACK_OK", (
                        "root.dataset['3dFallback'] === " + json.dumps("dead-frame:" + reason)
                        + " && window.__N3_WARNINGS.length === 1 && window.__N3_WARNINGS[0] === "
                        + json.dumps("The 3D card rendered dark or flat on this computer, so the simple version was used instead.")
                        if plant else "!root.dataset['3dFallback'] && probe.visibleFraction >= 0.02 && probe.mean >= 0.06"
                        " && !(probe.visibleFraction > 0.60 && probe.stddev < 0.02) && probe.range >= 0.08"))
                    guard += probe_guard
                page = page.replace('finally { loading.itemsLoaded = 1; loading.itemEnd("glass-card-setup"); }',
                                    'finally { loading.itemsLoaded = 1; loading.itemEnd("glass-card-setup"); }' + guard)
            project = harness.project(case, "project", page)
            sources = [(P / "runtime/motion/motion.js")] if lead == "motion" else [
                P / "runtime/three" / name for name in ("three.module.js", "three.core.js", "postprocessing.js",
                                                       "three.quarks.js", "quarks.core.js")]
            for source in sources:
                shutil.copy2(source, project / "vendor" / source.name)
            variables = {} if lead == "motion" else dict(defaults, mode=mode, place=place)
            vf = case / "variables.json"
            vf.write_bytes(json.dumps(variables).encode("utf-8"))
            out = case / "lead.mov"
            start = time.monotonic()
            rc, stdout, stderr = harness.ost.run(harness.rt.hyperframes_cmd(
                "render", project, "--format", "mov", "--workers", str(workers),
                "--strict-variables", "--variables-file", vf, "-o", out), env, timeout=600)
            harness.kill_warm()
            network = network_log.read_text(encoding="utf-8").splitlines() if network_log.exists() else []
            ok = ck(f"{tag}: MOV finishes", rc == 0 and out.is_file() and time.monotonic() - start < 600,
                    f"{time.monotonic()-start:.1f}s, exit {rc}; " + harness.ost.tail(stderr if rc else stdout))
            ck(f"{tag}: zero network attempts", not network, str(len(network)))
            ck(f"{tag}: screenshot capture", "screenshot capture" in stdout + stderr)
            if not ok:
                return None
            stream = harness.probe(out)
            ck(f"{tag}: 1080x1920, 120 alpha frames", (stream.get("width"), stream.get("height")) == (1080, 1920)
               and int(stream.get("nb_read_frames") or -1) == 120 and str(stream.get("pix_fmt", "")).startswith("yuva"))
            alpha = harness.raw(out, "alphaextract", "gray", 60)
            ck(f"{tag}: frame 60 is not blank", len(alpha) == 1080*1920 and sum(v > 0 for v in alpha) > 10000)
            return out, stream

        def hashes(result):
            if result is None:
                return []
            out, stream = result
            rc, stdout, stderr = harness.ost.run([harness.rt.tool("ffmpeg"), "-v", "error", "-i", out,
                "-map", "0:v:0", "-pix_fmt", stream["pix_fmt"], "-f", "framemd5", "-"], timeout=300)
            frames = [line.rsplit(",", 1)[-1].strip() for line in stdout.splitlines() if line and not line.startswith("#")]
            ck(f"{out.parent.name}: decode all frames for hashes", rc == 0 and len(frames) == 120, stderr[-200:])
            return frames

        if part == "region":
            for place in ("top", "bottom"):
                result = render("default", f"default-{place}", 2, place)
                if result:
                    before = len(three_d_test.FAILS)
                    three_d_test.region_check(harness, result[0], spec["regions"][place], f"default-{place}")
                    FAILS.extend(three_d_test.FAILS[before:])
        elif part in ("contrast", "deadframe"):
            if part == "deadframe":
                css = render("default", "deadframe-css", 2, mode="css")
                for plant in ("black", "flat", "lowcontrast"):
                    planted = render("default", f"deadframe-{plant}", 2, mode="auto", plant=plant)
                    a = harness.raw(css[0], "null", css[1]["pix_fmt"], 60) if css else b""
                    b = harness.raw(planted[0], "null", planted[1]["pix_fmt"], 60) if planted else b""
                    ck(f"deadframe {plant}: auto GPU fallback frame 60 equals forced CSS", bool(a) and a == b)
            for mode in ("webgl", "css"):
                clips[mode] = render("default", f"contrast-{mode}", 1,
                                     mode="auto" if part == "deadframe" and mode == "webgl" else mode)
            if all(clips.values()):
                inputs = [harness.rt.tool("ffmpeg"), "-v", "info", "-y", "-i", clips["webgl"][0],
                          "-i", clips["css"][0], "-f", "lavfi", "-i", "color=c=0x808080:s=1080x1920:r=30:d=4"]
                # Explicit RGBA after compositing, with identical opaque alpha.
                grey = ("[2:v]format=rgba,split=2[bg0][bg1];[0:v]format=rgba[fg0];[1:v]format=rgba[fg1];"
                        "[bg0][fg0]overlay=shortest=1:format=auto,format=rgba[a];"
                        "[bg1][fg1]overlay=shortest=1:format=auto,format=rgba[b];")
                rc, stdout, stderr = harness.ost.run(inputs + ["-filter_complex", grey + "[a][b]psnr=stats_file=-[v]",
                    "-map", "[v]", "-frames:v", "120", "-f", "null", "-"], timeout=300)
                frames = re.findall(r"^n:\s*(\d+)\s", stdout, re.M)
                average = re.search(r"PSNR .*?average:([\d.]+|inf)", stderr)
                value = float(average[1]) if average else float("inf")
                ck("default WebGL vs CSS: RGBA PSNR over all 120 frames below 24 dB",
                   rc == 0 and frames == [str(i) for i in range(1, 121)] and value < 24,
                   f"{value:.4f} dB; {len(frames)} frames; exit {rc}")
                if args.sheet:
                    args.sheet.parent.mkdir(parents=True, exist_ok=True)
                    select = "select='eq(n,20)+eq(n,60)+eq(n,110)',tile=1x3"
                    rc, _, err = harness.ost.run(inputs + ["-filter_complex", grey +
                        f"[a]{select}[left];[b]{select}[right];[left][right]hstack=inputs=2,format=rgba[v]",
                        "-map", "[v]", "-frames:v", "1", "-update", "1", args.sheet], timeout=300)
                    ck("contrast sheet: frames 20/60/110, WebGL left and CSS right over mid-grey",
                       rc == 0 and args.sheet.is_file(), err[-200:] if rc else str(args.sheet))
        elif part != "data":
            first = render(part, part + "-sequential", 1)
            jump = render(part, part + "-jump", 2)
            cold = render(part, part + "-cold-repeat", 1)
            if first and jump:
                a = harness.raw(first[0], "null", first[1]["pix_fmt"], 60)
                b = harness.raw(jump[0], "null", jump[1]["pix_fmt"], 60)
                ck(f"{part}: frame 60 byte-identical after fresh-page jump", bool(a) and a == b)
            a, b = hashes(first), hashes(cold)
            ck(f"{part}: independent cold render identical on every frame", len(a) == len(b) == 120 and a == b)
            if part == "motion" and first:
                a = harness.raw(first[0], "null", first[1]["pix_fmt"], 59)
                b = harness.raw(first[0], "null", first[1]["pix_fmt"], 61)
                ck("Motion moves visibly around frame 60", bool(a) and bool(b) and a != b)
        if args.write_clips:
            args.write_clips.mkdir(parents=True, exist_ok=True)
            for mode in ("webgl", "css"):
                result = clips.get(mode) or render("default", f"clip-{mode}", 1, mode=mode)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("data", "motion", "bloom", "quarks", "region", "contrast", "deadframe"), default="data")
    parser.add_argument("--sheet", type=Path, help="contrast PNG, WebGL left / CSS right, frames 20/60/110")
    parser.add_argument("--write-clips", type=Path, help="write GPU and fallback MP4s over mid-grey")
    args = parser.parse_args()
    try:
        if args.sheet and args.part != "contrast":
            parser.error("--sheet requires --part contrast")
        if args.part == "data":
            data_checks()
        if args.part != "data" or args.write_clips:
            heavy_checks(args)
    except Exception as error:
        ck("test completes", False, f"{type(error).__name__}: {error}")
    print(f"{len(FAILS)} failed" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
