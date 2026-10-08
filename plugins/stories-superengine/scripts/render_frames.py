#!/usr/bin/env python3
"""Render a story set (story.json) to 1080x1920 PNG frames plus a contact sheet.

Usage:
    python render_frames.py <story_dir>            # renders every frame in <story_dir>/story.json
    python render_frames.py <story_dir> --only 3   # one frame
    python render_frames.py --selftest             # proves the FIT and FONT gates catch planted defects

story.json (photos are paths inside <story_dir>):
    {"style": "strong",
     "frames": [
       {"bg": "photo.png" | "#000000" | "cm-3", "position": "top" | "center" | "bottom", "focus": "center 30%",
        "lines": [{"text": "line one\\nline two", "color": "white", "background": "solid"}]}]}

Gates (any failure = that frame is NOT written, exit 1):
  LOAD  the page loaded story.json and the frame exists
  FONT  every story-text style used on the frame has its font loaded (FontFace.status, not fonts.check())
  FIT   every text bubble sits inside the safe area: 65px sides, 270px top bar, 384px reply bar
Writes frame-N.png and _contact-sheet.png into <story_dir>.
"""
import json
import pathlib
import shutil
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _serve import FONT_JS, serve  # noqa: E402

SAFE = {"left": 65, "right": 1080 - 65, "top": 270, "bottom": 1920 - 384}

FIT_JS = """() => {
  const c = document.getElementById('canvas').getBoundingClientRect();
  const bad = [];
  // Measure every element inside each line's bubble, not just the bubble: text can spill past its box.
  document.querySelectorAll('#stack > *').forEach((el, i) => {
    const box = {left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity};
    [el, ...el.querySelectorAll('*')].forEach(n => {
      const r = n.getBoundingClientRect();
      if (!r.width || !r.height) return;
      box.left = Math.min(box.left, r.left - c.left); box.right = Math.max(box.right, r.right - c.left);
      box.top = Math.min(box.top, r.top - c.top); box.bottom = Math.max(box.bottom, r.bottom - c.top);
    });
    const range = document.createRange(); range.selectNodeContents(el);
    for (const r of range.getClientRects()) {
      box.left = Math.min(box.left, r.left - c.left); box.right = Math.max(box.right, r.right - c.left);
    }
    bad.push([i + 1, box]);
  });
  return bad;
}"""


def check_fit(boxes, warn=print):
    """Hard fail: text off the canvas sides, or under the top bar / reply bar (Instagram covers those).
    Warning only: text inside the 65px side margin (looks cramped, nothing gets cut)."""
    out = []
    for n, b in boxes:
        over = []
        if b["left"] < 0: over.append(f"left edge at {b['left']:.0f}px, off the screen")
        if b["right"] > 1080: over.append(f"right edge at {b['right']:.0f}px, off the screen")
        if b["top"] < SAFE["top"] - 1: over.append(f"top at {b['top']:.0f}px, under the top bar")
        if b["bottom"] > SAFE["bottom"] + 1: over.append(f"bottom at {b['bottom']:.0f}px, under the reply bar")
        if over:
            out.append(f"FIT   line {n}: {', '.join(over)}. Break the line shorter or move it.")
        elif b["left"] < SAFE["left"] - 1 or b["right"] > SAFE["right"] + 1:
            warn(f"  note: line {n} runs into the side margin ({b['left']:.0f}-{b['right']:.0f}px). Fine to post; a shorter break looks roomier.")
    return out


def render(story_dir, only=None, strip_fonts=False):
    story_dir = pathlib.Path(story_dir).resolve()
    story = json.loads((story_dir / "story.json").read_text(encoding="utf-8"))
    frames = [only] if only else list(range(1, len(story["frames"]) + 1))
    srv, base = serve(story_dir)
    failed, written = {}, []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1920})
            if strip_fonts:   # selftest only: cut the Google Fonts import out of the design tokens
                pg.route("**/design/tokens/fonts.css", lambda r: r.fulfill(body="", content_type="text/css"))
            for f in frames:
                pg.goto(f"{base}/plugin/renderer/frames.html?f={f}", timeout=60_000)
                pg.wait_for_selector("body[data-ready='1']", timeout=60_000)
                errs = []
                err = pg.evaluate("document.body.dataset.error || ''")
                if err:
                    errs.append(f"LOAD  {err}")
                else:
                    for fam, w, it in json.loads(pg.evaluate("document.body.dataset.fonts || '[]'")):
                        if not pg.evaluate(FONT_JS, [fam, w, it]):
                            errs.append(f"FONT  {fam} {w}{' italic' if it else ''} did not load (check the network).")
                    errs += check_fit(pg.evaluate(FIT_JS))
                if errs:
                    failed[f] = errs
                    continue
                out = story_dir / f"frame-{f}.png"
                pg.locator("#canvas").screenshot(path=str(out))
                written.append(out)
                print(f"  wrote {out.name}")
            if written and not only and not strip_fonts:
                sheet(pg, story_dir, len(story["frames"]))
            b.close()
    finally:
        srv.shutdown()
    for f, errs in failed.items():
        for e in errs:
            print(f"  frame {f}: {e}")
    return failed


def sheet(pg, story_dir, n):
    """Side-by-side contact sheet of every frame, for the eyeball check (faces, crops, wording)."""
    imgs = "".join(f'<img src="/job/frame-{i}.png">' for i in range(1, n + 1) if (story_dir / f"frame-{i}.png").exists())
    html = f"<html><body style='margin:0;background:#fff;display:flex;gap:12px'>{imgs}</body>" \
           "<style>img{width:270px;height:480px}</style></html>"
    (story_dir / "_sheet.html").write_text(html, encoding="utf-8")
    pg.set_viewport_size({"width": n * 282, "height": 480})
    pg.goto(pg.url.split("/plugin/")[0] + "/job/_sheet.html")
    pg.wait_for_load_state("networkidle")
    pg.screenshot(path=str(story_dir / "_contact-sheet.png"))
    (story_dir / "_sheet.html").unlink()
    print("  wrote _contact-sheet.png")


def selftest():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="stories-selftest-"))
    try:
        (tmp / "story.json").write_text(json.dumps({"style": "strong", "frames": [
            {"bg": "#000000", "lines": [{"text": "this single line is far too long to fit inside the safe area", "color": "purple"}]},
            {"bg": "cm-3", "lines": [{"text": "fits fine", "color": "white"}]}]}), encoding="utf-8")
        fit = render(tmp, only=1)
        good = render(tmp, only=2)
        font = render(tmp, only=2, strip_fonts=True)
        checks = {
            "FIT caught": any(e.startswith("FIT") for e in fit.get(1, [])),
            "clean frame passes": not good and (tmp / "frame-2.png").exists(),
            "FONT caught": any(e.startswith("FONT") for e in font.get(2, [])),
        }
        for k, v in checks.items():
            print(f"  {k}: {'yes' if v else 'NO'}")
        return all(checks.values())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        ok = selftest()
        print("selftest ok" if ok else "selftest FAILED")
        sys.exit(0 if ok else 1)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    only = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
    sys.exit(1 if render(sys.argv[1], only=only) else 0)
