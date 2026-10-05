# Self-check for the CTA rule and the runner steps. Run: python test_goldmine_build.py (prints OK or fails loudly).
# Cases come from a hand-reviewed caption set.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goldmine_build import detect_cta

CASES = [
    ('Comment "STACK" and I will send it', (True, "STACK", "quoted")),
    ("Comment «COOK» for the recipe", (True, "COOK", "quoted")),
    ('Comment "Now" for the link', (True, "Now", "quoted")),          # quoted beats the stop list
    ("Comment **HQ** below", (True, "HQ", "bold")),
    ("Comment MIKA for AI tools", (True, "MIKA", "bare_caps")),        # non-greedy filler
    ("Comment — GUIDE for the link", (True, "GUIDE", "bare_caps")),
    ("Comment Bottleneck below and I'll send it", (True, "Bottleneck", "bare_below")),
    ("Comment Cowork for my free starter guide", (True, "Cowork", "bare_word_payoff")),
    ("Comment Cowork for fun", (False, None, None)),                  # no payoff word
    ("comment below if you agree", (False, None, None)),              # generic ask
    ('Dm me "Closer" for the link', (False, None, None)),             # dm is not an anchor
    ("Comment AI and I'll send it", (False, None, None)),             # stop word, known miss
    ("", (False, None, None)),
    ("Type “pure focus” if you believe it starts in the morning.",
     (True, "pure focus", "quoted_weak")),                            # no-payoff ask, labelled weak
    ("Type AMEN if you agree", (True, "AMEN", "bare_caps_weak")),      # no-payoff ask, labelled weak
    ("Type POSTER LAYOUT and it builds the page", (False, None, None)),  # tool instruction
    ('Type "YES" below and I will send it', (True, "YES", "quoted")),  # type + comment context
    ("Comment the word starter below and I will send the guide",
     (True, "starter", "named_word")),                                # named word, any case
    ("Comment AMEN if you agree", (True, "AMEN", "bare_caps")),        # bait: a CTA here, lm_none in the reads
]

bad = [(c, want, detect_cta(c)) for c, want in CASES if detect_cta(c) != want]
for c, want, got in bad:
    print("FAIL %r: want %s, got %s" % (c, want, got))
assert not bad, "%d CTA cases failed" % len(bad)
print("OK %d CTA cases" % len(CASES))

# ---------------------------------------------------------------- runner steps, on invented fixtures
# No network: api_key and api_get are replaced, and any call other than the free balance check or
# a faked comments page fails the run.
import contextlib, glob, io, json, shutil, subprocess, tempfile
import goldmine_build as gb

CALLS = []


def fake_get(path, params, key, timeout=300):
    CALLS.append(path)
    if path == "credits/balance":
        return 200, {"data": {"balance": 100000}}
    if path == "prism/comments":
        return 200, {"success": True, "credits_used": 5, "data": {"comments": [], "completed": True}}
    raise AssertionError("unexpected API call: " + path)


gb.api_get = fake_get
gb.api_key = lambda: "sc_fixture_key"
gb.time.sleep = lambda s: None


def make(specs):
    """specs: (handle, shortcode, mult, caption). Every spec is a breakout in the window."""
    d = tempfile.mkdtemp(prefix="goldmine_test_")
    by_h = {}
    for h, sc, mult, cap in specs:
        by_h.setdefault(h, []).append({"post": {
            "url": "https://www.instagram.com/reel/%s/" % sc, "content": {"text": cap},
            "engagement": {"views": int(1000 * mult), "comments": 10}}})
    os.makedirs(os.path.join(d, "source", "competitors", "reels"))
    for h, items in by_h.items():
        with open(os.path.join(d, "source", "competitors", "reels", h + ".json"), "w", encoding="utf-8") as f:
            json.dump({"handle": h, "reels": items}, f)
    with open(os.path.join(d, "analysis-data.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": {"generated_at": "2000-01-01T00:00:00Z", "themes": ["growth"]},
                   "period_breakouts": {"window_from": "2000-01-01", "window_to": "2000-01-31", "reels": [
                       {"id": sc, "url": "https://www.instagram.com/reel/%s/" % sc, "handle": h,
                        "views": int(1000 * mult), "mult": mult, "tier": "small", "hook": "statement",
                        "themes": ["growth"], "hook_line": "Opening line of " + sc,
                        "published_at": "2000-01-10T00:00:00Z"} for h, sc, mult, cap in specs]}}, f)
    return d


