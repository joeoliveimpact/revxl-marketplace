#!/usr/bin/env python3
"""S8.2 caption pixels in the real 720p compositor, one case per call under the heavy lock.

Run with the editor's Python and EDITOR_SE_HOME; --out keeps sampled PNGs,
the rendered index.html and captions.json. Requires 10 GB free disk.
Only stdlib is imported; installed editor tools are called through runtime.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from editor_test_state import isolated_home
_spec = importlib.util.spec_from_file_location("caption_render_fixtures", HERE / "render_engine_test.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)
CAPTIONS = rt.PLUGIN / "skills" / "reel-captions" / "scripts"
captions = rt.load("captions", CAPTIONS)
TOOL_HOME = rt.rt.state_dir()
LOOKS = ("clean", "bold-pop", "boxed", "karaoke", "outline-caps")
CASES = tuple("look-" + look for look in LOOKS) + ("layout-switch", "ask", "none", "tri6", "tri6-marker", "two-styles")
SCALE = 720 / 1080


def fixture(root, look, layouts=("full", "full", "full")):
    ws, reel = rt.style_reel(root, rt.STATIC_SRC.replace("d=4", "d=6"),
                             {"style": "layout-switch"} if "split" in layouts else rt.IDENTITY, layouts)
    # Two three-word chunks per segment, with empty frames before and after each.
    # Symmetric letter shapes make the visible text's bounding centre measurable.
    words = [{"id": f"w_{i:04d}", "word": "mom", "start": round(base + offset, 2),
              "end": round(base + offset + .10, 2)}
             for i, (base, offset) in enumerate((base, offset) for base in (0, 2, 4)
                                               for offset in (.2, .36, .52, 1.2, 1.36, 1.52))]
    words[-1].update(start=5.64, end=5.74)  # last caption ends at total_f: exercise placer's inclusive API
    send = json.loads((reel / "beat-map-selection.json").read_text(encoding="utf-8"))
    for i, b in enumerate(send["beats"]):
        b["speech_anchor"] = {"text": " ".join(w["word"] for w in words[i * 6:(i + 1) * 6]),
                              "w0": i * 6, "w1": i * 6 + 5}
    if look is None:
        send.pop("caption_style", None)
    else:
        send["caption_style"] = {"style": look}
    rt.wj(reel / "work/edit_map.cut.json", {"words": words})
    rt.wj(reel / "beat-map-selection.json", send)
    return ws, reel, words, send


def preview(ws, reel, out):
    rc, log = rt.compose(ws, "preview", "--reel-dir", f"videos/{rt.REEL}", "--keep-project")
    rt.no_traceback("captions", log)
    video = reel / "renders" / rt.names()[0]
    passed = rt.ck("preview renders at 720x1280", rc == 0 and video.is_file()
                   and rt.size(video) == (720, 1280), log[-600:])
    page_path = reel / "work/render-tmp/proj/index.html"
    page = page_path.read_text(encoding="utf-8") if page_path.is_file() else ""
    rt.ck("the actual rendered page is kept and uses no CSS animation or translateX",
          bool(page) and "@keyframes" not in page and "translateX" not in page)
    doc_path = reel / "work/captions.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8")) if doc_path.is_file() else {}
    rt.ck("the placed caption plan is saved", bool(doc), doc)
    for path in (page_path, doc_path):
        if path.is_file():
            shutil.copy2(path, out / path.name)
    return video if passed else None, page, doc, log


def region(box):
    return tuple(round(v * SCALE) for v in box)


def ink(frame, box):
    """Bright or accent pixels above the flat dark source, as absolute (x, y)."""
    x0, y0, x1, y1 = region(box)
    return {(x, y) for y in range(y0, y1) for x in range(x0, x1)
            if max(frame[(y * 720 + x) * 3:(y * 720 + x) * 3 + 3]) > 110}


def save_pngs(video, frames, out):
    frames = sorted(frames)
    select = "+".join(f"eq(n,{n})" for n in frames)
    rc, log = rt.run([rt.rt.tool("ffmpeg"), "-v", "error", "-y", "-i", video,
                      "-vf", f"select='{select}'", "-fps_mode", "passthrough",
                      "-start_number", "0", out / "sample-%03d.png"])
    rt.ck("sampled PNGs are kept", rc == 0 and all((out / f"sample-{i:03d}.png").is_file()
                                                 for i in range(len(frames))), log[-300:])
    for i, n in enumerate(frames):
        path = out / f"sample-{i:03d}.png"
        if path.is_file():
            path.replace(out / f"frame-{n:03d}.png")


def look_case(root, out, look):
    ws, reel, _, _ = fixture(root, look)
    video, page, doc, log = preview(ws, reel, out)
    if video is None:
        return
    chunks = doc.get("chunks", [])
    rt.ck("each of the three segments has two or three chunks",
          all(2 <= sum(a <= c["start_f"] < e for c in chunks) <= 3 for a, e in rt.SEGS3), chunks)
    rt.ck("the final caption can end at the reel's exclusive frame 150", bool(chunks)
          and chunks[-1]["end_f"] == 150)
    rt.ck("no face anchors: the lowest safe spot is noted", not (reel / "work/anchors.json").exists()
          and any("lowest safe caption spot" in n for n in doc["notes"])
          and "note: No head samples" in log)
    pop = captions.STYLES[look]["pop"]["frames"]
    frames = set()
    for c in chunks:
        frames.update((c["start_f"], c["start_f"] + pop + 1))
        if c["start_f"] > 0:
            frames.add(c["start_f"] - 1)
        if c["end_f"] < 150:
            frames.add(c["end_f"])
    pixels = rt.grab(video, frames, "rgb24")
    save_pngs(video, frames, out)
    for c in chunks:
        start, end, label = c["start_f"], c["end_f"], f"chunk {c['i']}"
        settled = ink(pixels[start + pop + 1], c["box"])
        rt.ck(label + ": caption pixels inside its saved box", len(settled) > 40, len(settled))
        centre = (min(x for x, _ in settled) + max(x for x, _ in settled)) / 2 if settled else -999
        want = (c["box"][0] + c["box"][2]) / 2 * SCALE
        rt.ck(label + ": visible horizontal centre within 3 px (TRI-4)", abs(centre - want) <= 3,
              (centre, want))
        onset = ink(pixels[start], c["box"])
        rt.ck(label + ": pop first frame differs from the settled frame", len(onset ^ settled) > 10)
        before = start - 1
        if before >= 0 and not any(p["start_f"] <= before < p["end_f"] for p in chunks if p is not c):
            rt.ck(label + ": no caption pixels before start", not ink(pixels[before], c["box"]))
        if end < 150 and not any(p["start_f"] <= end < p["end_f"] for p in chunks if p is not c):
            rt.ck(label + ": hard kill at the exclusive end frame (F-13)", not ink(pixels[end], c["box"]))


def layout_case(root, out):
    ws, reel, words, _ = fixture(root, "clean", ("full", "split", "full"))
    # A phrase spans each layout boundary; individual words still have a whole frame.
    for last, first, switch in ((5, 6, 2), (11, 12, 4)):
        words[last].update(start=switch - .04, end=switch + .06)
        words[first].update(start=switch + .04, end=switch + .14)
    rt.wj(reel / "work/edit_map.cut.json", {"words": words})
    video, _, doc, _ = preview(ws, reel, out)
    rt.ck("full / split / full renders", video is not None)
    chunks = doc.get("chunks", [])
    for switch in (50, 100):
        rt.ck(f"no caption straddles layout switch {switch}", bool(chunks) and all(
            not c["start_f"] < switch <= c["end_f"] - 1 for c in chunks), chunks)
        rt.ck(f"words planted on both sides of switch {switch}", any(
            c["end_f"] == switch for c in chunks) and any(c["start_f"] == switch + 1 for c in chunks))


def two_styles_case(root, out):
    # All planted assets and saved styles live in scratch copies, never in the installed editor.
    root = root.resolve()
    plugin = root / "plugin"
    shutil.copytree(rt.PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    spec = importlib.util.spec_from_file_location("caption_font_fixtures", HERE / "captions_test.py")
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    family = helpers.plant_brand_font(plugin)
    original = rt.rt.state_dir()
    state = json.loads((original / "state.json").read_text(encoding="utf-8"))
    for component in state.get("components", {}).values():
        for name, path in component.get("bins", {}).items():
            component["bins"][name] = str((original / path).resolve())
    ws, reel, _, send = fixture(root, None)
    send.pop("edit_style", None)
    send["word_marks"] = [{"w": 0, "mark": "key"}]
    rt.wj(reel / "beat-map-selection.json", send)
    styles = (
        {"style_id": "client-a", "caption_style": {"style": "bold-pop"}, "accent": "#E0218A",
         "font": family, "edit_style": {"style": "punch-in"}},
        {"style_id": "client-b", "caption_style": {"style": "boxed"}, "accent": "#22C55E",
         "edit_style": {"style": "layout-switch"}},
    )
    samples, docs = [], []
    sample_f = None
    for saved in styles:
        client = saved["style_id"]
        home, kept = root / (client + "-state"), out / client
        (home / "styles").mkdir(parents=True)
        kept.mkdir(parents=True, exist_ok=True)
        rt.wj(home / "state.json", state)
        rt.wj(home / "styles/default.json", saved)
        # HyperFrames resolves its CLI relative to EDITOR_SE_HOME. Copy its installed
        # packages too; browser and ffmpeg binaries above remain read-only absolute paths.
        shutil.copytree(original / "hyperframes", home / "hyperframes")
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(home)}), \
                patch.object(rt, "COMPOSE", plugin / "skills/reel-canvas-build/scripts/compose.py"):
            video, page, doc, _ = preview(ws, reel, kept)
            if video is None:
                return
            look = saved["caption_style"]["style"]
            rt.ck(client + ": captions.json records its saved look and accent",
                  doc.get("style", {}).get("style") == look
                  and doc.get("style", {}).get("accent") == saved["accent"], doc.get("style"))
            track = json.loads((reel / "work/scale_track.json").read_text(encoding="utf-8"))
            rt.ck(client + ": saved editing style reaches the compositor",
                  track["style"]["style"] == saved["edit_style"]["style"], track["style"])
            font_file = reel / "work/render-tmp/proj/fonts/Caption-Test.woff2"
            rt.ck(client + ": caption font is the saved licensed face or Inter",
                  doc.get("font", {}).get("family") == saved.get("font", "Inter")
                  and ('font-family: "Caption Test", "Inter";' in page if "font" in saved
                       else '#captions .caption {position: absolute; font-family: "Inter";' in page)
                  and font_file.read_bytes() == (plugin / "runtime/fonts/Caption-Test.woff2").read_bytes())
            chunk = doc["chunks"][0]
            if sample_f is None:
                sample_f = chunk["start_f"] + max(captions.STYLES[look][k]["frames"] for k in ("pop", "punch")) + 2
            rt.ck(client + ": the common sample frame is inside the first caption",
                  chunk["start_f"] <= sample_f < chunk["end_f"])
            frame = rt.grab(video, [sample_f], "rgb24")[sample_f]
            rt.ck(client + ": visible caption pixels inside its box", len(ink(frame, chunk["box"])) > 40)
            save_pngs(video, [sample_f], kept)
            samples.append(frame)
            docs.append(doc)
    # Compare the same coordinates inside BOTH caption boxes on the identical dark source.
    boxes = [region(doc["chunks"][0]["box"]) for doc in docs]
    x0, y0 = max(b[0] for b in boxes), max(b[1] for b in boxes)
    x1, y1 = min(b[2] for b in boxes), min(b[3] for b in boxes)
    if not rt.ck("the two caption boxes overlap", x1 > x0 and y1 > y0, boxes):
        return
    delta = sum(abs(samples[0][i] - samples[1][i])
                for y in range(y0, y1) for i in range((y * 720 + x0) * 3, (y * 720 + x1) * 3))
    mad = delta / ((x1 - x0) * (y1 - y0) * 3)
    print(f"  two-styles caption frame {sample_f}: mean absolute RGB difference {mad:.3f} (threshold 8)")
    rt.ck("two saved client styles render clearly different caption pixels", mad > 8, mad)


def ask_case(root, out):
    ws, reel, _, _ = fixture(root, None)
    # Only state.json is needed before the ask: keep binary paths absolute in this copy.
    original = rt.rt.state_dir()
    state = json.loads((original / "state.json").read_text(encoding="utf-8"))
    for component in state.get("components", {}).values():
        for name, path in component.get("bins", {}).items():
            component["bins"][name] = str((original / path).resolve())
    home = root / "ask-state"
    (home / "styles").mkdir(parents=True)
    rt.wj(home / "state.json", state)
    rt.wj(home / "styles/default.json", {})
    previous = os.environ.get("EDITOR_SE_HOME")
    try:
        os.environ["EDITOR_SE_HOME"] = str(home)
        rc, log = rt.compose(ws, "preview", "--reel-dir", f"videos/{rt.REEL}")
    finally:
        if previous is None:
            os.environ.pop("EDITOR_SE_HOME", None)
        else:
            os.environ["EDITOR_SE_HOME"] = previous
    rt.no_traceback("caption ask", log)
    rt.ck("missing caption look: exit 1 and the plain ask line", rc == 1
          and log.strip().splitlines()[-1] == captions.ASK, log[-500:])
    rt.ck("the ask renders nothing", not any((reel / "renders").rglob("*"))
          and not (reel / "work/render-tmp").exists())


def none_case(root, out):
    ws, reel, words, _ = fixture(root, "none")
    video, page, doc, _ = preview(ws, reel, out)
    rt.ck("no captions still renders with no caption layer", video is not None and "#captions" not in page
          and 'id="captions"' not in page and doc.get("chunks") == [])
    rt.ck("every word is declared off", doc.get("declared_drops") == [
        {"w": i, "why": "captions off"} for i in range(len(words))])


def tri6_case(root, out, marker=False):
    ws, reel, words, send = fixture(root, "clean")
    for word, text in zip(words[:3], ("this", "doesn't", "work.")):
        word["word"] = text
    send["beats"][0]["speech_anchor"]["text"] = " ".join(w["word"] for w in words[:6])
    send["word_marks"] = [{"w": 2, "mark": "emph"}]
    if marker:
        send["caption_style"]["mark_look"] = "marker"
    rt.wj(reel / "work/edit_map.cut.json", {"words": words})
    rt.wj(reel / "beat-map-selection.json", send)
    video, page, doc, _ = preview(ws, reel, out)
    chunks = doc.get("chunks", [])
    marked = [w["w"] for c in chunks for w in c["words"] if w["mark"] == "emph"]
    punched = [w["w"] for c in chunks for w in c["words"] if w["punch"]]
    rt.ck("TRI-6: doesn't and work are marked and punched together, never work alone",
          video is not None and marked == punched == [1, 2] and any(
              [w["w"] for w in c["words"] if w["punch"]] == [1, 2] for c in chunks), (marked, punched))
    rt.ck("TRI-6: exactly one punch event in the rendered page", page.count('class="cap-punch"') == 1
          and page.count('tl.fromTo("#cap-0-punch-1"') == 1)
    if marker and video is not None:
        rt.ck("marker: exactly one band wraps both truthful words in the rendered page",
              page.count('class="cap-marker"') == 1 and bool(re.search(
                  r'class="cap-marker"[^>]*>.*?doesn&#x27;t.*?work\..*?</span></span>', page)))
        marked_chunk = next(c for c in chunks if any(w["mark"] for w in c["words"]))
        first = next(w["start_f"] for w in marked_chunk["words"] if w["mark"])
        settled = first + max(captions.STYLES["clean"][k]["frames"] for k in ("pop", "punch")) + 1
        geometry_js = r"""
