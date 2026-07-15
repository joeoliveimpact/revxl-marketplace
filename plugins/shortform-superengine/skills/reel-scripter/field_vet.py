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

Verdict bands (vs the field's own median views): >=1.5x WINNER, 0.8-1.5x NEUTRAL,
<0.8x LOSER. n<5 = THIN (treat as a hint, not a rule — the firewall's min-n logic).
Stdlib only. Deterministic. utf-8 reads; ASCII-safe stdout.
"""
import json, glob, os, re, sys, statistics as st

if len(sys.argv) < 3:
    print("Usage: python field_vet.py <project_dir> <keyword> [keyword2 ...]"); sys.exit(1)
ROOT = os.path.abspath(sys.argv[1])
KEYWORDS = sys.argv[2:]

def J(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}

# ---- spoken track (PRIMARY) ----
spoken = []  # (text_lower, views)
tpaths = sorted(glob.glob(os.path.join(ROOT, "source", "competitors", "transcripts", "*.json")))
cp = os.path.join(ROOT, "source", "client-transcripts.json")
if os.path.exists(cp): tpaths.append(cp)
for p in tpaths:
    for r in J(p).get("reels", []):
        t = (r.get("text") or "").lower(); v = r.get("views") or 0
        if t and v: spoken.append((t, v))

# ---- caption track (SECONDARY, kept separate per C7) ----
caption = []
def _reels_of(path, client=False):
    d = J(path); out = []
    for it in d.get("reels", d.get("items", [])):
        p = it.get("post", {}); e = p.get("engagement", {})
        txt = (p.get("content", {}).get("text", "") or "").lower(); v = e.get("views") or 0
        if txt and v: out.append((txt, v))
    return out
for p in sorted(glob.glob(os.path.join(ROOT, "source", "competitors", "reels", "*.json"))):
    caption += _reels_of(p)
rf = os.path.join(ROOT, "source", "reels-full.json")
if os.path.exists(rf): caption += _reels_of(rf)

if not spoken and not caption:
    print("No field data found under", ROOT); sys.exit(1)

def field_median(rows): return st.median([v for _, v in rows]) if rows else 0
SPOKEN_MED = field_median(spoken)
CAPTION_MED = field_median(caption)

def band(mult, n):
    if n < 5: return "THIN"
    if mult >= 1.5: return "WINNER"
    if mult >= 0.8: return "NEUTRAL"
    return "LOSER"

def scan(rows, med, kw):
    pat = re.compile(r"\b" + re.escape(kw.lower()) + r"", re.I) if kw.isalnum() else re.compile(re.escape(kw.lower()), re.I)
    hits = [v for t, v in rows if pat.search(t)]
    if not hits: return (0, 0, 0.0, "NONE")
    m = st.median(hits); mult = (m / med) if med else 0
    return (len(hits), m, mult, band(mult, len(hits)))

print(f"FIELD VET  |  project: {os.path.basename(ROOT)}")
print(f"spoken field median: {SPOKEN_MED:,.0f} views (n={len(spoken)})  |  caption field median: {CAPTION_MED:,.0f} (n={len(caption)})")
print(f"\n{'keyword':16} {'spoken n':>8} {'spoken med':>11} {'vs field':>9} {'verdict':>8}  |  {'cap n':>5} {'cap med':>9} {'vs':>6}")
verdicts = {}
for kw in KEYWORDS:
    sn, sm, smult, sv = scan(spoken, SPOKEN_MED, kw)
    cn, cm, cmult, cv = scan(caption, CAPTION_MED, kw)
    verdicts[kw] = (sv, smult, sn)
    print(f"{kw[:16]:16} {sn:>8} {sm:>11,.0f} {smult:>8.2f}x {sv:>8}  |  {cn:>5} {cm:>9,.0f} {cmult:>5.2f}x")

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
    print(f"  Strongest angle word: '{ranked[0][0]}' at {ranked[0][1][1]:.2f}x field median.")
elif untested and not losers:
    print("  No proven frame here -> this is a first-mover play; anchor it to a proven hook type to de-risk.")
print("  Rule: LOSER = has data, underperforms (pivot). UNTESTED = thin/no data (don't kill -- could be new).")
