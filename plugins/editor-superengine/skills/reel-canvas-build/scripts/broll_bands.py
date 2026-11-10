"""Small, cached B-roll detail measurements; placement only reads this cache."""
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import runtime as rt  # noqa: E402

CACHE = "work/broll-bands.json"
WIDTH, HEIGHT = 270, 480
ROW_PX = 16  # one stored row is four measured rows, in the 1920-high master


def beat_key(beat):
    clip = beat["broll"]
    return json.dumps([beat["start_f"], beat["end_f"], clip["src"], clip["in"], clip["out"],
                       clip["fit"], beat["layout"]], separators=(",", ":"))


def read_cache(reel):
    """No stat of source clips, probes, decoding or writes; old reels need no cache."""
    try:
        doc = json.loads((Path(reel) / CACHE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict) or doc.get("schema") != 1 or not isinstance(doc.get("beats"), dict):
        return {}
    return {key: entry for key, entry in doc["beats"].items()
            if isinstance(entry, dict) and isinstance(entry.get("rows"), list)
            and len(entry["rows"]) == 1920 // ROW_PX
            and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in entry["rows"])}


def _profile(path, beat):
    clip = beat["broll"]
    first = clip["in"]
    last = min(clip["out"], first + beat["end_f"] - beat["start_f"]) - 1
    if last < first:
        raise ValueError("empty clip range")
    frames = sorted({round(first + (last - first) * i / 4) for i in range(5)})
    select = "+".join(f"eq(n\\,{frame})" for frame in frames)
    if clip["fit"] == "cover":
        fit = "scale=270:480:force_original_aspect_ratio=increase,crop=270:480"
    else:
        fit = "scale=270:480:force_original_aspect_ratio=decrease,pad=270:480:(ow-iw)/2:(oh-ih)/2:black"
    result = subprocess.run([rt.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-i", str(path),
                             "-an", "-vf", f"select={select},{fit},setsar=1,format=gray",
                             "-vsync", "0", "-frames:v", str(len(frames)), "-f", "rawvideo", "pipe:1"],
                            capture_output=True, env=rt.python_env(), timeout=45)
    size = WIDTH * HEIGHT
    if result.returncode or len(result.stdout) != size * len(frames):
        raise ValueError("clip frames could not be read")
    profile = [0.0] * (1920 // ROW_PX)
    for offset in range(0, len(result.stdout), size):
        frame = result.stdout[offset:offset + size]
        rows = []
        for y in range(HEIGHT):
            row = frame[y * WIDTH:(y + 1) * WIDTH]
            horizontal = sum(abs(row[x] - row[x - 1]) for x in range(1, WIDTH)) / (WIDTH - 1)
            vertical = (sum(abs(row[x] - frame[(y - 1) * WIDTH + x]) for x in range(WIDTH)) / WIDTH
                        if y else 0)
            rows.append(horizontal + vertical)
        for group in range(len(profile)):
            # A busy sampled moment must not be hidden by plainer frames.
            profile[group] = max(profile[group], sum(rows[group * 4:group * 4 + 4]) / 4)
    return profile


def measure(reel, beats=None):
    """Refresh changed beats only; unreadable clips leave no profile and a plain note.

    Callers may supply the exact render beats; otherwise use the saved Beat Map.
    The identity plus source mtime/size invalidate both beat edits and clip edits.
    """
    reel = Path(reel)
    if beats is None:
        try:
            beats = json.loads((reel / "beat-map-selection.json").read_text(encoding="utf-8"))["beats"]
        except (OSError, ValueError, KeyError, TypeError):
            return []  # existing input checks own missing/invalid Beat Maps
    old, measured, notes = read_cache(reel), {}, []
    for beat in beats:
        clip = beat.get("broll")
        if not clip or clip.get("fit") not in ("cover", "contain"):
            continue
        try:
            key = beat_key(beat)
            source = reel / clip["src"]
            stat = source.stat()
            cached = old.get(key, {})
            if cached.get("mtime_ns") == stat.st_mtime_ns and cached.get("size") == stat.st_size:
                measured[key] = cached
            else:
                measured[key] = dict(mtime_ns=stat.st_mtime_ns, size=stat.st_size, rows=_profile(source, beat))
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            notes.append(f"The B-roll clip {clip.get('src', '')} could not be measured; using the usual caption position.")
    if measured != old or (measured and not (reel / CACHE).is_file()):
        try:
            (reel / CACHE).parent.mkdir(parents=True, exist_ok=True)
            (reel / CACHE).write_bytes((json.dumps(dict(schema=1, beats=measured), indent=2) + "\n").encode("utf-8"))
        except OSError:
            notes.append("The B-roll measurements could not be saved; using the usual caption position.")
    return notes
