#!/usr/bin/env python3
"""Structure gate: reel-scripter Step 4b loop integrity, run on the Checkpoint 2 skeleton.

Usage:  python structure_gate.py <project>/scripts/<slug>.skeleton.md
        python structure_gate.py --angles <project>/reel-build/angles-<date>.md
        python structure_gate.py --selftest   (the gate cases, a throwaway salt, temp projects)
        python structure_gate.py --selftest-hook   (hooks/stamp-on-skill.py on sample stdin, temp
                                                    home and project)

Reads:   the file named on the command line, and the stamps and the goldmine: line in
         <project>/reel-build/provenance.md. That file is found from the resolved absolute
         path of the file given: for <project>/scripts/<slug>.skeleton.md it is
         <project>/reel-build/provenance.md; for --angles it is the provenance.md beside the
         angles file. A skeleton run also reads <project>/reel-build/goldmine-run.json when it
         exists (check 9).
Writes:  <project>/reel-build/provenance.md, on a pass only. A skeleton pass replaces it with
         one line, `passed: <fingerprint of that skeleton's text>` (the stamps and the
         goldmine: line go). An --angles pass trims it to the angles `from:` line. A failing
         run writes nothing.
         Prints one line per failure, a Seams line, and a PASS/FAIL line.
Exit:    0 pass; 1 one or more failures (each with its beat number and a fix hint);
         2 unreadable or malformed input, or provenance.md cannot be written (says what is
         wrong).

Doctrine: references/pipeline-detail.md "Step 4b" (dead seam, early close, flat run) and
SKILL.md Step 4b. Beat-number checks only: a skeleton carries no per-beat seconds (D8).

SKELETON FORMAT (Checkpoint 2 writes exactly this shape)

    # <reel angle> ... skeleton
    angle_kind: statement
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
  already is; a bad or missing ID; no `[open ...]` tag anywhere; no `angle_kind:` line, more
  than one, or a value outside the list below.
- `angle_kind:` is required, one line anywhere: the body-structures.md bucket this skeleton
  came from. Closed list (case does not matter): question, numbered/list, myth-bust/negation,
  contrarian/curiosity, pain-callout, personal/story, statement.
- An "Other side" beat is a beat whose label starts `Other side` (case does not matter): the
  one line that names what the other camp believes. Tag it `[hold <main loop>]` like any beat
  that deepens a loop.
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
5. Sub-skill stamps: reel-build/provenance.md carries `from: <name> <stamp>` for angles
   (Step 1), rehooks (Step 2), rehookslines (rehooks again at Step 3, in its Step-3 mode; that
   stamp sits in rehooks' references/step3-lines.md, read only in that mode, so the Step 2
   call never shows it), hook (Step 3), viral (Step 4a, every reel) and polarize (Step 2;
   required only when check 8 names it). The plugin hook hooks/stamp-on-skill.py writes each
   stamp when the Skill tool really calls that skill (rehooks becomes rehookslines on a
   `step: 3-lines` call, or on a call with no step token after a valid rehooks line); the
   model never writes one.
   A stamp is stamp(name, project): the first 12 hex of sha256(SALT|name|project folder), so
   a stamp from another project, or a token typed by hand, fails. A missing file, or a missing
   or wrong stamp, fails with the Skill call that makes it. The angles stamp is not required when the skeleton's
   `angle_from: content-plan` (or `open-loop`, `unpicked`) says Step 1's proposal was skipped.
   A `from:` stamp line (any of the six names) inside the skeleton or the angles file fails: stamps written into a
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

ANGLE KIND AND GOLDMINE
8. Other side: angle_kind myth-bust/negation or contrarian/curiosity fails without an "Other
   side" beat (R6: after the opening, before the turn). Those two kinds, and an "Other side"
   beat on any kind, also need the `from: polarize` stamp (check 5).
9. Goldmine: provenance.md carries a `goldmine:` line, `asked-yes`, `asked-no` or `no-data`
   (P-M8a: the Goldmine question is asked at the Step 3 hook pass only when Goldmine data
   exists). `no-data` fails when <project>/reel-build/goldmine-run.json shows reads.passed
   true. A goldmine-run.json that cannot be read as a JSON object counts as no data, and the
   gate says so. `asked-no` always passes: the gate cannot tell whether the question was
   asked. Like the stamps, the line is cleared by a pass and not needed again on that
   skeleton's `passed:` line.

Stdlib only. Deterministic. utf-8 reads (a BOM is tolerated); ASCII-safe stdout.
"""
import hashlib, json, os, re, sys
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
KIND = re.compile(r"^[ \t]*angle_kind:[ \t]*(.*?)[ \t]*$", re.I)
KINDS = ("question", "numbered/list", "myth-bust/negation", "contrarian/curiosity", "pain-callout",
         "personal/story", "statement")
