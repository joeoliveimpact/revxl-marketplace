#!/usr/bin/env python3
"""Merge one take into a verbatim edit map: aligned words + acoustic events + silence islands.

    python build_edit_map.py <wav16k> <aligned.json> <vocal_truth.json> <out.json> [--report-md out.md]
                             [--expect words=481,events=23,silences=173]
    python build_edit_map.py --selftest

Two branches from the SAME Parakeet map, never chained (spec step 5):
  aligned.json      align_words.py output; its records become words[] (ids w_<parakeet index>)
  vocal_truth.json  vocal_truth.py output; only its bracketed items ([vocal]/[breath]) become events[]
Output, separate arrays, never interleaved:
  words[]    {id, word, start, end, parakeet_start, status, score_min}
             start/end = the aligned span when status is "aligned", else Parakeet's times (status says which).
             parakeet_start is the CUT ANCHOR: the Cut Board orders and snaps from it, so rulings reproduce.
  events[]   {id v_NNNN, word, start, end, why, peak_db}, exactly as vocal_truth emits them
  silences[] {id s_NNNN, start, end}, the Cut Board's islands() at vocal_truth's calibrated threshold
  duration and audio_sha256 (PCM sample data) from the WAV; word_list_hash over the board sequence
  (ids + text + order, never times). The map is validated before it is written; an invalid map writes nothing.
Audio contract: 16 kHz mono PCM16, the same as align_words.py.
"""
import argparse, copy, hashlib, json, math, re, sys, wave
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402


def check_wav(wav):
    """Refuse anything but 16 kHz mono PCM16 (R5): islands() reads raw int16 frames."""
    with wave.open(wav) as w:
        got = (w.getframerate(), w.getnchannels(), w.getsampwidth())
    if got != (16000, 1, 2):
        raise SystemExit(f"{wav}: need 16 kHz mono PCM16, got {got[0]} Hz, {got[1]} ch, {8 * got[2]}-bit")


def islands(wav, thr_db, min_s=0.10, win=0.010):
    """Silence runs below thr_db lasting >= min_s. The only legal places for a boundary."""
    check_wav(wav)
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(sr * win)
    nwin = len(x) // hop
    rms = np.sqrt((x[: nwin * hop].reshape(nwin, hop) ** 2).mean(1) + 1e-12)
    quiet = 20 * np.log10(rms) < thr_db
    out, run = [], None
    for k, q in enumerate(quiet):
        if q and run is None:
            run = k
        if not q and run is not None:
            if (k - run) * win >= min_s:
                out.append([round(run * win, 3), round(k * win, 3)])
            run = None
    if run is not None and (nwin - run) * win >= min_s:
        out.append([round(run * win, 3), round(nwin * win, 3)])
    return out


def wav_duration(wav):
    with wave.open(wav) as w:
        return w.getnframes() / w.getframerate()


def audio_sha256(wav):
    """Fingerprint of the PCM sample data, not the file: a re-wrapped header still matches, other audio does not (R4)."""
    check_wav(wav)
    with wave.open(wav) as w:
        return hashlib.sha256(w.readframes(w.getnframes())).hexdigest()


def board_sequence(m):
    """The mixed list the Cut Board indexes: words (by cut anchor) and events, words first on a tie.
    Reproduces vocal_truth's own merge: sorted(words + vocal, key=start), which is stable."""
    seq = [dict(id=w["id"], word=w["word"], start=w["parakeet_start"], end=w["end"]) for w in m["words"]]
    seq += [dict(id=e["id"], word=e["word"], start=e["start"], end=e["end"], why=e.get("why"), peak_db=e.get("peak_db"))
            for e in m["events"]]
    return sorted(seq, key=lambda x: x["start"])


def word_list_hash(seq):
    # Surrounding whitespace is not part of the word: one ASR export writes " Chat", another "Chat" (measured
    # 09.14.26 on take 2 of a test reel, identical times), and a leading space must not make the same take read as stale.
    return hashlib.sha256(json.dumps([[x.get("id"), x["word"].strip() if isinstance(x.get("word"), str) else x.get("word")]
                                      for x in seq], ensure_ascii=False).encode("utf-8")).hexdigest()


