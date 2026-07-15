#!/usr/bin/env python3
"""Layer-1 deterministic pattern matrix over ALL transcribed reels (Step 4c).

Usage:  python extract_patterns.py <project_dir>

Reads:   <project_dir>/source/competitors/transcripts/*.json  (+ client-transcripts.json)
         <project_dir>/source/competitors/reels/<h>.json      (caption/engagement join)
         <project_dir>/analysis-config.json or tiers.json     (config)
Writes:  <project_dir>/_pattern_matrix.json  (one row per reel, ~30 deterministic dims)
         <project_dir>/_pattern_stats.md     (winner-vs-loser lift, tool league,
                                              CTA payoff, cluster medians)

Config keys used (all optional beyond the tiers base):
  clusters: {"cluster-name": ["handle", ...]}   # cross-tab grouping; falls back to tiers
  themes:   {"theme-name": "regex", ...}        # same override analyze.py consumes
  tools:    {"tool-name": "regex", ...}         # overrides the generic tool lexicon

Rhetoric lexicons (contrast/hedges/curiosity/CTA/specificity) are niche-neutral
machinery and live here; per-niche knowledge belongs in the config, not this script.
Stdlib only. ASCII-safe console.
"""
import json, glob, os, re, statistics as st, sys
from collections import defaultdict

if len(sys.argv) < 2:
    print("Usage: python extract_patterns.py <project_dir>"); sys.exit(1)
RUN = os.path.abspath(sys.argv[1])
TDIR = os.path.join(RUN, "source", "competitors", "transcripts")
RDIR = os.path.join(RUN, "source", "competitors", "reels")

cfg = {}
for name in ("analysis-config.json", "tiers.json"):
    p = os.path.join(RUN, name)
    if os.path.exists(p): cfg = json.load(open(p, encoding="utf-8")); break
CLIENT = cfg.get("client", "client")
CLUSTERS = cfg.get("clusters") or {t: cfg.get(t, []) for t in ("GURU", "LARGE", "MED", "SMALL") if cfg.get(t)}
CLUSTER_OF = {h: c for c, hs in CLUSTERS.items() for h in hs}

# ---- niche-neutral rhetoric lexicons ----
CONTRAST = r"\b(but|actually|instead|however|nobody|no one|everyone|the truth|the problem|except|until|meanwhile|secret|crazy part|what's wild|plot twist|here's the thing|the real reason|wrong|mistake|stop)\b"
HEDGES = r"\b(maybe|probably|kind of|sort of|i think|i guess|perhaps|a bit|might be|possibly)\b"
CURIOSITY = r"\b(secret|nobody talks about|wait for it|you won't believe|here's why|the real reason|what nobody|until the end|watch (till|until)|stay (till|until)|most people (don't|miss))\b"
IMPERATIVE_START = r"^(stop|start|use|try|watch|listen|imagine|think|do|don't|grab|open|type|go|take|save|comment|follow|share|send|drop|check|copy|paste|build|make|write|ask)\b"
SPECIFICITY = r"(\$[\d,.]+|\b\d+%|\b\d+ ?(days?|minutes?|hours?|weeks?|months?|steps?|tools?|ways?|things?|clients?|figures?|x)\b|\b\d{2,}\b)"
ENUMERATION = r"\b(\d+|three|four|five|six|seven|eight|nine|ten) (\w+ ){0,2}(tools?|ways?|steps?|things?|prompts?|mistakes?|signs?|reasons?|hacks?|apps?|sites?|features?)\b"
CTA = {
    "comment-bait": r"\bcomment(?:\s+the\s+word)?\s+[\"']?([a-z0-9]+)[\"']?",
    "follow": r"\bfollow (me|for|and|if)\b|hit (that )?follow|give (me|us) a follow",
    "link-in-bio": r"link in (my |the )?bio",
    "save-share": r"\bsave this\b|\bshare this\b|send this to",
    "dm": r"\bdm me\b|\bmessage me\b|send me a (dm|message)",
}
TOOLS = cfg.get("tools") or {  # generic default; override per niche via config
    "claude": r"\bclaude\b", "claude-code": r"claude code", "cowork": r"\bcowork\b",
    "chatgpt": r"\bchat ?gpt\b|\bgpt-?[45o]?\b|\bopen ?ai\b", "gemini": r"\bgemini\b",
    "grok": r"\bgrok\b", "perplexity": r"\bperplexity\b", "n8n": r"\bn8n\b|\bn 8 n\b",
    "zapier": r"\bzapier\b", "make": r"\bmake\.com\b", "notion": r"\bnotion\b",
    "canva": r"\bcanva\b", "midjourney": r"\bmid ?journey\b", "sora": r"\bsora\b",
    "veo": r"\bveo\b", "heygen": r"\bhey ?gen\b", "elevenlabs": r"\beleven ?labs\b",
    "skool": r"\bskool\b", "highlevel": r"\bhigh ?level\b|\bghl\b",
}
THEMES = cfg.get("themes") or {}  # same key analyze.py reads; empty = theme dims skipped

