"""Prepare own or downloaded AI clips without audio, and log their exact bytes.

  <editor python> -X utf8 -I broll_ingest.py <reel_dir>
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "_shared"))
sys.path.insert(0, str(SKILLS / "_shared" / "checks"))
sys.path.insert(0, str(SKILLS / "reel-canvas-build" / "scripts"))
import runtime as rt
import footage_check
import cutout
import fps
from win_encoding import ensure_utf8_output


def first_cuts(name):
    path = SKILLS / "reel-first-cuts" / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location("broll_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = first_cuts("render")
probe = first_cuts("probe")
VIDEOS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".m2ts", ".mpg", ".mpeg"}


def reuse(reel, request_sha256):
    try:
        clips = json.loads((reel / "broll/clips.json").read_text(encoding="utf-8"))["clips"]
        ledger = footage_check.rows(reel)
        for clip in clips:
            if clip.get("origin") != "ai" or clip.get("request_sha256") != request_sha256:
                continue
            path = reel / clip["src"]
            matches = [r for r in ledger if r.get("id") == clip["ledger_id"] and
                       footage_check.normalized(footage_check.locate(reel, r)) ==
                       footage_check.normalized(path)]
            if (len(matches) == 1 and matches[0].get("role") == "broll" and
                    matches[0].get("origin") == "ai" and clip.get("job_id") and
                    matches[0].get("job_id") == clip["job_id"] and path.is_file() and
                    footage_check.digest(path) == matches[0]["sha256"]):
                print(f"reuse: {clip['ledger_id']} {clip['src']} (job {clip['job_id']})")
                return 0
    except (OSError, ValueError, KeyError, TypeError):
        pass
    print("no earlier AI clip for this exact request")
    return 1


def ingest(reel, ai=None, job_id=None, request_sha256=None):
    cuts = reel / "work" / "cuts.json"
    if not cuts.is_file():
        print("cut the reel first")
        return 1
    cut = json.loads(cuts.read_text(encoding="utf-8"))
    rate = fps.as_fraction(cut["fps"])
    raw = None if cut.get("takes") else json.loads(
        (reel / "work/probe.json").read_text(encoding="utf-8"))["input"]
    recordings = {}
    for use in footage_check.cut_uses(cut, raw):
        recording = footage_check.asset(reel, use["path"])
        if not recording.is_file():
            print(f"your recording {recording.name} is missing; restore it before adding B-roll")
            return 1
        recordings[footage_check.normalized(recording)] = recording
    try:
        ffmpeg, ffprobe = rt.tool("ffmpeg"), rt.tool("ffprobe")
        if not all(Path(p).is_file() for p in (ffmpeg, ffprobe)):
            raise OSError()
    except (KeyError, OSError, ValueError):
        print(render.SETUP)
        return 1
    probe.FFMPEG, probe.FFPROBE = ffmpeg, ffprobe
    folder = reel / "broll"
    out = folder / "clips.json"
    previous = json.loads(out.read_text(encoding="utf-8"))["clips"] if out.is_file() else []
    logged = {footage_check.normalized(footage_check.locate(reel, row))
              for row in footage_check.rows(reel)}
    for key, recording in recordings.items():
        if key not in logged:
            footage_check.add(reel, recording, role="aroll", origin="own", licence="own")
            print(f"logged your recording {recording.name} in the footage list, so B-roll and the final can check it")
    dest = folder / "ingested"
    dest.mkdir(parents=True, exist_ok=True)
    # An own scan refreshes own clips; adding one paid clip preserves every other pick.
    clips = list(previous) if ai else [c for c in previous if c.get("origin") == "ai"]
    stems = set()
    sources = [ai] if ai else sorted(folder.iterdir())
    failed = False
    for src in sources:
        if not src.is_file() or (not ai and src.suffix.lower() not in VIDEOS):
            continue
        if src.stem.casefold() in stems:
            print(f"skipped {src.name}: another clip has this name; give it a different name")
            continue
        stems.add(src.stem.casefold())
        dst = dest / ((("ai-" + request_sha256) if ai else src.stem) + ".mp4")
        partial = None
        try:
            ledger = footage_check.rows(reel)
            matches = [r for r in ledger if footage_check.normalized(footage_check.locate(reel, r)) ==
                       footage_check.normalized(dst)]
            if dst.exists():
                sha = footage_check.digest(dst)
                # add() dedupes bytes across paths. Keep its canonical path, never invent a second row.
                if not matches:
                    matches = [r for r in ledger if r.get("sha256") == sha]
                if len(matches) != 1 or sha != matches[0]["sha256"]:
                    print(f"skipped {src.name}: the prepared clip changed after it was logged; restore it before adding clips")
                    failed = True
                    continue  # never silently bless changed bytes or create duplicate ledger paths
                ident = matches[0]["id"]
            else:
                facts = probe.video_facts(src)
                if not facts.get("width"):
                    raise ValueError("the video could not be read")
                info = json.loads(fps._ffprobe(src, ffprobe, ["-select_streams", "v:0", "-show_entries",
                                                            "stream=duration:format=duration", "-of", "json"], "duration"))
                stream_duration = (info.get("streams") or [{}])[0].get("duration")
                duration = float(stream_duration if stream_duration not in (None, "N/A") else
                                 (info.get("format") or {}).get("duration", 0))
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError("the video duration could not be read")
                filters = [f"fps={rate}",
                           "scale=1080:1920:force_original_aspect_ratio=increase:force_divisible_by=2:flags=lanczos",
                           "setsar=1", *render.tonemap(facts), cutout.BT709_VF]
                fd, temp_name = tempfile.mkstemp(prefix=".broll-", suffix=".mp4", dir=dest)
                os.close(fd)
                partial = Path(temp_name)
                result = subprocess.run([str(ffmpeg), "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-an",
                                         "-sn", "-dn", "-vf", ",".join(filters), "-fps_mode", "cfr", "-c:v", "libx264",
                                         "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv420p", *cutout.TAGS,
                                         str(partial)], capture_output=True, env=rt.python_env())
                if result.returncode:
                    raise ValueError("the video could not be prepared")
                if not cutout.cfr_close_enough(duration * float(rate), fps.frame_count(partial)):
                    raise ValueError("the prepared clip's frame count does not match its duration")
                os.replace(partial, dst)
                ident = footage_check.add(reel, dst, role="broll", origin="ai" if ai else "own",
                                          licence="ai: higgsfield (client's own plan)" if ai else "own",
                                          job_id=job_id if ai else None)
            row = next(r for r in footage_check.rows(reel) if r["id"] == ident)
            # Byte deduplication must never present own footage as AI, or attach another job's id.
            if row.get("origin") != ("ai" if ai else "own") or (ai and
                    (row.get("role") != "broll" or row.get("job_id") != job_id)):
                raise ValueError("the prepared clip belongs to a different footage entry")
            logged = footage_check.locate(reel, row).resolve()
            rel = logged.relative_to(reel).as_posix()
            if not logged.is_file() or footage_check.digest(logged) != row["sha256"]:
                raise ValueError("the logged clip is missing or changed")
            if any(c["ledger_id"] == ident for c in clips) and not ai:
                print(f"reused {src.name}: the same clip is already in the picker")
                continue
            width, height = cutout.frame_size(logged)
            clip = dict(ledger_id=ident, src=rel, name=src.name, origin="ai" if ai else "own",
                        frames=fps.frame_count(logged), width=width, height=height)
            if ai:
                clip.update(job_id=job_id, request_sha256=request_sha256)
            existing = next((i for i, c in enumerate(clips) if c["ledger_id"] == ident), None)
            if existing is None:
                clips.append(clip)
            else:
                clips[existing] = clip
        except (OSError, ValueError, KeyError, TypeError, cutout.CutoutError):
            print(f"skipped {src.name}: the video could not be read or prepared")
            failed = True
        finally:
            if partial is not None:
                partial.unlink(missing_ok=True)
    if ai and failed:
        return 1
    tmp = out.with_suffix(".json.tmp")
    tmp.write_bytes((json.dumps({"fps": float(rate), "clips": clips}, indent=1) + "\n").encode("utf-8"))
    os.replace(tmp, out)
    print(f"Ready: {len(clips)} B-roll clips. Pick them on the Beat Map tab, then Send.")
    return 0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reel_dir")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--ai", type=Path)
    mode.add_argument("--reuse", type=Path)
    ap.add_argument("--job-id")
    ap.add_argument("--request", type=Path)
    args = ap.parse_args()
    try:
        if args.ai is not None:
            if not args.job_id or not args.job_id.strip() or args.request is None:
                print("adding an AI clip needs both its job id and request file")
                return 1
            if not args.ai.is_file():
                print("the downloaded AI clip is missing; restore it before adding it")
                return 1
        request_sha256 = None
        request = args.reuse if args.reuse is not None else args.request
        if request is not None:
            try:
                request_sha256 = hashlib.sha256(request.read_bytes()).hexdigest()
            except OSError:
                print("the request file could not be read; restore it and try again")
                return 1
        reel = Path(args.reel_dir).resolve()
        if args.reuse is not None:
            return reuse(reel, request_sha256)
        return ingest(reel, args.ai, args.job_id, request_sha256)
    except (OSError, ValueError, KeyError, TypeError):
        print("The B-roll step could not read the reel or its footage ledger; check them and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
