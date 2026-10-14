#!/usr/bin/env python3
"""closeout_bookkeep.py ... the mechanical half of /session-closeout, in code.

Usage:
    python closeout_bookkeep.py <workspace> summary-path [--date YYYY-MM-DD]
    python closeout_bookkeep.py <workspace> entry-header <summary path> [--session-id ID]
    python closeout_bookkeep.py <workspace> insert-entry <entry file>
    python closeout_bookkeep.py <workspace> check [<summary path>] [--date YYYY-MM-DD]
    python closeout_bookkeep.py --selftest

summary-path   Prints the next free sessions/session-summary-MM-DD-YY[-N].md
               (none, then -1, -2, ...). Creates sessions/. Never overwrites.
entry-header   Prints the entry's **Summary:** and **Session log:** lines. The log
               path is printed only when the transcript is on disk; otherwise a
               fixed "could not determine" line. Refuses a summary that is not on disk.
insert-entry   Inserts the entry held in <entry file> into <workspace>/Checkpoint.md
               directly above the first line starting "## " (the newest entry), or at
               the end when there is none. Keeps the file's line endings (CRLF stays
               CRLF). Refuses when the entry's [[handle]] is already in the file.
check          Exits non-zero, naming each problem, unless: the newest Checkpoint entry
               carries a **Summary:** handle whose file is on disk (and equals <summary
               path> when given); handoff.md has the five load-bearing headings; and
               its "## Last session" section carries the date (default today).

The summary queue line is NOT written here: the summary-queue hook is its only writer.
Stdlib only, Python 3.8+.
"""
import argparse
import datetime
import glob
import os
import re
import sys
import tempfile

HEADINGS = ["## Last session", "## Session summary", "## P0 \u2014 Next Actions",
            "## Verify before building", "## Key files from last session"]
HANDLE_LINE = re.compile(r"^\*\*Summary:\*\*.*?\[\[([^\]|#]+)", re.M)


class Refuse(Exception):
    pass


def parse_date(s):
    if not s:
        return datetime.date.today()
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise Refuse("--date must be YYYY-MM-DD, got %r" % s)


def summary_path(ws, date):
    d = os.path.join(ws, "sessions")
    os.makedirs(d, exist_ok=True)
    base = "session-summary-%s" % date.strftime("%m-%d-%y")
    n = 0
    while True:
        name = base + ("" if n == 0 else "-%d" % n) + ".md"
        if not os.path.exists(os.path.join(d, name)):
            return "sessions/" + name
        n += 1


def find_transcript(session_id):
    if not session_id or not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        return None
    conf = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    hits = sorted(glob.glob(os.path.join(conf, "projects", "*", session_id + ".jsonl")))
    return hits[0] if hits else None


def entry_header(ws, rel, session_id):
    path = os.path.join(ws, rel)
    if not os.path.isfile(path):
        raise Refuse("summary file not found: %s. Write the summary first." % rel)
    stem = os.path.splitext(os.path.basename(rel))[0]
    log = find_transcript(session_id)
    if log:
        log_line = "**Session log:** `%s` (confirmed on disk)" % os.path.normpath(log)
    elif session_id:
        log_line = "**Session log:** could not determine (no transcript on disk for session %s)" % session_id
    else:
        log_line = "**Session log:** could not determine (no session id available)"
    return "**Summary:** [[%s]]\n%s" % (stem, log_line)


def _lines(b):
    return b.splitlines(keepends=True)


