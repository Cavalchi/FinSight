"""
app/api/main.py
===============
FastAPI backend — serves FinSight data to the React dashboard.

Endpoints:
  GET /api/tickers           → list of available tickers
  GET /api/metrics/{ticker}  → daily_metrics for a ticker
  GET /api/news              → recent market news

Run:
  uvicorn app.api.main:app --port 8000 --reload
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from finsight.db import get_engine

app = FastAPI(title="FinSight API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tickers")
def get_tickers() -> list[str]:
    """Returns distinct tickers available in daily_metrics."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT DISTINCT ticker FROM public_marts.daily_metrics ORDER BY ticker")
        )
        return [row[0] for row in result]


@app.get("/api/metrics/{ticker}")
def get_metrics(ticker: str) -> list[dict[str, Any]]:
    """Returns all daily_metrics rows for a ticker, ordered by date asc."""
    engine = get_engine()
    query = """
        SELECT
            trade_date::text,
            open_price, high_price, low_price, close_price, adj_close_price,
            volume, daily_return_simple, sma_7d, sma_30d,
            volatility_30d_pct, relative_volume, price_vs_sma30
        FROM public_marts.daily_metrics
        WHERE ticker = :ticker
        ORDER BY trade_date ASC
    """
    try:
        df = pd.read_sql(text(query), get_engine(), params={"ticker": ticker})
        # Replace NaN with None for clean JSON
        return df.where(pd.notna(df), None).to_dict(orient="records")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/news")
def get_news(limit: int = 30) -> list[dict[str, Any]]:
    """Returns the most recent news items."""
    engine = get_engine()
    query = text(f"""
        SELECT
            headline,
            source,
            url,
            published_at::text,
            category,
            api_source,
            related_tickers
        FROM raw_news
        ORDER BY published_at DESC NULLS LAST
        LIMIT {limit}
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        cols = result.keys()
        rows = []
        for row in result:
            d = dict(zip(cols, row))
            if d.get("related_tickers") is None:
                d["related_tickers"] = []
            rows.append(d)
        return rows


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
