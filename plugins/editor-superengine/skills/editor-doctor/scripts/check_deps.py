"""editor-doctor (S1b): machine test, engine pick + install, Resolve detection, STATUS lines, config.

Claude runs it with the editor's own Python from the client's workspace folder (the cwd), never the client:
  <state>/venv/Scripts/python.exe (macOS: <state>/venv/bin/python) -X utf8 -I check_deps.py [--no-install] [--repick]
  [--set-nle mcp|resolve|none|auto] [--selftest]
1. Machine test: OS, arch, macOS version, NVIDIA GPU, RAM total and free. decide_engine() (runtime.py) keeps the
   recorded engine unless the facts cached beside it in state.json changed (a failed GPU read is never a change:
   STATUS gpu warn) or --repick is given; else pick_engine() picks, reading `language` from editor.config.json.
2. Unless --no-install: the S1a installer ensures that engine (sh install.sh --engine auto [--repick] makes the same
   decide_engine() decision); when Parakeet won't install, it falls back to faster-whisper and the PB-11 warning shows.
3. Read-only DaVinci Resolve detection (PB-40): installed, Studio, version >= 21.1, external scripting. Never
   starts Resolve. nle = resolve only when all four hold, else none.
4. Checks every component S1a installs against state.json and the real files (models by sha256).
5. Writes <cwd>/editor/editor.config.json (missing keys added, existing values kept; `engine`, `nle` and `nle_source`
   are the doctor's, and a `manual` nle is kept), <cwd>/editor/.platform.json (atomic), and <state>/styles/default.json
   once (never overwritten). --set-nle records the client's nle choice (auto = back to detection) and does nothing else.
Output (stable, for S13 Health and S15a Cockpit), after any installer lines:
  STATUS <component> ok|warn|missing <plain detail>
  FIX <component> <plain fix for this OS>          (right after every warn or missing line)
Exit 1 when anything required is missing, else 0. --no-install checks only (health checks).
"""
import argparse, contextlib, io, json, os, platform, plistlib, re, shutil, subprocess, sys, tempfile, time, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import install  # noqa: E402  (IMPORTS, ENGINE_MODEL, Setup.sha256: one copy of each)

INSTALL_SH = HERE / "install.sh"
PINS = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
MAC = sys.platform == "darwin"
STAMP = "S1a+S1b"
BLOCKS = ("grade", "scenes", "broll", "music", "transitions", "cover", "trial", "three")
# H-R3: setup and machine settings only, no brand/look/style keys (those live in the saved style, H-B5).
DEFAULTS = {"schema": 1, "engine": None, "language": None, "nle": "auto", "nle_source": "auto", "ports": {"board": 8747},
            "voice_cleanup": "free", "paths": {"editor": "editor", "videos": "videos"}, **{b: {} for b in BLOCKS}}
STYLE_SKELETON = ('{"schema":1,"style_id":null,"accent":null,"font":null,"look":null,'
                  '"transitions":{"allowed":[],"sfx_pair":null}}')
RESOLVE_MIN = (21, 1)
SCRIPTING = {0: "None", 1: "Local", 2: "Network"}  # Preferences > System > General order (Resolve's README)
PREFS = ("DaVinci Resolve > Preferences (Cmd+,)" if MAC else "DaVinci Resolve > Preferences (Ctrl+,)")
LINE = re.compile(r"^STATUS [a-z0-9-]+ (ok|warn|missing) \S.*$")
GPU_FIX = ("Nothing is needed now. If this shows again, restart the computer (that resets the graphics driver), "
           "then Claude re-runs the doctor.")
BAD_CONFIG = ("editor/editor.config.json isn't valid JSON, so the doctor left it as it is",
              "Claude repairs the JSON in editor/editor.config.json (keeping the client's values), then re-runs the doctor.")


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=300, **kw)


class Report:
    def __init__(self):
        self.items, self.required_missing = [], False

    def add(self, comp, level, detail, fix=None, required=True):
        assert (level == "ok") == (fix is None), comp
        self.items.append({"component": comp, "level": level, "detail": detail, "fix": fix})
        self.required_missing |= level == "missing" and required

    def lines(self):
        out = []
        for i in self.items:
            out.append(f"STATUS {i['component']} {i['level']} {i['detail']}")
            if i["fix"]:
                out.append(f"FIX {i['component']} {i['fix']}")
        return out


def rerun(engine):
    return f'Claude re-runs the setup: sh "{INSTALL_SH.as_posix()}" --engine {engine}'


def skill_needs():
    return {m.parent.name: set(json.loads(m.read_text(encoding="utf-8"))["needs"])
            for m in sorted((rt.PLUGIN_ROOT / "skills").glob("*/deps.json"))}


