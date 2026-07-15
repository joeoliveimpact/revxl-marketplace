#!/usr/bin/env python3
"""Stratified beat-map selection for the Layer-2 semantic pass (Step 4c).

Usage:  python select_beatmap_set.py <project_dir> [n_per_side]
        n_per_side default 3 -> per cluster: 3 winners + 3 losers.

Clusters come from analysis-config.json "clusters" ({name:[handles]}), falling back
to the tier lists (GURU/LARGE/MED/SMALL). Winners = highest-view transcribed reels
in the cluster, losers = lowest-view; distinct handles preferred within a side.
Only reels with a usable transcript (text present, duration >= 10s) qualify.

Writes <project_dir>/_beatmap_set.json (full transcript + segments per pick) and
prints the pick table. The semantic mapping itself (hook type, 4 Hook Killers,
re-hook devices, payoff, open-loop integrity, why-won/why-lost) is Claude's job —
one reel at a time, reading the segments; it is NOT automated here.
"""
import json, glob, os, sys

if len(sys.argv) < 2:
    print("Usage: python select_beatmap_set.py <project_dir> [n_per_side]"); sys.exit(1)
RUN = os.path.abspath(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
TDIR = os.path.join(RUN, "source", "competitors", "transcripts")

cfg = {}
for name in ("analysis-config.json", "tiers.json"):
    p = os.path.join(RUN, name)
    if os.path.exists(p): cfg = json.load(open(p, encoding="utf-8")); break
CLUSTERS = cfg.get("clusters") or {t: cfg.get(t, []) for t in ("GURU", "LARGE", "MED", "SMALL") if cfg.get(t)}
if not CLUSTERS:
    print("No clusters or tiers in config — nothing to stratify."); sys.exit(1)
CLUSTER_OF = {h: c for c, hs in CLUSTERS.items() for h in hs}

pool = []
for f in glob.glob(os.path.join(TDIR, "*.json")):
    h = os.path.basename(f)[:-5]
    cluster = CLUSTER_OF.get(h)
    if not cluster: continue
    d = json.load(open(f, encoding="utf-8"))
    for r in d.get("reels", []):
        if not r.get("text") or (r.get("duration") or 0) < 10: continue
        pool.append(dict(cluster=cluster, handle=h, views=r["views"], rank=r["rank"],
                         url=r["url"], duration=r["duration"], text=r["text"],
                         segments=r.get("segments", [])))

def pick(seq, n):
    out, seen = [], set()
    for p in seq:
        if p["handle"] in seen: continue
        out.append(p); seen.add(p["handle"])
        if len(out) == n: return out
    for p in seq:
        if p not in out:
            out.append(p)
            if len(out) == n: break
    return out

sel = {}
for c in CLUSTERS:
    cp = sorted([p for p in pool if p["cluster"] == c], key=lambda p: -p["views"])
    if len(cp) < 2 * N: print(f"WARN {c}: only {len(cp)} usable reels")
    if not cp: continue
    sel[c] = {"winners": pick(cp, N), "losers": pick(list(reversed(cp)), N)}

json.dump(sel, open(os.path.join(RUN, "_beatmap_set.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for c, g in sel.items():
    print(f"\n{c}")
    for w in g["winners"]: print(f"  WIN  {w['views']:>10,} @{w['handle']} {w['duration']:.0f}s")
    for l in g["losers"]:  print(f"  LOSE {l['views']:>10,} @{l['handle']} {l['duration']:.0f}s")
print("\nwrote _beatmap_set.json")
