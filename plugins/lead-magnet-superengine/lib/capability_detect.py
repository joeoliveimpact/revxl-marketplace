import socket
try:
    import requests
except ImportError:
    requests = None

def probe_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def probe_http(url: str, timeout: float = 2.0) -> bool:
    if requests is None:
        return False
    try:
        return 200 <= requests.get(url, timeout=timeout).status_code < 300
    except Exception:
        return False

def detect(profile: dict, probes: dict | None = None) -> dict:
    probes = probes or {}
    out = {}
    for cap, block in profile.get("upgrades", {}).items():
        if not block.get("enabled"):
            out[cap] = False
            continue
        probe = probes.get(cap)
        # Honest default: an enabled capability with no probe is UNVERIFIED,
        # so it must not report live. Supply a probe to mark it True.
        out[cap] = bool(probe()) if probe else False
    return out
