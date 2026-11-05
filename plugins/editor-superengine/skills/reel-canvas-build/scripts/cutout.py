"""Cut the speaker out of a clip: a ProRes 4444 .mov with straight alpha, frame for frame with the clip.

  <editor python> -X utf8 -I cutout.py <src.mp4> <out.mov> [--engine auto|rvm|remove-background] [--tmp DIR]
  <editor python> -X utf8 -I cutout.py --selftest

auto = RVM (RobustVideoMatting resnet50 on torch + torchvision) when this Python can import both, otherwise
HyperFrames' remove-background (the backup method). A VFR clip is first converted to CFR at its average rate
(HF-3) into --tmp (default <out>/../../render-tmp, i.e. work/render-tmp/); everything written there is deleted
when the run ends, and the folder too when it is then empty. The output always has exactly as many frames as
the clip it was matted from, or it is deleted. Last stdout line: one JSON summary.

Port notes: rewritten from our own earlier templates/matte/rvm_cutout.py (Shortform SE). Changed: size and fps
come from the clip (no 2160x3840@30 constants); the editor's own ffmpeg and env; the CFR step and both
frame-parity checks; the remove-background fallback; the hub code pinned to a commit and the weights fetched
and sha256-checked by this script; TORCH_HOME under the editor's state folder; BT.709 tags with a BT.709
conversion matrix (the old smpte170m tag is gone); RGB is the source picture inside the subject (RVM's fgr only
in the edge band, 0 outside), so the cutout stands on its own. The --probe head A/B sheets are dropped.
Kept: resnet50, downsample to 512 px on the short side, recurrent state carried frame to frame, edge band
0.02 < alpha < 0.98, no levels on the matte.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime  # noqa: E402
import fps  # noqa: E402

HUB_REPO = "PeterL1n/RobustVideoMatting:53d74c6826735f01f4406b5ca9075eee27bec094"  # master head 2023-03-13
WEIGHTS_URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_resnet50.pth"
WEIGHTS_SHA256 = "c191a807251164c073dce5fa408e7a816070d539b882b2a3150330a9fec112ce"  # measured 11.04.26
EDGE_LO, EDGE_HI = 0.02, 0.98
TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
# BT.709 conversion matrix + frame tags (ffmpeg 8 takes primaries/transfer from the frames, not only from TAGS)
BT709_VF = "scale=out_color_matrix=bt709:out_range=tv,setparams=color_primaries=bt709:color_trc=bt709"
PRORES = ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", *TAGS]


class CutoutError(Exception):
    """A plain-English reason the cutout stopped."""


def default_tmp(out):
    """--tmp default: <out>/../../render-tmp (out = work/matte/cutout.mov -> work/render-tmp)."""
    return Path(os.path.abspath(out)).parent.parent / "render-tmp"


def cfr_close_enough(src_frames, cfr_frames):
    """H-S6b-4: the CFR copy may differ from the VFR clip by max(2 frames, 1 %)."""
    return abs(cfr_frames - src_frames) <= max(2, src_frames / 100)


def check_parity(src_frames, out_frames):
    """H-S6b-4: the cutout has exactly the frames of the clip it was matted from."""
    if out_frames != src_frames:
        raise CutoutError(f"the cutout has {out_frames} frames but the clip it was made from has {src_frames}, "
                          f"so it would drift out of sync; it was deleted")


def ffmpeg(args, what, log):
    with open(log, "w", encoding="utf-8") as err:
        rc = subprocess.run([runtime.tool("ffmpeg"), "-v", "error", "-y", *args], stderr=err,
                            env=runtime.python_env()).returncode
    if rc:
        raise CutoutError(f"ffmpeg couldn't {what}: {last_line(log)}")


def last_line(log):
    try:
        lines = Path(log).read_text(encoding="utf-8", errors="replace").strip().splitlines()
    except OSError:
        lines = []
    return lines[-1][:300] if lines else "no details"


def frame_size(video):
    """(width, height) of the decoded picture (a 90/270 rotation tag swaps them; ffmpeg auto-rotates)."""
    s = fps._stream(video, None, ["-show_entries", "stream=width,height:stream_side_data=rotation"], "picture size")
    try:
        w, h = int(s["width"]), int(s["height"])
    except (KeyError, TypeError, ValueError):
        raise CutoutError(f"couldn't read the picture size of {Path(video).name}") from None
    rot = next((d.get("rotation") for d in s.get("side_data_list") or [] if "rotation" in d), 0)
    return (h, w) if abs(int(rot or 0)) % 180 == 90 else (w, h)


def to_cfr(src, rate, dst, log):
    ffmpeg(["-i", str(src), "-map", "0:v:0", "-an", "-sn", "-dn", "-vf", f"fps={rate},{BT709_VF}", "-fps_mode", "cfr",
            "-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv420p", *TAGS, str(dst)],
           "convert the clip to a constant frame rate", log)


def torch_ready():
    if runtime.masked("torch"):  # test-only mask (runtime.py docstring)
        return False
    try:
        import torch, torchvision  # noqa: F401
        return True
    except Exception:  # ImportError, or a DLL that won't load
        return False


def fetch_weights(path):
    """rvm_resnet50.pth into torch.hub's checkpoints folder, sha256-checked (torch.hub then skips its download)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        part = path.with_name(path.name + ".part")
        try:
            with urllib.request.urlopen(WEIGHTS_URL, timeout=60) as r, open(part, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
        except OSError as e:
            part.unlink(missing_ok=True)
            raise CutoutError(f"couldn't download the RVM model ({e}); check the internet connection and run it again") from None
        os.replace(part, path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    if h.hexdigest() != WEIGHTS_SHA256:
        path.unlink(missing_ok=True)
        raise CutoutError("the downloaded RVM model doesn't match its checksum, so it was deleted; run it again "
                          "(it downloads afresh), and if this repeats, send the setup report")


def load_rvm():
    """(model, device): the pinned hub code with the checked weights, under TORCH_HOME."""
    hub = Path(os.environ["TORCH_HOME"]) / "hub"
    fetch_weights(hub / "checkpoints" / "rvm_resnet50.pth")
    import torch
    torch.hub.set_dir(str(hub))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = torch.hub.load(HUB_REPO, "resnet50", pretrained=True, trust_repo=True, skip_validation=True)
    return model.to(dev).eval(), dev


def rvm(model, dev, src, out, size, rate, tmp):
    """Mattes src frame by frame into out (a decode that stops early is caught by check_parity)."""
    import numpy as np
    import torch
    w, h = size
    ds, n_bytes = 512 / min(w, h), w * h * 3
    env = runtime.python_env()
    dlog, elog = open(tmp / "decode.log", "w", encoding="utf-8"), open(tmp / "encode.log", "w", encoding="utf-8")
    dec = subprocess.Popen([runtime.tool("ffmpeg"), "-v", "error", "-i", str(src), "-map", "0:v:0", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=dlog, env=env)
    enc = subprocess.Popen([runtime.tool("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                            "-s", f"{w}x{h}", "-r", rate, "-i", "-",
                            "-vf", BT709_VF, *PRORES, str(out)],
                           stdin=subprocess.PIPE, stderr=elog, env=env)
    rec = [None] * 4
    try:
        with torch.no_grad():
            while True:
                buf = dec.stdout.read(n_bytes)
                if len(buf) < n_bytes:
                    break
                pic = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
                x = torch.from_numpy(pic.copy()).to(dev).permute(2, 0, 1).float().div(255)[None]
                fgr, pha, *rec = model(x, *rec, downsample_ratio=ds)
                a = pha[0, 0].clamp(0, 1).cpu().numpy()
                rgb = np.zeros((h, w, 3), np.uint8)
                inside, band = a >= EDGE_HI, (a > EDGE_LO) & (a < EDGE_HI)
                rgb[inside] = pic[inside]
                rgb[band] = (fgr[0].permute(1, 2, 0).clamp(0, 1).cpu().numpy()[band] * 255).round().astype(np.uint8)
                enc.stdin.write(np.dstack([rgb, (a * 255).round().astype(np.uint8)]).tobytes())
    except BrokenPipeError:
        pass  # the encoder stopped; its log says why (below)
    finally:
        dec.kill()
        dec.wait()
        try:
            enc.stdin.close()
        except OSError:
            pass
        rc = enc.wait()
        dlog.close()
        elog.close()
    if rc:
        raise CutoutError(f"ffmpeg couldn't write the cutout: {last_line(tmp / 'encode.log')}")


def remove_background(src, out, rate, tmp):
    """HyperFrames' ProRes 4444 .mov, then re-timed to the clip's exact rate (0.8.184 writes it rounded to
    2 decimals, e.g. 2843/100 for 3440/121) by a stream copy: no re-encode."""
    log, raw = tmp / "remove-background.log", tmp / "remove-background.mov"
    with open(log, "w", encoding="utf-8") as err:
        rc = subprocess.run(runtime.hyperframes_cmd("remove-background", str(src), "-o", str(raw)), cwd=tmp,
                            stdout=err, stderr=subprocess.STDOUT, env=runtime.hyperframes_env()).returncode
    if rc:
        raise CutoutError(f"the backup cutout (remove-background) failed: {last_line(log)}")
    ffmpeg(["-r", rate, "-i", str(raw), "-map", "0:v:0", "-c", "copy", str(out)], "re-time the backup cutout",
           tmp / "retime.log")
    return "auto"


def cutout(src, out, engine, tmp_root):
    src, out = Path(src), Path(out)
    if not src.is_file():
        raise CutoutError(f"{src} doesn't exist")
    if out.suffix.lower() != ".mov":
        raise CutoutError(f"the cutout must be a .mov file (ProRes 4444 with alpha), not {out.name}")
    has_torch = torch_ready()
    if engine == "rvm" and not has_torch:
        raise CutoutError("the RVM cutout needs torch and torchvision in the editor's Python, and they aren't "
                          "there; Claude re-runs the editor setup, or use --engine auto for the backup method")
    engine = ("rvm" if has_torch else "remove-background") if engine == "auto" else engine
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="cutout-", dir=tmp_root))
    try:
        rate = fps.probe_fps(src)
        src_frames = fps.frame_count(src)
        matted, cfr = src, fps.is_vfr(src)
        if cfr:
            matted = tmp / "cfr.mp4"
            to_cfr(src, rate, matted, tmp / "cfr.log")
            got = fps.frame_count(matted)
            if not cfr_close_enough(src_frames, got):
                raise CutoutError(f"the constant-frame-rate copy has {got} frames but the clip has {src_frames} "
                                  f"(more than 2 frames or 1 % apart), so the cutout would drift; nothing was made")
        n = fps.frame_count(matted)
        model, dev = load_rvm() if engine == "rvm" else (None, None)
        wall, cpu = time.perf_counter(), time.process_time()  # the matting itself (no download, no model load)
        try:
            if engine == "rvm":
                rvm(model, dev, matted, out, frame_size(matted), rate, tmp)
            else:
                dev = remove_background(matted, out, rate, tmp)
            secs, cpu = time.perf_counter() - wall, time.process_time() - cpu
            check_parity(n, fps.frame_count(out))
        except BaseException:
            out.unlink(missing_ok=True)
            raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            tmp_root.rmdir()  # only when nothing else is left in it
        except OSError:
            pass
    cpu_note = f", CPU process time {cpu:.1f} s" if engine == "rvm" else ""
    print(f"info: {engine} on {dev}: {n} frames in {secs:.1f} s ({n / secs if secs else 0:.2f} fps){cpu_note}")
    return {"engine": engine, "device": dev, "src_frames": src_frames, "frames": n, "cfr_converted": cfr,
            "seconds": round(secs, 2), "out": str(out)}


def selftest():
    fails = []
    check_parity(120, 120)
    for a, b in ((120, 121), (121, 120), (0, 1)):
        try:
            check_parity(a, b)
            fails.append(f"check_parity({a}, {b}) did not raise")
        except CutoutError:
            pass
    for src, cfr, want in ((89, 91, True), (89, 92, False), (1000, 1010, True), (1000, 1011, False), (5, 3, True)):
        if cfr_close_enough(src, cfr) != want:
            fails.append(f"cfr_close_enough({src}, {cfr}) != {want}")
    out = Path("videos") / "r1" / "work" / "matte" / "cutout.mov"
    if default_tmp(out) != Path(os.path.abspath("videos/r1/work/render-tmp")):
        fails.append(f"default_tmp({out}) = {default_tmp(out)}")
    if fails:
        for f in fails:
            print(f"selftest FAILED: {f}")
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    os.environ["TORCH_HOME"] = str(runtime.state_dir() / "torch-hub")  # before torch is imported; never ~/.cache
    ap = argparse.ArgumentParser(description="Cut the speaker out of a clip (ProRes 4444 with alpha).")
    ap.add_argument("src", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--engine", choices=("auto", "rvm", "remove-background"), default="auto")
    ap.add_argument("--tmp", help="scratch folder (default <out>/../../render-tmp); cleaned up afterwards")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks (no torch, no ffmpeg) and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.src and a.out):
        ap.print_help()
        return 2
    try:
        summary = cutout(a.src, a.out, a.engine, Path(a.tmp) if a.tmp else default_tmp(a.out))
    except (CutoutError, fps.FpsError, KeyError) as e:
        print(f"cutout failed: {str(e).strip(chr(39))}")
        return 1
    except Exception as e:  # torch / hub / OS trouble: one plain line, no traceback
        print(f"cutout failed: {type(e).__name__}: {e}")
        return 1
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
