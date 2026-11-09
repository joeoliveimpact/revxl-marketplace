#!/usr/bin/env python3
"""Build cut-board.config.json for the Cut Board.

    <editor python> -X utf8 -I make_board.py --script <script.md> --take 1:<reel>/work/edit_map.json:<reel>/work/tx.16k.wav \
        [--take 2:...] --shots <shots.json> --reel <reel> -o <reel folder>

Inputs : the teleprompter script (one line per spoken unit), one or more takes (an edit map from build_edit_map.py
         and the 16 kHz mono wav it was built on), a shots vocabulary.
Output : <o>/cut-board.config.json - every script line with every attempt found in every take, the default pick,
         sub-retakes inside an attempt (a repeated phrase: the last one is kept), reworded retakes inside an
         attempt for review (never struck: the client keeps the first, the second or both), and the legal boundary set
         (silence islands). Each take records its wav and edit map as paths relative to the reel folder (<o>), which
         the board loads from /videos/<reel>/<path>.
Default pick: the main take is the take holding the most lines (a tie goes to the higher take). Each line takes its
         attempt in the main take, the last one unless the saved style (<state>/styles/default.json,
         {"cut": {"default_attempt": "first"}}) says first. A line with no attempt in the main take starts dropped and
         flagged "not in take N", so the default never mixes takes.
Pause after commas: the board's starting value is editor.config.json cuts.beat_ms (else 300 ms), clamped to 200-400.

Line anchors are the first two sentences of each script line matched fuzzily against the letters-only word
stream, so a misheard name still anchors.
"""
import argparse, difflib, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import runtime as rt  # noqa: E402
import saved_style  # noqa: E402
from cut_timing import pause_default as style_pause_default  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

# islands(), the board sequence and the word-list hash have one home: build_edit_map.py in this folder (H-R16)
sys.path.insert(0, str(HERE))
from build_edit_map import audio_sha256, board_hash, board_sequence, validate, wav_duration  # noqa: E402
# the reworded-retake finder has one home: repeat_check.loose(), next to this file. Its folder goes on the path
# again here so this import never leans on the build_edit_map block above.
sys.path.append(str(HERE))
import repeat_check  # noqa: E402

LET = re.compile(r"[^a-z0-9]+")
BEAT_MS = 300


def letters(s):
    return LET.sub("", s.lower())


def script_lines(path):
    body = Path(path).read_text(encoding="utf-8").split("\n---\n")[-1]
    out = []
    for ln in body.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        ln = re.sub(r"^\(OPTIONAL SPOKEN HOOK\)\s*", "", ln)
        sents = re.split(r"(?<=[.?!])\s+", ln)
        anchor = " ".join(sents[:2]) if len(sents) > 1 else " ".join(ln.split()[:5])
        out.append(dict(id=f"L{len(out)+1:02d}", text=ln, anchor=anchor, label=sents[0].rstrip(".")))
    return out


def find_anchors(anchor, words, ratio=0.85):
    """Every place `anchor` occurs in the word stream: list of (first_word_idx, score).
    [vocal]/[breath] tokens are skipped so they cannot pollute the letters stream."""
    tgt = letters(anchor)
    m = len(tgt)
    # every sentence of the anchor must be present on its own: a half-match that scores high on the whole but
    # lacks one of the anchor's sentences is a different line
    parts = [letters(x) for x in re.split(r"(?<=[.?!])\s+", anchor) if len(letters(x)) >= 3]
    chars, owner = [], []
    for i, w in enumerate(words):
        if w["word"].startswith("["):
            continue
        for c in letters(w["word"]):
            chars.append(c); owner.append(i)
    s = "".join(chars)
    starts = sorted({k for k in range(len(owner)) if k == 0 or owner[k] != owner[k - 1]})
    hits = []
    for start in starts:
        best = 0.0
        for L in (m - 2, m, m + 2):
            if L <= 0 or start + L > len(s):
                continue
            best = max(best, difflib.SequenceMatcher(None, tgt, s[start:start + L]).ratio())
        if best >= ratio:
            win = s[start:start + m + 2]
            if all(max(difflib.SequenceMatcher(None, pt, win[k:k + len(pt) + 1]).ratio()
                       for k in range(0, max(1, len(win) - len(pt) + 2))) >= 0.75 for pt in parts):
                hits.append((start, best))
    keep = []
    for st, sc in hits:
        if keep and st - keep[-1][0] < m:
            if sc > keep[-1][1]:
                keep[-1] = (st, sc)
        else:
            keep.append((st, sc))
    return [(owner[st], round(sc, 3)) for st, sc in keep]


