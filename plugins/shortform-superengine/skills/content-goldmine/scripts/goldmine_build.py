#!/usr/bin/env python3
"""Content Goldmine runner: turns a finished competitor pull into every input the
Content Goldmine Dashboard needs. Replaces the earlier one-off scripts.

Usage:  python goldmine_build.py <step> <project_dir> [options]

Steps, in order. Every step is resume-safe: re-running never pays twice.
  plan [--top-per-creator K]
                          FREE. Freezes this pull's breakouts into a dated Breakout Manifest,
                          counts what is missing (comments, transcripts, shares), prints the
                          credit price (capped to the top K breakouts per creator when K is
                          given) and a NEXT line that always asks the user, with that price,
                          before the paid fetch, whatever the credit count.
  fetch --approved N [--top-per-creator K]
                          PAID. Only after the user said yes to plan's ask. One comments page
                          (prism/comments, 5 cr) per breakout that has none yet (the same top K
                          per creator). Hard-stops before spend would pass N.
  transcribe              FREE. Breakouts with no transcript, through the plugin's own engine
                          (faster-whisper small, GPU if present, else CPU). Merges into the
                          per-creator transcript files, never overwriting a good record.
  compute                 FREE. Lead-magnet popularity metric (CTA rule + comment-rate benchmark)
                          and the comment retrieval rate.
  reads                   FREE. Writes the reads packet Claude uses for PAPS, Topic Map and
                          Pattern Read, and pre-fills those three files with every mechanical
                          field, so Claude writes only the judgement fields (shapes:
                          ../references/reads.md). A file that already exists is left alone.
  check-reads             FREE. Validates those three files against the breakouts; records them
                          as this run's inputs only when all pass, then writes the 3-row
                          Proven Hooks file.
  dashboard               FREE. Downloads the pinned Content Goldmine Dashboard (curl), checks its
                          commit stamp, unpacks it into the cache, and builds the page from this
                          run's files into <project>/visuals/. Only after check-reads passed.

Reads:   <project>/analysis-data.json (period_breakouts, meta)
         <project>/source/competitors/reels/*.json          (the pull; the corpus)
         <project>/source/competitors/transcripts/*.json    (+ transcripts/<creator>/<sc>.txt)
         <project>/source/comments/<sc>.json, source/winners/<sc>-stats.json (legacy shares)
Writes:  <project>/reel-build/goldmine-run.json  (this run's state: which files are current)
         <project>/reel-build/Breakout Manifest - <n> - <date>.json
         <project>/reel-build/Lead Magnet Popularity - Metric - <date>.json
         <project>/reel-build/Comment Retrieval - Rate - <date>.json
         <project>/reel-build/Goldmine Reads Packet - <n> - <date>.json
         <project>/reel-build/Proven Hooks - <n> - <date>.json  (named in goldmine-run.json reads.proven_hooks)
         <project>/source/comments/<sc>.json, source/competitors/transcripts/<handle>.json
         <project>/visuals/Content Goldmine Dashboard - <date>.html, reel-build/dashboard-build.log
"""
import datetime, glob, json, os, re, shutil, statistics, subprocess, sys, tarfile, tempfile, time
import urllib.error, urllib.parse, urllib.request

BUDGET = 600          # goldmine per-pull credit budget; mirrored in hooks/credit-guard.mjs
COMMENT_CR = 5        # prism/comments, one page, per breakout
MIN_BASELINE_N = 3    # non-CTA reels with a rate needed before a creator median is trusted
BASE = "https://www.socialcrawl.dev/v1/"
NO_BREAKOUTS = ("No breakout reels in this pull's window, so there is nothing to build yet. A breakout "
                "is a reel that beat its creator's usual views by a wide margin, and none did in this "
                "window. Run the competitor pull again later, then run plan again.")


# ---------------------------------------------------------------- helpers
def die(msg, code=2):
    print("ERROR: " + msg)
    sys.exit(code)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return time.strftime("%m.%d.%y")


