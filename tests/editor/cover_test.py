"""G6 cover picker, truthful title, scene, frame-zero embed and hub proof.

Usage: <editor python> -X utf8 -I tests/editor/cover_test.py --case NAME|all
Set EDITOR_SE_HOME to the editor state. Cases: selftest, pick, title, scene,
embed, hub. --reel-src DIR is copied read only into scratch for media cases.
Scene/title/embed and browser work self-lock; exits 75/76 mean blocked.
Editor choices use editor_test_state.isolated_home; hub apply alone uses the
installed renderer state. The scene case creates the shipped preview if missing.
"""
import argparse
import contextlib
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P = HERE.parents[1] / "plugins/editor-superengine"
SCRIPT = P / "skills/reel-cover/scripts/cover_pick.py"
sys.path[:0] = [str(SCRIPT.parent), str(P / "scripts"), str(HERE)]
from editor_test_state import isolated_home
import cover_pick as cover

INSTALLED_HOME = cover.rt.state_dir()
HEAVY = Path("C:/Workspaces/Content Studio/output/scripts/heavy_lock.py")
DEFAULT_REEL = Path("C:/Work/_scratch/editor-superengine-0.2.0/renders/S7/run1/reel")
CASES = ("selftest", "title_geometry", "pick", "title", "scene", "embed", "hub")
FAILS = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f": {detail}" if detail and not ok else ""), flush=True)
    if not ok:
        FAILS.append(name)


def command(script, *args, timeout=2400):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(script), *map(str, args)],
                          env=cover.rt.python_env(), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def fixture(root, source):
    if not source.is_dir():
        raise ValueError("The read-only reel fixture is missing; supply --reel-src DIR.")
    reel = root / "videos/REEL_A"
    shutil.copytree(source, reel, ignore=shutil.ignore_patterns("__pycache__"))
    # Paths are resolved only in this copy; the source fixture is never edited.
    for name in ("cover.json", "cover-picker.state.json", "cover-picker-selection.json"):
        (reel / name).unlink(missing_ok=True)
    return reel


def prepare(reel):
    cover.candidates(reel)
    return cover.read(reel / "cover/candidates.json")


def case_selftest(root, source):
    result = command(SCRIPT, "--selftest")
    ck("cover selftest", result.returncode == 0 and "selftest ok" in result.stdout, result.stdout + result.stderr)
    spec = cover.read(P / "scenes/cover-title/scene.json")
    for lines in (1, 2):
        box = cover.title_box(None, lines)
        ck(f"no-face {lines}-line title uses scene default inside safe zone",
           box[1] == spec["params"]["y"]["default"] / 1920 == 1100 / 1920
           and box[3] <= 1470 / 1920)
    # Moving only the scene default must move the fallback too, without using
    # the top-of-frame alternative when the low box cannot fit.
    scene = root / "scenes/cover-title/scene.json"
    with patch.object(cover, "P", root):
        spec["params"]["y"]["default"] = 1280
        cover.save(scene, spec)
        placement = cover.title_placement(None, 2)
        ck("no-face overflow uses one size smaller at scene default",
           placement["size"] == "smaller" and placement["box"][1] == 1280 / 1920
           and placement["box"][3] <= 1470 / 1920)
        spec["params"]["y"]["default"] = 1291
        cover.save(scene, spec)
        try:
            cover.title_placement(None, 2)
        except cover.Stop as error:
            ck("no-face overflow refuses after smaller size", str(error) == cover.TITLE_REFUSAL)
        else:
            ck("no-face overflow refuses after smaller size", False)
    board = (P / "skills/reel-cover/boards/cover-picker/index.html").read_text(encoding="utf-8")
    ck("board includes no-face note", cover.NO_FACE_NOTE in board)
    result = command(SCRIPT, "apply", "--reel-dir", root / "missing")
    ck("failure is one plain line", result.returncode != 0 and len(result.stdout.strip().splitlines()) == 1
       and not result.stderr and "Traceback" not in result.stdout)
    import compose
    with patch.object(compose, "scene_project"), patch.object(cover.rt, "hyperframes_env", return_value={}), \
            patch.object(compose, "hf_render", side_effect=compose.Stop(1, "Layout check stopped.\nMore detail.", "Nothing was rendered.")):
        try:
            cover.render_title(None, "Clear cuts", None, lines=1)
        except cover.Stop as error:
            ck("render stop keeps first compose line", error.detail == "Layout check stopped."
               and str(error) == "The cover title could not render offline; check the editor tools and try again.")
        else:
            ck("render stop keeps first compose line", False)


