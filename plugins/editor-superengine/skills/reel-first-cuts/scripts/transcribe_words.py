#!/usr/bin/env python3
"""Stage 1 - word-timestamped transcript and edit map. The contract, implemented.

reel-first-cuts cuts on word edges, so a transcript without word timings is not a
transcript this pipeline can use. That failure has to be LOUD, not a quiet fallback
to sentence precision, which is exactly what produces the half-second boundary
errors Stage 3 exists to catch.

The engine is the one the doctor's machine test picked (state.json `engine`, TX-1):
Parakeet (parakeet_local.py, on the GPU or the CPU) by default; the faster-whisper
backup only where Parakeet can't install or the workspace language isn't English
(H-S1a-4). The backup always prints its plain warning, so Parakeet's absence is
never silent. The script re-runs itself in the editor's own Python, where the
engine lives. All workspaces share that one install (H-A2-1): when this
workspace's language needs the engine the install doesn't hold (an English
workspace after a Spanish one, say), the editor doctor re-picks and reinstalls
first, and its STATUS line says it is switching.

The chain transcribes the audio track probe.py chose (`audio_stream`), as 16 kHz
mono, and stores that track's `mean_loudness_db` in probe.json (S5's quiet-recording
gate reuses it). Three guards run on every transcript, raw or re-transcribed cut
(HF-5, hard rule; the numbers are the spec's, not tuned here):
  (a) silent tail: silencedetect at -35 dB / 0.6 s; when the clip ends with more
      than 0.8 s of silence, words starting over 0.4 s after the sound ends are
      dropped (the engine invented them)
  (b) near silence: mean loudness under -45 dB stops the run with a plain message
      that names the file's other audio tracks (VU-2)
  (c) a word with no time takes one from its neighbours, and a word with no
      length ends where the next later word starts (or where the audio ends)

--edit-map builds the verbatim edit map from the same words: align_words.py,
vocal_truth.py, then build_edit_map.py. The backup's words go in unchanged, so
`parakeet_start` (the cut anchor) is then the backup's start time.

Fixed by the contract for the backup (references/transcription-contract.md):
  * word_timestamps ON  - hard precondition
  * vad_filter      ON  - sequential decoding hallucinates whole sentences over
                          trailing silence; VAD is what suppresses it
  * vocabulary      absent entirely - a hotwords prompt can SILENTLY delete real
                          speech (946 chars measured down to 773, about 28 words,
                          no error and no gap in the output). A wrong name is
                          visible and fixable; missing speech is neither.

Derived from THIS machine, never inherited from another box's config:
  * device       cuda if a CUDA device is visible, else cpu
  * compute_type float16 on cuda, int8 on cpu - a memory compromise, not a
                 quality setting. Where memory allows, float16 beats int8_float16.

Batching (backup only) is OPT-IN (--batched N), off by default:
  * raw multi-take footage -> batched. Long trailing silences are where sequential
    invents sentences.
  * an already-cut file    -> sequential (the default). Measured on an approved cut,
    207 tokens both ways: batched-8 misheard the one trigger word the call to action
    depended on, where sequential got it right. Batching's accuracy cost is fully
    realised on a file that has almost no silence left to hallucinate over.

Usage
  python transcribe_words.py RAW.mp4 -o work/tx.json --probe work/probe.json --edit-map work/edit_map.json
  python transcribe_words.py CUT.mp4 -o work/tx-cut.json

Output JSON
  {text, segments:[{start,end,text}], words:[{i,word,start,end}], duration, model,
   device, batched, engine, audio_stream, mean_loudness_db, guards, _word_caveat}

Exit codes
  0 ok   1 bad input   2 no word timings in the output (hard fail)
  3 no engine on this computer   4 the track is nearly silent   5 an engine step failed
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

WORD_CAVEAT = ("ASR word ENDS run early (up to 0.54s measured) and word times are "
               "CONTIGUOUS, so they cannot locate silence. Use for identity and "
               "ordering; waveform-verify any cut point taken from them.")
TAIL_DB, TAIL_MIN_S, TAIL_LONG_S, TAIL_GRACE_S = -35, 0.6, 0.8, 0.4   # HF-5 (a)
QUIET_DB = -45.0                                                       # HF-5 (b)
CHILD = "EDITOR_SE_TX_CHILD"
DOCTOR = HERE.parents[1] / "editor-doctor" / "scripts" / "check_deps.py"


def pick_device(requested):
    """Resolve auto -> cuda/cpu by asking THIS machine, not a config file."""
    if requested != "auto":
        return requested
    try:
        import ctranslate2  # ships with faster-whisper
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def pick_precision(device, requested):
    """float16 on cuda, int8 on cpu. A memory compromise, not a quality setting -
    which is why it is derived here and never copied from another machine."""
    if requested:
        return requested
    return "float16" if device == "cuda" else "int8"


def transcribe(path, a):
    """The faster-whisper backup on a file path (decoded by PyAV)."""
    try:
        from faster_whisper import WhisperModel, BatchedInferencePipeline
    except ImportError:
        print("ERROR: faster-whisper is not installed in the editor's Python.", file=sys.stderr)
        print("       Run the editor doctor to repair the setup.", file=sys.stderr)
        sys.exit(3)

    device = pick_device(a.device)
    precision = pick_precision(device, a.compute_type)
    print("model %s | device %s | compute_type %s | batched %s"
          % (a.model, device, precision, a.batched or "off"))

    model = WhisperModel(getattr(a, "model_path", None) or a.model, device=device, compute_type=precision)
    # VAD and word timestamps are not exposed as flags on purpose - see the module
    # docstring. Turning either off breaks the contract this script exists to keep.
    kw = dict(language=a.language, word_timestamps=True, vad_filter=True)
    if a.batched:
        segs, info = BatchedInferencePipeline(model=model).transcribe(
            path, batch_size=a.batched, **kw)
    else:
        segs, info = model.transcribe(path, **kw)

    seg_list, words = [], []
    for s in segs:
        seg_list.append({"start": round(s.start, 2), "end": round(s.end, 2),
                         "text": s.text.strip()})
        for w in (s.words or []):
            words.append({"i": len(words), "word": w.word.strip(),
                          "start": round(w.start, 3), "end": round(w.end, 3),
                          "prob": round(w.probability, 4)})
    return {"text": " ".join(s["text"] for s in seg_list).strip(),
            "segments": seg_list,
            "words": words,
            "duration": round(info.duration, 2),
            "model": a.model,
            "device": device,
            "batched": a.batched or 0}


def parakeet(wav, out):
    """Parakeet in a child process (parakeet_local.py): {words, text, model, provider}."""
    run([sys.executable, HERE / "parakeet_local.py", wav, out], "Parakeet")
    d = json.loads(Path(out).read_text(encoding="utf-8"))
    return {"text": d["text"], "segments": [], "words": d["words"], "duration": wav_seconds(wav),
            "model": d["model"], "device": d["provider"], "batched": 0}


# ------------------------------------------------------------------- audio and guards
def ff(*args):
    return subprocess.run([str(x) for x in args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def run(cmd, what):
    p = subprocess.run([str(x) for x in cmd])
    if p.returncode:
        print("ERROR: %s stopped (exit %d); nothing after it ran." % (what, p.returncode), file=sys.stderr)
        sys.exit(5)


def wav_seconds(wav):
    with wave.open(str(wav)) as w:
        return round(w.getnframes() / w.getframerate(), 3)


def audio_tracks(src):
    p = ff("ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
           "-of", "csv=p=0", src)
    return len([x for x in p.stdout.splitlines() if x.strip()])


def extract(src, stream, wav):
    p = ff("ffmpeg", "-y", "-v", "error", "-i", src, "-map", "0:a:%d" % stream, "-vn",
           "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav)
    if p.returncode:
        print("ERROR: could not read audio track %d: %s" % (stream + 1, p.stderr.strip()[-300:]),
              file=sys.stderr)
        sys.exit(1)


def mean_loudness(wav):
    """The loudness reading (fix 8): ffmpeg volumedetect's mean, in dB. It logs at info."""
    m = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB",
                  ff("ffmpeg", "-hide_banner", "-nostats", "-i", wav, "-af", "volumedetect",
                     "-f", "null", "-").stderr)
    return -120.0 if not m or m.group(1) == "-inf" else float(m.group(1))