def sc_of(url):
    m = re.search(r"/(?:reel|reels|p|tv)/([^/?#]+)", url or "")
    return m.group(1) if m else None


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, obj):
    """Atomic write: a crash mid-write never leaves a half file (paid data lives here)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def items_of(d):
    if isinstance(d, list):
        return d
    return d.get("reels") or d.get("items") or (d.get("data") or {}).get("items") or []


class Project:
    def __init__(self, path):
        self.p = os.path.abspath(path)
        if not os.path.isfile(self.j("analysis-data.json")):
            die("no analysis-data.json in %s. Run the competitor pull (and analyze.py) first." % self.p)
        self.rb = self.j("reel-build")
        os.makedirs(self.rb, exist_ok=True)
        self.state_path = os.path.join(self.rb, "goldmine-run.json")
        self.state = jload(self.state_path) if os.path.isfile(self.state_path) else {"schema": "goldmine-run/1"}

    def j(self, *a):
        return os.path.join(self.p, *a)

    def save_state(self):
        self.state["updated_at"] = now_utc()
        jsave(self.state_path, self.state)

    def corpus(self):
        """Every competitor reel in the pull, keyed by shortcode. The client's own reels
        (source/reels-full.json) are not part of the field corpus."""
        out = {}
        for f in sorted(glob.glob(self.j("source", "competitors", "reels", "*.json"))):
            try:
                d = jload(f)
            except Exception:
                continue
            handle = (d.get("handle") if isinstance(d, dict) else None) or os.path.basename(f)[:-5]
            for r in items_of(d):
                p = r.get("post") or {}
                sc = sc_of(p.get("url"))
                if sc:
                    out[sc] = {"handle": handle, "post": p}
        return out

    def manifest(self):
        name = self.state.get("manifest")
        # No manifest and nothing broke out. A zero first run saves no run file (step_plan), so the
        # analysis is checked too.
        if not name and ((self.state.get("plan") or {}).get("breakouts") == 0
                         or not (jload(self.j("analysis-data.json")).get("period_breakouts") or {}).get("reels")):
            print(NO_BREAKOUTS)
            sys.exit(0)
        if not name or not os.path.isfile(os.path.join(self.rb, name)):
            die("no Breakout Manifest for this run. Run the plan step first.")
        return jload(os.path.join(self.rb, name))

    def transcript_index(self):
        """shortcode -> (status, text). status: 'done' (text, or a deliberate null with no
        error: a music-only ruling), 'failed' (the record carries an error: worth retrying)."""
        idx = {}
        for f in glob.glob(self.j("source", "competitors", "transcripts", "*.json")):
            try:
                d = jload(f)
            except Exception:
                continue
            for r in d.get("reels") or []:
                sc = sc_of(r.get("url"))
                if not sc:
                    continue
                t = r.get("text")
                ok = not r.get("error")
                if ok or sc not in idx:
                    idx[sc] = ("done" if ok else "failed", t if isinstance(t, str) else "")
        for f in glob.glob(self.j("transcripts", "*", "*.txt")):
            sc = os.path.basename(f)[:-4]
            body = open(f, encoding="utf-8", errors="replace").read()
            spoken = body.split("## SPOKEN TRANSCRIPT", 1)[-1].strip()
            if "NO VOICEOVER" in body[:600] or spoken:
                idx.setdefault(sc, ("done", spoken))
        return idx


def api_key():
    k = os.environ.get("SOCIALCRAWL_API_KEY", "").strip()
    if k.startswith("sc_") and "your" not in k.lower():
        return k
    p = os.path.expanduser("~/.config/socialcrawl/api_key")
    if os.path.isfile(p):
        k = open(p, encoding="utf-8").read().strip()
        if k:
            return k
    return None


def api_get(path, params, key, timeout=300):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"_raw": body[:500]}
    except Exception as e:
        return 0, {"_exc": repr(e)}


# ---------------------------------------------------------------- CTA rule (the earlier cta_rule.py, verbatim logic)
# A "trigger-comment CTA" asks the viewer to leave a specific TRIGGER WORD as a comment in
# exchange for a lead magnet. Not a generic engagement ask ("comment below").
# "dm" is deliberately NOT an anchor: a DM-routed trigger cannot move a comment rate.
ANCHOR = r"(?i:comment|drop|type|reply)(?i:s|ed|ing)?"
# Non-greedy filler: greedy filler swallowed the real trigger ("Comment MIKA for AI" -> "AI").
FILLER = r"(?:[ \t]+[^\s\"'‘’“”«»\n]{1,8}){0,2}?[\s:,\-\u2014]*"
OPENQ = CLOSEQ = "\"'‘’“”«»"
RE_QUOTED = re.compile(
    ANCHOR + FILLER + r"[" + OPENQ + r"]\s*([^\"'‘’“”«»\n]{1,30}?)\s*[" + CLOSEQ + r"]")
RE_BOLD = re.compile(ANCHOR + FILLER + r"\*\*\s*([^*\n]{1,30}?)\s*\*\*")
RE_BARE_CAPS = re.compile(ANCHOR + FILLER + r"\b([A-Z][A-Z0-9]{1,24}(?:\s+[A-Z][A-Z0-9]{1,24})?)\b")
RE_BARE_BELOW = re.compile(ANCHOR + r"[\s:,\-\u2014]*\b([A-Za-z][A-Za-z0-9]{1,24})\b\s+below",
                           re.IGNORECASE)
RE_BARE_WORD = re.compile(ANCHOR + r"[\s:,\-\u2014]*\b([A-Za-z][A-Za-z0-9]{1,24})\b\s+(?:for|to|and|if|&)\b",
                          re.IGNORECASE)
# "comment the word callout below": an explicitly named word is a trigger in any case (the bare
# rules allow no "the word" filler before a lowercase token).
RE_NAMED_WORD = re.compile(ANCHOR + r"\s+(?:the\s+)?(?:key\s*)?words?\s*[:\-]?\s*[\"'‘’“”«»]?([A-Za-z][A-Za-z0-9]{1,24})\b")
# "Type X and it generates..." is an instruction to type into a tool, not a comment ask. A "type"
# anchor only counts when its sentence points at the comments or a send.
RE_TYPE_ANCHOR = re.compile(r"(?i)^typ")
RE_COMMENT_CTX = re.compile(r"(?i)\bbelow\b|\bcomments?\b|👇|\bi'?ll\b|\bi will\b|\bsend you\b|\bdm you\b|\bin the replies\b")
# "Type 'X' if you believe..." is a comment ask with no payoff: counted, labelled weak (the rule
# name gets a "_weak" suffix).
RE_IF_YOU = re.compile(r"(?i)\bif\s+(?:you|u)\b")
RE_PAYOFF = re.compile(
    r"\b(send|sending|get|getting|grab|link|links|guide|guides|template|templates|prompt|"
    r"prompts|access|dm|breakdown|playbook|walkthrough|setup|steps|blueprint|checklist|"
    r"course|training|workshop|resource|repo|repos|file|files|copy|free|trial|details|"
    r"recording|video|list|swipe|cheat|doc|docs|pdf|notion)\b", re.IGNORECASE)
STOP = {
    "BELOW", "DOWN", "HERE", "YOUR", "YOURS", "IF", "WHAT", "WHICH", "WHO", "ANY", "ON",
    "IN", "TO", "FOR", "WITH", "THIS", "THAT", "THE", "A", "AN", "AND", "OR", "SECTION",
    "SECTIONS", "SOMETHING", "ANYTHING", "ME", "US", "IT", "OK", "YES", "NO", "PLEASE",
    "PLS", "AI", "LOL", "OMG", "BTW", "IM", "I", "IS", "ARE", "WAS", "WILL", "WOULD", "CAN",
    "DO", "DID", "DOES", "HOW", "WHY", "WHEN", "WHERE", "MY", "OUR", "YOU",
    "THEY", "WE", "HE", "SHE", "THEM", "THEIR", "OF", "AT", "BY", "SO", "BUT", "NOT",
    "ALL", "MORE", "MOST", "SOME", "ONE", "TWO", "NOW", "JUST", "ALSO", "THEN", "THAN",
    "BEEN", "HAVE", "HAS", "HAD", "BE", "AS", "UP", "OUT", "OFF", "LET", "TELL", "SAY",
    "WORD", "WORDS", "COMMENT", "COMMENTS", "BELOW👇",
}


def _tok_ok(tok, quoted=False):
    t = (tok or "").strip()
    if not t or not re.search(r"[A-Za-z0-9]", t) or len(t.split()) > 3:
        return False
    if quoted:  # an explicitly quoted token is a trigger even if it is a stop word ("Now")
        return True
    return all(w.upper().strip(".,!?:;") not in STOP for w in t.split())


def detect_cta(caption):
    """Return (is_cta, trigger_token, rule_name). First matching rule wins."""
    if not caption:
        return False, None, None

    def comment_ask(m):
        # "" = a comment ask, "_weak" = a no-payoff "type X if you..." ask, None = not an ask.
        if not RE_TYPE_ANCHOR.match(m.group(0)):
            return ""
        a = max(caption.rfind(x, 0, m.start()) for x in ".!?\n") + 1
        z = [i for i in (caption.find(x, m.end()) for x in ".!?\n") if i >= 0]
        sent = caption[a:min(z) if z else len(caption)]
        return "" if RE_COMMENT_CTX.search(sent) else "_weak" if RE_IF_YOU.search(sent) else None

    for m in RE_NAMED_WORD.finditer(caption):
        k = comment_ask(m)
        if _tok_ok(m.group(1)) and k is not None:
            return True, m.group(1).strip(), "named_word" + k
    for rx, name in ((RE_QUOTED, "quoted"), (RE_BOLD, "bold"),
                     (RE_BARE_CAPS, "bare_caps"), (RE_BARE_BELOW, "bare_below")):
        for m in rx.finditer(caption):
            k = comment_ask(m)
            if _tok_ok(m.group(1), quoted=name in ("quoted", "bold")) and k is not None:
                return True, m.group(1).strip(), name + k
    for m in RE_BARE_WORD.finditer(caption):
        k = comment_ask(m)
        if _tok_ok(m.group(1)) and RE_PAYOFF.search(caption) and k is not None:
            return True, m.group(1).strip(), "bare_word_payoff" + k
    return False, None, None


# ---------------------------------------------------------------- plan
def comments_status(prj, sc):
    cp = prj.j("source", "comments", sc + ".json")
    if not os.path.isfile(cp):
        return "missing"
    try:
        fx = jload(cp).get("_fetch") or {}
    except Exception:
        return "missing"  # corrupt: refetch
    return "have" if (fx.get("completed") or (fx.get("pages") or 0) >= 1) else "missing"


def per_creator_arg(args):
    v = args.get("top-per-creator")
    if v is None:
        return None
    if not str(v).isdigit():
        die("--top-per-creator needs a whole number, for example 3.")
    return int(v)


def top_per_creator(breakouts, n):
    """URLs of the top n breakouts per creator by multiplier, ties on shortcode. Without it a
    credit cap spends everything on the highest-multiplier creators."""
    ranked = sorted(breakouts, key=lambda b: (-(b.get("mult") or 0), sc_of(b["url"]) or ""))
    keep, per = set(), {}
    for b in ranked:
        if per.get(b["handle"], 0) < n:
            per[b["handle"]] = per.get(b["handle"], 0) + 1
            keep.add(b["url"])
    return keep


def shares_of(prj, corpus, sc):
    e = ((corpus.get(sc) or {}).get("post") or {}).get("engagement") or {}
    if e.get("shares") is not None:
        return e.get("shares"), "pull"
    sp = prj.j("source", "winners", sc + "-stats.json")
    if os.path.isfile(sp):
        try:
            s = jload(sp)["data"]["post"]["engagement"].get("shares")
            if s is not None:
                return s, "stats_file"
        except Exception:
            pass
    return None, None


def step_plan(prj, args):
    cap_n = per_creator_arg(args)
    ad = jload(prj.j("analysis-data.json"))
    pb = ad.get("period_breakouts") or {}
    src_at = (ad.get("meta") or {}).get("generated_at")
    reels = pb.get("reels") or []
    if not reels:
        print(NO_BREAKOUTS)
        # A first run saves nothing, so the next run is still a first run and opens the 30-day window.
        # After a Goldmine, the run file keeps its passed reads.
        if os.path.isfile(prj.state_path):
            prj.state.update({"manifest": None, "source_generated_at": src_at, "plan": {"breakouts": 0}})
            prj.save_state()
        return

    # Freeze the breakout set once per analyze run. Later steps read the manifest, never the
    # live period_breakouts, so a re-analyze mid-run cannot shift the set under paid work.
    name = prj.state.get("manifest")
    if not (name and prj.state.get("source_generated_at") == src_at
            and os.path.isfile(os.path.join(prj.rb, name))):
        name = "Breakout Manifest - %d - %s.json" % (len(reels), today())
        if os.path.isfile(os.path.join(prj.rb, name)):
            old = jload(os.path.join(prj.rb, name))
            if old.get("source_generated_at") != src_at:
                name = "Breakout Manifest - %d - %s - %s.json" % (len(reels), today(), time.strftime("%H%M%S"))
        keep = ("id", "url", "handle", "views", "mult", "tier", "hook", "themes", "hook_line", "published_at")
        jsave(os.path.join(prj.rb, name), {
            "schema": "goldmine-manifest/1",
            "_note": "Frozen copy of analysis-data.json period_breakouts for one goldmine run.",
            "generated_at": now_utc(), "source_generated_at": src_at,
            "window": {"from": pb.get("window_from"), "to": pb.get("window_to")},
            "denominator": pb.get("denominator"), "client_excluded": pb.get("client_excluded"),
            "creators_skipped": pb.get("creators_skipped") or [],
            "count": len(reels),
            "breakouts": [{k: r.get(k) for k in keep} for r in reels],
        })
        prj.state = {"schema": "goldmine-run/1", "manifest": name, "source_generated_at": src_at}
    man = jload(os.path.join(prj.rb, name))
    corpus = prj.corpus()
    tx = prj.transcript_index()

    need_comments, need_tx, no_media, share_src = [], [], [], {"pull": 0, "stats_file": 0, None: 0}
    keep = top_per_creator(man["breakouts"], cap_n) if cap_n is not None else None
    have = 0
    for b in man["breakouts"]:
        sc = sc_of(b["url"])
        status = comments_status(prj, sc)
        have += status == "have"
        if status == "missing" and (keep is None or b["url"] in keep):
            need_comments.append(sc)
        if tx.get(sc, ("missing",))[0] != "done":
            (need_tx if media_url(corpus, sc) else no_media).append(sc)
        share_src[shares_of(prj, corpus, sc)[1]] += 1

    est = COMMENT_CR * len(need_comments)
    key = api_key()
    balance = None
    if key and est:
        st, env = api_get("credits/balance", None, key, timeout=30)  # 0 credits
        if st == 200:
            balance = (env.get("data") or env).get("balance", (env.get("data") or env).get("credits_remaining"))
    plan = {
        "breakouts": man["count"], "comments_have": have,
        "comments_missing": len(need_comments), "estimate_credits": est, "budget": BUDGET,
        "over_budget": est > BUDGET, "balance": balance, "api_key_found": bool(key),
        "top_per_creator": cap_n,
        "transcripts_missing": len(need_tx), "transcripts_no_media": no_media,
        "shares_from_pull": share_src["pull"], "shares_from_stats_files": share_src["stats_file"],
        "shares_missing": share_src[None],
    }
    prj.state["plan"] = plan
    prj.save_state()

    print("Breakout Manifest : %s (%d breakouts, window %s to %s)"
          % (name, man["count"], man["window"]["from"], man["window"]["to"]))
    print("Comments          : %d have, %d to fetch%s -> price %d credits (budget %d)"
          % (plan["comments_have"], len(need_comments),
             " (top %d per creator)" % cap_n if cap_n is not None else "", est, BUDGET))
    if balance is not None:
        print("Balance           : %s credits" % balance)
    print("Transcripts       : %d missing%s" % (len(need_tx),
          (", %d with no media link (re-pull to transcribe)" % len(no_media)) if no_media else ""))
    print("Shares            : %d from the pull, %d from stats files, %d unavailable%s"
          % (share_src["pull"], share_src["stats_file"], share_src[None],
             " (pull without include=stats)" if share_src[None] else ""))
    if not est:
        print("NEXT: nothing to fetch. Run transcribe, then compute.")
    elif not key:
        print("NEXT: no SocialCrawl key found (SOCIALCRAWL_API_KEY or ~/.config/socialcrawl/api_key).")
    elif balance is not None and balance < est:
        print("NEXT: balance %s is below the %d credit estimate. Top up or skip comments." % (balance, est))
    else:
        # Always ask, whatever the count: the paid fetch runs only after the user's yes.
        print('NEXT: ASK the user and wait for a yes before any paid call, in these words: "Getting '
              'the comments for %d breakout reel%s costs %d SocialCrawl credits (%d each).%s Shall I '
              'spend %d credits?" Only after a yes, run: fetch --approved %d%s'
              % (len(need_comments), "" if len(need_comments) == 1 else "s", est, COMMENT_CR,
                 " That is over the %d credit per-pull budget." % BUDGET if est > BUDGET else "",
                 est, est, " --top-per-creator %d" % cap_n if cap_n is not None else ""))


def media_url(corpus, sc):
    m = (((corpus.get(sc) or {}).get("post") or {}).get("content") or {}).get("media_urls")
    if isinstance(m, list):
        m = m[0] if m else None
    return m


# ---------------------------------------------------------------- fetch
def step_fetch(prj, args):
    if args.get("approved") is None:
        die("fetch needs --approved <credits> (the plan step prints the number).")
    if not str(args["approved"]).isdigit():
        die("--approved needs a whole number of credits, for example 30 (the plan step prints it).")
    cap = int(args["approved"])
    key = api_key()
    if not key:
        die("no SocialCrawl key found (SOCIALCRAWL_API_KEY or ~/.config/socialcrawl/api_key).")
    man = prj.manifest()
    os.makedirs(prj.j("source", "comments"), exist_ok=True)
    todo = [b for b in man["breakouts"] if comments_status(prj, sc_of(b["url"])) == "missing"]
    cap_n = per_creator_arg(args)
    if cap_n is None:  # no flag: fetch exactly what plan priced
        cap_n = (prj.state.get("plan") or {}).get("top_per_creator")
    if cap_n is not None:
        keep = top_per_creator(man["breakouts"], cap_n)
        todo = [b for b in todo if b["url"] in keep]
    spent, done, failures, remaining = 0, 0, [], None
    max_calls, calls = cap // COMMENT_CR, 0  # hard ceiling: holds even if the API reports 0 credits
    print("fetch: %d breakouts need comments%s, cap %d credits"
          % (len(todo), " (top %d per creator)" % cap_n if cap_n is not None else "", cap))
    for i, b in enumerate(todo, 1):
        if spent + COMMENT_CR > cap:
            print("STOP: the next call would pass the approved %d credits (spent %d)." % (cap, spent))
            break
        if calls >= max_calls:
            print("STOP: the next call would pass the %d calls the approved %d credits allow (%d each)."
                  % (max_calls, cap, COMMENT_CR))
            break
        sc = sc_of(b["url"])
        status, env = api_get("prism/comments", {"url": b["url"]}, key)
        calls += 1
        if (status != 200 or not env.get("success")) and calls < max_calls:
            time.sleep(5)
            status, env = api_get("prism/comments", {"url": b["url"]}, key)
            calls += 1
        if status != 200 or not env.get("success"):
            failures.append({"shortcode": sc, "http": status, "error": str(env)[:300]})
            print("  %02d %s FAIL http=%s" % (i, sc, status))
            continue
        d = env.get("data") or {}
        cu, cu_est = env.get("credits_used"), False
        if isinstance(cu, bool) or not isinstance(cu, (int, float)):
            cu, cu_est = COMMENT_CR, True  # not reported: count plan's per-call price, so the cap still holds
        spent += cu
        remaining = env.get("credits_remaining", remaining)
        comments = d.get("comments") or []
        doc = dict(env)
        doc["data"] = dict(d, comments=comments, total_fetched=len(comments), returned=len(comments))
        doc["_fetch"] = {"shortcode": sc, "handle": b["handle"], "url": b["url"],
                         "fetched_at": now_utc(), "endpoint": "prism/comments",
                         "pages": 1, "page_credits": [cu], "credits_total": cu,
                         "completed": bool(d.get("completed")), "next_cursor": d.get("next_cursor"),
                         "by": "content-goldmine"}
        if cu_est:
            doc["_fetch"]["credits_estimated"] = True
        jsave(prj.j("source", "comments", sc + ".json"), doc)
        done += 1
        print("  %02d %s %s %dcr comments=%d" % (i, sc, b["handle"], cu, len(comments)))
        if done == 5 and spent > 2 * 5 * COMMENT_CR:
            print("STOP: the first 5 calls cost %d credits, over twice the %d estimate." % (spent, 5 * COMMENT_CR))
            break
        time.sleep(0.7)
    prj.state["fetch"] = {"at": now_utc(), "approved": cap, "spent": spent, "fetched": done,
                          "failures": failures, "credits_remaining": remaining}
    prj.save_state()
    print("fetch done: %d fetched, %d credits spent, %d failed, balance %s"
          % (done, spent, len(failures), remaining))


# ---------------------------------------------------------------- transcribe
def step_transcribe(prj, args):
    man = prj.manifest()
    corpus = prj.corpus()
    tx = prj.transcript_index()
    todo = [b for b in man["breakouts"]
            if tx.get(sc_of(b["url"]), ("missing",))[0] != "done" and media_url(corpus, sc_of(b["url"]))]
    if not todo:
        gap = sum(1 for b in man["breakouts"] if tx.get(sc_of(b["url"]), ("missing",))[0] != "done")
        print("transcribe: nothing to transcribe. The %d breakout%s with no transcript ha%s no media link, so the "
              "reads will use the captions." % ((gap,) + (("", "s") if gap == 1 else ("s", "ve")))
              if gap else "transcribe: every breakout with media already has a transcript.")
        prj.state["transcribe"] = {"at": now_utc(), "attempted": 0}
        prj.save_state()
        return
    if not shutil.which("ffmpeg"):
        die("ffmpeg is not installed or not on PATH. Install it, then re-run transcribe.", 3)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("faster-whisper is not installed. Install it (pip install faster-whisper), then re-run transcribe.", 3)
    try:
        model, dev = WhisperModel("small", device="cuda", compute_type="float16"), "cuda"
    except Exception:
        model, dev = WhisperModel("small", device="cpu", compute_type="int8"), "cpu"
    print("transcribe: %d breakouts, model small on %s" % (len(todo), dev))
    tmp = tempfile.mkdtemp(prefix="goldmine_tx_")
    ok = fail = 0
    by_handle = {}
    for i, b in enumerate(todo, 1):
        sc = sc_of(b["url"])
        wav = os.path.join(tmp, sc + ".wav")
        rec = {"rank": "breakout", "url": b["url"], "views": b.get("views")}
        try:
            subprocess.run(["ffmpeg", "-y", "-i", media_url(corpus, sc), "-vn", "-ar", "16000", "-ac", "1", wav],
                           capture_output=True, timeout=180)
            if not (os.path.isfile(wav) and os.path.getsize(wav) > 1000):
                raise RuntimeError("ffmpeg_empty (an expired media link: re-pull, then re-run)")
            segs, info = model.transcribe(wav, language="en", vad_filter=True)
            seg = [{"s": round(s.start, 2), "e": round(s.end, 2), "text": s.text.strip()} for s in segs]
            rec.update(text=" ".join(s["text"] for s in seg).strip(), segments=seg, duration=round(info.duration, 2))
            ok += 1
        except Exception as e:
            rec.update(text=None, error=str(e)[:200])
            fail += 1
        finally:
            if os.path.isfile(wav):
                os.remove(wav)
        by_handle.setdefault(b["handle"], []).append(rec)
        print("  %02d/%d %s %s" % (i, len(todo), sc, "ok" if rec.get("text") is not None else "FAIL " + rec["error"]))
    tdir = prj.j("source", "competitors", "transcripts")
    os.makedirs(tdir, exist_ok=True)
    for handle, recs in by_handle.items():
        path = os.path.join(tdir, handle + ".json")
        d = jload(path) if os.path.isfile(path) else {"handle": handle, "reels": []}
        rows = d.get("reels") or []
        pos = {sc_of(r.get("url")): k for k, r in enumerate(rows)}
        for rec in recs:
            k = pos.get(sc_of(rec["url"]))
            if k is None:
                rows.append(rec)
            elif rows[k].get("error"):
                rows[k] = rec  # replace only a failed record; a good one or a ruling is never overwritten
        d["reels"] = rows
        d["n"] = len(rows)
        d["ok"] = sum(1 for r in rows if not r.get("error"))
        d["fail"] = d["n"] - d["ok"]
        jsave(path, d)
    shutil.rmtree(tmp, ignore_errors=True)
    prj.state["transcribe"] = {"at": now_utc(), "attempted": len(todo), "ok": ok, "failed": fail, "device": dev}
    prj.save_state()
    print("transcribe done: %d ok, %d failed" % (ok, fail))


# ---------------------------------------------------------------- compute
def step_compute(prj, args):
    man = prj.manifest()
    corpus = prj.corpus()
    n, d8 = man["count"], today()

    # Popularity metric (the earlier popularity_metric.py). comment_rate = comments / views from the
    # pull's own metadata; retrieved comment TEXT never feeds it.
    reels = []
    for sc, c in corpus.items():
        p = c["post"]
        is_cta, tok, rule = detect_cta((p.get("content") or {}).get("text") or "")
        e = p.get("engagement") or {}
        views, comments = e.get("views"), e.get("comments")
        reels.append({"shortcode": sc, "handle": c["handle"], "url": p.get("url"),
                      "published_at": p.get("published_at"), "views": views, "comments": comments,
                      "comment_rate": (comments / views) if (views and comments is not None) else None,
                      "is_cta": is_cta, "trigger_token": tok, "cta_rule": rule})
    by_h = {}
    for r in reels:
        by_h.setdefault(r["handle"], []).append(r)
    creators = {}
    for h, rs in by_h.items():
        non = [r["comment_rate"] for r in rs if not r["is_cta"] and r["comment_rate"] is not None]
        cta = [r["comment_rate"] for r in rs if r["is_cta"] and r["comment_rate"] is not None]
        base = statistics.median(non) if len(non) >= MIN_BASELINE_N else None
        usable = base is not None and base > 0
        cm = statistics.median(cta) if cta else None
        creators[h] = {
            "handle": h, "reels": len(rs), "cta_reels": sum(1 for r in rs if r["is_cta"]),
            "non_cta_reels": sum(1 for r in rs if not r["is_cta"]),
            "non_cta_rated_n": len(non), "cta_rated_n": len(cta),
            "non_cta_median_comment_rate": base, "cta_median_comment_rate": cm,
            "baseline_usable": usable,
            "baseline_note": None if usable else (
                "fewer than %d non-CTA reels with views>0 (n=%d)" % (MIN_BASELINE_N, len(non))
                if base is None else "non-CTA median comment rate is 0"),
            "creator_cta_lift_x": round(cm / base, 3) if (base and cm) else None,
        }
    for r in reels:
        c = creators[r["handle"]]
        b = c["non_cta_median_comment_rate"]
        r["creator_non_cta_median_rate"] = b
        r["benchmark_x"] = (round(r["comment_rate"] / b, 3)
                            if (c["baseline_usable"] and r["comment_rate"] is not None) else None)
        r["benchmark_unavailable_reason"] = None if r["benchmark_x"] is not None else (
            "no creator baseline: " + (c["baseline_note"] or "") if not c["baseline_usable"]
            else "reel has no views/comments metadata")
    idx = {r["shortcode"]: r for r in reels}
    breakouts, missing = [], []
    for b in man["breakouts"]:
        sc = sc_of(b["url"])
        if sc not in idx:
            missing.append(sc)
            continue
        row = dict(idx[sc], manifest_views=b.get("views"), manifest_mult=b.get("mult"))
        row["shares"], row["shares_source"] = shares_of(prj, corpus, sc)
        breakouts.append(row)
    ranked = sorted(breakouts, key=lambda r: (r["benchmark_x"] is None, -(r["benchmark_x"] or 0)))
    for i, r in enumerate(ranked, 1):
        r["rank_by_benchmark"] = i if r["benchmark_x"] is not None else None
    for i, r in enumerate(sorted([x for x in breakouts if x["comment_rate"] is not None],
                                 key=lambda x: -x["comment_rate"]), 1):
        r["rank_by_raw_rate"] = i
    for r in breakouts:
        r.setdefault("rank_by_raw_rate", None)
    pop_name = "Lead Magnet Popularity - Metric - %s.json" % d8
    jsave(os.path.join(prj.rb, pop_name), {
        "_note": "Lead-magnet popularity metric, computed by content-goldmine from the pull's own "
                 "metadata. No API calls. Every CTA comment rate is an UPPER BOUND: Instagram's "
                 "comment counter includes the creator's own automated replies.",
        "generated_at": now_utc(), "manifest": prj.state["manifest"],
        "metric": {"comment_rate": "post.engagement.comments / post.engagement.views",
                   "benchmark_x": "reel comment_rate / that creator's median NON-CTA comment_rate",
                   "min_baseline_n": MIN_BASELINE_N},
        "corpus": {"reels_total": len(reels), "creators": len(creators),
                   "cta_reels": sum(1 for r in reels if r["is_cta"]),
                   "weak_cta_reels": sum(1 for r in reels if (r["cta_rule"] or "").endswith("_weak")),
                   "non_cta_reels": sum(1 for r in reels if not r["is_cta"]),
                   "reels_without_rate": sum(1 for r in reels if r["comment_rate"] is None),
                   "creators_without_usable_baseline": sorted(
                       h for h, c in creators.items() if not c["baseline_usable"])},
        "breakouts_missing_from_corpus": missing,
        "breakout_ranking": ranked,
        "creator_summary": sorted(creators.values(), key=lambda c: c["handle"]),
        "corpus_cta_top50": sorted([r for r in reels if r["is_cta"] and r["benchmark_x"] is not None],
                                   key=lambda r: -r["benchmark_x"])[:50],
    })

    # Comment retrieval rate (the earlier retrieval_rate.py): comments fetched / the reel's count.
    rows = []
    for b in man["breakouts"]:
        sc = sc_of(b["url"])
        row = {"shortcode": sc, "handle": b["handle"], "url": b["url"],
               "meta_count_stats_leg": None, "meta_count_prism": None,
               "meta_count_frozen_corpus": ((((corpus.get(sc) or {}).get("post") or {})
                                             .get("engagement") or {}).get("comments")),
               "fetched": None, "pages": None, "completed": None, "credits": None,
               "rate": None, "warnings": None, "status": None}
        sp = prj.j("source", "winners", sc + "-stats.json")
        if os.path.isfile(sp):
            try:
                row["meta_count_stats_leg"] = jload(sp)["data"]["post"]["engagement"].get("comments")
            except Exception as e:
                row["status"] = "stats file unreadable: %r" % e
        cp = prj.j("source", "comments", sc + ".json")
        if not os.path.isfile(cp):
            row["status"] = "NO COMMENTS FILE"
            rows.append(row)
            continue
        try:
            d = jload(cp)
        except Exception as e:
            row["status"] = "comments file unreadable: %r" % e
            rows.append(row)
            continue
        dd, fx = d.get("data") or {}, d.get("_fetch") or {}
        row.update(meta_count_prism=(dd.get("post") or {}).get("comment_count"),
                   fetched=len(dd.get("comments") or []), pages=fx.get("pages"),
                   completed=fx.get("completed"), credits=fx.get("credits_total"),
                   warnings=dd.get("_warnings"), status="ok")
        den = row["meta_count_stats_leg"] or row["meta_count_prism"] or row["meta_count_frozen_corpus"]
        row["meta_count_used"] = den
        row["denominator_source"] = ("stats_leg" if row["meta_count_stats_leg"] else
                                     "prism" if row["meta_count_prism"] else
                                     "frozen_corpus" if row["meta_count_frozen_corpus"] else None)
        row["rate"] = round(row["fetched"] / den, 4) if den else None
        rows.append(row)
    ok = [r for r in rows if r["status"] == "ok" and r["rate"] is not None]
    rates = sorted(r["rate"] for r in ok)
    pick = lambda r: {"shortcode": r["shortcode"], "handle": r["handle"],
                      "meta_count": r.get("meta_count_used"), "fetched": r["fetched"], "rate": r["rate"]}
    ret_name = "Comment Retrieval - Rate - %s.json" % d8
    jsave(os.path.join(prj.rb, ret_name), {"summary": {
        "generated_at": now_utc(), "manifest": prj.state["manifest"], "reels": len(rows),
        "with_comments_file": sum(1 for r in rows if r["status"] == "ok"),
        "missing_comments_file": [r["shortcode"] for r in rows if r["status"] == "NO COMMENTS FILE"],
        "completed_true": sum(1 for r in rows if r["completed"] is True),
        "completed_false": sum(1 for r in rows if r["completed"] is False),
        "median_rate": statistics.median(rates) if rates else None,
        "mean_rate": (sum(rates) / len(rates)) if rates else None,
        "total_comments_fetched": sum(r["fetched"] or 0 for r in rows),
        "total_meta_count": sum(r.get("meta_count_used") or 0 for r in ok),
        "worst_5": [pick(r) for r in sorted(ok, key=lambda x: x["rate"])[:5]],
        "best_5": [pick(r) for r in sorted(ok, key=lambda x: -x["rate"])[:5]],
    }, "rows": rows})

    prj.state["compute"] = {"at": now_utc(), "popularity": pop_name, "retrieval": ret_name}
    prj.save_state()
    cta_n = sum(1 for r in breakouts if r["is_cta"])
    print("compute: %d of %d breakouts ranked (%d CTA, %d missing from the pull)" % (len(breakouts), n, cta_n, len(missing)))
    print("  %s\n  %s" % (pop_name, ret_name))


# ---------------------------------------------------------------- reads
def step_reads(prj, args):
    man = prj.manifest()
    comp = prj.state.get("compute") or die("run compute first (the packet carries the CTA verdicts).")
    pop = {r["shortcode"]: r for r in jload(os.path.join(prj.rb, comp["popularity"]))["breakout_ranking"]}
    corpus = prj.corpus()
    tx = prj.transcript_index()
    n, d8 = man["count"], today()
    rows = []
    for b in man["breakouts"]:
        sc = sc_of(b["url"])
        p = (corpus.get(sc) or {}).get("post") or {}
        r = pop.get(sc) or {}
        rows.append({
            "shortcode": sc, "handle": b["handle"], "url": b["url"], "mult": b.get("mult"),
            "views": b.get("views"), "duration_seconds": (p.get("content") or {}).get("duration_seconds"),
            "engine_hook": b.get("hook"), "engine_themes": b.get("themes"),
            "caption": (p.get("content") or {}).get("text") or "",
            "transcript": tx.get(sc, ("missing", ""))[1] or "",
            "is_cta": bool(r.get("is_cta")), "trigger_word": r.get("trigger_token"),
            "trigger_detection_rule": r.get("cta_rule"),
            "popularity_rank": {k: r.get(k) for k in ("rank_by_benchmark", "benchmark_x", "rank_by_raw_rate",
                                                      "comment_rate", "benchmark_unavailable_reason")},
        })
    cta_n = sum(1 for r in rows if r["is_cta"])
    name = "Goldmine Reads Packet - %d - %s.json" % (n, d8)
    out = {"_note": "Input for the three reads (references/reads.md). Read-only: never edit.",
           "manifest": prj.state["manifest"], "window": man["window"], "breakouts": n, "cta_breakouts": cta_n,
           "write_to": {"paps": "Lead Magnet PAPS - %d - %s.json" % (n, d8),
                        "topicmap": "Topic Map - %d - %s.json" % (n, d8),
                        "patternread": "Pattern Read - %d - %s.json" % (n, d8)},
           "reels": rows}
    # Resume (plan kept this pull's reads entry): keep its names, so a later day never points the run
    # at new blank files. A new pull has no entry (plan drops it) and gets today's names.
    prev = prj.state.get("reads") or {}
    name, out["write_to"] = prev.get("packet") or name, prev.get("expected") or out["write_to"]
    jsave(os.path.join(prj.rb, name), out)
    # Pre-fill the three reads with every mechanical field, so Claude writes only the judgement
    # fields (the nulls and empty lists). A file that already exists is never overwritten.
    mech = ("shortcode", "handle", "url", "mult", "views", "duration_seconds", "trigger_word",
            "trigger_detection_rule")
    stubs = {
        "paps": {"generated_at": now_utc(), "window": man["window"],
                 "corpus": {"breakouts_total": n, "cta_breakouts": cta_n, "non_cta_breakouts": n - cta_n},
                 "paps": [dict({k: r[k] for k in mech}, topic=None, problem=None, agitation=None,
                               promise=None, solution_delivery=None, source_surface=None,
                               popularity_rank=r["popularity_rank"], note=None)
                          for r in rows if r["is_cta"]],
                 "non_cta": [r["shortcode"] for r in rows if not r["is_cta"]]},
        "topicmap": {"schema": "goldmine-topic-map/1", "pull": {"manifest": prj.state["manifest"], "n": n},
                     "read": None, "no_theme_label": "(no engine theme)", "topics": [],
                     "reels": {r["shortcode"]: {"topic": None, "angle": None} for r in rows}},
        "patternread": {"schema": "goldmine-pattern-read/1",
                        "pull": {"manifest": prj.state["manifest"], "n": n, "cta_n": cta_n},
                        "read": None, "formulas": [], "lm_types": [], "threads": [],
                        "reels": {r["shortcode"]: ({"formula": None, "lm_type": None, "magnet": None}
                                                   if r["is_cta"] else {"formula": None}) for r in rows}},
    }
    made = []
    for k, d in stubs.items():
        path = os.path.join(prj.rb, out["write_to"][k])
        if not os.path.isfile(path):
            jsave(path, d)
            made.append(out["write_to"][k])
    prj.state["reads"] = {"packet": name, "expected": out["write_to"], "passed": False}
    prj.save_state()
    print("reads packet: %s (%d breakouts, %d CTA, %d without transcript)"
          % (name, n, cta_n, sum(1 for r in rows if not r["transcript"])))
    print("Write, into reel-build/: " + ", ".join(out["write_to"].values()))
    if made:
        print("Pre-filled with the mechanical fields: %s. Fill in only the null and empty fields."
              % ", ".join(made))


def step_check_reads(prj, args):
    man = prj.manifest()
    rd = prj.state.get("reads") or die("run the reads step first.")
    exp = dict(rd["expected"])
    for k in ("paps", "topicmap", "patternread"):
        if args.get(k):
            exp[k] = os.path.basename(args[k])
    packet = jload(os.path.join(prj.rb, rd["packet"]))
    want = {r["shortcode"] for r in packet["reels"]}
    cta = {r["shortcode"] for r in packet["reels"] if r["is_cta"]}
    errs = []

    def load(k):
        path = os.path.join(prj.rb, exp[k])
        if not os.path.isfile(path):
            errs.append("%s: file missing (%s)" % (k, exp[k]))
            return None
        try:
            return jload(path)
        except Exception as e:
            errs.append("%s: not valid JSON (%s)" % (k, e))
            return None

    def ids(d, key, k):
        out = set()
        for i, x in enumerate(d.get(key) or []):
            if not isinstance(x, dict) or not x.get("id") or not x.get("name"):
                errs.append("%s: %s[%d] needs id and name" % (k, key, i))
                continue
            if x["id"] in out:
                errs.append("%s: duplicate %s id %s" % (k, key, x["id"]))
            out.add(x["id"])
        if not out:
            errs.append("%s: %s is empty" % (k, key))
        return out

    paps = load("paps")
    no_offer = []
    if paps is not None:
        got = set()
        for i, r in enumerate(paps.get("paps") or []):
            miss = [f for f in ("shortcode", "handle", "url", "trigger_word", "topic", "problem",
                                "agitation", "promise", "solution_delivery", "source_surface") if f not in r]
            if miss:
                errs.append("paps: row %d (%s) lacks %s" % (i, r.get("shortcode"), ", ".join(miss)))
            if not r.get("topic") or not r.get("source_surface"):
                errs.append("paps: row %s needs a topic and a source_surface" % r.get("shortcode"))
            if not r.get("solution_delivery") or not r.get("promise"):
                no_offer.append(r.get("shortcode"))  # allowed only for an engagement ask (lm_none)
            got.add(r.get("shortcode"))
        if got - want:
            errs.append("paps: rows not in the manifest: %s" % sorted(got - want)[:10])
        if cta - got:
            errs.append("paps: CTA breakouts with no row: %s" % sorted(cta - got)[:10])
        if (got & want) - cta:
            errs.append("paps: rows for breakouts that are not CTAs: %s" % sorted((got & want) - cta)[:10])
        top = newest(glob.glob(os.path.join(prj.rb, "Lead Magnet PAPS - * - *.json")))
        if top != exp["paps"]:
            errs.append("paps: the dashboard reads the newest Lead Magnet PAPS file in reel-build/, "
                        "which is %s, not this run's %s" % (top, exp["paps"]))
        c = paps.get("corpus") or {}
        if (c.get("breakouts_total"), c.get("cta_breakouts")) != (len(want), len(cta)):
            errs.append("paps: corpus must be {breakouts_total: %d, cta_breakouts: %d, non_cta_breakouts: %d}"
                        % (len(want), len(cta), len(want) - len(cta)))

    tm = load("topicmap")
    topic_ids = set()
    if tm is not None:
        if tm.get("schema") != "goldmine-topic-map/1":
            errs.append("topicmap: schema must be goldmine-topic-map/1")
        topic_ids = ids(tm, "topics", "topicmap")
        themes = set((jload(prj.j("analysis-data.json")).get("meta") or {}).get("themes") or [])
        shelf = tm.get("no_theme_label") or "(no engine theme)"
        for t in tm.get("topics") or []:
            if not t.get("summary"):
                errs.append("topicmap: topic %s needs a summary" % t.get("id"))
            if themes and t.get("theme") not in themes | {shelf}:
                errs.append("topicmap: topic %s theme %r is not an engine theme (never invent one; use %r)"
                            % (t.get("id"), t.get("theme"), shelf))
        reels = tm.get("reels") or {}
        if want - set(reels):
            errs.append("topicmap: breakouts with no row: %s" % sorted(want - set(reels))[:10])
        for sc, v in reels.items():
            if sc not in want:
                errs.append("topicmap: row %s is not in the manifest" % sc)
            elif v.get("topic") not in topic_ids or not v.get("angle"):
                errs.append("topicmap: row %s needs a known topic id and an angle" % sc)

    pr = load("patternread")
    if pr is not None:
        if pr.get("schema") != "goldmine-pattern-read/1":
            errs.append("patternread: schema must be goldmine-pattern-read/1")
        f_ids = ids(pr, "formulas", "patternread")
        lm_ids = ids(pr, "lm_types", "patternread") if (cta or pr.get("lm_types")) else set()
        ids(pr, "threads", "patternread")
        seen = {}
        for th in pr.get("threads") or []:
            bad = [t for t in th.get("topics") or [] if topic_ids and t not in topic_ids]
            if bad:
                errs.append("patternread: thread %s names unknown topics %s" % (th.get("id"), bad))
            for t in th.get("topics") or []:
                seen[t] = seen.get(t, 0) + 1
        if topic_ids:
            off = sorted(t for t in topic_ids if seen.get(t, 0) != 1)
            if off:
                errs.append("patternread: every topic sits in exactly one thread; not so for %s" % off[:10])
        reels = pr.get("reels") or {}
        if want - set(reels):
            errs.append("patternread: breakouts with no row: %s" % sorted(want - set(reels))[:10])
        for sc, v in reels.items():
            if sc not in want:
                errs.append("patternread: row %s is not in the manifest" % sc)
                continue
            if v.get("formula") not in f_ids:
                errs.append("patternread: row %s needs a known formula id" % sc)
            if sc in cta and (v.get("lm_type") not in lm_ids or not v.get("magnet")):
                errs.append("patternread: CTA row %s needs a known lm_type and a magnet" % sc)
            if v.get("lm_type") == "lm_none" and v.get("magnet") != "engagement ask":
                errs.append('patternread: row %s is lm_none, so its magnet is "engagement ask" '
                            "(never invent a lead magnet)" % sc)
    pr_reels = (pr or {}).get("reels") or {}
    for sc in no_offer:
        if (pr_reels.get(sc) or {}).get("lm_type") != "lm_none":
            errs.append("paps: row %s needs promise and solution_delivery (never null), unless it is an "
                        "engagement ask with no offer: lm_type lm_none in the Pattern Read" % sc)

    if errs:
        print("check-reads: FAIL (%d)" % len(errs))
        for e in errs[:40]:
            print("  - " + e)
        rd["passed"] = False
        prj.save_state()
        sys.exit(1)
    # Proven hooks: the top 3 breakouts by multiplier (ties on shortcode), each with its opening
    # line and its Pattern Read formula. Shape: ../references/reads.md, "Proven Hooks".
    fm = {f["id"]: f for f in pr["formulas"]}
    lines = {sc_of(b["url"]): b.get("hook_line") for b in man["breakouts"]}
    top3 = sorted(packet["reels"], key=lambda r: (-(r.get("mult") or 0), r["shortcode"] or ""))[:3]
    ph = rd["packet"].replace("Goldmine Reads Packet", "Proven Hooks", 1)
    jsave(os.path.join(prj.rb, ph), {
        "schema": "goldmine-proven-hooks/1", "generated_at": now_utc(),
        "packet": rd["packet"], "patternread": exp["patternread"],
        "hooks": [{"shortcode": r["shortcode"], "handle": r["handle"], "url": r["url"], "mult": r["mult"],
                   "views": r["views"], "opening_line": lines.get(r["shortcode"]),
                   "formula": {k: fm[pr["reels"][r["shortcode"]]["formula"]].get(k)
                               for k in ("id", "name", "template")}} for r in top3]})
    rd.update(passed=True, paps=exp["paps"], topicmap=exp["topicmap"], patternread=exp["patternread"],
              proven_hooks=ph, checked_at=now_utc())
    prj.save_state()
    print("check-reads: PASS (%d breakouts, %d CTA). Recorded as this run's reads." % (len(want), len(cta)))
    print("Proven hooks: %s (%d rows)" % (ph, len(top3)))


def newest(paths):
    """Base name of the newest reel-build file by the MM.DD.YY in its name, then by name: the same
    pick the dashboard assembler makes, so a plain sort's '- 9 -' over '- 12 -' never decides."""
    def key(p):
        m = re.findall(r"(\d\d)\.(\d\d)\.(\d\d)", os.path.basename(p))
        return ((m[-1][2], m[-1][0], m[-1][1]) if m else ("", "", ""), os.path.basename(p))
    return os.path.basename(sorted(paths, key=key)[-1]) if paths else None