SIDE_KINDS = ("myth-bust/negation", "contrarian/curiosity")
SIDE = re.compile(r"other side\b", re.I)
GOLD = re.compile(r"^[ \t]*goldmine:[ \t]*(.*?)[ \t]*$", re.I)
GOLD_OK = ("asked-yes", "asked-no", "no-data")
# ponytail: SALT sits in this readable file, so the stamp stops copying, not a model that runs
# Python on purpose. Rotate SALT if stamps ever show up computed by hand.
SALT = "46a8fef6cc5482af3a22925b94463a0d"
WHERE = {
    "angles": 'pipeline-detail.md "Step 1 propose"',
    "rehooks": 'pipeline-detail.md "Step 2"',
    "rehookslines": "step3-options.md, the secondary-hook pass",
    "hook": "step3-options.md, the hook pass",
    "polarize": 'pipeline-detail.md "Step 2"',
    "viral": 'pipeline-detail.md "Step 4a"',
}


def stamp(name, project_dir):
    """The stamp for skill `name` in this project: first 12 hex of sha256(SALT|name|dir). The dir
    is resolved, written with forward slashes, and lowercased on Windows. One definition: the
    hook hooks/stamp-on-skill.py imports it."""
    d = Path(project_dir).resolve().as_posix()
    if os.name == "nt":
        d = d.lower()
    return hashlib.sha256(f"{SALT}|{name}|{d}".encode("utf-8")).hexdigest()[:12]


class Malformed(Exception):
    pass


def say(s):
    print(s.encode("ascii", "replace").decode("ascii"))


def parse(text):
    """Return (beats, visual, kind). A beat is {"i", "label", "events", "after"}."""
    lines = text.splitlines()
    visual = False
    for k, ln in enumerate(lines):
        m = VISUAL.match(ln)
        if m:
            if not m.group(1):
                raise Malformed(f"line {k + 1}: visual_loop: has no value; describe the visual loop or delete the line")
            visual = visual or m.group(1).lower() not in ("none", "no", "n/a", "false")
    kinds = [m.group(1).lower() for m in map(KIND.match, lines) if m]
    if len(kinds) != 1:
        raise Malformed(("no angle_kind: line" if not kinds else "more than one angle_kind: line")
                        + "; keep one line `angle_kind: <bucket>`, the body-structures.md bucket this "
                        + "skeleton came from: " + ", ".join(KINDS))
    if kinds[0] not in KINDS:
        raise Malformed(f"angle_kind: {kinds[0] or '(empty)'} is not a body-structures.md bucket; "
                        + "use one of: " + ", ".join(KINDS))
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
    return beats, visual, kinds[0]


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


def check_other_side(beats, kind):
    if kind not in SIDE_KINDS or any(SIDE.match(b["label"]) for b in beats):
        return []
    return [f"angle_kind: {kind} needs an Other side beat and this skeleton has none. Fix: add a "
            f"one-line beat labelled Other side after the secondary hook and before the turn, tagged "
            f"[hold <main loop>]; its line comes from Skill shortform-superengine:polarize "
            f"({WHERE['polarize']})"]


