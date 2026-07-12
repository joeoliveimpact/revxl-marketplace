import json

REQUIRED = ("name", "mode", "upgrades")

def load_profile(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.loads(f.read())
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise ValueError(f"profile missing required keys: {missing}")
    return data

def save_profile(profile: dict, path: str) -> str:
    missing = [k for k in REQUIRED if k not in profile]
    if missing:
        raise ValueError(f"profile missing required keys: {missing}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    return path

def resolve(profile: dict, capability: str) -> dict | None:
    block = profile.get("upgrades", {}).get(capability)
    if not block or not block.get("enabled"):
        return None
    return block
