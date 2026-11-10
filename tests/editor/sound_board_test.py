"""S5 done-test (part B): the Sound Board end to end through the board server, plus the ways it must refuse.

  EDITOR_SE_HOME=<state> python -X utf8 -I tests/editor/sound_board_test.py [--case <name>]

<state> is an installed editor state folder (node, chrome-headless-shell, puppeteer-core, ffmpeg); it is only read.
Cases: send, reload, reject_all, reset, writes_guard, tips, hub_tab, music, beat_sync, voice_only (default: all). Each case builds its own reel
by hand (config.json, waveforms.json, a tiny mp4) and opens its own browser, so any one can run alone.
Prints one "✓ <case>" / "✗ <case>: <why>" line per case, then "N passed, M failed". Exit 0 only when all pass.
"""
import argparse, http.client, json, os, shutil, socket, subprocess, sys, tempfile, threading
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
DOCTOR = PLUGIN / "skills/editor-doctor/scripts"
sys.path.insert(0, str(PLUGIN / "skills/_shared"))
sys.path.insert(0, str(DOCTOR))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)

SERVER = DOCTOR / "board_server.py"
CLICK = Path(__file__).resolve().parent / "sound_board_click.js"
DUR = 3.0
LIBRARY = [{"file": "tick.wav", "duration": 0.3, "peak_dbfs": -3.0, "rms_dbfs": -20.0},
           {"file": "long-swoosh.wav", "duration": 2.4, "peak_dbfs": -2.0, "rms_dbfs": -18.0}]
CUES = [{"id": "c01", "beat": "Opening hit", "short": "hit", "why": "the first word", "time": 0.5, "candidates": ["tick.wav"]},
        {"id": "c02", "beat": "Second tick", "short": "tick", "why": "the list starts", "time": 0.8, "candidates": ["tick.wav"]},
        {"id": "c03", "beat": "Closer", "short": "end", "why": "the last line", "time": 2.0, "candidates": ["long-swoosh.wav"]}]
PAYLOAD_KEYS = {"project", "picture", "fps", "latency_ms", "bed", "unassigned", "cues", "rejected", "undecided",
                "music_request"}
ROW = "#cuebody tr.cuerow:nth-child(%d)"
LINE = "#musiclist .mline:nth-child(%d)"
# board bed rows, the shape new_board.py writes into config.json beds[]
BEDS = [{"file": "pack-bed.wav", "duration": 4.0, "peak_dbfs": -3.0, "rms_dbfs": -18.0, "lufs": -16.0, "title": "Pack Bed",
         "mood": "calm", "origin": "pack", "licence_ok": True, "rights_confirmed": True, "suggest_entry_s": 0.5},
        {"file": "my-track.wav", "duration": 4.0, "peak_dbfs": -3.0, "rms_dbfs": -18.0, "lufs": -16.0, "title": "My Track",
         "mood": "upbeat", "origin": "own", "licence_ok": True, "rights_confirmed": False, "suggest_entry_s": 1.5,
         "play_lufs": -14.0}]
KEEP, REJ = ROW + " td:last-child > button:nth-child(1)", ROW + " td:last-child > button:nth-child(2)"
# beat_sync: the shapes new_board.py writes (beds[i].grid, library[i].peak_s), built by hand to the shared interface
GRID = {"bpm": 120.0, "period_s": 0.5, "phase_s": 0.12, "downbeat_s": 0.12, "confidence": 0.95}
SYNC_LIB = [{"file": "tick.wav", "duration": 0.5, "peak_dbfs": -3.0, "rms_dbfs": -20.0, "peak_s": 0.25},
            {"file": "long-swoosh.wav", "duration": 2.4, "peak_dbfs": -2.0, "rms_dbfs": -18.0}]
SYNC_BEDS = [dict(BEDS[0], file="grid-bed.wav", title="Grid Bed", duration=8.0, suggest_entry_s=0.5, grid=GRID),
             dict(BEDS[0], file="flat-bed.wav", title="Flat Bed", duration=8.0, suggest_entry_s=0.5, grid=None)]
# entry 0 with the offset on a beat puts the reel beats on k * 0.5 s: c01 sits 0.03 s after one (inside the
# min(period/8, 80 ms) = 62.5 ms window), c02 0.2 s after one (outside), c03 exactly on one
SYNC_CUES = [{"id": "c01", "beat": "Hit", "short": "hit", "why": "near a beat", "time": 1.03, "candidates": ["tick.wav"]},
             {"id": "c02", "beat": "Off", "short": "off", "why": "between beats", "time": 1.7, "candidates": ["long-swoosh.wav"]},
             {"id": "c03", "beat": "On", "short": "on", "why": "on a beat", "time": 2.0, "candidates": ["long-swoosh.wav"]}]


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


