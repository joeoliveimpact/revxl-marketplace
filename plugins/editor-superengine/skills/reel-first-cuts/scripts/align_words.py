"""CTC forced alignment of a Parakeet word map to its audio with facebook/wav2vec2-base-960h (Apache-2.0).

usage: python align_words.py <wav16k-mono-s16> <parakeet-words.json> <out.json>
           [--star none|auto|<logprob>] [--inject-fake WORD@INDEX] [--chunk-s 400]
           [--hyp <vocal_truth.json>] [--hyp-word uh] [--flag-thresh auto|<mean-logprob>]

Gives every word a REAL start and end at 20 ms resolution (Parakeet's are token starts on an 80 ms grid with
synthetic ends = next word's start). Pure numpy Viterbi over the CTC lattice; no torchaudio, no new deps.
Runs in the editor's own Python (its installer puts torch + transformers there); nothing installs at run time.

Normalisation to the 960h vocab (UPPERCASE letters, apostrophe, '|' delimiter, no digits): hyphens split into
several CTC words under ONE map id; digits are spelled out by a small built-in; anything else is dropped from the
alignment string but the original token is kept on the record. Zero <unk> ids is asserted.

Two passes: words whose mean per-character log-prob falls under the flag threshold (auto: calibrated from this
file's own distribution) are treated as not-in-the-audio, kept on the record with status "unresolved" and their
Parakeet times, and removed from the lattice before a second pass so they cannot pull their neighbours.

Ids are the Parakeet map index (w_0007), never the list position, so inserting a hypothesis (h_*) or a fake (f_*)
renames nothing. Entries whose word starts with "[" (acoustic events) are never aligned.

Star column (--star): an extra "anything" emission appended at inference and a star token between every pair of
words. Measured 09.11.26: no effect on filler swallowing. Kept as an experiment flag.

ponytail: single full-file pass up to --chunk-s (4.56 GB VRAM measured on 253 s); longer files are chunked with
a 2 s overlap and spliced at the overlap midpoint (seam jitter measured at 1 frame).
"""
import json, re, sys, time, wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

SR = 16000
STRIDE, WIN = 320, 400          # wav2vec2-base conv stack: 320-sample stride, 400-sample receptive window
FRAME_S = STRIDE / SR           # exactly 0.02 s
NEG = -1e30
ONES = "ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN FOURTEEN FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN".split()
TENS = "_ _ TWENTY THIRTY FORTY FIFTY SIXTY SEVENTY EIGHTY NINETY".split()


def n_frames(n_samples: int) -> int:
    return (n_samples - WIN) // STRIDE + 1


