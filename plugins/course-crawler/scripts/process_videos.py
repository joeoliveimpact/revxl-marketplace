"""
process_videos.py ... download videos, extract slides, and produce transcripts.

Reads the v0.3 clean layout (NOT the old per-lesson written/*.json):
  - metadata/lesson_urls.json   the lesson manifest (module/title/post_id)
  - metadata/video_sources.json the videos found per lesson (joined by post_id)

Modes:
  (default)            download video -> slides -> transcript per lesson
  --transcripts-only   FAST: pull native captions (yt-dlp auto-subs, e.g.
                       YouTube) -> transcripts/<module>/<lesson>.md. No video
                       download, no Whisper. Best for "I just want transcripts
                       for a knowledge base".

Transcript fallback chain (default mode): native subs -> Groq Whisper (if
GROQ_API_KEY) -> local faster-whisper. In --transcripts-only, native subs only
(a lesson with no captions is reported, not Whispered, unless --allow-whisper).

Output:
  transcripts/<NN-module>/<lesson>.md     plain transcript (Markdown)
  transcripts/<NN-module>/<lesson>.srt    timestamps (when available)
  video/<NN-module>/<lesson>/video.mp4    (default mode only)
  visual/<NN-module>/<lesson>/            slide frames (default mode only)
  metadata/video_report.json              per-lesson status

How to run:
  python ${CLAUDE_SKILL_DIR}/../scripts/process_videos.py ./scraped/<slug> --transcripts-only
  python ${CLAUDE_SKILL_DIR}/../scripts/process_videos.py ./scraped/<slug>            # full
  ... --limit 3            test on first 3 lessons
  ... --skip-existing      resume (skip lessons that already have a transcript)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Shared lesson-path helpers so process_videos writes into the SAME
# <course>/NN-module/NN-lesson/ folder scrape_course created.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_course import lesson_dir_for, lesson_slug_for  # noqa: E402,F401


# Windows consoles default to cp1252; force UTF-8 so emoji/arrows in lesson
# titles never crash a print(). No-op where already UTF-8 or not reconfigurable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def find_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        for extra in ("/opt/homebrew/bin", "/opt/homebrew/sbin"):
            candidate = os.path.join(extra, name)
            if os.path.exists(candidate):
                return candidate
        raise FileNotFoundError(f"Required tool not found on PATH: {name}")
    return path


def slugify(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\-]+", "-", (text or "").lower()).strip("-")
    return s[:max_len] or "untitled"


def download_video(yt_dlp: str, video_url: str, dest_dir: Path,
                   cookies_file: Path | None) -> Path | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / "video.mp4"
    if out_path.exists():
        return out_path
    cmd = [yt_dlp, "--no-playlist", "--quiet", "--no-warnings", "--progress",
           "-o", str(out_path), "--merge-output-format", "mp4"]
    if cookies_file and cookies_file.exists():
        cmd += ["--cookies", str(cookies_file)]
    cmd.append(video_url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        sys.stderr.write(f"yt-dlp failed for {video_url}\n{result.stderr}\n")
        return None
    return out_path


def try_native_subtitles(yt_dlp: str, video_url: str, dest_dir: Path,
                        cookies_file: Path | None) -> Path | None:
    """Download native/auto subtitles as .srt. Returns the .srt path or None."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(dest_dir / "captions.%(ext)s")
    cmd = [yt_dlp, "--skip-download", "--write-auto-subs", "--write-subs",
           "--sub-langs", "en.*,en", "--sub-format", "srt/vtt/best",
           "--convert-subs", "srt", "--quiet", "--no-warnings",
           "-o", out_template]
    if cookies_file and cookies_file.exists():
        cmd += ["--cookies", str(cookies_file)]
    cmd.append(video_url)
    subprocess.run(cmd, capture_output=True, text=True)
    srt_files = sorted(dest_dir.glob("captions*.srt"))
    return srt_files[0] if srt_files else None


# --- slide-extraction helpers (OCR-gated; see plan go-majestic-reddy) -------

