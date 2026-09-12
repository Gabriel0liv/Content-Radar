from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderAuthExpired
from src.case_radar.providers.x import XLoggedInProvider, XOfficialApiProvider, XWebSearchProvider


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params or {}, headers or {}))
        return self.responses.pop(0)


class FakeLoggedInClient:
    def __init__(self, result=None, error=None):
        self.result = result or []
        self.error = error

    def search_tweet(self, query, mode):
        if self.error:
            raise self.error
        return self.result


class FakeTweet:
    id = "123"
    text = "strange forest footage"
    created_at = "2025-01-01T10:00:00+00:00"
    lang = "en"
    favorite_count = 10
    reply_count = 2
    retweet_count = 3
    user = SimpleNamespace(screen_name="tester", name="Tester")


def test_x_web_search_has_only_capabilities_it_implements():
    provider = XWebSearchProvider(backend=SimpleNamespace())
    assert provider.platform == "x"
    assert provider.method == "web_search"
    assert provider.capabilities.comments_supported is False
    assert provider.capabilities.replies_supported is False


def test_x_official_is_available_only_with_token():
    assert XOfficialApiProvider(bearer_token="").is_available() is False
    assert XOfficialApiProvider(bearer_token="token").is_available() is True


def test_x_official_search_normalizes_post_without_exposing_token():
    client = FakeClient([
        FakeResponse(
            {
                "data": [
                    {
                        "id": "42",
                        "text": "strange clip",
                        "author_id": "u1",
                        "created_at": "2025-01-01T00:00:00Z",
                        "lang": "en",
                        "public_metrics": {"like_count": 7, "reply_count": 1, "retweet_count": 2, "quote_count": 0},
                    }
                ],
                "meta": {},
            }
        )
    ])
    provider = XOfficialApiProvider(bearer_token="super-secret-token", client=client)
    page = provider.search(SimpleNamespace(), SimpleNamespace(query_text="forest mystery"))
    candidate = page.candidates[0]
    assert candidate.external_id == "42"
    assert candidate.discovery_method == "official_api"
    assert "super-secret-token" not in str(candidate.raw_json)


def test_x_logged_in_capabilities_do_not_claim_unimplemented_replies():
    provider = XLoggedInProvider(client=FakeLoggedInClient(result=[FakeTweet()]))
    assert provider.capabilities.comments_supported is False
    assert provider.capabilities.replies_supported is False
    page = provider.search(SimpleNamespace(), "forest")
    assert page.candidates[0].author_handle == "@tester"


def test_x_logged_in_auth_error_is_sanitized():
    provider = XLoggedInProvider(
        session_file="C:/private/session.json",
        client=FakeLoggedInClient(error=RuntimeError("login cookie secret=abc challenge")),
    )
    with pytest.raises(ProviderAuthExpired) as captured:
        provider.search(SimpleNamespace(), "forest")
    message = str(captured.value)
    assert "abc" not in message
    assert "C:/private" not in message
