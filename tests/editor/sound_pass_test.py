#!/usr/bin/env python3
"""S5 check for reel-sound-pass (part A): the mix pipeline, the Auphonic cost ask, the sound library, room tone,
the quiet gate, the stem bake, and (N2) the beat grid, the beat-synced bed, the cue pre-fill and the hit offsets.
Synthetic media made with ffmpeg here, plus two real beds from EDITOR_TEST_SOUND_PACK; no network (Auphonic is
faked in-process, the pack comes from a file:// URL).

usage: EDITOR_SE_HOME=<installed state> <state python> -X utf8 -I tests/editor/sound_pass_test.py
           [--case free_master|cost_ask|pack|ingest_trim|room_tone|quiet_gate|bake_exact|music_level|music_seam|
                   music_licence|music_absent|music_strongest|beat_grid|beat_grid_hard|beat_fit|edl_hash|
                   prefill|peak_offset|beat_steady|beat_drift|beat_half_trap|beat_real_bed|big_hits|sfx_peak_silence|
                   safe-fetch|no-overwrite] [--scratch <dir>]
           [--plugin <plugin root>]
Each case finishes in well under 150 s. Prints PASS/FAIL per check, then counts; exit 1 on any fail,
77 when blocked without failures. beat_real_bed reports BLOCKED if the local pack is missing or has the wrong hash.
"""
import argparse, hashlib, io, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, zipfile
from pathlib import Path

sys.dont_write_bytecode = True  # Tests read plugin modules without creating plugin cache files.

import numpy as np

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugins" / "editor-superengine"
results = []


class Blocked(RuntimeError):
    pass


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


def case_safe_fetch(scratch):
    """No network: exercise the actual fetch entry point with fake responses."""
    import contextlib
    from unittest.mock import patch
    import safe_fetch
    import sfx_ingest
    from types import SimpleNamespace

    class Reply(io.BytesIO):
        def __init__(self, body=b"", status=200, headers=None):
            super().__init__(body)
            self.status, self.headers = status, headers or {}
            self.bytes_read = 0

        def read(self, n=-1):
            data = super().read(n)
            self.bytes_read += len(data)
            return data

    ws = workspace(scratch, "safe-fetch")
    pack = io.BytesIO()
    with zipfile.ZipFile(pack, "w") as z:
        z.writestr("hit.wav", b"pack sound")
    data = pack.getvalue()
    manifest = dict(url="https://assets.example/pack.zip", bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    mf = ws / "manifest.json"
    mf.write_bytes((json.dumps(manifest) + "\n").encode("utf-8"))
    target = ws / "download.tmp"
    for location in ("http://10.1.2.3/p.zip", "http://[::1]/", "file:///pack.zip"):
        out, calls = io.StringIO(), []

        def redirect(url):
            calls.append(url)
            return Reply(status=302, headers={"Location": location})

        with patch.object(sfx_ingest, "library", return_value=ws / "sound"), patch.object(safe_fetch, "send", redirect), contextlib.redirect_stdout(out):
            rc = sfx_ingest.fetch(SimpleNamespace(manifest=mf))
        ck("safe-fetch: redirect checked before second request", rc == 1 and len(calls) == 1
           and not (ws / "sound").exists() and len(out.getvalue().splitlines()) == 1, out.getvalue())
    for headers in ({}, {"Content-Length": "1000"}):
        response = Reply(b"x" * 1000, headers=headers)
        try:
            safe_fetch.download(manifest["url"], target, 10, send=lambda url: response)
            refused = False
        except ValueError:
            refused = True
        ck("safe-fetch: cap aborts early and removes temp", refused and response.bytes_read <= 11
           and not target.exists(), response.bytes_read)
    hops = []

    def loop(url):
        hops.append(url)
        return Reply(status=302, headers={"Location": "/again"})

    try:
        safe_fetch.download(manifest["url"], target, 10, send=loop)
        refused = False
    except ValueError:
        refused = True
    ck("safe-fetch: at most five redirects", refused and len(hops) == 6 and not target.exists(), hops)
    for host in ("localhost", "sub.localhost", "host.local", "host.internal", "127.0.0.1", "169.254.1.2", "127.1", "127.0x0.0.1"):
        try:
            safe_fetch.check_url("http://" + host + "/pack.zip")
            refused = False
        except ValueError:
            refused = True
        ck("safe-fetch: local host refused", refused, host)
    for url in ("file:////10.1.2.3/share/pack.zip", "file:///%2f10.1.2.3/share/pack.zip",
                "file:///\\\\10.1.2.3/share/pack.zip"):
        try:
            safe_fetch.check_url(url, first=True)
            refused = False
        except ValueError:
            refused = True
        ck("safe-fetch: network file path refused", refused, url)
    out = io.StringIO()
    with patch.object(sfx_ingest, "library", return_value=ws / "sound"), patch.object(safe_fetch, "send", return_value=Reply(data)), contextlib.redirect_stdout(out):
        rc = sfx_ingest.fetch(SimpleNamespace(manifest=mf))
    ck("safe-fetch: valid bounded download unpacks", rc == 0 and (ws / "sound/hit.wav").read_bytes() == b"pack sound", out.getvalue())
    # A safe redirect is allowed, including https -> http, with exact byte cap.
    replies = iter([Reply(status=302, headers={"Location": "http://assets.example/final.zip"}), Reply(data)])
    safe_fetch.download(manifest["url"], target, len(data), send=lambda url: next(replies))
    ck("safe-fetch: public redirect passes", target.read_bytes() == data)


def case_no_overwrite(scratch):
    ws = workspace(scratch, "no-overwrite")
    first, second = ws / "a/hit.wav", ws / "b/hit.wav"
    first.parent.mkdir(); second.parent.mkdir()
    M.write_wav(first, tone(.3, 440))
    M.write_wav(second, tone(.3, 880))
    p = script(ws, "sfx_ingest.py", "add", first)
    lib = ws / "editor/sound"
    ck("no-overwrite: first add succeeds", p.returncode == 0 and (lib / "hit.wav").is_file(), p.all)
    original = (lib / "hit.wav").read_bytes()
    p = script(ws, "sfx_ingest.py", "add", second)
    ck("no-overwrite: second add gets first free name", p.returncode == 0 and (lib / "hit-2.wav").is_file()
       and "Kept hit.wav (yours); writing hit-2.wav instead." in p.stdout
       and (lib / "hit.wav").read_bytes() == original, p.all)
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.write(second, "hit.wav")
        z.write(second, "fresh.wav")
    pack = ws / "pack.zip"
    pack.write_bytes(data.getvalue())
    mf = ws / "manifest.json"
    mf.write_bytes((json.dumps(dict(url=pack.as_uri(), bytes=len(data.getvalue()),
                   sha256=hashlib.sha256(data.getvalue()).hexdigest())) + "\n").encode("utf-8"))
    p = script(ws, "sfx_ingest.py", "fetch", "--manifest", mf)
    ck("no-overwrite: pack keeps original, uses next free name", p.returncode == 0 and (lib / "hit-3.wav").is_file()
       and "writing hit-3.wav instead" in p.stdout and (lib / "hit.wav").read_bytes() == original, p.all)
    ck("no-overwrite: fresh pack member keeps its name", (lib / "fresh.wav").read_bytes() == second.read_bytes())
    idx = json.loads((lib / "library-index.json").read_text(encoding="utf-8"))
    ck("no-overwrite: all retained and new names indexed", {"hit.wav", "hit-2.wav", "hit-3.wav", "fresh.wav"} <= idx["files"].keys())
    p = script(ws, "sfx_ingest.py", "verify")
    ck("no-overwrite: final index verifies", p.returncode == 0, p.all)


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
         "fade_in_s": 0.5, "fade_out_s": 0.8, "stops": [], "carve": {"on": False, "strength": 0.8}}
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


