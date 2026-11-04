"""Shared paths and environment builders for editor-superengine scripts (stdlib only).

Scripts that Claude runs through Bash get no CLAUDE_PLUGIN_ROOT and no plugin option env, so
everything here is found from this file's own location and from the OS rule for the state folder:

    Windows  %LOCALAPPDATA%/revxl/editor-superengine
    macOS    ~/Library/Application Support/revxl/editor-superengine
    Linux    ${XDG_DATA_HOME:-~/.local/share}/revxl/editor-superengine
    EDITOR_SE_HOME overrides all three (tests).

The installer (skills/editor-doctor/scripts/install.sh) fills the state folder and writes
state.json; tool() reads binary paths from it. Every HyperFrames call goes through
hyperframes_cmd() + hyperframes_env(); every Python child gets python_env().

The client workspace (the cwd) holds editor/editor.config.json and editor/.platform.json (the doctor writes both).

TEST-ONLY MASKS (the one place they are documented): EDITOR_SE_MASK is a comma list for tests, never set for
a client. gpu = gpu_read() answers "no GPU" (a successful read); parakeet = install.py treats the Parakeet packages as uninstallable;
resolve = the doctor's Resolve detection finds nothing. Example: EDITOR_SE_MASK=gpu,parakeet,resolve
"""
import json, os, platform, re, shutil, subprocess, sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]

# PB-11: the one plain warning shown whenever the backup transcriber is chosen (S1b reuses it).
BACKUP_WARNING = ("On this computer the editor uses its backup transcriber. It can drop a retake "
                  "when you say the same line twice, so check the spots where you re-recorded a line.")

ENGINES = ("parakeet-gpu", "parakeet-cpu", "faster-whisper")
# H-S1a-1..3 (hub 11.04.26): no engine installs there; everything that doesn't need transcription keeps working.
NO_ENGINE_ARM = "Transcription needs macOS 14 or newer on this Mac. Update macOS to turn it on."
NO_ENGINE_INTEL = "Transcription needs macOS 13 or newer on this Mac. Update macOS to turn it on."
LINUX = "Linux isn't supported yet (Windows and macOS are)."
# S1b-fix: the plain line when a GPU read fails and the recorded engine is kept ({} = the engine).
GPU_KEPT = "The NVIDIA graphics card check didn't answer this time, so the editor kept its current transcriber ({})."
# HF-1 (hard rule, privacy): these HyperFrames commands never ship.
BANNED_HF_COMMANDS = {"skills", "init", "play", "upgrade", "docs"}


def masked(what):
    """True when the test-only EDITOR_SE_MASK (see the module docstring) hides `what`."""
    return what in {m.strip() for m in os.environ.get("EDITOR_SE_MASK", "").split(",")}


def config_path(cwd=None):
    return Path(cwd or Path.cwd()) / "editor" / "editor.config.json"


