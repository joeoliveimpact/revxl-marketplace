#!/usr/bin/env python3
"""Stage 0 - probe and calibrate. Trust nothing the container says.

Establishes, by measurement:
  * true frame rate (avg_frame_rate + a PTS-delta histogram over the WHOLE file)
  * the RMS envelope of the source audio - the single measurement surface for
    every later stage. Nothing downstream needs a render to exist.
  * per-file thresholds: noise floor, speech floor, breath/syllable split
  * the duplicate-frame cost of each candidate output rate
  * which frame-rate flag this ffmpeg supports

Writes work/probe.json + work/envelope.json. Prints a human-readable report.
"""
import argparse, json, math, os, re, shutil, struct, subprocess, sys, wave
from pathlib import Path

WIN = 0.010          # envelope resolution, seconds


def die(msg, code=2):
    print("ERROR: %s" % msg, file=sys.stderr)
    raise SystemExit(code)


def need(tool):
    if not shutil.which(tool):
        die("%s not found on PATH" % tool)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ffprobe_json(path, args):
    p = run(["ffprobe", "-v", "error", "-of", "json"] + args + [str(path)])
    if p.returncode:
        die("ffprobe failed: %s" % p.stderr.strip())
    return json.loads(p.stdout)


# --------------------------------------------------------------------------- fps
def true_fps(path):
    """Container headers lie. r_frame_rate said 60/1 on a file that was 22.31 VFR."""
    st = ffprobe_json(path, ["-select_streams", "v:0", "-show_entries",
                             "stream=r_frame_rate,avg_frame_rate,nb_frames,duration"])
    s = st["streams"][0]

    def frac(x):
        try:
            n, d = x.split("/")
            return float(n) / float(d) if float(d) else 0.0
        except Exception:
            return 0.0

    declared, avg = frac(s.get("r_frame_rate", "0/1")), frac(s.get("avg_frame_rate", "0/1"))

    # packet timestamps need no decode and cover the whole file
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)])
    ts = sorted(float(x) for x in p.stdout.split() if x.replace(".", "", 1).replace("-", "", 1).isdigit())
    deltas = [round((ts[i + 1] - ts[i]) * 1000) for i in range(len(ts) - 1)] if len(ts) > 1 else []
    span = (ts[-1] - ts[0]) if len(ts) > 1 else 0.0
    measured = (len(ts) - 1) / span if span > 0 else avg
    hist = {}
    for d in deltas:
        hist[d] = hist.get(d, 0) + 1
    top = sorted(hist.items(), key=lambda kv: -kv[1])[:6]
    median = sorted(deltas)[len(deltas) // 2] if deltas else 0
    # VFR when the modal delta does not dominate
    vfr = bool(deltas) and (max(hist.values()) / len(deltas) < 0.9)
    return {"declared_r_frame_rate": declared, "avg_frame_rate": avg,
            "measured_fps": round(measured, 3), "frames": len(ts),
            "span_s": round(span, 3), "median_delta_ms": median,
            "top_deltas_ms": top, "vfr": vfr}


# ---------------------------------------------------------------------- envelope
def envelope(path, workdir):
    wav = Path(workdir) / "_source.wav"
    p = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vn",
             "-map", "0:a:0", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1", str(wav)])
    if p.returncode:
        die("audio extract failed: %s" % p.stderr.strip())
    w = wave.open(str(wav), "rb")
    sr, n = w.getframerate(), w.getnframes()
    raw = w.readframes(n)
    w.close()
    s = struct.unpack("<%dh" % (len(raw) // 2), raw)
    step = int(sr * WIN)
    env = []
    for i in range(0, len(s) - step, step):
        b = s[i:i + step]
        r = math.sqrt(sum(float(x) * float(x) for x in b) / len(b)) / 32768.0
        env.append(round(20 * math.log10(r) if r > 1e-9 else -120.0, 2))
    return env


def calibrate(env):
    """Derive thresholds from THIS file. Never ship a magic number.

    A fixed -42dB floor ate consonants, which sit around -35..-45dB. The gap
    between the room-tone mode and the speech mode is what actually separates
    them, and it differs per recording, mic and room.
    """
    live = sorted(d for d in env if d > -119)
    if not live:
        die("no audio")
    q = lambda p: live[max(0, min(len(live) - 1, int(len(live) * p)))]
    noise_floor, speech_ref = q(0.05), q(0.90)

    # Offsets are ABOVE THE ROOM TONE, not below the speech level. Anchoring to
    # speech puts the floor tens of dB too low on a quiet recording: on the
    # reference build a speech-anchored rule produced -57.9/-52.9, where the
    # values that actually worked were -50/-45 == room tone +20 / +25.
    gap_db = round(noise_floor + 20.0, 1)
    speech_db = round(noise_floor + 25.0, 1)
    # never let the floors climb into speech itself
    ceiling = speech_ref - 20.0
    if speech_db > ceiling:
        speech_db = round(ceiling, 1)
        gap_db = round(ceiling - 5.0, 1)

    # Breath vs syllable is a DURATION question, not a level one. A voiced
    # syllable runs 100ms+; a breath or a splice decay tail runs ~40ms. Six
    # windows is the phonetic floor -- four was the value that read a breath as
    # speech and left a 0.667s gap standing (fixtures F5).
    runs, cur = [], 0
    for d in env:
        if d > speech_db:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    runs.sort()
    lower_q = runs[max(0, int(len(runs) * 0.25))] if runs else 6
    return {"noise_floor_db": round(noise_floor, 1), "speech_ref_db": round(speech_ref, 1),
            "gap_db": gap_db, "speech_db": speech_db,
            "speech_run_windows": max(6, min(12, lower_q)),
            "win_s": WIN}


def dup_table(measured_fps, speeds, out_rate):
    """Duplicate frames when conforming VFR source to CFR at each speed.

    Counter-intuitive and source-specific: speeding up pulls MORE source frames
    into each output second, so on VFR source a faster ramp is SMOOTHER. Report
    it; never assert it as a rule.
    """
    rows = []
    for sp in speeds:
        uniq = measured_fps * sp
        dup = max(0.0, (out_rate - uniq) / out_rate * 100.0)
        rows.append({"speed": sp, "unique_fps": round(uniq, 2), "dup_pct": round(dup, 1)})
    return rows


def fps_flag():
    h = run(["ffmpeg", "-hide_banner", "-h", "full"]).stdout
    return "-fps_mode" if re.search(r"^\s*-fps_mode", h, re.M) else "-vsync"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--work", default="work")
    ap.add_argument("--out-rate", type=float, default=30.0)
    ap.add_argument("--speeds", default="1.00,1.10,1.15")
    a = ap.parse_args()

    need("ffmpeg"); need("ffprobe")
    src = Path(a.input)
    if not src.exists():
        die("no such file: %s" % src)
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)

    fps = true_fps(src)
    env = envelope(src, work)
    cal = calibrate(env)
    speeds = [float(x) for x in a.speeds.split(",")]
    dups = dup_table(fps["measured_fps"], speeds, a.out_rate)

    (work / "envelope.json").write_text(json.dumps({"win_s": WIN, "db": env}), encoding="utf-8")
    probe = {"input": str(src), "fps": fps, "calibration": cal,
             "dup_table": dups, "out_rate": a.out_rate, "fps_flag": fps_flag()}
    (work / "probe.json").write_text(json.dumps(probe, indent=1), encoding="utf-8")

    L = []
    L.append("FRAME RATE")
    L.append("  container says : %.3f  <- do not use" % fps["declared_r_frame_rate"])
    L.append("  measured       : %.3f fps over %d frames / %.2fs" %
             (fps["measured_fps"], fps["frames"], fps["span_s"]))
    L.append("  VFR            : %s (median delta %d ms)" % (fps["vfr"], fps["median_delta_ms"]))
    if abs(fps["declared_r_frame_rate"] - fps["measured_fps"]) > 1.0:
        L.append("  !! header disagrees with measurement by %.1f fps"
                 % abs(fps["declared_r_frame_rate"] - fps["measured_fps"]))
    L.append("")
    L.append("CALIBRATION (from this file, not defaults)")
    L.append("  room tone      : %.1f dB" % cal["noise_floor_db"])
    L.append("  speech level   : %.1f dB" % cal["speech_ref_db"])
    L.append("  silence floor  : %.1f dB" % cal["gap_db"])
    L.append("  speech floor   : %.1f dB" % cal["speech_db"])
    L.append("  sustained run  : %d windows (%.0f ms) to count as speech"
             % (cal["speech_run_windows"], cal["speech_run_windows"] * WIN * 1000))
    L.append("")
    L.append("DUPLICATE FRAMES at %.0f fps CFR" % a.out_rate)
    for r in dups:
        L.append("  %.2fx  %5.2f unique fps  %4.1f%% dup" % (r["speed"], r["unique_fps"], r["dup_pct"]))
    if fps["vfr"]:
        L.append("  (VFR source: faster ramps carry FEWER duplicates. Source-specific.)")
    L.append("")
    L.append("ffmpeg frame-rate flag: %s" % probe["fps_flag"])
    L.append("wrote %s and %s" % (work / "probe.json", work / "envelope.json"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
