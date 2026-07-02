"""
ai/rag.py
=========
Pipeline RAG completo — o "cérebro" do FinSight AI Analyst.

Fluxo (3 passos):
  1. RETRIEVE  → vectorstore.search() busca os chunks mais relevantes no pgvector
  2. AUGMENT   → build_context() monta o contexto estruturado com dados de mercado
  3. GENERATE  → llm.get_llm_response() envia pergunta + contexto ao Gemini

Por que fazer na mão (sem LangChain)?
  - ~60 linhas de código vs 600 de abstração
  - Você entende exatamente o que acontece em cada etapa
  - Mais fácil de debugar e customizar para finanças
  - LangChain pode ser adicionado em v2 como refatoração

Uso:
    from ai.rag import answer
    result = answer("Como foi a PETR4 essa semana?", ticker="PETR4.SA")
    print(result["response"])
    print(result["sources"])
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from finsight.db import get_engine
from sqlalchemy import text

from ai.vectorstore import search, RetrievedChunk
from ai.llm import get_llm_response


# =============================================================================
# Tipos de retorno
# =============================================================================

@dataclass
class RagSource:
    """Fonte citada na resposta do RAG."""
    headline: str
    source:   Optional[str]
    url:      Optional[str]
    date:     Optional[str]
    similarity: float


@dataclass
class RagResult:
    """Resultado completo do pipeline RAG."""
    question:    str
    response:    str
    sources:     list[RagSource]
    ticker:      Optional[str]
    chunks_used: int
    has_market_data: bool
    error:       Optional[str] = None


# =============================================================================
# Recuperação de dados de mercado (complementa as notícias)
# =============================================================================

def _get_market_context(ticker: Optional[str]) -> str:
    """
    Busca dados recentes de mercado para enriquecer o contexto.
    Pega os últimos 7 dias de daily_metrics para o ticker selecionado.
    """
    if not ticker:
        return ""

    try:
        engine = get_engine()
        query = text("""
            SELECT
                trade_date,
                close_price,
                daily_return_simple,
                sma_7d,
                sma_30d,
                volatility_30d_pct,
                volume
            FROM public_marts.daily_metrics
            WHERE ticker = :ticker
            ORDER BY trade_date DESC
            LIMIT 7
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker})
            rows = result.fetchall()

        if not rows:
            return ""

        lines = [f"## Recent Market Data for {ticker} (last 7 trading days)"]
        for row in reversed(rows):  # Ordem cronológica
            date, close, ret, sma7, sma30, vol, volume = row
            ret_str  = f"{ret*100:+.2f}%" if ret is not None else "N/A"
            vol_str  = f"{vol:.2f}%" if vol is not None else "N/A"
            sma7_str = f"{sma7:.2f}" if sma7 is not None else "N/A"
            lines.append(
                f"- {date}: Close={close:.2f}, Return={ret_str}, "
                f"SMA7={sma7_str}, Volatility={vol_str}"
            )

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Could not fetch market data for {ticker}: {e}")
        return ""


# =============================================================================
# Montagem do contexto (Augment)
# =============================================================================

def build_context(chunks: list[RetrievedChunk], market_data: str) -> str:
    """
    Monta o contexto estruturado que será injetado no prompt do LLM.

    Estrutura:
      1. Dados de mercado recentes (se disponível)
      2. Notícias relevantes (chunks do pgvector)

    Tokens estimados: ~1.500-2.000 por resposta (bem dentro dos limites do Gemini)
    """
    parts: list[str] = []

    # Seção 1: Dados de mercado
    if market_data:
        parts.append(market_data)

    # Seção 2: Notícias relevantes
    if chunks:
        parts.append("\n## Relevant News Articles")
        seen_headlines: set[str] = set()

        for i, chunk in enumerate(chunks, 1):
            # Evita duplicar a mesma headline
            if chunk.headline in seen_headlines:
                continue
            seen_headlines.add(chunk.headline)

            date_str = chunk.published_at[:10] if chunk.published_at else "unknown date"
            source_str = chunk.source or "Unknown source"
            url_str = f" | URL: {chunk.url}" if chunk.url else ""

            parts.append(
                f"\n[Article {i}] {chunk.headline}\n"
                f"Source: {source_str} | Date: {date_str}{url_str}\n"
                f"Content: {chunk.chunk_text}"
            )

    if not parts:
        return "No relevant data found in the database for this query."

    return "\n".join(parts)


