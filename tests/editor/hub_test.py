"""S13 hub proof: generated tiny reels, real board server, fresh locked browsers, twelve biting mutants.

Run with the editor Python, -X utf8 -I; --case 1..12 (or the case name) runs independently.
EDITOR_SE_HOME is read only. All generated files and child homes live in an owned scratch directory,
removed even on failure. No downloads or real recordings. Each case has a 165 second watchdog.
"""
import argparse
import contextlib
import datetime as dt
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins/editor-superengine"
sys.path.insert(0, str(PLUGIN / "skills/_shared"))
import runtime as rt
from win_encoding import ensure_utf8_output

HEAVY = Path("C:/Workspaces/Content Studio/output/scripts/heavy_lock.py")
NAMES = ["reels", "tabs", "grade", "review", "sends", "health", "filmstrip", "layout", "attention", "sync", "edit_style", "look", "broll"]


class Blocked(RuntimeError):
    pass


def need(ok, why):
    if not ok:
        raise AssertionError(why)


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8"))


class Proof:
    def __init__(self, scratch):
        self.scratch = scratch
        self.plugin = scratch / "plugin"
        shutil.copytree(PLUGIN, self.plugin, ignore=shutil.ignore_patterns("__pycache__", ".git"))
        self.doctor = self.plugin / "skills/editor-doctor/scripts"
        self.ws = scratch / "workspace"
        self.editor = self.ws / "desk"
        self.videos = self.ws / "clips"
        self.hub = self.editor / "hub"
        self.env = rt.python_env(base=dict(os.environ, HOME=str(scratch / "home"),
                              USERPROFILE=str(scratch / "home"), TMP=str(scratch / "tmp"),
                              TEMP=str(scratch / "tmp"), TMPDIR=str(scratch / "tmp")))
        for n in ("home", "tmp"):
            (scratch / n).mkdir()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        write(self.ws / "editor/editor.config.json", {"paths": {"editor": "desk", "videos": "clips"},
                                                    "ports": {"board": self.port}, "nle": "none"})
        write(self.ws / "editor/.platform.json", {"status": [
            {"component": "video-tools", "level": "ok", "detail": "Video tools are ready"},
            {"component": "motion", "level": "missing", "detail": "Motion needs setup"}]})
        self.tools = {k: rt.tool(k) for k in ("ffmpeg", "node", "chrome")}
        self.pup = rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
        self.process = None
        self.jobs = 0
        self.clip = scratch / "clip.mp4"
        self.run([self.tools["ffmpeg"], "-v", "error", "-y", "-f", "lavfi", "-i",
                  "color=c=0xcd967d:s=320x240:r=12:d=2", "-c:v", "libx264", "-threads", "2",
                  "-pix_fmt", "yuv420p", self.clip])
        for name in ("reel-01", "reel-02"):
            d = self.videos / name
            (d / "raw").mkdir(parents=True)
            (d / "renders").mkdir()
            shutil.copyfile(self.clip, d / "raw/take.mp4")
            shutil.copyfile(self.clip, d / "renders" / f"{name} Master - 11.05.26.mp4")
        d = self.videos / "reel-01"
        write(d / "work/cuts.json", {"segments": [{"out_out_f": 24}]})
        write(d / "work/qa.json", {"checks": [{"label": "Loudness", "state": "ok", "detail": "Ready to post"}]})
        write(d / "work/map_check.json", {"blocks": [{"check": "speech", "level": "block",
                                                     "msg": "A word is clipped at the opening", "where": "0:01"}], "warns": []})
        write(d / "cover.json", {"frame": 0})
        self.run([self.tools["ffmpeg"], "-v", "error", "-y", "-i", self.clip,
                  "-frames:v", "1", d / "cover.jpg"])
        write(self.ws / "reel-build/goldmine-run.json", {"manifest": "manifest.json",
              "compute": {"popularity": "popularity.json"}})
        write(self.ws / "reel-build/manifest.json", {"count": 7})
        write(self.ws / "reel-build/popularity.json", {"corpus": {"reels_total": 123, "creators": 4},
              "breakout_ranking": [{"benchmark_x": 2.5, "comment_rate": 0.02}]})

    def run(self, args, timeout=140, check=True):
        p = subprocess.run([str(a) for a in args], env=self.env, cwd=self.ws if self.ws.exists() else self.scratch,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        if check:
            need(p.returncode == 0, f"exit {p.returncode}: {(p.stdout + p.stderr)[-1500:]}")
        return p

    def py(self, script, *args):
        return self.run([sys.executable, "-X", "utf8", "-I", "-B", script, *args])

    def refresh(self):
        self.py(self.doctor / "board_sync.py", "--root", self.ws)
        self.py(self.doctor / "hub_rows.py", "--root", self.ws)
        return read(self.hub / "hub-data.json")

    def start(self):
        if self.process:
            return
        self.process = subprocess.Popen([getattr(sys, "_base_executable", sys.executable), "-X", "utf8", "-I", "-B",
                         str(self.doctor / "board_server.py"), "--root", str(self.ws), "--idle", "180", "--grace", "180"],
                         env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        timer = threading.Timer(20, self.process.kill)
        timer.start()
        line = self.process.stdout.readline().strip()
        timer.cancel()
        need(line == f"Editor boards: {self.base}/", f"server: {line}")

    def browse(self, actions=(), reel="reel-01"):
        self.start()
        self.jobs += 1
        job = self.scratch / f"job-{self.jobs}.json"
        write(job, {"base": self.base, "userDataDir": str(self.scratch / f"profile-{self.jobs}"),
                    "actions": [{"do": "goto", "path": f"/editor/hub/?reel={reel}", "waitFn": "window.Hub && Hub.ready"}] + list(actions)})
        p = self.run([sys.executable, "-X", "utf8", "-I", HEAVY, "--wait", "20", "--min-gb", "3", "--",
                      self.tools["node"], HERE / "boards_click.js", self.pup, self.tools["chrome"], job], timeout=65, check=False)
        if p.returncode in (75, 76):
            raise Blocked(f"UNPROVEN heavy_lock exit {p.returncode}: {p.stderr[-500:]}")
        if "PermissionError" in p.stderr and "heavy.lock" in p.stderr:
            raise Blocked("sandbox denied the required shared heavy.lock; browser case unproven")
        need(p.returncode == 0, f"browser: {(p.stdout + p.stderr)[-1500:]}")
        out = json.loads(p.stdout.strip().splitlines()[-1])
        need(not out.get("errors"), f"page errors: {out.get('errors')}")
        need(all(u.startswith((self.base + "/", "data:", "blob:", "about:")) for u in out["requests"]), "off-server request")
        return [json.loads(r) if isinstance(r, str) else r for r in out["reads"]]

    def snapshot(self, expr, actions=(), reel="reel-01"):
        return self.browse(list(actions) + [{"do": "eval", "js": "JSON.stringify(" + expr + ")"}], reel)[-1]

    @contextlib.contextmanager
    def mutant(self, rel, before, after):
        p = self.hub / rel
        original = p.read_bytes()
        text = original.decode("utf-8")
        need(text.count(before) == 1, f"mutant anchor count: {rel}: {before}")
        p.write_bytes(text.replace(before, after).encode("utf-8"))
        try:
            yield
        finally:
            p.write_bytes(original)

    def bites(self, check, label):
        try:
            check()
        except AssertionError:
            print(f"  mutant rejected: {label}", flush=True)
            return
        raise AssertionError(f"mutant survived: {label}")

    def close(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)
            self.process.stdout.close()
            self.process.stderr.close()


def click(sel):
    return {"do": "click", "sel": sel}


def case_reels(p):
    def check():
        rows = p.snapshot("[...document.querySelectorAll('#wall .rc')].map(e=>({id:e.dataset.reel,src:e.querySelector('video')?.getAttribute('src')}))")
        need([r["id"] for r in rows] == ["reel-01", "reel-02"], f"reel folders differ: {rows}")
        need(all(r["src"].startswith(f"/videos/{r['id']}/") for r in rows), "hover videos missing")
        played = p.snapshot("document.querySelector('#wall video').paused", [{"do": "eval", "js":
            "document.querySelector('#wall .rc').dispatchEvent(new Event('mouseenter'))"},
            {"do": "waitFn", "js": "!document.querySelector('#wall video').paused"}])
        need(played is False, "hover did not play")
    check()
    with p.mutant("hub.js", "const reels = DATA.reels;", "const reels = DATA.reels.slice(0, 1);"):
        p.bites(check, "fixed reel list")


def case_tabs(p):
    m = read(p.doctor / "boards.json")
    m["boards"]["grade-board"]["tab"].update(label="Picture colour", order=5)
    write(p.doctor / "boards.json", m)
    shutil.rmtree(p.editor / "look-picker", ignore_errors=True)
    p.refresh()
    expected = [k for k, v in sorted(m["boards"].items(), key=lambda kv: kv[1].get("tab", {}).get("order", 999)) if "tab" in v]
    def check():
        rows = p.snapshot("[...document.querySelectorAll('[role=tab][data-board]')].map(e=>({id:e.dataset.board,text:e.textContent,href:e.getAttribute('href')}))")
        need([r["id"] for r in rows] == expected, f"manifest order: {rows}")
        need(rows[0]["text"] == "Picture colour", "manifest label ignored")
        for r in rows:
            if (p.editor / r["id"] / "index.html").is_file():
                need(r["href"] == f"/editor/{r['id']}/?reel=reel-01", f"bad built URL: {r}")
            else:
                need("not built yet" in r["text"] and not r["href"], f"unbuilt board: {r}")
        urls = p.snapshot("[...document.querySelectorAll('a[href],iframe[src]')].map(e=>e.getAttribute('href')||e.getAttribute('src'))")
        need(all(not u.endswith('/') and not u.startswith('file:') for u in urls), f"folder or local URL: {urls}")
    check()
    with p.mutant("hub.js", "const tabs = DATA.boards;", "const tabs = DATA.boards.filter(b=>b.id==='cut-board');"):
        p.bites(check, "fixed board list")


def case_grade(p):
    d = p.videos / "reel-01"
    p.py(p.plugin / "skills/reel-grade/scripts/make_grade.py", "--reel", d.name,
         "--video", d / "raw/take.mp4", "--reel-dir", d)
    def check():
        (d / "grade-selection.json").unlink(missing_ok=True)
        p.browse([click('#tab-grade-board'), {"do": "frame", "sel": "#panel iframe", "waitFn": "window.GB && GB.ready"},
                  click('#rail figure[data-look="warm"]'), {"do": "set", "sel": "#strength", "value": "0.6"}, click('#send'),
                  {"do": "waitText", "sel": "#saved", "re": "saved|FAILED"}])
        need((d / "grade-selection.json").is_file(), "Grade Send missing")
        need(read(d / "grade-selection.json")["look"] == {"id": "warm", "strength": 0.6}, "wrong Grade Send")
    check()
    live = p.editor / "grade-board/index.html"
    original = live.read_bytes()
    need(b"name=grade-selection.json" in original, "grade mutant anchor")
    live.write_bytes(original.replace(b"name=grade-selection.json", b"name=review.json"))
    try:
        p.bites(check, "Grade Send goes to forbidden filename")
    finally:
        live.write_bytes(original)


def case_look(p):
    """H-HUB-1 / H-X3-1: real picker output, hub tab, replay and allowlisted Send."""
    sys.path.insert(0, str(HERE))
    import canvas_boards_test as fixture
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    # Proof's take is 24 frames at 12 fps; keep the cut words and beats inside it.
    items = read(d / "work/edit_map.cut.json")["words"][:6]
    for i, w in enumerate(items):
        w.update(start=i * 0.25, end=i * 0.25 + 0.22, parakeet_start=i * 0.25)
    write(d / "work/edit_map.cut.json", {"words": items})
    write(d / "work/cuts.json", {"fps": 12, "speed": 1.0, "segments": [
        {"src_in_f": 0, "src_out_f": 24, "out_in_f": 0, "out_out_f": 24}]})
    write(d / "work/plan.json", {"beats": [
        {"w0": 0, "w1": 2, "layout": "full"}, {"w0": 3, "w1": 5, "layout": "split"}],
        "word_marks": [{"w": 0, "mark": "num"}], "needs": ""})
    p.py(p.plugin / "skills/reel-canvas-build/scripts/make_beat_map.py",
         "--reel-dir", d, "--plan", d / "work/plan.json")
    bm = read(d / "beat-map.state.json")
    bm.update(caption_style={"style": "clean"}, sent_at="2026-11-05T12:00:00-05:00")
    write(d / "beat-map-selection.json", bm)
    master = d / "work/renders/master-100x.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(d / "raw/take.mp4", master)
    p.py(p.plugin / "skills/reel-captions/scripts/captions.py", "picker", "--reel-dir", d)
    p.refresh()

    def check():
        dest = d / "look-picker-selection.json"
        dest.unlink(missing_ok=True)
        # A fresh opening starts from the picker current, including in the mutant run.
        (d / "look-picker.state.json").unlink(missing_ok=True)
        rows = p.browse([click('#tab-look-picker'),
            {"do": "frame", "sel": "#panel iframe", "waitFn": "window.LP && LP.ready"},
            {"do": "waitFn", "js": "[...document.querySelectorAll('.preview')].every(e=>"
             "{const i=e.shadowRoot.querySelector('img');return i && i.complete && i.naturalWidth>0})"},
            {"do": "eval", "js": "JSON.stringify({looks:document.querySelectorAll('#looks > .look-card').length,"
             "layouts:document.querySelectorAll('#layouts > .layout-card').length,"
             "frames:[...document.querySelectorAll('.preview')].map(e=>e.shadowRoot.querySelector('img').naturalWidth)})"},
            click('#replay'),
            {"do": "eval", "js": "JSON.stringify([...document.querySelectorAll('.preview')].map(e=>"
             "{const c=e.shadowRoot.querySelector('.caption');return !!c && c.getAnimations().some(a=>"
             "['running','finished'].includes(a.playState))}))"},
            click('#looks [data-look="bold-pop"]'), click('#mark-look'),
            {"do": "eval", "js": "JSON.stringify([...document.querySelectorAll('.preview')].map(e=>"
             "{const c=e.shadowRoot.querySelector('.caption');return !!c && c.getAnimations({subtree:true}).some(a=>"
             "a.effect.target!==c && a.effect.getKeyframes().some(k=>/^scaleX\\(/.test(k.transform||'')))}))"},
            click('#send'),
            {"do": "waitText", "sel": "#saved", "re": "saved|FAILED"}])
        need(rows[0]["looks"] == 5 and rows[0]["layouts"] == 5, f"picker cards: {rows[0]}")
        need(len(rows[0]["frames"]) == 10 and all(n > 0 for n in rows[0]["frames"]), "picker frame missing")
        need(len(rows[1]) == 10 and all(rows[1]), "Replay all missed a caption")
        need(len(rows[2]) == 10 and all(rows[2]), "Marker highlight missed a swipe")
        need(dest.is_file(), "Look Picker Send missing")
        doc = read(dest)
        need(doc["schema"] == 1 and doc["reel"] == d.name, "wrong picker envelope")
        need(doc["caption_style"] == {"style": "bold-pop", "mark_look": "marker",
             "under_small_overlays": True, "line_breaks": True, "echo_suppression": False,
             "loud_emphasis": False}, f"wrong picker options: {doc}")
        need(doc["make_default"] is False, "default was opted in")
        need(set(doc) == {"schema", "reel", "caption_style", "make_default", "sent_at"}, "layout leaked into Send")
        need(re.fullmatch(r".*[+-]\d{2}:\d{2}", doc.get("sent_at", "")) and
             dt.datetime.fromisoformat(doc["sent_at"]).utcoffset() is not None, "picker Send needs local ISO offset")
    check()
    live = p.editor / "look-picker/index.html"
    original = live.read_bytes()
    need(original.count(b"name=look-picker-selection.json") == 1, "look mutant anchor")
    live.write_bytes(original.replace(b"name=look-picker-selection.json", b"name=review.json"))
    try:
        p.bites(check, "Look Picker Send goes to forbidden filename")
    finally:
        live.write_bytes(original)


def case_review(p):
    latest = "reel-01 Preview 720p - 11.05.26.mp4"
    for reel in ("reel-01", "reel-02"):
        renders = p.videos / reel / "renders"
        for i, name in enumerate((f"{reel} Preview 720p - 11.04.26.mp4",
                                  f"{reel} Preview 720p - 11.05.26.mp4",
                                  f"{reel} Preview 720p - 11.06.26.partial.mp4",
                                  f"{reel} Preview 720p - 11.06.26.mp4.partial")):
            target = renders / name
            shutil.copyfile(p.clip, target)
            os.utime(target, (1700000000 + i, 1700000000 + i))
    (p.videos / "reel-02/renders/reel-02 Master - 11.05.26.mp4").unlink()
    data = p.refresh()
    need(data["reels"][0].get("preview_name") == latest, "latest finished preview name missing")
    need(data["reels"][0].get("preview_url", "").endswith("/" + latest.replace(" ", "%20")),
         "latest finished preview URL missing")
    def check():
        d = p.videos / "reel-01"
        (d / "review.json").unlink(missing_ok=True)
        r = p.snapshot("({preview:document.querySelector('#preview')?.getAttribute('src'),master:document.querySelector('#master')?.getAttribute('src'),qa:document.querySelector('#qa').textContent})",
            [click('#tab-review'), {"do": "frame", "sel": "#panel iframe", "waitFn": "window.ReviewReady"},
             {"do": "set", "sel": "#review-note", "value": "Keep the ending"}, click('#approve'),
             {"do": "waitText", "sel": "#status", "re": "Sent|Could not"}])
        need(r["preview"] == "/videos/reel-01/renders/" + latest.replace(" ", "%20"), f"review preview: {r}")
        need(r["master"] and "Loudness" in r["qa"] and "Ready to post" in r["qa"], f"review missing master/QA: {r}")
        need((d / "review.json").is_file(), "review Send missing")
        doc = read(d / "review.json")
        need(set(doc) == {"approve", "preview", "note", "sent_at"} and doc["approve"] is True
             and doc["preview"] == latest and doc["note"] == "Keep the ending", f"review Send: {doc}")
        need(dt.datetime.fromisoformat(doc["sent_at"].replace("Z", "+00:00")).tzinfo is not None,
             "review timestamp must be ISO with timezone")
    check()
    empty = p.snapshot("({qa:document.querySelector('#qa').textContent,master:document.querySelector('#master').getAttribute('src')})",
             [click('#tab-review'), {"do": "frame", "sel": "#panel iframe", "waitFn": "window.ReviewReady"},
              click('#approve'), {"do": "waitText", "sel": "#status", "re": "Sent|Could not"}], reel="reel-02")
    need("QA hasn't run yet" in empty["qa"] and not empty["master"], "preview-only review/QA empty state missing")
    doc = read(p.videos / "reel-02/review.json")
    need(doc["approve"] is True and doc["preview"] == latest.replace("reel-01", "reel-02"),
         "approval must work before a master exists")
    fallback = p.snapshot("document.querySelector('#fallback-line').value", [click('#tab-review'),
             {"do": "frame", "sel": "#panel iframe", "waitFn": "window.ReviewReady"},
             {"do": "eval", "js": "HubIO.send=async()=>{throw new Error('offline')}"}, click('#send-review'),
             {"do": "waitText", "sel": "#status", "re": "Could not"}])
    need("save review.json" in fallback, f"fallback must name review.json: {fallback}")
    with p.mutant("review.js", 'await io.send(reel, "review.json", body)', 'await io.send(reel, "hub-requests.json", body)'):
        p.bites(check, "review saved to wrong file")


def case_sends(p):
    d = p.videos / "reel-01"
    def check():
        for n in ("reel-notes.json", "hub-requests.json"):
            (d / n).unlink(missing_ok=True)
        p.browse([{"do": "set", "sel": "#note", "value": "Keep the laugh"}, click('#notes-send'),
                  {"do": "waitText", "sel": "#status", "re": "Sent|Could not"},
                  click('[data-skill="captions"]'), click('[data-skill="captions"]'),
                  {"do": "waitFn", "js": "Hub.pending===0"}])
        need((d / "reel-notes.json").is_file(), "notes Send missing")
        need(read(d / "reel-notes.json")[-1]["text"] == "Keep the laugh", "wrong note")
        need((d / "hub-requests.json").is_file() and len(read(d / "hub-requests.json")) == 2, "two clicks did not append two requests")
    check()
    with p.mutant("hub.js", "const list = previous.concat(entry);", "const list = [entry];"):
        p.bites(check, "requests overwrite earlier Sends")


def case_health(p):
    def check():
        r = p.snapshot("({health:document.querySelector('#health-list').textContent,gold:document.querySelector('#gold-data').textContent})")
        need("Video tools are ready" in r["health"] and "Motion needs setup" in r["health"], "STATUS details missing")
        need("123" in r["gold"] and "n =" in r["gold"] and "7" in r["gold"], "Goldmine export/n missing")
    check()
    with p.mutant("hub.js", "const gold = DATA.goldmine;", "const gold = null;"):
        p.bites(check, "fixture export ignored")
    (p.ws / "reel-build/goldmine-run.json").unlink()
    p.refresh()
    need("A run uses your SocialCrawl credits" in p.snapshot("document.querySelector('#gold-data').textContent"), "Goldmine empty state")


def case_filmstrip(p):
    data = read(p.hub / "hub-data.json")
    # Execute the actual Cockpit rules on exactly these disk listings, rather than copying the expected stage.
    logic = p.plugin / "hooks/mod/logic.ts"
    module = p.scratch / "logic.mjs"
    stripped = p.run([p.tools["node"], "--input-type=module", "-e",
        "import{stripTypeScriptTypes}from'node:module';import fs from'node:fs';process.stdout.write(stripTypeScriptTypes(fs.readFileSync(process.argv[1],'utf8')))", logic])
    module.write_bytes(stripped.stdout.encode("utf-8"))
    reel = p.videos / "reel-01"
    listing = {}
    for f in ("root", "raw", "work", "renders"):
        folder = reel if f == "root" else reel / f
        listing[f] = {"status": "ok", "value": [{"name": x.name, "kind": "file" if x.is_file() else "dir",
                      "size": x.stat().st_size, "mtimeMs": x.stat().st_mtime * 1000} for x in folder.iterdir()]}
    inp = p.scratch / "logic-input.json"
    write(inp, {"name": reel.name, "lists": listing, "json": {}, "probe": {}})
    got = p.run([p.tools["node"], "--input-type=module", "-e",
        "import fs from'node:fs';const m=await import(process.argv[1]);const r=m.reelOf(JSON.parse(fs.readFileSync(process.argv[2])),Date.now(),undefined,{});console.log(m.STAGES[r.cur].name)", module.as_uri(), inp])
    need(data["reels"][0]["stage"] == got.stdout.strip(), f"Cockpit stage mismatch: {got.stdout}")
    frames = list((p.hub / "frames/reel-01").glob("*.jpg"))
    stamps = [x.stat().st_mtime_ns for x in sorted(frames)]
    p.refresh()
    need(stamps == [x.stat().st_mtime_ns for x in sorted(frames)], "frames recut without newer render")
    def check():
        r = p.snapshot("({frames:document.querySelectorAll('#strip img').length,nle:!!document.querySelector('#nle'),steps:document.querySelector('#steps').textContent})",
            [{"do": "waitFn", "js": "[...document.querySelectorAll('#strip img')].every(i=>i.complete && i.naturalWidth>0)"}])
        need(r["frames"] == 12 and not r["nle"] and "Directions" not in r["steps"], f"filmstrip/stages/NLE: {r}")
    check()
    with p.mutant("hub.js", "const frames = r.frames;", "const frames = r.frames.slice(0, 11);"):
        p.bites(check, "one filmstrip frame missing")


def case_layout(p):
    def check():
        (p.videos / "reel-01/hub.state.json").unlink(missing_ok=True)
        initial, r = p.browse([{"do": "eval", "js": "JSON.stringify({layout:document.body.dataset.layout,rail:getComputedStyle(document.querySelector('#reel-list')).display})"}, click('#layout'),
            {"do": "waitFn", "js": "Hub.pending===0"},
            {"do": "goto", "path": "/editor/hub/?reel=reel-02", "waitFn": "window.Hub && Hub.ready"},
            {"do": "eval", "js": "JSON.stringify({layout:document.body.dataset.layout,rail:getComputedStyle(document.querySelector('#reel-list')).display})"}])
        need(initial == {"layout": "guided", "rail": "none"}, f"default layout: {initial}")
        need(r == {"layout": "full", "rail": "block"}, f"layout not remembered across reload/reel: {r}")
        need(read(p.videos / "reel-01/hub.state.json")["layout"] == "full", "layout not in server state")
    check()
    with p.mutant("hub.js", 'body: JSON.stringify(state)', 'body: JSON.stringify({...state, layout:"guided"})'):
        p.bites(check, "layout not persisted")


def case_attention(p):
    def check():
        text = p.snapshot("document.querySelector('#attention').textContent")
        need("A word is clipped at the opening" in text and "0:01" in text, f"map blocks absent: {text}")
    check()
    need("A word is clipped" not in p.snapshot("document.querySelector('#attention').textContent", reel="reel-02"), "absent map_check displays block")
    with p.mutant("hub.js", "const blocks = r.blocks;", "const blocks = [];"):
        p.bites(check, "map_check blocks ignored")


def case_sync(p):
    def check():
        f = p.hub / "hub-data.json"
        original = f.read_bytes()
        (p.hub / ".board-version").unlink(missing_ok=True)
        p.py(p.doctor / "board_sync.py", "--root", p.ws)
        need(f.read_bytes() == original, "board sync overwrote hub data")
    check()
    template = p.plugin / "skills/editor-doctor/boards/hub/hub-data.json"
    write(template, {"mutant": "template overwrites generated data"})
    try:
        p.bites(check, "generated data shipped as template")
    finally:
        template.unlink()


def case_edit_style(p):
    """H-HUB-1: the real Beat Map iframe saves, sends and restores the client's style."""
    sys.path.insert(0, str(HERE))
    import canvas_boards_test as fixture
    canvas = p.plugin / "skills/reel-canvas-build/scripts"
    sys.path.insert(0, str(canvas))
    import beat_schema, styles
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    p.py(canvas / "make_beat_map.py", "--reel-dir", d, "--plan", d / "work/plan.json")
    seeded = read(d / "beat-map.state.json")
    heard = beat_schema.load_words(d / beat_schema.DEFAULT_WORDS)
    word = 2  # initially unmarked; the browser cycles it to stress after enabling punches
    expected = {"style": "punch-in", "punch_scale": 1.18, "moves": {
        "opening_settle": False, "follow_cam": True,
        "word_punches": {"preset": "dramatic", "shape": "hard-cut", "picks": [word]}}}

    def open_map():
        # The board's Send bar is fixed to the bottom of the tab's frame: bring the whole frame into the window first.
        return [click('#tab-beat-map'), {"do": "waitFn", "js": "!!document.querySelector('#panel iframe')"},
                {"do": "eval", "js": "document.querySelector('#panel iframe').scrollIntoView({block: 'end'}), 0"},
                {"do": "frame", "sel": "#panel iframe",
                "wait": "#board:not([hidden]) #edit-style"}]

    def set_value(sel, value):
        return {"do": "set", "sel": sel, "value": value}

    def sent(actions):
        (d / "beat-map-selection.json").unlink(missing_ok=True)
        p.browse(open_map() + actions + [click('#send'),
                 {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])
        need((d / "beat-map-selection.json").is_file(), "Beat Map Send missing")
        doc = read(d / "beat-map-selection.json")
        need(not beat_schema.beat_map_problems(doc, heard), "Send fails the beat map schema")
        if "edit_style" in doc:
            styles.check_style(doc["edit_style"], "reel", len(heard))
        return doc

    def punch_check():
        write(d / "beat-map.state.json", seeded)
        doc = sent([set_value('#edit-style', 'punch-in'), set_value('#punch-scale', '1.18'),
                    click('#follow-cam'), set_value('#word-punches', 'dramatic'),
                    set_value('#punch-shape', 'hard-cut'),
                    {"do": "waitFn", "js": "!document.querySelector('#punch-hint').hidden && "
                     "document.querySelector('#punch-hint').textContent === "
                     "'Mark the words to stress first; the punches land on them.'"},
                    *[click(f'.word[data-w="{word}"]') for _ in range(3)]])
        need(doc.get("edit_style") == expected, f"punch Send differs: {doc.get('edit_style')}")
        need(read(d / "beat-map.state.json").get("edit_style") == expected, "style not saved in state")

    empty = sent([set_value('#edit-style', 'punch-in'), set_value('#word-punches', 'dramatic')])
    need(empty["edit_style"]["moves"]["word_punches"]["picks"] == [], "unmarked words became punch picks")
    punch_check()
    doc = sent([set_value('#edit-style', 'layout-switch')])
    need(doc.get("edit_style") == {"style": "layout-switch"}, "layout switch carries punch options")
    doc = sent([set_value('#edit-style', '')])
    need("edit_style" not in doc, "Ask me must omit edit_style")
    # This is the exact style planner called by compose.render's H-R36 preflight.
    # Supply the fixture's frame rate, as compose does; no synthetic video render is needed.
    with patch.object(styles.rt, "state_dir", return_value=p.scratch / "no-saved-style"):
        try:
            styles.plan(d, fps=str(fixture.FPS))
        except styles.Stop as e:
            need(e.code == 1 and e.lines == (styles.ASK,), f"wrong Ask me stop: {e.lines}")
        else:
            raise AssertionError("Ask me round-trip did not stop the preview's style planner")

    # Save on change without Send, then load with browse's next fresh browser profile.
    p.browse(open_map() + [set_value('#edit-style', 'punch-in'), set_value('#punch-scale', '1.18'),
             click('#opening-settle'), click('#follow-cam'), set_value('#word-punches', 'subtle'),
             {"do": "waitState", "board": "beat-map", "js": "s.edit_style?.style==='punch-in' && "
              "s.edit_style.punch_scale===1.18 && s.edit_style.moves.opening_settle && "
              "s.edit_style.moves.follow_cam && s.edit_style.moves.word_punches?.preset==='subtle'"}])
    restored = p.browse(open_map() + [{"do": "eval", "js": "JSON.stringify({style:"
        "document.querySelector('#edit-style').value,scale:document.querySelector('#punch-scale').value,"
        "settle:document.querySelector('#opening-settle').checked,follow:document.querySelector('#follow-cam').checked,"
        "words:document.querySelector('#word-punches').value,shape:document.querySelector('#punch-shape').value})"}])[-1]
    need(restored == {"style": "punch-in", "scale": "1.18", "settle": True, "follow": True,
                      "words": "subtle", "shape": "eased"}, f"fresh profile did not restore saved controls: {restored}")

    # Loading must preserve a valid saved level beyond the quick control's usual range.
    saved = read(d / "beat-map.state.json")
    saved["edit_style"] = dict(expected, punch_scale=1.43)
    write(d / "beat-map.state.json", saved)
    restored = p.browse(open_map() + [{"do": "eval", "js": "JSON.stringify({scale:"
        "document.querySelector('#punch-scale').value,follow:document.querySelector('#follow-cam').checked,"
        "words:document.querySelector('#word-punches').value,shape:document.querySelector('#punch-shape').value})"}])[-1]
    need(restored == {"scale": "1.43", "follow": True, "words": "dramatic", "shape": "hard-cut"},
         f"saved controls changed on load: {restored}")
    need(sent([]).get("edit_style") == saved["edit_style"], "out-of-range saved level changed on Send")

    # A Send alone also opens with its controls when there is no saved board state.
    (d / "beat-map.state.json").unlink()
    restored = p.browse(open_map() + [{"do": "eval", "js": "document.querySelector('#punch-scale').value"}])[-1]
    need(str(restored) == "1.43", f"Send style did not load: {restored}")
    with p.mutant("../beat-map/index.html", "body: JSON.stringify(doc)",
                  "body: JSON.stringify({...doc, edit_style: undefined})"):
        p.bites(punch_check, "Beat Map drops edit_style from Send")

    def ratchet_check():
        write(d / "beat-map.state.json", seeded)
        doc = sent([set_value('#edit-style', 'punch-in'), set_value('#word-punches', 'ratchet'),
                    *[click(f'.word[data-w="{word}"]') for _ in range(3)],
                    {"do": "waitFn", "js": "document.querySelector('#punch-shape-options').hidden"}])
        moves = doc.get("edit_style", {}).get("moves", {})
        need(moves.get("ratchet") == {"picks": [word], "levels": 3}, f"ratchet Send differs: {moves}")
        need(moves.get("word_punches", "missing") is None, "ratchet also enables word punches")

    ratchet_check()
    doc = sent([set_value('#camera-move', 'push')])
    moves = doc["edit_style"]["moves"]
    need(moves.get("push") == {"segments": "all", "to": 1.06}, f"push Send differs: {moves}")
    need(not moves.get("ken_burns") and not moves.get("reframe"), "push also enables another camera move")
    for choice, key, value in (("ken_burns", "ken_burns", {"segments": "all", "to": 1.08}),
                               ("reframe", "reframe", {"segments": "all", "edge": "top"}), ("", None, None)):
        doc = sent([set_value('#camera-move', choice)])
        moves = doc["edit_style"]["moves"]
        need(all(moves.get(n) == (value if n == key else None) for n in ("push", "ken_burns", "reframe")),
             f"camera choice {choice} differs: {moves}")

    custom = {"ratchet": {"picks": [word], "levels": 4}, "word_punches": None,
              "reframe": {"segments": [1], "edge": "bottom"}}
    for camera in ({"reframe": custom["reframe"]}, {"push": {"segments": [1], "to": 1.17}},
                   {"ken_burns": {"segments": "all", "to": 1.23}}):
        saved = dict(seeded, edit_style={"style": "punch-in", "punch_scale": 1.12,
            "moves": {"opening_settle": False, "follow_cam": False,
                      "ratchet": custom["ratchet"], "word_punches": None, **camera}})
        write(d / "beat-map.state.json", saved)
        doc = sent([{"do": "waitFn", "js": "document.querySelector('#word-punches').value === 'custom' && "
                     "document.querySelector('#camera-move').value === 'custom'"},
                    set_value('#punch-scale', '1.20')])
        need(doc["edit_style"] == dict(saved["edit_style"], punch_scale=1.20),
             f"unrelated edit changed custom moves: {doc['edit_style']}")
    doc = sent([set_value('#word-punches', 'ratchet'), set_value('#camera-move', 'push')])
    need(doc["edit_style"]["moves"]["ratchet"] == {"picks": [], "levels": 3}, "ratchet choice kept custom levels")
    need(doc["edit_style"]["moves"]["push"] == {"segments": "all", "to": 1.06}, "push choice kept custom settings")
    with p.mutant("../beat-map/index.html", "body: JSON.stringify(doc)",
                  "body: JSON.stringify({...doc, edit_style: {...doc.edit_style, moves: {...doc.edit_style.moves, ratchet: undefined}}})"):
        p.bites(ratchet_check, "Beat Map drops moves.ratchet from Send")


def case_broll(p):
    """H-HUB-1: own B-roll picks survive one Send through the real hub and a reload."""
    sys.path.insert(0, str(HERE))
    import canvas_boards_test as fixture
    canvas = p.plugin / "skills/reel-canvas-build/scripts"
    sys.path.insert(0, str(canvas))
    import beat_schema
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    p.py(canvas / "make_beat_map.py", "--reel-dir", d, "--plan", d / "work/plan.json")
    seeded = read(d / "beat-map.state.json")
    heard = beat_schema.load_words(d / beat_schema.DEFAULT_WORDS)
    clip = {"src": "broll/ingested/own.mp4", "ledger_id": "f01", "name": "My own clip.mov",
            "frames": 900, "width": 1536, "height": 1920, "origin": "own"}
    short = dict(clip, src="broll/ingested/short.mp4", ledger_id="f02", name="Too short.mov", frames=1)
    ai = dict(clip, src="broll/ingested/ai.mp4", ledger_id="f03", name="Garden.mp4", origin="ai",
              job_id="test-123", request_sha256="a" * 64)
    write(d / "broll/clips.json", {"fps": fixture.FPS, "clips": [clip, short, ai]})
    start = round(0.2 * fixture.FPS)
    length = seeded["beats"][0]["end_f"] - seeded["beats"][0]["start_f"]
    expected = {"src": clip["src"], "in": start, "out": start + length, "fit": "blur-fill", "ledger_id": "f01"}

    def open_map():
        return [click('#tab-beat-map'), {"do": "waitFn", "js": "!!document.querySelector('#panel iframe')"},
                {"do": "eval", "js": "document.querySelector('#panel iframe').scrollIntoView({block:'end'}), 0"},
                {"do": "frame", "sel": "#panel iframe", "wait": "#board:not([hidden]) #broll-0"}]

    def set_value(sel, value):
        return {"do": "set", "sel": sel, "value": value}

    def sent(actions):
        (d / "beat-map-selection.json").unlink(missing_ok=True)
        p.browse(open_map() + actions + [click('#send'),
                 {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])
        need((d / "beat-map-selection.json").is_file(), "Beat Map Send missing")
        doc = read(d / "beat-map-selection.json")
        need(not beat_schema.beat_map_problems(doc, heard), "B-roll Send fails beat schema")
        return doc

    def pick_check():
        write(d / "beat-map.state.json", seeded)
        doc = sent([set_value('#broll-0', 'f01'), set_value('#broll-fit-0', 'blur-fill'),
                    set_value('#broll-start-0', '0.2')])
        need(doc["beats"][0].get("broll") == expected, f"B-roll Send differs: {doc['beats'][0].get('broll')}")
        need(read(d / "beat-map.state.json")["beats"][0]["broll"] == expected, "B-roll not saved in state")

    labels = p.browse(open_map() + [{"do": "eval", "js":
        "JSON.stringify(Array.from(document.querySelector('#broll-0').options, o => o.textContent))"}])[-1]
    need(labels == ["None", "My own clip.mov", "Too short.mov", "Garden.mp4 (AI)"],
         f"AI option label differs: {labels}")
    ai_doc = sent([set_value('#broll-0', 'f03')])
    need(ai_doc["beats"][0]["broll"] == {"src": ai["src"], "in": 0, "out": length,
         "fit": "cover", "ledger_id": "f03"}, "AI picker did not send its ledger id")
    pick_check()
    restored = p.browse(open_map() + [{"do": "eval", "js": "JSON.stringify({clip:document.querySelector('#broll-0').value,"
        "fit:document.querySelector('#broll-fit-0').value,start:document.querySelector('#broll-start-0').value})"}])[-1]
    need(restored == {"clip": "f01", "fit": "blur-fill", "start": "0.2"}, f"B-roll controls not restored: {restored}")
    need(sent([])["beats"][0]["broll"] == expected, "loading changed saved B-roll")
    (d / "beat-map-selection.json").unlink()
    p.browse(open_map() + [set_value('#broll-0', 'f02'), click('#send'),
             {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='error' && "
              "document.querySelector('#status').textContent.includes('B-roll clip is too short')"}])
    need(not (d / "beat-map-selection.json").exists(), "short B-roll was sent")
    need(sent([set_value('#broll-0', '')])["beats"][0]["broll"] is None, "None did not clear B-roll")
    with p.mutant("../beat-map/index.html", "body: JSON.stringify(doc)",
                  "body: JSON.stringify({...doc, beats: doc.beats.map(b => ({...b, broll: null}))})"):
        p.bites(pick_check, "Beat Map drops B-roll from Send")
    # A saved choice survives an unrelated edit even when the catalog is absent.
    pick_check()
    (d / "broll/clips.json").unlink()
    p.browse(open_map() + [{"do": "waitFn", "js": "document.querySelector('#broll-0').disabled && "
        "document.querySelector('#broll-0').options.length===1 && "
        "document.querySelector('#broll-0').selectedIndex===0 && "
        "document.querySelector('#broll-0').textContent.includes('Drop your clips')"}])
    need(sent([set_value('#note-0', 'Keep my saved clip')])["beats"][0]["broll"] == expected,
         "missing catalog changed saved B-roll")


def data_checks(p):
    """Useful proof in a sandbox that cannot take the shared browser lock; never substitutes for the UI cases."""
    data = p.refresh()
    need([r["id"] for r in data["reels"]] == ["reel-01", "reel-02"], "disk reel enumeration")
    manifest = read(p.doctor / "boards.json")["boards"]
    need([b["id"] for b in data["boards"]] == sorted([k for k,v in manifest.items() if "tab" in v],
         key=lambda k: manifest[k]["tab"]["order"]), "manifest tabs")
    need(all(b["built"] == (p.editor / b["id"] / "index.html").is_file() for b in data["boards"]), "built tab detection")
    need(data["config"]["nle"] == "none" and "Directions" not in [s["name"] for s in data["stages"]], "NLE/stages")
    need(data["goldmine"]["n"] == 123 and data["goldmine"]["breakouts"] == 7, "Goldmine pointer")
    need(data["health"][1]["detail"] == "Motion needs setup", "Health STATUS entries")
    need(data["reels"][0]["blocks"][0]["msg"] == "A word is clipped at the opening" and not data["reels"][1]["blocks"], "attention blocks")
    need(data["reels"][0]["cover_url"].endswith("/cover.jpg"), "cover metadata/image")
    need(all(len(r["frames"]) == 12 for r in data["reels"]), "12 generated filmstrip frames per rendered reel")
    stamps = {f: f.stat().st_mtime_ns for f in (p.hub / "frames").rglob("*.jpg")}
    p.refresh()
    need(stamps == {f: f.stat().st_mtime_ns for f in stamps}, "frame cache")
    print("PASS data: reel folders, manifest tabs, Health, Goldmine, cover, QA, attention, 24 frames + cache", flush=True)

    # Import the builder, then compare its stage and open Sends with the actual TypeScript on each disk fixture.
    spec = importlib.util.spec_from_file_location("hub_rows_proof", p.doctor / "hub_rows.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    module = p.scratch / "cockpit.mjs"
    stripped = p.run([p.tools["node"], "--input-type=module", "-e",
        "import{stripTypeScriptTypes}from'node:module';import fs from'node:fs';process.stdout.write(stripTypeScriptTypes(fs.readFileSync(process.argv[1],'utf8')))", p.plugin / "hooks/mod/logic.ts"])
    module.write_bytes(stripped.stdout.encode("utf-8"))
    d = p.videos / "reel-01"
    snap = {"baseline": 0, "acked": {}}
    write(p.hub / "cockpit-state.json", snap)
    def parity(expected):
        lists, js = {}, {}
        for name in ("root", "raw", "work", "renders"):
            folder = d if name == "root" else d / name
            lists[name] = {"status": "ok", "value": [{"name": f.name, "kind": "file" if f.is_file() else "dir",
                          "size": f.stat().st_size, "mtimeMs": f.stat().st_mtime*1000} for f in folder.iterdir()]}
        for name in ("beat-map.state.json", "sketches.state.json"):
            js[name] = {"status": "ok", "value": read(d/name)} if (d/name).exists() else {"status": "missing"}
        inp = p.scratch / "parity.json"
        write(inp, {"reel": {"name": d.name, "lists": lists, "json": js, "probe": {}}, **snap})
        out = p.run([p.tools["node"], "--input-type=module", "-e",
            "import fs from'node:fs';const m=await import(process.argv[1]);const i=JSON.parse(fs.readFileSync(process.argv[2]));const r=m.reelOf(i.reel,Date.now(),i.baseline,i.acked);console.log(JSON.stringify({stage:m.STAGES[r.cur].name,done:r.done,sends:r.sends.map(s=>s.file)}))", module.as_uri(), inp])
        cockpit = json.loads(out.stdout.strip())
        row = mod.build(p.ws, p.plugin)["reels"][0]
        need(row["stage"] == cockpit["stage"] == expected, f"stage parity {expected}: {row['stage']}/{cockpit['stage']}")
        need(row["done"] == cockpit["done"], f"done parity at {expected}")
        need([s["file"] for s in row["open_sends"]] == cockpit["sends"], f"Send parity at {expected}")
    raw = d / "raw/take.mp4"
    raw.unlink()
    parity("Record")
    shutil.copyfile(p.clip, raw)
    cuts = d / "work/cuts.json"
    cuts.unlink()
    parity("Cut")
    write(cuts, {"segments": []})
    parity("Ear pass")
    write(d / "tweak-selection.json", {})
    parity("Beat map")
    write(d / "beat-map.state.json", {"sent_at": 0})  # != null, not a truthiness test
    parity("Motion")
    write(d / "sketches.state.json", {"locked_at": "2026-11-05T12:00:00Z"})
    parity("Sound")
    master = next((d / "renders").glob("*.mp4"))
    master.unlink()
    write(d / "sound-selection.json", {})
    parity("Master")  # optional Grade does not block
    shutil.copyfile(p.clip, master)
    parity("Post")
    for name in ("tweak-selection.json", "sound-selection.json"):
        snap["acked"][f"{d.name}/{name}"] = (d/name).stat().st_mtime*1000
    write(p.hub / "cockpit-state.json", snap)
    parity("Post")
    print("PASS data: executed logic.ts parity at all 8 mandatory stages, optional Grade skipped, Send baseline/acks/downstream", flush=True)

    p.start()
    def post(name):
        c = http.client.HTTPConnection("127.0.0.1", p.port, timeout=5)
        c.request("POST", f"/videos/reel-01/__save?board=hub&name={name}", body='{"fixture":true}',
                  headers={"Origin": p.base, "Content-Type": "application/json"})
        status = c.getresponse().status
        c.close()
        return status
    for name in ("review.json", "reel-notes.json", "hub-requests.json"):
        need(post(name) == 200 and read(d/name) == {"fixture": True}, f"server Send round-trip: {name}")
    need(post("unlisted.json") == 403, "server refused unlisted Send")
    print("PASS data: all three hub Send filenames round-trip through the server; unlisted name refused", flush=True)
    case_sync(p)
    (p.ws / "reel-build/goldmine-run.json").unlink()
    need(mod.goldmine(p.ws) is None, "missing Goldmine pointer must not revive old numbers")
    print("PASS data: no-pointer Goldmine empty state + sync positive/mutant", flush=True)


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=NAMES + [str(n) for n in range(1, len(NAMES) + 1)] + ["all"], default="all")
    ap.add_argument("--data-only", action="store_true", help="run the non-browser fixture/server/stage checks only")
    a = ap.parse_args()
    selected = ["data"] if a.data_only else NAMES if a.case == "all" else [NAMES[int(a.case)-1] if a.case.isdigit() else a.case]
    base = Path(tempfile.gettempdir()) / "editor-hub-test"
    base.mkdir(parents=True, exist_ok=True)
    failed = blocked = 0
    for name in selected:
        scratch = Path(tempfile.mkdtemp(prefix=f"hub-{name}-", dir=base))
        proof = None
        start = time.monotonic()
        # Hard cap includes fixture preparation, locks, browsers and mutant.
        watchdog = threading.Timer(165, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        try:
            proof = Proof(scratch)
            with patch.dict(os.environ, proof.env):
                proof.refresh()
                (data_checks if name == "data" else globals()["case_" + name])(proof)
            print(f"PASS {name} ({time.monotonic()-start:.1f}s), positive + mutant", flush=True)
        except Blocked as e:
            blocked += 1
            print(f"BLOCKED {name}: {e}", flush=True)
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}", flush=True)
        finally:
            watchdog.cancel()
            if proof:
                proof.close()
            shutil.rmtree(scratch)
    print(f"{len(selected)-failed-blocked} passed, {failed} failed, {blocked} blocked")
    return 1 if failed else 77 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
