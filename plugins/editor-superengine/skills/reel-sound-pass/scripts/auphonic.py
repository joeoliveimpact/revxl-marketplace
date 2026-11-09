# Changed from shorts-studio scripts/auphonic.py (MIT): voice track only, key from env or ~/.config/auphonic/api_key sent only in a header (urllib, no curl), plan/run with --yes and a paid-jobs ledger, room-tone padding, no mux.
"""auphonic.py: clean the voice track with Auphonic (noise removal, studio voice, leveling). It costs money.

  auphonic.py --setup-key
      makes ~/.config/auphonic/api_key (empty) and opens it in the computer's text editor for the client to paste
      their key into. The file is never read back to the screen.
  auphonic.py plan <voice.wav> --reel-dir <reel>
      prints the plan Claude shows the client: what runs, the expected cost, or that a saved result is reused free.
  auphonic.py run <voice.wav> --out <clean.wav> --reel-dir <reel> --yes
      runs it. Without --yes it refuses (exit 3) and calls nothing. Claude passes --yes only after the client said
      yes to the plan.

One Auphonic production per voice track (singletrack, never multitrack, never the summed mix). The production id is
written to <reel>/work/paid-jobs.json the moment it exists, and the download with its sha256 after, so a re-run
with the same track and settings reuses the result (no Auphonic call at all) or downloads a paid job again
instead of paying twice. The cleaned voice is lined up with the original to the millisecond; any gap that adds is
filled with the recording's own room tone. If it can't be lined up within 2 ms, nothing is written.

Key: AUPHONIC_API_KEY, else the file ~/.config/auphonic/api_key. It goes only into the request header: never on a
command line, in a log, an error, a report or the screen. No key: exit 2 (the free clean-up is used instead).
Exit codes: 0 done, 1 failed (nothing replaced), 2 no key, 3 no --yes.
"""
import argparse, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _media import SR, decode, write_wav, ffmpeg  # noqa: E402  (also puts skills/_shared on the path)
from _sync import load, env_db, lag_ms  # noqa: E402
import cost_ask, room_tone  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

API = "https://auphonic.com/api"
SERVICE = "Auphonic"
WHAT = "clean the voice track with Auphonic (noise removal, studio voice, leveling)"
SETTINGS = {"output_files": [{"format": "wav"}],
            "algorithms": {"leveler": True, "loudnesstarget": -14, "maxpeak": -1,
                           "denoise": True, "denoisemethod": "dynamic",
                           "filtering": True, "filtermethod": "studiovoice"}}
NO_KEY = "No Auphonic key is set up, so the free voice clean-up is used instead."
POLL_S, POLL_TRIES = 8, 90


class Fail(Exception):
    """A plain line for the client. Never holds the key."""


def key_file():
    return Path.home() / ".config" / "auphonic" / "api_key"


def read_key():
    k = os.environ.get("AUPHONIC_API_KEY", "").strip()
    if k:
        return k
    try:
        return key_file().read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None                      # http() follows redirects itself, so it decides which headers go along


_OPENER = urllib.request.build_opener(_NoRedirect)


