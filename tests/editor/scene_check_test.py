#!/usr/bin/env python3
"""G2-a light check for scripts/scene_check.py (the scene validator). No render.

usage: python -X utf8 -I tests/editor/scene_check_test.py
Every shipped scene passes `check`. Then, in a temp copy of the scenes, each planted mutant must FAIL with the
right reason, and the same copy un-mutated must pass in the same run (so no check is vacuous): a CDN GSAP
<script src>, a removed @font-face, a fill over maxChars, a CSS @keyframes, a CSS translateX(-50%), the CSS
translate property at -50% (either axis), Math.random(), z-index 700, a body background, a counter value missing
from the transcript, a counter with no transcript, a counter `from` outside 0..value (passing ones alongside).
G2-b registry rules, in a temp tree of the own scenes (which passes with no registry-allow.json) plus a fake
vendored hf-counter (the own counter renamed, with the header comment, licence Apache-2.0, category counter) and
its registry-allow.json entry (which passes): CDN GSAP, an asset file with no entry, an html-referenced asset with
no entry, scene.html not matching ours_sha256, a missing header comment, no registry-allow.json, a refused verdict,
a missing / unknown category must each FAIL, and a listed asset passes; then hf-counter fills by category: 47 said
passes, 47 never said fails (VES-3 f), from 48 fails. Then `--selftest`. Prints PASS/FAIL per check; exit 0 = all passed.
"""
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "editor-superengine"
SCENES = PLUGIN / "scenes"
CHECK = PLUGIN / "scripts" / "scene_check.py"
IDS = ("callout", "counter", "cta-end-card", "hook-title", "list", "lower-third", "quote", "stat-card", "slots", "cover-title")
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
ALL = sorted(d.name for d in SCENES.iterdir() if d.is_dir())
ck("every shipped scene passes check (%d OK lines, the own scenes included, exit 0)" % len(ALL),
   p.returncode == 0 and set(IDS) <= set(ALL)
   and sorted(l[3:] for l in p.stdout.splitlines() if l.startswith("OK ")) == ALL, out(p))


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

# ---- G2-b: registry-allow rules, on a fake vendored scene in a temp tree ------------------------------------
HDR = ("<!-- Adapted from HyperFrames registry/components/count-up (https://github.com/heygen-com/hyperframes, "
       "tag v0.8.184, d15a274c), Apache License 2.0, Copyright 2026 HeyGen, Inc. Modified by editor-superengine: "
       "portrait 1080x1920, local GSAP 3.15.0, Inter 400, scene contract. -->\n")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731


def save_allow(d, entries):
    write(d, "registry-allow.json", entries)


def tree(t):
    """A temp scenes/ holding a copy of the own scenes only (no registry-allow.json)."""
    d = Path(t) / "scenes"
    for sid in IDS:
        shutil.copytree(SCENES / sid, d / sid)
    return d


def add_vendored(d):
    """A fake vendored hf-counter (the own counter renamed, header comment, Apache-2.0) and its allowed entry."""
    v = d / "hf-counter"
    v.mkdir()
    html = (SCENES / "counter" / "scene.html").read_text(encoding="utf-8")
    html = html.replace('"counter"', '"hf-counter"').replace("#counter", "#hf-counter")
    (v / "scene.html").write_bytes((HDR + html).encode("utf-8"))
    spec = json.loads((SCENES / "counter" / "scene.json").read_text(encoding="utf-8"))
    spec.update(id="hf-counter", category="counter", source="HyperFrames registry/components/count-up (v0.8.184)",
                licence="Apache-2.0")
    write(v, "scene.json", spec)
    shutil.copy2(SCENES / "counter" / "preview.png", v / "preview.png")
    entry = {"id": "hf-counter", "category": "counter", "source": "registry/components/count-up", "tag": "v0.8.184",
             "tag_commit": "d15a274c198cf18bc1df177cbe20df95392a8947",
             "files": [{"path": "registry/components/count-up/count-up.html", "blob": "0" * 40, "sha256": "0" * 64}],
             "ours_sha256": sha(v / "scene.html"), "changed": True, "licence": "Apache-2.0", "verdict": "allowed",
             "reason": "test fixture"}
    save_allow(d, [entry])
    return v, entry


