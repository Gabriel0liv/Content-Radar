from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderUnavailable
from src.case_radar.providers.web_search import WebSearchProvider
from src.case_radar.url_normalization import canonicalize_url, infer_platform_from_url


class FakeSearchBackend:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def search(self, query, *, cursor=None, limit=20):
        self.calls.append({"query": query, "cursor": cursor, "limit": limit})
        return self.payload


def test_canonicalize_social_and_youtube_urls_without_destroying_ids():
    assert canonicalize_url("https://twitter.com/user/status/123?utm_source=x") == "https://x.com/user/status/123"
    assert canonicalize_url("https://x.com/user/status/456?s=20") == "https://x.com/user/status/456?s=20"
    assert canonicalize_url("https://youtu.be/abc123?si=tracking") == "https://youtube.com/watch?v=abc123"
    assert canonicalize_url("https://www.youtube.com/shorts/xyz987?feature=share") == "https://youtube.com/watch?v=xyz987"
    assert canonicalize_url("https://www.instagram.com/reel/ABC/?igsh=tracking") == "https://instagram.com/reel/ABC"
    assert canonicalize_url("https://www.tiktok.com/@user/video/123?utm_source=test") == "https://tiktok.com/@user/video/123"
    assert canonicalize_url("https://www.reddit.com/r/test/comments/abc/title/?utm_source=x") == "https://reddit.com/r/test/comments/abc/title"


def test_infer_platform_from_normalized_urls():
    assert infer_platform_from_url("https://twitter.com/a/status/1") == "x"
    assert infer_platform_from_url("https://youtu.be/abc") == "youtube"
    assert infer_platform_from_url("https://www.tiktok.com/@x/video/1") == "tiktok"
    assert infer_platform_from_url("https://example.com/post") == "web"


def test_web_search_provider_builds_site_query_and_normalizes_candidate():
    backend = FakeSearchBackend(
        {
            "results": [
                {
                    "url": "https://twitter.com/test/status/123?utm_source=google",
                    "title": "Strange forest clip",
                    "snippet": "A strange clip recorded at night",
                    "published_at": "2025-02-01T12:00:00Z",
                }
            ],
            "next_cursor": "next",
        }
    )
    provider = WebSearchProvider(backend=backend, target_platform="x", site_domain="x.com")

    page = provider.search(SimpleNamespace(), SimpleNamespace(query_text="strange forest video"))

    assert backend.calls[0]["query"] == "site:x.com strange forest video"
    assert page.next_cursor == "next"
    assert page.candidates[0].platform == "x"
    assert page.candidates[0].canonical_url == "https://x.com/test/status/123"
    assert page.candidates[0].discovery_method == "web_search"


def test_generic_web_provider_infers_social_platform_from_result_url():
    backend = FakeSearchBackend({"results": [{"url": "https://www.reddit.com/r/mystery/comments/abc/post"}]})
    provider = WebSearchProvider(backend=backend)
    page = provider.search(SimpleNamespace(), "mystery footage")
    assert page.candidates[0].platform == "reddit"


def test_web_search_without_backend_is_provider_unavailable(monkeypatch):
    monkeypatch.delenv("CASE_RADAR_WEB_SEARCH_URL", raising=False)
    monkeypatch.delenv("CASE_RADAR_WEB_SEARCH_API_KEY", raising=False)
    provider = WebSearchProvider()
    assert provider.is_available() is False
    with pytest.raises(ProviderUnavailable):
        provider.search(SimpleNamespace(), "query")


def test_web_search_raw_candidate_drops_obvious_secret_fields():
    backend = FakeSearchBackend(
        {
            "results": [
                {
                    "url": "https://example.com/a",
                    "title": "A",
                    "token": "secret",
                    "authorization": "Bearer secret",
                    "api_key": "secret",
                }
            ]
        }
    )
    provider = WebSearchProvider(backend=backend)
    candidate = provider.search(SimpleNamespace(), "query").candidates[0]
    assert "token" not in candidate.raw_json
    assert "authorization" not in candidate.raw_json
    assert "api_key" not in candidate.raw_json