# ---- 1. machine test ---------------------------------------------------------------------------------
def ram_gb():
    try:
        if sys.platform == "win32":
            import ctypes
            class M(ctypes.Structure):  # MEMORYSTATUSEX
                _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                    (n, ctypes.c_ulonglong) for n in ("total", "free", "tp", "ap", "tv", "av", "ae")]
            m = M()
            m.len = ctypes.sizeof(M)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                total, free = m.total, m.free
            else:
                return None, None
        elif MAC:
            total = int(run(["sysctl", "-n", "hw.memsize"]).stdout)
            vm = run(["vm_stat"]).stdout
            page = int(re.search(r"page size of (\d+)", vm).group(1))
            free = page * sum(int(re.search(rf"{k}:\s+(\d+)", vm).group(1))
                              for k in ("Pages free", "Pages inactive", "Pages speculative"))
        else:
            return None, None
        return round(total / 2**30, 1), round(free / 2**30, 1)
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None, None


def machine_test(gpu):
    """gpu: the NVIDIA answer the engine pick used; None when the read failed and the cached engine was kept."""
    total, free = ram_gb()
    return {"os": platform.system(), "os_release": platform.release(),
            "os_version": platform.mac_ver()[0] if MAC else platform.version(),
            "arch": platform.machine(), "platform": rt.platform_key(), "macos_major": rt.mac_major() if MAC else None,
            "nvidia_gpu": gpu, "ram_total_gb": total, "ram_free_gb": free,
            "test_masks": sorted(m for m in ("gpu", "parakeet", "resolve") if rt.masked(m))}


def describe(f):
    osn = f"macOS {f['os_version']}" if MAC else f"{f['os']} {f['os_release']} ({f['os_version']})"
    gpu = {True: "NVIDIA GPU", False: "no NVIDIA GPU"}.get(f["nvidia_gpu"], "NVIDIA GPU check didn't answer")
    ram = f", {f['ram_total_gb']} GB RAM ({f['ram_free_gb']} GB free)" if f["ram_total_gb"] else ""
    mask = f" [test masks: {','.join(f['test_masks'])}]" if f["test_masks"] else ""
    return f"{osn} {f['arch']}, {gpu}{ram}{mask}"


# ---- 2. the installer ensures the engine --------------------------------------------------------------
def run_installer(engine, repick=False):
    sh = shutil.which("sh") or shutil.which("bash")
    if not sh:
        print("✗ Editor setup: no shell was found to run the setup.")
        return 127
    sys.stdout.flush()
    return subprocess.run([sh, INSTALL_SH.as_posix(), "--engine", engine] + (["--repick"] if repick else [])).returncode


# ---- 3. Resolve detection (read-only, never starts Resolve) --------------------------------------------
def _reg(key, name):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            return str(winreg.QueryValueEx(k, name)[0])
    except (OSError, ImportError):
        return None


def scripting_mode(prefs):
    """External scripting as saved in Resolve's config.dat: None / Local / Network, or None when not saved."""
    try:
        m = re.search(r"^\s*System\.Scripting\.Mode\s*=\s*(\d+)", Path(prefs).read_text(encoding="utf-8", errors="replace"), re.M)
    except OSError:
        return None
    return SCRIPTING.get(int(m.group(1)), f"unknown ({m.group(1)})") if m else None


def version_ok(v):
    nums = tuple(int(x) for x in re.findall(r"\d+", v or "")[:2])
    return len(nums) == 2 and nums >= RESOLVE_MIN


def detect_resolve():
    d = {"installed": False, "studio": None, "version": None, "scripting": None, "evidence": []}
    if rt.masked("resolve"):
        d["evidence"].append("test mask: Resolve hidden")
        return d
    name = ""
    if sys.platform == "win32":
        app = Path(os.environ.get("ProgramFiles") or r"C:\Program Files") / "Blackmagic Design" / "DaVinci Resolve" / "Resolve.exe"
        if not app.is_file():
            return d
        d["version"] = _reg(r"SOFTWARE\Blackmagic Design\DaVinci Resolve", "Version")
        lic = Path(os.environ.get("ProgramData") or r"C:\ProgramData") / "Blackmagic Design" / "DaVinci Resolve" / "Support" / ".license"
        prefs = Path(os.environ.get("APPDATA", "")) / "Blackmagic Design" / "DaVinci Resolve" / "Preferences" / "config.dat"
        d["evidence"].append(r"HKLM\SOFTWARE\Blackmagic Design\DaVinci Resolve: Version")
    elif MAC:
        app = next((a for a in (Path("/Applications/DaVinci Resolve/DaVinci Resolve.app"),
                                Path("/Applications/DaVinci Resolve Studio.app"))
                    if (a / "Contents" / "Info.plist").is_file()), None)
        if not app:
            return d
        try:
            info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
        except (OSError, ValueError):
            info = {}
        d["version"] = info.get("CFBundleShortVersionString") or info.get("CFBundleVersion")
        name = f"{info.get('CFBundleName', '')} {info.get('CFBundleIdentifier', '')}"
        lic = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/.license")
        prefs = Path.home() / "Library" / "Preferences" / "Blackmagic Design" / "DaVinci Resolve" / "config.dat"
        d["evidence"].append(str(app / "Contents" / "Info.plist"))
    else:
        return d
    d["installed"] = True
    d["evidence"] += [str(app), str(lic), str(prefs)]
    lics = [p.name for p in lic.iterdir()] if lic.is_dir() else []  # names only; never read a licence file
    d["studio"] = "studio" in name.lower() or any("studio" in n.lower() and n.endswith(".lic") for n in lics)
    d["scripting"] = scripting_mode(prefs)
    return d


