"""
dags/financial_pipeline_dag.py
===============================
DAG principal do FinSight — orquestra todo o pipeline de dados diário.

Fluxo de tarefas (em ordem):
  1. healthcheck          → garante que o banco está acessível
  2. ingest_prices        → baixa cotações do dia via yfinance
  3. ingest_news          → puxa notícias das últimas 24h
  4. dbt_run              → executa os modelos dbt (staging + marts)
  5. dbt_test             → valida qualidade dos dados transformados
  6. embed_news           → gera embeddings das novas notícias (Fase 5)
  [futuro] notify_slack   → envia resumo do dia no Slack

Agendamento: todo dia útil às 17h00 BRT (20h00 UTC — pega dados do dia anterior).

Configurações importantes:
  - catchup=False: não re-executa dias passados em caso de downtime
  - max_active_runs=1: garante que apenas um pipeline roda por vez
  - retry_delay: 5 minutos entre tentativas (evita spam em falhas)

Documentação do Airflow: https://airflow.apache.org/docs/
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# Adiciona o diretório raiz do projeto ao path para importar módulos locais
# O volume ./finsight é montado em /opt/airflow/finsight no container
FINSIGHT_ROOT = "/opt/airflow/finsight"
if FINSIGHT_ROOT not in sys.path:
    sys.path.insert(0, FINSIGHT_ROOT)


# =============================================================================
# Configurações padrão de todas as tasks
# =============================================================================

DEFAULT_ARGS = {
    "owner": "finsight",
    "depends_on_past": False,          # Não depende do run anterior para iniciar
    "email_on_failure": False,         # Desabilitado (sem SMTP configurado)
    "email_on_retry": False,
    "retries": 2,                      # Até 2 tentativas em caso de falha
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),  # Mata task que travar por >1h
}


# =============================================================================
# Definição da DAG
# =============================================================================

with DAG(
    dag_id="financial_pipeline",
    description=(
        "Daily pipeline: ingest prices & news → dbt transform → "
        "generate embeddings for RAG"
    ),
    schedule_interval="0 20 * * 1-5",   # 17h00 BRT = 20h00 UTC (Seg-Sex)
    start_date=days_ago(1),
    catchup=False,                      # Não executa dias passados retroativamente
    max_active_runs=1,                  # Serializa execuções (evita race conditions)
    default_args=DEFAULT_ARGS,
    tags=["finsight", "production", "daily"],
    doc_md=__doc__,                     # Documentação visível na UI do Airflow
) as dag:

    # =========================================================================
    # Task 1: Healthcheck do banco de dados
    # Garante que o Postgres está acessível ANTES de qualquer coisa.
    # Em caso de falha, a DAG toda é abortada imediatamente.
    # =========================================================================
    def run_healthcheck(**context):
        """Verifica conectividade com o PostgreSQL."""
        from finsight.db import healthcheck
        healthcheck()

    task_healthcheck = PythonOperator(
        task_id="healthcheck_database",
        python_callable=run_healthcheck,
        doc_md="""
            **Healthcheck do banco**
            Testa a conexão com o PostgreSQL antes de iniciar o pipeline.
            Falha rápida aqui evita erros difíceis de depurar nas tarefas seguintes.
        """,
    )

    # =========================================================================
    # Task 2: Ingestão de Preços
    # Baixa cotações do dia para os tickers configurados.
    # =========================================================================
    def run_ingest_prices(**context):
        """Baixa cotações diárias do Yahoo Finance e salva no raw_prices."""
        from ingestion.fetch_prices import fetch_and_store_prices

        # days_lookback=2: pega hoje E ontem (segurança para pregões atrasados)
        count = fetch_and_store_prices(days_lookback=2)

        # Passa o resultado para a próxima task via XCom (auditoria)
        context["task_instance"].xcom_push(key="rows_ingested", value=count)
        return count

    task_ingest_prices = PythonOperator(
        task_id="ingest_prices",
        python_callable=run_ingest_prices,
        doc_md="""
            **Ingestão de Cotações**
            Fonte: Yahoo Finance (yfinance)
            Tabela destino: raw_prices
            Idempotente: usa upsert (ON CONFLICT DO UPDATE)
        """,
    )

    # =========================================================================
    # Task 3: Ingestão de Notícias
    # Puxa notícias financeiras das últimas 24h.
    # =========================================================================
    def run_ingest_news(**context):
        """Busca notícias financeiras e salva no raw_news."""
        from ingestion.fetch_news import fetch_and_store_news

        count = fetch_and_store_news(source="auto", hours_back=26)  # +2h de margem

        context["task_instance"].xcom_push(key="news_ingested", value=count)
        return count

    task_ingest_news = PythonOperator(
        task_id="ingest_news",
        python_callable=run_ingest_news,
        doc_md="""
            **Ingestão de Notícias**
            Fonte: Finnhub API (ou RSS como fallback)
            Tabela destino: raw_news
            Janela: últimas 26 horas (margem de segurança)
        """,
    )

    # =========================================================================
    # Task 4: dbt run
    # Executa todos os modelos dbt: staging → marts.
    # O BashOperator roda dbt dentro do container (que tem dbt instalado).
    # =========================================================================
    task_dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/airflow/finsight/dbt && "
            "dbt run "
            "--profiles-dir /opt/airflow/finsight/dbt "
            "--target docker "
            "--no-partial-parse"  # Força reparse completo (mais seguro)
        ),
        doc_md="""
            **dbt run**
            Executa os modelos SQL em ordem: stg_prices → stg_news → daily_metrics.
            Parâmetro --target docker usa o profile configurado para o ambiente Docker.
        """,
    )

    # =========================================================================
    # Task 5: dbt test
    # Valida qualidade dos dados após a transformação.
    # Falha aqui indica problema nos dados — alerta o engenheiro.
    # =========================================================================
    task_dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd /opt/airflow/finsight/dbt && "
            "dbt test "
            "--profiles-dir /opt/airflow/finsight/dbt "
            "--target docker"
        ),
        doc_md="""
            **dbt test**
            Roda os testes de qualidade definidos em schema.yml:
            - not_null nos campos obrigatórios
            - unique nas chaves compostas (ticker + date)
            Uma falha aqui indica dados corrompidos na ingestão.
        """,
    )

    # =========================================================================
    # Task 6: Geração de Embeddings (Fase 5)
    # Processa notícias novas (is_embedded = FALSE) e gera vetores.
    # É a tarefa mais lenta — pode levar alguns minutos para muitas notícias.
    # =========================================================================
    def run_embed_news(**context):
        """
        Gera embeddings das notícias não processadas e salva no pgvector.

        NOTA (Fase 0-4): Esta função retorna 0 sem erro.
        Será implementada na Fase 5.
        """
        try:
            from ai.embed import embed_pending_news
            count = embed_pending_news()
            context["task_instance"].xcom_push(key="embeddings_created", value=count)
            return count
        except ImportError:
            # Módulo ai/embed.py ainda não existe (Fase 0-4) — OK, segue em frente
            import logging
            logging.getLogger(__name__).info(
                "ai/embed.py not yet implemented (Fase 5). Skipping embedding step."
            )
            return 0

    task_embed_news = PythonOperator(
        task_id="embed_news",
        python_callable=run_embed_news,
        doc_md="""
            **Geração de Embeddings**
            Processa notícias com is_embedded=FALSE e gera vetores semânticos.
            Implementado na Fase 5. Segue sem erro nas fases anteriores.
        """,
    )

    # =========================================================================
    # Dependências entre tasks (define a ordem de execução)
    #
    #   healthcheck → ingest_prices ──┐
    #                                 ├──→ dbt_run → dbt_test → embed_news
    #               ingest_news ──────┘
    #
    # Preços e notícias rodam em paralelo (mais eficiente).
    # dbt só começa após AMBAS as ingestões concluírem.
    # =========================================================================
    task_healthcheck >> [task_ingest_prices, task_ingest_news]
    [task_ingest_prices, task_ingest_news] >> task_dbt_run
    task_dbt_run >> task_dbt_test >> task_embed_news