def run(step, d, **opts):
    buf, code = io.StringIO(), None
    with contextlib.redirect_stdout(buf):
        try:
            gb.STEPS[step](gb.Project(d), {k.replace("_", "-"): v for k, v in opts.items()})
        except SystemExit as e:
            code = e.code
    return buf.getvalue(), code


def next_line(out):
    return [l for l in out.splitlines() if l.startswith("NEXT:")][0]


def rjson(d, name):
    with open(os.path.join(d, "reel-build", name), encoding="utf-8") as f:
        return json.load(f)


def wjson(d, name, obj):
    with open(os.path.join(d, "reel-build", name), "w", encoding="utf-8") as f:
        json.dump(obj, f)


temps = []

# 1. Ask always, under the budget: 3 missing comment pages = 15 credits, still an ask.
d = make([("alpha_coach", "AAA001", 9.0, "x"), ("alpha_coach", "AAA002", 5.0, "x"),
          ("beta_coach", "BBB001", 4.0, "x")]); temps.append(d)
out, code = run("plan", d)
nl = next_line(out)
assert code is None, out
assert nl.startswith("NEXT: ASK the user") and "15 SocialCrawl credits" in nl and "spend 15 credits" in nl, nl
assert "fetch --approved 15" in nl and "over the" not in nl, nl
assert "no ask" not in out and "tell" not in out, out
assert CALLS == ["credits/balance"], CALLS

# 2. Ask always, over the budget: 130 missing pages = 650 credits, the ask names the budget.
specs = [("alpha_coach" if i % 2 else "beta_coach", "CCC%03d" % i, 2.5 + i / 100.0, "x") for i in range(130)]
d = make(specs); temps.append(d)
out, code = run("plan", d)
nl = next_line(out)
assert "650 SocialCrawl credits" in nl and "over the 600 credit per-pull budget" in nl, nl
assert "spend 650 credits" in nl and "fetch --approved 650" in nl, nl

# 3. --top-per-creator on plan prices the capped set, and the fetch it names takes the same cap.
out, code = run("plan", d, top_per_creator="3")
nl = next_line(out)
assert "for 6 breakout reels costs 30 SocialCrawl credits" in nl and "over the" not in nl, nl
assert "0 have, 6 to fetch (top 3 per creator)" in out, out          # skipped reels are not "have"
assert nl.endswith("fetch --approved 30 --top-per-creator 3"), nl
assert json.load(open(os.path.join(d, "reel-build", "goldmine-run.json")))["plan"]["top_per_creator"] == 3
want = ["CCC%03d" % i for i in (124, 125, 126, 127, 128, 129)]  # top 3 by mult, each creator
del CALLS[:]
out, code = run("fetch", d, approved="30", top_per_creator="3")
assert CALLS == ["prism/comments"] * 6, CALLS
got = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "source", "comments", "*.json")))
assert got == sorted(want), (got, want)
out, code = run("plan", d, top_per_creator="x")
assert code == 2 and "whole number" in out, out
out, code = run("fetch", d, approved="abc")
assert code == 2 and out.startswith("ERROR: --approved needs a whole number"), out

# 3b. fetch with no flag fetches exactly what plan priced (plan's saved top_per_creator).
d = make([("alpha_coach", "HHH%d" % i, 2.6 + i, "x") for i in range(4)] +
         [("beta_coach", "III%d" % i, 2.6 + i, "x") for i in range(4)]); temps.append(d)
