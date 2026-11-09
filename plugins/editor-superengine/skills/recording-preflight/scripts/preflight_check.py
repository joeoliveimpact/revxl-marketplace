"""Check a short test recording before the real take (stdlib only).

  preflight_check.py <clip> [--json] [--selftest]

Prints one ✓ / ⚠ / ✗ line per check, in plain words: picture size and orientation (rotation-aware),
real frame rate and VFR, freezes and repeated frames, HDR, sound present, peak and loudness, length.
measure() reads every frame's own timestamp (showinfo, -fps_mode passthrough) and checksum, so a frame
the recorder repeated to fill a gap counts as a repeat; a timestamp gap of 150 ms or more is a freeze.
Exit 0 when nothing is ✗, else 1. --json is for Claude only.
"""
import argparse, json, re, shutil, statistics as st, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

SETUP = "The editor's setup isn't finished yet."
MARK = {"ok": "✓", "warn": "⚠", "fail": "✗"}
FREEZE_MS = 150
REPEAT_SHARE = 0.01   # ponytail: more than 1% repeated frames = dropped frames; tune on real phone clips
VFR_SHARE = 0.10      # more than 10% of gaps off the median by over 2 ms = variable frame rate


def find(name):
    try:
        p = rt.tool(name)
        if Path(p).exists():
            return p
    except (KeyError, OSError):
        pass
    return shutil.which(name)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)


def measure(ffmpeg, video):
    """Ported from the recording test bench: real fps, repeats, freezes from frame timestamps."""
    err = run([ffmpeg, "-hide_banner", "-i", str(video), "-map", "0:v:0", "-an",
               "-vf", "showinfo", "-fps_mode", "passthrough", "-f", "null", "-"]).stderr
    t, ck = [], []
    for line in err.splitlines():
        if "pts_time:" in line and "checksum:" in line:
            t.append(float(line.split("pts_time:")[1].split()[0]))
            ck.append(line.split("checksum:")[1].split()[0])
    if len(t) < 2 or t[-1] <= t[0]:
        return None
    gaps = [(b - a) * 1000 for a, b in zip(t, t[1:])]
    med = st.median(gaps)
    return {"fps": (len(t) - 1) / (t[-1] - t[0]), "frames": len(t),
            "repeats": sum(a == b for a, b in zip(ck, ck[1:])),
            "freezes": [round(t[i], 1) for i, g in enumerate(gaps) if g >= FREEZE_MS],
            "vfr": sum(abs(g - med) > 2 for g in gaps) / len(gaps) > VFR_SHARE}


def rotation(v):
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            return int(float(sd["rotation"]))
    return int(float(v.get("tags", {}).get("rotate", 0) or 0))


def check(clip, ffmpeg, ffprobe):
    out = []
    add = lambda level, what, text: out.append({"level": level, "check": what, "text": text})
    pr = run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(clip)])
    try:
        info = json.loads(pr.stdout)
    except ValueError:
        info = {}
    vids = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    auds = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not vids:
        add("fail", "video", "This file has no picture the editor can read. Record the test again with the camera app.")
        return out
    v = vids[0]
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    if abs(rotation(v)) % 180 == 90:
        w, h = h, w
    shape = "upright (portrait)" if h > w else "sideways (landscape)" if w > h else "square"
    size = f"{w}x{h}, {shape}"
    if min(w, h) < 1080:
        add("warn", "resolution", f"Picture is {size}, smaller than 1080p. Set the camera to 1080p or 4K.")
    elif h <= w:
        add("warn", "resolution", f"Picture is {size}. Reels are tall: turn the phone upright.")
    else:
        add("ok", "resolution", f"Picture is {size}.")

    m = measure(ffmpeg, clip)
    if m is None:
        add("fail", "frames", "The editor couldn't read the video frames. Record the test again.")
    else:
        vfr = (" It's a VFR clip (variable frame rate: the phone changes speed mid-clip); the editor evens"
               " that out, so nothing to do.") if m["vfr"] else ""
        if m["fps"] < 23.5:
            add("warn", "fps", f"About {m['fps']:.0f} frames a second, lower than usual. Set the camera to 30 fps.{vfr}")
        else:
            add("ok", "fps", f"About {m['fps']:.0f} frames a second.{vfr}")
        if m["freezes"] or m["repeats"] > REPEAT_SHARE * m["frames"]:
            add("warn", "freezes", f"The picture froze or repeated frames ({len(m['freezes'])} freeze(s), "
                                   f"{m['repeats']} repeated frame(s)): the recorder dropped frames. "
                                   "Close other apps and record again.")
        else:
            add("ok", "freezes", "No freezes or dropped frames.")

    if v.get("color_transfer") in ("arib-std-b67", "smpte2084"):
        add("ok", "hdr", "Recorded in HDR. That's fine: the editor converts it.")

    if not auds:
        add("fail", "audio", "No sound was recorded. Check the mic is on and the camera app may use it.")
    else:
        err = run([ffmpeg, "-hide_banner", "-i", str(clip), "-map", "0:a:0", "-af", "volumedetect",
                   "-f", "null", "-"]).stderr
        peak = re.search(r"max_volume:\s*(-?[\d.]+|-inf) dB", err)
        mean = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", err)
        peak = float(peak.group(1)) if peak else None
        mean = float(mean.group(1)) if mean else None
        if peak is None or mean is None:
            add("warn", "audio", "The editor couldn't measure the sound level. Play the test back and listen.")
        elif peak >= -0.5:
            add("warn", "audio", "The sound is too loud and likely distorted (clipping), which can't be fixed "
                                 "later. Move the mic a little further away or turn its level down.")
        elif mean < -40:
            add("warn", "audio", "The sound is very quiet. Move the mic closer.")
        else:
            add("ok", "audio", "Sound level is good.")

    try:
        dur = float(info.get("format", {}).get("duration", 0))
    except ValueError:
        dur = 0
    if dur < 3:
        add("warn", "length", "The test is under 3 seconds. Record about 10 seconds so the check has enough to go on.")
    return out


