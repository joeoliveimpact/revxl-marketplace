#!/usr/bin/env python3
"""Structure gate: reel-scripter Step 4b loop integrity, run on the Checkpoint 2 skeleton.

Usage:  python structure_gate.py <project>/scripts/<slug>.skeleton.md
        python structure_gate.py --angles <project>/reel-build/angles-<date>.md
        python structure_gate.py --storyboard <project>/scripts/<slug>.md   (the final script's
                                                    storyboard table only; writes nothing)
        python structure_gate.py --selftest   (the gate cases, a throwaway salt, temp projects)
        python structure_gate.py --selftest-hook   (hooks/stamp-on-skill.py, storyboard-on-write.py
                                                    and goldmine-answer.py on sample stdin, temp
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
   stamp only when the Skill tool really calls that skill and the model then Reads its method
   file, references/legit-<name>.md (step3-lines.md for rehookslines), in the same session
   (rehooks becomes rehookslines on a `step: 3-lines` call, or on a call with no step token
   after a valid rehooks line); the model never writes one.
   A stamp is stamp(name, project): the first 12 hex of sha256(SALT|name|project folder), so
   a stamp from another project, or a token typed by hand, fails. A missing file, or a missing
   or wrong stamp, fails with the Skill call and method-file Read that make it. The angles stamp is not required when the skeleton's
   `angle_from: content-plan` (or `open-loop`, `unpicked`) names where the picked angle came
   from (Step 1 still runs; that idea is its option 1).
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
   gate says so. `asked-yes` and `asked-no` need a valid `goldmine-asked: <stamp("goldmine",
   project)>` line above them (SKLLPLG-365: a walk wrote asked-yes in the turn that asked,
   before the user answered). hooks/goldmine-answer.py writes that line only when the user
   replies to a message holding GOLD_Q as its own line, word for word, and blocks an asked-
   write before it. An asked- line with no valid goldmine-asked: line, or above it, fails.
   Like the stamps, these lines are cleared by a pass and not needed again on that skeleton's
   `passed:` line.

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
ASKED = re.compile(r"^[ \t]*goldmine-asked:[ \t]*(\S+)[ \t]*$", re.I)
# The Goldmine question, word for word. One definition: hooks/goldmine-answer.py imports it, and
# --selftest checks that hook/SKILL.md and references/step3-options.md each hold it as one line.
GOLD_Q = ("Should I double-check hook options against outliers, breakouts, and existing winners from the "
          "Content Goldmine dashboard? I'd look for anything that could apply to what we're trying to do "
          "with this reel and maximize its engagement, or any ideas that could better the content overall.")
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


def gold_mark(plines, proj):
    """Index of the first valid `goldmine-asked:` line in provenance.md's lines, else None."""
    want = stamp("goldmine", proj)
    return next((k for k, m in enumerate(map(ASKED.match, plines)) if m and m.group(1).lower() == want), None)


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
                     f"recorded in {PROV} automatically when that skill is called and its method file is then Read")
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
        method = ("skills/rehooks/references/step3-lines.md" if name == "rehookslines"
                  else f"skills/{name}/references/legit-{name}.md")
        fails.append(f"{what}, so the {who} was not called for this reel. Fix: call Skill "
                     f"shortform-superengine:{call} ({where}), THEN Read {method}; the stamp is "
                     f"recorded only when that Read follows the call")
    if angles_only:
        return fails, good
    gold = [m.group(1).lower() for m in map(GOLD.match, plines) if m]
    mark = gold_mark(plines, proj)
    early = [k for k, m in enumerate(map(GOLD.match, plines))
             if m and m.group(1).lower() in ("asked-yes", "asked-no") and (mark is None or k < mark)]
    ask = ("step3-options.md, the hook pass: when reel-build/goldmine-run.json shows reads.passed "
           "true, ask the Goldmine question in its exact words and, after the user replies, write "
           "goldmine: asked-yes or goldmine: asked-no; otherwise write goldmine: no-data")
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
    elif early and mark is None:
        fails.append(f"a goldmine: asked- line in {PROV} has no valid goldmine-asked: line above it, so no "
                     f"reply to the Goldmine question asked word for word was seen. Fix: delete that line, "
                     f"ask the question exactly as the fenced line in skills/hook/SKILL.md (its own line, no "
                     f"bold, no quotes), end your turn, and write goldmine: asked-yes or goldmine: asked-no "
                     f"after the user replies (the plugin hook writes goldmine-asked: when they do)")
    elif early:
        fails.append(f"a goldmine: asked- line in {PROV} sits above the goldmine-asked: line, so it was "
                     f"written before the user answered. Fix: delete that line and keep the one written "
                     f"after their reply")
    return fails, good


def write_prov(path, line):
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    except OSError as e:
        say(f"UNWRITABLE: {path}: {e}")
        return 2
    return 0


# Storyboard check on the final script (SKLLPLG-361), run by hooks/storyboard-on-write.py on every
# write. sb_num, sb_seconds, sb_cues and sb_table copy grade.py's num, seconds, cues and storyboard
# (tests/shortform/reel-scripter-walk/grade.py, criterion V), so gate and grader read one table.
MAX_ROW = 5
SCRIPT_HEAD = re.compile(r"^[ \t]*#{1,6}[ \t]+script\b", re.I)
SECTION = re.compile(r"^[ \t]*(hook|secondary|other side|body|proof|cta)[ \t]*:", re.I)


def sb_num(tok):
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", tok)
    return None if not m else float(m.group(2)) + 60 * float(m.group(1) or 0)


def sb_seconds(cell):
    """(start, end) for a range, (None, span) for one number, None when unreadable. end - start,
    or span, is what grade.py's seconds() returns."""
    c = re.sub(r"(?i)\s*(sec(ond)?s?|s)\b", "", cell.replace("~", "").replace("\u2248", "")).strip()
    m = re.fullmatch(r"(\d[\d:.]*)\s*(?:-|\u2013|\u2014|to)\s*(\d[\d:.]*)", c)
    if m and sb_num(m.group(1)) is not None and sb_num(m.group(2)) is not None:
        return sb_num(m.group(1)), sb_num(m.group(2))
    n = sb_num(c)
    return None if n is None else (None, n)


def sb_cues(cell):
    c = cell.strip()
    if re.fullmatch(r"(?i)(none|n/a|-+|\u2014|)", c):
        return 0
    return len([p for p in re.split(r"(?i);|\s\+\s|<br\s*/?>|\s/\s|->|\u2192|\bthen\b", c) if p.strip(" ,.")])


def sb_table(text):
    """(head, seconds col, cue col, beat col, body rows) of the first table grade.py would pick."""
    rows = [[x.strip() for x in l.strip().strip("|").split("|")] for l in text.splitlines() if l.strip().startswith("|")]
    for k, head in enumerate(rows):
        sc = next((i for i, h in enumerate(head) if re.search(r"(?i)sec|time|dur", h)), None)
        cc = next((i for i, h in enumerate(head) if re.search(r"(?i)cue", h)), None)
        if cc is None:
            cc = next((i for i, h in enumerate(head) if re.search(r"(?i)visual", h)), None)
        if sc is None or cc is None:
            continue
        bc = next((i for i, h in enumerate(head) if re.search(r"(?i)beat", h)), 0)
        body = []
        for r in rows[k + 1:]:
            if len(r) != len(head):
                break
            if all(re.fullmatch(r":?-+:?", x) for x in r if x):
                continue
            body.append(r)
        return head, sc, cc, bc, body
    return None