out, code = run("plan", d, top_per_creator="2")
assert next_line(out).endswith("fetch --approved 20 --top-per-creator 2"), out
del CALLS[:]
out, code = run("fetch", d, approved="20")
assert CALLS == ["prism/comments"] * 4 and "(top 2 per creator)" in out, (CALLS, out)
got = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "source", "comments", "*.json")))
assert got == ["HHH2", "HHH3", "III2", "III3"], got
# an explicit flag that differs from plan's saved value wins
d = make([("alpha_coach", "HHH%d" % i, 2.6 + i, "x") for i in range(4)] +
         [("beta_coach", "III%d" % i, 2.6 + i, "x") for i in range(4)]); temps.append(d)
run("plan", d, top_per_creator="2")
del CALLS[:]
out, code = run("fetch", d, approved="20", top_per_creator="1")
got = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "source", "comments", "*.json")))
assert CALLS == ["prism/comments"] * 2 and got == ["HHH3", "III3"], (CALLS, got)

# 3c. The cap holds when the API does not report credits_used (missing, or not a number).
for used in (None, "n/a"):
    d = make([("alpha_coach", "JJJ%d" % i, 3.0 + i, "x") for i in range(5)]); temps.append(d)
    run("plan", d)
    gb.api_get = lambda path, params, key, timeout=300, used=used: (
        CALLS.append(path) or (200, dict({"success": True, "data": {"comments": [], "completed": True}},
                                         **({} if used is None else {"credits_used": used}))))
    del CALLS[:]
    out, code = run("fetch", d, approved="10")
    gb.api_get = fake_get
    assert CALLS == ["prism/comments"] * 2, (used, CALLS)
    assert "STOP: the next call would pass the approved 10 credits (spent 10)." in out, out
    assert all(json.load(open(p))["_fetch"].get("credits_estimated") is True
               for p in glob.glob(os.path.join(d, "source", "comments", "*.json"))), used

# 3d. A reported credits_used of 0 cannot lift the cap: approved // 5 calls at most. A reported
#     number also writes no credits_estimated key.
d = make([("alpha_coach", "KKK%d" % i, 3.0 + i, "x") for i in range(5)]); temps.append(d)
run("plan", d)
gb.api_get = lambda path, params, key, timeout=300: (CALLS.append(path) or (200, {
    "success": True, "credits_used": 0, "data": {"comments": [], "completed": True}}))
del CALLS[:]
out, code = run("fetch", d, approved="10")
gb.api_get = fake_get
assert CALLS == ["prism/comments"] * 2, CALLS
assert "STOP: the next call would pass the 2 calls the approved 10 credits allow (5 each)." in out, out
files = glob.glob(os.path.join(d, "source", "comments", "*.json"))
assert len(files) == 2 and not any("credits_estimated" in json.load(open(p))["_fetch"] for p in files), files

# 4. Zero breakouts: one plain message and a clean exit from every step, never a traceback.
d = make([]); temps.append(d)
out, code = run("plan", d)
assert code is None and out.strip() == gb.NO_BREAKOUTS, out
for step in ("compute", "reads", "check-reads", "transcribe"):
    out, code = run(step, d)
    assert code == 0 and out.strip() == gb.NO_BREAKOUTS, (step, code, out)
env = {k: v for k, v in os.environ.items() if k != "SOCIALCRAWL_API_KEY"}  # compute is free; no key needed
p = subprocess.run([sys.executable, gb.__file__, "compute", d], capture_output=True, text=True, timeout=120, env=env)
assert p.returncode == 0 and "Traceback" not in p.stdout + p.stderr and "nothing to build" in p.stdout, p

# 5. reads pre-fills the mechanical fields; check-reads enforces the reads rules and, on a pass,
#    writes the 3-row Proven Hooks file. Two real asks, two bait asks, one plain reel.
d = make([("alpha_coach", "DDD001", 9.0, 'Comment "GUIDE" and I will send it'),
          ("alpha_coach", "DDD002", 7.0, "Comment AMEN if you agree"),
          ("beta_coach", "EEE001", 8.0, "Three habits that changed my mornings"),
          ("beta_coach", "EEE002", 3.0, "Type “pure focus” if you believe it"),
          ("beta_coach", "EEE003", 2.6, "Comment the word starter below and I will send the checklist")])