def per100(n, words): return round(n / words * 100, 2) if words else 0
def jac(a, b):
    A, B = set(re.findall(r"[a-z']+", a.lower())), set(re.findall(r"[a-z']+", b.lower()))
    return len(A & B) / len(A | B) if A | B else 0

def row_of(handle, r, caption, likes, comments, med_views):
    txt = r["text"]; low = txt.lower(); segs = r.get("segments", [])
    dur = r.get("duration") or (segs[-1]["e"] if segs else 0)
    words = re.findall(r"[a-z0-9'$%]+", low); nw = len(words)
    if not (dur and nw and segs): return None
    first = segs[0]
    t15 = None; acc = 0
    for s in segs:
        sw = len(re.findall(r"[a-z0-9'$%]+", s["text"].lower()))
        if acc + sw >= 15 and sw:
            t15 = round(s["s"] + (s["e"] - s["s"]) * ((15 - acc) / sw), 2); break
        acc += sw
    wps = round(nw / dur, 2)
    hw = len(re.findall(r"[a-z0-9'$%]+", first["text"].lower()))
    hook_wps = round(hw / (first["e"] - first["s"]), 2) if first["e"] > first["s"] else None
    gaps = [round(segs[i+1]["s"] - segs[i]["e"], 2) for i in range(len(segs)-1)]
    you = len(re.findall(r"\byou(r|'re|'ll|'ve)?\b", low)); i_ = len(re.findall(r"\bi('m|'ve|'ll)?\b|\bmy\b|\bme\b", low))
    cta_types = []; cta_pos = None; cta_pos_s = None; cta_word = None
    for name, pat in CTA.items():
        m = re.search(pat, low)
        if m:
            cta_types.append(name)
            if name == "comment-bait" and m.groups(): cta_word = m.group(1)
            if cta_pos is None:
                ch = m.start(); acc2 = 0
                for s in segs:
                    acc2 += len(s["text"]) + 1
                    if acc2 >= ch:
                        cta_pos = round(s["s"] / dur * 100, 1); cta_pos_s = round(s["s"], 2); break
    tail = " ".join(s["text"] for s in segs if s["s"] >= dur * 0.85).lower()
    if any(re.search(p, tail) for p in CTA.values()): ending = "cta-outro"
    elif segs and jac(segs[-1]["text"], first["text"]) > 0.5: ending = "loop-back"
    else: ending = "hard-stop"
    cap = caption or ""
    cap_first = cap.split("\n")[0][:200]
    cap_rel = ("hashtag-dump" if cap.count("#") >= 5 and len(re.sub(r"#\w+", "", cap).strip()) < 40
               else "repeats-hook" if jac(cap_first, first["text"]) > 0.35
               else "complements" if cap.strip() else "none")
    views = r["views"]
    return {
        "handle": handle, "cluster": CLUSTER_OF.get(handle, "CLIENT" if handle == CLIENT else "?"),
        "rank": r.get("rank"), "url": r["url"], "views": views,
        "outlier_mult": round(views / med_views, 2) if med_views else None,
        "er": round((likes + comments) / views, 4) if views else None,
        "comment_rate": round(comments / views, 5) if views else None,
        "duration": dur, "n_words": nw, "wps": wps,
        "hook_end_seg": first["e"], "hook_end_pct": round(first["e"] / dur * 100, 1),
        "t15w": t15, "t15w_pct": (round(t15 / dur * 100, 1) if t15 else None), "hook_wps": hook_wps,
        "silence_s": round(sum(g for g in gaps if g > 0.3), 2), "max_gap": max(gaps) if gaps else 0,
        "contrast_per100": per100(len(re.findall(CONTRAST, low)), nw),
        "hedges": len(re.findall(HEDGES, low)),
        "curiosity_hits": len(re.findall(CURIOSITY, low)),
        "you_i_ratio": (round(you / i_, 2) if i_ else (you or None)),
        "specificity_per100": per100(len(re.findall(SPECIFICITY, low)), nw),
        "enumeration": bool(re.search(ENUMERATION, low)),
        "questions": txt.count("?"),
        "imperative_segs": sum(1 for s in segs if re.match(IMPERATIVE_START, s["text"].strip().lower())),
        "negation_open": bool(re.match(r"^(stop|don't|never|nobody|no one|you're (doing|using).*wrong|most people)", low.strip())),
        "tools": [t for t, p in TOOLS.items() if re.search(p, low)],
        "themes": [t for t, p in THEMES.items() if re.search(p, low)],
        "cta_types": cta_types, "cta_word": cta_word, "cta_pos_pct": cta_pos, "cta_pos_s": cta_pos_s, "ending": ending,
        "caption_rel": cap_rel, "caption_len": len(cap),
    }