def read_config(cwd=None):
    """The workspace's editor.config.json as a dict ({} when missing or unreadable)."""
    try:
        return json.loads(config_path(cwd).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def is_english(language):
    """Unset counts as English (Parakeet v2 is English-only, H-S1a-4)."""
    return not language or str(language).strip().lower().replace("_", "-").split("-")[0] in ("en", "english")


def state_dir():
    if os.environ.get("EDITOR_SE_HOME"):
        return Path(os.environ["EDITOR_SE_HOME"])
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "revxl" / "editor-superengine"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "revxl" / "editor-superengine"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "revxl" / "editor-superengine"


def platform_key():
    """win-x64, mac-arm64 or mac-x64; None for anything the installer has no pins for."""
    m = platform.machine().lower()
    if sys.platform == "win32" and m in ("amd64", "x86_64"):
        return "win-x64"
    if sys.platform == "darwin":
        return "mac-arm64" if m == "arm64" else "mac-x64" if m == "x86_64" else None
    return None


def mac_major():
    v = platform.mac_ver()[0]
    return int(v.split(".")[0]) if v else 0


def gpu_read():
    """One `nvidia-smi -L` read: ("yes", "<GPU names>"), ("no", None) under the gpu test mask, ("no-smi", None) when
    nvidia-smi isn't there, ("failed", None) on a non-zero exit, a timeout, or output with no GPU line."""
    if masked("gpu"):
        return "no", None
    exe = shutil.which("nvidia-smi")
    if not exe and sys.platform == "win32":
        p = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        exe = str(p) if p.exists() else None
    if not exe:
        return "no-smi", None
    try:
        r = subprocess.run([exe, "-L"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "failed", None
    names = re.findall(r"^GPU \d+: (.+?)(?: \(UUID:.*)?$", r.stdout, re.M)
    return ("yes", ", ".join(n.strip() for n in names)) if r.returncode == 0 and names else ("failed", None)


def has_nvidia_gpu():
    return gpu_read()[0] == "yes"


def pick_facts(language, cached=None):
    """(facts, answered): what the engine pick uses (OS, arch, macOS major, NVIDIA GPU + name, the config language).
    answered is False when the GPU read failed, or nvidia-smi went missing where a GPU was recorded; a failed read is
    never a change, so facts are then the cached ones (or "no GPU" when nothing is cached, the pick before S1b-fix)."""
    got, name = gpu_read()
    answered = got in ("yes", "no") or (got == "no-smi" and not (cached or {}).get("gpu"))
    if not answered and cached:
        return dict(cached), False
    return {"os": sys.platform, "arch": platform.machine().lower(), "macos_major": mac_major() if sys.platform == "darwin" else None,
            "gpu": got == "yes", "gpu_name": name if got == "yes" else None, "language": language}, answered


def decide_engine(state, language, repick=False):
    """(engine, reason, facts, kept) for --engine auto. state.json keeps `pick_facts` beside the recorded `engine`.
    Re-picks only on the first run (nothing cached), when a successful read shows the facts changed, or on repick.
    kept = True: the GPU read failed, so the recorded engine stays (print GPU_KEPT); no packages change."""
    cached, recorded = state.get("pick_facts"), state.get("engine")
    facts, answered = pick_facts(language, cached)
    if cached and recorded:
        if not answered:
            return recorded, state.get("engine_reason", ""), facts, True
        if facts == cached and not repick:
            return recorded, state.get("engine_reason", ""), facts, False
    return (*pick_engine("auto", language, gpu=facts["gpu"]), facts, False)


def pick_engine(requested="auto", language=None, gpu=None):
    """(engine, reason). The one place the transcription engine is chosen (TX-1, H-S1a-1..4).
    engine "none" = no engine installs on this macOS; the reason is then the plain update-macOS message.
    gpu: the NVIDIA answer from pick_facts(); None reads it here."""
    if requested != "auto":
        if requested not in ENGINES:
            raise ValueError(f"unknown engine {requested!r}")
        return requested, "asked for"
    key = platform_key()
    other = None if is_english(language) else (
        "faster-whisper", f"language {language}: Parakeet understands English only, so the multilingual faster-whisper")
    if key == "win-x64":
        if other:
            return other
        if has_nvidia_gpu() if gpu is None else gpu:
            return "parakeet-gpu", "Windows with an NVIDIA GPU"
        return "parakeet-cpu", "Windows without an NVIDIA GPU"
    if key == "mac-arm64":
        if mac_major() < 14:
            return "none", NO_ENGINE_ARM
        return other or ("parakeet-cpu", "Apple Silicon on macOS 14 or newer")
    if key == "mac-x64":
        if mac_major() < 13:
            return "none", NO_ENGINE_INTEL
        return "faster-whisper", "Intel Mac"
    raise RuntimeError(LINUX if sys.platform.startswith("linux") else "this computer type has no editor setup yet")


def align_supported():
    """align_words needs torch; Intel Macs top out at torch 2.2.2, which is untested, so skip there."""
    return platform_key() != "mac-x64"


def load_state(state=None):
    p = Path(state or state_dir()) / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def tool(name, state=None):
    """Absolute path of an installed binary: node, npm-cli, ffmpeg, ffprobe, chrome, hyperframes, python."""
    st = Path(state or state_dir())
    if name == "python":
        return str(st / "venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    if name == "hyperframes":
        return str(st / "hyperframes" / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs")
    comps = load_state(st).get("components", {})
    for c in comps.values():
        if name in c.get("bins", {}):
            return str(st / c["bins"][name])
    raise KeyError(f"{name} is not installed; run the editor setup first")


def model_dir(model, state=None):
    """Snapshot folder of a hash-checked model (parakeet, wav2vec2, faster-whisper)."""
    st = Path(state or state_dir())
    m = load_state(st)["models"][model]
    return str(st / m["dir"])


def _nvidia_dll_dirs(st):
    sp = Path(st) / "venv" / "Lib" / "site-packages" / "nvidia"
    return [str(p) for p in sorted(sp.glob("*/bin")) if p.is_dir()] if sp.is_dir() else []


def python_env(state=None, base=None):
    """Env for every Python child we launch (TRI-1) plus the state folder's models and ffmpeg."""
    st = Path(state or state_dir())
    env = dict(os.environ if base is None else base)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", HF_HOME=str(st / "models"),
               HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TRANSFORMERS_OFFLINE="1")
    extra = []
    try:
        extra.append(str(Path(tool("ffmpeg", st)).parent))
    except (KeyError, OSError, ValueError):
        pass
    if sys.platform == "win32":
        extra += _nvidia_dll_dirs(st)  # CUDA 12 / cuDNN 9 DLLs from the nvidia-* wheels (parakeet-gpu)
    if extra:
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def hyperframes_env(state=None, base=None):
    """Env for every HyperFrames call: telemetry, update check and lazy installs off, set per call."""
    st = Path(state or state_dir())
    env = python_env(st, base)
    home = str(st / "hyperframes-home")  # 0.8.184 keeps its config, caches and the u2net model under ~
    env.update(HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_NO_UPDATE_CHECK="1",
               HYPERFRAMES_NO_AUTO_INSTALL="1", HYPERFRAMES_NO_OPTIONAL_INSTALL="1",
               HYPERFRAMES_BROWSER_PATH=tool("chrome", st), HYPERFRAMES_FFMPEG_PATH=tool("ffmpeg", st),
               HYPERFRAMES_FFPROBE_PATH=tool("ffprobe", st), HOME=home, USERPROFILE=home,
               npm_config_update_notifier="false")
    env["PATH"] = os.pathsep.join([str(Path(tool("node", st)).parent), env.get("PATH", "")])
    return env


def hyperframes_cmd(*args, state=None):
    """argv for the pinned local CLI (never bare npx). `preview` always gets --no-open (F-17)."""
    args = list(args)
    if args and args[0] in BANNED_HF_COMMANDS:
        raise ValueError(f"hyperframes {args[0]} is not allowed (HF-1)")
    if args and args[0] == "preview" and "--no-open" not in args:
        args.append("--no-open")
    return [tool("node", state), tool("hyperframes", state)] + args