# ---------------------------------------------------------------- dashboard
# The page and its assembler come from the public repo at a pinned tag, never bundled.
DASH_TAG = "v0.2.1"  # pinned with its commit (the tarball's pax comment); bump both together
DASH_SHA = "c33bf49cdc9348161c2c65dcc12559543d0fe27e"
DASH_URL = "https://github.com/joeoliveimpact/content-goldmine-dashboard/archive/refs/tags/%s.tar.gz"
OFFLINE = ("Could not download the dashboard: no internet connection, or GitHub did not answer. "
           "Everything built so far is saved. Check the connection, then run the dashboard step again.")
LAYOUT = ("The downloaded dashboard is not laid out the way the pinned version is, so it was not used. "
          "Nothing was changed. Tell the plugin's maintainer.")
LONG_PATH = ("The dashboard downloaded, but Windows could not open it because its folder path is too long "
             "(%d characters; Windows stops at 260). Everything built so far is saved. Running the step again "
             "fails the same way, so tell the plugin's maintainer.")
NOT_LANDED = ("The dashboard download did not land: it finished, but no file was saved. Everything built so far "
              "is saved. Run the dashboard step again later.")


def dash_cache(tag):
    return os.path.join(os.path.expanduser("~"), ".cache", "shortform-superengine", "goldmine-dashboard", tag)


