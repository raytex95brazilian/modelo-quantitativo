import os
import io
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson

# ============================================================
# TEX STATISTICS PRO 15.5 — HÍBRIDO
# Coração da versão 2.14 + visual em blocos + banca dinâmica + auditoria
# Tela em português brasileiro, sem termos técnicos desnecessários
# ============================================================

st.set_page_config(page_title="TEX PRO 15.5 — Blocos", layout="wide")

# ============================================================
# ESTILO VISUAL — melhor para celular
# ============================================================
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1200px;}
    div[data-testid="stMetricValue"] {font-size: 1.45rem;}
    .card-aposta {
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        margin: 12px 0;
        border: 1px solid rgba(49, 51, 63, 0.15);
        box-shadow: 0 3px 14px rgba(0,0,0,0.07);
        background: #ffffff;
    }
    .card-forte {border-left: 9px solid #0a8f3c;}
    .card-boa {border-left: 9px solid #e6a400;}
    .card-leve {border-left: 9px solid #2779bd;}
    .card-nao {border-left: 9px solid #c62828; opacity: 0.94;}
    .titulo-card {font-size: 1.18rem; font-weight: 800; margin-bottom: 8px;}
    .mercado-card {font-size: 1.42rem; font-weight: 900; margin-bottom: 12px;}
    .linha-info {font-size: 0.98rem; line-height: 1.6;}
    .mini {font-size: 0.83rem; opacity: 0.80;}
    .ok {color: #0a8f3c; font-weight: 900;}
    .warn {color: #bd7b00; font-weight: 900;}
    .bad {color: #c62828; font-weight: 900;}
    .blue {color: #2779bd; font-weight: 900;}
    @media (max-width: 768px) {
        .block-container {padding-left: 0.85rem; padding-right: 0.85rem;}
        .titulo-card {font-size: 1.08rem;}
        .mercado-card {font-size: 1.22rem;}
        .linha-info {font-size: 0.93rem;}
        div[data-testid="stMetricValue"] {font-size: 1.20rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# DADOS
# ============================================================

LIGAS_CSV = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Argentina - Primera Division": "https://www.football-data.co.uk/new/ARG.csv",
    "EUA - MLS": "https://www.football-data.co.uk/new/USA.csv",
    "México - Liga MX": "https://www.football-data.co.uk/new/MEX.csv",
    "Japão - J1 League": "https://www.football-data.co.uk/new/JPN.csv",
    "Suécia - Allsvenskan": "https://www.football-data.co.uk/new/SWE.csv",
    "Noruega - Eliteserien": "https://www.football-data.co.uk/new/NOR.csv",
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
}

LIGAS_API = {
    "Brasileirão Série A": "soccer_brazil_campeonato",
    "Argentina - Primera Division": "soccer_argentina_primera_division",
    "EUA - MLS": "soccer_usa_mls",
    "México - Liga MX": "soccer_mexico_ligamx",
    "Japão - J1 League": "soccer_japan_j_league",
    "Suécia - Allsvenskan": "soccer_sweden_allsvenskan",
    "Noruega - Eliteserien": "soccer_norway_eliteserien",
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
}

MERCADOS = [
    "Vitória Casa",
    "Empate",
    "Vitória Fora",
    "Casa ou Empate",
    "Fora ou Empate",
    "Empate Anula Casa",
    "Empate Anula Fora",
    "Mais de 2.5 gols",
    "Menos de 2.5 gols",
    "Ambos marcam - Sim",
    "Ambos marcam - Não",
]

ARQUIVO_AUDITORIA = "logs/auditoria_tex_pro_15.csv"

# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def dinheiro(valor: float) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def porcentagem(valor: float, casas: int = 1) -> str:
    try:
        return f"{float(valor) * 100:.{casas}f}%".replace(".", ",")
    except Exception:
        return "0,0%"


def numero(valor: float, casas: int = 2) -> str:
    try:
        return f"{float(valor):.{casas}f}".replace(".", ",")
    except Exception:
        return "0,00"


def texto_para_float(txt: str) -> Optional[float]:
    if txt is None:
        return None
    txt = str(txt).strip().replace("R$", "").replace(" ", "")
    if not txt:
        return None
    try:
        # aceita 1,85 e 1.85
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


def odd_valida(odd: Optional[float]) -> bool:
    return odd is not None and odd > 1.01 and np.isfinite(odd)


@st.cache_data(ttl=3600, show_spinner=False)
def extrair_dados(url: str) -> pd.DataFrame:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=20)
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
            df["DataTemp"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.sort_values("DataTemp", kind="mergesort")
        df = df.tail(1500).reset_index(drop=True)
        # Peso parecido com a versão antiga, mas um pouco mais estável
        df["Peso"] = np.exp(np.linspace(-1.25, 0, len(df)))
        return df
    except Exception:
        return pd.DataFrame()


def media_ponderada(serie: pd.Series, pesos: pd.Series, padrao: float) -> float:
    try:
        if len(serie) == 0:
            return float(padrao)
        return float(np.average(serie, weights=pesos))
    except Exception:
        return float(padrao)

# ============================================================
# MOTOR — base antiga melhorada
# ============================================================

def media_ponderada_estabilizada(serie: pd.Series, pesos: pd.Series, media_liga: float, k: float = 10.0) -> float:
    """
    Média do time puxada para a média da liga quando a amostra é pequena.

    Exemplo: se o visitante tem só 1 jogo fora, o app não pode concluir que ele
    é péssimo ou excelente. Com poucos jogos, a média da liga pesa mais.
    """
    try:
        n = len(serie)
        if n == 0:
            return float(media_liga)
        media_time = float(np.average(serie, weights=pesos))
        return float(((n * media_time) + (k * media_liga)) / (n + k))
    except Exception:
        return float(media_liga)


def calcular_forcas_e_probabilidades(df: pd.DataFrame, time_casa: str, time_fora: str) -> Tuple[float, float, Dict[str, float], float, Dict[str, object]]:
    """
    Motor híbrido 15.5:
    - mantém a lógica simples da versão 2.14;
    - usa Poisson direto;
    - corrige o erro de amostra pequena;
    - puxa dados pobres para a média da liga;
    - reduz confiança quando um dos lados tem poucos jogos no mando certo.
    """
    media_gols_casa_liga = max(0.20, float(np.average(df["HG"], weights=df["Peso"])))
    media_gols_fora_liga = max(0.20, float(np.average(df["AG"], weights=df["Peso"])))

    jogos_casa = df[df["Home"] == time_casa]
    jogos_fora = df[df["Away"] == time_fora]

    amostra_casa = len(jogos_casa)
    amostra_fora = len(jogos_fora)
    amostra_minima = min(amostra_casa, amostra_fora)
    amostra_total = amostra_casa + amostra_fora

    # Quanto menor a amostra, mais a média da liga entra no cálculo.
    # Isso evita absurdos como visitante com 1 jogo fora virar ataque 0,20.
    k_casa = 10.0
    k_fora = 12.0

    gols_feitos_casa = media_ponderada_estabilizada(jogos_casa["HG"], jogos_casa["Peso"], media_gols_casa_liga, k=k_casa)
    gols_sofridos_casa = media_ponderada_estabilizada(jogos_casa["AG"], jogos_casa["Peso"], media_gols_fora_liga, k=k_casa)
    gols_feitos_fora = media_ponderada_estabilizada(jogos_fora["AG"], jogos_fora["Peso"], media_gols_fora_liga, k=k_fora)
    gols_sofridos_fora = media_ponderada_estabilizada(jogos_fora["HG"], jogos_fora["Peso"], media_gols_casa_liga, k=k_fora)

    forca_ataque_casa = gols_feitos_casa / media_gols_casa_liga if media_gols_casa_liga > 0 else 1.0
    fragilidade_defesa_fora = gols_sofridos_fora / media_gols_casa_liga if media_gols_casa_liga > 0 else 1.0
    forca_ataque_fora = gols_feitos_fora / media_gols_fora_liga if media_gols_fora_liga > 0 else 1.0
    fragilidade_defesa_casa = gols_sofridos_casa / media_gols_fora_liga if media_gols_fora_liga > 0 else 1.0

    gols_esperados_casa = media_gols_casa_liga * forca_ataque_casa * fragilidade_defesa_fora
    gols_esperados_fora = media_gols_fora_liga * forca_ataque_fora * fragilidade_defesa_casa

    gols_esperados_casa = float(np.clip(gols_esperados_casa, 0.25, 4.00))
    gols_esperados_fora = float(np.clip(gols_esperados_fora, 0.25, 4.00))

    tamanho = 15
    matriz = np.zeros((tamanho, tamanho), dtype=float)
    for g_c in range(tamanho):
        for g_f in range(tamanho):
            matriz[g_c, g_f] = poisson.pmf(g_c, gols_esperados_casa) * poisson.pmf(g_f, gols_esperados_fora)

    soma = matriz.sum()
    if soma > 0:
        matriz = matriz / soma

    prob_casa = float(np.tril(matriz, -1).sum())
    prob_empate = float(np.diag(matriz).sum())
    prob_fora = float(np.triu(matriz, 1).sum())
    prob_mais25 = float(matriz[np.add.outer(np.arange(tamanho), np.arange(tamanho)) >= 3].sum())
    prob_ambos_sim = float(matriz[1:, 1:].sum())

    probabilidades = {
        "Vitória Casa": prob_casa,
        "Empate": prob_empate,
        "Vitória Fora": prob_fora,
        "Casa ou Empate": prob_casa + prob_empate,
        "Fora ou Empate": prob_fora + prob_empate,
        "Mais de 2.5 gols": prob_mais25,
        "Menos de 2.5 gols": 1.0 - prob_mais25,
        "Ambos marcam - Sim": prob_ambos_sim,
        "Ambos marcam - Não": 1.0 - prob_ambos_sim,
    }

    total_sem_empate = prob_casa + prob_fora
    probabilidades["Empate Anula Casa"] = prob_casa / total_sem_empate if total_sem_empate > 0 else 0.0
    probabilidades["Empate Anula Fora"] = prob_fora / total_sem_empate if total_sem_empate > 0 else 0.0

    # Confiança nova: quem manda é o lado com MENOS amostra.
    # Se visitante tem 1 jogo fora, confiança fica baixa, mesmo que o mandante tenha 90 jogos.
    confianca_minima_mando = min(100.0, (amostra_minima / 12.0) * 100.0)
    confianca_total = min(100.0, (amostra_total / 70.0) * 100.0)
    equilibrio = amostra_minima / max(1, max(amostra_casa, amostra_fora))

    confianca = (confianca_minima_mando * 0.70) + (confianca_total * 0.20) + (equilibrio * 10.0)

    if amostra_minima < 4:
        confianca = min(confianca, 35.0)
    elif amostra_minima < 8:
        confianca = min(confianca, 49.0)

    confianca = float(np.clip(confianca, 0.0, 100.0))

    if amostra_minima < 4:
        alerta = "Amostra muito baixa: não operar com dinheiro real."
    elif amostra_minima < 8:
        alerta = "Amostra baixa: observar ou usar valor simbólico."
    else:
        alerta = "Amostra suficiente para análise."

    amostras = {
        "casa": amostra_casa,
        "fora": amostra_fora,
        "total": amostra_total,
        "minima": amostra_minima,
        "alerta": alerta,
        "amostra_fraca": amostra_minima < 8,
    }
    return gols_esperados_casa, gols_esperados_fora, probabilidades, confianca, amostras

# ============================================================
# ODDS MANUAIS E API
# ============================================================

def input_odd(label: str, key: str) -> Optional[float]:
    valor = st.text_input(label, value="", key=key, placeholder="ex: 2,10")
    x = texto_para_float(valor)
    return x if odd_valida(x) else None


def coletar_odds_manuais(prefixo: str = "manual") -> Dict[str, float]:
    st.markdown("### Cotações da casa")
    st.caption("Preencha só o que você quer analisar. Campo vazio fica fora do cálculo.")

    odds: Dict[str, float] = {}

    st.markdown("**Resultado do jogo**")
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
        odds["Mais de 2.5 gols"] = input_odd("Mais de 2.5 gols", f"{prefixo}_mais25")
    with c2:
        odds["Menos de 2.5 gols"] = input_odd("Menos de 2.5 gols", f"{prefixo}_menos25")

    st.markdown("**Ambos marcam**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Ambos marcam - Sim"] = input_odd("Ambos marcam - Sim", f"{prefixo}_btts_sim")
    with c2:
        odds["Ambos marcam - Não"] = input_odd("Ambos marcam - Não", f"{prefixo}_btts_nao")

    st.markdown("**Proteções**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Casa ou Empate"] = input_odd("Casa ou Empate", f"{prefixo}_casa_empate")
    with c2:
        odds["Fora ou Empate"] = input_odd("Fora ou Empate", f"{prefixo}_fora_empate")

    c1, c2 = st.columns(2)
    with c1:
        odds["Empate Anula Casa"] = input_odd("Empate Anula Casa", f"{prefixo}_anula_casa")
    with c2:
        odds["Empate Anula Fora"] = input_odd("Empate Anula Fora", f"{prefixo}_anula_fora")

    return {m: o for m, o in odds.items() if odd_valida(o)}


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


def achar_time(nome_api: str, times_csv: List[str]) -> str:
    import difflib
    alvo = (nome_api or "").lower().replace("fc", "").replace("ec", "").replace("ac", "").strip()
    candidatos = [t.lower() for t in times_csv]
    achados = difflib.get_close_matches(alvo, candidatos, n=1, cutoff=0.68)
    if achados:
        return next(t for t in times_csv if t.lower() == achados[0])
    return times_csv[0]


def mediana(valores: List[float]) -> Optional[float]:
    limpos = [float(v) for v in valores if odd_valida(v)]
    if not limpos:
        return None
    return float(np.median(limpos))


def extrair_odds_de_jogo_api(jogo: dict) -> Dict[str, float]:
    pools = {m: [] for m in [
        "Vitória Casa", "Empate", "Vitória Fora", "Mais de 2.5 gols", "Menos de 2.5 gols", "Ambos marcam - Sim", "Ambos marcam - Não"
    ]}

    casa_api = jogo.get("home_team")
    fora_api = jogo.get("away_team")

    for book in jogo.get("bookmakers", []):
        for market in book.get("markets", []):
            key = market.get("key")
            for out in market.get("outcomes", []):
                nome = out.get("name")
                odd = texto_para_float(out.get("price"))
                if not odd_valida(odd):
                    continue

                if key == "h2h":
                    if nome == casa_api:
                        pools["Vitória Casa"].append(odd)
                    elif nome == "Draw":
                        pools["Empate"].append(odd)
                    elif nome == fora_api:
                        pools["Vitória Fora"].append(odd)

                elif key == "totals":
                    try:
                        ponto = float(out.get("point", 0))
                    except Exception:
                        ponto = 0
                    if abs(ponto - 2.5) < 0.001:
                        if nome == "Over":
                            pools["Mais de 2.5 gols"].append(odd)
                        elif nome == "Under":
                            pools["Menos de 2.5 gols"].append(odd)

                elif key == "btts":
                    if nome == "Yes":
                        pools["Ambos marcam - Sim"].append(odd)
                    elif nome == "No":
                        pools["Ambos marcam - Não"].append(odd)

    odds = {}
    for mercado, vals in pools.items():
        m = mediana(vals)
        if m is not None:
            odds[mercado] = m
    return odds

# ============================================================
# DECISÃO DE ENTRADA
# ============================================================

def classificar_entrada(prob: float, odd: float, confianca: float, perfil: str) -> Dict[str, object]:
    valor = (prob * odd) - 1.0
    odd_justa = 1.0 / prob if prob > 0 else np.inf

    if perfil == "Conservador":
        regras = [
            (0.18, 75, 0.030, "forte"),
            (0.13, 65, 0.020, "boa"),
            (0.09, 58, 0.010, "leve"),
        ]
    elif perfil == "Volume controlado":
        regras = [
            (0.15, 70, 0.030, "forte"),
            (0.10, 60, 0.020, "boa"),
            (0.06, 52, 0.010, "leve"),
        ]
    else:  # Agressivo com controle
        regras = [
            (0.12, 65, 0.030, "forte"),
            (0.08, 55, 0.020, "boa"),
            (0.04, 50, 0.0075, "leve"),
        ]

    if not odd_valida(odd):
        return {
            "apostar": False,
            "nivel": "nao",
            "percentual": 0.0,
            "motivo": "cotação não informada",
            "valor": valor,
            "odd_justa": odd_justa,
        }

    if confianca < 50:
        return {
            "apostar": False,
            "nivel": "nao",
            "percentual": 0.0,
            "motivo": "amostra baixa",
            "valor": valor,
            "odd_justa": odd_justa,
        }

    for valor_min, conf_min, percentual, nivel in regras:
        if valor >= valor_min and confianca >= conf_min:
            return {
                "apostar": True,
                "nivel": nivel,
                "percentual": percentual,
                "motivo": "valor encontrado",
                "valor": valor,
                "odd_justa": odd_justa,
            }

    motivo = "valor insuficiente"
    if valor > 0 and confianca >= 50:
        motivo = "tem algum valor, mas fraco para entrada"
    return {
        "apostar": False,
        "nivel": "nao",
        "percentual": 0.0,
        "motivo": motivo,
        "valor": valor,
        "odd_justa": odd_justa,
    }


def montar_resultados(probabilidades: Dict[str, float], odds: Dict[str, float], confianca: float, banca: float, perfil: str, limite_total_jogo: float) -> List[Dict[str, object]]:
    resultados = []
    for mercado in MERCADOS:
        if mercado not in probabilidades or mercado not in odds:
            continue
        prob = float(probabilidades[mercado])
        odd = float(odds[mercado])
        decisao = classificar_entrada(prob, odd, confianca, perfil)
        percentual_original = min(float(decisao["percentual"]), 0.03)  # trava máxima: 3% por entrada
        resultados.append({
            "mercado": mercado,
            "probabilidade": prob,
            "odd": odd,
            "odd_justa": float(decisao["odd_justa"]),
            "valor": float(decisao["valor"]),
            "apostar": bool(decisao["apostar"]),
            "nivel": str(decisao["nivel"]),
            "percentual": percentual_original if decisao["apostar"] else 0.0,
            "percentual_original": percentual_original if decisao["apostar"] else 0.0,
            "entrada_rs": banca * percentual_original if banca > 0 and decisao["apostar"] else 0.0,
            "motivo": str(decisao["motivo"]),
        })

    ordem = {"forte": 0, "boa": 1, "leve": 2, "nao": 3}
    resultados.sort(key=lambda r: (ordem.get(r["nivel"], 9), -r["valor"]))

    # Limite real de exposição no mesmo jogo.
    # Em vez de permitir 6 entradas de 3%, o app distribui o teto do jogo entre as entradas aprovadas.
    aprovadas = [r for r in resultados if r["apostar"] and float(r["percentual"]) > 0]
    limite_total_jogo = float(np.clip(limite_total_jogo, 0.01, 0.09))
    soma_original = sum(float(r["percentual"]) for r in aprovadas)

    if aprovadas and soma_original > limite_total_jogo:
        fator = limite_total_jogo / soma_original
        for r in aprovadas:
            novo_percentual = float(r["percentual"]) * fator
            # Abaixo de 0,30% fica pequeno demais para execução prática. Mantém como observação.
            if novo_percentual < 0.003:
                r["apostar"] = False
                r["nivel"] = "nao"
                r["percentual"] = 0.0
                r["entrada_rs"] = 0.0
                r["motivo"] = "valor existe, mas ficou pequeno após limite do jogo"
            else:
                r["percentual"] = novo_percentual
                r["entrada_rs"] = banca * novo_percentual if banca > 0 else 0.0
                r["motivo"] = "valor encontrado; entrada ajustada pelo limite do jogo"

    resultados.sort(key=lambda r: (ordem.get(r["nivel"], 9), -r["valor"]))
    return resultados

# ============================================================
# AUDITORIA
# ============================================================

def garantir_pasta_logs() -> None:
    os.makedirs("logs", exist_ok=True)


def carregar_auditoria() -> pd.DataFrame:
    garantir_pasta_logs()
    if os.path.exists(ARQUIVO_AUDITORIA):
        try:
            return pd.read_csv(ARQUIVO_AUDITORIA)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def salvar_auditoria(df: pd.DataFrame) -> None:
    garantir_pasta_logs()
    df.to_csv(ARQUIVO_AUDITORIA, index=False)


def banca_atual_auditada(banca_inicial: float, auditoria: pd.DataFrame) -> float:
    if auditoria.empty or "Resultado R$" not in auditoria.columns:
        return banca_inicial
    valores = pd.to_numeric(auditoria["Resultado R$"], errors="coerce").fillna(0.0)
    return float(banca_inicial + valores.sum())


def registrar_entrada(
    auditoria: pd.DataFrame,
    liga: str,
    jogo: str,
    casa_apostas: str,
    mercado: str,
    odd: float,
    prob: float,
    odd_justa: float,
    valor: float,
    percentual: float,
    entrada_rs: float,
    banca_antes: float,
    origem: str,
    observacao: str = "",
) -> pd.DataFrame:
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
        "Valor esperado %": round(float(valor) * 100, 2),
        "Entrada %": round(float(percentual) * 100, 3),
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
    return pd.concat([auditoria, pd.DataFrame([nova])], ignore_index=True)


def calcular_resultado(status: str, entrada_rs: float, odd_entrada: float, valor_cashout: float = 0.0) -> float:
    if status == "Green":
        return entrada_rs * (odd_entrada - 1.0)
    if status == "Red":
        return -entrada_rs
    if status == "Void":
        return 0.0
    if status == "Cashout":
        return valor_cashout - entrada_rs
    return 0.0




def limpar_nome_aba(nome: str, usados: set) -> str:
    """Limpa nome de aba para Excel sem depender de biblioteca externa."""
    proibidos = ['\\', '/', '*', '[', ']', ':', '?']
    nome = str(nome or "Aba")
    for c in proibidos:
        nome = nome.replace(c, "-")
    nome = nome.strip()[:31] or "Aba"
    base = nome
    i = 2
    while nome in usados:
        sufixo = f" {i}"
        nome = (base[:31 - len(sufixo)] + sufixo).strip()
        i += 1
    usados.add(nome)
    return nome


def coluna_excel(n: int) -> str:
    """Converte 1 -> A, 27 -> AA."""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def gerar_excel_simples(abas: Dict[str, pd.DataFrame]) -> bytes:
    """
    Gera arquivo .xlsx usando apenas bibliotecas internas do Python.
    Assim o app não quebra se o Streamlit Cloud não tiver openpyxl instalado.
    """
    import zipfile
    import html

    buffer = io.BytesIO()
    usados = set()
    nomes_abas = [limpar_nome_aba(nome, usados) for nome in abas.keys()]

    def valor_xml(valor):
        if valor is None:
            return ""
        try:
            if pd.isna(valor):
                return ""
        except Exception:
            pass
        if isinstance(valor, (datetime, date)):
            return valor.strftime("%Y-%m-%d")
        return str(valor)

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        content_types = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        ]
        for i in range(1, len(nomes_abas) + 1):
            content_types.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        content_types.append('</Types>')
        z.writestr('[Content_Types].xml', ''.join(content_types))

        z.writestr(
            '_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

        sheets_xml = []
        rels_xml = []
        for i, nome in enumerate(nomes_abas, start=1):
            nome_esc = html.escape(nome, quote=True)
            sheets_xml.append(f'<sheet name="{nome_esc}" sheetId="{i}" r:id="rId{i}"/>')
            rels_xml.append(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            )

        z.writestr(
            'xl/workbook.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>' + ''.join(sheets_xml) + '</sheets></workbook>'
        )
        z.writestr(
            'xl/_rels/workbook.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(rels_xml) +
            '</Relationships>'
        )

        for idx, (aba_original, df) in enumerate(abas.items(), start=1):
            df = df.copy()
            if df.empty:
                df = pd.DataFrame([{"Aviso": "Sem registros."}])

            linhas = [list(df.columns)] + df.astype(object).where(pd.notnull(df), "").values.tolist()
            max_cols = max([len(linha) for linha in linhas] + [1])

            # Largura simples das colunas
            cols_xml = ['<cols>']
            for c in range(1, max_cols + 1):
                textos_coluna = [valor_xml(linha[c - 1]) if c - 1 < len(linha) else "" for linha in linhas[:200]]
                largura = min(max(10, max(len(t) for t in textos_coluna) + 2), 38)
                cols_xml.append(f'<col min="{c}" max="{c}" width="{largura}" customWidth="1"/>')
            cols_xml.append('</cols>')

            rows_xml = []
            for r_idx, linha in enumerate(linhas, start=1):
                cells = []
                for c_idx, valor in enumerate(linha, start=1):
                    ref = f"{coluna_excel(c_idx)}{r_idx}"
                    if isinstance(valor, (int, float, np.integer, np.floating)) and np.isfinite(valor):
                        cells.append(f'<c r="{ref}" t="n"><v>{float(valor)}</v></c>')
                    else:
                        texto = html.escape(valor_xml(valor), quote=False)
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{texto}</t></is></c>')
                rows_xml.append(f'<row r="{r_idx}">' + ''.join(cells) + '</row>')

            sheet_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                + ''.join(cols_xml) +
                '<sheetData>' + ''.join(rows_xml) + '</sheetData>'
                '</worksheet>'
            )
            z.writestr(f'xl/worksheets/sheet{idx}.xml', sheet_xml)

    buffer.seek(0)
    return buffer.getvalue()


def gerar_excel_auditoria(auditoria: pd.DataFrame, banca_inicial: float) -> bytes:
    """Gera Excel completo da auditoria sem depender de openpyxl."""
    if auditoria.empty:
        return gerar_excel_simples({"Historico": pd.DataFrame([{"Aviso": "Ainda não há entradas registradas na auditoria."}])})

    base = auditoria.copy()
    base["Resultado R$"] = pd.to_numeric(base.get("Resultado R$", 0), errors="coerce").fillna(0.0)
    base["Entrada R$"] = pd.to_numeric(base.get("Entrada R$", 0), errors="coerce").fillna(0.0)
    base["Valor esperado %"] = pd.to_numeric(base.get("Valor esperado %", 0), errors="coerce")
    base["Vantagem no fechamento %"] = pd.to_numeric(base.get("Vantagem no fechamento %", 0), errors="coerce")

    fechadas = base[base["Status"].astype(str).isin(["Green", "Red", "Void", "Cashout"])].copy()
    pendentes = base[base["Status"].astype(str) == "Pendente"].copy()

    lucro_total = float(base["Resultado R$"].sum())
    total_entradas = int(len(base))
    total_fechadas = int(len(fechadas))
    valor_total_apostado = float(fechadas["Entrada R$"].sum()) if total_fechadas else 0.0
    retorno_percentual = (lucro_total / valor_total_apostado * 100.0) if valor_total_apostado > 0 else 0.0
    banca_final = float(banca_inicial + lucro_total)
    acertos = int((fechadas["Status"].astype(str) == "Green").sum()) if total_fechadas else 0
    reds = int((fechadas["Status"].astype(str) == "Red").sum()) if total_fechadas else 0
    anuladas = int((fechadas["Status"].astype(str) == "Void").sum()) if total_fechadas else 0
    taxa_acerto = (acertos / max(1, acertos + reds) * 100.0) if total_fechadas else 0.0
    vantagem_media = float(fechadas["Vantagem no fechamento %"].dropna().mean()) if not fechadas.empty else 0.0

    resumo = pd.DataFrame([
        {"Indicador": "Banca inicial", "Valor": banca_inicial},
        {"Indicador": "Banca atual pela auditoria", "Valor": banca_final},
        {"Indicador": "Resultado total R$", "Valor": lucro_total},
        {"Indicador": "Entradas registradas", "Valor": total_entradas},
        {"Indicador": "Entradas fechadas", "Valor": total_fechadas},
        {"Indicador": "Entradas pendentes", "Valor": int(len(pendentes))},
        {"Indicador": "Greens", "Valor": acertos},
        {"Indicador": "Reds", "Valor": reds},
        {"Indicador": "Anuladas", "Valor": anuladas},
        {"Indicador": "Taxa de acerto %", "Valor": round(taxa_acerto, 2)},
        {"Indicador": "Total apostado em entradas fechadas", "Valor": round(valor_total_apostado, 2)},
        {"Indicador": "Retorno sobre valor apostado %", "Valor": round(retorno_percentual, 2)},
        {"Indicador": "Vantagem média no fechamento %", "Valor": round(vantagem_media, 2)},
    ])

    abas = {"Historico": base, "Resumo": resumo}

    for coluna, aba in [
        ("Mercado", "Por mercado"),
        ("Liga", "Por liga"),
        ("Casa de apostas", "Por casa"),
    ]:
        if coluna in fechadas.columns and not fechadas.empty:
            agrupado = (
                fechadas.groupby(coluna, dropna=False)
                .agg(
                    Entradas=("ID", "count"),
                    Total_apostado=("Entrada R$", "sum"),
                    Resultado=("Resultado R$", "sum"),
                    Valor_esperado_medio=("Valor esperado %", "mean"),
                    Vantagem_fechamento_media=("Vantagem no fechamento %", "mean"),
                )
                .reset_index()
            )
            agrupado["Retorno_%"] = np.where(
                agrupado["Total_apostado"] > 0,
                agrupado["Resultado"] / agrupado["Total_apostado"] * 100.0,
                0.0,
            )
            abas[aba] = agrupado.round(2)

    if not pendentes.empty:
        abas["Pendentes"] = pendentes

    return gerar_excel_simples(abas)


CALENDARIO_LIGAS = [
    {"Liga": "Brasileirão Série A", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "ativo", "Jun": "ativo", "Jul": "ativo", "Ago": "ativo", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "encerra", "Observação": "Temporada 2026 prevista de jan/fev a dez. Melhor para análises: depois da 6ª rodada."},
    {"Liga": "Argentina - Primera Division", "Jan": "início", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "ativo", "Jun": "ativo", "Jul": "ativo", "Ago": "ativo", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "encerra", "Observação": "Calendário longo em 2026. Boa liga para volume, mas cuidado com formato e mata-mata."},
    {"Liga": "EUA - MLS", "Jan": "", "Fev": "início", "Mar": "ativo", "Abr": "ativo", "Mai": "pausa", "Jun": "pausa", "Jul": "retoma", "Ago": "ativo", "Set": "ativo", "Out": "ativo", "Nov": "playoffs", "Dez": "playoffs", "Observação": "Pausa longa pela Copa do Mundo. Boa para volume fora do calendário europeu."},
    {"Liga": "México - Liga MX", "Jan": "Clausura", "Fev": "Clausura", "Mar": "Clausura", "Abr": "Clausura", "Mai": "mata-mata", "Jun": "pausa", "Jul": "Apertura", "Ago": "Apertura", "Set": "Apertura", "Out": "Apertura", "Nov": "mata-mata", "Dez": "mata-mata", "Observação": "Dois torneios. Boa liga para manter operação quase o ano todo."},
    {"Liga": "Japão - J1 League", "Jan": "", "Fev": "início", "Mar": "ativo", "Abr": "ativo", "Mai": "ativo", "Jun": "playoff/pausa", "Jul": "pausa", "Ago": "nova temporada", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "2026 é ano de transição: torneio especial no 1º semestre e novo calendário a partir de agosto."},
    {"Liga": "Suécia - Allsvenskan", "Jan": "", "Fev": "", "Mar": "", "Abr": "início", "Mai": "ativo", "Jun": "ativo", "Jul": "ativo", "Ago": "ativo", "Set": "ativo", "Out": "ativo", "Nov": "encerra", "Dez": "", "Observação": "Excelente para cobrir o meio do ano europeu."},
    {"Liga": "Noruega - Eliteserien", "Jan": "", "Fev": "", "Mar": "início", "Abr": "ativo", "Mai": "ativo", "Jun": "ativo", "Jul": "ativo", "Ago": "ativo", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "encerra", "Observação": "Outra ótima liga de calendário anual para cobrir março a dezembro."},
    {"Liga": "Inglaterra - Premier League", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Temporada 26/27 começa em agosto. Mercado líquido, mas mais difícil de bater."},
    {"Liga": "Inglaterra - Championship", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra/playoffs", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Muito volume. Cuidado com calendário congestionado e rotação."},
    {"Liga": "Espanha - La Liga", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Liga forte e mais eficiente. Use como referência, mas exige preço muito bom."},
    {"Liga": "Espanha - Segunda Divisão", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "ativo", "Jun": "playoffs", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Boa para volume, mas muitos jogos truncados; olhar Under também."},
    {"Liga": "Itália - Série A", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Temporada 26/27 começa em agosto e termina em maio."},
    {"Liga": "Itália - Série B", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra/playoffs", "Jun": "playoffs", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Boa para volume, mas com maior variação de elencos e odds menos perfeitas."},
    {"Liga": "Alemanha - Bundesliga", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Bundesliga 26/27 começa no fim de agosto."},
    {"Liga": "Alemanha - 2. Bundesliga", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Começa antes da Bundesliga. Boa para retomar operação em agosto."},
    {"Liga": "França - Ligue 1", "Jan": "retoma", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Tem pausa de fim de ano e volta em janeiro."},
    {"Liga": "Portugal - Primeira Liga", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Começa no início de agosto; boa janela antes das ligas maiores aquecerem."},
    {"Liga": "Holanda - Eredivisie", "Jan": "retoma", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo/pausa", "Observação": "Tende a ter bom volume de gols; útil para mercados de gols."},
    {"Liga": "Bélgica - Pro League", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Calendário europeu; atenção a mudanças de formato."},
    {"Liga": "Turquia - Super Lig", "Jan": "ativo", "Fev": "ativo", "Mar": "ativo", "Abr": "ativo", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início", "Set": "ativo", "Out": "ativo", "Nov": "ativo", "Dez": "ativo", "Observação": "Começa em agosto; atenção a variação de elenco e mando forte."},
]


# ============================================================
# CARD VISUAL
# ============================================================

def render_card(resultado: Dict[str, object], banca: float, time_casa: str, time_fora: str) -> None:
    mercado = str(resultado["mercado"])
    nome_mercado = mercado.replace("Vitória Casa", f"Vitória {time_casa}").replace("Vitória Fora", f"Vitória {time_fora}")

    nivel = str(resultado["nivel"])
    apostar = bool(resultado["apostar"])
    percentual = float(resultado["percentual"])

    if apostar and nivel == "forte":
        classe = "card-forte"
        titulo = f"✅ APOSTAR {percentual*100:.2f}% DA BANCA".replace(".", ",")
        cor = "ok"
    elif apostar and nivel == "boa":
        classe = "card-boa"
        titulo = f"🟡 APOSTAR {percentual*100:.2f}% DA BANCA".replace(".", ",")
        cor = "warn"
    elif apostar and nivel == "leve":
        classe = "card-leve"
        titulo = f"🔵 APOSTAR {percentual*100:.2f}% DA BANCA".replace(".", ",")
        cor = "blue"
    else:
        classe = "card-nao"
        titulo = "❌ NÃO APOSTAR"
        cor = "bad"

    odd_justa_txt = "-" if not np.isfinite(float(resultado["odd_justa"])) else numero(float(resultado["odd_justa"]), 2)

    st.markdown(
        f"""
        <div class="card-aposta {classe}">
            <div class="titulo-card {cor}">{titulo}</div>
            <div class="mercado-card">{nome_mercado}</div>
            <div class="linha-info"><b>Cotação da casa:</b> {numero(float(resultado['odd']), 2)}</div>
            <div class="linha-info"><b>Cotação justa:</b> {odd_justa_txt}</div>
            <div class="linha-info"><b>Chance pelo sistema:</b> {porcentagem(float(resultado['probabilidade']), 1)}</div>
            <div class="linha-info"><b>Valor esperado:</b> {porcentagem(float(resultado['valor']), 1)}</div>
            <div class="linha-info"><b>Entrada sugerida:</b> {dinheiro(float(resultado['entrada_rs']))}</div>
            <div class="mini"><b>Motivo:</b> {resultado['motivo']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# APP
# ============================================================

st.title("TEX STATISTICS PRO 15.5")
st.caption("Motor em blocos: simples para operar, com banca dinâmica e auditoria.")

with st.sidebar:
    st.header("Banca")
    banca_inicial = st.number_input("Banca inicial da auditoria", min_value=0.0, value=1000.0, step=50.0)
    auditoria_sidebar = carregar_auditoria()
    banca_auditada = banca_atual_auditada(banca_inicial, auditoria_sidebar)
    usar_banca_auditada = st.checkbox("Usar banca calculada pela auditoria", value=True)
    banca_manual = st.number_input("Banca manual", min_value=0.0, value=1000.0, step=50.0)
    banca_usada = banca_auditada if usar_banca_auditada else banca_manual
    st.metric("Banca usada pelo sistema", dinheiro(banca_usada))
    st.caption("A entrada máxima por aposta nunca passa de 3% da banca atual; o total no mesmo jogo também é limitado.")

    st.divider()
    st.header("Perfil")
    perfil = st.selectbox(
        "Como quer operar?",
        ["Volume controlado", "Conservador", "Agressivo com controle"],
        index=0,
        help="Volume controlado é o equilíbrio entre a versão antiga e a auditoria nova.",
    )
    limite_total_jogo_pct = st.slider(
        "Máximo total no mesmo jogo",
        min_value=1.0,
        max_value=9.0,
        value=3.0,
        step=0.5,
        help="Proteção contra várias entradas dependentes do mesmo placar. O recomendado é 3%.",
    ) / 100.0

    st.divider()
    st.header("Dados")
    liga_sel = st.selectbox("Liga", list(LIGAS_CSV.keys()))
    chave_api = st.text_input("Chave da API de cotações", value=os.getenv("ODDS_API_KEY", ""), type="password")

    st.divider()
    st.header("Casa de apostas")
    casa_apostas = st.selectbox("Onde você vai apostar?", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"])

aba_analisar, aba_auditoria, aba_calendario = st.tabs(["🎯 Analisar jogo", "📒 Auditoria", "🗓️ Calendário das ligas"])

# O calendário vem antes da análise para nunca depender de jogo selecionado.
with aba_calendario:
    st.subheader("Calendário das ligas do app")
    st.success("Calendário carregado. Se esta aba aparecer vazia em alguma atualização futura, o problema quase sempre é uma parada de execução em outra aba; nesta versão isso foi corrigido.")
    st.caption(
        "Use isto como mapa de operação: quando uma liga estiver no começo, espere algumas rodadas para formar amostra. "
        "Quando estiver no meio da temporada, a leitura do modelo tende a ficar mais confiável."
    )

    calendario_df = pd.DataFrame(CALENDARIO_LIGAS)

    mes_atual = st.selectbox(
        "Escolha o mês para ver as ligas mais úteis",
        ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
        index=datetime.now().month - 1,
    )

    ativas = calendario_df[calendario_df[mes_atual].astype(str).str.strip() != ""].copy()
    st.markdown(f"### Ligas com movimento em {mes_atual}")
    if ativas.empty:
        st.info("Nenhuma liga marcada para este mês no calendário do app.")
    else:
        for _, linha in ativas.iterrows():
            st.markdown(
                f"""
                <div class="card-aposta card-leve">
                    <div class="mercado-card">{linha['Liga']}</div>
                    <div class="linha-info"><b>Status no mês:</b> {linha[mes_atual]}</div>
                    <div class="linha-info"><b>Observação:</b> {linha['Observação']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("Ver tabela completa do calendário"):
        st.dataframe(calendario_df, use_container_width=True, hide_index=True)

    st.markdown("### Como usar na prática")
    st.markdown(
        """
        - **Janeiro a maio:** foco nas ligas europeias em andamento, Argentina, México e Brasil.
        - **Junho e julho:** mês mais perigoso na Europa; priorize Brasil, Argentina, MLS, México, Suécia e Noruega.
        - **Agosto a dezembro:** volta forte da Europa + continuação das ligas de ano calendário.
        - **Evite exagerar nas 3 primeiras rodadas** de qualquer liga, porque elenco, técnico e padrão de gols ainda estão instáveis.
        - **Depois da 6ª rodada**, a leitura estatística fica mais confiável.
        """
    )

    csv_cal = calendario_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "BAIXAR CALENDÁRIO DAS LIGAS EM CSV",
        data=csv_cal,
        file_name="calendario_ligas_tex_pro_15.csv",
        mime="text/csv",
    )

    excel_cal = gerar_excel_simples({"Calendario": calendario_df})
    st.download_button(
        "BAIXAR CALENDÁRIO DAS LIGAS EM EXCEL",
        data=excel_cal,
        file_name="calendario_ligas_tex_pro_15.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )




with aba_analisar:
    with st.spinner("Carregando dados históricos da liga..."):
        df = extrair_dados(LIGAS_CSV[liga_sel])

    if df.empty:
        st.error("Não consegui carregar os dados históricos desta liga.")
        st.stop()

    times = sorted(df["Home"].dropna().unique().tolist())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Jogos históricos", len(df))
    col2.metric("Times", len(times))
    col3.metric("Gols casa", numero(np.average(df["HG"], weights=df["Peso"]), 2))
    col4.metric("Gols fora", numero(np.average(df["AG"], weights=df["Peso"]), 2))

    st.markdown("---")
    modo = st.radio("Escolha o modo de análise", ["Manual", "Automático pela API"], horizontal=True)

    odds: Dict[str, float] = {}
    time_casa = times[0]
    time_fora = times[min(1, len(times)-1)]
    jogo_nome = ""
    origem = modo

    if modo == "Manual":
        st.markdown("### Jogo")
        c1, c2 = st.columns(2)
        with c1:
            time_casa = st.selectbox("Mandante", times, key="time_casa_manual")
        with c2:
            time_fora = st.selectbox("Visitante", times, key="time_fora_manual")

        if time_casa == time_fora:
            st.warning("Mandante e visitante não podem ser o mesmo time. Altere um dos times para analisar. As outras abas continuam funcionando normalmente.")
            botao_analisar = False
        else:
            jogo_nome = f"{time_casa} x {time_fora}"
            odds = coletar_odds_manuais("manual")
            botao_analisar = st.button("ANALISAR JOGO MANUAL", type="primary")

    else:
        if not chave_api:
            st.warning("Informe a chave da API na barra lateral. Se a API não tiver jogo disponível, use o modo manual.")
            botao_analisar = False
        elif liga_sel not in LIGAS_API:
            st.warning("Esta liga não está mapeada na API. Use o modo manual.")
            botao_analisar = False
        else:
            with st.spinner("Buscando jogos na API..."):
                jogos_api = buscar_odds_api(chave_api, LIGAS_API[liga_sel])

            if not jogos_api:
                st.warning("API sem dados disponíveis para esta liga agora. Isso não significa que sua chave está errada. Pode não haver jogo aberto, mercado disponível ou cobertura para esta liga neste momento. Use o modo manual.")
                botao_analisar = False
            else:
                opcoes = {}
                agora = pd.Timestamp.now(tz="UTC")
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
                    st.warning("A API respondeu, mas não há partida pré-jogo disponível. Use o modo manual.")
                    botao_analisar = False
                else:
                    escolha = st.selectbox("Partida", list(opcoes.keys()))
                    jogo_api = opcoes[escolha]
                    time_casa = achar_time(jogo_api.get("home_team", ""), times)
                    time_fora = achar_time(jogo_api.get("away_team", ""), times)

                    c1, c2 = st.columns(2)
                    with c1:
                        time_casa = st.selectbox("Mandante na base", times, index=times.index(time_casa), key="time_casa_api")
                    with c2:
                        time_fora = st.selectbox("Visitante na base", times, index=times.index(time_fora), key="time_fora_api")

                    odds = extrair_odds_de_jogo_api(jogo_api)
                    jogo_nome = f"{time_casa} x {time_fora}"
                    st.info(f"Cotações reais encontradas: {len(odds)} mercado(s). Mercados de proteção só entram no automático se a API entregar esse tipo de cotação.")
                    botao_analisar = st.button("ANALISAR JOGO AUTOMÁTICO", type="primary")

    if botao_analisar and not odds:
        st.error("Nenhuma cotação válida foi informada ou encontrada.")

    if botao_analisar and odds:
        gols_casa, gols_fora, probabilidades, confianca, amostras = calcular_forcas_e_probabilidades(df, time_casa, time_fora)
        resultados = montar_resultados(probabilidades, odds, confianca, banca_usada, perfil, limite_total_jogo_pct)
        aprovadas = [r for r in resultados if r["apostar"]]

        st.markdown("---")
        st.subheader(f"Análise — {jogo_nome}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Força de gols casa", numero(gols_casa, 2))
        m2.metric("Força de gols fora", numero(gols_fora, 2))
        m3.metric("Confiança", f"{confianca:.1f}%".replace(".", ","))
        m4.metric("Entradas", len(aprovadas))
        m5.metric("Máximo no jogo", dinheiro(banca_usada * limite_total_jogo_pct))

        st.caption(f"Amostra: {time_casa} em casa {amostras['casa']} jogos | {time_fora} fora {amostras['fora']} jogos.")
        if amostras.get("amostra_fraca"):
            st.error(f"⚠️ {amostras.get('alerta')} O lado com menor amostra tem apenas {amostras.get('minima')} jogo(s). O app bloqueia entradas reais nesse cenário.")
        else:
            st.success(str(amostras.get("alerta", "Amostra suficiente para análise.")))

        if aprovadas:
            total_sugerido = sum(float(r["entrada_rs"]) for r in aprovadas)
            st.success(f"Foram encontradas {len(aprovadas)} entrada(s). Total sugerido se fizer todas: {dinheiro(total_sugerido)}.")
            if total_sugerido >= banca_usada * limite_total_jogo_pct * 0.99 and len(aprovadas) > 1:
                st.warning("As entradas aprovadas foram ajustadas para respeitar o limite total do mesmo jogo. Isso evita concentrar dinheiro demais em mercados que dependem do mesmo placar.")
        else:
            st.info("Nenhuma entrada passou. Se você quiser mais volume, use o perfil 'Agressivo com controle', mas registre tudo na auditoria.")

        st.markdown("### Blocos de decisão")
        for r in resultados:
            render_card(r, banca_usada, time_casa, time_fora)

        if aprovadas:
            st.markdown("---")
            st.markdown("### Registrar entradas aprovadas")
            st.caption("Marque as entradas que você realmente vai fazer. Elas irão para a auditoria.")
            auditoria = carregar_auditoria()
            escolhidas = []
            for i, r in enumerate(aprovadas):
                nome = r["mercado"].replace("Vitória Casa", f"Vitória {time_casa}").replace("Vitória Fora", f"Vitória {time_fora}")
                label = f"Registrar {nome} — {numero(r['odd'], 2)} — {dinheiro(r['entrada_rs'])}"
                if st.checkbox(label, value=True, key=f"reg_{i}_{nome}"):
                    escolhidas.append(r)

            observacao = st.text_area("Observação para a auditoria", value="", placeholder="Ex: Pixbet, cotação conferida antes de apostar, escalação ok...")
            if st.button("SALVAR ENTRADAS MARCADAS NA AUDITORIA", type="primary"):
                for r in escolhidas:
                    auditoria = registrar_entrada(
                        auditoria=auditoria,
                        liga=liga_sel,
                        jogo=jogo_nome,
                        casa_apostas=casa_apostas,
                        mercado=str(r["mercado"]),
                        odd=float(r["odd"]),
                        prob=float(r["probabilidade"]),
                        odd_justa=float(r["odd_justa"]),
                        valor=float(r["valor"]),
                        percentual=float(r["percentual"]),
                        entrada_rs=float(r["entrada_rs"]),
                        banca_antes=float(banca_usada),
                        origem=origem,
                        observacao=observacao,
                    )
                salvar_auditoria(auditoria)
                st.success("Entradas salvas na auditoria.")

with aba_auditoria:
    st.subheader("Auditoria operacional")
    st.caption("Aqui você acompanha banca, resultado e vantagem no fechamento.")
    auditoria = carregar_auditoria()
    banca_calc = banca_atual_auditada(banca_inicial, auditoria)

    c1, c2, c3 = st.columns(3)
    c1.metric("Banca inicial", dinheiro(banca_inicial))
    c2.metric("Banca auditada", dinheiro(banca_calc))
    lucro_total = banca_calc - banca_inicial
    c3.metric("Resultado total", dinheiro(lucro_total))

    st.markdown("---")
    st.markdown("### Lançar entrada manual na auditoria")
    with st.expander("Adicionar entrada que fiz fora do motor"):
        c1, c2 = st.columns(2)
        with c1:
            aud_liga = st.text_input("Liga", value=liga_sel, key="aud_liga")
            aud_jogo = st.text_input("Jogo", value="", placeholder="Ex: Botafogo x Santos", key="aud_jogo")
            aud_mercado = st.selectbox("Mercado", MERCADOS, key="aud_mercado")
            aud_casa = st.selectbox("Casa de apostas", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"], key="aud_casa")
        with c2:
            aud_odd = st.text_input("Cotação de entrada", value="", key="aud_odd")
            aud_entrada = st.text_input("Valor da entrada em R$", value="", key="aud_entrada")
            aud_banca_antes = st.number_input("Banca antes", min_value=0.0, value=float(banca_calc), step=10.0, key="aud_banca_antes")
            aud_obs = st.text_input("Observação", value="", key="aud_obs")

        if st.button("SALVAR ENTRADA MANUAL"):
            odd = texto_para_float(aud_odd)
            entrada = texto_para_float(aud_entrada)
            if not odd_valida(odd) or entrada is None or entrada <= 0 or not aud_jogo.strip():
                st.error("Preencha jogo, cotação válida e valor da entrada.")
            else:
                percentual = entrada / aud_banca_antes if aud_banca_antes > 0 else 0.0
                auditoria = registrar_entrada(
                    auditoria=auditoria,
                    liga=aud_liga,
                    jogo=aud_jogo,
                    casa_apostas=aud_casa,
                    mercado=aud_mercado,
                    odd=float(odd),
                    prob=0.0,
                    odd_justa=0.0,
                    valor=0.0,
                    percentual=percentual,
                    entrada_rs=float(entrada),
                    banca_antes=float(aud_banca_antes),
                    origem="Manual livre",
                    observacao=aud_obs,
                )
                salvar_auditoria(auditoria)
                st.success("Entrada manual salva.")

    st.markdown("---")
    st.markdown("### Fechar resultado de uma entrada")
    if auditoria.empty:
        st.info("Ainda não há entradas registradas.")
    else:
        pendentes = auditoria[auditoria["Status"].astype(str) == "Pendente"].copy()
        if pendentes.empty:
            st.info("Não há entradas pendentes para fechar.")
        else:
            opcoes = []
            mapa = {}
            for idx, row in pendentes.iterrows():
                label = f"{row['ID']} — {row['Jogo']} — {row['Mercado']} — {row['Casa de apostas']} — {dinheiro(row['Entrada R$'])}"
                opcoes.append(label)
                mapa[label] = idx

            escolha = st.selectbox("Escolha a entrada", opcoes)
            idx = mapa[escolha]
            row = auditoria.loc[idx]

            c1, c2, c3 = st.columns(3)
            with c1:
                status = st.selectbox("Resultado", ["Green", "Red", "Void", "Cashout"], key="fechar_status")
            with c2:
                odd_fechamento_txt = st.text_input("Cotação de fechamento", value="", key="fechar_odd")
            with c3:
                valor_cashout = st.number_input("Valor recebido no cashout", min_value=0.0, value=0.0, step=1.0, key="fechar_cashout")

            obs_fechamento = st.text_input("Observação do fechamento", value="", key="fechar_obs")

            if st.button("FECHAR ENTRADA"):
                entrada_rs = float(row["Entrada R$"])
                odd_entrada = float(row["Cotação de entrada"])
                resultado_rs = calcular_resultado(status, entrada_rs, odd_entrada, valor_cashout)
                odd_fechamento = texto_para_float(odd_fechamento_txt)
                vantagem_fechamento = ""
                if odd_valida(odd_fechamento):
                    vantagem_fechamento = round(((odd_entrada / odd_fechamento) - 1.0) * 100.0, 2)

                banca_depois = float(row["Banca antes"]) + resultado_rs
                auditoria.loc[idx, "Status"] = status
                auditoria.loc[idx, "Resultado R$"] = round(resultado_rs, 2)
                auditoria.loc[idx, "Banca depois"] = round(banca_depois, 2)
                auditoria.loc[idx, "Cotação de fechamento"] = odd_fechamento if odd_fechamento is not None else ""
                auditoria.loc[idx, "Vantagem no fechamento %"] = vantagem_fechamento
                auditoria.loc[idx, "Observação"] = str(row.get("Observação", "")) + " | Fechamento: " + obs_fechamento
                salvar_auditoria(auditoria)
                st.success("Entrada fechada e auditoria atualizada.")

    st.markdown("---")
    st.markdown("### Histórico")
    auditoria = carregar_auditoria()
    if auditoria.empty:
        st.info("Nenhum registro ainda.")
    else:
        # Mostra tabela só na auditoria, não na tela principal
        st.dataframe(auditoria.tail(300), use_container_width=True, hide_index=True)
        csv = auditoria.to_csv(index=False).encode("utf-8-sig")
        st.download_button("BAIXAR AUDITORIA EM CSV", data=csv, file_name="auditoria_tex_pro_15.csv", mime="text/csv")

        excel_bytes = gerar_excel_auditoria(auditoria, banca_inicial)
        st.download_button(
            "BAIXAR AUDITORIA EM EXCEL (.xlsx)",
            data=excel_bytes,
            file_name="auditoria_tex_pro_15.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