def quiet_message(db, stream, tracks):
    """HF-5 (b) and VU-2: the plain stop, naming the file's other tracks (1-based for people)."""
    msg = ("This recording is nearly silent on audio track %d (average %.1f dB; speech needs "
           "about %.0f dB or louder), so transcription stopped." % (stream + 1, db, QUIET_DB))
    others = [n for n in range(tracks) if n != stream]
    if others:
        msg += (" The file has other audio: %s. If the voice is there, run the probe again with %s."
                % (", ".join("track %d" % (n + 1) for n in others),
                   " or ".join("--audio-stream %d" % n for n in others)))
    return msg


def sound_end(wav, duration):
    """HF-5 (a): where the sound ends, when the clip ends in more than 0.8 s of silence; else None."""
    err = ff("ffmpeg", "-hide_banner", "-nostats", "-i", wav, "-af",
             "silencedetect=noise=%ddB:d=%s" % (TAIL_DB, TAIL_MIN_S), "-f", "null", "-").stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", err)]
    if not starts:
        return None
    last = max(0.0, starts[-1])
    open_tail = len(ends) < len(starts) or ends[-1] >= duration - 0.1
    return last if open_tail and duration - last > TAIL_LONG_S else None


def trim_tail(words, end):
    """Drop words that start more than 0.4 s after the sound ended. Returns (kept, dropped)."""
    if end is None:
        return words, []
    kept = [w for w in words if w["start"] <= end + TAIL_GRACE_S]
    return kept, [w for w in words if w["start"] > end + TAIL_GRACE_S]


