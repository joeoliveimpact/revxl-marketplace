"""Set up the Sound Board for one picture-locked reel.

  new_board.py --reel <reel> [--video <locked.mp4>] [--cues cues.json] [--stops stops.json] [--bed <bed file>]

Copies the sound library into the reel folder (sfx/ and beds/, so the board can play them), measures every sound,
computes the waveforms, and writes the board's config.json, waveforms.json and sfx_measured.json into
<paths.videos>/<reel>/. The board loads them from /videos/<reel>/<file>; open it at /editor/sound-board/?reel=<reel>
on the editor's board server.

Everything measured comes from the files themselves: durations and peaks are probed, because sound libraries are
not level matched and written tables go stale.
  --video   default: the newest work/renders/master-*.mp4. A video outside the reel folder is copied to
            media/locked.mp4 (the board can only play files inside the reel folder).
  --sfx / --beds   default: the workspace library, <paths.editor>/sound/ and <paths.editor>/sound/beds/.
            The client's own music library, <paths.editor>/music/ (music_pick.py), is added to the beds as well
            (a name that is in both is refused). Each bed row carries its catalogue entry (title, mood, origin,
            licence_ok, rights_confirmed) and suggest_entry_s: the TRACK position (s into the song) where its
            strongest section starts, for offset_s (never entry_s, the reel time the bed comes in).
  --cues    proposed cues: [{id, beat, short, why, time, candidates:[files]}] (propose more than should ship).
  --stops   proposed music stops: [{start_s, end_s, label}].
  --bed     a music bed to preset (a file name in the beds folder), at --bed-gain dB.
speech_spans (where the voice speaks, in the cut's time) comes from work/cut/tx-cut.json when the cut was transcribed.
voice_lufs is the picture's sound measured as bake.py measures voice.wav: the music level is set against it.
Each bed row's play_lufs is its loudness from suggest_entry_s for the reel's length (bake.py measures the bed the same way).
Each bed row's grid is its beat grid (music_fit.bed_grid, TRACK seconds), null when it has no steady beat; each library
row's peak_s is where its hit lands (measure_sfx), so the board can start the file that much before a cue's time.
"""
import argparse, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _media import decode, loudness, probe, find_picture, workspace, write_json, write_wav  # noqa: E402
import measure_sfx, make_waveforms, music_fit, music_pick  # noqa: E402


def copy_sounds(src, dst):
    n = 0
    dst.mkdir(parents=True, exist_ok=True)
    if src and Path(src).is_dir():
        for f in sorted(Path(src).iterdir()):
            if f.is_file() and f.suffix.lower() in measure_sfx.SOUND_EXT:
                shutil.copy2(f, dst / f.name)
                n += 1
    return n


