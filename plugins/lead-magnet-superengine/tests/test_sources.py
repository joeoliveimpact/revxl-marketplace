from lib import sources

def test_searxng_url_encodes_spaces():
    u = sources.searxng_url("lead magnet ideas", base="http://example-search:8888")
    assert "q=lead+magnet+ideas" in u or "q=lead%20magnet%20ideas" in u
    assert "format=json" in u
    assert u.startswith("http://example-search:8888")

def test_search_uses_first_successful_source():
    chain = [{"kind": "searxng", "base": "http://x"}, {"kind": "floor"}]
    def fetch(kind, spec, query):
        return ["hit"] if kind == "searxng" else []
    out = sources.search("q", chain, fetch=fetch)
    assert out["source"] == "searxng"
    assert out["results"] == ["hit"]

def test_search_falls_through_to_qa_when_all_empty():
    chain = [{"kind": "searxng", "base": "http://x"}]
    out = sources.search("q", chain, fetch=lambda k, s, q: [])
    assert out["source"] == "qa"
    assert out["results"] == []
