#!/usr/bin/env python3
"""S5 check for reel-sound-pass (part A): the mix pipeline, the Auphonic cost ask, the sound library, room tone,
the quiet gate and the stem bake. Synthetic media only, made with ffmpeg here; no network (Auphonic is faked
in-process, the pack comes from a file:// URL).

usage: EDITOR_SE_HOME=<installed state> <state python> -X utf8 -I tests/editor/sound_pass_test.py
           [--case free_master|cost_ask|pack|ingest_trim|room_tone|quiet_gate|bake_exact|music_level|music_seam|
                   music_licence|music_absent|music_strongest] [--scratch <dir>]
           [--plugin <plugin root>]
Each case finishes in well under 150 s. Prints PASS/FAIL per check, then "N passed, M failed"; exit 1 on any fail.
"""
import argparse, hashlib, io, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugins" / "editor-superengine"
results = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)), flush=True)
    results.append(bool(ok))


# ------------------------------------------------------------------ synthetic media
def voice_like(seconds, seed=1, room_db=-60.0, level=0.12):
    """Noise bursts shaped like syllables, with pauses, over a steady room noise (never digital silence)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 10 ** (room_db / 20), n)
    on = (t % 1.05) < 0.7
    syll = np.sin(np.pi * 5 * t) ** 2
    x += on * syll * rng.normal(0, level, n)
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(n, 1 / SR) > 6000] = 0      # speech-like band: AAC would strip white noise's top octave
    x = np.fft.irfft(X, n)
    return np.stack([x, x], 1).astype(np.float32)


def make_picture(path, audio, video_s, scratch):
    wav = Path(scratch) / (Path(path).stem + "-src.wav")
    M.write_wav(wav, audio)
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x336699:s=180x320:r=30:d=%.3f" % video_s,
                    "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ac", "1", str(path)], check=True)


def tone(seconds, freq, level=0.5, decay=8.0):
    t = np.arange(int(seconds * SR)) / SR
    x = level * np.sin(2 * np.pi * freq * t) * np.exp(-decay * t)
    return np.stack([x, x], 1).astype(np.float32)


def workspace(scratch, name):
    ws = Path(scratch) / name
    if ws.exists():
        shutil.rmtree(ws)
    (ws / "editor").mkdir(parents=True)
    (ws / "editor" / "editor.config.json").write_bytes(b'{"paths": {"editor": "editor", "videos": "videos"}}\n')
    return ws


def script(ws, name, *args, env=None):
    p = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SCRIPTS / name)] + [str(a) for a in args], cwd=ws,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=140)
    p.all = p.stdout + p.stderr
    return p


def reel_with_picture(scratch, ws, reel, seconds=8.0, audio_s=None):
    r = ws / "videos" / reel
    (r / "work").mkdir(parents=True)
    make_picture(r / "locked.mp4", voice_like(audio_s or seconds), seconds, scratch)
    return r


def selection(r, cues, bed=None, extra=None):
    sel = {"project": "test", "picture": "locked.mp4", "fps": 30, "latency_ms": 0,
           "bed": bed or {"file": None, "gain_db": 0, "entry_s": 0, "exit_s": 0, "offset_s": 0, "fade_in_s": 0,
                          "fade_out_s": 0, "stops": []},
           "unassigned": [], "cues": cues, "rejected": [], "undecided": []}
    sel.update(extra or {})
    (r / "sound-selection.json").write_bytes(json.dumps(sel, indent=1).encode())


def cue(i, t, f, gain=-3.0, **kw):
    c = {"id": "c%d" % i, "beat": "beat %d" % i, "time": t, "file": f, "gain_db": gain, "length_s": None,
         "end_mode": "hard", "fade_out_s": None, "source_peak_dbfs": -6, "duration": 0.5}
    c.update(kw)
    return c


def sounds(r):
    (r / "sfx").mkdir(exist_ok=True)
    (r / "beds").mkdir(exist_ok=True)
    M.write_wav(r / "sfx" / "tick.wav", tone(0.4, 1800))
    M.write_wav(r / "sfx" / "thud.wav", tone(0.6, 90, 0.7, 5))
    M.write_wav(r / "sfx" / "chime.wav", tone(0.8, 1200, 0.4, 3))
    t = np.arange(int(12 * SR)) / SR
    bed = 0.2 * (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 330 * t + 1)) * (1 + 0.2 * np.sin(2 * np.pi * 0.5 * t))
    M.write_wav(r / "beds" / "bed.wav", np.stack([bed, bed * 0.9], 1))


def licensed(ws, *files):
    """Starter-pack catalogue rows for these bed files (a mix with music needs the bed's licence row)."""
    cat = ws / "editor" / "sound" / "beds" / "beds.json"
    rows = json.loads(cat.read_text(encoding="utf-8")) if cat.exists() else {}
    for f in files:
        rows[f] = {"title": Path(f).stem.title(), "mood": "calm", "origin": "pack", "author": "Test pack",
                   "licence": "Starter pack: cleared for use in your own videos", "licence_url": None}
    cat.parent.mkdir(parents=True, exist_ok=True)
    cat.write_bytes(json.dumps(rows, indent=1).encode())


def final_ok(prefix, final, picture):
    ok, nums, problems = MA.gate(final)
    ck(prefix + ": delivered file is stereo", nums["channels"] == 2, nums)
    ck(prefix + ": -14 LUFS within 0.5", abs(nums["integrated_lufs"] + 14) <= 0.5, nums)
    ck(prefix + ": true peak <= -1.0 dBTP", nums["true_peak_dbtp"] <= -1.0, nums)
    ck(prefix + ": video stream MD5 unchanged", M.video_md5(final) == M.video_md5(picture))


# ------------------------------------------------------------------ cases
def case_free_master(scratch):
    ws = workspace(scratch, "free_master")
    r = reel_with_picture(scratch, ws, "reel-a", 8.0)
    t0 = time.time()
    p = script(ws, "mix.py", "--reel", "reel-a", "--voice", "free", "--video", r / "locked.mp4")
    ck("free_master: voice-only mix exits 0", p.returncode == 0, p.all[-600:])
    final = r / "sound" / "final.mp4"
    if final.exists():
        final_ok("free_master", final, r / "locked.mp4")
        rep = json.loads((r / "sound" / "mix-report.json").read_text(encoding="utf-8"))
        ck("free_master: mix-report.json says pass", rep.get("pass") is True, rep)
    print("INFO voice-only mix %.1f s" % (time.time() - t0))

    mono = Path(scratch) / "mono-delivery.mp4"
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-i", str(final), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
                    "-c:a", "aac", "-ac", "1", str(mono)], check=True)
    g = script(ws, "master_audio.py", "--gate", mono)
    ck("free_master: a mono delivery is refused by the F-4 gate", g.returncode == 1 and "mono" in g.stdout, g.all[-400:])

    # the same pipeline with board cues and a music bed with a stop: mix_check runs on the delivered file
    r2 = reel_with_picture(scratch, ws, "reel-b", 8.0)
    sounds(r2)
    licensed(ws, "bed.wav")
    selection(r2, [cue(1, 1.5, "tick.wav", -6), cue(2, 4.2, "thud.wav", -8), cue(3, 6.0, "chime.wav", -10)],
              {"file": "bed.wav", "gain_db": -16, "entry_s": 0, "exit_s": 8, "offset_s": 1.0, "fade_in_s": 0.5,
               "fade_out_s": 0.8, "stops": [{"start_s": 3.0, "end_s": 3.8, "label": "drop", "fade_out_s": 0.3, "fade_in_s": 0.5}]})
    t0 = time.time()
    p = script(ws, "mix.py", "--reel", "reel-b", "--voice", "free", "--video", r2 / "locked.mp4")
    ck("free_master: mix with cues and music exits 0", p.returncode == 0, p.all[-800:])
    if (r2 / "sound" / "final.mp4").exists():
        final_ok("free_master (cues)", r2 / "sound" / "final.mp4", r2 / "locked.mp4")
        rep = json.loads((r2 / "sound" / "mix-report.json").read_text(encoding="utf-8"))
        mc = rep.get("mix_check", {})
        ck("free_master: every cue survived in the delivered file", len(mc.get("cues", [])) == 3 and not mc.get("weak_cues"), mc.get("cues"))
        ck("free_master: music ratio spread under 1 dB", mc.get("music_ratio_spread_db") is not None and mc["music_ratio_spread_db"] < 1.0,
           (mc.get("music_ratio_spread_db"), mc.get("music_windows")))
    print("INFO cue mix %.1f s" % (time.time() - t0))


