#!/usr/bin/env python3
"""N4 regression proof. Each --case runs in a fresh scratch reel, under 150 seconds.

python tests/editor/n4_test.py SCRATCH --take RAW --edit-map EDIT_MAP [--case NAME]
Real inputs are read only; only the two scratch excerpts are fingerprinted.
"""
import argparse, copy, hashlib, importlib.util, json, math, os, re, shlex, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs

SCRIPTS, PY = cs.SCRIPTS, cs.PY
CHECK = SCRIPTS.parents[1] / "_shared/checks/footage_check.py"
FAILS = []
ENV = dict(cs.ENV)


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " " + str(detail)))
    if not ok:
        FAILS.append(name)


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def load_module(path, name=None):
    spec = importlib.util.spec_from_file_location(name or Path(path).stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sh(cmd, **kw):
    return subprocess.run(list(map(str, cmd)), env=ENV, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=140, **kw)


def script(name, *args):
    return sh([PY, "-X", "utf8", "-I", SCRIPTS / name, *args])


def ff(*args):
    p = sh([cs.rt.tool("ffmpeg"), "-y", "-v", "error", *args])
    if p.returncode:
        raise RuntimeError("fixture encode failed: " + p.stderr[-500:])


def synthetic(S):
    """No media needed: real gaps.py runs on a planted source envelope."""
    d = S / "reel"
    for n in (1, 2):
        w = d / "work" if n == 1 else d / "work/take2"
        w.mkdir(parents=True, exist_ok=True)
        raw = d / ("A.mp4" if n == 1 else "B.mp4")
        raw.write_bytes(("scratch recording " + str(n)).encode())
        write(w / "probe.json", dict(input=str(raw), fps=dict(measured_fps=30), out_rate=30,
              calibration=dict(speech_run_windows=3, speech_db=-40, gap_db=-50)))
        write(w / "envelope.json", dict(win_s=.01, db=[-20] * 2000))
        write(w / "edit_map.json", dict(events=[], silences=[], words=[dict(id="w_0000", word="One", start=1., end=1.4,
              parakeet_start=1.), dict(id="w_0001", word="Two", start=4., end=4.4, parakeet_start=4.)]))
    return d


def first_packet(path):
    p = sh([cs.rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-read_intervals", "%+#1",
            "-show_entries", "packet=pts_time", "-of", "json", path])
    return float(json.loads(p.stdout)["packets"][0]["pts_time"])


def fixture(S, a):
    """Two stream copies, never a hash or write on the original. Preserve the real keyframe offset."""
    if a.take is None or a.edit_map is None:
        raise ValueError("this case needs --take and --edit-map (read-only real fixtures)")
    d = S / "reel"; d.mkdir(parents=True, exist_ok=True)
    original = cs.load(a.edit_map)
    bem = cs.module("build_edit_map.py")
    offsets = {}
    for n, start, label in ((1, 0, "A"), (2, 25, "B")):
        raw, temp = d / (label + ".mp4"), d / (label + "-packets.mp4")
        ff("-ss", str(start), "-i", a.take, "-t", "30", "-map", "0:v:0", "-map", "0:a:0", "-c", "copy", temp)
        packet_start = start + first_packet(temp)
        if n == 1:
            temp.replace(raw)
            offsets[n] = 0.
        else:
            ff("-i", temp, "-c", "copy", "-avoid_negative_ts", "make_zero", raw)
            offsets[n] = packet_start - first_packet(raw)
        w = d / "work" if n == 1 else d / "work/take2"
        p = script("probe.py", raw, "-o", w)
        if p.returncode:
            raise ValueError("probe fixture failed: " + p.stderr[-300:])
        wav = w / "tx.16k.wav"
        ff("-i", raw, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav)
        duration = bem.wav_duration(str(wav))
        m = dict(version=1, duration=round(duration, 3), audio_sha256=bem.audio_sha256(str(wav)),
                 calibration=original["calibration"], events=[], silences=[], words=[])
        for kind in ("words", "events", "silences"):
            for item in original.get(kind, []):
                q = copy.deepcopy(item)
                offset = offsets[n]
                if not (offset <= q["start"] < q["end"] <= offset + duration):
                    continue
                if kind == "words" and not offset <= q["parakeet_start"] < offset + duration:
                    continue
                for key in ("start", "end", "parakeet_start", "aligned_start", "aligned_end"):
                    if key in q:
                        q[key] = round(q[key] - offset, 6)
                m[kind].append(q)
        m["word_list_hash"] = bem.word_list_hash(bem.board_sequence(m))
        errs = bem.validate(m)
        if errs:
            raise ValueError("split edit map is invalid: " + errs[0])
        write(w / "edit_map.json", m)
    write(d / "offsets.json", offsets)
    return d


def ruling(d, mixed=True, take_numbers=(1, 2)):
    bem = cs.module("build_edit_map.py")
    cfg = dict(takes={}, lines=[], gap_default_ms=150)
    for n in take_numbers:
        folder = "work" if n == 1 else "work/take%d" % n
        words = bem.board_sequence(cs.load(d / folder / "edit_map.json"))
        cfg["takes"][str(n)] = dict(edit_map=folder + "/edit_map.json", wav=folder + "/tx.wav",
                                    words=words, word_list_hash="hash" + str(n))
    for k, n in enumerate((take_numbers[0], take_numbers[1] if mixed else take_numbers[0])):
        t = 1. if k == 0 else 4.
        cfg["lines"].append(dict(id="L" + str(k), attempts=[dict(take=n, src_in=t-.1, src_out=t+.6,
          word_from=k, word_to=k+1,
          words=[dict(i=k, w=("One" if k == 0 else "Two"), s=t, cin=t-.1)], silences=[])]))
    cfg["board_hash"] = bem.board_hash(cfg)
    sel = dict(lines=[dict(id=x["id"], pick=0) for x in cfg["lines"]], speed=1.15,
               word_list_hash={n: t["word_list_hash"] for n, t in cfg["takes"].items()},
               board_hash=cfg["board_hash"])
    write(d / "cut-board.config.json", cfg)
    write(d / "cut-selection.json", sel)
    p = script("selection_to_edl.py", d / "cut-selection.json", d / "cut-board.config.json")
    return p, cfg, sel


def printed(p):
    line = next(x for x in p.stdout.splitlines() if x.startswith("<editor python>"))
    return shlex.split(line.replace("<editor python>", '"' + Path(PY).as_posix() + '"')
                      .replace("${CLAUDE_PLUGIN_ROOT}", SCRIPTS.parents[2].as_posix()))


def case_ledger(S, a):
    d = fixture(S, a) if a.take and a.edit_map else synthetic(S)
    fc = load_module(CHECK)
    A, B = d / "A.mp4", d / "B.mp4"
    i = fc.add(d, A, "aroll", "own", "own")
    j = fc.add(d, B, "aroll", "own", "own")
    rows = cs.load(d / "footage/ledger.json")
    ck("ledger: IDs, hashes and duplicate add", i == "f01" and j == "f02" and len(rows) == 2
       and rows[0]["sha256"] == hashlib.sha256(A.read_bytes()).hexdigest()
       and rows[1]["sha256"] == hashlib.sha256(B.read_bytes()).hexdigest()
       and fc.add(d, A, "aroll", "own", "own") == i)
    for role, origin in (("xroll", "own"), ("aroll", "unknown")):
        p = sh([PY, "-X", "utf8", "-I", CHECK, "add", d, A, "--role", role, "--origin", origin, "--licence", "own"])
        ck("ledger: invalid %s/%s is one plain refusal" % (role, origin), p.returncode != 0
           and len((p.stdout+p.stderr).splitlines()) == 1)
    uses = [dict(path=str(A), src_in_f=0, src_out_f=30), dict(path=str(B), src_in_f=0, src_out_f=30)]
    ck("ledger: clean assets pass", fc.check(d, uses) == [])
    write(d / "footage/ledger.json", rows + [dict(rows[0], id="f03")])
    ck("ledger: two rows for one used path block", bool(fc.check(d, uses)))
    write(d / "footage/ledger.json", rows)
    if os.name == "nt":
        rows[0]["path"] = rows[0]["path"].swapcase()
        write(d / "footage/ledger.json", rows)
        ck("ledger: Windows case differences pass", fc.check(d, uses) == [])
    # This is the scratch excerpt; no bytes from the supplied real raw are written or hashed.
    with B.open("r+b") as f:
        byte = f.read(1); f.seek(0); f.write(bytes([byte[0] ^ 1]))
    ck("ledger: tampering blocks", any("this recording changed after it was logged: B.mp4" in x for x in fc.check(d, uses)))
    ck("ledger: one-frame overlap blocks", any("is used twice" in x for x in fc.check(d, [uses[0], dict(path=str(A), src_in_f=29, src_out_f=40)])))
    ck("ledger: touching intervals pass", fc.check(d, [uses[0], dict(path=str(A), src_in_f=30, src_out_f=40)]) == [])


def case_edl(S, a):
    d = synthetic(S)
    p, cfg, sel = ruling(d)
    ck("edl: mixed ruling accepted, old refusal absent", p.returncode == 0 and "REFUSED" not in p.stdout+p.stderr, p.stderr)
    ck("edl: take carried on each cut; takes command printed", [s["take"] for s in cs.load(d / "work/edl.json")] == [1, 2]
       and "takes.py" in p.stdout)
    # Each selected take gets both drift and word-list fingerprint guards.
    sel["word_list_hash"]["2"] = "stale"
    write(d / "cut-selection.json", sel)
    bad = script("selection_to_edl.py", d / "cut-selection.json", d / "cut-board.config.json")
    ck("edl: second take fingerprint checked", bad.returncode != 0 and "word list" in bad.stdout+bad.stderr)
    sel["word_list_hash"]["2"] = cfg["takes"]["2"]["word_list_hash"]
    write(d / "cut-selection.json", sel)
    cfg["takes"]["2"]["words"][0]["start"] += .1
    write(d / "cut-board.config.json", cfg)
    bad = script("selection_to_edl.py", d / "cut-selection.json", d / "cut-board.config.json")
    ck("edl: second take drift checked", bad.returncode == 3 and "rebuild the board" in bad.stdout+bad.stderr)
    p, _, _ = ruling(d, False)
    edl = cs.load(d / "work/edl.json")
    ck("edl: single ruling retains gaps command and old entries", p.returncode == 0 and "gaps.py" in p.stdout
       and [{k:v for k,v in s.items() if k != "take"} for s in edl] == [
           dict(src_in=.9, src_out=1.6, line="L0"), dict(src_in=3.9, src_out=4.6, line="L1")])
    third = d / "work/take3"
    third.mkdir()
    for name in ("probe.json", "envelope.json", "edit_map.json"):
        shutil.copyfile(d / "work" / name, third / name)
    p, _, _ = ruling(d, take_numbers=(2, 3))
    accepted = p.returncode == 0 and [s["take"] for s in cs.load(d / "work/edl.json")] == [2, 3]
    p = sh(printed(p))
    cuts = cs.load(d / "work/cuts.json")
    r = cs.module("render.py")
    graph = r.build_graph(cuts, 48000, {"2": "hflip", "3": "vflip"}, {"2": 0, "3": 1})
    ck("edl: takes 2 and 3 accepted; take 2 raw is the first render input", accepted and p.returncode == 0
       and set(cuts["takes"]) == {"2", "3"}
       and r.mixed_inputs(cuts, str(d / "B.mp4")) == [str(d / "B.mp4"), str(d / "A.mp4")]
       and "[0:v]hflip,split=1[sv0];" in graph and "[1:v]vflip,split=1[sv1];" in graph, p.stdout+p.stderr)


def mixed(S):
    d = synthetic(S)
    p, _, _ = ruling(d)
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    p = sh(printed(p))
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    return d, cs.load(d / "work/cuts.json")


def case_takes(S, a):
    d, cuts = mixed(S)
    edl = cs.load(d / "work/edl.json")
    write(d / "work/edl.json", edl + [dict(src_in=7., src_out=8., take=1)])
    # Re-run the printed command after adding a return to the first recording.
    write(d / "work/segments.json", [[0.0, 1.0]])   # a stale single-take cut left behind (M1)
    p = script("takes.py", d / "work", "--edl", d / "work/edl.json", "--speed", "1.15",
               "--take", "1:%s:%s" % (d / "work", d / "work/edit_map.json"),
               "--take", "2:%s:%s" % (d / "work/take2", d / "work/take2/edit_map.json"))
    ck("takes: returning to a recording produces a third run", p.returncode == 0, p.stderr)
    audits = [l for l in p.stdout.splitlines() if "boundary_audit.py" in l]
    ck("takes: stale work/segments.json removed; one boundary audit printed per run",
       not (d / "work/segments.json").exists() and len(audits) == 3, p.stdout)
    for line in audits:
        q = sh([PY, "-X", "utf8", "-I"] + shlex.split(line.split("-I", 1)[1]))
        ck("takes: printed boundary audit runs (%s)" % shlex.split(line)[-2].rsplit("/", 1)[-1], q.returncode in (0, 1)
           and "Traceback" not in q.stderr, (q.returncode, q.stdout[-300:], q.stderr[-300:]))
    cuts = cs.load(d / "work/cuts.json")
    segs = cuts["segments"]
    ck("takes: reel order and continuous output", [s["take"] for s in segs] == [1, 2, 1]
       and segs[0]["out_in_f"] == 0 and all(x["out_out_f"] == y["out_in_f"] for x,y in zip(segs, segs[1:])))
    src, expect = 0, []
    for n, run in enumerate(sorted((d / "work/runs").glob("r*")), 1):
        c = cs.load(run / "cuts.json")
        for s in c["segments"]:
            ln = s["src_out_f"] - s["src_in_f"]
            expect.append(dict(s, take=[1,2,1][n-1], out_in_f=round(src/1.15), out_out_f=round((src+ln)/1.15)))
            src += ln
    ck("takes: each run's real gaps pieces, out frames on cumulative source frames (gaps.py's rule)", segs == expect)
    pth = d / "work/take2/probe.json"
    probe = cs.load(pth); probe["fps"]["measured_fps"] *= 1.02; write(pth, probe)
    p, _, _ = ruling(d)
    p = sh(printed(p))
    ck("takes: measured fps mismatch refuses in one line", p.returncode == 2 and len((p.stdout+p.stderr).splitlines()) == 1
       and "frame rate" in p.stdout+p.stderr)
    if a.take and a.edit_map:
        real = fixture(S / "real", a)
        entries = []
        for n, minimum in ((1,1.), (2,1.), (1,10.)):
            w = real / "work" if n == 1 else real / "work/take2"
            start = next(x["start"] for x in cs.load(w / "edit_map.json")["words"] if x["start"] >= minimum)
            entries.append(dict(src_in=start-.2, src_out=start+2, take=n))
        write(real / "work/edl.json", entries)
        p = script("takes.py", real / "work", "--edl", real / "work/edl.json", "--speed", "1.15",
                   "--take", "1:%s:%s" % (real / "work", real / "work/edit_map.json"),
                   "--take", "2:%s:%s" % (real / "work/take2", real / "work/take2/edit_map.json"))
        cuts = cs.load(real / "work/cuts.json")
        sequence = [s["take"] for i,s in enumerate(cuts.get("segments", []))
                    if i == 0 or s["take"] != cuts["segments"][i-1]["take"]]
        ck("takes: real stream-copy clips traverse A, B, A through real gaps", p.returncode == 0
           and sequence == [1,2,1], p.stdout+p.stderr)


def case_timemap(S, a):
    d, cuts = mixed(S)
    tm = cs.load(d / "work/timemap.json")
    take = cs.module("takes.py")
    joined = [(s["file"], f) for s in tm["segments"] for f in range(s["src_in_f"], s["src_out_f"])]
    # Independently model fps: round each incoming timestamp, keep the last due frame.
    due = [math.floor(j / tm["speed"] + .5) for j in range(len(joined))]
    ck("timemap: every output frame follows joined fps rounding", all(
        take.lookup(tm, f) == joined[max(j for j, pts in enumerate(due) if pts <= f)]
        for f in range(cuts["segments"][-1]["out_out_f"])))
    p = script("word_map.py", d)
    m = cs.load(d / "work/word_map.json")
    ck("timemap: both takes' words round-trip within one frame", p.returncode == 0 and {w["take"] for w in m["words"]} == {1,2}
       and all(abs(take.lookup(tm, round(w["out_start"]*tm["fps"]))[1] - round(w["src_start"]*tm["fps"])) <= 1 for w in m["words"]), p.stderr)
    mc = load_module(CHECK.with_name("map_check.py"))
    ck("timemap: same word IDs in different takes do not collide", mc.run(dict(reel_dir=str(d))) == [])
    em = d / "work/take2/edit_map.json"; doc = cs.load(em); doc["words"][1]["end"] += .1; write(em, doc)
    ck("timemap: changing second edit map blocks as stale", any(h["check"] == "word-map-stale" for h in mc.run(dict(reel_dir=str(d)))))
    # Repeated local IDs identify different words in different files.
    wm = cs.module("word_map.py")
    shared = cs.load(d / "work/edit_map.json")
    c = dict(fps=30, speed=1., segments=[dict(src_in_f=27, src_out_f=48, out_in_f=0, out_out_f=21, take=1),
                                         dict(src_in_f=27, src_out_f=48, out_in_f=21, out_out_f=42, take=2)])
    words = wm.build(c, {"takes": {"1":shared, "2":shared}})["words"]
    ck("timemap: local word IDs are qualified by take", len(words) == 2 and words[0]["id"] != words[1]["id"]
       and words[0]["source_id"] == words[1]["source_id"])
    boundary = dict(fps=30, speed=1.15, segments=[
        dict(file="A", src_in_f=0, src_out_f=21, out_in_f=0, out_out_f=18),
        dict(file="B", src_in_f=100, src_out_f=121, out_in_f=18, out_out_f=36),
        dict(file="C", src_in_f=200, src_out_f=221, out_in_f=36, out_out_f=54)])
    ck("timemap: rounded boundary shows previous segment without extending it",
       take.lookup(boundary, 36) == ("B", 120) and take.lookup(boundary, 37) == ("C", 201)
       and take.lookup(boundary, 53) == ("C", 219))
    if a.take and a.edit_map:
        real = fixture(S / "real", a)
        rc = media_cuts(real)
        tm = cs.module("takes.py").write_timemap(real / "work", rc)
        maps = {n: cs.load(real / t["work"] / "edit_map.json") for n,t in rc["takes"].items()}
        words = wm.build(rc, {"takes": maps})["words"]
        offsets = cs.load(real / "offsets.json")
        original = {w["id"]:w for w in cs.load(a.edit_map)["words"]}
        ck("timemap: real words return to their clip and original recording within one frame", bool(words) and all(
            abs(take.lookup(tm, round(w["out_start"]*tm["fps"]))[1] - round(w["src_start"]*tm["fps"])) <= 1
            and abs(take.lookup(tm, round(w["out_start"]*tm["fps"]))[1]/tm["fps"]
                    + offsets[str(w["take"])] - original[w["source_id"]]["start"]) <= 1/tm["fps"] + 1e-6
            for w in words))


def case_best_take(S, a):
    d = fixture(S, a)
    em = cs.load(d / "work/edit_map.json")
    em2 = cs.load(d / "work/take2/edit_map.json")
    common = {w["id"] for w in em2["words"]}
    overlap = [w for w in em["words"] if 25.1 <= w["parakeet_start"] and w["end"] <= 29.5
               and w["id"] in common and w.get("status") != "unresolved"]
    if len(overlap) < 3:
        raise ValueError("the real fixture needs three spoken words in the 25–30 second overlap")
    (d / "script.md").write_bytes((" ".join(w["word"].strip() for w in overlap[:4]) + "\n").encode("utf-8"))
    write(d / "shots.json", dict(vocab=["talking head"], default="talking head"))
    p = script("make_board.py", "--script", d / "script.md", "--shots", d / "shots.json", "--reel", "n4",
               "--take", "1:%s:%s" % (d / "work/edit_map.json", d / "work/tx.16k.wav"),
               "--take", "2:%s:%s" % (d / "work/take2/edit_map.json", d / "work/take2/tx.16k.wav"), "-o", d)
    cfg = cs.load(d / "cut-board.config.json")
    line = (cfg.get("lines") or [{}])[0]
    ck("best-take: real overlap offered from both clips; last clip wins", p.returncode == 0
       and {x["take"] for x in line.get("attempts", [])} == {1,2}
       and line["attempts"][line["default"]]["take"] == 2, p.stdout+p.stderr)


def media_cuts(d):
    """About ten seconds, one five-second run from each actual clip."""
    g = cs.module("gaps.py")
    sources, segs, off = {}, [], 0
    for n in (1,2):
        work = "work" if n == 1 else "work/take2"
        probe = cs.load(d / work / "probe.json")
        words = cs.load(d / work / "edit_map.json")["words"]
        first = next(w["start"] for w in words if w["start"] >= .5)
        end = min(first + 4.75, probe["fps"]["span_s"] - .2)   # stay inside the clip (the fixture recording's speech starts ~26.6 s)
        c = g.snap_cuts([(max(0., min(first, end - 2.) - .25), end)], probe["out_rate"], 1.)
        for s in c["segments"]:
            segs.append(dict(s, take=n, out_in_f=s["out_in_f"]+off, out_out_f=s["out_out_f"]+off))
        off = segs[-1]["out_out_f"]
        sources[str(n)] = dict(raw=probe["input"], work=work)
    cuts = dict(fps=c["fps"], speed=1., segments=segs, takes=sources)
    write(d / "work/cuts.json", cuts)
    return cuts


def decoded(path, vf):
    p = subprocess.run([str(cs.rt.tool("ffmpeg")), "-v", "error", "-i", str(path), "-an", "-vf", vf,
                        "-pix_fmt", "rgb24", "-fps_mode", "passthrough", "-f", "rawvideo", "-"],
                       env=ENV, capture_output=True, timeout=140)
    if p.returncode:
        raise ValueError("frame decode failed: " + p.stderr.decode(errors="replace")[-300:])
    import numpy as np
    return np.frombuffer(p.stdout, dtype=np.uint8).reshape(-1, 640, 360, 3)


def psnr(x, y):
    import numpy as np
    mse = np.mean((x.astype(np.float32)-y.astype(np.float32))**2)
    return math.inf if mse == 0 else 10*math.log10(255**2/mse)


def case_render(S, a):
    if shutil.disk_usage(S).free < 10 * 2**30:
        print("REFUSED: less than 10 GB free disk; the render case is unproven")
        raise SystemExit(76)
    if not a.locked:
        import boards_test
        lock = Path(os.environ.get("EDITOR_SE_HEAVY_LOCK", boards_test.HEAVY))
        if not lock.is_file():
            print("REFUSED: heavy_lock.py is missing; the render case is unproven")
            raise SystemExit(75)
        cmd = [PY, "-X", "utf8", "-I", lock, "--wait", "5", "--min-gb", "3", "--", PY, "-X", "utf8", "-I",
               Path(__file__), S / "locked", "--case", "render", "--locked"]
        if a.take: cmd += ["--take", a.take]
        if a.edit_map: cmd += ["--edit-map", a.edit_map]
        p = sh(cmd)
        print(p.stdout.rstrip()); print(p.stderr.rstrip())
        if p.returncode in (75,76):
            raise SystemExit(p.returncode)
        ck("render: shared lock proof passed", p.returncode == 0, p.returncode)
        return
    d = fixture(S, a)
    cuts = media_cuts(d)
    fc, take, r = load_module(CHECK), cs.module("takes.py"), cs.module("render.py")
    for t in cuts["takes"].values():
        fc.add(d, t["raw"], "aroll", "own", "own")
    tm = take.write_timemap(d / "work", cuts)
    p = script("render.py", d / "work", d / "A.mp4", "--master", "--tag", "n4")
    master = d / "work/renders/master-n4.mp4"
    ck("render: real mixed master encoded", p.returncode == 0 and master.is_file(), p.stdout+p.stderr)
    if not master.is_file():
        return
    ck("render: frame count equals cut list", r.count_frames(master) == cuts["segments"][-1]["out_out_f"])
    out = decoded(master, "scale=360:640:flags=lanczos")
    for seg in cuts["segments"]:
        n = str(seg["take"])
        t = cuts["takes"][n]
        probe = cs.load(d / t["work"] / "probe.json")
        indices = [seg["out_in_f"] + round((seg["out_out_f"]-seg["out_in_f"]-1)*q) for q in (.2,.5,.8)]
        srcframes = [take.lookup(tm, f)[1] for f in indices]
        wanted = sorted(set(srcframes))
        vf = r.conform(probe["video"]) + ",fps=%r:start_time=0,select='%s',scale=360:640:flags=lanczos" % (
             cuts["fps"], "+".join("eq(n,%d)" % f for f in wanted))
        source = dict(zip(wanted, decoded(t["raw"], vf)))
        scores = [psnr(out[f], source[src_f]) for f, src_f in zip(indices, srcframes)]
        ck("render: three frames from take %s PSNR >= 35" % n, min(scores) >= 35, scores)
    sys.path.insert(0, str(SCRIPTS.parents[1] / "reel-sound-pass/scripts"))
    import _sync
    audio = _sync.load(master)
    for seg in cuts["segments"]:
        n = str(seg["take"]); t = cuts["takes"][n]
        src = _sync.load(t["raw"])
        words = [w for w in cs.load(d / t["work"] / "edit_map.json")["words"]
                 if seg["src_in_f"]/cuts["fps"]+.2 <= w["start"] < seg["src_out_f"]/cuts["fps"]-1][:2]
        lags = []
        for w in words:
            at = seg["out_in_f"]/cuts["fps"] + w["start"]-seg["src_in_f"]/cuts["fps"]
            x, y, span = round(w["start"]*_sync.SR), round(at*_sync.SR), round(.8*_sync.SR)
            lag, _ = _sync.lag_ms(_sync.env_db(src[x:x+span]), _sync.env_db(audio[y:y+span]), 100)
            lags.append(lag)
        ck("render: two words in take %s audio lag <= 33 ms" % n, len(lags) == 2 and max(map(abs,lags)) <= 33, lags)
    with (d / "B.mp4").open("r+b") as f:
        byte = f.read(1); f.seek(0); f.write(bytes([byte[0] ^ 1]))
    p = script("render.py", d / "work", d / "A.mp4", "--master", "--tag", "tampered")
    ck("render: tampering refused before any output encode", p.returncode != 0
       and "changed after it was logged" in p.stdout+p.stderr and not (d / "work/renders/master-tampered.mp4").exists())


def case_sync(S, a):
    d = fixture(S, a)
    camera = d / "camera.mp4"
    ff("-i", d / "A.mp4", "-t", "10", "-vf", "scale=640:640:force_original_aspect_ratio=decrease:force_divisible_by=2", "-c:v", "libx264", "-preset", "ultrafast",
       "-c:a", "aac", camera)
    delay = d / "delayed.mp4"
    ff("-i", camera, "-af", "adelay=1234:all=1", "-c:v", "copy", "-c:a", "aac", delay)
    p = script("sync.py", "--video", camera, "--audio", delay, "--out", d / "synced", "--max-offset", "3")
    report = cs.load(d / "synced/sync.json")
    ck("sync: planted 1.234-second delay found within 20 ms", p.returncode == 0
       and abs(report.get("offset_s",0)-1.234) <= .02 and report.get("score",0) >= .3
       and (d / "synced/synced.mp4").is_file(), (report,p.stdout,p.stderr))
    noise = d / "unrelated.mp4"
    ff("-i", camera, "-sseof", "-10", "-i", d / "B.mp4", "-f", "lavfi", "-i", "anoisesrc=d=10:a=0.2",
       "-filter_complex", "[1:a][2:a]amix=inputs=2[a]", "-map", "0:v", "-map", "[a]", "-t", "10",
       "-c:v", "copy", "-c:a", "aac", noise)
    sine = d / "sine.mp4"
    ff("-i", camera, "-f", "lavfi", "-i", "sine=frequency=440:duration=10", "-map", "0:v", "-map", "1:a",
       "-c:v", "copy", "-c:a", "aac", sine)
    for name, src in (("unrelated",noise), ("sine",sine)):
        out = d / ("bad-"+name)
        p = script("sync.py", "--video", camera, "--audio", src, "--out", out, "--max-offset", "3")
        ck("sync: %s voice stops without synced.mp4" % name, p.returncode != 0
           and "The voices do not match well" in p.stdout+p.stderr and not (out / "synced.mp4").exists(), p.stdout+p.stderr)


def case_follow(S, a):
    cs.need_ram()
    src = S / "screen.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=size=360x640:rate=30:duration=10", "-c:v", "libx264", "-crf", "10", src)
    source = decoded(src, "null")
    g, r, take = cs.module("gaps.py"), cs.module("render.py"), cs.module("takes.py")
    for speed in (1.,1.15):
        cuts = g.snap_cuts([(.5,2), (4,7)], 30, speed)
        cp, out = S / "cuts.json", S / ("follow-%s.mp4" % speed)
        write(cp, cuts)
        tm = take.write_timemap(S, cuts, raw=str(src))
        previous = sum(prev["src_in_f"] <= take.lookup(tm, s["out_in_f"])[1] < prev["src_out_f"]
                       for prev, s in zip(cuts["segments"], cuts["segments"][1:]))
        print("INFO follow: speed %s segment starts showing the previous segment: %d" % (speed, previous))
        p = script("follow_cut.py", src, "--cuts", cp, "--out", out)
        ck("follow: speed %s exact frame count" % speed, p.returncode == 0
           and r.count_frames(out) == cuts["segments"][-1]["out_out_f"], p.stdout+p.stderr)
        if not out.is_file():
            continue
        frames = decoded(out, "null")
        scores = [psnr(frames[f], source[take.lookup(tm, f)[1]]) for f in range(len(frames))]
        ck("follow: speed %s every frame PSNR >= 35" % speed, min(scores) >= 35, min(scores))
    cuts["takes"] = {"1":{}, "2":{}}
    write(cp, cuts)
    p = script("follow_cut.py", src, "--cuts", cp, "--out", S / "mixed.mp4")
    ck("follow: mixed reel plain refusal", p.returncode == 2 and (p.stdout+p.stderr).strip()
       == "a screen recording can follow one recording's cut; this reel mixes recordings")