def long_ok(path):
    r"""Windows: the \\?\ form of the full path, which Python can open past 260 characters. A network
    (UNC) path, and any other system, gets the path back as it is."""
    p = os.path.abspath(path)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\") else path


def download(url, dest):
    """curl, never Python HTTPS: python.org's macOS builds ship without certificates."""
    if not shutil.which("curl"):
        die("curl is not installed, so the dashboard cannot be downloaded. Install curl, then run "
            "the dashboard step again.", 4)
    try:
        p = subprocess.run(["curl", "-fsSL", "--retry", "2", "-o", dest, url], capture_output=True, timeout=300)
    except (subprocess.TimeoutExpired, OSError):
        die(OFFLINE, 5)
    if p.returncode != 0:
        die(OFFLINE, 5)
    if not os.path.isfile(dest):
        n = len(os.path.abspath(dest))
        if os.name == "nt" and n >= 260 and not dest.startswith("\\\\?\\"):
            die(LONG_PATH % n, 9)  # curl saved it where plain Python cannot look
        die(NOT_LANDED, 5)


def fetch_dashboard():
    """The pinned dashboard, verified and unpacked in the cache. Returns its folder."""
    cache, top = dash_cache(DASH_TAG), "content-goldmine-dashboard-" + DASH_TAG.lstrip("v")
    if len(os.path.abspath(cache)) > 150:
        # ponytail: a fixed margin for the deepest file the unpack and the build touch under the cache
        # (about 90 characters today); measure the tarball if it nests deeper. Past it, every path in
        # here takes the \\?\ form, so Windows' 260-character limit never applies.
        cache = long_ok(cache)
    root = os.path.join(cache, top)
    if os.path.isfile(os.path.join(root, "goldmine_dashboard.py")):
        return root  # verified when it was unpacked
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="unpack-", dir=cache)
    try:
        tgz = os.path.join(tmp, "dashboard.tar.gz")
        download(DASH_URL % DASH_TAG, tgz)
        try:
            with tarfile.open(tgz, "r:gz") as tf:
                members = tf.getmembers()
                if tf.pax_headers.get("comment") != DASH_SHA:
                    die("The downloaded dashboard is not the pinned version (its commit stamp does not "
                        "match), so it was not used. Nothing was changed. Tell the plugin's maintainer.", 6)
                # exactly one top folder, the pinned one; no absolute path, no "..", only files and folders
                bad = [m.name for m in members
                       if m.name.split("/")[0] != top or ".." in m.name.replace("\\", "/").split("/")
                       or os.path.isabs(m.name) or ":" in m.name or not (m.isfile() or m.isdir())]
                if bad or not members:
                    die(LAYOUT, 7)
                if tmp.startswith("\\\\?\\"):  # a \\?\ path is read literally: give tarfile native separators
                    for m in members:
                        m.name = m.name.replace("/", "\\")
                tf.extractall(tmp, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        except (tarfile.TarError, OSError, EOFError):
            die(LAYOUT, 7)
        if os.path.isdir(root):
            shutil.rmtree(root)  # a half-unpacked folder from an interrupted run
        os.replace(os.path.join(tmp, top), root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.isdir(tmp):
            print("NOTE: could not remove the temporary folder %s. Nothing in it is needed; it is safe to "
                  "delete." % tmp)
    return root


def step_dashboard(prj, args):
    man = prj.manifest()
    if not (prj.state.get("reads") or {}).get("passed"):
        die("the reads have not passed check-reads, and the dashboard is only built from reads that "
            "passed. Finish the reads, run check-reads, then run the dashboard step.")
    root = fetch_dashboard()
    out = prj.j("visuals", "Content Goldmine Dashboard - %s.html" % today())
    os.makedirs(os.path.dirname(out), exist_ok=True)
    extras = os.path.join(prj.rb, "dashboard-extras.json")
    # Comment Mining counts only comments fetched for this pull: the manifest's UTC freeze day is the cut.
    jsave(extras, {"comments_since": (man.get("generated_at") or "")[:10]})
    log = os.path.join(prj.rb, "dashboard-build.log")
    try:
        p = subprocess.run([sys.executable, os.path.join(root, "goldmine_dashboard.py"), "--project", prj.p,
                            "--workspace", prj.p, "--out", out, "--extras", extras],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                           env=dict(os.environ, PYTHONPATH=root) if root.startswith("\\\\?\\") else None)
        code, text = p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, OSError) as e:
        code, text = -1, repr(e)
    with open(log, "w", encoding="utf-8") as f:
        f.write(text)
    if code != 0 or not os.path.isfile(out):
        err = [l[6:].strip() for l in text.splitlines() if l.startswith("ERROR:")]
        die("The dashboard could not be built%s. Everything else is saved; the full output is in "
            "reel-build/dashboard-build.log." % ((": " + err[-1]) if err else ""), 8)
    prj.state["dashboard"] = {"at": now_utc(), "html": out, "tag": DASH_TAG}
    prj.save_state()
    print("Dashboard saved: " + out)
    print("NEXT: publish this saved file as an Artifact per references/publish.md and store the link "
          "under goldmine.* in state. If publishing fails, give the client this path instead.")


# ---------------------------------------------------------------- main
STEPS = {"plan": step_plan, "fetch": step_fetch, "transcribe": step_transcribe,
         "compute": step_compute, "reads": step_reads, "check-reads": step_check_reads,
         "dashboard": step_dashboard}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in STEPS:
        print(__doc__)
        sys.exit(1)
    opts, rest = {}, sys.argv[3:]
    while rest:
        a = rest.pop(0)
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            opts[k] = v if v else (rest.pop(0) if rest else None)
    STEPS[sys.argv[1]](Project(sys.argv[2]), opts)