def eng_index(reels_path):
    idx = {}
    try:
        d = json.load(open(reels_path, encoding="utf-8"))
        for it in d.get("reels", d.get("items", [])):
            p = it.get("post", {}); e = p.get("engagement", {})
            idx[p.get("url")] = (p.get("content", {}).get("text", ""), e.get("likes") or 0, e.get("comments") or 0)
    except Exception: pass
    return idx

rows = []
files = glob.glob(os.path.join(TDIR, "*.json"))
cpath = os.path.join(RUN, "source", "client-transcripts.json")
if os.path.exists(cpath): files.append(cpath)
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    h = d["handle"]
    rp = os.path.join(RUN, "source", "reels-full.json") if h == CLIENT else os.path.join(RDIR, f"{h}.json")
    idx = eng_index(rp)
    tv = [x["views"] for x in d.get("reels", []) if x.get("views")]
    medv = st.median(tv) if tv else 0
    for r in d.get("reels", []):
        if not r.get("text"): continue
        cap, lk, cm = idx.get(r["url"], ("", 0, 0))
        row = row_of(h, r, cap, lk, cm, medv)
        if row: rows.append(row)

json.dump(rows, open(os.path.join(RUN, "_pattern_matrix.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

W = [r for r in rows if r["rank"] == "top" and r["cluster"] != "CLIENT"]
L = [r for r in rows if r["rank"] == "bottom" and r["cluster"] != "CLIENT"]
def m(rs, k):
    xs = [r[k] for r in rs if isinstance(r.get(k), (int, float))]
    return st.median(xs) if xs else None
NUM_DIMS = ["duration","wps","hook_end_seg","hook_end_pct","t15w","t15w_pct","hook_wps",
            "silence_s","contrast_per100","hedges","curiosity_hits","you_i_ratio",
            "specificity_per100","questions","imperative_segs","er","comment_rate",
            "cta_pos_pct","cta_pos_s","caption_len"]
out = []; o = out.append
o("# Pattern Matrix - Layer 1 stats (deterministic, all transcribed reels)")
o(f"\nRows: {len(rows)} reels ({len(W)} winners / {len(L)} losers / client {sum(1 for r in rows if r['cluster']=='CLIENT')}).")
o("\n## Winner vs Loser medians (field, ex-client)")
o("\n| Dim | Winners | Losers | Lift |")
o("|---|--:|--:|--:|")
for k in NUM_DIMS:
    a, b = m(W, k), m(L, k)
    o(f"| {k} | {a if a is not None else '-'} | {b if b is not None else '-'} | {(f'{a/b:.2f}x' if a and b else '-')} |")
def share(rs, pred): return round(sum(1 for r in rs if pred(r)) / len(rs) * 100, 1) if rs else 0
o("\n## Share-of-reels flags (W% vs L%)")
o("\n| Flag | Winners % | Losers % |")
o("|---|--:|--:|")
for name, pred in [
    ("enumeration", lambda r: r["enumeration"]),
    ("negation_open", lambda r: r["negation_open"]),
    ("comment-bait CTA", lambda r: "comment-bait" in r["cta_types"]),
    ("any CTA", lambda r: bool(r["cta_types"])),
    ("ending=cta-outro", lambda r: r["ending"] == "cta-outro"),
    ("ending=loop-back", lambda r: r["ending"] == "loop-back"),
    ("caption repeats hook", lambda r: r["caption_rel"] == "repeats-hook"),
]:
    o(f"| {name} | {share(W,pred)} | {share(L,pred)} |")
o("\n## Tool league (median views of reels mentioning tool, field, n>=5)")
tv = defaultdict(list)
for r in rows:
    if r["cluster"] == "CLIENT": continue
    for t in r["tools"]: tv[t].append(r["views"])
o("\n| Tool | Reels | Med views |")
o("|---|--:|--:|")
for t in sorted(tv, key=lambda k: -st.median(tv[k])):
    if len(tv[t]) >= 5: o(f"| {t} | {len(tv[t])} | {st.median(tv[t]):,.0f} |")
o("\n## CTA mechanics (field)")
cv = defaultdict(list)
for r in rows:
    if r["cluster"] == "CLIENT": continue
    for c in (r["cta_types"] or ["none"]): cv[c].append((r["views"], r["comment_rate"] or 0))
o("\n| CTA | Reels | Med views | Med comment-rate |")
o("|---|--:|--:|--:|")
for c in sorted(cv, key=lambda k: -st.median([x[0] for x in cv[k]])):
    vs = [x[0] for x in cv[c]]; cr = [x[1] for x in cv[c]]
    o(f"| {c} | {len(vs)} | {st.median(vs):,.0f} | {st.median(cr)*100:.2f}% |")
# ---- duration sweet spot: FULL pulled population (no transcript needed) ----
BANDS = [(0,10),(10,20),(20,30),(30,45),(45,60),(60,90),(90,10**9)]
def band_name(d):
    for lo,hi in BANDS:
        if lo <= d < hi: return f"{lo}-{hi}s" if hi < 10**9 else f"{lo}s+"
    return "?"
full = []  # (duration, views, mult_vs_creator_median)
for rf in glob.glob(os.path.join(RDIR, "*.json")):
    try: dd = json.load(open(rf, encoding="utf-8"))
    except Exception: continue
    pts = []
    for it in dd.get("reels", dd.get("items", [])):
        p = it.get("post", {})
        dur = p.get("content", {}).get("duration_seconds")
        v = p.get("engagement", {}).get("views") or 0
        if dur and v: pts.append((dur, v))
    if len(pts) < 5: continue
    cmed = st.median([v for _, v in pts]) or 1
    for dur, v in pts: full.append((dur, v, v / cmed))
o("\n## Duration sweet spot (FULL pulled population, per-creator normalized)")
o(f"\nAll pulled reels with duration+views: {len(full)}. 'Med mult' = views vs that creator's own median (1.0 = typical; >1 = overperforms) — the per-creator normalization is what makes bands comparable across account sizes.")
o("\n| Band | Reels | Med views | Med mult | % over 2x own median |")
o("|---|--:|--:|--:|--:|")
for lo,hi in BANDS:
    seg = [x for x in full if lo <= x[0] < hi]
    if len(seg) < 10: continue
    nm = f"{lo}-{hi}s" if hi < 10**9 else f"{lo}s+"
    over = sum(1 for x in seg if x[2] >= 2) / len(seg) * 100
    o(f"| {nm} | {len(seg)} | {st.median([x[1] for x in seg]):,.0f} | {st.median([x[2] for x in seg]):.2f} | {over:.0f}% |")
o("\nW-vs-L durations (transcribed sample): winners med "
  f"{m(W,'duration')}s vs losers {m(L,'duration')}s.")

o("\n## Cluster medians (winners only)")
o("\n| Cluster | n | Med views | Dur | WPS | Contrast/100 | Spec/100 |")
o("|---|--:|--:|--:|--:|--:|--:|")
for c in CLUSTERS:
    cw = [r for r in W if r["cluster"] == c]
    if cw: o(f"| {c} | {len(cw)} | {m(cw,'views'):,.0f} | {m(cw,'duration')} | {m(cw,'wps')} | {m(cw,'contrast_per100')} | {m(cw,'specificity_per100')} |")
open(os.path.join(RUN, "_pattern_stats.md"), "w", encoding="utf-8").write("\n".join(out))
print(f"rows={len(rows)} winners={len(W)} losers={len(L)} -> _pattern_matrix.json + _pattern_stats.md")
