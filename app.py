import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io

# Configuração
st.set_page_config(page_title="Motor PRO 2.7 - Intuitivo", layout="wide")

LIGAS = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Premier League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Série A Itália": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv"
}

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

def calcular_power_rating(df, t_casa, t_fora):
    media_gols_feitos_em_casa = np.average(df['HG'], weights=df['Peso'])
    media_gols_feitos_fora = np.average(df['AG'], weights=df['Peso'])
    
    df_c, df_f = df[df['Home'] == t_casa], df[df['Away'] == t_fora]
    
    gf_m = np.average(df_c['HG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gols_feitos_em_casa
    gs_m = np.average(df_c['AG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gols_feitos_fora
    gf_v = np.average(df_f['AG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gols_feitos_fora
    gs_v = np.average(df_f['HG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gols_feitos_em_casa

    xg_c = (gf_m / media_gols_feitos_em_casa) * (gs_v / media_gols_feitos_fora) * media_gols_feitos_em_casa
    xg_f = (gf_v / media_gols_feitos_fora) * (gs_m / media_gols_feitos_em_casa) * media_gols_feitos_fora
    return xg_c, xg_f

# ==========================================
# INTERFACE
# ==========================================
st.title("🚀 Motor Quantitativo PRO 2.7")
liga_sel = st.sidebar.selectbox("Liga", list(LIGAS.keys()))
df = extrair_dados(LIGAS[liga_sel])

if not df.empty:
    times = sorted(df['Home'].unique())
    c1, c2 = st.columns(2)
    t_casa = c1.selectbox("🏠 Time da Casa", times)
    t_fora = c2.selectbox("✈️ Time Visitante", times)

    st.sidebar.subheader("Odds da Corretora")
    # Nomes claros nos inputs
    odd_h = float(st.sidebar.text_input("Vitória Casa", "2.00").replace(',', '.'))
    odd_d = float(st.sidebar.text_input("Empate", "3.30").replace(',', '.'))
    odd_a = float(st.sidebar.text_input("Vitória Fora", "3.80").replace(',', '.'))
    odd_1x = float(st.sidebar.text_input("Casa ou Empate", "1.25").replace(',', '.'))
    odd_x2 = float(st.sidebar.text_input("Fora ou Empate", "1.80").replace(',', '.'))
    odd_dnb_h = float(st.sidebar.text_input("Casa ou Empate (Anula)", "1.45").replace(',', '.'))
    odd_dnb_a = float(st.sidebar.text_input("Fora ou Empate (Anula)", "2.70").replace(',', '.'))
    odd_o25 = float(st.sidebar.text_input("Mais de 2.5 Gols", "1.90").replace(',', '.'))
    odd_btts = float(st.sidebar.text_input("Ambas Marcam", "1.85").replace(',', '.'))

    if st.button("CALCULAR MOTOR 2.7"):
        xg_c, xg_f = calcular_power_rating(df, t_casa, t_fora)
        p_c = [poisson.pmf(i, xg_c) for i in range(11)]
        p_f = [poisson.pmf(i, xg_f) for i in range(11)]
        
        prob_h = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i > j)
        prob_d = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i == j)
        prob_a = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i < j)
        
        # Cálculos de prob
        prob_1x = prob_h + prob_d
        prob_x2 = prob_a + prob_d
        prob_dnb_h = prob_h / (prob_h + prob_a) if (prob_h + prob_a) > 0 else 0
        prob_dnb_a = prob_a / (prob_h + prob_a) if (prob_h + prob_a) > 0 else 0
        prob_o25 = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i + j > 2.5)
        prob_btts = (1 - p_c[0]) * (1 - p_f[0])

        # Tabela Final Limpa
        res = pd.DataFrame({
            "Mercado": ["Casa", "Empate", "Fora", "Casa ou Empate", "Fora ou Empate", "Casa ou Anula", "Fora ou Anula", "Mais de 2.5 Gols", "Ambas Marcam"],
            "Fairline": [1/prob_h, 1/prob_d, 1/prob_a, 1/prob_1x, 1/prob_x2, 1/prob_dnb_h, 1/prob_dnb_a, 1/prob_o25, 1/prob_btts],
            "Odd Banca": [odd_h, odd_d, odd_a, odd_1x, odd_x2, odd_dnb_h, odd_dnb_a, odd_o25, odd_btts],
            "EV %": [(prob_h*odd_h-1)*100, (prob_d*odd_d-1)*100, (prob_a*odd_a-1)*100, (prob_1x*odd_1x-1)*100, 
                     (prob_x2*odd_x2-1)*100, (prob_dnb_h*odd_dnb_h-1)*100, (prob_dnb_a*odd_dnb_a-1)*100, 
                     (prob_o25*odd_o25-1)*100, (prob_btts*odd_btts-1)*100]
        })
        st.table(res.style.format({"Fairline": "{:.2f}", "Odd Banca": "{:.2f}", "EV %": "{:.1f}%"}))
