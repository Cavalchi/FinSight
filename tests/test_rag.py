"""
tests/test_rag.py
=================
Unit tests for ai/rag.py.

Covers:
  - build_context(): monta o contexto a partir de chunks e dados de mercado
  - RagResult / RagSource: dataclasses de retorno
  - answer(): pipeline completo, usando mocks para DB e LLM

Run:
    pytest tests/test_rag.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.rag import build_context, RagResult, RagSource
from ai.vectorstore import RetrievedChunk


# =============================================================================
# Fixtures
# =============================================================================

def make_chunk(
    headline="PETR4 sobe 3% após resultado",
    chunk_text="Petrobras reportou lucro recorde.",
    source="Reuters",
    published_at="2024-06-01T10:00:00",
    url="https://reuters.com/petro",
    similarity=0.85,
    related_tickers=None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_text=chunk_text,
        headline=headline,
        source=source,
        published_at=published_at,
        url=url,
        similarity=similarity,
        related_tickers=related_tickers or ["PETR4.SA"],
    )


# =============================================================================
# build_context
# =============================================================================

class TestBuildContext:
    def test_no_chunks_no_market_returns_fallback(self):
        result = build_context([], "")
        assert "No relevant data" in result

    def test_with_market_data_includes_it(self):
        market = "## Recent Market Data for PETR4.SA\n- 2024-06-01: Close=38.50"
        result = build_context([], market)
        assert "Market Data" in result
        assert "38.50" in result

    def test_with_chunks_includes_headline(self):
        chunk = make_chunk(headline="Vale anuncia dividendos")
        result = build_context([chunk], "")
        assert "Vale anuncia dividendos" in result

    def test_with_chunks_includes_source(self):
        chunk = make_chunk(source="Bloomberg")
        result = build_context([chunk], "")
        assert "Bloomberg" in result

    def test_with_chunks_includes_chunk_text(self):
        chunk = make_chunk(chunk_text="Resultado acima do esperado pelo mercado.")
        result = build_context([chunk], "")
        assert "Resultado acima do esperado pelo mercado." in result

    def test_deduplicates_same_headline(self):
        """Dois chunks com a mesma headline devem aparecer só uma vez."""
        chunk_a = make_chunk(headline="PETR4 alta", chunk_text="Texto A")
        chunk_b = make_chunk(headline="PETR4 alta", chunk_text="Texto B")
        result = build_context([chunk_a, chunk_b], "")
        assert result.count("PETR4 alta") == 1

    def test_different_headlines_both_appear(self):
        chunk_a = make_chunk(headline="PETR4 sobe")
        chunk_b = make_chunk(headline="VALE3 cai")
        result = build_context([chunk_a, chunk_b], "")
        assert "PETR4 sobe" in result
        assert "VALE3 cai" in result

    def test_date_formatted_as_date_only(self):
        chunk = make_chunk(published_at="2024-06-15T09:30:00")
        result = build_context([chunk], "")
        # Deve mostrar apenas a data, não o timestamp completo
        assert "2024-06-15" in result
        assert "09:30:00" not in result

    def test_url_included_when_present(self):
        chunk = make_chunk(url="https://example.com/news")
        result = build_context([chunk], "")
        assert "https://example.com/news" in result

    def test_url_omitted_when_none(self):
        chunk = make_chunk(url=None)
        result = build_context([chunk], "")
        assert "URL:" not in result

    def test_market_data_comes_before_news(self):
        market = "## Recent Market Data"
        chunk = make_chunk()
        result = build_context([chunk], market)
        market_pos = result.find("Market Data")
        news_pos = result.find("Relevant News")
        assert market_pos < news_pos

    def test_no_market_data_empty_string(self):
        chunk = make_chunk()
        result = build_context([chunk], "")
        assert "Market Data" not in result


# =============================================================================
# RagSource e RagResult dataclasses
# =============================================================================

class TestRagDataclasses:
    def test_rag_source_fields(self):
        src = RagSource(
            headline="Test headline",
            source="Reuters",
            url="https://test.com",
            date="2024-06-01",
            similarity=0.9,
        )
        assert src.headline == "Test headline"
        assert src.similarity == 0.9

    def test_rag_result_error_defaults_to_none(self):
        result = RagResult(
            question="Como foi a PETR4?",
            response="Petrobras subiu 2%.",
            sources=[],
            ticker="PETR4.SA",
            chunks_used=3,
            has_market_data=True,
        )
        assert result.error is None

    def test_rag_result_with_error(self):
        result = RagResult(
            question="Teste",
            response="Error processing your question: timeout",
            sources=[],
            ticker=None,
            chunks_used=0,
            has_market_data=False,
            error="timeout",
        )
        assert result.error == "timeout"
        assert result.chunks_used == 0
        assert result.has_market_data is False

    def test_rag_result_sources_list(self):
        sources = [
            RagSource(headline="H1", source="S1", url=None, date="2024-06-01", similarity=0.8),
            RagSource(headline="H2", source="S2", url=None, date="2024-06-02", similarity=0.7),
        ]
        result = RagResult(
            question="q",
            response="r",
            sources=sources,
            ticker="PETR4.SA",
            chunks_used=2,
            has_market_data=False,
        )
        assert len(result.sources) == 2
        assert result.sources[0].headline == "H1"


# =============================================================================
# answer() — pipeline completo com mocks
# =============================================================================

class TestAnswerPipeline:
    @patch("ai.rag.get_llm_response", return_value="Petrobras subiu 2% na semana.")
    @patch("ai.rag.search", return_value=[])
    @patch("ai.rag._get_market_context", return_value="")
    def test_answer_returns_rag_result(self, mock_market, mock_search, mock_llm):
        from ai.rag import answer
        result = answer("Como foi a PETR4?", ticker="PETR4.SA")
        assert isinstance(result, RagResult)
        assert result.response == "Petrobras subiu 2% na semana."
        assert result.question == "Como foi a PETR4?"

    @patch("ai.rag.get_llm_response", return_value="Análise geral do mercado.")
    @patch("ai.rag.search", return_value=[make_chunk()])
    @patch("ai.rag._get_market_context", return_value="")
    def test_answer_counts_chunks(self, mock_market, mock_search, mock_llm):
        from ai.rag import answer
        result = answer("Mercado hoje?")
        assert result.chunks_used == 1

    @patch("ai.rag.get_llm_response", side_effect=Exception("LLM timeout"))
    @patch("ai.rag.search", return_value=[])
    @patch("ai.rag._get_market_context", return_value="")
    def test_answer_handles_llm_error_gracefully(self, mock_market, mock_search, mock_llm):
        from ai.rag import answer
        result = answer("Pergunta qualquer?")
        assert result.error is not None
        assert "LLM timeout" in result.error
        assert result.chunks_used == 0

    @patch("ai.rag.get_llm_response", return_value="Resposta global.")
    @patch("ai.rag.search")
    @patch("ai.rag._get_market_context", return_value="")
    def test_answer_fallback_to_global_when_ticker_empty(
        self, mock_market, mock_search, mock_llm
    ):
        """Se ticker filter não achar nada, deve chamar search sem filter (fallback)."""
        # Primeira call (com ticker) retorna vazio, segunda (global) retorna chunk
        mock_search.side_effect = [[], [make_chunk()]]
        from ai.rag import answer
        result = answer("Petrobras essa semana?", ticker="PETR4.SA")
        assert mock_search.call_count == 2
        assert result.chunks_used == 1

    @patch("ai.rag.get_llm_response", return_value="OK")
    @patch("ai.rag.search", return_value=[make_chunk()])
    @patch("ai.rag._get_market_context", return_value="## Market Data\n- 2024-06-01")
    def test_answer_has_market_data_true_when_present(
        self, mock_market, mock_search, mock_llm
    ):
        from ai.rag import answer
        result = answer("Análise PETR4", ticker="PETR4.SA")
        assert result.has_market_data is True
