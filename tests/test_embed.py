"""
tests/test_embed.py
===================
Unit tests for ai/embed.py.

Covers the pure functions chunk_text() and _vec_to_pg().
These tests run without a database or ML model — no external deps.

Run:
    pytest tests/test_embed.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.embed import chunk_text, _vec_to_pg


# =============================================================================
# chunk_text
# =============================================================================

class TestChunkText:
    def test_empty_string_returns_empty_list(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_text("   \n  ") == []

    def test_short_text_returns_single_chunk(self):
        text = "Petrobras reported record profits this quarter."
        result = chunk_text(text, size=512, overlap=50)
        assert len(result) == 1
        assert result[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        # Cria um texto com frases longas que excedem size=100
        sentence = "This is a long sentence about the Brazilian stock market. "
        text = sentence * 10  # ~560 chars
        result = chunk_text(text, size=100, overlap=20)
        assert len(result) > 1

    def test_chunks_are_non_empty_strings(self):
        text = "Vale posted strong earnings. Iron ore prices surged. Investors reacted positively."
        result = chunk_text(text, size=50, overlap=10)
        assert all(isinstance(c, str) and c.strip() for c in result)

    def test_chunk_size_respected(self):
        # Nenhum chunk deve ultrapassar size + tamanho de uma sentença (heurístico)
        text = "Short. " * 100  # 700 chars de sentenças curtas
        size = 50
        result = chunk_text(text, size=size, overlap=10)
        # Com overlap, o tamanho pode crescer um pouco, mas não deve explodir
        for chunk in result:
            assert len(chunk) <= size * 3  # margem razoável por overlap

    def test_fallback_returns_text_slice_when_no_sentences(self):
        # Texto sem pontuação (sem split por sentença) → deve retornar ao menos 1 chunk
        text = "a" * 600
        result = chunk_text(text, size=512)
        assert len(result) >= 1

    def test_single_long_sentence_does_not_crash(self):
        text = "word " * 200  # 1000 chars, sem pontuação final
        result = chunk_text(text, size=100, overlap=20)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_overlap_zero_still_works(self):
        sentence = "Sentence about VALE. " * 10
        result = chunk_text(sentence, size=60, overlap=0)
        assert len(result) >= 1
        assert all(c.strip() for c in result)

    def test_preserves_content(self):
        """Garante que nenhuma palavra se perde entre os chunks."""
        text = "Alpha. Beta. Gamma. Delta. Epsilon."
        result = chunk_text(text, size=20, overlap=0)
        combined = " ".join(result)
        for word in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]:
            assert word in combined


# =============================================================================
# _vec_to_pg
# =============================================================================

class TestVecToPg:
    def test_returns_string(self):
        result = _vec_to_pg([0.1, 0.2, 0.3])
        assert isinstance(result, str)

    def test_correct_bracket_format(self):
        result = _vec_to_pg([0.1, 0.5, 0.9])
        assert result.startswith("[")
        assert result.endswith("]")

    def test_values_are_comma_separated(self):
        result = _vec_to_pg([1.0, 2.0, 3.0])
        inner = result[1:-1]
        parts = inner.split(",")
        assert len(parts) == 3

    def test_six_decimal_places(self):
        result = _vec_to_pg([0.123456789])
        # Deve ter 6 casas decimais
        inner = result[1:-1]
        _, decimals = inner.split(".")
        assert len(decimals) == 6

    def test_empty_vector(self):
        result = _vec_to_pg([])
        assert result == "[]"

    def test_large_vector_length(self):
        vec = [0.5] * 384  # dimensão padrão do all-MiniLM-L6-v2
        result = _vec_to_pg(vec)
        inner = result[1:-1]
        parts = inner.split(",")
        assert len(parts) == 384

    def test_negative_values(self):
        result = _vec_to_pg([-0.5, -0.1, 0.9])
        assert "-0.500000" in result
        assert "-0.100000" in result

    def test_zero_value(self):
        result = _vec_to_pg([0.0])
        assert "0.000000" in result
