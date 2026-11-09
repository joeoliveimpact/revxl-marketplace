"""editor-doctor offline self-test (S1c): proves the editor renders and transcribes with no network.

Claude runs it with the editor's own Python, never the client:
  <editor python> -X utf8 -I offline_selftest.py [--static]
--static  no render: no remote URLs in the plugin's HTML/CSS, GSAP loaded as a local file and never inlined,
          and runtime.hyperframes_env() turning telemetry, update checks and auto-installs off.
default   --static, then in a temp project (fixture in ../selftest + the shipped GSAP and Inter font, cold font
          cache, Node network guard, proxies to a dead port): HyperFrames lint, a 2 s render checked with ffprobe,
          a second render without the font that must look different, zero network attempts, and the
          installed transcriber on selftest/speech10s.flac scored against selftest/speech10s.txt.
Prints one ✓/✗ line per check; exit 0 when all pass, else 1. On CI, failures also go to ::error:: and the step summary.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

P = HERE.parents[2]
FIXTURE = HERE.parent / "selftest"
NETGUARD = HERE / "netguard.cjs"
REMOTE = re.compile(r"<script\b[^>]*\bsrc\s*=\s*[\"']?\s*(?:https?:)?//|<link\b[^>]*\bhref\s*=\s*[\"']?\s*(?:https?:)?//"
                    r"|@import\s+(?:url\(\s*)?[\"']?\s*(?:https?:)?//|url\(\s*[\"']?\s*(?:https?:)?//"
                    r"|fonts\.googleapis|fonts\.gstatic", re.I)
INLINE_SCRIPT = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.I | re.S)
GSAP_MARKS = ("greensock", "gsap.com")
ENV_WANT = {"HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1",
            "HYPERFRAMES_NO_AUTO_INSTALL": "1", "npm_config_update_notifier": "false"}
DEAD = "http://127.0.0.1:9"
FONT_FRAME = 54        # 1.8 s: the scene's text is near full opacity
FONT_DIFF_MIN = 0.002  # share of pixels (gray, |diff| > 32) that must change when the font file is removed
results = []
measured = {}  # numbers for the CI notice line


def check(name, ok, detail=""):
    line = f"{'✓' if ok else '✗'} {name}" + (f": {detail}" if detail else "")
    print(line, flush=True)
    if not ok and os.environ.get("GITHUB_ACTIONS"):
        print(f"::error::{line[2:]}", flush=True)
    results.append((name, ok, detail))
    return ok


# ---- static -----------------------------------------------------------------------------------------------
def static():
    files = [f for d in (P / "skills", P / "runtime" / "fonts") if d.exists()
             for f in sorted(d.rglob("*")) if f.suffix.lower() in (".html", ".htm", ".css")]
    bad = [f"{f.relative_to(P).as_posix()}: {m.group(0)[:60]}" for f in files
           for m in [REMOTE.search(f.read_text(encoding="utf-8", errors="replace"))] if m]
    check("no remote scripts, stylesheets or fonts in the plugin's HTML/CSS", not bad,
          f"{len(files)} files scanned" if not bad else "; ".join(bad))
    idx = (FIXTURE / "index.html").read_text(encoding="utf-8")
    check("the self-test page loads GSAP from ./vendor/gsap.min.js",
          re.search(r"<script\b[^>]*\bsrc\s*=\s*[\"']\./vendor/gsap\.min\.js[\"']", idx) is not None)
    inl = [f.relative_to(P).as_posix() for f in files if f.suffix.lower() != ".css"
           for s in INLINE_SCRIPT.findall(f.read_text(encoding="utf-8", errors="replace"))
           if any(k in s.lower() for k in GSAP_MARKS)]
    check("GSAP is never inlined in a page", not inl, "; ".join(inl))
    with tempfile.TemporaryDirectory() as t:  # a stand-in state, so this check runs before any install
        bins = {b: f"x/{b}" for b in ("node", "chrome", "ffmpeg", "ffprobe")}
        (Path(t) / "state.json").write_bytes(json.dumps({"components": {"x": {"bins": bins}}}).encode())
        env = rt.hyperframes_env(t)
    off = [f"{k}={env.get(k)!r}" for k, v in ENV_WANT.items() if env.get(k) != v]
    check("HyperFrames runs with telemetry, update checks and auto-installs off", not off, "; ".join(off))


# ---- full ------------------------------------------------------------------------------------------------
def run(cmd, env=None, timeout=900):
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def tail(s, n=300):
    return " ".join(s.split())[-n:]


def frame(video, n, w, h):
    """One frame as 8-bit gray bytes, or b"" if it can't be read."""
    r = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-i", str(video), "-vf", f"select=eq(n\\,{n})",
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    return r.stdout if w and len(r.stdout) == w * h else b""


