import os
import io
import json
import uuid
import hashlib
import csv
import difflib
import html
import re
import time
import calendar
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson, chi2

# ============================================================
# TEX ESTATÍSTICAS V20.3.5 — DIREÇÃO ALGÉBRICA E COERÊNCIA INTERNA
# ============================================================
# Objetivo desta versão:
# - manter o cálculo auditável de forças e Poisson;
# - acrescentar frequências empíricas suavizadas para gols e ambas marcam;
# - impedir contradições entre a projeção agregada e o lado operacional escolhido;
# - cortar automaticamente informação posterior à data do jogo;
# - permitir análise científica sem cotações falsas e sem sugestão de entrada;
# - tratar estabilidade, odds incoerentes e lados opostos como travas reais, não meros avisos.
# ============================================================

st.set_page_config(page_title="TEX ESTATÍSTICAS — V20.3.5 Direção Algébrica", layout="wide")

# ============================================================
# FUSO HORÁRIO DOS REGISTROS
# ============================================================

# O servidor do Streamlit normalmente opera em UTC. Todos os horários gravados
# pelo TEX devem representar o horário local do usuário no Nordeste do Brasil.
FUSO_HORARIO_REGISTROS = os.getenv("TEX_FUSO_HORARIO", "America/Fortaleza")


def agora_local() -> datetime:
    """Retorna a data/hora local com fuso explícito; nunca usa o UTC do servidor."""
    try:
        return datetime.now(ZoneInfo(FUSO_HORARIO_REGISTROS))
    except (ZoneInfoNotFoundError, Exception):
        # Fallback seguro para o horário de Brasília/Nordeste (UTC-03:00).
        return datetime.now(timezone(timedelta(hours=-3)))


def agora_local_texto() -> str:
    return agora_local().strftime("%Y-%m-%d %H:%M:%S")


def carimbo_local_backup() -> str:
    return agora_local().strftime("%Y%m%d_%H%M%S_%f")


