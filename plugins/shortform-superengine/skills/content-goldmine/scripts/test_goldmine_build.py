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
    ("Comment\u2014GUIDE", (True, "GUIDE", "bare_caps")),               # em dash, no spaces
    ("Comment\u2014Bottleneck below", (True, "Bottleneck", "bare_below")),             # em dash, bare_below
    ("Comment\u2014Cowork for my free starter guide", (True, "Cowork", "bare_word_payoff")),  # em dash, bare_word
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

# 1. Ask always, under the budget: three levels, each priced, the client picks. Here Standard and
#    Deep cost the same (15 credits) and both are shown as they are.
d = make([("alpha_coach", "AAA001", 9.0, "x"), ("alpha_coach", "AAA002", 5.0, "x"),
          ("beta_coach", "BBB001", 4.0, "x")]); temps.append(d)
out, code = run("plan", d)
nl = next_line(out)
assert code is None, out
assert nl.startswith("NEXT: ASK the user to pick one level") and "posted 2000-01-01 to 2000-01-31" in nl, nl
assert "Light, the single best breakout per competitor: 2 reels, 10 credits." in nl, nl
assert "Standard, the top 3 breakouts per competitor: 3 reels, 15 credits." in nl, nl
assert "Deep, every breakout in the window: 3 reels, 15 credits." in nl, nl
assert "Your balance is 100000 SocialCrawl credits." in nl and 'A bare yes is not a pick: ask "Which level?"' in nl, nl
assert nl.endswith("Light: fetch --approved 10 --top-per-creator 1; Standard: fetch --approved 15 "
                   "--top-per-creator 3; Deep: fetch --approved 15"), nl
assert "over the" not in nl and "more than your balance" not in nl and "30 days" not in nl, nl
assert "no ask" not in out and "tell" not in out, out
assert CALLS == ["credits/balance"], CALLS

# 2. Ask always, over the budget: Deep is 130 missing pages = 650 credits, and only Deep names the budget.
specs = [("alpha_coach" if i % 2 else "beta_coach", "CCC%03d" % i, 2.5 + i / 100.0, "x") for i in range(130)]
d = make(specs); temps.append(d)
out, code = run("plan", d)
nl = next_line(out)
assert "Deep, every breakout in the window: 130 reels, 650 credits. That is over the 600 credit per-pull budget." in nl, nl
assert nl.count("over the 600") == 1 and "2 reels, 10 credits." in nl and "6 reels, 30 credits." in nl, nl
assert nl.endswith("Deep: fetch --approved 650"), nl

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

# 3c. The cap holds when the API does not report credits_used (missing, or not a number). Flagged:
#     top 5 priced at 25, approved only 10.
for used in (None, "n/a"):
    d = make([("alpha_coach", "JJJ%d" % i, 3.0 + i, "x") for i in range(5)]); temps.append(d)
    run("plan", d, top_per_creator="5")
    gb.api_get = lambda path, params, key, timeout=300, used=used: (
        CALLS.append(path) or (200, dict({"success": True, "data": {"comments": [], "completed": True}},
                                         **({} if used is None else {"credits_used": used}))))
    del CALLS[:]
    out, code = run("fetch", d, approved="10", top_per_creator="5")
    gb.api_get = fake_get
    assert CALLS == ["prism/comments"] * 2, (used, CALLS)
    assert "STOP: the next call would pass the approved 10 credits (spent 10)." in out, out
    assert all(json.load(open(p))["_fetch"].get("credits_estimated") is True
               for p in glob.glob(os.path.join(d, "source", "comments", "*.json"))), used

# 3d. A reported credits_used of 0 cannot lift the cap: approved // 5 calls at most. A reported
#     number also writes no credits_estimated key.
d = make([("alpha_coach", "KKK%d" % i, 3.0 + i, "x") for i in range(5)]); temps.append(d)
run("plan", d, top_per_creator="5")
gb.api_get = lambda path, params, key, timeout=300: (CALLS.append(path) or (200, {
    "success": True, "credits_used": 0, "data": {"comments": [], "completed": True}}))