def load_list(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else []


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Set up the Sound Board for a reel.")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--video", help="the picture-locked video")
    ap.add_argument("--sfx", help="folder of sound effects")
    ap.add_argument("--beds", help="folder of music beds")
    ap.add_argument("--name", default="Sound board", help="the name shown in the title and heading")
    ap.add_argument("--key", help="short project key that keeps two boards' browser storage apart (default: the reel)")
    ap.add_argument("--cues", help="JSON file: proposed cues")
    ap.add_argument("--stops", help="JSON file: proposed music stops [{start_s, end_s, label}]")
    ap.add_argument("--bed", help="a music bed to preset (file name in the beds folder)")
    ap.add_argument("--bed-gain", type=float, default=None, help="the preset bed's level, dB")
    ap.add_argument("--blurb", default="")
    a = ap.parse_args(argv)
    editor_dir, videos_dir = workspace()
    reel = videos_dir / a.reel
    if a.bed_gain is None:
        sys.path.insert(0, str(HERE.parents[1] / "_shared"))
        import saved_style
        gain = saved_style._get(saved_style.load(reel), "music.bed_gain_db")
        a.bed_gain = gain if saved_style._valid(gain, "number") else -18.0

    if not reel.is_dir():
        print("There is no reel folder named %s." % a.reel)
        return 2
    video = find_picture(reel, a.video)
    if not video or not video.is_file():
        print("Couldn't find the picture-locked video. Pass --video with it.")
        return 2
    try:
        rel = video.resolve().relative_to(reel.resolve()).as_posix()
    except ValueError:
        (reel / "media").mkdir(exist_ok=True)
        shutil.copy2(video, reel / "media" / "locked.mp4")
        rel = "media/locked.mp4"
    info = probe(reel / rel)
    dur = round(info["dur"], 3)
    print("Picture: %.3f s at %.3f fps" % (dur, info["fps"]))

    lib = editor_dir / "sound"
    n_sfx = copy_sounds(a.sfx or lib, reel / "sfx")
    pack_beds, music = Path(a.beds or lib / "beds"), editor_dir / "music"
    clash = sorted({f.name for f in music.glob("*")} & {f.name for f in pack_beds.glob("*")} if music.is_dir() else [])
    clash = [c for c in clash if c.lower().endswith(measure_sfx.SOUND_EXT)]
    if clash:
        print("The music library and the starter pack both have a track named %s. Rename the one in the music "
              "folder and run this again." % clash[0])
        return 1
    n_bed = copy_sounds(pack_beds, reel / "beds") + copy_sounds(music, reel / "beds")
    print("Copied %d sound effects and %d music beds." % (n_sfx, n_bed))
    if n_sfx == 0:
        print("No sound effects yet, so the board has nothing to pick from (the mix can still ship voice only).")

    m = measure_sfx.measure_dir(reel)
    make_waveforms.make(reel, reel / rel)
    library, beds = m["hits"], m["beds"]
    for b in beds:
        row = music_pick.lookup(editor_dir, b["file"])
        row.setdefault("origin", "own" if (music / b["file"]).is_file() else "pack")
        b.update(title=row.get("title") or Path(b["file"]).stem, mood=row.get("mood"), origin=row["origin"],
                 licence_ok=not music_pick.gaps(row), rights_confirmed=row.get("rights_confirmed") is True,
                 suggest_entry_s=music_fit.suggest_entry(decode(reel / "beds" / b["file"], 8000), 8000, dur))
        pl = music_fit.bed_loudness(reel / "beds" / b["file"], b["suggest_entry_s"],
                                    min(dur, (b["duration"] or 0) - b["suggest_entry_s"]))[0]
        b["play_lufs"] = round(pl, 2) if math.isfinite(pl) else None    # what the board sets the level against
        b["grid"] = music_fit.bed_grid(reel, b["file"])                   # null: the board's beat-sync is off for it

    cues = load_list(a.cues)
    for c in cues:
        c.setdefault("candidates", [])
        for cand in c["candidates"]:
            if not any(x["file"] == cand for x in library):
                print("Cue %s names a sound that isn't in the library: %s" % (c.get("id", "?"), cand))
                return 1
        if not (0.0 <= c.get("time", -1) <= dur):
            print("Cue %s is outside the picture (%s s)." % (c.get("id", "?"), c.get("time")))
            return 1

    cfg = {"board_name": a.name, "project_key": a.key or a.reel, "blurb": a.blurb,
           "picture": video.name, "picture_url": rel, "fps": round(info["fps"], 3), "dur": dur,
           "library": library, "beds": beds, "cues": cues}
    if a.stops:
        cfg["bed_stops"] = load_list(a.stops)
        for s in cfg["bed_stops"]:
            if not (0.0 <= s["start_s"] < s["end_s"] <= dur):
                print("A music stop is outside the picture: %s" % s)
                return 1
    if a.bed:
        if not any(b["file"] == a.bed for b in beds):
            print("The music bed %s isn't in the beds folder." % a.bed)
            return 1
        pre = next(b for b in beds if b["file"] == a.bed)
        cfg["bed_default"] = {"file": a.bed, "gain_db": a.bed_gain, "entry_s": 0, "exit_s": dur,
                              "offset_s": pre["suggest_entry_s"],
                              "fade_in_s": 0.5, "fade_out_s": 0.8, "duck_db": music_fit.DUCK_DB,
                              "carve": {"on": True, "strength": 0.8}}
    tmp = reel / "work" / "voice-lufs.tmp.wav"               # measured exactly as bake measures voice.wav
    voice = None
    try:
        voice = decode(reel / rel)
        write_wav(tmp, voice)
        v = loudness(tmp)[0]
        tmp.unlink()
    except RuntimeError:                                      # a picture with no sound: no voice to set music against
        v = float("nan")
    cfg["voice_lufs"] = v if math.isfinite(v) else None
    try:
        import carve
        # Preview uses the exact analysis at each stop of the strength slider.
        # The voice alone determines these curves; changing beds needs no new analysis.
        if voice is None:
            raise ValueError("No voice stem")
        samples = int(info["dur"] * 48000 + 0.5)
        voice = voice[:samples]
        if len(voice) < samples:
            import room_tone
            import numpy as np
            voice = np.vstack([voice, room_tone.fill(voice, samples - len(voice))])
        cfg["carve"] = {"profiles": {"%.2f" % (s / 100): carve.analyse(voice, 48000, s / 100)
                                     for s in range(25, 101, 5)}}
    except Exception:  # preview and bake both retain the dip when analysis is unavailable
        cfg["carve"] = None
        print("The music couldn't carve around the voice here, so it dips instead.")
    spans = music_fit.speech_spans(reel)
    if spans:
        cfg["speech_spans"] = spans
    write_json(reel / "config.json", cfg)

    print("Sound Board ready: %d cues proposed, %d sound effects, %d music beds." % (len(cues), len(library), len(beds)))
    print("Open it on the editor's board server at /editor/sound-board/?reel=%s" % a.reel)
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
