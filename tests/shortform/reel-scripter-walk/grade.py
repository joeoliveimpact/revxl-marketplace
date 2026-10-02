"""Grade one reel-scripter walk transcript against RUBRIC.md.
Usage: py -3.12 grade.py <log> [--fixture gut|contra] [--run2]

<log> is a name under <state>/logs (or a path). <state> is RS_WALK_STATE (default
<home>/rs-walk-state), the folder run-mt2.sh writes to. The project graded is <state>/proj
(gut, the default) or <state>/proj-contra (contra). The plugin under test, its gate and its
trigger hook are the ones in this repo, found from this file's own location. The gate is
not re-run (its stamps are per project, so a copy cannot pass); grading writes nothing.

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
log_name, fixture, run2 = args[0], "gut", False
rest = args[1:]
while rest:
    a = rest.pop(0)
    if a == "--fixture" and rest and rest[0] in ("gut", "contra"):
        fixture = rest.pop(0)
    elif a == "--run2":
        run2 = True
    else:
        usage()

D = Path(os.environ.get("RS_WALK_STATE") or Path.home() / "rs-walk-state")
PROJ = D / ("proj" if fixture == "gut" else "proj-contra")
spec = importlib.util.spec_from_file_location("structure_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

raw = (D / "logs" / log_name).read_text("utf-8", errors="replace")
ev = [json.loads(l) for l in raw.splitlines() if l.strip().startswith("{")]
inits = [e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"]
res = next((e for e in reversed(ev) if e.get("type") == "result"), {})

# One flat, ordered list of what happened: ("skill", name, step), ("read", path), ("text", text), ("tool", name, input).
seq = []
for e in ev:
    if e.get("type") != "assistant":
        continue
    for c in e.get("message", {}).get("content", []):
        if c.get("type") == "tool_use":
            name, inp = c.get("name"), c.get("input") or {}
            if name == "Skill":
                a = inp.get("args", "")
                a = a if isinstance(a, str) else json.dumps(a)
                m = re.search(r"(?i)\bstep(?:[ \t]*[:=][ \t]*|[ \t]+)([0-9A-Za-z][\w.-]*)", a)
                seq.append(("skill", inp.get("skill") or inp.get("command") or "", m.group(1).lower() if m else None))
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
crit("R5 script written", script is not None,
     f"{script}" if script else f"no script file under {PROJ / 'scripts'} was written in this transcript")

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
calls = [(k, s[1][len(SF):], s[2]) for k, s in enumerate(seq) if s[0] == "skill" and s[1].startswith(SF)]
REQ = [("angles", "1"), ("rehooks", "2"), ("rehooks", "3-lines"), ("hook", "3-hook"), ("viral", "4a-viral")]
if side_kind:
    REQ.insert(2, ("polarize", "2"))


def of(name):
    return [(k, st) for k, n, st in calls if n == name]


def method_read(k, folder, fname):
    """(item of a Read of the method file after item k and before the next options text, or None; that text's item)."""
    # The hook skill asks the Goldmine question first; that question is not the options.
    fl = lambda t: " ".join(t.replace("\u2019", "'").split())
    shown = next((j for j in range(k + 1, len(seq)) if seq[j][0] == "text" and len(seq[j][1]) >= OPTIONS_MIN
                  and fl(GOLDMINE_Q) not in fl(seq[j][1])), len(seq))
    # The method file may be read just before the call too: look back to the previous options text.
    prev = max((j for j in range(k) if seq[j][0] == "text" and len(seq[j][1]) >= OPTIONS_MIN), default=-1)
    read = next((j for j in list(range(k + 1, shown)) + list(range(prev + 1, k)) if seq[j][0] == "read"
                 and norm(seq[j][1]).endswith(f"/skills/{folder}/references/{fname}")), None)
    return read, shown


rh2 = [k for k, st in of("rehooks")[:1] if st in (None, "2", "slots")]
PLACE = {
    ("angles", "1"): ([k for k, _ in of("angles")], "any call"),
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

# Gate: (a) the transcript ran the gate on the final skeleton and its last verdict line is PASS
# (shell lines after it, like `EXIT:0`, are not gate output), and (b) the real project's
# provenance.md holds `passed:` with the gate's fingerprint of that skeleton's text. Nothing is
# re-run: stamps are per project, so a copy cannot pass.
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
    verdicts = []  # the last gate verdict line of each run on the final skeleton
    for e in ev:
        for c in e.get("message", {}).get("content", []) if e.get("type") == "assistant" else []:
            cmd = str((c.get("input") or {}).get("command", "")) if c.get("type") == "tool_use" else ""
            if ("structure_gate" in cmd and skel.name.lower() in cmd.lower() and "--angles" not in cmd
                    and c.get("name") in ("Bash", "PowerShell")):
                v = [l.strip() for l in outs.get(c.get("id"), "").splitlines()
                     if l.strip().startswith(("PASS", "FAIL", "MALFORMED", "UNREADABLE", "UNWRITABLE"))]
                verdicts.append(v[-1] if v else "no result")
    ran = any(v.startswith("PASS") for v in verdicts)
    prov_g = PROJ / "reel-build" / "provenance.md"
    plines = prov_g.read_text("utf-8-sig").splitlines() if prov_g.exists() else None
    fp = gate.fingerprint(skel.read_text("utf-8-sig"))
    stamped = plines is not None and any(m and m.group(1).lower() == fp for m in map(gate.PASSED.match, plines))
    why = []
    if not ran:
        why.append(f"no gate run on {skel.name} in the transcript ended in a PASS line (last verdict lines: {verdicts or 'no run'})")
    if not stamped:
        why.append(f"{prov_g} is missing" if plines is None else
                   f"{prov_g} holds no passed: line for this skeleton's text")
    crit("G gate passes", ran and stamped, f"{skel.name}: " + ("; ".join(why) if why else
         f"a gate run ended in PASS ({len(verdicts)} run(s)), and provenance.md holds its passed: line"))

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

# Goldmine question: asked on contra (Goldmine data exists), never on gut.
flat = lambda t: " ".join(t.replace("\u2019", "'").split())
asked = flat(GOLDMINE_Q) in " ".join(flat(s[1]) for s in seq if s[0] == "text")
if fixture == "contra":
    crit("Q goldmine question asked", asked, "asked in the exact words" if asked else "the exact question text never appears")
else:
    crit("Q goldmine question absent", not asked, "not asked" if not asked else "asked, but this fixture has no Goldmine data")

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
prov = PROJ / "reel-build" / "provenance.md"
print("provenance.md:", prov.read_text("utf-8-sig").splitlines() if prov.exists() else "missing")
print(f"result: subtype={res.get('subtype')} turns={res.get('num_turns')} cost=${res.get('total_cost_usd')} is_error={res.get('is_error')}")
print(f"fixture: {fixture} | project: {PROJ} | skeleton: {skel} | script: {script}\n")
for cid, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'} {cid}: {detail}")
failed = [cid for cid, ok, _ in results if not ok]
print(f"\nVERDICT: {'FAIL' if failed else 'PASS'}")
if failed:
    print("failed:", "; ".join(failed))
sys.exit(1 if failed else 0)
