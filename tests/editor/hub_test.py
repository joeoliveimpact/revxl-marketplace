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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import copy_tool_state

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins/editor-superengine"
sys.path.insert(0, str(PLUGIN / "skills/_shared"))
import runtime as rt
from win_encoding import ensure_utf8_output

HEAVY = Path("C:/Workspaces/Content Studio/output/scripts/heavy_lock.py")
NAMES = ["reels", "tabs", "grade", "review", "sends", "health", "filmstrip", "layout", "attention", "sync", "edit_style", "look", "broll", "styles", "reminder_holds", "strong_beats"]
NAMES.append("storyboard")
NAMES.append("rapid_sends")
NAMES.append("walk_polish")
NAMES.append("full_view")


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
        home = copy_tool_state(rt.state_dir(), scratch / "state")
        self.env = rt.python_env(base=dict(os.environ, HOME=str(scratch / "home"),
                              USERPROFILE=str(scratch / "home"), TMP=str(scratch / "tmp"),
                              TEMP=str(scratch / "tmp"), TMPDIR=str(scratch / "tmp"),
                              EDITOR_SE_HOME=str(home)))
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
            # The Cockpit now lists sound/ too; keep the hand-built parity input complete.
            (d / "sound").mkdir()
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
        write(self.ws / "reel-build/manifest.json", {"count": 7, "breakouts": [
              {"id": "SC0DE1x", "hook_line": "Stop posting every day"}]})
        write(self.ws / "reel-build/popularity.json", {"corpus": {"reels_total": 123, "creators": 4},
              "breakout_ranking": [{"benchmark_x": 2.5, "comment_rate": 0.02},
                                   {"shortcode": "SC0DE1x", "benchmark_x": 287.479, "comment_rate": 0.041184951443}]})

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

    def browse(self, actions=(), reel="reel-01", viewport=None):
        self.start()
        self.jobs += 1
        job = self.scratch / f"job-{self.jobs}.json"
        write(job, {"base": self.base, "userDataDir": str(self.scratch / f"profile-{self.jobs}"),
                    "viewport": viewport,
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
    # Read contrast in the same task as selection, before a colour transition can finish.
    for layout in ("guided", "full"):
        contrast = p.browse([{"do": "eval", "js": """(() => {
            document.body.dataset.layout = %s;
            const tab = document.querySelector('#tab-grade-board'); tab.click();
            const style = getComputedStyle(tab);
            const luminance = colour => colour.match(/[\\d.]+/g).slice(0,3).map(Number)
              .map(c => c/255).map(c => c <= .04045 ? c/12.92 : ((c+.055)/1.055)**2.4)
              .reduce((sum,c,i) => sum+c*[.2126,.7152,.0722][i],0);
            const a=luminance(style.color), b=luminance(style.backgroundColor);
            return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
        })()""" % json.dumps(layout)}], viewport={"width": 1024, "height": 768})[-1]
        need(contrast >= 4.5, f"selected tab contrast in {layout}: {contrast}")
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
                  {"do": "waitText", "sel": "#saved", "re": "✓ Sent to Claude at |FAILED"}])
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
    # Keep remembered picks in an owned home; installed tools remain read only.
    pick_home = p.scratch / "pick-state"
    write(pick_home / "state.json", {"components": {"fixture": {"bins": {
        key: rt.tool(key) for key in ("ffmpeg", "ffprobe", "node", "chrome")}}}})
    p.env["EDITOR_SE_HOME"] = str(pick_home)
    p.py(p.plugin / "skills/_shared/standing_notes.py", "pick", "caption_style.style",
         "--value", '"boxed"', "--note", "Keep it framed")
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
    bm.update(sent_at="2026-11-05T12:00:00-05:00")
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
        opening = p.browse([click('#tab-look-picker'),
            {"do": "frame", "sel": "#panel iframe", "waitFn": "window.LP && LP.ready"},
            {"do": "eval", "js": "JSON.stringify({badges:[...document.querySelectorAll('#look-choices small')]"
             ".filter(e=>e.textContent==='Your last pick').map(e=>e.closest('[data-look]').dataset.look),"
             "picked:document.querySelector('#look-choices [aria-checked=true]')?.dataset.look,"
             "disabled:document.querySelector('#send').disabled})"}])
        need(opening[0] == {"badges": ["boxed"], "picked": "boxed", "disabled": False}, f"remembered look (not sent on this reel yet, so Send is ready): {opening}")
        need(not dest.exists(), "Opening the Look Picker sent the remembered look")
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
            {"do": "eval", "js": "JSON.stringify({enabled:!document.querySelector('#send').disabled,"
             "text:document.querySelector('#saved').textContent,colour:getComputedStyle(document.querySelector('#saved')).color})"},
            click('#send'),
            {"do": "waitText", "sel": "#saved", "re": "^Sent\\b|FAILED"},
            {"do": "eval", "js": "JSON.stringify({text:document.querySelector('#saved').textContent,"
             "disabled:document.querySelector('#send').disabled})"}])
        need(rows[0]["looks"] == 5 and rows[0]["layouts"] == 5, f"picker cards: {rows[0]}")
        need(len(rows[0]["frames"]) == 10 and all(n > 0 for n in rows[0]["frames"]), "picker frame missing")
        need(len(rows[1]) == 10 and all(rows[1]), "Replay all missed a caption")
        need(len(rows[2]) == 10 and all(rows[2]), "Marker highlight missed a swipe")
        need(rows[3]["enabled"] and rows[3]["text"] == "Changes not sent." and
             rows[3]["colour"] != "rgb(98, 214, 154)", f"dirty look status: {rows[3]}")
        need(rows[4]["text"].startswith("Sent.") and rows[4]["disabled"], f"first Send: {rows[4]}")
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
        failed = p.browse([click('#tab-look-picker'),
            {"do": "frame", "sel": "#panel iframe", "waitFn": "window.LP && LP.ready"},
            click('#none'), {"do": "eval", "js": "const realFetch=window.fetch; window.fetch=(url,...args)=>"
             "String(url).includes('__save?')?Promise.resolve(new Response('{}',{status:500})):realFetch(url,...args); 0"},
            click('#send'), {"do": "waitFn", "js": "/FAILED/.test(document.querySelector('#saved').textContent)"},
            {"do": "eval", "js": "JSON.stringify({error:document.querySelector('#saved').classList.contains('error'),"
             "colour:getComputedStyle(document.querySelector('#saved')).color,enabled:!document.querySelector('#send').disabled})"}])[-1]
        need(failed == {"error": True, "colour": "rgb(255, 147, 130)", "enabled": True}, f"send failure: {failed}")
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
    d = p.videos / "reel-01"
    aids = {"strips": ["work/qa/cut-01.png", "work/qa/cut 02.png"],
            "contact": "work/qa/contact.jpg", "phone": "work/qa/phone-720p.mp4"}
    (d / "work/qa").mkdir()
    for rel in aids["strips"] + [aids["contact"]]:
        shutil.copyfile(d / "cover.jpg", d / rel)
    shutil.copyfile(p.clip, d / aids["phone"])
    qa = read(d / "work/qa.json")
    qa["aids"] = aids
    write(d / "work/qa.json", qa)
    data = p.refresh()
    need(data["reels"][0].get("preview_name") == latest, "latest finished preview name missing")
    need(data["reels"][0].get("preview_url", "").endswith("/" + latest.replace(" ", "%20")),
         "latest finished preview URL missing")
    def check():
        d = p.videos / "reel-01"
        (d / "review.json").unlink(missing_ok=True)
        _, _, before, status, approve, notes, r = p.browse(
            [click('#tab-review'), {"do": "frame", "sel": "#panel iframe", "waitFn": "window.ReviewReady"},
             {"do": "set", "sel": "#review-note", "value": "Keep the ending"},
             {"do": "eval", "js": "document.querySelector('#approve').scrollIntoView({block:'center'}); undefined"},
             {"do": "waitFn", "js": "[...document.querySelectorAll('#qa-aids img')].every(i=>i.complete && i.naturalWidth>0)"
              " && document.querySelector('#preview').readyState>=1 && document.querySelector('#master').readyState>=1"},
             {"do": "eval", "js": "const e=document.querySelector('#approve'); e.scrollIntoView({block:'center'});"
              " parent.scrollBy(0,frameElement.getBoundingClientRect().top+e.getBoundingClientRect().top-parent.innerHeight/2); undefined"},
             {"do": "bounds", "sel": "#approve"}, click('#approve'),
             {"do": "waitText", "sel": "#status", "re": "Sent|Could not"},
             # Do not scroll after Send: its confirmation must already be visible beside the buttons.
             {"do": "bounds", "sel": "#status"}, {"do": "bounds", "sel": "#approve"},
             {"do": "bounds", "sel": "#send-review"},
             {"do": "eval", "js": "JSON.stringify({preview:document.querySelector('#preview')?.getAttribute('src'),master:document.querySelector('#master')?.getAttribute('src'),qa:document.querySelector('#qa').textContent,"
              "aids:[...document.querySelectorAll('#qa-aids a')].map(a=>({href:a.getAttribute('href'),label:a.textContent,img:a.querySelector('img')?.getAttribute('src')}))})"}],
            viewport={"width": 1024, "height": 768})
        need(before["viewport"] == {"width": 1024, "height": 768}, f"review viewport: {before}")
        need(before["visible"] and before["hit"], f"Approve is clipped or covered before click: {before}")
        need(status["text"] == "Sent. Preview approved.", f"review confirmation: {status}")
        for label, bounds in (("confirmation", status), ("Approve", approve), ("Send notes", notes)):
            need(bounds["visible"] and bounds["hit"], f"review {label} is clipped or covered after click: {bounds}")
        row = {"left": min(approve["box"]["left"], notes["box"]["left"]),
               "right": max(approve["box"]["right"], notes["box"]["right"]),
               "top": min(approve["box"]["top"], notes["box"]["top"]),
               "bottom": max(approve["box"]["bottom"], notes["box"]["bottom"])}
        need(max(0, row["left"] - status["box"]["right"], status["box"]["left"] - row["right"],
                 row["top"] - status["box"]["bottom"], status["box"]["top"] - row["bottom"]) <= 16,
             f"review confirmation is not next to the buttons: {status}, {approve}, {notes}")
        need(r["preview"] == "/videos/reel-01/renders/" + latest.replace(" ", "%20"), f"review preview: {r}")
        need(r["master"] and "Loudness" in r["qa"] and "Ready to post" in r["qa"], f"review missing master/QA: {r}")
        expected = ["/videos/reel-01/" + path.replace(" ", "%20")
                    for path in [aids["phone"], *aids["strips"], aids["contact"]]]
        need([a["href"] for a in r["aids"]] == expected and r["aids"][0]["label"] == "Phone-size copy",
             f"review aid links missing: {r}")
        need(all(a["img"].endswith(a["href"]) for a in r["aids"][1:]), f"review aid thumbnails missing: {r}")
        need((d / "review.json").is_file(), "review Send missing")
        doc = read(d / "review.json")
        need(set(doc) == {"approve", "preview", "note", "sent_at"} and doc["approve"] is True
             and doc["preview"] == latest and doc["note"] == "Keep the ending", f"review Send: {doc}")
        need(dt.datetime.fromisoformat(doc["sent_at"].replace("Z", "+00:00")).tzinfo is not None,
             "review timestamp must be ISO with timezone")
    # The walk's scroll problem did not reproduce in headless Chrome; keep the positive check as a regression guard.
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
    # Positions inside the side panel (which scrolls on its own), so page-load settling above it doesn't count.
    side = "(document.querySelector('aside.side').getBoundingClientRect().top - document.querySelector('aside.side').scrollTop)"
    positions = ("JSON.stringify({style: document.querySelector('[data-skill=style]').getBoundingClientRect().top - " + side + ","
                 "actions: document.querySelector('#actions').getBoundingClientRect().top - " + side + "})")
    settled = "[...document.images].every(i => i.complete) && document.querySelector('#vid').readyState >= 1"
    def check():
        # Wait for drawSaved: note-list and queue growth shift the later pointer targets.
        for n in ("reel-notes.json", "hub-requests.json"):
            (d / n).unlink(missing_ok=True)
        notes_top, before, after = p.browse([
                  {"do": "waitFn", "js": settled},
                  {"do": "set", "sel": "#note", "value": "Keep the laugh"},
                  {"do": "eval", "js": "document.querySelector('#actions').getBoundingClientRect().top - " + side},
                  click('#notes-send'),
                  {"do": "waitText", "sel": "#status", "re": "Sent|Could not"},
                  {"do": "waitFn", "js": "Hub.pending===0"},
                  {"do": "eval", "js": positions},
                  click('[data-skill="captions"]'), click('[data-skill="captions"]'),
                  click('[data-skill="qa"]'),
                  {"do": "waitFn", "js": "Hub.pending===0"},
                  click('[data-skill="style"]'),
                  {"do": "waitFn", "js": "Hub.pending===0"},
                  {"do": "eval", "js": positions}])
        need(abs(before["actions"] - notes_top) <= 0.5,
             f"notes Send moved #actions: {notes_top} -> {before['actions']}")
        for target in ("style", "actions"):
            need(abs(after[target] - before[target]) <= 0.5,
                 f"skill Sends moved {target}: {before[target]} -> {after[target]}")
        need((d / "reel-notes.json").is_file(), "notes Send missing")
        need(read(d / "reel-notes.json")[-1]["text"] == "Keep the laugh", "wrong note")
        need((d / "hub-requests.json").is_file() and len(read(d / "hub-requests.json")) == 4, "four clicks did not append four requests")
        requests = read(d / "hub-requests.json")
        need(requests[-2]["skill"] == "qa" and requests[-2]["ask"].startswith("Run QA for reel-01"), "wrong QA request")
        need(requests[-1]["skill"] == "style", "wrong Save this style request")
    check()
    with p.mutant("hub.js", "const list = previous.concat(entry);", "const list = [entry];"):
        p.bites(check, "requests overwrite earlier Sends")
    with p.mutant("hub.css", ".queue{height:174px;", ".queue{"):
        p.bites(check, "queue without fixed height moves Save this style")