del CALLS[:]
out, code = run("fetch", d, approved="10", top_per_creator="5")
gb.api_get = fake_get
assert CALLS == ["prism/comments"] * 2, CALLS
assert "STOP: the next call would pass the 2 calls the approved 10 credits allow (5 each)." in out, out
files = glob.glob(os.path.join(d, "source", "comments", "*.json"))
assert len(files) == 2 and not any("credits_estimated" in json.load(open(p))["_fetch"] for p in files), files

# 3e. Three levels with distinct prices: one creator with 1 breakout, one with 5. Light 2 reels, Standard
#     1 + 3, Deep all 6. plan saves the three levels and keeps top_per_creator None.
MIXED = [("solo_coach", "SOL001", 6.0, "x")] + [("multi_coach", "MUL%03d" % i, 3.0 + i, "x") for i in range(5)]
d = make(MIXED); temps.append(d)
out, code = run("plan", d)
nl = next_line(out)
assert "Light, the single best breakout per competitor: 2 reels, 10 credits." in nl, nl
assert "Standard, the top 3 breakouts per competitor: 4 reels, 20 credits." in nl, nl
assert "Deep, every breakout in the window: 6 reels, 30 credits." in nl, nl
assert nl.endswith("Light: fetch --approved 10 --top-per-creator 1; Standard: fetch --approved 20 "
                   "--top-per-creator 3; Deep: fetch --approved 30"), nl
plan = rjson(d, "goldmine-run.json")["plan"]
assert plan["top_per_creator"] is None and plan["levels"] == {
    "light": {"top_per_creator": 1, "reels": 2, "credits": 10},
    "standard": {"top_per_creator": 3, "reels": 4, "credits": 20},
    "deep": {"top_per_creator": None, "reels": 6, "credits": 30}}, plan
# a Light price with no flag must not fetch: name the level, zero calls, no files
del CALLS[:]
out, code = run("fetch", d, approved="10")
assert code == 2 and "Name the level" in out and CALLS == [], (code, CALLS, out)
assert not glob.glob(os.path.join(d, "source", "comments", "*.json"))
# the Light command fetches exactly the best breakout per creator
out, code = run("fetch", d, approved="10", top_per_creator="1")
got = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "source", "comments", "*.json")))
assert CALLS == ["prism/comments"] * 2 and got == ["MUL004", "SOL001"], (CALLS, got)
# 3f. A level with nothing new costs 0 and says so; it names no fetch command.
out, code = run("plan", d)
nl = next_line(out)
assert "Light, the single best breakout per competitor: nothing new at this level" in nl and "Light: no fetch" in nl, nl
assert "Standard, the top 3 breakouts per competitor: 2 reels, 10 credits." in nl and nl.endswith(
    "Standard: fetch --approved 10 --top-per-creator 3; Deep: fetch --approved 20"), nl


def with_balance(resp):
    """fake_get, but the balance call answers resp: (status, body)."""
    def get(path, params, key, timeout=300):
        if path == "credits/balance":
            CALLS.append(path)
            return resp
        return fake_get(path, params, key, timeout)
    return get


# 3g. Balance below Light: say so plainly, no ask. Balance between levels: only the dearer ones are marked.
d = make(MIXED); temps.append(d)
gb.api_get = with_balance((200, {"data": {"balance": 5}}))
out, code = run("plan", d)
nl = next_line(out)
assert nl.startswith("NEXT: balance 5 is below even the cheapest level (10 credits)") and "ASK" not in nl, nl
gb.api_get = with_balance((200, {"data": {"balance": 25}}))
out, code = run("plan", d)
nl = next_line(out)
assert nl.count("That is more than your balance.") == 1 and "6 reels, 30 credits. That is more than your balance." in nl, nl
assert "Your balance is 25 SocialCrawl credits." in nl, nl
# 3h. Balance unknown: a failed balance call still shows every price; no key says so and still prices.
gb.api_get = with_balance((500, {"error": "down"}))
out, code = run("plan", d)
nl = next_line(out)
assert "balance unknown" in nl and "Balance           : unknown" in out and "6 reels, 30 credits." in nl, nl
assert nl.startswith("NEXT: ASK the user to pick one level") and "more than your balance" not in nl, nl
gb.api_get, gb.api_key = fake_get, lambda: None
del CALLS[:]
out, code = run("plan", d)
gb.api_key = lambda: "sc_fixture_key"
assert next_line(out).startswith("NEXT: no SocialCrawl key found") and CALLS == [], (CALLS, out)
assert "Balance           : unknown" in out and "Light 2 reels, 10 credits, Standard 4 reels, 20 credits, " \
       "Deep 6 reels, 30 credits" in out, out
