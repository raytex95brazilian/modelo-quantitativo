import os
import io
import json
import uuid
import math
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson


# ============================================================
# TEX STATISTICS PRO V18 — REWRITE TOTAL
# Núcleo novo: primeiro bloqueia risco, depois calcula valor.
# Foco: não deixar Under/BTTS Não passarem em jogo com fogo/goleada.
# ============================================================

st.set_page_config(page_title="TEX STATISTICS — V18 Anti-Goleada", layout="wide")


# ============================================================
# VISUAL
# ============================================================

st.markdown(
    """
    <style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@600;700&display=swap");

    :root {
        color-scheme: light !important;
        --bg: #f6f7fb;
        --card: #ffffff;
        --text: #111827;
        --muted: #64748b;
        --line: #e5e7eb;
        --green: #059669;
        --yellow: #d97706;
        --blue: #2563eb;
        --red: #dc2626;
        --black: #0f172a;
        --soft-green: #ecfdf5;
        --soft-red: #fef2f2;
        --soft-blue: #eff6ff;
        --soft-yellow: #fffbeb;
        --shadow: 0 10px 28px rgba(15,23,42,.08);
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }

    .block-container { max-width: 1180px; padding-top: 1rem; }

    .block-container *, [data-testid="stSidebar"] * {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background: #ffffff !important;
        border-right: 1px solid var(--line);
    }

    .mini, .muted, [data-testid="stCaptionContainer"], .stCaption, small {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
    }

    input, textarea, [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div {
        background: #ffffff !important;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        border-color: #cbd5e1 !important;
        border-radius: 12px !important;
    }

    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"],
    [data-baseweb="popover"] *, [data-baseweb="menu"] *, [role="listbox"] * {
        background: #ffffff !important;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    .hero {
        background: #ffffff;
        border: 1px solid var(--line);
        border-left: 8px solid var(--black);
        border-radius: 22px;
        box-shadow: var(--shadow);
        padding: 22px;
        margin-bottom: 14px;
    }

    .hero-title {
        font-family: "Space Grotesk", "Inter", sans-serif;
        font-size: 2.0rem;
        font-weight: 800;
        letter-spacing: -0.6px;
        margin-bottom: 6px;
    }

    .hero-sub { color: var(--muted) !important; line-height: 1.55; font-weight: 500; }

    .chip {
        display: inline-block;
        padding: 7px 10px;
        border-radius: 999px;
        border: 1px solid #d1d5db;
        background: #f8fafc;
        font-size: .78rem;
        font-weight: 800;
        margin: 8px 6px 0 0;
    }

    .decision-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px 18px;
        margin: 12px 0;
        box-shadow: var(--shadow);
    }

    .decision-green { border-left: 8px solid var(--green); }
    .decision-yellow { border-left: 8px solid var(--yellow); }
    .decision-blue { border-left: 8px solid var(--blue); }
    .decision-red { border-left: 8px solid var(--red); }

    .big-ok { color: var(--green) !important; -webkit-text-fill-color: var(--green) !important; font-weight: 900; }
    .big-warn { color: var(--yellow) !important; -webkit-text-fill-color: var(--yellow) !important; font-weight: 900; }
    .big-blue { color: var(--blue) !important; -webkit-text-fill-color: var(--blue) !important; font-weight: 900; }
    .big-bad { color: var(--red) !important; -webkit-text-fill-color: var(--red) !important; font-weight: 900; }

    .market-title { font-size: 1.18rem; font-weight: 900; margin: 6px 0 8px 0; }
    .line { line-height: 1.65; font-size: .95rem; }
    .explain { color: var(--muted) !important; font-size: .9rem; line-height: 1.55; }

    .risk-box {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 14px;
        box-shadow: 0 6px 20px rgba(15,23,42,.05);
        margin: 8px 0 12px;
    }

    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        background: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        font-weight: 850 !important;
        box-shadow: none !important;
    }

    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
    }

    @media (max-width: 768px) {
        .hero-title { font-size: 1.45rem; }
        .block-container { padding-left: .8rem; padding-right: .8rem; }
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

MERCADOS = [
    "Vitória Casa",
    "Empate",
    "Vitória Fora",
    "Mais de 2.5 gols",
    "Menos de 2.5 gols",
    "Ambos marcam - Sim",
    "Ambos marcam - Não",
    "Casa ou Empate",
    "Fora ou Empate",
    "Empate Anula Casa",
    "Empate Anula Fora",
]

MERCADOS_NUCLEO = {
    "Vitória Casa",
    "Empate",
    "Vitória Fora",
    "Mais de 2.5 gols",
    "Menos de 2.5 gols",
    "Ambos marcam - Sim",
    "Ambos marcam - Não",
}

MERCADOS_RESULTADO = {"Vitória Casa", "Empate", "Vitória Fora"}
MERCADOS_GOLS_BAIXOS = {"Menos de 2.5 gols", "Ambos marcam - Não"}
MERCADOS_GOLS_ALTOS = {"Mais de 2.5 gols", "Ambos marcam - Sim"}

ARQUIVO_AUDITORIA = "logs/auditoria_tex_v18.csv"
ARQUIVO_CATALOGO = "logs/catalogo_odds_tex_v18.csv"

COLUNAS_AUDITORIA = [
    "ID", "Registrado em", "Data do jogo", "Liga", "Jogo", "Casa de apostas",
    "Mercado", "Seleção", "Cotação de entrada", "Cotação justa",
    "Chance pelo sistema %", "Valor esperado %", "Entrada %", "Entrada R$",
    "Banca antes", "Status", "Resultado R$", "Banca depois",
    "Cotação de fechamento", "Vantagem no fechamento %", "Origem", "Observação",
]

COLUNAS_CATALOGO = [
    "ID Coleta", "Registrado em", "Data do jogo", "Hora do jogo", "Casa de apostas",
    "Liga", "Jogo", "Mandante", "Visitante", "Mercado", "Seleção", "Cotação",
    "Banca no momento", "Perfil", "Origem", "Observação",
]

CALENDARIO_LIGAS = [
    {"Liga": "Brasileirão Série A", "Jan": "fora/consultar", "Fev": "fora/consultar", "Mar": "início", "Abr": "jogos", "Mai": "jogos", "Jun": "pausa/consultar", "Jul": "retoma/consultar", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "encerra/consultar"},
    {"Liga": "Argentina - Primera Division", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "jogos", "Jun": "consultar", "Jul": "consultar", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "encerra/consultar"},
    {"Liga": "EUA - MLS", "Jan": "fora", "Fev": "início", "Mar": "jogos", "Abr": "jogos", "Mai": "jogos", "Jun": "consultar", "Jul": "consultar", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "playoffs", "Dez": "playoffs/consultar"},
    {"Liga": "México - Liga MX", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "fase final", "Jun": "pausa", "Jul": "início", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "fase final", "Dez": "fase final/pausa"},
    {"Liga": "Japão - J1 League", "Jan": "fora", "Fev": "início", "Mar": "jogos", "Abr": "jogos", "Mai": "jogos", "Jun": "consultar", "Jul": "jogos", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "encerra"},
    {"Liga": "Suécia - Allsvenskan", "Jan": "fora", "Fev": "fora", "Mar": "fora/início", "Abr": "jogos", "Mai": "jogos", "Jun": "jogos", "Jul": "jogos", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "encerra", "Dez": "fora"},
    {"Liga": "Noruega - Eliteserien", "Jan": "fora", "Fev": "fora", "Mar": "início", "Abr": "jogos", "Mai": "jogos", "Jun": "jogos", "Jul": "jogos", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "encerra", "Dez": "fora"},
    {"Liga": "Finlândia - Veikkausliiga", "Jan": "fora", "Fev": "fora", "Mar": "fora", "Abr": "início", "Mai": "jogos", "Jun": "jogos", "Jul": "jogos", "Ago": "jogos", "Set": "fase final", "Out": "fase final", "Nov": "fora", "Dez": "fora"},
    {"Liga": "Irlanda - Premier Division", "Jan": "fora", "Fev": "início", "Mar": "jogos", "Abr": "jogos", "Mai": "jogos", "Jun": "jogos", "Jul": "jogos", "Ago": "jogos", "Set": "jogos", "Out": "encerra", "Nov": "fora", "Dez": "fora"},
    {"Liga": "Inglaterra - Premier League", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "encerra", "Jun": "fora", "Jul": "fora", "Ago": "início", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos"},
    {"Liga": "Espanha - La Liga", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "encerra", "Jun": "fora", "Jul": "fora", "Ago": "início", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos"},
    {"Liga": "Itália - Série A", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "encerra", "Jun": "fora", "Jul": "fora", "Ago": "início", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos"},
    {"Liga": "Alemanha - Bundesliga", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "encerra", "Jun": "fora", "Jul": "fora", "Ago": "início", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos"},
    {"Liga": "França - Ligue 1", "Jan": "jogos", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "encerra", "Jun": "fora", "Jul": "fora", "Ago": "início", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos"},
]


# ============================================================
# UTILITÁRIOS
# ============================================================

def dinheiro(valor: float) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def numero(valor: float, casas: int = 2) -> str:
    try:
        return f"{float(valor):.{casas}f}".replace(".", ",")
    except Exception:
        return "0,00"


def porcentagem(valor: float, casas: int = 1) -> str:
    try:
        return f"{float(valor) * 100:.{casas}f}%".replace(".", ",")
    except Exception:
        return "0,0%"


def texto_para_float(valor: Any) -> Optional[float]:
    if valor is None:
        return None
    txt = str(valor).strip().replace("R$", "").replace(" ", "")
    if not txt:
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


def odd_valida(odd: Optional[float]) -> bool:
    return odd is not None and np.isfinite(float(odd)) and float(odd) > 1.01


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if b == 0 or not np.isfinite(b):
            return default
        return float(a) / float(b)
    except Exception:
        return default


def media(serie: pd.Series, default: float = 0.0) -> float:
    try:
        s = pd.to_numeric(serie, errors="coerce").dropna()
        if len(s) == 0:
            return float(default)
        return float(s.mean())
    except Exception:
        return float(default)


def taxa(condicao: pd.Series) -> float:
    try:
        if len(condicao) == 0:
            return 0.0
        return float(pd.Series(condicao).astype(bool).mean())
    except Exception:
        return 0.0


def clamp(x: float, a: float, b: float) -> float:
    try:
        return float(np.clip(float(x), float(a), float(b)))
    except Exception:
        return float(a)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def garantir_logs() -> None:
    os.makedirs("logs", exist_ok=True)


# ============================================================
# DADOS
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def carregar_base(url: str, janela: int) -> pd.DataFrame:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df = df.rename(columns={"HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG"})
        if not all(c in df.columns for c in ["Home", "Away", "HG", "AG"]):
            return pd.DataFrame()
        df = df.dropna(subset=["Home", "Away", "HG", "AG"]).copy()
        df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
        df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
        df = df.dropna(subset=["HG", "AG"]).copy()
        if "Date" in df.columns:
            df["DataTemp"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.sort_values(["DataTemp"], kind="mergesort")
        df = df.reset_index(drop=True)
        df["JogoID"] = np.arange(len(df))
        janela = int(np.clip(int(janela), 80, 1500))
        return df.tail(janela).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def jogos_do_time(df: pd.DataFrame, time: str, mando: str = "geral") -> pd.DataFrame:
    if mando == "casa":
        out = df[df["Home"] == time].copy()
        out["GF"] = out["HG"]
        out["GA"] = out["AG"]
        out["Local"] = "Casa"
    elif mando == "fora":
        out = df[df["Away"] == time].copy()
        out["GF"] = out["AG"]
        out["GA"] = out["HG"]
        out["Local"] = "Fora"
    else:
        casa = df[df["Home"] == time].copy()
        casa["GF"] = casa["HG"]
        casa["GA"] = casa["AG"]
        casa["Local"] = "Casa"
        fora = df[df["Away"] == time].copy()
        fora["GF"] = fora["AG"]
        fora["GA"] = fora["HG"]
        fora["Local"] = "Fora"
        out = pd.concat([casa, fora], ignore_index=True)
    if out.empty:
        return out
    if "DataTemp" in out.columns:
        out = out.sort_values(["DataTemp", "JogoID"], kind="mergesort")
    else:
        out = out.sort_values("JogoID", kind="mergesort")
    return out.reset_index(drop=True)


def perfil_time(jogos: pd.DataFrame, n: int = 10) -> Dict[str, float]:
    base = jogos.tail(n).copy()
    if base.empty:
        return {
            "jogos": 0, "gf_med": 0.0, "ga_med": 0.0, "total_med": 0.0,
            "over25": 0.0, "btts": 0.0,
            "marcou": 0.0, "zerou": 0.0, "clean": 0.0,
            "fez2": 0.0, "fez3": 0.0, "sofreu2": 0.0, "sofreu3": 0.0,
            "saldo_med": 0.0,
        }
    gf = pd.to_numeric(base["GF"], errors="coerce").fillna(0)
    ga = pd.to_numeric(base["GA"], errors="coerce").fillna(0)
    total = gf + ga
    return {
        "jogos": int(len(base)),
        "gf_med": float(gf.mean()),
        "ga_med": float(ga.mean()),
        "total_med": float(total.mean()),
        "over25": taxa(total >= 3),
        "btts": taxa((gf >= 1) & (ga >= 1)),
        "marcou": taxa(gf >= 1),
        "zerou": taxa(gf == 0),
        "clean": taxa(ga == 0),
        "fez2": taxa(gf >= 2),
        "fez3": taxa(gf >= 3),
        "sofreu2": taxa(ga >= 2),
        "sofreu3": taxa(ga >= 3),
        "saldo_med": float((gf - ga).mean()),
    }


def metricas_liga(df: pd.DataFrame) -> Dict[str, float]:
    hg = pd.to_numeric(df["HG"], errors="coerce").fillna(0)
    ag = pd.to_numeric(df["AG"], errors="coerce").fillna(0)
    total = hg + ag
    return {
        "home_avg": max(0.20, float(hg.mean())),
        "away_avg": max(0.20, float(ag.mean())),
        "total_avg": max(0.40, float(total.mean())),
        "over25": taxa(total >= 3),
        "btts": taxa((hg >= 1) & (ag >= 1)),
    }


def calcular_contexto(df: pd.DataFrame, time_casa: str, time_fora: str) -> Dict[str, Any]:
    liga = metricas_liga(df)

    casa_home = jogos_do_time(df, time_casa, "casa")
    fora_away = jogos_do_time(df, time_fora, "fora")
    casa_all = jogos_do_time(df, time_casa, "geral")
    fora_all = jogos_do_time(df, time_fora, "geral")

    ph5 = perfil_time(casa_all, 5)
    pa5 = perfil_time(fora_all, 5)
    ph10 = perfil_time(casa_all, 10)
    pa10 = perfil_time(fora_all, 10)
    ph_mando = perfil_time(casa_home, 10)
    pa_mando = perfil_time(fora_away, 10)

    gf_home = media(casa_home["HG"], liga["home_avg"])
    ga_home = media(casa_home["AG"], liga["away_avg"])
    gf_away = media(fora_away["AG"], liga["away_avg"])
    ga_away = media(fora_away["HG"], liga["home_avg"])

    atk_home = safe_div(gf_home, liga["home_avg"], 1.0)
    def_home = safe_div(ga_home, liga["away_avg"], 1.0)
    atk_away = safe_div(gf_away, liga["away_avg"], 1.0)
    def_away = safe_div(ga_away, liga["home_avg"], 1.0)

    exp_home_base = liga["home_avg"] * atk_home * def_away
    exp_away_base = liga["away_avg"] * atk_away * def_home

    # Recorte recente cruzado: ataque recente do time + defesa recente do adversário
    # Sem inventar milagre: se tem pouca amostra, o peso recente cai.
    amostra_min = min(len(casa_home), len(fora_away))
    confianca_amostra = clamp(amostra_min / 8.0, 0.25, 1.0)

    rec_home = 0.42 * ph5["gf_med"] + 0.28 * ph_mando["gf_med"] + 0.30 * pa_mando["ga_med"]
    rec_away = 0.42 * pa5["gf_med"] + 0.28 * pa_mando["gf_med"] + 0.30 * ph_mando["ga_med"]

    peso_recente = 0.42 * confianca_amostra
    exp_home = (1.0 - peso_recente) * exp_home_base + peso_recente * rec_home
    exp_away = (1.0 - peso_recente) * exp_away_base + peso_recente * rec_away

    exp_home = clamp(exp_home, 0.05, 5.50)
    exp_away = clamp(exp_away, 0.05, 5.50)

    total = exp_home + exp_away
    maior = max(exp_home, exp_away)
    menor = min(exp_home, exp_away)

    # Índices simples, transparentes e auditáveis.
    fogo_casa = (
        0.28 * ph5["fez2"] +
        0.18 * ph5["fez3"] +
        0.20 * pa_mando["sofreu2"] +
        0.14 * pa_mando["sofreu3"] +
        0.20 * clamp(exp_home / 2.20, 0, 1)
    )
    fogo_fora = (
        0.28 * pa5["fez2"] +
        0.18 * pa5["fez3"] +
        0.20 * ph_mando["sofreu2"] +
        0.14 * ph_mando["sofreu3"] +
        0.20 * clamp(exp_away / 2.20, 0, 1)
    )

    fogo_jogo = clamp(
        0.30 * clamp(total / 3.20, 0, 1)
        + 0.20 * ((ph5["over25"] + pa5["over25"]) / 2)
        + 0.15 * ((ph10["over25"] + pa10["over25"]) / 2)
        + 0.20 * max(fogo_casa, fogo_fora)
        + 0.15 * liga["over25"],
        0,
        1,
    )

    risco_goleada = clamp(
        0.33 * clamp(maior / 2.35, 0, 1)
        + 0.17 * clamp((maior - menor) / 1.55, 0, 1)
        + 0.18 * max(ph5["fez3"], pa5["fez3"])
        + 0.17 * max(ph_mando["fez2"], pa_mando["fez2"])
        + 0.15 * max(pa_mando["sofreu3"], ph_mando["sofreu3"]),
        0,
        1,
    )

    under_perigo = clamp(
        0.28 * clamp((total - 2.05) / 1.15, 0, 1)
        + 0.25 * fogo_jogo
        + 0.24 * risco_goleada
        + 0.13 * max(fogo_casa, fogo_fora)
        + 0.10 * max(pa_mando["sofreu2"], ph_mando["sofreu2"]),
        0,
        1,
    )

    return {
        "liga": liga,
        "amostra_casa_home": int(len(casa_home)),
        "amostra_fora_away": int(len(fora_away)),
        "amostra_min": int(amostra_min),
        "confianca_amostra": float(confianca_amostra),
        "gols_casa": float(exp_home),
        "gols_fora": float(exp_away),
        "total_gols": float(total),
        "maior_gols": float(maior),
        "menor_gols": float(menor),
        "casa_5": ph5,
        "fora_5": pa5,
        "casa_10": ph10,
        "fora_10": pa10,
        "casa_mando": ph_mando,
        "fora_mando": pa_mando,
        "fogo_casa": float(fogo_casa),
        "fogo_fora": float(fogo_fora),
        "fogo_jogo": float(fogo_jogo),
        "risco_goleada": float(risco_goleada),
        "under_perigo": float(under_perigo),
    }


def matriz_poisson(exp_home: float, exp_away: float, tamanho: int = 15) -> np.ndarray:
    matriz = np.zeros((tamanho, tamanho), dtype=float)
    for h in range(tamanho):
        ph = poisson.pmf(h, exp_home)
        for a in range(tamanho):
            matriz[h, a] = ph * poisson.pmf(a, exp_away)
    soma = matriz.sum()
    if soma > 0:
        matriz = matriz / soma
    return matriz


def calcular_probabilidades(contexto: Dict[str, Any]) -> Dict[str, float]:
    gh = float(contexto["gols_casa"])
    ga = float(contexto["gols_fora"])
    m = matriz_poisson(gh, ga, tamanho=15)
    idx = np.arange(m.shape[0])
    total_grid = np.add.outer(idx, idx)

    p_home = float(np.tril(m, -1).sum())
    p_draw = float(np.diag(m).sum())
    p_away = float(np.triu(m, 1).sum())
    p_over = float(m[total_grid >= 3].sum())
    p_under = float(m[total_grid <= 2].sum())
    p_btts = float(m[1:, 1:].sum())
    p_btts_no = max(0.0, 1.0 - p_btts)

    total_sem_empate = p_home + p_away
    return {
        "Vitória Casa": p_home,
        "Empate": p_draw,
        "Vitória Fora": p_away,
        "Casa ou Empate": p_home + p_draw,
        "Fora ou Empate": p_away + p_draw,
        "Empate Anula Casa": safe_div(p_home, total_sem_empate, 0.0),
        "Empate Anula Fora": safe_div(p_away, total_sem_empate, 0.0),
        "Mais de 2.5 gols": p_over,
        "Menos de 2.5 gols": p_under,
        "Ambos marcam - Sim": p_btts,
        "Ambos marcam - Não": p_btts_no,
    }


# ============================================================
# ODDS
# ============================================================

def input_odd(label: str, key: str) -> Optional[float]:
    txt = st.text_input(label, value="", placeholder="ex: 1,85", key=key)
    x = texto_para_float(txt)
    return x if odd_valida(x) else None


def coletar_odds_manuais(prefixo: str) -> Dict[str, float]:
    odds: Dict[str, float] = {}

    st.markdown("### Cotações")
    st.caption("Preencha só os mercados que você quer analisar. Campo vazio fica fora.")

    st.markdown("**Resultado seco**")
    c1, c2, c3 = st.columns(3)
    with c1:
        odds["Vitória Casa"] = input_odd("Vitória Casa", f"{prefixo}_vc")
    with c2:
        odds["Empate"] = input_odd("Empate", f"{prefixo}_emp")
    with c3:
        odds["Vitória Fora"] = input_odd("Vitória Fora", f"{prefixo}_vf")

    st.markdown("**Gols**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Mais de 2.5 gols"] = input_odd("Mais de 2.5 gols", f"{prefixo}_over")
    with c2:
        odds["Menos de 2.5 gols"] = input_odd("Menos de 2.5 gols", f"{prefixo}_under")

    st.markdown("**Ambos marcam**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Ambos marcam - Sim"] = input_odd("Ambos marcam - Sim", f"{prefixo}_btts_s")
    with c2:
        odds["Ambos marcam - Não"] = input_odd("Ambos marcam - Não", f"{prefixo}_btts_n")

    st.markdown("**Proteções — só auditoria/manual, não recomendação automática**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Casa ou Empate"] = input_odd("Casa ou Empate", f"{prefixo}_dc_c")
        odds["Empate Anula Casa"] = input_odd("Empate Anula Casa", f"{prefixo}_dnb_c")
    with c2:
        odds["Fora ou Empate"] = input_odd("Fora ou Empate", f"{prefixo}_dc_f")
        odds["Empate Anula Fora"] = input_odd("Empate Anula Fora", f"{prefixo}_dnb_f")

    return {k: float(v) for k, v in odds.items() if odd_valida(v)}


@st.cache_data(ttl=300, show_spinner=False)
def buscar_odds_api(chave: str, liga_api: str) -> Optional[List[dict]]:
    if not chave or not liga_api:
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


def mediana_odds(vals: List[float]) -> Optional[float]:
    limpos = [float(v) for v in vals if odd_valida(v)]
    if not limpos:
        return None
    return float(np.median(limpos))


def extrair_odds_api(jogo: dict) -> Dict[str, float]:
    pools = {
        "Vitória Casa": [],
        "Empate": [],
        "Vitória Fora": [],
        "Mais de 2.5 gols": [],
        "Menos de 2.5 gols": [],
        "Ambos marcam - Sim": [],
        "Ambos marcam - Não": [],
    }
    casa = jogo.get("home_team")
    fora = jogo.get("away_team")

    for book in jogo.get("bookmakers", []):
        for market in book.get("markets", []):
            key = market.get("key")
            for out in market.get("outcomes", []):
                nome = out.get("name")
                odd = texto_para_float(out.get("price"))
                if not odd_valida(odd):
                    continue
                if key == "h2h":
                    if nome == casa:
                        pools["Vitória Casa"].append(float(odd))
                    elif nome == "Draw":
                        pools["Empate"].append(float(odd))
                    elif nome == fora:
                        pools["Vitória Fora"].append(float(odd))
                elif key == "totals":
                    try:
                        point = float(out.get("point", 0))
                    except Exception:
                        point = 0
                    if abs(point - 2.5) < 0.001:
                        if nome == "Over":
                            pools["Mais de 2.5 gols"].append(float(odd))
                        elif nome == "Under":
                            pools["Menos de 2.5 gols"].append(float(odd))
                elif key == "btts":
                    if nome == "Yes":
                        pools["Ambos marcam - Sim"].append(float(odd))
                    elif nome == "No":
                        pools["Ambos marcam - Não"].append(float(odd))

    out: Dict[str, float] = {}
    for mercado, vals in pools.items():
        m = mediana_odds(vals)
        if m is not None:
            out[mercado] = m
    return out


def normalizar_nome_time(nome: str) -> str:
    s = str(nome or "").lower()
    for token in [" fc", " afc", " cf", " ec", " ac", ".", "-", "_"]:
        s = s.replace(token, " ")
    return " ".join(s.split()).strip()


def casar_time_api(nome_api: str, times_csv: List[str]) -> Optional[str]:
    # NUNCA retorna o primeiro time da lista por chute.
    import difflib
    alvo = normalizar_nome_time(nome_api)
    mapa = {normalizar_nome_time(t): t for t in times_csv}
    if alvo in mapa:
        return mapa[alvo]
    candidatos = list(mapa.keys())
    achados = difflib.get_close_matches(alvo, candidatos, n=1, cutoff=0.73)
    if not achados:
        return None
    return mapa[achados[0]]


# ============================================================
# DECISÃO
# ============================================================

def prob_implicita(odd: float) -> float:
    return 1.0 / float(odd) if odd_valida(odd) else 0.0


def probs_mercado_1x2(odds: Dict[str, float]) -> Dict[str, float]:
    brutas = {m: prob_implicita(odds[m]) for m in MERCADOS_RESULTADO if odd_valida(odds.get(m))}
    soma = sum(brutas.values())
    if soma <= 0:
        return {}
    return {m: v / soma for m, v in brutas.items()}


def menor_odd_resultado(odds: Dict[str, float]) -> Optional[float]:
    vals = [float(odds[m]) for m in MERCADOS_RESULTADO if odd_valida(odds.get(m))]
    return min(vals) if vals else None


def stake_quarto_kelly(prob: float, odd: float) -> float:
    try:
        if not odd_valida(odd) or prob <= 0:
            return 0.0
        ev = prob * odd - 1.0
        if ev <= 0:
            return 0.0
        kelly = ev / (odd - 1.0)
        return clamp(kelly / 4.0, 0.0, 0.05)
    except Exception:
        return 0.0


def hard_blocks(mercado: str, prob: float, odd: float, odds: Dict[str, float], contexto: Dict[str, Any]) -> List[str]:
    motivos: List[str] = []
    total = contexto["total_gols"]
    maior = contexto["maior_gols"]
    menor = contexto["menor_gols"]
    fogo = contexto["fogo_jogo"]
    goleada = contexto["risco_goleada"]
    under_perigo = contexto["under_perigo"]
    liga = contexto["liga"]
    ph5 = contexto["casa_5"]
    pa5 = contexto["fora_5"]
    phm = contexto["casa_mando"]
    pam = contexto["fora_mando"]
    amostra_min = contexto["amostra_min"]

    if amostra_min < 5:
        motivos.append("amostra casa/fora abaixo de 5 jogos; não usar dinheiro real")

    if mercado not in MERCADOS_NUCLEO:
        motivos.append("fora do núcleo automático da planilha; use apenas para auditoria manual")

    # Resultado seco: corta discordância absurda com mercado.
    if mercado in {"Vitória Casa", "Vitória Fora"}:
        if odd >= 6.00:
            motivos.append("odd seca muito alta; mercado pode estar vendo informação que a base não vê")
        probs_mkt = probs_mercado_1x2(odds)
        pm = probs_mkt.get(mercado)
        if pm is not None and odd >= 3.50 and (prob - pm) >= 0.15:
            motivos.append("modelo discordou demais do mercado em odd alta")
        menor_odd = menor_odd_resultado(odds)
        if menor_odd is not None and menor_odd <= 1.35 and odd >= 4.50:
            motivos.append("existe favorito fortíssimo no mercado contra essa vitória seca")

    if mercado == "Empate":
        if odd >= 4.40:
            motivos.append("empate em odd alta é variância pesada demais")
        if prob < 0.265:
            motivos.append("probabilidade de empate baixa para entrada automática")
        menor_odd = menor_odd_resultado(odds)
        if menor_odd is not None and menor_odd <= 1.48:
            motivos.append("favorito forte no 1x2 reduz qualidade do empate")

    # O coração da V18: Under só entra se o jogo for realmente frio.
    if mercado == "Menos de 2.5 gols":
        odd_over = odds.get("Mais de 2.5 gols")

        if total >= 2.38:
            motivos.append("Under bloqueado: total esperado acima do limite conservador")
        if maior >= 1.62:
            motivos.append("Under bloqueado: um lado tem capacidade de marcar 2 ou 3 gols")
        if fogo >= 0.48:
            motivos.append("Under bloqueado: índice de fogo do jogo alto")
        if goleada >= 0.45:
            motivos.append("Under bloqueado: risco de goleada unilateral alto")
        if under_perigo >= 0.44:
            motivos.append("Under bloqueado: combinação de forma recente + goleada + total esperado é perigosa")
        if liga["over25"] >= 0.58 and total >= 2.25:
            motivos.append("Under bloqueado: liga/janela com frequência alta de Over 2.5")
        if (ph5["fez2"] >= 0.40 and pam["sofreu2"] >= 0.40) or (pa5["fez2"] >= 0.40 and phm["sofreu2"] >= 0.40):
            motivos.append("Under bloqueado: ataque recente cruza com defesa que sofre 2+ gols")
        if ph5["fez3"] >= 0.20 or pa5["fez3"] >= 0.20 or phm["sofreu3"] >= 0.20 or pam["sofreu3"] >= 0.20:
            motivos.append("Under bloqueado: existe sinal recente de 3+ gols em um lado")
        if odd_valida(odd_over) and float(odd_over) <= 1.78:
            motivos.append("Under bloqueado: mercado precifica Over como caminho principal")

    if mercado == "Mais de 2.5 gols":
        odd_under = odds.get("Menos de 2.5 gols")
        if total <= 2.18 and fogo <= 0.40:
            motivos.append("Over bloqueado: total esperado e fogo recente baixos")
        if maior < 1.25 and menor < 0.95:
            motivos.append("Over bloqueado: nenhum lado tem força clara de 2 gols")
        if odd_valida(odd_under) and float(odd_under) <= 1.72 and odd >= 2.00:
            motivos.append("Over bloqueado: mercado precifica Under forte")

    # BTTS Não é outro tipo de "segurar gol"; precisa de barreira parecida.
    if mercado == "Ambos marcam - Não":
        odd_btts_sim = odds.get("Ambos marcam - Sim")
        if total >= 2.55 and menor >= 0.90:
            motivos.append("BTTS Não bloqueado: os dois lados têm caminho real para gol")
        if (ph5["marcou"] >= 0.70 and pa5["marcou"] >= 0.70) and menor >= 0.80:
            motivos.append("BTTS Não bloqueado: ambos vêm marcando com frequência")
        if fogo >= 0.52:
            motivos.append("BTTS Não bloqueado: jogo com fogo alto não combina com segurar gol")
        if odd_valida(odd_btts_sim) and float(odd_btts_sim) <= 1.72:
            motivos.append("BTTS Não bloqueado: mercado favorece Ambos Marcam Sim")

    if mercado == "Ambos marcam - Sim":
        odd_btts_nao = odds.get("Ambos marcam - Não")
        if menor <= 0.72:
            motivos.append("BTTS Sim bloqueado: um lado tem expectativa ofensiva baixa")
        if ph5["zerou"] >= 0.40 or pa5["zerou"] >= 0.40:
            motivos.append("BTTS Sim bloqueado: um lado vem passando em branco demais")
        if odd_valida(odd_btts_nao) and float(odd_btts_nao) <= 1.72 and odd >= 2.00:
            motivos.append("BTTS Sim bloqueado: mercado favorece Ambos Marcam Não")

    return motivos


def ajustar_stake_por_risco(mercado: str, stake: float, valor: float, odd: float, contexto: Dict[str, Any]) -> float:
    fator = 1.0

    if contexto["amostra_min"] < 8:
        fator *= 0.55

    if valor < 0.08:
        fator *= 0.60

    if mercado in {"Vitória Casa", "Vitória Fora"}:
        if odd >= 3.00:
            fator *= 0.55
        elif odd >= 2.50:
            fator *= 0.75

    if mercado == "Empate":
        fator *= 0.45

    if mercado in MERCADOS_GOLS_BAIXOS:
        # depois dos seus reds, mercado de segurar gol tem desconto estrutural
        fator *= 0.70
        if contexto["under_perigo"] >= 0.35:
            fator *= 0.60

    if mercado == "Menos de 2.5 gols":
        if contexto["total_gols"] >= 2.20:
            fator *= 0.70

    return clamp(stake * fator, 0.0, 0.05)


def classificar_mercado(
    mercado: str,
    prob: float,
    odd: float,
    odds: Dict[str, float],
    contexto: Dict[str, Any],
    perfil: str,
) -> Dict[str, Any]:

    valor = (prob * odd) - 1.0 if odd_valida(odd) else -1.0
    odd_justa = 1.0 / prob if prob > 0 else np.inf

    resultado = {
        "mercado": mercado,
        "probabilidade": float(prob),
        "odd": float(odd) if odd_valida(odd) else 0.0,
        "odd_justa": float(odd_justa) if np.isfinite(odd_justa) else np.inf,
        "valor": float(valor),
        "apostar": False,
        "nivel": "nao",
        "percentual": 0.0,
        "percentual_original": 0.0,
        "entrada_rs": 0.0,
        "motivo": "",
        "bloqueios": [],
    }

    if not odd_valida(odd):
        resultado["motivo"] = "cotação inválida ou ausente"
        return resultado

    if perfil == "Conservador":
        margem_minima = 0.10
        teto = 0.010
    elif perfil == "Agressivo com controle":
        margem_minima = 0.065
        teto = 0.020
    else:
        margem_minima = 0.080
        teto = 0.015

    # Under precisa de margem maior que outros mercados.
    if mercado == "Menos de 2.5 gols":
        margem_minima += 0.035

    bloqueios = hard_blocks(mercado, prob, odd, odds, contexto)
    resultado["bloqueios"] = bloqueios

    if bloqueios:
        resultado["motivo"] = " | ".join(bloqueios[:3])
        return resultado

    if valor <= margem_minima:
        if valor > 0:
            resultado["motivo"] = f"valor pequeno demais: exige pelo menos {margem_minima*100:.1f}%".replace(".", ",")
        else:
            resultado["motivo"] = "sem valor matemático contra a cotação"
        return resultado

    stake_base = stake_quarto_kelly(prob, odd)
    stake_ajustada = ajustar_stake_por_risco(mercado, stake_base, valor, odd, contexto)
    percentual = min(stake_ajustada, teto)

    if percentual < 0.0025:
        resultado["motivo"] = "valor existe, mas a stake final ficou pequena demais"
        return resultado

    resultado["apostar"] = True
    resultado["percentual"] = float(percentual)
    resultado["percentual_original"] = float(percentual)

    if valor >= 0.20 and percentual >= 0.010:
        nivel = "forte"
    elif valor >= 0.11 and percentual >= 0.006:
        nivel = "boa"
    else:
        nivel = "leve"

    resultado["nivel"] = nivel
    if stake_ajustada < stake_base * 0.95:
        resultado["motivo"] = "valor aprovado, mas stake reduzida por risco contextual"
    else:
        resultado["motivo"] = "valor aprovado após filtros de contexto, mercado e anti-goleada"

    return resultado


def prioridade(r: Dict[str, Any], contexto: Dict[str, Any]) -> float:
    mercado = str(r.get("mercado", ""))
    score = float(r.get("valor", 0)) + float(r.get("percentual", 0)) * 2.0 + float(r.get("probabilidade", 0)) * 0.04

    if mercado == "Menos de 2.5 gols":
        score -= contexto["under_perigo"] * 0.30
    if mercado == "Ambos marcam - Não":
        score -= contexto["fogo_jogo"] * 0.16
    if mercado in {"Vitória Casa", "Vitória Fora"} and float(r.get("probabilidade", 0)) >= 0.48:
        score += 0.07
    if mercado == "Empate":
        score -= 0.08
    return float(score)


def aplicar_correlacao(resultados: List[Dict[str, Any]], contexto: Dict[str, Any]) -> List[Dict[str, Any]]:
    grupos = [MERCADOS_GOLS_BAIXOS, MERCADOS_GOLS_ALTOS, MERCADOS_RESULTADO]
    for grupo in grupos:
        aprovadas = [r for r in resultados if r["apostar"] and r["mercado"] in grupo]
        if len(aprovadas) <= 1:
            continue
        melhor = max(aprovadas, key=lambda x: prioridade(x, contexto))
        for r in aprovadas:
            if r is melhor:
                continue
            r["apostar"] = False
            r["nivel"] = "nao"
            r["percentual"] = 0.0
            r["percentual_original"] = 0.0
            r["entrada_rs"] = 0.0
            r["motivo"] = f"bloqueada por correlação; mantém só a melhor tese do grupo: {melhor['mercado']}"
    return resultados


def montar_resultados(probabilidades: Dict[str, float], odds: Dict[str, float], contexto: Dict[str, Any], banca: float, perfil: str, limite_total: float) -> List[Dict[str, Any]]:
    resultados: List[Dict[str, Any]] = []

    for mercado in MERCADOS:
        if mercado not in probabilidades or mercado not in odds:
            continue
        r = classificar_mercado(
            mercado=mercado,
            prob=float(probabilidades[mercado]),
            odd=float(odds[mercado]),
            odds=odds,
            contexto=contexto,
            perfil=perfil,
        )
        resultados.append(r)

    resultados = aplicar_correlacao(resultados, contexto)

    ordem = {"forte": 0, "boa": 1, "leve": 2, "nao": 3}
    resultados.sort(key=lambda x: (ordem.get(x["nivel"], 9), -float(x["valor"])))

    limite_total = clamp(limite_total, 0.005, 0.06)
    usado = 0.0
    minimo = 0.0025

    for r in resultados:
        if not r["apostar"]:
            continue
        desejado = float(r["percentual"])
        restante = max(0.0, limite_total - usado)
        if restante < minimo:
            r["apostar"] = False
            r["nivel"] = "nao"
            r["percentual"] = 0.0
            r["entrada_rs"] = 0.0
            r["motivo"] = "bloqueada: limite total do jogo já preenchido"
            continue
        final = min(desejado, restante)
        if final < minimo:
            r["apostar"] = False
            r["nivel"] = "nao"
            r["percentual"] = 0.0
            r["entrada_rs"] = 0.0
            r["motivo"] = "bloqueada: stake ficou abaixo do mínimo executável"
        else:
            if final < desejado:
                r["motivo"] = "aprovada, mas reduzida pelo limite total do jogo"
            r["percentual"] = final
            r["entrada_rs"] = float(banca) * final if banca > 0 else 0.0
            usado += final

    resultados.sort(key=lambda x: (ordem.get(x["nivel"], 9), -float(x["valor"])))
    return resultados


# ============================================================
# AUDITORIA / CATÁLOGO / GOOGLE SHEETS OPCIONAL
# ============================================================

def segredo_para_dict(obj: Any) -> Dict[str, Any]:
    try:
        if isinstance(obj, dict):
            return dict(obj)
        return dict(obj)
    except Exception:
        return {}


def config_google() -> Dict[str, Any]:
    try:
        gs = segredo_para_dict(st.secrets.get("google_sheets", {}))
        sa = segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        spreadsheet_id = str(gs.get("spreadsheet_id", "")).strip()
        return {
            "configurado": bool(spreadsheet_id and sa),
            "spreadsheet_id": spreadsheet_id,
            "worksheet_catalogo": str(gs.get("worksheet_catalogo", "catalogo_odds")).strip() or "catalogo_odds",
            "worksheet_auditoria": str(gs.get("worksheet_auditoria", "auditoria_entradas")).strip() or "auditoria_entradas",
        }
    except Exception:
        return {"configurado": False, "spreadsheet_id": "", "worksheet_catalogo": "catalogo_odds", "worksheet_auditoria": "auditoria_entradas"}


@st.cache_resource(show_spinner=False)
def conectar_google():
    cfg = config_google()
    if not cfg.get("configurado"):
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        service_account = segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        service_account = json.loads(json.dumps(service_account))
        creds = Credentials.from_service_account_info(
            service_account,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(creds)
        return client.open_by_key(cfg["spreadsheet_id"])
    except Exception as exc:
        st.warning(f"Google Sheets não conectou. Usando backup local temporário. Detalhe: {exc}")
        return None


def obter_aba(nome: str, colunas: List[str]):
    sh = conectar_google()
    if sh is None:
        return None
    try:
        try:
            ws = sh.worksheet(nome)
        except Exception:
            ws = sh.add_worksheet(title=nome, rows=1000, cols=max(20, len(colunas) + 3))
            ws.update("A1", [colunas])
        valores = ws.get_all_values()
        if not valores:
            ws.update("A1", [colunas])
        elif valores[0] != colunas:
            ws.update("A1", [colunas])
        return ws
    except Exception as exc:
        st.warning(f"Não consegui abrir/criar aba {nome}. Detalhe: {exc}")
        return None


def normalizar_df(df: pd.DataFrame, colunas: List[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=colunas)
    base = df.copy()
    for c in colunas:
        if c not in base.columns:
            base[c] = ""
    return base[colunas].fillna("")


def carregar_csv(path: str, colunas: List[str]) -> pd.DataFrame:
    garantir_logs()
    if not os.path.exists(path):
        return pd.DataFrame(columns=colunas)
    try:
        return normalizar_df(pd.read_csv(path), colunas)
    except Exception:
        return pd.DataFrame(columns=colunas)


def salvar_csv(df: pd.DataFrame, path: str, colunas: List[str]) -> None:
    garantir_logs()
    normalizar_df(df, colunas).to_csv(path, index=False)


def carregar_google(nome_aba: str, colunas: List[str]) -> Optional[pd.DataFrame]:
    ws = obter_aba(nome_aba, colunas)
    if ws is None:
        return None
    try:
        valores = ws.get_all_values()
        if len(valores) <= 1:
            return pd.DataFrame(columns=colunas)
        return normalizar_df(pd.DataFrame(valores[1:], columns=valores[0]), colunas)
    except Exception:
        return None


def salvar_google(df: pd.DataFrame, nome_aba: str, colunas: List[str]) -> bool:
    ws = obter_aba(nome_aba, colunas)
    if ws is None:
        return False
    try:
        base = normalizar_df(df, colunas).astype(str)
        ws.clear()
        ws.update("A1", [colunas] + base.values.tolist(), value_input_option="USER_ENTERED")
        return True
    except Exception as exc:
        st.warning(f"Google Sheets falhou ao salvar. Backup local foi atualizado. Detalhe: {exc}")
        return False


def carregar_auditoria() -> pd.DataFrame:
    cfg = config_google()
    if cfg.get("configurado"):
        g = carregar_google(cfg["worksheet_auditoria"], COLUNAS_AUDITORIA)
        if g is not None:
            return normalizar_df(g, COLUNAS_AUDITORIA)
    return carregar_csv(ARQUIVO_AUDITORIA, COLUNAS_AUDITORIA)


def salvar_auditoria(df: pd.DataFrame) -> str:
    base = normalizar_df(df, COLUNAS_AUDITORIA)
    salvar_csv(base, ARQUIVO_AUDITORIA, COLUNAS_AUDITORIA)
    cfg = config_google()
    if cfg.get("configurado") and salvar_google(base, cfg["worksheet_auditoria"], COLUNAS_AUDITORIA):
        return "Google Sheets + backup local"
    return "backup local"


def carregar_catalogo() -> pd.DataFrame:
    cfg = config_google()
    if cfg.get("configurado"):
        g = carregar_google(cfg["worksheet_catalogo"], COLUNAS_CATALOGO)
        if g is not None:
            return normalizar_df(g, COLUNAS_CATALOGO)
    return carregar_csv(ARQUIVO_CATALOGO, COLUNAS_CATALOGO)


def salvar_catalogo(df: pd.DataFrame) -> str:
    base = normalizar_df(df, COLUNAS_CATALOGO)
    salvar_csv(base, ARQUIVO_CATALOGO, COLUNAS_CATALOGO)
    cfg = config_google()
    if cfg.get("configurado") and salvar_google(base, cfg["worksheet_catalogo"], COLUNAS_CATALOGO):
        return "Google Sheets + backup local"
    return "backup local"


def banca_atual(banca_inicial: float, auditoria: pd.DataFrame) -> float:
    if auditoria.empty or "Resultado R$" not in auditoria.columns:
        return float(banca_inicial)
    resultado = pd.to_numeric(auditoria["Resultado R$"], errors="coerce").fillna(0).sum()
    return float(banca_inicial + resultado)


def selecao_mercado(mercado: str, time_casa: str, time_fora: str) -> str:
    mapa = {
        "Vitória Casa": time_casa,
        "Vitória Fora": time_fora,
        "Empate": "Empate",
        "Mais de 2.5 gols": "Mais de 2.5 gols",
        "Menos de 2.5 gols": "Menos de 2.5 gols",
        "Ambos marcam - Sim": "Sim",
        "Ambos marcam - Não": "Não",
        "Casa ou Empate": f"{time_casa} ou empate",
        "Fora ou Empate": f"{time_fora} ou empate",
        "Empate Anula Casa": time_casa,
        "Empate Anula Fora": time_fora,
    }
    return mapa.get(mercado, mercado)


def registrar_odds_catalogo(catalogo: pd.DataFrame, liga: str, jogo: str, time_casa: str, time_fora: str, casa: str, odds: Dict[str, float], banca: float, perfil: str, data_jogo: date, hora_jogo: str, origem: str, obs: str) -> pd.DataFrame:
    base = normalizar_df(catalogo, COLUNAS_CATALOGO)
    coleta_id = str(uuid.uuid4())[:8]
    linhas = []
    for mercado, odd in odds.items():
        linhas.append({
            "ID Coleta": coleta_id,
            "Registrado em": now_str(),
            "Data do jogo": str(data_jogo),
            "Hora do jogo": str(hora_jogo),
            "Casa de apostas": casa,
            "Liga": liga,
            "Jogo": jogo,
            "Mandante": time_casa,
            "Visitante": time_fora,
            "Mercado": mercado,
            "Seleção": selecao_mercado(mercado, time_casa, time_fora),
            "Cotação": float(odd),
            "Banca no momento": float(banca),
            "Perfil": perfil,
            "Origem": origem,
            "Observação": obs,
        })
    return normalizar_df(pd.concat([base, pd.DataFrame(linhas)], ignore_index=True), COLUNAS_CATALOGO)


def registrar_entrada(auditoria: pd.DataFrame, liga: str, jogo: str, casa_apostas: str, mercado: str, selecao: str, resultado: Dict[str, Any], banca: float, origem: str, obs: str, data_jogo: str = "") -> pd.DataFrame:
    base = normalizar_df(auditoria, COLUNAS_AUDITORIA)
    entrada = float(resultado.get("entrada_rs", 0.0))
    nova = {
        "ID": str(uuid.uuid4())[:8],
        "Registrado em": now_str(),
        "Data do jogo": data_jogo,
        "Liga": liga,
        "Jogo": jogo,
        "Casa de apostas": casa_apostas,
        "Mercado": mercado,
        "Seleção": selecao,
        "Cotação de entrada": float(resultado.get("odd", 0.0)),
        "Cotação justa": float(resultado.get("odd_justa", 0.0)) if np.isfinite(float(resultado.get("odd_justa", 0.0))) else "",
        "Chance pelo sistema %": round(float(resultado.get("probabilidade", 0.0)) * 100, 2),
        "Valor esperado %": round(float(resultado.get("valor", 0.0)) * 100, 2),
        "Entrada %": round(float(resultado.get("percentual", 0.0)) * 100, 3),
        "Entrada R$": round(entrada, 2),
        "Banca antes": round(float(banca), 2),
        "Status": "Pendente",
        "Resultado R$": 0.0,
        "Banca depois": "",
        "Cotação de fechamento": "",
        "Vantagem no fechamento %": "",
        "Origem": origem,
        "Observação": obs,
    }
    return normalizar_df(pd.concat([base, pd.DataFrame([nova])], ignore_index=True), COLUNAS_AUDITORIA)


def fechar_resultado(status: str, entrada: float, odd: float, cashout: float = 0.0) -> float:
    if status == "Green":
        return entrada * (odd - 1.0)
    if status == "Red":
        return -entrada
    if status == "Void":
        return 0.0
    if status == "Cashout":
        return cashout - entrada
    return 0.0


def excel_bytes(abas: Dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for nome, df in abas.items():
                safe = nome[:31].replace("/", "-").replace("\\", "-").replace("*", "")
                df.to_excel(writer, sheet_name=safe, index=False)
        return buffer.getvalue()
    except Exception:
        return b""


# ============================================================
# RENDER
# ============================================================

def nome_mercado(mercado: str, time_casa: str, time_fora: str) -> str:
    return (
        mercado
        .replace("Vitória Casa", f"Vitória {time_casa}")
        .replace("Vitória Fora", f"Vitória {time_fora}")
        .replace("Casa ou Empate", f"{time_casa} ou Empate")
        .replace("Fora ou Empate", f"{time_fora} ou Empate")
        .replace("Empate Anula Casa", f"Empate Anula {time_casa}")
        .replace("Empate Anula Fora", f"Empate Anula {time_fora}")
    )


def render_resultado(r: Dict[str, Any], banca: float, time_casa: str, time_fora: str) -> None:
    nivel = r["nivel"]
    apostar = bool(r["apostar"])
    if apostar and nivel == "forte":
        cls, title, cor = "decision-green", f"✅ APOSTAR {porcentagem(r['percentual'], 2)} DA BANCA", "big-ok"
    elif apostar and nivel == "boa":
        cls, title, cor = "decision-yellow", f"🟡 APOSTAR {porcentagem(r['percentual'], 2)} DA BANCA", "big-warn"
    elif apostar and nivel == "leve":
        cls, title, cor = "decision-blue", f"🔵 APOSTAR {porcentagem(r['percentual'], 2)} DA BANCA", "big-blue"
    else:
        cls, title, cor = "decision-red", "❌ NÃO APOSTAR", "big-bad"

    odd_justa = "-" if not np.isfinite(float(r["odd_justa"])) else numero(float(r["odd_justa"]), 2)
    st.markdown(
        f"""
        <div class="decision-card {cls}">
            <div class="{cor}">{title}</div>
            <div class="market-title">{nome_mercado(r['mercado'], time_casa, time_fora)}</div>
            <div class="line"><b>Cotação:</b> {numero(r['odd'], 2)} | <b>Justa:</b> {odd_justa} | <b>Chance:</b> {porcentagem(r['probabilidade'], 1)} | <b>EV:</b> {porcentagem(r['valor'], 1)}</div>
            <div class="line"><b>Entrada sugerida:</b> {dinheiro(r['entrada_rs'])} | <b>Núcleo automático:</b> {"Sim" if r['mercado'] in MERCADOS_NUCLEO else "Não"}</div>
            <div class="explain"><b>Motivo:</b> {r['motivo']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_contexto(contexto: Dict[str, Any], time_casa: str, time_fora: str) -> None:
    st.markdown("### Leitura de risco antes da aposta")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"Gols {time_casa}", numero(contexto["gols_casa"], 2))
    c2.metric(f"Gols {time_fora}", numero(contexto["gols_fora"], 2))
    c3.metric("Total esperado", numero(contexto["total_gols"], 2))
    c4.metric("Fogo do jogo", porcentagem(contexto["fogo_jogo"], 0))
    c5.metric("Risco Under", porcentagem(contexto["under_perigo"], 0))

    with st.expander("Ver diagnóstico simples de gols e goleada"):
        ph5 = contexto["casa_5"]
        pa5 = contexto["fora_5"]
        phm = contexto["casa_mando"]
        pam = contexto["fora_mando"]

        st.markdown(
            f"""
            <div class="risk-box">
                <b>{time_casa} últimos 5:</b>
                média fez {numero(ph5['gf_med'],2)}, sofreu {numero(ph5['ga_med'],2)},
                fez 2+ em {porcentagem(ph5['fez2'],0)}, fez 3+ em {porcentagem(ph5['fez3'],0)},
                Over 2.5 em {porcentagem(ph5['over25'],0)}.
                <br>
                <b>{time_fora} últimos 5:</b>
                média fez {numero(pa5['gf_med'],2)}, sofreu {numero(pa5['ga_med'],2)},
                fez 2+ em {porcentagem(pa5['fez2'],0)}, fez 3+ em {porcentagem(pa5['fez3'],0)},
                Over 2.5 em {porcentagem(pa5['over25'],0)}.
                <br><br>
                <b>{time_casa} em casa:</b> sofre 2+ em {porcentagem(phm['sofreu2'],0)} e sofre 3+ em {porcentagem(phm['sofreu3'],0)}.
                <br>
                <b>{time_fora} fora:</b> sofre 2+ em {porcentagem(pam['sofreu2'],0)} e sofre 3+ em {porcentagem(pam['sofreu3'],0)}.
                <br><br>
                <b>Índice de goleada:</b> {porcentagem(contexto['risco_goleada'],0)}.
                <b>Amostra casa/fora:</b> {contexto['amostra_casa_home']} x {contexto['amostra_fora_away']} jogos.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# APP
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">TEX STATISTICS V18</div>
        <div class="hero-sub">
            Refeito do zero: primeiro lê forma recente, fogo do jogo e risco de goleada; só depois calcula Poisson, valor e stake.
            Under 2.5 e BTTS Não agora são tratados como mercados perigosos de "segurar gol".
        </div>
        <span class="chip">Anti-Goleada</span>
        <span class="chip">Forma recente 5/10</span>
        <span class="chip">Sem chute de time na API</span>
        <span class="chip">1/4 Kelly conservador</span>
        <span class="chip">Auditoria</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Banca")
    banca_inicial = st.number_input("Banca inicial", min_value=0.0, value=1000.0, step=50.0)
    auditoria_sidebar = carregar_auditoria()
    banca_calc = banca_atual(float(banca_inicial), auditoria_sidebar)
    usar_auditada = st.checkbox("Usar banca calculada pela auditoria", value=True)
    banca_manual = st.number_input("Banca manual", min_value=0.0, value=1000.0, step=50.0)
    banca_usada = banca_calc if usar_auditada else float(banca_manual)
    st.metric("Banca usada", dinheiro(banca_usada))

    st.divider()
    st.header("Perfil")
    perfil = st.selectbox("Perfil de operação", ["Conservador", "Volume controlado", "Agressivo com controle"], index=1)
    limite_default = {"Conservador": 0.015, "Volume controlado": 0.025, "Agressivo com controle": 0.035}[perfil]
    limite_total = st.slider("Máximo total no mesmo jogo", 0.5, 5.0, float(limite_default * 100), 0.5) / 100.0

    st.divider()
    st.header("Dados")
    liga_sel = st.selectbox("Liga", list(LIGAS_CSV.keys()))
    janela_txt = st.selectbox("Janela histórica", ["300 jogos", "500 jogos", "760 jogos", "1500 jogos"], index=1)
    janela = int(janela_txt.split()[0])
    st.caption("A janela define a base histórica. A forma recente continua olhando os últimos 5/10 jogos dos times.")

    st.divider()
    st.header("API de odds")
    chave_api = st.text_input("The Odds API key", value=os.getenv("ODDS_API_KEY", ""), type="password")
    casa_apostas = st.selectbox("Casa de apostas", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"])

tabs = st.tabs(["🎯 Analisar", "📒 Auditoria", "📊 Catálogo de odds", "🗓️ Calendário"])

with tabs[0]:
    with st.spinner("Carregando base..."):
        df = carregar_base(LIGAS_CSV[liga_sel], janela)

    if df.empty:
        st.error("Não consegui carregar a base da liga.")
        st.stop()

    times = sorted(df["Home"].dropna().unique().tolist())
    c1, c2, c3, c4 = st.columns(4)
    liga_metrics = metricas_liga(df)
    c1.metric("Jogos na base", len(df))
    c2.metric("Times", len(times))
    c3.metric("Média gols liga", numero(liga_metrics["total_avg"], 2))
    c4.metric("Over 2.5 liga", porcentagem(liga_metrics["over25"], 0))

    modo = st.radio("Modo de análise", ["Manual", "Automático pela API"], horizontal=True)

    odds: Dict[str, float] = {}
    time_casa = times[0]
    time_fora = times[min(1, len(times) - 1)]
    jogo_nome = ""
    origem = modo
    data_jogo = date.today()
    hora_jogo = ""
    botao_analisar = False
    botao_catalogo = False

    if modo == "Manual":
        st.markdown("### Jogo")
        c1, c2 = st.columns(2)
        with c1:
            time_casa = st.selectbox("Mandante", times, key="manual_home")
        with c2:
            time_fora = st.selectbox("Visitante", times, key="manual_away")

        c1, c2 = st.columns(2)
        with c1:
            data_jogo = st.date_input("Data do jogo", value=date.today(), key="manual_data")
        with c2:
            hora_jogo = st.text_input("Hora", value="", placeholder="ex: 15:45", key="manual_hora")

        if time_casa == time_fora:
            st.warning("Mandante e visitante não podem ser o mesmo time.")
        else:
            jogo_nome = f"{time_casa} x {time_fora}"
            odds = coletar_odds_manuais("manual")
            c1, c2 = st.columns(2)
            with c1:
                botao_analisar = st.button("ANALISAR JOGO", type="primary")
            with c2:
                botao_catalogo = st.button("SALVAR ODDS NO CATÁLOGO")

    else:
        if not chave_api:
            st.warning("Informe a chave da API na lateral ou use o modo manual.")
        elif liga_sel not in LIGAS_API:
            st.warning("Liga não mapeada na API. Use modo manual.")
        else:
            jogos_api = buscar_odds_api(chave_api, LIGAS_API[liga_sel])
            if not jogos_api:
                st.warning("API sem jogos/odds disponíveis agora para essa liga.")
            else:
                opcoes = {}
                agora = pd.Timestamp.now(tz="UTC")
                for jogo in jogos_api:
                    try:
                        inicio = pd.to_datetime(jogo.get("commence_time"), utc=True)
                        if inicio <= agora:
                            continue
                        label = f"{jogo.get('home_team')} x {jogo.get('away_team')} — {inicio.tz_convert('America/Sao_Paulo').strftime('%d/%m %H:%M')}"
                        opcoes[label] = jogo
                    except Exception:
                        continue

                if not opcoes:
                    st.info("A API respondeu, mas não há pré-jogo disponível.")
                else:
                    escolha = st.selectbox("Partida", list(opcoes.keys()))
                    jogo_api = opcoes[escolha]

                    candidato_casa = casar_time_api(jogo_api.get("home_team", ""), times)
                    candidato_fora = casar_time_api(jogo_api.get("away_team", ""), times)

                    if candidato_casa is None or candidato_fora is None:
                        st.error("Não consegui casar automaticamente um dos times da API com a base CSV. Isso agora BLOQUEIA análise automática para evitar jogo errado. Use modo manual.")
                    else:
                        time_casa = candidato_casa
                        time_fora = candidato_fora
                        c1, c2 = st.columns(2)
                        with c1:
                            time_casa = st.selectbox("Mandante na base", times, index=times.index(time_casa), key="api_home")
                        with c2:
                            time_fora = st.selectbox("Visitante na base", times, index=times.index(time_fora), key="api_away")
                        jogo_nome = f"{time_casa} x {time_fora}"
                        odds = extrair_odds_api(jogo_api)
                        st.info(f"Cotações encontradas: {len(odds)} mercado(s).")
                        botao_analisar = st.button("ANALISAR JOGO DA API", type="primary")

    if botao_catalogo:
        if not odds:
            st.error("Nenhuma cotação válida para salvar.")
        else:
            cat = carregar_catalogo()
            cat = registrar_odds_catalogo(cat, liga_sel, jogo_nome, time_casa, time_fora, casa_apostas, odds, banca_usada, perfil, data_jogo, hora_jogo, "Manual", "")
            destino = salvar_catalogo(cat)
            st.success(f"Odds salvas no catálogo. Destino: {destino}")

    if botao_analisar:
        if not odds:
            st.error("Nenhuma cotação válida informada/encontrada.")
        elif time_casa == time_fora:
            st.error("Jogo inválido: times iguais.")
        else:
            contexto = calcular_contexto(df, time_casa, time_fora)
            probabilidades = calcular_probabilidades(contexto)
            resultados = montar_resultados(probabilidades, odds, contexto, banca_usada, perfil, limite_total)
            st.session_state["ultima_analise_v18"] = {
                "liga": liga_sel,
                "jogo": jogo_nome,
                "time_casa": time_casa,
                "time_fora": time_fora,
                "casa_apostas": casa_apostas,
                "origem": origem,
                "banca": float(banca_usada),
                "perfil": perfil,
                "data_jogo": str(data_jogo),
                "contexto": contexto,
                "probabilidades": probabilidades,
                "odds": odds,
                "resultados": resultados,
            }

    analise = st.session_state.get("ultima_analise_v18")
    if analise:
        st.markdown("---")
        st.subheader(f"Análise — {analise['jogo']}")
        contexto = analise["contexto"]
        resultados = analise["resultados"]
        aprovadas = [r for r in resultados if r["apostar"]]

        render_contexto(contexto, analise["time_casa"], analise["time_fora"])

        if aprovadas:
            total_rs = sum(float(r["entrada_rs"]) for r in aprovadas)
            st.success(f"{len(aprovadas)} entrada(s) passaram. Total sugerido: {dinheiro(total_rs)}.")
        else:
            st.info("Nenhuma entrada passou. Isso é esperado quando há risco oculto, odd sem valor ou jogo com fogo/goleada.")

        st.markdown("### Decisões por mercado")
        for r in resultados:
            render_resultado(r, analise["banca"], analise["time_casa"], analise["time_fora"])

        if aprovadas:
            st.markdown("---")
            st.markdown("### Registrar na auditoria")
            auditoria = carregar_auditoria()
            analise_id = str(uuid.uuid4())[:6]
            escolhidas = []
            with st.form(key=f"form_reg_{analise_id}"):
                for i, r in enumerate(aprovadas):
                    label = f"{nome_mercado(r['mercado'], analise['time_casa'], analise['time_fora'])} — {numero(r['odd'],2)} — {dinheiro(r['entrada_rs'])}"
                    if st.checkbox(label, value=True, key=f"reg_{analise_id}_{i}"):
                        escolhidas.append(r)
                obs = st.text_area("Observação", value="", placeholder="Ex: escalação conferida, odds Pixbet, sem cashout...")
                salvar = st.form_submit_button("SALVAR ENTRADAS MARCADAS", type="primary")

            if salvar:
                if not escolhidas:
                    st.warning("Nenhuma entrada marcada.")
                else:
                    for r in escolhidas:
                        auditoria = registrar_entrada(
                            auditoria,
                            liga=analise["liga"],
                            jogo=analise["jogo"],
                            casa_apostas=analise["casa_apostas"],
                            mercado=r["mercado"],
                            selecao=selecao_mercado(r["mercado"], analise["time_casa"], analise["time_fora"]),
                            resultado=r,
                            banca=analise["banca"],
                            origem="Motor V18",
                            obs=obs,
                            data_jogo=analise.get("data_jogo", ""),
                        )
                    destino = salvar_auditoria(auditoria)
                    st.success(f"Entradas salvas. Destino: {destino}")

        if st.button("LIMPAR ANÁLISE"):
            st.session_state.pop("ultima_analise_v18", None)
            st.rerun()

with tabs[1]:
    st.subheader("Auditoria operacional")
    auditoria = carregar_auditoria()
    banca_calc = banca_atual(float(banca_inicial), auditoria)

    c1, c2, c3 = st.columns(3)
    c1.metric("Banca inicial", dinheiro(banca_inicial))
    c2.metric("Banca auditada", dinheiro(banca_calc))
    c3.metric("Resultado total", dinheiro(banca_calc - float(banca_inicial)))

    cfg = config_google()
    if cfg.get("configurado"):
        st.success("Google Sheets configurado para auditoria/catálogo.")
    else:
        st.warning("Google Sheets não configurado. O backup local pode sumir no Streamlit Cloud ao reiniciar.")

    with st.expander("Adicionar entrada manual"):
        c1, c2 = st.columns(2)
        with c1:
            aud_liga = st.text_input("Liga", value=liga_sel, key="aud_liga")
            aud_jogo = st.text_input("Jogo", value="", key="aud_jogo")
            aud_mercado = st.selectbox("Mercado", MERCADOS, key="aud_mercado")
            aud_selecao = st.text_input("Seleção", value="", key="aud_selecao")
        with c2:
            aud_casa = st.selectbox("Casa", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"], key="aud_casa")
            aud_odd = st.text_input("Cotação", value="", key="aud_odd")
            aud_valor = st.text_input("Entrada R$", value="", key="aud_valor")
            aud_banca = st.number_input("Banca antes", min_value=0.0, value=float(banca_calc), step=10.0, key="aud_banca")
        aud_obs = st.text_input("Observação", value="", key="aud_obs")
        if st.button("SALVAR ENTRADA MANUAL"):
            odd = texto_para_float(aud_odd)
            ent = texto_para_float(aud_valor)
            if not aud_jogo.strip() or not odd_valida(odd) or ent is None or ent <= 0:
                st.error("Preencha jogo, cotação válida e valor.")
            else:
                fake = {
                    "odd": float(odd), "odd_justa": 0.0, "probabilidade": 0.0,
                    "valor": 0.0, "percentual": safe_div(ent, aud_banca, 0.0),
                    "entrada_rs": float(ent),
                }
                auditoria = registrar_entrada(
                    auditoria, aud_liga, aud_jogo, aud_casa, aud_mercado,
                    aud_selecao or aud_mercado, fake, float(aud_banca), "Manual livre", aud_obs
                )
                destino = salvar_auditoria(auditoria)
                st.success(f"Entrada manual salva. Destino: {destino}")

    st.markdown("### Fechar entrada")
    if auditoria.empty:
        st.info("Ainda não há entradas.")
    else:
        pendentes = auditoria[auditoria["Status"].astype(str) == "Pendente"].copy()
        if pendentes.empty:
            st.info("Sem pendentes.")
        else:
            labels = []
            mapa = {}
            for idx, row in pendentes.iterrows():
                label = f"{row['ID']} — {row['Jogo']} — {row['Mercado']} — {dinheiro(texto_para_float(row['Entrada R$']) or 0)}"
                labels.append(label)
                mapa[label] = idx
            escolha = st.selectbox("Entrada", labels)
            idx = mapa[escolha]
            row = auditoria.loc[idx]
            c1, c2, c3 = st.columns(3)
            with c1:
                status = st.selectbox("Resultado", ["Green", "Red", "Void", "Cashout"])
            with c2:
                odd_close_txt = st.text_input("Odd fechamento", value="")
            with c3:
                cashout = st.number_input("Cashout recebido", min_value=0.0, value=0.0, step=1.0)
            obs_close = st.text_input("Observação fechamento", value="")
            if st.button("FECHAR ENTRADA"):
                entrada = texto_para_float(row["Entrada R$"]) or 0.0
                odd_ent = texto_para_float(row["Cotação de entrada"]) or 0.0
                res = fechar_resultado(status, entrada, odd_ent, cashout)
                odd_close = texto_para_float(odd_close_txt)
                vantagem = ""
                if odd_valida(odd_close) and odd_ent > 0:
                    vantagem = round(((odd_ent / float(odd_close)) - 1.0) * 100.0, 2)
                banca_depois = (texto_para_float(row["Banca antes"]) or 0.0) + res
                auditoria.loc[idx, "Status"] = status
                auditoria.loc[idx, "Resultado R$"] = round(res, 2)
                auditoria.loc[idx, "Banca depois"] = round(banca_depois, 2)
                auditoria.loc[idx, "Cotação de fechamento"] = odd_close if odd_close is not None else ""
                auditoria.loc[idx, "Vantagem no fechamento %"] = vantagem
                auditoria.loc[idx, "Observação"] = str(row.get("Observação", "")) + " | Fechamento: " + obs_close
                destino = salvar_auditoria(auditoria)
                st.success(f"Entrada fechada. Destino: {destino}")

        st.markdown("### Histórico")
        auditoria = carregar_auditoria()
        st.dataframe(auditoria.tail(500), use_container_width=True, hide_index=True)
        csv = auditoria.to_csv(index=False).encode("utf-8-sig")
        st.download_button("BAIXAR AUDITORIA CSV", data=csv, file_name="auditoria_tex_v18.csv", mime="text/csv")
        xb = excel_bytes({"Auditoria": auditoria})
        if xb:
            st.download_button("BAIXAR AUDITORIA EXCEL", data=xb, file_name="auditoria_tex_v18.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tabs[2]:
    st.subheader("Catálogo de odds")
    catalogo = carregar_catalogo()
    if catalogo.empty:
        st.info("Ainda não há odds salvas.")
    else:
        f1, f2, f3 = st.columns(3)
        with f1:
            filtro_liga = st.multiselect("Liga", sorted(catalogo["Liga"].dropna().unique().tolist()))
        with f2:
            filtro_casa = st.multiselect("Casa", sorted(catalogo["Casa de apostas"].dropna().unique().tolist()))
        with f3:
            busca = st.text_input("Buscar jogo/time", value="")
        filtrado = catalogo.copy()
        if filtro_liga:
            filtrado = filtrado[filtrado["Liga"].isin(filtro_liga)]
        if filtro_casa:
            filtrado = filtrado[filtrado["Casa de apostas"].isin(filtro_casa)]
        if busca.strip():
            termo = busca.strip().lower()
            filtrado = filtrado[
                filtrado["Jogo"].astype(str).str.lower().str.contains(termo, na=False)
                | filtrado["Mandante"].astype(str).str.lower().str.contains(termo, na=False)
                | filtrado["Visitante"].astype(str).str.lower().str.contains(termo, na=False)
            ]

        st.dataframe(filtrado.tail(500), use_container_width=True, hide_index=True)
        csv = filtrado.to_csv(index=False).encode("utf-8-sig")
        st.download_button("BAIXAR CATÁLOGO CSV", data=csv, file_name="catalogo_odds_tex_v18.csv", mime="text/csv")
        xb = excel_bytes({"Catalogo": filtrado})
        if xb:
            st.download_button("BAIXAR CATÁLOGO EXCEL", data=xb, file_name="catalogo_odds_tex_v18.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tabs[3]:
    st.subheader("Calendário operacional das ligas")
    st.warning("Use isto como mapa operacional, não como lista oficial de jogos. Confira sempre a casa/API antes.")
    cal = pd.DataFrame(CALENDARIO_LIGAS)
    mes = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], index=datetime.now().month - 1)
    st.dataframe(cal[["Liga", mes]], use_container_width=True, hide_index=True)

    st.markdown("### Conferir jogos agora pela API")
    ligas_check = st.multiselect("Ligas para consultar", list(LIGAS_API.keys()), default=[liga_sel] if liga_sel in LIGAS_API else [])
    if st.button("VERIFICAR JOGOS DISPONÍVEIS"):
        if not chave_api:
            st.warning("Informe a chave da API na lateral.")
        else:
            encontrados = []
            agora = pd.Timestamp.now(tz="UTC")
            for liga_nome in ligas_check:
                dados = buscar_odds_api(chave_api, LIGAS_API[liga_nome])
                for jogo in dados or []:
                    try:
                        inicio = pd.to_datetime(jogo.get("commence_time"), utc=True)
                        if inicio > agora:
                            encontrados.append({
                                "Liga": liga_nome,
                                "Jogo": f"{jogo.get('home_team')} x {jogo.get('away_team')}",
                                "Data/Hora": inicio.tz_convert("America/Sao_Paulo").strftime("%d/%m %H:%M"),
                            })
                    except Exception:
                        continue
            if encontrados:
                st.success(f"Encontrei {len(encontrados)} jogo(s).")
                st.dataframe(pd.DataFrame(encontrados), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum jogo pré-jogo encontrado nas ligas consultadas.")
