# Reel-scripter: first format engine. Turns a finished competitor-cross-reference
# analysis (analysis-data.json) -- plus optional spoken transcripts -- into a
# scripting-brief.md the creator can shoot from.
# Usage: python scripting_brief.py <project_dir>
# Writes <project_dir>/scripting-brief.md + prints an ASCII-only console summary.
#
# DETERMINISTIC by contract: no dates, no randomness, every sort has a stable
# secondary key -> byte-identical across runs (a regression fixture git-diffs it).
# WINDOWS: every open() is utf-8; non-ASCII NEVER hits stdout (cp1252 console).
import os, re, sys, glob, json, statistics as st
from collections import defaultdict, Counter

# shared core<->format helpers (load_analysis_json / parse_transcript_header / fix / med)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_shared', 'lib'))
import reel_io

if len(sys.argv) < 2:
    print('Usage: python scripting_brief.py <project_dir>')
    sys.exit(1)
ROOT = sys.argv[1]

# ----------------------------------------------------------------------------
# spoken-hook taxonomy (mirrors the analyze_scripts.py prototype's classifier --
# kept LOCAL, not imported, so the byte-locked analysis gate can never be touched).
# Runs on the SPOKEN first sentence, which is a different signal from caption hooks.
# ----------------------------------------------------------------------------
STOP = set('the a an and or but to of in on for with my you your i we is are was it that this these those at as be have has had do does so just me our their them they he she his her if then than not no yes can will would could about out up down here there what when how why who all'.split())

def first_sentence(t):
    t = t.strip()
    if not t:
        return ''
    return re.split(r'(?<=[.!?])\s+', t)[0][:140]

def hook_type(l):
    l = l.strip().lower()
    if not l:
        return 'none'
    if l.endswith('?') or re.match(r'^(why|what|how|is|are|can|do|does|could|should|when|which|who|did you|have you|ever)', l):
        return 'question'
    if re.match(r'^(here are|here\'s|\d|one|two|three|number one|first|the \d)', l) or re.search(r'\b(ways|tips|signs|reasons|things|steps|mistakes|foods|rules)\b', l):
        return 'numbered/list'
    if re.search(r'\b(myth|stop|don.?t|never|nobody|no one|the truth|lie|isn.?t|not just|wrong|mistake|forget|quit)\b', l):
        return 'myth-bust/negation'
    if re.search(r'\b(actually|unpopular|everyone|they don.?t want|real reason|secret|nobody talks|hill i|truth is)\b', l):
        return 'contrarian/curiosity'
    if re.search(r'(if you|you.?ve been|tired of|exhausted|struggling|still|feel like|when you|ladies over|women over|are you)\b', l):
        return 'pain-callout'
    if re.match(r'^(i |my |when i |i.?m |i.?ve |four years|let me tell|i was|i used)', l):
        return 'personal/story'
    return 'statement'

def opening_gram(text, k=4):
    return ' '.join(re.findall(r"[a-z']+", text.lower())[:k])

def content_words(text, n=8):
    return [w for w in re.findall(r"[a-z']+", text.lower())[:n] if w not in STOP and len(w) > 2]

# stable ordered most_common: sort by (-count, key) so ties never depend on dict order
def ranked(counter):
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))

# ----------------------------------------------------------------------------
# load the core interface (REQUIRED) + transcripts (OPTIONAL -> FULL mode)
# ----------------------------------------------------------------------------
data = reel_io.load_analysis_json(ROOT)
meta = data['meta']
client = data['client']
HANDLE = meta.get('client_handle') or client['handle']

TDIR = os.path.join(ROOT, 'transcripts')
tfiles = sorted(glob.glob(os.path.join(TDIR, '*', '*.txt')))  # sorted = deterministic walk
FULL = len(tfiles) > 0
CLIENT_DIR = 'reels-full'  # the client's own transcripts live here

def parse_reel(path):
    """Header dict from reel_io + the two fields it doesn't surface: rank group + NO-VOICEOVER."""
    txt = open(path, encoding='utf-8').read()
    h = reel_io.parse_transcript_header(txt)
    head = txt.split('## ', 1)[0]  # header portion only
    novo = 'NO VOICEOVER' in head
    rk = (h.get('rank') or '').lower()
    grp = 'best' if 'best' in rk else ('worst' if 'worst' in rk else None)
    creator = os.path.basename(os.path.dirname(path))
    spoken = '' if novo else (h.get('transcript') or '')
    return dict(creator=creator, group=grp, views=h.get('views') or 0, novo=novo,
                text=spoken, caption_hook=h.get('caption_hook') or '', url=h.get('url') or '')