class FakeAuphonic:
    """Answers one hop at a time like Auphonic (auphonic.send); counts every call. The download redirects (302) to a
    storage host that refuses any Authorization header, as the real one does. The 'cleaned' voice is the voice 25 ms
    late (an intro offset)."""
    STORE = "https://bucket.storage.example/presigned/voice.wav?sig=abc"

    def __init__(self, voice):
        x = M.decode(voice)
        pad = room_tone.fill(x, int(0.025 * SR))
        buf = Path(tempfile.mkdtemp()) / "clean.wav"
        M.write_wav(buf, np.vstack([pad, x]))
        self.clean = buf.read_bytes()
        self.calls, self.created, self.auth_ok, self.store_auth = [], 0, True, []

    def __call__(self, method, url, headers, body=None):
        self.calls.append((method, url))
        if url == self.STORE:
            self.store_auth.append(any(k.lower() == "authorization" for k in headers))
            if self.store_auth[-1]:
                raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)
            return 200, None, self.clean
        self.auth_ok &= headers.get("Authorization") == "bearer test-key-not-real"
        if url.endswith("/productions.json"):
            self.created += 1
            return 200, None, json.dumps({"data": {"uuid": "prod-%d" % self.created}}).encode()
        if url.endswith("/user.json"):
            return 200, None, json.dumps({"data": {"credits": 1.5}}).encode()
        if url.endswith("/upload.json") or url.endswith("/start.json"):
            return 200, None, b'{"data": {}}'
        if "/download/audio-result/" in url:
            return 302, self.STORE, b""
        if "/production/" in url and url.endswith(".json"):
            dl = "https://auphonic.com/api/download/audio-result/prod-1/voice.wav"
            return 200, None, json.dumps({"data": {"status": 3, "output_files": [{"download_url": dl}]}}).encode()
        raise AssertionError("unexpected call " + url)


