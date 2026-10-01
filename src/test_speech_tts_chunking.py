import pytest

from speech_worker.tts.text_chunking import chunk_text


def test_chunk_text_prefers_sentence_boundaries_and_is_deterministic():
    text = "Primeira frase curta. Segunda frase curta. Terceira frase curta."
    first = chunk_text(text, max_chars=42)
    second = chunk_text(text, max_chars=42)
    assert first == second
    assert " ".join(first) == text
    assert all(len(chunk) <= 42 for chunk in first)


def test_chunk_text_splits_long_clause_by_words_without_losing_content():
    text = "uma dois tres quatro cinco seis sete oito nove dez onze doze"
    chunks = chunk_text(text, max_chars=18)
    assert " ".join(chunks) == text
    assert all(len(chunk) <= 18 for chunk in chunks)


def test_chunk_text_normalizes_whitespace():
    assert chunk_text("  Olá\n\n mundo.   Tudo bem?  ", max_chars=100) == ["Olá mundo. Tudo bem?"]


def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_rejects_non_positive_limit():
    with pytest.raises(ValueError, match="max_chars"):
        chunk_text("texto", max_chars=0)


def test_single_word_larger_than_limit_is_preserved_in_one_chunk():
    word = "supercalifragilisticexpialidocious"
    assert chunk_text(word, max_chars=10) == [word]
