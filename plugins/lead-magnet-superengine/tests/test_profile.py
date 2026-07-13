import json, pathlib, pytest
from lib import profile

def test_load_blank_profile_has_required_keys(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"name": "client", "mode": "blank", "upgrades": {}}))
    prof = profile.load_profile(str(p))
    assert prof["name"] == "client"
    assert prof["mode"] == "blank"
    assert prof["upgrades"] == {}

def test_load_profile_rejects_missing_keys(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"name": "x"}))
    with pytest.raises(ValueError):
        profile.load_profile(str(p))

def test_resolve_returns_enabled_block():
    prof = {"name": "joe", "mode": "full",
            "upgrades": {"search": {"enabled": True, "endpoint": "http://example-search:8888"}}}
    assert profile.resolve(prof, "search")["endpoint"] == "http://example-search:8888"

def test_resolve_returns_none_when_absent_or_disabled():
    prof = {"name": "c", "mode": "blank",
            "upgrades": {"search": {"enabled": False}}}
    assert profile.resolve(prof, "search") is None
    assert profile.resolve(prof, "scrape") is None

def test_save_profile_roundtrips(tmp_path):
    prof = {"name": "roundtrip", "mode": "full", "upgrades": {"search": {"enabled": True}}}
    out = tmp_path / "out.json"
    profile.save_profile(prof, str(out))
    loaded = profile.load_profile(str(out))
    assert loaded == prof

def test_save_profile_writes_valid_json(tmp_path):
    prof = {"name": "jsoncheck", "mode": "blank", "upgrades": {}}
    out = tmp_path / "check.json"
    profile.save_profile(prof, str(out))
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
