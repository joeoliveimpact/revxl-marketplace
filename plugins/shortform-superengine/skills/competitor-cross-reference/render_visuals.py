#!/usr/bin/env python3
"""render_visuals.py — deterministic HTML visual pack from analysis-data.json.

Reads ONLY the core->format contract (analysis-data.json, schema 1.x) plus
optional strategy-roadmap.md (written section) and optional history snapshots.
Outputs self-contained offline HTML (Chart.js inlined, zero network) to
<project>/visuals/. Byte-identical re-runs on identical inputs (--stamp is the
only injected label). No LLM anywhere in this path.

  python render_visuals.py <project_dir> [--prev <old.json>] [--stamp "<label>"]
                           [--out <dir>] [--split]

Design system: dataviz-validated palette (CVD-safe), thin marks, hairline grid,
table-view twin per chart. Brand tokens override via <project>/visual-theme.json
{"brand": "#hex", "accent": "#hex", "logo_text": "..."}.
"""
import argparse, html, json, io, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_shared', 'lib'))
from reel_io import load_analysis_json  # noqa: E402

CHARTJS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_shared', 'lib', 'chart.umd.min.js')

DEFAULT_THEME = {'brand': '#2a78d6', 'accent': '#1baf7a', 'logo_text': ''}
TIER_ORDER = ['CLIENT', 'LARGE', 'MED', 'SMALL']
TIER_COLORS = {'CLIENT': '@@BRAND@@', 'LARGE': '#1baf7a', 'MED': '#eda100', 'SMALL': '#008300'}


