# Generalized caption harvester: pull YouTube auto-captions for a channel/playlist via yt-dlp (seconds, no Whisper).
# Usage:  python caption_harvest.py "<channel-or-playlist-url>" <creator_slug> <out_dir>
# Whisper fallback only for videos with no caption track.
import os, re, sys, json, glob, subprocess

def run(url, creator, out_dir):
    subs = os.path.join(out_dir, '_subs'); tx = out_dir
    os.makedirs(subs, exist_ok=True); os.makedirs(tx, exist_ok=True)

    flat = subprocess.run(['yt-dlp', '--flat-playlist', '--no-warnings', '--print', '%(id)s|%(title)s', url],
                          capture_output=True, text=True)
    vids = [l.split('|', 1) for l in flat.stdout.splitlines() if '|' in l]
    print(f'{len(vids)} videos in {url}')

    def slug(t): return re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-')[:70]

    def parse_json3(p):
        d = json.load(open(p, encoding='utf-8')); lines = []
        for ev in d.get('events', []):
            seg = ''.join(s.get('utf8', '') for s in (ev.get('segs') or [])).strip()
            if seg and seg != '\n': lines.append(seg)
        return re.sub(r'\s+', ' ', ' '.join(lines)).strip()

    no_caption = []
    for i, (vid, title) in enumerate(vids, 1):
        vid, title = vid.strip(), title.strip()
        if glob.glob(f'{tx}/*- {vid}.md') or glob.glob(f'{tx}/*-{vid}.md'):
            continue
        base = f'{subs}/{vid}'
        subprocess.run(['yt-dlp', '-q', '--no-warnings', '--skip-download', '--write-auto-subs', '--write-subs',
                        '--sub-lang', 'en', '--sub-format', 'json3', '--write-info-json',
                        '-o', f'{base}.%(ext)s', f'https://www.youtube.com/watch?v={vid}'],
                       capture_output=True, text=True)
        sf = glob.glob(f'{base}*.json3'); inf = glob.glob(f'{base}*.info.json')
        if not sf:
            no_caption.append(vid); print(f'[{i}/{len(vids)}] NO CAPTION {vid} (Whisper fallback needed)'); continue
        txt = parse_json3(sf[0])
        date = '00000000'
        if inf:
            try: date = json.load(open(inf[0], encoding='utf-8')).get('upload_date') or '00000000'
            except Exception: pass
        if len(txt) < 120:
            no_caption.append(vid); print(f'[{i}/{len(vids)}] EMPTY {vid}'); continue
        out = f'{tx}/{creator} - {slug(title)} - {date}.md'
        open(out, 'w', encoding='utf-8').write(
            f'# {title}\n- creator: {creator}\n- upload_date: {date}\n- video_id: {vid}\n'
            f'- url: https://www.youtube.com/watch?v={vid}\n- source: youtube auto-captions (yt-dlp)\n\n'
            f'## TRANSCRIPT\n\n{txt}\n')
        print(f'[{i}/{len(vids)}] OK {vid} ({date}) {len(txt):,} chars')
    if no_caption:
        print(f'\n{len(no_caption)} videos need Whisper fallback:', no_caption)
    print('DONE')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('usage: python caption_harvest.py "<channel-or-playlist-url>" <creator_slug> <out_dir>'); sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])