def case_cost_ask(scratch):
    ws = workspace(scratch, "cost_ask")
    home = ws / "home"
    home.mkdir()
    os.environ.update(HOME=str(home), USERPROFILE=str(home))
    os.environ.pop("AUPHONIC_API_KEY", None)
    r = ws / "videos" / "reel-c"
    (r / "work").mkdir(parents=True)
    (r / "sound").mkdir()
    voice = r / "sound" / "voice.wav"
    M.write_wav(voice, voice_like(5.0, seed=3))
    import auphonic
    fake = FakeAuphonic(voice)
    auphonic.send, auphonic.POLL_S = fake, 0
    led = r / "work" / "paid-jobs.json"
    out = r / "sound" / "voice-cleaned.wav"
    run = ["run", str(voice), "--out", str(out), "--reel-dir", str(r)]

    rc = auphonic.main(run)
    ck("cost_ask: run without --yes exits 3", rc == 3, rc)
    ck("cost_ask: ... and makes zero network calls", not fake.calls, fake.calls)
    ck("cost_ask: ... and the ledger has no spend", not led.exists())

    rc = auphonic.main(run + ["--yes"])
    ck("cost_ask: no key and --yes exits 2 (free clean-up instead)", rc == 2 and not fake.calls, (rc, fake.calls))

    kf = home / ".config" / "auphonic" / "api_key"
    kf.parent.mkdir(parents=True)
    kf.write_bytes(b"test-key-not-real\n")
    rc = auphonic.main(["plan", str(voice), "--reel-dir", str(r)])
    ck("cost_ask: plan asks first and reads only the balance", rc == 0 and [c[1].rsplit("/", 1)[-1] for c in fake.calls] == ["user.json"],
       fake.calls)
    fake.calls.clear()

    rc = auphonic.main(run + ["--yes"])
    jobs = cost_ask.load(led)["jobs"]
    e = next(iter(jobs.values()), {})
    ck("cost_ask: with --yes it runs and stores the job id", rc == 0 and fake.created == 1 and e.get("job_id") == "prod-1"
       and e.get("result_sha256") and e.get("yes_at"), (rc, e))
    ck("cost_ask: the key goes only in the request header", fake.auth_ok and "test-key" not in led.read_text(encoding="utf-8"))
    ck("cost_ask: the download's redirect to the storage host carries no key", fake.store_auth == [False], fake.store_auth)
    ck("cost_ask: the cleaned voice is lined up and the picture's length",
       out.exists() and len(M.decode(out)) == len(M.decode(voice)) and not room_tone.silent_runs(M.decode(out)))

    fake.calls.clear()
    out.unlink()
    rc = auphonic.main(run + ["--yes"])
    ck("cost_ask: same input again reuses the result with zero calls", rc == 0 and not fake.calls and out.exists(), fake.calls)
    deep = r / "not-made-yet" / "deeper" / "voice-auphonic.wav"
    rc = auphonic.main(["run", str(voice), "--out", str(deep), "--reel-dir", str(r), "--yes"])
    ck("cost_ask: run with --out in a folder that doesn't exist yet works", rc == 0 and deep.is_file(), rc)

    res = Path(e["result"])
    b = bytearray(res.read_bytes())
    b[len(b) // 2] ^= 0xFF
    res.write_bytes(bytes(b))
    ck("cost_ask: a result whose bytes changed is not reusable", cost_ask.find_reusable(led, next(iter(jobs))) is None)
    fake.calls.clear()
    rc = auphonic.main(run + ["--yes"])
    ck("cost_ask: ... it is downloaded again, never paid again", rc == 0 and fake.created == 1 and fake.calls
       and not any(u.endswith("/productions.json") for _, u in fake.calls), fake.calls)

    fake.calls.clear()
    b[len(b) // 2 + 1] ^= 0xFF
    res.write_bytes(bytes(b))
    keep, auphonic.cross_host = auphonic.cross_host, lambda h: h        # planted break: the key follows the redirect
    buf = io.StringIO()
    old_out, sys.stdout = sys.stdout, buf
    try:
        rc = auphonic.main(run + ["--yes"])
    finally:
        sys.stdout, auphonic.cross_host = old_out, keep
    ck("cost_ask: reverse, a key forwarded to the storage host fails the download", rc == 1 and fake.store_auth[-1] is True, rc)
    ck("cost_ask: ... and says Auphonic refused it, not the internet", "refused" in buf.getvalue()
       and "internet" not in buf.getvalue(), buf.getvalue())

    p = script(ws, str(PLUGIN / "skills" / "_shared" / "cost_ask.py"), "--selftest")
    ck("cost_ask: cost_ask.py --selftest passes", p.returncode == 0 and "ok" in p.stdout, p.all[-300:])

    kf.unlink()
    r2 = reel_with_picture(scratch, ws, "reel-d", 6.0)
    env = {k: v for k, v in os.environ.items() if k != "AUPHONIC_API_KEY"}
    p = script(ws, "mix.py", "--reel", "reel-d", "--voice", "auphonic", "--yes", "--video", r2 / "locked.mp4", env=env)
    ck("cost_ask: no key falls back to the free clean-up with the plain line",
       p.returncode == 0 and auphonic.NO_KEY in p.stdout and (r2 / "sound" / "final.mp4").exists(), p.all[-500:])


def case_pack(scratch):
    lib_files = {"hit-a.wav": tone(0.3, 1000), "beds/bed-a.wav": tone(2.0, 220, 0.2, 0.1)}
    src = Path(scratch) / "pack-src"
    src.mkdir(parents=True, exist_ok=True)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        for rel, x in lib_files.items():
            f = src / rel.replace("/", "_")
            M.write_wav(f, x)
            z.write(f, rel)
    good = Path(scratch) / "pack.zip"
    good.write_bytes(zbuf.getvalue())
    data = good.read_bytes()
    man = {"url": good.as_uri(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    def fetch(name, manifest):
        ws = workspace(scratch, "pack-" + name)
        mf = ws / "manifest.json"
        mf.write_bytes(json.dumps(manifest).encode())
        return ws, script(ws, "sfx_ingest.py", "fetch", "--manifest", mf)

    ws, p = fetch("good", man)
    lib = ws / "editor" / "sound"
    ck("pack: a good pack is verified and unpacked", p.returncode == 0 and (lib / "hit-a.wav").is_file()
       and (lib / "beds" / "bed-a.wav").is_file(), p.all[-300:])
    v = script(ws, "sfx_ingest.py", "verify")
    ck("pack: verify passes on the unpacked library", v.returncode == 0, v.all[-300:])
    (lib / "hit-a.wav").write_bytes((lib / "hit-a.wav").read_bytes()[:-4] + b"\0\0\0\1")
    v = script(ws, "sfx_ingest.py", "verify")
    ck("pack: verify catches a changed library file", v.returncode == 1, v.all[-300:])

    flipped = Path(scratch) / "pack-flipped.zip"
    b = bytearray(data)
    b[len(b) // 2] ^= 0x01
    flipped.write_bytes(bytes(b))
    ws, p = fetch("flipped", dict(man, url=flipped.as_uri()))
    ck("pack: one flipped byte exits 1 and unpacks nothing", p.returncode == 1 and not (ws / "editor" / "sound").exists(), p.all[-300:])
    ws, p = fetch("bytes", dict(man, bytes=man["bytes"] + 1))
    ck("pack: wrong byte count exits 1 and unpacks nothing", p.returncode == 1 and not (ws / "editor" / "sound").exists(), p.all[-300:])
    ws, p = fetch("null", {"url": None, "sha256": None, "bytes": None})
    ck("pack: no pack yet says voice only and exits 0", p.returncode == 0 and "voice only" in p.stdout, p.all[-300:])
    page = Path(scratch) / "share-page.html"
    page.write_bytes(b"<!doctype html><html><body>Sign in to download</body></html>")
    ws, p = fetch("html", dict(man, url=page.as_uri()))
    ck("pack: a web page instead of the pack exits 1, says so, unpacks nothing", p.returncode == 1
       and "web page" in p.stdout and not (ws / "editor" / "sound").exists(), p.all[-300:])
    shipped = json.loads((SCRIPTS.parent / "pack.json").read_text(encoding="utf-8"))    # read only, no network
    ck("pack: the shipped pack.json has an https url, a 64-hex sha256 and an int byte count",
       str(shipped.get("url") or "").startswith("https://") and len(shipped.get("sha256") or "") == 64
       and all(ch in "0123456789abcdef" for ch in shipped["sha256"]) and type(shipped.get("bytes")) is int
       and shipped["bytes"] > 0, shipped)


def case_ingest_trim(scratch):
    ws = workspace(scratch, "ingest_trim")
    rng = np.random.default_rng(7)
    lead, body, tail = int(1.0 * SR), int(0.5 * SR), int(0.8 * SR)
    snd = rng.normal(0, 0.2, body) * np.hanning(body) ** 0.1
    x = np.concatenate([np.zeros(lead), snd, np.zeros(tail)])
    f = Path(scratch) / "whoosh-raw.wav"
    M.write_wav(f, np.stack([x, x], 1))
    p = script(ws, "sfx_ingest.py", "add", f)
    out = ws / "editor" / "sound" / "whoosh-raw.wav"
    ck("ingest_trim: add exits 0", p.returncode == 0 and out.is_file(), p.all[-300:])
    if out.is_file():
        y = M.decode(out)[:, 0]
        loud = np.flatnonzero(np.abs(y) > 1e-4)
        ck("ingest_trim: the trimmed file starts within 20 ms of the sound", loud[0] / SR <= 0.020, loud[0] / SR)
        ck("ingest_trim: ... and ends within 50 ms of it", (len(y) - 1 - loud[-1]) / SR <= 0.050, (len(y) - loud[-1]) / SR)
        idx = json.loads((ws / "editor" / "sound" / "library-index.json").read_text(encoding="utf-8"))
        ck("ingest_trim: the sound is measured and indexed", idx["files"].get("whoosh-raw.wav", {}).get("peak_dbfs") is not None, idx)


def case_room_tone(scratch):
    ws = workspace(scratch, "room_tone")
    r = reel_with_picture(scratch, ws, "reel-e", seconds=6.0, audio_s=4.5)
    p = script(ws, "bake.py", "--reel", "reel-e", "--video", r / "locked.mp4")
    ck("room_tone: bake exits 0 on a voice shorter than the picture", p.returncode == 0, p.all[-400:])
    v = M.decode(r / "sound" / "voice.wav")
    src = M.decode(r / "locked.mp4")
    s, e = room_tone.find(src)
    room = 20 * np.log10(np.sqrt(np.mean(src[s:e].astype(np.float64) ** 2)))
    gap = 20 * np.log10(np.sqrt(np.mean(v[len(src) + 100:].astype(np.float64) ** 2)))
    ck("room_tone: the voice track is the picture's length", len(v) == int(round(M.probe(r / "locked.mp4")["dur"] * SR)))
    ck("room_tone: the gap sits at the room-tone level (within 3 dB)", abs(gap - room) <= 3, (round(gap, 1), round(room, 1)))
    ck("room_tone: no digital-silence run of 50 ms or more", not room_tone.silent_runs(v), room_tone.silent_runs(v)[:3])
    c = script(ws, "room_tone.py", "check", r / "sound" / "voice.wav")
    ck("room_tone: the check passes the filled track", c.returncode == 0, c.all[-300:])
    zp = Path(scratch) / "zero-padded.wav"
    M.write_wav(zp, np.vstack([src, np.zeros((SR, 2), np.float32)]))
    c = script(ws, "room_tone.py", "check", zp)
    ck("room_tone: a zero-padded file is caught by the check", c.returncode == 1, c.all[-300:])
    c = script(ws, "mix_check.py", Path(scratch) / "no-such.mp4", "--voice", zp, "--sound", Path(scratch) / "no-such-sound")
    ck("room_tone: an unexpected failure is one plain line and exit 1, never a traceback",
       c.returncode == 1 and "Traceback" not in c.all and "stopped unexpectedly" in c.stdout, c.all[-300:])


def case_quiet_gate(scratch):
    ws = workspace(scratch, "quiet_gate")
    r = reel_with_picture(scratch, ws, "reel-f", 5.0)
    (r / "work" / "probe.json").write_bytes(b'{"mean_loudness_db": -50}\n')
    p = script(ws, "mix.py", "--reel", "reel-f", "--video", r / "locked.mp4")
    ck("quiet_gate: -50 dB stops with exit 1 and a plain line", p.returncode == 1 and "nearly silent" in p.stdout, p.all[-300:])
    ck("quiet_gate: ... and nothing is written in sound/", not (r / "sound").exists() or not any((r / "sound").iterdir()))
    (r / "work" / "probe.json").write_bytes(b'{"mean_loudness_db": -30}\n')
    p = script(ws, "mix.py", "--reel", "reel-f", "--video", r / "locked.mp4")
    ck("quiet_gate: -30 dB proceeds to a delivered file", p.returncode == 0 and (r / "sound" / "final.mp4").exists(), p.all[-400:])


def case_bake_exact(scratch):
    ws = workspace(scratch, "bake_exact")
    r = reel_with_picture(scratch, ws, "reel-g", 6.0)
    sounds(r)
    cues = [cue(1, 1.013, "tick.wav", -2), cue(2, 1.2, "thud.wav", -4),          # overlaps cue 1
            cue(3, 3.5, "chime.wav", -6, length_s=0.5, end_mode="fade", fade_out_s=0.2)]
    stop = {"start_s": 2.5, "end_s": 3.2, "label": "hit", "fade_out_s": 0.3, "fade_in_s": 0.4}
    selection(r, cues, {"file": "bed.wav", "gain_db": -12, "entry_s": 0.2, "exit_s": 5.8, "offset_s": 0.5,
                        "fade_in_s": 0.3, "fade_out_s": 0.5, "stops": [stop]},
              {"undecided": [cue(9, 2.0, "tick.wav")], "rejected": [{"beat": "x", "file": "thud.wav"}]})
    p = script(ws, "bake.py", "--reel", "reel-g", "--video", r / "locked.mp4")
    ck("bake_exact: bake exits 0", p.returncode == 0, p.all[-400:])
    snd = r / "sound"
    st = {k: M.decode(snd / (k + ".wav")) for k in ("voice", "sfx", "music", "sum")}
    ck("bake_exact: one length for every stem", len({len(v) for v in st.values()}) == 1)
    ck("bake_exact: sum == voice + sfx + music exactly", np.array_equal(st["sum"], st["voice"] + st["sfx"] + st["music"]))
    src = M.decode(r / "locked.mp4")
    ck("bake_exact: voice bit-exact to the picture's sound", np.array_equal(st["voice"][:len(src)], src[:len(st["voice"])]))
    P = json.loads((snd / "placement.json").read_text(encoding="utf-8"))
    ck("bake_exact: only the 3 decided cues are baked (undecided and rejected never mixed)", len(P["cues"]) == 3, P["cues"])
    ck("bake_exact: the overlapping cue went on its own lane", P["lanes"] == 2, P["lanes"])
    clips = [(c["start_sample"], M.decode(snd / c["file"])) for c in P["cues"]]
    rebuilt = np.zeros_like(st["sfx"])
    for s0, x in clips:
        rebuilt[s0:s0 + len(x)] += x[:len(rebuilt) - s0]
    ck("bake_exact: the sfx stem is exactly its cues", np.array_equal(rebuilt, st["sfx"]))
    for (s0, x), c in zip(clips, P["cues"]):
        others = rebuilt.copy()
        others[s0:s0 + len(x)] -= x
        alone = st["sfx"][s0:s0 + len(x)] - others[s0:s0 + len(x)]
        snd_start = int(round(c["time"] * SR))
        ck("bake_exact: cue %s has its isolated contribution at its time" % c["id"],
           np.abs(alone - x).max() < 1e-5 and np.abs(st["sfx"][snd_start:snd_start + 480]).max() > 1e-3
           and np.abs(x[:snd_start - s0]).max(initial=0) == 0)
    inside = st["music"][int(stop["start_s"] * SR) + 1:int(stop["end_s"] * SR)]
    ck("bake_exact: the music is silent inside the stop", np.abs(inside).max() == 0)
    ck("bake_exact: the music plays outside the stop",
       np.abs(st["music"][int(2.0 * SR):int(2.1 * SR)]).max() > 1e-3 and np.abs(st["music"][int(3.7 * SR):int(3.8 * SR)]).max() > 1e-3)


# ------------------------------------------------------------------ music (G4)
SPEECH = [(0.3, 2.3), (4.3, 6.3), (8.3, 10.3)]        # the voice speaks here; pauses of 2 s between


def voice_with_pauses(seconds, level=0.2, room_db=-60.0, seed=5):
    """Syllable-shaped speech-band noise inside SPEECH, steady room noise everywhere (never digital silence)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    on = np.zeros(n, bool)
    for a, z in SPEECH:
        on |= (t >= a) & (t < z)
    x = rng.normal(0, 10 ** (room_db / 20), n) + on * np.sin(np.pi * 4 * t) ** 2 * rng.normal(0, level, n)
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(n, 1 / SR) > 6000] = 0
    x = np.fft.irfft(X, n)
    return np.stack([x, x], 1).astype(np.float32)


def tx_cut(r):
    """work/cut/tx-cut.json (where S4b's re-transcribe writes): 0.5 s words with 0.1 s gaps, so each SPEECH span
    is one stretch of speech."""
    words = []
    for a, z in SPEECH:
        t = a
        while t < z - 1e-9:
            words.append({"word": "w", "start": round(t, 3), "end": round(min(t + 0.5, z), 3)})
            t += 0.6
    (r / "work" / "cut").mkdir(parents=True, exist_ok=True)
    (r / "work" / "cut" / "tx-cut.json").write_bytes(json.dumps({"words": words}).encode())


def steady_bed(seconds, amp=0.25):
    """Stereo bed, different notes left and right, integer-Hz sines: every whole-second window has the same RMS.
    About -12 LUFS at amp 0.25."""
    t = np.arange(int(seconds * SR)) / SR
    left = amp * (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 330 * t + 1))
    right = amp * (0.8 * np.sin(2 * np.pi * 277 * t + 0.5) + 0.5 * np.sin(2 * np.pi * 440 * t))
    return np.stack([left, right], 1).astype(np.float32)


def bed_sel(f, **kw):
    b = {"file": f, "gain_db": -18, "duck_db": 6, "rights_confirmed": False, "entry_s": 0, "exit_s": 12, "offset_s": 0,
         "fade_in_s": 0.5, "fade_out_s": 0.8, "stops": []}
    b.update(kw)
    return b


def win_rms(x, a, z):
    """RMS in dBFS over [a, z) s, both channels together."""
    w = x[int(round(a * SR)):int(round(z * SR))].astype(np.float64)
    return 20 * np.log10(np.sqrt(np.mean(w ** 2)) + 1e-20)


MIN_GAP_S = 1.0     # a pause shorter than this is not measured


def bed_windows(bed, dur):
    """(pause windows, under-speech windows) in s, from SPEECH. Pause: each gap between speech spans of at least
    MIN_GAP_S, minus the dip ramps at its edges (300 ms release after the span before, 80 ms attack before the span
    after). Under speech: each span (the dip is at full depth there). Both clipped to where the bed plays at full
    level (after its fade-in, before its fade-out)."""
    lo, hi = bed["entry_s"] + bed["fade_in_s"], min(bed["exit_s"], dur) - bed["fade_out_s"]
    pause = [(z + 0.3, a2 - 0.08) for (a, z), (a2, _) in zip(SPEECH, SPEECH[1:]) if a2 - z >= MIN_GAP_S]
    return ([(max(a, lo), min(z, hi)) for a, z in w if min(z, hi) - max(a, lo) >= 0.4] for w in (pause, SPEECH))


def window_levels(x, wins, tmp):
    """(integrated LUFS, RMS dBFS) of x's windows laid end to end. LUFS is ffmpeg ebur128: gated BS.1770
    (-70 LUFS absolute gate, -10 LU relative gate). RMS is ungated, both channels together."""
    cat = np.vstack([x[int(round(a * SR)):int(round(z * SR))] for a, z in wins])
    M.write_wav(tmp, cat)
    return M.loudness(tmp)[0], 20 * np.log10(np.sqrt(np.mean(cat.astype(np.float64) ** 2)) + 1e-20)


MEASURE = ("pause windows = gaps between speech spans of >= %.1f s minus the dip ramps (300 ms after, 80 ms before), "
           "inside the bed's full-level stretch; integrated LUFS over those windows laid end to end, ffmpeg ebur128 "
           "(gated BS.1770); under-speech windows = the speech spans, same method" % MIN_GAP_S)


def isolated_bed(r):
    """(the bed as it is in the delivered file, master static gain, mix report): music.wav x the master's gain."""
    rep = json.loads((r / "sound" / "mix-report.json").read_text(encoding="utf-8"))
    g = rep["passes"][-1]["master"]["gain_db"]
    return M.decode(r / "sound" / "music.wav") * np.float32(10 ** (g / 20)), g, rep


def case_music_level(scratch):
    """The bed sits level_db (-18) under the voice in the final, whatever the recording's loudness. Measured in
    WINDOWS (see MEASURE): pause loudness must be -32 +-1 LUFS (voice at -14 + level -18), under-speech windows at
    least 4 dB lower. A whole-reel figure would read lower than the pause level, because most of a reel is dipped
    speech; that is why this measures windows. The isolated bed is music.wav times the master's static gain,
    cross-checked against the gain least squares solves from the delivered file. Reverse: a voice about 5 dB quieter
    still puts the bed at -32 +-1 in the pauses."""
    import mix_check, music_fit
    ws = workspace(scratch, "music_level")
    pack = ws / "editor" / "sound" / "beds"
    M.write_wav(pack / "steady.wav", steady_bed(14.0))
    licensed(ws, "steady.wav")
    tmp = Path(scratch) / "music_level-window.wav"
    print("INFO bed source %.2f LUFS" % M.loudness(pack / "steady.wav")[0])
    print("INFO measurement: " + MEASURE)
    sel = bed_sel("steady.wav")
    pw, sw = bed_windows(sel, 12.0)
    print("INFO pause windows %s s, under-speech windows %s s" % ([(round(a, 2), round(z, 2)) for a, z in pw],
                                                                 [(round(a, 2), round(z, 2)) for a, z in sw]))

    for reel, level, tag in (("reel-m", 0.2, "voice"), ("reel-q", 0.115, "quiet voice")):
        r = ws / "videos" / reel
        (r / "work").mkdir(parents=True)
        make_picture(r / "locked.mp4", voice_with_pauses(12.0, level), 12.0, scratch)
        tx_cut(r)
        if reel != "reel-m":
            (r / "beds").mkdir()
            shutil.copy2(pack / "steady.wav", r / "beds" / "steady.wav")
        else:
            p = script(ws, "new_board.py", "--reel", reel, "--video", r / "locked.mp4")
            ck("music_level: new_board exits 0", p.returncode == 0, p.all[-500:])
            cfg = json.loads((r / "config.json").read_text(encoding="utf-8")) if (r / "config.json").exists() else {}
            row = next((b for b in cfg.get("beds", []) if b["file"] == "steady.wav"), {})
            ck("music_level: the board's bed row has the catalogue merge and suggest_entry_s",
               row.get("origin") == "pack" and row.get("licence_ok") is True and row.get("title") == "Steady"
               and isinstance(row.get("suggest_entry_s"), float) and row.get("lufs") is not None
               and isinstance(row.get("play_lufs"), float), row)
        selection(r, [], sel, {"music_request": None})
        p = script(ws, "mix.py", "--reel", reel, "--voice", "free", "--video", r / "locked.mp4")
        ck("music_level (%s): the mix with a licensed bed exits 0" % tag, p.returncode == 0, p.all[-800:])
        if not (r / "sound" / "final.mp4").exists():
            continue
        final_ok("music_level (%s)" % tag, r / "sound" / "final.mp4", r / "locked.mp4")
        bed, g, rep = isolated_bed(r)
        lv = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))["bed"]["level"]
        pl, pr = window_levels(bed, pw, tmp)
        sl, sr_ = window_levels(bed, sw, tmp)
        print("INFO %s: voice stem %.2f LUFS, premaster %.2f LUFS, master gain %+.2f dB, applied bed gain %+.2f dB; "
              "bed in the final: pause %.2f LUFS (%.2f dBFS RMS), under speech %.2f LUFS (%.2f dBFS RMS)"
              % (tag, lv["voice_lufs"], rep["passes"][-1]["master"]["input_lufs"], g, lv["gain_db_applied"],
                 pl, pr, sl, sr_))
        ck("music_level (%s): pause loudness -32 +-1 LUFS" % tag, abs(pl + 32) <= 1, round(pl, 2))
        ck("music_level (%s): under-speech windows at least 4 dB under the pause windows" % tag, sl <= pl - 4,
           (round(pl, 2), round(sl, 2)))
        if reel != "reel-m":
            continue
        chk = mix_check.check(r / "sound" / "final.mp4", r / "sound" / "voice-mixed.wav", r / "sound")
        print("INFO least-squares music gain %s dB" % chk["track_gain_db"]["music"])
        ck("music_level: the isolation (music stem x master gain) matches the delivered file within 0.5 dB",
           chk["track_gain_db"]["music"] is not None and abs(chk["track_gain_db"]["music"] - g) <= 0.5,
           (chk["track_gain_db"], g))
        ck("music_level: the board config's voice_lufs is the voice the bake set the level against (0.1 dB)",
           cfg.get("voice_lufs") is not None and abs(cfg["voice_lufs"] - lv["voice_lufs"]) <= 0.1,
           (cfg.get("voice_lufs"), lv["voice_lufs"]))
        pb = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))["bed"]
        ck("music_level: placement.json bed carries source, window, level and dip for a native rebuild",
           pb.get("source") == "beds/steady.wav" and pb["level"]["level_db"] == -18 and pb["duck"]["depth_db"] == 6
           and pb["level"]["bed_lufs_scope"] == "played"
           and abs(pb["level"]["gain_db_applied"] - (pb["level"]["voice_lufs"] - pb["level"]["bed_lufs"] - 18)) < 0.01
           and len(pb["duck"]["spans"]) == 3 and len(pb["duck"]["keyframes"]) == 12
           and all(k in pb for k in ("entry_s", "exit_s", "offset_s", "fade_in_s", "fade_out_s", "stops")), pb)
        src = M.decode(r / "beds" / "steady.wav").astype(np.float64)
        st = M.decode(r / "sound" / "music.wav").astype(np.float64)
        i0, i1 = int(0.6 * SR), int(11.0 * SR)                 # past the fade-in, before the fade-out
        a, b = st[i0:i1, 0], src[i0:i1, 0]
        m = np.abs(b) > 0.05
        got = 20 * np.log10(np.abs(a[m]) / np.abs(b[m])) - pb["level"]["gain_db_applied"]
        want = music_fit.envelope_db(pb["duck"]["keyframes"], (np.arange(i0, i1) / SR)[m])
        ck("music_level: the dip rebuilt from the keyframes matches the baked dip within 0.1 dB",
           np.abs(got - want).max() < 0.1, float(np.abs(got - want).max()))

    r = ws / "videos" / "reel-m"
    selection(r, [], bed_sel("steady.wav", duck_db=0))      # reverse: a dip of 0 is raised to 4
    p = script(ws, "bake.py", "--reel", "reel-m", "--video", r / "locked.mp4")
    st = M.decode(r / "sound" / "music.wav")
    pb = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))["bed"]
    pl, sl = window_levels(st, pw, tmp)[0], window_levels(st, sw, tmp)[0]
    print("INFO duck 0 -> stem pause %.2f LUFS, under speech %.2f LUFS" % (pl, sl))
    ck("music_level: reverse, a dip of 0 is raised to 4 dB with a plain note", p.returncode == 0 and "raised" in p.stdout
       and pb["duck"]["depth_db"] == 4, p.all[-300:])
    ck("music_level: ... and still dips at least 4 dB", sl <= pl - 4 + 0.01, (round(pl, 2), round(sl, 2)))