def case_single(S, a):
    r = cs.module("render.py")
    base = sh(["git", "show", "3364bd2:" + (SCRIPTS / "render.py").relative_to(cs.REPO).as_posix()])
    if base.returncode:
        raise RuntimeError("base render is unavailable: " + base.stderr)
    old = type(sys)("base_render"); old.__file__ = str(SCRIPTS / "render.py"); exec(base.stdout, old.__dict__)
    for speed in (1., 1.15):
        cuts = cs.module("gaps.py").snap_cuts([(1,2), (4,6)], 30, speed)
        base_graph = old.build_graph(cuts, 48000, "scale=360:640", 0)
        for takes in ({}, {"1": {"raw": "A.mp4"}}):
            ck("single: speed %s build_graph byte-identical to base (%d takes)" % (speed, len(takes)),
               r.build_graph(dict(cuts, takes=takes), 48000, "scale=360:640", 0) == base_graph)
        mixed_cuts = dict(cuts, takes={"1": {}, "2": {}},
                          segments=[dict(s, take=n) for n, s in enumerate(cuts["segments"], 1)])
        mixed_graph = r.build_graph(mixed_cuts, 48000, {"1": "null", "2": "null"}, {"1": 0, "2": 1})
        ck("single: speed %s mixed cut shares source trims and joined speed tail" % speed,
           "[sv0]trim=start=1.0:end=2.0,setpts=PTS-STARTPTS,fps=30,trim=end_frame=30[v0];" in mixed_graph
           and "[1:a:1]aresample=48000" in mixed_graph
           and mixed_graph.splitlines()[-3:] == base_graph.replace("scale=360:640", "null").splitlines()[-3:]
           and mixed_graph.count("atempo=") == (1 if speed != 1. else 0))
    # A helper call below must not even import/check a ledger on the legacy path.
    d = synthetic(S)
    from unittest.mock import patch
    fc = load_module(CHECK)
    with patch.dict(sys.modules, {"footage_check": fc}), patch.object(fc, "check", side_effect=AssertionError("unexpected ledger check")) as check:
        r.footage_guard(d / "work", cuts, str(d / "A.mp4"))
        ck("single: footage check is never called without a ledger", check.call_count == 0
           and not (d / "footage/ledger.json").exists())


CASES = {"ledger": case_ledger, "edl": case_edl, "takes": case_takes,
         "timemap": case_timemap, "single": case_single, "best-take": case_best_take,
         "render": case_render, "sync": case_sync, "follow": case_follow}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--take", type=Path)
    ap.add_argument("--edit-map", type=Path)
    ap.add_argument("--case", choices=CASES)
    ap.add_argument("--locked", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    a.scratch = a.scratch.resolve()
    for path in (a.take, a.edit_map):
        if path and (path.resolve() == a.scratch or a.scratch in path.resolve().parents):
            raise SystemExit("REFUSED: scratch must not contain a supplied real fixture")
    a.scratch.mkdir(parents=True, exist_ok=True)
    home = a.scratch / "home"; home.mkdir(exist_ok=True)
    ENV.update(HOME=str(home), USERPROFILE=str(home))
    for name, fn in CASES.items():
        if a.case and a.case != name:
            continue
        S = a.scratch / name
        if S.exists():
            shutil.rmtree(S)
        S.mkdir()
        start = time.monotonic()
        try:
            fn(S, a)
        except Exception as e:
            ck(name + ": completed", False, str(e).splitlines()[0])
        ck(name + ": under 150 seconds", time.monotonic()-start < 150)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
