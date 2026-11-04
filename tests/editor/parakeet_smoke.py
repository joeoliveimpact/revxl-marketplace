"""A real Parakeet run on a short WAV from the installed state folder: prints one JSON line with the
word count, the first words and the execution provider each onnxruntime session ended up on.
usage: <venv python> parakeet_smoke.py <wav16k-mono>
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402


def sessions(obj, ort, seen=None, depth=0):
    seen = set() if seen is None else seen
    if id(obj) in seen or depth > 5:
        return []
    seen.add(id(obj))
    if isinstance(obj, ort.InferenceSession):
        return [obj]
    kids = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, (list, tuple)) else \
        getattr(obj, "__dict__", {}).values()
    return [s for k in kids for s in sessions(k, ort, seen, depth + 1)]


def main():
    ensure_utf8_output()
    import onnx_asr
    import onnxruntime as ort
    avail = ort.get_available_providers()
    want = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in avail]
    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", rt.model_dir("parakeet"),
                                quantization="int8", providers=want)
    found = sessions(model, ort)
    r = model.with_timestamps().recognize(sys.argv[1])
    words = "".join(r.tokens).replace("▁", " ").split()
    print(json.dumps({"words": len(words), "first": words[:8], "available": avail,
                      "providers": sorted({s.get_providers()[0] for s in found}), "sessions": len(found)},
                     ensure_ascii=False))
    return 0 if words and found else 1


if __name__ == "__main__":
    sys.exit(main())
