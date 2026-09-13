from datetime import datetime, timezone
from types import SimpleNamespace

from src.case_radar.providers.instagram_instagrapi import InstagrapiResearchAdapter


class FakeInstagramClient:
    def __init__(self):
        self.media = SimpleNamespace(
            pk="100",
            id="100_1",
            code="ABC",
            taken_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            media_type=2,
            product_type="clips",
            thumbnail_url="https://cdn.example/thumb.jpg",
            video_duration=12.0,
            like_count=20,
            comment_count=2,
            view_count=200,
            play_count=220,
            caption_text="night footage https://example.com/context",
            user=SimpleNamespace(username="creator", full_name="Creator"),
        )

    def media_search(self, query, amount=27):
        return [self.media]

    def media_pk_from_url(self, url):
        return "100"

    def media_info(self, pk):
        return self.media

    def media_comments(self, media_id, amount=20):
        return [
            SimpleNamespace(
                pk="c1",
                text="Original is here https://example.com/original?utm_source=ig",
                user=SimpleNamespace(username="helper", full_name="Helper"),
                created_at_utc=datetime(2025, 1, 2, tzinfo=timezone.utc),
                like_count=12,
                replied_to_comment_id=None,
            )
        ]

    def media_comment_replies(self, media_id, comment_id, amount=20):
        return [
            SimpleNamespace(
                pk="r1",
                text="Creator confirmed the location",
                user=SimpleNamespace(username="creator", full_name="Creator"),
                created_at_utc=datetime(2025, 1, 2, tzinfo=timezone.utc),
                like_count=4,
                replied_to_comment_id=comment_id,
            )
        ]


def test_instagrapi_adapter_search_normalizes_reel():
    adapter = InstagrapiResearchAdapter(FakeInstagramClient())
    rows = adapter.search("night footage")
    assert rows[0]["url"] == "https://www.instagram.com/reel/ABC/"
    assert rows[0]["author_handle"] == "@creator"
    assert rows[0]["media_type"] == "video"
    assert rows[0]["engagement"]["views"] == 200


def test_instagrapi_adapter_collects_comments_replies_and_links():
    adapter = InstagrapiResearchAdapter(FakeInstagramClient())
    rows = adapter.fetch_social_context(
        "https://instagram.com/reel/ABC",
        max_comments=10,
        max_depth=2,
    )
    assert [row["id"] for row in rows] == ["c1", "r1"]
    assert rows[0]["external_links"] == ["https://example.com/original"]
    assert rows[1]["parent_id"] == "c1"
    assert rows[1]["author_reply"] is True
