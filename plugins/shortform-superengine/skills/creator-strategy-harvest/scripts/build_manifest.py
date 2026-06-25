# Build a vault-handoff manifest: scan harvested transcript md files -> per-file facets JSON.
# Usage: python build_manifest.py <harvest_dir> <out.json>
# Reads the '- key: value' metadata block at the top of each transcript; newsletter files get derived facets.
import glob, os, re, sys, json
from collections import Counter

def hdr(path):
    d = {}
    for line in open(path, encoding='utf-8').read().splitlines()[:12]:
        m = re.match(r'-\s*(\w+):\s*(.+)', line)
        if m: d[m.group(1)] = m.group(2).strip()
    return d

def norm(c):
    c = (c or '').split('(')[0].strip().lower()
    return c

def build(harvest_dir, out):
    rows = []
    for f in glob.glob(os.path.join(harvest_dir, '**', '*.md'), recursive=True):
        base = os.path.basename(f).lower()
        rel = os.path.relpath(f, harvest_dir).replace(os.sep, '/')
        if 'newsletter' in rel or base.startswith('blueprint'):
            slug = re.sub(r'^blueprint-?', '', os.path.basename(f)[:-3])
            rows.append(dict(path=rel, author='', content_type='newsletter',
                             source_platform='web', date='', issue=re.sub(r'[^0-9]', '', slug) or slug, url=''))
            continue
        h = hdr(f)
        if 'upload_date' not in h and 'creator' not in h:
            continue  # not a transcript
        ctype = 'short' if 'short' in rel else 'video'
        rows.append(dict(path=rel, author=norm(h.get('creator', '')), content_type=ctype,
                         source_platform='youtube', date=h.get('upload_date', ''),
                         url=h.get('url', ''), video_id=h.get('video_id', '')))
    json.dump(rows, open(out, 'w', encoding='utf-8'), indent=1)
    c = Counter((r['author'], r['content_type']) for r in rows)
    print(f'{len(rows)} files ->', out)
    for k, v in sorted(c.items()): print('  ', k, v)
    print('missing date (non-newsletter):', sum(1 for r in rows if not r['date'] and r['content_type'] != 'newsletter'))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python build_manifest.py <harvest_dir> <out.json>'); sys.exit(1)
    build(sys.argv[1], sys.argv[2])