def num_words(n: int) -> str:
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + " HUNDRED" + ("" if n % 100 == 0 else " " + num_words(n % 100))
    if n < 1_000_000: return num_words(n // 1000) + " THOUSAND" + ("" if n % 1000 == 0 else " " + num_words(n % 1000))
    if n < 1_000_000_000: return num_words(n // 1_000_000) + " MILLION" + ("" if n % 1_000_000 == 0 else " " + num_words(n % 1_000_000))
    if n < 1_000_000_000_000: return num_words(n // 1_000_000_000) + " BILLION" + ("" if n % 1_000_000_000 == 0 else " " + num_words(n % 1_000_000_000))
    return " ".join(ONES[int(d)] for d in str(n))  # ponytail: digit-by-digit from a trillion up


def spell(tok: str) -> str:
    """'10K' -> ' TEN K', '6' -> ' SIX ', '2024' -> ' TWENTY TWENTY FOUR ', '3.5' -> ' THREE POINT FIVE ',
    '3.14' -> ' THREE POINT ONE FOUR ', '0.05' -> ' ZERO POINT ZERO FIVE '.
    The spelled numeral is padded with spaces so an abutting letter ('10K') becomes its own CTC word (R4-01)."""
    def rep(m):
        s = m.group(0)
        grouped = "," in s
        s = s.replace(",", "")  # '1,000' is one numeral, ONE THOUSAND (R6-01). ponytail: malformed grouping ('1,00') still splits
        if "." in s:  # fraction digits are read one by one, leading zeros kept (R5-01)
            i, f = s.split(".")
            return " " + num_words(int(i)) + " POINT " + " ".join(ONES[int(d)] for d in f) + " "
        n = int(s)
        if 1900 <= n <= 2099 and len(s) == 4 and not grouped:
            lo = n % 100
            return " " + num_words(n // 100) + " " + ("HUNDRED" if lo == 0 else ("OH " + ONES[lo]) if lo < 10 else num_words(lo)) + " "
        return " " + num_words(n) + " "
    return re.sub(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", rep, tok)


def normalise(word: str) -> list:
    t = word.strip().replace("’", "'").replace("‘", "'").upper()
    t = spell(t).replace("-", " ").replace("/", " ")
    return [p for p in (re.sub(r"[^A-Z']", "", x) for x in t.split()) if p]


def load_wav(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2, "need 16 kHz mono s16"
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0


def emissions(audio, chunk_s: float):
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h").to(dev).eval()
    vocab = proc.tokenizer.get_vocab()

    def run(x):
        inp = proc(x, sampling_rate=SR, return_tensors="pt").input_values.to(dev)
        with torch.no_grad():
            return torch.log_softmax(model(inp).logits[0], -1).float().cpu().numpy()

    step = max(1, int(chunk_s * SR) // STRIDE) * STRIDE      # integer samples, stride-aligned (R1)
    ov = (2 * SR // STRIDE) * STRIDE
    if len(audio) <= step + ov:
        return run(audio), vocab, dev
    # Chunked: every global frame is emitted exactly once; the last chunk runs to EOF and ends the loop (R2-01).
    out, pos = [], 0
    while True:
        last = pos + step + ov >= len(audio)
        seg = audio[pos:] if last else audio[pos: pos + step + ov]
        e = run(seg)
        lo = 0 if pos == 0 else n_frames(ov // 2)
        hi = e.shape[0] if last else n_frames(step + ov // 2)
        out.append(e[lo:hi])
        if last: break
        pos += step
    return np.concatenate(out), vocab, dev


def viterbi(logp, tokens, blank):
    """CTC forced alignment. Returns per-token (start_frame, end_frame, mean_logprob). Raises if infeasible (R3)."""
    if not tokens:
        return []  # nothing to align (R3-01)
    T = logp.shape[0]
    need = len(tokens) + sum(1 for a, b in zip(tokens, tokens[1:]) if a == b)
    if T < need:
        raise ValueError(f"CTC infeasible: {need} frames needed (incl. repeats), {T} available")
    S = 2 * len(tokens) + 1
    lab = np.full(S, blank, dtype=np.int64); lab[1::2] = tokens
    skip = np.zeros(S, dtype=bool)
    skip[3::2] = lab[3::2] != lab[1:-2:2]
    dp = np.full(S, NEG, dtype=np.float64); dp[0] = logp[0, lab[0]]
    if S > 1: dp[1] = logp[0, lab[1]]
    back = np.zeros((T, S), dtype=np.int8)
    for t in range(1, T):
        c1 = np.concatenate(([NEG], dp[:-1]))
        c2 = np.concatenate(([NEG, NEG], dp[:-2])); c2[~skip] = NEG
        stacked = np.stack([dp, c1, c2])
        back[t] = stacked.argmax(0)
        dp = stacked.max(0) + logp[t, lab]
    s = S - 1 if dp[S - 1] >= dp[S - 2] else S - 2
    if dp[s] <= NEG / 2:
        raise ValueError("CTC terminal state unreachable")
    path = np.empty(T, dtype=np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= int(back[t, s])
    spans = []
    for k, tok in enumerate(tokens):
        fr = np.flatnonzero(path == 2 * k + 1)
        if not len(fr):
            raise ValueError(f"token {k} never visited")
        spans.append((int(fr[0]), int(fr[-1]), float(logp[fr, tok].mean())))
    return spans


def build_tokens(entries, vocab, star_id):
    """entries: list of dicts with 'parts' (CTC words). Returns tokens and (entry index, is_letter) owners."""
    delim = vocab["|"]
    toks, owner = [], []
    for ei, e in enumerate(entries):
        if ei > 0:
            toks.append(delim); owner.append((ei, False))
            if star_id is not None: toks.append(star_id); owner.append((ei, False))
        for pi, p in enumerate(e["parts"]):
            if pi > 0: toks.append(delim); owner.append((ei, False))
            for ch in p:
                toks.append(vocab[ch]); owner.append((ei, True))
    return toks, owner


def align(entries, logp, vocab, blank, star_id):
    toks, owner = build_tokens(entries, vocab, star_id)
    assert vocab["<unk>"] not in toks, "<unk> in transcript tokens"
    spans = viterbi(logp, toks, blank)
    per = {}
    for (ei, is_letter), (s, e, sc) in zip(owner, spans):
        if not is_letter: continue
        d = per.setdefault(ei, {"s": s, "e": e, "chars": []})
        d["s"] = min(d["s"], s); d["e"] = max(d["e"], e); d["chars"].append(sc)
    return per, len(toks)


def main():
    ensure_utf8_output()
    a = sys.argv[1:]
    wav, pk, out = a[0], a[1], a[2]
    opt = {"--star": "none", "--inject-fake": None, "--chunk-s": "400", "--hyp": None, "--hyp-word": "uh", "--flag-thresh": "auto"}
    for i, x in enumerate(a):
        if x in opt: opt[x] = a[i + 1]
    audio = load_wav(wav); dur = len(audio) / SR
    src = json.load(open(pk, encoding="utf-8"))["words"]

    # records: real words keep the Parakeet index as identity (R7); events are never aligned (R5)
    recs = []
    for i, w in enumerate(src):
        if str(w.get("word", "")).strip().startswith("["): continue
        recs.append({"id": f"w_{i:04d}", "word": w["word"], "parakeet_start": w.get("start"), "parakeet_end": w.get("end"),
                     "parts": normalise(w["word"]), "kind": "word", "_t": w.get("start", 0.0)})
    if opt["--hyp"]:
        vt = json.load(open(opt["--hyp"], encoding="utf-8"))
        for k, isl in enumerate(x for x in (vt.get("items") or vt.get("words") or []) if x.get("word") == "[vocal]"):
            recs.append({"id": f"h_{k:03d}", "word": opt["--hyp-word"], "parakeet_start": isl["start"], "parakeet_end": isl["end"],
                         "parts": normalise(opt["--hyp-word"]), "kind": "hyp", "_t": isl["start"] + 1e-6})
    if opt["--inject-fake"]:
        fw, idx = opt["--inject-fake"].split("@"); idx = int(idx)
        t = src[idx]["start"]
        recs.append({"id": "f_000", "word": fw, "parakeet_start": t, "parakeet_end": t, "parts": normalise(fw), "kind": "fake", "_t": t - 1e-6,
                     "insert_before": f"w_{idx:04d}", "insert_after": (f"w_{idx-1:04d}" if idx > 0 else None)})  # identity for the proof (R4-02)
    recs.sort(key=lambda r: r["_t"])
    all_recs = recs
    recs = [r for r in all_recs if r["parts"]]          # alignable subset; the rest stay on the record as "unaligned" (R2-02)
    for r in all_recs:
        r["score_mean"] = r["score_min"] = None; r["_span"] = None

    t0 = time.time()
    logp, vocab, dev = emissions(audio, float(opt["--chunk-s"]))
    T = logp.shape[0]
    blank = vocab["<pad>"]
    star_id = None
    if opt["--star"] != "none":
        sv = float(np.percentile(logp.max(-1), 50)) - 1.0 if opt["--star"] == "auto" else float(opt["--star"])
        logp = np.concatenate([logp, np.full((T, 1), sv, dtype=np.float32)], 1); star_id = logp.shape[1] - 1

    # pass 1
    ntok = 0
    if recs:
        per, ntok = align(recs, logp, vocab, blank, star_id)
        for ei, r in enumerate(recs):
            d = per.get(ei)
            r["score_mean"] = round(float(np.mean(d["chars"])), 3) if d else None
            r["score_min"] = round(float(np.min(d["chars"])), 3) if d else None
            r["_span"] = (d["s"], d["e"]) if d else None
    # Calibration uses every word-like record, fakes included, exactly as a real hallucination would be (R2-03).
    cal = [r for r in recs if r["kind"] in ("word", "fake") and r["score_min"] is not None]
    real_means = np.array([r["score_mean"] for r in cal] or [0.0])
    real_mins = np.array([r["score_min"] for r in cal] or [0.0])
    FIXED_FLOOR = -11.5   # lowest real-word min observed across both takes of a test reel (-11.03) minus 0.5
    if opt["--flag-thresh"] == "auto":
        # Per-file: 3 log-units under the 1st percentile of the MIN per-character log-prob, but never looser than
        # FIXED_FLOOR, so a short transcript (where one hallucination IS the 1st percentile) still flags it.
        # Measured 09.11.26 (both takes): neither the mean score nor greedy-decode letter support separates a fake
        # from a badly-said real word; only an extreme min does. Detection limit: catches gross hallucinations
        # (an injected 8-letter word scored -12.2 vs a real floor of -9.5 / -11.0); a short fake will pass, and a
        # hallucination whose min sits above -11.5 will pass. ponytail: a ceiling of this model, not a tuning knob.
        thresh = max(float(np.percentile(real_mins, 1)) - 3.0, FIXED_FLOOR)
    else:
        thresh = float(opt["--flag-thresh"])
    flagged = [r for r in recs if r["kind"] in ("word", "fake") and r["score_min"] is not None and r["score_min"] < thresh
               and sum(len(p) for p in r["parts"]) >= 3]

    # pass 2 without flagged words (R2). First-pass scores are kept as *_p1 (they explain the flagging);
    # the published score_mean / score_min always describe the published span (R3-02).
    passes = 1
    for r in recs:
        r["score_mean_p1"], r["score_min_p1"] = r["score_mean"], r["score_min"]
    if flagged:
        keep = [r for r in recs if r not in flagged]
        passes = 2
        if keep:  # all-flagged: nothing left to align, every record is emitted as unresolved (R3-01)
            per2, _ = align(keep, logp, vocab, blank, star_id)
            for ei, r in enumerate(keep):
                d = per2.get(ei)
                r["_span"] = (d["s"], d["e"]) if d else None
                r["score_mean"] = round(float(np.mean(d["chars"])), 3) if d else None
                r["score_min"] = round(float(np.min(d["chars"])), 3) if d else None

    res = []
    for r in all_recs:
        is_flag = r in flagged
        s = r["_span"]
        res.append({"id": r["id"], "word": r["word"], "kind": r["kind"],
                    "parakeet_start": r["parakeet_start"], "parakeet_end": r["parakeet_end"],
                    "start": r["parakeet_start"] if is_flag or s is None else round(s[0] * FRAME_S, 3),
                    "end": r["parakeet_end"] if is_flag or s is None else round((s[1] + 1) * FRAME_S, 3),
                    "status": "unresolved" if is_flag else ("unaligned" if s is None else "aligned"),
                    "score_mean": r["score_mean"], "score_min": r["score_min"],
                    "score_mean_p1": r.get("score_mean_p1"), "score_min_p1": r.get("score_min_p1"), "ctc_words": r["parts"],
                    **({"insert_before": r["insert_before"], "insert_after": r["insert_after"]} if r["kind"] == "fake" else {})})
    meta = {"model": "facebook/wav2vec2-base-960h", "device": dev, "frames": int(T), "frame_s": FRAME_S, "duration": round(dur, 3),
            "star": (sv if star_id is not None else None), "tokens_pass1": ntok, "passes": passes, "unk": 0,
            "flag_thresh_min": round(thresh, 3), "flagged": [r["id"] for r in flagged], "elapsed_s": round(time.time() - t0, 1),
            "real_min_p1": round(float(np.percentile(real_mins, 1)), 3), "real_min_floor": round(float(real_mins.min()), 3),
            "real_mean_median": round(float(np.median(real_means)), 3), "real_mean_min": round(float(real_means.min()), 3)}
    json.dump({"meta": meta, "words": res}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(meta), file=sys.stderr)
    for r in res:
        if r["kind"] == "fake":
            print(f"FAKE {r['word']!r} mean {r['score_mean']} min {r['score_min']} status {r['status']} | thresh {meta['flag_thresh_min']} | real min floor {meta['real_min_floor']}", file=sys.stderr)


if __name__ == "__main__":
    main()