def esc(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def js_data(obj):
    return json.dumps(obj, ensure_ascii=False).replace('</', '<\\/')


def load_chartjs():
    if not os.path.isfile(CHARTJS_PATH):
        print('ERROR: vendored Chart.js missing at ' + CHARTJS_PATH)
        print('Re-vendor per skills/_shared/lib/README-chartjs.md — no CDN fallback by design.')
        sys.exit(1)
    return io.open(CHARTJS_PATH, encoding='utf-8').read()


def load_theme(root):
    t = dict(DEFAULT_THEME)
    p = os.path.join(root, 'visual-theme.json')
    if os.path.isfile(p):
        try:
            user = json.load(io.open(p, encoding='utf-8'))
            for k in DEFAULT_THEME:
                if isinstance(user.get(k), str) and (k == 'logo_text' or re.match(r'^#[0-9a-fA-F]{6}$', user[k])):
                    t[k] = user[k]
        except (json.JSONDecodeError, OSError):
            print('WARN: visual-theme.json unreadable - using house theme')
    return t


def check_version(data):
    v = str(data.get('meta', {}).get('schema_version', '0'))
    major = v.split('.')[0]
    if major != '1':
        print('ERROR: analysis-data.json schema major version %s is unsupported (need 1.x). Re-run analyze.py.' % v)
        sys.exit(1)
    if v not in ('1.0', '1.1'):
        print('WARN: schema %s is newer than this renderer knows (1.1) - unknown keys ignored.' % v)
    return v


def md_to_html(text):
    """Minimal deterministic markdown -> HTML for the roadmap include."""
    out, in_list = [], False
    for raw in text.splitlines():
        line = raw.rstrip()
        line = re.sub(r'\*\*(.+?)\*\*', lambda m: '<strong>' + m.group(1) + '</strong>', esc(line))
        line = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', line)
        if line.startswith('### '):
            if in_list: out.append('</ul>'); in_list = False
            out.append('<h4>' + line[4:] + '</h4>')
        elif line.startswith('## '):
            if in_list: out.append('</ul>'); in_list = False
            out.append('<h3>' + line[3:] + '</h3>')
        elif line.startswith('- '):
            if not in_list: out.append('<ul>'); in_list = True
            out.append('<li>' + line[2:] + '</li>')
        elif not line:
            if in_list: out.append('</ul>'); in_list = False
        else:
            if in_list: out.append('</ul>'); in_list = False
            out.append('<p>' + line + '</p>')
    if in_list: out.append('</ul>')
    return '\n'.join(out)


def roadmap_sections(root, wanted=('Executive Summary', 'Current State', 'Strengths', 'Weaknesses', 'Competitor Gaps')):
    p = os.path.join(root, 'strategy-roadmap.md')
    if not os.path.isfile(p):
        return None
    text = io.open(p, encoding='utf-8').read()
    parts = re.split(r'^##\s+', text, flags=re.M)
    keep = []
    for part in parts[1:]:
        title = part.splitlines()[0].strip()
        if any(w.lower() in title.lower() for w in wanted):
            keep.append('## ' + part.strip())
    return md_to_html('\n\n'.join(keep)) if keep else None


# ---------------------------------------------------------------- delta ------
def compute_delta(new, old):
    def by_handle(d):
        return {c['handle']: c for c in d.get('creators', [])}
    n_h, o_h = by_handle(new), by_handle(old)
    old_urls = {o.get('url') for o in old.get('outliers', [])}
    new_outliers = [o for o in new.get('outliers', []) if o.get('url') not in old_urls]
    hook_moves = []
    old_hooks = {h['hook']: h for h in old.get('hook_taxonomy', [])}
    for h in new.get('hook_taxonomy', []):
        o = old_hooks.get(h['hook'])
        if o and (h['field_med_views'] != o['field_med_views'] or h['client_med_views'] != o['client_med_views']):
            hook_moves.append({'hook': h['hook'],
                               'field_med_views': [o['field_med_views'], h['field_med_views']],
                               'client_med_views': [o['client_med_views'], h['client_med_views']]})
    stat_moves = []
    for handle in sorted(set(n_h) & set(o_h)):
        n, o = n_h[handle], o_h[handle]
        moves = {}
        for k in ('med_views', 'reach_eff'):
            if n['stats'][k] != o['stats'][k]:
                moves[k] = [o['stats'][k], n['stats'][k]]
        if (n.get('cadence') or 0) != (o.get('cadence') or 0):
            moves['cadence'] = [o.get('cadence'), n.get('cadence')]
        if moves:
            stat_moves.append({'handle': handle, 'moves': moves})
    def rank(d):
        order = sorted(d.get('creators', []), key=lambda c: -c['stats']['reach_eff'])
        for i, c in enumerate(order):
            if c['handle'] == d['meta']['client_handle']:
                return i + 1
        return None
    return {'new_outliers': new_outliers,
            'hook_moves': hook_moves,
            'stat_moves': stat_moves,
            'client_rank': {'reach_eff': [rank(old), rank(new)], 'of': len(new.get('creators', []))},
            'roster_changes': {'added': sorted(set(n_h) - set(o_h)), 'removed': sorted(set(o_h) - set(n_h))}}


# ---------------------------------------------------------------- shell ------
CSS = """
.viz-root{
  --brand:@@BRAND@@; --accent:@@ACCENT@@;
  --surface-1:#fcfcfb; --page:#f9f9f7;
  --ink-1:#0b0b0b; --ink-2:#52514e; --ink-muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --ring:rgba(11,11,11,.10);
  --good:#006300;
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
  color:var(--ink-1); background:var(--page);
}
*{box-sizing:border-box} html,body{margin:0;padding:0;background:#f9f9f7}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 64px}
header.rpt{padding:18px 0 6px}
.rpt h1{font-size:26px;font-weight:650;margin:0 0 4px}
.rpt .sub{color:var(--ink-2);font-size:14px}
.stamp{display:inline-block;margin-top:10px;font-size:12px;color:var(--ink-muted);border:1px solid var(--grid);border-radius:999px;padding:3px 10px;background:var(--surface-1)}
.logo{font-size:12px;color:var(--ink-muted);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 8px}
.card{background:var(--surface-1);border:1px solid var(--ring);border-radius:10px;padding:14px 16px}
.card .k{font-size:12px;color:var(--ink-2);margin-bottom:6px}
.card .v{font-size:26px;font-weight:650;letter-spacing:-.01em}
.card .d{font-size:12px;color:var(--ink-muted);margin-top:4px}
.card .d.up{color:var(--good)}
section.panel{background:var(--surface-1);border:1px solid var(--ring);border-radius:12px;padding:18px 20px 14px;margin:18px 0}
.panel h2{font-size:16px;font-weight:650;margin:0 0 2px}
.panel .note{font-size:12.5px;color:var(--ink-2);margin:0 0 12px}
.chart-box{position:relative;width:100%}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:760px){.duo{grid-template-columns:1fr}}
details.twin{margin-top:10px;border-top:1px solid var(--grid);padding-top:8px}
details.twin summary{font-size:12px;color:var(--ink-muted);cursor:pointer;user-select:none}
table.tw{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
table.tw th{text-align:left;color:var(--ink-2);font-weight:600;border-bottom:1px solid var(--grid);padding:4px 8px}
table.tw td{border-bottom:1px solid var(--grid);padding:4px 8px;font-variant-numeric:tabular-nums}
.gap-card{border:1px solid var(--ring);border-left:4px solid var(--brand);border-radius:10px;padding:14px 16px;background:var(--surface-1);margin-bottom:10px}
.gap-card .h{font-weight:650;font-size:15px;margin-bottom:4px}
.gap-card .w{font-size:13px;color:var(--ink-2)}
.gap-card .o{display:inline-block;margin-top:8px;font-size:12px;color:var(--brand);font-weight:600}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.oc{background:var(--surface-1);border:1px solid var(--ring);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.oc .m{font-size:20px;font-weight:700;color:var(--brand)}
.oc .who{font-size:12.5px;color:var(--ink-2)}
.chip{display:inline-block;font-size:10.5px;font-weight:600;border-radius:999px;padding:1px 8px;margin-left:6px;color:#fff;background:var(--ink-muted)}
.chip.LARGE{background:#1baf7a}.chip.MED{background:#eda100}.chip.SMALL{background:#008300}.chip.CLIENT{background:var(--brand)}
.oc .hook{font-size:12.5px;color:var(--ink-1);line-height:1.35}
.oc .meta{font-size:11.5px;color:var(--ink-muted)}
.oc a{color:var(--brand);text-decoration:none;font-size:12px}
.written{font-size:14px;line-height:1.55}
.written h3{font-size:15px;margin:18px 0 6px}
.written h4{font-size:13.5px;margin:14px 0 4px;color:var(--ink-2)}
.written ul{margin:4px 0 10px 18px;padding:0}
.picker{margin:0 0 14px}
.picker select{font:inherit;padding:6px 10px;border:1px solid var(--grid);border-radius:8px;background:var(--surface-1);color:var(--ink-1)}
.wn li{margin:3px 0}
.rankstrip{font-size:13px;color:var(--ink-2);margin:6px 0 2px}
.rankstrip b{color:var(--brand)}
footer{color:var(--ink-muted);font-size:11.5px;margin-top:26px;text-align:center}
"""

JS_COMMON = """
const FMT = n => n==null?'-':(n>=1e6?(n/1e6).toFixed(1)+'M':n>=1000?Math.round(n/1000)+'k':String(Math.round(n)));
const PCT = n => n==null?'-':(n*100).toFixed(1)+'%';
const INK2='#52514e', MUTED='#c9c8c1', MUTEDINK='#898781', GRID='#e1e0d9', BASE='#c3c2b7';
const BRAND=getComputedStyle(document.querySelector('.viz-root')).getPropertyValue('--brand').trim();
const ACCENT=getComputedStyle(document.querySelector('.viz-root')).getPropertyValue('--accent').trim();
const TIERC={CLIENT:BRAND,LARGE:'#1baf7a',MED:'#eda100',SMALL:'#008300'};
Chart.defaults.font.family='system-ui,-apple-system,"Segoe UI",sans-serif';
Chart.defaults.font.size=11.5; Chart.defaults.color=MUTEDINK;
const BARX=(t)=>({grid:{color:GRID},border:{color:BASE},ticks:{callback:v=>FMT(v)},title:t?{display:true,text:t,color:MUTEDINK}:undefined});
const CATY={grid:{display:false},border:{display:false},ticks:{color:INK2}};
function hbar(el,labels,datasets,xTitle){return new Chart(el,{type:'bar',data:{labels,datasets},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:datasets.length>1?{position:'top',labels:{boxWidth:10,boxHeight:10,usePointStyle:true,pointStyle:'circle'}}:{display:false}},scales:{x:BARX(xTitle),y:CATY}}});}
function vbar(el,labels,data,colors,title,fmt){return new Chart(el,{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors,borderRadius:4,borderSkipped:'start',barPercentage:.6}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},title:title?{display:true,text:title,color:INK2,font:{weight:'600'}}:undefined,tooltip:{callbacks:{label:c=>' '+(fmt||FMT)(c.parsed.y)}}},scales:{y:{grid:{color:GRID},border:{color:BASE},ticks:{callback:v=>(fmt||FMT)(v)}},x:{grid:{display:false},border:{display:false}}}}});}
const DS=(label,data,color)=>({label,data,backgroundColor:color,borderRadius:4,borderSkipped:'start',barPercentage:.78});
"""


def page_shell(title, sub, stamp, body, chartjs, theme, page_js):
    logo = ('<div class="logo">' + esc(theme['logo_text']) + '</div>') if theme.get('logo_text') else ''
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>' + esc(title) + '</title>\n<style>'
            + CSS.replace('@@BRAND@@', theme['brand']).replace('@@ACCENT@@', theme['accent'])
            + '</style>\n</head>\n<body class="viz-root">\n<div class="wrap">\n'
            '<header class="rpt">' + logo + '<h1>' + esc(title) + '</h1>'
            '<div class="sub">' + sub + '</div>'
            + ('<span class="stamp">' + esc(stamp) + '</span>' if stamp else '')
            + '</header>\n' + body
            + '\n<footer>Generated by shortform-superengine · deterministic render from analysis-data.json · offline file — no network calls</footer>'
            '\n</div>\n<script>' + chartjs + '</script>\n<script>' + JS_COMMON + page_js + '</script>\n</body>\n</html>\n')


