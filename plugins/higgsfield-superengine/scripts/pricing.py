#!/usr/bin/env python3
"""pricing.py - turn a hf_rest.py estimate record into a spend verdict (higgsfield-superengine). Stdlib only, 3.9+.

  python pricing.py price <record.json>   print ONE JSON line (the verdict) and nothing else
  python pricing.py --selftest            offline checks: all 82 table endpoints, the 09.24 replay, cap math

Prices are LIST dollars from pricing-table.json (next to this file: the Phase 0.3 table, byte-identical).
Fail closed: any doubt asks, and a doubtful number is never returned as "usd".

Verdict (a JSON object):
  ask            true = the spend guard must ask the client (a real click), whatever the numbers say
  usd            conservative dollars to count against the cap: a number > 0 when ask is false, else null
  display_usd    the figure to show the client, and to reserve if they approve an ask. With ask true it can be
                 below the real charge; null = no figure at all
  basis          fixed (/estimate usd + discount.usd) | formula (Seedance tokens) | per_second | ceiling | none
  code           priced | always_ask | unmeasured | unpriced | audio_unproven | option_unpriced |
                 not_upper_bound | bad_param | unexpected_response | not_in_table | invalid_record | unreadable |
                 table_error | usage | internal_error   (only "priced" has ask false)
  reason         one ASCII line: the math, or why it asks
  endpoint       the record's endpoint (null if unusable)
  record_sha256  sha256 of the exact bytes priced (price CLI / price_bytes only)
Exit codes (price): 0 = ask false, 1 = ask true (any reason), 2 = usage error. No JSON on stdout = treat as ask.

Cap math (pure; ledger.py supplies the numbers, see BUILD-NOTES 3.2):
  cap_usd(balance)                   min($5, 25% of the known balance); None if the balance is unknown
  fits_cap(usd, spent_24h, balance)  True / False; None = balance unknown (the ledger's own rule decides)
"""
import hashlib, json, math, re, sys
from decimal import Decimal
from pathlib import Path

TABLE_PATH = Path(__file__).with_name("pricing-table.json")
CAP_USD, CAP_SHARE = 5.0, 0.25
BASIS = {"estimate_usd": "fixed", "seedance_formula": "formula", "per_second": "per_second", "ceiling": "ceiling"}
MONEY = re.compile(r"[0-9]+(\.[0-9]+)?")  # /estimate sends dollars as plain decimal text, e.g. "0.015"
# Joe 09.28.26: reference-video cost is unknown on these two, so they always ask (not_upper_bound), by name, whatever
# a rebuilt table says about upper_bound
NOT_UPPER_BOUND = ("minimax/h3/reference-to-video", "alibaba/wan-3.0/reference-to-video")
# Joe 09.28.26: every Sunburst endpoint asks ("unmeasured") until one real run is measured. After that run, set this to
# True: Sunburst is then priced silently on the Flare grid, exactly like Flare.
SUNBURST_MEASURED = False
# Joe 09.28.26: an option whose cost is not in the price asks when set. Keyed by endpoint prefix ("alibaba/wan-3.0/"
# leaves out Wan 3.0 Prime, whose live /estimate quote covers the exact body). Each option maps to its "off" value: off
# = absent, null, or that value with the same JSON type (false, ""); anything else, an unexpected type included, is set.
UNPRICED_OPTIONS = {"alibaba/wan-3.0/": {"enable_thinking": False},
                    "marketing-studio/image/flare": {"enhance_prompt": False, "preset_id": ""},
                    "marketing-studio/image/sunburst": {"enhance_prompt": False, "preset_id": ""}}
_table = None


class Doubt(Exception):
    """The table can't vouch for a price: the verdict asks."""

    def __init__(self, code, reason):
        super().__init__(code)
        self.code, self.reason = code, reason


def _no_constant(name):
    raise ValueError(f"{name} is not valid JSON")


def _loads(text):
    return json.loads(text, parse_float=Decimal, parse_constant=_no_constant)  # exact decimals; NaN refused


def _short(v):
    return json.dumps(v, default=str)[:40]


def table():
    global _table
    if _table is None:
        t = _loads(TABLE_PATH.read_bytes().decode("utf-8"))["endpoints"]
        if not isinstance(t, dict):
            raise ValueError("endpoints is not an object")
        _table = t
    return _table


def _money(v, what):
    """A dollar amount from /estimate (decimal text or a JSON number), finite and >= 0, as a Decimal."""
    d = None
    if isinstance(v, str):
        d = Decimal(v) if MONEY.fullmatch(v) else None
    elif isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
        d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
    if d is None or not d.is_finite() or d < 0 or not math.isfinite(float(d)):
        raise Doubt("unexpected_response", f"/estimate {what} is not a dollar amount ({_short(v)})")
    return d


def _pick(d, key, what):
    if isinstance(key, str) and key in d:
        return d[key]
    raise Doubt("bad_param", f"{what} {_short(key)} has no price in the table")


def _seconds(p):
    v = p.get("duration")
    if isinstance(v, int) and not isinstance(v, bool) and v >= 1:
        return v
    raise Doubt("bad_param", f"duration must be a whole number of seconds (got {_short(v)})")


def _count(p, key):
    v = p.get(key)
    if v is None:
        return 0
    if isinstance(v, list):
        return len(v)
    raise Doubt("bad_param", f"{key} must be a list (got {_short(v)})")


def _has_video(p):
    return any("video" in str(k).lower() and v not in (None, "", [], {}) for k, v in p.items())