def sub_retakes(words, lo, hi, n=4, within=12.0):
    """A phrase of >= n words said twice inside one attempt within `within` seconds: the speaker
    stumbled and read it again. Drop from the FIRST read's start to the LAST read's start,
    keeping the last. Returns [[drop_from_idx, drop_to_idx_exclusive], ...]."""
    idx = [i for i in range(lo, hi) if not words[i]["word"].startswith("[")]
    toks = [letters(words[i]["word"]) for i in idx]
    first, out = {}, []
    for k in range(len(toks) - n + 1):
        key = " ".join(toks[k:k + n])
        if key in first:
            j = first[key]
            if words[idx[k]]["start"] - words[idx[j]]["start"] <= within:
                out.append([idx[j], idx[k]])
        first[key] = k
    merged = []
    for a0, b0 in sorted(out):
        if merged and a0 <= merged[-1][1]:  # overlapping stumbles are one region
            merged[-1][1] = max(merged[-1][1], b0)
        else:
            merged.append([a0, b0])
    return merged


def review_hits(words, lo, hi):
    """Reworded retakes inside one attempt: repeat_check's loose() (tier "review") over the attempt's own words, as
    [{first: [board i...], second: [board i...], why}]. Never struck by default: the client picks on the board.
    A pair that spans two attempts or two lines is not looked for here; picking the attempt settles it."""
    W = [dict(w=words[k]["word"], n=repeat_check.norm(words[k]["word"]), s=words[k]["start"], e=words[k]["end"],
              id=words[k]["id"]) for k in range(lo, hi) if not words[k]["word"].startswith("[")]
    W = [w for w in W if w["n"]]
    at = {words[k]["id"]: k for k in range(lo, hi)}   # loose() indexes its own filtered list: back to board i by word id
    out = []
    for h in repeat_check.loose(W, repeat_check.find(W)):   # a pair the strict finder already joins is not flagged
        spans = [(at[W[h["first"]]["id"]], at[W[h["first"] + h["n"] - 1]["id"]]),
                 (at[W[h["second"]]["id"]], at[W[h["second"] + h["m"] - 1]["id"]])]
        first, second = ([k for k in range(a, b + 1) if not words[k]["word"].startswith("[")] for a, b in spans)
        out.append(dict(first=first, second=second,
                        why=f"The second sentence says the first one again in other words "
                            f"({round(h['jaccard'] * 100)}% of the main words match)."))
    return out


def gap_island(isl, lo_t, hi_t, which="last"):
    """A silence island lying between two word starts (lo_t, hi_t): the one nearest the
    boundary word - last (closest before it) for an in-point, first (closest after it) for an
    out-point. Anything beyond it is the between-lines gap, not part of the read."""
    # the island must BEGIN after lo_t: an island that merely overlaps lo_t started before the
    # word on that side and is the pause before it, not after it (that chopped a sentence-final word)
    c = [x for x in isl if x[0] >= lo_t and x[0] < hi_t]
    return (c[-1] if which == "last" else c[0]) if c else None


def _is_event(w):
    return str(w.get("word", "")).strip().startswith("[")


def _prev_word_start(words, i):
    """Start of the nearest real WORD before i. Vocal events ([vocal], [breath]) are not neighbours:
    an event right after a word is usually that word's own fricative tail or release, and using its
    start as the out-point cut the final "s" off a word."""
    for k in range(i - 1, -1, -1):
        if not _is_event(words[k]):
            return words[k]["start"]
    return -1.0


def _next_word_start(words, j, duration):
    for k in range(j + 1, len(words)):
        if not _is_event(words[k]):
            return words[k]["start"]
    return duration


def in_point(words, i, isl):
    """Boundary just before word i: inside the island between word i-1 and word i."""
    prev = _prev_word_start(words, i)
    x = gap_island(isl, prev, words[i]["start"] + 0.02)
    if x:
        return round(x[1] - min(0.15, (x[1] - x[0]) / 2), 3), x
    return round(max(0.0, words[i]["start"] - 0.05), 3), None


def out_point(words, j, isl, duration):
    """Boundary just after word j: inside the island between word j and word j+1."""
    nxt = _next_word_start(words, j, duration)
    x = gap_island(isl, words[j]["start"], nxt, "first")
    if x:
        return round(x[0] + min(0.12, (x[1] - x[0]) / 2), 3), x
    return round(nxt - 0.05, 3), None


def reel_rel(path, reel_dir):
    """The path relative to the reel folder (the board loads it from /videos/<reel>/<path>); it must be inside."""
    p, top = os.path.realpath(path), os.path.realpath(reel_dir)
    try:
        inside = os.path.commonpath([os.path.normcase(p), os.path.normcase(top)]) == os.path.normcase(top)
    except ValueError:  # another drive
        inside = False
    if not inside or os.path.normcase(p) == os.path.normcase(top):
        raise SystemExit(f"{path} is not inside the reel folder {reel_dir}; the board can only load the reel's own files")
    return Path(os.path.relpath(p, top)).as_posix()


