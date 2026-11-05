#!/usr/bin/env python3
"""Acoustic truth layer: ASR words + energy scan -> an edit map that includes every voiced
sound the transcriber left out (fillers, breaths, false starts) as timed [vocal] tokens.

    python vocal_truth.py <wav16k> <words.json> <out.json> [--tella tella.json] [--report-md out.md]

words.json is the jetson/parakeet shape: {"words":[{"word","start","end"}]}. Only word STARTS
are trusted (Parakeet TDT gives token starts; Whisper ends run early).

Why energy and not another model: seven ASR arms across two families dropped every filler on
take 2 of a test reel while the audio at those moments sat at spoken-word level (-10 to -18 dB against
-57 dB gaps). For editing you need WHERE a sound is, not its label. Thresholds are calibrated
per file (floor = quiet percentile, speech = median inside words), never hardcoded.
"""
import argparse, json, math, re, struct, sys, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

HOP = 0.02          # s per frame
MIN_GAP = 0.12      # s of quiet that splits islands
MIN_ISLAND = 0.06   # s, shorter islands are clicks
SLACK = 0.30        # s of island time a word may exceed its estimate before it is flagged
LEAD = 0.25         # s before an island in which a word start still belongs to it (fricative onsets sit under the threshold)
PAD = 0.06          # s tolerance after an island
LOUD = 10.0         # dB under the speech level: a token peaking above this is voice ([vocal]), below it breath ([breath])


def frames(path):
    w = wave.open(path, "rb")
    assert w.getnchannels() == 1 and w.getsampwidth() == 2, "need 16-bit mono"
    sr = w.getframerate()
    n = w.getnframes()
    data = struct.unpack("<%dh" % n, w.readframes(n))
    w.close()
    hop = int(sr * HOP)
    out = []
    for i in range(0, n - hop, hop):
        seg = data[i:i + hop]
        rms = math.sqrt(sum(x * x for x in seg) / len(seg)) / 32768.0
        out.append(20 * math.log10(rms) if rms > 0 else -100.0)
    return out


