-- =============================================================================
-- FinSight — Script de Inicialização do Banco de Dados
-- =============================================================================
-- Este script roda AUTOMATICAMENTE na primeira vez que o container Postgres
-- é iniciado (via docker-entrypoint-initdb.d/).
--
-- Responsabilidades:
--   1. Cria o banco de metadados do Airflow
--   2. Cria o banco principal do FinSight (já definido via POSTGRES_DB)
--   3. Ativa a extensão pgvector no banco do FinSight
--   4. Cria as tabelas raw (dados brutos de ingestão)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Banco de Metadados do Airflow
-- O Airflow precisa de um banco separado para guardar DAGs, execuções, logs, etc.
-- -----------------------------------------------------------------------------
-- Cria o banco do Airflow se ainda não existir
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

-- Cria usuário dedicado ao Airflow
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'airflow') THEN
        CREATE ROLE airflow LOGIN PASSWORD 'airflow';
    END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;

-- Garante permissões no schema public do banco airflow
-- (necessário para o Airflow criar suas tabelas de metadados)
\connect airflow;
GRANT ALL ON SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow;
\connect finsight;


-- -----------------------------------------------------------------------------
-- Banco Principal do FinSight
-- A partir daqui, todas as operações são no banco 'finsight'
-- -----------------------------------------------------------------------------
\connect finsight;


-- Ativa a extensão de vetores (pgvector)
-- OBRIGATÓRIO para a Fase 5 (RAG / busca semântica)
CREATE EXTENSION IF NOT EXISTS vector;

-- Ativa extensão de UUID (útil para chaves primárias)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- =============================================================================
-- SCHEMA: raw — Dados brutos, como chegam da fonte, sem transformação
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela: raw_prices
-- Armazena cotações diárias brutas obtidas via yfinance.
-- A Fase 2 (dbt) vai limpar e transformar esses dados.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_prices (
    id              BIGSERIAL PRIMARY KEY,
    ticker          VARCHAR(20)     NOT NULL,               -- Ex: PETR4.SA
    trade_date      DATE            NOT NULL,               -- Data do pregão
    open_price      NUMERIC(12, 4)  NOT NULL,               -- Preço de abertura
    high_price      NUMERIC(12, 4)  NOT NULL,               -- Máxima do dia
    low_price       NUMERIC(12, 4)  NOT NULL,               -- Mínima do dia
    close_price     NUMERIC(12, 4)  NOT NULL,               -- Preço de fechamento
    adj_close_price NUMERIC(12, 4),                         -- Fechamento ajustado por dividendos
    volume          BIGINT,                                 -- Volume negociado
    source          VARCHAR(50)     NOT NULL DEFAULT 'yfinance',  -- Fonte do dado
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(), -- Timestamp de ingestão

    -- Garante que não inserimos o mesmo ticker + data duas vezes
    CONSTRAINT uq_raw_prices_ticker_date UNIQUE (ticker, trade_date)
);

COMMENT ON TABLE raw_prices IS
    'Cotações diárias brutas obtidas via yfinance. Dados não transformados — use daily_metrics para análise.';

COMMENT ON COLUMN raw_prices.adj_close_price IS
    'Fechamento ajustado por dividendos e splits. Use este campo para cálculos de retorno.';