def case_rapid_sends(p):
    target = p.videos / "reel-01/hub-requests.json"
    skills = ["captions", "qa", "cover", "style", "qa", "captions", "style", "cover"]

    def check():
        target.unlink(missing_ok=True)
        p.browse([{"do": "eval", "js":
                   "for (const skill of " + json.dumps(skills) + ") { "
                   "document.querySelector('[data-skill=\"' + skill + '\"]').click(); }"},
                  {"do": "waitFn", "js": "Hub.pending===0"}])
        need(target.is_file(), "rapid requests missing")
        requests = read(target)
        need(len(requests) == 8, f"eight clicks saved {len(requests)} requests")
        need([r["skill"] for r in requests] == skills, f"rapid requests out of click order: {requests}")

    check()
    with p.mutant("hub.js", "const work = queue.catch(() => {}).then(fn);",
                  "const work = Promise.resolve().then(fn);"):
        p.bites(check, "rapid requests run without serialization")


def case_styles(p):
    writer = p.plugin / "skills/_shared/saved_style.py"
    home = Path(p.env["EDITOR_SE_HOME"])
    write(home / "styles/default.json", {"font": "Inter"})
    write(home / "styles/client-b.json", {"font": "Montserrat"})
    data = p.refresh()
    need({s["id"]: s["label"] for s in data["styles"]} == {"default": "Style 1", "client-b": "Client b"},
         f"saved styles missing from hub data: {data.get('styles')}")
    d = p.videos / "reel-01"

    def check():
        (d / "hub-requests.json").unlink(missing_ok=True)
        p.browse([click('[data-style-id="client-b"] [data-style-action="default"]'),
                  {"do": "set", "sel": '[data-style-id="client-b"] input', "value": "Talking head"},
                  click('[data-style-id="client-b"] button[type="submit"]'),
                  {"do": "waitFn", "js": "Hub.pending===0"}])
        need((d / "hub-requests.json").is_file(), "style requests missing")
        requests = read(d / "hub-requests.json")
        need(len(requests) == 2, f"two style clicks did not append two requests: {requests}")
        for request, action, label, ask in zip(requests, ("default", "rename"), ("Client b", "Talking head"),
                ("Make Client b my default", "Rename Client b to Talking head")):
            need(request["skill"] == "styles" and request["reel"] == "reel-01" and request["ask"] == ask,
                 f"wrong style request: {request}")
            need(request["choices"] == {"action": action, "id": "client-b", "label": label},
                 f"style choices differ: {request['choices']}")

    check()
    with p.mutant("hub.js", "choices:{action,id,label}", "choices:{action,label}"):
        p.bites(check, "style requests drop their stable id")
    # Act on the requests exactly as the hub reference instructs, then rebuild.
    check()
    for request in read(d / "hub-requests.json"):
        choices = request["choices"]
        if choices["action"] == "rename":
            p.py(writer, "rename", choices["id"], choices["label"])
        else:
            p.py(writer, "set-default", choices["id"])
    data = p.refresh()
    row = next(s for s in data["styles"] if s["id"] == "client-b")
    need({k: row[k] for k in ("id", "label", "default")} ==
         {"id": "client-b", "label": "Talking head", "default": True}, "style commands did not update hub data")
    rows = p.snapshot("[...document.querySelectorAll('#styles form')].map(f=>({id:f.dataset.styleId,"
                        "label:f.querySelector('p').textContent,makeDefault:!!f.querySelector('[data-style-action=default]')}))")
    need(next(r for r in rows if r["id"] == "client-b") ==
         {"id": "client-b", "label": "Talking head (default)", "makeDefault": False}, "renamed default not shown")
    need(next(r for r in rows if r["id"] == "default")["makeDefault"], "old default cannot be selected")
    need("Auto edit unlocks after 3 smooth reels (0 so far)" in p.snapshot("document.querySelector('#styles').textContent"),
         "locked style does not explain Auto edit")
    write(home / "styles/client-b.learn.json", {"schema": 1,
        "style_created": read(home / "styles/_index.json")["styles"]["client-b"]["created"], "reels": [
        {"reel": str(d), "preview": str(i), "at": "2026-11-07T12:00:00+00:00", "mode": "normal",
         "changes": [], "big": False, "why": ""} for i in range(3)],
        "auto": {"on": False, "declined_at": None}, "learned": []})
    need(next(s for s in p.refresh()["styles"] if s["id"] == "client-b")["auto"]["ready"],
         "ready style does not reach the hub")

    def check_auto(on=True):
        (d / "hub-requests.json").unlink(missing_ok=True)
        p.browse([click('[data-style-id="client-b"] [data-style-action="auto"]'),
                  {"do": "waitFn", "js": "Hub.pending===0"}])
        requests = read(d / "hub-requests.json")
        need(len(requests) == 1, "one Auto edit click must append one request")
        request = requests[0]
        need(request["skill"] == "styles" and request["ask"] ==
             f"Turn Auto edit {'on' if on else 'off'} for Talking head", f"wrong Auto edit request: {request}")
        need(request["choices"] == {"action": "auto", "id": "client-b", "label": "Talking head", "on": on},
             f"wrong Auto edit choices: {request}")

    check_auto()
    with p.mutant("hub.js", "choices:{action,id,label,on}", "choices:{action,id,label}"):
        p.bites(check_auto, "Auto edit request drops the requested state")
    check_auto()
    learner = p.plugin / "skills/_shared/style_learn.py"
    choices = read(d / "hub-requests.json")[0]["choices"]
    p.py(learner, "auto", choices["id"], "on" if choices["on"] else "off", "--workspace", p.ws)
    p.refresh()
    need(p.snapshot("document.querySelector('[data-style-id=client-b] [data-style-action=auto]').textContent") ==
         "Auto edit: On", "enabled Auto edit is not shown")
    check_auto(False)
    # Labels are client input. They must stay text, including inside the input's value attribute.
    label = '<img src=x onerror="alert(1)">'
    p.py(writer, "rename", "client-b", label)
    p.refresh()
    escaped = p.snapshot("({images:document.querySelectorAll('#styles img').length,"
                         "label:document.querySelector('[data-style-id=client-b] input').value})")
    need(escaped == {"images": 0, "label": label}, f"style label became markup: {escaped}")
    (home / "styles/_index.json").write_bytes(b"{")
    need(p.refresh()["styles"] == [], "unreadable style names crashed the hub or exposed stale styles")
    need(p.snapshot("document.querySelector('#styles').textContent") == "No saved styles yet.",
         "empty styles message missing")