# =============================================================================
# Pipeline principal (Retrieve → Augment → Generate)
# =============================================================================

def answer(
    question: str,
    ticker: Optional[str] = None,
    top_k: int = 6,
    min_similarity: float = 0.2,
) -> RagResult:
    """
    Pipeline RAG completo: pergunta → resposta fundamentada.

    Args:
        question:       Pergunta em linguagem natural (PT ou EN).
        ticker:         Ticker para filtrar notícias e buscar dados de mercado.
                        Ex: "PETR4.SA". None = busca global.
        top_k:          Quantos chunks de notícias usar no contexto.
        min_similarity: Threshold mínimo de similaridade semântica (0-1).

    Returns:
        RagResult com a resposta do LLM e os metadados das fontes.
    """
    logger.info(f"RAG query: '{question}' | ticker={ticker}")

    try:
        # ── STEP 1: RETRIEVE ─────────────────────────────────────────────────
        chunks = search(
            query=question,
            top_k=top_k,
            ticker_filter=ticker,
            min_similarity=min_similarity,
        )

        # Fallback: se filtrou por ticker e não achou nada, busca global
        if not chunks and ticker:
            logger.info(f"No ticker-specific results, falling back to global search")
            chunks = search(query=question, top_k=top_k, min_similarity=min_similarity)

        # ── STEP 2: AUGMENT ──────────────────────────────────────────────────
        market_data = _get_market_context(ticker)
        context = build_context(chunks, market_data)

        # ── STEP 3: GENERATE ─────────────────────────────────────────────────
        response = get_llm_response(question=question, context=context)

        # Monta as fontes para exibir no frontend
        seen: set[str] = set()
        sources: list[RagSource] = []
        for chunk in chunks:
            if chunk.headline not in seen:
                seen.add(chunk.headline)
                sources.append(RagSource(
                    headline=chunk.headline,
                    source=chunk.source,
                    url=chunk.url,
                    date=chunk.published_at[:10] if chunk.published_at else None,
                    similarity=chunk.similarity,
                ))

        logger.info(f"RAG complete: {len(chunks)} chunks → response generated")

        return RagResult(
            question=question,
            response=response,
            sources=sources,
            ticker=ticker,
            chunks_used=len(chunks),
            has_market_data=bool(market_data),
        )

    except Exception as e:
        logger.exception(f"RAG pipeline error: {e}")
        return RagResult(
            question=question,
            response=f"Error processing your question: {str(e)}",
            sources=[],
            ticker=ticker,
            chunks_used=0,
            has_market_data=False,
            error=str(e),
        )


# =============================================================================
# Standalone — teste direto: python ai/rag.py
# =============================================================================

if __name__ == "__main__":
    print("FinSight RAG — Quick Test")
    print("=" * 50)

    test_cases = [
        ("Como foi a Petrobras essa semana?", "PETR4.SA"),
        ("What are the main risks for Brazilian stocks?", None),
        ("Qual o impacto do dólar nas ações brasileiras?", None),
    ]

    for question, ticker in test_cases:
        print(f"\n❓ Question: {question}")
        print(f"   Ticker: {ticker or 'all'}")
        result = answer(question, ticker=ticker)
        print(f"\n💬 Answer:\n{result.response}")
        print(f"\n📰 Sources ({len(result.sources)}):")
        for s in result.sources:
            print(f"   [{s.similarity:.2f}] {s.headline[:80]}")
        print("-" * 50)
