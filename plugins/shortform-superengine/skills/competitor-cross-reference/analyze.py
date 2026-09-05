# Cross-reference analysis: client vs competitors.
# Generalized: reads project dir + tiers.json for all config.
# Usage: python analyze.py <project_dir>
# Writes <project_dir>/analysis-data.md + prints findings.
import json, glob, os, re, statistics as st, sys
from collections import defaultdict, Counter

if len(sys.argv) < 2:
    print('Usage: python analyze.py <project_dir>')
    sys.exit(1)

ROOT = sys.argv[1]
def J(p): return json.load(open(p, encoding='utf-8'))

def fix(t):
    if not t: return ''
    try:
        import ftfy; return ftfy.fix_text(t)
    except Exception:
        try: return t.encode('latin-1','ignore').decode('utf-8','ignore')
        except Exception: return t

# ---- load config (analysis-config.json superset, else legacy tiers.json) ----
# Every key beyond the tiers.json base is optional + defaulted to the built-in EWH value,
# so a bare tiers.json stays on the identical code path (the regression gate can't drift).
def _load_cfg(root):
    for name in ('analysis-config.json', 'tiers.json'):
        p = os.path.join(root, name)
        if os.path.exists(p): return J(p)
    raise FileNotFoundError('no analysis-config.json or tiers.json in ' + root)
cfg = _load_cfg(ROOT)
CLIENT_HANDLE = cfg['client']
CLIENT_FOLLOWERS = cfg['client_followers']
TIERS = {
    'GURU':  cfg.get('GURU', []),
    'LARGE': cfg.get('LARGE', []),
    'MED':   cfg.get('MED', []),
    'SMALL': cfg.get('SMALL', []),
}
TIER_OF = {h:t for t,hs in TIERS.items() for h in hs}

# ---- lanes (optional; presence => lane_on enriched format) ----
LANES = cfg.get('lanes', {})
LANE_OF = {h:l for l,hs in LANES.items() for h in hs}
lane_on = bool(LANES)
CLIENT_LANE = cfg.get('client_lane')
TITLE = cfg.get('title', '# @' + CLIENT_HANDLE + ' - Cross-Reference Analysis Data (evidence appendix)')

def followers(handle):
    try: return J(os.path.join(ROOT, f'source/competitors/profiles/{handle}.json'))['data']['author'].get('followers') or 0
    except Exception: return 0

# ---- hook taxonomy (heuristic on caption line 1) ----
# base hook regexes + optional per-type lexicon extras from config.
# When hook_lexicon is absent/empty the assembled patterns equal the originals byte-for-byte.
HOOK_LEXICON = cfg.get('hook_lexicon', {})
def _alt(base, key):
    extra = HOOK_LEXICON.get(key, [])
    return base + ('|' + '|'.join(extra) if extra else '')
_MYTH   = r'\b(' + _alt('myth|stop|don.?t|never|nobody|no one|the truth|lie|isn.?t|not just|wrong|mistake', 'myth-bust/negation') + r')\b'
_CONTRA = r'\b(' + _alt('actually|unpopular|everyone|they don.?t want|real reason|secret|nobody talks', 'contrarian/curiosity') + r')\b'
_PAIN   = r'(' + _alt('if you|you.?ve been|tired of|exhausted|struggling|still|feel like|when you', 'pain-callout') + r')\b'
def hook_type(cap):
    l = fix(cap).strip().split('\n')[0].strip().lower()
    if not l: return 'none'
    if l.endswith('?') or re.match(r'^(why|what|how|is|are|can|do|does|could|should|when|which|who|ever wonder)', l): return 'question'
    if re.match(r'^\d', l) or re.search(r'^\w+\s+(ways|tips|signs|reasons|things|steps|mistakes|foods)\b', l): return 'numbered/list'
    if re.search(_MYTH, l): return 'myth-bust/negation'
    if re.search(_CONTRA, l): return 'contrarian/curiosity'
    if re.search(_PAIN, l): return 'pain-callout'
    if re.match(r'^(i |my |when i |i.?m |i.?ve )', l): return 'personal/story'
    return 'statement'

THEMES = cfg.get('themes') or {
 'thyroid': r'thyroid|hashimoto|tsh|t3|t4|hypothyroid',
 'nervous-system': r'nervous system|vagus|vagal|polyvagal|dysregulat|somatic|fight or flight|freeze|safety|regulat',
 'gut': r'\bgut\b|microbiome|digest|bloat|ibs|leaky|stomach|constipat',
 'circadian/light': r'circadian|sunlight|\blight\b|morning sun|melatonin|\bsleep\b|rhythm',
 'minerals/HTMA': r'mineral|htma|magnesium|potassium|copper|\bzinc\b|sodium|adrenal cocktail|electrolyte',
 'hormones': r'hormone|estrogen|progesterone|\bpcos\b|\bperiod\b|\bcycle\b|\bpms\b|fertilit',
 'metabolism/bloodsugar': r'metaboli|mitochond|blood sugar|glucose|insulin|\bcarbs?\b|body temp|energy production',
 'mindset/identity': r'mindset|belief|identity|\bfear\b|self-?worth|healing journey|nervous breakdown|burnout',
 'cortisol/stress': r'cortisol|stress response|chronic stress|adrenal',
}
def themes_of(cap):
    t = fix(cap).lower()
    return [name for name,pat in THEMES.items() if re.search(pat, t)]

