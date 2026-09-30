#!/usr/bin/env python3
"""hf-key-box.py - masked box for the Higgsfield API key on macOS. BETA, UNTESTED ON A REAL MAC.

The client pastes the ONE key string the console shows once ("KEY_ID:KEY_SECRET", open.higgsfield.ai > API keys)
into a hidden-answer osascript dialog. Surrounding spaces/line breaks are ignored; the shape must be a UUID-shaped
key id, ":", then 8-256 of A-Z a-z 0-9 . _ ~ + / = - (what hf_rest.py accepts).
It is saved to the login Keychain as ONE generic password: service "higgsfield-superengine", account "HF_API_KEY",
value "id:secret". hf_rest.py's _keychain_creds() reads it back. The key never reaches stdout, a file, or a
command line: it goes to `security -i` on stdin (so it does not show up in the process list).

  python3 hf-key-box.py              show the dialog (5-minute timeout)
  python3 hf-key-box.py --test       no dialog: reads HF_KEY_BOX_TEST_INPUT, saves under account HF_API_KEY_KEYBOXTEST
  python3 hf-key-box.py --selftest   offline checks with a fake `security`/`osascript` (runs on any OS)

Prints exactly one word: saved (exit 0) | cancelled (exit 1, also on timeout) | invalid (exit 2)
                         | error (exit 3: not macOS, or the Keychain did not keep the key)
"""
import io, os, re, subprocess, sys
from contextlib import redirect_stdout

SERVICE, ACCOUNT, TIMEOUT = "higgsfield-superengine", "HF_API_KEY", 300
KEY = re.compile(r"([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}):([A-Za-z0-9._~+/=-]{8,256})")
DIALOG = [
    'set r to display dialog "Paste your whole Higgsfield API key here (it looks like ID:SECRET).\\n\\n'
    'Get it at open.higgsfield.ai > API keys > Create API key. It is shown only once, so paste it here BEFORE you '
    'click Done there. It stays on this computer." default answer "" with hidden answer with title "Higgsfield API key" '
    'buttons {"Cancel", "Save"} default button "Save" cancel button "Cancel" giving up after %d' % TIMEOUT,
    'if gave up of r then return ""',
    'return text returned of r',
]


def parse(text):
    m = KEY.fullmatch((text or "").strip())
    return (m.group(1), m.group(2)) if m else None


def ask(run):
    """Show the dialog; returns the typed text, or None on Cancel / timeout."""
    args = ["osascript"]
    for line in DIALOG:
        args += ["-e", line]
    r = run(args, capture_output=True, text=True, timeout=TIMEOUT + 60)  # the dialog gives up after TIMEOUT itself
    return r.stdout.strip() or None if r.returncode == 0 else None


def save(kid, sec, account, run):
    """Add or update the Keychain item via stdin, then read it back; True only if the saved value matches."""
    run(["security", "-i"], input="add-generic-password -U -s %s -a %s -w %s:%s\n" % (SERVICE, account, kid, sec),
        capture_output=True, text=True, timeout=30)
    r = run(["security", "find-generic-password", "-s", SERVICE, "-a", account, "-w"],
            capture_output=True, text=True, timeout=30)
    return r.returncode == 0 and r.stdout.strip() == "%s:%s" % (kid, sec)


def main(argv, run=subprocess.run, platform=sys.platform, environ=os.environ):
    if platform != "darwin":
        print("error")
        return 3
    test = "--test" in argv
    text = environ.get("HF_KEY_BOX_TEST_INPUT") if test else ask(run)
    if text is None:
        print("cancelled")
        return 1
    key = parse(text)
    text = None
    if not key:
        print("invalid")
        return 2
    ok = save(key[0], key[1], ACCOUNT + ("_KEYBOXTEST" if test else ""), run)
    key = None
    print("saved" if ok else "error")
    return 0 if ok else 3


def selftest():
    fid, fsec = "0f0f0f0f-1e1e-2d2d-3c3c-4b4b4b4b4b4b", "FAKEsecret_for_selftest_0123456789abcdef"
    fails = []

    def check(name, cond):
        print(("PASS  " if cond else "FAIL  ") + name)
        cond or fails.append(name)

    check("parse: plain", parse(fid + ":" + fsec) == (fid, fsec))
    check("parse: surrounding spaces and line breaks", parse("\r\n  " + fid + ":" + fsec + " \n") == (fid, fsec))
    bad = ("", fid, fid + ":", "not-a-uuid:" + fsec, fid + ":short", fid + ":" + fsec + " x",
           fid + ":" + fsec + "\nmore", fid + " : " + fsec, fid + ":" + fsec + ":extra")
    check("parse rejects: empty, id only, no secret, non-UUID id, short secret, inner space, inner line break, "
          "spaced colon, second colon", all(parse(b) is None for b in bad))

    def fake(store, dialog=None, keep=True):
        calls = []

        def run(args, input=None, **kw):
            calls.append((list(args), input))
            out, code = "", 0
            if args[0] == "osascript":
                out, code = (dialog, 0) if dialog is not None else ("", 1)
            elif args[1:2] == ["-i"] and keep:
                m = re.search(r"-a (\S+) -w (\S+)\n", input)
                store[m.group(1)] = m.group(2)
            elif args[1:2] == ["find-generic-password"]:
                acct = args[args.index("-a") + 1]
                out, code = (store[acct] + "\n", 0) if acct in store else ("", 44)
            return subprocess.CompletedProcess(args, code, out, "")
        return run, calls

    def go(argv, run, env=None, platform="darwin"):
        o = io.StringIO()
        with redirect_stdout(o):
            code = main(argv, run, platform, env or {})
        return code, o.getvalue()

    store = {}
    run, calls = fake(store, dialog="  " + fid + ":" + fsec + "\n")
    code, out = go([], run)
    check("dialog -> saved, exit 0, output is exactly 'saved'", code == 0 and out == "saved\n")
    check("saved under service/account as one id:secret value", store.get(ACCOUNT) == fid + ":" + fsec)
    check("the secret is never on a command line (only on stdin)",
          all(fsec not in " ".join(a) for a, _ in calls) and any(fsec in (i or "") for _, i in calls))
    code, out = go([], fake({}, dialog=None)[0])
    check("Cancel / osascript error -> cancelled, exit 1", code == 1 and out == "cancelled\n")
    code, out = go([], fake({}, dialog="")[0])
    check("timeout (empty answer) -> cancelled, exit 1", code == 1 and out == "cancelled\n")
    code, out = go([], fake({}, dialog="garbage")[0])
    check("bad shape -> invalid, exit 2", code == 2 and out == "invalid\n")
    code, out = go([], fake({}, dialog=fid + ":" + fsec, keep=False)[0])
    check("Keychain did not keep it -> error, exit 3", code == 3 and out == "error\n")
    store = {}
    code, out = go(["--test"], fake(store)[0], {"HF_KEY_BOX_TEST_INPUT": fid + ":" + fsec})
    check("--test saves under the _KEYBOXTEST account only", code == 0 and list(store) == [ACCOUNT + "_KEYBOXTEST"])
    code, out = go([], fake({})[0], platform="win32")
    check("not macOS -> error, exit 3", code == 3 and out == "error\n")
    print("%d failed" % len(fails) if fails else "all passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main(sys.argv[1:]))
