#!/usr/bin/env python3
"""Structure gate: reel-scripter Step 4b loop integrity, run on the Checkpoint 2 skeleton.

Usage:  python structure_gate.py <project>/scripts/<slug>.skeleton.md
        python structure_gate.py --angles <project>/reel-build/angles-<date>.md
        python structure_gate.py --selftest   (the gate cases, throwaway tokens, temp projects)

Reads:   the file named on the command line, and the stamps in
         <project>/reel-build/provenance.md. That file is found from the resolved absolute
         path of the file given: for <project>/scripts/<slug>.skeleton.md it is
         <project>/reel-build/provenance.md; for --angles it is the provenance.md beside the
         angles file.
Writes:  <project>/reel-build/provenance.md, on a pass only. A skeleton pass replaces it with
         one line, `passed: <fingerprint of that skeleton's text>`. An --angles pass trims it
         to the angles `from:` line. A failing run writes nothing.
         Prints one line per failure, a Seams line, and a PASS/FAIL line.
Exit:    0 pass; 1 one or more failures (each with its beat number and a fix hint);
         2 unreadable or malformed input, or provenance.md cannot be written (says what is
         wrong).

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

PROVENANCE (SKLLPLG-336: prose call lines were skipped in 4 of 4 walks; a gate is not)
5. Sub-skill stamps: reel-build/provenance.md carries `from: <skill> <stamp>` for angles
   (Step 1), rehooks (Step 2) and hook (Step 3). Each stamp is the line that skill's wrapper
   SKILL.md hands back; only its sha256 prefix lives here, so a stamp cannot be written
   without loading the skill. A missing file, or a missing or wrong stamp, fails with the
   Skill call that makes it. The angles stamp is not required when the skeleton's
   `angle_from: content-plan` (or `open-loop`, `unpicked`) says Step 1's proposal was skipped.
   A `from:` stamp line inside the skeleton or the angles file fails: stamps written into a
   skeleton stay on disk, and the next reel could copy them without calling the skills.
6. Stamps are per run. When a skeleton passes every check, the gate replaces provenance.md
   with `passed: <first 16 hex of sha256 of the skeleton text>`. The same unchanged skeleton
   passes provenance on that line alone. For any other skeleton text that line proves
   nothing, so fresh stamps are needed. A structure failure leaves the file as it is.
7. `--angles <file>`: the Checkpoint 1 gate. Checks only the angles stamp, for the file holding
   Step 1's proposals, so angles runs before the user picks, not later just for its stamp (run6
   called it after Checkpoint 2). No beats are parsed in this mode. On a pass provenance.md is
   rewritten to the valid angles line only, which drops leftovers from an abandoned run. Run
   it once, before Checkpoint 1: a second run would drop the later stamps.

Stdlib only. Deterministic. utf-8 reads (a BOM is tolerated); ASCII-safe stdout.
"""
import hashlib, re, sys
from pathlib import Path

