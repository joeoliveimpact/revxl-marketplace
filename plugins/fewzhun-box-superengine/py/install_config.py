"""Read installer values with stdlib Python when a dry run has no Node yet.

The installed Node config loader remains the validator before --apply proceeds.
"""
import json, os, re, shlex, subprocess, sys

with open(sys.argv[1], encoding="utf-8") as f:
    c = json.load(f)
root = c.get("root") or "/opt/fewzhun-box"
code_root = c.get("code_root", "/opt/fewzhun-box-app")
spokes, readers = c.get("spokes", {}), c.get("readers", {})
if not spokes or not readers or any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", x) for x in [*spokes, *readers]):
    sys.exit("spokes and readers need plain names")
sync, graph, harvest = (c.get(k) or {} for k in ("sync", "graph", "harvest"))
etc = os.path.dirname(os.path.abspath(sys.argv[1]))
bind, tail = c.get("bind", "auto-docker"), c.get("tailnet_bind")
try:
    interfaces = json.loads(subprocess.check_output(["ip", "-j", "-4", "addr"], stderr=subprocess.DEVNULL))
except (OSError, subprocess.SubprocessError, ValueError):
    interfaces = []


def address(spec):
    if spec not in ("auto", "auto-docker"):
        return spec or ""
    for entry in sorted(interfaces, key=lambda e: e["ifname"] != "docker0"):
        name = entry["ifname"]
        if (spec == "auto-docker" and (name == "docker0" or name.startswith("br-"))) or (spec == "auto" and name == "tailscale0"):
            return next((a["local"] for a in entry.get("addr_info", []) if a.get("family") == "inet"), "")
    return ""


values = dict(ROOT=root, CODE_ROOT=code_root, SPOKES=" ".join(spokes), NSPOKES=len(spokes), READERS=" ".join(readers),
              PORT=c.get("port", 8791), BIND_SPEC=bind, BIND=address(bind), TAILNET_SPEC=tail or "", TAILNET=address(tail),
              WARM=c.get("warm", "all"), MEMORY_MAX=c.get("memory_max", "3500M"), TIMEZONE=c.get("timezone", "UTC"),
              LOG_DIR=c.get("log_dir", "/var/log/fewzhun-box"), ENGINE=c.get("engine") or code_root + "/node_modules/.bin/obsidian-hybrid-search",
              TOKENS_DIR=c.get("tokens_dir", "/etc/fewzhun-box/tokens"), TOKENS_FILE=etc + "/tokens.json",
              SYNC_ENABLED=int(bool(sync.get("enabled"))), SYNC_INTERVAL=sync.get("interval_min", 15),
              SYNC_GITCONFIG=sync.get("git_config", "/etc/fewzhun-box/sync.gitconfig"),
              SYNC_SSH=int(bool(re.match(r"^(git@|ssh://)", sync.get("repo") or ""))),
              DEPLOY_KEY=sync.get("deploy_key", "/etc/fewzhun-box/deploy_key"),
              GRAPH_ENABLED=int(bool(graph.get("enabled", True))), GRAPHIFY_VERSION=graph.get("graphify_version", "0.9.112"),
              GRAPH_TIME=graph.get("time", "03:30"), HARVEST_ENABLED=int(bool(harvest.get("enabled"))),
              HARVEST_TIME=harvest.get("time", "02:30"), CLAUDE_RUN_AS=(c.get("claude") or {}).get("run_as") or "")
for key, value in values.items():
    print(f"{key}={shlex.quote(str(value))}")
