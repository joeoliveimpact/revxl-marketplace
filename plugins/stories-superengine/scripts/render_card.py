#!/usr/bin/env python3
"""Render one quote card (an X-style post of the coach's own words) to a PNG.

Usage:
    python render_card.py <job_dir> "<settings>" <out.png>
    python render_card.py --selftest       # proves FONT and FIT catch planted defects

<job_dir> holds the coach's avatar and any background photo; paths in the settings are
relative to it. Settings are URL keys (see the stories-quote-card skill):
    size=story|carousel|square  theme=auto|dark|light|dim  font=native|brand  layout=full|card
    text=...  meta=...  bg=...  storybg=...  storytext=...  ring=on|off  name=...  handle=...  avatar=...
Type a line break as a literal \\n.

Gates (either failing = no PNG, exit 1):
  FONT  every weight the card draws has a loaded face (FontFace.status, never document.fonts.check())
  FIT   story: text bubble + card inside the safe area (270px top bar, 384px reply bar)
        carousel/square: the post inside the frame
Past 220 characters it warns: split into two cards.
"""
import pathlib
import re
import shutil
import sys
import tempfile
import urllib.parse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _serve import FONT_JS, serve  # noqa: E402

SIZES = {"story": (1080, 1920), "carousel": (1080, 1440), "square": (1080, 1080)}
WEIGHTS = {"native": ("Inter", [400, 700]), "brand": ("Poppins", [400, 600])}
SOFT_CAP = 220
KEYS = ("size", "theme", "font", "layout", "text", "meta", "bg", "storybg", "storytext", "ring",
        "name", "handle", "avatar", "check")


def parse_settings(qs):
    """Split on '&' only where a known key follows, so a line like "Sets & reps" keeps its '&'."""
    parts = re.split(r"&(?=(?:%s)=)" % "|".join(KEYS), qs)
    return dict(p.split("=", 1) if "=" in p else (p, "") for p in parts)

FIT_JS = """() => {
  const safe = document.getElementById('safe');
  const bound = (safe || document.getElementById('canvas')).getBoundingClientRect();
  const items = safe ? [...safe.children] : [document.getElementById('post')];
  let top = Infinity, bottom = Infinity;
  for (const el of items) {
    const r = el.getBoundingClientRect();
    top = Math.min(top, r.top - bound.top);
    bottom = Math.min(bottom, bound.bottom - r.bottom);
  }
  return [top, bottom, !!safe];
}"""


def render(job_dir, qs, out, strip_fonts=False):
    s = parse_settings(qs)
    missing = [k for k in ("name", "handle") if not s.get(k)]
    if missing:
        return [f"SETUP missing {', '.join(missing)}: read them from the coach's brand config, never a web search"]
    size = s.get("size", "carousel")
    w, h = SIZES.get(size, SIZES["carousel"])
    fam, weights = WEIGHTS.get(s.get("font", "native"), WEIGHTS["native"])
    need = [(fam, x, False) for x in weights]
    if size == "story" and s.get("storytext"):
        need.append(("Roboto Condensed", 400, False))
    text = s.get("text", "").replace("\\n", "\n")
    if len(text) > SOFT_CAP:
        print(f"  WARNING: post is {len(text)} characters (soft cap {SOFT_CAP}). Split it into two cards.")

    srv, base = serve(job_dir)
    fails = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": w, "height": h})
            if strip_fonts:
                pg.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(body="", content_type="text/css"))
            pg.goto(f"{base}/plugin/renderer/card.html?{urllib.parse.urlencode(s)}", timeout=60_000)
            pg.wait_for_selector("body[data-ready='1']", timeout=60_000)
            lost = [f"{f} {x}" for f, x, it in need if not pg.evaluate(FONT_JS, [f, x, it])]
            if lost:
                fails.append(f"FONT  not loaded: {', '.join(lost)} (check the network)")
            top, bottom, story = pg.evaluate(FIT_JS)
            if min(top, bottom) < 0:
                where = "the story safe area" if story else f"the {w}x{h} frame"
                fails.append(f"FIT   post overflows {where} (top {top:.0f}px, bottom {bottom:.0f}px). Shorten or split it.")
            if not fails:
                out = pathlib.Path(out)
                out.parent.mkdir(parents=True, exist_ok=True)
                pg.locator("#canvas").screenshot(path=str(out))
                theme = pg.evaluate("document.body.dataset.theme || 'set by hand / full-frame'")
                print(f"  wrote {out} ({w}x{h}, theme {theme})")
            b.close()
    finally:
        srv.shutdown()
    return fails


def selftest():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="stories-card-"))
    who = "name=Sam Rivera&handle=@samfit"
    try:
        cases = {
            "FIT caught": ("FIT", f"size=story&{who}&storytext=too long&text=" + "This line repeats until the card runs off the safe area. " * 22, False),
            "FONT caught": ("FONT", f"size=story&{who}&text=Fonts stripped from the page.", True),
            "SETUP caught": ("SETUP", "size=story&text=No name or handle given.", False),
        }
        ok = True
        for label, (gate, qs, strip) in cases.items():
            f = render(tmp, qs, tmp / "x.png", strip_fonts=strip)
            hit = any(x.startswith(gate) for x in f)
            print(f"  {label}: {'yes' if hit else 'NO'}")
            ok &= hit
        amp = parse_settings(f"size=story&{who}&text=Sets & reps don't matter&meta=off")
        kept = amp.get("text") == "Sets & reps don't matter" and amp.get("meta") == "off"
        print(f"  '&' kept in text: {'yes' if kept else 'NO'}")
        ok &= kept
        good = render(tmp, f"size=story&layout=card&storybg=cm-3&{who}&text=Clean card.\\n\\nSecond beat.&meta=8:00 AM", tmp / "ok.png")
        print(f"  clean card passes: {'yes' if not good and (tmp / 'ok.png').exists() else 'NO'}")
        return ok and not good
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        ok = selftest()
        print("selftest ok" if ok else "selftest FAILED")
        sys.exit(0 if ok else 1)
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    fails = render(*sys.argv[1:4])
    for f in fails:
        print("  " + f)
    sys.exit(1 if fails else 0)