-- -----------------------------------------------------------------------------
-- Tabela: raw_news
-- Armazena notícias brutas obtidas via Finnhub ou RSS.
-- A Fase 5 (RAG) vai gerar embeddings dessas notícias.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_news (
    id              BIGSERIAL PRIMARY KEY,
    external_id     TEXT,                                   -- ID único da notícia na fonte (URLs RSS podem ser longas)
    headline        TEXT            NOT NULL,               -- Título da notícia
    summary         TEXT,                                   -- Resumo / corpo da notícia
    source          VARCHAR(100),                           -- Veículo (ex: Reuters, Bloomberg)
    url             TEXT,                                   -- Link para a notícia original
    related_tickers TEXT[],                                 -- Tickers mencionados (array)
    published_at    TIMESTAMPTZ,                            -- Data/hora de publicação
    category        VARCHAR(50),                            -- Categoria (ex: earnings, macro)
    api_source      VARCHAR(50)     NOT NULL DEFAULT 'finnhub', -- Qual API forneceu
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(), -- Timestamp de ingestão
    is_embedded     BOOLEAN         NOT NULL DEFAULT FALSE, -- Flag: já gerou embedding?

    -- Evita duplicatas pela combinação de fonte + ID externo
    CONSTRAINT uq_raw_news_source_external_id UNIQUE (api_source, external_id)
);

COMMENT ON TABLE raw_news IS
    'Notícias financeiras brutas. O campo is_embedded indica se o embedding já foi gerado para o RAG.';

COMMENT ON COLUMN raw_news.related_tickers IS
    'Array de tickers relacionados à notícia (ex: {PETR4.SA, VALE3.SA}). Indexado para buscas.';

COMMENT ON COLUMN raw_news.is_embedded IS
    'Flag de controle: FALSE = ainda não processado pelo embed.py, TRUE = embedding gerado e salvo no pgvector.';


-- =============================================================================
-- SCHEMA: vectors — Embeddings gerados pelo módulo ai/embed.py
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela: news_embeddings
-- Armazena os vetores semânticos das notícias para busca por similaridade.
-- Criada aqui para garantir que a extensão vector está ativa antes.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS news_embeddings (
    id              BIGSERIAL PRIMARY KEY,
    news_id         BIGINT          NOT NULL REFERENCES raw_news(id) ON DELETE CASCADE,
    chunk_index     INTEGER         NOT NULL DEFAULT 0,     -- Índice do chunk (notícias longas são quebradas)
    chunk_text      TEXT            NOT NULL,               -- Texto do chunk que gerou o embedding
    embedding       vector(384),                            -- Vetor de 384 dimensões (all-MiniLM-L6-v2)
    model_name      VARCHAR(100)    NOT NULL,               -- Modelo que gerou o embedding
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_news_chunk UNIQUE (news_id, chunk_index)
);

COMMENT ON TABLE news_embeddings IS
    'Embeddings vetoriais das notícias para busca semântica (RAG). Dimensão 384 = modelo all-MiniLM-L6-v2.';

-- Índice HNSW para busca aproximada de vizinhos (ANN) — muito mais rápido que busca exata
-- operator class: vector_cosine_ops = usamos distância de cosseno (padrão para embeddings de texto)
CREATE INDEX IF NOT EXISTS idx_news_embeddings_hnsw
    ON news_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_news_embeddings_hnsw IS
    'Índice HNSW para busca semântica eficiente. m=16 e ef_construction=64 são bons valores default.';


-- =============================================================================
-- Índices auxiliares para performance
-- =============================================================================

-- raw_prices: buscas por ticker e por data são as mais comuns
CREATE INDEX IF NOT EXISTS idx_raw_prices_ticker      ON raw_prices (ticker);
CREATE INDEX IF NOT EXISTS idx_raw_prices_trade_date  ON raw_prices (trade_date DESC);

-- raw_news: buscas por data e por tickers relacionados
CREATE INDEX IF NOT EXISTS idx_raw_news_published_at  ON raw_news (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_news_is_embedded   ON raw_news (is_embedded) WHERE is_embedded = FALSE;
CREATE INDEX IF NOT EXISTS idx_raw_news_tickers       ON raw_news USING GIN (related_tickers);


-- =============================================================================
-- Mensagem de confirmação
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ FinSight DB initialized successfully!';
    RAISE NOTICE '   → Extension vector: ACTIVE';
    RAISE NOTICE '   → Tables: raw_prices, raw_news, news_embeddings';
    RAISE NOTICE '   → Airflow database: CREATED';
END $$;