def case_health(p):
    def check():
        r = p.snapshot("({health:document.querySelector('#health-list').textContent,gold:document.querySelector('#gold-data').textContent})")
        need("Video tools are ready" in r["health"] and "Motion needs setup" in r["health"], "STATUS details missing")
        need("123" in r["gold"] and "n =" in r["gold"] and "7" in r["gold"], "Goldmine export/n missing")
        need("Stop posting every day" in r["gold"] and "SC0DE1x" not in r["gold"], "breakout not named by its title")
        need("4.12%" in r["gold"] and "2.00%" in r["gold"] and "287×" in r["gold"] and "2.5×" in r["gold"]
             and "0.0411" not in r["gold"] and "287.479" not in r["gold"], "Goldmine numbers not rounded")
    check()
    with p.mutant("hub.js", "const gold = DATA.goldmine;", "const gold = null;"):
        p.bites(check, "fixture export ignored")
    (p.ws / "reel-build/goldmine-run.json").unlink()
    p.refresh()
    need("A run uses your SocialCrawl credits" in p.snapshot("document.querySelector('#gold-data').textContent"), "Goldmine empty state")

    # Same 15 status rows as hub_rows_test.py, copied from the S17W2 walk.
    status = [
        {"component": "machine", "level": "ok",
         "detail": "Windows 11 (10.0.26300) AMD64, no NVIDIA GPU, 31.7 GB RAM (4.9 GB free) [test masks: gpu,resolve]",
         "fix": None},
        {"component": "python", "level": "ok", "detail": "the editor's own Python 3.12.16 in its venv", "fix": None},
        {"component": "ffmpeg", "level": "ok", "detail": "ffmpeg 8.1.2 with zscale", "fix": None},
        {"component": "node", "level": "ok", "detail": "Node.js v22.23.4", "fix": None},
        {"component": "hyperframes", "level": "ok", "detail": "HyperFrames 0.8.184", "fix": None},
        {"component": "chrome", "level": "ok", "detail": "Chrome for rendering 152.0.7977.30", "fix": None},
        {"component": "cutout-model", "level": "ok", "detail": "u2net_human_seg: 1 file(s) match their sha256", "fix": None},
        {"component": "rvm", "level": "ok", "detail": "RVM cutout ready (torch + torchvision)", "fix": None},
        {"component": "transcriber", "level": "ok", "detail": "parakeet-cpu packages are installed and load", "fix": None},
        {"component": "model-parakeet", "level": "ok", "detail": "4 file(s) match their sha256", "fix": None},
        {"component": "align", "level": "ok", "detail": "align_words with wav2vec2: 7 file(s) match their sha256", "fix": None},
        {"component": "engine", "level": "ok", "detail": "parakeet-cpu (Windows without an NVIDIA GPU)", "fix": None},
        {"component": "resolve-installed", "level": "warn",
         "detail": "DaVinci Resolve isn't installed, so the Resolve hand-off stays off (optional)",
         "fix": "Nothing is needed for editing. For the Resolve hand-off, install DaVinci Resolve Studio 21.1 or newer from blackmagicdesign.com, then Claude re-runs the doctor."},
        {"component": "nle", "level": "ok", "detail": "none (the Resolve hand-off stays off)", "fix": None},
        {"component": "config", "level": "ok", "detail": "editor/editor.config.json is up to date", "fix": None},
    ]
    platform = read(p.ws / "editor/.platform.json")
    platform["status"] = status
    write(p.ws / "editor/.platform.json", platform)
    p.refresh()

    def check_optional():
        r = p.snapshot("({hidden:document.querySelector('#healthwarn').hidden,health:document.querySelector('#health-list').textContent})")
        need(r["hidden"] is True, "optional Resolve warning raised the health banner")
        need(all(text in r["health"] for text in ("Optional", "DaVinci Resolve", "This computer")), "plain Health labels missing")
        need(all(text not in r["health"] for text in ("sha256", "test mask", "⚠ Needs a look")), "technical or warning text in optional-only Health")
    check_optional()
    with p.mutant("hub.js", "h.matters !== false && h.level", "h.level"):
        p.bites(check_optional, "optional Resolve warning raises the health banner")

    status.append({"component": "ffmpeg", "level": "warn", "detail": "Video tools need a check", "fix": None})
    write(p.ws / "editor/.platform.json", platform)
    p.refresh()
    need(p.snapshot("document.querySelector('#healthwarn').hidden") is False, "mattering warning did not raise the health banner")


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
    for f in ("root", "raw", "work", "renders", "sound"):
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


