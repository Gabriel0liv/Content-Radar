from datetime import date
from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderAuthExpired
from src.case_radar.providers.tiktok_research import TikTokResearchProvider


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

    def post(self, url, params=None, json=None, headers=None):
        self.calls.append({"url": url, "params": params or {}, "json": json or {}, "headers": headers or {}})
        return self.responses.pop(0)


def test_tiktok_research_search_uses_keyword_query_and_normalizes_video():
    client = FakeClient([
        FakeResponse(
            {
                "data": {
                    "videos": [
                        {
                            "id": 12345,
                            "username": "mystery",
                            "video_description": "strange forest creature",
                            "create_time": 1735689600,
                            "region_code": "PT",
                            "view_count": 1000,
                            "like_count": 100,
                            "comment_count": 20,
                            "share_count": 5,
                            "favorites_count": 8,
                            "hashtag_names": ["mystery"],
                            "video_duration": 42,
                        }
                    ],
                    "cursor": 1,
                    "has_more": False,
                    "search_id": "s1",
                },
                "error": {"code": "ok"},
            }
        )
    ])
    provider = TikTokResearchProvider(access_token="secret-token", client=client)
    request = SimpleNamespace(date_from=date(2025, 1, 1), date_to=date(2025, 1, 20))

    page = provider.search(request, SimpleNamespace(query_text="forest creature"))

    assert page.candidates[0].canonical_url == "https://tiktok.com/@mystery/video/12345"
    assert page.candidates[0].engagement["comments"] == 20
    assert page.candidates[0].discovery_method == "official_api"
    sent = client.calls[0]
    assert sent["json"]["query"]["and"][0]["field_name"] == "keyword"
    assert sent["json"]["start_date"] == "20250101"
    assert sent["json"]["end_date"] == "20250120"
    assert "secret-token" not in str(page.raw_json)


def test_tiktok_research_caps_a_long_query_window_to_30_days():
    client = FakeClient([FakeResponse({"data": {"videos": [], "has_more": False}, "error": {"code": "ok"}})])
    provider = TikTokResearchProvider(access_token="token", client=client)
    request = SimpleNamespace(date_from=date(2024, 1, 1), date_to=date(2025, 1, 1))

    page = provider.search(request, "mystery")

    assert page.raw_json["date_window_truncated_to_30_days"] is True
    assert client.calls[0]["json"]["start_date"] == "20241203"
    assert client.calls[0]["json"]["end_date"] == "20250101"


def test_tiktok_research_collects_comments_and_direct_replies():
    client = FakeClient([
        FakeResponse(
            {
                "data": {
                    "comments": [
                        {"id": "c1", "video_id": "123", "text": "original source?", "like_count": 10, "reply_count": 1, "create_time": 1735689600}
                    ],
                    "has_more": False,
                },
                "error": {"code": "ok"},
            }
        ),
        FakeResponse(
            {
                "data": {
                    "comments": [
                        {"id": "r1", "video_id": "123", "parent_comment_id": "c1", "text": "it was posted in 2021", "like_count": 5, "reply_count": 0, "create_time": 1735689700}
                    ]
                },
                "error": {"code": "ok"},
            }
        ),
    ])
    provider = TikTokResearchProvider(access_token="token", client=client)
    candidate = SimpleNamespace(external_id="123")

    page = provider.fetch_social_context(candidate, {"max_comments": 10, "max_depth": 2})

    assert [item.platform_item_id for item in page.items] == ["c1", "r1"]
    assert page.items[1].parent_id == "c1"
    assert page.items[1].depth == 1
    assert client.calls[1]["json"]["comment_id"] == "c1"


def test_tiktok_research_maps_auth_failure_without_leaking_token():
    client = FakeClient([FakeResponse({}, status_code=403)])
    provider = TikTokResearchProvider(access_token="very-secret", client=client)
    with pytest.raises(ProviderAuthExpired) as captured:
        provider.search(SimpleNamespace(date_from=None, date_to=None), "test")
    assert "very-secret" not in str(captured.value)
