import os
import io
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import difflib
import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson

# =========================================================
# TEX STATISTICS PRO 14.2 — APP.PY EM PORTUGUÊS
# Cole este arquivo inteiro em app.py no GitHub/Streamlit.
# Foco: muitas entradas possíveis, sem cotações fictícias,
# banca dinâmica e auditoria real da vantagem sobre o fechamento.
# =========================================================

st.set_page_config(page_title="TEX STATISTICS PRO 14.2", layout="wide")

# =========================================================
# LIGAS
# =========================================================

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

EXCHANGES_BLOQUEADAS = {
    "smarkets", "matchbook", "betfair_ex_uk", "betfair_ex_au",
    "betfair_ex_eu", "betdaq", "betfair"
}

CASAS = ["Pixbet", "Pinnacle", "Bet365", "Betano", "KTO", "Superbet", "Outra"]
STATUS = ["Pendente", "Ganhou", "Perdeu", "Anulada", "Saída antecipada"]

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
AUDIT_FILE = LOG_DIR / "auditoria_entradas_tex_v14_2.csv"

AUDIT_COLS = [
    "id", "data_registro", "data_evento", "liga", "jogo", "mandante", "visitante",
    "mercado", "casa", "odd_entrada", "odd_fechamento", "clv_pct",
    "stake_pct", "stake_reais", "banca_antes", "banca_depois",
    "prob_modelo", "prob_conservadora", "prob_mercado",
    "ev_bruto", "ev_conservador", "edge", "confianca",
    "status", "resultado_reais", "observacao"
]

# =========================================================
# ESTRUTURAS
# =========================================================

@dataclass
class LinhaMercado:
    mercado: str
    odd: float
    prob_mercado: float
    origem: str
    bookmakers: int = 0

@dataclass
class ResultadoSinal:
    mercado: str
    prob_modelo: float
    prob_conservadora: float
    prob_mercado: float
    odd_justa: float
    odd_mercado: float
    ev_bruto: float
    ev_conservador: float
    edge: float
    divergencia: float
    confianca: float
    stake_frac: float
    stake_valor: float
    operavel: bool
    motivo: str
    origem_odd: str

# =========================================================
# UTILITÁRIOS
# =========================================================

def get_secret_or_env(nome: str, default: str = "") -> str:
    try:
        return st.secrets.get(nome, os.getenv(nome, default))
    except Exception:
        return os.getenv(nome, default)

def safe_float(x) -> Optional[float]:
    try:
        if pd.isna(x):
            return None
        v = float(str(x).replace(",", "."))
        if not np.isfinite(v) or v <= 1.01:
            return None
        return v
    except Exception:
        return None

def odd_input(label: str, key: str, coluna=None) -> Optional[float]:
    """Campo de cotação mostrado na tela principal. Aceita vírgula ou ponto."""
    ui = coluna if coluna is not None else st
    txt = ui.text_input(label, value="", key=f"cotacao_{key}")
    if not str(txt).strip():
        return None
    return safe_float(txt)

def normalizar_overround(odds: Dict[str, float], mercados: List[str], exigir_completo: bool = True) -> Dict[str, float]:
    if exigir_completo and not all(m in odds and odds[m] > 1.01 for m in mercados):
        return {}
    inv = {m: 1.0 / odds[m] for m in mercados if m in odds and odds[m] > 1.01}
    total = sum(inv.values())
    if total <= 0:
        return {}
    return {m: inv[m] / total for m in inv}

def prob_implicita_conservadora(odd: float) -> float:
    return 1.0 / odd if odd and odd > 1.01 else 0.0

def encontrar_match(nome_api: str, times_csv: List[str]) -> Optional[str]:
    base = (
        str(nome_api).lower().replace("fc", "").replace("ec", "")
        .replace("ac", "").replace("sp", "").replace("rj", "").strip()
    )
    candidatos = [t.lower() for t in times_csv]
    matches = difflib.get_close_matches(base, candidatos, n=1, cutoff=0.70)
    if not matches:
        return None
    return next(t for t in times_csv if t.lower() == matches[0])

def fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"