# ------------------------------------------------------------------ beat grid, bed fit, cue pre-fill, peak offset (N2)
def click_track(seconds, bpm, phase, accent=0, seed=0):
    """F-16 click track: a pitch-dropping kick burst on every beat (the beat with k % 4 == accent louder), a quieter
    hi-hat halfway between beats, light noise underneath. (stereo float32, the true beat times in s)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = rng.normal(0, 0.003, n)
    p = 60 / bpm
    tk = np.arange(int(0.15 * SR)) / SR
    kick = (np.sin(2 * np.pi * (50 * tk + 3 * (1 - np.exp(-tk / 0.03)))) * np.exp(-tk / 0.06)
            * np.minimum(1, tk / 0.001))
    th = np.arange(int(0.03 * SR)) / SR
    hat = np.diff(rng.normal(0, 1, len(th) + 1)) * np.exp(-th / 0.008) * 0.5
    true, k = [], 0
    while phase + k * p < seconds - 0.05:
        i = int(round((phase + k * p) * SR))
        x[i:i + len(kick)] += (0.9 if k % 4 == accent else 0.6) * kick[:n - i]
        j = int(round((phase + (k + 0.5) * p) * SR))
        if j < n:
            x[j:j + len(hat)] += 0.15 * hat[:n - j]
        true.append(i / SR)
        k += 1
    return np.stack([x, x], 1).astype(np.float32), np.array(true)


def trap_track(seconds, bpm, phase, seed=0):
    """A trap-like bar: a long 808 kick on 1 and the and-of-2, a snare on 2 and 4, hats in triplets with a roll in the
    last beat of every other bar, light noise. Its kick pattern repeats every 1.5 beats, which a plain self-match
    reads as 2/3 of the tempo. (stereo float32, the true beat times in s)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = rng.normal(0, 0.003, n)
    p = 60 / bpm

    def put(t, s, g):
        i = int(round(t * SR))
        if 0 <= i < n:
            x[i:i + len(s)] += g * s[:n - i]
    tk = np.arange(int(0.5 * SR)) / SR
    kick = np.sin(2 * np.pi * (45 * tk + 4 * (1 - np.exp(-tk / 0.02)))) * np.exp(-tk / 0.25) * np.minimum(1, tk / 0.001)
    ts = np.arange(int(0.18 * SR)) / SR
    snare = (rng.normal(0, 1, len(ts)) * 0.7 + np.sin(2 * np.pi * 190 * ts)) * np.exp(-ts / 0.05)
    th = np.arange(int(0.025 * SR)) / SR
    hat = np.diff(rng.normal(0, 1, len(th) + 1)) * np.exp(-th / 0.006)
    true, b = [], 0
    while phase + 4 * b * p < seconds:
        t0 = phase + 4 * b * p
        true += [int(round((t0 + q * p) * SR)) / SR for q in range(4) if t0 + q * p < seconds - 0.05]
        put(t0, kick, 0.8)
        put(t0 + 1.5 * p, kick, 0.7)
        put(t0 + p, snare, 0.5)
        put(t0 + 3 * p, snare, 0.5)
        for h in range(12):                                 # triplet eighths; a 4-note roll on each of the last 3
            if b % 2 and h >= 9:
                for r in range(4):
                    put(t0 + (h + r / 4) * p / 3, hat, 0.25)
            else:
                put(t0 + h * p / 3, hat, 0.3 if h % 3 == 0 else 0.22)
        b += 1
    return np.stack([x, x], 1).astype(np.float32), np.array(true)


def grid_lines(g, until):
    k = np.arange(int(max(0.0, until - g["phase_s"]) / g["period_s"]) + 1)
    t = g["phase_s"] + k * g["period_s"]
    return t[t <= until]


def frame_gap(g, true, fps):
    """The worst distance in frames, both ways: true click to its nearest grid line, grid line to its nearest click."""
    lines = grid_lines(g, true[-1] + g["period_s"] / 2)
    a = np.abs(np.rint(true[:, None] * fps) - np.rint(lines[None, :] * fps))
    return float(max(a.min(1).max(), a.min(0).max()))


def phase_off(g, at):
    """How far (s) the grid's nearest beat is from time at."""
    d = (g["phase_s"] - at) % g["period_s"]
    return min(d, g["period_s"] - d)


TEMPOS = [(72, 0.137, 50, 0), (98, 0.41, 40, 1), (123.4, 0.25, 60, 2), (140, 0.033, 45, 3), (174, 0.29, 55, 0)]


def case_beat_grid(scratch):
    import beat_grid
    d = Path(scratch) / "beat_grid"
    d.mkdir(parents=True, exist_ok=True)
    for bpm, phase, sec, acc in TEMPOS:
        x, true = click_track(sec, bpm, phase, acc, seed=int(bpm))
        f = d / ("click-%g.wav" % bpm)
        M.write_wav(f, x)
        g = beat_grid.grid(f)
        ck("beat_grid %g BPM: a grid is found with no tempo hint" % bpm, g is not None, g)
        if not g:
            continue
        print("INFO %g BPM -> %s" % (bpm, g))
        ck("beat_grid %g BPM: BPM within 0.5 %%" % bpm, abs(g["bpm"] - bpm) / bpm <= 0.005, g["bpm"])
        for fps in (30, 30000 / 1001):
            gap = frame_gap(g, true, fps)
            ck("beat_grid %g BPM: every grid line within 2 frames of the true click at %.2f fps, all %.0f s"
               % (bpm, fps, sec), gap <= 2, gap)
        ck("beat_grid %g BPM: the bar starts on the accented beat" % bpm,
           abs(g["downbeat_s"] - true[acc]) < g["period_s"] / 8, (g["downbeat_s"], true[acc]))
    x, true = click_track(50, 72, 0.137, 0, seed=72)
    wrong = {"phase_s": float(true[0]), "period_s": 60 / (72 * 1.01)}
    gap = frame_gap(wrong, true, 30)
    ck("beat_grid: reverse, a grid at the true BPM + 1 % fails the 2-frame check", gap > 2, gap)
    rng = np.random.default_rng(3)
    nz = rng.normal(0, 0.2, 45 * SR)
    M.write_wav(d / "noise.wav", np.stack([nz, nz], 1))
    ck("beat_grid: steady noise has no grid", beat_grid.grid(d / "noise.wav") is None)
    p = script(Path(scratch), "beat_grid.py", d / "noise.wav")
    ck("beat_grid: the command says so plainly, exit 1", p.returncode == 1 and "No steady beat" in p.stdout
       and "Traceback" not in p.all, p.all[-300:])
    p = script(Path(scratch), "beat_grid.py", d / "click-98.wav")
    ok = p.returncode == 0 and abs(json.loads(p.stdout or "{}").get("bpm", 0) - 98) < 0.5
    ck("beat_grid: the command prints the grid as JSON, exit 0", ok, p.all[-300:])