def edit(path, old, new):
    s = Path(path).read_text(encoding="utf-8")
    Path(path).write_bytes(s.replace(old, new, 1).encode("utf-8"))
    return old in s


with tempfile.TemporaryDirectory() as t:
    d = tree(t)
    p = run("check", d)
    ck(f"G2-b: the {len(IDS)} own scenes with no registry-allow.json pass",
       p.returncode == 0 and p.stdout.count("OK ") == len(IDS), out(p))
    add_vendored(d)
    p = run("check", d)
    ck(f"G2-b: plus a vendored hf-counter with its allowed entry passes ({len(IDS) + 1} OK)",
       p.returncode == 0 and p.stdout.count("OK ") == len(IDS) + 1 and "OK hf-counter" in p.stdout, out(p))


def vmutant(name, change, reason, sid="hf-counter"):
    """Fresh tree + vendored hf-counter; prove it passes; change(d, v, entry) plants one fault; prove it FAILs."""
    with tempfile.TemporaryDirectory() as t:
        d = tree(t)
        v, entry = add_vendored(d)
        before = run("check", d)
        planted = change(d, v, entry) is not False
        after = run("check", d)
        lines = [l for l in after.stdout.splitlines() if l.startswith(f"FAIL {sid}: ")]
        ck(f"G2-b {name}: un-mutated copy passes", before.returncode == 0 and "OK hf-counter" in before.stdout, out(before))
        ck(f"G2-b {name}: fails with '{reason}'", planted and after.returncode == 1 and any(reason in l for l in lines),
           ("change not planted; " if not planted else "") + out(after))


def resynced(fn):
    """Plant fn's change, then record the new ours_sha256, so only the planted fault can fail."""
    def change(d, v, entry):
        ok = fn(d, v, entry)
        entry["ours_sha256"] = sha(v / "scene.html")
        save_allow(d, [entry])
        return ok
    return change


vmutant("vendored block with CDN GSAP", resynced(lambda d, v, e: edit(v / "scene.html", 'src="./vendor/gsap.min.js"',
        'src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"')), "reaches the internet")
vmutant("asset file with no registry-allow entry", lambda d, v, e: (v / "avatar.jpg").write_bytes(b"\xff\xd8\xff fake"),
        "unconfirmed asset avatar.jpg")
vmutant("html-referenced asset with no entry", resynced(lambda d, v, e: edit(v / "scene.html", "</style>",
        '#hf-counter .bar { background-image: url("./assets/grain.png"); }\n    </style>')),
        "unconfirmed asset ./assets/grain.png (referenced by scene.html)")
vmutant("scene.html no longer matches ours_sha256", lambda d, v, e: edit(v / "scene.html", "</style>",
        "#hf-counter .num { letter-spacing: 1px; }\n    </style>"), "is not the ours_sha256")
vmutant("missing header comment", resynced(lambda d, v, e: edit(v / "scene.html", HDR, "")),
        "must open with the header comment")
vmutant("vendored scene with no registry-allow.json", lambda d, v, e: (d / "registry-allow.json").unlink(),
        "there is no registry-allow.json")
vmutant("vendored scene whose entry is refused", lambda d, v, e: save_allow(d, [dict(e, verdict="refused")]),
        "a refused item ships no scene folder")
vmutant("scene.json with no category", lambda d, v, e: edit(d / "list" / "scene.json", '  "category": "list",\n', ""),
        "scene.json is missing category", sid="list")
vmutant("scene.json with an unknown category", lambda d, v, e: edit(d / "list" / "scene.json", '"category": "list"',
        '"category": "banner"'), "category 'banner' must be one of", sid="list")
vmutant("vendored scene with no entry in an existing registry-allow.json", lambda d, v, e: save_allow(d, []),
        "there is none for hf-counter")