def goldmine_state(path):
    """(data, note). data: goldmine-run.json shows reads.passed true. note: why a file that is
    there was treated as no data, else None."""
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return False, None
    except (OSError, ValueError) as e:
        return False, f"{path.name} could not be read as JSON ({e}); treated as no Goldmine data"
    if not isinstance(d, dict):
        return False, f"{path.name} is not a JSON object; treated as no Goldmine data"
    reads = d.get("reads")
    return isinstance(reads, dict) and reads.get("passed") is True, None


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def check_provenance(text, prov, proj, angles_only=False, polarize=False, data=False):
    """text: the skeleton or angles file. prov: the text of provenance.md, or None when it is
    missing or unreadable. proj: the project folder the stamps must be made for. polarize: the polarize stamp is required (check 8). data:
    goldmine-run.json shows reads.passed true (check 9). Returns (failures, {name: its valid
    stamp token})."""
    lines, plines = text.splitlines(), (prov or "").splitlines()
    fails, good, got = [], {}, {}
    if any(m and m.group(1).lower() in WHERE for m in map(STRAY.match, lines)):
        fails.append(f"a from: stamp line is in this file; stamps do not belong in this file; they "
                     f"go in {PROV}. Fix: delete every from: line here. Each skill's from: line is "
                     f"recorded in {PROV} automatically when that skill is called")
    passes = [m.group(1).lower() for m in map(PASSED.match, plines) if m]
    if not angles_only and fingerprint(text) in passes:
        return fails, good
    for ln in plines:
        m = FROM.match(ln)
        if m:
            got.setdefault(m.group(1).lower(), []).append(m.group(2))
    skip_angles = not angles_only and any(ANGLE_FROM.match(ln) for ln in lines)
    for name in (["angles"] if angles_only else [n for n in WHERE if n != "polarize" or polarize]):
        where = WHERE[name]
        if name == "angles" and skip_angles:
            continue
        hit = next((t for t in got.get(name, []) if t.lower() == stamp(name, proj)), None)
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
        who, call = f"{name} skill", name
        if name == "rehookslines":
            who, call = "rehooks skill in Step-3 mode", "rehooks in Step-3 mode (args step: 3-lines)"
        if name == "polarize":
            who += " (this reel's angle_kind or its Other side beat needs it)"
        fails.append(f"{what}, so the {who} was not called for this reel. Fix: call Skill "
                     f"shortform-superengine:{call} ({where}); the stamp is recorded automatically "
                     f"when the skill is called")
    if angles_only:
        return fails, good
    gold = [m.group(1).lower() for m in map(GOLD.match, plines) if m]
    ask = ("step3-options.md, the hook pass: when reel-build/goldmine-run.json shows reads.passed "
           "true, ask the Goldmine question and write goldmine: asked-yes or goldmine: asked-no; "
           "otherwise write goldmine: no-data")
    if not gold:
        fails.append(f"no goldmine: line in {PROV}. Fix: append one, per {ask}")
    elif any(v not in GOLD_OK for v in gold):
        fails.append(f"a goldmine: line in {PROV} is not asked-yes, asked-no or no-data. Fix: keep "
                     f"one valid line, per {ask}")
    elif "no-data" in gold and data:
        fails.append(f"goldmine: no-data in {PROV}, but reel-build/goldmine-run.json shows "
                     f"reads.passed true, so Goldmine data exists. Fix: ask the Goldmine question "
                     f"({ask.split(':')[0]}), then replace the line with goldmine: asked-yes or "
                     f"goldmine: asked-no")
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
        say(f"       stamps and the goldmine: line are read from <project>/{PROV}, never from <file>")
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
    proj = prov_path.parent.parent
    if angles_only:
        unstamped, good = check_provenance(text, prov, proj, True)
        for what in unstamped:
            say(f"FAIL provenance: {what}. Do this before showing Checkpoint 1.")
        say(f"{'FAIL' if unstamped else 'PASS'}: angles stamp {'missing or wrong' if unstamped else 'present'}.")
        if unstamped:
            return 1
        return write_prov(prov_path, f"from: angles {good['angles']}")
    try:
        beats, visual, kind = parse(text)
    except Malformed as e:
        say(f"MALFORMED: {e}")
        return 2
    fails = sorted(check_early_close(beats, visual) + check_main_paid(beats) + check_flat_run(beats)
                   + check_dead_seam(beats))
    for p, what, fix in fails:
        say(f"FAIL beat {p} ({beats[p - 1]['label']}): {what}. Fix: {fix}.")
    side = check_other_side(beats, kind)
    for what in side:
        say(f"FAIL other side: {what}.")
    data, note = goldmine_state(prov_path.parent / "goldmine-run.json")
    if note:
        say(f"NOTE: {note}.")
    polarize = kind in SIDE_KINDS or any(SIDE.match(b["label"]) for b in beats)
    unstamped, _ = check_provenance(text, prov, proj, polarize=polarize, data=data)
    for what in unstamped:
        say(f"FAIL provenance: {what}.")
    seams = " | ".join(f"{b['i']}-{b['i'] + 1} {'+'.join(b['after']) or 'NONE'}" for b in beats[:-1])
    say("Seams: " + (seams or "none (one beat)"))
    if visual:
        say("visual_loop declared: an early close of the main loop is allowed (J3).")
    n_fail = len(fails) + len(side) + len(unstamped)
    say(f"{'FAIL' if n_fail else 'PASS'}: {len(beats)} beats, {n_fail} failure(s).")
    if n_fail:
        return 1
    return write_prov(prov_path, f"passed: {fingerprint(text)}")