# 3i. --top-per-creator must be a whole number of 1 or more.
for bad_n in ("0", "²", "-1"):
    out, code = run("plan", d, top_per_creator=bad_n)
    assert code == 2 and "whole number of 1 or more" in out, (bad_n, out)
    out, code = run("fetch", d, approved="30", top_per_creator=bad_n)
    assert code == 2 and "whole number of 1 or more" in out, (bad_n, out)
del CALLS[:]
print("OK depth levels: three prices, equal prices shown, a 0-credit level, balance below, between and "
      "unknown, the Light command, name the level, top-per-creator 1 or more")

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

# 4b. A zero first run leaves no goldmine-run.json, so the next run is still a first run (the 30-day
#     window). Once that window finds breakouts, plan freezes them as usual.
d = make([("alpha_coach", "NNN001", 5.0, "x")]); temps.append(d)
ap = os.path.join(d, "analysis-data.json")
full = json.load(open(ap))
with open(ap, "w", encoding="utf-8") as f:
    json.dump(dict(full, period_breakouts=dict(full["period_breakouts"], reels=[])), f)
out, code = run("plan", d)
assert code is None and out.strip() == gb.NO_BREAKOUTS, out
assert not os.path.exists(os.path.join(d, "reel-build", "goldmine-run.json")), os.listdir(os.path.join(d, "reel-build"))
with open(ap, "w", encoding="utf-8") as f:
    json.dump(full, f)
out, code = run("plan", d)
assert next_line(out).startswith("NEXT: ASK the user to pick one level") and rjson(d, "goldmine-run.json")["manifest"], out

# 4c. transcribe with no media links: nothing to transcribe, and the reads use the captions.
d = make([("alpha_coach", "OOO001", 5.0, "x"), ("beta_coach", "PPP001", 4.0, "x")]); temps.append(d)
run("plan", d)
out, code = run("transcribe", d)
assert code is None and out.strip() == ("transcribe: nothing to transcribe. The 2 breakouts with no transcript "
                                        "have no media link, so the reads will use the captions."), out

# 4d. transcribe counts only the breakouts with no transcript: 2 of 3, then 1 (singular), then none.
d = make([("alpha_coach", "QQQ001", 5.0, "x"), ("alpha_coach", "QQQ002", 4.0, "x"),
          ("alpha_coach", "QQQ003", 3.0, "x")]); temps.append(d)
run("plan", d)
tdir = os.path.join(d, "source", "competitors", "transcripts")
os.makedirs(tdir)


def transcribed(*scs):
    with open(os.path.join(tdir, "alpha_coach.json"), "w", encoding="utf-8") as f:
        json.dump({"handle": "alpha_coach", "reels": [{"url": "https://www.instagram.com/reel/%s/" % sc,
                                                       "text": "Spoken words"} for sc in scs]}, f)
    return run("transcribe", d)[0].strip()


out = transcribed("QQQ001")
assert out == ("transcribe: nothing to transcribe. The 2 breakouts with no transcript have no media link, so the "
               "reads will use the captions."), out
out = transcribed("QQQ001", "QQQ002")
assert out == ("transcribe: nothing to transcribe. The 1 breakout with no transcript has no media link, so the "
               "reads will use the captions."), out
