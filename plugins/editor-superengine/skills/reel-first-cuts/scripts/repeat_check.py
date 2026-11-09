#!/usr/bin/env python3
# Ported from Shorts Studio, scripts/repeat_check.py. MIT License, Copyright (c) 2026 Claude Video Studio contributors
# (full text in LICENSES/NOTICE).
# changed: the finder (repeat, cut-off start, restart, retake) is kept as it was; it also reads S3's edit map
# (`word`/`start`/`end`); deep mode uses the editor's own transcriber from state.json through S3's route() (no npx),
# loading the model once per run (parakeet_local.py --batch, or one faster-whisper process); ffmpeg from the
# editor's install; windows sliced with the wave module; argparse; UTF-8 output; the temp folder is removed.
# added (ours, N1): "never" is said twice on purpose; reworded retakes are flagged for review (loose(), --review),
# never cut and never counted in the exit code.
"""repeat_check.py: find stutters, repeats and restarts in a transcript (cut every false start).

usage: repeat_check.py <words.json> [--gap 1.5] [--json out.json] [--review review.json] [--jaccard 0.5]
       repeat_check.py <words.json> --audio <voice.wav|cut.mp4> [--win 3.0]   (deep: re-listens in short windows)

words.json: work/edit_map.cut.json or tx-cut.json ({"words": [{"word","start","end"}]}), or [{"w","s","e"}] /
[{"text","start","end"}].
It finds:
- a word or phrase said twice in a row: "and fixes and fixes", "the the", "so to so to"
- a cut-off start: "Sched- Schedule" (a short word that is the start of the next word)
- a restart: the same 2+ words again within --gap seconds, with up to 2 words between ("it is, it's live")
- a retake: the same sentence (5+ words, one word may differ) said again within 15 s: drop the first take
For each one it prints the time span to DROP (the FIRST copy, so the clean take stays) and exits 1 if it found any.
It also flags reworded retakes for review: two sentences starting within 15 s that share at least --jaccard of their
content words (shared / all) but don't pass the strict retake rule. A person picks which one stays (the Cut Board),
so these are never in the drop list (--json), never in the "N repeat(s) found" count and never change the exit code;
--review writes them as [{kind: "loose-retake", tier: "review", text, at, first, second, n, m, jaccard}]
(n and m: the word counts of the first and the second sentence).
A transcriber often merges repeats into one copy ("and fixes and fixes" came back as "and fixes"). So --audio
re-transcribes the voice in short overlapping windows (3 s, step 1.5 s) where the engine has no context to tidy the
repeat away, finds repeats in each window and maps them back to the file's time line. The engine is the one
state.json names (the editor doctor's pick), and its model loads once for all the windows.
Limit: deep mode catches restarts within about 3 s (both copies inside one window). Retakes further apart are
the shallow finder's job: it reads the whole transcript (a line said again 8 s later is found there, not here).

Exit codes: 0 no repeats, 1 repeats found, 3 no transcriber on this computer, 5 a transcriber step failed.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402


def norm(w):
    return re.sub(r"[^a-z0-9$']", '', w.lower().replace('’', "'"))


def load(p):
    W = json.load(open(p, encoding="utf-8")); W = W.get('words', W) if isinstance(W, dict) else W
    out = []
    for w in W:
        t = w.get('w', w.get('text', w.get('word', '')))
        out.append(dict(w=t, n=norm(t), s=float(w.get('s', w.get('start', 0))), e=float(w.get('e', w.get('end', 0)))))
    return [w for w in out if w['n']]


def find(W, gap=1.5):
    hits, used = [], set()
    N = len(W)
    for n in (4, 3, 2, 1):                      # longest phrase first
        for i in range(N - n):
            if any(k in used for k in range(i, i + n)): continue
            a = [W[k]['n'] for k in range(i, i + n)]
            for skip in (0, 1, 2) if n >= 2 else (0,):
                j = i + n + skip
                if j + n > N: break
                b = [W[k]['n'] for k in range(j, j + n)]
                if a != b or W[j]['s'] - W[i + n - 1]['e'] > gap: continue
                if n == 1 and a[0] in ('ha', 'very', 'really', 'no', 'yeah', 'bye', 'never') : continue   # said twice on purpose
                if W[i + n - 1]['w'].rstrip().endswith(('.', '?', '!')) and skip == 0: continue   # "...draw it. It is..." is a new sentence
                hits.append(dict(kind='repeat' if skip == 0 else 'restart', text=' '.join(W[k]['w'] for k in range(i, j + n)),
                                 drop=[round(W[i]['s'], 3), round(W[j]['s'], 3)], first=i, second=j, n=n))
                used.update(range(i, j)); break
    # retake: the same sentence said again within 15 s, allowing one changed or dropped word ("into a beautiful hand-drawn
    # illustration" -> "into a hand-drawn illustration"). A 10-word retake slipped past the 1 to 4 word check.
    def run(i, j):
        n = k = 0; skips = 0
        while i + n < N and j + k < N and j + k > i + n:
            if W[i + n]['n'] == W[j + k]['n']: n += 1; k += 1; continue
            if skips >= 1: break
            if i + n + 1 < N and W[i + n + 1]['n'] == W[j + k]['n']: n += 1; skips += 1; continue   # a word dropped in the retake
            if j + k + 1 < N and W[i + n]['n'] == W[j + k + 1]['n']: k += 1; skips += 1; continue   # a word added in the retake
            n += 1; k += 1; skips += 1                                                               # a word changed
        return n, k
    for i in range(N):
        if any(i in range(h['first'], h['second']) for h in hits): continue
        for j in range(i + 4, min(N, i + 60)):
            if W[j]['s'] - W[i]['s'] > 15 or W[j]['n'] != W[i]['n']: continue
            n, k = run(i, j)
            if n >= 5 and k >= 5 and j >= i + n - 1:
                hits.append(dict(kind='retake', text=' '.join(W[x]['w'] for x in range(i, i + n)) + ' | ' + ' '.join(W[x]['w'] for x in range(j, j + k)),
                                 drop=[round(W[i]['s'], 3), round(W[j]['s'], 3)], first=i, second=j, n=n)); break
    for i in range(N - 1):                       # cut-off start: "Sched-" then "Schedule"
        a, b = W[i]['n'], W[i + 1]['n']
        if i in used or len(a) < 2 or len(a) >= len(b): continue
        if b.startswith(a) and (W[i]['w'].endswith('-') or W[i]['e'] - W[i]['s'] < 0.18):
            hits.append(dict(kind='cut-off', text=f"{W[i]['w']} {W[i+1]['w']}", drop=[round(W[i]['s'], 3), round(W[i + 1]['s'], 3)], first=i, second=i + 1, n=1))
    return sorted(hits, key=lambda h: h['drop'][0])


STOP = set("a an the and or but so to of in on at for with from by as is are was were be been am it its it's this "
           "that these those there here i i'm you you're your we we're our they he she my me us them um uh oh like "
           "just then do does did can will would could all really very".split())


def loose(W, hits, jaccard=0.5, span=15.0):
    """Reworded retakes: two sentences starting within `span` s whose content-word sets overlap by `jaccard` or more
    (shared / all) and that no strict hit already joins. Tier "review", with no drop span: a person picks. Runs on
    the whole transcript only, never inside deep mode's 3 s windows (find() stays strict)."""
    # ponytail: sentences end only at . ? ! ; an unpunctuated transcript is one sentence, so nothing is flagged.
    S, lo = [], 0
    for k, w in enumerate(W):
        if w['w'].rstrip().endswith(('.', '?', '!')) or k == len(W) - 1:
            S.append((lo, k, {x['n'] for x in W[lo:k + 1]} - STOP)); lo = k + 1
    out = []
    for a, (i0, i1, A) in enumerate(S):
        if len(A) < 3: continue                  # "Done." twice is not a retake
        for j0, j1, B in S[a + 1:]:
            if W[j0]['s'] - W[i0]['s'] > span: break
            if len(B) < 3: continue
            jac = len(A & B) / len(A | B)
            if jac < jaccard or any(i0 <= h['first'] <= i1 and j0 <= h['second'] <= j1 for h in hits): continue
            out.append(dict(kind='loose-retake', tier='review',
                            text=' '.join(W[x]['w'] for x in range(i0, i1 + 1)) + ' | ' + ' '.join(W[x]['w'] for x in range(j0, j1 + 1)),
                            at=[round(W[i0]['s'], 3), round(W[j0]['s'], 3)], first=i0, second=j0, n=i1 - i0 + 1, m=j1 - j0 + 1, jaccard=round(jac, 3)))
            break
    return out


