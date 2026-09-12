from src.case_radar.clustering import ClusterFeatures, compare_sources


def test_exact_platform_external_id_merges():
    a = ClusterFeatures(platform="x", external_id="123", canonical_url="https://x.com/a/status/123")
    b = ClusterFeatures(platform="x", external_id="123", canonical_url="https://x.com/b/status/123")
    decision = compare_sources(a, b)
    assert decision.action == "merge"
    assert decision.score == 1.0
    assert "same_platform_external_id" in decision.reasons


def test_canonical_url_duplicate_merges():
    a = ClusterFeatures(canonical_url="https://youtube.com/watch?v=abc")
    b = ClusterFeatures(canonical_url="https://youtube.com/watch?v=abc")
    assert compare_sources(a, b).action == "merge"


def test_obvious_repost_merges_from_link_and_text_similarity():
    a = ClusterFeatures(
        canonical_url="https://x.com/a/status/1",
        linked_urls=("https://example.com/original",),
        text="Strange creature recorded in the forest at night",
    )
    b = ClusterFeatures(
        canonical_url="https://reddit.com/r/x/comments/2/post",
        linked_urls=("https://example.com/original",),
        text="Strange creature recorded in the forest at night video",
    )
    decision = compare_sources(a, b)
    assert decision.action == "merge"
    assert "shared_linked_url" in decision.reasons


def test_duplicate_long_indexed_titles_merge_even_when_snippets_and_urls_differ():
    a = ClusterFeatures(
        canonical_url="https://example.com/watch/one",
        title="Real Footage of Unexplained Videos That Shocked the Internet",
        text="Compilation with several mysterious recordings and commentary.",
    )
    b = ClusterFeatures(
        canonical_url="https://mirror.example/video/two",
        title="Real Footage of Unexplained Videos That Shocked the Internet",
        text="Watch the viral collection of unexplained clips online.",
    )
    decision = compare_sources(a, b)
    assert decision.action == "merge"
    assert "same_distinctive_title" in decision.reasons


def test_near_duplicate_long_indexed_titles_merge():
    a = ClusterFeatures(title="Real Footage of Unexplained Videos That Shocked the Internet")
    b = ClusterFeatures(title="Real Footage of Unexplained Videos That Shocked The Internet!")
    decision = compare_sources(a, b)
    assert decision.action == "merge"
    assert "same_distinctive_title" in decision.reasons


def test_distinctive_title_contained_in_aggregated_search_title_merges():
    clean = ClusterFeatures(title="Real Footage of Unexplained Videos That Shocked the Internet")
    aggregated = ClusterFeatures(
        title=(
            "Watch Unexplained Caught on Camera online "
            "Real Footage of Unexplained Videos That Shocked the Internet"
            "Real Footage of Unexplained Videos That Shocked the Internet"
        )
    )
    decision = compare_sources(clean, aggregated)
    assert decision.action == "merge"
    assert "contained_distinctive_title" in decision.reasons


def test_short_generic_title_containment_does_not_auto_merge():
    a = ClusterFeatures(title="Unexplained Footage")
    b = ClusterFeatures(title="Archive of Unexplained Footage From Different Countries and Years")
    assert compare_sources(a, b).action != "merge"


def test_short_generic_titles_do_not_auto_merge():
    a = ClusterFeatures(title="Unexplained Footage", text="lights above a city")
    b = ClusterFeatures(title="Unexplained Footage", text="creature recorded in woods")
    assert compare_sources(a, b).action != "merge"


def test_similar_but_not_same_cases_stay_separate():
    a = ClusterFeatures(text="Black bear walking beside a road in Canada", alleged_location="Canada")
    b = ClusterFeatures(text="Unknown light flying above a forest in Japan", alleged_location="Japan")
    assert compare_sources(a, b).action == "separate"


def test_ambiguous_media_match_is_only_suggestion():
    a = ClusterFeatures(text="creature in woods", thumbnail_hash="same")
    b = ClusterFeatures(text="creature in forest", thumbnail_hash="same")
    decision = compare_sources(a, b)
    assert decision.action == "suggest"
    assert "same_thumbnail_hash" in decision.reasons


def test_matching_transcripts_can_raise_confidence_to_suggestion_or_merge():
    spoken = "we were walking through the forest when we heard a sound behind the camera"
    a = ClusterFeatures(text="clip", transcript_text=spoken)
    b = ClusterFeatures(text="reupload", transcript_text=spoken)
    decision = compare_sources(a, b)
    assert decision.action in {"suggest", "merge"}
    assert "very_similar_transcript" in decision.reasons
