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
    ("Comment\u2013GUIDE", (True, "GUIDE", "bare_caps")),               # en dash, no spaces
    ("Comment \u2013 guide below", (True, "guide", "bare_below")),      # en dash, bare_below
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

# 11. Comment read. Invented comments on three posts: one-word trigger words, 2-3 word comments, messy
#     whitespace, a missing text, and a whole post fetched before this pull (an older pull's file). The read
#     covers exactly what the dashboard's Comment Mining reads: this pull's files, 4+ words.
import datetime, importlib.util
from pathlib import Path
d = make([("alpha_coach", "TOP001", 6.0, "x"), ("alpha_coach", "TOP002", 5.0, "x"),
          ("beta_coach", "TOP003", 4.0, "x")]); temps.append(d)
run("plan", d)
rb, crd = os.path.join(d, "reel-build"), os.path.join(d, "reel-build", "comment-read")
since = rjson(d, rjson(d, "goldmine-run.json")["manifest"])["generated_at"][:10]
RUN = since.replace("-", "")
COMMENTS = {
    "TOP001": ("alpha_coach", gb.now_utc(), [
        (1001, "GUIDE"), (1002, "guide!!"), (1003, "love this"), (1004, "so good bro"),
        (1005, "This will never work for a small team"), (1006, "Is this a scam or real?"),
        (1007, "What app is this called?"), (1008, "I tried it and it crashed twice"),
        (1009, "I made my first sale using this"), (1010, "  this   is\nreally  good "),
        (1011, "\U0001F525\U0001F525\U0001F525"), (1012, "great video, thanks a lot"), (1013, "need this asap"),
        (1014, "Send me the guide please"), (1015, None), ("1016", "Which model did you use here")]),
    "TOP002": ("alpha_coach", gb.now_utc(), [
        (1017, "AMEN"), (1018, "yes"), (1019, "wow"), (1020, "this is gold"),
        (1021, "The worst advice I have heard all week"), (1022, "This is just copied from another creator"),
        (1023, "Mine keeps timing out after a minute"), (1024, "Saved me two hours on my invoices today"),
        (1025, "Link to the template please?"), (1026, "a b c"), (1027, "Is it free to use though"),
        (1028, "@someone check this out now"), (1029, "Does it work on a phone"), (1030, "Thanks!")]),
    "TOP003": ("beta_coach", "2000-01-02T00:00:00Z", [                 # an older pull's file
        (1030 + k, "An older comment that has plenty of words %d" % k) for k in range(1, 11)]),
}
TEXTS = [t for _, _, items in COMMENTS.values() for _, t in items if t and len(t.split()) >= 4]


def comments_file(sc, handle, at, items):
    os.makedirs(os.path.join(d, "source", "comments"), exist_ok=True)
    with open(os.path.join(d, "source", "comments", sc + ".json"), "w", encoding="utf-8") as f:
        json.dump({"success": True, "data": {"comments": [
            {"comment": {"id": i, "text": t, "author": {"username": "fan_%s" % i}}} for i, t in items]},
            "_fetch": {"shortcode": sc, "handle": handle, "url": "https://www.instagram.com/reel/%s/" % sc,
                       "fetched_at": at, "pages": 1, "completed": True}}, f)


for sc, (h, at, items) in COMMENTS.items():
    comments_file(sc, h, at, items)
wjson(d, "Topic Map - 3 - fixture.json", {"schema": "goldmine-topic-map/1", "topics": [
    {"id": "t01", "name": "Invoices", "theme": "growth", "summary": "x"},
    {"id": "t02", "name": "Client onboarding", "theme": "growth", "summary": "x"}],
    "reels": {"TOP001": {"topic": "t01", "angle": "One tool that cuts invoice time"},
              "TOP002": {"topic": "t02", "angle": None}}})
st = rjson(d, "goldmine-run.json")
st["reads"] = {"passed": True, "topicmap": "Topic Map - 3 - fixture.json"}
wjson(d, "goldmine-run.json", st)
out, code = run("plan", d)                                        # a resumed run: plan never sends it back to fetch
assert code is None and next_line(out).startswith("NEXT: this run is already past the comments ask"), out
WANT ={"1005", "1006", "1007", "1008", "1009", "1010", "1012", "1014", "1016",       # from the rules, by hand
        "1021", "1022", "1023", "1024", "1025", "1027", "1028", "1029"}
got = {r["id"]: r for r in gb.readable_comments(gb.Project(d), since)}
assert set(got) == WANT, sorted(set(got) ^ WANT)
assert got["1010"]["text"] == "this is really good" and got["1010"]["post_topic"] == "One tool that cuts invoice time"
assert got["1021"] == {"id": "1021", "post": "TOP002", "handle": "alpha_coach", "post_topic": "Client onboarding",
                       "text": "The worst advice I have heard all week"}, got["1021"]
# The same pick, cross-checked against the dashboard assembler itself when one is on this computer: the
# GOLDMINE_DASHBOARD_PY file, else the plugin's own pinned download.
DASH_PY = os.environ.get("GOLDMINE_DASHBOARD_PY") or os.path.join(
    os.path.expanduser("~"), ".cache", "shortform-superengine", "goldmine-dashboard", gb.DASH_TAG, TOP, "goldmine_dashboard.py")
dm = None
if os.path.isfile(DASH_PY):
    spec = importlib.util.spec_from_file_location("goldmine_dashboard_parity", DASH_PY)
    dm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dm)


def mining():
    dm.PULL_COMMENTS_SINCE = since
    with contextlib.redirect_stdout(io.StringIO()):
        return dm.build_mining(Path(rb), Path(d), {"reels": []}, None)


if dm:
    assert {c["id"] for c in mining()["comments"]} == WANT
    print("OK comment window parity with the dashboard assembler's build_mining (%s)"
          % os.path.basename(os.path.dirname(DASH_PY)))
else:
    print("SKIP build_mining parity: no dashboard assembler here (set GOLDMINE_DASHBOARD_PY to one)")

# comment-read: an id tagged in an older batch is skipped; packets of PACKET_ROWS; empty batch files
os.makedirs(crd)
wjson(d, "comment-read/batch-20000102-01.read.json",
      {"schema": "goldmine-comment-read/1", "batch": "20000102-01", "n": 1, "tags": {"1005": []}})
gb.PACKET_ROWS = 10
out, code = run("comment-read", d)
gb.PACKET_ROWS = 130
assert code is None and "17 comments of four or more words" in out and "earlier pull: 1." in out, out
assert "Packets written: 2" in out and next_line(out).startswith(
    "NEXT: fill these 2 batch files in reel-build/comment-read/, each from its own packet per references/comment-read.md: "
    "batch-%s-01.read.json, batch-%s-02.read.json. Then run check-comments." % (RUN, RUN)), out
p1, p2 = (rjson(d, "comment-read/packet-%s-%s.json" % (RUN, k)) for k in ("01", "02"))
assert (p1["n"], p2["n"], p1["write_to"]) == (10, 6, "batch-%s-01.read.json" % RUN), (p1["n"], p2["n"])
assert {r["id"] for r in p1["rows"] + p2["rows"]} == WANT - {"1005"}
assert all(set(r) == {"id", "post", "handle", "post_topic", "text"} for r in p1["rows"] + p2["rows"])
for k, p in (("01", p1), ("02", p2)):
    assert rjson(d, "comment-read/batch-%s-%s.read.json" % (RUN, k)) == {
        "schema": "goldmine-comment-read/1", "batch": "%s-%s" % (RUN, k), "n": p["n"], "tags": {}}
cr = rjson(d, "goldmine-run.json")["comment_read"]
assert cr == {"comments_since": since, "packets": ["packet-%s-01.json" % RUN, "packet-%s-02.json" % RUN],
              "passed": False, "independent": None}, cr
out, code = run("comment-read", d)                                # a rerun writes nothing new
assert "Packets written" not in out and "this pull's packets: 16." in out, out
assert len(glob.glob(os.path.join(crd, "packet-*.json"))) == 2
h, at, items = COMMENTS["TOP002"]                                 # a comment fetched later: only it is new
comments_file("TOP002", h, at, items + [(1041, "Followed along and it finally worked")])
out, code = run("comment-read", d)
assert [r["id"] for r in rjson(d, "comment-read/packet-%s-03.json" % RUN)["rows"]] == ["1041"], out
# a resumed read names only the batch files still to fill; a finished one is never handed out again, and this pull's
# own batch files never count as an earlier pull's
b1 = "comment-read/batch-%s-01.read.json" % RUN
wjson(d, b1, dict(rjson(d, b1), tags={r["id"]: [] for r in p1["rows"]}))
out, code = run("comment-read", d)
assert code is None and "Already tagged in an earlier pull: 1. Already in this pull's packets: 17." in out, out
assert next_line(out) == ("NEXT: fill these 2 batch files in reel-build/comment-read/, each from its own packet per "
                          "references/comment-read.md: batch-%s-02.read.json, batch-%s-03.read.json. The other 1 is "
                          "finished: never tag it again. Then run check-comments." % (RUN, RUN)), out