def send(method, url, headers, body=None):
    """One request, redirects not followed (the test swaps this for a fake in-process): (status, Location, body)."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _OPENER.open(req, timeout=300) as r:
            return r.status, None, r.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            return e.code, e.headers["Location"], b""
        raise


def cross_host(headers):
    """Headers for a redirect to another host: never the key (downloads redirect to a storage host)."""
    return {k: v for k, v in headers.items() if k.lower() != "authorization"}


def http(method, url, headers, body=None):
    """The one network call. Follows up to 5 redirects; the Authorization header stays on same-host hops only."""
    for _ in range(6):
        status, loc, data = send(method, url, headers, body)
        if loc is None:
            return data
        nxt = urllib.parse.urljoin(url, loc)
        a, b = urllib.parse.urlsplit(url), urllib.parse.urlsplit(nxt)
        if (a.scheme, a.netloc.lower()) != (b.scheme, b.netloc.lower()):
            headers = cross_host(headers)
        if status == 303 or (status in (301, 302) and method == "POST"):
            method, body = "GET", None
            headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        url = nxt
    raise urllib.error.URLError("too many redirects")


def api(key, method, url, data=None, body=None, ctype=None):
    url = url if url.startswith("http") else API + url
    headers = {"Authorization": "bearer " + key}
    if data is not None:
        body, ctype = json.dumps(data).encode("utf-8"), "application/json"
    if ctype:
        headers["Content-Type"] = ctype
    tries = 3 if method == "GET" else 1      # a POST is never repeated: it could start a second production
    for n in range(tries):
        try:
            return http(method, url, headers, body)
        except urllib.error.HTTPError as e:
            why, refused = "HTTP %d" % e.code, True
        except (urllib.error.URLError, OSError) as e:
            why, refused = type(e).__name__, False
        if n + 1 < tries:
            time.sleep(3 * (n + 1))
    if refused:
        raise Fail("Auphonic refused the request (%s). A job already sent to Auphonic is picked up again later, "
                   "never paid for twice." % why)
    raise Fail("Auphonic didn't answer (%s). Check the internet connection and try again." % why)


def data(raw):
    return json.loads(raw)["data"]


def ledger(reel_dir):
    return Path(reel_dir) / "work" / "paid-jobs.json"


def seconds(path):
    return len(decode(path)) / SR


def multipart(path, filename):
    """multipart/form-data body with one file field, input_file."""
    b = "editorse" + uuid.uuid4().hex
    head = ('--%s\r\nContent-Disposition: form-data; name="input_file"; filename="%s"\r\n'
            'Content-Type: audio/wav\r\n\r\n' % (b, filename)).encode("ascii")
    return head + Path(path).read_bytes() + ("\r\n--%s--\r\n" % b).encode("ascii"), "multipart/form-data; boundary=" + b


# ------------------------------------------------------------------ subcommands
def setup_key():
    p = key_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(b"")
    if os.name != "nt":
        os.chmod(p, 0o600)
    if sys.platform == "win32":
        os.startfile(str(p))
    elif sys.platform == "darwin":
        subprocess.run(["open", "-t", str(p)])
    print("Paste your Auphonic key into the file that just opened, save it, close it, then say done.")
    return 0


def plan(a):
    key = cost_ask.job_key(SERVICE, a.voice, SETTINGS)
    if cost_ask.find_reusable(ledger(a.reel_dir), key):
        print("This exact voice track was already cleaned by Auphonic and the result is saved, "
              "so it will be reused at no charge.")
        return 0
    k = read_key()
    if not k:
        print(NO_KEY)
        return 2
    pending = cost_ask.find_pending(ledger(a.reel_dir), key)
    if pending and pending.get("status") != "failed":
        print("This exact voice track was already sent to Auphonic and paid for; the result will be downloaded "
              "again at no new charge.")
        return 0
    cost = "about %.1f minutes of your Auphonic time" % (seconds(a.voice) / 60)
    try:
        left = data(api(k, "GET", "/user.json")).get("credits")
        if left is not None:
            cost += " (your account has about %.1f hours left)" % float(left)
    except (Fail, ValueError, KeyError, TypeError):
        pass
    print(cost_ask.plan_text(SERVICE, WHAT, cost))
    return 0


def create(k, voice, led, key, reel_dir):
    """Make the production; its id goes in the ledger before anything else happens."""
    prod = data(api(k, "POST", "/productions.json", {"metadata": {"title": "voice"}, **SETTINGS}))
    cost_ask.record(led, key, service=SERVICE, what=WHAT, input=str(Path(voice).resolve()), job_id=prod["uuid"],
                    expected_cost="%.1f minutes of Auphonic time" % (seconds(voice) / 60),
                    yes_at=cost_ask.now(), status="created")
    return cost_ask.load(led)["jobs"][key]


def finish(k, e, voice, led, key, reel_dir):
    """Upload + start (when not started yet), wait, download. Returns the downloaded file."""
    job = e["job_id"]
    if e.get("status") == "created":
        up = Path(reel_dir) / "work" / "auphonic-upload.wav"
        up.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(voice), "-c:a", "pcm_s24le", str(up)], check=True)
        body, ctype = multipart(up, "voice.wav")
        api(k, "POST", "/production/%s/upload.json" % job, body=body, ctype=ctype)
        up.unlink()
        api(k, "POST", "/production/%s/start.json" % job, {})
        cost_ask.record(led, key, status="started")
    print("Auphonic is working on it (usually under 2 minutes)...")
    for _ in range(POLL_TRIES):
        d = data(api(k, "GET", "/production/%s.json" % job))
        if d.get("status") == 3:
            break
        if d.get("status") in (2, 9, 11, 13):
            cost_ask.record(led, key, status="failed")
            raise Fail("Auphonic couldn't finish it (%s)." % (d.get("status_string") or "error"))
        time.sleep(POLL_S)
    else:
        raise Fail("Auphonic is taking too long. Try again later; the paid job will be picked up, not paid again.")
    out = Path(reel_dir) / "work" / ("auphonic-%s.wav" % key[:12])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_bytes(api(k, "GET", d["output_files"][0]["download_url"]))
    os.replace(tmp, out)
    cost_ask.record(led, key, status="done", result=str(out.resolve()), result_sha256=cost_ask.file_sha256(out))
    return out


def align(voice, clean, out):
    """Line the cleaned voice up with the original; pad with room tone, never zeros. True when it lines up."""
    r = env_db(load(voice))
    lag, _ = lag_ms(r, env_db(load(clean)), 15000)
    n = len(decode(voice))
    x = decode(clean)
    shift = int(round(lag * SR / 1000))
    x = x[shift:] if shift >= 0 else np.vstack([room_tone.fill(x, -shift), x])
    x = x[:n] if len(x) >= n else np.vstack([x, room_tone.fill(x, n - len(x))])
    out = Path(out)
    tmp = out.with_name(out.stem + ".aligning.wav")
    write_wav(tmp, x)
    resid, _ = lag_ms(r, env_db(load(tmp)), 50)
    if abs(resid) > 2:
        tmp.unlink()
        print("The cleaned voice did not line up with the original (off by %d ms), so nothing was replaced." % resid)
        return False
    os.replace(tmp, out)
    print("Clean voice ready (lined up: moved %d ms, %d ms left over)." % (lag, resid))
    return True


def run(a):
    refused = cost_ask.refuse_without_yes(a.yes)
    if refused:
        return refused
    led = ledger(a.reel_dir)
    key = cost_ask.job_key(SERVICE, a.voice, SETTINGS)
    e = cost_ask.find_reusable(led, key)
    if e:
        print("Reusing the saved Auphonic result for this exact voice track (no charge).")
        src = Path(e["result"])
    else:
        k = read_key()
        if not k:
            print(NO_KEY)
            return 2
        e = cost_ask.find_pending(led, key)
        if not e or e.get("status") == "failed":    # a production Auphonic gave up on is made again
            e = create(k, a.voice, led, key, a.reel_dir)
        src = finish(k, e, a.voice, led, key, a.reel_dir)
    return 0 if align(a.voice, src, a.out) else 1


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Clean the voice track with Auphonic (costs money; plan first).")
    ap.add_argument("--setup-key", action="store_true", help="make the key file and open it for the client")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan")
    p.add_argument("voice")
    p.add_argument("--reel-dir", required=True)
    r = sub.add_parser("run")
    r.add_argument("voice")
    r.add_argument("--out", required=True)
    r.add_argument("--reel-dir", required=True)
    r.add_argument("--yes", action="store_true", help="the client said yes to the plan")
    a = ap.parse_args(argv)
    if a.setup_key:
        return setup_key()
    if a.cmd is None:
        ap.print_help()
        return 2
    try:
        return plan(a) if a.cmd == "plan" else run(a)
    except Fail as e:
        print(str(e))
        return 1


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main, detail=False))