def case_pick(root, source):
    reel = fixture(root, source)
    doc = prepare(reel)
    rows = doc["candidates"]
    video = Path(doc["video"])
    size, fps, duration, count = cover.video_info(video)
    anchors, segments = cover.load_anchors(reel)
    pool = cover.pool_frames(count, fps, anchors)
    pictures = cover.decode_frames(video, pool, size, duration)
    scored = cover.score_pool(pictures, size, anchors, segments)
    expected = cover.recommended_frame(scored, fps)
    ck("recommended opening first", 0 < len(rows) <= 6 and rows[0]["recommended"]
       and rows[0]["frame"] == expected and sum(r["recommended"] for r in rows) == 1)
    ck("candidate heads inside frame", all(r["head_box"] is not None
       and cover.inside(r["head_box"]) for r in rows))
    ck("remaining frames spread by a second", all(abs(a["frame"] - b["frame"]) / fps >= 1
       for i, a in enumerate(rows) for b in rows[i + 1:]))
    for row in rows:
        with cover.Image.open(reel / f'cover/cand-{row["frame"]}.jpg') as image:
            ck(f'frame {row["frame"]} full cover size', image.size == (1080, 1920))
    # Six eligible, separated frames: the planted blurred candidate must survive
    # the top-five selection, so this asserts rank rather than merely exclusion.
    from PIL import ImageFilter
    sharp = cover.np.random.default_rng(6).integers(0, 256, (size[1], size[0], 3), dtype="uint8")
    blurred = cover.Image.fromarray(sharp).filter(ImageFilter.GaussianBlur(12)).tobytes()
    step = math.ceil(fps)
    samples = {i * step: (blurred if i == 5 else sharp.tobytes()) for i in range(6)}
    scores = cover.score_pool(samples, size, [], [])
    selected = cover.choose_candidates(scores, fps)
    ck("planted blurred candidate ranks last", len(selected) == 6 and selected[-1]["frame"] == 5 * step
       and selected[-1]["score"] < selected[-2]["score"])
    # Exercise the same public candidates decoder with a planted blur as well.
    decode = cover.face.frames
    def planted(video, frames, requested_size, duration):
        return samples if requested_size == size else decode(video, frames, requested_size, duration)
    with patch.object(cover, "pool_frames", return_value=list(samples)), patch.object(cover.face, "frames", side_effect=planted):
        cover.candidates(reel, video)
    ck("candidate JSON retains blurred rank", cover.read(reel / "cover/candidates.json")["candidates"][-1]["frame"] == 5 * step)


def case_title_geometry(root, source):
    for head, above in (([0, .252, 1, .814], True), ([.1, .08, .9, .7], False)):
        protected = (head[0], head[1], head[2], head[1] + .75 * (head[3] - head[1]))
        for lines in (1, 2):
            box = cover.title_placement(head, lines)["box"]
            ck("title clears top 75% of head", not cover.overlaps(box, protected), box)
            ck("title above head first" if above else "tight crop title below face",
               box[3] * cover.H + cover.GAP <= head[1] * cover.H if above else
               box[1] * cover.H >= protected[3] * cover.H + cover.GAP, box)
    head = [0, .08, 1, .85]
    placement = cover.title_placement(head, 2)
    ck("tight crop uses smaller title without overlap", placement["size"] == "smaller"
       and not cover.overlaps(placement["box"], (0, .08, 1, .6575)))
    try:
        cover.title_placement([0, .2, 1, 1], 2)
    except cover.Stop as error:
        ck("no room refuses plainly", str(error) == cover.TITLE_REFUSAL)
    else:
        ck("no room refuses plainly", False)