def case_beat_grid_hard(scratch):
    """Real-music shape: a trap bar (kick on 1 and the and-of-2, snare on 2 and 4, triplet hats and rolls) must read at
    its own tempo, not 2/3 or 4/3 of it, and still clear the confidence cut-off."""
    import beat_grid
    d = Path(scratch) / "beat_grid_hard"
    d.mkdir(parents=True, exist_ok=True)
    for bpm, phase, sec, seed in ((130, 0.21, 45, 0), (130, 0.07, 60, 1), (140, 0.33, 50, 2)):
        x, true = trap_track(sec, bpm, phase, seed)
        f = d / ("trap-%g-%d.wav" % (bpm, seed))
        M.write_wav(f, x)
        g = beat_grid.grid(f)
        ck("beat_grid_hard trap %g BPM (seed %d): a grid is found with no tempo hint" % (bpm, seed), g is not None, g)
        if not g:
            continue
        print("INFO trap %g BPM -> %s" % (bpm, g))
        ck("beat_grid_hard trap %g BPM (seed %d): BPM within 0.5 %% (not 2/3 or 4/3 of it)" % (bpm, seed),
           abs(g["bpm"] - bpm) / bpm <= 0.005, g["bpm"])
        for fps in (30, 30000 / 1001):
            gap = frame_gap(g, true, fps)
            ck("beat_grid_hard trap %g BPM (seed %d): every grid line within 2 frames of the true beat at %.2f fps"
               % (bpm, seed, fps), gap <= 2, gap)


def case_beat_fit(scratch):
    import beat_grid
    ws = workspace(scratch, "beat_fit")
    r = reel_with_picture(scratch, ws, "reel-bf", 27.4)
    (r / "beds").mkdir()
    x, true = click_track(40, 123.4, 0.25, 0, seed=4)
    M.write_wav(r / "beds" / "clicks.wav", x)
    track_s, entry = len(x) / SR, 1.0
    N = int(round(M.probe(r / "locked.mp4")["dur"] * SR))

    def bake_with(offset, sync):
        selection(r, [], bed_sel("clicks.wav", entry_s=entry, exit_s=27.4, offset_s=offset, beat_sync=sync,
                                 fade_in_s=0.3, fade_out_s=0.8))
        p = script(ws, "bake.py", "--reel", "reel-bf", "--video", r / "locked.mp4")
        pb = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))["bed"] if p.returncode == 0 else {}
        return p, pb, beat_grid.grid(r / "sound" / "music.wav")

    p, pb, g = bake_with(3.37, True)
    ck("beat_fit: bake exits 0 with beat-sync on", p.returncode == 0, p.all[-400:])
    ck("beat_fit: the music stem is the picture's length N", len(M.decode(r / "sound" / "music.wav")) == N)
    bt = pb.get("beat") or {}
    ck("beat_fit: placement.json records the beat detail", bt.get("offset_from_s") == 3.37
       and all(k in bt for k in ("bpm", "period_s", "phase_s", "downbeat_s", "offset_s"))
       and pb.get("offset_s") == bt.get("offset_s"), pb.get("beat"))
    off = phase_off(g, entry) if g else None
    print("INFO beat-sync at 3.37 s -> offset %s, stem grid %s, kick phase vs entry %s s" % (pb.get("offset_s"), g, off))
    ck("beat_fit: the stem's kicks sit on the entry (phase <= 25 ms)", off is not None and off <= 0.025, off)

    p0 = bt.get("period_s") or 60 / 123.4
    far = bt.get("phase_s", 0.25) + round((30.0 - bt.get("phase_s", 0.25)) / p0) * p0     # on a beat, as the board sends it
    p, pb, g = bake_with(far, True)
    bt = pb.get("beat") or {}
    bars = (far - bt.get("offset_s", far)) / (4 * p0)
    ck("beat_fit: a track start near the end steps back whole bars (4 beats, within 2 ms)",
       p.returncode == 0 and round(bars) >= 1 and abs(bars - round(bars)) * 4 * p0 <= 0.002, (far, bt, p.all[-300:]))
    ck("beat_fit: ... with one plain line", "bars earlier so it lasts the whole reel" in p.stdout, p.stdout[-300:])
    st = M.decode(r / "sound" / "music.wav").astype(np.float64)
    dur = N / SR
    ck("beat_fit: ... and the music plays to the cut's end", abs(pb.get("exit_s", 0) - dur) < 1e-3
       and entry + track_s - bt.get("offset_s", far) >= dur - 1e-3
       and win_rms(st, dur - 2.8, dur - 0.8) >= win_rms(st, 5.0, 15.0) - 3,
       (pb.get("exit_s"), round(win_rms(st, dur - 2.8, dur - 0.8), 1), round(win_rms(st, 5.0, 15.0), 1)))
    off = phase_off(g, entry) if g else None
    ck("beat_fit: ... still on the beat (phase <= 25 ms)", off is not None and off <= 0.025, off)

    p, pb, g = bake_with(3.37, False)
    off = phase_off(g, entry) if g else None
    print("INFO beat-sync off at 3.37 s -> kick phase vs entry %s s" % off)
    ck("beat_fit: reverse, beat-sync off at 3.37 s leaves the kicks off the entry (> 25 ms)",
       p.returncode == 0 and pb.get("beat") is None and off is not None and off > 0.025, off)
    ck("beat_fit: beat-sync off is recorded as off, so no 'no steady beat' line can show", pb.get("beat_sync") is False, pb.get("beat_sync"))

    M.write_wav(r / "beds" / "steady.wav", steady_bed(30.0))           # sines only: no beat to find
    selection(r, [], bed_sel("steady.wav", exit_s=27.4, offset_s=1.23, beat_sync=True))
    p = script(ws, "bake.py", "--reel", "reel-bf", "--video", r / "locked.mp4")
    pb = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))["bed"] if p.returncode == 0 else {}
    ck("beat_fit: beat-sync on a track with no steady beat says so plainly and places it as the board set it",
       p.returncode == 0 and "No steady beat" in p.stdout and pb.get("beat") is None and pb.get("offset_s") == 1.23,
       (p.all[-300:], pb.get("offset_s")))
    ck("beat_fit: a refused grid is recorded with beat-sync on", pb.get("beat_sync") is True, pb.get("beat_sync"))


def drum_track(times, strengths, seconds=10.0, snares=()):
    """Short drum fixture with explicit beat times, kick levels and optional snare beats; no hats."""
    n = int(seconds * SR)
    x = np.zeros(n)
    tk = np.arange(int(0.15 * SR)) / SR
    kick = (np.sin(2 * np.pi * (50 * tk + 3 * (1 - np.exp(-tk / 0.03)))) * np.exp(-tk / 0.06)
            * np.minimum(1, tk / 0.001))
    ts = np.arange(int(0.03 * SR)) / SR
    snare = (np.random.default_rng(0).normal(0, 1, len(ts)) + np.sin(2 * np.pi * 190 * ts)) * np.exp(-ts / 0.05)
    for k, (at, strength) in enumerate(zip(times, strengths)):
        i = int(round(at * SR))
        if 0 <= i < n:
            hit = snare if k in snares else kick
            x[i:i + len(hit)] += strength * hit[:n - i]
    return np.stack([x, x], 1).astype(np.float32)