def resolve_lines(rep, d):
    """Adds the resolve-* STATUS lines; returns nle (resolve only when every requirement is met)."""
    later = "then Claude re-runs the doctor."
    if not d["installed"]:
        rep.add("resolve-installed", "warn", "DaVinci Resolve isn't installed, so the Resolve hand-off stays off (optional)",
                "Nothing is needed for editing. For the Resolve hand-off, install DaVinci Resolve Studio 21.1 or newer "
                f"from blackmagicdesign.com, {later}", required=False)
        return "none"
    rep.add("resolve-installed", "ok", "DaVinci Resolve is installed")
    if d["studio"]:
        rep.add("resolve-edition", "ok", "DaVinci Resolve Studio (a Studio licence is on this computer)")
    else:
        rep.add("resolve-edition", "warn", "no DaVinci Resolve Studio licence was found; the free edition can't take the hand-off",
                f"Optional: the hand-off needs DaVinci Resolve Studio (the paid edition). Once Studio is activated, {later}",
                required=False)
    if version_ok(d["version"]):
        rep.add("resolve-version", "ok", f"version {d['version']} (21.1 or newer)")
    else:
        rep.add("resolve-version", "warn", f"version {d['version'] or 'unknown'}; the hand-off needs 21.1 or newer",
                f"Update DaVinci Resolve Studio to 21.1 or newer (Help > Check for Updates), {later}", required=False)
    turn_on = (f"In DaVinci Resolve Studio open {PREFS} > System > General, set External scripting using to Local, "
               f"click Save, {later}")
    live = "a live connection can only be confirmed while Resolve is open, and the doctor never opens it"
    if d["scripting"] in ("Local", "Network"):
        rep.add("resolve-scripting", "ok", f"external scripting is {d['scripting']} in Resolve's saved preferences ({live})")
    elif d["scripting"] is None:
        rep.add("resolve-scripting", "warn", f"can't tell whether external scripting is on: Resolve hasn't saved that "
                f"preference yet ({live})", turn_on, required=False)
    else:
        rep.add("resolve-scripting", "warn", f"external scripting is {d['scripting']} in Resolve's saved preferences",
                turn_on, required=False)
    ok = d["studio"] and version_ok(d["version"]) and d["scripting"] in ("Local", "Network")
    return "resolve" if ok else "none"


# ---- 4. component checks -----------------------------------------------------------------------------
def model_check(st, name):
    m = PINS["models"][name]
    if "files" in m:
        d = st / f"models/hub/models--{m['repo'].replace('/', '--')}/snapshots/{m['commit']}"
        files = m["files"]
    else:
        d, files = (st / m["dest"]).parent, {Path(m["dest"]).name: m["sha256"]}
    bad = [f for f, sha in files.items() if not (d / f).is_file() or install.Setup.sha256(d / f) != sha]
    return (not bad), (f"{len(files)} file(s) match their sha256" if not bad else f"missing or damaged: {', '.join(bad)}")


def engine_line(picked, reason, inst, state_reason):
    """(level, detail, fix) for the transcription engine: which engine and why (TX-1, PB-11)."""
    if picked == "none":
        off = sorted(s for s, n in skill_needs().items() if n & {"transcribe", "align"})
        return "warn", f"none: {reason.split('. ')[0]}. Off until then: {', '.join(off)}", reason.split(". ", 1)[1]
    if inst is None:
        return "missing", f"no transcription engine is installed (this computer should use {picked}: {reason})", None
    if inst == "faster-whisper" and (picked == inst or str(state_reason).startswith("backup")):
        why = reason if picked == inst else state_reason
        return "warn", f"faster-whisper, the backup transcriber ({why})", rt.BACKUP_WARNING
    if inst != picked:
        return "warn", f"{inst} is installed, but this computer should use {picked} ({reason})", None
    return "ok", f"{inst} ({reason})", None