def norm_corr(a, b):
    return float(np.sum(a * b) / (np.sqrt(np.sum(a * a) * np.sum(b * b)) + 1e-20))


def case_music_seam(scratch):
    ws = workspace(scratch, "music_seam")
    r = reel_with_picture(scratch, ws, "reel-s", 8.0)
    (r / "beds").mkdir()
    short = steady_bed(3.0) * (1 + 0.3 * np.sin(2 * np.pi * 0.7 * np.arange(3 * SR) / SR))[:, None].astype(np.float32)
    M.write_wav(r / "beds" / "short.wav", short)
    selection(r, [], bed_sel("short.wav", entry_s=0.5, exit_s=8.0))
    p = script(ws, "bake.py", "--reel", "reel-s", "--video", r / "locked.mp4")
    ck("music_seam: bake exits 0 with a bed shorter than the cut", p.returncode == 0, p.all[-400:])
    ck("music_seam: no transcript means no dip, said plainly", "no transcript" in p.stdout, p.stdout[-300:])
    st = M.decode(r / "sound" / "music.wav").astype(np.float64).mean(1)
    L = len(M.decode(r / "beds" / "short.wav"))
    c = norm_corr(st[L:], st[:len(st) - L])
    looped = np.resize(st[int(0.5 * SR):int(0.5 * SR) + L], len(st))          # what a loop would have made
    cl = norm_corr(looped[L:], looped[:len(st) - L])
    print("INFO seam correlation at lag %d samples: %.3f (a looped bed reads %.3f)" % (L, c, cl))
    ck("music_seam: the bed against itself at lag = its length correlates < 0.9 (it ends, never repeats)", c < 0.9, c)
    ck("music_seam: ... and that measure does catch a loop (> 0.9)", cl > 0.9, cl)
    pb = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))["bed"]
    end = int(round((0.5 + L / SR) * SR))
    ck("music_seam: the bed ends where the track ends", abs(pb["exit_s"] - (0.5 + L / SR)) < 1e-3
       and np.abs(st[end + 1:]).max() == 0, pb["exit_s"])
    body, tail = win_rms(st, 1.5, 2.5), win_rms(st, end / SR - 0.02, end / SR)
    ck("music_seam: it has already faded out when the track runs out (last 20 ms >= 20 dB down)", tail <= body - 20,
       (round(body, 1), round(tail, 1)))
    hits = [f.relative_to(PLUGIN_ROOT).as_posix() for f in PLUGIN_ROOT.rglob("*")
            if f.is_file() and any(w in f.read_bytes() for w in (b"stream_loop", b"aloop"))]
    ck("music_seam: no stream_loop or aloop anywhere in the plugin", not hits, hits)


