#!/usr/bin/env python3
"""Runs INSIDE the editor's Python (onnx-asr). Called by transcribe_words.py when the engine is Parakeet.

    python parakeet_local.py <wav16k-mono> <out.json> [quantization]
    python parakeet_local.py --batch <wavs.json> <out.json> [quantization]

Writes the fleet JSON shape: {"text", "words":[{"i","word","start","end"}], "segments":[], ...}.
--batch (repeat_check.py's deep mode, H-M4) loads the model ONCE for a JSON list of wav paths and writes
{"results": [{"wav", "text", "words"}], "loads": 1, ...}.
Parakeet TDT emits token START times; a word's end is the next word's start (contiguous),
so ends cannot locate silence (same caveat as Whisper's). Model: nemo-parakeet-tdt-0.6b-v2,
int8 by default (measured 09.09.26: +2.6 GB GPU, .970 vs Tella on a 253 s take, better than
fp32's .963 at +4.7 GB).
"""
import json, sys, time
from pathlib import Path

import onnx_asr
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

ensure_utf8_output()

batch = sys.argv[1] == "--batch"
args = sys.argv[2:] if batch else sys.argv[1:]
wav, out = args[0], args[1]
quant = args[2] if len(args) > 2 else "int8"
name = "nemo-parakeet-tdt-0.6b-v2"
local = rt.model_dir("parakeet")   # the installer's hash-checked copy; nothing downloads here
want = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
t0 = time.time()
try:
    model = onnx_asr.load_model(name, local, quantization=quant, providers=want)
    provider = "cuda" if want[0] == "CUDAExecutionProvider" else "cpu"
except Exception as e:  # cuDNN missing, no GPU: CPU is ~25 s per 4 min, still fine
    if want[0] != "CUDAExecutionProvider":
        raise
    print(f"[parakeet] CUDA provider failed ({type(e).__name__}); using CPU", file=sys.stderr)
    model = onnx_asr.load_model(name, local, quantization=quant, providers=["CPUExecutionProvider"])
    provider = "cpu"
model = model.with_timestamps()
load = time.time() - t0


def recognize(wav):
    r = model.recognize(wav)
    words, cur, cs, lt = [], "", None, None
    for tok, t in zip(r.tokens, r.timestamps):
        piece = tok.replace("▁", " ")
        if piece.startswith(" ") or cur == "":
            if cur.strip():
                words.append({"word": cur.strip(), "start": round(cs, 3), "end": None})
            cur, cs = piece, t
        else:
            cur += piece
        lt = t
    if cur.strip():
        words.append({"word": cur.strip(), "start": round(cs, 3), "end": None})
    for i in range(len(words)):
        words[i]["i"] = i
        words[i]["end"] = words[i + 1]["start"] if i + 1 < len(words) else round(lt, 3)
    text = r.text.strip() if getattr(r, "text", None) else " ".join(w["word"] for w in words)
    return text, words


t1 = time.time()
if batch:
    wavs = json.loads(Path(wav).read_text(encoding="utf-8"))
    results = [dict(zip(("text", "words"), recognize(w)), wav=w) for w in wavs]
    el = time.time() - t1
    json.dump({"results": results, "model": name, "quantization": quant, "provider": provider, "loads": 1,
               "load_s": round(load, 1), "elapsed": round(el, 1)},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[parakeet] {name} {quant} on {provider}: load {load:.1f}s once for {len(wavs)} file(s), "
          f"recognize {el:.1f}s", file=sys.stderr)
    sys.exit(0)
text, words = recognize(wav)
el = time.time() - t1
json.dump({"text": text, "words": words, "segments": [],
           "model": name, "quantization": quant, "provider": provider,
           "load_s": round(load, 1), "elapsed": round(el, 1)},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[parakeet] {name} {quant} on {provider}: load {load:.1f}s, recognize {el:.1f}s, {len(words)} words", file=sys.stderr)