def run_checks(rep, st, picked, reason):
    """Adds one STATUS line per component; returns the engine that is really installed (or None)."""
    st = Path(st)
    state = rt.load_state(st)
    comps = state.get("components", {})
    needs = set().union(*skill_needs().values())
    if "hyperframes" in needs:
        needs |= {"node", "chrome", "ffmpeg"}
    vpy = Path(rt.tool("python", st))

    def tool(name):
        p = Path(rt.tool(name, st))
        if not p.is_file():
            raise FileNotFoundError(p)
        return p

    # the transcriber first: its result decides which engine the setup command names
    inst, tr = None, None
    pp = state.get("python_packages", {})
    eng = pp.get("engine")
    if picked != "none" and needs & {"transcribe", "align"}:
        tr = ("missing", "the transcriber's Python packages aren't installed")
        if eng in rt.ENGINES and vpy.is_file():
            if pp.get("lock_sha256") != install.Setup.sha256(HERE / "python" / f"{eng}.lock.txt"):
                tr = ("missing", f"the {eng} packages don't match this plugin version's lock")
            else:
                code = install.IMPORTS[eng] + ("; import torch, transformers, numpy" if rt.align_supported() else "")
                try:
                    loads = run([vpy, "-c", code], env=rt.python_env(st)).returncode == 0
                except (OSError, subprocess.SubprocessError):
                    loads = False
                if loads:
                    inst, tr = eng, ("ok", f"{eng} packages are installed and load")
                else:
                    tr = ("missing", f"the {eng} packages are installed but won't load")
    sreason = state.get("engine_reason", "")
    if inst and (inst == picked or str(sreason).startswith("backup")):
        setup_engine = inst
    else:
        setup_engine = picked if picked in rt.ENGINES else "auto"
    fix = rerun(setup_engine)

    def add(comp, ok, detail, required=True):
        rep.add(comp, "ok" if ok else "missing", detail, None if ok else fix, required)

    try:
        r = run([vpy, "-I", "-c", "import platform, sys; print(platform.python_version()); print(sys.base_prefix)"])
        ver, base = (r.stdout.split("\n") + ["", ""])[:2]
        managed = Path(base.strip()).resolve().is_relative_to((st / "python").resolve())
        add("python", ver.strip() == PINS["python"]["version"] and managed,
            f"the editor's own Python {ver.strip()} in its venv" if managed else "the editor's own Python isn't set up")
    except (OSError, subprocess.SubprocessError):
        add("python", False, "the editor's own Python isn't set up")
    if "ffmpeg" in needs:
        try:
            tool("ffprobe")
            ff = tool("ffmpeg")
            out = run([ff, "-hide_banner", "-filters"]).stdout + run([ff, "-hide_banner", "-encoders"]).stdout
            lack = [x for x in PINS["ffmpeg"]["need_filters"] + PINS["ffmpeg"]["need_encoders"]
                    if not re.search(rf"^\s*\S+\s+{re.escape(x)}\s", out, re.M)]
            add("ffmpeg", not lack, f"ffmpeg {comps['ffmpeg']['version']} with zscale" if not lack
                else f"ffmpeg lacks {', '.join(lack)}")
        except (KeyError, OSError, subprocess.SubprocessError):
            add("ffmpeg", False, "ffmpeg isn't installed")
    if "node" in needs:
        want = "v" + PINS["node"]["version"]
        try:
            got = run([tool("node"), "--version"]).stdout.strip()
            add("node", got == want, f"Node.js {got}" if got == want else f"Node.js reports {got or 'nothing'}, not {want}")
        except (KeyError, OSError, subprocess.SubprocessError):
            add("node", False, "Node.js isn't installed")
    if "hyperframes" in needs:
        want = PINS["hyperframes"]["version"]
        try:
            lock_ok = comps["hyperframes"]["lock_sha256"] == install.Setup.sha256(rt.PLUGIN_ROOT / "runtime" / "hyperframes" / "package-lock.json")
            v = run(rt.hyperframes_cmd("--version", state=st), cwd=st / "hyperframes", env=rt.hyperframes_env(st))
            got = (v.stdout.strip().splitlines() or [""])[-1]
            add("hyperframes", lock_ok and got == want, f"HyperFrames {got}" if lock_ok and got == want
                else f"HyperFrames reports {got or 'nothing'}, not {want} from this plugin's lockfile")
        except (KeyError, OSError, subprocess.SubprocessError):
            add("hyperframes", False, "HyperFrames isn't installed")
    if "chrome" in needs:
        try:
            tool("chrome")
            got = comps["chrome"]["version"]
            add("chrome", got == PINS["chrome"]["version"], f"Chrome for rendering {got}")
        except (KeyError, OSError):
            add("chrome", False, "Chrome for rendering isn't installed")
    if "cutout-model" in needs:
        ok, detail = model_check(st, "u2net")
        add("cutout-model", ok, f"u2net_human_seg: {detail}")
    if tr:
        add("transcriber", tr[0] == "ok", tr[1])
        model = install.ENGINE_MODEL.get(inst or setup_engine)
        if model and "transcribe" in needs:
            ok, detail = model_check(st, model)
            add(f"model-{model}", ok, detail)
        if "align" in needs:
            if not rt.align_supported():
                rep.add("align", "warn", "align_words is skipped on Intel Macs (torch 2.2.2 is not tested)",
                        "Nothing to do: word-level alignment is off on Intel Macs; everything else works.", required=False)
            else:
                ok, detail = model_check(st, "wav2vec2")
                ok = ok and state.get("align_words") == "installed" and inst is not None
                add("align", ok, f"align_words with wav2vec2: {detail}" if ok else f"align_words isn't ready ({detail})")
    if picked == "none" or tr:
        level, detail, efix = engine_line(picked, reason, inst, sreason)
        if level != "ok" and efix is None:
            efix = rerun(picked if picked in rt.ENGINES else "auto")
        rep.add("engine", level, detail, efix, required=level == "missing")
    return inst


