"""G1.1 done-test: looks, bake, skin guard and take matching (reel-grade scripts), both directions.

  EDITOR_SE_HOME=<state> <editor python> -X utf8 -I tests/editor/grade_test.py --fixture <talking-head.mp4> \
      [--case a|b|c|f|looks|cross|single|all] [--start 30] [--keep]

<state> is an installed editor state folder (ffmpeg, ffprobe, node); it is only read. --fixture (or GRADE_TEST_VIDEO)
is an optional talking-head recording with the face in the upper centre; it is only read: cases use a 4 s excerpt
from --start, scaled to 640 px wide, or a synthetic face patch when omitted. Cross always uses synthetic recordings.
These are light jobs (H-LOCK-1; below 1 GB free RAM the test refuses). Existing cases also run their mutants on
scratch COPIES of the scripts and require the mutants to fail. Cases:
  a      two takes in one file, the second pushed brighter and warmer: after grade_match.py the face differs by
         dE <= 3 and the skin hue by <= 5 deg; grade.json has the cut's cube + its sha256; one take = nothing to
         match. Mutant: matching off -> dE > 3.
  b      a planted grade that turns skin 25 deg is refused with a plain line. Mutant: guard off -> accepted.
  c      the identity (look None) through bake + apply moves known colour patches by exactly 0/255; a look at
         strength 0 stays within 2/255 and bakes the identity lattice. Mutant: one tint slider step in the identity
         path -> a patch moves.
  f      selftest_math.py: the page maths and the bake maths agree, py vs js < 1e-5. Mutant: one constant changed in
         grade_math.js. Pin: the sha256 of grade_math.json's non-text values (numbers, bools, null by key path) is
         fixed, so changing any number there fails this case; text fields stay free to change.
  looks  every look bakes, applies and passes the skin guard (Mono on brightness only), the looks sheet renders,
         and no file under reel-grade names a third-party cube or a private grade. Mutants: a planted look that
         swings skin -> caught; a planted cube file and name -> caught.
  cross  time-varying recordings (+0.3 stop and warmer) matched from their own kept ranges: face dE <= 3;
         reversed explicit file takes retain recording IDs and cubes. Mutants: argument-order IDs, sample offset lost.
  single legacy single-file takes keep the list schema, tune numbers and cube bytes.
Prints one "✓ <case>" / "✗ <case>: <why>" line per case, then "N passed, M failed". Exit 0 only when all pass.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
RG = PLUGIN / "skills/reel-grade"
sys.dont_write_bytecode = True   # importing the scripts below must not leave __pycache__ in the plugin
sys.path[:0] = [str(RG / "scripts"), str(PLUGIN / "skills/_shared")]
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

CLIP_S, CLIP_W = 4.0, 640
# the private grade's short name and the vendor words of the LUT packs it used, spelt so this file doesn't name them
PRIVATE = re.compile(r"(?i)\b" + "d" + "cg" + r"\b|" + "vib" + "rance|color grad" + "ing luts")
CUBE_NAME = re.compile(r"(?i)[A-Za-z0-9_-]\.cube\b")
# sha256 of grade_math.json's numbers/bools/nulls by key path (H-G1-9); a deliberate number change updates this
MATH_PIN = "8651fb2ae0d56a40c4e71b3ecd58279daa7fcb8d5bf62004b29928770123eea1"


class Fail(Exception):
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


def numbers_sha(obj):
    """sha256 of a parsed json's non-text values only: {json path: value}, strings dropped, sorted keys."""
    keep = {}

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + [k])
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + [i])
        elif not isinstance(o, str):
            keep[json.dumps(path)] = o
    walk(obj, [])
    return hashlib.sha256(json.dumps(keep, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj).encode("utf-8"))