def case_beat_steady(scratch):
    import beat_grid
    d = Path(scratch) / "beat_steady"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "steady.wav"
    M.write_wav(f, click_track(10, 120, 0.1)[0])
    g = beat_grid.grid(f)
    ck("beat_steady: ten seconds at 120 BPM finds a grid", g is not None, beat_grid.LAST_REASON)
    if g:
        ck("beat_steady: BPM within 0.5 %", abs(g["bpm"] - 120) / 120 <= 0.005, g)
        ck("beat_steady: median refit residual is at most 10 ms", g["residual_ms"] <= 10, g)
        ck("beat_steady: diagnostic residuals bound the median",
           0 <= g["residual_ms"] <= g["residual_p90_ms"] <= g["residual_max_ms"], g)
        ck("beat_steady: acceptance clears the last refusal reason", beat_grid.LAST_REASON is None)
        kicks = g["kicks"]
        ck("beat_steady: every grid line has a kick strength in time order", len(kicks) == 20
           and all(a[0] < b[0] for a, b in zip(kicks, kicks[1:])), kicks)
        ck("beat_steady: kick times and strengths have four and three decimal places",
           all(at == round(at, 4) and strength == round(strength, 3) for at, strength in kicks), kicks)
    limit = beat_grid.MAX_RESIDUAL
    try:
        beat_grid.MAX_RESIDUAL = 0.001
        ck("beat_steady: reverse, a 1 ms limit refuses the same audio", beat_grid.grid(f) is None
           and beat_grid.LAST_REASON == "drift", beat_grid.LAST_REASON)
    finally:
        beat_grid.MAX_RESIDUAL = limit
    # Seven strong lines cannot establish a grid, even with the residual limit relaxed.
    sparse = d / "seven.wav"
    M.write_wav(sparse, drum_track(0.1 + np.arange(7) * 0.5, np.full(7, 0.9)))
    try:
        beat_grid.MAX_RESIDUAL = 1
        ck("beat_steady: fewer than eight supported lines refuses as no beat, never drift, even with a loose limit",
           beat_grid.grid(sparse) is None and beat_grid.LAST_REASON == "no beat", beat_grid.LAST_REASON)
    finally:
        beat_grid.MAX_RESIDUAL = limit


def case_beat_drift(scratch):
    import beat_grid, music_fit
    ws = workspace(scratch, "beat_drift")
    r = ws / "videos" / "reel-d"
    (r / "beds").mkdir(parents=True)
    f = r / "beds" / "drifting.wav"
    p0, pend = 60 / 116, 60 / 124
    c = (pend ** 2 - p0 ** 2) / (4 * 10)
    k = np.arange(24)
    times = 0.1 + p0 * k + c * k ** 2
    times = times[times < 9.95]
    M.write_wav(f, drum_track(times, np.full(len(times), 0.8)))
    ck("beat_drift: a slide from 116 to 124 BPM refuses with drift", beat_grid.grid(f) is None
       and beat_grid.LAST_REASON == "drift", beat_grid.LAST_REASON)
    p = script(ws, "beat_grid.py", f)
    ck("beat_drift: CLI exits 1 with the plain drift line", p.returncode == 1
       and "drifts, so the music starts where the board set it and nothing snaps to the beat." in p.stdout
       and "Traceback" not in p.all, p.all[-400:])
    limit = beat_grid.MAX_RESIDUAL
    try:
        beat_grid.MAX_RESIDUAL = 1
        g = beat_grid.grid(f)
        ck("beat_drift: reverse, relaxing only the residual gate admits the same track", g is not None, g)
        if g:
            ck("beat_drift: its median refit residual exceeds 10 ms", g["residual_ms"] > 10, g)
    finally:
        beat_grid.MAX_RESIDUAL = limit
    cache = r / "work" / "beats" / "drifting.wav.json"
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    stale = {"sha256": sha, "grid": {"bpm": 120, "period_s": 0.5, "phase_s": 0.1, "downbeat_s": 0.1}}
    for version in (None, beat_grid.VERSION - 1):
        record = dict(stale)
        if version is not None:
            record["version"] = version
        M.write_json(cache, record)
        got = music_fit.bed_grid(r, f.name)
        saved = json.loads(cache.read_text(encoding="utf-8"))
        ck("beat_drift: cache version %s is recomputed, old accepted grid discarded" % version,
           got is None and saved.get("version") == beat_grid.VERSION and saved.get("grid") is None
           and beat_grid.LAST_REASON == "drift", saved)
    beat_grid.LAST_REASON = None
    out = io.StringIO()
    from contextlib import redirect_stdout
    with redirect_stdout(out):
        offset, detail = music_fit.snap(r, {"file": f.name}, 0, 1.23, 10, 8)
    ck("beat_drift: cached refusal keeps the board offset and explains drift", offset == 1.23 and detail is None
       and "drifts, so" in out.getvalue(), out.getvalue())
    silent = r / "beds" / "silence.wav"
    M.write_wav(silent, np.zeros((4 * SR, 2), np.float32))
    ck("beat_drift: a later no-beat call clears a stale drift reason", beat_grid.grid(silent) is None
       and beat_grid.LAST_REASON == "no beat", beat_grid.LAST_REASON)


def case_beat_half_trap(scratch):
    import beat_grid
    d = Path(scratch) / "beat_half_trap"
    d.mkdir(parents=True, exist_ok=True)
    times = 0.1 + np.arange(20) * 0.5
    f = d / "backbeat.wav"
    levels = np.where(np.arange(20) % 2 == 0, 0.9, 0.3)
    M.write_wav(f, drum_track(times, levels, snares=range(1, 20, 2)))
    g = beat_grid.grid(f)
    ck("beat_half_trap: full-band backbeats preserve 120 BPM", g is not None
       and abs(g["bpm"] - 120) / 120 <= 0.005, g or beat_grid.LAST_REASON)
    if g:
        checks = g["tempo_check"]
        ck("beat_half_trap: all three candidates are recorded", len(checks) == 3, checks)
        ck("beat_half_trap: candidate scores are precision and recall in [0, 1]", all(
            0 <= row["precision"] <= 1 and 0 <= row["recall"] <= 1
            for row in checks if row["eligible"]), checks)
        ck("beat_half_trap: only eligible candidates stay inside 60-200 BPM", all(
            60 <= row["bpm"] <= 200 for row in checks if row["eligible"]), checks)
        outside = [row for row in checks if row["bpm"] < 60 or row["bpm"] > 200]
        ck("beat_half_trap: an out-of-range relative is not eligible and never chosen", bool(outside)
           and all(row["eligible"] is False and row["precision"] is None and row["recall"] is None
                   and abs(row["bpm"] - g["bpm"]) > 0.5 for row in outside), checks)
    f = d / "kick-only.wav"
    M.write_wav(f, drum_track(times[::2], np.full(10, 0.9)))
    g = beat_grid.grid(f)
    ck("beat_half_trap: reverse, kicks alone at 60 BPM stay at 60", g is not None
       and abs(g["bpm"] - 60) / 60 <= 0.005, g or beat_grid.LAST_REASON)


# ElevenLabs Music beds from the editor's sound pack; credited in LICENSES/SOUND-PACK-CREDITS.md.
def case_beat_real_bed(scratch):
    import beat_grid
    pack_path = os.environ.get("EDITOR_TEST_SOUND_PACK")
    if not pack_path or not Path(pack_path).is_file():
        raise Blocked("set EDITOR_TEST_SOUND_PACK to the editor sound pack zip")
    manifest = json.loads((PLUGIN_ROOT / "skills/reel-sound-pass/pack.json").read_text(encoding="utf-8"))
    try:
        sha = hashlib.sha256(Path(pack_path).read_bytes()).hexdigest()
    except OSError:
        raise Blocked("the editor sound pack zip could not be read") from None
    if sha != manifest["sha256"]:
        raise Blocked("the editor sound pack zip sha256 does not match pack.json")
    d = Path(scratch) / "beat_real_bed"
    d.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pack_path) as pack:
        for member, bpm in (("beds/dark-trap-d-minor-130.mp3", 130), ("beds/bed-0720-a.mp3", 120),
                            ("beds/founders-focus.mp3", 130)):
            f = Path(pack.extract(member, d))
            g = beat_grid.grid(f)
            ck("beat_real_bed %s: grid accepted" % member, g is not None, beat_grid.LAST_REASON)
            if g:
                measured = {key: g[key] for key in ("bpm", "residual_ms", "residual_p90_ms", "residual_max_ms")}
                print("INFO beat_real_bed %s: %s" % (member, json.dumps(measured)), flush=True)
                ck("beat_real_bed %s: BPM within 0.5 %%" % member, abs(g["bpm"] - bpm) / bpm <= 0.005, g)
                ck("beat_real_bed %s: median refit residual at most 10 ms" % member, g["residual_ms"] <= 10, g)


