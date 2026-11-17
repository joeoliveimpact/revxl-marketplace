"""INT13-D: automatic hub rows, stable requested reels, and plain missing-board messages."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import quote

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
SCRIPTS = PLUGIN / "skills/editor-doctor/scripts"
sys.path.insert(0, str(SCRIPTS))
import board_server as server
import board_sync
import hub_rows

HUB = PLUGIN / "skills/editor-doctor/boards/hub"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data) + "\n").encode("utf-8"))


class HubReelTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="int13-hub-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        write(self.root / "editor/editor.config.json", {"paths": {"editor": "desk", "videos": "media/reels"}})
        self.editor, self.videos = board_sync.workspace_paths(self.root)
        spec = importlib.util.spec_from_file_location("prepare_reel", PLUGIN / "skills/reel-first-cuts/scripts/prepare_reel.py")
        self.intake = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.intake)
        # Personal libraries are unrelated to a local reel's identity and must stay untouched.
        for name, value in (("goldmine", None), ("style_rows", [])):
            mock = patch.object(hub_rows, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        self.intake.prepare(self.root, "reel-A")
        self.assertEqual(hub_rows.main(["--root", str(self.root)]), 0)

    def start(self):
        httpd = server.Server(("127.0.0.1", 0), self.root, board_sync.load_manifest(), self.editor, self.videos)
        self.addCleanup(httpd.server_close)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(httpd.shutdown)
        return httpd

    def rows(self, httpd, query="", method="GET"):
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
        try:
            conn.request(method, "/editor/hub/hub-data.json" + query)
            response = conn.getresponse()
            body = response.read()
            self.assertEqual(response.status, 200, body)
            return json.loads(body) if method == "GET" else body
        finally:
            conn.close()

    def test_server_rows(self):
        self.intake.prepare(self.root, "reel-B")
        # A render on disk must not make the server run video tools or generate frames.
        picture = self.videos / "reel-B/work/renders/master-100x.mp4"
        picture.parent.mkdir(parents=True)
        picture.write_bytes(b"fixture")
        with patch.object(hub_rows, "run", side_effect=AssertionError("server ran a video tool")):
            httpd = self.start()
            self.assertEqual([r["id"] for r in self.rows(httpd)["reels"]], ["reel-A", "reel-B"])
            self.assertEqual([r["id"] for r in json.loads((self.editor / "hub/hub-data.json").read_bytes())["reels"]],
                             ["reel-A", "reel-B"])
            self.intake.prepare(self.root, "reel-C")  # prepared after this server started
            self.assertEqual([r["id"] for r in self.rows(httpd, "?reel=reel-C")["reels"]],
                             ["reel-A", "reel-B", "reel-C"])
            self.intake.prepare(self.root, "reel-D")
            self.assertEqual(self.rows(httpd, "?reel=reel-D", method="HEAD"), b"")
            self.assertIn("reel-D", [r["id"] for r in self.rows(httpd)["reels"]])

    def test_keep_frames(self):
        picture = self.videos / "reel-A/work/renders/master-100x.mp4"
        picture.parent.mkdir(parents=True)
        picture.write_bytes(b"fixture")
        os.utime(picture, (100, 100))
        strip = self.editor / "hub/frames/reel-A"
        strip.mkdir(parents=True)
        frames = ["/editor/hub/frames/reel-A/%02d.jpg" % i for i in range(12)]
        for i in range(12):
            (strip / ("%02d.jpg" % i)).write_bytes(b"existing frame")
        write(strip / ".source.json", {"source": str(picture), "mtime_ns": picture.stat().st_mtime_ns})
        data_path = self.editor / "hub/hub-data.json"
        data = json.loads(data_path.read_bytes())
        data["reels"][0]["frames"] = frames
        write(data_path, data)
        os.utime(picture, (200, 200))  # a newer render must not erase the strip
        with patch.object(hub_rows, "run", side_effect=AssertionError("server ran a video tool")):
            httpd = self.start()
            self.assertEqual(self.rows(httpd)["reels"][0]["frames"], frames)
            self.intake.prepare(self.root, "reel-B")
            self.assertEqual(self.rows(httpd, "?reel=reel-B")["reels"][0]["frames"], frames)
        self.assertEqual(json.loads(data_path.read_bytes())["reels"][0]["frames"], frames)
        # An explicit rendering refresh can still replace the previous frame list.
        with patch.object(hub_rows, "filmstrip", return_value=["/editor/hub/frames/reel-A/new.jpg"]):
            refreshed = hub_rows.refresh(self.root)
        self.assertEqual(refreshed["reels"][0]["frames"], ["/editor/hub/frames/reel-A/new.jpg"])

    def hub_state(self, data, reel):
        # Execute the actual load/selection/address code in Node; unrelated painting is stubbed.
        harness = r'''
const vm = require('node:vm');
const elements = new Map(), requests = [];
const element = id => {
  if (!elements.has(id)) elements.set(id, {hidden:true, textContent:'', value:'', dataset:{},
    setAttribute(){}, querySelector(){return null}, querySelectorAll(){return []}});
  return elements.get(id);
};
const context = {URL, URLSearchParams, console, location:new URL('http://localhost/editor/hub/?reel='+encodeURIComponent(REEL)+'&board=cut-board&view=full'),
  document:{getElementById:element, querySelectorAll:()=>[], addEventListener(){}, body:{dataset:{}, style:{}}},
  window:{}, matchMedia:()=>({matches:false}), addEventListener(){}, setInterval(){},
  HubIO:{json:async url=>{requests.push(url); return url.includes('hub-data.json') ? DATA : {}}, base:()=>'', status(){}},
  history:{state:null, replaceState(state,unused,url){context.location=new URL(url)}}};
vm.createContext(context);
vm.runInContext(SCRIPT + '\ndrawPages=drawWall=drawHead=drawTabs=drawAdjust=()=>{}; drawSaved=async()=>{};', context);
setImmediate(()=>console.log(vm.runInContext('JSON.stringify({reel:CUR, url:location.href, error:$("error").textContent, errorHidden:$("error").hidden, workHidden:$("work").hidden, ready:Hub.ready})', context)));
'''.replace("REEL", json.dumps(reel)).replace("DATA", json.dumps(data)).replace("SCRIPT", json.dumps((HUB / "hub.js").read_text(encoding="utf-8")))
        result = subprocess.run([hub_rows.rt.tool("node"), "-"], input=harness, capture_output=True,
                                text=True, encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_unknown_reel(self):
        httpd = self.start()
        for missing in ("duet-killed-grokbot", 'missing "reel"'):
            with self.subTest(reel=missing):
                data = self.rows(httpd, "?reel=" + quote(missing))
                state = self.hub_state(data, missing)
                self.assertEqual(state["reel"], missing, state)
                self.assertIn("reel=" + quote(missing, safe=""), state["url"])
                self.assertEqual(state["error"], 'I can\'t find the reel "' + missing + '" yet. Ask Claude to set it up.')
                self.assertFalse(state["errorHidden"])
                self.assertTrue(state["workHidden"])
                self.assertTrue(state["ready"])
        # An empty workspace must keep an explicit reel too.
        data["reels"] = []
        self.assertEqual(self.hub_state(data, "missing")["reel"], "missing")

    def test_no_raw_404(self):
        source = (HUB / "hub.js").read_text(encoding="utf-8")
        # The request must reach the server with its reel, including on polling/reload.
        self.assertTrue(re.search(r'HubIO\.json\([^;\n]*[?&]reel=', source), "hub data request omits the reel")
        for rel in ("reel-first-cuts/boards/cut-board/index.html", "reel-first-cuts/boards/tweak-board/index.html",
                    "reel-sound-pass/boards/sound-board/index.html", "reel-grade/boards/grade-board/index.html"):
            board = (PLUGIN / "skills" / rel).read_text(encoding="utf-8")
            # Inspect the exception thrown on a failed fetch, not legitimate data URLs.
            fetch = re.search(r'fetch\([^\n]*config\.json', board)
            self.assertIsNotNone(fetch, rel)
            errors = re.findall(r'if\s*\(!r\.ok\)\s*\{?\s*(?:var e = )?(?:throw )?new Error\(([^;\n]+)',
                                board[fetch.start():fetch.end() + 350])
            self.assertTrue(errors, rel)
            for message in errors:
                self.assertNotRegex(message, r'HTTP|\.json|r\.status', rel)
        for path in HUB.glob("*.js"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r'new Error\([^\n]*(?:HTTP|\.json)')
        # The actual selection/address behavior must guard the existing replaceState call.
        state = self.hub_state({"reels":[{"id":"reel-A", "activity":1}], "boards":[], "stages":[]}, "missing")
        self.assertEqual(state["reel"], "missing", state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
