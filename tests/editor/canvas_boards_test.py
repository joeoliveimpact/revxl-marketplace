"""S6a done-test: the Beat Map and Sketches boards end to end, plus the ways they must refuse.

  EDITOR_SE_HOME=<state> python -X utf8 -I tests/editor/canvas_boards_test.py

<state> is an installed editor state folder (node, chrome-headless-shell, puppeteer-core); it is only read.
Prints one "✓ <case>" / "✗ <case>: <why>" line per case, then "N passed, M failed". Exit 0 only when all pass.
The browser work runs through canvas_boards_click.js (puppeteer-core, headless shell, a fresh profile per browser).
"""
import base64, copy, datetime, http.client, json, os, shutil, socket, subprocess, sys, tempfile, threading
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
DOCTOR = PLUGIN / "skills/editor-doctor/scripts"
CANVAS = PLUGIN / "skills/reel-canvas-build/scripts"
sys.path.insert(0, str(PLUGIN / "skills/_shared"))
sys.path.insert(0, str(DOCTOR))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)

SERVER = DOCTOR / "board_server.py"
SEED = CANVAS / "make_beat_map.py"
SCHEMA = CANVAS / "beat_schema.py"
CLICK = Path(__file__).resolve().parent / "canvas_boards_click.js"
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP438AAAAQBAYDFKhhdAAAAAElFTkSuQmCC")
WORDS = ["Three", "big", "wins", "for", "your", "next", "reel", "today.",
         "First,", "cut", "the", "silence.", "Then", "follow", "for", "more."]
FPS, TOTAL_F = 30, 270
PLAN = {"beats": [{"w0": 0, "w1": 3, "layout": "full", "shows": "the title", "why": "the opening line"},
                  {"w0": 4, "w1": 7, "layout": "full"},
                  {"w0": 8, "w1": 11, "layout": "stack", "why": "two steps"},
                  {"w0": 9, "w1": 10, "layout": "overlay", "value": 2, "shows": "a counter", "why": "a number"},
                  {"w0": 12, "w1": 15, "layout": "pip"}],
        "word_marks": [{"w": 0, "mark": "num"}, {"w": 13, "mark": "cta"}],
        "needs": ""}
D1, D2 = "d_bold", "d_calm"


class Fail(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Fail(why)


def free_port(*taken):
    while True:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port not in taken:
            return port


def find_tools():
    found, missing = {}, []
    for name in ("node", "chrome"):
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


def run(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def iso(v):
    try:
        datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1), encoding="utf-8")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def reel_fixture(reel):
    words = [{"id": f"w_{i:04d}", "word": w, "start": round(0.1 + 0.5 * i, 3), "end": round(0.5 + 0.5 * i, 3),
              "parakeet_start": round(0.1 + 0.5 * i, 3), "status": "aligned", "score_min": 0.9}
             for i, w in enumerate(WORDS)]
    write_json(reel / "work/edit_map.cut.json", {"words": words})
    write_json(reel / "work/cuts.json", {"fps": FPS, "segments": [
        {"src_in_f": 0, "src_out_f": 120, "out_in_f": 0, "out_out_f": 120},
        {"src_in_f": 150, "src_out_f": 300, "out_in_f": 120, "out_out_f": TOTAL_F}]})
    write_json(reel / "work/plan.json", PLAN)
    for d in (D1, D2):
        (reel / f"work/sketches/{d}.png").parent.mkdir(parents=True, exist_ok=True)
        (reel / f"work/sketches/{d}.png").write_bytes(PNG_1X1)
    write_json(reel / "sketches.state.json", {
        "schema": 1, "reel": reel.name, "rough": None,
        "directions": [{"id": D1, "name": "Bold", "why": "fast cuts", "frames": [f"work/sketches/{D1}.png"], "note": ""},
                       {"id": D2, "name": "Calm", "why": "room to breathe", "frames": [f"work/sketches/{D2}.png"], "note": ""}],
        "pick": None,
        "sketches": [{"id": "s_001", "beat": "b_001", "title": "Three wins", "media": None, "note": ""},
                     {"id": "s_002", "beat": "b_002", "title": "Next reel", "media": None, "note": ""}],
        "note": "", "sent_at": None, "locked_at": None})


