"""
youtube_pull.py ... capture YouTube content (single video, playlist, or channel).

What this does (plain English):
  You give it a YouTube URL and tell it what you want. It hands the URL to
  yt-dlp to enumerate the videos, then for each one pulls whatever subset the
  caller asked for: transcripts, slide frames, video files, descriptions.

What it expects:
  - yt-dlp and ffmpeg on PATH.
  - For private/age-restricted content: a cookies.txt file from /login.

What it produces (depending on --want flags):
  ./<out>/written/<video-id>/description.md
  ./<out>/written/<video-id>/chapters.json
  ./<out>/visual/<video-id>/slides/slide-NNN.jpg
  ./<out>/video/<video-id>/video.mp4
  ./<out>/video/<video-id>/transcript.srt
  ./<out>/video/<video-id>/transcript.txt
  ./<out>/metadata/playlist_manifest.json
  ./<out>/metadata/youtube_report.json

How to run:
  python youtube_pull.py "<url>" --out ./scraped/my-topic --want transcript,slides

Why this exists:
  YouTube has its own quirks ... native captions, playlist enumeration, age
  gating, channel pagination. A dedicated script handles all of that
  cleanly, with a one-flag knob for the user's actual deliverable.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

WANT_OPTIONS = {"transcript", "slides", "video", "description"}

# Windows consoles default to cp1252; force UTF-8 so non-ASCII never crashes
# a print(). No-op where already UTF-8 or not reconfigurable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def find_exe(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    for extra in ("/opt/homebrew/bin", "/opt/homebrew/sbin"):
        c = os.path.join(extra, name)
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"Required tool not on PATH: {name}")


def parse_want(s: str) -> set[str]:
    items = {x.strip() for x in s.split(",") if x.strip()}
    unknown = items - WANT_OPTIONS
    if unknown:
        raise SystemExit(f"Unknown --want options: {unknown}. Allowed: {WANT_OPTIONS}")
    return items


def enumerate_videos(yt_dlp: str, url: str, cookies: Path | None) -> list[dict]:
    """yt-dlp --flat-playlist gives a quick list of every video in a playlist/channel
    without downloading anything. Returns dicts with id, title, duration, url."""
    cmd = [yt_dlp, "--flat-playlist", "--dump-single-json", "--no-warnings"]
    if cookies and cookies.exists():
        cmd += ["--cookies", str(cookies)]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"yt-dlp failed to enumerate: {result.stderr}")
    data = json.loads(result.stdout)
    entries = data.get("entries") or [data]
    out = []
    for e in entries:
        if not e.get("id"):
            continue
        vid = e["id"]
        out.append({
            "id": vid,
            "title": e.get("title") or vid,
            "duration": e.get("duration") or 0,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "channel": e.get("channel"),
            "channel_id": e.get("channel_id"),
        })
    return out


def slugify(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\-]+", "-", (text or "").lower()).strip("-")
    return s[:max_len] or "untitled"


def download_video(yt_dlp: str, url: str, dest: Path, cookies: Path | None) -> Path | None:
    dest.mkdir(parents=True, exist_ok=True)
    out_path = dest / "video.mp4"
    if out_path.exists():
        return out_path
    cmd = [yt_dlp, "--no-playlist", "--quiet", "--no-warnings",
           "-o", str(out_path), "--merge-output-format", "mp4"]
    if cookies and cookies.exists():
        cmd += ["--cookies", str(cookies)]
    cmd.append(url)
    subprocess.run(cmd, check=False)
    return out_path if out_path.exists() else None


def get_native_subs(yt_dlp: str, url: str, dest: Path, cookies: Path | None) -> Path | None:
    template = str(dest / "captions.%(ext)s")
    cmd = [yt_dlp, "--skip-download", "--write-subs", "--write-auto-subs",
           "--sub-format", "srt/vtt/best", "--convert-subs", "srt",
           "--quiet", "--no-warnings", "-o", template]
    if cookies and cookies.exists():
        cmd += ["--cookies", str(cookies)]
    cmd.append(url)
    subprocess.run(cmd, capture_output=True, text=True)
    srt_files = list(dest.glob("captions*.srt"))
    return srt_files[0] if srt_files else None


def get_description_and_chapters(yt_dlp: str, url: str, dest: Path, cookies: Path | None) -> dict:
    """Pull description + chapter markers via yt-dlp --dump-json (no download)."""
    cmd = [yt_dlp, "--no-playlist", "--dump-json", "--no-warnings", "--skip-download"]
    if cookies and cookies.exists():
        cmd += ["--cookies", str(cookies)]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    info = json.loads(r.stdout)
    dest.mkdir(parents=True, exist_ok=True)
    description = info.get("description") or ""
    (dest / "description.md").write_text(
        f"# {info.get('title','')}\n\n{description}\n", encoding="utf-8")
    chapters = info.get("chapters") or []
    if chapters:
        (dest / "chapters.json").write_text(json.dumps(chapters, indent=2), encoding="utf-8")
    return {"title": info.get("title"), "duration": info.get("duration"),
            "uploader": info.get("uploader"), "upload_date": info.get("upload_date"),
            "chapters_count": len(chapters)}


def extract_slides(ffmpeg: str, video: Path, slides_dir: Path, threshold: float) -> int:
    slides_dir.mkdir(parents=True, exist_ok=True)
    for f in slides_dir.glob("slide-*.jpg"):
        f.unlink()
    subprocess.run([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video),
        "-vf", f"select='gt(scene,{threshold})',format=yuvj420p,scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-fps_mode", "vfr", "-qscale:v", "3",
        str(slides_dir / "slide-%03d.jpg"),
    ], check=False)
    return len(list(slides_dir.glob("slide-*.jpg")))


def srt_to_text(p: Path) -> str:
    out = []
    for block in p.read_text(encoding="utf-8").split("\n\n"):
        lines = [l for l in block.splitlines() if l.strip() and not l.strip().isdigit() and "-->" not in l]
        if lines:
            out.append(" ".join(lines))
    return "\n".join(out) + "\n"


def course_vocab(video: dict) -> "str | None":
    """
    Build the transcription vocabulary prompt for one video.

    Course audio is dense with names Whisper has never seen — the instructor,
    the product being taught, the tools referenced. Unprompted it substitutes the
    nearest common-English phrase ("Kling 01" -> "cling a one") silently, and the
    error then propagates into every downstream note and summary.

    The names are already in hand: yt-dlp gives us the channel and title before we
    transcribe. Phrasing them as a sentence primes the decoder for the right domain
    at no configuration cost.

    Deliberately a natural sentence, not a term list: Whisper imitates the style of
    its prompt, so an unpunctuated list teaches it to emit a transcript with no
    capitals or punctuation at all.

    Measured trade (Groq whisper-large-v3-turbo, real clip): the derived prompt
    recovered "Kling 01" and "Higgsfield Soul" from "uh cling a one higgs field
    soul", and also collapsed a sentence the speaker had said twice. Net -97 chars.
    Correct tool names are worth more than a duplicated sentence in reference
    material, which is why this is on by default here — but it IS lossy, so set
    COURSE_CRAWLER_VOCAB=off when transcribing something you need verbatim.

    COURSE_CRAWLER_VOCAB overrides the derived text; set it to "off" to disable.
    """
    override = os.environ.get("COURSE_CRAWLER_VOCAB", "").strip()
    if override.lower() in ("off", "0", "false", "none"):
        return None
    if override:
        return override

    def clean(v: str, cap: int) -> str:
        # Titles carry emoji, pipes and bracket tags that would only add noise.
        v = re.sub(r"[^\w\s.,'&/+-]", " ", v or "")
        return re.sub(r"\s+", " ", v).strip()[:cap]

    title = clean(video.get("title", ""), 120)
    channel = clean(video.get("channel", ""), 60)
    if channel and title:
        return f"This is a lesson from the channel {channel}, titled {title}."
    if title:
        return f"This is a lesson titled {title}."
    if channel:
        return f"This is a lesson from the channel {channel}."
    return None


def transcribe_groq(ffmpeg: str, video: Path, dest: Path, api_key: str,
                    vocab: str | None = None) -> tuple[Path, Path]:
    """
    `vocab` biases decoding toward spellings you supply — pass the course's product,
    tool and instructor names. Without it Whisper substitutes the nearest common-English
    phrase for anything it has not seen ("Kling 01" -> "cling a one"), silently.

    Write it as a PUNCTUATED SENTENCE, not a bare comma list: Whisper imitates the
    style of its prompt, so an unpunctuated list makes it emit a transcript with no
    capitals or punctuation at all. Groq caps this field at 224 tokens.

    Caveat: a prompt can also cause a speaker's repeated takes to be dropped, since
    Whisper suppresses what looks like a repetition loop. On multi-take source, compare
    the output length against an unprompted run before trusting it.

    Callers normally get this from course_vocab() rather than building it by hand.
    """
    import httpx
    audio = dest / "_audio.mp3"
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(video), "-vn", "-ar", "16000", "-ac", "1", "-b:a", "32k",
                    str(audio)], check=True)
    srt_path = dest / "transcript.srt"
    txt_path = dest / "transcript.txt"
    payload = {"model": "whisper-large-v3-turbo", "response_format": "verbose_json"}
    if vocab:
        payload["prompt"] = vocab
    for attempt in range(1, 7):
        with audio.open("rb") as f:
            r = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio.name, f, "audio/mpeg")},
                data=payload,
                timeout=600.0,
            )
        if r.status_code < 400:
            break
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("retry-after") or min(60, 2 ** attempt))
            print(f"  Groq {r.status_code}; sleeping {wait:.0f}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
    else:
        r.raise_for_status()
    data = r.json()

    def ts(s):
        h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int((sec - int(sec)) * 1000):03d}"

    segs = data.get("segments") or []
    with txt_path.open("w", encoding="utf-8") as t, srt_path.open("w", encoding="utf-8") as s:
        for i, seg in enumerate(segs, start=1):
            text = seg["text"].strip()
            t.write(text + "\n")
            s.write(f"{i}\n{ts(seg['start'])} --> {ts(seg['end'])}\n{text}\n\n")
    audio.unlink(missing_ok=True)
    return srt_path, txt_path


def _whisper_device() -> tuple[str, str]:
    """Use the NVIDIA GPU if CTranslate2 can see one (much faster), else CPU.

    Kept local rather than imported from process_videos.py: these scripts are run
    standalone, and a cross-script import would drag in that module's dependencies
    for an eight-line pure function.
    """
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def default_whisper_model(device: str) -> str:
    """Pick the model to match the hardware.

    On a GPU, large-v3-turbo costs roughly a second of extra load over `small` and
    is dramatically more accurate on proper nouns — the errors that make a
    transcript unusable. On CPU the encoder still runs full size, so turbo is
    meaningfully slower there; `small` stays the default so a laptop transcribing a
    long course does not crawl. Either can be overridden with --whisper-model.

    Disk cost if you do switch: small 464 MB vs large-v3-turbo 1547 MB (measured).
    `medium` is listed for compatibility but is strictly dominated — turbo is 6%
    larger, more accurate, and faster.
    """
    return "large-v3-turbo" if device == "cuda" else "small"


def transcribe_local(video: Path, dest: Path, model_name: str) -> tuple[Path, Path]:
    from faster_whisper import WhisperModel
    txt = dest / "transcript.txt"
    srt = dest / "transcript.srt"
    device, compute_type = _whisper_device()
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segs, _ = model.transcribe(str(video), beam_size=5)

    def ts(s):
        h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int((sec - int(sec)) * 1000):03d}"

    with txt.open("w", encoding="utf-8") as t, srt.open("w", encoding="utf-8") as s:
        for i, seg in enumerate(segs, start=1):
            t.write(seg.text.strip() + "\n")
            s.write(f"{i}\n{ts(seg.start)} --> {ts(seg.end)}\n{seg.text.strip()}\n\n")
    return srt, txt


def load_groq_key() -> str | None:
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    for envf in [Path.home() / ".iss" / ".env", Path.home() / ".config" / "watch" / ".env"]:
        if envf.exists():
            for line in envf.read_text().splitlines():
                if line.startswith("GROQ_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def process_one(video: dict, out_dir: Path, want: set[str], yt_dlp: str, ffmpeg: str,
                cookies: Path | None, scene_threshold: float, whisper_model: str,
                groq_key: str | None, video_only_cookies: Path | None) -> dict:
    vid_id = video["id"]
    title = video.get("title") or vid_id
    slug = slugify(title)
    result = {"id": vid_id, "title": title, "want": sorted(want), "produced": {}}

    written_dir = out_dir / "written" / f"{slug}-{vid_id}"
    visual_dir = out_dir / "visual" / f"{slug}-{vid_id}"
    video_dir = out_dir / "video" / f"{slug}-{vid_id}"

    # description/chapters: no video download needed.
    if "description" in want:
        info = get_description_and_chapters(yt_dlp, video["url"], written_dir, cookies)
        result["produced"]["description"] = str(written_dir / "description.md")
        result["info"] = info

    # If we need transcript without a video file, try native captions first.
    need_video_file = "video" in want or "slides" in want
    transcript_source = None
    if "transcript" in want and not need_video_file:
        target = video_dir
        target.mkdir(parents=True, exist_ok=True)
        srt = get_native_subs(yt_dlp, video["url"], target, cookies)
        if srt:
            final = target / "transcript.srt"
            shutil.move(str(srt), str(final))
            (target / "transcript.txt").write_text(srt_to_text(final), encoding="utf-8")
            transcript_source = "native"
            result["produced"]["transcript"] = str(target / "transcript.txt")

    # If we need slides, video, or fallback transcription, download the video.
    if need_video_file or (transcript_source is None and "transcript" in want):
        vpath = download_video(yt_dlp, video["url"], video_dir, video_only_cookies or cookies)
        if not vpath:
            result["error"] = "video_download_failed"
            return result
        result["produced"]["video"] = str(vpath)

    # Slides
    if "slides" in want:
        n = extract_slides(ffmpeg, video_dir / "video.mp4", visual_dir / "slides", scene_threshold)
        result["produced"]["slides_count"] = n

    # Transcript via Whisper if we still don't have one
    if "transcript" in want and transcript_source is None:
        try:
            srt = get_native_subs(yt_dlp, video["url"], video_dir, cookies)
            if srt:
                final = video_dir / "transcript.srt"
                shutil.move(str(srt), str(final))
                (video_dir / "transcript.txt").write_text(srt_to_text(final), encoding="utf-8")
                transcript_source = "native"
        except Exception:
            pass
        if transcript_source is None:
            if groq_key:
                transcribe_groq(ffmpeg, video_dir / "video.mp4", video_dir, groq_key,
                                vocab=course_vocab(video))
                transcript_source = "groq"
            else:
                transcribe_local(video_dir / "video.mp4", video_dir, whisper_model)
                transcript_source = "whisper_local"
        result["produced"]["transcript"] = str(video_dir / "transcript.txt")
        result["transcript_source"] = transcript_source

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture YouTube content.")
    parser.add_argument("url", help="YouTube video, playlist, or channel URL")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--want", default="transcript", help="Comma-separated: transcript,slides,video,description")
    parser.add_argument("--cookies", default=None, help="Path to a Netscape cookies.txt (for private/age-gated content)")
    parser.add_argument("--scene-threshold", type=float, default=0.3)
    parser.add_argument("--whisper-model", default=None,
                        choices=["tiny","base","small","large-v3-turbo","medium","large-v3"],
                        help="default: large-v3-turbo on GPU, small on CPU")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    want = parse_want(args.want)
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata").mkdir(exist_ok=True)

    yt_dlp = find_exe("yt-dlp")
    ffmpeg = find_exe("ffmpeg")
    cookies = Path(args.cookies).expanduser().resolve() if args.cookies else None
    if cookies and not cookies.exists():
        print(f"Cookies file not found: {cookies}", file=sys.stderr); return 1
    groq_key = load_groq_key()

    print(f"Enumerating videos from {args.url} ...")
    videos = enumerate_videos(yt_dlp, args.url, cookies)
    if args.limit:
        videos = videos[:args.limit]
    print(f"Found {len(videos)} videos. Want: {sorted(want)}")
    if args.whisper_model is None:
        args.whisper_model = default_whisper_model(_whisper_device()[0])
    print(f"Transcription: {'Groq Whisper-large-v3-turbo' if groq_key else f'local faster-whisper ({args.whisper_model})'}")

    (out_dir / "metadata" / "playlist_manifest.json").write_text(
        json.dumps(videos, indent=2), encoding="utf-8")

    results = []
    start = time.time()
    for i, v in enumerate(videos, start=1):
        print(f"  [{i}/{len(videos)}] {v.get('title') or v['id']}")
        r = process_one(v, out_dir, want, yt_dlp, ffmpeg, cookies,
                        args.scene_threshold, args.whisper_model, groq_key, None)
        results.append(r)

    elapsed = time.time() - start
    (out_dir / "metadata" / "youtube_report.json").write_text(
        json.dumps({"run_seconds": round(elapsed, 1), "want": sorted(want),
                    "results": results}, indent=2, default=str), encoding="utf-8")
    print()
    print("=" * 60)
    print(f"Done in {elapsed:.0f}s ... report at {out_dir}/metadata/youtube_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