def twin_table(tid, headers, rows):
    body = '<tr>' + ''.join('<th>' + esc(h) + '</th>' for h in headers) + '</tr>'
    for r in rows:
        body += '<tr>' + ''.join('<td>' + esc(c) + '</td>' for c in r) + '</tr>'
    return ('<details class="twin"><summary>Table view</summary><table class="tw" id="' + tid + '">'
            + body + '</table></details>')


def fmt_n(n):
    if n is None: return '-'
    n = float(n)
    if n >= 1e6: return '%.1fM' % (n / 1e6)
    if n >= 1000: return '%dk' % round(n / 1000)
    return str(int(round(n)))


def pct(n):
    return '-' if n is None else '%.1f%%' % (n * 100)


# ---------------------------------------------------------------- pages ------
def render_overview(data, theme, chartjs, stamp, delta, history):
    m, cl = data['meta'], data['client']
    creators = data['creators']
    lad = sorted(creators, key=lambda c: -c['stats']['reach_eff'])
    gaps, outliers = data.get('gaps', []), data.get('outliers', [])[:12]
    tiers = {t['group']: t for t in data['rollups']['tiers']}
    top_views = max((c['stats']['med_views'] for c in creators), default=0)
    cad_field = sorted([c['cadence'] for c in creators if c.get('cadence') and c['tier'] != 'CLIENT'])
    cad_med = cad_field[len(cad_field) // 2] if cad_field else None

    cards = [
        ('Median views / reel', fmt_n(cl['stats']['med_views']), 'field top: ' + fmt_n(top_views)),
        ('Reach efficiency', pct(cl['stats']['reach_eff']), 'views ÷ followers'),
        ('Engagement rate', pct(cl['stats']['med_er']), 'median per reel'),
        ('Posting cadence', (('%.1f' % cl['cadence']) if cl.get('cadence') else '-') + '/wk',
         ('field median %.1f/wk' % cad_med) if cad_med else ''),
        ('Gaps found', str(len(gaps)), (gaps[0]['theme'] + ' leads') if gaps else 'none — full coverage'),
    ]
    body = '<div class="cards">' + ''.join(
        '<div class="card"><div class="k">%s</div><div class="v">%s</div><div class="d">%s</div></div>'
        % (esc(k), esc(v), esc(d)) for k, v, d in cards) + '</div>\n'

    if delta:
        wn = []
        for o in delta['new_outliers'][:5]:
            wn.append('New breakout: <b>%s×</b> @%s — “%s” (<a href="%s" target="_blank" rel="noopener">%s views</a>)'
                      % (esc(round(o['mult'])), esc(o['handle']), esc(o['hook_line'][:70]), esc(o['url']), esc(fmt_n(o['views']))))
        r0, r1 = delta['client_rank']['reach_eff']
        if r0 and r1 and r0 != r1:
            wn.append('Client reach-efficiency rank: <b>#%s → #%s</b> of %s' % (r0, r1, delta['client_rank']['of']))
        for s in delta['stat_moves'][:6]:
            mv = s['moves'].get('med_views')
            if mv:
                wn.append('@%s median views %s → %s' % (esc(s['handle']), esc(fmt_n(mv[0])), esc(fmt_n(mv[1]))))
        for rc, label in ((delta['roster_changes']['added'], 'joined the roster'),
                          (delta['roster_changes']['removed'], 'left the roster')):
            for h in rc:
                wn.append('@%s %s' % (esc(h), label))
        if not wn:
            wn.append('No metric movement vs the previous snapshot.')
        body += ('<section class="panel"><h2>This week</h2><p class="note">Changes vs the previous snapshot.</p>'
                 '<ul class="wn">' + ''.join('<li>' + w + '</li>' for w in wn) + '</ul></section>\n')

    body += ('<section class="panel"><h2>Reach efficiency ladder</h2>'
             '<p class="note">Median views ÷ followers — who over-performs their audience size. Client highlighted.</p>'
             '<div class="chart-box" style="height:' + str(120 + 20 * len(lad)) + 'px"><canvas id="ladder"></canvas></div>'
             + twin_table('ladT', ['Account', 'Tier', 'Reach eff', 'Med views', 'Followers'],
                          [['@' + c['handle'], c['tier'], pct(c['stats']['reach_eff']),
                            fmt_n(c['stats']['med_views']), fmt_n(c['followers'])] for c in lad])
             + '</section>\n')

    body += ('<section class="panel"><h2>Tier scoreboard</h2>'
             '<p class="note">Median views (audience size wins) vs reach efficiency (small accounts punch above weight).</p>'
             '<div class="duo"><div><div class="chart-box" style="height:240px"><canvas id="tv"></canvas></div></div>'
             '<div><div class="chart-box" style="height:240px"><canvas id="tr"></canvas></div></div></div>'
             + twin_table('tT', ['Tier', 'Accounts', 'Med views', 'Reach eff', 'ER'],
                          [[g, tiers[g]['creators'], fmt_n(tiers[g]['med_views']),
                            pct(tiers[g]['med_reach_eff']), pct(tiers[g]['med_er'])]
                           for g in TIER_ORDER if g in tiers])
             + '</section>\n')

    body += ('<section class="panel"><h2>Hook types — what wins vs what the client posts</h2>'
             '<p class="note">Median views per hook type, field vs client. The gap between bars is the playbook.</p>'
             '<div class="chart-box" style="height:' + str(90 + 34 * len(data['hook_taxonomy'])) + 'px"><canvas id="hooks"></canvas></div>'
             + twin_table('hT', ['Hook', 'Field reels', 'Field med views', 'Client reels', 'Client med views'],
                          [[h['hook'], h['field_n'], fmt_n(h['field_med_views']), h['client_n'],
                            fmt_n(h['client_med_views']) if h['client_n'] else '-'] for h in data['hook_taxonomy']])
             + '</section>\n')

    body += ('<section class="panel"><h2>Followers × median views</h2>'
             '<p class="note">Log-log map of the field. Above the cloud = over-performing. Client is the large ringed point.</p>'
             '<div class="chart-box" style="height:400px"><canvas id="scat"></canvas></div></section>\n')

    body += ('<section class="panel"><h2>Posting cadence</h2>'
             '<p class="note">Reels per week. More is not automatically better — pair with the reach ladder.</p>'
             '<div class="chart-box" style="height:' + str(120 + 18 * len(lad)) + 'px"><canvas id="cad"></canvas></div></section>\n')

    body += ('<section class="panel"><h2>Theme performance</h2>'
             '<p class="note">Where demand is proven (field median views) vs where the client actually posts.</p>'
             '<div class="chart-box" style="height:' + str(90 + 34 * len(data['theme_performance'])) + 'px"><canvas id="themes"></canvas></div>'
             + twin_table('thT', ['Theme', 'Field reels', 'Field med', 'Client reels', 'Client med'],
                          [[t['theme'], t['field_reels'], fmt_n(t['field_med_views']), t['client_reels'],
                            fmt_n(t['client_med_views']) if t['client_reels'] else '-'] for t in data['theme_performance']])
             + '</section>\n')

    body += ('<section class="panel"><h2>Opportunity map</h2>'
             '<p class="note">x = what the theme earns in the field · y = client coverage vs field coverage '
             '(below 1.0 = underweight) · bubble = field volume. Bottom-right = the money.</p>'
             '<div class="chart-box" style="height:380px"><canvas id="oppo"></canvas></div></section>\n')

    if gaps:
        body += '<section class="panel"><h2>Content gaps</h2><p class="note">Themes the field proves and the client under-serves.</p>'
        for g in gaps:
            body += ('<div class="gap-card"><div class="h">%s</div><div class="w">%s</div>'
                     '<span class="o">Opportunity score %s · %s field reels at %s median views</span></div>'
                     % (esc(g.get('headline', g['theme'])), esc(g.get('why', '')),
                        esc(g.get('oppo', '-')), esc(g['field_reels']), esc(fmt_n(g['field_med_views']))))
        body += '</section>\n'

    body += ('<section class="panel"><h2>Outlier wall — the field\'s breakout reels</h2>'
             '<p class="note">Multiples of each creator\'s own median. These are the reels worth deep-reading.</p>'
             '<div class="wall">' + ''.join(
                 '<div class="oc"><div class="m">%s×</div><div class="who">@%s<span class="chip %s">%s</span></div>'
                 '<div class="hook">“%s”</div><div class="meta">%s views · %s hook</div>'
                 '<a href="%s" target="_blank" rel="noopener">watch reel →</a></div>'
                 % (esc(int(round(o['mult']))), esc(o['handle']), esc(o['tier']), esc(o['tier']),
                    esc(o['hook_line'][:90]), esc(fmt_n(o['views'])), esc(o['hook']), esc(o['url']))
                 for o in outliers) + '</div></section>\n')

    if history and len(history) >= 2:
        body += ('<section class="panel"><h2>Client trend</h2>'
                 '<p class="note">Across weekly snapshots (' + esc(history[0][0]) + ' → ' + esc(history[-1][0]) + ').</p>'
                 '<div class="duo"><div><div class="chart-box" style="height:220px"><canvas id="tr1"></canvas></div></div>'
                 '<div><div class="chart-box" style="height:220px"><canvas id="tr2"></canvas></div></div></div></section>\n')

    payload = {
        'lad': [{'h': c['handle'], 't': c['tier'], 're': round(c['stats']['reach_eff'] * 100, 2),
                 'mv': c['stats']['med_views'], 'f': c['followers'], 'cad': c.get('cadence')} for c in lad],
        'tiers': [{'g': g, 'mv': tiers[g]['med_views'], 're': round(tiers[g]['med_reach_eff'] * 100, 2)}
                  for g in TIER_ORDER if g in tiers],
        'hooks': [{'k': h['hook'], 'fv': h['field_med_views'], 'cv': h['client_med_views'],
                   'fn': h['field_n'], 'cn': h['client_n']} for h in data['hook_taxonomy']],
        'themes': [{'k': t['theme'], 'fv': t['field_med_views'], 'cv': t['client_med_views'],
                    'fr': t['field_reels'], 'cr': t['client_reels']} for t in data['theme_performance']],
        'client': m['client_handle'],
        'totals': {'client_reels': sum(t['client_reels'] for t in data['theme_performance']) or 1,
                   'field_reels': sum(t['field_reels'] for t in data['theme_performance']) or 1},
        'gapthemes': {g['theme']: g['reason'] for g in gaps},
        'trend': [{'d': d, 'mv': s['client']['stats']['med_views'],
                   're': round(s['client']['stats']['reach_eff'] * 100, 2)} for d, s in (history or [])],
    }
    page_js = 'const D=' + js_data(payload) + ';\n' + """
hbar(document.getElementById('ladder'), D.lad.map(c=>'@'+c.h),
 [{data:D.lad.map(c=>c.re),backgroundColor:D.lad.map(c=>c.t==='CLIENT'?BRAND:MUTED),borderRadius:4,borderSkipped:'start',barPercentage:.72}],
 'median views ÷ followers (%)');
vbar(document.getElementById('tv'), D.tiers.map(t=>t.g), D.tiers.map(t=>t.mv), D.tiers.map(t=>t.g==='CLIENT'?BRAND:MUTED), 'Median views by tier');
vbar(document.getElementById('tr'), D.tiers.map(t=>t.g), D.tiers.map(t=>t.re), D.tiers.map(t=>t.g==='CLIENT'?BRAND:MUTED), 'Median reach efficiency by tier', v=>v+'%');
hbar(document.getElementById('hooks'), D.hooks.map(h=>h.k),
 [DS('Field median views',D.hooks.map(h=>h.fv),ACCENT), DS('Client median views',D.hooks.map(h=>h.cv),BRAND)]);
new Chart(document.getElementById('scat'),{type:'scatter',
 data:{datasets:['CLIENT','LARGE','MED','SMALL'].map(t=>({label:t,
  data:D.lad.filter(c=>c.t===t).map(c=>({x:c.f,y:c.mv,h:c.h,re:c.re})),
  backgroundColor:TIERC[t],pointRadius:t==='CLIENT'?9:6,pointHoverRadius:t==='CLIENT'?11:9,
  pointBorderColor:'#fcfcfb',pointBorderWidth:2}))},
 options:{responsive:true,maintainAspectRatio:false,
  plugins:{legend:{position:'top',labels:{boxWidth:10,boxHeight:10,usePointStyle:true,pointStyle:'circle'}},
   tooltip:{callbacks:{label:c=>' @'+c.raw.h+' · '+FMT(c.raw.x)+' followers · '+FMT(c.raw.y)+' med views · '+c.raw.re+'% reach'}}},
  scales:{x:{type:'logarithmic',title:{display:true,text:'followers (log)',color:MUTEDINK},grid:{color:GRID},border:{color:BASE}},
          y:{type:'logarithmic',title:{display:true,text:'median views (log)',color:MUTEDINK},grid:{color:GRID},border:{color:BASE}}}}});
const cadRows=D.lad.filter(c=>c.cad!=null).sort((a,b)=>b.cad-a.cad);
hbar(document.getElementById('cad'), cadRows.map(c=>'@'+c.h),
 [{data:cadRows.map(c=>c.cad),backgroundColor:cadRows.map(c=>c.t==='CLIENT'?BRAND:MUTED),borderRadius:4,borderSkipped:'start',barPercentage:.72}],
 'reels per week');
hbar(document.getElementById('themes'), D.themes.map(t=>t.k),
 [DS('Field median views',D.themes.map(t=>t.fv),ACCENT), DS('Client median views',D.themes.map(t=>t.cv),BRAND)]);
new Chart(document.getElementById('oppo'),{type:'bubble',
 data:{datasets:[{label:'themes',
  data:D.themes.map(t=>({x:t.fv, y:+(((t.cr/D.totals.client_reels)/(t.fr/D.totals.field_reels))||0).toFixed(2),
   r:Math.max(6,Math.sqrt(t.fr)), k:t.k, fr:t.fr, cr:t.cr})),
  backgroundColor:D.themes.map(t=>D.gapthemes[t.k]==='absent'?BRAND:D.gapthemes[t.k]==='underweight'?ACCENT:MUTED)}]},
 options:{responsive:true,maintainAspectRatio:false,
  plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>' '+c.raw.k+' · field '+FMT(c.raw.x)+' med views · coverage ratio '+c.raw.y+' · '+c.raw.fr+' field / '+c.raw.cr+' client reels'}}},
  scales:{x:{title:{display:true,text:'field median views',color:MUTEDINK},grid:{color:GRID},border:{color:BASE},ticks:{callback:v=>FMT(v)}},
          y:{title:{display:true,text:'client÷field coverage ratio',color:MUTEDINK},grid:{color:GRID},border:{color:BASE}}}}});
if (D.trend.length>=2){
 const mk=(el,key,label)=>new Chart(document.getElementById(el),{type:'line',
  data:{labels:D.trend.map(t=>t.d),datasets:[{label,data:D.trend.map(t=>t[key]),borderColor:BRAND,backgroundColor:BRAND,borderWidth:2,pointRadius:4,pointBorderColor:'#fcfcfb',pointBorderWidth:2,tension:0}]},
  options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},title:{display:true,text:label,color:INK2,font:{weight:'600'}}},
   scales:{y:{grid:{color:GRID},border:{color:BASE}},x:{grid:{display:false},border:{color:BASE}}}}});
 mk('tr1','mv','Client median views'); mk('tr2','re','Client reach efficiency (%)');
}
"""
    sub = ('%s accounts · %s reels analyzed · client vs LARGE / MED / SMALL tiers'
           % (len(creators), fmt_n(m['total_reels'])))
    return page_shell('@' + m['client_handle'] + ' — Competitor Field Report', sub, stamp, body, chartjs, theme, page_js)


def competitor_payload(data):
    m = data['meta']
    tiers = {t['group']: t for t in data['rollups']['tiers']}
    comps = [c for c in data['creators'] if c['handle'] != m['client_handle']]
    return [{'h': c['handle'], 't': c['tier'], 'lane': c.get('lane'), 'f': c['followers'],
             'cad': c.get('cadence'), 'n': c['stats']['n'], 'mv': c['stats']['med_views'],
             're': round(c['stats']['reach_eff'] * 100, 2), 'er': round(c['stats']['med_er'] * 100, 2),
             'hm': c.get('hook_mix'),
             'tmv': tiers.get(c['tier'], {}).get('med_views'),
             'tre': round(tiers.get(c['tier'], {}).get('med_reach_eff', 0) * 100, 2),
             'outs': [{'m': int(round(o['mult'])), 'v': o['views'], 'line': o['hook_line'][:90],
                       'hk': o['hook'], 'u': o['url']}
                      for o in data.get('outliers', []) if o['handle'] == c['handle']][:4]}
            for c in comps]


COMP_JS = """
const sel=document.getElementById('pick');
CD.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent='@'+c.h+' ('+c.t+')';sel.appendChild(o)});
let charts=[];
function show(i){
 const c=CD[i]; charts.forEach(ch=>ch.destroy()); charts=[];
 document.getElementById('stats').innerHTML=
  '<div class="card"><div class="k">Followers</div><div class="v">'+FMT(c.f)+'</div></div>'+
  '<div class="card"><div class="k">Median views</div><div class="v">'+FMT(c.mv)+'</div><div class="d">tier median '+FMT(c.tmv)+'</div></div>'+
  '<div class="card"><div class="k">Reach efficiency</div><div class="v">'+c.re+'%</div><div class="d">tier median '+c.tre+'%</div></div>'+
  '<div class="card"><div class="k">Engagement</div><div class="v">'+c.er+'%</div></div>'+
  '<div class="card"><div class="k">Cadence</div><div class="v">'+(c.cad==null?'-':c.cad.toFixed(1))+'<span style="font-size:14px;font-weight:500">/wk</span></div></div>';
 charts.push(vbar(document.getElementById('vsT1'),['@'+c.h,c.t+' tier median'],[c.mv,c.tmv],[BRAND,MUTED],'Median views vs their tier'));
 charts.push(vbar(document.getElementById('vsT2'),['@'+c.h,c.t+' tier median'],[c.re,c.tre],[BRAND,MUTED],'Reach efficiency vs their tier',v=>v+'%'));
 const hmBox=document.getElementById('hmBox');
 if(c.hm){hmBox.innerHTML='<div class="chart-box" style="height:'+(70+30*Object.keys(c.hm).length)+'px"><canvas id="hm"></canvas></div>';
  const ks=Object.keys(c.hm).sort((a,b)=>c.hm[b]-c.hm[a]);
  charts.push(hbar(document.getElementById('hm'),ks,[{data:ks.map(k=>c.hm[k]),backgroundColor:BRAND,borderRadius:4,borderSkipped:'start',barPercentage:.7}],'reels using this hook'));
 } else hmBox.innerHTML='<p class="note">Hook mix needs schema 1.1 — re-run analyze.py to unlock.</p>';
 document.getElementById('outs').innerHTML=c.outs.length?c.outs.map(o=>
  '<div class="oc"><div class="m">'+o.m+'×</div><div class="hook">“'+o.line.replace(/</g,'&lt;')+'”</div><div class="meta">'+FMT(o.v)+' views · '+o.hk+' hook</div><a href="'+o.u+'" target="_blank" rel="noopener">watch reel →</a></div>').join('')
  :'<p class="note">No ≥2.5× breakouts in the field top-30 this window — steady performer, no spikes.</p>';
}
sel.addEventListener('change',e=>show(+e.target.value)); show(0);
"""


def render_competitors(data, theme, chartjs, stamp):
    m = data['meta']
    payload = competitor_payload(data)
    body = ('<section class="panel"><div class="picker"><label for="pick" style="font-size:13px;color:var(--ink-2)">Competitor: </label>'
            '<select id="pick"></select></div>'
            '<div class="cards" id="stats"></div>'
            '<div class="duo"><div><div class="chart-box" style="height:220px"><canvas id="vsT1"></canvas></div></div>'
            '<div><div class="chart-box" style="height:220px"><canvas id="vsT2"></canvas></div></div></div>'
            '<h2 style="margin-top:16px">Hook mix</h2><div id="hmBox"></div>'
            '<h2 style="margin-top:16px">Breakout reels</h2><div class="wall" id="outs"></div></section>')
    page_js = 'const CD=' + js_data(payload) + ';\n' + COMP_JS
    return page_shell('Competitor profiles — @' + m['client_handle'] + ' field',
                      str(len(payload)) + ' competitors · pick one to inspect', stamp, body, chartjs, theme, page_js)


def render_competitor_single(data, comp, theme, chartjs, stamp):
    body = ('<section class="panel"><div class="cards" id="stats"></div>'
            '<div class="duo"><div><div class="chart-box" style="height:220px"><canvas id="vsT1"></canvas></div></div>'
            '<div><div class="chart-box" style="height:220px"><canvas id="vsT2"></canvas></div></div></div>'
            '<h2 style="margin-top:16px">Hook mix</h2><div id="hmBox"></div>'
            '<h2 style="margin-top:16px">Breakout reels</h2><div class="wall" id="outs"></div></section>')
    page_js = ('const CD=' + js_data([comp]) + ';\n'
               'const sel={appendChild:()=>{},addEventListener:()=>{}};\n'
               + COMP_JS.replace("const sel=document.getElementById('pick');", '')
                        .replace("sel.addEventListener('change',e=>show(+e.target.value)); show(0);", 'show(0);')
                        .replace("CD.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent='@'+c.h+' ('+c.t+')';sel.appendChild(o)});", ''))
    return page_shell('@' + comp['h'] + ' — competitor profile',
                      comp['t'] + ' tier · ' + fmt_n(comp['f']) + ' followers', stamp, body, chartjs, theme, page_js)


def render_client(data, theme, chartjs, stamp, written_html):
    m, cl = data['meta'], data['client']
    lad = sorted(data['creators'], key=lambda c: -c['stats']['reach_eff'])
    rank = next((i + 1 for i, c in enumerate(lad) if c['handle'] == m['client_handle']), None)
    outs = [o for o in data.get('outliers', []) if o['handle'] == m['client_handle']][:6]
    gaps = {g['theme']: g for g in data.get('gaps', [])}

    body = ('<div class="rankstrip">Reach-efficiency rank: <b>#%s of %s</b> · tier %s</div>' % (rank, len(lad), esc(cl['tier'])))
    body += '<div class="cards">' + ''.join(
        '<div class="card"><div class="k">%s</div><div class="v">%s</div></div>' % (esc(k), esc(v))
        for k, v in [('Median views', fmt_n(cl['stats']['med_views'])),
                     ('Reach efficiency', pct(cl['stats']['reach_eff'])),
                     ('Engagement rate', pct(cl['stats']['med_er'])),
                     ('Cadence', (('%.1f' % cl['cadence']) if cl.get('cadence') else '-') + '/wk'),
                     ('Reels analyzed', cl['stats']['n'])]) + '</div>\n'

    body += ('<section class="panel"><h2>What you post vs what wins</h2>'
             '<p class="note">Left: your hook mix (reel counts). Right: what each hook earns in the field (median views). '
             'Two different units — read the shapes, not the heights.</p>'
             '<div class="duo"><div><div class="chart-box" style="height:300px"><canvas id="mix"></canvas></div></div>'
             '<div><div class="chart-box" style="height:300px"><canvas id="wins"></canvas></div></div></div></section>\n')

    body += ('<section class="panel"><h2>Theme coverage</h2>'
             '<p class="note">Your reels per theme vs the field, with gap flags.</p>'
             '<div class="chart-box" style="height:' + str(90 + 34 * len(data['theme_performance'])) + 'px"><canvas id="cov"></canvas></div>'
             + twin_table('covT', ['Theme', 'Client reels', 'Field reels', 'Flag'],
                          [[t['theme'], t['client_reels'], t['field_reels'],
                            gaps.get(t['theme'], {}).get('reason', '')] for t in data['theme_performance']])
             + '</section>\n')

    if outs:
        body += ('<section class="panel"><h2>Your breakout reels</h2><div class="wall">' + ''.join(
            '<div class="oc"><div class="m">%s×</div><div class="hook">“%s”</div>'
            '<div class="meta">%s views · %s hook</div><a href="%s" target="_blank" rel="noopener">watch reel →</a></div>'
            % (esc(int(round(o['mult']))), esc(o['hook_line'][:90]), esc(fmt_n(o['views'])), esc(o['hook']), esc(o['url']))
            for o in outs) + '</div></section>\n')
    else:
        body += ('<section class="panel"><h2>Your breakout reels</h2>'
                 '<p class="note">None ≥2.5× your median in this window — the roadmap\'s hook + theme moves are how we change that.</p></section>\n')

    if written_html:
        body += '<section class="panel"><h2>Written analysis</h2><div class="written">' + written_html + '</div></section>\n'
    else:
        body += '<section class="panel"><h2>Written analysis</h2><p class="note">strategy-roadmap.md not found in this project — run the cross-reference roadmap step to generate it.</p></section>\n'

    payload = {'hm': cl.get('hook_mix'),
               'hooks': [{'k': h['hook'], 'fv': h['field_med_views']} for h in data['hook_taxonomy']],
               'themes': [{'k': t['theme'], 'cr': t['client_reels'], 'fr': t['field_reels'],
                           'flag': gaps.get(t['theme'], {}).get('reason')} for t in data['theme_performance']]}
    page_js = 'const D=' + js_data(payload) + ';\n' + """
if (D.hm){const ks=Object.keys(D.hm).sort((a,b)=>D.hm[b]-D.hm[a]);
 hbar(document.getElementById('mix'),ks,[{data:ks.map(k=>D.hm[k]),backgroundColor:BRAND,borderRadius:4,borderSkipped:'start',barPercentage:.7}],'your reels using this hook');
}else{document.getElementById('mix').parentElement.innerHTML='<p class="note">Hook mix needs schema 1.1 — re-run analyze.py to unlock.</p>';}
hbar(document.getElementById('wins'),D.hooks.map(h=>h.k),
 [{data:D.hooks.map(h=>h.fv),backgroundColor:ACCENT,borderRadius:4,borderSkipped:'start',barPercentage:.7}],'field median views per hook');
hbar(document.getElementById('cov'),D.themes.map(t=>t.k),
 [DS('Client reels',D.themes.map(t=>t.cr),BRAND), DS('Field reels',D.themes.map(t=>t.fr),ACCENT)]);
"""
    return page_shell('@' + m['client_handle'] + ' — profile & written analysis',
                      'Your numbers, your mix, and the written roadmap in one page', stamp, body, chartjs, theme, page_js)


# ---------------------------------------------------------------- main -------
def load_history(root):
    hdir = os.path.join(root, 'history')
    if not os.path.isdir(hdir):
        return []
    snaps = []
    for f in sorted(os.listdir(hdir)):
        mt = re.match(r'analysis-data-(\d{4}-\d{2}-\d{2})\.json$', f)
        if mt:
            try:
                snaps.append((mt.group(1), json.load(io.open(os.path.join(hdir, f), encoding='utf-8'))))
            except (json.JSONDecodeError, OSError):
                pass
    return snaps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--prev')
    ap.add_argument('--stamp', default='')
    ap.add_argument('--out')
    ap.add_argument('--split', action='store_true')
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    data = load_analysis_json(root)
    if data is None:
        print('ERROR: no analysis-data.json in ' + root + ' - run competitor-cross-reference first.')
        sys.exit(1)
    check_version(data)
    theme = load_theme(root)
    chartjs = load_chartjs()
    out = args.out or os.path.join(root, 'visuals')
    os.makedirs(out, exist_ok=True)

    delta = None
    if args.prev:
        try:
            old = json.load(io.open(args.prev, encoding='utf-8'))
            delta = compute_delta(data, old)
            io.open(os.path.join(out, 'whats-new.json'), 'w', encoding='utf-8').write(
                json.dumps(delta, indent=2, ensure_ascii=False))
        except (json.JSONDecodeError, OSError) as e:
            print('WARN: --prev unreadable (%s) - skipping delta' % e)

    history = load_history(root)
    written = roadmap_sections(root)

    pages = {'overview.html': render_overview(data, theme, chartjs, args.stamp, delta, history),
             'competitors.html': render_competitors(data, theme, chartjs, args.stamp),
             'client.html': render_client(data, theme, chartjs, args.stamp, written)}
    for name, htm in pages.items():
        io.open(os.path.join(out, name), 'w', encoding='utf-8').write(htm)

    n_split = 0
    if args.split:
        sdir = os.path.join(out, 'competitors')
        os.makedirs(sdir, exist_ok=True)
        for comp in competitor_payload(data):
            fn = re.sub(r'[^A-Za-z0-9._-]', '_', comp['h']) + '.html'
            io.open(os.path.join(sdir, fn), 'w', encoding='utf-8').write(
                render_competitor_single(data, comp, theme, chartjs, args.stamp))
            n_split += 1

    print('visual pack -> ' + out)
    print('  overview.html competitors.html client.html'
          + (' whats-new.json' if delta else '')
          + ((' + %d split profiles' % n_split) if n_split else ''))


if __name__ == '__main__':
    main()
