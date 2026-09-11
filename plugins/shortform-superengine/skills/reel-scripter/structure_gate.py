#!/usr/bin/env python3
"""Structure gate: reel-scripter Step 4b loop integrity, run on the Checkpoint 2 skeleton.

Usage:  py -3.12 structure_gate.py <project>/scripts/<slug>.skeleton.md

Reads:   the skeleton file named on the command line.
Writes:  nothing. Prints one line per failure, a Seams line, and a PASS/FAIL line.
Exit:    0 pass; 1 one or more failures (each with its beat number and a fix hint);
         2 unreadable or malformed input (says what is wrong).

Doctrine: references/pipeline-detail.md "Step 4b" (dead seam, early close, flat run) and
SKILL.md Step 4b. Beat-number checks only: a skeleton carries no per-beat seconds (D8).

SKELETON FORMAT (Checkpoint 2 writes exactly this shape)

    # <reel angle> ... skeleton
    visual_loop: <what the viewer watches resolve, and the beat it resolves on>

    ## Beats
    1. Hook ... blame moves from Claude to the viewer [open L1]
    2. Anchor ... the thing on their own screen
    3. Secondary hook ... contrast re-hook, deepens L1 [open L2]
    4. Reveal ... name the one thing [close L1, L2] [open L3]
    5. CTA ... one ask [close L3]

- A `## Beats` heading is required (any heading level, case-insensitive). Beats are the
  numbered lines `N. <text>` from that heading to the next heading or the end of the file.
  Numbers run 1, 2, 3 ... in order. Every beat gets a number, the secondary hook and the CTA
  included. One line per beat.
- Loop tags sit on the beat line: `[open ID ...]`, `[close ID ...]` and `[hold ID ...]`. An
  ID is letters, digits, `_` or `-`; several IDs are separated by spaces, commas or `+`; case
  does not matter. Tags apply in the order written, so `[close L1] [open L3]` hands one loop
  to the next inside one beat. `[hold ID]` marks a beat that deepens a loop already open: it
  opens and closes nothing, but it counts as pull, so it breaks a flat run. A beat with no
  tag keeps whatever is open and counts as flat: name the loop a beat deepens, or it is flat.
- Malformed (exit 2): no Beats heading or no beat lines; numbers out of order; a tag on a
  line that is not a beat; closing or holding a loop that is not open; opening one that
  already is; a bad or missing ID; no `[open ...]` tag anywhere.
- `visual_loop:` is optional, one line anywhere. Omit it when there is no visual loop
  (`none`, `no`, `n/a` and `false` count as omitted; an empty value is malformed). Declaring
  it lets the main loop close early (J3: the visual carries the tension). It changes nothing
  else, so tag the visual loop on its beats like any loop (`[open V]` ... `[close V]`) and
  the seams it carries count as open.
- Any other text (title, notes, what was trimmed) is ignored.

CHECKS (n = number of beats, p = a beat's number)
1. Early close: the main loop is the first loop opened. Fails when its first close lands at
   beat p with 3*p <= 2*n, before the last third (5 beats: beat 4 or later passes; 6 beats:
   beat 5 or later). Skipped when visual_loop is declared.
2. Flat run: FLAT_RUN or more consecutive beats with no tag (a `[hold]` tag is a tag).
   FLAT_RUN = 2, the doctrine's "2+ consecutive beats" (pipeline-detail.md Step 4b).
3. Dead seam: the seam after beat p (p < n) has no loop open. Seams after the final payoff
   (the last beat that closes any loop) are exempt.
4. Unpaid main loop: the main loop never closes. Fails whether or not visual_loop is
   declared (J3 excuses an early close, never a missing one).

Stdlib only. Deterministic. utf-8 reads (a BOM is tolerated); ASCII-safe stdout.
"""
import re, sys

FLAT_RUN = 2
BEATS_HEAD = re.compile(r"^[ \t]*#{1,6}[ \t]+beats\b", re.I)
HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]")
BEAT = re.compile(r"^[ \t]*(\d+)\.[ \t]+(.*)$")
TAG = re.compile(r"\[[ \t]*(open|close|hold)(?=[ \t\]])([^\]]*)\]", re.I)
VISUAL = re.compile(r"^[ \t]*visual_loop:[ \t]*(.*?)[ \t]*$", re.I)
LOOP_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class Malformed(Exception):
    pass


def say(s):
    print(s.encode("ascii", "replace").decode("ascii"))


