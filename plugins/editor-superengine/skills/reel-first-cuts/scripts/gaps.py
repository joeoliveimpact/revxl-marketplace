#!/usr/bin/env python3
"""Stage 4 - gap tightening, entirely in SOURCE coordinates.

The reference build did this against a rendered master, which made Stage 4 depend
on Stage 6's output - a circular pipeline that forced two 4K renders. Here every
measurement comes from the source envelope produced by probe.py, so nothing needs
a render to exist.

Reads : work/probe.json, work/envelope.json, an EDL with src_in/src_out per cut
Writes: work/segments.json (source ranges to keep), work/gap-plan.txt,
        work/listen.txt (the targeted checklist Stage 8 hands to the human)
"""
import argparse, json, sys
from pathlib import Path


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
        """Silent runs strictly inside [a,b]."""
        out, run = [], None
        lo, hi = self.i(a), self.i(b)
        for k in range(lo, hi + 1):
            if self.db[k] < self.cal["gap_db"]:
                run = k if run is None else run
            else:
                if run is not None and (k - run) * self.win >= min_gap:
                    out.append((run * self.win, k * self.win))
                run = None
        if run is not None and (hi + 1 - run) * self.win >= min_gap:
            out.append((run * self.win, (hi + 1) * self.win))
        return out

    def speech_bounds(self, a, b):
        """First and last moment of real speech inside a cut."""
        lo, hi = self.i(a), self.i(b)
        first = last = None
        for k in range(lo, hi + 1):
            if self.db[k] > self.cal["speech_db"]:
                first = k * self.win if first is None else first
                last = (k + 1) * self.win
        return (first, last) if first is not None else (a, b)


def plan(edl, env, caps, guard, min_island, protect):
    """Return {cut_index: [(del_a, del_b), ...]} in source time, plus a log."""
    log, dels = [], {i: [] for i in range(len(edl))}

    def cap_for(kind, cut_i, t):
        for p_from, p_to, p_cap in protect:
            if p_from <= t <= p_to:
                return p_cap, "PROTECT"
        return caps[kind], kind

    # ---- internal gaps: wholly inside one cut -------------------------------
    for i, c in enumerate(edl):
        sa, sb = env.speech_bounds(c["src_in"], c["src_out"])
        for ga, gb in env.silences(sa, sb, caps["min_gap"]):
            cap, kind = cap_for("internal", i, ga)
            d = gb - ga
            half = max(cap / 2.0, guard)
            if d <= 2 * half + 0.02:
                continue
            da, db = ga + half, gb - half
            while db - da > 0.02 and env.peak(da, db) > env.cal["speech_db"]:
                da += env.win; db -= env.win
            if db - da <= 0.02:
                log.append("  cut%-3d %8.3f  %5.3fs  %-9s VETO (speech inside)" % (i + 1, ga, d, kind))
                continue
            dels[i].append((da, db))
            log.append("  cut%-3d %8.3f  %5.3f -> %5.3f  %-9s  peak %5.1f dB"
                       % (i + 1, ga, d, d - (db - da), kind, env.peak(da, db)))

    # ---- join gaps: cut i's tail + cut i+1's head are adjacent in output -----
    for i in range(len(edl)):
        c = edl[i]
        sa, sb = env.speech_bounds(c["src_in"], c["src_out"])
        head, tail = sa - c["src_in"], c["src_out"] - sb
        if i == 0:
            kind = "lead"
            budget = caps["lead"]
            if head > budget + 0.02:
                dels[i].append((c["src_in"], c["src_in"] + (head - budget)))
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
                    dels[i].append((c["src_out"] - take_tail, c["src_out"]))
                take_head = excess - take_tail
                if take_head > 0.02:
                    take_head = min(take_head, max(0.0, nhead - guard))
                    if take_head > 0.02:
                        dels[i + 1].append((nxt["src_in"], nxt["src_in"] + take_head))
                log.append("  cut%-3d %8.3f  %5.3f -> %5.3f  %-9s  (tail %.3f + head %.3f)"
                           % (i + 1, sb, total, cap, kind, tail, nhead))
        else:
            if tail > caps["tail"] + 0.02:
                dels[i].append((sb + caps["tail"], c["src_out"]))
                log.append("  cut%-3d %8.3f  %5.3f -> %5.3f  tail"
                           % (i + 1, sb, tail, caps["tail"]))
    return dels, log


def segments(edl, dels, env, min_island):
    """Apply deletions per cut, then run the orphan guard on the RESULT.

    The guard must see post-split pieces: a keep that straddles a join looks long
    enough until it is split at the cut boundary, which is how a 0.235s orphaned
    word survived the first implementation (fixtures F1).
    """
    out, notes, absorbed, reverted = [], [], 0, 0
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
            # A speech-bearing runt is a stranded word -> revert (fixtures F1 vs F2/F3).
            after = next((x for x in d if abs(x[0] - runt[1]) < 1e-6), None)
            before = next((x for x in d if abs(x[1] - runt[0]) < 1e-6), None)
            victim = after or before
            if victim is None:
                break
            d.remove(victim)
            if env.has_speech(*runt):
                reverted += 1
                notes.append("  cut%-3d runt %.3fs at %.3f holds speech -> gap restored"
                             % (i + 1, runt[1] - runt[0], runt[0]))
            else:
                absorbed += 1
                d.append((runt[0], victim[1]) if victim is after else (victim[0], runt[1]))
        for p in pieces:
            if p[1] - p[0] >= min_island:
                out.append([round(p[0], 4), round(p[1], 4)])
    return out, notes, absorbed, reverted


def main():
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
    a = ap.parse_args()

    work = Path(a.work)
    probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
    envj = json.loads((work / "envelope.json").read_text(encoding="utf-8"))
    edl = json.loads(Path(a.edl).read_text(encoding="utf-8"))
    if not edl or "src_in" not in edl[0]:
        die("EDL needs src_in/src_out per cut")

    env = Env(envj["db"], envj["win_s"], probe["calibration"])
    caps = {"internal": a.internal, "join": a.join, "beat_join": a.beat_join,
            "lead": a.lead, "tail": a.tail, "min_gap": a.min_gap}
    protect = []
    for p in filter(None, a.protect.split(",")):
        f, t, c = p.split(":")
        protect.append((float(f), float(t), float(c)))

    dels, log = plan(edl, env, caps, a.guard, a.min_island, protect)
    segs, notes, absorbed, reverted = segments(edl, dels, env, a.min_island)

    before = sum(c["src_out"] - c["src_in"] for c in edl)
    after = sum(b - x for x, b in segs)
    loudest = max([env.peak(x, b) for cut in dels.values() for x, b in cut] or [-120])

    L = ["GAP PLAN - source coordinates, no render required", ""]
    L.append("calibration: silence %.1f dB | speech %.1f dB | sustained run %d windows"
             % (env.cal["gap_db"], env.cal["speech_db"], env.cal["speech_run_windows"]))
    L.append("caps: internal %.0f / join %.0f / beat-join %.0f / lead %.0f / tail %.0f ms | guard %.0f"
             % (a.internal * 1e3, a.join * 1e3, a.beat_join * 1e3, a.lead * 1e3, a.tail * 1e3,
                a.guard * 1e3))
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
    (work / "segments.json").write_text(json.dumps(segs, indent=1), encoding="utf-8")

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
    print("wrote %s, %s, %s" % (work / "segments.json", work / "gap-plan.txt", work / "listen.txt"))


if __name__ == "__main__":
    main()
