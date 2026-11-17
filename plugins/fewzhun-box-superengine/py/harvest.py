#!/usr/bin/env python3
"""Nightly harvest: new items from the configured sources become draft notes that a person approves.

    python3 harvest.py run                              the nightly job (stages drafts, sends the card)
    python3 harvest.py list [YYYY-MM-DD]                 list staged drafts and decisions (newest by default)
    python3 harvest.py decide YYYY-MM-DD N approve|reject --by NAME
                                                        record one decision; the first decision on a draft wins
    python3 harvest.py post YYYY-MM-DD                  send that night's undecided drafts to notify again
    python3 harvest.py drain                            move queued taps (taps.jsonl) into approvals.jsonl
All take --config PATH (default $FEWZHUN_BOX_CONFIG or /etc/fewzhun-box/brain.json).

Never touches the vault or git. Drafts land in <root>/staging/YYYY-MM-DD/ (0700); an approved draft is
copied unchanged (status: draft) to <root>/approved/YYYY-MM-DD/, the outbox. The client's own agent, or
promote.py, flips status to active when it commits the note to the vault.
"""
import argparse, datetime as dt, json, os, re, shutil, sys, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boxlib, claude_guard, collect, draft  # noqa: E402
import ledger as L                             # noqa: E402

DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")
JOB = "harvest"


def staging(cfg):
    return boxlib.p(cfg, "staging")


def taps_file(cfg):
    return cfg["harvest"].get("taps_file") or os.path.join(staging(cfg), "taps.jsonl")


def _index(cfg, date):
    with open(os.path.join(staging(cfg), date, "index.json"), encoding="utf-8") as f:
        return json.load(f)


def _decided(cfg, date):
    """{n: approval line} for a night (first line per draft wins)."""
    path = os.path.join(staging(cfg), "approvals.jsonl")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    a = json.loads(line)
                    if a.get("date") == date:
                        out.setdefault(int(a["n"]), a)
                except (ValueError, KeyError, TypeError):
                    continue
    return out


def list_drafts(cfg, date=None):
    """Read the index and decisions without draining taps or writing any files."""
    if date is None:
        st = staging(cfg)
        dates = sorted(name for name in os.listdir(st) if DATE_RX.fullmatch(name)
                       and os.path.isfile(os.path.join(st, name, "index.json"))) if os.path.isdir(st) else []
        if not dates:
            print("no staged harvests")
            return 0
        date = dates[-1]
    if not DATE_RX.fullmatch(date):
        sys.exit("date must be YYYY-MM-DD")
    try:
        idx = _index(cfg, date)
    except FileNotFoundError:
        sys.exit(f"no harvest on {date}")
    decisions = _decided(cfg, date)
    print(f"Harvest {date}")
    if not idx.get("drafts"):
        print("no staged drafts")
    for d in idx.get("drafts", []):
        decision = decisions.get(d["n"], {}).get("decision", "undecided")
        print(f"#{d['n']} {d['id']} | {d.get('title', d['id'])} | {decision}")
    for n, d in enumerate(idx.get("blocked", []), 1):
        print(f"blocked #{n} {d['id']} | {d.get('title', d['id'])} | blocked: {'; '.join(d.get('why', []))}")
    return 0


