#!/usr/bin/env python3
"""Nightly graph job: one graphify graph per spoke, under the login guard.

    python3 graph_job.py [--config PATH] [--spoke NAME]

For each spoke in config.spokes (skip one with "graph": false):
  1. Stage only Markdown from <root>/spokes/<spoke> (sync's active copies), preserving relative paths.
     Empty spokes skip successfully and keep their old graph. Run graphify extract <staged notes>
     --backend <graph.backend> --out /var/lib/fewzhun-box-graph/<spoke>
     then graphify cluster-only <work> --no-label (extract writes graph.json only; cluster-only writes
     graph.html; --no-label = no second round of model calls).
     The work dir is persistent: graphify keeps its semantic cache and manifest in <work>/graphify-out/,
     so a rerun over unchanged notes makes no model calls (status records llm_calls per spoke).
  2. graphify's `claude` is claude_guard.py's shim (first on PATH): every model call passes the guard and
     runs with no tools / no MCP / the configured model. The whole run is capped at claude.max_run_minutes
     and its process group is killed on timeout.
  3. The new graph.json must parse and hold >= graph.min_nodes nodes (never empty), and graph.html must
     exist. Only then are both copied to a temp dir beside <root>/graphs/<spoke>/ and moved in with
     os.replace (atomic per file). On any failure the published graph stays as it was and the work dir's
     graph/manifest are put back, so the next run starts from the last good graph (the cache is kept).
  4. <root>/status/graph.json records every spoke; any failed spoke exits non-zero (alert unit fires).
"""
import argparse, json, os, re, shutil, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boxlib, claude_guard  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_ROOT = "/var/lib/fewzhun-box-graph"
SHIM_DIR = os.path.join(HERE, "shim")
STATE_FILES = ("graph.json", "manifest.json", ".graphify_analysis.json", ".graphify_labels.json",
               ".graphify_labels.json.sig", "graph.html", "GRAPH_REPORT.md")
PUBLISH = ("graph.json", "graph.html")


def error_line(output):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    errors = [line for line in lines if re.search(r"guard:|error|failed|refused|exception", line, re.I)]
    return (errors or lines or ["no error output"])[-1]


def markdown_files(src):
    """Spokes contain sync's active notes plus engine files; only notes reach graphify."""
    notes = []
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith(".") and not os.path.islink(os.path.join(base, d))]
        for name in files:
            if not name.startswith(".") and name.lower().endswith(".md") and not os.path.islink(os.path.join(base, name)):
                notes.append(os.path.relpath(os.path.join(base, name), src))
    return notes


def graphify_cmd(cfg):
    g = cfg["graph"].get("graphify")
    if g:
        return list(g) if isinstance(g, list) else [g]
    return [os.path.join(cfg["code_root"], "venv", "bin", "graphify")]


def graphify_env(cfg, shim_dir, home, calls):
    """Explicit env: shim first on PATH, no API keys, no GRAPHIFY_OUT, the job's config for the shim."""
    timeout_s = int(float(cfg["claude"]["max_run_minutes"]) * 60)
    env = boxlib.child_env(HOME=home, FEWZHUN_BOX_CONFIG=cfg["_path"], FEWZHUN_BOX_CALLS=calls,
                           GRAPHIFY_API_TIMEOUT=str(timeout_s), PYTHONDONTWRITEBYTECODE="1")
    env["PATH"] = shim_dir + os.pathsep + env["PATH"]
    if os.name == "nt":
        env["PATHEXT"] = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")
        env["USERPROFILE"] = home
    return env