rows = [parse_reel(f) for f in tfiles]
field_rows = [r for r in rows if r['creator'] != CLIENT_DIR]
client_rows = [r for r in rows if r['creator'] == CLIENT_DIR]

# ----------------------------------------------------------------------------
# CAPTION-ONLY fallback source: durations + the client's own caption first-lines
# ----------------------------------------------------------------------------
def load_source_reels():
    p = os.path.join(ROOT, 'source', 'reels-full.json')
    if not os.path.exists(p):
        return []
    d = reel_io.J(p)
    items = d.get('items') or d.get('data', {}).get('items', []) or []
    out = []
    for it in items:
        post = it.get('post', {}); eng = post.get('engagement', {}); con = post.get('content', {})
        out.append(dict(views=eng.get('views') or 0,
                        cap=reel_io.fix(con.get('text', '') or ''),
                        dur=con.get('duration_seconds'), url=post.get('url')))
    return out

src_reels = load_source_reels()

# ============================================================================
# BUILD scripting-brief.md  (unicode is fine here -- file is utf-8)
# ============================================================================
out = []
def w(s=''):
    out.append(s)

def fnum(x):
    return f'{x:,.0f}'

n_field_creators = meta.get('n_competitors', max(0, len(data['creators']) - 1))
mode_label = ('FULL (spoken transcripts present)' if FULL
              else 'CAPTION-ONLY (no transcripts -- spoken sections degraded)')

# jx = capture bag for the structured JSON twin. We stash the SAME variables the .md
# renders (never recompute) as each section produces them, then assemble + dump after
# the .md is written. Keeps the .json numbers byte-aligned to the .md by construction.
jx = {}

w(f'# @{HANDLE} -- Reel Scripting Brief')
w('')
if FULL:
    w(f'**Mode:** {mode_label}  ·  **Inputs:** analysis-data.json + {len(rows)} spoken transcripts '
      f'({len(field_rows)} competitor + {len(client_rows)} client).')
else:
    w(f'**Mode:** {mode_label}  ·  **Inputs:** analysis-data.json only '
      f'({meta.get("total_reels", 0)} reels analyzed, {n_field_creators} competitors).')
w(f'**Field:** {meta.get("total_reels", 0)} reels across {n_field_creators} competitors. '
  f'Client baseline: {fnum(client["stats"]["med_views"])} median views, '
  f'reach-eff {client["stats"]["reach_eff"]*100:.1f}%.')
w('')
w('> How to use: Sections 1-3 tell you WHAT to make (themes + hook types that overperform). '
  'Sections 4-6 tell you HOW to open, structure, and time it. Section 7 is the gap between '
  'what you do now and those winning moves. Pick a Section-1 theme, a Section-2 hook, an '
  'opener from Section 4 -> that is one reel.')
if not FULL:
    w('')
    w('> NOTE: No `transcripts/` folder found, so this brief is CAPTION-ONLY. Hook/theme/gap '
      'analysis (Sections 1-3) is fully intact (it reads the analysis JSON). The spoken-craft '
      'sections (4-6) fall back to caption + hook-line mining and are weaker -- harvest reel '
      'transcripts to upgrade them.')

# ---------------------------------------------------------------------------
# 1. ATTACK THEMES (ranked gaps)
# ---------------------------------------------------------------------------
w('')
w('## 1. Attack themes (where the field wins and you are thin)')
gaps = data.get('gaps', [])
themeperf = data.get('theme_performance', [])
if gaps:
    # absent first, then underweight; within each, highest field median views first
    order = {'absent': 0, 'underweight': 1}
    gaps_sorted = sorted(gaps, key=lambda g: (order.get(g['reason'], 2), -g['field_med_views'], g['theme']))
    jx['attack_themes'] = [
        {'theme': g['theme'], 'reason': g['reason'],
         'field_med_views': g['field_med_views'], 'field_reels': g['field_reels'],
         'client_reels': g['client_reels'], 'client_med_views': g.get('client_med_views', 0)}
        for g in gaps_sorted]
    w('')
    w('Themes the field gets paid on that you under-serve. Make these first.')
    w('')
    w('| Theme | Gap | Field med views | Field reels | Your reels | Why it matters |')
    w('|---|---|--:|--:|--:|---|')
    for g in gaps_sorted:
        if g['reason'] == 'absent':
            why = 'The field proves demand and you have posted ZERO. Pure whitespace -- claim it.'
        else:
            why = 'The field leans in far harder than you do; you are leaving reach on the table.'
        w(f"| {g['theme']} | {g['reason']} | {fnum(g['field_med_views'])} | {g['field_reels']} | "
          f"{g['client_reels']} | {why} |")
