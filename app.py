import os
import io
import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson
import difflib

# ============================================================
# TEX STATISTICS PRO 14.3
# Versão simples, em português brasileiro e com blocos por mercado
# ============================================================

st.set_page_config(
    page_title="TEX STATISTICS PRO 14.3",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# VISUAL — FOCO EM CELULAR
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.0rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #555;
        font-size: 1.0rem;
        margin-bottom: 1.2rem;
    }
    .card-apostar, .card-nao, .card-neutro {
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        margin: 14px 0 18px 0;
        box-shadow: 0 4px 18px rgba(0,0,0,0.07);
        border: 1px solid rgba(0,0,0,0.08);
    }
    .card-apostar {
        background: #f0fdf4;
        border-left: 8px solid #16a34a;
    }
    .card-nao {
        background: #fff7f7;
        border-left: 8px solid #dc2626;
    }
    .card-neutro {
        background: #f8fafc;
        border-left: 8px solid #64748b;
    }
    .status-apostar {
        color: #166534;
        font-size: 1.22rem;
        font-weight: 900;
        margin-bottom: 4px;
    }
    .status-nao {
        color: #991b1b;
        font-size: 1.22rem;
        font-weight: 900;
        margin-bottom: 4px;
    }
    .mercado-titulo {
        font-size: 1.40rem;
        font-weight: 900;
        color: #111827;
        margin-bottom: 12px;
    }
    .grade-card {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
        gap: 10px;
        margin-top: 8px;
    }
    .mini-box {
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(0,0,0,0.07);
        border-radius: 14px;
        padding: 10px;
    }
    .mini-label {
        font-size: 0.78rem;
        color: #555;
        margin-bottom: 2px;
    }
    .mini-value {
        font-size: 1.13rem;
        color: #111827;
        font-weight: 800;
    }
    .motivo-box {
        margin-top: 12px;
        padding: 11px 12px;
        border-radius: 12px;
        background: rgba(255,255,255,0.75);
        color: #374151;
        font-size: 0.96rem;
        line-height: 1.36rem;
    }
    .aviso-simples {
        padding: 12px 14px;
        border-radius: 12px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e3a8a;
        margin: 12px 0;
    }
    @media (max-width: 700px) {
        .main-title {font-size: 1.55rem;}
        .mercado-titulo {font-size: 1.18rem;}
        .status-apostar, .status-nao {font-size: 1.05rem;}
        .card-apostar, .card-nao, .card-neutro {padding: 14px; margin: 12px 0;}
        .grade-card {grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px;}
        .mini-value {font-size: 1.02rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# LIGAS
# ============================================================

LIGAS_CSV = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Argentina - Primeira Divisão": "https://www.football-data.co.uk/new/ARG.csv",
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
    "Argentina - Primeira Divisão": "soccer_argentina_primera_division",
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

CASAS_BLOQUEADAS = {
    "smarkets", "matchbook", "betfair_ex_uk", "betfair_ex_au", "betfair_ex_eu",
    "betdaq", "betfair"
}

ORDEM_MERCADOS = [
    "Vitória Casa",
    "Empate",
    "Vitória Fora",
    "Mais de 2.5 gols",
    "Menos de 2.5 gols",
    "Ambos marcam - Sim",
    "Ambos marcam - Não",
    "Casa ou Empate",
    "Fora ou Empate",
    "Empate anula - Casa",
    "Empate anula - Fora",
]

COLUNAS_AUDITORIA = [
    "ID", "Data registro", "Data jogo", "Liga", "Jogo", "Casa", "Mercado",
    "Cotação entrada", "Cotação fechamento", "Vantagem fechamento %",
    "Entrada %", "Entrada R$", "Banca antes", "Banca depois",
    "Probabilidade modelo %", "Probabilidade mercado %", "Cotação justa",
    "Valor esperado %", "Confiança %", "Status", "Resultado R$", "Observações"
]

CAMINHO_AUDITORIA = "logs/auditoria_tex_statistics.csv"

# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def dinheiro(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor: float, casas: int = 1) -> str:
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def numero_texto(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def texto_para_float(txt: str) -> Optional[float]:
    if txt is None:
        return None
    txt = str(txt).strip().replace("R$", "").replace(" ", "")
    if not txt:
        return None
    try:
        # Aceita 1,83 e também 1.83
        if "," in txt and "." in txt:
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", ".")
        valor = float(txt)
        if not np.isfinite(valor):
            return None
        return valor
    except Exception:
        return None


def ler_cotacao(label: str, chave: str) -> Optional[float]:
    valor = st.text_input(label, value="", key=chave, placeholder="Ex.: 1,85")
    cotacao = texto_para_float(valor)
    if cotacao is None:
        return None
    if cotacao <= 1.01:
        return None
    return cotacao


def cotacao_valida(valor) -> Optional[float]:
    try:
        v = float(valor)
        if np.isfinite(v) and v > 1.01:
            return v
    except Exception:
        pass
    return None

# ============================================================
# DADOS HISTÓRICOS E API
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def carregar_historico(url: str) -> pd.DataFrame:
    try:
        resposta = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resposta.raise_for_status()
        df = pd.read_csv(io.StringIO(resposta.text))
        df = df.rename(columns={
            "HomeTeam": "Home",
            "AwayTeam": "Away",
            "FTHG": "HG",
            "FTAG": "AG",
        })
        colunas = ["Home", "Away", "HG", "AG"]
        if not all(c in df.columns for c in colunas):
            return pd.DataFrame()

        df = df.dropna(subset=colunas).copy()
        df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
        df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
        df = df.dropna(subset=["HG", "AG"])

        if "Date" in df.columns:
            df["Data"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.sort_values("Data", kind="mergesort")
        else:
            df = df.sort_index()

        df = df.tail(1000).reset_index(drop=True)
        df["Peso"] = np.exp(np.linspace(-2.2, 0.0, len(df)))
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def buscar_api(chave_api: str, codigo_liga: str) -> Optional[List[dict]]:
    if not chave_api.strip():
        return None
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{codigo_liga}/odds/"
        parametros = {
            "apiKey": chave_api.strip(),
            "regions": "eu,uk,us",
            "markets": "h2h,totals,btts",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        resposta = requests.get(url, params=parametros, timeout=20)
        if resposta.status_code != 200:
            return None
        dados = resposta.json()
        if not isinstance(dados, list):
            return None
        return dados
    except Exception:
        return None


def achar_time(nome_api: str, times: List[str]) -> Optional[str]:
    if not nome_api:
        return None
    nome = nome_api.lower()
    remover = [" fc", " ec", " ac", " rj", " sp", " futebol clube", " clube"]
    for r in remover:
        nome = nome.replace(r, "")
    nome = nome.strip()
    opcoes = [t.lower() for t in times]
    encontrados = difflib.get_close_matches(nome, opcoes, n=1, cutoff=0.68)
    if encontrados:
        return next(t for t in times if t.lower() == encontrados[0])
    return None

# ============================================================
# MODELO DE PROBABILIDADES
# ============================================================

def ajuste_empates_baixos(df: pd.DataFrame) -> float:
    try:
        total = max(1, len(df))
        p00 = len(df[(df["HG"] == 0) & (df["AG"] == 0)]) / total
        p11 = len(df[(df["HG"] == 1) & (df["AG"] == 1)]) / total
        return float(np.clip((p00 - 0.10) + (p11 - 0.12), -0.10, 0.10))
    except Exception:
        return 0.0


def fator_placar_baixo(gols_casa: int, gols_fora: int, correcao: float) -> float:
    if gols_casa == 0 and gols_fora == 0:
        return 1.0 - correcao
    if gols_casa == 1 and gols_fora == 0:
        return 1.0 + (correcao * 0.5)
    if gols_casa == 0 and gols_fora == 1:
        return 1.0 + (correcao * 0.5)
    if gols_casa == 1 and gols_fora == 1:
        return 1.0 - (correcao * 0.25)
    return 1.0


def precificar_jogo(df: pd.DataFrame, time_casa: str, time_fora: str) -> Tuple[float, float, Dict[str, float], float, Dict[str, int]]:
    media_casa = float(np.average(df["HG"], weights=df["Peso"]))
    media_fora = float(np.average(df["AG"], weights=df["Peso"]))
    media_casa = max(media_casa, 0.20)
    media_fora = max(media_fora, 0.20)

    casa_em_casa = df[df["Home"] == time_casa]
    casa_fora = df[df["Away"] == time_casa]
    fora_em_casa = df[df["Home"] == time_fora]
    fora_fora = df[df["Away"] == time_fora]

    n_casa_mando = len(casa_em_casa)
    n_fora_mando = len(fora_fora)
    n_casa_total = n_casa_mando + len(casa_fora)
    n_fora_total = n_fora_mando + len(fora_em_casa)

    gols_casa_feitos_geral = pd.concat([casa_em_casa["HG"], casa_fora["AG"]])
    gols_casa_sofridos_geral = pd.concat([casa_em_casa["AG"], casa_fora["HG"]])
    pesos_casa_geral = pd.concat([casa_em_casa["Peso"], casa_fora["Peso"]])

    gols_fora_feitos_geral = pd.concat([fora_em_casa["HG"], fora_fora["AG"]])
    gols_fora_sofridos_geral = pd.concat([fora_em_casa["AG"], fora_fora["HG"]])
    pesos_fora_geral = pd.concat([fora_em_casa["Peso"], fora_fora["Peso"]])

    ataque_casa_geral = np.average(gols_casa_feitos_geral, weights=pesos_casa_geral) if len(gols_casa_feitos_geral) else media_casa
    defesa_casa_geral = np.average(gols_casa_sofridos_geral, weights=pesos_casa_geral) if len(gols_casa_sofridos_geral) else media_fora
    ataque_fora_geral = np.average(gols_fora_feitos_geral, weights=pesos_fora_geral) if len(gols_fora_feitos_geral) else media_fora
    defesa_fora_geral = np.average(gols_fora_sofridos_geral, weights=pesos_fora_geral) if len(gols_fora_sofridos_geral) else media_casa

    ataque_casa_mando = np.average(casa_em_casa["HG"], weights=casa_em_casa["Peso"]) if n_casa_mando >= 4 else media_casa
    defesa_casa_mando = np.average(casa_em_casa["AG"], weights=casa_em_casa["Peso"]) if n_casa_mando >= 4 else media_fora
    ataque_fora_mando = np.average(fora_fora["AG"], weights=fora_fora["Peso"]) if n_fora_mando >= 4 else media_fora
    defesa_fora_mando = np.average(fora_fora["HG"], weights=fora_fora["Peso"]) if n_fora_mando >= 4 else media_casa

    peso_casa = min(0.78, n_casa_mando / 11.0)
    peso_fora = min(0.78, n_fora_mando / 11.0)

    ataque_casa = ataque_casa_mando * peso_casa + ataque_casa_geral * (1 - peso_casa)
    defesa_casa = defesa_casa_mando * peso_casa + defesa_casa_geral * (1 - peso_casa)
    ataque_fora = ataque_fora_mando * peso_fora + ataque_fora_geral * (1 - peso_fora)
    defesa_fora = defesa_fora_mando * peso_fora + defesa_fora_geral * (1 - peso_fora)

    # Puxa para a média da liga quando a amostra é pequena.
    forca_regularizacao = 8.0
    ataque_casa = ((n_casa_mando * ataque_casa) + (forca_regularizacao * media_casa)) / (n_casa_mando + forca_regularizacao)
    defesa_casa = ((n_casa_mando * defesa_casa) + (forca_regularizacao * media_fora)) / (n_casa_mando + forca_regularizacao)
    ataque_fora = ((n_fora_mando * ataque_fora) + (forca_regularizacao * media_fora)) / (n_fora_mando + forca_regularizacao)
    defesa_fora = ((n_fora_mando * defesa_fora) + (forca_regularizacao * media_casa)) / (n_fora_mando + forca_regularizacao)

    forca_ataque_casa = ataque_casa / media_casa
    forca_defesa_casa = defesa_casa / media_fora
    forca_ataque_fora = ataque_fora / media_fora
    forca_defesa_fora = defesa_fora / media_casa

    gols_esperados_casa = float(np.clip(media_casa * forca_ataque_casa * forca_defesa_fora, 0.20, 4.20))
    gols_esperados_fora = float(np.clip(media_fora * forca_ataque_fora * forca_defesa_casa, 0.20, 4.20))

    tamanho = 20
    matriz = np.zeros((tamanho, tamanho))
    correcao = ajuste_empates_baixos(df)
    for i in range(tamanho):
        for j in range(tamanho):
            base = poisson.pmf(i, gols_esperados_casa) * poisson.pmf(j, gols_esperados_fora)
            matriz[i, j] = base * fator_placar_baixo(i, j, correcao)

    soma = matriz.sum()
    if soma > 0:
        matriz = matriz / soma

    p_casa = float(np.tril(matriz, -1).sum())
    p_empate = float(np.diag(matriz).sum())
    p_fora = float(np.triu(matriz, 1).sum())
    p_mais_25 = float(matriz[np.add.outer(np.arange(tamanho), np.arange(tamanho)) >= 3].sum())
    p_ambos = float(matriz[1:, 1:].sum())

    probs = {
        "Vitória Casa": p_casa,
        "Empate": p_empate,
        "Vitória Fora": p_fora,
        "Mais de 2.5 gols": p_mais_25,
        "Menos de 2.5 gols": 1.0 - p_mais_25,
        "Ambos marcam - Sim": p_ambos,
        "Ambos marcam - Não": 1.0 - p_ambos,
        "Casa ou Empate": p_casa + p_empate,
        "Fora ou Empate": p_fora + p_empate,
    }

    sem_empate = p_casa + p_fora
    probs["Empate anula - Casa"] = p_casa / sem_empate if sem_empate > 0 else 0.0
    probs["Empate anula - Fora"] = p_fora / sem_empate if sem_empate > 0 else 0.0

    variancia_casa = float(np.var(gols_casa_feitos_geral)) if len(gols_casa_feitos_geral) > 1 else 1.5
    variancia_fora = float(np.var(gols_fora_feitos_geral)) if len(gols_fora_feitos_geral) > 1 else 1.5
    estabilidade = np.clip(1.0 - (((variancia_casa + variancia_fora) / 2.0) / 5.5), 0.0, 1.0)
    volume_mando = np.clip(min(n_casa_mando, n_fora_mando) / 12.0, 0.0, 1.0)
    volume_total = np.clip(min(n_casa_total, n_fora_total) / 24.0, 0.0, 1.0)
    equilibrio = min(n_casa_mando, n_fora_mando) / max(1, max(n_casa_mando, n_fora_mando))

    confianca = 50 * volume_mando + 20 * volume_total + 20 * estabilidade + 10 * equilibrio
    confianca = float(np.clip(confianca, 0.0, 100.0))

    amostra = {
        "casa_mando": n_casa_mando,
        "fora_mando": n_fora_mando,
        "casa_total": n_casa_total,
        "fora_total": n_fora_total,
    }
    return gols_esperados_casa, gols_esperados_fora, probs, confianca, amostra

# ============================================================
# COTAÇÕES E PROBABILIDADE DO MERCADO
# ============================================================

def retirar_margem(cotacoes: Dict[str, float], grupo: List[str]) -> Dict[str, float]:
    if not all(m in cotacoes and cotacoes[m] and cotacoes[m] > 1.01 for m in grupo):
        return {}
    inversos = {m: 1 / cotacoes[m] for m in grupo}
    total = sum(inversos.values())
    if total <= 0:
        return {}
    return {m: inversos[m] / total for m in grupo}


def montar_linhas_manuais() -> Dict[str, Dict[str, float]]:
    st.markdown("### Preencha as cotações reais")
    st.caption("Pode preencher só os mercados que você quer analisar. Quanto mais completo, melhor.")

    cotacoes = {}

    with st.expander("Resultado do jogo", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            valor = ler_cotacao("Vitória casa", "cot_vitoria_casa")
            if valor: cotacoes["Vitória Casa"] = valor
        with c2:
            valor = ler_cotacao("Empate", "cot_empate")
            if valor: cotacoes["Empate"] = valor
        with c3:
            valor = ler_cotacao("Vitória fora", "cot_vitoria_fora")
            if valor: cotacoes["Vitória Fora"] = valor

    with st.expander("Gols", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            valor = ler_cotacao("Mais de 2.5 gols", "cot_mais25")
            if valor: cotacoes["Mais de 2.5 gols"] = valor
        with c2:
            valor = ler_cotacao("Menos de 2.5 gols", "cot_menos25")
            if valor: cotacoes["Menos de 2.5 gols"] = valor

    with st.expander("Ambos marcam", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            valor = ler_cotacao("Ambos marcam - Sim", "cot_ambos_sim")
            if valor: cotacoes["Ambos marcam - Sim"] = valor
        with c2:
            valor = ler_cotacao("Ambos marcam - Não", "cot_ambos_nao")
            if valor: cotacoes["Ambos marcam - Não"] = valor

    with st.expander("Proteções", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            valor = ler_cotacao("Casa ou empate", "cot_casa_empate")
            if valor: cotacoes["Casa ou Empate"] = valor
        with c2:
            valor = ler_cotacao("Fora ou empate", "cot_fora_empate")
            if valor: cotacoes["Fora ou Empate"] = valor
        c3, c4 = st.columns(2)
        with c3:
            valor = ler_cotacao("Empate anula - Casa", "cot_dnb_casa")
            if valor: cotacoes["Empate anula - Casa"] = valor
        with c4:
            valor = ler_cotacao("Empate anula - Fora", "cot_dnb_fora")
            if valor: cotacoes["Empate anula - Fora"] = valor

    prob_mercado = {}
    grupos = [
        ["Vitória Casa", "Empate", "Vitória Fora"],
        ["Mais de 2.5 gols", "Menos de 2.5 gols"],
        ["Ambos marcam - Sim", "Ambos marcam - Não"],
        ["Empate anula - Casa", "Empate anula - Fora"],
    ]
    for grupo in grupos:
        limpo = retirar_margem(cotacoes, grupo)
        if limpo:
            prob_mercado.update(limpo)
        else:
            for m in grupo:
                if m in cotacoes:
                    prob_mercado[m] = 1 / cotacoes[m]

    # Dupla chance não é par oposto perfeito. Usa 1/cotação para não maquiar.
    for m in ["Casa ou Empate", "Fora ou Empate"]:
        if m in cotacoes:
            prob_mercado[m] = 1 / cotacoes[m]

    return {m: {"cotacao": cotacoes[m], "prob_mercado": prob_mercado[m], "origem": "Manual"} for m in cotacoes if m in prob_mercado}


def montar_linhas_api(jogo: dict) -> Dict[str, Dict[str, float]]:
    grupos = {m: [] for m in [
        "Vitória Casa", "Empate", "Vitória Fora", "Mais de 2.5 gols",
        "Menos de 2.5 gols", "Ambos marcam - Sim", "Ambos marcam - Não"
    ]}

    for casa in jogo.get("bookmakers", []):
        chave_casa = casa.get("key", "").lower()
        if chave_casa in CASAS_BLOQUEADAS:
            continue
        for mercado in casa.get("markets", []):
            chave = mercado.get("key")
            for item in mercado.get("outcomes", []):
                cotacao = cotacao_valida(item.get("price"))
                if cotacao is None:
                    continue
                nome = item.get("name")
                if chave == "h2h":
                    if nome == jogo.get("home_team"):
                        grupos["Vitória Casa"].append(cotacao)
                    elif nome == "Draw":
                        grupos["Empate"].append(cotacao)
                    elif nome == jogo.get("away_team"):
                        grupos["Vitória Fora"].append(cotacao)
                elif chave == "totals":
                    try:
                        if abs(float(item.get("point", 0)) - 2.5) > 1e-9:
                            continue
                    except Exception:
                        continue
                    if nome == "Over":
                        grupos["Mais de 2.5 gols"].append(cotacao)
                    elif nome == "Under":
                        grupos["Menos de 2.5 gols"].append(cotacao)
                elif chave == "btts":
                    if nome == "Yes":
                        grupos["Ambos marcam - Sim"].append(cotacao)
                    elif nome == "No":
                        grupos["Ambos marcam - Não"].append(cotacao)

    cotacoes = {}
    for m, lista in grupos.items():
        lista = [x for x in lista if x and x > 1.01]
        if lista:
            cotacoes[m] = float(np.median(lista))

    prob_mercado = {}
    for grupo in [
        ["Vitória Casa", "Empate", "Vitória Fora"],
        ["Mais de 2.5 gols", "Menos de 2.5 gols"],
        ["Ambos marcam - Sim", "Ambos marcam - Não"],
    ]:
        prob_mercado.update(retirar_margem(cotacoes, grupo))

    return {m: {"cotacao": cotacoes[m], "prob_mercado": prob_mercado[m], "origem": "API"} for m in cotacoes if m in prob_mercado}

# ============================================================
# AVALIAÇÃO DAS ENTRADAS
# ============================================================

def nome_mercado(mercado: str, time_casa: str, time_fora: str) -> str:
    mapa = {
        "Vitória Casa": f"Vitória {time_casa}",
        "Vitória Fora": f"Vitória {time_fora}",
        "Empate": "Empate",
        "Mais de 2.5 gols": "Mais de 2.5 gols",
        "Menos de 2.5 gols": "Menos de 2.5 gols",
        "Ambos marcam - Sim": "Ambos marcam - Sim",
        "Ambos marcam - Não": "Ambos marcam - Não",
        "Casa ou Empate": f"{time_casa} ou empate",
        "Fora ou Empate": f"{time_fora} ou empate",
        "Empate anula - Casa": f"Empate anula — {time_casa}",
        "Empate anula - Fora": f"Empate anula — {time_fora}",
    }
    return mapa.get(mercado, mercado)


def desconto_de_segurança(confianca: float, cotacao: float) -> float:
    desconto = 0.008 + ((100 - confianca) / 100) * 0.028
    if cotacao >= 3.00:
        desconto += 0.010
    if cotacao >= 5.00:
        desconto += 0.010
    return float(np.clip(desconto, 0.008, 0.060))


def calcular_percentual_entrada(prob_modelo: float, cotacao: float, confianca: float, agressividade: float, maximo: float) -> float:
    ganho = cotacao - 1.0
    if ganho <= 0:
        return 0.0
    valor = (prob_modelo * cotacao) - 1.0
    if valor <= 0:
        return 0.0

    base = (valor / ganho) * agressividade
    base *= np.clip(confianca / 85.0, 0.45, 1.15)

    if cotacao >= 3.00:
        base *= 0.70
    if cotacao >= 5.00:
        base *= 0.55

    # Se foi aprovado, evita entrada ridiculamente pequena.
    if base > 0:
        base = max(base, 0.004)

    return float(np.clip(base, 0.0, maximo))


def avaliar_mercados(
    linhas: Dict[str, Dict[str, float]],
    probs_modelo: Dict[str, float],
    confianca: float,
    banca_atual: float,
    minimo_confianca: float,
    minimo_valor: float,
    minimo_vantagem: float,
    agressividade: float,
    maximo_por_aposta: float,
    maximo_por_jogo: float,
    maximo_entradas: int,
    cotacao_minima: float,
    cotacao_maxima: float,
) -> List[dict]:
    resultados = []

    for mercado in ORDEM_MERCADOS:
        if mercado not in linhas or mercado not in probs_modelo:
            continue
        cotacao = float(linhas[mercado]["cotacao"])
        prob_modelo = float(probs_modelo[mercado])
        prob_mercado = float(linhas[mercado]["prob_mercado"])
        cotacao_justa = np.inf if prob_modelo <= 0 else 1 / prob_modelo
        valor_esperado = (prob_modelo * cotacao) - 1
        vantagem = prob_modelo - prob_mercado
        desc = desconto_de_segurança(confianca, cotacao)
        prob_segura = max(0.0, prob_modelo - desc)
        valor_seguro = (prob_segura * cotacao) - 1

        motivos = []
        aprovado = True

        if cotacao < cotacao_minima or cotacao > cotacao_maxima:
            aprovado = False
            motivos.append("cotação fora da faixa escolhida")
        if confianca < minimo_confianca:
            aprovado = False
            motivos.append("poucos dados confiáveis para este jogo")
        if valor_esperado < minimo_valor:
            aprovado = False
            motivos.append("valor esperado insuficiente")
        if vantagem < minimo_vantagem:
            aprovado = False
            motivos.append("vantagem pequena contra o mercado")

        # Não trava por divergência alta. Divergência alta pode ser justamente oportunidade.
        # Apenas reduz o tamanho da entrada quando a margem de segurança ficar ruim.
        if cotacao >= 3.00 and valor_seguro < -0.06:
            aprovado = False
            motivos.append("cotação alta com margem de segurança ruim")
        elif valor_seguro < -0.10:
            aprovado = False
            motivos.append("margem de segurança muito ruim")

        percentual = 0.0
        if aprovado:
            percentual = calcular_percentual_entrada(
                prob_modelo=prob_modelo,
                cotacao=cotacao,
                confianca=confianca,
                agressividade=agressividade,
                maximo=maximo_por_aposta,
            )
            if percentual <= 0:
                aprovado = False
                motivos.append("valor positivo, mas pequeno demais para entrada")

        resultados.append({
            "mercado": mercado,
            "cotacao": cotacao,
            "prob_modelo": prob_modelo,
            "prob_mercado": prob_mercado,
            "prob_segura": prob_segura,
            "cotacao_justa": cotacao_justa,
            "valor_esperado": valor_esperado,
            "valor_seguro": valor_seguro,
            "vantagem": vantagem,
            "confianca": confianca,
            "apostar": aprovado,
            "percentual": percentual if aprovado else 0.0,
            "entrada_reais": banca_atual * percentual if aprovado else 0.0,
            "motivo": "Boa oportunidade dentro dos filtros atuais." if aprovado else "; ".join(motivos),
            "origem": linhas[mercado]["origem"],
        })

    # Organiza os aprovados primeiro e limita pelo total máximo por jogo.
    aprovados = [r for r in resultados if r["apostar"]]
    aprovados = sorted(aprovados, key=lambda r: (r["valor_seguro"], r["valor_esperado"], r["vantagem"]), reverse=True)

    escolhidos = []
    soma = 0.0
    for r in aprovados:
        if len(escolhidos) >= maximo_entradas:
            r["apostar"] = False
            r["percentual"] = 0.0
            r["entrada_reais"] = 0.0
            r["motivo"] = "ficou fora do limite de entradas por jogo"
            continue
        if soma + r["percentual"] > maximo_por_jogo:
            # Tenta reduzir para caber, se ainda ficar uma entrada útil.
            restante = maximo_por_jogo - soma
            if restante >= 0.004:
                r["percentual"] = restante
                r["entrada_reais"] = banca_atual * restante
                escolhidos.append(r)
                soma += restante
            else:
                r["apostar"] = False
                r["percentual"] = 0.0
                r["entrada_reais"] = 0.0
                r["motivo"] = "ficou fora do limite total de exposição no jogo"
            continue
        escolhidos.append(r)
        soma += r["percentual"]

    escolhidos_ids = {id(r) for r in escolhidos}
    for r in resultados:
        if r["apostar"] and id(r) not in escolhidos_ids:
            r["apostar"] = False
            r["percentual"] = 0.0
            r["entrada_reais"] = 0.0
            if "limite" not in r["motivo"]:
                r["motivo"] = "ficou fora dos limites de risco do jogo"

    return sorted(resultados, key=lambda r: (r["apostar"], r["valor_esperado"]), reverse=True)

# ============================================================
# AUDITORIA
# ============================================================

def garantir_auditoria() -> None:
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists(CAMINHO_AUDITORIA):
        pd.DataFrame(columns=COLUNAS_AUDITORIA).to_csv(CAMINHO_AUDITORIA, index=False)


def carregar_auditoria() -> pd.DataFrame:
    garantir_auditoria()
    try:
        df = pd.read_csv(CAMINHO_AUDITORIA)
        for c in COLUNAS_AUDITORIA:
            if c not in df.columns:
                df[c] = np.nan
        return df[COLUNAS_AUDITORIA]
    except Exception:
        return pd.DataFrame(columns=COLUNAS_AUDITORIA)


def salvar_auditoria(df: pd.DataFrame) -> None:
    garantir_auditoria()
    df[COLUNAS_AUDITORIA].to_csv(CAMINHO_AUDITORIA, index=False)


def banca_pela_auditoria(banca_inicial: float, auditoria: pd.DataFrame) -> float:
    if auditoria.empty:
        return banca_inicial
    resultados = pd.to_numeric(auditoria["Resultado R$"], errors="coerce").fillna(0.0)
    return float(banca_inicial + resultados.sum())


def registrar_entrada(liga: str, data_jogo: date, jogo: str, casa: str, item: dict, banca_atual: float, observacao: str = "") -> None:
    auditoria = carregar_auditoria()
    novo = {
        "ID": str(uuid.uuid4())[:8],
        "Data registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Data jogo": data_jogo.strftime("%d/%m/%Y") if isinstance(data_jogo, date) else str(data_jogo),
        "Liga": liga,
        "Jogo": jogo,
        "Casa": casa,
        "Mercado": item["nome_exibicao"],
        "Cotação entrada": round(item["cotacao"], 3),
        "Cotação fechamento": np.nan,
        "Vantagem fechamento %": np.nan,
        "Entrada %": round(item["percentual"] * 100, 3),
        "Entrada R$": round(item["entrada_reais"], 2),
        "Banca antes": round(banca_atual, 2),
        "Banca depois": np.nan,
        "Probabilidade modelo %": round(item["prob_modelo"] * 100, 2),
        "Probabilidade mercado %": round(item["prob_mercado"] * 100, 2),
        "Cotação justa": round(item["cotacao_justa"], 3) if np.isfinite(item["cotacao_justa"]) else np.nan,
        "Valor esperado %": round(item["valor_esperado"] * 100, 2),
        "Confiança %": round(item["confianca"], 2),
        "Status": "Pendente",
        "Resultado R$": 0.0,
        "Observações": observacao,
    }
    auditoria = pd.concat([auditoria, pd.DataFrame([novo])], ignore_index=True)
    salvar_auditoria(auditoria)


def fechar_entrada(id_entrada: str, status: str, cotacao_fechamento: Optional[float], cashout: Optional[float], observacao: str) -> None:
    auditoria = carregar_auditoria()
    idx_lista = auditoria.index[auditoria["ID"].astype(str) == str(id_entrada)].tolist()
    if not idx_lista:
        return
    idx = idx_lista[0]
    entrada = float(pd.to_numeric(auditoria.loc[idx, "Entrada R$"], errors="coerce") or 0)
    cotacao_entrada = float(pd.to_numeric(auditoria.loc[idx, "Cotação entrada"], errors="coerce") or 0)
    banca_antes = float(pd.to_numeric(auditoria.loc[idx, "Banca antes"], errors="coerce") or 0)

    if status == "Ganhou":
        resultado = entrada * (cotacao_entrada - 1)
    elif status == "Perdeu":
        resultado = -entrada
    elif status == "Anulada":
        resultado = 0.0
    elif status == "Encerrada antes":
        resultado = (cashout or 0.0) - entrada
    else:
        resultado = 0.0

    vantagem_fechamento = np.nan
    if cotacao_fechamento and cotacao_fechamento > 1.01 and cotacao_entrada > 1.01:
        vantagem_fechamento = ((cotacao_entrada / cotacao_fechamento) - 1) * 100

    auditoria.loc[idx, "Status"] = status
    auditoria.loc[idx, "Cotação fechamento"] = cotacao_fechamento if cotacao_fechamento else np.nan
    auditoria.loc[idx, "Vantagem fechamento %"] = vantagem_fechamento
    auditoria.loc[idx, "Resultado R$"] = round(resultado, 2)
    auditoria.loc[idx, "Banca depois"] = round(banca_antes + resultado, 2)
    auditoria.loc[idx, "Observações"] = observacao
    salvar_auditoria(auditoria)

# ============================================================
# CARD DE RESULTADO
# ============================================================

def montar_card(item: dict) -> str:
    apostar = item["apostar"]
    classe = "card-apostar" if apostar else "card-nao"
    status_classe = "status-apostar" if apostar else "status-nao"
    status = f"✅ APOSTAR {item['percentual'] * 100:.2f}% DA BANCA" if apostar else "❌ NÃO APOSTAR"
    status = status.replace(".", ",")
    cot_justa = "--" if not np.isfinite(item["cotacao_justa"]) else numero_texto(item["cotacao_justa"], 2)

    html = f"""
    <div class="{classe}">
        <div class="{status_classe}">{status}</div>
        <div class="mercado-titulo">{item['nome_exibicao']}</div>
        <div class="grade-card">
            <div class="mini-box"><div class="mini-label">Cotação da casa</div><div class="mini-value">{numero_texto(item['cotacao'], 2)}</div></div>
            <div class="mini-box"><div class="mini-label">Cotação justa</div><div class="mini-value">{cot_justa}</div></div>
            <div class="mini-box"><div class="mini-label">Chance pelo sistema</div><div class="mini-value">{pct(item['prob_modelo'])}</div></div>
            <div class="mini-box"><div class="mini-label">Chance do mercado</div><div class="mini-value">{pct(item['prob_mercado'])}</div></div>
            <div class="mini-box"><div class="mini-label">Valor esperado</div><div class="mini-value">{pct(item['valor_esperado'])}</div></div>
            <div class="mini-box"><div class="mini-label">Entrada sugerida</div><div class="mini-value">{dinheiro(item['entrada_reais']) if apostar else '-'}</div></div>
        </div>
        <div class="motivo-box"><b>Leitura:</b> {item['motivo']}</div>
    </div>
    """
    return html

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================

st.markdown('<div class="main-title">TEX STATISTICS PRO 14.3</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Análise clara por blocos, banca dinâmica e auditoria das entradas.</div>', unsafe_allow_html=True)

aba_analise, aba_auditoria = st.tabs(["🎯 Analisar jogo", "📒 Auditoria"])

auditoria_df = carregar_auditoria()

with st.sidebar:
    st.header("Banca")
    banca_inicial = st.number_input("Banca inicial", min_value=0.0, value=1000.0, step=50.0)
    banca_calculada = banca_pela_auditoria(banca_inicial, auditoria_df)
    usar_banca_calculada = st.checkbox("Usar banca pela auditoria", value=True)
    banca_manual = st.number_input("Banca atual manual", min_value=0.0, value=1000.0, step=50.0)
    banca_atual = banca_calculada if usar_banca_calculada else banca_manual
    st.metric("Banca usada", dinheiro(banca_atual))

    st.divider()
    st.header("Filtro de entradas")
    perfil = st.selectbox("Perfil", ["Mais entradas", "Equilibrado", "Mais seguro"], index=0)
    if perfil == "Mais entradas":
        pad_conf, pad_valor, pad_vantagem, pad_agress = 50.0, 0.015, 0.005, 0.15
    elif perfil == "Equilibrado":
        pad_conf, pad_valor, pad_vantagem, pad_agress = 60.0, 0.025, 0.012, 0.12
    else:
        pad_conf, pad_valor, pad_vantagem, pad_agress = 70.0, 0.040, 0.020, 0.10

    minimo_confianca = st.slider("Confiança mínima", 0.0, 100.0, pad_conf, 1.0)
    minimo_valor = st.slider("Valor esperado mínimo", -0.05, 0.20, pad_valor, 0.005)
    minimo_vantagem = st.slider("Vantagem mínima contra o mercado", -0.05, 0.15, pad_vantagem, 0.005)

    st.divider()
    st.header("Limites da banca")
    agressividade = st.slider("Agressividade da entrada", 0.03, 0.30, pad_agress, 0.01)
    maximo_por_aposta = st.slider("Máximo por aposta", 0.005, 0.03, 0.03, 0.001)
    maximo_entradas = st.slider("Máximo de entradas no jogo", 1, 8, 5, 1)
    maximo_por_jogo = st.slider("Total máximo no mesmo jogo", 0.01, 0.15, 0.09, 0.005)
    cotacao_minima = st.slider("Cotação mínima", 1.05, 3.00, 1.15, 0.05)
    cotacao_maxima = st.slider("Cotação máxima", 1.50, 15.00, 7.00, 0.50)

    st.divider()
    st.header("Dados")
    liga = st.selectbox("Liga", list(LIGAS_CSV.keys()))
    chave_api = st.text_input("Chave da API de cotações", type="password")

with st.spinner("Carregando jogos históricos..."):
    historico = carregar_historico(LIGAS_CSV[liga])

if historico.empty:
    st.error("Não consegui carregar os dados históricos desta liga.")
    st.stop()

times = sorted(historico["Home"].dropna().unique().tolist())

with aba_analise:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jogos históricos", len(historico))
    c2.metric("Times", len(times))
    c3.metric("Gols casa", numero_texto(float(np.average(historico["HG"], weights=historico["Peso"])), 2))
    c4.metric("Gols fora", numero_texto(float(np.average(historico["AG"], weights=historico["Peso"])), 2))

    st.markdown("---")
    modo = st.radio(
        "Como você quer analisar?",
        ["Manual", "Automática pela API"],
        horizontal=True,
        index=0,
    )

    time_casa = None
    time_fora = None
    data_jogo = date.today()
    linhas = {}
    jogo_nome = ""

    if modo == "Manual":
        st.markdown("### Escolha o jogo")
        c1, c2, c3 = st.columns([1, 1, 0.8])
        with c1:
            time_casa = st.selectbox("Time da casa", times, key="time_casa_manual")
        with c2:
            time_fora = st.selectbox("Time de fora", times, key="time_fora_manual")
        with c3:
            data_jogo = st.date_input("Data do jogo", value=date.today())

        if time_casa == time_fora:
            st.warning("Escolha times diferentes.")
        else:
            linhas = montar_linhas_manuais()
            analisar = st.button("ANALISAR JOGO MANUAL", type="primary", use_container_width=True)
            jogo_nome = f"{time_casa} x {time_fora}"

    else:
        st.markdown("### Automática pela API")
        st.markdown(
            '<div class="aviso-simples">Se a API não mostrar jogos, use o modo Manual. Isso não quer dizer, necessariamente, que sua chave está errada. Pode ser que a liga esteja sem jogo aberto ou sem cotação disponível agora.</div>',
            unsafe_allow_html=True,
        )
        analisar = False
        if not chave_api.strip():
            st.warning("Digite a chave da API na barra lateral ou escolha o modo Manual.")
        else:
            dados_api = buscar_api(chave_api, LIGAS_API[liga])
            if not dados_api:
                st.warning("API sem dados disponíveis para esta liga agora. Use o modo Manual para analisar com as cotações da Pixbet/Pinnacle.")
            else:
                agora = pd.Timestamp.now(tz="UTC")
                jogos_validos = {}
                for jogo in dados_api:
                    try:
                        inicio = pd.to_datetime(jogo.get("commence_time"), utc=True)
                        if inicio <= agora:
                            continue
                        horario = inicio.tz_convert("America/Sao_Paulo").strftime("%d/%m %H:%M")
                        label = f"{jogo.get('home_team')} x {jogo.get('away_team')} — {horario}"
                        jogos_validos[label] = jogo
                    except Exception:
                        continue

                if not jogos_validos:
                    st.warning("A API respondeu, mas não há partidas pré-jogo disponíveis agora.")
                else:
                    escolha = st.selectbox("Jogo encontrado", list(jogos_validos.keys()))
                    jogo = jogos_validos[escolha]
                    casa_sugerida = achar_time(jogo.get("home_team", ""), times) or times[0]
                    fora_sugerida = achar_time(jogo.get("away_team", ""), times) or times[min(1, len(times) - 1)]
                    c1, c2 = st.columns(2)
                    with c1:
                        time_casa = st.selectbox("Time da casa na base", times, index=times.index(casa_sugerida), key="time_casa_api")
                    with c2:
                        time_fora = st.selectbox("Time de fora na base", times, index=times.index(fora_sugerida), key="time_fora_api")
                    linhas = montar_linhas_api(jogo)
                    jogo_nome = f"{time_casa} x {time_fora}"
                    data_jogo = date.today()
                    st.info(f"Foram encontradas {len(linhas)} cotações reais pela API para este jogo.")
                    analisar = st.button("ANALISAR JOGO AUTOMÁTICO", type="primary", use_container_width=True)

    if 'analisar' in locals() and analisar:
        if not time_casa or not time_fora or time_casa == time_fora:
            st.error("Escolha corretamente os dois times.")
        elif not linhas:
            st.error("Nenhuma cotação válida foi preenchida ou encontrada.")
        else:
            gols_casa, gols_fora, probs_modelo, confianca, amostra = precificar_jogo(historico, time_casa, time_fora)
            resultados = avaliar_mercados(
                linhas=linhas,
                probs_modelo=probs_modelo,
                confianca=confianca,
                banca_atual=banca_atual,
                minimo_confianca=minimo_confianca,
                minimo_valor=minimo_valor,
                minimo_vantagem=minimo_vantagem,
                agressividade=agressividade,
                maximo_por_aposta=maximo_por_aposta,
                maximo_por_jogo=maximo_por_jogo,
                maximo_entradas=maximo_entradas,
                cotacao_minima=cotacao_minima,
                cotacao_maxima=cotacao_maxima,
            )

            for r in resultados:
                r["nome_exibicao"] = nome_mercado(r["mercado"], time_casa, time_fora)

            aprovadas = [r for r in resultados if r["apostar"]]

            st.markdown("---")
            st.markdown(f"## Análise — {jogo_nome}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Força de gols casa", numero_texto(gols_casa, 2))
            c2.metric("Força de gols fora", numero_texto(gols_fora, 2))
            c3.metric("Confiança", pct(confianca / 100.0))
            c4.metric("Entradas aprovadas", len(aprovadas))
            st.caption(f"Amostra: {time_casa} em casa {amostra['casa_mando']} jogos | {time_fora} fora {amostra['fora_mando']} jogos.")

            if aprovadas:
                st.success(f"Foram encontradas {len(aprovadas)} entradas dentro dos filtros atuais.")
            else:
                st.warning("Nenhuma entrada passou. Para buscar mais entradas, use o perfil 'Mais entradas' ou reduza os filtros na barra lateral.")

            st.markdown("### Blocos por mercado")
            for item in resultados:
                st.markdown(montar_card(item), unsafe_allow_html=True)
                if item["apostar"]:
                    col_b1, col_b2 = st.columns([1, 1])
                    with col_b1:
                        casa_aposta = st.selectbox(
                            "Casa para registrar",
                            ["Pixbet", "Pinnacle", "Bet365", "Betano", "KTO", "Superbet", "Outra"],
                            key=f"casa_{item['mercado']}",
                        )
                    with col_b2:
                        obs = st.text_input("Observação", key=f"obs_{item['mercado']}", placeholder="Opcional")
                    if st.button(f"Registrar entrada: {item['nome_exibicao']}", key=f"reg_{item['mercado']}", use_container_width=True):
                        registrar_entrada(liga, data_jogo, jogo_nome, casa_aposta, item, banca_atual, obs)
                        st.success("Entrada registrada na auditoria.")

with aba_auditoria:
    st.markdown("## Auditoria das entradas")
    auditoria_df = carregar_auditoria()
    banca_atualizada = banca_pela_auditoria(banca_inicial, auditoria_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Banca pela auditoria", dinheiro(banca_atualizada))
    c2.metric("Entradas registradas", len(auditoria_df))
    resultado_total = pd.to_numeric(auditoria_df["Resultado R$"], errors="coerce").fillna(0).sum() if not auditoria_df.empty else 0
    c3.metric("Resultado total", dinheiro(float(resultado_total)))
    pendentes = len(auditoria_df[auditoria_df["Status"].astype(str) == "Pendente"]) if not auditoria_df.empty else 0
    c4.metric("Pendentes", pendentes)

    st.markdown("---")
    st.markdown("### Registrar entrada manual na auditoria")
    with st.expander("Adicionar entrada feita fora do motor", expanded=False):
        with st.form("form_manual_auditoria"):
            c1, c2 = st.columns(2)
            with c1:
                data_manual = st.date_input("Data do jogo", value=date.today(), key="aud_data")
                jogo_manual = st.text_input("Jogo", placeholder="Ex.: Botafogo x Santos")
                mercado_manual = st.text_input("Mercado", placeholder="Ex.: Ambos marcam - Sim")
                casa_manual = st.selectbox("Casa", ["Pixbet", "Pinnacle", "Bet365", "Betano", "KTO", "Superbet", "Outra"], key="aud_casa")
            with c2:
                cot_manual = st.text_input("Cotação de entrada", placeholder="Ex.: 1,85")
                entrada_percentual = st.number_input("Entrada % da banca", min_value=0.0, max_value=3.0, value=1.0, step=0.1)
                banca_antes_manual = st.number_input("Banca antes", min_value=0.0, value=float(banca_atualizada), step=50.0)
                obs_manual = st.text_input("Observação", placeholder="Opcional")
            salvar_manual = st.form_submit_button("Salvar entrada manual")

        if salvar_manual:
            cot = texto_para_float(cot_manual)
            if not jogo_manual or not mercado_manual or not cot or cot <= 1.01:
                st.error("Preencha jogo, mercado e cotação válida.")
            else:
                auditoria = carregar_auditoria()
                valor_reais = banca_antes_manual * (entrada_percentual / 100)
                novo = {
                    "ID": str(uuid.uuid4())[:8],
                    "Data registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Data jogo": data_manual.strftime("%d/%m/%Y"),
                    "Liga": liga,
                    "Jogo": jogo_manual,
                    "Casa": casa_manual,
                    "Mercado": mercado_manual,
                    "Cotação entrada": round(cot, 3),
                    "Cotação fechamento": np.nan,
                    "Vantagem fechamento %": np.nan,
                    "Entrada %": round(entrada_percentual, 3),
                    "Entrada R$": round(valor_reais, 2),
                    "Banca antes": round(banca_antes_manual, 2),
                    "Banca depois": np.nan,
                    "Probabilidade modelo %": np.nan,
                    "Probabilidade mercado %": np.nan,
                    "Cotação justa": np.nan,
                    "Valor esperado %": np.nan,
                    "Confiança %": np.nan,
                    "Status": "Pendente",
                    "Resultado R$": 0.0,
                    "Observações": obs_manual,
                }
                auditoria = pd.concat([auditoria, pd.DataFrame([novo])], ignore_index=True)
                salvar_auditoria(auditoria)
                st.success("Entrada manual salva.")

    st.markdown("### Fechar resultado")
    auditoria_df = carregar_auditoria()
    pendentes_df = auditoria_df[auditoria_df["Status"].astype(str) == "Pendente"].copy() if not auditoria_df.empty else pd.DataFrame()
    if pendentes_df.empty:
        st.info("Não há entradas pendentes.")
    else:
        opcoes = [f"{row['ID']} — {row['Jogo']} — {row['Mercado']} — {dinheiro(float(row['Entrada R$']))}" for _, row in pendentes_df.iterrows()]
        escolha = st.selectbox("Entrada para fechar", opcoes)
        id_escolhido = escolha.split(" — ")[0]
        with st.form("form_fechar"):
            status = st.selectbox("Resultado", ["Ganhou", "Perdeu", "Anulada", "Encerrada antes"])
            cot_fech = st.text_input("Cotação de fechamento", placeholder="Opcional. Ex.: 1,72")
            cashout = st.number_input("Valor recebido se encerrou antes", min_value=0.0, value=0.0, step=1.0)
            obs = st.text_input("Observação final", placeholder="Opcional")
            fechar = st.form_submit_button("Salvar resultado")
        if fechar:
            cotacao_fechamento = texto_para_float(cot_fech)
            fechar_entrada(id_escolhido, status, cotacao_fechamento, cashout, obs)
            st.success("Resultado salvo.")

    st.markdown("### Histórico")
    auditoria_df = carregar_auditoria()
    if auditoria_df.empty:
        st.info("Nenhuma entrada registrada ainda.")
    else:
        st.dataframe(auditoria_df.sort_values("Data registro", ascending=False), use_container_width=True, hide_index=True)
        csv = auditoria_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar auditoria em CSV",
            data=csv,
            file_name="auditoria_tex_statistics.csv",
            mime="text/csv",
            use_container_width=True,
        )
