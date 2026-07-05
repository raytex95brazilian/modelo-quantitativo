import os
import io
import json
import uuid
import difflib
import html
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson, chi2

# ============================================================
# TEX STATISTICS V19.3.3 — PRIORIDADE OPERACIONAL REAL + GOOGLE ECONOMY
# ============================================================
# Objetivo desta versão:
# - parar de empilhar filtros subjetivos;
# - replicar a lógica simples da planilha que funcionou;
# - calcular forças ataque/defesa, Poisson, odd justa, margem +EV e Kelly fracionado;
# - manter apenas travas operacionais: liga correta, time correto e amostra mínima.
# ============================================================

st.set_page_config(page_title="TEX STATISTICS — V19.3.3 Prioridade Real", layout="wide")

# ============================================================
# VISUAL
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Space+Grotesk:wght@600;700&display=swap');

    :root {
        color-scheme: light;
        --bg: #f6f7fb;
        --card: #ffffff;
        --text: #111827;
        --muted: #64748b;
        --line: #e5e7eb;
        --accent: #0f766e;
        --green: #059669;
        --yellow: #d97706;
        --red: #dc2626;
        --blue: #2563eb;
        --shadow: 0 12px 28px rgba(15, 23, 42, 0.075);
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }

    [data-testid="stHeader"] {
        background: rgba(246, 247, 251, 0.92) !important;
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(229, 231, 235, 0.85);
    }

    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background: #ffffff !important;
        color: var(--text) !important;
        border-right: 1px solid var(--line);
    }

    label, p, span, small, div, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    .stCaption, [data-testid="stCaptionContainer"], .muted, small {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
    }

    input, textarea, [data-baseweb="input"], [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea, [data-baseweb="select"], [data-baseweb="select"] div,
    [role="listbox"], [role="option"], [data-baseweb="popover"], [data-baseweb="menu"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #cbd5e1 !important;
    }

    input::placeholder, textarea::placeholder,
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {
        color: #a8b1c2 !important;
        -webkit-text-fill-color: #a8b1c2 !important;
        opacity: 1 !important;
        font-weight: 500 !important;
    }

    .stat-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 16px 17px;
        box-shadow: 0 12px 26px rgba(15, 23, 42, 0.075);
        min-height: 92px;
    }

    .stat-label {
        font-family: "Inter", system-ui, sans-serif;
        font-size: 0.76rem;
        font-weight: 850;
        letter-spacing: .02em;
        text-transform: uppercase;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        margin-bottom: 6px;
    }

    .stat-value {
        font-family: "Space Grotesk", "Inter", sans-serif;
        font-size: 2.05rem;
        line-height: 1;
        letter-spacing: -0.04em;
        font-weight: 800;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    .stat-hint {
        margin-top: 8px;
        font-size: 0.76rem;
        font-weight: 700;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
    }

    .base-info {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 16px;
        padding: 12px 14px;
        margin: 10px 0 16px;
        font-size: .88rem;
        font-weight: 700;
        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;
    }

    .confidence-button {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border-radius: 999px;
        padding: 10px 15px;
        font-family: "Space Grotesk", "Inter", sans-serif;
        font-weight: 800;
        letter-spacing: -0.01em;
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
        margin: 5px 0 12px;
        border: 1px solid transparent;
    }
    .confidence-good { background: #dcfce7; border-color: #86efac; color: #166534 !important; -webkit-text-fill-color: #166534 !important; }
    .confidence-mid { background: #ffedd5; border-color: #fdba74; color: #9a3412 !important; -webkit-text-fill-color: #9a3412 !important; }
    .confidence-low { background: #fee2e2; border-color: #fca5a5; color: #991b1b !important; -webkit-text-fill-color: #991b1b !important; }

    .priority-badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 7px 11px;
        border-radius: 999px;
        font-weight: 900;
        font-size: .78rem;
        margin-bottom: 8px;
        border: 1px solid transparent;
    }
    .priority-high { background: #dcfce7; border-color: #86efac; color: #166534 !important; -webkit-text-fill-color: #166534 !important; }
    .priority-medium { background: #ffedd5; border-color: #fdba74; color: #9a3412 !important; -webkit-text-fill-color: #9a3412 !important; }
    .priority-low { background: #fee2e2; border-color: #fca5a5; color: #991b1b !important; -webkit-text-fill-color: #991b1b !important; }

    [role="option"]:hover, [role="option"][aria-selected="true"] {
        background: #f1f5f9 !important;
    }

    .hero {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 24px 22px;
        margin-bottom: 16px;
        box-shadow: var(--shadow);
        position: relative;
        overflow: hidden;
    }

    .hero:before {
        content: "";
        position: absolute;
        left: 0;
        top: 16%;
        height: 68%;
        width: 7px;
        border-radius: 999px;
        background: var(--accent);
    }

    .hero-title {
        font-family: "Space Grotesk", "Inter", sans-serif;
        font-size: 2.2rem;
        line-height: 1.05;
        font-weight: 700;
        letter-spacing: -0.8px;
        margin: 6px 0 8px;
    }

    .hero-sub {
        max-width: 980px;
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        line-height: 1.55;
        font-weight: 500;
    }

    .chip {
        display: inline-block;
        padding: 7px 11px;
        border-radius: 999px;
        background: #ecfdf5;
        border: 1px solid #bbf7d0;
        color: #166534 !important;
        -webkit-text-fill-color: #166534 !important;
        font-weight: 800;
        font-size: 0.78rem;
        margin-right: 7px;
        margin-top: 10px;
    }

    .box, .card-ev, .card-no, .card-info {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: var(--shadow);
        padding: 16px;
        margin: 12px 0;
    }

    .card-ev { border-left: 8px solid var(--green); }
    .card-no { border-left: 8px solid var(--red); }
    .card-info { border-left: 8px solid var(--blue); }

    .big-green { color: var(--green) !important; -webkit-text-fill-color: var(--green) !important; font-weight: 900; }
    .big-red { color: var(--red) !important; -webkit-text-fill-color: var(--red) !important; font-weight: 900; }
    .big-blue { color: var(--blue) !important; -webkit-text-fill-color: var(--blue) !important; font-weight: 900; }
    .big-yellow { color: var(--yellow) !important; -webkit-text-fill-color: var(--yellow) !important; font-weight: 900; }

    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button,
    button[kind="primary"], button[kind="secondary"] {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 14px !important;
        font-weight: 850 !important;
        box-shadow: none !important;
    }

    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover,
    button[kind="primary"]:hover, button[kind="secondary"]:hover {
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
    }

    [data-testid="stMetric"], [data-testid="stDataFrame"], [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid var(--line) !important;
        border-radius: 16px !important;
        box-shadow: var(--shadow) !important;
    }

    @media (max-width: 768px) {
        .hero { padding: 19px 16px; border-radius: 20px; }
        .hero-title { font-size: 1.55rem; }
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

COLUNAS_AUDITORIA = [
    "ID", "Registrado em", "Liga", "Jogo", "Casa de apostas", "Mercado",
    "Cotação de entrada", "Cotação justa", "Chance pelo sistema %", "Valor esperado %",
    "Entrada %", "Entrada R$", "Banca antes", "Cotação de fechamento",
    "Vantagem no fechamento %", "Status", "Resultado R$", "Banca depois", "Origem", "Observação",
]

COLUNAS_CATALOGO = [
    "ID Coleta", "Registrado em", "Casa de apostas", "Liga", "Jogo", "Mandante", "Visitante",
    "Data do jogo", "Hora do jogo", "Mercado", "Seleção", "Cotação", "Banca no momento",
    "Perfil", "Origem", "Observação",
]

ARQUIVO_AUDITORIA = "logs/auditoria_tex_v19_1.csv"  # mantém histórico da V19
ARQUIVO_CATALOGO = "logs/catalogo_odds_tex_v19_1.csv"  # mantém histórico da V19
GOOGLE_SHEETS_WORKSHEET_CATALOGO = "catalogo_odds"
GOOGLE_SHEETS_WORKSHEET_AUDITORIA = "auditoria_entradas"
GOOGLE_CACHE_TTL_SEG = 300  # evita estourar quota do Google Sheets em reruns do Streamlit
GOOGLE_COOLDOWN_SEG = 75    # espera depois de erro de quota

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

# ============================================================
# UTILITÁRIOS
# ============================================================

def garantir_logs() -> None:
    os.makedirs("logs", exist_ok=True)


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
        return {"jogos": 0, "inicio": "-", "fim": "-", "times": 0}
    inicio = fim = "sem data"
    if "DataTemp" in df.columns and pd.to_datetime(df["DataTemp"], errors="coerce").notna().any():
        datas = pd.to_datetime(df["DataTemp"], errors="coerce").dropna()
        inicio = datas.min().strftime("%d/%m/%Y")
        fim = datas.max().strftime("%d/%m/%Y")
    home = df.get("Home", pd.Series(dtype=str)).dropna().astype(str)
    away = df.get("Away", pd.Series(dtype=str)).dropna().astype(str)
    times = sorted(set(home) | set(away))
    return {"jogos": int(len(df)), "inicio": inicio, "fim": fim, "times": int(len(times))}


def texto_base_dados(resumo: Dict[str, object], modo: str) -> str:
    return f"Base usada: {html.escape(str(modo))} | Período: {resumo.get('inicio', '-')} até {resumo.get('fim', '-')} | Jogos: {resumo.get('jogos', 0)} | Times: {resumo.get('times', 0)}"


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
    if "boa" in n:
        return "confidence-good"
    if "média" in n or "media" in n:
        return "confidence-mid"
    return "confidence-low"


def render_botao_confianca(conf: Dict[str, object]) -> None:
    nivel = str(conf.get("nível", "-"))
    motivos = str(conf.get("motivos", ""))
    classe = classe_confianca(nivel)
    icone = "🟢" if "boa" in nivel.lower() else ("🟠" if "média" in nivel.lower() or "media" in nivel.lower() else "🔴")
    st.markdown(
        f'''
        <div class="confidence-button {classe}">
            <span>{icone}</span><span>CONFIABILIDADE DA AMOSTRA: {html.escape(nivel.upper())}</span>
        </div>
        <div class="muted" style="margin-top:-6px;margin-bottom:10px;font-weight:700;">{html.escape(motivos)}</div>
        ''',
        unsafe_allow_html=True,
    )


def prioridade_aposta(
    prob: float,
    margem: float,
    stake: float,
    veredito: str,
    status_operacional: str = "",
) -> Tuple[str, int, str]:
    if str(veredito) != "VALOR (+EV)" or margem <= 0 or stake <= 0:
        return "—", 0, "sem prioridade"

    # Prioridade combina valor, chance e tamanho natural do Kelly.
    # Não bloqueia a entrada; só ordena a leitura.
    if stake >= 0.025 or (margem >= 0.12 and prob >= 0.45):
        prioridade, score, motivo = "🟢 Alta", 3, "melhor equilíbrio entre margem, probabilidade e stake"
    elif stake >= 0.010 or (margem >= 0.075 and prob >= 0.40):
        prioridade, score, motivo = "🟠 Média", 2, "valor válido, mas não é a melhor da tela"
    else:
        prioridade, score, motivo = "🔴 Fraca", 1, "valor existe, porém é a mais volátil/fraca da lista"

    # Correção V19.3.3: amostra baixa não pode aparecer como prioridade alta.
    # O valor matemático continua existindo, mas a leitura operacional fica limitada.
    status = str(status_operacional or "").upper()
    if "AMOSTRA BAIXA" in status and score > 2:
        return "🟠 Média", 2, "valor forte, mas amostra baixa limita a prioridade operacional"

    return prioridade, score, motivo


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
        avisos.append("Menos de 2.5 e Ambos marcam - Não são altamente correlacionados; não trate como duas entradas independentes.")

    if {"Mais de 2.5 gols", "Ambos marcam - Sim"}.issubset(mercados):
        avisos.append("Mais de 2.5 e Ambos marcam - Sim são altamente correlacionados; não trate como duas entradas independentes.")

    gols_casa = float(calc.get("gols_esperados_casa", 0.0) or 0.0)
    gols_fora = float(calc.get("gols_esperados_fora", 0.0) or 0.0)

    if "Vitória Fora" in mercados and ({"Menos de 2.5 gols", "Ambos marcam - Não"} & mercados) and gols_fora > gols_casa:
        avisos.append("Vitória Fora junto com Under/BTTS Não concentra exposição no roteiro de visitante superior e jogo controlado.")

    if "Vitória Casa" in mercados and ({"Menos de 2.5 gols", "Ambos marcam - Não"} & mercados) and gols_casa > gols_fora:
        avisos.append("Vitória Casa junto com Under/BTTS Não concentra exposição no roteiro de mandante superior e jogo controlado.")

    if len(aprovadas) >= 3:
        avisos.append("Há 3 ou mais entradas no mesmo jogo. Para gestão conservadora, escolha a principal ou reduza a exposição total do jogo.")

    return avisos


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


def calcular_planilha_pura(df: pd.DataFrame, time_casa: str, time_fora: str) -> Dict[str, object]:
    media_gols_casa_liga = max(0.20, float(pd.to_numeric(df["HG"], errors="coerce").mean()))
    media_gols_fora_liga = max(0.20, float(pd.to_numeric(df["AG"], errors="coerce").mean()))

    jogos_casa = df[df["Home"].astype(str) == str(time_casa)].copy()
    jogos_fora = df[df["Away"].astype(str) == str(time_fora)].copy()

    gols_feitos_casa = media_simples(jogos_casa["HG"], media_gols_casa_liga)
    gols_sofridos_casa = media_simples(jogos_casa["AG"], media_gols_fora_liga)
    gols_feitos_fora = media_simples(jogos_fora["AG"], media_gols_fora_liga)
    gols_sofridos_fora = media_simples(jogos_fora["HG"], media_gols_casa_liga)

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

    probabilidades = {
        "Vitória Casa": prob_casa,
        "Empate": prob_empate,
        "Vitória Fora": prob_fora,
        "Mais de 2.5 gols": prob_over25,
        "Menos de 2.5 gols": prob_under25,
        "Ambos marcam - Sim": prob_btts_sim,
        "Ambos marcam - Não": prob_btts_nao,
    }

    cantos = calcular_cantos_se_existir(df, time_casa, time_fora)

    return {
        "media_gols_casa_liga": media_gols_casa_liga,
        "media_gols_fora_liga": media_gols_fora_liga,
        "jogos_casa": int(len(jogos_casa)),
        "jogos_fora": int(len(jogos_fora)),
        "amostra_minima": int(min(len(jogos_casa), len(jogos_fora))),
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
        "probabilidades": probabilidades,
        "cantos": cantos,
    }


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
    politica_amostra_baixa: str = "Avisar e reduzir stake",
    fator_reducao_amostra: float = 0.50,
) -> pd.DataFrame:
    """
    Avalia valor como a planilha, mas separa duas coisas que não podem ficar misturadas:
    1) Valor matemático: se a odd real está acima da odd justa com margem mínima.
    2) Status operacional: se a entrada está liberada, reduzida, apenas estudo ou bloqueada.

    Isso evita a burrice visual de mostrar margem +EV forte e ao mesmo tempo esconder que
    o motivo do corte foi só amostra baixa.
    """
    linhas = []
    politica = str(politica_amostra_baixa or "Avisar e reduzir stake").strip()
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
        stake_pct_base = min(kelly, teto_por_entrada)
        tem_valor = margem > margem_minima
        valor_matematico = "SIM" if tem_valor else "NÃO"

        if tem_valor:
            if amostra_ok:
                veredito = "VALOR (+EV)"
                status_operacional = "LIBERADO"
                entrada_pct = stake_pct_base
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
                    veredito = "VALOR (+EV)"
                    status_operacional = "AMOSTRA BAIXA — STAKE REDUZIDA"
                    entrada_pct = stake_pct_base * fator_reducao_amostra
                    motivo = (
                        (motivo_bloqueio_operacional or "amostra mínima insuficiente")
                        + f" | valor matemático +EV; stake reduzida para {fmt_pct(fator_reducao_amostra, 0)} da stake original."
                    )
        else:
            veredito = "SEM VALOR"
            status_operacional = "SEM VALOR"
            entrada_pct = 0.0
            motivo = "odd real abaixo ou muito próxima da odd justa"

        prioridade_txt, prioridade_score, prioridade_motivo = prioridade_aposta(prob, margem, entrada_pct, veredito, status_operacional)
        linhas.append({
            "Mercado": mercado,
            "Prioridade": prioridade_txt,
            "Valor matemático": valor_matematico,
            "Status operacional": status_operacional,
            "Probabilidade": prob,
            "Odd justa": odd_justa,
            "Odd real": float(odd),
            "Margem +EV": margem,
            "Veredito": veredito,
            "Stake %": entrada_pct,
            "Entrada R$": float(banca) * entrada_pct if banca > 0 else 0.0,
            "Motivo": motivo,
            "_prioridade_score": prioridade_score,
            "_prioridade_motivo": prioridade_motivo,
        })

    df = pd.DataFrame(linhas)
    if df.empty:
        return df

    # O limite total do jogo só vale para entradas com stake efetiva.
    mask_ev = df["Veredito"].eq("VALOR (+EV)") & (pd.to_numeric(df["Stake %"], errors="coerce").fillna(0.0) > 0)
    total_pct = float(df.loc[mask_ev, "Stake %"].sum())
    if total_pct > teto_por_jogo > 0:
        fator = teto_por_jogo / total_pct
        df.loc[mask_ev, "Stake %"] = df.loc[mask_ev, "Stake %"] * fator
        df.loc[mask_ev, "Entrada R$"] = df.loc[mask_ev, "Stake %"] * float(banca)
        df.loc[mask_ev, "Motivo"] = df.loc[mask_ev, "Motivo"] + " | stake ajustada proporcionalmente pelo limite total do jogo"
        for idx, row in df.loc[mask_ev].iterrows():
            prioridade_txt, prioridade_score, prioridade_motivo = prioridade_aposta(
                float(row.get("Probabilidade", 0.0)),
                float(row.get("Margem +EV", 0.0)),
                float(df.at[idx, "Stake %"]),
                str(row.get("Veredito", "")),
                str(row.get("Status operacional", "")),
            )
            df.at[idx, "Prioridade"] = prioridade_txt
            df.at[idx, "_prioridade_score"] = prioridade_score
            df.at[idx, "_prioridade_motivo"] = prioridade_motivo

    ordem_status = {
        "LIBERADO": 0,
        "AMOSTRA BAIXA — STAKE REDUZIDA": 1,
        "AMOSTRA BAIXA — ESTUDO": 2,
        "SEM VALOR": 3,
        "AMOSTRA BAIXA — BLOQUEADO": 4,
    }
    df["_ordem_status"] = df["Status operacional"].map(ordem_status).fillna(9)
    df = (
        df.sort_values(["_ordem_status", "_prioridade_score", "Margem +EV"], ascending=[True, False, False])
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
    amostra = int(modelo.get("amostra_minima", 0))
    margem_max = 0.0
    if resultados is not None and not resultados.empty and "Margem +EV" in resultados.columns:
        evs = pd.to_numeric(resultados["Margem +EV"], errors="coerce").dropna()
        if not evs.empty:
            margem_max = float(evs.max())

    pontos = 0
    motivos = []

    if amostra >= 8:
        pontos += 2
        motivos.append("amostra casa/fora boa")
    elif amostra >= 5:
        pontos += 1
        motivos.append("amostra casa/fora mínima")
    else:
        motivos.append("amostra baixa")

    if margem_max >= 0.15:
        pontos += 2
        motivos.append("margem +EV forte")
    elif margem_max > 0.00:
        pontos += 1
        motivos.append("margem +EV positiva, mas não larga")
    else:
        motivos.append("sem margem positiva relevante")

    total_esperado = float(modelo.get("gols_esperados_casa", 0.0)) + float(modelo.get("gols_esperados_fora", 0.0))
    if 1.20 <= total_esperado <= 4.20:
        pontos += 1
        motivos.append("gols esperados dentro de faixa normal")
    else:
        motivos.append("gols esperados em faixa extrema")

    if pontos >= 4:
        nivel = "Boa"
    elif pontos >= 2:
        nivel = "Média"
    else:
        nivel = "Baixa"

    return {"nível": nivel, "pontos": pontos, "motivos": "; ".join(motivos)}


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
    fechadas = base[base["Status"].isin(["Green", "Red", "Void", "Cashout"])].copy()
    if fechadas.empty:
        return {}

    fechadas["Green_bin"] = (fechadas["Status"] == "Green").astype(int)
    fechadas["Red_bin"] = (fechadas["Status"] == "Red").astype(int)
    fechadas["Faixa odd"] = fechadas["Cotação de entrada"].apply(faixa_odd)

    def agrupar(campo: str) -> pd.DataFrame:
        g = fechadas.groupby(campo, dropna=False).agg(
            Entradas=("ID", "count"),
            Greens=("Green_bin", "sum"),
            Reds=("Red_bin", "sum"),
            Apostado=("Entrada R$", "sum"),
            Resultado=("Resultado R$", "sum"),
        ).reset_index()
        g["Taxa acerto"] = np.where((g["Greens"] + g["Reds"]) > 0, g["Greens"] / (g["Greens"] + g["Reds"]), 0.0)
        g["ROI"] = np.where(g["Apostado"] > 0, g["Resultado"] / g["Apostado"], 0.0)
        return g.sort_values("Resultado", ascending=False)

    geral = pd.DataFrame([{
        "Entradas fechadas": len(fechadas),
        "Greens": int(fechadas["Green_bin"].sum()),
        "Reds": int(fechadas["Red_bin"].sum()),
        "Apostado": float(fechadas["Entrada R$"].sum()),
        "Resultado": float(fechadas["Resultado R$"].sum()),
        "Taxa acerto": float(fechadas["Green_bin"].sum() / max(1, (fechadas["Green_bin"].sum() + fechadas["Red_bin"].sum()))),
        "ROI": float(fechadas["Resultado R$"].sum() / max(0.01, fechadas["Entrada R$"].sum())),
    }])

    return {
        "geral": geral,
        "por_mercado": agrupar("Mercado"),
        "por_liga": agrupar("Liga"),
        "por_faixa_odd": agrupar("Faixa odd"),
    }


def formatar_tabela_resultados(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in ["_prioridade_score", "_prioridade_motivo"]:
        if col in out.columns:
            out = out.drop(columns=[col])
    out["Probabilidade"] = out["Probabilidade"].map(lambda x: fmt_pct(x, 1))
    out["Odd justa"] = out["Odd justa"].map(lambda x: "-" if not np.isfinite(x) else fmt_num(x, 2))
    out["Odd real"] = out["Odd real"].map(lambda x: fmt_num(x, 2))
    out["Margem +EV"] = out["Margem +EV"].map(lambda x: fmt_pct(x, 1))
    out["Stake %"] = out["Stake %"].map(lambda x: fmt_pct(x, 2))
    out["Entrada R$"] = out["Entrada R$"].map(fmt_dinheiro)
    return out

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
                return odds_alvo, f"✅ Odds extraídas da casa selecionada na API: {casa_alvo_txt}. Ainda assim, confira antes de apostar."

    pools = {m: [] for m in MERCADOS_NUCLEO}
    for book in bookmakers:
        _popular_pools_com_bookmaker(pools, book, casa_api, fora_api)
    odds_mediana = _pools_para_odds(pools)

    if deve_priorizar_casa:
        aviso = (
            f"⚠️ A API não encontrou odds da casa selecionada ({casa_alvo_txt}). "
            "Estou mostrando a mediana do mercado apenas como referência. "
            "Para apostar, confira e digite manualmente a odd da sua casa."
        )
    else:
        aviso = "ℹ️ Casa 'Outra' selecionada: a API mostra mediana do mercado. Para aposta real, prefira digitar a odd manualmente."

    return odds_mediana, aviso

# ============================================================
# GOOGLE SHEETS OPCIONAL
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
        service = _segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        client_email = str(service.get("client_email", "")).strip()
        return {
            "spreadsheet_id": spreadsheet_id,
            "worksheet_catalogo": worksheet_catalogo,
            "worksheet_auditoria": worksheet_auditoria,
            "client_email": client_email,
            "configurado": bool(spreadsheet_id and client_email),
        }
    except Exception:
        return {
            "spreadsheet_id": "",
            "worksheet_catalogo": GOOGLE_SHEETS_WORKSHEET_CATALOGO,
            "worksheet_auditoria": GOOGLE_SHEETS_WORKSHEET_AUDITORIA,
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
        st.warning(f"Google Sheets não conectou; usando backup local. Detalhe: {exc}")
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


def obter_aba(nome: str, colunas: List[str], linhas: int = 1000):
    """Obtém ou cria uma aba no Google Sheets sem fazer leituras desnecessárias.

    V19.3.3: o Streamlit reroda o script a cada clique. Antes, o app lia o Google
    Sheets várias vezes por rerun e batia quota de leitura. Agora o Google fica em
    modo economia: leitura só por cache ou sincronização manual, com cooldown quando
    aparecer quota 429.
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

        try:
            return planilha.worksheet(nome_limpo)
        except WorksheetNotFound:
            try:
                aba = planilha.add_worksheet(
                    title=nome_limpo,
                    rows=linhas,
                    cols=max(20, len(colunas) + 4),
                )
                # escreve cabeçalho somente na criação; não lê a aba só para checar vazio
                aba.update("A1", [colunas], value_input_option="USER_ENTERED")
                return aba
            except Exception as exc_criar:
                if "already exists" in str(exc_criar).lower() or "já existe" in str(exc_criar).lower():
                    return planilha.worksheet(nome_limpo)
                raise exc_criar
    except Exception as exc:
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
            st.warning(
                f"Google Sheets bateu limite de quota. Vou usar cache/backup local por {_segundos_cooldown_google()}s. "
                "Isso não altera o motor da planilha."
            )
        else:
            st.warning(f"Não consegui acessar a aba {nome_limpo} no Google Sheets. Detalhe: {exc}")
        return None


def carregar_google(nome: str, colunas: List[str], force: bool = False) -> Optional[pd.DataFrame]:
    """Carrega uma aba do Google com cache agressivo.

    Por padrão NÃO lê o Google a cada rerun. Para forçar leitura, use force=True
    através dos botões de sincronização manual.
    """
    cache = _pegar_cache_google(nome, colunas, aceitar_vencido=True)

    # Sem force, usa cache se existir e evita chamada ao Google. Se não existir cache,
    # devolve None para cair no backup local. Isso impede estouro de quota no sidebar.
    if not force:
        return cache

    if _google_cooldown_ativo():
        if cache is not None:
            st.info(f"Google em cooldown por {_segundos_cooldown_google()}s; usando última cópia em cache.")
            return cache
        return None

    aba = obter_aba(nome, colunas)
    if aba is None:
        return cache

    try:
        valores = aba.get_all_values()
        if not valores:
            df = pd.DataFrame(columns=colunas)
            try:
                aba.update("A1", [colunas], value_input_option="USER_ENTERED")
            except Exception:
                pass
        else:
            cabecalho = [str(c).strip() for c in valores[0]]
            linhas = valores[1:]
            df = pd.DataFrame(linhas, columns=cabecalho)
            df = normalizar_colunas(df, colunas)
        _salvar_cache_google(nome, df, colunas)
        return df
    except Exception as exc:
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
            st.warning(
                f"Google Sheets bateu quota de leitura. Usando cache/backup local por {_segundos_cooldown_google()}s."
            )
        else:
            st.warning(f"Não consegui ler {nome} no Google Sheets. Detalhe: {exc}")
        return cache


def salvar_google(nome: str, df: pd.DataFrame, colunas: List[str]) -> bool:
    if _google_cooldown_ativo():
        _salvar_cache_google(nome, df, colunas)
        return False

    aba = obter_aba(nome, colunas)
    if aba is None:
        _salvar_cache_google(nome, df, colunas)
        return False

    try:
        base = normalizar_colunas(df, colunas).astype(str)
        valores = [colunas] + base.values.tolist()
        aba.clear()
        aba.update("A1", valores, value_input_option="USER_ENTERED")
        _salvar_cache_google(nome, base, colunas)
        return True
    except Exception as exc:
        _salvar_cache_google(nome, df, colunas)
        if _erro_quota_google(exc):
            _ativar_cooldown_google(exc)
            st.warning(
                f"Google Sheets bateu quota de gravação. Salvei no backup local/cache e vou tentar de novo depois."
            )
        else:
            st.warning(f"Não consegui salvar {nome} no Google Sheets. Detalhe: {exc}")
        return False

# ============================================================
# AUDITORIA E CATÁLOGO
# ============================================================

def carregar_auditoria_local() -> pd.DataFrame:
    garantir_logs()
    if os.path.exists(ARQUIVO_AUDITORIA):
        try:
            return normalizar_colunas(pd.read_csv(ARQUIVO_AUDITORIA), COLUNAS_AUDITORIA)
        except Exception:
            return pd.DataFrame(columns=COLUNAS_AUDITORIA)
    return pd.DataFrame(columns=COLUNAS_AUDITORIA)


def salvar_auditoria(df: pd.DataFrame) -> str:
    garantir_logs()
    base = normalizar_colunas(df, COLUNAS_AUDITORIA)
    base.to_csv(ARQUIVO_AUDITORIA, index=False)
    if google_configurado() and salvar_google(obter_config_google()["worksheet_auditoria"], base, COLUNAS_AUDITORIA):
        return "Google Sheets + backup local"
    return "backup local"


def carregar_auditoria(force_google: bool = False) -> pd.DataFrame:
    local = carregar_auditoria_local()
    if google_configurado():
        cfg = obter_config_google()
        df_g = carregar_google(cfg["worksheet_auditoria"], COLUNAS_AUDITORIA, force=force_google)
        if df_g is not None:
            if df_g.empty and force_google and not local.empty:
                # só empurra backup local para o Google quando o usuário pediu sincronização
                salvar_google(cfg["worksheet_auditoria"], local, COLUNAS_AUDITORIA)
                return local
            return df_g
    return local


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
) -> pd.DataFrame:
    base = normalizar_colunas(auditoria, COLUNAS_AUDITORIA)
    nova = {
        "ID": str(uuid.uuid4())[:8],
        "Registrado em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Liga": liga,
        "Jogo": jogo,
        "Casa de apostas": casa_apostas,
        "Mercado": mercado,
        "Cotação de entrada": round(float(odd), 4),
        "Cotação justa": round(float(odd_justa), 4) if np.isfinite(odd_justa) else "",
        "Chance pelo sistema %": round(float(prob) * 100, 2),
        "Valor esperado %": round(float(margem) * 100, 2),
        "Entrada %": round(float(entrada_pct) * 100, 3),
        "Entrada R$": round(float(entrada_rs), 2),
        "Banca antes": round(float(banca_antes), 2),
        "Cotação de fechamento": "",
        "Vantagem no fechamento %": "",
        "Status": "Pendente",
        "Resultado R$": 0.0,
        "Banca depois": "",
        "Origem": origem,
        "Observação": observacao,
    }
    return pd.concat([base, pd.DataFrame([nova])], ignore_index=True)


def calcular_resultado(status: str, entrada_rs: float, odd: float, cashout: float = 0.0) -> float:
    status = str(status)
    if status == "Green":
        return float(entrada_rs) * (float(odd) - 1.0)
    if status == "Red":
        return -float(entrada_rs)
    if status == "Void":
        return 0.0
    if status == "Cashout":
        return float(cashout) - float(entrada_rs)
    return 0.0


def carregar_catalogo_local() -> pd.DataFrame:
    garantir_logs()
    if os.path.exists(ARQUIVO_CATALOGO):
        try:
            return normalizar_colunas(pd.read_csv(ARQUIVO_CATALOGO), COLUNAS_CATALOGO)
        except Exception:
            return pd.DataFrame(columns=COLUNAS_CATALOGO)
    return pd.DataFrame(columns=COLUNAS_CATALOGO)


def salvar_catalogo(df: pd.DataFrame) -> str:
    garantir_logs()
    base = normalizar_colunas(df, COLUNAS_CATALOGO)
    base.to_csv(ARQUIVO_CATALOGO, index=False)
    if google_configurado() and salvar_google(obter_config_google()["worksheet_catalogo"], base, COLUNAS_CATALOGO):
        return "Google Sheets + backup local"
    return "backup local"


def carregar_catalogo(force_google: bool = False) -> pd.DataFrame:
    local = carregar_catalogo_local()
    if google_configurado():
        cfg = obter_config_google()
        df_g = carregar_google(cfg["worksheet_catalogo"], COLUNAS_CATALOGO, force=force_google)
        if df_g is not None:
            if df_g.empty and force_google and not local.empty:
                salvar_google(cfg["worksheet_catalogo"], local, COLUNAS_CATALOGO)
                return local
            return df_g
    return local


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
) -> pd.DataFrame:
    base = normalizar_colunas(catalogo, COLUNAS_CATALOGO)
    coleta = str(uuid.uuid4())[:8]
    linhas = []
    for mercado, odd in odds.items():
        if not odd_valida(odd):
            continue
        linhas.append({
            "ID Coleta": coleta,
            "Registrado em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
    return base

# ============================================================
# UI
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">TEX STATISTICS V19.3.3</div>
        <div class="hero-sub">
            Pure Sheet Manual: ataque/defesa, mando, Poisson, odd justa, margem +EV e Kelly fracionado.
            Padrão fiel à planilha: temporada atual, margem mínima prática de 3% e modo manual como prioridade.
            Sem firula subjetiva. Diagnóstico, scout e auditoria informam — não bloqueiam o valor da planilha.
        </div>
        <span class="chip">Pure Sheet Manual</span>
        <span class="chip">Temporada atual</span>
        <span class="chip">+EV com margem</span>
        <span class="chip">Poisson auditável</span>
        <span class="chip">Scout opcional</span>
        <span class="chip">Sem hard blocks subjetivos</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Banca")
    banca_inicial = st.number_input("Banca inicial da auditoria", min_value=0.0, value=1000.0, step=50.0)

    cfg_sidebar = obter_config_google()
    force_sync_sidebar = False
    if cfg_sidebar.get("configurado"):
        st.caption("Google Sheets em modo econômico: não leio a planilha a cada clique para não estourar quota.")
        force_sync_sidebar = st.button("🔄 Sincronizar auditoria agora", key="sync_auditoria_sidebar")
        if _google_cooldown_ativo():
            st.warning(f"Google em espera por {_segundos_cooldown_google()}s. Usando cache/backup local.")

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
        data_inicio_recorte = st.date_input("Data inicial da base", value=date(ano_atual, 1, 1))
        data_fim_recorte = st.date_input("Data final da base", value=date.today())
    amostra_minima = st.slider("Amostra mínima casa/fora", 3, 12, 5, 1)
    politica_amostra_baixa = st.selectbox(
        "Política para amostra baixa",
        ["Avisar e reduzir stake", "Bloquear entrada", "Mostrar só para estudo"],
        index=0,
        help="Quando a amostra casa/fora fica abaixo do mínimo. Padrão: não zera o valor matemático; só reduz stake e avisa.",
    )
    fator_reducao_amostra_pct = st.slider(
        "Stake em amostra baixa",
        min_value=10.0,
        max_value=100.0,
        value=50.0,
        step=5.0,
        format="%.0f%%",
        help="Usado apenas quando a política é 'Avisar e reduzir stake'. Ex: 50% = metade da stake sugerida.",
    )
    fator_reducao_amostra = fator_reducao_amostra_pct / 100.0

    st.divider()
    st.header("Stake")
    fracao_kelly = st.select_slider(
        "Fração de Kelly",
        options=[0.10, 0.125, 0.20, 0.25, 0.33, 0.50],
        value=0.25,
        format_func=lambda x: {0.10: "1/10 Kelly", 0.125: "1/8 Kelly", 0.20: "1/5 Kelly", 0.25: "1/4 Kelly", 0.33: "1/3 Kelly", 0.50: "1/2 Kelly"}.get(x, str(x)),
    )
    margem_minima_pct = st.slider(
        "Margem mínima +EV",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        format="%.1f%%",
        help="0% só para estudo; 2% volume; 3% padrão honesto; 5% conservador.",
    )
    margem_minima = margem_minima_pct / 100.0
    teto_por_entrada_pct = st.slider("Teto por entrada", 0.5, 10.0, 3.0, 0.5, format="%.1f%%")
    teto_por_jogo_pct = st.slider("Teto total no jogo", 1.0, 20.0, 6.0, 0.5, format="%.1f%%")
    teto_por_entrada = teto_por_entrada_pct / 100.0
    teto_por_jogo = teto_por_jogo_pct / 100.0
    st.caption("Padrão recomendado: 1/4 Kelly, margem mínima 3%, teto de 3% por entrada e 6% por jogo. O recorte padrão agora é temporada atual, não histórico gigante.")

    st.divider()
    st.header("Odds")
    casa_apostas = st.selectbox("Casa de apostas", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"])
    chave_api = st.text_input("Chave The Odds API", value=os.getenv("ODDS_API_KEY", ""), type="password")

aba_analisar, aba_diagnostico, aba_scout, aba_auditoria, aba_catalogo, aba_calendario = st.tabs(["🎯 Analisar jogo", "🧪 Diagnóstico da liga", "🔎 Scout opcional", "📒 Auditoria", "📊 Catálogo", "🗓️ Ligas"])

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
    modo = st.radio("Modo de análise", ["Manual", "Automático pela API"], horizontal=True)

    odds: Dict[str, float] = {}
    time_casa = times_liga[0]
    time_fora = times_liga[min(1, len(times_liga) - 1)]
    jogo_nome = ""
    origem = modo
    data_jogo_catalogo = date.today()
    hora_jogo_catalogo = ""
    botao_analisar = False

    if modo == "Manual":
        st.markdown("### Jogo")
        st.info("Modo principal recomendado: digite as odds reais da casa onde você vai apostar. Não misture Pixbet com odds de outras casas no mesmo jogo.")
        c1, c2 = st.columns(2)
        with c1:
            time_casa = st.selectbox("Mandante", times_liga, key="manual_casa")
        with c2:
            time_fora = st.selectbox("Visitante", times_liga, key="manual_fora")

        c1, c2 = st.columns(2)
        with c1:
            data_jogo_catalogo = st.date_input("Data do jogo/mercado", value=date.today(), key="data_jogo")
        with c2:
            hora_jogo_catalogo = st.text_input("Hora do jogo", value="", placeholder="ex: 15:45", key="hora_jogo")

        if time_casa == time_fora:
            st.warning("Mandante e visitante não podem ser o mesmo time.")
        else:
            jogo_nome = f"{time_casa} x {time_fora}"
            odds = coletar_odds_manuais("manual")
            c1, c2 = st.columns(2)
            with c1:
                botao_analisar = st.button("ANALISAR PELA PLANILHA", type="primary")
            with c2:
                if st.button("SALVAR ODDS NO CATÁLOGO"):
                    if not odds:
                        st.error("Nenhuma odd válida para salvar.")
                    else:
                        catalogo = carregar_catalogo()
                        catalogo = registrar_odds_catalogo(
                            catalogo, liga_sel, jogo_nome, time_casa, time_fora, casa_apostas, odds,
                            banca_usada, "Planilha Pura", data_jogo_catalogo, hora_jogo_catalogo,
                            "Manual", "Odds salvas sem obrigação de aposta",
                        )
                        destino = salvar_catalogo(catalogo)
                        st.success(f"Odds salvas. Destino: {destino}.")

    else:
        if not chave_api:
            st.warning("Informe a chave da API ou use o modo Manual.")
        elif liga_sel not in LIGAS_API:
            st.warning("Liga sem mapeamento na API. Use o modo Manual.")
        else:
            jogos_api = buscar_odds_api(chave_api, LIGAS_API[liga_sel])
            if not jogos_api:
                st.warning("A API não retornou jogos/odds agora. Use Manual.")
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
                    st.warning("A API respondeu, mas não há partida pré-jogo disponível.")
                else:
                    escolha = st.selectbox("Partida", list(opcoes.keys()))
                    jogo_api = opcoes[escolha]
                    casa_api = jogo_api.get("home_team", "")
                    fora_api = jogo_api.get("away_team", "")
                    match_casa, score_casa = casar_time_seguro(casa_api, times_liga)
                    match_fora, score_fora = casar_time_seguro(fora_api, times_liga)

                    if match_casa is None or match_fora is None:
                        st.error("Não consegui casar com segurança os nomes da API com a base. Use modo Manual. O app não vai chutar time.")
                        st.write({"API mandante": casa_api, "API visitante": fora_api})
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
                        st.info(f"Mercados com odd encontrados: {len(odds)}")
                        botao_analisar = st.button("ANALISAR PELA PLANILHA", type="primary")

    if botao_analisar:
        if not odds:
            st.error("Nenhuma odd válida foi informada/encontrada.")
        elif time_casa == time_fora:
            st.error("Mandante e visitante não podem ser iguais.")
        else:
            calc = calcular_planilha_pura(df_liga, time_casa, time_fora)
            amostra_ok = int(calc["amostra_minima"]) >= int(amostra_minima)
            motivo_bloqueio = ""
            if not amostra_ok:
                motivo_bloqueio = f"amostra baixa: {time_casa} em casa {calc['jogos_casa']} jogo(s), {time_fora} fora {calc['jogos_fora']} jogo(s). Mínimo configurado: {amostra_minima}."

            resultados = avaliar_valor_planilha(
                calc["probabilidades"], odds, banca_usada, fracao_kelly, margem_minima,
                teto_por_entrada, teto_por_jogo, amostra_ok, motivo_bloqueio,
                politica_amostra_baixa=politica_amostra_baixa,
                fator_reducao_amostra=fator_reducao_amostra,
            )

            st.session_state["ultima_analise_v19"] = {
                "id": str(pd.Timestamp.now().value),
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
                "amostra_ok": amostra_ok,
                "motivo_bloqueio": motivo_bloqueio,
                "config": {
                    "janela": modo_recorte,
                    "periodo_base": resumo_base_dados(df_liga),
                    "fracao_kelly": fracao_kelly,
                    "margem_minima": margem_minima,
                    "teto_por_entrada": teto_por_entrada,
                    "teto_por_jogo": teto_por_jogo,
                    "amostra_minima": amostra_minima,
                    "politica_amostra_baixa": politica_amostra_baixa,
                    "fator_reducao_amostra": fator_reducao_amostra,
                },
            }

    analise = st.session_state.get("ultima_analise_v19")
    if analise:
        calc = analise["calc"]
        resultados = pd.DataFrame(analise["resultados"])
        aprovadas = resultados[(resultados["Veredito"].eq("VALOR (+EV)")) & (pd.to_numeric(resultados["Stake %"], errors="coerce").fillna(0.0) > 0)].copy() if not resultados.empty else pd.DataFrame()
        if not resultados.empty and "Valor matemático" in resultados.columns:
            valores_matematicos = resultados[resultados["Valor matemático"].astype(str).eq("SIM")].copy()
        else:
            valores_matematicos = pd.DataFrame()

        st.markdown("---")
        st.subheader(f"Análise — {analise['jogo']}")

        politica_atual = str(analise.get("config", {}).get("politica_amostra_baixa", "Avisar e reduzir stake"))
        fator_amostra_atual = float(analise.get("config", {}).get("fator_reducao_amostra", 0.50))
        if not analise.get("amostra_ok", False):
            if "Bloquear" in politica_atual:
                st.error(f"Amostra baixa: {analise.get('motivo_bloqueio', '')} Política atual: bloquear entrada.")
            elif "estudo" in politica_atual.lower():
                st.warning(f"Amostra baixa: {analise.get('motivo_bloqueio', '')} Política atual: mostrar só para estudo.")
            else:
                st.warning(f"Amostra baixa: {analise.get('motivo_bloqueio', '')} Política atual: permitir com stake reduzida para {fmt_pct(fator_amostra_atual, 0)}.")
        else:
            st.success("Amostra operacional aprovada. A partir daqui, quem manda é a margem +EV.")

        periodo_base = analise.get("config", {}).get("periodo_base") or resumo_base_dados(df_liga)
        st.markdown(f'<div class="base-info">{html.escape(texto_base_dados(periodo_base, analise.get("config", {}).get("janela", "-")))}</div>', unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            render_stat_card("Gols esp. casa", fmt_num(calc["gols_esperados_casa"], 2), analise["time_casa"], "⚽")
        with c2:
            render_stat_card("Gols esp. fora", fmt_num(calc["gols_esperados_fora"], 2), analise["time_fora"], "⚽")
        with c3:
            render_stat_card("Amostra casa", calc["jogos_casa"], "jogos do mandante em casa", "🏠")
        with c4:
            render_stat_card("Amostra fora", calc["jogos_fora"], "jogos do visitante fora", "🛫")
        with c5:
            render_stat_card("Entradas +EV", len(aprovadas), "pela margem configurada", "✅")

        conf = classificar_confianca_estimativa(calc, resultados)
        render_botao_confianca(conf)
        st.info("Confiabilidade é aviso operacional, não bloqueio. A decisão matemática continua sendo margem +EV, odd justa e Kelly.")

        with st.expander("Ver cálculo de forças da planilha"):
            dados_forca = pd.DataFrame([
                {"Item": "Média gols casa liga", "Valor": calc["media_gols_casa_liga"]},
                {"Item": f"{analise['time_casa']} gols feitos em casa", "Valor": calc["gols_feitos_casa"]},
                {"Item": f"{analise['time_casa']} gols sofridos em casa", "Valor": calc["gols_sofridos_casa"]},
                {"Item": f"{analise['time_casa']} força ataque casa", "Valor": calc["forca_ataque_casa"]},
                {"Item": f"{analise['time_casa']} força defesa casa", "Valor": calc["forca_defesa_casa"]},
                {"Item": "Média gols fora liga", "Valor": calc["media_gols_fora_liga"]},
                {"Item": f"{analise['time_fora']} gols feitos fora", "Valor": calc["gols_feitos_fora"]},
                {"Item": f"{analise['time_fora']} gols sofridos fora", "Valor": calc["gols_sofridos_fora"]},
                {"Item": f"{analise['time_fora']} força ataque fora", "Valor": calc["forca_ataque_fora"]},
                {"Item": f"{analise['time_fora']} força defesa fora", "Valor": calc["forca_defesa_fora"]},
            ])
            dados_forca["Valor"] = dados_forca["Valor"].map(lambda x: fmt_num(float(x), 3))
            st.dataframe(dados_forca, use_container_width=True, hide_index=True)

        if calc.get("cantos"):
            with st.expander("Cantos — leitura simples da planilha"):
                cantos = calc["cantos"]
                linha_cantos = st.number_input("Linha total de cantos da casa", min_value=0.0, value=10.0, step=0.5)
                dif = float(cantos["cantos_total"]) - float(linha_cantos)
                if abs(dif) < 0.75:
                    msg = "RISCO ALTO / linha justa demais"
                elif dif > 0:
                    msg = "Tendência Over cantos"
                else:
                    msg = "Tendência Under cantos"
                st.write(f"Previsão total: **{fmt_num(cantos['cantos_total'], 2)}** | Linha: **{fmt_num(linha_cantos, 1)}** | Diferença: **{fmt_num(dif, 2)}** | {msg}")

        if resultados.empty:
            st.warning("Nenhum mercado com odd válida para comparar.")
        else:
            st.markdown("### Tabela da planilha")
            st.dataframe(formatar_tabela_resultados(resultados), use_container_width=True, hide_index=True)

            if not aprovadas.empty:
                total_entrada = float(aprovadas["Entrada R$"].sum())
                st.success(f"A planilha encontrou {len(aprovadas)} mercado(s) com VALOR (+EV). Total sugerido: {fmt_dinheiro(total_entrada)}.")

                avisos_correlacao = detectar_correlacao_operacional(aprovadas, calc)
                if avisos_correlacao:
                    st.warning("⚠️ Exposição correlacionada no mesmo jogo: " + " ".join(avisos_correlacao))

                for _, r in aprovadas.iterrows():
                    prioridade = str(r.get("Prioridade", "🟠 Média"))
                    prioridade_extra = str(r.get("_prioridade_motivo", "ordem de prioridade"))
                    prioridade_cls = prioridade_classe(prioridade)
                    st.markdown(
                        f"""
                        <div class="card-ev">
                            <div class="priority-badge {prioridade_cls}">{html.escape(prioridade)} — {html.escape(prioridade_extra)}</div>
                            <div class="big-green">VALOR (+EV)</div>
                            <h3>{html.escape(str(r['Mercado']))}</h3>
                            <p><b>Status operacional:</b> {html.escape(str(r.get('Status operacional', 'LIBERADO')))} | <b>Valor matemático:</b> {html.escape(str(r.get('Valor matemático', 'SIM')))}</p>
                            <p><b>Probabilidade:</b> {fmt_pct(float(r['Probabilidade']), 1)} | <b>Odd justa:</b> {fmt_num(float(r['Odd justa']), 2)} | <b>Odd real:</b> {fmt_num(float(r['Odd real']), 2)}</p>
                            <p><b>Margem:</b> {fmt_pct(float(r['Margem +EV']), 1)} | <b>Stake:</b> {fmt_pct(float(r['Stake %']), 2)} | <b>Entrada:</b> {fmt_dinheiro(float(r['Entrada R$']))}</p>
                            <p class="muted"><b>Motivo:</b> {html.escape(str(r['Motivo']))}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                if not valores_matematicos.empty:
                    st.warning("Existe valor matemático (+EV) na tabela, mas a política operacional atual não liberou entrada com stake. Veja as colunas 'Valor matemático' e 'Status operacional'.")
                else:
                    st.info("Nenhum mercado ficou +EV com as odds informadas.")

        if not aprovadas.empty:
            st.markdown("---")
            st.markdown("### Registrar entradas +EV na auditoria")
            with st.form(key=f"form_registrar_v19_{analise['id']}"):
                escolhidas_idx = []
                for idx, r in aprovadas.iterrows():
                    label = f"Registrar {r['Mercado']} — odd {fmt_num(float(r['Odd real']), 2)} — {fmt_dinheiro(float(r['Entrada R$']))}"
                    if st.checkbox(label, value=True, key=f"check_{analise['id']}_{idx}"):
                        escolhidas_idx.append(idx)
                obs = st.text_area("Observação", value="", placeholder="Ex: Pixbet, odd conferida, escalação ok...", key=f"obs_{analise['id']}")
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
                            odd=float(r["Odd real"]),
                            prob=float(r["Probabilidade"]),
                            odd_justa=float(r["Odd justa"]),
                            margem=float(r["Margem +EV"]),
                            entrada_pct=float(r["Stake %"]),
                            entrada_rs=float(r["Entrada R$"]),
                            banca_antes=float(analise["banca"]),
                            origem=str(analise["origem"]),
                            observacao=(obs + f" | V19.3.3 Pure Sheet Manual | Janela {analise['config']['janela']} | Kelly {analise['config']['fracao_kelly']} | Amostra: {analise['config'].get('politica_amostra_baixa', '-')}").strip(),
                        )
                    destino = salvar_auditoria(auditoria)
                    st.success(f"Entradas salvas. Destino: {destino}.")

        if st.button("LIMPAR ÚLTIMA ANÁLISE"):
            st.session_state.pop("ultima_analise_v19", None)
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
        "Leitura honesta: se a aderência estiver ruim, não significa que não pode apostar; significa apenas que a liga está menos bem comportada para uma Poisson simples. "
        "A decisão da V19.3.3 continua sendo pela planilha: odd real contra odd justa."
    )


with aba_scout:
    st.subheader("Scout opcional")
    st.caption("Finalizações, chutes no alvo, escanteios e cartões entram aqui quando o CSV da liga traz essas colunas. Isto é diagnóstico, não veto automático.")

    c1, c2 = st.columns(2)
    with c1:
        scout_casa = st.selectbox("Mandante para scout", times_liga, key="scout_casa")
    with c2:
        scout_fora = st.selectbox("Visitante para scout", times_liga, index=min(1, len(times_liga)-1), key="scout_fora")

    if scout_casa == scout_fora:
        st.warning("Escolha times diferentes.")
    else:
        tabela_scout, avisos_scout = calcular_scout_opcional(df_liga, scout_casa, scout_fora)
        st.dataframe(tabela_scout, use_container_width=True, hide_index=True)
        for aviso in avisos_scout:
            st.caption("• " + aviso)

        modelo_scout = calcular_planilha_pura(df_liga, scout_casa, scout_fora)
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
    st.subheader("Catálogo de odds")
    cfg = obter_config_google()
    if cfg.get("configurado"):
        st.success(f"Google Sheets ativo. Aba: {cfg['worksheet_catalogo']}.")
    else:
        st.warning("Google Sheets não configurado. O backup local pode sumir em reinicializações do Streamlit Cloud.")

    force_sync_catalogo = False
    if cfg.get("configurado"):
        force_sync_catalogo = st.button("🔄 Sincronizar catálogo do Google", key="sync_catalogo_tab")
        if _google_cooldown_ativo():
            st.info(f"Google em cooldown por {_segundos_cooldown_google()}s; mostrando cache/backup local.")

    catalogo = carregar_catalogo(force_google=force_sync_catalogo)
    if catalogo.empty:
        st.info("Ainda não há odds salvas.")
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
        st.download_button("BAIXAR CATÁLOGO CSV", data=csv, file_name="catalogo_odds_tex_v19_1.csv", mime="text/csv")

with aba_auditoria:
    st.subheader("Auditoria")
    cfg = obter_config_google()
    if cfg.get("configurado"):
        st.success(f"Google Sheets ativo. Aba: {cfg['worksheet_auditoria']}.")
    else:
        st.warning("Google Sheets não configurado. Use com cuidado no Streamlit Cloud.")

    force_sync_auditoria_tab = False
    if cfg.get("configurado"):
        force_sync_auditoria_tab = st.button("🔄 Sincronizar auditoria do Google", key="sync_auditoria_tab")
        if _google_cooldown_ativo():
            st.info(f"Google em cooldown por {_segundos_cooldown_google()}s; mostrando cache/backup local.")

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
        st.dataframe(geral_fmt, use_container_width=True, hide_index=True)

        a1, a2, a3 = st.tabs(["Por mercado", "Por liga", "Por faixa de odd"])
        for aba_tmp, chave in [(a1, "por_mercado"), (a2, "por_liga"), (a3, "por_faixa_odd")]:
            with aba_tmp:
                t = resumo_adv[chave].copy()
                for col in ["Apostado", "Resultado"]:
                    t[col] = t[col].map(fmt_dinheiro)
                for col in ["Taxa acerto", "ROI"]:
                    t[col] = t[col].map(lambda x: fmt_pct(x, 2))
                st.dataframe(t, use_container_width=True, hide_index=True)

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
            aud_odd = st.text_input("Odd", value="", key="aud_odd")
            aud_entrada = st.text_input("Entrada R$", value="", key="aud_entrada")
            aud_banca = st.number_input("Banca antes", min_value=0.0, value=float(banca_calc), step=10.0, key="aud_banca")
            aud_obs = st.text_input("Observação", value="", key="aud_obs")
        if st.button("SALVAR ENTRADA MANUAL"):
            odd = texto_para_float(aud_odd)
            entrada = texto_para_float(aud_entrada)
            if not odd_valida(odd) or entrada is None or entrada <= 0 or not aud_jogo.strip():
                st.error("Preencha jogo, odd válida e entrada.")
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
                label = f"{row['ID']} — {row['Jogo']} — {row['Mercado']} — {fmt_dinheiro(texto_para_float(row['Entrada R$']) or 0)}"
                labels.append(label)
                mapa[label] = idx
            escolha = st.selectbox("Entrada", labels)
            idx = mapa[escolha]
            row = auditoria.loc[idx]
            c1, c2, c3 = st.columns(3)
            with c1:
                status = st.selectbox("Resultado", ["Green", "Red", "Void", "Cashout"], key="status_fechar")
            with c2:
                odd_fechamento_txt = st.text_input("Odd fechamento", value="", key="odd_fechamento")
            with c3:
                cashout = st.number_input("Valor cashout recebido", min_value=0.0, value=0.0, step=1.0, key="cashout")
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
                auditoria.loc[idx, "Observação"] = str(row.get("Observação", "")) + " | Fechamento: " + obs_fechamento
                destino = salvar_auditoria(auditoria)
                st.success(f"Entrada fechada. Destino: {destino}.")

    st.markdown("---")
    st.markdown("### Histórico")
    auditoria = carregar_auditoria()
    if auditoria.empty:
        st.info("Nenhum registro ainda.")
    else:
        st.dataframe(remover_colunas_duplicadas(auditoria).tail(500), use_container_width=True, hide_index=True)
        csv = auditoria.to_csv(index=False).encode("utf-8-sig")
        st.download_button("BAIXAR AUDITORIA CSV", data=csv, file_name="auditoria_tex_v19_1.csv", mime="text/csv")

with aba_calendario:
    st.subheader("Ligas cobertas")
    st.caption("A trava operacional mais importante é esta: só use a liga exatamente correspondente à base do app.")
    mapa = pd.DataFrame(CALENDARIO_LIGAS)
    st.dataframe(mapa, use_container_width=True, hide_index=True)
    st.markdown(
        """
        **Regra prática:** se a casa de apostas mostrar uma competição parecida, mas não igual, não force.
        Exemplo: Allsvenskan não é Ettan; Veikkausliiga não é Ykkönen; MLS não é MLS Next Pro.
        """
    )