def seedance_usd(pixels, seconds, rate, multiplier=1):
    """The Seedance token formula: ceil(pixels x seconds x 24 / 1024) tokens x rate per 1,000 tokens.
    Returns (dollars as Decimal, tokens)."""
    tokens = -(-(pixels * seconds * 24) // 1024)
    return Decimal(tokens) * Decimal(rate) / 1000 * Decimal(multiplier), tokens


def _input_s(known, mx):
    """Input video seconds to bill: the uploaded length rounded UP to whole seconds (capped at the table's max), or
    the max when the length is unknown."""
    if known is None:
        return mx, " (input video length unknown: the table's max)"
    return min(mx, math.ceil(known)), f" (input video {known} s, from upload)"


def _rule_raw(r, p, resp, known=None):
    rule = r["rule"]
    if rule == "estimate_usd":  # the live quote for this exact body; list = usd + discount.usd (usd alone = promo)
        if not isinstance(resp, dict) or resp.get("type") != "estimate":
            raise Doubt("unexpected_response", "expected a fixed /estimate quote (type estimate)")
        usd, disc = _money(resp.get("usd"), "usd"), resp.get("discount")
        disc = Decimal(0) if disc is None else _money(disc.get("usd") if isinstance(disc, dict) else None,
                                                      "discount.usd")
        if usd + disc <= 0:
            raise Doubt("unexpected_response", "a $0 list price is not trusted")
        return usd + disc, f"list ${usd + disc} = /estimate usd {usd} + discount.usd {disc}"
    if rule == "seedance_formula":  # output W x H = the tier's pixel ceiling; audio and image refs are free
        res = p.get("resolution")
        px, rate = _pick(r["pixel_ceiling"], res, "resolution"), _pick(r["rate_per_1k_tokens"], res, "resolution")
        mx = r["max_input_video_s"]
        # input video at 1.0x (Joe); its length from the upload record, else the table's max
        inp, src = _input_s(known, mx) if _has_video(p) else (0, "")
        g = r["generated_s_from"]
        if g == "duration":
            gen = _seconds(p)
        elif str(g).startswith("source_video"):
            gen = max(4, inp)  # video-edit: the output is the processed source (normalized 4..30 s)
        else:
            raise Doubt("table_error", f"unknown generated_s_from {_short(g)}")
        usd, tokens = seedance_usd(px, inp + gen, rate, r["video_input_multiplier_applied"])
        return usd, (f"{res}: {tokens} tokens = ceil({px} px x ({inp} s input video + {gen} s) x 24 / 1024) x "
                     f"${rate}/1k tokens{src}")
    if rule == "per_second":
        res = p.get("resolution")
        rate = _pick(r["usd_per_s"], res, "resolution")
        if r["seconds_from"] == "duration":
            s, how = _seconds(p), ""
        elif str(r["seconds_from"]).startswith("input video"):
            s, how = _input_s(known, r["max_seconds"])
        else:
            raise Doubt("table_error", f"unknown seconds_from {_short(r['seconds_from'])}")
        usd, how = rate * s, f"{res}: ${rate}/s x {s} s{how}"
        extra = r.get("extra_usd_per_image_ref_over_5")
        if extra is not None:
            n = max(0, _count(p, "image_urls") - 5)
            usd, how = usd + extra * n, how + f" + {n} image refs over 5 x ${extra}"
        return usd, how
    if rule == "ceiling":
        if "usd_per_image" in r:  # Flare / Sunburst: token-metered, so a per-tier ceiling reconciled afterwards
            res, q = p.get("resolution"), p.get("quality")
            per = _pick(_pick(r["usd_per_image"], res, "resolution"), q, "quality")
            n, add, text = _count(p, "image_urls"), r["plus_usd_per_image_url"], r["plus_usd_text"]
            return per + add * n + text, (f"{res}/{q} ceiling ${per} + {n} image_urls x ${add} + text ${text}; "
                                          "reconcile by re-reading the balance")
        s = r["max_seconds"]
        return r["usd_per_s"] * s, f"rough ceiling ${r['usd_per_s']}/s x {s} s of input video (display only)"
    raise Doubt("table_error", f"unknown rule {_short(rule)}")


def _rule_usd(r, p, resp, known=None):
    """(dollars, how) for the endpoint's table rule, or raise Doubt. Only estimate_usd reads the /estimate answer."""
    usd, how = _rule_raw(r, p, resp, known)
    if not (usd.is_finite() and usd > 0 and math.isfinite(float(usd))):
        raise Doubt("bad_param", "the price is not a positive finite number")
    return usd, how


def _unproven(r, p):
    """The table's unproven_when rule, fail-closed: a condition only clears when the body sets that key to a
    different value of the same JSON type (generate_audio: false). "false", 0 or null do not clear it."""
    uw = r.get("unproven_when")
    if uw is None:
        return False
    if not isinstance(uw, dict) or not uw:
        return True
    return all(not (k in p and type(p[k]) is type(v) and p[k] != v) for k, v in uw.items())


def _options_on(endpoint, p):
    """The UNPRICED_OPTIONS set in the merged body (so a default that is on would count as set)."""
    return [k for pre, opts in UNPRICED_OPTIONS.items() if endpoint.startswith(pre) for k, off in opts.items()
            if p.get(k) is not None and not (type(p[k]) is type(off) and p[k] == off)]


def _v(ask, usd, shown, basis, code, reason, endpoint):
    return {"ask": ask, "usd": None if ask or usd is None else float(usd),
            "display_usd": None if shown is None else float(shown), "basis": basis, "code": code,
            "reason": reason[:300], "endpoint": endpoint[:200] if isinstance(endpoint, str) else None}


def _verdict(endpoint, params, http, response, known=None):
    if not isinstance(endpoint, str) or not isinstance(params, dict):
        return _v(True, None, None, "none", "invalid_record", "the record has no usable endpoint or params", endpoint)
    try:
        r = table().get(endpoint)
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as e:
        return _v(True, None, None, "none", "table_error", f"pricing-table.json unusable ({type(e).__name__})",
                  endpoint)
    if not isinstance(r, dict):
        return _v(True, None, None, "none", "not_in_table", "this endpoint is not in the pricing table", endpoint)
    basis = BASIS.get(r.get("rule"))
    if basis is None:
        return _v(True, None, None, "none", "table_error", f"unknown rule {_short(r.get('rule'))}", endpoint)
    if isinstance(http, bool) or not isinstance(http, int) or not (http == 200 or 500 <= http <= 599):
        return _v(True, None, None, basis, "invalid_record", f"http {_short(http)} is not 200 or 5xx", endpoint)
    p = {**r["defaults"], **params}  # an omitted field is priced at its schema default, never the cheapest tier
    shown, how, doubt = None, "", None
    try:
        shown, how = _rule_usd(r, p, response if http == 200 else None, known)
    except Doubt as d:
        doubt = d
    if r.get("always_ask"):
        return _v(True, None, shown, basis, "always_ask", "always ask: /estimate fails for this endpoint, so its "
                  f"price is unknown (Joe 09.26.26); {how or doubt.reason}", endpoint)
    if "sunburst" in endpoint and not SUNBURST_MEASURED:
        return _v(True, None, shown, basis, "unmeasured", "unmeasured: no real Sunburst charge has been measured yet, "
                  f"so it asks until one is (Joe 09.28.26); {how or doubt.reason}", endpoint)
    if http != 200:
        return _v(True, None, shown, basis, "unpriced", f"/estimate answered HTTP {http}: no price, so ask"
                  + (f"; {how}" if how else ""), endpoint)
    if doubt:
        return _v(True, None, None, basis, doubt.code, doubt.reason, endpoint)
    if basis != "fixed" and (not isinstance(response, dict) or response.get("type") != "description"):
        return _v(True, None, None, basis, "unexpected_response", "expected the /estimate formula description "
                  "(type description) this rule was built from", endpoint)
    if _unproven(r, p):
        return _v(True, None, shown, basis, "audio_unproven", f"{', '.join(sorted(r['unproven_when']))} is not "
                  "false: the audio-on cost is unproven until the 7.2 smoke test (Joe 09.26.26); the figure is the "
                  f"audio-off price; {how}", endpoint)
    on = _options_on(endpoint, p)
    if on:
        return _v(True, None, shown, basis, "option_unpriced", f"unpriced option set ({', '.join(on)}): that cost is "
                  f"not in the price, so ask (Joe 09.28.26); the figure is the price without it; {how}", endpoint)
    if endpoint in NOT_UPPER_BOUND or (r.get("upper_bound") is not True and basis != "ceiling"):
        return _v(True, None, shown, basis, "not_upper_bound", "part of this endpoint's cost is unknown, so the price "
                  f"is not an upper bound; {how}", endpoint)
    return _v(False, shown, shown, basis, "priced", how, endpoint)


def price(endpoint, params, http=200, response=None, input_video_s=None):
    """The verdict for one request: endpoint, request body, and the /estimate answer (http 200 + JSON, or a 5xx).
    input_video_s: the input videos' total length from hf_rest's upload records (None = unknown: the table's max)."""
    known = input_video_s if isinstance(input_video_s, (int, float, Decimal)) and not isinstance(input_video_s, bool) \
        and math.isfinite(float(input_video_s)) and 0 < float(input_video_s) <= 3600 else None
    try:
        return _verdict(endpoint, params, http, response, None if known is None else float(known))
    except Exception as e:  # fail closed: a bug or a malformed table entry asks, never allows
        return _v(True, None, None, "none", "internal_error", f"unexpected {type(e).__name__}", endpoint)


def price_record(rec):
    """The verdict for a parsed hf_rest.py estimate record (CONTRACT v1, Phase 3.1 BUILD-NOTES)."""
    if not isinstance(rec, dict) or type(rec.get("v")) is not int or rec["v"] != 1 or \
            rec.get("kind") != "hf-superengine-estimate":
        return _v(True, None, None, "none", "invalid_record", "not a v1 hf-superengine estimate record",
                  rec.get("endpoint") if isinstance(rec, dict) else None)
    return price(rec.get("endpoint"), rec.get("params"), rec.get("http"), rec.get("response"),
                 rec.get("input_video_s"))


def price_bytes(raw):
    """The verdict for the exact record bytes, plus their sha256 (bind the hook's stamp to this price)."""
    try:
        v = price_record(_loads(raw.decode("utf-8")))
    except (ValueError, RecursionError):  # not UTF-8, not JSON, NaN/Infinity, nested too deep
        v = _v(True, None, None, "none", "invalid_record", "the record is not UTF-8 JSON", None)
    v["record_sha256"] = hashlib.sha256(raw).hexdigest()
    return v


def cap_usd(balance):
    """The silent cap: min($5, 25% of the known balance). None if the balance is unknown (None).
    A balance that is not a finite number, or is negative, gives 0.0: nothing runs silently."""
    if balance is None:
        return None
    if isinstance(balance, bool) or not isinstance(balance, (int, float, Decimal)) or \
            not math.isfinite(float(balance)):
        return 0.0
    return max(0.0, min(CAP_USD, CAP_SHARE * float(balance)))


def _amount(x):
    if isinstance(x, bool) or not isinstance(x, (int, float, Decimal)):
        return None
    x = float(x)
    return x if math.isfinite(x) and x >= 0 else None


def fits_cap(usd, spent_24h, balance):
    """True if spending usd now keeps the trailing-24 h total within the cap (at the cap is within). False if not,
    or if usd / spent_24h is not a finite amount >= 0. None if the balance is unknown: the ledger's rule decides."""
    u, s = _amount(usd), _amount(spent_24h)
    if u is None or s is None:
        return False
    cap = cap_usd(balance)
    if cap is None:
        return None
    return round(s + u, 6) <= round(cap, 6)  # micro-dollars, so float noise can't flip an exactly-at-the-cap case


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    try:
        if len(argv) != 2 or argv[0] != "price":
            v, code = _v(True, None, None, "none", "usage", "usage: python pricing.py price <record.json> | "
                         "--selftest", None), 2
        else:
            try:
                v = price_bytes(Path(argv[1]).read_bytes())
            except OSError as e:
                v = _v(True, None, None, "none", "unreadable", f"cannot read the record ({type(e).__name__})", None)
            code = 1 if v["ask"] else 0
        line = json.dumps(v, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    except Exception as e:  # still one JSON line, and it asks
        line, code = json.dumps({"ask": True, "usd": None, "display_usd": None, "basis": "none",
                                 "code": "internal_error", "reason": f"unexpected {type(e).__name__}",
                                 "endpoint": None}), 1
    print(line)
    return code


def selftest():
    """Offline: the shipped table, synthetic records, and a temp folder for the CLI checks. No network, no key."""
    import collections, shutil, subprocess, tempfile
    results, seen = [], []

    def check(name, ok, detail=""):
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))

    def P(ep, params, http=200, resp=None):
        v = price(ep, params, http, resp)
        seen.append(v)
        return v

    def run(name, fn):
        try:
            fn()
        except Exception as e:  # a crash inside a group is a FAIL line, never a traceback
            check(f"{name} crashed: {type(e).__name__}: {str(e)[:120]}", False)

    FIX = {"type": "estimate", "credits": "1.600", "usd": "0.100",
           "discount": {"percentage": "50.00", "credits": "1.600", "usd": "0.100"}}
    DESC = {"type": "description", "pricing_description": "selftest"}
    E = lambda usd, disc=None: {"type": "estimate", "usd": usd, "discount": None if disc is None else {"usd": disc}}
    T = table()

    def resp_for(ep):
        return FIX if T[ep]["rule"] == "estimate_usd" else DESC

    # the 6 always-ask Kling endpoints and their display ceilings ($0.42/s x max input s), fixed here on purpose:
    # a table edit that drops always_ask must fail this selftest
    ASK6 = {"kling-video/motion-control/pro": 12.6, "kling-video/motion-control/std": 12.6,
            "kling-video/v3/motion-control/pro": 12.6, "kling-video/v3/motion-control/std": 12.6,
            "kling-video/o3/video-edit": 6.72, "kling-video/omni/video-edit": 4.2}
    # Seedance 2.5 left this family in v0.1.1: audio on was measured at the audio-off price (09.30.26)
    AUDIO = sorted(e for e in T if e.startswith(("bytedance/seedance-2.0", "alibaba/wan-3.0", "higgsfield/cinema-studio")))
    S25 = sorted(e for e in T if e.startswith("bytedance/seedance-2.5/"))

    def t_table():
        check(f"T0 pricing-table.json next to the script: {len(T)} endpoints (82 expected)", len(T) == 82)
        check("T0 always_ask in the table = exactly the 6 Kling endpoints",
              sorted(e for e, r in T.items() if r.get("always_ask")) == sorted(ASK6))
        check(f"T0 audio-unproven family (Seedance 2.0, Cinema Studio, Wan 3.0/Prime): {len(AUDIO)} endpoints (10); "
              f"the {len(S25)} Seedance 2.5 endpoints have no unproven_when",
              len(AUDIO) == 10 and all(T[e].get("unproven_when") == {"generate_audio": True} for e in AUDIO)
              and len(S25) == 5 and not any("unproven_when" in T[e] for e in S25))

    def t_all():
        for body, want_priced, want_ask in (
                ({}, 64, {"always_ask": 6, "audio_unproven": 10, "not_upper_bound": 1, "unmeasured": 1}),
                ({"generate_audio": False}, 73, {"always_ask": 6, "not_upper_bound": 2, "unmeasured": 1})):
            vs = {ep: P(ep, body, 200, resp_for(ep)) for ep in T}
            asks = dict(collections.Counter(v["code"] for v in vs.values() if v["ask"]))
            priced = sum(not v["ask"] for v in vs.values())
            check(f"S1 all 82 endpoints resolve, body {json.dumps(body)}: {priced} priced + asks {asks}",
                  priced == want_priced and asks == want_ask)
            fixed = [v for ep, v in vs.items() if T[ep]["rule"] == "estimate_usd" and not v["ask"]]
            check(f"S1 {len(fixed)} fixed-price endpoints: list = usd 0.100 + discount.usd 0.100 = $0.20",
                  fixed and all(v["usd"] == 0.2 and v["basis"] == "fixed" for v in fixed))
        vs = [P(ep, {}, 500, {"code": 500, "detail": "Internal Server Error"}) for ep in T]
        asks = dict(collections.Counter(v["code"] for v in vs if v["ask"]))
        check(f"S2 every endpoint with an HTTP 500 estimate asks: {asks}",
              all(v["ask"] for v in vs) and asks == {"always_ask": 6, "unmeasured": 1, "unpriced": 75})
        vs = [P(ep, {}, 200, {"raw": "<html>not json</html>"}) for ep in T]
        asks = dict(collections.Counter(v["code"] for v in vs if v["ask"]))
        check(f"S2 every endpoint with a garbled 200 answer asks: {asks}",
              all(v["ask"] for v in vs) and asks == {"always_ask": 6, "unmeasured": 1, "unexpected_response": 75})

    def t_always_ask():
        for ep, ceil in sorted(ASK6.items()):
            a = P(ep, {"video_url": "https://x/v.mp4"}, 500, {"code": 500, "detail": "Internal Server Error"})
            b = P(ep, {"video_url": "https://x/v.mp4"}, 200, E("0.010"))  # even if /estimate starts to answer
            check(f"A1 {ep}: asks (500 and a 200 quote), display ${ceil}",
                  a["ask"] and b["ask"] and a["code"] == b["code"] == "always_ask" and a["usd"] is None
                  and a["display_usd"] == b["display_usd"] == ceil, f"{a['code']}/{b['code']} {a['display_usd']}")

    def t_audio():
        bad = []
        for ep in AUDIO:
            body = {"resolution": "480p", "duration": 5}
            for label, extra in (("on", {"generate_audio": True}), ("omitted", {}), ('"false"', {"generate_audio":
                                 "false"}), ("0", {"generate_audio": 0}), ("null", {"generate_audio": None})):
                v = P(ep, {**body, **extra}, 200, resp_for(ep))
                if not (v["ask"] and v["code"] == "audio_unproven" and v["usd"] is None):
                    bad.append(f"{ep} audio {label} -> {v['code']}")
            v = P(ep, {**body, "generate_audio": False}, 200, resp_for(ep))
            want = "not_upper_bound" if ep == "alibaba/wan-3.0/reference-to-video" else "priced"
            if v["code"] != want:
                bad.append(f"{ep} audio off -> {v['code']}")
        check("U1 10 Seedance 2.0/Cinema Studio/Wan 3.0 endpoints: audio on, omitted, \"false\", 0 or null -> ask "
              "audio_unproven; false -> priced (Wan 3.0 r2v: not_upper_bound)", not bad, "; ".join(bad[:3]))
        same = [ep for ep in S25 for extra in ({"generate_audio": True}, {}, {"generate_audio": False})
                if P(ep, {"resolution": "480p", "duration": 5, **extra}, 200, DESC)["usd"]
                != P(ep, {"resolution": "480p", "duration": 5, "generate_audio": False}, 200, DESC)["usd"]
                or P(ep, {"resolution": "480p", "duration": 5, **extra}, 200, DESC)["ask"]]
        check("U2 5 Seedance 2.5 endpoints: audio on, omitted or off -> priced, same price (measured 09.30.26)",
              not same, str(same[:2]))

    def t_formula():
        q = {"generate_audio": False}
        s25, s20 = "bytedance/seedance-2.5/", "bytedance/seedance-2.0/"
        cases = [  # (label, endpoint, body, expected $): hand-computed from pricing-table.json, not by this code
            ("2.5 t2v 480p 4 s (42,273 tokens)", s25 + "text-to-video", {"resolution": "480p", "duration": 4},
             0.9046422),
            ("2.5 t2v 480p 6 s (63,410 tokens)", s25 + "text-to-video", {"resolution": "480p", "duration": 6},
             1.356974),
            ("2.5 t2v defaults 720p 5 s (118,800 tokens)", s25 + "text-to-video", {}, 2.54232),
            ("2.5 t2v 1080p 5 s at $0.0234 (267,300 tokens)", s25 + "text-to-video",
             {"resolution": "1080p", "duration": 5}, 6.25482),
            ("2.5 r2v 480p 4 s + video_urls: 30 s input added", s25 + "reference-to-video",
             {"resolution": "480p", "duration": 4, "video_urls": ["https://x/v.mp4"]}, 7.6894694),
            ("2.5 r2v 480p 4 s, image + audio refs only: free", s25 + "reference-to-video",
             {"resolution": "480p", "duration": 4, "image_urls": ["a"], "audio_urls": ["b"], "video_urls": []},
             0.9046422),
            ("2.5 video-edit 480p: 30 s source + 30 s output", s25 + "video-edit",
             {"resolution": "480p", "video_url": "https://x/v.mp4"}, 13.569633),
            ("2.5 video-extend 480p 5 s: 30 s input + 5 s", s25 + "video-extend",
             {"resolution": "480p", "duration": 5, "video_url": "https://x/v.mp4"}, 7.9156246),
            ("2.0 t2v 4k 5 s at $0.008", s20 + "text-to-video", {"resolution": "4k", "duration": 5}, 8.5536),
            ("2.0 r2v 480p 5 s + video: 45 s input added", s20 + "reference-to-video",
             {"resolution": "480p", "duration": 5, "video_urls": ["https://x/v.mp4"]}, 7.397782),
            ("Cinema Studio 4.0 720p 5 s", "higgsfield/cinema-studio/4.0", {"resolution": "720p", "duration": 5},
             2.54232),
            ("Wan 3.0 t2v 1080p 5 s x $0.20", "alibaba/wan-3.0/text-to-video", {}, 1.0),
            ("Wan 3.0 i2v 480p 2 s x $0.05", "alibaba/wan-3.0/image-to-video", {"resolution": "480p",
                                                                                 "duration": 2}, 0.1),
            ("Genjutsu 720p: 30 s max input x $0.681", "higgsfield/genjutsu/motion-transfer/v1.0",
             {"video_url": "v", "image_urls": ["a"]}, 20.43),
            ("Genjutsu 480p: 30 s x $0.318", "higgsfield/genjutsu/object-swap/v1.0",
             {"resolution": "480p", "video_url": "v", "image_urls": ["a"]}, 9.54),
        ]
        for label, ep, body, want in cases:
            v = P(ep, {**body, **q}, 200, DESC)
            check(f"F1 {label} = ${want}", not v["ask"] and abs(v["usd"] - want) < 1e-9,
                  f"{v['code']} {v['usd']}")
        for label, ep, body in (("Cinema Studio 1080p (no rate)", "higgsfield/cinema-studio/4.0",
                                 {"resolution": "1080p", "duration": 5}),
                                ("Seedance 2.5 4k (no rate)", s25 + "text-to-video", {"resolution": "4k"}),
                                ("resolution 1440p", s25 + "text-to-video", {"resolution": "1440p"}),
                                ("resolution null", s25 + "text-to-video", {"resolution": None}),
                                ("resolution a list", s25 + "text-to-video", {"resolution": ["480p"]}),
                                ("duration null", s25 + "text-to-video", {"duration": None}),
                                ("duration \"5\"", s25 + "text-to-video", {"duration": "5"}),
                                ("duration 0", s25 + "text-to-video", {"duration": 0}),
                                ("duration -4", s25 + "text-to-video", {"duration": -4}),
                                ("duration true", s25 + "text-to-video", {"duration": True}),
                                ("duration 4.5", s25 + "text-to-video", {"duration": Decimal("4.5")}),
                                ("duration 10^400 (not a finite price)", s25 + "text-to-video",
                                 {"duration": 10 ** 400}),
                                ("Wan 3.0 duration missing", "alibaba/wan-3.0/text-to-video", {"duration": None}),
                                ("Genjutsu 1440p", "higgsfield/genjutsu/object-swap/v1.0", {"resolution": "1440p"})):
            v = P(ep, {**body, **q}, 200, DESC)
            check(f"F2 {label} -> ask bad_param", v["ask"] and v["code"] == "bad_param" and v["usd"] is None,
                  v["code"])
        for label, ep, body, secs, want in (  # hand-computed; the length comes from hf_rest's upload record
                ("2.5 video-edit 720p, 5.5 s source -> 6 s in + 6 s out (285,120 tokens)", s25 + "video-edit",
                 {"video_url": "u"}, 5.5, 6.101568),
                ("2.5 video-edit 720p, 2 s source -> 2 s in + 4 s out (the 4 s minimum)", s25 + "video-edit",
                 {"video_url": "u"}, 2.0, 3.050784),
                ("2.5 video-edit 720p, length unknown -> 30 s + 30 s (the JOI-016 $30.51)", s25 + "video-edit",
                 {"video_url": "u"}, None, 30.50784),
                ("2.5 video-edit 720p, 45 s source -> capped at 30 s", s25 + "video-edit", {"video_url": "u"}, 45,
                 30.50784),
                ("Genjutsu 720p, 3.7 s source -> 4 s x $0.681", "higgsfield/genjutsu/object-swap/v1.0",
                 {"video_url": "v", "image_urls": ["a"]}, 3.7, 2.724),
                ("2.5 video-edit, length \"5\" (text, not a number) -> treated as unknown", s25 + "video-edit",
                 {"video_url": "u"}, "5", 30.50784)):
            v = price(ep, {**body, **q}, 200, DESC, input_video_s=secs)
            check(f"F5 {label} = ${want}", not v["ask"] and abs(v["usd"] - want) < 1e-9, f"{v['code']} {v['usd']}")
        v = price_record({"v": 1, "kind": "hf-superengine-estimate", "endpoint": s25 + "video-edit",
                          "params": {"video_url": "u", **q}, "http": 200, "response": DESC, "input_video_s": 5.5})
        check("F5 an estimate record's input_video_s reaches the price ($6.101568)",
              not v["ask"] and abs(v["usd"] - 6.101568) < 1e-9, f"{v['code']} {v['usd']}")
        v = P(s25 + "text-to-video", {"resolution": "480p", "duration": 4, **q}, 200, E("0.200"))
        check("F3 Seedance with a fixed-quote answer (not the formula description) -> ask unexpected_response",
              v["ask"] and v["code"] == "unexpected_response", v["code"])
        v = P("minimax/h3/reference-to-video", {"duration": 5, "image_urls": list("abcdefg")}, 200, DESC)
        check("F4 MiniMax H3 r2v (video-ref cost unknown) -> ask not_upper_bound, shows $0.81 (5 s x $0.13 + "
              "2 refs x $0.08)", v["ask"] and v["code"] == "not_upper_bound" and v["display_usd"] == 0.81,
              f"{v['code']} {v['display_usd']}")

    def t_replay():
        # The 09.24 REST runs 1 and 2, as build_pricing.py (Phase 0.3) replays them. Fixed-price quotes are the
        # 09.26 /estimate answers (estimates/replay.json, soul_training.json). "exact" = the same list price with the
        # measured Seedance output (640x640 = 409,600 px); Flare's exact = its real charge, $0.06 (CSV).
        q = {"resolution": "480p", "aspect_ratio": "1:1", "generate_audio": False}
        R2V, T2V = "bytedance/seedance-2.5/reference-to-video", "bytedance/seedance-2.5/text-to-video"
        FL = "marketing-studio/image/flare"
        jobs = [  # (endpoint, body, /estimate answer, jobs, billed, build_pricing.py's printed pred per job)
            ("z-image/turbo", {"resolution": "1k", "aspect_ratio": "1:1"}, E("0.015"), 6, 6, 0.0150),
            (R2V, {**q, "duration": 4, "image_urls": ["a", "b"]}, DESC, 9, 9, 0.9046),
            (FL, {"resolution": "2k", "quality": "high", "aspect_ratio": "16:9"}, DESC, 1, 1, 0.1700),  # v0.1.1
            (T2V, {**q, "duration": 4}, DESC, 2, 2, 0.9046),
            (T2V, {**q, "duration": 6}, DESC, 3, 1, 1.3570),  # 2 of 3 ended nsfw: not charged
            ("kling-video/v3.0/std/text-to-video", {"duration": 5, "sound": "off", "aspect_ratio": "1:1"},
             E("0.231", "0.189"), 4, 4, 0.4200),
            ("minimax/h3/text-to-video", {"duration": 5, "aspect_ratio": "1:1"}, E("0.455", "0.195"), 2, 2, 0.6500),
            ("marketing-studio/image", {"resolution": "1k", "quality": "low", "aspect_ratio": "1:1",
                                        "image_urls": ["a", "b"]}, E("0.043"), 2, 2, 0.0430),
            ("v1/custom-references", {"model_version": "v2"}, E("2.500"), 1, 1, 2.5000),
            ("higgsfield-ai/soul/v2/standard", {"resolution": "720p", "aspect_ratio": "3:4", "batch_size": 1},
             E("0.004"), 4, 4, 0.0040),
        ]
        rate = T[T2V]["rate_per_1k_tokens"]["480p"]
        agg, bad = collections.defaultdict(lambda: [0.0, 0.0, 0.0]), []
        for ep, body, resp, n, billed, want in jobs:
            v = P(ep, body, 200, resp)
            if v["ask"] or round(v["usd"], 4) != want:
                bad.append(f"{ep} {v['code']} {v['usd']} != {want}")
                continue
            exact = 0.06 if ep == FL else float(seedance_usd(409_600, body["duration"], rate)[0]) \
                if ep in (R2V, T2V) else v["usd"]
            a = agg[ep]
            a[0], a[1], a[2] = a[0] + n * v["usd"], a[1] + billed * v["usd"], a[2] + billed * exact
        check("R1 every 09.24 job prices exactly as build_pricing.py's replay (per job, 4 dp)", not bad,
              "; ".join(bad[:2]))
        want = {"z-image/turbo": (0.09, 0.09, 0.09), R2V: (8.1418, 8.1418, 7.3958), FL: (0.17, 0.17, 0.06),
                T2V: (5.8802, 3.1663, 2.8762), "kling-video/v3.0/std/text-to-video": (1.68, 1.68, 1.68),
                "minimax/h3/text-to-video": (1.3, 1.3, 1.3), "marketing-studio/image": (0.086, 0.086, 0.086),
                "v1/custom-references": (2.5, 2.5, 2.5), "higgsfield-ai/soul/v2/standard": (0.016, 0.016, 0.016)}
        got = {ep: tuple(round(x, 4) for x in a) for ep, a in agg.items()}
        check("R2 per-model pred_all / pred_billed / exact_billed = build_pricing.py's AGG lines (Flare exact = its "
              "$0.06 charge, which build_pricing adds in its TOTAL line)", got == want,
              "" if got == want else str({k: v for k, v in got.items() if want.get(k) != v})[:200])
        total = sum(a[2] for ep, a in agg.items() if ep != "v1/custom-references")  # training: not in the CSV
        check(f"R3 exact list total of the 31 charged generations (33 requests, 2 nsfw free; Soul training is not "
              f"in the CSV) = ${total:.4f} vs console usage_before_discounts $13.51 (rounded per model)",
              abs(total - 13.504) < 1e-9 and abs(total - 13.51) <= 0.01)

    def t_flare():
        FL, SB = "marketing-studio/image/flare", "marketing-studio/image/sunburst"
        observed = [({"resolution": "2k", "quality": "high", "aspect_ratio": "16:9"}, 0.06),  # T2_flare, CSV
                    ({"resolution": "1k", "quality": "low", "aspect_ratio": "1:1"}, 0.02)]  # 7.3 walk, 09.30.26
        for body, actual in observed:
            v = P(FL, {"prompt": "x", **body}, 200, DESC)
            check(f"C1 Flare {body['resolution']}/{body['quality']} ceiling ${v['usd']} >= observed actual "
                  f"${actual}", not v["ask"] and v["basis"] == "ceiling" and v["usd"] >= actual, v["code"])
        grid = [P(FL, {"resolution": r, "quality": qq}, 200, DESC)["usd"] for r in ("1k", "2k", "4k")
                for qq in ("low", "medium", "high", "xhigh", "max")]
        check(f"C1 all 15 Flare tiers >= every observed actual (lowest ${min(grid)})",
              None not in grid and min(grid) >= max(a for _, a in observed))
        for label, body, want in (("defaults (2k/high)", {}, 0.17), ("1k/low", {"resolution": "1k",
                                  "quality": "low"}, 0.08), ("2k/high + 3 image_urls", {"image_urls": ["a"] * 3},
                                  0.32), ("4k/max + 16 image_urls (the table's worst case)",
                                  {"resolution": "4k", "quality": "max", "image_urls": ["a"] * 16}, 2.02)):
            v, w = P(FL, body, 200, DESC), P(SB, body, 200, DESC)
            check(f"C2 Flare {label} = ${want}; Sunburst asks unmeasured, shows ${want}", not v["ask"]
                  and abs(v["usd"] - want) < 1e-9 and w["ask"] and w["code"] == "unmeasured"
                  and abs(w["display_usd"] - want) < 1e-9, f"{v['usd']} {w['code']} {w['display_usd']}")
        for label, body in (("quality ultra", {"quality": "ultra"}), ("resolution 8k", {"resolution": "8k"}),
                            ("image_urls as text", {"image_urls": "a.png"}), ("quality null", {"quality": None})):
            v = P(FL, body, 200, DESC)
            check(f"C3 Flare {label} -> ask bad_param", v["ask"] and v["code"] == "bad_param", v["code"])

    def t_decisions():  # Joe 09.28.26, decisions 1-3 (decision 4, the rate-drift guard, is not built: BUILD-NOTES)
        global _table, SUNBURST_MEASURED
        FL, saved = "marketing-studio/image/flare", _table
        # 1: the two reference-video endpoints always ask, by name, even if a rebuilt table said upper_bound true
        REF2 = ["alibaba/wan-3.0/reference-to-video", "minimax/h3/reference-to-video"]  # named here, not read back
        check("N1 the by-name always-ask list = MiniMax H3 r2v + Wan 3.0 r2v, both in the table",
              sorted(NOT_UPPER_BOUND) == REF2 and all(e in T for e in REF2))
        refs = [("minimax/h3/reference-to-video", {}), ("minimax/h3/reference-to-video",
                 {"duration": 10, "image_urls": ["a"] * 7}), ("minimax/h3/reference-to-video", {"video_urls": ["v"]}),
                ("alibaba/wan-3.0/reference-to-video", {"generate_audio": False}),
                ("alibaba/wan-3.0/reference-to-video", {"generate_audio": False, "resolution": "480p", "duration": 2,
                                                        "video_urls": ["v"]})]
        try:
            for tag, flip in (("N2", False), ("N3", True)):
                if flip:
                    _table = {**saved, **{e: {**saved[e], "upper_bound": True} for e in REF2}}
                bad = [f"{ep} {v['code']}" for ep, body in refs for v in [P(ep, body, 200, DESC)]
                       if not (v["ask"] and v["code"] == "not_upper_bound" and v["usd"] is None and v["display_usd"])]
                check(f"{tag} MiniMax H3 r2v + Wan 3.0 r2v (audio off; image and video refs) ask not_upper_bound "
                      "by name" + (", even with upper_bound true in the table" if flip else ""), not bad,
                      "; ".join(bad[:2]))
        finally:
            _table = saved
        # 2: every Sunburst endpoint asks "unmeasured"; the one flag flips it to silent pricing on the Flare grid
        SB = sorted(e for e in T if "sunburst" in e)
        tiers = [{"resolution": r, "quality": q, "image_urls": ["a"] * n} for r in ("1k", "2k", "4k")
                 for q in ("low", "medium", "high", "xhigh", "max") for n in (0, 3, 16)]
        flare = [P(FL, b, 200, DESC) for b in tiers]
        bad = [f"{ep} {b['resolution']}/{b['quality']} -> {w['code']}" for ep in SB for b, f in zip(tiers, flare)
               for w in [P(ep, b, 200, DESC)] if f["ask"] or not (
                   w["ask"] and w["code"] == "unmeasured" and w["usd"] is None and w["display_usd"] == f["usd"])]
        bad += [f"{ep} http {h} -> {w['code']}" for ep in SB for h, resp in ((500, None), (200, E("0.01")))
                for w in [P(ep, {}, h, resp)] if not (w["ask"] and w["code"] == "unmeasured")]
        check(f"B1 every Sunburst endpoint in the table ({len(SB)}) asks unmeasured on 45 tier x image_urls bodies, a "
              "500 and a fixed quote; usd null, shows Flare's figure", SB and not bad, "; ".join(bad[:2]))
        try:
            SUNBURST_MEASURED = True
            bad = [f"{ep} {b['resolution']}/{b['quality']}" for ep in SB for b, f in zip(tiers, flare)
                   for w in [P(ep, b, 200, DESC)] if w["ask"] or w["usd"] != f["usd"] or w["basis"] != "ceiling"]
            check("B2 SUNBURST_MEASURED = True -> Sunburst priced silently, exactly like Flare, on all 45 bodies",
                  not bad, "; ".join(bad[:2]))
            w = P(SB[0], {"enhance_prompt": True, "preset_id": "p", "image_urls": ["a"]}, 200, DESC)
            check("B3 after the flip, Sunburst with enhance_prompt + preset_id set still asks option_unpriced",
                  w["ask"] and w["code"] == "option_unpriced", w["code"])
        finally:
            SUNBURST_MEASURED = False
        # 3: unpriced options ask when set; absent, null or their own off value (false, "") price silently
        WAN = sorted(e for e in T if e.startswith("alibaba/wan-3.0/"))
        q = {"generate_audio": False, "resolution": "480p", "duration": 2}
        on = {"enable_thinking": (True, "true", "false", 1, 0, "", [], {}),
              "enhance_prompt": (True, "true", "false", 1, 0, "", [], {}),
              "preset_id": ("5f1d2a8e-0c1b-4c6e-9a53-2b7f0e9d1c44", " ", "0", False, True, 0, [], {})}
        bad = []
        for ep, body, k in [(e, q, "enable_thinking") for e in WAN] + [(FL, {}, "enhance_prompt"),
                                                                        (FL, {}, "preset_id")]:
            off = P(ep, body, 200, DESC)
            bad += [f"{ep} {k}={json.dumps(x)} -> {v['code']}" for x in on[k]
                    for v in [P(ep, {**body, k: x}, 200, DESC)]
                    if not (v["ask"] and v["code"] == "option_unpriced" and v["display_usd"] == off["display_usd"])]
        check(f"O1 option set -> ask option_unpriced, showing the price without it: Wan 3.0 ({len(WAN)}) "
              "enable_thinking, Flare enhance_prompt / preset_id; true, text, numbers, lists, objects (unexpected "
              "types) all count as set", len(WAN) == 3 and not bad, "; ".join(bad[:2]))
        bad = []
        for ep, body, k, offs in [(e, q, "enable_thinking", (False, None)) for e in WAN if e not in REF2] \
                + [(FL, {}, "enhance_prompt", (False, None)), (FL, {}, "preset_id", (None, ""))]:
            want = P(ep, body, 200, DESC)  # the option absent
            bad += [f"{ep} {k}={json.dumps(x)} -> {v['code']}" for x in offs
                    for v in [want, P(ep, {**body, k: x}, 200, DESC)] if v["ask"] or v["usd"] != want["usd"]]
        for ep, body in (("marketing-studio/image", {"enhance_prompt": True, "preset_id": "x"}),
                         ("alibaba/wan-3.0-prime/text-to-video", {"generate_audio": False, "enable_thinking": True})):
            v = P(ep, body, 200, FIX)
            bad += [f"{ep} -> {v['code']}"] if v["ask"] else []
        check("O2 option absent, null or off (false; \"\" for preset_id) -> priced silently at the same price; the "
              "same options on fixed-quote endpoints (Marketing Studio image, Wan 3.0 Prime) price from the live quote",
              not bad, "; ".join(bad[:2]))

    def t_garbled():
        DROP = object()

        def rec(**over):
            r = {"v": 1, "kind": "hf-superengine-estimate", "estimate_key": "0" * 64, "endpoint": "z-image/turbo",
                 "params": {"prompt": "x"}, "params_sha256": "0" * 64, "created_at": 1.0, "http": 200,
                 "response": E("0.015")}
            for k, val in over.items():
                if val is DROP:
                    r.pop(k)
                else:
                    r[k] = val
            return json.dumps(r).encode()

        good = price_bytes(rec())
        check("G0 a well-formed z-image record -> priced $0.015 (fixed), record_sha256 of the bytes",
              not good["ask"] and good["usd"] == 0.015 and good["basis"] == "fixed"
              and good["record_sha256"] == hashlib.sha256(rec()).hexdigest(), good["code"])
        cases = [
            ("empty file", b"", "invalid_record"), ("not JSON", b"not json", "invalid_record"),
            ("not UTF-8", b"\xff\xfe{}", "invalid_record"), ("a JSON list", b"[1, 2]", "invalid_record"),
            ("UTF-8 BOM", b"\xef\xbb\xbf" + rec(), "invalid_record"),
            ("NaN in the record", rec().replace(b'"0.015"', b"NaN"), "invalid_record"),
            ("nested 100,000 deep", b"[" * 100000 + b"]" * 100000, "invalid_record"),
            ("v 2", rec(v=2), "invalid_record"), ("v true", rec(v=True), "invalid_record"),
            ("wrong kind", rec(kind="hf-superengine-stamp"), "invalid_record"),
            ("no endpoint", rec(endpoint=DROP), "invalid_record"), ("endpoint 123", rec(endpoint=123),
                                                                     "invalid_record"),
            ("endpoint not in the table", rec(endpoint="no/such/model"), "not_in_table"),
            ("endpoint with a trailing slash", rec(endpoint="z-image/turbo/"), "not_in_table"),
            ("no params", rec(params=DROP), "invalid_record"), ("params a list", rec(params=[]), "invalid_record"),
            ("no http", rec(http=DROP), "invalid_record"), ("http true", rec(http=True), "invalid_record"),
            ('http "200"', rec(http="200"), "invalid_record"), ("http 404", rec(http=404), "invalid_record"),
            ("http 302", rec(http=302), "invalid_record"),
            ("http 500, response null", rec(http=500, response=None), "unpriced"),
            ("http 503 with a valid-looking quote", rec(http=503), "unpriced"),
            ("200, response null", rec(response=None), "unexpected_response"),
            ("200, response raw text", rec(response={"raw": "<html>"}), "unexpected_response"),
            ("usd missing", rec(response={"type": "estimate", "discount": None}), "unexpected_response"),
            ('usd "abc"', rec(response=E("abc")), "unexpected_response"),
            ('usd "-0.5"', rec(response=E("-0.5")), "unexpected_response"),
            ("usd -0.5 (a number)", rec(response=E(-0.5)), "unexpected_response"),
            ('usd "1e3"', rec(response=E("1e3")), "unexpected_response"),
            ('usd " 0.5"', rec(response=E(" 0.5")), "unexpected_response"),
            ("usd true", rec(response=E(True)), "unexpected_response"),
            ("usd 1e999", rec().replace(b'"0.015"', b"1e999"), "unexpected_response"),
            ('usd "0.000", no discount ($0)', rec(response=E("0.000")), "unexpected_response"),
            ("discount {}", rec(response={"type": "estimate", "usd": "0.1", "discount": {}}), "unexpected_response"),
            ("discount without usd", rec(response={"type": "estimate", "usd": "0.1", "discount":
                                                   {"percentage": "45.00"}}), "unexpected_response"),
            ("discount usd null", rec(response={"type": "estimate", "usd": "0.1", "discount": {"usd": None}}),
             "unexpected_response"),
            ('discount "0.1" (not an object)', rec(response={"type": "estimate", "usd": "0.1", "discount": "0.1"}),
             "unexpected_response"),
            ('discount usd "-0.1"', rec(response=E("0.1", "-0.1")), "unexpected_response"),
            ("discount usd -0.1 (a number; usd + discount still > 0)", rec(response=E("0.5", -0.1)),
             "unexpected_response"),
            ("fixed endpoint answering a formula description", rec(response=DESC), "unexpected_response"),
            ("type missing", rec(response={"usd": "0.015", "discount": None}), "unexpected_response"),
        ]
        bad = []
        for label, raw, code in cases:
            v = price_bytes(raw)
            if not (v["ask"] is True and v["usd"] is None and v["code"] == code):
                bad.append(f"{label} -> {v['code']}")
            seen.append(v)
        check(f"G1 {len(cases)} garbled / unknown / unpriced records -> ask with the right code, usd null", not bad,
              "; ".join(bad[:3]))
        v = price_bytes(rec(endpoint="bytedance/seedance-2.5/text-to-video", http=500, response=None,
                            params={"prompt": "x", "resolution": "480p", "duration": 4, "generate_audio": False}))
        check("G2 unpriced Seedance record -> ask unpriced; shows the formula figure $0.9046422",
              v["ask"] and v["code"] == "unpriced" and v["display_usd"] == 0.9046422, v["code"])
        v = price_bytes(rec(endpoint="v1/custom-references", params={"model_version": "v2"}, response=E("2.500")))
        check("G3 Soul ID training record (estimated at /estimate/soul-id) -> priced $2.50",
              not v["ask"] and v["usd"] == 2.5, v["code"])

    def t_fail_closed():
        global _table, TABLE_PATH
        saved = (_table, TABLE_PATH)
        try:
            _table, TABLE_PATH = None, saved[1].with_name("no-such-pricing-table.json")
            v = P("z-image/turbo", {}, 200, E("0.015"))
            check("X1 pricing table missing -> ask table_error", v["ask"] and v["code"] == "table_error", v["code"])
            _table = {**saved[0], "x/no-defaults": {"rule": "estimate_usd"},
                      "x/odd-rule": {"rule": "guess", "defaults": {}},
                      "x/no-upper-bound-flag": {"rule": "per_second", "defaults": {}, "seconds_from": "duration",
                                                "usd_per_s": {"1k": Decimal("0.1")}}}
            v = P("x/no-defaults", {}, 200, E("0.015"))
            check("X2 a crash inside pricing (entry without defaults) -> ask internal_error",
                  v["ask"] and v["code"] == "internal_error", v["code"])
            v = P("x/odd-rule", {}, 200, DESC)
            check("X3 an unknown rule -> ask table_error", v["ask"] and v["code"] == "table_error", v["code"])
            v = P("x/no-upper-bound-flag", {"resolution": "1k", "duration": 2}, 200, DESC)
            check("X4 an entry without upper_bound true -> ask not_upper_bound",
                  v["ask"] and v["code"] == "not_upper_bound", v["code"])
        finally:
            _table, TABLE_PATH = saved

    def t_cap():
        cases = [(cap_usd(None), None), (cap_usd(100), 5.0), (cap_usd(20), 5.0), (cap_usd(19.99), 4.9975),
                 (cap_usd(4), 1.0), (cap_usd(Decimal("8.00")), 2.0), (cap_usd(0), 0.0), (cap_usd(-3), 0.0),
                 (cap_usd(float("nan")), 0.0), (cap_usd(float("inf")), 0.0), (cap_usd(True), 0.0),
                 (cap_usd("10"), 0.0)]
        check("K1 cap_usd: None->None; 100->5; 20->5; 19.99->4.9975; 4->1; 0, -3, NaN, inf, true, \"10\" -> 0",
              all(g == w if w is None or g is None else abs(g - w) < 1e-12 for g, w in cases),
              str([g for g, _ in cases]))
        fits = [
            (fits_cap(1.0, 0.0, 100), True), (fits_cap(1.0, 4.0, 100), True),  # lands exactly on the $5 cap
            (fits_cap(1.000001, 4.0, 100), False), (fits_cap(0.9046422, 4.0953578, 100), True),
            (fits_cap(0.1, 4.9, 100), True), (fits_cap(5.01, 0, 1000), False),
            (fits_cap(0.25, 0, 1.0), True), (fits_cap(0.26, 0, 1.0), False), (fits_cap(0.01, 0, 0), False),
            (fits_cap(0.01, 0, -5), False), (fits_cap(1.0, 0, None), None), (fits_cap(None, 0, 100), False),
            (fits_cap(float("nan"), 0, 100), False), (fits_cap(-1, 0, 100), False), (fits_cap(True, 0, 100), False),
            (fits_cap(1.0, float("nan"), 100), False), (fits_cap(1.0, -0.5, 100), False),
            (fits_cap(1.0, None, 100), False), (fits_cap(1.0, 0, float("nan")), False),
            (fits_cap(None, 0, None), False), (fits_cap(0, 0, 100), True),
        ]
        check("K2 fits_cap: at the cap fits, a micro-dollar over does not; 25% of a small balance binds; zero or "
              "negative balance fits nothing; unknown balance -> None; bad amounts -> False",
              all(g is w for g, w in fits), str([g for g, _ in fits]))

    def t_cli():
        me = str(Path(__file__).resolve())
        tmp = Path(tempfile.mkdtemp(prefix="pricing-selftest-"))

        def cli(*args):
            p = subprocess.run([sys.executable, "-I", "-B", me, *args], capture_output=True, timeout=60)
            lines = p.stdout.decode("ascii").strip().splitlines()
            v = json.loads(lines[0]) if len(lines) == 1 else None
            return p.returncode, v, len(lines), p.stderr

        try:
            t_cli_in(cli, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def t_cli_in(cli, tmp):
        good = tmp / "good.json"
        good.write_bytes(json.dumps({"v": 1, "kind": "hf-superengine-estimate", "endpoint": "z-image/turbo",
                                     "params": {"prompt": "x"}, "http": 200, "response": E("0.015")}).encode())
        ask = tmp / "ask.json"
        ask.write_bytes(json.dumps({"v": 1, "kind": "hf-superengine-estimate", "endpoint":
                                    "kling-video/o3/video-edit", "params": {"prompt": "x"}, "http": 500,
                                    "response": {"code": 500, "detail": "Internal Server Error"}}).encode())
        code, v, n, err = cli("price", str(good))
        check("L1 price <record> -> exit 0, exactly one JSON line, stderr empty, ask false, record_sha256 = the file's",
              code == 0 and n == 1 and not err and v and v["ask"] is False and v["usd"] == 0.015
              and v["record_sha256"] == hashlib.sha256(good.read_bytes()).hexdigest(), f"{code} {n} {err[:80]}")
        code, v, n, err = cli("price", str(ask))
        check("L2 always-ask record -> exit 1, one JSON line, ask true", code == 1 and n == 1 and not err and v
              and v["ask"] is True and v["code"] == "always_ask", f"{code} {n}")
        code, v, n, err = cli("price", str(tmp / "missing.json"))
        check("L3 missing record -> exit 1, ask unreadable", code == 1 and n == 1 and v and v["ask"] is True
              and v["code"] == "unreadable", f"{code} {n}")
        code, v, n, err = cli("price", str(tmp))
        check("L3 a folder instead of a record -> exit 1, ask unreadable", code == 1 and n == 1 and v
              and v["code"] == "unreadable", f"{code} {n}")
        for args in ((), ("price",), ("bogus", "x"), ("price", "a", "b")):
            code, v, n, err = cli(*args)
            check(f"L4 usage {list(args)} -> exit 2, one JSON line, ask usage", code == 2 and n == 1 and v
                  and v["ask"] is True and v["code"] == "usage", f"{code} {n}")

    def t_invariants():
        bad = [v for v in seen if not (
            (v["ask"] is False and v["code"] == "priced" and isinstance(v["usd"], float) and v["usd"] > 0
             and math.isfinite(v["usd"]) and v["display_usd"] == v["usd"])
            or (v["ask"] is True and v["code"] != "priced" and v["usd"] is None
                and (v["display_usd"] is None or (isinstance(v["display_usd"], float) and v["display_usd"] > 0
                                                  and math.isfinite(v["display_usd"])))))]
        check(f"I1 all {len(seen)} verdicts: ask false <=> code priced with usd > 0; ask true -> usd null",
              not bad, str(bad[:1])[:200])

    for name, fn in (("T0", t_table), ("S", t_all), ("A", t_always_ask), ("U", t_audio), ("F", t_formula),
                     ("R", t_replay), ("C", t_flare), ("N/B/O", t_decisions), ("G", t_garbled), ("X", t_fail_closed),
                     ("K", t_cap), ("L", t_cli), ("I", t_invariants)):
        run(name, fn)
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