def default_attempt(reel=None):
    """The saved-style rule cut.default_attempt ("last" or "first"), else "last"."""
    try:
        st = saved_style.load(reel)
        v = (st.get("cut") or {}).get("default_attempt")
    except (OSError, ValueError, AttributeError):
        v = None
    return v if v in ("last", "first") else "last"


def pause_default(reel=None):
    """The active style's pause between lines, else the existing 150 ms default."""
    return style_pause_default(saved_style._get(saved_style.load(reel), "cut.pause_ms"))


def beat_default():
    cuts = rt.read_config().get("cuts")
    ms = cuts.get("beat_ms") if isinstance(cuts, dict) else None
    if not isinstance(ms, (int, float)) or isinstance(ms, bool):
        return BEAT_MS
    if not 200 <= ms <= 400:
        print(f"cuts.beat_ms {ms} clamped to {min(400, max(200, ms))} (200-400)")
    return int(round(min(400, max(200, ms))))


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--take", action="append", required=True,
                    help="N:editmap.json:wav (editmap = build_edit_map.py output: words, events, silences, duration, hash)")
    ap.add_argument("--shots", required=True, help="shots.json: {vocab:[...], default:'...'}")
    ap.add_argument("--reel", required=True)
    ap.add_argument("-o", "--out", required=True, help="the reel folder: cut-board.config.json is written here")
    a = ap.parse_args()

    out = Path(a.out)
    lines = script_lines(a.script)
    takes = {}
    for spec in a.take:
        # N:map.json:wav, parsed on the ".json:" seam so Windows drive letters survive
        mt = re.fullmatch(r"(\d+):(.+?\.json):(.+)", spec)
        if not mt:
            raise SystemExit(f"--take {spec!r}: expected N:editmap.json:wav")
        n, em, wav = mt.groups()
        d = json.loads(Path(em).read_text(encoding="utf-8"))
        if "events" not in d:
            raise SystemExit(f"{em} is not an edit map (no events[]); build one with build_edit_map.py first")
        errs = validate(d)   # the shared validator also re-derives word_list_hash from the words/events
        if errs:
            raise SystemExit(f"{em} is not a valid edit map:\n  " + "\n  ".join(errs[:10]))
        if audio_sha256(wav) != d["audio_sha256"]:
            raise SystemExit(f"{wav} is not the audio {em} was built on (PCM sample data differs)")
        wd = round(wav_duration(wav), 3)   # duration from the verified WAV header, never trusted from the map
        if abs(wd - d["duration"]) > 0.001:
            raise SystemExit(f"{em} says duration {d['duration']} s but {wav} is {wd} s; rebuild the map")
        words = board_sequence(d)   # words by cut anchor with events interleaved: every index below refers to this list
        h = d["word_list_hash"]
        isl = [[x["start"], x["end"]] for x in d["silences"]]
        takes[n] = dict(n=int(n), wav=reel_rel(wav, out), edit_map=reel_rel(em, out), words=words, islands=isl,
                        word_list_hash=h,
                        audio_sha256=d["audio_sha256"],   # into board_hash: a re-recorded take invalidates rulings
                        calibration=d["calibration"], duration=wd)

    # each take plays its own wav: two different recordings at one path would play the same audio
    seen = {}
    for tk in takes.values():
        if seen.setdefault(tk["wav"], tk["audio_sha256"]) != tk["audio_sha256"]:
            raise SystemExit(f"two different recordings are both at {tk['wav']}; rename one before building the board")

    # anchors per take: (word_idx, line_id, score), sorted by position
    for tk in takes.values():
        anc = []
        for ln in lines:
            for wi, sc in find_anchors(ln["anchor"], tk["words"]):
                anc.append((wi, ln["id"], sc))
        anc.sort()
        dedup = {}
        for wi, lid, sc in anc:
            if wi not in dedup or sc > dedup[wi][1]:
                dedup[wi] = (lid, sc)
        tk["anchors"] = [(wi, lid, sc) for wi, (lid, sc) in sorted(dedup.items())]

    for ln in lines:
        ln["attempts"] = []
        for tn, tk in sorted(takes.items(), key=lambda kv: int(kv[0])):
            anc, words, isl = tk["anchors"], tk["words"], tk["islands"]
            for k, (wi, lid, sc) in enumerate(anc):
                if lid != ln["id"]:
                    continue
                hi = anc[k + 1][0] if k + 1 < len(anc) else len(words)
                if hi - wi < 3:
                    continue
                # drop trailing [vocal]/[breath] tokens from the attempt body
                while hi - 1 > wi and words[hi - 1]["word"].startswith("["):
                    hi -= 1
                s_in, isl_in = in_point(words, wi, isl)
                s_out, isl_out = out_point(words, hi - 1, isl, tk["duration"])
                # per-word snapped in-points (where a cut before that word would land) and the
                # internal silences >= 250 ms - the only places a cut or a pause ruling can go
                wl = [dict(i=k, w=words[k]["word"].strip(), s=words[k]["start"],
                           cin=in_point(words, k, isl)[0], snapped=in_point(words, k, isl)[1] is not None)
                      for k in range(wi, hi) if not words[k]["word"].startswith("[")]
                sil = []
                for x in isl:
                    if x[0] <= s_in or x[1] >= s_out or x[1] - x[0] < 0.25:
                        continue
                    # spoken word the pause follows; +0.15 s tolerance for late word starts
                    after = max((k for k in range(wi, hi) if not words[k]["word"].startswith("[")
                                 and words[k]["start"] < x[0] + 0.15), default=None)
                    if after is not None:
                        sil.append(dict(a=x[0], b=x[1], after=after))
                ln["attempts"].append(dict(
                    words=wl, silences=sil,
                    take=int(tn), attempt=sum(1 for x in ln["attempts"] if x["take"] == int(tn)) + 1,
                    word_from=wi, word_to=hi, src_in=s_in, src_out=s_out,
                    snapped=[isl_in is not None, isl_out is not None], score=sc,
                    text=" ".join(w["word"].strip() for w in words[wi:hi] if not w["word"].startswith("[")),
                    sub_retakes=[dict(drop_from=x, drop_to=y,
                                      text=" ".join(w["word"].strip() for w in words[x:y]),
                                      src_from=in_point(words, x, isl)[0],
                                      src_to=in_point(words, y, isl)[0] if y < len(words) else out_point(words, y - 1, isl, tk["duration"])[0])
                                 for x, y in sub_retakes(words, wi, hi)],
                    review=review_hits(words, wi, hi)))

    # the default ruling never mixes takes: the main take holds the most lines, a tie goes to the higher take
    held = {int(n): sum(1 for ln in lines if any(x["take"] == int(n) for x in ln["attempts"])) for n in takes}
    main_take = max(held, key=lambda n: (held[n], n))
    which = default_attempt(out)
    for ln in lines:
        js = [j for j, x in enumerate(ln["attempts"]) if x["take"] == main_take]
        ln["default"] = (js[-1] if which == "last" else js[0]) if js else None
        if not js and ln["attempts"]:
            ln["flag"] = f"not in take {main_take}"

    shots = json.loads(Path(a.shots).read_text(encoding="utf-8"))
    cfg = dict(reel=a.reel, rule=f"{which} attempt wins, take {main_take}", main_take=main_take,
               gap_presets=[["Tight", 0], ["150", 150], ["250", 250], ["500", 500], ["Breathe", 800], ["As spoken", None]],
               gap_default_ms=pause_default(out), beat_ms=beat_default(), speed_options=[1.0, 1.1, 1.15, 1.2], speed_default=1.0,
               shots=shots, lines=lines,
               takes={n: {k: v for k, v in t.items() if k != "anchors"} for n, t in takes.items()})
    if cfg["gap_default_ms"] not in [ms for _, ms in cfg["gap_presets"]]:
        index = next(i for i, (_, ms) in enumerate(cfg["gap_presets"])
                     if ms is None or ms > cfg["gap_default_ms"])
        cfg["gap_presets"].insert(index, [str(round(cfg["gap_default_ms"])), cfg["gap_default_ms"]])
    # what a ruling indexes: word lists, attempts, silences. attempts[].review is not in it: the keep choice is
    # stored as rm word indices, which the word lists already cover
    cfg["board_hash"] = board_hash(cfg)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cut-board.config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    miss = [ln["id"] for ln in lines if not ln["attempts"]]
    print(f"lines {len(lines)} · takes {len(takes)} · main take {main_take} · attempts "
          f"{sum(len(l['attempts']) for l in lines)} · unmatched {miss or 'none'}")
    for ln in lines:
        print(f"  {ln['id']} {ln['label'][:22]:22s} " + " | ".join(
            f"T{x['take']}#{x['attempt']} {x['src_in']:.2f}-{x['src_out']:.2f}" + ("*" if x["sub_retakes"] else "")
            for x in ln["attempts"]) + (f"  ({ln['flag']}: starts dropped)" if ln.get("flag") else ""))


if __name__ == "__main__":
    main()
