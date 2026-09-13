from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderAuthExpired, ProviderRateLimited
from src.case_radar.providers.reddit_oauth import RedditOAuthProvider


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, post_responses=None, get_responses=None):
        self.post_responses = list(post_responses or [])
        self.get_responses = list(get_responses or [])
        self.posts = []
        self.gets = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self.post_responses.pop(0)

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return self.get_responses.pop(0)


def _search_payload():
    return {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc",
                        "title": "Strange footage",
                        "selftext": "context",
                        "author": "poster",
                        "permalink": "/r/mystery/comments/abc/strange_footage/",
                        "created_utc": 1730000000,
                        "score": 10,
                        "num_comments": 1,
                        "is_video": True,
                        "subreddit": "mystery",
                    },
                }
            ],
            "after": None,
        }
    }


def _thread_payload():
    return [
        {"data": {"children": []}},
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c1",
                            "parent_id": "t3_abc",
                            "author": "poster",
                            "body": "Original source: https://example.com/source",
                            "created_utc": 1730000100,
                            "score": 9,
                            "permalink": "/r/mystery/comments/abc/strange_footage/c1/",
                            "replies": "",
                        },
                    }
                ]
            }
        },
    ]


def test_oauth_provider_is_available_only_with_client_credentials():
    assert RedditOAuthProvider(client_id="", client_secret="").is_available() is False
    assert RedditOAuthProvider(client_id="id", client_secret="secret").is_available() is True


def test_oauth_search_gets_app_token_and_normalizes_post_without_leaking_secret():
    client = FakeClient(
        post_responses=[FakeResponse({"access_token": "opaque-token", "expires_in": 3600})],
        get_responses=[FakeResponse(_search_payload())],
    )
    provider = RedditOAuthProvider(
        client_id="client-id",
        client_secret="super-secret",
        user_agent="linux:content-radar:1.0 (by /u/tester)",
        client=client,
    )

    page = provider.search(SimpleNamespace(), SimpleNamespace(query_text="strange footage"))

    assert page.candidates[0].platform == "reddit"
    assert page.candidates[0].external_id == "abc"
    assert page.candidates[0].discovery_method == "official_api"
    assert "super-secret" not in str(page.candidates[0].raw_json)
    token_url, token_kwargs = client.posts[0]
    assert token_url.endswith("/api/v1/access_token")
    assert token_kwargs["data"] == {"grant_type": "client_credentials"}
    search_url, search_kwargs = client.gets[0]
    assert search_url == "https://oauth.reddit.com/search"
    assert search_kwargs["headers"]["Authorization"] == "Bearer opaque-token"


def test_oauth_social_context_collects_comment_links():
    client = FakeClient(
        post_responses=[FakeResponse({"access_token": "opaque-token", "expires_in": 3600})],
        get_responses=[FakeResponse(_thread_payload())],
    )
    provider = RedditOAuthProvider(client_id="id", client_secret="secret", client=client)
    candidate = provider._post_to_candidate(_search_payload()["data"]["children"][0]["data"], "query")

    page = provider.fetch_social_context(candidate, {"max_comments": 5, "max_depth": 1})

    assert len(page.items) == 1
    assert page.items[0].author_reply is True
    assert page.items[0].external_links == ["https://example.com/source"]


def test_oauth_401_is_sanitized_auth_error():
    client = FakeClient(post_responses=[FakeResponse({"error": "invalid_client"}, status_code=401)])
    provider = RedditOAuthProvider(client_id="id", client_secret="secret-value", client=client)
    with pytest.raises(ProviderAuthExpired) as captured:
        provider.search(SimpleNamespace(), "query")
    assert "secret-value" not in str(captured.value)


def test_oauth_429_maps_to_rate_limit():
    client = FakeClient(
        post_responses=[FakeResponse({"access_token": "token", "expires_in": 3600})],
        get_responses=[FakeResponse({}, status_code=429)],
    )
    provider = RedditOAuthProvider(client_id="id", client_secret="secret", client=client)
    with pytest.raises(ProviderRateLimited):
        provider.search(SimpleNamespace(), "query")
