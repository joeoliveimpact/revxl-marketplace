#!/usr/bin/env python3
"""G1.3 done-test: render.py --grade bakes reel-grade's cube into the cut's one encode, both directions.

  EDITOR_SE_HOME=<state> <editor python> -X utf8 -I tests/editor/render_grade_test.py [--case a|b|c|d|e|f|take2|all] [--keep]

<state> is an installed editor state folder (ffmpeg, ffprobe); it is only read. Run it from a git checkout: case d
reads render.py as it was at BEFORE. Every case is a light job (H-LOCK-1): a 3 s 640x360 lavfi clip of four known
colour bands with a tone, a two-segment cuts.json, and render.py's own main() run in-process with conform() swapped
for a 360x640 scale (as cut_safety_test.py does), so no heavy lock; below 1 GB free RAM it refuses (exit 76). Cases:
  a  an identity grade (look none) -> the graded master's bands within 2/255 of the ungraded master's.
  b  a tint grade (look warm, baked by reel-grade's write_grade) -> the graded master's bands within TOL/255 of
     apply_grade.py's output on the ungraded master's frame (the same plate). Mutant: --grade ignored -> fails.
  c  grade.json's cube_sha wrong -> refused with one plain line, nothing rendered. Mutant: sha check off -> renders.
  d  no --grade -> the ffmpeg commands and filter graphs are byte-identical to render.py's at BEFORE, after the
     frame-exact render substitution, for the same
     inputs (real conform, SDR and HLG; captured, never encoded); with --grade the commands are the same and the
     graph gains exactly one lut3d, at the end of the conform.
  e  saved Warm and Mono looks in isolated scratch homes -> clearly different master colour bands.
  f  mixed recordings use their own cubes and reject changed cubes; a top-level-only cube mutant fails.
  take2  keeping only take 2 uses its raw even when take 1 is positional; the old > 1 rule fails.
Prints one "✓ <case>" / "✗ <case>: <why>" line per case, then "N passed, M failed". Exit 0 only when all pass.
"""
import argparse, contextlib, hashlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins/editor-superengine"
RENDER = PLUGIN / "skills/reel-first-cuts/scripts/render.py"
BEFORE = "02a6e9d"   # the last commit whose render.py has no --grade
sys.dont_write_bytecode = True   # the in-process imports below must not leave __pycache__ in the plugin
sys.path[:0] = [str(RENDER.parent), str(PLUGIN / "skills/reel-grade/scripts"), str(PLUGIN / "skills/_shared")]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import isolated_home  # noqa: E402
from frame_exact_graph import frame_exact_graph  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

BANDS = ["c08060", "2040d0", "20b040", "808080"]   # 160 px each in the 640x360 source, 90 px each in the master
TINY_VF = "scale=360:640"
TOL = 2   # 8-bit levels: the graded master (lut inside the encode) vs apply_grade.py on the ungraded master's frame
CUTS = {"fps": 30, "speed": 1.0, "segments": [{"src_in_f": 0, "src_out_f": 30, "out_in_f": 0, "out_out_f": 30},
                                              {"src_in_f": 45, "src_out_f": 75, "out_in_f": 30, "out_out_f": 60}]}


class Fail(Exception):
    pass


class Captured(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Fail(why)


def free_gb():
    if os.name != "nt":
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2 ** 30
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("tot", "avail", "totpf", "availpf", "totv", "availv", "ext")]
    m = MS()
    m.len = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2 ** 30


class Capture:
    """Stands in for render.py's subprocess: records each encode (command + graph file bytes) instead of running
    it, passes every other call through, and stops render.py once both encodes are recorded."""
    def __init__(self):
        self.encodes = []

    PIPE, DEVNULL = subprocess.PIPE, subprocess.DEVNULL

    def Popen(self, cmd, **kw):
        # The streaming encoder uses Popen; retain the same command/graph proof.
        if "-/filter_complex" in cmd:
            self.run(cmd)
            return subprocess.Popen([sys.executable, "-c", "pass"], **kw)
        return subprocess.Popen(cmd, **kw)

    def run(self, cmd, **kw):
        if "-/filter_complex" in cmd:
            self.encodes.append((list(cmd), Path(cmd[cmd.index("-/filter_complex") + 1]).read_bytes()))
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if len(self.encodes) == 2:
            raise Captured()
        return subprocess.run(cmd, **kw)