def render_checks(tmp):
    proj = tmp / "proj"
    shutil.copytree(FIXTURE, proj, ignore=shutil.ignore_patterns("speech10s.*"))
    (proj / "vendor").mkdir()
    shutil.copy2(P / "runtime" / "gsap" / "gsap.min.js", proj / "vendor" / "gsap.min.js")
    (proj / "fonts").mkdir()
    shutil.copy2(P / "runtime" / "fonts" / "Inter-Regular.woff2", proj / "fonts" / "selftest-font.woff2")
    for d in ("home", "cache", "tmp"):
        (tmp / d).mkdir()
    log = tmp / "netguard.jsonl"
    env = rt.hyperframes_env()
    env.update(HOME=str(tmp / "home"), USERPROFILE=str(tmp / "home"), XDG_CACHE_HOME=str(tmp / "cache"),
               TEMP=str(tmp / "tmp"), TMP=str(tmp / "tmp"), TMPDIR=str(tmp / "tmp"),
               NODE_OPTIONS=f'--require "{NETGUARD.as_posix()}"', NETGUARD_LOG=str(log), GIT_ALLOW_PROTOCOL="file",
               NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env[k] = env[k.lower()] = DEAD
    env.pop("NETGUARD_ALLOW", None)

    rc, out, err = run(rt.hyperframes_cmd("lint", proj, "--json"), env)
    try:
        errors = json.loads(out[out.index("{"):])["errorCount"]
    except (ValueError, KeyError):
        errors = None
    check("HyperFrames lint of the self-test page", rc == 0 and errors == 0,
          "0 errors" if rc == 0 and errors == 0 else f"exit {rc}, errors {errors}: {tail(out + err)}")

    videos = {}
    for tag in ("font", "nofont"):
        if tag == "nofont":
            (proj / "fonts" / "selftest-font.woff2").unlink()
        mp4 = tmp / f"{tag}.mp4"
        rc, out, err = run(rt.hyperframes_cmd("render", proj, "-o", mp4), env)
        ok = rc == 0 and mp4.exists()
        check(f"render ({'with' if tag == 'font' else 'without'} the font)", ok,
              "" if ok else f"exit {rc}: {tail(out + err)}")
        if ok:
            videos[tag] = mp4

    if "font" in videos:
        rc, out, err = run([rt.tool("ffprobe"), "-v", "error", "-count_frames", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_read_frames,width,height:format=duration", "-of", "json",
                            videos["font"]])
        try:
            j = json.loads(out)
            s, dur = j["streams"][0], float(j["format"]["duration"])
            frames, w, h = int(s["nb_read_frames"]), int(s["width"]), int(s["height"])
        except (ValueError, KeyError, IndexError):
            frames, dur, w, h = None, None, 0, 0
        check("the render is 2.0 s and 60 frames", frames == 60 and dur is not None and abs(dur - 2.0) <= 0.1,
              f"{dur} s, {frames} frames, {w}x{h}")
        rc, out, err = run([rt.tool("ffmpeg"), "-hide_banner", "-i", videos["font"], "-vf",
                            "signalstats,metadata=print:key=lavfi.signalstats.YMAX", "-f", "null", "-"])
        ymax = [int(float(v)) for v in re.findall(r"lavfi\.signalstats\.YMAX=([\d.]+)", err)]
        check("no black frames (every frame has bright pixels, YMAX >= 64)", len(ymax) == 60 and min(ymax) >= 64,
              f"{len(ymax)} frames, lowest YMAX {min(ymax) if ymax else None}")
        if "nofont" in videos:
            a, b = frame(videos["font"], FONT_FRAME, w, h), frame(videos["nofont"], FONT_FRAME, w, h)
            share = measured["font"] = sum(abs(x - y) > 32 for x, y in zip(a, b)) / len(a) if a and b else 0.0
            check("the shipped font is the one on screen (removing it changes the text)", share >= FONT_DIFF_MIN,
                  f"{share:.2%} of pixels changed at frame {FONT_FRAME} (needs >= {FONT_DIFF_MIN:.1%})")

    n = measured["netguard"] = sum(1 for _ in open(log, encoding="utf-8")) if log.exists() else 0
    # Both renders must have run under the guard (node exits at start if the guard can't load), or 0 proves nothing.
    check("no network attempts during lint and render", n == 0 and len(videos) == 2,
          f"{n} blocked attempts logged" if n else "0 attempts" if len(videos) == 2 else "the renders did not run")


def transcribe_check(tmp):
    engine = rt.read_config().get("engine") if rt.config_path().exists() else rt.load_state().get("engine")
    if engine not in rt.ENGINES:
        return check("transcription", False, f"no transcriber is installed (engine {engine}); run the editor doctor")
    wav = tmp / "speech.wav"
    rc, out, err = run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", FIXTURE / "speech10s.flac", "-ac", "1",
                        "-ar", "16000", "-c:a", "pcm_s16le", wav])
    if rc != 0:
        return check("transcription", False, f"ffmpeg could not decode the speech clip: {tail(err)}")
    rc, out, err = run([rt.tool("python"), "-X", "utf8", "-I", __file__, "--transcribe", engine, wav],
                       env=rt.python_env())
    try:
        hyp = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return check(f"transcription ({engine})", False, f"exit {rc}: {tail(out + err)}")
    norm = lambda s: re.findall(r"[a-z0-9]+", s.lower())  # noqa: E731
    ref, got = norm((FIXTURE / "speech10s.txt").read_text(encoding="utf-8")), norm(" ".join(hyp))
    score = sum(w in set(got) for w in ref) / len(ref)
    measured.update(engine=engine, words=len(got), score=score)
    check(f"transcription ({engine})", len(got) >= 10 and score >= 0.6,
          f"{len(got)} words, {score:.0%} of the {len(ref)} reference words heard (needs 10 words and 60%)")


