"""GPU variant (0.2.4): when the computer has an NVIDIA card the editor uses it; every other computer keeps the CPU path.

Three parts, each with its own fallback, all decided on the machine (state.json "gpu"), never per workspace:
  torch  install.py swaps the lock's CPU torch + torchvision for the CUDA wheels pinned in pins.json `torch_cuda`
         (Windows + NVIDIA, driver >= 580, Turing or newer, >= 6 GB free). Proven with a real CUDA op; any failure puts
         the lock's CPU wheels back and the setup carries on. cutout.py already picks cuda when torch sees it.
  nvenc  h264() gives h264_nvenc instead of libx264 for the editor's own encodes, once state.json says NVENC passed at
         setup AND a one-frame probe with the exact same settings passes in this process. Else libx264, byte-for-byte
         the arguments the script used before. Quality is mapped from measured parity (see cq_for).
  pref   Windows' per-app graphics setting for the render browser: HKCU UserGpuPreferences, value = the full path of
         chrome-headless-shell.exe, data GpuPreference=2; (high performance). A value the user set is never changed.
         HyperFrames renders in its `auto` browser-GPU mode, which uses Windows' choice of adapter.

Off switch: check_deps.py --gpu off (install.py --gpu off) records wanted=off, puts the CPU wheels back, removes the
registry value it set, and turns NVENC off. --gpu on turns all three back on. Undo notes: editor-doctor
references/doctor-details.md "GPU variant".

  python gpu.py --selftest      # offline checks of the decision and the encoder arguments
"""
import functools, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime as rt  # noqa: E402

PREF_KEY = r"Software\Microsoft\DirectX\UserGpuPreferences"
PREF_HIGH = "GpuPreference=2;"

# Measured 11.23.26 on an RTX 4060 Laptop (8 s of a real 1080x1920 take vs a lossless reference): every CQ below
# matches or beats the libx264 CRF it replaces on both SSIM and PSNR. CRF 14 slow .99324/49.66 dB -> CQ 18
# .99344/49.83; CRF 8 fast .99654/53.03 -> CQ 10 .99689/53.58; CRF 16 fast .99179/48.56 -> CQ 20 .99234/48.95;
# CRF 20 veryfast .98723/45.90 -> CQ 24 (CQ 23 .99041). -maxrate/-qmin lift NVENC's default cap (it stalls near CQ 18
# without them); -no-scenecut keeps the fixed GOP the scrub copies rely on (libx264's -sc_threshold 0).
NVENC = ["-preset", "p7", "-tune", "hq", "-rc", "vbr", "-b:v", "0", "-maxrate:v", "400M", "-bufsize:v", "800M",
         "-qmin", "0", "-spatial-aq", "1", "-temporal-aq", "1", "-bf", "3", "-b_ref_mode", "middle",
         "-rc-lookahead", "32", "-no-scenecut", "1", "-profile:v", "high"]


def cq_for(crf):
    """The NVENC CQ that matches or beats libx264 at this CRF (measured, see NVENC)."""
    return int(crf) + (2 if int(crf) <= 10 else 4)


