#!/usr/bin/env python3
"""S4b.3 check for the Cut Board and the Tweak Board on the editor boards (board_server.py), their scripts in
reel-first-cuts/scripts, the boards.json hub tabs and the videos folder's .gitignore.

usage: python tests/editor/boards_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case (each one runs in under 150 s);
without it every case runs. Cases: import, cut-send, cut-reload, all-take, tweak-send, roundtrip, tweak-beat, drift,
gitignore, port, hub-roundtrip, tabs, offline.

The fixture reel: S3's REEL_018 take1 work files (edit_map.json, tx.16k.wav, probe.json, envelope.json) entered as
take 1 and take 2, with take 2 a trimmed copy of the map that drops line L02's words. The script is the take's six
sentences from 46.5 s to 59.5 s, one per line; the last line's read runs to the end of the take, so a cut that is
rendered drops L06. Every child runs with HOME and USERPROFILE at <scratch>/home. Boards are served by the real
board_server.py from a scratch workspace (editor/editor.config.json names the paths, cuts.beat_ms 280).

H-LOCK-1: every headless Chrome run goes through heavy_lock.py --min-gb 3 (exit 75/76 = the case is unproven, the
test exits with that code). The renders are TINY (360x640, at most 10 s): render.py's own build_graph() and encode()
on a synthetic 360x640 source carrying the take's audio, with render.py's frame count checked against cuts.json;
they skip heavy_lock and refuse below 1 GB free RAM.
"""
import argparse, hashlib, http.client, json, os, re, shlex, shutil, socket, subprocess, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402  (S4b.1's helpers: tools, the RAM check, module(), TINY_VF)

rt, SCRIPTS, PY = cs.rt, cs.SCRIPTS, cs.PY
PLUGIN = SCRIPTS.parents[2]
DOCTOR = PLUGIN / "skills/editor-doctor/scripts"
sys.path.insert(0, str(DOCTOR))
import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)

HEAVY = r"C:/Workspaces/Content Studio/output/scripts/heavy_lock.py"
CLICK = HERE / "boards_click.js"
FX = Path(cs.S3_WORK)
FX_FILES = ("edit_map.json", "tx.16k.wav", "probe.json", "envelope.json")
WINDOW = (46.5, 59.5)            # the six sentences the script is made of
GONE_FROM_T2 = 1                 # L02 is absent from take 2
TABS = {"cut-board": ("Cut Board", ["cut"], 10), "beat-map": ("Beat Map", ["motion"], 20),
        "sketches": ("Sketches", ["motion"], 30), "tweak-board": ("Tweak Board", ["tweak"], 40),
        "sound-board": ("Sound Board", ["sound"], 50), "grade-board": ("Grade Board", ["grade"], 60),
        "look-picker": ("Look Picker", ["captions"], 70), "cover-picker": ("Cover Picker", ["cover"], 80),
        "trials": ("Trial reels", ["cover"], 90)}
SOUND_LINE = ('"sound-board": {"skill": "reel-sound-pass", "template": "skills/reel-sound-pass/boards/sound-board", '
              '"writes": ["sound-selection.json"], "tab": {"label": "Sound Board", "stages": ["sound"], "order": 50}},')
VIDEOS_IGNORE = ["*selection.json", "*.state.json", "*.prev"]
SHIPPED = ("make_board.py", "selection_to_edl.py", "port_selection.py", "make_tweaks.py", "tweaks_to_edl.py")
fails = []
G = {}                           # scratch, ws, env, server, port, tools, browsers


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)
    return ok


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sh(cmd, cwd=None, env=None, timeout=140):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env or G["env"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def script(name, *args, root=SCRIPTS):
    return sh([PY, "-X", "utf8", "-I", Path(root) / name] + list(args), cwd=G["ws"])


def write(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1), encoding="utf-8")


def bem():
    return cs.module("build_edit_map.py")


def printed(stdout, plugin=PLUGIN):
    """The printed `<editor python> ... gaps.py ...` line, as an argv for this machine."""
    line = next((ln for ln in stdout.splitlines() if "gaps.py" in ln), "")
    return line, shlex.split(line.replace("<editor python>", Path(PY).as_posix())
                             .replace("${CLAUDE_PLUGIN_ROOT}", Path(plugin).as_posix())) if line else []


# ------------------------------------------------------------------------------------------- workspace + reel
def setup(S):
    home = S / "home"
    home.mkdir(parents=True, exist_ok=True)
    G.update(scratch=S, env=dict(cs.ENV, HOME=str(home), USERPROFILE=str(home)), browsers=0)
    ws = S / "ws"
    shutil.rmtree(ws, ignore_errors=True)
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": free_port()}}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    cfg = rt.read_config(ws)
    cfg["cuts"] = {"beat_ms": 280}
    check_deps.atomic_write(rt.config_path(ws), json.dumps(cfg, indent=2))
    (ws / cfg["paths"]["videos"]).mkdir(parents=True, exist_ok=True)
    G["ws"], G["videos"] = ws, ws / cfg["paths"]["videos"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def sentences(m):
    out, cur = [], []
    for w in m["words"]:
        cur.append(w)
        if w["word"].strip().endswith((".", "?", "!")):
            out.append(cur)
            cur = []
    return [c for c in out if WINDOW[0] <= c[0]["parakeet_start"] < WINDOW[1]]


def reel(name):
    """A scratch reel: the S3 files as take 1, the trimmed map as take 2, the script, the shots, make_board."""
    d = G["videos"] / name
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    for n in FX_FILES:
        shutil.copyfile(FX / n, d / "work" / n)
    m = cs.load(FX / "edit_map.json")
    lines = sentences(m)
    gone = {w["id"] for w in lines[GONE_FROM_T2]}
    m2 = dict(m, words=[w for w in m["words"] if w["id"] not in gone])
    b = bem()
    m2["word_list_hash"] = b.word_list_hash(b.board_sequence(m2))
    assert not b.validate(m2), b.validate(m2)
    write(d / "work/edit_map.take2.json", m2)
    (d / "script.md").write_text("# Test script\n---\n" + "".join(" ".join(w["word"].strip() for w in s) + "\n"
                                                             for s in lines), encoding="utf-8")
    write(d / "shots.json", {"vocab": ["talking head", "screen"], "default": "talking head"})
    p = script("make_board.py", "--script", d / "script.md",
               "--take", "1:%s:%s" % (d / "work/edit_map.json", d / "work/tx.16k.wav"),
               "--take", "2:%s:%s" % (d / "work/edit_map.take2.json", d / "work/tx.16k.wav"),
               "--shots", d / "shots.json", "--reel", name, "-o", d)
    ck("%s: make_board.py builds cut-board.config.json (6 lines, 2 takes)" % name,
       p.returncode == 0 and (d / "cut-board.config.json").is_file(), (p.returncode, p.stdout[-300:], p.stderr[-500:]))
    return d, cs.load(d / "cut-board.config.json")


def selection(cfg, drop=("L06",), speed=1.0, beat_ms=None):
    """The page's fresh() ruling, with the lines in drop dropped."""
    return dict(v=2, reel=cfg["reel"], gap_default_ms=cfg["gap_default_ms"], speed=speed,
                beat_ms=cfg["beat_ms"] if beat_ms is None else beat_ms,
                word_list_hash={n: t["word_list_hash"] for n, t in cfg["takes"].items()}, board_hash=cfg["board_hash"],
                lines=[dict(id=l["id"], pick=l["default"], drop=l["default"] is None or l["id"] in drop,
                            flag=l.get("flag"), note="", gap_after={"mode": "default"}, shot=None, rm={}, sil={})
                       for l in cfg["lines"]])


def cut(d, sel_path):
    """selection_to_edl.py, then the gaps.py command it printed. Returns (selection_to_edl run, gaps run, argv)."""
    p = script("selection_to_edl.py", sel_path, d / "cut-board.config.json")
    line, argv = printed(p.stdout)
    g = sh(argv, cwd=G["ws"]) if argv else None
    return p, g, argv


SRC_S = 60.0


def source():
    """The tiny render's raw: 360x640 grey at 30 fps carrying the take's audio (48 kHz PCM), 0-60 s, made once."""
    out = G["scratch"] / "fixtures" / "take-grey-360x640.mov"
    if not out.exists():
        cs.need_ram()
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name("_partial.mov")
        p = sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=360x640:r=30:d=%s" % SRC_S,
                "-i", FX / "tx.16k.wav", "-t", SRC_S, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset",
                "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-ar", "48000", "-c:a", "pcm_s16le", tmp])
        if p.returncode:
            raise SystemExit("fixture ffmpeg failed: %s" % p.stderr[-600:])
        os.replace(tmp, out)
    return out