def transcribe_worker(engine, wav):
    """Runs in its own process under rt.python_env(); prints the words as one JSON line."""
    if engine.startswith("parakeet"):
        import onnx_asr, onnxruntime as ort
        want = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
        model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", rt.model_dir("parakeet"), quantization="int8",
                                    providers=want)
        words = "".join(model.with_timestamps().recognize(wav).tokens).replace("▁", " ").split()
    else:
        import wave, numpy as np
        from faster_whisper import WhisperModel
        with wave.open(wav) as w:  # samples, not a path: the locked PyAV 19 rejects faster-whisper 1.2.1's av.open()
            audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        # ponytail: CPU int8 only; a 10 s clip doesn't need the GPU path.
        segs, _ = WhisperModel(rt.model_dir("faster-whisper"), device="cpu", compute_type="int8").transcribe(
            audio, language="en")
        words = " ".join(s.text for s in segs).split()
    print(json.dumps(words, ensure_ascii=False))


# ---- cleanup and CI summary --------------------------------------------------------------------------------
def remove(tmp):
    """Delete the temp folder; on a lock (Windows), wait, then kill whatever still runs from it, then retry."""
    for attempt in range(6):
        shutil.rmtree(tmp, ignore_errors=True)
        if not tmp.exists():
            return
        if attempt == 2:
            if os.name == "nt":
                ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
                run([ps, "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "
                     f"'*{tmp.name}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"], timeout=60)
            else:
                run(["pkill", "-9", "-f", tmp.name], timeout=30)
        time.sleep(2)
    print(f"(could not delete the temp folder {tmp}; it is safe to delete by hand)")


def summary():
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    rows = "".join(f"| {'✓' if ok else '✗'} | {n} | {d.replace('|', '/')} |\n" for n, ok, d in results)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"### editor offline self-test\n\n| | check | detail |\n|---|---|---|\n{rows}\n")


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--static", action="store_true", help="static checks only, no render")
    ap.add_argument("--transcribe", nargs=2, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.transcribe:
        transcribe_worker(*a.transcribe)
        return 0
    static()
    if not a.static:
        tmp = Path(tempfile.mkdtemp(prefix="editor-selftest-"))
        try:
            render_checks(tmp)
            transcribe_check(tmp)
        except Exception as e:  # a crash is a failed check, never a pass
            check("self-test", False, f"stopped: {type(e).__name__}: {e}")
        finally:
            remove(tmp)
    summary()
    bad = sum(not ok for _, ok, _ in results)
    print(f"{'✓' if not bad else '✗'} offline self-test: {len(results) - bad} of {len(results)} checks passed")
    if not bad and not a.static and os.environ.get("GITHUB_ACTIONS"):  # annotations are what CI readers can see
        m = measured
        print(f"::notice title=offline self-test::{len(results)}/{len(results)} checks passed; engine {m['engine']}; "
              f"transcript {m['words']} words, {m['score']:.0%} of reference; font proof {m['font']:.2%} changed px; "
              f"netguard {m['netguard']} attempts")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