vmutant("entry category differs from scene.json's", lambda d, v, e: save_allow(d, [dict(e, category="stat-card")]),
        "entry says category 'stat-card' but scene.json says 'counter'")
for key in ("category", "source", "tag", "tag_commit", "files", "ours_sha256", "changed", "licence", "verdict", "reason"):
    vmutant(f"entry with no {key}", lambda d, v, e, key=key: save_allow(d, [{k: x for k, x in e.items() if k != key}]),
            "the verdict None" if key == "verdict" else f"entry is missing {key}")
vmutant("listed asset whose sha256 does not match", lambda d, v, e: ((v / "avatar.jpg").write_bytes(b"\xff\xd8\xff fake"),
        save_allow(d, [dict(e, files=e["files"] + [{"path": "registry/components/count-up/avatar.jpg", "blob": "0" * 40,
                                                    "sha256": "0" * 64}])])),
        "unconfirmed asset avatar.jpg: its sha256 is not the one")
vmutant("id listed twice in registry-allow.json", lambda d, v, e: save_allow(d, [e, dict(e)]),
        "lists 'hf-counter' more than once")
vmutant("header buried further down the file", resynced(lambda d, v, e: edit(v / "scene.html", HDR, "")
        and edit(v / "scene.html", "</style>", "</style>\n" + HDR)), "must open with the header comment")
vmutant("registry-allow.json that isn't JSON", lambda d, v, e: (d / "registry-allow.json").write_bytes(b"[{not json"),
        "registry-allow.json can't be read as JSON", sid="registry-allow.json")
vmutant("registry-allow.json of the wrong shape", lambda d, v, e: save_allow(d, {"x": 1}),
        "registry-allow.json must be a list of entries", sid="registry-allow.json")

with tempfile.TemporaryDirectory() as t:
    d = tree(t)
    v, entry = add_vendored(d)
    moved = edit(v / "scene.html", HDR + "<!doctype html>\n", "<!doctype html>\n" + HDR)
    entry["ours_sha256"] = sha(v / "scene.html")
    save_allow(d, [entry])
    p = run("check", d)
    ck("G2-b: the header on line 2, right after <!doctype html>, passes",
       moved and (v / "scene.html").read_text(encoding="utf-8").split("\n")[1].startswith("<!-- Adapted from")
       and p.returncode == 0 and "OK hf-counter" in p.stdout, out(p))

with tempfile.TemporaryDirectory() as t:
    d = tree(t)
    v, entry = add_vendored(d)
    (v / "avatar.jpg").write_bytes(b"\xff\xd8\xff fake")
    entry["files"].append({"path": "registry/components/count-up/avatar.jpg", "blob": "0" * 40, "sha256": sha(v / "avatar.jpg")})
    save_allow(d, [entry])
    p = run("check", d)
    ck("G2-b: an asset listed (name + sha256) in the scene's registry-allow files passes",
       p.returncode == 0 and "OK hf-counter" in p.stdout, out(p))
    said = write(t, "said.json", words("We", "hit", "47", "sign-ups", "this", "month."))
    unsaid = write(t, "unsaid.json", words("We", "hit", "46", "sign-ups", "this", "month."))
    for tag, frm, tr, code, reason in (("47 said", 0, said, 0, ""),
                                       ("47 never said", 0, unsaid, 1, "47 is not said in the transcript"),
                                       ("from 48", 48, said, 1, "from must lie between 0 and the value")):
        f = write(t, f"hf-{frm}-{code}.json", {"id": "hf-counter", "slots": {"label": "sign-ups"}, "params": {"value": 47, "from": frm}})
        p = run("fill", "hf-counter", f, "--transcript", tr, "--scenes", d)
        ck(f"G2-b fill: hf-counter (category counter) {tag} " + ("passes" if code == 0 else f"fails ('{reason}')"),
           p.returncode == code and (code == 0 and p.stdout.strip() == "OK hf-counter" or code == 1 and reason in p.stdout), out(p))

p = run("--selftest")
ck("scene_check.py --selftest", p.returncode == 0 and p.stdout.strip() == "selftest ok", out(p))

print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