def tiny(d):
    """A TINY master of the reel's cuts.json through render.py's own build_graph() + encode(); render.py's
    frame-count rule checked here. Returns the master path, or None after a FAIL."""
    w = d / "work"
    cuts, probe = cs.load(w / "cuts.json"), cs.load(w / "probe.json")
    if not cuts.get("segments"):
        ck("%s: gaps.py wrote cuts.json" % d.name, False, "no cuts.json")
        return None
    fps, frames = cuts["fps"], cuts["segments"][-1]["out_out_f"]
    if not ck("%s: the cut is short enough for a tiny render (%.2f s <= 10 s, inside the %g s source)"
              % (d.name, frames / fps, SRC_S), frames / fps <= 10.0 and
              cuts["segments"][-1]["src_out_f"] / fps <= SRC_S):
        return None
    src = source()
    cs.need_ram()
    render = cs.module("render.py")
    graph = w / "_graph-tiny.txt"
    graph.write_text(render.build_graph(cuts, render.sample_rate(src, 0), cs.TINY_VF, 0), encoding="utf-8")
    master = w / "renders" / "master-tiny.mp4"
    master.parent.mkdir(exist_ok=True)
    t0 = time.time()
    render.encode(src, graph, master, fps, probe.get("fps_flag", "-fps_mode"), 14, "slow", int(round(fps)), "192k")
    got = render.count_frames(master)
    ok = ck("%s: tiny master (360x640, %.2f s, %.1f s to render) has exactly the last out_out_f frames (%d rendered, "
            "%d in cuts.json)" % (d.name, frames / fps, time.time() - t0, got, frames), got == frames)
    return master if ok else None


def tweaks(d, master, take=1):
    p = script("make_tweaks.py", "--cut", master, "--work", d / "work", "--config", d / "cut-board.config.json",
               "--take", take, "-o", d)
    ck("%s: make_tweaks.py writes tweak-board.config.json" % d.name,
       p.returncode == 0 and (d / "tweak-board.config.json").is_file(), (p.stdout[-300:], p.stderr[-500:]))
    return cs.load(d / "tweak-board.config.json")


def ready_cut(d, cfg, **kw):
    """The default ruling (L06 dropped) -> edl -> gaps -> tiny render -> make_tweaks. Returns the tweak config or {}."""
    sel = d / "cut-selection.json"
    write(sel, selection(cfg, **kw))
    p, g, argv = cut(d, sel)
    if not ck("%s: selection_to_edl + the gaps.py command it printed run" % d.name,
              p.returncode == 0 and g is not None and g.returncode == 0,
              (p.returncode, p.stderr[-300:], g and g.stderr[-300:])):
        return {}
    master = tiny(d)
    return tweaks(d, master) if master else {}


