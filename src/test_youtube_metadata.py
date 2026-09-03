from src.schemas.content_item import ContentItemIngest
from src.services.youtube_metadata_service import normalize_tag, normalize_topic_category


def test_content_ingest_accepts_official_youtube_discovery_metadata():
    item = ContentItemIngest(
        source="youtube",
        external_id="dQw4w9WgXcQ",
        content_type="video",
        title="Example",
        url="https://youtu.be/dQw4w9WgXcQ",
        youtube_video_id="dQw4w9WgXcQ",
        youtube_category_id="20",
        youtube_category_name="Gaming",
        youtube_tags_json=["Minecraft", "Analog Horror"],
        youtube_topics_json=["Gaming", "Role-playing video game"],
        channel_id="UC123",
    )

    assert item.youtube_video_id == "dQw4w9WgXcQ"
    assert item.youtube_category_name == "Gaming"
    assert item.youtube_tags_json == ["Minecraft", "Analog Horror"]
    assert item.youtube_topics_json == ["Gaming", "Role-playing video game"]
    assert item.channel_id == "UC123"


def test_normalize_tag_is_search_friendly_but_does_not_change_source_value():
    assert normalize_tag("  Minecraft   Hardcore ") == "minecraft hardcore"


def test_normalize_topic_category_extracts_human_readable_topic_name():
    assert normalize_topic_category("https://en.wikipedia.org/wiki/Role-playing_video_game") == "Role-playing video game"
    assert normalize_topic_category("Minecraft") == "Minecraft"
