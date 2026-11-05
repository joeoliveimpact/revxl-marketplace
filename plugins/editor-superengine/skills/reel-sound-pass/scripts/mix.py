# Changed from shorts-studio scripts/mix.py (MIT): rewritten into the one sound-pass entry point (quiet gate, stems, free or Auphonic voice clean, ratio-keeping sum, master, mux last, F-4 gate, cue check); the music loop path is gone.
"""mix.py: finish the sound of a picture-locked reel.

  mix.py --reel <reel> [--voice free|auphonic] [--yes] [--video <locked.mp4>]

--voice defaults to editor.config.json voice_cleanup (free when unset). Auphonic costs money: it runs only with
--yes, which Claude passes only after the client said yes to `auphonic.py plan`. Without an Auphonic key the free
clean-up is used, and the output says so.

  1. Quiet gate (fix 8): the recording's average loudness (work/probe.json mean_loudness_db, else measured the way
     the transcription step does) under -45 dB stops here, exit 1, nothing written.
  1b. Music licence: with a bed picked, music.json is rewritten (music_pick.pick) and any missing licence row
      (checks/licence_rows.py) stops here, exit 1, nothing mixed. No bed: voice only, unchanged.
  2. Stems (bake.py): from sound-selection.json (the Sound Board's Send) when there is one, else voice only.
  3. Voice clean: free = a low cut at 80 Hz and light compression; auphonic = auphonic.py run.
  4. The cleaned voice is re-gained (one static gain) to the original voice's loudness, so the board's ratio
     holds, and summed with the sound effects and music at unity. No dead-silent holes allowed (room_tone check).
  5. Master (master_audio.py): one static gain to -14 LUFS, then a limiter swept until true peak <= -1.0 dBTP.
  6. Mux LAST: the picture is copied, never re-encoded; stereo AAC 192k; nothing truncated, nothing looped.
  7. F-4 gate on the delivered file: stereo, -14 +-0.5 LUFS, <= -1.0 dBTP, video stream unchanged. Outside the
     window: one corrective pass of 5-7; still outside: exit 1 with the numbers.
  8. mix_check.py on the delivered file when there are cues. Everything lands in <reel>/sound/mix-report.json.
Delivered file: <reel>/sound/final.mp4. Exit 0 done, 1 stopped by a check, 2 bad input, 3 Auphonic without --yes.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _media import SR, decode, write_wav, loudness, ffmpeg, video_md5, find_picture, workspace, write_json, rt  # noqa: E402
import auphonic, bake, master_audio, mix_check, room_tone  # noqa: E402
import music_pick  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "checks"))
import licence_rows  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

QUIET_DB = -45.0     # the same line the transcription step uses (HF-5 b)
FREE_VOICE = "highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2"


def mean_loudness(video):
    """The transcription step's reading: volumedetect's mean on the first audio track as 16 kHz mono 16-bit."""
    log = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-af",
                          "aformat=sample_fmts=s16:sample_rates=16000:channel_layouts=mono,volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", log)
    return -120.0 if not m or m.group(1) == "-inf" else float(m.group(1))


def recording_loudness(reel, picture):
    try:
        db = json.loads((reel / "work" / "probe.json").read_text(encoding="utf-8")).get("mean_loudness_db")
        if db is not None:
            return float(db)
    except (OSError, ValueError, AttributeError):
        pass
    return mean_loudness(picture)


def clean_voice(mode, yes, reel, sound):
    """Cleaned voice file, or an exit code."""
    voice, clean = sound / "voice.wav", sound / "voice-cleaned.wav"
    if mode == "auphonic":
        if not auphonic.read_key():
            print(auphonic.NO_KEY)
            mode = "free"
        else:
            rc = auphonic.main(["run", str(voice), "--out", str(clean), "--reel-dir", str(reel)] + (["--yes"] if yes else []))
            return clean if rc == 0 else (3 if rc == 3 else 1)
    p = subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(voice), "-af", FREE_VOICE, "-c:a", "pcm_f32le", str(clean)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        print("The free voice clean-up failed: %s" % p.stderr.strip()[-300:])
        return 1
    return clean


def mux(picture, master, out):
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(picture), "-i", str(master), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", str(out)],
                   check=True)


def run(a):
    reel = workspace()[1] / a.reel
    picture = find_picture(reel, a.video) if reel.is_dir() else None
    if not picture or not picture.is_file():
        print("Couldn't find the reel folder or its picture-locked video. Pass --video with the locked video.")
        return 2
    mode = a.voice or rt.read_config().get("voice_cleanup") or "free"

    db = recording_loudness(reel, picture)
    if db < QUIET_DB:
        print("This recording is nearly silent (average %.1f dB; a mix needs about %.0f dB or louder), so nothing "
              "was mixed. Check that the right microphone was recording." % (db, QUIET_DB))
        return 1

    if music_pick.pick(reel, workspace()[0]):                  # keeps music.json current, then the licence check
        blocks = [r["msg"] for r in licence_rows.run({"reel_dir": reel, "fps": None, "cuts": None, "beats": None,
                                                     "render": None}) if r["level"] == "block"]
        if blocks:
            print("The final wasn't made: %s. Fix the music's licence row, or pick other music on the board."
                  % "; ".join(blocks))
            return 1

    sound = reel / "sound"
    try:
        placement = bake.bake(reel, picture)
    except (bake.BakeError, room_tone.NoRoomTone) as e:
        print("The sound stems failed a check: %s. Nothing was mixed." % e)
        return 1

    clean = clean_voice(mode, a.yes, reel, sound)
    if isinstance(clean, int):
        return clean

    i_voice, i_clean = loudness(sound / "voice.wav")[0], loudness(clean)[0]
    regain = i_voice - i_clean
    voice = decode(clean) * np.float32(10 ** (regain / 20))
    if len(voice) != placement["samples"]:
        print("The cleaned voice is not the picture's length, so nothing was mixed.")
        return 1
    write_wav(sound / "voice-mixed.wav", voice)
    premaster = voice + decode(sound / "sfx.wav") + decode(sound / "music.wav")
    holes = room_tone.silent_runs(premaster)
    if holes:
        print("The mix has %d dead-silent stretch(es) (first at %.2f-%.2f s), so it was not mastered."
              % (len(holes), *holes[0]))
        return 1
    write_wav(sound / "premaster.wav", premaster)

    target, tp_max = master_audio.TARGET_I, master_audio.TP_MAX
    md5_in = video_md5(picture)
    final, partial = sound / "final.mp4", sound / "final.partial.mp4"
    report = {"voice": mode, "voice_regain_db": round(regain, 2), "cues": len(placement["cues"]), "passes": []}
    for attempt in (1, 2):
        m = master_audio.master(sound / "premaster.wav", sound / "master.wav", target, tp_max)
        mux(picture, sound / "master.wav", partial)
        ok, nums, problems = master_audio.gate(partial)
        same = video_md5(partial) == md5_in
        if not same:
            problems.append("the picture changed")
        report["passes"].append({"master": m, "gate": nums, "problems": problems})
        if ok and same:
            break
        if attempt == 2 or not same:
            write_json(sound / "mix-report.json", dict(report, **{"pass": False}))
            partial.unlink()
            print("The delivered file failed the sound check: %s. Nothing was delivered." % "; ".join(problems))
            return 1
        target += master_audio.TARGET_I - nums["integrated_lufs"]          # one corrective static gain
        if nums["true_peak_dbtp"] > master_audio.TP_MAX:
            tp_max -= nums["true_peak_dbtp"] - master_audio.TP_MAX + 0.1
    partial.replace(final)
    report.update(final=final.name, video_md5=md5_in, **{"pass": True})

    if placement["cues"]:
        chk = mix_check.check(final, sound / "voice-mixed.wav", sound)
        report["mix_check"] = chk
        report["pass"] = chk["pass"]
    write_json(sound / "mix-report.json", report)
    g = report["passes"][-1]["gate"]
    if not report["pass"]:
        print("Mixed, but the check found a problem: %s. Listen to sound/final.mp4 before using it." % (
            ", ".join("cue %s didn't come through" % c["id"] for c in report["mix_check"]["weak_cues"])
            or "the music level moved under the voice"))
        return 1
    print("Mixed: sound/final.mp4 (%.1f LUFS, peak %.1f dBTP, %s voice clean-up, %d sound effect%s)." % (
        g["integrated_lufs"], g["true_peak_dbtp"], mode, len(placement["cues"]), "" if len(placement["cues"]) == 1 else "s"))
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Finish the sound of a picture-locked reel.")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--voice", choices=["free", "auphonic"])
    ap.add_argument("--yes", action="store_true", help="the client said yes to the Auphonic plan")
    ap.add_argument("--video", help="the picture-locked video (default: the board's picture, else the newest master)")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main, detail=False))
