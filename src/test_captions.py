import sys
from src.services.youtube_reference_importer import (
    merge_overlapping_text,
    YouTubeReferenceImporter
)

def test_merge_overlapping_text():
    print("Running test_merge_overlapping_text...")

    # Case 1: Exact Duplicate
    prev = "Olá tudo bem"
    curr = "Olá tudo bem"
    res = merge_overlapping_text(prev, curr)
    assert res == "", f"Expected empty string, got '{res}'"
    print("✓ Exact Duplicate passed")

    # Case 2: Current starts with Previous (buildup)
    prev = "A B C"
    curr = "A B C D E"
    res = merge_overlapping_text(prev, curr)
    assert res == "D E", f"Expected 'D E', got '{res}'"
    print("✓ Current starts with previous passed")

    # Case 3: Partial Overlap (case-insensitive and punctuation ignored)
    prev = "lamentavelmente não tem 365 dias"
    curr = "não tem 365 dias. Tem 365 dias e 5 horas"
    res = merge_overlapping_text(prev, curr)
    assert res == "Tem 365 dias e 5 horas", f"Expected 'Tem 365 dias e 5 horas', got '{res}'"
    print("✓ Partial Overlap (case & punctuation) passed")

    # Case 4: Another Partial Overlap
    prev = "Os romanos tinham um calendário de 355 dias"
    curr = "calendário de 355 dias que era corrigido com a adição"
    res = merge_overlapping_text(prev, curr)
    assert res == "que era corrigido com a adição", f"Expected 'que era corrigido com a adição', got '{res}'"
    print("✓ Another Partial Overlap passed")

    # Case 5: No Overlap at all
    prev = "Os romanos tinham um calendário"
    curr = "Outro texto totalmente diferente"
    res = merge_overlapping_text(prev, curr)
    assert res == curr, f"Expected '{curr}', got '{res}'"
    print("✓ No Overlap passed")

def test_rolling_captions_chain():
    print("\nRunning test_rolling_captions_chain...")
    # Chain: "A B C" -> "B C D" -> "C D E"
    s1 = "A B C"
    s2 = "B C D"
    s3 = "C D E"

    res2 = merge_overlapping_text(s1, s2)
    assert res2 == "D", f"Expected 'D', got '{res2}'"

    accumulated = s1 + " " + res2
    assert accumulated == "A B C D"

    res3 = merge_overlapping_text(accumulated, s3)
    assert res3 == "E", f"Expected 'E', got '{res3}'"

    final = accumulated + " " + res3
    assert final == "A B C D E", f"Expected 'A B C D E', got '{final}'"
    print("✓ Rolling captions chain simulation passed")

def test_parse_vtt_and_build_clean_full_text():
    print("\nRunning test_parse_vtt_and_build_clean_full_text...")
    importer = YouTubeReferenceImporter()

    # Simulated VTT content representing rolling captions
    vtt_content = """WEBVTT
Kind: captions
Language: pt

00:00:01.000 --> 00:00:03.000
A B C

00:00:02.000 --> 00:00:04.000
B C D

00:00:03.000 --> 00:00:05.000
C D E
"""
    # 1. Test parse_vtt
    parsed_segments = importer.parse_vtt(vtt_content)
    
    # We expect the segments to have been merged into a single segment
    # since they are close in time (1s differences) and have large overlaps.
    assert len(parsed_segments) == 1, f"Expected 1 merged segment, got {len(parsed_segments)}"
    assert parsed_segments[0]["text"] == "A B C D E", f"Expected 'A B C D E', got '{parsed_segments[0]['text']}'"
    assert parsed_segments[0]["start_time"] == 1.0
    assert parsed_segments[0]["end_time"] == 5.0
    print("✓ parse_vtt merging passed")

    # 2. Test build_clean_full_text on raw segments (if we pass them directly)
    # Let's say we have raw segments that were NOT merged yet
    raw_segments = [
        {"segment_index": 0, "start_time": 1.0, "end_time": 3.0, "text": "A B C"},
        {"segment_index": 1, "start_time": 2.0, "end_time": 4.0, "text": "B C D"},
        {"segment_index": 2, "start_time": 3.0, "end_time": 5.0, "text": "C D E"},
    ]
    full_text = importer.build_clean_full_text(raw_segments)
    assert full_text == "A B C D E", f"Expected 'A B C D E', got '{full_text}'"
    print("✓ build_clean_full_text passed")