else:
    w('')
    w('No structural theme gaps flagged -- you already cover the themes the field rewards '
      '(nothing absent, nothing badly underweight). So the play is not NEW themes, it is making '
      'your STRONGEST existing themes hit harder. Highest field-value themes you already touch:')
    w('')
    w('| Theme | Field med views | Field reels | Your reels | Your med views |')
    w('|---|--:|--:|--:|--:|')
    covered = [t for t in themeperf if t.get('client_reels', 0) > 0]
    covered.sort(key=lambda t: (-t['field_med_views'], t['theme']))
    jx['attack_themes'] = [
        {'theme': t['theme'], 'reason': 'covered',
         'field_med_views': t['field_med_views'], 'field_reels': t['field_reels'],
         'client_reels': t['client_reels'], 'client_med_views': t.get('client_med_views', 0)}
        for t in covered[:6]]
    for t in covered[:6]:
        w(f"| {t['theme']} | {fnum(t['field_med_views'])} | {t['field_reels']} | "
          f"{t['client_reels']} | {fnum(t.get('client_med_views', 0))} |")
    w('')
    w('Read the gap between Field med and Your med: that multiple is your headroom on a theme '
      'you already understand. Lift the hook + opener (Sections 2 & 4), not the topic.')

# ---------------------------------------------------------------------------
# 2. WINNING HOOK TYPES  (with 4 Hook Killers framing)
# ---------------------------------------------------------------------------
w('')
w('## 2. Winning hook types (and the ones you are sleeping on)')
hooks = [h for h in data.get('hook_taxonomy', []) if h['hook'] != 'none']
# rank by field median views desc, stable by hook name
hooks_sorted = sorted(hooks, key=lambda h: (-h['field_med_views'], h['hook']))
field_med_overall = reel_io.med([h['field_med_views'] for h in hooks_sorted]) if hooks_sorted else 0
w('')
w('Hook = the FIRST move (caption line 1 / spoken first sentence). Ranked by field median views.')
w('')
w('| Hook type | Field med views | Field n | Your n | Your med views | Read |')
w('|---|--:|--:|--:|--:|---|')
underused = []  # winners the client barely uses
jx['winning_hooks'] = []
for h in hooks_sorted:
    above = h['field_med_views'] >= field_med_overall
    thin = h['client_n'] <= 2
    if above and thin:
        read = 'WINNER you under-use -- lean in'
        read_key = 'under-use'
        underused.append(h)
    elif above:
        read = 'Strong field hook; you use it'
        read_key = 'use-it'
    else:
        read = 'Below-median; deprioritize'
        read_key = 'deprioritize'
    jx['winning_hooks'].append(
        {'hook': h['hook'], 'field_med_views': h['field_med_views'], 'field_n': h['field_n'],
         'client_n': h['client_n'], 'client_med_views': h['client_med_views'], 'read': read_key})
    w(f"| {h['hook']} | {fnum(h['field_med_views'])} | {h['field_n']} | {h['client_n']} | "
      f"{fnum(h['client_med_views'])} | {read} |")
w('')
if underused:
    w('**Biggest hook openings for you (high field reach, low usage):**')
    for h in sorted(underused, key=lambda h: (-h['field_med_views'], h['hook']))[:4]:
        w(f"- **{h['hook']}** -- field median {fnum(h['field_med_views'])} views across "
          f"{h['field_n']} reels, but you have only {h['client_n']}. Add this to your rotation.")
else:
    w('You already touch every above-median hook type at least a few times -- the lift is '
      'execution quality, not adding a new hook category.')
w('')
w('**Diagnose every weak hook with the 4 Hook Killers** (root cause -> fix):')
w('- **DELAY** -- topic arrives too late. Fix: delete everything before the subject; lead with the first interesting noun.')
w('- **CONFUSION** -- needs a re-read. Fix: fewer/simpler words, active voice, one idea per line.')
w('- **IRRELEVANCE** -- viewer does not feel it is for them (usually "I"-framing). Fix: swap me/my -> you/your; name their pain.')
w('- **DISINTEREST** -- clear but flat, no open question. Fix: state an A-vs-B contrast ("Most people X. Here is why that is wrong.").')
w('- **Retention = curiosity sustained.** The #1 killer is closing the curiosity loop too early -- paying off the question before the viewer is invested. Keep at least one open loop running at all times; only resolve it once the next loop is already open.')
w('- **Re-hook every ~20-30 seconds.** Attention decays even after a great open, so plant a fresh micro-open on a cadence -- a new question, a "but here is the thing", a pattern interrupt -- so the curve never flattens.')
w('')
w('On a Reel the attention cliff is ~2 seconds (spoken + visual together) -- the hook must clear all four before then.')