# ---- transcript index (C7): spoken text keyed by reel url ----
# The live pipeline (transcribe_reels.py) writes source/client-transcripts.json +
# source/competitors/transcripts/<handle>.json. When transcripts exist, hook/theme
# diagnosis keys on the SPOKEN track (what actually retains, ~80% of the signal);
# captions stay as a separate packaging-surface read (<=20%). With no transcripts,
# every reel falls back to caption and output is byte-identical to the caption-only
# code path (the regression gate can't drift).
def _tx_index():
    idx = {}
    paths = [os.path.join(ROOT, 'source', 'client-transcripts.json')] + \
            sorted(glob.glob(os.path.join(ROOT, 'source', 'competitors', 'transcripts', '*.json')))
    for p in paths:
        if not os.path.exists(p): continue
        try: d = J(p)
        except Exception: continue
        for r in d.get('reels') or []:
            if r.get('url') and r.get('text'):
                idx[r['url']] = fix(r['text'])
    return idx
TX = _tx_index()

def _tx_first(t):
    t = t.strip()
    return re.split(r'(?<=[.!?])\s+', t)[0][:140] if t else ''

# primary-diagnosis wrappers: spoken first sentence when a transcript exists,
# caption line 1 otherwise. hook_type/themes_of bodies stay untouched -- both
# tracks reuse them on different inputs.
def r_hook(r):
    return hook_type(_tx_first(r['tx'])) if r.get('tx') else hook_type(r['cap'])

def r_hookline(r):
    return _tx_first(r['tx'])[:80] if r.get('tx') else r['cap'].split('\n')[0][:80]

def r_themes(r):
    # transcript + caption concatenated: spoken text dominates by length, caption
    # hashtags/keywords still register (the ~80/20 weighting)
    return themes_of((r['tx'] + '\n' + r['cap']) if r.get('tx') else r['cap'])

def r_src(r):
    return 'transcript' if r.get('tx') else 'caption'

def _epoch(pub):
    # accept epoch (int/float) or ISO-8601 string; return epoch seconds or None
    if isinstance(pub, (int, float)): return pub
    if isinstance(pub, str) and pub:
        try:
            from datetime import datetime
            return datetime.fromisoformat(pub.replace('Z', '+00:00')).timestamp()
        except Exception:
            return None
    return None

def reels_of(path):
    d = J(path); out=[]
    # puller wraps as {reels:[...]}; regression/mock data uses {items:[...]}; API list is {data:{items}}
    items = d.get('reels', d.get('items', d.get('data',{}).get('items',[])))
    for it in items:
        p = it.get('post',{}); e = p.get('engagement',{})
        out.append(dict(
            url=p.get('url'), views=e.get('views') or 0, likes=e.get('likes') or 0,
            comments=e.get('comments') or 0, cap=fix(p.get('content',{}).get('text','')),
            dur=p.get('content',{}).get('duration_seconds'), pub=_epoch(p.get('published_at')),
            tx=TX.get(p.get('url')),
        ))
    return out

# ---- load everyone ----
creators = {}  # handle -> dict
client = dict(handle=CLIENT_HANDLE, tier='CLIENT', lane=CLIENT_LANE, followers=CLIENT_FOLLOWERS,
              reels=reels_of(os.path.join(ROOT, 'source/reels-full.json')))
creators[CLIENT_HANDLE] = client
for f in glob.glob(os.path.join(ROOT, 'source/competitors/reels/*.json')):
    h = os.path.basename(f)[:-5]
    creators[h] = dict(handle=h, tier=TIER_OF.get(h,'?'), lane=LANE_OF.get(h,'?'), followers=followers(h), reels=reels_of(f))