temps.append(d)
for step in ("plan", "compute", "reads"):
    out, code = run(step, d)
    assert code is None, (step, out)
assert "Pre-filled with the mechanical fields" in out, out
st = json.load(open(os.path.join(d, "reel-build", "goldmine-run.json")))
names = st["reads"]["expected"]
pop = rjson(d, st["compute"]["popularity"])["corpus"]
assert (pop["cta_reels"], pop["weak_cta_reels"]) == (4, 1), pop     # the "pure focus" ask is weak
packet = rjson(d, st["reads"]["packet"])
prows = {r["shortcode"]: r for r in packet["reels"]}
cta = sorted(sc for sc, r in prows.items() if r["is_cta"])
assert cta == ["DDD001", "DDD002", "EEE002", "EEE003"], cta
paps = rjson(d, names["paps"])
assert sorted(r["shortcode"] for r in paps["paps"]) == cta and paps["non_cta"] == ["EEE001"]
assert paps["corpus"] == {"breakouts_total": 5, "cta_breakouts": 4, "non_cta_breakouts": 1}
for r in paps["paps"]:
    for k in ("shortcode", "handle", "url", "mult", "views", "duration_seconds", "trigger_word",
              "trigger_detection_rule", "popularity_rank"):
        assert r[k] == prows[r["shortcode"]][k], (k, r)
    assert all(r[k] is None for k in ("topic", "problem", "agitation", "promise", "solution_delivery",
                                      "source_surface", "note")), r
assert set(rjson(d, names["topicmap"])["reels"]) == set(prows)
prf = rjson(d, names["patternread"])["reels"]
assert prf["DDD001"] == {"formula": None, "lm_type": None, "magnet": None} and prf["EEE001"] == {"formula": None}
out, code = run("check-reads", d)
assert code == 1 and "check-reads: FAIL" in out, out            # the pre-fill alone never passes
out, code = run("reads", d)
assert "Pre-filled" not in out                                   # a file that exists is left alone


PRISTINE = {}


def good():
    """Write a passing set of reads, always rebuilt from the untouched pre-fill."""
    base = PRISTINE.setdefault(d, {k: json.dumps(rjson(d, names[k])) for k in names})
    for k in names:
        wjson(d, names[k], json.loads(base[k]))
    p = rjson(d, names["paps"])
    for r in p["paps"]:
        r.update(topic="Morning habits", source_surface=["caption"])
        if r["shortcode"] in ("DDD001", "EEE003"):
            r.update(promise="A morning checklist.", solution_delivery="A free checklist sent by DM.")
        else:
            r.update(note="engagement ask: no offer")
    wjson(d, names["paps"], p)
    tm = rjson(d, names["topicmap"])
    tm["topics"] = [{"id": "t01", "name": "Morning habits", "theme": "growth", "summary": "Mornings."}]
    tm["reels"] = {sc: {"topic": "t01", "angle": "How mornings go"} for sc in tm["reels"]}
    wjson(d, names["topicmap"], tm)
    pr = rjson(d, names["patternread"])
    pr["formulas"] = [{"id": "f_list", "name": "List open", "template": "[N] things that...", "summary": "A list."}]
    pr["lm_types"] = [{"id": "lm_check", "name": "Checklist", "summary": "A checklist."},
                      {"id": "lm_none", "name": "Engagement ask", "summary": "A comment ask with no offer."}]
    pr["threads"] = [{"id": "th_am", "name": "Mornings", "topics": ["t01"], "summary": "Mornings."}]
    for sc, v in pr["reels"].items():
        v["formula"] = "f_list"
        if sc in ("DDD001", "EEE003"):
            v.update(lm_type="lm_check", magnet="Morning checklist")
        elif sc in ("DDD002", "EEE002"):
            v.update(lm_type="lm_none", magnet="engagement ask")
    wjson(d, names["patternread"], pr)
    return p, tm, pr