# ---------------------------------------------------------------------------
# 3. THEME x HOOK  (derived from outliers)
# ---------------------------------------------------------------------------
w('')
w('## 3. Theme x hook -- what pairing actually overperforms')
outliers = data.get('outliers', [])
# group: theme -> hook -> [views]; only outliers carrying >=1 theme
tk = defaultdict(lambda: defaultdict(list))
theme_tot = defaultdict(list)
for o in outliers:
    for th in (o.get('themes') or []):
        tk[th][o['hook']].append(o['views'])
        theme_tot[th].append(o['views'])
if tk:
    # top themes among overperformers = most outlier-reels, then higher median views
    top_themes = sorted(theme_tot.items(), key=lambda kv: (-len(kv[1]), -reel_io.med(kv[1]), kv[0]))[:5]
    w('')
    w('From the field outliers (reels >=2.5x their own creator median). For each top theme, the '
      'hook types that show up most among the overperformers -- copy the PAIRING, not the post.')
    w('')
    w('| Theme | Outlier reels | Top hook (count) | That hook med views |')
    w('|---|--:|---|--:|')
    jx['theme_hook'] = []
    for th, allv in top_themes:
        hooks_here = tk[th]
        best_hook, best_views = sorted(
            hooks_here.items(), key=lambda kv: (-len(kv[1]), -reel_io.med(kv[1]), kv[0]))[0]
        jx['theme_hook'].append(
            {'theme': th, 'outlier_reels': len(allv), 'top_hook': best_hook,
             'top_hook_count': len(best_views), 'top_hook_med_views': reel_io.med(best_views)})
        w(f"| {th} | {len(allv)} | {best_hook} ({len(best_views)}) | {fnum(reel_io.med(best_views))} |")
    w('')
    w('Detail (every hook seen per top theme, count x):')
    for th, _allv in top_themes:
        pairs = sorted(tk[th].items(), key=lambda kv: (-len(kv[1]), -reel_io.med(kv[1]), kv[0]))
        chunk = ', '.join(f"{hk} x{len(vs)}" for hk, vs in pairs)
        w(f'- **{th}:** {chunk}')
else:
    w('')
    w('Outliers in this dataset carry no theme tags (their captions did not match a tracked '
      'theme), so no theme x hook pairing can be derived. Fall back to Section 2 (hook types) '
      'crossed with Section 1 (themes) manually.')

# ---------------------------------------------------------------------------
# 4. OPENER PATTERNS
# ---------------------------------------------------------------------------
w('')
w('## 4. Opener patterns -- how winners actually start')
if FULL:
    best_field = [r for r in field_rows if r['group'] == 'best' and r['text']]
    # most common 4-word spoken openings in field BEST reels
    opens = Counter(opening_gram(r['text']) for r in best_field if opening_gram(r['text']).strip())
    common = [(p, c) for p, c in ranked(opens) if c > 1 and p.strip()][:12]
    jx['openers'] = {'mode': 'FULL',
                     'spoken_openings': [{'phrase': p, 'count': c} for p, c in common]}
    w('')
    w(f'Mined from the SPOKEN first words of {len(best_field)} field best-reels (not captions).')
    w('')
    if common:
        w('**Most common 4-word spoken openings in winners:**')
        for p, c in common:
            w(f'- "{p}..." ({c}x)')
    else:
        w('No 4-word opening recurred more than once across the best reels (high opener diversity '
          '-- winners do not share a single template phrase).')
    # best vs worst opening vocabulary
    bw, ww = Counter(), Counter()
    for r in field_rows:
        if not r['text']:
            continue
        (bw if r['group'] == 'best' else ww).update(content_words(r['text']))
    w('')
    jx['openers']['winner_vocab'] = [{'word': x, 'count': c} for x, c in ranked(bw)[:18]]
    jx['openers']['flop_vocab'] = [{'word': x, 'count': c} for x, c in ranked(ww)[:18]]
    w('**Opening vocabulary that clusters in WINNERS:** '
      + ', '.join(f'{x}({c})' for x, c in ranked(bw)[:18]))
    w('')
    w('**Opening vocabulary that clusters in FLOPS:** '
      + ', '.join(f'{x}({c})' for x, c in ranked(ww)[:18]))
    w('')
    w('Words that appear in the winner list but NOT the flop list are your sharpest spoken-hook '
      'wedges -- lead with them.')