def board_hash(cfg):
    """Everything a Cut Board ruling indexes, never times (R2): each take's recording and word list, the line ids,
    each line's attempt list (take and word span, which `pick` indexes) and each attempt's silences (which word each
    follows, which `sil[j][k]` indexes). The recording is in it so a same-words re-record invalidates rulings (R2-02).
    Each take's word list is re-derived from its stored records and each attempt's own word records (index + text,
    which `rm` indexes) are included, so editing any indexed record changes the hash (R3-01)."""
    shape = {"takes": {n: [t.get("audio_sha256"), t.get("word_list_hash"), word_list_hash(t.get("words", []))]
                       for n, t in sorted(cfg["takes"].items())},
             "lines": [[ln["id"], [[a["take"], a["word_from"], a["word_to"], [s["after"] for s in a.get("silences", [])],
                                    [[w.get("i"), w.get("w")] for w in a.get("words", [])]]
                                   for a in ln["attempts"]]] for ln in cfg["lines"]]}
    return hashlib.sha256(json.dumps(shape, sort_keys=True).encode("utf-8")).hexdigest()


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# AC7 word/silence overlap rule (ruled 09.13.26: flag, keep building). 3 CTC frames = the largest overlap measured on any
# clean aligned word across both takes of a test reel (take 2 max 0.060 s, take 1 max 0.030 s), so it is the real-end residual.
OVERLAP_TOL = 0.06


def silence_overlap(start, end, silences):
    """(seconds of the span covered by silence islands, whether a whole island lies inside the span)."""
    ov = sum(max(0.0, min(end, s["end"]) - max(start, s["start"])) for s in silences)
    return ov, any(s["start"] > start and s["end"] < end for s in silences)


def flag_overlaps(words, silences, parakeet_end):
    """An aligned span that swallows a pause is not a word span: status "overlap", Parakeet times, span kept for audit."""
    flagged = []
    for w in words:
        if w["status"] != "aligned":
            continue
        ov, inside = silence_overlap(w["start"], w["end"], silences)
        if inside or ov > OVERLAP_TOL + 1e-6:
            w.update(status="overlap", aligned_start=w["start"], aligned_end=w["end"], overlap_s=round(ov, 3),
                     start=w["parakeet_start"], end=parakeet_end[w["id"]])
            flagged.append(w["id"])
    return flagged


def validate(m):
    errs, D = [], m.get("duration")
    if not (_num(D) and D > 0):
        return [f"duration {D!r} is not a finite positive number"]
    if not re.fullmatch(r"[0-9a-f]{64}", str(m.get("audio_sha256"))):
        errs.append("audio_sha256 missing or malformed")
    ids = [x.get("id") for k in ("words", "events", "silences") for x in m[k]]
    if len(ids) != len(set(ids)):
        errs.append("duplicate ids: " + ", ".join(sorted(str(i) for i, c in Counter(ids).items() if c > 1)[:5]))
    for k, pat in (("words", r"w_\d{4,}"), ("events", r"v_\d{4,}"), ("silences", r"s_\d{4,}")):
        for x in m[k]:
            if not re.fullmatch(pat, str(x.get("id"))):
                errs.append(f"{k}: bad id {x.get('id')!r}")
            if x.get("start") is None or x.get("end") is None:
                errs.append(f"{x.get('id')}: missing boundary")
            elif not (_num(x["start"]) and _num(x["end"]) and 0 <= x["start"] < x["end"] <= D + 1e-6):
                errs.append(f"{x['id']}: span {x['start']}-{x['end']} not increasing inside [0, {D}]")
    for w in m["words"]:
        a = w.get("parakeet_start")
        if not (_num(a) and 0 <= a <= D):
            errs.append(f"{w.get('id')}: cut anchor {a!r} outside [0, {D}]")   # R3: it is the cutting start
    for k, key, sel in (("words", "parakeet_start", None), ("words", "start", "aligned"), ("events", "start", None),
                        ("silences", "start", None)):
        v = [x[key] for x in m[k] if _num(x.get(key)) and (sel is None or x.get("status") == sel)]
        if any(b < a for a, b in zip(v, v[1:])):
            errs.append(f"{k}: {'aligned ' if sel else ''}{key} not monotonic")
    sil = m["silences"]
    if any(_num(a.get("end")) and _num(b.get("start")) and b["start"] < a["end"] for a, b in zip(sil, sil[1:])):
        errs.append("silences overlap")
    if not errs:
        for w in m["words"]:
            if w.get("status") == "aligned":
                ov, inside = silence_overlap(w["start"], w["end"], sil)
                if inside or ov > OVERLAP_TOL + 1e-6:
                    errs.append(f"{w['id']}: aligned span {w['start']}-{w['end']} swallows silence ({ov:.3f} s"
                                f"{', a whole island inside' if inside else ''}); status must be overlap")
    if not errs and m.get("word_list_hash") != word_list_hash(board_sequence(m)):
        errs.append("word_list_hash does not match the words/events sequence")
    return errs


