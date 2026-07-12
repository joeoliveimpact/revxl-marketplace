from urllib.parse import quote_plus

def searxng_url(query: str, base: str) -> str:
    # base comes from the active profile: profile["upgrades"]["search"]["endpoint"]
    return f"{base}/search?q={quote_plus(query)}&format=json"

def _default_fetch(kind, spec, query):
    # real network fetch; unit tests inject their own. Returns list of results.
    import requests
    if kind == "searxng":
        base = spec.get("base")
        if not base:
            return []  # no endpoint configured -> skip this chain slot
        url = searxng_url(query, base)
        r = requests.get(url, timeout=5)
        return r.json().get("results", []) if r.ok else []
    if kind == "floor":
        return []  # WebSearch floor handled by the skill layer, not here
    return []

def search(query: str, chain: list, fetch=None) -> dict:
    fetch = fetch or _default_fetch
    for spec in chain:
        kind = spec.get("kind")
        try:
            results = fetch(kind, spec, query)
        except Exception:
            results = []
        if results:
            return {"source": kind, "results": results}
    return {"source": "qa", "results": []}