FLAT_RUN = 2
PROV = "reel-build/provenance.md"
BEATS_HEAD = re.compile(r"^[ \t]*#{1,6}[ \t]+beats\b", re.I)
HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]")
BEAT = re.compile(r"^[ \t]*(\d+)\.[ \t]+(.*)$")
TAG = re.compile(r"\[[ \t]*(open|close|hold)(?=[ \t\]])([^\]]*)\]", re.I)
VISUAL = re.compile(r"^[ \t]*visual_loop:[ \t]*(.*?)[ \t]*$", re.I)
LOOP_ID = re.compile(r"^[A-Za-z0-9_-]+$")
FROM = re.compile(r"^[ \t]*from:[ \t]*([A-Za-z]+)[ \t]+(\S+)[ \t]*$", re.I)
STRAY = re.compile(r"^[ \t]*from:[ \t]*([A-Za-z]+)\b", re.I)
PASSED = re.compile(r"^[ \t]*passed:[ \t]*([0-9a-f]{16})[ \t]*$", re.I)
ANGLE_FROM = re.compile(r"^[ \t]*angle_from:[ \t]*(content-plan|open-loop|unpicked)[ \t]*$", re.I)
# ponytail: static stamps; if one leaks into a model's habits, rotate the token in the
# wrapper SKILL.md and its hash here together.
STAMPS = {
    "angles": ("6e86601968d18f5a", 'pipeline-detail.md "Step 1 propose"'),
    "rehooks": ("c0a64be33e004bd8", 'pipeline-detail.md "Step 2"'),
    "hook": ("1181e62c8ec735b6", "step3-options.md, the hook pass"),
}


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


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def check_provenance(text, prov, angles_only=False):
    """text: the skeleton or angles file. prov: the text of provenance.md, or None when it is
    missing or unreadable. Returns (failures, {skill: its valid stamp token})."""
    lines, plines = text.splitlines(), (prov or "").splitlines()
    fails, good, got = [], {}, {}
    if any(m and m.group(1).lower() in STAMPS for m in map(STRAY.match, lines)):
        fails.append(f"a from: stamp line is in this file; stamps do not belong in this file; they "
                     f"go in {PROV}. Fix: delete every from: line here. Each skill's from: line is "
                     f"appended to {PROV} when that skill is called")
    passes = [m.group(1).lower() for m in map(PASSED.match, plines) if m]
    if not angles_only and fingerprint(text) in passes:
        return fails, good
    for ln in plines:
        m = FROM.match(ln)
        if m:
            got.setdefault(m.group(1).lower(), []).append(m.group(2))
    skip_angles = not angles_only and any(ANGLE_FROM.match(ln) for ln in lines)
    for name in (["angles"] if angles_only else STAMPS):
        digest, where = STAMPS[name]
        if name == "angles" and skip_angles:
            continue
        hit = next((t for t in got.get(name, []) if fingerprint(t) == digest), None)
        if hit is not None:
            good[name] = hit
            continue
        if prov is None:
            what = f"{PROV} is missing"
        elif name in got:
            what = f"the from: {name} stamp in {PROV} does not match"
        elif passes:
            what = f"{PROV} holds a pass for a different skeleton text and no fresh from: {name} line"
        else:
            what = f"no from: {name} line in {PROV}"
        fails.append(f"{what}, so the {name} skill was not called for this reel. Fix: call Skill "
                     f"shortform-superengine:{name} ({where}) and append the from: {name} line it "
                     f"returns to {PROV}, verbatim")
    return fails, good


def write_prov(path, line):
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    except OSError as e:
        say(f"UNWRITABLE: {path}: {e}")
        return 2
    return 0


def main(argv):
    angles_only = len(argv) == 3 and argv[1] == "--angles"
    if angles_only:
        argv = argv[:1] + argv[2:]
    if len(argv) != 2:
        say("usage: python structure_gate.py [--angles] <file>   (or --selftest)")
        say(f"       stamps are read from <project>/{PROV}, never from <file>")
        return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        say(f"UNREADABLE: {argv[1]}: {e}")
        return 2
    here = Path(argv[1]).resolve().parent
    prov_path = here / "provenance.md" if angles_only else here.parent / "reel-build" / "provenance.md"
    try:
        with open(prov_path, encoding="utf-8-sig") as f:
            prov = f.read()
    except (OSError, UnicodeDecodeError):
        prov = None
    if angles_only:
        unstamped, good = check_provenance(text, prov, True)
        for what in unstamped:
            say(f"FAIL provenance: {what}. Do this before showing Checkpoint 1.")
        say(f"{'FAIL' if unstamped else 'PASS'}: angles stamp {'missing or wrong' if unstamped else 'present'}.")
        if unstamped:
            return 1
        return write_prov(prov_path, f"from: angles {good['angles']}")
    try:
        beats, visual = parse(text)
    except Malformed as e:
        say(f"MALFORMED: {e}")
        return 2
    fails = sorted(check_early_close(beats, visual) + check_main_paid(beats) + check_flat_run(beats)
                   + check_dead_seam(beats))
    for p, what, fix in fails:
        say(f"FAIL beat {p} ({beats[p - 1]['label']}): {what}. Fix: {fix}.")
    unstamped, _ = check_provenance(text, prov)
    for what in unstamped:
        say(f"FAIL provenance: {what}.")
    seams = " | ".join(f"{b['i']}-{b['i'] + 1} {'+'.join(b['after']) or 'NONE'}" for b in beats[:-1])
    say("Seams: " + (seams or "none (one beat)"))
    if visual:
        say("visual_loop declared: an early close of the main loop is allowed (J3).")
    n_fail = len(fails) + len(unstamped)
    say(f"{'FAIL' if n_fail else 'PASS'}: {len(beats)} beats, {n_fail} failure(s).")
    if n_fail:
        return 1
    return write_prov(prov_path, f"passed: {fingerprint(text)}")

SELFTEST_BEATS = ("## Beats\n1. Hook [open L1]\n2. Secondary hook [open L2]\n3. Body beat 1 [hold L1, L2]\n"
                  "4. Proof [close L2] [open L3]\n5. CTA [close L1, L3]\n")