def _hamming(a: int, b: int) -> int:
    """Bit-difference count between two perceptual hashes."""
    return bin(a ^ b).count("1")


def _dhash(path, hash_size: int = 8) -> int:
    """64-bit difference hash: grayscale, resize to (n+1)x n, compare
    horizontally adjacent pixels. Near-identical frames hash within a few bits."""
    from PIL import Image
    img = Image.open(path).convert("L").resize(
        (hash_size + 1, hash_size), Image.LANCZOS)
    px = list(img.getdata())
    w = hash_size + 1
    bits = 0
    for row in range(hash_size):
        for col in range(hash_size):
            bits = (bits << 1) | (1 if px[row * w + col] > px[row * w + col + 1] else 0)
    return bits


def _sharpness(path) -> float:
    """Variance of the discrete Laplacian (numpy slicing, no scipy). Higher =
    sharper; motion-blurred / fade frames score low."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    lap = (-4.0 * a[1:-1, 1:-1]
           + a[:-2, 1:-1] + a[2:, 1:-1]
           + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.var())


def _resolve_tesseract(cfg: dict):
    """Locate the Tesseract binary. Order: cfg flag -> PATH -> known install
    locations. The UB-Mannheim Windows installer does NOT add itself to PATH,
    so the explicit Program Files path is essential. Returns path or None."""
    candidates = []
    if cfg.get("tesseract_cmd"):
        candidates.append(cfg["tesseract_cmd"])
    which = shutil.which("tesseract")
    if which:
        candidates.append(which)
    candidates += [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract",
        "/usr/bin/tesseract",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def _ocr_score(path, tesseract_cmd) -> tuple[int, int, str]:
    """OCR a frame; return (word_count, char_count, text[:240]) counting only
    tokens at confidence >= 40. Slides/UI are text-dense; talking-head isn't."""
    import pytesseract
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    data = pytesseract.image_to_data(str(path), config="--psm 6",
                                     output_type=pytesseract.Output.DICT)
    words = []
    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
        t = (txt or "").strip()
        try:
            c = float(conf)
        except (TypeError, ValueError):
            c = -1.0
        if t and c >= 40:
            words.append(t)
    joined = " ".join(words)
    return len(words), len(joined), joined[:240]


def _extract_slides_scenedetect(ffmpeg: str, video_path: Path,
                                slides_dir: Path, threshold: float) -> int:
    """Legacy ffmpeg scene-detect path. Fallback when OCR is unavailable."""
    slides_dir.mkdir(parents=True, exist_ok=True)
    for f in slides_dir.glob("slide-*.jpg"):
        f.unlink()
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(video_path),
           "-vf", f"select='gt(scene,{threshold})',format=yuvj420p,scale=trunc(iw/2)*2:trunc(ih/2)*2",
           "-fps_mode", "vfr", "-qscale:v", "3",
           str(slides_dir / "slide-%03d.jpg")]
    subprocess.run(cmd, check=False)
    return len(list(slides_dir.glob("slide-*.jpg")))


