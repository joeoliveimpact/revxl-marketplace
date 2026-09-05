#!/usr/bin/env python3
"""Batch reel transcription for competitor-cross-reference (Step 4c pattern matrix,
and the deep-read layer of the roadmap).

Usage:  python transcribe_reels.py <project_dir> [top_n] [bottom_n]
        top_n/bottom_n default 10/10 (per creator, ranked by views; all if <= top+bottom).

Pipeline per reel — NO downloading, NO yt-dlp, NO scraping (see SKILL.md Transcription):
  the pulled reel JSON already carries a signed IG CDN .mp4 at post.content.media_urls;
  ffmpeg streams that URL directly -> 16k mono wav -> faster-whisper (GPU if available).
  CDN URLs EXPIRE (hours-to-days): transcribe the same day as the pull, else re-pull first.

Parallel ffmpeg prefetch (6 workers) feeds a single transcribe loop. Resume-safe:
skips creators whose transcript file already exists.

Reads:   <project_dir>/source/reels-full.json            (client)
         <project_dir>/source/competitors/reels/*.json   (competitors)
Writes:  <project_dir>/source/client-transcripts.json
         <project_dir>/source/competitors/transcripts/<handle>.json
         <project_dir>/_transcribe_progress.txt          (tail-able progress log)

Output per reel: {rank: top|bottom|all, url, views, text, segments:[{s,e,text}], duration}
Segments (timestamps) are REQUIRED downstream — never strip them.
"""
import json, glob, os, subprocess, tempfile, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

if len(sys.argv) < 2:
    print("Usage: python transcribe_reels.py <project_dir> [top_n] [bottom_n]"); sys.exit(1)
RUN = os.path.abspath(sys.argv[1])
TOP_N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
BOT_N = int(sys.argv[3]) if len(sys.argv) > 3 else 10

COMP_REELS = os.path.join(RUN, "source", "competitors", "reels")
TDIR = os.path.join(RUN, "source", "competitors", "transcripts")
os.makedirs(TDIR, exist_ok=True)
LOG = os.path.join(RUN, "_transcribe_progress.txt")
TMP = tempfile.mkdtemp(prefix="sse_tx_")
MODEL_SIZE = "small"

def log(m):
    with open(LOG, "a", encoding="utf-8") as f: f.write(m + "\n")

def select(reels):
    rv = sorted(reels, key=lambda r: (r.get("post", {}).get("engagement", {}).get("views") or 0), reverse=True)
    if len(rv) <= TOP_N + BOT_N:
        return [("all", r) for r in rv]
    return [("top", r) for r in rv[:TOP_N]] + [("bottom", r) for r in rv[-BOT_N:]]

def meta_of(rank, r):
    p = r.get("post", {})
    return {"rank": rank, "url": p.get("url"),
            "views": p.get("engagement", {}).get("views") or 0,
            "media": p.get("content", {}).get("media_urls")}

def fetch_wav(idx, meta):
    url = meta.get("media")
    if not url: return idx, meta, None, "no_media_url"
    wav = os.path.join(TMP, f"{idx}.wav")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", url, "-vn", "-ar", "16000", "-ac", "1", wav],
                       capture_output=True, timeout=90)
        if os.path.exists(wav) and os.path.getsize(wav) > 1000:
            return idx, meta, wav, None
        return idx, meta, None, "ffmpeg_empty"   # on an old pull this = EXPIRED CDN URL -> re-pull
    except Exception as e:
        return idx, meta, None, f"ffmpeg_err:{type(e).__name__}"

from faster_whisper import WhisperModel
try:
    model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16"); dev = "cuda"
except Exception:
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8"); dev = "cpu"
log(f"=== transcribe START · model={MODEL_SIZE} dev={dev} top={TOP_N} bottom={BOT_N} ===")

def transcribe(wav):
    segs, info = model.transcribe(wav, language="en", vad_filter=True)
    seg_list = [{"s": round(s.start, 2), "e": round(s.end, 2), "text": s.text.strip()} for s in segs]
    return " ".join(s["text"] for s in seg_list).strip(), seg_list, round(info.duration, 2)

def do_creator(handle, reels, outpath):
    picks = select(reels)
    results = []; ok = fail = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_wav, i, meta_of(rank, r)): i for i, (rank, r) in enumerate(picks)}
        for fut in as_completed(futs):
            idx, meta, wav, err = fut.result()
            base = {k: meta[k] for k in ("rank", "url", "views")}
            if err:
                results.append({**base, "text": None, "error": err}); fail += 1; continue
            try:
                txt, seg_list, dur = transcribe(wav)
                results.append({**base, "text": txt, "segments": seg_list, "duration": dur}); ok += 1
            except Exception as e:
                results.append({**base, "text": None, "error": f"tx:{e}"}); fail += 1
            finally:
                try: os.remove(wav)
                except Exception: pass
    results.sort(key=lambda x: -x["views"])
    json.dump({"handle": handle, "n": len(results), "ok": ok, "fail": fail, "reels": results},
              open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return ok, fail

# client first
cpath = os.path.join(RUN, "source", "client-transcripts.json")
cfg = {}
for name in ("analysis-config.json", "tiers.json"):
    p = os.path.join(RUN, name)
    if os.path.exists(p): cfg = json.load(open(p, encoding="utf-8")); break
client_handle = cfg.get("client", "client")
if not os.path.exists(cpath):
    c = json.load(open(os.path.join(RUN, "source", "reels-full.json"), encoding="utf-8"))
    o, f = do_creator(client_handle, c.get("reels", c.get("items", [])), cpath)
    log(f"[client] {client_handle}: ok={o} fail={f}")
else:
    log("[client] skip (exists)")

files = sorted(glob.glob(os.path.join(COMP_REELS, "*.json")))
for i, fpath in enumerate(files, 1):
    handle = os.path.basename(fpath)[:-5]
    outpath = os.path.join(TDIR, f"{handle}.json")
    if os.path.exists(outpath):
        log(f"[{i}/{len(files)}] {handle}: SKIP (exists)"); continue
    reels = json.load(open(fpath, encoding="utf-8")).get("reels", [])
    t0 = time.time()
    o, f = do_creator(handle, reels, outpath)
    log(f"[{i}/{len(files)}] {handle}: ok={o} fail={f} ({time.time()-t0:.0f}s)")

log("=== transcribe DONE ===")
print("done")
