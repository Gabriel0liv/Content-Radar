from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderAuthExpired, ProviderUnavailable
from src.case_radar.providers.instagram import (
    InstagramLoggedInProvider,
    InstagramOfficialProvider,
    InstagramWebSearchProvider,
)
from src.case_radar.providers.tiktok import TikTokLoggedInProvider, TikTokOfficialProvider, TikTokWebSearchProvider


class FakeAdapter:
    def __init__(self, rows=None, error=None, comments=None, source=None):
        self.rows = rows or []
        self.error = error
        self.comments = comments
        self.source = source

    def search(self, query, cursor=None):
        if self.error:
            raise self.error
        return self.rows

    def fetch_social_context(self, url, **kwargs):
        if self.error:
            raise self.error
        return self.comments or []

    def fetch_source(self, url, **kwargs):
        if self.error:
            raise self.error
        return self.source or {"url": url}


class SearchOnlyAdapter:
    def __init__(self, rows=None):
        self.rows = rows or []

    def search(self, query, cursor=None):
        return self.rows


def test_tiktok_web_search_capabilities_are_conservative():
    provider = TikTokWebSearchProvider(backend=SimpleNamespace())
    assert provider.platform == "tiktok"
    assert provider.capabilities.comments_supported is False


def test_tiktok_official_search_is_disabled_without_explicit_endpoint():
    provider = TikTokOfficialProvider(access_token="token", endpoint="")
    assert provider.capabilities.search_supported is False
    assert provider.is_available() is False
    with pytest.raises(ProviderUnavailable):
        provider.search(SimpleNamespace(), "query")


def test_tiktok_logged_in_search_only_adapter_does_not_claim_comments():
    provider = TikTokLoggedInProvider(adapter=SearchOnlyAdapter())
    assert provider.capabilities.comments_supported is False
    assert provider.capabilities.replies_supported is False


def test_tiktok_logged_in_adapter_normalizes_rows_without_exposing_session():
    provider = TikTokLoggedInProvider(
        session_file="C:/secret/tiktok.json",
        adapter=FakeAdapter(
            rows=[
                {
                    "id": "1",
                    "url": "https://www.tiktok.com/@u/video/1?utm_source=x",
                    "author_handle": "@u",
                    "caption": "strange clip",
                    "engagement": {"likes": 3},
                }
            ]
        ),
    )
    page = provider.search(SimpleNamespace(), "forest")
    candidate = page.candidates[0]
    assert candidate.canonical_url == "https://tiktok.com/@u/video/1"
    assert "secret" not in str(candidate.raw_json)
    assert provider.capabilities.comments_supported is True
    assert provider.capabilities.replies_supported is True


def test_tiktok_logged_in_adapter_normalizes_comments_and_links():
    adapter = FakeAdapter(
        comments=[
            {
                "id": "c1",
                "body": "Original source: https://example.com/original?utm_source=tiktok",
                "author_handle": "@helper",
                "engagement": {"likes": 12},
                "external_links": ["https://example.com/original?utm_source=tiktok"],
                "pinned": True,
            }
        ]
    )
    provider = TikTokLoggedInProvider(adapter=adapter)
    candidate = SimpleNamespace(
        canonical_url="https://tiktok.com/@u/video/1",
        external_id="1",
    )

    page = provider.fetch_social_context(candidate, {"max_comments": 20, "max_depth": 3})

    assert page.items[0].platform_item_id == "c1"
    assert page.items[0].external_links == ["https://example.com/original"]
    assert page.items[0].pinned is True


def test_tiktok_logged_in_auth_error_is_sanitized():
    provider = TikTokLoggedInProvider(
        session_file="C:/secret/tiktok.json",
        adapter=FakeAdapter(error=RuntimeError("auth challenge cookie abc")),
    )
    with pytest.raises(ProviderAuthExpired) as captured:
        provider.search(SimpleNamespace(), "forest")
    assert "abc" not in str(captured.value)
    assert "C:/secret" not in str(captured.value)


def test_instagram_official_does_not_claim_global_reel_search():
    provider = InstagramOfficialProvider(access_token="token")
    assert provider.capabilities.official_api is True
    assert provider.capabilities.search_supported is False
    assert provider.is_available() is False


def test_instagram_web_search_is_available_with_backend():
    provider = InstagramWebSearchProvider(backend=SimpleNamespace())
    assert provider.platform == "instagram"
    assert provider.method == "web_search"


def test_instagram_logged_in_search_only_adapter_does_not_claim_comments():
    provider = InstagramLoggedInProvider(adapter=SearchOnlyAdapter())
    assert provider.capabilities.comments_supported is False
    assert provider.capabilities.replies_supported is False


def test_instagram_logged_in_adapter_normalizes_reel():
    provider = InstagramLoggedInProvider(
        adapter=FakeAdapter(
            rows=[
                {
                    "id": "ABC",
                    "url": "https://www.instagram.com/reel/ABC/?igsh=tracking",
                    "author_handle": "mystery",
                    "caption": "night footage",
                }
            ]
        )
    )
    page = provider.search(SimpleNamespace(), "night")
    assert page.candidates[0].canonical_url == "https://instagram.com/reel/ABC"
    assert page.candidates[0].discovery_method == "logged_in"
    assert provider.capabilities.comments_supported is True


def test_instagram_logged_in_adapter_normalizes_comments():
    provider = InstagramLoggedInProvider(
        adapter=FakeAdapter(
            comments=[
                {
                    "id": "igc1",
                    "parent_id": None,
                    "body": "Creator said this was filmed in Porto in 2022",
                    "author_handle": "context_account",
                    "engagement": {"likes": 30},
                    "author_reply": False,
                }
            ]
        )
    )
    candidate = SimpleNamespace(
        canonical_url="https://instagram.com/reel/ABC",
        external_id="ABC",
    )

    page = provider.fetch_social_context(candidate, {"max_comments": 20, "max_depth": 3})

    assert page.items[0].platform_item_id == "igc1"
    assert page.items[0].body.startswith("Creator said")
    assert page.items[0].engagement == {"likes": 30}
