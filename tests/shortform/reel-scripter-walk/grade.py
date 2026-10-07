"""Grade one reel-scripter walk transcript against RUBRIC.md.
Usage: py -3.12 grade.py <log> [--fixture gut|contra] [--goldmine on|off|override] [--run2]

<log> is a name under <state>/logs (or a path). <state> is RS_WALK_STATE (default
<home>/rs-walk-state), the folder run-mt2.sh writes to. The project graded is <state>/proj
(gut, the default) or <state>/proj-contra (contra). The plugin under test, its gate and its
trigger hook are the ones in this repo, found from this file's own location. The gate is
not re-run (its stamps are per project, so a copy cannot pass); grading writes nothing.

--goldmine sets what criterion Q expects of the Goldmine data (reel-build/goldmine-run.json):
  on        the data is there (reads.passed) and the hook pass used it
  override  the data is there, the client said to use their own hook / ignore the data, none used
  off       no data, none used
Default: off for gut (its seed has no data), on for contra. A gut walk with a Goldmine copy
added after reset.sh needs --goldmine on or override.

Prints one PASS or FAIL line per criterion, then `VERDICT: PASS` or `VERDICT: FAIL` with the
failed criteria. Exit 0 on PASS, 1 on FAIL, 2 on bad usage. A criterion whose input is absent
FAILS and says why."""
import importlib.util, json, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing the gate must not write into the plugin tree
PLUGIN = Path(__file__).resolve().parents[3] / "plugins/shortform-superengine"
GATE = PLUGIN / "skills/reel-scripter/structure_gate.py"
SF = "shortform-superengine:"
GOLDMINE_Q = ("Should I double-check hook options against outliers, breakouts, and existing winners from "
              "the Content Goldmine dashboard? I'd look for anything that could apply to what we're trying "
              "to do with this reel and maximize its engagement, or any ideas that could better the content "
              "overall.")
DELETED = ("hook-formulas.md", "hook-mastery.md", "opener-patterns.md", "retention-psychology.md",
           "reel-scripter/references/say-this-not-that.md")
OPTIONS_MIN = 300  # ponytail: an assistant text this long counts as options shown; tune if narration runs long
PART2 = re.compile(r"follow\W+for\W+part\W*(2|two)\b", re.I)


def norm(p):
    return str(p).replace("\\", "/").rstrip("/").lower()


def usage():
    print(__doc__)
    sys.exit(2)


args = sys.argv[1:]
if not args or args[0].startswith("--"):
    usage()
log_name, fixture, run2, goldmine = args[0], "gut", False, None
rest = args[1:]
while rest:
    a = rest.pop(0)
    if a == "--fixture" and rest and rest[0] in ("gut", "contra"):
        fixture = rest.pop(0)
    elif a == "--goldmine" and rest and rest[0] in ("on", "off", "override"):
        goldmine = rest.pop(0)
    elif a == "--run2":
        run2 = True
    else:
        usage()
goldmine = goldmine or ("on" if fixture == "contra" else "off")

