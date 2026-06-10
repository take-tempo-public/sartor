"""Unit tests for scraper.py — the deterministic URL layer.

These functions must remain LLM-free. The fetch helpers are exercised against
a stubbed requests.get so no network access is required.
"""

from scraper import _ensure_scheme, fetch_url_content


class TestEnsureScheme:
    def test_prepends_https_to_bare_host(self):
        assert _ensure_scheme("github.com/you") == "https://github.com/you"

    def test_prepends_https_to_www_host(self):
        assert _ensure_scheme("www.example.com") == "https://www.example.com"

    def test_leaves_https_untouched(self):
        assert _ensure_scheme("https://example.com") == "https://example.com"

    def test_leaves_http_untouched(self):
        assert _ensure_scheme("http://example.com") == "http://example.com"

    def test_leaves_other_explicit_scheme_untouched(self):
        assert _ensure_scheme("ftp://files.example.com") == "ftp://files.example.com"

    def test_strips_surrounding_whitespace(self):
        assert _ensure_scheme("  example.com  ") == "https://example.com"

    def test_empty_string_stays_empty(self):
        assert _ensure_scheme("") == ""

    def test_whitespace_only_stays_empty(self):
        assert _ensure_scheme("   ") == ""

    def test_host_with_port_is_not_mistaken_for_scheme(self):
        assert _ensure_scheme("example.com:8080/path") == "https://example.com:8080/path"


class TestFetchUrlContentNormalizesScheme:
    def test_bare_host_is_fetched_over_https(self, monkeypatch):
        captured = {}

        class _Resp:
            text = "<html><body><p>hello</p></body></html>"

            def raise_for_status(self):
                pass

        def fake_get(url, **kwargs):
            captured["url"] = url
            return _Resp()

        monkeypatch.setattr("scraper.requests.get", fake_get)

        result = fetch_url_content("github.com/you")

        assert captured["url"] == "https://github.com/you"
        assert "hello" in result

    def test_empty_url_short_circuits_without_request(self, monkeypatch):
        def fail_get(url, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("requests.get should not be called for empty URL")

        monkeypatch.setattr("scraper.requests.get", fail_get)

        assert fetch_url_content("   ") == ""