def test_transcript_versioning():
    print("\nRunning test_transcript_versioning (DB integration)...")
    from src.db.session import SessionLocal
    from src.services.references_service import ReferencesService
    from src.schemas.references import ReferenceSourceCreate, TranscriptCreate
    from src.models.reference import ReferenceSource

    db = SessionLocal()
    service = ReferencesService(db)

    # 1. Create a temporary ReferenceSource
    source_in = ReferenceSourceCreate(
        source_type="manual",
        source_url="https://example.com/test-versioning",
        title="Test Transcript Versioning",
        status="new"
    )
    # Use repo directly to create source
    db_source = service.repo.create_reference_source(source_in)
    source_id = db_source.id
    print(f"Created temp reference source with ID {source_id}")

    try:
        # 2. Add first manual transcript
        payload1 = TranscriptCreate(
            language="pt",
            source_method="manual",
            full_text="Texto da transcrição v1"
        )
        t1 = service.create_manual_transcript(source_id, payload1)
        print(f"Transcript 1 created: ID={t1.id}, version={t1.version_number}, active={t1.is_active}")
        assert t1.version_number == 1
        assert t1.is_active is True
        assert t1.duplicate_of_transcript_id is None

        # 3. Add second manual transcript with different text
        payload2 = TranscriptCreate(
            language="pt",
            source_method="manual",
            full_text="Texto da transcrição v2 (diferente)"
        )
        t2 = service.create_manual_transcript(source_id, payload2)
        print(f"Transcript 2 created: ID={t2.id}, version={t2.version_number}, active={t2.is_active}")
        assert t2.version_number == 2
        assert t2.is_active is True
        assert t2.duplicate_of_transcript_id is None

        # Refresh t1 to see if it was deactivated
        db.refresh(t1)
        assert t1.is_active is False
        print("✓ Transcript 1 successfully deactivated")

        # 4. Add third manual transcript with the SAME text as v1
        payload3 = TranscriptCreate(
            language="pt",
            source_method="manual",
            full_text="Texto da transcrição v1" # Same as t1
        )
        t3 = service.create_manual_transcript(source_id, payload3)
        print(f"Transcript 3 created: ID={t3.id}, version={t3.version_number}, active={t3.is_active}, duplicate_of={t3.duplicate_of_transcript_id}")
        assert t3.version_number == 3
        assert t3.is_active is True
        assert t3.duplicate_of_transcript_id == t1.id

        # Refresh t2 to check if it was deactivated
        db.refresh(t2)
        assert t2.is_active is False
        print("✓ Transcript 2 successfully deactivated")

        # 5. List transcripts for the source and ensure they are all kept and returned
        transcripts = service.get_transcripts_for_source(source_id)
        assert len(transcripts) == 3
        print("✓ All 3 versions are successfully kept in the database")

    finally:
        # Clean up
        print("Cleaning up temp reference source...")
        db.delete(db_source)
        db.commit()
        db.close()
    print("✓ test_transcript_versioning passed")

def test_youtube_url_validation():
    print("\nRunning test_youtube_url_validation...")
    from src.schemas.references import extract_youtube_video_id

    # 1. Valid URLs
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLB03EA954E5E1E8B8"
    ]
    for url in valid_urls:
        video_id = extract_youtube_video_id(url)
        assert video_id == "dQw4w9WgXcQ", f"Expected 'dQw4w9WgXcQ' for {url}, got '{video_id}'"
    print("✓ Valid URLs successfully extracted")

    # 2. Invalid channel/profile URLs
    invalid_channels = [
        "https://www.youtube.com/@GabrielOliv",
        "youtube.com/@SomeUser",
        "https://www.youtube.com/channel/UC_x5XG1OV2P6uYZ5FHSFzFQ",
        "https://www.youtube.com/c/YouTubeBrasil",
        "https://www.youtube.com/user/Google"
    ]
    for url in invalid_channels:
        try:
            extract_youtube_video_id(url)
            assert False, f"Expected ValueError for channel URL: {url}"
        except ValueError as e:
            assert "canais ou perfis" in str(e), f"Unexpected error message: {e}"
    print("✓ Channel URLs successfully rejected")

    # 3. Invalid playlist URLs
    invalid_playlists = [
        "https://www.youtube.com/playlist?list=PLB03EA954E5E1E8B8",
        "youtube.com/playlist?list=PLB03EA954E5E1E8B8"
    ]
    for url in invalid_playlists:
        try:
            extract_youtube_video_id(url)
            assert False, f"Expected ValueError for playlist URL: {url}"
        except ValueError as e:
            assert "playlists" in str(e), f"Unexpected error message: {e}"
    print("✓ Playlist URLs successfully rejected")

if __name__ == "__main__":
    try:
        test_youtube_url_validation()
        test_merge_overlapping_text()
        test_rolling_captions_chain()
        test_parse_vtt_and_build_clean_full_text()
        test_transcript_versioning()
        print("\nAll tests passed successfully!")
    except AssertionError as e:
        print(f"\nAssertion error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        sys.exit(1)