const {pathToFileURL} = require('url');
(async () => {
  const [pup, chrome, file, seconds, profile] = process.argv.slice(1);
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath:chrome, headless:'shell',
    args:['--no-sandbox', '--allow-file-access-from-files'], userDataDir:profile});
  try {
    const page = await browser.newPage();
    await page.setViewport({width:720, height:1280});
    await page.goto(pathToFileURL(file).href, {waitUntil:'load'});
    await page.evaluate(() => document.fonts.ready);
    const result = await page.evaluate(t => {
      window.__timelines.main.seek(Number(t));
      const bands = [...document.querySelectorAll('.cap-marker')];
      const run = bands[0];
      return {count:bands.length, text:run.textContent, band:run.querySelector('.cap-marker-swipe').getBoundingClientRect().toJSON(),
        words:[...run.querySelectorAll('.cap-word')].map(w => ({text:w.textContent,
          box:w.getBoundingClientRect().toJSON()}))};
    }, seconds);
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => { console.error(String(e.stack || e)); process.exit(1); });
"""
        pup = rt.rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
        rc, log = rt.run([rt.rt.tool("node"), "-e", geometry_js, pup, rt.rt.tool("chrome"),
                          reel / "work/render-tmp/proj/index.html", str(settled / 25), root / "marker-profile"], timeout=60)
        rt.ck("marker: rendered DOM geometry is available", rc == 0, log[-400:])
        if rc == 0:
            geometry = json.loads(log.strip().splitlines()[-1])
            rt.ck("marker: one band covers both word boxes", geometry["count"] == 1
                  and [w["text"] for w in geometry["words"]] == ["doesn't", "work."]
                  and all(geometry["band"]["left"] <= w["box"]["left"] + 1
                          and geometry["band"]["right"] >= w["box"]["right"] - 1 for w in geometry["words"]))
            frame = rt.grab(video, [settled], "rgb24")[settled]
            save_pngs(video, [settled], out)
            band = geometry["band"]
            for word in geometry["words"]:
                box = word["box"]
                pixels = [frame[(y * 720 + x) * 3:(y * 720 + x) * 3 + 3]
                          for y in range(max(0, int(band["top"]) + 2), min(1280, int(band["bottom"]) - 2))
                          for x in range(max(0, int(box["left"]) + 2), min(720, int(box["right"]) - 2))]
                # The translucent yellow fill over the dark source, excluding white ink and bright accent letters.
                count = sum(80 < r < 180 and g > 70 and b < 90 and r > b * 1.4 and g > b * 1.3
                            for r, g, b in pixels)
                rt.ck(f"marker pixels behind {word['text']} at the settled frame", count > 20, count)
        rc, log = rt.run([sys.executable, "-X", "utf8", "-I", CAPTIONS / "captions.py",
                          "picker", "--reel-dir", reel])
        rt.ck("picker command builds the render fixture's document and five full-size stills", rc == 0
              and (reel / "work/look-picker.json").is_file() and all(
                  rt.size(reel / f"work/look-picker/frame-{name}.jpg") == (1080, 1920)
                  for name in captions.beat_schema.LAYOUTS), log[-400:])


def tri6_marker_case(root, out):
    tri6_case(root, out, marker=True)


@isolated_home(packages=True)
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", required=True, choices=CASES)
    ap.add_argument("--out", help="folder for kept PNGs and rendered page/plan")
    ap.add_argument("--tmp", help="fixture parent folder (default: next to the editor state)")
    args = ap.parse_args()
    parent = Path(args.tmp or TOOL_HOME.parent)
    free = shutil.disk_usage(parent).free / 2 ** 30
    if free < 10:
        print(f"FAIL only {free:.1f} GB free disk; renders need 10 GB. Free some space and run again.")
        return 1
    out = Path(args.out or parent / "captions-render-out") / args.case
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="captions-render-", dir=parent) as tmp:
        try:
            if args.case.startswith("look-"):
                look_case(Path(tmp), out, args.case[5:])
            else:
                {"layout-switch": layout_case, "ask": ask_case, "none": none_case,
                 "tri6": tri6_case, "tri6-marker": tri6_marker_case,
                 "two-styles": two_styles_case}[args.case](Path(tmp), out)
        except Exception as exc:
            rt.ck(args.case + ": test run", False, f"{type(exc).__name__}: {exc}")
        finally:
            rt.ck("no warmCheck.js left running", rt.warm_left() == 0)
    print(f"{args.case} took {time.perf_counter() - started:.1f} s; "
          + (f"{len(rt.fails)} failed" if rt.fails else "all passed"))
    return 1 if rt.fails else 0


if __name__ == "__main__":
    sys.exit(main())