def extract_slides(ffmpeg: str, video_path: Path, slides_dir: Path,
                  threshold: float, cfg: dict | None = None) -> int:
    """OCR-gated slide extraction. Steady-sample -> perceptual-hash dedupe ->
    sharpest-frame pick -> blur floor -> OCR text-density gate -> global
    dedupe. Emits slide-NNN.jpg + slides.json (timestamp + OCR text index).
    Falls back to legacy scene-detect if Tesseract is unavailable."""
    cfg = cfg or {}
    slides_dir.mkdir(parents=True, exist_ok=True)
    for f in slides_dir.glob("slide-*.jpg"):
        f.unlink()
    (slides_dir / "slides.json").unlink(missing_ok=True)

    tcmd = _resolve_tesseract(cfg)
    try:
        import pytesseract  # noqa: F401
        ocr_ok = tcmd is not None
    except Exception:
        ocr_ok = False
    if not ocr_ok:
        print("      [slides] OCR unavailable -> scene-detect fallback")
        return _extract_slides_scenedetect(ffmpeg, video_path,
                                           slides_dir, threshold)

    fps = float(cfg.get("fps", 1.0))
    phash_dist = int(cfg.get("phash_dist", 6))
    blur_min = float(cfg.get("blur_min", 60.0))
    min_words = int(cfg.get("min_words", 4))
    min_chars = int(cfg.get("min_chars", 24))

    work = Path(tempfile.mkdtemp(prefix="slides_"))
    try:
        subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(video_path),
             "-vf", f"fps={fps},scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-qscale:v", "3", str(work / "f-%05d.jpg")],
            check=False)
        frames = sorted(work.glob("f-*.jpg"))
        if not frames:
            return 0

        # 1. group consecutive near-identical frames (a slide held on screen)
        runs, cur = [], [frames[0]]
        prev_h = _dhash(frames[0])
        for fr in frames[1:]:
            h = _dhash(fr)
            if _hamming(h, prev_h) <= phash_dist:
                cur.append(fr)
            else:
                runs.append(cur)
                cur = [fr]
            prev_h = h
        runs.append(cur)

        # 2. per run: sharpest frame; drop runs that never get sharp
        reps = []
        for run in runs:
            best = max(run, key=_sharpness)
            if _sharpness(best) >= blur_min:
                reps.append((best, frames.index(best)))

        # 3. OCR content gate (excludes talking-head / no-content)
        kept = []
        for fr, idx0 in reps:
            w, ch, txt = _ocr_score(fr, tcmd)
            if w >= min_words and ch >= min_chars:
                kept.append((fr, idx0, txt))

        # 4. global dedupe (recaps / repeated slides later in the video)
        out, seen = [], []
        for fr, idx0, txt in kept:
            h = _dhash(fr)
            if any(_hamming(h, s) <= phash_dist for s in seen):
                continue
            seen.append(h)
            out.append((fr, idx0, txt))

        # 5. write ordered jpgs + timestamped/text-indexed sidecar
        manifest = []
        for n, (fr, idx0, txt) in enumerate(out, start=1):
            dest = slides_dir / f"slide-{n:03d}.jpg"
            shutil.copyfile(fr, dest)
            manifest.append({"file": dest.name,
                             "t": round(idx0 / fps, 1),
                             "text": txt})
        (slides_dir / "slides.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8")
        return len(out)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def ts(seconds: float) -> str:
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = seconds % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def _load_key(var: str) -> str | None:
    """Read an API key from env or ~/.iss/.env / ~/.config/watch/.env."""
    if os.environ.get(var):
        return os.environ[var]
    for env_file in [Path.home() / ".iss" / ".env",
                     Path.home() / ".config" / "watch" / ".env"]:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith(var + "="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val or None
    return None


def load_groq_key() -> str | None:
    return _load_key("GROQ_API_KEY")


def load_openai_key() -> str | None:
    return _load_key("OPENAI_API_KEY")


def extract_audio_for_api(ffmpeg: str, video_path: Path, dest_dir: Path) -> Path:
    audio_path = dest_dir / "_audio.mp3"
    if audio_path.exists():
        return audio_path
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(video_path), "-vn", "-ar", "16000", "-ac", "1",
                    "-b:a", "32k", str(audio_path)], check=True)
    return audio_path


