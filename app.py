import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Motor TEX STATISTICS PRO 2.15", layout="wide")

# ==========================================
# CHAVE API HARDCODED (A PEDIDO DO DIRETOR)
# ==========================================
API_KEY = "d9c21f8217e059554c94a263642fc0eb"

# ==========================================
# BANCOS DE DADOS E API
# ==========================================
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
    "Grécia - Super League": "https://www.football-data.co.uk/mmz4281/2526/G1.csv"
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
    "Grécia - Super League": "soccer_greece_super_league"
}

# ==========================================
# FUNÇÕES CORE
# ==========================================
@st.cache_data(ttl=3600)
def extrair_dados(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(response.text))
        df = df.rename(columns={'HomeTeam': 'Home', 'AwayTeam': 'Away', 'FTHG': 'HG', 'FTAG': 'AG'})
        df = df.dropna(subset=['Home', 'Away', 'HG', 'AG']).tail(1500).copy()
        df['Peso'] = np.exp(np.linspace(-1.2, 0, len(df)))
        return df
    except: return pd.DataFrame()

# REMOVIDO O CACHE PARA FORÇAR A LEITURA REAL DA API
def extrair_odds_api(api_key, sport_key):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h,totals,btts&oddsFormat=decimal"
        response = requests.get(url, timeout=15)
        if response.status_code == 200: 
            return response.json()
        elif response.status_code == 401:
            st.error("❌ ERRO 401: A chave da API é inválida ou não tem permissão.")
            return []
        elif response.status_code == 429:
            st.error("❌ ERRO 429: Esgotou o seu limite mensal de requisições da API.")
            return []
        elif response.status_code == 422:
            st.warning(f"⚠️ A liga '{sport_key}' não possui jogos com odds abertas no mundo neste exato momento.")
            return []
        else:
            st.error(f"❌ Falha na comunicação com os servidores globais. Código: {response.status_code}")
            return []
    except Exception as e: 
        st.error(f"❌ Erro crítico de rede: {e}")
        return []

def calcular_power_rating(df, t_casa, t_fora):
    media_gf_c = np.average(df['HG'], weights=df['Peso'])
    media_gf_f = np.average(df['AG'], weights=df['Peso'])
    df_c, df_f = df[df['Home'] == t_casa], df[df['Away'] == t_fora]
    amostra = len(df_c) + len(df_f)
    
    gf_m = np.average(df_c['HG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gf_c
    gs_m = np.average(df_c['AG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gf_f
    gf_v = np.average(df_f['AG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gf_f
    gs_v = np.average(df_f['HG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gf_c

    xg_c = (gf_m / media_gf_c) * (gs_v / media_gf_f) * media_gf_c
    xg_f = (gf_v / media_gf_f) * (gs_m / media_gf_c) * media_gf_f
    return xg_c, xg_f, amostra

def ler_odd(label):
    val = st.sidebar.text_input(label, value="", key=f"manual_{label}")
    if not val: return 1.00
    try: return float(val.replace(',', '.'))
    except: return 1.00

# ==========================================
# ESTRUTURA VISUAL E INTERRUPTOR
# ==========================================
st.sidebar.markdown("## 🎛️ Painel de Controlo Mestre")
modo_operacao = st.sidebar.radio("Selecione o Ambiente de Execução:", ["Modo Manual (Laboratório)", "Modo FULL AUTO (Institucional)"])
st.sidebar.markdown("---")

st.title(f"🚀 Motor TEX STATISTICS PRO 2.15")
st.markdown(f"**Status de Operação:** `{modo_operacao}` | API Conectada Automaticamente")

liga_sel = st.sidebar.selectbox("Liga Operacional", list(LIGAS_CSV.keys()))
banca_total = st.sidebar.number_input("Banca Total (R$)", value=0.0, step=100.0)

df = extrair_dados(LIGAS_CSV[liga_sel])

if not df.empty:
    times_csv = sorted(df['Home'].unique())

    # ==========================================
    # LÓGICA MODO MANUAL
    # ==========================================
    if modo_operacao == "Modo Manual (Laboratório)":
        c1, c2 = st.columns(2)
        t_casa = c1.selectbox("🏠 Mandante", times_csv, key="sel_casa_manual")
        t_fora = c2.selectbox("✈️ Visitante", times_csv, key="sel_fora_manual")

        st.sidebar.subheader("Odds da Corretora (Digitação)")
        odds = {
            "Vitória Casa": ler_odd("Vitória Casa"),
            "Empate": ler_odd("Empate"),
            "Vitória Fora": ler_odd("Vitória Fora"),
            "Casa