def case_storyboard(p):
    """Storyboard choices survive the real hub Send and clear the real suggestion."""
    import canvas_boards_test as fixture
    canvas = p.plugin / "skills/reel-canvas-build/scripts"
    sys.path.insert(0, str(canvas))
    import beat_schema
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    p.py(canvas / "make_beat_map.py", "--reel-dir", d, "--plan", d / "work/plan.json")
    beat_map = read(d / "beat-map.state.json")
    write(d / "beat-map-selection.json", beat_map)

    def module(name):
        spec = importlib.util.spec_from_file_location(name, p.plugin / "skills/_shared/checks" / (name + ".py"))
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    checks, storyboard = module("check"), module("storyboard_check")

    def open_sketches():
        return [click('#tab-sketches'), {"do": "waitFn", "js": "!!document.querySelector('#panel iframe')"},
                {"do": "frame", "sel": "#panel iframe", "wait": "#board:not([hidden]) #storyboard"},
                click('#storyboard summary')]

    def control(beat, field):
        return f'#storyboard [data-beat="{beat}"] [data-field="{field}"]'

    def sent(actions):
        (d / "sketches-selection.json").unlink(missing_ok=True)
        p.browse(open_sketches() + actions + [click('#send'),
                 {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])
        doc = read(d / "sketches-selection.json")
        need(beat_schema.sketches_problems(doc, beat_map) == [], "storyboard Send failed schema")
        return doc

    def mismatch():
        fixture.reel_fixture(d)
        doc = sent([{"do": "set", "sel": control("b_001", "out"), "value": "hold"},
                    {"do": "set", "sel": control("b_002", "in"), "value": "slide"},
                    {"do": "waitText", "sel": "#storyboard", "re": "Tip: match this exit"}])
        need(doc.get("storyboard") == {"beats": {"b_001": {"out": "hold"}, "b_002": {"in": "slide"}}},
             "storyboard dropped from Send")
        rows = storyboard.run(checks.build_context(d))
        need(len(rows) == 1 and rows[0]["level"] == "warn", f"expected one storyboard suggestion: {rows}")

    mismatch()
    restored = p.browse(open_sketches() + [{"do": "eval", "js": "JSON.stringify(["
        "document.querySelector('#storyboard [data-beat=\"b_001\"] [data-field=out]').value,"
        "document.querySelector('#storyboard [data-beat=\"b_002\"] [data-field=in]').value])"}])[-1]
    need(restored == ["hold", "slide"], "fresh browser did not restore storyboard")
    sent([{"do": "set", "sel": control("b_002", "in"), "value": "hold"},
          {"do": "waitFn", "js": "!document.querySelector('#storyboard .storyboard-tip')"}])
    need(storyboard.run(checks.build_context(d)) == [], "matching choices did not clear suggestion")
    doc = sent([{"do": "set", "sel": control("b_001", "out"), "value": ""},
                {"do": "set", "sel": control("b_002", "in"), "value": ""}])
    need("storyboard" not in doc, "blank choices left a storyboard key")
    with p.mutant("../sketches/index.html", "body: JSON.stringify(doc)}",
                  "body: JSON.stringify(Object.fromEntries(Object.entries(doc).filter(([k]) => k !== 'storyboard')))}"):
        p.bites(mismatch, "Send drops storyboard")


def case_reminder_holds(p):
    """The real hub saves optional reminder controls and reasons for quiet stretches."""
    import canvas_boards_test as fixture
    canvas = p.plugin / "skills/reel-canvas-build/scripts"
    sys.path.insert(0, str(canvas))
    import beat_schema
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    p.py(canvas / "make_beat_map.py", "--reel-dir", d, "--plan", d / "work/plan.json")
    seeded = read(d / "beat-map.state.json")
    # Remove the fixture's CTA mark for the happy path; plant it again below.
    seeded["word_marks"] = []
    # Keep one long gap, 120..270, including every cut start and overlay boundary.
    for beat, (start, end) in zip(seeded["beats"], [(0, 30), (30, 60), (60, 90), (65, 85), (90, 270)]):
        beat.update(start_f=start, end_f=end)
    write(d / "beat-map.state.json", seeded)
    heard = beat_schema.load_words(d / beat_schema.DEFAULT_WORDS)

    def module(name):
        path = p.plugin / "skills/_shared/checks" / (name + ".py")
        spec = importlib.util.spec_from_file_location(name, path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    checks = module("check")
    cta, hold = module("cta_reminder_check"), module("hold_gap_check")
    expected = dict(at_s=6.3, hold_s=2, gain=0, keyword="NOTES")
    reason = "Give your viewer time to read."

    def open_map():
        return [click('#tab-beat-map'), {"do": "waitFn", "js": "!!document.querySelector('#panel iframe')"},
                {"do": "eval", "js": "document.querySelector('#panel iframe').scrollIntoView({block: 'end'}), 0"},
                {"do": "frame", "sel": "#panel iframe", "wait": "#board:not([hidden]) #reminder-holds"},
                click('#reminder-holds summary')]

    def set_value(sel, value):
        return {"do": "set", "sel": sel, "value": value}

    def sent(actions):
        (d / "beat-map-selection.json").unlink(missing_ok=True)
        p.browse(open_map() + actions + [click('#send'),
                 {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])
        need((d / "beat-map-selection.json").is_file(), "Beat Map Send missing")
        doc = read(d / "beat-map-selection.json")
        problems = beat_schema.beat_map_problems(doc, heard)
        need(problems == [], f"Send fails the beat map schema: {problems}")
        return doc

    def reminder_check():
        write(d / "beat-map.state.json", seeded)
        doc = sent([click('#reminder-enabled'), set_value('#reminder-keyword', 'NOTES'),
                    set_value('#reminder-at', '6.3'), set_value('#reminder-hold', '2'),
                    set_value('#reminder-volume', '0')])
        need(doc.get("cta_reminder") == expected, f"reminder Send differs: {doc.get('cta_reminder')}")
        need(cta.run(checks.build_context(d)) == [], "valid reminder failed its real check")
        rows = hold.run(checks.build_context(d))
        need(len(rows) == 1 and rows[0]["level"] == "warn" and rows[0]["at"] == 4,
             f"expected one unexplained gap: {rows}")

    reminder_check()
    baseline = (d / "beat-map-selection.json").read_bytes()

    def refused(actions, message):
        p.browse(open_map() + actions + [click('#send'),
                 {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='error' && "
                  f"document.querySelector('#status').textContent.includes({json.dumps(message)})"}])
        need((d / "beat-map-selection.json").read_bytes() == baseline, "refused Send changed the file")

    refused([set_value('#reminder-volume', '15')], "10%")
    # A scene category and a marked word must each independently prevent overlap.
    saved = read(d / "beat-map-selection.json")
    scene_doc = json.loads(json.dumps(saved))
    catalog = read(p.plugin / "scenes/cta-end-card/scene.json")
    scene_doc["beats"][-1]["scene"] = dict(id="cta-end-card",
        slots={name: slot["default"] for name, slot in catalog["slots"].items()}, params={})
    write(d / "scenes/catalog.json", [dict(catalog,
        slots=[dict(name=name, maxChars=slot["maxChars"]) for name, slot in catalog["slots"].items()],
        params=[dict(name=name, **param) for name, param in catalog["params"].items()])])
    write(d / "beat-map.state.json", scene_doc)
    refused([], "Move your reminder")
    word_doc = json.loads(json.dumps(saved))
    word_doc["word_marks"] = [dict(w=13, mark="cta")]
    write(d / "beat-map.state.json", word_doc)
    refused([], "Move your reminder")

    write(d / "beat-map.state.json", saved)
    doc = sent([set_value('#hold-reason-120', reason),
                {"do": "waitState", "board": "beat-map", "js": "s.holds?.[0]?.reason===" + json.dumps(reason)}])
    need(doc.get("holds") == [dict(at_f=120, reason=reason)], "gap reason missing from Send")
    need(hold.run(checks.build_context(d)) == [], "sent reason did not clear the real warning")
    restored = p.browse(open_map() + [{"do": "eval", "js": "JSON.stringify({enabled:"
        "document.querySelector('#reminder-enabled').checked,keyword:document.querySelector('#reminder-keyword').value,"
        "at:document.querySelector('#reminder-at').value,hold:document.querySelector('#reminder-hold').value,"
        "volume:document.querySelector('#reminder-volume').value,reason:document.querySelector('#hold-reason-120').value})"}])[-1]
    need(restored == dict(enabled=True, keyword="NOTES", at="6.3", hold="2", volume="0", reason=reason),
         f"fresh browser did not restore reminder and reason: {restored}")
    need("cta_reminder" not in sent([click('#reminder-enabled')]), "unticking kept the reminder key")

    # Shape checks remain light, but reject invalid types and overlong keywords.
    for bad in (None, dict(expected, at_s=True), dict(expected, keyword="X" * 17)):
        need(beat_schema.beat_map_problems(dict(doc, cta_reminder=bad), heard), "invalid reminder shape accepted")
    for bad in (None, [dict(at_f=True, reason=reason)], [dict(at_f=120, reason=" ")]):
        need(beat_schema.beat_map_problems(dict(doc, holds=bad), heard), "invalid holds shape accepted")
    with p.mutant("../beat-map/index.html", "body: JSON.stringify(doc)",
                  "body: JSON.stringify({...doc, cta_reminder: undefined})"):
        p.bites(reminder_check, "Beat Map drops cta_reminder from Send")


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


def case_strong_beats(p):
    """H-BEAT-2: up to 3 strong beats and honest empty states leave the Beat Map Send unchanged."""
    import canvas_boards_test as fixture
    canvas = p.plugin / "skills/reel-canvas-build/scripts"
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    p.py(canvas / "make_beat_map.py", "--reel-dir", d, "--plan", d / "work/plan.json")
    seeded = read(d / "beat-map.state.json")
    placement = d / "sound/placement.json"
    times = [1.25, 4.5, 7.75]
    total = fixture.TOTAL_F / fixture.FPS
    label = "strong beat: good spot for a punch-in or transition"
    quiet = "No steady beat in the music, so no strong-beat suggestions."
    no_hits = "No standout kick in the part of the song this reel plays."
    p.refresh()

    def open_map():
        return [click('#tab-beat-map'), {"do": "waitFn", "js": "!!document.querySelector('#panel iframe')"},
                {"do": "eval", "js": "document.querySelector('#panel iframe').scrollIntoView({block: 'end'}), 0"},
                {"do": "frame", "sel": "#panel iframe", "wait": "#board:not([hidden]) #edit-style"}]

    def show_and_send(value, marked=False, note=None):
        write(d / "beat-map.state.json", seeded)
        (d / "beat-map-selection.json").unlink(missing_ok=True)
        if value is None:
            placement.unlink(missing_ok=True)
        else:
            write(placement, value)
        snapshot = {"do": "eval", "js": "JSON.stringify((() => {"
            "const note = document.querySelector('#strong-beat-note');"
            "return {marks:[...document.querySelectorAll('#timeline .strong-beat-mark')].map(e => {"
            "const r = e.getBoundingClientRect(), button = e.closest('.tl-beat'), box = button.getBoundingClientRect();"
            "return {time:Number(e.dataset.timeS),label:e.title,beat:button.dataset.beat,"
            "aria:e.getAttribute('aria-label'),fraction:parseFloat(e.style.left)/100,"
            "pixelFraction:(r.left + r.width/2 - box.left - button.clientLeft)/button.clientWidth,"
            "width:button.clientWidth,visible:r.width > 0 && r.height > 0};}),"
            "quiet:!note.hidden,note:note.textContent,suggestions:!document.querySelector('#strong-beat-suggestions').hidden,"
            "list:[...document.querySelectorAll('#strong-beat-times li')].map(e => e.textContent)};})())"}
        actions = [snapshot]
        if marked:
            # A suggestion click must not edit a beat, even when followed by Send.
            actions.append({"do": "eval", "js": "document.querySelector('#timeline .strong-beat-mark')?.click(), 0"})
        reads = p.browse(open_map() + actions + [click('#send'),
            {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])
        view = reads[1]  # open_map records its scroll expression before the snapshot
        marks = view["marks"]
        need(len(marks) == (3 if marked else 0), f"strong-beat mark count differs: {marks}")
        if marked:
            need([m["time"] for m in marks] == times, f"strong-beat times differ: {marks}")
            need(all(m["label"] == label and label in m["aria"] and m["visible"] for m in marks),
                 f"strong-beat labels or visibility differ: {marks}")
            for m, at in zip(marks, times):
                beat = next(b for b in seeded["beats"] if b["layout"] != "overlay"
                            and b["start_f"] <= at * fixture.FPS < b["end_f"])
                fraction = (at * fixture.FPS - beat["start_f"]) / (beat["end_f"] - beat["start_f"])
                need(m["beat"] == beat["id"] and abs(m["fraction"] - fraction) < 1e-6 and
                     abs(m["pixelFraction"] - fraction) * m["width"] <= 1,
                     f"strong-beat timeline position differs: {m}")
            need(not view["quiet"] and view["suggestions"]
                 and view["list"] == [f"{t:.2f} s: {label}" for t in times],
                 f"strong-beat time list differs: {view}")
        else:
            need(view["quiet"] == (note is not None) and (note is None or view["note"] == note)
                 and not view["list"] and not view["suggestions"], f"wrong strong-beat empty state: {view}")
        sent = read(d / "beat-map-selection.json")
        need(read(d / "beat-map.state.json") == sent, "saved state and Send differ")
        # Send timestamps vary between fresh browsers; every other key and value must be identical.
        need("sent_at" in sent, "Send timestamp missing")
        return {k: v for k, v in sent.items() if k != "sent_at"}

    baseline = show_and_send({})
    need(show_and_send(None) == baseline, "missing placement changed the Send")
    need(show_and_send({"bed": None}) == baseline, "absent bed changed the Send")
    need(show_and_send({"bed": {"beat_sync": True}}, note=quiet) == baseline, "refused grid changed the Send")
    need(show_and_send({"bed": {"beat_sync": False}}) == baseline, "beat-sync off showed a note or changed the Send")
    need(show_and_send({"bed": {"beat": {"big_hits_s": []}}}, note=no_hits) == baseline,
         "empty strong-beat list changed the Send")

    def positive():
        sent = show_and_send({"bed": {"beat": {"big_hits_s": times}}}, True)
        need(set(sent) == set(baseline), "strong-beat suggestions added Send keys")
        need(sent == baseline, "strong-beat suggestions edited the Beat Map Send")

    positive()
    with p.mutant("../beat-map/index.html", "strongBeatTimes = Array.isArray(times) ? times : [];",
                  "strongBeatTimes = [];"):
        p.bites(positive, "Beat Map ignores strong-beat placement data")


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
                {"do": "frame", "sel": "#panel iframe", "wait": "#board:not([hidden]) #broll-0"},
                click('#more > summary')]

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
    need(labels == ["None", "My own clip", "Too short", "Garden (AI)"],
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
        "document.querySelector('#broll-0').textContent.includes('No clips yet. Ask Claude to add your own clips.') && "
        "!document.querySelector('#broll-0').textContent.includes('videos/') && "
        "!document.querySelector('#broll-0').textContent.includes('broll/')"}])
    need(sent([set_value('#note-0', 'Keep my saved clip')])["beats"][0]["broll"] == expected,
         "missing catalog changed saved B-roll")


def case_walk_polish(p):
    d = p.videos / "reel-01"
    write(d / "tweak-selection.json", {})
    os.utime(d / "tweak-selection.json", (100, 100))
    # A sent Beat Map with no scene on any beat: there is no motion step, so the sound pass is next.
    write(d / "beat-map.state.json", {"sent_at": "now", "beats": [{"id": "b_001", "scene": None}]})
    library = p.editor / "sound"
    write(library / "library-index.json", {"files": {"tick.wav": {"sha256": "fixture"}}})
    (library / "tick.wav").write_bytes(b"sound")
    p.refresh()
    rows = p.browse([
        {"do": "eval", "js": "JSON.stringify({head:document.querySelector('#move h2').textContent,"
         "hint:document.querySelector('#move .what').textContent,step:document.querySelectorAll('#steps small')[5].textContent})"},
        {"do": "eval", "js": "current().sound_pass_ran=true;current().sound_voice_only=true;drawHead();"
         "JSON.stringify(document.querySelectorAll('#steps small')[5].textContent)"},
        {"do": "eval", "js": "current().sound_pass_ran=false;current().sound_pack_installed=false;drawHead();"
         "JSON.stringify(document.querySelectorAll('#steps small')[5].textContent)"}])
    need("No sound pass yet" in rows[0]["hint"] and "starter pack" in rows[0]["hint"] and
         "voice only" not in rows[0]["hint"] and rows[0]["hint"] == rows[0]["step"], f"next sound pass: {rows[0]}")
    need(all("voice only" in text for text in rows[1:]), f"voice-only alternatives: {rows[1:]}")
    (d / "sound/final.mp4").write_bytes(b"mix")
    p.refresh()
    post = p.browse([{"do": "eval", "js": "JSON.stringify({tile:document.querySelector('#wall [data-reel=\"reel-01\"] .stg').textContent,"
        "head:document.querySelector('#move h2').textContent,button:document.querySelector('#move [data-open]')?.textContent||'',"
        "progress:document.querySelector('#rhead .pct').textContent})"}], viewport={"width": 1024, "height": 768})[-1]
    need(post["tile"] == "Ready to post" and post["progress"] == "Ready to post", f"post progress: {post}")
    need("Post" in post["head"] and not post["button"], f"post next action: {post}")


def case_full_view(p):
    """H14: keep one live board in Full view; the lane runs the browser proof."""
    import canvas_boards_test as fixture
    d = p.videos / "reel-01"
    fixture.reel_fixture(d)
    p.py(p.plugin / "skills/reel-canvas-build/scripts/make_beat_map.py",
         "--reel-dir", d, "--plan", d / "work/plan.json")
    for name in ("tweak-selection.json", "work/edl.json"):
        (d / name).unlink(missing_ok=True)
    # Make one real manifest tab unavailable in this owned fixture, even as more boards ship.
    manifest = read(p.doctor / "boards.json")
    manifest["boards"]["trials"]["template"] = "skills/reel-trials/boards/h14-unbuilt"
    write(p.doctor / "boards.json", manifest)
    (p.editor / "trials/index.html").unlink(missing_ok=True)
    data = p.refresh()
    unbuilt = next((b["id"] for b in data["boards"] if not b["built"]), None)
    need(unbuilt, "Full view proof needs an unavailable board tab")

    def check(width=1024, core=False, layout="guided", controls="simple"):
        full_view_static(p)
        config = read(p.ws / "editor/editor.config.json")
        config["controls"] = controls
        write(p.ws / "editor/editor.config.json", config)
        p.py(p.doctor / "hub_rows.py", "--root", p.ws)
        p.browse([
            {"do": "eval", "js": f"applyLayout({json.dumps(layout)}); localStorage.setItem('editor-controls',{json.dumps(controls)}); BoardClient.controls.apply(), 0"},
            {"do": "fullView", "coreOnly": core, "unbuilt": unbuilt, "layout": layout, "controls": controls,
             "python": sys.executable, "rows": str(p.doctor / "hub_rows.py"),
             "root": str(p.ws), "reel": str(d)}],
            viewport={"width": width, "height": 768 if width == 1024 else 800})

    check()
    check(470, layout="full", controls="advanced")
    check(core=True, layout="full", controls="advanced")
    check(470, core=True)
    with p.mutant("hub.js", 'await enterFull();', 'await enterFull(false);'):
        p.bites(check, "direct Full view skips the same-document Back entry")
    for before, after, label in [
        ('document.body.dataset.boardview = "full";',
         '$("panel").innerHTML = $("panel").innerHTML; document.body.dataset.boardview = "full";',
         "entering Full view recreates the iframe"),
        ('frame.contentDocument?.addEventListener("keydown", boardEscape);',
         'frame.contentDocument?.removeEventListener("keydown", boardEscape);',
         "Escape inside the board is ignored"),
        ('region.inert = false;', 'region.inert = true;', "exit leaves hub regions inert"),
    ]:
        with p.mutant("hub.js", before, after):
            p.bites(lambda: check(core=True), label)
    with p.mutant("index.html", '<button type="button" class="ghostbtn" id="fullview"',
                  '<a target="_blank" href="/editor/hub/">Open board</a><button type="button" class="ghostbtn" id="fullview"'):
        p.bites(lambda: full_view_static(p), "own-tab link returns")


def full_view_static(p):
    for name in ("index.html", "hub.js", "common.js", "review.html", "review.js"):
        text = (p.hub / name).read_text(encoding="utf-8")
        need(not re.search(r'target\s*=\s*[\"\x27]?_blank|window\s*\.\s*open\b', text, re.I),
             f"hub opens another page: {name}")
    for name in ("logic.ts", "register.ts"):
        text = (p.plugin / "hooks/mod" / name).read_text(encoding="utf-8")
        need(not re.search(r'window\s*\.\s*open\b|openExternal|target\s*=\s*[\"\x27]?_blank|editor/(?!editor\.config\.json\b|\.platform\.json\b)', text, re.I),
             f"Cockpit opens a board address: {name}")


def wording_checks(p):
    """Reject client-opening instructions that escape the one-window hub."""
    import ast
    from types import SimpleNamespace
    from urllib.parse import quote

    skills = p.plugin / "skills"
    texts = {f.relative_to(skills).as_posix(): f.read_text(encoding="utf-8")
             for f in skills.rglob("*.md")}
    ids = set(read(p.doctor / "boards.json")["boards"]) - {"hub"}
    own_page = re.compile(r'editor/(?:' + '|'.join(map(re.escape, sorted(ids))) + r')/\?reel')
    bare_video = re.compile(r'videos/[^\s`]+')
    opening = re.compile(r'preview_start|in the Browser pane', re.I)
    exceptions = (
        ("editor-doctor/references/board-server.md", "A board's own page (`{url}editor/<board>/?reel=<reel>`) still loads; it is for tests and direct links only."),
        ("reel-sound-pass/references/sound-board.md", "The client opens it inside the hub (board-server.md step 3); this address is the board's own page."),
    )
    sentence = "The hub is the client's one window: never open a second tab or a bare board or video address for them."

    def check(docs):
        for name, text in docs.items():
            for n, line in enumerate(text.splitlines(), 1):
                if any(name == file and substring in line for file, substring in exceptions):
                    continue
                need(not own_page.search(line) and not (bare_video.search(line) and opening.search(line)),
                     f"bare board/video opening: {name}:{n}: {line}")
        need(sum(text.count(sentence) for text in docs.values()) == 1, "one-window sentence must appear exactly once")

    check(texts)
    mutant = dict(texts)
    mutant["reel-sound-pass/SKILL.md"] += "\nOpen `/editor/sound-board/?reel=<reel>` in the Browser pane.\n"
    p.bites(lambda: check(mutant), "bare Sound Board instruction")
    p.bites(lambda: check({name: text.replace(sentence, "") for name, text in texts.items()}),
            "missing one-window sentence")

    script = skills / "reel-sound-pass/scripts/new_board.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    lines = [node.args[0] for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "print" and node.args
             and any(isinstance(part, ast.Constant) and isinstance(part.value, str)
                     and part.value.startswith("Open it ") for part in ast.walk(node.args[0]))]
    need(len(lines) == 1, "new_board opening print missing or duplicated")
    printed = eval(compile(ast.Expression(lines[0]), str(script), "eval"),
                   {"a": SimpleNamespace(reel="reel one & two"), "quote": quote})
    need(printed == "Open it inside the editor hub: /editor/hub/?reel=reel%20one%20%26%20two&board=sound-board&view=full",
         f"new_board printed opening: {printed}")
    check(dict(texts, **{"reel-sound-pass/scripts/new_board.py": printed}))
    print("PASS data: hub-only wording, one-window sentence, new_board encoded opening + mutants", flush=True)


def data_checks(p):
    """Useful proof in a sandbox that cannot take the shared browser lock; never substitutes for the UI cases."""
    full_view_static(p)
    print("PASS data: hub and Cockpit never open another page", flush=True)
    wording_checks(p)
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
        for name in ("root", "raw", "work", "renders", "sound"):
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
    # Preserve the Ear pass assertion: this Send was successfully applied, even with no marks.
    write(d / "work/edl.json", [])
    parity("Beat map")
    write(d / "beat-map.state.json", {"sent_at": 0})  # != null, not a truthiness test
    # Preserve the Motion assertion: this fixture has an open direction to lock.
    write(d / "sketches.state.json", {})
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