def check(expect_fail=None):
    out, code = run("check-reads", d)
    if expect_fail:
        assert code == 1 and expect_fail in out, out
    else:
        assert code is None and "check-reads: PASS" in out, out
    return out


good(); check()                                                  # bait rows pass as lm_none
st = json.load(open(os.path.join(d, "reel-build", "goldmine-run.json")))
assert st["reads"]["passed"] is True
ph = rjson(d, st["reads"]["proven_hooks"])
assert st["reads"]["proven_hooks"] == st["reads"]["packet"].replace("Goldmine Reads Packet", "Proven Hooks")
assert [h["shortcode"] for h in ph["hooks"]] == ["DDD001", "EEE001", "DDD002"], ph   # top 3 by mult
assert ph["hooks"][0]["opening_line"] == "Opening line of DDD001" and ph["hooks"][0]["handle"] == "alpha_coach"
assert ph["hooks"][0]["formula"] == {"id": "f_list", "name": "List open", "template": "[N] things that..."}
assert ph["packet"] == st["reads"]["packet"] and ph["patternread"] == names["patternread"]

# bait with a made-up type and magnet: its null promise is no longer allowed
p, tm, pr = good(); pr["reels"]["DDD002"].update(lm_type="lm_check", magnet="Prayer guide")
wjson(d, names["patternread"], pr); check("row DDD002 needs promise and solution_delivery")
# lm_none must be labelled, never given an invented magnet
p, tm, pr = good(); pr["reels"]["EEE002"]["magnet"] = "Free focus guide"
wjson(d, names["patternread"], pr); check("never invent a lead magnet")
# a pre-filled row left without its topic
p, tm, pr = good(); p["paps"][0]["topic"] = None
wjson(d, names["paps"], p); check("needs a topic and a source_surface")
# stale row: a PAPS row for a breakout that is not a CTA
p, tm, pr = good(); p["paps"].append(dict(p["paps"][0], shortcode="EEE001"))
wjson(d, names["paps"], p); check("rows for breakouts that are not CTAs: ['EEE001']")
# stale file: a newer PAPS in reel-build/ is what the dashboard would read
good(); newer = "Lead Magnet PAPS - 5 - 12.31.99.json"
wjson(d, newer, rjson(d, names["paps"])); check("which is %s, not this run's" % newer)
os.remove(os.path.join(d, "reel-build", newer))
# lm_types: required when CTA rows exist
p, tm, pr = good(); pr["lm_types"] = []
for v in pr["reels"].values():
    v.pop("lm_type", None)
wjson(d, names["patternread"], pr); check("lm_types is empty")
good(); check()

# 6. lm_types: not required when the pull has no CTA rows.
d = make([("alpha_coach", "FFF001", 6.0, "Three habits"), ("beta_coach", "GGG001", 4.0, "Two habits")])
temps.append(d)
for step in ("plan", "compute", "reads"):
    run(step, d)
names = json.load(open(os.path.join(d, "reel-build", "goldmine-run.json")))["reads"]["expected"]
p, tm, pr = good()
assert pr["lm_types"] and not p["paps"]
pr["lm_types"] = []
wjson(d, names["patternread"], pr); check()

# 7. dashboard: the pinned tarball is verified before anything in it runs. No network: the download
#    is replaced by a local fake tarball, curl itself is stubbed, and every case gets an empty cache.
import tarfile
TOP = "content-goldmine-dashboard-" + gb.DASH_TAG.lstrip("v")
FAKE = b'import sys\na = sys.argv\nopen(a[a.index("--out") + 1], "w").write(open(a[a.index("--extras") + 1]).read())\n'