else:
    w('')
    w('No transcripts, so opener mining falls back to written hook-lines + your own caption '
      'first-lines (a weaker proxy for the spoken first 2 seconds).')
    # opener patterns from outlier hook_line: leading 4 words across all outliers
    ol_opens = Counter()
    for o in outliers:
        g = opening_gram(reel_io.fix(o.get('hook_line', '')))
        if g.strip():
            ol_opens[g] += 1
    common = [(p, c) for p, c in ranked(ol_opens) if c > 1 and p.strip()][:10]
    jx['openers'] = {'mode': 'CAPTION_ONLY',
                     'spoken_openings': [{'phrase': p, 'count': c} for p, c in common],
                     'client_first_lines': []}
    w('')
    if common:
        w('**Recurring 4-word openings across the field outlier hook-lines:**')
        for p, c in common:
            w(f'- "{p}..." ({c}x)')
    else:
        w('Field outlier hook-lines share no repeated 4-word opening (each winner opens '
          'differently) -- study the full hook-lines in Section 3 sources instead.')
    if src_reels:
        w('')
        w('**Your current caption first-lines (top reels by views) -- your opener habit today:**')
        top_client = sorted(src_reels, key=lambda r: (-r['views'], r['url'] or ''))[:8]
        for r in top_client:
            first = reel_io.fix((r['cap'] or '').split('\n')[0])[:90].replace('|', '/')
            jx['openers']['client_first_lines'].append({'views': r['views'], 'line': first})
            w(f"- {fnum(r['views'])}v -- {first}")

w('')
w('**Opener order (non-negotiable): HOOK -> PROMISE -> MICRO-INTRO.** Open on the hook, then '
  'promise the payoff ("by the end you will know exactly how to X"), and only THEN introduce '
  'yourself -- never lead with your name or a greeting. The self-intro is a <=6-second, '
  'credibility-fused line ("I am X, I have done Y N times") that earns the next 30 seconds; it '
  'comes AFTER the hook+promise have bought the attention, not before, when it just burns the '
  'opening on someone the viewer has no reason to care about yet.')

# ---------------------------------------------------------------------------
# 5. WINNING STRUCTURES
# ---------------------------------------------------------------------------
w('')
w('## 5. Winning structures -- open -> develop -> CTA')
if FULL:
    best_field = [r for r in field_rows if r['group'] == 'best' and r['text']]
    lens = [len(r['text']) for r in best_field]
    med_len = reel_io.med(lens)
    # hook-type distribution of the openers of best field reels (how they OPEN)
    open_hooks = Counter(hook_type(first_sentence(r['text'])) for r in best_field)
    cta_pat = re.compile(r'\b(comment|dm|link in bio|save this|share this|follow|tap|click|sign up|book|grab|download|join)\b', re.I)
    cta_rate = (sum(1 for r in best_field if cta_pat.search(r['text'])) / len(best_field) * 100) if best_field else 0
    jx['structures'] = [{
        'name': 'hook -> one story or mechanism -> single explicit ask',
        'mode': 'FULL',
        'n_best_reels': len(best_field),
        'beats': [
            {'beat': 'open', 'open_hook_mix': [{'hook': hk, 'count': c} for hk, c in ranked(open_hooks)[:4]]},
            {'beat': 'develop', 'med_body_chars': med_len, 'approx_seconds': med_len / 15},
            {'beat': 'cta', 'spoken_cta_rate_pct': cta_rate},
        ],
    }]
    w('')
    w(f'Across {len(best_field)} field best-reel transcripts:')
    w('')
    w('- **Open:** the winning first move skews to '
      + ', '.join(f'{hk} ({c})' for hk, c in ranked(open_hooks)[:4])
      + ' -- i.e. they lead with a hook type, not a topic announcement.')
    w(f'- **Develop:** median spoken body is ~{fnum(med_len)} characters '
      f'(~{fnum(med_len/15)} seconds of talking) -- one tight idea developed, not a list of five.')
    w(f'- **CTA:** {cta_rate:.0f}% of winners put an explicit call-to-action in the spoken track '
      '(comment / DM keyword / save / follow). The rest let the content carry and CTA in caption.')
    w('')
    w('Template that fits this data: **[hook in first sentence] -> [one story or one mechanism] '
      '-> [single explicit ask].** Do not stack multiple asks.')
