from src.services.discovery_terms_service import (
    discovery_term_score,
    should_promote_tag,
)


def test_generic_tags_are_suppressed_even_when_frequent():
    assert should_promote_tag("viral", video_count=50, channel_count=20) is False
    assert should_promote_tag("youtube", video_count=100, channel_count=40) is False


def test_specific_tag_is_promoted_across_multiple_videos_and_channels():
    assert should_promote_tag("minecraft hardcore", video_count=4, channel_count=3) is True


def test_single_video_tag_is_not_promoted_automatically():
    assert should_promote_tag("obscure one off tag", video_count=1, channel_count=1) is False


def test_relevance_rewards_breadth_more_than_raw_usage():
    broad = discovery_term_score(video_count=10, channel_count=5, usage_count=10)
    spammy = discovery_term_score(video_count=10, channel_count=1, usage_count=40)
    assert broad > spammy