def storyboard_problems(text):
    """Problems with the final script's storyboard table; empty = pass. Each row: a readable
    seconds cell spanning more than 0 and at most MAX_ROW s, exactly one visual cue. Every
    section label under `## Script` (Hook:, Secondary:, Other side:, Body:, Proof:, CTA:) named
    in some beat cell. When every seconds cell is a range: back to back from 0:00 (0.5 s slack)."""
    sb = sb_table(text)
    if not sb:
        return ["no storyboard table: no pipe table with a seconds column and a visual cue column"]
    head, sc, cc, bc, body = sb
    if not body:
        return ["the storyboard table has no rows"]
    probs, spans = [], []
    for i, r in enumerate(body, 1):
        at = f"row {i} ({r[bc]}, {r[sc]})"
        s = sb_seconds(r[sc])
        spans.append(s)
        span = None if s is None else s[1] if s[0] is None else s[1] - s[0]
        if span is None:
            probs.append(f"{at}: the seconds cell cannot be read; write a range like 0:04-0:08")
        elif not 0 < span <= MAX_ROW:
            probs.append(f"{at}: runs {span:g} s; a row runs more than 0 and at most {MAX_ROW} s, so split it")
        n = sb_cues(r[cc])
        if n != 1:
            probs.append(f"{at}: {n} visual cues in '{r[cc]}'; give the row exactly one")
    lines = text.splitlines()
    start = next((k for k, ln in enumerate(lines) if SCRIPT_HEAD.match(ln)), None)
    if start is not None:
        end = next((k for k in range(start + 1, len(lines)) if HEADING.match(lines[k])), len(lines))
        found = {}
        for ln in lines[start + 1:end]:
            m = SECTION.match(ln)
            if m:
                found.setdefault(m.group(1).lower(), m.group(1))
        missing = [v for k, v in found.items() if not any(k in r[bc].lower() for r in body)]
        if missing:
            probs.append(f"script sections with no storyboard row: {', '.join(missing)}; add a row whose "
                         f"Beat cell names each")
    if all(s and s[0] is not None for s in spans):
        prev = 0.0
        for i, (s, r) in enumerate(zip(spans, body), 1):
            if abs(s[0] - prev) > 0.5:
                probs.append(f"row 1 ({r[bc]}, {r[sc]}): the first row starts at 0:00" if i == 1 else
                             f"row {i} ({r[bc]}, {r[sc]}) does not start where row {i - 1} ends "
                             f"({body[i - 2][sc]}); make the times run back to back")
                break
            prev = s[1]
    return probs


# Placeholder rule on the final script (SKLLPLG-370), the one definition: hooks/storyboard-on-write.py runs
# it on every write route (Write, Edit, MultiEdit, Bash, PowerShell), and the walk rig's run-mt2.sh and
# grade.py import it. A final script still holding a part the client has to give is a draft (walks 050-reel2
# and 050-contra saved one at the final path). Measured 10.06.26 before choosing it: no hit on any finished
# walk script, the seed project or any shortform skill doc; a hit on all 8 unfinished final-script writes in
# the walk logs that mark gaps in capitals, [your ...] or [placeholder ...]. Ceiling: a lowercase
# placeholder ([actual culprit], 3 past scripts) is missed, since a lowercase rule also hit [vault] and
# [re-hook] in finished ones.
PH_CUES = r"(?:B-?ROLL|SFX|PAUSE|BEAT|CUT|MUSIC|VO|V/O)\b"
PH_TOKEN = re.compile(r"\[[ \t]*(?:(?!" + PH_CUES + r")[A-Z][A-Z0-9'\u2019 _/&.-]*[A-Z0-9][ \t]*(?::|\](?!\())"
                      r"|(?i:your|needs your input|placeholder)\b[^\]\n]*\])")
PH_LINES = ((re.compile(r"(?im)^[ \t>*_#-]*status[ \t*_]*:[ \t*_]*draft\b"), "a STATUS: DRAFT line"),
            (re.compile(r"\bINCOMPLETE\b"), "INCOMPLETE"),
            (re.compile(r"(?m)^[ \t>*_-]*OPEN[ \t*_]*:"), "an OPEN: note"))


def placeholder_problems(text):
    """What still marks the final script unfinished, each once; empty = finished. An all-caps bracket
    token ([KEYWORD], [YOUR LIST], [THE MISSING PIECE], [NEEDS YOUR INPUT: ...]), a [your ...] or
    [placeholder ...] token in any case, a STATUS: DRAFT line, INCOMPLETE in capitals, or a line starting OPEN:. Not counted: a stage
    cue ([B-ROLL], [SFX: whoosh], [PAUSE], [CUT TO ...]), a one-letter [X], an all-caps markdown link
    [TEXT](url), lowercase tags like [open L1]."""
    found = []
    for m in PH_TOKEN.finditer(text):
        t = m.group(0) if m.group(0).endswith("]") else m.group(0) + " ...]"
        t = t if len(t) <= 40 else t[:35].rstrip() + " ...]"
        if t not in found:
            found.append(t)
    return found + [what for rx, what in PH_LINES if rx.search(text)]