def fmt_money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =========================================================
# HISTÓRICO
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def carregar_historico(url: str) -> pd.DataFrame:
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
        df = df.dropna(subset=["HG", "AG"])
        if "Date" in df.columns:
            df["DataParse"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.sort_values("DataParse", kind="mergesort")
        df = df.tail(1000).reset_index(drop=True)
        df["Peso"] = np.exp(np.linspace(-2.2, 0.0, len(df)))
        return df
    except Exception:
        return pd.DataFrame()

# =========================================================
# MODELO POISSON + SHRINKAGE
# =========================================================

def correcao_empirica(df: pd.DataFrame) -> float:
    try:
        total = max(1, len(df))
        p00 = len(df[(df["HG"] == 0) & (df["AG"] == 0)]) / total
        p11 = len(df[(df["HG"] == 1) & (df["AG"] == 1)]) / total
        return float(np.clip((p00 - 0.10) + (p11 - 0.12), -0.10, 0.10))
    except Exception:
        return 0.0

def ajuste_dc(i: int, j: int, rho: float) -> float:
    if i == 0 and j == 0:
        return 1.0 - rho
    if i == 1 and j == 0:
        return 1.0 + rho * 0.5
    if i == 0 and j == 1:
        return 1.0 + rho * 0.5
    if i == 1 and j == 1:
        return 1.0 - rho * 0.25
    return 1.0

def precificar(df: pd.DataFrame, casa: str, fora: str) -> Tuple[float, float, Dict[str, float], float, Dict[str, int]]:
    media_h = max(float(np.average(df["HG"], weights=df["Peso"])), 0.20)
    media_a = max(float(np.average(df["AG"], weights=df["Peso"])), 0.20)

    ch = df[df["Home"] == casa]
    ca = df[df["Away"] == casa]
    fh = df[df["Home"] == fora]
    fa = df[df["Away"] == fora]

    n_ch = len(ch)
    n_fa = len(fa)
    n_c_total = len(ch) + len(ca)
    n_f_total = len(fh) + len(fa)

    gf_c = pd.concat([ch["HG"], ca["AG"]])
    gs_c = pd.concat([ch["AG"], ca["HG"]])
    pw_c = pd.concat([ch["Peso"], ca["Peso"]])
    gf_f = pd.concat([fh["HG"], fa["AG"]])
    gs_f = pd.concat([fh["AG"], fa["HG"]])
    pw_f = pd.concat([fh["Peso"], fa["Peso"]])

    att_c_g = np.average(gf_c, weights=pw_c) if len(gf_c) else media_h
    def_c_g = np.average(gs_c, weights=pw_c) if len(gs_c) else media_a
    att_f_g = np.average(gf_f, weights=pw_f) if len(gf_f) else media_a
    def_f_g = np.average(gs_f, weights=pw_f) if len(gs_f) else media_h

    att_c_m = np.average(ch["HG"], weights=ch["Peso"]) if n_ch >= 4 else media_h
    def_c_m = np.average(ch["AG"], weights=ch["Peso"]) if n_ch >= 4 else media_a
    att_f_m = np.average(fa["AG"], weights=fa["Peso"]) if n_fa >= 4 else media_a
    def_f_m = np.average(fa["HG"], weights=fa["Peso"]) if n_fa >= 4 else media_h

    w_c = min(0.75, n_ch / 12.0)
    w_f = min(0.75, n_fa / 12.0)

    att_c = att_c_m * w_c + att_c_g * (1.0 - w_c)
    def_c = def_c_m * w_c + def_c_g * (1.0 - w_c)
    att_f = att_f_m * w_f + att_f_g * (1.0 - w_f)
    def_f = def_f_m * w_f + def_f_g * (1.0 - w_f)

    k = 10.0
    att_c = ((n_ch * att_c) + (k * media_h)) / (n_ch + k)
    def_c = ((n_ch * def_c) + (k * media_a)) / (n_ch + k)
    att_f = ((n_fa * att_f) + (k * media_a)) / (n_fa + k)
    def_f = ((n_fa * def_f) + (k * media_h)) / (n_fa + k)

    lambda_h = media_h * (att_c / media_h) * (def_f / media_h)
    lambda_a = media_a * (att_f / media_a) * (def_c / media_a)
    lambda_h = float(np.clip(lambda_h, 0.20, 3.80))
    lambda_a = float(np.clip(lambda_a, 0.20, 3.80))

    grid = 20
    rho = correcao_empirica(df)
    matriz = np.zeros((grid, grid))
    for i in range(grid):
        for j in range(grid):
            matriz[i, j] = poisson.pmf(i, lambda_h) * poisson.pmf(j, lambda_a) * ajuste_dc(i, j, rho)
    if matriz.sum() > 0:
        matriz /= matriz.sum()

    p_h = float(np.tril(matriz, -1).sum())
    p_d = float(np.diag(matriz).sum())
    p_a = float(np.triu(matriz, 1).sum())
    p_o25 = float(matriz[np.add.outer(np.arange(grid), np.arange(grid)) >= 3].sum())
    p_btts = float(matriz[1:, 1:].sum())
    sem_empate = p_h + p_a

    probs = {
        "Vitória Casa": p_h,
        "Empate": p_d,
        "Vitória Fora": p_a,
        "Mais de 2.5 gols": p_o25,
        "Under 2.5": 1.0 - p_o25,
        "Ambos marcam": p_btts,
        "BTTS_No": 1.0 - p_btts,
        "Casa ou Empate": p_h + p_d,
        "Fora ou Empate": p_a + p_d,
        "Empate Anula Casa": p_h / sem_empate if sem_empate > 0 else 0.0,
        "Empate Anula Fora": p_a / sem_empate if sem_empate > 0 else 0.0,
    }

    var_c = float(np.var(gf_c)) if len(gf_c) > 1 else 1.5
    var_f = float(np.var(gf_f)) if len(gf_f) > 1 else 1.5
    estabilidade = np.clip(1.0 - (((var_c + var_f) / 2.0) / 5.0), 0.0, 1.0)
    volume_mando = min(n_ch, n_fa) / 14.0
    volume_total = min(n_c_total, n_f_total) / 26.0
    equilibrio = min(n_ch, n_fa) / max(1, max(n_ch, n_fa))
    conf = 55 * np.clip(volume_mando, 0, 1) + 20 * np.clip(volume_total, 0, 1) + 15 * estabilidade + 10 * equilibrio
    conf = float(np.clip(conf, 0.0, 100.0))

    amostras = {
        "casa_mando": n_ch, "fora_mando": n_fa,
        "casa_total": n_c_total, "fora_total": n_f_total
    }
    return lambda_h, lambda_a, probs, conf, amostras

# =========================================================
# ODDS MANUAL E API
# =========================================================

def linhas_manuais() -> Dict[str, LinhaMercado]:
    st.markdown("### 3) Preencha as cotações")
    st.caption(
        "Preencha apenas cotações reais da casa onde você vai apostar. "
        "Quando preencher os dois lados de um mercado, o sistema tira a margem. "
        "Quando preencher só um lado, ele usa uma leitura mais dura para evitar entrada falsa."
    )

    with st.expander("Cotações manuais", expanded=True):
        st.markdown("**Resultado do jogo**")
        c1, c2, c3 = st.columns(3)
        odd_casa = odd_input("Vitória casa", "vitoria_casa", c1)
        odd_empate = odd_input("Empate", "empate", c2)
        odd_fora = odd_input("Vitória fora", "vitoria_fora", c3)

        st.markdown("**Gols**")
        c4, c5 = st.columns(2)
        odd_mais25 = odd_input("Mais de 2.5 gols", "mais_25", c4)
        odd_menos25 = odd_input("Menos de 2.5 gols", "menos_25", c5)

        st.markdown("**Ambos marcam**")
        c6, c7 = st.columns(2)
        odd_ambos_sim = odd_input("Ambos marcam - Sim", "ambos_sim", c6)
        odd_ambos_nao = odd_input("Ambos marcam - Não", "ambos_nao", c7)

        st.markdown("**Proteções**")
        c8, c9 = st.columns(2)
        odd_casa_empate = odd_input("Casa ou empate", "casa_empate", c8)
        odd_fora_empate = odd_input("Fora ou empate", "fora_empate", c9)
        c10, c11 = st.columns(2)
        odd_anula_casa = odd_input("Empate anula - Casa", "anula_casa", c10)
        odd_anula_fora = odd_input("Empate anula - Fora", "anula_fora", c11)

    odds_raw = {
        "Vitória Casa": odd_casa,
        "Empate": odd_empate,
        "Vitória Fora": odd_fora,
        "Mais de 2.5 gols": odd_mais25,
        "Under 2.5": odd_menos25,
        "Ambos marcam": odd_ambos_sim,
        "BTTS_No": odd_ambos_nao,
        "Casa ou Empate": odd_casa_empate,
        "Fora ou Empate": odd_fora_empate,
        "Empate Anula Casa": odd_anula_casa,
        "Empate Anula Fora": odd_anula_fora,
    }
    odds = {m: o for m, o in odds_raw.items() if o is not None}
    probs: Dict[str, float] = {}

    grupos = [
        ["Vitória Casa", "Empate", "Vitória Fora"],
        ["Mais de 2.5 gols", "Under 2.5"],
        ["Ambos marcam", "BTTS_No"],
        ["Empate Anula Casa", "Empate Anula Fora"],
    ]
    for grupo in grupos:
        p_grupo = normalizar_overround(odds, grupo, exigir_completo=True)
        if p_grupo:
            probs.update(p_grupo)
        else:
            for m in grupo:
                if m in odds:
                    probs[m] = prob_implicita_conservadora(odds[m])

    for m in ["Casa ou Empate", "Fora ou Empate"]:
        if m in odds:
            probs[m] = prob_implicita_conservadora(odds[m])

    return {m: LinhaMercado(m, odds[m], probs[m], "Manual") for m in odds if probs.get(m, 0) > 0}

@st.cache_data(ttl=300, show_spinner=False)
def odds_api(api_key: str, sport_key: str) -> Optional[List[dict]]:
    if not api_key.strip():
        return None
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
        params = {
            "apiKey": api_key,
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

def mediana(pool: List[float]) -> Optional[float]:
    vals = [float(x) for x in pool if x and np.isfinite(x) and x > 1.01]
    return float(np.median(vals)) if vals else None

def linhas_api(jogo: dict) -> Dict[str, LinhaMercado]:
    pools = {m: [] for m in [
        "Vitória Casa", "Empate", "Vitória Fora",
        "Mais de 2.5 gols", "Under 2.5", "Ambos marcam", "BTTS_No"
    ]}
    bookies = {m: set() for m in pools}

    for bk in jogo.get("bookmakers", []):
        bk_key = str(bk.get("key", "")).lower()
        if bk_key in EXCHANGES_BLOQUEADAS:
            continue
        for market in bk.get("markets", []):
            key = market.get("key")
            for o in market.get("outcomes", []):
                odd = safe_float(o.get("price"))
                if odd is None:
                    continue
                nome = o.get("name")
                if key == "h2h":
                    if nome == jogo.get("home_team"):
                        pools["Vitória Casa"].append(odd); bookies["Vitória Casa"].add(bk_key)
                    elif nome == "Draw":
                        pools["Empate"].append(odd); bookies["Empate"].add(bk_key)
                    elif nome == jogo.get("away_team"):
                        pools["Vitória Fora"].append(odd); bookies["Vitória Fora"].add(bk_key)
                elif key == "totals":
                    try:
                        if abs(float(o.get("point", 0)) - 2.5) > 1e-9:
                            continue
                    except Exception:
                        continue
                    if nome == "Over":
                        pools["Mais de 2.5 gols"].append(odd); bookies["Mais de 2.5 gols"].add(bk_key)
                    elif nome == "Under":
                        pools["Under 2.5"].append(odd); bookies["Under 2.5"].add(bk_key)
                elif key == "btts":
                    if nome == "Yes":
                        pools["Ambos marcam"].append(odd); bookies["Ambos marcam"].add(bk_key)
                    elif nome == "No":
                        pools["BTTS_No"].append(odd); bookies["BTTS_No"].add(bk_key)

    odds = {m: mediana(v) for m, v in pools.items()}
    odds = {m: o for m, o in odds.items() if o is not None}
    probs = {}
    probs.update(normalizar_overround(odds, ["Vitória Casa", "Empate", "Vitória Fora"], True))
    probs.update(normalizar_overround(odds, ["Mais de 2.5 gols", "Under 2.5"], True))
    probs.update(normalizar_overround(odds, ["Ambos marcam", "BTTS_No"], True))

    linhas = {}
    for m, odd in odds.items():
        if probs.get(m, 0) > 0:
            linhas[m] = LinhaMercado(m, odd, probs[m], "API real", len(bookies[m]))
    return linhas

# =========================================================
# FILTRO, KELLY E SELEÇÃO
# =========================================================

def margem_erro(conf: float, mercado: str, odd: float) -> float:
    base = 0.012 + ((100.0 - conf) / 100.0) * 0.050
    if mercado == "Empate" or odd >= 3.0:
        base += 0.008
    if odd >= 4.0:
        base += 0.012
    return float(np.clip(base, 0.012, 0.080))

def limite_div(odd: float) -> float:
    if odd <= 1.65:
        return 0.080
    if odd <= 2.20:
        return 0.105
    if odd <= 3.20:
        return 0.130
    if odd <= 5.00:
        return 0.155
    return 0.170

def kelly_frac(prob: float, odd: float, fracao: float, teto: float) -> float:
    b = odd - 1.0
    if b <= 0:
        return 0.0
    k = ((b * prob) - (1.0 - prob)) / b
    if k <= 0:
        return 0.0
    return float(min(k * fracao, teto))

def avaliar(
    probs_modelo: Dict[str, float], linhas: Dict[str, LinhaMercado], conf: float, banca: float,
    conf_min: float, ev_min: float, ev_cons_min: float, edge_min: float,
    kelly_f: float, stake_max: float
) -> List[ResultadoSinal]:
    res = []
    for mercado, linha in linhas.items():
        if mercado not in probs_modelo:
            continue
        p = float(probs_modelo[mercado])
        odd = float(linha.odd)
        p_m = float(linha.prob_mercado)
        p_cons = max(0.0, p - margem_erro(conf, mercado, odd))
        ev = p * odd - 1.0
        evc = p_cons * odd - 1.0
        edge = p - p_m
        div = abs(edge)
        st_frac = kelly_frac(p_cons, odd, kelly_f, stake_max)

        motivos = []
        if conf < conf_min:
            motivos.append(f"confiança baixa {conf:.1f}%")
        if ev < ev_min:
            motivos.append(f"valor esperado baixo {ev*100:.1f}%")
        if evc < ev_cons_min:
            motivos.append(f"valor seguro baixo {evc*100:.1f}%")
        if edge < edge_min:
            motivos.append(f"vantagem insuficiente {edge*100:.1f}%")
        if div > limite_div(odd):
            motivos.append(f"divergência excessiva {div*100:.1f}%")
        if st_frac <= 0:
            motivos.append("cálculo da banca zerado")

        ok = len(motivos) == 0
        res.append(ResultadoSinal(
            mercado=mercado,
            prob_modelo=p,
            prob_conservadora=p_cons,
            prob_mercado=p_m,
            odd_justa=(1.0 / p if p > 0 else np.inf),
            odd_mercado=odd,
            ev_bruto=ev,
            ev_conservador=evc,
            edge=edge,
            divergencia=div,
            confianca=conf,
            stake_frac=st_frac if ok else 0.0,
            stake_valor=banca * st_frac if ok else 0.0,
            operavel=ok,
            motivo="OK" if ok else "; ".join(motivos),
            origem_odd=linha.origem,
        ))
    return sorted(res, key=lambda x: (x.operavel, x.ev_conservador, x.edge), reverse=True)

def selecionar(resultados: List[ResultadoSinal], max_por_jogo: int, exposicao_max: float, banca: float) -> List[ResultadoSinal]:
    ops = [r for r in resultados if r.operavel]
    ops = sorted(ops, key=lambda r: (r.ev_conservador, r.edge, r.confianca), reverse=True)
    escolhidos = []
    exp = 0.0
    for r in ops:
        if len(escolhidos) >= max_por_jogo:
            break
        if exp + r.stake_frac > exposicao_max:
            continue
        r.stake_valor = banca * r.stake_frac
        escolhidos.append(r)
        exp += r.stake_frac
    return escolhidos

# =========================================================
# AUDITORIA
# =========================================================

def load_audit() -> pd.DataFrame:
    if not AUDIT_FILE.exists():
        return pd.DataFrame(columns=AUDIT_COLS)
    try:
        df = pd.read_csv(AUDIT_FILE)
        for c in AUDIT_COLS:
            if c not in df.columns:
                df[c] = np.nan
        return df[AUDIT_COLS]
    except Exception:
        return pd.DataFrame(columns=AUDIT_COLS)

def save_audit(df: pd.DataFrame) -> None:
    for c in AUDIT_COLS:
        if c not in df.columns:
            df[c] = np.nan
    df[AUDIT_COLS].to_csv(AUDIT_FILE, index=False)

def calcular_resultado(status: str, stake: float, odd: float, cashout: float = 0.0) -> float:
    if status in ["Ganhou", "Green"]:
        return stake * (odd - 1.0)
    if status in ["Perdeu", "Red"]:
        return -stake
    if status in ["Anulada", "Void", "Pendente"]:
        return 0.0
    if status in ["Saída antecipada", "Cashout"]:
        return cashout - stake
    return 0.0

def banca_atual(df_audit: pd.DataFrame, banca_inicial: float) -> float:
    if df_audit.empty:
        return banca_inicial
    fechadas = df_audit[df_audit["status"].isin(["Ganhou", "Perdeu", "Anulada", "Saída antecipada", "Green", "Red", "Void", "Cashout"])]
    total = pd.to_numeric(fechadas["resultado_reais"], errors="coerce").fillna(0).sum()
    return float(banca_inicial + total)

def metricas_auditoria(df_audit: pd.DataFrame, banca_inicial: float) -> Dict[str, float]:
    if df_audit.empty:
        return {"entradas": 0, "fechadas": 0, "lucro": 0.0, "roi": 0.0, "clv": 0.0, "banca": banca_inicial}
    fechadas = df_audit[df_audit["status"].isin(["Ganhou", "Perdeu", "Anulada", "Saída antecipada", "Green", "Red", "Void", "Cashout"])]
    lucro = pd.to_numeric(fechadas["resultado_reais"], errors="coerce").fillna(0).sum()
    clv = pd.to_numeric(df_audit["clv_pct"], errors="coerce").dropna()
    return {
        "entradas": len(df_audit),
        "fechadas": len(fechadas),
        "lucro": float(lucro),
        "roi": float((lucro / banca_inicial) * 100.0) if banca_inicial > 0 else 0.0,
        "clv": float(clv.mean()) if len(clv) else 0.0,
        "banca": banca_inicial + float(lucro),
    }

def auditoria_para_tela(df: pd.DataFrame) -> pd.DataFrame:
    """Mostra a auditoria com nomes simples, em português brasileiro."""
    if df.empty:
        return df.copy()
    cols = [
        "id", "data_registro", "data_evento", "liga", "jogo", "mercado", "casa",
        "odd_entrada", "odd_fechamento", "clv_pct", "stake_pct", "stake_reais",
        "banca_antes", "banca_depois", "prob_modelo", "prob_conservadora",
        "prob_mercado", "ev_bruto", "ev_conservador", "edge", "confianca",
        "status", "resultado_reais", "observacao"
    ]
    cols = [c for c in cols if c in df.columns]
    saida = df[cols].copy()
    nomes = {
        "id": "ID",
        "data_registro": "Registrada em",
        "data_evento": "Data do jogo",
        "liga": "Liga",
        "jogo": "Jogo",
        "mercado": "Mercado",
        "casa": "Casa",
        "odd_entrada": "Cotação de entrada",
        "odd_fechamento": "Cotação de fechamento",
        "clv_pct": "Vantagem no fechamento %",
        "stake_pct": "Entrada %",
        "stake_reais": "Entrada R$",
        "banca_antes": "Banca antes",
        "banca_depois": "Banca depois",
        "prob_modelo": "Probabilidade do sistema",
        "prob_conservadora": "Probabilidade segura",
        "prob_mercado": "Probabilidade do mercado",
        "ev_bruto": "Valor esperado",
        "ev_conservador": "Valor esperado seguro",
        "edge": "Vantagem contra mercado",
        "confianca": "Confiança",
        "status": "Status",
        "resultado_reais": "Resultado R$",
        "observacao": "Observação",
    }
    return saida.rename(columns=nomes)

def nova_linha_auditoria(
    liga: str, jogo: str, casa: str, fora: str, sinal: ResultadoSinal,
    casa_apostas: str, banca_usada: float, data_evento, observacao: str = ""
) -> Dict[str, object]:
    return {
        "id": str(uuid.uuid4())[:8],
        "data_registro": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_evento": str(data_evento),
        "liga": liga,
        "jogo": jogo,
        "mandante": casa,
        "visitante": fora,
        "mercado": sinal.mercado,
        "casa": casa_apostas,
        "odd_entrada": sinal.odd_mercado,
        "odd_fechamento": np.nan,
        "clv_pct": np.nan,
        "stake_pct": sinal.stake_frac * 100.0,
        "stake_reais": sinal.stake_valor,
        "banca_antes": banca_usada,
        "banca_depois": np.nan,
        "prob_modelo": sinal.prob_modelo,
        "prob_conservadora": sinal.prob_conservadora,
        "prob_mercado": sinal.prob_mercado,
        "ev_bruto": sinal.ev_bruto,
        "ev_conservador": sinal.ev_conservador,
        "edge": sinal.edge,
        "confianca": sinal.confianca,
        "status": "Pendente",
        "resultado_reais": 0.0,
        "observacao": observacao,
    }

# =========================================================
# UI PRINCIPAL
# =========================================================

st.title("TEX STATISTICS PRO 14.2")
st.caption("Motor quantitativo com banca dinâmica, limite de 3% da banca atual e auditoria real da vantagem sobre o fechamento.")

# Carrega auditoria cedo para calcular banca dinâmica
banca_inicial_default = 1000.0
df_audit = load_audit()

with st.sidebar:
    st.header("Banca e controle")
    banca_inicial = st.number_input("Banca inicial da auditoria (R$)", min_value=1.0, value=banca_inicial_default, step=100.0)
    usar_auditada = st.checkbox("Usar banca auditada nas entradas", value=True)
    banca_manual = st.number_input("Banca manual atual (R$)", min_value=1.0, value=banca_inicial, step=100.0)
    banca_calc = banca_atual(df_audit, banca_inicial)
    banca_usada = banca_calc if usar_auditada else banca_manual
    st.metric("Banca usada pelo sistema", fmt_money(banca_usada))

    st.divider()
    st.header("Filtro de entradas")
    conf_min = st.slider("Confiança mínima", 0.0, 100.0, 62.0, 1.0)
    ev_min = st.slider("Valor esperado mínimo", 0.0, 0.30, 0.045, 0.005)
    ev_cons_min = st.slider("Valor esperado seguro mínimo", 0.0, 0.20, 0.005, 0.005)
    edge_min = st.slider("Vantagem mínima contra o mercado", 0.0, 0.15, 0.018, 0.001)

    st.divider()
    kelly_f = st.slider("Agressividade da banca", 0.01, 0.25, 0.10, 0.01)
    stake_max = st.slider("Entrada máxima por aposta", 0.001, 0.03, 0.03, 0.001)
    max_por_jogo = st.slider("Máximo de entradas por jogo", 1, 3, 3, 1)
    exposicao_max = st.slider("Total máximo no mesmo jogo", 0.005, 0.03, 0.03, 0.001)

    st.divider()
    st.header("Dados")
    liga_sel = st.selectbox("Liga", list(LIGAS_CSV.keys()))
    # O tipo de análise é escolhido na tela principal, para ficar mais claro.
    api_default = get_secret_or_env("ODDS_API_KEY", "")
    api_key = st.text_input("Chave da API de cotações", value=api_default, type="password")

with st.spinner("Carregando base histórica..."):
    df_hist = carregar_historico(LIGAS_CSV[liga_sel])

if df_hist.empty:
    st.error("Não consegui carregar a base histórica desta liga.")
    st.stop()

times = sorted(df_hist["Home"].dropna().unique().tolist())

aba_motor, aba_auditoria = st.tabs(["🎯 Analisar jogo", "📒 Minha auditoria"])

with aba_motor:
    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("Jogos históricos", len(df_hist))
    colm2.metric("Times", len(times))
    colm3.metric("Gols casa", f"{np.average(df_hist['HG'], weights=df_hist['Peso']):.2f}")
    colm4.metric("Gols fora", f"{np.average(df_hist['AG'], weights=df_hist['Peso']):.2f}")

    st.markdown("### 1) Escolha o tipo de análise")
    modo = st.radio(
        "Tipo de análise",
        ["Manual", "Automática pela API"],
        horizontal=True,
        label_visibility="collapsed",
        help="Manual: você escolhe o jogo e digita as cotações. Automática: o app tenta buscar jogos e cotações pela API."
    )
    if modo == "Manual":
        st.info("Modo manual selecionado: escolha os times e digite as cotações da Pixbet, Pinnacle ou outra casa.")
    else:
        st.info("Modo automático selecionado: o app depende da API ter jogos e cotações disponíveis para a liga escolhida. Se não aparecer jogo, use o modo manual.")

    linhas: Dict[str, LinhaMercado] = {}
    casa = fora = None
    jogo_label = ""
    data_evento = pd.Timestamp.today().date()

    if modo == "Manual":
        c1, c2, c3 = st.columns([1, 1, 1])
        casa = c1.selectbox("Mandante", times, key="manual_casa")
        fora = c2.selectbox("Visitante", times, key="manual_fora")
        data_evento = c3.date_input("Data do evento", value=pd.Timestamp.today().date())
        linhas = linhas_manuais()
        jogo_label = f"{casa} x {fora}"
        calcular = st.button("ANALISAR JOGO MANUAL", type="primary")
    else:
        if not api_key.strip():
            st.warning("Informe a chave da API de cotações na barra lateral ou use a análise manual.")
            calcular = False
        else:
            dados = odds_api(api_key, LIGAS_API[liga_sel])
            if not dados:
                st.warning("A API não encontrou jogos ou cotações para esta liga neste momento. Isso não é erro do código: pode não haver jogo aberto agora, a liga pode não estar disponível na API ou sua chave pode não cobrir esse mercado. Use a análise manual para inserir as cotações da Pixbet/Pinnacle.")
                calcular = False
            else:
                agora = pd.Timestamp.now(tz="UTC")
                jogos = {}
                for j in dados:
                    try:
                        ini = pd.to_datetime(j.get("commence_time"), utc=True)
                        if ini <= agora:
                            continue
                        label = f"{j.get('home_team')} vs {j.get('away_team')} ({ini.tz_convert('America/Sao_Paulo').strftime('%d/%m %H:%M')})"
                        jogos[label] = j
                    except Exception:
                        continue
                if not jogos:
                    st.info("Nenhuma partida pré-jogo disponível.")
                    calcular = False
                else:
                    escolha = st.selectbox("Partida", list(jogos.keys()))
                    jogo_api = jogos[escolha]
                    linhas = linhas_api(jogo_api)
                    m_casa = encontrar_match(jogo_api.get("home_team", ""), times) or times[0]
                    m_fora = encontrar_match(jogo_api.get("away_team", ""), times) or times[min(1, len(times)-1)]
                    c1, c2 = st.columns(2)
                    casa = c1.selectbox("Mandante na base", times, index=times.index(m_casa), key="auto_casa")
                    fora = c2.selectbox("Visitante na base", times, index=times.index(m_fora), key="auto_fora")
                    jogo_label = escolha
                    data_evento = pd.Timestamp.today().date()
                    st.info(f"Linhas reais encontradas: {len(linhas)}")
                    calcular = st.button("ANALISAR JOGO AUTOMÁTICO", type="primary")

    if casa == fora and casa is not None:
        st.error("Mandante e visitante não podem ser o mesmo time.")
        st.stop()

    if calcular:
        if not linhas:
            st.error("Nenhuma cotação real foi informada/coletada. O sistema não trabalha com cotação inventada.")
            st.stop()

        lamb_h, lamb_a, probs, conf, amostras = precificar(df_hist, casa, fora)
        resultados = avaliar(probs, linhas, conf, banca_usada, conf_min, ev_min, ev_cons_min, edge_min, kelly_f, stake_max)
        escolhidos = selecionar(resultados, max_por_jogo, exposicao_max, banca_usada)

        st.markdown("---")
        st.subheader(f"Análise — {jogo_label}")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Força de gols casa", f"{lamb_h:.2f}")
        k2.metric("Força de gols fora", f"{lamb_a:.2f}")
        k3.metric("Confiança", f"{conf:.1f}%")
        k4.metric("Entradas aprovadas", len(escolhidos))
        k5.metric("Máximo no jogo", fmt_money(banca_usada * exposicao_max))
        st.write(
            f"Amostra: {casa} em casa `{amostras['casa_mando']}` jogos | "
            f"{fora} fora `{amostras['fora_mando']}` jogos."
        )

        tabela = pd.DataFrame([{
            "Status": "✅ OPERÁVEL" if r in escolhidos else ("🟡 Passou, fora do limite" if r.operavel else "❌ Rejeitado"),
            "Mercado": r.mercado,
            "Cotação": round(r.odd_mercado, 2),
            "Prob. Modelo": fmt_pct(r.prob_modelo),
            "Prob. segura": fmt_pct(r.prob_conservadora),
            "Prob. Mercado": fmt_pct(r.prob_mercado),
            "Valor esperado": f"{r.ev_bruto*100:+.1f}%",
            "Valor esperado seguro": f"{r.ev_conservador*100:+.1f}%",
            "Entrada %": f"{r.stake_frac*100:.2f}%" if r in escolhidos else "0.00%",
            "Entrada R$": fmt_money(r.stake_valor) if r in escolhidos else "-",
            "Motivo": r.motivo,
            "Origem": r.origem_odd,
        } for r in resultados])
        st.dataframe(tabela, use_container_width=True, hide_index=True)

        st.subheader("Resumo executivo")
        if escolhidos:
            for r in escolhidos:
                st.success(
                    f"✅ {r.mercado} @ {r.odd_mercado:.2f} | Modelo {fmt_pct(r.prob_modelo)} | "
                    f"Segura {fmt_pct(r.prob_conservadora)} | Valor seguro {r.ev_conservador*100:+.1f}% | "
                    f"Entrada {r.stake_frac*100:.2f}% = {fmt_money(r.stake_valor)}"
                )

            with st.expander("Registrar entradas aprovadas na auditoria", expanded=True):
                casa_apostas = st.selectbox("Casa de apostas", CASAS, index=CASAS.index("Pixbet"))
                obs = st.text_area("Observação", value="")
                mercados_disp = [f"{r.mercado} @ {r.odd_mercado:.2f}" for r in escolhidos]
                selecionados_txt = st.multiselect("Entradas para registrar", mercados_disp, default=mercados_disp)
                if st.button("SALVAR ENTRADAS NA AUDITORIA"):
                    audit = load_audit()
                    novas = []
                    for txt, sinal in zip(mercados_disp, escolhidos):
                        if txt in selecionados_txt:
                            novas.append(nova_linha_auditoria(liga_sel, jogo_label, casa, fora, sinal, casa_apostas, banca_usada, data_evento, obs))
                    if novas:
                        audit = pd.concat([audit, pd.DataFrame(novas)], ignore_index=True)
                        save_audit(audit)
                        st.success(f"{len(novas)} entrada(s) registrada(s). Recarregue a página para atualizar a banca auditada.")
                    else:
                        st.warning("Nenhuma entrada selecionada.")
        else:
            st.info("Nenhuma entrada passou. Isso protege a banca quando o mercado está eficiente.")

with aba_auditoria:
    st.subheader("Minha auditoria")
    df_audit = load_audit()
    mets = metricas_auditoria(df_audit, banca_inicial)
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Entradas", int(mets["entradas"]))
    a2.metric("Fechadas", int(mets["fechadas"]))
    a3.metric("Lucro", fmt_money(mets["lucro"]))
    a4.metric("Banca auditada", fmt_money(mets["banca"]))
    a5.metric("Vantagem média no fechamento", f"{mets['clv']:+.2f}%")

    st.markdown("### Lançar entrada manual na auditoria")
    with st.form("manual_audit"):
        c1, c2, c3 = st.columns(3)
        data_ev = c1.date_input("Data evento", value=pd.Timestamp.today().date(), key="audit_data")
        liga_a = c2.selectbox("Liga", list(LIGAS_CSV.keys()), index=list(LIGAS_CSV.keys()).index(liga_sel), key="audit_liga")
        casa_bet = c3.selectbox("Casa", CASAS, key="audit_casa")
        c4, c5 = st.columns(2)
        jogo_a = c4.text_input("Jogo", value="")
        mercado_a = c5.text_input("Mercado", value="")
        c6, c7, c8 = st.columns(3)
        odd_ent = c6.number_input("Cotação de entrada", min_value=1.01, value=2.00, step=0.01)
        stake_rs = c7.number_input("Valor apostado R$", min_value=0.0, value=30.0, step=1.0)
        banca_ant = c8.number_input("Banca antes", min_value=1.0, value=float(banca_usada), step=10.0)
        obs_a = st.text_area("Observação manual", value="")
        salvar_manual = st.form_submit_button("SALVAR ENTRADA MANUAL")
        if salvar_manual:
            stake_pct = (stake_rs / banca_ant) * 100.0 if banca_ant > 0 else 0.0
            linha = {c: np.nan for c in AUDIT_COLS}
            linha.update({
                "id": str(uuid.uuid4())[:8],
                "data_registro": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_evento": str(data_ev),
                "liga": liga_a,
                "jogo": jogo_a,
                "mandante": "",
                "visitante": "",
                "mercado": mercado_a,
                "casa": casa_bet,
                "odd_entrada": odd_ent,
                "stake_pct": stake_pct,
                "stake_reais": stake_rs,
                "banca_antes": banca_ant,
                "status": "Pendente",
                "resultado_reais": 0.0,
                "observacao": obs_a,
            })
            df_audit = pd.concat([df_audit, pd.DataFrame([linha])], ignore_index=True)
            save_audit(df_audit)
            st.success("Entrada manual salva.")

    st.markdown("### Fechar/atualizar entrada")
    df_audit = load_audit()
    if df_audit.empty:
        st.info("Ainda não há entradas registradas.")
    else:
        df_show = auditoria_para_tela(df_audit.sort_values("data_registro", ascending=False))
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        opcoes = [f"{row['id']} | {row['status']} | {row['jogo']} | {row['mercado']} @ {row['odd_entrada']}" for _, row in df_audit.iterrows()]
        escolha = st.selectbox("Selecionar entrada", opcoes)
        id_sel = escolha.split(" | ")[0]
        idx = df_audit.index[df_audit["id"].astype(str) == str(id_sel)][0]
        row = df_audit.loc[idx]

        with st.form("fechar_entrada"):
            c1, c2, c3 = st.columns(3)
            odd_fech = c1.number_input("Cotação de fechamento", min_value=0.0, value=float(row["odd_fechamento"]) if pd.notna(row["odd_fechamento"]) else 0.0, step=0.01)
            status_new = c2.selectbox("Status", STATUS, index=STATUS.index(row["status"]) if row["status"] in STATUS else 0)
            cashout = c3.number_input("Valor recebido na saída antecipada", min_value=0.0, value=0.0, step=1.0)
            obs_new = st.text_area("Observação", value=str(row["observacao"]) if pd.notna(row["observacao"]) else "")
            salvar_fech = st.form_submit_button("ATUALIZAR ENTRADA")
            if salvar_fech:
                stake = float(row["stake_reais"]) if pd.notna(row["stake_reais"]) else 0.0
                odd_ent = float(row["odd_entrada"]) if pd.notna(row["odd_entrada"]) else 0.0
                resultado = calcular_resultado(status_new, stake, odd_ent, cashout)
                clv = ((odd_ent / odd_fech) - 1.0) * 100.0 if odd_fech and odd_fech > 1.01 and odd_ent > 1.01 else np.nan
                banca_depois = float(row["banca_antes"]) + resultado if pd.notna(row["banca_antes"]) else np.nan

                df_audit.loc[idx, "odd_fechamento"] = odd_fech if odd_fech > 1.01 else np.nan
                df_audit.loc[idx, "clv_pct"] = clv
                df_audit.loc[idx, "status"] = status_new
                df_audit.loc[idx, "resultado_reais"] = resultado
                df_audit.loc[idx, "banca_depois"] = banca_depois
                df_audit.loc[idx, "observacao"] = obs_new
                save_audit(df_audit)
                st.success("Entrada atualizada.")

        csv = df_audit.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar auditoria CSV", data=csv, file_name="auditoria_entradas_tex_v14_2.csv", mime="text/csv")
