import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io

# Configuração da Página
st.set_page_config(page_title="Sistema Quantitativo PRO 2.5", layout="wide")

# ==========================================
# 1. MOTOR (CÁLCULOS E EXTRAÇÃO PRO 2.5)
# ==========================================
LIGAS = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Premier League (Inglaterra)": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "La Liga (Espanha)": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Bundesliga (Alemanha)": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "Serie A (Itália)": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Ligue 1 (França)": "https://www.football-data.co.uk/mmz4281/2526/F1.csv"
}

@st.cache_data(ttl=3600)
def extrair_dados(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200: return pd.DataFrame()

        df = pd.read_csv(io.StringIO(response.text))
        traducao = {'HomeTeam': 'Home', 'AwayTeam': 'Away', 'FTHG': 'HG', 'FTAG': 'AG'}
        df = df.rename(columns=traducao)
        
        # Filtro de robustez
        df = df.dropna(subset=['Home', 'Away', 'HG', 'AG'])
        
        # Aumentei a janela para 1500 jogos para dar lastro estatístico ao Power Rating
        df = df.tail(1500).copy() 
        
        # Decaimento Exponencial (Peso maior para jogos recentes)
        df['Peso'] = np.exp(np.linspace(-1.2, 0, len(df)))
        
        return df
    except:
        return pd.DataFrame()

def calcular_power_rating(df, t_casa, t_fora):
    media_gols_feitos_em_casa = np.average(df['HG'], weights=df['Peso'])
    media_gols_feitos_fora = np.average(df['AG'], weights=df['Peso'])
    
    df_c = df[df['Home'] == t_casa]
    df_f = df[df['Away'] == t_fora]
    
    # Se não houver dados históricos suficientes, usa a média geral (prevenção de erro)
    gf_m = np.average(df_c['HG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gols_feitos_em_casa
    gs_m = np.average(df_c['AG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gols_feitos_fora
    gf_v = np.average(df_f['AG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gols_feitos_fora
    gs_v = np.average(df_f['HG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gols_feitos_em_casa

    forca_atq_c = gf_m / media_gols_feitos_em_casa
    forca_def_c = gs_m / media_gols_feitos_fora
    forca_atq_f = gf_v / media_gols_feitos_fora
    forca_def_f = gs_v / media_gols_feitos_em_casa

    xg_c = forca_atq_c * forca_def_f * media_gols_feitos_em_casa
    xg_f = forca_atq_f * forca_def_c * media_gols_feitos_fora

    return xg_c, xg_f, len(df_c), len(df_f)

# ==========================================
# 2. INTERFACE VISUAL
# ==========================================
st.title("📈 Motor Quantitativo PRO 2.5")
liga_selecionada = st.sidebar.selectbox("Escolha a Liga", list(LIGAS.keys()))
df = extrair_dados(LIGAS[liga_selecionada])

if df.empty:
    st.error("⚠️ Falha ao carregar dados. Verifique a conexão.")
else:
    times = sorted(df['Home'].unique())
    c1, c2 = st.columns(2)
    with c1: t_casa = st.selectbox("🏠 Mandante", times)
    with c2: t_fora = st.selectbox("✈️ Visitante", times)

    # Função de entrada robusta
    def input_odd(label):
        val = st.sidebar.text_input(label, value="2.00")
        try: return float(val.replace(',', '.'))
        except: return 1.00

    odd_h = input_odd("Odd Casa (1)")
    odd_d = input_odd("Odd Empate (X)")
    odd_a = input_odd("Odd Fora (2)")
    odd_dnb_h = input_odd("DNB Casa")
    odd_o25 = input_odd("Over 2.5")

    if st.button("🚀 EXECUTAR ORDEM"):
        xg_c, xg_f, j_c, j_f = calcular_power_rating(df, t_casa, t_fora)
        
        # Probabilidades
        p_c = [poisson.pmf(i, xg_c) for i in range(11)]
        p_f = [poisson.pmf(i, xg_f) for i in range(11)]
        
        prob_h = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i > j)
        prob_d = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i == j)
        prob_a = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i < j)
        prob_o25 = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i + j > 2.5)
        prob_dnb_h = prob_h / (prob_h + prob_a) if (prob_h + prob_a) > 0 else 0

        # Output
        st.subheader("Análise de Valor (EV)")
        res = pd.DataFrame({
            "Mercado": ["Casa", "Empate", "Fora", "DNB Casa", "Over 2.5"],
            "Fairline": [1/prob_h, 1/prob_d, 1/prob_a, 1/prob_dnb_h, 1/prob_o25],
            "Odd Banca": [odd_h, odd_d, odd_a, odd_dnb_h, odd_o25],
            "EV %": [(prob_h*odd_h-1)*100, (prob_d*odd_d-1)*100, (prob_a*odd_a-1)*100, (prob_dnb_h*odd_dnb_h-1)*100, (prob_o25*odd_o25-1)*100]
        })
        st.table(res)
        
