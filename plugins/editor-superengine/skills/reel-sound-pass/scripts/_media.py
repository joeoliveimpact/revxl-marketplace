# Changed from shorts-studio scripts/_media.py (MIT): ffprobe/ffmpeg via runtime.tool, video-stream length, float audio in/out, loudness, workspace paths; frame helpers dropped.
"""Small media helpers shared by the sound-pass scripts. Standard library + numpy; ffmpeg comes from the editor install."""
import json, re, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE.parents[1] / "editor-doctor" / "scripts"))
import runtime as rt  # noqa: E402

SR = 48000          # every stem, mix and master: float32, 48 kHz, stereo


def ffmpeg():
    return rt.tool("ffmpeg")


def ffprobe():
    return rt.tool("ffprobe")


def probe(path):
    """The picture: w, h, fps and dur (the video stream's own length when the file has one)."""
    out = subprocess.check_output([ffprobe(), '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height,r_frame_rate,duration:format=duration', '-of', 'json', str(path)])
    info = json.loads(out)
    s = info['streams'][0]
    num, den = s.get('r_frame_rate', '30/1').split('/')
    dur = s.get('duration') or info.get('format', {}).get('duration') or 0
    return {'w': s['width'], 'h': s['height'], 'dur': float(dur), 'fps': float(num) / float(den or 1)}


def decode(path, sr=SR):
    """The file's first audio track as float32 frames x 2 channels."""
    p = subprocess.run([ffmpeg(), '-v', 'error', '-i', str(path), '-map', '0:a:0', '-ac', '2', '-ar', str(sr),
                        '-f', 'f32le', '-'], capture_output=True)
    if p.returncode:
        raise RuntimeError("could not read the sound in %s: %s" % (Path(path).name, p.stderr.decode(errors='replace')[-300:]))
    return np.frombuffer(p.stdout, np.float32).reshape(-1, 2).copy()


def write_wav(path, x, sr=SR):
    """float32 WAV, written through ffmpeg (no audio library needed). The samples go in and out unchanged."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    x = np.ascontiguousarray(x, np.float32)
    p = subprocess.run([ffmpeg(), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', str(x.shape[1]), '-i', '-',
                        '-c:a', 'pcm_f32le', str(path)], input=x.tobytes(), capture_output=True)
    if p.returncode:
        raise RuntimeError("could not write %s: %s" % (Path(path).name, p.stderr.decode(errors='replace')[-300:]))


def loudness(path, af=None):
    """(integrated LUFS, true peak dBTP) of the first audio track, by ffmpeg ebur128 with true peak on."""
    chain = (af + ',' if af else '') + 'ebur128=peak=true'
    log = subprocess.run([ffmpeg(), '-nostats', '-i', str(path), '-vn', '-af', chain, '-f', 'null', '-'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    return (float(re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", log)[-1]),
            float(re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", log)[-1]))


def channels(path):
    out = subprocess.run([ffprobe(), '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else 0


def video_md5(path):
    """MD5 of the video stream's packets (a copy keeps it, a re-encode changes it)."""
    return subprocess.run([ffmpeg(), '-v', 'error', '-i', str(path), '-map', '0:v', '-c', 'copy', '-f', 'md5', '-'],
                          capture_output=True, text=True).stdout.strip()


def workspace():
    """(editor folder, videos folder) of the client's workspace (the cwd), from editor.config.json paths."""
    import board_sync
    return board_sync.workspace_paths(Path.cwd())


def find_picture(reel, video=None):
    """The picture-locked video: --video, else the board config's picture_url, else the newest master render."""
    if video:
        return Path(video)
    try:
        url = json.loads((reel / 'config.json').read_text(encoding='utf-8')).get('picture_url')
        if url and (reel / url).is_file():
            return reel / url
    except (OSError, ValueError):
        pass
    renders = sorted((reel / 'work' / 'renders').glob('master-*.mp4'), key=lambda p: p.stat().st_mtime)
    return renders[-1] if renders else None


def write_json(path, obj, indent=1):
    """JSON with LF line ends on every OS, written whole (.tmp then replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes((json.dumps(obj, indent=indent) + '\n').encode('utf-8'))
    tmp.replace(path)


def guarded(main, detail=True):
    """Run a script's main(): an unexpected failure prints one plain line and exits 1, never a traceback.
    detail=False names only the kind of failure (scripts that hold the Auphonic key, so no message can carry it)."""
    try:
        return main()
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001  (the last line of defence; known failures print their own line)
        msg = str(e).strip().splitlines()[0][:200] if detail and str(e).strip() else ""
        print("The sound step stopped unexpectedly (%s%s). Run it again; if it fails twice, offer the failure report."
              % (type(e).__name__, ": " + msg if msg else ""))
        return 1
