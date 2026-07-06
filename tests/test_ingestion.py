"""
tests/test_ingestion.py
========================
Unit tests for ingestion/fetch_prices.py.

Covers pure/mockable functions:
  - _normalize_yfinance_output(): conversão MultiIndex → long format
  - store_prices(): com DataFrame vazio (não precisa de DB)

Run:
    pytest tests/test_ingestion.py -v
"""

import sys
import os
import pytest
import pandas as pd
from datetime import date
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingestion.fetch_prices import _normalize_yfinance_output, store_prices


# =============================================================================
# _normalize_yfinance_output
# =============================================================================

class TestNormalizeYfinanceOutput:

    def _make_single_ticker_df(self, ticker="PETR4.SA", rows=3) -> pd.DataFrame:
        """Cria um DataFrame no formato que yfinance retorna para 1 ticker."""
        dates = pd.date_range("2024-06-01", periods=rows, freq="B")
        df = pd.DataFrame({
            "Open":      [30.0, 31.0, 32.0][:rows],
            "High":      [31.5, 32.5, 33.5][:rows],
            "Low":       [29.5, 30.5, 31.5][:rows],
            "Close":     [31.0, 32.0, 33.0][:rows],
            "Adj Close": [30.9, 31.9, 32.9][:rows],
            "Volume":    [1_000_000, 2_000_000, 3_000_000][:rows],
        }, index=dates)
        df.index.name = "Date"
        return df

    def _make_multi_ticker_df(self, tickers: list[str], rows=2) -> pd.DataFrame:
        """Cria um DataFrame MultiIndex como yfinance retorna para múltiplos tickers."""
        dates = pd.date_range("2024-06-01", periods=rows, freq="B")
        cols = pd.MultiIndex.from_product(
            [["Open", "High", "Low", "Close", "Adj Close", "Volume"], tickers],
            names=["Price", "Ticker"],
        )
        data = {
            (price, ticker): [30.0 + i for i in range(rows)]
            for price in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
            for ticker in tickers
        }
        df = pd.DataFrame(data, index=dates, columns=cols)
        df.index.name = "Date"
        return df

    def test_single_ticker_returns_dataframe(self):
        raw = self._make_single_ticker_df()
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        assert isinstance(result, pd.DataFrame)

    def test_single_ticker_has_correct_columns(self):
        raw = self._make_single_ticker_df()
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        expected = {
            "ticker", "trade_date", "open_price", "high_price",
            "low_price", "close_price", "adj_close_price", "volume", "source"
        }
        assert expected.issubset(set(result.columns))

    def test_single_ticker_correct_row_count(self):
        raw = self._make_single_ticker_df(rows=3)
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        assert len(result) == 3

    def test_single_ticker_name_set_correctly(self):
        raw = self._make_single_ticker_df()
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        assert (result["ticker"] == "PETR4.SA").all()

    def test_single_ticker_source_is_yfinance(self):
        raw = self._make_single_ticker_df()
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        assert (result["source"] == "yfinance").all()

    def test_multi_ticker_row_count(self):
        tickers = ["PETR4.SA", "VALE3.SA"]
        raw = self._make_multi_ticker_df(tickers, rows=2)
        result = _normalize_yfinance_output(raw, tickers)
        # 2 tickers × 2 dias = 4 linhas
        assert len(result) == 4

    def test_multi_ticker_both_present(self):
        tickers = ["PETR4.SA", "VALE3.SA"]
        raw = self._make_multi_ticker_df(tickers, rows=2)
        result = _normalize_yfinance_output(raw, tickers)
        assert set(result["ticker"].unique()) == {"PETR4.SA", "VALE3.SA"}

    def test_drops_rows_with_null_close(self):
        raw = self._make_single_ticker_df(rows=3)
        raw.loc[raw.index[1], "Close"] = float("nan")  # Torna o dia 2 nulo
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        assert len(result) == 2  # 1 linha removida

    def test_trade_date_is_python_date(self):
        raw = self._make_single_ticker_df()
        result = _normalize_yfinance_output(raw, ["PETR4.SA"])
        for d in result["trade_date"]:
            assert isinstance(d, date)


# =============================================================================
# store_prices
# =============================================================================

class TestStorePrices:
    def test_empty_dataframe_returns_zero_without_db_call(self):
        """store_prices com df vazio não deve tentar conectar ao banco."""
        df = pd.DataFrame()
        result = store_prices(df)
        assert result == 0

    @patch("ingestion.fetch_prices.execute_values")
    @patch("ingestion.fetch_prices.get_raw_connection")
    def test_non_empty_calls_db(self, mock_conn_factory, mock_execute_values):
        """store_prices com dados deve chamar get_raw_connection e execute_values."""
        df = pd.DataFrame([{
            "ticker": "PETR4.SA",
            "trade_date": date(2024, 6, 1),
            "open_price": 30.0,
            "high_price": 31.0,
            "low_price": 29.5,
            "close_price": 30.5,
            "adj_close_price": 30.4,
            "volume": 1_000_000,
            "source": "yfinance",
        }])

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn_factory.return_value = mock_conn

        result = store_prices(df)

        assert mock_conn_factory.called
        assert mock_execute_values.called
        # execute_values recebeu o cursor e o SQL correto
        call_args = mock_execute_values.call_args
        assert "raw_prices" in call_args.args[1]  # SQL contém a tabela alvo
        assert isinstance(result, int)