def parse(text):
    """Return (beats, visual). A beat is {"i", "label", "events", "after"}."""
    lines = text.splitlines()
    visual = False
    for k, ln in enumerate(lines):
        m = VISUAL.match(ln)
        if m:
            if not m.group(1):
                raise Malformed(f"line {k + 1}: visual_loop: has no value; describe the visual loop or delete the line")
            visual = visual or m.group(1).lower() not in ("none", "no", "n/a", "false")
    start = next((k for k, ln in enumerate(lines) if BEATS_HEAD.match(ln)), None)
    if start is None:
        raise Malformed("no '## Beats' heading; put the numbered beat lines under one")
    end = next((k for k in range(start + 1, len(lines)) if HEADING.match(lines[k])), len(lines))
    beats, open_now = [], set()
    for k in range(start + 1, end):
        m = BEAT.match(lines[k])
        if not m:
            if TAG.search(lines[k]):
                raise Malformed(f"line {k + 1}: loop tag on a line that is not a numbered beat; keep each beat on one line")
            continue
        want = len(beats) + 1
        if int(m.group(1)) != want:
            raise Malformed(f"line {k + 1}: beat number {m.group(1)}, expected {want}; number beats 1, 2, 3 ... in order")
        events = []
        for kind, ids in TAG.findall(m.group(2)):
            kind, toks = kind.lower(), [t for t in re.split(r"[ \t,+]+", ids) if t]
            if not toks:
                raise Malformed(f"line {k + 1}: [{kind}] tag names no loop")
            for t in toks:
                if not LOOP_ID.match(t):
                    raise Malformed(f"line {k + 1}: '{t}' is not a loop id (letters, digits, _ or -)")
                lid = t.upper()
                if kind == "open" and lid in open_now:
                    raise Malformed(f"line {k + 1}: opens {lid}, which is already open")
                if kind != "open" and lid not in open_now:
                    raise Malformed(f"line {k + 1}: {kind}s {lid}, which is not open")
                if kind != "hold":
                    (open_now.add if kind == "open" else open_now.discard)(lid)
                events.append((kind, lid))
        label = TAG.sub("", m.group(2)).strip()
        beats.append({"i": want, "label": label[:48], "events": events, "after": sorted(open_now)})
    if not beats:
        raise Malformed("no numbered beat lines under the Beats heading")
    if not any(kind == "open" for b in beats for kind, _ in b["events"]):
        raise Malformed("no [open ...] tag on any beat; tag the loops each beat opens and closes")
    return beats, visual


def check_early_close(beats, visual):
    if visual:
        return []
    n = len(beats)
    main = next(lid for b in beats for kind, lid in b["events"] if kind == "open")
    p = next((b["i"] for b in beats if ("close", main) in b["events"]), None)
    if p is None or 3 * p > 2 * n:
        return []
    k = 2 * n // 3 + 1
    return [(p, f"early close: main loop {main} pays off at beat {p} of {n}, before the last third",
             f"hold the {main} payoff until beat {k} or later; if a visual loop carries the reel past it, declare visual_loop:")]


def check_main_paid(beats):
    main = next(lid for b in beats for kind, lid in b["events"] if kind == "open")
    if any(("close", main) in b["events"] for b in beats):
        return []
    p = next(b["i"] for b in beats if ("open", main) in b["events"])
    k = 2 * len(beats) // 3 + 1
    return [(p, f"unpaid loop: main loop {main} opens at beat {p} and never closes",
             f"close {main} on a beat from {k} on, with the payoff it promised")]


def check_flat_run(beats):
    fails, run = [], []
    for b in beats + [None]:
        if b is not None and not b["events"]:
            run.append(b["i"])
            continue
        if len(run) >= FLAT_RUN:
            fails.append((run[0], f"flat run: beats {run[0]} to {run[-1]} neither open nor close a loop",
                          f"turn beat {run[0]} into a question-chain link that opens a loop beat {run[0] + 1} pays"))
        run = []
    return fails


def check_dead_seam(beats):
    last_close = max((b["i"] for b in beats if any(kind == "close" for kind, _ in b["events"])), default=0)
    return [(b["i"], f"dead seam between beat {b['i']} and beat {b['i'] + 1}: no loop is open",
             "hold a reveal longer, or plant a connective re-hook at this seam that opens a loop a later beat pays")
            for b in beats[:-1] if not b["after"] and b["i"] < last_close]


def main(argv):
    if len(argv) != 2:
        say("usage: py -3.12 structure_gate.py <project>/scripts/<slug>.skeleton.md")
        return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        say(f"UNREADABLE: {argv[1]}: {e}")
        return 2
    try:
        beats, visual = parse(text)
    except Malformed as e:
        say(f"MALFORMED: {e}")
        return 2
    fails = sorted(check_early_close(beats, visual) + check_main_paid(beats) + check_flat_run(beats)
                   + check_dead_seam(beats))
    for p, what, fix in fails:
        say(f"FAIL beat {p} ({beats[p - 1]['label']}): {what}. Fix: {fix}.")
    seams = " | ".join(f"{b['i']}-{b['i'] + 1} {'+'.join(b['after']) or 'NONE'}" for b in beats[:-1])
    say("Seams: " + (seams or "none (one beat)"))
    if visual:
        say("visual_loop declared: an early close of the main loop is allowed (J3).")
    say(f"{'FAIL' if fails else 'PASS'}: {len(beats)} beats, {len(fails)} failure(s).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