# ------------------------------------------------------------------------------------------- server + browser
def server():
    if G.get("server") and G["server"].poll() is None:
        return G["port"]
    # the venv's python.exe is a launcher that runs the real one as a child, so a kill would leave the server up
    exe = getattr(sys, "_base_executable", sys.executable)
    p = subprocess.Popen([exe, "-X", "utf8", "-I", str(DOCTOR / "board_server.py"), "--root", str(G["ws"]),
                          "--idle", "60", "--grace", "180"], env=G["env"], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    t = threading.Timer(20, p.kill)
    t.start()
    line = p.stdout.readline().strip()
    t.cancel()
    if not line.startswith("Editor boards: http://127.0.0.1:"):
        raise SystemExit("board_server.py did not start: %r" % line)
    G["server"], G["port"] = p, int(line.rsplit(":", 1)[1].rstrip("/"))
    return G["port"]


def tools():
    if "tools" not in G:
        G["tools"] = {"node": rt.tool("node"), "chrome": rt.tool("chrome"),
                      "pup": str(rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js")}
    return G["tools"]


def refresh_hub():
    """Install the real hub and build its data after the fixture reels exist."""
    server()  # Finish startup board_sync before refreshing the generated data.
    for name in ("board_sync.py", "hub_rows.py"):
        p = sh([PY, "-X", "utf8", "-I", "-B", DOCTOR / name, "--root", G["ws"]], cwd=G["ws"])
        if p.returncode:
            raise RuntimeError("hub setup %s: %s" % (name, p.stdout + p.stderr))


def browse(actions, label):
    """One NEW headless Chrome (fresh profile) under heavy_lock. Returns the driver's output; a failed run is a FAIL."""
    port, t = server(), tools()
    G["browsers"] += 1
    job = G["scratch"] / "jobs" / ("%02d-%s.json" % (G["browsers"], label))
    write(job, {"base": "http://127.0.0.1:%d" % port, "userDataDir": str(G["scratch"] / "profiles" / job.stem),
                "actions": actions})
    p = sh([PY, "-X", "utf8", "-I", HEAVY, "--wait", "60", "--min-gb", "3", "--", t["node"], CLICK, t["pup"],
            t["chrome"], job], timeout=145)
    if p.returncode in (75, 76):
        print(p.stdout[-300:] + p.stderr[-300:])
        print("UNPROVEN (%s): heavy_lock exit %d" % ("RAM" if p.returncode == 76 else "lock wait", p.returncode))
        sys.exit(p.returncode)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        out = {}
    ck("%s: the browser run finished with no page error" % label, p.returncode == 0 and out and not out.get("errors"),
       (p.returncode, out.get("error"), out.get("errors"), p.stderr[-400:]))
    return out or {"reads": [], "errors": [], "requests": []}


def canon(o):
    return json.dumps({k: v for k, v in o.items() if k != "saved_at"}, sort_keys=True)


CUT_READY = {"wait": "section.line"}
TWEAK_READY = {"waitFn": "typeof C!=='undefined' && C && document.getElementById('v').readyState>=1"}
STATE = "JSON.stringify(S)"


def word_click(cfg, line, att, n):
    w = cfg["lines"][line]["attempts"][att]["words"][n]
    return '.w[data-w="%d:%d:%d"]' % (line, att, w["i"]), w["i"]


# ------------------------------------------------------------------------------------------- cases
def case_import(S, a):
    d, cfg = reel("import")
    write(d / "cut-selection.json", selection(cfg))
    p = script("selection_to_edl.py", d / "cut-selection.json", d / "cut-board.config.json")
    line, argv = printed(p.stdout)
    ck("import: with HOME at scratch, selection_to_edl.py runs (exit %d)" % p.returncode, p.returncode == 0, p.stderr[-400:])
    ck("import: the printed gaps.py command is the editor python on the plugin's gaps.py with --words and --speed: %s"
       % line, line.startswith('<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/gaps.py"')
       and "--words" in argv and "--speed" in argv and "python scripts/gaps.py" not in p.stdout, p.stdout[-400:])
    for n in SHIPPED:
        t = (SCRIPTS / n).read_text(encoding="utf-8")
        ck("import: %s imports nothing from ~/.claude and calls ensure_utf8_output()" % n,
           "jetson-whisper" not in t and ".claude" not in t and "ensure_utf8_output()" in t)
    # H-R16 proof: a scratch mirror of the plugin's scripts where make_board.py has the old import back
    mut = mirror(S, "mut-import")
    mb = mut / "skills/reel-first-cuts/scripts/make_board.py"
    t = mb.read_text(encoding="utf-8")
    ours = ("sys.path.insert(0, str(HERE))\n"
            "from build_edit_map import audio_sha256, board_hash, board_sequence, validate, wav_duration  # noqa: E402\n")
    old = ('sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "jetson-whisper" / "scripts"))\n'
           "try:\n    from build_edit_map import audio_sha256, board_hash, board_sequence, validate, wav_duration\n"
           "except ImportError as e:\n"
           '    raise SystemExit(f"make_board.py needs build_edit_map.py from the jetson-whisper skill: {e}")\n')
    ck("import: the mutant replaces make_board.py's own import block", t.count(ours) == 1)
    mb.write_text(t.replace(ours, old), encoding="utf-8")
    args = ["--script", d / "script.md", "--take", "1:%s:%s" % (d / "work/edit_map.json", d / "work/tx.16k.wav"),
            "--shots", d / "shots.json", "--reel", "mut", "-o", d]
    p = script("make_board.py", *args, root=mb.parent)
    ck("import: the mutant with the old jetson-whisper import fails with HOME at scratch (exit %d: %s)"
       % (p.returncode, p.stderr.strip()[-160:]), p.returncode != 0 and ("jetson-whisper" in p.stderr or "ImportError" in p.stderr
                                                                         or "No module named" in p.stderr))
    # control: the same mutant runs once a jetson-whisper copy sits under that HOME, so it really read ~
    jw = S / "home-jw"
    (jw / ".claude/skills/jetson-whisper/scripts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCRIPTS / "build_edit_map.py", jw / ".claude/skills/jetson-whisper/scripts/build_edit_map.py")
    p = sh([PY, "-X", "utf8", "-I", mb] + args, cwd=G["ws"], env=dict(G["env"], HOME=str(jw), USERPROFILE=str(jw)))
    ck("import: control: the mutant runs when HOME holds a jetson-whisper copy (exit %d)" % p.returncode,
       p.returncode == 0, p.stderr[-300:])
    shutil.rmtree(mut, ignore_errors=True)
    shutil.rmtree(jw, ignore_errors=True)


def mirror(S, name):
    """skills/_shared + skills/reel-first-cuts/scripts copied to scratch, keeping their relative layout."""
    m = S / name
    shutil.rmtree(m, ignore_errors=True)
    for rel in ("skills/_shared", "skills/reel-first-cuts/scripts"):
        shutil.copytree(PLUGIN / rel, m / rel, ignore=shutil.ignore_patterns("__pycache__"))
    return m


def case_cut_send(S, a):
    d, cfg = reel("cut-send")
    sentinel = d / "tweak-selection.json"
    sentinel.write_bytes(b'{"marks": [], "sentinel": true}\n')
    old = time.time() - 3600
    os.utime(sentinel, (old, old))
    before = (sha(sentinel), sentinel.stat().st_mtime_ns)
    strike, wi = word_click(cfg, 2, 0, 1)
    browse([dict(do="goto", path="/editor/cut-board/?reel=cut-send", **CUT_READY),
            {"do": "click", "sel": '[data-pick="0:1"]'}, {"do": "click", "sel": strike},
            {"do": "waitState", "board": "cut-board", "js": "s.lines[0].pick===1 && (s.lines[2].rm['0']||[]).includes(%d)" % wi},
            {"do": "click", "sel": "#send"}, {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"}],
           "cut-send")
    sel = cs.load(d / "cut-selection.json")
    keys = {"v", "reel", "gap_default_ms", "speed", "beat_ms", "word_list_hash", "board_hash", "lines", "saved_at"}
    ck("cut-send: cut-selection.json is written with the v:2 shape (keys %s)" % sorted(sel),
       sel.get("v") == 2 and keys <= set(sel) and sel.get("reel") == cfg["reel"] and sel.get("board_hash") == cfg["board_hash"]
       and len(sel.get("lines", [])) == len(cfg["lines"]), sorted(sel))
    ls = sel.get("lines") or [{}] * 3
    ck("cut-send: the changed pick (L01 on its take-2 read) and the struck word (L03 word %d) are in it" % wi,
       ls[0].get("pick") == 1 and ls[2].get("rm", {}).get("0") == [wi], ls[:3])
    ck("cut-send: beat_ms is the workspace's cuts.beat_ms (280)", sel.get("beat_ms") == 280, sel.get("beat_ms"))
    ck("cut-send: no shared selection.json, and tweak-selection.json is untouched (sha + mtime)",
       not (d / "selection.json").exists() and (sha(sentinel), sentinel.stat().st_mtime_ns) == before)


def case_cut_reload(S, a):
    d, cfg = reel("cut-reload")
    strike, wi = word_click(cfg, 3, 0, 2)
    browse([dict(do="goto", path="/editor/cut-board/?reel=cut-reload", **CUT_READY),
            {"do": "click", "sel": '[data-pick="2:1"]'}, {"do": "click", "sel": strike},
            {"do": "waitState", "board": "cut-board", "js": "s.lines[2].pick===1 && (s.lines[3].rm['0']||[]).includes(%d)" % wi}],
           "cut-reload-1")
    disk = cs.load(d / "cut-board.state.json")
    ck("cut-reload: cut-board.state.json on disk holds the pick and the strike",
       disk.get("lines", [{}] * 4)[2].get("pick") == 1 and disk["lines"][3]["rm"].get("0") == [wi])
    out = browse([dict(do="goto", path="/editor/cut-board/?reel=cut-reload", **CUT_READY), {"do": "eval", "js": STATE},
                  {"do": "eval", "js": "document.querySelectorAll('.w.rm').length"}], "cut-reload-2")
    s = json.loads(out["reads"][0]) if out["reads"] else {}
    ls = s.get("lines") or [{}] * 4
    ck("cut-reload: a new browser (no local copy) shows the same pick and strike, from the disk state",
       ls[2].get("pick") == 1 and ls[3].get("rm", {}).get("0") == [wi] and out["reads"][1] >= 1, ls[2:4])


def case_all_take(S, a):
    d, cfg = reel("all-take")
    L = cfg["lines"]
    out = browse([dict(do="goto", path="/editor/cut-board/?reel=all-take", **CUT_READY),
                  {"do": "click", "sel": '[data-drop="2"]'},
                  {"do": "waitState", "board": "cut-board", "js": "s.lines[2].drop===true"},
                  {"do": "eval", "js": STATE},
                  {"do": "click", "sel": '[data-all="1"]'},
                  {"do": "waitState", "board": "cut-board", "js": "s.lines[2].drop===false"},
                  {"do": "eval", "js": STATE},
                  {"do": "press", "key": "z", "ctrl": True},
                  {"do": "waitState", "board": "cut-board", "js": "s.lines[2].drop===true"},
                  {"do": "eval", "js": STATE},
                  {"do": "click", "sel": '[data-all="2"]'},
                  {"do": "waitState", "board": "cut-board", "js": "s.lines[%d].drop===true" % GONE_FROM_T2},
                  {"do": "eval", "js": STATE},
                  {"do": "eval", "js": "[...document.querySelectorAll('section.line')].map(x=>{const f=x.querySelector('.flag');return f?f.textContent:null;})"}],
                 "all-take")
    r = out["reads"]
    if not ck("all-take: the page answered every read", len(r) == 5, len(r)):
        return
    before, s1, undone, s2, flags = json.loads(r[0]), json.loads(r[1]), json.loads(r[2]), json.loads(r[3]), r[4]

    def last_in(i, n):
        js = [j for j, x in enumerate(L[i]["attempts"]) if x["take"] == n]
        return js[-1] if js else None
    ck("all-take: the dropped line L03 is back on its last take-1 read after 'all take 1'",
       s1["lines"][2]["drop"] is False and s1["lines"][2]["pick"] == last_in(2, 1), s1["lines"][2])
    ck("all-take: after 'all take 1' every line is on its take-1 read and none is flagged 'not in take 1' (take 1 holds "
       "every line)", all(l["pick"] == last_in(i, 1) and not l["drop"] and not l.get("flag") for i, l in enumerate(s1["lines"])),
       [(l["pick"], l["drop"], l.get("flag")) for l in s1["lines"]])
    ck("all-take: one Ctrl+Z restores the state from before the click", canon(undone) == canon(before),
       [(l["pick"], l["drop"]) for l in undone["lines"]])
    g = s2["lines"][GONE_FROM_T2]
    ck("all-take: after 'all take 2' the line absent from take 2 (L02) is flagged 'not in take 2' and dropped, on the page too",
       g["drop"] is True and g.get("flag") == "not in take 2" and flags[GONE_FROM_T2] == "not in take 2", (g, flags))
    takes = {L[i]["attempts"][l["pick"]]["take"] for i, l in enumerate(s2["lines"]) if not l["drop"] and l["pick"] is not None}
    ck("all-take: after 'all take 2' the kept lines use take 2 only (takes %s)" % sorted(takes), takes == {2})


def case_tweak_silence(S, a):
    d, cfg = reel("tweak-silence")
    tc = ready_cut(d, cfg)
    if not tc:
        return
    gap = dict(start=1.0, end=4.5, duration=3.5)
    if not ck("tweak-silence: fixture contains the gap", tc["duration"] >= gap["end"], tc["duration"]):
        return
    report = d / "work/long-silences.json"
    write(report, dict(silences=[gap]))
    refresh_hub()
    hub = G["ws"] / "editor/hub"
    shutil.copyfile(HERE / "fixtures/stub-hub.html", hub / "index.html")
    shutil.copyfile(DOCTOR / "boards.json", hub / "boards.json")

    def opened():
        return [{"do": "goto", "path": "/editor/hub/?reel=tweak-silence", "wait": '.tabs[data-built="boards.json"]'},
                {"do": "click", "sel": "#tab-tweak-board"}, dict(do="frame", sel=".frame iframe", **TWEAK_READY),
                {"do": "click", "sel": "#long-quiet summary"}]

    def sent(choice, label):
        (d / "tweak-selection.json").unlink(missing_ok=True)
        out = browse(opened() + [{"do": "click", "sel": f'#long-quiet input[value="{choice}"]'},
                     {"do": "eval", "js": "!document.querySelector('#dirty').hidden"},
                     {"do": "waitState", "board": "tweak-board", "js":
                      "s.silences?.[0]?.choice===" + json.dumps(choice) if choice else "!s.silences"},
                     {"do": "click", "sel": "#send"},
                     {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"},
                     {"do": "eval", "js": "document.querySelector('#dirty').hidden"}], label)
        ck(label + ": dirty before Send, clean after", out["reads"] == [True, True], out["reads"])
        return cs.load(d / "tweak-selection.json")

    def title_check(label):
        sel = sent("title", label)
        return sel.get("silences") == [dict(start=1.0, end=4.5, choice="title")] and sel["marks"] == []

    if not ck("tweak-silence: title rides Send without a mark", title_check("silence-title")):
        return
    out = browse(opened() + [{"do": "eval", "js": "document.querySelector('#long-quiet input[value=title]').checked"}],
                 "silence-restored")
    ck("tweak-silence: fresh browser restores title", out["reads"] == [True], out["reads"])
    sel = sent("cut", "silence-cut")
    entry = (sel.get("silences") or [{}])[0]
    ck("tweak-silence: cut has exactly its linked mark", sel["marks"] ==
       [dict(id=entry.get("mark"), type="cut", a=1.0, b=4.5)] and entry.get("choice") == "cut", sel)
    q = script("tweaks_to_edl.py", d / "tweak-selection.json", d / "work")
    ck("tweak-silence: tweaks_to_edl accepts silence key", q.returncode == 0, q.stdout + q.stderr)
    sel = sent("", "silence-later")
    ck("tweak-silence: decide later removes linked mark and key", "silences" not in sel and sel["marks"] == [], sel)
    report.unlink()
    out = browse(opened() + [{"do": "eval", "js": "document.querySelector('#long-quiet').textContent"}], "silence-missing")
    ck("tweak-silence: missing report is plain", bool(out["reads"]) and
       "No long quiet stretches to decide on." in out["reads"][0], out["reads"])
    write(report, dict(silences=[gap]))
    # Mutate only the served copy, then restore its exact bytes.
    board = G["ws"] / "editor/tweak-board/index.html"
    original = board.read_bytes()
    anchor = "body:JSON.stringify(S,null,1)"
    text = original.decode("utf-8")
    if ck("tweak-silence: mutant anchor unique", text.count(anchor) == 1):
        try:
            board.write_bytes(text.replace(anchor, "body:JSON.stringify({...S,silences:undefined},null,1)").encode("utf-8"))
            ck("tweak-silence: dropping silences from Send is caught", not title_check("silence-mutant"))
        finally:
            board.write_bytes(original)


def case_tweak_send(S, a):
    d, cfg = reel("tweak-send")
    tc = ready_cut(d, cfg)
    if not tc:
        return
    ckt = sha(d / "cut-selection.json")
    browse([dict(do="goto", path="/editor/tweak-board/?reel=tweak-send", **TWEAK_READY),
            {"do": "seek", "t": 1.0}, {"do": "click", "sel": '[data-add="cut"]'},
            {"do": "seek", "t": 1.5}, {"do": "click", "sel": '[data-add="cut"]'},
            {"do": "waitState", "board": "tweak-board", "js": "s.marks.length===1"},
            {"do": "click", "sel": "#send"}, {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"}],
           "tweak-send-1")
    sel = cs.load(d / "tweak-selection.json")
    m = (sel.get("marks") or [{}])[0]
    ck("tweak-send: tweak-selection.json is written with the one cut mark (1.0 -> 1.5 s)",
       len(sel.get("marks", [])) == 1 and m.get("type") == "cut" and abs(m.get("a", 0) - 1.0) < 0.02
       and abs(m.get("b", 0) - 1.5) < 0.02 and sel.get("reel") == "tweak-send", sel.get("marks"))
    ck("tweak-send: cut-selection.json is untouched", sha(d / "cut-selection.json") == ckt)
    out = browse([dict(do="goto", path="/editor/tweak-board/?reel=tweak-send", **TWEAK_READY),
                  {"do": "eval", "js": "JSON.stringify(S.marks)"}, {"do": "eval", "js": "document.querySelectorAll('#marks .mark').length"}],
                 "tweak-send-2")
    marks = json.loads(out["reads"][0]) if out["reads"] else []
    ck("tweak-send: a reload in a new browser restores the mark", len(marks) == 1 and marks[0].get("a") == m.get("a")
       and marks[0].get("b") == m.get("b") and out["reads"][1] == 1, marks)


def frames_of(cuts):
    return [(s["src_in_f"], s["src_out_f"]) for s in cuts.get("segments", [])]


# ---- G2-c: separate case preserves the existing tweak-send expectations ----
def case_tweak_fine_tune(S, a):
    d, cfg = reel("tweak-fine-tune")
    if not ready_cut(d, cfg):
        return
    out = browse([
        dict(do="goto", path="/editor/tweak-board/?reel=tweak-fine-tune", **TWEAK_READY),
        {"do": "seek", "t": 1.0}, {"do": "click", "sel": '[data-add="tight"]'},
        {"do": "waitFn", "js": "document.querySelector('#fine-pane .tp-rotv_b') !== null"},
        {"do": "click", "sel": '#fine-pane .tp-rotv_b'},
        {"do": "slider", "sel": '#fine-pane .tp-sldv', "fraction": 0.65},
        {"do": "eval", "js": "S.marks[0].a"},
        {"do": "click", "sel": '#send'},
        {"do": "waitText", "sel": '#saved', "re": "✓ Sent to Claude at |FAILED"},
    ], "tweak-fine-tune")
    marks = cs.load(d / "tweak-selection.json").get("marks", [])
    ck("Tweakpane slider travels through Tweak Send", bool(out["reads"]) and len(marks) == 1
       and marks[0]["a"] == out["reads"][0] and abs(marks[0]["a"] - 1.0) > 0.02, marks)


def case_roundtrip(S, a):
    d, cfg = reel("roundtrip")
    tc = ready_cut(d, cfg)
    if not tc:
        return
    w = d / "work"
    shutil.copyfile(w / "cuts.json", w / "cuts.cut-board.json")
    cuts0 = cs.load(w / "cuts.json")
    fps = cuts0["fps"]
    # the cut mark: exactly the cut-time span of L03's segments (L03 = the take-1 read of line 3)
    l3 = cfg["lines"][2]["attempts"][0]
    mine = [s for s in cuts0["segments"] if s["src_out_f"] / fps > l3["src_in"] and s["src_in_f"] / fps < l3["src_out"]]
    ta, tb = mine[0]["out_in_f"] / fps, mine[-1]["out_out_f"] / fps
    send = [{"do": "eval", "js": "document.getElementById('saved').textContent=''"}, {"do": "click", "sel": "#send"},
            {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"}]
    out = browse([dict(do="goto", path="/editor/tweak-board/?reel=roundtrip", **TWEAK_READY)] + send +
                 [{"do": "eval", "js": "fetch(BASE+'tweak-selection.json',{cache:'no-store'}).then(r=>r.text())"},
                  {"do": "seek", "t": round(ta, 3)}, {"do": "click", "sel": '[data-add="cut"]'},
                  {"do": "seek", "t": round(tb, 3)}, {"do": "click", "sel": '[data-add="cut"]'},
                  {"do": "waitState", "board": "tweak-board", "js": "s.marks.length===1"}] + send,
                 "roundtrip")
    if len(out["reads"]) != 3:
        return
    sel0, sel1 = d / "tweak-sent-0.json", d / "tweak-sent-1.json"   # next to tweak-board.config.json, which tweaks_to_edl reads
    sel0.write_text(out["reads"][1], encoding="utf-8")
    shutil.copyfile(d / "tweak-selection.json", sel1)
    ck("roundtrip: the first Tweak Send has no marks, the second one cut mark",
       cs.load(sel0).get("marks") == [] and len(cs.load(sel1).get("marks", [])) == 1)

    def again(sel):
        shutil.copyfile(w / "cuts.cut-board.json", w / "cuts.json")   # each pass maps through the cut it was made on
        p = script("tweaks_to_edl.py", sel, w)
        line, argv = printed(p.stdout)
        g = sh(argv, cwd=G["ws"]) if argv else None
        ok = p.returncode == 0 and g is not None and g.returncode == 0
        ck("roundtrip: tweaks_to_edl.py + its gaps.py command run (%s)" % sel.name, ok,
           (p.returncode, p.stderr[-300:], g and g.stderr[-300:]))
        # AE-2b (hub ruling H-STY-5): tweaks_to_edl now carries the reel's Cut Board pause default as one equal
        # --internal/--join pair (it used to fall back to gaps.py's 150 ms); it never copies --beat-join.
        pair = [argv[argv.index(k) + 1] if k in argv else None for k in ("--internal", "--join")]
        sent = cs.load(d / "cut-selection.json") if (d / "cut-selection.json").is_file() else {}
        ms = sent.get("gap_default_ms", cfg.get("gap_default_ms"))
        want = "%.3f" % (9.0 if ms is None else ms / 1000.0)
        ck("roundtrip: the printed command has --words, the cut's --speed and --beat, the reel's pause default as "
           "--internal/--join (%s s), and no --beat-join" % want, {"--words", "--speed", "--beat"} <= set(argv)
           and "--beat-join" not in argv and pair == [want, want], line)
        return cs.load(w / "cuts.json") if ok else {}
    cuts1 = again(sel0)
    f0, f1 = frames_of(cuts0), frames_of(cuts1)
    diff = [(x, y) for x, y in zip(cuts0.get("segments", []), cuts1.get("segments", [])) if x != y]
    ck("roundtrip: a Tweak Send with no marks gives back the cut's own cuts.json, byte for byte (every frame edge equal; "
       "%d vs %d segments, %d differ)" % (len(f0), len(f1), len(diff)),
       bool(cuts1) and (w / "cuts.json").read_bytes() == (w / "cuts.cut-board.json").read_bytes(), (diff[:3], f0, f1))
    cuts2 = again(sel1)
    if not cuts2:
        return
    m = cs.load(sel1)["marks"][0]
    # the mark's span in source time, through the cut's own frames
    cm = cs.module("make_tweaks.py").cut_map(cuts0)
    to_src = cs.module("tweaks_to_edl.py").to_src
    sa, sb = to_src(m["a"], cm, cuts0["speed"]), to_src(m["b"], cm, cuts0["speed"])
    kept = cs.kept_in(cuts2, sa, sb)

    def held(c):
        return [x["w"] for x in l3["words"] if any(s["src_in_f"] / fps <= x["s"] < s["src_out_f"] / fps for s in c.get("segments", []))]
    ck("roundtrip: a Tweak Send with one cut mark gives a cuts.json without that span (source %.3f-%.3f s: %.3f s kept; "
       "L03 words in the cut before %s, after %s)" % (sa, sb, kept, held(cuts0), held(cuts2)),
       bool(cuts2) and kept <= 1.0 / fps + 1e-6 and held(cuts0) and not held(cuts2))


def case_tweak_beat(S, a):
    """H-S4b-13: the Cut Board's beat (0.35 s) survives a Tweak Send whose mark touches a segment holding it."""
    d, cfg = reel("tweak-beat")
    tc = ready_cut(d, cfg, beat_ms=350)
    if not tc:
        return
    w = d / "work"
    cuts0 = cs.load(w / "cuts.json")
    fps, speed = cuts0["fps"], cuts0["speed"]
    plan0 = (w / "gap-plan.txt").read_text(encoding="utf-8")
    # a punctuation beat gaps.py cut down to the 350 ms beat: "cutN  <silence start>  <silence> -> 0.350  beat"
    hit = re.search(r"cut\d+\s+([\d.]+)\s+([\d.]+) ->\s+0\.350\s+beat\s", plan0)
    if not ck("tweak-beat: the cut planned a punctuation beat at the Cut Board's 350 ms (%s)"
              % (hit.group(0).strip() if hit else None), "beat: 350 ms" in plan0 and hit, plan0[:600]):
        return
    ga, gb = float(hit.group(1)), float(hit.group(1)) + float(hit.group(2))
    beat0 = cs.kept_in(cuts0, ga, gb)
    holding = [k for k, s in enumerate(cuts0["segments"]) if s["src_out_f"] / fps > ga and s["src_in_f"] / fps < gb]
    ck("tweak-beat: the cut keeps that beat at 0.350 s (+-1 frame: %.3f s of the %.3f-%.3f s silence, in segments %s)"
       % (beat0, ga, gb, holding), abs(beat0 - 0.35) <= 1.0 / fps + 1e-6 and holding)
    # the mark: a cut of one word in the last segment holding the beat, clear of the beat and of the segment's ends.
    # Word times are the edit map's start/end (what gaps.py reads). The mark runs 10 ms past each end and the word sits
    # 20 ms clear of both neighbours, so gaps.py's keep-whole-words rule has no reason to move the mark's edges.
    k = holding[-1]
    seg = cuts0["segments"][k]
    s_in, s_out = seg["src_in_f"] / fps, seg["src_out_f"] / fps
    ws = [x for x in cs.load(w / "edit_map.json")["words"] if x.get("status") != "unresolved"]
    word = next((x for i, x in enumerate(ws[1:-1], 1) if x["start"] >= max(gb, s_in) + 0.3 and x["end"] <= s_out - 0.3
                 and ws[i - 1]["end"] < x["start"] - 0.02 and ws[i + 1]["start"] > x["end"] + 0.02), None)
    if not ck("tweak-beat: segment %d (%.3f-%.3f s) has a word clear of the beat to cut (%s)"
              % (k, s_in, s_out, word and word["word"]), word):
        return
    to_cut = lambda t: seg["out_in_f"] / fps + (t - s_in) / speed
    sel = d / "tweak-selection.json"
    write(sel, dict(reel=d.name, version=tc["version"], speed=speed, marks=[dict(type="cut", a=round(to_cut(word["start"] - 0.01), 3),
                                                            b=round(to_cut(word["end"] + 0.01), 3))]))
    p = script("tweaks_to_edl.py", sel, w)
    line, argv = printed(p.stdout)
    g = sh(argv, cwd=G["ws"]) if argv else None
    if not ck("tweak-beat: tweaks_to_edl.py + its gaps.py command run", p.returncode == 0 and g is not None
              and g.returncode == 0, (p.returncode, p.stderr[-300:], g and g.stderr[-300:])):
        return
    beat = argv[argv.index("--beat") + 1] if "--beat" in argv else None
    holds = argv[argv.index("--hold") + 1].split(",") if "--hold" in argv else []
    ck("tweak-beat: the printed gaps.py command carries the Cut Board's beat (--beat %s) and holds every segment but "
       "the touched one (%d held of %d)" % (beat, len(holds), len(cuts0["segments"])),
       beat is not None and float(beat) == 0.35 and len(holds) == len(cuts0["segments"]) - 1
       and not any(abs(float(h.split(":")[0]) - s_in) < 1e-6 for h in holds), line)
    cuts1 = cs.load(w / "cuts.json")
    beat1 = cs.kept_in(cuts1, ga, gb)
    ck("tweak-beat: after the Tweak Send the beat is still 0.350 s (+-1 frame at %g fps: %.3f s, %d frames; not 0.300, "
       "not the 0.150 join cap)" % (fps, beat1, round(beat1 * fps)), abs(beat1 - 0.35) <= 1.0 / fps + 1e-6)
    ck("tweak-beat: the mark took '%s' (%.3f-%.3f s) out of the cut (%.3f s kept)"
       % (word["word"], word["start"], word["end"], cs.kept_in(cuts1, word["start"], word["end"])),
       cs.kept_in(cuts1, word["start"], word["end"]) <= 1.0 / fps + 1e-6)


def case_drift(S, a):
    d, cfg = reel("drift")
    tc = ready_cut(d, cfg)
    if not tc:
        return
    cp = d / "cut-board.config.json"
    orig = cp.read_bytes()
    cuts = cs.load(d / "work/cuts.json")
    k = cfg["lines"][2]["attempts"][0]["words"][1]["i"]   # a word of L03, by its index in take 1's board sequence

    def planted(where, ms):
        c = json.loads(orig)
        if where == "take":
            c["takes"]["1"]["words"][k]["start"] = round(c["takes"]["1"]["words"][k]["start"] + ms / 1000.0, 3)
        else:
            w = c["lines"][2]["attempts"][0]["words"][1]
            w["s"] = round(w["s"] + ms / 1000.0, 3)
        cp.write_text(json.dumps(c, indent=1), encoding="utf-8")
        return script("selection_to_edl.py", d / "cut-selection.json", cp)
    for where in ("take", "attempt"):
        p81, p79 = planted(where, 81), planted(where, 79)
        ck("drift: cut board, %s word time +81 ms: selection_to_edl exits 3 with one plain line (%s)"
           % (where, p81.stderr.strip()[-200:]), p81.returncode == 3 and len(p81.stderr.strip().splitlines()) == 1
           and "ms apart" in p81.stderr)
        ck("drift: cut board, %s word time +79 ms: selection_to_edl exits 0" % where, p79.returncode == 0, p79.stderr[-200:])
    cp.write_bytes(orig)
    tp = d / "tweak-board.config.json"
    torig = tp.read_bytes()
    write(d / "tweak-selection.json", {"reel": "drift", "version": "v1", "marks": []})
    # a word well inside its segment, so a planted shift stays in that segment
    fps = cuts["fps"]
    edges = [(s["out_in_f"] / fps, s["out_out_f"] / fps) for s in cuts["segments"]]
    j = next(i for i, x in enumerate(tc["words"]) if any(a0 + 0.15 < x["t"] < b0 - 0.15 for a0, b0 in edges))

    def tplanted(ms):
        c = json.loads(torig)
        c["words"][j]["t"] = round(c["words"][j]["t"] + ms / 1000.0, 3)
        tp.write_text(json.dumps(c), encoding="utf-8")
        return script("tweaks_to_edl.py", d / "tweak-selection.json", d / "work")
    p0 = script("tweaks_to_edl.py", d / "tweak-selection.json", d / "work")
    ck("drift: tweak board, as built: tweaks_to_edl exits 0", p0.returncode == 0, p0.stderr[-200:])
    p81, p79 = tplanted(81), tplanted(79)
    ck("drift: tweak board, word '%s' +81 ms: tweaks_to_edl exits 3 with one plain line (%s)"
       % (tc["words"][j]["w"], p81.stderr.strip()[-200:]), p81.returncode == 3 and len(p81.stderr.strip().splitlines()) == 1)
    ck("drift: tweak board, +79 ms: tweaks_to_edl exits 0", p79.returncode == 0, p79.stderr[-200:])
    tp.write_bytes(torig)


def case_gitignore(S, a):
    ws = S / "ws-gitignore"
    shutil.rmtree(ws, ignore_errors=True)
    check_deps.atomic_write(rt.config_path(ws), json.dumps({}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    gi = ws / "videos" / ".gitignore"
    gi.parent.mkdir(parents=True)
    gi.write_bytes(b"my-own-line\n")
    want = b"my-own-line\n" + "".join(x + "\n" for x in VIDEOS_IGNORE).encode()
    for n in (1, 2):
        p = sh([PY, "-X", "utf8", "-I", DOCTOR / "board_sync.py", "--root", ws], cwd=ws)
        got = gi.read_bytes()
        ck("gitignore: board_sync run %d keeps the user's line first and has the 3 lines once (%r)" % (n, got),
           p.returncode == 0 and got == want, (p.returncode, p.stdout[-200:], p.stderr[-200:]))
    ws2 = S / "ws-gitignore-novideos"
    shutil.rmtree(ws2, ignore_errors=True)
    check_deps.atomic_write(rt.config_path(ws2), json.dumps({}))
    assert check_deps.write_config(ws2, engine=None, nle="none")
    p = sh([PY, "-X", "utf8", "-I", DOCTOR / "board_sync.py", "--root", ws2], cwd=ws2)
    ck("gitignore: with no videos folder, board_sync creates neither the folder nor its .gitignore",
       p.returncode == 0 and not (ws2 / "videos").exists())
    shutil.rmtree(ws, ignore_errors=True)
    shutil.rmtree(ws2, ignore_errors=True)


def case_port(S, a):
    d, cfg = reel("port")
    old_cfg = d / "cut-board.config.old.json"
    shutil.copyfile(d / "cut-board.config.json", old_cfg)
    # the rebuilt board: take 2's recording gained a vocal event at its start, so every take-2 index moves by one
    m2 = cs.load(d / "work/edit_map.take2.json")
    m2["events"] = [{"id": "v_9999", "word": "[breath]", "start": 0.2, "end": 0.3, "why": "planted", "peak_db": -30.0}] + m2["events"]
    b = bem()
    m2["word_list_hash"] = b.word_list_hash(b.board_sequence(m2))
    write(d / "work/edit_map.take2.json", m2)
    p = script("make_board.py", "--script", d / "script.md",
               "--take", "1:%s:%s" % (d / "work/edit_map.json", d / "work/tx.16k.wav"),
               "--take", "2:%s:%s" % (d / "work/edit_map.take2.json", d / "work/tx.16k.wav"),
               "--shots", d / "shots.json", "--reel", "port", "-o", d)
    new = cs.load(d / "cut-board.config.json")
    ck("port: the rebuilt board (take 2 gained an event) builds", p.returncode == 0 and new.get("board_hash") != cfg["board_hash"],
       p.stderr[-300:])
    # L04 picked on take 1 (attempt 0); a word struck on its take-2 read (attempt 1, not picked)
    att = cfg["lines"][3]["attempts"][1]
    ck("port: L04's attempt 1 is its take-2 read", att["take"] == 2)
    old_i = att["words"][1]["i"]
    wid = cfg["takes"]["2"]["words"][old_i]["id"]
    want = next(w["i"] for w in new["lines"][3]["attempts"][1]["words"] if new["takes"]["2"]["words"][w["i"]]["id"] == wid)
    sel = selection(cfg)
    sel["lines"][3]["pick"], sel["lines"][3]["rm"] = 0, {"1": [old_i]}
    write(d / "old-selection.json", sel)

    def ported(root):
        out = d / "ported.json"
        out.unlink(missing_ok=True)
        q = script("port_selection.py", d / "old-selection.json", old_cfg, d / "cut-board.config.json", "-o", out, root=root)
        return q, (cs.load(out).get("lines") or [{}] * 4)[3].get("rm") if out.exists() else None
    q, rm = ported(SCRIPTS)
    ck("port: the struck take-2 word %s (index %d) maps to its new index %d" % (wid, old_i, want),
       q.returncode == 0 and rm == {"1": [want]} and want != old_i, (q.returncode, q.stderr[-300:], rm))
    mut = mirror(S, "mut-port")
    mp = mut / "skills/reel-first-cuts/scripts/port_selection.py"
    t = mp.read_text(encoding="utf-8")
    fix = "            otw_j, ntw_j = take_words(old, att_o), take_words(new, att_n)   # attempt j's own take, not the pick's\n"
    ck("port: the mutant swaps the per-attempt lookup for the picked attempt's take", t.count(fix) == 1)
    mp.write_text(t.replace(fix, "            otw_j, ntw_j = otw, ntw\n"), encoding="utf-8")
    q, rm = ported(mp.parent)
    ck("port: the mutant with the old lookup maps it wrongly (exit %d, rm %s)" % (q.returncode, rm),
       q.returncode != 0 or rm != {"1": [want]})
    shutil.rmtree(mut, ignore_errors=True)


def case_hub_roundtrip(S, a):
    d, cfg = reel("hub")
    refresh_hub()
    strike, wi = word_click(cfg, 2, 0, 1)
    out = browse([{"do": "goto", "path": "/editor/hub/?reel=hub", "waitFn": "window.Hub && Hub.ready"},
                  {"do": "eval", "js": "[...document.querySelectorAll('.tabs [role=tab]')].map(b=>b.textContent)"},
                  {"do": "click", "sel": "#tab-cut-board"},
                  dict(do="frame", sel=".frame iframe", **CUT_READY),
                  {"do": "eval", "js": "document.getElementById('beat').value"},
                  {"do": "click", "sel": '[data-drop="5"]'}, {"do": "click", "sel": strike},
                  {"do": "set", "sel": "#beat", "value": "0.35"},
                  {"do": "waitState", "board": "cut-board", "js": "s.beat_ms===350 && s.lines[5].drop===true"},
                  {"do": "click", "sel": "#send"}, {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"},
                  {"do": "top"}, {"do": "eval", "js": "document.querySelector('.frame iframe').getAttribute('src')"}],
                 "hub-roundtrip-1")
    r = out["reads"]
    if not ck("hub-roundtrip: the page answered every read", len(r) == 3, r):
        return
    order = [TABS[k][0] for k in sorted(TABS, key=lambda k: TABS[k][2])] + ["Master review"]
    ck("hub-roundtrip: the host page's tab strip is built from boards.json tab, sorted by order (%s)" % r[0], r[0] == order)
    ck("hub-roundtrip: the Cut Board opened in the frame at /editor/cut-board/?reel=hub, its pause-after-commas starting at "
       "the workspace's 0.28 s", r[2] == "/editor/cut-board/?reel=hub" and r[1] == "0.28", r[1:])
    sel = cs.load(d / "cut-selection.json")
    ck("hub-roundtrip: cut-selection.json has beat_ms 350, the drop and the strike",
       sel.get("beat_ms") == 350 and sel["lines"][5]["drop"] and sel["lines"][2]["rm"].get("0") == [wi],
       (sel.get("beat_ms"), sel.get("lines", [{}] * 6)[5]))
    p, g, argv = cut(d, d / "cut-selection.json")
    beat = argv[argv.index("--beat") + 1] if "--beat" in argv else None
    ck("hub-roundtrip: selection_to_edl prints gaps.py with --words and --beat 0.35 (%s), and it runs"
       % beat, p.returncode == 0 and "--words" in argv and beat is not None and float(beat) == 0.35
       and g is not None and g.returncode == 0, (p.stderr[-300:], g and g.stderr[-300:]))
    plan = (d / "work/gap-plan.txt").read_text(encoding="utf-8") if (d / "work/gap-plan.txt").exists() else ""
    ck("hub-roundtrip: gaps.py planned with the 350 ms beat", "beat: 350 ms" in plan, plan[:300])
    master = tiny(d)
    if not master:
        return
    tc = tweaks(d, master)
    cuts = cs.load(d / "work/cuts.json")
    dur = cuts["segments"][-1]["out_out_f"] / cuts["fps"]
    refresh_hub()
    out = browse([{"do": "goto", "path": "/editor/hub/?reel=hub", "waitFn": "window.Hub && Hub.ready"},
                  {"do": "click", "sel": "#tab-tweak-board"},
                  dict(do="frame", sel=".frame iframe", **TWEAK_READY),
                  {"do": "eval", "js": "JSON.stringify({d: document.getElementById('v').duration, src: document.getElementById('v').currentSrc, "
                                       "words: C.words, title: document.getElementById('title').textContent})"},
                  {"do": "click", "sel": "#send"}, {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"}],
                 "hub-roundtrip-2")
    v = json.loads(out["reads"][0]) if out["reads"] else {}
    ck("hub-roundtrip: the Tweak Board tab shows the new cut: video %s, duration %.3f s vs the last out_out_f/fps %.3f s "
       "(within half a frame)" % (v.get("src", "")[-40:], v.get("d") or -1, dur),
       v.get("src", "").endswith("/videos/hub/work/renders/master-tiny.mp4") and v.get("d") is not None
       and abs(v["d"] - dur) <= 0.5 / cuts["fps"], v.get("d"))
    ck("hub-roundtrip: the Tweak Board lists the cut's words (%d)" % len(v.get("words") or []),
       bool(v.get("words")) and v.get("words") == tc.get("words"))
    sel = cs.load(d / "tweak-selection.json")
    ck("hub-roundtrip: Send inside the hub wrote tweak-selection.json", sel.get("reel") == "hub" and "marks" in sel)


def case_tabs(S, a):
    raw = (DOCTOR / "boards.json").read_text(encoding="utf-8")
    boards = json.loads(raw)["boards"]
    for k, (label, stages, order) in TABS.items():
        ck("tabs: %s has tab %s / %s / %d" % (k, label, stages, order),
           boards.get(k, {}).get("tab") == {"label": label, "stages": stages, "order": order}, boards.get(k, {}).get("tab"))
    ck("tabs: the hub board has no tab (it is the host)", "tab" not in boards.get("hub", {"tab": 1}))
    ck("tabs: the sound-board entry is S5's, byte for byte", SOUND_LINE in raw)
    ck("tabs: cut-board writes only cut-selection.json, tweak-board only tweak-selection.json",
       boards["cut-board"]["writes"] == ["cut-selection.json"] and boards["tweak-board"]["writes"] == ["tweak-selection.json"])
    port = server()
    d = G["videos"] / "tabs"
    d.mkdir(exist_ok=True)
    bad = []
    for k in boards:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("POST", "/videos/tabs/__state?name=" + k, body=b'{"v": 1}',
                  headers={"Origin": "http://127.0.0.1:%d" % port, "Content-Type": "application/json"})
        st = c.getresponse().status
        c.close()
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", "/editor/%s/index.html" % k)
        gt = c.getresponse().status
        c.close()
        built = (PLUGIN / boards[k]["template"]).is_dir()
        copy = (G["ws"] / "editor" / k / "index.html").is_file()   # board_sync installs the real hub too
        if st != 200 or not (d / (k + ".state.json")).is_file() or gt != (200 if copy else 404) or (built and not copy):
            bad.append((k, st, gt, built, copy))
    ck("tabs: board_server serves every built board and saves every board's state with the tab key in boards.json "
       "(%d boards, %d built)" % (len(boards), sum((PLUGIN / b["template"]).is_dir() for b in boards.values())), not bad, bad)
    exe = getattr(sys, "_base_executable", sys.executable)   # the venv launcher's pid is not the server's
    p = sh([exe, "-X", "utf8", "-I", HERE / "test_board_server.py"], cwd=HERE.parents[1], timeout=140)
    ck("tabs: test_board_server.py passes (%s)" % p.stdout.strip()[-60:], p.returncode == 0 and "ok test_board_server.py" in p.stdout,
       (p.stdout[-300:], p.stderr[-600:]))


def case_offline(S, a):
    d, cfg = reel("offline")
    if not ready_cut(d, cfg):
        return
    out = browse([dict(do="goto", path="/editor/cut-board/?reel=offline", **CUT_READY),
                  {"do": "click", "sel": '[data-play="0:0"]'}, {"do": "sleep", "ms": 500},
                  dict(do="goto", path="/editor/tweak-board/?reel=offline", **TWEAK_READY),
                  {"do": "eval", "js": "document.getElementById('v').play().then(()=>new Promise(r=>setTimeout(r,500))).then(()=>true,()=>true)"}],
                 "offline")
    base = "http://127.0.0.1:%d/" % G["port"]
    req = out.get("requests", [])
    inline = [u for u in req if u.startswith(("data:", "blob:"))]   # in-page (the video controls' own icons), no network
    outside = [u for u in req if not u.startswith(base) and u not in inline]
    for page, f in (("cut-board", "cut-board.config.json"), ("tweak-board", "tweak-board.config.json")):
        ck("offline: the %s page loaded board-client.js and %s from the board server" % (page, f),
           base + "editor/%s/board-client.js" % page in req and any(u.startswith(base + "videos/offline/" + f) for u in req))
    ck("offline: both pages made %d requests (%d inline data:/blob:), none outside 127.0.0.1 (%s)"
       % (len(req), len(inline), [u[:80] for u in outside[:3]]), req and not outside)
    ck("offline: no page error", not out.get("errors"), out.get("errors"))


CASES = {"import": case_import, "cut-send": case_cut_send, "cut-reload": case_cut_reload, "all-take": case_all_take,
         "tweak-send": case_tweak_send, "roundtrip": case_roundtrip, "tweak-beat": case_tweak_beat, "drift": case_drift, "gitignore": case_gitignore,
         "port": case_port, "hub-roundtrip": case_hub_roundtrip, "tabs": case_tabs, "offline": case_offline}
CASES["tweak-fine-tune"] = case_tweak_fine_tune
CASES["tweak-silence"] = case_tweak_silence


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    setup(S)
    print("python %s\nffmpeg %s\nHOME %s" % (PY, shutil.which("ffmpeg"), G["env"]["HOME"]))
    state_json = Path(rt.state_dir()) / "state.json"
    before = sha(state_json)
    try:
        for name in [a.case] if a.case else list(CASES):
            t0 = time.time()
            print("-- %s" % name)
            CASES[name](S, a)
            print("   (%s: %.0f s)" % (name, time.time() - t0))
    finally:
        if G.get("server"):
            G["server"].kill()
            G["server"].wait(10)
            G["server"].stdout.close()
        for sub in ("profiles", "fixtures"):
            shutil.rmtree(S / sub, ignore_errors=True)
        for f in G["videos"].glob("*/work/renders/*.mp4"):
            f.unlink()
        for f in G["videos"].glob("*/work/tx.16k.wav"):
            f.unlink()
    ck("state.json sha256 unchanged (%s, %s)" % (before[:12], state_json), sha(state_json) == before)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
