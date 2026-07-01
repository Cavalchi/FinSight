"""
app/streamlit_app.py
====================
FinSight Dashboard — Fase 4 (redesigned).

Features:
  - Dark premium UI with glassmorphism cards
  - Language toggle: EN / PT / ES
  - Candlestick + SMA chart
  - Volatility & Daily Return charts
  - KPI cards with delta indicators
  - Phase 5 RAG placeholder

How to run:
  streamlit run app/streamlit_app.py
  Access: http://localhost:8501
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

# =============================================================================
# Page config — must be first Streamlit call
# =============================================================================

st.set_page_config(
    page_title="FinSight — Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# i18n — translations
# =============================================================================

TRANSLATIONS = {
    "EN": {
        "title": "FinSight",
        "subtitle": "AI-Ready Market Data Pipeline",
        "tagline": "Real-time market intelligence powered by a production-grade data pipeline.",
        "filters": "⚙️ Controls",
        "lang_label": "Language",
        "ticker_label": "Stock Ticker",
        "period_label": "Period",
        "period_opts": ["All", "Last 30 days", "Last 7 days"],
        "last_close": "Last Close",
        "volatility": "Volatility 30d",
        "sma7": "SMA 7d",
        "rel_volume": "Relative Volume",
        "chart_price": "Price & Moving Averages",
        "chart_vol": "Volatility (30d annualized)",
        "chart_ret": "Daily Return",
        "raw_data": "📋 Raw Data Table",
        "rag_title": "🤖 Ask the AI Analyst",
        "rag_info": "**Coming in Phase 5:** Ask natural-language questions grounded in your own pipeline data.\n\n*Example: 'How was PETR4 volatility this week and what news drove it?'*",
        "no_data": "⚠️ No data yet. Trigger the Airflow DAG first.",
        "ohlc": "OHLC",
        "sma7_label": "SMA 7d",
        "sma30_label": "SMA 30d",
        "footer": "Built with Python · PostgreSQL · dbt · Apache Airflow · Docker · Streamlit",
    },
    "PT": {
        "title": "FinSight",
        "subtitle": "Pipeline de Dados de Mercado com IA",
        "tagline": "Inteligência de mercado em tempo real, alimentada por um pipeline de dados profissional.",
        "filters": "⚙️ Controles",
        "lang_label": "Idioma",
        "ticker_label": "Ativo",
        "period_label": "Período",
        "period_opts": ["Tudo", "Últimos 30 dias", "Últimos 7 dias"],
        "last_close": "Último Fechamento",
        "volatility": "Volatilidade 30d",
        "sma7": "MM 7d",
        "rel_volume": "Volume Relativo",
        "chart_price": "Preço & Médias Móveis",
        "chart_vol": "Volatilidade (30d anualizada)",
        "chart_ret": "Retorno Diário",
        "raw_data": "📋 Tabela de Dados",
        "rag_title": "🤖 Pergunte ao Analista IA",
        "rag_info": "**Fase 5 em breve:** Faça perguntas em linguagem natural baseadas nos seus próprios dados.\n\n*Exemplo: 'Como foi a volatilidade da PETR4 essa semana e quais notícias influenciaram?'*",
        "no_data": "⚠️ Sem dados ainda. Dispare a DAG no Airflow primeiro.",
        "ohlc": "OHLC",
        "sma7_label": "MM 7d",
        "sma30_label": "MM 30d",
        "footer": "Construído com Python · PostgreSQL · dbt · Apache Airflow · Docker · Streamlit",
    },
    "ES": {
        "title": "FinSight",
        "subtitle": "Pipeline de Datos de Mercado con IA",
        "tagline": "Inteligencia de mercado en tiempo real, impulsada por un pipeline de datos profesional.",
        "filters": "⚙️ Controles",
        "lang_label": "Idioma",
        "ticker_label": "Activo",
        "period_label": "Período",
        "period_opts": ["Todo", "Últimos 30 días", "Últimos 7 días"],
        "last_close": "Último Cierre",
        "volatility": "Volatilidad 30d",
        "sma7": "MM 7d",
        "rel_volume": "Volumen Relativo",
        "chart_price": "Precio & Medias Móviles",
        "chart_vol": "Volatilidad (30d anualizada)",
        "chart_ret": "Retorno Diario",
        "raw_data": "📋 Tabla de Datos",
        "rag_title": "🤖 Pregunta al Analista IA",
        "rag_info": "**Fase 5 próximamente:** Haz preguntas en lenguaje natural basadas en tus propios datos.\n\n*Ejemplo: '¿Cómo fue la volatilidad de PETR4 esta semana y qué noticias la impulsaron?'*",
        "no_data": "⚠️ Sin datos aún. Primero dispara el DAG en Airflow.",
        "ohlc": "OHLC",
        "sma7_label": "MM 7d",
        "sma30_label": "MM 30d",
        "footer": "Construido con Python · PostgreSQL · dbt · Apache Airflow · Docker · Streamlit",
    },
}

# =============================================================================
# Custom CSS — dark premium theme
# =============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1020 100%);
        color: #e2e8f0;
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(99, 179, 237, 0.15);
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    /* ── Hero header ── */
    .hero-header {
        background: linear-gradient(135deg, rgba(99,179,237,0.08) 0%, rgba(139,92,246,0.08) 100%);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 28px;
        backdrop-filter: blur(12px);
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(90deg, #63b3ed, #a78bfa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 4px 0;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 1rem;
        font-weight: 500;
        color: #94a3b8;
        margin: 0 0 10px 0;
    }
    .hero-tagline {
        font-size: 0.875rem;
        color: #64748b;
        margin: 0;
    }

    /* ── KPI Cards ── */
    .kpi-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 20px 24px;
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
    }
    .kpi-card:hover {
        border-color: rgba(99,179,237,0.3);
        background: rgba(99,179,237,0.06);
        transform: translateY(-2px);
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 4px;
        line-height: 1;
    }
    .kpi-delta-pos { font-size: 0.8rem; color: #34d399; font-weight: 500; }
    .kpi-delta-neg { font-size: 0.8rem; color: #f87171; font-weight: 500; }
    .kpi-delta-neu { font-size: 0.8rem; color: #94a3b8; font-weight: 500; }

    /* ── Section headers ── */
    .section-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 28px 0 16px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.06);
    }

    /* ── Chart container ── */
    .chart-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 4px;
        margin-bottom: 16px;
    }

    /* ── RAG placeholder ── */
    .rag-card {
        background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(59,130,246,0.08));
        border: 1px solid rgba(139,92,246,0.25);
        border-radius: 12px;
        padding: 28px 32px;
        text-align: center;
        margin-top: 12px;
    }

    /* ── Language toggle pills ── */
    div[data-testid="stRadio"] > div {
        flex-direction: row !important;
        gap: 8px !important;
    }
    div[data-testid="stRadio"] label {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem;
        font-weight: 500;
        cursor: pointer;
    }

    /* ── Footer ── */
    .footer-bar {
        text-align: center;
        color: #334155;
        font-size: 0.75rem;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid rgba(255,255,255,0.05);
    }

    /* ── Divider ── */
    hr { border-color: rgba(255,255,255,0.06) !important; }

    /* Dataframe */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Data functions
# =============================================================================

@st.cache_data(ttl=300)
def get_available_tickers() -> list[str]:
    from finsight.db import get_engine
    from sqlalchemy import text
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT DISTINCT ticker FROM public_marts.daily_metrics ORDER BY ticker")
            )
            return [row[0] for row in result]
    except Exception:
        return []


@st.cache_data(ttl=300)
def load_metrics(ticker: str) -> pd.DataFrame:
    from finsight.db import get_engine
    query = """
        SELECT
            trade_date, open_price, high_price, low_price,
            close_price, adj_close_price, volume,
            daily_return_simple, sma_7d, sma_30d,
            volatility_30d_pct, relative_volume, price_vs_sma30
        FROM public_marts.daily_metrics
        WHERE ticker = %(ticker)s
        ORDER BY trade_date ASC
    """
    engine = get_engine()
    df = pd.read_sql(query, engine, params={"ticker": ticker})
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def filter_by_period(df: pd.DataFrame, period: str, t: dict) -> pd.DataFrame:
    opts = t["period_opts"]
    if period == opts[1]:  # 30 days
        cutoff = df["trade_date"].max() - pd.Timedelta(days=30)
        return df[df["trade_date"] >= cutoff]
    elif period == opts[2]:  # 7 days
        cutoff = df["trade_date"].max() - pd.Timedelta(days=7)
        return df[df["trade_date"] >= cutoff]
    return df


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    # Language dropdown
    lang_options = {"🇬🇧 English": "EN", "🇧🇷 Português": "PT", "🇪🇸 Español": "ES"}
    lang_label = st.selectbox("🌐 Language", options=list(lang_options.keys()), index=0)
    lang = lang_options[lang_label]
    t = TRANSLATIONS[lang]

    st.divider()

    available_tickers = get_available_tickers()

    if not available_tickers:
        st.warning(t["no_data"])
        st.stop()

    selected_ticker = st.selectbox(t["ticker_label"], options=available_tickers, index=0)
    selected_period = st.selectbox(t["period_label"], options=t["period_opts"], index=0)

    st.divider()
    st.markdown(f"<div style='font-size:0.72rem;color:#334155;'>{t['footer']}</div>", unsafe_allow_html=True)


# =============================================================================
# Load & filter data
# =============================================================================

df_full = load_metrics(selected_ticker)

if df_full.empty:
    st.error(t["no_data"])
    st.stop()

df = filter_by_period(df_full, selected_period, t)
latest = df.iloc[-1]

# =============================================================================
# Hero header
# =============================================================================

st.markdown(f"""
<div class="hero-header">
    <div class="hero-title">{t['title']}</div>
    <div class="hero-subtitle">{t['subtitle']}</div>
    <div class="hero-tagline">{t['tagline']}</div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# KPI Cards