# ------------------------------------------------------------------------------ deep mode
def tool(name):
    """The editor's own ffmpeg/ffprobe (state.json), else the one on PATH."""
    try:
        p = rt.tool(name)
        if Path(p).exists():
            return p
    except (KeyError, OSError):
        pass
    return shutil.which(name)


class Stop(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def engine_ready():
    """(engine, editor python, language) the way transcribe_words.py picks them: state.json's engine, after S3's
    route() (the doctor's re-pick for this workspace's language)."""
    import transcribe_words as tw
    state = rt.load_state()
    if not state.get("engine"):
        raise Stop(3, "Transcription isn't set up on this computer yet. Run the editor doctor first.")
    if state["engine"] == "none":
        raise Stop(3, state.get("engine_reason") or "This computer has no transcriber.")
    vpy = rt.tool("python")
    if not Path(vpy).exists():
        raise Stop(3, "The editor's Python is missing. Run the editor doctor to repair the setup.")
    language = rt.read_config().get("language")
    if tw.route(state, language, vpy):
        raise Stop(3, "The transcriber switch didn't finish, so the deep check didn't run.")
    engine = rt.load_state().get("engine")
    if engine.startswith("parakeet") and not rt.is_english(language):
        raise Stop(3, "The workspace language is %s, and Parakeet understands English only. Run the editor doctor "
                      "so it sets up the multilingual transcriber." % language)
    return engine, vpy, language


def transcribe_all(wavs, tmp, engine, vpy, language):
    """Every window in ONE engine process, so the model loads once. Returns ([words per wav], loads)."""
    lst, out = Path(tmp) / "wavs.json", Path(tmp) / "heard.json"
    lst.write_text(json.dumps([str(w) for w in wavs]), encoding="utf-8")
    if engine.startswith("parakeet"):
        cmd = [vpy, "-X", "utf8", "-I", str(HERE / "parakeet_local.py"), "--batch", str(lst), str(out)]
    else:
        print(rt.BACKUP_WARNING)
        cmd = [vpy, "-X", "utf8", "-I", str(Path(__file__).resolve()), "--whisper-batch", str(lst), str(out),
               rt.lang_key(language)]
    if subprocess.run(cmd, env=rt.python_env()).returncode:
        raise Stop(5, "The transcriber stopped, so the deep check didn't finish.")
    d = json.loads(out.read_text(encoding="utf-8"))
    return [r["words"] for r in d["results"]], d.get("loads")


def whisper_batch(lst, out, language):
    """faster-whisper for every window in this one process (the backup engine; runs in the editor's Python).
    The transcription contract holds: word timestamps on, VAD on, no vocabulary prompt."""
    import transcribe_words as tw
    from faster_whisper import WhisperModel
    device = tw.pick_device("auto")
    model = WhisperModel(rt.model_dir("faster-whisper"), device=device, compute_type=tw.pick_precision(device, None))
    results = []
    for wav in json.loads(Path(lst).read_text(encoding="utf-8")):
        segs, _ = model.transcribe(wav, language=language, word_timestamps=True, vad_filter=True)
        words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
                 for s in segs for w in (s.words or [])]
        results.append({"wav": wav, "words": words})
    Path(out).write_text(json.dumps({"results": results, "loads": 1}, ensure_ascii=False), encoding="utf-8")
    print("[faster-whisper] model loaded once for %d file(s) on %s" % (len(results), device), file=sys.stderr)