def _transcribe_api(ffmpeg: str, video_path: Path, dest_dir: Path,
                    api_key: str, url: str, model: str,
                    label: str) -> tuple[Path, Path]:
    """POST extracted audio to an OpenAI-compatible /audio/transcriptions
    endpoint (Groq or OpenAI). Retries on 429/5xx with backoff."""
    import httpx
    audio_path = extract_audio_for_api(ffmpeg, video_path, dest_dir)
    txt_path = dest_dir / "transcript.txt"
    srt_path = dest_dir / "transcript.srt"
    for attempt in range(1, 7):
        with audio_path.open("rb") as f:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio_path.name, f, "audio/mpeg")},
                data={"model": model, "response_format": "verbose_json"},
                timeout=600.0)
        if resp.status_code < 400:
            break
        if resp.status_code == 429 or resp.status_code >= 500:
            ra = resp.headers.get("retry-after")
            try:
                wait = float(ra) if ra else min(60.0, 2 ** attempt)
            except ValueError:
                wait = min(60.0, 2 ** attempt)
            print(f"      {label} {resp.status_code} (attempt {attempt}/6); sleeping {wait:.1f}s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
    else:
        resp.raise_for_status()
    data = resp.json()
    segments = data.get("segments") or []
    with txt_path.open("w", encoding="utf-8") as t, srt_path.open("w", encoding="utf-8") as s:
        if segments:
            for i, seg in enumerate(segments, start=1):
                text = seg["text"].strip()
                t.write(text + "\n")
                s.write(f"{i}\n{ts(seg['start'])} --> {ts(seg['end'])}\n{text}\n\n")
        else:
            t.write((data.get("text") or "").strip() + "\n")
    try:
        audio_path.unlink()
    except FileNotFoundError:
        pass
    return srt_path, txt_path


def transcribe_groq(ffmpeg: str, video_path: Path, dest_dir: Path, api_key: str) -> tuple[Path, Path]:
    return _transcribe_api(ffmpeg, video_path, dest_dir, api_key,
                           "https://api.groq.com/openai/v1/audio/transcriptions",
                           "whisper-large-v3-turbo", "Groq")


def transcribe_openai(ffmpeg: str, video_path: Path, dest_dir: Path, api_key: str) -> tuple[Path, Path]:
    return _transcribe_api(ffmpeg, video_path, dest_dir, api_key,
                           "https://api.openai.com/v1/audio/transcriptions",
                           "whisper-1", "OpenAI")


def local_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def _whisper_device() -> tuple[str, str]:
    """Use the NVIDIA GPU if CTranslate2 can see one (much faster), else CPU."""
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def _whisper_worker(video_path: str, dest_dir: str, model_name: str,
                    device: str, compute_type: str) -> None:
    """Disposable subprocess entrypoint for local faster-whisper.

    Root cause this exists for: on Windows/Python 3.13, ctranslate2's CUDA
    model destructor calls abort() (0xC0000409 STATUS_STACK_BUFFER_OVERRUN) at
    interpreter finalization (and on GC). In a long batch that native abort is
    uncatchable and kills EVERY remaining lesson. We do the transcription, write
    transcript.txt/.srt, fsync, then os._exit(0) so Python finalization (and the
    buggy CUDA destructor) never runs. Bonus: a native crash in here cannot take
    down the parent batch -- the caller just sees missing output and moves on."""
    from faster_whisper import WhisperModel
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    txt_path = dest / "transcript.txt"
    srt_path = dest / "transcript.srt"
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(video_path, beam_size=5)
    with txt_path.open("w", encoding="utf-8") as t, srt_path.open("w", encoding="utf-8") as s:
        for i, seg in enumerate(segments, start=1):
            t.write(seg.text.strip() + "\n")
            s.write(f"{i}\n{ts(seg.start)} --> {ts(seg.end)}\n{seg.text.strip()}\n\n")
        t.flush(); s.flush()
        os.fsync(t.fileno()); os.fsync(s.fileno())
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0)


