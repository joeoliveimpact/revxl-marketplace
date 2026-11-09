#!/usr/bin/env python3
"""S3 check for the reel-first-cuts transcription chain: transcribe_words.py and the vendored
parakeet_local / align_words / vocal_truth / build_edit_map.

usage: python tests/editor/transcribe_chain_test.py <scratch-dir> --parakeet-state <dir> --fw-state <dir>
           --clip <a short real speech clip> [--take <the 162.7 s take>]
           [--long-take <the 315.9 s take> --cpu-state <a parakeet-cpu state>] [--plugin <plugin root>]
The states are installed editor state folders (EDITOR_SE_HOME): Parakeet, the faster-whisper backup and,
for the speed row, Parakeet on the CPU. The clips are test inputs and never ship.
Prints PASS/FAIL per check, and INFO lines for speed and peak RAM (information only, H-M14).
Exit 0 = every check passed. --plugin runs the same checks against another tree (a planted break).
"""
import argparse, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)), flush=True)
    if not ok:
        fails.append(name)


def info(msg):
    print("INFO " + msg, flush=True)


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


class Chain:
    def __init__(self, plugin, rt):
        self.scripts = plugin / "skills" / "reel-first-cuts" / "scripts"
        self.rt = rt

    def env(self, state):
        """BL1.6: this install's own env, a copy of os.environ (never changed), EDITOR_SE_HOME = state. Any inherited
        EDITOR_SE_MASK is dropped; gpu is set only for an install set up with the GPU masked (its recorded pick says no
        GPU), else route() re-picks parakeet-gpu on a GPU PC and the doctor reinstalls its venv. Every other one runs
        unmasked, so its pick holds too (under one shared mask, state-fw re-picked parakeet-cpu)."""
        env = {k: v for k, v in os.environ.items() if k not in ("EDITOR_SE_TX_CHILD", "EDITOR_SE_MASK")}
        env["EDITOR_SE_HOME"] = str(state)
        if self.rt.pick_record(self.rt.load_state(state), None).get("pick_facts", {}).get("gpu") is False:
            env["EDITOR_SE_MASK"] = "gpu"
        return env

    def run(self, state, name, *args, cwd=None, measure=False, extra=None):
        """A plugin script as the client runs it (any Python), with this install's own env (EDITOR_SE_HOME = state)."""
        env = self.env(state)
        env.update(PYTHONUTF8="1", **(extra or {}))
        env["PATH"] = os.pathsep.join([str(Path(self.rt.tool("ffmpeg", state)).parent), env.get("PATH", "")])
        t0, peak = time.time(), [0]
        p = subprocess.Popen([sys.executable, str(self.scripts / name)] + [str(a) for a in args], cwd=cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                             errors="replace")
        if measure:
            threading.Thread(target=watch_ram, args=(p, peak), daemon=True).start()
        out, err = p.communicate(timeout=3600)
        p.secs, p.peak_gb, p.out, p.err = time.time() - t0, peak[0] / 2**30, out, err
        return p

    def venv(self, state, code):
        return subprocess.run([self.rt.tool("python", state), "-c", code], capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              env=self.rt.python_env(state, base=self.env(state)))


def watch_ram(p, peak):
    """Peak resident memory of the process tree, polled (needs psutil; else it reads 0)."""
    try:
        import psutil
        root = psutil.Process(p.pid)
    except Exception:
        return
    while p.poll() is None:
        try:
            procs = [root] + root.children(recursive=True)
            peak[0] = max(peak[0], sum(q.memory_info().rss for q in procs if q.is_running()))
        except Exception:
            pass
        time.sleep(0.25)


def link_copy(src, dst):
    """A copy of an installed state made of hard links (seconds, no disk), except the files a doctor run writes in
    place: state.json and pyvenv.cfg are real copies (pyvenv.cfg pointed at the copy's own Python) and logs/ too."""
    shutil.copytree(src, dst, copy_function=os.link, ignore=shutil.ignore_patterns("logs"))
    shutil.copytree(Path(src) / "logs", Path(dst) / "logs")
    for rel in ("state.json", "venv/pyvenv.cfg"):
        (Path(dst) / rel).unlink()
        shutil.copy2(Path(src) / rel, Path(dst) / rel)
    cfg = Path(dst) / "venv" / "pyvenv.cfg"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace(str(Path(src)), str(Path(dst))), encoding="utf-8")
    return Path(dst)