def est_dur(word):
    """Rough spoken length of a word from its vowel groups (a syllable proxy)."""
    syl = len(re.findall(r"[aeiouy]+", word.lower())) or 1
    return 0.06 + 0.15 * syl


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("wav"); ap.add_argument("words"); ap.add_argument("out")
    ap.add_argument("--tella"); ap.add_argument("--report-md", dest="report_md")
    a = ap.parse_args()
    rep = Path(a.report_md) if a.report_md else None   # H-M3: only ever overwrites its own report
    if rep and rep.exists() and not rep.read_text(encoding="utf-8", errors="replace").startswith("# vocal_truth on "):
        sys.exit(f"REFUSED: {rep} exists and is not a vocal_truth report; nothing written")

    db = frames(a.wav)
    words = [w for w in json.load(open(a.words, encoding="utf-8"))["words"] if w.get("start") is not None]
    words.sort(key=lambda w: w["start"])

    # --- calibrate -------------------------------------------------------------------------
    s = sorted(db)
    floor = s[int(0.10 * len(s))]
    inside = [db[int(w["start"] / HOP)] for w in words if int(w["start"] / HOP) < len(db)]
    speech = sorted(inside)[len(inside) // 2]
    thr = floor + 0.45 * (speech - floor)

    # --- voiced islands ----------------------------------------------------------------------
    voiced = [d > thr for d in db]
    islands, i = [], 0
    while i < len(voiced):
        if voiced[i]:
            j = i
            while j < len(voiced):
                if voiced[j]:
                    j += 1
                else:
                    k = j
                    while k < len(voiced) and not voiced[k] and (k - j) * HOP < MIN_GAP:
                        k += 1
                    if k < len(voiced) and voiced[k]:
                        j = k
                    else:
                        break
            if (j - i) * HOP >= MIN_ISLAND:
                islands.append((i * HOP, j * HOP))
            i = j
        else:
            i += 1

    # --- account for each island with the words that start inside it ------------------------
    vocal = []
    for (s0, e0) in islands:
        ws = [w for w in words if s0 - LEAD <= w["start"] <= e0 + PAD]
        if not ws:
            vocal.append({"word": "[vocal]", "start": round(s0, 3), "end": round(e0, 3), "why": "no word"})
            continue
        lead = ws[0]["start"] - s0
        if lead > 0.15 + SLACK:
            vocal.append({"word": "[vocal]", "start": round(s0, 3), "end": round(ws[0]["start"], 3), "why": "before first word"})
        last = ws[-1]
        tail = e0 - last["start"]
        if tail > est_dur(last["word"]) + SLACK:
            vocal.append({"word": "[vocal]", "start": round(last["start"] + est_dur(last["word"]), 3), "end": round(e0, 3), "why": "after last word"})
        # interior: a gap between consecutive word starts far larger than the earlier word needs
        for p, q in zip(ws, ws[1:]):
            gap = q["start"] - p["start"]
            if gap > est_dur(p["word"]) + 0.25 + SLACK:
                vocal.append({"word": "[vocal]", "start": round(p["start"] + est_dur(p["word"]), 3), "end": round(q["start"], 3), "why": "between words"})

    # --- voice or breath, by peak level inside the token ----------------------------------------
    for v in vocal:
        i0, i1 = int(v["start"] / HOP), max(int(v["end"] / HOP), int(v["start"] / HOP) + 1)
        v["peak_db"] = round(max(db[i0:i1]) if i1 <= len(db) else max(db[i0:]), 1)
        v["word"] = "[vocal]" if v["peak_db"] >= speech - LOUD else "[breath]"
    merged = sorted(words + vocal, key=lambda w: w["start"])
    res = {"calibration": {"floor_db": round(floor, 1), "speech_db": round(speech, 1), "threshold_db": round(thr, 1)},
           "islands": len(islands), "vocal_tokens": len(vocal), "words": merged}

    # --- score against Tella's fillers if given ------------------------------------------------
    lines = [f"# vocal_truth on {a.wav}", "",
             f"- calibration: floor {floor:.1f} dB, speech {speech:.1f} dB, threshold {thr:.1f} dB",
             f"- islands {len(islands)} · ASR words {len(words)} · [vocal] tokens {len(vocal)}"]
    if a.tella:
        T = json.load(open(a.tella, encoding="utf-8"))["words"]
        fill_all = [(w["text"], w["startTimeMs"] / 1000, w["endTimeMs"] / 1000) for w in T
                    if re.sub(r"[^a-z]", "", w["text"].lower()) in ("uh", "um", "ah", "hmm", "mm")]
        fill = [f for f in fill_all if f[2] - f[1] >= 0.10]      # sub-100 ms "uh" tokens are Tella splinters, not fillers
        splinters = len(fill_all) - len(fill)
        hit = 0
        lines.append(f"- Tella fillers: {len(fill)} (plus {splinters} sub-100 ms splinters ignored)")
        for t, s0, e0 in fill:
            ov = [v for v in vocal if v["start"] < e0 + 0.1 and v["end"] > s0 - 0.1]
            hit += bool(ov)
            lines.append(f"  - {t:>4} {s0:7.2f}-{e0:6.2f}: {'HIT ' + ov[0]['why'] if ov else 'miss'}")
        nv = sum(1 for v in vocal if v["word"] == "[vocal]"); nb = len(vocal) - nv
        lines.append(f"- **recall {hit}/{len(fill)}** · tokens: {nv} [vocal] + {nb} [breath] · not at a Tella filler: {len(vocal) - hit}")
        res["score"] = {"tella_fillers": len(fill), "hit": hit, "vocal": nv, "breath": nb, "extra": len(vocal) - hit}
    lines.append(""); lines.append("## tokens")
    for v in vocal:
        lines.append(f"- {v['word']:9s} {v['start']:7.2f}-{v['end']:6.2f} ({v['end']-v['start']:.2f}s) peak {v['peak_db']:6.1f} dB  {v['why']}")
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if rep:
        open(rep, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