def transcribe_local(video_path: Path, dest_dir: Path, model_name: str) -> tuple[Path, Path]:
    """Transcribe via local faster-whisper in a DISPOSABLE child process.

    See _whisper_worker for why: ctranslate2's CUDA teardown abort()s and would
    kill the whole batch. Isolating each transcription in a short-lived process
    that os._exit(0)s after writing output avoids the destructor entirely and
    contains any native crash to a single lesson."""
    txt_path = dest_dir / "transcript.txt"
    srt_path = dest_dir / "transcript.srt"
    device, compute_type = _whisper_device()
    print(f"      local faster-whisper ({model_name}) on {device}"
          f"{' (GPU, isolated subprocess)' if device == 'cuda' else ''}...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    for p in (txt_path, srt_path):
        p.unlink(missing_ok=True)
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--__whisper_worker",
         str(video_path), str(dest_dir), model_name, device, compute_type],
        capture_output=True, text=True)
    if not (srt_path.exists() and txt_path.exists()):
        raise RuntimeError(
            f"local whisper subprocess failed (exit {proc.returncode}); "
            f"stderr tail: {(proc.stderr or '')[-400:]}")
    return srt_path, txt_path


def srt_to_text(srt_path: Path) -> str:
    """Flatten an .srt into clean readable prose: drop indices/timestamps and
    caption filler ([music], [applause], ...), de-dupe YouTube's rolling
    repeats, then reflow the hard-wrapped fragments into sentences and
    paragraphs so it's usable as knowledge-base material."""
    frags = []
    for block in srt_path.read_text(encoding="utf-8").split("\n\n"):
        for l in block.splitlines():
            s = l.strip()
            if not s or s.isdigit() or "-->" in s:
                continue
            frags.append(s)
    # Drop bracketed/parenthetical caption cues like [Music], (applause).
    cleaned = []
    for f in frags:
        f = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", f).strip()
        if f:
            cleaned.append(f)
    # De-dupe consecutive identical fragments (rolling captions).
    dd, prev = [], None
    for f in cleaned:
        if f != prev:
            dd.append(f)
        prev = f
    # Join all fragments, normalize whitespace.
    blob = re.sub(r"\s+", " ", " ".join(dd)).strip()
    # Sentence-split, then group ~4 sentences per paragraph.
    sentences = re.findall(r"[^.!?]+[.!?]+|\S[^.!?]*$", blob)
    paras, buf = [], []
    for s in sentences:
        buf.append(s.strip())
        if len(buf) >= 4:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(p for p in paras if p) + "\n"