def case_big_hits(scratch):
    ws = workspace(scratch, "big_hits")
    r = reel_with_picture(scratch, ws, "reel-bh", 10.0)
    (r / "beds").mkdir()
    # At 198 BPM, three hits sixteen beats apart fit inside ten seconds.
    times = 0.1 + np.arange(33) * (60 / 198)
    loud = np.array([0, 16, 32])
    strengths = np.full(33, 0.4)
    strengths[loud] = [0.95, 0.9, 0.85]
    entry = 0.05

    def bake_hits(name, levels, offset=0.1, end=10.0):
        M.write_wav(r / "beds" / name, drum_track(times, levels))
        selection(r, [], bed_sel(name, entry_s=entry, exit_s=end, offset_s=offset, beat_sync=True))
        p = script(ws, "bake.py", "--reel", "reel-bh", "--video", r / "locked.mp4")
        placement = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
        bed = placement.get("bed") or {}
        beat = bed.get("beat") or {}
        hits = beat.get("big_hits_s", [])
        ck("big_hits %s: bake writes big_hits_s in placement.json" % name, p.returncode == 0
           and "big_hits_s" in beat, p.all[-400:])
        ck("big_hits %s: up to 3 strong beats, separated by at least sixteen beats" % name, len(hits) <= 3
           and all(abs(a - b) + 2e-4 >= 16 * beat.get("period_s", 60 / 198)
                   for i, a in enumerate(hits) for b in hits[i + 1:]), hits)
        ck("big_hits %s: every hit is inside the played window" % name,
           all(entry <= t < bed.get("exit_s", end) for t in hits), hits)
        return hits, bed

    hits, bed = bake_hits("loud.wav", strengths)
    planted = entry + times[loud] - bed.get("offset_s", 0.1)
    ck("big_hits: all three spaced loud kicks survive the spacing rule", len(hits) == 3
       and all(min(abs(t - at) for at in planted) <= 1 / 30 for t in hits), (hits, planted.tolist()))
    ck("big_hits: loud kicks are strongest first and within one frame", len(hits) == 3
       and all(abs(t - at) <= 1 / 30 for t, at in zip(hits, planted)), hits)
    cached = json.loads((r / "work" / "beats" / "loud.wav.json").read_text(encoding="utf-8"))
    kicks = (cached.get("grid") or {}).get("kicks", [])
    ck("big_hits: all thirty-three grid beats have kick records in time order", len(kicks) == 33
       and all(a[0] < b[0] for a, b in zip(kicks, kicks[1:])), kicks)
    hits, bed = bake_hits("window.wav", strengths, offset=1.6, end=7.5)
    ck("big_hits: excluded loud kicks do not suppress the strongest played kick", len(hits) == 1
       and abs(hits[0] - (entry + times[16] - bed.get("offset_s", 1.6))) <= 1 / 30, hits)
    single = np.full(33, 0.4)
    single[0] = 0.95
    hits, bed = bake_hits("threshold.wav", single)
    ck("big_hits: distant kicks below sixty percent are excluded", len(hits) == 1
       and abs(hits[0] - (entry + times[0] - bed.get("offset_s", 0.1))) <= 1 / 30, hits)
    hits, bed = bake_hits("uniform.wav", np.full(33, 0.6))
    ck("big_hits: uniform kicks still yield a hit", 1 <= len(hits) <= 3, hits)


