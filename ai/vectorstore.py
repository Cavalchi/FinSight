"""
ai/vectorstore.py
=================
Busca semântica no pgvector — o "retrieval" do RAG.

Dado uma pergunta em linguagem natural:
  1. Gera o embedding da pergunta (mesmo modelo usado na ingestão)
  2. Busca os N chunks mais próximos por similaridade de cosseno
  3. Retorna os chunks com metadados (headline, source, published_at)

Por que similaridade de cosseno?
  - Mede o ângulo entre dois vetores, não a distância euclidiana
  - Independente do comprimento do texto — ideal para frases e parágrafos
  - Padrão da indústria para busca semântica em textos

O operador `<=>` no pgvector calcula a distância de cosseno:
  distância = 1 - similaridade
  → valores menores = mais similar

Uso:
    from ai.vectorstore import search
    results = search("volatilidade da PETR4 essa semana", top_k=5)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from finsight.db import get_raw_connection

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
TOP_K:           int  = int(os.getenv("RAG_TOP_K_RESULTS", "5"))


@dataclass
class RetrievedChunk:
    """Um chunk recuperado pelo retrieval, com seus metadados."""
    chunk_text:   str
    headline:     str
    source:       Optional[str]
    published_at: Optional[str]
    url:          Optional[str]
    similarity:   float          # 0.0 a 1.0 (maior = mais relevante)
    related_tickers: list[str]


def _vec_to_pg(vec: list[float]) -> str:
    """Converte lista de floats para string pgvector."""
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def search(
    query: str,
    top_k: int = TOP_K,
    ticker_filter: Optional[str] = None,
    min_similarity: float = 0.2,
) -> list[RetrievedChunk]:
    """
    Busca semântica: retorna os chunks mais relevantes para a query.

    Args:
        query:          Texto da pergunta do usuário.
        top_k:          Quantos chunks retornar.
        ticker_filter:  Se fornecido, filtra notícias relacionadas ao ticker.
        min_similarity: Filtra resultados abaixo desta similaridade.

    Returns:
        Lista de RetrievedChunk, ordenada por similaridade decrescente.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")

    # Gera embedding da query
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_vec = model.encode(query).tolist()
    vec_str = _vec_to_pg(query_vec)

    logger.info(f"Searching vectorstore: query='{query[:60]}…' top_k={top_k}")

    # Busca por similaridade de cosseno no pgvector
    # O operador <=> é distância de cosseno (0=idêntico, 2=oposto)
    # Similaridade = 1 - distância
    sql = """
        SELECT
            ne.chunk_text,
            rn.headline,
            rn.source,
            rn.published_at::text,
            rn.url,
            rn.related_tickers,
            1 - (ne.embedding <=> %(vec)s::vector) AS similarity
        FROM news_embeddings ne
        JOIN raw_news rn ON ne.news_id = rn.id
        {ticker_clause}
        ORDER BY ne.embedding <=> %(vec)s::vector
        LIMIT %(top_k)s
    """

    ticker_clause = ""
    if ticker_filter:
        ticker_clause = f"WHERE %(ticker)s = ANY(rn.related_tickers)"

    sql = sql.format(ticker_clause=ticker_clause)

    params: dict = {"vec": vec_str, "top_k": top_k}
    if ticker_filter:
        params["ticker"] = ticker_filter

    with get_raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    results = []
    for chunk_text, headline, source, published_at, url, related_tickers, similarity in rows:
        if similarity < min_similarity:
            continue
        results.append(RetrievedChunk(
            chunk_text=chunk_text,
            headline=headline,
            source=source,
            published_at=published_at,
            url=url,
            similarity=round(float(similarity), 4),
            related_tickers=related_tickers or [],
        ))

    logger.info(f"  Found {len(results)} relevant chunks (threshold={min_similarity})")
    return results


if __name__ == "__main__":
    results = search("Petrobras performance this week", top_k=3)
    for r in results:
        print(f"\n[{r.similarity:.2f}] {r.headline}")
        print(f"  Source: {r.source} | {r.published_at}")
        print(f"  Chunk: {r.chunk_text[:150]}...")