SELFTEST_BEATS = ("## Beats\n1. Hook [open L1]\n2. Secondary hook [open L2]\n3. Body beat 1 [hold L1, L2]\n"
                  "4. Proof [close L2] [open L3]\n5. CTA [close L1, L3]\n")
SELFTEST_SIDE = ("## Beats\n1. Hook [open L1]\n2. Secondary hook [open L2]\n3. Other side ... the camp says X [hold L1]\n"
                 "4. Body beat 1 [hold L1, L2]\n5. Proof [close L2] [open L3]\n6. CTA [close L1, L3]\n")


def selftest():
    """Run the gate cases through main() on throwaway project folders and check each exit code
    and what provenance.md holds afterwards (and, where a case names it, a phrase the gate must
    print). A throwaway SALT is swapped in for the run, so real stamps never appear here. In
    case text, @name@ becomes stamp(name, that case's project) and #name# the stamp for another
    project folder. One case switches the stray-stamp check off to prove stamps are read only
    from provenance.md, never from the skeleton."""
    import contextlib, io, tempfile
    global SALT, STRAY
    a, r, rl, h, p, v = (f"from: {n} @{n}@\n" for n in ("angles", "rehooks", "rehookslines", "hook", "polarize", "viral"))
    g = "goldmine: no-data\n"
    full = a + r + rl + h + v + g
    kind = lambda k: f"angle_kind: {k}\n"
    good = kind("statement") + "visual_loop: none\n" + SELFTEST_BEATS
    other = good.replace("Proof", "Receipt")
    waived = "angle_from: content-plan\n" + kind("statement") + SELFTEST_BEATS
    flat = kind("statement") + "## Beats\n1. Hook [open L1]\n2. a\n3. b\n4. c [close L1]\n"
    myth = kind("myth-bust/negation") + SELFTEST_SIDE
    contra = kind("contrarian/curiosity") + SELFTEST_SIDE
    ang = "# Angles\n1. gut x myth-bust\n2. thyroid x question\n"
    fake = "from: angles abc\nfrom: rehooks abcdef\nfrom: hook not-a-stamp\n" + rl + v + g
    stale = "passed: 0123456789abcdef\n"
    gm = lambda passed: '{"schema": "goldmine-run/1", "reads": {"passed": %s}}' % passed
    done = lambda t: f"passed: {fingerprint(t)}\n"
    KEEP, SAME = "keep", "same"
    # (name, angles mode, file text, provenance.md before, expected exit, provenance.md after
    #  [, {"say": phrase the output must hold, "gm": goldmine-run.json text, "nostray": True}])
    # before: None = no file, KEEP = whatever the case above left (same project folder).
    # after: SAME = untouched by the run.
    cases = [
        ("pass: good provenance, then one passed: line", False, good, full, 0, done(good)),
        ("second: a different skeleton against that passed: file", False, other, KEEP, 1, SAME),
        ("again: the same skeleton against its passed: line", False, good, KEEP, 0, done(good)),
        ("none: provenance.md has no stamps", False, good, "", 1, SAME),
        ("missing: no provenance.md", False, good, None, 1, SAME),
        ("fake: wrong stamps", False, good, fake, 1, SAME),
        ("flatstamped: a structure failure does not clear the file", False, flat, full, 1, SAME),
        ("nohook: one stamp short", False, good, a + r + rl + v + g, 1, SAME),
        ("waiver: angle_from waives the angles stamp", False, waived, r + rl + h + v + g, 0, done(waived)),
        ("fresh: an old passed: line plus fresh stamps", False, waived, stale + r + rl + h + v + g, 0, done(waived)),
        ("inskel: stamps in the skeleton only", False, a + r + rl + h + v + good, None, 1, SAME),
        ("stray: stamps in the skeleton and in provenance.md", False, a + r + rl + h + v + good, full, 1, SAME),
        ("a-pass: trims provenance.md to the angles line", True, ang, stale + r + rl + a + h + p + v + g, 0, a),
        ("a-none: no angles stamp", True, ang, stale, 1, SAME),
        ("a-missing: no provenance.md", True, ang, None, 1, SAME),
        ("a-fake: wrong angles stamp", True, ang, "from: angles made-up\n", 1, SAME),
        ("a-infile: the stamp is in the angles file", True, ang + a, a, 1, SAME),
        ("nolines: no rehookslines stamp, the hint names rehooks in Step-3 mode", False, good,
         a + r + h + v + g, 1, SAME, {"say": "Skill shortform-superengine:rehooks in Step-3 mode"}),
        ("noviral: no viral stamp", False, good, a + r + rl + h + g, 1, SAME, {"say": "no from: viral line"}),
        ("nokind: no angle_kind: line", False, "visual_loop: none\n" + SELFTEST_BEATS, full, 2, SAME,
         {"say": "no angle_kind: line"}),
        ("badkind: angle_kind outside the closed list", False, kind("myth-bust") + SELFTEST_BEATS, full, 2, SAME,
         {"say": "not a body-structures.md bucket"}),
        ("twokind: two angle_kind: lines", False, kind("statement") + good, full, 2, SAME,
         {"say": "more than one angle_kind: line"}),
        ("myth: myth-bust, an Other side beat and the polarize stamp", False, myth, full + p, 0, done(myth)),
        ("contra: contrarian, an Other side beat and the polarize stamp", False, contra, full + p, 0, done(contra)),
        ("myth-noside: myth-bust with no Other side beat", False, kind("myth-bust/negation") + SELFTEST_BEATS,
         full + p, 1, SAME, {"say": "needs an Other side beat"}),
        ("contra-noside: contrarian with no Other side beat", False, kind("contrarian/curiosity") + SELFTEST_BEATS,
         full + p, 1, SAME, {"say": "needs an Other side beat"}),
        ("myth-nopolarize: an Other side beat, no polarize stamp", False, myth, full, 1, SAME,
         {"say": "no from: polarize line"}),
        ("side-nopolarize: a statement reel with an Other side beat, no polarize stamp", False,
         kind("statement") + SELFTEST_SIDE, full, 1, SAME, {"say": "no from: polarize line"}),
        ("nogold: no goldmine: line", False, good, a + r + rl + h + v, 1, SAME, {"say": "no goldmine: line"}),
        ("badgold: goldmine: value outside the list", False, good, a + r + rl + h + v + "goldmine: maybe\n", 1,
         SAME, {"say": "is not asked-yes, asked-no or no-data"}),
        ("nodata-lie: no-data while goldmine-run.json shows reads.passed true", False, good, full, 1, SAME,
         {"gm": gm("true"), "say": "Goldmine data exists"}),
        ("asked: asked-yes with Goldmine data", False, good, a + r + rl + h + v + "goldmine: asked-yes\n", 0,
         done(good), {"gm": gm("true")}),
        ("nodata-ok: no-data, goldmine-run.json shows reads.passed false", False, good, full, 0, done(good),
         {"gm": gm("false")}),
        ("badjson: a malformed goldmine-run.json counts as no data, and says so", False, good, full, 0,
         done(good), {"gm": "{not json", "say": "treated as no Goldmine data"}),
        ("nostray: stray check off, stamps in the skeleton still do not count", False, a + r + rl + h + v + good,
         g, 1, SAME, {"nostray": True, "say": "no from: angles line"}),
        ("otherproj: stamps made for a different project folder", False, good, full.replace("@", "#"), 1, SAME,
         {"say": "stamp in reel-build/provenance.md does not match"}),
        ("static: a hand-written static token", False, good, a + r + rl + "from: hook 0123456789ab\n" + v + g, 1,
         SAME, {"say": "the from: hook stamp in reel-build/provenance.md does not match"}),
    ]
    real, real_stray = SALT, STRAY
    SALT = "selftest-throwaway-salt"
    ok, tmp = 0, None
    read = lambda p: p.read_text(encoding="utf-8") if p.exists() else None
    try:
        for name, angles, text, before, want, after, *x in cases:
            x = x[0] if x else {}
            if before != KEEP or tmp is None:
                if tmp:
                    tmp.cleanup()
                tmp = tempfile.TemporaryDirectory()
            proj = Path(tmp.name)
            fill = lambda s: s if s in (None, KEEP, SAME) else re.sub(
                r"([@#])(\w+)\1", lambda m: stamp(m.group(2), proj if m.group(1) == "@" else proj / "other"), s)
            text, before, after = fill(text), fill(before), fill(after)
            (proj / "scripts").mkdir(exist_ok=True)
            (proj / "reel-build").mkdir(exist_ok=True)
            prov = proj / "reel-build" / "provenance.md"
            if before not in (None, KEEP):
                prov.write_text(before, encoding="utf-8", newline="\n")
            if "gm" in x:
                (proj / "reel-build" / "goldmine-run.json").write_text(x["gm"], encoding="utf-8", newline="\n")
            target = proj / "reel-build" / "angles-x.md" if angles else proj / "scripts" / "x.skeleton.md"
            target.write_text(text, encoding="utf-8", newline="\n")
            was = read(prov)
            out = io.StringIO()
            STRAY = re.compile(r"(?!)") if x.get("nostray") else real_stray
            with contextlib.redirect_stdout(out):
                got = main(["structure_gate.py"] + (["--angles"] if angles else []) + [str(target)])
            STRAY = real_stray
            now = read(prov)
            said = x.get("say", "") in out.getvalue()
            fine = got == want and now == (was if after == SAME else after) and said
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} {name}: exit {got}, expected {want}; provenance.md "
                f"{'as expected' if now == (was if after == SAME else after) else 'NOT as expected'}"
                f"{'' if said else '; output lacks: ' + x['say']}")
    finally:
        SALT, STRAY = real, real_stray
        if tmp:
            tmp.cleanup()
    say(f"SELFTEST {'PASS' if ok == len(cases) else 'FAIL'}: {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


def selftest_hook():
    """Feed hooks/stamp-on-skill.py sample PostToolUse stdin in a temp home and project. Each case
    checks exit 0, empty stdout, and the lines provenance.md gains. Stamps are computed here at
    run time for temp folders and never printed."""
    import subprocess, tempfile
    hook = Path(__file__).resolve().parents[2] / "hooks" / "stamp-on-skill.py"
    call = lambda skill, args="": json.dumps({"session_id": "t", "hook_event_name": "PostToolUse",
                                               "tool_name": "Skill", "tool_input": {"skill": skill, "args": args},
                                               "tool_response": "ok"})
    sf = "shortform-superengine:"
    # (name, fresh project, stdin, no marker so the cwd decides, skill names of the expected new lines)
    cases = [
        ("angles: one from: angles line", True, call(sf + "angles", "step: 1"), False, ["angles"]),
        ("rehooks first call: from: rehooks", False, call(sf + "rehooks", "step: 2\nscript: x"), False, ["rehooks"]),
        ("rehooks again, no step token, after a valid rehooks line: rehookslines", False,
         call(sf + "rehooks", "slots: secondary hook"), False, ["rehookslines"]),
        ("rehooks step: 4b after a valid rehooks line: rehooks, not rehookslines", False,
         call(sf + "rehooks", "step: 4b\nslots: x"), False, ["rehooks"]),
        ("rehooks step: 2, fresh project: rehooks", True, call(sf + "rehooks", "step: 2"), False, ["rehooks"]),
        ("rehooks step: 2 again, after a valid rehooks line: rehooks", False, call(sf + "rehooks", "step: 2"),
         False, ["rehooks"]),
        ("rehooks 3-lines by step token, no rehooks line yet: rehookslines", True,
         call(sf + "rehooks", "Step=3-Lines\nslots: x"), False, ["rehookslines"]),
        ("non-shortform skill: no write", True, call("other-plugin:hook", "step: 3-hook"), False, []),
        ("malformed stdin: no write", True, "{not json", False, []),
        ("no marker, cwd holds analysis-data.json: angles", True, call(sf + "angles"), True, ["angles"]),
    ]
    ok = 0
    with tempfile.TemporaryDirectory() as t:
        proj = None
        for k, (name, fresh, stdin, cwd_mode, want) in enumerate(cases):
            if fresh or proj is None:
                proj = Path(t) / f"proj{k}"
                proj.mkdir()
                (proj / "analysis-data.json").write_text("{}", encoding="utf-8")
            home = Path(t) / f"home{k}"
            if not cwd_mode:
                st = home / ".claude" / "shortform-superengine"
                (st / "state").mkdir(parents=True)
                (st / ".superengine").write_text(json.dumps({"active_brand": "testbrand"}), encoding="utf-8")
                (st / "state" / "testbrand.json").write_text(json.dumps({"project_path": str(proj)}), encoding="utf-8")
            else:
                home.mkdir()
            prov = proj / "reel-build" / "provenance.md"
            was = prov.read_text(encoding="utf-8") if prov.exists() else ""
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
            r = subprocess.run([sys.executable, str(hook)], input=stdin.encode("utf-8"), capture_output=True,
                               env=env, cwd=str(proj if cwd_mode else t), timeout=60)
            now = prov.read_text(encoding="utf-8") if prov.exists() else ""
            exp = was + "".join(f"from: {n} {stamp(n, proj)}\n" for n in want)
            fine = r.returncode == 0 and not r.stdout and now == exp
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} {name}: exit {r.returncode}, stdout {'empty' if not r.stdout else 'NOT empty'}, "
                f"provenance.md {'as expected' if now == exp else 'NOT as expected'}")
    say(f"SELFTEST-HOOK {'PASS' if ok == len(cases) else 'FAIL'}: {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(selftest() if sys.argv[1:] == ["--selftest"] else selftest_hook() if sys.argv[1:] == ["--selftest-hook"]
             else main(sys.argv))
