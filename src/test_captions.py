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

if __name__ == "__main__":
    try:
        test_merge_overlapping_text()
        test_rolling_captions_chain()
        test_parse_vtt_and_build_clean_full_text()
        print("\nAll tests passed successfully!")
    except AssertionError as e:
        print(f"\nAssertion error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        sys.exit(1)