# check-comments: the batch files are validated by id, and never echo comment text
TAGS = {"1006": ["skeptic"], "1007": ["tool_ask"], "1008": ["stuck"], "1009": ["win"], "1010": [], "1012": [],
        "1014": [], "1016": ["tool_ask"], "1021": ["counterargument"], "1022": ["counterargument", "skeptic"],
        "1023": ["stuck"], "1024": ["win"], "1025": ["tool_ask"], "1027": ["tool_ask"], "1028": ["win"],
        "1029": [], "1041": []}


def fill(over=None, drop=None, extra=None):
    for k in ("01", "02", "03"):
        name = "comment-read/batch-%s-%s.read.json" % (RUN, k)
        doc = rjson(d, name)
        doc["tags"] = {r["id"]: list(TAGS[r["id"]])
                       for r in rjson(d, "comment-read/packet-%s-%s.json" % (RUN, k))["rows"] if r["id"] != drop}
        doc["tags"].update({i: v for i, v in (over or {}).items() if i in doc["tags"]})
        if extra and k == "01":
            doc["tags"][extra] = []
        wjson(d, name, doc)


def merged():
    tags = {}
    for f in glob.glob(os.path.join(crd, "batch-%s-*.read.json" % RUN)):
        tags.update(json.load(open(f, encoding="utf-8"))["tags"])
    return tags


def settag(i, v):
    """Set one comment's tag value in whichever batch file holds it."""
    for f in glob.glob(os.path.join(crd, "batch-%s-*.read.json" % RUN)):
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        if i in doc["tags"]:
            doc["tags"][i] = v
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
            return f


def failed(want, **kw):
    out, code = run("check-comments", d, **kw)
    assert code == 1 and want in out and not any(t in out for t in TEXTS), (want, out)


out, code = run("check-comments", d)
assert code == 1 and "batch-%s-02.read.json: 6 comments with no entry" % RUN in out, out
fill(drop="1007"); failed("1 comment with no entry (use [] for no category): 1007")
fill(over={"1009": ["praise"]}); failed("comment 1009 has a category outside the five")
fill(over={"1012": None}); failed("comment 1012 needs a list (use [] for no category, never null)")
fill(extra="9999"); failed("ids not in its packet: 9999")
assert rjson(d, "goldmine-run.json")["comment_read"]["passed"] is False
st = rjson(d, "goldmine-run.json")                                # a read from another pull is not this pull's
st["comment_read"]["comments_since"] = "2000-01-02"; wjson(d, "goldmine-run.json", st)
out, code = run("check-comments", d)
assert code == 2 and "this pull has no comment read yet" in out, out
st["comment_read"]["comments_since"] = since; wjson(d, "goldmine-run.json", st)
fill()
out, code = run("check-comments", d)
assert code is None and "check-comments: PASS (17 comments in 3 batch files" in out, out
smp = rjson(d, "comment-read/check-sample.json")
assert sorted((r["id"], r["cat"]) for r in smp["rows"]) == sorted([
    ("1021", "counterargument"), ("1022", "counterargument"), ("1006", "skeptic"), ("1022", "skeptic"),
    ("1007", "tool_ask"), ("1016", "tool_ask"), ("1025", "tool_ask"), ("1027", "tool_ask"), ("1008", "stuck"),
    ("1023", "stuck"), ("1009", "win"), ("1024", "win"), ("1028", "win")]), smp
assert smp["comments_since"] == since and all(set(r) == {"id", "cat", "text", "post_topic"} for r in smp["rows"])
gb.SAMPLE_PER_CAT = 2                                             # the cap per category, the same draw twice
run("check-comments", d); a = rjson(d, "comment-read/check-sample.json")["rows"]
run("check-comments", d); b = rjson(d, "comment-read/check-sample.json")["rows"]
gb.SAMPLE_PER_CAT = 30
assert a == b and [sum(1 for r in a if r["cat"] == c) for c in gb.CR_CATS] == [2, 2, 2, 2, 2], a
run("check-comments", d)

# --verdicts: must cover the sample exactly; precision, removed, the strip keeps a comment's other categories
WRONG = {("1022", "skeptic"), ("1027", "tool_ask"), ("1028", "win")}
V = [{"id": int(r["id"]) if r["id"] == "1027" else r["id"], "cat": r["cat"],  # 1027: an id written as a number
      "verdict": "WRONG" if (r["id"], r["cat"]) in WRONG else "CORRECT"}
     for r in rjson(d, "comment-read/check-sample.json")["rows"]]
vf = os.path.join(crd, "verdicts.json")


def verdicts(v, **kw):
    with open(vf, "w", encoding="utf-8") as f:
        json.dump(v, f)
    return run("check-comments", d, verdicts=vf, **kw)


for bad, why in ((V[1:], "Rows with no verdict: 1."),
                 (V + [{"id": "1010", "cat": "win", "verdict": "CORRECT"}], "Verdicts not in the sample: 1."),
                 (V + V[:1], "judged more than once"), ([dict(V[0], verdict="MAYBE")] + V[1:], "CORRECT or WRONG")):
    out, code = verdicts(bad)
    assert code == 1 and why in out, (why, out)
assert not os.path.exists(os.path.join(crd, "check-result.json"))
wjson(d, "comment-read/check-sample.json", dict(smp, comments_since="2000-01-02"))  # another pull's sample
out, code = verdicts(V)
assert code == 2 and "no check sample" in out, out
wjson(d, "comment-read/check-sample.json", smp)
out, code = verdicts(V)
assert code is None and "3 wrong tags removed" in out, out
res = rjson(d, "comment-read/check-result.json")
assert res["precision"] == {"counterargument": [2, 2], "skeptic": [1, 2], "tool_ask": [3, 4], "stuck": [2, 2],
                            "win": [2, 3]}, res
assert res["removed"] == [["1022", "skeptic"], ["1027", "tool_ask"], ["1028", "win"]], res
assert (res["schema"], res["checked_at"], res["sample"]) == (
    "goldmine-comment-check/1", datetime.date.today().isoformat(), 13), res
assert res["independent"] is False and res["method"].startswith("Claude re-checked"), res
assert "fewer than 10 tagged comments to check" in res["note"] and "85%" not in res["note"], res["note"]
assert "re-read" not in res["note"] and "\u2014" not in res["note"] + res["method"], res["note"]
tags = merged()
assert (tags["1022"], tags["1027"], tags["1028"], tags["1007"]) == (["counterargument"], [], [], ["tool_ask"]), tags
cr = rjson(d, "goldmine-run.json")["comment_read"]
assert (cr["passed"], cr["independent"], cr["below_bar"]) == (True, False, []), cr
assert not os.path.exists(os.path.join(crd, "check-sample.json"))  # graded once: a regrade needs a fresh sample
out, code = verdicts(V)
assert code == 2 and "no check sample" in out, out
out, code = run("check-comments", d)                              # the fresh sample is drawn from the stripped tags
assert code is None and sorted((r["id"], r["cat"]) for r in rjson(d, "comment-read/check-sample.json")["rows"]) == sorted(
    (r["id"], r["cat"]) for r in smp["rows"] if (r["id"], r["cat"]) not in WRONG), out
out, code, cache = dash(proj=d)                                   # the check is tied to the page's own pull
assert code is None and "then run record-publish --url <the link>" in next_line(out), out
html = out.split("Dashboard saved: ")[1].splitlines()[0]
assert res["comments_since"] == json.load(open(html))["comments_since"] == since, res
with open(os.path.join(cache, TOP, "goldmine_dashboard.py"), "w") as f:  # iterates every tag list, as build_mining does
    f.write('import glob, json, os, sys\na = sys.argv\n'
            'for f in glob.glob(os.path.join(a[a.index("--project") + 1], "reel-build", "comment-read", "batch-*.read.json")):\n'
            '    [x for v in json.load(open(f, encoding="utf-8"))["tags"].values() for x in v]\n'
            'open(a[a.index("--out") + 1], "w").write("{}")\n')
nb = settag("1010", None)                                         # a null before the read passed: no category
others = {f: open(f, "rb").read() for f in glob.glob(os.path.join(crd, "batch-*.read.json")) if f != nb}
out, code = run("dashboard", d)
assert code is None and "1 comment with no category list (null) treated as no category." in out, out
assert merged()["1010"] == [] and all(open(f, "rb").read() == b for f, b in others.items()), merged()
# --independent from the command line, before --verdicts: a bare flag never swallows the next option
fill(); run("check-comments", d)                                  # the original tags again: V's sample again
p =subprocess.run([sys.executable, gb.__file__, "check-comments", d, "--independent", "--verdicts", vf],
                   capture_output=True, text=True, timeout=120)
