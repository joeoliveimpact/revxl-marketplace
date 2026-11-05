#!/usr/bin/env python3
"""G2-a light check for scripts/scene_check.py (the scene validator). No render.

usage: python -X utf8 -I tests/editor/scene_check_test.py
Every shipped scene passes `check`. Then, in a temp copy of the scenes, each planted mutant must FAIL with the
right reason, and the same copy un-mutated must pass in the same run (so no check is vacuous): a CDN GSAP
<script src>, a removed @font-face, a fill over maxChars, a CSS @keyframes, a CSS translateX(-50%), the CSS
translate property at -50% (either axis), Math.random(), z-index 700, a body background, a counter value missing
from the transcript, a counter with no transcript, a counter `from` outside 0..value (passing ones alongside).
Then `--selftest`. Prints PASS/FAIL per check; exit 0 = all passed.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "editor-superengine"
SCENES = PLUGIN / "scenes"
CHECK = PLUGIN / "scripts" / "scene_check.py"
IDS = ("callout", "counter", "cta-end-card", "hook-title", "list", "lower-third", "quote", "stat-card")
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def run(*args):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(CHECK), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)


def out(p):
    return "exit %s: %s" % (p.returncode, (p.stdout + p.stderr).strip()[-600:])


p = run("check")
ck("every shipped scene passes check (8 OK lines, exit 0)",
   p.returncode == 0 and sorted(l[3:] for l in p.stdout.splitlines() if l.startswith("OK ")) == list(IDS), out(p))


def mutant(name, sid, old, new, reason):
    """Copy the scenes, prove the copy passes, plant one change in <sid>/scene.html, prove it fails for reason."""
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "scenes"
        shutil.copytree(SCENES, d)
        before = run("check", d)
        h = d / sid / "scene.html"
        s = h.read_text(encoding="utf-8")
        planted = old in s
        h.write_bytes(s.replace(old, new, 1).encode("utf-8"))
        after = run("check", d)
        lines = [l for l in after.stdout.splitlines() if l.startswith(f"FAIL {sid}: ")]
        ck(f"{name}: un-mutated copy passes", before.returncode == 0, out(before))
        ck(f"{name}: fails with '{reason}'", planted and after.returncode == 1 and any(reason in l for l in lines),
           ("text to replace not found; " if not planted else "") + out(after))


FACE = '@font-face { font-family: "Inter"; src: url("./fonts/Inter-Regular.woff2") format("woff2"); font-weight: 400; font-style: normal; }'
mutant("CDN GSAP <script src>", "counter", 'src="./vendor/gsap.min.js"',
       'src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"', "reaches the internet")
mutant("removed @font-face", "quote", FACE, "", 'font family \'Inter\' has no @font-face')
mutant("CSS @keyframes", "lower-third", "</style>",
       "@keyframes pop { from { opacity: 0; } to { opacity: 1; } }\n    </style>", "uses CSS @keyframes")
mutant("CSS translateX(-50%)", "callout", "</style>",
       "#callout .text { transform: translateX(-50%); }\n    </style>", "centres with CSS translate(-50%")
mutant("CSS translate: -50% 0", "hook-title", "#hook-title .block { position: absolute;",
       "#hook-title .block { position: absolute; translate: -50% 0;", "centres with the CSS translate property")
mutant("CSS translate: 0 -50%", "callout", "</style>",
       "#callout .text { translate: 0 -50%; }\n    </style>", "centres with the CSS translate property")
mutant("Math.random()", "list", "const tl = gsap.timeline", "const r = Math.random();\n        const tl = gsap.timeline",
       "uses Math.random")
mutant("z-index 700", "stat-card", "z-index: 400", "z-index: 700", "z-index 700 is outside the scene layer band")
mutant("body background", "hook-title", "html, body { width: 1080px;", "html, body { background: #000000; width: 1080px;",
       "html, body and the root stay transparent")


def write(d, name, obj):
    p = Path(d) / name
    p.write_bytes(json.dumps(obj).encode("utf-8"))
    return p


with tempfile.TemporaryDirectory() as t:
    words = lambda *w: {"text": " ".join(w), "words": [{"word": x, "start": i, "end": i + 0.5} for i, x in enumerate(w)]}  # noqa: E731
    said = write(t, "said.json", words("We", "hit", "47", "sign-ups", "this", "month."))
    unsaid = write(t, "unsaid.json", words("We", "hit", "46", "sign-ups", "this", "month."))
    counter = write(t, "counter.json", {"id": "counter", "slots": {"label": "sign-ups this month"}, "params": {"value": 47}})
    p = run("fill", "counter", counter, "--transcript", said)
    ck("fill: counter 47 with 47 in the transcript passes", p.returncode == 0 and p.stdout.strip() == "OK counter", out(p))
    p = run("fill", "counter", counter, "--transcript", unsaid)
    ck("fill: counter 47 missing from the transcript fails (VES-3 f)",
       p.returncode == 1 and "47 is not said in the transcript" in p.stdout, out(p))
    p = run("fill", "counter", counter)
    ck("fill: counter with no transcript fails", p.returncode == 1 and "it was not given" in p.stdout, out(p))
    for frm, code, reason in ((10, 0, ""), (0, 0, ""), (47, 0, ""), (-99999999, 1, "param from -99999999 must be between"),
                              (48, 1, "from must lie between 0 and the value"), (-1, 1, "from must lie between 0 and the value")):
        f = write(t, f"from{frm}.json", {"id": "counter", "slots": {"label": "sign-ups"}, "params": {"value": 47, "from": frm}})
        p = run("fill", "counter", f, "--transcript", said)
        ck(f"fill: counter 47 from {frm} " + ("passes" if code == 0 else f"fails ('{reason}')"),
           p.returncode == code and (code == 0 and p.stdout.strip() == "OK counter" or code == 1 and reason in p.stdout), out(p))
    f = write(t, "fromwide.json", {"id": "counter", "slots": {"label": "sign-ups"}, "params": {"value": 47, "prefix": "$", "from": 9999999}})
    p = run("fill", "counter", f, "--transcript", said)
    ck("fill: counter $47 from 9999999 fails (the from end must fit the display, F-11)",
       p.returncode == 1 and "(from)" in p.stdout, out(p))
    for n, code in ((32, 0), (33, 1)):
        f = write(t, f"callout{n}.json", {"id": "callout", "slots": {"text": "W" * n}, "params": {}})
        p = run("fill", "callout", f)
        ck(f"fill: callout text of {n} characters (maxChars 32) " + ("passes" if code == 0 else "fails (F-11)"),
           p.returncode == code and (code == 0 or "fits 32 at most" in p.stdout), out(p))

p = run("--selftest")
ck("scene_check.py --selftest", p.returncode == 0 and p.stdout.strip() == "selftest ok", out(p))

print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
