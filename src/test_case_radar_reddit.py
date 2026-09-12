from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderRateLimited
from src.case_radar.providers.reddit import RedditCaseRadarProvider


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

    def get(self, url, params=None):
        self.calls.append((url, params or {}))
        return self.responses.pop(0)


def _post_payload():
    return {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "post1",
                        "title": "Strange forest footage",
                        "selftext": "Found this last night",
                        "author": "poster",
                        "permalink": "/r/mystery/comments/post1/strange_forest/",
                        "created_utc": 1730000000,
                        "score": 120,
                        "num_comments": 2,
                        "is_video": True,
                        "subreddit": "mystery",
                    },
                }
            ],
            "after": "t3_next",
        }
    }


def _thread_payload():
    return [
        _post_payload(),
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c1",
                            "parent_id": "t3_post1",
                            "author": "poster",
                            "body": "Original upload is here: https://example.com/original",
                            "created_utc": 1730000100,
                            "score": 15,
                            "permalink": "/r/mystery/comments/post1/strange_forest/c1/",
                            "replies": {
                                "data": {
                                    "children": [
                                        {
                                            "kind": "t1",
                                            "data": {
                                                "id": "c2",
                                                "parent_id": "t1_c1",
                                                "author": "[deleted]",
                                                "body": "[removed]",
                                                "created_utc": 1730000200,
                                                "score": 2,
                                                "permalink": "/r/mystery/comments/post1/strange_forest/c2/",
                                            },
                                        }
                                    ]
                                }
                            },
                        },
                    }
                ]
            }
        },
    ]


def test_reddit_search_normalizes_posts():
    client = FakeClient([FakeResponse(_post_payload())])
    provider = RedditCaseRadarProvider(client=client)

    page = provider.search(SimpleNamespace(), SimpleNamespace(query_text="forest mystery"))

    assert page.next_cursor == "t3_next"
    candidate = page.candidates[0]
    assert candidate.platform == "reddit"
    assert candidate.external_id == "post1"
    assert candidate.author_handle == "poster"
    assert candidate.engagement == {"score": 120, "comments": 2}


def test_reddit_comments_preserve_parent_child_hierarchy_and_deleted_values():
    client = FakeClient([FakeResponse(_thread_payload())])
    provider = RedditCaseRadarProvider(client=client)
    candidate = provider._post_to_candidate(_post_payload()["data"]["children"][0]["data"], "query")

    page = provider.fetch_social_context(candidate, {"max_comments": 10, "max_depth": 3})

    assert [item.platform_item_id for item in page.items] == ["c1", "c2"]
    assert page.items[0].depth == 0
    assert page.items[0].author_reply is True
    assert page.items[1].depth == 1
    assert page.items[1].parent_id == "t1_c1"
    assert page.items[1].author_handle is None
    assert page.items[1].body == ""


def test_reddit_comment_depth_budget_stops_deep_replies():
    client = FakeClient([FakeResponse(_thread_payload())])
    provider = RedditCaseRadarProvider(client=client)
    candidate = provider._post_to_candidate(_post_payload()["data"]["children"][0]["data"], "query")

    page = provider.fetch_social_context(candidate, {"max_comments": 10, "max_depth": 0})
    assert [item.platform_item_id for item in page.items] == ["c1"]


def test_reddit_rate_limit_maps_to_provider_error():
    client = FakeClient([FakeResponse({}, status_code=429)])
    provider = RedditCaseRadarProvider(client=client)
    with pytest.raises(ProviderRateLimited):
        provider.search(SimpleNamespace(), "query")