# =============================================================================

ret = latest.get("daily_return_simple", 0) or 0
ret_pct = ret * 100
vol = latest.get("volatility_30d_pct")
sma7 = latest.get("sma_7d")
rel_vol = latest.get("relative_volume")

delta_class = "kpi-delta-pos" if ret_pct >= 0 else "kpi-delta-neg"
delta_arrow = "▲" if ret_pct >= 0 else "▼"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{t['last_close']}</div>
        <div class="kpi-value">$ {latest['adj_close_price']:.2f}</div>
        <div class="{delta_class}">{delta_arrow} {ret_pct:+.2f}%</div>
    </div>""", unsafe_allow_html=True)

with col2:
    vol_str = f"{vol:.1f}%" if pd.notna(vol) else "—"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{t['volatility']}</div>
        <div class="kpi-value">{vol_str}</div>
        <div class="kpi-delta-neu">annualized</div>
    </div>""", unsafe_allow_html=True)

with col3:
    sma7_str = f"$ {sma7:.2f}" if pd.notna(sma7) else "—"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{t['sma7']}</div>
        <div class="kpi-value">{sma7_str}</div>
        <div class="kpi-delta-neu">7-day avg</div>
    </div>""", unsafe_allow_html=True)

with col4:
    rv_str = f"{rel_vol:.2f}×" if pd.notna(rel_vol) else "—"
    rv_class = "kpi-delta-pos" if pd.notna(rel_vol) and rel_vol > 1.2 else "kpi-delta-neu"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{t['rel_volume']}</div>
        <div class="kpi-value">{rv_str}</div>
        <div class="{rv_class}">vs 30d avg</div>
    </div>""", unsafe_allow_html=True)