def build(wav, aligned_p, vt_p):
    al = json.load(open(aligned_p, encoding="utf-8"))
    vt = json.load(open(vt_p, encoding="utf-8"))
    extra = [x["id"] for x in al["words"] if x.get("kind") != "word"]
    if extra:
        sys.exit(f"REFUSED: {aligned_p} carries non-word records {extra[:5]} (a fake/hypothesis proof run); "
                 "build from a production alignment")
    dur = wav_duration(wav)
    ad = (al.get("meta") or {}).get("duration")
    if not _num(ad) or abs(ad - dur) > 0.01:
        sys.exit(f"REFUSED: {aligned_p} was aligned on a {ad!r} s file but {wav} is {dur:.3f} s (R4)")
    aw = al["words"]
    vw = [w for w in vt["words"] if not str(w["word"]).startswith("[")]
    if len(aw) != len(vw) or any(a["word"] != v["word"] or abs(a["parakeet_start"] - v["start"]) > 1e-6 for a, v in zip(aw, vw)):
        sys.exit("REFUSED: aligned words and vocal_truth words are not the same Parakeet map (count, text or start differs)")
    words = [dict(id=a["id"], word=a["word"], start=a["start"], end=a["end"], parakeet_start=a["parakeet_start"],
                  status=a["status"], score_min=a.get("score_min")) for a in aw]
    events = [dict(id=f"v_{k:04d}", word=e["word"], start=e["start"], end=e["end"], why=e.get("why"), peak_db=e.get("peak_db"))
              for k, e in enumerate(x for x in vt["words"] if str(x["word"]).startswith("["))]
    silences = [dict(id=f"s_{k:04d}", start=a, end=b) for k, (a, b) in enumerate(islands(wav, vt["calibration"]["threshold_db"]))]
    flag_overlaps(words, silences, {a["id"]: a["parakeet_end"] for a in aw})
    m = dict(version=1, wav=Path(wav).name, audio_sha256=audio_sha256(wav), aligned=Path(aligned_p).name,
             vocal_truth=Path(vt_p).name, duration=round(dur, 3), calibration=vt["calibration"], word_list_hash=None,
             words=words, events=events, silences=silences)
    m["word_list_hash"] = word_list_hash(board_sequence(m))
    return m


def refuse_non_report(path, head="# Edit map: "):
    """H-M3: --report-md only ever overwrites its own report, never another file."""
    p = Path(path)
    if p.exists() and not p.read_text(encoding="utf-8", errors="replace").startswith(head):
        sys.exit(f"REFUSED: {p} exists and is not an edit-map report; nothing written")