else:
    w('')
    w('Structure (open -> develop -> CTA) needs the spoken track to read reliably, and there are '
      'no transcripts here. Light inference from the outlier hook-lines only:')
    cta_lines = [o for o in outliers if re.search(r'\b(comment|dm|link|save|share|follow|book|episode)\b', (o.get('hook_line') or ''), re.I)]
    jx['structures'] = [{
        'name': 'open -> develop -> CTA (degraded: no transcripts)',
        'mode': 'CAPTION_ONLY',
        'note': ('Structure needs the spoken track; only a light inference from outlier '
                 'hook-lines is available. Harvest transcripts and re-run in FULL mode.'),
        'outliers_total': len(outliers),
        'outliers_with_opening_cta': len(cta_lines),
    }]
    w('')
    w(f'- Of the {len(outliers)} field outliers, {len(cta_lines)} put an explicit CTA / '
      'engagement-bait right in the opening line (e.g. "Comment X", "link in bio") -- a common '
      'overperformer move worth testing.')
    w('- For real open->develop->CTA structure, harvest transcripts and re-run in FULL mode.')

# ---------------------------------------------------------------------------
# 6. LENGTH TARGETS
# ---------------------------------------------------------------------------
w('')
w('## 6. Length targets')
if FULL:
    def med_len_of(rs, grp):
        L = [len(r['text']) for r in rs if r['group'] == grp and r['text']]
        return reel_io.med(L)
    fb_len = med_len_of(field_rows, 'best'); fw_len = med_len_of(field_rows, 'worst')
    cb_len = med_len_of(client_rows, 'best'); cw_len = med_len_of(client_rows, 'worst')
    w('')
    w('Spoken length in characters (rough seconds = chars / 15).')
    w('')
    w('| Group | Best med chars | Best ~sec | Worst med chars | Worst ~sec |')
    w('|---|--:|--:|--:|--:|')
    w(f'| Field | {fnum(fb_len)} | {fnum(fb_len/15)} | {fnum(fw_len)} | {fnum(fw_len/15)} |')
    if client_rows:
        w(f'| You | {fnum(cb_len)} | {fnum(cb_len/15)} | {fnum(cw_len)} | {fnum(cw_len/15)} |')
    w('')
    _ln_notes = []
    if fb_len and fw_len and fb_len < fw_len:
        w('Field winners talk **less** than field flops -- tighter beats longer.')
        _ln_notes.append('Field winners talk less than field flops -- tighter beats longer.')
    if client_rows and cb_len and fb_len and cb_len > fb_len * 1.15:
        w(f'You run ~{cb_len/fb_len:.1f}x longer than the field median even on your winners -- '
          f'trim the wind-up. Target ~{fnum(fb_len)} spoken chars (~{fnum(fb_len/15)} sec) for reach reels.')
        _ln_notes.append(f'You run ~{cb_len/fb_len:.1f}x longer than the field median even on your '
                         f'winners -- trim the wind-up. Target ~{fnum(fb_len)} spoken chars '
                         f'(~{fnum(fb_len/15)} sec) for reach reels.')
    elif not client_rows:
        w('No client transcripts to compare length against -- match the field best target above.')
        _ln_notes.append('No client transcripts to compare length against -- match the field best target above.')
    jx['length_target'] = {
        'field_best_chars': fb_len, 'field_best_sec': fb_len / 15,
        'field_worst_chars': fw_len, 'field_worst_sec': fw_len / 15,
        'note': ' '.join(_ln_notes),
    }
    if client_rows:
        jx['length_target']['client_best_chars'] = cb_len
        jx['length_target']['client_best_sec'] = cb_len / 15
        jx['length_target']['client_worst_chars'] = cw_len
        jx['length_target']['client_worst_sec'] = cw_len / 15