res = rjson(d, "comment-read/check-result.json")
assert p.returncode == 0 and res["independent"] is True and res["method"].startswith("A separate reader"), (p, res)
assert rjson(d, "goldmine-run.json")["comment_read"]["independent"] is True
fill(); run("check-comments", d)
gb.SMALL_SAMPLE = 2                                              # the 85% bar, once enough were sampled
out, code = verdicts(V)                                          # every tag of each one was sampled: no re-read
gb.SMALL_SAMPLE = 10
res, cr = rjson(d, "comment-read/check-result.json"), rjson(d, "goldmine-run.json")["comment_read"]
assert cr["below_bar"] == cr["fully_checked"] == ["skeptic", "tool_ask", "win"] and cr["passed"] is True, cr
assert ("Skeptics and BS calls, Tool and resource asks, Wins came in under 85% correct, but they were fully checked "
        "(every tagged comment graded), so their wrong tags are all removed.") in res["note"], res["note"]
assert "first pass" not in res["note"] and next_line(out).startswith("NEXT: the comment read passed"), (res["note"], out)
if dm:                                                            # the assembler reads the result and the tags
    m = mining()
    assert m["check"]["comments_since"] == since and m["check"]["precision"] == res["precision"], m["check"]
    assert [m["cats"][c] for c in gb.CR_CATS] == [2, 1, 3, 2, 2], m["cats"]
fill()                                                            # 3 per category: tool_ask (4 tagged) is part-sampled
gb.SAMPLE_PER_CAT = 3
run("check-comments", d)
gb.SAMPLE_PER_CAT = 30
TA = [r["id"] for r in rjson(d, "comment-read/check-sample.json")["rows"] if r["cat"] == "tool_ask"][0]
VP = [{"id": r["id"], "cat": r["cat"], "verdict": "WRONG" if (r["id"], r["cat"]) in {
    ("1022", "skeptic"), ("1028", "win"), (TA, "tool_ask")} else "CORRECT"}
    for r in rjson(d, "comment-read/check-sample.json")["rows"]]
gb.SMALL_SAMPLE = 2
out, code = verdicts(VP)
gb.SMALL_SAMPLE = 10
res, cr = rjson(d, "comment-read/check-result.json"), rjson(d, "goldmine-run.json")["comment_read"]
assert (cr["below_bar"], cr["fully_checked"], cr["passed"]) == (["skeptic", "tool_ask", "win"], ["skeptic", "win"], False), cr
assert ("Tool and resource asks came in under 85% correct, so read it as a first pass. Skeptics and BS calls, Wins came "
        "in under 85% correct, but they were fully checked") in res["note"] and "first_check" not in res, res
assert "--reread <category> for tool_ask." in out, out
out, code = run("comment-read", d)                                # a resumed run lands on the re-read, never past it
assert code is None and next_line(out).startswith("NEXT: under the 85% bar and not re-read yet: tool_ask."), out
out, code = run("reply-candidates", d)
assert code == 2 and "comment read for this pull has not passed" in out, out
fill(over={"1022": ["counterargument"], "1027": [], "1028": []})  # the tags as V's strip left them, for the re-read below

# --reread / --apply-reread: keep or remove one category, the others untouched; one re-read per category
out, code = run("check-comments", d, reread="praise")
assert code == 2 and "--reread needs one of" in out, out
settag("1016", ["tool_ask", "stuck"])                            # two categories: the re-read removes only its own
out, code = run("check-comments", d, reread="tool_ask")
rrn = "comment-read/reread-%s-tool_ask.json" % RUN
rr = rjson(d, rrn)
assert code is None and [r["id"] for r in rr["rows"]] == ["1007", "1016", "1025"] and rr["keep"] is None, rr
assert set(rr["rows"][0]) == {"id", "text", "post_topic"}
out, code = run("check-comments", d, apply_reread="tool_ask")
assert code == 2 and "is not filled" in out, out
rr["keep"] = ["1007", "1025", "4242"]; wjson(d, rrn, rr)
out, code = run("check-comments", d, apply_reread="tool_ask")
assert code == 2 and "4242" in out and merged()["1016"] == ["tool_ask", "stuck"], out
rr["keep"] = ["1007", 1025]; wjson(d, rrn, rr)                    # an id written as a number still counts
out, code = run("check-comments", d, apply_reread="tool_ask")
assert code is None and "kept on 2 of 3 comments, removed from 1" in out, out
tags = merged()
assert (tags["1016"], tags["1007"], tags["1025"], tags["1022"]) == (["stuck"], ["tool_ask"], ["tool_ask"], ["counterargument"])
cr = rjson(d, "goldmine-run.json")["comment_read"]
assert cr["reread"] == {"tool_ask": "applied"} and cr["passed"] is False, cr
assert not os.path.exists(os.path.join(crd, "check-sample.json"))
out, code = verdicts(V)                                           # the old sample is gone: grade a fresh one
assert code == 2 and "no check sample" in out, out
for kw in ({"reread": "tool_ask"}, {"apply_reread": "tool_ask"}):
    out, code = run("check-comments", d, **kw)
    assert code == 2 and "already re-read once" in out, (kw, out)
out, code = run("check-comments", d)
V2 = [{"id": r["id"], "cat": r["cat"], "verdict": "CORRECT"} for r in rjson(d, "comment-read/check-sample.json")["rows"]]
out, code = verdicts(V2, independent=True)
res = rjson(d, "comment-read/check-result.json")
assert code is None and "Tool and resource asks were re-read once" in res["note"], res["note"]
assert res["independent"] is True and res["removed"] == [] and res["precision"]["tool_ask"] == [2, 2], res
# the regrade never hides the check that sent the category to its re-read: kept beside it, and said in the note
assert res["first_check"] == {"precision": {"counterargument": [2, 2], "skeptic": [1, 2], "tool_ask": [2, 3],
                                            "stuck": [2, 2], "win": [2, 3]}, "removed_count": 3}, res
assert ("Before the re-read, the first check found Tool and resource asks 2 of 3 correct and removed 3 wrong "
        "tags.") in res["note"], res["note"]
assert rjson(d, "goldmine-run.json")["comment_read"]["passed"] is True
out, code = run("comment-read", d)
assert next_line(out).startswith("NEXT: the comment read for this pull has passed. Offer reply drafts"), out
# After its one re-read a category still under the bar no longer holds the read back: it passes, and the note says
# so. The verdicts file is saved as the checker returned it, inside one ```json fence (CRLF here); prose around a
# fence, or a fenced object that is not a list, is still refused.
gb.SAMPLE_PER_CAT = 1                                             # tool_ask part-sampled, so the bar still applies
out, code = run("check-comments", d)
gb.SAMPLE_PER_CAT = 30
VR = [{"id": r["id"], "cat": r["cat"], "verdict": "WRONG" if r["cat"] == "tool_ask" else "CORRECT"}
      for r in rjson(d, "comment-read/check-sample.json")["rows"]]


def fenced(text):
    with open(vf, "w", encoding="utf-8") as f:
        f.write(text)
    return run("check-comments", d, verdicts=vf)


out, code = fenced("Here they are:\n```json\n%s\n```\n" % json.dumps(VR))
assert code == 2 and "is missing or not valid JSON" in out, out
out, code = fenced("```json\n%s\n```\n" % json.dumps({"rows": VR}))
assert code == 1 and "must be a JSON list" in out, out
gb.SMALL_SAMPLE = 1
out, code = fenced("```json\n%s\n```\n" % json.dumps(VR, indent=1))
gb.SMALL_SAMPLE = 10
cr, res = rjson(d, "goldmine-run.json")["comment_read"], rjson(d, "comment-read/check-result.json")
assert code is None and cr["below_bar"] == ["tool_ask"] and cr["passed"] is True, (out, cr)
assert "Tool and resource asks came in under 85% correct even after a re-read" in res["note"], res["note"]
assert next_line(out).startswith("NEXT: the comment read passed. Offer reply drafts"), out

# Zero readable comments: passed, with a note, nothing written. Nothing tagged: a check with nothing to show.
z = make([("alpha_coach", "ZZZ001", 5.0, "x")]); temps.append(z)
run("plan", z)
st = rjson(z, "goldmine-run.json")                                # an older pull's read: the new pull starts over
st["comment_read"] = {"comments_since": "2000-01-02", "packets": ["packet-20000102-01.json"], "passed": False,
                      "independent": True, "reread": {"win": "applied"}}
