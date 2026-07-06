"""
finsight/db.py
==============
M├│dulo central de conex├úo com o banco de dados.

Fornece:
  - engine()       ÔåÆ SQLAlchemy Engine (para pandas, dbt, scripts)
  - get_connection()  ÔåÆ context manager com psycopg2 puro (para INSERTs em massa)
  - healthcheck()  ÔåÆ verifica se o banco est├í acess├¡vel

Design:
  Usa vari├íveis de ambiente (.env) carregadas via python-dotenv.
  O engine ├® criado uma vez (singleton) e reutilizado entre chamadas.
  Em caso de falha, usa tenacity para retry autom├ítico com backoff exponencial.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

import psycopg2
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from tenacity import retry, stop_after_attempt, wait_exponential

# Carrega vari├íveis do .env (sem efeito se j├í estiverem no ambiente, ex: dentro do Docker)
load_dotenv()


# =============================================================================
# Configura├º├úo
# =============================================================================

def _build_database_url() -> str:
    """
    Monta a URL de conex├úo a partir das vari├íveis de ambiente.

    Prioridade:
      1. DATABASE_URL (vari├ível completa, usada dentro do Docker)
      2. Vari├íveis individuais POSTGRES_* (usadas em desenvolvimento local)
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user     = os.getenv("POSTGRES_USER", "finsight")
    password = os.getenv("POSTGRES_PASSWORD", "finsight123")
    host     = os.getenv("POSTGRES_HOST", "localhost")
    port     = os.getenv("POSTGRES_PORT", "5432")
    db       = os.getenv("POSTGRES_DB", "finsight")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


# =============================================================================
# Engine SQLAlchemy (singleton ÔÇö criado uma vez por processo)
# =============================================================================

@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Retorna o SQLAlchemy Engine singleton.

    O @lru_cache garante que o engine ├® criado uma ├║nica vez e reutilizado
    em todas as chamadas subsequentes dentro do mesmo processo Python.

    Returns:
        Engine: inst├óncia configurada do SQLAlchemy.

    Example:
        engine = get_engine()
        df.to_sql("my_table", engine, if_exists="append", index=False)
    """
    url = _build_database_url()
    logger.debug(f"Creating SQLAlchemy engine for: {url.split('@')[-1]}")  # N├úo loga senha

    return create_engine(
        url,
        pool_size=5,          # Conex├Áes mantidas no pool
        max_overflow=10,      # Conex├Áes extras em pico de carga
        pool_pre_ping=True,   # Testa conex├úo antes de usar (evita "connection closed" silencioso)
        echo=False,           # True = loga todas as queries (├║til para debug, verboso demais em prod)
    )


# =============================================================================
# Context Manager com psycopg2 puro (para INSERTs em massa com execute_values)
# =============================================================================

@contextmanager
def get_raw_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager que fornece uma conex├úo psycopg2 pura.

    Use quando precisar de performance m├íxima em INSERTs em massa
    (execute_values ├® ~10x mais r├ípido que INSERT row a row).

    Usage:
        with get_raw_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, "INSERT INTO ...", data)
            conn.commit()

    O commit ├® feito manualmente. Em caso de exce├º├úo, o rollback ├® autom├ítico.
    """
    url = _build_database_url()
    # Remove o prefixo "postgresql+psycopg2://" que o psycopg2 n├úo entende
    dsn = url.replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(dsn)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# Healthcheck
# =============================================================================

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def healthcheck() -> bool:
    """
    Verifica se o banco de dados est├í acess├¡vel.

    Usa retry autom├ítico (at├® 5 tentativas, backoff exponencial 2s ÔåÆ 30s).
    ├Ütil para aguardar o Postgres iniciar antes de rodar scripts de ingest├úo.

    Returns:
        True se a conex├úo for bem-sucedida.

    Raises:
        Exception: se todas as tentativas falharem.

    Example:
        from finsight.db import healthcheck
        healthcheck()  # lan├ºa exce├º├úo se o banco estiver fora do ar
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1, "Healthcheck query returned unexpected result"

    logger.info("Ô£à Database connection: OK")
    return True


# =============================================================================
# Utilit├írio: garante que as extens├Áes necess├írias est├úo ativas
# =============================================================================

def ensure_extensions() -> None:
    """
    Garante que as extens├Áes PostgreSQL necess├írias est├úo instaladas.

    Em produ├º├úo, o script SQL de inicializa├º├úo j├í faz isso.
    Este m├®todo ├® um fallback para ambientes de teste ou dev manual.
    """
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    logger.info("Ô£à PostgreSQL extensions: vector, uuid-ossp ÔÇö active")


if __name__ == "__main__":
    # Execu├º├úo direta: python -m finsight.db
    # ├Ütil para testar a conex├úo rapidamente
    healthcheck()
    ensure_extensions()