def tarball(path, comment=gb.DASH_SHA, names=(TOP + "/goldmine_dashboard.py",)):
    with tarfile.open(path, "w:gz", format=tarfile.PAX_FORMAT, pax_headers={"comment": comment}) as tf:
        for n in names:
            ti = tarfile.TarInfo(n)
            ti.size = len(FAKE)
            tf.addfile(ti, io.BytesIO(FAKE))


real_download, real_run, real_which = gb.download, gb.subprocess.run, gb.shutil.which


def dash(proj=None, **kw):
    cache = tempfile.mkdtemp(prefix="goldmine_cache_"); temps.append(cache)
    gb.dash_cache = lambda tag: cache
    gb.download = lambda url, dest: tarball(dest, **kw)
    out, code = run("dashboard", proj or d)
    return out, code, cache


out, code, cache = dash()                                        # verify passes: built, saved, NEXT publish
assert code is None and "Dashboard saved: " in out and "references/publish.md" in next_line(out), out
html = out.split("Dashboard saved: ")[1].splitlines()[0]
man = rjson(d, json.load(open(os.path.join(d, "reel-build", "goldmine-run.json")))["manifest"])
assert json.load(open(html)) == {"comments_since": man["generated_at"][:10]}, html
assert os.path.dirname(html) == os.path.join(d, "visuals")
gb.download = lambda url, dest: (_ for _ in ()).throw(AssertionError("re-downloaded"))
out, code = run("dashboard", d)                                  # a verified cache is reused
assert code is None and "Dashboard saved" in out, out
out, code, cache = dash(comment="0" * 40)                        # SHA mismatch
assert code == 6 and "commit stamp" in out and not os.path.isdir(os.path.join(cache, TOP)), out
out, code, cache = dash(names=(TOP + "/goldmine_dashboard.py", "other-folder/x.py"))  # two top folders
assert code == 7 and "laid out" in out and not os.path.isdir(os.path.join(cache, TOP)), out
out, code, cache = dash(names=(TOP + "/goldmine_dashboard.py", TOP + "/../escaped.py"))  # path traversal
assert code == 7 and not os.path.exists(os.path.join(cache, "escaped.py")), out
gb.download = real_download                                      # offline: curl runs and fails
gb.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 6, b"", b"Could not resolve host")
cache = tempfile.mkdtemp(prefix="goldmine_cache_"); temps.append(cache)
gb.dash_cache = lambda tag: cache
out, code = run("dashboard", d)
assert code == 5 and "no internet connection" in out and "Traceback" not in out, out
gb.shutil.which = lambda name: None                               # curl missing
out, code = run("dashboard", d)
assert code == 4 and "curl is not installed" in out, out
gb.subprocess.run, gb.shutil.which = real_run, real_which
z = make([]); temps.append(z)                                    # zero breakouts: the plain message
run("plan", z)
out, code, cache = dash(proj=z)
assert code == 0 and out.strip() == gb.NO_BREAKOUTS, out
print("OK dashboard: verify pass, cache reuse, SHA mismatch, two top folders, path traversal, "
      "offline, curl missing, zero breakouts")

# 8. Guards the cases above do not reach: no dashboard before check-reads, a reads resume on a
#    later day, link members, a failing assembler, a corrupt tarball, a curl timeout or OSError.
d = make([("alpha_coach", "LLL001", 6.0, "Three habits"), ("beta_coach", "MMM001", 4.0, "Two habits")])
temps.append(d)
for step in ("plan", "compute", "reads"):
    run(step, d)
