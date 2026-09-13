from speech_worker.stt.normalize import normalize_whisperx_result


def test_normalize_preserves_repeated_spoken_text_and_word_timestamps():
    raw = {
        "language": "pt",
        "segments": [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "sim sim",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "sim", "start": 0.0, "end": 0.4, "score": 0.9, "speaker": "SPEAKER_00"},
                    {"word": "sim", "start": 0.5, "end": 0.9, "score": 0.8, "speaker": "SPEAKER_00"},
                ],
            }
        ],
    }
    result = normalize_whisperx_result(raw, model="medium", diarized=True, alignment_used=True)
    assert result.full_text == "sim sim"
    assert [word.word for word in result.segments[0].words] == ["sim", "sim"]
    assert result.segments[0].speaker == "SPEAKER_00"


def test_normalize_does_not_invent_missing_word_times():
    raw = {
        "language": "pt",
        "segments": [{"start": 2.0, "end": 3.0, "text": "teste", "words": [{"word": "teste"}]}],
    }
    result = normalize_whisperx_result(raw, model="small", diarized=False, alignment_used=False)
    assert result.segments[0].words[0].start is None
    assert result.segments[0].words[0].end is None


def test_unknown_speaker_becomes_none_in_canonical_data():
    raw = {"segments": [{"start": 0, "end": 1, "text": "fala", "speaker": "UNKNOWN"}]}
    result = normalize_whisperx_result(raw, model="small", diarized=False, alignment_used=False)
    assert result.segments[0].speaker is None


def test_segments_are_ordered_by_start_time_with_stable_ties():
    raw = {
        "segments": [
            {"start": 2.0, "end": 3.0, "text": "terceiro"},
            {"start": 1.0, "end": 1.5, "text": "primeiro"},
            {"start": 1.0, "end": 1.7, "text": "segundo"},
        ]
    }
    result = normalize_whisperx_result(raw, model="small", diarized=False, alignment_used=False)
    assert [segment.text for segment in result.segments] == ["primeiro", "segundo", "terceiro"]
