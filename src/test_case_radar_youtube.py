from datetime import date
from types import SimpleNamespace

import pytest

from src.case_radar.providers.base import ProviderRateLimited, ProviderUnavailable
from src.case_radar.providers.youtube import YouTubeCaseRadarProvider


class FakeRequest:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return self.payload


class FakeResource:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.responses.pop(0)
        if isinstance(payload, Exception):
            return FakeRequest(error=payload)
        return FakeRequest(payload=payload)


class FakeYouTube:
    def __init__(self, search_responses, video_responses):
        self.search_resource = FakeResource(search_responses)
        self.video_resource = FakeResource(video_responses)

    def search(self):
        return self.search_resource

    def videos(self):
        return self.video_resource


def _video_item(video_id="abc123"):
    return {
        "id": video_id,
        "snippet": {
            "title": "Strange forest footage",
            "description": "Recorded at night",
            "channelTitle": "Mystery Channel",
            "channelId": "channel-1",
            "publishedAt": "2025-01-02T03:04:05Z",
            "defaultAudioLanguage": "en",
            "tags": ["forest", "mystery"],
            "thumbnails": {"high": {"url": "https://img.example/thumb.jpg"}},
            "categoryId": "24",
        },
        "statistics": {"viewCount": "123", "likeCount": "4", "commentCount": "5"},
        "contentDetails": {"duration": "PT1M2S"},
    }


def test_youtube_provider_requires_api_key():
    provider = YouTubeCaseRadarProvider(api_key="")
    assert provider.is_available() is False
    with pytest.raises(ProviderUnavailable):
        provider.search(SimpleNamespace(), "query")


def test_youtube_provider_search_normalizes_video_metadata():
    fake = FakeYouTube(
        search_responses=[{"items": [{"id": {"videoId": "abc123"}}], "nextPageToken": "next"}],
        video_responses=[{"items": [_video_item()]}],
    )
    provider = YouTubeCaseRadarProvider(api_key="key", client_factory=lambda key: fake)
    request = SimpleNamespace(date_from=date(2025, 1, 1), date_to=date(2025, 2, 1))
    query = SimpleNamespace(query_text="strange forest", language="en")

    page = provider.search(request, query)

    assert page.next_cursor == "next"
    assert page.candidates[0].external_id == "abc123"
    assert page.candidates[0].canonical_url == "https://youtube.com/watch?v=abc123"
    assert page.candidates[0].duration_seconds == 62.0
    assert page.candidates[0].engagement == {"views": 123, "likes": 4, "comments": 5}
    search_call = fake.search_resource.calls[0]
    assert search_call["publishedAfter"].startswith("2025-01-01T00:00:00")
    assert search_call["publishedBefore"].startswith("2025-02-01T23:59:59")
    assert search_call["relevanceLanguage"] == "en"


def test_youtube_fetch_source_enriches_existing_candidate():
    fake = FakeYouTube(search_responses=[], video_responses=[{"items": [_video_item()]}])
    provider = YouTubeCaseRadarProvider(api_key="key", client_factory=lambda key: fake)
    candidate = provider._details_to_candidate(_video_item(), "query")

    snapshot = provider.fetch_source(candidate)

    assert snapshot.candidate.title_or_caption == "Strange forest footage"
    assert snapshot.raw_json["source"] == "youtube_data_api"


def test_youtube_quota_error_maps_to_rate_limited():
    fake = FakeYouTube(search_responses=[RuntimeError("403 quota exceeded")], video_responses=[])
    provider = YouTubeCaseRadarProvider(api_key="key", client_factory=lambda key: fake)

    with pytest.raises(ProviderRateLimited):
        provider.search(SimpleNamespace(date_from=None, date_to=None), "query")


def test_importing_youtube_provider_does_not_load_speech_ml_modules():
    import sys

    assert "whisperx" not in sys.modules
    assert "torch" not in sys.modules
