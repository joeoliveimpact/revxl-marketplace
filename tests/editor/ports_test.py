#!/usr/bin/env python3
"""S4b.2 check for reel-first-cuts' Shorts Studio ports and the re-transcribed cut: fix_words.py (port 1),
repeat_check.py (port 2, deep mode on the editor's own transcriber, no npx), cut_qa.py (port 9) and
transcribe_words.py on a rendered cut writing work/edit_map.cut.json (H-S4b-5).

usage: python tests/editor/ports_test.py <scratch-dir> [--case NAME] [--take REEL_018 take1]
The real take (repeat-deep, retranscribe) comes from --take, else the env var EDITOR_SE_TEST_TAKE.
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case (each one runs in under 150 s);
without it every case runs. Cases: fix, repeat, repeat-deep, repeat-deep-fw, whisper-stub, no-npx, silence-only,
murmur, retranscribe.

H-S4b-8: repeat-deep checks the shallow finder on S3's real REEL_018 map (the retake at 26.58-34.58, 8 s apart, which
deep mode's 3 s windows can't hold), and deep mode on real speech: the first 1.5 s of the line said at 26.3 s,
spliced twice back to back (3.0 s, one window), must be flagged as a restart/repeat with ONE model load.
H-S4b-11: whisper-stub checks faster-whisper's deep path with a stub faster_whisper module (one load, word parsing);
repeat-deep-fw runs it for real once, on the faster-whisper install FW (its state.json must stay byte-identical).

H-LOCK-1: repeat-deep, no-npx and retranscribe run the transcriber, so this test wraps those runs in
heavy_lock.py --min-gb 3 itself (exit 75/76 = the case is unproven, the test exits with that code).
retranscribe's render is TINY (360x640, at most 10 s): render.py's own build_graph() and encode(), no lock, and
it refuses below 1 GB free RAM. The other cases use planted, synthetic inputs.

Tools come from the editor state folder (EDITOR_SE_HOME): its ffmpeg and its venv Python, which runs every script
as `python -X utf8 -I`. When that install's recorded engine pick says "no GPU", the transcriber runs get the
documented test mask EDITOR_SE_MASK=gpu, so S3's route() keeps the install's engine instead of re-picking it
(H-S4b-9: the mask lives in this test only, never in shipped code or config). The run ends by checking that the
install's state.json sha256 is unchanged.
"""
import argparse, hashlib, json, math, os, random, re, shutil, subprocess, sys, time, types, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402  (S4b.1's helpers: fixtures, synthetic media, the RAM check)

rt, SCRIPTS, PY = cs.rt, cs.SCRIPTS, cs.PY
HEAVY = r"C:/Workspaces/Content Studio/output/scripts/heavy_lock.py"
STATE = rt.load_state()
ENV = dict(cs.ENV)
if (STATE.get("pick_facts") or {}).get("gpu") is False and not ENV.get("EDITOR_SE_MASK"):
    ENV["EDITOR_SE_MASK"] = "gpu"
FW = Path(r"C:/Work/_scratch/editor-superengine-0.2.0/a2/doctor-test-r2/state-fw")   # faster-whisper 1.2.1 install
SR = cs.SR
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sh(cmd, cwd=None, env=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env or ENV, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=150)


def script(name, *args, py=None):
    return [py or PY, "-X", "utf8", "-I", SCRIPTS / name] + list(args)


def heavy(cmd, cwd=None, env=None):
    """A transcriber run under the shared lock. 75/76 = unproven (lock wait / RAM): say so and stop, never loop."""
    p = sh([PY, "-X", "utf8", "-I", HEAVY, "--wait", "60", "--min-gb", "3", "--"] + cmd, cwd=cwd, env=env)
    if p.returncode in (75, 76):
        print(p.stdout[-300:] + p.stderr[-300:])
        print("UNPROVEN (%s): heavy_lock exit %d" % ("RAM" if p.returncode == 76 else "lock wait", p.returncode))
        sys.exit(p.returncode)
    return p


def bem():
    return cs.module("build_edit_map.py")


def edit_map(words):
    """A valid S3-shape edit map from (text, start, end) triples."""
    m = {"version": 1, "duration": max(e for _, _, e in words) + 1.0, "audio_sha256": "0" * 64,
         "calibration": {"threshold_db": -48.0}, "word_list_hash": None, "events": [], "silences": [],
         "words": [{"id": "w_%04d" % k, "word": " " + t, "start": s, "end": e, "parakeet_start": s,
                    "status": "aligned", "score_min": -1.0} for k, (t, s, e) in enumerate(words)]}
    b = bem()
    m["word_list_hash"] = b.word_list_hash(b.board_sequence(m))
    return m


def timed(text, t0=0.5, step=0.35, dur=0.3, gaps=None):
    """Words 0.3 s long, 0.35 s apart; gaps = {index: extra seconds before that word}."""
    out, t = [], t0
    for k, w in enumerate(text.split()):
        t += (gaps or {}).get(k, 0.0)
        out.append((w, round(t, 3), round(t + dur, 3)))
        t += step
    return out


# ------------------------------------------------------------------------------------------- fix
def case_fix(S, a):
    d = cs.fresh(S, "fix")
    client = d / "client"
    (client / "editor").mkdir(parents=True)
    fx = client / "editor" / "word-fixes.json"
    fx.write_text(json.dumps({"fixes": {"AGENTA": "Agentic"}, "phrases": {"comment guy": "GUIDE"}, "cta": ["GUIDE"]}),
                  encoding="utf-8")
    em = d / "work" / "edit_map.cut.json"
    em.write_text(json.dumps(edit_map(timed("The guy said comment guy. Agenta, rocks")), indent=1), encoding="utf-8")
    orig = em.read_bytes()
    old_hash = cs.load(em)["word_list_hash"]
    prev = em.with_name(em.name + ".prev")

    p = sh(script("fix_words.py", em, "--cta-check"), cwd=client)
    ck("fix: --cta-check before the fix exits 1 and names GUIDE", p.returncode == 1 and "missing: GUIDE" in p.stdout,
       (p.returncode, p.stdout[-200:], p.stderr[-200:]))
    ck("fix: --cta-check changed nothing", em.read_bytes() == orig and not prev.exists())
    p = sh(script("fix_words.py", em), cwd=client)
    m = cs.load(em)
    ws = [w["word"].strip() for w in m.get("words", [])]
    ck("fix: the phrase fix (from <paths.editor>/word-fixes.json) turns 'guy.' after 'comment' into 'GUIDE.'",
       p.returncode == 0 and ws[4:5] == ["GUIDE."], (p.returncode, ws, p.stderr[-200:]))
    ck("fix: the 'guy' NOT after 'comment' is left alone", ws[1:2] == ["guy"], ws)
    ck("fix: a fixes entry matches case-insensitively and keeps the punctuation ('Agenta,' -> 'Agentic,')",
       ws[5:6] == ["Agentic,"], ws)
    errs = bem().validate(m) if m else ["no map"]
    ck("fix: validate() passes on the fixed map (word_list_hash recomputed: %s -> %s)"
       % (old_hash[:8], str(m.get("word_list_hash"))[:8]), not errs and m.get("word_list_hash") != old_hash, errs[:3])
    ck("fix: the previous file is kept as %s, byte for byte" % prev.name, prev.exists() and prev.read_bytes() == orig)
    p = sh(script("fix_words.py", em, "--cta-check"), cwd=client)
    ck("fix: --cta-check after the fix exits 0", p.returncode == 0 and "present: GUIDE" in p.stdout,
       (p.returncode, p.stdout[-200:]))
    before_at = em.read_bytes()
    p = sh(script("fix_words.py", em, "--map", fx, "--at", '{"6": "ROCKS", "2": "says"}'), cwd=d)
    m2 = cs.load(em)
    ws2 = [w["word"].strip() for w in m2.get("words", [])]
    ck("fix: --at replaces words by list index (6 -> ROCKS, 2 -> says), the rest unchanged",
       p.returncode == 0 and ws2 == ws[:2] + ["says"] + ws[3:6] + ["ROCKS"], (ws, ws2, p.stderr[-200:]))
    ck("fix: after --at, validate() passes and the one .prev is the file before it",
       not bem().validate(m2) and prev.read_bytes() == before_at
       and len(list(em.parent.glob("*.prev"))) == 1)
    tx = d / "work" / "tx-cut.json"
    tx.write_text(json.dumps({"words": [{"i": 0, "text": "Agenta.", "start": 0.1, "end": 0.4},
                                        {"i": 1, "text": "comment", "start": 0.5, "end": 0.8},
                                        {"i": 2, "text": "guy?", "start": 0.9, "end": 1.2}]}), encoding="utf-8")
    p = sh(script("fix_words.py", tx, "--map", fx), cwd=d)
    tws = [w["text"] for w in cs.load(tx).get("words", [])]
    ck("fix: a tx.json with the `text` key is fixed too (%s)" % tws,
       p.returncode == 0 and tws == ["Agentic.", "comment", "GUIDE?"], (tws, p.stderr[-200:]))


# ------------------------------------------------------------------------------------------- repeat
PLANT = "So this tool and fixes and fixes your audio. It cuts every silent pause fast. Then it saves. " \
        "It cuts every silent pause quickly. Done."
CLEAN = "So this tool fixes your audio. It cuts every silent pause fast. Then it saves. Done."


def case_repeat(S, a):
    d = cs.fresh(S, "repeat")
    words = timed(PLANT, gaps={9: 1.0, 15: 1.0, 18: 2.0})
    f = d / "work" / "edit_map.cut.json"
    f.write_text(json.dumps(edit_map(words)), encoding="utf-8")
    out = d / "work" / "repeats.json"
    p = sh(script("repeat_check.py", f, "--json", out), cwd=d)
    H = cs.load(out) if out.exists() else []
    st = {w: [s for t, s, _ in words if t == w] for w in ("and", "It")}
    rep = [h for h in H if h.get("kind") == "repeat"]
    ret = [h for h in H if h.get("kind") == "retake"]
    ck("repeat: 'and fixes and fixes' found; drop = the first copy %s" % (st["and"],),
       len(rep) == 1 and rep[0]["drop"] == st["and"] and rep[0]["n"] == 2, rep)
    ck("repeat: the 6-word retake found; drop = the first take %s" % (st["It"],),
       len(ret) == 1 and ret[0]["drop"] == st["It"] and ret[0]["n"] == 6, ret)
    ck("repeat: exit 1 on hits, exactly those 2 hits (--json written)", p.returncode == 1 and len(H) == 2,
       (p.returncode, p.stdout[-300:], p.stderr[-300:]))
    c = d / "work" / "tx-cut.json"
    c.write_text(json.dumps({"words": [{"i": k, "word": t, "start": s, "end": e}
                                       for k, (t, s, e) in enumerate(timed(CLEAN, gaps={6: 1.0}))]}),
                 encoding="utf-8")
    p = sh(script("repeat_check.py", c), cwd=d)
    ck("repeat: a clean tx-cut.json has no hits and exits 0", p.returncode == 0 and "no repeats found" in p.stdout,
       (p.returncode, p.stdout[-300:], p.stderr[-300:]))


# ------------------------------------------------------------------------------------------- deep
LINE = (26.3, 1.5)        # REEL_018 take1: the line said at 26.3 s; its first 1.5 s is "Claude just killed Instagram."
RETAKE = [26.58, 34.58]   # S3's map: the same line again at 34.58 s, 8 s later (a retake for the shallow finder)


def spliced(S, take):
    """H-S4b-8 (b'): real speech, the line's first 1.5 s twice back to back (3.0 s), so ONE 3 s window holds both."""
    out = S / "fixtures" / "reel018-take1-restart-x2.wav"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        one = out.with_name("reel018-take1-line-1.5s.wav")
        cs.ff("-ss", str(LINE[0]), "-t", str(LINE[1]), "-i", cs.real_take(take), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(SR),
              "-c:a", "pcm_s16le", one)
        with wave.open(str(one)) as w:
            params, pcm = w.getparams(), w.readframes(w.getnframes())
        with wave.open(str(out), "wb") as o:
            o.setparams(params)
            o.writeframes(pcm + pcm)
        one.unlink()
    return out


def deep_run(S, a, d, env=None, py=None):
    wav = spliced(S, a.take)
    none = d / "work" / "none.json"
    none.write_text(json.dumps({"words": []}), encoding="utf-8")
    out = d / "work" / "deep.json"
    t0 = time.time()
    p = heavy(script("repeat_check.py", none, "--audio", wav, "--json", out, py=py), cwd=d, env=env)
    return p, time.time() - t0, cs.load(out) if out.exists() else []


def deep_ran(p):
    return p.returncode in (0, 1) and "Traceback" not in p.stderr and re.search(r"^deep: engine ", p.stdout, re.M)


def deep_checks(label, p, secs, H, engine):
    """The deep run: our engine, ONE model load over 2+ windows, and the spliced restart flagged (first copy)."""
    print(p.stdout.rstrip())
    print(p.stderr.rstrip()[-1500:])
    m = re.search(r"^deep: engine (\S+) \| (\d+) windows .*model loaded (\S+) time", p.stdout, re.M)
    loads = len(re.findall(r"^\[(?:parakeet|faster-whisper)\] .*load", p.stderr, re.M))
    heard = [h for h in H if h.get("kind", "").endswith("(heard)")]
    ck("%s: the deep check ran (engine %s, %s windows, %.1f s wall)" % (label, m and m.group(1), m and m.group(2), secs),
       bool(deep_ran(p)) and m is not None, (p.returncode, p.stderr[-400:]))
    ck("%s: the engine is the one state.json names (%s)" % (label, engine), m is not None and m.group(1) == engine)
    ck("%s: the model loaded once for %s windows (engine lines: %d, repeat_check says %s)"
       % (label, m and m.group(2), loads, m and m.group(3)),
       loads == 1 and m is not None and m.group(3) == "1" and int(m.group(2)) >= 2)
    flag = [h for h in heard if h["kind"].split()[0] in ("restart", "repeat")
            and h["drop"][0] < LINE[1] and h["drop"][1] >= LINE[1] - 0.3]
    ck("%s: the spliced restart (real speech, 2 x %.1f s) is flagged, drop = the first copy (%s)"
       % (label, LINE[1], [(h["kind"], h["drop"], h["text"]) for h in heard]), p.returncode == 1 and bool(flag), H)


def case_repeat_deep(S, a):
    d = cs.fresh(S, "repeat-deep")
    real = Path(cs.S3_WORK) / "edit_map.json"
    out = d / "work" / "shallow.json"
    p = sh(script("repeat_check.py", real, "--json", out), cwd=d)
    H = cs.load(out) if out.exists() else []
    ret = [h for h in H if h.get("kind") == "retake" and h["drop"] == RETAKE]
    ck("repeat-deep (a): the shallow finder catches the retake %s-%s on S3's real map (%s)"
       % (RETAKE[0], RETAKE[1], ret and ret[0]["text"][:60]), p.returncode == 1 and len(ret) == 1,
       (p.returncode, H[:3], p.stderr[-300:]))
    p, secs, H = deep_run(S, a, d)
    deep_checks("repeat-deep (b')", p, secs, H, STATE.get("engine"))


def case_repeat_deep_fw(S, a):
    """H-S4b-11: ONE real faster-whisper deep run, on the install FW (no test mask: its pick says GPU)."""
    st, before = rt.load_state(FW), sha(FW / "state.json")
    d = cs.fresh(S, "repeat-deep-fw")
    env = rt.python_env(FW, {k: v for k, v in os.environ.items() if k != "EDITOR_SE_MASK"})
    env["EDITOR_SE_HOME"] = str(FW)
    ck("repeat-deep-fw: the install's engine is faster-whisper (%s)" % st.get("engine"),
       st.get("engine") == "faster-whisper")
    p, secs, H = deep_run(S, a, d, env, rt.tool("python", FW))
    deep_checks("repeat-deep-fw", p, secs, H, "faster-whisper")
    ck("repeat-deep-fw: FW's state.json sha256 is unchanged (%s)" % before[:12], sha(FW / "state.json") == before)


def case_whisper_stub(S, a):
    """H-S4b-11: whisper_batch() with a stub faster_whisper (sys.modules): the model loads once, words are parsed."""
    d = cs.fresh(S, "whisper-stub")
    made, calls = [], []
    word = lambda t, s, e: types.SimpleNamespace(word=t, start=s, end=e)

    class Model:
        def __init__(self, path, device, compute_type):
            made.append((path, device, compute_type))

        def transcribe(self, wav, **kw):
            calls.append((wav, kw))
            return iter([types.SimpleNamespace(words=[word(" Claude", 0.28149, 0.5), word(" just,", 0.52, 0.7004)]),
                         types.SimpleNamespace(words=None)]), None
    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = Model
    wavs = [str(d / ("s%d.wav" % k)) for k in range(3)]
    lst, out = d / "work" / "wavs.json", d / "work" / "heard.json"
    lst.write_text(json.dumps(wavs), encoding="utf-8")
    rc = cs.module("repeat_check.py")
    saved, sys.modules["faster_whisper"] = rc.rt.model_dir, fake
    rc.rt.model_dir = lambda model, state=None: "stub/" + model
    try:
        rc.whisper_batch(lst, out, "en")
    finally:
        rc.rt.model_dir = saved
        sys.modules.pop("faster_whisper", None)
    r = cs.load(out)
    ck("whisper-stub: the model is made ONCE for 3 windows (%s)" % made,
       len(made) == 1 and made[0][0] == "stub/faster-whisper" and r.get("loads") == 1)
    ck("whisper-stub: every window is transcribed in order with word timestamps + VAD, language en",
       [c[0] for c in calls] == wavs and all(c[1] == {"language": "en", "word_timestamps": True, "vad_filter": True}
                                            for c in calls), calls)
    want = [{"word": "Claude", "start": 0.281, "end": 0.5}, {"word": "just,", "start": 0.52, "end": 0.7}]
    ck("whisper-stub: words are stripped and rounded, a segment with no words is skipped (%s)"
       % (r.get("results") or [{}])[0].get("words"),
       [x["wav"] for x in r.get("results", [])] == wavs and all(x["words"] == want for x in r["results"]), r)


def case_no_npx(S, a):
    d = cs.fresh(S, "no-npx")
    fake, marker = d / "fakebin", d / "npx-called.txt"
    fake.mkdir()
    (fake / "npx").write_bytes(('#!/bin/sh\necho called > "%s"\n' % marker.as_posix()).encode())
    (fake / "npx.cmd").write_bytes(('@echo off\r\necho called> "%s"\r\n' % marker).encode())
    env = dict(ENV)
    env["PATH"] = str(fake) + os.pathsep + env["PATH"]
    which = shutil.which("npx.cmd", path=env["PATH"]) or shutil.which("npx", path=env["PATH"])
    if which:
        subprocess.run([which, "--yes", "x"], env=env, capture_output=True, timeout=30)
    ck("no-npx control: the fake npx on PATH (%s) writes the marker when called" % which,
       bool(which) and Path(which).parent == fake and marker.exists())
    marker.unlink(missing_ok=True)
    p, secs, _ = deep_run(S, a, d, env)
    ck("no-npx: repeat-deep's command ran to the end with the fake npx first on PATH (%.1f s)" % secs,
       bool(deep_ran(p)), (p.returncode, p.stdout[-300:], p.stderr[-400:]))
    ck("no-npx: the marker is absent (nothing called npx)", not marker.exists())


# ------------------------------------------------------------------------------------------- silence-only
SIL_TONES = [(0.50, 1.50), (2.50, 3.50), (3.80, 4.20), (4.50, 5.50)]   # (3.80, 4.20) sits between the EDL cuts
BURST = (1.98, 2.02)                                                    # 40 ms = 4 windows, inside gaps.py's deletion
SIL_EDL = [(0.3, 3.6), (4.4, 5.8)]
SIL_FPS = 24                                                            # not 30, so a hard-coded 30 shows


def synth_sil(d, burst):
    rnd, n, ramp = random.Random(4), int(6.0 * SR), int(0.005 * SR)
    x = [rnd.gauss(0.0, 0.0007) for _ in range(n)]
    for s, e in SIL_TONES:
        a, b = round(s * SR), round(e * SR)
        for j in range(a, b):
            g = max(0.0, min(1.0, (j - a) / ramp, (b - 1 - j) / ramp))
            x[j] += 0.3 * (0.5 - 0.5 * math.cos(math.pi * g)) * math.sin(2 * math.pi * 220 * (j - a) / SR)
    if burst:
        for j in range(round(BURST[0] * SR), round(BURST[1] * SR)):
            x[j] += 0.3 * math.sin(2 * math.pi * 220 * j / SR)
    cs.write_wav(d / "sil.wav", x)
    return cs.mux(d, d / "sil.wav", 6.0, "sil.mov")


def sil_words():
    return edit_map([("w%d" % k, s, e) for k, (s, e) in enumerate(SIL_TONES)])


def case_silence_only(S, a):
    for burst in (True, False):
        label = "burst" if burst else "clean"
        d = cs.fresh(S, "silence-only-" + label)
        w = d / "work"
        src = synth_sil(d, burst)
        p = sh(script("probe.py", src, "-o", w, "--out-rate", str(SIL_FPS)), cwd=d)
        edl = cs.edl_file(w, SIL_EDL)
        g = sh(script("gaps.py", w, "--edl", edl), cwd=d)
        cuts = cs.load(w / "cuts.json")
        if p.returncode or g.returncode or not cuts:
            ck("silence-only %s: probe and gaps.py run" % label, False, (p.stderr[-300:], g.stderr[-300:]))
            continue
        em = w / "edit_map.json"
        em.write_text(json.dumps(sil_words()), encoding="utf-8")
        q = sh(script("cut_qa.py", w, "--words", em, "--json", w / "cut-qa.json"), cwd=d)
        R = cs.load(w / "cut-qa.json").get("results", [])
        fps = cuts["fps"]
        segs = [(s["src_in_f"] / fps, s["src_out_f"] / fps, s["out_out_f"]) for s in cuts["segments"]]
        # the span gaps.py removed around the burst, measured from cuts.json: between two pieces of EDL cut 1
        gap = next(((x[1], y[0], x[2]) for x, y in zip(segs, segs[1:]) if x[1] <= BURST[0] and y[0] >= BURST[1]), None)
        ck("silence-only %s: cuts.json is at %s fps and gaps.py removed %s around the burst, inside EDL cut 1"
           % (label, fps, gap and "%.3f-%.3f s" % gap[:2]),
           fps == SIL_FPS and gap is not None and SIL_EDL[0][0] <= gap[0] and gap[1] <= SIL_EDL[0][1], segs)
        print(q.stdout.rstrip())
        hit = [r for r in R if r["check"] == "silence-only" and r["result"] == "fail"]
        if burst:
            ck("silence-only burst: exactly one FAIL, the span holding the burst, 4 windows of voice",
               q.returncode == 1 and len(hit) == 1 and gap is not None and abs(hit[0]["src"][0] - gap[0]) < 1e-3
               and hit[0]["voice_windows"] == 4, (q.returncode, hit))
            ck("silence-only burst: the FAIL line gives the source time and out frame %s"
               % (gap and gap[2]), gap is not None and re.search(r"^FAIL silence-only: %.3f-%.3f s removed at out "
                                                                 r"frame %d," % (gap[0], gap[1], gap[2]),
                                                                 q.stdout, re.M) is not None, q.stdout[-400:])
        else:
            ck("silence-only clean: the same with the burst removed passes (exit 0, no FAIL)",
               q.returncode == 0 and not hit, (q.returncode, q.stdout[-400:]))
        env = cs.load(w / "envelope.json")
        p90 = sorted(env["db"])[int(0.9 * (len(env["db"]) - 1))]
        skip = [r for r in R if r["result"] == "skip" and r["src"][0] <= 3.80 and r["src"][1] >= 4.20]
        loud = skip and sum(1 for v in env["db"][round(skip[0]["src"][0] / 0.01):round(skip[0]["src"][1] / 0.01)]
                            if v > p90 - 18)
        ck("silence-only %s: the span between the EDL cuts holds speech (%s windows over p90-18) and is skipped"
           % (label, loud), bool(skip) and loud >= 4 and re.search(r"^SKIP silence-only: ", q.stdout, re.M), R)


# ------------------------------------------------------------------------------------------- murmur
MUR_FPS, MUR_SPEED = 25, 1.15
# (start s, windows, dB, the word over it or None, flagged?) against p90 = -6 dB: the band is -30 .. -15 dB
RUNS = [(3.0, 40, -22.0, None, True),                 # the 0.4 s mid-level run with no word
        (3.7, 27, -22.0, None, False),                # 0.27 s: under 28 windows
        (4.4, 28, -22.0, None, True),                 # 0.28 s: exactly 28
        (5.1, 40, -30.5, None, False),                # just under p90-24
        (5.8, 40, -29.5, None, True),                 # just inside p90-24
        (6.5, 40, -14.5, None, False),                # just over p90-9
        (7.2, 40, -15.5, None, True),                 # just inside p90-9
        (7.9, 40, -22.0, (7.9, 8.3), False),          # covered by a normal 0.4 s word
        (8.6, 40, -22.0, (8.5, 9.4), True),           # covered by a 0.9 s word (over 0.8 s)
        (9.6, 40, -22.0, (9.6, 9.78), True),          # a word over 45% of it: not covering
        (10.3, 40, -22.0, (10.2, 10.95), False)]      # a 0.75 s word covering it: not too long
MUR_SEGS = [(0.0, 6.2), (6.4, 12.0)]


def murmur_inputs(w, extra_words=()):
    db = [-60.0] * 1200
    for k in range(300):
        db[k] = -6.0                                  # 25% speech, so p90 = -6
    words = [("s%d" % k, 0.1 + 0.5 * k, 0.5 + 0.5 * k) for k in range(5)]
    for s, n, lvl, wd, _ in RUNS:
        k0 = round(s * 100)
        db[k0:k0 + n] = [lvl] * n
        if wd:
            words.append(("w%.1f" % s, wd[0], wd[1]))
    words += list(extra_words)
    (w / "envelope.json").write_text(json.dumps({"win_s": 0.01, "db": db}), encoding="utf-8")
    segs, S = [], 0
    for a, b in MUR_SEGS:
        f0, f1 = round(a * MUR_FPS), round(b * MUR_FPS)
        segs.append({"src_in_f": f0, "src_out_f": f1, "out_in_f": round(S / MUR_SPEED),
                     "out_out_f": round((S + f1 - f0) / MUR_SPEED)})
        S += f1 - f0
    (w / "cuts.json").write_text(json.dumps({"fps": MUR_FPS, "speed": MUR_SPEED, "segments": segs}), encoding="utf-8")
    cs.edl_file(w, [(0.0, 12.0)])
    em = w / "edit_map.json"
    em.write_text(json.dumps(edit_map(sorted(words, key=lambda x: x[1]))), encoding="utf-8")
    return em, segs


def out_frame(segs, t):
    s = next(s for s in segs if s["src_in_f"] <= t * MUR_FPS < s["src_out_f"])
    return s["out_in_f"] + round((t * MUR_FPS - s["src_in_f"]) / MUR_SPEED)


def case_murmur(S, a):
    d = cs.fresh(S, "murmur")
    w = d / "work"
    em, segs = murmur_inputs(w)
    q = sh(script("cut_qa.py", w, "--words", em, "--json", w / "cut-qa.json"), cwd=d)
    print(q.stdout.rstrip())
    F = {round(r["src"][0], 2): r for r in cs.load(w / "cut-qa.json").get("results", []) if r["check"] == "murmur"}
    for s, n, lvl, wd, want in RUNS:
        got = F.get(round(s, 2))
        what = "%.2f s at %.1f dB%s" % (n / 100, lvl, " under a %.2f s word" % (wd[1] - wd[0]) if wd else ", no word")
        if want:
            ck("murmur: %s at %.1f s is flagged at out frame %d" % (what, s, out_frame(segs, s)),
               got is not None and got["out_frame"] == out_frame(segs, s)
               and abs(got["src"][1] - got["src"][0] - n / 100) < 1e-6, got)
        else:
            ck("murmur: %s at %.1f s is not flagged" % (what, s), got is None, got)
    ck("murmur: the flags are exactly the planted ones and cut_qa exits 1 (%d flagged)" % len(F),
       q.returncode == 1 and len(F) == sum(r[4] for r in RUNS), (q.returncode, sorted(F)))
    em2, _ = murmur_inputs(w, [("covered", 3.0, 3.4)])
    q = sh(script("cut_qa.py", w, "--words", em2, "--json", w / "cut-qa.json"), cwd=d)
    F2 = {round(r["src"][0], 2) for r in cs.load(w / "cut-qa.json").get("results", []) if r["check"] == "murmur"}
    ck("murmur: the same 0.4 s run at 3.0 s covered by a normal word is not flagged", 3.0 not in F2 and len(F2) == len(F) - 1,
       sorted(F2))


# ------------------------------------------------------------------------------------------- retranscribe
def case_retranscribe(S, a):
    d = cs.fresh(S, "retranscribe")
    w = d / "work"
    src = cs.excerpt(S, a.take, cs.TINY_SRC)
    p = sh(script("probe.py", src, "-o", w), cwd=d)
    g = sh(script("gaps.py", w, "--edl", cs.edl_file(w, cs.SOURCES["cfr"])), cwd=d)
    cuts, probe = cs.load(w / "cuts.json"), cs.load(w / "probe.json")
    ck("retranscribe: probe and gaps.py on the 10 s REEL_018 take1 excerpt", not p.returncode and not g.returncode
       and bool(cuts), (p.stderr[-300:], g.stderr[-300:]))
    if not cuts:
        return
    fps, frames = cuts["fps"], cuts["segments"][-1]["out_out_f"]
    cs.need_ram()
    render = cs.module("render.py")
    astream = int(probe.get("audio_stream", 0))
    graph = w / "_graph-tiny.txt"
    graph.write_text(render.build_graph(cuts, render.sample_rate(src, astream), cs.TINY_VF, astream), encoding="utf-8")
    master = w / "renders" / "master-tiny.mp4"
    master.parent.mkdir(exist_ok=True)
    t0 = time.time()
    render.encode(src, graph, master, fps, probe.get("fps_flag", "-fps_mode"), 14, "slow", int(round(fps)), "192k")
    got = render.count_frames(master)
    ck("retranscribe: tiny master (360x640, %.2f s, %.0f s to render) has exactly the last out_out_f frames "
       "(%d rendered, %d in cuts.json)" % (frames / fps, time.time() - t0, got, frames),
       got == frames and frames / fps <= 10.0)
    side = {n: w / n for n in ("aligned.json", "vocal_truth.json")}   # the source's (planted), must stay as they are
    for n, f in side.items():
        f.write_text(json.dumps({"planted": "the source's " + n}), encoding="utf-8")
    shas = {n: sha(f) for n, f in side.items()}
    t0 = time.time()
    p = heavy(script("transcribe_words.py", master, "-o", w / "cut" / "tx-cut.json", "--edit-map",
                     w / "edit_map.cut.json"), cwd=d)
    print(p.stdout.rstrip()[-1200:])
    print("work/: %s | work/cut/: %s" % (sorted(x.name for x in w.glob("*.json")),
                                         sorted(x.name for x in (w / "cut").glob("*"))))
    ck("retranscribe: the source's work/aligned.json and work/vocal_truth.json are byte-unchanged (sha256 before %s, "
       "after %s)" % ({n: v[:8] for n, v in shas.items()}, {n: sha(f)[:8] for n, f in side.items()}),
       all(sha(f) == shas[n] for n, f in side.items()))
    ck("retranscribe: the cut's own side files are next to the transcript (work/cut/aligned.json, work/cut/vocal_truth.json)",
       all((w / "cut" / n).is_file() for n in side), sorted(x.name for x in (w / "cut").glob("*")))
    ecm = w / "edit_map.cut.json"
    m = cs.load(ecm)
    ck("retranscribe: transcribe_words.py on the master writes work/edit_map.cut.json (%.0f s under heavy_lock)"
       % (time.time() - t0), p.returncode == 0 and ecm.exists(), (p.returncode, p.stderr[-600:]))
    if not m:
        return
    errs = bem().validate(m)
    ck("retranscribe: validate() is OK on edit_map.cut.json (%d words)" % len(m.get("words", [])), not errs, errs[:3])
    ids = [x["id"] for x in m["words"]]
    ck("retranscribe: the word list indexes from 0 (w_0000, w_0001, ...)",
       bool(ids) and ids == ["w_%04d" % k for k in range(len(ids))], ids[:5])
    dur = frames / fps
    last = max(x["end"] for x in m["words"])
    ck("retranscribe: cut-time seconds: the last word ends at %.3f s, before the cut's %.3f s (map duration %.3f)"
       % (last, dur, m["duration"]), last < dur and abs(m["duration"] - dur) < 0.1)
    tx = cs.load(w / "cut" / "tx-cut.json")
    ck("retranscribe: the engine is the one state.json names (%s)" % tx.get("engine"),
       tx.get("engine") == STATE.get("engine"))


CASES = {"fix": case_fix, "repeat": case_repeat, "repeat-deep": case_repeat_deep, "repeat-deep-fw": case_repeat_deep_fw,
         "whisper-stub": case_whisper_stub, "no-npx": case_no_npx, "silence-only": case_silence_only,
         "murmur": case_murmur, "retranscribe": case_retranscribe}


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    ap.add_argument("--take", default=cs.TAKE)
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    print("python %s\nffmpeg %s\nengine %s%s" % (PY, shutil.which("ffmpeg"), STATE.get("engine"),
                                               " (EDITOR_SE_MASK=gpu)" if ENV.get("EDITOR_SE_MASK") else ""))
    state_json = Path(rt.state_dir()) / "state.json"
    before = sha(state_json)
    for name in [a.case] if a.case else list(CASES):
        t0 = time.time()
        print("-- %s" % name)
        CASES[name](S, a)
        print("   (%s: %.0f s)" % (name, time.time() - t0))
    ck("state.json sha256 unchanged (%s, %s)" % (before[:12], state_json), sha(state_json) == before)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