def deep(audio, win=3.0, gap=1.5):
    """Re-listen in short windows. Returns hits with times on the full file."""
    import transcribe_words as tw
    ffmpeg = tool("ffmpeg")
    if not ffmpeg:
        raise Stop(3, "ffmpeg is missing. Run the editor doctor to repair the setup.")
    engine, vpy, language = engine_ready()
    t_start = time.time()
    tmp = tempfile.mkdtemp(prefix='es-rep-')
    try:
        wav = os.path.join(tmp, 'a.wav')
        p = subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', audio, '-vn', '-ac', '1', '-ar', '16000',
                            '-c:a', 'pcm_s16le', wav], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise Stop(5, "could not read the audio of %s: %s" % (audio, p.stderr.strip()[-300:]))
        with wave.open(wav) as w:
            sr, pcm = w.getframerate(), w.readframes(w.getnframes())
        dur = len(pcm) / 2 / sr
        starts, wavs, t0 = [], [], 0.0
        while t0 < dur - 0.5:
            sl = os.path.join(tmp, f's{t0:.1f}.wav')
            with wave.open(sl, 'wb') as o:
                o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr)
                o.writeframes(pcm[round(t0 * sr) * 2:round((t0 + win) * sr) * 2])
            starts.append(t0); wavs.append(sl)
            t0 += win / 2
        heard, loads = transcribe_all(wavs, tmp, engine, vpy, language)
        hits = []
        for t0, R in zip(starts, heard):
            tw.fill_untimed(R, min(win, dur - t0))
            W = [dict(w=w['word'].strip(), n=norm(w['word'].strip().rstrip('.-')), s=w['start'] + t0, e=w['end'] + t0) for w in R]
            W = [w for w in W if w['n']]
            for h in find(W, gap):
                if not any(abs(h['drop'][0] - g['drop'][0]) < 0.3 for g in hits): hits.append(h)
        print("deep: engine %s | %d windows of %.1f s | model loaded %s time(s) | %.1f s"
              % (engine, len(wavs), win, loads, time.time() - t_start))
        return sorted(hits, key=lambda h: h['drop'][0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ensure_utf8_output()
    if len(sys.argv) > 1 and sys.argv[1] == "--whisper-batch":   # the faster-whisper child (editor's Python only)
        whisper_batch(*sys.argv[2:5])
        return 0
    ap = argparse.ArgumentParser(description="Find repeats, restarts, retakes and cut-off starts.")
    ap.add_argument("words")
    ap.add_argument("--gap", type=float, default=1.5)
    ap.add_argument("--json", help="write the hits here")
    ap.add_argument("--audio", help="deep mode: re-listen to this file in short windows (catches restarts within about 3 s; retakes further apart are the shallow finder's job)")
    ap.add_argument("--win", type=float, default=3.0)
    ap.add_argument("--jaccard", type=float, default=0.5, help="reworded retakes: the share of content words (shared / all) two sentences need in common to be flagged for review")
    ap.add_argument("--review", help="write the reworded retakes (tier review: never cut, not in the exit code) here")
    a = ap.parse_args()
    W = load(a.words)
    H = find(W, a.gap)
    R = loose(W, H, a.jaccard)
    if a.audio:
        try:
            D = deep(a.audio, a.win, a.gap)
        except Stop as e:
            print(str(e), file=sys.stderr)
            return e.code
        for h in D: h['kind'] += ' (heard)'
        H = sorted(H + [h for h in D if not any(abs(h['drop'][0] - g['drop'][0]) < 0.3 for g in H)], key=lambda h: h['drop'][0])
    for h in H: print(f"{h['kind']:8s} {h['drop'][0]:7.2f}-{h['drop'][1]:7.2f}  \"{h['text']}\"  -> drop the first copy")
    if a.json: Path(a.json).write_text(json.dumps(H, ensure_ascii=False, indent=1), encoding="utf-8")
    for h in R: print(f"review   {h['at'][0]:7.2f} {h['at'][1]:7.2f}  \"{h['text']}\"  -> said twice in different words: pick one (not cut)")
    if a.review: Path(a.review).write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(H)} repeat(s) found" if H else 'no repeats found')
    if R: print(f"{len(R)} reworded retake(s) for review (not cut)")
    return 1 if H else 0


if __name__ == '__main__':
    sys.exit(main())
