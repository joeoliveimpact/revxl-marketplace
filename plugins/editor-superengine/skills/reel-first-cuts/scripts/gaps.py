#!/usr/bin/env python3
"""Stage 4 - gap tightening, entirely in SOURCE coordinates.

The reference build did this against a rendered master, which made Stage 4 depend
on Stage 6's output - a circular pipeline that forced two 4K renders. Here every
measurement comes from the source envelope produced by probe.py, so nothing needs
a render to exist.

Reads : work/probe.json, work/envelope.json, an EDL with src_in/src_out per cut, and with
        --words S3's edit map (word times: beats after punctuation, whole words at the edges)
Writes: work/cuts.json (the kept pieces in whole frames at the master's fps: the one cut list
        render.py reads), work/segments.json (seconds, derived from cuts.json for the 0.1.0 path),
        work/gap-plan.txt, work/listen.txt (the targeted checklist Stage 8 hands to the human)
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402
# the Cut Board's cut time per word has one home: make_board.in_point over build_edit_map.board_sequence (H-N1-11)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_edit_map import board_sequence  # noqa: E402
from make_board import in_point  # noqa: E402

# F-1: a silence right after one of these words is a beat: capped at the beat length, never at --internal
BEAT_PUNCT = (",", ";", ":", ".", "?", "!", "\u2026", "\u2014")
LIST_MARKERS = {"first", "second", "third", "fourth", "fifth", "next", "then", "finally", "lastly", "also",
                "one", "two", "three", "four", "five"}


def die(m):
    print("ERROR: %s" % m, file=sys.stderr)
    raise SystemExit(2)


class Env:
    """The source-audio RMS envelope, and the questions worth asking of it."""

    def __init__(self, db, win, cal):
        self.db, self.win, self.cal = db, win, cal

    def i(self, t):
        return max(0, min(len(self.db) - 1, int(t / self.win)))

    def peak(self, a, b):
        lo, hi = self.i(a), self.i(b)
        return max(self.db[lo:hi + 1]) if hi >= lo else -120.0

    def has_speech(self, a, b):
        """A SUSTAINED run above the speech floor - not a peak.

        One loud window at a splice is a decay tail; ~40ms is a breath. Testing
        peak() reverted a whole deletion on a single -28.9 dB sample, and a 30ms
        run test read a breath as speech (fixtures F5)."""
        lo, hi = self.i(a), self.i(b)
        need, run = self.cal["speech_run_windows"], 0
        for d in self.db[lo:hi + 1]:
            run = run + 1 if d > self.cal["speech_db"] else 0
            if run >= need:
                return True
        return False

    def silences(self, a, b, min_gap):
        """Runs with nobody talking, strictly inside [a,b].

        Measured against the SPEECH floor, not the silence floor: room noise that sits between
        the two (a reference build: ~-48 dB under a -50.6/-45.6 calibration) broke every run at
        gap_db, so 14 s of humming read as content and the cut shipped at 42% silence. The
        deletion itself is still proven by has_speech() before anything is removed."""
        out, run = [], None
        lo, hi = self.i(a), self.i(b)
        # a window is "talking" only inside a SUSTAINED run above the speech floor (the has_speech
        # rule); a lone window at -45.4 dB against a -45.6 floor is noise and must not break a gap.
        need, n = self.cal["speech_run_windows"], hi - lo + 1
        above = [d > self.cal["speech_db"] for d in self.db[lo:hi + 1]]
        talking = [False] * n
        r = 0
        for j in range(n):
            r = r + 1 if above[j] else 0
            if r >= need:
                for q in range(j - r + 1, j + 1):
                    talking[q] = True
        for k in range(lo, hi + 1):
            if not talking[k - lo]:
                run = k if run is None else run
            else:
                if run is not None:
                    self._emit(out, run, k, lo, above, min_gap)
                run = None
        if run is not None:
            self._emit(out, run, hi + 1, lo, above, min_gap)
        return out

    def _emit(self, out, r0, r1, lo, above, min_gap):
        """Trim a silence run so it never starts before, or ends after, a short above-floor burst
        that sits within `attach` of its edge. A run's sustained-speech test rightly ignores a 40 ms
        burst (a breath is longer and quieter) - but a burst GLUED to a word is that word's own stop
        release, or a short function word ("If", "The"): a reference build deleted a leading "If"
        and most of a leading "The" this way, and a -28 dB release from "deal."
        Cost is bounded: at most `attach` per edge, and only where such a burst exists."""
        attach = int(round(self.cal.get("attach_s", 0.15) / self.win))
        while r1 - r0 > 0 and any(above[j - lo] for j in range(r0, min(r1, r0 + attach))):
            r0 = max(j for j in range(r0, min(r1, r0 + attach)) if above[j - lo]) + 1
        while r1 - r0 > 0 and any(above[j - lo] for j in range(max(r0, r1 - attach), r1)):
            r1 = min(j for j in range(max(r0, r1 - attach), r1) if above[j - lo])
        if (r1 - r0) * self.win >= min_gap:
            out.append((r0 * self.win, r1 * self.win))

    def speech_bounds(self, a, b):
        """First and last moment of real speech inside a cut."""
        lo, hi = self.i(a), self.i(b)
        first = last = None
        for k in range(lo, hi + 1):
            if self.db[k] > self.cal["speech_db"]:
                first = k * self.win if first is None else first
                last = (k + 1) * self.win
        return (first, last) if first is not None else (a, b)

    def talk_span(self, a, b):
        """(first, last) moment of SUSTAINED speech inside [a,b] (the has_speech rule), or None."""
        lo, hi = self.i(a), self.i(b)
        need, run, span = self.cal["speech_run_windows"], 0, None
        for k in range(lo, hi + 1):
            run = run + 1 if self.db[k] > self.cal["speech_db"] else 0
            if run >= need:
                span = ((k - run + 1) * self.win if span is None else span[0], (k + 1) * self.win)
        return span

    def quietest(self, a, b):
        """Centre of the quietest window inside [a,b], clamped to [a,b]."""
        k = min(range(self.i(a), self.i(b) + 1), key=lambda j: self.db[j])
        return min(b, max(a, (k + 0.5) * self.win))


def protected(word):
    """F-1: a word ending in punctuation, or a list marker ("First", "next", "2"), case-insensitive."""
    t = str(word).strip()
    if t.endswith(BEAT_PUNCT):
        return True
    t = re.sub(r"[\W_]+$", "", t.lower())
    return t in LIST_MARKERS or t.isdigit()


def word_before(words, t):
    """The last edit-map word ending by t + 30 ms: the word a silence starting at t follows."""
    return next((w for w in reversed(words) if w["end"] <= t + 0.03), None)


def overlaps(words, a, b):
    return [w for w in words if w["start"] < b and w["end"] > a]


def clear_of(words, a, b, guard):
    """F-2: the longest part of [a, b] that stays guard clear of every edit-map word inside it. Never wider."""
    parts, t = [], a
    for w in sorted(overlaps(words, a, b), key=lambda w: w["start"]):
        parts.append((t, min(b, w["start"] - guard)))
        t = max(t, w["end"] + guard)
    parts.append((t, b))
    return max(parts, key=lambda p: p[1] - p[0])


def board_cuts(em):
    """{word id: the Cut Board's cut time for that word} (make_board.in_point over the edit map's own silences), or
    None when a word has no parakeet_start (a tx.json word list): then keep_edge_words keeps its old rule."""
    if not em["words"] or not all("parakeet_start" in w and "id" in w for w in em["words"]):
        return None
    seq = board_sequence(dict(words=em["words"], events=em.get("events", [])))
    isl = [[x["start"], x["end"]] for x in em.get("silences", [])]
    return {x["id"]: in_point(seq, k, isl)[0] for k, x in enumerate(seq)}


def keep_edge_words(edl, env, words, guard, fps, log, cin=None):
    """F-2: an EDL edge inside a word moves to that word's edge. The new edge sits at the envelope minimum within
    guard past (or before) the word, or between the two words when the neighbour starts sooner. Half a frame of
    margin (when there is room) keeps the frame snap from moving it back into the word.
    H-N1-11: cin is board_cuts(). A word is picked for an EDL cut when its board cut time lies inside the cut's own
    [src_in, src_out): the board's rule (selection_to_edl.py). A straddled picked word is kept whole (the edge moves
    outward); a straddled word that is not picked is left out (the edge moves inward past it). A picked word always
    stays whole: where a word that is not picked overlaps one, it still plays (in part or whole) and gap-plan.txt
    logs the conflict. cin=None (no parakeet_start, the tx.json word list) keeps the old rule: every straddled word
    is kept."""
    hf, out = 0.5 / fps, []

    def place(lo, hi):
        lo, hi = (lo + hf, hi - hf) if hi - lo > 2 * hf else ((lo + hi) / 2,) * 2
        return env.quietest(lo, hi)

    def before(k):
        hi = words[k]["start"]
        return place(hi - guard if k == 0 else min(hi, max(hi - guard, words[k - 1]["end"])), hi)

    def after(k):
        lo = words[k]["end"]
        return place(lo, lo + guard if k + 1 == len(words) else max(lo, min(lo + guard, words[k + 1]["start"])))

    def inside(t):
        return [j for j, w in enumerate(words) if w["start"] < t < w["end"]]

    def start(j):
        return words[j]["start"]

    def end(j):
        return words[j]["end"]

    for i, c in enumerate(edl):
        c = dict(c)
        a, b = c["src_in"], c["src_out"]

        def picked(j):
            return cin is None or a <= cin.get(words[j]["id"], -1.0) < b

        for side in ("src_out", "src_in"):
            old, S, head = c[side], inside(c[side]), side == "src_in"
            if not S:
                continue
            keep = [j for j in S if picked(j)]
            if keep:
                k = S[0] if cin is None else (min(keep, key=start) if head else max(keep, key=end))
                c[side] = before(k) if head else after(k)
                what = "keep '%s'" % words[k]["word"].strip()
            else:
                k = max(S, key=end) if head else min(S, key=start)
                new = after(k) if head else before(k)
                clip = [j for j in range(len(words)) if picked(j) and
                        (start(j) < new and end(j) > old if head else end(j) > new and start(j) < old)]
                if clip:   # moving past the word would clip a picked word: that one stays whole
                    new = before(min(clip, key=start)) if head else after(max(clip, key=end))
                c[side] = new
                what = "leave out '%s' (not picked)" % words[k]["word"].strip()
            log.append("  cut%-3d %8.3f  EDGE moved to %s (%s %.3f -> %.3f)" % (i + 1, old, what, side, old, c[side]))
            # A word not picked plays (in part or whole) when it sits under the new edge, or under the old edge that
            # moved outward to keep a picked word whole: both are logged.
            for j in sorted(set(S if keep else ()) | set(inside(c[side]))) if cin is not None else ():
                if not picked(j):
                    log.append("  cut%-3d %8.3f  EDGE conflict: '%s' was not picked but overlaps a picked word kept "
                               "whole, so it plays (in part or whole)" % (i + 1, c[side], words[j]["word"].strip()))
        out.append(c)
    return out


def plan(edl, env, caps, guard, min_island, protect, holds=(), words=(), beat=None):
    """Return {cut_index: [(del_a, del_b), ...]} in source time, plus a log."""
    log, dels = [], {i: [] for i in range(len(edl))}

    def held(c):
        # A HOLD is picture kept on purpose with nobody talking (a silent visual beat, a reaction, a
        # screen fill). Every silence rule below would delete it as a gap - a reference build lost a
        # silent visual opener that way. A cut inside a hold range gets no deletions at all.
        return any(h0 - 1e-6 <= c["src_in"] and c["src_out"] <= h1 + 1e-6 for h0, h1 in holds)

    def cap_for(kind, cut_i, t):
        for p_from, p_to, p_cap in protect:
            if p_from <= t <= p_to:
                return p_cap, "PROTECT"
        return caps[kind], kind

    def add(i, a, b, head, kind):
        """F-2: a lead, join or tail deletion never takes speech. One holding sustained speech or overlapping an
        edit-map word shrinks to its silent part (head: the kept audio follows it) or is vetoed. Never widened."""
        spans = [s for s in (env.talk_span(a, b),) if s] + [(w["start"], w["end"]) for w in overlaps(words, a, b)]
        if spans:
            a2, b2 = (a, min(s for s, _ in spans) - guard) if head else (max(e for _, e in spans) + guard, b)
            ok = b2 - a2 > 0.02
            log.append("  cut%-3d %8.3f  %-9s %s (speech inside)"
                       % (i + 1, a, kind, "SHRUNK %.3f -> %.3f s" % (b - a, b2 - a2) if ok else "VETO"))
            if not ok:
                return
            a, b = a2, b2
        dels[i].append((a, b))

    # ---- internal gaps: wholly inside one cut -------------------------------
    for i, c in enumerate(edl):
        if held(c):
            log.append("  cut%-3d %8.3f  HOLD (silent beat kept whole)" % (i + 1, c["src_in"])); continue
        sa, sb = env.speech_bounds(c["src_in"], c["src_out"])
        for ga, gb in env.silences(sa, sb, caps["min_gap"]):
            cap, kind = cap_for("internal", i, ga)
            pw = word_before(words, ga) if beat and kind == "internal" else None
            if pw and protected(pw["word"]):
                cap, kind = beat, "beat"     # F-1: capped at the beat length, never at --internal
            else:
                pw = None
            d = gb - ga
            half = max(cap / 2.0, guard)
            kept = d
            if d > 2 * half + 0.02:
                da, db = ga + half, gb - half
                hit = overlaps(words, da, db)
                a2, b2 = clear_of(words, da, db, guard) if hit else (da, db)
                # Sustained-speech test, not peak(): shrinking both ends to dodge one noise window at the
                # floor turned a 14.47 s gap into an 8.43 s hole (a reference build).
                if env.has_speech(da, db):
                    log.append("  cut%-3d %8.3f  %5.3fs  %-9s VETO (speech inside)" % (i + 1, ga, d, kind))
                elif b2 - a2 <= 0.02:
                    # F-2: an edit-map word inside the deletion (a soft word the envelope reads as silence) is kept
                    log.append("  cut%-3d %8.3f  %5.3fs  %-9s VETO (word '%s' inside)"
                               % (i + 1, ga, d, kind, hit[0]["word"].strip()))
                else:
                    if hit:   # F-2: shrink to the longest part a guard clear of the words; never widened
                        log.append("  cut%-3d %8.3f  %5.3fs  %-9s SHRUNK %.3f -> %.3f s (word '%s' inside)"
                                   % (i + 1, ga, d, kind, db - da, b2 - a2, hit[0]["word"].strip()))
                        da, db = a2, b2
                    dels[i].append((da, db))
                    kept = d - (db - da)
                    log.append("  cut%-3d %8.3f  %5.3f -> %5.3f  %-9s  peak %5.1f dB"
                               % (i + 1, ga, d, kept, kind, env.peak(da, db)))
            if pw:
                log.append("  cut%-3d BEAT kept %.3fs after '%s' at %.2f" % (i + 1, kept, pw["word"].strip(), ga))

    # ---- join gaps: cut i's tail + cut i+1's head are adjacent in output -----
    for i in range(len(edl)):
        c = edl[i]
        if held(c):
            continue
        sa, sb = env.speech_bounds(c["src_in"], c["src_out"])
        head, tail = sa - c["src_in"], c["src_out"] - sb
        if i + 1 < len(edl) and held(edl[i + 1]):
            continue   # the incoming cut is a hold: leave its head alone too
        if i == 0:
            kind = "lead"
            budget = caps["lead"]
            if head > budget + 0.02:
                add(i, c["src_in"], c["src_in"] + (head - budget), True, kind)
                log.append("  cut1   %8.3f  %5.3f -> %5.3f  lead      (reel opens on air)"
                           % (c["src_in"], head, budget))
        if i + 1 < len(edl):
            nxt = edl[i + 1]
            nsa, _ = env.speech_bounds(nxt["src_in"], nxt["src_out"])
            nhead = nsa - nxt["src_in"]
            kind = "beat_join" if nxt.get("beat") != c.get("beat") else "join"
            cap, kind = cap_for(kind, i, sb)
            total = tail + nhead
            if total > cap + 0.02:
                excess = total - cap
                # take from the tail first, then the incoming head; never past guard
                take_tail = min(excess, max(0.0, tail - guard))
                if take_tail > 0.02:
                    add(i, c["src_out"] - take_tail, c["src_out"], False, kind)
                take_head = excess - take_tail
                if take_head > 0.02:
                    take_head = min(take_head, max(0.0, nhead - guard))
                    if take_head > 0.02:
                        add(i + 1, nxt["src_in"], nxt["src_in"] + take_head, True, kind)
                log.append("  cut%-3d %8.3f  %5.3f -> %5.3f  %-9s  (tail %.3f + head %.3f)"
                           % (i + 1, sb, total, cap, kind, tail, nhead))
        else:
            if tail > caps["tail"] + 0.02:
                add(i, sb + caps["tail"], c["src_out"], False, "tail")
                log.append("  cut%-3d %8.3f  %5.3f -> %5.3f  tail"
                           % (i + 1, sb, tail, caps["tail"]))
    return dels, log


def segments(edl, dels, env, min_island, words=(), log=None):
    """Apply deletions per cut, then run the orphan guard on the RESULT.

    The guard must see post-split pieces: a keep that straddles a join looks long
    enough until it is split at the cut boundary, which is how a 0.235s orphaned
    word survived the first implementation (fixtures F1).
    F-2: a short piece holding speech (sustained, or an edit-map word) is never dropped.
    """
    out, notes, absorbed, reverted = [], [], 0, 0
    log = [] if log is None else log

    def holds(p):
        return env.has_speech(*p) or bool(overlaps(words, *p))
    for i, c in enumerate(edl):
        d = sorted(dels[i])
        while True:
            merged = []
            for a, b in d:
                if merged and a <= merged[-1][1] + 1e-9:
                    merged[-1][1] = max(merged[-1][1], b)
                else:
                    merged.append([a, b])
            pieces, t = [], c["src_in"]
            for a, b in merged:
                if a > t + 1e-9:
                    pieces.append((t, a))
                t = b
            if t < c["src_out"] - 1e-9:
                pieces.append((t, c["src_out"]))
            runt = next((p for p in pieces if p[1] - p[0] < min_island), None)
            if runt is None:
                break
            # A silent runt is what the deletion meant to remove -> absorb it.
            # A speech-bearing runt is a stranded word -> revert (fixtures F1 vs F2/F3),
            # and revert the SHORTER neighbour: rejoining "That's it." to its sentence costs
            # 0.17 s; restoring the pause after it cost 4.4 s of dead air (a reference build).
            after = next((x for x in d if abs(x[0] - runt[1]) < 1e-6), None)
            before = next((x for x in d if abs(x[1] - runt[0]) < 1e-6), None)
            speech = holds(runt)
            near = [x for x in (after, before) if x]
            if not near:
                break
            victim = min(near, key=lambda x: x[1] - x[0]) if speech else near[0]
            d.remove(victim)
            if speech:
                reverted += 1
                notes.append("  cut%-3d runt %.3fs at %.3f holds speech -> gap restored"
                             % (i + 1, runt[1] - runt[0], runt[0]))
            else:
                absorbed += 1
                log.append("  cut%-3d runt %.3fs at %.3f silent -> absorbed into the deletion"
                           % (i + 1, runt[1] - runt[0], runt[0]))
                d.append((runt[0], victim[1]) if victim is after else (victim[0], runt[1]))
        for p in pieces:
            if p[1] - p[0] >= min_island or holds(p):
                if p[1] - p[0] < min_island:
                    log.append("  cut%-3d KEPT short piece %.3fs at %.3f (holds speech)" % (i + 1, p[1] - p[0], p[0]))
                out.append([round(p[0], 4), round(p[1], 4)])
            else:
                log.append("  cut%-3d DROPPED short piece %.3fs at %.3f (silent)" % (i + 1, p[1] - p[0], p[0]))
    return out, notes, absorbed, reverted


def snap_cuts(pieces_s, fps, speed=1.0, keep=(), log=None):
    """F-3: kept pieces in seconds -> whole frames at the master's fps, and their place in the output.

    src_in_f/src_out_f = round(t * fps). Pieces that touch or overlap after the snap merge. A piece that snaps
    to nothing is dropped, unless its index is in `keep` (it holds words): that one keeps 1 frame. Output frames
    run over the cumulative source frames S: out_in_f = round(S/speed), out_out_f = round((S+len)/speed).
    The one place a cut is quantised: render.py and the tests read its result, cuts.json."""
    log = [] if log is None else log
    frames = []
    for k, (a, b) in enumerate(pieces_s):
        f0, f1 = round(a * fps), round(b * fps)
        if f1 <= f0:
            if k not in keep:
                log.append("  SNAP dropped %.3f-%.3f (under one frame)" % (a, b))
                continue
            f1 = f0 + 1
            log.append("  SNAP kept 1 frame at %.3f (holds words)" % a)
        if frames and frames[-1][0] <= f0 <= frames[-1][1]:
            frames[-1][1] = max(frames[-1][1], f1)
        else:
            frames.append([f0, f1])
    segs, S = [], 0
    for f0, f1 in frames:
        segs.append({"src_in_f": f0, "src_out_f": f1,
                     "out_in_f": round(S / speed), "out_out_f": round((S + f1 - f0) / speed)})
        S += f1 - f0
    return {"fps": fps, "speed": speed, "segments": segs}


def write_cuts(work, cuts):
    """work/cuts.json, and work/segments.json derived from it (seconds, 6 dp): the 0.1.0 path's view."""
    fps = cuts["fps"]
    segs = [[round(s["src_in_f"] / fps, 6), round(s["src_out_f"] / fps, 6)] for s in cuts["segments"]]
    (Path(work) / "cuts.json").write_text(json.dumps(cuts, indent=1), encoding="utf-8")
    (Path(work) / "segments.json").write_text(json.dumps(segs, indent=1), encoding="utf-8")
    return segs


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--edl", required=True)
    ap.add_argument("--internal", type=float, default=0.150)
    ap.add_argument("--join", type=float, default=0.150)
    ap.add_argument("--beat-join", type=float, default=0.320)
    ap.add_argument("--lead", type=float, default=0.080)
    ap.add_argument("--tail", type=float, default=0.100)
    ap.add_argument("--guard", type=float, default=0.070)
    ap.add_argument("--min-island", type=float, default=0.500)
    ap.add_argument("--min-gap", type=float, default=0.100)
    ap.add_argument("--protect", default="", help="src_from:src_to:cap,... (comedic beats)")
    ap.add_argument("--hold", default="", help="src_from:src_to,... cuts inside these ranges are kept whole: silent visual beats")
    ap.add_argument("--words", help="S3's edit_map.json: beats after punctuation and list markers, whole words at the edges")
    ap.add_argument("--beat", type=float, default=None,
                    help="beat length, seconds (else editor.config.json cuts.beat_ms, else 0.300; clamped 0.20-0.40)")
    ap.add_argument("--speed", type=float, default=1.0, help="the speed render.py ships at: sets cuts.json's output frames")
    a = ap.parse_args()

    work = Path(a.work)
    probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
    envj = json.loads((work / "envelope.json").read_text(encoding="utf-8"))
    edl = json.loads(Path(a.edl).read_text(encoding="utf-8"))
    if not edl or "src_in" not in edl[0]:
        die("EDL needs src_in/src_out per cut")

    env = Env(envj["db"], envj["win_s"], probe["calibration"])
    fps = probe["out_rate"]
    words, beat, pre = [], None, []
    if a.words:
        em = json.loads(Path(a.words).read_text(encoding="utf-8"))
        words = [w for w in em["words"] if w.get("status") != "unresolved"]
        cfg = rt.read_config().get("cuts")
        beat = a.beat if a.beat is not None else (
            cfg["beat_ms"] / 1000.0 if isinstance(cfg, dict) and "beat_ms" in cfg else 0.300)
        if not 0.20 <= beat <= 0.40:
            pre.append("  beat %.3fs clamped to %.3fs (0.20-0.40)" % (beat, min(0.40, max(0.20, beat))))
            print(pre[-1].strip())
            beat = min(0.40, max(0.20, beat))
        edl = keep_edge_words(edl, env, words, a.guard, fps, pre, board_cuts(em))
    caps = {"internal": a.internal, "join": a.join, "beat_join": a.beat_join,
            "lead": a.lead, "tail": a.tail, "min_gap": a.min_gap}
    protect = []
    for p in filter(None, a.protect.split(",")):
        f, t, c = p.split(":")
        protect.append((float(f), float(t), float(c)))

    holds = [tuple(map(float, h.split(":"))) for h in filter(None, a.hold.split(","))]
    dels, log = plan(edl, env, caps, a.guard, a.min_island, protect, holds, words, beat)
    log = pre + log
    segs, notes, absorbed, reverted = segments(edl, dels, env, a.min_island, words, log)
    keep = {k for k, p in enumerate(segs) if overlaps(words, *p)}
    cuts = snap_cuts(segs, fps, a.speed, keep, log)
    segs = write_cuts(work, cuts)
    # The frame map exists for the single-recording path too. No media bytes are read here.
    from takes import write_timemap
    reel = next((p for p in (work, *work.parents) if (p / "cut-board.config.json").exists()
                 or (p / "footage/ledger.json").exists()), work.parent)
    try:
        write_timemap(work, cuts, probe.get("input"), reel_dir=reel, take=edl[0].get("take", 1))
    except (OSError, ValueError, KeyError, TypeError) as e:
        die("the source time map could not be written: " + str(e).splitlines()[0])

    before = sum(c["src_out"] - c["src_in"] for c in edl)
    after = sum(b - x for x, b in segs)
    loudest = max([env.peak(x, b) for cut in dels.values() for x, b in cut] or [-120])

    L = ["GAP PLAN - source coordinates, no render required", ""]
    L.append("calibration: silence %.1f dB | speech %.1f dB | sustained run %d windows"
             % (env.cal["gap_db"], env.cal["speech_db"], env.cal["speech_run_windows"]))
    L.append("caps: internal %.0f / join %.0f / beat-join %.0f / lead %.0f / tail %.0f ms | guard %.0f"
             % (a.internal * 1e3, a.join * 1e3, a.beat_join * 1e3, a.lead * 1e3, a.tail * 1e3,
                a.guard * 1e3))
    if words:
        L.append("beat: %.0f ms after punctuation or a list marker (--words)" % (beat * 1e3))
    L.append("frames: %s fps, speed %s (cuts.json)" % (fps, a.speed))
    L += ["", "DECISIONS"] + log
    if notes:
        L += ["", "ORPHAN GUARD"] + notes
    L += ["",
          "runts absorbed : %d" % absorbed,
          "gaps restored  : %d (runt held speech)" % reverted,
          "segments       : %d  (shortest %.3fs)" % (len(segs), min(b - x for x, b in segs)),
          "runtime        : %.2fs -> %.2fs  (removed %.2fs)" % (before, after, before - after),
          "loudest deleted window: %.1f dB" % loudest]
    (work / "gap-plan.txt").write_text("\n".join(L), encoding="utf-8")

    # the targeted checklist - Stage 8 depends on this existing
    C = ["LISTEN FOR THESE - the automated gates cannot hear them", ""]
    for n in notes:
        C.append(n.strip() + "   <- a gap was left long on purpose")
    if loudest > env.cal["speech_db"]:
        C.append("  a deletion reached %.1f dB (above the %.1f dB speech floor) - a word tail"
                 % (loudest, env.cal["speech_db"]))
        C.append("  may end more abruptly than recorded")
    for p in protect:
        C.append("  protected beat %.2f-%.2f held at %.0f ms - is the timing still funny?"
                 % (p[0], p[1], p[2] * 1e3))
    C.append("  any word left stranded between two pauses")
    C.append("  any beat change that now runs together")
    C.append("  the first half second - dead air there costs retention")
    (work / "listen.txt").write_text("\n".join(C), encoding="utf-8")

    print("\n".join(L[-6:]))
    print("wrote %s, %s, %s, %s" % (work / "cuts.json", work / "segments.json", work / "gap-plan.txt",
                                    work / "listen.txt"))


if __name__ == "__main__":
    main()