def run(args, env=None):
    return subprocess.run(args, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1), encoding="utf-8")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    ensure_utf8_output()
    names = ["send", "reload", "reject_all", "reset", "writes_guard", "tips", "hub_tab", "music", "beat_sync", "carve", "voice_only"]
    ap = argparse.ArgumentParser(description="Sound Board done-test")
    ap.add_argument("--case", choices=names + ["all"], default="all")
    pick = ap.parse_args().case
    want = names if pick == "all" else [pick]
    tools, missing = find_tools()
    if missing:
        print(f"✗ This test needs an installed editor state: set EDITOR_SE_HOME to one (missing: {', '.join(missing)})")
        return 1
    scratch = Path(tempfile.mkdtemp(prefix="s5_sound_board_"))
    env = dict(os.environ, HOME=str(scratch), USERPROFILE=str(scratch))
    ws = scratch / "ws"
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": free_port()}}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    videos = ws / rt.read_config(ws)["paths"]["videos"]
    videos.mkdir(parents=True, exist_ok=True)
    mp4 = scratch / "locked.mp4"
    S = {"server": None, "port": None, "browsers": 0}
    procs, results = [], []

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
        p = subprocess.Popen([sys.executable, "-X", "utf8", "-I", str(SERVER), "--root", str(ws)], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        procs.append(p)
        t = threading.Timer(20, p.kill)  # a hung start fails the case instead of blocking the test
        t.start()
        line = p.stdout.readline().strip()
        t.cancel()
        need(line.startswith("Editor boards: http://127.0.0.1:") and line.endswith("/"), f"server said {line!r}")
        S["server"], S["port"] = p, int(line.rsplit(":", 1)[1].rstrip("/"))
        return S["port"]

    def reel(name, **extra):
        """A minimal reel, by hand: the config keys the board reads, waveforms, a tiny mp4 under media/."""
        if not mp4.exists():
            p = run([tools["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=160x284:d={DUR}:r=30",
                     "-f", "lavfi", "-i", f"sine=f=440:d={DUR}", "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(mp4)])
            need(p.returncode == 0, f"ffmpeg could not make the test video: {p.stderr.strip()[-300:]}")
        d = videos / name
        (d / "media").mkdir(parents=True)
        shutil.copyfile(mp4, d / "media/locked.mp4")
        cfg = {"board_name": "Test reel sound", "project_key": name, "blurb": "Test board.", "picture": "locked.mp4",
               "picture_url": "media/locked.mp4", "fps": 30, "dur": DUR, "library": LIBRARY, "beds": [], "cues": CUES}
        cfg.update(extra)
        write_json(d / "config.json", cfg)
        write_json(d / "waveforms.json", {"bins_per_s": 20, "voice": {"peaks": [0.5] * 60, "duration": DUR}, "beds": {}})
        return d

    def browse(reel_name, actions, page="editor/sound-board/", viewport=None):
        """A NEW browser (fresh profile, so nothing comes from this browser's storage) runs the actions."""
        port = server()
        if page == "editor/hub/":
            # Refresh after creating each reel, including when the server is already running.
            for name in ("board_sync.py", "hub_rows.py"):
                p = run([sys.executable, "-X", "utf8", "-I", "-B", str(DOCTOR / name), "--root", str(ws)], env=env)
                need(p.returncode == 0, f"hub setup {name}: {p.stdout} {p.stderr}")
        S["browsers"] += 1
        job = scratch / f"job-{S['browsers']}.json"
        write_json(job, {"url": f"http://127.0.0.1:{port}/{page}?reel={reel_name}",
                         "userDataDir": str(scratch / f"profile-{S['browsers']}"), "actions": actions, "viewport": viewport})
        p = run([tools["node"], str(CLICK), tools["pup"], tools["chrome"], str(job)])
        try:
            out = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            out = {}
        need(p.returncode == 0, f"browser: {out.get('error') or p.stderr.strip()[-500:]}; "
                                f"page showed {json.dumps(out.get('last'))[:600]}; page errors {out.get('errors')}")
        need(not out["errors"], f"page errors {out['errors']}")
        return out

    def states(read):
        return [r["state"] for r in read["rows"]]

    def disk_states(doc):
        return [c.get("state") for c in sorted(doc["cues"], key=lambda c: c["id"])]

    # ---- cases ----
    def c_voice_only():
        (videos / "voice-only-reel").mkdir()
        read = browse("voice-only-reel", [{"do": "goto", "noRows": True},
                     {"do": "waitTrue", "js": "document.querySelector('h1')?.textContent === 'No sound cues for this reel'"},
                     {"do": "eval", "js": "document.dispatchEvent(new KeyboardEvent('keydown', {key: ' '}))"},
                     {"do": "eval", "js": "({heading: document.querySelector('h1').innerText, text: document.body.innerText})"}])["reads"][-1]
        need(read["heading"] == "No sound cues for this reel", f"heading: {read['heading']}")
        need(all(s not in read["text"] for s in ("404", "HTTP", "config.json")), f"raw error shown: {read['text']}")
        need("voice only" in read["text"] and "Claude" in read["text"], f"missing next step: {read['text']}")

    def c_send():
        d = reel("send-reel")
        cfg = load(d / "config.json")
        cfg["cues"][0]["beat"] = "Keep one clip with the full cue name visible"
        cfg["cues"][0]["why"] = "Three words must never be clipped at the start of the cue name. " * 3
        write_json(d / "config.json", cfg)
        narrow = browse("send-reel", [{"do": "goto"}, {"do": "eval", "js": """(() => {
            const panels = [...document.querySelectorAll('.leftcol,.panel')];
            const cue = document.querySelector('#cuebody .beat'), why = cue.querySelector('small');
            const cell = cue.closest('td').getBoundingClientRect();
            const range = document.createRange(); range.selectNodeContents(cue);
            const r = range.getBoundingClientRect();
            return {width:innerWidth, pageFits:document.documentElement.scrollWidth <= innerWidth,
              panelsFit:panels.every(e=>e.scrollWidth <= e.clientWidth),
              name:cue.firstChild.textContent, nameFits:r.left >= cell.left && r.right <= cell.right,
              whyFits:why.scrollHeight <= why.clientHeight};
        })()"""}], viewport={"width": 1024, "height": 768})["reads"][-1]
        need(narrow == {"width": 1024, "pageFits": True, "panelsFit": True,
             "name": cfg["cues"][0]["beat"], "nameFits": True, "whyFits": True},
             f"Sound Board panels and full cue names must fit at 1024: {narrow}")
        browse("send-reel", [{"do": "goto"}, {"do": "click", "sel": KEEP % 1}, {"do": "waitSaved"},
                             {"do": "click", "sel": "#send"}, {"do": "waitSent"}])
        sel = d / "sound-selection.json"
        need(sel.is_file(), "no sound-selection.json")
        need(not (d / "selection.json").exists(), "a selection.json was written too")
        doc = load(sel)
        need(set(doc) == PAYLOAD_KEYS, f"payload keys {sorted(doc)}")
        need([c["id"] for c in doc["cues"]] == ["c01"], f"cues sent: {doc['cues']}")
        need(doc["cues"][0]["file"] == "tick.wav" and doc["cues"][0]["gain_db"] == 2.0, f"c01 sent as {doc['cues'][0]}")
        need([u["id"] for u in doc["undecided"]] == ["c02", "c03"], f"undecided sent: {doc['undecided']}")
        need(doc["rejected"] == [] and doc["unassigned"] == [], f"rejected {doc['rejected']}, unassigned {doc['unassigned']}")
        need(doc["fps"] == 30 and doc["picture"] == "locked.mp4", f"fps {doc['fps']}, picture {doc['picture']!r}")

    def c_reload():
        d = reel("reload-reel")
        browse("reload-reel", [{"do": "goto"}, {"do": "click", "sel": KEEP % 1}, {"do": "click", "sel": REJ % 3},
                               {"do": "waitSaved"}])
        need((d / "sound-board.state.json").is_file(), "no sound-board.state.json on disk")
        r = browse("reload-reel", [{"do": "goto"}, {"do": "read"}])["reads"][0]
        need(states(r) == ["keep", None, "rej"], f"after a reload in a new browser the rows show {states(r)}")

    def c_reject_all():
        d = reel("rej-reel")
        out = browse("rej-reel", [
            {"do": "goto"}, {"do": "click", "sel": KEEP % 1}, {"do": "waitSaved"},
            {"do": "dialog", "accept": False}, {"do": "click", "sel": "#rejall"}, {"do": "sleep", "ms": 900},
            {"do": "read"}, {"do": "fetchState"},
            {"do": "dialog", "accept": True}, {"do": "click", "sel": "#rejall"}, {"do": "waitSaved"},
            {"do": "read"}, {"do": "fetchState"}])
        r1, s1, r2, s2 = out["reads"]
        need(len(out["dialogs"]) == 2, f"confirm asked {len(out['dialogs'])} times: {out['dialogs']}")
        need(states(r1) == ["keep", None, None] and disk_states(s1) == ["keep", None, None],
             f"after Cancel: rows {states(r1)}, disk {disk_states(s1)}")
        need(states(r2) == ["rej"] * 3 and disk_states(s2) == ["rej"] * 3, f"after OK: rows {states(r2)}, disk {disk_states(s2)}")
        need(disk_states(load(d / "sound-board.state.json")) == ["rej"] * 3, "the state file is not all rejected")

    def c_reset():
        reel("reset-reel")
        out = browse("reset-reel", [
            {"do": "goto"}, {"do": "click", "sel": KEEP % 1}, {"do": "click", "sel": REJ % 2},
            {"do": "gain", "row": 3, "db": 6}, {"do": "waitSaved"},
            {"do": "dialog", "accept": False}, {"do": "click", "sel": "#reset"}, {"do": "sleep", "ms": 900},
            {"do": "read"}, {"do": "fetchState"},
            {"do": "dialog", "accept": True}, {"do": "click", "sel": "#reset"}, {"do": "waitSaved"},
            {"do": "read"}, {"do": "fetchState"}])
        r1, s1, r2, s2 = out["reads"]
        need(len(out["dialogs"]) == 2, f"confirm asked {len(out['dialogs'])} times: {out['dialogs']}")
        need(states(r1) == ["keep", "rej", None] and r1["rows"][2]["gain"] == "6", f"after Cancel: rows {r1['rows']}")
        need(disk_states(s1) == ["keep", "rej", None], f"after Cancel the disk shows {disk_states(s1)}")
        need(states(r2) == [None] * 3 and disk_states(s2) == [None] * 3, f"after OK: rows {states(r2)}, disk {disk_states(s2)}")
        need(r2["rows"][2]["gain"] == "1", f"after OK the closer's gain is {r2['rows'][2]['gain']}, not the seeded 1")

    def c_writes_guard():
        boards = load(DOCTOR / "boards.json")["boards"]
        need(boards["sound-board"]["writes"] == ["sound-selection.json"], f"boards.json writes {boards['sound-board']['writes']}")
        d = reel("guard-reel")
        port = server()

        def post(name):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            c.request("POST", f"/videos/guard-reel/__save?board=sound-board&name={name}", body=b'{"v": 1}',
                      headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"})
            status = c.getresponse().status
            c.close()
            return status
        need(post("selection.json") == 403, "a __save of selection.json for sound-board was not refused with 403")
        need(not (d / "selection.json").exists(), "selection.json was written")
        need(post("sound-selection.json") == 200 and (d / "sound-selection.json").is_file(),
             "the control __save of sound-selection.json did not write")

    def c_tips():
        reel("tips-reel", speech_spans=[{"start_s": 1.8, "end_s": 2.6}])
        out = browse("tips-reel", [{"do": "goto"}, {"do": "read"}, {"do": "click", "sel": KEEP % 1},
                                   {"do": "click", "sel": "#send"}, {"do": "waitSent"}])
        tips = [r["tips"] for r in out["reads"][0]["rows"]]
        need(any("doubled" in t for t in tips[0]) and any("doubled" in t for t in tips[1]), f"doubled tips {tips[:2]}")
        need(any("long swooshes" in t for t in tips[2]) and any("over speech" in t for t in tips[2]), f"closer tips {tips[2]}")
        need(not any("long swooshes" in t or "over speech" in t for t in tips[0] + tips[1]), f"stray tips {tips[:2]}")

    def c_hub_tab():
        d = reel("hub-reel")
        out = browse("hub-reel", [
            {"do": "goto", "noRows": True}, {"do": "waitTrue", "js": "window.Hub && Hub.ready"},
            {"do": "click", "sel": "#tab-sound-board"},
            {"do": "frame", "sel": ".frame iframe"},
            {"do": "gain", "row": 1, "db": 5}, {"do": "click", "sel": KEEP % 1},
            {"do": "click", "sel": (ROW % 1) + " button.nudge:nth-child(4)"}, {"do": "waitSaved"},
            {"do": "click", "sel": "#send"}, {"do": "waitSent"}, {"do": "read"}], page="editor/hub/")
        need(not out["reads"][0]["gone"], "the board showed its server-gone banner inside the hub")
        sel = d / "sound-selection.json"
        need(sel.is_file(), "no sound-selection.json after Send inside the hub tab")
        cue = (load(sel)["cues"] or [{}])[0]
        need((cue.get("id"), cue.get("gain_db"), cue.get("time")) == ("c01", 5.0, 0.6),
             f"c01 sent as {cue} (wanted gain +3 dB to 5.0 and time +100 ms to 0.6)")
        st = load(d / "sound-board.state.json")
        c01 = next(c for c in st["cues"] if c["id"] == "c01")
        need((c01["gain"], c01["time"], c01["state"]) == (5, 0.6, "keep"), f"state file has c01 {c01}")

    def c_music():
        reel("nomusic-reel")
        r0 = browse("nomusic-reel", [{"do": "goto"}, {"do": "read"}])["reads"][0]["music"]
        need(r0["lines"] == [] and r0["empty"] == "No music yet. Add a free track or use your own.", f"empty list shows {r0}")
        d = reel("music-reel", beds=BEDS, voice_lufs=-12.0, speech_spans=[{"start_s": 0.4, "end_s": 1.2}])
        labels = browse("music-reel", [{"do": "goto"},
            {"do": "eval", "js": "({track: document.querySelector('#bedsel option[value]').nextElementSibling.textContent, text: document.body.innerText, level: getComputedStyle(document.getElementById('bedvol')).display})"},
            {"do": "eval", "js": "localStorage.setItem('editor-controls', 'advanced'); BoardClient.controls.apply(); document.querySelector('#bedsel option[value]').nextElementSibling.textContent"},
            {"do": "eval", "js": "localStorage.setItem('editor-controls', 'simple'); BoardClient.controls.apply(); document.querySelector('#bedsel option[value]').nextElementSibling.textContent"}])["reads"]
        need(labels[0]["track"] == "Pack Bed (4 s)" and labels[0]["level"] != "none", f"simple controls: {labels[0]}")
        need("LUFS" not in labels[0]["text"] and "dB" not in labels[0]["text"], f"simple readouts: {labels[0]['text']}")
        need("LUFS" in labels[1] and labels[2] == "Pack Bed (4 s)", f"mode changes: {labels[1:]}")
        (d / "beds").mkdir()
        for b in BEDS:  # real files, so the preview decodes and plays
            p = run([tools["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=4", "-ac", "2",
                     str(d / "beds" / b["file"])])
            need(p.returncode == 0, f"ffmpeg could not make {b['file']}: {p.stderr.strip()[-300:]}")
        own = LINE % 2
        tab = [{"do": "goto", "noRows": True}, {"do": "waitTrue", "js": "window.Hub && Hub.ready"},
               {"do": "click", "sel": "#tab-sound-board"}, {"do": "frame", "sel": ".frame iframe"}]
        out = browse("music-reel", tab + [
            {"do": "read"},
            {"do": "click", "sel": own + " button.muse"},
            {"do": "click", "sel": own + " button.mplay"}, {"do": "waitFor", "sel": own + " button.mplay.on"},
            {"do": "click", "sel": own + " button.mplay"}, {"do": "waitNone", "sel": "button.mplay.on"},
            {"do": "set", "sel": "#bedvol", "value": -20}, {"do": "set", "sel": "#bedduck", "value": 8},
            {"do": "click", "sel": own + " input.mrights"}, {"do": "click", "sel": "#mfree"}, {"do": "waitSaved"},
            {"do": "click", "sel": "#send"}, {"do": "waitSent"}, {"do": "read"}], page="editor/hub/")
        m0, m1 = out["reads"][0]["music"], out["reads"][1]["music"]
        need(len(m0["lines"]) == 2 and all(k in m0["lines"][0] for k in ("Pack Bed", "calm", "0:04", "Starter pack"))
             and all(k in m0["lines"][1] for k in ("My Track", "upbeat", "Your track", "I have the rights")),
             f"music lines {m0['lines']}")
        need((m0["vol"], m0["duck"], m0["ticks"]) == ("-18", "6", [False]), f"defaults level {m0['vol']}, dip {m0['duck']}, ticks {m0['ticks']}")
        want = (-12.0 - BEDS[1]["play_lufs"]) + -20  # (voice LUFS - LUFS of the stretch that plays) + level = -18
        need(abs(m1["gainDb"] - want) < 1e-9, f"bed preview gain {m1['gainDb']} dB, wanted {want}")
        need(m1["request"] == ["mfree"] and "Press Send" in (m1["note"] or ""), f"request {m1['request']}, note {m1['note']!r}")
        doc = load(d / "sound-selection.json")
        need(set(doc) == PAYLOAD_KEYS, f"payload keys {sorted(doc)}")
        bed = doc["bed"]
        got = (bed["file"], bed["gain_db"], bed["duck_db"], bed["rights_confirmed"], bed["offset_s"], bed["entry_s"],
               doc["music_request"])
        need(got == ("my-track.wav", -20, 8, True, 1.5, 0, "free"),
             f"sent (file, gain_db, duck_db, rights_confirmed, offset_s, entry_s, music_request) = {got}")
        need([u["id"] for u in doc["undecided"]] == ["c01", "c02", "c03"], f"undecided sent: {doc['undecided']}")
        r = browse("music-reel", tab + [{"do": "read"}, {"do": "dialog", "accept": True}, {"do": "click", "sel": "#reset"},
                                        {"do": "waitSaved"}, {"do": "read"}], page="editor/hub/")["reads"]
        back, reset = r[0]["music"], r[1]["music"]
        got = (back["bed"], back["vol"], back["duck"], back["offset"], back["entry"], back["ticks"], back["request"])
        need(got == ("my-track.wav", "-20", "8", "1.50", "0.00", [True], ["mfree"]), f"after a reload the picks show {got}")
        got = (reset["bed"], reset["vol"], reset["duck"], reset["ticks"], reset["request"])
        need(got == ("", "-18", "6", [False], []), f"after reset the music shows {got}")

    def c_carve():
        frequencies = (160, 400, 630, 1000, 1600, 2500)
        data = {"profiles": {"0.80": {
            "strength": 0.8,
            "bands": [{"freq": f, "q": 2.06, "gainDb": -14.8 if f == 1600 else -7.4} for f in frequencies],
            "points": [{"freq": f, "points": [{"t": 0, "v": 0}, {"t": 0.2, "v": -8},
                                              {"t": 2, "v": -8}, {"t": 4, "v": 0}]} for f in frequencies]}}}
        d = reel("carve-reel", beds=BEDS, carve=data)
        (d / "beds").mkdir()
        p = run([tools["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=1600:d=4", "-ac", "2",
                 str(d / "beds" / BEDS[0]["file"])])
        need(p.returncode == 0, p.stderr[-300:])
        reads = browse("carve-reel", [{"do": "goto"}, {"do": "read"},
            {"do": "click", "sel": LINE % 1 + " button.muse"},
            {"do": "set", "sel": "#carvestrength", "value": 0.8},
            {"do": "waitSaved"}, {"do": "click", "sel": "#send"}, {"do": "waitSent"}, {"do": "read"}])["reads"]
        need(reads[0]["music"]["carve"] == {"on": True, "strength": 0.8, "visible": True, "preview": True},
             f"carve defaults: {reads[0]['music']['carve']}")
        need(load(d / "sound-selection.json")["bed"]["carve"] == {"on": True, "strength": 0.8}, "Send lost on/strength")
        need(load(d / "sound-board.state.json")["bed"]["carve"] == {"on": True, "strength": 0.8}, "save lost on/strength")
        reads = browse("carve-reel", [{"do": "goto"}, {"do": "read"},
            {"do": "eval", "js": "window.CARVE_FILTERS = []; var ac = audio(), originalFilter = ac.createBiquadFilter.bind(ac); ac.createBiquadFilter = function(){ var f = originalFilter(), ramp = f.gain.linearRampToValueAtTime.bind(f.gain); f.carveRamps = []; f.gain.linearRampToValueAtTime = function(v,t){ f.carveRamps.push([v,t]); return ramp(v,t); }; CARVE_FILTERS.push(f); return f; }; true"},
            {"do": "click", "sel": "#play"}, {"do": "waitTrue", "js": "CARVE_FILTERS.length > 0"},
            {"do": "eval", "js": "CARVE_FILTERS.map(function(f){ return {type:f.type, freq:f.frequency.value, q:f.Q.value, lastRampGain:f.carveRamps[f.carveRamps.length-1][0]}; })"},
            {"do": "click", "sel": "#play"},
            {"do": "click", "sel": "#bedcarve"}, {"do": "waitSaved"}, {"do": "read"},
            {"do": "click", "sel": "#send"}, {"do": "waitSent"}])["reads"]
        need(reads[0]["music"]["carve"] == {"on": True, "strength": 0.8, "visible": True, "preview": True}, "reload lost strength")
        need(reads[3]["music"]["carve"] == {"on": False, "strength": 0.8, "visible": False, "preview": False}, "off did not hide the slider")
        need([f["freq"] for f in reads[2]] == list(frequencies)
             and all(f["type"] == "peaking" and abs(f["q"] - 2.06) < 1e-5
                     and f["lastRampGain"] == 0 for f in reads[2]),
             f"preview filter nodes: {reads[2]}")
        need(load(d / "sound-selection.json")["bed"]["carve"] == {"on": False, "strength": 0.8}, "unticking did not send on:false")
        reads = browse("carve-reel", [{"do": "goto"}, {"do": "read"}, {"do": "dialog", "accept": True},
            {"do": "click", "sel": "#reset"}, {"do": "waitSaved"}, {"do": "read"},
            {"do": "eval", "js": "CFG.carve = null; previewCarve()"}])["reads"]
        need(not reads[0]["music"]["carve"]["on"], "off did not survive reload")
        need(reads[1]["music"]["carve"] == {"on": True, "strength": 0.8, "visible": True, "preview": True}, "reset lost defaults")
        need(reads[2] is None, "missing curves must use the dip")
        preset = {"file": BEDS[0]["file"], "gain_db": -18, "entry_s": 0, "exit_s": DUR, "offset_s": 0,
                  "fade_in_s": 0.5, "fade_out_s": 0.8, "carve": {"on": False, "strength": 0.8}}
        reel("carve-preset", beds=BEDS, carve=data, bed_default=preset)
        p = browse("carve-preset", [{"do": "goto"}, {"do": "read"}])["reads"][0]["music"]["carve"]
        need(p == {"on": False, "strength": 0.8, "visible": False, "preview": False}, f"preset: {p}")
        # Saved sessions made before carve existed must retain their dip setting.
        old = load(d / "sound-board.state.json")
        old["bed"].pop("carve", None)
        write_json(d / "sound-board.state.json", old)
        p = browse("carve-reel", [{"do": "goto"}, {"do": "read"}])["reads"][0]["music"]["carve"]
        need(not p["on"] and not p["visible"], f"old saved board unexpectedly enabled carve: {p}")

    def c_beat_sync():
        def make(name):
            d = reel(name, library=SYNC_LIB, beds=SYNC_BEDS, cues=SYNC_CUES)
            for sub, f, secs in (("beds", "grid-bed.wav", 8), ("beds", "flat-bed.wav", 8), ("sfx", "tick.wav", 0.5)):
                (d / sub).mkdir(exist_ok=True)  # real files, so the loop and the bed decode and play
                p = run([tools["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f=220:d={secs}", str(d / sub / f)])
                need(p.returncode == 0, f"ffmpeg could not make {f}: {p.stderr.strip()[-300:]}")
            return d
        tab = [{"do": "goto", "noRows": True}, {"do": "waitTrue", "js": "window.Hub && Hub.ready"},
               {"do": "click", "sel": "#tab-sound-board"}, {"do": "frame", "sel": ".frame iframe"}]
        flat, grid = LINE % 2 + " button.muse", LINE % 1 + " button.muse"
        to_snap = [{"do": "click", "sel": flat}, {"do": "read"},                       # null grid
                   {"do": "click", "sel": grid}, {"do": "read"},                       # grid, beat-sync still off
                   {"do": "click", "sel": "#bsync"}, {"do": "read"},                   # on: the offset snaps
                   {"do": "set", "sel": "#boffset", "value": 1.0}, {"do": "read"},     # a typed offset snaps too
                   {"do": "click", "sel": "#bsnap"}, {"do": "waitSaved"}, {"do": "read"}]

        def times(read):
            return [r["time"] for r in read["rows"]]

        def cues_snapped(read):  # the assert the reverse run must trip
            need(times(read) == ["1.000", "1.700", "2.000"],
                 f"after Snap cues to the beat the cue times are {times(read)} (wanted c01 1.03 -> 1.000, the rest put)")

        d = make("sync-reel")
        loop = (ROW % 1) + " td:last-child > button:nth-child(3)"   # loop with picture / stop loop
        out = browse("sync-reel", tab + to_snap + [
            {"do": "click", "sel": KEEP % 1}, {"do": "click", "sel": loop},
            {"do": "waitTrue", "js": "SCHED.c01 != null"}, {"do": "eval", "js": "SCHED.c01"},
            {"do": "click", "sel": loop}, {"do": "waitSaved"}, {"do": "click", "sel": "#send"}, {"do": "waitSent"}],
            page="editor/hub/")
        r_flat, r_off, r_on, r_typed, r_snap = (r["music"] for r in out["reads"][:5])
        need(r_flat["sync"] == {"checked": False, "disabled": True, "note": "no steady beat found in this track",
                                "snapDisabled": True}, f"with a null grid beat-sync shows {r_flat['sync']}")
        need(r_off["sync"]["disabled"] is False and r_off["sync"]["checked"] is False and r_off["offset"] == "0.50"
             and r_off["beatTicks"] == 0,
             f"grid bed, beat-sync off: {r_off['sync']}, offset {r_off['offset']}, {r_off['beatTicks']} ticks")
        need(r_on["sync"]["checked"] and r_on["offset"] == "0.62",
             f"toggled on: offset {r_on['offset']} (wanted the nearest beat 0.62), {r_on['sync']}")
        need(r_typed["offset"] == "1.12", f"typed 1.0 with beat-sync on: offset {r_typed['offset']} (wanted 1.12)")
        need(r_snap["beatTicks"] == 6, f"{r_snap['beatTicks']} beat ticks on the timeline (wanted 6: 0, 0.5 ... 2.5)")
        cues_snapped(out["reads"][4])
        start = out["reads"][5]
        need(isinstance(start, (int, float)) and abs(start - (1.0 - 0.25)) < 1e-3,
             f"c01 (peak_s 0.25 at 1.0 s) was scheduled to start at {start} s, wanted 0.75")
        doc = load(d / "sound-selection.json")
        need(set(doc) == PAYLOAD_KEYS, f"payload keys {sorted(doc)}")
        bed = doc["bed"]
        got = (bed["file"], bed["beat_sync"], bed["offset_s"])
        need(got == ("grid-bed.wav", True, 1.12), f"sent bed (file, beat_sync, offset_s) = {got}")
        sent = [(c["id"], c["time"], c["peak_s"]) for c in doc["cues"] + doc["undecided"]]
        need(sent == [("c01", 1.0, 0.25), ("c02", 1.7, 0), ("c03", 2.0, 0)], f"sent (id, time, peak_s) = {sent}")
        r = browse("sync-reel", tab + [{"do": "read"}, {"do": "click", "sel": "#bsync"}, {"do": "waitSaved"}, {"do": "read"}],
                   page="editor/hub/")["reads"]
        back, off = r[0], r[1]
        got = (back["music"]["bed"], back["music"]["sync"]["checked"], back["music"]["offset"], times(back))
        need(got == ("grid-bed.wav", True, "1.12", ["1.000", "1.700", "2.000"]), f"after a reload: {got}")
        got = (off["music"]["sync"]["checked"], off["music"]["offset"], times(off), off["music"]["beatTicks"])
        need(got == (False, "1.12", ["1.000", "1.700", "2.000"], 0), f"turned off, nothing moves back: {got}")
        # reverse: the same clicks with every snap turned off by the page flag; the cue assert must fail
        make("sync-rev")
        rev = browse("sync-rev", tab + [{"do": "eval", "js": "window.BEAT_SNAP_OFF = true"}] + to_snap,
                     page="editor/hub/")["reads"][-1]
        try:
            cues_snapped(rev)
        except Fail:
            pass
        else:
            raise Fail(f"with snapping off the cue check still passed: {times(rev)}")

    fns = {"send": ("send: decide one cue, Send writes sound-selection.json with every undecided cue", c_send),
           "voice_only": ("voice_only: no config opens a plain empty state without raw errors", c_voice_only),
           "reload": ("reload: decisions come back from disk in a new browser", c_reload),
           "reject_all": ("reject_all: Cancel changes nothing, OK rejects every cue", c_reject_all),
           "reset": ("reset: Cancel changes nothing, OK goes back to the proposals", c_reset),
           "writes_guard": ("writes_guard: boards.json lists sound-selection.json; selection.json is refused (403)", c_writes_guard),
           "tips": ("tips: long sound, doubled sound and closer-over-speech tips show and Send still works", c_tips),
           "hub_tab": ("hub_tab: inside the hub's iframe, a gain and nudge adjust saves and goes out on Send", c_hub_tab),
           "music": ("music: inside the hub's iframe, pick, preview, level, dip, rights tick and a free-track request "
                     "go out on Send and come back on reload", c_music),
           "carve": ("carve: defaults, Send, off, save/restore/reset, preset and peaking preview", c_carve),
           "beat_sync": ("beat_sync: inside the hub's iframe, beat-sync snaps the music start and near cues to a beat, "
                         "a hit plays peak_s early, Send and reload carry it, a null grid disables it", c_beat_sync)}
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