wjson(z, "goldmine-run.json", st)
out, code = run("comment-read", z)
cr = rjson(z, "goldmine-run.json")["comment_read"]
assert code is None and "NEXT: nothing to read." in out and (cr["passed"], cr["packets"]) == (True, []), (out, cr)
assert cr["independent"] is None and "reread" not in cr and cr["comments_since"] != "2000-01-02", cr
assert cr["note"].startswith("No comments of four or more words") and not glob.glob(os.path.join(z, "reel-build", "comment-read", "*"))
out, code = run("check-comments", z)
assert code is None and "nothing to check" in out, out
d = z
comments_file("ZZZ001", "alpha_coach", gb.now_utc(), [(2001, "Nice one, saving this for later")])
run("comment-read", z)
zb = "comment-read/batch-%s-01.read.json" % rjson(z, "goldmine-run.json")["comment_read"]["comments_since"].replace("-", "")
wjson(z, zb, dict(rjson(z, zb), tags={"2001": []}))
out, code = run("check-comments", z)
res = rjson(z, "comment-read/check-result.json")
assert code is None and (res["precision"], res["sample"], res["removed"]) == ({}, 0, []), (out, res)
assert res["note"] == "No comment carried one of these categories, so there was nothing to check.", res
# The bar's edges: 17 of 20 (exactly 85%) is not under it; 10 sampled is not a small sample, 9 is
EDGE = [{"id": "%s%d" % (c, k), "cat": c, "verdict": "CORRECT" if k < ok else "WRONG"}
        for c, n, ok in (("counterargument", 20, 17), ("skeptic", 10, 8), ("tool_ask", 9, 5)) for k in range(n)]
wjson(z, "comment-read/check-sample.json", {"comments_since": rjson(z, "goldmine-run.json")["comment_read"][
    "comments_since"], "rows": EDGE})
out, code = verdicts(EDGE)
res = rjson(z, "comment-read/check-result.json")
assert code is None and rjson(z, "goldmine-run.json")["comment_read"]["below_bar"] == ["skeptic"], (out, res)
assert res["note"] == ("Skeptics and BS calls came in under 85% correct, so read it as a first pass. Tool and "
                       "resource asks had fewer than 10 tagged comments to check: a small sample. The 9 tags judged "
                       "wrong in the sample were removed."), res["note"]
# A second pull the same UTC day (a re-analyze) shares the day's run id. Its re-read lists its own comments, never the
# first pull's list left on disk, and that old list cannot be applied in its place.
d = make([("alpha_coach", "SDY001", 5.0, "x")]); temps.append(d)
run("plan", d)


def sd_pull(ids):
    comments_file("SDY001", "alpha_coach", gb.now_utc(), [(i, "a comment with enough words %d" % i) for i in ids])
    run("comment-read", d)
    for f in glob.glob(os.path.join(d, "reel-build", "comment-read", "batch-*.read.json")):
        doc = json.load(open(f, encoding="utf-8"))
        pk = json.load(open(f.replace("batch-", "packet-").replace(".read.json", ".json"), encoding="utf-8"))
        doc["tags"].update({r["id"]: ["win"] for r in pk["rows"] if r["id"] not in doc["tags"]})
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
    run("check-comments", d)
    rows = rjson(d, "comment-read/check-sample.json")["rows"]
    verdicts([dict(id=r["id"], cat=r["cat"], verdict="WRONG" if k == 0 else "CORRECT") for k, r in enumerate(rows)])


gb.SAMPLE_PER_CAT, gb.SMALL_SAMPLE = 2, 2                         # 2 of 4+ sampled, half wrong: a re-read is due
sd_pull(range(1, 5))
out, code = run("check-comments", d, reread="win")
sdr = "comment-read/reread-%s-win.json" % rjson(d, "goldmine-run.json")["comment_read"]["comments_since"].replace("-", "")
wjson(d, sdr, dict(rjson(d, sdr), keep=[r["id"] for r in rjson(d, sdr)["rows"]]))
out, code = run("check-comments", d, apply_reread="win")
assert code is None and "Re-read applied" in out, out
with open(os.path.join(d, "analysis-data.json"), encoding="utf-8") as f:
    ad = json.load(f)
ad["meta"]["generated_at"] = "2000-02-01T00:00:00Z"
with open(os.path.join(d, "analysis-data.json"), "w", encoding="utf-8") as f:
    json.dump(ad, f)
run("plan", d)                                                    # pull 2, same day: a fresh run state
sd_pull(range(1, 9))
out, code = run("check-comments", d, apply_reread="win")
assert code == 2 and "no re-read list for win" in out, out
out, code = run("check-comments", d, reread="win")
ids = [r["id"] for r in rjson(d, sdr)["rows"]]
assert code is None and out.startswith("Re-read list: ") and {"5", "6", "7", "8"} & set(ids), (out, ids)
sdt = {i: v for f in glob.glob(os.path.join(d, "reel-build", "comment-read", "batch-*.read.json"))
       for i, v in json.load(open(f, encoding="utf-8"))["tags"].items()}
assert ids == sorted(i for i, v in sdt.items() if "win" in v) and rjson(d, sdr)["keep"] is None, ids
assert rjson(d, "goldmine-run.json")["comment_read"]["reread"] == {"win": "pending"}
gb.SAMPLE_PER_CAT, gb.SMALL_SAMPLE = 30, 10
print("OK comment read: 4+ word window, older pull skipped, packets and empty batch files, rerun skips tagged and "
      "queued ids, missing / unknown / null / extra ids rejected without comment text, fixed-seed sample, verdicts "
      "cover the sample, precision and removed, strip keeps other categories, comments_since matches the extras, "
      "independent flag, 85% bar and its edges, one re-read per category, a graded sample is spent, another pull's "
      "read and sample refused, a new pull starts over, null tags no longer stop the dashboard, zero comments, "
      "nothing tagged")

# 12. Reply drafts. An invented client who goes by "Dana Reyes" in two call transcripts (one with Fathom lines,
#     one with plain lines) beside another speaker, plus one written answers file. Questions (the free label at
#     p >= .5), tool asks and stuck points become candidates; the drafts are checked word for word.
OWNER, OTHER = "Dana Reyes", "Sam Ortiz"
CALL_A = [(OTHER, "How often do you post each week, and does it matter?"),
          (OWNER, "I post three times a week and never more than that."),
          (OWNER, "Consistency beats volume every single time."),
          (OTHER, "I always write the hook first and the script after."),
          (OWNER, "Write the script first, then cut the hook from the best line.")]
CALL_B = [(OWNER, "For captions I just use the free tool built into the editor."),
          (OTHER, "Batching saved my whole week."),
          (OWNER, "If you fall behind, batch two weeks at once on a Sunday.")]
LONG = ("Here is the long version of how I plan a month of posts, step by step, so nothing slips: I pick four themes "
        "on the first Sunday, I write ten hooks for each theme, I film the strongest five in one sitting, I edit them "
        "the next morning, I schedule them across the month, and I keep a short list of spare ideas for busy weeks.")
FAQ = ["Batching works when you plan the topics first.", "Pick one day, film everything, and edit the next day.", LONG]
assert len(LONG) > 300
ws = tempfile.mkdtemp(prefix="goldmine_ws_"); temps.append(ws)
for rel, lines, fathom in (("sales/call-a.md", CALL_A, True), ("group/call-b.txt", CALL_B, False)):
    os.makedirs(os.path.dirname(os.path.join(ws, "voc", "transcripts", rel)), exist_ok=True)
    with open(os.path.join(ws, "voc", "transcripts", rel), "w", encoding="utf-8") as f:
        f.write("# Call notes\n\n" + "\n".join(
            ("[00:%02d](https://calls.example/x#t=%d) %s: %s" % (k, k, s, t)) if fathom else "%s: %s" % (s, t)
            for k, (s, t) in enumerate(lines)) + "\n")


def reply_project(posts, tags):
    """posts: {shortcode: (handle, [(id, text, question p, likes)])}. A pull whose comment read has passed."""
    global d
    d = make([(h, sc, 6.0 - k, "x") for k, (sc, (h, _)) in enumerate(posts.items())]); temps.append(d)
    run("plan", d)
    os.makedirs(os.path.join(d, "reel-build", "comment-read"))
    for sc, (h, items) in posts.items():
        reply_comments(sc, h, items)
    s = rjson(d, rjson(d, "goldmine-run.json")["manifest"])["generated_at"][:10]
    wjson(d, "comment-read/batch-%s-01.read.json" % s.replace("-", ""),
          {"schema": "goldmine-comment-read/1", "batch": s.replace("-", "") + "-01", "n": len(tags), "tags": tags})
    return s


def reply_comments(sc, h, items):
    os.makedirs(os.path.join(d, "source", "comments"), exist_ok=True)
    with open(os.path.join(d, "source", "comments", sc + ".json"), "w", encoding="utf-8") as f:
        json.dump({"success": True, "data": {"comments": [
            {"comment": {"id": i, "text": t, "author": {"username": "viewer_%s" % i},
                         "published_at": "2000-01-20T10:00:00Z", "engagement": {"likes": lk}},
             "computed": {"labels": {"question": {"p": p}}}} for i, t, p, lk in items]},
            "_fetch": {"shortcode": sc, "handle": h, "url": "https://www.instagram.com/reel/%s/" % sc,
                       "fetched_at": gb.now_utc(), "pages": 1, "completed": True}}, f)


def pass_read(s):
    st = rjson(d, "goldmine-run.json")
    st["comment_read"] = {"comments_since": s, "packets": [], "passed": True}
    wjson(d, "goldmine-run.json", st)