D = Path(os.environ.get("RS_WALK_STATE") or Path.home() / "rs-walk-state")
PROJ = D / ("proj" if fixture == "gut" else "proj-contra")
spec = importlib.util.spec_from_file_location("structure_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

raw = (D / "logs" / log_name).read_text("utf-8", errors="replace")
ev = [json.loads(l) for l in raw.splitlines() if l.strip().startswith("{")]
inits = [e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"]
res = next((e for e in reversed(ev) if e.get("type") == "result"), {})

# One flat, ordered list of what happened: ("skill", name, step, turn, blocked, args), ("read", path), ("text", text),
# ("tool", name, input). turn: the result events before it (one per user turn). blocked: its tool_result is an
# error (a plugin hook stopped it), so it never ran and counts as no call.
errored = {c.get("tool_use_id") for e in ev if e.get("type") == "user"
           and isinstance(e.get("message", {}).get("content"), list) for c in e["message"]["content"]
           if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error")}
seq, turn = [], 0
for e in ev:
    if e.get("type") == "result":
        turn += 1
    if e.get("type") != "assistant":
        continue
    for c in e.get("message", {}).get("content", []):
        if c.get("type") == "tool_use":
            name, inp = c.get("name"), c.get("input") or {}
            if name == "Skill":
                a = inp.get("args", "")
                a = a if isinstance(a, str) else json.dumps(a)
                m = re.search(r"(?i)\bstep(?:[ \t]*[:=][ \t]*|[ \t]+)([0-9A-Za-z][\w.-]*)", a)
                seq.append(("skill", inp.get("skill") or inp.get("command") or "", m.group(1).lower().rstrip(".") if m else None,
                            turn, c.get("id") in errored, a))
            elif name == "Read":
                seq.append(("read", inp.get("file_path", "")))
            else:
                seq.append(("tool", name, inp))
        elif c.get("type") == "text" and c.get("text", "").strip():
            seq.append(("text", c["text"]))

results = []  # (id, ok, detail)


def crit(cid, ok, detail):
    results.append((cid, bool(ok), detail))


# V1: the build under test, and only it.
want = norm(PLUGIN)
bad_inits = []
for k, e in enumerate(inits):
    sf = [p for p in e.get("plugins", []) if p.get("name") == "shortform-superengine"]
    if len(sf) != 1 or norm(sf[0].get("path", "")) != want:
        bad_inits.append(f"init {k}: {[(p.get('path'), p.get('source')) for p in sf] or 'no shortform-superengine'}")
market = raw.count(".claude/plugins/marketplaces/") + raw.count(".claude\\\\plugins\\\\marketplaces\\\\")
if not inits:
    crit("V1 build under test", False, "no init event in the log")
else:
    crit("V1 build under test", not bad_inits and not market,
         f"{len(inits)} init events, all list shortform-superengine once from {PLUGIN}; marketplaces paths: {market}"
         if not bad_inits and not market else f"bad inits: {bad_inits or 'none'}; marketplaces paths: {market}")


# The final skeleton and script: files under the project's scripts/ that this transcript wrote.
def written(skeleton):
    names = set()
    for s in seq:
        if s[0] != "tool":
            continue
        name, inp = s[1], s[2]
        if name in ("Write", "Edit", "MultiEdit"):
            names.add(Path(norm(inp.get("file_path", ""))).name)
        elif name in ("Bash", "PowerShell"):
            cmd = inp.get("command", "")
            if re.search(r">|\btee\b|Set-Content|Out-File", cmd):
                names.update(Path(norm(t)).name for t in re.findall(r"[^\s'\"<>|;]+\.md", cmd))
    files = [p for p in (PROJ / "scripts").glob("*.md")
             if p.name.lower() in names and p.name.endswith(".skeleton.md") == skeleton
             and not p.name.endswith(".draft.md")]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


skel, script = written(True), written(False)
# A script the plugin's placeholder rule flags (the hooks' rule, structure_gate.placeholder_problems) is a draft.
held = gate.placeholder_problems(script.read_text("utf-8-sig")) if script else []
crit("R5 script written", script is not None and not held,
     f"no script file under {PROJ / 'scripts'} was written in this transcript" if script is None else
     f"{script} still holds placeholders, so it is a draft: {', '.join(held)}" if held else f"{script}")

kind, beats = None, None
if skel is None:
    kind_why = f"no skeleton under {PROJ / 'scripts'} was written in this transcript"
else:
    try:
        beats, _, kind = gate.parse(skel.read_text("utf-8-sig"))
        kind_why = None
    except gate.Malformed as e:
        kind_why = f"skeleton {skel.name} is malformed: {e}"
side_kind = kind in gate.SIDE_KINDS

# Required calls, placed by skill name + a step token parsed from the args (step: X, step=X or
# step X, any case; None = no token). Models paraphrase the template's step line, so this is tolerant.
calls = [(k, s[1][len(SF):], s[2]) for k, s in enumerate(seq) if s[0] == "skill" and s[1].startswith(SF) and not s[4]]
REQ = [("angles", "1"), ("rehooks", "2"), ("rehooks", "3-lines"), ("hook", "3-hook"), ("viral", "4a-viral")]
if side_kind:
    REQ.insert(2, ("polarize", "2"))


def of(name):
    return [(k, st) for k, n, st in calls if n == name]


def method_read(k, folder, fname):
    """(item of a Read of the method file after item k and before the next options text, or None; that text's item)."""
    # Pre-0.6.0 logs: the hook skill asked the Goldmine question first; that question is not the options.
    fl = lambda t: " ".join(t.replace("\u2019", "'").split())
    shown = next((j for j in range(k + 1, len(seq)) if seq[j][0] == "text" and len(seq[j][1]) >= OPTIONS_MIN
                  and fl(GOLDMINE_Q) not in fl(seq[j][1])), len(seq))
    # The method file may be read just before the call too: look back to the previous options text.
    prev = max((j for j in range(k) if seq[j][0] == "text" and len(seq[j][1]) >= OPTIONS_MIN), default=-1)
    read = next((j for j in list(range(k + 1, shown)) + list(range(prev + 1, k)) if seq[j][0] == "read"
                 and norm(seq[j][1]).endswith(f"/skills/{folder}/references/{fname}")), None)
    return read, shown


rh2 = [k for k, st in of("rehooks")[:1] if st in (None, "2", "slots")]
first_use = min((k for k, n, _ in calls if n in ("rehooks", "polarize", "hook", "viral")), default=len(seq))
PLACE = {
    ("angles", "1"): ([k for k, _ in of("angles") if k < first_use],
                      f"a call before the first rehooks, polarize, hook or viral call (item {first_use})"),
    ("polarize", "2"): ([k for k, _ in of("polarize")], "any call"),
    ("rehooks", "2"): (rh2, "the first rehooks call, step 2, slots or none"),
    ("hook", "3-hook"): ([k for k, st in of("hook") if st in (None, "3", "3-hook") and rh2 and k > rh2[0]],
                         "step 3, 3-hook or none, after the rehooks Step-2 call"),
    ("viral", "4a-viral"): ([k for k, st in of("viral") if st is None or st.startswith("4a")], "step 4a... or none"),
    ("rehooks", "3-lines"): ([k for k, _ in of("rehooks")[1:] if method_read(k, "rehooks", "step3-lines.md")[0] is not None],
                             f"a later rehooks call followed by a Read of step3-lines.md before the next {OPTIONS_MIN}+ char text"),
}
for name, step in REQ:
    hits, rule = PLACE[(name, step)]
    crit(f"C {name} step {step}", hits, f"at item {hits} ({rule})" if hits else
         f"no Skill call {SF}{name} that is {rule}; {name} calls (item, step): {of(name)}")
if kind_why:
    crit("C polarize step 2", False, f"cannot tell whether polarize is required: {kind_why}")


# ORDER: Skill call, then a Read of the skill's method file, before the options are shown.
def method(name, step):
    return ("rehooks", "step3-lines.md") if step == "3-lines" else (name, f"legit-{name}.md")


for name, step in REQ:
    folder, fname = method(name, step)
    hits = PLACE[(name, step)][0]
    if not hits:
        crit(f"O {name} step {step}", False, "no such Skill call to order")
        continue
    why = []
    for k in hits:
        read, shown = method_read(k, folder, fname)
        if read is not None:
            crit(f"O {name} step {step}", True, f"Skill at item {k}, Read {fname} at {read}, options after")
            break
        why.append(f"Skill at item {k}: no Read of {fname} before the next text of {OPTIONS_MIN}+ chars (item {shown})")
    else:
        crit(f"O {name} step {step}", False, "; ".join(why))

# A stamp counts only from its Skill call: no Read of a wrapper SKILL.md, no search for "from:" in
# one or in step3-lines.md (the method file itself must be Read, so a plain Read of it is fine).
WRAP = re.compile(r"skills/+(angles|polarize|hook|rehooks|viral)/+skill\.md")
LINES = re.compile(r"rehooks/+references/+step3-lines\.md")
copied = []
for k, s in enumerate(seq):
    if s[0] == "read" and WRAP.search(s[1].lower().replace("\\", "/")):
        copied.append(f"item {k} Read {s[1]}")
    elif s[0] == "tool" and s[1] in ("Bash", "PowerShell", "Grep"):
        inp = s[2]
        target = (inp.get("command") or f"{inp.get('path', '')}/{inp.get('glob', '')}").lower().replace("\\", "/")
        if (WRAP.search(target) or LINES.search(target)) and "from:" in (inp.get("command") or inp.get("pattern") or "").lower():
            copied.append(f"item {k} {s[1]} {json.dumps(inp)[:200]}")
crit("N no stamp copied from a file", not copied, "; ".join(copied) if copied else
     "no Read of a wrapper SKILL.md; no search for 'from:' in one or in step3-lines.md")

# K: checkpoints hold. Steps as hooks/stamp-on-skill.py maps them. A call above the highest step reached,
# in the same user turn as the last call at that step, crossed a checkpoint without the user.
# ponytail: "an earlier rehooks call" stands in for the hook's valid-rehooks-stamp test on a rehooks call
# with no step token; read provenance history if the two ever disagree.
STEPS = {"reel-scripter": 0, "angles": 1, "rehooks": 2, "polarize": 2, "hook": 3, "viral": 5}
top, at, rehooked, crossed = 0, None, False, []
for k, n, st in calls:
    st, s = st and st.rstrip("."), STEPS.get(n)
    if n == "rehooks":
        s = 4 if st in ("3", "3-lines") or (st is None and rehooked) else 5 if st and st.startswith("4") else 2
        rehooked = True
    if s is None:
        continue
    if s > top and at == seq[k][3]:
        crossed.append(f"item {k} {n} (step {s}) in turn {seq[k][3]} crosses Checkpoint {min(top, 3)}")
    if s <= 1 or s >= top:
        top, at = s, seq[k][3]
crit("K checkpoints hold", not crossed, "; ".join(crossed) if crossed else "no step rose inside one user turn")

# Gate, from the transcript alone: the last gate run on the final skeleton ends in a PASS line (shell
# lines after it, like `EXIT:0`, are not gate output), and nothing writes the skeleton after that run
# (Write, Edit or MultiEdit on it, or a shell command naming it that written() counts as a write).
# provenance.md is not read: it is per project, so a later reel's pass rewrites it, and a grade read
# from it would depend on when grading ran. Nothing is re-run: stamps are per project, so a copy
# cannot pass.
if skel is None:
    crit("G gate passes", False, kind_why)
else:
    outs = {}  # tool_use_id -> the text its tool_result returned
    for e in ev:
        content = e.get("message", {}).get("content") if e.get("type") == "user" else None
        for c in content if isinstance(content, list) else []:
            if c.get("type") == "tool_result":
                t = c.get("content")
                outs[c.get("tool_use_id")] = t if isinstance(t, str) else "\n".join(
                    x.get("text", "") for x in t or [] if isinstance(x, dict))
    sk, runs, last, after = skel.name.lower(), 0, None, []  # after: writes of the skeleton after the last run
    for e in ev:
        for c in e.get("message", {}).get("content", []) if e.get("type") == "assistant" else []:
            if c.get("type") != "tool_use":
                continue
            inp = c.get("input") or {}
            cmd = str(inp.get("command", ""))
            shell = c.get("name") in ("Bash", "PowerShell")
            if shell and "structure_gate" in cmd and sk in cmd.lower() and "--angles" not in cmd:
                v = [l.strip() for l in outs.get(c.get("id"), "").splitlines()
                     if l.strip().startswith(("PASS", "FAIL", "MALFORMED", "UNREADABLE", "UNWRITABLE"))]
                runs, last, after = runs + 1, v[-1] if v else "no result", []
            elif (c.get("name") in ("Write", "Edit", "MultiEdit") and c.get("id") not in errored
                  and Path(norm(inp.get("file_path", ""))).name == sk
                  or shell and sk in cmd.lower() and re.search(r">|\btee\b|Set-Content|Out-File", cmd)):
                after.append(f"{c.get('name')} {c.get('id')}")
    passed = last is not None and last.startswith("PASS") and not after
    why = (f"no gate run on {skel.name} in the transcript" if last is None else
           f"the last gate run on {skel.name} ended in {last!r}, not a PASS line" if not last.startswith("PASS") else
           f"the skeleton was written after its last gate run ({', '.join(after)})")
    crit("G gate passes", passed, f"{skel.name}: " + (f"the last of {runs} gate run(s) ended in PASS, and nothing "
         f"wrote the skeleton after it" if passed else why))

# Other side beat, for myth-bust/negation and contrarian/curiosity.
if kind_why:
    crit("S other side beat", False, kind_why)
elif side_kind:
    ok = any(gate.SIDE.match(b["label"]) for b in beats)
    crit("S other side beat", ok, f"angle_kind {kind}: " + ("Other side beat present" if ok else "no beat labelled Other side"))
else:
    crit("S other side beat", True, f"angle_kind {kind}: not required")


# Visual cues >= duration / 5, from the storyboard table in the final script.
def num(tok):
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", tok)
    return None if not m else float(m.group(2)) + 60 * float(m.group(1) or 0)


def seconds(cell):
    c = re.sub(r"(?i)\s*(sec(ond)?s?|s)\b", "", cell.replace("~", "").replace("\u2248", "")).strip()
    m = re.fullmatch(r"(\d[\d:.]*)\s*(?:-|\u2013|\u2014|to)\s*(\d[\d:.]*)", c)
    if m and num(m.group(1)) is not None and num(m.group(2)) is not None:
        return num(m.group(2)) - num(m.group(1))
    return num(c)


def cues(cell):
    c = cell.strip()
    if re.fullmatch(r"(?i)(none|n/a|-+|\u2014|)", c):
        return 0
    return len([p for p in re.split(r"(?i);|\s\+\s|<br\s*/?>|\s/\s|->|\u2192|\bthen\b", c) if p.strip(" ,.")])


def storyboard(text):
    rows = [[x.strip() for x in l.strip().strip("|").split("|")] for l in text.splitlines() if l.strip().startswith("|")]
    for k, head in enumerate(rows):
        sc = next((i for i, h in enumerate(head) if re.search(r"(?i)sec|time|dur", h)), None)
        cc = next((i for i, h in enumerate(head) if re.search(r"(?i)cue", h)), None)
        if cc is None:
            cc = next((i for i, h in enumerate(head) if re.search(r"(?i)visual", h)), None)
        if sc is None or cc is None:
            continue
        body = []
        for r in rows[k + 1:]:
            if len(r) != len(head):
                break
            if all(re.fullmatch(r":?-+:?", x) for x in r if x):
                continue
            body.append(r)
        return head, sc, cc, body
    return None


if script is None:
    crit("V visual cues >= duration/5", False, "no final script to read a storyboard from")
else:
    sb = storyboard(script.read_text("utf-8-sig"))
    if not sb or not sb[3]:
        crit("V visual cues >= duration/5", False, f"no storyboard table with a seconds and a cue column in {script.name}")
    else:
        head, sc, cc, body = sb
        secs = [seconds(r[sc]) for r in body]
        bad = [r[sc] for r, s in zip(body, secs) if s is None or s < 0]
        if bad:
            crit("V visual cues >= duration/5", False, f"duration cannot be parsed from seconds cells {bad}")
        else:
            dur, n = sum(secs), sum(cues(r[cc]) for r in body)
            crit("V visual cues >= duration/5", n >= dur / 5,
                 f"{n} cues over {dur:g} s in {len(body)} rows (need >= {dur / 5:g}); columns '{head[sc]}', '{head[cc]}'")

# No Read of a deleted method file.
dead = [s[1] for s in seq if s[0] == "read" and any(norm(s[1]).endswith("/" + d) for d in DELETED)]
crit("D no deleted-file Read", not dead, f"read: {dead}" if dead else "none read")

# Q, Goldmine data (0.6.0): used by default when goldmine-run.json shows reads.passed; the only off switch
# is the client saying to use their own hook / ignore the data; never offered as a question.
GM_ARG = re.compile(r"(?im)(?:^|\s)(?:proven_hooks|pattern_read)[ \t]*[:=][ \t]*([^\n]*)")
GM_NAME = re.compile(r"(?i)\b(?:Pattern Read|Proven Hooks|Goldmine Reads Packet) - ")
# ponytail: one sentence (no . ! ? or newline inside) naming the Goldmine or "check the hooks against", ending
# in "?". Tuned on 347 walk logs: no false fire. A pick question naming a Goldmine-backed option would fire.
GM_ASK = re.compile(r"(?i)[^.!?\n]*\b(?:goldmine|check (?:the|your|these) hooks? (?:options )?against)\b[^.!?\n]*\?")
OPENERS = ("Read", "Bash", "PowerShell", "Grep")


def gm_args(s):
    """A Skill call's non-empty proven_hooks / pattern_read values (none, n/a, and bracketed placeholders like (none) / [not passed] are empty)."""
    return [v.strip()[:80] for v in GM_ARG.findall(s[5]) if v.strip()
            and not re.match(r"(?i)[(\[]?\s*(none|n/?a|null|no\b|not\b|omit|empty|-)", v.strip())]


def gm_named(s, tools):
    """The tool call names a Pattern Read, Proven Hooks or reads packet file (tools=None: any tool)."""
    if s[0] == "read":
        return (tools is None or "Read" in tools) and GM_NAME.search(s[1])
    return s[0] == "tool" and (tools is None or s[1] in tools) and GM_NAME.search(json.dumps(s[2], ensure_ascii=False))


def strings(x):
    return [x] if isinstance(x, str) else [t for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else [])
                                           for t in strings(v)]


flat = lambda t: " ".join(t.replace("\u2019", "'").split())
said = [s[1] for s in seq if s[0] == "text"] + [t for s in seq if s[0] == "tool" and s[1] == "AskUserQuestion" for t in strings(s[2])]
exact = flat(GOLDMINE_Q) in " ".join(flat(t) for t in said)
offers = [m.group(0).strip()[-160:] for t in said for m in GM_ASK.finditer(t)]
crit("Q no Goldmine question", not exact and not offers,
     "the old question never appears and no text or AskUserQuestion offers the Goldmine as a question" if not exact and not offers
     else f"old question text {'appears' if exact else 'absent'}; {len(offers)} question(s) offering the Goldmine: {offers[:3]}")

gm_file = PROJ / "reel-build" / "goldmine-run.json"
has_data, gm_note = gate.goldmine_state(gm_file)
data_why = (f"{gm_file} is missing; copy the Goldmine data into the walk project after reset.sh (a walk with no data "
            f"copy proves nothing about use)" if not gm_file.exists() else gm_note or f"{gm_file} does not show reads.passed true")
sk = [(k, s) for k, s in enumerate(seq) if s[0] == "skill" and not s[4]]
if goldmine == "on":
    why, used = [], []
    hooks = [k for k, s in sk if s[1] == SF + "hook"]
    for k in hooks:
        shown = method_read(k, "hook", "legit-hook.md")[1]
        hit = gm_args(seq[k]) or [f"item {j} {seq[j][0] if seq[j][0] == 'read' else seq[j][1]}" for j in range(k + 1, shown)
                                  if gm_named(seq[j], OPENERS)]
        (used if hit else why).append(f"hook at item {k}: {hit[:2]}" if hit else
                                      f"hook at item {k}: no proven_hooks/pattern_read arg and no Read/Bash/PowerShell/Grep "
                                      f"naming a Goldmine file before its options (item {shown})")
    ok = has_data and hooks and not why
    crit("Q Goldmine data used (on)", ok, "; ".join(used) if ok else data_why if not has_data else
         "no unblocked hook call" if not hooks else "; ".join(why))
else:
    args_use = [f"item {k} {s[1][len(SF):]}: {gm_args(s)[:1]}" for k, s in sk if gm_args(s)]
    named = [f"item {k} {s[0] if s[0] == 'read' else s[1]}" for k, s in enumerate(seq) if gm_named(s, None)]
    none_used = not args_use and not named
    if goldmine == "override":
        ok, pre = has_data and none_used, None if has_data else data_why
    else:
        ok, pre = not has_data and none_used, f"{gm_file} shows reads.passed true: grade with --goldmine on or override" if has_data else None
    crit(f"Q Goldmine data not used ({goldmine})", ok, pre or (
         "no Skill args carry proven_hooks/pattern_read and no tool input names a Pattern Read, Proven Hooks or reads packet file"
         if none_used else f"Skill args: {args_use[:4]}; tool inputs: {named[:4]}"))

# No "follow for part 2" CTA in the final script.
if script is None:
    crit("P no part-2 CTA", False, "no final script to check")
else:
    hit = PART2.search(script.read_text("utf-8-sig"))
    crit("P no part-2 CTA", not hit, f"found: {hit.group(0)!r}" if hit else "none")

# Second reel: this run's own angles, rehooks and hook calls.
if run2:
    own = {n for _, n, _ in calls}
    miss = [n for n in ("angles", "rehooks", "hook") if n not in own]
    crit("R2 run 2 own calls", not miss, f"missing: {miss}" if miss else "angles, rehooks, hook all called in this run")

print("Skill calls (item in the call/Read/text sequence, skill, step):", [(k, n, st) for k, n, st in calls])
print("Other Skill calls:", [s[1] for s in seq if s[0] == "skill" and not s[1].startswith(SF)])
print("Blocked Skill calls (item, skill, turn):", [(k, s[1], s[3]) for k, s in enumerate(seq) if s[0] == "skill" and s[4]])
prov = PROJ / "reel-build" / "provenance.md"
print("provenance.md:", prov.read_text("utf-8-sig").splitlines() if prov.exists() else "missing")
print(f"result: subtype={res.get('subtype')} turns={res.get('num_turns')} cost=${res.get('total_cost_usd')} is_error={res.get('is_error')}")
print(f"fixture: {fixture} | goldmine: {goldmine} | project: {PROJ} | skeleton: {skel} | script: {script}\n")
for cid, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'} {cid}: {detail}")
failed = [cid for cid, ok, _ in results if not ok]
print(f"\nVERDICT: {'FAIL' if failed else 'PASS'}")
if failed:
    print("failed:", "; ".join(failed))
sys.exit(1 if failed else 0)