def case_title(root, source):
    ck("scene font wraps one line", cover.title_lines("MMMMMMMM") == 1)
    ck("scene font wraps two lines", cover.title_lines("MMMMMMMM MMMMMMMM") == 2)
    ck("three-line title measured", cover.title_lines("MMMMMMMM MMMMMMMM MMMMMMMM") == 3)
    spec = cover.read(P / "scenes/cover-title/scene.json")
    ck("scene and validator share title cap", spec["slots"]["title"]["maxChars"] == cover.TITLE_MAX_CHARS)
    ck("wide title fits smaller size", cover.title_lines("W" * cover.TITLE_MAX_CHARS, "smaller") <= 2)
    try:
        cover.validate_title("W" * (cover.TITLE_MAX_CHARS + 1), "W" * (cover.TITLE_MAX_CHARS + 1))
    except cover.Stop as error:
        ck("title character cap enforced", str(error) == cover.TITLE_LIMIT)
    else:
        ck("title character cap enforced", False)
    reel = fixture(root, source)
    doc = prepare(reel)
    source_text = cover.source_words(reel)
    title = " ".join(source_text.split()[:3])
    row = doc["candidates"][0]
    placement = cover.title_placement(row["head_box"], title=title)
    ck("fixture uses normal title size", placement["size"] == "normal")
    band_bottom = math.ceil(cover.head_band(row["head_box"])[3] * 1920)
    ck("fixture title above head when it fits, otherwise below face",
       placement["box"][3] * cover.H + cover.GAP <= row["head_box"][1] * cover.H
       or round(placement["box"][1] * 1920) == band_bottom + cover.GAP,
       (placement["box"], band_bottom))
    pick = {"frame": row["frame"], "title": title, "embed_first_frame": False}
    cover.save(reel / "cover-picker-selection.json", pick)
    result = command(SCRIPT, "apply", "--reel-dir", reel)
    ck("said words accepted", result.returncode == 0, result.stdout + result.stderr)
    ck("face title needs no fallback note", cover.NO_FACE_NOTE not in result.stdout)
    if result.returncode:
        return
    box = placement["box"]
    ck("fixture title clears face with gap", box[3] * cover.H + cover.GAP <= row["head_box"][1] * cover.H
       or box[1] * cover.H >= math.ceil(cover.head_band(row["head_box"])[3] * cover.H) + cover.GAP)
    ck("title clears face", row["head_box"] is None or not cover.overlaps(box, cover.head_band(row["head_box"])))
    for name, top, bottom in (("eyes", .25, .5), ("mouth", .5, .75)):
        head = row["head_box"]
        feature = (head[0], head[1] + top * (head[3] - head[1]), head[2], head[1] + bottom * (head[3] - head[1]))
        ck("title clears protected " + name, not cover.overlaps(box, feature))
    with cover.Image.open(reel / "cover.jpg") as image:
        ck("finished cover size", image.size == (1080, 1920))
    output = cover.read(reel / "cover.json")
    ck("cover manifest four keys", set(output) == {"frame", "score", "title", "embed_first_frame"}
       and output == dict(pick, score=row["score"]))
    anchors_path = reel / "work/anchors.json"
    original_anchors = anchors_path.read_bytes()
    segments = cover.read(reel / "work/cuts.json")["segments"]
    selected_segment = next(i for i, segment in enumerate(segments)
                            if segment["out_in_f"] <= row["frame"] < segment["out_out_f"])
    try:
        for missing in ("anchors", "segment samples"):
            if missing == "anchors":
                anchors_path.unlink()
            else:
                anchors = json.loads(original_anchors)
                for group in anchors["segments"]:
                    if group["seg"] == selected_segment:
                        group["samples"] = []
                cover.save(anchors_path, anchors)
            (reel / "cover.json").unlink()
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed), patch.object(cover, "save", wraps=cover.save) as writes:
                cover.apply(reel)
            fills = [call.args[1] for call in writes.call_args_list if Path(call.args[0]).name == "fill.json"]
            ck("no " + missing + " renders title at low scene default", len(fills) == 1 and fills[0]["y"] == 1100)
            ck("no " + missing + " writes approved cover", cover.read(reel / "cover.json") == output
               and (reel / "cover.jpg").is_file())
            ck("no " + missing + " prints one fallback note", printed.getvalue().splitlines().count(cover.NO_FACE_NOTE) == 1)
    finally:
        anchors_path.write_bytes(original_anchors)
    for bad in ("zzunsaidcoverword", "987654321098765"):
        cover.save(reel / "cover-picker-selection.json", dict(pick, title=bad))
        result = command(SCRIPT, "apply", "--reel-dir", reel)
        ck("unsaid title refused: " + bad, result.returncode != 0
           and len(result.stdout.strip().splitlines()) == 1 and not result.stderr)
    cover.save(reel / "cover-picker-selection.json", dict(pick, frame=10**12))
    ck("nonexistent frame refused", command(SCRIPT, "apply", "--reel-dir", reel).returncode != 0)
    ck("failed apply preserves approved cover", cover.read(reel / "cover.json") == output)
    # Keep the real fixture video and plant only the selected frame's head box.
    smaller_head = [0, .08, 1, .85]
    no_room_head = [0, .2, 1, 1]
    anchors_path = reel / "work/anchors.json"
    original_anchors = anchors_path.read_bytes()
    pick["title"] = "MMMMMMMM MMMMMMMM"
    ck("planted title stays two lines at both sizes", all(cover.title_lines(pick["title"], size) == 2 for size in cover.TITLE_SIZES))
    cover.save(reel / "cover-picker-selection.json", pick)
    try:
        for name, head in (("smaller", smaller_head), ("refusal", no_room_head)):
            anchors = json.loads(original_anchors)
            for group in anchors["segments"]:
                for sample in group["samples"]:
                    sample["box"] = head
            cover.save(anchors_path, anchors)
            before = {p: p.read_bytes() for p in (reel / "cover.jpg", reel / "cover.json")}
            with patch.object(cover, "source_words", return_value=pick["title"]), \
                    patch.object(cover, "render_title", wraps=cover.render_title) as render:
                if name == "smaller":
                    cover.apply(reel)
                    ck("planted frame renders one size smaller", render.call_args.args[4] == "smaller")
                else:
                    try:
                        cover.apply(reel)
                    except cover.Stop as error:
                        ck("no-room refusal offers both fixes", str(error) == cover.TITLE_REFUSAL
                           and "Use a shorter title" in str(error) and "pick another cover frame from the picker" in str(error)
                           and len(str(error).splitlines()) == 1)
                    else:
                        ck("no-room refusal offers both fixes", False)
                    ck("refusal never starts render", not render.called)
                    ck("refusal writes nothing", all(p.read_bytes() == content for p, content in before.items())
                       and not (reel / "cover.tmp.jpg").exists())
    finally:
        anchors_path.write_bytes(original_anchors)