def storyboard_main(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        say(f"UNREADABLE: {path}: {e}")
        return 2
    probs = storyboard_problems(text)
    for p in probs:
        say(f"FAIL storyboard: {p}.")
    say(f"{'FAIL' if probs else 'PASS'}: storyboard, {len(probs)} problem(s).")
    return 1 if probs else 0


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
    mk = "goldmine-asked: @goldmine@\n"
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
        ("asked: asked-yes under the goldmine-asked: line, with Goldmine data", False, good,
         a + r + rl + h + v + mk + "goldmine: asked-yes\n", 0, done(good), {"gm": gm("true")}),
        ("asked-no: asked-no under the goldmine-asked: line", False, good, a + r + rl + h + v + mk + "goldmine: asked-no\n",
         0, done(good), {"gm": gm("true")}),
        ("asked-nomark: asked-yes with no goldmine-asked: line (written before any reply)", False, good,
         a + r + rl + h + v + "goldmine: asked-yes\n", 1, SAME, {"gm": gm("true"), "say": "no valid goldmine-asked: line"}),
        ("asked-early: asked-yes above the goldmine-asked: line, asked-no below it", False, good,
         a + r + rl + h + v + "goldmine: asked-yes\n" + mk + "goldmine: asked-no\n", 1, SAME,
         {"gm": gm("true"), "say": "written before the user answered"}),
        ("asked-fakemark: a hand-typed goldmine-asked: token", False, good,
         a + r + rl + h + v + "goldmine-asked: 0123456789ab\ngoldmine: asked-no\n", 1, SAME,
         {"gm": gm("true"), "say": "no valid goldmine-asked: line"}),
        ("asked-otherproj: a goldmine-asked: line made for another project", False, good,
         a + r + rl + h + v + mk.replace("@", "#") + "goldmine: asked-no\n", 1, SAME,
         {"gm": gm("true"), "say": "no valid goldmine-asked: line"}),
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
    sb_ok, sb_n = storyboard_selftest()
    ph_ok, ph_n = placeholder_selftest()
    ok, n = ok + sb_ok + ph_ok, len(cases) + sb_n + ph_n
    for rel in ("../hook/SKILL.md", "references/step3-options.md"):
        f = Path(__file__).resolve().parent / rel
        fine = GOLD_Q in (ln.strip() for ln in f.read_text(encoding="utf-8-sig").splitlines())
        ok, n = ok + fine, n + 1
        say(f"{'ok ' if fine else 'BAD'} goldq: {rel} holds the Goldmine question word for word, as one line")
    say(f"SELFTEST {'PASS' if ok == n else 'FAIL'}: {ok}/{n}")
    return 0 if ok == n else 1


def storyboard_selftest():
    """storyboard_problems() on synthetic text. (name, text, None for a pass, or a phrase the one
    problem found must hold: a failing case must trip its own rule and nothing else)."""
    head = "## Text overlays\n| Beat | Seconds | Overlay | Visual cue |\n|---|---|---|---|\n"
    sec = "## Script\nHook: a\nSecondary: b\nCTA: c\n"
    tb = lambda *rows, script=sec: script + head + "".join(f"| {b} | {s} | x | {c} |\n" for b, s, c in rows)
    mmss = lambda t: f"{t // 60}:{t % 60:02d}"
    beat = lambda i: "Hook" if i == 0 else "Secondary" if i == 1 else "CTA"
    dash = ("-", " to ", "\u2013")
    good = [("Hook (frame 1)", "0-4", "Close-up"), ("Secondary hook", "4-8", "Cut to kitchen"), ("CTA", "8-12", "Hold")]
    cases = [
        ("sb-valid: a good table passes", tb(*good), None),
        ("sb-list: a plain aligned list, no pipes", sec + "## Text overlays\n0:00  Hook  \"X\"  close-up\n"
         "0:04  CTA  \"Y\"  hold\n", "no storyboard table"),
        ("sb-long: a 0:00-0:08 row", tb(("Hook", "0:00-0:08", "Close-up"), ("Secondary", "0:08-0:12", "Cut"),
                                        ("CTA", "0:12-0:16", "Hold")), "runs 8 s"),
        ("sb-twocues: 'close-up; cut to kitchen' is two cues", tb(good[0], ("Secondary", "4-8",
                                                                  "close-up; cut to kitchen"), good[2]), "2 visual cues"),
        ("sb-comma: 'Hold, slow push-in' is one cue", tb(good[0], ("Secondary", "4-8", "Hold, slow push-in"), good[2]),
         None),
        ("sb-nocue: an empty cue cell", tb(good[0], good[1], ("CTA", "8-12", "")), "0 visual cues"),
        ("sb-mmss: m:ss ranges past a minute, with -, to and an en dash", tb(
            *[(beat(i), f"{mmss(4 * i)}{dash[i % 3]}{mmss(4 * i + 4)}", "Cut") for i in range(16)]),
         None),
        ("sb-gap: 0:04 then 0:06", tb(("Hook", "0:00-0:04", "Cut"), ("Secondary", "0:06-0:10", "Cut"),
                                      ("CTA", "0:10-0:14", "Hold")), "does not start where row 1 ends"),
        ("sb-start: the first row starts at 0:02", tb(("Hook", "0:02-0:06", "Cut"), ("Secondary", "0:06-0:10", "Cut"),
                                                      ("CTA", "0:10-0:14", "Hold")), "the first row starts at 0:00"),
        ("sb-nocta: no CTA row while the script has CTA:", tb(good[0], good[1]), "no storyboard row: CTA"),
        ("sb-span: a span-only cell ('4') skips the back-to-back check", tb(
            ("Hook", "0:02-0:06", "Cut"), ("Secondary", "4", "Cut"), ("CTA", "4", "Hold")), None),
        ("sb-noscript: no ## Script section skips the section check", tb(good[0], script="CTA: c\n"), None),
    ]
    ok = 0
    for name, text, want in cases:
        probs = storyboard_problems(text)
        fine = not probs if want is None else len(probs) == 1 and want in probs[0]
        ok += fine
        say(f"{'ok ' if fine else 'BAD'} {name}: {len(probs)} problem(s){': ' + ' | '.join(probs) if probs else ''}")
    return ok, len(cases)


def placeholder_selftest():
    """placeholder_problems() on synthetic text: (name, text, the one thing it must find, or None for
    no hit). Hits are the walks' own placeholders (050-reel2, 050-contra, 369b-gut, s8)."""
    cases = [
        ("ph-needs: [NEEDS YOUR INPUT]", "Beats 3, 4 and 5 are marked [NEEDS YOUR INPUT].", "[NEEDS YOUR INPUT]"),
        ("ph-needs-colon: [NEEDS YOUR INPUT: ...]", "Body: [NEEDS YOUR INPUT: what they tried, in their words]",
         "[NEEDS YOUR INPUT: ...]"),
        ("ph-keyword: [KEYWORD]", "CTA: Comment [KEYWORD] and I'll send it.", "[KEYWORD]"),
        ("ph-list: [YOUR LIST]", "| Mirror | 0:08 to 0:11 | [YOUR LIST] | cut to counter |", "[YOUR LIST]"),
        ("ph-piece: [THE MISSING PIECE]", "| Bridge | 0:11 to 0:14 | [THE MISSING PIECE] | wider shot |",
         "[THE MISSING PIECE]"),
        ("ph-your: [your real result here], any case", "Proof: [your real result here]", "[your real result here]"),
        ("ph-your-dash: [YOUR ANSWER -- ...]", "Body: [YOUR ANSWER -- eating too fast]", "[YOUR ANSWER -- eating too fast]"),
        ("ph-word: [PLACEHOLDER, a dash, lowercase] (walk s8b-reel2)", "Proof: [PLACEHOLDER \u2014 the real test name]",
         "[PLACEHOLDER \u2014 the real test name]"),
        ("ph-status: a STATUS: DRAFT line", "> STATUS: DRAFT. Fill the beats before recording.", "a STATUS: DRAFT line"),
        ("ph-incomplete: INCOMPLETE", "# Gut myth (INCOMPLETE)", "INCOMPLETE"),
        ("ph-open: an OPEN: note", "  CTA: Comment PACK and I'll send it.\n  OPEN: the keyword is the client's call.",
         "an OPEN: note"),
        ("ph-cues: [B-ROLL], [B-ROLL: kitchen], [SFX: whoosh], [PAUSE], [CUT TO KITCHEN]: no hit",
         "| Hook | 0-3 | x | [B-ROLL] |\n| CTA | 3-6 | x | [B-ROLL: kitchen] [SFX: whoosh] [PAUSE] [CUT TO KITCHEN] |", None),
        ("ph-tags: loop tags [open L1] [close L1, L2]: no hit", "1. Hook [open L1]\n2. CTA [close L1, L2]", None),
        ("ph-link: an all-caps link and a one-letter [X]: no hit", "[DM ME](https://example.com) for [X] more", None),
        ("ph-prose: Open gaps:, Status: approved, lowercase incomplete, OPENING: no hit",
         "Open gaps: none.\nStatus: approved\nAn incomplete routine.\nOPENING line: a question", None),
    ]
    ok = 0
    for name, text, want in cases:
        got = placeholder_problems(text)
        fine = not got if want is None else got == [want]
        ok += fine
        say(f"{'ok ' if fine else 'BAD'} {name}: {got or 'no hit'}")
    return ok, len(cases)


def selftest_hook():
    """Feed hooks/stamp-on-skill.py sample PostToolUse, PreToolUse and UserPromptSubmit stdin in a
    temp home and project. Each case checks the exit code of every run (0, or the case's own code
    for its last run), stderr (empty, or the case's phrase on its last run), empty stdout, no
    stamp-hook.log, the lines provenance.md gains, any keys the case names in one session's entry of
    stamp-pending.json, and
    an empty reel-build/ when the case says so.
    A Skill call alone opens a slot; the stamp comes from a later Read of the method file in the
    same session. Stamps are computed here at run time for temp folders and never printed."""
    import subprocess, tempfile
    hook = Path(__file__).resolve().parents[2] / "hooks" / "stamp-on-skill.py"
    root = hook.parent.parent

    def payload(tool, inp, sid, event="PostToolUse"):
        d = {"hook_event_name": event, "tool_name": tool, "tool_input": inp, "tool_response": "ok"}
        if sid is not None:
            d["session_id"] = sid
        return json.dumps(d)

    call = lambda skill, args="", sid="t": payload("Skill", {"skill": skill, "args": args}, sid)
    rd = lambda path, sid="t": payload("Read", {"file_path": str(path)}, sid)
    sf = "shortform-superengine:"
    legit = lambda n: (root / "skills" / n / "references" / f"legit-{n}.md").as_posix()
    lines3 = (root / "skills" / "rehooks" / "references" / "step3-lines.md").as_posix()
    ang_win = legit("angles").replace("/", "\\")
    # The order check (SKLLPLG-362, 366): ups is one user turn, pre the PreToolUse of a Skill call,
    # run a whole sub-skill call (pre, the call, the Read of its method file).
    pre = lambda skill, args="", sid="t": payload("Skill", {"skill": skill, "args": args}, sid, "PreToolUse")
    up = lambda sid: json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": sid, "prompt": "next"})
    ups = up("t")
    ask = payload("AskUserQuestion", {"questions": [{"question": "Which angle?"}]}, "t")
    run = lambda n, args, method: [pre(sf + n, args), call(sf + n, args), rd(method)]
    first = [ups, pre(sf + "reel-scripter")]
    ang = [ups] + run("angles", "step: 1", legit("angles"))
    step2 = [ups] + run("polarize", "step: 2", legit("polarize")) + run("rehooks", "step: 2", legit("rehooks"))
    hk = [ups, ups] + run("hook", "step: 3-hook", legit("hook"))
    l3 = [ups] + run("rehooks", "step: 3-lines", lines3)
    reel = first + ang + step2 + hk + l3 + l3 + [ups] + run("viral", "step: 4a", legit("viral"))
    # (name, fresh project, stdin, no marker so the cwd decides, skill names of the expected new lines
    #  [, {"exit": code of the last run, "err": phrase its stderr must hold, "prov": provenance.md
    #  text before the case, fresh or not (as the gate's pass rewrites it), "state": keys after in the
    #  stamp-pending.json entry of session "sid" (default t), "empty": reel-build/ holds no file after}])
    # stdin is one payload, or a list of payloads run as separate hook runs in order (one home and
    # project for all); the expected lines are what the whole list adds. A fresh project starts
    # with an empty reel-build/, so a no-stamp case cannot pass just because that folder is missing.
    # A case that is not fresh runs on the project, provenance.md and stamp-pending.json the case
    # above left, so a call and its Read are two cases in a row.
    cases = [
        ("(a) angles call, no Read: no stamp", True, call(sf + "angles", "step: 1"), False, []),
        ("(b) then Read of the plugin's legit-angles.md, backslash form: angles", False, rd(ang_win), False,
         ["angles"]),
        ("(e) second Read of legit-angles.md, no new call: no stamp", False, rd(legit("angles")), False, []),
        ("(c) Read with no prior call, fresh project: no stamp", True, rd(legit("angles")), False, []),
        ("(d) Read, then Skill (wrong order): no stamp", True, [rd(legit("angles")), call(sf + "angles")], False,
         []),
        ("(f) angles call in session A: no stamp", True, call(sf + "angles", sid="A"), False, []),
        ("(f) Read in session B: no stamp", False, rd(legit("angles"), sid="B"), False, []),
        ("(f) control: Read in session A: angles", False, rd(legit("angles"), sid="A"), False, ["angles"]),
        ("(i) angles call before an outside Read: no stamp", True, call(sf + "angles"), False, []),
        ("(i) Read of a legit-angles.md outside the plugin root: no stamp", False,
         rd(Path(tempfile.gettempdir()) / "x" / "plugins" / "shortform-superengine" / "skills" / "angles"
            / "references" / "legit-angles.md"), False, []),
        ("(i) control: Read of the plugin's own legit-angles.md: angles", False, rd(legit("angles")), False,
         ["angles"]),
        ("(h) rehooks step: 2 call: no stamp", True, call(sf + "rehooks", "step: 2\nscript: x"), False, []),
        ("(h) then Read legit-rehooks.md: rehooks", False, rd(legit("rehooks")), False, ["rehooks"]),
        ("rehooks again, no step token, after a valid rehooks line: no stamp yet", False,
         call(sf + "rehooks", "slots: secondary hook"), False, []),
        ("then Read step3-lines.md: rehookslines", False, rd(lines3), False, ["rehookslines"]),
        ("rehooks step: 4b after a valid rehooks line: no stamp yet", False,
         call(sf + "rehooks", "step: 4b\nslots: x"), False, []),
        ("then Read legit-rehooks.md: rehooks, not rehookslines", False, rd(legit("rehooks")), False, ["rehooks"]),
        ("rehooks step: 2 again, after a valid rehooks line: no stamp yet", False, call(sf + "rehooks", "step: 2"),
         False, []),
        ("then Read legit-rehooks.md: rehooks", False, rd(legit("rehooks")), False, ["rehooks"]),
        ("(g) rehooks 3-lines by step token, fresh project: no stamp yet", True,
         call(sf + "rehooks", "Step=3-Lines\nslots: x"), False, []),
        ("(g) Read legit-rehooks.md in the rehookslines slot: no stamp", False, rd(legit("rehooks")), False, []),
        ("(g) Read step3-lines.md: rehookslines", False, rd(lines3), False, ["rehookslines"]),
        ("(j) hook call: no stamp", True, call(sf + "hook", "step: 3-hook"), False, []),
        ("(j) then Read legit-hook.md: hook", False, rd(legit("hook")), False, ["hook"]),
        ("(j) polarize call: no stamp", False, call(sf + "polarize", "step: 2"), False, []),
        ("(j) then Read legit-polarize.md: polarize", False, rd(legit("polarize")), False, ["polarize"]),
        ("(j) viral call, no session_id: no stamp", False, call(sf + "viral", "step: 4a", sid=None), False, []),
        ("(j) then Read legit-viral.md, no session_id: viral", False, rd(legit("viral"), sid=None), False,
         ["viral"]),
        ("non-shortform skill: no write", True, call("other-plugin:hook", "step: 3-hook"), False, []),
        ("malformed stdin: no write", True, "{not json", False, []),
        ("no marker, cwd holds analysis-data.json: angles call, no stamp yet", True, call(sf + "angles"), True, []),
        ("no marker, then Read legit-angles.md: angles", False, rd(legit("angles")), True, ["angles"]),
        ("order: second reel, provenance.md holds only a passed: line, rehooks with no angles call: blocked",
         True, first + [ups, ups, pre(sf + "rehooks", "place rehook slots, skeleton: Hook")], False, [],
         {"exit": 2, "err": "Step 1 has not run for this reel", "prov": "passed: 0123456789abcdef\n"}),
        ("order: a hand-typed angles line does not count: blocked", True, first + [ups, pre(sf + "rehooks", "step: 2")],
         False, [], {"exit": 2, "err": "Step 1 has not run for this reel", "prov": "from: angles 0123456789ab\n"}),
        ("standalone (370): no reel-scripter call this session, hook with no angles stamp: allowed", True,
         [ups] + run("hook", "step: 3-hook", legit("hook")), False, ["hook"]),
        ("standalone (370): rehooks step 2 then hook in one turn, no reel-scripter call: allowed", True,
         [ups] + run("rehooks", "step: 2", legit("rehooks")) + run("hook", "step: 3-hook", legit("hook")), False,
         ["rehooks", "hook"]),
        ("standalone (370): then reel-scripter in that session, rehooks step 2 a turn later: blocked, angles", False,
         [ups, pre(sf + "reel-scripter"), ups, pre(sf + "rehooks", "step: 2")], False, [],
         {"exit": 2, "err": "Step 1 has not run"}),
        ("order: angles, then rehooks in the same turn: blocked at Checkpoint 1", True,
         first + ang + [pre(sf + "rehooks", "step: 2")], False, ["angles"], {"exit": 2, "err": "Checkpoint 1"}),
        ("order: contra2 replay, rehooks 3-lines then viral in one turn: blocked at Checkpoint 3", True,
         first + ang + step2 + hk + l3 + [pre(sf + "viral", "step: 4a")], False,
         ["angles", "polarize", "rehooks", "hook", "rehookslines"], {"exit": 2, "err": "crossing Checkpoint 3"}),
        ("order: the first reel, every step in its own turn: allowed", True, reel, False,
         ["angles", "polarize", "rehooks", "hook", "rehookslines", "rehookslines", "viral"],
         {"state": {"turn": 7, "top": 5, "at": 7}}),
        ("order: then a hook call in viral's turn (backward): allowed, top stays 5", False,
         run("hook", "step: 3-hook", legit("hook")), False, ["hook"], {"state": {"turn": 7, "top": 5, "at": 7}}),
        ("order: then the gate's pass leaves only passed:, rehooks 4b in viral's turn: top resets to 5, allowed (a fix call)",
         False, [pre(sf + "rehooks", "step: 4b")], False, [],
         {"exit": 0, "state": {"top": 5}, "prov": "passed: 0123456789abcdef\n"}),
        ("order (M2a): same session, passed: only, a second reel's rehooks step 2 with no new angles call: ask",
         False, [ups, pre(sf + "rehooks", "step: 2")], False, [],
         {"exit": 2, "err": "Ask the client", "prov": "passed: 0123456789abcdef\n"}),
        ("order: passed: only, reel-scripter again, then rehooks 4b a turn later: allowed, a fix call", False,
         [ups, pre(sf + "reel-scripter"), ups, pre(sf + "rehooks", "step: 4b")], False, [],
         {"prov": "passed: 0123456789abcdef\n"}),
        ("order (M2c): passed: only, angles call and Read, then rehooks step 2 a turn later: allowed", False,
         [ups] + run("angles", "step: 1", legit("angles")) + [ups] + run("rehooks", "step: 2", legit("rehooks")),
         False, ["angles", "rehooks"], {"prov": "passed: 0123456789abcdef\n"}),
        ("order: a new session, passed: only, reel-scripter then rehooks step 2: blocked, angles", False,
         [json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "u", "prompt": "next"}),
          payload("Skill", {"skill": sf + "reel-scripter", "args": ""}, "u", "PreToolUse"),
          json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "u", "prompt": "next"}),
          payload("Skill", {"skill": sf + "rehooks", "args": "step: 2"}, "u", "PreToolUse")], False, [],
         {"exit": 2, "err": "Step 1 has not run for this reel", "prov": "passed: 0123456789abcdef\n"}),
        ("order (M2b): a new session, passed: only, a hook call (Checkpoint 4 fix): allowed", False,
         [up("w"), pre(sf + "hook", "step: 3-hook", "w"), call(sf + "hook", "step: 3-hook", "w"),
          rd(legit("hook"), "w")], False, ["hook"], {"prov": "passed: 0123456789abcdef\n"}),
        ("order: garbage stdin exits 0 and is no turn; angles in reel-scripter's turn: blocked at Checkpoint 0",
         True, first + ["{not json", pre(sf + "angles", "step: 1")], False, [],
         {"exit": 2, "err": "crossing Checkpoint 0"}),
        ("order (M1): a prompt in session b leaves session t's state alone; rehooks step 2 a turn later: allowed",
         True, first + ang + [up("b"), ups] + run("rehooks", "step: 2", legit("rehooks")), False,
         ["angles", "rehooks"], {"state": {"turn": 2, "top": 2, "at": 2}}),
        ("order (M1): a prompt from a session with no state: no file", True, [up("b")], False, [], {"empty": True}),
        ("order (M3): angles, an AskUserQuestion answer, then polarize: allowed", True,
         first + [ups] + run("angles", "step: 1", legit("angles")) + [ask] + run("polarize", "step: 2", legit("polarize")),
         False, ["angles", "polarize"], {"state": {"turn": 2, "top": 2, "at": 2}}),
        ("ask (370 D2): a reel in this session", True, first, False, []),
        ("ask (370 D2): its pass, then polarize step 2: blocked, ask the client", False,
         [ups, pre(sf + "polarize", "step: 2")], False, [],
         {"exit": 2, "err": "Ask the client", "prov": "passed: 0123456789abcdef\n"}),
        ("ask (370 D2): standalone in the same turn as the ask: still blocked", False,
         [pre(sf + "polarize", "standalone: yes\nhot take")], False, [], {"exit": 2, "err": "Ask the client"}),
        ("ask (370 m5): `not standalone` a turn later: still blocked", False,
         [ups, pre(sf + "polarize", "not standalone, part of the reel")], False, [],
         {"exit": 2, "err": "Ask the client"}),
        ("ask (370 m5): `standalone: false` a turn later: still blocked", False,
         [ups, pre(sf + "polarize", "standalone: false")], False, [], {"exit": 2, "err": "Ask the client"}),
        ("ask (370 m5): `not a standalone call` a turn later: still blocked", False,
         [ups, pre(sf + "polarize", "step: 2, part of the reel, not a standalone call")], False, [],
         {"exit": 2, "err": "Ask the client"}),
        ("ask (370 D2): the client answered, standalone a turn later: allowed, order rules off", False,
         [ups, pre(sf + "polarize", "standalone: yes\nhot take")], False, [], {"state": {"rs": False}}),
        ("ask (370 D2): then rehooks step 2 with no angles stamp: allowed", False,
         [ups, pre(sf + "rehooks", "step: 2")], False, []),
        ("per-session (370 M2): reel in progress in t, a hook call and Read in chat b: stamps, t's state kept",
         True, first + ang + [up("b"), pre(sf + "hook", "step: 3-hook", "b"), call(sf + "hook", "step: 3-hook", "b"),
                              rd(legit("hook"), "b")], False, ["angles", "hook"], {"state": {"rs": True, "top": 1}}),
        ("per-session (370 M2): then t's rehooks in the angles turn: still blocked at Checkpoint 1", False,
         [pre(sf + "rehooks", "step: 2")], False, [], {"exit": 2, "err": "Checkpoint 1"}),
        ("per-session (370 M1): after a pass, t calls reel-scripter (a second reel), a one-off hook in b: stamps",
         True, first + [up("b"), pre(sf + "hook", "step: 3-hook", "b"), call(sf + "hook", "step: 3-hook", "b"),
                        rd(legit("hook"), "b")], False, ["hook"],
         {"state": {"rs": True}, "prov": "passed: 0123456789abcdef\n"}),
        ("per-session (370 M1): then t's rehooks step 2 a turn later: blocked, Step 1 (t's rules still on)", False,
         [ups, pre(sf + "rehooks", "step: 2")], False, [], {"exit": 2, "err": "Step 1 has not run for this reel"}),
        ("ask (370 m4): a reel in this session", True, first, False, []),
        ("ask (370 m4): its pass, reel-scripter again, polarize step 2 a turn later: Step 1, no ask", False,
         [ups, pre(sf + "reel-scripter"), ups, pre(sf + "polarize", "step: 2")], False, [],
         {"exit": 2, "err": "Step 1 has not run for this reel", "prov": "passed: 0123456789abcdef\n"}),
        ("ask (370 M3): a reel in this session", True, first, False, []),
        ("ask (370 M3): its pass, polarize step 2: ask", False, [ups, pre(sf + "polarize", "step: 2")], False, [],
         {"exit": 2, "err": "Ask the client", "prov": "passed: 0123456789abcdef\n"}),
        ("ask (370 M3): the client said new reel: angles call and Read: allowed, ask cleared", False,
         [ups] + run("angles", "step: 1", legit("angles")), False, ["angles"], {"state": {"asked": None}}),
        ("ask (370 M3): that reel's pass, standalone polarize a turn later: ask again", False,
         [ups, pre(sf + "polarize", "standalone: yes\nhot take")], False, [],
         {"exit": 2, "err": "Ask the client", "prov": "passed: 1111111111111111\n"}),
        ("ask (370 M3): a newer pass, no new ask, standalone a turn later: ask again (pass changed)", False,
         [ups, pre(sf + "polarize", "standalone: yes\nhot take")], False, [],
         {"exit": 2, "err": "Ask the client", "prov": "passed: 2222222222222222\n"}),
        ("cap (370): 11 chats call reel-scripter: the oldest entry is dropped", True,
         [pre(sf + "reel-scripter", sid=f"s{i}") for i in range(11)], False, [], {"sid": "s0", "state": {"rs": None}}),
        ("cap (370): the next oldest is kept and counts its turn", False, [up("s1")], False, [],
         {"sid": "s1", "state": {"rs": True, "turn": 1}}),
        ("cap (370): a reel in t, then one-off hook calls in 10 other chats: t's entry is kept", True,
         first + [call(sf + "hook", "step: 3-hook", f"o{i}") for i in range(10)], False, [], {"state": {"rs": True}}),
    ]
    ok = 0
    with tempfile.TemporaryDirectory() as t:
        proj = None
        for k, (name, fresh, stdin, cwd_mode, want, *x) in enumerate(cases):
            x = x[0] if x else {}
            if fresh or proj is None:
                proj = Path(t) / f"proj{k}"
                (proj / "reel-build").mkdir(parents=True)
                (proj / "analysis-data.json").write_text("{}", encoding="utf-8")
            if "prov" in x:
                (proj / "reel-build" / "provenance.md").write_text(x["prov"], encoding="utf-8", newline="\n")
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
            rs = [subprocess.run([sys.executable, str(hook)], input=s.encode("utf-8"), capture_output=True,
                                 env=env, cwd=str(proj if cwd_mode else t), timeout=60)
                  for s in ([stdin] if isinstance(stdin, str) else stdin)]
            codes, out = [r.returncode for r in rs], b"".join(r.stdout for r in rs)
            errs = [r.stderr.decode("utf-8", "replace") for r in rs]
            now = prov.read_text(encoding="utf-8") if prov.exists() else ""
            exp = was + "".join(f"from: {n} {stamp(n, proj)}\n" for n in want)
            pend = proj / "reel-build" / "stamp-pending.json"
            st = json.loads(pend.read_text(encoding="utf-8")) if pend.exists() else {}
            st = (st.get("sessions") or {}).get(x.get("sid", "t"), {})
            err_ok = not any(errs[:-1]) and (x["err"] in errs[-1] if "err" in x else not errs[-1])
            st_ok = all(st.get(key) == v for key, v in x.get("state", {}).items())
            st_ok = st_ok and not (x.get("empty") and any((proj / "reel-build").iterdir()))
            fine = (codes == [0] * (len(rs) - 1) + [x.get("exit", 0)] and err_ok and st_ok and not out and now == exp
                    and not (proj / "reel-build" / "stamp-hook.log").exists())
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} {name}: exit {codes[-1]}, expected {x.get('exit', 0)}"
                f"{'' if codes[:-1] == [0] * (len(rs) - 1) else ', an earlier run NOT 0'}, stderr "
                f"{'as expected' if err_ok else 'NOT as expected'}, stdout {'empty' if not out else 'NOT empty'}, "
                f"provenance.md {'as expected' if now == exp else 'NOT as expected'}"
                f"{'' if st_ok else ', stamp-pending.json or reel-build/ NOT as expected'}")
    sb_ok, sb_n = storyboard_hook_selftest()
    gm_ok, gm_n = goldmine_hook_selftest()
    ok, n = ok + sb_ok + gm_ok, len(cases) + sb_n + gm_n
    say(f"SELFTEST-HOOK {'PASS' if ok == n else 'FAIL'}: {ok}/{n}")
    return 0 if ok == n else 1