# =============================================================================
# Chart 1 — Candlestick + SMAs
# =============================================================================

st.markdown(f'<div class="section-title">📊 {t["chart_price"]} — {selected_ticker}</div>', unsafe_allow_html=True)

fig_price = go.Figure()

fig_price.add_trace(go.Candlestick(
    x=df["trade_date"],
    open=df["open_price"],
    high=df["high_price"],
    low=df["low_price"],
    close=df["close_price"],
    name=t["ohlc"],
    increasing_line_color="#34d399",
    decreasing_line_color="#f87171",
    increasing_fillcolor="rgba(52,211,153,0.15)",
    decreasing_fillcolor="rgba(248,113,113,0.15)",
))

fig_price.add_trace(go.Scatter(
    x=df["trade_date"], y=df["sma_7d"],
    name=t["sma7_label"],
    line=dict(color="#f59e0b", width=1.5, dash="dot"),
))

fig_price.add_trace(go.Scatter(
    x=df["trade_date"], y=df["sma_30d"],
    name=t["sma30_label"],
    line=dict(color="#63b3ed", width=2),
))

fig_price.update_layout(
    height=420,
    xaxis_rangeslider_visible=False,
    margin=dict(l=0, r=0, t=8, b=0),
    legend=dict(orientation="h", y=1.06, x=0, bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=12)),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8"),
    hoverlabel=dict(
        bgcolor="rgba(10,14,26,0.98)",
        bordercolor="rgba(99,179,237,0.4)",
        font=dict(color="#cbd5e1", size=12),
    ),
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)", tickfont=dict(color="#64748b")),
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)", tickfont=dict(color="#64748b")),
)

