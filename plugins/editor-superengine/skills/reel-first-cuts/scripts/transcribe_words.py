#!/usr/bin/env python3
"""Stage 1 - word-timestamped transcript. The contract, implemented.

reel-first-cuts cuts on word edges, so a transcript without word timings is not a
transcript this pipeline can use. That failure has to be LOUD, not a quiet fallback
to sentence precision, which is exactly what produces the half-second boundary
errors Stage 3 exists to catch.

Fixed by the contract (references/transcription-contract.md), not configurable here:
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

Batching is OPT-IN (--batched N), off by default:
  * raw multi-take footage -> batched. Long trailing silences are where sequential
    invents sentences.
  * an already-cut file    -> sequential (the default). Measured on an approved cut,
    207 tokens both ways: batched-8 misheard the one trigger word the call to action
    depended on, where sequential got it right. Batching's accuracy cost is fully
    realised on a file that has almost no silence left to hallucinate over.

Usage
  python transcribe_words.py RAW.mp4
  python transcribe_words.py RAW.mp4 -o work/tx.json --batched 8

Output JSON
  {text, segments:[{start,end,text}], words:[{i,word,start,end,prob}],
   duration, model, device, batched, _word_caveat}

Exit codes
  0 ok   2 no word timings in the output (hard fail)   3 faster-whisper missing
"""
import argparse
import json
import sys
from pathlib import Path

WORD_CAVEAT = ("ASR word ENDS run early (up to 0.54s measured) and word times are "
               "CONTIGUOUS, so they cannot locate silence. Use for identity and "
               "ordering; waveform-verify any cut point taken from them.")


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
    try:
        from faster_whisper import WhisperModel, BatchedInferencePipeline
    except ImportError:
        print("ERROR: faster-whisper is not installed.", file=sys.stderr)
        print("       pip install faster-whisper", file=sys.stderr)
        print("       Or supply your own word-timestamped JSON; see "
              "references/transcription-contract.md", file=sys.stderr)
        sys.exit(3)

    device = pick_device(a.device)
    precision = pick_precision(device, a.compute_type)
    print("model %s | device %s | compute_type %s | batched %s"
          % (a.model, device, precision, a.batched or "off"))

    model = WhisperModel(a.model, device=device, compute_type=precision)
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
            "batched": a.batched or 0,
            "_word_caveat": WORD_CAVEAT}


def selftest():
    assert pick_device("cpu") == "cpu" and pick_device("cuda") == "cuda"
    assert pick_precision("cuda", None) == "float16"
    assert pick_precision("cpu", None) == "int8"
    assert pick_precision("cuda", "int8_float16") == "int8_float16"
    print("selftest ok")


def main():
    p = argparse.ArgumentParser(
        description="Word-timestamped transcript for reel-first-cuts Stage 1.")
    p.add_argument("input", nargs="?", help="audio or video file")
    p.add_argument("-o", "--out", help="output JSON (default <input>.words.json)")
    p.add_argument("--model", default="large-v3-turbo")
    p.add_argument("--device", default="auto", choices=("auto", "cuda", "cpu"))
    p.add_argument("--compute-type", dest="compute_type",
                   help="default: float16 on cuda, int8 on cpu")
    p.add_argument("--language", default="en")
    p.add_argument("--batched", type=int, metavar="N", default=0,
                   help="batch size for raw multi-take footage; OFF by default")
    p.add_argument("--selftest", action="store_true", help="check the derivations")
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
    out = Path(a.out) if a.out else src.with_suffix(src.suffix + ".words.json")
    if out.is_dir():
        out = out / (src.name + ".words.json")

    d = transcribe(str(src), a)

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

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("words %d | segments %d | duration %.2fs" %
          (len(d["words"]), len(d["segments"]), d["duration"]))
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
