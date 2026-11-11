"""editor-superengine setup, stage 2 (F1). Started by install.sh inside the editor's own venv; never run directly.

Installs the union of what the skills' deps.json manifests need, every download pinned by sha256 in
pins.json: Node, ffmpeg (zscale checked), HyperFrames (npm ci from runtime/hyperframes), chrome-headless-shell,
the u2net cutout model, the transcription engine's Python packages (--require-hashes) and its models.
Records versions, URLs, hashes and the engine (with the facts its pick used) in <state>/state.json. Re-running skips
what is in place; --engine auto keeps the recorded engine unless those facts changed or --repick is given (S1b-fix).
Every failure prints one plain line and exits 1; details go to <state>/logs/install.log.
"""
import argparse, hashlib, json, os, platform, re, shutil, subprocess, sys, tarfile, time, traceback, zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

ALIGN_SKIPPED = "skipped (Intel Mac, torch 2.2.2 not tested)"
IMPORTS = {"parakeet-gpu": "import onnx_asr, onnxruntime", "parakeet-cpu": "import onnx_asr, onnxruntime",
           "faster-whisper": "import faster_whisper, ctranslate2, onnxruntime"}
ENGINE_MODEL = {"parakeet-gpu": "parakeet", "parakeet-cpu": "parakeet", "faster-whisper": "faster-whisper"}


class Fail(Exception):
    """One plain line for the client: what failed and what to do."""