RC = {"RPL001": ("alpha_coach", [
          (3001, "How often should I post each week?", 0.9, 4), (3002, "What app do you use for the captions", 0.2, 0),
          (3003, "I tried batching and still fall behind every week", 0.1, 2),
          (3004, "This changed how I plan my whole month", 0.0, 1), (3005, "Total scam do not buy this", 0.1, 0),
          (3006, "Is this good for a brand new account?", 0.4, 0), (3007, "great stuff", 0.9, 0)]),
      "RPL002": ("beta_coach", [(3008, "Do you write hooks before the script or after", 0.7, 3),
                                (3009, "Where do you find your topic ideas each week", 0.8, 0)])}
RTAGS = {"3002": ["tool_ask"], "3003": ["stuck"], "3004": ["win"], "3005": ["skeptic"], "3006": []}
since = reply_project(RC, RTAGS)
SECRETS = [t for _, items in RC.values() for _, t, _, _ in items] + [t for _, t in CALL_A + CALL_B] + FAQ
ans = os.path.join(d, "reel-build", "reply-answers")
os.makedirs(ans)
with open(os.path.join(ans, "faq.md"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(FAQ) + "\n")
real_today = gb.today
gb.today = lambda: "01.05.00"


def rc(**kw):
    out, code = run("reply-candidates", d, **kw)
    assert not any(t in out for t in SECRETS), out
    return out, code


out, code = rc(owner=OWNER, workspace=ws)                         # the comment read has not passed: refused
assert code == 2 and "comment read for this pull has not passed" in out, out
pass_read(since)
wjson(d, "comment-read/Reply Candidates - 01.02.00.json", [{"n": 40, "comment_id": "3009"}])  # an earlier run
NAMES = 'Speaker names found: Dana Reyes (5 lines), Sam Ortiz (3 lines). Ask the client in plain words "Which of these is you?"'
out, code = rc(workspace=ws)                                      # transcripts, no owner label: ask once
assert code == 2 and "2 call transcript files found" in out and "no owner label is set" in out and NAMES in out, out
assert rjson(d, "goldmine-run.json")["reply_drafts"] == {"accepted": True}  # the yes is kept: a stop never re-asks it
out, code = rc(owner="Nobody Here", workspace=ws)                 # a label no line carries: stop, name it
assert code == 2 and 'no line in the 2 call transcript files scanned is spoken by "Nobody Here"' in out and NAMES in out, out
assert not glob.glob(os.path.join(d, "reel-build", "comment-read", "Reply * - 01.05.00.json"))
# a speaker name is a Fathom label, or a plain label shaped like a name (capitalised words of letters, no digits) on 2+
# lines: prose before a colon is never listed, however often it repeats
nws = tempfile.mkdtemp(prefix="goldmine_ws_"); temps.append(nws)
os.makedirs(os.path.join(nws, "voc", "transcripts", "c"))
with open(os.path.join(nws, "voc", "transcripts", "c", "n.md"), "w", encoding="utf-8") as f:
    f.write("\n".join([
        "Here's the thing: you have to post every day", "Here's the thing: nobody tells you the hard part",
        "Priya earns 40k: she told me that", "Priya earns 40k: twice now", "Meeting purpose: plan the month",
        "Meeting purpose: plan it again", "Q3 Review: the numbers", "Q3 Review: more numbers",
        "Sam Lee: hello there", "Sam Lee: so what do you charge",
        "Mary-Jo O'Neil: hi Sam", "Mary-Jo O'Neil: about two grand a month", "Solo Speaker: said once",
        "[00:01](https://calls.example/y#t=1) Dana Ortiz: one Fathom line"]) + "\n")
out, code = rc(workspace=nws)
assert code == 2 and ("Speaker names found: Sam Lee (2 lines), Mary-Jo O'Neil (2 lines), Dana Ortiz (1 line). "
                      "Ask") in out, out
assert all(map(gb.rd_name_ok, ("Sam Lee", "Mary-Jo O'Neil", "J. Smith", "Dana"))), "name shapes"
assert not any(map(gb.rd_name_ok, ("Here's the thing", "Priya earns 40k", "Meeting purpose", "Q3 Review", "A B C D E")))
out, code = rc(owner=OWNER, workspace=ws)
assert code is None and "4 new (n 41 to 44)" in out and "2 call transcript files, 1 written answer file" in out, out
assert "Workspace: %s (2 call transcript files found in its voc/transcripts/)." % os.path.abspath(ws) in out, out
C = rjson(d, "comment-read/Reply Candidates - 01.05.00.json")
assert [(c["n"], c["comment_id"], c["cats"]) for c in C] == [
    (41, "3001", ["question"]), (42, "3002", ["tool_ask"]), (43, "3003", ["stuck"]), (44, "3008", ["question"])], C
assert C[0] == {"n": 41, "post": "RPL001", "creator": "alpha_coach", "post_topic": "", "comment_id": "3001",
                "user": "viewer_3001", "date": "2000-01-20", "likes": 4, "cats": ["question"],
                "text": "How often should I post each week?", "original": None}, C[0]
DF, PF = "comment-read/Reply Drafts - 01.05.00.json", "comment-read/reply-drafts-pending-01.05.00.json"
assert rjson(d, PF) == []                                         # the matcher's working file, empty to fill
CDIR = os.path.join(d, "reel-build", "comment-read")
assert not os.path.exists(os.path.join(d, "reel-build", DF))      # no final file until a set passes
assert not glob.glob(os.path.join(CDIR, "Reply Drafts - *.json"))  # the assembler's glob never sees the pending file
assert rjson(d, "goldmine-run.json")["reply_drafts"] == {
    "date": "01.05.00", "candidates": 4, "sources": {"transcripts": 2, "answers": 1}, "owner_label": OWNER,
    "workspace": os.path.abspath(ws), "passed": False}
SL = rjson(d, "comment-read/reply-shortlist-01.05.00.json")
said = " ".join(p["text"] for r in SL["rows"] for p in r["passages"])
assert SL["owner_label"] == OWNER and not any(t in said for s, t in CALL_A + CALL_B if s == OTHER), said
assert [(p["id"], p["overlap"]) for p in SL["rows"][0]["passages"]] == [   # post + week, then each
    ("transcripts/sales/call-a.md#1-2", 2), ("reply-answers/faq.md#3-3", 1)], SL["rows"][0]
assert SL["rows"][0]["passages"][0]["text"] == CALL_A[1][1] + "\n" + CALL_A[2][1]  # line breaks stay visible
assert all(set(p) == {"id", "file", "overlap", "text"} and len(p["text"]) <= 1500 for r in SL["rows"] for p in r["passages"])
assert [p[0] for p in gb.rd_passages({"transcripts/x/a.md": [["line %d" % k for k in range(1, 9)]],
                                      "reply-answers/b.md": [["one"], ["w " * 900]]})] == [
    "transcripts/x/a.md#1-6", "transcripts/x/a.md#4-8", "reply-answers/b.md#1-1", "reply-answers/b.md#2-2",
    "reply-answers/b.md#3-3"]
assert gb.rd_passages({"transcripts/x/c.md": [["a b", "c d"], ["e f"]]}) == [   # a window never spans another speaker
    ("transcripts/x/c.md#1-2", "transcripts/x/c.md", "a b\nc d"), ("transcripts/x/c.md#3-3", "transcripts/x/c.md", "e f")]
assert max(len(p[2]) for p in gb.rd_passages({"reply-answers/b.md": [["w " * 900]]})) <= 1500
# a quote copied verbatim from any shortlist passage (line breaks and all) passes the word-for-word check
_, RUNS, _, _ = gb.rd_units(gb.Project(d), ws, OWNER)
TX = {k: [gb.rd_norm(r) for r in v] for k, v in RUNS.items()}
for p in (p for r in SL["rows"] for p in r["passages"]):
    assert gb.rd_rule({"draft": p["text"], "quote": p["text"], "files": [p["file"]], "added": []}, TX) in (
        None, "over 300 characters"), p["id"]
assert gb.rd_rule({"draft": "Honestly, " + CALL_B[0][1][0].lower() + CALL_B[0][1][1:], "quote": CALL_B[0][1],
                   "files": ["transcripts/group/call-b.txt"], "added": ["Honestly,"]}, TX) is None  # a plain-lines file
# the owner label matches any case; runs break at another speaker; an answer file is one run
lo = gb.rd_units(gb.Project(d), ws, OWNER.lower())
assert lo == gb.rd_units(gb.Project(d), ws, OWNER) and lo[1]["transcripts/sales/call-a.md"] == [
    CALL_A[1][1] + " " + CALL_A[2][1], CALL_A[4][1]] and lo[1]["reply-answers/faq.md"] == [" ".join(FAQ)], lo[1]
# a failing set leaves no final file; a new run is refused until the set passes
out, code = run("check-replies", d)
assert code == 1 and "4 candidates with no drafts row" in out and not os.path.exists(os.path.join(d, "reel-build", DF)), out
out, code = rc()
assert code == 2 and "Finish the 01.05.00 reply drafts first: run check-replies." in out, out
FIRST = [{"n": n, "comment_id": c, "outcome": "skip", "why": "kept"} for n, c in ((41, "3001"), (42, "3002"),
                                                                                   (43, "3003"), (44, "3008"))]
wjson(d, PF, FIRST)
out, code = run("check-replies", d)
assert code is None and rjson(d, DF) == FIRST, out                # the final file is written only on a full pass
os.remove(os.path.join(d, "reel-build", PF))                      # so the append below must rebuild it from the final
# the same day again: a newly fetched stuck point is appended (n 45); the pending file starts from the final rows
RC["RPL002"][1].append((3010, "Mine keeps stalling at the editing step", 0.1, 0))
reply_comments("RPL002", *RC["RPL002"])
wjson(d, "comment-read/batch-%s-01.read.json" % since.replace("-", ""), {"schema": "goldmine-comment-read/1",
      "batch": "x", "n": 6, "tags": dict(RTAGS, **{"3010": ["stuck"]})})
SECRETS.append("Mine keeps stalling at the editing step")
out, code = rc()                                                  # owner label and workspace kept from the first run
assert code is None and "1 new (n 45 to 45), 5 in Reply Candidates - 01.05.00.json" in out, out
assert [c["n"] for c in rjson(d, "comment-read/Reply Candidates - 01.05.00.json")] == [41, 42, 43, 44, 45]
assert rjson(d, PF) == FIRST and rjson(d, DF) == FIRST, rjson(d, PF)
out, code = rc()
assert code == 2 and "Finish the 01.05.00 reply drafts first" in out, out
print("OK reply candidates: comment read must pass, questions / tool asks / stuck only, earlier runs skipped, n "
      "continues, pending file outside the assembler's glob, final only on a full pass, new run refused until "
      "then, same-day append keeps the final rows, owner label asked once, kept and matched in any case, runs "
      "break at another speaker, a label with no lines stops, shortlist holds only the owner's lines in capped "
      "windows")

# check-replies: every draft word for word; a failing one is demoted to no_match naming the rule, never the text
GOOD = [
    {"n": 41, "comment_id": "3001", "outcome": "draft", "mode": "top", "files": ["transcripts/sales/call-a.md"],
     "source": "call-a.md", "quote": "I post three times a week and never more than that. ... Consistency beats volume "
     "every single time.", "draft": "I post three times a week and never more than that. Consistency beats volume "
     "every single time.", "added": [], "why": "Answered on a call."},
    {"n": 42, "comment_id": "3002", "outcome": "skip", "why": "One reply per post."},   # RPL001 has its one draft
    {"n": 43, "comment_id": "3003", "outcome": "skip", "why": "Only the post's creator could answer."},
    {"n": 44, "comment_id": "3008", "outcome": "no_match", "idea": "A reel on writing the script before the hook.",
     "why": "No passage answers it."},
    {"n": 45, "comment_id": "3010", "outcome": "draft", "mode": "reply", "files": ["reply-answers/faq.md"],
     "source": "faq.md", "quote": "Batching works when you plan the topics first.",
     "draft": "Honestly, batching works when you plan the topics first.", "added": ["Honestly,"], "why": "x"}]
CAPS = {"n": 42, "comment_id": "3002", "outcome": "draft", "mode": "reply", "files": ["transcripts/group/call-b.txt"],
        "source": "call-b.txt", "quote": CALL_B[0][1], "draft": "Honestly, for captions I just use the free tool "
        "built into the editor.", "added": ["Honestly,"], "why": "x"}   # a second draft on RPL001
SECRETS += [r["quote"] for r in GOOD + [CAPS] if "quote" in r] + [r["draft"] for r in GOOD + [CAPS] if "draft" in r]


def replies(rows):
    wjson(d, PF, rows)
    out, code = run("check-replies", d)
    assert not any(t in out for t in SECRETS), out
    return out, code, rjson(d, PF), rjson(d, "goldmine-run.json")["reply_drafts"]["passed"]


out, code, rows, ok = replies(GOOD)                               # GOOD[0] is a valid two-piece quote
assert code is None and ok and "PASS (5 rows: 2 draft, 1 no_match, 2 skip; 0 demoted)" in out and rows == GOOD, out
assert next_line(out) == gb.REBUILD, out
assert rjson(d, DF) == GOOD                                       # a full pass replaces the final file
# one draft per post: a second passing draft on the same post becomes skip, "One reply per post."
out, code, rows, ok = replies(GOOD[:1] + [CAPS] + GOOD[2:])
assert code is None and ok and "Demoted to skip: n 42 (one reply per post)." in out and rows == GOOD, out
# a quote copied straight from a multi-line shortlist passage (its line break kept) passes check-replies
P1 = SL["rows"][0]["passages"][0]["text"]
assert "\n" in P1
out, code, rows, ok = replies([dict(GOOD[0], quote=P1, draft=P1.replace("\n", " "))] + GOOD[1:])
assert code is None and ok and "0 demoted" in out, out
wjson(d, PF, GOOD); run("check-replies", d)
K = "Consistency beats volume every single time."
MUT = [("paraphrase", {"quote": K, "draft": "Consistency beats volume most of the time."},
        "the draft's words (minus added) are not exactly the quote's words"),
       ("silent gap", {"draft": "I post three times a week and never more than that. Consistency beats volume."},
        "the draft's words (minus added) are not exactly the quote's words"),
       ("piece under 4 words", {"quote": "I post three times a week and never more than that. ... Consistency beats "
                                         "volume.", "draft": "I post three times a week and never more than that. "
                                                             "Consistency beats volume."}, "a quote piece is under 4 words"),
       ("across another speaker", {"quote": K + " " + CALL_A[4][1], "draft": K + " " + CALL_A[4][1]},
        "a quote piece is not word for word"),
       ("partial word", {"quote": "I post three times a wee", "draft": "I post three times a wee"},
        "a quote piece is not word for word"),
       ("bare domain", {"quote": K, "draft": K[:-1] + " at mysite.xyz/free"}, "a link"),
       ("short link", {"quote": K, "draft": K[:-1] + ", linktr.ee/me"}, "a link"),
       ("grouped digits", {"quote": K, "draft": K[:-1] + " for $12,500"}, "a number of 4 or more digits"),
       ("percent", {"quote": K, "draft": K[:-1] + " for a 40% lift"}, "an amount or a percentage"),
       ("added link", {"quote": K, "draft": K, "added": ["at mysite.xyz"]}, "an added phrase carries a link"),
       ("added handle", {"quote": K, "draft": K, "added": ["ask @plan_studio"]}, "an added phrase carries an @handle"),
       ("added number", {"quote": K, "draft": K, "added": ["call 555 1234"]},
        "an added phrase carries a number of 4 or more digits"),
       ("quote not verbatim", {"quote": "I post three times every week.", "draft": "I post three times every week."},
        "a quote piece is not word for word"),
       ("another speaker's words", {"quote": CALL_A[3][1], "draft": CALL_A[3][1]}, "a quote piece is not word for word"),
       ("dropped never", {"draft": "I post three times a week and more than that."}, "a negation in the quote was dropped"),
       ("added over 5", {"draft": "Great question, here is what I do: I post three times a week and never more than "
                                  "that.", "added": ["Great question, here is what I do:"]}, "more than 5 added words"),
       ("added negation", {"quote": K, "draft": "Consistency never beats volume every single time.", "added": ["never"]},
        "an added word is a negation"),
       ("over 300", {"files": ["reply-answers/faq.md"], "quote": LONG, "draft": LONG}, "over 300 characters"),
       ("en dash", {"quote": K, "draft": "Consistency beats volume \u2013 every single time."}, "a long dash"),
       ("url", {"quote": K, "draft": K[:-1] + ", see https://example.com/plan", "added": ["see https://example.com/plan"]},
        "a link"),
       ("handle", {"quote": K, "draft": K[:-1] + ", ask @plan_studio", "added": ["ask @plan_studio"]}, "an @handle"),
       ("4+ digits", {"quote": K, "draft": K[:-1] + ", call 5551234", "added": ["call 5551234"]},
        "a number of 4 or more digits"),
       ("unknown file", {"files": ["transcripts/sales/missing.md"]}, "a cited file is not one of this run's")]
for name, change, rule in MUT:
    out, code, rows, ok = replies([dict(GOOD[0], **change)] + GOOD[1:])
    assert code == 1 and not ok and "Demoted to no_match: n 41 (%s" % rule in out, (name, out)
    assert rows[0] == {"n": 41, "comment_id": "3001", "outcome": "no_match", "why": rows[0]["why"]}, (name, rows[0])
    assert rows[0]["why"].startswith("Demoted by check-replies: " + rule), (name, rows[0])
    assert "n 41: no_match needs a one-line content idea" in out and rows[1:] == GOOD[1:], (name, out)
    assert rjson(d, DF) == GOOD, name                             # a failing set never touches the final file
CHK = "Ads work for big brands but organic works for small creators"   # the checker's example: a silent gap
assert gb.rd_rule({"draft": "Ads work for small creators", "quote": CHK, "files": ["f"], "added": []},
                  {"f": [gb.rd_norm(CHK + ".")]}) == "the draft's words (minus added) are not exactly the quote's words"
assert gb.rd_rule({"draft": CHK, "quote": CHK, "files": ["f"], "added": []}, {"f": [gb.rd_norm(CHK + ".")]}) is None
# the speaker's own "...": a short piece passes when the joined text is in the run as said; a real gap still needs 4 words
ELL = {"f": [gb.rd_norm("Honestly... yes, three times a week is plenty for most people.")]}
for q in ("Honestly... yes, three times a week is plenty", "Honestly ... yes, three times a week is plenty",
          "Honestly\u2026 yes, three times a week is plenty"):
    assert gb.rd_rule({"draft": "Honestly, yes, three times a week is plenty.", "quote": q, "files": ["f"], "added": []},
                      ELL) is None, q
assert gb.rd_rule({"draft": "Honestly, plenty for most people.", "quote": "Honestly ... plenty for most people.",
                   "files": ["f"], "added": []}, ELL) == "a quote piece is under 4 words"
for t in ("e.g. this", "the U.S. market", "3.5 stars", "a 10x result", "time. Then", "3 or 4 posts"):
    assert gb.rd_flag(t) is None, t                               # ordinary text is not a link or a number
out, code, rows, ok = replies([dict(rows[0], idea="A reel on posting rhythm.")] + GOOD[1:])
assert code is None and ok, out                                   # a demoted row passes once it carries an idea
# same_as: rides on a passing draft on the same post; one pointing across posts is demoted
SA = [dict(GOOD[0]), {"n": 42, "comment_id": "3002", "outcome": "draft", "same_as": 41, "why": "same ask"}, GOOD[2],
      {"n": 44, "comment_id": "3008", "outcome": "draft", "same_as": 41, "idea": "x", "why": "same ask"}, GOOD[4]]
out, code, rows, ok = replies(SA)
assert code is None and ok and "n 44 (same_as points to no passing draft on the same post)" in out, out
assert rows[1] == SA[1] and rows[3]["outcome"] == "no_match" and "same_as" not in rows[3], rows
for target, why in ((41, "a demoted draft"), (42, "itself")):  # n 41 here fails (a paraphrase), so it is demoted first
    out, code, rows, ok = replies([dict(GOOD[0], draft="I usually post about three times weekly.", idea="x"),
                                   {"n": 42, "comment_id": "3002", "outcome": "draft", "same_as": target, "idea": "y",
                                    "why": "same ask"}] + GOOD[2:])
    assert code is None and ok and "n 42 (same_as points to no passing draft on the same post)" in out, (why, out)
    assert rows[1] == {"n": 42, "comment_id": "3002", "outcome": "no_match", "idea": "y", "why": rows[1]["why"]}, rows
# pairing: every candidate exactly once, every row a candidate with the same comment_id, known outcomes, ideas
for rows_in, want in ((GOOD[:4], "1 candidate with no drafts row: 45"),
                      (GOOD[:3] + [dict(GOOD[3], comment_id="9999")] + GOOD[4:], "drafts row n 44: no candidate"),
                      (GOOD + [GOOD[2]], "candidates with more than one drafts row: 43"),
                      (GOOD + [{"n": 99, "comment_id": "3001", "outcome": "skip"}], "drafts row n 99: no candidate"),
                      (GOOD[:4] + [dict(GOOD[4], outcome="maybe")], "n 45: outcome must be draft, no_match or skip"),
                      (GOOD[:3] + [dict(GOOD[3], idea=" ")] + GOOD[4:], "n 44: no_match needs a one-line content idea")):
    out, code, rows, ok = replies(rows_in)
    assert code == 1 and not ok and want in out, (want, out)
print("OK check-replies: a passing set, %d rejections each demoted naming its rule (paraphrase, silent gap, piece "
      "under 4 words, across another speaker, partial word, not verbatim, another speaker, dropped negation, added "
      "over 5 or a negation, over 300, long dash, links, @handle, numbers, amounts, added link / handle / number, "
      "unknown file), a failing set leaves the final file alone, demoted rows need an idea, same_as (other post, a "
      "demoted draft, itself), pairing gaps; no comment, quote or transcript text printed" % len(MUT))

# no sources at all: the client is told once, plainly; every draft comes back as no_match
z_since = reply_project({"NOS001": ("alpha_coach", [(4001, "What do you use to plan your posts?", 0.9, 0)])}, {})
pass_read(z_since)
empty_ws = tempfile.mkdtemp(prefix="goldmine_ws_"); temps.append(empty_ws)
here = os.getcwd()
os.chdir(empty_ws)                                                # no --workspace: the current folder is used
try:
    out, code = run("reply-candidates", d)                        # nothing found: likely the wrong folder, so it stops
    assert code == 2 and "no call transcripts in " in out and "%s and no written answers in %s, so nothing was saved" % (
        os.path.join("voc", "transcripts"), os.path.join(d, "reel-build", "reply-answers")) in out, out
    assert "--no-sources-ok" in out, out
    st = rjson(d, "goldmine-run.json")
    assert st["reply_drafts"] == {"accepted": True} and "reply_settings" not in st, st  # the folder is never kept
    assert not [f for f in os.listdir(os.path.join(d, "reel-build", "comment-read")) if "eply" in f]
    out, code = run("reply-candidates", d, no_sources_ok=None)    # the client said they have no call transcripts
finally:
    os.chdir(here)
rdz = rjson(d, "goldmine-run.json")["reply_drafts"]
assert code is None and gb.NO_SOURCES in out and rdz["note"] == gb.NO_SOURCES, out
assert rdz["sources"] == {"transcripts": 0, "answers": 0} and rdz["owner_label"] is None, rdz
assert os.path.samefile(rdz["workspace"], empty_ws), rdz
assert rjson(d, "comment-read/reply-shortlist-01.05.00.json")["rows"][0]["passages"] == []
wjson(d, PF, [dict(GOOD[0], n=1, comment_id="4001", idea="A reel on a simple posting plan.")])
out, code = run("check-replies", d)
assert code is None and "n 1 (a cited file is not one of this run's" in out and rjson(d, DF)[0]["outcome"] == "no_match", out
assert rjson(d, "goldmine-run.json")["reply_drafts"]["passed"] is True
# after that stop, a run pointed at the right folder goes ahead and keeps it
pass_read(reply_project({"WSP001": ("alpha_coach", [(4501, "How often should I post each week?", 0.9, 0)])}, {}))
os.chdir(empty_ws)
try:
    out, code = rc()
    assert code == 2 and "nothing was saved" in out, out
    out, code = rc(workspace=ws, owner=OWNER)
finally:
    os.chdir(here)
assert code is None and "Sources: 2 call transcript files" in out, out
assert rjson(d, "goldmine-run.json")["reply_settings"] == {"owner_label": OWNER, "workspace": os.path.abspath(ws)}
print("OK no sources: an empty folder stops and keeps nothing, --workspace then works; with --no-sources-ok the "
      "plain client line, recorded in state, drafts demoted to no_match, workspace defaults to the current folder")

# zero candidates: nothing written, the run counts as passed, check-replies has nothing to check
pass_read(reply_project({"ZER001": ("alpha_coach", [(5001, "This changed how I plan my whole month", 0.0, 1)])},
                        {"5001": ["win"]}))
out, code = run("reply-candidates", d, workspace=empty_ws)
assert code is None and "reply candidates: none" in out, out
assert rjson(d, "goldmine-run.json")["reply_drafts"]["candidates"] == 0 and rjson(d, "goldmine-run.json")[
    "reply_drafts"]["passed"] is True
assert not [f for f in os.listdir(os.path.join(d, "reel-build", "comment-read")) if "eply" in f], out
out, code = run("check-replies", d)
assert code is None and out.startswith("check-replies: nothing to check."), out
print("OK zero candidates: no files, passed, check-replies has nothing to check")

# declined: recorded for this pull with nothing written; a later yes in the same pull runs as normal
pass_read(reply_project({"DEC001": ("alpha_coach", [(6001, "What do you use to plan your posts?", 0.9, 0)])}, {}))
out, code = run("reply-candidates", d, decline=None)
assert code is None and "declined for this pull" in out and next_line(out) == gb.REBUILD, out
assert rjson(d, "goldmine-run.json")["reply_drafts"] == {"declined": True}
assert not [f for f in os.listdir(os.path.join(d, "reel-build", "comment-read")) if "eply" in f]
out, code = run("check-replies", d)
assert code == 2 and "Run reply-candidates first" in out, out
out, code = run("reply-candidates", d, workspace=empty_ws, no_sources_ok=None)
assert code is None and "1 new (n 1 to 1)" in out and "declined" not in rjson(d, "goldmine-run.json")["reply_drafts"], out
print("OK declined: recorded for this pull, nothing written, a later yes clears it")

# record-publish: the skill routes on this pull's publish marker, never on a file path. First publish (Step 9), then
# the one rebuild after the read passed and drafts passed or were declined (Step 12): final, and the pull is done.
out, code = run("record-publish", d, url="https://claude.ai/a/x")
assert code == 2 and "no saved page yet" in out, out
st = rjson(d, "goldmine-run.json")
st.update(dashboard={"html": "page.html"}, comment_read={"comments_since": "x", "packets": ["p"], "passed": False})
st.pop("reply_drafts")
wjson(d, "goldmine-run.json", st)
out, code = run("record-publish", d, url="https://claude.ai/a/x")
pub = rjson(d, "goldmine-run.json")["published"]
assert code is None and next_line(out) == "NEXT: run comment-read for this pull's comment read.", out
assert pub == {"manifest": st["manifest"], "url": "https://claude.ai/a/x", "at": pub["at"], "phase": "first"}, pub
st = rjson(d, "goldmine-run.json")
st["comment_read"]["passed"] = True
wjson(d, "goldmine-run.json", st)
out, code = run("record-publish", d)                               # read passed, drafts not settled: not final yet
assert rjson(d, "goldmine-run.json")["published"]["phase"] == "first", out
for rdv in ({"declined": True}, {"candidates": 3, "passed": True}):
    st["reply_drafts"] = rdv
    wjson(d, "goldmine-run.json", st)
    out, code = run("record-publish", d)                           # no --url (publishing failed): the kept link stays
    pub = rjson(d, "goldmine-run.json")["published"]
    assert code is None and (pub["phase"], pub["url"]) == ("final", "https://claude.ai/a/x"), (rdv, pub)
    assert next_line(out).startswith("NEXT: this pull is done."), out
print("OK record-publish: needs a saved page, first then final (read passed, drafts passed or declined), keeps the link")

# two weekly runs stack in the dashboard's Reply Queue (v0.2.2 assembler: every dated pair, keyed by comment_id)
d = [t for t in temps if os.path.isdir(os.path.join(t, "reel-build", "reply-answers"))][0]
wjson(d, PF, GOOD)
run("check-replies", d)
gb.today = lambda: "01.12.00"
RC["RPL002"][1].append((3011, "How many hooks do you test per idea?", 0.9, 1))
reply_comments("RPL002", *RC["RPL002"])
out, code = run("reply-candidates", d)
assert code is None and "1 new (n 46 to 46), 1 in Reply Candidates - 01.12.00.json" in out, out
wjson(d, "comment-read/reply-drafts-pending-01.12.00.json", [{"n": 46, "comment_id": "3011", "outcome": "no_match",
                                                              "idea": "A reel on testing hooks.", "why": "x"}])
out, code = run("check-replies", d)
assert code is None and "PASS (1 rows" in out, out
assert sorted(f for f in os.listdir(os.path.join(d, "reel-build", "comment-read")) if "rafts" in f) == [
    "Reply Drafts - 01.05.00.json", "Reply Drafts - 01.12.00.json", "reply-drafts-pending-01.05.00.json",
    "reply-drafts-pending-01.12.00.json"]                          # both pending files sit beside the finals
gb.today = real_today
if dm:
    with contextlib.redirect_stdout(io.StringIO()):
        R = dm.load_replies(Path(d))
    assert R["source"] == "Reply Drafts - 01.05.00.json + Reply Drafts - 01.12.00.json", R["source"]
    assert sorted(r["comment_id"] for r in R["rows"]) == ["3001", "3002", "3003", "3008", "3010", "3011"], R["rows"]
    assert {r["comment_id"]: r["outcome"] for r in R["rows"]}["3011"] == "no_match"
    print("OK reply runs stack in the dashboard assembler's load_replies (%s)" % os.path.basename(os.path.dirname(DASH_PY)))
else:
    print("SKIP load_replies stacking: no dashboard assembler here (set GOLDMINE_DASHBOARD_PY to one)")


# a new pull: plan starts the run state over, but the owner label and workspace are kept, and a set left unfinished
# in an earlier pull blocks a new run (read from disk) until check-replies --date finishes it
def new_pull(day, at):
    with open(os.path.join(d, "analysis-data.json"), encoding="utf-8") as f:
        ad = json.load(f)
    ad["meta"]["generated_at"] = at                                # a re-analyze: plan freezes a new manifest
    with open(os.path.join(d, "analysis-data.json"), "w", encoding="utf-8") as f:
        json.dump(ad, f)
    gb.today = lambda: day
    run("plan", d)
    pass_read(rjson(d, rjson(d, "goldmine-run.json")["manifest"])["generated_at"][:10])


NP = [(7001, "How often should I post each week?", 0.9, 0), (7002, "What do you use to plan your posts?", 0.9, 0),
      (7003, "Which camera do you film your reels on?", 0.9, 0)]
SECRETS += [t for _, t, _, _ in NP]
gb.today = lambda: "02.01.00"
pass_read(reply_project({"NEW001": ("alpha_coach", NP[:1])}, {}))
out, code = rc(owner=OWNER, workspace=ws)
assert code is None and "1 new (n 1 to 1)" in out, out             # left unchecked: no drafts written
st = rjson(d, "goldmine-run.json")
st["published"] = {"manifest": st["manifest"], "url": "https://claude.ai/a/x", "phase": "final"}
wjson(d, "goldmine-run.json", st)
new_pull("02.08.00", "2000-02-08T00:00:00Z")                      # a new pull is never "done": its marker starts empty
st = rjson(d, "goldmine-run.json")
assert "reply_drafts" not in st and "published" not in st and st["reply_settings"] == {"owner_label": OWNER, "workspace": os.path.abspath(ws)}, st
reply_comments("NEW001", "alpha_coach", NP[:2])
out, code = rc()
assert code == 2 and "Finish the 02.01.00 reply drafts first: run check-replies --date 02.01.00." in out, out
assert rjson(d, "goldmine-run.json")["reply_drafts"] == {"accepted": True}  # the yes is kept before that stop
out, code = run("check-replies", d)                               # no --date: the newest unfinished set on disk
assert code == 1 and "1 candidate with no drafts row: 1" in out, out  # the kept label read the transcripts: no re-ask
wjson(d, "comment-read/reply-drafts-pending-02.01.00.json", [{"n": 1, "comment_id": "7001", "outcome": "skip", "why": "x"}])
out, code = run("check-replies", d, date="02.01.00")
assert code is None and "PASS (1 rows" in out and rjson(d, "comment-read/Reply Drafts - 02.01.00.json")[0]["n"] == 1, out
assert rjson(d, "goldmine-run.json")["reply_drafts"] == {"accepted": True}  # an earlier pull's set leaves it alone
out, code = rc()                                                  # no --owner: the kept label, never asked again
assert code is None and "1 new (n 2 to 2)" in out and "Sources: 2 call transcript files" in out, out  # the kept workspace
out, code = run("check-replies", d, date="02.01.00")             # --date reaches past this pull's own unpassed set
assert code is None and "PASS (1 rows" in out and rjson(d, "goldmine-run.json")["reply_drafts"]["passed"] is False, out
wjson(d, "comment-read/reply-drafts-pending-02.08.00.json", [{"n": 2, "comment_id": "7002", "outcome": "skip", "why": "x"}])
out, code = run("check-replies", d)
assert code is None and "PASS (1 rows" in out, out
reply_comments("NEW001", "alpha_coach", NP)                       # same day: n 3 appended, pending restarts from the final
out, code = rc()
assert code is None and "1 new (n 3 to 3)" in out, out
new_pull("02.15.00", "2000-02-15T00:00:00Z")                      # pending equals the final, but n 3 was never checked
out, code = rc()
assert code == 2 and "Finish the 02.08.00 reply drafts first: run check-replies --date 02.08.00." in out, out
out, code = run("check-replies", d, date="2.8.00")
assert code == 2 and "--date takes a reply run's date as MM.DD.YY" in out, out
wjson(d, "comment-read/reply-drafts-pending-02.08.00.json", [{"n": n, "comment_id": c, "outcome": "skip", "why": "x"}
                                                             for n, c in ((2, "7002"), (3, "7003"))])
out, code = run("check-replies", d)
assert code is None and "PASS (2 rows" in out, out
out, code = rc()                                                  # finished, so this pull's run goes ahead
assert code is None and "reply candidates: none" in out, out
gb.today = real_today
print("OK a new pull keeps the owner label and workspace, an earlier pull's unfinished set (no final, or a "
      "same-day append never checked) blocks reply-candidates from disk, check-replies --date (default the "
      "newest unfinished) finishes it without touching this pull's state")

for t in temps:
    shutil.rmtree(t, ignore_errors=True)
print("OK runner steps: ask always (under and over budget), top-per-creator, zero breakouts, "
      "reads pre-fill, bait as lm_none, stale PAPS row and file, lm_types rule, proven hooks")
