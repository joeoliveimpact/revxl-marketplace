#!/usr/bin/env python3
"""Custom-idea field vet: how has THIS niche's field performed on a topic?

Usage:  python field_vet.py <project_dir> <keyword> [keyword2 ...]

When the creator brings their OWN idea (not one derived from the brief's attack
themes), run its topic word(s) through this before committing beats to it. It
answers "does the field actually win on this?" with the same transcript-primary
weighting the analysis uses (C7): spoken track is the signal, captions are a
separate packaging read.

Reads:   <project>/source/competitors/transcripts/*.json (+ client-transcripts.json)  [spoken, PRIMARY]
         <project>/source/competitors/reels/*.json (+ reels-full.json)                [captions, secondary]
Writes:  nothing — prints an ASCII table + a one-line verdict per keyword.

Verdict bands on PER-ACCOUNT LIFT (SKLLPLG-260): each account's matching reels are scored against
that account's OWN median views, then the median across accounts. 1.0x = neutral. >=1.5x WINNER,
0.8-1.5x NEUTRAL, <0.8x LOSER. n<5 hits or <3 accounts = THIN (a hint, not a rule). A pooled
field median let one large account be the field (a keyword read 10.80x pooled, 1.27x per account).
Stdlib only. Deterministic. utf-8 reads; ASCII-safe stdout.
"""
import json, glob, os, re, sys, statistics as st
from collections import defaultdict

if len(sys.argv) < 3:
    print("Usage: python field_vet.py <project_dir> <keyword> [keyword2 ...]"); sys.exit(1)
ROOT = os.path.abspath(sys.argv[1])
KEYWORDS = sys.argv[2:]

def J(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}

def _items_of(d):
    # SKLLPLG-263: one reader for every payload shape ({reels} / {items} / {data:{items}}), on BOTH
    # tracks -- the spoken loader used to read only `reels` while the caption loader also read `items`.
    if not isinstance(d, dict): return []
    return d.get("reels") or d.get("items") or (d.get("data") or {}).get("items") or []

# ---- spoken track (PRIMARY) ----
spoken = []  # (text_lower, views, handle)  -- the handle is what makes per-account lift possible
tpaths = sorted(glob.glob(os.path.join(ROOT, "source", "competitors", "transcripts", "*.json")))
cp = os.path.join(ROOT, "source", "client-transcripts.json")
if os.path.exists(cp): tpaths.append(cp)
for p in tpaths:
    hname = "CLIENT" if p == cp else os.path.splitext(os.path.basename(p))[0]
    for r in _items_of(J(p)):
        t = (r.get("text") or "").lower(); v = r.get("views") or 0
        if t and v: spoken.append((t, v, hname))

# ---- caption track (SECONDARY, kept separate per C7) ----
caption = []
def _reels_of(path, hname):
    d = J(path); out = []
    for it in _items_of(d):
        p = it.get("post", {}); e = p.get("engagement", {})
        if (p.get("flags") or {}).get("pinned"): continue   # SKLLPLG-261: pinned rows never rank
        txt = (p.get("content", {}).get("text", "") or "").lower(); v = e.get("views") or 0
        if txt and v: out.append((txt, v, hname))
    return out
for p in sorted(glob.glob(os.path.join(ROOT, "source", "competitors", "reels", "*.json"))):
    caption += _reels_of(p, os.path.splitext(os.path.basename(p))[0])
rf = os.path.join(ROOT, "source", "reels-full.json")
if os.path.exists(rf): caption += _reels_of(rf, "CLIENT")

if not spoken and not caption:
    print("No field data found under", ROOT); sys.exit(1)

def field_median(rows): return st.median([v for _, v, _h in rows]) if rows else 0
SPOKEN_MED = field_median(spoken)
CAPTION_MED = field_median(caption)
def acct_meds(rows):
    by = defaultdict(list)
    for _, v, h in rows: by[h].append(v)
    return {h: st.median(vs) for h, vs in by.items()}
SPOKEN_ACCT = acct_meds(spoken)   # each account's own median on that track: the lift denominator
CAPTION_ACCT = acct_meds(caption)

def band(lift, n, accounts):
    if n < 5 or accounts < 3: return "THIN"
    if lift >= 1.5: return "WINNER"
    if lift >= 0.8: return "NEUTRAL"
    return "LOSER"

