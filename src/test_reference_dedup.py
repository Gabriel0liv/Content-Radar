from src.schemas.references import ReferenceSourceCreate, extract_youtube_video_id


def test_youtube_url_forms_share_canonical_video_id():
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ]

    assert {extract_youtube_video_id(url) for url in urls} == {"dQw4w9WgXcQ"}


def test_reference_source_schema_accepts_canonical_youtube_video_id():
    source = ReferenceSourceCreate(
        source_type="youtube_video",
        source_url="https://youtu.be/dQw4w9WgXcQ",
        external_id="dQw4w9WgXcQ",
        youtube_video_id="dQw4w9WgXcQ",
        title="Reference",
    )

    assert source.youtube_video_id == "dQw4w9WgXcQ"


def test_reference_repository_exposes_canonical_youtube_lookup():
    from src.repositories.references_repository import ReferencesRepository

    assert hasattr(ReferencesRepository, "get_reference_source_by_youtube_video_id")