def smi_facts():
    """(driver major, compute capability) of the best NVIDIA card nvidia-smi lists; None for what it can't say."""
    exe = rt.nvidia_smi()
    if not exe:
        return None, None
    try:
        r = subprocess.run([exe, "--query-gpu=driver_version,compute_cap", "--format=csv,noheader"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=20, env=dict(os.environ))
    except (OSError, subprocess.SubprocessError):
        return None, None
    return parse_smi(r.stdout if r.returncode == 0 else "")


def parse_smi(text):
    drivers, caps = [], []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        m = re.match(r"(\d+)\.", parts[0]) if parts else None
        if m:
            drivers.append(int(m.group(1)))
        if len(parts) > 1 and re.fullmatch(r"\d+\.\d+", parts[1]):
            caps.append(float(parts[1]))
    return (max(drivers) if drivers else None), (max(caps) if caps else None)


def torch_plan(key, gpu, driver, compute, free_gb, wanted, pin):
    """(use CUDA torch?, plain reason). Pure: the one place this is decided (selftest covers every branch).
    key: rt.platform_key(); gpu: rt.gpu_read()[0]; driver/compute: smi_facts(); pin: pins.json torch_cuda."""
    if wanted == "off":
        return False, "the graphics card speed-up is turned off"
    if key != "win-x64" or key not in pin:
        return False, "the graphics card speed-up is for Windows computers with an NVIDIA card"
    if gpu != "yes":
        return False, ("no NVIDIA graphics card was found" if gpu in ("no", "no-smi")
                       else "the NVIDIA graphics card check didn't answer, so the CPU version stays for now")
    if driver is None or driver < pin["min_driver"]:
        return False, (f"the NVIDIA driver ({driver or 'unknown'}) is older than {pin['min_driver']}; "
                       "updating the NVIDIA driver turns the speed-up on")
    if compute is not None and compute < pin["min_compute"]:
        return False, "this NVIDIA card is older than the CUDA build supports (it needs a GeForce 16/20 series or newer)"
    if free_gb < pin["min_free_gb"]:
        return False, f"only {free_gb:.0f} GB is free on the disk; the speed-up needs about {pin['min_free_gb']} GB"
    return True, "NVIDIA graphics card"


def nvenc_cmd(ffmpeg):
    """The one-frame probe: the exact NVENC settings h264() uses, on a tiny black frame, into nothing."""
    return [ffmpeg, "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:r=30:d=0.1",
            "-frames:v", "1", "-c:v", "h264_nvenc", *NVENC, "-cq", "20", "-pix_fmt", "yuv420p", "-f", "null", "-"]


def nvenc_probe(ffmpeg):
    try:
        return subprocess.run(nvenc_cmd(ffmpeg), capture_output=True, timeout=60, env=dict(os.environ)).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@functools.lru_cache(maxsize=None)
def nvenc_ready(state=None):
    """True when setup recorded NVENC as on for this machine and the probe passes now (once per process)."""
    if rt.masked("gpu"):
        return False
    try:
        if rt.load_state(state).get("gpu", {}).get("nvenc") is not True:
            return False
        return nvenc_probe(rt.tool("ffmpeg", state))
    except (KeyError, OSError, ValueError):
        return False


def h264(crf, preset, state=None):
    """Video-encoder arguments for one H.264 encode: NVENC when ready, else libx264 with this CRF and preset."""
    if nvenc_ready(state):
        return ["-c:v", "h264_nvenc", *NVENC, "-cq", str(cq_for(crf))]
    return ["-c:v", "libx264", "-crf", str(crf), "-preset", preset]


# ---- Windows per-app graphics preference (HKCU only) -------------------------------------------------------------
def pref_set(exe):
    """Sets high performance for exe. "set" (written now), "same" (already ours), "kept" (the user chose another)."""
    import winreg
    exe = os.path.normpath(os.path.abspath(exe))
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, PREF_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
        try:
            cur = winreg.QueryValueEx(k, exe)[0]
        except FileNotFoundError:
            cur = None
        if cur == PREF_HIGH:
            return "same"
        if cur is not None:
            return "kept"
        winreg.SetValueEx(k, exe, 0, winreg.REG_SZ, PREF_HIGH)
        return "set"


def pref_clear(exe):
    """Removes the value for exe only when it still holds exactly what pref_set wrote. True when removed."""
    import winreg
    exe = os.path.normpath(os.path.abspath(exe))
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PREF_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
            if winreg.QueryValueEx(k, exe)[0] != PREF_HIGH:
                return False
            winreg.DeleteValue(k, exe)
            return True
    except OSError:
        return False


def status(state):
    """(level, plain detail) for the doctor's `gpu` line, from state.json "gpu" (None when there's nothing to say)."""
    g = state.get("gpu") or {}
    if not g:
        return None
    if g.get("wanted") == "off":
        return "ok", "the graphics card speed-up is turned off (everything runs on the processor)"
    parts = []
    if g.get("torch") == "cuda":
        parts.append("cutouts")
    if g.get("nvenc"):
        parts.append("video encodes")
    if g.get("pref") in ("set", "same"):
        parts.append("motion renders")
    if parts:
        return "ok", f"the NVIDIA graphics card speeds up {', '.join(parts[:-1]) + ' and ' + parts[-1] if len(parts) > 1 else parts[0]}"
    return "ok", f"everything runs on the processor ({g.get('torch_reason') or 'no NVIDIA graphics card'})"


def selftest():
    pin = {"min_driver": 580, "min_compute": 7.5, "min_free_gb": 6, "win-x64": {}}
    ok = lambda *a: torch_plan(*a)[0]  # noqa: E731
    assert ok("win-x64", "yes", 616, 8.9, 70, "auto", pin)
    assert ok("win-x64", "yes", 580, 7.5, 6, "auto", pin)               # exactly at every line
    assert ok("win-x64", "yes", 616, None, 70, "auto", pin)             # old nvidia-smi without compute_cap: the CUDA op decides
    assert not ok("win-x64", "yes", 616, 8.9, 70, "off", pin)
    assert not ok("mac-arm64", "no-smi", None, None, 70, "auto", pin)
    assert not ok("win-x64", "no-smi", None, None, 70, "auto", pin)
    assert not ok("win-x64", "no", None, None, 70, "auto", pin)
    assert "didn't answer" in torch_plan("win-x64", "failed", None, None, 70, "auto", pin)[1]
    assert not ok("win-x64", "yes", 579, 8.9, 70, "auto", pin) and "driver" in torch_plan("win-x64", "yes", 579, 8.9, 70, "auto", pin)[1]
    assert not ok("win-x64", "yes", None, 8.9, 70, "auto", pin)
    assert not ok("win-x64", "yes", 616, 6.1, 70, "auto", pin)          # Pascal: CUDA 13 dropped it
    assert not ok("win-x64", "yes", 616, 8.9, 5.9, "auto", pin)
    assert not ok("win-x64", "yes", 616, 8.9, 70, "auto", {k: v for k, v in pin.items() if k != "win-x64"})
    assert parse_smi("616.56, 8.9\n") == (616, 8.9)
    assert parse_smi("552.22, 6.1\n616.56, 8.9\n") == (616, 8.9)
    assert parse_smi("616.56, [N/A]\n") == (616, None)
    assert parse_smi("") == (None, None)
    assert [cq_for(c) for c in (8, 10, 14, 16, 18, 20, 23)] == [10, 12, 18, 20, 22, 24, 27]
    # libx264 fallback: the same arguments the scripts passed before 0.2.4, with no probe on a machine without NVENC
    nvenc_ready.cache_clear()
    saved = os.environ.get("EDITOR_SE_MASK")
    os.environ["EDITOR_SE_MASK"] = "gpu"
    try:
        assert h264(14, "slow") == ["-c:v", "libx264", "-crf", "14", "-preset", "slow"]
    finally:
        os.environ.pop("EDITOR_SE_MASK") if saved is None else os.environ.__setitem__("EDITOR_SE_MASK", saved)
        nvenc_ready.cache_clear()
    probe = nvenc_cmd("ffmpeg")
    assert probe[probe.index("-c:v") + 1:probe.index("-cq")] == ["h264_nvenc", *NVENC]  # the probe tests what h264() uses
    assert status({}) is None
    assert "turned off" in status({"gpu": {"wanted": "off"}})[1]
    assert status({"gpu": {"torch": "cuda", "nvenc": True, "pref": "set"}})[1].endswith("cutouts, video encodes and motion renders")
    assert status({"gpu": {"torch": "cpu", "nvenc": True, "pref": "kept"}})[1].endswith("speeds up video encodes")
    print("✓ gpu selftest: decision, smi parsing, CQ map, libx264 fallback, probe settings, status line")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    sys.exit(__doc__)