def case_music_licence(scratch):
    import licence_rows
    ws = workspace(scratch, "music_licence")
    r = reel_with_picture(scratch, ws, "reel-l", 6.0)
    (r / "beds").mkdir()
    M.write_wav(r / "beds" / "planted.wav", steady_bed(8.0))
    selection(r, [], bed_sel("planted.wav", exit_s=6))

    def chk():
        return script(ws, CHECKS / "licence_rows.py", r)

    c = chk()
    ck("music_licence: a planted bed with no licence row blocks (exit 1)", c.returncode == 1 and "block" in c.stdout,
       c.all[-300:])
    p = script(ws, "mix.py", "--reel", "reel-l", "--voice", "free", "--video", r / "locked.mp4")
    ck("music_licence: ... and mix.py refuses the final with a plain line", p.returncode == 1
       and "wasn't made" in p.stdout and not (r / "sound" / "final.mp4").exists(), p.all[-400:])
    mj = json.loads((r / "music.json").read_text(encoding="utf-8"))
    ck("music_licence: ... music.json records the unknown track with licence null",
       mj["licence"] is None and mj["file"] == "planted.wav", mj)
    c = chk()
    ck("music_licence: ... and licence_rows still exits 1 on it", c.returncode == 1, c.all[-300:])

    track = Path(scratch) / "bright-day.wav"
    M.write_wav(track, steady_bed(8.0, 0.2))
    cc = ["--licence", "CC BY 4.0", "--licence-url", "https://creativecommons.org/licenses/by/4.0/"]
    p = script(ws, "music_pick.py", "add-free", track, "--title", "Bright Day", *cc)
    ck("music_licence: add-free without an author is refused, nothing copied", p.returncode == 1
       and "author" in p.stdout and not (ws / "editor" / "music" / track.name).exists(), p.all[-300:])
    p = script(ws, "music_pick.py", "add-free", track, "--title", "Bright Day", "--author", "A. Composer", *cc,
               "--mood", "upbeat")
    line = '"Bright Day" by A. Composer, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)'
    lj = ws / "editor" / "music" / "library.json"
    lib = json.loads(lj.read_text(encoding="utf-8")) if lj.exists() else {}
    ck("music_licence: add-free CC-BY builds the standard attribution line", p.returncode == 0
       and lib.get(track.name, {}).get("attribution") == line and lib[track.name].get("sha256"), (p.all[-300:], lib))
    nc = Path(scratch) / "night-drive.wav"
    M.write_wav(nc, steady_bed(4.0, 0.2))
    p = script(ws, "music_pick.py", "add-free", nc, "--title", "Night Drive", "--author", "B", "--licence",
               "CC BY-NC 4.0", "--licence-url", "https://creativecommons.org/licenses/by-nc/4.0/")
    ck("music_licence: an NC licence is added with a plain warning", p.returncode == 0 and "non-commercial" in p.stdout,
       p.all[-300:])
    own = Path(scratch) / "my-song.wav"
    M.write_wav(own, steady_bed(8.0, 0.15))
    p = script(ws, "music_pick.py", "add-own", own, "--title", "My Song")
    ck("music_licence: add-own exits 0", p.returncode == 0, p.all[-300:])
    p = script(ws, "music_pick.py", "list")
    ck("music_licence: list shows the library with origin and licence status", p.returncode == 0
       and "Free library" in p.stdout and "Your track" in p.stdout and "needs the rights tick" in p.stdout, p.all[-500:])

    p = script(ws, "new_board.py", "--reel", "reel-l", "--video", r / "locked.mp4")
    cfg = json.loads((r / "config.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
    rows = {b["file"]: b for b in cfg.get("beds", [])}
    ck("music_licence: new_board puts the library tracks on the board with origin, licence_ok and rights",
       rows.get(track.name, {}).get("origin") == "free" and rows[track.name]["licence_ok"] is True
       and rows.get(own.name, {}).get("origin") == "own" and rows[own.name]["rights_confirmed"] is False
       and rows.get("planted.wav", {}).get("licence_ok") is False, (p.all[-400:], rows))

    selection(r, [], bed_sel(track.name, exit_s=6))
    p = script(ws, "music_pick.py", "pick", "reel-l")
    credits = (r / "credits.txt").read_text(encoding="utf-8") if (r / "credits.txt").exists() else ""
    ck("music_licence: pick writes credits.txt with the attribution line", p.returncode == 0 and line in credits,
       (p.all[-300:], credits))
    c = chk()
    ck("music_licence: ... and licence_rows passes the CC-BY track", c.returncode == 0, c.all[-300:])
    (r / "credits.txt").write_bytes(b"\n")
    ck("music_licence: a CC-BY track whose line isn't in credits.txt blocks",
       any(x["where"] == "credits.txt" for x in licence_rows.run({"reel_dir": r})))
    b = bytearray((r / "beds" / track.name).read_bytes())
    b[-10] ^= 1
    (r / "beds" / track.name).write_bytes(bytes(b))
    ck("music_licence: a track whose bytes changed since its row was written blocks",
       any("isn't the one" in x["msg"] for x in licence_rows.run({"reel_dir": r})))

    selection(r, [], bed_sel(own.name, exit_s=6))
    script(ws, "music_pick.py", "pick", "reel-l")
    c = chk()
    ck("music_licence: an own track without the rights tick blocks", c.returncode == 1 and "rights" in c.stdout,
       c.all[-300:])
    selection(r, [], bed_sel(own.name, exit_s=6, rights_confirmed=True))
    script(ws, "music_pick.py", "pick", "reel-l")
    c = chk()
    lib = json.loads(lj.read_text(encoding="utf-8"))
    mj = json.loads((r / "music.json").read_text(encoding="utf-8"))
    ck("music_licence: ... with the tick it passes, recorded in music.json and the library", c.returncode == 0
       and mj["rights_confirmed"] is True and lib[own.name]["rights_confirmed"] is True, (c.all[-300:], mj))

    selection(r, [])
    script(ws, "music_pick.py", "pick", "reel-l")
    ck("music_licence: no bed picked removes music.json and credits.txt",
       not (r / "music.json").exists() and not (r / "credits.txt").exists())
    (ws / "editor" / "sound" / "beds").mkdir(parents=True, exist_ok=True)
    shutil.copy2(own, ws / "editor" / "sound" / "beds" / own.name)
    p = script(ws, "new_board.py", "--reel", "reel-l", "--video", r / "locked.mp4")
    ck("music_licence: a name in both the pack and the music library is refused plainly", p.returncode == 1
       and "both have" in p.stdout, p.all[-300:])


def case_music_absent(scratch):
    import licence_rows
    ws = workspace(scratch, "music_absent")
    r = reel_with_picture(scratch, ws, "reel-n", 6.0)
    p = script(ws, "new_board.py", "--reel", "reel-n", "--video", r / "locked.mp4")
    cfg = json.loads((r / "config.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
    ck("music_absent: new_board with no sound library at all exits 0 with no beds", p.returncode == 0
       and cfg.get("beds") == [], p.all[-400:])
    p = script(ws, "mix.py", "--reel", "reel-n", "--voice", "free", "--video", r / "locked.mp4")
    ck("music_absent: mix renders a voice-only final", p.returncode == 0 and (r / "sound" / "final.mp4").exists(),
       p.all[-500:])
    if (r / "sound" / "final.mp4").exists():
        final_ok("music_absent", r / "sound" / "final.mp4", r / "locked.mp4")
    ck("music_absent: no music.json, and the licence check has no rows",
       not (r / "music.json").exists() and licence_rows.run({"reel_dir": r}) == [])


def case_music_strongest(scratch):
    import music_fit
    rng = np.random.default_rng(11)
    x = np.concatenate([rng.normal(0, 0.01, 10 * SR), rng.normal(0, 0.3, 10 * SR)])
    x = np.stack([x, x], 1)
    e = music_fit.suggest_entry(x, SR, 8.0)
    ck("music_strongest: quiet 10 s then loud: the entry lands on the loud section (10 +-0.5 s)", abs(e - 10.0) <= 0.5, e)
    e = music_fit.suggest_entry(x[::-1], SR, 8.0)
    ck("music_strongest: reversed (loud first): the 8 s window stays inside the loud 10 s", e <= 2.0, e)
    e = music_fit.suggest_entry(x[:5 * SR], SR, 8.0)
    ck("music_strongest: a track shorter than the cut starts at 0", e == 0.0, e)


CASES = {"free_master": case_free_master, "cost_ask": case_cost_ask, "pack": case_pack, "ingest_trim": case_ingest_trim,
         "room_tone": case_room_tone, "quiet_gate": case_quiet_gate, "bake_exact": case_bake_exact,
         "music_level": case_music_level, "music_seam": case_music_seam, "music_licence": case_music_licence,
         "music_absent": case_music_absent, "music_strongest": case_music_strongest}


def main():
    global M, MA, SR, SCRIPTS, CHECKS, PLUGIN_ROOT, room_tone, cost_ask
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=sorted(CASES), action="append")
    ap.add_argument("--scratch")
    ap.add_argument("--plugin", default=str(PLUGIN))
    a = ap.parse_args()
    PLUGIN_ROOT = Path(a.plugin)
    SCRIPTS = PLUGIN_ROOT / "skills" / "reel-sound-pass" / "scripts"
    CHECKS = PLUGIN_ROOT / "skills" / "_shared" / "checks"
    sys.path.insert(0, str(SCRIPTS))
    sys.path.insert(0, str(CHECKS))
    import _media as M  # noqa: E402
    import master_audio as MA  # noqa: E402
    import room_tone  # noqa: E402
    import cost_ask  # noqa: E402
    SR = M.SR
    scratch = Path(a.scratch) if a.scratch else Path(tempfile.mkdtemp(prefix="sound-pass-test-"))
    scratch.mkdir(parents=True, exist_ok=True)
    for name in a.case or sorted(CASES):
        t0 = time.time()
        try:
            CASES[name](scratch)
        except Exception as e:  # a crash is a failed case, never a silent pass
            ck("%s: ran without crashing" % name, False, "%s: %s" % (type(e).__name__, e))
        print("INFO %s took %.1f s" % (name, time.time() - t0), flush=True)
    passed = sum(results)
    print("%d passed, %d failed" % (passed, len(results) - passed))
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