class Setup:
    def __init__(self, st, engine, repick=False):
        self.st, self.requested, self.repick = Path(st), engine, repick
        self.pins = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
        self.key = rt.platform_key()
        (self.st / "logs").mkdir(parents=True, exist_ok=True)
        self.log = open(self.st / "logs" / "install.log", "a", encoding="utf-8")
        p = self.st / "state.json"
        self.state = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        self.state.setdefault("components", {})
        self.state.setdefault("models", {})

    # ---- helpers -------------------------------------------------------------------------------------
    def save(self):
        p = self.st / "state.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes((json.dumps(self.state, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        os.replace(tmp, p)

    def run(self, cmd, **kw):
        self.log.write(f"$ {' '.join(map(str, cmd))}\n")
        self.log.flush()
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", **kw)
        self.log.write(f"{r.stdout}{r.stderr}[exit {r.returncode}]\n")
        self.log.flush()
        self.last_result = r
        return r

    def command_failure(self, label, result=None):
        r = result if result is not None else getattr(self, "last_result", None)
        output = f"{r.stdout}\n{r.stderr}" if r is not None and r.returncode != 0 else ""
        lines = [line.strip() for line in output.splitlines() if line.strip()
                 and not re.search(r'^\s*File ".*", line \d+', line)
                 and not re.search(r"^\s*(?:hint:|note:)|A complete log of this run", line, re.I)]
        if re.search(r"\b(?:failed to download|error sending request|dns error|"
                     r"connection (?:refused|reset|timed out|closed)|timed out|tls handshake|certificate|"
                     r"EAI_AGAIN|ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|CERT_HAS_EXPIRED|"
                     r"UNABLE_TO_VERIFY_LEAF_SIGNATURE)\b|"
                     r"\bHTTP(?:\s+status\b[^\n]*|/[0-9.]+\s+)[45]\d\d\b", "\n".join(lines), re.I):
            return f"{label} failed. Check the internet connection, then run the setup again."
        errors = [i for i, line in enumerate(lines) if re.search(r"error:|npm (?:error|ERR!)|\w*Error:", line, re.I)]
        detail = lines[errors[-1]] if errors else (lines or ["the command reported no error details"])[-1]
        uv_errors = [i for i, line in enumerate(lines) if re.match(r"error:", line, re.I)]
        if uv_errors:
            causes = [line.split(":", 1)[1].strip() for line in lines[uv_errors[-1] + 1:]
                      if re.match(r"Caused by:", line, re.I)]
            if causes:
                detail = f"{lines[uv_errors[-1]]} ({causes[-1]})"
        npm = [re.sub(r"^npm (?:error|ERR!)(?:\s+|$)", "", line, flags=re.I).strip()
               for line in lines if re.match(r"npm (?:error|ERR!)(?:\s|$)", line, re.I)]
        if npm:
            code, descriptions = "", []
            for line in npm:
                if line.lower() == "usage:":
                    if descriptions and "." not in descriptions[-1]:
                        descriptions.pop()
                    break
                if (not line or re.match(r"(?:syscall|errno|path)\b", line, re.I)
                        or (re.match(r"command\b", line, re.I) and line.lower() != "command failed")
                        or line.startswith(("[", "{", "}")) or re.match(r"\S+:\s*.*,$", line)):
                    continue
                if re.match(r"code\s+\S+", line, re.I):
                    code = line.split(None, 1)[1]
                    if code.isdigit():
                        code = f"exit code {code}"
                else:
                    descriptions.append(line)
            detail = " ".join(descriptions)
            if code:
                detail = f"{code}: {detail}" if detail else code
            detail = re.sub(r"\s+", " ", detail)[:300].rstrip(". ")
        else:
            detail = detail[:200].rstrip(". ")
        return f"{label} failed: {detail}. Send the setup report."

    @staticmethod
    def sha256(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    def download(self, url, dest, sha, label):
        """Hash-checked download; a stuck or broken transfer is resumed with curl -C -."""
        dest = Path(dest)
        if dest.exists() and self.sha256(dest) == sha:
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        curl = shutil.which("curl")
        if not curl:
            raise Fail("curl is missing, so nothing can be downloaded. Reinstall Git for Windows (or update macOS), then run the setup again.")
        for _ in range(3):
            if part.exists() and self.sha256(part) == sha:
                break
            r = self.run([curl, "-fL", "-sS", "--retry", "5", "--retry-delay", "3", "--retry-all-errors",
                          "--connect-timeout", "30", "--speed-limit", "20000", "--speed-time", "60",
                          "-C", "-", "-o", part, url])
            if r.returncode == 0 and self.sha256(part) == sha:
                break
            if r.returncode in (0, 33):  # finished but wrong bytes, or the server can't resume: start over
                part.unlink(missing_ok=True)
            time.sleep(3)
        else:
            raise Fail(f"downloading {label} failed or arrived damaged. Check the internet connection, then run the setup again.")
        os.replace(part, dest)

    @staticmethod
    def extract(archive, dest):
        dest.mkdir(parents=True, exist_ok=True)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                for i in z.infolist():
                    out = z.extract(i, dest)
                    mode = i.external_attr >> 16
                    if mode & 0o111 and not i.is_dir():  # zipfile drops the exec bit (macOS binaries)
                        os.chmod(out, (mode & 0o777) | 0o200)
        else:
            with tarfile.open(archive) as t:
                t.extractall(dest, filter="data")

    # ---- components ----------------------------------------------------------------------------------
    def archives(self, name, label):
        pin = self.pins[name]
        plat = pin[self.key]
        cdir = f"{name}/{pin['version']}"
        bins = {b: f"{cdir}/{rel}" for b, rel in plat["bins"].items()}
        rec = self.state["components"].get(name, {})
        if rec.get("files") == plat["files"] and all((self.st / b).exists() for b in bins.values()):
            print(f"✓ {label} {pin['version']} already in place")
            return False
        print(f"Downloading {label} {pin['version']} ...", flush=True)
        target = self.st / cdir
        shutil.rmtree(target, ignore_errors=True)
        for f in plat["files"]:
            a = self.st / "downloads" / f"{name}-{unquote(Path(urlparse(f['url']).path).name)}"
            self.download(f["url"], a, f["sha256"], label)
            try:
                self.extract(a, target)
            except (OSError, zipfile.BadZipFile, tarfile.TarError) as e:
                if getattr(e, "winerror", None) == 206:  # Windows: the file name or path is too long
                    raise Fail(f"unpacking {label} failed because the install folder's path is too long for Windows. "
                               "Re-run the setup with EDITOR_SE_HOME set to a shorter folder, such as C:\\revxl-es.")
                raise Fail(f"unpacking {label} failed. Check the disk has free space, then run the setup again.")
            a.unlink()
        if not all((self.st / b).exists() for b in bins.values()):
            raise Fail(f"{label} unpacked without its program file. Send the setup report.")
        self.state["components"][name] = {"version": pin["version"], "files": plat["files"], "bins": bins}
        self.save()
        print(f"✓ {label} {pin['version']}")
        return True

    def node(self):
        if self.archives("node", "Node.js"):
            want = "v" + self.pins["node"]["version"]
            r = self.run([rt.tool("node", self.st), "--version"])
            if r.stdout.strip() != want:
                raise Fail(f"Node.js reports {r.stdout.strip() or 'nothing'} instead of {want}. Send the setup report.")

    def ffmpeg(self):
        if self.archives("ffmpeg", "ffmpeg"):
            pin = self.pins["ffmpeg"]
            ff = rt.tool("ffmpeg", self.st)
            filters = self.run([ff, "-hide_banner", "-filters"]).stdout
            encoders = self.run([ff, "-hide_banner", "-encoders"]).stdout
            for f in pin["need_filters"]:
                if not re.search(rf"^\s*\S+\s+{re.escape(f)}\s", filters, re.M):
                    raise Fail(f"the downloaded ffmpeg lacks its {f} filter, which the editor needs. Send the setup report.")
            for e in pin["need_encoders"]:
                if not re.search(rf"^\s*\S+\s+{re.escape(e)}\s", encoders, re.M):
                    raise Fail(f"the downloaded ffmpeg lacks its {e} encoder, which the editor needs. Send the setup report.")
            self.state["components"]["ffmpeg"]["checked"] = pin["need_filters"] + pin["need_encoders"]
            self.save()

    def chrome(self):
        self.archives("chrome", "Chrome for rendering (chrome-headless-shell)")

    def hyperframes(self):
        src = rt.PLUGIN_ROOT / "runtime" / "hyperframes"
        want = self.pins["hyperframes"]["version"]
        lock_sha = self.sha256(src / "package-lock.json")
        hfdir = self.st / "hyperframes"
        pkg = hfdir / "node_modules" / "hyperframes" / "package.json"
        rec = self.state["components"].get("hyperframes", {})
        if (rec.get("lock_sha256") == lock_sha and pkg.exists()
                and json.loads(pkg.read_text(encoding="utf-8")).get("version") == want):
            print(f"✓ HyperFrames {want} already in place")
            return
        print(f"Installing HyperFrames {want} (the motion renderer) ...", flush=True)
        hfdir.mkdir(parents=True, exist_ok=True)
        for f in ("package.json", "package-lock.json"):
            shutil.copyfile(src / f, hfdir / f)
        node = rt.tool("node", self.st)
        env = rt.python_env(self.st)
        env.update(npm_config_cache=str(self.st / "cache" / "npm"), npm_config_update_notifier="false",
                   npm_config_fund="false", npm_config_audit="false", HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1",
                   HYPERFRAMES_NO_UPDATE_CHECK="1", HYPERFRAMES_NO_AUTO_INSTALL="1", HYPERFRAMES_NO_OPTIONAL_INSTALL="1")
        env["PATH"] = os.pathsep.join([str(Path(node).parent), env["PATH"]])
        r = self.run([node, rt.tool("npm-cli", self.st), "ci", "--no-audit", "--no-fund"], cwd=hfdir, env=env)
        if r.returncode != 0:
            raise Fail(self.command_failure("installing HyperFrames", r))
        v = self.run(rt.hyperframes_cmd("--version", state=self.st), cwd=hfdir, env=rt.hyperframes_env(self.st))
        if v.stdout.strip().splitlines()[-1:] != [want]:
            raise Fail(f"HyperFrames reports {v.stdout.strip() or 'nothing'} instead of {want}. Send the setup report.")
        self.state["components"]["hyperframes"] = {
            "version": want, "source": "npm ci from runtime/hyperframes/package-lock.json (registry.npmjs.org)",
            "lock_sha256": lock_sha}
        self.save()
        print(f"✓ HyperFrames {want}")

    def cutout_model(self):
        m = self.pins["models"]["u2net"]
        dest = self.st / m["dest"]
        rec = self.state["models"].get("u2net", {})
        if rec.get("sha256") == m["sha256"] and dest.exists() and dest.stat().st_size == rec.get("size"):
            print("✓ cutout model (u2net_human_seg) already in place")
            return
        print("Downloading the cutout model (u2net_human_seg, 168 MB) ...", flush=True)
        self.download(m["url"], dest, m["sha256"], "the cutout model")
        self.state["models"]["u2net"] = {"url": m["url"], "sha256": m["sha256"], "dir": str(Path(m["dest"]).parent.as_posix()),
                                         "size": dest.stat().st_size}
        self.save()
        print("✓ cutout model")

    def hf_model(self, name):
        m = self.pins["models"][name]
        repo_dir = f"models/hub/models--{m['repo'].replace('/', '--')}"
        rel = f"{repo_dir}/snapshots/{m['commit']}"
        d = self.st / rel
        rec = self.state["models"].get(name, {})
        if (rec.get("commit") == m["commit"] and rec.get("files") == m["files"]
                and all((d / f).exists() and (d / f).stat().st_size == rec["sizes"].get(f) for f in m["files"])):
            print(f"✓ {name} model already in place")
            return
        print(f"Downloading the {name} model ({m['repo']}) ...", flush=True)
        src = m.get("download_repo", m["repo"])
        for f, sha in m["files"].items():
            self.download(f"https://huggingface.co/{src}/resolve/{m['commit']}/{f}", d / f, sha, f"the {name} model")
        refs = self.st / repo_dir / "refs"
        refs.mkdir(parents=True, exist_ok=True)
        (refs / "main").write_bytes(m["commit"].encode())  # lets name-based loads resolve offline (HF_HUB_OFFLINE=1)
        self.state["models"][name] = {"repo": m["repo"], "commit": m["commit"],
                                      "source": f"https://huggingface.co/{src}/resolve/{m['commit']}/",
                                      "dir": rel, "files": m["files"],
                                      "sizes": {f: (d / f).stat().st_size for f in m["files"]}}
        self.save()
        print(f"✓ {name} model")

    def python_packages(self, engine):
        """True when the engine's hash-locked packages are installed and import."""
        if engine.startswith("parakeet") and rt.masked("parakeet"):  # test-only mask (runtime.py docstring)
            print("(test mask: Parakeet is made uninstallable)")
            return False
        lock = HERE / "python" / f"{engine}.lock.txt"
        lock_sha = self.sha256(lock)
        vpy = rt.tool("python", self.st)
        code = IMPORTS[engine] + ("; import torch, transformers, numpy" if rt.align_supported() else "")
        rec = self.state.get("python_packages", {})
        if rec.get("lock_sha256") == lock_sha and self.run([vpy, "-c", code], env=rt.python_env(self.st)).returncode == 0:
            print(f"✓ Python packages for {engine} already in place")
            return True
        print(f"Installing the Python packages for {engine} (this is the big one, about 1-3 GB) ...", flush=True)
        env = rt.python_env(self.st)
        env.update(UV_CACHE_DIR=str(self.st / "cache" / "uv"), UV_NO_CONFIG="1", UV_PYTHON_INSTALL_DIR=str(self.st / "python"),
                   UV_HTTP_TIMEOUT="120")
        r = self.run([os.environ["EDITOR_SE_UV"], "pip", "sync", "--require-hashes", "--only-binary", ":all:",
                      "--python", vpy, lock], env=env)
        if r.returncode != 0 or self.run([vpy, "-c", code], env=rt.python_env(self.st)).returncode != 0:
            return False
        self.state["python_packages"] = {"engine": engine, "lock": f"skills/editor-doctor/scripts/python/{lock.name}",
                                         "lock_sha256": lock_sha, "source": "pypi.org, --require-hashes"}
        self.save()
        print(f"✓ Python packages for {engine}")
        return True

    def transcription(self, needs):
        language = rt.read_config().get("language")
        if self.requested == "auto":  # S1b-fix: re-picks only when the cached facts changed (or --repick)
            engine, reason, facts, kept = rt.decide_engine(self.state, language, self.repick)
            if kept:
                print("⚠ " + rt.GPU_KEPT.format(engine))
            backup, rec = f"backup: {engine} failed to install", rt.pick_record(self.state, language)
            if not self.repick and rec.get("engine") == "faster-whisper" and rec.get("engine_reason") == backup:
                engine, reason = "faster-whisper", backup  # D7: a failed Parakeet isn't retried on re-runs, only on --repick
        else:
            engine, reason = rt.pick_engine(self.requested)
            facts = rt.pick_facts(language, rt.pick_record(self.state, language).get("pick_facts"))[0]
        if engine == "none":  # H-S1a-1/2: old macOS; skip the engine install, don't fail
            print(f"⚠ {reason}")
            rt.record_pick(self.state, language, "none", reason, facts)
            self.state["align_words"] = "off (no transcription on this macOS)"
            self.save()
            return
        print(f"Transcription engine: {engine} ({reason})")
        if not self.python_packages(engine):
            if self.requested == "auto" and engine != "faster-whisper":
                print("Parakeet would not install on this computer, so the editor switches to its backup transcriber.")
                engine, reason = "faster-whisper", f"backup: {engine} failed to install"
                if not self.python_packages(engine):
                    raise Fail(self.command_failure("installing the transcriber's Python packages"))
            else:
                raise Fail(self.command_failure("installing the transcriber's Python packages"))
        rt.record_pick(self.state, language, engine, reason, facts)
        self.save()
        if "transcribe" in needs:
            self.hf_model(ENGINE_MODEL[engine])
        if "align" in needs:
            if rt.align_supported():
                self.hf_model("wav2vec2")
                self.state["align_words"] = "installed"
            else:
                self.state["align_words"] = ALIGN_SKIPPED
            self.save()
        if engine == "faster-whisper":
            print("⚠ " + rt.BACKUP_WARNING)

    # ---- entry ---------------------------------------------------------------------------------------
    def go(self):
        if self.key is None:
            raise Fail(rt.LINUX if sys.platform.startswith("linux") else
                       "this computer type isn't supported yet. The editor setup supports 64-bit Windows and macOS.")
        py = self.pins["python"]
        if platform.python_version() != py["version"]:
            raise Fail(f"the editor's Python is {platform.python_version()}, not {py['version']}. Run the setup again.")
        needs = set()
        for m in sorted((rt.PLUGIN_ROOT / "skills").glob("*/deps.json")):
            needs |= set(json.loads(m.read_text(encoding="utf-8"))["needs"])
        if "hyperframes" in needs:
            needs |= {"node", "chrome", "ffmpeg"}
        self.state.update(schema=1, platform=self.key, needs=sorted(needs))
        self.state["components"]["uv"] = {"version": os.environ.get("EDITOR_SE_UV_VERSION"),
                                          "url": os.environ.get("EDITOR_SE_UV_URL"),
                                          "sha256": os.environ.get("EDITOR_SE_UV_SHA256")}
        self.state["components"]["python"] = {"version": py["version"], "url": py[self.key]["url"],
                                              "sha256": py[self.key]["sha256"], "checked_by": py["via"]}
        self.save()
        if "ffmpeg" in needs:
            self.ffmpeg()
        if "node" in needs:
            self.node()
        if "chrome" in needs:
            self.chrome()
        if "hyperframes" in needs:
            self.hyperframes()
        if "cutout-model" in needs:
            self.cutout_model()
        if needs & {"transcribe", "align"}:
            self.transcription(needs)
        self.state["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()
        print(f"✓ Editor setup is ready (transcription: {self.state.get('engine', 'none')}).")


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", default="auto", choices=("auto",) + rt.ENGINES)
    ap.add_argument("--repick", action="store_true", help="with --engine auto: pick the engine again even if nothing changed")
    a = ap.parse_args()
    st = rt.state_dir()
    s = None
    try:
        s = Setup(st, a.engine, a.repick)
        s.go()
        rt.write_home_pointer(st)  # H-S1a-path-2: later runs with no EDITOR_SE_HOME find this folder
        return 0
    except Fail as e:
        print(f"✗ Editor setup: {e}")
    except KeyboardInterrupt:
        print("✗ Editor setup: stopped before it finished. Run it again to carry on where it stopped.")
    except Exception:
        if s is not None:
            s.log.write(traceback.format_exc())
            s.log.flush()
        print(f"✗ Editor setup stopped unexpectedly. Run it again; if it repeats, send the setup report "
              f"(details in {Path(st) / 'logs' / 'install.log'}).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