def case_scene(root, source):
    preview = P / "scenes/cover-title/preview.png"
    if not preview.is_file():
        result = command(HERE / "scene_render_test.py", "--scene", "cover-title", "--part", "base", "--write-previews")
        ck("real cover-title preview", result.returncode == 0, result.stdout + result.stderr)
    import scene_check
    import scene_fill
    ck("cover-title contract", not scene_check.scene_problems(P / "scenes/cover-title"),
       scene_check.scene_problems(P / "scenes/cover-title"))
    result = command(P / "scripts/scene_check.py", "check")
    ck("all existing scenes still pass", result.returncode == 0, result.stdout + result.stderr)
    ck("cover scene excluded from Beat Map", all(r["category"] != "cover-title" for r in scene_fill.catalog()))


def raw_frame(path, frame, size=(720, 1280)):
    return cover.face.frames(path, [frame], size, 120)[frame].tobytes()


def case_embed(root, source):
    import compose
    import motion_check
    reel = fixture(root, source)
    send = cover.read(reel / compose.SEND)
    send["caption_style"] = {"style": "none"}
    cover.save(reel / compose.SEND, send)
    doc = prepare(reel)
    cover.save(reel / "cover-picker-selection.json", {"frame": doc["candidates"][0]["frame"],
               "title": None, "embed_first_frame": False})
    cover.apply(reel)
    saved = cover.read(reel / "cover.json")
    render_script = P / "skills/reel-canvas-build/scripts/compose.py"
    outputs, pages = {}, {}
    for mode in ("absent", "off", "on"):
        if mode == "absent":
            (reel / "cover.json").unlink(missing_ok=True)
        else:
            cover.save(reel / "cover.json", dict(saved, embed_first_frame=mode == "on"))
        result = command(render_script, "preview", "--reel-dir", reel, "--keep-project")
        ck("compose preview " + mode, result.returncode == 0, result.stdout + result.stderr)
        if result.returncode:
            return
        summary = json.loads(result.stdout.strip().splitlines()[-1])
        output = Path(summary["out"])
        target = root / (mode + ".mp4")
        shutil.copyfile(output if output.is_absolute() else reel / output, target)
        outputs[mode] = target
        # --keep-project's retained project location is printed by compose.
        retained = [line.split("info: render project kept at ", 1)[1] for line in result.stdout.splitlines()
                    if line.startswith("info: render project kept at ")]
        if retained:
            pages[mode] = (Path(retained[-1]) / "index.html").read_bytes()
    ck("off opening hash unchanged", hashlib.sha256(raw_frame(outputs["absent"], 0)).digest()
       == hashlib.sha256(raw_frame(outputs["off"], 0)).digest())
    ck("off HTML byte identical", set(pages) == {"absent", "off", "on"} and pages["absent"] == pages["off"])
    reference = cover.Image.open(reel / "cover.jpg").convert("RGB").resize((720, 1280), cover.Image.Resampling.LANCZOS)
    # Luma PSNR (BT.709 Y): every H.264 frame stores colour at 4:2:0, so an RGB PSNR
    # charges chroma subsampling to the embed; the luma plane is what the embed controls.
    luma = cover.np.array([0.2126, 0.7152, 0.0722])
    a = cover.np.asarray(reference, dtype=float) @ luma

    def y_psnr(mode):
        b = cover.np.frombuffer(raw_frame(outputs[mode], 0), dtype="uint8").reshape(1280, 720, 3).astype(float) @ luma
        mse = float(cover.np.mean((a - b)**2))
        return math.inf if mse == 0 else 10 * math.log10(255**2 / mse)
    psnr, plain = y_psnr("on"), y_psnr("off")
    print(f"info: frame 0 luma PSNR vs cover.jpg: embed on {psnr:.2f} dB, embed off {plain:.2f} dB", flush=True)
    # Bar is 38 dB luma at the 720p preview, not the gap design's 40 (H-G6-2): the preview's H.264
    # 4:2:0 encode costs every frame (measured 39.1-40.2 across resize filters on the fixture).
    # The 10 dB margin over the plain opening proves the cover is what's on screen (measured 15.8);
    # 3 dB would let a half-working embed pass. One 1080p final-tier measure runs in the M8-end sweep.
    ck("embedded first frame luma PSNR >= 38 (720p preview)", psnr >= 38, psnr)
    ck("embed on is closer to the cover than the plain opening (>= 10 dB)", psnr >= plain + 10, (psnr, plain))
    # A changed I-frame may alter later codec rounding; prove the exact clock
    # setting as well as the visible first frame, length and untouched sound.
    hide = (f'tl.set("#cover-first-frame", {{ autoAlpha: 0, immediateRender: false }}, '
            f'{compose.at(1, Fraction(str(doc["fps"])))});')
    ck("cover hidden at frame one", hide in pages.get("on", b"").decode("utf-8"))
    ck("frame count unchanged", len({cover.video_info(p)[3] for p in outputs.values()}) == 1)
    audio = [compose.packet_md5(p, "a:0") for p in outputs.values()]
    ck("audio packet md5 unchanged", all(audio) and len(set(audio)) == 1)
    rows = motion_check.run({"reel_dir": reel, "render": outputs["on"], "fps": doc["fps"], "cuts": None, "beats": None})
    ck("motion proof ran", not any(r["check"] == "motion-unreadable" for r in rows), rows)
    ck("first-frame-plain absent", not any(r["check"] == "first-frame-plain" for r in rows), rows)