def scan(rows, accts, kw):
    pat = re.compile(r"\b" + re.escape(kw.lower()) + r"", re.I) if kw.isalnum() else re.compile(re.escape(kw.lower()), re.I)
    hits = [(v, h) for t, v, h in rows if pat.search(t)]
    if not hits: return (0, 0, 0.0, 0, "NONE")
    by = defaultdict(list)
    for v, h in hits: by[h].append(v)
    ratios = [st.median(vs) / accts[h] for h, vs in by.items() if accts.get(h)]
    lift = st.median(ratios) if ratios else 0.0
    m = st.median([v for v, _ in hits])
    return (len(hits), m, lift, len(ratios), band(lift, len(hits), len(ratios)))

print(f"FIELD VET  |  project: {os.path.basename(ROOT)}")
print(f"spoken field median: {SPOKEN_MED:,.0f} views (n={len(spoken)}, {len(SPOKEN_ACCT)} accounts)  |  caption field median: {CAPTION_MED:,.0f} (n={len(caption)}, {len(CAPTION_ACCT)} accounts)")
print("lift = per-account (each account vs its OWN median, then the median across accounts); 1.00x = neutral")
print(f"\n{'keyword':16} {'spoken n':>8} {'spoken med':>11} {'lift':>7} {'accts':>5} {'verdict':>8}  |  {'cap n':>5} {'cap med':>9} {'lift':>6} {'accts':>5}")
verdicts = {}
for kw in KEYWORDS:
    sn, sm, smult, sacc, sv = scan(spoken, SPOKEN_ACCT, kw)
    cn, cm, cmult, cacc, cv = scan(caption, CAPTION_ACCT, kw)
    verdicts[kw] = (sv, smult, sn)
    print(f"{kw[:16]:16} {sn:>8} {sm:>11,.0f} {smult:>6.2f}x {sacc:>5} {sv:>8}  |  {cn:>5} {cm:>9,.0f} {cmult:>5.2f}x {cacc:>5}")

# recommendation off the SPOKEN read (primary). THREE buckets, deliberately split:
# - WINNER/NEUTRAL: field-backed, frame on it.
# - LOSER: HAS data and it underperforms -> proven-weak -> PIVOT (don't ditch).
# - UNTESTED (THIN/NONE): little/no data -> NOT a loser; could be first-mover -> de-risk, don't kill.
ranked = sorted(verdicts.items(), key=lambda kv: -kv[1][1])
winners  = [k for k, (v, m, n) in ranked if v == "WINNER"]
neutral  = [k for k, (v, m, n) in ranked if v == "NEUTRAL"]
losers   = [k for k, (v, m, n) in ranked if v == "LOSER"]
untested = [k for k, (v, m, n) in ranked if v in ("THIN", "NONE")]
print("\nVERDICT (spoken/primary):")
if winners:
    print("  FIELD-BACKED (frame ON):", ", ".join(f"{k} ({verdicts[k][1]:.2f}x)" for k in winners))
if neutral:
    print("  NEUTRAL (safe, no edge):", ", ".join(f"{k} ({verdicts[k][1]:.2f}x)" for k in neutral))
if losers:
    print("  PROVEN WEAK -> PIVOT, don't ditch:", ", ".join(f"{k} ({verdicts[k][1]:.2f}x, n={verdicts[k][2]})" for k in losers))
    print("    -> keep the idea; reframe the headline toward the strongest WINNER below.")
if untested:
    print("  UNTESTED (little/no field data -> NOT a loser; possible first-mover):",
          ", ".join(f"{k} (n={verdicts[k][2]})" for k in untested))
    print("    -> new/timely idea can win before the field catches up. De-risk it: ride the novel")
    print("       topic on a PROVEN hook type + the nearest proven frame word, don't also gamble structure.")
if winners:
    print(f"  Strongest angle word: '{ranked[0][0]}' at {ranked[0][1][1]:.2f}x per-account lift.")
elif untested and not losers:
    print("  No proven frame here -> this is a first-mover play; anchor it to a proven hook type to de-risk.")
print("  Rule: LOSER = has data, underperforms (pivot). UNTESTED = thin/no data (don't kill -- could be new).")