out = transcribed("QQQ001", "QQQ002", "QQQ003")
assert out == "transcribe: every breakout with media already has a transcript.", out

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
# curl finishes but saves no file, on a short path: "did not land", exit 5, never Windows or a long path.
cache = empty_cache()
gb.subprocess.run, gb.shutil.which = (lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, b"", b"")), (lambda n: "curl")
out, code = run("dashboard", d)
gb.subprocess.run, gb.shutil.which = real_run, real_which
assert code == 5 and out.startswith("ERROR: The dashboard download did not land") and "Windows" not in out, out
assert os.listdir(cache) == [], os.listdir(cache)
if os.name == "nt":                                              # exit 9 only for a plain path past 260
    far = os.path.join(cache, "x" * 240, "dashboard.tar.gz")     # nothing creates it
    gb.subprocess.run, gb.shutil.which = (lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, b"", b"")), (lambda n: "curl")
    for dest, want in ((far, 9), (gb.long_ok(far), 5)):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                gb.download("https://example.invalid/x.tar.gz", dest)
            code = None
        except SystemExit as e:
            code = e.code
        assert code == want, (len(dest), dest[:4], code, want)
    gb.subprocess.run, gb.shutil.which = real_run, real_which
# A cache past 260 characters on Windows just works: the fetch takes the \\?\ form, and the build finds
# its sibling module. Runs where Windows blocks long paths (a probe checks); the cache is sized so the
# download's own path runs past 260 (unpack-* 244, the download 261).
cache = empty_cache()
probe, real_long = os.path.join(cache, "p" * 250), False
if os.name == "nt":
    open(gb.long_ok(probe), "w").close()
    real_long = not os.path.isfile(probe)
    os.remove(gb.long_ok(probe))
real_long_ok = gb.long_ok


def long_cache():
    c = empty_cache()
    c = os.path.join(c, "c" * (227 - len(c)))                   # 228 characters
    os.makedirs(c)
    gb.dash_cache = lambda tag: c
    return c


def fake_curl(cmd, **k):                                         # curl itself writes long paths fine
    if cmd[0] != "curl":
        return real_run(cmd, **k)
    with tarfile.open(real_long_ok(cmd[cmd.index("-o") + 1]), "w:gz", format=tarfile.PAX_FORMAT,
                      pax_headers={"comment": gb.DASH_SHA}) as tf:
        for n, body in ((TOP, None), (TOP + "/goldmine_dashboard.py", b"import sibling\n" + FAKE),
                        (TOP + "/sibling.py", b""), (TOP + "/vendor", None), (TOP + "/vendor/x.js", b"x")):
            ti = tarfile.TarInfo(n)                              # folders as members, as a real tarball has
            if body is None:
                ti.type = tarfile.DIRTYPE
                tf.addfile(ti)
                continue
            ti.size = len(body)
            tf.addfile(ti, io.BytesIO(body))
    return subprocess.CompletedProcess(cmd, 0, b"", b"")


if real_long:
    cache = long_cache()
    gb.subprocess.run, gb.shutil.which = fake_curl, lambda name: "curl"
    out, code = run("dashboard", d)
    assert code is None and "Dashboard saved: " in out and "NOTE:" not in out, out
    assert os.path.isfile(real_long_ok(os.path.join(cache, TOP, "vendor", "x.js"))), os.listdir(cache)
    assert not glob.glob(os.path.join(cache, "unpack-*")), os.listdir(cache)
    gb.download = lambda url, dest: (_ for _ in ()).throw(AssertionError("re-downloaded"))
    out, code = run("dashboard", d)                              # the long cache is reused
    gb.download = real_download
    assert code is None and "Dashboard saved: " in out, out
    shutil.rmtree(real_long_ok(cache))                           # too deep for the plain cleanup at the end
    # Without the \\?\ form (a network home folder): exit 9, only then. A tarball deeper than the margin
    # fails its unpack instead: exit 7.
    cache = long_cache()
    gb.long_ok = lambda p: p
    out, code = run("dashboard", d)
    gb.long_ok = real_long_ok
    assert code == 9 and out.startswith("ERROR: The dashboard downloaded, but Windows could not open it"), out
    assert "maintainer" in out and "long paths" not in out and "NOTE: could not remove" in out, out
    shutil.rmtree(real_long_ok(cache))                           # the plain cleanup could not reach it, as its NOTE says
    gb.subprocess.run, gb.shutil.which = real_run, real_which