def process_one_lesson(yt_dlp: str, ffmpeg: str, lesson_meta: dict,
                       course_dir: Path, scene_threshold: float,
                       whisper_model: str, cookies_file: Path | None,
                       skip_existing: bool, groq_key: str | None,
                       openai_key: str | None, whisper_sel: str,
                       transcripts_only: bool, allow_whisper: bool,
                       slides_mode: bool,
                       slide_cfg: dict | None = None) -> dict:
    videos = lesson_meta.get("videos", [])
    if not videos:
        return {"post_id": lesson_meta.get("post_id"),
                "title": lesson_meta.get("title"), "status": "no_video"}

    title = lesson_meta.get("title") or lesson_meta.get("post_id")
    # SAME lesson folder scrape_course used (holds <lesson>.md + downloads/).
    ldir = lesson_dir_for(course_dir, lesson_meta)
    work = ldir / ".work"          # temp: video + caption working files
    md_path = ldir / "transcript.md"
    srt_dest = ldir / "transcript.srt"

    primary = next((v for v in videos if not v.get("drm_protected")), None)
    if primary is None:
        return {"post_id": lesson_meta.get("post_id"), "title": title,
                "status": "drm_locked",
                "note": videos[0].get("note", "DRM-protected; manual capture only")}

    if skip_existing and md_path.exists():
        return {"post_id": lesson_meta.get("post_id"), "title": title,
                "status": "skipped_existing"}

    ldir.mkdir(parents=True, exist_ok=True)

    def _clean_work():
        shutil.rmtree(work, ignore_errors=True)

    # --- transcripts-only: native captions, no download, no Whisper ---------
    if transcripts_only and not slides_mode:
        srt = try_native_subtitles(yt_dlp, primary["url"], work, cookies_file)
        if srt:
            shutil.move(str(srt), str(srt_dest))
            md_path.write_text(f"# {title}\n\n{srt_to_text(srt_dest)}",
                               encoding="utf-8")
            _clean_work()
            return {"post_id": lesson_meta.get("post_id"), "title": title,
                    "status": "ok", "transcript_source": "native",
                    "transcript_md": str(md_path)}
        _clean_work()
        if not allow_whisper:
            return {"post_id": lesson_meta.get("post_id"), "title": title,
                    "status": "no_captions",
                    "note": "No native captions. Re-run without "
                            "--transcripts-only (or add --allow-whisper) to "
                            "transcribe the audio."}
        # else fall through to download + whisper

    # --- download -> slides -> transcript (into the lesson folder) ----------
    video_path = download_video(yt_dlp, primary["url"], work, cookies_file)
    if not video_path:
        _clean_work()
        return {"post_id": lesson_meta.get("post_id"), "title": title,
                "status": "download_failed", "video_url": primary["url"]}

    n_slides = 0
    if (not transcripts_only) or slides_mode:
        n_slides = extract_slides(ffmpeg, video_path, ldir / "slides",
                                  scene_threshold, slide_cfg)

    srt = try_native_subtitles(yt_dlp, primary["url"], work, cookies_file)
    if srt:
        shutil.move(str(srt), str(srt_dest))
        md_path.write_text(f"# {title}\n\n{srt_to_text(srt_dest)}",
                           encoding="utf-8")
        source = "native"
    else:
        # No native captions -> transcribe. Default is LOCAL FIRST (GPU when
        # available), with API as fallback. whisper_sel can force/reorder.
        order = {
            "auto":   ["local", "groq", "openai"],
            "local":  ["local"],
            "groq":   ["groq", "local"],
            "openai": ["openai", "local"],
        }.get(whisper_sel, ["local", "groq", "openai"])
        source = None
        for backend in order:
            try:
                if backend == "local" and local_whisper_available():
                    s_srt, s_txt = transcribe_local(video_path, work, whisper_model)
                    source = "whisper_local"
                elif backend == "groq" and groq_key:
                    print("      transcribing via Groq Whisper-large-v3-turbo...")
                    s_srt, s_txt = transcribe_groq(ffmpeg, video_path, work, groq_key)
                    source = "groq"
                elif backend == "openai" and openai_key:
                    print("      transcribing via OpenAI whisper-1...")
                    s_srt, s_txt = transcribe_openai(ffmpeg, video_path, work, openai_key)
                    source = "openai"
                else:
                    continue
                shutil.move(str(s_srt), str(srt_dest))
                md_path.write_text(
                    f"# {title}\n\n{s_txt.read_text(encoding='utf-8')}",
                    encoding="utf-8")
                s_txt.unlink(missing_ok=True)
                break
            except Exception as e:
                print(f"      {backend} failed: {e}")
                source = None
        if source is None:
            _clean_work()
            return {"post_id": lesson_meta.get("post_id"), "title": title,
                    "status": "no_transcription",
                    "note": "No native captions and no working Whisper backend. "
                            "Install faster-whisper in the venv, or set a "
                            "Groq/OpenAI key in ~/.iss/.env."}

    # Keep video.mp4 in the lesson folder only in pure default mode.
    # --slides / --transcripts-only discard it (no multi-GB bloat). The lesson
    # folder itself is NEVER deleted (it holds <lesson>.md + downloads/).
    video_bytes = video_path.stat().st_size if video_path.exists() else 0
    if not (transcripts_only or slides_mode):
        shutil.move(str(video_path), str(ldir / "video.mp4"))
    _clean_work()

    return {"post_id": lesson_meta.get("post_id"), "title": title,
            "status": "ok", "transcript_source": source,
            "transcript_md": str(md_path),
            "slides": n_slides,
            "video_bytes": 0 if (transcripts_only or slides_mode) else video_bytes}