def main():
    ensure_utf8_output()
    tools, missing = find_tools()
    if missing:
        print(f"✗ This test needs an installed editor state: set EDITOR_SE_HOME to one "
              f"(node, chrome and puppeteer-core missing: {', '.join(missing)})")
        return 1
    scratch = Path(tempfile.mkdtemp(prefix="s6a_boards_"))
    env = dict(os.environ, HOME=str(scratch), USERPROFILE=str(scratch))  # H-R16; EDITOR_SE_HOME/LOCALAPPDATA kept
    ws = scratch / "ws"
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": free_port()}}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    videos = ws / rt.read_config(ws)["paths"]["videos"]
    reel = videos / "demo-reel"
    reel_fixture(reel)
    py = [sys.executable, "-X", "utf8", "-I"]
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

    def start(port):
        if S["server"]:
            S["server"].terminate()
            S["server"].wait(10)
        need(check_deps.write_config(ws, ports={"board": port}), "could not set the board port")
        p = subprocess.Popen(py + [str(SERVER), "--root", str(ws)], env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        procs.append(p)
        t = threading.Timer(20, p.kill)  # a hung start fails the case instead of blocking the test
        t.start()
        line = p.stdout.readline().strip()
        t.cancel()
        need(line.startswith("Editor boards: http://127.0.0.1:") and line.endswith("/"), f"server said {line!r}")
        S["server"], S["port"] = p, int(line.rsplit(":", 1)[1].rstrip("/"))
        return S["port"]

    def url(board, reel_name="demo-reel"):
        return f"http://127.0.0.1:{S['port']}/editor/{board}/?reel={reel_name}"

    def browse(page_url, actions):
        """A NEW browser (fresh profile) runs the actions; returns its reads."""
        S["browsers"] += 1
        job = scratch / f"job-{S['browsers']}.json"
        write_json(job, {"url": page_url, "userDataDir": str(scratch / f"profile-{S['browsers']}"), "actions": actions})
        p = run([tools["node"], str(CLICK), tools["pup"], tools["chrome"], str(job)])
        try:
            out = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            out = {}
        need(p.returncode == 0, f"browser: {out.get('error') or p.stderr.strip()[-500:]}; "
                                f"page showed {json.dumps(out.get('last'))[:600]}; page errors {out.get('errors')}")
        return out["reads"]

    def check(*args):
        p = run(py + [str(SCHEMA), *map(str, args)], env=env)
        return p.returncode, p.stdout + p.stderr

    def seed(*extra):
        return run(py + [str(SEED), "--reel-dir", str(reel), "--plan", "work/plan.json", "--words",
                         "work/edit_map.cut.json", "--cuts", "work/cuts.json", *extra], cwd=reel, env=env)

    state = reel / "beat-map.state.json"
    sel = reel / "beat-map-selection.json"

    # ---- forward ----
    def c1():
        p = seed()
        need(p.returncode == 0, f"make_beat_map exit {p.returncode}: {(p.stdout + p.stderr).strip()[-500:]}")
        rc, out = check("check", state)
        need(rc == 0, f"beat_schema check exit {rc}: {out.strip()[-500:]}")
        S["seeded"] = state.read_bytes()
        beats = load(state)["beats"]
        tiled = [b for b in beats if b["layout"] != "overlay"]
        need(len(tiled) == 4 and len(beats) == 5, f"{len(tiled)} tiled + {len(beats) - len(tiled)} overlay beats")
        need(tiled[0]["start_f"] == 0, f"first beat starts at {tiled[0]['start_f']}")
        gaps = [(a["id"], a["end_f"], b["start_f"]) for a, b in zip(tiled, tiled[1:]) if a["end_f"] != b["start_f"]]
        need(not gaps, f"beats don't tile: {gaps}")
        need(tiled[-1]["end_f"] == TOTAL_F, f"last beat ends at {tiled[-1]['end_f']}, not {TOTAL_F}")
        S["bid"] = beats[1]["id"]

    def edits_shown(r, bid):
        row = next((x for x in r["rows"] if x["beat"] == bid), None)
        need(row, f"no row for {bid}: {r['rows']}")
        need((row["layout"], row["value"], row["note"], row["changed"]) == ("split", "3", "tighter here", True),
             f"row {bid} shows {row}")
        need(r["marks"].get("5") == "key", f"word 5 mark is {r['marks'].get('5')!r}")
        need(r["needs"] == "logo please", f"needs shows {r['needs']!r}")
        need(not r["empty"], "#empty is showing")

    def c2():
        start(S["A"])
        bid = S["bid"]
        row = f'#beats tr[data-beat="{bid}"]'
        reads = browse(url("beat-map"), [
            {"do": "goto"}, {"do": "wait", "sel": row},
            {"do": "select", "sel": f"{row} select[name=layout]", "value": "split"},
            {"do": "type", "sel": f"{row} input[name=value]", "text": "3"},
            {"do": "type", "sel": f"{row} textarea[name=note]", "text": "tighter here"},
            {"do": "click", "sel": '#beats span.word[data-w="5"]'},
            {"do": "click", "sel": '#beats span.word[data-w="5"]'},
            {"do": "type", "sel": "#needs", "text": "logo please"},
            {"do": "waitState", "state": "saved", "change": True},
            {"do": "goto"}, {"do": "wait", "sel": row}, {"do": "read"},
            {"do": "click", "sel": "#send"}, {"do": "waitState", "state": "sent"}, {"do": "read"}])
        edits_shown(reads[0], bid)
        S["sent_read"] = reads[1]

    def c3():
        need(S.get("sent_read"), "the Send step did not run (case 2 failed first)")
        need(sel.is_file(), "no beat-map-selection.json")
        rc, out = check("check", sel)
        need(rc == 0, f"beat_schema check exit {rc}: {out.strip()[-500:]}")
        doc, bid = load(sel), S["bid"]
        beat = next((b for b in doc["beats"] if b["id"] == bid), {})
        need((beat.get("layout"), beat.get("value")) == ("split", 3), f"beat {bid} sent as {beat}")
        need(doc["notes"].get(bid) == "tighter here", f"notes sent as {doc['notes']}")
        need({"w": 5, "mark": "key"} in doc["word_marks"], f"word_marks sent as {doc['word_marks']}")
        need(doc["needs"] == "logo please", f"needs sent as {doc['needs']!r}")
        need(iso(doc.get("sent_at")), f"selection sent_at is {doc.get('sent_at')!r}")
        need(iso(load(state).get("sent_at")), f"beat-map.state.json on disk has sent_at {load(state).get('sent_at')!r}")

    def c4():
        got = start(S["B"])
        need(got != S["A"], f"restarted on port {got}, the same as before")
        reads = browse(url("beat-map"), [{"do": "goto"}, {"do": "wait", "sel": f'#beats tr[data-beat="{S["bid"]}"]'},
                                         {"do": "read"}])
        edits_shown(reads[0], S["bid"])
        need((reads[0]["status"] or {}).get("state") == "sent", f"status is {reads[0]['status']}")

    def c5():
        need(S["port"] != S["A"], "case 4 did not restart the server on a new port")
        dsel = '#directions section.direction[data-id="%s"]'
        reads = browse(url("sketches"), [
            {"do": "goto"}, {"do": "wait", "sel": dsel % D2}, {"do": "wait", "sel": "#lock"}, {"do": "read"},
            {"do": "type", "sel": (dsel % D1) + " textarea[name=note]", "text": "brighter"},
            {"do": "type", "sel": "#note", "text": "ok"},
            {"do": "click", "sel": (dsel % D2) + ' input[type=radio][name=pick]'},
            {"do": "click", "sel": "#lock"},
            {"do": "waitState", "state": "saved", "change": True},
            {"do": "click", "sel": "#send"}, {"do": "waitState", "state": "sent"}])
        need(reads[0]["lock"] == {"disabled": True}, f"before a pick #lock is {reads[0]['lock']}")
        locked = load(reel / "sketches.state.json").get("locked_at")
        need(iso(locked), f"sketches.state.json on disk has locked_at {locked!r}")
        ssel = reel / "sketches-selection.json"
        need(ssel.is_file(), "no sketches-selection.json")
        rc, out = check("check-sketches", ssel, "--beat-map", state)
        need(rc == 0, f"check-sketches exit {rc}: {out.strip()[-500:]}")
        need(load(ssel)["pick"] == D2, f"pick sent as {load(ssel)['pick']!r}")
        prev = S["port"]
        got = start(free_port(prev))
        need(got != prev, f"restarted on port {got}, the same as before")
        r = browse(url("sketches"), [{"do": "goto"}, {"do": "wait", "sel": dsel % D2}, {"do": "read"}])[0]
        picked = [d["id"] for d in r["directions"] if d["picked"]]
        need(picked == [D2], f"picked directions shown: {picked}")
        need(r["locked"], "#directions is not .locked after the restart")
        d1 = next((d for d in r["directions"] if d["id"] == D1), {})
        need(d1.get("note") == "brighter" and r["note"] == "ok", f"notes shown: {D1} {d1.get('note')!r}, page {r['note']!r}")

    def c6():
        (videos / "empty-reel").mkdir()
        reads = browse(url("beat-map", "empty-reel"), [
            {"do": "goto"}, {"do": "wait", "sel": "#empty", "visible": True}, {"do": "read"},
            {"do": "goto", "url": url("sketches", "empty-reel")}, {"do": "wait", "sel": "#empty", "visible": True},
            {"do": "read"}])
        need(reads[0]["empty"] and reads[1]["empty"], f"#empty shown: beat-map {reads[0]['empty']}, sketches {reads[1]['empty']}")

    # ---- reverse ----
    def c7():
        need(S.get("seeded"), "no seeded doc (case 1 failed)")
        good = json.loads(S["seeded"])
        planted = scratch / "planted"
        planted.mkdir()

        def plant(name, fn):
            d = copy.deepcopy(good)
            fn(d["beats"][0])
            write_json(planted / name, d)
            return check("check", planted / name)
        write_json(planted / "valid.json", good)
        rc, out = check("check", planted / "valid.json")
        need(rc == 0, f"the unplanted doc exit {rc}: {out.strip()[-300:]}")
        for name, fn, words in (("no-id.json", lambda b: b.pop("id"), ("missing id",)),
                                ("grid.json", lambda b: b.update(layout="grid"), ("layout 'grid'",)),
                                ("start-after-end.json", lambda b: b.update(start_f=b["end_f"] + 5),
                                 ("start_f", "after end_f"))):
            rc, out = plant(name, fn)
            need(rc == 1 and all(w in out for w in words), f"{name}: exit {rc}, output {out.strip()[-300:]!r}")

    def c8():
        need(S.get("seeded"), "no seeded doc (case 1 failed)")
        bad_reel = videos / "broken-reel"
        shutil.copytree(reel / "work", bad_reel / "work")
        doc = json.loads(S["seeded"])
        doc["reel"] = "broken-reel"
        doc["beats"][0]["layout"] = "grid"
        write_json(bad_reel / "beat-map.state.json", doc)
        browse(url("beat-map", "broken-reel"), [{"do": "goto"}, {"do": "wait", "sel": "#send"},
                                                {"do": "click", "sel": "#send"}, {"do": "waitState", "state": "error"}])
        need(not (bad_reel / "beat-map-selection.json").exists(), "beat-map-selection.json was written")

    def c9():
        need(state.is_file(), "no beat-map.state.json to protect (case 1 failed)")
        before = state.read_bytes()
        p = seed()
        need(p.returncode == 1, f"a second run exit {p.returncode}, not 1")
        need(state.read_bytes() == before, "the second run changed beat-map.state.json")
        p = seed("--replace")
        need(p.returncode == 0, f"--replace exit {p.returncode}: {(p.stdout + p.stderr).strip()[-300:]}")
        prev = reel / "beat-map.state.json.prev"
        need(prev.is_file() and prev.read_bytes() == before, "beat-map.state.json.prev is not the old file")

    def c10():
        port = S["port"]
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("POST", "/videos/demo-reel/__save?board=beat-map&name=other.json", body=b'{"v": 1}',
                  headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"})
        status = c.getresponse().status
        c.close()
        need(status == 403, f"HTTP {status}, not 403")
        need(not (reel / "other.json").exists(), "other.json was written")

    S["A"] = free_port()
    S["B"] = free_port(S["A"])
    try:
        case("1 seed: make_beat_map writes a valid map whose beats tile 0..end", c1)
        case("7 schema rejects a beat with no id, layout grid, start_f > end_f", c7)
        case("2 edit + reload: layout, value, note, word mark and needs survive a reload", c2)
        case("3 Send: beat-map-selection.json is valid and carries the edits and sent_at", c3)
        case("4 port change + new browser: the edits and sent come back from disk", c4)
        case("5 sketches: lock waits for a pick; pick, lock, notes saved, Send valid, restored on a new port", c5)
        case("6 empty: a reel with no beat map or sketches shows #empty on both pages", c6)
        case("8 the board won't send a broken doc", c8)
        case("10 __save refuses a name outside the board's writes list", c10)
        case("9 seed refuses to overwrite; --replace keeps .prev", c9)
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