cache = empty_cache()                                            # a cleanup that cannot remove the folder says so
gb.shutil.rmtree, real_rmtree, gb.download = (lambda *a, **k: None), gb.shutil.rmtree, bad_gzip
out, code = run("dashboard", d)
gb.shutil.rmtree, gb.download = real_rmtree, real_download
assert code == 7 and "NOTE: could not remove the temporary folder" in out, out
if os.name == "nt":                                              # a \\?\ cache: the NOTE shows the normal path
    cache = long_cache()
    gb.shutil.rmtree, gb.download = (lambda *a, **k: None), bad_gzip
    out, code = run("dashboard", d)
    gb.shutil.rmtree, gb.download = real_rmtree, real_download
    assert code == 7 and ("temporary folder %s\\unpack-" % cache) in out and "\\\\?\\" not in out, out
    shutil.rmtree(real_long_ok(cache))
print("OK guards: no dashboard before check-reads, reads resume on a later day, symlink and hardlink "
      "members, assembler failure, corrupt tarball, curl timeout and OSError")

# 9. Zero breakouts after a Goldmine: the run file stays, with its passed reads and Proven Hooks.
ap = os.path.join(d, "analysis-data.json")
ad = json.load(open(ap))
ad["meta"]["generated_at"], ad["period_breakouts"]["reels"] = "2000-02-01T00:00:00Z", []
with open(ap, "w", encoding="utf-8") as f:
    json.dump(ad, f)
before = rjson(d, "goldmine-run.json")["reads"]
out, code = run("plan", d)
st = rjson(d, "goldmine-run.json")
assert code is None and out.strip() == gb.NO_BREAKOUTS, out
assert before["passed"] is True and st["reads"] == before and os.path.isfile(os.path.join(rb, before["proven_hooks"])), st
assert (st["manifest"], st["plan"]) == (None, {"breakouts": 0}), st
out, code = run("compute", d)
assert code == 0 and out.strip() == gb.NO_BREAKOUTS, out
print("OK fixes: zero first run keeps the 30-day window, zero after a Goldmine keeps its reads, transcribe "
      "with no media, long download path, a cleanup that cannot remove its folder, em dash CTA")

# 10. Long project folders. A short project or cache keeps its plain path, exactly as before.
s = make([("alpha_coach", "SSS001", 5.0, "x")]); temps.append(s)
assert len(os.path.abspath(s)) <= 150 and gb.Project(s).p == os.path.abspath(s), gb.Project(s).p
cache = empty_cache()
gb.download = lambda url, dest: tarball(dest)
assert gb.fetch_dashboard() == os.path.join(cache, TOP)
gb.download = real_download
SPECS = [("alpha_coach", "DDD001", 9.0, 'Comment "GUIDE" and I will send it'),   # section 5's fixture
         ("alpha_coach", "DDD002", 7.0, "Comment AMEN if you agree"),
         ("beta_coach", "EEE001", 8.0, "Three habits that changed my mornings"),
         ("beta_coach", "EEE002", 3.0, "Type “pure focus” if you believe it"),
         ("beta_coach", "EEE003", 2.6, "Comment the word starter below and I will send the checklist")]


def flow(proj, root):
    """Every step on the path the client gives (proj); the test's own file reads and writes go through root."""
    global d, names
    os.makedirs(os.path.join(root, "source", "competitors", "transcripts"))
    with open(os.path.join(root, "source", "competitors", "transcripts", "beta_coach.json"), "w", encoding="utf-8") as f:
        json.dump({"handle": "beta_coach", "reels": [{"url": "https://www.instagram.com/reel/EEE001/",
                                                      "text": "Spoken words"}]}, f)
    outs = []
    for step, kw in (("plan", {}), ("fetch", {"approved": "25"}), ("transcribe", {}), ("compute", {}), ("reads", {})):
        out, code = run(step, proj, **kw)
        assert code is None, (step, code, out)
        outs.append(out)
    d, names = root, rjson(root, "goldmine-run.json")["reads"]["expected"]
    good()                                                       # the judgement fields, filled
    cache = empty_cache()
    gb.subprocess.run, gb.shutil.which = fake_curl, lambda name: "curl"
    for step in ("check-reads", "dashboard"):
        out, code = run(step, proj)
        assert code is None, (step, code, out)
        outs.append(out)
    gb.subprocess.run, gb.shutil.which = real_run, real_which
    return outs, cache