def med(xs): return st.median(xs) if xs else 0
def creator_stats(c):
    rv=[r['views'] for r in c['reels'] if r['views']>=0]
    mv=med([r['views'] for r in c['reels']]) or 0
    er=[ (r['likes']+r['comments'])/r['views'] for r in c['reels'] if r['views']>0 ]
    cr=[ r['comments']/r['views'] for r in c['reels'] if r['views']>0 ]
    reach = (mv/c['followers']) if c['followers'] else 0
    return dict(n=len(c['reels']), med_views=mv, mean_views=(sum(rv)//len(rv) if rv else 0),
                reach_eff=reach, med_er=med(er), med_cr=med(cr),
                med_likes=med([r['likes'] for r in c['reels']]), med_cmt=med([r['comments'] for r in c['reels']]))
for h,c in creators.items(): c['stats']=creator_stats(c)

# ---- cadence (posts/week) ----
def cadence(c):
    ps=sorted([r['pub'] for r in c['reels'] if isinstance(r['pub'],(int,float))])
    if len(ps)<2: return None
    span_days=(ps[-1]-ps[0])/86400.0
    return (len(ps)/span_days*7) if span_days>0 else None
for h,c in creators.items(): c['cadence']=cadence(c)

# ================= OUTPUT =================
out=[]
def w(s=''): out.append(s)

w(TITLE)
w(f'\nGenerated from {sum(len(c["reels"]) for c in creators.values())} reels (client {len(client["reels"])} + {len(creators)-1} competitors). '
  'Engagement = views/likes/comments only (SocialCrawl drops IG saves/shares). Reach efficiency = median views / followers.\n')

# per-creator table
w('## Per-creator metrics (sorted by reach efficiency)')
if lane_on:
    w('\n| Tier | Lane | Handle | Followers | Reels | Med views | Reach-eff | Med ER | Med cmts | Posts/wk |')
    w('|---|---|---|--:|--:|--:|--:|--:|--:|--:|')
    for h,c in sorted(creators.items(), key=lambda kv:-kv[1]['stats']['reach_eff']):
        s=c['stats']; cad=f"{c['cadence']:.1f}" if c['cadence'] else '-'
        w(f"| {c['tier']} | {c.get('lane','?')} | @{h} | {c['followers']:,} | {s['n']} | {s['med_views']:,.0f} | {s['reach_eff']*100:.1f}% | {s['med_er']*100:.1f}% | {s['med_cmt']:,.0f} | {cad} |")
else:
    w('\n| Tier | Handle | Followers | Reels | Med views | Reach-eff | Med ER | Med cmts | Posts/wk |')
    w('|---|---|--:|--:|--:|--:|--:|--:|--:|')
    for h,c in sorted(creators.items(), key=lambda kv:-kv[1]['stats']['reach_eff']):
        s=c['stats']
        w(f"| {c['tier']} | @{h} | {c['followers']:,} | {s['n']} | {s['med_views']:,.0f} | {s['reach_eff']*100:.1f}% | {s['med_er']*100:.1f}% | {s['med_cmt']:,.0f} | {c['cadence']:.1f} |" if c['cadence'] else
          f"| {c['tier']} | @{h} | {c['followers']:,} | {s['n']} | {s['med_views']:,.0f} | {s['reach_eff']*100:.1f}% | {s['med_er']*100:.1f}% | {s['med_cmt']:,.0f} | - |")

# tier rollups
w('\n## Tier rollups (median of per-creator medians)')
w('\n| Group | Creators | Med reach-eff | Med ER | Med views |')
w('|---|--:|--:|--:|--:|')
def rollup(name, hs):
    cs=[creators[h] for h in hs if h in creators]
    if not cs: return
    re_=med([c['stats']['reach_eff'] for c in cs]); er_=med([c['stats']['med_er'] for c in cs]); mv_=med([c['stats']['med_views'] for c in cs])
    w(f"| {name} | {len(cs)} | {re_*100:.1f}% | {er_*100:.1f}% | {mv_:,.0f} |")
rollup('CLIENT',[CLIENT_HANDLE]); rollup('GURU',TIERS['GURU']); rollup('LARGE',TIERS['LARGE']); rollup('MED',TIERS['MED']); rollup('SMALL',TIERS['SMALL'])
if lane_on:
    for lane in LANES: rollup('-- ' + lane + ' lane', LANES[lane])

# transcript coverage (C7): drives the dual-track emit below
_n_reels_total = sum(len(c['reels']) for c in creators.values())
_n_reels_tx = sum(1 for c in creators.values() for r in c['reels'] if r.get('tx'))
TX_COVERAGE = (_n_reels_tx / _n_reels_total) if _n_reels_total else 0

# hook taxonomy — PRIMARY (spoken-first via r_hook; == caption when no transcripts)
w('\n## Hook taxonomy — field vs client (median views by hook type)')
field_hook=defaultdict(list); client_hook=defaultdict(list)
cap_field_hook=defaultdict(list); cap_client_hook=defaultdict(list)
for h,c in creators.items():
    for r in c['reels']:
        ht=r_hook(r)
        (client_hook if h==CLIENT_HANDLE else field_hook)[ht].append(r['views'])
        cht=hook_type(r['cap'])   # caption bucket: separate accumulators, never merged
        (cap_client_hook if h==CLIENT_HANDLE else cap_field_hook)[cht].append(r['views'])
w('\n| Hook type | Field n | Field med views | Client n | Client med views |')
w('|---|--:|--:|--:|--:|')
for ht in sorted(field_hook, key=lambda k:-med(field_hook[k])):
    w(f"| {ht} | {len(field_hook[ht])} | {med(field_hook[ht]):,.0f} | {len(client_hook.get(ht,[]))} | {med(client_hook.get(ht,[])):,.0f} |")

# theme prevalence + performance (field)
w('\n## Theme performance (field-wide, by median views of reels touching theme)')
theme_v=defaultdict(list); theme_client=defaultdict(list)
cap_theme_v=defaultdict(list); cap_theme_client=defaultdict(list)
for h,c in creators.items():
    for r in c['reels']:
        for th in r_themes(r):
            (theme_client if h==CLIENT_HANDLE else theme_v)[th].append(r['views'])
        for th in themes_of(r['cap']):   # caption bucket
            (cap_theme_client if h==CLIENT_HANDLE else cap_theme_v)[th].append(r['views'])
if lane_on:
    w('\n| Theme | Field reels | Field med views | Client reels | Client med views |')
    w('|---|--:|--:|--:|--:|')
    for th in sorted(theme_v, key=lambda k:-med(theme_v[k])):
        w(f"| {th} | {len(theme_v[th])} | {med(theme_v[th]):,.0f} | {len(theme_client.get(th,[]))} | {med(theme_client.get(th,[])):,.0f} |")
else:
    w('\n| Theme | Field reels | Field med views | Client reels |')
    w('|---|--:|--:|--:|')
    for th in sorted(theme_v, key=lambda k:-med(theme_v[k])):
        w(f"| {th} | {len(theme_v[th])} | {med(theme_v[th]):,.0f} | {len(theme_client.get(th,[]))} |")

# theme performance by lane (only when lanes configured)
if lane_on:
    w('\n## Theme performance by lane (median views of reels touching theme, within lane)')
    for lane in LANES:
        lane_theme=defaultdict(list)
        for h in LANES[lane]:
            c=creators.get(h)
            if not c: continue
            for r in c['reels']:
                for th in r_themes(r): lane_theme[th].append(r['views'])
        w(f'\n**{lane} lane:** ' + ', '.join(f'{th} {med(v):,.0f}({len(v)})' for th,v in sorted(lane_theme.items(), key=lambda kv:-med(kv[1]))))

# top field outliers (each creator's reels >=2.5x their own median), ranked by multiple
outliers=[]
for h,c in creators.items():
    mv=c['stats']['med_views']
    if mv<=0: continue
    for r in c['reels']:
        if r['views']>=2.5*mv:
            if lane_on:
                outliers.append((r['views']/mv, h, c['tier'], c.get('lane','?'), r['views'], r_hook(r), r_themes(r), r_hookline(r), r['url'], r_src(r)))
            else:
                outliers.append((r['views']/mv, h, c['tier'], r['views'], r_hook(r), r_themes(r), r_hookline(r), r['url'], r_src(r)))
outliers.sort(reverse=True)
if lane_on:
    w('\n\n## Top outliers (reels >=2.5x their creator’s own median) — what overperforms')
    w('\n| Mult | Handle | Tier | Lane | Views | Hook | Themes | Hook line | URL |')
    w('|--:|---|---|---|--:|---|---|---|---|')
    for m,h,t,ln,v,ht,th,line,url,src in outliers[:30]:
        w(f"| {m:.1f}x | @{h} | {t} | {ln} | {v:,} | {ht} | {','.join(th)[:24]} | {line.replace('|','/')} | {url} |")
else:
    w('\n## Top outliers (reels >=2.5x their creator\'s own median) — what overperforms')
    w('\n| Mult | Handle | Tier | Views | Hook | Themes | Hook line | URL |')
    w('|--:|---|---|--:|---|---|---|---|')
    for m,h,t,v,ht,th,line,url,src in outliers[:30]:
        w(f"| {m:.1f}x | @{h} | {t} | {v:,} | {ht} | {','.join(th)[:24]} | {line.replace('|','/')} | {url} |")

# client reels detail
w(f'\n## Client reels ({"all" if lane_on else len(client["reels"])}) — views / hook / themes')
w('\n| Views | ER | Hook | Themes | Hook line |')
w('|--:|--:|---|---|---|')
for r in sorted(client['reels'], key=lambda r:-r['views']):
    er=(r['likes']+r['comments'])/r['views']*100 if r['views'] else 0
    w(f"| {r['views']:,} | {er:.1f}% | {r_hook(r)} | {','.join(r_themes(r))[:24]} | {r_hookline(r)[:70].replace('|','/')} |")

# ---- caption patterns bucket (C7): emitted ONLY when transcripts exist. ----
# Deliberately separate from the primary (spoken) tables above: captions are the
# packaging/SEO surface — what the reel LOOKS like it's about — never the
# retention diagnosis. With no transcripts this whole section is absent and the
# md stays byte-identical to the caption-only code path.
if TX_COVERAGE > 0:
    w('\n## Caption patterns (packaging surface — separate read, never mix into the spoken diagnosis)')
    w(f'\nCaption-keyed tables ({_n_reels_tx}/{_n_reels_total} reels transcript-covered; the primary tables above key on the spoken track). '
      'Use these for packaging/SEO choices only — a caption pattern that wins here says nothing about what retains.')
    w('\n**Caption hook taxonomy — field vs client (median views by hook type)**')
    w('\n| Hook type | Field n | Field med views | Client n | Client med views |')
    w('|---|--:|--:|--:|--:|')
    for ht in sorted(cap_field_hook, key=lambda k:-med(cap_field_hook[k])):
        w(f"| {ht} | {len(cap_field_hook[ht])} | {med(cap_field_hook[ht]):,.0f} | {len(cap_client_hook.get(ht,[]))} | {med(cap_client_hook.get(ht,[])):,.0f} |")
    w('\n**Caption theme performance (field-wide)**')
    w('\n| Theme | Field reels | Field med views | Client reels | Client med views |')
    w('|---|--:|--:|--:|--:|')
    for th in sorted(cap_theme_v, key=lambda k:-med(cap_theme_v[k])):
        w(f"| {th} | {len(cap_theme_v[th])} | {med(cap_theme_v[th]):,.0f} | {len(cap_theme_client.get(th,[]))} | {med(cap_theme_client.get(th,[])):,.0f} |")

open(os.path.join(ROOT, 'analysis-data.md'),'w',encoding='utf-8').write('\n'.join(out))

# ================= CONSOLE FINDINGS =================
def asc(s): return str(s).encode('ascii','ignore').decode()
print('=== HEADLINE FINDINGS ===')
cs=client['stats']
print(f"CLIENT @{CLIENT_HANDLE}: {client['followers']:,} followers | med views {cs['med_views']:,.0f} | reach-eff {cs['reach_eff']*100:.2f}% | med ER {cs['med_er']*100:.2f}% | cadence {(client['cadence'] or 0):.1f}/wk")
print('\nREACH EFFICIENCY (med views/followers) -- client vs tiers:')
for name,hs in [('CLIENT',[CLIENT_HANDLE])]+list(TIERS.items()):
    cs2=[creators[h] for h in hs if h in creators]
    print(f"  {name:6} median reach-eff {med([c['stats']['reach_eff'] for c in cs2])*100:5.2f}%  (median ER {med([c['stats']['med_er'] for c in cs2])*100:.2f}%)")
print(f'\nCLIENT rank by reach-eff among all {len(creators)}:',
      [h for h,_ in sorted(creators.items(), key=lambda kv:-kv[1]['stats']['reach_eff'])].index(CLIENT_HANDLE)+1, f'of {len(creators)}')
print('\nHOOK TYPES by field median views (desc):')
for ht in sorted(field_hook, key=lambda k:-med(field_hook[k])):
    print(f"  {ht:22} field_med {med(field_hook[ht]):>9,.0f} (n={len(field_hook[ht]):3})  | client n={len(client_hook.get(ht,[]))} med={med(client_hook.get(ht,[])):,.0f}")
print('\nCLIENT hook mix:', asc(dict(Counter(r_hook(r) for r in client['reels']))))
print('\nTHEME field median views (desc):')
for th in sorted(theme_v, key=lambda k:-med(theme_v[k])):
    print(f"  {th:22} field_med {med(theme_v[th]):>9,.0f} (n={len(theme_v[th]):3}) | client_n={len(theme_client.get(th,[]))}")
print('\nTOP 12 OUTLIERS:')
if lane_on:
    for m,h,t,ln,v,ht,th,line,url,src in outliers[:12]:
        print(f"  {m:4.1f}x @{h:22} [{ln}] {v:>8,} [{ht}] {asc(line)[:48]}")
else:
    for m,h,t,v,ht,th,line,url,src in outliers[:12]:
        print(f"  {m:4.1f}x @{h:24} {v:>8,} [{ht}] {asc(line)[:54]}")
print('\nCADENCE: client {:.1f}/wk | field median {:.1f}/wk'.format(
    client['cadence'] or 0, med([c['cadence'] for h,c in creators.items() if c['cadence'] and h!=CLIENT_HANDLE])))
if TX_COVERAGE > 0:
    print(f'\nTRANSCRIPT COVERAGE: {_n_reels_tx}/{_n_reels_total} reels ({TX_COVERAGE*100:.0f}%) -- hooks/themes keyed on the SPOKEN track; caption patterns kept as a separate packaging-surface read')
print('\nwrote analysis-data.md')

# ================= analysis-data.json (core->format interface; additive LAST write) =================
# Machine-readable twin of the md, consumed by format engines (reel-scripter, ...).
# SILENT on stdout (a print here would break the EWH stdout oracle) and GUARDED
# (never crashes the run — md + console stay authoritative). Lane-keyed blocks omitted when lane-free.
try:
    from datetime import datetime as _dt, timezone as _tz
    # ---- schema 1.3 helpers (G17, 08.27.26) --------------------------------
    # meta.generated_at: this emit sits in a bare try/except that KEEPS the previous
    # analysis-data.json on any error, so a stale file is indistinguishable from a
    # fresh one. A generation stamp makes staleness visible.
    _now_dt = _dt.now(_tz.utc)
    _now_ts = _now_dt.timestamp()
    def _iso(ts): return _dt.fromtimestamp(ts, _tz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    _gen_at = _iso(_now_ts)

    # Period window, derived from the project's OWN pull log: _delta/<YYYY-MM-DD>[-suffix].
    # The NEWEST dir is the pull that produced this corpus, so the period that pull
    # covers OPENS at the pull before it -> window = [previous pull, generation time].
    # Deliberately NOT derived from history/ snapshots: on 08.27.26 the newest snapshot
    # and the newest _delta dir disagreed by 22 days.
    # CONVENTION: each history/ snapshot answers for its own day (it carries the literal
    # window_from/window_to it was generated with), so retroactive per-scan filtering
    # comes free -- read the snapshot for that day instead of recomputing a window.
    def _window_from_delta(root, now_ts):
        ddir = os.path.join(root, '_delta')
        ds = set()
        if os.path.isdir(ddir):
            for name in os.listdir(ddir):
                mt = re.match(r'^(\d{4}-\d{2}-\d{2})', name)
                if mt and os.path.isdir(os.path.join(ddir, name)):
                    ds.add(mt.group(1))
        ds = sorted(ds)
        if len(ds) >= 2: d = ds[-2]      # the pull before the one that built this corpus
        elif ds:         d = ds[-1]      # only one pull on record -> it opens the window
        else:            return now_ts - 7 * 86400   # no pull log -> documented 7d default
        return _dt.fromisoformat(d + 'T00:00:00+00:00').timestamp()
    _win_from_ts = _window_from_delta(ROOT, _now_ts)
    _win_from = _iso(_win_from_ts)

    def _creator_obj(c):
        s = c['stats']
        return {'handle': c['handle'], 'tier': c['tier'], 'lane': c.get('lane'),
                'followers': c['followers'],
                'cadence': (round(c['cadence'], 4) if c['cadence'] else c['cadence']),
                'stats': {'n': s['n'], 'med_views': s['med_views'],
                          'reach_eff': round(s['reach_eff'], 6), 'med_er': round(s['med_er'], 6),
                          'med_cmt': s['med_cmt']},
                'hook_mix': dict(Counter(r_hook(r) for r in c['reels']))}
    def _rollup_obj(name, hs):
        cs = [creators[h] for h in hs if h in creators]
        if not cs: return None
        return {'group': name, 'creators': len(cs),
                'med_reach_eff': round(med([c['stats']['reach_eff'] for c in cs]), 6),
                'med_er': round(med([c['stats']['med_er'] for c in cs]), 6),
                'med_views': med([c['stats']['med_views'] for c in cs])}
    _rollups = {'tiers': [r for r in [_rollup_obj('CLIENT', [CLIENT_HANDLE]),
                                      _rollup_obj('GURU', TIERS['GURU']),
                                      _rollup_obj('LARGE', TIERS['LARGE']),
                                      _rollup_obj('MED', TIERS['MED']),
                                      _rollup_obj('SMALL', TIERS['SMALL'])] if r]}
    if lane_on:
        _rollups['lanes'] = [r for r in (_rollup_obj(l, LANES[l]) for l in LANES) if r]
    _hooktax = [{'hook': ht, 'field_n': len(field_hook[ht]), 'field_med_views': med(field_hook[ht]),
                 'client_n': len(client_hook.get(ht, [])), 'client_med_views': med(client_hook.get(ht, []))}
                for ht in sorted(field_hook, key=lambda k: -med(field_hook[k]))]
    _themeperf = []
    for th in sorted(theme_v, key=lambda k: -med(theme_v[k])):
        e = {'theme': th, 'field_reels': len(theme_v[th]), 'field_med_views': med(theme_v[th]),
             'client_reels': len(theme_client.get(th, [])), 'client_med_views': med(theme_client.get(th, []))}
        if lane_on:
            bl = {}
            for l in LANES:
                vs = []
                for h in LANES[l]:
                    c = creators.get(h)
                    if not c: continue
                    for r in c['reels']:
                        if th in r_themes(r): vs.append(r['views'])
                if vs: bl[l] = {'med_views': med(vs), 'n': len(vs)}
            e['by_lane'] = bl
        _themeperf.append(e)
    _total_client = len(client['reels'])
    _total_field = sum(len(c['reels']) for h, c in creators.items() if h != CLIENT_HANDLE)
    _field_theme_max = max((med(theme_v[t]) for t in theme_v), default=1) or 1
    _gaps = []
    for th in sorted(theme_v, key=lambda k: -med(theme_v[k])):
        fr = len(theme_v[th]); cr = len(theme_client.get(th, []))
        if fr < 5: continue
        fmv = med(theme_v[th])
        fshare = fr / _total_field if _total_field else 0
        cshare = cr / _total_client if _total_client else 0
        oppo = round(fmv / _field_theme_max * 100)  # 0-100 opportunity = field value vs the top theme
        if cr == 0:
            _gaps.append({'theme': th, 'reason': 'absent', 'field_med_views': fmv,
                          'field_reels': fr, 'client_reels': cr,
                          'client_med_views': med(theme_client.get(th, [])),
                          'headline': f'Zero reels on {th} — the field runs {fr} at {fmv:,.0f} median views.',
                          'why': f'Pure whitespace: the field proves demand on {th} and the client has posted nothing.',
                          'oppo': oppo})
        elif cshare < 0.5 * fshare:
            _gaps.append({'theme': th, 'reason': 'underweight', 'field_med_views': fmv,
                          'field_reels': fr, 'client_reels': cr,
                          'client_med_views': med(theme_client.get(th, [])),
                          'headline': f'Thin on {th} — {cr} client reels vs the field’s {fr} at {fmv:,.0f} median views.',
                          'why': f'The field leans into {th} far harder than the client; reach is being left on the table.',
                          'oppo': oppo})
    # Outlier records are built ONCE over the FULL >=2.5x population and then sliced.
    # `outliers` stays the historic all-time top-30 leaderboard and is byte-identical
    # to the pre-1.3 emit: it is sliced from the UNFILTERED list and the enumerate index i
    # is the same for the first 30 entries, so the `{handle}-{i}` id fallback cannot drift.
    # The client filter is applied AFTER that slice, never before it, so the top-30 cannot
    # move even if a client reel were ever to rank into it.
    _oj_unfiltered = []
    for i, tup in enumerate(outliers):
        if lane_on: m, h, t, ln, v, ht, th, line, url, src = tup
        else: m, h, t, v, ht, th, line, url, src = tup; ln = None
        _sc = re.search(r'/reel/([^/]+)/', url or '')
        _rid = _sc.group(1) if _sc else f'{h}-{i}'
        # dashboard reel-card aliases (id/outlier/creator/title) alongside the native keys
        _oj_unfiltered.append({'id': _rid, 'mult': round(m, 3), 'outlier': round(m, 3),
                    'handle': h, 'creator': '@' + h, 'tier': t, 'lane': ln, 'views': v,
                    'hook': ht, 'themes': th, 'hook_line': line, 'title': line, 'url': url,
                    'src': src})
    _oj = _oj_unfiltered[:30]
    # outliers_full is the FIELD population: the client is excluded (Joe's ruling 08.28.26),
    # so "field outliers" is literally true wherever a consumer reads it -- reel-scripter's
    # theme x hook and opener mining were previously counting the client's own reels as
    # evidence about the field. `outliers` above is deliberately sliced BEFORE this filter.
    _oj_all = [_r for _r in _oj_unfiltered if _r['handle'] != CLIENT_HANDLE]

    # ---- period breakouts (schema 1.3) -------------------------------------
    # What actually broke out INSIDE the window, which the top-30 leaderboard
    # structurally cannot answer (its floor sat at 87.4x on 08.27.26, so no reel
    # published this period could ever enter it -- G17, a 38x under-report).
    # Uncapped, no transcript requirement, client excluded (a client reel is not a
    # field breakout). Same record shape as `outliers`, plus published_at.
    def _period_breakouts_block():
        rows, skipped = [], []
        for h, c in creators.items():
            if h == CLIENT_HANDLE:
                continue
            # Denominator: this creator's ALL-TIME median views over ALL their reels,
            # zeros included -- the SAME median `outliers` uses (c['stats']['med_views']),
            # so the two views cannot disagree about what "2.5x their own median" means.
            # The guard is what makes it >0: a creator whose all-reels median is <=0 (more
            # than half their reels report no views at all) is SKIPPED entirely rather than
            # divided by. Hence the label `..._gt0_...` -- the denominator is guaranteed
            # positive by the skip, not by pre-filtering the sample.
            # (Orchestrator ruling 08.28.26. Pre-filtering to views>0 instead was measured
            # to skip 0 creators and silently hand three zero-view creators a synthetic
            # denominator they had not earned.)
            mv = med([r['views'] for r in c['reels']])
            if mv <= 0:
                skipped.append(h)
                continue
            for r in c['reels']:
                pub = r.get('pub')
                if pub is None:            # None-publication-date guard: an undated reel
                    continue               # cannot be placed in a window -- never counted
                if pub < _win_from_ts or pub > _now_ts:
                    continue
                if r['views'] < 2.5 * mv:
                    continue
                _sc2 = re.search(r'/reel/([^/]+)/', r['url'] or '')
                _line = r_hookline(r)
                rows.append({'id': _sc2.group(1) if _sc2 else f'{h}-{pub:.0f}',
                             'mult': round(r['views'] / mv, 3), 'outlier': round(r['views'] / mv, 3),
                             'handle': h, 'creator': '@' + h, 'tier': c['tier'], 'lane': c.get('lane'),
                             'views': r['views'], 'hook': r_hook(r), 'themes': r_themes(r),
                             'hook_line': _line, 'title': _line, 'url': r['url'], 'src': r_src(r),
                             'published_at': _iso(pub)})
        rows.sort(key=lambda x: (-x['mult'], x['handle'], x['url'] or ''))
        return {'window_from': _win_from, 'window_to': _gen_at,
                'denominator': 'all_time_median_views_gt0_at_generation',
                'client_excluded': CLIENT_HANDLE,
                'n': len(rows), 'creators_skipped_median_le_0': len(skipped),
                'creators_skipped': sorted(skipped),
                'note': ('Reels PUBLISHED inside [window_from, window_to], scored against each '
                         'creator\'s own all-time median views over ALL their reels (zeros '
                         'included -- the same median `outliers` uses), measured at generation '
                         'time. A creator whose median is <=0 is SKIPPED, never divided by, which '
                         'is what guarantees the denominator is >0 (see creators_skipped). '
                         'Uncapped and transcript-agnostic. This is the "what '
                         'broke out this period" answer; `outliers` is the all-time top-30 hall of '
                         'fame and `outliers_full` the uncapped all-time field population -- neither can '
                         'answer it. The window opens at the previous _delta pull. Each history/ '
                         'snapshot answers for its own day because it carries these literal '
                         'timestamps, so retroactive per-scan filtering comes free: read the '
                         'snapshot for that day instead of recomputing a window.'),
                'reels': rows}
    _data = {'client': _creator_obj(client),
             'creators': [_creator_obj(c) for h, c in sorted(creators.items(), key=lambda kv: -kv[1]['stats']['reach_eff'])],
             'rollups': _rollups, 'hook_taxonomy': _hooktax, 'theme_performance': _themeperf,
             'gaps': _gaps, 'outliers': _oj,
             'meta': {'client_handle': CLIENT_HANDLE,
                      'total_reels': sum(len(c['reels']) for c in creators.values()),
                      'n_competitors': len(creators) - 1, 'lane_on': lane_on,
                      'themes': list(THEMES.keys()), 'source': 'competitor-cross-reference/analyze.py',
                      'transcript_coverage': round(TX_COVERAGE, 4),
                      'schema_version': '1.3',
                      'generated_at': _gen_at}}
    # captions bucket (C7, additive): the caption-keyed read, separate from the
    # primary spoken-keyed hook_taxonomy/theme_performance above. Present only
    # when transcripts exist (without them primary IS caption-keyed already).
    if TX_COVERAGE > 0:
        _data['captions'] = {
            'note': 'caption-keyed patterns (packaging surface) -- never mix into the spoken diagnosis',
            'hook_taxonomy': [{'hook': ht, 'field_n': len(cap_field_hook[ht]),
                               'field_med_views': med(cap_field_hook[ht]),
                               'client_n': len(cap_client_hook.get(ht, [])),
                               'client_med_views': med(cap_client_hook.get(ht, []))}
                              for ht in sorted(cap_field_hook, key=lambda k: -med(cap_field_hook[k]))],
            'theme_performance': [{'theme': th, 'field_reels': len(cap_theme_v[th]),
                                   'field_med_views': med(cap_theme_v[th]),
                                   'client_reels': len(cap_theme_client.get(th, [])),
                                   'client_med_views': med(cap_theme_client.get(th, []))}
                                  for th in sorted(cap_theme_v, key=lambda k: -med(cap_theme_v[k]))]}
    # ---- schema 1.3 keys, appended AFTER `captions` -------------------------
    # Insertion order matters: every byte before this point is unchanged from 1.2
    # except meta.schema_version and the added meta.generated_at.
    _data['outliers_full'] = _oj_all              # uncapped all-time >=2.5x FIELD population (client excluded)
    _data['period_breakouts'] = _period_breakouts_block()
    open(os.path.join(ROOT, 'analysis-data.json'), 'w', encoding='utf-8').write(
        json.dumps(_data, indent=2, ensure_ascii=False))
except Exception as _e:
    print('WARN: analysis-data.json emit skipped:', _e, file=sys.stderr)