def insert_entry(ws, entry_file):
    cp = os.path.join(ws, "Checkpoint.md")
    if not os.path.isfile(cp):
        raise Refuse("Checkpoint.md not found in %s." % ws)
    if not os.path.isfile(entry_file):
        raise Refuse("entry file not found: %s" % entry_file)
    with open(entry_file, "rb") as fh:
        text = fh.read().decode("utf-8-sig")
    text = text.replace("\r\n", "\n").strip("\n").rstrip()
    if not text.startswith("## "):
        raise Refuse("the entry must start with its '## ' heading line.")
    with open(cp, "rb") as fh:
        orig = fh.read()
    cur = orig.decode("utf-8", "replace")
    m = HANDLE_LINE.search(text)
    if m:
        stem = m.group(1).strip()
        if re.search(r"\[\[" + re.escape(stem) + r"(\]\]|\|)", cur):
            raise Refuse("Checkpoint.md already has an entry for [[%s]]. Not inserted again." % stem)
    first = orig.find(b"\n")
    eol = b"\r\n" if first > 0 and orig[first - 1:first] == b"\r" else b"\n"
    block = text.replace("\n", eol.decode()).encode("utf-8")
    pos, at, where = 0, None, None
    for ln in _lines(orig):
        if ln.startswith(b"## "):
            at, where = pos, ln.rstrip(b"\r\n").decode("utf-8", "replace")
            break
        pos += len(ln)
    if at is not None:
        new = orig[:at] + block + eol + eol + orig[at:]
        msg = "inserted above: %s" % where
    else:
        lead = b"" if not orig or orig.endswith(b"\n") else eol
        new = orig + lead + (eol if orig else b"") + block + eol
        msg = "appended at the end (no '## ' entry yet)"
    _replace(cp, orig, new)
    return msg


def _replace(path, orig, new):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".Checkpoint.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(new)
        with open(path, "rb") as fh:
            if fh.read() != orig:
                raise Refuse("Checkpoint.md changed while inserting. Nothing written; run it again.")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _section(text, heading):
    out, on = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            if on:
                break
            on = ln.rstrip() == heading
            continue
        if on:
            out.append(ln)
    return "\n".join(out)


