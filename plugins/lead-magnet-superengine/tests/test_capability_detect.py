from lib import capability_detect as cd

def test_detect_uses_injected_probe_true():
    prof = {"name":"j","mode":"full","upgrades":{"search":{"enabled":True}}}
    result = cd.detect(prof, probes={"search": lambda: True})
    assert result["search"] is True

def test_detect_disabled_upgrade_is_false_without_probe():
    prof = {"name":"c","mode":"blank","upgrades":{"search":{"enabled":False}}}
    result = cd.detect(prof, probes={})
    assert result["search"] is False

def test_detect_enabled_but_probe_fails_is_false():
    prof = {"name":"j","mode":"full","upgrades":{"search":{"enabled":True}}}
    result = cd.detect(prof, probes={"search": lambda: False})
    assert result["search"] is False

def test_detect_enabled_no_probe_is_false():
    # An enabled capability with NO probe supplied must NOT report live.
    # Honest default: unprobed = unverified = False.
    prof = {"name":"c","mode":"blank","upgrades":{"social":{"enabled":True}}}
    result = cd.detect(prof, probes={})
    assert result["social"] is False

def test_probe_port_closed_is_false():
    # nothing listens on this port
    assert cd.probe_port("127.0.0.1", 1, timeout=0.2) is False