def case_hub(root, source):
    import hub_test
    proof = hub_test.Proof(root)
    try:
        reel = proof.videos / "reel-01"
        cover.save(reel / "work/edit_map.cut.json", {"words": [{"word": w} for w in "Clear cuts today".split()]})
        script = proof.plugin / "skills/reel-cover/scripts/cover_pick.py"
        proof.py(script, "candidates", "--reel-dir", reel)
        proof.refresh()
        actions = [{"do": "click", "sel": "#tab-cover-picker"},
                   {"do": "frame", "sel": "#panel iframe", "wait": "#candidates button"}]
        data = proof.browse(actions + [{"do": "eval", "js": "JSON.stringify({first:document.querySelector('#candidates button').textContent,embed:document.querySelector('#embed').checked})"},
            {"do": "click", "sel": "#candidates button"}, {"do": "set", "sel": "#title", "value": "Clear cuts"},
            {"do": "click", "sel": "#send"},
            {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])[0]
        ck("hub recommended first, embed off", data["first"].startswith("Recommended:") and data["embed"] is False)
        selection = cover.read(reel / "cover-picker-selection.json")
        ck("hub Send round trip", selection["title"] == "Clear cuts" and selection["embed_first_frame"] is False)
        # Only apply uses the installed renderer; browser work keeps Proof's home.
        env = cover.rt.python_env(INSTALLED_HOME, base=dict(os.environ, EDITOR_SE_HOME=str(INSTALLED_HOME)))
        python = cover.rt.tool("python", INSTALLED_HOME)
        applied = subprocess.run([python, "-X", "utf8", "-I", str(HEAVY), "--wait", "600", "--min-gb", "3", "--",
                                  python, "-X", "utf8", "-I", "-B", str(script), "apply", "--reel-dir", str(reel)],
                                 env=env, cwd=proof.ws, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=2400)
        if applied.returncode in (75, 76):
            raise hub_test.Blocked("The cover-title render lock is unavailable.")
        ck("hub apply completed", applied.returncode == 0, applied.stdout + applied.stderr)
        ck("hub choice applied", (reel / "cover.jpg").is_file() and cover.read(reel / "cover.json")["title"] == "Clear cuts")
        invalid = proof.browse(actions + [{"do": "set", "sel": "#title", "value": "zzunsaidcoverword"},
            {"do": "eval", "js": "JSON.stringify({disabled:document.querySelector('#send').disabled,error:document.querySelector('#validation').textContent})"}])
        ck("invalid board draft flagged before Send", invalid[0]["disabled"] and "not said" in invalid[0]["error"])
        ck("invalid board draft cannot overwrite Send", cover.read(reel / "cover-picker-selection.json") == selection)
    finally:
        proof.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=(*CASES, "all"), default="all")
    parser.add_argument("--reel-src", type=Path, default=DEFAULT_REEL)
    parser.add_argument("--locked", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    blocked = 0
    for name in CASES if args.case == "all" else (args.case,):
        if name == "hub" and not HEAVY.is_file():
            print("BLOCKED hub: shared heavy lock is missing")
            blocked = 75
            continue
        if name in ("title", "scene", "embed") and not args.locked:
            if not HEAVY.is_file():
                print("BLOCKED " + name + ": shared heavy lock is missing")
                blocked = 75
                continue
            result = command(HEAVY, "--wait", "600", "--min-gb", "3", "--", sys.executable,
                             "-X", "utf8", "-I", Path(__file__), "--case", name,
                             "--reel-src", args.reel_src, "--locked")
            print(result.stdout + result.stderr, end="")
            if result.returncode in (75, 76):
                blocked = result.returncode
            else:
                ck(name + " locked proof", result.returncode == 0)
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="editor-g6-") as folder:
                with isolated_home(packages=name in ("title", "scene", "embed", "hub")):
                    globals()["case_" + name](Path(folder), args.reel_src)
        except Exception as error:
            if type(error).__name__ == "Blocked":
                print("BLOCKED " + name + ": shared browser lock unavailable")
                blocked = 75
            else:
                ck(name, False, str(error))
    print(f"{len(FAILS)} failed" + (f", blocked exit {blocked}" if blocked else ""))
    return 1 if FAILS else blocked


if __name__ == "__main__":
    sys.exit(main())