def selftest():
    """Run the gate cases through main() on throwaway project folders and check each exit code
    and what provenance.md holds afterwards. Uses throwaway tokens and a test-only stamp table
    swapped in for the run; the real stamps never appear in this file."""
    import contextlib, io, tempfile
    global STAMPS
    tok = {n: f"selftest-{n}-token" for n in STAMPS}
    a, r, h = (f"from: {n} {tok[n]}\n" for n in ("angles", "rehooks", "hook"))
    good = "visual_loop: none\n" + SELFTEST_BEATS
    other = good.replace("Proof", "Receipt")
    waived = "angle_from: content-plan\n" + SELFTEST_BEATS
    flat = "## Beats\n1. Hook [open L1]\n2. a\n3. b\n4. c [close L1]\n"
    ang = "# Angles\n1. gut x myth-bust\n2. thyroid x question\n"
    fake = "from: angles abc\nfrom: rehooks abcdef\nfrom: hook not-a-stamp\n"
    stale = "passed: 0123456789abcdef\n"
    done = lambda t: f"passed: {fingerprint(t)}\n"
    KEEP, SAME = "keep", "same"
    # (name, angles mode, file text, provenance.md before, expected exit, provenance.md after)
    # before: None = no file, KEEP = whatever the case above left (same project folder).
    # after: SAME = untouched by the run.
    cases = [
        ("pass: good provenance, then one passed: line", False, good, a + r + h, 0, done(good)),
        ("second: a different skeleton against that passed: file", False, other, KEEP, 1, SAME),
        ("again: the same skeleton against its passed: line", False, good, KEEP, 0, done(good)),
        ("none: provenance.md has no stamps", False, good, "", 1, SAME),
        ("missing: no provenance.md", False, good, None, 1, SAME),
        ("fake: wrong stamps", False, good, fake, 1, SAME),
        ("flatstamped: a structure failure does not clear the file", False, flat, a + r + h, 1, SAME),
        ("nohook: one stamp short", False, good, a + r, 1, SAME),
        ("waiver: angle_from waives the angles stamp", False, waived, r + h, 0, done(waived)),
        ("fresh: an old passed: line plus fresh stamps", False, waived, stale + r + h, 0, done(waived)),
        ("inskel: stamps in the skeleton only", False, a + r + h + good, None, 1, SAME),
        ("stray: stamps in the skeleton and in provenance.md", False, a + r + h + good, a + r + h, 1, SAME),
        ("a-pass: trims provenance.md to the angles line", True, ang, stale + r + a + h, 0, a),
        ("a-none: no angles stamp", True, ang, stale, 1, SAME),
        ("a-missing: no provenance.md", True, ang, None, 1, SAME),
        ("a-fake: wrong angles stamp", True, ang, "from: angles made-up\n", 1, SAME),
        ("a-infile: the stamp is in the angles file", True, ang + a, a, 1, SAME),
    ]
    real = STAMPS
    STAMPS = {n: (hashlib.sha256(tok[n].encode()).hexdigest()[:16], real[n][1]) for n in real}
    ok, tmp = 0, None
    read = lambda p: p.read_text(encoding="utf-8") if p.exists() else None
    try:
        for name, angles, text, before, want, after in cases:
            if before != KEEP or tmp is None:
                if tmp:
                    tmp.cleanup()
                tmp = tempfile.TemporaryDirectory()
            proj = Path(tmp.name)
            (proj / "scripts").mkdir(exist_ok=True)
            (proj / "reel-build").mkdir(exist_ok=True)
            prov = proj / "reel-build" / "provenance.md"
            if before not in (None, KEEP):
                prov.write_text(before, encoding="utf-8", newline="\n")
            target = proj / "reel-build" / "angles-x.md" if angles else proj / "scripts" / "x.skeleton.md"
            target.write_text(text, encoding="utf-8", newline="\n")
            was = read(prov)
            with contextlib.redirect_stdout(io.StringIO()):
                got = main(["structure_gate.py"] + (["--angles"] if angles else []) + [str(target)])
            now = read(prov)
            fine = got == want and now == (was if after == SAME else after)
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} {name}: exit {got}, expected {want}; provenance.md "
                f"{'as expected' if now == (was if after == SAME else after) else 'NOT as expected'}")
    finally:
        STAMPS = real
        if tmp:
            tmp.cleanup()
    say(f"SELFTEST {'PASS' if ok == len(cases) else 'FAIL'}: {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(selftest() if sys.argv[1:] == ["--selftest"] else main(sys.argv))