else:
    w('')
    durs = [r['dur'] for r in src_reels if isinstance(r['dur'], (int, float))]
    if durs:
        top = sorted(src_reels, key=lambda r: (-r['views'], r['url'] or ''))[:12]
        top_durs = [r['dur'] for r in top if isinstance(r['dur'], (int, float))]
        jx['length_target'] = {
            'basis': 'duration',
            'client_all_med_sec': reel_io.med(durs),
            'client_all_min_sec': min(durs), 'client_all_max_sec': max(durs),
            'client_n': len(durs),
            'client_top_med_sec': (reel_io.med(top_durs) if top_durs else None),
            'note': ('No transcripts: spoken-length target unavailable. Use your own top-reel '
                     'duration as the floor; harvest competitor transcripts for the field target.'),
        }
        w('From your own reels (source data) since there are no transcripts to measure spoken length:')
        w('')
        w(f'- **All your reels:** median duration {fnum(reel_io.med(durs))}s '
          f'(min {fnum(min(durs))}s, max {fnum(max(durs))}s, n={len(durs)}).')
        if top_durs:
            w(f'- **Your top {len(top_durs)} reels by views:** median duration {fnum(reel_io.med(top_durs))}s.')
        w('')
        w('Use your own top-reel duration as the floor; harvest competitor transcripts to learn '
          'the field spoken-length target.')
    else:
        jx['length_target'] = {
            'basis': 'none',
            'note': ('No duration data in source/reels-full.json -- cannot set a length target '
                     'without transcripts or durations.'),
        }
        w('No duration data in source/reels-full.json -- cannot set a length target without '
          'transcripts or durations.')

# ---------------------------------------------------------------------------
# 7. YOUR CURRENT PATTERNS  (the gap to close)
# ---------------------------------------------------------------------------
w('')
w('## 7. Your current patterns -- the gap to close')
# client hook mix: prefer spoken transcripts (FULL); else infer from hook_taxonomy client_n
if FULL and client_rows:
    cmix = Counter(hook_type(first_sentence(r['text'])) if r['text'] else 'none' for r in client_rows)
    w('')
    w('**Your spoken hook mix today** (from your transcripts): '
      + ', '.join(f'{hk} ({c})' for hk, c in ranked(cmix)))
else:
    cmix = Counter()
    for h in data.get('hook_taxonomy', []):
        if h['client_n']:
            cmix[h['hook']] = h['client_n']
    w('')
    w('**Your hook mix today** (from caption analysis in the JSON): '
      + (', '.join(f'{hk} ({c})' for hk, c in ranked(cmix)) if cmix else 'no client hooks recorded'))

# themes the client actually leans on now
client_themes = sorted([t for t in themeperf if t.get('client_reels', 0) > 0],
                       key=lambda t: (-t['client_reels'], t['theme']))
if client_themes:
    w('')
    w('**Themes you actually post now** (by your reel count): '
      + ', '.join(f"{t['theme']} ({t['client_reels']})" for t in client_themes[:6]))

# the explicit gap: top winning hook you under-use + top gap theme
w('')
w('**The gap to close:**')
if underused:
    top_u = sorted(underused, key=lambda h: (-h['field_med_views'], h['hook']))[0]
    w(f"- Hook: the field's strongest hooks include **{top_u['hook']}** "
      f"({fnum(top_u['field_med_views'])} median views) yet you have only {top_u['client_n']}. "
      'Bake it into your next batch.')
if gaps:
    order = {'absent': 0, 'underweight': 1}
    top_g = sorted(gaps, key=lambda g: (order.get(g['reason'], 2), -g['field_med_views'], g['theme']))[0]
    w(f"- Theme: **{top_g['theme']}** ({top_g['reason']}, {fnum(top_g['field_med_views'])} field "
      f"median views) -- you run {top_g['client_reels']} reels here vs {top_g['field_reels']} field. Close it.")
else:
    if themeperf:
        top_head = max((t for t in themeperf if t.get('client_reels', 0) > 0),
                       key=lambda t: (t['field_med_views'] - t.get('client_med_views', 0)), default=None)
        if top_head:
            w(f"- Theme: no whitespace gaps, but **{top_head['theme']}** has the widest reach "
              f"headroom -- field {fnum(top_head['field_med_views'])} vs your "
              f"{fnum(top_head.get('client_med_views', 0))} median views on the same theme.")
if FULL and client_rows:
    w('- Craft: compare your spoken hook mix above to Section 2 -- shift volume toward the '
      'above-median hook types and away from the below-median ones.')
else:
    w('- Craft: harvest your reel transcripts to unlock spoken-hook, opener, structure, and '
      'length analysis (Sections 4-6) at full strength.')

# capture §7 (current_patterns) from the SAME settled variables the .md just rendered
_gap_bits = []
if underused:
    _gu = sorted(underused, key=lambda h: (-h['field_med_views'], h['hook']))[0]
    _gap_bits.append(f"Hook: lean into {_gu['hook']} ({fnum(_gu['field_med_views'])} field median "
                     f"views) -- you have only {_gu['client_n']}.")
