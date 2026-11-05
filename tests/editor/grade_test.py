"""G1.1 done-test: looks, bake, skin guard and take matching (reel-grade scripts), both directions.

  EDITOR_SE_HOME=<state> <editor python> -X utf8 -I tests/editor/grade_test.py --fixture <talking-head.mp4> \
      [--case a|b|c|f|looks|all] [--start 30] [--keep]

<state> is an installed editor state folder (ffmpeg, ffprobe, node); it is only read. --fixture (or GRADE_TEST_VIDEO)
is a talking-head recording with the face in the upper centre; it is only read: every case works on a 10 s excerpt
from --start, scaled to 640 px wide, in a scratch folder (a light job, H-LOCK-1; below 1 GB free RAM it refuses).
Each case also runs its mutant on a scratch COPY of the scripts and requires the mutant to fail, so the case is
shown to bite. Cases:
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

CLIP_S, CLIP_W = 10.0, 640
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
    names = ["a", "b", "c", "f", "looks"]
    ap = argparse.ArgumentParser(description="G1.1 grade done-test")
    ap.add_argument("--case", choices=names + ["all"], default="all")
    ap.add_argument("--fixture", default=os.environ.get("GRADE_TEST_VIDEO"), help="a talking-head recording (read only)")
    ap.add_argument("--start", type=float, default=30.0, help="where the 10 s excerpt starts in the fixture")
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
    if any(c in want for c in ("a", "b", "looks")) and not (a.fixture and Path(a.fixture).is_file()):
        print("✗ Cases a, b and looks need a talking-head video: pass --fixture <file.mp4> (or set GRADE_TEST_VIDEO)")
        return 1

    scratch = Path(tempfile.mkdtemp(prefix="g1_grade_"))
    env = dict(os.environ, HOME=str(scratch), USERPROFILE=str(scratch))
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

    def clip():
        if S["clip"] is None:
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

    cases = {"a": case_a, "b": case_b, "c": case_c, "f": case_f, "looks": case_looks}
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