def storyboard_hook_selftest():
    """Feed hooks/storyboard-on-write.py PostToolUse stdin with every key the real one carries.
    A bad final script must exit 2 with the problems on stderr; every other case exits 0 with
    stdout and stderr empty. Stdout must stay empty in every case. Terminal cases (SKLLPLG-370) run
    PreToolUse Bash|PowerShell, write the case's files as the command would, then PostToolUse, in a
    temp home; the Pre must be silent, record a snapshot only inside a project, and leave none behind."""
    import subprocess, tempfile
    hook = Path(__file__).resolve().parents[2] / "hooks" / "storyboard-on-write.py"
    good = ("## Script\nHook: a\nCTA: b\n## Text overlays\n| Beat | Seconds | Overlay | Visual cue |\n|---|---|---|---|\n"
            "| Hook | 0:00-0:04 | x | Close-up |\n| CTA | 0:04-0:08 | x | Hold |\n")
    bad = good.replace("0:04-0:08", "0:04-0:12")
    ph = good.replace("CTA: b\n", "CTA: Comment [KEYWORD] for the guide\n")
    ph2 = "> STATUS: DRAFT. Beats 3, 4 and 5 are marked [NEEDS YOUR INPUT].\n" + good
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        files = {}
        for key, folder, marker, text in (("bad", "proj", "a", bad), ("good", "proj", "a", good),
                                          ("skel", "proj", "a", bad), ("rb", "rbproj", "r", bad),
                                          ("loose", "loose", None, bad)):
            f = t / folder / "scripts" / ("x.skeleton.md" if key == "skel" else f"{key}.md")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
            if marker == "a":
                (t / folder / "analysis-data.json").write_text("{}", encoding="utf-8")
            elif marker == "r":
                (t / folder / "reel-build").mkdir(exist_ok=True)
            files[key] = f
        # SKLLPLG-370: a reel whose skeleton has not passed (fin), one that has (finok), an existing final
        # script beside an unpassed skeleton with no Text overlays heading (old), a draft, and client notes.
        sk = "## Beats\n1. Hook [open L1]\n2. CTA [close L1]\n"
        for folder, ok_ in (("fin", False), ("finok", True)):
            (t / folder / "scripts").mkdir(parents=True)
            (t / folder / "reel-build").mkdir()
            for stem in ("r", "old"):
                (t / folder / "scripts" / f"{stem}.skeleton.md").write_text(sk, encoding="utf-8")
            if ok_:
                (t / folder / "reel-build" / "provenance.md").write_text(f"passed: {fingerprint(sk)}\n", encoding="utf-8")
        (t / "fin" / "scripts" / "old.md").write_text(bad.replace("## Text overlays\n", ""), encoding="utf-8")
        (t / "proj" / "scripts" / "notes.md").write_text(bad.replace("## Text overlays\n", ""), encoding="utf-8")
        (t / "proj" / "scripts" / "ph.md").write_text(ph, encoding="utf-8")
        files["ph"] = t / "proj" / "scripts" / "ph.md"
        files.update(fin=t / "fin" / "scripts" / "r.md", finok=t / "finok" / "scripts" / "r.md",
                     old=t / "fin" / "scripts" / "old.md", draft=t / "fin" / "scripts" / "r.draft.md",
                     notes=t / "proj" / "scripts" / "notes.md")

        def pl(tool, key, posix=False, event="PostToolUse", content=None):
            f = files[key]
            path = f.as_posix() if posix else str(f).replace("/", "\\")
            edit = {"old_string": "x", "new_string": "x", "replace_all": False}
            content = content if content is not None else f.read_text(encoding="utf-8") if f.exists() else good
            inp = ({"file_path": path, "content": content} if tool == "Write" else
                   dict(edit, file_path=path) if tool == "Edit" else {"file_path": path, "edits": [edit]})
            return json.dumps({"session_id": "t", "transcript_path": str(t / "t.jsonl"), "cwd": str(t),
                               "permission_mode": "default", "hook_event_name": event, "tool_name": tool,
                               "tool_input": inp, "tool_response": {"filePath": path}, "tool_use_id": "toolu_t",
                               "prompt_id": "p", "effort": "medium", "duration_ms": 1})

        # (name, stdin, expected exit, phrase stderr must hold; None = stderr empty)
        cases = [
            ("bad final script, Write, backslash path: exit 2", pl("Write", "bad"), 2,
             "Storyboard check failed for bad.md:"),
            ("bad final script, Write, forward-slash path: exit 2", pl("Write", "bad", True), 2, "runs 8 s"),
            ("bad final script, Edit: exit 2 with the required shape", pl("Edit", "bad"), 2,
             "| Beat | Seconds | Overlay | Visual cue |"),
            ("bad final script, MultiEdit: exit 2", pl("MultiEdit", "bad"), 2, "bad.md"),
            ("bad final script, project marked by reel-build/ only: exit 2", pl("Write", "rb"), 2, "rb.md"),
            ("good final script: silent", pl("Write", "good"), 0, None),
            ("bad *.skeleton.md: silent", pl("Write", "skel"), 0, None),
            ("bad .md in scripts/, parent has no analysis-data.json or reel-build/: silent", pl("Write", "loose"), 0,
             None),
            ("garbage stdin: silent", "{not json", 0, None),
            ("370 Pre Write, new final script, skeleton not passed: blocked, routed to the draft",
             pl("Write", "fin", event="PreToolUse"), 2, "save it as scripts/r.draft.md"),
            ("370 Pre Write, new final script, skeleton passed: allowed", pl("Write", "finok", event="PreToolUse"), 0,
             None),
            ("370 Pre Write of a .draft.md: allowed", pl("Write", "draft", event="PreToolUse"), 0, None),
            ("370 Pre Edit of a final script: allowed", pl("Edit", "fin", event="PreToolUse"), 0, None),
            ("370 Pre Write over an existing final script, skeleton not passed: allowed",
             pl("Write", "old", event="PreToolUse"), 0, None),
            ("370 Post: final script with a sibling skeleton and no Text overlays heading: checked, exit 2",
             pl("Write", "old"), 2, "Storyboard check failed for old.md:"),
            ("370 Post: client notes in scripts/, no skeleton, no Text overlays heading: silent", pl("Write", "notes"),
             0, None),
            ("370 Pre Write, new final script with [KEYWORD], skeleton passed: blocked, routed to the draft",
             pl("Write", "finok", event="PreToolUse", content=ph), 2, "Save it as scripts/r.draft.md instead"),
            ("370 Pre Write, the walk 050-reel2 draft (STATUS: DRAFT, [NEEDS YOUR INPUT]): blocked",
             pl("Write", "finok", event="PreToolUse", content=ph2), 2, "[NEEDS YOUR INPUT], a STATUS: DRAFT line"),
            ("370 Pre Write over an existing final script, with [KEYWORD]: blocked",
             pl("Write", "old", event="PreToolUse", content=ph), 2, "Not saved: scripts/old.md is the final script"),
            ("370 Pre Write of a .draft.md with [KEYWORD]: allowed", pl("Write", "draft", event="PreToolUse", content=ph),
             0, None),
            ("370 Pre Write of client notes with an OPEN: line: allowed",
             pl("Write", "notes", event="PreToolUse", content="OPEN: ask about the launch date\n"), 0, None),
            ("370 Post Edit leaving [KEYWORD] in a final script: exit 2, move it to the draft", pl("Edit", "ph"), 2,
             "Move it to scripts/ph.draft.md now"),
            ("370 Post MultiEdit leaving [KEYWORD] in a final script: exit 2", pl("MultiEdit", "ph"), 2, "[KEYWORD]"),
        ]
        ok = 0
        for name, stdin, want, phrase in cases:
            r = subprocess.run([sys.executable, str(hook)], input=stdin.encode("utf-8"), capture_output=True,
                               env=dict(os.environ), cwd=str(t), timeout=60)
            err = r.stderr.decode("utf-8", "replace")
            fine = r.returncode == want and not r.stdout and (not err if phrase is None else phrase in err)
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} {name}: exit {r.returncode}, stdout {'empty' if not r.stdout else 'NOT empty'}"
                f", stderr {'empty' if not err else 'set'}")

        # SKLLPLG-370 terminal route. (name, tool, skeleton passed (None: no project at all), r.md before or None,
        # {path under the folder: text} the command writes, expected Post exit, phrase stderr must hold; None = empty)
        home = t / "home"
        store = home / ".claude" / "shortform-superengine" / "script-snap"
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
        term = [
            ("Bash creates a final script with [KEYWORD], skeleton passed: exit 2, move it to the draft", "Bash", True,
             None, {"scripts/r.md": ph}, 2, "Move it to scripts/r.draft.md now"),
            ("Bash changes a final script, leaving [KEYWORD]: exit 2", "Bash", True, good, {"scripts/r.md": ph}, 2,
             "[KEYWORD]"),
            ("PowerShell changes a final script, leaving [KEYWORD]: exit 2", "PowerShell", True, good,
             {"scripts/r.md": ph}, 2, "[KEYWORD]"),
            ("Bash creates a final script before the skeleton's passed: line: exit 2, move it to the draft", "Bash",
             False, None, {"scripts/r.md": good}, 2, "has no matching passed: line"),
            ("Bash rewrites an existing final script, skeleton not passed: silent (older reels stay editable)", "Bash",
             False, good, {"scripts/r.md": good + "\n"}, 0, None),
            ("Bash creates a good final script, skeleton passed: silent", "Bash", True, None, {"scripts/r.md": good}, 0,
             None),
            ("Bash creates a final script with a bad storyboard: exit 2", "Bash", True, None, {"scripts/r.md": bad}, 2,
             "Storyboard check failed for r.md:"),
            ("Bash not touching scripts/ (an unfinished final script already there): silent", "Bash", False, ph,
             {"reel-build/notes.txt": "x"}, 0, None),
            ("Bash writes a draft and a skeleton with placeholders: silent", "Bash", False, None,
             {"scripts/r.draft.md": ph, "scripts/n.skeleton.md": ph}, 0, None),
            ("Bash outside a project: silent, nothing recorded", "Bash", None, None, {"scripts/r.md": ph}, 0, None),
        ]
        for k, (name, tool, passed, before, writes, want, phrase) in enumerate(term):
            p = t / f"term{k}"
            (p / "scripts").mkdir(parents=True)
            if passed is not None:
                (p / "analysis-data.json").write_text("{}", encoding="utf-8")
                (p / "reel-build").mkdir()
                (p / "scripts" / "r.skeleton.md").write_text(sk, encoding="utf-8")
                if passed:
                    (p / "reel-build" / "provenance.md").write_text(f"passed: {fingerprint(sk)}\n", encoding="utf-8")
            if before is not None:
                (p / "scripts" / "r.md").write_text(before, encoding="utf-8")
            snap = store / f"toolu_term{k}.json"

            def run(event):
                d = {"session_id": "t", "transcript_path": str(t / "t.jsonl"), "cwd": str(p), "permission_mode": "default",
                     "hook_event_name": event, "tool_name": tool,
                     "tool_input": {"command": "python - <<'E'\nopen('scripts/r.md', 'w').write(s)\nE", "description": "x"},
                     "tool_use_id": f"toolu_term{k}"}
                if event == "PostToolUse":
                    d.update(tool_response={"stdout": "", "stderr": "", "interrupted": False}, duration_ms=1)
                return subprocess.run([sys.executable, str(hook)], input=json.dumps(d).encode("utf-8"),
                                      capture_output=True, env=env, cwd=str(p), timeout=60)
            r0 = run("PreToolUse")
            recorded = snap.is_file()
            for rel, text in writes.items():
                (p / rel).write_text(text, encoding="utf-8")
            r = run("PostToolUse")
            err = r.stderr.decode("utf-8", "replace")
            pre_ok = r0.returncode == 0 and not r0.stdout and not r0.stderr and recorded == (passed is not None)
            fine = (pre_ok and r.returncode == want and not r.stdout and (not err if phrase is None else phrase in err)
                    and not snap.exists())
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} 370 terminal, {name}: Pre {'silent' if pre_ok else 'NOT as expected'}, "
                f"Post exit {r.returncode}, stdout {'empty' if not r.stdout else 'NOT empty'}, stderr "
                f"{'empty' if not err else 'set'}, snapshot {'left behind' if snap.exists() else 'gone'}")
    return ok, len(cases) + len(term)


