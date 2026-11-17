#!/usr/bin/env python3
"""Promote approved drafts into the client's own git clone of the vault. Dry run unless --apply.

    python3 promote.py --repo PATH [--staging DIR] [--ledger FILE] [--apply] [--ids ID[,DATE/ID...] --by NAME]

Reads (never writes) the staging dir: approvals.jsonl plus each night's index.json and NN-<id>.md drafts.
The same layout the harvest writes, so an older staging dir of that shape works read-only too.
For each approved draft not yet promoted:
  - sets the harvest.promote.on_promote fields (default status: active, last_verified: today);
  - picks the folder from harvest.schema.folders by type;
  - runs the note check (with the promoted status), the threat scan and the secret-path gate;
  - writes <repo>/<folder>/<id>.md, never over an existing file.
--ids promotes drafts approved outside approvals.jsonl; --by must be in harvest.approvers and is recorded
in the promoted ledger (default <root>/status/promoted.jsonl), never in the staging dir.
With --apply: `git add` + `git commit` of exactly those files with the repo's own identity, hooks off.
Never pushes, never touches remotes. A re-run is a no-op.
Exit: 0 = nothing blocked, 1 = something blocked or failed, 2 = refused input.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boxlib, notecheck, scan  # noqa: E402


def read_jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def nights(st):
    """{date: index.json} for every night in the staging dir."""
    out = {}
    for name in sorted(os.listdir(st)) if os.path.isdir(st) else []:
        idx = os.path.join(st, name, "index.json")
        if len(name) == 10 and os.path.isfile(idx):
            try:
                with open(idx, encoding="utf-8") as f:
                    out[name] = json.load(f)
            except ValueError:
                continue
    return out


def line_threats(text, h):
    """Threat-scan reasons with line numbers, plus the secret-path gate's."""
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        out += [f"line {n}: {r}" for r in scan.scan(line, h["known_hosts"])]
    whole = scan.scan(text, h["known_hosts"])
    if whole and not out:
        out += [f"{r}" for r in whole]
    return out + scan.secret_reasons(text, h["secret_patterns"])


def git(repo, *args, hooks=None):
    pre = ["git", "-c", f"safe.directory={os.path.abspath(repo)}", "-C", repo]
    pre += ["-c", f"core.hooksPath={hooks}"] if hooks else []
    env = boxlib.child_env(HOME=os.environ.get("HOME") or os.path.expanduser("~"), GIT_TERMINAL_PROMPT="0")
    if os.name == "posix":
        import pwd
        owner = pwd.getpwuid(os.stat(repo).st_uid)
        env["HOME"] = owner.pw_dir
        if os.geteuid() == 0:
            pre = ["runuser", "-u", owner.pw_name, "--"] + pre
        elif os.geteuid() != owner.pw_uid:
            raise PermissionError("git must run as the repo owner")
    if os.name == "nt":
        env["PATH"] = os.environ.get("PATH", "")
    return subprocess.run(pre + list(args), capture_output=True, text=True, timeout=120, env=env)


def chown_repo(repo, path):
    """Root-created repo files and directories belong to the clone's owner."""
    if os.name == "posix" and os.geteuid() == 0:
        if os.path.commonpath([os.path.realpath(repo), os.path.realpath(path)]) == os.path.realpath(repo):
            owner = os.stat(repo)
            os.chown(path, owner.st_uid, owner.st_gid)


def makedirs(repo, path):
    missing, parent = [], path
    while not os.path.exists(parent):
        missing.append(parent)
        parent = os.path.dirname(parent)
    os.makedirs(path, exist_ok=True)
    for parent in missing:
        chown_repo(repo, parent)


def candidates(cfg, st, idxs, ids, by, report):
    """[(date, entry, by, via)] approved drafts, oldest first."""
    approvers = set(cfg["harvest"].get("approvers") or [])
    first = {}
    for a in read_jsonl(os.path.join(st, "approvals.jsonl")):
        try:
            first.setdefault((a["date"], int(a["n"])), a)
        except (KeyError, TypeError, ValueError):
            continue
    out = {}
    for (date, n), a in sorted(first.items()):
        if a.get("decision") != "approve":
            continue
        e = next((d for d in idxs.get(date, {}).get("drafts", []) if d.get("n") == n), None)
        label = f"{date} #{n} {a.get('id', '?')}"
        if e is None or (a.get("id") and a["id"] != e.get("id")):
            report.append(("skipped", label, "no matching draft in index.json"))
        elif a.get("by") not in approvers:
            report.append(("skipped", label, f"approver {a.get('by')!r} not in harvest.approvers"))
        else:
            out[(date, n)] = (date, e, a["by"], "approvals")
    for spec in ids:
        date, _, did = spec.rpartition("/")
        hits = [(d, e) for d, ix in idxs.items() if not date or d == date
                for e in ix.get("drafts", []) if e.get("id") == did]
        if not hits:
            report.append(("skipped", spec, "no staged draft with that id"))
        elif len(hits) > 1:
            report.append(("skipped", spec, f"in more than one night ({', '.join(d for d, _ in hits)}); use DATE/ID"))
        else:
            d, e = hits[0]
            prev = first.get((d, e["n"]))
            if prev and prev.get("decision") == "reject":
                report.append(("skipped", f"{d} #{e['n']} {did}", f"rejected by {prev.get('by')}"))
            elif (d, e["n"]) not in out:
                out[(d, e["n"])] = (d, e, by, "ids")
    return [out[k] for k in sorted(out)]


