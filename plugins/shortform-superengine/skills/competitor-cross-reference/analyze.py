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

def reels_of(path):
    d = J(path); out=[]
    for it in d.get('items', d.get('data',{}).get('items',[])):
        p = it.get('post',{}); e = p.get('engagement',{})
        out.append(dict(
            url=p.get('url'), views=e.get('views') or 0, likes=e.get('likes') or 0,
            comments=e.get('comments') or 0, cap=fix(p.get('content',{}).get('text','')),
            dur=p.get('content',{}).get('duration_seconds'), pub=p.get('published_at'),
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
        w(f"| {c['tier']} | @{h} | {c['followers']:,} | {s['n']} | {s['med_views']:,.0f} | {s['reach_eff']*100:.1f}% | {s['med_er']*100:.1f}% | {s['med_cmt']:,.0f} | {c['cadence']:.1f}" if c['cadence'] else
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
rollup('CLIENT',[CLIENT_HANDLE]); rollup('LARGE',TIERS['LARGE']); rollup('MED',TIERS['MED']); rollup('SMALL',TIERS['SMALL'])
if lane_on:
    for lane in LANES: rollup('-- ' + lane + ' lane', LANES[lane])

# hook taxonomy
w('\n## Hook taxonomy — field vs client (median views by hook type)')
field_hook=defaultdict(list); client_hook=defaultdict(list)
for h,c in creators.items():
    for r in c['reels']:
        ht=hook_type(r['cap'])
        (client_hook if h==CLIENT_HANDLE else field_hook)[ht].append(r['views'])
w('\n| Hook type | Field n | Field med views | Client n | Client med views |')
w('|---|--:|--:|--:|--:|')
for ht in sorted(field_hook, key=lambda k:-med(field_hook[k])):
    w(f"| {ht} | {len(field_hook[ht])} | {med(field_hook[ht]):,.0f} | {len(client_hook.get(ht,[]))} | {med(client_hook.get(ht,[])):,.0f} |")

# theme prevalence + performance (field)
w('\n## Theme performance (field-wide, by median views of reels touching theme)')
theme_v=defaultdict(list); theme_client=defaultdict(list)
for h,c in creators.items():
    for r in c['reels']:
        for th in themes_of(r['cap']):
            (theme_client if h==CLIENT_HANDLE else theme_v)[th].append(r['views'])
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
                for th in themes_of(r['cap']): lane_theme[th].append(r['views'])
        w(f'\n**{lane} lane:** ' + ', '.join(f'{th} {med(v):,.0f}({len(v)})' for th,v in sorted(lane_theme.items(), key=lambda kv:-med(kv[1]))))

# top field outliers (each creator's reels >=2.5x their own median), ranked by multiple
outliers=[]
for h,c in creators.items():
    mv=c['stats']['med_views']
    if mv<=0: continue
    for r in c['reels']:
        if r['views']>=2.5*mv:
            if lane_on:
                outliers.append((r['views']/mv, h, c['tier'], c.get('lane','?'), r['views'], hook_type(r['cap']), themes_of(r['cap']), r['cap'].split('\n')[0][:80], r['url']))
            else:
                outliers.append((r['views']/mv, h, c['tier'], r['views'], hook_type(r['cap']), themes_of(r['cap']), r['cap'].split('\n')[0][:80], r['url']))
outliers.sort(reverse=True)
if lane_on:
    w('\n\n## Top outliers (reels >=2.5x their creator’s own median) — what overperforms')
    w('\n| Mult | Handle | Tier | Lane | Views | Hook | Themes | Hook line | URL |')
    w('|--:|---|---|---|--:|---|---|---|---|')
    for m,h,t,ln,v,ht,th,line,url in outliers[:30]:
        w(f"| {m:.1f}x | @{h} | {t} | {ln} | {v:,} | {ht} | {','.join(th)[:24]} | {line.replace('|','/')} | {url} |")
else:
    w('\n## Top outliers (reels >=2.5x their creator\'s own median) — what overperforms')
    w('\n| Mult | Handle | Tier | Views | Hook | Themes | Hook line | URL |')
    w('|--:|---|---|--:|---|---|---|---|')
    for m,h,t,v,ht,th,line,url in outliers[:30]:
        w(f"| {m:.1f}x | @{h} | {t} | {v:,} | {ht} | {','.join(th)[:24]} | {line.replace('|','/')} | {url} |")

# client reels detail
w(f'\n## Client reels ({"all" if lane_on else len(client["reels"])}) — views / hook / themes')
w('\n| Views | ER | Hook | Themes | Hook line |')
w('|--:|--:|---|---|---|')
for r in sorted(client['reels'], key=lambda r:-r['views']):
    er=(r['likes']+r['comments'])/r['views']*100 if r['views'] else 0
    w(f"| {r['views']:,} | {er:.1f}% | {hook_type(r['cap'])} | {','.join(themes_of(r['cap']))[:24]} | {r['cap'].split(chr(10))[0][:70].replace('|','/')} |")

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
print('\nCLIENT hook mix:', asc(dict(Counter(hook_type(r['cap']) for r in client['reels']))))
print('\nTHEME field median views (desc):')
for th in sorted(theme_v, key=lambda k:-med(theme_v[k])):
    print(f"  {th:22} field_med {med(theme_v[th]):>9,.0f} (n={len(theme_v[th]):3}) | client_n={len(theme_client.get(th,[]))}")
print('\nTOP 12 OUTLIERS:')
if lane_on:
    for m,h,t,ln,v,ht,th,line,url in outliers[:12]:
        print(f"  {m:4.1f}x @{h:22} [{ln}] {v:>8,} [{ht}] {asc(line)[:48]}")
else:
    for m,h,t,v,ht,th,line,url in outliers[:12]:
        print(f"  {m:4.1f}x @{h:24} {v:>8,} [{ht}] {asc(line)[:54]}")
print('\nCADENCE: client {:.1f}/wk | field median {:.1f}/wk'.format(
    client['cadence'] or 0, med([c['cadence'] for h,c in creators.items() if c['cadence'] and h!=CLIENT_HANDLE])))
print('\nwrote analysis-data.md')

# ================= analysis-data.json (core->format interface; additive LAST write) =================
# Machine-readable twin of the md, consumed by format engines (reel-scripter, ...).
# SILENT on stdout (a print here would break the EWH stdout oracle) and GUARDED
# (never crashes the run — md + console stay authoritative). Lane-keyed blocks omitted when lane-free.
try:
    def _creator_obj(c):
        s = c['stats']
        return {'handle': c['handle'], 'tier': c['tier'], 'lane': c.get('lane'),
                'followers': c['followers'],
                'cadence': (round(c['cadence'], 4) if c['cadence'] else c['cadence']),
                'stats': {'n': s['n'], 'med_views': s['med_views'],
                          'reach_eff': round(s['reach_eff'], 6), 'med_er': round(s['med_er'], 6),
                          'med_cmt': s['med_cmt']}}
    def _rollup_obj(name, hs):
        cs = [creators[h] for h in hs if h in creators]
        if not cs: return None
        return {'group': name, 'creators': len(cs),
                'med_reach_eff': round(med([c['stats']['reach_eff'] for c in cs]), 6),
                'med_er': round(med([c['stats']['med_er'] for c in cs]), 6),
                'med_views': med([c['stats']['med_views'] for c in cs])}
    _rollups = {'tiers': [r for r in [_rollup_obj('CLIENT', [CLIENT_HANDLE]),
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
                        if th in themes_of(r['cap']): vs.append(r['views'])
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
                          'headline': f'Zero reels on {th} — the field runs {fr} at {fmv:,.0f} median views.',
                          'why': f'Pure whitespace: the field proves demand on {th} and the client has posted nothing.',
                          'oppo': oppo})
        elif cshare < 0.5 * fshare:
            _gaps.append({'theme': th, 'reason': 'underweight', 'field_med_views': fmv,
                          'field_reels': fr, 'client_reels': cr,
                          'headline': f'Thin on {th} — {cr} client reels vs the field’s {fr} at {fmv:,.0f} median views.',
                          'why': f'The field leans into {th} far harder than the client; reach is being left on the table.',
                          'oppo': oppo})
    _oj = []
    for i, tup in enumerate(outliers[:30]):
        if lane_on: m, h, t, ln, v, ht, th, line, url = tup
        else: m, h, t, v, ht, th, line, url = tup; ln = None
        _sc = re.search(r'/reel/([^/]+)/', url or '')
        _rid = _sc.group(1) if _sc else f'{h}-{i}'
        # dashboard reel-card aliases (id/outlier/creator/title) alongside the native keys
        _oj.append({'id': _rid, 'mult': round(m, 3), 'outlier': round(m, 3),
                    'handle': h, 'creator': '@' + h, 'tier': t, 'lane': ln, 'views': v,
                    'hook': ht, 'themes': th, 'hook_line': line, 'title': line, 'url': url})
    _data = {'client': _creator_obj(client),
             'creators': [_creator_obj(c) for h, c in sorted(creators.items(), key=lambda kv: -kv[1]['stats']['reach_eff'])],
             'rollups': _rollups, 'hook_taxonomy': _hooktax, 'theme_performance': _themeperf,
             'gaps': _gaps, 'outliers': _oj,
             'meta': {'client_handle': CLIENT_HANDLE,
                      'total_reels': sum(len(c['reels']) for c in creators.values()),
                      'n_competitors': len(creators) - 1, 'lane_on': lane_on,
                      'themes': list(THEMES.keys()), 'source': 'competitor-cross-reference/analyze.py',
                      'schema_version': '1.0'}}
    open(os.path.join(ROOT, 'analysis-data.json'), 'w', encoding='utf-8').write(
        json.dumps(_data, indent=2, ensure_ascii=False))
except Exception as _e:
    print('WARN: analysis-data.json emit skipped:', _e, file=sys.stderr)