# ============================================================
# VISUAL
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@600;700;800&display=swap');

    :root {
        color-scheme: light;
        --bg: #eef1f6;
        --surface: rgba(255, 255, 255, 0.86);
        --ink: #0b1220;
        --muted: #64748b;
        --line: rgba(148, 163, 184, 0.28);
        --navy: #0f172a;
        --teal: #0f766e;
        --gold: #c08a2c;
        --green: #047857;
        --amber: #b45309;
        --red: #b91c1c;
        --blue: #1d4ed8;
        --shadow: 0 20px 55px rgba(15, 23, 42, 0.10);
        --shadow-soft: 0 10px 25px rgba(15, 23, 42, 0.075);
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background:
            radial-gradient(circle at top left, rgba(20, 184, 166, 0.13), transparent 34rem),
            radial-gradient(circle at top right, rgba(192, 138, 44, 0.14), transparent 36rem),
            linear-gradient(180deg, #f8fafc 0%, var(--bg) 52%, #e8edf5 100%) !important;
        color: var(--ink) !important;
        font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        letter-spacing: -0.01em;
    }

    .block-container { padding-top: 1.4rem !important; max-width: 1460px !important; }

    [data-testid="stHeader"] {
        background: rgba(248, 250, 252, 0.78) !important;
        backdrop-filter: blur(18px);
        border-bottom: 1px solid rgba(148, 163, 184, 0.22);
    }

    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        color: var(--ink) !important;
        border-right: 1px solid rgba(148, 163, 184, 0.24);
    }

    label, p, span, small, div, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    .stCaption, [data-testid="stCaptionContainer"], .muted, small {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
    }

    h1, h2, h3, h4 {
        font-family: "Space Grotesk", "Inter", sans-serif !important;
        color: var(--ink) !important;
        letter-spacing: -0.035em !important;
    }

    input, textarea, [data-baseweb="input"], [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea, [data-baseweb="select"], [data-baseweb="select"] div,
    [role="listbox"], [role="option"], [data-baseweb="popover"], [data-baseweb="menu"] {
        background-color: #ffffff !important;
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        border-color: rgba(148, 163, 184, 0.42) !important;
        border-radius: 14px !important;
    }

    input::placeholder, textarea::placeholder,
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {
        color: #a8b1c2 !important;
        -webkit-text-fill-color: #a8b1c2 !important;
        opacity: 1 !important;
        font-weight: 500 !important;
    }

    .hero {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(15, 118, 110, 0.96) 54%, rgba(192, 138, 44, 0.92) 130%);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 30px;
        padding: 30px 30px 26px;
        margin-bottom: 18px;
        box-shadow: 0 28px 70px rgba(15, 23, 42, 0.20);
        position: relative;
        overflow: hidden;
    }
    .hero:before { content: ""; position: absolute; inset: -70px auto auto -80px; width: 250px; height: 250px; background: radial-gradient(circle, rgba(255, 255, 255, 0.22), transparent 62%); opacity: 0.65; }
    .hero:after { content: ""; position: absolute; right: -120px; bottom: -140px; width: 360px; height: 360px; background: radial-gradient(circle, rgba(255, 255, 255, 0.16), transparent 58%); }
    .hero-title {
        position: relative; z-index: 1;
        font-family: "Space Grotesk", "Inter", sans-serif;
        font-size: clamp(2rem, 4vw, 3.25rem);
        line-height: 0.96; font-weight: 800; letter-spacing: -0.07em;
        margin: 8px 0 10px;
        color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    }
    .hero-sub {
        position: relative; z-index: 1; max-width: 1020px;
        color: rgba(255, 255, 255, 0.78) !important; -webkit-text-fill-color: rgba(255, 255, 255, 0.78) !important;
        line-height: 1.58; font-weight: 520; font-size: 0.98rem;
    }
    .chip-row { position: relative; z-index: 1; margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
    .chip {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 8px 12px; border-radius: 999px;
        background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.20);
        color: rgba(255, 255, 255, 0.90) !important; -webkit-text-fill-color: rgba(255, 255, 255, 0.90) !important;
        font-weight: 800; font-size: 0.79rem; backdrop-filter: blur(10px);
    }

    .base-info, .premium-panel {
        background: rgba(255, 255, 255, 0.78); border: 1px solid var(--line);
        border-radius: 20px; padding: 14px 16px; margin: 10px 0 16px;
        font-size: .88rem; font-weight: 750; color: #334155 !important; -webkit-text-fill-color: #334155 !important;
        box-shadow: var(--shadow-soft); backdrop-filter: blur(14px);
    }

    .analysis-head {
        background: rgba(255, 255, 255, 0.82); border: 1px solid var(--line);
        border-radius: 28px; padding: 20px 22px; margin: 8px 0 16px;
        box-shadow: var(--shadow-soft); backdrop-filter: blur(16px);
    }
    .analysis-kicker { font-size: .78rem; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--teal) !important; -webkit-text-fill-color: var(--teal) !important; margin-bottom: 7px; }
    .analysis-title { font-family: "Space Grotesk", "Inter", sans-serif; font-size: clamp(1.65rem, 3vw, 2.6rem); line-height: 1.02; font-weight: 800; letter-spacing: -0.055em; color: var(--navy) !important; -webkit-text-fill-color: var(--navy) !important; }
    .version-pill { display: inline-flex; margin-top: 12px; padding: 8px 11px; border-radius: 999px; background: #ecfeff; border: 1px solid #99f6e4; color: #0f766e !important; -webkit-text-fill-color: #0f766e !important; font-weight: 850; font-size: .80rem; }

    .stat-card {
        background: rgba(255, 255, 255, 0.82); border: 1px solid var(--line); border-radius: 24px;
        padding: 17px 18px 16px; box-shadow: var(--shadow-soft); min-height: 104px;
        backdrop-filter: blur(14px); position: relative; overflow: hidden;
    }
    .stat-card:after { content: ""; position: absolute; right: -44px; top: -44px; width: 100px; height: 100px; border-radius: 999px; background: radial-gradient(circle, rgba(20, 184, 166, 0.13), transparent 65%); }
    .stat-label { position: relative; z-index: 1; font-size: 0.72rem; font-weight: 900; letter-spacing: .055em; text-transform: uppercase; color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; margin-bottom: 9px; }
    .stat-value { position: relative; z-index: 1; font-family: "Space Grotesk", "Inter", sans-serif; font-size: 2.05rem; line-height: 1; letter-spacing: -0.055em; font-weight: 800; color: var(--navy) !important; -webkit-text-fill-color: var(--navy) !important; }
    .stat-hint { position: relative; z-index: 1; margin-top: 8px; font-size: 0.76rem; font-weight: 750; color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; }

    .confidence-button { display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 9px 13px; font-family: "Space Grotesk", "Inter", sans-serif; font-weight: 800; letter-spacing: -0.01em; box-shadow: var(--shadow-soft); margin: 8px 0 8px; border: 1px solid transparent; }
    .confidence-good { background: #ecfdf5; border-color: #a7f3d0; color: #065f46 !important; -webkit-text-fill-color: #065f46 !important; }
    .confidence-mid { background: #fff7ed; border-color: #fed7aa; color: #9a3412 !important; -webkit-text-fill-color: #9a3412 !important; }
    .confidence-low { background: #fef2f2; border-color: #fecaca; color: #991b1b !important; -webkit-text-fill-color: #991b1b !important; }

    .entry-card { background: rgba(255, 255, 255, 0.90); border: 1px solid var(--line); border-radius: 28px; padding: 20px; margin: 16px 0; box-shadow: var(--shadow); backdrop-filter: blur(16px); overflow: hidden; position: relative; }
    .entry-card:before { content: ""; position: absolute; inset: 0 auto 0 0; width: 7px; background: var(--amber); }
    .entry-card.high:before { background: linear-gradient(180deg, #10b981, #047857); }
    .entry-card.mid:before { background: linear-gradient(180deg, #f59e0b, #b45309); }
    .entry-card.low:before { background: linear-gradient(180deg, #ef4444, #991b1b); }
    .entry-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-left: 2px; }
    .entry-badge { display: inline-flex; align-items: center; gap: 7px; padding: 8px 11px; border-radius: 999px; font-weight: 900; font-size: .78rem; border: 1px solid transparent; white-space: nowrap; }
    .entry-card.high .entry-badge { background: #ecfdf5; border-color: #a7f3d0; color: #065f46 !important; -webkit-text-fill-color: #065f46 !important; }
    .entry-card.mid .entry-badge { background: #fff7ed; border-color: #fed7aa; color: #9a3412 !important; -webkit-text-fill-color: #9a3412 !important; }
    .entry-card.low .entry-badge { background: #fef2f2; border-color: #fecaca; color: #991b1b !important; -webkit-text-fill-color: #991b1b !important; }
    .entry-type { font-weight: 900; font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; color: var(--green) !important; -webkit-text-fill-color: var(--green) !important; margin: 16px 0 5px 0; }
    .entry-market { font-family: "Space Grotesk", "Inter", sans-serif; font-weight: 800; letter-spacing: -0.045em; font-size: clamp(1.35rem, 2.5vw, 2.2rem); line-height: 1.04; color: var(--navy) !important; -webkit-text-fill-color: var(--navy) !important; margin-bottom: 10px; }
    .entry-meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 14px; }
    .meta-pill { display: inline-flex; align-items: center; padding: 7px 10px; border-radius: 999px; border: 1px solid rgba(148, 163, 184, 0.28); background: #f8fafc; color: #334155 !important; -webkit-text-fill-color: #334155 !important; font-size: .82rem; font-weight: 750; }
    .kv-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
    .kv { border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 18px; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); padding: 12px 13px; }
    .kv-label { font-size: .72rem; font-weight: 900; letter-spacing: .05em; text-transform: uppercase; color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; margin-bottom: 4px; }
    .kv-value { font-family: "Space Grotesk", "Inter", sans-serif; font-size: 1.32rem; font-weight: 800; line-height: 1; letter-spacing: -0.04em; color: var(--navy) !important; -webkit-text-fill-color: var(--navy) !important; }

    .warn-list-box { background: #fff7ed; border: 1px solid #fed7aa; border-left: 7px solid #f97316; border-radius: 20px; padding: 14px 16px; margin: 10px 0 14px 0; box-shadow: var(--shadow-soft); }
    .market-alert { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 14px; padding: 10px 12px; color: #7c2d12; font-weight: 800; }
    .big-green { color: var(--green) !important; -webkit-text-fill-color: var(--green) !important; font-weight: 900; }
    .big-red { color: var(--red) !important; -webkit-text-fill-color: var(--red) !important; font-weight: 900; }
    .big-blue { color: var(--blue) !important; -webkit-text-fill-color: var(--blue) !important; font-weight: 900; }
    .big-yellow { color: var(--amber) !important; -webkit-text-fill-color: var(--amber) !important; font-weight: 900; }

    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, button[kind="primary"], button[kind="secondary"] { border-radius: 16px !important; font-weight: 900 !important; border: 1px solid rgba(15, 118, 110, 0.24) !important; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08) !important; }
    button[kind="primary"] { background: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; border: 1px solid #ef4444 !important; }
    button[kind="secondary"], .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { background: rgba(255, 255, 255, 0.88) !important; color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover, button[kind="primary"]:hover, button[kind="secondary"]:hover { transform: translateY(-1px); border-color: rgba(15, 118, 110, 0.55) !important; }

    [data-testid="stMetric"], [data-testid="stDataFrame"], [data-testid="stExpander"] { background: rgba(255, 255, 255, 0.82) !important; border: 1px solid var(--line) !important; border-radius: 20px !important; box-shadow: var(--shadow-soft) !important; overflow: hidden !important; }
    [data-testid="stExpander"] summary { font-weight: 850 !important; }
    [data-testid="stAlert"] { border-radius: 18px !important; border: 1px solid rgba(148, 163, 184, 0.22) !important; box-shadow: var(--shadow-soft) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 999px !important; background: rgba(255, 255, 255, 0.72) !important; border: 1px solid rgba(148, 163, 184, 0.24) !important; padding: 8px 14px !important; font-weight: 850 !important; }
    .stTabs [data-baseweb="tab"] * { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; }
    .stTabs [aria-selected="true"] { background: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; border-bottom: 3px solid #ef4444 !important; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08) !important; }
    .stTabs [aria-selected="true"] * { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; }

    @media (max-width: 860px) {
        .hero { padding: 22px 18px; border-radius: 24px; }
        .kv-grid { grid-template-columns: 1fr; }
        .entry-top { flex-direction: column; }
        .entry-badge { white-space: normal; }
        .stat-card { min-height: 92px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

LIGAS_CSV = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Argentina - Primera Division": "https://www.football-data.co.uk/new/ARG.csv",
    "EUA - MLS": "https://www.football-data.co.uk/new/USA.csv",
    "México - Liga MX": "https://www.football-data.co.uk/new/MEX.csv",
    "Japão - J1 League": "https://www.football-data.co.uk/new/JPN.csv",
    "China - Super League": "https://www.football-data.co.uk/new/CHN.csv",
    "Suécia - Allsvenskan": "https://www.football-data.co.uk/new/SWE.csv",
    "Noruega - Eliteserien": "https://www.football-data.co.uk/new/NOR.csv",
    "Finlândia - Veikkausliiga": "https://www.football-data.co.uk/new/FIN.csv",
    "Irlanda - Premier Division": "https://www.football-data.co.uk/new/IRL.csv",
    "Inglaterra - Premier League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "Inglaterra - Championship": "https://www.football-data.co.uk/mmz4281/2526/E1.csv",
    "Espanha - La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Espanha - Segunda Divisão": "https://www.football-data.co.uk/mmz4281/2526/SP2.csv",
    "Itália - Série A": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Itália - Série B": "https://www.football-data.co.uk/mmz4281/2526/I2.csv",
    "Alemanha - Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "Alemanha - 2. Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D2.csv",
    "França - Ligue 1": "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    "Portugal - Primeira Liga": "https://www.football-data.co.uk/mmz4281/2526/P1.csv",
    "Holanda - Eredivisie": "https://www.football-data.co.uk/mmz4281/2526/N1.csv",
    "Bélgica - Pro League": "https://www.football-data.co.uk/mmz4281/2526/B1.csv",
    "Turquia - Super Lig": "https://www.football-data.co.uk/mmz4281/2526/T1.csv",
    "Grécia - Super League": "https://www.football-data.co.uk/mmz4281/2526/G1.csv",
}

LIGAS_API = {
    "Brasileirão Série A": "soccer_brazil_campeonato",
    "Argentina - Primera Division": "soccer_argentina_primera_division",
    "EUA - MLS": "soccer_usa_mls",
    "México - Liga MX": "soccer_mexico_ligamx",
    "Japão - J1 League": "soccer_japan_j_league",
    "China - Super League": "soccer_china_superleague",
    "Suécia - Allsvenskan": "soccer_sweden_allsvenskan",
    "Noruega - Eliteserien": "soccer_norway_eliteserien",
    "Finlândia - Veikkausliiga": "soccer_finland_veikkausliiga",
    "Irlanda - Premier Division": "soccer_ireland_premier_division",
    "Inglaterra - Premier League": "soccer_epl",
    "Inglaterra - Championship": "soccer_efl_champ",
    "Espanha - La Liga": "soccer_spain_la_liga",
    "Espanha - Segunda Divisão": "soccer_spain_segunda_division",
    "Itália - Série A": "soccer_italy_serie_a",
    "Itália - Série B": "soccer_italy_serie_b",
    "Alemanha - Bundesliga": "soccer_germany_bundesliga",
    "Alemanha - 2. Bundesliga": "soccer_germany_bundesliga2",
    "França - Ligue 1": "soccer_france_ligue_one",
    "Portugal - Primeira Liga": "soccer_portugal_primeira_liga",
    "Holanda - Eredivisie": "soccer_netherlands_eredivisie",
    "Bélgica - Pro League": "soccer_belgium_first_div",
    "Turquia - Super Lig": "soccer_turkey_super_league",
    "Grécia - Super League": "soccer_greece_super_league",
}

MERCADOS_NUCLEO = [
    "Vitória Casa",
    "Empate",
    "Vitória Fora",
    "Mais de 2.5 gols",
    "Menos de 2.5 gols",
    "Ambos marcam - Sim",
    "Ambos marcam - Não",
]

VERSAO_MODELO = "TEX ESTATÍSTICAS V20.3.5"

COLUNAS_HISTORICO_ANALISES = [
    "ID Análise", "ID Coleta", "Registrado em", "Liga", "Jogo", "Mandante", "Visitante",
    "Data do jogo", "Hora do jogo", "Casa de apostas", "Origem", "Mercado", "Cotação",
    "Probabilidade operacional %", "Probabilidade Poisson %", "Probabilidade empírica %",
    "Probabilidade de mercado ajustada %", "Cotação justa", "Valor esperado %",
    "Gols projetados casa", "Gols projetados fora", "Gols projetados total",
    "Chance mandante marcar %", "Chance visitante marcar %",
    "Amostra casa", "Amostra fora", "Estabilidade", "Situação", "Entrada %",
    "Versão do modelo", "Configuração JSON",
]

COLUNAS_AUDITORIA = [
    "ID", "Registrado em", "Liga", "Jogo", "Casa de apostas", "Mercado",
    "Cotação de entrada", "Probabilidade implícita bruta %", "Margem do mercado %",
    "Probabilidade de mercado ajustada %", "Chance pelo sistema %",
    "Vantagem do modelo (p.p.)", "Referência da vantagem", "Cotação justa", "Valor esperado %",
    "Fonte da probabilidade", "Versão do modelo", "Entrada %", "Entrada R$", "Banca antes",
    "Cotação de fechamento", "Vantagem no fechamento %", "Status", "Resultado R$", "Banca depois",
    "Diagnóstico pós-jogo", "Origem", "Observação", "Etiquetas",
]

COLUNAS_CATALOGO = [
    "ID Coleta", "Registrado em", "Casa de apostas", "Liga", "Jogo", "Mandante", "Visitante",
    "Data do jogo", "Hora do jogo", "Mercado", "Seleção", "Cotação",
    "Grupo do mercado", "Mercado completo", "Probabilidade implícita bruta %",
    "Margem do mercado %", "Probabilidade ajustada sem margem %",
    "Banca no momento", "Perfil", "Origem", "Observação",
]

ARQUIVO_AUDITORIA = "logs/auditoria_tex_v19_1.csv"  # mantém histórico da V19
ARQUIVO_CATALOGO = "logs/catalogo_odds_tex_v19_1.csv"  # mantém histórico da V19
ARQUIVO_HISTORICO_ANALISES = "logs/historico_analises_tex_v20_3_3.csv"
DIRETORIO_BACKUPS = "logs/backups"
GOOGLE_SHEETS_WORKSHEET_CATALOGO = "catalogo_odds"
GOOGLE_SHEETS_WORKSHEET_AUDITORIA = "auditoria_entradas"
GOOGLE_SHEETS_WORKSHEET_HISTORICO = "historico_analises"
GOOGLE_CACHE_TTL_SEG = 300
GOOGLE_COOLDOWN_SEG = 75

CALENDARIO_LIGAS = [
    {"Liga": "Brasileirão Série A", "Observação": "Use somente Série A. Não misture estaduais, Copa do Brasil, Série B, Sub-20 ou feminino."},
    {"Liga": "Argentina - Primera Division", "Observação": "Use somente Primera División/Liga Profesional principal. Não misture Primera Nacional, copa ou reservas."},
    {"Liga": "EUA - MLS", "Observação": "Use somente MLS principal. Não use MLS Next Pro, times II ou reservas."},
    {"Liga": "México - Liga MX", "Observação": "Use somente Liga MX principal. Não misture Expansión, Sub-23 ou feminino."},
    {"Liga": "Japão - J1 League", "Observação": "Use somente J1. Não misture J2, J3, Copa da Liga ou Copa do Imperador."},
    {"Liga": "China - Super League", "Observação": "Use somente Super League principal."},
    {"Liga": "Suécia - Allsvenskan", "Observação": "Use somente Allsvenskan. Não usar Ettan/Division 1."},
    {"Liga": "Noruega - Eliteserien", "Observação": "Use somente Eliteserien. Não usar OBOS-ligaen."},
    {"Liga": "Finlândia - Veikkausliiga", "Observação": "Use somente Veikkausliiga. Não usar Ykkösliiga/Ykkönen."},
    {"Liga": "Irlanda - Premier Division", "Observação": "Use somente Premier Division. Não usar First Division ou copas."},
    {"Liga": "Inglaterra - Premier League", "Observação": "Use somente Premier League. Não usar copas ou Championship."},
    {"Liga": "Inglaterra - Championship", "Observação": "Use somente Championship."},
    {"Liga": "Espanha - La Liga", "Observação": "Use somente La Liga."},
    {"Liga": "Espanha - Segunda Divisão", "Observação": "Use somente Segunda División."},
    {"Liga": "Itália - Série A", "Observação": "Use somente Serie A."},
    {"Liga": "Itália - Série B", "Observação": "Use somente Serie B."},
    {"Liga": "Alemanha - Bundesliga", "Observação": "Use somente Bundesliga."},
    {"Liga": "Alemanha - 2. Bundesliga", "Observação": "Use somente 2. Bundesliga."},
    {"Liga": "França - Ligue 1", "Observação": "Use somente Ligue 1."},
    {"Liga": "Portugal - Primeira Liga", "Observação": "Use somente Primeira Liga."},
    {"Liga": "Holanda - Eredivisie", "Observação": "Use somente Eredivisie."},
    {"Liga": "Bélgica - Pro League", "Observação": "Use somente Pro League principal."},
    {"Liga": "Turquia - Super Lig", "Observação": "Use somente Süper Lig."},
    {"Liga": "Grécia - Super League", "Observação": "Use somente Super League Greece principal."},
]

# Catálogo histórico recuperado pelo usuário. A sincronização usa chave única e
# acrescenta apenas registros ausentes; nunca apaga ou substitui linhas remotas.
CATALOGO_RECUPERACAO_2026 = json.loads(r"""[{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Vitória Casa","Seleção":"Bodo/Glimt","Cotação":1.13,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Empate","Seleção":"Empate","Cotação":7.2,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Vitória Fora","Seleção":"Fredrikstad","Cotação":10.7,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.22,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":3.03,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.76,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"47cf8d1d","Registrado em":"2026-07-16 03:36:24","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Bodo/Glimt x Fredrikstad","Mandante":"Bodo/Glimt","Visitante":"Fredrikstad","Data do jogo":"2026-07-17","Hora do jogo":"14:15:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":1.82,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Vitória Casa","Seleção":"HamKam","Cotação":3.25,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Empate","Seleção":"Empate","Cotação":2.99,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Vitória Fora","Seleção":"Tromso","Cotação":2.11,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.92,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":1.67,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.72,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"218123bc","Registrado em":"2026-07-16 03:46:26","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"HamKam x Tromso","Mandante":"HamKam","Visitante":"Tromso","Data do jogo":"2026-07-18","Hora do jogo":"09:00:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":1.86,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Vitória Casa","Seleção":"Kristiansund","Cotação":2.9,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Empate","Seleção":"Empate","Cotação":3.38,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Vitória Fora","Seleção":"Sarpsborg 08","Cotação":2.1,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.57,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":2.09,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.45,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"512d3429","Registrado em":"2026-07-16 04:04:59","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Kristiansund x Sarpsborg 08","Mandante":"Kristiansund","Visitante":"Sarpsborg 08","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":2.28,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Vitória Casa","Seleção":"Start","Cotação":2.93,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Empate","Seleção":"Empate","Cotação":3.32,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Vitória Fora","Seleção":"Rosenborg","Cotação":2.11,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.64,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":1.96,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.52,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"0eb572ac","Registrado em":"2026-07-16 04:07:09","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Start x Rosenborg","Mandante":"Start","Visitante":"Rosenborg","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":2.17,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Vitória Casa","Seleção":"Lillestrom","Cotação":1.64,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Empate","Seleção":"Empate","Cotação":3.72,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Vitória Fora","Seleção":"KFUM Oslo","Cotação":4.2,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.61,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":2.01,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.61,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"8b0dd959","Registrado em":"2026-07-16 04:17:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Lillestrom x KFUM Oslo","Mandante":"Lillestrom","Visitante":"KFUM Oslo","Data do jogo":"2026-07-18","Hora do jogo":"11:00:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":2.02,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Vitória Casa","Seleção":"Molde","Cotação":1.97,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Empate","Seleção":"Empate","Cotação":3.52,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Vitória Fora","Seleção":"Brann","Cotação":3.7,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.48,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":2.23,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.43,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"1b3285e8","Registrado em":"2026-07-16 04:27:55","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Molde x Brann","Mandante":"Molde","Visitante":"Brann","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":2.39,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Vitória Casa","Seleção":"Viking","Cotação":1.26,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Empate","Seleção":"Empate","Cotação":5.3,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Vitória Fora","Seleção":"Sandefjord","Cotação":7.6,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Mais de 2.5 gols","Seleção":"Mais de 2.5 gols","Cotação":1.31,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Menos de 2.5 gols","Seleção":"Menos de 2.5 gols","Cotação":2.78,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Ambos marcam - Sim","Seleção":"Sim","Cotação":1.63,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"},{"ID Coleta":"79b70236","Registrado em":"2026-07-16 04:34:01","Casa de apostas":"Pixbet","Liga":"Noruega - Eliteserien","Jogo":"Viking x Sandefjord","Mandante":"Viking","Visitante":"Sandefjord","Data do jogo":"2026-07-18","Hora do jogo":"13:00:00","Mercado":"Ambos marcam - Não","Seleção":"Não","Cotação":1.99,"Banca no momento":1000.0,"Perfil":"Planilha Pura","Origem":"Manual","Observação":"Cotações salvas sem obrigação de aposta"}]""")


# ============================================================
# UTILITÁRIOS
# ============================================================

def garantir_logs() -> None:
    os.makedirs("logs", exist_ok=True)
    os.makedirs(DIRETORIO_BACKUPS, exist_ok=True)


def texto_para_float(valor) -> Optional[float]:
    if valor is None:
        return None
    txt = str(valor).strip().replace("R$", "").replace("%", "").replace(" ", "")
    if txt == "":
        return None
    try:
        if "," in txt and "." in txt:
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", ".")
        x = float(txt)
        if not np.isfinite(x):
            return None
        return x
    except Exception:
        return None


def odd_valida(odd) -> bool:
    x = texto_para_float(odd)
    return x is not None and x > 1.01 and np.isfinite(x)


def fmt_dinheiro(valor: float) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def fmt_dinheiro_texto(valor: float) -> str:
    """Moeda para textos renderizados em markdown/status/widget, sem cifrão para evitar LaTeX do Streamlit."""
    try:
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " reais"
    except Exception:
        return "0,00 reais"


def fmt_pct(valor: float, casas: int = 2) -> str:
    try:
        return f"{float(valor) * 100:.{casas}f}%".replace(".", ",")
    except Exception:
        return "0,00%"


def fmt_num(valor: float, casas: int = 2) -> str:
    try:
        return f"{float(valor):.{casas}f}".replace(".", ",")
    except Exception:
        return "0,00"


MESES_PT_BR = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def seletor_data_portugues(
    rotulo: str,
    valor: Optional[date] = None,
    chave: str = "data",
    ano_minimo: int = 2000,
    ano_maximo: Optional[int] = None,
) -> date:
    """Seletor de data totalmente em português, independente do navegador."""
    base = valor if isinstance(valor, date) else date.today()
    limite_ano = int(ano_maximo or (date.today().year + 3))
    st.markdown(f"**{rotulo}**")
    coluna_dia, coluna_mes, coluna_ano = st.columns([1, 2, 1])

    with coluna_ano:
        ano = int(st.number_input(
            "Ano",
            min_value=int(ano_minimo),
            max_value=limite_ano,
            value=int(np.clip(base.year, ano_minimo, limite_ano)),
            step=1,
            key=f"{chave}_ano",
        ))
    with coluna_mes:
        mes_nome = st.selectbox(
            "Mês",
            list(MESES_PT_BR),
            index=max(0, min(11, base.month - 1)),
            key=f"{chave}_mes",
        )
    mes = MESES_PT_BR.index(mes_nome) + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    with coluna_dia:
        dia_padrao = max(1, min(int(base.day), ultimo_dia))
        dia = int(st.selectbox(
            "Dia",
            list(range(1, ultimo_dia + 1)),
            index=dia_padrao - 1,
            key=f"{chave}_dia",
        ))
    return date(ano, mes, dia)


def remover_colunas_duplicadas(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    base = df.copy()
    base.columns = [str(c).strip() for c in base.columns]
    base = base.loc[:, ~pd.Index(base.columns).duplicated(keep="first")]
    return base


def normalizar_colunas(df: pd.DataFrame, colunas: List[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=colunas)
    base = remover_colunas_duplicadas(df)
    for col in colunas:
        if col not in base.columns:
            base[col] = ""
    return base[colunas].fillna("")


def media_simples(serie: pd.Series, padrao: float) -> float:
    try:
        s = pd.to_numeric(serie, errors="coerce").dropna()
        if s.empty:
            return float(padrao)
        return float(s.mean())
    except Exception:
        return float(padrao)


def nome_selecao(mercado: str, time_casa: str, time_fora: str) -> str:
    mapa = {
        "Vitória Casa": time_casa,
        "Empate": "Empate",
        "Vitória Fora": time_fora,
        "Mais de 2.5 gols": "Mais de 2.5 gols",
        "Menos de 2.5 gols": "Menos de 2.5 gols",
        "Ambos marcam - Sim": "Sim",
        "Ambos marcam - Não": "Não",
    }
    return mapa.get(mercado, mercado)



def grupo_mercado(mercado: object) -> str:
    """Agrupa as seleções que formam um mercado completo para retirar a margem da casa."""
    m = str(mercado or "").strip()
    if m in {"Vitória Casa", "Empate", "Vitória Fora"}:
        return "Resultado final 1X2"
    if m in {"Mais de 2.5 gols", "Menos de 2.5 gols"}:
        return "Total de gols 2.5"
    if m in {"Ambos marcam - Sim", "Ambos marcam - Não"}:
        return "Ambas marcam"
    return "Outro"


def tamanho_esperado_grupo(grupo: object) -> int:
    return {"Resultado final 1X2": 3, "Total de gols 2.5": 2, "Ambas marcam": 2}.get(str(grupo), 0)


def metricas_probabilidade_das_odds(odds: Dict[str, float]) -> Dict[str, Dict[str, object]]:
    """
    Converte as odds em probabilidade bruta e, quando todas as seleções do mercado
    estão disponíveis, calcula a margem (overround) e a probabilidade normalizada.
    """
    saida: Dict[str, Dict[str, object]] = {}
    grupos: Dict[str, List[Tuple[str, float]]] = {}

    for mercado, odd_valor in (odds or {}).items():
        odd = texto_para_float(odd_valor)
        if not odd_valida(odd):
            continue
        grupo = grupo_mercado(mercado)
        grupos.setdefault(grupo, []).append((str(mercado), float(odd)))

    for grupo, itens in grupos.items():
        esperado = tamanho_esperado_grupo(grupo)
        completo = esperado > 0 and len(itens) == esperado
        soma_bruta = sum(1.0 / odd for _, odd in itens) if itens else 0.0
        margem = soma_bruta - 1.0 if completo and soma_bruta > 0 else None

        for mercado, odd in itens:
            prob_bruta = 1.0 / odd
            prob_ajustada = (prob_bruta / soma_bruta) if completo and soma_bruta > 0 else None
            saida[mercado] = {
                "grupo": grupo,
                "completo": completo,
                "prob_bruta": prob_bruta,
                "margem_mercado": margem,
                "prob_ajustada": prob_ajustada,
            }
    return saida


def enriquecer_catalogo_probabilidades(df: pd.DataFrame) -> pd.DataFrame:
    """Migra registros antigos e recalcula as colunas derivadas sem apagar os dados originais."""
    base = normalizar_colunas(df, COLUNAS_CATALOGO).copy()
    if base.empty:
        return base

    base["Grupo do mercado"] = base["Mercado"].map(grupo_mercado)
    odds_num = pd.to_numeric(base["Cotação"], errors="coerce")
    base["Probabilidade implícita bruta %"] = np.where(odds_num > 1.0, 100.0 / odds_num, np.nan)
    base["Mercado completo"] = "Não"
    base["Margem do mercado %"] = np.nan
    base["Probabilidade ajustada sem margem %"] = np.nan

    chaves = ["ID Coleta", "Grupo do mercado"]
    for _, idxs in base.groupby(chaves, dropna=False).groups.items():
        idxs = list(idxs)
        grupo = str(base.loc[idxs[0], "Grupo do mercado"])
        esperado = tamanho_esperado_grupo(grupo)
        probs = pd.to_numeric(base.loc[idxs, "Probabilidade implícita bruta %"], errors="coerce")
        mercados_unicos = base.loc[idxs, "Mercado"].astype(str).nunique()
        completo = esperado > 0 and mercados_unicos == esperado and probs.notna().sum() == esperado
        if not completo:
            continue
        soma = float(probs.sum())
        if soma <= 0:
            continue
        base.loc[idxs, "Mercado completo"] = "Sim"
        base.loc[idxs, "Margem do mercado %"] = round(soma - 100.0, 4)
        base.loc[idxs, "Probabilidade ajustada sem margem %"] = (probs / soma * 100.0).round(4)

    for col in ["Probabilidade implícita bruta %", "Margem do mercado %", "Probabilidade ajustada sem margem %"]:
        base[col] = pd.to_numeric(base[col], errors="coerce").round(4)
    return base[COLUNAS_CATALOGO]


def enriquecer_auditoria_probabilidades(df: pd.DataFrame) -> pd.DataFrame:
    """Preenche campos derivados em registros novos e antigos sem inventar a probabilidade do modelo."""
    base = normalizar_colunas(df, COLUNAS_AUDITORIA).copy()
    if base.empty:
        return base

    odd = pd.to_numeric(base["Cotação de entrada"], errors="coerce")
    modelo_pct = pd.to_numeric(base["Chance pelo sistema %"], errors="coerce")
    ajustada_pct = pd.to_numeric(base["Probabilidade de mercado ajustada %"], errors="coerce")

    base["Probabilidade implícita bruta %"] = np.where(odd > 1.0, 100.0 / odd, np.nan)
    bruta_pct = pd.to_numeric(base["Probabilidade implícita bruta %"], errors="coerce")
    referencia_pct = ajustada_pct.where(ajustada_pct.notna(), bruta_pct)
    base["Vantagem do modelo (p.p.)"] = (modelo_pct - referencia_pct).where(modelo_pct > 0)
    base["Referência da vantagem"] = np.where(
        modelo_pct <= 0,
        "",
        np.where(ajustada_pct.notna(), "Mercado ajustado sem margem", "Mercado bruto (margem indisponível)"),
    )

    justa_atual = pd.to_numeric(base["Cotação justa"], errors="coerce")
    justa_calculada = np.where(modelo_pct > 0, 100.0 / modelo_pct, np.nan)
    base["Cotação justa"] = justa_atual.where(justa_atual.notna(), justa_calculada)
    base["Valor esperado %"] = np.where(
        (modelo_pct > 0) & (odd > 1.0),
        ((modelo_pct / 100.0) * odd - 1.0) * 100.0,
        pd.to_numeric(base["Valor esperado %"], errors="coerce"),
    )

    for col in [
        "Probabilidade implícita bruta %", "Margem do mercado %",
        "Probabilidade de mercado ajustada %", "Chance pelo sistema %",
        "Vantagem do modelo (p.p.)", "Cotação justa", "Valor esperado %",
    ]:
        base[col] = pd.to_numeric(base[col], errors="coerce").round(4)
    return base[COLUNAS_AUDITORIA]


def dataframe_para_excel_bytes(df: pd.DataFrame, nome_aba: str) -> Optional[bytes]:
    """Gera um XLSX em memória. Se o ambiente não tiver engine Excel, mantém o CSV disponível."""
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            df.to_excel(writer, index=False, sheet_name=str(nome_aba)[:31])
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        return None


def resultado_perspectiva(gf: float, gs: float) -> str:
    try:
        gf = float(gf)
        gs = float(gs)
    except Exception:
        return "-"
    if gf > gs:
        return "Vitória"
    if gf < gs:
        return "Derrota"
    return "Empate"


def montar_jogos_usados(df_jogos: pd.DataFrame, time: str, perspectiva: str) -> List[Dict[str, object]]:
    """
    Monta a lista exata de jogos que entrou nas médias do cálculo da planilha.

    perspectiva='casa': usa Home=time, gols feitos=HG, sofridos=AG.
    perspectiva='fora': usa Away=time, gols feitos=AG, sofridos=HG.
    """
    if df_jogos is None or df_jogos.empty:
        return []

    base = df_jogos.copy()
    if "DataTemp" in base.columns:
        base["DataTemp"] = pd.to_datetime(base["DataTemp"], errors="coerce")
        base = base.sort_values("DataTemp", kind="mergesort")

    registros: List[Dict[str, object]] = []
    for _, row in base.iterrows():
        mandante = str(row.get("Home", ""))
        visitante = str(row.get("Away", ""))
        hg = pd.to_numeric(row.get("HG", np.nan), errors="coerce")
        ag = pd.to_numeric(row.get("AG", np.nan), errors="coerce")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg_f = float(hg)
        ag_f = float(ag)

        if perspectiva == "casa":
            gf = hg_f
            gs = ag_f
        else:
            gf = ag_f
            gs = hg_f

        data_original = row.get("Date", "")
        data_temp = row.get("DataTemp", pd.NaT)
        try:
            if pd.notna(data_temp):
                data_txt = pd.to_datetime(data_temp).strftime("%d/%m/%Y")
            else:
                data_txt = str(data_original)
        except Exception:
            data_txt = str(data_original)

        registros.append({
            "Data": data_txt,
            "Mandante": mandante,
            "Placar": f"{int(hg_f)} x {int(ag_f)}",
            "Visitante": visitante,
            f"Resultado do {time}": resultado_perspectiva(gf, gs),
            "Gols feitos": int(gf),
            "Gols sofridos": int(gs),
        })

    return registros


def resumir_jogos_usados(jogos: List[Dict[str, object]]) -> Dict[str, object]:
    if not jogos:
        return {"Jogos": 0, "Vitórias": 0, "Empates": 0, "Derrotas": 0, "Gols feitos": 0, "Gols sofridos": 0, "Média feitos": 0.0, "Média sofridos": 0.0}
    df = pd.DataFrame(jogos)
    col_res = next((c for c in df.columns if str(c).startswith("Resultado do ")), None)
    resultados = df[col_res].astype(str) if col_res else pd.Series(dtype=str)
    gf = pd.to_numeric(df.get("Gols feitos", 0), errors="coerce").fillna(0)
    gs = pd.to_numeric(df.get("Gols sofridos", 0), errors="coerce").fillna(0)
    n = int(len(df))
    return {
        "Jogos": n,
        "Vitórias": int((resultados == "Vitória").sum()),
        "Empates": int((resultados == "Empate").sum()),
        "Derrotas": int((resultados == "Derrota").sum()),
        "Gols feitos": int(gf.sum()),
        "Gols sofridos": int(gs.sum()),
        "Média feitos": float(gf.mean()) if n else 0.0,
        "Média sofridos": float(gs.mean()) if n else 0.0,
    }


def tabela_resumo_jogos_usados(time_casa: str, time_fora: str, jogos_casa: List[Dict[str, object]], jogos_fora: List[Dict[str, object]]) -> pd.DataFrame:
    r_casa = resumir_jogos_usados(jogos_casa)
    r_fora = resumir_jogos_usados(jogos_fora)
    linhas = [
        {"Recorte usado": f"{time_casa} em casa", **r_casa},
        {"Recorte usado": f"{time_fora} fora", **r_fora},
    ]
    out = pd.DataFrame(linhas)
    for col in ["Média feitos", "Média sofridos"]:
        if col in out.columns:
            out[col] = out[col].map(lambda x: fmt_num(float(x), 2))
    return out


def render_resumo_jogos_legivel(time_casa: str, time_fora: str, jogos_casa: List[Dict[str, object]], jogos_fora: List[Dict[str, object]]) -> None:
    """Mostra os jogos usados em texto normal, sem HTML."""

    def linhas(titulo: str, jogos: List[Dict[str, object]]) -> List[str]:
        resumo = resumir_jogos_usados(jogos)
        out = [
            f"**{titulo}**",
            (
                f"- Resumo: {resumo['Jogos']} jogo(s), {resumo['Vitórias']} vitória(s), "
                f"{resumo['Empates']} empate(s), {resumo['Derrotas']} derrota(s), "
                f"{resumo['Gols feitos']} gol(s) feito(s), {resumo['Gols sofridos']} gol(s) sofrido(s), "
                f"média feita {fmt_num(float(resumo['Média feitos']), 2)}, "
                f"média sofrida {fmt_num(float(resumo['Média sofridos']), 2)}."
            ),
        ]
        if jogos:
            for j in jogos:
                resultado = next((v for k, v in j.items() if str(k).startswith("Resultado do ")), "-")
                out.append(
                    f"- {j.get('Data', '-')} — {j.get('Mandante', '-')} {j.get('Placar', '-')} {j.get('Visitante', '-')} "
                    f"| Resultado: {resultado} | Gols feitos: {j.get('Gols feitos', '-')} | Gols sofridos: {j.get('Gols sofridos', '-')}"
                )
        else:
            out.append("- Nenhum jogo entrou nesse recorte.")
        return out

    st.markdown("\n".join(linhas(f"🏠 {time_casa} em casa — texto conferível", jogos_casa)))
    st.markdown("\n".join(linhas(f"🛫 {time_fora} fora — texto conferível", jogos_fora)))


def render_alerta_lista(titulo: str, itens: List[str]) -> None:
    """Renderiza alertas em tópicos nativos, sem HTML."""
    limpos: List[str] = []
    for item in itens:
        item_txt = texto_limpo_para_tela(item)
        if item_txt and item_txt not in limpos:
            limpos.append(item_txt)
    if not limpos:
        return
    st.warning(f"{titulo}\n" + "\n".join(f"- {item}" for item in limpos))


def texto_limpo_para_tela(valor: object) -> str:
    """Remove HTML cru/acidental e frases duplicadas antes de mostrar/salvar."""
    txt = html.unescape(str(valor or ""))
    txt = re.sub(r"</p>\s*<p[^>]*>", " | ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<br\s*/?>", " | ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    txt = re.sub(r"valor matemático\s+valor positivo", "valor matemático positivo", txt, flags=re.IGNORECASE)
    txt = txt.replace("valor matemático Valor positivo", "valor matemático positivo")
    txt = txt.replace("atenção: base distante da data do jogo", "base distante da data do jogo")
    substituicoes = {
        "STAKE": "ENTRADA",
        "Stake": "Entrada",
        "stake": "entrada",
        "ODDS": "COTAÇÕES",
        "Odds": "Cotações",
        "odds": "cotações",
        "Over 2.5": "Mais de 2,5",
        "Under 2.5": "Menos de 2,5",
        "BTTS Sim": "Ambas marcam — Sim",
        "BTTS Não": "Ambas marcam — Não",
        "Green": "Vitória",
        "Red": "Derrota",
        "Void": "Anulada",
        "Cashout": "Encerramento antecipado",
    }
    for antigo, novo in substituicoes.items():
        txt = txt.replace(antigo, novo)
    return txt.strip(" |")


def limpar_dataframe_operacional(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa textos operacionais antes de exibir, salvar no estado ou mandar para auditoria."""
    if df is None or df.empty:
        return df
    out = df.copy()
    colunas_texto = [
        "Mercado", "Prioridade", "Valor matemático", "Status operacional", "Alerta de mercado",
        "Divergência mercado", "Etiquetas", "Veredito", "Motivo", "_prioridade_motivo",
    ]
    for col in colunas_texto:
        if col in out.columns:
            out[col] = out[col].map(texto_limpo_para_tela)
    return out


def _container_visual():
    """Usa card nativo quando o Streamlit suportar; cai para container comum se não suportar."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def escape_card_html(valor: object) -> str:
    """Escapa texto para HTML e blinda cifrão para o Streamlit não interpretar como fórmula."""
    txt = html.escape(str(valor or ""), quote=True)
    return txt.replace("$", "&#36;")


def render_linha_operacional_card(itens: List[Tuple[str, str]]) -> None:
    # Linha compacta premium para números do card, sem st.metric e sem markdown com R$.
    caixas = []
    for rotulo, valor in itens:
        caixas.append(
            f'''<div class="kv">
                    <div class="kv-label">{escape_card_html(rotulo)}</div>
                    <div class="kv-value">{escape_card_html(valor)}</div>
                </div>'''
        )
    st.markdown(f'<div class="kv-grid">{"".join(caixas)}</div>', unsafe_allow_html=True)


def _classe_card_prioridade(prioridade: str) -> str:
    txt = str(prioridade or "").strip()
    if txt.startswith("🟢"):
        return "high"
    if txt.startswith("🔴"):
        return "low"
    return "mid"


def _tag_pills_html(etiquetas: str) -> str:
    """Desativado: não renderiza etiquetas no card principal para evitar HTML cru na tela."""
    return ""


def _alertas_html(alertas: List[str]) -> str:
    """Desativado: alertas ficam na tabela técnica/checklist, não dentro do card principal."""
    return ""


def render_card_valor_positivo(r: pd.Series) -> None:
    # Card visual premium, sem st.metric gigante e sem risco de quebrar o R$ no markdown.
    prioridade = texto_limpo_para_tela(r.get("Prioridade", "🟠 Média"))
    prioridade_extra = texto_limpo_para_tela(r.get("_prioridade_motivo", "ordem de prioridade"))
    classe = _classe_card_prioridade(prioridade)

    def _num(col, formatter, fallback="-"):
        try:
            return formatter(float(r[col]))
        except Exception:
            return fallback

    prob = _num("Probabilidade", lambda x: fmt_pct(x, 1))
    justa = _num("Cotação justa", lambda x: fmt_num(x, 2))
    real = _num("Cotação real", lambda x: fmt_num(x, 2))
    margem = _num("Margem positiva", lambda x: fmt_pct(x, 1))
    entrada_pct = _num("Entrada %", lambda x: fmt_pct(x, 2))
    entrada_rs = _num("Entrada R$", fmt_dinheiro)

    alertas = [p.strip() for p in texto_limpo_para_tela(r.get("Alerta de mercado", "")).split("|") if p.strip()]
    etiquetas = texto_limpo_para_tela(r.get("Etiquetas", ""))
    motivo = texto_limpo_para_tela(r.get("Motivo", ""))
    status = texto_limpo_para_tela(r.get("Status operacional", "LIBERADO"))
    valor_matematico = texto_limpo_para_tela(r.get("Valor matemático", "SIM"))
    mercado = mercado_exibicao(r.get("Mercado", ""))

    html_card = f'''
    <div class="entry-card {classe}">
        <div class="entry-top">
            <span class="entry-badge">{escape_card_html(prioridade)} — {escape_card_html(prioridade_extra)}</span>
        </div>
        <div class="entry-type">Valor positivo</div>
        <div class="entry-market">{escape_card_html(mercado)}</div>
        <div class="entry-meta">
            <span class="meta-pill">Situação operacional: {escape_card_html(status)}</span>
            <span class="meta-pill">Valor matemático: {escape_card_html(valor_matematico)}</span>
        </div>
        <div class="kv-grid">
            <div class="kv"><div class="kv-label">Probabilidade</div><div class="kv-value">{escape_card_html(prob)}</div></div>
            <div class="kv"><div class="kv-label">Cotação justa</div><div class="kv-value">{escape_card_html(justa)}</div></div>
            <div class="kv"><div class="kv-label">Cotação real</div><div class="kv-value">{escape_card_html(real)}</div></div>
            <div class="kv"><div class="kv-label">Margem</div><div class="kv-value">{escape_card_html(margem)}</div></div>
            <div class="kv"><div class="kv-label">Entrada %</div><div class="kv-value">{escape_card_html(entrada_pct)}</div></div>
            <div class="kv"><div class="kv-label">Entrada em reais</div><div class="kv-value">{escape_card_html(entrada_rs)}</div></div>
        </div>
    </div>
    '''
    st.markdown(html_card, unsafe_allow_html=True)


# ============================================================
# DADOS HISTÓRICOS
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def carregar_dados_liga(url: str, janela: int = 0) -> pd.DataFrame:
    """
    Carrega a base da liga.

    janela = 0 significa: usa todos os jogos disponíveis no CSV,
    que é o comportamento mais fiel à planilha original.
    """
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df = df.rename(columns={"HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG"})
        obrigatorias = ["Home", "Away", "HG", "AG"]
        if not all(c in df.columns for c in obrigatorias):
            return pd.DataFrame()
        df = df.dropna(subset=obrigatorias).copy()
        df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
        df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
        df = df.dropna(subset=["HG", "AG"])
        if "Date" in df.columns:
            df["DataTemp"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.sort_values("DataTemp", kind="mergesort")

        try:
            janela_int = int(janela)
        except Exception:
            janela_int = 0

        if janela_int and janela_int > 0:
            janela_int = int(np.clip(janela_int, 40, 1500))
            df = df.tail(janela_int)

        return df.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def rotulo_janela(janela: int) -> str:
    try:
        janela = int(janela)
    except Exception:
        janela = 0
    if janela <= 0:
        return "Temporada inteira / todos os jogos do CSV"
    return f"Últimos {janela} jogos"


def aplicar_recorte_historico(
    df: pd.DataFrame,
    modo: str,
    url: str = "",
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
) -> pd.DataFrame:
    """
    Aplica o recorte histórico sem mexer no motor da planilha.

    - Temporada atual: nos CSVs /new/ do football-data, usa o ano do último jogo disponível.
      Nos CSVs de temporada específica (ex: /2526/E0.csv), usa o arquivo inteiro.
    - Histórico completo: usa tudo.
    - Últimos N jogos: usa tail(N).
    - Data personalizada: filtra pelo intervalo escolhido.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    modo = str(modo or "Temporada atual")

    if modo.startswith("Últimos"):
        try:
            n = int(modo.split()[1])
        except Exception:
            n = 300
        return out.tail(max(1, n)).reset_index(drop=True)

    if "DataTemp" in out.columns:
        out["DataTemp"] = pd.to_datetime(out["DataTemp"], errors="coerce")
        out = out.sort_values("DataTemp", kind="mergesort")

    if modo == "Data personalizada" and "DataTemp" in out.columns:
        if data_inicio:
            out = out[out["DataTemp"] >= pd.Timestamp(data_inicio)]
        if data_fim:
            out = out[out["DataTemp"] <= pd.Timestamp(data_fim)]
        return out.reset_index(drop=True)

    if modo == "Histórico completo":
        return out.reset_index(drop=True)

    # Temporada atual
    if "DataTemp" in out.columns and out["DataTemp"].notna().any():
        # Arquivos /new/ costumam acumular histórico. Para eles, ano do último jogo = temporada atual.
        if "/new/" in str(url):
            ultimo_ano = int(out["DataTemp"].dropna().max().year)
            atual = out[out["DataTemp"].dt.year == ultimo_ano].copy()
            if not atual.empty:
                return atual.reset_index(drop=True)

    # Arquivos mmz4281/2526 já são de uma temporada específica.
    return out.reset_index(drop=True)


def resumo_base_dados(df: pd.DataFrame) -> Dict[str, object]:
    if df is None or df.empty:
        return {"jogos": 0, "inicio": "-", "fim": "-", "times": 0, "inicio_data": None, "fim_data": None}
    inicio = fim = "sem data"
    inicio_data = fim_data = None
    if "DataTemp" in df.columns and pd.to_datetime(df["DataTemp"], errors="coerce").notna().any():
        datas = pd.to_datetime(df["DataTemp"], errors="coerce").dropna()
        dmin = datas.min()
        dmax = datas.max()
        inicio_data = dmin.strftime("%Y-%m-%d")
        fim_data = dmax.strftime("%Y-%m-%d")
        inicio = dmin.strftime("%d/%m/%Y")
        fim = dmax.strftime("%d/%m/%Y")
    home = df.get("Home", pd.Series(dtype=str)).dropna().astype(str)
    away = df.get("Away", pd.Series(dtype=str)).dropna().astype(str)
    times = sorted(set(home) | set(away))
    return {"jogos": int(len(df)), "inicio": inicio, "fim": fim, "times": int(len(times)), "inicio_data": inicio_data, "fim_data": fim_data}

def texto_base_dados(resumo: Dict[str, object], modo: str) -> str:
    return f"Base usada: {html.escape(str(modo))} | Período: {resumo.get('inicio', '-')} até {resumo.get('fim', '-')} | Jogos: {resumo.get('jogos', 0)} | Times: {resumo.get('times', 0)}"



def dias_base_ate_jogo(resumo: Dict[str, object], data_jogo: object) -> Optional[int]:
    """Distância em dias entre a última data da base usada e a data do jogo analisado."""
    try:
        fim = resumo.get("fim_data") if isinstance(resumo, dict) else None
        if not fim or str(fim).lower() in {"none", "-", "sem data"}:
            return None
        dt_base = pd.to_datetime(fim, errors="coerce")
        dt_jogo = pd.to_datetime(data_jogo, errors="coerce")
        if pd.isna(dt_base) or pd.isna(dt_jogo):
            return None
        return int((dt_jogo.normalize() - dt_base.normalize()).days)
    except Exception:
        return None


def append_tag_texto(valor: object, *tags: str) -> str:
    existentes: List[str] = []
    for parte in str(valor or "").split(";"):
        parte = parte.strip()
        if parte:
            existentes.append(parte)
    for tag in tags:
        tag = str(tag or "").strip()
        if tag and tag not in existentes:
            existentes.append(tag)
    return "; ".join(existentes)


def classificar_divergencia_mercado(prob_app: float, odd_real: float, mercado: str, margem: float, alertas: List[str]) -> Tuple[str, float, float]:
    """
    Índice simples e auditável de divergência com o mercado.
    Usa apenas probabilidade do modelo e probabilidade implícita bruta da cotação real.
    Não é filtro subjetivo; é alerta operacional.
    """
    try:
        prob_app = float(prob_app)
        odd_real = float(odd_real)
        prob_mercado = 1.0 / odd_real if odd_real > 1 else 0.0
        dif = prob_app - prob_mercado
    except Exception:
        return "INDEFINIDA", 0.0, 0.0

    texto_alerta = " ".join(str(a).lower() for a in (alertas or []))
    extremo_por_1x2 = str(mercado) in {"Vitória Casa", "Vitória Fora"} and prob_app >= 0.50 and odd_real >= 3.00
    extremo_por_dif = abs(dif) >= 0.25 and ("favorito do mercado" in texto_alerta or "cotação real muito acima" in texto_alerta)
    if extremo_por_1x2 or extremo_por_dif:
        nivel = "EXTREMA"
    elif abs(dif) >= 0.18 or "favorito do mercado" in texto_alerta:
        nivel = "FORTE"
    elif abs(dif) >= 0.10 or bool(alertas):
        nivel = "MÉDIA"
    else:
        nivel = "NORMAL"
    return nivel, prob_mercado, dif


def aplicar_alerta_base_distante(resultados: pd.DataFrame, dias_distante: Optional[int]) -> pd.DataFrame:
    if resultados is None or resultados.empty or dias_distante is None or dias_distante <= 14:
        return resultados

    out = resultados.copy()

    # Garante colunas necessárias antes de usar .at[row, col].
    # O erro da V19.4 acontecia porque o código tentou usar out.at[idx].get(...),
    # mas .at sempre precisa de linha E coluna no pandas.
    for coluna in ["Etiquetas", "Motivo", "Prioridade", "_prioridade_score", "_prioridade_motivo", "Veredito"]:
        if coluna not in out.columns:
            out[coluna] = ""

    tag = "Base distante da data do jogo"
    detalhe = f"base distante da data do jogo ({dias_distante} dias desde o último jogo da base)"

    for idx in out.index:
        veredito = str(out.at[idx, "Veredito"] or "")
        if veredito == "VALOR POSITIVO":
            etiquetas_atuais = str(out.at[idx, "Etiquetas"] or "")
            motivo_atual = str(out.at[idx, "Motivo"] or "")
            prioridade_atual = str(out.at[idx, "Prioridade"] or "")

            out.at[idx, "Etiquetas"] = append_tag_texto(etiquetas_atuais, tag)
            out.at[idx, "Motivo"] = (motivo_atual + f" | atenção: {detalhe}.").strip()

            # Base muito distante não transforma valor em lixo, mas impede leitura alta.
            if prioridade_atual.startswith("🟢"):
                out.at[idx, "Prioridade"] = "🟠 Média"
                out.at[idx, "_prioridade_score"] = 2
                out.at[idx, "_prioridade_motivo"] = "valor positivo, mas a base está distante da data do jogo"

    return out

def render_stat_card(label: str, value: object, hint: str = "", icon: str = "") -> None:
    st.markdown(
        f'''
        <div class="stat-card">
            <div class="stat-label">{html.escape(str(icon + " " + label).strip())}</div>
            <div class="stat-value">{html.escape(str(value))}</div>
            <div class="stat-hint">{html.escape(str(hint))}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def classe_confianca(nivel: str) -> str:
    n = str(nivel).lower()
    if "robusta" in n or "adequada" in n:
        return "confidence-good"
    if "mínima" in n or "minima" in n:
        return "confidence-mid"
    return "confidence-low"


def render_botao_confianca(conf: Dict[str, object]) -> None:
    nivel = str(conf.get("nível", "-"))
    motivos = str(conf.get("motivos", ""))
    classe = classe_confianca(nivel)
    nl = nivel.lower()
    icone = "🟢" if ("robusta" in nl or "adequada" in nl) else ("🟠" if ("mínima" in nl or "minima" in nl) else "🔴")
    st.markdown(
        f'''
        <div class="confidence-button {classe}">
            <span>{icone}</span><span>QUALIDADE DOS DADOS: {html.escape(nivel.upper())}</span>
        </div>
        <div class="muted" style="margin-top:-6px;margin-bottom:10px;font-weight:700;">{html.escape(motivos)}</div>
        ''',
        unsafe_allow_html=True,
    )


def prioridade_aposta(
    prob: float,
    margem: float,
    entrada: float,
    veredito: str,
    status_operacional: str = "",
    amostra_minima: int = 0,
) -> Tuple[str, int, str]:
    if str(veredito) != "VALOR POSITIVO" or margem <= 0 or entrada <= 0:
        return "—", 0, "sem prioridade"

    # Prioridade combina valor, chance e tamanho natural da entrada.
    # Não bloqueia a entrada; só ordena a leitura operacional.
    if entrada >= 0.025 or (margem >= 0.12 and prob >= 0.45):
        prioridade, score, motivo = "🟢 Alta", 3, "melhor equilíbrio entre margem, probabilidade e entrada"
    elif entrada >= 0.010 or (margem >= 0.075 and prob >= 0.40):
        prioridade, score, motivo = "🟠 Média", 2, "valor válido, mas não é a melhor da tela"
    else:
        prioridade, score, motivo = "🔴 Fraca", 1, "valor existe, porém é a mais volátil/fraca da lista"

    # Régua operacional de amostra:
    # 0 a 4 jogos: baixa; 5 a 7: mínima aprovada; 8 a 12: boa; 13+: forte.
    # Amostra mínima aprovada não é a mesma coisa que amostra boa.
    amostra = int(amostra_minima or 0)
    status = str(status_operacional or "").upper()

    if "DIVERGÊNCIA CRÍTICA" in status:
        return "🟠 Média", 2, "forte diferença em relação ao mercado; entrada reduzida, mas a tese interna permanece válida"

    if "DIVERGÊNCIA EXTREMA" in status:
        return "🔴 Baixa", 1, "valor contra o mercado; exige confirmação manual antes de apostar"

    if amostra < 5 or "AMOSTRA BAIXA" in status:
        return "🔴 Fraca", 1, "valor matemático existe, mas a amostra baixa limita a prioridade operacional"

    if "DIVERGÊNCIA FORTE" in status and score > 2:
        return "🟠 Média", 2, "valor forte, mas há divergência importante com o mercado"

    if 5 <= amostra <= 7 and score > 2:
        return "🟠 Média", 2, "valor forte, mas amostra mínima aprovada ainda limita a prioridade operacional"

    return prioridade, score, motivo


def mercado_exibicao(mercado: object) -> str:
    """Texto exibido para o usuário, sem mexer na chave interna do cálculo."""
    return str(mercado).replace("2.5", "2,5")


def _odd_numero_segura(odds: Dict[str, float], mercado: str) -> Optional[float]:
    try:
        odd = texto_para_float(odds.get(mercado))
        if odd is not None and odd_valida(odd):
            return float(odd)
    except Exception:
        pass
    return None


def detectar_alertas_mercado(
    mercado: str,
    odd_real: float,
    odd_justa: float,
    margem: float,
    odds: Dict[str, float],
) -> List[str]:
    """
    Alerta operacional: mostra quando o modelo está muito contra o mercado.
    Não bloqueia e não altera o cálculo da planilha; serve para evitar erro de cotação,
    mandante/visitante invertido, jogo errado ou contexto que a base não sabe.
    """
    alertas: List[str] = []
    mercado = str(mercado)
    try:
        razao = float(odd_real) / max(float(odd_justa), 1e-9)
    except Exception:
        razao = 0.0

    # Cotação real muito acima da justa é bom matematicamente, mas exige conferência.
    if margem >= 0.80 or razao >= 1.70:
        alertas.append(
            "cotação real muito acima da cotação justa; confira se o mercado, mandante/visitante e cotação foram digitados corretamente"
        )

    # Resultado final: alerta quando o modelo encontra valor forte contra o favorito do mercado.
    if mercado in {"Vitória Casa", "Vitória Fora"}:
        odds_1x2 = {
            "Vitória Casa": _odd_numero_segura(odds, "Vitória Casa"),
            "Empate": _odd_numero_segura(odds, "Empate"),
            "Vitória Fora": _odd_numero_segura(odds, "Vitória Fora"),
        }
        odds_validas = {k: v for k, v in odds_1x2.items() if v is not None}
        if len(odds_validas) >= 2:
            favorito_mercado = min(odds_validas, key=odds_validas.get)
            if favorito_mercado != mercado and (margem >= 0.35 or razao >= 1.40):
                alertas.append(
                    f"modelo contra o favorito do mercado: a menor cotação do resultado final é {mercado_exibicao(favorito_mercado)}, mas o modelo encontrou valor em {mercado_exibicao(mercado)}"
                )

    # Mercado de gols: alerta quando a casa favorece o lado contrário.
    if mercado == "Menos de 2.5 gols":
        odd_mais = _odd_numero_segura(odds, "Mais de 2.5 gols")
        if odd_mais is not None and odd_mais < float(odd_real) and margem >= 0.12:
            alertas.append("mercado de gols favorece Mais de 2,5 gols, mas o modelo encontrou valor em Menos de 2,5 gols")
    elif mercado == "Mais de 2.5 gols":
        odd_menos = _odd_numero_segura(odds, "Menos de 2.5 gols")
        if odd_menos is not None and odd_menos < float(odd_real) and margem >= 0.12:
            alertas.append("mercado de gols favorece Menos de 2,5 gols, mas o modelo encontrou valor em Mais de 2,5 gols")

    # Ambos marcam: alerta quando a casa favorece o lado contrário.
    if mercado == "Ambos marcam - Não":
        odd_sim = _odd_numero_segura(odds, "Ambos marcam - Sim")
        if odd_sim is not None and odd_sim < float(odd_real) and margem >= 0.12:
            alertas.append("mercado de ambos marcam favorece Sim, mas o modelo encontrou valor em Não")
    elif mercado == "Ambos marcam - Sim":
        odd_nao = _odd_numero_segura(odds, "Ambos marcam - Não")
        if odd_nao is not None and odd_nao < float(odd_real) and margem >= 0.12:
            alertas.append("mercado de ambos marcam favorece Não, mas o modelo encontrou valor em Sim")

    # Remove duplicidades preservando ordem.
    vistos = set()
    saida = []
    for a in alertas:
        if a not in vistos:
            vistos.add(a)
            saida.append(a)
    return saida


def detectar_correlacao_operacional(aprovadas: pd.DataFrame, calc: Dict[str, object]) -> List[str]:
    """
    Mostra correlação operacional entre entradas do mesmo jogo.
    Não bloqueia e não altera o motor da planilha; só impede tratar 3 entradas do
    mesmo roteiro como se fossem oportunidades independentes.
    """
    if aprovadas is None or aprovadas.empty or "Mercado" not in aprovadas.columns:
        return []

    mercados = set(aprovadas["Mercado"].astype(str).tolist())
    avisos: List[str] = []

    if {"Menos de 2.5 gols", "Ambos marcam - Não"}.issubset(mercados):
        avisos.append("Menos de 2,5 e Ambos marcam - Não são altamente correlacionados; não trate como duas entradas independentes.")

    if {"Mais de 2.5 gols", "Ambos marcam - Sim"}.issubset(mercados):
        avisos.append("Mais de 2,5 e Ambos marcam - Sim são altamente correlacionados; não trate como duas entradas independentes.")

    gols_casa = float(calc.get("gols_esperados_casa", 0.0) or 0.0)
    gols_fora = float(calc.get("gols_esperados_fora", 0.0) or 0.0)

    if "Vitória Fora" in mercados and ({"Menos de 2.5 gols", "Ambos marcam - Não"} & mercados) and gols_fora > gols_casa:
        avisos.append("Vitória Fora junto com Menos de 2,5 gols ou Ambos marcam - Não concentra exposição no roteiro de visitante superior e jogo controlado.")

    if "Vitória Casa" in mercados and ({"Menos de 2.5 gols", "Ambos marcam - Não"} & mercados) and gols_casa > gols_fora:
        avisos.append("Vitória Casa junto com Menos de 2,5 gols ou Ambos marcam - Não concentra exposição no roteiro de mandante superior e jogo controlado.")

    if len(aprovadas) >= 3:
        avisos.append("Há 3 ou mais entradas no mesmo jogo. Para gestão conservadora, escolha a principal ou reduza a exposição total do jogo.")

    return avisos



def ajustar_exposicao_correlacionada(
    resultados: pd.DataFrame,
    banca: float,
    politica: str = "Dividir a entrada entre correlacionados",
) -> pd.DataFrame:
    """Aplica uma política clara aos pares que descrevem praticamente o mesmo roteiro."""
    if resultados is None or resultados.empty:
        return resultados
    out = resultados.copy()
    politica_txt = str(politica or "Somente avisar")
    if "Somente avisar" in politica_txt:
        return out

    pares = [
        ("Mais de 2.5 gols", "Ambos marcam - Sim"),
        ("Menos de 2.5 gols", "Ambos marcam - Não"),
    ]
    for mercado_a, mercado_b in pares:
        idxs = []
        for mercado in (mercado_a, mercado_b):
            candidatos = out.index[
                out["Mercado"].astype(str).eq(mercado)
                & out["Veredito"].astype(str).eq("VALOR POSITIVO")
                & (pd.to_numeric(out["Entrada %"], errors="coerce").fillna(0.0) > 0)
            ].tolist()
            idxs.extend(candidatos)
        if len(idxs) != 2:
            continue

        if "Manter somente" in politica_txt:
            principal = max(
                idxs,
                key=lambda i: (
                    float(pd.to_numeric(out.at[i, "_coerencia_score"], errors="coerce") or 0.0) if "_coerencia_score" in out.columns else 0.0,
                    float(pd.to_numeric(out.at[i, "_prioridade_score"], errors="coerce") or 0.0),
                    float(pd.to_numeric(out.at[i, "Margem positiva"], errors="coerce") or 0.0),
                    float(pd.to_numeric(out.at[i, "Probabilidade"], errors="coerce") or 0.0),
                ),
            )
            for idx in idxs:
                if idx == principal:
                    out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], "Principal entre correlacionadas")
                    out.at[idx, "Motivo"] = str(out.at[idx, "Motivo"]) + " | mantida como principal entre mercados correlacionados."
                    continue
                out.at[idx, "Entrada teórica %"] = 0.0
                out.at[idx, "Entrada teórica R$"] = 0.0
                out.at[idx, "Entrada %"] = 0.0
                out.at[idx, "Entrada R$"] = 0.0
                out.at[idx, "Veredito"] = "ESTUDO"
                out.at[idx, "Status operacional"] = "CORRELACIONADA — SOMENTE PRINCIPAL"
                out.at[idx, "Prioridade"] = "—"
                out.at[idx, "_prioridade_score"] = 0
                out.at[idx, "_prioridade_motivo"] = "valor preservado para estudo; exposição concentrada na principal"
                out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], "Correlacionada sem entrada")
                out.at[idx, "Motivo"] = str(out.at[idx, "Motivo"]) + " | entrada zerada porque a política mantém somente a principal do par correlacionado."
        else:
            # O orçamento do par vira a maior stake individual, em vez da soma das duas.
            stakes = [max(0.0, float(pd.to_numeric(out.at[i, "Entrada %"], errors="coerce") or 0.0)) for i in idxs]
            orcamento_par = max(stakes)
            pesos = [max(0.0001, float(pd.to_numeric(out.at[i, "Margem positiva"], errors="coerce") or 0.0)) for i in idxs]
            soma_pesos = sum(pesos)
            for idx, peso in zip(idxs, pesos):
                nova_stake = orcamento_par * peso / soma_pesos
                out.at[idx, "Entrada teórica %"] = nova_stake
                out.at[idx, "Entrada teórica R$"] = float(banca) * nova_stake
                out.at[idx, "Entrada %"] = nova_stake
                out.at[idx, "Entrada R$"] = float(banca) * nova_stake
                out.at[idx, "Status operacional"] = str(out.at[idx, "Status operacional"]).replace(" — ENTRADA CORRELACIONADA DIVIDIDA", "") + " — ENTRADA CORRELACIONADA DIVIDIDA"
                out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], "Entrada correlacionada dividida")
                out.at[idx, "Motivo"] = str(out.at[idx, "Motivo"]) + " | entrada do par correlacionado dividida sem duplicar a exposição."

    return out


def formatar_tabela_estabilidade(estabilidade: Dict[str, object]) -> pd.DataFrame:
    linhas = estabilidade.get("linhas", []) if isinstance(estabilidade, dict) else []
    if not linhas:
        return pd.DataFrame()
    out = pd.DataFrame(linhas)
    for col in ["Gols casa", "Gols fora"]:
        if col in out.columns:
            out[col] = out[col].map(lambda x: "-" if pd.isna(x) else fmt_num(float(x), 2))
    for col in ["Vitória Casa", "Empate", "Vitória Fora", "Over 2.5", "Under 2.5", "BTTS Sim", "BTTS Não"]:
        if col in out.columns:
            out[col] = out[col].map(lambda x: "-" if pd.isna(x) else fmt_pct(float(x), 1))
    return out.rename(columns={
        "Over 2.5": "Mais de 2,5",
        "Under 2.5": "Menos de 2,5",
        "BTTS Sim": "Ambas marcam — Sim",
        "BTTS Não": "Ambas marcam — Não",
    })


def _linhas_unicas_texto(valores) -> List[str]:
    saida: List[str] = []
    for valor in valores or []:
        for parte in str(valor or "").split("|"):
            limpo = texto_limpo_para_tela(parte)
            if limpo and limpo not in saida:
                saida.append(limpo)
    return saida


def gerar_resumo_compartilhavel(
    analise: Dict[str, object],
    calc: Dict[str, object],
    resultados: pd.DataFrame,
    aprovadas: pd.DataFrame,
    confianca: Dict[str, object],
    estabilidade: Optional[Dict[str, object]] = None,
) -> str:
    """Gera um texto completo, determinístico e fácil de copiar para outra conversa."""
    cfg = analise.get("config", {}) or {}
    periodo = cfg.get("periodo_base", {}) or {}
    linhas: List[str] = []
    linhas.append("RESUMO — TEX ESTATÍSTICAS V20.3.5")
    linhas.append(f"Jogo: {analise.get('jogo', '-')}")
    linhas.append(f"Liga: {analise.get('liga', '-')} | Casa de apostas: {analise.get('casa_apostas', '-')} | Origem das cotações: {analise.get('origem', '-')}")
    linhas.append(
        f"Base: {cfg.get('janela', '-')} | Período: {periodo.get('inicio', '-')} a {periodo.get('fim', '-')} | "
        f"Jogos da liga: {periodo.get('jogos', 0)} | Times: {periodo.get('times', 0)}"
    )
    dias = cfg.get("dias_base_jogo")
    if dias is not None:
        linhas.append(f"Distância entre a última partida da base e o jogo: {dias} dia(s).")

    regressao = bool(calc.get("regressao_media_ativa", False))
    peso = float(calc.get("peso_media_liga", 0.0) or 0.0)
    linhas.append(
        f"Modelo: Poisson casa/fora; regressão à média da liga {'ATIVA em ' + fmt_pct(peso, 0) if regressao else 'DESATIVADA'}; "
        f"peso empírico em gols/ambas marcam {fmt_pct(float(calc.get('peso_prob_empirica', 0.0)), 0)}; "
        f"amostra mínima configurada: {cfg.get('amostra_minima', '-')} jogo(s)."
    )
    linhas.append(
        f"Amostra usada: {analise.get('time_casa', '-')} em casa = {calc.get('jogos_casa', 0)}; "
        f"{analise.get('time_fora', '-')} fora = {calc.get('jogos_fora', 0)}."
    )
    linhas.append(
        f"Médias observadas: casa marcou {fmt_num(calc.get('gols_feitos_casa_bruto', calc.get('gols_feitos_casa', 0)), 2)} e sofreu "
        f"{fmt_num(calc.get('gols_sofridos_casa_bruto', calc.get('gols_sofridos_casa', 0)), 2)}; visitante marcou "
        f"{fmt_num(calc.get('gols_feitos_fora_bruto', calc.get('gols_feitos_fora', 0)), 2)} e sofreu "
        f"{fmt_num(calc.get('gols_sofridos_fora_bruto', calc.get('gols_sofridos_fora', 0)), 2)}."
    )
    if regressao:
        linhas.append(
            f"Médias após ajuste: casa marcou {fmt_num(calc.get('gols_feitos_casa', 0), 2)} e sofreu {fmt_num(calc.get('gols_sofridos_casa', 0), 2)}; "
            f"visitante marcou {fmt_num(calc.get('gols_feitos_fora', 0), 2)} e sofreu {fmt_num(calc.get('gols_sofridos_fora', 0), 2)}."
        )
    linhas.append(
        f"Gols projetados: {analise.get('time_casa', '-')} {fmt_num(calc.get('gols_esperados_casa', 0), 2)} x "
        f"{fmt_num(calc.get('gols_esperados_fora', 0), 2)} {analise.get('time_fora', '-')} "
        f"(total {fmt_num(float(calc.get('gols_esperados_casa', 0)) + float(calc.get('gols_esperados_fora', 0)), 2)})."
    )
    linhas.append(f"Qualidade dos dados: {confianca.get('nível', '-')} — {confianca.get('motivos', '-')}")
    linhas.append(f"Validação histórica: {confianca.get('calibração', 'Em acompanhamento')}.")

    if estabilidade:
        linhas.append(f"Estabilidade 5/8/12: {estabilidade.get('nivel', '-')} — {estabilidade.get('motivo', '-')}")
        for r in estabilidade.get("linhas", []):
            if r.get("Situação") != "completa":
                linhas.append(f"  Janela {r.get('Janela')}: {r.get('Situação')}")
            else:
                linhas.append(
                    f"  Janela {r.get('Janela')}: casa {fmt_num(r.get('Gols casa', 0), 2)}, fora {fmt_num(r.get('Gols fora', 0), 2)}, "
                    f"1X2 {fmt_pct(r.get('Vitória Casa', 0), 1)}/{fmt_pct(r.get('Empate', 0), 1)}/{fmt_pct(r.get('Vitória Fora', 0), 1)}, "
                    f"Mais de 2,5 {fmt_pct(r.get('Over 2.5', 0), 1)}, Ambas marcam — Sim {fmt_pct(r.get('BTTS Sim', 0), 1)}."
                )

    linhas.append("Probabilidades do motor:")
    p_final = calc.get("probabilidades", {}) or {}
    p_pois = calc.get("probabilidades_poisson", {}) or {}
    p_emp = calc.get("probabilidades_empiricas", {}) or {}
    for mercado in MERCADOS_NUCLEO:
        extra = ""
        if mercado in {"Mais de 2.5 gols", "Menos de 2.5 gols", "Ambos marcam - Sim", "Ambos marcam - Não"}:
            extra = f" | Poisson {fmt_pct(float(p_pois.get(mercado, 0.0)), 1)} | empírico {fmt_pct(float(p_emp.get(mercado, 0.0)), 1)}"
        linhas.append(f"  - {mercado_exibicao(mercado)}: operacional {fmt_pct(float(p_final.get(mercado, 0.0)), 1)}{extra}")
    linhas.append(
        f"Coerência simples: total projetado {fmt_num(float(calc.get('gols_total_esperado', 0.0)), 2)}; "
        f"placar arredondado {calc.get('placar_arredondado_casa', 0)} x {calc.get('placar_arredondado_fora', 0)} (apenas visual)."
    )
    linhas.append(
        f"Chance individual de marcar: mandante {fmt_pct(float(calc.get('prob_casa_marcar', 0.0)), 1)}; "
        f"visitante {fmt_pct(float(calc.get('prob_fora_marcar', 0.0)), 1)}."
    )

    if resultados is None or resultados.empty:
        linhas.append("Nenhuma cotação válida foi comparada.")
    else:
        linhas.append("Mercados avaliados:")
        for _, r in resultados.iterrows():
            linhas.append(
                f"  - {mercado_exibicao(r.get('Mercado', '-'))}: prob. {fmt_pct(float(r.get('Probabilidade', 0)), 1)}, "
                f"cotação justa {fmt_num(float(r.get('Cotação justa', 0)), 2)}, cotação real {fmt_num(float(r.get('Cotação real', 0)), 2)}, "
                f"valor esperado {fmt_pct(float(r.get('Margem positiva', 0)), 1)}, situação {texto_limpo_para_tela(r.get('Status operacional', '-'))}, "
                f"direção algébrica {texto_limpo_para_tela(r.get('Direção algébrica', '-'))}, "
                f"entrada final {fmt_pct(float(r.get('Entrada %', 0)), 2)} ({fmt_dinheiro(float(r.get('Entrada R$', 0)))})."
            )

    if aprovadas is not None and not aprovadas.empty:
        total = float(pd.to_numeric(aprovadas["Entrada R$"], errors="coerce").fillna(0.0).sum())
        principal = aprovadas.sort_values(["_prioridade_score", "Margem positiva"], ascending=[False, False]).iloc[0]
        linhas.append(
            f"Entradas efetivas: {len(aprovadas)} | exposição total: {fmt_dinheiro(total)} "
            f"({fmt_pct(total / float(analise.get('banca', 1) or 1), 2)} da banca)."
        )
        linhas.append(f"Mercado operacional prioritário após as travas: {mercado_exibicao(principal.get('Mercado', '-'))}.")
    else:
        linhas.append("Nenhuma entrada efetiva foi liberada pela configuração atual.")

    alertas_correlacao = detectar_correlacao_operacional(aprovadas, calc) if aprovadas is not None else []
    alertas_mercado = _linhas_unicas_texto(resultados.get("Alerta de mercado", pd.Series(dtype=str)).tolist() if resultados is not None and not resultados.empty and "Alerta de mercado" in resultados.columns else [])
    if alertas_correlacao or alertas_mercado:
        linhas.append("Alertas:")
        for alerta in alertas_correlacao + alertas_mercado:
            linhas.append(f"  - {texto_limpo_para_tela(alerta)}")

    linhas.append(
        f"Gestão: teto por entrada {fmt_pct(float(cfg.get('teto_por_entrada', 0)), 1)}; teto total por jogo {fmt_pct(float(cfg.get('teto_por_jogo', 0)), 1)}; "
        f"correlação: {cfg.get('politica_correlacao', 'Somente avisar')}."
    )
    linhas.append("Observação: o resumo reproduz o cálculo do aplicativo; não incorpora automaticamente escalações, lesões ou notícias externas.")
    return "\n".join(linhas)

def prioridade_classe(prioridade: str) -> str:
    p = str(prioridade).lower()
    if "alta" in p:
        return "priority-high"
    if "média" in p or "media" in p:
        return "priority-medium"
    return "priority-low"


def matriz_poisson(gols_casa: float, gols_fora: float, tamanho: int = 15) -> np.ndarray:
    matriz = np.zeros((tamanho, tamanho), dtype=float)
    for g_casa in range(tamanho):
        for g_fora in range(tamanho):
            matriz[g_casa, g_fora] = poisson.pmf(g_casa, gols_casa) * poisson.pmf(g_fora, gols_fora)
    soma = float(matriz.sum())
    if soma > 0:
        matriz /= soma
    return matriz


def _ordenar_e_limitar_jogos(df: pd.DataFrame, limite_jogos: Optional[int] = None) -> pd.DataFrame:
    """Ordena cronologicamente e, se solicitado, mantém apenas os jogos mais recentes."""
    if df is None or df.empty:
        return pd.DataFrame(columns=getattr(df, "columns", []))
    out = df.copy()
    if "DataTemp" in out.columns:
        out["DataTemp"] = pd.to_datetime(out["DataTemp"], errors="coerce")
        out = out.sort_values("DataTemp", kind="mergesort")
    if limite_jogos is not None:
        try:
            n = max(1, int(limite_jogos))
            out = out.tail(n)
        except Exception:
            pass
    return out.reset_index(drop=True)


def _regredir_media(valor_time: float, media_liga: float, ativa: bool, peso_liga: float) -> float:
    """Combina a média recente do time com a média da liga sem esconder o valor bruto."""
    try:
        valor = float(valor_time)
        liga = float(media_liga)
        peso = float(np.clip(peso_liga, 0.0, 0.80)) if ativa else 0.0
        return float((1.0 - peso) * valor + peso * liga)
    except Exception:
        return float(media_liga)



def filtrar_base_antes_do_jogo(df: pd.DataFrame, data_jogo: object) -> Tuple[pd.DataFrame, int]:
    """Remove partidas disputadas na data do evento ou depois dela.

    A previsão deve usar somente informação conhecida antes do jogo. Isso evita
    vazamento temporal quando uma partida antiga é reanalisada com a base atual.
    Retorna a base filtrada e quantas linhas posteriores foram removidas.
    """
    if df is None or df.empty or "DataTemp" not in df.columns:
        return (df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()), 0
    try:
        limite = pd.to_datetime(data_jogo, errors="coerce")
        if pd.isna(limite):
            return df.copy(), 0
        out = df.copy()
        out["DataTemp"] = pd.to_datetime(out["DataTemp"], errors="coerce")
        validas = out["DataTemp"].isna() | (out["DataTemp"].dt.normalize() < limite.normalize())
        removidas = int((~validas).sum())
        return out.loc[validas].reset_index(drop=True), removidas
    except Exception:
        return df.copy(), 0


def _taxa_binaria(df: pd.DataFrame, tipo: str) -> Tuple[int, int, float]:
    """Conta eventos de gols sem esconder o tamanho da amostra."""
    if df is None or df.empty:
        return 0, 0, 0.0
    hg = pd.to_numeric(df.get("HG"), errors="coerce")
    ag = pd.to_numeric(df.get("AG"), errors="coerce")
    validas = hg.notna() & ag.notna()
    hg, ag = hg[validas], ag[validas]
    n = int(validas.sum())
    if n <= 0:
        return 0, 0, 0.0
    if tipo == "over25":
        eventos = (hg + ag >= 3)
    elif tipo == "btts":
        eventos = (hg >= 1) & (ag >= 1)
    else:
        raise ValueError(f"Tipo binário desconhecido: {tipo}")
    sucessos = int(eventos.sum())
    return n, sucessos, float(sucessos / n)


def _suavizar_taxa(sucessos: int, n: int, taxa_liga: float, forca_prior: float = 6.0) -> float:
    """Suavização beta-binomial simples: amostras pequenas voltam para a liga."""
    n = max(0, int(n))
    sucessos = int(np.clip(int(sucessos), 0, n)) if n else 0
    prior = float(max(0.0, forca_prior))
    liga = float(np.clip(taxa_liga, 0.0, 1.0))
    denom = n + prior
    return float((sucessos + prior * liga) / denom) if denom > 0 else liga


def calcular_probabilidades_empiricas(
    df_liga: pd.DataFrame,
    jogos_casa: pd.DataFrame,
    jogos_fora: pd.DataFrame,
    forca_prior: float = 6.0,
) -> Dict[str, float]:
    """Frequências de Mais/Menos 2,5 e Ambas marcam com suavização.

    Combinação auditável:
    - 45% histórico do mandante em casa;
    - 45% histórico do visitante fora;
    - 10% frequência da liga.
    As duas amostras dos times são suavizadas pela taxa da liga antes da mistura.
    """
    n_liga_o, s_liga_o, taxa_liga_o = _taxa_binaria(df_liga, "over25")
    n_liga_b, s_liga_b, taxa_liga_b = _taxa_binaria(df_liga, "btts")
    n_casa_o, s_casa_o, taxa_casa_o = _taxa_binaria(jogos_casa, "over25")
    n_fora_o, s_fora_o, taxa_fora_o = _taxa_binaria(jogos_fora, "over25")
    n_casa_b, s_casa_b, taxa_casa_b = _taxa_binaria(jogos_casa, "btts")
    n_fora_b, s_fora_b, taxa_fora_b = _taxa_binaria(jogos_fora, "btts")

    casa_o_s = _suavizar_taxa(s_casa_o, n_casa_o, taxa_liga_o, forca_prior)
    fora_o_s = _suavizar_taxa(s_fora_o, n_fora_o, taxa_liga_o, forca_prior)
    casa_b_s = _suavizar_taxa(s_casa_b, n_casa_b, taxa_liga_b, forca_prior)
    fora_b_s = _suavizar_taxa(s_fora_b, n_fora_b, taxa_liga_b, forca_prior)

    over = float(np.clip(0.45 * casa_o_s + 0.45 * fora_o_s + 0.10 * taxa_liga_o, 0.0, 1.0))
    btts = float(np.clip(0.45 * casa_b_s + 0.45 * fora_b_s + 0.10 * taxa_liga_b, 0.0, 1.0))
    return {
        "Mais de 2.5 gols": over,
        "Menos de 2.5 gols": 1.0 - over,
        "Ambos marcam - Sim": btts,
        "Ambos marcam - Não": 1.0 - btts,
        "over25_liga": taxa_liga_o,
        "over25_casa_bruta": taxa_casa_o,
        "over25_fora_bruta": taxa_fora_o,
        "over25_casa_suavizada": casa_o_s,
        "over25_fora_suavizada": fora_o_s,
        "btts_liga": taxa_liga_b,
        "btts_casa_bruta": taxa_casa_b,
        "btts_fora_bruta": taxa_fora_b,
        "btts_casa_suavizada": casa_b_s,
        "btts_fora_suavizada": fora_b_s,
        "n_liga": n_liga_o,
        "n_casa": n_casa_o,
        "n_fora": n_fora_o,
        "forca_prior": float(forca_prior),
    }


def diagnostico_dispersao_total(df: pd.DataFrame) -> Dict[str, object]:
    """Mede se os gols totais variam mais do que uma Poisson simples supõe."""
    if df is None or df.empty:
        return {"n": 0, "media": np.nan, "variancia": np.nan, "razao": np.nan, "nivel": "sem dados"}
    totais = pd.to_numeric(df.get("HG"), errors="coerce") + pd.to_numeric(df.get("AG"), errors="coerce")
    totais = totais.dropna()
    if totais.empty:
        return {"n": 0, "media": np.nan, "variancia": np.nan, "razao": np.nan, "nivel": "sem dados"}
    media = float(totais.mean())
    variancia = float(totais.var(ddof=1)) if len(totais) > 1 else 0.0
    razao = variancia / media if media > 0 else np.nan
    if len(totais) < 40:
        nivel = "amostra pequena"
    elif np.isfinite(razao) and razao >= 1.25:
        nivel = "sobredispersão forte"
    elif np.isfinite(razao) and razao >= 1.10:
        nivel = "sobredispersão moderada"
    else:
        nivel = "dispersão próxima da Poisson"
    return {"n": int(len(totais)), "media": media, "variancia": variancia, "razao": razao, "nivel": nivel}


def calcular_planilha_pura(
    df: pd.DataFrame,
    time_casa: str,
    time_fora: str,
    regressao_media_ativa: bool = False,
    peso_media_liga: float = 0.25,
    limite_jogos: Optional[int] = None,
    peso_prob_empirica: float = 0.40,
) -> Dict[str, object]:
    """
    Motor simples e auditável.

    - O recorte oficial continua sendo o selecionado pelo usuário.
    - limite_jogos é usado apenas nos diagnósticos 5/8/12.
    - A regressão, quando ativa, preserva a leitura recente e puxa levemente
      médias extremas para a média atual da liga.
    """
    media_gols_casa_liga = max(0.20, float(pd.to_numeric(df["HG"], errors="coerce").mean()))
    media_gols_fora_liga = max(0.20, float(pd.to_numeric(df["AG"], errors="coerce").mean()))

    jogos_casa_todos = df[df["Home"].astype(str) == str(time_casa)].copy()
    jogos_fora_todos = df[df["Away"].astype(str) == str(time_fora)].copy()
    jogos_casa = _ordenar_e_limitar_jogos(jogos_casa_todos, limite_jogos)
    jogos_fora = _ordenar_e_limitar_jogos(jogos_fora_todos, limite_jogos)

    # Médias observadas no recorte casa/fora.
    gols_feitos_casa_bruto = media_simples(jogos_casa["HG"], media_gols_casa_liga)
    gols_sofridos_casa_bruto = media_simples(jogos_casa["AG"], media_gols_fora_liga)
    gols_feitos_fora_bruto = media_simples(jogos_fora["AG"], media_gols_fora_liga)
    gols_sofridos_fora_bruto = media_simples(jogos_fora["HG"], media_gols_casa_liga)

    # Ajuste leve e explícito à média atual da liga.
    gols_feitos_casa = _regredir_media(gols_feitos_casa_bruto, media_gols_casa_liga, regressao_media_ativa, peso_media_liga)
    gols_sofridos_casa = _regredir_media(gols_sofridos_casa_bruto, media_gols_fora_liga, regressao_media_ativa, peso_media_liga)
    gols_feitos_fora = _regredir_media(gols_feitos_fora_bruto, media_gols_fora_liga, regressao_media_ativa, peso_media_liga)
    gols_sofridos_fora = _regredir_media(gols_sofridos_fora_bruto, media_gols_casa_liga, regressao_media_ativa, peso_media_liga)

    forca_ataque_casa = gols_feitos_casa / media_gols_casa_liga if media_gols_casa_liga else 1.0
    forca_defesa_casa = gols_sofridos_casa / media_gols_fora_liga if media_gols_fora_liga else 1.0
    forca_ataque_fora = gols_feitos_fora / media_gols_fora_liga if media_gols_fora_liga else 1.0
    forca_defesa_fora = gols_sofridos_fora / media_gols_casa_liga if media_gols_casa_liga else 1.0

    gols_esperados_casa = media_gols_casa_liga * forca_ataque_casa * forca_defesa_fora
    gols_esperados_fora = media_gols_fora_liga * forca_ataque_fora * forca_defesa_casa
    gols_esperados_casa = float(np.clip(gols_esperados_casa, 0.05, 5.00))
    gols_esperados_fora = float(np.clip(gols_esperados_fora, 0.05, 5.00))

    matriz = matriz_poisson(gols_esperados_casa, gols_esperados_fora, tamanho=15)
    idx = np.arange(matriz.shape[0])
    soma_gols = np.add.outer(idx, idx)

    prob_casa = float(np.tril(matriz, -1).sum())
    prob_empate = float(np.diag(matriz).sum())
    prob_fora = float(np.triu(matriz, 1).sum())
    prob_over25 = float(matriz[soma_gols >= 3].sum())
    prob_under25 = float(matriz[soma_gols <= 2].sum())
    prob_btts_sim = float(matriz[1:, 1:].sum())
    prob_btts_nao = float(1.0 - prob_btts_sim)
    prob_casa_marcar = float(1.0 - np.exp(-gols_esperados_casa))
    prob_fora_marcar = float(1.0 - np.exp(-gols_esperados_fora))

    probabilidades_poisson = {
        "Vitória Casa": prob_casa,
        "Empate": prob_empate,
        "Vitória Fora": prob_fora,
        "Mais de 2.5 gols": prob_over25,
        "Menos de 2.5 gols": prob_under25,
        "Ambos marcam - Sim": prob_btts_sim,
        "Ambos marcam - Não": prob_btts_nao,
    }

    probabilidades_empiricas = calcular_probabilidades_empiricas(df, jogos_casa, jogos_fora)
    peso_emp = float(np.clip(peso_prob_empirica, 0.0, 0.70))
    prob_over_operacional = float((1.0 - peso_emp) * prob_over25 + peso_emp * probabilidades_empiricas["Mais de 2.5 gols"])
    prob_btts_operacional = float((1.0 - peso_emp) * prob_btts_sim + peso_emp * probabilidades_empiricas["Ambos marcam - Sim"])

    # Resultado final permanece no motor Poisson. Gols e ambas marcam recebem
    # uma segunda fonte observável, reduzindo dependência de uma única hipótese.
    probabilidades = {
        "Vitória Casa": prob_casa,
        "Empate": prob_empate,
        "Vitória Fora": prob_fora,
        "Mais de 2.5 gols": prob_over_operacional,
        "Menos de 2.5 gols": 1.0 - prob_over_operacional,
        "Ambos marcam - Sim": prob_btts_operacional,
        "Ambos marcam - Não": 1.0 - prob_btts_operacional,
    }

    cantos = calcular_cantos_se_existir(df, time_casa, time_fora)
    jogos_casa_usados = montar_jogos_usados(jogos_casa, time_casa, "casa")
    jogos_fora_usados = montar_jogos_usados(jogos_fora, time_fora, "fora")

    return {
        "jogos_casa_usados": jogos_casa_usados,
        "jogos_fora_usados": jogos_fora_usados,
        "media_gols_casa_liga": media_gols_casa_liga,
        "media_gols_fora_liga": media_gols_fora_liga,
        "jogos_casa": int(len(jogos_casa)),
        "jogos_fora": int(len(jogos_fora)),
        "jogos_casa_disponiveis": int(len(jogos_casa_todos)),
        "jogos_fora_disponiveis": int(len(jogos_fora_todos)),
        "amostra_minima": int(min(len(jogos_casa), len(jogos_fora))),
        "gols_feitos_casa_bruto": gols_feitos_casa_bruto,
        "gols_sofridos_casa_bruto": gols_sofridos_casa_bruto,
        "gols_feitos_fora_bruto": gols_feitos_fora_bruto,
        "gols_sofridos_fora_bruto": gols_sofridos_fora_bruto,
        "gols_feitos_casa": gols_feitos_casa,
        "gols_sofridos_casa": gols_sofridos_casa,
        "gols_feitos_fora": gols_feitos_fora,
        "gols_sofridos_fora": gols_sofridos_fora,
        "forca_ataque_casa": forca_ataque_casa,
        "forca_defesa_casa": forca_defesa_casa,
        "forca_ataque_fora": forca_ataque_fora,
        "forca_defesa_fora": forca_defesa_fora,
        "gols_esperados_casa": gols_esperados_casa,
        "gols_esperados_fora": gols_esperados_fora,
        "gols_total_esperado": float(gols_esperados_casa + gols_esperados_fora),
        "placar_arredondado_casa": int(np.floor(gols_esperados_casa + 0.5)),
        "placar_arredondado_fora": int(np.floor(gols_esperados_fora + 0.5)),
        "prob_casa_marcar": prob_casa_marcar,
        "prob_fora_marcar": prob_fora_marcar,
        "probabilidades": probabilidades,
        "probabilidades_poisson": probabilidades_poisson,
        "probabilidades_empiricas": probabilidades_empiricas,
        "peso_prob_empirica": peso_emp,
        "diagnostico_dispersao": diagnostico_dispersao_total(df),
        "regressao_media_ativa": bool(regressao_media_ativa),
        "peso_media_liga": float(np.clip(peso_media_liga, 0.0, 0.80)) if regressao_media_ativa else 0.0,
        "limite_jogos": limite_jogos,
        "cantos": cantos,
    }


def calcular_estabilidade_janelas(
    df: pd.DataFrame,
    time_casa: str,
    time_fora: str,
    regressao_media_ativa: bool,
    peso_media_liga: float,
    janelas: Tuple[int, ...] = (5, 8, 12),
    peso_prob_empirica: float = 0.40,
) -> Dict[str, object]:
    """Compara 5/8/12 sem misturar as janelas na previsão oficial."""
    linhas: List[Dict[str, object]] = []
    disponiveis_casa = int((df["Home"].astype(str) == str(time_casa)).sum())
    disponiveis_fora = int((df["Away"].astype(str) == str(time_fora)).sum())

    for janela in janelas:
        completa = disponiveis_casa >= janela and disponiveis_fora >= janela
        if not completa:
            linhas.append({
                "Janela": int(janela),
                "Situação": f"indisponível ({disponiveis_casa} casa / {disponiveis_fora} fora)",
                "Amostra casa": min(disponiveis_casa, janela),
                "Amostra fora": min(disponiveis_fora, janela),
            })
            continue
        modelo = calcular_planilha_pura(
            df, time_casa, time_fora,
            regressao_media_ativa=regressao_media_ativa,
            peso_media_liga=peso_media_liga,
            limite_jogos=janela,
            peso_prob_empirica=peso_prob_empirica,
        )
        p = modelo["probabilidades"]
        linhas.append({
            "Janela": int(janela),
            "Situação": "completa",
            "Amostra casa": int(modelo["jogos_casa"]),
            "Amostra fora": int(modelo["jogos_fora"]),
            "Gols casa": float(modelo["gols_esperados_casa"]),
            "Gols fora": float(modelo["gols_esperados_fora"]),
            "Vitória Casa": float(p["Vitória Casa"]),
            "Empate": float(p["Empate"]),
            "Vitória Fora": float(p["Vitória Fora"]),
            "Over 2.5": float(p["Mais de 2.5 gols"]),
            "Under 2.5": float(p["Menos de 2.5 gols"]),
            "BTTS Sim": float(p["Ambos marcam - Sim"]),
            "BTTS Não": float(p["Ambos marcam - Não"]),
        })

    completos = [r for r in linhas if r.get("Situação") == "completa"]
    if len(completos) < 2:
        return {
            "nivel": "INCONCLUSIVO",
            "amplitude_max": None,
            "motivo": "São necessárias pelo menos duas janelas completas para comparar estabilidade.",
            "linhas": linhas,
        }

    colunas_prob = ["Vitória Casa", "Empate", "Vitória Fora", "Over 2.5", "Under 2.5", "BTTS Sim", "BTTS Não"]
    amplitudes = {c: max(float(r[c]) for r in completos) - min(float(r[c]) for r in completos) for c in colunas_prob}
    mercado_mais_sensivel = max(amplitudes, key=amplitudes.get)
    amplitude_max = float(amplitudes[mercado_mais_sensivel])

    # Também verifica se muda o lado preferido dos mercados principais.
    favoritos_1x2 = {max(["Vitória Casa", "Empate", "Vitória Fora"], key=lambda c: float(r[c])) for r in completos}
    lados_gols = {"Over 2.5" if float(r["Over 2.5"]) >= 0.5 else "Under 2.5" for r in completos}
    lados_btts = {"BTTS Sim" if float(r["BTTS Sim"]) >= 0.5 else "BTTS Não" for r in completos}
    mudou_lado = len(favoritos_1x2) > 1 or len(lados_gols) > 1 or len(lados_btts) > 1

    if amplitude_max <= 0.05 and not mudou_lado:
        nivel = "ESTÁVEL"
    elif amplitude_max <= 0.10 and not mudou_lado:
        nivel = "MODERADA"
    else:
        nivel = "INSTÁVEL"

    motivo = f"Maior variação: {fmt_pct(amplitude_max, 1)} em {mercado_mais_sensivel}."
    if mudou_lado:
        motivo += " Pelo menos uma conclusão principal mudou de lado entre as janelas."
    return {
        "nivel": nivel,
        "amplitude_max": amplitude_max,
        "mercado_mais_sensivel": mercado_mais_sensivel,
        "motivo": motivo,
        "linhas": linhas,
        "amplitudes": amplitudes,
    }


def _estabilidade_mudou_lado(estabilidade: Optional[Dict[str, object]], grupo: str) -> bool:
    if not estabilidade:
        return False
    completas = [r for r in estabilidade.get("linhas", []) if r.get("Situação") == "completa"]
    if len(completas) < 2:
        return False
    if grupo == "gols":
        lados = {"Mais" if float(r.get("Over 2.5", 0.0)) >= 0.5 else "Menos" for r in completas}
    elif grupo == "btts":
        lados = {"Sim" if float(r.get("BTTS Sim", 0.0)) >= 0.5 else "Não" for r in completas}
    else:
        return False
    return len(lados) > 1


def _bloquear_operacional(out: pd.DataFrame, idx, status: str, motivo: str, etiqueta: str) -> None:
    """Mantém a linha auditável, mas zera qualquer ação operacional."""
    for col, padrao in [
        ("Veredito", ""), ("Status operacional", ""),
        ("Entrada teórica %", 0.0), ("Entrada teórica R$", 0.0),
        ("Entrada %", 0.0), ("Entrada R$", 0.0),
        ("Prioridade", "—"), ("_prioridade_score", 0), ("_prioridade_motivo", "sem prioridade"),
        ("Motivo", ""), ("Etiquetas", ""), ("Coerência interna", ""),
        ("Direção algébrica", ""), ("_coerencia_score", 0),
    ]:
        if col not in out.columns:
            out[col] = padrao
    out.at[idx, "Veredito"] = "BLOQUEADO"
    out.at[idx, "Status operacional"] = status
    out.at[idx, "Entrada teórica %"] = 0.0
    out.at[idx, "Entrada teórica R$"] = 0.0
    out.at[idx, "Entrada %"] = 0.0
    out.at[idx, "Entrada R$"] = 0.0
    out.at[idx, "Prioridade"] = "—"
    out.at[idx, "_prioridade_score"] = 0
    out.at[idx, "_prioridade_motivo"] = "bloqueado por coerência estrutural"
    out.at[idx, "Motivo"] = (str(out.at[idx, "Motivo"] or "") + " | " + motivo).strip(" |")
    out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], etiqueta)


def _reduzir_operacional(out: pd.DataFrame, idx, fator: float, motivo: str, etiqueta: str) -> None:
    fator = float(np.clip(fator, 0.0, 1.0))
    if "Entrada %" not in out.columns or "Entrada R$" not in out.columns:
        return
    entrada_pct = float(pd.to_numeric(pd.Series([out.at[idx, "Entrada %"]]), errors="coerce").fillna(0.0).iloc[0])
    entrada_rs = float(pd.to_numeric(pd.Series([out.at[idx, "Entrada R$"]]), errors="coerce").fillna(0.0).iloc[0])
    if entrada_pct <= 0:
        return
    out.at[idx, "Entrada %"] = entrada_pct * fator
    out.at[idx, "Entrada R$"] = entrada_rs * fator
    if "Entrada teórica %" in out.columns:
        out.at[idx, "Entrada teórica %"] = out.at[idx, "Entrada %"]
    if "Entrada teórica R$" in out.columns:
        out.at[idx, "Entrada teórica R$"] = out.at[idx, "Entrada R$"]
    out.at[idx, "Motivo"] = (str(out.at[idx, "Motivo"] or "") + " | " + motivo).strip(" |")
    out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], etiqueta)
    status = str(out.at[idx, "Status operacional"] or "LIBERADO")
    if "REDUZIDA" not in status:
        out.at[idx, "Status operacional"] = status + " — ENTRADA REDUZIDA"


def aplicar_travas_coerencia(
    resultados: pd.DataFrame,
    calc: Dict[str, object],
    estabilidade: Optional[Dict[str, object]] = None,
    linha_gols: float = 2.50,
    usar_direcao_algebrica_gols: bool = True,
    usar_direcao_algebrica_btts: bool = True,
    reduzir_conflito_modelos: bool = True,
) -> pd.DataFrame:
    """Aplica uma camada direcional simples antes do valor esperado.

    Princípio desta versão:
    - a soma dos gols projetados escolhe o lado estrutural do mercado de 2,5 gols;
    - o arredondamento aritmético individual escolhe o lado estrutural de ambas marcam;
    - Poisson, frequência real e estabilidade confirmam ou reduzem a força da tese;
    - divergência contra o mercado não bloqueia por si só, pois pode ser justamente a vantagem;
    - somente incoerência interna, lado oposto ou cotações inválidas bloqueiam a entrada.
    """
    if resultados is None or resultados.empty:
        return resultados

    out = resultados.copy()
    for col, padrao in [
        ("Direção algébrica", ""), ("Coerência interna", ""), ("_coerencia_score", 0),
    ]:
        if col not in out.columns:
            out[col] = padrao

    lam_casa = float(calc.get("gols_esperados_casa", 0.0) or 0.0)
    lam_fora = float(calc.get("gols_esperados_fora", 0.0) or 0.0)
    total = float(calc.get("gols_total_esperado", lam_casa + lam_fora) or (lam_casa + lam_fora))
    placar_casa = int(calc.get("placar_arredondado_casa", np.floor(lam_casa + 0.5)) or 0)
    placar_fora = int(calc.get("placar_arredondado_fora", np.floor(lam_fora + 0.5)) or 0)

    direcao_gols = "Mais de 2.5 gols" if total >= float(linha_gols) else "Menos de 2.5 gols"
    direcao_btts = "Ambos marcam - Sim" if placar_casa >= 1 and placar_fora >= 1 else "Ambos marcam - Não"

    p_pois = calc.get("probabilidades_poisson", {}) or {}
    p_emp = calc.get("probabilidades_empiricas", {}) or {}
    p_final = calc.get("probabilidades", {}) or {}
    instavel_gols = _estabilidade_mudou_lado(estabilidade, "gols")
    instavel_btts = _estabilidade_mudou_lado(estabilidade, "btts")

    def lado_favorecido(prob_sim_ou_mais: float, positivo: str, negativo: str) -> str:
        return positivo if float(prob_sim_ou_mais) >= 0.5 else negativo

    direcao_poisson_gols = lado_favorecido(p_pois.get("Mais de 2.5 gols", 0.0), "Mais de 2.5 gols", "Menos de 2.5 gols")
    direcao_empirica_gols = lado_favorecido(p_emp.get("Mais de 2.5 gols", 0.0), "Mais de 2.5 gols", "Menos de 2.5 gols")
    direcao_motor_gols = lado_favorecido(p_final.get("Mais de 2.5 gols", 0.0), "Mais de 2.5 gols", "Menos de 2.5 gols")
    direcao_poisson_btts = lado_favorecido(p_pois.get("Ambos marcam - Sim", 0.0), "Ambos marcam - Sim", "Ambos marcam - Não")
    direcao_empirica_btts = lado_favorecido(p_emp.get("Ambos marcam - Sim", 0.0), "Ambos marcam - Sim", "Ambos marcam - Não")
    direcao_motor_btts = lado_favorecido(p_final.get("Ambos marcam - Sim", 0.0), "Ambos marcam - Sim", "Ambos marcam - Não")

    for idx, row in out.iterrows():
        mercado = str(row.get("Mercado", ""))
        score = 0
        observacoes: List[str] = []

        if mercado in {"Mais de 2.5 gols", "Menos de 2.5 gols"}:
            out.at[idx, "Direção algébrica"] = mercado_exibicao(direcao_gols)
            if usar_direcao_algebrica_gols and mercado != direcao_gols:
                _bloquear_operacional(
                    out, idx,
                    "BLOQUEADO — SOMA PROJETADA APONTA O LADO OPOSTO",
                    f"a soma projetada é {total:.2f}; a direção algébrica é {mercado_exibicao(direcao_gols)}",
                    "Direção algébrica de gols",
                )
                continue

            score += 5
            observacoes.append(f"soma projetada {total:.2f} confirma {mercado_exibicao(mercado)}")
            if direcao_motor_gols == mercado:
                score += 2
                observacoes.append("probabilidade operacional confirma")
            else:
                observacoes.append("probabilidade operacional aponta o lado oposto")
            if direcao_poisson_gols == mercado:
                score += 1
                observacoes.append("Poisson confirma")
            else:
                observacoes.append("Poisson diverge")
            if direcao_empirica_gols == mercado:
                score += 1
                observacoes.append("frequência real confirma")
            else:
                observacoes.append("frequência real diverge")
            if instavel_gols:
                observacoes.append("janelas mudaram de lado")
                if reduzir_conflito_modelos:
                    _reduzir_operacional(out, idx, 0.60, "janelas 5/8/12 mudaram de lado; entrada reduzida", "Instabilidade específica de gols")
            elif reduzir_conflito_modelos and (direcao_poisson_gols != mercado or direcao_empirica_gols != mercado):
                _reduzir_operacional(out, idx, 0.75, "a direção algébrica foi mantida, mas um componente do modelo divergiu", "Conflito interno reduzido")

        elif mercado in {"Ambos marcam - Sim", "Ambos marcam - Não"}:
            out.at[idx, "Direção algébrica"] = mercado_exibicao(direcao_btts)
            if usar_direcao_algebrica_btts and mercado != direcao_btts:
                _bloquear_operacional(
                    out, idx,
                    "BLOQUEADO — PROJEÇÕES INDIVIDUAIS APONTAM O LADO OPOSTO",
                    f"placar algébrico arredondado {placar_casa} x {placar_fora}; direção {mercado_exibicao(direcao_btts)}",
                    "Direção algébrica de ambas marcam",
                )
                continue

            score += 4
            observacoes.append(f"placar algébrico {placar_casa} x {placar_fora} confirma {mercado_exibicao(mercado)}")
            if direcao_motor_btts == mercado:
                score += 2
                observacoes.append("probabilidade operacional confirma")
            else:
                observacoes.append("probabilidade operacional aponta o lado oposto")
            if direcao_poisson_btts == mercado:
                score += 1
                observacoes.append("Poisson confirma")
            else:
                observacoes.append("Poisson diverge")
            if direcao_empirica_btts == mercado:
                score += 1
                observacoes.append("frequência real confirma")
            else:
                observacoes.append("frequência real diverge")
            if instavel_btts:
                observacoes.append("janelas mudaram de lado")
                if reduzir_conflito_modelos:
                    _reduzir_operacional(out, idx, 0.60, "janelas 5/8/12 mudaram de lado; entrada reduzida", "Instabilidade específica de ambas marcam")
            elif reduzir_conflito_modelos and (direcao_poisson_btts != mercado or direcao_empirica_btts != mercado):
                _reduzir_operacional(out, idx, 0.75, "a direção algébrica foi mantida, mas um componente do modelo divergiu", "Conflito interno reduzido")

        else:
            # Resultado final não possui a mesma camada algébrica de gols.
            score = 1 if str(row.get("Veredito", "")) == "VALOR POSITIVO" else 0
            observacoes.append("mercado de resultado final avaliado pelo motor probabilístico")

        out.at[idx, "_coerencia_score"] = score
        out.at[idx, "Coerência interna"] = "; ".join(observacoes)
        if score >= 7:
            out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], "Coerência interna forte")
        elif score >= 4:
            out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], "Coerência algébrica")

    # Sobredispersão reduz, mas não anula automaticamente uma direção coerente.
    diag = calc.get("diagnostico_dispersao", {}) or {}
    razao = diag.get("razao")
    if razao is not None and np.isfinite(razao) and float(razao) >= 1.25:
        for idx, row in out.iterrows():
            if str(row.get("Mercado", "")) in {"Mais de 2.5 gols", "Menos de 2.5 gols", "Ambos marcam - Sim", "Ambos marcam - Não"}:
                _reduzir_operacional(out, idx, 0.80, f"liga com sobredispersão (variância/média {float(razao):.2f})", "Sobredispersão")

    # Nunca permite os dois lados opostos com entrada simultânea.
    for par in [("Mais de 2.5 gols", "Menos de 2.5 gols"), ("Ambos marcam - Sim", "Ambos marcam - Não")]:
        idxs = out.index[
            out["Mercado"].astype(str).isin(par)
            & out["Veredito"].astype(str).eq("VALOR POSITIVO")
            & (pd.to_numeric(out["Entrada %"], errors="coerce").fillna(0.0) > 0)
        ].tolist()
        if len(idxs) > 1:
            principal = max(
                idxs,
                key=lambda i: (
                    float(pd.to_numeric(out.at[i, "_coerencia_score"], errors="coerce") or 0.0),
                    float(out.at[i, "Probabilidade"]),
                    float(out.at[i, "Margem positiva"]),
                ),
            )
            for idx in idxs:
                if idx != principal:
                    _bloquear_operacional(out, idx, "BLOQUEADO — LADO OPOSTO À DIREÇÃO PRINCIPAL", f"o lado {out.at[principal, 'Mercado']} possui maior coerência interna", "Exclusividade do mercado")

    return limpar_dataframe_operacional(out)

def manter_apenas_entrada_principal(
    resultados: pd.DataFrame,
    banca: float,
    teto_por_jogo: float,
    permitir_multiplas: bool = False,
) -> pd.DataFrame:
    """Mantém no máximo uma entrada financeira por partida; as demais viram confirmações."""
    if resultados is None or resultados.empty or permitir_multiplas:
        return resultados
    out = resultados.copy()
    candidatos = out.index[
        out["Veredito"].astype(str).eq("VALOR POSITIVO")
        & (pd.to_numeric(out["Entrada %"], errors="coerce").fillna(0.0) > 0)
    ].tolist()
    if not candidatos:
        return out

    principal = max(
        candidatos,
        key=lambda i: (
            float(pd.to_numeric(out.at[i, "_coerencia_score"], errors="coerce") or 0.0) if "_coerencia_score" in out.columns else 0.0,
            float(pd.to_numeric(out.at[i, "_prioridade_score"], errors="coerce") or 0.0),
            float(pd.to_numeric(out.at[i, "Margem positiva"], errors="coerce") or 0.0),
            float(pd.to_numeric(out.at[i, "Probabilidade"], errors="coerce") or 0.0),
        ),
    )

    # Usa a entrada já reduzida por divergência, instabilidade e sobredispersão.
    # Não restaura a entrada bruta anterior às travas.
    base_operacional = float(pd.to_numeric(out.at[principal, "Entrada %"], errors="coerce") or 0.0)
    entrada_principal = min(max(0.0, base_operacional), max(0.0, float(teto_por_jogo))) if teto_por_jogo > 0 else max(0.0, base_operacional)
    out.at[principal, "Entrada teórica %"] = entrada_principal
    out.at[principal, "Entrada teórica R$"] = float(banca) * entrada_principal
    out.at[principal, "Entrada %"] = entrada_principal
    out.at[principal, "Entrada R$"] = float(banca) * entrada_principal
    out.at[principal, "Etiquetas"] = append_tag_texto(out.at[principal, "Etiquetas"], "Entrada principal única")
    out.at[principal, "Motivo"] = (str(out.at[principal, "Motivo"] or "") + " | selecionada como única entrada financeira da partida.").strip()

    for idx in candidatos:
        if idx == principal:
            continue
        out.at[idx, "Entrada teórica %"] = 0.0
        out.at[idx, "Entrada teórica R$"] = 0.0
        out.at[idx, "Entrada %"] = 0.0
        out.at[idx, "Entrada R$"] = 0.0
        out.at[idx, "Veredito"] = "CONFIRMAÇÃO"
        out.at[idx, "Status operacional"] = "CONFIRMAÇÃO — SEM ENTRADA"
        out.at[idx, "Prioridade"] = "—"
        out.at[idx, "_prioridade_score"] = 0
        out.at[idx, "_prioridade_motivo"] = "sinal secundário sem nova exposição financeira"
        out.at[idx, "Etiquetas"] = append_tag_texto(out.at[idx, "Etiquetas"], "Confirmação sem entrada")
        out.at[idx, "Motivo"] = (str(out.at[idx, "Motivo"] or "") + " | valor preservado como confirmação; somente o mercado principal recebe entrada.").strip()
    return limpar_dataframe_operacional(out)


def aplicar_modo_estudo(resultados: pd.DataFrame) -> pd.DataFrame:
    """Mantém comparação com odds, mas proíbe stake e recomendação."""
    if resultados is None or resultados.empty:
        return resultados
    out = resultados.copy()
    mask = pd.to_numeric(out.get("Entrada %", 0), errors="coerce").fillna(0.0) > 0
    out.loc[mask, "Veredito"] = "ESTUDO"
    out.loc[mask, "Status operacional"] = "ESTUDO — SOMENTE PROBABILIDADES"
    out.loc[mask, "Entrada %"] = 0.0
    out.loc[mask, "Entrada R$"] = 0.0
    out.loc[mask, "Prioridade"] = "—"
    out.loc[mask, "_prioridade_score"] = 0
    out.loc[mask, "_prioridade_motivo"] = "modo somente probabilidades sem entrada"
    out.loc[mask, "Etiquetas"] = out.loc[mask, "Etiquetas"].map(lambda x: append_tag_texto(x, "Modo somente probabilidades"))
    return out


def tabela_comparacao_probabilidades(calc: Dict[str, object]) -> pd.DataFrame:
    """Poisson, frequência empírica e probabilidade usada, lado a lado."""
    p_final = calc.get("probabilidades", {}) or {}
    p_poisson = calc.get("probabilidades_poisson", {}) or {}
    p_emp = calc.get("probabilidades_empiricas", {}) or {}
    linhas = []
    for mercado in MERCADOS_NUCLEO:
        prob = float(p_final.get(mercado, 0.0))
        linhas.append({
            "Mercado": mercado_exibicao(mercado),
            "Poisson": p_poisson.get(mercado, prob) if mercado in p_poisson else prob,
            "Frequência empírica": p_emp.get(mercado, np.nan) if mercado in {"Mais de 2.5 gols", "Menos de 2.5 gols", "Ambos marcam - Sim", "Ambos marcam - Não"} else np.nan,
            "Probabilidade operacional": prob,
            "Cotação justa operacional": (1.0 / prob) if prob > 0 else np.nan,
        })
    out = pd.DataFrame(linhas)
    for col in ["Poisson", "Frequência empírica", "Probabilidade operacional"]:
        out[col] = out[col].map(lambda x: "-" if x is None or pd.isna(x) else fmt_pct(float(x), 1))
    out["Cotação justa operacional"] = out["Cotação justa operacional"].map(lambda x: "-" if x is None or pd.isna(x) else fmt_num(float(x), 2))
    return out


def calcular_cantos_se_existir(df: pd.DataFrame, time_casa: str, time_fora: str) -> Optional[Dict[str, float]]:
    if not all(c in df.columns for c in ["HC", "AC"]):
        return None
    try:
        base = df.dropna(subset=["HC", "AC"]).copy()
        if base.empty:
            return None
        base["HC"] = pd.to_numeric(base["HC"], errors="coerce")
        base["AC"] = pd.to_numeric(base["AC"], errors="coerce")
        base = base.dropna(subset=["HC", "AC"])
        if base.empty:
            return None

        media_hc = max(0.20, float(base["HC"].mean()))
        media_ac = max(0.20, float(base["AC"].mean()))
        jogos_casa = base[base["Home"].astype(str) == str(time_casa)].copy()
        jogos_fora = base[base["Away"].astype(str) == str(time_fora)].copy()

        cantos_feitos_casa = media_simples(jogos_casa["HC"], media_hc)
        cantos_sofridos_casa = media_simples(jogos_casa["AC"], media_ac)
        cantos_feitos_fora = media_simples(jogos_fora["AC"], media_ac)
        cantos_sofridos_fora = media_simples(jogos_fora["HC"], media_hc)

        forca_cantos_casa = cantos_feitos_casa / media_hc if media_hc else 1.0
        defesa_cantos_fora = cantos_sofridos_fora / media_hc if media_hc else 1.0
        forca_cantos_fora = cantos_feitos_fora / media_ac if media_ac else 1.0
        defesa_cantos_casa = cantos_sofridos_casa / media_ac if media_ac else 1.0

        prev_cantos_casa = media_hc * forca_cantos_casa * defesa_cantos_fora
        prev_cantos_fora = media_ac * forca_cantos_fora * defesa_cantos_casa
        return {
            "cantos_casa": float(prev_cantos_casa),
            "cantos_fora": float(prev_cantos_fora),
            "cantos_total": float(prev_cantos_casa + prev_cantos_fora),
        }
    except Exception:
        return None

# ============================================================
# STAKE E VALOR
# ============================================================

def kelly_fracionado(prob: float, odd: float, fracao: float) -> float:
    try:
        prob = float(prob)
        odd = float(odd)
        ev = prob * odd - 1.0
        if prob <= 0 or odd <= 1.01 or ev <= 0:
            return 0.0
        kelly_cheio = ev / (odd - 1.0)
        return float(max(0.0, kelly_cheio * fracao))
    except Exception:
        return 0.0


def avaliar_valor_planilha(
    probabilidades: Dict[str, float],
    odds: Dict[str, float],
    banca: float,
    fracao_kelly: float,
    margem_minima: float,
    teto_por_entrada: float,
    teto_por_jogo: float,
    amostra_ok: bool,
    motivo_bloqueio_operacional: str = "",
    politica_amostra_baixa: str = "Avisar e reduzir entrada",
    fator_reducao_amostra: float = 0.50,
    amostra_minima_real: int = 0,
    fator_reducao_divergencia: float = 0.50,
) -> pd.DataFrame:
    """
    Avalia valor como a planilha, mas separa duas coisas que não podem ficar misturadas:
    1) Valor matemático: se a cotação real está acima da cotação justa com margem mínima.
    2) Status operacional: se a entrada está liberada, reduzida, apenas estudo ou bloqueada.

    Isso evita a burrice visual de mostrar margem positiva forte e ao mesmo tempo esconder que
    o motivo do corte foi só amostra baixa.
    """
    linhas = []
    metricas_mercado = metricas_probabilidade_das_odds(odds)
    politica = str(politica_amostra_baixa or "Avisar e reduzir entrada").strip()
    politica_lower = politica.lower()
    fator_reducao_amostra = float(max(0.0, min(1.0, fator_reducao_amostra)))

    for mercado in MERCADOS_NUCLEO:
        prob = float(probabilidades.get(mercado, 0.0))
        odd = texto_para_float(odds.get(mercado))
        if odd is None or not odd_valida(odd) or prob <= 0:
            continue

        odd_justa = 1.0 / prob if prob > 0 else np.inf
        margem = (prob * odd) - 1.0
        kelly = kelly_fracionado(prob, odd, fracao_kelly)
        entrada_pct_base = min(kelly, teto_por_entrada)
        tem_valor = margem > margem_minima
        valor_matematico = "SIM" if tem_valor else "NÃO"

        if tem_valor:
            if amostra_ok:
                veredito = "VALOR POSITIVO"
                status_operacional = "LIBERADO"
                entrada_pct = entrada_pct_base
                motivo = "valor positivo pela lógica da planilha"
            else:
                if "bloquear" in politica_lower:
                    veredito = "BLOQUEADO"
                    status_operacional = "AMOSTRA BAIXA — BLOQUEADO"
                    entrada_pct = 0.0
                    motivo = (motivo_bloqueio_operacional or "amostra mínima insuficiente") + " | valor matemático existe, mas a política atual bloqueia."
                elif "estudo" in politica_lower:
                    veredito = "ESTUDO"
                    status_operacional = "AMOSTRA BAIXA — ESTUDO"
                    entrada_pct = 0.0
                    motivo = (motivo_bloqueio_operacional or "amostra mínima insuficiente") + " | valor matemático existe, mas está marcado apenas para estudo."
                else:
                    veredito = "VALOR POSITIVO"
                    status_operacional = "AMOSTRA BAIXA — ENTRADA REDUZIDA"
                    entrada_pct = entrada_pct_base * fator_reducao_amostra
                    motivo = (
                        (motivo_bloqueio_operacional or "amostra mínima insuficiente")
                        + f" | valor matemático positivo; entrada reduzida para {fmt_pct(fator_reducao_amostra, 0)} da entrada original."
                    )
        else:
            veredito = "SEM VALOR"
            status_operacional = "SEM VALOR"
            entrada_pct = 0.0
            motivo = "cotação real abaixo ou muito próxima da cotação justa"

        alertas_mercado = detectar_alertas_mercado(mercado, float(odd), float(odd_justa), float(margem), odds) if tem_valor else []
        alerta_mercado_txt = " | ".join(alertas_mercado)
        metricas_casa = metricas_mercado.get(mercado, {})
        prob_mercado_bruta = float(metricas_casa.get("prob_bruta") or (1.0 / float(odd)))
        prob_mercado_ajustada = metricas_casa.get("prob_ajustada")
        margem_mercado = metricas_casa.get("margem_mercado")

        # Mercado completo com margem negativa demais ou margem abusiva geralmente
        # significa odds de teste, lados de casas diferentes ou erro de digitação.
        odds_inconsistentes = False
        if bool(metricas_casa.get("completo")) and margem_mercado is not None:
            try:
                mkt = float(margem_mercado)
                odds_inconsistentes = mkt < -0.05 or mkt > 0.30
            except Exception:
                odds_inconsistentes = False
        if odds_inconsistentes:
            veredito = "ESTUDO"
            status_operacional = "ODDS INCONSISTENTES — ESTUDO"
            entrada_pct = 0.0
            motivo = motivo + " | conjunto de cotações incompatível com um mercado normal; use o modo somente probabilidades para testes."

        nivel_divergencia, prob_mercado, dif_app_mercado = classificar_divergencia_mercado(prob, float(odd), mercado, float(margem), alertas_mercado) if tem_valor else ("NORMAL", prob_mercado_bruta, prob - prob_mercado_bruta)
        diferenca_ajustada = (prob - float(prob_mercado_ajustada)) if prob_mercado_ajustada is not None else (prob - prob_mercado_bruta)
        divergencia_critica = (
            tem_valor
            and bool(metricas_casa.get("completo"))
            and prob_mercado_ajustada is not None
            and abs(float(diferenca_ajustada)) >= 0.10
        )
        if divergencia_critica and not odds_inconsistentes:
            nivel_divergencia = "CRÍTICA"
            if tem_valor and entrada_pct > 0:
                fator_div = float(max(0.0, min(1.0, fator_reducao_divergencia)))
                entrada_pct = entrada_pct * fator_div
                status_operacional = "LIBERADO — DIVERGÊNCIA CRÍTICA"
                motivo = motivo + (
                    f" | diferença de {abs(float(diferenca_ajustada)) * 100:.1f} pontos percentuais entre o modelo e o mercado ajustado; "
                    f"a divergência foi tratada como possível vantagem, com entrada reduzida para {fmt_pct(fator_div, 0)}."
                )

        etiquetas: List[str] = []
        if not amostra_ok:
            etiquetas.append("Amostra baixa")
        elif 5 <= int(amostra_minima_real or 0) <= 7:
            etiquetas.append("Amostra mínima aprovada")
        elif int(amostra_minima_real or 0) >= 13:
            etiquetas.append("Amostra forte")
        elif int(amostra_minima_real or 0) >= 8:
            etiquetas.append("Amostra boa")

        if nivel_divergencia == "CRÍTICA":
            etiquetas.append("Divergência crítica com mercado")
        elif nivel_divergencia == "EXTREMA":
            etiquetas.append("Divergência extrema com mercado")
        elif nivel_divergencia == "FORTE":
            etiquetas.append("Divergência forte com mercado")
        elif nivel_divergencia == "MÉDIA":
            etiquetas.append("Divergência média com mercado")

        for alerta in alertas_mercado:
            a = str(alerta).lower()
            if "favorito do mercado" in a:
                etiquetas.append("Contra favorito do mercado")
            if "mercado de gols" in a:
                etiquetas.append("Mercado de gols contrário")
            if "ambos marcam" in a:
                etiquetas.append("Mercado de ambos marcam contrário")

        if alerta_mercado_txt and entrada_pct > 0:
            motivo = motivo + " | atenção de mercado: conferência manual recomendada."

        if tem_valor and entrada_pct > 0 and nivel_divergencia == "EXTREMA":
            fator_div = float(max(0.0, min(1.0, fator_reducao_divergencia)))
            entrada_pct = entrada_pct * fator_div
            motivo = motivo + f" | divergência extrema com o mercado; entrada reduzida para {fmt_pct(fator_div, 0)} da entrada original."
            if status_operacional == "LIBERADO":
                status_operacional = "LIBERADO — DIVERGÊNCIA EXTREMA"
            else:
                status_operacional = status_operacional + " — DIVERGÊNCIA EXTREMA"
        elif tem_valor and nivel_divergencia == "FORTE" and status_operacional == "LIBERADO":
            status_operacional = "LIBERADO — DIVERGÊNCIA FORTE"

        prioridade_txt, prioridade_score, prioridade_motivo = prioridade_aposta(prob, margem, entrada_pct, veredito, status_operacional, amostra_minima_real)

        linhas.append({
            "Mercado": mercado,
            "Prioridade": prioridade_txt,
            "Valor matemático": valor_matematico,
            "Status operacional": status_operacional,
            "Alerta de mercado": alerta_mercado_txt,
            "Divergência mercado": nivel_divergencia,
            "Prob. mercado": prob_mercado,
            "Prob. mercado bruta": prob_mercado_bruta,
            "Margem do mercado": margem_mercado,
            "Prob. mercado ajustada": prob_mercado_ajustada,
            "Mercado completo": "Sim" if bool(metricas_casa.get("completo")) else "Não",
            "Diferença app-mercado": dif_app_mercado,
            "Diferença modelo-mercado ajustada": (prob - float(prob_mercado_ajustada)) if prob_mercado_ajustada is not None else (prob - prob_mercado_bruta),
            "Etiquetas": append_tag_texto("", *etiquetas),
            "Probabilidade": prob,
            "Cotação justa": odd_justa,
            "Cotação real": float(odd),
            "Margem positiva": margem,
            "Veredito": veredito,
            "Entrada teórica %": entrada_pct if tem_valor else 0.0,
            "Entrada teórica R$": float(banca) * (entrada_pct if tem_valor else 0.0) if banca > 0 else 0.0,
            "_entrada_operacional_base": entrada_pct,
            "Entrada %": entrada_pct,
            "Entrada R$": float(banca) * entrada_pct if banca > 0 else 0.0,
            "Motivo": motivo,
            "_prioridade_score": prioridade_score,
            "_prioridade_motivo": prioridade_motivo,
        })

    df = pd.DataFrame(linhas)
    if df.empty:
        return df

    # O limite total do jogo só vale para entradas com entrada efetiva.
    mask_ev = df["Veredito"].eq("VALOR POSITIVO") & (pd.to_numeric(df["Entrada %"], errors="coerce").fillna(0.0) > 0)
    total_pct = float(df.loc[mask_ev, "Entrada %"].sum())
    if total_pct > teto_por_jogo > 0:
        fator = teto_por_jogo / total_pct
        df.loc[mask_ev, "Entrada %"] = df.loc[mask_ev, "Entrada %"] * fator
        df.loc[mask_ev, "Entrada R$"] = df.loc[mask_ev, "Entrada %"] * float(banca)
        df.loc[mask_ev, "Entrada teórica %"] = df.loc[mask_ev, "Entrada %"]
        df.loc[mask_ev, "Entrada teórica R$"] = df.loc[mask_ev, "Entrada R$"]
        df.loc[mask_ev, "Motivo"] = df.loc[mask_ev, "Motivo"] + " | entrada ajustada proporcionalmente pelo limite total do jogo"
        for idx, row in df.loc[mask_ev].iterrows():
            prioridade_txt, prioridade_score, prioridade_motivo = prioridade_aposta(
                float(row.get("Probabilidade", 0.0)),
                float(row.get("Margem positiva", 0.0)),
                float(df.at[idx, "Entrada %"]),
                str(row.get("Veredito", "")),
                str(row.get("Status operacional", "")),
                amostra_minima_real,
            )
            if str(row.get("Divergência mercado", "")).strip().upper() == "EXTREMA":
                prioridade_txt = "🔴 Baixa"
                prioridade_score = 1
                prioridade_motivo = "valor contra o mercado; exige confirmação manual antes de apostar"
            elif str(row.get("Alerta de mercado", "")).strip() and prioridade_score > 2:
                prioridade_txt = "🟠 Média"
                prioridade_score = 2
                prioridade_motivo = "valor forte, mas há divergência importante com o mercado; confira antes de apostar"
            df.at[idx, "Prioridade"] = prioridade_txt
            df.at[idx, "_prioridade_score"] = prioridade_score
            df.at[idx, "_prioridade_motivo"] = prioridade_motivo

    ordem_status = {
        "LIBERADO": 0,
        "LIBERADO — DIVERGÊNCIA FORTE": 1,
        "LIBERADO — DIVERGÊNCIA CRÍTICA": 1,
        "LIBERADO — DIVERGÊNCIA EXTREMA": 2,
        "AMOSTRA BAIXA — ENTRADA REDUZIDA": 3,
        "AMOSTRA BAIXA — ESTUDO": 2,
        "SEM VALOR": 3,
        "AMOSTRA BAIXA — BLOQUEADO": 4,
    }
    df["_ordem_status"] = df["Status operacional"].map(ordem_status).fillna(9)
    df = (
        df.sort_values(["_ordem_status", "_prioridade_score", "Margem positiva"], ascending=[True, False, False])
        .drop(columns=["_ordem_status"])
        .reset_index(drop=True)
    )
    return df

def faixa_odd(odd: float) -> str:
    try:
        o = float(odd)
    except Exception:
        return "-"
    if o < 1.50:
        return "1.01–1.49"
    if o < 2.00:
        return "1.50–1.99"
    if o < 3.00:
        return "2.00–2.99"
    if o < 5.00:
        return "3.00–4.99"
    return "5.00+"


def tabela_chi_poisson(serie: pd.Series, rotulo: str) -> Tuple[pd.DataFrame, Dict[str, object]]:
    gols = pd.to_numeric(serie, errors="coerce").dropna().astype(int)
    if gols.empty:
        return pd.DataFrame(), {"rotulo": rotulo, "n": 0, "media": np.nan, "estatistica": np.nan, "p_valor": np.nan, "aderencia": "sem dados"}

    n = int(len(gols))
    media = float(gols.mean())
    categorias = [0, 1, 2, 3, 4, 5, "6+"]
    observados = [int((gols == k).sum()) for k in range(6)] + [int((gols >= 6).sum())]
    esperados = [float(poisson.pmf(k, media) * n) for k in range(6)]
    esperados.append(float((1.0 - poisson.cdf(5, media)) * n))

    # Ajuste numérico para as somas baterem exatamente.
    soma_esp = sum(esperados)
    if soma_esp > 0:
        esperados = [e * n / soma_esp for e in esperados]

    tabela = pd.DataFrame({
        "Categoria de gols": categorias,
        "Observado": observados,
        "Esperado Poisson": esperados,
        "Diferença": [o - e for o, e in zip(observados, esperados)],
    })

    try:
        stat = float(sum(((o - e) ** 2) / e for o, e in zip(observados, esperados) if e > 0))
        # Como a média foi estimada pela amostra, usamos k - 1 - 1 graus de liberdade.
        gl = max(1, len(categorias) - 2)
        p_valor = float(chi2.sf(stat, gl))
    except Exception:
        stat, p_valor = np.nan, np.nan

    if n < 80:
        aderencia = "amostra pequena"
    elif not np.isfinite(p_valor):
        aderencia = "indefinido"
    elif p_valor >= 0.05:
        aderencia = "Poisson aceitável"
    else:
        aderencia = "Poisson ruim/instável"

    stats = {"rotulo": rotulo, "n": n, "media": media, "estatistica": stat, "p_valor": p_valor, "aderencia": aderencia}
    return tabela, stats


def diagnostico_poisson_liga(df: pd.DataFrame) -> Dict[str, object]:
    casa_tab, casa_stats = tabela_chi_poisson(df["HG"], "Gols do mandante")
    fora_tab, fora_stats = tabela_chi_poisson(df["AG"], "Gols do visitante")
    return {
        "casa_tabela": casa_tab,
        "fora_tabela": fora_tab,
        "casa_stats": casa_stats,
        "fora_stats": fora_stats,
    }


def classificar_confianca_estimativa(modelo: Dict[str, object], resultados: pd.DataFrame) -> Dict[str, object]:
    """Classifica somente a qualidade dos dados; não afirma confiabilidade preditiva."""
    amostra = int(modelo.get("amostra_minima", 0))
    motivos: List[str] = []

    if amostra >= 13:
        nivel = "Robusta"
        pontos = 4
        motivos.append(f"pelo menos {amostra} jogos no menor recorte casa/fora")
    elif amostra >= 8:
        nivel = "Adequada"
        pontos = 3
        motivos.append(f"pelo menos {amostra} jogos no menor recorte casa/fora")
    elif amostra >= 5:
        nivel = "Mínima"
        pontos = 2
        motivos.append(f"apenas {amostra} jogos no menor recorte casa/fora")
    else:
        nivel = "Insuficiente"
        pontos = 1
        motivos.append(f"somente {amostra} jogos no menor recorte casa/fora")

    total_esperado = float(modelo.get("gols_esperados_casa", 0.0)) + float(modelo.get("gols_esperados_fora", 0.0))
    if 1.20 <= total_esperado <= 4.20:
        motivos.append("projeção total dentro da faixa operacional usual")
    else:
        motivos.append("projeção total em faixa extrema")

    motivos.append("validação histórica em acompanhamento")
    return {
        "nível": nivel,
        "pontos": pontos,
        "motivos": "; ".join(motivos),
        "calibração": "Em acompanhamento",
    }


def coluna_se_existir(df: pd.DataFrame, *candidatas: str) -> Optional[str]:
    for col in candidatas:
        if col in df.columns:
            return col
    return None


def media_col(df: pd.DataFrame, col: Optional[str], padrao: float = 0.0) -> float:
    if not col or col not in df.columns or df.empty:
        return float(padrao)
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return float(padrao)
    return float(s.mean())


def calcular_scout_opcional(df: pd.DataFrame, time_casa: str, time_fora: str) -> Tuple[pd.DataFrame, List[str]]:
    avisos: List[str] = []
    base = df.copy()
    jogos_casa = base[base["Home"].astype(str) == str(time_casa)].copy()
    jogos_fora = base[base["Away"].astype(str) == str(time_fora)].copy()

    col_hs, col_as = coluna_se_existir(base, "HS"), coluna_se_existir(base, "AS")
    col_hst, col_ast = coluna_se_existir(base, "HST"), coluna_se_existir(base, "AST")
    col_hc, col_ac = coluna_se_existir(base, "HC"), coluna_se_existir(base, "AC")
    col_hf, col_af = coluna_se_existir(base, "HF"), coluna_se_existir(base, "AF")
    col_hy, col_ay = coluna_se_existir(base, "HY"), coluna_se_existir(base, "AY")
    col_hr, col_ar = coluna_se_existir(base, "HR"), coluna_se_existir(base, "AR")

    linhas = []
    def add(nome, casa_val, fora_val):
        linhas.append({"Indicador": nome, f"{time_casa} em casa": casa_val, f"{time_fora} fora": fora_val})

    add("Jogos na amostra", len(jogos_casa), len(jogos_fora))
    add("Gols feitos", media_col(jogos_casa, "HG"), media_col(jogos_fora, "AG"))
    add("Gols sofridos", media_col(jogos_casa, "AG"), media_col(jogos_fora, "HG"))

    if col_hs and col_as:
        chutes_casa = media_col(jogos_casa, col_hs)
        chutes_fora = media_col(jogos_fora, col_as)
        add("Finalizações", chutes_casa, chutes_fora)
        gf_casa = media_col(jogos_casa, "HG")
        gf_fora = media_col(jogos_fora, "AG")
        add("Gols / finalização", gf_casa / chutes_casa if chutes_casa > 0 else 0.0, gf_fora / chutes_fora if chutes_fora > 0 else 0.0)
    else:
        avisos.append("A base desta liga não trouxe finalizações HS/AS.")

    if col_hst and col_ast:
        alvo_casa = media_col(jogos_casa, col_hst)
        alvo_fora = media_col(jogos_fora, col_ast)
        add("Finalizações no alvo", alvo_casa, alvo_fora)
        gf_casa = media_col(jogos_casa, "HG")
        gf_fora = media_col(jogos_fora, "AG")
        add("Gols / chute no alvo", gf_casa / alvo_casa if alvo_casa > 0 else 0.0, gf_fora / alvo_fora if alvo_fora > 0 else 0.0)
    else:
        avisos.append("A base desta liga não trouxe chutes no alvo HST/AST.")

    if col_hc and col_ac:
        add("Escanteios", media_col(jogos_casa, col_hc), media_col(jogos_fora, col_ac))
        add("Escanteios sofridos", media_col(jogos_casa, col_ac), media_col(jogos_fora, col_hc))
    else:
        avisos.append("A base desta liga não trouxe escanteios HC/AC.")

    if col_hf and col_af:
        add("Faltas", media_col(jogos_casa, col_hf), media_col(jogos_fora, col_af))
    if col_hy and col_ay:
        add("Cartões amarelos", media_col(jogos_casa, col_hy), media_col(jogos_fora, col_ay))
    if col_hr and col_ar:
        add("Cartões vermelhos", media_col(jogos_casa, col_hr), media_col(jogos_fora, col_ar))

    tabela = pd.DataFrame(linhas)
    for col in tabela.columns[1:]:
        tabela[col] = pd.to_numeric(tabela[col], errors="coerce")
    return tabela, avisos


def resumo_auditoria_avancado(auditoria: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    if auditoria is None or auditoria.empty:
        return {}
    base = normalizar_colunas(auditoria, COLUNAS_AUDITORIA).copy()
    base["Entrada R$"] = pd.to_numeric(base["Entrada R$"], errors="coerce").fillna(0.0)
    base["Resultado R$"] = pd.to_numeric(base["Resultado R$"], errors="coerce").fillna(0.0)
    base["Cotação de entrada"] = pd.to_numeric(base["Cotação de entrada"], errors="coerce")
    base["Status"] = base["Status"].astype(str)
    mapa_situacao = {
        "Green": "Vitória", "Red": "Derrota", "Void": "Anulada", "Cashout": "Encerramento antecipado",
        "Vitória": "Vitória", "Derrota": "Derrota", "Anulada": "Anulada", "Encerramento antecipado": "Encerramento antecipado",
    }
    base["Situação normalizada"] = base["Status"].map(mapa_situacao).fillna(base["Status"])
    fechadas = base[base["Situação normalizada"].isin(["Vitória", "Derrota", "Anulada", "Encerramento antecipado"])].copy()
    if fechadas.empty:
        return {}

    fechadas["Vitoria_bin"] = (fechadas["Situação normalizada"] == "Vitória").astype(int)
    fechadas["Derrota_bin"] = (fechadas["Situação normalizada"] == "Derrota").astype(int)
    fechadas["Faixa de cotação"] = fechadas["Cotação de entrada"].apply(faixa_odd)

    def agrupar(campo: str) -> pd.DataFrame:
        g = fechadas.groupby(campo, dropna=False).agg(
            Entradas=("ID", "count"),
            Vitórias=("Vitoria_bin", "sum"),
            Derrotas=("Derrota_bin", "sum"),
            Apostado=("Entrada R$", "sum"),
            Resultado=("Resultado R$", "sum"),
        ).reset_index()
        g["Taxa acerto"] = np.where((g["Vitórias"] + g["Derrotas"]) > 0, g["Vitórias"] / (g["Vitórias"] + g["Derrotas"]), 0.0)
        g["ROI"] = np.where(g["Apostado"] > 0, g["Resultado"] / g["Apostado"], 0.0)
        return g.sort_values("Resultado", ascending=False)

    geral = pd.DataFrame([{
        "Entradas fechadas": len(fechadas),
        "Vitórias": int(fechadas["Vitoria_bin"].sum()),
        "Derrotas": int(fechadas["Derrota_bin"].sum()),
        "Apostado": float(fechadas["Entrada R$"].sum()),
        "Resultado": float(fechadas["Resultado R$"].sum()),
        "Taxa acerto": float(fechadas["Vitoria_bin"].sum() / max(1, (fechadas["Vitoria_bin"].sum() + fechadas["Derrota_bin"].sum()))),
        "ROI": float(fechadas["Resultado R$"].sum() / max(0.01, fechadas["Entrada R$"].sum())),
    }])

    por_etiqueta = pd.DataFrame()
    if "Etiquetas" in fechadas.columns:
        tag_base = fechadas.copy()
        tag_base["Etiqueta"] = tag_base["Etiquetas"].fillna("").astype(str).str.split(";")
        tag_base = tag_base.explode("Etiqueta")
        tag_base["Etiqueta"] = tag_base["Etiqueta"].astype(str).str.strip()
        tag_base = tag_base[tag_base["Etiqueta"].ne("")]
        if not tag_base.empty:
            g = tag_base.groupby("Etiqueta", dropna=False).agg(
                Entradas=("ID", "count"),
                Vitórias=("Vitoria_bin", "sum"),
                Derrotas=("Derrota_bin", "sum"),
                Apostado=("Entrada R$", "sum"),
                Resultado=("Resultado R$", "sum"),
            ).reset_index()
            g["Taxa acerto"] = np.where((g["Vitórias"] + g["Derrotas"]) > 0, g["Vitórias"] / (g["Vitórias"] + g["Derrotas"]), 0.0)
            g["ROI"] = np.where(g["Apostado"] > 0, g["Resultado"] / g["Apostado"], 0.0)
            por_etiqueta = g.sort_values("Resultado", ascending=False)

    return {
        "geral": geral,
        "por_mercado": agrupar("Mercado"),
        "por_liga": agrupar("Liga"),
        "por_faixa_odd": agrupar("Faixa de cotação"),
        "por_etiqueta": por_etiqueta,
    }


def formatar_tabela_resultados(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = limpar_dataframe_operacional(df)
    if "Mercado" in out.columns:
        out["Mercado"] = out["Mercado"].map(mercado_exibicao)
    for col in ["_prioridade_score", "_prioridade_motivo", "_entrada_operacional_base", "_coerencia_score", "Entrada teórica %", "Entrada teórica R$"]:
        if col in out.columns:
            out = out.drop(columns=[col])
    for col in ["Alerta de mercado", "Etiquetas", "Motivo", "Status operacional", "Prioridade"]:
        if col in out.columns:
            out[col] = out[col].map(texto_limpo_para_tela)
    out["Probabilidade"] = out["Probabilidade"].map(lambda x: fmt_pct(x, 1))
    for col in ["Prob. mercado", "Prob. mercado bruta", "Prob. mercado ajustada", "Margem do mercado", "Diferença app-mercado", "Diferença modelo-mercado ajustada"]:
        if col in out.columns:
            out[col] = out[col].map(lambda x: "-" if x is None or pd.isna(x) else fmt_pct(float(x), 1))
    out["Cotação justa"] = out["Cotação justa"].map(lambda x: "-" if not np.isfinite(x) else fmt_num(x, 2))
    out["Cotação real"] = out["Cotação real"].map(lambda x: "-" if x is None or pd.isna(x) or float(x) <= 1.0 else fmt_num(x, 2))
    out["Margem positiva"] = out["Margem positiva"].map(lambda x: fmt_pct(x, 1))
    for col in ["Entrada %"]:
        if col in out.columns:
            out[col] = out[col].map(lambda x: fmt_pct(x, 2))
    for col in ["Entrada R$"]:
        if col in out.columns:
            out[col] = out[col].map(fmt_dinheiro)
    return out.rename(columns={
        "Status operacional": "Situação operacional",
        "Diferença app-mercado": "Diferença aplicativo-mercado",
    })


def formatar_tabela_resumo_operacional(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela curta para a tela principal; a tabela completa fica no expander técnico."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = formatar_tabela_resultados(df)
    cols = [
        "Mercado", "Prioridade", "Valor matemático", "Situação operacional",
        "Divergência mercado", "Probabilidade", "Prob. mercado ajustada", "Cotação justa", "Cotação real",
        "Margem positiva", "Direção algébrica", "Coerência interna", "Entrada %", "Entrada R$", "Etiquetas",
    ]
    return out[[c for c in cols if c in out.columns]].copy()

# ============================================================
# ODDS MANUAIS E API
# ============================================================

def input_odd(label: str, key: str) -> Optional[float]:
    txt = st.text_input(label, value="", placeholder="ex: 2,10", key=key)
    x = texto_para_float(txt)
    return x if odd_valida(x) else None


def coletar_odds_manuais(prefixo: str) -> Dict[str, float]:
    odds: Dict[str, float] = {}

    st.markdown("### Cotações da casa")
    st.caption("Preencha apenas os mercados que você quer avaliar. Campo vazio fica fora da análise.")

    st.markdown("**Resultado final — 1X2**")
    c1, c2, c3 = st.columns(3)
    with c1:
        odds["Vitória Casa"] = input_odd("Vitória Casa", f"{prefixo}_vitoria_casa")
    with c2:
        odds["Empate"] = input_odd("Empate", f"{prefixo}_empate")
    with c3:
        odds["Vitória Fora"] = input_odd("Vitória Fora", f"{prefixo}_vitoria_fora")

    st.markdown("**Gols**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Mais de 2.5 gols"] = input_odd("Mais de 2.5 gols", f"{prefixo}_over25")
    with c2:
        odds["Menos de 2.5 gols"] = input_odd("Menos de 2.5 gols", f"{prefixo}_under25")

    st.markdown("**Ambos marcam**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Ambos marcam - Sim"] = input_odd("Ambos marcam - Sim", f"{prefixo}_btts_sim")
    with c2:
        odds["Ambos marcam - Não"] = input_odd("Ambos marcam - Não", f"{prefixo}_btts_nao")

    return {m: float(o) for m, o in odds.items() if odd_valida(o)}


@st.cache_data(ttl=300, show_spinner=False)
def buscar_odds_api(chave: str, liga_api: str) -> Optional[List[dict]]:
    if not chave:
        return None
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{liga_api}/odds/"
        params = {
            "apiKey": chave,
            "regions": "eu,uk,us",
            "markets": "h2h,totals,btts",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def limpar_nome_time(nome: str) -> str:
    nome = str(nome or "").lower().strip()
    for termo in [" fc", " cf", " ec", " ac", " sc", " afc", "football club", "soccer club"]:
        nome = nome.replace(termo, "")
    return " ".join(nome.split())


def casar_time_seguro(nome_api: str, times_csv: List[str], cutoff: float = 0.72) -> Tuple[Optional[str], float]:
    alvo = limpar_nome_time(nome_api)
    if not alvo:
        return None, 0.0
    candidatos_limpos = {limpar_nome_time(t): t for t in times_csv}
    if alvo in candidatos_limpos:
        return candidatos_limpos[alvo], 1.0
    melhores = difflib.get_close_matches(alvo, list(candidatos_limpos.keys()), n=1, cutoff=cutoff)
    if not melhores:
        return None, 0.0
    score = difflib.SequenceMatcher(None, alvo, melhores[0]).ratio()
    return candidatos_limpos[melhores[0]], float(score)


def mediana(valores: List[float]) -> Optional[float]:
    limpos = [float(v) for v in valores if odd_valida(v)]
    if not limpos:
        return None
    return float(np.median(limpos))


MAPA_BOOKMAKERS = {
    "Pixbet": ["pixbet", "pix bet"],
    "Pinnacle": ["pinnacle"],
    "Bet365": ["bet365", "bet 365"],
    "Betano": ["betano"],
    "Superbet": ["superbet", "super bet"],
    "KTO": ["kto"],
}


def bookmaker_corresponde(book: dict, casa_alvo: str) -> bool:
    aliases = MAPA_BOOKMAKERS.get(str(casa_alvo), [])
    if not aliases:
        return False
    key = str(book.get("key", "")).lower().strip()
    title = str(book.get("title", "")).lower().strip()
    texto = f"{key} {title}"
    return any(alias.lower() in texto for alias in aliases)


def _popular_pools_com_bookmaker(pools: Dict[str, List[float]], book: dict, casa_api: str, fora_api: str) -> None:
    for market in book.get("markets", []):
        key = market.get("key")
        for outcome in market.get("outcomes", []):
            nome = outcome.get("name")
            odd = texto_para_float(outcome.get("price"))
            if not odd_valida(odd):
                continue
            if key == "h2h":
                if nome == casa_api:
                    pools["Vitória Casa"].append(float(odd))
                elif nome == "Draw":
                    pools["Empate"].append(float(odd))
                elif nome == fora_api:
                    pools["Vitória Fora"].append(float(odd))
            elif key == "totals":
                try:
                    ponto = float(outcome.get("point", 0))
                except Exception:
                    ponto = 0.0
                if abs(ponto - 2.5) < 0.001:
                    if nome == "Over":
                        pools["Mais de 2.5 gols"].append(float(odd))
                    elif nome == "Under":
                        pools["Menos de 2.5 gols"].append(float(odd))
            elif key == "btts":
                if nome == "Yes":
                    pools["Ambos marcam - Sim"].append(float(odd))
                elif nome == "No":
                    pools["Ambos marcam - Não"].append(float(odd))


def _pools_para_odds(pools: Dict[str, List[float]]) -> Dict[str, float]:
    saida = {}
    for mercado, vals in pools.items():
        m = mediana(vals)
        if m is not None:
            saida[mercado] = float(m)
    return saida


def extrair_odds_api(jogo: dict, casa_alvo: Optional[str] = None) -> Tuple[Dict[str, float], str]:
    """
    Extrai odds da API.

    Regra V19.3:
    - se a casa escolhida existir na API, usa somente essa casa;
    - se não existir, usa mediana do mercado só como referência e avisa claramente;
    - no uso real, o modo Manual continua sendo o padrão recomendado.
    """
    casa_api = jogo.get("home_team")
    fora_api = jogo.get("away_team")
    bookmakers = list(jogo.get("bookmakers", []) or [])

    casa_alvo_txt = str(casa_alvo or "").strip()
    deve_priorizar_casa = bool(casa_alvo_txt) and casa_alvo_txt != "Outra"

    if deve_priorizar_casa:
        books_alvo = [book for book in bookmakers if bookmaker_corresponde(book, casa_alvo_txt)]
        if books_alvo:
            pools_alvo = {m: [] for m in MERCADOS_NUCLEO}
            for book in books_alvo:
                _popular_pools_com_bookmaker(pools_alvo, book, casa_api, fora_api)
            odds_alvo = _pools_para_odds(pools_alvo)
            if odds_alvo:
                return odds_alvo, f"✅ Cotações extraídas da casa selecionada na fonte automática: {casa_alvo_txt}. Ainda assim, confira antes de apostar."

    pools = {m: [] for m in MERCADOS_NUCLEO}
    for book in bookmakers:
        _popular_pools_com_bookmaker(pools, book, casa_api, fora_api)
    odds_mediana = _pools_para_odds(pools)

    if deve_priorizar_casa:
        aviso = (
            f"⚠️ A fonte automática não encontrou cotações da casa selecionada ({casa_alvo_txt}). "
            "Estou mostrando a mediana do mercado apenas como referência. "
            "Para apostar, confira e digite manualmente a cotação da sua casa."
        )
    else:
        aviso = "ℹ️ Casa 'Outra' selecionada: a fonte automática mostra a mediana do mercado. Para aposta real, prefira digitar a cotação manualmente."

    return odds_mediana, aviso

# ============================================================
# GOOGLE SHEETS — PERSISTÊNCIA NÃO DESTRUTIVA
# ============================================================

def _segredo_para_dict(obj) -> dict:
    try:
        return dict(obj)
    except Exception:
        return {}


def obter_config_google() -> Dict[str, object]:
    try:
        cfg = _segredo_para_dict(st.secrets.get("google_sheets", {}))
        spreadsheet_id = str(cfg.get("spreadsheet_id", "")).strip()
        worksheet_catalogo = str(cfg.get("worksheet_catalogo", GOOGLE_SHEETS_WORKSHEET_CATALOGO)).strip() or GOOGLE_SHEETS_WORKSHEET_CATALOGO
        worksheet_auditoria = str(cfg.get("worksheet_auditoria", GOOGLE_SHEETS_WORKSHEET_AUDITORIA)).strip() or GOOGLE_SHEETS_WORKSHEET_AUDITORIA
        worksheet_historico = str(cfg.get("worksheet_historico", GOOGLE_SHEETS_WORKSHEET_HISTORICO)).strip() or GOOGLE_SHEETS_WORKSHEET_HISTORICO
        service = _segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        client_email = str(service.get("client_email", "")).strip()
        return {
            "spreadsheet_id": spreadsheet_id,
            "worksheet_catalogo": worksheet_catalogo,
            "worksheet_auditoria": worksheet_auditoria,
            "worksheet_historico": worksheet_historico,
            "client_email": client_email,
            "configurado": bool(spreadsheet_id and client_email),
        }
    except Exception:
        return {
            "spreadsheet_id": "",
            "worksheet_catalogo": GOOGLE_SHEETS_WORKSHEET_CATALOGO,
            "worksheet_auditoria": GOOGLE_SHEETS_WORKSHEET_AUDITORIA,
            "worksheet_historico": GOOGLE_SHEETS_WORKSHEET_HISTORICO,
            "client_email": "",
            "configurado": False,
        }


def google_configurado() -> bool:
    return bool(obter_config_google().get("configurado"))


@st.cache_resource(show_spinner=False)
def conectar_google_sheets():
    if not google_configurado():
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        service_account = _segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        service_account = json.loads(json.dumps(service_account))
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(service_account, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_key(obter_config_google()["spreadsheet_id"])
    except Exception as exc:
        st.warning(f"Planilhas Google não conectadas; usando cópia local. Detalhe: {exc}")
        return None


def _cache_key_google(nome: str) -> str:
    safe = str(nome).strip().lower().replace(" ", "_")
    return f"_google_cache_df_{safe}"


def _cache_time_key_google(nome: str) -> str:
    safe = str(nome).strip().lower().replace(" ", "_")
    return f"_google_cache_ts_{safe}"


def _google_cooldown_ativo() -> bool:
    return float(st.session_state.get("_google_cooldown_until", 0.0)) > time.time()


def _segundos_cooldown_google() -> int:
    restante = float(st.session_state.get("_google_cooldown_until", 0.0)) - time.time()
    return max(0, int(restante))


def _erro_quota_google(exc: Exception) -> bool:
    txt = str(exc).lower()
    return (
        "quota exceeded" in txt
        or "read requests per minute" in txt
        or "write requests per minute" in txt
        or "resource_exhausted" in txt
        or "429" in txt
    )


def _ativar_cooldown_google(exc: Exception) -> None:
    st.session_state["_google_cooldown_until"] = time.time() + GOOGLE_COOLDOWN_SEG
    st.session_state["_google_ultimo_erro"] = str(exc)


def _pegar_cache_google(nome: str, colunas: List[str], aceitar_vencido: bool = True) -> Optional[pd.DataFrame]:
    key = _cache_key_google(nome)
    ts_key = _cache_time_key_google(nome)
    if key not in st.session_state:
        return None
    idade = time.time() - float(st.session_state.get(ts_key, 0.0))
    if idade <= GOOGLE_CACHE_TTL_SEG or aceitar_vencido:
        try:
            return normalizar_colunas(st.session_state[key].copy(), colunas)
        except Exception:
            return None
    return None


def _salvar_cache_google(nome: str, df: pd.DataFrame, colunas: List[str]) -> None:
    st.session_state[_cache_key_google(nome)] = normalizar_colunas(df, colunas).copy()
    st.session_state[_cache_time_key_google(nome)] = time.time()


def _numero_coluna_excel(numero: int) -> str:
    numero = max(1, int(numero))
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _valor_nativo_google(valor):
    """Converte pandas/numpy para tipos nativos sem transformar decimais em texto."""
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass
    if isinstance(valor, np.generic):
        valor = valor.item()
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(valor, date):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, (bool, int, float, str)):
        return valor
    return str(valor)


def _linha_google(row: pd.Series, colunas: List[str]) -> List[object]:
    return [_valor_nativo_google(row.get(col, "")) for col in colunas]


def _texto_chave(valor: object) -> str:
    txt = str(valor or "").strip().lower()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _chave_linha(row: pd.Series, colunas_chave: List[str]) -> str:
    partes = [_texto_chave(row.get(c, "")) for c in colunas_chave]
    if any(partes):
        return "|".join(partes)
    bruto = "|".join(_texto_chave(row.get(c, "")) for c in row.index)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _fundir_sem_apagar(
    dataframes: List[pd.DataFrame],
    colunas: List[str],
    colunas_chave: List[str],
) -> pd.DataFrame:
    partes = []
    for df in dataframes:
        if df is not None and not df.empty:
            partes.append(normalizar_colunas(df, colunas))
    if not partes:
        return pd.DataFrame(columns=colunas)
    base = pd.concat(partes, ignore_index=True)
    base["_chave_sync"] = base.apply(lambda r: _chave_linha(r, colunas_chave), axis=1)
    base = base.drop_duplicates("_chave_sync", keep="last").drop(columns=["_chave_sync"])
    return normalizar_colunas(base, colunas)


def _salvar_backup_versionado(df: pd.DataFrame, nome_base: str, colunas: List[str]) -> None:
    garantir_logs()
    base = normalizar_colunas(df, colunas)
    caminho_atual = os.path.join("logs", f"{nome_base}.csv")
    base.to_csv(caminho_atual, index=False, encoding="utf-8-sig")
    carimbo = carimbo_local_backup()
    caminho_backup = os.path.join(DIRETORIO_BACKUPS, f"{nome_base}_{carimbo}.csv")
    base.to_csv(caminho_backup, index=False, encoding="utf-8-sig")


def obter_aba(
    nome: str,
    colunas: List[str],
    linhas: int = 1000,
    criar_se_ausente: bool = False,
):
    """Obtém a aba sem escrever em abas existentes.

    Leitura nunca gera escrita. O cabeçalho só é criado quando a própria aba é
    criada pelo aplicativo. Isso evita gastar uma requisição de escrita em cada
    rerun do Streamlit.
    """
    if _google_cooldown_ativo():
        return None

    planilha = conectar_google_sheets()
    if planilha is None:
        return None

    nome_limpo = str(nome).strip()
    try:
        try:
            from gspread.exceptions import WorksheetNotFound
        except Exception:
            WorksheetNotFound = Exception

        criada = False
        try:
            aba = planilha.worksheet(nome_limpo)
        except WorksheetNotFound:
            if not criar_se_ausente:
                return None
            aba = planilha.add_worksheet(
                title=nome_limpo,
                rows=max(linhas, 1000),
                cols=max(20, len(colunas) + 4),
            )
            criada = True

        if criada:
            ultima_coluna = _numero_coluna_excel(len(colunas))
            aba.update(f"A1:{ultima_coluna}1", [colunas], value_input_option="RAW")
        return aba
    except Exception as exc:
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
            st.warning(
                f"Planilhas Google atingiram o limite de requisições. A cópia local foi preservada; "
                f"nova tentativa será possível em {_segundos_cooldown_google()}s."
            )
        else:
            st.warning(f"Não consegui acessar a aba {nome_limpo}. Detalhe: {exc}")
        return None


def _ler_aba_google_direto(aba, colunas: List[str]) -> pd.DataFrame:
    valores = aba.get_all_values()
    if not valores or len(valores) == 1:
        return pd.DataFrame(columns=colunas)
    linhas = valores[1:]
    largura = len(colunas)
    ajustadas = []
    for linha in linhas:
        linha = list(linha[:largura]) + [""] * max(0, largura - len(linha))
        if any(str(v).strip() for v in linha):
            ajustadas.append(linha)
    return normalizar_colunas(pd.DataFrame(ajustadas, columns=colunas), colunas)


def carregar_google(nome: str, colunas: List[str], force: bool = False) -> Optional[pd.DataFrame]:
    """Lê o Google ao menos uma vez por sessão; cache é apenas aceleração, nunca fonte exclusiva."""
    cache = _pegar_cache_google(nome, colunas, aceitar_vencido=not force)
    if cache is not None and not force:
        return cache

    if _google_cooldown_ativo():
        return cache

    aba = obter_aba(nome, colunas, criar_se_ausente=False)
    if aba is None:
        return cache

    try:
        df = _ler_aba_google_direto(aba, colunas)
        _salvar_cache_google(nome, df, colunas)
        return df
    except Exception as exc:
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
        st.warning(f"Não consegui ler {nome} nas Planilhas Google. Detalhe: {exc}")
        return cache


def salvar_catalogo_google_append_unico(
    nome: str,
    df: pd.DataFrame,
    colunas: List[str],
    colunas_chave: List[str],
) -> Tuple[bool, str, pd.DataFrame]:
    """Grava o catálogo com no máximo UMA escrita remota por clique.

    A aba precisa existir. O aplicativo lê as chaves atuais e, se houver linhas
    novas, envia todas de uma vez por append_rows. Não há clear, update de linha,
    batch_update, sobrescrita nem regravação do catálogo completo.
    """
    entrada = normalizar_colunas(df, colunas)
    if entrada.empty:
        return True, "nenhum registro novo", entrada

    if _google_cooldown_ativo():
        _salvar_cache_google(nome, entrada, colunas)
        return False, "Google temporariamente indisponível; cópia local preservada", entrada

    # Para garantir uma única escrita, esta rotina não cria a aba nem regrava cabeçalho.
    aba = obter_aba(nome, colunas, criar_se_ausente=False)
    if aba is None:
        return False, (
            f"a aba '{nome}' não foi encontrada; crie-a uma única vez com o cabeçalho "
            "antes de salvar cotações"
        ), entrada

    try:
        remoto = _ler_aba_google_direto(aba, colunas)
        chaves_remotas = set()
        if not remoto.empty:
            chaves_remotas = set(
                remoto.apply(lambda r: _chave_linha(r, colunas_chave), axis=1)
            )

        novas: List[List[object]] = []
        vistos = set()
        for _, row in entrada.iterrows():
            chave = _chave_linha(row, colunas_chave)
            if chave in vistos or chave in chaves_remotas:
                continue
            vistos.add(chave)
            novas.append(_linha_google(row, colunas))

        if not novas:
            consolidado = _fundir_sem_apagar([remoto], colunas, colunas_chave)
            _salvar_cache_google(nome, consolidado, colunas)
            return True, "0 incluído(s); o lote já existia; 0 apagado(s)", consolidado

        # ÚNICA escrita remota deste clique: todas as linhas seguem no mesmo lote.
        try:
            aba.append_rows(novas, value_input_option="RAW", insert_data_option="INSERT_ROWS")
        except TypeError:
            aba.append_rows(novas, value_input_option="RAW")

        # Consolidação local sem uma segunda escrita e sem alterar o histórico remoto.
        novas_df = normalizar_colunas(pd.DataFrame(novas, columns=colunas), colunas)
        consolidado = _fundir_sem_apagar([remoto, novas_df], colunas, colunas_chave)
        _salvar_cache_google(nome, consolidado, colunas)
        return True, f"{len(novas)} incluído(s) em 1 gravação; 0 alterado(s); 0 apagado(s)", consolidado
    except Exception as exc:
        _salvar_cache_google(nome, entrada, colunas)
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
        st.warning(f"Não consegui salvar o catálogo. A cópia local foi mantida. Detalhe: {exc}")
        return False, f"falha no Google; cópia local preservada: {exc}", entrada


def salvar_google_sem_apagar(
    nome: str,
    df: pd.DataFrame,
    colunas: List[str],
    colunas_chave: List[str],
    modo: str = "atualizar",
) -> Tuple[bool, str, pd.DataFrame]:
    """Sincroniza sem limpar a aba e com no máximo duas escritas por operação.

    modo="acrescentar": histórico imutável. Chaves já existentes nunca são
    sobrescritas; somente registros ausentes são acrescentados em um único lote.

    modo="atualizar": usado apenas onde a mesma linha precisa evoluir, como o
    resultado de uma entrada da auditoria. Todas as linhas alteradas são enviadas
    por uma única requisição em lote.
    """
    entrada = normalizar_colunas(df, colunas)
    if entrada.empty:
        return True, "nenhum registro novo", entrada

    if _google_cooldown_ativo():
        _salvar_cache_google(nome, entrada, colunas)
        return False, "Google temporariamente indisponível; cópia local preservada", entrada

    aba = obter_aba(nome, colunas, criar_se_ausente=True)
    if aba is None:
        _salvar_cache_google(nome, entrada, colunas)
        return False, "Google indisponível; cópia local preservada", entrada

    try:
        remoto = _ler_aba_google_direto(aba, colunas)
        mapa_remoto: Dict[str, Tuple[int, List[object]]] = {}
        for pos, (_, row) in enumerate(remoto.iterrows(), start=2):
            chave = _chave_linha(row, colunas_chave)
            if chave not in mapa_remoto:
                mapa_remoto[chave] = (pos, _linha_google(row, colunas))

        novas: List[List[object]] = []
        atualizacoes: List[Tuple[int, List[object]]] = []
        conflitos_preservados = 0
        vistos_entrada = set()
        somente_acrescentar = str(modo).strip().lower() == "acrescentar"

        for _, row in entrada.iterrows():
            chave = _chave_linha(row, colunas_chave)
            if chave in vistos_entrada:
                continue
            vistos_entrada.add(chave)
            valores = _linha_google(row, colunas)
            if chave in mapa_remoto:
                numero_linha, antigos = mapa_remoto[chave]
                diferentes = [str(v) for v in antigos] != [str(v) for v in valores]
                if diferentes:
                    if somente_acrescentar:
                        # Catálogo e histórico são imutáveis: nunca reescreva o passado.
                        conflitos_preservados += 1
                    else:
                        atualizacoes.append((numero_linha, valores))
            else:
                novas.append(valores)

        ultima_coluna = _numero_coluna_excel(len(colunas))
        if atualizacoes:
            pacote = [
                {
                    "range": f"A{numero_linha}:{ultima_coluna}{numero_linha}",
                    "values": [valores],
                }
                for numero_linha, valores in atualizacoes
            ]
            try:
                aba.batch_update(pacote, value_input_option="RAW")
            except TypeError:
                aba.batch_update(pacote, raw=True)

        if novas:
            try:
                aba.append_rows(novas, value_input_option="RAW", insert_data_option="INSERT_ROWS")
            except TypeError:
                aba.append_rows(novas, value_input_option="RAW")

        # Uma única leitura de confirmação; nenhuma nova escrita é provocada.
        confirmado = _ler_aba_google_direto(aba, colunas)
        consolidado = _fundir_sem_apagar([confirmado], colunas, colunas_chave)
        _salvar_cache_google(nome, consolidado, colunas)

        chaves_consolidadas = set(consolidado.apply(lambda r: _chave_linha(r, colunas_chave), axis=1))
        chaves_entrada = set(entrada.apply(lambda r: _chave_linha(r, colunas_chave), axis=1))
        faltantes = chaves_entrada - chaves_consolidadas
        if faltantes:
            raise RuntimeError(f"Falha de verificação: {len(faltantes)} registro(s) não apareceram após a sincronização.")

        detalhe = (
            f"{len(novas)} incluído(s), {len(atualizacoes)} atualizado(s), "
            f"{conflitos_preservados} conflito(s) histórico(s) preservado(s), nenhum apagado"
        )
        return True, detalhe, consolidado
    except Exception as exc:
        _salvar_cache_google(nome, entrada, colunas)
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
        st.warning(f"Não consegui sincronizar {nome}. A cópia local foi mantida. Detalhe: {exc}")
        return False, f"falha no Google; cópia local preservada: {exc}", entrada

# ============================================================
# AUDITORIA E CATÁLOGO
# ============================================================

def carregar_auditoria_local() -> pd.DataFrame:
    garantir_logs()
    if os.path.exists(ARQUIVO_AUDITORIA):
        try:
            return enriquecer_auditoria_probabilidades(pd.read_csv(ARQUIVO_AUDITORIA))
        except Exception:
            return pd.DataFrame(columns=COLUNAS_AUDITORIA)
    return pd.DataFrame(columns=COLUNAS_AUDITORIA)


def salvar_auditoria(df: pd.DataFrame) -> str:
    garantir_logs()
    entrada = enriquecer_auditoria_probabilidades(df)
    local = carregar_auditoria_local()
    consolidado_local = _fundir_sem_apagar(
        [local, entrada], COLUNAS_AUDITORIA, ["ID"]
    )
    consolidado_local = enriquecer_auditoria_probabilidades(consolidado_local)
    _salvar_backup_versionado(consolidado_local, "auditoria_tex_v19_1", COLUNAS_AUDITORIA)

    if google_configurado():
        cfg = obter_config_google()
        ok, detalhe, consolidado_google = salvar_google_sem_apagar(
            cfg["worksheet_auditoria"],
            consolidado_local,
            COLUNAS_AUDITORIA,
            ["ID"],
            modo="atualizar",
        )
        if ok:
            consolidado_google = enriquecer_auditoria_probabilidades(consolidado_google)
            _salvar_backup_versionado(consolidado_google, "auditoria_tex_v19_1", COLUNAS_AUDITORIA)
            return f"Planilhas Google + cópia local ({detalhe})"
        return f"cópia local; sincronização pendente ({detalhe})"
    return "cópia local"


def carregar_auditoria(force_google: bool = False) -> pd.DataFrame:
    local = carregar_auditoria_local()
    if google_configurado():
        cfg = obter_config_google()
        remoto = carregar_google(
            cfg["worksheet_auditoria"],
            COLUNAS_AUDITORIA,
            force=force_google,
        )
        consolidado = _fundir_sem_apagar(
            [local, remoto if remoto is not None else pd.DataFrame()],
            COLUNAS_AUDITORIA,
            ["ID"],
        )
        consolidado = enriquecer_auditoria_probabilidades(consolidado)
        return consolidado
    return enriquecer_auditoria_probabilidades(local)


def banca_atual(banca_inicial: float, auditoria: pd.DataFrame) -> float:
    if auditoria.empty or "Resultado R$" not in auditoria.columns:
        return float(banca_inicial)
    valores = pd.to_numeric(auditoria["Resultado R$"], errors="coerce").fillna(0.0)
    return float(banca_inicial) + float(valores.sum())


def registrar_entrada(
    auditoria: pd.DataFrame,
    liga: str,
    jogo: str,
    casa_apostas: str,
    mercado: str,
    odd: float,
    prob: float,
    odd_justa: float,
    margem: float,
    entrada_pct: float,
    entrada_rs: float,
    banca_antes: float,
    origem: str,
    observacao: str,
    etiquetas: str = "",
    prob_mercado_bruta: Optional[float] = None,
    prob_mercado_ajustada: Optional[float] = None,
    margem_mercado: Optional[float] = None,
    fonte_probabilidade: str = "Modelo Poisson do aplicativo",
    versao_modelo: str = VERSAO_MODELO,
) -> pd.DataFrame:
    base = enriquecer_auditoria_probabilidades(auditoria)
    p_bruta = float(prob_mercado_bruta) if prob_mercado_bruta is not None else (1.0 / float(odd) if odd_valida(odd) else np.nan)
    p_ajustada = float(prob_mercado_ajustada) if prob_mercado_ajustada is not None else np.nan
    margem_casa = float(margem_mercado) if margem_mercado is not None else np.nan
    referencia = p_ajustada if np.isfinite(p_ajustada) else p_bruta
    nova = {
        "ID": str(uuid.uuid4())[:8],
        "Registrado em": agora_local_texto(),
        "Liga": liga,
        "Jogo": jogo,
        "Casa de apostas": casa_apostas,
        "Mercado": mercado,
        "Cotação de entrada": round(float(odd), 4),
        "Probabilidade implícita bruta %": round(p_bruta * 100.0, 4) if np.isfinite(p_bruta) else "",
        "Margem do mercado %": round(margem_casa * 100.0, 4) if np.isfinite(margem_casa) else "",
        "Probabilidade de mercado ajustada %": round(p_ajustada * 100.0, 4) if np.isfinite(p_ajustada) else "",
        "Chance pelo sistema %": round(float(prob) * 100, 4),
        "Vantagem do modelo (p.p.)": round((float(prob) - referencia) * 100.0, 4) if float(prob) > 0 and np.isfinite(referencia) else "",
        "Referência da vantagem": "Mercado ajustado sem margem" if np.isfinite(p_ajustada) else ("Mercado bruto (margem indisponível)" if float(prob) > 0 else ""),
        "Cotação justa": round(float(odd_justa), 4) if np.isfinite(odd_justa) else "",
        "Valor esperado %": round(float(margem) * 100, 4),
        "Fonte da probabilidade": fonte_probabilidade if float(prob) > 0 else "",
        "Versão do modelo": versao_modelo if float(prob) > 0 else "",
        "Entrada %": round(float(entrada_pct) * 100, 3),
        "Entrada R$": round(float(entrada_rs), 2),
        "Banca antes": round(float(banca_antes), 2),
        "Cotação de fechamento": "",
        "Vantagem no fechamento %": "",
        "Status": "Pendente",
        "Resultado R$": 0.0,
        "Banca depois": "",
        "Diagnóstico pós-jogo": "",
        "Origem": origem,
        "Observação": observacao,
        "Etiquetas": etiquetas,
    }
    return enriquecer_auditoria_probabilidades(pd.concat([base, pd.DataFrame([nova])], ignore_index=True))


def calcular_resultado(status: str, entrada_rs: float, odd: float, cashout: float = 0.0) -> float:
    status = str(status)
    if status in {"Vitória", "Green"}:
        return float(entrada_rs) * (float(odd) - 1.0)
    if status in {"Derrota", "Red"}:
        return -float(entrada_rs)
    if status in {"Anulada", "Void"}:
        return 0.0
    if status in {"Encerramento antecipado", "Cashout"}:
        return float(cashout) - float(entrada_rs)
    return 0.0


def carregar_catalogo_local() -> pd.DataFrame:
    garantir_logs()
    if os.path.exists(ARQUIVO_CATALOGO):
        try:
            return enriquecer_catalogo_probabilidades(pd.read_csv(ARQUIVO_CATALOGO))
        except Exception:
            return pd.DataFrame(columns=COLUNAS_CATALOGO)
    return pd.DataFrame(columns=COLUNAS_CATALOGO)


def salvar_catalogo(df: pd.DataFrame) -> str:

    """Salva somente o lote recebido e nunca regrava o catálogo inteiro.


    Contrato operacional:

    - esta função só deve ser chamada por uma ação explícita do usuário;

    - no Google, executa no máximo UMA escrita por clique;

    - a escrita é somente de acréscimo (append);

    - nenhuma linha histórica é atualizada, substituída ou apagada;

    - a leitura remota serve apenas para evitar duplicação da mesma chave.

    """

    garantir_logs()

    entrada = enriquecer_catalogo_probabilidades(df)

    if entrada.empty:

        return "nenhuma cotação válida"


    # A cópia local recebe o novo lote e mantém tudo o que já existia.

    local = carregar_catalogo_local()

    consolidado_local = _fundir_sem_apagar(

        [local, entrada],

        COLUNAS_CATALOGO,

        ["ID Coleta", "Mercado", "Seleção"],

    )

    consolidado_local = enriquecer_catalogo_probabilidades(consolidado_local)

    _salvar_backup_versionado(consolidado_local, "catalogo_odds_tex_v19_1", COLUNAS_CATALOGO)


    if google_configurado():

        cfg = obter_config_google()

        # Envia SOMENTE o lote do clique atual. A função abaixo lê as chaves

        # existentes e faz um único append_rows com as linhas realmente novas.

        ok, detalhe, consolidado_google = salvar_catalogo_google_append_unico(
            cfg["worksheet_catalogo"],
            entrada,
            COLUNAS_CATALOGO,
            ["ID Coleta", "Mercado", "Seleção"],
        )

        if ok:

            consolidado_google = enriquecer_catalogo_probabilidades(consolidado_google)

            # O backup local é atualizado sem provocar nova escrita no Google.

            backup_consolidado = _fundir_sem_apagar(

                [consolidado_local, consolidado_google],

                COLUNAS_CATALOGO,

                ["ID Coleta", "Mercado", "Seleção"],

            )

            _salvar_backup_versionado(backup_consolidado, "catalogo_odds_tex_v19_1", COLUNAS_CATALOGO)

            return f"Planilhas Google + cópia local ({detalhe})"

        return f"cópia local; sincronização pendente ({detalhe})"

    return "cópia local"


def carregar_catalogo(force_google: bool = False) -> pd.DataFrame:
    local = carregar_catalogo_local()
    if google_configurado():
        cfg = obter_config_google()
        remoto = carregar_google(
            cfg["worksheet_catalogo"],
            COLUNAS_CATALOGO,
            force=force_google,
        )
        consolidado = _fundir_sem_apagar(
            [local, remoto if remoto is not None else pd.DataFrame()],
            COLUNAS_CATALOGO,
            ["ID Coleta", "Mercado", "Seleção"],
        )
        consolidado = enriquecer_catalogo_probabilidades(consolidado)
        return consolidado
    return enriquecer_catalogo_probabilidades(local)


def catalogo_recuperacao_dataframe() -> pd.DataFrame:
    base = pd.DataFrame(CATALOGO_RECUPERACAO_2026)
    return enriquecer_catalogo_probabilidades(base)


def preparar_catalogo_recuperado_local() -> str:
    """Garante as 49 cotações na cópia local sem fazer qualquer chamada ao Google."""
    recuperado = catalogo_recuperacao_dataframe()
    local = carregar_catalogo_local()
    consolidado = _fundir_sem_apagar(
        [local, recuperado],
        COLUNAS_CATALOGO,
        ["ID Coleta", "Mercado", "Seleção"],
    )
    consolidado = enriquecer_catalogo_probabilidades(consolidado)
    _salvar_backup_versionado(consolidado, "catalogo_odds_tex_v19_1", COLUNAS_CATALOGO)
    return f"cópia local com {len(consolidado)} registro(s)"


def restaurar_catalogo_recuperado() -> str:
    """Envia ao Google somente as cotações ausentes, em um único lote e sem sobrescrever."""
    preparar_catalogo_recuperado_local()
    return salvar_catalogo(catalogo_recuperacao_dataframe())


def registrar_odds_catalogo(
    catalogo: pd.DataFrame,
    liga: str,
    jogo: str,
    time_casa: str,
    time_fora: str,
    casa_apostas: str,
    odds: Dict[str, float],
    banca: float,
    perfil: str,
    data_jogo: date,
    hora_jogo: str,
    origem: str,
    observacao: str,
    id_coleta: Optional[str] = None,
    registrado_em: Optional[str] = None,
) -> pd.DataFrame:
    base = normalizar_colunas(catalogo, COLUNAS_CATALOGO)
    coleta = str(id_coleta or uuid.uuid4().hex[:8])
    momento = str(registrado_em or agora_local_texto())
    linhas = []
    for mercado, odd in odds.items():
        if not odd_valida(odd):
            continue
        linhas.append({
            "ID Coleta": coleta,
            "Registrado em": momento,
            "Casa de apostas": casa_apostas,
            "Liga": liga,
            "Jogo": jogo,
            "Mandante": time_casa,
            "Visitante": time_fora,
            "Data do jogo": data_jogo.strftime("%Y-%m-%d") if isinstance(data_jogo, date) else str(data_jogo),
            "Hora do jogo": hora_jogo,
            "Mercado": mercado,
            "Seleção": nome_selecao(mercado, time_casa, time_fora),
            "Cotação": float(odd),
            "Banca no momento": float(banca),
            "Perfil": perfil,
            "Origem": origem,
            "Observação": observacao,
        })
    if linhas:
        base = pd.concat([base, pd.DataFrame(linhas)], ignore_index=True)
    return enriquecer_catalogo_probabilidades(base)



def carregar_historico_analises_local() -> pd.DataFrame:
    garantir_logs()
    if os.path.exists(ARQUIVO_HISTORICO_ANALISES):
        try:
            return normalizar_colunas(pd.read_csv(ARQUIVO_HISTORICO_ANALISES), COLUNAS_HISTORICO_ANALISES)
        except Exception:
            return pd.DataFrame(columns=COLUNAS_HISTORICO_ANALISES)
    return pd.DataFrame(columns=COLUNAS_HISTORICO_ANALISES)


def salvar_historico_analises(df: pd.DataFrame) -> str:
    entrada = normalizar_colunas(df, COLUNAS_HISTORICO_ANALISES)
    local = carregar_historico_analises_local()
    consolidado_local = _fundir_sem_apagar(
        [local, entrada],
        COLUNAS_HISTORICO_ANALISES,
        ["ID Análise", "Mercado"],
    )
    _salvar_backup_versionado(
        consolidado_local,
        "historico_analises_tex_v20_3_3",
        COLUNAS_HISTORICO_ANALISES,
    )

    if google_configurado():
        cfg = obter_config_google()
        ok, detalhe, consolidado_google = salvar_google_sem_apagar(
            cfg["worksheet_historico"],
            consolidado_local,
            COLUNAS_HISTORICO_ANALISES,
            ["ID Análise", "Mercado"],
            modo="acrescentar",
        )
        if ok:
            _salvar_backup_versionado(
                consolidado_google,
                "historico_analises_tex_v20_3_3",
                COLUNAS_HISTORICO_ANALISES,
            )
            return f"Planilhas Google + cópia local ({detalhe})"
        return f"cópia local; sincronização pendente ({detalhe})"
    return "cópia local"


def carregar_historico_analises(force_google: bool = False) -> pd.DataFrame:
    local = carregar_historico_analises_local()
    if google_configurado():
        cfg = obter_config_google()
        remoto = carregar_google(
            cfg["worksheet_historico"],
            COLUNAS_HISTORICO_ANALISES,
            force=force_google,
        )
        consolidado = _fundir_sem_apagar(
            [local, remoto if remoto is not None else pd.DataFrame()],
            COLUNAS_HISTORICO_ANALISES,
            ["ID Análise", "Mercado"],
        )
        return consolidado
    return local


def registrar_historico_analise(
    id_analise: str,
    id_coleta: str,
    liga: str,
    jogo: str,
    time_casa: str,
    time_fora: str,
    data_jogo: date,
    hora_jogo: str,
    casa_apostas: str,
    origem: str,
    odds: Dict[str, float],
    calc: Dict[str, object],
    resultados: pd.DataFrame,
    estabilidade: Optional[Dict[str, object]],
    config: Dict[str, object],
) -> pd.DataFrame:
    p_oper = calc.get("probabilidades", {}) or {}
    p_pois = calc.get("probabilidades_poisson", {}) or {}
    p_emp = calc.get("probabilidades_empiricas", {}) or {}
    metricas_odds = metricas_probabilidade_das_odds(odds)
    resultado_por_mercado = {}
    if resultados is not None and not resultados.empty and "Mercado" in resultados.columns:
        resultado_por_mercado = {
            str(r.get("Mercado")): r for _, r in resultados.iterrows()
        }

    nivel_estabilidade = ""
    if isinstance(estabilidade, dict):
        nivel_estabilidade = str(estabilidade.get("nivel", ""))

    linhas = []
    momento = agora_local_texto()
    for mercado in MERCADOS_NUCLEO:
        r = resultado_por_mercado.get(mercado)
        metrica = metricas_odds.get(mercado, {}) or {}
        prob_mercado = metrica.get("prob_ajustada")
        odd = odds.get(mercado)
        situacao = ""
        entrada = 0.0
        cotacao_justa = ""
        ev = ""
        if r is not None:
            situacao = texto_limpo_para_tela(r.get("Status operacional", r.get("Veredito", "")))
            entrada_num = pd.to_numeric(r.get("Entrada %", 0.0), errors="coerce")
            entrada = 0.0 if pd.isna(entrada_num) else float(entrada_num)
            cotacao_justa = pd.to_numeric(r.get("Cotação justa", np.nan), errors="coerce")
            ev = pd.to_numeric(r.get("Margem positiva", np.nan), errors="coerce")
            if pd.isna(cotacao_justa):
                cotacao_justa = ""
            if pd.isna(ev):
                ev = ""
            elif isinstance(ev, (float, np.floating)):
                ev = float(ev) * 100.0

        linhas.append({
            "ID Análise": id_analise,
            "ID Coleta": id_coleta,
            "Registrado em": momento,
            "Liga": liga,
            "Jogo": jogo,
            "Mandante": time_casa,
            "Visitante": time_fora,
            "Data do jogo": data_jogo.strftime("%Y-%m-%d") if isinstance(data_jogo, date) else str(data_jogo),
            "Hora do jogo": hora_jogo,
            "Casa de apostas": casa_apostas,
            "Origem": origem,
            "Mercado": mercado,
            "Cotação": float(odd) if odd_valida(odd) else "",
            "Probabilidade operacional %": round(float(p_oper.get(mercado, 0.0)) * 100.0, 4),
            "Probabilidade Poisson %": round(float(p_pois.get(mercado, 0.0)) * 100.0, 4),
            "Probabilidade empírica %": round(float(p_emp.get(mercado, 0.0)) * 100.0, 4) if mercado in p_emp else "",
            "Probabilidade de mercado ajustada %": round(float(prob_mercado) * 100.0, 4) if prob_mercado is not None else "",
            "Cotação justa": cotacao_justa,
            "Valor esperado %": ev,
            "Gols projetados casa": round(float(calc.get("gols_esperados_casa", 0.0)), 4),
            "Gols projetados fora": round(float(calc.get("gols_esperados_fora", 0.0)), 4),
            "Gols projetados total": round(float(calc.get("gols_total_esperado", 0.0)), 4),
            "Chance mandante marcar %": round(float(calc.get("prob_casa_marcar", 0.0)) * 100.0, 4),
            "Chance visitante marcar %": round(float(calc.get("prob_fora_marcar", 0.0)) * 100.0, 4),
            "Amostra casa": int(calc.get("jogos_casa", 0)),
            "Amostra fora": int(calc.get("jogos_fora", 0)),
            "Estabilidade": nivel_estabilidade,
            "Situação": situacao,
            "Entrada %": round(float(entrada) * 100.0, 4),
            "Versão do modelo": VERSAO_MODELO,
            "Configuração JSON": json.dumps(config, ensure_ascii=False, default=str, sort_keys=True),
        })
    return normalizar_colunas(pd.DataFrame(linhas), COLUNAS_HISTORICO_ANALISES)


def importar_catalogo_arquivo(conteudo: bytes, nome_arquivo: str) -> pd.DataFrame:
    """Importa CSV/TSV sem apagar nada; o salvamento posterior deduplica por ID+mercado+seleção."""
    texto = conteudo.decode("utf-8-sig", errors="replace")
    separador = "\t" if ("\t" in texto.splitlines()[0]) else ","
    try:
        base = pd.read_csv(io.StringIO(texto), sep=separador, dtype=str)
    except Exception:
        base = pd.read_csv(io.StringIO(texto), sep=None, engine="python", dtype=str)
    base = base.loc[:, ~base.columns.astype(str).str.startswith("Unnamed")].copy()
    for col in ["Cotação", "Banca no momento"]:
        if col in base.columns:
            base[col] = base[col].map(texto_para_float)
    return enriquecer_catalogo_probabilidades(base)

# ============================================================
# UI
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">TEX ESTATÍSTICAS V20.3.5</div>
        <div class="hero-sub">
            Painel operacional limpo: planilha pura, Poisson auditável, regressão leve à média, teste de estabilidade, cotação justa e gestão de risco.
            A tela principal mostra só o que importa; o detalhe técnico fica recolhido para conferência.
        </div>
        <div class="chip-row">
            <span class="chip">Planilha pura</span>
            <span class="chip">Visual refinado</span>
            <span class="chip">Valor positivo</span>
            <span class="chip">Auditoria</span>
            <span class="chip">Sem firula</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Banca")
    banca_inicial = st.number_input("Banca inicial da auditoria", min_value=0.0, value=1000.0, step=50.0)
    st.caption(f"Horário dos registros: {FUSO_HORARIO_REGISTROS} (UTC−03:00).")

    cfg_sidebar = obter_config_google()
    force_sync_sidebar = False
    if cfg_sidebar.get("configurado"):
        st.caption("Catálogo somente de acréscimo: nenhuma gravação ocorre ao analisar. Um único lote é enviado apenas ao clicar em SALVAR COTAÇÕES; nenhuma linha antiga é alterada ou apagada.")
        if not st.session_state.get("_catalogo_recuperado_49_local", False):
            destino_recuperacao = preparar_catalogo_recuperado_local()
            st.session_state["_catalogo_recuperado_49_local"] = True
            st.info(
                f"Catálogo recuperado preservado em {destino_recuperacao}. "
                "O Google só será alterado quando você usar o botão de restauração na aba Catálogo."
            )
        force_sync_sidebar = st.button("🔄 Atualizar leitura da auditoria", key="sync_auditoria_sidebar")
        if _google_cooldown_ativo():
            st.warning(f"Planilhas Google em espera por {_segundos_cooldown_google()}s. A cópia local e os backups permanecem preservados.")
    elif not st.session_state.get("_catalogo_recuperado_49_local", False):
        preparar_catalogo_recuperado_local()
        st.session_state["_catalogo_recuperado_49_local"] = True

    auditoria_sidebar = carregar_auditoria(force_google=force_sync_sidebar)
    banca_auditada = banca_atual(banca_inicial, auditoria_sidebar)
    usar_banca_auditada = st.checkbox("Usar banca calculada pela auditoria", value=True)
    banca_manual = st.number_input("Banca manual", min_value=0.0, value=1000.0, step=50.0)
    banca_usada = float(banca_auditada if usar_banca_auditada else banca_manual)
    st.metric("Banca usada", fmt_dinheiro(banca_usada))

    st.divider()
    st.header("Modelo")
    liga_sel = st.selectbox("Liga", list(LIGAS_CSV.keys()))
    modo_recorte = st.selectbox(
        "Recorte histórico",
        ["Temporada atual", "Últimos 300 jogos", "Últimos 500 jogos", "Últimos 760 jogos", "Últimos 1500 jogos", "Histórico completo", "Data personalizada"],
        index=0,
        help="Padrão recomendado: temporada atual. Histórico completo só para estudo, porque pode misturar anos demais.",
    )
    data_inicio_recorte = None
    data_fim_recorte = None
    if modo_recorte == "Data personalizada":
        ano_atual = date.today().year
        data_inicio_recorte = seletor_data_portugues("Data inicial da base", valor=date(ano_atual, 1, 1), chave="data_inicio_base")
        data_fim_recorte = seletor_data_portugues("Data final da base", valor=date.today(), chave="data_fim_base")
        st.caption("Datas no padrão brasileiro: dia/mês/ano.")
    amostra_minima = st.slider("Amostra mínima casa/fora", 3, 12, 5, 1)
    politica_amostra_baixa = st.selectbox(
        "Política para amostra baixa",
        ["Avisar e reduzir entrada", "Bloquear entrada", "Mostrar só para estudo"],
        index=0,
        help="Quando a amostra casa/fora fica abaixo do mínimo. Padrão: não zera o valor matemático; só reduz entrada e avisa.",
    )
    fator_reducao_amostra_pct = st.slider(
        "Entrada em amostra baixa",
        min_value=10.0,
        max_value=100.0,
        value=50.0,
        step=5.0,
        format="%.0f%%",
        help="Usado apenas quando a política é 'Avisar e reduzir entrada'. Ex: 50% = metade da entrada sugerida.",
    )
    fator_reducao_amostra = fator_reducao_amostra_pct / 100.0

    st.markdown("**Estabilidade e ajuste**")
    regressao_media_ativa = st.checkbox(
        "Aplicar ajuste à média da liga",
        value=True,
        help="Mantém a informação recente, mas reduz o efeito de placares extremos. Pode ser desligado para reproduzir o cálculo antigo.",
    )
    peso_media_liga_pct = st.slider(
        "Peso da média da liga",
        min_value=0.0,
        max_value=50.0,
        value=25.0,
        step=5.0,
        format="%.0f%%",
        disabled=not regressao_media_ativa,
        help="25% significa: 75% da média recente do time e 25% da média atual da liga.",
    )
    peso_media_liga = peso_media_liga_pct / 100.0 if regressao_media_ativa else 0.0
    teste_estabilidade_ativo = st.checkbox(
        "Comparar estabilidade em 5/8/12 jogos",
        value=True,
        help="As janelas medem estabilidade. Quando mudam de lado, a entrada é reduzida, mas a análise não é congelada automaticamente.",
    )
    peso_prob_empirica_pct = st.slider(
        "Peso das frequências reais em gols/ambas marcam",
        min_value=0.0,
        max_value=70.0,
        value=40.0,
        step=5.0,
        format="%.0f%%",
        help="Combina Poisson com frequências suavizadas do mandante em casa, visitante fora e liga. Resultado final 1X2 permanece Poisson.",
    )
    peso_prob_empirica = peso_prob_empirica_pct / 100.0
    usar_direcao_algebrica_gols = st.checkbox(
        "Usar a soma projetada para escolher Mais ou Menos de 2,5",
        value=True,
        help="Com a opção ativa, total projetado igual ou superior a 2,50 aponta Mais de 2,5; abaixo de 2,50 aponta Menos de 2,5.",
    )
    usar_direcao_algebrica_btts = st.checkbox(
        "Usar o placar algébrico arredondado para escolher Ambas marcam",
        value=True,
        help="O arredondamento é aritmético: se os dois lados resultarem em pelo menos 1 gol, aponta Sim; se algum resultar em zero, aponta Não.",
    )
    reduzir_conflito_modelos = st.checkbox(
        "Reduzir a entrada quando componentes internos discordarem",
        value=True,
        help="A soma algébrica continua escolhendo o lado; divergências de Poisson, frequência real ou janelas apenas reduzem a entrada, sem congelar toda a análise.",
    )

    st.divider()
    st.header("Entrada")
    somente_probabilidades = st.checkbox(
        "Modo somente probabilidades — sem calcular entrada",
        value=False,
        help="Use apenas quando quiser analisar sem cotações. O padrão é comparar cotações reais e calcular o valor matemático.",
    )
    fracao_kelly = st.select_slider(
        "Cálculo proporcional da entrada",
        options=[0.10, 0.125, 0.20, 0.25, 0.33, 0.50],
        value=0.25,
        format_func=lambda x: {0.10: "1/10 do cálculo", 0.125: "1/8 do cálculo", 0.20: "1/5 do cálculo", 0.25: "1/4 do cálculo", 0.33: "1/3 do cálculo", 0.50: "1/2 do cálculo"}.get(x, str(x)),
    )
    margem_minima_pct = st.slider(
        "Margem mínima valor positivo",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        format="%.1f%%",
        help="0% só para estudo; 2% volume; 3% padrão honesto; 5% conservador.",
    )
    margem_minima = margem_minima_pct / 100.0
    teto_por_entrada_pct = st.slider("Teto por entrada", 0.5, 10.0, 3.0, 0.5, format="%.1f%%")
    teto_por_jogo_pct = st.slider("Teto total no jogo", 0.5, 20.0, 2.0, 0.5, format="%.1f%%")
    teto_por_entrada = teto_por_entrada_pct / 100.0
    teto_por_jogo = teto_por_jogo_pct / 100.0
    fator_reducao_divergencia_pct = st.slider(
        "Redução da entrada em divergência forte com o mercado",
        min_value=10.0,
        max_value=100.0,
        value=50.0,
        step=5.0,
        format="%.0f%%",
        help="Quando o modelo bate de frente com o mercado, a entrada é reduzida automaticamente. Não bloqueia; só protege a banca.",
    )
    fator_reducao_divergencia = fator_reducao_divergencia_pct / 100.0
    politica_correlacao = st.selectbox(
        "Tratamento de mercados correlacionados",
        ["Manter somente a principal", "Dividir a entrada entre correlacionados", "Somente avisar"],
        index=0,
        help="Evita somar como independentes Mais de 2,5 + Ambas marcam — Sim ou Menos de 2,5 + Ambas marcam — Não.",
    )
    permitir_multiplas_entradas = st.checkbox(
        "Permitir mais de uma entrada no mesmo jogo — modo avançado",
        value=False,
        help="Desmarcado por padrão. Quando desmarcado, o aplicativo escolhe uma única entrada principal e transforma as demais em sinais de confirmação.",
    )
    st.caption("O padrão é informar cotações reais. O modo somente probabilidades vem desmarcado. A entrada é calculada depois da direção algébrica, das travas de coerência e da escolha de um único mercado principal.")

    st.divider()
    st.header("Cotações")
    casa_apostas = st.selectbox("Casa de apostas", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"])
    chave_api = st.text_input("Chave da fonte automática de cotações", value=os.getenv("ODDS_API_KEY", ""), type="password")

aba_analisar, aba_diagnostico, aba_scout, aba_auditoria, aba_catalogo, aba_historico, aba_calendario = st.tabs(["🎯 Analisar jogo", "🧪 Diagnóstico da liga", "🔎 Análise complementar", "📒 Auditoria", "📊 Catálogo", "🧾 Histórico de análises", "🗓️ Ligas"])

with st.spinner("Carregando base da liga..."):
    df_liga_bruta = carregar_dados_liga(LIGAS_CSV[liga_sel], 0)
    df_liga = aplicar_recorte_historico(df_liga_bruta, modo_recorte, LIGAS_CSV[liga_sel], data_inicio_recorte, data_fim_recorte)

if df_liga.empty:
    st.error("Não consegui carregar os dados históricos desta liga. Confira conexão, URL ou tente outra liga.")
    st.stop()

times_liga = sorted(df_liga["Home"].dropna().astype(str).unique().tolist())

with aba_analisar:
    resumo_base = resumo_base_dados(df_liga)
    st.markdown(f'<div class="base-info">{html.escape(texto_base_dados(resumo_base, modo_recorte))}</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_stat_card("Jogos usados", len(df_liga), "recorte ativo", "📚")
    with m2:
        render_stat_card("Times", len(times_liga), "na base filtrada", "🧩")
    with m3:
        render_stat_card("Média gols casa", fmt_num(float(df_liga["HG"].mean()), 2), "liga", "🏠")
    with m4:
        render_stat_card("Média gols fora", fmt_num(float(df_liga["AG"].mean()), 2), "liga", "🛫")

    st.markdown("---")
    modo = st.radio("Modo de análise", ["Manual", "Automático pela fonte de cotações"], horizontal=True)

    odds: Dict[str, float] = {}
    time_casa = times_liga[0]
    time_fora = times_liga[min(1, len(times_liga) - 1)]
    jogo_nome = ""
    origem = modo
    data_jogo_catalogo = date.today()
    hora_jogo_catalogo = ""
    botao_analisar = False
    botao_salvar_cotacoes = False

    if modo == "Manual":
        st.markdown("### Jogo")
        st.info("Para apenas obter probabilidades, ative o modo somente probabilidades. Para a análise normal, informe cotações reais da mesma casa.")
        c1, c2 = st.columns(2)
        with c1:
            time_casa = st.selectbox("Mandante", times_liga, key="manual_casa")
        with c2:
            time_fora = st.selectbox("Visitante", times_liga, key="manual_fora")

        c1, c2 = st.columns(2)
        with c1:
            data_jogo_catalogo = seletor_data_portugues("Data do jogo ou mercado", valor=date.today(), chave="data_jogo")
            st.caption("Formato brasileiro: dia/mês/ano.")
        with c2:
            hora_jogo_catalogo = st.text_input("Hora do jogo", value="", placeholder="ex: 15:45", key="hora_jogo")

        if time_casa == time_fora:
            st.warning("Mandante e visitante não podem ser o mesmo time.")
        else:
            jogo_nome = f"{time_casa} x {time_fora}"
            odds = coletar_odds_manuais("manual")
            st.caption("ANALISAR JOGO não grava nada. O catálogo só recebe dados quando você clicar em SALVAR COTAÇÕES.")
            c1, c2 = st.columns(2)
            with c1:
                botao_analisar = st.button("ANALISAR JOGO", type="primary")
            with c2:
                botao_salvar_cotacoes = st.button("SALVAR COTAÇÕES")

    else:
        if not chave_api:
            st.warning("Informe a chave da fonte automática de cotações ou use o modo manual.")
        elif liga_sel not in LIGAS_API:
            st.warning("Liga sem mapeamento na fonte automática de cotações. Use o modo manual.")
        else:
            jogos_api = buscar_odds_api(chave_api, LIGAS_API[liga_sel])
            if not jogos_api:
                st.warning("A fonte automática não retornou jogos ou cotações agora. Use o modo manual.")
            else:
                agora = pd.Timestamp.now(tz="UTC")
                opcoes = {}
                for jogo in jogos_api:
                    try:
                        inicio = pd.to_datetime(jogo.get("commence_time"), utc=True)
                        if inicio <= agora:
                            continue
                        horario = inicio.tz_convert("America/Sao_Paulo").strftime("%d/%m %H:%M")
                        label = f"{jogo.get('home_team')} x {jogo.get('away_team')} — {horario}"
                        opcoes[label] = jogo
                    except Exception:
                        continue
                if not opcoes:
                    st.warning("A fonte automática respondeu, mas não há partida futura disponível.")
                else:
                    escolha = st.selectbox("Partida", list(opcoes.keys()))
                    jogo_api = opcoes[escolha]
                    try:
                        inicio_local = pd.to_datetime(jogo_api.get("commence_time"), utc=True).tz_convert("America/Sao_Paulo")
                        data_jogo_catalogo = inicio_local.date()
                        hora_jogo_catalogo = inicio_local.strftime("%H:%M")
                    except Exception:
                        pass
                    casa_api = jogo_api.get("home_team", "")
                    fora_api = jogo_api.get("away_team", "")
                    match_casa, score_casa = casar_time_seguro(casa_api, times_liga)
                    match_fora, score_fora = casar_time_seguro(fora_api, times_liga)

                    if match_casa is None or match_fora is None:
                        st.error("Não foi possível relacionar com segurança os nomes recebidos com a base. Use o modo manual. O aplicativo não escolherá um time por aproximação insegura.")
                        st.write({"Mandante recebido": casa_api, "Visitante recebido": fora_api})
                    else:
                        st.success(f"Times casados: {casa_api} → {match_casa} ({score_casa:.0%}); {fora_api} → {match_fora} ({score_fora:.0%})")
                        c1, c2 = st.columns(2)
                        with c1:
                            time_casa = st.selectbox("Mandante na base", times_liga, index=times_liga.index(match_casa), key="api_casa")
                        with c2:
                            time_fora = st.selectbox("Visitante na base", times_liga, index=times_liga.index(match_fora), key="api_fora")
                        odds, aviso_api = extrair_odds_api(jogo_api, casa_apostas)
                        jogo_nome = f"{time_casa} x {time_fora}"
                        if aviso_api:
                            if "⚠️" in aviso_api:
                                st.warning(aviso_api)
                            else:
                                st.info(aviso_api)
                        st.info(f"Mercados com cotação encontrados: {len(odds)}")
                        st.caption("ANALISAR JOGO não grava nada. O catálogo só recebe dados quando você clicar em SALVAR COTAÇÕES.")
                        c1, c2 = st.columns(2)
                        with c1:
                            botao_analisar = st.button("ANALISAR JOGO", type="primary", key="api_analisar")
                        with c2:
                            botao_salvar_cotacoes = st.button("SALVAR COTAÇÕES", key="api_salvar_cotacoes")

    if botao_salvar_cotacoes:
        if not odds:
            st.error("Nenhuma cotação válida para salvar.")
        elif time_casa == time_fora:
            st.error("Mandante e visitante não podem ser iguais.")
        else:
            id_snapshot = uuid.uuid4().hex[:8]
            snapshot = registrar_odds_catalogo(
                pd.DataFrame(columns=COLUNAS_CATALOGO),
                liga_sel, jogo_nome, time_casa, time_fora, casa_apostas, odds,
                banca_usada, "Planilha Pura", data_jogo_catalogo, hora_jogo_catalogo,
                origem, "Lote salvo por clique explícito; histórico somente de acréscimo",
                id_coleta=id_snapshot,
            )
            destino = salvar_catalogo(snapshot)
            st.session_state["ultima_coleta_catalogo_salva"] = id_snapshot
            st.success(
                f"Uma coleta com {len(snapshot)} cotação(ões) foi processada. O Google recebeu no máximo uma gravação em lote. "
                f"Nenhuma linha antiga foi alterada ou apagada. Destino: {destino}."
            )

    if botao_analisar:
        if not odds and not somente_probabilidades:
            st.error("Nenhuma cotação válida foi informada. Ative 'Modo somente probabilidades — sem calcular entrada' para analisar sem cotações.")
        elif time_casa == time_fora:
            st.error("Mandante e visitante não podem ser iguais.")
        else:
            id_analise = uuid.uuid4().hex
            id_coleta_analise = str(st.session_state.get("ultima_coleta_catalogo_salva", "")) if odds else ""

            df_modelo, jogos_futuros_removidos = filtrar_base_antes_do_jogo(df_liga, data_jogo_catalogo)
            if df_modelo.empty:
                st.error("A base ficou vazia após o corte anterior à data do jogo. Confira a data selecionada.")
                st.stop()

            calc = calcular_planilha_pura(
                df_modelo, time_casa, time_fora,
                regressao_media_ativa=regressao_media_ativa,
                peso_media_liga=peso_media_liga,
                peso_prob_empirica=peso_prob_empirica,
            )
            estabilidade = calcular_estabilidade_janelas(
                df_modelo, time_casa, time_fora, regressao_media_ativa, peso_media_liga,
                peso_prob_empirica=peso_prob_empirica,
            ) if teste_estabilidade_ativo else None

            amostra_ok = int(calc["amostra_minima"]) >= int(amostra_minima)
            motivo_bloqueio = ""
            if not amostra_ok:
                motivo_bloqueio = f"{time_casa} em casa {calc['jogos_casa']} jogo(s), {time_fora} fora {calc['jogos_fora']} jogo(s). Mínimo configurado: {amostra_minima}."

            if odds:
                resultados = avaliar_valor_planilha(
                    calc["probabilidades"], odds, banca_usada, fracao_kelly, margem_minima,
                    teto_por_entrada, teto_por_jogo, amostra_ok, motivo_bloqueio,
                    politica_amostra_baixa=politica_amostra_baixa,
                    fator_reducao_amostra=fator_reducao_amostra,
                    amostra_minima_real=int(calc.get("amostra_minima", 0)),
                    fator_reducao_divergencia=fator_reducao_divergencia,
                )
                resultados = aplicar_travas_coerencia(
                    resultados, calc, estabilidade,
                    usar_direcao_algebrica_gols=usar_direcao_algebrica_gols,
                    usar_direcao_algebrica_btts=usar_direcao_algebrica_btts,
                    reduzir_conflito_modelos=reduzir_conflito_modelos,
                )
                resultados = ajustar_exposicao_correlacionada(resultados, banca_usada, politica_correlacao)
                resultados = manter_apenas_entrada_principal(
                    resultados,
                    banca=banca_usada,
                    teto_por_jogo=teto_por_jogo,
                    permitir_multiplas=permitir_multiplas_entradas,
                )
                if somente_probabilidades:
                    resultados = aplicar_modo_estudo(resultados)
                else:
                    resultados = limpar_dataframe_operacional(resultados)
            else:
                resultados = pd.DataFrame()

            periodo_usado = resumo_base_dados(df_modelo)
            dias_base_jogo = dias_base_ate_jogo(periodo_usado, data_jogo_catalogo)
            resultados = aplicar_alerta_base_distante(resultados, dias_base_jogo)
            resultados = limpar_dataframe_operacional(resultados)

            st.session_state["ultima_analise_v20"] = {
                "id": id_analise,
                "id_coleta": id_coleta_analise,
                "liga": liga_sel,
                "jogo": jogo_nome,
                "time_casa": time_casa,
                "time_fora": time_fora,
                "origem": origem,
                "casa_apostas": casa_apostas,
                "banca": banca_usada,
                "calc": calc,
                "odds": odds,
                "resultados": resultados.to_dict("records") if not resultados.empty else [],
                "estabilidade": estabilidade,
                "amostra_ok": amostra_ok,
                "motivo_bloqueio": motivo_bloqueio,
                "config": {
                    "janela": modo_recorte,
                    "periodo_base": periodo_usado,
                    "data_jogo": data_jogo_catalogo.strftime("%Y-%m-%d") if isinstance(data_jogo_catalogo, date) else str(data_jogo_catalogo),
                    "dias_base_jogo": dias_base_jogo,
                    "fracao_kelly": fracao_kelly,
                    "margem_minima": margem_minima,
                    "teto_por_entrada": teto_por_entrada,
                    "teto_por_jogo": teto_por_jogo,
                    "amostra_minima": amostra_minima,
                    "politica_amostra_baixa": politica_amostra_baixa,
                    "fator_reducao_amostra": fator_reducao_amostra,
                    "fator_reducao_divergencia": fator_reducao_divergencia,
                    "regressao_media_ativa": regressao_media_ativa,
                    "peso_media_liga": peso_media_liga,
                    "teste_estabilidade_ativo": teste_estabilidade_ativo,
                    "usar_direcao_algebrica_gols": usar_direcao_algebrica_gols,
                    "usar_direcao_algebrica_btts": usar_direcao_algebrica_btts,
                    "reduzir_conflito_modelos": reduzir_conflito_modelos,
                    "politica_correlacao": politica_correlacao,
                    "permitir_multiplas_entradas": permitir_multiplas_entradas,
                    "peso_prob_empirica": peso_prob_empirica,
                    # Configuração V20.3 atual: sem chaves órfãs de versões anteriores.
                    "somente_probabilidades": somente_probabilidades,
                    "jogos_futuros_removidos": jogos_futuros_removidos,
                },
            }

            historico_analise = registrar_historico_analise(
                id_analise=id_analise,
                id_coleta=id_coleta_analise,
                liga=liga_sel,
                jogo=jogo_nome,
                time_casa=time_casa,
                time_fora=time_fora,
                data_jogo=data_jogo_catalogo,
                hora_jogo=hora_jogo_catalogo,
                casa_apostas=casa_apostas,
                origem=origem,
                odds=odds,
                calc=calc,
                resultados=resultados,
                estabilidade=estabilidade,
                config=st.session_state["ultima_analise_v20"]["config"],
            )
            st.session_state["historico_analise_pendente"] = historico_analise
            st.info("Análise concluída sem qualquer gravação automática no Google. O histórico da análise ficou apenas na sessão até uma ação explícita de salvamento.")

    analise = st.session_state.get("ultima_analise_v20")
    if analise:
        calc = analise["calc"]
        resultados = limpar_dataframe_operacional(pd.DataFrame(analise["resultados"]))
        aprovadas = resultados[(resultados["Veredito"].eq("VALOR POSITIVO")) & (pd.to_numeric(resultados["Entrada %"], errors="coerce").fillna(0.0) > 0)].copy() if not resultados.empty else pd.DataFrame()
        if not resultados.empty and "Valor matemático" in resultados.columns:
            valores_matematicos = resultados[resultados["Valor matemático"].astype(str).eq("SIM")].copy()
        else:
            valores_matematicos = pd.DataFrame()

        st.markdown("---")
        st.markdown(
            f'''
            <div class="analysis-head">
                <div class="analysis-kicker">Análise operacional</div>
                <div class="analysis-title">{html.escape(str(analise['jogo']))}</div>
                <div class="version-pill">Versão carregada: TEX ESTATÍSTICAS V20.3.5 — direção algébrica, coerência interna e uma entrada principal</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        politica_atual = str(analise.get("config", {}).get("politica_amostra_baixa", "Avisar e reduzir entrada"))
        fator_amostra_atual = float(analise.get("config", {}).get("fator_reducao_amostra", 0.50))
        if not analise.get("amostra_ok", False):
            if "Bloquear" in politica_atual:
                st.error(f"Amostra baixa: {analise.get('motivo_bloqueio', '')} Política atual: bloquear entrada.")
            elif "estudo" in politica_atual.lower():
                st.warning(f"Amostra baixa: {analise.get('motivo_bloqueio', '')} Política atual: mostrar só para estudo.")
            else:
                st.warning(f"Amostra baixa: {analise.get('motivo_bloqueio', '')} Política atual: permitir com entrada reduzida para {fmt_pct(fator_amostra_atual, 0)}.")
        else:
            st.success("Qualidade mínima dos dados aprovada. A entrada será decidida pela direção algébrica, coerência interna, valor esperado e limite por jogo.")

        periodo_base = analise.get("config", {}).get("periodo_base") or resumo_base_dados(df_liga)
        st.markdown(f'<div class="base-info">{html.escape(texto_base_dados(periodo_base, analise.get("config", {}).get("janela", "-")))}</div>', unsafe_allow_html=True)
        removidos = int(analise.get("config", {}).get("jogos_futuros_removidos", 0) or 0)
        if removidos > 0:
            st.warning(f"Corte temporal ativo: {removidos} jogo(s) na data do evento ou posteriores foram removidos da base antes do cálculo.")
        dias_base_jogo = analise.get("config", {}).get("dias_base_jogo")
        data_jogo_cfg = analise.get("config", {}).get("data_jogo", "-")
        if dias_base_jogo is not None:
            if int(dias_base_jogo) > 14:
                st.warning(f"⚠️ Base distante da data do jogo: jogo em {data_jogo_cfg}, última partida da base em {periodo_base.get('fim', '-')}. Distância: {int(dias_base_jogo)} dia(s). Pode haver pausa, amistosos, desfalques, troca de técnico ou mudança de elenco que o modelo não capturou.")
            elif int(dias_base_jogo) >= 0:
                st.info(f"Base próxima da data do jogo: {int(dias_base_jogo)} dia(s) entre a última partida da base e o jogo analisado.")

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            render_stat_card("Gols esperados — casa", fmt_num(calc["gols_esperados_casa"], 2), analise["time_casa"], "⚽")
        with c2:
            render_stat_card("Gols esperados — fora", fmt_num(calc["gols_esperados_fora"], 2), analise["time_fora"], "⚽")
        with c3:
            render_stat_card("Total projetado", fmt_num(calc.get("gols_total_esperado", 0), 2), "linha de 2,5", "➕")
        with c4:
            render_stat_card("Placar arredondado", f"{calc.get('placar_arredondado_casa', 0)} x {calc.get('placar_arredondado_fora', 0)}", "apenas visual, não é previsão", "🧮")
            render_stat_card("Mandante marcar", fmt_pct(float(calc.get('prob_casa_marcar', 0.0)), 1), "chance de ao menos um gol", "🏠")
            render_stat_card("Visitante marcar", fmt_pct(float(calc.get('prob_fora_marcar', 0.0)), 1), "chance de ao menos um gol", "🛫")
        with c5:
            render_stat_card("Amostra casa/fora", f"{calc['jogos_casa']} / {calc['jogos_fora']}", "recortes posicionais", "📚")
        with c6:
            render_stat_card("Entradas liberadas", len(aprovadas), "após todas as travas", "✅")

        conf = classificar_confianca_estimativa(calc, resultados)
        render_botao_confianca(conf)
        st.info("Qualidade dos dados descreve o tamanho e a consistência do recorte. A validação histórica continua sendo acompanhada, mas não paralisa o motor.")

        if calc.get("regressao_media_ativa"):
            st.info(f"Ajuste à média da liga ativo: {fmt_pct(float(calc.get('peso_media_liga', 0.0)), 0)} da média da liga e {fmt_pct(1.0 - float(calc.get('peso_media_liga', 0.0)), 0)} do recorte recente.")
        else:
            st.caption("Ajuste à média da liga desativado: cálculo reproduz as médias observadas sem suavização.")

        estabilidade = analise.get("estabilidade")
        if estabilidade:
            nivel_est = str(estabilidade.get("nivel", "INCONCLUSIVO"))
            msg_est = f"Estabilidade 5/8/12: {nivel_est} — {estabilidade.get('motivo', '')}"
            if nivel_est == "ESTÁVEL":
                st.success(msg_est)
            elif nivel_est == "INSTÁVEL":
                st.warning(msg_est)
            else:
                st.info(msg_est)
            with st.expander("Ver comparação de estabilidade 5/8/12", expanded=False):
                tabela_est = formatar_tabela_estabilidade(estabilidade)
                if not tabela_est.empty:
                    st.dataframe(tabela_est, use_container_width=True, hide_index=True)

        with st.expander("Ver cálculo de forças da planilha"):
            dados_forca = pd.DataFrame([
                {"Item": "Média gols casa liga", "Valor": calc["media_gols_casa_liga"]},
                {"Item": f"{analise['time_casa']} gols feitos em casa — observado", "Valor": calc.get("gols_feitos_casa_bruto", calc["gols_feitos_casa"])},
                {"Item": f"{analise['time_casa']} gols feitos em casa — usado", "Valor": calc["gols_feitos_casa"]},
                {"Item": f"{analise['time_casa']} gols sofridos em casa — observado", "Valor": calc.get("gols_sofridos_casa_bruto", calc["gols_sofridos_casa"])},
                {"Item": f"{analise['time_casa']} gols sofridos em casa — usado", "Valor": calc["gols_sofridos_casa"]},
                {"Item": f"{analise['time_casa']} força ataque casa", "Valor": calc["forca_ataque_casa"]},
                {"Item": f"{analise['time_casa']} força defesa casa", "Valor": calc["forca_defesa_casa"]},
                {"Item": "Média gols fora liga", "Valor": calc["media_gols_fora_liga"]},
                {"Item": f"{analise['time_fora']} gols feitos fora — observado", "Valor": calc.get("gols_feitos_fora_bruto", calc["gols_feitos_fora"])},
                {"Item": f"{analise['time_fora']} gols feitos fora — usado", "Valor": calc["gols_feitos_fora"]},
                {"Item": f"{analise['time_fora']} gols sofridos fora — observado", "Valor": calc.get("gols_sofridos_fora_bruto", calc["gols_sofridos_fora"])},
                {"Item": f"{analise['time_fora']} gols sofridos fora — usado", "Valor": calc["gols_sofridos_fora"]},
                {"Item": f"{analise['time_fora']} força ataque fora", "Valor": calc["forca_ataque_fora"]},
                {"Item": f"{analise['time_fora']} força defesa fora", "Valor": calc["forca_defesa_fora"]},
            ])
            dados_forca["Valor"] = dados_forca["Valor"].map(lambda x: fmt_num(float(x), 3))
            st.dataframe(dados_forca, use_container_width=True, hide_index=True)

        with st.expander("Ver jogos usados no cálculo da planilha", expanded=False):
            jogos_casa_usados = calc.get("jogos_casa_usados", []) or []
            jogos_fora_usados = calc.get("jogos_fora_usados", []) or []
            st.caption("Aqui estão exatamente os jogos que alimentaram as médias de gols feitos/sofridos, as forças e os gols esperados. Não entram copa, amistoso ou jogo fora desse recorte se eles não estiverem na base filtrada acima.")

            resumo_jogos = tabela_resumo_jogos_usados(analise["time_casa"], analise["time_fora"], jogos_casa_usados, jogos_fora_usados)
            st.dataframe(resumo_jogos, use_container_width=True, hide_index=True)
            render_resumo_jogos_legivel(analise["time_casa"], analise["time_fora"], jogos_casa_usados, jogos_fora_usados)

            aba_jc, aba_jf = st.tabs([f"🏠 {analise['time_casa']} em casa", f"🛫 {analise['time_fora']} fora"])
            with aba_jc:
                if jogos_casa_usados:
                    st.dataframe(pd.DataFrame(jogos_casa_usados), use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum jogo do mandante em casa entrou no cálculo.")
            with aba_jf:
                if jogos_fora_usados:
                    st.dataframe(pd.DataFrame(jogos_fora_usados), use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum jogo do visitante fora entrou no cálculo.")

        if calc.get("cantos"):
            with st.expander("Cantos — leitura simples da planilha"):
                cantos = calc["cantos"]
                linha_cantos = st.number_input("Linha total de cantos da casa", min_value=0.0, value=10.0, step=0.5)
                dif = float(cantos["cantos_total"]) - float(linha_cantos)
                if abs(dif) < 0.75:
                    msg = "RISCO ALTO / linha justa demais"
                elif dif > 0:
                    msg = "Tendência de mais cantos"
                else:
                    msg = "Tendência de menos cantos"
                st.write(f"Previsão total: **{fmt_num(cantos['cantos_total'], 2)}** | Linha: **{fmt_num(linha_cantos, 1)}** | Diferença: **{fmt_num(dif, 2)}** | {msg}")

        st.markdown("### Probabilidades auditáveis")
        st.caption("Resultado final usa Poisson. Total de gols e ambas marcam combinam Poisson com frequência empírica suavizada. A probabilidade operacional é a usada na cotação justa.")
        st.dataframe(tabela_comparacao_probabilidades(calc), use_container_width=True, hide_index=True)
        emp = calc.get("probabilidades_empiricas", {}) or {}
        diag_disp = calc.get("diagnostico_dispersao", {}) or {}
        st.caption(
            f"Frequências brutas — Mais de 2,5: casa {fmt_pct(float(emp.get('over25_casa_bruta', 0)), 1)}, fora {fmt_pct(float(emp.get('over25_fora_bruta', 0)), 1)}, liga {fmt_pct(float(emp.get('over25_liga', 0)), 1)}. "
            f"Ambas marcam: casa {fmt_pct(float(emp.get('btts_casa_bruta', 0)), 1)}, fora {fmt_pct(float(emp.get('btts_fora_bruta', 0)), 1)}, liga {fmt_pct(float(emp.get('btts_liga', 0)), 1)}. "
            f"Dispersão total: {diag_disp.get('nivel', '-')}"
        )

        if resultados.empty:
            if analise.get("config", {}).get("somente_probabilidades", False):
                st.info("Análise concluída sem cotações: probabilidades exibidas acima, nenhuma entrada calculada.")
            else:
                st.warning("Nenhum mercado com cotação válida para comparar.")
        else:
            st.markdown("### Resumo operacional")
            st.caption("Tela principal limpa. A tabela completa fica recolhida abaixo para auditoria técnica.")
            st.dataframe(formatar_tabela_resumo_operacional(resultados), use_container_width=True, hide_index=True)
            with st.expander("Tabela técnica completa da planilha", expanded=False):
                st.dataframe(formatar_tabela_resultados(resultados), use_container_width=True, hide_index=True)

            if not aprovadas.empty:
                total_entrada = float(aprovadas["Entrada R$"].sum())
                st.success(f"Mercados operacionalmente elegíveis após todas as travas: {len(aprovadas)}. Exposição calculada: {fmt_dinheiro_texto(total_entrada)}. Isto não é garantia de acerto.")

                avisos_correlacao = detectar_correlacao_operacional(aprovadas, calc)
                if avisos_correlacao:
                    st.warning("⚠️ Exposição correlacionada no mesmo jogo:\n" + "\n".join(f"- {texto_limpo_para_tela(a)}" for a in avisos_correlacao))

                if "Alerta de mercado" in aprovadas.columns:
                    alertas_mercado_gerais = []
                    for alerta in aprovadas["Alerta de mercado"].dropna().astype(str):
                        for parte in [p.strip() for p in alerta.split("|") if p.strip()]:
                            if parte not in alertas_mercado_gerais:
                                alertas_mercado_gerais.append(parte)
                    if alertas_mercado_gerais:
                        render_alerta_lista("⚠️ Divergência com o mercado", alertas_mercado_gerais)

                etiquetas_gerais = "; ".join(str(x) for x in aprovadas.get("Etiquetas", pd.Series(dtype=str)).dropna().astype(str).tolist())
                precisa_checklist = any(p in etiquetas_gerais for p in ["Divergência extrema", "Divergência forte", "Contra favorito", "Mercado de gols contrário", "Base distante"])
                if precisa_checklist:
                    with st.expander("✅ Lista de conferência manual antes de registrar uma entrada", expanded=False):
                        st.warning("Há valor matemático, mas existe alerta operacional. Faça a conferência humana; o aplicativo não conhece automaticamente notícias, escalações, lesões ou movimentos recentes da cotação.")
                        checks = [
                            ("cotacao", "Conferi a cotação na mesma casa onde vou apostar."),
                            ("mandante", "Conferi que mandante, visitante e competição estão corretos."),
                            ("base", "Conferi se a base está atualizada ou aceitei o risco de base distante/pós-pausa."),
                            ("noticias", "Conferi notícias reais de desfalque, treinador, escalação ou elenco — ou assumo que não sei."),
                            ("mercado", "Entendi quando o mercado de gols/resultado está contra o modelo."),
                            ("exposicao", "Entendi que entradas correlacionadas não são apostas independentes."),
                        ]
                        st.markdown("**Marque os itens abaixo antes de transformar isto em aposta real:**")
                        valores_check = []
                        for i, (suf, texto_check) in enumerate(checks, start=1):
                            valores_check.append(
                                st.checkbox(
                                    f"{i}. {texto_check}",
                                    value=False,
                                    key=f"check_operacional_{analise['id']}_{suf}",
                                )
                            )
                        checklist_ok = all(valores_check)
                        st.session_state[f"checklist_operacional_ok_{analise['id']}"] = checklist_ok
                        if checklist_ok:
                            st.success("Lista de conferência concluída. Isso não garante acerto; apenas confirma que a verificação mínima foi realizada.")
                        else:
                            st.error("Entrada operacional pendente de conferência. Para banca real, trate como estudo ou reduza bastante a exposição.")

                for _, r in aprovadas.iterrows():
                    render_card_valor_positivo(r)
            else:
                if not valores_matematicos.empty:
                    st.warning("Existe valor matemático positivo na tabela, mas a política operacional atual não liberou entrada real. Veja as colunas 'Valor matemático' e 'Situação operacional'.")
                else:
                    st.info("Nenhum mercado ficou valor positivo com as cotações informadas.")

        st.markdown("---")
        st.markdown("### Resumo para compartilhar")
        st.caption("Texto automático com os principais números, configurações, estabilidade, entradas e alertas. Pode ser copiado e enviado sem repetir toda a tela.")
        resumo_compartilhavel = gerar_resumo_compartilhavel(
            analise, calc, resultados, aprovadas, conf, analise.get("estabilidade")
        )
        st.text_area(
            "Resumo",
            value=resumo_compartilhavel,
            height=520,
            key=f"resumo_compartilhavel_{analise['id']}",
        )
        nome_resumo = re.sub(r"[^A-Za-z0-9_-]+", "_", str(analise.get("jogo", "analise"))).strip("_")
        st.download_button(
            "BAIXAR RESUMO EM TXT",
            data=resumo_compartilhavel.encode("utf-8"),
            file_name=f"resumo_{nome_resumo}.txt",
            mime="text/plain",
            key=f"download_resumo_{analise['id']}",
        )

        if not aprovadas.empty:
            st.markdown("---")
            st.markdown("### Registrar entradas com valor positivo na auditoria")
            with st.form(key=f"form_registrar_v20_{analise['id']}"):
                escolhidas_idx = []
                for idx, r in aprovadas.iterrows():
                    label = f"Registrar {mercado_exibicao(r['Mercado'])} — cotação {fmt_num(float(r['Cotação real']), 2)} — entrada {fmt_dinheiro_texto(float(r['Entrada R$']))}"
                    if st.checkbox(label, value=True, key=f"check_{analise['id']}_{idx}"):
                        escolhidas_idx.append(idx)
                obs = st.text_area("Observação", value="", placeholder="Ex: Pixbet, cotação conferida, escalação ok...", key=f"obs_{analise['id']}")
                salvar = st.form_submit_button("SALVAR MARCADAS NA AUDITORIA", type="primary")

            if salvar:
                if not escolhidas_idx:
                    st.warning("Nenhuma entrada marcada.")
                else:
                    auditoria = carregar_auditoria()
                    for idx in escolhidas_idx:
                        r = resultados.loc[idx]
                        auditoria = registrar_entrada(
                            auditoria=auditoria,
                            liga=analise["liga"],
                            jogo=analise["jogo"],
                            casa_apostas=analise["casa_apostas"],
                            mercado=str(r["Mercado"]),
                            odd=float(r["Cotação real"]),
                            prob=float(r["Probabilidade"]),
                            odd_justa=float(r["Cotação justa"]),
                            margem=float(r["Margem positiva"]),
                            entrada_pct=float(r["Entrada %"]),
                            entrada_rs=float(r["Entrada R$"]),
                            banca_antes=float(analise["banca"]),
                            origem=str(analise["origem"]),
                            observacao=(obs + f" | V20.3.5 Direção Algébrica | Janela {analise['config']['janela']} | Cálculo proporcional {analise['config']['fracao_kelly']} | Amostra: {analise['config'].get('politica_amostra_baixa', '-')} | Lista de conferência: {'CONCLUÍDA' if st.session_state.get(f'checklist_operacional_ok_{analise["id"]}', False) else 'PENDENTE'}").strip(),
                            etiquetas=str(r.get("Etiquetas", "")),
                            prob_mercado_bruta=float(r.get("Prob. mercado bruta")) if pd.notna(r.get("Prob. mercado bruta")) else None,
                            prob_mercado_ajustada=float(r.get("Prob. mercado ajustada")) if pd.notna(r.get("Prob. mercado ajustada")) else None,
                            margem_mercado=float(r.get("Margem do mercado")) if pd.notna(r.get("Margem do mercado")) else None,
                            fonte_probabilidade="Motor V20.3.5: direção algébrica para gols e ambas marcam; Poisson e frequência empírica como confirmação; corte temporal anterior ao jogo",
                            versao_modelo=VERSAO_MODELO,
                        )
                    destino = salvar_auditoria(auditoria)
                    st.success(f"Entradas salvas. Destino: {destino}.")

        if st.button("LIMPAR ÚLTIMA ANÁLISE"):
            st.session_state.pop("ultima_analise_v20", None)
            st.rerun()


with aba_diagnostico:
    st.subheader("Diagnóstico científico da liga")
    st.caption("Esta aba não decide aposta. Ela só mostra se a distribuição de gols da liga parece razoavelmente compatível com Poisson.")
    diag = diagnostico_poisson_liga(df_liga)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Mandante")
        s = diag["casa_stats"]
        st.metric("Média gols mandante", fmt_num(s.get("media", 0.0), 2))
        st.metric("Aderência", str(s.get("aderencia", "-")))
        st.caption(f"p-valor indicativo: {fmt_num(s.get('p_valor', np.nan), 4) if np.isfinite(s.get('p_valor', np.nan)) else '-'}")
        st.dataframe(diag["casa_tabela"], use_container_width=True, hide_index=True)
    with c2:
        st.markdown("### Visitante")
        s = diag["fora_stats"]
        st.metric("Média gols visitante", fmt_num(s.get("media", 0.0), 2))
        st.metric("Aderência", str(s.get("aderencia", "-")))
        st.caption(f"p-valor indicativo: {fmt_num(s.get('p_valor', np.nan), 4) if np.isfinite(s.get('p_valor', np.nan)) else '-'}")
        st.dataframe(diag["fora_tabela"], use_container_width=True, hide_index=True)

    st.info(
        "Leitura responsável: aderência ruim significa que a Poisson simples descreve pior a distribuição de gols da liga; nessas condições, o resultado deve permanecer em estudo e não servir isoladamente para entrada financeira. "
        "Na V20.3.5, a soma projetada e o placar algébrico escolhem a direção. Poisson, frequência real, estabilidade e sobredispersão confirmam ou reduzem a entrada; divergência contra o mercado não bloqueia sozinha."
    )


with aba_scout:
    st.subheader("Análise complementar")
    st.caption("Finalizações, chutes no alvo, escanteios e cartões aparecem quando a base da liga contém essas informações. É um diagnóstico, não uma trava automática.")

    c1, c2 = st.columns(2)
    with c1:
        scout_casa = st.selectbox("Mandante para análise complementar", times_liga, key="scout_casa")
    with c2:
        scout_fora = st.selectbox("Visitante para análise complementar", times_liga, index=min(1, len(times_liga)-1), key="scout_fora")

    if scout_casa == scout_fora:
        st.warning("Escolha times diferentes.")
    else:
        tabela_scout, avisos_scout = calcular_scout_opcional(df_liga, scout_casa, scout_fora)
        st.dataframe(tabela_scout, use_container_width=True, hide_index=True)
        for aviso in avisos_scout:
            st.caption("• " + aviso)

        modelo_scout = calcular_planilha_pura(df_liga, scout_casa, scout_fora, regressao_media_ativa=regressao_media_ativa, peso_media_liga=peso_media_liga)
        c1, c2, c3 = st.columns(3)
        c1.metric("Gols esperados casa", fmt_num(modelo_scout["gols_esperados_casa"], 2))
        c2.metric("Gols esperados fora", fmt_num(modelo_scout["gols_esperados_fora"], 2))
        c3.metric("Total esperado", fmt_num(modelo_scout["gols_esperados_casa"] + modelo_scout["gols_esperados_fora"], 2))

        if modelo_scout.get("cantos"):
            cantos = modelo_scout["cantos"]
            st.markdown("### Escanteios previstos pela lógica simples")
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Cantos casa", fmt_num(cantos["cantos_casa"], 2))
            cc2.metric("Cantos fora", fmt_num(cantos["cantos_fora"], 2))
            cc3.metric("Total cantos", fmt_num(cantos["cantos_total"], 2))

with aba_catalogo:
    st.subheader("Catálogo de cotações")
    cfg = obter_config_google()
    if cfg.get("configurado"):
        st.success(f"Planilhas Google ativas. Aba: {cfg['worksheet_catalogo']}. O catálogo é somente de acréscimo e recebe no máximo uma escrita por clique em SALVAR COTAÇÕES.")
    else:
        st.warning("Planilhas Google não configuradas. Os dados ficam em cópia local e backups, mas a hospedagem pode apagar arquivos locais ao reiniciar.")

    with st.expander("Recuperação, importação e conferência do catálogo", expanded=False):
        st.info("Nenhuma operação desta seção apaga linhas. Registros são identificados por ID da coleta + mercado + seleção.")
        c_rec1, c_rec2 = st.columns(2)
        with c_rec1:
            if st.button("SINCRONIZAR AS 49 COTAÇÕES AUSENTES", key="restaurar_49_catalogo"):
                destino = restaurar_catalogo_recuperado()
                st.success(f"Recuperação concluída sem apagar linhas. Destino: {destino}.")
        with c_rec2:
            st.metric("Registros do pacote recuperado", len(CATALOGO_RECUPERACAO_2026))

        arquivo_importacao = st.file_uploader(
            "Importar outro catálogo CSV ou TXT",
            type=["csv", "txt", "tsv"],
            key="importar_catalogo_seguro",
            help="A importação é incremental e deduplicada. Nenhuma aba é limpa.",
        )
        if arquivo_importacao is not None:
            try:
                importado = importar_catalogo_arquivo(arquivo_importacao.getvalue(), arquivo_importacao.name)
                st.dataframe(importado.head(20), use_container_width=True, hide_index=True)
                if st.button("IMPORTAR SEM APAGAR", key="confirmar_importacao_catalogo"):
                    destino = salvar_catalogo(importado)
                    st.success(f"{len(importado)} linha(s) processada(s). Destino: {destino}.")
            except Exception as exc:
                st.error(f"Não consegui ler o arquivo de importação: {exc}")

    force_sync_catalogo = False
    if cfg.get("configurado"):
        force_sync_catalogo = st.button("🔄 Sincronizar catálogo do Google", key="sync_catalogo_tab")
        if _google_cooldown_ativo():
            st.info(f"Planilhas Google em espera por {_segundos_cooldown_google()}s; cópia local e backups continuam preservados.")

    catalogo = carregar_catalogo(force_google=force_sync_catalogo)
    if catalogo.empty:
        st.info("Ainda não há cotações salvas.")
    else:
        f1, f2, f3 = st.columns(3)
        with f1:
            filtro_casa = st.multiselect("Casa", sorted(catalogo["Casa de apostas"].dropna().unique().tolist()))
        with f2:
            filtro_liga = st.multiselect("Liga", sorted(catalogo["Liga"].dropna().unique().tolist()))
        with f3:
            busca = st.text_input("Buscar jogo/time", value="")
        filtrado = catalogo.copy()
        if filtro_casa:
            filtrado = filtrado[filtrado["Casa de apostas"].isin(filtro_casa)]
        if filtro_liga:
            filtrado = filtrado[filtrado["Liga"].isin(filtro_liga)]
        if busca.strip():
            termo = busca.strip().lower()
            filtrado = filtrado[
                filtrado["Jogo"].astype(str).str.lower().str.contains(termo, na=False)
                | filtrado["Mandante"].astype(str).str.lower().str.contains(termo, na=False)
                | filtrado["Visitante"].astype(str).str.lower().str.contains(termo, na=False)
            ]
        st.dataframe(remover_colunas_duplicadas(filtrado).tail(500), use_container_width=True, hide_index=True)
        csv = filtrado.to_csv(index=False).encode("utf-8-sig")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("BAIXAR CATÁLOGO EM CSV", data=csv, file_name="catalogo_cotacoes_tex_v20_3_3.csv", mime="text/csv")
        with d2:
            excel = dataframe_para_excel_bytes(filtrado, "Catálogo de cotações")
            if excel is not None:
                st.download_button(
                    "BAIXAR CATÁLOGO EXCEL",
                    data=excel,
                    file_name="catalogo_cotacoes_tex_v20_3_3.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.caption("A exportação em Excel não está disponível neste ambiente; o arquivo CSV continua completo.")


with aba_historico:
    st.subheader("Histórico de análises do motor")
    pendente = st.session_state.get("historico_analise_pendente")
    if isinstance(pendente, pd.DataFrame) and not pendente.empty:
        st.info("Existe uma análise concluída ainda não salva. Nenhuma gravação ocorre sem o botão abaixo.")
        if st.button("SALVAR ESTA ANÁLISE NO HISTÓRICO", key="salvar_historico_explicito"):
            destino_historico = salvar_historico_analises(pendente)
            st.success(f"Análise salva por ação explícita. Destino: {destino_historico}.")
            st.session_state.pop("historico_analise_pendente", None)
    cfg_hist = obter_config_google()
    if cfg_hist.get("configurado"):
        st.success(f"Planilhas Google ativas. Aba: {cfg_hist['worksheet_historico']}. Cada análise salva cotações, probabilidades e projeções.")
    else:
        st.warning("Planilhas Google não configuradas. O histórico fica apenas nas cópias locais e backups.")

    forcar_hist = False
    if cfg_hist.get("configurado"):
        forcar_hist = st.button("🔄 Sincronizar histórico do Google", key="sync_historico_tab")
    historico_modelo = carregar_historico_analises(force_google=forcar_hist)
    if historico_modelo.empty:
        st.info("Ainda não há análises registradas nesta versão.")
    else:
        h1, h2, h3 = st.columns(3)
        with h1:
            filtro_hist_liga = st.multiselect(
                "Liga do histórico",
                sorted(historico_modelo["Liga"].dropna().astype(str).unique().tolist()),
                key="filtro_hist_liga",
            )
        with h2:
            filtro_hist_mercado = st.multiselect(
                "Mercado do histórico",
                sorted(historico_modelo["Mercado"].dropna().astype(str).unique().tolist()),
                key="filtro_hist_mercado",
            )
        with h3:
            busca_hist = st.text_input("Buscar jogo no histórico", value="", key="busca_hist")
        hist_filtrado = historico_modelo.copy()
        if filtro_hist_liga:
            hist_filtrado = hist_filtrado[hist_filtrado["Liga"].isin(filtro_hist_liga)]
        if filtro_hist_mercado:
            hist_filtrado = hist_filtrado[hist_filtrado["Mercado"].isin(filtro_hist_mercado)]
        if busca_hist.strip():
            termo = busca_hist.strip().lower()
            hist_filtrado = hist_filtrado[
                hist_filtrado["Jogo"].astype(str).str.lower().str.contains(termo, na=False)
            ]
        st.dataframe(hist_filtrado.tail(1000), use_container_width=True, hide_index=True)
        csv_hist = hist_filtrado.to_csv(index=False).encode("utf-8-sig")
        h_d1, h_d2 = st.columns(2)
        with h_d1:
            st.download_button(
                "BAIXAR HISTÓRICO EM CSV",
                data=csv_hist,
                file_name="historico_analises_tex_v20_3_3.csv",
                mime="text/csv",
            )
        with h_d2:
            excel_hist = dataframe_para_excel_bytes(hist_filtrado, "Histórico de análises")
            if excel_hist is not None:
                st.download_button(
                    "BAIXAR HISTÓRICO EM EXCEL",
                    data=excel_hist,
                    file_name="historico_analises_tex_v20_3_3.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

with aba_auditoria:
    st.subheader("Auditoria")
    cfg = obter_config_google()
    if cfg.get("configurado"):
        st.success(f"Planilhas Google ativas. Aba: {cfg['worksheet_auditoria']}.")
    else:
        st.warning("Planilhas Google não configuradas. Use a cópia local com cuidado no serviço de hospedagem.")

    force_sync_auditoria_tab = False
    if cfg.get("configurado"):
        force_sync_auditoria_tab = st.button("🔄 Sincronizar auditoria do Google", key="sync_auditoria_tab")
        if _google_cooldown_ativo():
            st.info(f"Planilhas Google em espera por {_segundos_cooldown_google()}s; mostrando cópia temporária e cópia local.")

    auditoria = carregar_auditoria(force_google=force_sync_auditoria_tab)
    banca_calc = banca_atual(banca_inicial, auditoria)
    lucro = banca_calc - float(banca_inicial)
    c1, c2, c3 = st.columns(3)
    c1.metric("Banca inicial", fmt_dinheiro(banca_inicial))
    c2.metric("Banca auditada", fmt_dinheiro(banca_calc))
    c3.metric("Resultado total", fmt_dinheiro(lucro))

    resumo_adv = resumo_auditoria_avancado(auditoria)
    if resumo_adv:
        st.markdown("---")
        st.markdown("### Auditoria inteligente")
        geral_fmt = resumo_adv["geral"].copy()
        for col in ["Apostado", "Resultado"]:
            geral_fmt[col] = geral_fmt[col].map(fmt_dinheiro)
        for col in ["Taxa acerto", "ROI"]:
            geral_fmt[col] = geral_fmt[col].map(lambda x: fmt_pct(x, 2))
        st.dataframe(geral_fmt.rename(columns={"ROI": "Retorno sobre o valor apostado"}), use_container_width=True, hide_index=True)

        a1, a2, a3, a4 = st.tabs(["Por mercado", "Por liga", "Por faixa de cotação", "Por etiqueta operacional"])
        for aba_tmp, chave in [(a1, "por_mercado"), (a2, "por_liga"), (a3, "por_faixa_odd"), (a4, "por_etiqueta")]:
            with aba_tmp:
                t = resumo_adv[chave].copy()
                for col in ["Apostado", "Resultado"]:
                    t[col] = t[col].map(fmt_dinheiro)
                for col in ["Taxa acerto", "ROI"]:
                    t[col] = t[col].map(lambda x: fmt_pct(x, 2))
                st.dataframe(t.rename(columns={"ROI": "Retorno sobre o valor apostado"}), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Lançar entrada manual")
    with st.expander("Adicionar entrada feita fora do motor"):
        c1, c2 = st.columns(2)
        with c1:
            aud_liga = st.text_input("Liga", value=liga_sel, key="aud_liga")
            aud_jogo = st.text_input("Jogo", value="", placeholder="Ex: Bournemouth x Man City", key="aud_jogo")
            aud_mercado = st.selectbox("Mercado", MERCADOS_NUCLEO, key="aud_mercado")
            aud_casa = st.selectbox("Casa", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"], key="aud_casa")
        with c2:
            aud_odd = st.text_input("Cotação", value="", key="aud_odd")
            aud_entrada = st.text_input("Entrada em reais", value="", key="aud_entrada")
            aud_banca = st.number_input("Banca antes", min_value=0.0, value=float(banca_calc), step=10.0, key="aud_banca")
            aud_obs = st.text_input("Observação", value="", key="aud_obs")
        if st.button("SALVAR ENTRADA MANUAL"):
            odd = texto_para_float(aud_odd)
            entrada = texto_para_float(aud_entrada)
            if not odd_valida(odd) or entrada is None or entrada <= 0 or not aud_jogo.strip():
                st.error("Preencha jogo, cotação válida e entrada.")
            else:
                percentual = float(entrada) / float(aud_banca) if aud_banca > 0 else 0.0
                auditoria = registrar_entrada(
                    auditoria, aud_liga, aud_jogo, aud_casa, aud_mercado,
                    float(odd), 0.0, 0.0, 0.0, percentual, float(entrada), float(aud_banca),
                    "Manual livre", aud_obs,
                )
                destino = salvar_auditoria(auditoria)
                st.success(f"Entrada salva. Destino: {destino}.")

    st.markdown("---")
    st.markdown("### Fechar resultado")
    auditoria = carregar_auditoria()
    if auditoria.empty:
        st.info("Ainda não há entradas.")
    else:
        pendentes = auditoria[auditoria["Status"].astype(str).eq("Pendente")].copy()
        if pendentes.empty:
            st.info("Não há entradas pendentes.")
        else:
            labels = []
            mapa = {}
            for idx, row in pendentes.iterrows():
                label = f"{row['ID']} — {row['Jogo']} — {row['Mercado']} — entrada {fmt_dinheiro_texto(texto_para_float(row['Entrada R$']) or 0)}"
                labels.append(label)
                mapa[label] = idx
            escolha = st.selectbox("Entrada", labels)
            idx = mapa[escolha]
            row = auditoria.loc[idx]
            c1, c2, c3 = st.columns(3)
            with c1:
                status = st.selectbox("Resultado", ["Vitória", "Derrota", "Anulada", "Encerramento antecipado"], key="status_fechar")
            with c2:
                odd_fechamento_txt = st.text_input("Cotação de fechamento", value="", key="odd_fechamento")
            with c3:
                cashout = st.number_input("Valor recebido no encerramento antecipado", min_value=0.0, value=0.0, step=1.0, key="cashout")
            diagnostico_pos = st.selectbox(
                "Diagnóstico pós-jogo",
                ["Não classificado", "Variância provável", "Erro de modelo", "Erro de execução", "Evento extraordinário", "Dados desatualizados", "Inconclusivo"],
                key="diagnostico_pos_jogo",
            )
            obs_fechamento = st.text_input("Observação fechamento", value="", key="obs_fechamento")
            if st.button("FECHAR ENTRADA"):
                entrada_rs = float(texto_para_float(row["Entrada R$"]) or 0.0)
                odd_entrada = float(texto_para_float(row["Cotação de entrada"]) or 0.0)
                resultado_rs = calcular_resultado(status, entrada_rs, odd_entrada, cashout)
                odd_fechamento = texto_para_float(odd_fechamento_txt)
                vantagem = ""
                if odd_valida(odd_fechamento) and odd_entrada > 0:
                    vantagem = round(((odd_entrada / float(odd_fechamento)) - 1.0) * 100.0, 2)
                banca_depois = float(texto_para_float(row["Banca antes"]) or 0.0) + resultado_rs
                auditoria.loc[idx, "Status"] = status
                auditoria.loc[idx, "Resultado R$"] = round(resultado_rs, 2)
                auditoria.loc[idx, "Banca depois"] = round(banca_depois, 2)
                auditoria.loc[idx, "Cotação de fechamento"] = odd_fechamento if odd_fechamento is not None else ""
                auditoria.loc[idx, "Vantagem no fechamento %"] = vantagem
                auditoria.loc[idx, "Diagnóstico pós-jogo"] = "" if diagnostico_pos == "Não classificado" else diagnostico_pos
                auditoria.loc[idx, "Observação"] = str(row.get("Observação", "")) + " | Fechamento: " + obs_fechamento
                destino = salvar_auditoria(auditoria)
                st.success(f"Entrada fechada. Destino: {destino}.")

    st.markdown("---")
    st.markdown("### Histórico")
    auditoria = carregar_auditoria()
    if auditoria.empty:
        st.info("Nenhum registro ainda.")
    else:
        auditoria_exibicao = remover_colunas_duplicadas(auditoria).tail(500).copy()
        if "Status" in auditoria_exibicao.columns:
            auditoria_exibicao["Status"] = auditoria_exibicao["Status"].replace({
                "Green": "Vitória", "Red": "Derrota", "Void": "Anulada", "Cashout": "Encerramento antecipado"
            })
            auditoria_exibicao = auditoria_exibicao.rename(columns={"Status": "Situação"})
        st.dataframe(auditoria_exibicao, use_container_width=True, hide_index=True)
        csv = auditoria.to_csv(index=False).encode("utf-8-sig")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("BAIXAR AUDITORIA EM CSV", data=csv, file_name="auditoria_tex_v20_3_3.csv", mime="text/csv")
        with d2:
            excel = dataframe_para_excel_bytes(auditoria, "Auditoria")
            if excel is not None:
                st.download_button(
                    "BAIXAR AUDITORIA EXCEL",
                    data=excel,
                    file_name="auditoria_tex_v20_3_3.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.caption("A exportação em Excel não está disponível neste ambiente; o arquivo CSV continua completo.")

with aba_calendario:
    st.subheader("Ligas cobertas")
    st.caption("A trava operacional mais importante é usar exatamente a liga correspondente à base do aplicativo.")
    mapa = pd.DataFrame(CALENDARIO_LIGAS)
    st.dataframe(mapa, use_container_width=True, hide_index=True)
    st.markdown(
        """
        **Regra prática:** se a casa de apostas mostrar uma competição parecida, mas não igual, não force.
        Exemplo: Allsvenskan não é Ettan; Veikkausliiga não é Ykkönen; MLS não é MLS Next Pro.
        """
    )