def _timed(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def fill_untimed(words, duration):
    """HF-5 (c): a run of untimed words shares the span between its timed neighbours; a word whose
    end is not after its start (Parakeet's one-token last word) ends at the next later start."""
    n, filled, k = len(words), 0, 0
    while k < n:
        w = words[k]
        if _timed(w.get("start")) and _timed(w.get("end")):
            k += 1
            continue
        j = k
        while j < n and not (_timed(words[j].get("start")) and _timed(words[j].get("end"))):
            j += 1
        lo = words[k - 1]["end"] if k else 0.0
        hi = words[j]["start"] if j < n else duration
        hi = max(hi, lo)
        step = (hi - lo) / (j - k)
        for m in range(k, j):
            words[m].update(start=round(lo + step * (m - k), 3), end=round(lo + step * (m - k + 1), 3),
                            filled=True)
            filled += 1
        k = j
    for k, w in enumerate(words):
        if w["end"] <= w["start"]:
            later = [x["start"] for x in words[k + 1:] if x["start"] > w["start"]]
            w.update(end=round(later[0] if later else max(duration, w["start"]), 3), filled=True)
            filled += 1
    return filled


def build_edit_map(wav, tx, out):
    """align_words -> vocal_truth -> build_edit_map, all on the same words and 16 kHz track."""
    if not rt.align_supported():
        print("Word alignment isn't available on this Mac, so no edit map was built.")
        return
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    aligned, vt = Path(tx).parent / "aligned.json", Path(tx).parent / "vocal_truth.json"
    run([sys.executable, HERE / "align_words.py", wav, tx, aligned], "Word alignment")
    run([sys.executable, HERE / "vocal_truth.py", wav, tx, vt], "The vocal scan")
    run([sys.executable, HERE / "build_edit_map.py", wav, aligned, vt, out], "The edit map")


def route(state, language, vpy):
    """H-S1a-4 + H-A2-1: the doctor's own re-pick for this workspace's language; when that engine isn't the one
    the shared install holds, the doctor switches it (STATUS engine-switch) before anything is transcribed."""
    held = state.get("python_packages", {}).get("engine") or state.get("engine")
    try:
        want = rt.decide_engine(state, language)[0]
    except RuntimeError:
        return 0
    if want == held or want not in rt.ENGINES:
        return 0
    print("This workspace needs the %s transcriber but the editor holds %s, so the editor doctor is switching "
          "it now (a one-time reinstall of about 1-3 GB)." % (want, held), flush=True)
    if subprocess.run([vpy, "-X", "utf8", "-I", str(DOCTOR)], env=dict(os.environ)).returncode:
        print("The transcriber switch didn't finish, so nothing was transcribed. The doctor's lines above say "
              "what to fix.", file=sys.stderr)
        return 3
    return 0


# ---------------------------------------------------------------------------- selftest
def selftest():
    assert pick_device("cpu") == "cpu" and pick_device("cuda") == "cuda"
    assert pick_precision("cuda", None) == "float16"
    assert pick_precision("cpu", None) == "int8"
    assert pick_precision("cuda", "int8_float16") == "int8_float16"
    w = [{"word": "a", "start": 1.0, "end": 1.5}, {"word": "b", "start": None, "end": None},
         {"word": "c", "start": float("nan"), "end": 2.0}, {"word": "d", "start": 2.5, "end": 3.0},
         {"word": "e", "start": None, "end": None}]
    assert fill_untimed(w, 4.0) == 3
    assert [(x["start"], x["end"]) for x in w] == [(1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 4.0)], w
    z = [{"start": 1.0, "end": 1.0}, {"start": 1.0, "end": 1.2}, {"start": 2.0, "end": 2.4},
         {"start": 3.0, "end": 3.0}]
    assert fill_untimed(z, 3.5) == 2 and [x["end"] for x in z] == [2.0, 1.2, 2.4, 3.5], z
    kept, dropped = trim_tail([{"start": 1.0}, {"start": 5.3}, {"start": 5.5}], 5.0)
    assert [x["start"] for x in kept] == [1.0, 5.3] and [x["start"] for x in dropped] == [5.5]
    assert trim_tail([{"start": 9.0}], None) == ([{"start": 9.0}], [])
    assert "track 2" in quiet_message(-60.0, 0, 2) and "--audio-stream 1" in quiet_message(-60.0, 0, 2)
    assert "other audio" not in quiet_message(-60.0, 0, 1)
    print("selftest ok")


def main():
    ensure_utf8_output()
    p = argparse.ArgumentParser(
        description="Word-timestamped transcript and edit map for reel-first-cuts Stage 1.")
    p.add_argument("input", nargs="?", help="audio or video file")
    p.add_argument("-o", "--out", help="output JSON (default <input>.words.json)")
    p.add_argument("--probe", help="work/probe.json: its audio_stream is transcribed and "
                                   "mean_loudness_db is stored in it")
    p.add_argument("--edit-map", dest="edit_map", help="also build the edit map here")
    p.add_argument("--model", default="large-v3-turbo", help="backup engine only")
    p.add_argument("--device", default="auto", choices=("auto", "cuda", "cpu"), help="backup engine only")
    p.add_argument("--compute-type", dest="compute_type",
                   help="backup engine only; default: float16 on cuda, int8 on cpu")
    p.add_argument("--batched", type=int, metavar="N", default=0,
                   help="backup engine only: batch size for raw multi-take footage; OFF by default")
    p.add_argument("--selftest", action="store_true", help="check the derivations and guards")
    a = p.parse_args()

    if a.selftest:
        selftest()
        return 0
    if not a.input:
        p.error("input is required")
    src = Path(a.input)
    if not src.exists():
        print("ERROR: no such file: %s" % src, file=sys.stderr)
        return 1

    state = rt.load_state()
    engine = state.get("engine")
    if not engine:
        print("Transcription isn't set up on this computer yet. Run the editor doctor first.", file=sys.stderr)
        return 3
    if engine == "none":
        print(state.get("engine_reason") or "This computer has no transcriber.", file=sys.stderr)
        return 3
    if not os.environ.get(CHILD):          # run in the editor's Python, where the engine is
        vpy = rt.tool("python")
        if not Path(vpy).exists():
            print("The editor's Python is missing. Run the editor doctor to repair the setup.", file=sys.stderr)
            return 3
        rc = route(state, rt.read_config().get("language"), vpy)
        if rc:
            return rc
        env = rt.python_env()
        env.update({CHILD: "1", "PYTHONUNBUFFERED": "1"})
        return subprocess.run([vpy, str(Path(__file__).resolve())] + sys.argv[1:], env=env).returncode

    language = rt.read_config().get("language")
    if engine.startswith("parakeet") and not rt.is_english(language):
        print("The workspace language is %s, and Parakeet understands English only. Run the editor "
              "doctor so it sets up the multilingual transcriber." % language, file=sys.stderr)
        return 3
    for t in ("ffmpeg", "ffprobe"):
        if not shutil.which(t):
            print("ERROR: %s is missing. Run the editor doctor to repair the setup." % t, file=sys.stderr)
            return 3

    out = Path(a.out) if a.out else src.with_suffix(src.suffix + ".words.json")
    if out.is_dir():
        out = out / (src.name + ".words.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    probe, stream = None, 0
    if a.probe:
        probe = json.loads(Path(a.probe).read_text(encoding="utf-8"))
        if Path(probe.get("input", "")).resolve() != src.resolve():
            print("ERROR: %s describes %s, not %s." % (a.probe, probe.get("input"), src), file=sys.stderr)
            return 1
        stream = int(probe.get("audio_stream", 0))

    wav = out.with_name(out.stem + ".16k.wav")
    extract(src, stream, wav)
    db = mean_loudness(wav)
    if probe is not None:
        probe["mean_loudness_db"] = round(db, 1)
        Path(a.probe).write_text(json.dumps(probe, indent=1), encoding="utf-8")
    print("audio track %d | mean loudness %.1f dB" % (stream + 1, db))
    if db < QUIET_DB:
        print(quiet_message(db, stream, audio_tracks(src)), file=sys.stderr)
        return 4

    if engine.startswith("parakeet"):
        print("engine %s: Parakeet" % engine)
        d = parakeet(wav, out.with_name(out.stem + ".parakeet.json"))
    else:
        print(rt.BACKUP_WARNING)
        print("Parakeet isn't set up on this computer (%s)." % (state.get("engine_reason") or engine))
        a.language = rt.lang_key(language)
        a.model_path = None if a.model != "large-v3-turbo" else rt.model_dir("faster-whisper")
        d = transcribe(str(wav), a)
    d.update(engine=engine, audio_stream=stream, mean_loudness_db=round(db, 1))

    filled = fill_untimed(d["words"], d["duration"])
    kept, dropped = trim_tail(d["words"], sound_end(wav, d["duration"]))
    for i, w in enumerate(kept):
        w["i"] = i
    d["words"] = kept
    d["guards"] = {"untimed_filled": filled, "tail_dropped": [w["word"] for w in dropped]}
    d["_word_caveat"] = WORD_CAVEAT
    if filled:
        print("gave %d untimed word(s) a time from their neighbours" % filled)
    if dropped:
        print("dropped %d word(s) the engine heard in the silent tail: %s"
              % (len(dropped), " ".join(w["word"] for w in dropped)))

    if not d["words"]:
        print("", file=sys.stderr)
        print("HARD FAIL: the transcript has NO word timings.", file=sys.stderr)
        print("  This pipeline cuts on word edges. Sentence precision silently",
              file=sys.stderr)
        print("  produces the half-second boundary errors Stage 3 exists to catch,",
              file=sys.stderr)
        print("  so nothing was written. Fix the backend, do not proceed.",
              file=sys.stderr)
        return 2

    out.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("words %d | segments %d | duration %.2fs" %
          (len(d["words"]), len(d["segments"]), d["duration"]))
    print("wrote %s" % out)
    if a.edit_map:
        build_edit_map(wav, out, a.edit_map)
    return 0


if __name__ == "__main__":
    sys.exit(main())