def main():
    ensure_utf8_output()
    names = ["a", "b", "c", "f", "looks", "cross", "single"]
    ap = argparse.ArgumentParser(description="G1.1 grade done-test")
    ap.add_argument("--case", choices=names + ["all"], default="all")
    ap.add_argument("--fixture", default=os.environ.get("GRADE_TEST_VIDEO"), help="a talking-head recording (read only)")
    ap.add_argument("--start", type=float, default=30.0, help="where the 4 s excerpt starts in the fixture")
    ap.add_argument("--keep", action="store_true", help="keep the scratch folder")
    a = ap.parse_args()
    want = names if a.case == "all" else [a.case]
    gb = free_gb()
    if gb < 1.0:
        print("REFUSED: %.2f GB free RAM < 1.0 GB, so this test is unproven (RAM)" % gb)
        return 76
    try:
        ff, node = rt.tool("ffmpeg"), rt.tool("node")
        need(Path(ff).is_file() and Path(node).is_file(), "")
    except (KeyError, OSError, ValueError, Fail):
        print("✗ This test needs an installed editor state: set EDITOR_SE_HOME to one (ffmpeg, node)")
        return 1
    if a.fixture and not Path(a.fixture).is_file():
        print("✗ The fixture was not found: " + a.fixture)
        return 1

    scratch = Path(tempfile.mkdtemp(prefix="g1_grade_"))
    env = dict(os.environ, HOME=str(scratch), USERPROFILE=str(scratch))
    home = scratch / "state"
    home.mkdir()
    state = load(rt.state_dir() / "state.json")
    for component in state.get("components", {}).values():
        component["bins"] = {k: str((rt.state_dir() / v).resolve()) for k, v in component.get("bins", {}).items()}
    write_json(home / "state.json", state)
    env["EDITOR_SE_HOME"] = str(home)  # Client preferences must not colour the baseline or solver tests.
    import numpy as np
    import bake_grade as bg
    import skin_guard as sg
    from apply_grade import read_frame
    S = {"clip": None, "mut": 0}
    results = []

    def sh(cmd):
        return subprocess.run([str(x) for x in cmd], env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=160)

    def py(root, script, *args):
        """Run a reel-grade script from the repo (root=RG) or from a mutant copy."""
        return sh([sys.executable, "-X", "utf8", "-I", "-B", Path(root) / "scripts" / script, *args])

    def ok(p, what):
        need(p.returncode == 0, f"{what} exited {p.returncode}: {(p.stdout + p.stderr).strip()[-400:]}")
        need("Traceback" not in p.stdout + p.stderr, f"{what} printed a traceback")
        return p.stdout

    def mutant(edits=None, add=None):
        """A scratch copy of skills/reel-grade (+ _shared) with exact one-place edits; -> the copy's reel-grade."""
        S["mut"] += 1
        root = scratch / f"mutant{S['mut']}" / "skills"
        ign = shutil.ignore_patterns("__pycache__")
        shutil.copytree(RG, root / "reel-grade", ignore=ign)
        shutil.copytree(PLUGIN / "skills/_shared", root / "_shared", ignore=ign)
        for rel, (old, new) in (edits or {}).items():
            p = root / "reel-grade" / rel
            s = p.read_bytes().decode("utf-8")
            need(s.count(old) == 1, f"mutant edit did not apply to {rel} ({old[:40]!r})")
            p.write_bytes(s.replace(old, new).encode("utf-8"))
        for rel, text in (add or {}).items():
            (root / "reel-grade" / rel).write_bytes(text.encode("utf-8"))
        return root / "reel-grade"

    def synthetic():
        out = scratch / "synthetic.mp4"
        if not out.exists():
            # A face-like patch with a little tonal spread exercises the real mask and solver, without media.
            p = sh([ff, "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=0x303840:s=640x360:r=30:d=4,"
                        "drawbox=x=200:y=48:w=240:h=164:color=0xc08060:t=fill,"
                        "drawbox=x=200:y=48:w=100:h=164:color=0xb87858:t=fill,"
                        "drawbox=x=210:y=76:w=32:h=12:color=0x302820:t=fill,"
                        "drawbox=x=350:y=76:w=32:h=12:color=0x302820:t=fill",
                        "-an", "-c:v", "libx264", "-threads", "2", "-crf", "12", "-preset", "veryfast", out])
            need(p.returncode == 0 and out.is_file(), "could not make the light fixture: " + p.stderr[-300:])
        return out

    def clip():
        if S["clip"] is None:
            if not a.fixture:
                S["clip"] = synthetic()
                return S["clip"]
            out = scratch / "clip.mp4"
            # thread caps keep a 4K source's decode near 250 MB peak (all threads: ~640 MB), inside H-LOCK-1's 500 MB
            p = sh([ff, "-v", "error", "-y", "-threads", "4", "-ss", f"{a.start:.3f}", "-t", f"{CLIP_S:g}", "-i",
                    a.fixture, "-vf", f"scale={CLIP_W}:-2", "-an", "-c:v", "libx264", "-threads", "2", "-crf", "12",
                    "-preset", "veryfast", out])
            need(p.returncode == 0 and out.is_file(), f"could not cut the excerpt: {p.stderr[-300:]}")
            S["clip"] = out
        return S["clip"]

    def setup(root, video, name):
        reel = scratch / name
        out = ok(py(root, "make_grade.py", "--reel", name, "--video", video, "--reel-dir", reel), "make_grade.py")
        return reel, load(reel / "grade" / "grade-config.json"), out

    # ---- (a) take matching -------------------------------------------------------------------------------------
    def face_stats(video, take, cube):
        """The test's own measure: 5 frames (not the matcher's 6), graded through the take's cube, face mask on the
        graded frames -> (mean Lab, LCh of the median skin colour)."""
        t0, t1 = take
        imgs = [bg.through_cube(cube, read_frame(video, t0 + (j + 0.2) * (t1 - t0) / 5, CLIP_W)) for j in range(5)]
        px = sg.face_pixels(imgs)
        need(px is not None, f"no face found in take {t0:g}-{t1:g}")
        return sg.rgb_to_lab(px).mean(0), sg.lch(np.median(px, 0))

    def take_gap(video, reel):
        g = load(reel / "grade.json")
        (m1, c1), (m2, c2) = (face_stats(video, t["range"], reel / t["cube"]) for t in g["takes"])
        return float(np.linalg.norm(m1 - m2)), abs((c2[2] - c1[2] + 180.0) % 360.0 - 180.0)

    def case_a():
        pushed = scratch / "pushed.mp4"
        half = CLIP_S / 2
        p = sh([ff, "-v", "error", "-y", "-i", clip(), "-vf",
                f"colorchannelmixer=rr=1.27:gg=1.23:bb=1.13:enable='gte(t,{half:g})'",
                "-c:v", "libx264", "-crf", "12", "-preset", "veryfast", pushed])
        need(p.returncode == 0, f"could not push the second take: {p.stderr[-300:]}")
        takes = ["--take", f"0-{half:g}", "--take", f"{half:g}-{CLIP_S:g}"]
        one = ok(py(RG, "grade_match.py", "--video", pushed, "--reel-dir", scratch / "a1", "--take", f"0-{CLIP_S:g}"),
                 "grade_match.py (one take)")
        need("Nothing to match" in one and not (scratch / "a1" / "grade.json").exists(), f"one take: {one.strip()}")
        reel = scratch / "a"
        print("    " + ok(py(RG, "grade_match.py", "--video", pushed, "--reel-dir", reel, *takes), "grade_match.py")
              .strip().replace("\n", "\n    "))
        g = load(reel / "grade.json")
        need(len(g["takes"]) == 2 and g["cube"] == g["takes"][0]["cube"], "grade.json: 2 takes, the cut's cube = take 1's")
        for t in g["takes"]:
            need({"range", "measured", "correction", "cube", "cube_sha"} <= set(t), f"grade.json take keys {sorted(t)}")
            need(hashlib.sha256((reel / t["cube"]).read_bytes()).hexdigest() == t["cube_sha"], "a take's cube_sha is wrong")
        need(hashlib.sha256((reel / g["cube"]).read_bytes()).hexdigest() == g["cube_sha"], "top-level cube_sha is wrong")
        need(set(g["look"]) == {"id", "strength"}, f"grade.json look {g['look']}")
        de, dh = take_gap(pushed, reel)
        print(f"    matched: face dE {de:.2f} (<= 3), skin hue gap {dh:.2f} deg (<= 5)")
        need(de <= 3.0 and dh <= 5.0, f"after matching the takes still differ: dE {de:.2f}, hue {dh:.2f} deg")
        mut = mutant({"scripts/grade_match.py": ("params = solve(m[\"px\"], target, params, keys)",
                                                 "params = dict.fromkeys(SOLVE, 0.0)")})
        reel_m = scratch / "a_mut"
        pm = py(mut, "grade_match.py", "--video", pushed, "--reel-dir", reel_m, *takes)
        need(pm.returncode == 0, f"mutant (matching off) should still write grade.json: {pm.stdout.strip()[-300:]}")
        de_m, dh_m = take_gap(pushed, reel_m)
        print(f"    mutant matching off: face dE {de_m:.2f}, hue gap {dh_m:.2f} deg -> must exceed dE 3")
        need(de_m > 3.0, f"mutant (matching off) was not caught: dE {de_m:.2f} <= 3")

    # ---- (b) skin guard refuses a 25 deg skin turn -----------------------------------------------------------------
    def case_b():
        reel, cfg, _ = setup(RG, clip(), "b")
        face = reel / "grade" / cfg["face_frame"]
        spec = scratch / "planted.json"
        write_json(spec, {"correction": {"skin_hue": cfg["measured"]["skin_hue"], "skin_rot": 25.0}})
        cube = scratch / "planted.cube"
        ok(py(RG, "bake_grade.py", spec, "-o", cube), "bake_grade.py")
        p = py(RG, "skin_guard.py", "--face", face, cube)
        print("    " + p.stdout.strip().replace("\n", "\n    "))
        need(p.returncode == 1, f"the planted 25 deg skin turn was not refused (exit {p.returncode})")
        need("Refused: this grade turns skin" in p.stdout and "Traceback" not in p.stdout + p.stderr,
             "the refusal is not a plain line")
        mut = mutant({"scripts/skin_guard.py": ("    ok = not problems\n", "    ok = True\n")})
        pm = py(mut, "skin_guard.py", "--face", face, cube)
        print(f"    mutant guard off: exit {pm.returncode} -> must be accepted (0)")
        need(pm.returncode == 0, "mutant (guard off) still refused, so the test can't tell the guard from noise")

    # ---- (c) identity through bake + apply ----------------------------------------------------------------------
    PATCHES = ["000000", "ffffff", "808080", "c08060", "d02020", "20b040", "2040d0", "102030", "f0e0a0", "604880"]

    def patches_png():
        out = scratch / "patches.png"
        if not out.exists():
            ins = []
            for c in PATCHES:
                ins += ["-f", "lavfi", "-i", f"color=c=0x{c}:s=32x32:d=1,format=rgb24"]
            n = len(PATCHES)
            p = sh([ff, "-v", "error", "-y", *ins, "-filter_complex",
                    "".join(f"[{i}:v]" for i in range(n)) + f"hstack=inputs={n},format=rgb24", "-frames:v", "1", out])
            need(p.returncode == 0, f"could not make the colour patches: {p.stderr[-300:]}")
        return out

    def worst(root, spec, tag):
        src = patches_png()
        write_json(scratch / f"{tag}.json", spec)
        cube, out = scratch / f"{tag}.cube", scratch / f"{tag}.png"
        ok(py(root, "bake_grade.py", scratch / f"{tag}.json", "-o", cube), "bake_grade.py")
        ok(py(root, "apply_grade.py", src, cube, "-o", out), "apply_grade.py")
        a0, a1 = (np.round(read_frame(x) * 255.0) for x in (src, out))
        need(a0.shape == a1.shape, "apply changed the picture size")
        centres = a0[16, 16::32], a1[16, 16::32]
        need(np.abs(centres[0] - np.array([[int(c[i:i + 2], 16) for i in (0, 2, 4)] for c in PATCHES])).max() <= 1,
             "the patch frame doesn't hold the known colours")
        return float(np.abs(centres[0] - centres[1]).max()), cube

    def case_c():
        d, cube = worst(RG, {}, "identity")
        d0, cube0 = worst(RG, {"look": {"id": "warm", "strength": 0.0}}, "warm0")
        n, lat, _ = bg.parse_cube(cube)
        _, lat0, _ = bg.parse_cube(cube0)
        print(f"    look None: worst patch {d:g}/255 (must be 0) · Warm at strength 0: {d0:g}/255 (<= 2) · "
              f"lattices equal {np.abs(lat - lat0).max() == 0}")
        need(d == 0, f"the identity moved a known colour by {d:g}/255 (it must move none)")
        need(d0 <= 2, f"Warm at strength 0 moved a known colour by {d0:g}/255")
        need(np.abs(lat - lat0).max() == 0, "strength 0 is not the identity")
        # mutant: one slider step of tint (the step in grade_math.json's ranges) slipped into the identity path
        pre = "    c = gm.pre_pass(identity_lattice(size), pre)\n"
        mut = mutant({"scripts/bake_grade.py": (pre, pre + '    c = gm.apply_slot(c, c, {**gm.defaults(gm.SLOT), '
                                                      '"tint": gm.RANGES["tint"][2]})\n')})
        d1, _ = worst(mut, {}, "tint1")
        print(f"    mutant one-step tint ({bg.gm.RANGES['tint'][2]:g}) in the identity path: worst patch {d1:g}/255 "
              f"-> must be above 0")
        need(d1 > 0, f"mutant (one-step tint) was not caught: {d1:g}/255")

    # ---- (f) the page maths = the bake maths --------------------------------------------------------------------
    def case_f():
        out = ok(py(RG, "selftest_math.py"), "selftest_math.py")
        diff = re.search(r"max abs diff (\S+)", out)
        print(f"    selftest: max abs diff {diff.group(1) if diff else '?'} (tolerance 1e-05)")
        need("PASS" in out, f"selftest did not pass: {out.strip()[-200:]}")
        pin = numbers_sha(load(RG / "boards/grade-board/grade_math.json"))
        print(f"    grade_math.json numbers pin: {pin[:16]}... -> must equal {MATH_PIN[:16]}...")
        need(pin == MATH_PIN, f"a number in grade_math.json changed: sha256 {pin} != pinned {MATH_PIN}")
        mut = mutant({"boards/grade-board/grade_math.js": ("if (mx === r) h = 60 * ((g - b) / d);",
                                                           "if (mx === r) h = 61 * ((g - b) / d);")})
        pm = py(mut, "selftest_math.py")
        print(f"    mutant (one constant in grade_math.js): exit {pm.returncode} -> must fail")
        need(pm.returncode != 0 and "DIVERGED" in pm.stdout, "mutant (one constant changed) was not caught")

    # ---- every look bakes, applies, passes; nothing private ships -----------------------------------------------
    def scan(root):
        hits = [str(p.relative_to(root)) for p in root.rglob("*.cube")]
        for p in root.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                t = p.read_bytes().decode("utf-8", "replace")
                hits += [f"{p.relative_to(root)}: {m.group(0)}" for r in (PRIVATE, CUBE_NAME) for m in r.finditer(t)]
        return hits

    def looks_fail(root, reel, cfg):
        """-> the first reason the looks don't all bake, apply and pass, or None."""
        face = reel / "grade" / cfg["face_frame"]
        src = read_frame(face)
        ids = [lk["id"] for lk in cfg["looks"]]
        if root == RG and ids != list(bg.load_looks()):
            return f"config looks {ids} != looks.json"
        for lk in cfg["looks"]:
            if not lk["guard"]["ok"]:
                return f"make_grade's guard refused {lk['name']}"
            cube = reel / lk["cube"]
            out = scratch / f"{reel.name}-{lk['id']}.png"
            p = py(root, "apply_grade.py", face, cube, "-o", out)
            if p.returncode != 0:
                return f"apply_grade.py failed on {lk['name']}"
            if float(np.abs(read_frame(out) - src).mean()) * 255 < 1.0:
                return f"{lk['name']} changed nothing"
            g = py(root, "skin_guard.py", "--face", face, cube, *(["--neutral"] if lk["neutral"] else []))
            if g.returncode != 0:
                return f"skin_guard.py refused {lk['name']}: {g.stdout.strip()[-200:]}"
            print(f"    {lk['name']}: applied, guard {lk['guard']}")
        return None

    def case_looks():
        reel, cfg, _ = setup(RG, clip(), "looks")
        need([lk["name"] for lk in cfg["looks"]] == ["Natural", "Warm", "Punchy", "Soft matte", "Mono"],
             f"looks {[lk['name'] for lk in cfg['looks']]}")
        need([lk["id"] for lk in cfg["looks"] if lk["neutral"]] == ["mono"], "only Mono is neutral")
        need(cfg["correction"] == {k: v[3] for k, v in load(RG / "boards/grade-board/grade_math.json")["ranges"].items()
                                   if k in cfg["correction"]}, "the correction does not open at the identity")
        need({"black", "white", "skin_hue"} == set(cfg["suggested"]), "measured values are not saved as suggested")
        why = looks_fail(RG, reel, cfg)
        need(why is None, why)
        out = ok(py(RG, "looks_sheet.py", "--reel-dir", reel), "looks_sheet.py")
        sheet = read_frame(reel / "grade" / "looks-sheet.jpg")
        print(f"    {out.strip()}")
        need(sheet.shape[1] == 3 * 480 and "6 tiles" in out, f"looks sheet {sheet.shape}")
        hits = scan(RG)
        need(not hits, f"reel-grade names a cube file or a private grade: {hits[:5]}")
        # mutant 1: a planted look that swings skin must not pass
        lj = load(RG / "looks/looks.json")
        lj["looks"].append({"id": "planted", "name": "Planted", "stack": [{"temp": -1.0, "tint": 1.0, "sat": -0.5}]})
        mut = mutant(add={"looks/looks.json": json.dumps(lj)})
        reel_m, cfg_m, _ = setup(mut, clip(), "looks_mut")
        why_m = looks_fail(mut, reel_m, cfg_m)
        print(f"    mutant planted look: {why_m} -> must be caught")
        need(why_m is not None, "mutant (planted skin-swinging look) was not caught")
        # mutant 2: a planted vendor cube and a private name must be found
        mut2 = mutant(add={"looks/19_Pack.cube": "LUT_3D_SIZE 2\n", "looks/notes.txt": "the " + "D" + "CG preset\n"})
        hits_m = scan(mut2)
        print(f"    mutant planted cube + name: {len(hits_m)} hit(s) -> must be found")
        need(len(hits_m) >= 2, f"mutant (planted cube + name) was not caught: {hits_m}")

    def recordings():
        src = scratch / "ramp.mp4"
        if not src.exists():
            # Only cross-file fixtures vary over time; sampling the wrong range must change the measured mean.
            p = sh([ff, "-v", "error", "-y", "-i", synthetic(), "-vf", "eq=brightness='0.02*t':eval=frame",
                    "-an", "-c:v", "libx264", "-threads", "2", "-crf", "12", "-preset", "veryfast", src])
            need(p.returncode == 0, "could not make the brightness ramp: " + p.stderr[-300:])
        shifted = scratch / "warmer.mp4"
        if not shifted.exists():
            # Exposure is specified in stops, with a small warm cast on top of the +0.3 stop push.
            gain = 2 ** 0.3
            p = sh([ff, "-v", "error", "-y", "-i", src, "-vf",
                    f"colorchannelmixer=rr={gain * 1.02}:gg={gain}:bb={gain * 0.94}",
                    "-an", "-c:v", "libx264", "-threads", "2", "-crf", "12", "-preset", "veryfast", shifted])
            need(p.returncode == 0, "could not make the second recording: " + p.stderr[-300:])
        return src, shifted

    def sampled_mean(video, times):
        # Independent timestamps and the full face mask, rather than the matcher's capped pixel sample.
        px = sg.face_pixels([read_frame(video, t, CLIP_W) for t in times])
        need(px is not None, "no face in the cross-file mean check")
        return sg.rgb_to_lab(px).mean(0)

    def case_cross():
        src, shifted = recordings()
        reel = scratch / "cross"
        # Nonconsecutive IDs catch accidental conversion from recording IDs to positions.
        write_json(reel / "work/cuts.json", {"fps": 30, "speed": 1.0,
                   "takes": {"2": {"raw": str(src)}, "7": {"raw": str(shifted)}}, "segments": [
                       {"take": 2, "src_in_f": 0, "src_out_f": 30},
                       {"take": 7, "src_in_f": 0, "src_out_f": 30},
                       {"take": 2, "src_in_f": 60, "src_out_f": 90},
                       {"take": 7, "src_in_f": 60, "src_out_f": 90}]})
        out = ok(py(RG, "grade_match.py", "--from-cuts", reel), "cross-file grade_match.py")
        g = load(reel / "grade.json")
        need(set(g["takes"]) == {"2", "7"}, "cross-file grade lost the recording IDs")
        need(g["cube"] == g["takes"]["2"]["cube"], "top-level cube is not the reference recording's")
        for n, video in (("2", src), ("7", shifted)):
            tk = g["takes"][n]
            need(Path(tk["raw"]) == video and tk["ranges"] == [[0, 1], [2, 3]], "wrong file or kept ranges")
            need(tk["tune"] == tk["correction"], "the take's tune was not recorded")
            need(bg.sha256(reel / tk["cube"]) == tk["cube_sha"], "wrong per-take cube hash")
        # Six midpoint samples across [0, 1] and [2, 3], calculated independently of sample_times().
        expected = sampled_mean(src, [1 / 6, 0.5, 5 / 6, 13 / 6, 2.5, 17 / 6])
        mean_gap = float(np.linalg.norm(np.array(g["takes"]["2"]["measured"]["lab_mean"]) - expected))
        need(mean_gap <= 0.25, f"measured skin mean is not from the kept ranges: dE {mean_gap:.2f}")
        first = face_stats(src, (0, 1), reel / g["takes"]["2"]["cube"])[0]
        before = face_stats(shifted, (0, 1), reel / g["takes"]["2"]["cube"])[0]
        after = face_stats(shifted, (0, 1), reel / g["takes"]["7"]["cube"])[0]
        de0, de = float(np.linalg.norm(first - before)), float(np.linalg.norm(first - after))
        need(de0 > 3.0 and de <= 3.0 and de < de0, f"cross-file face dE {de0:.2f} -> {de:.2f} (must drop to <= 3)")
        explicit = scratch / "cross-explicit"
        ok(py(RG, "grade_match.py", "--reel-dir", explicit, "--take", f"{src}::0-1",
              "--take", f"{shifted}::0-1"), "explicit cross-file takes")
        eg = load(explicit / "grade.json")
        need(set(eg["takes"]) == {"1", "2"}, "explicit file takes were not written by ID")
        # With cuts metadata, paths (including reel-relative paths and Windows case) identify recordings.
        write_json(explicit / "work/cuts.json", {"takes": {
            "2": {"raw": os.path.relpath(src, explicit)}, "7": {"raw": str(shifted)}}})
        ok(py(RG, "grade_match.py", "--reel-dir", explicit, "--take", f"{src}::2-3",
              "--take", f"{shifted}::2-3"), "explicit recording IDs")
        forward = load(explicit / "grade.json")
        need(set(forward["takes"]) == {"2", "7"}, "explicit takes lost the cuts recording IDs")
        expected_explicit = sampled_mean(src, [2 + (j + 0.5) / 6 for j in range(6)])
        need(np.linalg.norm(np.array(forward["takes"]["2"]["measured"]["lab_mean"]) - expected_explicit) <= 0.25,
             "explicit take was not measured from its own time range")

        def reversed_takes(root):
            reverse = scratch / ("cross-reverse-" + root.parent.parent.name)
            write_json(reverse / "work/cuts.json", load(explicit / "work/cuts.json"))
            alias = src.parent / "unused" / ".." / src.name
            if os.name == "nt":
                alias = Path(str(alias).swapcase())
            p = py(root, "grade_match.py", "--reel-dir", reverse, "--ref", "2",
                   "--take", f"{shifted}::2-3", "--take", f"{alias}::2-3")
            ok(p, "reversed explicit takes")
            return reverse, load(reverse / "grade.json")

        def own_cubes(reverse, doc):
            if set(doc["takes"]) != {"2", "7"}:
                return False
            for n in ("2", "7"):
                tk, want = doc["takes"][n], forward["takes"][n]
                if tk["correction"] != want["correction"] or not np.array_equal(
                        bg.parse_cube(reverse / tk["cube"])[1], bg.parse_cube(explicit / want["cube"])[1]):
                    return False
            return doc["cube"] == doc["takes"]["2"]["cube"]

        reverse, rg = reversed_takes(RG)
        need(own_cubes(reverse, rg), "reversed explicit takes put a cube on the wrong recording")
        # A file outside the reel must be refused before any grade is written, in one plain line.
        unknown = scratch / "cross-unknown"
        write_json(unknown / "work/cuts.json", load(explicit / "work/cuts.json"))
        p = py(RG, "grade_match.py", "--reel-dir", unknown, "--take", f"{synthetic()}::0-1",
               "--take", f"{shifted}::0-1")
        need(p.returncode == 1 and len(p.stdout.strip().splitlines()) == 1 and not p.stderr.strip()
             and "not part of this reel" in p.stdout and not (unknown / "grade.json").exists(),
             "unknown recording was not refused with one plain line")
        # Two ranges from one recording cannot share its single cube in a mixed reel.
        duplicate = scratch / "cross-duplicate"
        write_json(duplicate / "work/cuts.json", load(explicit / "work/cuts.json"))
        alias = src.parent / "unused" / ".." / src.name
        if os.name == "nt":
            alias = Path(str(alias).swapcase())
        refusal = ("Two of these takes come from the same recording; match takes from different recordings, "
                   "or match inside that recording on its own.")
        for existing in (False, True):
            if existing:
                (duplicate / "grade").mkdir()
                (duplicate / "grade/keep.cube").write_bytes(b"keep this cube\n")
                (duplicate / "grade.json").write_bytes(b'{"keep": "this grade"}\n')
            before = {p.relative_to(duplicate): p.read_bytes() for p in duplicate.rglob("*") if p.is_file()}
            p = py(RG, "grade_match.py", "--reel-dir", duplicate, "--take", f"{src}::0-1",
                   "--take", f"{alias}::2-3", "--take", f"{shifted}::0-1")
            need(p.returncode == 1 and p.stdout.splitlines() == [refusal] and not p.stderr.strip(),
                 "duplicate recording was not refused with one plain line")
            after = {p.relative_to(duplicate): p.read_bytes() for p in duplicate.rglob("*") if p.is_file()}
            need(after == before, "duplicate recording refusal wrote or changed files")
        mut = mutant({"scripts/grade_match.py": ("take_id = recording_ids[key]", "take_id = str(i)")})
        reverse_m, mg = reversed_takes(mut)
        need(not own_cubes(reverse_m, mg), "argument-order ID mutant was not caught")
        offset_mut = mutant({"scripts/grade_match.py": ("yield t0 + offset", "yield offset")})
        bad = scratch / "cross-offset"
        write_json(bad / "work/cuts.json", load(reel / "work/cuts.json"))
        ok(py(offset_mut, "grade_match.py", "--from-cuts", bad), "sample-offset mutant")
        bad_mean = load(bad / "grade.json")["takes"]["2"]["measured"]["lab_mean"]
        bad_gap = float(np.linalg.norm(np.array(bad_mean) - expected))
        need(bad_gap > 0.25, f"frame-sample-offset mutant was not caught: dE {bad_gap:.2f}")
        print(f"    own recording per take: face dE {de0:.2f} -> {de:.2f} (<= 3)")
        print(f"    kept-range mean dE {mean_gap:.2f}; sample-offset mutant dE {bad_gap:.2f}; argument-order mutant caught")

    def case_single():
        src = clip()
        old, explicit = scratch / "single-old", scratch / "single-explicit"
        ok(py(RG, "grade_match.py", "--video", src, "--reel-dir", old,
              "--take", "0-1", "--take", "2-3"), "legacy single-file takes")
        ok(py(RG, "grade_match.py", "--reel-dir", explicit,
              "--take", f"{src}::0-1", "--take", f"{src}::2-3"), "explicit same-file takes")
        lg, eg = load(old / "grade.json"), load(explicit / "grade.json")
        need(isinstance(lg["takes"], list), "legacy single-file grade schema changed")
        p = sh(["git", "-C", PLUGIN.parents[1], "show", "a77161973eb25cb630ccad1235a7c1b399adc521:" +
                (RG / "scripts/grade_match.py").relative_to(PLUGIN.parents[1]).as_posix()])
        need(p.returncode == 0 and "def main" in p.stdout, "could not read baseline grade_match.py: " + p.stderr[-200:])
        baseline = mutant(add={"scripts/grade_match.py": p.stdout})
        before = scratch / "single-before"
        ok(py(baseline, "grade_match.py", "--video", src, "--reel-dir", before,
              "--take", "0-1", "--take", "2-3"), "baseline single-file takes")
        need(lg == load(before / "grade.json"), "legacy single-file grade.json differs from the fixed G1-b baseline")
        for i, tk in enumerate(lg["takes"], 1):
            et = eg["takes"][str(i)]
            need(tk["correction"] == et["correction"] and tk["cube_sha"] == et["cube_sha"],
                 "legacy single-file tune or cube changed")
        print("    legacy grade.json equals fixed G1-b baseline; tune and cube bytes equal explicit-file results")

    cases = {"a": case_a, "b": case_b, "c": case_c, "f": case_f, "looks": case_looks,
             "cross": case_cross, "single": case_single}
    for name in want:
        try:
            cases[name]()
            results.append(True)
            print(f"✓ {name}", flush=True)
        except Exception as e:  # any crash in a case is that case's failure, the rest still run
            results.append(False)
            print(f"✗ {name}: {e.__class__.__name__ + ': ' if not isinstance(e, Fail) else ''}{e}", flush=True)
    if not a.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    else:
        print(f"scratch kept: {scratch}")
    print(f"{sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