def collect_lessons(course_dir: Path) -> list[dict]:
    """Build the lesson list from the v0.3 layout: lesson_urls.json joined with
    video_sources.json by post_id."""
    meta = course_dir / "metadata"
    manifest = json.loads((meta / "lesson_urls.json").read_text(encoding="utf-8"))
    by_pid: dict = {}
    vsf = meta / "video_sources.json"
    if vsf.exists():
        for v in json.loads(vsf.read_text(encoding="utf-8")):
            by_pid.setdefault(v.get("post_id"), []).append(v)
    # Ensure lesson_order (older manifests lack it) using manifest position
    # within each module ... identical logic to scrape_course, so both compute
    # the same NN-lesson folder.
    ctr: dict = {}
    lessons = []
    for l in manifest:
        mo = l.get("module_order", 1)
        ctr[mo] = ctr.get(mo, 0) + 1
        l.setdefault("lesson_order", ctr[mo])
        lessons.append({**l, "videos": by_pid.get(l.get("post_id"), [])})
    lessons.sort(key=lambda l: (l.get("module_order", 99),
                                l.get("lesson_order", 99)))
    return lessons


def main() -> int:
    parser = argparse.ArgumentParser(description="Videos -> slides + transcripts.")
    parser.add_argument("course_dir", help="Scraped course folder")
    parser.add_argument("--transcripts-only", action="store_true",
                        help="Fast path: native captions only, no download/Whisper")
    parser.add_argument("--slides", action="store_true",
                        help="Download each video, extract scene-detect slide "
                             "frames + transcript, then DELETE the video. Keeps "
                             "slides (visual/) + transcript only ... helpful "
                             "visuals, no multi-GB bloat.")
    parser.add_argument("--allow-whisper", action="store_true",
                        help="In --transcripts-only, fall back to Whisper when "
                             "a lesson has no native captions")
    parser.add_argument("--scene-threshold", type=float, default=0.3)
    # OCR-gated slide extraction tuning (see extract_slides)
    parser.add_argument("--slide-fps", type=float, default=1.0,
                        help="Frames/sec sampled for slide detection")
    parser.add_argument("--slide-phash-dist", type=int, default=6,
                        help="Max dHash Hamming distance treated as same slide")
    parser.add_argument("--slide-blur-min", type=float, default=60.0,
                        help="Min Laplacian-variance sharpness to keep a frame")
    parser.add_argument("--slide-min-words", type=int, default=4,
                        help="Min OCR words for a frame to count as a slide")
    parser.add_argument("--slide-min-chars", type=int, default=24,
                        help="Min OCR characters for a frame to count as a slide")
    parser.add_argument("--slide-tesseract-cmd", default=None,
                        help="Explicit path to the tesseract binary "
                             "(else PATH / known install locations)")
    parser.add_argument("--whisper-model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip lessons that already have a transcript")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--whisper", choices=["auto", "groq", "openai", "local"],
                        default="auto",
                        help="Transcription backend when there are no native "
                             "captions. auto = Groq -> OpenAI -> local "
                             "faster-whisper, by whichever key/lib is available.")
    parser.add_argument("--no-groq", action="store_true",
                        help="(legacy) same as --whisper openai/local")
    args = parser.parse_args()

    course_dir = Path(args.course_dir).expanduser().resolve()
    # Windows MAX_PATH (260) fix: extended-length prefix so deep
    # transcript/slide/video paths (long lesson titles) can be written.
    if sys.platform == "win32" and not str(course_dir).startswith("\\\\?\\"):
        course_dir = Path("\\\\?\\" + str(course_dir))
    if not (course_dir / "metadata" / "lesson_urls.json").exists():
        print(f"Error: {course_dir}/metadata/lesson_urls.json not found. "
              f"Run discovery + scrape_course.py first.", file=sys.stderr)
        return 1

    yt_dlp = find_executable("yt-dlp")
    need_ffmpeg = (not args.transcripts_only) or args.slides
    ffmpeg = find_executable("ffmpeg") if need_ffmpeg else \
        (shutil.which("ffmpeg") or "ffmpeg")
    cookies_file = course_dir / "metadata" / "cookies.txt"
    # Keys are loaded as fallbacks; the LOCAL-first order is decided per-lesson
    # by whisper_sel (default "auto" = local -> groq -> openai). --no-groq is
    # legacy: just drop the Groq key from the fallback set.
    groq_key = None if args.no_groq else load_groq_key()
    openai_key = load_openai_key()

    lessons = collect_lessons(course_dir)
    if args.limit:
        lessons = lessons[:args.limit]
    n_with_video = sum(1 for l in lessons if l.get("videos"))

    if args.slides:
        mode = "slides + transcript (video discarded after)"
    elif args.transcripts_only:
        mode = "transcripts-only (native captions)"
    else:
        dev, _ = _whisper_device()
        if args.whisper in ("auto", "local") and local_whisper_available():
            mode = f"local faster-whisper ({args.whisper_model}, {dev})"
        elif args.whisper == "groq" or (args.whisper == "auto" and groq_key):
            mode = "Groq Whisper"
        elif args.whisper == "openai" or (args.whisper == "auto" and openai_key):
            mode = "OpenAI Whisper"
        else:
            mode = f"local faster-whisper ({args.whisper_model}, {dev})"
    print(f"{len(lessons)} lessons ({n_with_video} with video) | mode: {mode}")
    print(f"  yt-dlp: {yt_dlp}\n")

    slide_cfg = {
        "fps": args.slide_fps,
        "phash_dist": args.slide_phash_dist,
        "blur_min": args.slide_blur_min,
        "min_words": args.slide_min_words,
        "min_chars": args.slide_min_chars,
        "tesseract_cmd": args.slide_tesseract_cmd,
    }

    report = []
    start = time.time()
    for i, lesson in enumerate(lessons, start=1):
        title = lesson.get("title") or lesson.get("post_id")
        print(f"  [{i:>3}/{len(lessons)}] {title}")
        r = process_one_lesson(
            yt_dlp, ffmpeg, lesson, course_dir, args.scene_threshold,
            args.whisper_model, cookies_file, args.skip_existing, groq_key,
            openai_key, args.whisper, args.transcripts_only,
            args.allow_whisper, args.slides, slide_cfg)
        report.append(r)
        st = r.get("status")
        if st == "ok":
            print(f"        ok | transcript via {r.get('transcript_source')}")
        else:
            print(f"        {st}{(' - ' + r['note']) if r.get('note') else ''}")

    elapsed = time.time() - start
    ok = sum(1 for r in report if r.get("status") == "ok")
    skipped = sum(1 for r in report if r.get("status") == "skipped_existing")
    novideo = sum(1 for r in report if r.get("status") == "no_video")
    # A hard failure is a download/transcription error -- NOT "nothing new to
    # do" (everything already transcribed or genuinely video-less).
    hard_fail = sum(1 for r in report if r.get("status")
                    in ("download_failed", "error"))
    (course_dir / "metadata" / "video_report.json").write_text(
        json.dumps({"run_seconds": round(elapsed, 1),
                    "mode": mode, "ok": ok, "total": len(report),
                    "report": report}, indent=2, default=str,
                   ensure_ascii=False),
        encoding="utf-8")
    print()
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s ... {ok} new, {skipped} already done, "
          f"{novideo} no-video, {hard_fail} failed (of {len(report)})")
    print(f"  Course tree: {course_dir}  (per lesson: transcript.md"
          f"{', slides/' if (args.slides or not args.transcripts_only) else ''}"
          f"{', video.mp4' if not (args.slides or args.transcripts_only) else ''})")
    print(f"  Report:      {course_dir / 'metadata' / 'video_report.json'}")
    # Success unless something actually broke. "Nothing to do" is success.
    return 2 if hard_fail else 0


if __name__ == "__main__":
    if len(sys.argv) >= 7 and sys.argv[1] == "--__whisper_worker":
        # Disposable GPU-whisper child (see _whisper_worker). Never returns.
        _whisper_worker(sys.argv[2], sys.argv[3], sys.argv[4],
                        sys.argv[5], sys.argv[6])
    sys.exit(main())
