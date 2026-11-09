#!/usr/bin/env python3
"""S6b check for reel-canvas-build's cutout.py (RVM first, remove-background fallback, CFR + frame parity).

usage (one heavy job; EDITOR_SE_HOME = a state folder whose venv has torch + torchvision):
  python "C:/Workspaces/Content Studio/output/scripts/heavy_lock.py" --wait 600 -- \
    <state>/venv/Scripts/python.exe -X utf8 -I tests/editor/cutout_test.py
Fixture: the first 3 s of the read-only iPhone clip at 540x960, VFR timestamps kept. Runs cutout.py with the
state's venv python. Prints PASS/FAIL per check; exit 0 = all passed.
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "editor-superengine"
SCRIPT = PLUGIN / "skills" / "reel-canvas-build" / "scripts" / "cutout.py"
SOURCE = Path("C:/Workspaces/Content Studio/input/editor-tests/iPhone.mp4")  # read only
SCRATCH = Path("C:/Work/_scratch/editor-superengine-0.2.0/s6b")
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
sys.path.insert(0, str(SCRIPT.parent))
import runtime  # noqa: E402
import fps  # noqa: E402

fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def cutout(*args, mask=None):
    env = dict(os.environ)
    env.pop("EDITOR_SE_MASK", None)
    if mask:
        env["EDITOR_SE_MASK"] = mask
    t0 = time.perf_counter()
    p = subprocess.Popen([runtime.tool("python"), "-X", "utf8", "-I", str(SCRIPT), *map(str, args)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = p.communicate(timeout=900)
    out, err = out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
    secs = time.perf_counter() - t0
    print(f"  ran cutout.py {' '.join(map(str, args[2:]))} (mask={mask}): exit {p.returncode} in {secs:.1f} s")
    for line in out.splitlines():
        if line.startswith("info:"):
            print("  " + line)
    try:
        summary = json.loads(out.strip().splitlines()[-1])
    except (IndexError, ValueError):
        summary = None
    return p.returncode, out, err, summary


def stream(video):
    r = subprocess.run([runtime.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=codec_name,profile,pix_fmt,width,height,color_space,color_primaries,color_transfer",
                        "-of", "json", str(video)], capture_output=True, text=True, encoding="utf-8",
                       env=runtime.python_env(), timeout=60)
    return (json.loads(r.stdout or "{}").get("streams") or [{}])[0]


def alpha_counts(video, frame):
    raw = subprocess.run([runtime.tool("ffmpeg"), "-v", "error", "-i", str(video), "-vf",
                          f"select=eq(n\\,{frame}),alphaextract", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt",
                          "gray", "-"], capture_output=True, env=runtime.python_env(), timeout=120).stdout
    return len(raw), sum(b > 200 for b in raw), sum(b < 50 for b in raw)


def listing(d):
    return sorted(str(p.relative_to(d)) for p in d.rglob("*")) if d.is_dir() else None


def prores_4444_alpha(s):
    # ffmpeg 8.1.2's ProRes decoder reports every 4444 file as yuva444p12le, including the yuva444p10le that
    # cutout.py encodes, so ffprobe can't tell 10 from 12 bits; either is ProRes 4444 with an alpha plane.
    return (s.get("codec_name"), s.get("profile")) == ("prores", "4444") and \
        s.get("pix_fmt") in ("yuva444p10le", "yuva444p12le")


def main():
    state = runtime.state_dir()
    print(f"state folder: {state}")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    td = Path(tempfile.mkdtemp(prefix="cutout-test-", dir=SCRATCH))
    user_hub = Path(os.environ.get("USERPROFILE") or Path.home()) / ".cache" / "torch" / "hub"
    hub_before = listing(user_hub)
    try:
        fx = td / "fixture.mp4"
        subprocess.run([runtime.tool("ffmpeg"), "-v", "error", "-y", "-t", "3", "-i", str(SOURCE), "-map", "0:v:0",
                        "-an", "-vf", "scale=540:960", "-fps_mode", "passthrough", "-c:v", "libx264", "-preset",
                        "fast", "-crf", "16", "-pix_fmt", "yuv420p", str(fx)], check=True, env=runtime.python_env(),
                       timeout=120)
        fx_rate, fx_frames = fps.probe_fps(fx), fps.frame_count(fx)
        print(f"  fixture: {fx_frames} frames, avg rate {fx_rate}")
        if not fps.is_vfr(fx):
            ck("fixture isn't VFR", False, "the fixture has constant frame timing")
            return 1

        # 1. auto with torch present -> RVM, CFR first, everything checked on the output
        out1 = td / "r1" / "work" / "matte" / "cutout.mov"
        rc, out, err, j = cutout(fx, out1, "--engine", "auto")
        ck("1 auto runs (exit 0, JSON last)", rc == 0 and j is not None, (out + err)[-600:])
        j = j or {}
        ck("1 engine rvm", j.get("engine") == "rvm", j)
        ck("1 cfr_converted", j.get("cfr_converted") is True, j)
        sf, cf = j.get("src_frames"), j.get("frames")
        ck("1 CFR vs source within max(2, 1 %)", isinstance(sf, int) and isinstance(cf, int) and
           abs(cf - sf) <= max(2, sf / 100), (sf, cf))
        s = stream(out1)
        ck("1 ProRes 4444 with alpha", prores_4444_alpha(s), s)
        ck("1 540x960", (s.get("width"), s.get("height")) == (540, 960), s)
        try:
            same_rate = Fraction(fps.probe_fps(out1)) == Fraction(fx_rate)
        except fps.FpsError as e:
            same_rate = e
        ck("1 fps == the fixture's avg rate", same_rate is True, same_rate)
        ck("1 BT.709 tags", (s.get("color_space"), s.get("color_primaries"), s.get("color_transfer")) ==
           ("bt709", "bt709", "bt709"), s)
        n1 = fps.frame_count(out1) if out1.is_file() else None
        ck("1 output frames == the CFR count", n1 == cf, (n1, cf))
        size, hi, lo = alpha_counts(out1, (n1 or 2) // 2)
        ck("1 subject present (alpha > 200 and < 50 both seen)", size == 540 * 960 and hi > 0 and lo > 0,
           (size, hi, lo))
        hub = state / "torch-hub" / "hub"
        ck("1 pinned hub code under the state folder",
           any("53d74c6826735f01f4406b5ca9075eee27bec094" in p.name for p in hub.iterdir()) if hub.is_dir() else False,
           listing(hub))
        ck("1 weights under the state folder", (hub / "checkpoints" / "rvm_resnet50.pth").is_file())
        ck("1 nothing new in ~/.cache/torch/hub", listing(user_hub) == hub_before, (hub_before, listing(user_hub)))
        tmp1 = out1.parent.parent / "render-tmp"
        ck("1 default --tmp left nothing", not tmp1.exists() or not any(tmp1.iterdir()), listing(tmp1))

        # 2. torch masked -> remove-background; an explicit --tmp keeps what was already in it
        out2, tmp2 = td / "r2" / "cutout.mov", td / "r2-tmp"
        tmp2.mkdir()
        (tmp2 / "keep.txt").write_text("not cutout's", encoding="utf-8")
        rc, out, err, j = cutout(fx, out2, "--engine", "auto", "--tmp", tmp2, mask="torch")
        ck("2 masked auto runs (exit 0)", rc == 0 and j is not None, (out + err)[-600:])
        j = j or {}
        ck("2 engine remove-background", j.get("engine") == "remove-background", j)
        ck("2 ProRes 4444 with alpha", prores_4444_alpha(stream(out2)), stream(out2))
        n2 = fps.frame_count(out2) if out2.is_file() else None
        ck("2 frame parity exact", n2 is not None and n2 == j.get("frames") and
           abs(n2 - fx_frames) <= max(2, fx_frames / 100), (n2, j.get("frames"), fx_frames))
        try:
            same_rate = Fraction(fps.probe_fps(out2)) == Fraction(fx_rate)
        except fps.FpsError as e:
            same_rate = e
        ck("2 fps == the fixture's avg rate", same_rate is True, same_rate)
        ck("2 --tmp holds only what was there", listing(tmp2) == ["keep.txt"], listing(tmp2))

        # 3. --engine rvm without torch -> plain error, no output
        out3 = td / "r3" / "cutout.mov"
        rc, out, err, _ = cutout(fx, out3, "--engine", "rvm", mask="torch")
        ck("3 rvm without torch: exit 1, plain message, no traceback, no file",
           rc == 1 and "torch" in out and "Traceback" not in out + err and not out3.exists(), (rc, out, err[-400:]))

        # 4. check_parity, imported by path
        spec = importlib.util.spec_from_file_location("editor_cutout", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.check_parity(86, 86)
        try:
            mod.check_parity(86, 87)
            raised = False
        except mod.CutoutError:
            raised = True
        ck("4 check_parity: equal passes, off by one raises", raised)
        r = subprocess.run([runtime.tool("python"), "-X", "utf8", "-I", str(SCRIPT), "--selftest"],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        ck("4 cutout.py --selftest", r.returncode == 0 and r.stdout.strip() == "selftest ok", r.stdout + r.stderr)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print(f"{'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