# ---- 5. files ----------------------------------------------------------------------------------------
def atomic_write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, p)


def write_config(cwd, **keys):
    """Missing keys added, existing values kept; only `keys` (the doctor's: engine, nle, nle_source) are set. False on bad JSON."""
    p = rt.config_path(cwd)
    cur = {}
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return False
        if not isinstance(cur, dict):
            return False
    out = dict(cur)
    for k, v in DEFAULTS.items():
        if k not in out:
            out[k] = json.loads(json.dumps(v))
        elif isinstance(v, dict) and isinstance(out[k], dict):
            for kk, vv in v.items():
                out[k].setdefault(kk, vv)
    out.update(keys)
    atomic_write(p, json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return True


def choose_nle(cfg, detected):
    """(nle, nle_source): a `manual` nle (the client's choice) is kept; `auto` or no nle_source (older configs) takes detection."""
    return (cfg.get("nle"), "manual") if cfg.get("nle_source") == "manual" else (detected, "auto")


def nle_detail(nle, source):
    if source == "manual":
        return f"{nle} (chosen by you; the doctor keeps it)"
    return f"{nle} (the Resolve hand-off {'can be offered later' if nle == 'resolve' else 'stays off'})"


def set_nle(cwd, choice):
    """--set-nle: records the client's choice as manual; auto goes back to detection (run now, read-only)."""
    rep = Report()
    nle, src = (resolve_lines(Report(), detect_resolve()), "auto") if choice == "auto" else (choice, "manual")
    if write_config(Path(cwd), nle=nle, nle_source=src):
        rep.add("nle", "ok", nle_detail(nle, src))
    else:
        rep.add("config", "missing", *BAD_CONFIG)
    print("\n".join(rep.lines()))
    return 1 if rep.required_missing else 0


def ensure_style(st):
    """H-B5: the empty saved-style skeleton, created once and never overwritten (S10 fills it)."""
    p = Path(st) / "styles" / "default.json"
    if p.exists():
        return False
    atomic_write(p, STYLE_SKELETON)
    return True


def doctor(cwd, st, do_install=True, run_install=run_installer, repick=False):
    cwd, st = Path(cwd), Path(st)
    rep = Report()
    cfg = rt.read_config(cwd)
    language = cfg.get("language")
    try:
        picked, reason, pf, kept = rt.decide_engine(rt.load_state(st), language, repick)
    except RuntimeError as e:
        rep.add("machine", "missing", f"{describe(machine_test(rt.has_nvidia_gpu()))}: {e}", "Use the editor on a Windows PC or a Mac.")
        print("\n".join(rep.lines()))
        return 1
    facts = machine_test(None if kept else pf["gpu"])
    rep.add("machine", "ok", describe(facts))
    if kept:
        rep.add("gpu", "warn", rt.GPU_KEPT.format(picked), GPU_FIX, required=False)
    rc = run_install("auto", repick) if do_install else None  # the installer makes the same decision, then ensures it
    fell_back = str(rt.load_state(st).get("engine_reason", "")).startswith("backup")
    inst = run_checks(rep, st, picked, reason)
    res = detect_resolve()
    nle, nle_source = choose_nle(cfg, resolve_lines(rep, res))
    engine = "none" if picked == "none" else inst
    rep.add("nle", "ok", nle_detail(nle, nle_source))
    if not write_config(cwd, engine=engine, nle=nle, nle_source=nle_source):
        rep.add("config", "missing", *BAD_CONFIG)
    else:
        rep.add("config", "ok", "editor/editor.config.json is up to date")
    ensure_style(st)
    tools = {}
    for n in ("python", "node", "npm-cli", "ffmpeg", "ffprobe", "chrome", "hyperframes"):
        try:
            tools[n] = rt.tool(n, st)
        except KeyError:
            tools[n] = None
    pj = json.loads((rt.PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    atomic_write(cwd / "editor" / ".platform.json", json.dumps({
        "schema": 1, "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stamp": {"plugin_version": pj.get("version"), "steps": STAMP},
        "state_folder": str(st), "machine": facts, "language": language,
        "engine": {"picked": picked, "reason": reason, "installed": engine, "fell_back": fell_back, "installer_exit": rc,
                   "kept_gpu_unanswered": kept},
        "resolve": res, "nle": nle, "nle_source": nle_source, "tools": tools, "status": rep.items, "required_missing": rep.required_missing,
    }, indent=1, ensure_ascii=False) + "\n")
    print("\n".join(rep.lines()))
    return 1 if rep.required_missing else 0


# ---- selftest (offline, temp dirs only) ----------------------------------------------------------------
def selftest():
    saved_env = {k: os.environ.get(k) for k in ("EDITOR_SE_MASK", "EDITOR_SE_HOME")}
    saved_rt = (rt.platform_key, rt.mac_major, rt.sys)
    saved_gpu = (rt.gpu_read, rt.shutil, rt.subprocess)
    n = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ws, st = td / "ws", td / "state"
        os.environ["EDITOR_SE_HOME"] = str(st)
        here = os.getcwd()
        os.chdir(td)  # read_config() reads the cwd's editor/; keep the real workspace out of it
        try:
            # config: every key and empty block; an existing config keeps its values, gains missing keys
            assert write_config(ws, engine="parakeet-cpu", nle="none")
            c = json.loads(rt.config_path(ws).read_text(encoding="utf-8"))
            assert set(c) == set(DEFAULTS) and all(c[b] == {} for b in BLOCKS)
            assert (c["engine"], c["nle"], c["voice_cleanup"], c["language"], c["ports"]["board"]) == ("parakeet-cpu", "none", "free", None, 8747)
            atomic_write(rt.config_path(ws), json.dumps({"voice_cleanup": "auphonic", "ports": {"board": 9001},
                                                          "grade": {"lut": "x"}, "paths": {"videos": "clips"},
                                                          "language": "es", "custom": 1}))
            assert write_config(ws, engine="faster-whisper", nle="resolve")
            c = json.loads(rt.config_path(ws).read_text(encoding="utf-8"))
            assert (c["voice_cleanup"], c["ports"]["board"], c["grade"], c["paths"], c["language"], c["custom"]) == \
                ("auphonic", 9001, {"lut": "x"}, {"videos": "clips", "editor": "editor"}, "es", 1)
            assert set(DEFAULTS) <= set(c) and c["scenes"] == {} and (c["engine"], c["nle"]) == ("faster-whisper", "resolve")
            rt.config_path(ws).write_bytes(b"{not json")
            assert not write_config(ws, engine="x", nle="none") and rt.config_path(ws).read_bytes() == b"{not json"
            n += 3
            # style skeleton: exact bytes, created once, never overwritten
            assert ensure_style(st) and (st / "styles" / "default.json").read_text(encoding="utf-8") == STYLE_SKELETON
            json.loads(STYLE_SKELETON)
            (st / "styles" / "default.json").write_bytes(b'{"schema":1,"style_id":"mine"}')
            assert not ensure_style(st) and (st / "styles" / "default.json").read_bytes() == b'{"schema":1,"style_id":"mine"}'
            n += 1
            # machine-test picks, masks, language and the hub's H-S1a-1..4 cases
            rt.platform_key = lambda: "win-x64"
            os.environ["EDITOR_SE_MASK"] = "gpu"
            assert not rt.has_nvidia_gpu() and rt.pick_engine()[0] == "parakeet-cpu"
            assert rt.pick_engine("auto", "en-US")[0] == "parakeet-cpu" and rt.pick_engine("auto", "English")[0] == "parakeet-cpu"
            e, why = rt.pick_engine("auto", "es")
            assert e == "faster-whisper" and "es" in why and "English only" in why
            rt.platform_key, rt.mac_major = (lambda: "mac-arm64"), (lambda: 13)
            assert rt.pick_engine() == ("none", rt.NO_ENGINE_ARM)
            assert rt.NO_ENGINE_ARM == "Transcription needs macOS 14 or newer on this Mac. Update macOS to turn it on."
            rt.mac_major = lambda: 14
            assert rt.pick_engine()[0] == "parakeet-cpu" and rt.pick_engine("auto", "fr")[0] == "faster-whisper"
            rt.platform_key, rt.mac_major = (lambda: "mac-x64"), (lambda: 12)
            assert rt.pick_engine() == ("none", rt.NO_ENGINE_INTEL)
            assert rt.NO_ENGINE_INTEL == "Transcription needs macOS 13 or newer on this Mac. Update macOS to turn it on."
            rt.mac_major = lambda: 13
            assert rt.pick_engine() == ("faster-whisper", "Intel Mac")
            rt.platform_key, rt.sys = (lambda: None), type("S", (), {"platform": "linux"})
            try:
                rt.pick_engine()
                raise AssertionError("Linux must not pick an engine")
            except RuntimeError as x:
                assert str(x) == "Linux isn't supported yet (Windows and macOS are)."
            rt.platform_key, rt.mac_major, rt.sys = saved_rt
            lv, ld, lf = engine_line("none", rt.NO_ENGINE_ARM, None, "")
            assert lv == "warn" and "macOS 14" in ld and "reel-first-cuts" in ld and lf == "Update macOS to turn it on."
            n += 4
            # Parakeet masked: the installer's guard refuses it, S1a's auto falls back, and the warning shows.
            # Offline: the real Setup.transcription(), with only the backup's package install stubbed out.
            os.environ["EDITOR_SE_MASK"] = "parakeet"
            assert install.Setup.python_packages(None, "parakeet-gpu") is False
            rt.platform_key = lambda: "win-x64"
            s = install.Setup(td / "fb", "auto")
            real = s.python_packages
            s.python_packages = lambda e: real(e) if e.startswith("parakeet") else True
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                s.transcription(set())
            s.log.close()
            rt.platform_key = saved_rt[0]
            out = buf.getvalue()
            assert s.state["engine"] == "faster-whisper" and s.state["engine_reason"].startswith("backup: parakeet-")
            assert "Parakeet would not install" in out and ("⚠ " + rt.BACKUP_WARNING) in out, out
            lv, ld, lf = engine_line("parakeet-gpu", "Windows with an NVIDIA GPU", "faster-whisper", "backup: parakeet-gpu failed to install")
            assert lv == "warn" and "backup" in ld and lf == rt.BACKUP_WARNING
            assert engine_line("parakeet-gpu", "w", "parakeet-gpu", "")[0] == "ok"
            n += 3
            # Resolve masked -> nle none; the saved scripting preference and the version rule
            os.environ["EDITOR_SE_MASK"] = "resolve"
            rep = Report()
            assert resolve_lines(rep, detect_resolve()) == "none" and rep.items[0]["fix"]
            assert write_config(ws / "r", engine=None, nle="none") and rt.read_config(ws / "r")["nle"] == "none"
            for text, want in (("System.Scripting.Mode = 1\n", "Local"), ("a = 1\nSystem.Scripting.Mode = 0\n", "None"),
                               ("System.Scripting.Mode = 2", "Network"), ("Other = 1\n", None)):
                (td / "config.dat").write_text(text, encoding="utf-8")
                assert scripting_mode(td / "config.dat") == want, text
            assert scripting_mode(td / "absent.dat") is None
            assert version_ok("21.1.00017") and version_ok("22.0") and not version_ok("21.0.3") and not version_ok(None)
            full = {"installed": True, "studio": True, "version": "21.1.00017", "scripting": "Local", "evidence": []}
            assert resolve_lines(Report(), full) == "resolve"
            assert resolve_lines(Report(), dict(full, scripting=None)) == "none"
            assert resolve_lines(Report(), dict(full, studio=False)) == "none"
            n += 3
            # a missing dep: its STATUS line, then its plain fix naming the exact setup command
            os.environ.pop("EDITOR_SE_MASK")
            ms = td / "missing"
            atomic_write(ms / "state.json", json.dumps({"components": {"ffmpeg": {"version": "8.1.2", "bins": {"ffmpeg": "ffmpeg/x/ffmpeg.exe", "ffprobe": "ffmpeg/x/ffprobe.exe"}}},
                                                        "python_packages": {"engine": "parakeet-gpu"}}))
            rep = Report()
            assert run_checks(rep, ms, "parakeet-gpu", "Windows with an NVIDIA GPU") is None and rep.required_missing
            lines = rep.lines()
            for comp in ("python", "ffmpeg", "node", "hyperframes", "chrome", "cutout-model", "transcriber", "engine"):
                i = lines.index(next(x for x in lines if x.startswith(f"STATUS {comp} missing ")))
                assert lines[i + 1].startswith(f"FIX {comp} Claude re-runs the setup: sh \"") and \
                    lines[i + 1].endswith('install.sh" --engine parakeet-gpu'), lines[i + 1]
            assert all(LINE.match(x) for x in lines if x.startswith("STATUS")), lines
            n += 2
            # S1b-fix engine cache (stubbed GPU reads): a failed or ambiguous read never changes the recorded engine
            rt.platform_key, read = (lambda: "win-x64"), ["yes", "RTX 4060"]
            rt.gpu_read = lambda: tuple(read)
            e, why, f, kept = rt.decide_engine({}, None)  # first run, nothing cached: the pick as before
            assert (e, kept, f["gpu"], f["gpu_name"], f["language"]) == ("parakeet-gpu", False, True, "RTX 4060", None)
            st0 = {"engine": e, "engine_reason": why, "pick_facts": f}
            for bad in (["failed", None], ["no-smi", None]):  # timeout/non-zero/garbled, or nvidia-smi gone: kept
                read[:] = bad
                assert rt.decide_engine(st0, None) == (e, why, f, True)
                assert rt.decide_engine(st0, "es", repick=True) == (e, why, f, True)
            read[:] = ["yes", "RTX 4060"]
            assert rt.decide_engine(st0, None) == (e, why, f, False)  # unchanged: no re-pick
            assert rt.decide_engine(dict(st0, engine="faster-whisper"), None)[0] == "faster-whisper"
            assert rt.decide_engine(dict(st0, engine="faster-whisper"), None, repick=True)[0] == "parakeet-gpu"
            assert rt.decide_engine(st0, "es")[0] == "faster-whisper"  # the language changed
            read[:] = ["yes", "RTX 5090"]
            assert rt.decide_engine(st0, None)[2]["gpu_name"] == "RTX 5090"  # a new card is a change (re-picked)
            read[:] = ["no", None]  # a successful no-GPU read (the gpu mask) is a change
            e2, why2, f2, kept = rt.decide_engine(st0, None)
            assert (e2, kept, f2["gpu"]) == ("parakeet-cpu", False, False)
            read[:] = ["no-smi", None]  # no nvidia-smi where no GPU was recorded: an answer, unchanged
            assert rt.decide_engine({"engine": e2, "engine_reason": why2, "pick_facts": f2}, None) == (e2, why2, f2, False)
            read[:] = ["failed", None]  # first run with a failed read: the pick as before (no GPU)
            assert rt.decide_engine({}, None)[:2] == ("parakeet-cpu", "Windows without an NVIDIA GPU")
            rt.gpu_read = saved_gpu[0]
            fake = {}
            rt.shutil = types.SimpleNamespace(which=lambda name: "nvidia-smi")

            def frun(cmd, **kw):
                if fake["out"] is None:
                    raise subprocess.TimeoutExpired(cmd, 20)
                return subprocess.CompletedProcess(cmd, fake["rc"], fake["out"], "")
            rt.subprocess = types.SimpleNamespace(run=frun, SubprocessError=subprocess.SubprocessError)
            for rc, out, want in ((0, "GPU 0: NVIDIA GeForce RTX 4060 Laptop GPU (UUID: GPU-2f33)\n", ("yes", "NVIDIA GeForce RTX 4060 Laptop GPU")),
                                  (9, "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.", ("failed", None)),
                                  (0, "zz9 qq garbled\n", ("failed", None)), (0, "", ("failed", None)), (0, None, ("failed", None))):
                fake.update(rc=rc, out=out)
                assert rt.gpu_read() == want, (rc, out)
            rt.gpu_read, rt.shutil, rt.subprocess = saved_gpu
            n += 3
            # S1b-fix nle_source: a manual nle survives detection; auto (or no nle_source: older configs) follows it
            assert choose_nle({"nle": "mcp", "nle_source": "manual"}, "resolve") == ("mcp", "manual")
            assert choose_nle({"nle": "mcp"}, "none") == ("none", "auto") and choose_nle({"nle_source": "auto"}, "resolve") == ("resolve", "auto")
            os.environ["EDITOR_SE_MASK"] = "resolve"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                assert set_nle(ws / "n", "mcp") == 0
                c1 = rt.read_config(ws / "n")
                assert set_nle(ws / "n", "auto") == 0
            c2 = rt.read_config(ws / "n")
            assert (c1["nle"], c1["nle_source"], c2["nle"], c2["nle_source"]) == ("mcp", "manual", "none", "auto")
            assert "STATUS nle ok mcp (chosen by you" in buf.getvalue() and set(DEFAULTS) <= set(c2), buf.getvalue()
            n += 2
            # S1b-fix round 2: a recorded fallback is kept on re-runs (D7), but --repick retries Parakeet, then falls back
            # again with the PB-11 warning. The real Setup.transcription(); only the package installs are stubbed.
            os.environ["EDITOR_SE_MASK"] = ""
            rt.platform_key, rt.gpu_read = (lambda: "win-x64"), (lambda: ("yes", "RTX 4060"))
            facts = rt.pick_facts(None)[0]
            for repick, want in ((False, ["faster-whisper"]), (True, ["parakeet-gpu", "faster-whisper"])):
                rs = td / f"rp{int(repick)}"
                atomic_write(rs / "state.json", json.dumps({"engine": "faster-whisper", "pick_facts": facts,
                                                            "engine_reason": "backup: parakeet-gpu failed to install"}))
                s = install.Setup(rs, "auto", repick)
                calls = []
                s.python_packages = lambda e: calls.append(e) or e == "faster-whisper"
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    s.transcription(set())
                s.log.close()
                out = buf.getvalue()
                assert calls == want, (repick, calls)
                assert (s.state["engine"], s.state["engine_reason"]) == ("faster-whisper", "backup: parakeet-gpu failed to install")
                assert ("Parakeet would not install" in out) == repick and ("⚠ " + rt.BACKUP_WARNING) in out, out
            rt.platform_key, rt.gpu_read = saved_rt[0], saved_gpu[0]
            n += 1
        finally:
            os.chdir(here)
            rt.platform_key, rt.mac_major, rt.sys = saved_rt
            rt.gpu_read, rt.shutil, rt.subprocess = saved_gpu
            for k, v in saved_env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    print(f"✓ editor-doctor selftest: {n} check groups passed")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-install", action="store_true", help="check only; never runs the installer")
    ap.add_argument("--repick", action="store_true", help="pick the transcription engine again even if nothing changed")
    ap.add_argument("--set-nle", choices=("mcp", "resolve", "none", "auto"),
                    help="record the client's hand-off choice in editor.config.json (auto = back to detection); nothing else runs")
    ap.add_argument("--selftest", action="store_true", help="offline self-check in temp folders")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.set_nle:
        return set_nle(Path.cwd(), a.set_nle)
    return doctor(Path.cwd(), rt.state_dir(), do_install=not a.no_install, repick=a.repick)


if __name__ == "__main__":
    sys.exit(main())
