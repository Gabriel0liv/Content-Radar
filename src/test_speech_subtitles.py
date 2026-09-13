from speech_worker.stt.subtitles import (
    format_timestamp,
    group_words_into_cards,
    render_srt,
    render_vtt,
    split_segment_without_words,
)


def test_speaker_change_splits_subtitle_card():
    cards = group_words_into_cards([
        {"word": "olá", "start": 0.0, "end": 0.5, "speaker": "SPEAKER_00"},
        {"word": "mundo", "start": 0.5, "end": 1.0, "speaker": "SPEAKER_00"},
        {"word": "sim", "start": 1.0, "end": 1.3, "speaker": "SPEAKER_01"},
    ])
    assert len(cards) == 2
    assert cards[0]["speaker"] == "SPEAKER_00"
    assert cards[1]["speaker"] == "SPEAKER_01"


def test_silence_gap_splits_subtitle_card():
    cards = group_words_into_cards([
        {"word": "primeiro", "start": 0.0, "end": 0.4, "speaker": None},
        {"word": "depois", "start": 2.1, "end": 2.5, "speaker": None},
    ])
    assert len(cards) == 2


def test_srt_and_vtt_use_expected_timestamp_formats():
    cards = [{"start": 1.25, "end": 2.5, "speaker": None, "lines": ["Teste"]}]
    srt = render_srt(cards, show_speaker=False)
    vtt = render_vtt(cards, show_speaker=False)
    assert "00:00:01,250 --> 00:00:02,500" in srt
    assert vtt.startswith("WEBVTT")
    assert "00:00:01.250 --> 00:00:02.500" in vtt


def test_fallback_segment_without_words_keeps_text_in_readable_cards():
    text = " ".join(["palavra"] * 30)
    cards = split_segment_without_words(text, 0.0, 10.0)
    assert len(cards) > 1
    assert all(len(card["lines"]) <= 2 for card in cards)
    assert all(all(len(line) <= 42 for line in card["lines"]) for card in cards)


def test_timestamp_rounding_handles_millisecond_carry():
    assert format_timestamp(59.9996) == "00:01:00,000"
