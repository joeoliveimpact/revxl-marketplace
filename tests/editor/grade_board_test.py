"""G1.2 done-test: the Grade Board inside the real hub's Grade tab, through the real board server, both directions.

  EDITOR_SE_HOME=<state> <editor python> -X utf8 -I tests/editor/grade_board_test.py --fixture <talking-head.mp4> \
      [--case send_loading|early_send|failed_init|identity|send|reload|roundtrip|all] [--start 30]
  python -X utf8 -I tests/editor/grade_board_test.py --data-only  # static Send + mutant, no installed tools needed

<state> is an installed editor state folder (node, chrome-headless-shell, puppeteer-core, ffmpeg); it is only read.
--fixture (or GRADE_TEST_VIDEO) is a talking-head recording, only read: each run cuts one 10 s excerpt at 640 px wide
into a scratch folder (a light job) and every case builds its own reel from it with make_grade.py, so any case runs
alone. Every browser is a NEW headless Chrome (fresh profile, so nothing comes from its storage) driven by
boards_click.js under heavy_lock.py (exit 75/76 = unproven). The board is always opened from the real hub's Grade tab
(a same-origin iframe); failed-init cases open it directly to test a missing reel or config. Cases:
  send_loading  static Send starts disabled with Loading...; an enabled-button mutant is rejected (no browser).
  early_send    without waiting for boot, Send is disabled or already wired; an enabled click writes the Send.
  failed_init   missing reel/config gives a plain error, no Loading cue, Send disabled; cleanup mutants fail.
  identity   the board opens at the identity: white slider 1.000, the correction equals grade_math.json's defaults,
             look None; Suggested fix then sets make_grade's measured values; every request stays on the board server.
             Mutant: a board copy that opens at the measured values -> the identity check fails.
  send       boards.json lets grade-board write only grade-selection.json and every Send name in hooks/mod/logic.ts is
             in some board's writes; a look + strength + Send lands grade-selection.json in the reel folder and no
             selection.json (a __save of selection.json is refused, 403). At 1024x768 in the hub and at a 799 px
             board width the confirmation is fully visible and inside the header.
  reload     a look, strength and the Suggested fix come back in a new browser from grade-board.state.json. Without
             that file the board opens at the identity again.
  roundtrip  known colour patches on the board: look + strength + Suggested fix + a fine-tune move, Send, then
             grade_from_selection.py bakes the cube and applies it (only with --yes) to the same patches; the applied
             pixels match the board's within 3/255, and the board's own float maths (GM.prePass + slotsOf) on the
             patches' nearest lattice nodes match the cube there within 1e-4 (the 8-bit check cannot see a 1-step
             tint). Mutants: the bake ignores the strength -> the pixel match fails; the bake or the board runs one
             tint step (0.01) the other does not -> the float match fails. A video applied with --yes records
             extra_generations 1; a changed cube is refused.
Prints one "✓ <case>" / "✗ <case>: <why>" line per case, then "N passed, M failed". Exit 0 only when all pass.
"""
import argparse, http.client, json, os, re, shutil, socket, subprocess, sys, tempfile, threading
from pathlib import Path
from html.parser import HTMLParser

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugins/editor-superengine"
RG = PLUGIN / "skills/reel-grade"
DOCTOR = PLUGIN / "skills/editor-doctor/scripts"
sys.dont_write_bytecode = True   # importing check_deps must not leave __pycache__ in the plugin
sys.path[:0] = [str(PLUGIN / "skills/_shared"), str(DOCTOR), str(RG / "scripts")]
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)