def to_md(m):
    L = [f"# Edit map: {m['wav']}", "",
         f"- duration {m['duration']} s · words {len(m['words'])} · events {len(m['events'])} · silences {len(m['silences'])}",
         f"- threshold {m['calibration']['threshold_db']} dB · word_list_hash `{m['word_list_hash'][:16]}` · audio `{m['audio_sha256'][:16]}`",
         f"- word status: {dict(Counter(w['status'] for w in m['words']))}", "", "## Sequence (cut anchor, id, text, end)"]
    L += [f"- {x['start']:8.2f}  {x['id']}  {x['word'].strip()}  → {x['end']:.2f}" for x in board_sequence(m)]
    return "\n".join(L) + "\n"


def selftest():
    base = dict(duration=10.0, audio_sha256="0" * 64, calibration={"threshold_db": -48.0}, word_list_hash=None,
                words=[dict(id="w_0000", word=" Hi", start=1.02, end=1.4, parakeet_start=1.0, status="aligned", score_min=-1.0),
                       dict(id="w_0001", word=" there", start=1.5, end=2.0, parakeet_start=1.6, status="aligned", score_min=-1.0)],
                events=[dict(id="v_0000", word="[vocal]", start=2.1, end=2.5, why="after last word", peak_db=-9.0)],
                silences=[dict(id="s_0000", start=0.0, end=0.9), dict(id="s_0001", start=2.6, end=10.0)])
    base["word_list_hash"] = word_list_hash(board_sequence(base))
    assert validate(base) == [], validate(base)
    cases = {  # name: (mutation, text the validator must report)
        "end before start": (lambda m: m["words"][0].update(end=0.9), "not increasing"),
        "past duration": (lambda m: m["silences"][1].update(end=10.5), "not increasing"),
        "missing boundary": (lambda m: m["events"][0].update(end=None), "missing boundary"),
        "duplicate id": (lambda m: m["words"][1].update(id="w_0000"), "duplicate ids"),
        "bad id": (lambda m: m["events"][0].update(id="e_0"), "bad id"),
        "anchor out of order": (lambda m: m["words"][1].update(parakeet_start=0.5), "parakeet_start not monotonic"),
        "anchor out of range": (lambda m: m["words"][0].update(parakeet_start=-1.0), "cut anchor"),
        "anchor NaN": (lambda m: m["words"][1].update(parakeet_start=float("nan")), "cut anchor"),
        "aligned spans out of order": (lambda m: m["words"][1].update(start=0.5, end=0.8), "aligned start not monotonic"),
        "duration not finite": (lambda m: m.update(duration=float("inf")), "finite positive"),
        "audio fingerprint missing": (lambda m: m.update(audio_sha256=None), "audio_sha256"),
        "silences overlap": (lambda m: m["silences"][0].update(end=3.0), "silences overlap"),
        "aligned word swallows a pause": (lambda m: m["words"][0].update(start=0.5), "swallows silence"),
        "word text changed": (lambda m: m["words"][1].update(word=" where"), "word_list_hash"),
        "event dropped": (lambda m: m["events"].clear(), "word_list_hash"),
    }
    for name, (mutate, expect) in cases.items():
        m = copy.deepcopy(base); mutate(m)
        errs = validate(m)
        assert any(expect in e for e in errs), f"validator missed '{name}': {errs}"
        print(f"caught {name}: {next(e for e in errs if expect in e)}")
    fw = [dict(id="w_0000", word=" But", start=1.0, end=5.0, parakeet_start=1.0, status="aligned"),
          dict(id="w_0001", word=" so", start=5.1, end=5.3, parakeet_start=5.1, status="aligned")]
    fs = [dict(id="s_0000", start=2.0, end=4.0), dict(id="s_0001", start=5.25, end=5.3)]
    assert flag_overlaps(fw, fs, {"w_0000": 1.4, "w_0001": 5.4}) == ["w_0000"], fw
    assert fw[0]["status"] == "overlap" and (fw[0]["start"], fw[0]["end"]) == (1.0, 1.4) and fw[0]["aligned_end"] == 5.0
    assert fw[1]["status"] == "aligned", "a 50 ms overlap is inside the 60 ms tolerance"
    print("caught stretched span: flagged overlap, fell back to Parakeet times, kept the aligned span for audit")
    t = copy.deepcopy(base); t["words"][0]["end"] = 1.45
    assert word_list_hash(board_sequence(t)) == base["word_list_hash"], "hash must ignore times"
    cfg = {"takes": {"2": {"word_list_hash": "a", "audio_sha256": "c", "words": [{"id": "w_0000", "word": " Hi", "start": 1.0}]}},
           "lines": [{"id": "L01", "attempts": [{"take": 2, "word_from": 0, "word_to": 5, "silences": [{"after": 2, "a": 1.0, "b": 1.3}],
                                                  "words": [{"i": 0, "w": "Hi", "s": 1.0, "cin": 0.9}]}]}]}
    h = board_hash(cfg)
    moved = copy.deepcopy(cfg); moved["lines"][0]["attempts"][0]["silences"][0]["a"] = 1.01
    moved["lines"][0]["attempts"][0]["words"][0]["cin"] = 0.95; moved["takes"]["2"]["words"][0]["start"] = 1.02
    assert board_hash(moved) == h, "board hash must ignore times"
    for name, f in {"attempt span": lambda c: c["lines"][0]["attempts"][0].update(word_to=6),
                    "attempt added": lambda c: c["lines"][0]["attempts"].append(dict(take=2, word_from=6, word_to=9, silences=[])),
                    "silence follows another word": lambda c: c["lines"][0]["attempts"][0]["silences"][0].update(after=3),
                    "word list": lambda c: c["takes"]["2"].update(word_list_hash="b"),
                    "recording": lambda c: c["takes"]["2"].update(audio_sha256="d"),
                    "attempt word index": lambda c: c["lines"][0]["attempts"][0]["words"][0].update(i=1),
                    "attempt word text": lambda c: c["lines"][0]["attempts"][0]["words"][0].update(w="Bye"),
                    "stored take word record": lambda c: c["takes"]["2"]["words"][0].update(word=" Bye")}.items():
        c = copy.deepcopy(cfg); f(c)
        assert board_hash(c) != h, f"board hash missed '{name}'"
    print(f"selftest ok: {len(cases)} broken maps caught, valid map clean, both hashes ignore times, board hash sees 8 changes incl. the recording and indexed word records")


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="<wav16k> <aligned.json> <vocal_truth.json> <out.json>")
    ap.add_argument("--report-md", dest="report_md", help="a readable report; never overwrites another file")
    ap.add_argument("--expect", help="real-data assertion, e.g. words=481,events=23,silences=173")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if len(a.paths) != 4:
        ap.error("need <wav16k> <aligned.json> <vocal_truth.json> <out.json>")
    wav, aligned_p, vt_p, out = a.paths
    if a.report_md:
        refuse_non_report(a.report_md)
    m = build(wav, aligned_p, vt_p)
    errs = validate(m)
    if errs:
        sys.exit("INVALID map, nothing written:\n  " + "\n  ".join(errs[:20]))
    got = {"words": len(m["words"]), "events": len(m["events"]), "silences": len(m["silences"])}
    if a.expect:
        want = {k: int(v) for k, v in (p.split("=") for p in a.expect.split(","))}
        bad = {k: {"got": got.get(k), "want": v} for k, v in want.items() if got.get(k) != v}
        if bad:
            sys.exit(f"EXPECT failed, nothing written: {bad}")
    json.dump(m, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.report_md:
        Path(a.report_md).write_text(to_md(m), encoding="utf-8")
    print(f"{Path(out).name}: duration {m['duration']} s · {got} · status {dict(Counter(w['status'] for w in m['words']))} "
          f"· hash {m['word_list_hash'][:12]} · audio {m['audio_sha256'][:12]}")


if __name__ == "__main__":
    main()
