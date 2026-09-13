from types import SimpleNamespace

from src.services.series_detection_service import select_series_candidates


def item(title, tags=None, raw_json=None):
    return SimpleNamespace(
        id=1,
        title=title,
        youtube_tags_json=tags or [],
        raw_json=raw_json or {},
    )


def test_repeated_named_smp_can_become_series_candidate():
    items = [
        item("The Beginning | Drathos SMP", ["Drathos SMP", "minecraft"]),
        item("The War | Drathos SMP", ["Drathos SMP", "roleplay"]),
        item("The Betrayal | Drathos SMP", ["Drathos SMP", "lore"]),
    ]

    candidates = select_series_candidates(items, minimum_videos=3)
    drathos = next(candidate for candidate in candidates if candidate["name"] == "Drathos SMP")
    assert drathos["video_count"] == 3


def test_playlist_title_is_strong_series_evidence():
    items = [
        item("Episode One", raw_json={"playlist_title": "Signal 9 Archives"}),
        item("Episode Two", raw_json={"playlist_title": "Signal 9 Archives"}),
        item("Episode Three", raw_json={"playlist_title": "Signal 9 Archives"}),
    ]
    names = {candidate["name"] for candidate in select_series_candidates(items, minimum_videos=3)}
    assert "Signal 9 Archives" in names


def test_generic_minecraft_tag_never_becomes_series():
    items = [item(f"Video {index}", ["minecraft", "gaming", "smp"]) for index in range(6)]
    candidates = select_series_candidates(items, minimum_videos=3)
    assert candidates == []