def goldmine_hook_selftest():
    """Feed hooks/goldmine-answer.py sample stdin, a fresh temp home and project per case. A reply
    to a turn holding GOLD_Q as its own line appends the goldmine-asked: line and prints context;
    a reworded, bolded, lowercased or older question does not. A goldmine: asked- write before
    that line exits 2 (the walk's same-turn write); after it, exit 0. Stamps are never printed."""
    import subprocess, tempfile
    hook = Path(__file__).resolve().parents[2] / "hooks" / "goldmine-answer.py"
    me = lambda t: {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": t}]}}
    you = lambda t: {"type": "user", "message": {"role": "user", "content": t}}
    tool = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "x", "name": "Skill", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}]
    meta = {"type": "user", "isMeta": True, "message": {"content": [{"type": "text", "text": "skill body\n" + GOLD_Q}]}}
    asks = lambda q: [you("write a reel script"), *tool, meta, me("Before I write openings:\n\n" + q)]
    ups = lambda tr: ("UserPromptSubmit", {"prompt": "yes"}, tr)
    auq = lambda q: ("PostToolUse", {"tool_name": "AskUserQuestion",
                                     "tool_input": {"questions": [{"question": q, "header": "Goldmine", "options": []}]}}, None)
    pre = lambda tool_name, inp: ("PreToolUse", {"tool_name": tool_name, "tool_input": inp}, None)
    PROV_AT = "@PROV@"
    # (name, (event, payload fields, transcript entries or None), marker on disk before, expected exit,
    #  marker appended, phrase stderr must hold or None for empty). @PROV@ becomes provenance.md's path.
    cases = [
        ("reply to the exact question: marker and context", ups(asks(GOLD_Q)), False, 0, True, None),
        ("reply already logged in the transcript: marker", ups(asks(GOLD_Q) + [you("yes")]), False, 0, True, None),
        ("curly apostrophes, as the grader allows: marker", ups(asks(GOLD_Q.replace("'", "\u2019"))), False, 0, True,
         None),
        ("reworded, the walk's 'what we're doing': no marker",
         ups(asks(GOLD_Q.replace("what we're trying to do", "what we're doing"))), False, 0, False, None),
        ("bold-wrapped: no marker", ups(asks(f"**{GOLD_Q}**")), False, 0, False, None),
        ("lowercased 'should': no marker", ups(asks("s" + GOLD_Q[1:])), False, 0, False, None),
        ("question one turn back, not in the turn replied to: no marker",
         ups(asks(GOLD_Q) + [you("hm"), me("Writing the openings now.")]), False, 0, False, None),
        ("question only in a skill body (isMeta): no marker", ups([you("x"), meta, me("Here are your openings.")]),
         False, 0, False, None),
        ("AskUserQuestion with the exact question: marker", auq(GOLD_Q), False, 0, True, None),
        ("AskUserQuestion reworded: no marker", auq(GOLD_Q.replace("Should I", "should I")), False, 0, False, None),
        ("Bash append of asked-yes before any reply (the walk's same-turn write): blocked",
         pre("Bash", {"command": f'echo "goldmine: asked-yes" >> "{PROV_AT}"'}), False, 2, False, "Blocked"),
        ("Write of asked-no before any reply: blocked",
         pre("Write", {"file_path": PROV_AT, "content": "goldmine: asked-no\n"}), False, 2, False, GOLD_Q),
        ("Edit appending asked-no after the goldmine-asked: line: allowed",
         pre("Edit", {"file_path": PROV_AT, "old_string": "a", "new_string": "a\ngoldmine: asked-no"}), True, 0, False,
         None),
        ("Edit deleting an early asked-yes line (old_string only): allowed",
         pre("Edit", {"file_path": PROV_AT, "old_string": "goldmine: asked-yes\n", "new_string": ""}), False, 0, False,
         None),
        ("Bash append of goldmine: no-data: allowed", pre("Bash", {"command": f'echo "goldmine: no-data" >> "{PROV_AT}"'}),
         False, 0, False, None),
        ("hand-written goldmine-asked: line: blocked even after a reply",
         pre("Bash", {"command": f'echo "goldmine-asked: 0123456789ab" >> "{PROV_AT}"'}), True, 2, False,
         "only the plugin hook writes"),
        ("garbage stdin: silent", ("raw", "{not json", None), False, 0, False, None),
    ]
    ok = 0
    with tempfile.TemporaryDirectory() as t:
        for k, (name, (event, fields, tr), marked, want, adds, phrase) in enumerate(cases):
            proj, home = Path(t) / f"gproj{k}", Path(t) / f"ghome{k}"
            (proj / "reel-build").mkdir(parents=True)
            st = home / ".claude" / "shortform-superengine"
            (st / "state").mkdir(parents=True)
            (st / ".superengine").write_text(json.dumps({"active_brand": "testbrand"}), encoding="utf-8")
            (st / "state" / "testbrand.json").write_text(json.dumps({"project_path": str(proj)}), encoding="utf-8")
            prov = proj / "reel-build" / "provenance.md"
            mark = f"goldmine-asked: {stamp('goldmine', proj)}\n"
            was = "from: hook x\n" + (mark if marked else "")
            prov.write_text(was, encoding="utf-8", newline="\n")
            if event == "raw":
                stdin = fields
            else:
                d = dict(json.loads(json.dumps(fields).replace(PROV_AT, prov.as_posix())), session_id="t",
                         hook_event_name=event, cwd=str(t))
                if tr is not None:
                    (Path(t) / f"t{k}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in tr), encoding="utf-8")
                    d["transcript_path"] = str(Path(t) / f"t{k}.jsonl")
                stdin = json.dumps(d)
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
            r = subprocess.run([sys.executable, str(hook)], input=stdin.encode("utf-8"), capture_output=True, env=env,
                               cwd=str(t), timeout=60)
            err, out = r.stderr.decode("utf-8", "replace"), r.stdout.decode("utf-8", "replace")
            now = prov.read_text(encoding="utf-8")
            try:
                ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""
            except (ValueError, KeyError, TypeError):
                ctx = None
            fine = (r.returncode == want and now == was + (mark if adds else "")
                    and (("goldmine: asked-yes" in (ctx or "")) if adds else out == "")
                    and (not err if phrase is None else phrase in err))
            ok += fine
            say(f"{'ok ' if fine else 'BAD'} goldmine hook, {name}: exit {r.returncode}, provenance.md "
                f"{'as expected' if now == was + (mark if adds else '') else 'NOT as expected'}, "
                f"stdout {'context' if ctx else 'empty' if not out else 'NOT as expected'}, stderr {'set' if err else 'empty'}")
    return ok, len(cases)


if __name__ == "__main__":
    sys.exit(selftest() if sys.argv[1:] == ["--selftest"] else selftest_hook() if sys.argv[1:] == ["--selftest-hook"]
             else storyboard_main(sys.argv[2]) if len(sys.argv) == 3 and sys.argv[1] == "--storyboard"
             else main(sys.argv))
