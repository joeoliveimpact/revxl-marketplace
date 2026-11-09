#!/usr/bin/env python3
"""The cut review page, work/cut-review.html. render.py writes it after every render.

It shows what was kept (green) and cut (red) along the raw recording, lists the 20
largest cuts, and plays the raw and the cut side by side. Clicking a cut, on the bar
or in the list, moves both players to half a second before it. The page opens
straight from disk: no server, nothing to install.
"""
import html, json, os, subprocess, sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import runtime as rt  # noqa: E402

LEAD = 0.5   # seconds of run-up before a cut
TOP = 20
SETUP = "The editor's setup isn't finished: its video tools are missing. Run the editor setup (editor-doctor), then try again."
FFPROBE = None


def die(m):
    print("ERROR: %s" % m, file=sys.stderr)
    raise SystemExit(2)


def find_tools():
    """ffmpeg/ffprobe come from the editor's install (_shared/runtime.py), never PATH. Looked up on first use."""
    global FFPROBE
    if FFPROBE:
        return
    try:
        ffmpeg, ffprobe = rt.tool("ffmpeg"), rt.tool("ffprobe")
    except (KeyError, OSError, ValueError):
        die(SETUP)
    if not (Path(ffmpeg).exists() and Path(ffprobe).exists()):
        die(SETUP)
    FFPROBE = ffprobe


def duration(path):
    find_tools()
    p = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def cuts(segs, total, speed=1.0):
    """Raw ranges that were not kept. `at` is where each one falls in the cut."""
    out, prev, kept = [], 0.0, 0.0
    for a, b in sorted(segs):
        if a - prev > 1e-3:
            out.append({"start": round(prev, 3), "end": round(a, 3), "len": round(a - prev, 3),
                        "at": round(kept / speed, 3)})
        kept += b - a
        prev = max(prev, b)
    if total - prev > 1e-3:
        out.append({"start": round(prev, 3), "end": round(total, 3), "len": round(total - prev, 3),
                    "at": round(kept / speed, 3)})
    return out


def src(path, page_dir):
    """A link the page can follow from disk: relative when it can be, else a file URL."""
    p = Path(path).resolve()
    try:
        return quote(os.path.relpath(p, page_dir).replace(os.sep, "/"))
    except ValueError:            # another drive on Windows
        return p.as_uri()


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Cut review: %(name)s</title>
<style>
body{margin:0;padding:20px 24px;background:#111418;color:#e8eaed;font:14px/1.45 system-ui,sans-serif}
h1{font-size:18px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 8px}
.sum{color:#9aa0a6;margin:0 0 14px}
#bar{position:relative;height:40px;background:#2a2f36;border-radius:6px;overflow:hidden}
#bar div{position:absolute;top:0;height:100%%}
#bar .keep{background:#2ea043;opacity:.6}#bar .cut{background:#e5534b;cursor:pointer;min-width:2px}
.key{color:#9aa0a6;font-size:12px;margin:6px 0 16px}
.players{display:flex;gap:16px;flex-wrap:wrap}
figure{margin:0;flex:1 1 280px;max-width:420px}figcaption{color:#9aa0a6;margin-bottom:6px}
video{width:100%%;max-height:60vh;background:#000;border-radius:6px}
table{border-collapse:collapse;min-width:420px}
th,td{padding:5px 12px;text-align:left;border-bottom:1px solid #2a2f36}th{color:#9aa0a6;font-weight:600}
tbody tr{cursor:pointer}tbody tr:hover{background:#1c2128}
</style></head><body>
<h1>Cut review: %(name)s</h1>
<p class="sum" id="sum"></p>
<div id="bar"></div>
<p class="key">Green is kept, red is cut. Click a red mark or a row: both players jump to half a second before that cut.</p>
<div class="players">
<figure><figcaption>Raw recording</figcaption><video id="raw" src="%(raw)s" controls preload="metadata"></video></figure>
<figure><figcaption>The cut</figcaption><video id="cut" src="%(cut)s" controls preload="metadata"></video></figure>
</div>
<h2>The largest cuts (up to %(top)d)</h2>
<table><thead><tr><th>#</th><th>In the raw</th><th>In the cut</th><th>Length</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const D = %(data)s;
const t = (s) => { const m = Math.floor(s / 60); return m + ":" + (s - m * 60).toFixed(2).padStart(5, "0"); };
const pct = (s) => (100 * s / D.total) + "%%";
function seek(c) {
  document.getElementById("raw").currentTime = Math.max(0, c.start - D.lead);
  document.getElementById("cut").currentTime = Math.max(0, c.at - D.lead);
}
const bar = document.getElementById("bar");
for (const k of D.keep) {
  const e = document.createElement("div"); e.className = "keep";
  e.style.left = pct(k[0]); e.style.width = pct(k[1] - k[0]); bar.appendChild(e);
}
for (const c of D.cuts) {
  const e = document.createElement("div"); e.className = "cut";
  e.style.left = pct(c.start); e.style.width = pct(c.len);
  e.title = t(c.start) + " to " + t(c.end) + " (" + c.len.toFixed(2) + " s)";
  e.onclick = () => seek(c); bar.appendChild(e);
}
const big = [...D.cuts].sort((a, b) => b.len - a.len).slice(0, D.top);
const rows = document.getElementById("rows");
big.forEach((c, i) => {
  const r = rows.insertRow();
  r.dataset.start = c.start; r.dataset.at = c.at;
  [i + 1, t(c.start) + " to " + t(c.end), t(c.at), c.len.toFixed(2) + " s"].forEach((v) => { r.insertCell().textContent = v; });
  r.onclick = () => seek(c);
});
const removed = D.cuts.reduce((s, c) => s + c.len, 0);
document.getElementById("sum").textContent = D.cuts.length + " cuts, " + removed.toFixed(1) + " s removed from "
  + t(D.total) + (D.speed !== 1 ? ", played at " + D.speed + "x" : "") + ".";
</script>
</body></html>
"""


def write(work, raw, edited, segs, speed=1.0):
    work = Path(work)
    page = work / "cut-review.html"
    total = duration(raw) or max(b for _, b in segs)
    data = {"total": round(total, 3), "speed": speed, "lead": LEAD, "top": TOP,
            "keep": [[round(a, 3), round(b, 3)] for a, b in sorted(segs)],
            "cuts": cuts(segs, total, speed)}
    page.write_text(PAGE % {
        "name": html.escape(Path(raw).name), "top": TOP,
        "raw": html.escape(src(raw, work.resolve())), "cut": html.escape(src(edited, work.resolve())),
        "data": json.dumps(data).replace("</", "<\\/")}, encoding="utf-8")
    return page