st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# Charts 2 & 3 — Volatility + Daily Return
# =============================================================================

col_vol, col_ret = st.columns(2)

with col_vol:
    st.markdown(f'<div class="section-title">🌊 {t["chart_vol"]}</div>', unsafe_allow_html=True)
    fig_vol = go.Figure(go.Scatter(
        x=df["trade_date"], y=df["volatility_30d_pct"],
        fill="tozeroy",
        line=dict(color="#f87171", width=2),
        fillcolor="rgba(248,113,113,0.08)",
        name="Vol %",
    ))
    fig_vol.update_layout(
        height=260, margin=dict(l=0, r=0, t=8, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(color="#64748b"), ticksuffix="%"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(color="#64748b")),
        showlegend=False,
    )
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with col_ret:
    st.markdown(f'<div class="section-title">📉 {t["chart_ret"]}</div>', unsafe_allow_html=True)
    rets = df["daily_return_simple"].fillna(0)
    colors = ["rgba(52,211,153,0.75)" if r >= 0 else "rgba(248,113,113,0.75)" for r in rets]
    fig_ret = go.Figure(go.Bar(
        x=df["trade_date"], y=rets * 100,
        marker_color=colors,
        marker_line_width=0,
        name="Return %",
    ))
    fig_ret.update_layout(
        height=260, margin=dict(l=0, r=0, t=8, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(color="#64748b"), ticksuffix="%",
                   zerolinecolor="rgba(255,255,255,0.1)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(color="#64748b")),
        showlegend=False,
    )
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.plotly_chart(fig_ret, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# Raw data table
# =============================================================================

with st.expander(t["raw_data"]):
    display_cols = [
        "trade_date", "open_price", "high_price", "low_price",
        "close_price", "adj_close_price", "volume",
        "daily_return_simple", "sma_7d", "sma_30d", "volatility_30d_pct",
    ]
    st.dataframe(
        df[display_cols].tail(30).sort_values("trade_date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

# =============================================================================
# RAG placeholder — Phase 5
# =============================================================================

st.markdown(f'<div class="section-title">🤖 AI Analyst</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="rag-card">
    <div style="font-size:2.5rem;margin-bottom:12px;">🤖</div>
    <div style="font-size:1.1rem;font-weight:600;color:#a78bfa;margin-bottom:12px;">{t['rag_title']}</div>
    <div style="color:#64748b;font-size:0.875rem;line-height:1.7;">{t['rag_info'].replace(chr(10), '<br>')}</div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# Footer
# =============================================================================

st.markdown(f'<div class="footer-bar">{t["footer"]}</div>', unsafe_allow_html=True)