def whoosh(seconds, seed=2):
    """A noise swell that peaks in its middle (a transition sound), under 6 kHz (AAC would strip white noise's top)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    X = np.fft.rfft(rng.normal(0, 0.3, n))
    X[np.fft.rfftfreq(n, 1 / SR) > 6000] = 0
    x = np.fft.irfft(X, n) * np.sin(np.pi * np.arange(n) / n) ** 2
    return np.stack([x, x], 1).astype(np.float32)


def beat_map(r, fps, layouts, beat_f, marks):
    """beat-map-selection.json (the S6a Send) with beats of beat_f frames each."""
    beats = [{"id": "b_%03d" % (i + 1), "start_f": i * beat_f, "end_f": (i + 1) * beat_f,
              "speech_anchor": {"text": "line %d" % (i + 1), "w0": 0, "w1": 0}, "layout": lay, "value": None,
              "scene": None, "broll": None, "transition": None} for i, lay in enumerate(layouts)]
    doc = {"schema": 1, "reel": r.name, "fps": fps, "words": "work/edit_map.cut.json", "beats": beats,
           "word_marks": marks, "proposed": {}, "notes": {}, "needs": "", "sent_at": "2026-11-05T10:00:00Z"}
    (r / "beat-map-selection.json").write_bytes(json.dumps(doc, indent=1).encode())


def cut_words(r, starts):
    words = [{"id": "w_%04d" % i, "word": "word%d" % i, "start": round(s, 3), "end": round(s + 0.2, 3)}
             for i, s in enumerate(starts)]
    (r / "work" / "edit_map.cut.json").write_bytes(json.dumps({"words": words}, indent=1).encode())


def case_prefill(scratch):
    import prefill_cues
    ws = workspace(scratch, "prefill")
    r = ws / "videos" / "reel-p"
    (r / "work").mkdir(parents=True)
    lib = ws / "editor" / "sound"
    for name, x in (("whoosh-soft.wav", whoosh(0.4)), ("swoosh-fast.wav", whoosh(0.5, 3)),
                    ("sweep-long.wav", whoosh(1.2, 4)), ("air-puff.wav", whoosh(0.3, 5)),
                    ("hit-low.wav", tone(0.4, 90, 0.7, 5)), ("tick.wav", tone(0.2, 1800)),
                    ("pop-a.wav", tone(0.15, 900)), ("chime.wav", tone(0.8, 1200, 0.4, 3))):
        M.write_wav(lib / name, x)
    starts = [0.3 + 0.25 * i for i in range(60)]
    starts[3], starts[14], starts[15], starts[23], starts[50], starts[54] = 1.05, 4.0, 4.03, 6.02, 12.8, 13.3
    starts = sorted(starts)
    cut_words(r, starts)
    w = {round(s, 2): i for i, s in enumerate(starts)}
    marks = [{"w": w[1.05], "mark": "num"}, {"w": w[4.0], "mark": "key"}, {"w": w[4.03], "mark": "emph"},
             {"w": w[6.02], "mark": "key"}, {"w": w[12.8], "mark": "emph"}, {"w": w[13.3], "mark": "cta"}]
    beat_map(r, 30, ["full", "split", "full", "pip", "full"], 90, marks)     # beats every 3 s, the closer at 12 s
    out = ws / "cues.json"
    before = sorted(f.relative_to(ws).as_posix() for f in ws.rglob("*"))
    p = script(ws, "prefill_cues.py", "--reel", "reel-p", "--out", out)
    ck("prefill: exits 0", p.returncode == 0 and out.is_file(), p.all[-400:])
    after = sorted(f.relative_to(ws).as_posix() for f in ws.rglob("*"))
    ck("prefill: ... and writes nothing but --out", sorted(set(after) - set(before)) == ["cues.json"],
       sorted(set(after) ^ set(before)))
    cues = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else []
    print("INFO prefill: %s" % [(c["time"], c["short"], c["candidates"]) for c in cues])
    seconds = {f.name: len(M.decode(f)) / SR for f in lib.iterdir()}

    def at(t):
        return [c for c in cues if abs(c["time"] - t) <= 0.05]

    def no_closer(cs):
        return not [c for c in cs if c["time"] >= 12.0]

    ck("prefill: a cue at each of the 3 layout changes before the closer (3, 6, 9 s)",
       all(len(at(t)) == 1 for t in (3.0, 6.0, 9.0)), [c["time"] for c in cues])
    ck("prefill: ... the change at 6 s and the marked word 0.02 s later are one cue, the word's",
       len(at(6.0)) == 1 and at(6.0)[0]["time"] == 6.02 and at(6.0)[0]["short"].startswith("hit"), at(6.0))
    ck("prefill: the two marks 0.03 s apart are one cue", len(at(4.015)) == 1, at(4.015))
    ck("prefill: the num mark has its hit", len(at(1.05)) == 1 and at(1.05)[0]["short"].startswith("hit"), at(1.05))
    ck("prefill: nothing at or after the closer's start (12 s)", no_closer(cues), [c["time"] for c in cues])
    ck("prefill: every cue has 2-3 candidates, all in the library",
       cues and all(2 <= len(c["candidates"]) <= 3 and set(c["candidates"]) <= set(seconds) for c in cues), cues)
    tr = [c for c in cues if c["short"].startswith("whoosh")]
    ck("prefill: transition candidates are 0.6 s or shorter (the 1.2 s sweep is never offered)",
       tr and all(seconds[f] <= 0.6 for c in tr for f in c["candidates"]), tr)
    ck("prefill: hit candidates are hit sounds by name", all(set(c["candidates"]) <= {"hit-low.wav", "tick.wav", "pop-a.wav"}
                                                             for c in cues if c["short"].startswith("hit")), cues)
    ck("prefill: no state field (they arrive undecided)", cues and all(set(c) == {"id", "beat", "short", "why", "time",
                                                                                   "candidates"} for c in cues), cues)
    sel = json.loads((r / "beat-map-selection.json").read_text(encoding="utf-8"))
    words = json.loads((r / "work" / "edit_map.cut.json").read_text(encoding="utf-8"))["words"]
    prefill_cues.CLOSER_SILENT = False
    try:
        flipped = prefill_cues.propose(sel, words, prefill_cues.library(lib))
    finally:
        prefill_cues.CLOSER_SILENT = True
    ck("prefill: reverse, with the closer rule off a cue lands in the closer and the check fails",
       not no_closer(flipped), [c["time"] for c in flipped])

    (r / "beat-map-selection.json").unlink()
    out.unlink()
    p = script(ws, "prefill_cues.py", "--reel", "reel-p", "--out", out)
    ck("prefill: no Beat Map Send is one plain line, exit 2, nothing written", p.returncode == 2 and not out.exists()
       and "Beat Map" in p.stdout and "Traceback" not in p.all, p.all[-300:])
    beat_map(r, 30, ["full", "split"], 90, [])
    p = script(ws, "prefill_cues.py", "--reel", "reel-p", "--out", out, "--sfx", ws / "no-sounds-here")
    ck("prefill: an empty library is one plain line, exit 2, nothing written", p.returncode == 2 and not out.exists()
       and "library" in p.stdout, p.all[-300:])


def riser(seconds=1.2, at=0.8):
    """A rising tone that tapers off 10 ms before a sharp burst centred exactly at `at`, then a short tail."""
    t = np.arange(int(seconds * SR)) / SR
    x = np.where(t < at - 0.01, (0.02 + 0.25 * t / at) * np.sin(2 * np.pi * 300 * t + 1.0)
                 * np.clip((at - 0.01 - t) / 0.01, 0, 1), 0.0)
    x += 0.9 * np.exp(-0.5 * ((t - at) / 0.003) ** 2) * np.cos(2 * np.pi * 2000 * (t - at))
    x += np.where(t > at + 0.01, 0.15 * np.sin(2 * np.pi * 150 * (t - at)) * np.exp(-(t - at) / 0.1), 0.0)
    return np.stack([x, x], 1).astype(np.float32)


def case_peak_offset(scratch):
    import measure_sfx
    ws = workspace(scratch, "peak_offset")
    r = reel_with_picture(scratch, ws, "reel-k", 8.0)
    (r / "sfx").mkdir()
    M.write_wav(r / "sfx" / "riser.wav", riser())
    ps = measure_sfx.measure(r / "sfx" / "riser.wav")["peak_s"]
    ck("peak_offset: the riser's peak_s is 0.80 +-0.005", ps is not None and abs(ps - 0.8) <= 0.005, ps)
    ps = ps or 0.8

    def bake(cues):
        selection(r, cues)
        p = script(ws, "bake.py", "--reel", "reel-k", "--video", r / "locked.mp4")
        sfx = np.abs(M.decode(r / "sound" / "sfx.wav")[:, 0]) if p.returncode == 0 else np.zeros(1)
        P = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
        return p, sfx, P

    p, sfx, P = bake([cue(1, 5.0, "riser.wav", 0.0, peak_s=ps), cue(2, 0.3, "riser.wav", 0.0, peak_s=ps)])
    ck("peak_offset: bake exits 0", p.returncode == 0, p.all[-400:])
    hit = (int(np.argmax(sfx[3 * SR:])) + 3 * SR) / SR
    ck("peak_offset: a cue at 5.0 s with peak_s 0.8 has its peak at 5.000 +-0.001 s", abs(hit - 5.0) <= 0.001, hit)
    ck("peak_offset: ... its file starts peak_s earlier", int(np.flatnonzero(sfx[3 * SR:] > 1e-6)[0]) + 3 * SR
       == int(round((5.0 - ps) * SR)))
    early = int(np.argmax(sfx[:2 * SR])) / SR
    ck("peak_offset: a cue at 0.3 s with peak_s 0.8 has its head trimmed and its peak at 0.3 s",
       abs(early - 0.3) <= 0.001 and sfx[0] > 1e-6, (early, float(sfx[0])))
    ck("peak_offset: placement.json clip rows carry peak_s", [c.get("peak_s") for c in P.get("cues", [])] == [ps, ps],
       P.get("cues"))
    p, sfx, P = bake([cue(1, 5.0, "riser.wav", 0.0)])
    first = int(np.flatnonzero(sfx > 1e-6)[0]) if sfx.any() else -1
    ck("peak_offset: the same cue without peak_s starts its file at 5.0 s (as before)", p.returncode == 0
       and first == int(round(5.0 * SR)) and abs(int(np.argmax(sfx)) / SR - 5.8) <= 0.001, (first, p.all[-300:]))


def case_sfx_peak_silence(scratch):
    import measure_sfx
    ws = workspace(scratch, "sfx_peak_silence")
    r = reel_with_picture(scratch, ws, "reel-ps", 6.0)
    (r / "sfx").mkdir()
    t = np.arange(SR) / SR
    x = np.zeros(SR)
    burst = (t >= 0.5) & (t < 0.503)
    x[burst] = 0.9 * np.exp(-0.5 * ((t[burst] - 0.501) / 0.0003) ** 2) * np.cos(2 * np.pi * 2000 * (t[burst] - 0.501))
    tail = (t >= 0.503) & (t < 0.506)
    x[tail] = 0.02 * np.sin(2 * np.pi * 2000 * (t[tail] - 0.503))
    f = r / "sfx" / "delayed.wav"
    M.write_wav(f, np.stack([x, x], 1).astype(np.float32))
    ck("sfx_peak_silence: the first half second is digital silence", not M.decode(f)[:SR // 2].any())
    ps = measure_sfx.measure(f)["peak_s"]
    ck("sfx_peak_silence: peak_s is 0.500 within 5 ms", ps is not None and abs(ps - 0.5) <= 0.005, ps)
    if ps is None:
        return
    selection(r, [cue(1, 3.0, f.name, 0.0, peak_s=ps)])
    p = script(ws, "bake.py", "--reel", "reel-ps", "--video", r / "locked.mp4")
    ck("sfx_peak_silence: bake exits 0", p.returncode == 0, p.all[-400:])
    if p.returncode == 0:
        hit = int(np.argmax(np.abs(M.decode(r / "sound" / "sfx.wav")[:, 0]))) / SR
        ck("sfx_peak_silence: baked peak lands on the cue within 1 ms", abs(hit - 3.0) <= 0.001, hit)
        detail = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8"))
        ck("sfx_peak_silence: placement keeps the measured peak offset", detail["cues"][0].get("peak_s") == ps, detail["cues"])


def edl_hash(r):
    """H-N2-6: sha256 of work/cuts.json + work/edit_map.cut.json (the speech cuts)."""
    h = hashlib.sha256()
    for f in ("cuts.json", "edit_map.cut.json"):
        h.update((r / "work" / f).read_bytes())
    return h.hexdigest()


def case_edl_hash(scratch):
    ws = workspace(scratch, "edl_hash")
    lib = ws / "editor" / "sound"
    for name, x in (("whoosh-soft.wav", whoosh(0.4)), ("swoosh-fast.wav", whoosh(0.5, 3)),
                    ("hit-low.wav", tone(0.4, 90, 0.7, 5)), ("tick.wav", tone(0.3, 1800)), ("pop-a.wav", tone(0.3, 900))):
        M.write_wav(lib / name, x)
    M.write_wav(lib / "beds" / "clicks.wav", click_track(30, 120, 0.21, 0, seed=8)[0] * np.float32(0.5))
    licensed(ws, "clicks.wav")
    r = reel_with_picture(scratch, ws, "reel-h", 10.0)
    (r / "work" / "cuts.json").write_bytes(json.dumps({"fps": 30, "cuts": [{"in_f": 0, "out_f": 300}]}, indent=1).encode())
    cut_words(r, [0.3 + 0.3 * i for i in range(30)])
    beat_map(r, 30, ["full", "split", "full", "pip"], 75, [{"w": 3, "mark": "num"}, {"w": 12, "mark": "emph"},
                                                          {"w": 27, "mark": "key"}])
    h0 = edl_hash(r)
    cues_json = ws / "cues.json"
    p = script(ws, "prefill_cues.py", "--reel", "reel-h", "--out", cues_json)
    ck("edl_hash: prefill exits 0", p.returncode == 0, p.all[-300:])
    p = script(ws, "new_board.py", "--reel", "reel-h", "--video", r / "locked.mp4", "--cues", cues_json)
    ck("edl_hash: new_board takes the pre-filled cues", p.returncode == 0, p.all[-400:])
    cfg = json.loads((r / "config.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
    rows = {x["file"]: x for x in cfg.get("library", [])}
    bed = next((b for b in cfg.get("beds", []) if b["file"] == "clicks.wav"), {})
    g = bed.get("grid")
    ck("edl_hash: config.json carries peak_s on library rows and the bed's grid", rows
       and all(isinstance(x.get("peak_s"), float) for x in rows.values()) and g and abs(g["bpm"] - 120) < 0.6,
       (list(rows.values())[:1], g))
    ck("edl_hash: the pre-filled cues arrive undecided (no state field)", cfg.get("cues")
       and not any("state" in c for c in cfg["cues"]), cfg.get("cues"))
    g = g or {"phase_s": 0.21, "period_s": 0.5}
    cues = [cue(i + 1, c["time"], c["candidates"][0], -6, peak_s=rows[c["candidates"][0]]["peak_s"])
            for i, c in enumerate(cfg.get("cues", []))]
    o = g["phase_s"] + max(0, round((bed.get("suggest_entry_s", 0) - g["phase_s"]) / g["period_s"])) * g["period_s"]
    selection(r, cues, bed_sel("clicks.wav", exit_s=10, offset_s=round(o, 4), beat_sync=True), {"music_request": None})
    p = script(ws, "mix.py", "--reel", "reel-h", "--voice", "free", "--video", r / "locked.mp4")
    ck("edl_hash: bake + mix with beat-sync on exits 0", p.returncode == 0, p.all[-600:])
    pb = json.loads((r / "sound" / "placement.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
    ck("edl_hash: the bed was beat-synced and every clip row carries peak_s", (pb.get("bed") or {}).get("beat")
       and all("peak_s" in c for c in pb.get("cues", [])) and len(pb.get("cues", [])) == len(cues), pb.get("bed"))
    ck("edl_hash: the speech cuts are byte-identical after prefill, board, bake and mix", edl_hash(r) == h0)
    doc = json.loads((r / "work" / "cuts.json").read_text(encoding="utf-8"))
    (r / "work" / "cuts.json").write_bytes(json.dumps(doc).encode())          # planted: a step rewrites cuts.json
    ck("edl_hash: reverse, a planted rewrite of cuts.json (same data, new bytes) is caught", edl_hash(r) != h0)


def case_carve(scratch):
    """Frozen DR-CARVE thresholds, real speech, old-path parity and deterministic bakes."""
    import ast
    import contextlib
    import types
    from unittest.mock import patch
    sys.path.insert(0, str(HERE))
    from carve_ab import fixture, measurements
    import carve
    import bake as BA
    import music_fit as MF
    ws = workspace(scratch, "carve")
    r = ws / "videos" / "carve"
    voice, bed, spans = fixture(PLUGIN_ROOT)
    (r / "beds").mkdir(parents=True)
    M.write_wav(r / "beds/bed.wav", bed)
    (r / "work/cut").mkdir(parents=True)
    M.write_json(r / "work/cut/tx-cut.json", {"words": [{"start": s["start_s"], "end": s["end_s"]} for s in spans]})
    M.write_wav(r / "voice.wav", voice)
    b = bed_sel("bed.wav", exit_s=15, fade_in_s=0, fade_out_s=0)
    b.pop("carve")  # exercise a genuinely old Send with no carve key
    plain, _ = MF.place(r, b, len(bed), 15, r / "voice.wav")
    carved, info = MF.place(r, dict(b, carve={"on": True, "strength": 0.8}), len(bed), 15, r / "voice.wav")
    default, default_info = MF.place(r, dict(b, carve={"on": True}), len(bed), 15, r / "voice.wav")
    ck("carve: missing strength uses 0.8", default_info["carve"]["strength"] == 0.8 and np.array_equal(default, carved))
    # Remove only the dip to get the same placed and levelled reference.
    with patch.object(MF, "keyframes", return_value=[]):
        reference, _ = MF.place(r, b, len(bed), 15, r / "voice.wav")
    ck("carve: bake honours on and records six bands", info["mode"] == "carve" and len(info["carve"]["bands"]) == 6, info)
    nums = measurements(voice, reference, carved, plain, info["carve"], SR)
    print("INFO carve measurements " + json.dumps(nums, sort_keys=True), flush=True)
    ck("carve: strongest selected band drops >= 6 dB", nums["strongest_drop_db"] >= 6, nums)
    ck("carve: every selected band drops >= 3 dB", min(nums["band_drop_db"]) >= 3, nums)
    ck("carve: outer bands stay within 1.5 dB", max(map(abs, nums["outer_drop_db"])) <= 1.5, nums)
    ck("carve: dip drops the same outer bands >= 4 dB", min(nums["dip_outer_drop_db"]) >= 4, nums)
    ck("carve: pauses return every band within 0.5 dB", max(map(abs, nums["pause_drop_db"])) <= 0.5, nums)
    # measured -1.69 dB at 0.8, H-CARVE-2: 0.8 was chosen by ear; the carve trades ~2 dB of voice-band clearance for a fuller bed
    ck("carve: 1-4 kHz voice/bed ratio >= dip - 2.0 dB", nums["ratio_advantage_db"] >= -2.0, nums)
    off, off_info = MF.place(r, dict(b, carve={"on": False, "strength": 0.8}), len(bed), 15, r / "voice.wav")
    ck("carve: missing key and explicit off are sample-identical", np.array_equal(plain, off) and off_info["mode"] == "dip")
    # Bake against 81858f4's actual pre-change module, not just a second new-code branch.
    old = types.ModuleType("music_fit_81858f4")
    old.__file__ = str(SCRIPTS / "music_fit.py")
    source = subprocess.check_output(["git", "show", "81858f4:plugins/editor-superengine/skills/reel-sound-pass/scripts/music_fit.py"],
                                     cwd=HERE.parents[1], text=True, encoding="utf-8")
    exec(compile(source, old.__file__, "exec"), old.__dict__)
    make_picture(r / "locked.mp4", voice, 15, scratch)
    library = ws / "editor/sound/beds"
    library.mkdir(parents=True)
    shutil.copyfile(r / "beds/bed.wav", library / "bed.wav")
    p = script(ws, "new_board.py", "--reel", "carve", "--video", r / "locked.mp4", "--bed", "bed.wav")
    ck("carve: new_board builds the default and preview profiles", p.returncode == 0, p.all[-600:])
    cfg = json.loads((r / "config.json").read_text(encoding="utf-8")) if p.returncode == 0 else {}
    ck("carve: new board defaults on at 0.8", cfg.get("bed_default", {}).get("carve") == {"on": True, "strength": 0.8})
    previews = (cfg.get("carve") or {}).get("profiles", {})
    ck("carve: config covers every strength slider stop", set(previews) == {"%.2f" % (s / 100) for s in range(25, 101, 5)}
       and previews.get("0.80", {}).get("bands") and previews.get("0.80", {}).get("points"), list(previews))
    selection(r, [], b)
    with patch.object(BA, "music_fit", old):
        BA.bake(r, r / "locked.mp4")
    before = hashlib.sha256((r / "sound/music.wav").read_bytes()).hexdigest()
    print("INFO carve 81858f4 music.wav sha256 " + before, flush=True)
    BA.bake(r, r / "locked.mp4")
    ck("carve: old selection bakes byte-identical to 81858f4", before == hashlib.sha256((r / "sound/music.wav").read_bytes()).hexdigest(), before)
    selection(r, [], dict(b, carve={"on": True, "strength": 0.8}))
    BA.bake(r, r / "locked.mp4")
    h = hashlib.sha256((r / "sound/music.wav").read_bytes()).hexdigest()
    BA.bake(r, r / "locked.mp4")
    ck("carve: two bakes give identical music.wav sha256", h == hashlib.sha256((r / "sound/music.wav").read_bytes()).hexdigest(), h)
    for name in ("silent", "missing", "no bands", "exception", "render exception"):
        stream = io.StringIO()
        if name == "silent":
            M.write_wav(r / "silent.wav", np.zeros_like(voice))
        vp = r / ("silent.wav" if name == "silent" else "voice.wav") if name != "missing" else None
        original = carve.analyse
        def analyse(*args, **kwargs):
            if name == "exception":
                raise RuntimeError("forced")
            return {"strength": 0.8, "bands": [], "points": []} if name == "no bands" else original(*args, **kwargs)
        def render_failure(*args, **kwargs):
            raise RuntimeError("forced render failure")
        renderer = render_failure if name == "render exception" else carve.render
        with patch.object(carve, "analyse", analyse), patch.object(carve, "render", renderer), contextlib.redirect_stdout(stream):
            fallback, detail = MF.place(r, dict(b, carve={"on": True}), len(bed), 15, vp)
        # The same gain reference for silent/missing voice uses the old anchor.
        with contextlib.redirect_stdout(io.StringIO()):
            expected, _ = MF.place(r, b, len(bed), 15, vp)
        ck("carve: %s falls back to the unchanged dip" % name,
           detail["mode"] == "dip" and np.array_equal(fallback, expected)
           and stream.getvalue().count("The music couldn't carve around the voice here, so it dips instead.") == 1,
           stream.getvalue())
        with patch.object(MF, "keyframes", return_value=[]), contextlib.redirect_stdout(io.StringIO()):
            ref, _ = MF.place(r, b, len(bed), 15, vp)
        inside = MF.envelope_db(detail["duck"]["keyframes"], np.arange(len(bed)) / SR) <= -4
        drop = 10 * np.log10(np.mean(ref[inside].astype(np.float64) ** 2) / np.mean(fallback[inside].astype(np.float64) ** 2))
        ck("carve: %s fallback dips >= 4 dB" % name, drop >= 4, float(drop))
    text = (SCRIPTS / "carve.py").read_text(encoding="utf-8")
    imports = {n.name.split(".")[0] for node in ast.walk(ast.parse(text))
               for n in (node.names if isinstance(node, ast.Import) else [])}
    froms = {node.module.split(".")[0] for node in ast.walk(ast.parse(text)) if isinstance(node, ast.ImportFrom)}
    ck("carve: numpy and stdlib only, no network or telemetry", (imports | froms) <= (sys.stdlib_module_names | {"numpy"})
       and not any(s in text.lower() for s in ("track", "posthog", "fetch", "http")))
    ck("carve: Apache source header and changes line", all(s in text for s in
       ("Apache", "HeyGen", "heygen-com/hyperframes", "v0.8.184", "d15a274c198cf18bc1df177cbe20df95392a8947",
        "packages/core/src/audioCarve.ts", "Changed by editor-superengine:")))


CASES = {"carve": case_carve, "free_master": case_free_master, "cost_ask": case_cost_ask, "pack": case_pack, "ingest_trim": case_ingest_trim,
         "room_tone": case_room_tone, "quiet_gate": case_quiet_gate, "bake_exact": case_bake_exact,
         "music_level": case_music_level, "music_seam": case_music_seam, "music_licence": case_music_licence,
         "music_absent": case_music_absent, "music_strongest": case_music_strongest, "beat_grid": case_beat_grid,
         "beat_grid_hard": case_beat_grid_hard, "beat_fit": case_beat_fit, "edl_hash": case_edl_hash,
         "prefill": case_prefill, "peak_offset": case_peak_offset,
         "beat_steady": case_beat_steady, "beat_drift": case_beat_drift, "beat_half_trap": case_beat_half_trap,
         "beat_real_bed": case_beat_real_bed,
         "big_hits": case_big_hits,
         "sfx_peak_silence": case_sfx_peak_silence,
         "safe-fetch": case_safe_fetch, "no-overwrite": case_no_overwrite}


def main():
    global M, MA, SR, SCRIPTS, CHECKS, PLUGIN_ROOT, room_tone, cost_ask
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch_dir", nargs="?", help="scratch folder (also accepted through --scratch)")
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
    scratch = Path(a.scratch or a.scratch_dir) if (a.scratch or a.scratch_dir) else Path(tempfile.mkdtemp(prefix="sound-pass-test-"))
    scratch.mkdir(parents=True, exist_ok=True)
    blocked = 0
    for name in a.case or sorted(CASES):
        t0 = time.time()
        try:
            CASES[name](scratch)
        except Blocked as e:
            blocked += 1
            print("BLOCKED %s: %s" % (name, e), flush=True)
        except Exception as e:  # a crash is a failed case, never a silent pass
            ck("%s: ran without crashing" % name, False, "%s: %s" % (type(e).__name__, e))
        print("INFO %s took %.1f s" % (name, time.time() - t0), flush=True)
    passed = sum(results)
    failed = len(results) - passed
    print("%d passed, %d failed, %d blocked" % (passed, failed, blocked))
    return 1 if failed else 77 if blocked else 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