SERVER = DOCTOR / "board_server.py"
CLICK = HERE / "boards_click.js"
HEAVY = r"C:/Workspaces/Content Studio/output/scripts/heavy_lock.py"
BOARD_HTML = RG / "boards/grade-board/index.html"
CLIP_S, CLIP_W = 10.0, 640
SPEC = json.loads((RG / "boards/grade-board/grade_math.json").read_text(encoding="utf-8"))
TUNE = [k for k in SPEC["slot"]["params"] if k != "mix"]
IDENTITY = {k: SPEC["ranges"][k][3] for k in SPEC["pre_pass"]["params"] + TUNE}
# per channel, of 255: the page and ffmpeg each round to 8 bits (1), and the bake's 33^3 lattice interpolates across
# a clip where the page clips exactly (measured 3 on the highlight patch after the Suggested fix + Punchy)
TOL = 3
# 3 x 2 flat patches, 120 px each: skin, mid grey, shadow, highlight, blue, green
PATCHES = [(205, 150, 125), (128, 128, 128), (40, 40, 48), (235, 230, 220), (40, 80, 190), (60, 150, 70)]
PTS = [((i % 3 + 0.5) / 3, (i // 3 + 0.5) / 2) for i in range(6)]
MUTANT_OPEN = ("GM.defaults(PRE.concat(TUNE))", "Object.assign(GM.defaults(PRE.concat(TUNE)),C.suggested)")
MUTANT_BAKE = ('"strength": look.get("strength", 1.0)}', '"strength": 1.0}')
# the float check: each patch's nearest node of the 33^3 lattice, so the cube is read with no interpolation and the
# only gap left is the cube's 6 written decimals; one tint step (0.01) moves green by ~8e-4, far over FTOL
LAT = [[round(v / 255 * 32) / 32 for v in c] for c in PATCHES]
FTOL = 1e-4
STEP = SPEC["ranges"]["tint"][2]
MUTANT_TINT_BAKE = ('list(spec.get("stack") or [])', 'list(spec.get("stack") or []) + [{"tint": %r}]' % STEP)
MUTANT_TINT_BOARD = ("const t={}; TUNE.forEach(k=>{ t[k]=state.correction[k]; });",
                     "const t={}; TUNE.forEach(k=>{ t[k]=state.correction[k]; }); t.tint+=%r;" % STEP)
FLOAT = ("(() => { const s = GB.st(); return JSON.stringify(%s.map(c => { let x = GM.prePass(c, s.correction);"
         " slotsOf(s).forEach(t => { x = GM.slotTune(x, t); }); return x; })); })()" % json.dumps(LAT))
READ = ("JSON.stringify({corr: GB.st().correction, look: GB.st().look, frame: GB.S.frame, suggested: GB.C.suggested,"
        " white: document.querySelector('#corr input[data-k=white]').value,"
        " whiteText: document.querySelector('#corr input[data-k=white]').parentNode.querySelector('.v').textContent,"
        " on: [...document.querySelectorAll('#rail figure.on')].map(f => f.dataset.look),"
        " strength: (document.getElementById('strength') || {}).value || null})")
PIXELS = ("(() => { GB.draw(); const cv = document.getElementById('gl'), g = cv.getContext('webgl2'), W = cv.width,"
          " H = cv.height, px = new Uint8Array(4); return JSON.stringify(%s.map(([u, v]) => {"
          " g.readPixels(Math.floor(u * W), Math.floor((1 - v) * H), 1, 1, g.RGBA, g.UNSIGNED_BYTE, px);"
          " return [px[0], px[1], px[2]]; })); })()" % json.dumps(PTS))


class Fail(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Fail(why)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_tools():
    """sound_board_test.py's: the editor's own node, chrome-headless-shell, ffmpeg and puppeteer-core."""
    found, missing = {}, []
    for name in ("node", "chrome", "ffmpeg"):
        try:
            found[name] = rt.tool(name)
            if not Path(found[name]).is_file():
                missing.append(name)
        except (KeyError, OSError, ValueError):
            missing.append(name)
    pup = rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
    if not pup.is_file():
        missing.append("puppeteer-core")
    found["pup"] = str(pup)
    return found, missing


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, indent=1).encode("utf-8"))


def identity_problems(r):
    """What is not the identity in one board read (empty = it opened at the identity)."""
    out = []
    if r["whiteText"] != "1.000":
        out.append(f"white slider shows {r['whiteText']}")
    if r["corr"] != IDENTITY:
        out.append(f"correction {r['corr']} is not grade_math.json's defaults")
    if r["look"]["id"] != "none" or r["on"] != ["none"]:
        out.append(f"look {r['look']}, highlighted {r['on']}")
    return out


def check_send_loading(html):
    class SendParser(HTMLParser):
        attrs = None
        inside = False
        cue = False

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "button" and attrs.get("id") == "send":
                self.attrs, self.inside = attrs, True
            if self.inside and tag == "small" and "data-loading" in attrs:
                self.cue = True

        def handle_endtag(self, tag):
            if tag == "button":
                self.inside = False

        def handle_data(self, data):
            if self.inside:
                self.text.append(data)

    parser = SendParser()
    parser.text = []
    parser.feed(html)
    need(parser.attrs is not None and "disabled" in parser.attrs, "Send is live during load")
    need(parser.cue and "Loading..." in "".join(parser.text), "Send has no loading cue")


def send_loading_case():
    html = BOARD_HTML.read_text(encoding="utf-8")
    check_send_loading(html)
    button = re.search(r'<button\b[^>]*\bid="send"[^>]*>', html).group()
    need(button.count(" disabled") == 1, "loading mutant anchor differs")
    try:
        check_send_loading(html.replace(button, button.replace(" disabled", "", 1), 1))
    except Fail as e:
        need(str(e) == "Send is live during load", f"wrong mutant rejection: {e}")
    else:
        raise Fail("loading mutant survived: Send enabled before init")


def main():
    ensure_utf8_output()
    names = ["send_loading", "early_send", "failed_init", "identity", "send", "reload", "roundtrip"]
    ap = argparse.ArgumentParser(description="Grade Board done-test")
    ap.add_argument("--case", choices=names + ["all"], default="all")
    ap.add_argument("--data-only", action="store_true", help="run the static Send check and its mutant only")
    ap.add_argument("--fixture", default=os.environ.get("GRADE_TEST_VIDEO"), help="a talking-head recording (read only)")
    ap.add_argument("--start", type=float, default=30.0, help="where the 10 s excerpt starts in the fixture")
    a = ap.parse_args()
    if a.data_only or a.case == "send_loading":
        send_loading_case()
        print("Send loading static check + enabled-button mutant passed")
        return 0
    import numpy as np
    import bake_grade as bg  # through_cube: the cube read the way the GPU reads it
    want = names if a.case == "all" else [a.case]
    tools, missing = find_tools()
    if missing:
        print(f"✗ This test needs an installed editor state: set EDITOR_SE_HOME to one (missing: {', '.join(missing)})")
        return 1
    if not (a.fixture and Path(a.fixture).is_file()):
        print("✗ This test needs a talking-head video: pass --fixture <file.mp4> (or set GRADE_TEST_VIDEO)")
        return 1
    scratch = Path(tempfile.mkdtemp(prefix="g1_grade_board_"))
    if shutil.disk_usage(scratch).free < 10 * 2 ** 30:
        print("REFUSED: under 10 GB free disk, so this test is unproven (disk)")
        shutil.rmtree(scratch, ignore_errors=True)
        return 76
    env = dict(os.environ, HOME=str(scratch), USERPROFILE=str(scratch))
    ws = scratch / "ws"
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": free_port()}}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    videos = ws / rt.read_config(ws)["paths"]["videos"]
    videos.mkdir(parents=True, exist_ok=True)
    S = {"server": None, "port": None, "browsers": 0, "clip": None, "mut": 0}
    procs, results = [], []
    from PIL import Image

    def sh(cmd, timeout=160):
        return subprocess.run([str(x) for x in cmd], env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)

    def py(root, script, *args):
        """A reel-grade script from the repo (root=RG) or from a mutant copy."""
        return sh([sys.executable, "-X", "utf8", "-I", "-B", Path(root) / "scripts" / script, *args])

    def ok(p, what):
        need(p.returncode == 0, f"{what} exited {p.returncode}: {(p.stdout + p.stderr).strip()[-400:]}")
        need("Traceback" not in p.stdout + p.stderr, f"{what} printed a traceback")
        return p.stdout

    def case(name, fn):
        try:
            fn()
            results.append(True)
            print(f"✓ {name}", flush=True)
        except Exception as e:  # any crash in a case is that case's failure, the rest still run
            results.append(False)
            print(f"✗ {name}: {e.__class__.__name__ + ': ' if not isinstance(e, Fail) else ''}{e}", flush=True)

    def server():
        if S["server"]:
            return S["port"]
        p = subprocess.Popen([sys.executable, "-X", "utf8", "-I", "-B", str(SERVER), "--root", str(ws)], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        procs.append(p)
        t = threading.Timer(20, p.kill)  # a hung start fails the case instead of blocking the test
        t.start()
        line = p.stdout.readline().strip()
        t.cancel()
        need(line.startswith("Editor boards: http://127.0.0.1:") and line.endswith("/"), f"server said {line!r}")
        S["server"], S["port"] = p, int(line.rsplit(":", 1)[1].rstrip("/"))
        return S["port"]

    def clip():
        if S["clip"] is None:
            out = scratch / "clip.mp4"
            # thread caps keep a 4K source's decode light (grade_test.py's excerpt)
            p = sh([tools["ffmpeg"], "-v", "error", "-y", "-threads", "4", "-ss", f"{a.start:.3f}", "-t", f"{CLIP_S:g}",
                    "-i", a.fixture, "-vf", f"scale={CLIP_W}:-2", "-an", "-c:v", "libx264", "-threads", "2", "-crf", "12",
                    "-preset", "veryfast", out])
            need(p.returncode == 0 and out.is_file(), f"could not cut the excerpt: {p.stderr[-300:]}")
            S["clip"] = out
        return S["clip"]

    def reel(name):
        """A reel folder with the excerpt under raw/ and the grade set up by make_grade.py (at the identity)."""
        d = videos / name
        (d / "raw").mkdir(parents=True)
        shutil.copyfile(clip(), d / "raw/clip.mp4")
        ok(py(RG, "make_grade.py", "--reel", name, "--video", d / "raw/clip.mp4", "--reel-dir", d), "make_grade.py")
        return d, load(d / "grade/grade-config.json")

    def browse(reel_name, actions, label, ready=True, direct_path=None, viewport=None):
        """A NEW headless Chrome (fresh profile) under heavy_lock opens the real hub, the Grade tab, then runs actions."""
        port = server()
        for name in ("board_sync.py", "hub_rows.py"):
            p = sh([sys.executable, "-X", "utf8", "-I", "-B", DOCTOR / name, "--root", ws])
            ok(p, "hub setup " + name)
        S["browsers"] += 1
        job = scratch / "jobs" / f"{S['browsers']:02d}-{label}.json"
        tab = [{"do": "goto", "path": f"/editor/hub/?reel={reel_name}", "waitFn": "window.Hub && Hub.ready"},
               {"do": "click", "sel": "#tab-grade-board"},
               {"do": "frame", "sel": ".frame iframe", **({"waitFn": "window.GB && GB.ready"} if ready else {"wait": "#send"})}]
        if direct_path is not None:
            tab = [{"do": "goto", "path": direct_path, "wait": "#send"}]
        write_json(job, {"base": f"http://127.0.0.1:{port}", "userDataDir": str(scratch / "profiles" / job.stem),
                         "viewport": viewport,
                         "actions": tab + actions})
        p = sh([sys.executable, "-X", "utf8", "-I", HEAVY, "--wait", "60", "--min-gb", "3", "--",
                tools["node"], CLICK, tools["pup"], tools["chrome"], job], timeout=150)
        if p.returncode in (75, 76):
            raise Fail(f"UNPROVEN ({'RAM' if p.returncode == 76 else 'lock wait'}): heavy_lock exit {p.returncode}")
        try:
            out = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            out = {}
        need(p.returncode == 0 and out, f"browser: {out.get('error') or (p.stdout + p.stderr).strip()[-500:]}")
        need(not out["errors"], f"page errors {out['errors']}")
        base = f"http://127.0.0.1:{port}/"
        outside = [u for u in out["requests"] if not u.startswith((base, "data:", "blob:", "about:"))]
        need(not outside, f"the page fetched from outside the board server: {outside[:3]}")
        return out

    def reads(out):
        return [json.loads(r) for r in out["reads"]]

    def post(reel_name, name):
        port = server()
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("POST", f"/videos/{reel_name}/__save?board=grade-board&name={name}", body=b'{"v": 1}',
                  headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"})
        status = c.getresponse().status
        c.close()
        return status

    def drop_state(d):
        for f in ("grade-board.state.json", "grade-board.state.json.prev"):
            (d / f).unlink(missing_ok=True)

    # ---- cases ----
    def c_early_send():
        d, _ = reel("early-send-reel")
        out = browse("early-send-reel", [
            {"do": "eval", "js": "document.querySelector('#send').disabled || typeof document.querySelector('#send').onclick === 'function'"},
            {"do": "waitFn", "js": "!document.querySelector('#send').disabled"},
            {"do": "click", "sel": "#send"},
            {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"}], "early-send", ready=False)
        need(out["reads"] == [True], "Send was enabled before its handler was attached")
        need((d / "grade-selection.json").is_file(), "early Send did not write grade-selection.json")

    def c_failed_init():
        (videos / "no-grade-reel").mkdir()
        for path, message in (("/editor/grade-board/", "Ask Claude to open the Grade Board for this reel."),
                              ("/editor/grade-board/?reel=no-grade-reel", "No grade is set up for this reel yet.")):
            def check_init():
                out = browse("no-grade-reel", [
                    {"do": "waitFn", "js": "!!document.querySelector('body > pre')"},
                    {"do": "eval", "js": "JSON.stringify({error: document.querySelector('body > pre').textContent, "
                     "disabled: document.querySelector('#send').disabled, loading: !!document.querySelector('#send [data-loading]')})"}],
                    "failed-init", ready=False, direct_path=path)
                r = reads(out)[0]
                need("Grade Board could not start:" in r["error"] and message in r["error"], f"wrong boot error: {r}")
                need(r["disabled"], "failed init: Send is enabled")
                need(not r["loading"], "failed init: loading cue survived")
            check_init()
            live = ws / "editor/grade-board/index.html"
            original = live.read_bytes()
            html = original.decode("utf-8")
            cleanup = "$('#send').querySelector('[data-loading]')?.remove();"
            need(html.count(cleanup) == 1, "failed-init mutant anchor differs")
            live.write_bytes(html.replace(cleanup, "", 1).encode("utf-8"))
            try:
                try:
                    check_init()
                except Fail as e:
                    need(str(e) == "failed init: loading cue survived", f"wrong mutant rejection: {e}")
                else:
                    raise Fail("failed-init loading cue mutant survived")
            finally:
                live.write_bytes(original)

    def c_identity():
        html = BOARD_HTML.read_text(encoding="utf-8")
        need(not re.search(r"localStorage|https?://|fonts\.g", html), "the board names localStorage or a web address")
        d, cfg = reel("identity-reel")
        steps = [{"do": "eval", "js": READ}, {"do": "click", "sel": "#suggest"}, {"do": "eval", "js": READ}]
        r0, r1 = reads(browse("identity-reel", steps, "identity"))
        bad = identity_problems(r0)
        need(not bad, "the board did not open at the identity: " + "; ".join(bad))
        need(r0["frame"] == cfg["face_frame"], f"opened on {r0['frame']}, not the face frame {cfg['face_frame']}")
        sug = cfg["suggested"]
        need(all(r1["corr"][k] == sug[k] for k in sug) and r1["whiteText"] == f"{sug['white']:.3f}",
             f"Suggested fix gave {r1['corr']} (white shows {r1['whiteText']}), wanted {sug}")
        # mutant: a copy of the board that opens at the measured values must fail the same identity check
        live = ws / "editor/grade-board/index.html"
        orig = live.read_bytes()
        need(orig.decode("utf-8").count(MUTANT_OPEN[0]) == 1, "the mutant edit does not apply to the board")
        drop_state(d)
        live.write_bytes(orig.decode("utf-8").replace(*MUTANT_OPEN).encode("utf-8"))
        try:
            m = reads(browse("identity-reel", [{"do": "eval", "js": READ}], "identity-mutant"))[0]
        finally:
            live.write_bytes(orig)
        need(identity_problems(m), f"the mutant (opens at the measured values) still passed the identity check: {m}")

    def c_send():
        boards = load(DOCTOR / "boards.json")["boards"]
        need(boards["grade-board"]["writes"] == ["grade-selection.json"], f"grade-board writes {boards['grade-board']['writes']}")
        block = (PLUGIN / "hooks/mod/logic.ts").read_text(encoding="utf-8").split("export const SENDS", 1)[1].split("\n]", 1)[0]
        sends = re.findall(r"file: '([^']+)'", block)
        writes = {w for b in boards.values() for w in b.get("writes", [])}
        need("grade-selection.json" in sends and not set(sends) - writes,
             f"logic.ts Send names not in any boards.json writes: {sorted(set(sends) - writes)} (SENDS {sends})")
        d, cfg = reel("send-reel")
        need(post("send-reel", "selection.json") == 403 and not (d / "selection.json").exists(),
             "a __save of selection.json for grade-board was not refused with 403")
        # Pick the look at run time: the first look the skin guard passes on THIS clip. A look that fails
        # the guard is refused by the board by design, so a hard-coded look breaks on some clips.
        passing = [lk["id"] for lk in cfg["looks"] if (lk.get("guard") or {}).get("ok") is not False]
        need(passing, f"no look passes the skin check on this clip: {[(lk['id'], lk.get('guard')) for lk in cfg['looks']]}")
        pick = passing[0]
        print(f"    send look: {pick} (first look the skin guard passes on this clip)")
        # Refusal leg: a look that fails the guard is refused with the board's plain message, no slider,
        # no crash. Use a look that fails on this clip; if none does, plant the failure in the config.
        failing = [lk for lk in cfg["looks"] if (lk.get("guard") or {}).get("ok") is False]
        rd, rcfg = reel("refuse-reel")
        if failing:
            bad = failing[0]
            planted = False
        else:
            bad = next(lk for lk in rcfg["looks"] if lk["id"] == "warm")
            bad["guard"] = dict(bad.get("guard") or {}, ok=False)
            write_json(rd / "grade/grade-config.json", rcfg)
            planted = True
        print(f"    refused look: {bad['id']} ({'planted' if planted else 'fails the guard on this clip'})")
        msg = f"{bad['name']} fails the skin check on this reel"
        browse("refuse-reel", [{"do": "domclick", "sel": f'#rail figure[data-look="{bad["id"]}"]'},
                               {"do": "waitText", "sel": "#lookNote", "re": re.escape(msg)},
                               {"do": "waitFn", "js": "!document.getElementById('strength')"
                                " && document.querySelector('#rail figure.on').dataset.look === 'none'"}], "refuse")
        need(not (rd / "grade-selection.json").exists(), "a refused look wrote a grade-selection.json")
        def check_visible():
            # Keep the real hub geometry at 1024x768, then reproduce the walk's
            # 799 px board itself. A 799 px HUB window gives a much narrower iframe.
            for width, direct in ((1024, None), (799, "/editor/grade-board/?reel=send-reel")):
                (d / "grade-selection.json").unlink(missing_ok=True)
                saved, layout = reads(browse("send-reel", [
                    {"do": "waitFn", "js": "window.GB && GB.ready"},
                    {"do": "domclick", "sel": f'#rail figure[data-look="{pick}"]'},
                    {"do": "set", "sel": "#strength", "value": "0.6"},
                    {"do": "waitFn", "js": "!document.querySelector('#send').disabled"},
                    {"do": "click", "sel": "#send"},
                    {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"},
                    # No scrollIntoView of #saved: it must be visible immediately after Send.
                    {"do": "bounds", "sel": "#saved"},
                    {"do": "eval", "js": "JSON.stringify({width:innerWidth,"
                     "header:document.querySelector('header').getBoundingClientRect().toJSON(),"
                     "send:document.querySelector('#send').getBoundingClientRect().toJSON()})"}],
                    f"send-{width}", direct_path=direct, viewport={"width": width, "height": 768}))
                need(saved["viewport"] == {"width": width, "height": 768}, f"Grade viewport: {saved}")
                need(layout["width"] == 799 if direct else 0 < layout["width"] < 1024,
                     f"Grade board width: {layout}")
                need(saved["text"].startswith("✓ Sent to Claude at "), f"Grade confirmation: {saved}")
                need(saved["visible"] and saved["hit"],
                     f"Grade confirmation is clipped or covered after Send: {saved}; layout: {layout}")
                box, header = saved["box"], layout["header"]
                need(box["left"] >= header["left"] and box["right"] <= header["right"]
                     and box["top"] >= header["top"] and box["bottom"] <= header["bottom"],
                     f"Grade confirmation overflows the header: {saved}; layout: {layout}")
                send = layout["send"]
                same_row = abs((box["top"] + box["bottom"]) / 2 - (send["top"] + send["bottom"]) / 2) <= 12
                horizontal_gap = max(0, box["left"] - send["right"], send["left"] - box["right"])
                under = (max(box["left"], send["left"]) < min(box["right"], send["right"])
                         and 0 <= box["top"] - send["bottom"] <= 12)
                need((same_row and horizontal_gap <= 24) or under,
                     f"Grade confirmation is not next to Send: {saved}; layout: {layout}")
                print(f"    Grade {width} window / {layout['width']} board: {saved}; layout: {layout}", flush=True)
        check_visible()
        sel = d / "grade-selection.json"
        need(sel.is_file(), "no grade-selection.json in the reel folder after Send")
        need(not (d / "selection.json").exists(), "a selection.json was written too")
        doc = load(sel)
        need(doc["look"] == {"id": pick, "strength": 0.6}, f"look sent as {doc['look']}")
        need(doc["correction"] == IDENTITY, f"correction sent as {doc['correction']}")
        need(doc["reel"] == "send-reel" and doc["math_version"] == SPEC["version"] and doc["saved_at"],
             f"reel {doc.get('reel')}, math_version {doc.get('math_version')}, saved_at {doc.get('saved_at')}")
        # The walk's missing-confirmation report did not reproduce in headless Chrome at 1024x768 or 799 px (the header wraps), so the positive visibility/next-to-Send checks stay as a regression guard.

    def c_reload():
        d, cfg = reel("reload-reel")
        ok_looks = [lk["id"] for lk in cfg["looks"] if (lk.get("guard") or {}).get("ok") is not False]
        need(ok_looks, "no look passes the skin check on this clip")
        look = "punchy" if "punchy" in ok_looks else ok_looks[0]  # run-time pick: a guard-failing look is refused
        browse("reload-reel", [{"do": "domclick", "sel": f'#rail figure[data-look="{look}"]'},
                               {"do": "set", "sel": "#strength", "value": "0.4"}, {"do": "click", "sel": "#suggest"},
                               {"do": "waitState", "board": "grade-board",
                                "js": f"s.A && s.A.look.id === '{look}' && s.A.look.strength === 0.4 && s.A.correction.white !== 1"}],
               "reload-1")
        need((d / "grade-board.state.json").is_file(), "no grade-board.state.json on disk")
        r = reads(browse("reload-reel", [{"do": "eval", "js": READ}], "reload-2"))[0]
        sug = cfg["suggested"]
        got = (r["look"], r["on"], r["strength"], r["corr"]["white"], r["whiteText"])
        need(got == ({"id": look, "strength": 0.4}, [look], "0.4", sug["white"], f"{sug['white']:.3f}"),
             f"after a reload in a new browser the board shows (look, highlighted, strength, white, white text) = {got}")
        drop_state(d)
        r = reads(browse("reload-reel", [{"do": "eval", "js": READ}], "reload-3"))[0]
        bad = identity_problems(r)
        need(not bad, "without grade-board.state.json the board did not open at the identity: " + "; ".join(bad))

    def c_roundtrip():
        d, cfg = reel("trip-reel")
        img = Image.new("RGB", (360, 240))
        for i, c in enumerate(PATCHES):
            img.paste(c, (i % 3 * 120, i // 3 * 120, i % 3 * 120 + 120, i // 3 * 120 + 120))
        img.save(d / "grade/patches.png")
        cfg["frames"].append({"pct": None, "t": None, "file": "patches.png", "label": "patches"})
        write_json(d / "grade/grade-config.json", cfg)
        # Pick the look at run time: Punchy first, else the first guard-passing look, whose bake of this exact
        # Send (strength 0.5, Suggested fix, temp +0.2) the skin guard accepts on THIS clip. A combination that
        # turns skin past the limit is refused by design, so a hard-coded look breaks on some clips.
        corr = dict(IDENTITY)
        corr.update({k: float(v) for k, v in cfg["suggested"].items() if k in SPEC["pre_pass"]["params"]})
        corr["temp"] = 0.2
        order = ["punchy"] + [lk["id"] for lk in cfg["looks"]
                              if lk["id"] != "punchy" and (lk.get("guard") or {}).get("ok") is not False]
        pd, _ = reel("trip-probe")
        look = None
        for lid in order:
            write_json(pd / "grade-selection.json", {"look": {"id": lid, "strength": 0.5}, "correction": corr,
                                                     "reel": "trip-probe", "math_version": SPEC["version"],
                                                     "saved_at": "probe"})
            if py(RG, "grade_from_selection.py", "--reel-dir", pd).returncode == 0:
                look = lid
                break
        need(look, f"no look's Send passes the skin guard on this clip (tried {order})")
        print(f"    roundtrip look: {look} (first whose Send the skin guard accepts on this clip)")
        out = browse("trip-reel", [
            {"do": "click", "sel": '#frames button[data-f="patches.png"]'},
            {"do": "waitFn", "js": "GB.S.frame === 'patches.png' && GB.ready"},
            {"do": "domclick", "sel": f'#rail figure[data-look="{look}"]'}, {"do": "set", "sel": "#strength", "value": "0.5"},
            {"do": "click", "sel": "#suggest"}, {"do": "set", "sel": "#tune input[data-k=temp]", "value": "0.2"},
            {"do": "eval", "js": PIXELS}, {"do": "eval", "js": FLOAT},
            {"do": "waitFn", "js": "!document.querySelector('#send').disabled"}, {"do": "click", "sel": "#send"},
            {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"},
            {"do": "waitState", "board": "grade-board",
             "js": f"s.A && s.A.look.id === '{look}' && s.A.look.strength === 0.5 && s.A.correction.temp === 0.2"}], "roundtrip")
        board, board_f = reads(out)[:2]
        sel = load(d / "grade-selection.json")
        need(sel["look"] == {"id": look, "strength": 0.5} and sel["correction"]["temp"] == 0.2
             and sel["correction"]["white"] == cfg["suggested"]["white"], f"sent {sel['look']} {sel['correction']}")
        msg = ok(py(RG, "grade_from_selection.py", "--reel-dir", d), "grade_from_selection.py")
        need("Nothing was applied" in msg, f"the bake said {msg.strip()!r}")
        g = load(d / "grade.json")
        need(g["look"] == {"id": look, "strength": 0.5} and g["takes"][0]["correction"] == sel["correction"]
             and "extra_generations" not in g, f"grade.json {json.dumps(g)[:400]}")

        def fgap(cube, vals):
            need(bg.parse_cube(cube)[0] == 33, "the cube is not 33^3, so LAT is not on its lattice")
            return float(np.max(np.abs(bg.through_cube(cube, LAT) - np.asarray(vals, dtype=np.float64))))
        fg = fgap(d / g["cube"], board_f)
        need(fg <= FTOL, f"the cube vs the board's float maths on the lattice nodes: {fg:.2e} > {FTOL:g}")

        def applied(root, reel_dir, name):
            o = scratch / name
            p = py(root, "grade_from_selection.py", "--reel-dir", reel_dir, "--apply", reel_dir / "grade/patches.png", "-o", o)
            need(p.returncode == 2 and not o.exists(), f"--apply without --yes: exit {p.returncode}, output {o.exists()}")
            ok(py(root, "grade_from_selection.py", "--reel-dir", reel_dir, "--apply", reel_dir / "grade/patches.png",
                  "-o", o, "--yes"), "grade_from_selection.py --apply --yes")
            im = Image.open(o).convert("RGB")
            return [list(im.getpixel((int(u * im.width), int(v * im.height)))) for u, v in PTS]

        def gap(x, y):
            return max(abs(p - q) for a_, b_ in zip(x, y) for p, q in zip(a_, b_))
        got = applied(RG, d, "applied.png")
        need(gap(got, [list(c) for c in PATCHES]) > TOL, f"the applied grade barely moved the patches: {got}")
        need(gap(got, board) <= TOL, f"applied {got} vs the board {board}: {gap(got, board)}/255 > {TOL}")
        def mutant(script, edit):
            """A copy of the scripts with one edit, baked from a copy of this reel's Send -> (script root, reel dir)."""
            S["mut"] += 1
            root = scratch / f"mutant{S['mut']}" / "skills"
            ign = shutil.ignore_patterns("__pycache__")
            shutil.copytree(RG, root / "reel-grade", ignore=ign)
            shutil.copytree(PLUGIN / "skills/_shared", root / "_shared", ignore=ign)
            mp = root / "reel-grade/scripts" / script
            src = mp.read_bytes().decode("utf-8")
            need(src.count(edit[0]) == 1, f"the mutant edit does not apply to {script}")
            mp.write_bytes(src.replace(*edit).encode("utf-8"))
            md = scratch / f"trip-mutant{S['mut']}"
            shutil.copytree(d, md, ignore=shutil.ignore_patterns("raw"))
            ok(py(root / "reel-grade", "grade_from_selection.py", "--reel-dir", md), f"mutant bake ({script})")
            return root / "reel-grade", md
        # mutant: a bake that ignores the strength must not match the board's pixels
        mroot, md = mutant("grade_from_selection.py", MUTANT_BAKE)
        mgot = applied(mroot, md, "applied-mutant.png")
        need(gap(mgot, board) > TOL, f"the mutant (strength ignored) still matched the board: {gap(mgot, board)}/255")
        # mutant: a bake that runs one tint step more than the board must not match the board's float maths
        _, td = mutant("bake_grade.py", MUTANT_TINT_BAKE)
        tb = fgap(td / load(td / "grade.json")["cube"], board_f)
        need(tb > FTOL, f"the mutant (bake +1 tint step) still matched the board's float maths: {tb:.2e}")
        # mutant: a board that runs one tint step more than it sends (state comes back from disk) must not match the cube
        live = ws / "editor/grade-board/index.html"
        orig = live.read_bytes()
        need(orig.decode("utf-8").count(MUTANT_TINT_BOARD[0]) == 1, "the tint mutant edit does not apply to the board")
        live.write_bytes(orig.decode("utf-8").replace(*MUTANT_TINT_BOARD).encode("utf-8"))
        try:
            ms, mf = reads(browse("trip-reel", [{"do": "eval", "js": "JSON.stringify(GB.st())"}, {"do": "eval", "js": FLOAT}],
                                  "roundtrip-board-mutant"))
        finally:
            live.write_bytes(orig)
        need((ms["look"], ms["correction"]) == (sel["look"], sel["correction"]),
             f"the board mutant reopened at {ms['look']} {ms['correction']}, not the sent grade")
        tw = fgap(d / g["cube"], mf)
        need(tw > FTOL, f"the mutant (board +1 tint step) still matched the cube: {tw:.2e}")
        print(f"    applied vs board {gap(got, board)}/255 (<= {TOL}); strength-ignored mutant {gap(mgot, board)}/255;"
              f" float {fg:.1e} (<= {FTOL:g}); tint-step mutants bake {tb:.1e}, board {tw:.1e}", flush=True)
        # a video takes the client's yes and is counted as one more generation; a changed cube is refused
        mp4 = scratch / "graded.mp4"
        ok(py(RG, "grade_from_selection.py", "--reel-dir", d, "--apply", d / "raw/clip.mp4", "-o", mp4, "--yes"),
           "grade_from_selection.py --apply <video> --yes")
        g = load(d / "grade.json")
        need(mp4.is_file() and g.get("extra_generations") == 1, f"video applied {mp4.is_file()}, grade.json {g.get('extra_generations')}")
        cube = d / g["cube"]
        cube.write_bytes(cube.read_bytes() + b"\n")
        bad = scratch / "tampered.mp4"
        p = py(RG, "grade_from_selection.py", "--reel-dir", d, "--apply", d / "raw/clip.mp4", "-o", bad, "--yes")
        need(p.returncode == 1 and not bad.exists() and "changed" in p.stdout, f"a changed cube: exit {p.returncode}, {p.stdout.strip()}")

    fns = {"send_loading": ("send_loading: disabled static Send and cue; enabled-button mutant fails", send_loading_case),
           "early_send": ("early_send: Send is disabled or wired before boot; an enabled click writes grade-selection.json", c_early_send),
           "failed_init": ("failed_init: plain error, no Loading cue and disabled Send; cleanup mutants fail", c_failed_init),
           "identity": ("identity: the board opens at the identity (white 1.000, grade_math defaults, look None); "
                        "Suggested fix applies the measured values; the measured-defaults mutant fails", c_identity),
           "send": ("send: a look + strength + Send writes grade-selection.json, never selection.json", c_send),
           "reload": ("reload: the look, strength and fix come back from grade-board.state.json in a new browser", c_reload),
           "roundtrip": ("roundtrip: Send -> cube -> apply matches the board within 3/255 and its float maths within 1e-4; "
                         "the strength and 1-step tint mutants fail; "
                         "a video apply needs --yes and records extra_generations 1", c_roundtrip)}
    try:
        for n in want:
            case(*fns[n])
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
                p.wait(10)
            p.stdout.close()
        shutil.rmtree(scratch, ignore_errors=True)
    passed = sum(results)
    print(f"{passed} passed, {len(results) - passed} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