def ff(c, state, *args):
    p = subprocess.run([c.rt.tool("ffmpeg", state), "-y", "-v", "error"] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=c.env(state))
    if p.returncode:
        raise SystemExit("fixture ffmpeg failed: %s" % p.stderr[-600:])


def full_run(c, state, clip, d, edit_map=True, probe_args=(), extra=None):
    """probe -> transcribe (--probe, --edit-map) into d/work, the Stage 0-1 flow."""
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    c.run(state, "probe.py", clip, "-o", d / "work", *probe_args)
    args = [clip, "-o", d / "work" / "tx.json", "--probe", d / "work" / "probe.json"]
    if edit_map:
        args += ["--edit-map", d / "work" / "edit_map.json"]
    return c.run(state, "transcribe_words.py", *args, measure=True, extra=extra)


def first(words, n=6):
    return [w["word"].strip(".,!?").lower() for w in words[:n]]


def check_map(label, tx, em):
    tw, mw = tx.get("words", []), em.get("words", [])
    ck("%s: edit map has every transcript word (%d of %d) with its start as the cut anchor" % (label, len(mw), len(tw)),
       bool(tw) and len(mw) == len(tw) and all(abs(m["parakeet_start"] - w["start"]) < 1e-6 for m, w in zip(mw, tw)),
       "map %d, words %d" % (len(mw), len(tw)))
    ck("%s: edit map carries aligned words, events and silences" % label,
       sum(w["status"] == "aligned" for w in mw) >= len(mw) // 2 and isinstance(em.get("events"), list)
       and len(em.get("silences", [])) > 0, {k: len(em.get(k, [])) for k in ("words", "events", "silences")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--parakeet-state", required=True)
    ap.add_argument("--fw-state", required=True)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--take")
    ap.add_argument("--long-take")
    ap.add_argument("--cpu-state")
    ap.add_argument("--plugin", default=str(REPO / "plugins" / "editor-superengine"))
    a = ap.parse_args()
    plugin = Path(a.plugin).resolve()
    sys.path.insert(0, str(plugin / "skills" / "_shared"))
    import runtime as rt
    c = Chain(plugin, rt)
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    # PF-2 (hub 4, 11.04.26): a setup the doctor runs from here (the H-A2-1 switch) leaves home-pointer.txt in the default
    # state folder, so every child gets a scratch LOCALAPPDATA and HOME; a dev PC's real one must never point at scratch.
    real_ptr = rt.default_state_dir() / rt.HOME_POINTER
    real_before = real_ptr.read_bytes() if real_ptr.exists() else None
    for d in ("appdata", "home"):
        (S / d).mkdir(exist_ok=True)
    os.environ.update(LOCALAPPDATA=str(S / "appdata"), HOME=str(S / "home"))
    PK, FW, clip = Path(a.parakeet_state), Path(a.fw_state), Path(a.clip)

    # -- selftests (HF-5 (c) untimed words, the tail and stop helpers; the edit-map validator)
    p = c.run(PK, "transcribe_words.py", "--selftest")
    ck("transcribe_words --selftest (untimed words filled, tail trim, stop message)", p.returncode == 0,
       (p.out + p.err)[-400:])
    p = subprocess.run([rt.tool("python", PK), str(c.scripts / "build_edit_map.py"), "--selftest"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=rt.python_env(PK, base=c.env(PK)))
    ck("build_edit_map --selftest (15 broken maps caught)", p.returncode == 0 and "selftest ok" in p.stdout,
       (p.stdout + p.stderr)[-400:])

    # -- the primary engine on a real clip: words + edit map + the loudness reading
    d = S / "parakeet"
    p = full_run(c, PK, clip, d)
    tx, pr, em = load(d / "work" / "tx.json"), load(d / "work" / "probe.json"), load(d / "work" / "edit_map.json")
    info("Parakeet (%s) on %s: %.1f s, peak RAM %.2f GB" % (load(PK / "state.json").get("engine"), clip.name,
                                                            p.secs, p.peak_gb))
    ck("Parakeet runs on the real clip: exit 0, %d words, engine %s on %s" % (len(tx.get("words", [])), tx.get("engine"),
                                                                             tx.get("device")),
       p.returncode == 0 and str(tx.get("engine", "")).startswith("parakeet") and len(tx.get("words", [])) >= 10
       and "Parakeet" in p.out, (p.out + p.err)[-600:])
    ck("fix 8: probe.json stores mean_loudness_db (%s) and the transcript carries the same reading"
       % pr.get("mean_loudness_db"),
       isinstance(pr.get("mean_loudness_db"), (int, float)) and pr.get("mean_loudness_db") == tx.get("mean_loudness_db")
       and pr.get("mean_loudness_db") > -45, pr)
    check_map("Parakeet", tx, em)
    pk_words = tx.get("words", [])

    # -- the backup engine: a path-based transcribe() on the locked av, then the chain with the edit-map adapter
    v = c.venv(FW, "import av, faster_whisper; print(av.__version__, faster_whisper.__version__)")
    ck("backup venv runs the locked av 18.1.0 (got %s)" % v.stdout.strip(), v.stdout.split()[:1] == ["18.1.0"],
       v.stderr[-300:])
    code = ("import sys, json, types; sys.path.insert(0, %r); import transcribe_words as t; "
            "import runtime as rt; a = types.SimpleNamespace(model='large-v3-turbo', model_path=rt.model_dir('faster-whisper'), "
            "device='auto', compute_type=None, language='en', batched=0); d = t.transcribe(%r, a); "
            "print(json.dumps([len(d['words']), d['words'][0]['word'] if d['words'] else None]))"
            % (str(c.scripts), str(clip)))
    v = c.venv(FW, code)
    got = (v.stdout.strip().splitlines() or ["[0]"])[-1]
    ck("backup: transcribe() given the clip's file path returns words (%s)" % got,
       v.returncode == 0 and got.startswith("[") and json.loads(got)[0] >= 10, v.stderr[-600:])
    d = S / "backup"
    p = full_run(c, FW, clip, d)
    tx, em = load(d / "work" / "tx.json"), load(d / "work" / "edit_map.json")
    info("faster-whisper on %s: %.1f s, peak RAM %.2f GB" % (clip.name, p.secs, p.peak_gb))
    ck("backup chain: exit 0, %d words, engine %s" % (len(tx.get("words", [])), tx.get("engine")),
       p.returncode == 0 and tx.get("engine") == "faster-whisper" and len(tx.get("words", [])) >= 10,
       (p.out + p.err)[-600:])
    ck("backup: Parakeet's absence is reported, with the PB-11 warning",
       rt.BACKUP_WARNING in p.out and "Parakeet isn't set up" in p.out, p.out[-400:])
    check_map("backup (edit-map adapter)", tx, em)

    # -- H-M3: --report-md refuses an existing non-report file, and rewrites its own report
    w = d / "work"
    own = w / "notes.md"
    own.write_text("my own notes\n", encoding="utf-8")
    for name, args, out in (("build_edit_map.py", [w / "tx.16k.wav", w / "aligned.json", w / "vocal_truth.json"], w / "em2.json"),
                            ("vocal_truth.py", [w / "tx.16k.wav", w / "tx.json"], w / "vt2.json")):
        p = subprocess.run([rt.tool("python", FW), str(c.scripts / name)] + [str(x) for x in args + [out]]
                           + ["--report-md", str(own)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=rt.python_env(FW, base=c.env(FW)))
        ck("H-M3: %s --report-md refuses an existing non-report file, nothing written" % name,
           p.returncode != 0 and own.read_text(encoding="utf-8") == "my own notes\n" and not out.exists(),
           (p.returncode, p.stderr[-300:]))
        rep = w / (name + ".report.md")
        rs = [subprocess.run([rt.tool("python", FW), str(c.scripts / name)] + [str(x) for x in args + [out]]
                             + ["--report-md", str(rep)], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", env=rt.python_env(FW, base=c.env(FW))).returncode for _ in range(2)]
        ck("H-M3: %s --report-md writes, then rewrites, its own report" % name,
           rs == [0, 0] and rep.read_text(encoding="utf-8").startswith("# "), rs)

    # -- HF-5 (a): a planted silent tail with an invented word
    t = S / "tail"
    shutil.rmtree(t, ignore_errors=True)
    t.mkdir()
    ff(c, PK, "-i", clip, "-map", "0:a:0", "-af", "apad=pad_dur=3", "-ac", "1", "-ar", "16000", t / "tail.wav")
    sys.path.insert(0, str(c.scripts))
    import transcribe_words as tw
    import wave
    with wave.open(str(t / "tail.wav")) as wf:
        dur = wf.getnframes() / wf.getframerate()
    prev = os.environ.get("EDITOR_SE_HOME")
    os.environ["EDITOR_SE_HOME"] = str(PK)  # FT.1b: sound_end's ffmpeg is runtime.tool()'s, so PK's state
    end = tw.sound_end(t / "tail.wav", dur)
    os.environ.pop("EDITOR_SE_HOME") if prev is None else os.environ.update(EDITOR_SE_HOME=prev)
    planted = [dict(x) for x in pk_words] + [{"word": "subscribe", "start": round((end or dur) + 1.5, 3),
                                              "end": round((end or dur) + 1.9, 3)}]
    kept, dropped = tw.trim_tail(planted, end)
    ck("HF-5 (a): the 3 s silent tail is found (sound ends %.2f s of %.2f s)" % (end or -1, dur),
       end is not None and dur - end >= 2.9, end)
    ck("HF-5 (a): the invented tail word is dropped and every real word kept (%d kept, dropped %s)"
       % (len(kept), [x["word"] for x in dropped]),
       [x["word"] for x in dropped] == ["subscribe"] and len(kept) == len(pk_words), dropped)
    p = c.run(PK, "transcribe_words.py", t / "tail.wav", "-o", t / "tx.json")
    tt = load(t / "tx.json")
    ck("HF-5 (a): a real run on the padded clip keeps no word past the tail grace (%d words)" % len(tt.get("words", [])),
       p.returncode == 0 and "guards" in tt and tt["words"] and all(x["start"] <= end + 0.4 for x in tt["words"]),
       (p.out + p.err)[-400:])

    # -- HF-5 (b): a near-silent clip stops
    q = S / "quiet"
    shutil.rmtree(q, ignore_errors=True)
    q.mkdir()
    ff(c, PK, "-i", clip, "-map", "0:a:0", "-af", "volume=-40dB", "-ac", "1", "-ar", "48000", q / "quiet.wav")
    p = c.run(PK, "transcribe_words.py", q / "quiet.wav", "-o", q / "tx.json")
    ck("HF-5 (b): a near-silent clip stops (exit %d) with the plain message, nothing written" % p.returncode,
       p.returncode == 4 and "nearly silent" in p.err and not (q / "tx.json").exists(), (p.out + p.err)[-400:])

    # -- VU-2: a planted second audio track
    v2 = S / "two-track"
    shutil.rmtree(v2, ignore_errors=True)
    v2.mkdir()
    ff(c, PK, "-i", clip, "-f", "lavfi", "-i", "anoisesrc=a=0.0003:c=white:r=48000", "-map", "0:v:0", "-map", "1:a",
       "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", v2 / "two.mp4")
    two = v2 / "two.mp4"
    p = full_run(c, PK, two, v2 / "voice", edit_map=False, probe_args=("--audio-stream", "1"))
    tv = load(v2 / "voice" / "work" / "tx.json")
    ck("VU-2: with track 2 chosen, the chain transcribes it (audio_stream %s, %d words, same opening as the clip)"
       % (tv.get("audio_stream"), len(tv.get("words", []))),
       p.returncode == 0 and tv.get("audio_stream") == 1 and first(tv.get("words", [])) == first(pk_words),
       (first(tv.get("words", [])), first(pk_words), (p.out + p.err)[-300:]))
    wk = v2 / "voice" / "work"
    import importlib.util   # cuts.json (render.py's only input) through gaps.py's own frame snap
    spec = importlib.util.spec_from_file_location("gaps", c.scripts / "gaps.py")
    gaps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gaps)
    gaps.write_cuts(wk, gaps.snap_cuts([[0.0, 8.0]], load(wk / "probe.json")["out_rate"], 1.0))
    r = c.run(PK, "render.py", wk, two, "--master")
    master = wk / "renders" / "master-100x.mp4"
    p = c.run(PK, "transcribe_words.py", master, "-o", wk / "tx-cut.json")
    tc = load(wk / "tx-cut.json")
    ck("VU-2: the conformed cut carries the same chosen track (re-transcribed opening %s)" % first(tc.get("words", [])),
       r.returncode == 0 and p.returncode == 0 and first(tc.get("words", []), 4) == first(pk_words, 4),
       (r.err[-200:], (p.out + p.err)[-300:]))
    p = full_run(c, PK, two, v2 / "noise", edit_map=False, probe_args=("--audio-stream", "0"))
    ck("VU-2: with the near-silent track chosen, the stop names the other track (exit %d)" % p.returncode,
       p.returncode == 4 and "track 2" in p.err and "--audio-stream 1" in p.err, (p.out + p.err)[-400:])

    # -- H-S1a-4 + H-A2-1: an English workspace whose shared install holds the backup (left by a Spanish workspace)
    # calls the doctor's switch. Runs on a hard-link copy of the backup state; Parakeet is masked (test-only), so the
    # doctor's installer falls back to the backup instead of downloading 1-3 GB.
    sw = S / "switch"
    shutil.rmtree(sw, ignore_errors=True)
    st = link_copy(FW, sw / "state")
    before = (FW / "state.json").read_bytes()
    js = load(st / "state.json")
    es = dict(js["picks"]["en"], pick_facts=dict(js["picks"]["en"]["pick_facts"], language="es"),
              engine="faster-whisper", engine_reason="language es: Parakeet understands English only")
    js["picks"] = {"es": es, "en": {"engine": "parakeet-gpu", "engine_reason": "Windows with an NVIDIA GPU",
                                    "pick_facts": rt.pick_facts(None)[0]}}
    js.update(engine="faster-whisper", engine_reason=es["engine_reason"], pick_facts=es["pick_facts"])
    (st / "state.json").write_text(json.dumps(js, indent=1), encoding="utf-8")
    (sw / "ws").mkdir()
    p = c.run(st, "transcribe_words.py", clip, "-o", sw / "ws" / "tx.json", cwd=sw / "ws",
              extra={"EDITOR_SE_MASK": "parakeet"})
    tx = load(sw / "ws" / "tx.json")
    ck("H-A2-1: an English workspace on a backup-holding install calls the doctor, whose STATUS says it is switching",
       "editor doctor is switching" in p.out and "STATUS engine-switch warn This workspace uses English" in p.out
       and "(test mask: Parakeet is made uninstallable)" in p.out, p.out[-800:])
    ck("H-A2-1: after the doctor's (masked) switch the run goes on, on the backup it fell back to (%d words)"
       % len(tx.get("words", [])), p.returncode == 0 and tx.get("engine") == "faster-whisper"
       and len(tx.get("words", [])) >= 10, (p.out + p.err)[-400:])
    ck("H-A2-1: the source backup state is untouched", (FW / "state.json").read_bytes() == before)

    # -- the full 162.7 s take: words + edit map, no skip
    if a.take:
        d = S / "take"
        p = full_run(c, PK, Path(a.take), d)
        tx, em = load(d / "work" / "tx.json"), load(d / "work" / "edit_map.json")
        info("full take %s: %.1f s, peak RAM %.2f GB" % (Path(a.take).name, p.secs, p.peak_gb))
        ck("full take: exit 0, %d words over %.2f s" % (len(tx.get("words", [])), tx.get("duration", 0)),
           p.returncode == 0 and len(tx.get("words", [])) >= 200 and abs(tx.get("duration", 0) - 162.67) < 0.5,
           (p.out + p.err)[-600:])
        check_map("full take", tx, em)
    else:
        print("SKIP full take (no --take)")

    # -- speed and peak RAM on the 315.9 s take, GPU and CPU: information only (H-M14)
    if a.long_take:
        # the CPU state was installed with the GPU masked; the same mask keeps its pick (no switch to parakeet-gpu)
        for label, st, mask in (("GPU", PK, {}), ("CPU", Path(a.cpu_state) if a.cpu_state else None, {"EDITOR_SE_MASK": "gpu"})):
            if st is None:
                info("315.9 s take on the %s: not run (no --cpu-state)" % label)
                continue
            d = S / ("long-" + label.lower())
            p = full_run(c, st, Path(a.long_take), d, extra=mask)
            tx = load(d / "work" / "tx.json")
            info("315.9 s take, Parakeet on the %s (%s): exit %d, %d words, %.1f s wall (words + edit map), "
                 "peak RAM %.2f GB" % (label, tx.get("device"), p.returncode, len(tx.get("words", [])), p.secs,
                                       p.peak_gb))
            ck("315.9 s take on the %s: words + edit map, exit %d" % (label, p.returncode),
               p.returncode == 0 and (d / "work" / "edit_map.json").exists(), (p.out + p.err)[-600:])

    ck("PF-2: no home-pointer.txt landed in the real app-data", (real_ptr.read_bytes() if real_ptr.exists() else None)
       == real_before, real_ptr)
    print("\n%s: %d failed" % ("FAIL" if fails else "PASS", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
