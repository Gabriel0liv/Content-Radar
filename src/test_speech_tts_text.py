from speech_worker.tts.ptbr_text import analyze_ptbr_text, normalize_ptbr_text


def test_analysis_is_advisory_and_does_not_rewrite_text():
    text = "Ola, voce pode fazer a transcricao deste audio?"
    report = analyze_ptbr_text(text)
    assert report["original_text"] == text
    assert report["normalized_text"] == text
    assert report["has_issues"] is True
    suggestions = {(item["original"], item["suggested"]) for item in report["suggestions"]}
    assert ("ola", "Olá") in suggestions
    assert ("voce", "você") in suggestions
    assert ("transcricao", "transcrição") in suggestions
    assert ("audio", "áudio") in suggestions


def test_normalization_only_applies_known_conservative_whole_word_fixes():
    text = "Ola voce nao viu o audio da transcricao."
    normalized = normalize_ptbr_text(text)
    assert normalized == "Olá você não viu o áudio da transcrição."


def test_normalization_preserves_unknown_words_and_basic_casing():
    text = "DRATHOS e AUDIO; Video, videos, próprio."
    normalized = normalize_ptbr_text(text)
    assert normalized.startswith("DRATHOS e ÁUDIO")
    assert "Vídeo" in normalized
    assert "vídeos" in normalized
    assert "próprio" in normalized


def test_empty_text_analysis_is_clean():
    report = analyze_ptbr_text("   ")
    assert report["has_issues"] is False
    assert report["suggestions"] == []
    assert report["warnings"] == []


def test_analysis_detects_long_unpunctuated_text_without_modifying_it():
    text = " ".join(["palavra"] * 25)
    report = analyze_ptbr_text(text)
    assert report["has_issues"] is True
    assert any("pontua" in warning.lower() for warning in report["warnings"])
    assert report["normalized_text"] == text