if gaps:
    _go = {'absent': 0, 'underweight': 1}
    _gg = sorted(gaps, key=lambda g: (_go.get(g['reason'], 2), -g['field_med_views'], g['theme']))[0]
    _gap_bits.append(f"Theme: {_gg['theme']} ({_gg['reason']}, {fnum(_gg['field_med_views'])} field "
                     f"median views) -- you run {_gg['client_reels']} vs {_gg['field_reels']} field.")
else:
    _th = None
    if themeperf:
        _th = max((t for t in themeperf if t.get('client_reels', 0) > 0),
                  key=lambda t: (t['field_med_views'] - t.get('client_med_views', 0)), default=None)
    if _th:
        _gap_bits.append(f"Theme: no whitespace gaps, but {_th['theme']} has the widest reach headroom "
                         f"-- field {fnum(_th['field_med_views'])} vs your "
                         f"{fnum(_th.get('client_med_views', 0))} median views.")
jx['current_patterns'] = {
    'client_hook_mix': [{'hook': hk, 'count': c} for hk, c in ranked(cmix)],
    'client_themes': [{'theme': t['theme'], 'count': t['client_reels']} for t in client_themes[:6]],
    'gap_note': ' '.join(_gap_bits),
}

w('')
w('---')
w(f'Generated by reel-scripter (Content Superengine) from analysis-data.json '
  f'(schema {meta.get("schema_version", "?")}). Mode: {"FULL" if FULL else "CAPTION-ONLY"}.')

# write the brief (utf-8; real unicode allowed in the file)
with open(os.path.join(ROOT, 'scripting-brief.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')

# ============================================================================
# BUILD + WRITE scripting-brief.json  (structured twin of the 7 sections above)
# Reuses the SAME variables/numbers the .md rendered (captured into jx per section);
# never recomputes. Deterministic -> byte-identical across runs (git-diffed fixture).
# Feeds the browser "Scripting Studio" UI, so keys are stable + mode-aware.
# ============================================================================
brief = {
    'meta': {
        'client_handle': HANDLE,
        'mode': 'FULL' if FULL else 'CAPTION_ONLY',
        'schema_version': '1.0',
        'total_reels': meta.get('total_reels', 0),
        'n_competitors': n_field_creators,
    },
    'attack_themes': jx.get('attack_themes', []),
    'winning_hooks': jx.get('winning_hooks', []),
    'theme_hook': jx.get('theme_hook', []),
    'openers': jx.get('openers', {'mode': 'FULL' if FULL else 'CAPTION_ONLY'}),
    'structures': jx.get('structures', []),
    'length_target': jx.get('length_target', {}),
    'current_patterns': jx.get('current_patterns', {}),
}
with open(os.path.join(ROOT, 'scripting-brief.json'), 'w', encoding='utf-8') as f:
    json.dump(brief, f, indent=2, ensure_ascii=False)
    f.write('\n')

# ============================================================================
# CONSOLE SUMMARY  (ASCII-only -- cp1252 console raises on non-ASCII)
# ============================================================================
def asc(s):
    return str(s).encode('ascii', 'ignore').decode()

print('=== REEL SCRIPTING BRIEF ===')
print(f'client: @{asc(HANDLE)}  |  mode: {"FULL" if FULL else "CAPTION-ONLY"}')
if FULL:
    print(f'transcripts: {len(rows)} ({len(field_rows)} field + {len(client_rows)} client)')
else:
    print(f'transcripts: none (caption-only); source reels: {len(src_reels)}')
print(f'themes tracked: {len(meta.get("themes", []))}  |  gaps flagged: {len(gaps)}  |  outliers: {len(outliers)}')
if gaps:
    order = {'absent': 0, 'underweight': 1}
    print('attack themes:')
    for g in sorted(gaps, key=lambda g: (order.get(g['reason'], 2), -g['field_med_views'], g['theme'])):
        print(f'  - {asc(g["theme"]):22} {g["reason"]:11} field_med={g["field_med_views"]:>10,.0f} you={g["client_reels"]}')
else:
    print('attack themes: none flagged (cover-existing-themes-harder mode)')
if underused:
    print('under-used winning hooks:')
    for h in sorted(underused, key=lambda h: (-h['field_med_views'], h['hook']))[:4]:
        print(f'  - {asc(h["hook"]):22} field_med={h["field_med_views"]:>10,.0f} you_n={h["client_n"]}')
print('wrote scripting-brief.md')