def selftest(ffmpeg, ffprobe):
    tmp = Path(tempfile.mkdtemp(prefix="preflight-"))
    vid = "testsrc2=size=180x320:rate=30:duration={d}"
    tone = "sine=frequency=440:sample_rate=48000:duration={d}"
    plans = {
        "clean": (vid, tone, None),
        "clipped": (vid, tone + ",volume=24dB", None),
        "silent": (vid, None, None),
        "freeze": (vid, tone, "settb=1/1000,setpts='(N/30+if(gte(N,45),0.4,0))/TB'"),
        "vfr": (vid, tone, "settb=1/1000,setpts='(N/30+if(mod(N,2),0.01,0))/TB'"),
    }
    failed = []
    try:
        for name, (v, a, vf) in plans.items():
            clip = tmp / f"{name}.mkv"
            cmd = [ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", v.format(d=3.2)]
            if a:
                cmd += ["-f", "lavfi", "-i", a.format(d=3.2)]
            if vf:
                cmd += ["-vf", vf]
            cmd += ["-fps_mode", "passthrough", "-enc_time_base", "1/1000", "-c:v", "mpeg4", "-q:v", "5"]
            cmd += ["-c:a", "pcm_s16le"] if a else []
            cmd += ["-shortest", str(clip)] if a else [str(clip)]
            r = run(cmd)
            if r.returncode:
                failed.append(f"{name}: making the test clip failed: {r.stderr.strip()[:200]}")
                continue
            res = {i["check"]: i for i in check(clip, ffmpeg, ffprobe)}
            lv = lambda k: res.get(k, {}).get("level")
            fails = [k for k, i in res.items() if i["level"] == "fail"]
            ok = {
                "clean": not fails and lv("audio") == "ok" and lv("freezes") == "ok"
                         and "portrait" in res["resolution"]["text"] and "VFR" not in res["fps"]["text"],
                "clipped": lv("audio") == "warn" and "clipping" in res["audio"]["text"],
                "silent": lv("audio") == "fail",
                "freeze": lv("freezes") == "warn",
                "vfr": "VFR" in res.get("fps", {}).get("text", ""),
            }[name]
            if not ok:
                failed.append(f"{name}: {list(res.values())}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if failed:
        print("SELFTEST FAIL\n" + "\n".join(failed))
        return 1
    print("SELFTEST PASS")
    return 0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    ffmpeg, ffprobe = find("ffmpeg"), find("ffprobe")
    if not (ffmpeg and ffprobe):
        print(SETUP)
        return 1
    if a.selftest:
        return selftest(ffmpeg, ffprobe)
    if not a.clip:
        ap.error("give the test clip")
    if not Path(a.clip).is_file():
        print("The test clip isn't there. Drop the file in again.")
        return 1
    res = check(a.clip, ffmpeg, ffprobe)
    if a.json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        for i in res:
            print(f"{MARK[i['level']]} {i['text']}")
    return 1 if any(i["level"] == "fail" for i in res) else 0


if __name__ == "__main__":
    sys.exit(main())