def _node_count(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        nodes = data.get("nodes")
        return len(nodes) if isinstance(nodes, list) else None
    except (OSError, ValueError, AttributeError):
        return None


def _snapshot(out, keep):
    shutil.rmtree(keep, ignore_errors=True)
    os.makedirs(keep)
    for name in STATE_FILES:
        if os.path.exists(os.path.join(out, name)):
            shutil.copy2(os.path.join(out, name), os.path.join(keep, name))


def _restore(out, keep):
    for name in STATE_FILES:
        src, dst = os.path.join(keep, name), os.path.join(out, name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        elif os.path.exists(dst):
            os.remove(dst)


def publish(cfg, spoke, out):
    """Copy graph.json + graph.html beside the target, then os.replace each into graphs/<spoke>/."""
    graphs = boxlib.p(cfg, "graphs")
    dest = os.path.join(graphs, spoke)
    os.makedirs(dest, mode=0o750, exist_ok=True)
    if os.name == "posix":
        os.chown(dest, -1, os.stat(graphs).st_gid)
    tmp = tempfile.mkdtemp(prefix=f".tmp-{spoke}-", dir=graphs)
    try:
        for name in PUBLISH:
            shutil.copyfile(os.path.join(out, name), os.path.join(tmp, name))
            os.chmod(os.path.join(tmp, name), 0o640)
            if os.name == "posix":
                os.chown(os.path.join(tmp, name), -1, os.stat(graphs).st_gid)
        for name in PUBLISH:
            os.replace(os.path.join(tmp, name), os.path.join(dest, name))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_spoke(cfg, spoke, deadline):
    src = boxlib.p(cfg, "spokes", spoke)
    work = os.path.join(WORK_ROOT, spoke)
    out = os.path.join(work, "graphify-out")
    keep = os.path.join(work, ".last-good")
    home = os.path.join(work, ".home")
    calls = os.path.join(work, ".calls")
    if not os.path.isdir(src):
        return {"ok": False, "reason": f"spoke folder missing: spokes/{spoke}", "llm_calls": 0}
    notes = markdown_files(src)
    if not notes:
        return {"ok": True, "skipped": True, "reason": "spoke has no notes yet; graph skipped", "llm_calls": 0}
    # A stable input path preserves graphify's per-file cache keys across runs.
    staged = os.path.join(work, "notes")
    for d in (WORK_ROOT, work, out, home):
        os.makedirs(d, mode=0o700, exist_ok=True)
    open(calls, "w").close()
    _snapshot(out, keep)
    env = graphify_env(cfg, SHIM_DIR, home, calls)
    g = graphify_cmd(cfg)
    res = {"ok": False}
    try:
        shutil.rmtree(staged, ignore_errors=True)
        for rel in notes:
            dst = os.path.join(staged, rel)
            os.makedirs(os.path.dirname(dst), mode=0o700, exist_ok=True)
            shutil.copy2(os.path.join(src, rel), dst)
        for argv in (g + ["extract", staged, "--backend", cfg["graph"]["backend"], "--out", work],
                     g + ["cluster-only", work, "--no-label"]):
            left = deadline - time.time()
            if left <= 0:
                res["reason"] = f"time cap of {cfg['claude']['max_run_minutes']} min reached"
                break
            rc, tail, timed_out = claude_guard.run_guarded(argv, env, work, left)
            if timed_out or rc != 0:
                res["reason"] = (f"graphify {argv[len(g)]} " + ("killed at the time cap" if timed_out else f"exited {rc}")
                                 + f" (exit {rc}): " + error_line(tail))
                break
        else:
            n = _node_count(os.path.join(out, "graph.json"))
            html = os.path.join(out, "graph.html")
            floor = max(1, int(cfg["graph"].get("min_nodes") or 1))
            if n is None:
                res["reason"] = "graph.json missing or unreadable after the run"
            elif n < floor:
                res["reason"] = f"new graph has {n} nodes (< floor {floor}); kept the old graph"
            elif not (os.path.exists(html) and os.path.getsize(html)):
                res["reason"] = "graph.html missing or empty after cluster-only"
            else:
                publish(cfg, spoke, out)
                res = {"ok": True, "nodes": n}
    except Exception as e:
        res["reason"] = f"{type(e).__name__}: {e}"[:500]
    finally:
        shutil.rmtree(staged, ignore_errors=True)
    if not res["ok"]:
        _restore(out, keep)
    with open(calls, encoding="utf-8") as f:
        res["llm_calls"] = sum(1 for _ in f)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--spoke")
    a = ap.parse_args(argv)
    try:
        cfg = boxlib.load_config(a.config)
    except (OSError, ValueError, TypeError) as e:
        print(f"graph config: {e} (exit 2)", file=sys.stderr)
        return 2
    if not cfg["graph"].get("enabled"):
        print("graph disabled in config; nothing to do")
        return 0
    spokes = [s for s, v in (cfg.get("spokes") or {}).items() if (v or {}).get("graph", True)]
    if a.spoke:
        if a.spoke not in spokes:
            sys.exit(f"unknown or graph-disabled spoke: {a.spoke}")
        spokes = [a.spoke]
    # Empty spokes need no model login and must still report a successful skip.
    if any(not os.path.isdir(boxlib.p(cfg, "spokes", s)) or markdown_files(boxlib.p(cfg, "spokes", s)) for s in spokes):
        try:
            claude_guard.wait_ready(cfg, "graph")          # writes status/graph.json itself on refusal
        except claude_guard.GuardRefused as e:
            print(f"{e} (exit {e.exit_code})", file=sys.stderr)
            return e.exit_code
    cap = float(cfg["claude"]["max_run_minutes"]) * 60
    results = {}
    for s in spokes:
        results[s] = run_spoke(cfg, s, time.time() + cap)
        if results[s].get("skipped"):
            print(f"{s}: {results[s]['reason']}")
            continue
        print(f"{s}: " + ("ok, %d nodes" % results[s]["nodes"] if results[s]["ok"] else "FAILED: " + results[s]["reason"])
              + f" (model calls: {results[s]['llm_calls']})")
    bad = [s for s, r in results.items() if not r["ok"]]
    reason = "; ".join(f"{s}: {results[s]['reason'][:200]}" for s in bad) or None
    boxlib.write_status(cfg, "graph", not bad, reason=reason, spokes=results)
    return 1 if bad else 0


if __name__ == "__main__":
    os.umask(0o027)
    sys.exit(main())