rb = os.path.join(d, "reel-build")
names = json.load(open(os.path.join(rb, "goldmine-run.json")))["reads"]["expected"]
out, code, cache = dash()                                        # reads not passed: refused, nothing built
assert code == 2 and "reads have not passed" in out, out
assert os.listdir(cache) == [] and not os.path.exists(os.path.join(d, "visuals")), out
good()                                                           # resume on a later day keeps the filled files
st = json.load(open(os.path.join(rb, "goldmine-run.json")))["reads"]
filled = {k: open(os.path.join(rb, names[k]), "rb").read() for k in names}
listing, real_today = sorted(os.listdir(rb)), gb.today
gb.today = lambda: "12.31.99"
out, code = run("reads", d)
gb.today = real_today
st2 = json.load(open(os.path.join(rb, "goldmine-run.json")))["reads"]
assert code is None and (st2["packet"], st2["expected"]) == (st["packet"], names), st2
assert sorted(os.listdir(rb)) == listing and not glob.glob(os.path.join(rb, "*12.31.99*")), os.listdir(rb)
assert all(open(os.path.join(rb, names[k]), "rb").read() == filled[k] for k in names)
check()


def link_tarball(dest, kind):
    """The dashboard plus a link to it inside the same folder, so only the files-and-folders rule
    stops it (the "data" extract filter lets an inside link through)."""
    with tarfile.open(dest, "w:gz", format=tarfile.PAX_FORMAT, pax_headers={"comment": gb.DASH_SHA}) as tf:
        ti = tarfile.TarInfo(TOP + "/goldmine_dashboard.py")
        ti.size = len(FAKE)
        tf.addfile(ti, io.BytesIO(FAKE))
        ti = tarfile.TarInfo(TOP + "/link.py")
        ti.type = kind
        ti.linkname = "goldmine_dashboard.py" if kind == tarfile.SYMTYPE else TOP + "/goldmine_dashboard.py"
        tf.addfile(ti)


def empty_cache():
    cache = tempfile.mkdtemp(prefix="goldmine_cache_"); temps.append(cache)
    gb.dash_cache = lambda tag: cache
    return cache


for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):                  # a symlink, then a hardlink member
    cache = empty_cache()
    gb.download = lambda url, dest, kind=kind: link_tarball(dest, kind)
    out, code = run("dashboard", d)
    assert code == 7 and "laid out" in out and os.listdir(cache) == [], (kind, out)
out, code, cache = dash()                                        # the assembler fails: exit 8, log kept
assert code is None, out
with open(os.path.join(cache, TOP, "goldmine_dashboard.py"), "w") as f:  # writes the page, then fails
    f.write('import sys\na = sys.argv\nopen(a[a.index("--out") + 1], "w").write("x")\n'
            'print("ERROR: boom")\nsys.exit(1)\n')
os.remove(os.path.join(rb, "dashboard-build.log"))
out, code = run("dashboard", d)
assert code == 8 and [l for l in out.splitlines() if l.startswith("ERROR:")] == [out.strip()], out
assert ": boom." in out and "Dashboard saved" not in out, out
assert "ERROR: boom" in open(os.path.join(rb, "dashboard-build.log"), encoding="utf-8").read()


def bad_gzip(url, dest):
    with open(dest, "wb") as f:
        f.write(b"not a gzip file")


cache = empty_cache()                                            # corrupt tarball
gb.download = bad_gzip
out, code = run("dashboard", d)
assert code == 7 and "laid out" in out and "Traceback" not in out and os.listdir(cache) == [], out
gb.download, gb.shutil.which = real_download, lambda name: "curl"   # curl times out, or cannot start
for exc in (subprocess.TimeoutExpired("curl", 300), OSError("curl could not start")):
    cache = empty_cache()
    gb.subprocess.run = lambda *a, exc=exc, **k: (_ for _ in ()).throw(exc)
    out, code = run("dashboard", d)
    assert code == 5 and out.startswith("ERROR: Could not download") and os.listdir(cache) == [], (exc, out)
gb.subprocess.run, gb.shutil.which = real_run, real_which
print("OK guards: no dashboard before check-reads, reads resume on a later day, symlink and hardlink "
      "members, assembler failure, corrupt tarball, curl timeout and OSError")

for t in temps:
    shutil.rmtree(t, ignore_errors=True)
print("OK runner steps: ask always (under and over budget), top-per-creator, zero breakouts, "
      "reads pre-fill, bait as lm_none, stale PAPS row and file, lm_types rule, proven hooks")