def load_render(path):
    spec = importlib.util.spec_from_file_location("render_under_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_render(path, work, src, *args, tiny=True, sub=None):
    """render.py's main() in-process -> (exit code, everything it printed, the module)."""
    m = load_render(path)
    if tiny:
        m.conform = lambda video, crop=None: TINY_VF
    if sub:
        m.subprocess = sub
    argv, buf = sys.argv, io.StringIO()
    sys.argv = ["render.py", str(work), str(src), *map(str, args)]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            m.main()
        rc = 0
    except SystemExit as e:
        rc = e.code
    except Captured:
        rc = "captured"
    finally:
        sys.argv = argv
    return rc, buf.getvalue(), m


def main():
    ensure_utf8_output()
    names = ["a", "b", "c", "d", "e", "f", "take2"]
    ap = argparse.ArgumentParser(description="G1.3 render --grade done-test")
    ap.add_argument("--case", choices=names + ["all"], default="all")
    ap.add_argument("--keep", action="store_true", help="keep the scratch folder")
    a = ap.parse_args()
    want = names if a.case == "all" else [a.case]
    gb = free_gb()
    if gb < 1.0:
        print("REFUSED: %.2f GB free RAM < 1.0 GB, so this test is unproven (RAM)" % gb)
        return 76
    try:
        ff = rt.tool("ffmpeg")
        need(Path(ff).is_file() and Path(rt.tool("ffprobe")).is_file(), "")
    except (KeyError, OSError, ValueError, Fail):
        print("✗ This test needs an installed editor state: set EDITOR_SE_HOME to one (ffmpeg, ffprobe)")
        return 1

    import numpy as np
    import bake_grade as bg
    from apply_grade import read_frame
    scratch = Path(tempfile.mkdtemp(prefix="g13_render_grade_"))
    S = {"clip": None, "plain": None, "n": 0}
    results = []

    def sh(cmd):
        return subprocess.run([str(x) for x in cmd], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=160)

    def clip():
        """3 s, 640x360, 30 fps, BT.709-tagged, four flat known-colour bands, a 48 kHz tone."""
        if S["clip"] is None:
            out, ins = scratch / "clip.mp4", []
            for c in BANDS:
                ins += ["-f", "lavfi", "-i", "color=c=0x%s:s=160x360:r=30:d=3,format=rgb24" % c]
            p = sh([ff, "-v", "error", "-y", *ins, "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:d=3",
                    "-filter_complex", "".join("[%d:v]" % i for i in range(4)) + "hstack=inputs=4,"
                    "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]", "-map", "[v]", "-map", "4:a",
                    "-c:v", "libx264", "-crf", "0", "-preset", "veryfast", "-colorspace", "bt709",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-c:a", "aac", out])
            need(p.returncode == 0 and out.is_file(), "could not make the colour clip: %s" % p.stderr[-300:])
            S["clip"] = out
        return S["clip"]

    def work(transfer="bt709"):
        S["n"] += 1
        w = scratch / ("w%d" % S["n"]) / "work"
        w.mkdir(parents=True)
        (w / "cuts.json").write_bytes(json.dumps(CUTS).encode("utf-8"))
        probe = {"fps_flag": "-fps_mode", "audio_stream": 0,
                 "video": {"width": 640, "height": 360, "color_transfer": transfer}}
        (w / "probe.json").write_bytes(json.dumps(probe).encode("utf-8"))
        return w

    def grade(look, name):
        """videos/<reel>/grade.json + its take-1 cube, through reel-grade's own writer (bake_grade.write_grade)."""
        reel = scratch / "videos" / name
        doc, problems = bg.write_grade(reel, [{"range": [0.0, 3.0], "measured": {}, "correction": {}}],
                                       {"id": look, "strength": 1.0})
        need(doc and not problems, "write_grade refused the %s grade: %s" % (look, problems))
        return reel / "grade.json"

    def render(path, w, *args):
        rc, out, _ = run_render(path, w, clip(), "--master", *args)
        need(rc == 0, "render.py %s exited %s: %s" % (" ".join(map(str, args)), rc, out.strip()[-400:]))
        need("Traceback" not in out, "render.py printed a traceback")
        return w / "renders" / "master-100x.mp4"

    def centres(f):
        """The four bands' centre 20x20 means of a 360x640 frame, in 8-bit levels."""
        need(f.shape == (640, 360, 3), "the frame is %dx%d, not 360x640" % (f.shape[1], f.shape[0]))
        return np.array([f[310:330, 35 + 90 * i:55 + 90 * i].reshape(-1, 3).mean(0) for i in range(4)])

    def bands(path):
        return centres(np.round(read_frame(path, 1.0) * 255.0))

    def plain():
        """The ungraded master and its bands, checked against the planted colours."""
        if S["plain"] is None:
            m = render(RENDER, work())
            b = bands(m)
            planted = np.array([[int(c[i:i + 2], 16) for i in (0, 2, 4)] for c in BANDS])
            need(np.abs(b - planted).max() <= 4, "the ungraded master doesn't hold the known colours: %s" % b.round(1))
            S["plain"] = (m, b)
        return S["plain"]

    def mutant(old, new):
        S["n"] += 1
        s = RENDER.read_bytes().decode("utf-8")
        need(s.count(old) == 1, "mutant edit did not apply to render.py (%r)" % old[:40])
        p = scratch / ("mutant%d" % S["n"]) / "render.py"
        p.parent.mkdir(parents=True)
        p.write_bytes(s.replace(old, new).encode("utf-8"))
        return p

    def case_a():
        _, b0 = plain()
        d = float(np.abs(bands(render(RENDER, work(), "--grade", grade("none", "reel-a"))) - b0).max())
        print("    identity grade vs ungraded: worst band %.2f/255 (must be <= 2)" % d)
        need(d <= 2.0, "the identity grade moved a band by %.2f/255" % d)

    def tint_gap(path):
        """-> (graded master vs apply_grade.py on the ungraded master's frame, the look's own shift), 8-bit levels."""
        m0, b0 = plain()
        g = grade("warm", "reel-b")
        doc = json.loads(g.read_text(encoding="utf-8"))
        still, want_png = scratch / "plate.png", scratch / "plate-warm.png"
        p = sh([ff, "-v", "error", "-y", "-ss", "1.000", "-i", m0, "-frames:v", "1", "-update", "1", still])
        need(p.returncode == 0, "could not take the plate frame: %s" % p.stderr[-300:])
        p = sh([sys.executable, "-X", "utf8", "-I", "-B", PLUGIN / "skills/reel-grade/scripts/apply_grade.py",
                still, g.parent / doc["cube"], "-o", want_png])
        need(p.returncode == 0, "apply_grade.py exited %d: %s" % (p.returncode, (p.stdout + p.stderr)[-300:]))
        want = centres(np.round(read_frame(want_png) * 255.0))
        got = bands(render(path, work(), "--grade", g))
        return float(np.abs(got - want).max()), float(np.abs(want - b0).max())

    def case_b():
        d, shift = tint_gap(RENDER)
        print("    warm grade in the encode vs apply_grade.py on the same plate: worst band %.2f/255 (must be <= %d); "
              "the look itself moves a band by %.2f/255" % (d, TOL, shift))
        need(shift > TOL, "the warm look moves the bands only %.2f/255, too little to tell graded from ungraded" % shift)
        need(d <= TOL, "the graded master is %.2f/255 from apply_grade.py's output" % d)
        dm, _ = tint_gap(mutant('        vfilter += "," + grade_filter(a.grade)\n', "        pass\n"))
        print("    mutant --grade ignored: worst band %.2f/255 -> must exceed %d" % (dm, TOL))
        need(dm > TOL, "mutant (--grade ignored) was not caught: %.2f/255" % dm)

    def refusal(path):
        """None when render.py refuses a grade.json with the wrong cube_sha and renders nothing, else why not."""
        g = grade("warm", "reel-c")
        doc = json.loads(g.read_text(encoding="utf-8"))
        g.write_bytes(json.dumps(dict(doc, cube_sha="0" * 64)).encode("utf-8"))
        w = work()
        rc, out, _ = run_render(path, w, clip(), "--master", "--grade", g)
        made = [p.name for p in w.rglob("*") if p.suffix in (".mp4", ".txt", ".html")]
        print("    wrong cube_sha: exit %s, %r, files made %s" % (rc, out.strip()[-200:], made))
        if rc in (0, None) or made:
            return "it rendered (exit %s, files %s)" % (rc, made)
        if "Traceback" in out or len(out.strip().splitlines()) != 1 or "match" not in out:
            return "the refusal isn't one plain line: %r" % out[-300:]
        return None

    def case_c():
        why = refusal(RENDER)
        need(why is None, "a wrong cube_sha was not refused: %s" % why)
        print("    mutant sha check off:")
        why_m = refusal(mutant("    if hashlib.sha256(cube.read_bytes()).hexdigest() != sha:\n", "    if False:\n"))
        need(why_m is not None, "mutant (sha check off) was not caught: it still refused")

    def case_d():
        p = sh(["git", "-C", REPO, "show", "%s:%s" % (BEFORE, RENDER.relative_to(REPO).as_posix())])
        need(p.returncode == 0 and "def main" in p.stdout, "can't read render.py at %s: %s" % (BEFORE, p.stderr[-200:]))
        need("--grade" not in p.stdout, "render.py at %s already has --grade" % BEFORE)
        before = scratch / "before" / "render.py"
        before.parent.mkdir(parents=True)
        before.write_bytes(p.stdout.encode("utf-8"))
        g = grade("none", "reel-d")
        for transfer in ("bt709", "arib-std-b67"):
            w = work(transfer)
            caps = []
            for path, extra in ((before, ()), (RENDER, ()), (RENDER, ("--grade", g))):
                cap = Capture()
                rc, out, m = run_render(path, w, clip(), *extra, tiny=False, sub=cap)
                need(rc == "captured" and len(cap.encodes) == 2, "render.py %s didn't reach both encodes: %s %s"
                     % (" ".join(map(str, extra)), rc, out.strip()[-300:]))
                caps.append(cap.encodes)
            old, new, graded = caps
            old = [(cmd, frame_exact_graph(graph.decode("utf-8"), CUTS).encode("utf-8")) for cmd, graph in old]
            print("    %s: before %s, after %s (sha256 of the 2 commands + graphs)" % (
                transfer, hashlib.sha256(repr(old).encode("utf-8")).hexdigest()[:16],
                hashlib.sha256(repr(new).encode("utf-8")).hexdigest()[:16]))
            need(new == old, "%s: without --grade the command or graph differs from render.py at %s" % (transfer, BEFORE))
            lut = b"," + m.grade_filter(g).encode("utf-8")
            for (c0, g0), (c1, g1) in zip(new, graded):
                need(c1 == c0, "%s: --grade changed the ffmpeg command itself" % transfer)
                need(g1.count(b"lut3d") == 1 and g1.replace(lut + b"[v];", b"[v];") == g0,
                     "%s: --grade didn't add exactly one lut3d at the end of the conform" % transfer)

    def case_e():
        outputs = []
        src = scratch / "saved-look-face.mp4"
        p = sh([ff, "-v", "error", "-y", "-i", clip(), "-vf",
                "drawbox=x=210:y=48:w=220:h=80:color=0xc08060:t=fill", "-c:v", "libx264",
                "-threads", "2", "-crf", "0", "-preset", "veryfast", "-c:a", "copy", src])
        need(p.returncode == 0, "could not make saved-look face patch: " + p.stderr[-300:])
        saved_env = os.environ.get("EDITOR_SE_HOME")
        try:
            for look in ("warm", "mono"):
                home = scratch / ("home-" + look)
                (home / "styles").mkdir(parents=True)
                # Tool paths stay read-only; only the copied state and style live in scratch.
                state = json.loads((rt.state_dir() / "state.json").read_text(encoding="utf-8"))
                for component in state.get("components", {}).values():
                    component["bins"] = {k: str((rt.state_dir() / v).resolve())
                                         for k, v in component.get("bins", {}).items()}
                (home / "state.json").write_bytes(json.dumps(state).encode("utf-8"))
                (home / "styles/default.json").write_bytes(json.dumps({
                    "look": {"id": look, "strength": 1.0}}).encode("utf-8"))
                w = work()
                env = dict(os.environ, EDITOR_SE_HOME=str(home))
                # Saved styles apply per reel once picked (H-STY-1); a bare default.json is not a pick.
                p = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(PLUGIN / "skills/_shared/saved_style.py"),
                                    "pick", str(w.parent), "default"], env=env, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=60)
                need(p.returncode == 0, "could not pick the saved style for the reel: " + (p.stdout + p.stderr)[-300:])
                p = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B",
                                    str(PLUGIN / "skills/reel-grade/scripts/grade_match.py"),
                                    "--video", str(src), "--reel-dir", str(w.parent),
                                    "--take", "0-1", "--take", "1.5-2.5"], env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=160)
                need(p.returncode == 0, "saved look matching failed: " + (p.stdout + p.stderr)[-400:])
                need("Using your saved look: %s at 100 %%." % look.capitalize() in p.stdout,
                     "saved look was not explained: " + p.stdout)
                g = w.parent / "grade.json"
                matched = json.loads(g.read_text(encoding="utf-8"))
                need(matched["look"] == {"id": look, "strength": 1.0},
                     "the saved look was not baked")
                board = scratch / ("board-" + look)
                (board / "grade").mkdir(parents=True)
                p = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(PLUGIN / "skills/_shared/saved_style.py"),
                                    "pick", str(board), "default"], env=env, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=60)
                need(p.returncode == 0, "could not pick the saved style for the board reel: " + (p.stdout + p.stderr)[-300:])
                (board / "grade-selection.json").write_bytes(json.dumps({
                    "math_version": bg.gm.SPEC["version"], "correction": {}}).encode("utf-8"))
                (board / "grade/grade-config.json").write_bytes(json.dumps({
                    "duration": 3.0, "measured": matched["takes"][0]["measured"]}).encode("utf-8"))
                p = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B",
                                    str(PLUGIN / "skills/reel-grade/scripts/grade_from_selection.py"),
                                    "--reel-dir", str(board)], env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=160)
                need(p.returncode == 0, "Grade Board saved-look fallback failed: " + (p.stdout + p.stderr)[-400:])
                need(json.loads((board / "grade.json").read_text(encoding="utf-8"))["look"] == matched["look"],
                     "the Grade Board did not use the saved look")
                os.environ["EDITOR_SE_HOME"] = str(home)
                choice = scratch / ("precedence-" + look)
                choice.mkdir()
                selection = {"id": "mono", "strength": 0.4}
                (choice / "grade-selection.json").write_bytes(json.dumps({"look": selection}).encode("utf-8"))
                need(bg.resolve_look(choice) == selection, "the board choice did not beat the saved look")
                reel_look = {"id": "warm", "strength": 0.5}
                (choice / "grade.json").write_bytes(json.dumps({"look": reel_look}).encode("utf-8"))
                need(bg.resolve_look(choice) == reel_look, "the reel choice was not preserved")
                explicit = {"id": "none", "strength": 1.0}
                need(bg.resolve_look(choice, explicit=explicit) == explicit, "explicit none did not beat the reel")
                need(bg.resolve_look(choice, selection=selection) == selection, "a new Send did not beat the old grade")
                rc, out, _ = run_render(RENDER, w, src, "--master", "--grade", g)
                need(rc == 0, "saved-look render failed: " + out[-400:])
                outputs.append(bands(w / "renders/master-100x.mp4"))
                if saved_env is None:
                    os.environ.pop("EDITOR_SE_HOME", None)
                else:
                    os.environ["EDITOR_SE_HOME"] = saved_env
        finally:
            if saved_env is None:
                os.environ.pop("EDITOR_SE_HOME", None)
            else:
                os.environ["EDITOR_SE_HOME"] = saved_env
        gap = float(np.abs(outputs[0] - outputs[1]).max())
        need(gap > 20, "saved warm and mono masters are too similar: %.2f/255" % gap)
        need(float(np.ptp(outputs[1], axis=1).max()) <= 4, "the saved mono look did not remove colour")
        print("    saved warm vs mono: worst band difference %.2f/255" % gap)

    def mixed_work():
        w = work()
        src2 = scratch / "second.mp4"
        if not src2.exists():
            p = sh([ff, "-v", "error", "-y", "-i", clip(), "-vf", "hflip", "-c:v", "libx264",
                    "-threads", "2", "-crf", "0", "-preset", "veryfast", "-c:a", "copy", src2])
            need(p.returncode == 0, "could not make recording 2: " + p.stderr[-300:])
        c = json.loads(json.dumps(CUTS))
        c["takes"] = {"1": {"raw": str(clip()), "work": "work/take1"},
                      "2": {"raw": str(src2), "work": "work/take2"}}
        for n, s in enumerate(c["segments"], 1):
            s["take"] = n
            folder = w / ("take%d" % n)
            folder.mkdir()
            shutil.copyfile(w / "probe.json", folder / "probe.json")
        (w / "cuts.json").write_bytes(json.dumps(c).encode("utf-8"))
        sys.path.insert(0, str(PLUGIN / "skills/_shared/checks"))
        import footage_check
        for src in (clip(), src2):
            footage_check.add(w.parent, src, "aroll", "own", "own")
        return w

    def mixed_gap(path):
        w = mixed_work()
        doc, problems = bg.write_grade(w.parent, [
            {"range": [0, 1], "correction": {}}, {"range": [1.5, 2.5], "correction": {"sat": -1.0}}],
            {"id": "none"}, take_ids=["1", "2"])
        need(doc and not problems, "could not bake mixed grade")
        g = w.parent / "grade.json"
        master = render(path, w, "--grade", g)
        gaps = []
        for n, time in (("1", 0.5), ("2", 1.5)):
            source = clip() if n == "1" else scratch / "second.mp4"
            # Independent single-source render supplies the expected colour bands for this take's own cube.
            single = work()
            one = single.parent / "grade.json"
            # Cube paths in the one-take document are absolute, so its different reel folder is irrelevant.
            tk = dict(doc["takes"][n], cube=str(w.parent / doc["takes"][n]["cube"]))
            one.write_bytes(json.dumps(tk).encode("utf-8"))
            rc, out, _ = run_render(RENDER, single, source, "--master", "--grade", one)
            need(rc == 0, "expected single-source render failed: " + out[-300:])
            expected = bands(single / "renders/master-100x.mp4")
            got = centres(np.round(read_frame(master, time) * 255.0))
            gaps.append(float(np.abs(got - expected).max()))
        return max(gaps), w, g

    def case_f():
        gap, w, g = mixed_gap(RENDER)
        need(gap <= TOL, "mixed take differs from its own cube by %.2f/255" % gap)
        bad = json.loads(g.read_text(encoding="utf-8"))
        original = json.loads(json.dumps(bad))
        bad["takes"]["2"]["cube_sha"] = "0" * 64
        g.write_bytes(json.dumps(bad).encode("utf-8"))
        cap = Capture()
        rc, out, _ = run_render(RENDER, w, clip(), "--grade", g, sub=cap)
        need(rc == 2 and not cap.encodes and "match" in out, "bad per-take sha was not refused before encoding")
        for fallback in ({"1": original["takes"]["1"]},
                         {"1": original["takes"]["1"], "2": {"tune": {}}},
                         [original["takes"]["1"]]):
            g.write_bytes(json.dumps(dict(original, takes=fallback)).encode("utf-8"))
            cap = Capture()
            rc, out, m = run_render(RENDER, w, clip(), "--grade", g, sub=cap)
            need(rc == "captured" and len(cap.encodes) == 2, "mixed fallback failed: " + out[-300:])
            lut = m.grade_filter(g).encode("utf-8")
            need(all(graph.count(lut) == 2 for _, graph in cap.encodes), "a missing take cube did not use the top-level cube")
        dm, _, _ = mixed_gap(mutant("            take_grade = take_grades.get(n)\n",
                                    "            take_grade = None\n"))
        need(dm > TOL, "mutant using the top-level cube for all takes was not caught")
        print("    mixed own cubes: %.2f/255; top-level-only mutant: %.2f/255" % (gap, dm))

    def take2_bands(path):
        w = mixed_work()
        cuts = json.loads((w / "cuts.json").read_text(encoding="utf-8"))
        cuts["takes"] = {"2": cuts["takes"]["2"]}
        for segment in cuts["segments"]:
            segment["take"] = 2
        (w / "cuts.json").write_bytes(json.dumps(cuts).encode("utf-8"))
        g = grade("none", "reel-take2")
        rc, out, _ = run_render(path, w, clip(), "--master", "--scrub", "--grade", g)
        need(rc == 0, "take2 render failed: " + out[-400:])
        master = bands(w / "renders/master-100x.mp4")
        scrub = bands(w / "renders/scrub-100x.mp4")
        need(float(np.abs(master - scrub).max()) <= TOL, "take2 master and scrub disagree")
        return master

    def case_take2():
        _, first = plain()
        # Recording 2 is the horizontal reversal of the four planted colour bands.
        second = first[::-1]
        got = take2_bands(RENDER)
        gap = float(np.abs(got - second).max())
        need(gap <= TOL, "keep-only-take-2 master has the wrong recording: %.2f/255" % gap)
        old_rule = 'bool(cuts.get("takes"))'
        source = RENDER.read_text(encoding="utf-8")
        need(source.count(old_rule) == 3, "expected three take-path decisions for the mutant")
        broken = scratch / "old-take-rule" / "render.py"
        broken.parent.mkdir()
        broken.write_bytes(source.replace(old_rule, 'len(cuts.get("takes") or {}) > 1').encode("utf-8"))
        wrong = take2_bands(broken)
        wrong_gap = float(np.abs(wrong - second).max())
        need(float(np.abs(wrong - first).max()) <= TOL, "old-rule mutant didn't show take 1")
        need(wrong_gap > 20, "old > 1 mutant was not caught")
        print("    take2 colour gap: %.2f/255; old > 1 mutant: %.2f/255 (shows take 1)" % (gap, wrong_gap))

    cases = {"a": case_a, "b": case_b, "c": case_c, "d": case_d, "e": case_e, "f": case_f,
             "take2": case_take2}
    for name in want:
        try:
            cases[name]()
            results.append(True)
            print("✓ %s" % name, flush=True)
        except Exception as e:  # any crash in a case is that case's failure, the rest still run
            results.append(False)
            print("✗ %s: %s%s" % (name, "" if isinstance(e, Fail) else e.__class__.__name__ + ": ", e), flush=True)
    if a.keep:
        print("scratch kept: %s" % scratch)
    else:
        shutil.rmtree(scratch, ignore_errors=True)
    print("%d passed, %d failed" % (sum(results), len(results) - sum(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    with isolated_home():
        sys.exit(main())