def prepare(cfg, st, repo, date, e, today):
    """-> (relative path, new text) or raises ValueError(reason)."""
    h = cfg["harvest"]
    fname = e.get("file") or f"{int(e['n']):02d}-{e['id']}.md"
    with open(os.path.join(st, date, fname), "rb") as f:
        raw = f.read()
    if e.get("sha256") and hashlib.sha256(raw).hexdigest() != e["sha256"]:
        raise ValueError("sha256 does not match index.json")
    text = raw.decode("utf-8").replace("\r\n", "\n")
    on = h["promote"].get("on_promote") or {}
    for k, v in on.items():
        text = notecheck.set_field(text, k, str(v).replace("{today}", today))
    fm, _ = notecheck.split_note(text)
    folder = h["schema"]["folders"].get((fm or {}).get("type"))
    if not folder:
        raise ValueError(f"no folder for type {(fm or {}).get('type')!r} in harvest.schema.folders")
    why = notecheck.check(text, e["id"], notecheck.ref_rx(None), str(on.get("status", "active")), h["schema"])
    why += line_threats(text, h)
    if why:
        raise ValueError("; ".join(why))
    rel = f"{folder}/{e['id']}.md"
    target = os.path.realpath(os.path.join(repo, rel))
    if not target.startswith(os.path.realpath(repo) + os.sep):
        raise ValueError("target path leaves the repo")
    return rel, text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--staging")
    ap.add_argument("--repo")
    ap.add_argument("--ledger")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ids", default="")
    ap.add_argument("--by")
    a = ap.parse_args(argv)
    cfg = boxlib.load_config(a.config)
    st = a.staging or boxlib.p(cfg, "staging")
    repo = a.repo or cfg["harvest"]["promote"].get("repo")
    ledger = a.ledger or boxlib.p(cfg, "status", "promoted.jsonl")
    boxlib.refuse_symlink(ledger)
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    if not repo or not os.path.isdir(repo):
        print("refused: --repo must be an existing git clone of the vault", file=sys.stderr)
        return 2
    if ids and a.by not in (cfg["harvest"].get("approvers") or []):
        print(f"refused: --by {a.by!r} is not in harvest.approvers", file=sys.stderr)
        return 2
    if a.apply:
        if git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
            print("refused: --repo is not a git work tree", file=sys.stderr)
            return 2
        if not (git(repo, "config", "user.name").stdout.strip() and git(repo, "config", "user.email").stdout.strip()):
            print("refused: the repo has no git identity (user.name / user.email); set it in the repo", file=sys.stderr)
            return 2
    done = {f"{x.get('date')}/{x.get('id')}" for x in read_jsonl(ledger)}
    today = boxlib.now(cfg).date().isoformat()
    report, todo = [], []
    for date, e, by, via in candidates(cfg, st, nights(st), ids, a.by, report):
        label = f"{date} #{e['n']} {e['id']}"
        if f"{date}/{e['id']}" in done:
            report.append(("skipped", label, "already promoted"))
            continue
        try:
            rel, text = prepare(cfg, st, repo, date, e, today)
        except (ValueError, OSError, UnicodeDecodeError) as ex:
            report.append(("blocked", label, str(ex)[:600]))
            continue
        target = os.path.join(repo, rel)
        if os.path.exists(target):
            with open(target, encoding="utf-8", errors="replace") as f:
                same = f.read().replace("\r\n", "\n") == text
            report.append(("skipped", label, "already in the repo, identical") if same
                          else ("blocked", label, f"{rel} already exists; never overwritten"))
            continue
        todo.append((date, e, by, via, rel, text, label))
    rc = 1 if any(k == "blocked" for k, _, _ in report) else 0
    if todo and not a.apply:
        report += [("would promote", t[6], f"-> {t[4]} (by {t[2]})") for t in todo]
    elif todo:
        written = []
        try:
            for date, e, by, via, rel, text, label in todo:
                target = os.path.join(repo, rel)
                makedirs(repo, os.path.dirname(target))
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)   # never overwrite, even in a race
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                written.append(rel)
                chown_repo(repo, target)
            with tempfile.TemporaryDirectory(dir=repo) as nohooks:
                if os.name == "posix" and os.geteuid() == 0:
                    owner = os.stat(repo)
                    os.chown(nohooks, owner.st_uid, owner.st_gid)
                r = git(repo, "add", "--", *written, hooks=nohooks)
                if r.returncode == 0:
                    r = git(repo, "commit", "-q", "-m", f"fewzhun-box: promote {len(written)} approved note(s)",
                            "--", *written, hooks=nohooks)
            if r.returncode != 0:
                raise RuntimeError(f"git failed: {(r.stderr or r.stdout).strip()[:300]}")
        except Exception as ex:
            git(repo, "reset", "-q", "--", *written)
            for rel in written:
                os.remove(os.path.join(repo, rel))
            report.append(("failed", "commit", f"{ex}; nothing was committed and the new files were removed"))
            rc = 1
            todo = []
        if todo:
            sha = git(repo, "rev-parse", "HEAD").stdout.strip()
            makedirs(repo, os.path.dirname(os.path.abspath(ledger)))
            boxlib.refuse_symlink(ledger)
            previous = ""
            if os.path.exists(ledger):
                fd = os.open(ledger, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                with os.fdopen(fd, encoding="utf-8") as f:
                    previous = f.read()
            lines = []
            for date, e, by, via, rel, text, label in todo:
                lines.append(json.dumps({"date": date, "n": e["n"], "id": e["id"], "path": rel, "by": by, "via": via,
                                         "commit": sha, "at": boxlib.stamp()}) + "\n")
                report.append(("promoted", label, f"-> {rel}"))
            boxlib.write_atomic(ledger, previous + "".join(lines))
            chown_repo(repo, ledger)
    if not report:
        report.append(("skipped", "-", "nothing approved to promote"))
    for kind, label, why in report:
        print(f"{kind}: {label} ({why})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