if not real_long:
    print("SKIP long project: this system opens paths past 260 characters itself, so there is no limit to get past")
else:
    short = make(SPECS); temps.append(short)
    base = tempfile.mkdtemp(prefix="goldmine_test_")             # the plain cleanup at the end cannot reach inside
    proj = os.path.join(base, "p" * (229 - len(base)))           # 230 characters: the reel-build files pass 260
    src = make(SPECS); temps.append(src)
    shutil.copytree(src, real_long_ok(proj))
    try:
        s_outs, _ = flow(short, short)
        l_outs, l_cache = flow(proj, real_long_ok(proj))
        assert [o.replace(short, "<p>") for o in s_outs] == [o.replace(proj, "<p>") for o in l_outs], (s_outs, l_outs)
        assert not any("\\\\?\\" in o for o in l_outs), l_outs
        html = l_outs[-1].split("Dashboard saved: ")[1].splitlines()[0]
        assert html == os.path.join(proj, "visuals", "Content Goldmine Dashboard - %s.html" % gb.today()), html
        st = rjson(real_long_ok(proj), "goldmine-run.json")
        assert len(os.path.join(proj, "reel-build", st["reads"]["packet"])) > 260, st["reads"]["packet"]
        assert st["dashboard"]["html"] == html and st["reads"]["passed"] is True, st
        assert json.dumps("\\\\?\\")[1:-1] not in open(os.path.join(real_long_ok(proj), "reel-build", "goldmine-run.json"),
                                                       encoding="utf-8").read()
        man = rjson(real_long_ok(proj), st["manifest"])
        assert json.load(open(real_long_ok(html))) == {"comments_since": man["generated_at"][:10]}
        packet = rjson(real_long_ok(proj), st["reads"]["packet"])
        assert [r["transcript"] for r in packet["reels"] if r["shortcode"] == "EEE001"] == ["Spoken words"], packet
        files = lambda r: sorted(os.path.relpath(os.path.join(a, f), r) for a, _, fs in os.walk(r) for f in fs)
        assert files(short) == files(real_long_ok(proj)), (files(short), files(real_long_ok(proj)))  # no .tmp left
        assert not glob.glob(os.path.join(l_cache, "unpack-*")), os.listdir(l_cache)
        with open(os.path.join(l_cache, TOP, "goldmine_dashboard.py"), "w") as f:   # fails, naming its --project
            f.write('import sys\na = sys.argv\nprint("ERROR: project dir not found: " + a[a.index("--project") + 1])\n'
                    'sys.exit(1)\n')
        out, code = run("dashboard", proj)
        assert code == 8 and ("not found: %s." % proj) in out and "\\\\?\\" not in out, out
        out, code = run("plan", os.path.join(proj, "no-project-here"))
        assert code == 2 and ("in %s." % os.path.join(proj, "no-project-here")) in out and "\\\\?\\" not in out, out
    finally:
        shutil.rmtree(real_long_ok(base))
    print("OK long project: plan, fetch, transcribe, compute, reads, check-reads and dashboard at %d characters, "
          "same as short; normal paths shown" % len(proj))
if os.name == "nt":                     # a long network folder has no \\?\ form: one plain line, exit 10
    out, code = run("plan", "\\\\goldmine-no-such-host\\share\\" + "u" * 140)
    assert code == 10 and out.startswith("ERROR: This project is in a network folder") and len(out.splitlines()) == 1, out
print("OK short paths stay plain%s" % ("; a long network folder stops with exit 10" if os.name == "nt" else ""))

for t in temps:
    shutil.rmtree(t, ignore_errors=True)
print("OK runner steps: ask always (under and over budget), top-per-creator, zero breakouts, "
      "reads pre-fill, bait as lm_none, stale PAPS row and file, lm_types rule, proven hooks")
