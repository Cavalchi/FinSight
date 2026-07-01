"""
ai/embed.py
===========
Gera embeddings semânticos das notícias e salva no pgvector.

Fluxo:
  1. Busca notícias com is_embedded = FALSE
  2. Para cada notícia: headline + summary → chunks de texto
  3. Gera vetor 384d com sentence-transformers (local, sem custo de API)
  4. Insere em news_embeddings
  5. Marca raw_news.is_embedded = TRUE

Modelo: all-MiniLM-L6-v2 (80MB, download automático na primeira execução)
Dimensão: 384 → corresponde à coluna `embedding vector(384)` no banco

Roda standalone:
  python ai/embed.py
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from finsight.db import get_raw_connection

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE:      int  = int(os.getenv("RAG_CHUNK_SIZE", "512"))
CHUNK_OVERLAP:   int  = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))


# =============================================================================
# Chunking
# =============================================================================

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Quebra texto em chunks com overlap.

    Overlap evita perder contexto na fronteira entre chunks.
    Ex: tamanho 512, overlap 50 → cada chunk "compartilha" 50 chars com o próximo.
    """
    if not text or not text.strip():
        return []

    # Split em sentenças (heurística simples por pontuação)
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= size:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current.strip())
            # Overlap: pega o final do chunk anterior
            if overlap > 0 and current:
                tail = current[-overlap:]
                current = tail + " " + sentence
            else:
                current = sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks or [text[:size]]


# =============================================================================
# Embedding principal
# =============================================================================

def _vec_to_pg(vec: list[float]) -> str:
    """Converte lista de floats para formato pgvector: '[0.1,0.2,...]'"""
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def embed_pending_news(batch_size: int = 100) -> int:
    """
    Processa notícias pendentes (is_embedded=FALSE) e gera seus embeddings.

    Args:
        batch_size: Quantas notícias processar por execução (evita timeout no Airflow).

    Returns:
        Número de embeddings criados.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers not installed.\n"
            "Run: pip install sentence-transformers"
        )

    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Busca notícias pendentes
    with get_raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, headline, COALESCE(summary, ''), source, published_at
                FROM raw_news
                WHERE is_embedded = FALSE
                ORDER BY published_at DESC NULLS LAST
                LIMIT %s
            """, (batch_size,))
            pending = cur.fetchall()

    if not pending:
        logger.info("No pending news to embed.")
        return 0

    logger.info(f"Embedding {len(pending)} news articles...")
    total_chunks = 0

    for news_id, headline, summary, source, published_at in pending:
        # Monta texto completo: headline tem mais peso (repetida)
        full_text = f"{headline}. {headline}. {summary}".strip()
        chunks = chunk_text(full_text)

        if not chunks:
            logger.warning(f"  Skipping news_id={news_id}: empty text")
            continue

        # Gera embeddings para todos os chunks de uma vez (batch eficiente)
        embeddings = model.encode(chunks, batch_size=32, show_progress_bar=False)

        with get_raw_connection() as conn:
            with conn.cursor() as cur:
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    vec_str = _vec_to_pg(embedding.tolist())
                    cur.execute("""
                        INSERT INTO news_embeddings
                            (news_id, chunk_index, chunk_text, embedding, model_name)
                        VALUES (%s, %s, %s, %s::vector, %s)
                        ON CONFLICT (news_id, chunk_index) DO NOTHING
                    """, (news_id, i, chunk, vec_str, EMBEDDING_MODEL))

                # Marca como embedded
                cur.execute(
                    "UPDATE raw_news SET is_embedded = TRUE WHERE id = %s",
                    (news_id,)
                )
            conn.commit()

        total_chunks += len(chunks)
        logger.debug(f"  news_id={news_id}: {len(chunks)} chunk(s) embedded")

    logger.info(f"✅ Done. {total_chunks} embeddings created for {len(pending)} articles.")
    return total_chunks


# =============================================================================
# Standalone
# =============================================================================

if __name__ == "__main__":
    from finsight.db import healthcheck
    healthcheck()
    total = embed_pending_news()
    print(f"\n✅ Total embeddings created: {total}")