def _outbox(cfg, date, d):
    """Copy an approved draft, byte for byte, to <root>/approved/<date>/ after checking its sha256."""
    src = os.path.join(staging(cfg), date, d["file"])
    with open(src, "rb") as f:
        data = f.read()
    if hashlib.sha256(data).hexdigest() != d["sha256"]:
        raise RuntimeError(f"{d['file']}: sha256 does not match index.json; not copied")
    dest = boxlib.p(cfg, "approved", date)
    os.makedirs(dest, exist_ok=True)
    os.chmod(dest, 0o750)              # install.sh gives <root>/approved to the reader group
    tmp = os.path.join(dest, f".{d['file']}.tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o640)
    os.replace(tmp, os.path.join(dest, d["file"]))


def _record(cfg, date, d, decision, by, at):
    """Caller holds the approvals lock. -> (True, new line) or (False, the earlier line). First decision wins."""
    prev = _decided(cfg, date).get(d["n"])
    if prev:
        return False, prev
    if decision == "approve":
        _outbox(cfg, date, d)          # before the line: a recorded approval always has its outbox file
    line = {"date": date, "n": d["n"], "id": d["id"], "decision": decision, "by": by, "at": at}
    with open(os.path.join(staging(cfg), "approvals.jsonl"), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(line) + "\n")
    return True, line


def _approver(cfg, by):
    return isinstance(by, str) and by in (cfg["harvest"].get("approvers") or [])


def decide(cfg, date, n, decision, by):
    """Appends one decision line. Idempotent: a draft already decided is left as it is (exit 0)."""
    if not _approver(cfg, by):
        sys.exit(f"--by {by!r} is not in harvest.approvers")
    if not DATE_RX.fullmatch(date):
        sys.exit("date must be YYYY-MM-DD")
    if decision not in ("approve", "reject"):
        sys.exit("decision must be approve or reject")
    try:
        idx = _index(cfg, date)
    except FileNotFoundError:
        sys.exit(f"no harvest on {date}")
    d = next((x for x in idx["drafts"] if x["n"] == n), None)
    if d is None:
        sys.exit(f"no draft {n} on {date}")
    drain(cfg)                                   # queued taps first: they came earlier
    with boxlib.Lock(staging(cfg), ".approvals.lock"):
        new, line = _record(cfg, date, d, decision, by, boxlib.now(cfg).isoformat(timespec="seconds"))
    if new:
        msg = f"recorded: {decision} {date} #{n} {d['id']} by {by}"
    else:
        msg = f"already decided: {line['decision']} {date} #{n} {d['id']} by {line['by']} at {line['at']}; no change"
    print(msg)
    return msg


def drain(cfg):
    """Moves taps a bot queued in taps.jsonl ({date, n, decision, by, id?, at?} per line) into approvals.jsonl.
    `by` must be in harvest.approvers. Re-reading every tap is harmless: the first decision per draft wins."""
    path = taps_file(cfg)
    if not os.path.exists(path):
        return 0
    added = 0
    with boxlib.Lock(staging(cfg), ".approvals.lock"):
        with open(path, encoding="utf-8", errors="replace") as f:
            raws = f.readlines()
        for raw in raws:
            try:
                t = json.loads(raw)
                date, n = t["date"], int(t["n"])
                assert DATE_RX.fullmatch(date) and t["decision"] in ("approve", "reject")
                assert _approver(cfg, t.get("by")), "by not an approver"
                d = next(x for x in _index(cfg, date)["drafts"] if x["n"] == n)
                assert t.get("id") in (None, d["id"])
            except Exception as e:
                print(f"taps: skipped a line ({type(e).__name__}{': ' + str(e) if isinstance(e, AssertionError) else ''})",
                      file=sys.stderr)
                continue
            added += _record(cfg, date, d, t["decision"], t["by"], str(t.get("at") or boxlib.stamp()))[0]
    return added


def apply_approvals(cfg, led):
    """Applies new approvals.jsonl lines to the ledger: approve/reject marks the draft's refs."""
    drain(cfg)
    path = os.path.join(staging(cfg), "approvals.jsonl")
    if not os.path.exists(path):
        return 0
    with boxlib.Lock(staging(cfg), ".approvals.lock"):
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    n = 0
    for line in lines[led["approvals_read"]:]:
        try:
            a = json.loads(line)
            d = next(x for x in _index(cfg, a["date"])["drafts"] if x["n"] == int(a["n"]))
            if a.get("id") and a["id"] != d["id"]:
                raise ValueError("id mismatch")
            state = {"approve": "approved", "reject": "rejected"}[a["decision"]]
        except Exception as e:
            print(f"approvals: skipped a line ({type(e).__name__})", file=sys.stderr)
            continue
        for r in d["refs"]:
            L.mark(led, r, state, a["date"], d["id"])
        n += 1
    led["approvals_read"] = len(lines)
    return n


def header_text(date, blocked, dropped, n):
    lines = [f"Brain drafts for {date}: {n} to review."]
    if blocked:
        lines.append(f"Blocked by the threat scan (not staged): {blocked}")
    if dropped:
        lines.append(f"Dropped (failed checks or over the cap): {dropped}")
    return "\n".join(lines)


def send_card(cfg, date, drafts, header):
    """notify gets {"kind": "card", ...} on stdin: one entry per draft with the full text to show
    and the decide command to run. Returns True/False, or None when notify is not configured."""
    payload = {"kind": "card", "date": date, "header": header,
               "decide": f"fewzhun-box harvest decide {date} <n> approve|reject --by <name>",
               "drafts": [{k: d[k] for k in ("n", "id", "title", "type", "folder", "file", "sha256", "conflict",
                                             "collides")} | {"text": draft.block(d)} for d in drafts]}
    return boxlib.notify(cfg, payload)


def post(cfg, date):
    """Send the undecided drafts of one night to notify again."""
    if not DATE_RX.fullmatch(date):
        sys.exit("date must be YYYY-MM-DD")
    idx = _index(cfg, date)
    drain(cfg)
    done = _decided(cfg, date)
    todo = [d for d in idx["drafts"] if d["n"] not in done]
    if not todo:
        print(f"{date}: every draft is decided; nothing to post")
        return None
    ok = send_card(cfg, date, todo, header_text(date, 0, 0, len(todo)))
    print({None: "notify is not configured", True: f"posted {len(todo)} draft(s)", False: "notify failed"}[ok])
    return ok


def run(cfg, now=None):
    h = cfg["harvest"]
    if not h.get("enabled"):
        print("harvest disabled in config; nothing to do")
        return 0
    now = now or boxlib.now(cfg)
    date = now.astimezone(boxlib.tz(cfg)).strftime("%Y-%m-%d")
    st = staging(cfg)
    night = os.path.join(st, date)
    os.makedirs(st, mode=0o700, exist_ok=True)
    os.chmod(st, 0o700)
    res = {"drafts": [], "blocked": [], "dropped": []}
    with boxlib.Lock(st):
        path = os.path.join(st, "ledger.json")
        led = L.load(path)
        applied = apply_approvals(cfg, led)
        L.save(path, led)
        if os.path.exists(os.path.join(night, "index.json")):
            print(f"{date}: already harvested; nothing to do")
            return 0
        try:
            os.makedirs(night, mode=0o700, exist_ok=True)
            inp = os.path.join(night, "input.md")
            fed, marks, counts = collect.collect(cfg, led, now, inp)
            cost = None
            if fed:
                with open(inp, encoding="utf-8") as f:
                    text = f.read()
                claude_guard.wait_ready(cfg, JOB)                 # last check, then launch at once
                result = claude_guard.run_claude(cfg, draft.system_prompt(h), text)
                reply, cost = result.get("result") or "", result.get("total_cost_usd")
                boxlib.write_private(os.path.join(night, "reply.md"), reply)
                res = draft.process(reply, {r for _, r in fed}, draft.known_ids(cfg, night, led), h)
            draft.stage(night, res)
            text = draft.card(date, res, counts)
            boxlib.write_private(os.path.join(night, "card.md"), text)
            # Commit to the ledger only now: a failed night leaves every item for the next one.
            outcome = {}
            for state in ("dropped", "blocked", "drafted"):          # strongest outcome wins
                for d in res["drafts" if state == "drafted" else state]:
                    for r in d["refs"]:
                        outcome[r] = (state, d["id"])
            for _, r in fed:
                s, did = outcome.get(r, ("no-claim", ""))
                L.mark(led, r, s, date, did)
            led["marks"].update(marks)
            L.save(path, led)
        except Exception as e:
            # Remove the half night so a retry starts clean (no index.json = not harvested).
            shutil.rmtree(night, ignore_errors=True)
            boxlib.write_status(cfg, JOB, False, date=date, reason=f"{type(e).__name__}: {e}"[:500],
                                approvals_applied=applied)
            raise
    posted = None
    if res["drafts"]:
        posted = send_card(cfg, date, res["drafts"],
                           header_text(date, len(res["blocked"]), len(res["dropped"]), len(res["drafts"])))
    boxlib.write_status(cfg, JOB, True, date=date, fed=len(fed), counts=counts, staged=len(res["drafts"]),
                        blocked=len(res["blocked"]), dropped=len(res["dropped"]), cost_usd=cost,
                        approvals_applied=applied, card_posted=posted)
    print(text, end="")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("drain")
    sub.add_parser("list").add_argument("date", nargs="?")
    sub.add_parser("post").add_argument("date")
    d = sub.add_parser("decide")
    d.add_argument("date")
    d.add_argument("n", type=int)
    d.add_argument("decision", choices=["approve", "reject"])
    d.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    try:
        cfg = boxlib.load_config(a.config)
    except (OSError, ValueError, TypeError) as e:
        print(f"harvest config: {e}", file=sys.stderr)
        return 2
    if a.cmd == "list":
        return list_drafts(cfg, a.date)
    if a.cmd == "run":
        try:
            return run(cfg)
        except claude_guard.GuardRefused as e:
            print(f"harvest refused: {e}", file=sys.stderr)
            return e.exit_code
        except Exception as e:
            print(f"harvest failed: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
    if a.cmd == "post":
        return 0 if post(cfg, a.date) is not False else 1
    if a.cmd == "drain":
        print(f"drained: {drain(cfg)} new decision(s)")
        return 0
    decide(cfg, a.date, a.n, a.decision, a.by)
    return 0


if __name__ == "__main__":
    os.umask(0o077)
    sys.exit(main())