def check(ws, rel, date):
    probs = []
    cp = os.path.join(ws, "Checkpoint.md")
    if not os.path.isfile(cp):
        probs.append("Checkpoint.md is missing")
    else:
        with open(cp, "rb") as fh:
            text = fh.read().decode("utf-8", "replace").replace("\r\n", "\n")
        parts = re.split(r"(?m)^(?=## )", text)
        top = parts[1] if len(parts) > 1 else ""
        m = HANDLE_LINE.search(top)
        if not top:
            probs.append("Checkpoint.md has no entry")
        elif not m:
            probs.append("the newest Checkpoint entry has no **Summary:** [[handle]] line")
        else:
            stem = m.group(1).strip()
            if rel and stem != os.path.splitext(os.path.basename(rel))[0]:
                probs.append("the newest Checkpoint entry points at [[%s]], not %s" % (stem, rel))
            if not os.path.isfile(os.path.join(ws, "sessions", stem + ".md")):
                probs.append("the handle [[%s]] does not resolve: sessions/%s.md is not on disk" % (stem, stem))
    ho = os.path.join(ws, "handoff.md")
    if not os.path.isfile(ho):
        probs.append("handoff.md is missing")
    else:
        with open(ho, "rb") as fh:
            htext = fh.read().decode("utf-8", "replace").replace("\r\n", "\n")
        have = {ln.rstrip() for ln in htext.splitlines()}
        for h in HEADINGS:
            if h not in have:
                probs.append("handoff.md is missing the heading '%s'" % h)
        if "## Last session" in have and date.isoformat() not in _section(htext, "## Last session"):
            probs.append("handoff.md '## Last session' does not carry %s" % date.isoformat())
    return probs


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    if argv[:1] == ["--selftest"]:
        return selftest()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--date")
    common.add_argument("--session-id")
    ap = argparse.ArgumentParser(description="session-closeout bookkeeping")
    ap.add_argument("workspace")
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    sub.add_parser("summary-path", parents=[common])
    p = sub.add_parser("entry-header", parents=[common])
    p.add_argument("summary")
    p = sub.add_parser("insert-entry", parents=[common])
    p.add_argument("entry_file")
    p = sub.add_parser("check", parents=[common])
    p.add_argument("summary", nargs="?")
    a = ap.parse_args(argv)
    ws = os.path.abspath(a.workspace)
    try:
        if not os.path.isdir(ws):
            raise Refuse("workspace folder not found: %s" % ws)
        if a.cmd == "summary-path":
            print(summary_path(ws, parse_date(a.date)))
        elif a.cmd == "entry-header":
            print(entry_header(ws, a.summary, a.session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")))
        elif a.cmd == "insert-entry":
            print(insert_entry(ws, a.entry_file))
        else:
            probs = check(ws, a.summary, parse_date(a.date))
            if probs:
                print("CHECK FAILED:")
                for x in probs:
                    print("- " + x)
                return 1
            print("check ok")
    except Refuse as e:
        print("REFUSED: %s" % e)
        return 1
    return 0


def selftest():
    import shutil
    fails = []

    def ok(cond, label):
        print(("ok   " if cond else "FAIL ") + label)
        if not cond:
            fails.append(label)

    root = tempfile.mkdtemp(prefix="closeout-bookkeep-selftest ")
    try:
        ws = os.path.join(root, "work space")
        os.makedirs(ws)
        d = datetime.date(2026, 10, 14)
        # summary-path: none, -1, -2; creates sessions/
        r0 = summary_path(ws, d)
        ok(r0 == "sessions/session-summary-10-14-26.md" and os.path.isdir(os.path.join(ws, "sessions")),
           "summary-path first of day, sessions/ created")
        open(os.path.join(ws, r0), "w").close()
        r1 = summary_path(ws, d)
        ok(r1 == "sessions/session-summary-10-14-26-1.md", "summary-path second of day is -1")
        open(os.path.join(ws, r1), "w").close()
        ok(summary_path(ws, d) == "sessions/session-summary-10-14-26-2.md", "summary-path third of day is -2")

        # entry-header: log found, log missing, no id, summary missing
        conf = os.path.join(root, "conf")
        os.makedirs(os.path.join(conf, "projects", "C--x"))
        log = os.path.join(conf, "projects", "C--x", "abc-123.jsonl")
        open(log, "w").close()
        old = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = conf
        try:
            h = entry_header(ws, r1, "abc-123").splitlines()
            ok(h[0] == "**Summary:** [[session-summary-10-14-26-1]]", "entry-header Summary line carries the -1 suffix")
            ok(os.path.normpath(log) in h[1] and "confirmed on disk" in h[1], "entry-header Session log path when on disk")
            ok("could not determine" in entry_header(ws, r1, "zzz-999").splitlines()[1], "entry-header fallback when no transcript")
            ok("no session id" in entry_header(ws, r1, None).splitlines()[1], "entry-header fallback when no session id")
        finally:
            if old is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = old
        try:
            entry_header(ws, "sessions/session-summary-01-01-26.md", "abc-123")
            ok(False, "entry-header refuses a summary not on disk")
        except Refuse:
            ok(True, "entry-header refuses a summary not on disk")

        entry = os.path.join(root, "entry.md")
        with open(entry, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("## 2026-10-14 \u2014 New work\n**Duration:** ~1h\n**Summary:** [[session-summary-10-14-26-1]]\n\n### Completed\n- x\n\n---\n")
        cp = os.path.join(ws, "Checkpoint.md")

        # insert-entry: legacy CRLF file, no '---' in its preamble
        legacy = (b"# Checkpoint Log\r\n\r\nAppend-only. Newest entries at top.\r\n\r\n"
                  b"## 2026-10-13 \xe2\x80\x94 Old work\r\n**Summary:** [[session-summary-10-13-26]]\r\n\r\n---\r\n")
        with open(cp, "wb") as fh:
            fh.write(legacy)
        msg = insert_entry(ws, entry)
        b = open(cp, "rb").read()
        ok(b.count(b"\r") == b.count(b"\n"), "insert-entry keeps CRLF (CR == LF)")
        ok(b.startswith(b"# Checkpoint Log\r\n\r\nAppend-only. Newest entries at top.\r\n\r\n## 2026-10-14"),
           "insert-entry lands above the first '## ' in a legacy file with no '---' preamble")
        ok(b.endswith(legacy[legacy.index(b"## 2026-10-13"):]) and b"---\r\n\r\n## 2026-10-13" in b,
           "insert-entry keeps the old entry intact, one blank line between")
        ok("Old work" in msg, "insert-entry names the heading it inserted above")
        try:
            insert_entry(ws, entry)
            ok(False, "insert-entry refuses a duplicate handle")
        except Refuse:
            ok(open(cp, "rb").read() == b, "insert-entry refuses a duplicate handle and leaves the file unchanged")

        # insert-entry: fresh scaffold from the shipped template
        tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "super-setup", "templates", "Checkpoint.md")
        with open(tpl, "rb") as fh:
            t = fh.read()
        crlf = b"\r\n" in t
        with open(cp, "wb") as fh:
            fh.write(t)
        insert_entry(ws, entry)
        b = open(cp, "rb").read()
        i_new, i_old = b.find(b"## 2026-10-14"), b.find(b"## {{DATE}}")
        ok(0 < i_new < i_old, "insert-entry on a fresh template lands above the scaffold entry")
        ok((b.count(b"\r") == b.count(b"\n")) if crlf else (b.count(b"\r") == 0), "insert-entry keeps the template's line endings")
        ok(b.rstrip().endswith(b"-->"), "insert-entry leaves the template's closing comment last")

        # insert-entry: LF file stays LF; no '## ' appends; bad entry refused
        with open(cp, "wb") as fh:
            fh.write(b"# Checkpoint\n\nNo entries yet.\n")
        insert_entry(ws, entry)
        b = open(cp, "rb").read()
        ok(b"\r" not in b and b.startswith(b"# Checkpoint\n\nNo entries yet.\n\n## 2026-10-14"),
           "insert-entry appends to a file with no entry, LF kept")
        bad = os.path.join(root, "bad.md")
        with open(bad, "w") as fh:
            fh.write("**Summary:** [[x]]\n")
        try:
            insert_entry(ws, bad)
            ok(False, "insert-entry refuses an entry without a '## ' heading")
        except Refuse:
            ok(True, "insert-entry refuses an entry without a '## ' heading")
        try:
            insert_entry(ws, os.path.join(root, "no-such-entry.md"))
            ok(False, "insert-entry refuses a missing entry file")
        except Refuse as e:
            ok("entry file not found" in str(e), "insert-entry refuses a missing entry file")

        # check
        with open(cp, "wb") as fh:
            fh.write(legacy)
        insert_entry(ws, entry)
        ho = os.path.join(ws, "handoff.md")
        good = ("# Handoff\r\n\r\n## Last session\r\n2026-10-14 \u2014 New work\r\n\r\n## Session summary\r\n"
                "[[session-summary-10-14-26-1]]\r\n\r\n## P0 \u2014 Next Actions\r\n1. x\r\n\r\n"
                "## Verify before building\r\n(none)\r\n\r\n## Key files from last session\r\n(none)\r\n")
        with open(ho, "wb") as fh:
            fh.write(good.encode("utf-8"))
        ok(check(ws, r1, d) == [], "check passes on a complete closeout")
        ok(any("not session-summary-10-14-26-2" in p or "points at" in p for p in check(ws, "sessions/session-summary-10-14-26-2.md", d)),
           "check names a handle that is not this session's summary")
        ok(any("does not carry 2026-10-15" in p for p in check(ws, r1, datetime.date(2026, 10, 15))),
           "check names a stale '## Last session' date")
        with open(ho, "wb") as fh:
            fh.write(good.replace("## Verify before building", "## Verify").encode("utf-8"))
        ok(any("Verify before building" in p for p in check(ws, r1, d)), "check names a missing load-bearing heading")
        os.remove(os.path.join(ws, r1))
        ok(any("does not resolve" in p for p in check(ws, r1, d)), "check names a handle whose file is not on disk")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("selftest: %d failed" % len(fails) if fails else "selftest: all passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
