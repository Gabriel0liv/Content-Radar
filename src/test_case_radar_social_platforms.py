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
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error

    def search(self, query, cursor=None):
        if self.error:
            raise self.error
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
